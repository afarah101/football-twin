"""The records a source returns, in the Twin model's own words, and the one interface every source implements.

No source word appears here, so the live adapter (#15) can replace the stand-in loader with no change to this module.
"""
from dataclasses import dataclass
from typing import Optional, Protocol

# Only this source can ever publish (spec, "The publishing guard").
PUBLISHING_SOURCE = "understat"


@dataclass(frozen=True)
class PlayerSeason:
    """One player's time in one league in one season. Every player of the source's seasons, defenders and players under 900 minutes too."""
    player_id: str  # one person across seasons
    name: str
    league: str
    season: int  # start year, so 2023 is 2023/24
    clubs: tuple
    minutes: int
    attacking_minutes: int  # substitute appearances ignored
    other_minutes: int
    display_position: Optional[str]  # most frequent first-listed attacking label, None if it has none
    xa: Optional[float]  # season totals: None when the source holds no single row for this PlayerSeason
    key_passes: Optional[int]
    xg_buildup: Optional[float]
    goals: Optional[int]
    assists: Optional[int]
    held_for_review: bool  # no shot or per-90 metric may be used

    @property
    def key(self):
        return self.league, self.season, self.player_id


@dataclass(frozen=True)
class Shot:
    """One shot of a PlayerSeason. Penalties and own goals stay in, because the metric criteria own that filter (#8)."""
    player_id: str
    league: str
    season: int
    x: float
    y: float
    xg: float
    situation: str
    shot_type: str
    last_action: Optional[str]
    result: str


@dataclass(frozen=True)
class LoadedSource:
    """What a source returns. Whether it may publish belongs to the source, so it sits here and not on the records."""
    player_seasons: tuple
    shots: tuple
    source: str
    may_publish: bool = False

    def __post_init__(self):
        # Runs on `dataclasses.replace` too, so no copy can raise it either.
        if self.may_publish and self.source != PUBLISHING_SOURCE:
            raise ValueError(f"source {self.source!r} may not publish: only {PUBLISHING_SOURCE!r} can, through its publishing gate")


class Source(Protocol):
    """The interface every source implements: the stand-in loader now, the live adapter in #15."""

    def load(self) -> LoadedSource:
        ...
