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
from contextlib import contextmanager
from functools import lru_cache
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_build import loaded
from twin.application import build, site_data
from twin.domain import careers, profiles
from twin.domain.pool import in_pool

ON_SCREEN_LINE = "Matches how they shoot and create, not how they move."  # plan:9
STYLE_LABEL = "style twin, not level twin"  # plan:36
SMALL_SAMPLE = "small sample"  # plan:20, below 1,500 minutes
DATA_TO = "Data to 2023/24"  # plan:119
CREDIT = "Shot and xG data: Understat"  # Ahmed, 7 Nov 2026, with "Understat" linked to https://understat.com
CREDIT_LINK = '<a href="https://understat.com">Understat</a>'
TAKEDOWN = "Takedown contact: [TO BE ADDED BEFORE LAUNCH]"  # Ahmed, 7 Nov 2026: a placeholder until #13
CLOSENESS = "of all pairs"  # issue #11: "closer than X% of all pairs"
SAME_LEAGUE_CLOSENESS = "of same-league pairs"  # #11: the same-league list is ranked against same-league pairs
SITE_TWIN_KEYS = {"player_id", "name", "league", "season", "minutes", "closeness", "small_sample"}
CAREER_CLOSENESS = "of all careers"  # D30-9
SEASON_TWINS = "Season twins"  # D30-8
SAME_ROLE = "Same role only"  # #30 decision 7, D30-5
FINISHING_LABEL = "Finishing (goals vs xG per shot)"  # D30-12
SEASONS_COVERED = "Seasons covered: "  # #30 decision 6
SEASON_PERCENTILE = "Percentile within "  # D30-14: "Percentile within <league> <season>, from 0 to 100"
HOW_IT_WORKS = (  # #30 decision 11, with the D30-1 bar
    "How it works",
    "compared with the other attackers in the same league and season",
    "averaged over the career, weighted by minutes played",
    "nearest match",
    "Attacking style only",
    "Data 2017/18-2023/24",
    "Careers need 1,350+ minutes in each of 3+ seasons",
)
CAREER_BAR = 900  # the cut sample holds no #29 career, so tests lower the rules to the Pool's 900, as in B1
CAREER_FILE_KEYS = {"player_id", "name", "role_group", "first_season", "last_season", "season_count", "minutes", "metrics", "percentiles", "player_seasons", "twins"}
CAREER_TWIN_KEYS = {"player_id", "name", "role_group", "first_season", "last_season", "season_count", "minutes", "closeness"}


@contextmanager
def career_bar(minutes):
    """The Build with a lower career bar. Real sample records only; just the bar moves."""
    with mock.patch.object(build, "career_profiles", lambda groups: careers.career_profiles(groups, career_minutes=minutes, eligible_minutes=minutes, career_seasons=1)), mock.patch.object(build, "CAREER_MINUTES", minutes):
        yield


def site_of(source, bar=None):
    """The Build, then the site, into a temporary build folder: {path under the site folder: text}. `bar` lowers the career bar."""
    if bar is not None:
        with career_bar(bar):
            return site_of(source)
    with TemporaryDirectory() as folder:
        paths = build.run(source, Path(folder))
        site = site_data.write_site(paths, Path(folder) / "private" / "site")
        return {path.relative_to(site).as_posix(): path.read_text(encoding="utf8") for path in site.rglob("*") if path.is_file()}


@lru_cache(maxsize=None)
def sample_site():
    return site_of(loaded())


@lru_cache(maxsize=None)
def career_site():
    return site_of(loaded(), CAREER_BAR)


def names(site=sample_site):
    return json.loads(site()["data/names.json"])


def data_files(site=sample_site):
    """The league-season files."""
    return {path: json.loads(text) for path, text in site().items() if path.startswith("data/") and path != "data/names.json" and not path.startswith("data/careers/")}


def career_files(site=career_site):
    return {path: json.loads(text) for path, text in site().items() if path.startswith("data/careers/")}


