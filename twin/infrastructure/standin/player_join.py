"""Rule 2, id merges and rule 3 of docs/phase-1-plan.md: raw stand-in rows to the final join of shots to FBref players."""
import csv
import html
import io
import re
import unicodedata
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
FOLDED_LETTERS = str.maketrans({"ø": "o", "ð": "d", "đ": "dj", "ı": "i", "ł": "l", "ß": "ss", "æ": "ae", "œ": "oe", "þ": "th"})
MIN_ANCHOR_MATCHES = 2
FULL_JOIN_PERCENT = 95
ATTACKING_POS = {"FW", "LW", "RW", "AM"}
LINK_ITEM_TYPES = {"name_map", "season_anchor"}
ITEM_TYPES = LINK_ITEM_TYPES | {"partial_join", "player_season", "cross_season_ids"}
DECISIONS = {"approve", "reject", "link_to", "merge_ids"}
# Links first, then what is left unjoined, then whole records, so one order holds whatever order Ahmed's rows are in.
ROW_ORDER = {"cross_season_ids": 0, "name_map": 1, "season_anchor": 2, "partial_join": 3, "player_season": 4}


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


class ShotGroup(NamedTuple):
    """One player's shots in one match, as Understat names them. The club comes from the side and the linked match."""
    league: str
    season: int
    match: str
    understat_id: int
    name: str
    club: str

    @property
    def player_season_name(self):
        return self.league, self.season, self.understat_id, self.name

    @property
    def player_season(self):
        return self.league, self.season, self.understat_id


class RosterPlayer(NamedTuple):
    fbref_id: str
    player: str
    compared: str


class PlayerSeasonName(NamedTuple):
    """One review item: a player-season, under one shot name, on one FBref id."""
    league: str
    season: int
    understat_id: int
    name: str
    fbref_id: str


class TwoIds(NamedTuple):
    """A player-season whose exact and step 1 links reach 2+ FBref ids. Plan: left to the id merges."""
    player_season: tuple
    ids: tuple
    different_names: bool


class NameMap(NamedTuple):
    """Step 2's result. `stopped_links` are the links the 2+ FBref ids rule took away, for the review route."""
    links: dict
    undecided: dict
    stopped: Counter
    conflicts: list
    stopped_links: dict
    two_ids: list


class Anchors(NamedTuple):
    """Step 3's result. `barred` holds the links a stopped player-season would have made."""
    links: dict
    stopped: Counter
    barred: dict


class SeasonRow(NamedTuple):
    """One row of the season totals file: the FBref clubs of its team list, and its minutes."""
    clubs: set
    minutes: int


class GuardFacts(NamedTuple):
    """What the minutes guard and the totals lookup read."""
    season_rows: dict
    fbref_minutes: dict
    fbref_names: dict
    fbref_clubs: dict
    shot_names: dict


class Rule3(NamedTuple):
    """Rule 3's links at each step, up to the final join."""
    joined: dict
    name_map: NameMap
    pair_of: dict
    name_map_rows: Counter
    matches_of: Counter
    guard: dict
    after_guard: dict
    anchors: Anchors
    anchor_pair_of: dict
    anchor_rows: Counter
    anchor_matches: Counter
    anchor_guard: dict
    after_anchor: dict
    after_anchor_guard: dict
    collisions: dict
    final: dict


class JoinResult(NamedTuple):
    """The final join, after the review decisions. `rule3` holds the links and verdicts as the decisions left them."""
    rule3: Rule3
    positions: pd.DataFrame
    candidates: list
    flags: dict
    pool: list
    partial: dict
    pool_before: int
    pool_after: int
    joined_before: int
    joined_after: int
    collisions: dict
    merge_ids_rows: list
    merged_collisions: list
    anchors_removed: list
    cross_season_cases: list
    combined_outside_pool: list
    refused_merges: list
    unjoined_listed: list


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
    frames = []
    for league, stem in SHOT_FILE_OF_LEAGUE.items():
        path = files.path(f"{stem}_shot_data.parquet")
        rows = pd.read_parquet(path, columns=columns)
        frames.append(rows.assign(league=league, source_file=path.name, source_row=range(len(rows))))
    return pd.concat(frames, ignore_index=True)


def with_side(rows):
    """`h_a`, or `home_away` where it is empty. D30: a row with no side, or an unknown one, has no club, so it stops the run."""
    side = rows["h_a"].where(rows["h_a"].fillna("") != "", rows["home_away"]).fillna("")
    for row, value in zip(rows.itertuples(), side):
        if value not in ("h", "a"):
            problem = f"unknown side {value!r}" if value else "no side"
            raise SystemExit(f"{row.source_file}: row {row.source_row} has {problem}. Restore the file or re-trim it.")
    return rows.assign(side=side)


def load_shots(files=StandinFiles()):
    rows = shot_files(files, ["season", "match_id", "date", "player", "player_id", "home_team", "away_team", "h_a", "home_away", "result"])
    rows = rows[rows["season"].between(POOL_FIRST_SEASON, POOL_LAST_SEASON)].copy()
    rows["season"] = rows["season"].astype(int)
    rows["player_id"] = rows["player_id"].astype(int)
    return with_side(rows)


def earlier_shots(files=StandinFiles()):
    """Plan line 122: shot rows before the Pool seasons stay unchanged, for later live-Understat use."""
    rows = shot_files(files).drop(columns=["source_file", "source_row"])
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


def decision_key(pair):
    """The key review_decisions.csv uses for a name_map or season_anchor link."""
    return f"{pair.league}|{pair.season}|{pair.understat_id}|{html.unescape(pair.name)}|{pair.fbref_id}"


def link_keys(links):
    """The review keys of links given as {ShotGroup: fbref_id}, one per player-season, shot name and FBref id."""
    return sorted({decision_key(PlayerSeasonName(*group.player_season_name, fbref_id)) for group, fbref_id in links.items()})


