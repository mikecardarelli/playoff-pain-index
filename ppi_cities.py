#!/usr/bin/env python3
"""Aggregate team PPI into city/metro pain via a RANK-DISCOUNTED SUM, with a
CITY-LEVEL CHAMPIONSHIP RESET.

Base measure (rank-discounted sum). Sort a city's teams by their CITY pain (see
the reset below), then add at a diminishing rate: the worst team counts in full,
the second at 1/2, the third at 1/3, and so on (contribution = round(pain / rank)).
This rewards a city for several genuinely cursed teams without letting a high
team count win on volume.

City reset. A city's pain resets when ANY of its BIG-FOUR teams (MLB, NBA, NHL,
NFL) wins a championship, exactly the way a single team's drought resets when it
wins. The city clock starts at that title and re-accrues from the next season on.
Concretely: find the most recent year a big-four team won a title *for this city*
(titles won under a former city/identity do not count) and call it the reset
year. Each team then contributes only the PPI it has piled up in seasons AFTER
that title:
  - a team whose drought began before the reset (e.g. Minneapolis' Vikings, reset
    by the 1991 Twins) is scored season-by-season from the next season forward,
    so the Vikings' 1970s Super Bowl losses drop out but every playoff loss since
    1991 still counts. These post-reset scores are researched per season and
    stored in ppi-cities-postreset.json (POSTRESET below);
  - the reset champion and any team whose drought began at/after the reset already
    have a drought that lives entirely after the title, so their full PPI is the
    post-reset pain (no separate research needed);
  - a redeemed team with no completed season since the reset contributes 0.

Two deliberate scope choices, set with the project owner:
  - Only BIG-FOUR titles reset a city. A WNBA, MLS, or CFL title does not relieve
    the city (those teams still accrue and contribute pain, and are themselves
    re-scored from the city's last big-four title forward).
  - Post-reset scores are real, sourced, season-by-season ledgers, never estimates.
    Where a season's result could not be confirmed it is flagged in
    ppi-cities-postreset.json rather than guessed.

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
    "Dallas Wings",         # 2008 WNBA title as the Detroit Shock (all-leagues mode)
}

ALL_LEAGUES = {"MLB", "NBA", "NHL", "NFL", "CFL", "WNBA", "MLS"}


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


def _load_postreset(path):
    """{metro: {team: postResetPPI}} — sourced season-by-season pain a team has
    accrued since its city's reset title. See the JSON files for the full ledgers."""
    try:
        d = json.load(open(path))
    except FileNotFoundError:
        return {}
    return {c: {tm: rec["postResetPPI"] for tm, rec in teams.items()}
            for c, teams in d.get("cities", {}).items()}


# Two specs: big-four-only resets (default), and all-leagues resets (any title,
# incl. WNBA/MLS/CFL). Each has its own post-reset ledgers.
POSTRESET = {
    "big4": _load_postreset("ppi-cities-postreset.json"),
    "all": _load_postreset("ppi-cities-postreset-all.json"),
}
RESET_LEAGUES = {"big4": BIG_FOUR, "all": ALL_LEAGUES}


def collect(mode="big4"):
    """Build {metro: [team dicts]} with reset bookkeeping, then rank by city pain.
    mode='big4' (only MLB/NBA/NHL/NFL titles reset) or 'all' (any league's title)."""
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
        _apply_reset(metro, teams, mode)
    ranked = sorted(cities.items(), key=lambda kv: -city_pain(kv[1]))
    return ranked, unmapped


