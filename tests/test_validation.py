"""The Validation report seam (Q26, #10): the Pool in, a self-match PASS, WEAK or FAIL for each method out.

The bands are tested with plain rates (Q29). The loader sample has 0 next-season transitions, so the self-match hit rule uses
a small hand-made input: it says so in its name and in a comment, and it never goes in tests/fixtures/.
Run from the repo root: python3 -m unittest tests.test_validation
"""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_build import loaded
from twin.application import validation
from twin.domain.profiles import METRICS, peer_group_profiles


def sample_groups():
    found = loaded()
    return peer_group_profiles(found.player_seasons, found.shots)


def hand_made(player_id, season, values, league="ENG"):
    return SimpleNamespace(values=values, player_season=SimpleNamespace(player_id=player_id, season=season, league=league, key=(league, season, player_id)))


class Bands(unittest.TestCase):
    def test_bands_with_plain_rates(self):
        cases = {1.0: "PASS", 0.40: "PASS", 0.3999: "WEAK", 0.35: "WEAK", 0.30: "WEAK", 0.2999: "FAIL", 0.0: "FAIL"}
        for rate, expected in cases.items():
            with self.subTest(rate=rate):
                self.assertEqual(validation.band(rate), expected)

    def test_wilson_interval_with_plain_counts(self):
        low, high = validation.wilson(40, 100)
        self.assertAlmostEqual(low, 0.3094, places=3)
        self.assertAlmostEqual(high, 0.4980, places=3)
        self.assertEqual(validation.wilson(0, 0), (0.0, 0.0))


class SelfMatch(unittest.TestCase):
    def test_hand_made_the_next_season_counts_and_other_own_seasons_are_removed(self):
        # hand-made: 0 real transitions in the sample. Player A's 2017 season sits next to his own 2016 season (which must be
        # removed) and 2018 season (the target). 12 other players sit between, so the target is the 12th closest player: a miss
        # with 10 slots, a hit once the 3 nearest others move away.
        members = [hand_made("A", 2017, (0.0,)), hand_made("A", 2016, (0.01,)), hand_made("A", 2018, (12.5,))]
        members += [hand_made(f"P{k}", 2017, (k + 1.0,)) for k in range(12)]
        vectors = np.array([member.values for member in members])
        found = validation.self_match(members, vectors, "euclidean", [(0, [2])])
        self.assertEqual((found.hits, found.tests), (0, 1))
        self.assertAlmostEqual(found.baseline, 10 / 13)  # 12 others plus A's target, his 2016 season removed
        vectors[3:6] = 100.0
        self.assertEqual(validation.self_match(members, vectors, "euclidean", [(0, [2])]).hits, 1)

    def test_hand_made_transitions_and_the_choose_judge_split(self):
        # hand-made: consecutive seasons 2020-2023 for one player.
        members = [hand_made("A", season, (0.0,)) for season in (2020, 2021, 2022, 2023)]
        found = validation.transitions(members)
        self.assertEqual([target for _, _, target in found], [2021, 2022, 2023])
        choose, judge = validation.split(found)
        self.assertEqual((len(choose), len(judge)), (1, 2))  # 2020->2021 chooses; 2021->2022 and 2022->2023 are judged


class Report(unittest.TestCase):
    def test_the_report_runs_on_the_sample_with_every_section(self):
        text, results = validation.validation_report(sample_groups())
        self.assertEqual(set(results), {"euclidean", "cosine", "pearson", "basketball"})
        for heading in ("## Self-match", "## Stability", "## Correlation matrix", "## PCA", "## Basketball method beside", "## Not run here"):
            self.assertIn(heading, text)
        self.assertIn("(comparison only)", text)  # Q20: Basketball is never the winner
        self.assertEqual(text.count("\n| ") - text.count("\n| Method") - text.count("\n| Component") - text.count("\n| |"), 4 + len(METRICS) * 2)

    def test_pca_shares_sum_to_one_and_signs_are_fixed(self):
        z = np.array([member.values for member in validation.pool_members(sample_groups())])
        shares, loadings = validation.pca(z)
        self.assertAlmostEqual(float(shares.sum()), 1.0)
        self.assertTrue(all(row[np.abs(row).argmax()] > 0 for row in loadings))

    def test_an_approved_cross_season_ids_row_stops_the_report(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "review_decisions.csv"
            path.write_text("item_type,key,decision\ncross_season_ids,a|b,approve\n", encoding="utf8")
            with self.assertRaises(validation.ValidationStopped):
                validation.check_cross_season_ids(path)
            path.write_text('item_type,key,decision\nname_map,"cross_season_ids, quoted",approve\n', encoding="utf8")
            self.assertEqual(validation.check_cross_season_ids(path), 0)

    def test_the_committed_review_decisions_have_no_cross_season_ids_row(self):
        header = validation.REVIEW_DECISIONS.read_text(encoding="utf8").splitlines()[0]
        self.assertTrue(header.startswith("item_type,"))  # the check reads the real column layout
        self.assertEqual(validation.check_cross_season_ids(), 0)

    def test_spearman_averages_tied_ranks(self):
        self.assertEqual(list(validation.average_ranks([3, 1, 3, 2])), [2.5, 0.0, 2.5, 1.0])
        self.assertAlmostEqual(validation.spearman([1, 2, 2, 3], [1, 2, 2, 3]), 1.0)

    def test_the_report_goes_to_build_private_only(self):
        self.assertEqual(validation.REPORT.relative_to(ROOT).parts[:2], ("build", "private"))


if __name__ == "__main__":
    unittest.main()