def compared_name(name):
    """Step 1: case, accents and punctuation removed, letters NFKD does not reduce folded, a hyphen counts as a space."""
    decomposed = unicodedata.normalize("NFKD", html.unescape(name))
    folded = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().translate(FOLDED_LETTERS)
    return " ".join(re.sub(r"[^\w\s]", "", folded.replace("-", " ")).split())


def is_name_map_candidate(shot_words, roster_words):
    """Step 2: shares the last name, or one name holds the other as whole words, in any order."""
    return roster_words[-1] == shot_words[-1] or set(shot_words) <= set(roster_words) or set(roster_words) <= set(shot_words)


def shot_groups(shots, links, positions):
    """Rows per ShotGroup, in linked matches only. Also returns each linked shot row's group."""
    fbref_matches = positions.drop_duplicates("match").set_index("match")
    home, away = fbref_matches["Home_Team"].to_dict(), fbref_matches["Away_Team"].to_dict()
    rows, keys = Counter(), []
    for league, season, match_id, name, understat_id, side in zip(shots["league"], shots["season"], shots["match_id"], shots["player"], shots["player_id"], shots["side"]):
        match = links.get((league, match_id))
        if match is None:
            keys.append(None)
            continue
        group = ShotGroup(league, season, match, understat_id, name, home[match] if side == "h" else away[match])
        rows[group] += 1
        keys.append(group)
    return rows, keys


def build_rosters(positions):
    rosters = defaultdict(list)
    for match, club, fbref_id, player in zip(positions["match"], positions["Team"], positions["fbref_id"], positions["Player"]):
        rosters[(match, club)].append(RosterPlayer(fbref_id, player, compared_name(player)))
    return rosters


def join_by_name(groups, rosters):
    """Exact, then step 1. Two players matching inside one club and match decides nothing, so that group stays unjoined."""
    joined = {}
    for group in groups:
        roster = rosters[(group.match, group.club)]
        exact = [player for player in roster if player.player == html.unescape(group.name)]
        same = [player for player in roster if player.compared == compared_name(group.name)]
        if len(exact) == 1:
            joined[group] = ("exact", exact[0].fbref_id)
        elif not exact and len(same) == 1:
            joined[group] = ("step 1", same[0].fbref_id)
    return joined


def name_map_links(groups, rosters, joined):
    """Step 2, within the match and club only. Lists what each rule stopped, with the links the 2+ FBref ids rule took away."""
    taken = {(group.match, joined[group][1]) for group in joined}
    claims, undecided, stopped = defaultdict(list), {}, Counter()
    for group in groups:
        if group in joined:
            continue
        shot_words = compared_name(group.name).split()
        options = [player for player in rosters[(group.match, group.club)] if (group.match, player.fbref_id) not in taken and player.compared and shot_words and is_name_map_candidate(shot_words, player.compared.split())]
        if len(options) == 1:
            claims[(group.match, options[0].fbref_id)].append(group)
        elif options:
            undecided[group] = {player.fbref_id for player in options}
            stopped["2+ candidates"] += 1
        else:
            stopped["no candidate"] += 1
    links = {}
    for (_, fbref_id), claimants in claims.items():
        if len(claimants) > 1:
            stopped["two shot names on one roster player"] += len(claimants)
        else:
            links[claimants[0]] = fbref_id
    ids_of_player_season = defaultdict(set)
    for group, link in joined.items():
        ids_of_player_season[group.player_season].add(link[1])
    for group, fbref_id in links.items():
        ids_of_player_season[group.player_season].add(fbref_id)
    # Only step 2 links stop. Exact and step 1 links stay, and two ids with no step 2 link are left to the id merges.
    conflicts = sorted({group.player_season for group in links if len(ids_of_player_season[group.player_season]) > 1})
    stopped["player-seasons reaching 2+ FBref ids"] = len(conflicts)
    stopped_links = {group: fbref_id for group, fbref_id in links.items() if group.player_season in conflicts}
    return NameMap({group: fbref_id for group, fbref_id in links.items() if group not in stopped_links}, undecided, stopped, conflicts, stopped_links, two_id_player_seasons(joined, rosters, conflicts))


def two_id_player_seasons(joined, rosters, conflicts):
    """Q3: player-seasons whose exact and step 1 links alone reach 2+ FBref ids, and whether those ids carry different names."""
    ids_of, names_of = defaultdict(set), defaultdict(set)
    for group, (_, fbref_id) in joined.items():
        ids_of[group.player_season].add(fbref_id)
        names_of[fbref_id] |= {player.player for player in rosters[(group.match, group.club)] if player.fbref_id == fbref_id}
    return [TwoIds(key, tuple(sorted(ids)), len(set.union(*(names_of[fbref_id] for fbref_id in ids))) > 1) for key, ids in sorted(ids_of.items()) if len(ids) > 1 and key not in conflicts]


def links_after_step_2(joined, name_map):
    return {**joined, **{group: ("map", fbref_id) for group, fbref_id in name_map.links.items()}}


def season_anchor_links(undecided, linked, stopped_player_seasons=()):
    """Step 3: in a match with 2+ candidates, the one FBref id the same Understat id links to in 2+ other matches of that season and club.

    Anchors come only from links that survived the guard, and one pass only, so an anchor link never anchors another.
    A stopped player-season gains no link: what it would have made is listed as barred, each with its own key (Q4).
    """
    matches_of_id = defaultdict(lambda: defaultdict(set))
    for group, (step, fbref_id) in linked.items():
        if step != "season_anchor":
            matches_of_id[(group.league, group.season, group.understat_id, group.club)][fbref_id].add(group.match)
    taken = {(group.match, link[1]) for group, link in linked.items()}
    claims, stopped = defaultdict(list), Counter()
    for group, candidates in undecided.items():
        ids = matches_of_id.get((group.league, group.season, group.understat_id, group.club), {})
        if len(ids) != 1:
            stopped["no links for that club" if not ids else "links to 2+ FBref ids"] += 1
            continue
        fbref_id, matches = next(iter(ids.items()))
        if len(matches - {group.match}) < MIN_ANCHOR_MATCHES:
            stopped[f"under {MIN_ANCHOR_MATCHES} other matches"] += 1
        elif fbref_id not in candidates:
            stopped["id not a candidate"] += 1
        elif (group.match, fbref_id) in taken:
            stopped["id already linked in that match"] += 1
        else:
            claims[(group.match, fbref_id)].append(group)
    links = {}
    for (_, fbref_id), claimants in claims.items():
        if len(claimants) > 1:
            stopped["two shot names on one roster player"] += len(claimants)
        else:
            links[claimants[0]] = fbref_id
    barred = {group: fbref_id for group, fbref_id in links.items() if group.player_season in stopped_player_seasons}
    return Anchors({group: fbref_id for group, fbref_id in links.items() if group not in barred}, stopped, barred)


