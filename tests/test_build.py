"""The Build seam (Q26, #8): the stand-in loader's result on tests/fixtures/standin/loader_sample/ in, MetricProfile files out.

The sample is cut as whole matches, so its players hold partial seasons. ENG 2017/18 is the league-season with the most
Pool players (11), so it is the small real sample #8 asks for. A clause with 0 real cases uses a small hand-made input,
says so in its name and in a comment, and never goes in tests/fixtures/.
Run from the repo root: python3 -m unittest discover tests
"""
import dataclasses
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_standin_loader import sample_run
from twin.application import build
from twin.domain import careers, profiles
from twin.domain.pool import in_pool

PEER_GROUP = ("ENG", 2017)
PLAYER_KEYS = {"player_id", "name", "clubs", "minutes", "display_position", "metric_profile", "display_stats", "twins", "career"}
FILE_KEYS = {"source", "league", "season", "metrics", "player_seasons"}
CAREER_FILE_KEYS = {"source", "metrics", "career_minutes", "careers"}
CAREER_KEYS = {"player_id", "name", "minutes", "role_group", "first_season", "last_season", "season_count", "player_seasons", "metric_profile", "percentiles", "twins"}
CAREER_TWIN_KEYS = {"player_id", "name", "role_group", "first_season", "last_season", "season_count", "minutes", "distance", "closeness"}


def loaded():
    return sample_run().loaded


def written_files(source=None):
    """The stand-in run on the sample, into a temporary build folder: {relative path: parsed JSON}, the career file too."""
    with TemporaryDirectory() as folder:
        build.run(source or loaded(), Path(folder))
        return {path.relative_to(folder).as_posix(): json.loads(path.read_text(encoding="utf8")) for path in Path(folder).rglob("*") if path.is_file()}


def built_files(source=None):
    """The league-season files only."""
    return {path: content for path, content in written_files(source).items() if not path.endswith(build.CAREER_FILE)}


def peer_group_file():
    return built_files()[f"private/{PEER_GROUP[0]}_{PEER_GROUP[1]}.json"]


def pool_of(league, season):
    return [found for found in loaded().player_seasons if in_pool(found) and (found.league, found.season) == (league, season)]


def shots_of(player_season):
    return [shot for shot in loaded().shots if (shot.league, shot.season, shot.player_id) == player_season.key]


class PoolRules(unittest.TestCase):
    def test_profile_files_hold_exactly_the_pool_one_entry_per_stint(self):
        files = built_files()
        pool = {found.key: found for found in loaded().player_seasons if in_pool(found)}
        written = {}
        for content in files.values():
            for entry in content["player_seasons"]:
                key = (content["league"], content["season"], entry["player_id"])
                self.assertNotIn(key, written)
                written[key] = entry
        self.assertEqual(set(written), set(pool))
        self.assertEqual(len(pool_of(*PEER_GROUP)), 11)
        for key, entry in written.items():
            self.assertEqual(entry["minutes"], pool[key].minutes, key)  # its own stint's minutes, never a merged total

    def test_two_stints_of_one_player_stay_two_player_seasons(self):
        # Real: Lucas Moura 2017/18, Ligue 1 then Premier League. The Pool test runs on each stint alone.
        stints = [found for found in loaded().player_seasons if found.player_id == "2b622f01" and found.season == 2017]
        self.assertEqual(sorted(found.league for found in stints), ["ENG", "FRA"])
        profiled = {(content["league"], entry["player_id"]) for content in built_files().values() for entry in content["player_seasons"]}
        for found in stints:
            self.assertEqual((found.league, found.player_id) in profiled, in_pool(found), found.league)

    def test_players_out_of_the_pool_get_no_profile(self):
        out = [found for found in loaded().player_seasons if (found.league, found.season) == PEER_GROUP and not in_pool(found)]
        self.assertTrue(any(found.minutes >= 900 for found in out))  # real defenders and keepers at 900+, e.g. Andrew Robertson
        written = {entry["player_id"] for entry in peer_group_file()["player_seasons"]}
        self.assertFalse(written & {found.player_id for found in out})


