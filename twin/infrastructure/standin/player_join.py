"""Rule 2, id merges and rule 3 of docs/phase-1-plan.md: raw stand-in rows to the final join of shots to FBref players."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pandas as pd

DATA = Path(__file__).resolve().parents[3] / "data" / "standin"
SHOT_FILE_OF_LEAGUE = {"ENG": "epl", "ESP": "la_liga", "FRA": "ligue_1", "GER": "bundesliga", "ITA": "serie_a"}
POOL_FIRST_SEASON, POOL_LAST_SEASON = 2017, 2023
MAX_LINK_GAP_DAYS = 14
LISTED_GAP_DAYS = 1


@dataclass(frozen=True)
class StandinFiles:
    """Where the stand-in files are. The tests point it at the real samples, whose names carry a prefix."""
    folder: Path = DATA
    prefix: str = ""

    def path(self, name):
        return self.folder / f"{self.prefix}{name}"


class DateLinks(NamedTuple):
    """Rule 2's result, keyed by (league, Understat match id)."""
    links: dict
    gap_days: dict
    listed_gaps: list
    equal_gaps: list
    dropped_rows: Counter
    understat_matches: int


class IdMerge(NamedTuple):
    league: str
    year: int
    player: str
    ids: tuple
    survivor: str
    equal_minutes: bool


class RefusedMerge(NamedTuple):
    league: str
    year: int
    player: str
    ids: tuple
    reason: str


def without_tie_breakers(positions):
    """Plan line 121: tie-breaker matches count for neither minutes nor shots, and a shot row can only link to what is left."""
    return positions[~positions["Matchweek"].str.contains("tie-breaker")]


