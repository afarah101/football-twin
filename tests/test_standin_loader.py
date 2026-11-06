"""The adapter seam: the stand-in loader on tests/fixtures/standin/loader_sample/, and the record checks (D10, D11).

The sample's own review_decisions.csv is copied whole from data/standin/, and its one row names Ezzalzouli, who is not in
the sample, so each test loads a copy of the folder with its own decisions file. The sample is cut as whole matches, so
most of its players hold partial seasons: the loader runs with the season totals checks (D3, D4) off, and the checks run
on a named candidate only. A clause with 0 real cases uses a small hand-made input, says so in its name and in a comment,
and never goes in tests/fixtures/.
Run from the repo root: python3 -m unittest discover tests
"""
import dataclasses
import html
import shutil
import socket
import sys
import unittest
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.domain.pool import in_pool, is_pool_candidate
from twin.domain.records import LoadedSource, PlayerSeason, Shot
from twin.infrastructure.standin import loader
from twin.infrastructure.standin import player_join as join

SAMPLE = ROOT / "tests" / "fixtures" / "standin" / "loader_sample"
HEADER = "item_type,key,decision,fbref_id,reviewer,date,reason\n"
JOHNSEN = ("ITA", 2021, "66784dee")
JOHNSEN_APPROVE = HEADER + "player_season,ITA|2021|66784dee,approve,,x,2026-01-01,synthetic: hand-made row on Dennis Johnsen's real data\n"


def sample_copy(decisions_text, folder):
    """A copy of loader_sample/ whose review_decisions.csv holds `decisions_text`."""
    for path in SAMPLE.iterdir():
        if path.name != "review_decisions.csv":
            shutil.copy(path, folder)
    (Path(folder) / "review_decisions.csv").write_text(decisions_text, encoding="utf8")
    return join.StandinFiles(Path(folder))


def load_copy(decisions_text, folder):
    return loader.load_standin(sample_copy(decisions_text, folder), season_checks=False)


def checked_join(candidate, decisions_text=HEADER):
    """The join on the sample with D3 and D4 on, for one candidate: the cut holds partial seasons for every other player."""
    with TemporaryDirectory() as folder:
        files = sample_copy(decisions_text, folder)
        positions, _, refused = join.merge_fbref_ids(join.load_positions(files))
        shots, clubs = join.load_shots(files), join.understat_to_fbref_clubs(files)
        rows_of = join.shot_groups(shots, join.link_matches(shots, positions, clubs).links, positions)[0]
        rosters = join.build_rosters(positions)
        facts = join.guard_facts(positions, shots, join.season_rows_by_name(clubs, files))
        decisions = join.read_review_decisions(files.path("review_decisions.csv"))
        return join.finish_join(join.rule3_links(rows_of, rosters, facts), rows_of, rosters, positions, decisions, refused, lambda _: [candidate], facts, season_checks=True)


@lru_cache(maxsize=None)
def sample_run(decisions_text=HEADER):
    with TemporaryDirectory() as folder:
        return load_copy(decisions_text, folder)


def record(league, season, player_id, run=None):
    found = [found for found in (run or sample_run()).loaded.player_seasons if (found.league, found.season, found.player_id) == (league, season, player_id)]
    assert len(found) == 1, (league, season, player_id, found)
    return found[0]


@lru_cache(maxsize=None)
def sample_positions(league):
    return pd.read_parquet(SAMPLE / f"{league}_M_1st_positions.parquet")


def fixture_rows(league, season, player_id):
    rows = sample_positions(league)
    return rows[(rows["Season_End_Year"] == season + 1) & (rows["Player_Href"].str.contains(f"/players/{player_id}/"))]


def came_on(league):
    events = pd.read_parquet(SAMPLE / f"{league}_M_1st_match_summary.parquet")
    events = events[events["Event_Type"] == "Substitute"]
    return set(zip(events["MatchURL"], events["Event_Players"].str.split(" for ").str[0].str.strip()))


