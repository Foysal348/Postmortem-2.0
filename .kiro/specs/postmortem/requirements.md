# Requirements Document

## Introduction

PostMortem 2.0 is an interactive **dependency surgery lab** for Python projects, presented as a gothic autopsy table. Built for the Kiroween 2026 hackathon Costume Contest category, it helps developers who inherit legacy Python projects diagnose version conflicts and known vulnerabilities, simulate dependency operations before editing the repo, and export a surgical report.

The system follows four non-negotiable principles:

1. **Evidence over assumptions.** Every claim shows its source (PyPI JSON, wheel METADATA, OSV record id, pip report).
2. **Simulation over promises.** A resolver success means constraints are satisfiable, never "your app will run".
3. **Unknown is never green.** Missing metadata is shown as unknown fog, never as healthy.
4. **Decoration serves decision.** Every visual effect encodes data (severity, conflict, uncertainty).

This document specifies the **P0 (must-ship) scope** for the initial build (R1-R6, R9). **R7 (Simulation)** and **R8 (Surgical Report)** are P1 requirements, recorded here so tests and tasks can reference them, but deferred to separate later tasks and NOT part of the initial build. **P2 items** (GitHub URL scanning, npm, automatic code fixing, accounts, AI chat) are out of scope.

Requirements use EARS patterns and carry stable IDs (R1.x through R9.x) referenced by tests and tasks. Correctness properties P1-P8 are validated with property-based tests (Hypothesis).

## Glossary

The glossary includes the strict definitions from the product brief, because these terms determine requirement semantics.

- **PostMortem System**: The application described by this spec — the interactive dependency surgery lab. All EARS requirements are directed at this system.
- **Declared graph**: A dependency graph built from the manifest plus package metadata. May be partial or contradictory.
- **Resolved graph**: One package selection that pip accepted for a recorded target environment. Not proof the app runs.
- **Remove Pin**: An operation that deletes a manifest line and re-resolves; the package may come back transitively.
- **Force Remove**: A hypothetical removal of a package from a graph; shows which packages declare it as a requirement.
- **Constraint pass**: A resolver success only.
- **Unknown**: No reliable metadata or evidence available for a node or edge.
- **Unpinned**: A requirement line whose specifier is not an exact pin (`==`), for example `>=1.0`, `~=2.0`, `<3`, or a bare package name. In P0 its version is not determined and the node is treated as Unknown.
- **Known OSV finding**: An OSV record that matches a specific package and version. Not proof of exploitability.
- **Time since last release**: A date interval since the package's last release. Not proof of abandonment.
- **Manifest**: The uploaded requirements file, restricted to a narrow PEP 508 subset.
- **PEP 508**: The Python requirement specification standard. PostMortem accepts only the `name[extras] specifier [; marker]` subset.
- **PEP 503**: The distribution-name normalization standard (for example, `Flask`, `flask` and `FLASK` are one package).
- **Wheel METADATA**: The `.dist-info/METADATA` file inside a wheel, read for `Requires-Dist`; the package is never executed.
- **Target environment**: The single recorded environment that markers are evaluated against — CPython 3.12, Linux x86_64.
- **Environment markers**: PEP 508 markers evaluated against the target environment to include or exclude requirements.
- **Extras**: Optional dependency groups in PEP 508. Requirements guarded by unrequested extras are dropped.
- **OSV**: The Open Source Vulnerabilities database, queried in batch with per-id detail fetches.
- **Alias deduplication**: Collapsing OSV records that are aliases of the same underlying advisory.
- **Evidence**: The recorded source and URL for every dependency edge or finding. Sources are one of `pypi-json`, `wheel-metadata`, `osv`, `pip-report`, or `unknown`.
- **Operation**: A dependency change the user simulates: `remove_pin`, `force_remove`, or `set_pin`.
- **Conflict**: A situation where a pinned version violates another package's specifier.
- **Root**: A package named directly in the manifest (as opposed to a transitive dependency).

## Visual Language

R9.1 depends on this table; every visual effect encodes a data value.

| Data | Visual |
|---|---|
| Healthy, no findings | calm pale organ |
| Behind latest release | greyish, faded |
| Long time since last release | darkened, dust (label says "no release for N years", never "dead") |
| Known OSV finding | green infection glow; pulse speed by severity; unknown severity = grey glow, never "critical" |
| Version conflict | torn red artery between two organs |
| Unknown metadata | fog / mist over the organ, label "Unknown: no evidence" |
| Overall state | heartbeat monitor at the top |
| Successful simulation | "The patient survives" + calm heartbeat (only when the resolver actually succeeded) |

The UI must respect `prefers-reduced-motion` and keep text contrast at or above 4.5:1.

## Requirements

