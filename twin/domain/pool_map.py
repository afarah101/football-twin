"""The Pool map (#12): every Pool PlayerSeason placed in 2 dimensions by PCA on its z-scores.

The map is for position only, so no axis is named. Each component's sign is fixed so its largest loading is positive,
which keeps the picture the same from run to run.
"""
import numpy as np

MAP_DECIMALS = 3


def pca_points(peer_groups):
    """[(league, season, player_id, x, y)] for every MetricProfile, PCA fitted on the whole Pool."""
    members = [member for _, profiles in sorted(peer_groups.items()) for member in profiles]
    if len(members) < 3:
        return []
    z = np.array([member.values for member in members], dtype=float)
    centred = z - z.mean(axis=0)
    _, _, components = np.linalg.svd(centred, full_matrices=False)
    axes = components[:2]
    axes = axes * np.sign(axes[np.arange(2), np.abs(axes).argmax(axis=1)])[:, None]
    points = np.round(centred @ axes.T, MAP_DECIMALS)
    return [(member.player_season.league, member.player_season.season, member.player_season.player_id, float(x), float(y))
            for member, (x, y) in zip(members, points)]
