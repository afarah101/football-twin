"""Measure rule 3 of docs/phase-1-plan.md, joining shots to FBref players, on data/standin.

Usage: python3 scripts/measure_rule3.py

Prints the join table, the minutes guard results, the season anchors, the partial joins and the id collisions, with the
checks behind them. Writes a fixed
random sample of the name map to docs/reports/name_map_sample.csv. Reads data/standin only, makes no network calls, and
the same files give identical output. It runs twice, with the FBref id merges off and then on, and prints one `Merges` line for
each. Every other section, and the sample, come from the merges-on run only. Of review_decisions.csv it applies only `approve` on a link, at the guard, and only
that row stops on a stale key. It prints any other row as not applied. read_review_decisions adds two stops, on an unknown
value and on two rows with one key. All the plan's other stops are #6 work.
Exits non-zero if a check at the end fails.
"""
import contextlib
import csv
import html
import io
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.infrastructure.standin.player_join import SHOT_FILE_OF_LEAGUE, link_matches, load_positions, load_shots, merge_fbref_ids, positions_for_join, understat_to_fbref_clubs

DATA = ROOT / "data" / "standin"
SAMPLE_FILE = ROOT / "docs" / "reports" / "name_map_sample.csv"
SAMPLE_SEED = 20261104
SAMPLE_SIZE = 50

FOLDED_LETTERS = str.maketrans({"ø": "o", "ð": "d", "đ": "dj", "ı": "i", "ł": "l", "ß": "ss", "æ": "ae", "œ": "oe", "þ": "th"})
ATTACKING_POS = {"FW", "LW", "RW", "AM"}
DECISIONS_FILE = DATA / "review_decisions.csv"
LINK_ITEM_TYPES = {"name_map", "season_anchor"}
ITEM_TYPES = LINK_ITEM_TYPES | {"partial_join", "pool_candidate"}
DECISIONS = {"approve", "reject", "link_to", "merge_ids"}
# League, Understat season and player_id of the cases the plan asks about, and the former collisions.
NAMED_CASES = (
    ("ESP", 2018, 5114), ("ESP", 2019, 2302), ("FRA", 2022, 11016), ("FRA", 2022, 11249),
    ("ESP", 2021, 2098), ("ESP", 2021, 8978), ("ESP", 2023, 2400), ("ESP", 2023, 8042), ("ITA", 2019, 1140), ("ITA", 2019, 2244),
)
MIN_JOINED_ROWS = 315_073
# With the current review_decisions.csv, as (Pool, candidates). A new `approve` can move them.
EXPECTED_MERGES_OFF, EXPECTED_MERGES_ON = (3_108, 3_136), (3_109, 3_137)
MIN_ANCHOR_MATCHES = 2
FULL_JOIN_PERCENT = 95


class ShotGroup(NamedTuple):
    """One player's shots in one match, as Understat names them. The club comes from h_a and the linked match."""
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
    league: str
    season: int
    understat_id: int
    name: str
    fbref_id: str


def decision_key(pair):
    """The key review_decisions.csv uses for a name_map or season_anchor link."""
    return f"{pair.league}|{pair.season}|{pair.understat_id}|{html.unescape(pair.name)}|{pair.fbref_id}"


def read_review_decisions():
    """Every row of the review decisions file. Stops on an unknown item_type or decision, or on two rows with one key. The plan's `fbref_id` stops are #6 work."""
    # utf-8-sig: spreadsheets save this hand-edited file with a byte order mark.
    with DECISIONS_FILE.open(encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))
    for row in decisions:
        if row["item_type"] not in ITEM_TYPES or row["decision"] not in DECISIONS:
            raise SystemExit(f"{DECISIONS_FILE.name}: unknown item_type or decision: {row}")
    repeated = sorted(key for key, count in Counter((row["item_type"], row["key"]) for row in decisions).items() if count > 1)
    if repeated:
        raise SystemExit(f"{DECISIONS_FILE.name}: two rows on one key: {repeated}")
    return decisions


