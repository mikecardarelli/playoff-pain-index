#!/usr/bin/env python3
"""Aggregate team PPI into city/metro pain via a RANK-DISCOUNTED SUM, with a
CITY-LEVEL CHAMPIONSHIP RESET.

Base measure (rank-discounted sum). Sort a city's teams by PPI (most painful
first), then add them at a diminishing rate: the worst team counts in full, the
second at 1/2, the third at 1/3, and so on (contribution = round(PPI / rank)).
This rewards a city for several genuinely cursed teams without letting a high
team count win on volume.

City reset (new). A city's pain resets when ANY of its BIG-FOUR teams (MLB, NBA,
NHL, NFL) wins a championship, exactly the way a single team's drought resets
when it wins. Concretely: find the most recent year a big-four team won a title
*for this city* (titles won under a former city/identity do not count). Any team
whose own drought began before that title was made whole by it, so it is
"redeemed": it contributes 0 to the city total. Redeemed teams KEEP their full,
real PPI in their row (nothing is zeroed or pro-rated); they simply stop counting
toward the city until they suffer anew. The most recent champion and every team
whose drought began at/after that title still count, at full PPI.

Two deliberate scope choices, set with the project owner:
  - Only BIG-FOUR titles reset a city. A WNBA, MLS, or CFL title does not relieve
    the city (those teams still accrue and contribute pain, and can still be
    redeemed by a big-four title).
  - Redeemed teams keep their full PPI on display. Because the dataset stores each
    team's TOTAL drought pain and not a season-by-season ledger, the pain a
    redeemed team has accrued SINCE the city's last title cannot be isolated, so
    it is counted as 0 rather than fabricated. This UNDERSTATES those teams and is
    flagged per row (redeemed=true). An honest gap beats an invented number.

Every team is mapped to a metro below; suburbs fold into their major city. The
judgment calls behind those groupings are tagged in JUDGMENT.

Usage: python3 ppi_cities.py [N]      most painful, top N (default 20)
       python3 ppi_cities.py --least [min_teams]
       python3 ppi_cities.py --json    (re)write ppi-cities.json
       python3 ppi_cities.py --html    print index.html table rows
"""
import json, re, sys

LEAGUES = ("mlb", "nba", "nhl", "nfl", "cfl", "wnba", "mls")
BIG_FOUR = {"MLB", "NBA", "NHL", "NFL"}

