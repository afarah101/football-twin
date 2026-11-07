"""MetricProfiles: the 10 metrics of each Pool PlayerSeason, shrunk and standardised within its PeerGroup (plan, Metrics and Method).

Shares shrink by beta-binomial and npxG per shot by normal-normal, both by method of moments (plan step 1, Q8). Per-90
metrics stay unshrunk. Every metric is z-scored within the PeerGroup and clipped at ±3 (plan step 2).
"""
import math
from collections import defaultdict
from dataclasses import dataclass

from twin.domain.pool import in_pool

# Q16, calibrated in docs/reports/T3_step0_facts.md. Inside a box: X at or above the X line, Y between the Y lines, inclusive.
BOX_X_MIN, BOX_Y_MIN, BOX_Y_MAX = 0.8275, 0.2075, 0.7925
SIX_X_MIN, SIX_Y_MIN, SIX_Y_MAX = 0.9425, 0.365, 0.635
Z_CLIP = 3.0

PER_90 = ("shots_per_90", "xa_per_90", "key_passes_per_90", "xg_buildup_per_90")
SHARES = ("six_yard_share", "outside_box_share", "header_share", "take_on_share", "through_ball_share")
METRICS = PER_90 + ("npxg_per_shot",) + SHARES


def in_box(shot, x_min, y_min, y_max):
    return shot.x >= x_min and y_min <= shot.y <= y_max


SHARE_TESTS = {
    "six_yard_share": lambda shot: in_box(shot, SIX_X_MIN, SIX_Y_MIN, SIX_Y_MAX),
    "outside_box_share": lambda shot: not in_box(shot, BOX_X_MIN, BOX_Y_MIN, BOX_Y_MAX),
    "header_share": lambda shot: shot.shot_type == "Head",
    "take_on_share": lambda shot: shot.last_action == "TakeOn",
    "through_ball_share": lambda shot: shot.last_action == "Throughball",
}


def counts_for_metrics(shot):
    """Q15: shares, npxG per shot and shots per 90 use non-penalty shots, own goals excluded."""
    return shot.situation != "Penalty" and shot.result != "OwnGoal"


@dataclass(frozen=True)
class RawMetrics:
    """One PlayerSeason's metrics before shrinkage: per-90 values, its shot xGs, and its count for each share."""
    shots_per_90: float
    xa_per_90: float
    key_passes_per_90: float
    xg_buildup_per_90: float
    npxg_per_shot: float  # nan with no non-penalty shot: shrinkage gives it the PeerGroup mean
    shot_xgs: tuple
    share_counts: tuple  # in SHARES order


@dataclass(frozen=True)
class DisplayStats:
    """Shown to the reader, never part of a MetricProfile."""
    goals: int
    assists: int
    npg_minus_npxg: float


@dataclass(frozen=True)
class MetricProfile:
    player_season: object  # the PlayerSeason it describes
    values: tuple  # z-scores, in METRICS order
    shrunk: tuple  # the values before the z-score, in METRICS order: the Basketball method's input (Q20)
    display_stats: DisplayStats


def raw_metrics(player_season, shots):
    """`shots` are this PlayerSeason's Shot records. Season totals give the other per-90 metrics."""
    kept = [shot for shot in shots if counts_for_metrics(shot)]
    per_90 = 90 / player_season.minutes
    xgs = tuple(shot.xg for shot in kept)
    return RawMetrics(
        len(kept) * per_90, player_season.xa * per_90, player_season.key_passes * per_90, player_season.xg_buildup * per_90,
        sum(xgs) / len(xgs) if xgs else math.nan, xgs, tuple(sum(1 for shot in kept if SHARE_TESTS[share](shot)) for share in SHARES),
    )


def display_stats(player_season, shots):
    kept = [shot for shot in shots if counts_for_metrics(shot)]
    return DisplayStats(player_season.goals, player_season.assists, sum(1 for shot in kept if shot.result == "Goal") - sum(shot.xg for shot in kept))


def beta_binomial_prior(successes, trials):
    """Method of moments for unequal trials: (prior mean, prior size alpha + beta). Size inf means no between-player spread."""
    total = sum(trials)
    if not total:
        return math.nan, math.inf
    mean = sum(successes) / total
    groups = sum(1 for n in trials if n)
    denominator = total - sum(n * n for n in trials) / total - (groups - 1)
    if mean in (0.0, 1.0) or denominator <= 0:
        return mean, math.inf
    spread = sum(n * (k / n - mean) ** 2 for k, n in zip(successes, trials) if n)
    rho = (spread / (mean * (1 - mean)) - (groups - 1)) / denominator  # 1 / (alpha + beta + 1)
    if rho <= 0:
        return mean, math.inf
    return mean, 0.0 if rho >= 1 else 1 / rho - 1


def shrunk_shares(successes, trials):
    mean, size = beta_binomial_prior(successes, trials)
    if size == math.inf:
        return [mean] * len(trials)
    return [(k + mean * size) / (n + size) if n + size else mean for k, n in zip(successes, trials)]


def normal_normal_prior(groups):
    """One-way method of moments on each player's values: (grand mean, between-player variance, within-player variance)."""
    filled = [group for group in groups if group]
    total = sum(len(group) for group in filled)
    if not total:
        return math.nan, 0.0, 0.0
    mean = sum(sum(group) for group in filled) / total
    means = [sum(group) / len(group) for group in filled]
    within = sum((value - group_mean) ** 2 for group, group_mean in zip(filled, means) for value in group) / (total - len(filled)) if total > len(filled) else 0.0
    spread = sum(len(group) * (group_mean - mean) ** 2 for group, group_mean in zip(filled, means))
    denominator = total - sum(len(group) ** 2 for group in filled) / total
    between = max(0.0, (spread - (len(filled) - 1) * within) / denominator) if denominator > 0 else 0.0
    return mean, between, within


def shrunk_means(groups):
    mean, between, within = normal_normal_prior(groups)
    if not between:
        return [mean] * len(groups)
    return [mean + between / (between + within / len(group)) * (sum(group) / len(group) - mean) if group else mean for group in groups]


def z_scores(values):
    """Population standard deviation within the PeerGroup. With no spread, every z is 0."""
    mean = sum(values) / len(values)
    deviation = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
    if not deviation:
        return [0.0] * len(values)
    return [max(-Z_CLIP, min(Z_CLIP, (value - mean) / deviation)) for value in values]


def peer_group_profiles(player_seasons, shots):
    """{(league, season): [MetricProfile]} for every Pool PlayerSeason, each PeerGroup standardised alone."""
    shots_of = defaultdict(list)
    for shot in shots:
        shots_of[(shot.league, shot.season, shot.player_id)].append(shot)
    peer_groups = defaultdict(list)
    for found in player_seasons:
        if in_pool(found):
            peer_groups[(found.league, found.season)].append(found)
    profiles = {}
    for key, members in sorted(peer_groups.items()):
        members.sort(key=lambda found: found.player_id)
        raws = [raw_metrics(found, shots_of[found.key]) for found in members]
        trials = [len(raw.shot_xgs) for raw in raws]
        columns = [[getattr(raw, metric) for raw in raws] for metric in PER_90]
        columns.append(shrunk_means([raw.shot_xgs for raw in raws]))
        columns += [shrunk_shares([raw.share_counts[index] for raw in raws], trials) for index in range(len(SHARES))]
        z_columns = [z_scores(column) for column in columns]
        profiles[key] = [
            MetricProfile(found, tuple(column[row] for column in z_columns), tuple(column[row] for column in columns), display_stats(found, shots_of[found.key]))
            for row, found in enumerate(members)
        ]
    return profiles
