# POSTMORTEM 3.0 — Evidence-Backed Interactive Dependency Surgery

**Research & build blueprint | 23 November 2026 | Kiroween 2026 | Costume Contest | Solo Python developer | Deadline: 4 December 2026, 22:00 UTC**

> Status: This is a research-backed design and implementation plan, NOT a claim that the listed application features have been built or that the user's reported experiments were independently rerun. Reports of four successful tests came from the user; original logs and code have not yet been independently inspected.

## 1. Executive recommendation

Build one complete Python-only-ecosystem product, **PostMortem — Interactive Dependency Surgery Lab**. It must explain *why* dependencies conflict, allow controlled counterfactual edits, show *what changed*, preserve uncertainty, and generate an evidence-backed report. The distinct experience is a gothic operating theatre, not a dark-themed ordinary vulnerability scanner.

**Key message:** “Don't just scan your dependencies. Perform surgery before changing your code.”

**Novelty positioning:** The individual components (vulnerability scans, dependency graph, upgrade advice, package health) exist elsewhere. Claim the **integrated, evidence-first decision and interactive surgical explanation**, not a world-first algorithm or automatic proof of runtime safety.

## 2. Prior art reviewed

- Kiroween 2025 **Pack-Man**: Multi-ecosystem dependency analyzer: https://devpost.com/software/pack-man-ix09ma
- Kiroween 2025 **Necromancer**: dependency decay score and resurrection paths: https://devpost.com/software/necromancer-sb2ui8
- Kiroween 2025 **NECRO**: dependency health visualization: https://devpost.com/software/necro
- Kiroween 2025 **GhostOps**: haunted repository security scanning: https://devpost.com/software/ghostops
- **pip-audit**: Python vulnerability auditing: https://github.com/pypa/pip-audit
- **pipdeptree**: installed dependency tree, reverse lookup, conflicts: https://pipdeptree.readthedocs.io/en/latest/
- **GitHub Dependency Review**: diff of dependency changes / vulnerabilities: https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review
- **Snyk Breakability Analysis**: upgrade risk: https://updates.snyk.io/merge-with-confidence-introducing-breakability-analysis-for-pull-requests/
- **OWASP Dependency-Track**: software supply chain monitoring: https://owasp.org/projects/dependency-track

**Differentiation hypothesis (not proven absence of prior art):** A compelling user-controlled “surgery theatre” that preserves exact manifest diffs, compares 2–3 viable candidates, shows reason/evidence for constraint conflicts, and renders uncertainty explicitly could stand apart from simple scanner-style hackathon entries.

## 3. Product thesis and target audience

**User:** Python developers inheriting a legacy project; student maintainers; small open-source teams with dependency conflicts and known vulnerable versions.

**Job:** “Before touching my repository, explain which declared package constraints conflict, let me try a small change, show the exact dependency-resolution result and any OSV findings, and tell me what remains unknown.”

**Main user journey:** Upload supported requirements -> inspect patient -> tap conflicting vein -> open evidence -> choose operation -> run bounded simulation -> see surgical timeline/diff -> compare proposals -> export report. No user account needed.

## 4. Rules and constraints

Official rules: https://kiroween.devpost.com/rules
- One working app using Kiro; Costume Contest UI must enhance function.
- Submit a working app URL, public GitHub with recognizable open-source license, root `.kiro/` folder, public YouTube demo UNDER 3 minutes, documentation, eligible student details to pursue category student award.
- New work within event period, disclose pre-existing resources. No promise of winning.
- Project deadline: Dec 4 at 22:00 UTC. Kiro credits request deadline: Dec 1 at noon Pacific time (check Resources).

## 5. Strict definitions (these prevent misleading claims)

1. **Declared graph**: manifest + package metadata-derived dependency claims; can be partial or contradictory. This is not an installed environment.
2. **Resolved graph**: one candidate package selection that pip accepted for the explicitly recorded target environment, not proof app runs.
3. **Installed graph**: actual environment inspection via `pip inspect`; optional, *not inferred* from declared or resolved data.
4. **Remove Pin**: delete a line from the manifest and re-resolve; package may still be selected transitively.
5. **Force Remove**: hypothetical removal from a *given resolved graph*, displaying dependent packages that require it; not a prediction of app crash.
6. **Constraint pass**: resolver success only, not guaranteed functional, secure, or supported application.
7. **Unknown**: lack of reliable metadata / evidence; never automatically green.
8. **Known OSV finding**: a vulnerability record associated with a specific package-version; not necessarily remotely exploitable in this app.
9. **Time since last release**: observable date interval, not proof of abandonment.