def hand_player_season(player_id="x", minutes=900, held_for_review=False, totals=(1.0, 10, 2.0, 5, 3)):
    """A hand-made PlayerSeason. Only synthetic tests use it."""
    return PlayerSeason(player_id, "Kike", "ESP", 2021, ("A",), minutes, 600, 300, "FW", *totals, held_for_review)


def hand_shot(player_id="x"):
    """A hand-made Shot. Only synthetic tests use it."""
    return Shot(player_id, "ESP", 2021, 0.9, 0.5, 0.3, "OpenPlay", "RightFoot", "Pass", "Goal")


HAND_POSITIONS = pd.DataFrame({"league": ["ESP"], "Season_End_Year": [2022], "fbref_id": ["x"], "Min": [900]})


class LoaderRecords(unittest.TestCase):
    def test_league_move_gives_two_player_seasons(self):
        # Real: Lucas Moura 2017/18, Ligue 1 then the Premier League.
        found = sorted((found.league, found.minutes) for found in sample_run().loaded.player_seasons if (found.season, found.player_id) == (2017, "2b622f01"))
        self.assertEqual([league for league, _ in found], ["ENG", "FRA"])
        for league, minutes in found:
            self.assertEqual(minutes, int(fixture_rows(league, 2017, "2b622f01")["Min"].sum()))

    def test_shared_name_gives_two_player_seasons(self):
        # Real: Nacho ESP 2019/20, one name on two FBref ids.
        first, second = record("ESP", 2019, "2946f9a1"), record("ESP", 2019, "e29d1111")
        self.assertEqual((first.name, second.name), ("Nacho", "Nacho"))
        self.assertNotEqual(first.clubs, second.clubs)

    def test_own_goal_and_penalty_stay_on_shot_records(self):
        # Real: match 7890, Víctor Camarasa's own goal. #8 owns the filter, so the records keep both.
        shots = pd.read_parquet(SAMPLE / "la_liga_shot_data.parquet")
        own_goal = shots[(shots["match_id"] == 7890) & (shots["result"] == "OwnGoal")].iloc[0]
        loaded = sample_run().loaded.shots
        self.assertIn(("ESP", 2017, float(own_goal["X"]), float(own_goal["Y"]), float(own_goal["xG"]), "OwnGoal"), {(shot.league, shot.season, shot.x, shot.y, shot.xg, shot.result) for shot in loaded})
        self.assertTrue(any(shot.situation == "Penalty" for shot in loaded))

    def test_under_900_player_season_is_returned_and_out_of_pool(self):
        # Real: Lukas Nmecha GER 2022/23, 899 minutes.
        nmecha = record("GER", 2022, "0cc5f4a5")
        self.assertEqual(nmecha.minutes, 899)
        self.assertFalse(in_pool(nmecha))

    def test_any_attacking_label_counts_as_attacking(self):
        # Real: Ben Brereton ENG 2023/24, whose `FW,LW` and `LM,FW` rows count as attacking.
        rows = fixture_rows("ENG", 2023, "57827369")
        started = rows[[(url, player) not in came_on("ENG") for url, player in zip(rows["MatchURL"], rows["Player"])]]
        labels = started["Pos"].str.split(",")
        any_label = int(started.loc[labels.map(lambda found: bool(set(found) & join.ATTACKING_POS)), "Min"].sum())
        single_label = int(started.loc[labels.map(lambda found: len(found) == 1 and found[0] in join.ATTACKING_POS), "Min"].sum())
        self.assertIn("FW,LW", set(started["Pos"]))
        self.assertGreater(any_label, single_label)
        self.assertEqual(record("ENG", 2023, "57827369").attacking_minutes, any_label)

    def test_lm_rm_only_stays_out_of_pool(self):
        # Real: Robbie Brady ENG 2020/21, 900+ minutes on LM and RM only, which stay other.
        brady = record("ENG", 2020, "96bb8cc2")
        self.assertGreaterEqual(brady.minutes, 900)
        self.assertEqual(brady.attacking_minutes, 0)
        self.assertFalse(in_pool(brady))

    def test_substitute_appearance_is_ignored_for_position(self):
        # Real: match 30d3212e, where Radamel Falcao came on for 9 minutes, his only ESP 2023/24 row in the sample.
        falcao = record("ESP", 2023, "66116290")
        self.assertEqual((falcao.minutes, falcao.attacking_minutes, falcao.other_minutes), (9, 0, 0))

    def test_match_with_no_events_counts_as_start(self):
        # Real: plan line 126, 3,091 rows. Match 05060e6f has no event rows, so Ángel Algobia's 13 minutes count as a start.
        algobia = record("ESP", 2022, "acc1aefa")
        self.assertEqual((algobia.minutes, algobia.attacking_minutes, algobia.other_minutes), (13, 13, 0))
        unknown = sample_run().review.sub_status_unknown
        self.assertIn(("ESP", 2022, "05060e6f", "acc1aefa"), unknown)
        self.assertEqual(sum(row[2] == "05060e6f" for row in unknown), int((sample_positions("ESP")["MatchURL"].str.contains("/05060e6f/")).sum()))

    def test_null_min_adds_zero_and_keeps_the_appearance(self):
        # Real: plan line 127, 4 rows, each kept with 0 minutes and listed as `min_missing = yes`.
        missing = sample_run().review.min_missing
        self.assertEqual(sorted(missing), [("ENG", 2017, "0e98ac46", "76c131da"), ("FRA", 2022, "58f908b1", "88f130ed"), ("ITA", 2021, "eb75d1da", "03f946ed"), ("ITA", 2023, "bca64d25", "bba30585")])
        for league, season, _, player_id in missing:
            self.assertEqual(record(league, season, player_id).minutes, int(fixture_rows(league, season, player_id)["Min"].sum()))

    def test_totals_reach_guirassy_through_fbref_name(self):
        # Real: Q5. The season file spells him Serhou, the shots Sehrou, so the lookup falls back to the FBref name.
        totals = pd.read_parquet(SAMPLE / "understat_xg_data.parquet")
        row = totals[(totals["player_name"] == "Serhou Guirassy") & (totals["season"] == "2018-2019") & (totals["league"] == "FRA")].iloc[0]
        guirassy = record("FRA", 2018, "923f4dda")
        self.assertEqual((guirassy.goals, guirassy.assists, guirassy.key_passes), (int(row["goals"]), int(row["assists"]), int(row["key_passes"])))
        self.assertAlmostEqual(guirassy.xa, float(row["xA"]))
        self.assertEqual(sample_run().review.season_totals[("FRA", 2019, "923f4dda")].route, "FBref name")

    def test_totals_narrow_by_club_when_two_rows_share_a_name(self):
        # Real: Q5, Emerson ENG 2022/23, one of 12 Pool candidates. Two rows share the name, and the linked club picks one.
        found = sample_run().review.season_totals[("ENG", 2023, "df8b52a5")]
        self.assertEqual(found.route, "shot name + club")
        self.assertEqual(found.row.clubs, {"Tottenham Hotspur"})
        self.assertAlmostEqual(record("ENG", 2022, "df8b52a5").xa, found.row.xa)

    def test_player_season_outside_the_pool_with_no_totals_row_has_none(self):
        # Real: Mathias Jørgensen ENG 2017/18, one of 772 (design check).
        jorgensen = record("ENG", 2017, "0db5d2c8")
        self.assertEqual((jorgensen.xa, jorgensen.key_passes, jorgensen.xg_buildup, jorgensen.goals, jorgensen.assists), (None,) * 5)
        self.assertFalse(is_pool_candidate(jorgensen.minutes, jorgensen.attacking_minutes, jorgensen.other_minutes))

    def test_player_season_name_takes_the_spelling_with_most_minutes(self):
        # Real: D7, Jarell Quansah 1,074 minutes and Jarrell Quansah 116, ENG 2023/24.
        minutes = fixture_rows("ENG", 2023, "4125cb98").groupby("Player")["Min"].sum()
        self.assertEqual(len(minutes), 2)
        self.assertEqual(record("ENG", 2023, "4125cb98").name, "Jarell Quansah")

    def test_display_position_tie_is_alphabetical(self):
        # Real: plan line 120, 918 ties. ENG 2017/18 2f90f6b8 leads with AM, LW and RW once each.
        first = fixture_rows("ENG", 2017, "2f90f6b8")["Pos"].str.split(",").str[0]
        self.assertEqual(sorted(first[first.isin(join.ATTACKING_POS)]), ["AM", "LW", "RW"])
        self.assertEqual(record("ENG", 2017, "2f90f6b8").display_position, "AM")

    def test_roger_gap_of_3_passes(self):
        # Real: Roger ESP 2023/24, totals 36 and shot rows minus own goals 33. The limit is not raised.
        roger = ("ESP", 2024, "0ae4e09a")
        result = checked_join(roger)
        self.assertEqual(result.season_totals[roger].gap, 3)
        self.assertEqual(result.pool, [roger])
        self.assertEqual(sample_run().review.season_totals[roger].gap, 3)
        self.assertTrue(in_pool(record("ESP", 2023, "0ae4e09a")))

    def test_partial_join_outside_the_candidates_is_held(self):
        # Real: plan line 137, Jeffinho FRA 2022/23, 1 of 10 rows joined.
        jeffinho = record("FRA", 2022, "45cce300")
        self.assertTrue(jeffinho.held_for_review)
        self.assertFalse(is_pool_candidate(jeffinho.minutes, jeffinho.attacking_minutes, jeffinho.other_minutes))

    def test_candidate_already_held_with_no_totals_row_does_not_fail(self):
        # Real: Ruslan Malinovskyi ITA 2019/20, one of 27, held for no joined shots.
        malinovskyi = record("ITA", 2019, "48d5bd33")
        self.assertTrue(malinovskyi.held_for_review)
        self.assertTrue(is_pool_candidate(malinovskyi.minutes, malinovskyi.attacking_minutes, malinovskyi.other_minutes))
        self.assertIsNone(malinovskyi.xa)
        result = checked_join(("ITA", 2020, "48d5bd33"))
        self.assertEqual((result.pool, result.held_without_totals), ([], [("ITA", 2020, "48d5bd33")]))

    def test_synthetic_approve_on_flagged_candidate_with_small_gap_is_valid(self):
        # synthetic: hand-made row on Dennis Johnsen's real data. He is flagged `partial_join` with a gap of 3 or less.
        johnsen = ("ITA", 2022, "66784dee")
        self.assertEqual(checked_join(johnsen).pool, [])
        result = checked_join(johnsen, JOHNSEN_APPROVE)
        self.assertLessEqual(result.season_totals[johnsen].gap, 3)
        self.assertEqual(result.pool, [johnsen])
        self.assertTrue(in_pool(record(*JOHNSEN, run=sample_run(JOHNSEN_APPROVE))))


