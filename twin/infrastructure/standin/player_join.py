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


def minutes_guard(pairs, facts, approved_keys=frozenset()):
    """One verdict per player-season name and FBref id: agree, disagree, approved or none, with both minutes."""
    results = {}
    for pair in sorted(pairs):
        names = facts.shot_names.get((pair.league, pair.season, pair.understat_id), {html.unescape(pair.name)})
        row = season_totals_row(facts, pair.league, pair.season, names, pair.fbref_id)
        fbref = facts.fbref_minutes.get((pair.league, pair.season + 1, pair.fbref_id), 0)
        if row is None:
            results[pair] = ("none", None, fbref)
            continue
        within = abs(row.minutes - fbref) <= minutes_limit(row.minutes, fbref)
        results[pair] = ("agree" if within else "approved" if decision_key(pair) in approved_keys else "disagree", row.minutes, fbref)
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


def rule3_links(rows_of, rosters, facts, approved_keys=frozenset()):
    """Exact, step 1, step 2, the guard, step 3, the guard on its links, then id collisions. Plan lines 129 to 136, in that order."""
    groups = sorted(rows_of)
    joined = join_by_name(groups, rosters)
    name_map = name_map_links(groups, rosters, joined)
    pair_of = {group: PlayerSeasonName(*group.player_season_name, fbref_id) for group, fbref_id in name_map.links.items()}
    name_map_rows, matches_of = Counter(), Counter()
    for group, pair in pair_of.items():
        name_map_rows[pair] += rows_of[group]
        matches_of[pair] += 1
    guard = minutes_guard(name_map_rows, facts, approved_keys)
    after_step_2 = links_after_step_2(joined, name_map)
    after_guard = {group: link for group, link in after_step_2.items() if link[0] != "map" or guard[pair_of[group]][0] != "disagree"}
    anchors = season_anchor_links(name_map.undecided, after_guard, name_map.conflicts)
    anchor_pair_of = {group: PlayerSeasonName(*group.player_season_name, fbref_id) for group, fbref_id in anchors.links.items()}
    anchor_rows, anchor_matches = Counter(), Counter()
    for group, pair in anchor_pair_of.items():
        anchor_rows[pair] += rows_of[group]
        anchor_matches[pair] += 1
    anchor_guard = minutes_guard(anchor_rows, facts, approved_keys)
    after_anchor = {**after_guard, **{group: ("season_anchor", fbref_id) for group, fbref_id in anchors.links.items()}}
    after_anchor_guard = {group: link for group, link in after_anchor.items() if link[0] != "season_anchor" or anchor_guard[anchor_pair_of[group]][0] != "disagree"}
    collisions = id_collisions(after_anchor_guard)
    colliding = {(league, season, understat_id) for (league, season, _), ids in collisions.items() for understat_id in ids}
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
