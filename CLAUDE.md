# CLAUDE.md

Guidance for AI agents working in this repository. Read this before changing any
PPI data, scoring logic, or skills.

## What this project is

The Playoff Pain Index (PPI) is a static site (`index.html`, served via GitHub
Pages) that ranks the most painful active championship droughts in pro sports.
This repo also holds a full computed dataset and seven skills that report PPI for
every team in MLB, NBA, NHL, NFL, CFL, WNBA, and MLS.

This is a **public** repository. Never commit anything confidential. Do not add a
`GOALS.md` unless explicitly asked; if asked, it must be gitignored here.

## Hard rule: never fabricate data

Never simulate, impute, interpolate, estimate, or invent a season's playoff
result or record. If a value cannot be confirmed from an authoritative source,
mark it: set `confidence` to `medium` or `low` and describe the gap in `flags`.
An honest, flagged gap is always better than a confident wrong number. This
overrides any urge to make the dataset look complete.

## Scoring (canonical)

```
PPI = 16*finals + 8*semis + 4*quarters + 2*firstRound + 1*winningRecordNoPlayoff
```

| Field | Meaning |
| --- | --- |
| `finals` | lost in the championship round (final 2) |
| `semis` | lost the round before the final (final 4) |
| `quarters` | lost two rounds before the final (final 8) |
| `firstRound` | lost in the first playoff round (final 16) |
| `winningRecordNoPlayoff` | winning regular-season record (more wins than losses), missed the playoffs |

Tiers are assigned by **depth from the championship**, not by a round's literal
name, which is what makes older/odd formats and different leagues comparable.

### Reset and combination rules

- A championship resets the score to 0. The drought starts the **next** season.
- A relocation resets the score to 0 in the new city. Use the most recent of
  {last title, relocation, founding} as the drought start. New-city fans do not
  inherit the old city's pain.
- Designated expansion-replacement cities combine with the team that left
  (Minnesota Wild + North Stars; Houston Texans + Oilers).
- Only completed seasons score. A league's season counts once its championship has
  been decided, not when the calendar year ends. As of 2026-10-28 the data runs
  through: MLB 2026 (Brewers won the World Series), NBA 2025-26 (Knicks), NHL
  2025-26 (Hurricanes), NFL 2025 (Seahawks, Super Bowl LX), CFL 2025
  (Roughriders), WNBA 2025 (Aces), MLS 2025 (Inter Miami). The 2026 WNBA Finals
  (Golden State vs Atlanta) were still in progress, and the 2026 CFL and MLS
  seasons and the 2026 NFL season had not finished. Update this line whenever a
  league's latest season is added.

### Per-league round mapping

- **MLB:** World Series=finals, LCS=semis, Division Series=quarters, Wild Card=firstRound.
  Pre-1969 had only the World Series, so a pennant winner who lost the WS is a
  finals loss and other winning teams that missed it count as winningRecordNoPlayoff
  (this is why old MLB droughts carry large winningRecordNoPlayoff totals).
