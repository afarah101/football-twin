"""Trim the stand-in originals to the columns the build needs, into data/standin/ as Parquet, and write its MANIFEST.md.

Usage: python3 scripts/trim_standin.py <folder holding the release assets> [output folder]

Each original is checked against its SHA-256 before use. Shot, event and HF files keep every row, in source order.
FBref positions combine five stat files per league, see combined_positions. Only their Pos can differ from the file a
match came from, see majority_pos. club_map.csv links Understat and FBref clubs, see club_rows. Names stay exactly as
stored. Reading .rds follows the plan's rdata rules. No network calls. The same originals and library versions give
identical bytes.
"""
import platform
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import rdata

from cut_fixtures import SOURCE_RELEASE, read_source, sha256_of

MAX_BYTES = 100_000_000

SHA256 = {
    "bundesliga_shot_data.rds": "7481d4eea7a32c261ae45711e735a074c23aa4530a181c7f3c490150e8639bee",
    "epl_shot_data.rds": "c51e6661029a2b0f2b770bd9fc0a54da1913b303d6c6c908d11008f5c526ab60",
    "la_liga_shot_data.rds": "1a3a80f5e42c797ad056cb38fa10ca7c27b11f90987ee1921347eeba0728a803",
    "ligue_1_shot_data.rds": "bbc5bc4e6f0ffc94f01ec016e4df45dc6d53264f92c917e113c0c5b9ecdbc49a",
    "serie_a_shot_data.rds": "fb024cc8fc8aa72edf6b826629ffe1f36dc3f2e20645f3aade85a4f2ec36b559",
    "ENG_M_1st_defense_player_advanced_match_stats.rds": "a7ef11574455db1aa086377ef90a6a87239365538c3ee7e038725d9bfe47d9b9",
    "ENG_M_1st_keeper_player_advanced_match_stats.rds": "963ea839deabf5866bf25f1c21b49124b0fc79b71254f9b6ad1b199ee78c063c",
    "ENG_M_1st_misc_player_advanced_match_stats.rds": "9c8b96b0bf1166c51cd996b0b16eaebfaa633c0981d028feca71d6ea04e738c2",
    "ENG_M_1st_passing_player_advanced_match_stats.rds": "9cc109613af0c89624ffdf845dcffcb5e1c48b779d160fd4a592fd7c4f6dcf1f",
    "ENG_M_1st_passing_types_player_advanced_match_stats.rds": "26c3cb1c949d29a52be80774ea8c3f181f089ba386ec77658a90049df14005b5",
    "ENG_M_1st_possession_player_advanced_match_stats.rds": "0380e5719d050847bda441983e8ec9560cd6529d74d74a10efd6cb36403d0c7d",
    "ESP_M_1st_defense_player_advanced_match_stats.rds": "6c6edcb327338fb1fdc2fcab428dbbb47ed9cc401b91df3146edb689cb02a6d6",
    "ESP_M_1st_misc_player_advanced_match_stats.rds": "e06350efd8e4e4f7bf6b729b78399a012176fc598121f2772b4b9660027f8b9f",
    "ESP_M_1st_passing_player_advanced_match_stats.rds": "0915ccb4f6c964f7f3b5d829b9a6079c4bc79a0bcee6f1dc4777fb0a3a020230",
    "ESP_M_1st_passing_types_player_advanced_match_stats.rds": "01a1a30460e92e7ce362bab5338907f52504d1e120b1a05d7293f1f09256f0e4",
    "ESP_M_1st_possession_player_advanced_match_stats.rds": "00bcb883f245a4c73c61851bee7bb4818d66f2bd97844ba94c5e54a715bc03fe",
    "FRA_M_1st_defense_player_advanced_match_stats.rds": "9948a5e024dbc37dc7231f870604f97f0bc2813b23d20a7152a4784808a04e32",
    "FRA_M_1st_misc_player_advanced_match_stats.rds": "aafe3c5e59d8ba35e5510a4143bc1eb0bd6af62e721bf2bb5426687abc0d3e2d",
    "FRA_M_1st_passing_player_advanced_match_stats.rds": "9312d576021d26b5ea8c14a6cdee28638c118e22a921bf6c861afd6eec6f2623",
    "FRA_M_1st_passing_types_player_advanced_match_stats.rds": "f071c00d319a8a8562be8164fc6347dcbb9737dcf1d3f939cc8ff96f633f5ae6",
    "FRA_M_1st_possession_player_advanced_match_stats.rds": "39539d465b5a21253d0540155316b73c8653d5ed6e47ef6400ceadc212e9238f",
    "GER_M_1st_defense_player_advanced_match_stats.rds": "6c5286f084a7c69b94264585accc1cfaab022c63f0bd130da08bdb0068722ca0",
    "GER_M_1st_misc_player_advanced_match_stats.rds": "eacb8d76af227e2a60f1ed8b70e967da6a23398f254b229809ac45919198de03",
    "GER_M_1st_passing_player_advanced_match_stats.rds": "64f2488bf5358bb7011368d047def48c099f44244e3642bd9fb4b0aa5a1e2fc4",
    "GER_M_1st_passing_types_player_advanced_match_stats.rds": "f79a66cad851e0df013d149436372320191b848864ff5119b9f304acd5bb73ac",
    "GER_M_1st_possession_player_advanced_match_stats.rds": "9506d49cd2af4bc48a4fefd1389867363cff207b51c87d0c04b4644645ff2da3",
    "ITA_M_1st_defense_player_advanced_match_stats.rds": "b75b2819e1dbf6f811fa9b00c6d1b20136692c1acbb374b194e5fa675b70531b",
    "ITA_M_1st_misc_player_advanced_match_stats.rds": "fdbaaef29028309c925c2fe870101db8be8711b475f368acbc6951375ed4cbbb",
    "ITA_M_1st_passing_player_advanced_match_stats.rds": "96e8e99ce2b8f7cb91d6af87752ce0dd363d8f1627ccfe7f9a14ac25d575ca43",
    "ITA_M_1st_passing_types_player_advanced_match_stats.rds": "e0fae3c5ce6eaa8260b610505a0f201dd32938e0518a3446525faac1ee275e72",
    "ITA_M_1st_possession_player_advanced_match_stats.rds": "2a09ba7cf18e3e83f5b7332a5fd36f2728607fb6a04b56d50f95b664af8bdd3a",
    "ENG_M_1st_match_summary.csv": "50d6f42a81bba279f734439d356e0512ab7e9d2ef9e74db98856dd3db2b45861",
    "ESP_M_1st_match_summary.rds": "f8d0532f1110f3bdeea10fd6a164c00a1f57c6dcc1d7484f5feb818ba4697c6e",
    "FRA_M_1st_match_summary.rds": "7cb154acdc243cb252a48091fe586b0e7ca0cf85f103b9af2b2677c053eff56c",
    "GER_M_1st_match_summary.rds": "dc9356a544132e92c6e9831e4d5fbfa176abab82c347209b6380b8014fdbb913",
    "ITA_M_1st_match_summary.rds": "2b09168c196fc4004b6ba3992c30f1883589bc50d2c28570389a70166ad56a2c",
    "understat_xg_data.csv": "4e3751c47205c274315bb99f7df983adc4d15fe03c454590299587e7d3b3e475",
    "master_player_stats.csv": "96a5379af53321616d727bb49259befc0506755b0e2829859ce191146f65a8c8",
}

