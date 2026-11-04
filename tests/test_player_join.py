"""Rule 3 clauses, one test each. Real rows come from tests/fixtures/standin/rule3__*, cut by scripts/cut_fixtures.py.

A clause with 0 real cases uses a small hand-made input inside the test, says so in its name and in a comment, and never
goes in tests/fixtures/. Run from the repo root: python3 -m unittest discover tests
"""
import html
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


if __name__ == "__main__":
    unittest.main()
