"""Cut small real samples from the stand-in originals into tests/fixtures/standin/, and write its README.

Usage: python3 scripts/cut_fixtures.py <folder holding the release assets> [output folder]

The originals are the assets of the private release named in SOURCE_RELEASE. Each one is checked against its
SHA-256 before use. Rows are never edited: each fixture is one source file, one row filter, all columns and the
source row order. Reading .rds follows the plan's rdata rules. No network calls.
"""
import hashlib
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import rdata

# rdata warns about R classes it has no constructor for. On these files they are object attributes, not columns.
warnings.filterwarnings("ignore", message="Missing constructor for R class")

SOURCE_RELEASE = "https://github.com/afarah101/football-twin/releases/tag/stand-in-originals"
MAX_BYTES = 1_000_000

SHA256 = {
    "bundesliga_shot_data.rds": "7481d4eea7a32c261ae45711e735a074c23aa4530a181c7f3c490150e8639bee",
    "epl_shot_data.rds": "c51e6661029a2b0f2b770bd9fc0a54da1913b303d6c6c908d11008f5c526ab60",
    "la_liga_shot_data.rds": "1a3a80f5e42c797ad056cb38fa10ca7c27b11f90987ee1921347eeba0728a803",
    "ligue_1_shot_data.rds": "bbc5bc4e6f0ffc94f01ec016e4df45dc6d53264f92c917e113c0c5b9ecdbc49a",
    "ENG_M_1st_passing_player_advanced_match_stats.rds": "9cc109613af0c89624ffdf845dcffcb5e1c48b779d160fd4a592fd7c4f6dcf1f",
    "ESP_M_1st_passing_player_advanced_match_stats.rds": "0915ccb4f6c964f7f3b5d829b9a6079c4bc79a0bcee6f1dc4777fb0a3a020230",
    "FRA_M_1st_passing_player_advanced_match_stats.rds": "9312d576021d26b5ea8c14a6cdee28638c118e22a921bf6c861afd6eec6f2623",
    "GER_M_1st_passing_player_advanced_match_stats.rds": "64f2488bf5358bb7011368d047def48c099f44244e3642bd9fb4b0aa5a1e2fc4",
    "ESP_M_1st_match_summary.rds": "f8d0532f1110f3bdeea10fd6a164c00a1f57c6dcc1d7484f5feb818ba4697c6e",
    "understat_xg_data.csv": "4e3751c47205c274315bb99f7df983adc4d15fe03c454590299587e7d3b3e475",
}

PASSING = "_M_1st_passing_player_advanced_match_stats.rds"
SUB_MATCH = "https://fbref.com/en/matches/30d3212e/Almeria-Rayo-Vallecano-August-11-2023-La-Liga"
OWN_GOAL_MATCH = "https://fbref.com/en/matches/0d3827c8/Real-Betis-Celta-Vigo-August-25-2017-La-Liga"
MOURA = "/en/players/2b622f01/Lucas-Moura"
NMECHA = "/en/players/0cc5f4a5/Lukas-Nmecha"
BRERETON = "/en/players/57827369/Ben-Brereton"
BRADY = "/en/players/96bb8cc2/Robbie-Brady"
PUERTAS = "/en/players/185a2732/Cameron-Puertas"


@dataclass(frozen=True)
class Sample:
    case: str
    source: str
    where: tuple
    rows: int
    why: str