## 6. Recommended MVP features / priority

### P0 — Must ship
- Strict input validator for simple pinned and bounded PEP 508 requirements (choose a narrow documented grammar). Reject `-r/-c`, `--index-url`, `--extra-index-url`, direct URL, Git/VCS, local paths, editable install, arbitrary pip switches, unbounded file size. Normalize distribution names with `packaging`.
- Version-specific metadata provider: PyPI JSON -> core `.metadata` sidecar or bounded wheel `.dist-info/METADATA` -> optional safe static sdist `PKG-INFO` if reliable -> Unknown. Preserve source URL, retrieval timestamp, selected artifact hash.
- **Evidence-first declared dependency graph** with edge provenance and marker/extras evaluation; incomplete edges cannot be treated as absent.
- **OSV querybatch** for exact versions: handle per-query result mapping, pagination and fetch detail as needed; avoid counting duplicate/alias advisories as independent confirmed security issues; show source links.
- **Preoperative findings**: conflicts, transitive paths, missing evidence, release gap. On inconsistent manifest show Declared Graph only; do NOT show it as 'installed before'.
- **Operation 1 — Remove Pin**, changes manifest and re-resolves; may still include the target package through other requirements.
- **Operation 2 — Force Remove**, predicts which *declared requirements* depend on a missing package, explicitly ‘hypothetical / missing dependency’, never predicts guaranteed crashes.
- **Operation 3 — Change Pin / Upgrade Candidate**, bounded pip resolver in isolated worker; report exact manifest diff and result.
- **Surgical timeline**: original file -> problem -> candidate operation -> resolver evidence -> after status/unknowns. Export JSON/HTML report.
- Polished dark, anatomical interface with keyboard accessibility, labeled findings, reduced-motion option and color-independent statuses.
- Kiro spec-driven workflow, evidence-oriented custom agent/steering, hook-triggered tests, property-based invariant tests, and before/after development logs.

### P1 — Only after P0 stability
- **Minimum-Change Surgery**: compare 2–3 permitted candidates from a bounded selection (e.g., modify one root pin, then add a second edit). Criteria: direct edits, total resolved version changes, distinct known OSV findings, unknown evidence count. Never equate fewer edits with safety.
- A two-column comparative timeline with a diff of resolved candidate package sets.
- Curated reproducible case study and snapshot mode for reliable demo with clearly dated data.
- Limited CycloneDX SBOM export, only if accurate and quick.

### Excluded for the 11-day MVP
- Automatic code repair, code execution of target repositories, GitHub PR submission, npm, full AI remediation, automatic CVE exploitability, unrestricted user-provided pip execution, claims of zero risk, claims of universal upgrade-safety proof.

## 7. Core edge cases to get correct

| Case | Correct behavior |
|---|---|
| `requests==2.19.0` with `urllib3==1.24.1` | Show declared-version conflict (requests requires urllib3 <1.24). |
| Upgrade `requests` while retaining urllib3 pin | Show exact line diff and re-resolver output. Do not silently change urllib3 pin. |
| After report shows `urllib3==2.8.0` | Require explicit removed/changed urllib3 pin in the recorded surgery; changing requests alone cannot override a retained exact urllib3 pin. |
| Remove urllib3 line but requests still requires it | Resolver can bring urllib3 back as transitive dependency; don't label 'dead'. |
| Force remove urllib3 from a resolved graph | Label requests as structurally missing a required dependency; actual runtime effects unknown. |
| Two top-level packages use same shared dependency | Removing one root must not orphan the still-required shared dependency. |
| Baseline is ResolutionImpossible | Before graph is declared/inconsistent, not installed/resolved. Valid candidate is a new resolved graph, not before/after of two resolved states. |
| `Requires-Dist` absent in legacy metadata | Unknown / incomplete, unless independent reliable artifact data resolves it. |
| No OSV matches | ‘No known matches in current consulted data’, never ‘secure’. |
| `extra` or `python_version` markers | Apply to stated target environment / extras; otherwise show conditional status. |
| Only sdist available | Never execute setup.py/build hooks in public service; show limited static metadata or Unknown. |
| Wheel only supports other Python ABI/platform | Not installable for target; not necessarily a broken package. |
| Vulnerability has aliases or withdrawn record | Deduplicate cautiously, retain raw IDs, record exclusions and reason. |
| Multiple candidate operations | Explicit comparison baseline, versions, source date, resolver output, and unknowns. |

