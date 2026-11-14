"""Pooled player Verdicts (#43): an Extraction and the stand-in's records in, one Verdict per Reading out (Seam 1).

Rules: Reference groups (Q7, D1-D2), the shot minimum (Q7), the bootstrap and strict Verdict rule (Q9, ADR 0003), polarity
(Q5), the fail-safe reasons in check order and the coverage line (Q12, Q13). Per-season, season-totals, team and league
Claim types come in #44, #45 and #46: until then they stop with an error, never a Verdict.
Per-season player Verdicts (#44): Shot volume, Goal threat, Goalscoring, Aerial threat (2 Main metrics) and Availability.
Each qualifying season is a test against that season's Reference group (D1), bootstrapped over the Subject's PlayerMatches.
"""
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

from claim_check.domain.extraction import Unreadable, read_extraction, season_span
from claim_check.domain.word_map import DRAFT_MARK, LEAGUE_NAMES, LEVEL_SCALE_VERSION, SUBJECT_LEAGUE, WORD_MAP_VERSION, NotInCatalogue, player_readings, reference_rule, tokens
from twin.domain.profiles import SHARE_TESTS, counts_for_metrics
from twin.domain.twins import percentiles

SEASONS = tuple(range(2017, 2024))  # the stand-in window, 2017/18-2023/24 (start years)
PRESENT = SEASONS[-3:]  # present tense, no season named: the last 3 seasons (Q2)
QUALIFY_MINUTES = 900
PLAYER_REFERENCE_MINIMUM = 30
SHOT_MINIMUM = 40  # proposed by the spec's measurement; Ahmed's freeze ticket (#38) may change it
RESAMPLES, SEED, INTERVAL = 1000, 43, 80
METHOD = (f"method stand-in-2: bootstrap of {RESAMPLES:,} resamples of the Subject's shots (Pooled metrics) or PlayerMatches "
          f"(per-season metrics), seed {SEED}, {INTERVAL}% interval, Twin's mid-rank percentiles")
DATA_END = "Data to 2023/24"
PRESENT_WARNING = "Our data ends in 2023/24. This verdict may not match the current season."
SUPPORTED, MIXED, NOT_SUPPORTED, CANT = "Supported", "Mixed", "Not supported", "Can't check with this data"
FLIP = {SUPPORTED: NOT_SUPPORTED, NOT_SUPPORTED: SUPPORTED}  # polarity: Mixed and Can't check stay as they are
REASONS = (  # the fail-safe check order (spec "Fail-safe for missing data"): the first that fails is the one reason
    "could not read the claim", "subject type not covered", "subject not in data", "subject is ambiguous",
    "claim word not in catalogue", "peer group not in catalogue", "level word does not fit a 5-league comparison",
    "metric not in data", "no injury data", "season not in data", "too few minutes", "held for review", "too few shots",
    "season totals missing", "peer group too small",
)
LINE_WORDS = {"Forward": "forwards", "Wide": "wide players", "Central AM": "central attacking midfielders", "Central midfielder": "central midfielders",
              "Full-back": "full-backs", "Centre-back": "centre-backs", "Goalkeeper": "goalkeepers"}
outside_box = SHARE_TESTS["outside_box_share"]


def finishing(shots):
    return sum((shot.result == "Goal") - shot.xg for shot in shots) / len(shots)


@dataclass(frozen=True)
class PooledMetric:
    main_metric: str
    counts: object  # which non-penalty shots the metric is taken on
    value: object
    unit: str  # how a value reads, filled by format
    shots_words: str = ""


POOLED = {
    "Finishing": PooledMetric("(non-penalty goals − npxG) per non-penalty shot", lambda shot: True, finishing, "{:+.3f} goals minus npxG per shot"),
    "Finishing from distance": PooledMetric("(npG − npxG) per shot, on shots from outside the box", outside_box, finishing,
                                            "{:+.3f} goals minus npxG per shot from outside the box", " from outside the box"),
    "Shot quality": PooledMetric("npxG per shot", lambda shot: True, lambda shots: sum(shot.xg for shot in shots) / len(shots), "{:.3f} npxG per shot"),
    "Long shots": PooledMetric("share of shots from outside the box", lambda shot: True, lambda shots: sum(map(outside_box, shots)) / len(shots),
                               "{:.1%} of shots from outside the box"),
}


