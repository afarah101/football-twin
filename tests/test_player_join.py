"""Rule 3 clauses, one test each. Real rows come from tests/fixtures/standin/rule3__*, cut by scripts/cut_fixtures.py.

A clause with 0 real cases uses a small hand-made input inside the test, says so in its name and in a comment, and never
goes in tests/fixtures/. Run from the repo root: python3 -m unittest discover tests
"""
import sys
import unittest
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.infrastructure.standin import player_join as join

SAMPLE = join.StandinFiles(ROOT / "tests" / "fixtures" / "standin", "rule3__")
SPEZIA_VERONA_TIE_BREAKER = "e0449015"
STREFEZZA_IDS = {"ac4a4508", "674cfc5a"}
MEITE_IDS = {"8eb68164", "cb9ef70f"}


@lru_cache(maxsize=None)
def sample_positions():
    return join.load_positions(SAMPLE)


@lru_cache(maxsize=None)
def sample_shots():
    return join.load_shots(SAMPLE)


@lru_cache(maxsize=None)
def sample_clubs():
    return join.understat_to_fbref_clubs(SAMPLE)


@lru_cache(maxsize=None)
def sample_date_links():
    return join.link_matches(sample_shots(), sample_positions(), sample_clubs())


@lru_cache(maxsize=None)
def sample_merges():
    return join.merge_fbref_ids(sample_positions())


def understat_match(league, season, home, away):
    """The sample's Understat match ids for one ordered pair, in date order."""
    shots = sample_shots()
    found = shots[(shots["league"] == league) & (shots["season"] == season) & (shots["home_team"] == home) & (shots["away_team"] == away)]
    return list(found.sort_values("date")["match_id"].drop_duplicates())


def fbref_rows(*rows):
    """Hand-made FBref rows, each (match, date, home, away, team, player, fbref_id, minutes). Only synthetic tests use it."""
    columns = ["match", "Match_Date", "Home_Team", "Away_Team", "Team", "Player", "fbref_id", "Min"]
    frame = pd.DataFrame(rows, columns=columns)
    return frame.assign(league="ESP", Season_End_Year=2021, Pos="FW", Matchweek="Regular Season")


def shot_rows(*rows):
    """Hand-made shot rows, each (match_id, date, home_team, away_team). Only synthetic tests use it."""
    frame = pd.DataFrame(rows, columns=["match_id", "date", "home_team", "away_team"])
    return frame.assign(league="ESP", season=2020, player="Kike", player_id=1, side="h")


HAND_MADE_CLUBS = {("ESP", "A"): "A", ("ESP", "B"): "B"}


