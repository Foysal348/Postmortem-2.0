# Implementation Plan: PostMortem 2.0

## Overview

PostMortem 2.0 is an interactive dependency surgery lab for Python projects, built as a single-process FastAPI application with a gothic autopsy-table UI. The P0 build implements R1–R6 and R9: input validation, metadata recovery, declared graph construction, conflict detection, vulnerability discovery, force-remove, and the data-driven gothic frontend. R7 (Simulation) and R8 (Surgical Report) are P1-deferred and included as optional tasks at the end.

Implementation follows the design in `.kiro/specs/postmortem/design.md` and the requirements in `.kiro/specs/postmortem/requirements.md`. The stack is Python 3.12, FastAPI, Jinja2, `packaging`, `networkx`, `httpx`, SQLite cache, Cytoscape.js, pytest + Hypothesis. Dependencies are managed with `uv`.

The domain layer (`validate.py`, `graph.py`, pure parsing in `metadata.py`/`osv.py`) is pure and is the target of property-based tests (P1–P6, P8, P9–P14). The adapter layer isolates all network/filesystem I/O so failures never escape as exceptions (R2.10).

## Tasks

- [ ] 1. Set up project scaffold and core data models
  - [ ] 1.1 Create project structure, pyproject.toml with uv, and directory layout
    - Create `app/`, `app/surgery/`, `app/templates/`, `app/static/`, `tests/unit/`, `tests/property/` directories per the design module layout
    - Create `pyproject.toml` with uv, declaring dependencies: fastapi, uvicorn, jinja2, packaging, networkx, httpx, pydantic; dev dependencies: pytest, hypothesis
    - Set up pytest configuration with `tests/unit` and `tests/property` as test paths
    - _Requirements: infrastructure — enables all_

  - [ ] 1.2 Implement models.py with all Pydantic models and enums from the design
    - Implement `EvidenceSource` enum (pypi-json, wheel-metadata, osv, pip-report, unknown)
    - Implement `NodeStatus` enum (healthy, conflict, vulnerable, unknown) — the closed enum that makes "Unknown is never healthy" a structural guarantee (R2.11, R3.3)
    - Implement `Evidence`, `PackageNode`, `DependencyEdge`, `Conflict`, `Advisory`, `Finding`, `Operation`, `ResolutionResult`, `SurgeryReport` models with the fields and types specified in the design's Data Models section
    - _Requirements: R2.4, R2.11, R3.3, R4.1, R5.1–R5.3, R7.1, R8.1_

  - [ ]* 1.3 Write unit tests verifying models import, load, and enum invariants
    - Test all models import correctly and can be instantiated with valid data
    - Test `NodeStatus.UNKNOWN != NodeStatus.HEALTHY` (structural invariant for R2.11)
    - Test `EvidenceSource` is a closed set of exactly five values
    - _Requirements: R2.4, R2.11, R3.3_

