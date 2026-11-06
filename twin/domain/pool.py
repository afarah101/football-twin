"""The Pool rule, the one version: 900 or more minutes, attacking minutes above other minutes, and not held for review."""
POOL_MINUTES = 900


def is_pool_candidate(minutes, attacking_minutes, other_minutes):
    """Plan line 107. Equal attacking and other minutes stays out (plan line 120)."""
    return minutes >= POOL_MINUTES and attacking_minutes > other_minutes


def in_pool(player_season):
    """A candidate that a review flag holds stays out until reviewed."""
    return is_pool_candidate(player_season.minutes, player_season.attacking_minutes, player_season.other_minutes) and not player_season.held_for_review
