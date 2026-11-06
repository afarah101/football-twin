"""The one place the stand-in reads files (spec, "What counts as a wrong file").

A missing, empty, unreadable or changed file raises StandinFileError with the file, the reason and the way back. It is
never read as missing data.
"""
import csv
import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[3] / "data" / "standin"
TRIM_WAY_BACK = "git checkout the file, or run scripts/trim_standin.py, which rewrites MANIFEST.md"
DECISIONS_WAY_BACK = "restore it from git"
DECISIONS_COLUMN_WAY_BACK = "restore the column by hand or from git. scripts/trim_standin.py cannot rebuild this file"
DECISION_COLUMNS = ["item_type", "key", "decision", "fbref_id", "reviewer", "date", "reason"]
# A trimmed file's row in MANIFEST.md: | source | source SHA-256 | `trimmed file` | `trimmed SHA-256` | ...
MANIFEST_ROW = re.compile(r"^\|[^|]*\|[^|]*\| `([^`]+)` \| `([0-9a-f]{64})` \|", re.MULTILINE)
MANIFEST_CLUB_MAP = re.compile(r"^`(club_map\.csv)`, SHA-256 `([0-9a-f]{64})`", re.MULTILINE)


class StandinFileError(SystemExit):
    """A wrong stand-in file. A SystemExit, like every other stop in the stand-in run, so a script exits with the message."""

    def __init__(self, path, reason, way_back=TRIM_WAY_BACK):
        super().__init__(f"{path}: {reason}. Way back: {way_back}")
        self.path, self.reason, self.way_back = Path(path), reason, way_back


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_hashes(folder):
    path = folder / "MANIFEST.md"
    if not path.is_file():
        raise StandinFileError(path, "the folder has no MANIFEST.md, so its files cannot be checked")
    text = path.read_text(encoding="utf8")
    return dict(MANIFEST_ROW.findall(text) + MANIFEST_CLUB_MAP.findall(text))


def check_present(path, way_back=TRIM_WAY_BACK):
    if not path.is_file():
        raise StandinFileError(path, "the file is missing", way_back)
    if path.stat().st_size == 0:
        raise StandinFileError(path, "the file has 0 bytes", way_back)


def check_columns(path, found, needed, way_back=TRIM_WAY_BACK):
    missing = [column for column in needed if column not in found]
    if missing:
        raise StandinFileError(path, f"missing column(s) {missing}", way_back)


def csv_text_rows(text):
    """Rows of a CSV file's text, such as a committed file read from git."""
    return list(csv.DictReader(io.StringIO(text)))


def read_review_decision_rows(path):
    """Ahmed's hand-edited file. A header-only file is valid and means no decisions. It is not in MANIFEST.md, because it is not trimmed."""
    check_present(path, DECISIONS_WAY_BACK)
    # utf-8-sig: spreadsheets save this hand-edited file with a byte order mark.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    check_columns(path, reader.fieldnames or [], DECISION_COLUMNS, DECISIONS_COLUMN_WAY_BACK)
    return rows


@dataclass(frozen=True)
class StandinFiles:
    """Where the stand-in files are. The tests point it at the real samples, whose names carry a prefix."""
    folder: Path = DATA
    prefix: str = ""

    def path(self, name):
        return self.folder / f"{self.prefix}{name}"

    def check_hash(self, name):
        """The file's SHA-256 against MANIFEST.md. Prefixed samples share one folder with no manifest of their own, so only a whole folder is checked."""
        if self.prefix:
            return
        path = self.path(name)
        expected = manifest_hashes(self.folder).get(name)
        if expected is None:
            raise StandinFileError(path, "the file is not listed in MANIFEST.md")
        if sha256_of(path) != expected:
            raise StandinFileError(path, "its SHA-256 differs from MANIFEST.md")

    def parquet(self, name, columns=None):
        path = self.path(name)
        check_present(path)
        try:
            rows = pd.read_parquet(path)
        except Exception as error:
            raise StandinFileError(path, f"the file cannot be read ({type(error).__name__}: {error})") from error
        if rows.empty:
            raise StandinFileError(path, "the Parquet file has 0 rows")
        if columns is not None:
            check_columns(path, rows.columns, columns)
            rows = rows[columns]
        self.check_hash(name)
        return rows

    def csv(self, name, columns):
        path = self.path(name)
        check_present(path)
        try:
            rows = pd.read_csv(path, keep_default_na=False)
        except Exception as error:
            raise StandinFileError(path, f"the file cannot be read ({type(error).__name__}: {error})") from error
        check_columns(path, rows.columns, columns)
        self.check_hash(name)
        return rows