- [ ] 2. Implement R1 input validation — validate.py
  - [ ] 2.1 Implement strict PEP 508 subset parser, dangerous-construct rejection, normalization, duplicate detection, and unpinned detection
    - Implement `validate_manifest(text: str) -> ValidationResult` as a pure function (no I/O)
    - Processing order: byte size check >64 KB → reject (R1.3); line count >200 non-comment lines → reject (R1.3)
    - Per-line: strip inline comments at first `#`; reject lines starting with `-` as pip options (R1.2); parse with `packaging.requirements.Requirement.parse`; reject if parsed `.url` is non-None (URL/VCS/path) (R1.2); accept only `name[extras] specifier [; marker]` grammar (R1.1)
    - Normalize names with `canonicalize_name` (R1.4); detect duplicates by canonical name (R1.5); mark unpinned (non-`==` specifier) with `pinned = False` (R1.6)
    - Return `ValidationResult` with `requirements: list[ParsedRequirement]`, `errors: list[ValidationError]`, `rejected: bool`
    - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6_

  - [ ]* 2.2 Write property test P1: name normalization is idempotent
    - **Property 1: Name normalization is idempotent** — `norm(norm(x)) == norm(x)` for any package-name string
    - **Validates: Requirements 1.4**
    - Generator: random package-name strings with case variations, `_`, `-`, `.`, repeated separators

  - [ ]* 2.3 Write property test P2: the validator never accepts a dangerous line
    - **Property 2: The validator never accepts a dangerous line** — any line containing a pip option, URL, VCS reference, or local path is rejected with the offending line number
    - **Validates: Requirements 1.1, 1.2**
    - Generator: random lines embedding URLs, VCS prefixes (`git+…`), pip options (`-r`, `-c`, `-e`, `--…`), local paths

  - [ ]* 2.4 Write property test P9: the narrow-grammar parser round-trips
    - **Property 9: The narrow-grammar parser round-trips** — for any valid `name[extras] specifier [; marker]` line, parsing and re-serializing yields an equivalent requirement
    - **Validates: Requirements 1.1**
    - Generator: random valid narrow-grammar lines (name, optional extras, `==` specifier, optional marker)

  - [ ]* 2.5 Write property test P10: duplicate detection keys on canonical names
    - **Property 10: Duplicate detection keys on canonical names** — two lines normalizing to the same PEP 503 name are duplicates; distinct canonical names are never duplicates
    - **Validates: Requirements 1.4, 1.5**
    - Generator: random pairs normalizing to one key + distinct-key pairs

  - [ ]* 2.6 Write unit tests for R1.3 size and line limit boundaries
    - Boundary tests at 64 KB ±1 byte and 200 ±1 requirement lines
    - _Requirements: R1.3_

- [ ] 3. Checkpoint — R1 input validation complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement R2 metadata recovery — metadata.py and cache.py
  - [ ] 4.1 Implement cache.py SQLite caching for PyPI and OSV responses
    - Create SQLite schema: `pypi_metadata`, `osv_batch`, `osv_detail` tables per the design
    - TTL-based freshness (default 24h); cache key uses canonical name (R1.4)
    - Never cache failures as success: 404 cached as durable Unknown; timeout cached with short TTL
    - _Requirements: R2.5_

  - [ ] 4.2 Implement PyPI JSON → wheel METADATA → Unknown fallback chain
    - Implement `recover_dependencies(req: ParsedRequirement, cache: Cache) -> MetadataResult`
    - R2.1: for pinned `name==version`, GET PyPI JSON, read `info.requires_dist`; each becomes a `DependencyEdge` with `evidence.source = "pypi-json"`
    - R2.2: if `requires_dist` missing/empty, find `bdist_wheel` in `releases[version]`, download wheel, read `.dist-info/METADATA` `Requires-Dist` headers without executing package code; `evidence.source = "wheel-metadata"`
    - R2.3: if no wheel exists → dependencies Unknown, `evidence.source = "unknown"`
    - R2.4: every edge records `Evidence` with source, url, fetched_at
    - Wheel METADATA parsed with `packaging.requirements.Requirement` for consistent semantics
    - _Requirements: R2.1, R2.2, R2.3, R2.4_

  - [ ] 4.3 Implement failure handling for all external service failures
    - R2.6: skip metadata and OSV fetching for unpinned nodes (short-circuit, return Unknown)
    - R2.7: PyPI unreachable/timeout → `status = UNKNOWN`, `unknown_reason = "PyPI unreachable"/"PyPI timeout"`
    - R2.9: package/version not on PyPI (404) → `status = UNKNOWN`, `unknown_reason = "not found on PyPI"`
    - R2.10: all network/parse failures caught in adapter layer, converted to Unknown results; no exception ever propagates to caller
    - R2.11: Unknown node status is the `UNKNOWN` enum value, distinct from `HEALTHY` by construction
    - _Requirements: R2.6, R2.7, R2.9, R2.10, R2.11_

  - [ ]* 4.4 Write property test P14: any external-service failure yields a result without raising
    - **Property 14: Any external-service failure yields a result without raising** — for any failure (PyPI/OSV unreachable, timeout, HTTP error, malformed JSON, wheel unzip error, not found), the system returns a result with Unknown status and does not raise
    - **Validates: Requirements 2.7, 2.8, 2.9, 2.10**
    - Generator: random failure modes injected via mock adapters

  - [ ]* 4.5 Write integration tests for R2.1–R2.3 metadata recovery with recorded fixtures
    - Test PyPI JSON path with recorded fixture (including `flask 0.12.2` empty-`requires_dist` fallback to wheel METADATA)
    - Test no-wheel Unknown case (`markupsafe 1.0` sdist-only from Known Limitations)
    - Test 404 not-found case
    - _Requirements: R2.1, R2.2, R2.3, R2.9_

