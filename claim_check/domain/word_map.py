"""Word map and level scale v1-draft, players only (#43), copied from docs/specs/claim-check-wordmap-v1-draft.md.

DRAFT, NOT FROZEN: Ahmed's approval (#38) freezes v1. Until then every Verdict says "word map: DRAFT, not frozen".
Team and league rows come with their Verdicts in #46.
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


def tokens(text):
    """Case-insensitive, hyphen = space, accents dropped: the matching rules of word map v1-draft."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", plain)


def _same(claim_token, map_token):
    # Plain variants: plural (-s, -es) and "-ing".
    return claim_token == map_token or claim_token in (map_token + "s", map_token + "es", map_token + "ing") or (map_token.endswith("e") and claim_token == map_token[:-1] + "ing")


def _phrases():
    rows = [(tuple(tokens(phrase)), "level", phrase) for phrase in LEVEL_SCALE]
    rows += [(tuple(tokens(phrase)), "word", phrase) for phrase in PLAYER_WORDS]
    rows += [(tuple(tokens(phrase)), "cant", phrase) for phrase in PLAYER_CANT_CHECK]
    return sorted(rows, key=lambda row: -len(row[0]))  # the longest match wins


PHRASES = _phrases()
REFERENCE_KEYS = {" ".join(tokens(phrase)): rule for phrase, rule in REFERENCE_PHRASES.items()}


def match_words(claim_words):
    """[(kind, phrase)] for the Claim's words, longest phrase first. An unmatched word raises "claim word not in catalogue"."""
    found, unknown, words, at = [], [], tokens(" ".join(claim_words)), 0
    while at < len(words):
        for phrase, kind, name in PHRASES:
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


def player_readings(claim_words):
    """The Readings of a player Claim's words, in order (fail-safe reasons 4 and 5 raise NotInCatalogue)."""
    found = match_words(claim_words)
    cant = sorted(((PLAYER_CANT_CHECK[name], name) for kind, name in found if kind == "cant"), key=lambda item: item[0] != "claim word not in catalogue")
    levels = [name for kind, name in found if kind == "level"]
    words = [name for kind, name in found if kind == "word"]
    if cant:  # "decent" (reason 4) before "pace" or "injury-prone" (reason 5)
        raise NotInCatalogue(*cant[0])
    if not words or len(levels) > 1:  # a level word alone, or two together, has no catalogue row
        raise NotInCatalogue("claim word not in catalogue", " ".join(levels))
    readings = []
    for name in words:
        row = PLAYER_WORDS[name]
        level_word = levels[0] if levels else name if row.level else None
        threshold = LEVEL_SCALE[levels[0]] if levels else row.level or TOP_25
        readings += [Reading(claim_type, row.direction, threshold, level_word) for claim_type in row.readings]
    return readings


def reference_rule(phrase):
    """(league, Line) for a `reference_named` phrase, (None, None) for the default; reason 4 if not in the catalogue."""
    if phrase is None:
        return None, None
    key = " ".join(tokens(phrase))
    if key not in REFERENCE_KEYS:
        raise NotInCatalogue("peer group not in catalogue", phrase)
    return REFERENCE_KEYS[key]
