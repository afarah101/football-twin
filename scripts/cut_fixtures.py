"""Cut small real samples into tests/fixtures/standin/, and write their READMEs.

Usage: python3 scripts/cut_fixtures.py <folder holding the release assets> [output folder]
       python3 scripts/cut_fixtures.py --rule3 [output folder]

The second form cuts the rule3__* samples from data/standin/ for the join module's tests.

The originals are the assets of the private release named in SOURCE_RELEASE. Each one is checked against its
SHA-256 before use. Rows are never edited: each fixture is one source file, one row filter, all columns and the
source row order. Reading .rds follows the plan's rdata rules. No network calls.
"""
import hashlib
import html
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
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.infrastructure.standin import player_join as join

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

# Whole Understat matches as (league, season, home, away), each with its linked FBref match.
RULE3_SHOT_MATCHES = (
    ("ESP", 2023, "Getafe", "Cadiz"), ("ESP", 2023, "Cadiz", "Getafe"),  # both legs of one pair
    ("ENG", 2023, "Brighton", "Everton"),  # the club map changes the name
    ("FRA", 2017, "Caen", "Toulouse"), ("FRA", 2022, "Strasbourg", "Lyon"), ("ITA", 2023, "Udinese", "Roma"),  # the 3 gaps over 1 day
    ("ITA", 2023, "Atalanta", "Fiorentina"),  # no FBref minutes, so 20 rows drop
    ("GER", 2023, "Bochum", "Augsburg"),
)
# Whole shot matches by id, for rows outside the Pool seasons or with one spelling of the league.
RULE3_SHOT_MATCH_IDS = (("ESP", 1779), ("ESP", 5826), ("ESP", 18962), ("ENG", 22275))
RULE3_FBREF_MATCHES = (
    "e0449015",  # Spezia v Hellas Verona, the one tie-breaker
    # One real example of each step 1 and step 2 clause, each with its linked Understat match.
    "017448ed", "01d63d4d", "06ec2f77", "082489f8", "0cbb18e2", "68df68a4", "127b8258", "11a67612", "21098c4b", "2424dced", "10b27265", "9ba359c1", "0abc466b", "ba501a17", "09d80d49", "010301bf", "711e1d1f",
)
# Every shot of a player-season, as (league, season, player_id), each match whole: the anchors, stops and named cases.
RULE3_PLAYER_SEASONS = (
    ("ESP", 2021, 2098), ("ESP", 2021, 8978),  # Luis Suárez, twice
    ("ESP", 2019, 2302), ("ENG", 2021, 8845), ("ESP", 2019, 684), ("FRA", 2018, 684), ("GER", 2018, 684),  # Bruno, Hwang, Baba
    ("ESP", 2020, 4136), ("ESP", 2020, 6216), ("ESP", 2019, 6216),  # Ángel, and Chema in two seasons
    ("GER", 2023, 3738), ("ENG", 2020, 5613), ("ENG", 2021, 10092), ("ESP", 2023, 5159), ("ENG", 2020, 8756),  # Guirassy, Gabriel, Fosu-Henry, Marc Cardona, Dara O'Shea
    ("ITA", 2021, 9882), ("FRA", 2022, 7947), ("FRA", 2022, 11399), ("ITA", 2019, 7941), ("ITA", 2019, 8259),  # Johnsen, Malinovskiy, Jeffinho, André and Djavan Anderson
    ("ESP", 2023, 10095), ("FRA", 2018, 3738), ("ENG", 2022, 1245),  # Ezzalzouli, Guirassy under the FBref name, Emerson at West Ham
)
# Taken by club names, not through the link under test, as (league, year, home, away).
RULE3_FBREF_PAIRS = (("ITA", 2024, "Atalanta", "Fiorentina"),)
# Every row of these ids, so their minutes and Pool test are whole: the 3 merges, Juanfran at 2 teams, and the guard and flag cases.
RULE3_FBREF_IDS = (
    "ac4a4508", "674cfc5a", "8eb68164", "cb9ef70f", "1d039497", "f365b837", "cfd8d664", "9ba48d64",
    "66784dee", "48d5bd33", "45cce300", "ca241ad3", "bed68338", "923f4dda", "e0bc6fdc", "67ac5bb8", "b92b456a", "169fd162",
)

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