- [ ] 5. Checkpoint — R2 metadata recovery complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement R3 declared graph and R4 conflict detection — graph.py
  - [ ] 6.1 Implement declared graph builder with marker evaluation and Unknown status assignment
    - Implement `build_declared_graph(roots, metadata_lookup) -> DeclaredGraph` using `networkx.DiGraph`
    - R3.1: evaluate environment markers against the fixed `TARGET_ENV` (CPython 3.12, Linux x86_64) via `Marker.evaluate(env)`; display target environment in UI
    - R3.2: drop edges guarded by unrequested extras (P0 requests no extras; `extra == ""` evaluates False for non-empty extras)
    - R3.3: assign `NodeStatus` per node — UNKNOWN for unrecoverable/unpinned metadata; HEALTHY for pinned with recovered metadata and no conflicts/findings; CONFLICT and VULNERABLE set later
    - Recurse into pinned transitives; unpinned/Unknown transitives become leaf Unknown nodes
    - _Requirements: R3.1, R3.2, R3.3, R2.11_

  - [ ]* 6.2 Write property test P6: an Unknown node never receives a healthy status
    - **Property 6: An Unknown node never receives a healthy status** — for any node whose metadata is Unknown (unpinned, not found, unreachable, no wheel), status is UNKNOWN, never HEALTHY
    - **Validates: Requirements 1.6, 2.11, 3.3**
    - Generator: random graphs injecting each Unknown reason

  - [ ]* 6.3 Write property test P11: edge inclusion reflects the target environment
    - **Property 11: Edge inclusion reflects the target environment** — an edge is included iff its marker evaluates true against the fixed target environment and its extra (if any) was requested; unrequested extras are dropped
    - **Validates: Requirements 3.1, 3.2**
    - Generator: random edges with markers and extra guards

  - [ ] 6.4 Implement conflict detector using SpecifierSet.contains
    - Implement `detect_conflicts(graph: DeclaredGraph) -> list[Conflict]`
    - R4.1: for each edge `A -> B` with specifier `S`, if B is pinned to version `V` and `V` does not satisfy `S` (`not S.contains(V)`), create a `Conflict(requirer=A, required=B, specifier=S, pinned_version=V, evidence=edge.evidence)`
    - R4.2: conflict record emitted by graph.py; torn artery rendering is a frontend concern (task 12.2)
    - _Requirements: R4.1, R4.2_

  - [ ]* 6.5 Write property test P5: conflict detection agrees with reference specifier semantics
    - **Property 5: Conflict detection agrees with the reference specifier semantics** — conflict flagged iff `packaging.specifiers.SpecifierSet.contains(S, V)` is False; record carries requirer, required, specifier, pinned version, evidence
    - **Validates: Requirements 4.1**
    - Generator: random `(SpecifierSet, Version)` pairs

