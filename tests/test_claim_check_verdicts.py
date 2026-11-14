"""Claim Check Seam 1 (#43): an Extraction in, a pooled player Verdict out, as a record, a Verdict JSON and printed lines.

Synthetic tests build hand-made PlayerSeasons and PlayerMatches here, labelled `synthetic`, and kept out of tests/fixtures/.
The real-data test runs the CLI on tests/fixtures/standin/loader_sample/, loaded as tests/test_claim_check_adapter.py loads it.
Word map v1 is a DRAFT: these tests use it as input only, and check that every Verdict says so.
Run from the repo root: python3 -m unittest discover tests
"""
import ast
import contextlib
import dataclasses
import io
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from claim_check.domain import verdicts
from claim_check.domain.records import PlayerMatch
from claim_check.domain.verdicts import check
from claim_check.interface import cli
from twin.domain.records import PlayerSeason, Shot
from claim_check.domain.word_map import TOP_25, Reading

DOMAIN = ROOT / "claim_check" / "domain"
CLAIM = "X is an elite finisher"
LEAGUES = ("ENG", "ESP", "GER", "ITA", "FRA")
INSIDE, OUTSIDE = (0.9, 0.5), (0.6, 0.5)  # Understat x, y: inside the box, and outside it


def extraction(name="Subject", words=("elite", "finisher"), polarity="affirmed", tense="present", seasons_named=None, reference_named=None, kind="player"):
    return {"form": "absolute", "subjects": [{"name": name, "kind": kind}], "claim_words": list(words), "comparison_words": None,
            "polarity": polarity, "tense": tense, "seasons_named": seasons_named, "reference_named": reference_named}


def shots(player_id, league, season, goals, total, xg=0.1, place=INSIDE):
    return tuple(Shot(player_id, league, season, place[0], place[1], xg, "OpenPlay", "RightFoot", None, "Goal" if i < goals else "MissedShots") for i in range(total))


class World:
    """synthetic: hand-made PlayerSeasons, one PlayerMatch per PlayerSeason carrying its minutes and shots."""

    def __init__(self):
        self.seasons, self.matches = [], []

    def add(self, player_id, name, goals, total, league="ENG", season=2022, minutes=2000, position="FW", held=False, xg=0.1, place=INSIDE, extra=()):
        self.seasons.append(PlayerSeason(player_id, name, league, season, ("Club",), minutes, minutes, 0, "FW", None, None, None, None, None, held))
        self.matches.append(PlayerMatch(player_id, league, season, f"{player_id}-{season}", "Club", minutes, position, False, shots(player_id, league, season, goals, total, xg, place) + extra))
        return self

    def peers(self, count=30, season=2022):
        # Peer k scores k of 50 shots at 0.1 xG each: Finishing (k - 5) / 50, from -0.10 to +0.48, across all 5 leagues.
        for k in range(count):
            self.add(f"peer{k}", f"Peer Number{k}", k, 50, league=LEAGUES[k % 5], season=season)
        return self

    def check(self, raw=None, claim=CLAIM):
        return check(claim, extraction() if raw is None else raw, tuple(self.seasons), tuple(self.matches))


def reading(verdict):
    (found,) = verdict.readings
    return found


class Boundary(unittest.TestCase):
    def test_domain_imports_no_framework_llm_tracer_pandas_or_outer_layer(self):
        # As Twin's tests/test_domain_boundary.py does: no pandas, and no infrastructure, application or interface module.
        files = sorted(DOMAIN.rglob("*.py"))
        self.assertTrue(files)
        for path in files:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf8"))):
                modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                for module in modules:
                    self.assertNotIn(module.split(".")[0], {"pandas", "pyarrow", "langgraph", "langchain", "groq", "langfuse", "requests", "httpx"}, path)
                    for layer in ("infrastructure", "application", "interface"):
                        self.assertNotIn(layer, module, path)


