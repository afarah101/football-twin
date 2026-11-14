"""The Validation report seam (Q26, #10): the Pool in, a self-match PASS, WEAK or FAIL for each method out.

Local parts only. The outside review and the blind spot-check (Q12, Q22) need a non-Claude model, so they do not run here.
- Self-match (plan test 1, Q10): for each Pool PlayerSeason whose player has a Pool season the next year, the twins are ranked
  with every other season of that player removed except the next one. A hit is that next season in the top 10 players.
  The random baseline is the same chance for a random pick of 10 players.
- Split (Q10 split): the method is chosen on transitions inside 2017/18-2021/22 and judged on the 2022/23 and 2023/24 transitions.
- Bands (Q10, Q19): on the judged rate's point estimate, 40%+ PASS, 30% to under 40% WEAK, under 30% FAIL. A 95% Wilson interval
  is shown beside it.
- Stability (Q21): report-only. Mean Spearman correlation of each sampled row's distances with one metric dropped.
- The correlation matrix and the PCA loadings with explained variance are printed. The Basketball method (Q20) is reported beside.
Usage: python3 -m twin.application.validation  (the stand-in run; the report goes to build/private/, never to the site)
"""
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from twin.domain.profiles import METRICS
from twin.domain.twins import CANDIDATE_METHODS, COMPARISON_METHODS, DISTANCE_DECIMALS, TOP, method_vectors

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DECISIONS = ROOT / "data" / "standin" / "review_decisions.csv"
REPORT = ROOT / "build" / "private" / "validation_report.md"
CHOOSE_LAST = 2021  # choose on transitions whose both seasons are in 2017/18-2021/22 (start years 2017-2021)
JUDGE_TARGETS = (2022, 2023)  # judge on the transitions into 2022/23 and 2023/24
PASS_RATE, WEAK_RATE = 0.40, 0.30
Z_95 = 1.959964
STABILITY_ROWS, STABILITY_SEED = 200, 43
SPOT_LISTS, SPOT_SEED, SPOT_SHOWN = 10, 43, 5


class ValidationStopped(SystemExit):
    pass


def band(rate):
    """Q10 and Q19: the band of a self-match rate's point estimate."""
    if rate >= PASS_RATE:
        return "PASS"
    if rate >= WEAK_RATE:
        return "WEAK"
    return "FAIL"


def wilson(hits, tests, z=Z_95):
    """The 95% Wilson interval of hits / tests, (0, 0) for no tests."""
    if not tests:
        return 0.0, 0.0
    rate = hits / tests
    middle = (rate + z * z / (2 * tests)) / (1 + z * z / tests)
    half = z * math.sqrt(rate * (1 - rate) / tests + z * z / (4 * tests * tests)) / (1 + z * z / tests)
    return max(0.0, middle - half), min(1.0, middle + half)


def check_cross_season_ids(path=REVIEW_DECISIONS):
    """#10: an approved cross_season_ids row would make one person read as two players, so the report stops and Ahmed decides."""
    count = sum(line.startswith("cross_season_ids,") for line in path.read_text(encoding="utf8").splitlines()) if path.exists() else 0
    if count:
        raise ValidationStopped(f"validation: {count} approved cross_season_ids row(s) in {path.name}, so two ids may be one player. Ahmed decides.")
    return count


@dataclass(frozen=True)
class SelfMatch:
    method: str
    hits: int
    tests: int
    baseline: float  # the mean chance of a hit for 10 random players

    @property
    def rate(self):
        return self.hits / self.tests if self.tests else 0.0


def pool_members(peer_groups):
    return sorted((member for group in peer_groups.values() for member in group), key=lambda member: member.player_season.key)


def self_match(members, vectors, method, test_rows):
    """Hits over `test_rows`, each a (row, target rows) pair: the target rows are that player's seasons the next year."""
    ids = np.array([member.player_season.player_id for member in members])
    positions = np.arange(len(members))
    hits, chances = 0, []
    for row, targets in test_rows:
        distances = row_distances(vectors, row, method)
        keep = (ids != ids[row]) | np.isin(positions, targets)  # every other season of the player is removed, except the next one
        order = positions[keep][np.lexsort((positions[keep], distances[keep]))]
        _, first = np.unique(ids[order], return_index=True)
        top = order[np.sort(first)][:TOP]
        hits += bool(np.isin(top, targets).any())
        players = len(np.unique(ids[keep]))
        chances.append(min(TOP, players) / players if players else 0.0)
    return SelfMatch(method, hits, len(test_rows), float(np.mean(chances)) if chances else 0.0)


