"""The Extraction: the fixed JSON shape the LLM fills from a Claim (spec "The Extraction and the word map").

An Extraction that fails this shape gives Can't check with this data, reason "could not read the claim" (fail-safe reason 1).
"""
import re
from dataclasses import dataclass
from typing import Optional

FIELDS = {"form", "subjects", "claim_words", "comparison_words", "polarity", "tense", "seasons_named", "reference_named"}
KINDS = ("player", "team", "league", "match", "manager")  # match and manager are read, then "subject type not covered" (Q1)
SEASON = re.compile(r"\b(\d{4})\s*[/-]\s*(\d{2}|\d{4})\b")  # "2022/23", "2022-23", "2022/2023"


class Unreadable(ValueError):
    """The Extraction fails its shape."""


@dataclass(frozen=True)
class Subject:
    name: str
    kind: str


@dataclass(frozen=True)
class Extraction:
    form: str
    subjects: tuple
    claim_words: tuple
    comparison_words: Optional[str]
    polarity: str
    tense: str
    seasons_named: Optional[str]
    reference_named: Optional[str]


def season_span(text):
    """(first, last) start years named in verbatim season text: one season, or the first and last of a range."""
    found = []
    for start, end in SEASON.findall(text):
        start, end = int(start), int(end)
        if end % 100 != (start + 1) % 100 or (end >= 1000 and end != start + 1):
            raise Unreadable(f"seasons_named {text!r}: {start}/{end} is not one season")
        found.append(start)
    if len(found) not in (1, 2) or found != sorted(found):
        raise Unreadable(f"seasons_named {text!r}: not one season or one range")
    return found[0], found[-1]


def _text(value, field, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise Unreadable(f"{field} must be {'null or ' if optional else ''}a non-empty string")
    return value


def read_extraction(raw):
    if not isinstance(raw, dict) or set(raw) != FIELDS:
        raise Unreadable(f"the Extraction must hold exactly {sorted(FIELDS)}")
    if raw["form"] not in ("absolute", "comparison"):
        raise Unreadable(f"form {raw['form']!r}")
    subjects = raw["subjects"]
    if not isinstance(subjects, list) or len(subjects) != (1 if raw["form"] == "absolute" else 2):
        raise Unreadable("an absolute Claim holds 1 subject, a comparison 2")
    for found in subjects:
        if not isinstance(found, dict) or set(found) != {"name", "kind"} or found["kind"] not in KINDS:
            raise Unreadable(f"subject {found!r}")
        _text(found["name"], "subject name")
    words = raw["claim_words"]
    if not isinstance(words, list) or not words:
        raise Unreadable("claim_words must be a non-empty list")
    for word in words:
        _text(word, "claim word")
    _text(raw["comparison_words"], "comparison_words", optional=raw["form"] == "absolute")
    if raw["form"] == "absolute" and raw["comparison_words"] is not None:
        raise Unreadable("an absolute Claim has no comparison_words")
    if raw["polarity"] not in ("affirmed", "negated") or raw["tense"] not in ("present", "past"):
        raise Unreadable(f"polarity {raw['polarity']!r}, tense {raw['tense']!r}")
    if _text(raw["seasons_named"], "seasons_named", optional=True) is not None:
        season_span(raw["seasons_named"])
    _text(raw["reference_named"], "reference_named", optional=True)
    return Extraction(raw["form"], tuple(Subject(found["name"], found["kind"]) for found in subjects), tuple(words), raw["comparison_words"],
                      raw["polarity"], raw["tense"], raw["seasons_named"], raw["reference_named"])