SAMPLES = [
    Sample("league_move", "epl_shot_data.rds", (("player", "Lucas Moura"), ("season", 2017)), 5, "Second stint of a mid-season move, Ligue 1 to Premier League. Two PlayerSeasons, never merged."),
    Sample("league_move", "ligue_1_shot_data.rds", (("player", "Lucas Moura"), ("season", 2017)), 3, "First stint of the same move."),
    Sample("league_move", "ENG" + PASSING, (("Player_Href", MOURA), ("Season_End_Year", 2018)), 6, "Premier League positions and minutes for the second stint."),
    Sample("league_move", "FRA" + PASSING, (("Player_Href", MOURA), ("Season_End_Year", 2018)), 5, "Ligue 1 positions and minutes for the first stint."),
    Sample("league_move", "understat_xg_data.csv", (("player_name", "Lucas Moura"), ("season", "2017-2018")), 2, "Season totals, one row per league."),
    Sample("substitute", "ESP_M_1st_match_summary.rds", (("MatchURL", SUB_MATCH),), 16, "All events of one match, including `Substitute` rows in the form `X for Y`. The left name came on."),
    Sample("substitute", "ESP" + PASSING, (("MatchURL", SUB_MATCH),), 32, "All players of that match. Pos has no `Sub` value, so substitutes come from the events."),
    Sample("own_goal", "la_liga_shot_data.rds", (("match_id", 7890),), 20, "All shots of a match holding a `result` of `OwnGoal`, which metrics must exclude."),
    Sample("own_goal", "ESP_M_1st_match_summary.rds", (("MatchURL", OWN_GOAL_MATCH),), 13, "The same match in the events, where the own goal is an `Own Goal` row."),
    Sample("under_900", "GER" + PASSING, (("Player_Href", NMECHA), ("Season_End_Year", 2023)), 16, "Attacker just under the line: 899 FBref minutes, so out of the Pool."),
    Sample("under_900", "bundesliga_shot_data.rds", (("player", "Lukas Nmecha"), ("season", 2022)), 22, "The same player-season's shots."),
    Sample("under_900", "understat_xg_data.csv", (("player_name", "Lukas Nmecha"), ("season", "2022-2023"), ("league", "GER")), 1, "The same player-season in HF, which has 893 minutes."),
    Sample("multi_position", "ENG" + PASSING, (("Player_Href", BRERETON), ("Season_End_Year", 2024)), 14, "A player-season with a `FW,LW` row and non-attacking rows, for the attacking-minutes rule."),
    Sample("lm_rm_only", "ENG" + PASSING, (("Player_Href", BRADY), ("Season_End_Year", 2021)), 19, "A player-season at 900+ with only LM and RM labels. These stay \"other\", so it is out of the Pool."),
    Sample("html_entity", "epl_shot_data.rds", (("player", "Dara O&#039;Shea"), ("season", 2020)), 3, "Name stored with an HTML entity in the shot file."),
    Sample("html_entity", "understat_xg_data.csv", (("player_name", "Dara O&#039;Shea"), ("season", "2020-2021")), 1, "The same entity in HF."),
    Sample("html_entity", "ENG" + PASSING, (("Player", "Dara O'Shea"), ("Season_End_Year", 2021)), 28, "FBref stores the plain name, so joins must unescape."),
    Sample("shared_name", "la_liga_shot_data.rds", (("player", "Nacho"), ("season", 2019)), 15, "One name, two `player_id` values, one league-season."),
    Sample("shared_name", "ESP" + PASSING, (("Player", "Nacho"), ("Season_End_Year", 2020)), 29, "The same name with two `Player_Href` values."),
    Sample("shared_name", "understat_xg_data.csv", (("player_name", "Nacho"), ("season", "2019-2020"), ("league", "ESP")), 2, "HF has no id, so only the row count shows two players."),
    Sample("current_season", "bundesliga_shot_data.rds", (("player", "Cameron Puertas"), ("season", 2025)), 3, "A 2025/26 player, under 900 minutes. The files stop in September 2025."),
    Sample("current_season", "GER" + PASSING, (("Player_Href", PUERTAS), ("Season_End_Year", 2026)), 1, "The same player's FBref row. HF has no 2025/26 rows."),
]

NOT_FOUND = [
    ("A `Sub` Pos label", "FBref Pos has no `Sub` value in any stat file. Substitute appearances are taken from `Substitute` event rows instead."),
    ("HF row for the current-season player", "HF stops at 2024-2025, so `understat_xg_data.csv` has no 2025-2026 rows."),
]


