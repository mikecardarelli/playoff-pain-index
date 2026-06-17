---
name: ppi-wnba
description: Show the Playoff Pain Index (PPI) for WNBA teams. Use when the user types /ppi-wnba, optionally with a team name (e.g. "/ppi-wnba sun") or "all". With no argument, shows the ranked leaderboard of all WNBA teams by active title drought pain.
---

# /ppi-wnba

Report the Playoff Pain Index for WNBA teams from the project's data file.

PPI measures a team's **active** championship drought (it resets to 0 when they win). Score = `16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*(winning seasons that missed the playoffs)`.

For the WNBA the rounds map by depth from the Finals: WNBA Finals loss -> Finals(16), Conference Finals/Semifinals loss -> Semi-finals(8), first playoff round loss -> Quarter-finals(4). The shallow bracket means First round and winning-record-no-playoff are usually 0.

## What to do

Run the shared query script from the repo root and show its output verbatim:

```bash
python3 ppi_query.py wnba $ARGS
```

`$ARGS` is whatever follows `/ppi-wnba`: **nothing** -> leaderboard; **`all`** -> full breakdown for every team; **a team name** (e.g. `sun`, `liberty`, `aces`) -> that team's full card with the math, confidence, flags, and sources.

The script fuzzy-matches names (case-insensitive substring) and recomputes the score from the breakdown.

## Notes

- Data lives in `ppi-wnba.json` (repo root). If missing, the research workflow hasn't been run yet.
- Confidence markers: `(~)` = medium, `(?)` = low.
- The Connecticut Sun count from 2003 (formerly the Orlando Miracle). Las Vegas won the 2025 title -> PPI 0. Brand-new 2026 expansion teams (Toronto Tempo, Portland Fire) with no completed season sit at 0.
- Do not invent numbers. If a team is flagged low-confidence, say so plainly.