# team (exact name) -> metro
CITY = {
    # New York metro (incl. New Jersey + Long Island)
    "New York Yankees":"New York","New York Mets":"New York","New York Knicks":"New York",
    "Brooklyn Nets":"New York","New York Rangers":"New York","New York Islanders":"New York",
    "New Jersey Devils":"New York","New York Giants":"New York","New York Jets":"New York",
    "New York City FC":"New York","New York Red Bulls":"New York","New York Liberty":"New York",
    # Los Angeles metro (incl. Anaheim)
    "Los Angeles Dodgers":"Los Angeles","Los Angeles Angels":"Los Angeles","Los Angeles Lakers":"Los Angeles",
    "LA Clippers":"Los Angeles","Los Angeles Kings":"Los Angeles","Los Angeles Rams":"Los Angeles",
    "Los Angeles Chargers":"Los Angeles","Los Angeles FC":"Los Angeles","LA Galaxy":"Los Angeles",
    "Los Angeles Sparks":"Los Angeles","Anaheim Ducks":"Los Angeles",
    # San Francisco Bay Area (SF + San Jose + Santa Clara)
    "San Francisco Giants":"Bay Area","Golden State Warriors":"Bay Area","Golden State Valkyries":"Bay Area",
    "San Francisco 49ers":"Bay Area","San Jose Sharks":"Bay Area","San Jose Earthquakes":"Bay Area",
    # Chicago
    "Chicago Cubs":"Chicago","Chicago White Sox":"Chicago","Chicago Bulls":"Chicago",
    "Chicago Blackhawks":"Chicago","Chicago Bears":"Chicago","Chicago Sky":"Chicago","Chicago Fire FC":"Chicago",
    # Dallas-Fort Worth (Arlington + Frisco)
    "Texas Rangers":"Dallas","Dallas Cowboys":"Dallas","Dallas Mavericks":"Dallas",
    "Dallas Stars":"Dallas","FC Dallas":"Dallas","Dallas Wings":"Dallas",
    # Boston (Foxborough folds in)
    "Boston Red Sox":"Boston","Boston Celtics":"Boston","Boston Bruins":"Boston",
    "New England Patriots":"Boston","New England Revolution":"Boston",
    # Philadelphia (Chester folds in)
    "Philadelphia Phillies":"Philadelphia","Philadelphia 76ers":"Philadelphia",
    "Philadelphia Flyers":"Philadelphia","Philadelphia Eagles":"Philadelphia","Philadelphia Union":"Philadelphia",
    # Washington DC (Landover folds in)
    "Washington Nationals":"Washington","Washington Wizards":"Washington","Washington Capitals":"Washington",
    "Washington Commanders":"Washington","Washington Mystics":"Washington","D.C. United":"Washington",
    # Toronto
    "Toronto Blue Jays":"Toronto","Toronto Raptors":"Toronto","Toronto Maple Leafs":"Toronto",
    "Toronto Argonauts":"Toronto","Toronto FC":"Toronto","Toronto Tempo":"Toronto",
    # Minneapolis / Twin Cities
    "Minnesota Twins":"Minneapolis","Minnesota Timberwolves":"Minneapolis","Minnesota Wild":"Minneapolis",
    "Minnesota Vikings":"Minneapolis","Minnesota Lynx":"Minneapolis","Minnesota United FC":"Minneapolis",
    # Denver
    "Colorado Rockies":"Denver","Denver Nuggets":"Denver","Colorado Avalanche":"Denver",
    "Denver Broncos":"Denver","Colorado Rapids":"Denver",
    # Miami / South Florida (Sunrise + Fort Lauderdale fold in)
    "Miami Marlins":"Miami","Miami Heat":"Miami","Miami Dolphins":"Miami",
    "Florida Panthers":"Miami","Inter Miami CF":"Miami",
    # Atlanta
    "Atlanta Braves":"Atlanta","Atlanta Hawks":"Atlanta","Atlanta Falcons":"Atlanta",
    "Atlanta Dream":"Atlanta","Atlanta United FC":"Atlanta",
    # Phoenix (Arizona teams, Glendale folds in)
    "Arizona Diamondbacks":"Phoenix","Phoenix Suns":"Phoenix","Arizona Cardinals":"Phoenix","Phoenix Mercury":"Phoenix",
    # Pittsburgh / Detroit / Houston / Cleveland / Seattle / Cincinnati / St. Louis
    "Pittsburgh Pirates":"Pittsburgh","Pittsburgh Penguins":"Pittsburgh","Pittsburgh Steelers":"Pittsburgh",
    "Detroit Tigers":"Detroit","Detroit Pistons":"Detroit","Detroit Red Wings":"Detroit","Detroit Lions":"Detroit",
    "Houston Astros":"Houston","Houston Rockets":"Houston","Houston Texans":"Houston","Houston Dynamo":"Houston",
    "Cleveland Guardians":"Cleveland","Cleveland Cavaliers":"Cleveland","Cleveland Browns":"Cleveland",
    "Seattle Mariners":"Seattle","Seattle Seahawks":"Seattle","Seattle Kraken":"Seattle",
    "Seattle Storm":"Seattle","Seattle Sounders FC":"Seattle",
    "Cincinnati Reds":"Cincinnati","Cincinnati Bengals":"Cincinnati","FC Cincinnati":"Cincinnati",
    "St. Louis Cardinals":"St. Louis","St. Louis Blues":"St. Louis","St. Louis City SC":"St. Louis",
    # Tampa Bay (St. Petersburg + Tampa)
    "Tampa Bay Rays":"Tampa Bay","Tampa Bay Lightning":"Tampa Bay","Tampa Bay Buccaneers":"Tampa Bay",
    # Charlotte (Carolina Panthers = Charlotte)
    "Charlotte Hornets":"Charlotte","Carolina Panthers":"Charlotte","Charlotte FC":"Charlotte",
    # Indianapolis (Indiana teams)
    "Indiana Pacers":"Indianapolis","Indianapolis Colts":"Indianapolis","Indiana Fever":"Indianapolis",
    # Nashville (Tennessee Titans = Nashville)
    "Nashville Predators":"Nashville","Tennessee Titans":"Nashville","Nashville SC":"Nashville",
    # Salt Lake City (Utah teams)
    "Utah Jazz":"Salt Lake City","Utah Mammoth":"Salt Lake City","Real Salt Lake":"Salt Lake City",
    # Smaller / single-cluster metros
    "Milwaukee Brewers":"Milwaukee","Milwaukee Bucks":"Milwaukee",
    "Buffalo Bills":"Buffalo","Buffalo Sabres":"Buffalo",
    "Kansas City Royals":"Kansas City","Kansas City Chiefs":"Kansas City","Sporting Kansas City":"Kansas City",
    "Portland Trail Blazers":"Portland","Portland Timbers":"Portland","Portland Fire":"Portland",
    "Baltimore Orioles":"Baltimore","Baltimore Ravens":"Baltimore",
    "Las Vegas Raiders":"Las Vegas","Vegas Golden Knights":"Las Vegas","Las Vegas Aces":"Las Vegas",
    "San Diego Padres":"San Diego","San Diego FC":"San Diego",
    "Columbus Blue Jackets":"Columbus","Columbus Crew":"Columbus",
    "New Orleans Pelicans":"New Orleans","New Orleans Saints":"New Orleans",
    "Orlando Magic":"Orlando","Orlando City SC":"Orlando",
    "San Antonio Spurs":"San Antonio","Memphis Grizzlies":"Memphis",
    "Oklahoma City Thunder":"Oklahoma City","Green Bay Packers":"Green Bay","Jacksonville Jaguars":"Jacksonville",
    "Sacramento Kings":"Sacramento","Athletics":"Sacramento",
    "Austin FC":"Austin","Connecticut Sun":"Connecticut",
    # Canadian metros
    "Montreal Canadiens":"Montreal","Montreal Alouettes":"Montreal","CF Montreal":"Montreal",
    "Vancouver Canucks":"Vancouver","Vancouver Whitecaps FC":"Vancouver","BC Lions":"Vancouver",
    "Calgary Flames":"Calgary","Calgary Stampeders":"Calgary",
    "Edmonton Oilers":"Edmonton","Edmonton Elks":"Edmonton",
    "Winnipeg Jets":"Winnipeg","Winnipeg Blue Bombers":"Winnipeg",
    "Ottawa Senators":"Ottawa","Ottawa Redblacks":"Ottawa",
    "Hamilton Tiger-Cats":"Hamilton","Saskatchewan Roughriders":"Regina",
    "Carolina Hurricanes":"Raleigh",
}