class NameIndex(unittest.TestCase):
    def test_name_index_holds_one_entry_per_player_never_one_per_season(self):
        # D30-13: one search row per player; his Pool seasons are season links inside that one entry.
        pool = [found for found in loaded().player_seasons if in_pool(found)]
        ids = [entry["player_id"] for entry in names()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {found.player_id for found in pool})
        for entry in names():
            mine = sorted((found for found in pool if found.player_id == entry["player_id"]), key=lambda found: (found.season, found.league))
            self.assertEqual([(link["league"], link["season"], link["minutes"]) for link in entry["player_seasons"]], [(found.league, found.season, found.minutes) for found in mine])
            self.assertEqual((entry["first_season"], entry["last_season"], entry["minutes"]), (mine[0].season, mine[-1].season, sum(found.minutes for found in mine)))
            self.assertEqual(entry["name"], mine[-1].name)
            self.assertEqual(entry["clubs"], list(dict.fromkeys(club for found in mine for club in found.clubs)))
            for link in entry["player_seasons"]:
                listed = {player["player_id"] for player in data_files()[f"data/{link['file']}"]["player_seasons"]}
                self.assertIn(entry["player_id"], listed)
        # Real: Mohamed Salah holds two Pool seasons in the sample (2017/18 and 2023/24): one entry, two season links.
        salah = [entry for entry in names() if entry["name"] == "Mohamed Salah"]
        self.assertEqual(len(salah), 1)
        self.assertEqual([link["season"] for link in salah[0]["player_seasons"]], [2017, 2023])
        self.assertEqual((salah[0]["career"], salah[0]["file"]), (False, "ENG_2023.json"))  # no career: opens his latest season

    def test_a_career_entry_carries_the_career_summary(self):
        # Real: at the 900-minute bar Salah is a Wide career, 2017/18-2023/24, 3,611 Pool minutes.
        salah = [entry for entry in names(career_site) if entry["name"] == "Mohamed Salah"]
        self.assertEqual(len(salah), 1)
        self.assertEqual((salah[0]["career"], salah[0]["role_group"], salah[0]["first_season"], salah[0]["last_season"], salah[0]["minutes"]), (True, "Wide", 2017, 2023, 3611))

    def test_a_stint_out_of_the_pool_is_not_a_season_link(self):
        # Real: Ben Brereton 2023/24, Premier League stint in the Pool, La Liga stint 23 minutes. Stints are never merged.
        stints = sorted(found.league for found in loaded().player_seasons if found.player_id == "57827369" and found.season == 2023)
        self.assertEqual(stints, ["ENG", "ESP"])
        brereton = [entry for entry in names() if entry["player_id"] == "57827369"]
        self.assertEqual([(link["league"], link["minutes"]) for link in brereton[0]["player_seasons"]], [("ENG", 1105)])

    def test_real_two_stint_season_shows_as_two_season_links_on_data_standin(self):
        # Real, on data/standin/: Philippe Coutinho 2017/18, Liverpool then Barcelona. The sample holds no such case.
        # D30-13: the #11 two-stint rule now lives in the season links, in the names entry and the career file alike.
        from twin.infrastructure.standin.loader import StandinLoader

        full = site_of(StandinLoader().load())
        coutinho = [entry for entry in json.loads(full["data/names.json"]) if entry["name"] == "Philippe Coutinho"]
        self.assertEqual(len(coutinho), 1)
        stints = [(link["league"], link["season"], link["minutes"], link["file"]) for link in coutinho[0]["player_seasons"] if link["season"] == 2017]
        self.assertEqual(stints, [("ENG", 2017, 1109, "ENG_2017.json"), ("ESP", 2017, 1296, "ESP_2017.json")])
        if coutinho[0]["career"]:
            career = json.loads(full[f"data/careers/{coutinho[0]['player_id']}.json"])
            self.assertEqual([(season["league"], season["season"], season["minutes"], season["file"]) for season in career["player_seasons"] if season["season"] == 2017], stints)


class SeasonPercentiles(unittest.TestCase):
    def test_season_fingerprint_holds_build_percentiles_within_the_league_season(self):
        # D30-14: mid-rank percentiles of each metric among the league-season's Pool PlayerSeasons, from 0 to 100.
        from twin.domain.twins import percentiles

        groups = profiles.peer_group_profiles(loaded().player_seasons, loaded().shots)
        for (league, season), members in groups.items():
            content = data_files()[f"data/{league}_{season}.json"]
            shown = {entry["player_id"]: entry["percentiles"] for entry in content["player_seasons"]}
            for index, metric in enumerate(profiles.METRICS):
                expected = percentiles([member.values[index] for member in members])
                for member, value in zip(members, expected):
                    self.assertAlmostEqual(shown[member.player_season.player_id][metric], float(value))
                    self.assertTrue(0 <= shown[member.player_season.player_id][metric] <= 100)


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


