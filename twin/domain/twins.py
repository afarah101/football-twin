"""TwinMatches: each Pool PlayerSeason's closest PlayerSeasons by every Candidate method and the Basketball method (#9).

Twins can cross leagues, so each PlayerSeason gets two lists: all leagues and same league (plan step 7). A player's own
seasons never appear (plan step 4). Closeness is "closer than X% of all pairs", against every pair of two different
players in the Pool for that method (plan step 5).
"""
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from twin.domain.profiles import METRICS

CANDIDATE_METHODS = ("euclidean", "cosine", "pearson")
COMPARISON_METHODS = ("basketball",)  # Q20: reported beside the Candidate methods, never the default and never the winner
TOP = 10  # Q4: the site shows 5, with "show more" up to these 10
DISTANCE_DECIMALS = 9  # equal distances summed in a different order still tie, so the tie rule decides, not float noise


@dataclass(frozen=True)
class TwinMatch:
    player_season: object  # the PlayerSeason returned as a twin
    distance: float
    closeness: float  # percent of all pairs of two different players that are farther apart


@dataclass(frozen=True)
class TwinLists:
    all_leagues: tuple  # TwinMatches, closest first
    same_league: tuple


def percentiles(column):
    """Mid-rank percentiles within one PeerGroup: the share below, plus half the share equal."""
    values = np.asarray(column, dtype=float)
    below = (values[None, :] < values[:, None]).sum(axis=1)
    equal = (values[None, :] == values[:, None]).sum(axis=1)
    return 100 * (below + 0.5 * equal) / len(values)


def distance_matrix(vectors, method):
    if method in ("euclidean", "basketball"):
        return np.array([np.sqrt(((vectors - row) ** 2).sum(axis=1)) for row in vectors])
    if method == "pearson":
        vectors = vectors - vectors.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # A zero vector, as in a PeerGroup of one, has no direction: its similarity is 0, so its distance is 1.
    unit = np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms > 0)
    return 1 - unit @ unit.T


def method_vectors(members):
    """{method: one row per member}: z-scores for the Candidate methods, PeerGroup percentiles of the shrunk metrics for the Basketball method."""
    z = np.array([member.values for member in members], dtype=float)
    shrunk = np.array([member.shrunk for member in members], dtype=float)
    if not (np.isfinite(z).all() and np.isfinite(shrunk).all()):
        raise ValueError("twins: a MetricProfile holds a non-finite value, so no distance can rank it")
    basketball = np.empty_like(shrunk)
    rows_of = defaultdict(list)
    for row, member in enumerate(members):
        rows_of[(member.player_season.league, member.player_season.season)].append(row)
    for rows in rows_of.values():
        basketball[rows] = np.column_stack([percentiles(shrunk[rows, index]) for index in range(len(METRICS))])
    return {**{method: z for method in CANDIDATE_METHODS}, "basketball": basketball}


def twin_lists(peer_groups):
    """{(league, season): [MetricProfile]} to {method: {PlayerSeason key: TwinLists}}. Ties go to the smaller key."""
    members = sorted((member for group in peer_groups.values() for member in group), key=lambda member: member.player_season.key)
    ids = np.array([member.player_season.player_id for member in members])
    leagues = np.array([member.player_season.league for member in members])
    other_player = ids[:, None] != ids[None, :]
    pairs = np.triu(other_player, k=1)
    positions = np.arange(len(members))
    found = {}
    for method, vectors in method_vectors(members).items():
        distances = np.round(distance_matrix(vectors, method), DISTANCE_DECIMALS)
        reference = np.sort(distances[pairs])

        def matches(row, chosen):
            closeness = 100 * (len(reference) - np.searchsorted(reference, distances[row, chosen], side="right")) / max(len(reference), 1)
            return tuple(TwinMatch(members[other].player_season, float(distances[row, other]), float(share)) for other, share in zip(chosen, closeness))

        lists = {}
        for row, member in enumerate(members):
            order = np.lexsort((positions, distances[row]))
            order = order[other_player[row, order]]
            lists[member.player_season.key] = TwinLists(matches(row, order[:TOP]), matches(row, order[leagues[order] == leagues[row]][:TOP]))
        found[method] = lists
    return found
