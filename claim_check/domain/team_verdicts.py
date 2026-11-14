"""Team and league Verdicts (#46): the spec's "Teams (Q4)" and "Leagues (Q4)" Claim types, word map v1-draft.

Teams: per-season types test each full season (D5) against that league-season's other full-season teams (Q7, 10 peers).
Pooled types (Chances conceded, Team finishing) are ratios of sums over the Window. Every test bootstraps TeamMatches (D4).
Leagues: a rank among the 5 leagues over the Window. The interval is the rank range over the resamples (D4).
An ambiguous word ("defensive") gives one Verdict per Reading, each shown with its meaning (Q4).
"""
import random
from collections import defaultdict
from dataclasses import dataclass

from claim_check.domain.word_map import LEAGUE_NAMES, REFERENCE_KEYS, SUBJECT_LEAGUE, NotInCatalogue, league_readings, reference_rule, team_readings, tokens
from twin.domain.twins import percentiles

TEAM_REFERENCE_MINIMUM = 10
LEAGUE_COUNT = 5
TOO_FEW_MATCHES = "too few matches"  # a team with no full season in the Window (D5)


def ratio(top, bottom):
    return top / bottom if bottom else 0.0


@dataclass(frozen=True)
class TeamMetric:
    name: str
    value: object  # TeamMatches -> float
    unit: str


def per_match(field):
    return lambda matches: ratio(sum(field(found) for found in matches), len(matches))


TEAM_PER_SEASON = {  # spec "Teams (Q4)", Pooled: no
    "Attack": TeamMetric("npxG for per match", per_match(lambda m: m.npxg_for), "{:.2f} npxG for per match"),
    "Defence": TeamMetric("npxG against per match", per_match(lambda m: m.npxg_against), "{:.2f} npxG against per match"),
    "Game openness": TeamMetric("total npxG per match", per_match(lambda m: m.npxg_for + m.npxg_against), "{:.2f} total npxG per match"),
    "Dominance": TeamMetric("npxG difference per match", per_match(lambda m: m.npxg_for - m.npxg_against), "{:+.2f} npxG difference per match"),
    "Set-piece threat": TeamMetric("set-piece xG for per match", per_match(lambda m: m.set_piece_xg_for), "{:.2f} set-piece xG for per match"),
    "Set-piece defence": TeamMetric("set-piece xG against per match", per_match(lambda m: m.set_piece_xg_against), "{:.2f} set-piece xG against per match"),
}
TEAM_POOLED = {  # spec "Teams (Q4)", Pooled: yes
    "Chances conceded": TeamMetric("npxG per shot against", lambda ms: ratio(sum(m.npxg_against for m in ms), sum(m.shots_against for m in ms)),
                                   "{:.3f} npxG per shot against"),
    "Team finishing": TeamMetric("(npG - npxG) per shot", lambda ms: ratio(sum(m.goals_for - m.npxg_for for m in ms), sum(m.shots_for for m in ms)),
                                 "{:+.3f} (npG - npxG) per shot"),
}
TEAM_CONTEXT = {  # shown, never the Verdict
    "Attack": (("goals per match", per_match(lambda m: m.goals_for)), ("shots per match", per_match(lambda m: m.shots_for))),
    "Defence": (("goals against per match", per_match(lambda m: m.goals_against)), ("shots against per match", per_match(lambda m: m.shots_against))),
    "Game openness": (("npxG for per match", per_match(lambda m: m.npxg_for)), ("npxG against per match", per_match(lambda m: m.npxg_against))),
    "Set-piece threat": (("share of xG from set pieces", lambda ms: ratio(sum(m.set_piece_xg_for for m in ms), sum(m.npxg_for for m in ms))),),
}
LEAGUE_METRICS = {  # spec "Leagues (Q4)"
    "Open or high-scoring": TeamMetric("npxG per match (both teams)", per_match(lambda m: m.npxg_for + m.npxg_against), "{:.2f} npxG per match"),
    "Set-piece league": TeamMetric("share of xG from set pieces", lambda ms: ratio(sum(m.set_piece_xg_for for m in ms), sum(m.npxg_for for m in ms)),
                                   "{:.1%} of xG from set pieces"),
    "Long-shot league": TeamMetric("outside-box share of shots", lambda ms: ratio(sum(m.outside_box_shots_for for m in ms), sum(m.shots_for for m in ms)),
                                   "{:.1%} of shots from outside the box"),
}
LEAGUE_CONTEXT = (("goals per match", per_match(lambda m: m.goals_for + m.goals_against)), ("shots per match", per_match(lambda m: m.shots_for + m.shots_against)))