def _apply_reset(metro, teams, mode):
    """Score each team's CITY pain (post-reset) and rank-discount the city in place.
    A city resets at the most recent title won for it by a reset-eligible league
    (big-four only, or any league). Teams whose drought predates that title
    ('redeemed') count only the pain they have piled up since, taken from the
    mode's POSTRESET ledgers; every other team counts its full PPI."""
    reset_lgs = RESET_LEAGUES[mode]
    postmap = POSTRESET[mode]
    titles = [t["titleYear"] for t in teams
              if t["league"] in reset_lgs and t["titleYear"] is not None]
    reset_year = max(titles) if titles else None
    champ = None
    if reset_year is not None:
        champ = next(t["team"] for t in teams
                     if t["league"] in reset_lgs and t["titleYear"] == reset_year)
    for t in teams:
        t["resetYear"] = reset_year
        t["resetChamp"] = champ          # team whose title is the city's reset (or None)
        redeemed = (reset_year is not None
                    and t["titleYear"] != reset_year
                    and t["droughtStart"] is not None
                    and t["droughtStart"] < reset_year)
        t["redeemed"] = bool(redeemed)
        t["redeemedBy"] = f"{champ} ({reset_year})" if redeemed else None
        if redeemed:
            pr = postmap.get(metro, {}).get(t["team"])
            t["cityScore"] = pr if pr is not None else 0   # 0 = no completed season since reset
            t["postResetMissing"] = pr is None
        else:
            t["cityScore"] = t["score"]                    # full drought lives after the reset
            t["postResetMissing"] = False
    # rank ALL teams by their city (post-reset) pain, then discount by rank
    for r, t in enumerate(sorted(teams, key=lambda t: -t["cityScore"]), 1):
        t["discountRank"] = r
        t["multiplier"] = "1" if r == 1 else f"1/{r}"
        t["contribution"] = round(t["cityScore"] / r)


def city_pain(teams):
    return sum(t["contribution"] for t in teams)


def _ordered(teams):
    return sorted(teams, key=lambda t: t["discountRank"])


def city_record(rank, city, teams):
    def row(t):
        return {"team": t["team"], "league": t["league"],
                "fullPPI": t["score"], "cityScore": t["cityScore"],
                "discountRank": t["discountRank"], "multiplier": t["multiplier"],
                "contribution": t["contribution"], "redeemed": t["redeemed"],
                "resetYear": t["resetYear"], "redeemedBy": t["redeemedBy"]}
    return {"rank": rank, "city": city, "pain": city_pain(teams),
            "teamCount": len(teams), "resetYear": teams[0]["resetYear"],
            "resetChamp": teams[0]["resetChamp"],
            "rawTotal": sum(t["score"] for t in teams),
            "teams": [row(t) for t in _ordered(teams)]}


# Both tables require at least two teams in a metro (a one-team town can top either
# end by default, e.g. Hamilton's lone Tiger-Cats or a single team fresh off a title).
MIN_TEAMS = 2


def most_painful(ranked, min_teams=MIN_TEAMS, n=20):
    elig = [(c, ts) for c, ts in ranked if len(ts) >= min_teams]   # ranked is already desc
    return [city_record(i, c, ts) for i, (c, ts) in enumerate(elig[:n], 1)]


def least_painful(ranked, min_teams=MIN_TEAMS, n=10):
    elig = [(c, ts) for c, ts in ranked if len(ts) >= min_teams]
    elig.sort(key=lambda ct: city_pain(ct[1]))   # ascending = least painful first
    return [city_record(i, c, ts) for i, (c, ts) in enumerate(elig[:n], 1)]


def _method(mode):
    base = ("Each city's teams are sorted by their post-reset pain (most painful first) and "
            "summed at a diminishing rate: the worst counts in full, the second at 1/2, the "
            "third at 1/3, and so on (contribution = round(pain / rank)). A city RESETS like a "
            "team does: when a reset-eligible team wins a title for the city, the city clock "
            "restarts at that title, and each team counts only the PPI it has piled up in "
            "seasons AFTER it (a team whose drought predates the reset is re-scored "
            "season-by-season from the next season forward; the reset champion and later "
            "droughts count their full PPI). ")
    scope = ("Reset-eligible = the big four only (MLB/NBA/NHL/NFL); a WNBA/MLS/CFL title does "
             "not reset a city." if mode == "big4" else
             "Reset-eligible = ANY league, so a WNBA, MLS, or CFL title resets the city too.")
    return base + scope


