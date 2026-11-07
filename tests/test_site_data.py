"""The site's data (#11): the Build's files on tests/fixtures/standin/loader_sample/ in, the static site's files out.

The sample's Pool is 30 real PlayerSeasons. It holds no player with two stints in the Pool in one season (Ben Brereton
2023/24 has 1,105 Premier League minutes but 23 in La Liga), so the two-stint case also runs once on data/standin/, where
Philippe Coutinho 2017/18 holds both stints. On-screen texts are copied word for word from docs/phase-1-plan.md and
Ahmed's decisions of 7 Nov 2026.
Run from the repo root: python3 -m unittest discover tests
"""
import json
import re
import sys
import unittest
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_build import loaded
from twin.application import build, site_data
from twin.domain.pool import in_pool

ON_SCREEN_LINE = "Matches how they shoot and create, not how they move."  # plan:9
STYLE_LABEL = "style twin, not level twin"  # plan:36
SMALL_SAMPLE = "small sample"  # plan:20, below 1,500 minutes
DATA_TO = "Data to 2023/24"  # plan:119
CREDIT = "Shot and xG data: Understat"  # Ahmed, 7 Nov 2026, with "Understat" linked to https://understat.com
CREDIT_LINK = '<a href="https://understat.com">Understat</a>'
TAKEDOWN = "Takedown contact: [TO BE ADDED BEFORE LAUNCH]"  # Ahmed, 7 Nov 2026: a placeholder until #13
CLOSENESS = "of all pairs"  # issue #11: "closer than X% of all pairs"
SITE_TWIN_KEYS = {"player_id", "name", "league", "season", "minutes", "closeness", "small_sample"}


def site_of(source):
    """The Build, then the site, into a temporary build folder: {path under the site folder: text}."""
    with TemporaryDirectory() as folder:
        paths = build.run(source, Path(folder))
        site = site_data.write_site(paths, Path(folder) / "private" / "site")
        return {path.relative_to(site).as_posix(): path.read_text(encoding="utf8") for path in site.rglob("*") if path.is_file()}


@lru_cache(maxsize=None)
def sample_site():
    return site_of(loaded())


def names():
    return json.loads(sample_site()["data/names.json"])


def data_files():
    return {path: json.loads(text) for path, text in sample_site().items() if path.startswith("data/") and path != "data/names.json"}


class NameIndex(unittest.TestCase):
    def test_name_index_holds_each_pool_player_season_once(self):
        pool = {found.key: found for found in loaded().player_seasons if in_pool(found)}
        keys = [(entry["league"], entry["season"], entry["player_id"]) for entry in names()]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), set(pool))
        for entry in names():
            found = pool[(entry["league"], entry["season"], entry["player_id"])]
            self.assertEqual((entry["name"], entry["minutes"], entry["clubs"]), (found.name, found.minutes, list(found.clubs)))
            listed = {player["player_id"] for player in data_files()[f"data/{entry['file']}"]["player_seasons"]}
            self.assertIn(entry["player_id"], listed)
        # Real: Mohamed Salah holds two Pool seasons in the sample (2017/18 and 2023/24), so search shows two entries.
        self.assertEqual(sorted(entry["season"] for entry in names() if entry["name"] == "Mohamed Salah"), [2017, 2023])

    def test_a_stint_out_of_the_pool_is_not_in_the_name_index(self):
        # Real: Ben Brereton 2023/24, Premier League stint in the Pool, La Liga stint 23 minutes. Stints are never merged.
        stints = sorted(found.league for found in loaded().player_seasons if found.player_id == "57827369" and found.season == 2023)
        self.assertEqual(stints, ["ENG", "ESP"])
        self.assertEqual([(entry["league"], entry["minutes"]) for entry in names() if entry["player_id"] == "57827369"], [("ENG", 1105)])

    def test_real_two_stint_player_shows_as_two_player_seasons_on_data_standin(self):
        # Real, on data/standin/: Philippe Coutinho 2017/18, Liverpool then Barcelona. The sample holds no such case.
        from twin.infrastructure.standin.loader import StandinLoader

        full = json.loads(site_of(StandinLoader().load())["data/names.json"])
        coutinho = sorted((entry["league"], entry["season"], entry["minutes"], entry["file"]) for entry in full if entry["name"] == "Philippe Coutinho" and entry["season"] == 2017)
        self.assertEqual(coutinho, [("ENG", 2017, 1109, "ENG_2017.json"), ("ESP", 2017, 1296, "ESP_2017.json")])