def row_distances(vectors, row, method):
    """One row of distance_matrix (rounded as in twin_lists), without building the whole matrix."""
    if method in ("euclidean", "basketball"):
        return np.round(np.sqrt(((vectors - vectors[row]) ** 2).sum(axis=1)), DISTANCE_DECIMALS)
    return np.round(pair_distances(vectors, row, method), DISTANCE_DECIMALS)


def pair_distances(vectors, row, method):
    if method == "pearson":
        vectors = vectors - vectors.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(vectors, axis=1)
    unit = np.divide(vectors, norms[:, None], out=np.zeros_like(vectors), where=norms[:, None] > 0)
    return 1 - unit @ unit[row]


def transitions(members):
    """[(row, target rows, target season)]: every Pool PlayerSeason whose player has a Pool season the next year."""
    rows_of = {}
    for row, member in enumerate(members):
        rows_of.setdefault((member.player_season.player_id, member.player_season.season), []).append(row)
    return [(row, rows_of[(member.player_season.player_id, member.player_season.season + 1)], member.player_season.season + 1)
            for row, member in enumerate(members) if (member.player_season.player_id, member.player_season.season + 1) in rows_of]


def split(found):
    choose = [(row, targets) for row, targets, target in found if target <= CHOOSE_LAST]
    judge = [(row, targets) for row, targets, target in found if target in JUDGE_TARGETS]
    return choose, judge


def spearman(a, b):
    ranks_a, ranks_b = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    if np.std(ranks_a) == 0 or np.std(ranks_b) == 0:
        return 1.0
    return float(np.corrcoef(ranks_a, ranks_b)[0, 1])


def stability(z):
    """Q21, report-only: {metric: mean Spearman correlation of a sampled row's distances, all metrics v that metric dropped}."""
    rows = sorted(random.Random(STABILITY_SEED).sample(range(len(z)), min(STABILITY_ROWS, len(z))))
    full = [np.sqrt(((z - z[row]) ** 2).sum(axis=1)) for row in rows]
    found = {}
    for index, metric in enumerate(METRICS):
        kept = np.delete(z, index, axis=1)
        found[metric] = float(np.mean([spearman(full[at], np.sqrt(((kept - kept[row]) ** 2).sum(axis=1))) for at, row in enumerate(rows)]))
    return found


def pca(z):
    """(explained variance shares, loadings with one row per component) of the Pool's z-scores, signs fixed as in the map (#12)."""
    centred = z - z.mean(axis=0)
    _, values, components = np.linalg.svd(centred, full_matrices=False)
    components = components * np.sign(components[np.arange(len(components)), np.abs(components).argmax(axis=1)])[:, None]
    variance = values ** 2
    return variance / variance.sum(), components


def spot_lists(members, vectors, method):
    """SPOT_LISTS fixed-seed players' top SPOT_SHOWN twins (other players only), for the Basketball comparison."""
    ids = np.array([member.player_season.player_id for member in members])
    positions = np.arange(len(members))
    chosen = sorted(random.Random(SPOT_SEED).sample(range(len(members)), min(SPOT_LISTS, len(members))))
    found = {}
    for row in chosen:
        distances = row_distances(vectors, row, method)
        keep = ids != ids[row]
        order = positions[keep][np.lexsort((positions[keep], distances[keep]))]
        _, first = np.unique(ids[order], return_index=True)
        found[row] = [members[other].player_season for other in order[np.sort(first)][:SPOT_SHOWN]]
    return chosen, found


def season_words(found):
    return f"{found.name} ({found.league} {found.season}/{(found.season + 1) % 100:02d})"


