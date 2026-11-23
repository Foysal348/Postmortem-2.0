# Requirements: GhostText

## R1 Page grid
WHEN any page is rendered THE SYSTEM SHALL produce exactly 24 rows of exactly 40 cells.
WHEN text exceeds 40 columns THE SYSTEM SHALL word-wrap it, and truncate with "..." if it exceeds the page body.

## R2 Navigation
WHEN the user types three digits THE SYSTEM SHALL load that page number.
IF the page does not exist THEN THE SYSTEM SHALL show page 404 "THE SPIRITS FOUND NOTHING HERE".
WHEN the user presses the red/green/yellow/cyan Fastext key THE SYSTEM SHALL go to that page's linked page.

## R3 Header row
THE SYSTEM SHALL show on row 0: "P{num}  GHOSTTEXT  {day} {date} {HH:MM:SS}" with a live clock.

## R4 Content
- Page 100: index.  Pages 101–119: news headlines (one story per page).
- Pages 400–409: weather for a user-chosen city.
- Pages 666–669: "haunted" pages (spooky stories, ASCII ghost art).
WHEN content is fetched THE SYSTEM SHALL rewrite it in a spooky Teletext tone, at most 18 lines of 38 characters.

## R5 Resilience
IF a source or the LLM fails THEN THE SYSTEM SHALL serve the last cached page and mark it "OLD NEWS FROM THE CRYPT".

## R6 Look
THE SYSTEM SHALL use only the 8 Teletext colours, a blocky monospace font, CRT scanlines, and an optional flicker effect that respects `prefers-reduced-motion`.