- [ ] 7. Checkpoint — Gate 1: R3/R4 declared graph and conflict detection complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement R5 vulnerability discovery — osv.py
  - [ ] 8.1 Implement OSV batch query, per-id details, alias dedup, severity derivation, and "no OSV record ≠ safe" label
    - Implement `query_vulnerabilities(packages, cache) -> OSVResult`
    - R5.1: build `querybatch` request with ≤1000 queries per batch; follow pagination; fetch per-id detail via `GET /v1/vulns/{id}`
    - R5.2: alias deduplication via union-find over all IDs (record id + aliases); `raw_count` = total records, `dedup_count` = connected components; every raw id maps to exactly one finding
    - R5.3: severity from `database_specific.severity` if present, else CVSS score mapped to LOW/MODERATE/HIGH/CRITICAL bands
    - R5.5: no severity and no CVSS → label `"severity unknown"`, never `"critical"`
    - R5.6: severity read only from `database_specific.severity` or CVSS; `severity_source` records which; no inference from other fields
    - R5.4: empty OSV result labeled "No known OSV records found — no OSV record does not mean safe", never "safe"
    - R2.8: OSV unreachable/timeout → vulnerability status Unknown with reason; caught in adapter, no exception propagates
    - _Requirements: R5.1, R5.2, R5.3, R5.4, R5.5, R5.6, R2.8, R2.10_

  - [ ]* 8.2 Write property test P8: OSV deduplication is sound and complete over aliases
    - **Property 8: OSV dedup count ≤ raw count, and every raw id maps to exactly one deduplicated finding** — records sharing any alias id collapse into one finding; no id is dropped or appears in two findings
    - **Validates: Requirements 5.2**
    - Generator: random OSV record sets with overlapping alias ids

  - [ ]* 8.3 Write property test P12: severity is derived only from documented fields with documented precedence
    - **Property 12: Severity derived only from documented fields** — `database_specific.severity` if present, else CVSS, else `"severity unknown"` (never `"critical"`); severity_source is one of exactly `database_specific.severity`, `cvss`, or `none`
    - **Validates: Requirements 5.3, 5.5, 5.6**
    - Generator: random records with/without `database_specific.severity` and CVSS

- [ ] 9. Checkpoint — R5 vulnerability discovery complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement R6 force remove — graph.py
  - [ ] 10.1 Implement force remove: highlight dependents, retain shared deps, mark incomplete on Unknown
    - Implement `force_remove(graph: DeclaredGraph, package: str) -> ForceRemoveResult`
    - R6.1: `impacted` = exactly the set of nodes with a direct edge to P (the dependents); highlight them
    - R6.2: remove only node P; retain every dependency still reachable from a remaining root (never orphan shared transitive deps)
    - R6.3: if any impacted dependent or node in P's subtree is Unknown → `incomplete = True` with list of unknown nodes
    - _Requirements: R6.1, R6.2, R6.3_

  - [ ]* 10.2 Write property test P3: force remove of P affects only packages with an edge to P
    - **Property 3: Force Remove of P affects only packages with an edge to P** — impacted set is exactly the direct dependents of P; no other node's membership changes
    - **Validates: Requirements 6.1**
    - Generator: random `networkx` DiGraphs; pick random node P

  - [ ]* 10.3 Write property test P4: removing one root never removes a dependency still required by another root
    - **Property 4: Removing one root never removes a dep still required by another root** — shared transitive dependencies are retained
    - **Validates: Requirements 6.2**
    - Generator: random graphs with shared transitive deps; remove a root

  - [ ]* 10.4 Write property test P13: force-remove impact is marked incomplete when Unknown nodes are involved
    - **Property 13: Force-remove impact marked incomplete when Unknown nodes involved** — incomplete iff at least one impacted dependent or node in P's subtree is Unknown
    - **Validates: Requirements 6.3**
    - Generator: random graphs with Unknown nodes in impact set

