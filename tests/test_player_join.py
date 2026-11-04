"""Rule 3 clauses, one test each. Real rows come from tests/fixtures/standin/rule3__*, cut by scripts/cut_fixtures.py.

A clause with 0 real cases uses a small hand-made input inside the test, says so in its name and in a comment, and never
goes in tests/fixtures/. Run from the repo root: python3 -m unittest discover tests
"""
import html
import sys
import unittest
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import measure_rule3 as script
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


@lru_cache(maxsize=None)
def sample_merged():
    return join.positions_for_join(SAMPLE, merges=True)


@lru_cache(maxsize=None)
def sample_date_links_merged():
    return join.link_matches(sample_shots(), sample_merged(), sample_clubs())


@lru_cache(maxsize=None)
def sample_rosters():
    return join.build_rosters(sample_merged())


@lru_cache(maxsize=None)
def sample_rows_of():
    return join.shot_groups(sample_shots(), sample_date_links_merged().links, sample_merged())[0]


@lru_cache(maxsize=None)
def sample_joined():
    return join.join_by_name(sorted(sample_rows_of()), sample_rosters())


@lru_cache(maxsize=None)
def sample_name_map():
    return join.name_map_links(sorted(sample_rows_of()), sample_rosters(), sample_joined())


@lru_cache(maxsize=None)
def sample_anchors():
    linked = {**sample_joined(), **{group: ("map", fbref_id) for group, fbref_id in sample_name_map().links.items()}}
    return join.season_anchor_links(sample_name_map().undecided, linked, sample_name_map().conflicts)


def sample_groups_of(league, season, understat_id, match=None):
    found = [group for group in sample_rows_of() if (group.league, group.season, group.understat_id) == (league, season, understat_id) and (match is None or group.match == match)]
    assert found, (league, season, understat_id, match)
    return found


def hand_group(match="m1", understat_id=1, name="Kike", club="A", season=2021):
    return join.ShotGroup("ESP", season, match, understat_id, name, club)


def hand_roster(*players):
    """Hand-made roster, each player (fbref_id, name). Only synthetic tests use it."""
    return [join.RosterPlayer(fbref_id, name, join.compared_name(name)) for fbref_id, name in players]