# Judgment calls that meaningfully move the ranking (shown to the user).
JUDGMENT = [
    "New Jersey + Long Island count as New York (Devils, Red Bulls, Giants, Jets, Islanders).",
    "Anaheim counts as Los Angeles (Angels, Ducks).",
    "Bay Area merges SF + San Jose + Santa Clara (Giants/Warriors/Valkyries + Sharks/Earthquakes/49ers).",
    "Athletics mapped to Sacramento (their 2025 interim home) alongside the Kings.",
    "Hamilton kept SEPARATE from Toronto (it is its own CFL market, ~70km away).",
    "Connecticut Sun kept as its own market (not New York or Boston).",
    "BC Lions count as Vancouver; Carolina Panthers/Hornets/Charlotte FC as Charlotte; Carolina Hurricanes as Raleigh (separate).",
    "City reset uses BIG-FOUR titles only (MLB/NBA/NHL/NFL); a WNBA/MLS/CFL title does not reset a city.",
]

# Big-four teams whose most recent championship was won under a FORMER city or
# identity, so it does NOT count as a title for their current metro and does not
# reset that city. (Relocations / pre-merger oddities. Verified against each
# team's lastChampionship string.)
TITLE_WON_ELSEWHERE = {
    "Athletics",            # 1989 World Series won in Oakland; interim home now Sacramento
    "Atlanta Hawks",        # 1958 NBA title as the St. Louis Hawks
    "Sacramento Kings",     # 1951 NBA title as the Rochester Royals
    "Brooklyn Nets",        # 1976 ABA title as the New York Nets (and ABA, pre-Brooklyn)
    "Tennessee Titans",     # 1961 AFL title as the Houston Oilers
    "Arizona Cardinals",    # 1947 NFL title as the Chicago Cardinals
    "Los Angeles Chargers", # 1963 AFL title as the San Diego Chargers
    "Las Vegas Raiders",    # 1983 NFL title as the Los Angeles Raiders
}