def resolve_team(name, team_matches):
    query = tokens(name)
    return sorted({found.team for found in team_matches
                   for words in [tokens(found.team)] if any(words[at:at + len(query)] == query for at in range(len(words) - len(query) + 1))})


def resolve_league(name):
    for key in (" ".join(["in"] + tokens(name)), " ".join(["in", "the"] + tokens(name))):
        rule = REFERENCE_KEYS.get(key)
        if rule and rule[0] not in (None, SUBJECT_LEAGUE) and rule[1] is None:
            return rule[0]
    return None


def resampled(matches, value, score):
    """The 80% interval of score(value(resample)) over the resamples of the Subject's TeamMatches (D4)."""
    from claim_check.domain.verdicts import INTERVAL, RESAMPLES, SEED
    draw = random.Random(SEED)
    found = sorted(score(value(draw.choices(matches, k=len(matches)))) for _ in range(RESAMPLES))
    tail = RESAMPLES * (100 - INTERVAL) // 200
    return found[tail], found[RESAMPLES - 1 - tail]


def percentile_of(value, peer_values, direction):
    point = float(percentiles(peer_values + [value])[-1])
    return point if direction == "more" else 100 - point


def check_team(claim, raw, extraction, subject, team_matches, polarity, warning, window_of):
    from claim_check.domain import verdicts as v

    def cant(reason, detail=None, name=None):
        return v.ClaimVerdict(claim, raw, name, polarity, (v.ReadingVerdict(None, v.CANT, reason, detail),), warning)

    teams = resolve_team(subject.name, team_matches)
    if not teams:
        return cant("subject not in data", subject.name)
    if len(teams) > 1:
        return cant("subject is ambiguous", ", ".join(teams))
    (team,) = teams
    problems = []
    for find in (lambda: team_readings(extraction.claim_words), lambda: reference_rule(extraction.reference_named)):
        try:
            problems.append(("", find()))
        except NotInCatalogue as error:
            problems.append(error.args)
    if not problems[1][0] and problems[1][1][1] is not None:  # a Line names a player's position, never a team's
        problems[1] = ("peer group not in catalogue", extraction.reference_named)
    reasons = [found for found in problems if found[0]]
    if reasons:
        return cant(*min(reasons, key=lambda found: v.REASONS.index(found[0])), name=team)
    readings, (league, _) = problems[0][1], problems[1][1]
    window = window_of(extraction)
    if isinstance(window, str):
        return cant("season not in data", window, team)

    played = defaultdict(list)  # (league, season, team) -> TeamMatches
    for found in team_matches:
        if found.season in window:
            played[(found.league, found.season, found.team)].append(found)
    own = sorted(key for key in played if key[2] == team)
    if league in (None, SUBJECT_LEAGUE):  # a team's Reference group is its own league (Q7): the league of its latest season
        league = max(own, key=lambda key: (key[1], len(played[key])))[0] if own else None
    own = [key for key in own if key[0] == league]
    if not own:
        return cant("subject not in data", f"{team} in {LEAGUE_NAMES.get(league, league)}", team)
    full = defaultdict(int)
    for key, found in played.items():
        full[key[:2]] = max(full[key[:2]], len(found))
    is_full = {key for key, found in played.items() if len(found) == full[key[:2]]}  # D5: every league match of that season in the data
    if not any(key in is_full for key in own):
        return cant(TOO_FEW_MATCHES, f"no full season in {v.window_label(window)}", team)

    verdicts = []
    for reading in readings:
        if reading.claim_type in TEAM_POOLED:
            verdicts.append(pooled_team(reading, team, league, window, played, is_full, polarity))
        else:
            verdicts.append(season_team(reading, team, league, window, played, is_full, polarity))
    return v.ClaimVerdict(claim, raw, team, polarity, tuple(verdicts), warning)


def team_threshold(reading, main_metric):
    level = reading.level_word.capitalize() if reading.level_word else "No level word"
    lowest = ", counted from the lowest value" if reading.direction == "less" else ""
    return f"{level} = {reading.threshold.words()} of the league's teams on {main_metric}{lowest}."


