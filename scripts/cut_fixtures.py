"""Cut every fixture in tests/fixtures/standin/ from the trimmed files in data/standin/, and write their READMEs.

Usage: python3 scripts/cut_fixtures.py [output folder]

It writes the case samples, the rule3__* samples for the join module's tests and loader_sample/ for the adapter
seam. Rows are never edited: whole rows, all columns and the source row order. No network calls.

SOURCE_RELEASE, read_source and sha256_of stay here because scripts/trim_standin.py imports them (D17).
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

POSITIONS = "_M_1st_positions.parquet"
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
    Sample("league_move", "epl_shot_data.parquet", (("player", "Lucas Moura"), ("season", 2017)), 5, "Second stint of a mid-season move, Ligue 1 to Premier League. Two PlayerSeasons, never merged."),
    Sample("league_move", "ligue_1_shot_data.parquet", (("player", "Lucas Moura"), ("season", 2017)), 3, "First stint of the same move."),
    Sample("league_move", "ENG" + POSITIONS, (("Player_Href", MOURA), ("Season_End_Year", 2018)), 6, "Premier League positions and minutes for the second stint."),
    Sample("league_move", "FRA" + POSITIONS, (("Player_Href", MOURA), ("Season_End_Year", 2018)), 5, "Ligue 1 positions and minutes for the first stint."),
    Sample("league_move", "understat_xg_data.parquet", (("player_name", "Lucas Moura"), ("season", "2017-2018")), 2, "Season totals, one row per league."),
    Sample("substitute", "ESP_M_1st_match_summary.parquet", (("MatchURL", SUB_MATCH),), 16, "All events of one match, including `Substitute` rows in the form `X for Y`. The left name came on."),
    Sample("substitute", "ESP" + POSITIONS, (("MatchURL", SUB_MATCH),), 32, "All players of that match. Pos has no `Sub` value, so substitutes come from the events."),
    Sample("own_goal", "la_liga_shot_data.parquet", (("match_id", 7890),), 20, "All shots of a match holding a `result` of `OwnGoal`, which metrics must exclude."),
    Sample("own_goal", "ESP_M_1st_match_summary.parquet", (("MatchURL", OWN_GOAL_MATCH),), 13, "The same match in the events, where the own goal is an `Own Goal` row."),
    Sample("under_900", "GER" + POSITIONS, (("Player_Href", NMECHA), ("Season_End_Year", 2023)), 16, "Attacker just under the line: 899 FBref minutes, so out of the Pool."),
    Sample("under_900", "bundesliga_shot_data.parquet", (("player", "Lukas Nmecha"), ("season", 2022)), 22, "The same player-season's shots."),
    Sample("under_900", "understat_xg_data.parquet", (("player_name", "Lukas Nmecha"), ("season", "2022-2023"), ("league", "GER")), 1, "The same player-season in HF, which has 893 minutes."),
    Sample("multi_position", "ENG" + POSITIONS, (("Player_Href", BRERETON), ("Season_End_Year", 2024)), 14, "A player-season with a `FW,LW` row and non-attacking rows, for the attacking-minutes rule."),
    Sample("lm_rm_only", "ENG" + POSITIONS, (("Player_Href", BRADY), ("Season_End_Year", 2021)), 19, "A player-season at 900+ with only LM and RM labels. These stay \"other\", so it is out of the Pool."),
    Sample("html_entity", "epl_shot_data.parquet", (("player", "Dara O&#039;Shea"), ("season", 2020)), 3, "Name stored with an HTML entity in the shot file."),
    Sample("html_entity", "understat_xg_data.parquet", (("player_name", "Dara O&#039;Shea"), ("season", "2020-2021")), 1, "The same entity in HF."),
    Sample("html_entity", "ENG" + POSITIONS, (("Player", "Dara O'Shea"), ("Season_End_Year", 2021)), 28, "FBref stores the plain name, so joins must unescape."),
    Sample("shared_name", "la_liga_shot_data.parquet", (("player", "Nacho"), ("season", 2019)), 15, "One name, two `player_id` values, one league-season."),
    Sample("shared_name", "ESP" + POSITIONS, (("Player", "Nacho"), ("Season_End_Year", 2020)), 29, "The same name with two `Player_Href` values."),
    Sample("shared_name", "understat_xg_data.parquet", (("player_name", "Nacho"), ("season", "2019-2020"), ("league", "ESP")), 2, "HF has no id, so only the row count shows two players."),
    Sample("current_season", "bundesliga_shot_data.parquet", (("player", "Cameron Puertas"), ("season", 2025)), 3, "A 2025/26 player, under 900 minutes. The files stop in September 2025."),
    Sample("current_season", "GER" + POSITIONS, (("Player_Href", PUERTAS), ("Season_End_Year", 2026)), 1, "The same player's FBref row. HF has no 2025/26 rows."),
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
    ("ITA", 2023, 7944), ("ENG", 2022, 8845), ("ENG", 2023, 8845),  # Strefezza's two ids, Hwang's other seasons
)
# loader_sample/: ticket 3's real cases. Every row of each player-season, as (league, Season_End_Year, FBref id), with each match whole.
LOADER_FBREF_PLAYER_SEASONS = (
    ("ENG", 2018, "2b622f01"), ("FRA", 2018, "2b622f01"),  # Lucas Moura's league move
    ("ESP", 2020, "2946f9a1"), ("ESP", 2020, "e29d1111"),  # Nacho, two players
    ("GER", 2023, "0cc5f4a5"), ("ENG", 2024, "57827369"), ("ENG", 2021, "96bb8cc2"),  # Nmecha at 899, Brereton FW,LW, Brady LM and RM only
    ("FRA", 2019, "923f4dda"), ("ENG", 2023, "df8b52a5"), ("ENG", 2018, "0db5d2c8"),  # Guirassy by the FBref name, Emerson narrowed by club, Mathias Jørgensen with no totals row
    ("ENG", 2024, "4125cb98"), ("ENG", 2018, "2f90f6b8"), ("ESP", 2024, "0ae4e09a"),  # Jarell and Jarrell Quansah, a display label tie, Roger's gap of 3
    ("FRA", 2023, "45cce300"), ("ITA", 2022, "66784dee"), ("ITA", 2020, "48d5bd33"), ("GER", 2026, "185a2732"),  # Jeffinho, Dennis Johnsen, Ruslan Malinovskyi, a 2025/26 player
)
# Whole FBref matches: the substitute match, a match with no events, and the 4 Pool-season rows with a null Min.
LOADER_FBREF_MATCHES = ("30d3212e", "05060e6f", "0e98ac46", "58f908b1", "eb75d1da", "bca64d25")
# Whole Understat matches: the own goal and penalty match.
LOADER_SHOT_MATCH_IDS = (("ESP", 7890),)
# Every shot of these Understat player-seasons, each match whole, for the shots that joined no FBref row.
LOADER_SHOT_PLAYER_SEASONS = (("ITA", 2021, 9882), ("FRA", 2022, 11399), ("ITA", 2019, 7947), ("FRA", 2018, 3738))  # Johnsen, Jeffinho, Malinovskyi, Guirassy
# Every file the loader reads, under its data/standin/ name.
LOADER_FILES = (
    [f"{league}{POSITIONS}" for league in join.SHOT_FILE_OF_LEAGUE] + [f"{league}_M_1st_match_summary.parquet" for league in join.SHOT_FILE_OF_LEAGUE]
    + [f"{stem}_shot_data.parquet" for stem in join.SHOT_FILE_OF_LEAGUE.values()] + ["understat_xg_data.parquet", "club_map.csv", "review_decisions.csv"]
)

# Taken by club names, not through the link under test, as (league, year, home, away).
RULE3_FBREF_PAIRS = (("ITA", 2024, "Atalanta", "Fiorentina"),)
# Every row of these ids, so their minutes and Pool test are whole: the 3 merges, Juanfran at 2 teams, and the guard and flag cases.
RULE3_FBREF_IDS = (
    "ac4a4508", "674cfc5a", "8eb68164", "cb9ef70f", "1d039497", "f365b837", "cfd8d664", "9ba48d64",
    "66784dee", "48d5bd33", "45cce300", "ca241ad3", "bed68338", "923f4dda", "e0bc6fdc", "67ac5bb8", "b92b456a", "169fd162", "8cfc2f69",
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
    versions = f"pandas {pd.__version__}, pyarrow {pa.__version__}"
    table = "\n".join(lines)
    missing = "\n".join(f"| {case} | NOT FOUND | {reason} |" for case, reason in NOT_FOUND)
    return f"""# Stand-in fixtures

