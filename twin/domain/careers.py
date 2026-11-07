"""CareerProfiles and their twin lists (#30): one person's Pool PlayerSeasons, averaged over the career.

A CareerProfile is the minutes-weighted mean of the person's season MetricProfiles, each stint with its own minutes and its
own PeerGroup z-scores (decisions 1 and 8, D30-7). Only a person with 6,000+ career minutes has one (D30-1). Its role group
is the one with the most career minutes (D30-4). Career closeness uses career pairs only (decision 3): all career pairs on
the all-roles list, and career pairs inside the role group on the same-role list, as the same-league season list does.
The role filter is the only career filter (D30-5). Percentiles for the Fingerprint are among all careers (D30-6).
"""
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from twin.domain.twins import CANDIDATE_METHODS, DISTANCE_DECIMALS, TOP, distance_matrix, percentiles

CAREER_MINUTES = 6000  # D30-1
ROLE_GROUPS = {"FW": "Forward", "LW": "Wide", "RW": "Wide", "AM": "Central AM"}  # #30 decision 7


@dataclass(frozen=True)
class CareerProfile:
    player_id: str  # one person across seasons
    name: str  # the name of the latest Pool PlayerSeason
    profiles: tuple  # the person's Pool MetricProfiles, by season, then league
    minutes: int  # career minutes: each stint's own minutes, summed (D30-7)
    role_group: str
    values: tuple  # minutes-weighted mean z-scores, in METRICS order

    @property
    def first_season(self):
        return self.profiles[0].player_season.season

    @property
    def last_season(self):
        return self.profiles[-1].player_season.season

    @property
    def season_count(self):
        """Distinct seasons, so a two-stint season counts once (D30-7)."""
        return len({profile.player_season.season for profile in self.profiles})


@dataclass(frozen=True)
class CareerMatch:
    career: CareerProfile
    distance: float
    closeness: float  # percent of the list's reference career pairs that are farther apart


@dataclass(frozen=True)
class CareerLists:
    all_roles: tuple  # CareerMatches, closest first
    same_role: tuple


def role_group(profiles):
    """The role group with the most career minutes (D30-4). profiles are in season order."""
    minutes = defaultdict(int)
    for profile in profiles:
        minutes[ROLE_GROUPS[profile.player_season.display_position]] += profile.player_season.minutes
    most = max(minutes.values())
    # shortcut: a tie goes to the latest Pool season's group; 0 ties in the full data (T30), ask Ahmed if one appears
    return next(ROLE_GROUPS[profile.player_season.display_position] for profile in reversed(profiles) if minutes[ROLE_GROUPS[profile.player_season.display_position]] == most)


def career_profiles(peer_groups, career_minutes=CAREER_MINUTES):
    """{(league, season): [MetricProfile]} to the CareerProfiles at or above `career_minutes`, by player_id.

    `career_minutes` is the bar. Only tests set it lower, because the cut sample holds no 6,000-minute career.
    """
    seasons = defaultdict(list)
    for members in peer_groups.values():
        for profile in members:
            seasons[profile.player_season.player_id].append(profile)
    found = []
    for player_id, profiles in sorted(seasons.items()):
        profiles.sort(key=lambda profile: (profile.player_season.season, profile.player_season.league))
        weights = np.array([profile.player_season.minutes for profile in profiles], dtype=float)
        minutes = int(weights.sum())
        if minutes < career_minutes:
            continue
        values = weights @ np.array([profile.values for profile in profiles], dtype=float) / minutes
        found.append(CareerProfile(player_id, profiles[-1].player_season.name, tuple(profiles), minutes, role_group(profiles), tuple(float(value) for value in values)))
    return found


def career_percentiles(careers):
    """{player_id: percentiles in METRICS order}: mid-rank percentiles of each career value among all careers (D30-6)."""
    if not careers:
        return {}
    values = np.array([career.values for career in careers], dtype=float)
    columns = np.column_stack([percentiles(values[:, index]) for index in range(values.shape[1])])
    return {career.player_id: tuple(float(value) for value in row) for career, row in zip(careers, columns)}


def career_matches(careers, row_distances, chosen, reference):
    closeness = 100 * (len(reference) - np.searchsorted(reference, row_distances[chosen], side="right")) / max(len(reference), 1)
    return tuple(CareerMatch(careers[other], float(row_distances[other]), float(share)) for other, share in zip(chosen, closeness))


def career_lists(careers):
    """{method: {player_id: CareerLists}} for every Candidate method, on the careers' z-score means (decision 4). Ties go to the smaller player_id."""
    if not careers:
        return {method: {} for method in CANDIDATE_METHODS}
    careers = sorted(careers, key=lambda career: career.player_id)
    vectors = np.array([career.values for career in careers], dtype=float)
    groups = np.array([career.role_group for career in careers])
    positions = np.arange(len(careers))
    pairs = np.triu(np.ones((len(careers), len(careers)), dtype=bool), k=1)
    role_pairs = {group: pairs & (groups[:, None] == group) & (groups[None, :] == group) for group in sorted(set(groups))}
    found = {}
    for method in CANDIDATE_METHODS:
        distances = np.round(distance_matrix(vectors, method), DISTANCE_DECIMALS)
        reference = np.sort(distances[pairs])
        role_reference = {group: np.sort(distances[mask]) for group, mask in role_pairs.items()}
        lists = {}
        for row, career in enumerate(careers):
            order = np.lexsort((positions, distances[row]))
            order = order[order != row]
            same = order[groups[order] == groups[row]]
            lists[career.player_id] = CareerLists(
                career_matches(careers, distances[row], order[:TOP], reference),
                career_matches(careers, distances[row], same[:TOP], role_reference[groups[row]]),
            )
        found[method] = lists
    return found