- [ ] 11. Checkpoint — R6 force remove complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement P0 API and frontend — main.py, templates, static
  - [ ] 12.1 Implement main.py P0 API routes and orchestration
    - `POST /api/patients`: accept multipart file or JSON text; call `validate_manifest`; create in-memory patient store; return patient_id, requirements, errors, rejected, summary
    - `GET /api/patients/{id}`: build declared graph (metadata + OSV), detect conflicts, serialize nodes/edges/conflicts/unknowns/vulnerabilities as JSON per the API design
    - `POST /api/patients/{id}/force-remove`: call `force_remove`; return impacted, retained_shared, incomplete, unknown_involved
    - Sample loader: serve `samples/legacy_flask_requests.txt` as a demo patient
    - In-memory patient store maps `patient_id -> DeclaredGraph` for session life only (no persistence)
    - _Requirements: R1.1–R1.6 (via validate), R2.1–R2.11 (via metadata), R3.1–R3.3, R4.1–R4.2, R5.1–R5.6, R6.1–R6.3_

  - [ ] 12.2 Implement Cytoscape.js graph rendering with data-driven visual classes and evidence drawer
    - Server-rendered HTML (Jinja2) with Cytoscape.js graph; no SPA framework
    - R9.1: map node status to CSS classes per the Visual Language table — `node-healthy` (calm pale organ), `node-conflict` (red artery), `node-vuln` (green infection glow, pulse speed from severity; unknown severity = grey, never "critical"), `node-unknown` (fog/mist, label "Unknown: no evidence")
    - R9.1: map edge types — `edge-conflict` (torn red artery), `edge-unknown` (dotted amber); overall state as heartbeat monitor
    - Evidence drawer: click/keyboard-activate node or edge → side drawer showing Evidence (source, url, fetched_at), Conflict details, Advisory/Finding records with severity and source; Unknown node shows `unknown_reason` and "Unknown: no evidence"; empty OSV shows "No known OSV records found — no OSV record does not mean safe" (R5.4)
    - Every CSS class derived from data fields; no visual state hard-coded
    - _Requirements: R9.1, R4.2, R5.4_

  - [ ] 12.3 Implement keyboard-only navigation, prefers-reduced-motion, and contrast
    - R9.3: graph container is focusable; Tab moves between nodes in document order; Enter/Space activates drawer; Escape closes; upload form, force-remove control, and drawer reachable without pointer; skip-to-graph link and visible focus rings
    - R9.2: `prefers-reduced-motion` media query disables pulse/heartbeat animations, replacing with static states that preserve information (severity via static glow color + text label; overall state via static icon); all text contrast ≥ 4.5:1 against charcoal background; status never conveyed by color alone (paired with text label/icon)
    - _Requirements: R9.2, R9.3_

  - [ ]* 12.4 Write end-to-end integration test with sample patient
    - Test `samples/legacy_flask_requests.txt` end-to-end: upload → validate → build graph → assert known conflict detected (`requests==2.19.0` requires `urllib3<1.24` vs pinned `urllib3==1.24.1`)
    - Assert graph + evidence render with correct status classes
    - _Requirements: R1.1–R1.6, R2.1–R2.4, R3.1–R3.3, R4.1–R4.2, R9.1_

- [ ] 13. Checkpoint — P0 complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. [P1 Optional] Implement R7 simulation engine — surgery/
  - [ ] 14.1 Implement surgery/operations.py: build edited manifest and exact line diff
    - Implement `build_edited_manifest(original, op) -> EditedManifest` for `remove_pin` (delete line), `set_pin` (replace specifier), `force_remove` (no manifest change)
    - Implement `compute_diff(original, edited) -> list[DiffLine]` with exact line-level diff (added/removed/unchanged, with line numbers)
    - R7.5: comparison view composes up to three Operation results side by side
    - _Requirements: R7.1, R7.5_

  - [ ] 14.2 Implement surgery/worker.py: isolated pip dry-run resolver
    - Implement `run_resolver(edited_manifest, timeout=60) -> ResolutionResult`
    - R7.2: run `pip install --dry-run --ignore-installed --only-binary=:all: --python-version 3.12 --platform manylinux2014_x86_64 --target <tmpdir> --report -` as subprocess with `shell=False`, cleared environment, fixed PyPI index, hard timeout
    - R7.3: on failure, extract resolver conflict message into `error`
    - R7.4: on success, return resolved versions, OSV before/after, and label "Constraints satisfied - runtime not tested"
    - Security: argument list built from parsed/allowlisted objects, never raw text; `--only-binary=:all:` prevents sdist execution; temp dir cleaned up; no secrets in logs
    - _Requirements: R7.2, R7.3, R7.4_

  - [ ]* 14.3 Write property test P7: operation diff application is exact
    - **Property 7: Operation diff application is exact** — applying the computed line diff to the original manifest yields the edited manifest exactly
    - **Validates: Requirements 7.1**
    - Generator: random operations and original manifests

  - [ ] 14.4 Implement P1 API endpoint: POST /api/patients/{id}/operations
    - Accept `Operation` request; call `build_edited_manifest` + `compute_diff` + `run_resolver`; return diff, resolution, osv_before, osv_after per the API design
    - _Requirements: R7.1–R7.5_

