"""TwinMatches: each Pool PlayerSeason's closest PlayerSeasons by every Candidate method and the Basketball method (#9).

Twins can cross leagues, so each PlayerSeason gets two lists: all leagues and same league (plan step 7). A player's own
seasons never appear (plan step 4), and each other player fills one slot, with his closest season (Ahmed, 6 Nov 2026).
Closeness is "closer than X% of all pairs" (plan step 5): on the all-leagues list against every pair of two different
players in the Pool for that method, and on the same-league list against those pairs inside that league only (Ahmed, 6 Nov 2026).
"""
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from twin.domain.profiles import METRICS

CANDIDATE_METHODS = ("euclidean", "cosine", "pearson")
COMPARISON_METHODS = ("basketball",)  # Q20: reported beside the Candidate methods, never the default and never the winner
TWIN_MINUTES = 1350  # #29 decision 2: a PlayerSeason is twin-eligible at 1,350+ minutes; the Pool rule (900) does not change
TOP = 10  # Q4: the site shows 5, with "show more" up to these 10
DISTANCE_DECIMALS = 9  # equal distances summed in a different order still tie, so the tie rule decides, not float noise


@dataclass(frozen=True)
class TwinMatch:
    player_season: object  # the PlayerSeason returned as a twin
    distance: float
    closeness: float  # percent of the list's reference pairs of two different players that are farther apart


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


def one_slot_each(order, ids):
    """The first, so closest, season of each player in `order`, up to TOP players."""
    _, first = np.unique(ids[order], return_index=True)
    return order[np.sort(first)][:TOP]


def twin_matches(members, row_distances, chosen, reference):
    """TwinMatches for the rows `chosen`, with closeness against the sorted `reference` pair distances."""
    closeness = 100 * (len(reference) - np.searchsorted(reference, row_distances[chosen], side="right")) / max(len(reference), 1)
    return tuple(TwinMatch(members[other].player_season, float(row_distances[other]), float(share)) for other, share in zip(chosen, closeness))


def twin_lists(peer_groups, twin_minutes=None):
    """{(league, season): [MetricProfile]} to {method: {PlayerSeason key: TwinLists}}. Ties go to the smaller key.

    Every Pool PlayerSeason gets lists, but only a twin-eligible one (#29: `twin_minutes`, 1,350 by default) appears in any list.
    Closeness stays against every pair of two different players in the Pool.
    """
    twin_minutes = TWIN_MINUTES if twin_minutes is None else twin_minutes
    members = sorted((member for group in peer_groups.values() for member in group), key=lambda member: member.player_season.key)
    ids = np.array([member.player_season.player_id for member in members])
    leagues = np.array([member.player_season.league for member in members])
    other_player = ids[:, None] != ids[None, :]
    pairs = np.triu(other_player, k=1)
    eligible = np.array([member.player_season.minutes >= twin_minutes for member in members], dtype=bool)
    league_pairs = {league: pairs & (leagues[:, None] == league) & (leagues[None, :] == league) for league in sorted(set(leagues))}
    positions = np.arange(len(members))
    found = {}
    for method, vectors in method_vectors(members).items():
        distances = np.round(distance_matrix(vectors, method), DISTANCE_DECIMALS)
        reference = np.sort(distances[pairs])
        league_reference = {league: np.sort(distances[mask]) for league, mask in league_pairs.items()}
        lists = {}
        for row, member in enumerate(members):
            order = np.lexsort((positions, distances[row]))
            order = order[other_player[row, order] & eligible[order]]
            same = order[leagues[order] == leagues[row]]  # filter the league first, so a player's closest season in this league is kept
            lists[member.player_season.key] = TwinLists(
                twin_matches(members, distances[row], one_slot_each(order, ids), reference),
                twin_matches(members, distances[row], one_slot_each(same, ids), league_reference[leagues[row]]),
            )
        found[method] = lists
    return found
