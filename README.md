# Playoff Pain Index

Live: https://mikecardarelli.github.io/playoff-pain-index/

The Playoff Pain Index (PPI) scores how much accumulated heartbreak a fan base
has built up during its **active championship drought**. The longer you go
without a title, and the closer you keep coming, the higher your score. Win a
title and the score resets to 0.

The live site (`index.html`) shows the 25 most painful active droughts across
seven leagues, plus aggregated **Most** and **Least Painful Cities** tables.
This repository also contains the full computed dataset behind those tables:
the PPI for **every** team in MLB, NBA, NHL, NFL, CFL, WNBA, and MLS (178 teams).

## Scoring

A team earns points for every season in its active drought, based on how deep
it went in the playoffs (or whether it had a winning record but missed them):

| Outcome | Points |
| --- | --- |
| Lost in the Finals (championship round) | 16 |
| Lost in the Semi-finals (round before the final) | 8 |
| Lost in the Quarter-finals (two rounds before the final) | 4 |
| Lost in the First round | 2 |
| Winning record, but missed the playoffs | 1 |

```
PPI = 16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*WinningRecordNoPlayoff
```

Rules:

- **Active streak only.** Winning a title resets the score to 0.
- **Relocations reset.** A team that moves starts fresh in its new city. New-city
  fans do not inherit the old city's pain.
- **Expansion replacements combine.** A city that loses a team and later gets a
  replacement combines both scores (Minnesota fans keep the North Stars' pain on
  the Wild; Houston combines the Texans and Oilers).
- The winning-record-no-playoff bonus matters most in MLB and the NFL, whose
  playoff fields were historically small.

### Round mapping per league

Each league's bracket is mapped by depth from its championship:

| League | Finals (16) | Semis (8) | Quarters (4) | First round (2) |
| --- | --- | --- | --- | --- |
| MLB | World Series | LCS | Division Series | Wild Card |
| NBA | NBA Finals | Conference Finals | Conference Semifinals | First Round |
| NHL | Stanley Cup Final | Conference Finals | Second Round | First Round |
| NFL | Super Bowl | Conference Championship | Divisional Round | Wild Card |
| CFL | Grey Cup | Division Final | Division Semifinal | (usually none) |
| WNBA | WNBA Finals | Conference Finals / Semifinals | First playoff round | (usually none) |
| MLS | MLS Cup | Conference Final | Conference Semifinal | Round One |

## The data

One JSON file per league, all in the repo root:

`ppi-mlb.json`, `ppi-nba.json`, `ppi-nhl.json`, `ppi-nfl.json`, `ppi-cfl.json`,
`ppi-wnba.json`, `ppi-mls.json`

Each file looks like:

```json
{
  "league": "MLB",
  "updated": "2026-06-16",
  "scoring": "16*Finals + 8*Semis + 4*Quarters + 2*FirstRound + 1*WinningRecordNoPlayoff",
  "teams": [
    {
      "team": "Cleveland Guardians",
      "score": 139,
      "since": "Since last title in 1948",
      "lastChampionship": "1948 World Series",
      "breakdown": { "finals": 4, "semis": 3, "quarters": 6, "firstRound": 3, "winningRecordNoPlayoff": 21 },
      "confidence": "high",
      "flags": [],
      "sources": ["..."],
      "notes": "..."
    }
  ]
}
```

`score` always equals the breakdown run through the scoring formula, so the two
can never drift apart. Coverage: MLB 30, NBA 30, NHL 32, NFL 32, CFL 9, WNBA 15,
MLS 30 (178 teams).

### How the data was sourced

- The teams that also appear on the live site are **pinned to the site's
  published numbers**, so the dataset agrees with the existing leaderboard.
- The rest were researched per team from authoritative sources (Wikipedia
  "List of <team> seasons" tables and league championship pages), with the
  source URLs kept in each team's `sources`.
- Every entry carries a `confidence` value and a `flags` list. Anything that
  could not be confirmed is flagged, never guessed. Recent championship resets
  were confirmed against live sources before any team was set to 0.

## Most and Least Painful Cities

`ppi_cities.py` aggregates team PPI into cities and writes `ppi-cities.json`,
which feeds the two tables on the site.

Cities use a **rank-discounted sum**: a city's teams are sorted by PPI (most
painful first), then added at a diminishing rate. The most painful team counts
in full, the second at 1/2, the third at 1/3, and so on:

```
CityPain = p(1)*1 + p(2)/2 + p(3)/3 + ... + p(n)/n     (teams sorted desc)
```

Each team keeps its real PPI; the multiplier is just 1/rank. This rewards a city
for having several genuinely cursed teams without letting a high team count win
on volume alone. The **Least Painful Cities** table is the same measure, lowest
scores first, limited to cities with at least two teams (a one-team town fresh
off a title would otherwise top it by default).

Teams are grouped into metros (suburbs fold into their major city). The grouping
choices that meaningfully move the ranking are recorded in `ppi_cities.py`
(`JUDGMENT`) and in `ppi-cities.json` (`judgmentCalls`).

```bash
python3 ppi_cities.py            # Most Painful Cities, top 20
python3 ppi_cities.py --least 2  # Least Painful Cities, min 2 teams
python3 ppi_cities.py --json     # regenerate ppi-cities.json
```

## Querying the data

`ppi_query.py` reads a league file, fuzzy-matches a team, and prints its card or
a ranked leaderboard (it recomputes the score from the breakdown so the two stay
in sync):

```bash
python3 ppi_query.py nba              # NBA leaderboard
python3 ppi_query.py nba knicks       # one team's full card
python3 ppi_query.py mlb all          # every MLB team, full breakdowns
```

There is also one editor skill per league under `.claude/skills/` (`ppi-mlb`,
`ppi-nba`, `ppi-nhl`, `ppi-nfl`, `ppi-cfl`, `ppi-wnba`, `ppi-mls`) that wrap the
same query, and a `CLAUDE.md` documenting the scoring methodology, reset rules,
and per-league round mapping for anyone editing the data.

## Updating after a season

When a season finishes:

1. Reset any new champion to 0 and start its drought the following season.
2. Add the latest season's result for every other team in that league (the round
   they lost in, or a winning-record-no-playoff if they missed the playoffs).
3. Recompute and bump `updated` in the affected JSON file.
4. Run `python3 ppi_cities.py --json` to refresh the city aggregates.

## Project structure

```
index.html              the live site (leaderboard + city tables)
style.css               site styles
ppi-<league>.json       computed PPI data, one file per league
ppi-cities.json         aggregated city pain (Most + Least Painful Cities)
ppi_cities.py           city aggregator / generator
ppi_query.py            per-team / leaderboard query tool
.claude/skills/ppi-*    one query skill per league
CLAUDE.md               scoring methodology and editing notes
*.png                   team logos and site assets
```