**Scope legend:** Requirements R1-R6, R9 are **P0 (initial build)**. Requirements R7 (Simulation) and R8 (Surgical Report) are **P1, deferred to separate later tasks** and are NOT part of the initial P0 build. Numeric order is preserved (R1 = Requirement 1 ... R9 = Requirement 9) so existing IDs referenced by tests and tasks are unchanged.

### Requirement 1: Input Validation (R1)

**Scope:** P0 — Initial build

**User Story:** As a Python developer inheriting a legacy project, I want my requirements file validated against a strict PEP 508 subset, so that unsupported or dangerous constructs are rejected before any metadata is fetched.

#### Acceptance Criteria

- **R1.1** WHEN a user uploads a requirements file, THE PostMortem System SHALL accept only lines of the form `name[extras] specifier [; marker]` together with comments and blank lines.
- **R1.2** IF a line contains `-r`, `-c`, `-e`, a `--` option, a URL, a VCS reference, or a local path, THEN THE PostMortem System SHALL reject the file and name the offending line.
- **R1.3** IF the file exceeds 64 KB or 200 requirement lines, THEN THE PostMortem System SHALL reject the file.
- **R1.4** THE PostMortem System SHALL normalize distribution names per PEP 503, so that `Flask`, `flask` and `FLASK` refer to one package.
- **R1.5** IF the same package appears more than once in the file, THEN THE PostMortem System SHALL report a duplicate error.
- **R1.6** IF a requirement is not an exact pin (`==`), THEN THE PostMortem System SHALL mark the node as "Unpinned: version not determined" with an Unknown status.

### Requirement 2: Metadata Recovery (R2)

**Scope:** P0 — Initial build

**User Story:** As a maintainer, I want dependency metadata recovered from authoritative sources with a clear fallback, so that I know where each dependency edge came from and can see when evidence is missing.

#### Acceptance Criteria

- **R2.1** WHEN analysing a pinned `name==version` requirement, THE PostMortem System SHALL read `requires_dist` from the PyPI release JSON.
- **R2.2** IF `requires_dist` is missing from the PyPI JSON, THEN THE PostMortem System SHALL read `Requires-Dist` from the wheel `.dist-info/METADATA` without executing any package code.
- **R2.3** IF no wheel exists, THEN THE PostMortem System SHALL mark the package's dependencies as Unknown.
- **R2.4** THE PostMortem System SHALL record the evidence source of every dependency edge as one of `pypi-json`, `wheel-metadata`, or `unknown`.
- **R2.5** THE PostMortem System SHALL cache metadata and OSV responses.
- **R2.6** WHERE a node is Unpinned, THE PostMortem System SHALL skip metadata and OSV fetching in the P0 scope.
- **R2.7** IF PyPI is unreachable or times out, THEN THE PostMortem System SHALL mark the affected node as Unknown and display the reason (for example "PyPI unreachable" or "PyPI timeout").
- **R2.8** IF OSV is unreachable or times out, THEN THE PostMortem System SHALL mark the vulnerability status as Unknown and display the reason.
- **R2.9** IF a package or version does not exist on PyPI, THEN THE PostMortem System SHALL mark the node as Unknown with the reason "not found on PyPI".
- **R2.10** IF any external-service failure occurs, THEN THE PostMortem System SHALL continue operating without crashing.
- **R2.11** THE PostMortem System SHALL never display an Unknown node with a healthy status.

### Requirement 3: Declared Graph (R3)

**Scope:** P0 — Initial build

**User Story:** As a developer, I want a dependency graph evaluated for one fixed target environment, so that the graph reflects what would actually be installed there rather than every possible environment.

#### Acceptance Criteria

- **R3.1** THE PostMortem System SHALL evaluate environment markers against one recorded target environment (CPython 3.12, Linux x86_64) and display that environment in the UI.
- **R3.2** THE PostMortem System SHALL drop requirements guarded by extras that were not requested.
- **R3.3** THE PostMortem System SHALL assign every Unknown node a status distinct from the healthy status.

### Requirement 4: Conflict Detection (R4)

**Scope:** P0 — Initial build

**User Story:** As a developer, I want version conflicts detected and visualized, so that I can find the exact dependency path causing a resolution failure.

#### Acceptance Criteria

- **R4.1** WHEN a pinned version does not satisfy another package's specifier, THE PostMortem System SHALL create a conflict recording both packages, the specifier, the pinned version, and the evidence source.
- **R4.2** THE PostMortem System SHALL render each conflict as a torn artery between the two organs.

### Requirement 5: Vulnerability Discovery (R5)

**Scope:** P0 — Initial build

**User Story:** As a maintainer, I want known vulnerabilities surfaced from OSV with raw and deduplicated counts, so that I am not misled by duplicate advisories or by missing severity.

#### Acceptance Criteria

