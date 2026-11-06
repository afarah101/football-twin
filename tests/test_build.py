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
from twin.domain import profiles
from twin.domain.pool import in_pool

PEER_GROUP = ("ENG", 2017)
PLAYER_KEYS = {"player_id", "name", "clubs", "minutes", "display_position", "metric_profile", "display_stats"}
FILE_KEYS = {"source", "league", "season", "metrics", "player_seasons"}


def loaded():
    return sample_run().loaded


def built_files(source=None):
    """The stand-in run on the sample, into a temporary build folder: {relative path: parsed JSON}."""
    with TemporaryDirectory() as folder:
        build.run(source or loaded(), Path(folder))
        return {path.relative_to(folder).as_posix(): json.loads(path.read_text(encoding="utf8")) for path in Path(folder).rglob("*") if path.is_file()}


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
        # Another league-season's players never move this PeerGroup's z-scores.
        alone = dataclasses.replace(loaded(), player_seasons=tuple(found for found in loaded().player_seasons if (found.league, found.season) == PEER_GROUP))
        self.assertEqual(built_files(alone)[f"private/{PEER_GROUP[0]}_{PEER_GROUP[1]}.json"], content)

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
        files = built_files()
        self.assertIn(f"private/{PEER_GROUP[0]}_{PEER_GROUP[1]}.json", files)
        self.assertTrue(all(path.startswith("private/") for path in files), sorted(files))


if __name__ == "__main__":
    unittest.main()
