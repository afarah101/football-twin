"""The site's data: the Build's per-league-season files to the plain static site (Q23, #11).

It copies site/ and writes `data/names.json`, the name index with one entry per Pool PlayerSeason, so a two-stint player
shows twice, one `data/<league>_<season>.json` per league-season with the precomputed twins, and one
`data/careers/<player_id>.json` per CareerProfile (#30). The Build's career file is split per career so no file one player
view loads tops 1 MB (D30-11). The browser only reads these files: no distance maths runs there. On the stand-in source
the site goes under build/private/site/ (D43).
"""
import json
import shutil
from pathlib import Path

from twin.application.build import CAREER_FILE

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


def site_file(content):
    """One league-season for the browser: the shown fields and the twins of SITE_METHOD only."""
    return {
        "source": content["source"],
        "league": content["league"],
        "season": content["season"],
        "metrics": content["metrics"],
        "player_seasons": [
            {
                "player_id": entry["player_id"], "name": entry["name"], "clubs": entry["clubs"], "minutes": entry["minutes"],
                "display_position": entry["display_position"], "small_sample": small_sample(entry["minutes"]),
                "metric_profile": entry["metric_profile"], "display_stats": entry["display_stats"],
                "twins": {kind: site_twins(entry["twins"][SITE_METHOD][kind]) for kind in ("all_leagues", "same_league")},
                "career": entry["career"],
            }
            for entry in content["player_seasons"]
        ],
    }


def name_index(contents):
    entries = [
        {"player_id": entry["player_id"], "name": entry["name"], "league": content["league"], "season": content["season"],
         "clubs": entry["clubs"], "minutes": entry["minutes"], "file": f"{content['league']}_{content['season']}.json", "career": entry["career"]}
        for content in contents for entry in content["player_seasons"]
    ]
    return sorted(entries, key=lambda entry: (entry["name"], entry["season"], entry["league"], entry["player_id"]))


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
    write_json(data / "names.json", name_index(contents))
    if profile_paths:
        built = json.loads((profile_paths[0].parent / CAREER_FILE).read_text(encoding="utf8"))
        (data / "careers").mkdir()
        for career in built["careers"]:
            write_json(data / "careers" / f"{career['player_id']}.json", career_site_file(career, built["metrics"]))
    return folder