def write_json(mode="big4", path=None):
    path = path or ("ppi-cities.json" if mode == "big4" else "ppi-cities-all.json")
    ranked, unmapped = collect(mode)
    out = {
        "title": "Most Painful Cities",
        "mode": mode,
        "measure": ("Rank-discounted post-reset PPI (big-four reset)" if mode == "big4"
                    else "Rank-discounted post-reset PPI (all-leagues reset)"),
        "method": _method(mode),
        "updated": "2026-06-18",
        "tableMinTeams": MIN_TEAMS,   # both published tables require >= this many teams
        "judgmentCalls": JUDGMENT,
        "cities": [city_record(i, c, ts) for i, (c, ts) in enumerate(ranked, 1)],
        "mostPainful": most_painful(ranked),
        "leastPainful": {
            "minTeams3": least_painful(ranked, 3),
            "minTeams2": least_painful(ranked, 2),
        },
    }
    json.dump(out, open(path, "w"), indent=2)
    print(f"wrote {path}: {len(out['cities'])} cities"
          + (f" | UNMAPPED: {unmapped}" if unmapped else ""))


def _team_calc(t, html=False):
    """One team's contribution string. Redeemed teams note their full PPI + reset."""
    times = "&times;" if html else "x"
    full = t.get("fullPPI", t.get("score"))
    s = f"{t['team']} {t['cityScore']}{times}{t['multiplier']}={t['contribution']}"
    if t["redeemed"]:
        note = f"since {t['resetYear']}; was {full}"
        s += f" <em>({note})</em>" if html else f" ({note})"
    return s


def _calc_str(teams):
    return ", ".join(_team_calc(t) for t in _ordered(teams))


def last_champ_note(rec, mode):
    """Human label for the city's last (reset-eligible) championship."""
    if rec["resetYear"]:
        return f'last title: {rec["resetChamp"]} ({rec["resetYear"]})'
    return "no big-four title yet" if mode == "big4" else "no title yet"


def _html_rows(records, mode="big4"):
    rows = []
    for rec in records:
        teamstr = ", ".join(_team_calc(t, html=True) for t in rec["teams"])
        note = last_champ_note(rec, mode)
        rows.append(
            '                <tr>\n'
            f'                    <td class="rank">#{rec["rank"]}</td>\n'
            f'                    <td><span class="city-name">{rec["city"]}</span> '
            f'<span class="last-champ">&middot; {note}</span><br>'
            f'<span class="teams">{teamstr}</span></td>\n'
            f'                    <td class="pain">{rec["pain"]}</td>\n'
            '                </tr>')
    return "\n".join(rows)


def _mode_arg(default="big4"):
    return "all" if "--all" in sys.argv else default


def main():
    if "--json" in sys.argv:
        write_json("big4"); write_json("all"); return
    if "--html" in sys.argv:
        mode = _mode_arg()
        ranked, _ = collect(mode)
        print(f"<!-- MOST PAINFUL ({mode}, min 2 teams) -->")
        print(_html_rows(most_painful(ranked), mode))
        print(f"\n<!-- LEAST PAINFUL ({mode}, min 2 teams) -->")
        print(_html_rows(least_painful(ranked), mode))
        return
    if "--least" in sys.argv:
        mode = _mode_arg()
        ranked, _ = collect(mode)
        print(f"\n  LEAST PAINFUL CITIES ({mode}, min 2 teams)\n")
        for rec in least_painful(ranked, 2):
            calc = ", ".join(_team_calc(t) for t in rec["teams"])
            print(f"  {rec['rank']:>2}. {rec['city']:<14}{rec['pain']:>5}  [{calc}]")
        return
    mode = _mode_arg()
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    n = int(nums[0]) if nums else 20
    ranked, unmapped = collect(mode)
    if unmapped:
        print("!! UNMAPPED TEAMS:", unmapped)
    print(f"\n  MOST PAINFUL CITIES  ({mode} reset, top {n})\n")
    print(f"  {'#':>2}  {'CITY':<16}{'PAIN':>6}{'TEAMS':>7}")
    print("  " + "-"*42)
    for i, (city, teams) in enumerate(ranked[:n], 1):
        print(f"  {i:>2}. {city:<16}{city_pain(teams):>6}{len(teams):>7}")
    print("\n  Breakdown of the top 12:\n")
    for city, teams in ranked[:12]:
        print(f"  {city} ({city_pain(teams)}): {_calc_str(teams)}")


if __name__ == "__main__":
    main()
