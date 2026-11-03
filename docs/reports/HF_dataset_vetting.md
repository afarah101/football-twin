# Hugging Face dataset vetting: aloobun/fbref_understat_combined

Run date: 2026-11-03. Pinned commit: `980fefef65fe802bf89abeb0ddd1ed208a3e1a51`.

**Mode used: NAMES-ONLY.** `config/face_validity_pairs.yaml` is not committed, so this report holds column names, category labels, counts and rates only. It holds no player names and no player values.

One exception needs your review. The rule says column names and row counts only, but task 3 asks for seasons and leagues and task 4 needs position labels. So those category labels are shown. They identify no player and carry no metric.

## Verdict

| Use | Can it replace Understat? | Reason |
|---|---|---|
| (a) Output metrics | **YES, with limits, as a temporary stand-in** | Minutes, shots, npxG, xA, key passes and xGBuildup are all present with 0 nulls. Limits: no 2014/15, no updates after 2024-25, no player id, and values not checked against Understat. |
| (b) Shot profile | **NO** | There are no shot rows. X/Y, `lastAction`, `situation` and `shotType` are absent and cannot be derived. |
| (c) Positions | **NO** | Only broad GK/DF/MF/FW labels exist. All five of FWL, FWR, AML, AMC and AMR have 0 rows, and there are no per-match rosters. |

**The Phase 1 method cannot run on this dataset.** Five of its 10 equal-weight metrics are shot shares, which need the missing shot rows. Using this data means changing the agreed metrics, which is Ahmed's decision.

**"Understat is down" has not been shown.** Two networks failed to connect, but that does not prove the site is down. The hotspot test in `docs/reports/T1_understatapi_vetting.md` is still the cheapest way to find out, and it would decide whether a stand-in is needed at all.

## Findings