def with_standard_nulls(frame):
    """Plan rule: pd.NA is the only null. float64 is the one dtype here that still holds NaN."""
    frame = frame.reset_index(drop=True)
    return frame.astype({c: "Float64" for c in frame.select_dtypes("float64").columns})


def read_source(path):
    if path.suffix == ".rds":
        return with_standard_nulls(rdata.read_rds(path, default_encoding="utf8"))
    return with_standard_nulls(pd.read_csv(path, low_memory=False))


def sha256_of(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(2**20):
            digest.update(chunk)
    return digest.hexdigest()


def fixture_name(sample):
    return f"{sample.case}__{Path(sample.source).stem}.parquet"


def filter_text(sample):
    return " and ".join(f"`{column} == {value!r}`" for column, value in sample.where)


def matching_rows(frame, sample):
    mask = pd.Series(True, index=frame.index)
    for column, value in sample.where:
        mask &= (frame[column] == value).fillna(False).astype(bool)
    return frame[mask]


def write_fixture(frame, target):
    pq.write_table(pa.Table.from_pandas(frame.reset_index(drop=True), preserve_index=False), target, compression="zstd")
    if target.stat().st_size >= MAX_BYTES:
        raise SystemExit(f"{target.name} is over {MAX_BYTES} bytes")
    back = pq.read_table(target).to_pandas()
    if not back.reset_index(drop=True).astype(str).equals(frame.reset_index(drop=True).astype(str)):
        raise SystemExit(f"{target.name} did not read back the same")


def readme(lines):
    versions = f"pandas {pd.__version__}, pyarrow {pa.__version__}, rdata {rdata.__version__}"
    table = "\n".join(lines)
    missing = "\n".join(f"| {case} | NOT FOUND | {reason} |" for case, reason in NOT_FOUND)
    return f"""# Stand-in fixtures

Small real samples cut from the stand-in originals. Rows are real and unedited: all columns, source row order, no invented data. Generated by `scripts/cut_fixtures.py`, so do not edit by hand.

- Source: private release <{SOURCE_RELEASE}>. Each file is checked against the SHA-256 below before use.
- Reading `.rds`: `rdata.read_rds(path, default_encoding="utf8")`, 1-based index dropped, nulls converted to `pd.NA`.
- Written with: {versions}.
- Re-cut: `python3 scripts/cut_fixtures.py <folder holding the release assets>`. Live Understat recordings replace these when Understat returns.

Source rows are 0-based positions in the source file.

| Fixture | Source file | Source SHA-256 | Row filter | Rows | Source rows | Why it exists |
|---|---|---|---|---:|---|---|
{table}

## Cases not found

| Case | Result | Why |
|---|---|---|
{missing}
"""


def main(originals, out):
    out.mkdir(parents=True, exist_ok=True)
    for name, expected in SHA256.items():
        if sha256_of(originals / name) != expected:
            raise SystemExit(f"{name} does not match its SHA-256")
    frames = {name: read_source(originals / name) for name in sorted({s.source for s in SAMPLES})}
    lines = []
    for sample in SAMPLES:
        rows = matching_rows(frames[sample.source], sample)
        if len(rows) != sample.rows:
            raise SystemExit(f"{fixture_name(sample)}: expected {sample.rows} rows, found {len(rows)}")
        write_fixture(rows, out / fixture_name(sample))
        positions = rows.index.tolist()
        span = f"{positions[0]}" if len(positions) == 1 else f"{positions[0]} to {positions[-1]}"
        lines.append(f"| `{fixture_name(sample)}` | `{sample.source}` | `{SHA256[sample.source]}` | {filter_text(sample)} | {len(rows)} | {span} | {sample.why} |")
        print(f"{fixture_name(sample)}\t{len(rows)}\t{(out / fixture_name(sample)).stat().st_size}")
    (out / "README.md").write_text(readme(lines), encoding="utf8")


if __name__ == "__main__":
    default_out = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "standin"
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else default_out)