def per_90(count, matches):
    minutes = sum(found.minutes for found in matches)
    return 90 * count / minutes if minutes else 0.0


def np_shots(matches):
    return [shot for found in matches for shot in found.shots if counts_for_metrics(shot)]


def is_header(shot):
    return shot.shot_type == "Head"


@dataclass(frozen=True)
class SeasonMetric:
    """One Main metric of a per-season Claim type. `value` takes one PlayerSeason's PlayerMatches and the league-season's match count."""
    name: str
    value: object
    unit: str


PER_SEASON = {  # spec "Claim-type catalogue, players"
    "Shot volume": (SeasonMetric("non-penalty shots per 90", lambda m, n: per_90(len(np_shots(m)), m), "{:.2f} non-penalty shots per 90"),),
    "Goal threat": (SeasonMetric("npxG per 90", lambda m, n: per_90(sum(shot.xg for shot in np_shots(m)), m), "{:.2f} npxG per 90"),),
    "Goalscoring": (SeasonMetric("non-penalty goals per 90", lambda m, n: per_90(sum(shot.result == "Goal" for shot in np_shots(m)), m),
                                 "{:.2f} non-penalty goals per 90"),),
    "Aerial threat": (
        SeasonMetric("headed shots per 90", lambda m, n: per_90(sum(map(is_header, np_shots(m))), m), "{:.2f} headed shots per 90"),
        SeasonMetric("headed npxG per 90", lambda m, n: per_90(sum(shot.xg for shot in np_shots(m) if is_header(shot)), m), "{:.3f} headed npxG per 90"),
    ),
    # Share of league minutes played: the Subject's minutes over the league-season's matches per club x 90.
    "Availability": (SeasonMetric("share of league minutes played", lambda m, n: sum(found.minutes for found in m) / (90 * n) if n else 0.0,
                                  "{:.1%} of league minutes"),),
}
CONTEXT = {  # shown, never the Verdict (spec: Context metric column)
    "Aerial threat": ("header share of shots", lambda m: (sum(map(is_header, np_shots(m))) / len(np_shots(m))) if np_shots(m) else 0.0, "{:.0%} of shots headed"),
}


@dataclass(frozen=True)
class Test:
    value: float
    value_words: str
    shots: int
    percentile: float  # mid-rank, in the Claim's direction (D3)
    interval: tuple  # (low, high): the 80% interval of the resampled percentile
    outcome: str  # meets, misses or borderline
    label: Optional[str] = None  # per-season tests: the season, and the Main metric when there are 2
    matches: Optional[int] = None  # per-season tests: the PlayerMatches resampled
    reference_size: Optional[int] = None  # per-season tests: that season's peers


@dataclass(frozen=True)
class ClaimQuery:
    subject: str
    subject_id: str
    claim_type: str
    main_metric: str
    direction: str
    threshold: str
    window: tuple  # (first, last) start years
    reference_group: dict  # league (None: all 5) and Line


@dataclass(frozen=True)
class ReadingVerdict:
    claim_type: Optional[str]  # None when the whole Claim is Can't check before any Reading
    verdict: str
    reason: Optional[str]
    detail: Optional[str] = None
    claim_query: Optional[ClaimQuery] = None
    threshold: Optional[str] = None
    test: Optional[Test] = None
    reference_group: Optional[str] = None
    reference_size: Optional[int] = None
    seasons: Optional[str] = None
    coverage: Optional[str] = None
    thin: bool = False
    seasons_alone: tuple = ()  # context only, never the Verdict
    tests: tuple = ()  # per-season Claim types: one Test per qualifying season (and per Main metric)


