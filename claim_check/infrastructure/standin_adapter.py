"""Claim Check's stand-in adapter: PlayerMatch and TeamMatch records from Twin's stand-in join (#42).

A Conformist (ADR 0002): it runs Twin's stand-in loader and calls the join's own functions read-only, and it copies or
changes none of the join's rules. Two pins keep it in step with Twin on every load, and a failed pin is a Fault.
"""
from collections import Counter, defaultdict
from typing import NamedTuple

import pandas as pd

from claim_check.domain.records import SET_PIECE_SITUATIONS, PlayerMatch, TeamMatch
from twin.domain.pool import in_pool
from twin.domain.profiles import counts_for_metrics
from twin.domain.records import Shot
from twin.infrastructure.standin.loader import load_standin, text
from twin.infrastructure.standin.player_join import StandinFiles, link_matches, load_shots, position_minutes, read_events, shot_groups, understat_to_fbref_clubs

SHOT_COLUMNS = ["league", "season", "X", "Y", "xG", "situation", "shotType", "lastAction", "result"]  # as Twin's build_records reads them


class PinFailed(SystemExit):
    """A Fault: Claim Check and Twin read the join differently, so the run stops. Never a Verdict."""

    def __init__(self, pin, detail):
        super().__init__(f"Claim Check stand-in adapter: {pin} failed: {detail}. Way back: fix the adapter, never the pin (ADR 0002)")
        self.pin = pin


class StandinMatches(NamedTuple):
    loaded: object  # Twin's LoadedSource, unchanged
    positions: pd.DataFrame  # the join's FBref rows, merged ids, one per appearance
    player_matches: tuple
    team_matches: tuple


def substitute_rows(positions, events):
    """Twin's own rule for who came on, asked once per appearance: each row gets its own id and 1 minute, so its start minutes are 1, or 0 for a substitute."""
    rows = positions.assign(fbref_id=[str(index) for index in positions.index], Min=1)
    starts = position_minutes(rows, events)
    started = {fbref_id for (_, _, fbref_id), attacking, other in zip(starts.index, starts["attacking"], starts["other"]) if attacking + other}
    return [str(index) not in started for index in positions.index]


def team_matches(shot_records, groups, positions, linked):
    """Two TeamMatches per linked match, summed from every shot row in it, joined to a player or not."""
    sums = defaultdict(lambda: [0.0, 0.0, 0])
    for shot, group in zip(shot_records, groups):
        if group is not None and counts_for_metrics(shot):
            found = sums[(group.match, group.club)]
            found[0] += shot.xg
            found[1] += shot.xg if shot.situation in SET_PIECE_SITUATIONS else 0.0
            found[2] += 1
    records = []
    for row in positions.drop_duplicates("match").itertuples():
        if row.match not in linked:
            continue
        for team, opponent in ((row.Home_Team, row.Away_Team), (row.Away_Team, row.Home_Team)):
            own, other = sums[(row.match, team)], sums[(row.match, opponent)]
            records.append(TeamMatch(row.league, int(row.Season_End_Year) - 1, row.match, team, opponent, own[0], other[0], own[1], other[1], own[2], other[2]))
    return tuple(records)


def check_pins(loaded, player_matches):
    """Pin 1: the shots on PlayerMatches are exactly Twin's joined Shot records. Pin 2: their minutes sum to every Pool PlayerSeason's minutes."""
    ours, twins = Counter(shot for found in player_matches for shot in found.shots), Counter(loaded.shots)
    if ours != twins:
        raise PinFailed("pin 1", f"Claim Check holds {sum(ours.values())} joined shots, Twin holds {sum(twins.values())}, and {sum(((ours - twins) + (twins - ours)).values())} differ")
    minutes = Counter()
    for found in player_matches:
        minutes[(found.league, found.season, found.player_id)] += found.minutes
    wrong = sorted(f"{'|'.join(map(str, found.key))} {minutes[found.key]} v {found.minutes}" for found in loaded.player_seasons if in_pool(found) and minutes[found.key] != found.minutes)
    if wrong:
        raise PinFailed("pin 2", f"PlayerMatch minutes differ from Twin's season minutes for {len(wrong)} Pool PlayerSeasons: {wrong[:5]}")


def load_matches(files=StandinFiles(), season_checks=True):
    """Twin's stand-in run, then its join's match links read again (the same functions on the same files), turned into Claim Check records."""
    run = load_standin(files, season_checks)
    positions, final = run.review.join.positions, run.review.join.rule3.final
    shots = load_shots(files)
    linked = link_matches(shots, positions, understat_to_fbref_clubs(files)).links
    _, groups = shot_groups(shots, linked, positions)
    shot_records = [
        Shot(final[group][1] if group in final else None, league, int(season), float(x), float(y), float(xg), text(situation), text(shot_type), text(last_action), text(outcome))
        for group, (league, season, x, y, xg, situation, shot_type, last_action, outcome) in zip(groups, zip(*(shots[column] for column in SHOT_COLUMNS)))
    ]
    shots_of = defaultdict(list)
    for shot, group in zip(shot_records, groups):
        if group in final:
            shots_of[(shot.league, shot.season, group.match, shot.player_id)].append(shot)
    substitutes = substitute_rows(positions, read_events(files))
    player_matches = tuple(
        PlayerMatch(fbref_id, league, int(year) - 1, match, club, 0 if pd.isna(minutes) else int(minutes), pos.split(",")[0], substitute, tuple(shots_of[(league, int(year) - 1, match, fbref_id)]))
        for league, year, match, fbref_id, club, minutes, pos, substitute in zip(
            positions["league"], positions["Season_End_Year"], positions["match"], positions["fbref_id"], positions["Team"], positions["Min"], positions["Pos"], substitutes,
        )
    )
    check_pins(run.loaded, player_matches)
    return StandinMatches(run.loaded, positions, player_matches, team_matches(shot_records, groups, positions, set(linked.values())))
