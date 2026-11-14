"""Word map and level scale v1-draft, copied from docs/specs/claim-check-wordmap-v1-draft.md: players (#43), teams and leagues (#46).

DRAFT, NOT FROZEN: Ahmed's approval (#38) freezes v1. Until then every Verdict says "word map: DRAFT, not frozen".
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

WORD_MAP_VERSION = "v1-draft"
LEVEL_SCALE_VERSION = "v1-draft"
DRAFT_MARK = "word map: DRAFT, not frozen"


@dataclass(frozen=True)
class Threshold:
    """A percentile rule in the Claim's direction (D3). `first` and `last` are rank 1 and last in the Reference group."""
    rule: str  # at_least, above, at_most, below, between, first, last
    value: float = 0
    upper: float = 0

    def outcome(self, low, high, size):
        """meets, misses or borderline for an interval (Q9). `size` counts the Subject with its peers."""
        rule, value = self.rule, self.value
        if rule == "first":
            rule, value = "at_least", 100 * (size - 0.5) / size  # mid-rank percentile of a value above every peer
        if rule == "last":
            rule, value = "at_most", 100 * 0.5 / size
        meets, misses = {
            "at_least": (low >= value, high < value),
            "above": (low > value, high <= value),
            "at_most": (high <= value, low > value),
            "below": (high < value, low >= value),
            "between": (value <= low and high <= self.upper, high < value or low > self.upper),
        }[rule]
        return "meets" if meets else "misses" if misses else "borderline"

    def words(self):
        return {
            "at_least": f"top {100 - self.value:g}%", "above": "above the median", "at_most": f"bottom {self.value:g}%",
            "below": "below the median", "between": f"between the {self.value:g}th and {self.upper:g}th percentile",
            "first": "first", "last": "last",
        }[self.rule]


TOP_25 = Threshold("at_least", 75)  # no level word: >= 75th in the Claim's direction (so a negative word is <= 25th, Q6)

LEVEL_SCALE = {
    "the best": Threshold("first"), "the worst": Threshold("last"),
    "elite": Threshold("at_least", 90), "world-class": Threshold("at_least", 90), "one of the best": Threshold("at_least", 90),
    "great": TOP_25, "excellent": TOP_25, "very good": TOP_25, "top": TOP_25,
    "good": Threshold("at_least", 60),
    "above average": Threshold("above", 50),
    "average": Threshold("between", 25, 75),
    "below average": Threshold("below", 50),
    "poor": Threshold("at_most", 25), "bad": Threshold("at_most", 25),
    "terrible": Threshold("at_most", 10), "one of the worst": Threshold("at_most", 10),
}


@dataclass(frozen=True)
class WordRow:
    readings: tuple  # Claim types
    direction: str  # "more": a high Main metric meets it; "less": a low one does
    level: Optional[Threshold] = None  # built-in level; None: the Claim's level word, else TOP_25

# Players (word map v1-draft). "Finishing" here is Claim Check's Claim type, not Twin's shrunk metric (#36 name clash, #38).
PLAYER_WORDS = {
    "finisher": WordRow(("Finishing",), "more"), "finishing": WordRow(("Finishing",), "more"),
    "clinical": WordRow(("Finishing",), "more", TOP_25),
    "wasteful": WordRow(("Finishing",), "less", TOP_25),
    "deadly in front of goal": WordRow(("Finishing", "Goalscoring"), "more", TOP_25),
    "scores from distance": WordRow(("Finishing from distance",), "more", TOP_25), "great from range": WordRow(("Finishing from distance",), "more", TOP_25),
    "shoots a lot": WordRow(("Shot volume",), "more", TOP_25),
    "shy": WordRow(("Shot volume",), "less", TOP_25), "shot-shy": WordRow(("Shot volume",), "less", TOP_25),
    "gets into great positions": WordRow(("Shot quality",), "more", TOP_25),
    "takes bad shots": WordRow(("Shot quality",), "less", TOP_25),
    "dangerous": WordRow(("Goal threat",), "more", TOP_25), "goal threat": WordRow(("Goal threat",), "more", TOP_25),
    "prolific": WordRow(("Goalscoring",), "more", TOP_25), "scores a lot": WordRow(("Goalscoring",), "more", TOP_25),
    "goalscorer": WordRow(("Goalscoring",), "more"), "scorer": WordRow(("Goalscoring",), "more"),
    "creative": WordRow(("Chance creation",), "more", TOP_25), "creator": WordRow(("Chance creation",), "more", TOP_25),
    "involved in build-up": WordRow(("Build-up",), "more", TOP_25),
    "shoots from distance": WordRow(("Long shots",), "more", TOP_25), "long shots": WordRow(("Long shots",), "more", TOP_25),
    "good in the air": WordRow(("Aerial threat",), "more", Threshold("at_least", 60)), "aerial threat": WordRow(("Aerial threat",), "more", TOP_25),
    "ever-present": WordRow(("Availability",), "more", Threshold("at_least", 90)),
    "regular starter": WordRow(("Availability",), "more", TOP_25),
}