@dataclass(frozen=True)
class ClaimVerdict:
    claim: str
    extraction: object  # as given
    subject: Optional[str]
    polarity: Optional[str]
    readings: tuple
    warning: Optional[str] = None
    data_end: str = DATA_END
    word_map: str = WORD_MAP_VERSION
    level_scale: str = LEVEL_SCALE_VERSION
    draft: str = DRAFT_MARK
    method: str = METHOD
    blocked_words: Optional[str] = None  # no Summary lines before #48
    llm_model: Optional[str] = None  # no LLM before #47


def season_label(season):
    return f"{season}/{(season + 1) % 100:02d}"


def window_label(window):
    return season_label(window[0]) if len(window) == 1 else f"{season_label(window[0])}-{season_label(window[-1])}"


def resolve(name, player_seasons):
    """{player_id: latest PlayerSeason} for every person whose name holds the Subject's name as whole words."""
    query, found = tokens(name), {}
    for season in player_seasons:
        words = tokens(season.name)
        if any(words[at:at + len(query)] == query for at in range(len(words) - len(query) + 1)):
            best = found.get(season.player_id)
            if best is None or (season.season, season.minutes) > (best.season, best.minutes):
                found[season.player_id] = season
    return found


def percentile_of(value, peer_values, direction):
    """Twin's mid-rank percentile of one value among its peers, in the Claim's direction."""
    point = float(percentiles(peer_values + [value])[-1])
    return point if direction == "more" else 100 - point


def bootstrap(shots, metric, peer_values, direction):
    """The 80% interval of the percentile over RESAMPLES resamples of the Subject's shots, against the fixed peers."""
    draw = random.Random(SEED)
    found = sorted(percentile_of(metric.value(draw.choices(shots, k=len(shots))), peer_values, direction) for _ in range(RESAMPLES))
    tail = RESAMPLES * (100 - INTERVAL) // 200
    return found[tail], found[RESAMPLES - 1 - tail]


