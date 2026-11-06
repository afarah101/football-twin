"""Measure rule 3 of docs/phase-1-plan.md, joining shots to FBref players, on data/standin.

Usage: python3 scripts/measure_rule3.py

Prints the join table, the minutes guard results, the season anchors, the partial joins, the id collisions and the
records the stand-in loader builds, with the checks behind them. Writes data/standin/name_map.csv, and a fixed random sample of it to docs/reports/name_map_sample.csv.
Reads data/standin only, makes no network calls, and the same files give identical output. All the join logic is in
twin/infrastructure/standin/player_join.py, so one version exists. It runs twice, with the FBref id merges off and then on,
and prints one `Merges` line for each. Every other section, and the files, come from the merges-on run only.
Exits non-zero if a check at the end fails.
"""
import contextlib
import csv
import html
import io
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.domain.pool import in_pool, is_pool_candidate
from twin.infrastructure.standin.loader import build_records
from twin.infrastructure.standin.player_join import (
    MAX_SHOT_GAP, MIN_ANCHOR_MATCHES, anchor_listing, build_rosters, check_sample_pairs, compared_name, finish_join, guard_facts, guard_review_list, join_counts, link_keys, link_matches, load_positions,
    load_shots, merge_fbref_ids, minutes_limit, name_map_file_rows, partial_joins, pool_candidates, positions_for_join, read_review_decisions, rule3_links, season_rows_by_name, shot_groups,
    understat_to_fbref_clubs,
)

DATA = ROOT / "data" / "standin"
SAMPLE_FILE = ROOT / "docs" / "reports" / "name_map_sample.csv"
SAMPLE_SEED = 20261104
SAMPLE_SIZE = 50
NAME_MAP_FILE = DATA / "name_map.csv"
FILE_COLUMNS = ["league", "understat_season", "understat_id", "shot_name", "fbref_id", "fbref_name", "shot_rows", "matches", "understat_minutes", "fbref_minutes", "minutes_check"]
# League, Understat season and player_id of the cases the plan asks about, and the former collisions.
NAMED_CASES = (
    ("ESP", 2018, 5114), ("ESP", 2019, 2302), ("FRA", 2022, 11016), ("FRA", 2022, 11249),
    ("ESP", 2021, 2098), ("ESP", 2021, 8978), ("ESP", 2023, 2400), ("ESP", 2023, 8042), ("ITA", 2019, 1140), ("ITA", 2019, 2244),
)
MIN_JOINED_ROWS = 315_073
# With the current review_decisions.csv, as (Pool, candidates). A new `approve` can move them.
EXPECTED_MERGES_OFF, EXPECTED_MERGES_ON = (3_108, 3_136), (3_109, 3_137)


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