PLAYER_CANT_CHECK = {
    "injury-prone": "no injury data",
    **dict.fromkeys(("decent", "underrated", "overrated"), "claim word not in catalogue"),
    **dict.fromkeys(("dribbler", "dribbling", "presses", "pressing", "work rate", "hard-working", "pace", "quick", "fast", "passer", "passing range",
                     "tackler", "defends well", "leader", "most of his time", "own half", "off the ball"), "metric not in data"),
}

# Teams (word map v1-draft, spec "Word map v1: teams"). "Clinical" and "wasteful" map by Subject kind, so they are not ambiguous.
TEAM_WORDS = {
    "attacking": WordRow(("Attack",), "more", TOP_25), "free-scoring": WordRow(("Attack",), "more", TOP_25),
    "blunt": WordRow(("Attack",), "less", TOP_25),
    "solid": WordRow(("Defence",), "less", TOP_25), "tight at the back": WordRow(("Defence",), "less", TOP_25),
    "leaky": WordRow(("Defence",), "more", TOP_25),
    "defensive": WordRow(("Defence", "Game openness"), "less", TOP_25), "defensive football": WordRow(("Defence", "Game openness"), "less", TOP_25),
    "boring": WordRow(("Game openness",), "less", TOP_25), "park the bus": WordRow(("Game openness",), "less", TOP_25),
    "open": WordRow(("Game openness",), "more", TOP_25), "end-to-end": WordRow(("Game openness",), "more", TOP_25),
    "give up big chances": WordRow(("Chances conceded",), "more", TOP_25),
    "dominant": WordRow(("Dominance",), "more", TOP_25), "control games": WordRow(("Dominance",), "more", TOP_25),
    "clinical": WordRow(("Team finishing",), "more", TOP_25), "wasteful": WordRow(("Team finishing",), "less", TOP_25),
    "dangerous from set pieces": WordRow(("Set-piece threat",), "more", TOP_25),
    "weak at set pieces": WordRow(("Set-piece defence",), "more", TOP_25),
}
TEAM_CANT_CHECK = dict.fromkeys(("press", "pressing", "high press", "ppda", "possession", "direct", "long-ball", "high line", "counter-attacking",
                                 "on the counter", "formation", "wins", "results", "points"), "metric not in data")
# The Q4 ambiguity rule: each Reading of an ambiguous word is shown with its meaning.
MEANINGS = {("defensive", "Defence"): "they concede little", ("defensive", "Game openness"): "their games have few chances",
            ("defensive football", "Defence"): "they concede little", ("defensive football", "Game openness"): "their games have few chances"}

# Leagues (spec "Word map v1: leagues") and the league level scale: ranks among the 5, not percentiles.
LEAGUE_WORDS = {
    "open": ("Open or high-scoring", "more"), "high-scoring": ("Open or high-scoring", "more"),
    "defensive": ("Open or high-scoring", "less"), "defensive league": ("Open or high-scoring", "less"),
    "set-piece heavy": ("Set-piece league", "more"), "lots of long shots": ("Long-shot league", "more"),
}
LEAGUE_LEVELS = {"the most": (1, False), "one of the most": (2, False), "the least": (1, True), "one of the least": (2, True)}  # (top k, flips direction)

LEAGUE_NAMES = {"ENG": "the Premier League", "ESP": "La Liga", "GER": "the Bundesliga", "ITA": "Serie A", "FRA": "Ligue 1"}
SUBJECT_LEAGUE = "the Subject's league"  # "in the league": the Subject's league in the Window's latest season

# Reference group phrases v1-draft (`reference_named`): (league or None for all 5, Line or None for the Subject's Line).
REFERENCE_PHRASES = {
    **dict.fromkeys(("in the premier league", "in the epl", "in england"), ("ENG", None)),
    **dict.fromkeys(("in la liga", "in spain"), ("ESP", None)),
    **dict.fromkeys(("in the bundesliga", "in germany"), ("GER", None)),
    **dict.fromkeys(("in serie a", "in italy"), ("ITA", None)),
    **dict.fromkeys(("in ligue 1", "in france"), ("FRA", None)),
    "in the league": (SUBJECT_LEAGUE, None),
    **dict.fromkeys(("in europe", "in the top 5 leagues"), (None, None)),
    **dict.fromkeys(("for a forward", "for a striker"), (None, "Forward")),
    "for a winger": (None, "Wide"),
    **dict.fromkeys(("for an attacking midfielder", "for a number 10"), (None, "Central AM")),
    "for a midfielder": (None, "Central midfielder"),
    **dict.fromkeys(("for a full-back", "for a wing-back"), (None, "Full-back")),
    **dict.fromkeys(("for a centre-back", "for a defender"), (None, "Centre-back")),
}


class NotInCatalogue(ValueError):
    """A Can't check reason found while mapping words. `args[0]` is the reason, `args[1]` the words."""


@dataclass(frozen=True)
class Reading:
    claim_type: str
    direction: str
    threshold: Threshold
    level_word: Optional[str]  # the word that set the threshold, None for the bare >= 75th
    meaning: Optional[str] = None  # an ambiguous word's meaning for this Reading (Q4), e.g. "they concede little"


