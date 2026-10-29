#!/usr/bin/env python3
"""Playoff Pain Index query tool.

Usage:
    python3 ppi_query.py <league> [team|all]

    <league>   mlb | nba | nhl | nfl | cfl | wnba | mls
    (no arg)   ranked leaderboard (one line per team)
    all        full breakdown for every team, ranked
    <team>     full card for one team (fuzzy, case-insensitive substring)

Reads ppi-<league>.json (same directory). Score is recomputed from the
breakdown so the printed number always matches the components:
    score = 16*finals + 8*semis + 4*quarters + 2*firstRound + 1*winningRecordNoPlayoff
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = {"finals": 16, "semis": 8, "quarters": 4, "firstRound": 2, "winningRecordNoPlayoff": 1}
ROUND_LABEL = {
    "finals": "Finals losses",
    "semis": "Semi-finals losses",
    "quarters": "Quarter-finals losses",
    "firstRound": "First round losses",
    "winningRecordNoPlayoff": "Winning record, no playoffs",
}
CONF_MARK = {"high": "", "medium": " (~)", "low": " (?)"}


def load(league):
    path = os.path.join(HERE, f"ppi-{league}.json")
    if not os.path.exists(path):
        sys.exit(f"No data file: ppi-{league}.json (run the research workflow first)")
    with open(path) as fh:
        return json.load(fh)


def calc(team):
    b = team["breakdown"]
    return sum(WEIGHTS[k] * b.get(k, 0) for k in WEIGHTS)


def ranked(teams):
    return sorted(teams, key=lambda t: calc(t), reverse=True)


def leaderboard(data):
    teams = ranked(data["teams"])
    print(f"\n  {data['league']} Playoff Pain Index  (updated {data.get('updated','?')})\n")
    for i, t in enumerate(teams, 1):
        mark = CONF_MARK.get(t.get("confidence", "high"), "")
        print(f"  {i:>2}. {calc(t):>4}  {t['team']}{mark}")
    print(f"\n  {len(teams)} teams. (~)=medium / (?)=low confidence. Score = 16F+8S+4Q+2R+1W\n")


def card(t):
    b = t["breakdown"]
    print(f"\n  {t['team']}  -  PPI {calc(t)}")
    print(f"  {t.get('since','')}")
    if t.get("lastChampionship"):
        print(f"  Last championship: {t['lastChampionship']}")
    print()
    for k in WEIGHTS:
        n = b.get(k, 0)
        print(f"    {ROUND_LABEL[k]:<30} {n:>3}  x{WEIGHTS[k]:<2} = {n*WEIGHTS[k]:>4}")
    print(f"    {'':<30} {'':>3}        {'':>4}")
    print(f"    {'TOTAL PPI':<30} {'':>3}        {calc(t):>4}")
    conf = t.get("confidence", "high")
    print(f"\n  Confidence: {conf}")
    if t.get("flags"):
        for f in t["flags"]:
            print(f"    ! {f}")
    if t.get("notes"):
        print(f"  Notes: {t['notes']}")
    if t.get("sources"):
        print("  Sources:")
        for s in t["sources"]:
            print(f"    - {s}")
    print()


def find(data, query):
    q = query.lower()
    hits = [t for t in data["teams"] if q in t["team"].lower()]
    if not hits:
        # try matching any word
        hits = [t for t in data["teams"] if any(q in w.lower() for w in t["team"].split())]
    return hits


def main():
    leagues = ("mlb", "nba", "nhl", "nfl", "cfl", "wnba", "mls")
    if len(sys.argv) < 2:
        sys.exit(f"Usage: python3 ppi_query.py <{'|'.join(leagues)}> [team|all]")
    league = sys.argv[1].lower().lstrip("/").replace("ppi-", "")
    if league not in leagues:
        sys.exit(f"Unknown league '{league}' (use one of: {', '.join(leagues)})")
    data = load(league)
    arg = " ".join(sys.argv[2:]).strip()

    if not arg:
        leaderboard(data)
    elif arg.lower() == "all":
        for t in ranked(data["teams"]):
            card(t)
    else:
        hits = find(data, arg)
        if not hits:
            print(f"\n  No {league.upper()} team matches '{arg}'. Try one of:")
            for t in ranked(data["teams"]):
                print(f"    {t['team']}")
            print()
        elif len(hits) > 1:
            print(f"\n  '{arg}' matches multiple {league.upper()} teams:")
            for t in hits:
                print(f"    {t['team']}")
            print("  Be more specific.\n")
        else:
            card(hits[0])


if __name__ == "__main__":
    main()
