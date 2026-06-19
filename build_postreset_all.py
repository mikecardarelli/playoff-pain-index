#!/usr/bin/env python3
"""Build ppi-cities-postreset-all.json (the ALL-LEAGUES reset spec) from:

  1. ppi-cities-postreset.json   the big-four ledgers (season-by-season)
  2. /tmp/ppi_all_*.json          freshly researched ledgers for teams that are
                                  redeemed only under the all-leagues reset

In all-leagues mode a city resets on ANY league's title (incl. WNBA/MLS/CFL), so
its reset year (Yall) is >= the big-four reset year (Y4). Because Yall >= Y4, a
team that already has a big-four ledger (drought began before Y4) just needs its
seasons filtered to those after Yall; the points re-sum from the kept seasons.
Teams that become redeemed only between Y4 and Yall have no big-four ledger and
are supplied by the /tmp/ppi_all_*.json research files.

Usage: python3 build_postreset_all.py
"""
import json, re, glob, os
import ppi_cities as p

ALL_TWE = set(p.TITLE_WON_ELSEWHERE) | {"Dallas Wings"}   # 2008 title as Detroit Shock
BIG4 = {"MLB", "NBA", "NHL", "NFL"}


def ctitle(team, lc):
    if "never" in lc.lower() or team in ALL_TWE:
        return None
    ys = p._years(lc)
    if not ys:
        return None
    m = re.search(r"(\d{4})\s+season", lc)
    return int(m.group(1)) if m else max(ys)


def compare_year(season):
    """The year used to test 'strictly after the reset'. NHL/NBA 'YYYY-YY' ranges
    use the ending year (1991-92 -> 1992); single-year labels use the year."""
    s = season.strip()
    m = re.match(r"(\d{4})-(\d{2})$", s)
    if m:
        start, tail = int(m.group(1)), int(m.group(2))
        end = (start // 100) * 100 + tail
        if tail < start % 100:
            end += 100
        return end
    m = re.match(r"(\d{4})-(\d{4})$", s)
    if m:
        return int(m.group(2))
    m = re.search(r"\d{4}", s)
    return int(m.group(0)) if m else None


def reset_years():
    """{metro: (Y4, Yall)}."""
    meta = {}
    for lg in p.LEAGUES:
        for t in json.load(open(f"ppi-{lg}.json"))["teams"]:
            c = p.CITY.get(t["team"])
            if not c:
                continue
            meta.setdefault(c, []).append(
                (t["team"], lg.upper(), ctitle(t["team"], t.get("lastChampionship", ""))))
    out = {}
    for c, teams in meta.items():
        y4 = [ty for tm, lg, ty in teams if lg in BIG4 and ty is not None]
        ya = [ty for tm, lg, ty in teams if ty is not None]
        out[c] = (max(y4) if y4 else None, max(ya) if ya else None)
    return out


def refilter(rec, yall):
    """Filter a big-four ledger record to seasons strictly after `yall` and re-sum."""
    kept = [s for s in rec.get("seasons", []) if (compare_year(s["season"]) or 0) > yall]
    b = {"finals": 0, "semis": 0, "quarters": 0, "firstRound": 0, "winningRecordNoPlayoff": 0}
    for s in kept:
        if s.get("tier") in b:          # ignore 0-point 'missed'/'none' rows
            b[s["tier"]] += 1
    ppi = 16*b["finals"]+8*b["semis"]+4*b["quarters"]+2*b["firstRound"]+b["winningRecordNoPlayoff"]
    return {"postResetPPI": ppi, "breakdown": b,
            "window": f"after {yall}", "confidence": rec.get("confidence", "high"),
            "flags": rec.get("flags", []) + [f"All-leagues reset {yall}: big-four ledger filtered to seasons after {yall}."],
            "sources": rec.get("sources", []), "seasons": kept}


def main():
    big4 = json.load(open("ppi-cities-postreset.json"))["cities"]
    ry = reset_years()
    out = {}

    # 1. carry over / re-filter every big-four ledger
    for city, teams in big4.items():
        y4, yall = ry[city]
        for tm, rec in teams.items():
            if yall is not None and y4 is not None and yall > y4:
                out.setdefault(city, {})[tm] = refilter(rec, yall)
            else:
                out.setdefault(city, {})[tm] = rec        # identical reset

    # 2. merge researched all-leagues-only ledgers
    merged = []
    for f in sorted(glob.glob("/tmp/ppi_all_*.json")):
        d = json.load(open(f))
        for t in d["teams"]:
            b = t["postResetBreakdown"]
            calc = 16*b["finals"]+8*b["semis"]+4*b["quarters"]+2*b["firstRound"]+b["winningRecordNoPlayoff"]
            assert calc == t["postResetPPI"], f"{d['city']}/{t['team']} PPI mismatch {calc} vs {t['postResetPPI']}"
            out.setdefault(d["city"], {})[t["team"]] = {
                "postResetPPI": t["postResetPPI"], "breakdown": b,
                "window": t.get("window", ""), "confidence": t.get("confidence", "high"),
                "flags": t.get("flags", []), "sources": t.get("sources", []),
                "seasons": t.get("seasons", [])}
            merged.append(f"{d['city']}/{t['team']}={t['postResetPPI']}")

    json.dump({"_note": "All-leagues reset: a city resets on ANY league's title (incl. WNBA/MLS/CFL). "
                        "Teams with a big-four ledger are filtered to seasons after the all-leagues reset; "
                        "teams redeemed only under all-leagues are researched fresh (see build_postreset_all.py).",
               "cities": out}, open("ppi-cities-postreset-all.json", "w"), indent=2)
    print(f"wrote ppi-cities-postreset-all.json: {sum(len(v) for v in out.values())} team-ledgers")
    print("merged research:", ", ".join(merged) if merged else "(none yet)")


if __name__ == "__main__":
    main()