class MetricShots(unittest.TestCase):
    def test_shots_exclude_penalties_and_own_goals(self):
        shots = [shot for shot in loaded().shots if (shot.league, shot.season) == PEER_GROUP]
        penalties = [shot for shot in shots if shot.situation == "Penalty"]
        own_goals = [shot for shot in shots if shot.result == "OwnGoal"]
        self.assertTrue(penalties and own_goals)  # real: 17 penalties and 7 own goals in the sample's ENG 2017/18
        kept = [shot for shot in shots if shot not in penalties and shot not in own_goals]
        self.assertEqual([shot for shot in shots if profiles.counts_for_metrics(shot)], kept)
        for found in pool_of(*PEER_GROUP):
            own = shots_of(found)
            self.assertEqual(profiles.raw_metrics(found, own), profiles.raw_metrics(found, [shot for shot in own if shot in kept]), found.name)

    def test_shots_per_90_and_npxg_per_shot_use_non_penalty_shots(self):
        # Real: Mohamed Salah ENG 2017/18 takes penalties in the sample.
        salah = next(found for found in pool_of(*PEER_GROUP) if found.name == "Mohamed Salah")
        own = shots_of(salah)
        kept = [shot for shot in own if shot.situation != "Penalty" and shot.result != "OwnGoal"]
        self.assertLess(len(kept), len(own))
        raw = profiles.raw_metrics(salah, own)
        self.assertAlmostEqual(raw.shots_per_90, len(kept) * 90 / salah.minutes)
        self.assertAlmostEqual(raw.npxg_per_shot, sum(shot.xg for shot in kept) / len(kept))
        self.assertAlmostEqual(raw.xa_per_90, salah.xa * 90 / salah.minutes)


class MetricSet(unittest.TestCase):
    def test_key_passes_is_gone_and_finishing_is_in_the_10_metrics(self):
        # D30-2: key passes per 90 correlated 0.815 with xA per 90 (T30), so it goes and finishing comes in.
        self.assertEqual(len(profiles.METRICS), 10)
        self.assertNotIn("key_passes_per_90", profiles.METRICS)
        self.assertIn("xa_per_90", profiles.METRICS)
        self.assertIn("finishing", profiles.METRICS)
        for content in built_files().values():
            self.assertEqual(content["metrics"], list(profiles.METRICS))
            for entry in content["player_seasons"]:
                self.assertEqual(list(entry["metric_profile"]), list(profiles.METRICS))

    def test_finishing_is_npg_minus_npxg_per_non_penalty_shot(self):
        # Real: Mohamed Salah ENG 2017/18 scores and takes penalties in the sample.
        salah = next(found for found in pool_of(*PEER_GROUP) if found.name == "Mohamed Salah")
        kept = [shot for shot in shots_of(salah) if shot.situation != "Penalty" and shot.result != "OwnGoal"]
        goals = sum(1 for shot in kept if shot.result == "Goal")
        self.assertTrue(goals)
        raw = profiles.raw_metrics(salah, shots_of(salah))
        self.assertAlmostEqual(raw.finishing, (goals - sum(shot.xg for shot in kept)) / len(kept))
        self.assertAlmostEqual(raw.finishing, profiles.display_stats(salah, shots_of(salah)).npg_minus_npxg / len(kept))

    def test_finishing_shrinks_by_the_npxg_per_shot_method(self):
        # D30-3: normal-normal on each non-penalty shot's goal minus xG, as npxG per shot shrinks each shot's xG.
        index = profiles.METRICS.index("finishing")
        for (league, season), members in profiles.peer_group_profiles(loaded().player_seasons, loaded().shots).items():
            groups = [[(shot.result == "Goal") - shot.xg for shot in shots_of(member.player_season) if profiles.counts_for_metrics(shot)] for member in members]
            self.assertEqual([member.shrunk[index] for member in members], profiles.shrunk_means(groups), (league, season))
            self.assertEqual([member.values[index] for member in members], profiles.z_scores(profiles.shrunk_means(groups)), (league, season))
        groups = [[(shot.result == "Goal") - shot.xg for shot in shots_of(player) if profiles.counts_for_metrics(shot)] for player in pool_of(*PEER_GROUP)]
        mean, _, _ = profiles.normal_normal_prior(groups)
        for group, shrunk in zip(groups, profiles.shrunk_means(groups)):
            self.assertLessEqual(abs(shrunk - mean), abs(sum(group) / len(group) - mean) + 1e-12)