class StageBNameSteps(unittest.TestCase):
    def assert_step_1_links(self, league, season, understat_id, match, fbref_name):
        group = sample_groups_of(league, season, understat_id, match)[0]
        step, fbref_id = sample_joined()[group]
        self.assertEqual(step, "step 1")
        self.assertEqual({player.player for player in sample_rosters()[(match, group.club)] if player.fbref_id == fbref_id}, {fbref_name})
        self.assertNotEqual(html.unescape(group.name), fbref_name)

    def assert_step_2_links(self, league, season, understat_id, match, fbref_name):
        group = sample_groups_of(league, season, understat_id, match)[0]
        self.assertNotIn(group, sample_joined())
        fbref_id = sample_name_map().links[group]
        self.assertEqual({player.player for player in sample_rosters()[(match, group.club)] if player.fbref_id == fbref_id}, {fbref_name})

    def test_b_same_name_resolves_by_club(self):
        for group in sample_groups_of("ESP", 2021, 2098):
            self.assertEqual(sample_joined()[group], ("exact", "a6154613"))
        for group in sample_groups_of("ESP", 2021, 8978):
            self.assertEqual(sample_name_map().links[group], "eeba07f8")
        self.assertEqual({group.name for group in sample_groups_of("ESP", 2021, 2098)} & {group.name for group in sample_groups_of("ESP", 2021, 8978)}, {"Luis Suárez"})

    def test_b_club_comes_from_h_a(self):
        shots = sample_shots()
        match_id = next(key[1] for key, match in sample_date_links_merged().links.items() if match == "017448ed")
        rows = shots[(shots["match_id"] == match_id) & (shots["player_id"] == 453)]
        self.assertTrue((rows["h_a"].fillna("") != "").all())
        fbref_match = sample_merged()[sample_merged()["match"] == "017448ed"].iloc[0]
        side_club = fbref_match["Home_Team"] if rows["h_a"].iloc[0] == "h" else fbref_match["Away_Team"]
        self.assertEqual(side_club, "Tottenham Hotspur")
        self.assertEqual(sample_groups_of("ENG", 2017, 453, "017448ed")[0].club, side_club)

    def test_b_club_comes_from_home_away_when_h_a_empty(self):
        shots = sample_shots()
        rows = shots[(shots["league"] == "ENG") & (shots["match_id"] == 22275)]
        koleosho = rows[rows["player"] == "Luca Koleosho"]
        self.assertTrue((koleosho["h_a"].fillna("") == "").all())
        self.assertTrue((koleosho["home_away"].fillna("") != "").all())
        match = sample_date_links_merged().links[("ENG", 22275)]
        fbref_match = sample_merged()[sample_merged()["match"] == match].iloc[0]
        side_club = fbref_match["Home_Team"] if koleosho["home_away"].iloc[0] == "h" else fbref_match["Away_Team"]
        self.assertEqual(sample_groups_of("ENG", 2023, int(koleosho["player_id"].iloc[0]), match)[0].club, side_club)

    def test_b_roster_does_not_decide_the_club(self):
        rosters = sample_rosters()
        for match in ("37414fba", "7d399b5f"):
            group = sample_groups_of("ESP", 2021, 8978, match)[0]
            self.assertEqual(group.club, "Granada")
            self.assertNotIn("Luis Suárez", {player.player for player in rosters[(match, "Granada")]})
            other_club = next(club for found_match, club in rosters if found_match == match and club != "Granada")
            self.assertIn("Luis Suárez", {player.player for player in rosters[(match, other_club)]})

    def test_b_synthetic_row_with_no_side_stops(self):
        # synthetic: 0 real, every shot row fills exactly one side (T7:437).
        rows = pd.DataFrame({"h_a": [pd.NA], "home_away": [""], "source_file": ["x_shot_data.parquet"], "source_row": [7]})
        with self.assertRaises(SystemExit) as stop:
            join.with_side(rows)
        self.assertIn("x_shot_data.parquet", str(stop.exception))
        self.assertIn("row 7", str(stop.exception))
        self.assertIn("no side", str(stop.exception))

    def test_b_synthetic_row_with_unknown_side_stops(self):
        # synthetic: 0 real, every shot row holds h or a (T7:437).
        rows = pd.DataFrame({"h_a": ["x"], "home_away": [""], "source_file": ["x_shot_data.parquet"], "source_row": [7]})
        with self.assertRaises(SystemExit) as stop:
            join.with_side(rows)
        self.assertIn("x_shot_data.parquet", str(stop.exception))
        self.assertIn("row 7", str(stop.exception))
        self.assertIn("unknown side 'x'", str(stop.exception))

    def test_b_exact_matches_after_html_unescape(self):
        group = sample_groups_of("ENG", 2020, 8756)[0]
        self.assertEqual(group.name, "Dara O&#039;Shea")
        self.assertEqual(sample_joined()[group][0], "exact")

    def test_b_synthetic_two_exact_roster_matches_do_not_link(self):
        # synthetic: 0 real (design check).
        group = hand_group()
        rosters = {("m1", "A"): hand_roster(("x", "Kike"), ("y", "Kike"))}
        self.assertEqual(join.join_by_name([group], rosters), {})
        # It goes on to step 2 as undecided, which is the plan's route to a season anchor.
        result = join.name_map_links([group], rosters, {})
        self.assertEqual(result.links, {})
        self.assertEqual(result.undecided, {group: {"x", "y"}})

    def test_b_synthetic_two_exact_matches_skip_step_1(self):
        # synthetic: 0 real (design check). The third player fits step 1 only, and must not be chosen.
        group = hand_group()
        self.assertEqual(join.join_by_name([group], {("m1", "A"): hand_roster(("x", "Kike"), ("y", "Kike"), ("z", "KIKE"))}), {})

    def test_b_step_1_ignores_case(self):
        self.assert_step_1_links("ENG", 2017, 453, "017448ed", "Son Heung-min")

    def test_b_step_1_ignores_accents(self):
        self.assert_step_1_links("ENG", 2017, 697, "06ec2f77", "Nemanja Matić")

    def test_b_step_1_ignores_punctuation(self):
        self.assert_step_1_links("ENG", 2017, 1729, "68df68a4", "Georges-Kévin N'Koudou")

    def test_b_step_1_folds_letters_nfkd_does_not_reduce(self):
        cases = (("ENG", 2020, 2517, "127b8258", "Martin Ødegaard"), ("ENG", 2017, 714, "01d63d4d", "Gylfi Sigurðsson"), ("ESP", 2022, 10971, "10b27265", "Srđan Babić"), ("ESP", 2019, 8051, "2424dced", "İsmail Köybaşı"), ("ENG", 2021, 10097, "11a67612", "Przemysław Płacheta"), ("ESP", 2017, 4699, "21098c4b", "Simon Kjær"), ("FRA", 2017, 3408, "9ba359c1", "Kolbeinn Sigþórsson"))
        for case in cases:
            self.assert_step_1_links(*case)

    def test_b_step_1_folds_sharp_s(self):
        self.assertEqual(sample_groups_of("ENG", 2017, 239, "0cbb18e2")[0].name, "Pascal Groß")
        # 0 real names need the fold to link, so a link alone could not fail: the compared name can.
        self.assertEqual(join.compared_name("Pascal Groß"), "pascal gross")

    def test_b_synthetic_step_1_folds_oe(self):
        # synthetic: 0 real, no name holds œ (design check).
        self.assertEqual(join.join_by_name([hand_group(name="Leboeuf")], {("m1", "A"): hand_roster(("x", "Lebœuf"))}), {hand_group(name="Leboeuf"): ("step 1", "x")})

    def test_b_step_1_counts_hyphen_as_space(self):
        self.assertEqual(join.compared_name("Son Heung-Min"), "son heung min")
        self.assert_step_1_links("ENG", 2017, 453, "017448ed", "Son Heung-min")

    def test_b_synthetic_two_step_1_roster_matches_do_not_link(self):
        # synthetic: 0 real (design check).
        self.assertEqual(join.join_by_name([hand_group(name="JOSE")], {("m1", "A"): hand_roster(("x", "José"), ("y", "Jose"))}), {})

    def test_b_synthetic_two_step_1_matches_go_to_step_2(self):
        # synthetic: 0 real (design check). "José Garcia" takes y exactly, so step 2 leaves one candidate for the name step 1 could not decide.
        undecided_name, taken_name = hand_group(name="JOSE GARCIA"), hand_group(understat_id=2, name="José Garcia")
        rosters = {("m1", "A"): hand_roster(("x", "Jose Garcia"), ("y", "José Garcia"))}
        joined = join.join_by_name([undecided_name, taken_name], rosters)
        self.assertEqual(joined, {taken_name: ("exact", "y")})
        self.assertEqual(join.name_map_links([undecided_name, taken_name], rosters, joined).links, {undecided_name: "x"})

    def test_b_step_2_stays_inside_match_and_club(self):
        # Danilo's name is on Bologna's opponents' roster, and he still links inside Bologna.
        group = sample_groups_of("ITA", 2019, 1140, "711e1d1f")[0]
        self.assertEqual((group.club, sample_name_map().links[group]), ("Bologna", "fed5f993"))
        opponents = next(club for match, club in sample_rosters() if match == "711e1d1f" and club != "Bologna")
        self.assertIn("danilo", {player.compared for player in sample_rosters()[("711e1d1f", opponents)]})

    def test_b_step_2_links_on_shared_last_name(self):
        self.assert_step_2_links("ENG", 2017, 368, "09d80d49", "Kostas Stafylidis")

    def test_b_step_2_links_shot_name_inside_roster_name(self):
        self.assert_step_2_links("ENG", 2017, 1245, "082489f8", "Emerson Palmieri")
        for group in sample_groups_of("ESP", 2019, 2302):
            self.assertEqual(sample_name_map().links[group], "09332647")

    def test_b_step_2_links_roster_name_inside_shot_name(self):
        self.assert_step_2_links("ENG", 2019, 7726, "010301bf", "Ezri Konsa")

    def test_b_step_2_requires_whole_words(self):
        # "Larra" sits inside "Gaizka Larrazabal" as letters, not as a word.
        group = sample_groups_of("ESP", 2019, 7780, "ba501a17")[0]
        self.assertIn("Larra", {player.player for player in sample_rosters()[("ba501a17", "Athletic Club")]})
        self.assertNotIn(group, sample_joined())
        self.assertNotIn(group, sample_name_map().links)
        self.assertNotIn(group, sample_name_map().undecided)

    def test_b_step_2_ignores_word_order(self):
        groups = sample_groups_of("ENG", 2021, 8845)
        self.assertEqual({group.name for group in groups}, {"Hee-Chan Hwang"})
        for group in groups:
            self.assertNotIn(group, sample_joined())
            self.assertEqual(sample_name_map().links[group], "169fd162")

    def test_b_step_2_roster_inside_shot_in_any_order(self):
        for key in (("ESP", 2019, 684), ("FRA", 2018, 684), ("GER", 2018, 684)):
            for group in sample_groups_of(*key):
                self.assertEqual(group.name, "Abdul Rahman Baba")
                self.assertEqual(sample_name_map().links[group], "e4086af3")
        self.assertEqual(sum(sample_rows_of()[group] for group in sample_rows_of() if group.understat_id == 684), 8)

    def test_b_synthetic_step_2_shot_inside_roster_in_any_order(self):
        # synthetic: 0 real (T7:148).
        group = hand_group(name="Fernandes Bruno")
        self.assertEqual(join.name_map_links([group], {("m1", "A"): hand_roster(("x", "Bruno Miguel Fernandes"))}, {}).links, {group: "x"})

    def test_b_step_2_skips_roster_player_already_matched(self):
        # Sergi Cardona's own shot matched him exactly, so he is no candidate for "Marc Cardona" in that match.
        group = sample_groups_of("ESP", 2023, 5159, "b5b5ee07")[0]
        self.assertIn("Sergi Cardona", {player.player for player in sample_rosters()[("b5b5ee07", "Las Palmas")]})
        self.assertNotIn(group, sample_joined())
        self.assertNotIn(group, sample_name_map().links)
        self.assertNotIn(group, sample_name_map().undecided)

    def test_b_step_2_no_candidate_does_not_link(self):
        group = sample_groups_of("ENG", 2017, 191, "0abc466b")[0]
        self.assertEqual(group.name, "Chicharito")
        self.assertNotIn(group, sample_joined())
        self.assertNotIn(group, sample_name_map().links)
        self.assertNotIn(group, sample_name_map().undecided)

    def test_b_step_2_two_candidates_do_not_link(self):
        for match in ("92f705d2", "add782a1"):
            group = sample_groups_of("ESP", 2020, 6216, match)[0]
            self.assertNotIn(group, sample_name_map().links)
            self.assertGreaterEqual(len(sample_name_map().undecided[group]), 2)

    def test_b_synthetic_two_shot_names_on_one_player_block_each_other(self):
        # synthetic: 0 real (design check, step 2 stopped).
        first, second = hand_group(name="Garcia"), hand_group(understat_id=2, name="Jose Garcia")
        result = join.name_map_links([first, second], {("m1", "A"): hand_roster(("x", "Kike Garcia"))}, {})
        self.assertEqual(result.links, {})
        self.assertEqual(result.stopped["two shot names on one roster player"], 2)

    def test_b_two_candidate_name_does_not_block(self):
        # "Chema Rodríguez" has 2+ candidates, one of them Ángel Rodríguez, and must not block "Ángel".
        for match in ("92f705d2", "add782a1"):
            chema = sample_groups_of("ESP", 2020, 6216, match)[0]
            self.assertIn("8cfc2f69", sample_name_map().undecided[chema])
            self.assertEqual(sample_name_map().links[sample_groups_of("ESP", 2020, 4136, match)[0]], "8cfc2f69")

    def test_b_step_2_link_is_flagged_map(self):
        linked = join.links_after_step_2(sample_joined(), sample_name_map())
        group = sample_groups_of("ENG", 2017, 1245, "082489f8")[0]
        self.assertEqual(linked[group], ("map", sample_name_map().links[group]))
        self.assertEqual(linked[sample_groups_of("ENG", 2017, 453, "017448ed")[0]][0], "step 1")

    def test_b_synthetic_two_fbref_ids_stop_step_2_links(self):
        # synthetic: 0 real (design check).
        spellings = [hand_group("m1", name="Sehrou Kike"), hand_group("m2", name="Serhou Kike")]
        rosters = {("m1", "A"): hand_roster(("x", "S Kike")), ("m2", "A"): hand_roster(("y", "S Kike"))}
        result = join.name_map_links(spellings, rosters, {})
        self.assertEqual(result.links, {})
        self.assertEqual(result.conflicts, [("ESP", 2021, 1)])
        self.assertEqual(result.stopped["player-seasons reaching 2+ FBref ids"], 1)

    def test_b_synthetic_stop_keeps_exact_and_step_1_links(self):
        # synthetic: 0 real (design check).
        mapped, exact = hand_group("m1", name="Sehrou Kike"), hand_group("m2", name="Serhou Kike")
        rosters = {("m1", "A"): hand_roster(("x", "S Kike")), ("m2", "A"): hand_roster(("y", "Serhou Kike"))}
        joined = join.join_by_name([mapped, exact], rosters)
        self.assertEqual(joined, {exact: ("exact", "y")})
        result = join.name_map_links([mapped, exact], rosters, joined)
        self.assertEqual(result.links, {})
        self.assertEqual(join.links_after_step_2(joined, result), {exact: ("exact", "y")})

    def test_b_synthetic_merged_ids_do_not_trigger_the_stop(self):
        # synthetic: 0 real (design check). Before the merge the shot names reach x and y. After it they reach one id.
        positions = fbref_rows(("m1", "2021-01-10", "A", "B", "A", "S Kike", "x", 90), ("m2", "2021-01-17", "A", "C", "A", "S Kike", "y", 90))
        spellings = [hand_group("m1", name="Sehrou Kike"), hand_group("m2", name="Serhou Kike")]
        self.assertEqual(len(join.name_map_links(spellings, join.build_rosters(positions), {}).conflicts), 1)
        merged = join.merge_fbref_ids(positions)[0]
        result = join.name_map_links(spellings, join.build_rosters(merged), {})
        self.assertEqual(result.conflicts, [])
        self.assertEqual(len(result.links), 2)

    def test_b_two_spellings_on_one_id_do_not_stop(self):
        groups = sample_groups_of("GER", 2023, 3738)
        self.assertEqual({group.name for group in groups}, {"Sehrou Guirassy", "Serhou Guirassy"})
        self.assertEqual(sample_name_map().conflicts, [])
        self.assertEqual(len({join.links_after_step_2(sample_joined(), sample_name_map())[group][1] for group in groups}), 1)

    def test_b_synthetic_stopped_link_is_listed_with_its_key(self):
        # synthetic: 0 real (design check).
        first, second = hand_group("m1", name="Sehrou Kike"), hand_group("m2", name="Serhou Kike")
        result = join.name_map_links([first, second], {("m1", "A"): hand_roster(("x", "S Kike")), ("m2", "A"): hand_roster(("y", "S Kike"))}, {})
        self.assertEqual(result.stopped_links, {first: "x", second: "y"})
        self.assertEqual(sorted(join.link_keys(result.stopped_links)), ["ESP|2021|1|Sehrou Kike|x", "ESP|2021|1|Serhou Kike|y"])

    def test_b_synthetic_two_ids_with_different_names_keep_both_links(self):
        # synthetic: 0 real (design check).
        first, second = hand_group("m1", name="Kike Garcia"), hand_group("m2", name="Enrique Lopez")
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("y", "Enrique Lopez"))}
        joined = join.join_by_name([first, second], rosters)
        result = join.name_map_links([first, second], rosters, joined)
        self.assertEqual(joined, {first: ("exact", "x"), second: ("exact", "y")})
        self.assertEqual(result.conflicts, [])
        self.assertEqual(result.two_ids, [join.TwoIds(("ESP", 2021, 1), ("x", "y"), True)])

    def test_b_anchor_links_id_seen_in_two_other_matches(self):
        group = sample_groups_of("ENG", 2020, 5613, "9f6c52f8")[0]
        self.assertIn(group, sample_name_map().undecided)
        self.assertEqual(sample_anchors().links[group], "67ac5bb8")

    def test_b_anchor_never_runs_on_a_zero_candidate_group(self):
        # Marc Cardona has 20 other links on one id, so only the missing candidates keep this group from anchoring.
        group = sample_groups_of("ESP", 2023, 5159, "b5b5ee07")[0]
        self.assertGreaterEqual(len({found.match for found in sample_groups_of("ESP", 2023, 5159) if found in sample_joined()}), 2)
        self.assertNotIn(group, sample_name_map().undecided)
        self.assertNotIn(group, sample_anchors().links)

    def test_b_anchor_needs_two_other_matches(self):
        group = sample_groups_of("ESP", 2019, 6216, "8a009fd3")[0]
        self.assertIn(group, sample_name_map().undecided)
        self.assertNotIn(group, sample_anchors().links)
        linked = join.links_after_step_2(sample_joined(), sample_name_map())
        other_matches = {found.match: linked[found][1] for found in sample_groups_of("ESP", 2019, 6216) if found.match != group.match and found in linked}
        self.assertEqual(len(other_matches), 1)
        # The id is a candidate, so only the count of other matches keeps this group from anchoring.
        self.assertIn(next(iter(other_matches.values())), sample_name_map().undecided[group])
        self.assertEqual(join.season_anchor_links({group: sample_name_map().undecided[group]}, linked).stopped["under 2 other matches"], 1)

    def test_b_anchor_needs_links_for_that_club(self):
        group = sample_groups_of("ENG", 2021, 10092, "c8c7dd9b")[0]
        self.assertIn(group, sample_name_map().undecided)
        self.assertNotIn(group, sample_anchors().links)
        self.assertFalse([found for found in sample_groups_of("ENG", 2021, 10092) if found.club == group.club and (found in sample_joined() or found in sample_name_map().links)])
        # The real player has no links at all, so add two at another club, in memory: they must not anchor this group.
        candidate = next(iter(sample_name_map().undecided[group]))
        elsewhere = {group._replace(match=match, club="Another club"): ("exact", candidate) for match in ("m1", "m2")}
        result = join.season_anchor_links({group: sample_name_map().undecided[group]}, elsewhere)
        self.assertEqual(result.links, {})
        self.assertEqual(result.stopped["no links for that club"], 1)

    def anchored_on_x(self, undecided, extra=None):
        two_other = {hand_group("m1"): ("map", "x"), hand_group("m2"): ("map", "x")}
        return join.season_anchor_links(undecided, {**two_other, **(extra or {})})

    def test_b_synthetic_anchor_id_must_be_a_candidate(self):
        # synthetic: 0 real (design check).
        result = self.anchored_on_x({hand_group("m3"): {"y", "z"}})
        self.assertEqual(result.links, {})
        self.assertEqual(result.stopped["id not a candidate"], 1)

    def test_b_synthetic_anchor_needs_one_fbref_id(self):
        # synthetic: 0 real (design check).
        result = self.anchored_on_x({hand_group("m3"): {"x", "y"}}, {hand_group("m4"): ("map", "z")})
        self.assertEqual(result.links, {})
        self.assertEqual(result.stopped["links to 2+ FBref ids"], 1)

    def test_b_synthetic_anchor_id_already_linked_in_match(self):
        # synthetic: 0 real (design check).
        result = self.anchored_on_x({hand_group("m3"): {"x", "y"}}, {hand_group("m3", 2, "Other"): ("exact", "x")})
        self.assertEqual(result.links, {})
        self.assertEqual(result.stopped["id already linked in that match"], 1)

    def test_b_synthetic_anchor_two_names_on_one_player(self):
        # synthetic: 0 real (design check).
        result = self.anchored_on_x({hand_group("m3", name="Kike"): {"x", "y"}, hand_group("m3", name="Enrique"): {"x", "y"}})
        self.assertEqual(result.links, {})
        self.assertEqual(result.stopped["two shot names on one roster player"], 2)

    def test_b_synthetic_anchor_link_does_not_anchor(self):
        # synthetic: 0 real (the rule runs one pass). Two anchor links alone must not anchor a third.
        linked = {hand_group("m1"): ("season_anchor", "x"), hand_group("m2"): ("season_anchor", "x")}
        self.assertEqual(join.season_anchor_links({hand_group("m3"): {"x", "y"}}, linked).links, {})

    def test_b_synthetic_stopped_player_season_gains_no_anchor(self):
        # synthetic: 0 real (design check).
        two_other = {hand_group("m1"): ("exact", "x"), hand_group("m2"): ("exact", "x")}
        self.assertEqual(join.season_anchor_links({hand_group("m3"): {"x", "y"}}, two_other, [("ESP", 2021, 1)]).links, {})

    def test_b_synthetic_barred_link_is_listed_with_its_key(self):
        # synthetic: 0 real (design check).
        two_other = {hand_group("m1"): ("exact", "x"), hand_group("m2"): ("exact", "x")}
        barred = join.season_anchor_links({hand_group("m3"): {"x", "y"}}, two_other, [("ESP", 2021, 1)]).barred
        self.assertEqual(barred, {hand_group("m3"): "x"})
        self.assertEqual(join.link_keys(barred), ["ESP|2021|1|Kike|x"])