def _years(text):
    """All four-digit years in text, with two-digit range tails resolved.
    'Since last title in 1974-75' -> [1975]; '1999 (1998 ...)' -> [1999, 1998]."""
    out = []
    for m in re.finditer(r"(\d{4})(?:-(\d{2}))?", text):
        y = int(m.group(1))
        if m.group(2) is not None:                 # range like 1974-75 / 1999-00
            tail = int(m.group(2))
            y = (y // 100) * 100 + tail
            if tail < (int(m.group(1)) % 100):     # century rollover (1999-00 -> 2000)
                y += 100
        out.append(y)
    return out


def drought_start(since):
    """Year a team's current drought began = the most recent year named in `since`
    (older parentheticals reference history)."""
    ys = _years(since)
    return max(ys) if ys else None


def city_title_year(team, last_champ):
    """Year this team last won a title FOR ITS CURRENT CITY, or None.
    None when the team never won, or won under a former city/identity."""
    if "never" in last_champ.lower():
        return None
    if team in TITLE_WON_ELSEWHERE:
        return None
    ys = _years(last_champ)
    if not ys:
        return None
    m = re.search(r"(\d{4})\s+season", last_champ)   # prefer the "(YYYY season)" tag
    return int(m.group(1)) if m else max(ys)


def collect():
    """Build {metro: [team dicts]} with reset bookkeeping, then rank by city pain."""
    cities, unmapped = {}, []
    for lg in LEAGUES:
        for t in json.load(open(f"ppi-{lg}.json"))["teams"]:
            metro = CITY.get(t["team"])
            if metro is None:
                unmapped.append(t["team"]); continue
            cities.setdefault(metro, []).append({
                "team": t["team"], "score": t["score"], "league": lg.upper(),
                "droughtStart": drought_start(t.get("since", "")),
                "titleYear": city_title_year(t["team"], t.get("lastChampionship", "")),
            })
    for metro, teams in cities.items():
        _apply_reset(metro, teams)
    ranked = sorted(cities.items(), key=lambda kv: -city_pain(kv[1]))
    return ranked, unmapped


def _apply_reset(metro, teams):
    """Mark each team redeemed/not and compute its city contribution in place.
    A city resets at the most recent big-four title won for it; any team whose
    drought predates that title is redeemed (contributes 0, full PPI retained)."""
    big4_titles = [t["titleYear"] for t in teams
                   if t["league"] in BIG_FOUR and t["titleYear"] is not None]
    reset_year = max(big4_titles) if big4_titles else None
    # which big-four team(s) supplied the reset, for the human-readable note
    champ = None
    if reset_year is not None:
        champ = next(t["team"] for t in teams
                     if t["league"] in BIG_FOUR and t["titleYear"] == reset_year)
    for t in teams:
        t["resetYear"] = reset_year
        t["redeemedBy"] = None
        redeemed = (reset_year is not None
                    and t["titleYear"] != reset_year
                    and t["droughtStart"] is not None
                    and t["droughtStart"] < reset_year)
        t["redeemed"] = bool(redeemed)
        if redeemed:
            t["redeemedBy"] = f"{champ} ({reset_year})"
    # rank only the live (non-redeemed) teams; redeemed contribute 0
    live = sorted([t for t in teams if not t["redeemed"]],
                  key=lambda t: -t["score"])
    for r, t in enumerate(live, 1):
        t["discountRank"] = r
        t["multiplier"] = "1" if r == 1 else f"1/{r}"
        t["contribution"] = round(t["score"] / r)
    for t in teams:
        if t["redeemed"]:
            t["discountRank"] = None
            t["multiplier"] = "0"
            t["contribution"] = 0


def city_pain(teams):
    return sum(t["contribution"] for t in teams)


def _ordered(teams):
    """Live teams by rank, then redeemed teams by PPI (for display)."""
    live = [t for t in teams if not t["redeemed"]]
    dead = [t for t in teams if t["redeemed"]]
    live.sort(key=lambda t: t["discountRank"])
    dead.sort(key=lambda t: -t["score"])
    return live, dead


def city_record(rank, city, teams):
    live, dead = _ordered(teams)
    def row(t):
        return {"team": t["team"], "score": t["score"], "league": t["league"],
                "discountRank": t["discountRank"], "multiplier": t["multiplier"],
                "contribution": t["contribution"], "redeemed": t["redeemed"],
                "redeemedBy": t["redeemedBy"]}
    return {"rank": rank, "city": city, "pain": city_pain(teams),
            "teamCount": len(teams), "liveCount": len(live),
            "resetYear": teams[0]["resetYear"],
            "rawTotal": sum(t["score"] for t in teams),
            "teams": [row(t) for t in live + dead]}


def least_painful(ranked, min_teams, n=10):
    elig = [(c, ts) for c, ts in ranked if len(ts) >= min_teams]
    elig.sort(key=lambda ct: city_pain(ct[1]))   # ascending = least painful first
    return [city_record(i, c, ts) for i, (c, ts) in enumerate(elig[:n], 1)]


METHOD = ("Each city's teams are sorted by PPI (most painful first) and summed at a "
          "diminishing rate: the worst team counts in full, the second at 1/2, the third "
          "at 1/3, and so on (contribution = round(PPI / rank)). A city then RESETS like a "
          "team does: when any big-four team (MLB/NBA/NHL/NFL) wins a title for the city, "
          "every team whose drought began before that title is 'redeemed' and contributes "
          "0 until it suffers anew. Redeemed teams keep their full PPI on display; because "
          "the dataset is not season-by-season, their post-title pain cannot be isolated and "
          "is counted as 0 rather than estimated. WNBA/MLS/CFL titles do not reset a city.")


def write_json(path="ppi-cities.json"):
    ranked, unmapped = collect()
    out = {
        "title": "Most Painful Cities",
        "measure": "Rank-discounted PPI with a big-four city championship reset",
        "method": METHOD,
        "updated": "2026-06-18",
        "judgmentCalls": JUDGMENT,
        "cities": [city_record(i, c, ts) for i, (c, ts) in enumerate(ranked, 1)],
        "leastPainful": {
            "minTeams3": least_painful(ranked, 3),
            "minTeams2": least_painful(ranked, 2),
        },
    }
    json.dump(out, open(path, "w"), indent=2)
    print(f"wrote {path}: {len(out['cities'])} cities"
          + (f" | UNMAPPED: {unmapped}" if unmapped else ""))


def _calc_str(teams):
    live, dead = _ordered(teams)
    parts = [f"{t['team']} {t['score']}x{t['multiplier']}={t['contribution']}" for t in live]
    if dead:
        champ = dead[0]["redeemedBy"]
        names = ", ".join(f"{t['team']} {t['score']}" for t in dead)
        parts.append(f"reset by {champ}: {names} (->0)")
    return ", ".join(parts)


def _html_rows(records):
    rows = []
    for rec in records:
        live = [t for t in rec["teams"] if not t["redeemed"]]
        spans = [f"{t['team']} {t['score']}&times;{t['multiplier'].replace('1/','1/')}={t['contribution']}"
                 for t in live]
        dead = [t for t in rec["teams"] if t["redeemed"]]
        teamstr = ", ".join(spans)
        if dead:
            champ = dead[0]["redeemedBy"]
            names = ", ".join(f"{t['team']} {t['score']}" for t in dead)
            teamstr += f" &middot; <em>reset by {champ}: {names} &rarr; 0</em>"
        rows.append(
            '                <tr>\n'
            f'                    <td class="rank">#{rec["rank"]}</td>\n'
            f'                    <td><span class="city-name">{rec["city"]}</span><br>'
            f'<span class="teams">{teamstr}</span></td>\n'
            f'                    <td class="pain">{rec["pain"]}</td>\n'
            '                </tr>')
    return "\n".join(rows)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        write_json(); return
    if len(sys.argv) > 1 and sys.argv[1] == "--html":
        ranked, _ = collect()
        most = [city_record(i, c, ts) for i, (c, ts) in enumerate(ranked, 1)][:20]
        print("<!-- MOST PAINFUL -->")
        print(_html_rows(most))
        print("\n<!-- LEAST PAINFUL (min 2 teams) -->")
        print(_html_rows(least_painful(ranked, 2)))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--least":
        min_teams = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        ranked, _ = collect()
        print(f"\n  LEAST PAINFUL CITIES (rank-discounted PPI w/ reset, min {min_teams} teams)\n")
        for rec in least_painful(ranked, min_teams):
            print(f"  {rec['rank']:>2}. {rec['city']:<14}{rec['pain']:>5}  [{_calc_str_rec(rec)}]")
        return
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    ranked, unmapped = collect()
    if unmapped:
        print("!! UNMAPPED TEAMS:", unmapped)
    print(f"\n  MOST PAINFUL CITIES  (rank-discounted PPI with big-four reset, top {n})\n")
    print(f"  {'#':>2}  {'CITY':<16}{'PAIN':>6}{'LIVE':>6}{'TEAMS':>7}")
    print("  " + "-"*48)
    for i, (city, teams) in enumerate(ranked[:n], 1):
        live = sum(1 for t in teams if not t["redeemed"])
        print(f"  {i:>2}. {city:<16}{city_pain(teams):>6}{live:>6}{len(teams):>7}")
    print("\n  Breakdown of the top 12:\n")
    for city, teams in ranked[:12]:
        print(f"  {city} ({city_pain(teams)}): {_calc_str(teams)}")


def _calc_str_rec(rec):
    live = [t for t in rec["teams"] if not t["redeemed"]]
    parts = [f"{t['team']} {t['score']}x{t['multiplier']}={t['contribution']}" for t in live]
    dead = [t for t in rec["teams"] if t["redeemed"]]
    if dead:
        parts.append(f"reset by {dead[0]['redeemedBy']}: " +
                     ", ".join(f"{t['team']} {t['score']}" for t in dead) + " (->0)")
    return ", ".join(parts)


if __name__ == "__main__":
    main()