| Severity | Finding | Evidence |
|---|---|---|
| **Critical** | No shot-level data, so 5 of the 10 planned metrics cannot be computed. | Tasks 3, 4 |
| **Critical** | No plan-level positions and no rosters, so the Pool rule (Q5 and the FW, FWL, FWR, AML, AMC, AMR list) cannot be applied. Attacking midfielders cannot be separated from other midfielders. | Task 4 |
| Warning | The numbers cannot be traced to source. The README gives no scrape date or method, and Understat could not be reached to compare. Goals agree with FBref on most joined rows, but that does not test xG, xA or xGBuildup. | Tasks 1, 5 |
| Warning | The MIT tag is the uploader's own claim, and there is no licence file. An uploader cannot relicense Understat or FBref data, so it does not settle Q3 or Q18. | Task 1 |
| Warning | No 2014/15 season, and data stops at 2024-25. The last commit is 2026-01-22. It cannot support the current-season search (Q7), the Monday job (#13) or the 2014/15 scope. Only one season, 2024-25, falls after the 2023/24 selection cut (Q10). | Tasks 1, 3 |
| Warning | The Understat file has no player id. Joining needs names, and leaves 1,265 unmatched rows at 900+ minutes. 16.00% of all La Liga rows are unmatched, the worst league. The file has 57 name keys with several rows, and 23 of those sum past 3,420 minutes, which suggests namesakes. I could not confirm this in names-only mode. | Tasks 5, 6 |
| Warning | `player_stats_multi` shots look unreliable: `goals > shots` on 467 rows and `shots_on_target > shots` on 698. Use the Understat `shots` column, not this one. | Task 6 |
| Warning | Non-penalty shots (Q15) need FBref `pkatt` through the imperfect join, and own goals cannot be removed. So shots per 90 and npxG per shot only approximate the plan's definitions. I did not verify whether this `shots` column includes penalties. | Task 4 |
| Info | `player_stats` contains 1,290 repeated header rows, the cause of its 1,230 exact duplicate rows. With them removed it has 0 exact duplicates and the same row count as `player_stats_multi`. | Task 6 |
| Info | One Understat row has minutes above 3,420 and one has apps above 38. Neither has merged clubs. Not inspected, because of names-only mode. | Task 6 |
| Info | 739 Understat rows hold several clubs in one row. That fits Q6, which treats player + league + season as one PlayerSeason. | Task 6 |
| Info | Many columns are 100% empty, including every passing, blocks and `xg_assist_net` column in `player_stats_multi` and `npxg_source` and `npxg_target` in `transfers`. | Task 6 |
| Info | Security result is clean: plain text only, no binaries, 0 formula-style cells, 0 URL or script cells. `.gitattributes` is also present, so strictly the files are CSV, MD and one Git config file. | Task 2 |

## Step 0

```
$ pwd
/Users/ahmed.farah/Projects/football-twin
$ git status -sb
## main...origin/main [ahead 1]
?? config/
$ git log --oneline -- config/
(no output: never committed)
$ wc -c config/face_validity_pairs.yaml
0
```

Hard rules from `CLAUDE.md`: no distance code runs and no metric output is produced or shown until Ahmed has committed `config/face_validity_pairs.yaml`, and nobody else suggests, drafts or edits the pairs. No distance code ran here. The file remains empty and untouched.

Fields the plan needs (`docs/phase-1-plan.md`, Data, Metrics, Pool rules, Decisions):

- Player-season: time, shots, npg, npxG, xA, key_passes, xGBuildup, position.
- Shot rows: location X/Y, lastAction, situation, shotType, result.
- Match rosters: per-match position, for primary position (Q5).
- Metrics: per 90 shots, xA, key passes, xGBuildup; npxG per shot; non-penalty shot shares for six-yard box, outside box, headers, after TakeOn and after Throughball.
- Pool: 2014/15 onward, five leagues, 900-minute minimum, positions FW, FWL, FWR, AML, AMC, AMR.

## Task 1: download

Downloaded with `curl` from pinned `resolve/<sha>/` URLs into `~/sandbox/hf_dump/files`. No dataset code or loader ran.

```
$ for f in <each file>; do curl -fsSL -o "$f" "https://huggingface.co/datasets/aloobun/fbref_understat_combined/resolve/980fefef65fe802bf89abeb0ddd1ed208a3e1a51/$f"; done

$ curl -sS 'https://huggingface.co/api/datasets/aloobun/fbref_understat_combined?blobs=true'
id = aloobun/fbref_understat_combined
author = aloobun
sha = 980fefef65fe802bf89abeb0ddd1ed208a3e1a51
lastModified = 2026-01-22T14:29:53.000Z
createdAt = 2026-01-22T14:23:15.000Z
private = False
gated = False
downloads = 73
likes = 0
tags = ['license:mit', 'size_categories:100K<n<1M', 'format:csv', 'modality:tabular', 'modality:text', 'library:datasets', 'library:pandas', 'library:polars', 'library:mlcroissant', 'region:us', 'fbref', 'understat', 'football']

$ curl -sS https://huggingface.co/api/datasets/aloobun/fbref_understat_combined/commits/main
980fefef65 2026-01-22 aloobun Update README.md
7b1c5dbeae 2026-01-22 aloobun Update README.md
0f96e30a84 2026-01-22 aloobun Update README.md
38ac734aaf 2026-01-22 aloobun Update README.md
1310c61bff 2026-01-22 aloobun Upload football dataset with multiple configs
b832f60bc9 2026-01-22 aloobun initial commit

$ curl -sS https://huggingface.co/api/users/aloobun/overview
{'user': 'aloobun', 'fullname': 'aloobun', 'createdAt': '2023-09-20T06:40:02.000Z', 'numDatasets': 11, 'numModels': 63, 'numFollowers': 43, 'type': 'user'}

$ find files -type f -exec wc -c {} + ; find files -type f -exec shasum -a 256 {} + ; find files -type f -exec file {} +
    1359 files/README.md
    2461 files/.gitattributes
  316415 files/data/skills_multi/player_skills_multi.csv
 7815906 files/data/player_stats/master_player_stats.csv
 4246594 files/data/understat_xg/understat_xg_data.csv
   74215 files/data/transfers/transfers_v1.csv
 7918232 files/data/player_stats_multi/master_player_stats_multi.csv
  158678 files/data/skills/player_skills.csv
   68913 files/data/transfers_multi/transfers_v2_multi.csv
 20602773 total

e6f3745755f66902bd920abbc0236a375d0a9f92559e04296cb98e3e9547b45b  files/README.md
e7a120ab07b1bc5b486be249e9fc6c83d59448d0093e1dfebe95d1566d9cafc0  files/.gitattributes
52acae7c09c9135a7fa0d7370939ef7fd3418d3b2a378322186e0bbf64515a7a  files/data/skills_multi/player_skills_multi.csv
96a5379af53321616d727bb49259befc0506755b0e2829859ce191146f65a8c8  files/data/player_stats/master_player_stats.csv
4e3751c47205c274315bb99f7df983adc4d15fe03c454590299587e7d3b3e475  files/data/understat_xg/understat_xg_data.csv
35f1d8e69c130d826d093940f88aa290617649184e6f0cfde48a008e46355bfd  files/data/transfers/transfers_v1.csv
1dbbfd975e6b2a07ac2b110ae98abf53e475dfa0f5315b3d3b2315e1ab5a5fc8  files/data/player_stats_multi/master_player_stats_multi.csv
994adff855843c88aef46b6c6d3ece7d8cc528028f1d5d601dee9e7c0073a654  files/data/skills/player_skills.csv
49189f6e18f3dad9d224e7a82789eefe8469046eb42796f52627dd458cc0d17b  files/data/transfers_multi/transfers_v2_multi.csv

files/README.md:                                             ASCII text
files/.gitattributes:                                        ASCII text
files/data/skills_multi/player_skills_multi.csv:             CSV text
files/data/player_stats/master_player_stats.csv:             CSV text
files/data/understat_xg/understat_xg_data.csv:               CSV text
files/data/transfers/transfers_v1.csv:                       CSV text
files/data/player_stats_multi/master_player_stats_multi.csv: CSV text
files/data/skills/player_skills.csv:                         CSV text
files/data/transfers_multi/transfers_v2_multi.csv:           CSV text
```

| Item | Value |
|---|---|
| Commit | `980fefef65fe802bf89abeb0ddd1ed208a3e1a51` |
| Licence | MIT, by README tag only. No licence file. |
| Uploader | `aloobun` |
| Total size | 20,602,773 bytes across 9 files |
| README statement | Covers 2015-16 to 2024-25. Names Understat as the xG source. No scrape date or method. |

## Task 2: security

Script: `~/sandbox/hf_dump/tools/security_check.py`. It checks every cell and prints no cell content. Signed numbers are counted apart from formula-style text. All 13,322 leading-sign cells across the files (1 + 4,251 + 9,070) are plain numbers.

```
$ python3 -I tools/security_check.py files

== .gitattributes  bytes=2461  NUL=0  head_is_binary_magic=False

== README.md  bytes=1359  NUL=0  head_is_binary_magic=False

== data/player_stats/master_player_stats.csv  bytes=7815906  NUL=0  head_is_binary_magic=False
columns 30 ['rank', 'player', 'player_id', 'nation', 'pos', 'squad', 'age', 'birth_year', 'mp', 'starts', 'min', '90s', 'gls', 'ast', 'g_a', 'g_pk', 'pk', 'pkatt', 'crdy', 'crdr', 'goals_per90', 'assists_per90', 'goals_assists_per90', 'goals_pens_per90', 'goals_assists_pens_per90', 'matches', 'season', 'league', 'source_file', 'unique_key']
rows 34246 | rows with wrong column count 0
signed numbers (not formulas) 0
non-numeric cells starting = + - @ {}
other {}

== data/player_stats_multi/master_player_stats_multi.csv  bytes=7918232  NUL=0  head_is_binary_magic=False
columns 88 ['player', 'player_id', 'ranker', 'nationality', 'position', 'squad', 'age', 'birth_year', 'games', 'games_starts', 'minutes', 'minutes_90s', 'goals', 'assists', 'goals_assists', 'goals_pens', 'pens_made', 'pens_att', 'cards_yellow', 'cards_red', 'goals_per90', 'assists_per90', 'goals_assists_per90', 'goals_pens_per90', 'goals_assists_pens_per90', 'matches', 'season', 'league', 'tackles', 'tackles_won', 'tackles_def_3rd', 'tackles_mid_3rd', 'tackles_att_3rd', 'challenge_tackles', 'challenges', 'challenge_tackles_pct', 'challenges_lost', 'blocks', 'blocked_shots', 'blocked_passes', 'interceptions', 'tackles_interceptions', 'clearances', 'errors', 'passes_completed', 'passes', 'passes_pct', 'passes_total_distance', 'passes_progressive_distance', 'passes_completed_short', 'passes_short', 'passes_pct_short', 'passes_completed_medium', 'passes_medium', 'passes_pct_medium', 'passes_completed_long', 'passes_long', 'passes_pct_long', 'xg_assist_net', 'assisted_shots', 'passes_into_final_third', 'passes_into_penalty_area', 'crosses_into_penalty_area', 'shots', 'shots_on_target', 'shots_on_target_pct', 'shots_per90', 'shots_on_target_per90', 'goals_per_shot', 'goals_per_shot_on_target', 'gk_games', 'gk_games_starts', 'gk_minutes', 'gk_goals_against', 'gk_goals_against_per90', 'gk_shots_on_target_against', 'gk_saves', 'gk_save_pct', 'gk_wins', 'gk_ties', 'gk_losses', 'gk_clean_sheets', 'gk_clean_sheets_pct', 'gk_pens_att', 'gk_pens_allowed', 'gk_pens_saved', 'gk_pens_missed', 'gk_pens_save_pct']
rows 32956 | rows with wrong column count 0
signed numbers (not formulas) 1
non-numeric cells starting = + - @ {}
other {}

== data/skills/player_skills.csv  bytes=158678  NUL=0  head_is_binary_magic=False
columns 3 ['player_id', 'adjusted_skill', 'skill_uncertainty']
rows 7431 | rows with wrong column count 0
signed numbers (not formulas) 4251
non-numeric cells starting = + - @ {}
other {}

== data/skills_multi/player_skills_multi.csv  bytes=316415  NUL=0  head_is_binary_magic=False
columns 7 ['player_id', 'adj_goals', 'adj_goals_sd', 'adj_tackles_won', 'adj_tackles_won_sd', 'adj_interceptions', 'adj_interceptions_sd']
rows 7129 | rows with wrong column count 0
signed numbers (not formulas) 9070
non-numeric cells starting = + - @ {}
other {}

== data/transfers/transfers_v1.csv  bytes=74215  NUL=0  head_is_binary_magic=False
columns 20 ['player_id', 'player_name', 'transfer_type', 'season_source', 'season_target', 'age_at_transfer', 'league_source', 'squad_source', 'min_source', 'gls_source', 'ast_source', 'npxg_source', 'league_target', 'squad_target', 'min_target', 'gls_target', 'ast_target', 'npxg_target', 'gls_90_source', 'ast_90_source']
rows 482 | rows with wrong column count 0
signed numbers (not formulas) 0
non-numeric cells starting = + - @ {}
other {}

== data/transfers_multi/transfers_v2_multi.csv  bytes=68913  NUL=0  head_is_binary_magic=False
columns 24 ['player_id', 'player_name', 'transfer_type', 'season_source', 'season_target', 'age_at_transfer', 'league_source', 'squad_source', 'minutes_source', 'gls_source', 'ast_source', 'gls_90_source', 'ast_90_source', 'tackles_won_source', 'interceptions_source', 'blocks_source', 'passes_completed_source', 'passes_pct_source', 'prog_passes_source', 'league_target', 'squad_target', 'minutes_target', 'gls_target', 'ast_target']
rows 482 | rows with wrong column count 0
signed numbers (not formulas) 0
non-numeric cells starting = + - @ {}
other {}

== data/understat_xg/understat_xg_data.csv  bytes=4246594  NUL=0  head_is_binary_magic=False
columns 18 ['player_name', 'team', 'league', 'season', 'apps', 'minutes', 'goals', 'assists', 'shots', 'key_passes', 'xG', 'xA', 'npxG', 'xGChain', 'xGBuildup', 'xG90', 'xA90', 'npxG90']
rows 27182 | rows with wrong column count 0
signed numbers (not formulas) 0
non-numeric cells starting = + - @ {}
other {}
```

Independent line-level grep, counting lines where any cell starts with `=`, `+` or `@`, or `-` followed by a non-number:

```
data/player_stats/master_player_stats.csv  =,+,@ lines: 0  -non-number lines: 0
data/player_stats_multi/master_player_stats_multi.csv  =,+,@ lines: 0  -non-number lines: 0
data/skills/player_skills.csv  =,+,@ lines: 0  -non-number lines: 0
data/skills_multi/player_skills_multi.csv  =,+,@ lines: 0  -non-number lines: 0
data/transfers/transfers_v1.csv  =,+,@ lines: 0  -non-number lines: 0
data/transfers_multi/transfers_v2_multi.csv  =,+,@ lines: 0  -non-number lines: 0
data/understat_xg/understat_xg_data.csv  =,+,@ lines: 0  -non-number lines: 0
```

`.gitattributes` non-LFS lines:

```
# Audio files - uncompressed
# Audio files - compressed
# Image files - uncompressed
# Image files - compressed
# Video files - compressed
(end)
```

## Task 3: coverage

Columns and row counts per file are in the Task 2 output. Season and league counts:

```
$ python3 -I tools/coverage.py files

== data/understat_xg/understat_xg_data.csv  rows=27182
[league x season] leagues=5 seasons=10
season,EPL,ESP,FRA,GER,ITA
2015-2016,550,539,575,476,551
2016-2017,524,541,559,470,560
2017-2018,515,557,540,472,533
2018-2019,505,531,548,468,543
2019-2020,515,556,531,487,572
2020-2021,524,570,575,496,594
2021-2022,537,603,589,511,608
2022-2023,554,584,585,506,577
2023-2024,570,598,525,494,590
2024-2025,562,590,542,481,599

== data/player_stats/master_player_stats.csv  rows=34246
[league x season] leagues=6 seasons=10
season,EPL,ESP,FRA,GER,ITA,NED
2015-2016,583,567,611,511,607,491
2016-2017,564,577,598,494,605,503
2017-2018,550,595,575,503,575,496
2018-2019,528,565,583,492,591,498
2019-2020,542,592,563,517,624,503
2020-2021,553,605,607,525,643,542
2021-2022,567,641,628,543,657,554
2022-2023,591,619,630,535,627,547
2023-2024,603,633,561,527,640,544
2024-2025,596,625,575,511,659,555

== data/player_stats_multi/master_player_stats_multi.csv  rows=32956
[league x season] leagues=6 seasons=10
season,EPL,ESP,FRA,GER,ITA,NED
2015-2016,561,546,588,492,584,473
2016-2017,543,555,575,475,582,484
2017-2018,529,573,553,484,553,477
2018-2019,508,544,561,474,569,479
2019-2020,522,570,542,498,600,484
2020-2021,532,582,584,505,619,522
2021-2022,546,617,604,523,632,533
2022-2023,569,596,606,515,603,526
2023-2024,580,609,540,507,616,524
2024-2025,574,601,553,492,634,534

== data/transfers/transfers_v1.csv  rows=482
[league_source x season_source] leagues=5 seasons=9
season,ESP,FRA,GER,ITA,NED
2015-2016,15,17,11,5,7
2016-2017,12,10,15,11,11
2017-2018,17,12,14,7,7
2018-2019,7,10,10,4,2
2019-2020,13,14,8,6,7
2020-2021,10,12,9,13,4
2021-2022,13,22,13,13,8
2022-2023,13,16,11,13,8
2023-2024,15,12,11,11,3
[league_target x season_target] leagues=1 seasons=9
season,EPL
2016-2017,48
2017-2018,48
2018-2019,56
2019-2020,43
2020-2021,50
2021-2022,47
2022-2023,69
2023-2024,64
2024-2025,57

== data/transfers_multi/transfers_v2_multi.csv  rows=482
[league_source x season_source] leagues=5 seasons=9
season,ESP,FRA,GER,ITA,NED
2015-2016,15,17,11,5,7
2016-2017,12,10,15,11,11
2017-2018,17,12,14,7,7
2018-2019,7,10,10,4,2
2019-2020,13,14,8,6,7
2020-2021,10,12,9,13,4
2021-2022,13,22,13,13,8
2022-2023,13,16,11,13,8
2023-2024,15,12,11,11,3
[league_target x season_target] leagues=1 seasons=9
season,EPL
2016-2017,48
2017-2018,48
2018-2019,56
2019-2020,43
2020-2021,50
2021-2022,47
2022-2023,69
2023-2024,64
2024-2025,57

== data/skills/player_skills.csv  rows=7431
no season or league column

== data/skills_multi/player_skills_multi.csv  rows=7129
no season or league column
```

Plan scope compared with the Understat file: all five leagues are present. 2014/15 is missing. Seasons run 2015-2016 to 2024-2025. There is no current season.

## Task 4: gap table

| # | Field | Status | Where or how |
|---|---|---|---|
| 1 | time | **PRESENT** | `understat_xg.minutes`, 0 nulls |
| 2 | shots | **PRESENT** | `understat_xg.shots`, 0 nulls. Non-penalty shots (Q15) would need `shots - pkatt` through the join. Own goals cannot be removed. |
| 3 | npg | **DERIVABLE** | FBref `player_stats.g_pk` through the join. `g_pk != gls - pk` has 0 violations. At 900+ minutes, 14,314 rows join to one FBref row. |
| 4 | npxG | **PRESENT** | `understat_xg.npxG`, 0 nulls |
| 5 | xA | **PRESENT** | `understat_xg.xA`, 0 nulls |
| 6 | key_passes | **PRESENT** | `understat_xg.key_passes`, 0 nulls |
| 7 | xGBuildup | **PRESENT** | `understat_xg.xGBuildup`, 0 nulls |
| 8 | position | **MISSING** | FBref has only GK, DF, MF and FW combinations. FWL, FWR, AML, AMC and AMR have 0 rows. No per-match position. FW itself exists but alone does not meet the plan. |
| 9 | shot X/Y | **MISSING** | No shot rows in any file |
| 10 | lastAction | **MISSING** | No shot rows in any file |
| 11 | situation | **MISSING** | No shot rows in any file |
| 12 | shotType | **MISSING** | No shot rows in any file |

Totals: 6 present, 1 derivable, 5 missing. The plan's shot `result` field and match rosters are also missing.

Effect on the 10 metrics:

| Metric | Possible? |
|---|---|
| xA per 90, key passes per 90, xGBuildup per 90 | Yes |
| Shots per 90, npxG per shot | Approximate only, see Q15 note |
| Six-yard, outside-box, header, after-TakeOn, after-Throughball shares | No |

## Task 5: join test

Understat (`player_name`, `season`, `league`) to FBref `player_stats` (`player`, `season`, `league`), tried as exact, then accent-folded, then token-set. No fuzzy matching. Season and league labels already agree, so no mapping was needed. Scripts: `tools/join_integrity.py`, `tools/supplement.py`. The supplement repeats the join with header rows removed; the match counts do not change.

| Set | Rows | Matched | Match rate | Unmatched | One FBref row | Several FBref rows |
|---|---|---|---|---|---|---|
| All Understat rows | 27,182 | 24,810 | 91.27% | 2,372 | 24,066 | 744 |
| Understat minutes >= 900 | 16,082 | 14,817 | 92.13% | 1,265 | 14,314 | 503 |

Raw output for the join is below with Task 6, in the two script blocks.

No match was checked by hand, because that would need player names. Agreement on goals and minutes gives indirect support only. Same-named different players could match by accident.

## Task 6: integrity

Counts only.

```
$ python3 -I tools/join_integrity.py files
=== JOIN: understat_xg -> player_stats on (player, season, league)
fbref rows in the 5 leagues 29013 | NED rows left out 5233

[all rows] understat rows 27182
matched 24810 (91.27%) | unmatched 2372 (8.73%)
by level {'exact': 22201, 'unmatched': 2372, 'accent_fold': 2570, 'token_set': 39}
matched to more than one fbref row 744
single matches, minutes difference {'within_90': 13041, 'within_5': 10962, 'over_90': 63}
single matches, goals {'same': 23951, 'differ': 115}

[understat minutes >= 900] understat rows 16082
matched 14817 (92.13%) | unmatched 1265 (7.87%)
by level {'exact': 13294, 'unmatched': 1265, 'accent_fold': 1506, 'token_set': 17}
matched to more than one fbref row 503
single matches, minutes difference {'within_90': 8441, 'within_5': 5827, 'over_90': 46}
single matches, goals {'same': 14219, 'differ': 95}
league EPL: rows 5356 unmatched 292 (5.45%)
league ESP: rows 5669 unmatched 907 (16.00%)
league FRA: rows 5569 unmatched 534 (9.59%)
league GER: rows 4861 unmatched 254 (5.23%)
league ITA: rows 5727 unmatched 385 (6.72%)

understat (player, season, league) keys with more than one row: 57
rows sharing such a key: 115
fbref (player, season, league) keys with more than one row: 821
fbref rows sharing such a key: 2639
understat file has a player id column: False

=== POSITION LABELS (category labels and counts, no players)
player_stats pos [('MF', 8341), ('DF', 7170), ('FW', 3685), ('MFFW', 2153), ('GK', 2099), ('FWMF', 1874), ('DFMF', 1565), ('Pos', 1093), ('MFDF', 981), ('DFFW', 44), ('FWDF', 4), ('', 4)]
player_stats_multi position [('MF', 8341), ('DF', 7170), ('FW', 3685), ('MF,FW', 2153), ('GK', 2099), ('FW,MF', 1874), ('DF,MF', 1565), ('MF,DF', 981), ('DF,FW', 44), ('FW,DF', 4), ('', 4)]
plan labels present in player_stats: {'FW': 3685, 'FWL': 0, 'FWR': 0, 'AML': 0, 'AMC': 0, 'AMR': 0, 'MF': 8341}

=== INTEGRITY: per file

[understat_xg] rows 27182 | exact duplicate rows 0
columns with no nulls: 18 of 18

[player_stats] rows 34246 | exact duplicate rows 1230
columns with no nulls: 7 of 30
  null rank: 1290 (3.77%)
  null player_id: 1290 (3.77%)
  null nation: 27 (0.08%)
  null pos: 5 (0.01%)
  null age: 1304 (3.81%)
  null birth_year: 1304 (3.81%)
  null mp: 1290 (3.77%)
  null starts: 1290 (3.77%)
  null min: 1291 (3.77%)
  null 90s: 1290 (3.77%)
  null gls: 1291 (3.77%)
  null ast: 1291 (3.77%)
  null g_a: 1291 (3.77%)
  null g_pk: 1291 (3.77%)
  null pk: 1291 (3.77%)
  null pkatt: 1291 (3.77%)
  null crdy: 1290 (3.77%)
  null crdr: 1290 (3.77%)
  null goals_per90: 1291 (3.77%)
  null assists_per90: 1291 (3.77%)
  null goals_assists_per90: 1291 (3.77%)
  null goals_pens_per90: 1291 (3.77%)
  null goals_assists_pens_per90: 1291 (3.77%)

[player_stats_multi] rows 32956 | exact duplicate rows 0
columns with no nulls: 12 of 88
  null nationality: 27 (0.08%)
  null position: 5 (0.02%)
  null age: 14 (0.04%)
  null birth_year: 14 (0.04%)
  null minutes: 1 (0.00%)
  null goals: 1 (0.00%)
  null assists: 1 (0.00%)
  null goals_assists: 1 (0.00%)
  null goals_pens: 1 (0.00%)
  null pens_made: 1 (0.00%)
  null pens_att: 1 (0.00%)
  null goals_per90: 1 (0.00%)
  null assists_per90: 1 (0.00%)
  null goals_assists_per90: 1 (0.00%)
  null goals_pens_per90: 1 (0.00%)
  null goals_assists_pens_per90: 1 (0.00%)
  null tackles: 32956 (100.00%)
  null tackles_won: 3209 (9.74%)
  null tackles_def_3rd: 32956 (100.00%)
  null tackles_mid_3rd: 32956 (100.00%)
  null tackles_att_3rd: 32956 (100.00%)
  null challenge_tackles: 32956 (100.00%)
  null challenges: 32956 (100.00%)
  null challenge_tackles_pct: 32956 (100.00%)
  null challenges_lost: 32956 (100.00%)
  null blocks: 32956 (100.00%)
  null blocked_shots: 32956 (100.00%)
  null blocked_passes: 32956 (100.00%)
  null interceptions: 3209 (9.74%)
  null tackles_interceptions: 32956 (100.00%)
  null clearances: 32956 (100.00%)
  null errors: 32956 (100.00%)
  null passes_completed: 32956 (100.00%)
  null passes: 32956 (100.00%)
  null passes_pct: 32956 (100.00%)
  null passes_total_distance: 32956 (100.00%)
  null passes_progressive_distance: 32956 (100.00%)
  null passes_completed_short: 32956 (100.00%)
  null passes_short: 32956 (100.00%)
  null passes_pct_short: 32956 (100.00%)
  null passes_completed_medium: 32956 (100.00%)
  null passes_medium: 32956 (100.00%)
  null passes_pct_medium: 32956 (100.00%)
  null passes_completed_long: 32956 (100.00%)
  null passes_long: 32956 (100.00%)
  null passes_pct_long: 32956 (100.00%)
  null xg_assist_net: 32956 (100.00%)
  null assisted_shots: 32956 (100.00%)
  null passes_into_final_third: 32956 (100.00%)
  null passes_into_penalty_area: 32956 (100.00%)
  null crosses_into_penalty_area: 32956 (100.00%)
  null shots: 3208 (9.73%)
  null shots_on_target: 480 (1.46%)
  null shots_on_target_pct: 9312 (28.26%)
  null shots_per90: 3208 (9.73%)
  null shots_on_target_per90: 480 (1.46%)
  null goals_per_shot: 9312 (28.26%)
  null goals_per_shot_on_target: 10264 (31.14%)
  null gk_games: 30538 (92.66%)
  null gk_games_starts: 30538 (92.66%)
  null gk_minutes: 30541 (92.67%)
  null gk_goals_against: 30538 (92.66%)
  null gk_goals_against_per90: 30541 (92.67%)
  null gk_shots_on_target_against: 30577 (92.78%)
  null gk_saves: 30578 (92.78%)
  null gk_save_pct: 30619 (92.91%)
  null gk_wins: 30538 (92.66%)
  null gk_ties: 30538 (92.66%)
  null gk_losses: 30538 (92.66%)
  null gk_clean_sheets: 30538 (92.66%)
  null gk_clean_sheets_pct: 30642 (92.98%)
  null gk_pens_att: 30747 (93.30%)
  null gk_pens_allowed: 30747 (93.30%)
  null gk_pens_saved: 30747 (93.30%)
  null gk_pens_missed: 30747 (93.30%)
  null gk_pens_save_pct: 31407 (95.30%)

[transfers] rows 482 | exact duplicate rows 0
columns with no nulls: 18 of 20
  null npxg_source: 482 (100.00%)
  null npxg_target: 482 (100.00%)

[transfers_multi] rows 482 | exact duplicate rows 0
columns with no nulls: 18 of 24
  null tackles_won_source: 42 (8.71%)
  null interceptions_source: 42 (8.71%)
  null blocks_source: 482 (100.00%)
  null passes_completed_source: 482 (100.00%)
  null passes_pct_source: 482 (100.00%)
  null prog_passes_source: 482 (100.00%)

[skills] rows 7431 | exact duplicate rows 0
columns with no nulls: 3 of 3

[skills_multi] rows 7129 | exact duplicate rows 0
columns with no nulls: 3 of 7
  null adj_tackles_won: 455 (6.38%)
  null adj_tackles_won_sd: 455 (6.38%)
  null adj_interceptions: 455 (6.38%)
  null adj_interceptions_sd: 455 (6.38%)

=== IMPOSSIBLE VALUES AND MINUTES (counts)
[understat_xg]
  negative cells: 0
  non-numeric cells: 0
  minutes > 3420 in one row: 1
  player+league+season minutes sum > 3420: 24
  player+season minutes sum > 3420 (any league): 57
  apps > 38: 1
  minutes > apps * 120: 0
  goals > shots: 0
  npxG > xG + 0.001: 0
  xGBuildup > xGChain + 0.001: 0
  assists > key_passes: 0
  shots > 0 with 0 minutes: 0
  |xG90 - xG*90/minutes| > 0.01: 0
  |npxG90 - npxG*90/minutes| > 0.01: 0
[player_stats]
  negative cells: 0
  non-numeric cells: 0
  min > 3420 in one row: 0 (rows with a missing number, skipped: 1291)
  player_id+league+season minutes sum > 3420: 0
  player_id+season minutes sum > 3420 (any league): 0
  mp > 38: 0 (rows with a missing number, skipped: 1290)
  starts > mp: 0 (rows with a missing number, skipped: 1290)
  min > mp * 120: 0 (rows with a missing number, skipped: 1291)
  g_pk != gls - pk: 0 (rows with a missing number, skipped: 1291)
  pk > pkatt: 1 (rows with a missing number, skipped: 1291)
  duplicate unique_key: 2081
  duplicate player_id+season+league+squad: 1230
[player_stats_multi]
  negative cells: 0
  non-numeric cells: 0
  minutes > 3420 in one row: 0 (rows with a missing number, skipped: 1)
  player_id+league+season minutes sum > 3420: 0
  goals_pens != goals - pens_made: 0 (rows with a missing number, skipped: 1)
  shots_on_target > shots: 698 (rows with a missing number, skipped: 3208)
  goals > shots: 467 (rows with a missing number, skipped: 3208)
  passes_completed > passes: 0 (rows with a missing number, skipped: 32956)
  duplicate player_id+season+league+squad: 0
[skills, skills_multi]
  duplicate player_id: 0 0
[transfers, transfers_multi]
  transfers: minutes > 3420: 0 | season_target <= season_source: 0
  transfers_multi: minutes > 3420: 0 | season_target <= season_source: 0
```

```
$ python3 -I tools/supplement.py files
player_stats repeated header rows: 1290 | other rows: 32956
player_stats rows with null player_id after removing them: 0
exact duplicate rows after removing them: 0
duplicate unique_key after removing them: 851
clean player_stats rows == player_stats_multi rows: True 32956 32956
clean fbref rows in the 5 leagues: 27920
clean fbref (player, season, league) keys with more than one row: 771 | rows: 1546
clean fbref (player_id, season, league) keys with more than one row: 739 | rows: 1479

Join on clean fbref rows, any of exact, accent fold, token set (token set covers the other two):
[all understat rows] rows 27182 | matched 24810 (91.27%) | unmatched 2372 (8.73%) | one fbref row 24066 | several fbref rows 744, of which one player_id 678, several player_ids 66
[understat minutes >= 900] rows 16082 | matched 14817 (92.13%) | unmatched 1265 (7.87%) | one fbref row 14314 | several fbref rows 503, of which one player_id 456, several player_ids 47
understat >= 900 minutes joined to an fbref row with FW in pos: 3711
clean fbref rows with FW in pos and min >= 900: 3966

Understat stints and namesakes:
rows whose team holds a comma (several clubs merged in one row): 739
of those, minutes >= 900: 504
(player, season, league) keys with several rows: 57 | with different teams: 56
keys with several rows and summed minutes > 3420: 23
single rows with minutes > 3420, of which team holds a comma: 1 0
single rows with apps > 38, of which team holds a comma: 1 0
understat rows with shots > 0: 22379

FBref per-file shots against Understat shots, single joined rows with both numbers:
same 11587 | differ 1558 | no comparable row 1169
pkatt available on joined single rows at >= 900 minutes: 14314
understat shots < fbref pkatt on those rows: 0
```

## Task 7: verdict reasons

**(a) Output metrics: YES, with limits.** Six of the seven numeric fields are directly present and the file's internal checks are clean: 0 negatives, 0 nulls and 0 failures on `npxG > xG`, `xGBuildup > xGChain` and `goals > shots`. Limits are those in the Findings table. It suits offline exploration of completed seasons once the pairs are committed. It does not suit the public site's Monday job.

**(b) Shot profile: NO.** No file has shot rows, and season totals cannot rebuild location or action shares.

**(c) Positions: NO.** Broad labels cannot apply the agreed position list, and there is no per-match data for primary position.

## Limits of this check

- Dataset values were not compared with live Understat, because the site could not be reached.
- Names-only mode meant no row could be inspected, so causes of odd counts are inferences.
- The Sports Reference and Understat terms were not read.
- `skills` and `transfers` files were checked only for basics, since the plan does not use them.

## Scope

- Changed in the repo: this report only. No data files in the repo.
- Not touched: `config/`, `CLAUDE.md`, `GLOSSARY.md`, `docs/phase-1-plan.md`, issues, `.github/`. Nothing pushed.
- Sandbox kept at `~/sandbox/hf_dump` so results can be reproduced. Remove with `rm -rf ~/sandbox/hf_dump`.