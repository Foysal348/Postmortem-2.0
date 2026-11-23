# PostMortem 2.0 - Requirements Draft (EARS)

> Draft for Kiro. Ask Kiro to refine these into `.kiro/specs/postmortem/requirements.md`.
> IDs are referenced by tests and tasks.

## R1 Input validation
- R1.1 WHEN a user uploads a requirements file THE SYSTEM SHALL accept only lines of the form `name[extras] specifier [; marker]` and comments/blank lines.
- R1.2 IF a line contains `-r`, `-c`, `-e`, `--` options, a URL, a VCS reference, or a local path THEN THE SYSTEM SHALL reject the file and name the offending line.
- R1.3 IF the file exceeds 64 KB or 200 requirement lines THEN THE SYSTEM SHALL reject it.
- R1.4 THE SYSTEM SHALL normalize distribution names (PEP 503), so `Flask`, `flask` and `FLASK` are one package.
- R1.5 IF the same package appears twice THEN THE SYSTEM SHALL report a duplicate error.

## R2 Metadata recovery
- R2.1 WHEN analysing `name==version` THE SYSTEM SHALL read `requires_dist` from the PyPI release JSON.
- R2.2 IF `requires_dist` is missing THEN THE SYSTEM SHALL read `Requires-Dist` from the wheel `.dist-info/METADATA` without executing any package code.
- R2.3 IF no wheel exists THEN THE SYSTEM SHALL mark the package's dependencies as Unknown.
- R2.4 THE SYSTEM SHALL record the evidence source of every dependency edge (`pypi-json`, `wheel-metadata`, `unknown`).
- R2.5 THE SYSTEM SHALL cache metadata and OSV responses.

## R3 Declared graph
- R3.1 THE SYSTEM SHALL evaluate environment markers against one recorded target environment (CPython 3.12, Linux x86_64) and show that environment in the UI.
- R3.2 THE SYSTEM SHALL drop requirements guarded by extras that were not requested.
- R3.3 THE SYSTEM SHALL never present an Unknown node as healthy.

## R4 Conflicts
- R4.1 WHEN a pinned version does not satisfy another package's specifier THE SYSTEM SHALL create a conflict with both packages, the specifier, the pinned version and the evidence source.
- R4.2 THE SYSTEM SHALL draw each conflict as a torn artery between the two organs.

## R5 Vulnerabilities
- R5.1 THE SYSTEM SHALL query OSV in batch and fetch details per id.
- R5.2 THE SYSTEM SHALL show raw OSV record count and the count after alias deduplication.
- R5.3 IF severity is unavailable THEN THE SYSTEM SHALL label it "severity unknown", not critical.
- R5.4 THE SYSTEM SHALL state that "no OSV record" does not mean "safe".

## R6 Force Remove ("What dies if I remove this?")
- R6.1 WHEN the user force-removes package P THE SYSTEM SHALL highlight every package that declares P as a requirement.
- R6.2 THE SYSTEM SHALL not mark a package as affected if P is still provided (it is never removed from other roots that still need it - shared dependencies stay).
- R6.3 THE SYSTEM SHALL mark impact as incomplete where Unknown nodes are involved.

## R7 Simulation (P1)
- R7.1 WHEN the user runs an operation THE SYSTEM SHALL build the edited manifest and show the exact line diff.
- R7.2 THE SYSTEM SHALL run the resolver only in an isolated worker with only binary distributions, a fixed target environment, no installation, and a timeout.
- R7.3 IF the resolver fails THEN THE SYSTEM SHALL show the resolver's conflict message.
- R7.4 IF the resolver succeeds THEN THE SYSTEM SHALL show resolved versions, OSV findings before vs after, and the label "Constraints satisfied - runtime not tested".
- R7.5 THE SYSTEM SHALL compare up to 3 candidate operations side by side.

## R8 Report
- R8.1 THE SYSTEM SHALL export a Markdown/JSON report with every finding, its evidence and all unknowns.

## R9 UI / accessibility
- R9.1 THE SYSTEM SHALL encode every visual effect from data (see product brief table).
- R9.2 THE SYSTEM SHALL respect `prefers-reduced-motion` and keep text contrast ≥ 4.5:1.
- R9.3 THE SYSTEM SHALL work with keyboard only.

## Correctness properties (for property-based tests)
- P1 Name normalization is idempotent: `norm(norm(x)) == norm(x)`.
- P2 Validator never accepts a line containing a URL, path, or pip option.
- P3 For any generated graph, Force Remove of P affects only packages with an edge to P.
- P4 Removing one root never removes a dependency still required by another root.
- P5 Conflict detector agrees with `packaging.SpecifierSet.contains` for random versions/specifiers.
- P6 An Unknown node never receives a "healthy" status.
- P7 For any operation, applying the diff to the original manifest yields the edited manifest exactly.
- P8 OSV dedup count ≤ raw count, and every raw id maps to exactly one deduplicated finding.
