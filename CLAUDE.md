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
- The 2026 seasons are in progress and do not count. Only completed seasons score.

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
- Bump `updated` in any file you touch.
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