def validation_report(peer_groups):
    """The report text and {method: (choose SelfMatch, judge SelfMatch)}. Stops if a cross_season_ids row is approved."""
    check_cross_season_ids()
    members = pool_members(peer_groups)
    vectors = method_vectors(members)
    choose, judge = split(transitions(members))
    results = {method: (self_match(members, vectors[method], method, choose), self_match(members, vectors[method], method, judge))
               for method in CANDIDATE_METHODS + COMPARISON_METHODS}
    winner = max(CANDIDATE_METHODS, key=lambda method: (results[method][0].rate, -CANDIDATE_METHODS.index(method)))
    lines = ["# Validation report (stand-in, local parts)", "",
             f"Pool: {len(members)} PlayerSeasons. Choose set: {len(choose)} transitions inside 2017/18-2021/22. "
             f"Judge set: {len(judge)} transitions into 2022/23 and 2023/24.", "",
             "## Self-match (top 10, own next season)", "",
             "| Method | Choose rate | Judge rate | 95% interval | Random baseline | Band |", "|---|---|---|---|---|---|"]
    for method, (chose, judged) in results.items():
        low, high = wilson(judged.hits, judged.tests)
        mark = " (winner)" if method == winner else " (comparison only)" if method in COMPARISON_METHODS else ""
        lines.append(f"| {method}{mark} | {chose.rate:.1%} ({chose.hits}/{chose.tests}) | {judged.rate:.1%} ({judged.hits}/{judged.tests}) | "
                     f"{low:.1%}-{high:.1%} | {judged.baseline:.1%} | {band(judged.rate) if method not in COMPARISON_METHODS else '-'} |")
    lines += ["", f"Winning method (highest choose rate): **{winner}**, judged **{band(results[winner][1].rate)}**.", ""]
    z = vectors["euclidean"]
    lines += ["## Stability (report-only, Q21)", "", f"Mean Spearman correlation of {min(STABILITY_ROWS, len(z))} sampled rows' distances with one metric dropped (seed {STABILITY_SEED}).", ""]
    found = stability(z)
    flag = min(found, key=found.get)
    lines += [f"- {metric}: {value:.3f}" + (" (changes the rankings most: flag for the outside review)" if metric == flag else "") for metric, value in found.items()]
    matrix = np.corrcoef(z, rowvar=False)
    lines += ["", "## Correlation matrix (z-scores)", "", "| | " + " | ".join(METRICS) + " |", "|" + "---|" * (len(METRICS) + 1)]
    lines += [f"| {metric} | " + " | ".join(f"{value:.2f}" for value in row) + " |" for metric, row in zip(METRICS, matrix)]
    shares, loadings = pca(z)
    lines += ["", "## PCA (z-scores)", "", "| Component | Explained variance | " + " | ".join(METRICS) + " |", "|" + "---|" * (len(METRICS) + 2)]
    lines += [f"| {index + 1} | {share:.1%} | " + " | ".join(f"{value:+.2f}" for value in row) + " |" for index, (share, row) in enumerate(zip(shares, loadings))]
    chosen, ours = spot_lists(members, vectors[winner], winner)
    _, theirs = spot_lists(members, vectors["basketball"], "basketball")
    lines += ["", f"## Basketball method beside {winner} (Q20)", "", f"{len(chosen)} fixed-seed players (seed {SPOT_SEED}), top {SPOT_SHOWN} twins.", ""]
    for row in chosen:
        lines += [f"- {season_words(members[row].player_season)}", f"  - {winner}: " + "; ".join(map(season_words, ours[row])),
                  "  - basketball: " + "; ".join(map(season_words, theirs[row]))]
    lines += ["", "## Not run here", "", "- Outside review by a non-Claude model (Q22) and the blind spot-check of 10 lists (Q12). They need a free-tier model key.",
              "- So this report is not a launch decision on its own (Q12)."]
    return "\n".join(lines) + "\n", results


def write_report(peer_groups, path=REPORT):
    text, results = validation_report(peer_groups)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    return path, results


if __name__ == "__main__":
    from twin.domain.profiles import peer_group_profiles
    from twin.infrastructure.standin.loader import StandinLoader

    loaded = StandinLoader().load()
    path, _ = write_report(peer_group_profiles(loaded.player_seasons, loaded.shots))
    print(path.read_text(encoding="utf8"))
