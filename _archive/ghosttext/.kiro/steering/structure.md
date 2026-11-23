# Project structure

```
app/
  main.py          # FastAPI routes: GET /, GET /p/{num}, GET /api/p/{num}
  pages/           # one module per page group (index, news, weather, spooky)
  render.py        # grid model + render_page()
  sources/         # rss.py, weather.py
  rewrite.py       # Rewriter interface + LLM implementation + stub
  cache.py         # SQLite cache
  templates/ static/
tests/
```

Rules:
- Every line of page text must fit in 40 columns; never rely on CSS to clip.
- Keep functions small and typed; use `ruff` formatting.
