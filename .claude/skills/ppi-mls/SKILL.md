---
name: ppi-mls
description: Show the Playoff Pain Index (PPI) for MLS teams. Use when the user types /ppi-mls, optionally with a team name (e.g. "/ppi-mls dallas") or "all". With no argument, shows the ranked leaderboard of all MLS teams by active MLS Cup drought pain.
---

# /ppi-mls

Report the Playoff Pain Index for MLS teams from the project's data file.

PPI measures a team's **active** MLS Cup drought (it resets to 0 when they win). Score = `16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*(winning seasons that missed the playoffs)`.

For MLS the rounds map by depth from MLS Cup: MLS Cup loss -> Finals(16), Conference Final loss -> Semi-finals(8), Conference Semifinal loss -> Quarter-finals(4), Round One loss -> First round(2).

## What to do

Run the shared query script from the repo root and show its output verbatim:

```bash
python3 ppi_query.py mls $ARGS
```

`$ARGS` is whatever follows `/ppi-mls`: **nothing** -> leaderboard; **`all`** -> full breakdown for every team; **a team name** (e.g. `dallas`, `revolution`, `galaxy`) -> that team's full card with the math, confidence, flags, and sources.

The script fuzzy-matches names (case-insensitive substring) and recomputes the score from the breakdown.

## Notes

- Data lives in `ppi-mls.json` (repo root). If missing, the research workflow hasn't been run yet.
- Confidence markers: `(~)` = medium, `(?)` = low.
- Rebrands/relocations reset or carry the clock: MetroStars -> Red Bulls (since 1996), Dallas Burn -> FC Dallas (since 1996), current San Jose counts from its 2008 re-founding. Inter Miami won the 2025 MLS Cup -> PPI 0.
- Several teams are recent expansions with short histories. Do not invent numbers; if a team is flagged low-confidence, say so plainly.
