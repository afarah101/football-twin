"""Claim Check's stand-in adapter (#42, ADR 0002): PlayerMatch and TeamMatch records from Twin's stand-in join, and the two pins.

Unit tests run on tests/fixtures/standin/loader_sample/, loaded as tests/test_standin_loader.py loads it: a copy with a
header-only review_decisions.csv, season checks off, because the sample is cut as whole matches. The two pins also run on
the full data/standin/, skipped where that private folder is absent.
Run from the repo root: python3 -m unittest discover tests
"""
import ast
import dataclasses
import math
import os
import shutil
import subprocess
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from claim_check.domain.records import LINE_OF_POSITION, SET_PIECE_SITUATIONS, PlayerMatch, TeamMatch
from claim_check.infrastructure import standin_adapter as adapter
from twin.domain.pool import in_pool
from twin.infrastructure.standin import player_join as join

SAMPLE = ROOT / "tests" / "fixtures" / "standin" / "loader_sample"
FULL = ROOT / "data" / "standin"
HEADER = "item_type,key,decision,fbref_id,reviewer,date,reason\n"
JOINED_SHOTS = 315_073  # the #6 spec's pinned number
POOL_LINES = ["Merges off: joined 315073 | Pool 3108 of 3136", "Merges on: joined 315073 | Pool 3109 of 3137"]
DOMAIN = ROOT / "claim_check" / "domain"
BANNED_IN_DOMAIN = {"pandas", "numpy", "langgraph", "langchain", "groq", "langfuse", "requests", "httpx", "urllib", "socket", "pyarrow"}


def sample_files(folder):
    for path in SAMPLE.iterdir():
        if path.name != "review_decisions.csv":
            shutil.copy(path, folder)
    (Path(folder) / "review_decisions.csv").write_text(HEADER, encoding="utf8")
    return join.StandinFiles(Path(folder))


class SampleRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = TemporaryDirectory()
        cls.files = sample_files(cls.folder.name)
        cls.matches = adapter.load_matches(cls.files, season_checks=False)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()


class Layers(unittest.TestCase):
    def test_domain_imports_no_pandas_framework_or_network(self):
        for path in DOMAIN.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf8"))
            names = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
            self.assertFalse(names & BANNED_IN_DOMAIN, f"{path.name} imports {sorted(names & BANNED_IN_DOMAIN)}")

    def test_records_are_plain_frozen_dataclasses(self):
        for record in (PlayerMatch, TeamMatch):
            self.assertTrue(dataclasses.is_dataclass(record))
            self.assertTrue(record.__dataclass_params__.frozen)

    def test_line_table_is_q7(self):
        self.assertEqual(LINE_OF_POSITION, {
            "FW": "Forward", "LW": "Wide", "RW": "Wide", "LM": "Wide", "RM": "Wide", "AM": "Central AM",
            "CM": "Central midfielder", "DM": "Central midfielder", "MF": "Central midfielder",
            "LB": "Full-back", "RB": "Full-back", "WB": "Full-back", "CB": "Centre-back", "DF": "Centre-back", "GK": "Goalkeeper",
        })
        self.assertEqual(SET_PIECE_SITUATIONS, ("FromCorner", "SetPiece", "DirectFreekick"))


class PlayerMatches(SampleRun):
    def test_one_player_match_per_appearance(self):
        keys = [found.key for found in self.matches.player_matches]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), len(self.matches.positions))

    def test_line_comes_from_the_first_listed_position_and_a_substitute_has_none(self):
        substitutes = [found for found in self.matches.player_matches if found.substitute]
        starts = [found for found in self.matches.player_matches if not found.substitute]
        self.assertTrue(substitutes and starts)  # the sample holds both, so both branches are real cases
        for found in starts:
            self.assertEqual(found.line, LINE_OF_POSITION[found.position])
        for found in substitutes:
            self.assertIsNone(found.line)
        self.assertTrue(any(found.minutes > 0 for found in substitutes))

    def test_substitute_minutes_count_for_minutes_but_not_for_position(self):
        # Twin's own rule decides who came on: its start minutes (attacking + other) per PlayerSeason must equal ours.
        totals = join.position_minutes(self.matches.positions, join.read_events(self.files))
        starts, everything = Counter(), Counter()
        for found in self.matches.player_matches:
            key = (found.league, found.season + 1, found.player_id)
            everything[key] += found.minutes
            if not found.substitute:
                starts[key] += found.minutes
        for key, total, attacking, other in zip(totals.index, totals["total"], totals["attacking"], totals["other"]):
            self.assertEqual(everything[key], int(total), key)
            self.assertEqual(starts[key], int(attacking + other), key)

    def test_each_shot_sits_on_its_player_match(self):
        shots_on_records = Counter(shot for found in self.matches.player_matches for shot in found.shots)
        self.assertEqual(shots_on_records, Counter(self.matches.loaded.shots))
        for found in self.matches.player_matches:
            for shot in found.shots:
                self.assertEqual((shot.player_id, shot.league, shot.season), (found.player_id, found.league, found.season))