## 8. Architecture and data contracts

```text
Browser: Anatomical UI / Cytoscape.js graph / timeline / evidence drawer
       | HTTPS (strict file size/timeout and rate caps)
       v
FastAPI app: input validation -> case management -> analysis orchestrator
       |               |                  |
       v               v                  v
Metadata adapter    OSV adapter       Surgery engine
 PyPI & wheels       OSV querybatch     declared graph + changes
       |               |                  |
       +------- Evidence ledger <----------+
                       |
              Resolver interface (isolated bounded worker)
                       |
              pip dry-run JSON report
                       |
              snapshots / result comparisons
```

**Stack:** Python 3.12 (or selected locked version), FastAPI, Pydantic, `packaging`, `httpx`, NetworkX (graph reasoning), SQLite or in-memory cache, `pytest`, Hypothesis, Cytoscape.js with simple HTML/CSS and minimal vanilla JS. Avoid elaborate React architecture unless already comfortable with it. Use local bundles and accessible controls.

**API sketch:**
- `POST /api/cases` (manifest text; returns case + parsed requirements / unsupported entries)
- `GET /api/cases/{id}/graph` (declared graph and evidence statuses)
- `GET /api/cases/{id}/findings` (OSV + known constraints)
- `POST /api/cases/{id}/operations` (remove-pin / force-remove / change-pin)
- `GET /api/cases/{id}/operations/{opid}` (report, diff, status, evidence)
- `GET /api/cases/{id}/export` (signed? no; dated noncryptographic evidence JSON)

**Data model fields:**
- Case: input_hash, created_at, target_python, target_platform, selected_extras, resolver_version, snapshot_time, original_manifest
- Package: canonical_name, requested_spec, resolved_version?, top_level, metadata_status, metadata_source, sha256?, release_last_seen?
- Edge: parent, child, specifier, marker, marker_applies?, evidence_source, confidence_status
- Advisory: osv_id, aliases, modified_at, affected_package_version, severity_if_supplied, url
- Operation: type, edited_manifest, exact_text_diff, resolver_exit_status, resolver_stdout_stderr_redacted, resolver_report?, changed_packages, unresolved_items
- Report: original_case, operation, before_declared_graph, before_resolved_graph_if_any, after_resolved_graph_if_any, uncertainty, timestamp

**Graph orientation:** `A -> B` means A requires B. `reverse-reachable(B)` gives potential dependents. “Orphans after removing a root” are nodes unreachable from the remaining roots in that graph, not necessarily uninstalled packages. Preserve whether edges are complete; `not found` is not `not required`.

## 9. Resolver safety design

- `--dry-run --ignore-installed --report` is the official pip resolution mechanism. Prefer `--only-binary=:all:` and lock the target environment parameters. See https://pip.pypa.io/en/stable/cli/pip_install/ and https://pip.pypa.io/en/stable/reference/installation-report/
- **Important:** `--dry-run` is not a sandbox. Wheel-only avoids executing source-build hooks, but a pip process still downloads/parses untrusted archives; bound downloads, decompression, memory, CPU, file system and duration.
- Build the pip command from *parsed allowlisted requirement objects*, never concatenate raw uploaded lines into shell strings. Use argument list, `shell=False`, fixed PyPI index, cleared environment, non-root identity, quotas, timeout, read-only root where possible, private temp directory, and egress restrictions compatible with PyPI as supported.
- Ideally a separate ephemeral container/VM worker. A second process within the web container is not a strong isolation boundary. If secure isolation is not feasible for free deployment: allow unrestricted **static metadata analysis** on validated inputs, and expose full resolver simulation only for a fixed curated set of demo cases on the hosted app. Offer local container setup for full simulation; clearly label snapshot vs live.
- Never execute arbitrary uploaded project code or package tests in a shared server.
- Set sensible P0 quotas: upload <=64 KiB; <=50 pinned top-level packages; <=200 graph nodes; <=2 candidate operations per live case; candidate timeout 20s per operation. These are proposed defaults, not measured capacities.

