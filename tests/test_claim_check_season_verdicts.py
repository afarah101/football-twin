"""Claim Check #44: per-season player Verdicts with a match bootstrap.

Every test here is synthetic: hand-made PlayerSeasons and PlayerMatches, kept out of tests/fixtures/.
Each player-season is split into 10 PlayerMatches of equal minutes, so the match bootstrap has something to resample.
Run from the repo root: python3 -m unittest tests.test_claim_check_season_verdicts
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from claim_check.domain import verdicts
from claim_check.domain.records import PlayerMatch
from claim_check.domain.verdicts import check
from claim_check.interface.cli import render
from test_claim_check_verdicts import LEAGUES, extraction
from twin.domain.records import PlayerSeason, Shot

MATCHES = 10


class SeasonWorld:
    """synthetic: each player-season is 10 PlayerMatches; `shots` non-penalty shots spread over them, `headers` of them headed."""

    def __init__(self):
        self.seasons, self.matches = [], []

    def add(self, player_id, name, season, shots=0, headers=0, goals=0, minutes=1800, league="ENG", held=False, club="Club"):
        self.seasons.append(PlayerSeason(player_id, name, league, season, (club,), minutes, minutes, 0, "FW", None, None, None, None, None, held))
        made = [Shot(player_id, league, season, 0.9, 0.5, 0.1, "OpenPlay", "Head" if i < headers else "RightFoot", None,
                     "Goal" if i < goals else "MissedShots") for i in range(shots)]
        for m in range(MATCHES):
            self.matches.append(PlayerMatch(player_id, league, season, f"{league}-{season}-{club}-{m}", club, minutes // MATCHES, "FW", False,
                                            tuple(made[m::MATCHES])))
        return self

    def peers(self, season, count=32, shots_step=3):
        # Peer k takes k * shots_step shots over 1,800 minutes: a spread of shot volumes, each in its own club and one of the 5 leagues.
        for k in range(count):
            self.add(f"peer{k}", f"Peer Number{k}", season, shots=k * shots_step, league=LEAGUES[k % 5], club=f"Club{k}")
        return self

    def check(self, words, **extra):
        return check("claim", extraction(name="Subject Person", words=words, **extra), tuple(self.seasons), tuple(self.matches))


def only(verdict):
    (found,) = verdict.readings
    return found


class PerSeasonTests(unittest.TestCase):
    def test_synthetic_a_peer_in_2_leagues_in_a_season_counts_once(self):
        world = SeasonWorld().peers(2023)
        world.add("peer0", "Peer Number0", 2023, shots=0, league="ESP", club="Other")  # peer0 also has 1,800 minutes in Spain
        world.add("subj", "Subject Person", 2023, shots=200)
        self.assertEqual(only(world.check(("shoots", "a", "lot"))).tests[0].reference_size, 32)

    def test_synthetic_one_test_per_qualifying_season(self):
        world = SeasonWorld()
        for season in (2021, 2022, 2023):
            world.peers(season).add("subj", "Subject Person", season, shots=200)
        found = only(world.check(("shoots", "a", "lot")))
        self.assertEqual([test.label for test in found.tests], ["2021/22", "2022/23", "2023/24"])
        self.assertEqual(found.verdict, verdicts.SUPPORTED)
        self.assertTrue(all(test.matches == MATCHES and test.reference_size == 32 for test in found.tests))

    def test_synthetic_aerial_threat_has_one_test_per_main_metric_per_season(self):
        world = SeasonWorld()
        for season in (2022, 2023):
            world.peers(season).add("subj", "Subject Person", season, shots=60, headers=40)
        found = only(world.check(("aerial", "threat")))
        self.assertEqual([test.label for test in found.tests], [
            "2022/23, headed shots per 90", "2022/23, headed npxG per 90", "2023/24, headed shots per 90", "2023/24, headed npxG per 90"])
        self.assertEqual(found.verdict, verdicts.SUPPORTED)

    def test_synthetic_season_under_900_minutes_is_skipped_not_a_miss(self):
        world = SeasonWorld()
        for season in (2021, 2022, 2023):
            world.peers(season)
        world.add("subj", "Subject Person", 2021, shots=200).add("subj", "Subject Person", 2022, shots=1, minutes=500)
        world.add("subj", "Subject Person", 2023, shots=200)
        found = only(world.check(("shoots", "a", "lot")))
        self.assertEqual(found.verdict, verdicts.SUPPORTED)  # the 500-minute season is not counted as a miss
        self.assertEqual([test.label for test in found.tests], ["2021/22", "2023/24"])
        self.assertIn("2022/23 not enough minutes", found.coverage)
        self.assertIn("Based on 2 of 3 seasons", found.coverage)

    def test_synthetic_every_season_skipped_is_too_few_minutes(self):
        world = SeasonWorld()
        for season in (2021, 2022, 2023):
            world.peers(season).add("subj", "Subject Person", season, shots=50, minutes=600)
        found = only(world.check(("shoots", "a", "lot")))
        self.assertEqual((found.verdict, found.reason), (verdicts.CANT, "too few minutes"))

    def test_synthetic_mixed_says_how_many_seasons_meet(self):
        world = SeasonWorld()
        for season, shots in ((2021, 200), (2022, 0), (2023, 200)):
            world.peers(season).add("subj", "Subject Person", season, shots=shots)
        found = only(world.check(("shoots", "a", "lot")))
        self.assertEqual((found.verdict, found.reason), (verdicts.MIXED, "2 of 3 seasons meet the threshold"))

    def test_synthetic_mixed_says_the_range_crosses_the_line(self):
        world = SeasonWorld().peers(2023)
        # 72 shots sit on the 75th-percentile line: some match resamples land below it, others above.
        world.add("subj", "Subject Person", 2023, shots=72)
        found = only(world.check(("shoots", "a", "lot"), seasons_named="2023/24"))
        (test,) = found.tests
        self.assertEqual(test.outcome, "borderline")
        self.assertEqual((found.verdict, found.reason), (verdicts.MIXED, "the range crosses the line"))

    def test_synthetic_negation_swaps_supported_only(self):
        world = SeasonWorld()
        for season in (2022, 2023):
            world.peers(season).add("subj", "Subject Person", season, shots=200)
        found = only(world.check(("shoots", "a", "lot"), polarity="negated"))
        self.assertEqual(found.verdict, verdicts.NOT_SUPPORTED)

    def test_synthetic_thin_evidence_when_under_half_the_window_remains(self):
        world = SeasonWorld()
        for season in (2021, 2022, 2023):
            world.peers(season)
        world.add("subj", "Subject Person", 2021, shots=200, minutes=500).add("subj", "Subject Person", 2022, shots=200, minutes=500)
        world.add("subj", "Subject Person", 2023, shots=200)
        found = only(world.check(("shoots", "a", "lot")))
        self.assertTrue(found.thin)
        self.assertIn("Thin evidence", render(world.check(("shoots", "a", "lot"))))

    def test_synthetic_fully_used_one_season_window_is_never_thin(self):
        world = SeasonWorld().peers(2023).add("subj", "Subject Person", 2023, shots=200)
        found = only(world.check(("shoots", "a", "lot"), seasons_named="2023/24"))
        self.assertEqual(found.coverage, "Based on 1 of 1 season.")
        self.assertFalse(found.thin)

    def test_synthetic_header_share_is_context_and_never_sets_the_verdict(self):
        verdicts_seen = []
        for headers in (0, 30):  # same headed volume share either side of the context metric would not change the Main metrics
            world = SeasonWorld().peers(2023, shots_step=1)
            world.add("subj", "Subject Person", 2023, shots=100 if headers else 30, headers=30)
            found = only(world.check(("aerial", "threat"), seasons_named="2023/24"))
            self.assertTrue(found.seasons_alone and found.seasons_alone[0].startswith("header share of shots, 2023/24"))
            verdicts_seen.append(found.verdict)
        self.assertEqual(verdicts_seen[0], verdicts_seen[1])  # 100% vs 30% header share, same headed shots: same Verdict

    def test_synthetic_peer_group_too_small_in_every_season(self):
        world = SeasonWorld().peers(2023, count=10).add("subj", "Subject Person", 2023, shots=200)
        found = only(world.check(("shoots", "a", "lot"), seasons_named="2023/24"))
        self.assertEqual((found.verdict, found.reason), (verdicts.CANT, "peer group too small"))

    def test_synthetic_availability_is_share_of_league_minutes(self):
        world = SeasonWorld().peers(2023)
        world.add("subj", "Subject Person", 2023, shots=10, minutes=900)  # 900 of 10 matches x 90 = 100%
        found = only(world.check(("regular", "starter"), seasons_named="2023/24"))
        (test,) = found.tests
        self.assertAlmostEqual(test.value, 900 / (MATCHES * 90))

    def test_synthetic_render_shows_each_season_test(self):
        world = SeasonWorld()
        for season in (2022, 2023):
            world.peers(season).add("subj", "Subject Person", season, shots=200)
        text = render(world.check(("shoots", "a", "lot")))
        self.assertIn("2022/23: ", text)
        self.assertIn("vs 32 peers, 10 matches: meets", text)
        self.assertIn("PlayerMatches (per-season metrics)", text)


if __name__ == "__main__":
    unittest.main()