def minutes_limit(understat_minutes, fbref_minutes):
    return max(90, 0.1 * max(understat_minutes, fbref_minutes))


def season_rows_by_name(clubs, files=StandinFiles()):
    """The season totals file per league, Understat season and name."""
    rows = pd.read_parquet(files.path("understat_xg_data.parquet"), columns=["player_name", "team", "league", "season", "minutes"])
    index = defaultdict(list)
    for league, season, name, team, minutes in zip(rows["league"], rows["season"], rows["player_name"], rows["team"], rows["minutes"]):
        league = "ENG" if league == "EPL" else league
        index[(league, int(season[:4]), html.unescape(name))].append(SeasonRow({clubs.get((league, part.strip())) for part in team.split(",")}, int(minutes)))
    return index


def guard_facts(positions, shots, season_rows):
    fbref_minutes = {key: int(value) for key, value in positions.groupby(["league", "Season_End_Year", "fbref_id"])["Min"].sum().items()}
    fbref_names = positions.groupby(["league", "Season_End_Year", "fbref_id"])["Player"].agg(lambda names: sorted(set(names))).to_dict()
    fbref_clubs, shot_names = defaultdict(set), defaultdict(set)
    for league, year, club, fbref_id in zip(positions["league"], positions["Season_End_Year"], positions["Team"], positions["fbref_id"]):
        fbref_clubs[(league, year, fbref_id)].add(club)
    for league, season, understat_id, name in zip(shots["league"], shots["season"], shots["player_id"], shots["player"]):
        shot_names[(league, season, understat_id)].add(html.unescape(name))
    return GuardFacts(season_rows, fbref_minutes, fbref_names, fbref_clubs, shot_names)


def season_totals_row(facts, league, season, shot_names, fbref_id):
    """Q5, the one lookup: the player-season's shot names, then the linked FBref name. If 2+ rows match, the one with the linked club. Else None."""
    year = season + 1
    rows = [row for name in sorted(shot_names) for row in facts.season_rows.get((league, season, name), [])]
    if not rows:
        rows = [row for name in facts.fbref_names.get((league, year, fbref_id), []) for row in facts.season_rows.get((league, season, html.unescape(name)), [])]
    if len(rows) > 1:
        rows = [row for row in rows if row.clubs & facts.fbref_clubs.get((league, year, fbref_id), set())]
    return rows[0] if len(rows) == 1 else None


def minutes_guard(pairs, facts):
    """One verdict per player-season name and FBref id: agree, disagree or none, with both minutes. Only a review decision can make it `approved`."""
    results = {}
    for pair in sorted(pairs):
        names = facts.shot_names.get((pair.league, pair.season, pair.understat_id), {html.unescape(pair.name)})
        row = season_totals_row(facts, pair.league, pair.season, names, pair.fbref_id)
        fbref = facts.fbref_minutes.get((pair.league, pair.season + 1, pair.fbref_id), 0)
        if row is None:
            results[pair] = ("none", None, fbref)
            continue
        results[pair] = ("agree" if abs(row.minutes - fbref) <= minutes_limit(row.minutes, fbref) else "disagree", row.minutes, fbref)
    return results


def guard_review_list(rule3):
    """Plan line 132: what the guard took away, approved or could not check, on name map and anchor links alike, by verdict."""
    listed = defaultdict(list)
    for guard in (rule3.guard, rule3.anchor_guard):
        for pair, verdict in guard.items():
            if verdict[0] != "agree":
                listed[verdict[0]].append(pair)
    return listed


def anchor_listing(rule3):
    """Plan line 133: every `season_anchor` link, as (pair, verdict, rows, matches), whether or not it survived the guard."""
    return [(pair, rule3.anchor_guard[pair], rule3.anchor_rows[pair], rule3.anchor_matches[pair]) for pair in sorted(rule3.anchor_rows)]


def id_collisions(joined):
    """Two Understat ids on one FBref id in a league-season."""
    ids = defaultdict(set)
    for group, (_, fbref_id) in joined.items():
        ids[(group.league, group.season, fbref_id)].add(group.understat_id)
    return {key: sorted(found) for key, found in sorted(ids.items()) if len(found) > 1}


def colliding_player_seasons(collisions):
    return {(league, season, understat_id) for (league, season, _), ids in collisions.items() for understat_id in ids}


