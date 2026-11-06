"""The fixtures in tests/fixtures/standin/ against the trimmed files in data/standin/ they are cut from (#18)."""
import hashlib
import unittest
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "standin"
FIXTURES = ROOT / "tests" / "fixtures" / "standin"
LOADER_SAMPLE = FIXTURES / "loader_sample"
LEAGUES = {"ENG": "epl", "ESP": "la_liga", "FRA": "ligue_1", "GER": "bundesliga", "ITA": "serie_a"}
# Every file the stand-in loader reads, under its data/standin/ name (spec "What counts as a wrong file").
LOADER_FILES = (
    {f"{league}_M_1st_positions.parquet" for league in LEAGUES}
    | {f"{league}_M_1st_match_summary.parquet" for league in LEAGUES}
    | {f"{stem}_shot_data.parquet" for stem in LEAGUES.values()}
    | {"understat_xg_data.parquet", "club_map.csv", "review_decisions.csv"}
)
# Ticket 3's real cases, as (league, Season_End_Year, FBref id): every row of each player-season is in the sample.
TICKET_3_PLAYER_SEASONS = (
    ("ENG", 2018, "2b622f01"), ("FRA", 2018, "2b622f01"),  # Lucas Moura's league move
    ("ESP", 2020, "2946f9a1"), ("ESP", 2020, "e29d1111"),  # Nacho, two players
    ("GER", 2023, "0cc5f4a5"), ("ENG", 2024, "57827369"), ("ENG", 2021, "96bb8cc2"),  # Nmecha, Brereton, Brady
    ("FRA", 2019, "923f4dda"), ("ENG", 2023, "df8b52a5"), ("ENG", 2018, "0db5d2c8"),  # Guirassy, Emerson, Mathias Jørgensen
    ("ENG", 2024, "4125cb98"), ("ENG", 2018, "2f90f6b8"), ("ESP", 2024, "0ae4e09a"),  # Quansah, a display label tie, Roger
    ("FRA", 2023, "45cce300"), ("ITA", 2022, "66784dee"), ("ITA", 2020, "48d5bd33"), ("GER", 2026, "185a2732"),  # Jeffinho, Johnsen, Malinovskyi, Puertas
)
# Whole FBref matches: the substitute match, a match with no events, and the 4 Pool-season rows with a null Min.
TICKET_3_FBREF_MATCHES = ("30d3212e", "05060e6f", "0e98ac46", "58f908b1", "eb75d1da", "bca64d25")
# Whole Understat matches: the own goal and penalty match.
TICKET_3_SHOT_MATCHES = (("la_liga", 7890),)


def fixture_files():
    return sorted(path for path in FIXTURES.rglob("*") if path.is_file() and path.suffix != ".md")


def data_name(path):
    """The data/standin/ file a fixture is cut from: the same name in loader_sample/, else the name after its `case__` prefix."""
    return path.name if path.parent == LOADER_SAMPLE else path.name.split("__", 1)[1]


@lru_cache(maxsize=None)
def data_frame(name):
    return pd.read_parquet(DATA / name)


def row_counts(frame):
    return Counter(map(tuple, frame.astype(str).itertuples(index=False, name=None)))


def sample(name):
    return pd.read_parquet(LOADER_SAMPLE / name)


def match_of(urls):
    return urls.str.extract(r"/matches/([0-9a-f]{8})/", expand=False)


class FixturesMatchTheTrimmedFiles(unittest.TestCase):
    def test_fixture_columns_match_trimmed_schema(self):
        parquets = [path for path in fixture_files() if path.suffix == ".parquet"]
        self.assertTrue(parquets)
        for path in parquets:
            with self.subTest(path.relative_to(FIXTURES)):
                fields = lambda schema: [(field.name, str(field.type)) for field in schema]
                self.assertEqual(fields(pq.read_schema(path)), fields(pq.read_schema(DATA / data_name(path))))

    def test_every_fixture_row_exists_in_data_standin(self):
        for path in fixture_files():
            with self.subTest(path.relative_to(FIXTURES)):
                if path.suffix == ".csv":
                    self.assertEqual(path.read_bytes(), (DATA / data_name(path)).read_bytes())
                    continue
                fixture, data = row_counts(pd.read_parquet(path)), row_counts(data_frame(data_name(path)))
                self.assertTrue(fixture)
                self.assertEqual([row for row, count in fixture.items() if data[row] < count], [])


class LoaderSample(unittest.TestCase):
    def test_loader_sample_holds_every_required_file(self):
        self.assertEqual({path.name for path in LOADER_SAMPLE.iterdir()}, LOADER_FILES | {"MANIFEST.md"})
        manifest = (LOADER_SAMPLE / "MANIFEST.md").read_text(encoding="utf8")
        for name in sorted(LOADER_FILES - {"review_decisions.csv"}):
            with self.subTest(name):
                self.assertIn(f"`{name}`", manifest)
                self.assertIn(f"`{hashlib.sha256((LOADER_SAMPLE / name).read_bytes()).hexdigest()}`", manifest)
                if name.endswith(".parquet"):
                    self.assertGreater(pq.read_metadata(LOADER_SAMPLE / name).num_rows, 0)

    def test_loader_sample_matches_are_whole(self):
        for league, stem in LEAGUES.items():
            with self.subTest(league):
                for name, key in ((f"{league}_M_1st_positions.parquet", "MatchURL"), (f"{league}_M_1st_match_summary.parquet", "MatchURL"), (f"{stem}_shot_data.parquet", "match_id")):
                    found, data = sample(name), data_frame(name)
                    self.assertEqual(row_counts(found), row_counts(data[data[key].isin(set(found[key]))]), name)
                positions, events = sample(f"{league}_M_1st_positions.parquet"), data_frame(f"{league}_M_1st_match_summary.parquet")
                self.assertEqual(row_counts(sample(f"{league}_M_1st_match_summary.parquet")), row_counts(events[events["MatchURL"].isin(set(positions["MatchURL"]))]))

    def test_loader_sample_holds_ticket_3_cases(self):
        for league, year, fbref_id in TICKET_3_PLAYER_SEASONS:
            with self.subTest((league, year, fbref_id)):
                name = f"{league}_M_1st_positions.parquet"
                rows = lambda frame: frame[(frame["Season_End_Year"] == year) & frame["Player_Href"].str.contains(f"/players/{fbref_id}/", regex=False)]
                self.assertGreater(len(rows(data_frame(name))), 0)
                self.assertEqual(row_counts(rows(sample(name))), row_counts(rows(data_frame(name))))
        found = set()
        for league in LEAGUES:
            found |= set(match_of(sample(f"{league}_M_1st_positions.parquet")["MatchURL"]))
        self.assertEqual(set(TICKET_3_FBREF_MATCHES) - found, set())
        for stem, match_id in TICKET_3_SHOT_MATCHES:
            self.assertIn(match_id, set(sample(f"{stem}_shot_data.parquet")["match_id"]))


if __name__ == "__main__":
    unittest.main()