class TeamMatches(SampleRun):
    def plain_sums(self):
        """Raw shot rows summed in plain Python per (FBref match, side), over matches Twin's rule 2 links."""
        positions = self.matches.positions
        clubs = join.understat_to_fbref_clubs(self.files)
        shots = join.load_shots(self.files)
        links = join.link_matches(shots, positions, clubs).links
        sums = defaultdict(lambda: [0.0, 0.0, 0])
        for league, match_id, side, xg, situation, result in zip(shots["league"], shots["match_id"], shots["side"], shots["xG"], shots["situation"], shots["result"]):
            match = links.get((league, match_id))
            if match is None or situation == "Penalty" or result == "OwnGoal":
                continue
            found = sums[(match, side)]
            found[0] += float(xg)
            found[1] += float(xg) if situation in ("FromCorner", "SetPiece", "DirectFreekick") else 0.0
            found[2] += 1
        return set(links.values()), sums

    def test_two_team_matches_per_linked_match_and_they_mirror(self):
        matches, _ = self.plain_sums()
        by_match = defaultdict(list)
        for found in self.matches.team_matches:
            by_match[found.match].append(found)
        self.assertEqual(set(by_match), matches)
        for match, pair in by_match.items():
            self.assertEqual(len(pair), 2, match)
            first, second = pair
            self.assertEqual((first.team, first.opponent), (second.opponent, second.team))
            self.assertEqual((first.npxg_for, first.set_piece_xg_for, first.shots_for), (second.npxg_against, second.set_piece_xg_against, second.shots_against))

    def test_team_sums_equal_a_plain_python_sum_of_the_shot_rows(self):
        _, sums = self.plain_sums()
        home = self.matches.positions.drop_duplicates("match").set_index("match")["Home_Team"].to_dict()
        for found in self.matches.team_matches:
            own = sums[(found.match, "h" if found.team == home[found.match] else "a")]
            other = sums[(found.match, "a" if found.team == home[found.match] else "h")]
            self.assertTrue(math.isclose(found.npxg_for, own[0], abs_tol=1e-9), found)
            self.assertTrue(math.isclose(found.set_piece_xg_for, own[1], abs_tol=1e-9), found)
            self.assertEqual(found.shots_for, own[2], found)
            self.assertTrue(math.isclose(found.npxg_against, other[0], abs_tol=1e-9), found)
            self.assertTrue(math.isclose(found.set_piece_xg_against, other[1], abs_tol=1e-9), found)
            self.assertEqual(found.shots_against, other[2], found)
        self.assertTrue(any(found.set_piece_xg_for > 0 for found in self.matches.team_matches))  # the set-piece branch has real cases

    def test_team_names_are_fbref_clubs_of_the_match(self):
        teams = self.matches.positions.drop_duplicates("match").set_index("match")[["Home_Team", "Away_Team"]]
        for found in self.matches.team_matches:
            self.assertIn(found.team, set(teams.loc[found.match]))


class Pins(SampleRun):
    def test_pins_pass_on_the_sample(self):
        adapter.check_pins(self.matches.loaded, self.matches.player_matches)  # load_matches ran them too: this states it

    def test_synthetic_a_lost_shot_fails_pin_1_as_a_fault(self):
        # synthetic: the real records with one shot removed, since the real run never loses one.
        records = list(self.matches.player_matches)
        index = next(i for i, found in enumerate(records) if found.shots)
        records[index] = dataclasses.replace(records[index], shots=records[index].shots[1:])
        with self.assertRaises(adapter.PinFailed) as stop:
            adapter.check_pins(self.matches.loaded, records)
        self.assertIn("pin 1", str(stop.exception))
        self.assertIsInstance(stop.exception, SystemExit)  # a Fault stops the run, like every other stand-in stop

    def test_synthetic_lost_minutes_fail_pin_2_as_a_fault(self):
        # synthetic: one Pool PlayerSeason's appearance loses a minute.
        pool = {found.key for found in self.matches.loaded.player_seasons if in_pool(found)}
        records = list(self.matches.player_matches)
        index = next(i for i, found in enumerate(records) if (found.league, found.season, found.player_id) in pool and found.minutes)
        records[index] = dataclasses.replace(records[index], minutes=records[index].minutes - 1)
        with self.assertRaises(adapter.PinFailed) as stop:
            adapter.check_pins(self.matches.loaded, records)
        self.assertIn("pin 2", str(stop.exception))


@unittest.skipUnless((FULL / "MANIFEST.md").is_file(), "data/standin/ is private and absent here")
class FullDataPins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matches = adapter.load_matches()

    def test_pin_1_joined_shots(self):
        self.assertEqual(sum(len(found.shots) for found in self.matches.player_matches), JOINED_SHOTS)
        self.assertEqual(len(self.matches.loaded.shots), JOINED_SHOTS)

    def test_pin_1_measure_rule3_still_prints_both_pool_lines(self):
        # The #6 number check: the script rewrites name_map.csv and its sample with the same rows, as every number check does.
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "measure_rule3.py")], cwd=ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        printed = [line for line in done.stdout.splitlines() if line.startswith("Merges ")]
        self.assertEqual(printed, POOL_LINES)

    def test_pin_2_minutes_for_every_pool_player_season(self):
        minutes = Counter()
        for found in self.matches.player_matches:
            minutes[(found.league, found.season, found.player_id)] += found.minutes
        pool = [found for found in self.matches.loaded.player_seasons if in_pool(found)]
        self.assertTrue(pool)
        for found in pool:
            self.assertEqual(minutes[found.key], found.minutes, found.key)


if __name__ == "__main__":
    unittest.main()