class StageARule2AndIdMerges(unittest.TestCase):
    def test_a_tie_breaker_match_is_excluded_from_minutes(self):
        raw = pd.read_parquet(SAMPLE.path("ITA_M_1st_positions.parquet"))
        self.assertEqual(raw["MatchURL"].str.contains(SPEZIA_VERONA_TIE_BREAKER).sum(), 31)
        self.assertNotIn(SPEZIA_VERONA_TIE_BREAKER, set(sample_positions()["match"]))

    def test_a_synthetic_tie_breaker_match_is_excluded_from_shots(self):
        # synthetic: 0 real, no shot row falls on the tie-breaker's date (T7:750).
        positions = join.without_tie_breakers(fbref_rows(("m1", "2021-05-30", "A", "B", "A", "Kike", "x", 90)).assign(Matchweek="Relegation tie-breaker"))
        links = join.link_matches(shot_rows((1, "2021-05-30 18:00:00", "A", "B")), positions, HAND_MADE_CLUBS)
        self.assertEqual(links.links, {})
        self.assertEqual(links.dropped_rows, {("ESP", 2020): 1})

    def test_a_match_links_on_home_away_and_season(self):
        links = sample_date_links().links
        brighton = understat_match("ENG", 2023, "Brighton", "Everton")[0]
        positions = sample_positions()
        match = positions[positions["match"] == links[("ENG", brighton)]].iloc[0]
        self.assertEqual((match["Home_Team"], match["Away_Team"], match["Season_End_Year"]), ("Brighton & Hove Albion", "Everton", 2024))
        # The same real rows, read as one season later, have no match to link to, so the season is part of the key.
        shots = sample_shots()
        next_season = shots[(shots["league"] == "ENG") & (shots["match_id"] == brighton)].assign(season=2024)
        self.assertEqual(join.link_matches(next_season, positions, sample_clubs()).links, {})

    def test_a_match_links_only_in_home_away_order(self):
        links = sample_date_links().links
        positions = sample_positions().drop_duplicates("match").set_index("match")
        for home, away, fbref_home in (("Getafe", "Cadiz", "Getafe"), ("Cadiz", "Getafe", "Cádiz")):
            self.assertEqual(positions.loc[links[("ESP", understat_match("ESP", 2023, home, away)[0])], "Home_Team"], fbref_home)
        getafe_home = understat_match("ESP", 2023, "Getafe", "Cadiz")[0]
        self.assertNotEqual(links[("ESP", getafe_home)], links[("ESP", understat_match("ESP", 2023, "Cadiz", "Getafe")[0])])
        # The real legs are months apart, so date alone would pick the right one. With only the reverse leg left, and the
        # shot rows moved in memory to its date, nothing may link.
        reverse_leg = sample_positions()[sample_positions()["match"] == links[("ESP", understat_match("ESP", 2023, "Cadiz", "Getafe")[0])]]
        shots = sample_shots()
        moved = shots[(shots["league"] == "ESP") & (shots["match_id"] == getafe_home)].assign(date=reverse_leg["Match_Date"].iloc[0])
        self.assertEqual(join.link_matches(moved, reverse_leg, sample_clubs()).links, {})

    def test_a_club_names_go_through_club_map(self):
        clubs = sample_clubs()
        self.assertEqual(clubs[("ENG", "Brighton")], "Brighton & Hove Albion")
        # The file's 168 rows hold 14 with one side blank, which map nothing.
        self.assertEqual(sum(understat != fbref for (_, understat), fbref in clubs.items()), 43)
        self.assertEqual(len(clubs), 154)

    def test_a_synthetic_nearest_fbref_date_wins(self):
        # synthetic: 0 real ordered pairs on 2+ matches (design check).
        positions = fbref_rows(("far", "2021-01-20", "A", "B", "A", "Kike", "x", 90), ("near", "2021-01-12", "A", "B", "A", "Kike", "x", 90))
        links = join.link_matches(shot_rows((1, "2021-01-10 18:00:00", "A", "B")), positions, HAND_MADE_CLUBS)
        self.assertEqual(links.links, {("ESP", 1): "near"})

    def test_a_date_gap_days_recorded_on_rescheduled_match(self):
        date_links = sample_date_links()
        caen_toulouse = understat_match("FRA", 2017, "Caen", "Toulouse")[0]
        rows = join.with_date_link(sample_shots(), date_links)
        linked = rows[rows["match_id"] == caen_toulouse]
        self.assertTrue(len(linked))
        self.assertEqual(set(linked["date_gap_days"]), {11})
        self.assertTrue(rows["date_gap_days"].notna().all())

    def test_a_gap_over_1_day_is_listed(self):
        listed = {(league, match_id): gap for league, match_id, gap in sample_date_links().listed_gaps}
        self.assertEqual(listed, {("FRA", 8886): 11, ("FRA", 19973): 2, ("ITA", 22621): 11})

    def test_a_synthetic_gap_over_14_days_does_not_link(self):
        # synthetic: 0 real, the largest real gap is 11 days (design check, gap days).
        positions = fbref_rows(("m1", "2021-01-25", "A", "B", "A", "Kike", "x", 90))
        self.assertEqual(join.link_matches(shot_rows((1, "2021-01-10 18:00:00", "A", "B")), positions, HAND_MADE_CLUBS).links, {})

    def test_a_synthetic_gap_over_14_days_drops_and_counts_rows(self):
        # synthetic: 0 real, the largest real gap is 11 days (design check, gap days).
        positions = fbref_rows(("m1", "2021-01-25", "A", "B", "A", "Kike", "x", 90))
        shots = shot_rows((1, "2021-01-10 18:00:00", "A", "B"), (1, "2021-01-10 18:00:00", "A", "B"))
        date_links = join.link_matches(shots, positions, HAND_MADE_CLUBS)
        self.assertEqual(date_links.dropped_rows, {("ESP", 2020): 2})
        self.assertTrue(join.with_date_link(shots, date_links).empty)

    def test_a_synthetic_gap_of_exactly_14_days_links(self):
        # synthetic: 0 real, the largest real gap is 11 days (design check, gap days).
        positions = fbref_rows(("m1", "2021-01-24", "A", "B", "A", "Kike", "x", 90))
        links = join.link_matches(shot_rows((1, "2021-01-10 18:00:00", "A", "B")), positions, HAND_MADE_CLUBS)
        self.assertEqual(links.links, {("ESP", 1): "m1"})
        self.assertEqual(links.gap_days, {("ESP", 1): 14})

    def test_a_synthetic_equal_date_gap_takes_lowest_match_id(self):
        # synthetic: 0 real ordered pairs on 2+ matches (design check, ordered pairs).
        positions = fbref_rows(("m2", "2021-01-08", "A", "B", "A", "Kike", "x", 90), ("m1", "2021-01-12", "A", "B", "A", "Kike", "x", 90))
        links = join.link_matches(shot_rows((1, "2021-01-10 18:00:00", "A", "B")), positions, HAND_MADE_CLUBS)
        self.assertEqual(links.links, {("ESP", 1): "m1"})
        self.assertEqual(links.equal_gaps, [("ESP", 1, ("m1", "m2"))])

    def test_a_match_without_fbref_minutes_drops_its_shots(self):
        match = understat_match("ITA", 2023, "Atalanta", "Fiorentina")[0]
        # The cut takes this pair's FBref rows by club names, not through the link under test, so the sample shows the file holds none.
        positions = sample_positions()
        self.assertFalse(((positions["Home_Team"] == "Atalanta") & (positions["Away_Team"] == "Fiorentina") & (positions["Season_End_Year"] == 2024)).any())
        self.assertNotIn(("ITA", match), sample_date_links().links)
        self.assertEqual(len(sample_shots().query("match_id == @match")), 20)
        self.assertFalse((join.with_date_link(sample_shots(), sample_date_links())["match_id"] == match).any())

    def test_a_dropped_shots_are_counted_per_league_season(self):
        self.assertEqual(sample_date_links().dropped_rows[("ITA", 2023)], 20)

    def test_a_shots_before_pool_seasons_are_untouched(self):
        raw = pd.read_parquet(SAMPLE.path("la_liga_shot_data.parquet"))
        raw = raw[raw["season"] == 2016].reset_index(drop=True)
        self.assertTrue(len(raw))
        earlier = join.earlier_shots(SAMPLE)
        earlier = earlier[(earlier["league"] == "ESP") & (earlier["season"] == 2016)].reset_index(drop=True)
        pd.testing.assert_frame_equal(earlier[raw.columns.drop("league")], raw.drop(columns="league"))
        self.assertFalse((sample_shots()["season"] == 2016).any())

    def test_a_league_comes_from_the_file_name(self):
        raw = pd.read_parquet(SAMPLE.path("la_liga_shot_data.parquet"))
        self.assertEqual(set(raw["league"]), {"La_liga", "La liga"})
        shots = pd.concat([sample_shots(), join.earlier_shots(SAMPLE)])
        self.assertEqual(set(shots.loc[shots["match_id"].isin(raw["match_id"]), "league"]), {"ESP"})

    def test_a_two_ids_merge_when_name_team_season_match(self):
        merged, _, _ = sample_merges()
        strefezza = merged[(merged["league"] == "ITA") & (merged["Season_End_Year"] == 2024) & (merged["Player"] == "Gabriel Strefezza")]
        self.assertEqual(sample_positions().loc[strefezza.index, "fbref_id"].nunique(), 2)
        self.assertEqual(strefezza["fbref_id"].nunique(), 1)

    def test_a_every_merge_is_listed(self):
        _, done, _ = sample_merges()
        self.assertEqual(sorted((merge.league, merge.player) for merge in done), [("FRA", "Abdoul Meité"), ("FRA", "Joseph Nduquidi"), ("ITA", "Gabriel Strefezza")])

    def test_a_same_name_at_different_team_does_not_merge(self):
        merged, done, refused = sample_merges()
        juanfran = merged[(merged["league"] == "ESP") & (merged["Season_End_Year"] == 2018) & (merged["Player"] == "Juanfran")]
        self.assertEqual(juanfran["Team"].nunique(), 2)
        self.assertEqual(juanfran["fbref_id"].nunique(), 2)
        self.assertNotIn("Juanfran", {merge.player for merge in [*done, *refused]})

    def test_a_synthetic_overlapping_ids_do_not_merge_and_are_listed(self):
        # synthetic: 0 real (design check, merge results).
        positions = fbref_rows(("m1", "2021-01-10", "A", "B", "A", "Kike", "x", 90), ("m1", "2021-01-10", "A", "B", "A", "Kike", "y", 10))
        merged, done, refused = join.merge_fbref_ids(positions)
        self.assertEqual(set(merged["fbref_id"]), {"x", "y"})
        self.assertEqual(done, [])
        self.assertEqual([(case.player, case.ids, case.reason) for case in refused], [("Kike", ("x", "y"), "matches overlap")])

    def test_a_merged_player_keeps_id_from_other_seasons(self):
        _, done, _ = sample_merges()
        self.assertEqual({merge.player: merge.survivor for merge in done}["Gabriel Strefezza"], "ac4a4508")
        positions = sample_positions()
        this_season = positions[(positions["league"] == "ITA") & (positions["Season_End_Year"] == 2024) & positions["fbref_id"].isin(STREFEZZA_IDS)].groupby("fbref_id")["Min"].sum()
        self.assertGreater(this_season["674cfc5a"], this_season["ac4a4508"], "other seasons must beat minutes here")
        self.assertTrue((positions[positions["fbref_id"] == "ac4a4508"]["Season_End_Year"] != 2024).any())
        self.assertFalse((positions[positions["fbref_id"] == "674cfc5a"]["Season_End_Year"] != 2024).any())

    def test_a_merged_player_keeps_id_with_more_minutes(self):
        _, done, _ = sample_merges()
        meite = next(merge for merge in done if merge.player == "Abdoul Meité")
        self.assertEqual(set(meite.ids), MEITE_IDS)
        self.assertEqual(meite.survivor, "8eb68164")
        positions = sample_positions()
        self.assertFalse(((positions["fbref_id"].isin(MEITE_IDS)) & (positions["Season_End_Year"] != 2024)).any())
        minutes = positions[positions["fbref_id"].isin(MEITE_IDS)].groupby("fbref_id")["Min"].sum()
        self.assertGreater(minutes["8eb68164"], minutes["cb9ef70f"])
        # The id with more minutes also sorts first, so relabel it in memory to sort last: minutes must still decide.
        relabelled = positions[positions["fbref_id"].isin(MEITE_IDS)].replace({"fbref_id": {"8eb68164": "ffffffff"}})
        _, done, _ = join.merge_fbref_ids(relabelled)
        self.assertEqual([merge.survivor for merge in done], ["ffffffff"])

    def test_a_synthetic_equal_minutes_keeps_id_that_sorts_first(self):
        # synthetic: 0 real (design check, merge results).
        positions = fbref_rows(("m1", "2021-01-10", "A", "B", "A", "Kike", "y", 90), ("m2", "2021-01-17", "B", "A", "A", "Kike", "x", 90))
        merged, done, _ = join.merge_fbref_ids(positions)
        self.assertEqual(set(merged["fbref_id"]), {"x"})
        self.assertEqual([(merge.survivor, merge.equal_minutes) for merge in done], [("x", True)])

    def test_a_synthetic_both_ids_in_other_seasons_do_not_merge(self):
        # synthetic: 0 real (design check, merge results).
        this_season = fbref_rows(("m1", "2021-01-10", "A", "B", "A", "Kike", "x", 90), ("m2", "2021-01-17", "B", "A", "A", "Kike", "y", 90))
        other_season = fbref_rows(("m3", "2020-01-10", "A", "B", "A", "Kike", "x", 90), ("m4", "2020-01-17", "B", "A", "A", "Kike", "y", 90)).assign(Season_End_Year=2020, Team=["A", "B"])
        merged, done, refused = join.merge_fbref_ids(pd.concat([this_season, other_season], ignore_index=True))
        self.assertEqual(set(merged["fbref_id"]), {"x", "y"})
        self.assertEqual(done, [])
        self.assertEqual([(case.player, case.reason) for case in refused], [("Kike", "both ids in other seasons")])

    def test_a_merges_off_leaves_two_ids_apart(self):
        self.assertEqual(set(join.positions_for_join(SAMPLE, merges=False).query("Player == 'Gabriel Strefezza' and Season_End_Year == 2024")["fbref_id"]), STREFEZZA_IDS)
        self.assertEqual(set(join.positions_for_join(SAMPLE, merges=True).query("Player == 'Gabriel Strefezza' and Season_End_Year == 2024")["fbref_id"]), {"ac4a4508"})


if __name__ == "__main__":
    unittest.main()
