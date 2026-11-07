# #30 Part A: career measurements

Source: full stand-in data (`data/standin/`), loaded by `load_standin()` with merges on. Pool: 3109 PlayerSeasons, seasons 2017/18 to 2023/24, 1262 people (FBref ids).

Every number below comes from one command, run from the repo root: `uv run --no-project --python 3.12 --with-requirements requirements.txt python scripts/measure_careers.py`. Each section names the function that computes it.

A career here is all Pool PlayerSeasons of one FBref id. Career minutes are the sum of their minutes, so only seasons of 900+ minutes count, and a two-stint season counts each stint that is in the Pool.

## 1. Careers by total Pool minutes

Computed in `main`, from `careers_of` and the sum of Pool minutes.

| minutes at least | careers |
|---|---|
| 6,000 | 338 |
| 7,500 | 253 |
| 9,000 | 188 |
| 10,000 | 152 |

At 9,000: 188 careers. #30 target range: 500 to 1,000.

## 2. Careers by role group

Computed in `role_group`. Role groups from `display_position` (#30 decision 7): FW = Forward, LW/RW = Wide, AM = Central AM. A career's group here is the group with the most Pool minutes over its seasons. That rule is a measuring shortcut, not a decision.

| minutes at least | Forward | Wide | Central AM | tie |
|---|---|---|---|---|
| 6,000 | 183 | 104 | 51 | 0 |
| 7,500 | 143 | 76 | 34 | 0 |
| 9,000 | 110 | 53 | 25 | 0 |
| 10,000 | 86 | 45 | 21 | 0 |

Of the 188 careers at 9,000, 89 hold seasons in more than one role group.

Pool seasons by role group: Forward 1606, Wide 946, Central AM 557 (display_position: {'AM': 557, 'FW': 1606, 'LW': 475, 'RW': 471}).

## 3. Correlation of the 10 metrics across Pool seasons

Computed in `correlation_section` with `numpy.corrcoef`, over the 3109 MetricProfiles from `peer_group_profiles`. The z-scores are what the distance uses. The shrunk values, before the z-score, are shown too.

**z-scores (MetricProfile.values)**

| metric | shots/90 | xa/90 | key_passes/90 | xg_buildup/90 | npxg_per_shot | six_yard% | outside_box% | header% | take_on% | through_ball% |
|---|---|---|---|---|---|---|---|---|---|---|
| shots/90 | 1.00 | 0.19 | 0.06 | 0.10 | 0.11 | 0.06 | -0.09 | 0.10 | -0.02 | 0.09 |
| xa/90 | 0.19 | 1.00 | 0.82 | 0.60 | -0.10 | -0.23 | 0.26 | -0.39 | 0.18 | -0.00 |
| key_passes/90 | 0.06 | 0.82 | 1.00 | 0.58 | -0.26 | -0.37 | 0.45 | -0.48 | 0.18 | -0.10 |
| xg_buildup/90 | 0.10 | 0.60 | 0.58 | 1.00 | -0.06 | -0.20 | 0.23 | -0.36 | 0.15 | 0.00 |
| npxg_per_shot | 0.11 | -0.10 | -0.26 | -0.06 | 1.00 | 0.71 | -0.71 | 0.39 | -0.12 | 0.42 |
| six_yard% | 0.06 | -0.23 | -0.37 | -0.20 | 0.71 | 1.00 | -0.61 | 0.56 | -0.21 | 0.16 |
| outside_box% | -0.09 | 0.26 | 0.45 | 0.23 | -0.71 | -0.61 | 1.00 | -0.64 | 0.15 | -0.30 |
| header% | 0.10 | -0.39 | -0.48 | -0.36 | 0.39 | 0.56 | -0.64 | 1.00 | -0.35 | 0.01 |
| take_on% | -0.02 | 0.18 | 0.18 | 0.15 | -0.12 | -0.21 | 0.15 | -0.35 | 1.00 | -0.03 |
| through_ball% | 0.09 | -0.00 | -0.10 | 0.00 | 0.42 | 0.16 | -0.30 | 0.01 | -0.03 | 1.00 |

Pairs with |r| above 0.8: xa_per_90 and key_passes_per_90: 0.815
Decision 10 trio: xa_per_90 and key_passes_per_90: 0.815; xa_per_90 and xg_buildup_per_90: 0.601; key_passes_per_90 and xg_buildup_per_90: 0.584

**Shrunk values before the z-score (MetricProfile.shrunk)**

| metric | shots/90 | xa/90 | key_passes/90 | xg_buildup/90 | npxg_per_shot | six_yard% | outside_box% | header% | take_on% | through_ball% |
|---|---|---|---|---|---|---|---|---|---|---|
| shots/90 | 1.00 | 0.20 | 0.09 | 0.12 | 0.09 | 0.04 | -0.07 | 0.08 | -0.02 | 0.07 |
| xa/90 | 0.20 | 1.00 | 0.81 | 0.61 | -0.06 | -0.20 | 0.24 | -0.38 | 0.17 | 0.02 |
| key_passes/90 | 0.09 | 0.81 | 1.00 | 0.57 | -0.26 | -0.36 | 0.45 | -0.47 | 0.17 | -0.10 |
| xg_buildup/90 | 0.12 | 0.61 | 0.57 | 1.00 | -0.02 | -0.16 | 0.20 | -0.35 | 0.13 | 0.00 |
| npxg_per_shot | 0.09 | -0.06 | -0.26 | -0.02 | 1.00 | 0.72 | -0.71 | 0.37 | -0.09 | 0.40 |
| six_yard% | 0.04 | -0.20 | -0.36 | -0.16 | 0.72 | 1.00 | -0.61 | 0.53 | -0.18 | 0.19 |
| outside_box% | -0.07 | 0.24 | 0.45 | 0.20 | -0.71 | -0.61 | 1.00 | -0.62 | 0.16 | -0.27 |
| header% | 0.08 | -0.38 | -0.47 | -0.35 | 0.37 | 0.53 | -0.62 | 1.00 | -0.33 | 0.01 |
| take_on% | -0.02 | 0.17 | 0.17 | 0.13 | -0.09 | -0.18 | 0.16 | -0.33 | 1.00 | 0.03 |
| through_ball% | 0.07 | 0.02 | -0.10 | 0.00 | 0.40 | 0.19 | -0.27 | 0.01 | 0.03 | 1.00 |

Pairs with |r| above 0.8: xa_per_90 and key_passes_per_90: 0.807
Decision 10 trio: xa_per_90 and key_passes_per_90: 0.807; xa_per_90 and xg_buildup_per_90: 0.612; key_passes_per_90 and xg_buildup_per_90: 0.573

## 4. Finishing = (npG - npxG) per shot

Computed in `main`: `display_stats.npg_minus_npxg` divided by the PlayerSeason's non-penalty shots (`counts_for_metrics`, own goals out). Raw, with no shrinkage: #30 decision 5 asks for the same shrinkage as other small-sample values, and that rule is not built yet.

| seasons | no shot (left out) | mean | SD | min | 10th pct | median | 90th pct | max |
|---|---|---|---|---|---|---|---|---|
| 3109 | 0 | -0.0051 | 0.0488 | -0.2140 | -0.0651 | -0.0069 | 0.0568 | 0.2522 |

Spread by non-penalty shots in the season (small samples spread wider, which is what shrinkage would pull in):

| shots | seasons | mean | SD |
|---|---|---|---|
| 0-29 | 740 | -0.0095 | 0.0617 |
| 30-59 | 1540 | -0.0051 | 0.0476 |
| 60-99 | 695 | -0.0018 | 0.0372 |
| 100+ | 134 | 0.0016 | 0.0300 |

Correlation (Pearson r) of finishing with each metric, across the same seasons. Raw: raw finishing against the shrunk metric. z: finishing z-scored within its PeerGroup (clipped at ±3, as the others) against the metric's z-score.

| metric | r raw | r z |
|---|---|---|
| shots_per_90 | -0.010 | -0.012 |
| xa_per_90 | 0.080 | 0.088 |
| key_passes_per_90 | 0.099 | 0.101 |
| xg_buildup_per_90 | 0.096 | 0.099 |
| npxg_per_shot | -0.112 | -0.103 |
| six_yard_share | -0.178 | -0.165 |
| outside_box_share | 0.135 | 0.125 |
| header_share | -0.158 | -0.156 |
| take_on_share | 0.036 | 0.043 |
| through_ball_share | -0.019 | 0.003 |

## 5. People that cross_season_ids rows join into one career

Computed in `main`: the `cross_season_ids` rows in `data/standin/review_decisions.csv`, and `cross_season_cases` from the join (each Understat id that reaches 2+ FBref ids across seasons, allowed by such a row).

`cross_season_ids` rows: 0. Cross-season cases in the join: 0 []. People joined into one career by them: 0.

The 3 id merges inside one league-season (Meité, Nduquidi, Strefezza, all 2024) are a different rule and already one FBref id.

## 6. Harry Kane and Mohamed Salah

Computed in `main` from `careers_of` and `role_group`, by exact name.

| name | FBref id | career minutes | seasons covered | Pool seasons | each season (league, season, position, minutes) | role group | 9,000+ |
|---|---|---|---|---|---|---|---|
| Harry Kane | 21a66f6a | 20,645 | 2017/18-2023/24 | 7 | ENG 2017/18 FW 3,076, ENG 2018/19 FW 2,424, ENG 2019/20 FW 2,587, ENG 2020/21 FW 3,082, ENG 2021/22 FW 3,232, ENG 2022/23 FW 3,405, GER 2023/24 FW 2,839 | Forward | yes |
| Mohamed Salah | e342ad68 | 20,697 | 2017/18-2023/24 | 7 | ENG 2017/18 RW 2,907, ENG 2018/19 RW 3,250, ENG 2019/20 RW 2,876, ENG 2020/21 RW 3,078, ENG 2021/22 RW 2,762, ENG 2022/23 RW 3,290, ENG 2023/24 RW 2,534 | Wide | yes |
