# How to start building in Kiro (step by step)

The code, spec and steering must be produced **with Kiro's own agent** (rules: work done through other AI tools does not count as Kiro usage). The files in `docs/plan/` are your human-written planning input.

## Step 1 - Open the project
Kiro -> File -> Open Folder -> `D:\DevPost\Kiroween 2026`

## Step 2 - Steering
Open the Kiro panel -> Steering -> "Generate Steering Docs". Then chat:

> Read docs/plan/01-product-brief.md and docs/plan/03-architecture-draft.md. Update the steering docs (product.md, tech.md, structure.md) to match them. Add a steering file `principles.md` with the four non-negotiable principles and the strict definitions table. Keep them concise.

## Step 3 - Spec
Start a new **Spec** session (not Vibe):

> Create a spec named "postmortem" for PostMortem 2.0. Use docs/plan/01-product-brief.md, docs/plan/02-requirements-draft.md and docs/plan/03-architecture-draft.md as input. Keep the EARS requirement IDs (R1-R9) and the correctness properties P1-P8. Only P0 scope first; put P1 items as separate later tasks.

Review requirements -> design -> tasks. Edit anything you disagree with *in Kiro*.

## Step 4 - Hooks
Kiro panel -> Agent Hooks -> "+":
1. **Run tests on save:** when `app/**/*.py` or `tests/**/*.py` is saved -> "Run `uv run pytest -q`; if anything fails, explain and propose a fix."
2. **Self-autopsy:** when `pyproject.toml` or `requirements*.txt` changes -> "Run PostMortem's analyzer on this project's own dependencies and summarize conflicts and OSV findings."

## Step 5 - Build
Run tasks one by one from `tasks.md` ("Start task"). After each task: run tests, commit.

## Step 6 - Keep the log
After every interesting moment, add a line to `docs/KIRO_LOG.md` (bug found by a property test, steering that fixed a wrong answer, a hook that saved time, screenshot path). This becomes the write-up and blog post.

## Tips
- Use the property-based testing option when Kiro offers it for a requirement.
- If Kiro invents a PyPI/OSV field, add the correct API shape to steering (e.g. a `steering/apis.md`).
- Commit often: `git add -A && git commit -m "..."` (keep `.kiro/` committed).