def rule3_shot_keys(shots):
    """The (league, match_id) of every Understat match the cases name."""
    keys = set(RULE3_SHOT_MATCH_IDS)
    for league, season, player_id in RULE3_PLAYER_SEASONS:
        found = shots[(shots["league"] == league) & (shots["season"] == season) & (shots["player_id"] == player_id)]
        if found.empty:
            raise SystemExit(f"no shot rows for {league} {season} {player_id}")
        keys |= set(zip(found["league"], found["match_id"]))
    for league, season, home, away in RULE3_SHOT_MATCHES:
        found = shots[(shots["league"] == league) & (shots["season"] == season) & (shots["home_team"] == home) & (shots["away_team"] == away)]
        if found.empty:
            raise SystemExit(f"no shot rows for {league} {season} {home} v {away}")
        keys |= set(zip(found["league"], found["match_id"]))
    return keys


def cut_rule3(out):
    """Whole rows of data/standin, filtered and never edited, under the same file names with a rule3__ prefix."""
    source = join.StandinFiles()
    shots = join.load_shots(source)
    keys = rule3_shot_keys(join.shot_files(source))
    links = join.link_matches(shots, join.load_positions(source), join.understat_to_fbref_clubs(source)).links
    keys |= {key for key, match in links.items() if match in RULE3_FBREF_MATCHES}
    fbref_matches = set(RULE3_FBREF_MATCHES) | {links[key] for key in keys if key in links}
    lines = []

    def write(frame, name, why):
        write_fixture(frame, out / f"rule3__{name}")
        lines.append(f"| `rule3__{name}` | `data/standin/{name}` | {len(frame)} | {why} |")
        print(f"rule3__{name}\t{len(frame)}\t{(out / f'rule3__{name}').stat().st_size}")

    names = set()
    for league, stem in join.SHOT_FILE_OF_LEAGUE.items():
        rows = pd.read_parquet(source.path(f"{league}_M_1st_positions.parquet"))
        match = rows["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False)
        fbref_id = rows["Player_Href"].str.extract(r"/players/([0-9a-f]{8})/", expand=False)
        pairs = {(year, home, away) for found_league, year, home, away in RULE3_FBREF_PAIRS if found_league == league}
        in_pair = pd.Series([key in pairs for key in zip(rows["Season_End_Year"], rows["Home_Team"], rows["Away_Team"])], index=rows.index)
        kept = rows[match.isin(fbref_matches) | fbref_id.isin(RULE3_FBREF_IDS) | in_pair]
        write(kept, f"{league}_M_1st_positions.parquet", "Whole FBref matches, and every row of the named ids")
        names |= {(league, int(year) - 1, html.unescape(player)) for year, player in zip(kept["Season_End_Year"], kept["Player"])}
        events = pd.read_parquet(source.path(f"{league}_M_1st_match_summary.parquet"))
        write(events[events["MatchURL"].isin(kept["MatchURL"])], f"{league}_M_1st_match_summary.parquet", "All events of those FBref matches, for the substitutes")
        rows = pd.read_parquet(source.path(f"{stem}_shot_data.parquet"))
        kept = rows[[(league, match_id) in keys for match_id in rows["match_id"]]]
        write(kept, f"{stem}_shot_data.parquet", "Whole Understat matches")
        names |= {(league, int(season), html.unescape(player)) for season, player in zip(kept["season"], kept["player"])}
    rows = pd.read_parquet(source.path("understat_xg_data.parquet"))
    wanted = [("ENG" if league == "EPL" else league, int(season[:4]), html.unescape(name)) in names for league, season, name in zip(rows["league"], rows["season"], rows["player_name"])]
    write(rows[wanted], "understat_xg_data.parquet", "Season totals rows under any name in the sample's league-seasons")
    (out / "rule3__club_map.csv").write_bytes(source.path("club_map.csv").read_bytes())
    lines.append("| `rule3__club_map.csv` | `data/standin/club_map.csv` | all | The whole map |")
    table = "\n".join(lines)
    (out / "rule3__README.md").write_text(f"""# rule3__ samples

Real rows for `tests/test_player_join.py`, cut from `data/standin/` and never edited. Generated by `python3 scripts/cut_fixtures.py --rule3`, so do not edit by hand. The cases are the `RULE3_*` lists in `scripts/cut_fixtures.py`.

| Fixture | Source file | Rows | What it holds |
|---|---|---:|---|
{table}
""", encoding="utf8")


if __name__ == "__main__":
    default_out = ROOT / "tests" / "fixtures" / "standin"
    if sys.argv[1] == "--rule3":
        cut_rule3(Path(sys.argv[2]) if len(sys.argv) > 2 else default_out)
    else:
        main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else default_out)