class CareerFile(unittest.TestCase):
    def test_the_build_writes_a_career_file_and_marks_each_season_entry(self):
        content = written_files()[f"private/{build.CAREER_FILE}"]
        self.assertEqual(set(content), CAREER_FILE_KEYS)
        self.assertEqual((content["source"], content["metrics"], content["career_minutes"]), ("standin", list(profiles.METRICS), 0))
        self.assertEqual(content["careers"], [])  # real: no sample player has 3 seasons of 1,350+ minutes (#29)
        # D30-8: so every sample player keeps season twins only.
        self.assertEqual({entry["career"] for found in built_files().values() for entry in found["player_seasons"]}, {False})

    def test_career_entries_hold_the_career_profile_percentiles_and_lists(self):
        # Real sample careers with the rules at the Pool's 900 minutes and 1 season, since none meets #29's rules.
        found = careers.career_profiles(profiles.peer_group_profiles(loaded().player_seasons, loaded().shots), career_minutes=900, eligible_minutes=900, career_seasons=1)
        content = build.career_file(loaded(), found, 900)
        self.assertEqual(content["career_minutes"], 900)
        percentiles, lists = careers.career_percentiles(found), careers.career_lists(found)
        self.assertEqual([entry["player_id"] for entry in content["careers"]], [career.player_id for career in found])
        for entry, career in zip(content["careers"], found):
            self.assertEqual(set(entry), CAREER_KEYS)
            self.assertEqual(entry["metric_profile"], dict(zip(profiles.METRICS, career.values)))
            self.assertEqual(entry["percentiles"], dict(zip(profiles.METRICS, percentiles[career.player_id])))
            self.assertEqual(entry["minutes"], sum(season["minutes"] for season in entry["player_seasons"]))
            self.assertEqual(set(entry["twins"]), set(lists))
            for method, kinds in entry["twins"].items():
                self.assertEqual(set(kinds), {"all_roles", "same_role"})
                self.assertEqual([twin["player_id"] for twin in kinds["same_role"]], [match.career.player_id for match in lists[method][career.player_id].same_role])
                for twin in kinds["all_roles"] + kinds["same_role"]:
                    self.assertEqual(set(twin), CAREER_TWIN_KEYS)
        salah = next(entry for entry in content["careers"] if entry["name"] == "Mohamed Salah")
        self.assertEqual((salah["minutes"], salah["role_group"], salah["first_season"], salah["last_season"], salah["season_count"]), (3611, "Wide", 2017, 2023, 2))


class Shrinkage(unittest.TestCase):
    def counts(self, test):
        found = pool_of(*PEER_GROUP)
        return [sum(1 for shot in shots_of(player) if profiles.counts_for_metrics(shot) and test(shot)) for player in found], [
            sum(1 for shot in shots_of(player) if profiles.counts_for_metrics(shot)) for player in found]

    def test_beta_binomial_prior_meets_both_moment_conditions(self):
        # Real header counts of the ENG 2017/18 Pool in the sample.
        successes, trials = self.counts(lambda shot: shot.shot_type == "Head")
        mean, size = profiles.beta_binomial_prior(successes, trials)
        total = sum(trials)
        self.assertAlmostEqual(mean, sum(successes) / total)
        self.assertTrue(0 < size < float("inf"), size)  # this group has real between-player spread
        rho = 1 / (size + 1)
        spread = sum(n * (k / n - mean) ** 2 for k, n in zip(successes, trials) if n)
        groups = sum(1 for n in trials if n)
        expected = mean * (1 - mean) * ((total - sum(n * n for n in trials) / total) * rho + (groups - 1) * (1 - rho))
        self.assertAlmostEqual(spread, expected)

    def test_shrunk_shares_move_toward_the_peer_group_mean(self):
        successes, trials = self.counts(lambda shot: shot.shot_type == "Head")
        mean, _ = profiles.beta_binomial_prior(successes, trials)
        for k, n, shrunk in zip(successes, trials, profiles.shrunk_shares(successes, trials)):
            raw = k / n if n else mean
            self.assertLessEqual(min(raw, mean) - 1e-12, shrunk)
            self.assertLessEqual(shrunk, max(raw, mean) + 1e-12)
            self.assertLess(abs(shrunk - mean), abs(raw - mean) + 1e-12)

    def test_normal_normal_prior_meets_the_moment_condition(self):
        # Real npxG of the ENG 2017/18 Pool's non-penalty shots in the sample.
        groups = [[shot.xg for shot in shots_of(player) if profiles.counts_for_metrics(shot)] for player in pool_of(*PEER_GROUP)]
        mean, between, within = profiles.normal_normal_prior(groups)
        values = [value for group in groups for value in group]
        total, filled = len(values), [group for group in groups if group]
        self.assertAlmostEqual(mean, sum(values) / total)
        self.assertAlmostEqual(within, sum((value - sum(group) / len(group)) ** 2 for group in filled for value in group) / (total - len(filled)))
        self.assertGreater(between, 0)  # this group has real between-player spread
        spread = sum(len(group) * (sum(group) / len(group) - mean) ** 2 for group in filled)
        self.assertAlmostEqual(spread, (len(filled) - 1) * within + (total - sum(len(group) ** 2 for group in filled) / total) * between)
        for group, shrunk in zip(groups, profiles.shrunk_means(groups)):
            raw = sum(group) / len(group)
            self.assertLess(abs(shrunk - mean), abs(raw - mean) + 1e-12)

    def test_synthetic_no_spread_shrinks_every_share_to_the_mean(self):
        # Synthetic, plain counts: equal rates leave no between-player spread, so the method of moments gives the mean.
        self.assertEqual(profiles.shrunk_shares([1, 2, 0], [10, 20, 0]), [0.1, 0.1, 0.1])
        self.assertEqual(profiles.shrunk_shares([0, 0], [5, 7]), [0.0, 0.0])


