---
name: ppi-cfl
description: Show the Playoff Pain Index (PPI) for CFL teams. Use when the user types /ppi-cfl, optionally with a team name (e.g. "/ppi-cfl ticats") or "all". With no argument, shows the ranked leaderboard of all 9 CFL teams by active Grey Cup drought pain.
---

# /ppi-cfl

Report the Playoff Pain Index for CFL teams from the project's data file.

PPI measures a team's **active** Grey Cup drought (it resets to 0 when they win). Score = `16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*(winning seasons that missed the playoffs)`.

For the CFL the rounds map by depth from the Grey Cup: Grey Cup loss -> Finals(16), Division Final loss -> Semi-finals(8), Division Semifinal loss -> Quarter-finals(4). The CFL's small bracket means First round and winning-record-no-playoff are usually 0.

## What to do

Run the shared query script from the repo root and show its output verbatim:

```bash
python3 ppi_query.py cfl $ARGS
```

`$ARGS` is whatever follows `/ppi-cfl`: **nothing** -> leaderboard of all 9 teams; **`all`** -> full breakdown for every team; **a team name** (e.g. `ticats`, `riders`, `argos`) -> that team's full card with the math, confidence, flags, and sources.

The script fuzzy-matches names (case-insensitive substring) and recomputes the score from the breakdown.

## Notes

- Data lives in `ppi-cfl.json` (repo root). If missing, the research workflow hasn't been run yet.
- Confidence markers: `(~)` = medium, `(?)` = low.
- A team that just won (Saskatchewan won the 2025 Grey Cup) sits at PPI 0.
- Do not invent numbers. If a team is flagged low-confidence, say so plainly.