def season_team(reading, team, league, window, played, is_full, polarity):
    from claim_check.domain import verdicts as v
    metric = TEAM_PER_SEASON[reading.claim_type]
    used, skipped, tests, context, sizes = [], [], [], [], []
    for season in window:
        key = (league, season, team)
        if key not in played:
            skipped.append(f"{v.season_label(season)} not in {LEAGUE_NAMES[league]}")
            continue
        matches = played[key]
        if key not in is_full:
            skipped.append(f"{v.season_label(season)} not a full season ({len(matches)} matches)")
            continue
        peers = [other for other in is_full if other[:2] == (league, season) and other != key]
        if len(peers) < TEAM_REFERENCE_MINIMUM:
            skipped.append(f"{v.season_label(season)} peer group too small ({len(peers)} teams)")
            continue
        used.append(season)
        sizes.append(len(peers))
        peer_values = [metric.value(played[other]) for other in peers]
        value = metric.value(matches)
        point = percentile_of(value, peer_values, reading.direction)
        low, high = resampled(matches, metric.value, lambda found: percentile_of(found, peer_values, reading.direction))
        tests.append(v.Test(value, metric.unit.format(value), sum(m.shots_for for m in matches), point, (low, high),
                            reading.threshold.outcome(low, high, len(peers) + 1), v.season_label(season), len(matches), len(peers)))
        for name, measure in TEAM_CONTEXT.get(reading.claim_type, ()):
            context.append(f"{v.season_label(season)}: {name} {measure(matches):.2f}" if "share" not in name else f"{v.season_label(season)}: {name} {measure(matches):.0%}")
    coverage = f"Based on {len(used)} of {len(window)} season{'s' if len(window) > 1 else ''}" + (f": {', '.join(skipped)}." if skipped else ".")
    reference = f"vs the other full-season teams in {LEAGUE_NAMES[league]}, each season" + (f": {min(sizes)}-{max(sizes)} teams per season" if sizes else "")
    common = dict(claim_type=reading.claim_type, threshold=team_threshold(reading, metric.name), seasons=v.window_label(window), coverage=coverage,
                  thin=len(used) < len(window) / 2, reference_group=reference, reference_size=min(sizes) if sizes else 0, meaning=reading.meaning)
    if not tests:
        if any("peer group too small" in found for found in skipped):
            return v.ReadingVerdict(verdict=v.CANT, reason="peer group too small", detail=f"the minimum is {TEAM_REFERENCE_MINIMUM} teams per season", **common)
        return v.ReadingVerdict(verdict=v.CANT, reason=TOO_FEW_MATCHES, **common)
    verdict, why = v.combine([test.outcome for test in tests], "seasons")
    if polarity == "negated":
        verdict = v.FLIP.get(verdict, verdict)
    query = v.ClaimQuery(team, team, reading.claim_type, metric.name, reading.direction, reading.threshold.words(),
                         (window[0], window[-1]), {"league": league, "line": None})
    return v.ReadingVerdict(verdict=verdict, reason=why, claim_query=query, tests=tuple(tests), seasons_alone=tuple(context), **common)


def pooled_team(reading, team, league, window, played, is_full, polarity):
    from claim_check.domain import verdicts as v
    metric = TEAM_POOLED[reading.claim_type]
    in_league = defaultdict(list)  # Q7: teams with 1+ full season in the Window, counted only for their seasons in that league
    for key, found in sorted(played.items(), key=lambda item: item[0][1]):
        if key[0] == league:
            in_league[key[2]].extend(found)
    qualifying = {key[2] for key in is_full if key[0] == league}
    seasons = sorted(key[1] for key in played if key[0] == league and key[2] == team)
    peers = sorted(qualifying - {team})
    peer_values = [metric.value(in_league[other]) for other in peers]
    coverage = f"Based on {len(seasons)} of {len(window)} season{'s' if len(window) > 1 else ''}."
    reference = f"vs teams in {LEAGUE_NAMES[league]}, {v.window_label(window)}, 1+ full season: {len(peers)} teams"
    common = dict(claim_type=reading.claim_type, threshold=team_threshold(reading, metric.name), seasons=v.window_label(window), coverage=coverage,
                  thin=len(seasons) < len(window) / 2, reference_group=reference, reference_size=len(peers), meaning=reading.meaning)
    if len(peers) < TEAM_REFERENCE_MINIMUM:
        return v.ReadingVerdict(verdict=v.CANT, reason="peer group too small", detail=f"{len(peers)} teams, the minimum is {TEAM_REFERENCE_MINIMUM}", **common)
    matches = in_league[team]
    value = metric.value(matches)
    point = percentile_of(value, peer_values, reading.direction)
    low, high = resampled(matches, metric.value, lambda found: percentile_of(found, peer_values, reading.direction))
    outcome = reading.threshold.outcome(low, high, len(peers) + 1)
    verdict = {"meets": v.SUPPORTED, "misses": v.NOT_SUPPORTED, "borderline": v.MIXED}[outcome]
    if polarity == "negated":
        verdict = v.FLIP.get(verdict, verdict)
    query = v.ClaimQuery(team, team, reading.claim_type, metric.name, reading.direction, reading.threshold.words(),
                         (window[0], window[-1]), {"league": league, "line": None})
    shots = sum(m.shots_against if reading.claim_type == "Chances conceded" else m.shots_for for m in matches)
    return v.ReadingVerdict(verdict=verdict, reason="the range crosses the line" if outcome == "borderline" else None, claim_query=query,
                            test=v.Test(value, metric.unit.format(value), shots, point, (low, high), outcome, matches=len(matches)), **common)