class VerdictRule(unittest.TestCase):
    def test_synthetic_meets(self):
        # synthetic: 50 of 50 shots scored, above every peer, with no spread to resample.
        found = reading(World().peers().add("s", "Subject", 50, 50).check())
        self.assertEqual((found.claim_type, found.verdict, found.test.outcome), ("Finishing", "Supported", "meets"))
        self.assertEqual(found.test.interval, (found.test.percentile, found.test.percentile))
        self.assertGreaterEqual(found.test.interval[0], 90)

    def test_synthetic_misses(self):
        # synthetic: 0 of 50 scored, level with the lowest peer.
        found = reading(World().peers().add("s", "Subject", 0, 50).check())
        self.assertEqual((found.verdict, found.test.outcome), ("Not supported", "misses"))
        self.assertLess(found.test.interval[1], 90)

    def test_synthetic_borderline_is_mixed_and_says_why(self):
        # synthetic: 27 of 50 puts the point at the 90th percentile, and resampling the shots spreads it both ways.
        found = reading(World().peers().add("s", "Subject", 27, 50).check())
        self.assertEqual((found.verdict, found.test.outcome, found.reason), ("Mixed", "borderline", "the range crosses the line"))
        low, high = found.test.interval
        self.assertTrue(low < 90 <= high, found.test)

    def test_synthetic_negation_swaps_supported_and_not_supported_only(self):
        # synthetic: the three worlds above, negated.
        for goals, affirmed, negated in ((50, "Supported", "Not supported"), (0, "Not supported", "Supported"), (27, "Mixed", "Mixed")):
            world = World().peers().add("s", "Subject", goals, 50)
            self.assertEqual(reading(world.check()).verdict, affirmed)
            self.assertEqual(reading(world.check(extraction(polarity="negated"))).verdict, negated, goals)

    def test_synthetic_less_direction_word_counts_from_the_lowest_value(self):
        # synthetic: "wasteful" is Finishing, less (word map v1-draft): 0 of 50 is the most wasteful, so it meets.
        found = reading(World().peers().add("s", "Subject", 0, 50).check(extraction(words=["wasteful"])))
        self.assertEqual(found.verdict, "Supported")
        self.assertIn("counted from the lowest", found.threshold)


class Bootstrap(unittest.TestCase):
    def test_synthetic_1000_shot_resamples_fixed_seed_80_percent_interval_same_input_same_output(self):
        world = World().peers().add("s", "Subject", 27, 50)
        first, second = world.check(), world.check()
        self.assertEqual(dataclasses.asdict(first), dataclasses.asdict(second))
        self.assertEqual((verdicts.RESAMPLES, verdicts.INTERVAL), (1000, 80))
        self.assertIsInstance(verdicts.SEED, int)
        for words in ("1,000 resamples", f"seed {verdicts.SEED}", "80% interval", "shots"):
            self.assertIn(words, first.method)
        low, high = reading(first).test.interval
        self.assertLess(low, high)  # a real spread comes from resampling the shots


class ReferenceGroup(unittest.TestCase):
    def excluded(self, world):
        # synthetic: one of each player Q7 and D1-D2 leave out, each better than the Subject so it would matter.
        world.add("wide", "Wide Player", 50, 50, position="RW")  # another Line
        world.add("short", "Short Minutes", 50, 50, minutes=899)  # under 900 minutes
        world.add("held", "Held Peer", 50, 50, held=True)  # held for review
        world.add("few", "Few Shots", verdicts.SHOT_MINIMUM - 1, verdicts.SHOT_MINIMUM - 1, xg=0.01)  # under the shot minimum
        world.add("old", "Old Season", 50, 50, season=2017)  # outside the Window
        return world

    def test_synthetic_all_5_leagues_same_line_900_minutes_held_and_shot_minimum(self):
        found = reading(self.excluded(World().peers()).add("s", "Subject", 27, 50).check())
        self.assertEqual(found.reference_size, 30)
        self.assertEqual(found.verdict, "Mixed")
        self.assertEqual(found.reference_group, "vs forwards in the top 5 leagues, 2021/22-2023/24, 900+ minutes per season, 40+ non-penalty shots: 30 players")

    def test_synthetic_30_peer_minimum(self):
        found = reading(self.excluded(World().peers(29)).add("s", "Subject", 27, 50).check())
        self.assertEqual((found.verdict, found.reason), ("Can't check with this data", "peer group too small"))

    def test_shot_minimum_is_one_constant_of_40(self):
        self.assertEqual(verdicts.SHOT_MINIMUM, 40)  # proposed in the spec's measurement; Ahmed's freeze ticket may change it

    def test_synthetic_subject_line_is_its_most_minutes_and_a_named_line_replaces_it(self):
        world = World().peers()
        for k in range(30):
            world.add(f"mid{k}", f"Mid Number{k}", 50, 50, position="CM", league=LEAGUES[k % 5])
        world.add("s", "Subject", 27, 50, minutes=1500).add("s", "Subject", 0, 0, season=2021, minutes=1000, position="CM")
        found = reading(world.check())
        self.assertTrue(found.reference_group.startswith("vs forwards"), found.reference_group)  # 1,500 FW minutes beat 1,000 CM
        named = reading(world.check(extraction(reference_named="for a midfielder")))
        self.assertTrue(named.reference_group.startswith("vs central midfielders"), named.reference_group)
        self.assertEqual(named.verdict, "Not supported")  # every midfielder scored 50 of 50

    def test_synthetic_named_league_keeps_that_league_only(self):
        found = reading(World().peers(150).add("s", "Subject", 27, 50).check(extraction(reference_named="in the Premier League")))
        self.assertEqual(found.reference_size, 30)
        self.assertIn("in the Premier League", found.reference_group)