- **NBA:** Finals, Conference Finals=semis, Conference Semifinals=quarters, First
  Round=firstRound. The play-in tournament is not a playoff round. ABA seasons
  count for pre-1976 droughts (e.g. the Pacers' drought dates to their 1973 ABA title).
- **NHL:** Stanley Cup Final, Conference Finals=semis, Second Round=quarters, First
  Round=firstRound. Formats varied a lot (Original Six, division era); map by depth.
- **NFL:** Super Bowl (or pre-1966 league championship), Conference Championship=semis,
  Divisional=quarters, Wild Card=firstRound.
- **CFL:** Grey Cup, Division Final=semis, Division Semifinal=quarters. Small bracket,
  so firstRound and winningRecordNoPlayoff are usually 0.
- **WNBA:** WNBA Finals, Conference Finals/Semifinals=semis, first playoff round=quarters.
  Shallow bracket, so firstRound and winningRecordNoPlayoff are usually 0.
- **MLS:** MLS Cup, Conference Final=semis, Conference Semifinal=quarters, Round
  One=firstRound. Watch rebrands/relocations (MetroStars to Red Bulls, Dallas Burn
  to FC Dallas, San Jose's 2008 re-founding, Houston Dynamo from the relocated San Jose).

## Files

- `index.html` is the live site and the source of truth for the 25 teams it lists.
- `ppi-<league>.json` holds the computed dataset, one file per league. Shape:
  `{ league, updated, scoring, teams: [ { team, score, since, lastChampionship,
  breakdown:{finals,semis,quarters,firstRound,winningRecordNoPlayoff}, confidence,
  flags, sources, notes } ] }`. The optional `methodologyNote` carries a
  league-level caveat.
- `ppi_query.py` reads a league file, fuzzy-matches a team, and **recomputes the
  score from `breakdown`**. Always trust the recomputed score over a stored one.
- `.claude/skills/ppi-<league>/SKILL.md` are thin wrappers that call
  `python3 ppi_query.py <league> $ARGS`.
- `ppi_cities.py` aggregates team PPI into metros (rank-discounted sum with a
  city-level championship reset) and writes `ppi-cities.json` (big-four reset)
  and `ppi-cities-all.json` (any-league reset). `python3 ppi_cities.py --html`
  prints the four `<tbody>` blocks for the cities tables in `index.html`.
- `ppi-cities-postreset.json` and `ppi-cities-postreset-all.json` hold sourced,
  season-by-season ledgers of the pain a team has piled up since its city's last
  reset title. `build_postreset_all.py` derives the all-leagues file from the
  big-four one plus extra research.

## The pinning convention

The 20 teams that also appear on `index.html` are **pinned** to the site's
published numbers so the dataset never disagrees with the live page. A pinned
team's `notes` begins with "Pinned to the published playoff-pain-index site
numbers". When research and the site disagree, keep the pin and record the
discrepancy in `notes` (see Hamilton Tiger-Cats and the New England Revolution).
If you ever decide to correct the site itself, update `index.html` and the pin
together.

## Editing the data

- Editing a single team: change its `breakdown`, leave `score` to the query tool
  (it recomputes). If you store a `score`, keep it consistent with the breakdown.
- Adding the latest completed season: append that season's result for each team
  (the round lost, or a winningRecordNoPlayoff), and reset any new champion to 0.
  Clear any flags that said that season was "in progress".
- Then carry the season into the city files: append it to every ledger in both
  `ppi-cities-postreset*.json` for that league's teams, drop the ledger of a team
  that just became its city's reset champion, run `python3 ppi_cities.py --json`,
  and paste the `--html` output into the cities tables. If a pinned site team's
  score changes, update its card on `index.html` and re-sort the cards.
- City reset timing: a team's season counts toward its city only if the season
  falls in a later year than the reset title (an MLB season that ends in October
  2026 does not count against a June 2026 NBA or NHL title in the same city).
- Bump `updated` in any file you touch. When `index.html` changes, also bump the
  footer's "(Last updated: Month D, YYYY)" line (near the bottom of the page) to
  the same date. It is easy to miss and the live site shows it to every visitor.
- Keep `sources` populated for any researched change. Do not strip a flag without
  confirming the underlying value.

## Regenerating from scratch

The dataset was built by fanning out one research agent per team, each returning
a sourced, confidence-flagged breakdown, with the score computed deterministically
from the counts and the site teams used as cross-check anchors. To rebuild or
extend, repeat that pattern: research each team independently, cite sources, flag
uncertainty, pin the `index.html` teams, and verify every championship reset
against a live source before setting a team to 0.

## Verify a few invariants after any change

- `python3 -c "import json; [json.load(open(f'ppi-{l}.json')) for l in
  ('mlb','nba','nhl','nfl','cfl','wnba','mls')]"` parses every file.
- Each team's `score` equals `16*finals + 8*semis + 4*quarters + 2*firstRound + 1*winningRecordNoPlayoff`.
- Every team listed on `index.html` still matches its JSON entry.
- No team has a negative or impossible count, and champions from the latest
  completed season read 0.
- The footer's "Last updated" date on `index.html` matches the newest `updated`
  date in the JSON files: `grep -o 'Last updated: [^)]*' index.html`.