def check(claim, raw, player_seasons, player_matches):
    """The Verdict for one Claim's Extraction. A Fault (bad data, a code error, a Claim type not built yet) raises; it is never a Verdict."""
    def cant(reason, detail=None, subject=None, polarity=None, warning=None):
        return ClaimVerdict(claim, raw, subject, polarity, (ReadingVerdict(None, CANT, reason, detail),), warning)

    try:
        extraction = read_extraction(raw)
    except Unreadable as error:
        return cant("could not read the claim", str(error))
    polarity = extraction.polarity
    warning = PRESENT_WARNING if extraction.tense == "present" else None
    if any(subject.kind in ("match", "manager") for subject in extraction.subjects):
        return cant("subject type not covered", polarity=polarity, warning=warning)
    if extraction.form == "comparison":
        raise NotImplementedError("comparison Claims: the verdict rule is still to design (Q5)")
    (subject,) = extraction.subjects
    if subject.kind != "player":
        raise NotImplementedError(f"{subject.kind} Claims come in #46")
    people = resolve(subject.name, player_seasons)
    if not people:
        return cant("subject not in data", subject.name, polarity=polarity, warning=warning)
    if len(people) > 1:
        listed = sorted(f"{found.name} ({found.clubs[-1]}, {season_label(found.season)})" for found in people.values())
        return cant("subject is ambiguous", ", ".join(listed), polarity=polarity, warning=warning)
    ((person, latest),) = people.items()

    def subject_cant(reason, detail=None):
        return cant(reason, detail, latest.name, polarity, warning)

    problems = []
    for find in (lambda: player_readings(extraction.claim_words), lambda: reference_rule(extraction.reference_named)):
        try:
            problems.append(("", find()))
        except NotInCatalogue as error:
            problems.append(error.args)
    reasons = [found for found in problems if found[0]]
    if reasons:
        return subject_cant(*min(reasons, key=lambda found: REASONS.index(found[0])))
    readings, (league, named_line) = problems[0][1], problems[1][1]

    if extraction.seasons_named:
        first, last = season_span(extraction.seasons_named)
        window = tuple(season for season in SEASONS if first <= season <= last)
        if not window:
            return subject_cant("season not in data", extraction.seasons_named)
    else:
        window = PRESENT if extraction.tense == "present" else SEASONS
    if league == SUBJECT_LEAGUE:  # "in the league": the Subject's league in the Window's latest season it played
        own = [found for found in player_seasons if found.player_id == person and found.season in window]
        league = max(own, key=lambda found: (found.season, found.minutes)).league if own else None

    in_scope = {found.key: found for found in player_seasons if found.season in window and (league is None or found.league == league)}
    qualifying = {key for key, found in in_scope.items() if found.minutes >= QUALIFY_MINUTES and not found.held_for_review}
    own_seasons = [found for found in in_scope.values() if found.player_id == person]
    if not any(found.minutes >= QUALIFY_MINUTES for found in own_seasons):
        return subject_cant("too few minutes")
    if not any(found.key in qualifying for found in own_seasons):
        return subject_cant("held for review")

    line_minutes, line_latest, shots_of, keys_of = defaultdict(Counter), defaultdict(dict), defaultdict(list), defaultdict(set)
    matches_of, club_matches = defaultdict(list), defaultdict(set)
    for found in player_matches:
        club_matches[(found.league, found.season, found.club)].add(found.match)
        key = (found.league, found.season, found.player_id)
        if key not in qualifying:
            continue
        keys_of[found.player_id].add(key)
        matches_of[key].append(found)
        shots_of[key].extend(shot for shot in found.shots if counts_for_metrics(shot))
        if found.line is not None:  # substitute appearances count for minutes, not for a Line
            line_minutes[found.player_id][found.line] += found.minutes
            line_latest[found.player_id][found.line] = max(found.season, line_latest[found.player_id].get(found.line, found.season))
    lines = {player: max(minutes, key=lambda line: (minutes[line], line_latest[player][line])) for player, minutes in line_minutes.items() if minutes}  # D2
    line = named_line or lines.get(person)
    if line == "Goalkeeper":
        return subject_cant("metric not in data", "every catalogue Claim on a goalkeeper (Q7)")
    if line is None:
        return subject_cant("peer group too small", "no start in the Window, so no Line")

    season_matches = Counter()  # matches per club in each league-season: the Availability denominator
    for (found_league, found_season, _), played in club_matches.items():
        season_matches[(found_league, found_season)] = max(season_matches[(found_league, found_season)], len(played))
    data = dict(keys_of=keys_of, shots_of=shots_of, matches_of=matches_of, season_matches=season_matches)
    verdicts = tuple(reading_verdict(reading, latest, person, window, league, line, lines, in_scope, qualifying, data, polarity) for reading in readings)
    return ClaimVerdict(claim, raw, latest.name, polarity, verdicts, warning)