def tokens(text):
    """Case-insensitive, hyphen = space, accents dropped: the matching rules of word map v1-draft."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", plain)


def _same(claim_token, map_token):
    # Plain variants: plural (-s, -es) and "-ing".
    return claim_token == map_token or claim_token in (map_token + "s", map_token + "es", map_token + "ing") or (map_token.endswith("e") and claim_token == map_token[:-1] + "ing")


def _phrases(words=None, cant=None, levels=None):
    rows = [(tuple(tokens(phrase)), "level", phrase) for phrase in (LEVEL_SCALE if levels is None else levels)]
    rows += [(tuple(tokens(phrase)), "word", phrase) for phrase in (PLAYER_WORDS if words is None else words)]
    rows += [(tuple(tokens(phrase)), "cant", phrase) for phrase in (PLAYER_CANT_CHECK if cant is None else cant)]
    return sorted(rows, key=lambda row: -len(row[0]))  # the longest match wins


PHRASES = _phrases()
TEAM_PHRASES = _phrases(TEAM_WORDS, TEAM_CANT_CHECK)
LEAGUE_PHRASES = _phrases(LEAGUE_WORDS, {}, {**LEVEL_SCALE, **LEAGUE_LEVELS})
REFERENCE_KEYS = {" ".join(tokens(phrase)): rule for phrase, rule in REFERENCE_PHRASES.items()}


def match_words(claim_words, phrases=None):
    """[(kind, phrase)] for the Claim's words, longest phrase first. An unmatched word raises "claim word not in catalogue"."""
    found, unknown, words, at = [], [], tokens(" ".join(claim_words)), 0
    while at < len(words):
        for phrase, kind, name in (PHRASES if phrases is None else phrases):
            if len(phrase) <= len(words) - at and all(_same(word, token) for word, token in zip(words[at:], phrase)):
                found.append((kind, name))
                at += len(phrase)
                break
        else:
            unknown.append(words[at])
            at += 1
    if unknown:
        raise NotInCatalogue("claim word not in catalogue", " ".join(unknown))
    return found


def player_readings(claim_words, words_table=None, cant_table=None, phrases=None):
    """The Readings of a player (or team) Claim's words, in order (fail-safe reasons 4 and 5 raise NotInCatalogue)."""
    words_table = PLAYER_WORDS if words_table is None else words_table
    cant_table = PLAYER_CANT_CHECK if cant_table is None else cant_table
    found = match_words(claim_words, phrases)
    cant = sorted(((cant_table[name], name) for kind, name in found if kind == "cant"), key=lambda item: item[0] != "claim word not in catalogue")
    levels = [name for kind, name in found if kind == "level"]
    words = [name for kind, name in found if kind == "word"]
    if cant:  # "decent" (reason 4) before "pace" or "injury-prone" (reason 5)
        raise NotInCatalogue(*cant[0])
    if not words or len(levels) > 1:  # a level word alone, or two together, has no catalogue row
        raise NotInCatalogue("claim word not in catalogue", " ".join(levels))
    readings = []
    for name in words:
        row = words_table[name]
        level_word = levels[0] if levels else name if row.level else None
        threshold = LEVEL_SCALE[levels[0]] if levels else row.level or TOP_25
        readings += [Reading(claim_type, row.direction, threshold, level_word, MEANINGS.get((name, claim_type))) for claim_type in row.readings]
    return readings


def team_readings(claim_words):
    """The Readings of a team Claim: team words, the same level scale as players (Q6)."""
    return player_readings(claim_words, TEAM_WORDS, TEAM_CANT_CHECK, TEAM_PHRASES)


@dataclass(frozen=True)
class LeagueReading:
    claim_type: str
    direction: str  # after the level word: "the least open" reads as "less"
    top: int  # rank 1, or ranks 1-2
    level_word: str


def league_readings(claim_words):
    """League Readings. Only "the most", "one of the most", "the least" and "one of the least" fit a 5-league rank (league level scale)."""
    found = match_words(claim_words, LEAGUE_PHRASES)
    levels = [name for kind, name in found if kind == "level"]
    words = [name for kind, name in found if kind == "word"]
    if not words:
        raise NotInCatalogue("claim word not in catalogue", " ".join(levels))
    if len(levels) != 1 or levels[0] not in LEAGUE_LEVELS:
        raise NotInCatalogue("level word does not fit a 5-league comparison", " ".join(levels) or "no level word")
    top, flips = LEAGUE_LEVELS[levels[0]]
    readings = []
    for name in words:
        claim_type, direction = LEAGUE_WORDS[name]
        if flips:
            direction = "less" if direction == "more" else "more"
        readings.append(LeagueReading(claim_type, direction, top, levels[0]))
    return readings


def reference_rule(phrase):
    """(league, Line) for a `reference_named` phrase, (None, None) for the default; reason 4 if not in the catalogue."""
    if phrase is None:
        return None, None
    key = " ".join(tokens(phrase))
    if key not in REFERENCE_KEYS:
        raise NotInCatalogue("peer group not in catalogue", phrase)
    return REFERENCE_KEYS[key]