def compared_name(name):
    """Step 1: case, accents and punctuation removed, letters NFKD does not reduce folded, a hyphen counts as a space."""
    decomposed = unicodedata.normalize("NFKD", html.unescape(name))
    folded = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().translate(FOLDED_LETTERS)
    return " ".join(re.sub(r"[^\w\s]", "", folded.replace("-", " ")).split())


def minutes_limit(understat_minutes, fbref_minutes):
    return max(90, 0.1 * max(understat_minutes, fbref_minutes))


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
    """Step 2, within the match and club only. Returns the links, the 2+ candidate groups and what each rule stopped."""
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
    return {group: fbref_id for group, fbref_id in links.items() if group.player_season not in conflicts}, undecided, stopped, conflicts


def season_anchor_links(undecided, linked):
    """Step 3: in a match with 2+ candidates, the one FBref id the same Understat id links to in 2+ other matches of that season and club.

    Anchors come only from links that survived the guard, and one pass only, so an anchor link never anchors another.
    Returns the links and what stopped the others.
    """
    matches_of_id = defaultdict(lambda: defaultdict(set))
    for group, (_, fbref_id) in linked.items():
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
    return links, stopped


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


def season_minutes_by_name(clubs):
    """Understat season minutes per league, season and name, with the FBref clubs of each row's team list."""
    rows = pd.read_parquet(DATA / "understat_xg_data.parquet", columns=["player_name", "team", "league", "season", "minutes"])
    index = defaultdict(list)
    for league, season, name, team, minutes in zip(rows["league"], rows["season"], rows["player_name"], rows["team"], rows["minutes"]):
        league = "ENG" if league == "EPL" else league
        index[(league, int(season[:4]), html.unescape(name))].append(({clubs.get((league, part.strip())) for part in team.split(",")}, int(minutes)))
    return index


def minutes_guard(name_map_rows, understat_minutes, fbref_minutes, clubs_of_player, approved_keys):
    """One verdict per name map player-season: agree, disagree, approved or none."""
    results = {}
    for pair in sorted(name_map_rows):
        options = understat_minutes.get((pair.league, pair.season, html.unescape(pair.name)), [])
        if len(options) > 1:
            options = [option for option in options if option[0] & clubs_of_player[(pair.league, pair.season + 1, pair.fbref_id)]]
        fbref = fbref_minutes.get((pair.league, pair.season + 1, pair.fbref_id), 0)
        if not options:
            results[pair] = ("none", None, fbref)
            continue
        understat = sum(option[1] for option in options)
        within = abs(understat - fbref) <= minutes_limit(understat, fbref)
        results[pair] = ("agree" if within else "approved" if decision_key(pair) in approved_keys else "disagree", understat, fbref)
    return results


def id_collisions(joined):
    """Two Understat ids on one FBref id in a league-season."""
    ids = defaultdict(set)
    for group, (_, fbref_id) in joined.items():
        ids[(group.league, group.season, fbref_id)].add(group.understat_id)
    return {key: sorted(found) for key, found in sorted(ids.items()) if len(found) > 1}


def pool_candidates(positions):
    """PlayerSeasons at 900+ minutes with attacking minutes above other minutes, substitute appearances ignored."""
    events = pd.concat([pd.read_parquet(DATA / f"{league}_M_1st_match_summary.parquet", columns=["MatchURL", "Team", "Event_Type", "Event_Players"]) for league in SHOT_FILE_OF_LEAGUE])
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


def chance_of_passing_guard(guard, fbref_minutes, roster_of_club, clubs_of_player):
    """How often a wrong same-club player would pass the limit, so what a pass is worth."""
    passed = tried = 0
    for pair, (_, understat, _) in guard.items():
        if understat is None:
            continue
        for club in sorted(clubs_of_player[(pair.league, pair.season + 1, pair.fbref_id)]):
            for other in sorted(roster_of_club[(pair.league, pair.season + 1, club)] - {pair.fbref_id}):
                minutes = fbref_minutes.get((pair.league, pair.season + 1, other), 0)
                tried += 1
                passed += abs(understat - minutes) <= minutes_limit(understat, minutes)
    return passed, tried