- **R5.1** THE PostMortem System SHALL query OSV in batch and fetch details per record id.
- **R5.2** THE PostMortem System SHALL display the raw OSV record count and the count after alias deduplication.
- **R5.3** THE PostMortem System SHALL derive the severity label from the OSV record's `database_specific.severity` field, or from a CVSS score if present.
- **R5.4** THE PostMortem System SHALL state that "no OSV record" does not mean "safe".
- **R5.5** IF neither `database_specific.severity` nor a CVSS score is present, THEN THE PostMortem System SHALL label the finding "severity unknown" rather than critical.
- **R5.6** THE PostMortem System SHALL NOT guess or infer severity from any other field.

### Requirement 6: Force Remove (R6)

**Scope:** P0 — Initial build

**User Story:** As a developer considering removing a dependency, I want to see what depends on it, so that I can judge the blast radius before editing the manifest.

#### Acceptance Criteria

- **R6.1** WHEN the user force-removes package P, THE PostMortem System SHALL highlight every package that declares P as a requirement.
- **R6.2** THE PostMortem System SHALL retain shared dependencies that other roots still require after a Force Remove of P.
- **R6.3** THE PostMortem System SHALL mark Force Remove impact as incomplete where Unknown nodes are involved.

---

> **P1 — Deferred to separate later tasks.** The requirements below (R7 and R8) are recorded here so tests and tasks can reference them, but they are NOT part of the initial P0 build. Release-age labels are likewise P1/deferred.

### Requirement 7: Simulation (R7)

**Scope:** P1 — Deferred (separate later task; NOT part of the initial build)

**User Story:** As a developer, I want to simulate a dependency change in an isolated resolver before touching my repo, so that I can see the exact manifest diff and resolver outcome safely.

#### Acceptance Criteria

- **R7.1** WHEN the user runs an operation, THE PostMortem System SHALL build the edited manifest and show the exact line diff.
- **R7.2** THE PostMortem System SHALL run the resolver only in an isolated worker using only binary distributions, a fixed target environment, no installation, and a timeout.
- **R7.3** IF the resolver fails, THEN THE PostMortem System SHALL display the resolver's conflict message.
- **R7.4** WHEN the resolver succeeds, THE PostMortem System SHALL display resolved versions, OSV findings before versus after, and the label "Constraints satisfied - runtime not tested".
- **R7.5** THE PostMortem System SHALL compare up to three candidate operations side by side.

### Requirement 8: Surgical Report (R8)

**Scope:** P1 — Deferred (separate later task; NOT part of the initial build)

**User Story:** As a developer, I want to export a report of every finding with its evidence and unknowns, so that I can share the diagnosis with my team.

#### Acceptance Criteria

- **R8.1** THE PostMortem System SHALL export a Markdown and JSON report containing every finding, its evidence, and all unknowns.

---

> **P0 resumes below.** R9 is part of the initial P0 build.

### Requirement 9: UI and Accessibility (R9)

**Scope:** P0 — Initial build

**User Story:** As a developer and as a contest judge, I want the gothic autopsy UI to encode data in every visual effect while remaining usable, so that the decoration aids decisions and stays accessible.

#### Acceptance Criteria

- **R9.1** THE PostMortem System SHALL encode every visual effect from data, following the Visual Language table above.
- **R9.2** THE PostMortem System SHALL respect `prefers-reduced-motion` and keep text contrast at or above 4.5:1.
- **R9.3** THE PostMortem System SHALL be fully operable with keyboard only.

## Correctness Properties (Property-Based Tests)

The following properties are validated with Hypothesis. Property IDs P1-P8 are referenced by tests and tasks and are kept verbatim from the requirements draft.

- **P1** Name normalization is idempotent: `norm(norm(x)) == norm(x)`.
- **P2** Validator never accepts a line containing a URL, path, or pip option.
- **P3** For any generated graph, Force Remove of P affects only packages with an edge to P.
- **P4** Removing one root never removes a dependency still required by another root.
- **P5** Conflict detector agrees with `packaging.SpecifierSet.contains` for random versions/specifiers.
- **P6** An Unknown node never receives a "healthy" status.
- **P7** For any operation, applying the diff to the original manifest yields the edited manifest exactly. **Scope: P1 — Deferred (depends on R7)**
- **P8** OSV dedup count ≤ raw count, and every raw id maps to exactly one deduplicated finding.

## Scope Boundaries

- **Out of scope (P2):** GitHub URL scanning, npm, automatic code fixing, accounts, AI chat.
- **P1 deferred (not part of initial build):** R7 Simulation; R8 Surgical Report; release-age labels; property P7 (depends on R7).
- **Known limitations:**
  - Some old packages are sdist-only (for example markupsafe 1.0, itsdangerous 0.24), so their dependencies are Unknown.
  - flask 0.12.2 has empty `requires_dist` in PyPI JSON but its wheel METADATA has them, so the fallback works.
  - Any "after" scenario must state exactly which lines changed.