## 10. EARS-style acceptance requirements

- **R-01** WHEN a user uploads an allowed requirements file, THE system SHALL parse and normalize each supported requirement while separately reporting any rejected entries.
- **R-02** WHEN metadata for a dependency edge is unavailable, THE system SHALL mark the edge status incomplete and SHALL NOT assert absence of the dependency.
- **R-03** WHEN two exact top-level pins violate an active dependency specifier, THE system SHALL show the conflicting packages, exact specifier, and source evidence.
- **R-04** WHEN the user requests Remove Pin, THE system SHALL re-resolve the edited manifest and SHALL NOT assume the package disappeared from the candidate selection.
- **R-05** WHEN the user requests Force Remove, THE system SHALL identify graph dependents and SHALL label output hypothetical rather than confirmed runtime breakage.
- **R-06** WHEN a resolver attempt fails, THE system SHALL show unsuccessful resolution and SHALL NOT produce an after-resolved graph.
- **R-07** WHEN a resolver attempt succeeds, THE system SHALL preserve exact manifest edits, pip version, environment and selected package versions.
- **R-08** WHEN an OSV query returns no records, THE system SHALL say ‘No known matches found in the consulted OSV data’ rather than ‘Safe’.
- **R-09** WHEN the baseline is inconsistent, THE system SHALL call it a Declared Graph and SHALL NOT claim a previous successfully installed environment.
- **R-10** WHEN two users upload equivalent canonical requirements, THE system SHALL generate an equivalent normalized requirement set, independent of superficial package-name casing/hyphen differences.
- **R-11** WHEN the interface presents a finding, THE system SHALL offer a source-evidence drawer or an explicit Unknown marker.
- **R-12** WHEN a user chooses reduced motion, THE interface SHALL suppress major surgical movement without losing information.

## 11. Correctness and benchmark tests

Unit + property-based tests with `pytest` + Hypothesis:
- Canonical name equivalence, allowed grammar, rejection of untrusted pip options.
- Edge direction & reverse reachability and shared-root reachability.
- Unknown never promoted to verified; no source no edge assertion.
- Remove Pin vs Force Remove invariant for retained transitive requirements.
- Deterministic graph construction under the same fixed captured metadata and target environment; do not claim live online queries are deterministic over time.
- Matching candidate result to its *exact* manifest diff, not a different surgery.
- Dedupe aliases without silently dropping raw advisory evidence.
- Correct handling of `python_version` markers and extras.
- Snapshot mode reproducibility: store input hash, provider response fixtures, interpreter/pip version, dated results.

**Suggested benchmark design (future tests; no numbers pre-claimed):**
- 3 curated case suites: (A) satisfiable modern pins, (B) 2018-era declared conflict, (C) incomplete legacy metadata.
- Golden fixtures with independent expected conflict and edge evidence.
- Measure API latency, parsed package coverage, unknown cases, resolution success/failure classification and repeatability of same snapshot.
- Establish target acceptance gates: 100% fixture regression pass; zero wrong 'runtime verified' labels; no executed sdist builds; all supported findings have provenance. Do not use performance claims without actual recordings.

## 12. Visual design brief: make the visual metaphor functional

**Screen 1 — Admission:** Patient ID, `requirements.txt` drop-zone, predefined sample button, Python target environment, progress stages.

**Screen 2 — Autopsy:** Main anatomical graph with packages as stylized organs, glowing blood-red constraint edges, dotted amber unknown links, infected vulnerability glyphs. Selecting an organ opens exact version/edge/advisory evidence. Provide text fallback and keyboard navigation.

**Screen 3 — Operating Theatre:** Single selected intervention; side-by-side comparison with source diff in the middle; surgery button; bounded live or snapshot resolution; outcome label must be one of `RESOLVED_CONSTRAINTS`, `CONFLICT`, `INCOMPLETE`, `UNAVAILABLE`, `TIMEOUT` (never just ‘safe’).

