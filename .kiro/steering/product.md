# PostMortem 2.0 - Product

## What it is
An interactive **dependency surgery lab** for Python projects, presented as a gothic autopsy table.

**Tagline:** "Don't just scan your dependencies. Perform surgery before you change them."

## Context
Kiroween 2026 hackathon, **Costume Contest** category. The spooky UI must make the app *more useful*, not just decorate it. Solo student developer, Python. Feature freeze: 2 Dec 2026.

## Problem
Developers inheriting an old Python project face version conflicts and known vulnerabilities. Existing tools (pip-audit, pipdeptree, Dependabot, Snyk) produce dry lists. They rarely let you **try a change safely first** and see exactly what it does, and they rarely say what is *unknown*.

## Users
Python developers inheriting legacy projects, student maintainers, small open-source teams.

## Core journey
Upload `requirements.txt` -> see the patient (graph of organs) -> click a torn artery (conflict) -> read the evidence -> choose an operation -> run a bounded simulation -> see the exact manifest diff and resolver outcome -> compare 2-3 operations -> export a surgical report.

## Three verbs
1. **Diagnose** - what is wrong, with evidence, and through which dependency path.
2. **Operate** - simulate remove / pin change / upgrade before touching the repo.
3. **Compare** - before vs after: conflicts fixed, OSV findings remaining, new risks, unknowns.

## Scope
- **P0 (must ship):** strict input validator, name normalization with `packaging`, metadata recovery (PyPI JSON -> wheel METADATA -> Unknown), declared graph for one fixed target env (CPython 3.12, Linux x86_64), conflict detector, OSV batch+details with dedup, Force Remove impact, gothic autopsy UI with evidence drawer, property-based tests (Hypothesis).
- **P1 (if time allows):** isolated resolver worker, exact manifest diff per operation, before/after comparison, Minimum-Change Surgery (2-3 candidate operations), release age labels, export report (Markdown/JSON).
- **P2 (out of scope):** GitHub URL scanning, npm, automatic code fixing, accounts, AI chat.

## Known limitations (probe 23 Nov 2026)
- Some old packages are sdist-only (markupsafe 1.0, itsdangerous 0.24) -> dependencies Unknown.
- flask 0.12.2 has empty `requires_dist` in PyPI JSON but wheel METADATA has them -> fallback works.
- Demo conflict: `requests==2.19.0` requires `urllib3<1.24,>=1.21.1`, file pins `urllib3==1.24.1` -> pip reports ResolutionImpossible.
- Any "after" scenario must state exactly which lines changed.
