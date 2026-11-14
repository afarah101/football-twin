"""Claim Check #46: team and league Verdicts with a TeamMatch bootstrap.

Every test here is synthetic: hand-made TeamMatches, kept out of tests/fixtures/.
Run from the repo root: python3 -m unittest tests.test_claim_check_team_verdicts
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from claim_check.domain.records import TeamMatch
from claim_check.domain.verdicts import CANT, MIXED, NOT_SUPPORTED, SUPPORTED, check
from claim_check.domain.word_map import NotInCatalogue, league_readings, team_readings
from claim_check.interface.cli import render
from test_claim_check_verdicts import LEAGUES, extraction

MATCHES = 20
TEAMS = 12


def team_season(league, season, team, xg_for, xg_against, matches=MATCHES, wobble=0.1, goals_for=0, set_piece=0.0, outside=0, shots=10):
    """synthetic: `matches` TeamMatches; npxG alternates +-wobble around the mean so the bootstrap has spread."""
    return [TeamMatch(league, season, f"{league}-{season}-{team}-{m}", team, "Opponent",
                      xg_for + (wobble if m % 2 else -wobble), xg_against + (wobble if m % 2 else -wobble), set_piece, 0.0, shots, shots,
                      goals_for, 0, outside, 0) for m in range(matches)]


def league_world(season=2023, subject_against=0.5, subject_for=1.5, **subject):
    """11 peer teams in ENG with npxG for and against from 1.0 to 2.0, plus the Subject 'Solid Town'."""
    found = []
    for k in range(TEAMS - 1):
        found += team_season("ENG", season, f"Peer Club{k}", 1.0 + k / 10, 1.0 + k / 10)
    found += team_season("ENG", season, "Solid Town", subject_for, subject_against, **subject)
    return found


def run(world, name="Solid Town", words=("solid",), kind="team", **fields):
    return check("claim", extraction(name=name, words=words, kind=kind, **fields), (), (), world)


class TeamWordMap(unittest.TestCase):
    def test_synthetic_defensive_has_two_readings_each_with_its_meaning(self):
        found = team_readings(["defensive"])
        self.assertEqual([(r.claim_type, r.direction, r.meaning) for r in found],
                         [("Defence", "less", "they concede little"), ("Game openness", "less", "their games have few chances")])

    def test_synthetic_clinical_maps_to_team_finishing_for_a_team(self):
        self.assertEqual(team_readings(["clinical"])[0].claim_type, "Team finishing")

    def test_synthetic_pressing_is_metric_not_in_data(self):
        with self.assertRaises(NotInCatalogue) as caught:
            team_readings(["high", "press"])
        self.assertEqual(caught.exception.args[0], "metric not in data")

    def test_synthetic_league_level_words(self):
        (most,) = league_readings(["the", "most", "open"])
        self.assertEqual((most.direction, most.top), ("more", 1))
        (least,) = league_readings(["one", "of", "the", "least", "open"])
        self.assertEqual((least.direction, least.top), ("less", 2))
        for words in (["elite", "open"], ["open"]):
            with self.assertRaises(NotInCatalogue) as caught:
                league_readings(words)
            self.assertEqual(caught.exception.args[0], "level word does not fit a 5-league comparison")


class TeamVerdicts(unittest.TestCase):
    def test_synthetic_a_team_conceding_least_is_solid(self):
        verdict = run(league_world())
        (reading,) = verdict.readings
        self.assertEqual((verdict.subject, reading.verdict), ("Solid Town", SUPPORTED))
        self.assertEqual(len(reading.tests), 1)
        self.assertEqual(reading.reference_size, TEAMS - 1)
        self.assertIn("vs the other full-season teams in the Premier League", render(verdict))

    def test_synthetic_negated_claim_swaps_the_verdict(self):
        self.assertEqual(run(league_world(), polarity="negated").readings[0].verdict, NOT_SUPPORTED)

    def test_synthetic_a_leaky_team_is_not_solid(self):
        self.assertEqual(run(league_world(subject_against=2.5)).readings[0].verdict, NOT_SUPPORTED)

    def test_synthetic_defensive_gives_one_verdict_per_reading(self):
        # The Subject concedes little (Defence meets) but its games are not low on total npxG (2.5 + 0.5 = 3.0, mid-table): Mixed readings.
        verdict = run(league_world(subject_for=2.5), words=["defensive"])
        self.assertEqual([(r.claim_type, r.verdict) for r in verdict.readings], [("Defence", SUPPORTED), ("Game openness", NOT_SUPPORTED)])
        text = render(verdict)
        self.assertIn("Reading: they concede little", text)
        self.assertIn("Reading: their games have few chances", text)

    def test_synthetic_one_season_meets_and_one_misses_is_mixed(self):
        world = league_world(2022) + league_world(2023, subject_against=2.5)
        reading = run(world, seasons_named="2022/23-2023/24").readings[0]
        self.assertEqual((reading.verdict, reading.reason), (MIXED, "1 of 2 seasons meet the threshold"))

    def test_synthetic_a_part_season_is_skipped_and_none_full_is_cant(self):
        world = league_world(matches=MATCHES - 1)
        verdict = run(world)
        self.assertEqual((verdict.readings[0].verdict, verdict.readings[0].reason), (CANT, "too few matches"))

    def test_synthetic_too_few_peer_teams_is_cant(self):
        world = [found for found in league_world() if not found.team.startswith("Peer Club1")]  # drops Peer Club1 and Peer Club10
        reading = run(world).readings[0]
        self.assertEqual((reading.verdict, reading.reason), (CANT, "peer group too small"))

    def test_synthetic_pooled_team_finishing(self):
        world = league_world(goals_for=3)  # 3 goals a match on 1.5 npxG: far above every peer (0 goals)
        reading = run(world, words=["clinical"], tense="past").readings[0]
        self.assertEqual((reading.claim_type, reading.verdict), ("Team finishing", SUPPORTED))
        self.assertEqual(reading.test.matches, MATCHES)

    def test_synthetic_a_line_phrase_does_not_fit_a_team(self):
        verdict = run(league_world(), reference_named="for a midfielder")
        self.assertEqual(verdict.readings[0].reason, "peer group not in catalogue")

    def test_synthetic_unknown_and_ambiguous_teams(self):
        world = league_world() + team_season("ENG", 2023, "Solid Town Reserves", 1.0, 1.0)
        self.assertEqual(run(world, name="Nobody FC").readings[0].reason, "subject not in data")
        self.assertEqual(run(world).readings[0].reason, "subject is ambiguous")


class LeagueVerdicts(unittest.TestCase):
    def world(self, top=2.0):
        found = []
        for rank, league in enumerate(LEAGUES):
            for k in range(TEAMS):
                found += team_season(league, 2023, f"{league} Club{k}", (top if league == "ENG" else 1.0 + rank / 10) / 2,
                                     (top if league == "ENG" else 1.0 + rank / 10) / 2)
        return found

    def test_synthetic_the_most_open_league_ranks_first(self):
        verdict = run(self.world(), name="Premier League", words=["the", "most", "open"], kind="league")
        (reading,) = verdict.readings
        self.assertEqual((verdict.subject, reading.verdict, reading.test.rank), ("the Premier League", SUPPORTED, 1))
        self.assertIn("rank 1 of 5", render(verdict))

    def test_synthetic_the_least_open_league_is_not_supported_for_the_top(self):
        reading = run(self.world(), name="Premier League", words=["the", "least", "open"], kind="league").readings[0]
        self.assertEqual((reading.verdict, reading.test.rank), (NOT_SUPPORTED, 5))

    def test_synthetic_a_bare_league_word_is_cant(self):
        reading = run(self.world(), name="Premier League", words=["open"], kind="league").readings[0]
        self.assertEqual((reading.verdict, reading.reason), (CANT, "level word does not fit a 5-league comparison"))

    def test_synthetic_four_leagues_is_too_few(self):
        world = [found for found in self.world() if found.league != LEAGUES[-1]]
        reading = run(world, name="Premier League", words=["the", "most", "open"], kind="league").readings[0]
        self.assertEqual(reading.reason, "peer group too small")


if __name__ == "__main__":
    unittest.main()