**Screen 4 — Surgical Decision Lab:** Two candidate intervention cards: `minimum direct edits` vs `broader vulnerability reduction`. Show exact count of changed direct pins and selected candidate versions; reveal trade-offs. Never promise that one is universally safe.

**Screen 5 — Discharge:** `Resolution succeeded, runtime compatibility unverified` with downloadable plain report and links to PyPI/OSV evidence.

**Typography/theme:** near-black charcoal background, clinical ivory primary text, muted burgundy for conflict, violet for proposed intervention, blue/cyan for evidence provenance, gray fog for unknown, restrained green for verified resolver success. Avoid red/green alone; large accessible tap targets, contrast, reduced motion and responsive desktop-first layout.

## 13. 11-day implementation schedule (Nov 24 – Dec 4, 2026)

| Date | Build | Exit gate |
|---|---|---|
| Nov 24 | Final EARS spec + source schemas + exact fixtures + scaffold | Spec traceability done; app runs locally |
| Nov 25 | Restricted input parser, metadata adapters, provenance ledger | Can parse/sample 11-packages and mark unknown truthfully |
| Nov 26 | Graph engine + conflict diagnostics + unit/PBT | Known conflict and shared-root tests pass |
| Nov 27 | OSV adapter, dedup/status/snapshot, evidence drawer | Every displayed finding has source |
| Nov 28 | Surgery engine: Remove Pin vs Force Remove | Correctly different outcomes; no fabricated crash |
| Nov 29 | Bounded isolated pip resolver + before/after reports | Exact pip result linked to exact manifest diff |
| Nov 30 | Gothic UI, dependency anatomy interaction, responsive flows | Complete user journey on curated case |
| Dec 1 | 2-operation decision lab, Kiro workflow evidence; credit request by deadline | Two candidates accurately compared, Kiro receipts available |
| Dec 2 | Hosting hardening, limits/security, public live app, sample snapshot fallback | Judges can open working URL and reproduce |
| Dec 3 | Regression, visual polish, docs, GitHub license, 2:45 demo filming | Candidate release freeze |
| Dec 4 | Final submission checks and submit ahead of 22:00 UTC | Devpost entry done, YouTube public, URL tests pass |

**Early kill gates:** Day 3 no correct graph -> cut decision lab. Day 6 safe resolver missing -> keep metadata/graph simulation, expose curated verified fixtures as snapshot only and clearly disclose limitations. Day 9 hosted availability weak -> prefer robust static backed demonstration and local reproducible Docker instructions; never falsely claim full public untrusted live resolver support.

## 14. Three-minute video storyboard (target 2:45)

- 0:00–0:15: Real developer pain: old Python requirements conflict, security updates hard to judge.
- 0:15–0:35: Drop validated 2018 sample; anatomical patient appears.
- 0:35–1:05: Click red edge showing source: `requests==2.19.0` requires `urllib3<1.24`; exact pin `urllib3==1.24.1` violates it.
- 1:05–1:25: Explain remove pin vs force remove using one click; show why inferred outcomes differ.
- 1:25–2:00: Candidate A vs B surgery; show exact manifest diff, isolated pip dry-run, constraints succeed/fail, updated graph.
- 2:00–2:22: Reveal uncertain legacy package as fog; OSV evidence and safe wording `runtime not tested`.
- 2:22–2:38: Kiro specs, hook-triggered tests, property-based failing counterexample and fix (only if actual evidence exists).
- 2:38–2:45: Closing product line and real audience.

No dramatic animation should imply runtime safety. Showcase the truthfulness of Unknown as a differentiator, not a limitation to hide.

## 15. Kiro development organization

```text
.kiro/
  steering/
    product.md           # users, scope, no invented claims
    tech.md              # Python architecture, immutable evidence, supported inputs
    design.md            # gothic design, legibility, accessibility
    safety.md            # no untrusted code execution; no 'safe' labels
  specs/postmortem/
    requirements.md      # EARS requirements with IDs
    design.md            # data flow, models, contracts, failure taxonomy
    tasks.md             # chronological, test-gated task list
  hooks/
    test-on-save.json    # run focused deterministic test command
    validate-spec.json   # ensure references/requirements consistency
  agents/
    evidence-auditor.*   # optional, scoped checker; use supported current Kiro format
  settings/ (only if needed, use current Kiro docs)
```