def write_sample(name_map_rows, guard, names, rows_of, matches_of):
    pairs = random.Random(SAMPLE_SEED).sample(sorted(name_map_rows), SAMPLE_SIZE)
    with SAMPLE_FILE.open("w", encoding="utf8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["league", "understat_season", "understat_id", "shot_name", "fbref_id", "fbref_name", "shot_rows", "matches", "understat_minutes", "fbref_minutes", "minutes_check"])
        for pair in sorted(pairs):
            check, understat, fbref = guard[pair]
            writer.writerow([pair.league, pair.season, pair.understat_id, html.unescape(pair.name), pair.fbref_id, names[pair.fbref_id], rows_of[pair], matches_of[pair], "" if understat is None else understat, fbref, check])
    return len(pairs)


def self_check():
    assert compared_name("Kylian Mbappe-Lottin") == "kylian mbappe lottin"
    assert compared_name("Martin Ødegaard") == compared_name("Martin Odegaard")
    assert compared_name("N&#039;Golo Kanté") == "ngolo kante"
    assert is_name_map_candidate(["bruno"], ["bruno", "fernandes"])
    assert is_name_map_candidate(["kylian", "mbappe", "lottin"], ["kylian", "mbappe"])
    assert not is_name_map_candidate(["bruno"], ["brunos", "fernandes"])
    # 0 real rows reach this direction out of order, so only an assert can hold it.
    assert is_name_map_candidate(["fernandes", "bruno"], ["bruno", "miguel", "fernandes"])
    assert abs(minutes_limit(839, 933) - 93.3) < 1e-9 and minutes_limit(49, 167) == 90
    assert decision_key(PlayerSeasonName("ESP", 2023, 10095, "N&#039;Golo", "bed68338")) == "ESP|2023|10095|N'Golo|bed68338"
    shot = lambda match, understat_id=1, club="A": ShotGroup("ESP", 2021, match, understat_id, "Kike", club)
    two_other = {shot("m1"): ("map", "x"), shot("m2"): ("map", "x")}
    assert season_anchor_links({shot("m3"): {"x", "y"}}, two_other)[0] == {shot("m3"): "x"}
    assert season_anchor_links({shot("m3"): {"x", "y"}}, {shot("m1"): ("map", "x")})[0] == {}
    assert season_anchor_links({shot("m3"): {"y", "z"}}, two_other)[0] == {}
    assert season_anchor_links({shot("m3", club="B"): {"x", "y"}}, two_other)[0] == {}
    assert season_anchor_links({shot("m3"): {"x", "y"}}, {**two_other, shot("m4"): ("map", "z")})[0] == {}
    assert season_anchor_links({shot("m3"): {"x", "y"}, shot("m3", 2): {"x", "y"}}, {**two_other, shot("m1", 2): ("map", "x"), shot("m2", 2): ("map", "x")})[0] == {}
    assert list(partial_joins({shot("m1"): 19, shot("m2"): 1}, {shot("m1")})) == []
    assert list(partial_joins({shot("m1"): 18, shot("m2"): 2}, {shot("m1")})) == [("ESP", 2021, 1)]
    spellings = [ShotGroup("GER", 2023, "m1", 1, "Sehrou Guirassy", "A"), ShotGroup("GER", 2023, "m2", 1, "Serhou Guirassy", "A")]
    roster_with = lambda second_id: {("m1", "A"): [RosterPlayer("x", "S Guirassy", "s guirassy")], ("m2", "A"): [RosterPlayer(second_id, "S Guirassy", "s guirassy")]}
    assert len(name_map_links(spellings, roster_with("x"), {})[0]) == 2
    assert name_map_links(spellings, roster_with("y"), {})[0] == {}
    assert name_map_links(spellings, roster_with("y"), {spellings[1]: ("exact", "y")})[0] == {}
    assert len(name_map_links(spellings, roster_with("x"), {spellings[1]: ("exact", "x")})[0]) == 1
    assert name_map_links(spellings, roster_with("y"), {spellings[0]: ("exact", "x"), spellings[1]: ("exact", "y")})[3] == []


def measure(positions, shots, clubs):
    """One whole run. Returns the joined rows, the Pool count, the candidates and the checks, and writes the sample."""
    date_links = link_matches(shots, positions, clubs)
    links, gaps, understat_match_count = date_links.links, Counter(date_links.gap_days.values()), date_links.understat_matches
    both_filled = shots[(shots["h_a"].fillna("") != "") & (shots["home_away"].fillna("") != "")]
    print(f"Pool seasons: shot rows {len(shots)} | side values {dict(sorted(Counter(shots['side'].fillna('')).items()))} | h_a and home_away both filled {len(both_filled)}, disagreeing {int((both_filled['h_a'] != both_filled['home_away']).sum())}")
    print(f"Date link: Understat matches {understat_match_count} | linked {len(links)} | gap days to matches {dict(sorted(gaps.items()))}")

    rows_of, row_groups = shot_groups(shots, links, positions)
    groups = sorted(rows_of)
    total = sum(rows_of.values())
    rosters = build_rosters(positions)
    names = positions.sort_values(["Season_End_Year", "match"]).groupby("fbref_id")["Player"].first().to_dict()
    fbref_minutes = {key: int(value) for key, value in positions.groupby(["league", "Season_End_Year", "fbref_id"])["Min"].sum().items()}
    clubs_of_player = defaultdict(set)
    roster_of_club = defaultdict(set)
    for league, year, club, fbref_id in zip(positions["league"], positions["Season_End_Year"], positions["Team"], positions["fbref_id"]):
        clubs_of_player[(league, year, fbref_id)].add(club)
        roster_of_club[(league, year, club)].add(fbref_id)

    joined = join_by_name(groups, rosters)
    exact = {group: link for group, link in joined.items() if link[0] == "exact"}
    after_step_1 = dict(joined)
    mapped, undecided, stopped, conflicts = name_map_links(groups, rosters, joined)
    after_step_2 = {**joined, **{group: ("map", fbref_id) for group, fbref_id in mapped.items()}}
    pair_of = {group: PlayerSeasonName(group.league, group.season, group.understat_id, group.name, fbref_id) for group, fbref_id in mapped.items()}
    name_map_rows, matches_of = Counter(), Counter()
    for group, pair in pair_of.items():
        name_map_rows[pair] += rows_of[group]
        matches_of[pair] += 1
    understat_minutes = season_minutes_by_name(clubs)
    decisions = read_review_decisions()
    approved_keys = {row["key"] for row in decisions if row["decision"] == "approve" and row["item_type"] in LINK_ITEM_TYPES}
    guard = minutes_guard(name_map_rows, understat_minutes, fbref_minutes, clubs_of_player, approved_keys)
    after_guard = {group: link for group, link in after_step_2.items() if link[0] != "map" or guard[pair_of[group]][0] != "disagree"}
    anchored, anchor_stopped = season_anchor_links(undecided, after_guard)
    anchor_pair_of = {group: PlayerSeasonName(group.league, group.season, group.understat_id, group.name, fbref_id) for group, fbref_id in anchored.items()}
    anchor_rows, anchor_matches = Counter(), Counter()
    for group, pair in anchor_pair_of.items():
        anchor_rows[pair] += rows_of[group]
        anchor_matches[pair] += 1
    anchor_guard = minutes_guard(anchor_rows, understat_minutes, fbref_minutes, clubs_of_player, approved_keys)
    keys_of_type = {"name_map": {decision_key(pair) for pair in guard}, "season_anchor": {decision_key(pair) for pair in anchor_guard}}
    stale = [row for row in decisions if row["decision"] == "approve" and row["item_type"] in LINK_ITEM_TYPES and row["key"] not in keys_of_type[row["item_type"]]]
    if stale:
        raise SystemExit(f"{DECISIONS_FILE.name}: stale decisions, key not in the data: {stale}")
    not_applied = [row for row in decisions if row["decision"] != "approve" or row["item_type"] not in LINK_ITEM_TYPES]
    if not_applied:
        print(f"Review decisions this script does not apply, so #6's numbers will differ: {not_applied}")
    after_anchor = {**after_guard, **{group: ("season_anchor", fbref_id) for group, fbref_id in anchored.items()}}
    after_anchor_guard = {group: link for group, link in after_anchor.items() if link[0] != "season_anchor" or anchor_guard[anchor_pair_of[group]][0] != "disagree"}
    collisions = id_collisions(after_anchor_guard)
    colliding = {(league, season, understat_id) for (league, season, _), ids in collisions.items() for understat_id in ids}
    final = {group: link for group, link in after_anchor_guard.items() if (group.league, group.season, group.understat_id) not in colliding}
    partial = partial_joins(rows_of, final)

    def count(stage):
        return sum(rows_of[group] for group in stage)

    print("\n### Join table")
    print(f"Pool shot rows in linked matches: {total}")
    for label, stage in (("Exact", exact), ("After step 1", after_step_1), ("After step 2", after_step_2), ("After the minutes guard", after_guard), ("After season anchors", after_anchor), ("After the guard on anchors", after_anchor_guard), ("After id collisions", final)):
        print(f"{label}: {count(stage)} ({100 * count(stage) / total:.2f}%)")
    print(f"Unjoined: {total - count(final)}")
    by_league = defaultdict(Counter)
    for group in groups:
        by_league[group.league]["all"] += rows_of[group]
        for label, stage in (("exact", exact), ("step 1", after_step_1), ("step 2", after_step_2), ("final", final)):
            by_league[group.league][label] += rows_of[group] if group in stage else 0
    for league, counts in sorted(by_league.items()):
        print(f"{league}: " + " / ".join(f"{label} {100 * counts[label] / counts['all']:.2f}" for label in ("exact", "step 1", "step 2", "final")))
    print(f"Stopped at step 2: {dict(sorted(stopped.items()))} | listed 2+ FBref ids: {conflicts}")

    print("\n### Minutes guard")
    verdicts = Counter(result[0] for result in guard.values())
    print(f"Name map player-seasons {len(guard)}, rows {sum(name_map_rows.values())} | {dict(sorted(verdicts.items()))}")
    kept_pairs = {pair: rows for pair, rows in name_map_rows.items() if guard[pair][0] != "disagree"}
    print(f"Keep their link: {len(kept_pairs)} player-seasons, {sum(kept_pairs.values())} rows")
    for pair, (check, understat, fbref) in guard.items():
        if check in ("disagree", "approved"):
            print(f"  {check}: {pair.league} {pair.season} id {pair.understat_id} {html.unescape(pair.name)} to {names[pair.fbref_id]} {pair.fbref_id}: {understat} v {fbref}, gap {abs(understat - fbref)}, limit {minutes_limit(understat, fbref):.1f}, {name_map_rows[pair]} rows")
    for pair, (check, _, fbref) in guard.items():
        if check == "none":
            print(f"  minutes_check = none: {pair.league} {pair.season} id {pair.understat_id} {html.unescape(pair.name)} to {names[pair.fbref_id]} {pair.fbref_id}: FBref {fbref}, {name_map_rows[pair]} rows")
    passed, tried = chance_of_passing_guard(guard, fbref_minutes, roster_of_club, clubs_of_player)
    print(f"Wrong same-club players who would pass the limit: {passed} of {tried} ({100 * passed / tried:.1f}%)")

    print("\n### Season anchors")
    print(f"2+ candidate groups {len(undecided)}, rows {sum(rows_of[group] for group in undecided)} | linked groups {len(anchored)}, rows {sum(anchor_rows.values())} | not linked: {dict(sorted(anchor_stopped.items()))}")
    print(f"Guard on {len(anchor_guard)} anchor player-seasons: {dict(sorted(Counter(result[0] for result in anchor_guard.values()).items()))}")
    basis = defaultdict(set)
    for group, link in after_guard.items():
        basis[(group.league, group.season, group.understat_id, group.club)].add(link[0])
    for pair, (check, understat, fbref) in anchor_guard.items():
        anchor_clubs = {group.club for group, found in anchor_pair_of.items() if found == pair}
        anchor_basis = sorted({step for club in anchor_clubs for step in basis[(pair.league, pair.season, pair.understat_id, club)]})
        print(f"  {check}: {pair.league} {pair.season} id {pair.understat_id} {html.unescape(pair.name)} to {names[pair.fbref_id]} {pair.fbref_id}: {anchor_rows[pair]} rows in {anchor_matches[pair]} matches, minutes {understat} v {fbref}, anchored on {anchor_basis}, clubs {sorted(anchor_clubs)}")
    print("Not linked:", [(group.league, group.season, group.understat_id, html.unescape(group.name), group.club, rows_of[group]) for group in sorted(undecided) if group not in anchored])
    side_club = {}
    for group, side, home_team, away_team in zip(row_groups, shots["side"], shots["home_team"], shots["away_team"]):
        if group in anchored:
            side_club[group] = clubs.get((group.league, home_team if side == "h" else away_team))
    print(f"Anchor links where the h_a club through club_map differs from the link's club: {sum(side_club[group] != group.club for group in anchored)} (0 by construction)")
    minutes_in_match = dict(zip(zip(positions["match"], positions["fbref_id"]), positions["Min"]))
    no_minutes = sorted((group.league, group.season, group.match, html.unescape(group.name), fbref_id) for group, fbref_id in anchored.items() if pd.isna(minutes_in_match[(group.match, fbref_id)]) or minutes_in_match[(group.match, fbref_id)] == 0)
    print(f"Anchor links where the linked player has no minutes in that match: {no_minutes}")
    other_team = set()
    for group, pair in anchor_pair_of.items():
        options = understat_minutes.get((pair.league, pair.season, html.unescape(pair.name)), [])
        if options and not any(group.club in option[0] for option in options):
            other_team.add((pair.league, pair.season, html.unescape(pair.name), group.club))
    other_team = sorted(other_team)
    print(f"Anchor links whose club is not in the Understat season file's team list: {other_team}")

    print("\n### Partial joins")
    pool = pool_candidates(positions)
    pool_set = set(pool)
    partly_joined = {key: value for key, value in partial.items() if value[0] > 0}
    none_joined = {key: value for key, value in partial.items() if value[0] == 0}
    ids_of_season, names_of_season, clubs_of_season = defaultdict(set), defaultdict(set), defaultdict(set)
    for group in groups:
        names_of_season[(group.league, group.season, group.understat_id)].add(html.unescape(group.name))
        clubs_of_season[(group.league, group.season, group.understat_id)].add(group.club)
    for group, link in final.items():
        ids_of_season[(group.league, group.season, group.understat_id)].add(link[1])
    def season_minutes(key):
        return sum(option[1] for name in sorted(names_of_season[key]) for option in understat_minutes.get((key[0], key[1], name), []) if option[0] & clubs_of_season[key])
    before_anchors, after_anchors = ({key: counts for key, counts in join_counts(rows_of, stage).items() if 0 < counts[0] < counts[1]} for stage in (after_guard, final))
    print(f"Partly joined before anchors: {len(before_anchors)}, holding {sum(total - found for found, total in before_anchors.values())} unjoined rows | now fully joined {sum(key not in after_anchors for key in before_anchors)} | still partly joined {len(after_anchors)}, holding {sum(total - found for found, total in after_anchors.values())} unjoined rows")
    print("Still partly joined at 95% or above, so no flag:", [(key, value) for key, value in after_anchors.items() if key not in partial])
    print(f"partial_join = yes: {len(partial)} player-seasons | some rows joined {len(partly_joined)}, holding {sum(total - found for found, total in partly_joined.values())} unjoined rows | no rows joined {len(none_joined)}, holding {sum(total for _, total in none_joined.values())} rows")
    pool_partly_joined = sorted((key[0], key[1], names[key[2]]) for key in pool_set if any((key[0], key[1] - 1) == found[:2] and key[2] in ids_of_season[found] for found in partly_joined))
    print(f"Pool candidates holding a partial_join: {pool_partly_joined}")
    print("Some rows joined, as league, season, id, names, joined, total, percent, FBref ids, Pool candidate:")
    for key, (found, total) in sorted(partly_joined.items(), key=lambda item: (item[1][0] / item[1][1], item[0])):
        print(f"  {key[0]} {key[1]} {key[2]} {sorted(names_of_season[key])} {found} of {total} ({100 * found / total:.1f}%) {sorted(ids_of_season[key])} Pool: {[(key[0], key[1] + 1, fbref_id) in pool_set for fbref_id in sorted(ids_of_season[key])]}")
    print("No rows joined, as league, season, id, names, rows, Understat minutes:")
    for key, (_, total) in sorted(none_joined.items(), key=lambda item: (-item[1][1], item[0])):
        print(f"  {key[0]} {key[1]} {key[2]} {sorted(names_of_season[key])} {total} {season_minutes(key)}")

    print("\n### Id collisions")
    for (league, season, fbref_id), ids in collisions.items():
        print(f"  {league} {season} {names[fbref_id]} {fbref_id}: Understat ids {ids}, rows {sum(rows_of[group] for group in after_guard if (group.league, group.season) == (league, season) and group.understat_id in ids)}")
    print(f"Collisions: {len(collisions)}")
    ids_of_understat = defaultdict(set)
    for group, (_, fbref_id) in final.items():
        ids_of_understat[(group.league, group.season, group.understat_id)].add(fbref_id)
    print("One Understat id on 2+ FBref ids:", [(key, sorted(ids)) for key, ids in sorted(ids_of_understat.items()) if len(ids) > 1])

    print("\n### Outside checks")
    clubs_in_match = defaultdict(set)
    for (match, club) in rosters:
        clubs_in_match[match].add(club)
    other_club_only = []
    for group in groups:
        wanted = compared_name(group.name)
        on_own = any(player.compared == wanted for player in rosters[(group.match, group.club)])
        on_other = any(player.compared == wanted for club in clubs_in_match[group.match] - {group.club} for player in rosters[(group.match, club)])
        if on_other and not on_own:
            other_club_only.append((group.league, group.season, group.match, html.unescape(group.name), group.club, rows_of[group]))
    print(f"h_a club holds no such name but the other club does: {len(other_club_only)} groups, {sum(item[-1] for item in other_club_only)} rows: {other_club_only}")
    own_goal = Counter()
    for group, result in zip(row_groups, shots["result"]):
        if group is not None and result == "OwnGoal":
            own_goal["joined" if group in final else "unjoined"] += 1
    print(f"Own goal rows in linked matches: {dict(sorted(own_goal.items()))}")

    print("\n### Named cases")
    for case in NAMED_CASES:
        found = defaultdict(int)
        for group in groups:
            if (group.league, group.season, group.understat_id) == case:
                link = final.get(group)
                found[(html.unescape(group.name), link[0] if link else "unjoined", link[1] if link else "", names.get(link[1], "") if link else "")] += rows_of[group]
        print(f"  {case}: {[(*key, rows) for key, rows in sorted(found.items())]}")

    print("\n### Still unjoined")
    unjoined_names, unjoined_seasons = Counter(), Counter()
    for group in groups:
        if group not in final:
            unjoined_names[(group.league, html.unescape(group.name))] += rows_of[group]
            unjoined_seasons[(group.league, group.season)] += rows_of[group]
    print("Largest:", sorted(unjoined_names.items(), key=lambda item: (-item[1], item[0]))[:12])
    print("Per league-season:", sorted(unjoined_seasons.items()))

    joined_rows, unjoined_rows = Counter(), Counter()
    for group in groups:
        (joined_rows if group in final else unjoined_rows)[group.player_season_name] += rows_of[group]
    partly = sorted(((name, joined_rows[name], unjoined_rows[name]) for name in joined_rows if name in unjoined_rows), key=lambda item: (-item[2], item[0]))
    print(f"Player-seasons partly joined: {len(partly)}, holding {sum(item[2] for item in partly)} unjoined rows. Largest, as (league, season, id, name), joined, unjoined: {partly[:12]}")

    with_shots = {(group.league, group.season + 1, link[1]) for group, link in final.items()}
    no_shots = sorted((key[0], key[1], names[key[2]]) for key in pool if key not in with_shots)
    print(f"\nPool candidates with shots: {len(pool) - len(no_shots)} of {len(pool)} ({100 * (len(pool) - len(no_shots)) / len(pool):.2f}%)")
    print(f"No joined shots, so partial_join = yes: {len(no_shots)}: {no_shots}")
    pool_count = len(pool) - len(no_shots) - len(pool_partly_joined)
    print(f"Pool until Ahmed's review: {pool_count} of {len(pool)} candidates")

    final_pairs = {pair_of[group] for group, link in final.items() if link[0] == "map"}
    sampled = write_sample(final_pairs, guard, names, name_map_rows, matches_of)
    print(f"\n### Sample\n{sampled} of {len(final_pairs)} name map pairs, seed {SAMPLE_SEED}, written to {SAMPLE_FILE.relative_to(ROOT)}")

    return count(final), pool_count, len(pool), {
        "no id collisions": not collisions,
        f"at least {MIN_JOINED_ROWS} rows joined": count(final) >= MIN_JOINED_ROWS,
        "Ezzalzouli approved": any(pair.name == "Abdessamad Ezzalzouli" and result[0] == "approved" for pair, result in guard.items()),
        f"sample holds {SAMPLE_SIZE} rows": sampled == SAMPLE_SIZE,
    }


def main():
    self_check()
    unmerged = positions_for_join(merges=False)
    shots = load_shots()
    clubs = understat_to_fbref_clubs()
    # The sample file is written by whichever run comes last, so the merges-on run must stay last.
    with contextlib.redirect_stdout(io.StringIO()):
        joined_off, pool_off, candidates_off, _ = measure(unmerged, shots, clubs)
    merged, merges, refused = merge_fbref_ids(unmerged)
    joined_on, pool_on, candidates_on, checks = measure(merged, shots, clubs)
    print(f"\n### Id merges\nMerged: {[(merge.league, merge.year, merge.player, merge.ids, merge.survivor) for merge in merges]} | refused: {refused}")
    print(f"Merges off: joined {joined_off} | Pool {pool_off} of {candidates_off}")
    print(f"Merges on: joined {joined_on} | Pool {pool_on} of {candidates_on}")
    checks[f"merges off: Pool is {EXPECTED_MERGES_OFF}"] = (pool_off, candidates_off) == EXPECTED_MERGES_OFF
    checks[f"merges on: Pool is {EXPECTED_MERGES_ON}"] = (pool_on, candidates_on) == EXPECTED_MERGES_ON
    print("\n### Checks")
    for label, passed_check in checks.items():
        print(f"{'PASS' if passed_check else 'FAIL'}: {label}")
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