def reading_verdict(reading, latest, person, window, league, line, lines, in_scope, qualifying, data, polarity):
    if reading.claim_type in PER_SEASON:
        return season_verdict(reading, latest, person, window, league, line, lines, in_scope, qualifying, data, polarity)
    if reading.claim_type not in POOLED:
        raise NotImplementedError(f"{reading.claim_type}: season totals come in #45")
    keys_of, shots_of = data["keys_of"], data["shots_of"]
    metric = POOLED[reading.claim_type]

    def sample(player):
        return [shot for key in sorted(keys_of[player], key=lambda key: key[1]) for shot in shots_of[key] if metric.counts(shot)]

    level = reading.level_word.capitalize() if reading.level_word else "No level word"
    lowest = ", counted from the lowest value" if reading.direction == "less" else ""
    threshold = f"{level} = {reading.threshold.words()} of the peer group on {metric.main_metric}{lowest}."
    used, skipped = [], []
    for season in window:
        own = [found for found in in_scope.values() if found.player_id == person and found.season == season]
        if not any(found.minutes >= QUALIFY_MINUTES for found in own):
            skipped.append(f"{season_label(season)} too few minutes")
        elif not any(found.key in qualifying for found in own):
            skipped.append(f"{season_label(season)} held for review")
        elif not any(metric.counts(shot) for found in own for shot in shots_of[found.key]):
            skipped.append(f"{season_label(season)} no shots")
        else:
            used.append(season)
    coverage = f"Based on {len(used)} of {len(window)} season{'s' if len(window) > 1 else ''}" + (f": {', '.join(skipped)}." if skipped else ".")
    common = dict(claim_type=reading.claim_type, threshold=threshold, seasons=window_label(window), coverage=coverage, thin=len(used) < len(window) / 2)

    shots = sample(person)
    if len(shots) < SHOT_MINIMUM:
        return ReadingVerdict(verdict=CANT, reason="too few shots", detail=f"{len(shots)} shots, the minimum is {SHOT_MINIMUM}", **common)
    peer_values = []
    for player, peer_line in lines.items():
        if player != person and peer_line == line:
            found = sample(player)
            if len(found) >= SHOT_MINIMUM:
                peer_values.append(metric.value(found))
    scope = LEAGUE_NAMES[league] if league else "the top 5 leagues"
    reference = (f"vs {LINE_WORDS[line]} in {scope}, {window_label(window)}, {QUALIFY_MINUTES}+ minutes per season, "
                 f"{SHOT_MINIMUM}+ non-penalty shots{metric.shots_words}: {len(peer_values)} players")
    common.update(reference_group=reference, reference_size=len(peer_values))
    if len(peer_values) < PLAYER_REFERENCE_MINIMUM:
        return ReadingVerdict(verdict=CANT, reason="peer group too small", detail=f"{len(peer_values)} peers, the minimum is {PLAYER_REFERENCE_MINIMUM}", **common)

    value = metric.value(shots)
    point = percentile_of(value, peer_values, reading.direction)
    low, high = bootstrap(shots, metric, peer_values, reading.direction)
    outcome = reading.threshold.outcome(low, high, len(peer_values) + 1)
    verdict = {"meets": SUPPORTED, "misses": NOT_SUPPORTED, "borderline": MIXED}[outcome]
    if polarity == "negated":
        verdict = FLIP.get(verdict, verdict)
    query = ClaimQuery(latest.name, person, reading.claim_type, metric.main_metric, reading.direction, reading.threshold.words(),
                       (window[0], window[-1]), {"league": league, "line": line})
    seasons_alone = tuple(
        f"{season_label(season)}: {metric.unit.format(metric.value(found))} on {len(found)} shots"
        for season in used for found in [[shot for shot in shots if shot.season == season]] if found
    )
    return ReadingVerdict(verdict=verdict, reason="the range crosses the line" if outcome == "borderline" else None, claim_query=query,
                          test=Test(value, metric.unit.format(value), len(shots), point, (low, high), outcome), seasons_alone=seasons_alone, **common)


def threshold_words(reading, main_metric):
    level = reading.level_word.capitalize() if reading.level_word else "No level word"
    lowest = ", counted from the lowest value" if reading.direction == "less" else ""
    return f"{level} = {reading.threshold.words()} of the peer group on {main_metric}{lowest}."


def match_bootstrap(matches, value, peer_values, direction):
    """The 80% interval of the percentile over RESAMPLES resamples of the Subject's PlayerMatches, against the fixed peers."""
    draw = random.Random(SEED)
    found = sorted(percentile_of(value(draw.choices(matches, k=len(matches))), peer_values, direction) for _ in range(RESAMPLES))
    tail = RESAMPLES * (100 - INTERVAL) // 200
    return found[tail], found[RESAMPLES - 1 - tail]


def combine(outcomes, unit):
    """The strict rule (Q9, ADR 0003): Supported if every test meets, Not supported if every test misses, else Mixed with one line why."""
    if all(outcome == "meets" for outcome in outcomes):
        return SUPPORTED, None
    if all(outcome == "misses" for outcome in outcomes):
        return NOT_SUPPORTED, None
    if "borderline" in outcomes:
        return MIXED, "the range crosses the line"
    meets = sum(outcome == "meets" for outcome in outcomes)
    return MIXED, f"{meets} of {len(outcomes)} {unit} meet the threshold"


