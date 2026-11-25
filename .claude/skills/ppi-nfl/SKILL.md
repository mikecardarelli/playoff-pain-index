---
name: ppi-nfl
description: Show the Playoff Pain Index (PPI) for NFL teams. Use when the user types /ppi-nfl, optionally with a team name (e.g. "/ppi-nfl bills") or "all". With no argument, shows the ranked leaderboard of all 32 NFL teams by active title-drought pain.
---

# /ppi-nfl

Report the Playoff Pain Index for NFL teams from the project's data file.

PPI measures a team's **active** championship drought (it resets to 0 when they win a title). Score = `16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*(winning seasons that missed the playoffs)`.

For the NFL the rounds map as: Super Bowl loss -> Finals(16), Conference Championship loss -> Semi-finals(8), Divisional Round loss -> Quarter-finals(4), Wild Card loss -> First round(2). The "winning record, no playoffs" bonus matters a lot for the NFL given its historically small playoff field.

## What to do

Run the shared query script from the repo root and show its output verbatim:

```bash
python3 ppi_query.py nfl $ARGS
```

Where `$ARGS` is whatever the user passed after `/ppi-nfl`:

- **no argument** -> ranked leaderboard of all 32 teams
- **`all`** -> full breakdown card for every team, ranked
- **a team name** (e.g. `bills`, `vikings`, `49ers`) -> that team's full card with the scoring math, confidence, flags, and sources

The script fuzzy-matches team names (case-insensitive substring) and recomputes the score from the breakdown so the printed number always matches its components.

## Notes

- Data lives in `ppi-nfl.json` (repo root). If it's missing, the research workflow hasn't been run yet.
- Confidence markers: `(~)` = medium, `(?)` = low. Mention these if the user asks about a flagged team.
- The Houston Texans entry combines Texans + Oilers seasons since 1962 (Houston keeps the pain after the Oilers left for Tennessee). The Tennessee Titans count only from the 1997 relocation.
- Relocations reset the clock: e.g. Las Vegas Raiders (2020), Los Angeles Chargers (2017).
- Do not invent or "fill in" numbers. If a team is flagged low-confidence, say so plainly.
