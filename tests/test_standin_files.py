"""Wrong files (spec, "What counts as a wrong file"): each one fails the stand-in run with StandinFileError, never missing data.

Each input is a copy of tests/fixtures/standin/loader_sample/ broken at test time, so every test here is `synthetic`, with
0 real cases. The run goes through loader.load_standin, so each read in the loader is the one under test.
Run from the repo root: python3 -m unittest discover tests
"""
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from twin.infrastructure.standin import loader  # noqa: E402
from twin.infrastructure.standin.files import StandinFileError, StandinFiles  # noqa: E402

SAMPLE = ROOT / "tests" / "fixtures" / "standin" / "loader_sample"
TRIM_WAY_BACK = "scripts/trim_standin.py"
GIT_WAY_BACK = "git"


def remove(path):
    path.unlink()


def empty(path):
    path.write_bytes(b"")


def zero_rows(path):
    pd.read_parquet(path).iloc[:0].to_parquet(path)


def corrupt(path):
    path.write_bytes(b"not a parquet file")


def without_event_type(path):
    pd.read_parquet(path).drop(columns=["Event_Type"]).to_parquet(path)


def one_row_less(path):
    pd.read_parquet(path).iloc[:-1].to_parquet(path)


def without_reviewer(path):
    path.write_text("item_type,key,decision,fbref_id,date,reason\n", encoding="utf8")


# Test name to (file broken, how, words in the reason, the way back).
CASES = {
    "missing_file": ("epl_shot_data.parquet", remove, "missing", TRIM_WAY_BACK),
    "zero_byte_file": ("club_map.csv", empty, "0 bytes", TRIM_WAY_BACK),
    "zero_row_parquet": ("ENG_M_1st_positions.parquet", zero_rows, "0 rows", TRIM_WAY_BACK),
    "corrupt_parquet": ("understat_xg_data.parquet", corrupt, "cannot be read", TRIM_WAY_BACK),
    "missing_column": ("ITA_M_1st_match_summary.parquet", without_event_type, "Event_Type", TRIM_WAY_BACK),
    "hash_differs_from_manifest": ("GER_M_1st_positions.parquet", one_row_less, "SHA-256", TRIM_WAY_BACK),
    "missing_manifest": ("MANIFEST.md", remove, "MANIFEST.md", TRIM_WAY_BACK),
    "missing_review_decisions": ("review_decisions.csv", remove, "missing", GIT_WAY_BACK),
    "zero_byte_review_decisions": ("review_decisions.csv", empty, "0 bytes", GIT_WAY_BACK),
    "review_decisions_missing_column": ("review_decisions.csv", without_reviewer, "reviewer", "by hand"),
}


def broken_run(case):
    """The loader on a copy of loader_sample/ with one file broken. Returns the error, or None if the run passed."""
    name, breaks, _, _ = CASES[case]
    with TemporaryDirectory() as folder:
        for path in SAMPLE.iterdir():
            shutil.copy(path, folder)
        breaks(Path(folder) / name)
        try:
            loader.load_standin(StandinFiles(Path(folder)), season_checks=False)
        except StandinFileError as error:
            return error
    return None


class WrongFiles(unittest.TestCase):
    def assert_fails(self, case):
        name, _, reason, way_back = CASES[case]
        error = broken_run(case)
        self.assertIsNotNone(error, f"{case}: the run passed")
        self.assertEqual(error.path.name, name)
        self.assertIn(reason, error.reason)
        self.assertIn(way_back, error.way_back)

    def test_synthetic_missing_file_fails(self):
        self.assert_fails("missing_file")

    def test_synthetic_zero_byte_file_fails(self):
        self.assert_fails("zero_byte_file")

    def test_synthetic_zero_row_parquet_fails(self):
        self.assert_fails("zero_row_parquet")

    def test_synthetic_corrupt_parquet_fails(self):
        self.assert_fails("corrupt_parquet")

    def test_synthetic_missing_column_fails(self):
        self.assert_fails("missing_column")

    def test_synthetic_hash_differs_from_manifest_fails(self):
        self.assert_fails("hash_differs_from_manifest")

    def test_synthetic_missing_manifest_fails(self):
        self.assert_fails("missing_manifest")

    def test_synthetic_missing_review_decisions_fails(self):
        self.assert_fails("missing_review_decisions")

    def test_synthetic_zero_byte_review_decisions_fails(self):
        self.assert_fails("zero_byte_review_decisions")

    def test_synthetic_review_decisions_missing_column_fails(self):
        # The trim cannot rebuild Ahmed's file, so its way back is restoring the column.
        self.assert_fails("review_decisions_missing_column")
        self.assertNotIn(f"run {TRIM_WAY_BACK}", broken_run("review_decisions_missing_column").way_back)

    def test_synthetic_header_only_review_decisions_is_valid(self):
        with TemporaryDirectory() as folder:
            for path in SAMPLE.iterdir():
                shutil.copy(path, folder)
            (Path(folder) / "review_decisions.csv").write_text("item_type,key,decision,fbref_id,reviewer,date,reason\n", encoding="utf8")
            loaded = loader.load_standin(StandinFiles(Path(folder)), season_checks=False).loaded
        self.assertTrue(loaded.player_seasons)

    def test_synthetic_failure_names_the_file_and_the_way_back(self):
        for case, (name, _, _, way_back) in CASES.items():
            with self.subTest(case):
                error = broken_run(case)
                message = str(error)
                self.assertIn(name, message)
                self.assertIn(f"Way back: {error.way_back}", message)
                self.assertIn(way_back, message)


if __name__ == "__main__":
    unittest.main()