- [ ] 15. [P1 Optional] Implement R8 surgical report — report.py
  - [ ] 15.1 Implement report.py Markdown and JSON export
    - Implement `export_report(patient, operations) -> tuple[str, str]` returning (markdown, json)
    - R8.1: report contains every finding with its evidence and all unknowns; Markdown and JSON produced from the same `SurgeryReport` model so they cannot diverge
    - _Requirements: R8.1_

  - [ ] 15.2 Implement P1 API endpoints: GET /api/patients/{id}/report.md and /report.json
    - Return Markdown and JSON report respectively, per the API design
    - _Requirements: R8.1_

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; core implementation tasks are never optional
- Each task references specific requirements (R-IDs) and properties (P-IDs) for traceability
- Checkpoints ensure incremental validation between phases; the Gate 1 checkpoint (task 7) validates R3/R4 before proceeding to R5
- Property tests validate universal correctness properties (P1–P14) with Hypothesis; unit/integration tests validate specific examples and edge cases
- P1 tasks (14–15) are deferred and build on the P0 foundation; property P7 is P1-deferred because it depends on R7
- All external-service failures are caught in the adapter layer and converted to Unknown results (R2.10) — the system never crashes from an external failure
- The closed `NodeStatus` enum makes "Unknown as healthy" unrepresentable (R2.11, P6) — this is a structural guarantee, not a runtime check
- Integration tests use recorded golden fixtures (PyPI JSON, wheel METADATA, OSV responses) for reproducibility; property tests use mocked adapters for determinism

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "2.5", "2.6"] },
    { "id": 4, "tasks": ["3"] },
    { "id": 5, "tasks": ["4.1"] },
    { "id": 6, "tasks": ["4.2"] },
    { "id": 7, "tasks": ["4.3"] },
    { "id": 8, "tasks": ["4.4", "4.5"] },
    { "id": 9, "tasks": ["5"] },
    { "id": 10, "tasks": ["6.1"] },
    { "id": 11, "tasks": ["6.2", "6.3"] },
    { "id": 12, "tasks": ["6.4"] },
    { "id": 13, "tasks": ["6.5"] },
    { "id": 14, "tasks": ["7"] },
    { "id": 15, "tasks": ["8.1"] },
    { "id": 16, "tasks": ["8.2", "8.3"] },
    { "id": 17, "tasks": ["9"] },
    { "id": 18, "tasks": ["10.1"] },
    { "id": 19, "tasks": ["10.2", "10.3", "10.4"] },
    { "id": 20, "tasks": ["11"] },
    { "id": 21, "tasks": ["12.1"] },
    { "id": 22, "tasks": ["12.2"] },
    { "id": 23, "tasks": ["12.3"] },
    { "id": 24, "tasks": ["12.4"] },
    { "id": 25, "tasks": ["13"] },
    { "id": 26, "tasks": ["14.1"] },
    { "id": 27, "tasks": ["14.2", "14.3"] },
    { "id": 28, "tasks": ["14.4", "15.1"] },
    { "id": 29, "tasks": ["15.2"] }
  ]
}
```
