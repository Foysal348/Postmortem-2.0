# PostMortem 2.0 - Tech

## Stack
- Python 3.12, FastAPI, Jinja2, `uv` for dependencies.
- `packaging` (requirements, specifiers, markers, versions), `networkx` (graph), `httpx` (HTTP).
- SQLite cache.
- Frontend: HTML/CSS + minimal JS, Cytoscape.js for the graph (organs/arteries styled via data classes).
- Tests: pytest + Hypothesis.
- Hosting: Render free web service (sleeps when idle; warm it before judging). Resolver worker only if isolation is possible; otherwise ship curated, clearly labelled recorded cases.

## Key models
- `Evidence(source: Literal["pypi-json","wheel-metadata","osv","pip-report","unknown"], url, fetched_at)`
- `DependencyEdge(from_pkg, to_pkg, specifier, marker, evidence)`
- `Conflict(requirer, required, specifier, pinned_version, evidence)`
- `Operation(kind: remove_pin | force_remove | set_pin, package, new_spec)`
- `ResolutionResult(ok, resolved: dict[str,str] | None, error: str | None, environment, raw_report_path)`

## API
- `POST /api/patients` (upload) -> patient id
- `GET /api/patients/{id}` -> graph JSON (nodes with status classes, edges, conflicts, unknowns)
- `POST /api/patients/{id}/force-remove` -> affected nodes
- `POST /api/patients/{id}/operations` -> diff + resolution result (P1)
- `GET /api/patients/{id}/report.md`

## Security
- Never run `pip` with user-controlled options; build the argument list in code.
- `--only-binary=:all:` so no `setup.py` runs; `--dry-run`, `--ignore-installed`, fixed `--python-version`/`--platform`, `--target` temp dir, timeout 60 s.
- Do not store uploaded files beyond the session; no secrets in logs.
