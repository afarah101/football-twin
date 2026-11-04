"""Rule 3 on real rows from data/standin. With requirements.txt installed, run: python3 -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import measure_rule3 as rule3

ANGEL_ID, CHEMA_ID = 4136, 6216
ANGEL_RODRIGUEZ = "8cfc2f69"
MATCHES_WITH_BOTH = {"92f705d2", "add782a1"}
HWANG_ID, HWANG_FBREF_ID = 8845, "169fd162"
BABA_ID, BABA_FBREF_ID = 684, "e4086af3"


class TwoShotNamesReachOnePlayer(unittest.TestCase):
    """ESP 2020/21 Getafe: "Chema Rodríguez" has 2+ candidates, one of them Ángel Rodríguez, so he must not block "Ángel"."""

    @classmethod
    def setUpClass(cls):
        positions = rule3.load_positions()
        positions = positions[(positions["league"] == "ESP") & (positions["Season_End_Year"] == 2021)]
        shots = rule3.load_shots()
        shots = shots[(shots["league"] == "ESP") & (shots["season"] == 2020)]
        cls.clubs = rule3.understat_to_fbref_clubs()
        links, _, _ = rule3.link_matches(shots, positions, cls.clubs)
        cls.rows_of, _ = rule3.shot_groups(shots, links, positions)
        rosters = rule3.build_rosters(positions)
        joined = rule3.join_by_name(sorted(cls.rows_of), rosters)
        cls.mapped, cls.undecided, _, _ = rule3.name_map_links(sorted(cls.rows_of), rosters, joined)
        # shortcut: builds the stages here, without the guard on other links or the collision rule, because main runs them inline. Upgrade when #6 moves rule 3 out of main.
        after_step_2 = {**joined, **{group: ("map", fbref_id) for group, fbref_id in cls.mapped.items()}}
        cls.anchored, _ = rule3.season_anchor_links(cls.undecided, after_step_2)
        cls.final = {**after_step_2, **{group: ("season_anchor", fbref_id) for group, fbref_id in cls.anchored.items()}}
        cls.angel_minutes = int(positions.loc[positions["fbref_id"] == ANGEL_RODRIGUEZ, "Min"].sum())

    def groups_in_both_matches(self, understat_id):
        found = [group for group in self.rows_of if group.understat_id == understat_id and group.match in MATCHES_WITH_BOTH]
        self.assertEqual({group.match for group in found}, MATCHES_WITH_BOTH)
        return found

    def test_angel_links_to_angel_rodriguez(self):
        for group in self.groups_in_both_matches(ANGEL_ID):
            self.assertEqual(self.mapped[group], ANGEL_RODRIGUEZ)

    def test_chema_reaches_angel_rodriguez_but_does_not_link(self):
        for group in self.groups_in_both_matches(CHEMA_ID):
            self.assertIn(ANGEL_RODRIGUEZ, self.undecided[group])
            self.assertNotIn(group, self.final)

    def test_angel_passes_the_minutes_guard(self):
        pair = rule3.PlayerSeasonName("ESP", 2020, ANGEL_ID, "Ángel", ANGEL_RODRIGUEZ)
        guard = rule3.minutes_guard([pair], rule3.season_minutes_by_name(self.clubs), {("ESP", 2021, ANGEL_RODRIGUEZ): self.angel_minutes}, {("ESP", 2021, ANGEL_RODRIGUEZ): {"Getafe"}}, set())
        self.assertEqual(guard[pair][0], "agree")

    def test_chema_is_flagged_partial_join_and_angel_is_not(self):
        partial = rule3.partial_joins(self.rows_of, self.final)
        self.assertNotIn(("ESP", 2020, ANGEL_ID), partial)
        self.assertIn(("ESP", 2020, CHEMA_ID), partial)


class NameWordsInAnotherOrder(unittest.TestCase):
    """ENG 2021/22 to 2023/24 Wolves: the shot name "Hee-Chan Hwang" is FBref's "Hwang Hee-chan". Step 1 compares in order, so only step 2 can link them."""

    @classmethod
    def setUpClass(cls):
        positions = rule3.load_positions()
        positions = positions[(positions["league"] == "ENG") & positions["Season_End_Year"].between(2022, 2024)]
        shots = rule3.load_shots()
        shots = shots[(shots["league"] == "ENG") & shots["season"].between(2021, 2023)]
        links, _, _ = rule3.link_matches(shots, positions, rule3.understat_to_fbref_clubs())
        rows_of, _ = rule3.shot_groups(shots, links, positions)
        rosters = rule3.build_rosters(positions)
        cls.joined = rule3.join_by_name(sorted(rows_of), rosters)
        cls.mapped = rule3.name_map_links(sorted(rows_of), rosters, cls.joined)[0]
        cls.hwang = [group for group in rows_of if group.understat_id == HWANG_ID]

    def test_step_1_does_not_link_them(self):
        self.assertTrue(self.hwang)
        for group in self.hwang:
            self.assertNotIn(group, self.joined)

    def test_step_2_links_them_in_all_three_seasons(self):
        self.assertEqual({group.season for group in self.hwang}, {2021, 2022, 2023})
        for group in self.hwang:
            self.assertEqual(self.mapped.get(group), HWANG_FBREF_ID)


class RosterNameInsideTheShotName(unittest.TestCase):
    """ESP 2019/20, FRA 2018/19 and GER 2018/19: FBref's "Baba Rahman" is inside the shot name "Abdul Rahman Baba". Last names differ, so only the roster-inside-shot direction of the word set links them."""

    def test_step_2_links_all_8_rows_in_all_3_player_seasons(self):
        positions = rule3.load_positions()
        shots = rule3.load_shots()
        shots = shots[shots["match_id"].isin(shots.loc[shots["player_id"] == BABA_ID, "match_id"])]
        links, _, _ = rule3.link_matches(shots, positions, rule3.understat_to_fbref_clubs())
        rows_of, _ = rule3.shot_groups(shots, links, positions)
        rosters = rule3.build_rosters(positions)
        joined = rule3.join_by_name(sorted(rows_of), rosters)
        mapped = rule3.name_map_links(sorted(rows_of), rosters, joined)[0]
        baba = [group for group in rows_of if group.understat_id == BABA_ID]
        self.assertEqual(sum(rows_of[group] for group in baba), 8)
        self.assertEqual({group.player_season for group in baba}, {("ESP", 2019, BABA_ID), ("FRA", 2018, BABA_ID), ("GER", 2018, BABA_ID)})
        for group in baba:
            self.assertNotIn(group, joined)
            self.assertEqual(mapped.get(group), BABA_FBREF_ID)


class SelfCheck(unittest.TestCase):
    def test_self_check_passes(self):
        rule3.self_check()


if __name__ == "__main__":
    unittest.main()