def load_positions(files=StandinFiles()):
    frames = []
    for league in SHOT_FILE_OF_LEAGUE:
        columns = ["MatchURL", "Match_Date", "Matchweek", "Season_End_Year", "Home_Team", "Away_Team", "Team", "Player", "Player_Href", "Pos", "Min"]
        frames.append(pd.read_parquet(files.path(f"{league}_M_1st_positions.parquet"), columns=columns).assign(league=league))
    rows = pd.concat(frames, ignore_index=True)
    rows = without_tie_breakers(rows[rows["Season_End_Year"].between(POOL_FIRST_SEASON + 1, POOL_LAST_SEASON + 1)]).copy()
    rows["match"] = rows["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False)
    rows["fbref_id"] = rows["Player_Href"].str.extract(r"/players/([0-9a-f]{8})/", expand=False)
    return rows


def shot_files(files=StandinFiles(), columns=None):
    """Every season's shot rows. The league comes from the file name, because the `league` column spells one league two ways (T7:59)."""
    frames = [pd.read_parquet(files.path(f"{stem}_shot_data.parquet"), columns=columns).assign(league=league) for league, stem in SHOT_FILE_OF_LEAGUE.items()]
    return pd.concat(frames, ignore_index=True)


def load_shots(files=StandinFiles()):
    rows = shot_files(files, ["season", "match_id", "date", "player", "player_id", "home_team", "away_team", "h_a", "home_away", "result"])
    rows = rows[rows["season"].between(POOL_FIRST_SEASON, POOL_LAST_SEASON)].copy()
    rows["season"] = rows["season"].astype(int)
    rows["player_id"] = rows["player_id"].astype(int)
    # Every row fills exactly one of the two columns: the script prints the check.
    rows["side"] = rows["h_a"].where(rows["h_a"].fillna("") != "", rows["home_away"])
    if not set(rows["side"].fillna("")) <= {"h", "a"}:
        raise SystemExit("a Pool shot row has no side, or an unknown one")
    return rows


def earlier_shots(files=StandinFiles()):
    """Plan line 122: shot rows before the Pool seasons stay unchanged, for later live-Understat use."""
    rows = shot_files(files)
    return rows[rows["season"] < POOL_FIRST_SEASON]


def understat_to_fbref_clubs(files=StandinFiles()):
    club_map = pd.read_csv(files.path("club_map.csv"), keep_default_na=False)
    return {(row.league, row.understat_club): row.fbref_club for row in club_map.itertuples() if row.understat_club and row.fbref_club}


def link_matches(shots, positions, clubs):
    """Rule 2: same home club and same away club, in that order, same season, nearest FBref date, at most 14 days."""
    fbref_matches = positions.drop_duplicates("match")
    by_pair = defaultdict(list)
    for row in fbref_matches.itertuples():
        by_pair[(row.league, row.Season_End_Year, row.Home_Team, row.Away_Team)].append((date.fromisoformat(row.Match_Date[:10]), row.match))
    links, gap_days, listed_gaps, equal_gaps = {}, {}, [], []
    understat_matches = shots.drop_duplicates(["league", "match_id"])
    for row in understat_matches.itertuples():
        pair = (row.league, row.season + 1, clubs.get((row.league, row.home_team)), clubs.get((row.league, row.away_team)))
        day = date.fromisoformat(row.date[:10])
        options = sorted((abs((match_day - day).days), match) for match_day, match in by_pair.get(pair, []))
        if not options or options[0][0] > MAX_LINK_GAP_DAYS:
            continue
        gap, match = options[0]
        key = (row.league, row.match_id)
        links[key], gap_days[key] = match, gap
        if gap > LISTED_GAP_DAYS:
            listed_gaps.append((row.league, row.match_id, gap))
        tied = tuple(found for found_gap, found in options if found_gap == gap)
        if len(tied) > 1:
            equal_gaps.append((row.league, row.match_id, tied))
    dropped_rows = Counter(
        (league, season) for league, season, match_id in zip(shots["league"], shots["season"], shots["match_id"]) if (league, match_id) not in links
    )
    return DateLinks(links, gap_days, listed_gaps, equal_gaps, dropped_rows, len(understat_matches))


def with_date_link(shots, date_links):
    """Plan line 122: only rows in linked matches go on, each with its FBref match and `date_gap_days`. `dropped_rows` counts the rest."""
    keys = list(zip(shots["league"], shots["match_id"]))
    rows = shots[[key in date_links.links for key in keys]]
    keys = list(zip(rows["league"], rows["match_id"]))
    return rows.assign(fbref_match=[date_links.links[key] for key in keys], date_gap_days=[date_links.gap_days[key] for key in keys])


def merge_fbref_ids(positions):
    """Plan line 123 and the survivor rule. Returns the rows under merged ids, every merge and every refused merge."""
    merged, done, refused = positions.copy(), [], []
    for (league, year, _, player), part in positions.groupby(["league", "Season_End_Year", "Team", "Player"]):
        ids = sorted(part["fbref_id"].unique())
        if len(ids) < 2:
            continue
        matches = [set(part.loc[part["fbref_id"] == fbref_id, "match"]) for fbref_id in ids]
        if sum(map(len, matches)) != len(set().union(*matches)):
            refused.append(RefusedMerge(league, year, player, tuple(ids), "matches overlap"))
            continue
        elsewhere = positions[~((positions["league"] == league) & (positions["Season_End_Year"] == year))]
        in_other_seasons = [fbref_id for fbref_id in ids if (elsewhere["fbref_id"] == fbref_id).any()]
        if len(in_other_seasons) > 1:
            refused.append(RefusedMerge(league, year, player, tuple(ids), "both ids in other seasons"))
            continue
        minutes = part.groupby("fbref_id")["Min"].sum()
        survivor = in_other_seasons[0] if in_other_seasons else sorted(ids, key=lambda fbref_id: (-minutes[fbref_id], fbref_id))[0]
        done.append(IdMerge(league, year, player, tuple(ids), survivor, not in_other_seasons and minutes.nunique() == 1))
        merged.loc[(merged["league"] == league) & (merged["Season_End_Year"] == year) & merged["fbref_id"].isin(ids), "fbref_id"] = survivor
    return merged, done, refused


def positions_for_join(files=StandinFiles(), merges=True):
    """One path: the join only ever sees merged ids. Merges off exists only so the script can print the before-merge numbers."""
    positions = load_positions(files)
    return merge_fbref_ids(positions)[0] if merges else positions