class LoaderSeam(unittest.TestCase):
    def test_loader_makes_no_network_calls(self):
        # Real: loader_sample, loaded with sockets blocked.
        with TemporaryDirectory() as folder, mock.patch.object(socket, "socket", side_effect=AssertionError("network call")), mock.patch.object(socket, "create_connection", side_effect=AssertionError("network call")):
            loaded = load_copy(HEADER, folder).loaded
        self.assertTrue(loaded.player_seasons)

    def test_loader_returns_only_pool_seasons(self):
        # Real: the current_season rows, Cameron Puertas 2025/26, are not returned.
        loaded = sample_run().loaded
        seasons = {found.season for found in loaded.player_seasons} | {shot.season for shot in loaded.shots}
        self.assertLessEqual(seasons, set(range(join.POOL_FIRST_SEASON, join.POOL_LAST_SEASON + 1)))
        self.assertIn(2017, seasons)
        self.assertNotIn("185a2732", {found.player_id for found in loaded.player_seasons} | {shot.player_id for shot in loaded.shots})

    def test_standin_loader_may_publish_is_always_false(self):
        # Real: Dennis Johnsen in loader_sample. No review row and no flag changes it.
        self.assertFalse(sample_run().loaded.may_publish)
        approved = sample_run(JOHNSEN_APPROVE)
        self.assertFalse(approved.loaded.may_publish)
        self.assertFalse(record(*JOHNSEN, run=approved).held_for_review)
        with TemporaryDirectory() as folder:
            for path in SAMPLE.iterdir():
                shutil.copy(path, folder)
            (Path(folder) / "review_decisions.csv").write_text(HEADER, encoding="utf8")
            self.assertFalse(loader.StandinLoader(join.StandinFiles(Path(folder)), season_checks=False).load().may_publish)

    def test_loader_result_names_its_source_and_records_have_no_may_publish(self):
        # Real: loader_sample.
        loaded = sample_run().loaded
        self.assertIsInstance(loaded, LoadedSource)
        self.assertEqual(loaded.source, "standin")
        self.assertIsInstance(loaded.player_seasons[0], PlayerSeason)
        self.assertIsInstance(loaded.shots[0], Shot)
        for record_type in (PlayerSeason, Shot):
            self.assertNotIn("may_publish", {field.name for field in dataclasses.fields(record_type)})


