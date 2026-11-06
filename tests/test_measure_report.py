"""The #6 report (D22, D23): its sections, the review keys it lists, the shot gaps and the worst case for matches with no event rows.

The report itself is checked on data/standin by #21's acceptance checks. These tests cover the rules behind it on
hand-made inputs, so each is `synthetic`, with 0 real cases: the real cases are only in the full run.
Run from the repo root: python3 -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import measure_rule3 as script  # noqa: E402

KEY = ("ESP", 2024, "abcd1234")
MATCH = "https://fbref.com/en/matches/0000aaaa/x"
OTHER_MATCH = "https://fbref.com/en/matches/0000bbbb/x"


def appearance(url, player, fbref_id, pos, minutes, team="Getafe"):
    return {"MatchURL": url, "Team": team, "Player": player, "Pos": pos, "Min": minutes, "league": "ESP", "Season_End_Year": 2024, "fbref_id": fbref_id, "match": url.split("/")[5]}


def decision(key, choice, reason):
    return {"item_type": "player_season", "key": key, "decision": choice, "fbref_id": "", "reviewer": "x", "date": "y", "reason": reason}


class Report(unittest.TestCase):
    def test_synthetic_report_writes_each_section_as_a_level_2_heading(self):
        text = script.report_text([("Join rates", ["- a"]), ("Open items", [])])
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        self.assertIn("## Join rates", lines)
        self.assertIn("## Open items", lines)
        self.assertIn("None.", lines)  # an empty section says so, so it is never read as missing
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(text, script.report_text([("Join rates", ["- a"]), ("Open items", [])]))

    def test_synthetic_held_candidates_list_their_player_season_keys(self):
        lines = script.held_lines([KEY, ("ITA", 2020, "ffff0000")], {KEY: {"partial_join", "no joined shots"}}, {"abcd1234": "Roger"})
        self.assertEqual(lines, ["- `ESP|2023|abcd1234` Roger: no joined shots, partial_join"])

    def test_synthetic_shot_gap_without_a_decision_reads_unexplained_cause_unknown(self):
        self.assertEqual(script.gap_explanation(KEY, []), "unexplained, cause unknown")
        self.assertEqual(script.gap_explanation(KEY, [decision("ESP|2023|abcd1234", "reject", "no")]), "unexplained, cause unknown")

    def test_synthetic_shot_gap_with_an_approve_row_reads_explained_with_its_reason(self):
        self.assertEqual(script.gap_explanation(KEY, [decision("ESP|2023|abcd1234", "approve", "a penalty retaken")]), "explained: a penalty retaken")

    def test_synthetic_worst_case_counts_every_short_appearance_in_a_match_with_no_event_rows_as_a_substitute(self):
        # MATCH has no event rows. "Out" holds 460 attacking v 440 other minutes, 45 of the attacking ones in MATCH, so the
        # worst case leaves 415 v 440: out. "In" is the mirror: 440 v 460 with 45 other in MATCH, so 440 v 415: in.
        # "Full" plays 90 in MATCH, which is not under 90, so the worst case leaves it alone.
        rows = [
            appearance(OTHER_MATCH, "Out", "o", "FW", 415), appearance(OTHER_MATCH, "Out", "o", "DF", 440), appearance(MATCH, "Out", "o", "FW", 45),
            appearance(OTHER_MATCH, "In", "i", "FW", 440), appearance(OTHER_MATCH, "In", "i", "DF", 415), appearance(MATCH, "In", "i", "DF", 45),
            appearance(OTHER_MATCH, "Full", "f", "FW", 810), appearance(MATCH, "Full", "f", "FW", 90),
        ]
        events = pd.DataFrame([{"MatchURL": OTHER_MATCH, "Team": "Getafe", "Event_Type": "Goal", "Event_Players": "Full"}])
        out_of_pool, into_pool = script.worst_case_flips(pd.DataFrame(rows), events)
        self.assertEqual(out_of_pool, [("ESP", 2024, "o")])
        self.assertEqual(into_pool, [("ESP", 2024, "i")])

if __name__ == "__main__":
    unittest.main()
