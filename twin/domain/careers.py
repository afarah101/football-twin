"""CareerProfiles and their twin lists (#30): one person's Pool PlayerSeasons, averaged over the career.

A CareerProfile is the minutes-weighted mean of the person's season MetricProfiles, each stint with its own minutes and its
own PeerGroup z-scores (decisions 1 and 8, D30-7). #29: only twin-eligible stints (1,350+ minutes) count, and a person needs
them in 3+ different seasons to have one (this replaces D30-1's 6,000 career minutes; Ahmed decides). Its role group
is the one with the most career minutes (D30-4). Career closeness is against all career pairs (decision 3), on both lists,
so a twin keeps its closeness when the role filter toggles (D30-9). The role filter is the only career filter (D30-5). Percentiles for the Fingerprint are among all careers (D30-6).
"""
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from twin.domain.twins import CANDIDATE_METHODS, DISTANCE_DECIMALS, TOP, TWIN_MINUTES, distance_matrix, percentiles

CAREER_MINUTES = 0  # #29: no career-minutes bar; D30-1's 6,000 is replaced by the two rules below (needs Ahmed: #29 v D30-1)
CAREER_SEASONS = 3  # #29 decision 3: twin-eligible seasons in 3 or more different seasons
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
    closeness: float  # percent of all career pairs that are farther apart (D30-9)


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


def career_profiles(peer_groups, career_minutes=CAREER_MINUTES, eligible_minutes=TWIN_MINUTES, career_seasons=CAREER_SEASONS):
    """{(league, season): [MetricProfile]} to the CareerProfiles, by player_id.

    #29: a career averages only the twin-eligible stints (`eligible_minutes`, decisions 1-2), and needs them in `career_seasons`
    different seasons (decision 3). `career_minutes` is an extra total bar, 0 under #29. Only tests set the rules lower,
    because the cut sample holds partial seasons.
    """
    seasons = defaultdict(list)
    for members in peer_groups.values():
        for profile in members:
            seasons[profile.player_season.player_id].append(profile)
    found = []
    for player_id, profiles in sorted(seasons.items()):
        profiles = sorted((profile for profile in profiles if profile.player_season.minutes >= eligible_minutes),
                          key=lambda profile: (profile.player_season.season, profile.player_season.league))
        if len({profile.player_season.season for profile in profiles}) < max(career_seasons, 1):
            continue
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
    found = {}
    for method in CANDIDATE_METHODS:
        distances = np.round(distance_matrix(vectors, method), DISTANCE_DECIMALS)
        reference = np.sort(distances[pairs])
        lists = {}
        for row, career in enumerate(careers):
            order = np.lexsort((positions, distances[row]))
            order = order[order != row]
            same = order[groups[order] == groups[row]]
            lists[career.player_id] = CareerLists(
                career_matches(careers, distances[row], order[:TOP], reference),
                career_matches(careers, distances[row], same[:TOP], reference),
            )
        found[method] = lists
    return found