def rule3_links(rows_of, rosters, facts):
    """Exact, step 1, step 2, the guard, step 3, the guard on its links, then id collisions. Plan lines 129 to 136, in that order."""
    groups = sorted(rows_of)
    joined = join_by_name(groups, rosters)
    name_map = name_map_links(groups, rosters, joined)
    pair_of = {group: PlayerSeasonName(*group.player_season_name, fbref_id) for group, fbref_id in name_map.links.items()}
    name_map_rows, matches_of = Counter(), Counter()
    for group, pair in pair_of.items():
        name_map_rows[pair] += rows_of[group]
        matches_of[pair] += 1
    guard = minutes_guard(name_map_rows, facts)
    after_step_2 = links_after_step_2(joined, name_map)
    after_guard = {group: link for group, link in after_step_2.items() if link[0] != "map" or guard[pair_of[group]][0] != "disagree"}
    anchors = season_anchor_links(name_map.undecided, after_guard, name_map.conflicts)
    anchor_pair_of = {group: PlayerSeasonName(*group.player_season_name, fbref_id) for group, fbref_id in anchors.links.items()}
    anchor_rows, anchor_matches = Counter(), Counter()
    for group, pair in anchor_pair_of.items():
        anchor_rows[pair] += rows_of[group]
        anchor_matches[pair] += 1
    anchor_guard = minutes_guard(anchor_rows, facts)
    after_anchor = {**after_guard, **{group: ("season_anchor", fbref_id) for group, fbref_id in anchors.links.items()}}
    after_anchor_guard = {group: link for group, link in after_anchor.items() if link[0] != "season_anchor" or anchor_guard[anchor_pair_of[group]][0] != "disagree"}
    collisions = id_collisions(after_anchor_guard)
    colliding = colliding_player_seasons(collisions)
    final = {group: link for group, link in after_anchor_guard.items() if group.player_season not in colliding}
    return Rule3(joined, name_map, pair_of, name_map_rows, matches_of, guard, after_guard, anchors, anchor_pair_of, anchor_rows, anchor_matches, anchor_guard, after_anchor, after_anchor_guard, collisions, final)


def name_map_file_rows(rule3, name_of):
    """Plan line 135: one row per kept `map` player-season, for `name_map.csv` and its sample."""
    kept = {rule3.pair_of[group] for group, link in rule3.final.items() if link[0] == "map"}
    rows = []
    for pair in sorted(kept):
        check, understat, fbref = rule3.guard[pair]
        rows.append([pair.league, pair.season, pair.understat_id, html.unescape(pair.name), pair.fbref_id, name_of(pair.fbref_id), rule3.name_map_rows[pair], rule3.matches_of[pair], "" if understat is None else understat, fbref, check])
    return rows


def check_sample_pairs(drawn, committed_text):
    """D12: Ahmed's check (b) rests on these 50 pairs, so a new draw stops the run. `drawn` holds (league, season, Understat id, FBref id)."""
    committed = {(row["league"], int(row["understat_season"]), int(row["understat_id"]), row["fbref_id"]) for row in csv.DictReader(io.StringIO(committed_text))}
    if drawn != committed:
        raise SystemExit(f"docs/reports/name_map_sample.csv: the drawn pairs differ from the committed file: {sorted(drawn ^ committed)}. A new draw needs Ahmed's approval in a commit. Way back: git checkout that file.")


def join_counts(rows_of, stage):
    """Understat player-season to (rows joined at that stage, rows in linked matches)."""
    joined, total = Counter(), Counter()
    for group, rows in rows_of.items():
        key = (group.league, group.season, group.understat_id)
        total[key] += rows
        joined[key] += rows if group in stage else 0
    return {key: (joined[key], total[key]) for key in sorted(total)}


def partial_joins(rows_of, final):
    """Player-seasons with under FULL_JOIN_PERCENT of their linked shot rows joined."""
    return {key: counts for key, counts in join_counts(rows_of, final).items() if counts[0] * 100 < counts[1] * FULL_JOIN_PERCENT}