HAND_SEASON_ROWS = {("ESP", 2021, "Kike"): [join.SeasonRow({"A"}, 900)]}


def hand_facts(fbref_minutes, season_rows=None, shot_names=None, fbref_names=None, fbref_clubs=None):
    """Hand-made guard facts. Only synthetic tests use it."""
    return join.GuardFacts(
        season_rows if season_rows is not None else HAND_SEASON_ROWS, {("ESP", 2022, fbref_id): minutes for fbref_id, minutes in fbref_minutes.items()},
        fbref_names or {}, fbref_clubs or {}, shot_names or {("ESP", 2021, 1): {"Kike"}},
    )


@lru_cache(maxsize=None)
def sample_rule3():
    facts = join.guard_facts(sample_merged(), sample_shots(), join.season_rows_by_name(sample_clubs(), SAMPLE))
    return join.rule3_links(sample_rows_of(), sample_rosters(), facts)


@lru_cache(maxsize=None)
def sample_facts():
    return join.guard_facts(sample_merged(), sample_shots(), join.season_rows_by_name(sample_clubs(), SAMPLE))


@lru_cache(maxsize=None)
def sample_candidates():
    return join.pool_candidates(sample_merged(), SAMPLE)


@lru_cache(maxsize=None)
def sample_partial():
    return join.partial_joins(sample_rows_of(), sample_rule3().final)


@lru_cache(maxsize=None)
def sample_flags():
    return join.review_flags(sample_candidates(), sample_rule3().final, sample_partial(), sample_rule3().name_map.two_ids)


def lookup(league, season, shot_names, fbref_id):
    facts = sample_facts()
    return join.season_totals_row(facts, league, season, shot_names, fbref_id)


ANDERSON = join.PlayerSeasonName("ITA", 2019, 7941, "André Anderson", "ca241ad3")
EZZALZOULI = join.PlayerSeasonName("ESP", 2023, 10095, "Abdessamad Ezzalzouli", "bed68338")
GABRIEL = join.PlayerSeasonName("ENG", 2020, 5613, "Gabriel", "67ac5bb8")
MALINOVSKYI = ("FRA", 2023, "48d5bd33")
JOHNSEN = ("ITA", 2022, "66784dee")
JEFFINHO = ("FRA", 2023, "45cce300")