def write_rows(path, rows):
    with path.open("w", encoding="utf8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows([FILE_COLUMNS, *rows])


def committed_sample_text():
    """The sample as committed, because each run rewrites the working copy."""
    return subprocess.run(["git", "show", f"HEAD:{SAMPLE_FILE.relative_to(ROOT).as_posix()}"], cwd=ROOT, capture_output=True, text=True, encoding="utf8", check=True).stdout


def write_outputs(rule3, names):
    """`name_map.csv`, and the fixed random sample of it. Returns the sample's size."""
    rows = name_map_file_rows(rule3, names.get)
    drawn = random.Random(SAMPLE_SEED).sample(rows, SAMPLE_SIZE)
    check_sample_pairs({(row[0], row[1], row[2], row[4]) for row in drawn}, committed_sample_text())
    write_rows(NAME_MAP_FILE, rows)
    write_rows(SAMPLE_FILE, sorted(drawn))
    return len(drawn)


def print_records(run, result):
    """The records built from this run, and the season totals checks behind them (D3, D4). Returns the records' Pool count."""
    found = run.loaded.player_seasons
    candidates = [player_season for player_season in found if is_pool_candidate(player_season.minutes, player_season.attacking_minutes, player_season.other_minutes)]
    pool = sum(map(in_pool, found))
    held = sum(player_season.held_for_review for player_season in found)
    print(f"Records: player_seasons {len(found)} | shots {len(run.loaded.shots)} | minutes {sum(player_season.minutes for player_season in found)} | Pool candidates {len(candidates)} | held {held} | held among candidates {sum(player_season.held_for_review for player_season in candidates)} | Pool {pool}")
    routes = Counter()
    for key in result.candidates:
        totals = result.season_totals[key]
        routes[totals.route if totals.row is not None else "no single row, already held" if key in result.flags else "no single row, not otherwise held"] += 1
    labels = ("shot name", "shot name + club", "FBref name", "no single row, not otherwise held", "no single row, already held")
    print("Season totals: " + " | ".join(f"{label} {routes.pop(label, 0)}" for label in labels) + "".join(f" | {label} {count}" for label, count in sorted(routes.items())))
    gaps = Counter(totals.gap for totals in result.season_totals.values() if totals.gap is not None)
    print(f"Shot gap: {' '.join(f'{gap}={count}' for gap, count in sorted(gaps.items()))} | over {MAX_SHOT_GAP}: {sum(count for gap, count in gaps.items() if gap > MAX_SHOT_GAP)}")
    return pool


def measure(positions, shots, clubs, refused, merges_on):
    """One whole run. Returns the joined rows, the Pool count, the candidates and the checks. Only the merges-on run writes files."""
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

    understat_minutes = season_rows_by_name(clubs)
    decisions = read_review_decisions()
    facts = guard_facts(positions, shots, understat_minutes)
    before_decisions = rule3_links(rows_of, rosters, facts)
    result = finish_join(before_decisions, rows_of, rosters, positions, decisions, refused, pool_candidates, facts, merges_on, season_checks=True)
    rule3 = result.rule3
    joined, name_map, pair_of, name_map_rows, matches_of, guard, after_guard = rule3.joined, rule3.name_map, rule3.pair_of, rule3.name_map_rows, rule3.matches_of, rule3.guard, rule3.after_guard
    anchors, anchor_pair_of, anchor_rows, anchor_matches, anchor_guard = rule3.anchors, rule3.anchor_pair_of, rule3.anchor_rows, rule3.anchor_matches, rule3.anchor_guard
    after_anchor, after_anchor_guard, collisions, final = rule3.after_anchor, rule3.after_anchor_guard, result.collisions, rule3.final
    exact = {group: link for group, link in joined.items() if link[0] == "exact"}
    after_step_1 = dict(joined)
    mapped, undecided, stopped, conflicts = name_map.links, name_map.undecided, name_map.stopped, name_map.conflicts
    after_step_2 = {**joined, **{group: ("map", fbref_id) for group, fbref_id in mapped.items()}}
    anchored, anchor_stopped = anchors.links, anchors.stopped
    partial = result.partial

    def count(stage):
        return sum(rows_of[group] for group in stage)

    print("\n### Join table")
    print(f"Pool shot rows in linked matches: {total}")
    for label, stage in (("Exact", exact), ("After step 1", after_step_1), ("After step 2", after_step_2), ("After the minutes guard", after_guard), ("After season anchors", after_anchor), ("After the guard on anchors", after_anchor_guard), ("After id collisions", before_decisions.final), ("After the review decisions", final)):
        print(f"{label}: {count(stage)} ({100 * count(stage) / total:.2f}%)")
    print(f"Unjoined: {total - count(final)}")
    by_league = defaultdict(Counter)
    for group in groups:
        by_league[group.league]["all"] += rows_of[group]
        for label, stage in (("exact", exact), ("step 1", after_step_1), ("step 2", after_step_2), ("final", final)):
            by_league[group.league][label] += rows_of[group] if group in stage else 0
    for league, counts in sorted(by_league.items()):
        print(f"{league}: " + " / ".join(f"{label} {100 * counts[label] / counts['all']:.2f}" for label in ("exact", "step 1", "step 2", "final")))
    print(f"Stopped at step 2: {dict(sorted(stopped.items()))} | listed 2+ FBref ids: {conflicts} | stopped links: {link_keys(name_map.stopped_links)} | barred links: {link_keys(anchors.barred)} | two ids: {name_map.two_ids}")

    print("\n### Minutes guard")
    verdicts = Counter(result[0] for result in guard.values())
    print(f"Name map player-seasons {len(guard)}, rows {sum(name_map_rows.values())} | {dict(sorted(verdicts.items()))}")
    kept_pairs = {pair: name_map_rows[pair] for pair in {pair_of[group] for group, link in final.items() if link[0] == "map"}}
    print(f"Keep their link: {len(kept_pairs)} player-seasons, {sum(kept_pairs.values())} rows")
    review = guard_review_list(rule3)
    for pair in [*review["disagree"], *review["approved"]]:
        check, understat, fbref = guard.get(pair) or anchor_guard[pair]
        print(f"  {check}: {pair.league} {pair.season} id {pair.understat_id} {html.unescape(pair.name)} to {names[pair.fbref_id]} {pair.fbref_id}: {understat} v {fbref}, gap {abs(understat - fbref)}, limit {minutes_limit(understat, fbref):.1f}, {name_map_rows[pair] + anchor_rows[pair]} rows")
    for pair in review["none"]:
        _, _, fbref = guard.get(pair) or anchor_guard[pair]
        print(f"  minutes_check = none: {pair.league} {pair.season} id {pair.understat_id} {html.unescape(pair.name)} to {names[pair.fbref_id]} {pair.fbref_id}: FBref {fbref}, {name_map_rows[pair] + anchor_rows[pair]} rows")
    passed, tried = chance_of_passing_guard(guard, fbref_minutes, roster_of_club, clubs_of_player)
    print(f"Wrong same-club players who would pass the limit: {passed} of {tried} ({100 * passed / tried:.1f}%)")

    print("\n### Season anchors")
    print(f"2+ candidate groups {len(undecided)}, rows {sum(rows_of[group] for group in undecided)} | linked groups {len(anchored)}, rows {sum(anchor_rows.values())} | not linked: {dict(sorted(anchor_stopped.items()))}")
    print(f"Guard on {len(anchor_guard)} anchor player-seasons: {dict(sorted(Counter(result[0] for result in anchor_guard.values()).items()))}")
    basis = defaultdict(set)
    for group, link in after_guard.items():
        basis[(group.league, group.season, group.understat_id, group.club)].add(link[0])
    for pair, (check, understat, fbref), _, _ in anchor_listing(rule3):
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
    pool = result.candidates
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
    for group, shot_result in zip(row_groups, shots["result"]):
        if group is not None and shot_result == "OwnGoal":
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
    flags, pool_count = result.flags, result.pool_after
    print(f"PlayerSeasons held by a flag: {len(flags)}, of them candidates {sum(key in pool_set for key in flags)}")
    print(f"Pool before the decisions: {result.pool_before} | after: {result.pool_after} | joined before: {result.joined_before} | after: {result.joined_after}")
    print(f"Pool until Ahmed's review: {pool_count} of {len(pool)} candidates")
    records_pool = pool_count
    if merges_on:
        print("\n### Records")
        records_pool = print_records(build_records(result, shots, row_groups), result)

    sampled = SAMPLE_SIZE
    if merges_on:
        sampled = write_outputs(rule3, names)
    print(f"Cross-season: {len(result.cross_season_cases)} Understat ids on 2+ FBref ids")
    print(f"merge_ids rows: {result.merge_ids_rows} | merged collisions: {result.merged_collisions} | anchors gone with their evidence: {result.anchors_removed} | refused merges: {result.refused_merges} | combined and outside the Pool: {result.combined_outside_pool} | left unjoined by reject: {result.unjoined_listed}")
    print(f"\n### Sample\n{sampled} of {len(name_map_file_rows(rule3, names.get))} name map pairs, seed {SAMPLE_SEED}, written to {SAMPLE_FILE.relative_to(ROOT)}")

    return count(final), pool_count, len(pool), {
        "no id collisions": not collisions,
        f"at least {MIN_JOINED_ROWS} rows joined": count(final) >= MIN_JOINED_ROWS,
        "Ezzalzouli approved": any(pair.name == "Abdessamad Ezzalzouli" and result[0] == "approved" for pair, result in guard.items()),
        f"sample holds {SAMPLE_SIZE} rows": sampled == SAMPLE_SIZE,
        "the records give the join's Pool": records_pool == pool_count,
    }


def main():
    unmerged = positions_for_join(merges=False)
    shots = load_shots()
    clubs = understat_to_fbref_clubs()
    merged, merges, refused = merge_fbref_ids(unmerged)
    with contextlib.redirect_stdout(io.StringIO()):
        joined_off, pool_off, candidates_off, _ = measure(unmerged, shots, clubs, refused, merges_on=False)
    joined_on, pool_on, candidates_on, checks = measure(merged, shots, clubs, refused, merges_on=True)
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