def season_verdict(reading, latest, person, window, league, line, lines, in_scope, qualifying, data, polarity):
    """A per-season Claim type (#44): one Test per qualifying season and Main metric, combined by the strict rule."""
    keys_of, matches_of, season_matches = data["keys_of"], data["matches_of"], data["season_matches"]
    metrics = PER_SEASON[reading.claim_type]
    main_metric = " and ".join(metric.name for metric in metrics)
    threshold = threshold_words(reading, main_metric)
    used, skipped, tests, context, sizes = [], [], [], [], []
    for season in window:
        own = [found for found in in_scope.values() if found.player_id == person and found.season == season]
        if not any(found.minutes >= QUALIFY_MINUTES for found in own):
            skipped.append(f"{season_label(season)} not enough minutes")
            continue
        own_keys = [key for key in keys_of[person] if key[1] == season]
        if not own_keys:
            skipped.append(f"{season_label(season)} held for review")
            continue
        # One season, one test: a Subject qualifying in 2 leagues in a season is tested on the league with more minutes.
        key = max(own_keys, key=lambda key: sum(found.minutes for found in matches_of[key]))
        matches, count = matches_of[key], season_matches[(key[0], key[1])]
        peers = []  # one test per peer too: a peer in 2 leagues in the season counts once, in the league with more minutes
        for player, peer_line in lines.items():
            found = [peer_key for peer_key in keys_of[player] if peer_key[1] == season] if player != person and peer_line == line else []
            if found:
                peers.append(max(found, key=lambda peer_key: sum(match.minutes for match in matches_of[peer_key])))
        if len(peers) < PLAYER_REFERENCE_MINIMUM:
            skipped.append(f"{season_label(season)} peer group too small ({len(peers)} peers)")
            continue
        used.append(season)
        sizes.append(len(peers))
        for metric in metrics:
            peer_values = [metric.value(matches_of[peer_key], season_matches[(peer_key[0], peer_key[1])]) for peer_key in peers]
            value = metric.value(matches, count)
            point = percentile_of(value, peer_values, reading.direction)
            low, high = match_bootstrap(matches, lambda sample: metric.value(sample, count), peer_values, reading.direction)
            label = season_label(season) + (f", {metric.name}" if len(metrics) > 1 else "")
            tests.append(Test(value, metric.unit.format(value), len(np_shots(matches)), point, (low, high),
                              reading.threshold.outcome(low, high, len(peer_values) + 1), label, len(matches), len(peer_values)))
        if reading.claim_type in CONTEXT:
            name, value, unit = CONTEXT[reading.claim_type]
            context.append(f"{season_label(season)}: {unit.format(value(matches))}")
    coverage = f"Based on {len(used)} of {len(window)} season{'s' if len(window) > 1 else ''}" + (f": {', '.join(skipped)}." if skipped else ".")
    scope = LEAGUE_NAMES[league] if league else "the top 5 leagues"
    reference = (f"vs {LINE_WORDS[line]} in {scope}, each season's {QUALIFY_MINUTES}+ minute players"
                 + (f": {min(sizes)}-{max(sizes)} players per season" if sizes else ""))
    common = dict(claim_type=reading.claim_type, threshold=threshold, seasons=window_label(window), coverage=coverage,
                  thin=len(used) < len(window) / 2, reference_group=reference, reference_size=min(sizes) if sizes else 0)
    if not tests:
        if any("peer group too small" in found for found in skipped):
            return ReadingVerdict(verdict=CANT, reason="peer group too small", detail=f"the minimum is {PLAYER_REFERENCE_MINIMUM} peers per season", **common)
        return ReadingVerdict(verdict=CANT, reason="too few minutes", **common)
    verdict, why = combine([test.outcome for test in tests], "seasons" if len(metrics) == 1 else "tests")
    if polarity == "negated":
        verdict = FLIP.get(verdict, verdict)
    query = ClaimQuery(latest.name, person, reading.claim_type, main_metric, reading.direction, reading.threshold.words(),
                       (window[0], window[-1]), {"league": league, "line": line})
    return ReadingVerdict(verdict=verdict, reason=why, claim_query=query, tests=tuple(tests),
                          seasons_alone=tuple(f"{CONTEXT[reading.claim_type][0]}, {found}" for found in context) if context else (), **common)