class ZScores(unittest.TestCase):
    def test_z_scores_are_within_the_peer_group_and_clipped(self):
        content = peer_group_file()
        self.assertEqual(content["metrics"], list(profiles.METRICS))
        for metric in profiles.METRICS:
            values = [entry["metric_profile"][metric] for entry in content["player_seasons"]]
            self.assertTrue(all(-3 <= value <= 3 for value in values), metric)
            if all(abs(value) < 3 for value in values):
                self.assertAlmostEqual(sum(values), 0, places=9, msg=metric)
        # Another league-season's players never move this PeerGroup's entries. Only the twin lists span the whole Pool.
        alone = dataclasses.replace(loaded(), player_seasons=tuple(found for found in loaded().player_seasons if (found.league, found.season) == PEER_GROUP))
        profiles_of = lambda found: {entry["player_id"]: {name: value for name, value in entry.items() if name != "twins"} for entry in found["player_seasons"]}
        self.assertEqual(profiles_of(built_files(alone)[f"private/{PEER_GROUP[0]}_{PEER_GROUP[1]}.json"]), profiles_of(content))

    def test_synthetic_z_scores_clip_at_3(self):
        # Synthetic, plain numbers: no real PeerGroup in the sample reaches the clip.
        self.assertEqual(profiles.z_scores([0.0] * 10 + [100.0])[-1], 3.0)
        self.assertEqual(profiles.z_scores([0.0] * 10 + [-100.0])[-1], -3.0)
        self.assertEqual(profiles.z_scores([2.0, 2.0]), [0.0, 0.0])


class PublicFile(unittest.TestCase):
    def test_public_file_holds_only_derived_values_and_no_shot_rows(self):
        content = peer_group_file()
        self.assertEqual(set(content), FILE_KEYS)
        self.assertEqual(len(content["player_seasons"]), 11)
        for entry in content["player_seasons"]:
            self.assertEqual(set(entry), PLAYER_KEYS)
            self.assertEqual(set(entry["metric_profile"]), set(profiles.METRICS))
            self.assertEqual(set(entry["display_stats"]), {"goals", "assists", "npg_minus_npxg"})
            self.assertTrue(all(isinstance(value, (int, float)) for value in entry["metric_profile"].values()))

    def test_public_file_step_fails_on_the_standin_result_and_names_the_source(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(SystemExit) as stopped:
                build.write_public_files(loaded(), Path(folder))
            self.assertIn("'standin'", str(stopped.exception))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_public_file_records_its_source(self):
        self.assertEqual({content["source"] for content in built_files().values()}, {"standin"})
        # Synthetic: the sample's real records relabelled as the one source that may publish, to reach the public step.
        live = dataclasses.replace(loaded(), source="understat", may_publish=True)
        with TemporaryDirectory() as folder:
            written = build.write_public_files(live, Path(folder))
            self.assertTrue(written)
            self.assertEqual({json.loads(path.read_text(encoding="utf8"))["source"] for path in written}, {"understat"})

    def test_standin_run_writes_only_under_build_private(self):
        self.assertEqual(build.BUILD, ROOT / "build")
        files = written_files()
        self.assertIn(f"private/{PEER_GROUP[0]}_{PEER_GROUP[1]}.json", files)
        self.assertIn(f"private/{build.CAREER_FILE}", files)
        self.assertTrue(all(path.startswith("private/") for path in files), sorted(files))


if __name__ == "__main__":
    unittest.main()