Small real samples cut from the trimmed files in `data/standin/`. Rows are real and unedited: whole rows, all columns, source row order, no invented data. Generated by `scripts/cut_fixtures.py`, so do not edit by hand.

- Source: `data/standin/`, the files listed in its `MANIFEST.md`, with the SHA-256 each sample was cut from.
- Written with: {versions}.
- Re-cut: `python3 scripts/cut_fixtures.py`. It also writes the `rule3__*` samples (`rule3__README.md`) and `loader_sample/` (`loader_sample/MANIFEST.md`). Live Understat recordings replace these when Understat returns.

Source rows are 0-based positions in the source file.

| Fixture | Source file | Source SHA-256 | Row filter | Rows | Source rows | Why it exists |
|---|---|---|---|---:|---|---|
{table}

## Cases not found

| Case | Result | Why |
|---|---|---|
{missing}
"""


def cut_samples(out):
    lines = []
    for name in sorted({sample.source for sample in SAMPLES}):
        frame = pd.read_parquet(join.DATA / name)
        for sample in [sample for sample in SAMPLES if sample.source == name]:
            rows = matching_rows(frame, sample)
            if len(rows) != sample.rows:
                raise SystemExit(f"{fixture_name(sample)}: expected {sample.rows} rows, found {len(rows)}")
            write_fixture(rows, out / fixture_name(sample))
            positions = rows.index.tolist()
            span = f"{positions[0]}" if len(positions) == 1 else f"{positions[0]} to {positions[-1]}"
            lines.append((SAMPLES.index(sample), f"| `{fixture_name(sample)}` | `data/standin/{name}` | `{sha256_of(join.DATA / name)}` | {filter_text(sample)} | {len(rows)} | {span} | {sample.why} |"))
            print(f"{fixture_name(sample)}\t{len(rows)}\t{(out / fixture_name(sample)).stat().st_size}")
    (out / "README.md").write_text(readme([line for _, line in sorted(lines)]), encoding="utf8")


def shot_keys(shots, match_ids, player_seasons, matches=()):
    """The (league, match_id) of every Understat match the cases name."""
    keys = set(match_ids)
    for league, season, player_id in player_seasons:
        found = shots[(shots["league"] == league) & (shots["season"] == season) & (shots["player_id"] == player_id)]
        if found.empty:
            raise SystemExit(f"no shot rows for {league} {season} {player_id}")
        keys |= set(zip(found["league"], found["match_id"]))
    for league, season, home, away in matches:
        found = shots[(shots["league"] == league) & (shots["season"] == season) & (shots["home_team"] == home) & (shots["away_team"] == away)]
        if found.empty:
            raise SystemExit(f"no shot rows for {league} {season} {home} v {away}")
        keys |= set(zip(found["league"], found["match_id"]))
    return keys


def cut_rule3(out):
    """Whole rows of data/standin, filtered and never edited, under the same file names with a rule3__ prefix."""
    source = join.StandinFiles()
    shots = join.load_shots(source)
    keys = shot_keys(join.shot_files(source), RULE3_SHOT_MATCH_IDS, RULE3_PLAYER_SEASONS, RULE3_SHOT_MATCHES)
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
    (out / "rule3__review_decisions.csv").write_bytes(source.path("review_decisions.csv").read_bytes())
    lines.append("| `rule3__review_decisions.csv` | `data/standin/review_decisions.csv` | all | Ahmed's file as it stands |")
    lines.append("| `rule3__club_map.csv` | `data/standin/club_map.csv` | all | The whole map |")
    table = "\n".join(lines)
    (out / "rule3__README.md").write_text(f"""# rule3__ samples