class TwinsData(unittest.TestCase):
    def test_every_list_stores_10_twins_from_the_build(self):
        with TemporaryDirectory() as folder:
            built = {(content["league"], content["season"], entry["player_id"]): entry["twins"][site_data.SITE_METHOD]
                     for path in build.run(loaded(), Path(folder)) for content in [json.loads(path.read_text(encoding="utf8"))] for entry in content["player_seasons"]}
        for path, content in data_files().items():
            for entry in content["player_seasons"]:
                lists = entry["twins"]
                self.assertEqual(set(lists), {"all_leagues", "same_league"}, path)
                self.assertEqual(len(lists["all_leagues"]), 10, (path, entry["name"]))
                source = built[(content["league"], content["season"], entry["player_id"])]
                for kind in ("all_leagues", "same_league"):
                    self.assertEqual([found["player_id"] for found in lists[kind]], [found["player_id"] for found in source[kind]])
                    for found in lists[kind]:
                        self.assertEqual(set(found), SITE_TWIN_KEYS)
                        self.assertEqual(found["small_sample"], found["minutes"] < 1500)

    def test_small_sample_flag_marks_player_seasons_under_1500_minutes(self):
        flagged = {(entry["name"], content["season"]): entry["small_sample"] for content in data_files().values() for entry in content["player_seasons"]}
        self.assertTrue(flagged[("Darwin Núñez", 2023)])  # real: 934 minutes, ENG 2023/24
        self.assertFalse(flagged[("Mohamed Salah", 2017)])  # real: 2,907 minutes
        for content in data_files().values():
            for entry in content["player_seasons"]:
                self.assertEqual(entry["small_sample"], entry["minutes"] < site_data.SMALL_SAMPLE_MINUTES)


class SiteFiles(unittest.TestCase):
    def test_every_on_screen_text_from_the_spec_is_in_the_site(self):
        page = sample_site()["index.html"]
        for text in (ON_SCREEN_LINE, STYLE_LABEL, DATA_TO, TAKEDOWN):
            self.assertIn(text, page)
        self.assertIn(f"Shot and xG data: {CREDIT_LINK}", page)
        self.assertIn(CREDIT, re.sub(r"<[^>]+>", "", page))
        script = sample_site()["app.js"]
        self.assertIn(SMALL_SAMPLE, script)
        self.assertIn("closer than", script)
        self.assertIn(CLOSENESS, script)

    def test_no_framework_and_no_distance_maths_in_the_browser(self):
        page, script = sample_site()["index.html"], sample_site()["app.js"]
        self.assertEqual(re.findall(r"<script[^>]*>", page), ['<script src="app.js">'])
        self.assertEqual(re.findall(r'<link[^>]*rel="stylesheet"[^>]*>', page), ['<link rel="stylesheet" href="style.css">'])
        # The SVG namespace is a name, not a request, so it is the one URL allowed.
        self.assertNotRegex(script.replace('"http://www.w3.org/2000/svg"', ""), r"\bimport\b|\brequire\(|https?://")
        self.assertNotRegex(script, r"Math\.(sqrt|hypot|pow)|\*\*")
        self.assertEqual(sorted(path for path in sample_site() if not path.startswith("data/")), ["app.js", "index.html", "style.css"])
        for content in data_files().values():
            self.assertNotIn("distance", json.dumps(content))
            self.assertNotIn("metric_profile", json.dumps(content["player_seasons"][0]["twins"]))

    def test_standin_site_goes_under_build_private(self):
        self.assertEqual(site_data.SITE_FOLDER, build.BUILD / "private" / "site")


if __name__ == "__main__":
    unittest.main()
