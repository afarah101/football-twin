"""#30 Part A: measure careers on the full stand-in data before any career model code. Read-only.

It loads data/standin/ through the stand-in loader, computes the six measurements of #30 Part A, prints them, and writes
them to docs/reports/T30_measurements.md. It writes nothing else.
Usage, from the repo root:
  uv run --no-project --python 3.12 --with-requirements requirements.txt python scripts/measure_careers.py
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twin.domain.pool import in_pool
from twin.domain.profiles import METRICS, counts_for_metrics, peer_group_profiles, z_scores
from twin.infrastructure.standin.loader import load_standin

COMMAND = "uv run --no-project --python 3.12 --with-requirements requirements.txt python scripts/measure_careers.py"
REPORT = ROOT / "docs" / "reports" / "T30_measurements.md"
CAREER_MINUTES = 9000  # #30 decision 2
COMPARE_MINUTES = (6000, 7500, 9000, 10000)
ROLE_GROUPS = {"FW": "Forward", "LW": "Wide", "RW": "Wide", "AM": "Central AM"}  # #30 decision 7
CORRELATION_LIMIT = 0.8  # #30 decision 10
NAMED = ("Harry Kane", "Mohamed Salah")


def season_label(season):
    return f"{season}/{(season + 1) % 100:02d}"


def careers_of(pool):
    """{player_id: [Pool PlayerSeasons]}. player_id is the FBref id, one person across seasons."""
    careers = defaultdict(list)
    for found in pool:
        careers[found.player_id].append(found)
    return careers


def role_group(seasons):
    """shortcut: the role group with the most Pool minutes, ties listed as 'tie'; the owner decides the real rule in Part B."""
    minutes = Counter()
    for found in seasons:
        minutes[ROLE_GROUPS[found.display_position]] += found.minutes
    ranked = minutes.most_common()
    return "tie" if len(ranked) > 1 and ranked[0][1] == ranked[1][1] else ranked[0][0]


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]


def correlation_section(title, columns):
    """Pearson r across Pool seasons between every two metric columns."""
    matrix = np.corrcoef(np.array(columns))
    short = [metric.replace("_per_90", "/90").replace("_share", "%") for metric in METRICS]
    lines = [f"**{title}**", ""] + table(["metric"] + short, [[short[i]] + [f"{matrix[i, j]:.2f}" for j in range(len(METRICS))] for i in range(len(METRICS))])
    pairs = [(METRICS[i], METRICS[j], matrix[i, j]) for i in range(len(METRICS)) for j in range(i + 1, len(METRICS)) if abs(matrix[i, j]) > CORRELATION_LIMIT]
    lines += ["", f"Pairs with |r| above {CORRELATION_LIMIT}: " + ("; ".join(f"{a} and {b}: {r:.3f}" for a, b, r in pairs) if pairs else "none")]
    trio = ("xa_per_90", "key_passes_per_90", "xg_buildup_per_90")
    lines.append("Decision 10 trio: " + "; ".join(f"{a} and {b}: {matrix[METRICS.index(a), METRICS.index(b)]:.3f}" for k, a in enumerate(trio) for b in trio[k + 1:]))
    return lines, pairs


def main():
    run = load_standin()
    loaded = run.loaded
    pool = [found for found in loaded.player_seasons if in_pool(found)]
    careers = careers_of(pool)
    career_minutes = {player_id: sum(found.minutes for found in seasons) for player_id, seasons in careers.items()}
    groups = {player_id: role_group(seasons) for player_id, seasons in careers.items()}
    out = [
        "# #30 Part A: career measurements",
        "",
        f"Source: full stand-in data (`data/standin/`), loaded by `load_standin()` with merges on. Pool: {len(pool)} PlayerSeasons, "
        f"seasons {season_label(min(f.season for f in pool))} to {season_label(max(f.season for f in pool))}, {len(careers)} people (FBref ids).",
        "",
        f"Every number below comes from one command, run from the repo root: `{COMMAND}`. Each section names the function that computes it.",
        "",
        "A career here is all Pool PlayerSeasons of one FBref id. Career minutes are the sum of their minutes, so only seasons of 900+ minutes count, "
        "and a two-stint season counts each stint that is in the Pool.",
        "",
    ]

    # 1. Career counts by threshold.
    out += ["## 1. Careers by total Pool minutes", "", f"Computed in `main`, from `careers_of` and the sum of Pool minutes.", ""]
    out += table(["minutes at least", "careers"], [[f"{limit:,}", sum(1 for total in career_minutes.values() if total >= limit)] for limit in COMPARE_MINUTES])
    passing = {player_id for player_id, total in career_minutes.items() if total >= CAREER_MINUTES}
    out += ["", f"At {CAREER_MINUTES:,}: {len(passing)} careers. #30 target range: 500 to 1,000.", ""]

    # 2. Per role group.
    out += ["## 2. Careers by role group", "",
            "Computed in `role_group`. Role groups from `display_position` (#30 decision 7): FW = Forward, LW/RW = Wide, AM = Central AM. "
            "A career's group here is the group with the most Pool minutes over its seasons. That rule is a measuring shortcut, not a decision.", ""]
    names = ("Forward", "Wide", "Central AM", "tie")
    out += table(["minutes at least"] + list(names), [[f"{limit:,}"] + [sum(1 for player_id, total in career_minutes.items() if total >= limit and groups[player_id] == name) for name in names] for limit in COMPARE_MINUTES])
    mixed = [player_id for player_id in passing if len({ROLE_GROUPS[found.display_position] for found in careers[player_id]}) > 1]
    out += ["", f"Of the {len(passing)} careers at {CAREER_MINUTES:,}, {len(mixed)} hold seasons in more than one role group.", ""]
    season_groups = Counter(ROLE_GROUPS[found.display_position] for found in pool)
    out += ["Pool seasons by role group: " + ", ".join(f"{name} {season_groups[name]}" for name in names[:3]) + f" (display_position: {dict(sorted(Counter(f.display_position for f in pool).items()))}).", ""]

    # 3. Correlation of the 10 metrics.
    peer_groups = peer_group_profiles(loaded.player_seasons, loaded.shots)
    profiles = [profile for members in peer_groups.values() for profile in members]
    out += ["## 3. Correlation of the 10 metrics across Pool seasons", "",
            f"Computed in `correlation_section` with `numpy.corrcoef`, over the {len(profiles)} MetricProfiles from `peer_group_profiles`. "
            "The z-scores are what the distance uses. The shrunk values, before the z-score, are shown too.", ""]
    z_lines, z_pairs = correlation_section("z-scores (MetricProfile.values)", [[profile.values[i] for profile in profiles] for i in range(len(METRICS))])
    s_lines, s_pairs = correlation_section("Shrunk values before the z-score (MetricProfile.shrunk)", [[profile.shrunk[i] for profile in profiles] for i in range(len(METRICS))])
    out += z_lines + [""] + s_lines + [""]

    # 4. Finishing.
    shots_of = Counter((shot.league, shot.season, shot.player_id) for shot in loaded.shots if counts_for_metrics(shot))
    finishing_rows = []  # (profile, finishing per shot, non-penalty shots)
    no_shot = 0
    for profile in profiles:
        count = shots_of[profile.player_season.key]
        if not count:
            no_shot += 1
            continue
        finishing_rows.append((profile, profile.display_stats.npg_minus_npxg / count, count))
    values = np.array([value for _, value, _ in finishing_rows])
    out += ["## 4. Finishing = (npG - npxG) per shot", "",
            "Computed in `main`: `display_stats.npg_minus_npxg` divided by the PlayerSeason's non-penalty shots (`counts_for_metrics`, own goals out). "
            "Raw, with no shrinkage: #30 decision 5 asks for the same shrinkage as other small-sample values, and that rule is not built yet.", ""]
    out += table(["seasons", "no shot (left out)", "mean", "SD", "min", "10th pct", "median", "90th pct", "max"],
                 [[len(values), no_shot, f"{values.mean():.4f}", f"{values.std():.4f}", f"{values.min():.4f}", f"{np.percentile(values, 10):.4f}",
                   f"{np.median(values):.4f}", f"{np.percentile(values, 90):.4f}", f"{values.max():.4f}"]])
    bands = ((0, 30), (30, 60), (60, 100), (100, 10_000))
    out += ["", "Spread by non-penalty shots in the season (small samples spread wider, which is what shrinkage would pull in):", ""]
    out += table(["shots", "seasons", "mean", "SD"], [[f"{low}-{high - 1}" if high < 10_000 else f"{low}+", len(band), f"{band.mean():.4f}", f"{band.std():.4f}"]
                                                     for low, high in bands for band in [np.array([v for _, v, n in finishing_rows if low <= n < high])] if len(band)])
    # Finishing z-scored within each PeerGroup like the other metrics, against each metric's z-score.
    by_group = defaultdict(list)
    for row in finishing_rows:
        by_group[(row[0].player_season.league, row[0].player_season.season)].append(row)
    paired = [(row[0], z) for rows in by_group.values() for row, z in zip(rows, z_scores([value for _, value, _ in rows]))]
    finishing_z = np.array([z for _, z in paired])
    out += ["", "Correlation (Pearson r) of finishing with each metric, across the same seasons. Raw: raw finishing against the shrunk metric. "
            "z: finishing z-scored within its PeerGroup (clipped at ±3, as the others) against the metric's z-score.", ""]
    rows = []
    for i, metric in enumerate(METRICS):
        raw_r = np.corrcoef(values, [row[0].shrunk[i] for row in finishing_rows])[0, 1]
        z_r = np.corrcoef(finishing_z, [profile.values[i] for profile, _ in paired])[0, 1]
        rows.append([metric, f"{raw_r:.3f}", f"{z_r:.3f}"])
    out += table(["metric", "r raw", "r z"], rows) + [""]

    # 5. cross_season_ids.
    decisions = (ROOT / "data" / "standin" / "review_decisions.csv").read_text(encoding="utf8").splitlines()
    rows_cs = [line for line in decisions[1:] if line.startswith("cross_season_ids,")]
    cases = run.review.join.cross_season_cases
    out += ["## 5. People that cross_season_ids rows join into one career", "",
            "Computed in `main`: the `cross_season_ids` rows in `data/standin/review_decisions.csv`, and `cross_season_cases` from the join "
            "(each Understat id that reaches 2+ FBref ids across seasons, allowed by such a row).", "",
            f"`cross_season_ids` rows: {len(rows_cs)}. Cross-season cases in the join: {len(cases)} {cases}. "
            f"People joined into one career by them: {len(cases)}.", "",
            "The 3 id merges inside one league-season (Meité, Nduquidi, Strefezza, all 2024) are a different rule and already one FBref id.", ""]

    # 6. Named players.
    out += ["## 6. Harry Kane and Mohamed Salah", "", "Computed in `main` from `careers_of` and `role_group`, by exact name.", ""]
    named_rows = []
    for name in NAMED:
        ids = sorted({found.player_id for found in pool if found.name == name})
        for player_id in ids:
            seasons = sorted(careers[player_id], key=lambda found: (found.season, found.league))
            named_rows.append([name, player_id, f"{career_minutes[player_id]:,}", f"{season_label(seasons[0].season)}-{season_label(seasons[-1].season)}",
                               len(seasons), ", ".join(f"{f.league} {season_label(f.season)} {f.display_position} {f.minutes:,}" for f in seasons),
                               groups[player_id], "yes" if career_minutes[player_id] >= CAREER_MINUTES else "no"])
        if not ids:
            named_rows.append([name, "not in the Pool", "", "", "", "", "", ""])
    out += table(["name", "FBref id", "career minutes", "seasons covered", "Pool seasons", "each season (league, season, position, minutes)", "role group", f"{CAREER_MINUTES:,}+"], named_rows)
    out.append("")

    text = "\n".join(out)
    REPORT.write_text(text, encoding="utf8")
    print(text)
    print(f"\nwrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