class StageCGuardAndFlags(unittest.TestCase):
    def test_c_guard_runs_once_per_name_map_player_season(self):
        rule3 = sample_rule3()
        pairs = {join.PlayerSeasonName(*group.player_season_name, fbref_id) for group, fbref_id in rule3.name_map.links.items()}
        self.assertGreater(len(rule3.name_map.links), len(pairs))
        # Once per pair: the lookup is called once per verdict, not once per shot group.
        with mock.patch.object(join, "season_totals_row", wraps=join.season_totals_row) as totals_row:
            again = join.rule3_links(sample_rows_of(), sample_rosters(), sample_facts())
        self.assertEqual(totals_row.call_count, len(again.guard) + len(again.anchor_guard))
        self.assertEqual(set(again.guard), pairs)
        # After the merges: Strefezza's minutes are his two ids' together, 410 and 703.
        pair = join.PlayerSeasonName("ITA", 2023, 1, "Gabriel Strefezza", "ac4a4508")
        self.assertEqual(join.minutes_guard([pair], sample_facts())[pair][2], 1113)

    def test_c_limit_is_90_minutes_at_low_totals(self):
        self.assertEqual(join.minutes_limit(49, 167), 90)
        self.assertEqual(sample_rule3().guard[ANDERSON], ("disagree", 49, 167))

    def test_c_limit_is_10_percent_of_larger_total(self):
        self.assertAlmostEqual(join.minutes_limit(839, 933), 93.3)
        # A gap of 94 against 93.3.
        self.assertEqual(sample_rule3().guard[EZZALZOULI], ("disagree", 839, 933))

    def test_c_synthetic_gap_at_the_limit_keeps_the_link(self):
        # synthetic: 0 real gaps exactly at the limit (design check).
        pair = join.PlayerSeasonName("ESP", 2021, 1, "Kike", "x")
        self.assertEqual(join.minutes_guard([pair], hand_facts({"x": 1000}))[pair], ("agree", 900, 1000))
        self.assertEqual(join.minutes_guard([pair], hand_facts({"x": 1001}))[pair], ("disagree", 900, 1001))

    def test_c_link_beyond_the_limit_is_removed_and_listed(self):
        rule3 = sample_rule3()
        group = sample_groups_of("ITA", 2019, 7941, "588b69d5")[0]
        self.assertEqual(rule3.name_map.links[group], "ca241ad3")
        self.assertNotIn(group, rule3.after_guard)
        self.assertEqual(rule3.guard[ANDERSON][0], "disagree")
        self.assertIn(ANDERSON, join.guard_review_list(rule3)["disagree"])

    def test_c_lookup_uses_shot_name(self):
        row = lookup("ENG", 2021, {"Hee-Chan Hwang"}, "169fd162")
        self.assertEqual(row.minutes, 1804)

    def test_c_lookup_uses_any_spelling_of_the_player_season(self):
        fbref_id = sample_rule3().final[sample_groups_of("GER", 2023, 3738)[0]][1]
        self.assertEqual(sample_facts().shot_names[("GER", 2023, 3738)], {"Sehrou Guirassy", "Serhou Guirassy"})
        self.assertEqual(lookup("GER", 2023, sample_facts().shot_names[("GER", 2023, 3738)], fbref_id).minutes, 2228)
        pair = join.PlayerSeasonName("GER", 2023, 3738, "Sehrou Guirassy", fbref_id)
        self.assertEqual(sample_rule3().guard[pair][0], "agree")
        # Without the FBref name the row is under the other shot spelling only, so only "every spelling" can reach it.
        without_fbref_name = sample_facts()._replace(fbref_names={})
        self.assertEqual(join.minutes_guard([pair], without_fbref_name)[pair][1], 2228)

    def test_c_lookup_falls_back_to_fbref_name(self):
        # FRA 2018/19's shot rows say Sehrou, and the season row and FBref say Serhou.
        self.assertEqual(sample_facts().shot_names[("FRA", 2018, 3738)], {"Sehrou Guirassy"})
        self.assertFalse(sample_facts().season_rows.get(("FRA", 2018, "Sehrou Guirassy")))
        self.assertIsNotNone(lookup("FRA", 2018, {"Sehrou Guirassy"}, "923f4dda"))
        self.assertEqual(sample_rule3().guard[join.PlayerSeasonName("FRA", 2018, 3738, "Sehrou Guirassy", "923f4dda")][0], "agree")

    def test_c_lookup_uses_club_when_two_rows_share_a_name(self):
        self.assertEqual(len(sample_facts().season_rows[("ENG", 2022, "Emerson")]), 2)
        self.assertEqual(lookup("ENG", 2022, {"Emerson"}, "e0bc6fdc").minutes, 1331)

    def test_c_synthetic_no_season_row_keeps_link_flagged_none(self):
        # synthetic: 0 real once the guard uses Q5 (design check).
        group = hand_group(name="Kike Lopez")
        rosters = {("m1", "A"): hand_roster(("x", "Enrique Lopez"))}
        facts = hand_facts({"x": 900}, season_rows={}, shot_names={("ESP", 2021, 1): {"Kike Lopez"}}, fbref_names={("ESP", 2022, "x"): ["Enrique Lopez"]})
        rule3 = join.rule3_links({group: 1}, rosters, facts)
        pair = join.PlayerSeasonName("ESP", 2021, 1, "Kike Lopez", "x")
        self.assertEqual(rule3.guard[pair], ("none", None, 900))
        self.assertEqual(rule3.final, {group: ("map", "x")})
        self.assertEqual(join.guard_review_list(rule3)["none"], [pair])
        # No single row also means 2+ rows at the linked club, or 2+ rows none of them at that club.
        two_rows = [join.SeasonRow({"A"}, 900), join.SeasonRow({"A"}, 800)]
        for clubs in ({"A"}, {"B"}):
            facts = hand_facts({"x": 900}, season_rows={("ESP", 2021, "Kike Lopez"): two_rows}, shot_names={("ESP", 2021, 1): {"Kike Lopez"}}, fbref_clubs={("ESP", 2022, "x"): clubs})
            self.assertEqual(join.minutes_guard([pair], facts)[pair][0], "none")

    def test_c_anchor_link_passes_the_guard(self):
        rule3 = sample_rule3()
        group = sample_groups_of("ENG", 2020, 5613, "9f6c52f8")[0]
        self.assertEqual(rule3.anchor_guard[GABRIEL][0], "agree")
        self.assertEqual(rule3.final[group], ("season_anchor", "67ac5bb8"))

    def anchored_on_exact_links(self, season_minutes):
        """Two exact links on x, then a match where step 2 finds x and y."""
        groups = {hand_group("m1"): 1, hand_group("m2"): 1, hand_group("m3"): 1}
        rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike")), ("m3", "A"): hand_roster(("x", "Kike Garcia"), ("y", "Kike Lopez"))}
        return groups, rosters, hand_facts({"x": 900}, season_rows={("ESP", 2021, "Kike"): [join.SeasonRow({"A"}, season_minutes)]})

    def test_c_synthetic_guard_removes_anchor_link(self):
        # synthetic: 0 real (design check).
        groups, rosters, facts = self.anchored_on_exact_links(100)
        rule3 = join.rule3_links(groups, rosters, facts)
        self.assertEqual(rule3.anchors.links, {hand_group("m3"): "x"})
        self.assertEqual(rule3.anchor_guard[join.PlayerSeasonName("ESP", 2021, 1, "Kike", "x")][0], "disagree")
        self.assertNotIn(hand_group("m3"), rule3.final)

    def test_c_synthetic_guard_removed_link_does_not_anchor(self):
        # synthetic: 0 real (design check). Step 2 links m1 and m2 to x, the guard removes them, so m3 has nothing to anchor on.
        groups = {hand_group("m1"): 1, hand_group("m2"): 1, hand_group("m3"): 1}
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("x", "Kike Garcia")), ("m3", "A"): hand_roster(("x", "Kike Garcia"), ("y", "Kike Lopez"))}
        facts = hand_facts({"x": 900}, season_rows={("ESP", 2021, "Kike"): [join.SeasonRow({"A"}, 100)]})
        rule3 = join.rule3_links(groups, rosters, facts)
        self.assertEqual(set(rule3.name_map.links), {hand_group("m1"), hand_group("m2")})
        self.assertEqual(rule3.guard[join.PlayerSeasonName("ESP", 2021, 1, "Kike", "x")][0], "disagree")
        self.assertEqual(rule3.anchors.links, {})
        self.assertEqual(rule3.final, {})

    def test_c_every_anchor_link_is_listed(self):
        rule3 = sample_rule3()
        listing = join.anchor_listing(rule3)
        self.assertIn(GABRIEL, [entry[0] for entry in listing])
        self.assertEqual(sum(entry[2] for entry in listing), sum(sample_rows_of()[group] for group in rule3.anchors.links))
        self.assertEqual(sum(entry[3] for entry in listing), len(rule3.anchors.links))

    def test_c_name_map_holds_one_row_per_kept_player_season(self):
        rule3 = sample_rule3()
        rows = join.name_map_file_rows(rule3, {"ca241ad3": "Djavan Anderson"}.get)
        keys = [(row[0], row[1], row[2], row[3], row[4]) for row in rows]
        kept_groups = {group: link for group, link in rule3.final.items() if link[0] == "map"}
        self.assertEqual(sum(row[6] for row in rows), sum(sample_rows_of()[group] for group in kept_groups))
        self.assertEqual(sum(row[7] for row in rows), len(kept_groups))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn(("ITA", 2019, 7941, "André Anderson", "ca241ad3"), keys)
        # Many shot groups, one review row: Guirassy's "Sehrou" is step 2 in many matches, and "Serhou" is exact, so not a map row.
        self.assertEqual([key for key in keys if key[:3] == ("GER", 2023, 3738)], [("GER", 2023, 3738, "Sehrou Guirassy", sample_rule3().final[sample_groups_of("GER", 2023, 3738)[0]][1])])

    def test_c_synthetic_redrawn_sample_pairs_fail_against_the_committed_file(self):
        # synthetic: 0 real redraws (design check).
        committed = "league,understat_season,understat_id,shot_name,fbref_id\nESP,2021,1,Kike,x\n"
        join.check_sample_pairs({("ESP", 2021, 1, "x")}, committed)
        with self.assertRaises(SystemExit) as stop:
            join.check_sample_pairs({("ESP", 2021, 2, "y")}, committed)
        self.assertIn("name_map_sample.csv", str(stop.exception))
        # The script reads the committed file, not the working copy, and a new draw stops it before it writes anything.
        with mock.patch.object(script.subprocess, "run", return_value=mock.Mock(stdout=committed)) as git:
            self.assertEqual(script.committed_sample_text(), committed)
        self.assertEqual(git.call_args.args[0], ["git", "show", "HEAD:docs/reports/name_map_sample.csv"])
        fifty = [["ESP", 2021, number, "Kike", "z"] for number in range(50)]
        with TemporaryDirectory() as folder, mock.patch.object(script, "name_map_file_rows", return_value=fifty), mock.patch.object(script, "committed_sample_text", return_value=committed), mock.patch.object(script, "NAME_MAP_FILE", Path(folder) / "name_map.csv"), mock.patch.object(script, "SAMPLE_FILE", Path(folder) / "sample.csv"):
            with self.assertRaises(SystemExit):
                script.write_outputs(None, {})
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_c_synthetic_id_collision_leaves_both_unjoined(self):
        # synthetic: 0 real after the guard (design check).
        first, second = hand_group(), hand_group(understat_id=2)
        rule3 = join.rule3_links({first: 1, second: 1}, {("m1", "A"): hand_roster(("x", "Kike"))}, hand_facts({"x": 900}))
        self.assertEqual(rule3.collisions, {("ESP", 2021, "x"): [1, 2]})
        self.assertEqual(rule3.final, {})

    def test_c_guard_removes_false_link_before_collision_check(self):
        rule3 = sample_rule3()
        anderson, djavan = sample_groups_of("ITA", 2019, 7941, "588b69d5")[0], sample_groups_of("ITA", 2019, 8259)[0]
        self.assertEqual(rule3.name_map.links[anderson], "ca241ad3")
        self.assertEqual(sample_joined()[djavan][1], "ca241ad3")
        self.assertEqual(rule3.collisions, {})
        self.assertEqual(rule3.final[djavan][1], "ca241ad3")
        self.assertNotIn(anderson, rule3.final)

    def test_c_partial_join_below_95_percent(self):
        self.assertEqual(sample_partial()[("ITA", 2021, 9882)], (14, 15))

    def test_c_no_partial_join_above_95_percent(self):
        self.assertEqual(join.join_counts(sample_rows_of(), sample_rule3().final)[("ESP", 2023, 5159)], (21, 22))
        self.assertNotIn(("ESP", 2023, 5159), sample_partial())

    def test_c_synthetic_exactly_95_percent_is_not_flagged(self):
        # synthetic: 0 real (design check).
        joined, unjoined = hand_group("m1"), hand_group("m2")
        self.assertEqual(join.partial_joins({joined: 19, unjoined: 1}, {joined: ("exact", "x")}), {})
        self.assertEqual(join.partial_joins({joined: 18, unjoined: 2}, {joined: ("exact", "x")}), {("ESP", 2021, 1): (18, 20)})

    def test_c_no_joined_rows_is_partial_join(self):
        found, total = sample_partial()[("FRA", 2022, 7947)]
        self.assertEqual((found, total), (0, 34))

    def test_c_candidate_with_no_joined_shots_is_flagged(self):
        self.assertIn(MALINOVSKYI, sample_candidates())
        self.assertIn("no joined shots", sample_flags()[MALINOVSKYI])

    def test_c_flagged_candidates_stay_out(self):
        for candidate in (MALINOVSKYI, JOHNSEN):
            self.assertIn(candidate, sample_candidates())
            self.assertIn(candidate, sample_flags())
            self.assertNotIn(candidate, join.pool_of(sample_candidates(), sample_flags()))
        self.assertIn("partial_join", sample_flags()[JOHNSEN])

    def test_c_partial_join_outside_the_candidates_is_held(self):
        self.assertEqual(sample_partial()[("FRA", 2022, 11399)], (1, 10))
        self.assertNotIn(JEFFINHO, sample_candidates())
        self.assertEqual(sample_flags()[JEFFINHO], {"partial_join"})
        # A player-season with no rows joined has no FBref id, so no PlayerSeason to hold. It stays listed in `partial`.
        self.assertIn(("FRA", 2022, 7947), sample_partial())

    def test_c_synthetic_two_id_candidate_is_held(self):
        # synthetic: 0 real (design check).
        first, second = hand_group("m1"), hand_group("m2")
        two_ids = [join.TwoIds(("ESP", 2021, 1), ("x", "y"), True)]
        flags = join.review_flags([("ESP", 2022, "x")], {first: ("exact", "x"), second: ("exact", "y")}, {}, two_ids)
        self.assertEqual(flags, {("ESP", 2022, "x"): {"two ids"}})
        self.assertEqual(join.pool_of([("ESP", 2022, "x")], flags), [])
        self.assertEqual(join.review_flags([("ESP", 2022, "x")], {first: ("exact", "x"), second: ("exact", "y")}, {}, [join.TwoIds(("ESP", 2021, 1), ("x", "y"), False)]), {})


def decision(item_type, key, verdict, fbref_id=""):
    """One hand-made review row. Only synthetic tests use it, apart from row 1's real key."""
    return {"item_type": item_type, "key": key, "decision": verdict, "fbref_id": fbref_id, "reviewer": "x", "date": "2026-01-01", "reason": "x"}


def decisions_file(folder, text):
    path = Path(folder) / "review_decisions.csv"
    path.write_text(text, encoding="utf8")
    return path


HEADER = "item_type,key,decision,fbref_id,reviewer,date,reason\n"


def positions_of(rosters, minutes=90):
    """Hand-made FBref rows from hand-made rosters."""
    rows = [(match, "2022-01-10", "A", "B", club, player.player, player.fbref_id, minutes) for (match, club), roster in rosters.items() for player in roster]
    return fbref_rows(*rows).assign(Season_End_Year=2022)


def at_900_minutes(positions):
    totals = positions.groupby(["league", "Season_End_Year", "fbref_id"])["Min"].sum()
    return sorted(totals[totals >= 900].index)


def hand_run(rows_of, rosters, decisions=(), candidates=(), refused=(), positions=None, facts=None, merges_on=True):
    """The whole of stage D on hand-made rows. Only synthetic tests use it."""
    facts = facts or hand_facts(dict.fromkeys("xyzc", 900))
    rule3 = join.rule3_links(rows_of, rosters, facts)
    candidates_of = candidates if callable(candidates) else lambda _: sorted(candidates)
    return join.finish_join(rule3, rows_of, rosters, positions_of(rosters) if positions is None else positions, list(decisions), list(refused), candidates_of, facts, merges_on)


@lru_cache(maxsize=None)
def sample_decisions():
    return join.read_review_decisions(SAMPLE.path("review_decisions.csv"))


def sample_finish(decisions=None, positions=None, refused=(), merges_on=True):
    positions = sample_merged() if positions is None else positions
    rows_of = join.shot_groups(sample_shots(), join.link_matches(sample_shots(), positions, sample_clubs()).links, positions)[0]
    facts = join.guard_facts(positions, sample_shots(), join.season_rows_by_name(sample_clubs(), SAMPLE))
    rule3 = join.rule3_links(rows_of, join.build_rosters(positions), facts)
    return join.finish_join(rule3, rows_of, join.build_rosters(positions), positions, sample_decisions() if decisions is None else decisions, list(refused), lambda found: join.pool_candidates(found, SAMPLE), facts, merges_on)


@lru_cache(maxsize=None)
def sample_finished():
    return sample_finish()


JOHNSEN_KEYS = ("ITA|2021|66784dee", "ITA|2021|9882")
EZZALZOULI_KEY = "ESP|2023|10095|Abdessamad Ezzalzouli|bed68338"
CARDONA_GROUP = ("ESP", 2023, 5159, "b5b5ee07")