**Important Kiro distinction:** agent hooks run development/workflow events, not application's production runtime scheduler. Use Kiro specs and Kiro correctness to produce genuine tests. See https://kiro.dev/docs/specs/, https://kiro.dev/docs/specs/correctness/, https://kiro.dev/docs/hooks/, https://kiro.dev/docs/custom-agents/ .

**Illustrative current hook JSON:**

```json
{
  "version": "v1",
  "hooks": [{
    "name": "Focused Python tests after save",
    "trigger": "PostFileSave",
    "matcher": "\\.py$",
    "action": {"type": "command", "command": "python -m pytest -q tests/unit tests/property"},
    "timeout": 45
  }]
}
```

Check Kiro version and run the hook manually during setup; avoid hook recursion / slow tests.

## 16. Hosting/budget and contest packaging

**API/data:** PyPI JSON (public), official wheel metadata, OSV API (currently no published rate cap, but cache fairly), no mandatory paid LLM. Sources: https://docs.pypi.org/api/json/, https://google.github.io/osv.dev/post-v1-querybatch/, https://google.github.io/osv.dev/faq/

**Frontend:** local-bundled static JS/CSS. **Backend:** FastAPI on a free web-service tier if available; Render free plan has 15-min inactivity spin-down and ephemeral storage, so cache cannot be relied on as persistent. https://render.com/docs/free

**Hosting caution:** As of Nov 2026, creating a compute-backed Hugging Face Space (Gradio/Docker) requires paid account despite free CPU hourly pricing; do not assume it can be created with a free account: https://huggingface.co/docs/hub/spaces-overview

**Core security trade-off:** Free hosting is not a reason to execute arbitrary pip on untrusted public uploads without isolation. Restrict resolution to curated cases on hosted preview unless a sufficiently isolated worker is actually available, and label snapshots accurately. A working publicly demonstrable product is mandatory; ensure public demo demonstrates core capability with real previously captured resolver evidence and optional supported live paths.

**Submission:** README with reproducibility instructions, open-source license, `.kiro` tracked; screenshot gallery; source provenance; anonymized sample cases; GitHub repo; working app; public <3-minute YouTube; student details; optional genuine Kiro build blog & social post. Check policies/eligibility on official Devpost rules.

## 17. Honest expected judging outlook

Do not promise “44/50” or any fixed winner score. It depends on implementation. Rough subjective scenario ranges, not empirical predictions:
- Scanner + Halloween skin only: Innovation weak, likely undifferentiated.
- Complete evidence-backed surgery, honest uncertainty, excellent UI: noticeably better competitive position.
- Deep decision lab with reliable candidate comparisons, independent tests and impeccable 3-minute demo: strongest achievable path for this time budget.

## 18. Immediate first actions

1. Freeze product definition and acceptance criteria, especially *declared vs resolved vs installed*, *remove pin vs force remove*, and *unknown*.
2. Request the reported four-test source code, exact requirements snapshots, pip invocation and raw reports to make proof independently reproducible. Never claim independent verification until it occurs.
3. Set up repo in Kiro with current `.kiro/` spec/hook format and a curated regression fixture.
4. Implement end-to-end single case before expanding package types or redesigning the UI.
5. Choose hosted resolver isolation architecture deliberately instead of executing user-supplied package instructions on a free shared web container.

## Primary sources

- Contest official rules: https://kiroween.devpost.com/rules
- Kiro docs: https://kiro.dev/docs/specs/ ; https://kiro.dev/docs/specs/correctness/ ; https://kiro.dev/docs/hooks/
- PyPI JSON API: https://docs.pypi.org/api/json/
- Python Core Metadata: https://packaging.python.org/en/latest/specifications/core-metadata/
- pip dry-run/install report: https://pip.pypa.io/en/stable/cli/pip_install/ ; https://pip.pypa.io/en/stable/reference/installation-report/
- Requirements syntax/security: https://pip.pypa.io/en/stable/reference/requirements-file-format/
- OSV: https://google.github.io/osv.dev/post-v1-querybatch/ ; https://google.github.io/osv.dev/faq/
- Competitors: links in Section 2.
