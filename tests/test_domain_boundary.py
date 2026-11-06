"""The domain layer: its boundary, the publishing guard on LoadedSource, and the Pool rule's synthetic tie.

Run from the repo root: python3 -m unittest discover tests
"""
import ast
import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.domain.pool import in_pool, is_pool_candidate
from twin.domain.records import LoadedSource, PlayerSeason

DOMAIN = ROOT / "twin" / "domain"


def hand_player_season(minutes=900, attacking_minutes=500, other_minutes=400, held_for_review=False):
    """A hand-made PlayerSeason. Only synthetic tests use it."""
    return PlayerSeason("p1", "Kike", "ESP", 2021, ("A",), minutes, attacking_minutes, other_minutes, "FW", 1.0, 10, 2.0, 5, 3, held_for_review)


class DomainBoundary(unittest.TestCase):
    def test_domain_imports_no_pandas_pyarrow_infrastructure_or_fbref(self):
        files = sorted(DOMAIN.rglob("*.py"))
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding="utf8")
            self.assertNotIn("fbref", text.lower(), path)
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                else:
                    continue
                for module in modules:
                    self.assertNotIn(module.split(".")[0], {"pandas", "pyarrow"}, path)
                    self.assertNotIn("infrastructure", module, path)


class PublishingGuard(unittest.TestCase):
    def test_synthetic_loaded_source_refuses_may_publish_on_any_other_source(self):
        # synthetic: 0 real. No source but `understat` may publish (spec, "The publishing guard").
        with self.assertRaises(ValueError) as refused:
            LoadedSource((), (), "standin", may_publish=True)
        self.assertIn("standin", str(refused.exception))
        closed = LoadedSource((), (), "standin")
        self.assertFalse(closed.may_publish)
        with self.assertRaises(ValueError):
            dataclasses.replace(closed, may_publish=True)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            closed.may_publish = True
        self.assertTrue(LoadedSource((), (), "understat", may_publish=True).may_publish)


class PoolRule(unittest.TestCase):
    def test_synthetic_pool_equal_attacking_and_other_stays_out(self):
        # synthetic: 0 real at 900+ minutes (D24). Plan line 120: a tie stays out.
        self.assertFalse(is_pool_candidate(900, 450, 450))
        self.assertFalse(in_pool(hand_player_season(attacking_minutes=450, other_minutes=450)))
        self.assertTrue(in_pool(hand_player_season(attacking_minutes=451, other_minutes=449)))


if __name__ == "__main__":
    unittest.main()