Real rows for `tests/test_player_join.py`, cut from `data/standin/` and never edited. Generated by `python3 scripts/cut_fixtures.py`, so do not edit by hand. The cases are the `RULE3_*` lists in `scripts/cut_fixtures.py`.

| Fixture | Source file | Rows | What it holds |
|---|---|---:|---|
{table}
""", encoding="utf8")


def cut_loader_sample(out):
    """Whole matches of ticket 3's cases, from every file the loader reads, under the data/standin/ names."""
    out.mkdir(parents=True, exist_ok=True)
    source = join.StandinFiles()
    positions = {league: pd.read_parquet(source.path(f"{league}{POSITIONS}")) for league in join.SHOT_FILE_OF_LEAGUE}
    fbref_matches = set(LOADER_FBREF_MATCHES)
    for league, year, fbref_id in LOADER_FBREF_PLAYER_SEASONS:
        rows = positions[league]
        found = rows[(rows["Season_End_Year"] == year) & (rows["Player_Href"].str.extract(r"/players/([0-9a-f]{8})/", expand=False) == fbref_id)]
        if found.empty:
            raise SystemExit(f"no FBref rows for {league} {year} {fbref_id}")
        fbref_matches |= set(found["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False))
    links = join.link_matches(join.load_shots(source), join.load_positions(source), join.understat_to_fbref_clubs(source)).links
    keys = shot_keys(join.shot_files(source), LOADER_SHOT_MATCH_IDS, LOADER_SHOT_PLAYER_SEASONS) | {key for key, match in links.items() if match in fbref_matches}
    fbref_matches |= {links[key] for key in keys if key in links}
    kept, names = {}, set()
    for league, stem in join.SHOT_FILE_OF_LEAGUE.items():
        rows = positions[league]
        kept[f"{league}{POSITIONS}"] = rows[rows["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False).isin(fbref_matches)]
        names |= {(league, int(year) - 1, html.unescape(player)) for year, player in zip(kept[f"{league}{POSITIONS}"]["Season_End_Year"], kept[f"{league}{POSITIONS}"]["Player"])}
        events = pd.read_parquet(source.path(f"{league}_M_1st_match_summary.parquet"))
        kept[f"{league}_M_1st_match_summary.parquet"] = events[events["MatchURL"].isin(kept[f"{league}{POSITIONS}"]["MatchURL"])]
        rows = pd.read_parquet(source.path(f"{stem}_shot_data.parquet"))
        kept[f"{stem}_shot_data.parquet"] = rows[[(league, match_id) in keys for match_id in rows["match_id"]]]
        names |= {(league, int(season), html.unescape(player)) for season, player in zip(kept[f"{stem}_shot_data.parquet"]["season"], kept[f"{stem}_shot_data.parquet"]["player"])}
    rows = pd.read_parquet(source.path("understat_xg_data.parquet"))
    kept["understat_xg_data.parquet"] = rows[[("ENG" if league == "EPL" else league, int(season[:4]), html.unescape(name)) in names for league, season, name in zip(rows["league"], rows["season"], rows["player_name"])]]
    source_lines, file_lines = [], []
    for name in sorted(kept):
        write_fixture(kept[name], out / name)
        metadata = pq.read_metadata(source.path(name))
        columns = ", ".join(f"`{column}`" for column in metadata.schema.names)
        source_lines.append(f"| `data/standin/{name}` | `{sha256_of(source.path(name))}` | `{name}` | `{sha256_of(out / name)}` | {metadata.num_rows} | {len(kept[name])} | {metadata.num_columns} | not used (cut from Parquet) |")
        file_lines.append(f"| `{name}` | {len(kept[name])} | {metadata.num_columns} | {(out / name).stat().st_size} | {columns} |")
        print(f"loader_sample/{name}\t{len(kept[name])}\t{(out / name).stat().st_size}")
    for name in ("club_map.csv", "review_decisions.csv"):
        (out / name).write_bytes(source.path(name).read_bytes())
    assert sorted(path.name for path in out.iterdir() if path.name != "MANIFEST.md") == sorted(LOADER_FILES), "loader_sample/ must hold exactly the files the loader reads"
    (out / "MANIFEST.md").write_text(f"""# Stand-in loader sample

Private. Not for publication. Generated by `scripts/cut_fixtures.py`, so do not edit by hand.

- Source: `data/standin/`. Whole rows, never edited: every match of ticket 3's cases, each one whole in the positions, event and shot files, and its linked match on the other side. The cases are the `LOADER_*` lists in `scripts/cut_fixtures.py`.
- Written with: pandas {pd.__version__}, pyarrow {pa.__version__}.
- Repeat: `python3 scripts/cut_fixtures.py`.
- File names are those of `data/standin/`, so the loader reads this folder as it reads that one. `review_decisions.csv` is copied whole, as it stands.

## Sources

| Source asset | Original SHA-256 | Trimmed file | Trimmed SHA-256 | Source rows | Rows kept | Source columns | rdata version |
|---|---|---|---|---:|---:|---:|---|
{chr(10).join(source_lines)}

## Trimmed files

| File | Rows | Columns | Bytes | Kept columns |
|---|---:|---:|---:|---|
{chr(10).join(file_lines)}

## Club map

`club_map.csv`, SHA-256 `{sha256_of(out / "club_map.csv")}`. Copied whole from `data/standin/club_map.csv`.
""", encoding="utf8")


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    cut_samples(out)
    cut_rule3(out)
    cut_loader_sample(out / "loader_sample")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tests" / "fixtures" / "standin")