def pool_candidates(positions, files=StandinFiles()):
    """PlayerSeasons at 900+ minutes with attacking minutes above other minutes, substitute appearances ignored."""
    events = pd.concat([pd.read_parquet(files.path(f"{league}_M_1st_match_summary.parquet"), columns=["MatchURL", "Team", "Event_Type", "Event_Players"]) for league in SHOT_FILE_OF_LEAGUE])
    substitutes = events[events["Event_Type"] == "Substitute"].drop_duplicates(["MatchURL", "Team", "Event_Players"])
    came_on = set(zip(substitutes["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False), substitutes["Team"], substitutes["Event_Players"].str.split(" for ").str[0].str.strip()))
    is_substitute = pd.Series([key in came_on for key in zip(positions["match"], positions["Team"], positions["Player"])], index=positions.index)
    is_attacking = pd.Series([bool(set(pos.split(",")) & ATTACKING_POS) for pos in positions["Pos"]], index=positions.index)
    keys = ["league", "Season_End_Year", "fbref_id"]
    totals = pd.DataFrame({
        "total": positions.groupby(keys)["Min"].sum(),
        "attacking": positions[~is_substitute & is_attacking].groupby(keys)["Min"].sum(),
        "other": positions[~is_substitute & ~is_attacking].groupby(keys)["Min"].sum(),
    }).fillna(0)
    return sorted(totals[(totals["total"] >= 900) & (totals["attacking"] > totals["other"])].index)


def review_flags(candidates, final, partial, two_ids):
    """What holds each PlayerSeason, keyed (league, FBref year, FBref id). Plan line 137 and Q3. A held PlayerSeason's metrics are not used."""
    flags = defaultdict(set)
    ids_of = defaultdict(set)
    for group, link in final.items():
        ids_of[group.player_season].add(link[1])
    with_shots = {(key[0], key[1] + 1, fbref_id) for key, ids in ids_of.items() for fbref_id in ids}
    for candidate in candidates:
        if candidate not in with_shots:
            flags[candidate].add("no joined shots")
    for key in partial:
        for fbref_id in ids_of[key]:
            flags[(key[0], key[1] + 1, fbref_id)].add("partial_join")
    candidate_set = set(candidates)
    for case in two_ids:
        if case.different_names:
            for fbref_id in case.ids:
                if (case.player_season[0], case.player_season[1] + 1, fbref_id) in candidate_set:
                    flags[(case.player_season[0], case.player_season[1] + 1, fbref_id)].add("two ids")
    return dict(flags)


def pool_of(candidates, flags):
    """A flagged candidate stays out of the Pool until Ahmed reviews it."""
    return [candidate for candidate in candidates if candidate not in flags]


def read_review_decisions(path=DATA / "review_decisions.csv"):
    """Every row of Ahmed's file, checked on its own. The stops that need the join's output are in `finish_join`."""
    # utf-8-sig: spreadsheets save this hand-edited file with a byte order mark.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))
    for row in decisions:
        if row["item_type"] not in ITEM_TYPES or row["decision"] not in DECISIONS:
            raise SystemExit(f"{path.name}: unknown item_type or decision: {row}")
        needs_id = row["decision"] in ("link_to", "merge_ids")
        if needs_id != bool(row["fbref_id"]):
            raise SystemExit(f"{path.name}: `{row['decision']}` {'needs' if needs_id else 'takes no'} fbref_id: {row}")
        if row["decision"] == "merge_ids" and row["item_type"] == "player_season":
            raise SystemExit(f"{path.name}: merge_ids does not apply to player_season: {row}")
        if row["item_type"] == "cross_season_ids" and row["decision"] != "approve":
            raise SystemExit(f"{path.name}: cross_season_ids takes only approve: {row}")
    repeated = sorted(key for key, count in Counter((row["item_type"], row["key"]) for row in decisions).items() if count > 1)
    if repeated:
        raise SystemExit(f"{path.name}: two rows on one key: {repeated}")
    return decisions


def partial_join_key(player_season):
    return "|".join(str(part) for part in player_season)


def player_season_key(fbref_key):
    """(league, FBref year, FBref id) as a review key. Its season is the Understat one, so one season has one number in the whole file."""
    league, year, fbref_id = fbref_key
    return f"{league}|{year - 1}|{fbref_id}"


def stop(message):
    raise SystemExit(f"review_decisions.csv: {message}")


def link_items(rule3):
    """Every link a row can name, by (item_type, key): those rule 3 made, including any the guard, the stop, the bar or a collision took away."""
    items = defaultdict(dict)
    for group, pair in rule3.pair_of.items():
        items[("name_map", decision_key(pair))][group] = ("map", pair.fbref_id)
    for group, fbref_id in rule3.name_map.stopped_links.items():
        items[("name_map", decision_key(PlayerSeasonName(*group.player_season_name, fbref_id)))][group] = ("map", fbref_id)
    for (league, season, fbref_id), ids in rule3.collisions.items():
        for group, link in rule3.after_anchor_guard.items():
            if link[1] == fbref_id and group.league == league and group.season == season and group.understat_id in ids:
                items[("name_map", decision_key(PlayerSeasonName(*group.player_season_name, fbref_id)))][group] = link
    for links in (rule3.anchors.links, rule3.anchors.barred):
        for group, fbref_id in links.items():
            items[("season_anchor", decision_key(PlayerSeasonName(*group.player_season_name, fbref_id)))][group] = ("season_anchor", fbref_id)
    return items


def understat_ids_on(fbref_key, links):
    """The player-seasons whose links reach this PlayerSeason, keyed as `partial_join` is."""
    league, year, fbref_id = fbref_key
    return {group.player_season for group, link in links.items() if link[1] == fbref_id and group.league == league and group.season == year - 1}


def check_cases_agree(rows, links, refused):
    """D36 and D37: rows on different keys for one case must agree. The two-row rule only sees one key."""
    by_key = {(row["item_type"], row["key"]): row for row in rows}
    for row in rows:
        if row["item_type"] != "player_season":
            continue
        league, season, fbref_id = row["key"].split("|")
        for player_season in understat_ids_on((league, int(season) + 1, fbref_id), links):
            other = by_key.get(("partial_join", partial_join_key(player_season)))
            if other and {row["decision"], other["decision"]} == {"approve", "reject"}:
                stop(f"{row['decision']} on player_season {row['key']} and {other['decision']} on partial_join {other['key']} disagree. Keep one.")
    for case in refused:
        keys = [player_season_key((case.league, case.year, fbref_id)) for fbref_id in case.ids]
        found = [by_key[("player_season", key)] for key in keys if ("player_season", key) in by_key]
        if any(row["decision"] == "approve" for row in found):
            stop(f"approve on a refused merge {keys}: use reject, or link_to to combine the ids")
        if len(found) > 1 and any(row["decision"] == "link_to" for row in found):
            stop(f"rows on one refused merge disagree: {[(row['key'], row['decision'], row['fbref_id']) for row in found]}. Keep one.")


def drop_anchors_without_evidence(rule3, rows, items, links):
    """Step 3 again, without the links Ahmed took away or moved: an anchor resting on them goes, unless its own row kept it. Returns what went, for the report."""
    changed = {group for row in rows if row["item_type"] in LINK_ITEM_TYPES and row["decision"] != "approve" for group in items[(row["item_type"], row["key"])]}
    if not changed:
        return []
    own_rows = {group for row in rows if row["item_type"] == "season_anchor" for group in items[("season_anchor", row["key"])]}
    evidence = {group: link for group, link in rule3.after_guard.items() if group not in changed}
    still_anchored = season_anchor_links(rule3.name_map.undecided, evidence, rule3.name_map.conflicts).links
    removed = [group for group, link in links.items() if link[0] == "season_anchor" and group not in still_anchored and group not in own_rows]
    for group in removed:
        del links[group]
    return sorted(removed)


def finish_join(rule3, rows_of, rosters, positions, decisions, refused, candidates_of, facts, merges_on=True):
    """Plan lines 142 to 146: apply Ahmed's rows after rule 3, then every check again. Rows are sorted, and the checks run after them all, so order never matters."""
    rows = sorted(decisions, key=lambda row: (ROW_ORDER[row["item_type"]], row["key"]))
    candidates = candidates_of(positions)
    candidate_set = set(candidates)
    partial_before = partial_joins(rows_of, rule3.final)
    flags_before = review_flags(candidates, rule3.final, partial_before, two_id_player_seasons(rule3.final, rosters, []))
    items = link_items(rule3)
    counts = join_counts(rows_of, rule3.final)
    partial_keys = {partial_join_key(key): key for key, (found, total) in counts.items() if found < total}
    season_keys = {player_season_key(key): key for key in flags_before if key in candidate_set}
    season_keys.update({player_season_key((case.league, case.year, fbref_id)): (case.league, case.year, fbref_id) for case in refused for fbref_id in case.ids})
    in_league_season = set(zip(positions["league"], positions["Season_End_Year"], positions["fbref_id"]))
    ids_at_club = defaultdict(set)
    for match, club, fbref_id in zip(positions["match"], positions["Team"], positions["fbref_id"]):
        ids_at_club[(match, club)].add(fbref_id)

    def key_exists(row):
        kind, key = row["item_type"], row["key"]
        return (kind, key) in items if kind in LINK_ITEM_TYPES else key in partial_keys if kind == "partial_join" else key in season_keys if kind == "player_season" else True

    if not merges_on:
        # The file's keys name merged ids, and this run exists only for the before-merge numbers (D21).
        rows = [row for row in rows if key_exists(row) and (not row["fbref_id"] or (row["key"].split("|")[0], int(row["key"].split("|")[1]) + 1, row["fbref_id"]) in in_league_season)]
    for row in rows:
        kind, key = row["item_type"], row["key"]
        if not key_exists(row):
            stop(f"stale decision, key not in the data: {kind} {key}")
        if row["fbref_id"]:
            league, season = key.split("|")[:2]
            if (league, int(season) + 1, row["fbref_id"]) not in in_league_season:
                stop(f"{row['decision']} on {key}: {row['fbref_id']} is not in that league-season")
    check_cases_agree(rows, rule3.final, refused)

    def must(holds, message):
        """The merges-off run exists only for the before-merge numbers: a row that is good on merged ids must not stop it (D21)."""
        if merges_on and not holds:
            stop(message)

    # One group can sit under two keys. `approve` on one with `link_to` on the other would split the player, `reject` would cancel the `link_to` with no error, and two `link_to` rows with different ids would let the last one win (spec:115).
    kept_or_rejected_rows = [row for row in rows if row["item_type"] in LINK_ITEM_TYPES and row["decision"] in ("approve", "reject")]
    moved_rows = [row for row in rows if row["item_type"] in LINK_ITEM_TYPES and row["decision"] in ("link_to", "merge_ids")]
    for index, row in enumerate(moved_rows):
        for other in [*kept_or_rejected_rows, *(later for later in moved_rows[index + 1:] if later["fbref_id"] != row["fbref_id"])]:
            must(items[(row["item_type"], row["key"])].keys().isdisjoint(items[(other["item_type"], other["key"])]), f"{row['decision']} on {row['item_type']} {row['key']} and {other['decision']} on {other['item_type']} {other['key']} name one shot group. Keep one.")

    def move_rows(groups, row):
        for group in groups:
            must(row["fbref_id"] in ids_at_club[(group.match, group.club)], f"{row['decision']} on {row['key']}: {row['fbref_id']} has no FBref row in match {group.match} for {group.club}")
        links.update({group: ("reviewed", row["fbref_id"]) for group in groups})

    links, guard, pair_of = dict(rule3.final), dict(rule3.guard), dict(rule3.pair_of)
    name_map_rows, matches_of = Counter(rule3.name_map_rows), Counter(rule3.matches_of)
    anchor_guard, anchor_pair_of = dict(rule3.anchor_guard), dict(rule3.anchor_pair_of)
    anchor_rows, anchor_matches = Counter(rule3.anchor_rows), Counter(rule3.anchor_matches)
    # A rejected link stays out, whichever other row could bring its rows back.
    rejected_groups = {group for row in rows if row["item_type"] in LINK_ITEM_TYPES and row["decision"] == "reject" for group in items[(row["item_type"], row["key"])]}
    approved_partial, kept_partial, approved_seasons, rejected_seasons, unjoined_listed = set(), set(), set(), set(), []
    merged, settled, decided, combine, merge_rows, allowed_ids, merged_collisions = set(), set(), defaultdict(set), {}, [], set(), []
    anchors_removed, anchors_checked = [], False
    approved_by_row = {"map": set(), "season_anchor": set()}
    for row in rows:
        kind, key, verdict = row["item_type"], row["key"], row["decision"]
        if kind in LINK_ITEM_TYPES:
            # One group can sit under two keys, so a row on the other key must not bring a rejected link back.
            found = {group: link for group, link in items[(kind, key)].items() if verdict == "reject" or group not in rejected_groups}
            league, season = key.split("|")[0], int(key.split("|")[1])
            link_fbref = key.rsplit("|", 1)[1]
            collision = (league, season, link_fbref)
            if collision in rule3.collisions:
                # `approve` gives the id to this Understat id. Any other row settles only this Understat id, so the collision stays listed until each has a row.
                if verdict == "approve" and found:
                    settled.add(collision)
                else:
                    decided[collision].add(int(key.split("|")[2]))
            if verdict == "approve":
                links.update(found)
                for group, link in found.items():
                    if link[0] in approved_by_row:
                        approved_by_row[link[0]].add(PlayerSeasonName(*group.player_season_name, link[1]))
                    if link[0] == "map":
                        pair = PlayerSeasonName(*group.player_season_name, link[1])
                        if group not in pair_of:
                            pair_of[group] = pair
                            name_map_rows[pair] += rows_of[group]
                            matches_of[pair] += 1
                        if pair not in guard:
                            guard.update(minutes_guard([pair], facts))
                        if guard[pair][0] == "disagree":
                            guard[pair] = ("approved", *guard[pair][1:])
                    elif link[0] == "season_anchor":
                        pair = PlayerSeasonName(*group.player_season_name, link[1])
                        if group not in anchor_pair_of:
                            anchor_pair_of[group] = pair
                            anchor_rows[pair] += rows_of[group]
                            anchor_matches[pair] += 1
                        if pair not in anchor_guard:
                            anchor_guard.update(minutes_guard([pair], facts))
                        if anchor_guard[pair][0] == "disagree":
                            anchor_guard[pair] = ("approved", *anchor_guard[pair][1:])
            elif verdict == "reject":
                for group in found:
                    links.pop(group, None)
            else:
                move_rows(found, row)
                if verdict == "merge_ids":
                    merge_rows.append(row)
                    merged.add((league, season, row["fbref_id"]))
                    collision_key = (league, season, row["fbref_id"])
                    collision_ids = rule3.collisions.get(collision_key, [])
                    for group, link in rule3.after_anchor_guard.items():
                        if group.league == league and group.season == season and group.understat_id in collision_ids and link[1] == row["fbref_id"] and group not in rejected_groups:
                            links.setdefault(group, link)
                    if collision_ids and (collision_key, collision_ids) not in merged_collisions:
                        merged_collisions.append((collision_key, collision_ids))
        elif kind == "partial_join":
            if not anchors_checked:
                anchors_checked = True
                anchors_removed = drop_anchors_without_evidence(rule3, rows, items, links)
            player_season = partial_keys[key]
            flagged = player_season in partial_before
            if verdict == "approve":
                must(flagged, f"approve on partial_join {key}: it holds no flag to clear. Use reject to leave its rows unjoined. link_to joins them only if its id has a row at that club in every one of their matches")
                approved_partial.add(player_season)
            elif verdict == "reject":
                (kept_partial.add(player_season) if flagged else unjoined_listed.append(player_season))
            else:
                unjoined = [group for group in rows_of if group.player_season == player_season and group not in links and group not in rejected_groups]
                must(unjoined, f"stale decision: {verdict} on partial_join {key}: no unjoined rows are left for it")
                move_rows(unjoined, row)
                if verdict == "merge_ids":
                    merge_rows.append(row)
                    merged.add((player_season[0], player_season[1], row["fbref_id"]))
        elif kind == "player_season":
            season_key = season_keys[key]
            if verdict == "approve":
                approved_seasons.add(season_key)
            elif verdict == "reject":
                if season_key in flags_before:
                    rejected_seasons.add(season_key)
            else:
                combine[season_key] = row["fbref_id"]
        else:
            allowed_ids.add(key)

    if not anchors_checked:
        anchors_removed = drop_anchors_without_evidence(rule3, rows, items, links)

    # Fixed before any combine, so the result does not depend on how the ids sort: the links that stand, and those rule 3's guard took unless a collision holds the player-season (D45).
    colliding = colliding_player_seasons(rule3.collisions)
    combine_rechecks = {
        step: {group for group, link in links.items() if link[0] == step} | {group for group, pair in first_pairs.items() if group not in links and group not in rejected_groups and group.player_season not in colliding and first_verdicts[pair][0] == "disagree"}
        for step, first_pairs, first_verdicts in (("map", rule3.pair_of, rule3.guard), ("season_anchor", rule3.anchor_pair_of, rule3.anchor_guard))
    }
    linked_before_combines = set(links)
    for (league, year, old_id), new_id in sorted(combine.items()):
        if (league, year, new_id) in combine:
            stop(f"link_to on {player_season_key((league, year, old_id))} names {new_id}, and {player_season_key((league, year, new_id))} has its own link_to. Name the id the record ends under.")
        here = (positions["league"] == league) & (positions["Season_End_Year"] == year)
        if set(positions.loc[here & (positions["fbref_id"] == old_id), "match"]) & set(positions.loc[here & (positions["fbref_id"] == new_id), "match"]):
            stop(f"link_to on {player_season_key((league, year, old_id))}: {old_id} and {new_id} share a match, so they are two players")
        positions = positions.copy()
        positions.loc[here & (positions["fbref_id"] == old_id), "fbref_id"] = new_id
        links = {group: (link[0], new_id) if link[1] == old_id and group.league == league and group.season == year - 1 else link for group, link in links.items()}
        # Every check runs again on the combined record, the guard with both ids' minutes, names and clubs.
        old_key, new_key = (league, year, old_id), (league, year, new_id)
        facts = facts._replace(
            fbref_minutes={**facts.fbref_minutes, new_key: facts.fbref_minutes.get(new_key, 0) + facts.fbref_minutes.get(old_key, 0)},
            fbref_names={**facts.fbref_names, new_key: sorted({*facts.fbref_names.get(new_key, []), *facts.fbref_names.get(old_key, [])})},
            fbref_clubs={**facts.fbref_clubs, new_key: {*facts.fbref_clubs.get(new_key, ()), *facts.fbref_clubs.get(old_key, ())}},
        )
        for step, pairs, verdicts, row_counts, match_counts in (("map", pair_of, guard, name_map_rows, matches_of), ("season_anchor", anchor_pair_of, anchor_guard, anchor_rows, anchor_matches)):
            # Read before any row moves: one approval covers every group of a pair, on either id. From the rows too, because a verdict reads `approved` only if it was `disagree` when the row applied.
            approved_pairs = approved_by_row[step] | {pair for pair, verdict in verdicts.items() if verdict[0] == "approved"}
            # The approval moves with its pair, so a later combine under new_id still sees it.
            approved_pairs |= {pair._replace(fbref_id=new_id) for pair in approved_pairs if pair.fbref_id == old_id and pair.league == league and pair.season == year - 1}
            approved_by_row[step] = approved_pairs
            for group, pair in list(pairs.items()):
                if pair.fbref_id not in (old_id, new_id) or group.league != league or group.season != year - 1:
                    continue
                new_pair = pair._replace(fbref_id=new_id)
                if new_pair != pair:
                    pairs[group] = new_pair
                    row_counts[new_pair] += rows_of[group]
                    row_counts[pair] -= rows_of[group]
                    match_counts[new_pair] += 1
                    match_counts[pair] -= 1
                verdict = minutes_guard([new_pair], facts)[new_pair]
                kept_by_ahmed = new_pair in approved_pairs and verdict[0] == "disagree"
                verdicts[new_pair] = ("approved", *verdict[1:]) if kept_by_ahmed else verdict
                if group not in combine_rechecks[step]:
                    continue
                if verdicts[new_pair][0] == "disagree":
                    links.pop(group, None)
                else:
                    links[group] = (step, new_id)
            for pair in [pair for pair in verdicts if pair.fbref_id == old_id and pair.league == league and pair.season == year - 1]:
                del verdicts[pair]

    def combines_onto(group):
        return [f"link_to on player_season {player_season_key(key)} to {new_id}" for key, new_id in sorted(combine.items()) if new_id == links[group][1] and key[:2] == (group.league, group.season + 1)]

    # A combine must not join rows a `reject` left unjoined (D46). The merges-off run does not stop (D21), so the rows stay out there.
    left_unjoined = {partial_keys[row["key"]] for row in rows if row["item_type"] == "partial_join" and row["decision"] == "reject"}
    for group in sorted(links.keys() - linked_before_combines):
        if group.player_season in left_unjoined:
            must(False, f"{' and '.join(combines_onto(group))} would join {group.name} ({partial_join_key(group.player_season)}) in match {group.match}, which reject on partial_join {partial_join_key(group.player_season)} left unjoined. Keep one.")
            del links[group]

    collisions_now = id_collisions(links)
    for key, ids in collisions_now.items():
        # Both runs stop: two players on one id is a wrong join, even in the before-merge numbers (D47).
        if key not in merged:
            stop(f"two Understat ids {ids} on FBref id {key[2]} in {key[0]} {key[1]}: only a merge_ids row may do that")
    for key in merged:
        must(key in collisions_now, f"merge_ids on {key} puts no second Understat id on that FBref id")

    # Again on the final links, because a decision or a combine can reach an id rule 3 did not. Merges-on only, so a row good only on merged ids does not stop the other run (D21).
    if merges_on:
        check_cases_agree(rows, links, refused)

    for season_key in rejected_seasons:
        kept_partial |= understat_ids_on(season_key, links)

    # partial_join holds every id its player-season reaches, so it clears only when all of those ids are approved. Each id's own flag clears below.
    joined_ids = defaultdict(set)
    for group, link in links.items():
        joined_ids[group.player_season].add(link[1])
    for league, year, fbref_id in approved_seasons:
        for player_season in understat_ids_on((league, year, fbref_id), links):
            if all((league, year, found) in approved_seasons for found in joined_ids[player_season]):
                approved_partial.add(player_season)

    partial = partial_joins(rows_of, links)
    for player_season in approved_partial:
        partial.pop(player_season, None)
    new_counts = join_counts(rows_of, links)
    for player_season in kept_partial:
        partial[player_season] = new_counts[player_season]
    candidates_after = candidates_of(positions) if combine else candidates
    # Worked out on the links as they now stand, so a second id from a decision holds a candidate as one from rule 3 does.
    flags = review_flags(candidates_after, links, partial, two_id_player_seasons(links, build_rosters(positions) if combine else rosters, []))
    for season_key in approved_seasons:
        must("no joined shots" not in flags.get(season_key, ()), f"approve on {player_season_key(season_key)}: it has no joined shots, so its shot metrics would read as zero. Its shots need a partial_join row with link_to")
        flags.pop(season_key, None)
    for season_key in rejected_seasons:
        flags.setdefault(season_key, set()).add("rejected")

    cross_season_cases = []
    if merges_on:
        fbref_ids_of = defaultdict(set)
        for group, link in links.items():
            fbref_ids_of[group.understat_id].add(link[1])
        for key in sorted(allowed_ids):
            if len(fbref_ids_of[int(key)]) < 2:
                stop(f"stale decision: cross_season_ids {key} does not reach 2+ FBref ids")
        for understat_id, ids in sorted(fbref_ids_of.items()):
            if len(ids) > 1:
                if str(understat_id) not in allowed_ids:
                    stop(f"Understat id {understat_id} reaches FBref ids {sorted(ids)}: the run needs a cross_season_ids row with that id, or a different decision")
                cross_season_cases.append((understat_id, tuple(sorted(ids))))

    # Final check (D46): whatever route joined it, no row in `final` may be one a `reject` row left unjoined. Both runs stop, because it is a wrong join in either (D47).
    rejected_by = {}
    for row in rows:
        if row["decision"] == "reject" and row["item_type"] in LINK_ITEM_TYPES:
            rejected_by.update(dict.fromkeys(items[(row["item_type"], row["key"])], row))
        elif row["decision"] == "reject" and row["item_type"] == "partial_join":
            rejected_by.update(dict.fromkeys((group for group in rows_of if group.player_season == partial_keys[row["key"]] and group not in rule3.final), row))
    for group in sorted(rejected_by.keys() & links.keys()):
        link_rows = [row for row in rows if row["item_type"] in LINK_ITEM_TYPES and row["decision"] != "reject" and (group in items[(row["item_type"], row["key"])] or (row["decision"] == "merge_ids" and row["fbref_id"] == links[group][1] and row["key"].split("|")[:2] == [group.league, str(group.season)]))]
        routes = [f"{row['decision']} on {row['item_type']} {row['key']}" for row in link_rows] + combines_onto(group) or [f"a {links[group][0]} link"]
        rejected = rejected_by[group]
        stop(f"final check: {group.name} ({partial_join_key(group.player_season)}) in match {group.match} is joined on {links[group][1]} by {' and '.join(routes)}, but reject on {rejected['item_type']} {rejected['key']} left it unjoined. Keep one.")

    pool = pool_of(candidates_after, flags)
    finished = rule3._replace(final=links, guard=guard, pair_of=pair_of, name_map_rows=+name_map_rows, matches_of=+matches_of, anchor_guard=anchor_guard, anchor_pair_of=anchor_pair_of, anchor_rows=+anchor_rows, anchor_matches=+anchor_matches)
    joined_before, joined_after = (sum(rows_of[group] for group in stage) for stage in (rule3.final, links))
    return JoinResult(
        finished, positions, candidates_after, flags, pool, partial, len(pool_of(candidates, flags_before)), len(pool), joined_before, joined_after,
        {key: ids for key, ids in rule3.collisions.items() if key not in merged and key not in settled and not set(ids) <= decided[key]}, merge_rows, merged_collisions, anchors_removed, cross_season_cases,
        [(league, year, new_id) for (league, year, _), new_id in sorted(combine.items()) if (league, year, new_id) not in set(candidates_after)], list(refused), unjoined_listed,
    )