class Coverage(unittest.TestCase):
    def test_synthetic_skipped_seasons_are_listed_and_thin_evidence_is_shown(self):
        world = World().peers().add("s", "Subject", 27, 50).add("s", "Subject", 50, 50, season=2023, held=True)
        found = reading(world.check())
        self.assertEqual(found.coverage, "Based on 1 of 3 seasons: 2021/22 too few minutes, 2023/24 held for review.")
        self.assertTrue(found.thin)
        self.assertEqual(found.test.shots, 50)  # the held season's 50 goals are never used
        self.assertEqual(found.seasons, "2021/22-2023/24")

    def test_synthetic_a_fully_used_one_season_window_is_never_thin(self):
        found = reading(World().peers().add("s", "Subject", 27, 50).check(extraction(seasons_named="in 2022/23")))
        self.assertEqual((found.coverage, found.thin, found.seasons), ("Based on 1 of 1 season.", False, "2022/23"))

    def test_synthetic_past_tense_is_every_season_and_a_named_range_is_cut_to_the_data(self):
        world = World().peers().add("s", "Subject", 27, 50)
        self.assertEqual(reading(world.check(extraction(tense="past"))).seasons, "2017/18-2023/24")
        self.assertEqual(reading(world.check(extraction(seasons_named="from 2016/17 to 2022/23"))).seasons, "2017/18-2022/23")


class CantCheck(unittest.TestCase):
    """synthetic: one Extraction per reason #43 covers, each against the same world."""

    def setUp(self):
        self.world = World().peers().add("s", "Subject", 27, 50).add("s2", "Alex Twin", 27, 50).add("s3", "Bruno Twin", 27, 50)

    def assert_reason(self, raw, reason):
        verdict = self.world.check(raw)
        found = reading(verdict)
        self.assertEqual((found.verdict, found.reason), ("Can't check with this data", reason))
        self.assertEqual(verdict.draft, "word map: DRAFT, not frozen")
        return found

    def test_synthetic_could_not_read_the_claim(self):
        for raw in ({**extraction(), "polarity": "maybe"}, {"subjects": []}, {**extraction(), "claim_words": []}, {**extraction(), "seasons_named": "last year"}):
            self.assert_reason(raw, "could not read the claim")

    def test_synthetic_subject_type_not_covered(self):
        self.assert_reason(extraction(kind="manager"), "subject type not covered")
        self.assert_reason(extraction(kind="match"), "subject type not covered")

    def test_synthetic_subject_not_in_data(self):
        self.assert_reason(extraction(name="Nobody"), "subject not in data")

    def test_synthetic_subject_is_ambiguous_lists_the_matches(self):
        found = self.assert_reason(extraction(name="Twin"), "subject is ambiguous")
        self.assertIn("Alex Twin", found.detail)
        self.assertIn("Bruno Twin", found.detail)

    def test_synthetic_claim_word_not_in_catalogue(self):
        for words in (["majestic", "finisher"], ["decent", "finisher"], ["elite"]):
            self.assert_reason(extraction(words=words), "claim word not in catalogue")

    def test_synthetic_peer_group_not_in_catalogue(self):
        self.assert_reason(extraction(reference_named="for a goalkeeper coach"), "peer group not in catalogue")

    def test_synthetic_metric_not_in_data(self):
        self.assert_reason(extraction(words=["pace"]), "metric not in data")

    def test_synthetic_season_not_in_data(self):
        self.assert_reason(extraction(seasons_named="in 2015/16"), "season not in data")

    def test_synthetic_too_few_minutes(self):
        self.assert_reason(extraction(tense="present", seasons_named="in 2023/24"), "too few minutes")

    def test_synthetic_held_for_review(self):
        self.world.add("h", "Held Subject", 27, 50, held=True)
        self.assert_reason(extraction(name="Held Subject"), "held for review")

    def test_synthetic_too_few_shots(self):
        self.world.add("f", "Few Subject", 20, verdicts.SHOT_MINIMUM - 1)
        self.assert_reason(extraction(name="Few Subject"), "too few shots")

    def test_synthetic_the_first_reason_in_check_order_wins(self):
        # Subject not in data (3) and a word not in the catalogue (4) and a season not in data (6): reason 3.
        self.assert_reason(extraction(name="Nobody", words=["majestic"], seasons_named="in 2015/16"), "subject not in data")

    def test_synthetic_a_claim_type_with_no_verdict_path_stops_with_an_error(self):
        # Every catalogue Claim type is built by #45, so this uses a made-up Reading: an error, never a wrong Verdict.
        reading = Reading("Not a claim type", "more", TOP_25, None)
        with self.assertRaises(NotImplementedError):
            verdicts.reading_verdict(reading, *[None] * 10)


