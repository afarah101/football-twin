"""Claim Check #45: season-totals player Verdicts (Chance creation, Build-up) with the fixed 5-point band (Q10).

Every test here is synthetic: hand-made PlayerSeasons and PlayerMatches, kept out of tests/fixtures/.
Run from the repo root: python3 -m unittest tests.test_claim_check_totals_verdicts
"""
import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from claim_check.domain import verdicts
from claim_check.interface.cli import render
from test_claim_check_season_verdicts import SeasonWorld, only

PEERS = 40


class TotalsWorld(SeasonWorld):
    """synthetic: peer k has xA k * 0.01 per 1,800 minutes (so xA per 90 = k * 0.0005) and xG buildup the same."""

    def add_totals(self, player_id, name, season, xa, buildup=None, key_passes=None, **extra):
        self.add(player_id, name, season, shots=10, **extra)
        self.seasons[-1] = dataclasses.replace(self.seasons[-1], xa=xa, xg_buildup=buildup, key_passes=key_passes)
        return self

    def totals_peers(self, season):
        for k in range(PEERS):
            self.add_totals(f"peer{k}", f"Peer Number{k}", season, k * 0.01, k * 0.01, k, club=f"Club{k}")
        return self


def subject_at(rank, season=2023):
    """The Subject's xA sits just above peer `rank`."""
    return TotalsWorld().totals_peers(season).add_totals("subj", "Subject Person", season, rank * 0.01 + 0.001, rank * 0.01 + 0.001, 20)


class SeasonTotals(unittest.TestCase):
    def test_synthetic_a_top_creator_is_supported_with_the_range_label(self):
        verdict = subject_at(PEERS).check(("creative",))
        found = only(verdict)
        self.assertEqual((found.claim_type, found.verdict), ("Chance creation", verdicts.SUPPORTED))
        self.assertEqual(found.range_note, "Range not available: this metric has season totals only.")
        self.assertIn("Range not available: this metric has season totals only.", render(verdict))
        self.assertEqual(found.seasons_alone[0], "2023/24: 1.00 key passes per 90")

    def test_synthetic_within_5_points_of_the_threshold_is_borderline(self):
        # Just above 30 of 40 peers: mid-rank about 75th, on the >= 75th line, so inside the 5-point band.
        found = only(subject_at(30).check(("creative",)))
        self.assertEqual(found.tests[0].outcome, "borderline")
        self.assertEqual((found.verdict, found.reason), (verdicts.MIXED, "within 5 points of the line"))
        self.assertLess(abs(found.tests[0].percentile - 75), verdicts.BAND)

    def test_synthetic_more_than_5_points_below_misses(self):
        self.assertEqual(only(subject_at(10).check(("creative",))).verdict, verdicts.NOT_SUPPORTED)

    def test_synthetic_build_up(self):
        found = only(subject_at(PEERS).check(("involved", "in", "build-up")))
        self.assertEqual((found.claim_type, found.verdict), ("Build-up", verdicts.SUPPORTED))

    def test_synthetic_season_totals_missing_for_every_season(self):
        world = TotalsWorld().totals_peers(2023).add_totals("subj", "Subject Person", 2023, None)
        found = only(world.check(("creative",)))
        self.assertEqual((found.verdict, found.reason), (verdicts.CANT, "season totals missing"))

    def test_synthetic_the_method_version_names_the_band(self):
        verdict = subject_at(PEERS).check(("creative",))
        self.assertIn("5-point band for season-totals metrics", verdict.method)


if __name__ == "__main__":
    unittest.main()
