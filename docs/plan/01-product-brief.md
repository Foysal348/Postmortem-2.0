# PostMortem 2.0 - Product Brief

> Input document for Kiro. Kiro should turn this into steering docs and a spec.
> Deep research and sources: `docs/research/PostMortem_3_Deep_Research_Build_Blueprint_2026-11-23.md`

## One line
An interactive **dependency surgery lab** for Python projects, presented as a gothic autopsy table.

**Tagline:** "Don't just scan your dependencies. Perform surgery before you change them."

## Hackathon
- Kiroween 2026, category **Costume Contest** (the spooky UI must make the app *more useful*, not just decorate it).
- Solo student developer, Python. Deadline: 4 Dec 2026, 2:00 PM PT. Feature freeze: 2 Dec.

## Problem
Developers who inherit an old Python project face version conflicts and known vulnerabilities. Existing tools (pip-audit, pipdeptree, Dependabot, Snyk) produce dry lists. They rarely let you **try a change safely first** and see exactly what it does, and they rarely say what is *unknown*.

## Users
Python developers inheriting legacy projects, student maintainers, small open-source teams.

## Core journey
Upload `requirements.txt` -> see the patient (graph of organs) -> click a torn artery (conflict) -> read the evidence -> choose an operation -> run a bounded simulation -> see the exact manifest diff and resolver outcome -> compare 2-3 operations -> export a surgical report.

## Three verbs
1. **Diagnose** - what is wrong, with evidence, and through which dependency path.
2. **Operate** - simulate remove / pin change / upgrade before touching the repo.
3. **Compare** - before vs after: conflicts fixed, OSV findings remaining, new risks, unknowns.

## Principles (non-negotiable)
1. **Evidence over assumptions.** Every claim shows its source (PyPI JSON, wheel METADATA, OSV record id, pip report).
2. **Simulation over promises.** A resolver success means *constraints are satisfiable*, never "your app will run".
3. **Unknown is never green.** Missing metadata is shown as unknown fog, never as healthy.
4. **Decoration serves decision.** Every visual effect encodes data (severity, conflict, uncertainty).

## Strict definitions
| Term | Meaning |
|---|---|
| Declared graph | Built from the manifest + package metadata. May be partial or contradictory. |
| Resolved graph | One package selection pip accepted for a recorded target environment. Not proof the app runs. |
| Remove Pin | Delete a line and re-resolve; the package may come back transitively. |
| Force Remove | Hypothetical removal from a graph; shows which packages declare it as a requirement. |
| Constraint pass | Resolver success only. |
| Unknown | No reliable metadata / evidence. |
| Known OSV finding | An OSV record that matches this package+version. Not proof of exploitability. |
| Time since last release | A date interval. Not proof of abandonment. |

## Visual language (Costume Contest)
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
Respect `prefers-reduced-motion`. Text must stay readable (contrast ≥ 4.5:1).

## Scope
**P0 (must ship)**
- Strict input validator (narrow PEP 508 subset; reject `-r`, `-c`, `--index-url`, `--extra-index-url`, URLs, VCS, local paths, `-e`, any pip option; size and line limits).
- Name normalization with `packaging`.
- Metadata recovery: PyPI release JSON -> wheel `.dist-info/METADATA` (read only, never execute) -> else Unknown.
- Declared graph with markers evaluated for one fixed target env (CPython 3.12, Linux x86_64).
- Conflict detector (pinned version violates another package's specifier).
- OSV querybatch + per-id details; show raw count and alias-deduplicated count.
- Force Remove impact ("what dies if I remove this").
- Gothic autopsy table UI with evidence drawer.
- Property-based tests (Hypothesis).

**P1 (if time allows)**
- Isolated resolver worker: `pip install --dry-run --ignore-installed --only-binary=:all: --python-version 3.12 --platform manylinux2014_x86_64 --report` in a separate restricted process/container, with timeout.
- Exact manifest diff per operation and before/after comparison.
- Minimum-Change Surgery: compare 2-3 candidate operations (fewest direct edits vs most OSV findings removed - shown as separate objectives).
- Release age labels; export report (Markdown/JSON).

**P2 (out of scope)**
GitHub URL scanning, npm, automatic code fixing, accounts, AI chat.

## Known limitations (verified by a probe on 23 Nov 2026)
- Some old packages are sdist-only (e.g. markupsafe 1.0, itsdangerous 0.24) -> dependencies Unknown.
- flask 0.12.2 has empty requires_dist in PyPI JSON but its wheel METADATA has them -> fallback works.
- Example real conflict for the demo: `requests==2.19.0` requires `urllib3<1.24,>=1.21.1`, file pins `urllib3==1.24.1` -> pip reports ResolutionImpossible.
- Any "after" scenario must state exactly which lines changed.