class PooledClaimTypes(unittest.TestCase):
    def test_synthetic_finishing_from_distance_shot_quality_and_long_shots(self):
        world = World()
        for k in range(30):  # peer k: 50 shots inside the box at 0.1 xG, and k shots outside at 0.03 xG, none scored
            world.add(f"peer{k}", f"Peer Number{k}", 0, 50, league=LEAGUES[k % 5], extra=shots(f"peer{k}", LEAGUES[k % 5], 2022, 0, 40 + k, 0.03, OUTSIDE))
        world.add("s", "Subject", 0, 10, extra=shots("s", "ENG", 2022, 20, 80, 0.03, OUTSIDE))
        distance = reading(world.check(extraction(words=["scores from distance"])))
        self.assertEqual((distance.claim_type, distance.verdict, distance.test.shots), ("Finishing from distance", "Supported", 80))
        self.assertIn("from outside the box", distance.reference_group)
        quality = reading(world.check(extraction(words=["gets into great positions"])))
        self.assertEqual((quality.claim_type, quality.verdict), ("Shot quality", "Not supported"))  # 0.038 npxG per shot, the lowest
        long_shots = reading(world.check(extraction(words=["long shots"])))
        self.assertEqual((long_shots.claim_type, long_shots.verdict), ("Long shots", "Supported"))  # 80 of 90 from outside


class Rendered(unittest.TestCase):
    def test_synthetic_printed_verdict_shows_every_fact(self):
        verdict = World().peers().add("s", "Subject", 27, 50).check()
        text = cli.render(verdict)
        found = reading(verdict)
        for fact in ("Finishing: Mixed", "Elite = top 10% of the peer group", f"Subject: {found.test.percentile:.0f}", "range",
                     found.reference_group, "Seasons: 2021/22-2023/24 · Data to 2023/24",
                     "Our data ends in 2023/24. This verdict may not match the current season.",
                     "word map v1-draft", "word map: DRAFT, not frozen", "level scale v1-draft", verdict.method, found.coverage, "the range crosses the line"):
            self.assertIn(fact, text)
        past = cli.render(World().peers().add("s", "Subject", 27, 50).check(extraction(tense="past")))
        self.assertNotIn("Our data ends", past)  # the warning is for present-tense Verdicts only

    def test_synthetic_every_verdict_is_marked_draft_word_map(self):
        world = World().peers().add("s", "Subject", 27, 50)
        for raw in (extraction(), extraction(name="Nobody"), {"bad": 1}):
            verdict = world.check(raw)
            self.assertEqual((verdict.word_map, verdict.draft), ("v1-draft", "word map: DRAFT, not frozen"))
            self.assertIn("word map: DRAFT, not frozen", cli.render(verdict))


class SampleCli(unittest.TestCase):
    def test_extraction_json_in_verdict_json_out_on_loader_sample(self):
        from tests.test_claim_check_adapter import sample_files
        with TemporaryDirectory() as folder:
            standin = Path(folder) / "standin"
            standin.mkdir()
            sample_files(standin)
            name = "Aaron Mooy"  # in loader_sample: 3,067 season minutes, but the sample holds few of his matches
            source = Path(folder) / "mooy.json"
            source.write_text(json.dumps({"claim": "Mooy is an elite finisher", "extraction": extraction(name=name)}), encoding="utf8")
            out = Path(folder) / "out"
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                cli.main([str(source), "--standin", str(standin), "--out", str(out), "--no-season-checks"])
            (written,) = out.glob("*.json")
            saved = json.loads(written.read_text(encoding="utf8"))
            self.assertEqual(saved["claim"], "Mooy is an elite finisher")
            self.assertEqual(saved["draft"], "word map: DRAFT, not frozen")
            self.assertEqual(saved["readings"][0]["verdict"], "Can't check with this data")
            self.assertIn("Mooy is an elite finisher", printed.getvalue())
            self.assertIn(saved["readings"][0]["reason"], printed.getvalue())
            self.assertIn("not linked to Understat", printed.getvalue())

    def test_default_output_is_build_private_claim_check(self):
        self.assertEqual(cli.OUT, ROOT / "build" / "private" / "claim_check")


if __name__ == "__main__":
    unittest.main()