LEAGUES = ("ENG", "ESP", "FRA", "GER", "ITA")
SHOT_FILE_OF_LEAGUE = {"ENG": "epl_shot_data.rds", "ESP": "la_liga_shot_data.rds", "FRA": "ligue_1_shot_data.rds", "GER": "bundesliga_shot_data.rds", "ITA": "serie_a_shot_data.rds"}
SHOT_FILES = tuple(sorted(SHOT_FILE_OF_LEAGUE.values()))
EVENT_FILES = ("ENG_M_1st_match_summary.csv", "ESP_M_1st_match_summary.rds", "FRA_M_1st_match_summary.rds", "GER_M_1st_match_summary.rds", "ITA_M_1st_match_summary.rds")
# Measured order: the file that differs least from the other four on Pos comes first. See docs/reports/T7_trim.md.
POSITION_KINDS = ("passing_types", "possession", "passing", "defense", "misc")
NOT_STORED = {"ENG_M_1st_keeper_player_advanced_match_stats.rds": "No Pos column, and goalkeepers are out of scope."}

SHOT_COLUMNS = ["id", "league", "season", "match_id", "date", "player", "player_id", "home_team", "away_team", "X", "Y", "xG", "situation", "shotType", "lastAction", "result"]
POSITION_COLUMNS = ["MatchURL", "Match_Date", "Matchweek", "Season_End_Year", "Home_Team", "Away_Team", "Team", "Player", "Player_Href", "Pos", "Min"]
EVENT_COLUMNS = ["MatchURL", "Match_Date", "Season_End_Year", "Team", "Event_Type", "Event_Players"]
HF_TOTALS_COLUMNS = ["player_name", "team", "league", "season", "minutes", "goals", "assists", "shots", "key_passes", "xA", "npxG", "xGBuildup"]
HF_MASTER_COLUMNS = ["player", "player_id", "league", "season", "squad", "pos", "min"]