def stopped_case():
    """Two spellings that step 2 links to two FBref ids, so both links stop."""
    first, second = hand_group("m1", name="Sehrou Kike"), hand_group("m2", name="Serhou Kike")
    rosters = {("m1", "A"): hand_roster(("x", "S Kike"), ("z", "Enrique")), ("m2", "A"): hand_roster(("y", "S Kike"), ("z", "Enrique"))}
    return first, second, {first: 1, second: 1}, rosters, "ESP|2021|1|Sehrou Kike|x", "ESP|2021|1|Serhou Kike|y"


def barred_case():
    """Exact links to x, a step 2 link to y that stops, and a group that would anchor on x."""
    groups = {hand_group("m1"): 1, hand_group("m2"): 1, hand_group("m3"): 1, hand_group("m4", name="Kik"): 1}
    rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike")), ("m3", "A"): hand_roster(("x", "Kike Garcia"), ("w", "Kike Lopez")), ("m4", "A"): hand_roster(("y", "Kik Ramos"))}
    return groups, rosters, "ESP|2021|1|Kik|y", "ESP|2021|1|Kike|x"


def unjoined_case():
    """One exact link on x in m1, and an unjoined row in m2, where only z is on the roster."""
    joined, unjoined = hand_group("m1"), hand_group("m2")
    return joined, unjoined, {joined: 1, unjoined: 1}, {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("z", "Enrique"))}