class PoolRuleOnRealValues(unittest.TestCase):
    def test_pool_needs_900_minutes(self):
        # Real values: Lukas Nmecha, 899.
        nmecha = record("GER", 2022, "0cc5f4a5")
        self.assertGreater(nmecha.attacking_minutes, nmecha.other_minutes)
        self.assertFalse(in_pool(nmecha))
        self.assertTrue(in_pool(dataclasses.replace(nmecha, minutes=900)))

    def test_pool_needs_attacking_above_other(self):
        # Real values: Robbie Brady.
        brady = record("ENG", 2020, "96bb8cc2")
        self.assertFalse(in_pool(brady))
        self.assertTrue(in_pool(dataclasses.replace(brady, attacking_minutes=brady.other_minutes + 1)))

    def test_pool_held_player_season_stays_out(self):
        # Real values: Dennis Johnsen, held for `partial_join`.
        johnsen = record(*JOHNSEN)
        self.assertTrue(is_pool_candidate(johnsen.minutes, johnsen.attacking_minutes, johnsen.other_minutes))
        self.assertFalse(in_pool(johnsen))
        self.assertTrue(in_pool(dataclasses.replace(johnsen, held_for_review=False)))


class RecordChecks(unittest.TestCase):
    def assert_records_stop(self, needle, player_seasons, shots=()):
        with self.assertRaises(SystemExit) as stop:
            loader.check_records(list(player_seasons), list(shots), HAND_POSITIONS)
        self.assertIn(needle, str(stop.exception))

    def test_synthetic_lost_minutes_fail_the_run(self):
        # synthetic: 0 real. 24,894,121 minutes before and after the merges (D10).
        loader.check_records([hand_player_season()], [hand_shot()], HAND_POSITIONS)
        self.assert_records_stop("ESP 2021", [hand_player_season(minutes=899)])

    def test_synthetic_repeated_player_season_key_fails_the_run(self):
        # synthetic: 0 real, 19,062 keys (D10).
        self.assert_records_stop("ESP|2021|x", [hand_player_season(minutes=450), hand_player_season(minutes=450)])

    def test_synthetic_shot_without_player_season_fails_the_run(self):
        # synthetic: 0 real (D10).
        self.assert_records_stop("z", [hand_player_season()], [hand_shot("z")])

    def test_synthetic_not_held_without_totals_fails_the_run(self):
        # synthetic: 0 real (D11). D4 fails the run or holds such a player first, so this means a code fault.
        self.assert_records_stop("ESP|2021|x", [hand_player_season(totals=(None,) * 5)])
        loader.check_records([hand_player_season(totals=(None,) * 5, held_for_review=True)], [], HAND_POSITIONS)


if __name__ == "__main__":
    unittest.main()