class CareerData(unittest.TestCase):
    def test_names_and_season_files_say_which_players_have_a_career(self):
        # Real: under the #29 rules no sample player has a career, so every search opens season twins (D30-8).
        self.assertEqual({entry["career"] for entry in names()}, {False})
        self.assertEqual(career_files(sample_site), {})
        self.assertEqual({entry["career"] for content in data_files().values() for entry in content["player_seasons"]}, {False})
        # At the Pool's 900 minutes every Pool player has one, with one file each.
        self.assertEqual({entry["career"] for entry in names(career_site)}, {True})
        self.assertEqual(set(career_files()), {f"data/careers/{entry['player_id']}.json" for entry in names(career_site)})
        self.assertEqual({entry["career"] for content in data_files(career_site).values() for entry in content["player_seasons"]}, {True})

    def test_career_file_holds_the_site_method_lists_and_percentiles(self):
        found = careers.career_profiles(profiles.peer_group_profiles(loaded().player_seasons, loaded().shots), career_minutes=CAREER_BAR, eligible_minutes=CAREER_BAR, career_seasons=1)
        lists = careers.career_lists(found)[site_data.SITE_METHOD]  # D30-10: the site shows Euclidean
        percentiles = careers.career_percentiles(found)
        seasons = data_files(career_site)
        for career in found:
            content = career_files()[f"data/careers/{career.player_id}.json"]
            self.assertEqual(set(content), CAREER_FILE_KEYS)
            self.assertEqual((content["name"], content["role_group"], content["minutes"], content["season_count"]), (career.name, career.role_group, career.minutes, career.season_count))
            self.assertEqual(content["metrics"], list(profiles.METRICS))
            self.assertEqual(content["percentiles"], dict(zip(profiles.METRICS, percentiles[career.player_id])))
            self.assertNotIn("distance", json.dumps(content))
            for kind in ("all_roles", "same_role"):
                self.assertEqual([twin["player_id"] for twin in content["twins"][kind]], [match.career.player_id for match in getattr(lists[career.player_id], kind)])
                for twin in content["twins"][kind]:
                    self.assertEqual(set(twin), CAREER_TWIN_KEYS)
            # Each season link opens a league-season file that lists this player.
            for season in content["player_seasons"]:
                self.assertIn(career.player_id, {entry["player_id"] for entry in seasons[f"data/{season['file']}"]["player_seasons"]})
        salah = career_files()["data/careers/e342ad68.json"]
        self.assertEqual((salah["first_season"], salah["last_season"], salah["minutes"], salah["role_group"]), (2017, 2023, 3611, "Wide"))

    def test_closeness_is_the_same_on_both_career_lists(self):
        # D30-9: against all career pairs, so a twin on both lists keeps its closeness when the filter toggles.
        shared = 0
        for content in career_files().values():
            both = {twin["player_id"]: twin["closeness"] for twin in content["twins"]["all_roles"]}
            for twin in content["twins"]["same_role"]:
                if twin["player_id"] in both:
                    self.assertEqual(twin["closeness"], both[twin["player_id"]])
                    shared += 1
        self.assertTrue(shared)

    def test_every_data_file_is_at_most_1_mb(self):
        # D30-11. The full-data sizes are in the #30 B2 report; this guards the rule on every run.
        self.assertEqual(site_data.MAX_DATA_BYTES, 1_000_000)
        for site in (sample_site, career_site):
            for path, text in site().items():
                if path.startswith("data/"):
                    self.assertLessEqual(len(text.encode("utf8")), site_data.MAX_DATA_BYTES, path)

    def test_synthetic_a_data_file_over_1_mb_fails_the_run(self):
        # Synthetic, plain numbers: no real data file comes near 1 MB, so the guard is reached with a hand-made value.
        with TemporaryDirectory() as folder:
            path = Path(folder) / "big.json"
            with self.assertRaises(SystemExit) as stopped:
                site_data.write_json(path, ["x" * 1000] * 1000)
            self.assertIn("big.json", str(stopped.exception))
            self.assertFalse(path.exists())


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
        self.assertIn(SAME_LEAGUE_CLOSENESS, script)
        for text in (CAREER_CLOSENESS, FINISHING_LABEL, SEASONS_COVERED, SEASON_PERCENTILE):
            self.assertIn(text, script)
        for text in (SEASON_TWINS, SAME_ROLE) + HOW_IT_WORKS:
            self.assertIn(text, page)
        self.assertNotIn("Key passes", script)  # D30-2

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
