# PostMortem 2.0 - Structure

## Layout
```
app/
  main.py            FastAPI routes
  validate.py        R1 input validator
  metadata.py        R2 PyPI JSON -> wheel METADATA -> Unknown
  graph.py           R3/R4/R6 declared graph, conflicts, force remove
  osv.py             R5 OSV batch + details + dedup
  surgery/
    operations.py    R7 build edited manifest + diff
    worker.py        R7 isolated pip dry-run (subprocess, timeout, no network beyond PyPI)
  report.py          R8
  models.py          Package, DependencyEdge, Evidence, Advisory, Conflict, Operation, ResolutionResult, SurgeryReport
  templates/ static/
tests/
samples/             legacy_flask_requests.txt (demo patient)
```

## Module responsibilities
- **validate.py** - Strict PEP 508 subset input validator. Reject `-r`, `-c`, `--index-url`, `--extra-index-url`, URLs, VCS, local paths, `-e`, any pip option; enforce size and line limits.
- **metadata.py** - Recover metadata: PyPI release JSON -> wheel `.dist-info/METADATA` (read only, never execute) -> else Unknown.
- **graph.py** - Declared graph with markers evaluated for one fixed target env (CPython 3.12, Linux x86_64); conflict detector; Force Remove impact ("what dies if I remove this").
- **osv.py** - OSV batch query + per-id details; show raw count and alias-deduplicated count.
- **surgery/operations.py** - Build edited manifest + diff per operation; before/after comparison (P1).
- **surgery/worker.py** - Isolated pip dry-run in a separate restricted process/container, with timeout (P1).
- **report.py** - Surgical report export (P1).
- **models.py** - All shared data models. Package, DependencyEdge, Evidence, Advisory, Conflict, Operation, ResolutionResult, SurgeryReport.
