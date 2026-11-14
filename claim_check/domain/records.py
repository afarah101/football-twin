"""Claim Check's match records, in its own words: one PlayerMatch per appearance, one TeamMatch per team per match.

Plain Python, no source word and no pandas. Shots are Twin's Shot records, reused as they are (ADR 0002).
"""
from dataclasses import dataclass
from typing import Optional

# The Line table (spec Q7): first-listed FBref position to Line.
LINE_OF_POSITION = {
    "FW": "Forward", "LW": "Wide", "RW": "Wide", "LM": "Wide", "RM": "Wide", "AM": "Central AM",
    "CM": "Central midfielder", "DM": "Central midfielder", "MF": "Central midfielder",
    "LB": "Full-back", "RB": "Full-back", "WB": "Full-back", "CB": "Centre-back", "DF": "Centre-back", "GK": "Goalkeeper",
}
SET_PIECE_SITUATIONS = ("FromCorner", "SetPiece", "DirectFreekick")  # spec Q4: set-piece xG


class UnknownPosition(ValueError):
    """A Fault: a start's first-listed position is not in the Line table, so its Line is unknown. The run stops; it never gets "no Line"."""


@dataclass(frozen=True)
class PlayerMatch:
    """One player's part in one match. Minutes count from every appearance, and a substitute appearance has no Line."""
    player_id: str  # the PlayerSeason's id: one person across seasons
    league: str
    season: int  # start year, so 2023 is 2023/24
    match: str
    club: str
    minutes: int
    position: str  # the first-listed position
    substitute: bool
    shots: tuple  # Twin Shot records

    @property
    def key(self):
        return self.league, self.season, self.match, self.player_id

    @property
    def line(self) -> Optional[str]:
        if self.substitute:
            return None
        if self.position not in LINE_OF_POSITION:
            raise UnknownPosition(f"PlayerMatch {'|'.join(map(str, self.key))}: position {self.position!r} is not in the Line table (Q7)")
        return LINE_OF_POSITION[self.position]


@dataclass(frozen=True)
class TeamMatch:
    """One team's side of one match. Every figure uses non-penalty shots with own goals left out, as Twin's metrics do."""
    league: str
    season: int
    match: str
    team: str
    opponent: str
    npxg_for: float
    npxg_against: float
    set_piece_xg_for: float
    set_piece_xg_against: float
    shots_for: int
    shots_against: int
