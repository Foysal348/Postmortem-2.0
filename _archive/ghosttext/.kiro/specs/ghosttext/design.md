# Design: GhostText

## Data model
`Cell(ch: str, fg: Colour, bg: Colour, flash: bool, double: bool)`
`Page(num: int, rows: list[list[Cell]], fastext: dict[Colour, int], fetched_at: datetime, stale: bool)`

## Flow
Request /p/{num} -> page registry -> builder for that range -> (cache hit? return) -> fetch source -> Rewriter -> layout -> render_page() -> cache -> HTML/JSON.

## Frontend
Template paints a CSS grid of 24x40 spans. JS: digit buffer for navigation, Fastext key mapping (F1–F4 and R/G/Y/C), clock tick, fetch /api/p/{num} for instant page flips.

## Testing
Property-based (hypothesis): for any input text, the rendered page is 24x40 and only uses palette colours. Unit tests for navigation and fallback.