def rank_of(value, others, direction):
    """1 + the leagues strictly ahead in the Claim's direction."""
    return 1 + sum((other > value) if direction == "more" else (other < value) for other in others)


def check_league(claim, raw, extraction, subject, team_matches, polarity, warning, window_of):
    from claim_check.domain import verdicts as v

    def cant(reason, detail=None, name=None):
        return v.ClaimVerdict(claim, raw, name, polarity, (v.ReadingVerdict(None, v.CANT, reason, detail),), warning)

    league = resolve_league(subject.name)
    if league is None:
        return cant("subject not in data", subject.name)
    name = LEAGUE_NAMES[league]
    problems = [("", None)]
    try:
        problems[0] = ("", league_readings(extraction.claim_words))
    except NotInCatalogue as error:
        problems[0] = error.args
    if extraction.reference_named is not None:  # a league's Reference group is always the 5 leagues
        problems.append(("peer group not in catalogue", extraction.reference_named))
    reasons = [found for found in problems if found[0]]
    if reasons:
        return cant(*min(reasons, key=lambda found: v.REASONS.index(found[0])), name=name)
    readings = problems[0][1]
    window = window_of(extraction)
    if isinstance(window, str):
        return cant("season not in data", window, name)
    of_league = defaultdict(list)
    for found in team_matches:
        if found.season in window:
            of_league[found.league].append(found)
    if len(of_league) < LEAGUE_COUNT or league not in of_league:
        return cant("peer group too small", f"{len(of_league)} leagues, the minimum is {LEAGUE_COUNT}", name)
    seasons = sorted({found.season for found in of_league[league]})
    coverage = f"Based on {len(seasons)} of {len(window)} season{'s' if len(window) > 1 else ''}."
    context = tuple(f"{label} {measure(of_league[league]):.2f}" for label, measure in LEAGUE_CONTEXT)
    verdicts = []
    for reading in readings:
        metric = LEAGUE_METRICS[reading.claim_type]
        others = [metric.value(found) for other, found in of_league.items() if other != league]
        value = metric.value(of_league[league])
        rank = rank_of(value, others, reading.direction)
        best, worst = resampled(of_league[league], metric.value, lambda found: rank_of(found, others, reading.direction))
        outcome = "meets" if worst <= reading.top else "misses" if best > reading.top else "borderline"
        verdict = {"meets": v.SUPPORTED, "misses": v.NOT_SUPPORTED, "borderline": v.MIXED}[outcome]
        if polarity == "negated":
            verdict = v.FLIP.get(verdict, verdict)
        lowest = ", counted from the lowest value" if reading.direction == "less" else ""
        ranks = "rank 1" if reading.top == 1 else f"rank 1-{reading.top}"
        query = v.ClaimQuery(name, league, reading.claim_type, metric.name, reading.direction, f"{ranks} of {LEAGUE_COUNT}",
                             (window[0], window[-1]), {"league": None, "line": None})
        verdicts.append(v.ReadingVerdict(
            claim_type=reading.claim_type, verdict=verdict, reason="the range crosses the line" if outcome == "borderline" else None,
            threshold=f"{reading.level_word.capitalize()} = {ranks} of the {LEAGUE_COUNT} leagues on {metric.name}{lowest}.",
            claim_query=query, test=v.Test(value, metric.unit.format(value), sum(m.shots_for for m in of_league[league]), None, (best, worst), outcome,
                                           matches=len(of_league[league]), reference_size=LEAGUE_COUNT, rank=rank),
            reference_group=f"vs the {LEAGUE_COUNT} leagues, {v.window_label(window)}", reference_size=LEAGUE_COUNT,
            seasons=v.window_label(window), coverage=coverage, thin=len(seasons) < len(window) / 2,
            seasons_alone=context if reading.claim_type == "Open or high-scoring" else ()))
    return v.ClaimVerdict(claim, raw, name, polarity, tuple(verdicts), warning)
