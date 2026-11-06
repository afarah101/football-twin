"""The stand-in loader: the stand-in files to one LoadedSource, behind the domain's Source interface.

It reads local files only, and builds the records from the join in player_join.py, so the measured numbers and the
records come from one version of the join. Stand-in flags stay in its review output: the domain sees only `held_for_review`.
"""
from collections import Counter
from typing import NamedTuple

import pandas as pd

from twin.domain.pool import in_pool
from twin.domain.records import LoadedSource, PlayerSeason, Shot
from twin.infrastructure.standin.player_join import (
    ATTACKING_POS, JoinResult, StandinFiles, build_rosters, finish_join, guard_facts, link_matches, load_positions, load_shots, merge_fbref_ids, pool_candidates,
    position_minutes, read_events, read_review_decisions, rule3_links, season_rows_by_name, season_totals, shot_groups, understat_to_fbref_clubs,
)

SOURCE = "standin"
PLAYER_SEASON_KEY = ["league", "Season_End_Year", "fbref_id"]


class StandinReview(NamedTuple):
    """What the stand-in lists for review and the #6 report (spec, "Where the rest goes")."""
    join: JoinResult
    season_totals: dict  # every PlayerSeason, as (league, FBref year, FBref id), to its SeasonTotals
    sub_status_unknown: list  # (league, season, match, FBref id): appearances in a match with no event rows, each counted as a start
    min_missing: list  # the same form: appearances with a null Min, kept with 0 minutes


class StandinRun(NamedTuple):
    loaded: LoadedSource
    review: StandinReview


def stop(message):
    raise SystemExit(f"stand-in records: {message}")


def text(value):
    return None if pd.isna(value) else str(value)


def first_by_count(counts):
    """{(league, year, id, value): count} to {(league, year, id): value}, the largest count first and a tie alphabetical (D7, D8)."""
    found = {}
    for (*key, value), _ in sorted(counts.items(), key=lambda item: (item[0][:3], -item[1], item[0][3])):
        found.setdefault(tuple(key), value)
    return found


def check_records(player_seasons, shots, positions):
    """D10 and D11. Each failure means a code fault, not a data case, so the way back is fixing the code."""
    repeated = sorted("|".join(map(str, key)) for key, count in Counter(found.key for found in player_seasons).items() if count > 1)
    if repeated:
        stop(f"two PlayerSeasons on one key: {repeated}")
    record_minutes = Counter()
    for found in player_seasons:
        record_minutes[(found.league, found.season)] += found.minutes
    fbref_minutes = {(league, year - 1): int(minutes) for (league, year), minutes in positions.groupby(["league", "Season_End_Year"])["Min"].sum().items()}
    for league, season in sorted(record_minutes.keys() | fbref_minutes.keys()):
        if record_minutes[(league, season)] != fbref_minutes.get((league, season), 0):
            stop(f"record minutes {record_minutes[(league, season)]} differ from the FBref rows' {fbref_minutes.get((league, season), 0)} in {league} {season}")
    keys = {found.key for found in player_seasons}
    lost = sorted({shot.player_id for shot in shots if (shot.league, shot.season, shot.player_id) not in keys})
    if lost:
        stop(f"Shot records with no PlayerSeason, player_id {lost}")
    # D4 fails the run or holds such a player first, so one here is a code fault (D11).
    no_totals = sorted("|".join(map(str, found.key)) for found in player_seasons if in_pool(found) and None in (found.xa, found.key_passes, found.xg_buildup, found.goals, found.assists))
    if no_totals:
        stop(f"PlayerSeasons in the Pool with no season totals: {no_totals}")


def build_records(result, shots, row_groups, files=StandinFiles()):
    """The records from the final join: every PlayerSeason of the Pool seasons, and every joined shot row."""
    positions = result.positions
    events = read_events(files)
    minutes = position_minutes(positions, events)
    totals = season_totals(result.facts, result.rule3.final, list(minutes.index))
    names = first_by_count({key: int(value) for key, value in positions.groupby([*PLAYER_SEASON_KEY, "Player"])["Min"].sum().items()})
    clubs = positions.groupby(PLAYER_SEASON_KEY)["Team"].agg(lambda found: tuple(sorted(set(found)))).to_dict()
    first_label = positions["Pos"].str.split(",").str[0]
    labelled = positions[first_label.isin(ATTACKING_POS)]
    display = first_by_count(Counter(zip(labelled["league"], labelled["Season_End_Year"], labelled["fbref_id"], first_label[labelled.index])))
    player_seasons = []
    for key, total, attacking, other in zip(minutes.index, minutes["total"], minutes["attacking"], minutes["other"]):
        league, year, fbref_id = key
        row = totals[key].row
        season_totals_of = (row.xa, row.key_passes, row.xg_buildup, row.goals, row.assists) if row is not None else (None,) * 5
        player_seasons.append(PlayerSeason(fbref_id, names[key], league, year - 1, clubs[key], int(total), int(attacking), int(other), display.get(key), *season_totals_of, key in result.flags))
    final = result.rule3.final
    columns = ["league", "season", "X", "Y", "xG", "situation", "shotType", "lastAction", "result"]
    shot_records = [
        Shot(final[group][1], league, int(season), float(x), float(y), float(xg), text(situation), text(shot_type), text(last_action), text(outcome))
        for group, (league, season, x, y, xg, situation, shot_type, last_action, outcome) in zip(row_groups, zip(*(shots[column] for column in columns)))
        if group in final
    ]
    check_records(player_seasons, shot_records, positions)
    event_matches = set(events["MatchURL"])
    appearances = list(zip(positions["league"], positions["Season_End_Year"] - 1, positions["match"], positions["fbref_id"], positions["MatchURL"], positions["Min"]))
    review = StandinReview(
        result, totals,
        sorted((league, int(season), match, fbref_id) for league, season, match, fbref_id, url, _ in appearances if url not in event_matches),
        sorted((league, int(season), match, fbref_id) for league, season, match, fbref_id, _, found in appearances if pd.isna(found)),
    )
    return StandinRun(LoadedSource(tuple(player_seasons), tuple(shot_records), SOURCE), review)


def load_standin(files=StandinFiles(), season_checks=True):
    """The whole stand-in run: id merges, rule 2, rule 3, the review decisions, then the records.

    `season_checks` stays on for data/standin. Only tests on the cut samples, whose players hold partial seasons, turn it off.
    """
    positions, _, refused = merge_fbref_ids(load_positions(files))
    shots = load_shots(files)
    clubs = understat_to_fbref_clubs(files)
    rows_of, row_groups = shot_groups(shots, link_matches(shots, positions, clubs).links, positions)
    rosters = build_rosters(positions)
    facts = guard_facts(positions, shots, season_rows_by_name(clubs, files))
    decisions = read_review_decisions(files.path("review_decisions.csv"))
    result = finish_join(rule3_links(rows_of, rosters, facts), rows_of, rosters, positions, decisions, refused, lambda found: pool_candidates(found, files), facts, season_checks=season_checks)
    return build_records(result, shots, row_groups, files)


class StandinLoader:
    """The stand-in source, behind the domain's Source interface."""

    def __init__(self, files=StandinFiles(), season_checks=True):
        self.files, self.season_checks = files, season_checks

    def load(self):
        return load_standin(self.files, self.season_checks).loaded
