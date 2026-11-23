# Tech stack

- Python 3.12, FastAPI, Jinja2 templates, plain HTML/CSS/vanilla JS (no frontend framework).
- Page rendering: a pure-Python `render_page()` that returns a 24x40 grid of cells (char, fg, bg, flags). The HTML template only paints that grid.
- Teletext palette only: black, red, green, yellow, blue, magenta, cyan, white.
- Data: RSS via `feedparser`, weather via Open-Meteo (no key needed).
- LLM rewriting behind an interface `Rewriter` so it can be swapped or stubbed in tests.
- Cache pages in SQLite; content refreshes every 15 minutes.
- Tests: pytest + hypothesis (property-based tests for page layout invariants).
- Dependency management: `uv` with `pyproject.toml`.
