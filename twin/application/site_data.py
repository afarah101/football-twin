"""The site's data: the Build's per-league-season files to the plain static site (Q23, #11).

It copies site/ and writes `data/names.json`, the name index with one entry per player whose Pool PlayerSeasons are his
season links, so a two-stint season shows as two links (D30-13), one `data/<league>_<season>.json` per league-season with
the precomputed twins and the season Fingerprint as percentiles within the league-season (D30-14), and one
`data/careers/<player_id>.json` per CareerProfile (#30). The Build's career file is split per career so no file one player
view loads tops 1 MB (D30-11). The browser only reads these files: no distance maths runs there. On the stand-in source
the site goes under build/private/site/ (D43).
"""
import json
import shutil
from pathlib import Path

from twin.application.build import CAREER_FILE
from twin.domain.twins import percentiles

ROOT = Path(__file__).resolve().parent.parent.parent
SITE = ROOT / "site"
SITE_FILES = ("index.html", "app.js", "style.css")
SITE_FOLDER = ROOT / "build" / "private" / "site"
SITE_METHOD = "euclidean"  # shortcut: the first Candidate method until #10 names the winning method, then show the winner
SMALL_SAMPLE_MINUTES = 1500  # plan: flag "small sample" below 1,500 minutes
MAX_DATA_BYTES = 1_000_000  # D30-11: no data file loaded for one player view may exceed 1 MB
CAREER_TWIN_FIELDS = ("player_id", "name", "role_group", "first_season", "last_season", "season_count", "minutes", "closeness")


def small_sample(minutes):
    return minutes < SMALL_SAMPLE_MINUTES


def site_twins(matches):
    return [
        {"player_id": found["player_id"], "name": found["name"], "league": found["league"], "season": found["season"],
         "minutes": found["minutes"], "closeness": found["closeness"], "small_sample": small_sample(found["minutes"])}
        for found in matches
    ]


def season_percentiles(player_seasons, metrics):
    """[{metric: percentile}] in `player_seasons` order: mid-rank percentiles of each z-score within the league-season (D30-14)."""
    columns = {metric: percentiles([entry["metric_profile"][metric] for entry in player_seasons]) for metric in metrics}
    return [{metric: float(columns[metric][row]) for metric in metrics} for row in range(len(player_seasons))]


def site_file(content):
    """One league-season for the browser: the shown fields, the Fingerprint percentiles and the twins of SITE_METHOD only."""
    shown = season_percentiles(content["player_seasons"], content["metrics"])
    return {
        "source": content["source"],
        "league": content["league"],
        "season": content["season"],
        "metrics": content["metrics"],
        "player_seasons": [
            {
                "player_id": entry["player_id"], "name": entry["name"], "clubs": entry["clubs"], "minutes": entry["minutes"],
                "display_position": entry["display_position"], "small_sample": small_sample(entry["minutes"]),
                "percentiles": found, "display_stats": entry["display_stats"],
                "twins": {kind: site_twins(entry["twins"][SITE_METHOD][kind]) for kind in ("all_leagues", "same_league")},
                "career": entry["career"],
            }
            for entry, found in zip(content["player_seasons"], shown)
        ],
    }


def name_index(contents, careers):
    """One entry per player (D30-13): his Pool PlayerSeasons as season links, oldest first, each stint its own link.

    A career entry carries the career's name, role group and minutes; any other sums its seasons and opens the latest."""
    seasons = {}
    for content in contents:
        for entry in content["player_seasons"]:
            seasons.setdefault(entry["player_id"], []).append({**entry, "league": content["league"], "season": content["season"]})
    by_id = {career["player_id"]: career for career in careers}
    entries = []
    for player_id, mine in seasons.items():
        mine.sort(key=lambda found: (found["season"], found["league"]))
        career = by_id.get(player_id)
        entries.append({
            "player_id": player_id,
            "name": career["name"] if career else mine[-1]["name"],
            "role_group": career["role_group"] if career else None,
            "first_season": mine[0]["season"], "last_season": mine[-1]["season"],
            "minutes": career["minutes"] if career else sum(found["minutes"] for found in mine),
            "clubs": list(dict.fromkeys(club for found in mine for club in found["clubs"])),
            "file": f"{mine[-1]['league']}_{mine[-1]['season']}.json",
            "career": career is not None,
            "player_seasons": [{"league": found["league"], "season": found["season"], "minutes": found["minutes"], "file": f"{found['league']}_{found['season']}.json"} for found in mine],
        })
    return sorted(entries, key=lambda entry: (entry["name"], entry["player_id"]))


def career_site_file(career, metrics):
    """One CareerProfile for the browser: its summary, percentiles, season links and both SITE_METHOD lists (D30-10)."""
    return {
        **{field: career[field] for field in CAREER_TWIN_FIELDS if field != "closeness"},
        "metrics": metrics,
        "percentiles": career["percentiles"],
        "player_seasons": [{**season, "file": f"{season['league']}_{season['season']}.json"} for season in career["player_seasons"]],
        "twins": {kind: [{field: twin[field] for field in CAREER_TWIN_FIELDS} for twin in career["twins"][SITE_METHOD][kind]] for kind in ("all_roles", "same_role")},
    }


def write_json(path, value):
    # allow_nan=False: a NaN fails the run here instead of breaking the browser's JSON.parse.
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(text.encode("utf8")) > MAX_DATA_BYTES:
        raise SystemExit(f"site: {path.name} would be {len(text.encode('utf8')):,} bytes, over the {MAX_DATA_BYTES:,}-byte limit (D30-11)")
    path.write_text(text, encoding="utf8")


def write_site(profile_paths, folder=SITE_FOLDER):
    """`profile_paths` are the Build's files. Returns the site folder."""
    data = folder / "data"
    if data.exists():
        shutil.rmtree(data)  # a league-season that left the Pool leaves no file behind
    data.mkdir(parents=True)
    for name in SITE_FILES:
        shutil.copyfile(SITE / name, folder / name)
    contents = [json.loads(path.read_text(encoding="utf8")) for path in profile_paths]
    for content in contents:
        write_json(data / f"{content['league']}_{content['season']}.json", site_file(content))
    built = json.loads((profile_paths[0].parent / CAREER_FILE).read_text(encoding="utf8")) if profile_paths else {"careers": []}
    write_json(data / "names.json", name_index(contents, built["careers"]))
    if profile_paths:
        (data / "careers").mkdir()
        for career in built["careers"]:
            write_json(data / "careers" / f"{career['player_id']}.json", career_site_file(career, built["metrics"]))
    return folder
