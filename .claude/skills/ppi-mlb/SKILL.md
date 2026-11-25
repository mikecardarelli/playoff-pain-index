---
name: ppi-mlb
description: Show the Playoff Pain Index (PPI) for MLB teams. Use when the user types /ppi-mlb, optionally with a team name (e.g. "/ppi-mlb mets") or "all". With no argument, shows the ranked leaderboard of all 30 MLB teams by active title-drought pain.
---

# /ppi-mlb

Report the Playoff Pain Index for MLB teams from the project's data file.

PPI measures a team's **active** championship drought (it resets to 0 when they win a title). Score = `16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*(winning seasons that missed the playoffs)`.

## What to do

Run the shared query script from the repo root and show its output verbatim:

```bash
python3 ppi_query.py mlb $ARGS
```

Where `$ARGS` is whatever the user passed after `/ppi-mlb`:

- **no argument** -> ranked leaderboard of all 30 teams
- **`all`** -> full breakdown card for every team, ranked
- **a team name** (e.g. `mets`, `red sox`, `dodgers`) -> that team's full card with the scoring math, confidence, flags, and sources

The script fuzzy-matches team names (case-insensitive substring) and recomputes the score from the breakdown so the printed number always matches its components.

## Notes

- Data lives in `ppi-mlb.json` (repo root). If it's missing, the research workflow hasn't been run yet.
- Confidence markers: `(~)` = medium, `(?)` = low. Mention these if the user asks about a flagged team.
- Do not invent or "fill in" numbers. If a team is flagged low-confidence, say so plainly.