def majority_pos(kept, rows):
    """Plan rule: the most common Pos across the files holding the match. On a tie, the chosen file's value stays.

    Players match across files by the 8-character FBref id. An empty Pos is no vote. Pos is compared as stored, so
    `FW,AM` and `AM,FW` are different values. Adds how many files voted and whether the top count was tied.
    """
    key = ["match_id", "player_id"]
    votes = rows.loc[rows["Pos"] != "", [*key, "file_rank", "Pos"]].drop_duplicates([*key, "file_rank"])
    counts = votes.groupby([*key, "Pos"]).size().rename("votes").reset_index()
    tops = counts[counts["votes"] == counts.groupby(key)["votes"].transform("max")]
    summary = tops.groupby(key).agg(winner=("Pos", "first"), winners=("Pos", "size"))
    summary["Pos_Files_Voted"] = votes.groupby(key).size()
    merged = kept.merge(summary.reset_index(), on=key, how="left")
    winners = merged["winners"].fillna(0).astype("int64")
    return merged.assign(
        Pos=merged["winner"].where(winners == 1, merged["Pos"]),
        Pos_Files_Voted=merged["Pos_Files_Voted"].fillna(0).astype("int64"),
        Pos_Tie=winners > 1,
    )


def combined_positions(frames):
    """One row per player per match, each match taken whole from one file.

    Files can give one player two hrefs in the same match, so mixing files inside a match would count that player twice.
    A match holding two URL spellings of its id keeps the spelling found in the most files. A match takes the file with
    the most rows for it, then the most Min values, then the earliest in POSITION_KINDS. Pos then comes from majority_pos.
    Returns the rows, the rows taken from each file, the rows after URL de-duplication and the rows whose Pos changed.
    """
    rows = pd.concat([frame.assign(file_rank=rank) for rank, frame in enumerate(frames)], ignore_index=True)
    rows["match_id"] = rows["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False)
    rows["player_id"] = rows["Player_Href"].str.extract(r"/players/([0-9a-f]{8})/", expand=False)
    if rows[["match_id", "player_id"]].isna().any(axis=None):
        raise SystemExit("a MatchURL or Player_Href holds no id")
    urls = rows.groupby(["match_id", "MatchURL"])["file_rank"].nunique().rename("files").reset_index()
    spellings = urls.sort_values(["files", "MatchURL"], ascending=[False, True]).drop_duplicates("match_id")["MatchURL"]
    rows = rows[rows["MatchURL"].isin(spellings)]
    deduplicated = len(rows)
    sizes = rows.groupby(["match_id", "file_rank"])["Min"].agg(["size", "count"]).reset_index()
    chosen = sizes.sort_values(["size", "count", "file_rank"], ascending=[False, False, True]).drop_duplicates("match_id")
    kept = rows.merge(chosen[["match_id", "file_rank"]], on=["match_id", "file_rank"])
    if kept.duplicated(["match_id", "player_id"]).any():
        raise SystemExit("a player appears twice in one match")
    voted = majority_pos(kept, rows)
    changed = int((voted["Pos"] != kept["Pos"]).sum())
    kept = voted.sort_values(["Season_End_Year", "Match_Date", "MatchURL", "Team", "Player_Href"])
    taken = [int((kept["file_rank"] == rank).sum()) for rank in range(len(frames))]
    return kept[[*POSITION_COLUMNS, "Pos_Files_Voted", "Pos_Tie"]].reset_index(drop=True), taken, deduplicated, changed


def write_trimmed(frame, target):
    pq.write_table(pa.Table.from_pandas(frame.reset_index(drop=True), preserve_index=False), target, compression="zstd")
    if target.stat().st_size >= MAX_BYTES:
        raise SystemExit(f"{target.name} is over {MAX_BYTES} bytes")
    if not pq.read_table(target).to_pandas().astype(str).equals(frame.reset_index(drop=True).astype(str)):
        raise SystemExit(f"{target.name} did not read back the same")
    print(f"{target.name}\t{len(frame)}\t{frame.shape[1]}\t{target.stat().st_size}", flush=True)


def trim_one(name, columns, originals, out):
    """A plain trim: same rows, same order, fewer columns."""
    frame = read_source(originals / name)
    trimmed = f"{Path(name).stem}.parquet"
    write_trimmed(frame[columns], out / trimmed)
    return {"source": name, "rows": len(frame), "columns": frame.shape[1], "kept_rows": len(frame), "trimmed": trimmed}


def trim_positions(league, originals, out):
    trimmed = f"{league}_M_1st_positions.parquet"
    names = [f"{league}_M_1st_{kind}_player_advanced_match_stats.rds" for kind in POSITION_KINDS]
    frames, source_columns = [], []
    for name in names:
        frame = read_source(originals / name)
        source_columns.append(frame.shape[1])
        # Min is text in some files and float in others. Both casts raise on anything that is not a whole number.
        frames.append(frame[POSITION_COLUMNS].assign(Min=pd.to_numeric(frame["Min"]).astype("Int64")))
    kept, taken, deduplicated, changed = combined_positions(frames)
    write_trimmed(kept, out / trimmed)
    before = sum(len(frame) for frame in frames)
    print(f"{league} positions rows: before {before}, after URL de-duplication {deduplicated}, after {len(kept)}, Pos changed by majority {changed}", flush=True)
    return [
        {"source": name, "rows": len(frame), "columns": columns, "kept_rows": count, "trimmed": trimmed}
        for name, frame, columns, count in zip(names, frames, source_columns, taken)
    ]


def club_rows(league, out):
    """Map Understat clubs to FBref clubs from the matches: same date, same pair of clubs.

    Same names map first. Then each other club takes the FBref club most often found opposite an already mapped
    opponent on the same date. A tied or absent count leaves the club unmapped. Clubs on one side only stay listed.
    """
    shots = pq.read_table(out / f"{Path(SHOT_FILE_OF_LEAGUE[league]).stem}.parquet", columns=["match_id", "date", "home_team", "away_team"]).to_pandas().drop_duplicates("match_id")
    understat = [(date[:10], home, away) for date, home, away in zip(shots["date"], shots["home_team"], shots["away_team"])]
    positions = pq.read_table(out / f"{league}_M_1st_positions.parquet", columns=["MatchURL", "Match_Date", "Team"]).to_pandas().drop_duplicates()
    pairs = {(day, frozenset(teams)) for (day, _), teams in positions.groupby(["Match_Date", "MatchURL"])["Team"]}
    if any(len(pair) != 2 for _, pair in pairs):
        raise SystemExit(f"{league}: an FBref match does not hold two clubs")
    understat_clubs = set(shots["home_team"]) | set(shots["away_team"])
    fbref_clubs = set(positions["Team"])
    mapping = {club: club for club in understat_clubs & fbref_clubs}
    votes = Counter()
    for day, home, away in understat:
        for club, opponent in ((home, away), (away, home)):
            if club not in mapping and opponent in mapping:
                votes.update((club, next(iter(pair - {mapping[opponent]}))) for pair_day, pair in pairs if pair_day == day and mapping[opponent] in pair)
    for club in sorted(understat_clubs - set(mapping)):
        counts = sorted((count for (voted_club, _), count in votes.items() if voted_club == club), reverse=True)
        if counts and (len(counts) == 1 or counts[0] > counts[1]):
            mapping[club] = next(fbref for (voted_club, fbref), count in votes.items() if voted_club == club and count == counts[0])
    linked = Counter()
    for day, home, away in understat:
        if home in mapping and away in mapping and (day, frozenset((mapping[home], mapping[away]))) in pairs:
            linked.update((home, away))
    rows = [(league, club, mapping.get(club, ""), mapping.get(club) == club, linked[club]) for club in sorted(understat_clubs)]
    rows += [(league, "", club, False, 0) for club in sorted(fbref_clubs - set(mapping.values()))]
    return rows


def manifest(records, out):
    versions = f"pandas {pd.__version__}, pyarrow {pa.__version__}, rdata {rdata.__version__}"
    hashes = {name: sha256_of(out / name) for name in sorted({record["trimmed"] for record in records})}
    source_lines = []
    for record in records:
        reader = f"rdata {rdata.__version__}" if record["source"].endswith(".rds") else "not used (CSV, read with pandas)"
        source_lines.append(
            f"| `{record['source']}` | `{SHA256[record['source']]}` | `{record['trimmed']}` | `{hashes[record['trimmed']]}` "
            f"| {record['rows']} | {record['kept_rows']} | {record['columns']} | {reader} |"
        )
    for name, reason in NOT_STORED.items():
        source_lines.append(f"| `{name}` | `{SHA256[name]}` | Not stored: {reason} | | Not read | 0 | Not read | Not read |")
    file_lines = []
    for name in hashes:
        metadata = pq.read_metadata(out / name)
        columns = ", ".join(f"`{column}`" for column in metadata.schema.names)
        file_lines.append(f"| `{name}` | {metadata.num_rows} | {metadata.num_columns} | {(out / name).stat().st_size} | {columns} |")
    return f"""# Stand-in trimmed files

Private. Not for publication. Generated by `scripts/trim_standin.py`, so do not edit by hand.

- Source: private release <{SOURCE_RELEASE}>. Each file is checked against the SHA-256 below before use.
- Reading `.rds`: `rdata.read_rds(path, default_encoding="utf8")`, 1-based index dropped, nulls converted to `pd.NA`.
- Written with: {versions}, Python {platform.python_version()}. Identical bytes were checked on these versions only.
- Repeat: `python3 scripts/trim_standin.py <folder holding the release assets>`.
- Shot, event and HF files keep every source row, in source order.
- Positions files combine five stat files per league. Each match comes whole from one file, so "Rows kept" is what that file gave. Only `Pos` can differ from that file: it is the majority across the files holding the match. Rules and findings: `docs/reports/T7_trim.md`.

## Sources

| Source asset | Original SHA-256 | Trimmed file | Trimmed SHA-256 | Source rows | Rows kept | Source columns | rdata version |
|---|---|---|---|---:|---:|---:|---|
{chr(10).join(source_lines)}

## Trimmed files

| File | Rows | Columns | Bytes | Kept columns |
|---|---:|---:|---:|---|
{chr(10).join(file_lines)}

## Club map

`club_map.csv`, SHA-256 `{sha256_of(out / "club_map.csv")}`. Built from the trimmed shot and positions files: same date, same pair of clubs. An empty club means no match on the other side.
"""


def main(originals, out):
    out.mkdir(parents=True, exist_ok=True)
    for name, expected in SHA256.items():
        if sha256_of(originals / name) != expected:
            raise SystemExit(f"{name} does not match its SHA-256")
    records = [trim_one(name, SHOT_COLUMNS, originals, out) for name in SHOT_FILES]
    for league in LEAGUES:
        records += trim_positions(league, originals, out)
    records += [trim_one(name, EVENT_COLUMNS, originals, out) for name in EVENT_FILES]
    records.append(trim_one("understat_xg_data.csv", HF_TOTALS_COLUMNS, originals, out))
    records.append(trim_one("master_player_stats.csv", HF_MASTER_COLUMNS, originals, out))
    club_map = pd.DataFrame([row for league in LEAGUES for row in club_rows(league, out)], columns=["league", "understat_club", "fbref_club", "exact_name", "linked_matches"])
    club_map.to_csv(out / "club_map.csv", index=False, encoding="utf8")
    (out / "MANIFEST.md").write_text(manifest(records, out), encoding="utf8")


if __name__ == "__main__":
    default_out = Path(__file__).resolve().parent.parent / "data" / "standin"
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else default_out)
