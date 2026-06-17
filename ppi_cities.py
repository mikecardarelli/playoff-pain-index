#!/usr/bin/env python3
"""Aggregate team PPI into city/metro pain via a RANK-DISCOUNTED SUM.

The measure: sort a city's teams by PPI (most painful first), then add them up
at a diminishing rate. The most painful team counts in full, the second at
half, the third at a third, and so on:

    CityPain = p(1)*1 + p(2)/2 + p(3)/3 + ... + p(n)/n   (teams sorted desc)

Each team keeps its real PPI; the multiplier is just 1/rank. This rewards a
city for having several genuinely cursed teams but with diminishing returns,
so a 12th team barely moves the number and a single team can't fake its way to
the top. Team scores are never altered, and the rounded contributions sum to
the city total.

Every team is mapped to a metro below; suburbs fold into their major city.
The judgment calls behind those groupings are tagged in JUDGMENT.

Usage: python3 ppi_cities.py [N]   (default top 20)
"""
import json, sys

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
]

def collect():
    cities, unmapped = {}, []
    for lg in ("mlb","nba","nhl","nfl","cfl","wnba","mls"):
        for t in json.load(open(f"ppi-{lg}.json"))["teams"]:
            c = CITY.get(t["team"])
            if c is None:
                unmapped.append(t["team"]); continue
            cities.setdefault(c, []).append((t["score"], t["team"], lg.upper()))
    ranked = sorted(cities.items(), key=lambda kv: -city_pain(kv[1]))
    return ranked, unmapped


def discounted(teams):
    """Return [(real_PPI, team, league, rank, contribution)] sorted desc.
    contribution = round(PPI / rank); multiplier is 1/rank."""
    rows = []
    for r, (s, tm, lg) in enumerate(sorted(teams, reverse=True), 1):
        rows.append((s, tm, lg, r, round(s / r)))
    return rows


def city_pain(teams):
    """Rank-discounted city pain = sum of rounded per-team contributions."""
    return sum(c for *_, c in discounted(teams))


def mult_label(rank):
    return "1" if rank == 1 else f"1/{rank}"


def city_record(rank, city, teams):
    return {"rank": rank, "city": city, "pain": city_pain(teams), "teamCount": len(teams),
            "rawTotal": sum(s for s,_,_ in teams),
            "teams": [{"team": tm, "score": s, "league": lg,
                       "discountRank": r, "multiplier": mult_label(r), "contribution": c}
                      for s, tm, lg, r, c in discounted(teams)]}


def least_painful(ranked, min_teams, n=10):
    elig = [(city, teams) for city, teams in ranked if len(teams) >= min_teams]
    elig.sort(key=lambda ct: city_pain(ct[1]))   # ascending = least painful first
    return [city_record(i, city, teams) for i,(city,teams) in enumerate(elig[:n],1)]


def write_json(path="ppi-cities.json"):
    ranked, unmapped = collect()
    out = {
        "title": "Most Painful Cities",
        "measure": "Rank-discounted PPI",
        "method": "Each city's teams are sorted by PPI (most painful first), then summed at a "
                  "diminishing rate: the worst team counts in full, the second at 1/2, the third "
                  "at 1/3, and so on (contribution = round(PPI / rank)). Real team PPIs are kept; "
                  "this rewards having several cursed teams without letting a high team count win on volume.",
        "updated": "2026-06-17",
        "judgmentCalls": JUDGMENT,
        "cities": [city_record(i, city, teams) for i,(city,teams) in enumerate(ranked,1)],
        "leastPainful": {
            "minTeams3": least_painful(ranked, 3),
            "minTeams2": least_painful(ranked, 2),
        },
    }
    json.dump(out, open(path,"w"), indent=2)
    print(f"wrote {path}: {len(out['cities'])} cities" + (f" | UNMAPPED: {unmapped}" if unmapped else ""))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        write_json(); return
    if len(sys.argv) > 1 and sys.argv[1] == "--least":
        min_teams = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        ranked, _ = collect()
        print(f"\n  LEAST PAINFUL CITIES (rank-discounted PPI, min {min_teams} teams)\n")
        for rec in least_painful(ranked, min_teams):
            calc = ", ".join(f"{t['team']} {t['score']}x{t['multiplier']}={t['contribution']}" for t in rec['teams'])
            print(f"  {rec['rank']:>2}. {rec['city']:<14}{rec['pain']:>5}  [{calc}]")
        return
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    ranked, unmapped = collect()
    if unmapped:
        print("!! UNMAPPED TEAMS:", unmapped)
    print(f"\n  MOST PAINFUL CITIES  (rank-discounted PPI: worst team x1, 2nd x1/2, 3rd x1/3 ..., top {n})\n")
    print(f"  {'#':>2}  {'CITY':<16}{'PAIN':>6}{'TEAMS':>7}")
    print("  " + "-"*42)
    for i,(city,teams) in enumerate(ranked[:n],1):
        print(f"  {i:>2}. {city:<16}{city_pain(teams):>6}{len(teams):>7}")
    print("\n  Breakdown of the top 10 (PPI x multiplier = contribution):\n")
    for city,teams in ranked[:10]:
        parts = ", ".join(f"{tm} {s}x{mult_label(r)}={c}" for s, tm, lg, r, c in discounted(teams))
        print(f"  {city} ({city_pain(teams)}): {parts}")

if __name__ == "__main__":
    main()