def collision_case():
    """Two Understat ids reaching x exactly, in different matches."""
    first, second = hand_group("m1"), hand_group("m2", understat_id=2)
    return first, second, {first: 1, second: 1}, {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike"))}


def no_shots_case():
    """Candidate c has no joined shots. x holds one exact link, in another match."""
    group = hand_group("m1")
    return group, {group: 1}, {("m1", "A"): hand_roster(("x", "Kike")), ("m3", "A"): hand_roster(("c", "Carlos"))}


REFUSED = join.RefusedMerge("ESP", 2022, "Kike", ("x", "y"), "both ids in other seasons")


def refused_case():
    """Two ids of one player, refused. x holds an exact link. y plays only in m3."""
    group = hand_group("m1")
    return group, {group: 1}, {("m1", "A"): hand_roster(("x", "Kike")), ("m3", "A"): hand_roster(("y", "Kike"))}


class StageDReviewDecisions(unittest.TestCase):
    def assert_stops(self, *needles, **run):
        with self.assertRaises(SystemExit) as stop:
            hand_run(**run)
        for needle in needles:
            self.assertIn(needle, str(stop.exception))

    def assert_file_stops(self, text, *needles):
        with TemporaryDirectory() as folder, self.assertRaises(SystemExit) as stop:
            join.read_review_decisions(decisions_file(folder, HEADER + text))
        for needle in needles:
            self.assertIn(needle, str(stop.exception))

    def test_d_reader_reads_the_real_row(self):
        self.assertEqual(len(sample_decisions()), 1)
        row = sample_decisions()[0]
        self.assertEqual((row["item_type"], row["key"], row["decision"], row["fbref_id"], row["reviewer"]), ("name_map", EZZALZOULI_KEY, "approve", "", "Ahmed"))

    def test_d_synthetic_reader_accepts_byte_order_mark(self):
        # synthetic: 0 real, the file has none.
        with TemporaryDirectory() as folder:
            path = Path(folder) / "review_decisions.csv"
            path.write_text(HEADER + "name_map,k,approve,,x,y,z\n", encoding="utf-8-sig")
            self.assertEqual(join.read_review_decisions(path)[0]["item_type"], "name_map")

    def test_d_name_map_key_form(self):
        self.assertEqual(join.decision_key(EZZALZOULI), EZZALZOULI_KEY)
        self.assertEqual(join.decision_key(join.PlayerSeasonName("ESP", 2023, 10095, "N&#039;Golo", "bed68338")), "ESP|2023|10095|N'Golo|bed68338")

    def test_d_synthetic_season_anchor_key_form(self):
        # synthetic: 0 real rows.
        groups, rosters, _, anchor_key = barred_case()
        result = hand_run(groups, rosters, [decision("season_anchor", anchor_key, "approve")])
        self.assertEqual(result.rule3.final[hand_group("m3")], ("season_anchor", "x"))

    def test_d_synthetic_partial_join_key_form(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = unjoined_case()
        self.assertEqual(join.partial_join_key(("ESP", 2021, 1)), "ESP|2021|1")
        self.assertEqual(hand_run(rows_of, rosters, [decision("partial_join", "ESP|2021|1", "reject")]).rule3.final[hand_group("m1")], ("exact", "x"))

    def test_d_synthetic_player_season_key_form(self):
        # synthetic: 0 real rows. The FBref year is 2022, so the key's season is 2021.
        self.assertEqual(join.player_season_key(("ESP", 2022, "c")), "ESP|2021|c")
        _, rows_of, rosters = no_shots_case()
        self.assertEqual(hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|c", "reject")], [("ESP", 2022, "c")]).pool, [])
        self.assert_stops("stale", rows_of=rows_of, rosters=rosters, decisions=[decision("player_season", "ESP|2022|c", "reject")], candidates=[("ESP", 2022, "c")])

    def test_d_synthetic_measure_rule3_accepts_a_player_season_row(self):
        # synthetic: 0 real rows (`data/standin/review_decisions.csv`).
        with TemporaryDirectory() as folder:
            self.assertEqual(script.read_review_decisions(decisions_file(folder, HEADER + "player_season,ESP|2021|c,reject,,x,y,z\n"))[0]["item_type"], "player_season")
            with self.assertRaises(SystemExit):
                script.read_review_decisions(decisions_file(folder, HEADER + "pool_" + "candidate,ESP|2021|c,reject,,x,y,z\n"))

    def test_d_synthetic_measure_rule3_accepts_a_cross_season_row(self):
        # synthetic: 0 real rows (`data/standin/review_decisions.csv`).
        with TemporaryDirectory() as folder:
            self.assertEqual(script.read_review_decisions(decisions_file(folder, HEADER + "cross_season_ids,1,approve,,x,y,z\n"))[0]["item_type"], "cross_season_ids")

    def test_d_approve_runs_after_rule_3_and_changes_30_rows(self):
        result, without_rows = sample_finished(), sample_finish([])
        self.assertEqual(result.joined_after - result.joined_before, 30)
        self.assertEqual(without_rows.joined_after, result.joined_before)
        changed = set(result.rule3.final) - set(without_rows.rule3.final)
        self.assertEqual({group.understat_id for group in changed}, {10095})
        # Rule 3 runs without the decisions, and the guard's own verdict is still there to see.
        self.assertEqual(sample_rule3().guard[EZZALZOULI][0], "disagree")

    def test_d_approve_restores_guard_removed_link(self):
        result = sample_finished()
        self.assertEqual(result.rule3.guard[EZZALZOULI], ("approved", 839, 933))
        group = next(found for found, pair in sample_rule3().pair_of.items() if pair == EZZALZOULI)
        self.assertNotIn(group, sample_rule3().final)
        self.assertEqual(result.rule3.final[group], ("map", "bed68338"))

    def test_d_approved_link_stays_in_name_map_csv(self):
        keys = [tuple(row[:5]) for row in join.name_map_file_rows(sample_finished().rule3, {}.get)]
        self.assertIn(("ESP", 2023, 10095, "Abdessamad Ezzalzouli", "bed68338"), keys)
        self.assertNotIn(("ESP", 2023, 10095, "Abdessamad Ezzalzouli", "bed68338"), [tuple(row[:5]) for row in join.name_map_file_rows(sample_finish([]).rule3, {}.get)])

    def test_d_synthetic_approve_stays_on_its_own_link_type(self):
        # synthetic: 0 real rows.
        groups, rosters, name_map_key, anchor_key = barred_case()
        self.assert_stops("stale", anchor_key, rows_of=groups, rosters=rosters, decisions=[decision("name_map", anchor_key, "approve")])
        self.assert_stops("stale", name_map_key, rows_of=groups, rosters=rosters, decisions=[decision("season_anchor", name_map_key, "approve")])
        # On its own type, `approve` brings back an anchor link the guard removed, and its verdict says so.
        anchored = {hand_group("m1"): 1, hand_group("m2"): 1, hand_group("m3"): 1}
        anchor_rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike")), ("m3", "A"): hand_roster(("x", "Kike Garcia"), ("w", "Kike Lopez"))}
        low_minutes = hand_facts({"x": 900}, season_rows={("ESP", 2021, "Kike"): [join.SeasonRow({"A"}, 100)]})
        self.assertNotIn(hand_group("m3"), hand_run(anchored, anchor_rosters, facts=low_minutes).rule3.final)
        result = hand_run(anchored, anchor_rosters, [decision("season_anchor", anchor_key, "approve")], facts=low_minutes)
        self.assertEqual(result.rule3.final[hand_group("m3")], ("season_anchor", "x"))
        self.assertEqual(result.rule3.anchor_guard[join.PlayerSeasonName("ESP", 2021, 1, "Kike", "x")][0], "approved")

    def test_d_synthetic_approve_clears_partial_join(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = unjoined_case()
        candidate = [("ESP", 2022, "x")]
        self.assertEqual(hand_run(rows_of, rosters, [], candidate).pool, [])
        result = hand_run(rows_of, rosters, [decision("partial_join", "ESP|2021|1", "approve")], candidate)
        self.assertEqual(result.pool, candidate)
        self.assertNotIn(("ESP", 2021, 1), result.partial)

    def test_d_synthetic_approve_on_flagged_partial_join_stays_cleared(self):
        # synthetic: hand-made row on Jeffinho, who has no `player_season` key, so this key is his only `approve` route.
        result = sample_finish([decision("partial_join", "FRA|2022|11399", "approve")])
        self.assertNotIn(JEFFINHO, result.flags)
        self.assertNotIn(("FRA", 2022, 11399), result.partial)
        self.assertIn(JEFFINHO, sample_finish([]).flags)

    def test_d_synthetic_approve_returns_player_season(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = unjoined_case()
        candidate = [("ESP", 2022, "x")]
        self.assertEqual(hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|x", "approve")], candidate).pool, candidate)

    def test_d_synthetic_approved_player_season_stays_cleared_after_recompute(self):
        # synthetic: hand-made row on Dennis Johnsen, 14 of 15 (T7:247).
        self.assertNotIn(JOHNSEN, sample_finish([]).pool)
        result = sample_finish([decision("player_season", JOHNSEN_KEYS[0], "approve")])
        self.assertIn(JOHNSEN, result.pool)
        self.assertNotIn(JOHNSEN, result.flags)
        self.assertNotIn(("ITA", 2021, 9882), result.partial)

    def test_d_synthetic_reject_removes_a_link(self):
        # synthetic: 0 real rows.
        group, other = hand_group("m1"), hand_group("m2")
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("x", "Kike"))}
        rows_of = {group: 1, other: 1}
        self.assertIn(group, hand_run(rows_of, rosters).rule3.final)
        result = hand_run(rows_of, rosters, [decision("name_map", "ESP|2021|1|Kike|x", "reject")])
        self.assertEqual(result.rule3.final, {other: ("exact", "x")})
        self.assertEqual(join.name_map_file_rows(result.rule3, {}.get), [])
        # An anchor resting on the rejected links goes with them, and the report lists it.
        anchored = hand_group("m3")
        evidence_rows = {hand_group("m1"): 1, hand_group("m2"): 1, anchored: 1}
        evidence_rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("x", "Kike Garcia")), ("m3", "A"): hand_roster(("x", "Kike Garcia"), ("w", "Kike Lopez"))}
        self.assertEqual(hand_run(evidence_rows, evidence_rosters).rule3.final[anchored], ("season_anchor", "x"))
        gone = hand_run(evidence_rows, evidence_rosters, [decision("name_map", "ESP|2021|1|Kike|x", "reject")])
        self.assertEqual(gone.rule3.final, {})
        self.assertEqual(gone.anchors_removed, [anchored])

    def test_d_synthetic_reject_keeps_a_flag(self):
        # synthetic: 0 real rows. The row joins m2, so `partial_join` would clear on its own, and the second row keeps the hold.
        joined, _, rows_of, rosters = unjoined_case()
        candidate = [("ESP", 2022, "x")]
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|x", "reject")], candidate)
        self.assertEqual(result.pool, [])
        self.assertIn(("ESP", 2022, "x"), result.flags)
        rows = [decision("partial_join", "ESP|2021|1", "link_to", "z"), decision("player_season", "ESP|2021|x", "reject"), decision("cross_season_ids", "1", "approve")]
        joined_up = hand_run({joined: 18, hand_group("m2"): 2}, rosters, rows, candidate)
        self.assertEqual(joined_up.pool, [])
        self.assertIn(("ESP", 2021, 1), joined_up.partial)

    def test_d_synthetic_reject_does_not_clear_the_cross_season_failure(self):
        # synthetic: 0 real (design check).
        first, second = hand_group("m1", name="Kike Garcia"), hand_group("m2", name="Enrique Lopez")
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("y", "Enrique Lopez"))}
        rows = {first: 1, second: 1}
        self.assert_stops("cross_season_ids", rows_of=rows, rosters=rosters, decisions=[decision("player_season", "ESP|2021|x", "reject")], candidates=[("ESP", 2022, "x")])

    def test_d_synthetic_link_to_joins_rows(self):
        # synthetic: 0 real rows.
        group = hand_group("m1")
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia"), ("z", "Enrique"))}
        result = hand_run({group: 1}, rosters, [decision("name_map", "ESP|2021|1|Kike|x", "link_to", "z")])
        self.assertEqual(result.rule3.final, {group: ("reviewed", "z")})
        self.assertEqual(join.name_map_file_rows(result.rule3, {}.get), [])

    def combined_case(self, shared_match=False):
        group, carlos = hand_group("m1"), hand_group("m3", name="Carlos")
        rosters = {("m1", "A"): hand_roster(("x", "Kike"), *([("c", "Carlos")] if shared_match else [])), ("m3", "A"): hand_roster(("c", "Carlos"))}
        return group, {group: 1, carlos: 1}, rosters

    def test_d_synthetic_link_to_player_season_combines_records(self):
        # synthetic: 0 real rows. x and c each hold 90 minutes, and only together do they pass the hand-made 180-minute line.
        group, rows_of, rosters = self.combined_case()
        at_180 = lambda positions: sorted(key for key, total in positions.groupby(["league", "Season_End_Year", "fbref_id"])["Min"].sum().items() if total >= 180) + [("ESP", 2022, "c")]
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], at_180)
        self.assertEqual(set(result.positions["fbref_id"]), {"x"})
        self.assertEqual(result.positions["Min"].sum(), 180)
        # c's own joined shots come along under x, so they are not left on a retired id.
        self.assertEqual(result.rule3.final, {group: ("exact", "x"), hand_group("m3", name="Carlos"): ("exact", "x")})
        self.assertIn(("ESP", 2022, "x"), result.pool)

    def test_d_synthetic_link_to_player_season_stops_on_shared_match(self):
        # synthetic: 0 real rows.
        _, rows_of, rosters = self.combined_case(shared_match=True)
        self.assert_stops("share a match", rows_of=rows_of, rosters=rosters, decisions=[decision("player_season", "ESP|2021|c", "link_to", "x")], candidates=[("ESP", 2022, "c")])

    def test_d_synthetic_combined_record_failing_pool_test_stays_out(self):
        # synthetic: 0 real rows. The hand-made line is 900 minutes, and the two ids hold 180 together.
        _, rows_of, rosters = self.combined_case()
        candidates = lambda positions: [("ESP", 2022, "c")] if "c" in set(positions["fbref_id"]) else at_900_minutes(positions)
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], candidates)
        self.assertEqual(result.pool, [])
        self.assertEqual(result.combined_outside_pool, [("ESP", 2022, "x")])

    def test_d_synthetic_merge_ids_links_second_understat_id(self):
        # synthetic: 0 real rows.
        first, second, rows_of, rosters = collision_case()
        result = hand_run(rows_of, rosters, [decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x")])
        self.assertEqual(result.rule3.final[second], ("reviewed", "x"))
        self.assertEqual(result.rule3.final[first][1], "x")

    def test_d_synthetic_merge_ids_key_exists_on_an_exact_link(self):
        # synthetic: 0 real collisions (design check). Exact links have a key only inside a collision.
        _, _, rows_of, rosters = collision_case()
        self.assertEqual(hand_run(rows_of, rosters).rule3.final, {})
        hand_run(rows_of, rosters, [decision("name_map", "ESP|2021|1|Kike|x", "merge_ids", "x")])
        group = hand_group("m1")
        self.assert_stops("stale", rows_of={group: 1}, rosters={("m1", "A"): hand_roster(("x", "Kike"))}, decisions=[decision("name_map", "ESP|2021|1|Kike|x", "reject")])

    def test_d_synthetic_merge_ids_clears_the_no_id_collisions_check(self):
        # synthetic: 0 real collisions (design check).
        _, _, rows_of, rosters = collision_case()
        self.assertEqual(hand_run(rows_of, rosters).collisions, {("ESP", 2021, "x"): [1, 2]})
        self.assertEqual(hand_run(rows_of, rosters, [decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x")]).collisions, {})
        # `approve` on one id settles a collision too, and an exact link stays an exact link.
        settled = hand_run(rows_of, rosters, [decision("name_map", "ESP|2021|1|Kike|x", "approve")])
        self.assertEqual(settled.rule3.final, {hand_group("m1"): ("exact", "x")})
        self.assertEqual(settled.rule3.anchor_pair_of, {})
        # One row settles its own FBref id and lists every id it brought back. Another collision of the same id stays out.
        three = {hand_group("m1"): 1, hand_group("m2", 2): 1, hand_group("m3", 3): 1}
        three_rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike")), ("m3", "A"): hand_roster(("x", "Kike"))}
        self.assertEqual(hand_run(three, three_rosters, [decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x")]).merged_collisions, [(("ESP", 2021, "x"), [1, 2, 3])])
        crossed = {hand_group("m1"): 1, hand_group("m2", 2): 1, hand_group("m7"): 1, hand_group("m8", 3): 1}
        crossed_rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike")), ("m7", "A"): hand_roster(("w", "Kike")), ("m8", "A"): hand_roster(("w", "Kike"))}
        allowed = decision("cross_season_ids", "1", "approve")
        with self.assertRaises(SystemExit):
            hand_run(crossed, crossed_rosters, [decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x"), allowed])
        only_x = hand_run(crossed, crossed_rosters, [decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x")])
        self.assertEqual(set(only_x.rule3.final), {hand_group("m1"), hand_group("m2", 2)})
        self.assertEqual(only_x.collisions, {("ESP", 2021, "w"): [1, 3]})

    def test_d_synthetic_merge_ids_row_is_listed(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = collision_case()
        row = decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x")
        self.assertEqual(hand_run(rows_of, rosters, [row]).merge_ids_rows, [row])

    def test_d_synthetic_approve_restores_stopped_link(self):
        # synthetic: 0 real rows.
        first, _, rows_of, rosters, first_key, _ = stopped_case()
        self.assertEqual(hand_run(rows_of, rosters).rule3.final, {})
        self.assertEqual(hand_run(rows_of, rosters, [decision("name_map", first_key, "approve")]).rule3.final, {first: ("map", "x")})

    def test_d_synthetic_approved_stopped_link_needs_a_cross_season_row(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters, first_key, second_key = stopped_case()
        both = [decision("name_map", first_key, "approve"), decision("name_map", second_key, "approve")]
        self.assert_stops("cross_season_ids", "1", rows_of=rows_of, rosters=rosters, decisions=both)
        self.assertEqual(len(hand_run(rows_of, rosters, [*both, decision("cross_season_ids", "1", "approve")]).rule3.final), 2)

    def test_d_synthetic_reject_leaves_stopped_link_removed(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters, first_key, _ = stopped_case()
        self.assertEqual(hand_run(rows_of, rosters, [decision("name_map", first_key, "reject")]).rule3.final, {})

    def test_d_synthetic_link_to_redirects_stopped_link(self):
        # synthetic: 0 real rows.
        first, _, rows_of, rosters, first_key, _ = stopped_case()
        self.assertEqual(hand_run(rows_of, rosters, [decision("name_map", first_key, "link_to", "z")]).rule3.final, {first: ("reviewed", "z")})

    def test_d_synthetic_approving_stopped_link_keeps_the_bar(self):
        # synthetic: 0 real rows.
        groups, rosters, name_map_key, _ = barred_case()
        result = hand_run(groups, rosters, [decision("name_map", name_map_key, "approve"), decision("cross_season_ids", "1", "approve")])
        self.assertEqual(result.rule3.final[hand_group("m4", name="Kik")], ("map", "y"))
        self.assertNotIn(hand_group("m3"), result.rule3.final)

    def test_d_synthetic_barred_link_returns_through_its_own_row(self):
        # synthetic: 0 real rows. Its own `link_to` works as well as its own `approve`.
        groups, rosters, _, anchor_key = barred_case()
        self.assertEqual(hand_run(groups, rosters, [decision("season_anchor", anchor_key, "approve")]).rule3.final[hand_group("m3")], ("season_anchor", "x"))
        self.assertEqual(hand_run(groups, rosters, [decision("season_anchor", anchor_key, "link_to", "x")]).rule3.final[hand_group("m3")], ("reviewed", "x"))

    def test_d_synthetic_stale_key_stops(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters, _, _ = stopped_case()
        self.assert_stops("stale", "ESP|2021|9|Nobody|x", rows_of=rows_of, rosters=rosters, decisions=[decision("name_map", "ESP|2021|9|Nobody|x", "approve")])

    def test_d_guard_removed_link_is_not_stale(self):
        self.assertIn(EZZALZOULI, sample_rule3().guard)
        self.assertEqual(sample_rule3().guard[EZZALZOULI][0], "disagree")
        self.assertEqual(len(sample_finished().rule3.final) - len(sample_finish([]).rule3.final), sum(1 for group, pair in sample_rule3().pair_of.items() if pair == EZZALZOULI))

    def test_d_synthetic_collision_removed_link_is_not_stale(self):
        # synthetic: 0 real collisions after the guard (design check).
        first, second, rows_of, rosters = collision_case()
        result = hand_run(rows_of, rosters, [decision("name_map", "ESP|2021|1|Kike|x", "reject")])
        self.assertNotIn(first, result.rule3.final)
        self.assertNotIn(second, result.rule3.final)

    def test_d_synthetic_one_player_season_row_covers_every_flag(self):
        # synthetic: 0 real rows. x holds `partial_join` and two ids at once, and one row covers both.
        first, second = hand_group("m1", name="Kike Garcia"), hand_group("m2", name="Enrique Lopez")
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("y", "Enrique Lopez")), ("m4", "A"): hand_roster(("z", "Ana"))}
        rows_of = {first: 19, second: 1, hand_group("m4", name="Nobody"): 19}
        allowed = decision("cross_season_ids", "1", "approve")
        self.assertEqual(hand_run(rows_of, rosters, [allowed], [("ESP", 2022, "x")]).flags[("ESP", 2022, "x")], {"partial_join", "two ids"})
        self.assertEqual(hand_run(rows_of, rosters, [allowed, decision("player_season", "ESP|2021|x", "approve")], [("ESP", 2022, "x")]).pool, [("ESP", 2022, "x")])

    def test_d_synthetic_player_season_key_exists_for_any_flagged_candidate(self):
        # synthetic: 0 real rows. No flag, no key: the row stops as stale.
        group = hand_group("m1")
        rosters = {("m1", "A"): hand_roster(("x", "Kike"))}
        self.assert_stops("stale", rows_of={group: 1}, rosters=rosters, decisions=[decision("player_season", "ESP|2021|x", "approve")], candidates=[("ESP", 2022, "x")])
        _, _, rows_of, flagged_rosters = unjoined_case()
        self.assertEqual(hand_run(rows_of, flagged_rosters, [decision("player_season", "ESP|2021|x", "reject")], [("ESP", 2022, "x")]).pool, [])

    def test_d_synthetic_link_to_player_season_reruns_every_check(self):
        # synthetic: 0 real rows. c has no shots and x is at 1 of 2, so the combined record is still partial and stays held.
        _, _, rows_of, rosters = unjoined_case()
        rosters = {**rosters, ("m3", "A"): hand_roster(("c", "Carlos"))}
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], lambda positions: [("ESP", 2022, fbref_id) for fbref_id in ("c", "x") if fbref_id in set(positions["fbref_id"])])
        self.assertEqual(result.flags[("ESP", 2022, "x")], {"partial_join"})
        self.assertEqual(result.pool, [])
        # The guard runs again too: 900 agrees with x's 900, and 900 against the combined 1400 does not, so the link goes.
        mapped = hand_group("m1")
        facts = hand_facts({"x": 900, "c": 500})
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m3", "A"): hand_roster(("c", "Carlos"))}
        again = hand_run({mapped: 1}, rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], [("ESP", 2022, "c")], facts=facts)
        self.assertEqual(again.rule3.guard[join.PlayerSeasonName("ESP", 2021, 1, "Kike", "x")], ("disagree", 900, 1400))
        self.assertEqual(again.rule3.final, {})
        # And a link the guard took away comes back when the combined minutes agree: 900 against 450 and 450.
        back = hand_run({mapped: 1}, rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], [("ESP", 2022, "c")], facts=hand_facts({"x": 450, "c": 450}))
        self.assertEqual(back.rule3.final, {mapped: ("map", "x")})
        # An approval covers every match of the pair, and a combined record keeps it.
        matches = {hand_group("m1"): 1, hand_group("m2"): 1}
        two_matches = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("x", "Kike Garcia")), ("m3", "A"): hand_roster(("c", "Carlos")), ("m4", "A"): hand_roster(("y", "Yago"))}
        rows = [decision("name_map", "ESP|2021|1|Kike|x", "approve"), decision("player_season", "ESP|2021|x", "link_to", "y")]
        kept = hand_run(matches, two_matches, rows, [], [join.RefusedMerge("ESP", 2022, "Kike", ("x", "y"), "both ids in other seasons")], facts=hand_facts({"x": 100, "y": 100}))
        self.assertEqual(kept.rule3.final, {hand_group("m1"): ("map", "y"), hand_group("m2"): ("map", "y")})
        self.assertEqual(kept.rule3.guard[join.PlayerSeasonName("ESP", 2021, 1, "Kike", "y")][0], "approved")
        # An anchor link goes through the guard again as well.
        anchor_rows = {hand_group("m1"): 1, hand_group("m2"): 1, hand_group("m3"): 1}
        anchor_rosters = {("m1", "A"): hand_roster(("c", "Kike")), ("m2", "A"): hand_roster(("c", "Kike")), ("m3", "A"): hand_roster(("c", "Kike Garcia"), ("w", "Kike Lopez")), ("m4", "A"): hand_roster(("x", "Xavi"))}
        anchored = hand_run(anchor_rows, anchor_rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], [], [join.RefusedMerge("ESP", 2022, "Kike", ("c", "x"), "both ids in other seasons")], facts=hand_facts({"c": 900, "x": 500}))
        self.assertEqual(anchored.rule3.final, {hand_group("m1"): ("exact", "x"), hand_group("m2"): ("exact", "x")})
        self.assertEqual(anchored.rule3.anchor_guard[join.PlayerSeasonName("ESP", 2021, 1, "Kike", "x")], ("disagree", 900, 1400))
        # A link a collision took away does not come back from an unrelated combine.
        collided = {hand_group("m1"): 1, hand_group("m2", 2): 1}
        collided_rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("x", "Kike Garcia")), ("m3", "A"): hand_roster(("c", "Carlos"))}
        no_return = hand_run(collided, collided_rosters, [decision("player_season", "ESP|2021|c", "link_to", "x")], [("ESP", 2022, "c")], facts=hand_facts({"x": 900, "c": 0}))
        self.assertEqual(no_return.rule3.final, {})

    def test_d_synthetic_refused_merge_has_a_player_season_key(self):
        # synthetic: 0 real (design check, merge results). y is outside the Pool, and its key exists.
        _, rows_of, rosters = refused_case()
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|y", "reject")], [], [REFUSED])
        self.assertEqual(result.refused_merges, [REFUSED])

    def test_d_synthetic_link_to_combines_a_refused_merge(self):
        # synthetic: 0 real.
        _, rows_of, rosters = refused_case()
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|y", "link_to", "x")], [], [REFUSED])
        self.assertEqual(set(result.positions["fbref_id"]), {"x"})

    def test_d_synthetic_reject_keeps_a_refused_merge_apart(self):
        # synthetic: 0 real.
        _, rows_of, rosters = refused_case()
        result = hand_run(rows_of, rosters, [decision("player_season", "ESP|2021|y", "reject")], [], [REFUSED])
        self.assertEqual(set(result.positions["fbref_id"]), {"x", "y"})
        self.assertEqual(result.refused_merges, [REFUSED])
        self.assertEqual(result.flags, {})

    def test_d_synthetic_approve_on_refused_merge_stops(self):
        # synthetic: 0 real (design check, merge results).
        _, rows_of, rosters = refused_case()
        self.assert_stops("reject", "link_to", rows_of=rows_of, rosters=rosters, decisions=[decision("player_season", "ESP|2021|y", "approve")], refused=[REFUSED])

    def test_d_synthetic_opposite_link_to_on_refused_merge_stops(self):
        # synthetic: 0 real (design check, merge results).
        _, rows_of, rosters = refused_case()
        rows = [decision("player_season", "ESP|2021|y", "link_to", "x"), decision("player_season", "ESP|2021|x", "link_to", "y")]
        self.assert_stops("ESP|2021|x", "ESP|2021|y", rows_of=rows_of, rosters=rosters, decisions=rows, refused=[REFUSED])

    def test_d_synthetic_reject_and_link_to_on_one_refused_merge_stop(self):
        # synthetic: 0 real (design check, merge results).
        _, rows_of, rosters = refused_case()
        rows = [decision("player_season", "ESP|2021|y", "link_to", "x"), decision("player_season", "ESP|2021|x", "reject")]
        self.assert_stops("ESP|2021|x", "ESP|2021|y", rows_of=rows_of, rosters=rosters, decisions=rows, refused=[REFUSED])

    def test_d_synthetic_link_to_joins_an_unflagged_unjoined_row(self):
        # synthetic: 0 real rows. Marc Cardona's own target has no FBref row in that match, so on his data the row stops (D39).
        joined, unjoined, _, rosters = unjoined_case()
        result = hand_run({joined: 19, unjoined: 1}, rosters, [decision("partial_join", "ESP|2021|1", "link_to", "z"), decision("cross_season_ids", "1", "approve")])
        self.assertEqual(result.rule3.final[unjoined], ("reviewed", "z"))
        self.assertNotIn(("ESP", 2021, 1), hand_run({joined: 19, unjoined: 1}, rosters).partial)
        with self.assertRaises(SystemExit) as stop:
            sample_finish([decision("partial_join", "ESP|2023|5159", "link_to", "b92b456a")])
        self.assertIn("no FBref row in match b5b5ee07", str(stop.exception))

    def test_d_synthetic_partial_join_key_with_no_unjoined_row_is_stale(self):
        # synthetic: 0 real rows.
        group = hand_group("m1")
        self.assert_stops("stale", rows_of={group: 1}, rosters={("m1", "A"): hand_roster(("x", "Kike"))}, decisions=[decision("partial_join", "ESP|2021|1", "reject")])

    def test_d_synthetic_approve_on_unflagged_partial_join_stops(self):
        # synthetic: hand-made row on Marc Cardona, 21 of 22 (design check).
        with self.assertRaises(SystemExit) as stop:
            sample_finish([decision("partial_join", "ESP|2023|5159", "approve")])
        self.assertIn("link_to", str(stop.exception))

    def test_d_synthetic_reject_on_unflagged_partial_join_leaves_rows_unjoined(self):
        # synthetic: hand-made row on Marc Cardona (design check).
        result = sample_finish([decision("partial_join", "ESP|2023|5159", "reject")])
        self.assertNotIn(sample_groups_of(*CARDONA_GROUP)[0], result.rule3.final)
        self.assertIn(("ESP", 2023, 5159), result.unjoined_listed)

    def test_d_synthetic_unknown_item_type_stops(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("nonsense,k,approve,,x,y,z\n", "nonsense")

    def test_d_synthetic_unknown_decision_stops(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("name_map,k,maybe,,x,y,z\n", "maybe")

    def test_d_synthetic_link_to_without_fbref_id_stops(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("name_map,k,link_to,,x,y,z\n", "fbref_id", "link_to")

    def test_d_synthetic_merge_ids_without_fbref_id_stops(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("name_map,k,merge_ids,,x,y,z\n", "fbref_id", "merge_ids")

    def test_d_synthetic_link_to_fbref_id_outside_league_season_stops(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = unjoined_case()
        self.assert_stops("nobody", "league-season", rows_of=rows_of, rosters=rosters, decisions=[decision("partial_join", "ESP|2021|1", "link_to", "nobody")])

    def test_d_synthetic_link_to_target_not_in_those_matches_stops(self):
        # synthetic: 0 real rows. x plays in that league-season, in m1, and not in m2, where the unjoined row is.
        _, _, rows_of, rosters = unjoined_case()
        self.assert_stops("x", "m2", rows_of=rows_of, rosters=rosters, decisions=[decision("partial_join", "ESP|2021|1", "link_to", "x")])

    def test_d_synthetic_merge_ids_fbref_id_outside_league_season_stops(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = collision_case()
        self.assert_stops("nobody", "league-season", rows_of=rows_of, rosters=rosters, decisions=[decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "nobody")])

    def test_d_synthetic_fbref_id_on_other_decision_stops(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("name_map,k,approve,x,x,y,z\n", "fbref_id", "approve")

    def test_d_synthetic_merge_ids_on_player_season_stops(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("player_season,k,merge_ids,x,x,y,z\n", "merge_ids", "player_season")

    def test_d_synthetic_merge_ids_without_second_id_stops(self):
        # synthetic: 0 real rows.
        group = hand_group("m1")
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia"), ("z", "Enrique"))}
        self.assert_stops("merge_ids", "second", rows_of={group: 1}, rosters=rosters, decisions=[decision("name_map", "ESP|2021|1|Kike|x", "merge_ids", "z")])

    def test_d_synthetic_two_rows_on_one_key_stop(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("name_map,k,approve,,x,y,z\nname_map,k,reject,,x,y,z\n", "two rows", "k")

    def test_d_synthetic_approve_and_reject_on_two_keys_of_one_player_stop(self):
        # synthetic: hand-made rows on Dennis Johnsen, in both directions.
        for first, second in (("approve", "reject"), ("reject", "approve")):
            with self.assertRaises(SystemExit) as stop:
                sample_finish([decision("player_season", JOHNSEN_KEYS[0], first), decision("partial_join", JOHNSEN_KEYS[1], second)])
            self.assertIn(JOHNSEN_KEYS[0], str(stop.exception))
            self.assertIn(JOHNSEN_KEYS[1], str(stop.exception))

    def test_d_synthetic_player_season_without_shots_stops(self):
        # synthetic: 0 real rows.
        _, rows_of, rosters = no_shots_case()
        self.assert_stops("no joined shots", "partial_join", rows_of=rows_of, rosters=rosters, decisions=[decision("player_season", "ESP|2021|c", "approve")], candidates=[("ESP", 2022, "c")])

    def test_d_synthetic_two_understat_ids_without_merge_ids_stop(self):
        # synthetic: 0 real rows.
        group, other = hand_group("m1"), hand_group("m1", understat_id=2, name="Enrique")
        rosters = {("m1", "A"): hand_roster(("x", "Kike")), ("m2", "A"): hand_roster(("z", "Ana"))}
        rows = {group: 1, other: 1, hand_group("m2", understat_id=2, name="Nobody"): 1}
        self.assert_stops("merge_ids", "[1, 2]", rows_of=rows, rosters=rosters, decisions=[decision("partial_join", "ESP|2021|2", "link_to", "x")], positions=positions_of({**rosters, ("m2", "A"): hand_roster(("x", "Kike"))}))

    def test_d_synthetic_approve_with_two_understat_ids_stops(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = collision_case()
        rows = [decision("name_map", "ESP|2021|1|Kike|x", "approve"), decision("name_map", "ESP|2021|2|Kike|x", "approve")]
        self.assert_stops("merge_ids", "[1, 2]", rows_of=rows_of, rosters=rosters, decisions=rows)

    def test_d_synthetic_row_order_does_not_change_the_result(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters, first_key, second_key = stopped_case()
        rows = [decision("name_map", first_key, "approve"), decision("name_map", second_key, "link_to", "z"), decision("cross_season_ids", "1", "approve")]
        forward, backward = hand_run(rows_of, rosters, rows), hand_run(rows_of, rosters, rows[::-1])
        self.assertEqual((forward.rule3.final, forward.flags, forward.partial, forward.pool), (backward.rule3.final, backward.flags, backward.partial, backward.pool))
        # A rejected link stays out, whichever row names the same rows, and whichever id of a collision the reject is on.
        group, unjoined = hand_group("m1"), hand_group("m2")
        link_rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia"), ("z", "Enrique")), ("m2", "A"): hand_roster(("z", "Enrique"))}
        both = [decision("name_map", "ESP|2021|1|Kike|x", "reject"), decision("partial_join", "ESP|2021|1", "link_to", "z")]
        for order in (both, both[::-1]):
            self.assertEqual(hand_run({group: 1, unjoined: 1}, link_rosters, order).rule3.final, {unjoined: ("reviewed", "z")})
        _, _, collided, collision_rosters = collision_case()
        for rejected, merged in ((1, 2), (2, 1)):
            mixed = [decision("name_map", f"ESP|2021|{rejected}|Kike|x", "reject"), decision("name_map", f"ESP|2021|{merged}|Kike|x", "merge_ids", "x")]
            for order in (mixed, mixed[::-1]):
                self.assert_stops("no second", rows_of=collided, rosters=collision_rosters, decisions=order)
        # The listed rows keep one order too, and a chain of `link_to` rows stops rather than depending on how the ids sort.
        second_collision = {hand_group("m5", 3): 1, hand_group("m6", 4): 1}
        two_collisions = {**collided, **second_collision}
        rosters_of_two = {**collision_rosters, ("m5", "A"): hand_roster(("y", "Kike")), ("m6", "A"): hand_roster(("y", "Kike"))}
        merges = [decision("name_map", "ESP|2021|2|Kike|x", "merge_ids", "x"), decision("name_map", "ESP|2021|4|Kike|y", "merge_ids", "y")]
        self.assertEqual(hand_run(two_collisions, rosters_of_two, merges[::-1]).merge_ids_rows, merges)
        _, _, chain_rows, chain_rosters = unjoined_case()
        chain_rosters = {**chain_rosters, ("m3", "A"): hand_roster(("c", "Carlos")), ("m4", "A"): hand_roster(("d", "Dani"))}
        chain = [decision("player_season", "ESP|2021|c", "link_to", "d"), decision("player_season", "ESP|2021|d", "link_to", "x")]
        self.assert_stops("has its own link_to", rows_of=chain_rows, rosters=chain_rosters, decisions=chain, candidates=[("ESP", 2022, "c"), ("ESP", 2022, "d")])

    def test_d_synthetic_partial_join_is_recomputed_after_decisions(self):
        # synthetic: 0 real rows.
        _, _, rows_of, rosters = unjoined_case()
        self.assertIn(("ESP", 2021, 1), hand_run(rows_of, rosters).partial)
        self.assertNotIn(("ESP", 2021, 1), hand_run(rows_of, rosters, [decision("partial_join", "ESP|2021|1", "link_to", "z"), decision("cross_season_ids", "1", "approve")]).partial)

    def test_d_pool_count_is_returned_before_and_after_decisions(self):
        result = sample_finished()
        self.assertEqual(result.pool_after, len(result.pool))
        self.assertEqual(result.pool_before, sample_finish([]).pool_after)
        self.assertEqual(sample_finish([*sample_decisions(), decision("player_season", JOHNSEN_KEYS[0], "approve")]).pool_after, result.pool_after + 1)

    def test_d_synthetic_two_fbref_ids_fail_the_run(self):
        # synthetic: 0 real with merges on (design check).
        first, second = hand_group("m1", name="Kike Garcia"), hand_group("m2", name="Enrique Lopez", season=2022)
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("y", "Enrique Lopez"))}
        self.assert_stops("cross_season_ids", "1", "x", "y", rows_of={first: 1, second: 1}, rosters=rosters)

    def test_d_synthetic_cross_season_row_allows_two_ids(self):
        # synthetic: 0 real rows.
        first, second = hand_group("m1", name="Kike Garcia"), hand_group("m2", name="Enrique Lopez", season=2022)
        rosters = {("m1", "A"): hand_roster(("x", "Kike Garcia")), ("m2", "A"): hand_roster(("y", "Enrique Lopez"))}
        result = hand_run({first: 1, second: 1}, rosters, [decision("cross_season_ids", "1", "approve")])
        self.assertEqual(result.cross_season_cases, [(1, ("x", "y"))])
        # A second id that a decision made holds a candidate, as one from rule 3 does.
        _, _, rows_of, unjoined_rosters = unjoined_case()
        made = hand_run(rows_of, unjoined_rosters, [decision("partial_join", "ESP|2021|1", "link_to", "z"), decision("cross_season_ids", "1", "approve")], [("ESP", 2022, "x")])
        self.assertIn("two ids", made.flags[("ESP", 2022, "x")])
        self.assertEqual(made.pool, [])

    def test_d_synthetic_cross_season_row_accepts_only_approve(self):
        # synthetic: 0 real rows.
        self.assert_file_stops("cross_season_ids,1,reject,,x,y,z\n", "cross_season_ids", "approve")

    def test_d_synthetic_cross_season_row_stale_stops(self):
        # synthetic: 0 real rows.
        group = hand_group("m1")
        self.assert_stops("stale", "cross_season_ids", rows_of={group: 1}, rosters={("m1", "A"): hand_roster(("x", "Kike"))}, decisions=[decision("cross_season_ids", "1", "approve")])

    def test_d_merges_off_skips_the_cross_season_check(self):
        unmerged = join.positions_for_join(SAMPLE, merges=False)
        off = sample_finish([], unmerged, merges_on=False)
        ids = {link[1] for group, link in off.rule3.final.items() if group.understat_id == 7944 and group.season == 2023}
        self.assertEqual(ids, STREFEZZA_IDS)
        self.assertEqual(off.cross_season_cases, [])
        rows_of = join.shot_groups(sample_shots(), join.link_matches(sample_shots(), unmerged, sample_clubs()).links, unmerged)[0]
        facts = join.guard_facts(unmerged, sample_shots(), join.season_rows_by_name(sample_clubs(), SAMPLE))
        with self.assertRaises(SystemExit) as stop:
            join.finish_join(join.rule3_links(rows_of, join.build_rosters(unmerged), facts), rows_of, join.build_rosters(unmerged), unmerged, [], [], lambda found: [], facts, True)
        self.assertIn("cross_season_ids", str(stop.exception))
        # A key that exists only on merged ids stops the merges-on run, and the merges-off run passes over it.
        row = decision("player_season", "ITA|2023|nobody", "reject")
        self.assertEqual(sample_finish([row], unmerged, merges_on=False).joined_after, off.joined_after)
        with self.assertRaises(SystemExit):
            sample_finish([row])
        # So does a row good only on merged ids: the survivor has no FBref row in this match until the merge.
        _, _, rows_of, rosters = unjoined_case()
        moved = decision("partial_join", "ESP|2021|1", "link_to", "x")
        self.assertEqual(hand_run(rows_of, rosters, [moved], merges_on=False).joined_after, 2)
        with self.assertRaises(SystemExit):
            hand_run(rows_of, rosters, [moved])


class MovedFromTheOldTestFile(unittest.TestCase):
    """The real cases of tests/test_measure_rule3.py and the asserts of the script's old self_check."""

    def test_angel_passes_the_minutes_guard(self):
        pair = join.PlayerSeasonName("ESP", 2020, 4136, "Ángel", "8cfc2f69")
        self.assertEqual(sample_rule3().guard[pair][0], "agree")

    def test_chema_reaches_angel_but_does_not_link(self):
        for match in ("92f705d2", "add782a1"):
            group = sample_groups_of("ESP", 2020, 6216, match)[0]
            self.assertIn("8cfc2f69", sample_name_map().undecided[group])
            self.assertNotIn(group, sample_rule3().final)

    def test_chema_is_flagged_partial_join_and_angel_is_not(self):
        self.assertNotIn(("ESP", 2020, 4136), sample_partial())
        self.assertIn(("ESP", 2020, 6216), sample_partial())

    def test_hwang_links_in_all_three_seasons_at_step_2_only(self):
        for season in (2021, 2022, 2023):
            for group in sample_groups_of("ENG", season, 8845):
                self.assertNotIn(group, sample_joined())
                self.assertEqual(sample_name_map().links[group], "169fd162")

    def test_name_rules(self):
        self.assertEqual(join.compared_name("Kylian Mbappe-Lottin"), "kylian mbappe lottin")
        self.assertEqual(join.compared_name("Martin Ødegaard"), join.compared_name("Martin Odegaard"))
        self.assertEqual(join.compared_name("N&#039;Golo Kanté"), "ngolo kante")
        self.assertTrue(join.is_name_map_candidate(["bruno"], ["bruno", "fernandes"]))
        self.assertTrue(join.is_name_map_candidate(["kylian", "mbappe", "lottin"], ["kylian", "mbappe"]))
        self.assertFalse(join.is_name_map_candidate(["bruno"], ["brunos", "fernandes"]))
        self.assertTrue(join.is_name_map_candidate(["fernandes", "bruno"], ["bruno", "miguel", "fernandes"]))


if __name__ == "__main__":
    unittest.main()
