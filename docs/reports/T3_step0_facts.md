# T3: STEP 0 data facts from the stand-in files

Run date: 2026-11-03. Issue: #3. Repo position at the start: `08d85e7`, level with origin. Analysis ran on a cache of the 35 `.rds` originals read with `rdata` under the plan's three rules, plus the 3 CSV originals. The scripts are in the appendix, and every number below comes from output shown in this report.

## Verdict

| Criterion of #3 | Result |
|---|---|
| 1. Exact strings | **Met** |
| 2. Season coverage | **Met** |
| 3. Planned fields | **Met**: all present in a named file. `npg` has to be rebuilt from shots. |
| 4. Joins | **Met** |
| 5. Box boundaries | **Met**: proposed constants below, for X and Y |
| 6. Real samples | **Met**: 22 files, all real rows |
| 7. Cases not found | **Met**: two reported and left out |
| 8. Terms | **Met**: read and summarised. What they mean for launch is unclear, and that is Ahmed's call. |

**Ready for #7: YES.** Reasons and conditions are in the last section.

## Findings

| Severity | Finding | Section |
|---|---|---|
| **Critical, launch only** | Sports Reference's data use page says "you should not create websites or tools based on data you scrape". The planned public site is built on FBref positions and minutes scraped by a third party. This does not affect private work in #7. It needs Ahmed's decision before #13. | 8 |
| Warning | The plan's box estimates are X only. With X alone, 1,342 of 20,357 direct free kicks (6.592%) count as inside the box, against 43 (0.211%) with the proposed Y lines. Y lines move 2,408 shots out of the box and 11,150 out of the six-yard box. Six-yard share falls from 9.63% to 7.38%. | 5 |
| Warning | The six-yard lines rest on weaker evidence than the box lines. Free kicks can only test the penalty box. The six-yard lines come from the scale of the penalty spot and from density dips. | 5 |
| Warning | No single FBref file is complete. `ESP` passing has 239 of 380 matches in 2020/21, `ESP` possession 10 of 380 in 2019/20 and `ITA` misc 74 of 380 in 2023/24. #7 needs the union of the five Pos files. The union still lacks one match in GER 2021/22 and one in ITA 2020/21. It holds extra match URLs in ITA 2022/23 (381) and 2023/24 (383). | 2 |
| Warning | Shot files and FBref join only by name. With names compared without accents or word order, 92.11% of Pool candidates find shots, and La Liga is lowest at 85.35%. Unmatched attackers would drop out or lose their shot metrics unless a name map is built. No matched pair was checked by hand. | 4 |
| Warning | Names are not unique. 24 shot-file name-seasons hold two `player_id` values, 38 FBref name-seasons hold two `Player_Href` values, and HF has no id. HF has 39 keys with several rows. | 4 |
| Warning | FBref `Min` is stored as text (`large_string`), not a number. Any sum needs a conversion. 6 rows in the five leagues' passing files have no `Min` value. | 2, 3 |
| Warning | HF and FBref minutes differ near the 900 line: the `under_900` player has 899 in FBref and 893 in HF. The plan's gate depends on which source is used, and on the stand-in source it is FBref. | 6 |
| Warning | Match event files have gaps in Pool seasons, including ITA 2019/20 (312 of 380) and 370 of 380 in 2022/23 for ESP, FRA and ITA. Substitutes come from these files, so a few matches cannot apply the rule that ignores substitute appearances. | 2 |
| Info | Understat fields `time`, `npg`, `npxG`, `xA` and `key_passes` are not in the shot files. HF holds them, except `npg`, which is rebuilt from shots. `xGBuildup` is only in HF. | 3 |
| Info | `lastAction` holds the literal text `None` on 59,088 rows. It is a label, not a null. | 1 |
| Info | 6 cells in `GER_M_1st_defense` have an empty Pos. All other Pos cells have a label. | 2 |
| Info | There is no `Sub` value in Pos, so `Sub` from the plan does not exist on this source. | 1, 7 |
| Info | Shot and event times differ by one for the own-goal sample: minute 9 in the shot file, 10 in the events. Own-goal rows joined on date and name for 143 of 195 La Liga shots. The other 52 were not looked into. | 6 |
| Info | `.rds` files carry a `scrape_timestamp` attribute. It causes `rdata` warnings about missing R classes, and no column is affected in the 3 files checked. | Appendix |
| Info | Everything ran on Python 3.15 on macOS arm64. The repo has no dependency file yet, and adding one was out of scope. | Appendix |

## Step 0

```
$ pwd
/Users/ahmed.farah/Projects/football-twin
$ git status --short --branch; git rev-list --left-right --count HEAD...origin/main
## main...origin/main
0	0
$ git log --oneline -3
08d85e7 docs: allow rdata with reading rules, record round-trip result
4d10d5e docs: record library vetting, add pyarrow, leave rdata pending
70d590f docs: store stand-in files as Parquet and gate launch on recorded terms
$ grep -n 'Allowed libraries' docs/phase-1-plan.md
51:- Allowed libraries: understatapi, pandas, numpy, scipy, scikit-learn, pyyaml, pytest, pyarrow, rdata. pyreadr is not allowed (AGPL). See `docs/reports/library_vetting.md`.
$ grep -n 'stand-in-originals' docs/phase-1-plan.md
113:- Original stand-in files: private release https://github.com/afarah101/football-twin/releases/tag/stand-in-originals, with their hashes in its release notes.
```

Release assets against the release notes, GitHub's digest and the `~/sandbox` copies:

```
$ python3 -I check_release.py release.json release_assets release_files.txt
names: notes 38 assets 38 on disk 38 only notes [] only assets []
mismatches 0
$ grep -c 'local_original True' release_check.txt
38
```

Read before starting: `docs/phase-1-plan.md`, issues #1, #3 and #7, `docs/reports/WFR_shots_vetting.md`, `docs/reports/WFR_positions_vetting.md` and `docs/reports/HF_dataset_vetting.md`.

## 1. Exact strings

> Exact lastAction, situation, shotType and result strings are confirmed from the shot files, and position labels from FBref Pos

**Met.** The strings are below, exactly as stored. Every label the plan relies on exists: `TakeOn`, `Throughball`, `Head`, `Penalty`, `OwnGoal`.

Pos has 13 main labels, plus `MF` and `DF` on a few rows and 6 empty cells. Attacking labels under the plan's rule are `FW`, `LW`, `RW`, `AM`. Several labels can share a cell, such as `FW,LW`: 241,534 of 2,005,292 rows. `ENG_M_1st_keeper` has no Pos column. The other keeper files were not in the originals used here.

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_a.py <scripts>
### exact strings in the shot files, repr, rows
lastAction: 41 values, nulls 0
  'Pass' 178832, 'Cross' 70665, 'None' 59088, 'Aerial' 38676, 'Standard' 26627, 'TakeOn' 25240, 'Chipped' 24981, 'Rebound' 22377, 'BallRecovery' 12002, 'HeadPass' 11780, 'Throughball' 10153, 'BallTouch' 9339, 'LayOff' 4009, 'Dispossessed' 2714, 'Tackle' 1153, 'Foul' 919, 'CornerAwarded' 881, 'BlockedPass' 668, 'Interception' 491, 'Goal' 357, 'End' 346, 'Challenge' 228, 'Clearance' 211, 'OffsidePass' 142, 'Card' 127, 'Save' 101, 'GoodSkill' 85, 'SubstitutionOn' 79, 'OffsideProvoked' 27, 'KeeperPickup' 26, 'FormationChange' 23, 'Start' 16, 'Error' 14, 'Punch' 7, 'ShieldBallOpp' 6, 'ChanceMissed' 5, 'KeeperSweeper' 4, 'PenaltyFaced' 3, 'CrossNotClaimed' 2, 'SubstitutionOff' 1, 'Smother' 1
situation: 5 values, nulls 0
  'OpenPlay' 367276, 'FromCorner' 76256, 'SetPiece' 32247, 'DirectFreekick' 20357, 'Penalty' 6270
shotType: 4 values, nulls 0
  'RightFoot' 254429, 'LeftFoot' 159845, 'Head' 86060, 'OtherBodyPart' 2072
result: 6 values, nulls 0
  'MissedShots' 192120, 'BlockedShot' 128473, 'SavedShot' 116763, 'Goal' 53720, 'ShotOnPost' 9684, 'OwnGoal' 1646
situation by file identical label set: True
shotType by file identical label set: True
result by file identical label set: True
plan labels present: {'TakeOn': 25240, 'Throughball': 10153, 'Head': 86060, 'Penalty': 6270, 'OwnGoal': 1646}

### FBref Pos across the 30 stat files
files without Pos: ['ENG_M_1st_keeper_player_advanced_match_stats.parquet']
rows 2005292 | null 0 | multi-label rows 241534 | distinct values 994
atomic labels, rows: 'CB' 364669, 'FW' 320863, 'CM' 295094, 'DM' 139878, 'RB' 139395, 'AM' 138678, 'GK' 137632, 'LB' 136503, 'RM' 127208, 'LM' 126936, 'RW' 122268, 'LW' 122183, 'WB' 92770, 'MF' 157, 'DF' 96, '' 6
'Sub' as a Pos value: 0 | any label containing 'Sub' or 'sub': 0
most common values: 'CB' 339433, 'FW' 271380, 'CM' 221638, 'GK' 137591, 'RB' 112661, 'LB' 112599, 'DM' 94783, 'AM' 93897, 'RW' 80200, 'LW' 79456, 'LM' 76558, 'RM' 76224, 'WB' 67209, 'DM,CM' 14075, 'CM,DM' 11854, 'RM,CM' 5403, 'FW,AM' 5026, 'CM,RM' 5019, 'LM,CM' 5010, 'LW,RW' 4915, 'CM,LM' 4825, 'FW,LW' 4681, 'AM,FW' 4639, 'RW,RM' 4582, 'RM,LM' 4493
```

## 2. Season coverage

> Season coverage for all five leagues is reported for each stand-in file, with any gaps

**Met.** Counts are matches, by start year in the shot files and by end year in FBref files. HF counts are rows. Seasons outside the Pool are reported too.

| Source | Seasons | Gaps in Pool seasons (2017/18 to 2023/24) |
|---|---|---|
| Shot files | 2014/15 to 2025/26. 2025/26 stops at 2025-09-15. | None. |
| FBref stat files | 2017/18 to 2025/26. 2024/25 is partial (180 to 239 matches) and 2025/26 stops at 2025-09-15. | Many, per file, below. |
| Union of the five Pos files | Same | GER 2021/22 (305 of 306), ITA 2020/21 (379 of 380). Extra URLs: ITA 2022/23 (381), ITA 2023/24 (383). |
| Match events | 2017/18 to 2024/25. No 2025/26 rows. | Listed below. |
| HF | 2015-16 to 2024-25 | No season is missing. `master_player_stats.csv` also holds NED, which is out of scope. |

Outside the Pool, shot files lack single matches in Bundesliga 2014/15 and 2024/25 (305 of 306) and Ligue 1 2016/17 (379 of 380), and Serie A 2024/25 has 374 of 380.

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_a.py <scripts>
### shot files: matches and rows by season start year
bundesliga 2014:305 2015:306 2016:306 2017:306 2018:306 2019:306 2020:306 2021:306 2022:306 2023:306 2024:305 2025:27 | last date 2025-09-14 15:30:00
epl 2014:380 2015:380 2016:380 2017:380 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:380 2025:40 | last date 2025-09-14 15:30:00
la_liga 2014:380 2015:380 2016:380 2017:380 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:380 2025:41 | last date 2025-09-15 19:00:00
ligue_1 2014:380 2015:380 2016:379 2017:380 2018:380 2019:279 2020:380 2021:380 2022:380 2023:306 2024:306 2025:36 | last date 2025-09-14 18:45:00
serie_a 2014:380 2015:380 2016:380 2017:380 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:374 2025:30 | last date 2025-09-15 18:45:00

### FBref stat files and events: matches by Season_End_Year
ENG_M_1st_defense 2018:380 2019:378 2020:380 2021:380 2022:379 2023:380 2024:380 2025:239 2026:40 | dates 2017-08-11 2025-09-14
ENG_M_1st_keeper 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:380 2025:239 2026:40 | dates 2017-08-11 2025-09-14
ENG_M_1st_misc 2018:380 2019:380 2020:380 2021:380 2022:305 2023:373 2024:380 2025:239 2026:40 | dates 2017-08-11 2025-09-14
ENG_M_1st_passing 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:380 2025:239 2026:40 | dates 2017-08-11 2025-09-14
ENG_M_1st_passing_types 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:380 2025:239 2026:40 | dates 2017-08-11 2025-09-14
ENG_M_1st_possession 2018:380 2019:380 2020:310 2021:380 2022:380 2023:380 2024:380 2025:239 2026:40 | dates 2017-08-11 2025-09-14
ESP_M_1st_defense 2018:380 2019:378 2020:380 2021:380 2022:380 2023:379 2024:380 2025:220 2026:41 | dates 2017-08-18 2025-09-15
ESP_M_1st_match_summary 2018:380 2019:380 2020:380 2021:380 2022:380 2023:370 2024:381 2025:220 | dates 2017-08-18 2025-02-03
ESP_M_1st_misc 2018:380 2019:380 2020:378 2021:380 2022:380 2023:380 2024:380 2025:220 2026:41 | dates 2017-08-18 2025-09-15
ESP_M_1st_passing 2018:380 2019:380 2020:380 2021:239 2022:380 2023:380 2024:380 2025:220 2026:41 | dates 2017-08-18 2025-09-15
ESP_M_1st_passing_types 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:380 2025:220 2026:41 | dates 2017-08-18 2025-09-15
ESP_M_1st_possession 2018:380 2019:380 2020:10 2021:380 2022:380 2023:380 2024:380 2025:220 2026:41 | dates 2017-08-18 2025-09-15
FRA_M_1st_defense 2018:380 2019:380 2020:278 2021:377 2022:380 2023:370 2024:306 2025:180 2026:36 | dates 2017-08-04 2025-09-14
FRA_M_1st_match_summary 2018:380 2019:380 2020:279 2021:380 2022:380 2023:370 2024:307 2025:180 | dates 2017-08-04 2025-02-02
FRA_M_1st_misc 2018:380 2019:380 2020:279 2021:380 2022:380 2023:380 2024:306 2025:180 2026:36 | dates 2017-08-04 2025-09-14
FRA_M_1st_passing 2018:380 2019:380 2020:278 2021:377 2022:380 2023:370 2024:306 2025:180 2026:36 | dates 2017-08-04 2025-09-14
FRA_M_1st_passing_types 2018:380 2019:380 2020:278 2021:377 2022:380 2023:370 2024:306 2025:180 2026:36 | dates 2017-08-04 2025-09-14
FRA_M_1st_possession 2018:380 2019:380 2020:278 2021:377 2022:380 2023:370 2024:306 2025:180 2026:36 | dates 2017-08-04 2025-09-14
GER_M_1st_defense 2018:306 2019:306 2020:306 2021:306 2022:305 2023:306 2024:306 2025:180 2026:27 | dates 2017-08-18 2025-09-14
GER_M_1st_match_summary 2018:306 2019:306 2020:306 2021:304 2022:306 2023:306 2024:335 2025:180 | dates 2017-08-18 2025-02-02
GER_M_1st_misc 2018:306 2019:306 2020:306 2021:306 2022:305 2023:306 2024:300 2025:180 2026:27 | dates 2017-08-18 2025-09-14
GER_M_1st_passing 2018:306 2019:306 2020:306 2021:306 2022:305 2023:306 2024:306 2025:180 2026:27 | dates 2017-08-18 2025-09-14
GER_M_1st_passing_types 2018:306 2019:306 2020:306 2021:305 2022:299 2023:306 2024:306 2025:180 2026:27 | dates 2017-08-18 2025-09-14
GER_M_1st_possession 2018:306 2019:306 2020:306 2021:306 2022:305 2023:306 2024:306 2025:180 2026:27 | dates 2017-08-18 2025-09-14
ITA_M_1st_defense 2018:380 2019:380 2020:377 2021:376 2022:379 2023:381 2024:379 2025:228 2026:30 | dates 2017-08-19 2025-09-15
ITA_M_1st_match_summary 2018:380 2019:380 2020:312 2021:380 2022:380 2023:370 2024:384 2025:228 | dates 2017-08-19 2025-02-03
ITA_M_1st_misc 2018:380 2019:380 2020:379 2021:379 2022:380 2023:381 2024:74 2025:228 2026:30 | dates 2017-08-19 2025-09-15
ITA_M_1st_passing 2018:380 2019:380 2020:377 2021:376 2022:379 2023:370 2024:383 2025:228 2026:30 | dates 2017-08-19 2025-09-15
ITA_M_1st_passing_types 2018:380 2019:380 2020:377 2021:376 2022:379 2023:370 2024:383 2025:228 2026:30 | dates 2017-08-19 2025-09-15
ITA_M_1st_possession 2018:380 2019:380 2020:377 2021:376 2022:379 2023:370 2024:383 2025:228 2026:30 | dates 2017-08-19 2025-09-15
ENG_M_1st_match_summary.csv 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:389 2025:239 | dates 2017-08-11 2025-02-03

### HF understat_xg_data.csv rows by league and season; master_player_stats.csv same
season  2015-2016  2016-2017  2017-2018  2018-2019  2019-2020  2020-2021  2021-2022  2022-2023  2023-2024  2024-2025
lg                                                                                                                  
ENG           550        524        515        505        515        524        537        554        570        562
ESP           539        541        557        531        556        570        603        584        598        590
FRA           575        559        540        548        531        575        589        585        525        542
GER           476        470        472        468        487        496        511        506        494        481
ITA           551        560        533        543        572        594        608        577        590        599
season  2015-2016  2016-2017  2017-2018  2018-2019  2019-2020  2020-2021  2021-2022  2022-2023  2023-2024  2024-2025
league                                                                                                              
EPL           583        564        550        528        542        553        567        591        603        596
ESP           567        577        595        565        592        605        641        619        633        625
FRA           611        598        575        583        563        607        628        630        561        575
GER           511        494        503        492        517        525        543        535        527        511
ITA           607        605        575        591        624        643        657        627        640        659
NED           491        503        496        498        503        542        554        547        544        555
```

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_gaps.py <scripts>
expected: 380, GER 306, FRA 2019/20 279 (shortened), FRA 2023/24 on 306 (18 clubs). Pool seasons only.
shots ENG complete
shots ESP complete
shots FRA complete
shots GER complete
shots ITA complete
ENG_M_1st_defense [('2018/19', 378, 380), ('2021/22', 379, 380)]
ENG_M_1st_keeper complete
ENG_M_1st_misc [('2021/22', 305, 380), ('2022/23', 373, 380)]
ENG_M_1st_passing complete
ENG_M_1st_passing_types complete
ENG_M_1st_possession [('2019/20', 310, 380)]
ESP_M_1st_defense [('2018/19', 378, 380), ('2022/23', 379, 380)]
ESP_M_1st_match_summary [('2022/23', 370, 380), ('2023/24', 381, 380)]
ESP_M_1st_misc [('2019/20', 378, 380)]
ESP_M_1st_passing [('2020/21', 239, 380)]
ESP_M_1st_passing_types complete
ESP_M_1st_possession [('2019/20', 10, 380)]
FRA_M_1st_defense [('2019/20', 278, 279), ('2020/21', 377, 380), ('2022/23', 370, 380)]
FRA_M_1st_match_summary [('2022/23', 370, 380), ('2023/24', 307, 306)]
FRA_M_1st_misc complete
FRA_M_1st_passing [('2019/20', 278, 279), ('2020/21', 377, 380), ('2022/23', 370, 380)]
FRA_M_1st_passing_types [('2019/20', 278, 279), ('2020/21', 377, 380), ('2022/23', 370, 380)]
FRA_M_1st_possession [('2019/20', 278, 279), ('2020/21', 377, 380), ('2022/23', 370, 380)]
GER_M_1st_defense [('2021/22', 305, 306)]
GER_M_1st_match_summary [('2020/21', 304, 306), ('2023/24', 335, 306)]
GER_M_1st_misc [('2021/22', 305, 306), ('2023/24', 300, 306)]
GER_M_1st_passing [('2021/22', 305, 306)]
GER_M_1st_passing_types [('2020/21', 305, 306), ('2021/22', 299, 306)]
GER_M_1st_possession [('2021/22', 305, 306)]
ITA_M_1st_defense [('2019/20', 377, 380), ('2020/21', 376, 380), ('2021/22', 379, 380), ('2022/23', 381, 380), ('2023/24', 379, 380)]
ITA_M_1st_match_summary [('2019/20', 312, 380), ('2022/23', 370, 380), ('2023/24', 384, 380)]
ITA_M_1st_misc [('2019/20', 379, 380), ('2020/21', 379, 380), ('2022/23', 381, 380), ('2023/24', 74, 380)]
ITA_M_1st_passing [('2019/20', 377, 380), ('2020/21', 376, 380), ('2021/22', 379, 380), ('2022/23', 370, 380), ('2023/24', 383, 380)]
ITA_M_1st_passing_types [('2019/20', 377, 380), ('2020/21', 376, 380), ('2021/22', 379, 380), ('2022/23', 370, 380), ('2023/24', 383, 380)]
ITA_M_1st_possession [('2019/20', 377, 380), ('2020/21', 376, 380), ('2021/22', 379, 380), ('2022/23', 370, 380), ('2023/24', 383, 380)]
ENG_M_1st_match_summary.csv [('2023/24', 389, 380)]
union of the five Pos files:
  ENG 2017:380 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:239 2025:40 | Pool gaps none
  ESP 2017:380 2018:380 2019:380 2020:380 2021:380 2022:380 2023:380 2024:220 2025:41 | Pool gaps none
  FRA 2017:380 2018:380 2019:279 2020:380 2021:380 2022:380 2023:306 2024:180 2025:36 | Pool gaps none
  GER 2017:306 2018:306 2019:306 2020:306 2021:305 2022:306 2023:306 2024:180 2025:27 | Pool gaps [(2021, 305)]
  ITA 2017:380 2018:380 2019:380 2020:379 2021:380 2022:381 2023:383 2024:228 2025:30 | Pool gaps [(2020, 379), (2022, 381), (2023, 383)]

Pos rows with an empty label:
  ENG passing: 0 [] | Min [] | null Min rows: 1
  ESP passing: 0 [] | Min [] | null Min rows: 0
  FRA passing: 0 [] | Min [] | null Min rows: 3
  GER passing: 0 [] | Min [] | null Min rows: 0
  ITA passing: 0 [] | Min [] | null Min rows: 2

own goals in shots, Pool seasons, by league: {'ENG': 263, 'ESP': 195, 'FRA': 201, 'GER': 173, 'ITA': 217}

Pos cells with an empty label, every stat file:
  GER_M_1st_defense_player_advanced_ 6 ['', '', '', '', '', ''] [4.0, 12.0, 14.0, 11.0, 11.0, 21.0]
Min column type in the files: large_string | sample 90
```

## 3. Planned fields

> Every planned player-season, shot and position field is confirmed present in a named stand-in file, or reported missing

**Met.** None is missing.

| Planned field | Named file | Column | Nulls or note |
|---|---|---|---|
| time | `understat_xg_data.csv`, and FBref stat files | `minutes`; `Min` | 0 of 27,182; `Min` is text, with a few nulls per file |
| shots | Shot files; `understat_xg_data.csv` | Count rows; `shots` | Rule Q15 needs the rows, not the HF total |
| npg | Shot files | Count `result` `Goal` with `situation` not `Penalty` | Rebuilt |
| npxG | Shot files; `understat_xg_data.csv` | Sum `xG` without `Penalty`; `npxG` | 0 of 502,406; 0 of 27,182 |
| xA | `understat_xg_data.csv` | `xA` | 0 of 27,182 |
| key_passes | `understat_xg_data.csv` | `key_passes` | 0 of 27,182 |
| xGBuildup | `understat_xg_data.csv` | `xGBuildup` | 0 of 27,182. In HF only. |
| position | FBref stat files | `Pos` | 0 nulls in all files holding it. `ENG_M_1st_keeper` has no `Pos`. |
| Shot X and Y | Shot files | `X`, `Y` | 0 of 502,406 |
| lastAction, situation, shotType, result | Shot files | Same names | 0 of 502,406 |
| Per-match position | FBref stat files | `Pos`, by `MatchURL` | 0 nulls |
| Substitute appearance | Match event files | `Event_Type` `Substitute` | `ENG` is a CSV, the other four `.rds` |
| Display: goals, assists | `understat_xg_data.csv` | `goals`, `assists` | 0 of 27,182 |

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_a.py <scripts>
### fields
shot file columns: {'bundesliga': True, 'epl': True, 'la_liga': True, 'ligue_1': True, 'serie_a': True}
shots.X: nulls 0 of 502406
shots.Y: nulls 0 of 502406
shots.lastAction: nulls 0 of 502406
shots.situation: nulls 0 of 502406
shots.shotType: nulls 0 of 502406
shots.result: nulls 0 of 502406
shots.xG: nulls 0 of 502406
shots.player: nulls 0 of 502406
shots.player_id: nulls 0 of 502406
shots.player_assisted: nulls 132795 of 502406
shots.match_id: nulls 0 of 502406
shots.season: nulls 0 of 502406
shots.date: nulls 0 of 502406
shots.h_a: nulls 139625 of 502406
shots.home_away: nulls 362781 of 502406
shots.league: nulls 0 of 502406
understat_xg_data.csv.player_name: nulls 0 of 27182
understat_xg_data.csv.minutes: nulls 0 of 27182
understat_xg_data.csv.goals: nulls 0 of 27182
understat_xg_data.csv.assists: nulls 0 of 27182
understat_xg_data.csv.shots: nulls 0 of 27182
understat_xg_data.csv.key_passes: nulls 0 of 27182
understat_xg_data.csv.xG: nulls 0 of 27182
understat_xg_data.csv.xA: nulls 0 of 27182
understat_xg_data.csv.npxG: nulls 0 of 27182
understat_xg_data.csv.xGBuildup: nulls 0 of 27182
understat_xg_data.csv.apps: nulls 0 of 27182
understat_xg_data.csv.team: nulls 0 of 27182
master_player_stats.csv.player: nulls 0 of 34246
master_player_stats.csv.player_id: nulls 1290 of 34246
master_player_stats.csv.pos: nulls 5 of 34246
master_player_stats.csv.min: nulls 1291 of 34246
master_player_stats.csv.pk: nulls 1291 of 34246
master_player_stats.csv.pkatt: nulls 1291 of 34246
master_player_stats.csv.gls: nulls 1291 of 34246
master_player_stats.csv.squad: nulls 0 of 34246
ENG_M_1st_defense_player_advanced_match_ {'Pos': 0, 'Min': 1, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 83515
ENG_M_1st_keeper_player_advanced_match_s {'Pos': 'missing', 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 5938
ENG_M_1st_misc_player_advanced_match_sta {'Pos': 0, 'Min': 1, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 81328
ENG_M_1st_passing_player_advanced_match_ {'Pos': 0, 'Min': 1, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 83613
ENG_M_1st_passing_types_player_advanced_ {'Pos': 0, 'Min': 1, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 83613
ENG_M_1st_possession_player_advanced_mat {'Pos': 0, 'Min': 1, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 81667
ESP_M_1st_defense_player_advanced_match_ {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 87315
ESP_M_1st_misc_player_advanced_match_sta {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 87340
ESP_M_1st_passing_player_advanced_match_ {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 83106
ESP_M_1st_passing_types_player_advanced_ {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 87400
ESP_M_1st_possession_player_advanced_mat {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 76729
FRA_M_1st_defense_player_advanced_match_ {'Pos': 0, 'Min': 3, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 78973
FRA_M_1st_misc_player_advanced_match_sta {'Pos': 0, 'Min': 2, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 79421
FRA_M_1st_passing_player_advanced_match_ {'Pos': 0, 'Min': 3, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 78973
FRA_M_1st_passing_types_player_advanced_ {'Pos': 0, 'Min': 3, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 78973
FRA_M_1st_possession_player_advanced_mat {'Pos': 0, 'Min': 3, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 78973
GER_M_1st_defense_player_advanced_match_ {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 69868
GER_M_1st_misc_player_advanced_match_sta {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 69668
GER_M_1st_passing_player_advanced_match_ {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 69868
GER_M_1st_passing_types_player_advanced_ {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 69652
GER_M_1st_possession_player_advanced_mat {'Pos': 0, 'Min': 0, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 69868
ITA_M_1st_defense_player_advanced_match_ {'Pos': 0, 'Min': 2, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 87089
ITA_M_1st_misc_player_advanced_match_sta {'Pos': 0, 'Min': 1, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 77736
ITA_M_1st_passing_player_advanced_match_ {'Pos': 0, 'Min': 2, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 86868
ITA_M_1st_passing_types_player_advanced_ {'Pos': 0, 'Min': 2, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 86868
ITA_M_1st_possession_player_advanced_mat {'Pos': 0, 'Min': 2, 'Player': 0, 'Player_Href': 0, 'MatchURL': 0} rows 86868
xA/xGBuildup/key_passes/time/npxG in shot file? {'xA': False, 'xGBuildup': False, 'key_passes': False, 'time': False, 'npxG': False, 'npg': False, 'position': False}
```

## 4. Joins

> The joins between the three sources are stated, with match rates by league

**Met.** Rates are for Pool seasons, 2017/18 to 2023/24.

| Join | Key | All leagues | Lowest league |
|---|---|---|---|
| Shot files to HF `understat_xg_data.csv` | Unescaped name, league, season start | 99.96% of keys, 99.91% of shot rows | FRA 99.87% |
| Shot files to FBref | Same key, exact name | 82.27% of keys, 83.06% of shot rows | FRA 76.99% |
| Shot files to FBref | Name without accents or word order | 91.74% of keys, 92.66% of shot rows | ESP 85.40% |
| FBref at 900+ to shot files | Same | 85.95% | ESP 80.35% |
| Pool candidates to shot files | Same | 92.11% | ESP 85.35% |
| Pool candidates to HF `understat_xg_data.csv` | Same | 92.27% | ESP 85.35% |
| FBref at 900+ to HF `master_player_stats.csv` | FBref player id, league, season | 99.94% | ESP 99.83% |

Mapping used:

- **League:** from the file name in shot files (`epl` = ENG, `la_liga` = ESP, `bundesliga` = GER, `serie_a` = ITA, `ligue_1` = FRA). From the file prefix in FBref. HF `EPL` = ENG.
- **Season:** shot `season` 2017 = FBref `Season_End_Year` 2018 = HF `2017-2018`.
- **Name:** `html.unescape` first, because shot and HF names can hold `&#039;` and FBref names do not.
- **Player id:** FBref's 8-character id is in `Player_Href`. Shot files use a separate `player_id`, and `understat_xg_data.csv` has none.

"Pool candidates" means 900+ FBref minutes and attacking minutes above other minutes, with substitute appearances not removed. It approximates the Pool for this rate only.

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_join.py <scripts> <scripts>

A. Shot keys to HF understat_xg, exact unescaped name
league | keys | matched | rate | rows | rows matched | rate
ENG | 3114 | 3114 | 100.00% | 67553 | 67553 | 100.00%
ESP | 3302 | 3302 | 100.00% | 62845 | 62845 | 100.00%
FRA | 3181 | 3177 | 99.87% | 60920 | 60750 | 99.72%
GER | 2850 | 2847 | 99.89% | 56009 | 55881 | 99.77%
ITA | 3298 | 3298 | 100.00% | 70131 | 70131 | 100.00%
ALL | 15745 | 15738 | 99.96% | 317458 | 317160 | 99.91%

A2. Shot keys to HF understat_xg, folded name
league | keys | matched | rate | rows | rows matched | rate
ENG | 3114 | 3114 | 100.00% | 67553 | 67553 | 100.00%
ESP | 3302 | 3302 | 100.00% | 62845 | 62845 | 100.00%
FRA | 3181 | 3177 | 99.87% | 60920 | 60750 | 99.72%
GER | 2850 | 2847 | 99.89% | 56009 | 55881 | 99.77%
ITA | 3298 | 3298 | 100.00% | 70131 | 70131 | 100.00%
ALL | 15745 | 15738 | 99.96% | 317458 | 317160 | 99.91%

B. Shot keys to FBref, exact unescaped name
league | keys | matched | rate | rows | rows matched | rate
ENG | 3114 | 2788 | 89.53% | 67553 | 61175 | 90.56%
ESP | 3302 | 2549 | 77.20% | 62845 | 50820 | 80.87%
FRA | 3181 | 2449 | 76.99% | 60920 | 46273 | 75.96%
GER | 2850 | 2475 | 86.84% | 56009 | 49102 | 87.67%
ITA | 3298 | 2693 | 81.66% | 70131 | 56314 | 80.30%
ALL | 15745 | 12954 | 82.27% | 317458 | 263684 | 83.06%

B2. Shot keys to FBref, folded name
league | keys | matched | rate | rows | rows matched | rate
ENG | 3114 | 2976 | 95.57% | 67553 | 65190 | 96.50%
ESP | 3302 | 2820 | 85.40% | 62845 | 55012 | 87.54%
FRA | 3181 | 2869 | 90.19% | 60920 | 53881 | 88.45%
GER | 2850 | 2691 | 94.42% | 56009 | 53562 | 95.63%
ITA | 3298 | 3088 | 93.63% | 70131 | 66512 | 94.84%
ALL | 15745 | 14444 | 91.74% | 317458 | 294157 | 92.66%

C. FBref keys at 900+ to shot keys, folded name
league | keys | matched | rate
ENG | 2331 | 2094 | 89.83%
ESP | 2402 | 1930 | 80.35%
FRA | 2243 | 1881 | 83.86%
GER | 2005 | 1783 | 88.93%
ITA | 2362 | 2061 | 87.26%
ALL | 11343 | 9749 | 85.95%

D. Pool candidates (900+, attacking > other, subs not removed) to shot keys, exact
league | keys | matched | rate
ENG | 664 | 611 | 92.02%
ESP | 594 | 474 | 79.80%
FRA | 650 | 485 | 74.62%
GER | 603 | 528 | 87.56%
ITA | 632 | 522 | 82.59%
ALL | 3143 | 2620 | 83.36%

D2. Pool candidates to shot keys, folded
league | keys | matched | rate
ENG | 664 | 647 | 97.44%
ESP | 594 | 507 | 85.35%
FRA | 650 | 569 | 87.54%
GER | 603 | 572 | 94.86%
ITA | 632 | 600 | 94.94%
ALL | 3143 | 2895 | 92.11%

E. Pool candidates to HF understat_xg, folded
league | keys | matched | rate
ENG | 664 | 647 | 97.44%
ESP | 594 | 507 | 85.35%
FRA | 650 | 573 | 88.15%
GER | 603 | 573 | 95.02%
ITA | 632 | 600 | 94.94%
ALL | 3143 | 2900 | 92.27%

href without an 8-hex id: 0

F. FBref keys at 900+ to HF master_player_stats, by FBref player id
league | keys | matched | rate | identical minutes among matched
ENG | 2328 | 2328 | 100.00% | 98.45%
ESP | 2401 | 2397 | 99.83% | 99.46%
FRA | 2240 | 2239 | 99.96% | 99.29%
GER | 2002 | 2000 | 99.90% | 92.15%
ITA | 2360 | 2360 | 100.00% | 83.64%
ALL | 11331 | 11324 | 99.94% | 94.63%

ambiguity
shot keys (name, league, season) with several player_id: 24 rows 1122
FBref keys (name, league, season) with several Player_Href: 38
HF understat_xg keys with several rows: 39
matched folded keys that hit several exact FBref names: 6
names holding an HTML entity: shot rows 1127 | HF rows 96 | FBref rows 0
```

## 5. Box boundaries

> Box boundaries are calibrated from real shot data and checked on a heatmap, for both X and Y

**Met.** Proposed constants, for Ahmed to adopt. They are recorded only in this report.

| Constant | Proposed | Plan's estimate | Evidence |
|---|---:|---:|---|
| `BOX_X_MIN` | 0.8275 | 0.8275 | Penalty-spot scale gives 0.8275. Central free kicks: 0 from X = 0.829 to 0.834, and 25 of 11,412 at X ≥ 0.8275. Density dip 0.8305 (range 0.8285 to 0.8325). |
| `BOX_Y_MIN` | 0.2075 | None | Free kicks at X > 0.86 stop at Y = 0.207. Density dip 0.2105 (0.2065 to 0.2155). |
| `BOX_Y_MAX` | 0.7925 | None | Free kicks at X > 0.86 start again at Y = 0.793. Density dip 0.7915 (0.7895 to 0.7935). |
| `SIX_X_MIN` | 0.9425 | 0.9425 | Penalty-spot scale gives 0.9425. Density dip 0.9415 (0.9395 to 0.9435). |
| `SIX_Y_MIN` | 0.365 | None | Density dip 0.3655 (0.3635 to 0.3675). A 68 m width gives 0.3653. |
| `SIX_Y_MAX` | 0.635 | None | Density dip 0.6345 (0.6325 to 0.6365). A 68 m width gives 0.6347. |

A shot is inside a box when X is at or above the X line and Y is between the two Y lines, both inclusive.

How the lines were found:

1. **Penalty spot:** all 6,270 penalties sit at exactly X = 0.885, Y = 0.5. The spot is 11 m from goal, so one X unit is 95.65 m, which gives the X lines from the 16.5 m and 5.5 m distances.
2. **Direct free kicks:** the laws do not allow them inside the box, so they mark its edge from outside. This is independent of the penalty scale, and it tests X and both Y lines. It cannot test the six-yard box.
3. **Density dips:** shot density falls in a narrow band at each line. Each value is the emptiest 0.005 bin in a window around the line, averaged over bin offsets.

Checks:

- **Stability:** the box X dip is 0.8305 in all 5 leagues and 10 of 11 seasons. The other lines move by up to about 0.02 across leagues and seasons, as listed below. Season 2025 has too few rows and was skipped.
- **Y lines vs a 68 m pitch:** a 68 m width would give box lines of 0.2035 and 0.7965. Free kicks reject those: 58 fall inside, against 43 with the proposed lines. So the Y scale is not exactly 68 m.
- **Six-yard Y lines at the free-kick scale:** the box half-width of 0.2925 times 18.32 / 40.32 gives 0.3671 and 0.6329. That is within about 0.002 of the proposed lines and close to the range of the dips, so the two pieces of evidence roughly agree.
- **Headers:** 99.66% of 85,773 headers fall inside the proposed box.
- **Range:** 0 X or Y values fall outside 0 to 1.

Coordinates are stored to 3 decimals. Lines such as 0.8275 fall between stored values, while 0.365 and 0.635 can equal one, which is why the Y test is inclusive.

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_box.py <scripts>
penalties 6270 X {0.885: 6270} Y {0.5: 6270}
X decimals: share of rows on a 0.001 grid 1.0
scale from the spot: 11 m = 1 - 0.885 => metres per unit 95.65
laws-of-the-game lines at that scale: box X 0.8275 six-yard X 0.9425
Y lines if width is 68 m: box 0.2035 0.7965 six-yard 0.3653 0.6347
non-penalty, non-own-goal shots 494490 | direct free kicks 20357

-- free kicks, central |Y-0.5|<0.15, by X
X 0.800:123 0.802:94 0.805:173 0.807:101 0.810:182 0.812:91 0.815:193 0.818:78 0.820:99 0.823:19 0.825:24 0.828:2 0.830:0 0.833:0 0.835:0 0.838:0 0.840:2 0.843:1 0.845:2 0.848:0 0.850:0 0.853:0 0.855:0 0.858:0
share of central free kicks with X >= t: {0.82: 167, 0.8225: 68, 0.825: 49, 0.8275: 25, 0.83: 23, 0.8325: 23, 0.835: 23} of 11412

-- free kicks, X>0.86, by Y
Y low 0.180:21 0.182:26 0.185:16 0.188:17 0.190:13 0.193:13 0.195:15 0.198:4 0.200:9 0.203:3 0.205:2 0.207:0 0.210:0 0.212:0 0.215:0 0.217:0 0.220:0 0.223:0 0.225:0 0.228:0 0.230:0 0.233:0 0.235:0 0.237:0
Y high 0.760:0 0.762:0 0.765:0 0.767:0 0.770:0 0.772:0 0.775:0 0.777:0 0.780:1 0.782:0 0.785:0 0.787:0 0.790:0 0.792:5 0.795:5 0.797:7 0.800:22 0.802:12 0.805:19 0.807:30 0.810:28 0.812:12 0.815:36 0.818:33

-- all shots, density dips
X near box 0.810:5668 0.812:2499 0.815:5340 0.818:3604 0.820:3814 0.823:1806 0.825:2248 0.828:1244 0.830:1312 0.833:950 0.835:2318 0.838:1865 0.840:3743 0.843:3015 0.845:5272 0.848:4554 0.850:6418 0.853:4571 0.855:7665 0.858:8306
X near six 0.925:7069 0.927:3173 0.930:5174 0.932:2405 0.935:3919 0.938:1433 0.940:1739 0.943:1418 0.945:2228 0.948:1987 0.950:3800 0.953:2794 0.955:4044 0.958:3025
Y low box 0.180:62 0.182:42 0.185:45 0.188:48 0.190:63 0.193:37 0.195:45 0.198:22 0.200:36 0.203:23 0.205:18 0.207:11 0.210:17 0.212:12 0.215:25 0.217:27 0.220:29 0.223:29 0.225:60 0.228:50 0.230:108 0.233:115 0.235:176 0.237:186
Y high box 0.760:224 0.762:155 0.765:165 0.767:93 0.770:106 0.772:48 0.775:75 0.777:41 0.780:39 0.782:19 0.785:39 0.787:17 0.790:12 0.792:16 0.795:36 0.797:25 0.800:70 0.802:57 0.805:63 0.807:54 0.810:79 0.812:36 0.815:69 0.818:77
Y low six 0.340:307 0.343:124 0.345:263 0.347:194 0.350:227 0.352:134 0.355:235 0.357:128 0.360:137 0.362:113 0.365:145 0.367:67 0.370:111 0.372:113 0.375:190 0.378:79 0.380:253 0.383:155 0.385:268 0.388:226 0.390:350 0.393:180 0.395:338 0.398:370
Y high six 0.600:425 0.603:200 0.605:329 0.608:268 0.610:372 0.613:168 0.615:246 0.618:130 0.620:203 0.623:151 0.625:173 0.627:74 0.630:97 0.632:88 0.635:146 0.637:117 0.640:193 0.642:125 0.645:273 0.647:195 0.650:249 0.652:171 0.655:247 0.657:317

-- density-dip centre (mean, lowest, highest across bin offsets)
BOX_X_MIN (0.8305, 0.8285, 0.8325)
SIX_X_MIN (0.9415, 0.9395, 0.9435)
BOX_Y_MIN (0.2105, 0.2065, 0.2155)
BOX_Y_MAX (0.7915, 0.7895, 0.7935)
SIX_Y_MIN (0.3655, 0.3635, 0.3675)
SIX_Y_MAX (0.6345, 0.6325, 0.6365)

-- stability: density-dip centre by league
bundesliga box X 0.8305 six X 0.9415 box Y 0.2105 0.7895 six Y 0.3755 0.6325
epl box X 0.8305 six X 0.9415 box Y 0.1995 0.7915 six Y 0.3695 0.6345
la_liga box X 0.8305 six X 0.9415 box Y 0.2135 0.7895 six Y 0.3655 0.6345
ligue_1 box X 0.8305 six X 0.9415 box Y 0.2085 0.7895 six Y 0.3655 0.6335
serie_a box X 0.8305 six X 0.9415 box Y 0.2065 0.7925 six Y 0.3685 0.6295
-- stability by season
2014 box X 0.8305 six X 0.9445 box Y 0.2085 0.7925 six Y 0.3735 0.6305
2015 box X 0.8305 six X 0.9425 box Y 0.2165 0.7895 six Y 0.3705 0.6335
2016 box X 0.8305 six X 0.9425 box Y 0.2125 0.7905 six Y 0.3755 0.6345
2017 box X 0.8305 six X 0.9425 box Y 0.2025 0.7915 six Y 0.3645 0.6345
2018 box X 0.8305 six X 0.9425 box Y 0.2015 0.7905 six Y 0.3725 0.6325
2019 box X 0.8325 six X 0.9415 box Y 0.2075 0.7865 six Y 0.3705 0.6345
2020 box X 0.8305 six X 0.9405 box Y 0.2095 0.7955 six Y 0.3675 0.6305
2021 box X 0.8305 six X 0.9415 box Y 0.1975 0.7855 six Y 0.3655 0.6345
2022 box X 0.8305 six X 0.9405 box Y 0.2165 0.7905 six Y 0.3645 0.6325
2023 box X 0.8305 six X 0.9405 box Y 0.2095 0.7875 six Y 0.3655 0.6355
2024 box X 0.8305 six X 0.9405 box Y 0.2055 0.7865 six Y 0.3655 0.6295
2025 rows 4206 too few, skipped
```

Heatmaps, with the proposed lines. The free-kick map shows the check clearly: the rectangle inside the lines is almost empty, with a sharp edge along each line.

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_box2.py <scripts>
free kicks, central, each 0.001 of X: 0.820:38 0.821:32 0.822:29 0.823:14 0.824:5 0.825:13 0.826:7 0.827:4 0.828:2 0.829:0 0.830:0 0.831:0 0.832:0 0.833:0 0.834:0
free kicks, X>0.86, each 0.001 of Y, low: 0.198:3 0.199:1 0.200:4 0.201:3 0.202:2 0.203:2 0.204:1 0.205:0 0.206:0 0.207:2 0.208:0 0.209:0 0.210:0 0.211:0 0.212:0 0.213:0 0.214:0 0.215:0 0.216:0
free kicks, X>0.86, each 0.001 of Y, high: 0.784:0 0.785:0 0.786:0 0.787:0 0.788:0 0.789:0 0.790:0 0.791:0 0.792:0 0.793:2 0.794:3 0.795:0 0.796:4 0.797:1 0.798:0 0.799:7 0.800:9 0.801:2 0.802:11
direct free kicks inside the proposed box: 43 of 20357 = 0.211%
direct free kicks inside X-only starting estimate (X >= 0.8275): 1342 = 6.592%
direct free kicks inside with 68 m Y lines (0.2035, 0.7965): 58
non-penalty, non-own-goal shots 494490 | inside box 305234 = 61.73% | outside box 189256 = 38.27% | six-yard 36483 = 7.38%
X-only starting estimate would give: outside 186848 = 37.79% | six-yard 47633 = 9.63%
shots reclassified by adding Y lines: box 2408 | six-yard 11150
headers inside box 99.66% of 85773
X and Y out of range: 0

All non-penalty, non-own-goal shots. Rows are Y, columns are X in 0.01 steps from 0.78. Digit = shots on a log scale, 0-9, '.' = none. Peak cell 2571. '|' and '-' mark the proposed lines: the box and the six-yard box.
         8 9 0 1|2 3 4 5 6 7 8 9 0 1 2 3|4 5 6 7 8 9
0.14     2 3 2 1|2 2 2 2 3 3 3 3 3 2 0 2|1 0 0 1 0 .
0.16     3 3 3 3|2 2 3 4 3 3 3 3 3 3 2 2|2 2 2 1 1 .
0.18     4 4 4 4|3 4 4 4 5 4 4 4 4 3 3 2|3 2 1 0 . .
box 0.2075 --------------------------------------------
0.20     5 5 4 4|4 2 3 4 3 3 3 3 3 2 2 2|1 2 1 0 . .
0.22     6 5 6 5|4 4 5 5 5 5 5 5 5 4 4 4|3 3 3 0 0 0
0.24     7 7 7 6|5 5 6 7 7 7 6 6 6 6 6 5|5 4 4 3 2 0
0.26     7 7 7 7|6 6 7 7 7 7 7 7 7 7 6 6|6 5 5 4 3 1
0.28     8 8 7 7|7 6 7 8 8 8 8 8 7 7 7 7|6 6 6 5 4 1
0.30     8 8 8 7|7 6 8 8 8 8 8 8 8 8 8 7|7 7 6 6 5 2
0.32     8 8 8 7|7 7 8 8 8 8 8 8 8 8 8 8|7 7 7 6 5 3
0.34     8 8 8 7|7 7 8 8 8 8 8 8 8 8 8 7|7 8 7 6 5 2
six 0.3650 --------------------------------------------
0.36     8 8 8 7|7 7 8 8 8 8 8 8 8 8 8 7|7 7 7 6 5 3
0.38     8 8 8 7|7 6 7 8 8 8 8 8 8 8 8 7|7 8 8 7 6 3
0.40     8 8 7 7|6 6 8 8 8 8 8 9 9 9 8 8|7 8 8 7 6 4
0.42     8 7 7 7|7 7 8 8 8 9 9 9 9 9 9 8|8 8 8 7 6 4
0.44     8 7 8 8|7 7 8 9 9 9 9 9 9 9 9 9|8 8 8 7 6 3
0.46     8 7 8 9|8 7 8 9 9 9 9 9 9 9 9 9|8 9 8 7 7 5
0.48     7 7 8 9|8 7 8 9 9 8 8 9 9 9 9 9|8 9 8 7 6 4
0.50     7 7 9 9|8 7 8 9 9 8 8 9 9 9 9 9|8 9 8 7 6 4
0.52     7 7 8 9|8 7 8 9 9 9 9 9 9 9 9 9|8 9 8 8 7 5
0.54     8 7 7 8|8 7 8 9 9 9 9 9 9 9 9 9|8 8 8 7 6 3
0.56     8 8 7 8|7 7 8 8 9 9 9 9 9 9 9 8|8 8 8 7 6 3
0.58     8 7 7 7|6 6 7 8 8 8 8 9 9 9 8 8|7 8 8 7 6 4
0.60     8 8 8 7|6 6 8 8 8 8 8 8 8 8 8 7|7 8 8 7 6 4
six 0.6350 --------------------------------------------
0.62     8 8 8 8|7 7 8 8 8 8 8 8 8 8 8 7|7 7 7 6 5 3
0.64     8 8 8 8|7 7 8 8 8 8 8 8 8 8 8 7|7 7 7 6 5 3
0.66     8 8 8 8|7 7 8 8 8 8 8 8 8 8 8 8|8 8 7 6 5 2
0.68     8 8 8 8|7 7 8 8 8 8 8 8 8 8 8 8|7 7 7 6 4 2
0.70     8 8 8 7|7 6 7 8 8 8 8 8 8 7 7 7|7 6 6 5 3 1
0.72     7 7 7 7|6 6 7 8 7 8 7 7 7 7 7 6|5 5 4 4 2 1
0.74     7 7 7 7|6 6 7 7 7 7 6 6 6 6 5 5|4 4 3 3 1 0
0.76     6 6 6 6|4 4 5 6 5 6 5 5 5 4 4 3|3 3 3 2 0 .
box 0.7925 --------------------------------------------
0.78     5 5 5 4|3 3 4 4 4 3 3 3 3 2 2 1|1 0 . . . .
0.80     5 4 4 4|4 4 5 5 5 4 4 4 4 4 4 2|3 2 2 2 0 .
0.82     4 4 4 4|4 4 4 4 4 4 4 4 4 3 3 3|3 2 2 2 0 .
0.84     3 3 2 3|3 3 3 4 3 4 3 3 2 2 3 1|2 1 2 0 . .

Direct free kicks only: these cannot legally start inside the box. Rows are Y, columns are X in 0.01 steps from 0.78. Digit = shots on a log scale, 0-9, '.' = none. Peak cell 83. '|' and '-' mark the proposed lines: the box and the six-yard box.
         8 9 0 1|2 3 4 5 6 7 8 9 0 1 2 3|4 5 6 7 8 9
0.14     0 3 3 1|1 2 4 3 4 4 4 5 5 3 0 0|2 . 0 2 . .
0.16     3 4 4 4|3 4 4 6 4 5 5 4 5 4 4 3|4 3 1 0 1 .
0.18     4 4 5 5|4 4 6 6 6 6 5 6 6 5 4 3|4 4 1 . . .
box 0.2075 --------------------------------------------
0.20     5 4 5 4|4 0 . 1 1 0 1 0 . 1 0 1|. 2 . . . .
0.22     6 6 6 6|1 . . . . . . . . . . .|. . . . . .
0.24     8 8 7 6|1 . . . 0 . . . . . . .|. . . . . .
0.26     8 9 8 6|4 . . . . . . . . . . .|. . . . . .
0.28     9 9 7 7|4 0 . . . . . 0 . . . .|. . . . . .
0.30     9 8 9 7|4 . 0 0 . . . . . . . .|. . . . . .
0.32     9 8 8 7|1 1 . 0 . . . . . . . .|. . . . . .
0.34     9 9 8 7|5 . . . . . . . . 0 . .|. . . . . .
six 0.3650 --------------------------------------------
0.36     9 8 8 7|4 . . . . 0 . 1 . . . .|. . . . . .
0.38     8 7 8 6|3 . . . . . 0 . . . . .|. . . . . .
0.40     8 8 6 5|3 . 1 . . . . . . . . .|. . . . . .
0.42     8 7 6 6|4 . 0 . . . . . . . . .|. . . . . .
0.44     7 6 6 8|5 . . . . . . . . . . 0|. . . . . .
0.46     7 5 7 9|5 . 1 . . . . . . . 0 .|. . . . . .
0.48     8 6 8 9|6 . . . . . . . 0 . . .|. . 0 . . .
0.50     6 6 8 9|5 . . . . . . . . . . .|. . . . . .
0.52     7 6 7 9|4 . . . . . . . 0 . 0 .|. . . . . .
0.54     8 7 6 8|6 . . . 0 . . . . . . .|. . . . . .
0.56     8 8 6 5|6 . . . 0 . . . . . . .|. . 0 . . .
0.58     7 7 7 6|2 . . . . . . . . . . .|. . . . . .
0.60     8 8 8 7|4 . . . 1 . . . . . . .|. . . . . .
six 0.6350 --------------------------------------------
0.62     9 8 9 8|4 . . . . 0 . . . . . .|. . 0 . . .
0.64     9 9 8 7|4 . . . . . . . . . . .|0 . . . . .
0.66     9 9 9 7|4 . . . . . . . . . . .|. 0 . . . .
0.68     9 9 9 8|5 . . 0 . . . . . . . .|. . . . . .
0.70     9 9 8 7|4 0 . . . . . . . . . .|. . . . . .
0.72     8 8 9 8|5 . . 0 0 . . . . . . .|. . . . . .
0.74     8 8 8 7|4 . 0 . . . . . . . 0 .|. . . . . .
0.76     8 7 6 6|1 . . . . . . . . . . .|. . . . . .
box 0.7925 --------------------------------------------
0.78     6 7 6 4|4 2 . 2 2 4 1 0 2 0 . 1|. . . . . .
0.80     5 5 5 5|5 4 6 7 7 6 6 7 6 7 6 3|4 4 2 3 0 .
0.82     5 5 5 5|5 5 6 6 6 7 6 7 6 6 5 4|5 4 3 3 . .
0.84     3 3 3 3|3 5 4 6 6 6 5 6 4 3 4 0|3 1 2 0 . .
```

## 6. Real samples

> Small real samples are cut from the stand-in files for: a mid-season league move, `Sub` appearances, an own goal, a player under 900 minutes and a current-season player. Real rows, never invented

**Met.** `tests/fixtures/standin/` holds 22 Parquet files and `README.md`, which traces each one to its source file, SHA-256 and row filter. `scripts/cut_fixtures.py` writes them all. The largest is 40,536 bytes.

| Case | Example chosen | Rule used to choose |
|---|---|---|
| Mid-season league move | Lucas Moura, 2017/18, Ligue 1 then Premier League | Same FBref id in two leagues, in shots and HF for both, no date overlap, attacker in both stints, fewest shots |
| Substitute appearance | Almería v Rayo Vallecano, 2023-08-11: 10 substitutes | Earliest ESP 2023/24 match with exactly 11 non-substitutes per team |
| Own goal | Víctor Camarasa, 2017-08-25 | Earliest La Liga own goal in both the shot and event files |
| Under 900 minutes | Lukas Nmecha, Bundesliga 2022/23, 899 minutes | Attacker closest to the line, under 900 in FBref and HF |
| Multi-position row | Ben Brereton, 2023/24: one `FW,LW` row | 900+ minutes, a `FW,LW` row and a non-attacking row, fewest rows |
| LM/RM only | Robbie Brady, 2020/21 | 900+ minutes, every label LM or RM, fewest rows |
| HTML-entity name | `Dara O&#039;Shea`, 2020/21 | Entity in shot file and HF, in FBref too, fewest shots |
| Name shared by two players | Nacho, La Liga 2019/20 | Two ids in shot file and FBref, fewest shots |
| Current-season player | Cameron Puertas, 2025/26 | Attacker in shots and FBref, fewest shots |

The search, with candidate counts:

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_fix.py <scripts>
### league move: same FBref id in two leagues in one Pool season, same name in shots and HF for both, stints do not overlap in the shot dates
FBref id-seasons in two leagues: 390
and attacking minutes > other minutes in both stints: 43
with both stints in shots and HF, 3+ shots each, no overlap, full passing file: 43
chosen (fewest shots):
     lg  start       Player                       Player_Href  rows  mins  shots                first                 last  hf  hfmin    att  oth
6   ENG   2017  Lucas Moura  /en/players/2b622f01/Lucas-Moura     6   210      5  2018-04-14 18:45:00  2018-05-13 15:00:00   1    208  210.0  0.0
90  FRA   2017  Lucas Moura  /en/players/2b622f01/Lucas-Moura     5    76      3  2017-09-08 19:45:00  2017-10-27 19:45:00   1     69   76.0  0.0

### substitute: ESP 2023/24 match, 11 non-subs per team, sub in event rows, name in passing
Event_Type values: {'Substitute': 22661, 'Yellow Card': 13956, 'Goal': 6419, 'Penalty': 951, 'Red Card': 364, 'Second Yellow Card': 313, 'Own Goal': 209}
candidate matches: 319
chosen (earliest): ('2023-08-11', 'https://fbref.com/en/matches/30d3212e/Almeria-Rayo-Vallecano-August-11-2023-La-Liga', 10, 32)

### own goal: La Liga Pool season shot row result OwnGoal, same date and name in ESP events
shot own goals (La Liga, Pool seasons): 195 | event own goals (ESP): 209
matched on date and name: 143
chosen (earliest): 2017-08-25 Víctor Camarasa match_id 7890 https://fbref.com/en/matches/0d3827c8/Real-Betis-Celta-Vigo-August-25-2017-La-Liga | shot rows in match 20 | event rows 13
own goals in shots and events match on team side? Celta Vigo

### under 900: Pool season attacker with FBref minutes under 900 and HF under 900, closest to the line, 3+ shots
candidates: 988
       lg  start        Player                        Player_Href    Min  hfmin  shots  rows
1356  GER   2022  Lukas Nmecha  /en/players/0cc5f4a5/Lukas-Nmecha  899.0    893     22    16

### multi-position: player-season at 900+ with an exact 'FW,LW' row and a non-attacking row, fewest rows
rows with exact Pos 'FW,LW' in passing files: 865
candidates: 226
       lg  start        Player                        Player_Href   n  mins  fwlw  other
3208  ENG   2023  Ben Brereton  /en/players/57827369/Ben-Brereton  14  1105     1      2

### LM/RM only: player-season at 900+, every label LM or RM
candidates: 5
       lg  start        Player                        Player_Href   n  mins  only
1961  ENG   2020  Robbie Brady  /en/players/96bb8cc2/Robbie-Brady  19  1052  True

### HTML entity: shot name holds an entity, HF name too, unescaped name in FBref
shot name-seasons: 80 | distinct raw names: 33 | entities: ['&#039;']
in all three: 27
    lg  start            player       player_name       Player  size  rows
4  ENG   2020  Dara O&#039;Shea  Dara O&#039;Shea  Dara O'Shea     3    28

### shared name: one name, two ids, same league-season, in shot file and FBref
shot name-seasons with two ids: 24 | FBref name-seasons with two ids: 24
in both: 6
    lg  start      name  ids  shots  hrefs  frows  hf  hfmin
4  ESP   2019     Nacho    2     15      2     29   2   2326
2  ESP   2018     Nacho    2     22      2     55   2   4854
0  ESP   2017  Juanfran    2     27      2     52   2   4371

### current-season: 2025/26 attacker, in shots and FBref, exact name
HF rows for 2025-2026: 0 | candidates: 244
      lg             name  shots  ids                 last           Player                           Player_Href  n  mins  atts
688  GER  Cameron Puertas      3    1  2025-09-14 15:30:00  Cameron Puertas  /en/players/185a2732/Cameron-Puertas  1    82     1
max FBref minutes in 2025/26: 450 | FBref matches: 174 | dates 2025-08-15 2025-09-15
```

The cut, run with the network blocked:

```
$ sandbox-exec -f cut.sb venv/bin/python3 -I -B scripts/cut_fixtures.py release_assets
league_move__epl_shot_data.parquet	5	13104
league_move__ligue_1_shot_data.parquet	3	12998
league_move__ENG_M_1st_passing_player_advanced_match_stats.parquet	6	33400
league_move__FRA_M_1st_passing_player_advanced_match_stats.parquet	5	40536
league_move__understat_xg_data.parquet	2	10731
substitute__ESP_M_1st_match_summary.parquet	16	20673
substitute__ESP_M_1st_passing_player_advanced_match_stats.parquet	32	34664
own_goal__la_liga_shot_data.parquet	20	14001
own_goal__ESP_M_1st_match_summary.parquet	13	20744
under_900__GER_M_1st_passing_player_advanced_match_stats.parquet	16	34727
under_900__bundesliga_shot_data.parquet	22	14193
under_900__understat_xg_data.parquet	1	10581
multi_position__ENG_M_1st_passing_player_advanced_match_stats.parquet	14	35078
lm_rm_only__ENG_M_1st_passing_player_advanced_match_stats.parquet	19	35206
html_entity__epl_shot_data.parquet	3	13127
html_entity__understat_xg_data.parquet	1	10656
html_entity__ENG_M_1st_passing_player_advanced_match_stats.parquet	28	37491
shared_name__la_liga_shot_data.parquet	15	13800
shared_name__ESP_M_1st_passing_player_advanced_match_stats.parquet	29	36554
shared_name__understat_xg_data.parquet	2	10687
current_season__bundesliga_shot_data.parquet	3	12982
current_season__GER_M_1st_passing_player_advanced_match_stats.parquet	1	31636
```

An outside check that uses none of the cut script's code. It parses the README, reads each source with a different reader (`pyreadr` in the sandbox, the `csv` module for HF), and compares every cell. It then tests what each fixture claims to show.

```
$ cd ~/sandbox/parquet-vet; venv/bin/python3 -I -B t3_verify.py tests/fixtures/standin release_assets
README fixture rows: 22 | parquet files: 22
league_move__epl_shot_data.parquet: source rows 5 fixture rows 5 README 5 cell diffs 0 OK
league_move__ligue_1_shot_data.parquet: source rows 3 fixture rows 3 README 3 cell diffs 0 OK
league_move__ENG_M_1st_passing_player_advanced_match_stats.parquet: source rows 6 fixture rows 6 README 6 cell diffs 0 OK
league_move__FRA_M_1st_passing_player_advanced_match_stats.parquet: source rows 5 fixture rows 5 README 5 cell diffs 0 OK
league_move__understat_xg_data.parquet: source rows 2 fixture rows 2 README 2 cell diffs 0 OK
substitute__ESP_M_1st_match_summary.parquet: source rows 16 fixture rows 16 README 16 cell diffs 0 OK
substitute__ESP_M_1st_passing_player_advanced_match_stats.parquet: source rows 32 fixture rows 32 README 32 cell diffs 0 OK
own_goal__la_liga_shot_data.parquet: source rows 20 fixture rows 20 README 20 cell diffs 0 OK
own_goal__ESP_M_1st_match_summary.parquet: source rows 13 fixture rows 13 README 13 cell diffs 0 OK
under_900__GER_M_1st_passing_player_advanced_match_stats.parquet: source rows 16 fixture rows 16 README 16 cell diffs 0 OK
under_900__bundesliga_shot_data.parquet: source rows 22 fixture rows 22 README 22 cell diffs 0 OK
under_900__understat_xg_data.parquet: source rows 1 fixture rows 1 README 1 cell diffs 0 OK
multi_position__ENG_M_1st_passing_player_advanced_match_stats.parquet: source rows 14 fixture rows 14 README 14 cell diffs 0 OK
lm_rm_only__ENG_M_1st_passing_player_advanced_match_stats.parquet: source rows 19 fixture rows 19 README 19 cell diffs 0 OK
html_entity__epl_shot_data.parquet: source rows 3 fixture rows 3 README 3 cell diffs 0 OK
html_entity__understat_xg_data.parquet: source rows 1 fixture rows 1 README 1 cell diffs 0 OK
html_entity__ENG_M_1st_passing_player_advanced_match_stats.parquet: source rows 28 fixture rows 28 README 28 cell diffs 0 OK
shared_name__la_liga_shot_data.parquet: source rows 15 fixture rows 15 README 15 cell diffs 0 OK
shared_name__ESP_M_1st_passing_player_advanced_match_stats.parquet: source rows 29 fixture rows 29 README 29 cell diffs 0 OK
shared_name__understat_xg_data.parquet: source rows 2 fixture rows 2 README 2 cell diffs 0 OK
current_season__bundesliga_shot_data.parquet: source rows 3 fixture rows 3 README 3 cell diffs 0 OK
current_season__GER_M_1st_passing_player_advanced_match_stats.parquet: source rows 1 fixture rows 1 README 1 cell diffs 0 OK
fixtures failing: 0 | cells compared: 10957

claims
league_move: same player_id True | Ligue 1 last 2017-10-27 19:45:00 before EPL first 2018-04-14 18:45:00 True
  HF [{'league': 'EPL', 'team': 'Tottenham', 'minutes': 208, 'shots': 5}, {'league': 'FRA', 'team': 'Paris Saint Germain', 'minutes': 69, 'shots': 3}]
  ENG FBref minutes 210 labels ['AM', 'LW', 'LW,RW', 'RW,AM', 'RW,DM']
  FRA FBref minutes 76 labels ['FW', 'RW']
substitute: event rows 16 | Substitute rows 10 | sample Sergio Arribas for Lázaro | player rows 32 | 'Sub' in Pos 0
  incoming in player rows 10 of 10 | minutes of incoming, max 45 | non-subs by team {'Almería': 11, 'Rayo Vallecano': 11}
own_goal: OwnGoal shot rows [{'player': 'Víctor Camarasa', 'minute': 9.0, 'home_team': 'Real Betis', 'away_team': 'Celta Vigo'}] | Own Goal events [{'Event_Players': 'Víctor Camarasa Own Goal —', 'Event_Time': 10.0, 'Team': 'Celta Vigo'}]
under_900: FBref minutes 899 | HF minutes 893 | shots 22 | labels ['FW', 'RW,FW']
multi_position: 'FW,LW' rows 1 | labels {'FW': 9, 'LM': 2, 'LM,FW': 1, 'FW,LW': 1, 'LW': 1} | minutes 1105
lm_rm_only: labels {'RM': 14, 'LM,RM': 2, 'RM,LM': 2, 'LM': 1} | minutes 1052
html_entity: shot 'Dara O&#039;Shea' | HF 'Dara O&#039;Shea' | FBref "Dara O'Shea"
shared_name: player_id {np.float64(2161.0): 9, np.float64(2247.0): 6} | hrefs {'/en/players/2946f9a1/Nacho': 6, '/en/players/e29d1111/Nacho': 23} | HF [{'team': 'Real Madrid', 'minutes': 434, 'shots': 6}, {'team': 'Real Valladolid', 'minutes': 1892, 'shots': 9}]
current_season: shot season {np.float64(2025.0)} dates 2025-09-14 15:30:00 2025-09-14 15:30:00 | FBref year {np.int32(2026)} minutes ['82'] Pos ['AM']
largest file bytes: 40536 | over 1 MB: 0
```

## 7. Cases not found

> Any case that can't be found in the stand-in files is reported and left out, never invented

**Met.**

| Case | Result | Why |
|---|---|---|
| A `Sub` Pos label | NOT FOUND | Pos has no `Sub` value: `'Sub' as a Pos value: 0` in section 1. Substitute appearances are cut from `Substitute` event rows instead. |
| HF row for the current-season player | NOT FOUND | `HF rows for 2025-2026: 0`, in section 6. The current-season sample has shot and FBref files only. |

## 8. Terms

> The FBref (Sports Reference) and Hugging Face dataset terms are read and summarised, and the worldfootballR repo's licence status is recorded

**Met.** This is a plain reading, not legal advice. Pages were read on 2026-11-03. Scripted requests to Sports Reference returned 403, so its pages were read in a normal browser view.

### FBref (Sports Reference)

[Terms of Use](https://www.sports-reference.com/termsofuse.html), last updated May 19, 2023. [Data use page](https://www.sports-reference.com/data_use.html). The [bot traffic page](https://www.sports-reference.com/bot-traffic.html) was not read, because it covers live scraping and this project does none.

- **Allowed:** sharing, using, changing or publishing data found on individual pages, commercial or not, with credit to Sports Reference.
- **Not allowed:** using the content to build a database or service that competes with, or substitutes for, the site or its data providers.
- **Not allowed without permission:** automated access that harms site performance.
- **Not allowed:** using the content for AI models, including training or prompting them and supporting machine-learning methods that predict, classify, label or score inputs.
- **Data use page:** says "you should not create websites or tools based on data you scrape". It also says some of its licences preclude any redistribution, and that facts cannot be copyrighted.
- **Terms, stated concern:** the Terms name copying a materially significant part of the data as harm to the business.

**What is unclear:**

- Whether a tool built on files scraped by someone else falls under that sentence. The sentence is guidance on a data use page, and it reads against this project either way.
- Whether positions and minutes for five leagues over seven seasons count as a large share of the data, or as a substitute.
- Whether PCA and distance methods count as the machine-learning methods named in the terms.
- Which football fields are under licences that bar redistribution. The page does not name them.

### Hugging Face

[Terms of Service](https://huggingface.co/terms-of-service), effective September 15, 2022. [Dataset card](https://huggingface.co/datasets/aloobun/fbref_understat_combined), commit `980fefef65fe802bf89abeb0ddd1ed208a3e1a51`.

- The uploader keeps ownership and is solely responsible for what they post.
- A public repository gives each user a licence to use and reproduce the content through Hugging Face's services.
- Licence notices stay in force, and downloaded content is used at the user's own risk.
- The service gives no warranty, and the terms do not say that Hugging Face checks licences.
- The dataset card has a `license: mit` tag. `docs/reports/HF_dataset_vetting.md` found no licence file.

**What is unclear:** whether the uploader had any right to apply MIT to data taken from FBref and Understat. The tag does not settle this, and the card gives no scrape date or method.

### worldfootballR

```
$ gh repo view JaseZiv/worldfootballR_data --json licenseInfo,isArchived,pushedAt
{"isArchived":true,"licenseInfo":null,"pushedAt":"2025-09-18T19:54:58Z"}
$ gh api repos/JaseZiv/worldfootballR_data/git/trees/HEAD?recursive=1 --jq '.tree[].path' | grep -iE '(^|/)(licen[cs]e|copying)[^/]*$'
(no output)
$ gh api repos/JaseZiv/worldfootballR_data/contents/README.md --jq .content | base64 -d | grep -ciE 'licen[cs]e|terms'
0
$ gh repo view JaseZiv/worldfootballR --json licenseInfo,isArchived,pushedAt
{"isArchived":true,"licenseInfo":null,"pushedAt":"2025-09-18T19:59:35Z"}
$ gh api repos/JaseZiv/worldfootballR/contents/DESCRIPTION --jq .content | base64 -d | grep -iE '^(Package|Version|License):'
Package: worldfootballR
Version: 0.6.8.0001
License: GPL-3
```

**Status:** `worldfootballR_data`, the repo holding these files, has no licence, and its README says nothing on terms. It is archived. The separate `worldfootballR` package states GPL-3 for its code, which says nothing about the data files.

**What is unclear:** with no licence, no one has been given permission to reuse those files. The plan already bars public launch until these terms are recorded and Ahmed approves, and Understat's own terms still wait for #14.

## Ready for #7: YES

#7 trims the vetted files into private Parquet storage, with no public release. Everything it needs is in place:

- `rdata` and `pyarrow` are allowed, and the round-trip is proven in `docs/reports/library_vetting.md`.
- The originals are backed up, and all 38 hashes match.
- Every planned field has a named source, and section 2 gives the coverage counts #7 must match.

#7 must take these from this report:

1. Use the union of the five Pos files. No single FBref file is complete.
2. Convert `Min` from text.
3. Treat the extra ITA 2022/23 and 2023/24 match URLs as possible duplicates. Nothing has been removed.
4. Keep `player_id` and `Player_Href`, because names are not unique.

**Decisions for Ahmed, none blocking #7:**

- Adopt the box constants in section 5 into the plan, which this task could not edit.
- Decide what the Sports Reference terms mean for the public site, before #13.
- Decide whether to build a name map for the unmatched 7.89% of Pool candidates. That belongs to #6 or #8.

## Appendix: scripts

Small checks quoted above:

```
$ venv/bin/python3 --version
Python 3.15.0
$ curl -sS -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0' -L https://www.sports-reference.com/termsofuse.html
403
$ python3 arithmetic
box half-width 0.2925
law widths used: box 40.32 m, six-yard 18.32 m
six-yard Y at that scale 0.3671 0.6329
gap to proposed 0.0021
emptiest-bin width 0.005, from trough() in t3_box.py
unmatched Pool candidates, 100 - 92.11 = 7.89
largest season range of a Y dip, 0.2165 - 0.1975 = 0.019
HF dataset commit 980fefef65fe802bf89abeb0ddd1ed208a3e1a51
```

The analysis scripts are not committed as files, because they were outside the scope of this task. They read `tmp/t3`, a cache in `~/sandbox/parquet-vet` built from the originals. `check_release.py` and `t3_verify.py` read the downloaded release assets.

<details><summary><code>t3_cache.py</code></summary>

```python
"""Working cache for #3 analysis only: read every .rds under the plan's rdata rules and keep all columns as Parquet in the sandbox."""
import sys, time, warnings
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq, rdata
warnings.simplefilter("ignore")
out = Path(sys.argv[2])
for l in Path(sys.argv[1]).read_text().splitlines():
    f = Path(l)
    if f.suffix != ".rds" or (out / (f.stem + ".parquet")).exists(): continue
    t = time.time()
    df = rdata.read_rds(f, default_encoding="utf8").reset_index(drop=True)
    df = df.astype({c: "Float64" for c in df.select_dtypes("float64").columns})
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out / (f.stem + ".parquet"), compression="zstd")
    print(f.name, df.shape, round(time.time() - t), flush=True)
```

</details>

<details><summary><code>t3_common.py</code></summary>

```python
"""Shared loaders for the #3 analysis. Reads the sandbox cache made from the .rds originals under the plan's rdata rules."""
import glob, html, os, re, unicodedata
import numpy as np, pandas as pd, pyarrow.parquet as pq
CACHE = "tmp/t3"
HF = os.path.expanduser("~/sandbox/hf_dump/files/data")
SHOT_FILES = {"bundesliga": "GER", "epl": "ENG", "la_liga": "ESP", "ligue_1": "FRA", "serie_a": "ITA"}
HF_LEAGUE = {"EPL": "ENG", "ESP": "ESP", "FRA": "FRA", "GER": "GER", "ITA": "ITA"}
STATS = ["passing", "defense", "misc", "passing_types", "possession"]
LEAGUES = ["ENG", "ESP", "FRA", "GER", "ITA"]
POOL_SEASONS = range(2017, 2024)  # season start years, 2017/18 to 2023/24
ATT = {"FW", "LW", "RW", "AM"}
def shots(columns=None):
    out = []
    for f, lg in SHOT_FILES.items():
        d = pq.read_table(f"{CACHE}/{f}_shot_data.parquet", columns=columns).to_pandas()
        d["file"], d["lg"] = f, lg
        out.append(d)
    return pd.concat(out, ignore_index=True)
def fbref_file(lg, stat, columns=None):
    return pq.read_table(f"{CACHE}/{lg}_M_1st_{stat}_player_advanced_match_stats.parquet", columns=columns).to_pandas()
def fbref_union():
    """One row per match + player across the five stat types holding Pos, in the order `passing` first."""
    cols = ["MatchURL", "Match_Date", "Team", "Home_Away", "Player", "Player_Href", "Pos", "Min", "Season_End_Year"]
    out = []
    for lg in LEAGUES:
        for st in STATS:
            d = fbref_file(lg, st, cols); d["lg"], d["stat"] = lg, st; out.append(d)
    u = pd.concat(out, ignore_index=True)
    return u.drop_duplicates(["lg", "MatchURL", "Player_Href"], keep="first")
def hf_xg():
    d = pd.read_csv(f"{HF}/understat_xg/understat_xg_data.csv", low_memory=False)
    d["lg"] = d.league.map(HF_LEAGUE); d["start"] = d.season.str[:4].astype(int)
    return d
def hf_fbref():
    d = pd.read_csv(f"{HF}/player_stats/master_player_stats.csv", low_memory=False)
    return d[d["rank"].astype(str) != "Rk"]
def plain(s):
    return html.unescape(s) if isinstance(s, str) else s
def fold(s):
    """Accents removed, lower case, word order ignored."""
    s = unicodedata.normalize("NFKD", html.unescape(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("-", " ").replace("'", "")
    return " ".join(sorted(s.split()))
def labels(pos):
    return [] if not isinstance(pos, str) else [p.strip() for p in pos.split(",")]
```

</details>

<details><summary><code>t3_a.py</code></summary>

```python
"""Criterion 1: exact strings. Criterion 2: season coverage per file. Criterion 3: field presence."""
import sys, glob, collections
sys.path.insert(0, sys.argv[1])
from t3_common import *
s = shots()
print("### exact strings in the shot files, repr, rows")
for c in ["lastAction", "situation", "shotType", "result"]:
    vc = s[c].value_counts(dropna=False)
    print(f"{c}: {len(vc)} values, nulls {int(s[c].isna().sum())}")
    print("  " + ", ".join(f"{k!r} {v}" for k, v in vc.items()))
for c in ["situation", "shotType", "result"]:
    print(c, "by file identical label set:", len({frozenset(s[s.file == f][c].unique()) for f in SHOT_FILES}) == 1)
print("plan labels present:", {k: int((s[c] == k).sum()) for c, k in [("lastAction", "TakeOn"), ("lastAction", "Throughball"), ("shotType", "Head"), ("situation", "Penalty"), ("result", "OwnGoal")]})
print("\n### FBref Pos across the 30 stat files")
pos_tot = collections.Counter(); atom = collections.Counter(); multi = rows = nulls = 0; lacks = []
for f in sorted(glob.glob(f"{CACHE}/*_player_advanced_match_stats.parquet")):
    name = f.split("/")[-1]
    t = pq.read_schema(f).names
    if "Pos" not in t: lacks.append(name); continue
    p = pq.read_table(f, columns=["Pos"]).to_pandas().Pos
    rows += len(p); nulls += int(p.isna().sum())
    pos_tot.update(p.dropna().tolist())
    multi += int(p.dropna().str.contains(",").sum())
for k, v in pos_tot.items():
    for a in labels(k): atom[a] += v
print("files without Pos:", lacks)
print("rows", rows, "| null", nulls, "| multi-label rows", multi, "| distinct values", len(pos_tot))
print("atomic labels, rows:", ", ".join(f"{k!r} {v}" for k, v in atom.most_common()))
print("'Sub' as a Pos value:", pos_tot.get("Sub", 0), "| any label containing 'Sub' or 'sub':", sum(v for k, v in atom.items() if "sub" in k.lower()))
print("most common values:", ", ".join(f"{k!r} {v}" for k, v in pos_tot.most_common(25)))
print("\n### shot files: matches and rows by season start year")
for f in SHOT_FILES:
    d = s[s.file == f]; g = d.groupby("season").agg(matches=("match_id", "nunique"), rows=("id", "size"), first=("date", "min"), last=("date", "max"))
    print(f, " ".join(f"{int(k)}:{v.matches}" for k, v in g.iterrows()), "| last date", g["last"].iloc[-1])
print("\n### FBref stat files and events: matches by Season_End_Year")
for f in sorted(glob.glob(f"{CACHE}/*_M_1st_*.parquet")):
    d = pq.read_table(f, columns=["MatchURL", "Season_End_Year", "Match_Date"]).to_pandas()
    g = d.groupby("Season_End_Year").MatchURL.nunique()
    print(f.split("/")[-1].replace(".parquet", "").replace("_player_advanced_match_stats", ""), " ".join(f"{int(k)}:{v}" for k, v in g.items()), "| dates", d.Match_Date.min(), d.Match_Date.max())
ev = pd.read_csv(os.path.expanduser("~/sandbox/wfr/files_events/ENG_M_1st_match_summary.csv"), low_memory=False)
print("ENG_M_1st_match_summary.csv", " ".join(f"{int(k)}:{v}" for k, v in ev.groupby("Season_End_Year").MatchURL.nunique().items()), "| dates", ev.Match_Date.min(), ev.Match_Date.max())
print("\n### HF understat_xg_data.csv rows by league and season; master_player_stats.csv same")
x = hf_xg(); m = hf_fbref()
print(x.pivot_table(index="lg", columns="season", values="minutes", aggfunc="size").to_string())
print(m.pivot_table(index="league", columns="season", values="min", aggfunc="size").to_string())
print("\n### fields")
print("shot file columns:", {f: [c for c in pq.read_schema(f"{CACHE}/{f}_shot_data.parquet").names] == pq.read_schema(f"{CACHE}/epl_shot_data.parquet").names for f in SHOT_FILES})
for c in ["X", "Y", "lastAction", "situation", "shotType", "result", "xG", "player", "player_id", "player_assisted", "match_id", "season", "date", "h_a", "home_away", "league"]:
    print(f"shots.{c}: nulls {int(s[c].isna().sum())} of {len(s)}")
for c in ["player_name", "minutes", "goals", "assists", "shots", "key_passes", "xG", "xA", "npxG", "xGBuildup", "apps", "team"]:
    print(f"understat_xg_data.csv.{c}: nulls {int(x[c].isna().sum())} of {len(x)}")
for c in ["player", "player_id", "pos", "min", "pk", "pkatt", "gls", "squad"]:
    print(f"master_player_stats.csv.{c}: nulls {int(m[c].isna().sum())} of {len(m)}")
for f in sorted(glob.glob(f"{CACHE}/*_player_advanced_match_stats.parquet")):
    n = pq.read_schema(f).names; d = pq.read_table(f, columns=[c for c in ["Pos", "Min", "Player", "Player_Href", "MatchURL"] if c in n]).to_pandas()
    print(f.split("/")[-1][:40], {c: ("missing" if c not in n else int(d[c].isna().sum())) for c in ["Pos", "Min", "Player", "Player_Href", "MatchURL"]}, "rows", len(d))
print("xA/xGBuildup/key_passes/time/npxG in shot file?", {c: c in s.columns for c in ["xA", "xGBuildup", "key_passes", "time", "npxG", "npg", "position"]})
```

</details>

<details><summary><code>t3_gaps.py</code></summary>

```python
"""Criterion 2 gaps: Pool-season match counts below or above what the league played, per file and for the union of the five Pos files."""
import sys, glob
sys.path.insert(0, sys.argv[1])
from t3_common import *
def expected(lg, start):
    if lg == "GER": return 306
    if lg == "FRA" and start == 2019: return 279
    if lg == "FRA" and start >= 2023: return 306
    return 380
print("expected: 380, GER 306, FRA 2019/20 279 (shortened), FRA 2023/24 on 306 (18 clubs). Pool seasons only.")
s = shots(["match_id", "season"])
for lg in LEAGUES:
    g = s[s.lg == lg].groupby("season").match_id.nunique()
    print("shots", lg, [(int(k), int(v)) for k, v in g.items() if int(k) in POOL_SEASONS and v != expected(lg, int(k))] or "complete")
for f in sorted(glob.glob(f"{CACHE}/*_M_1st_*.parquet")):
    n = f.split("/")[-1]; lg = n[:3]
    d = pq.read_table(f, columns=["MatchURL", "Season_End_Year"]).to_pandas(); g = d.groupby("Season_End_Year").MatchURL.nunique()
    gaps = [(f"{int(k)-1}/{str(int(k))[2:]}", int(v), expected(lg, int(k) - 1)) for k, v in g.items() if int(k) - 1 in POOL_SEASONS and v != expected(lg, int(k) - 1)]
    print(n.replace("_player_advanced_match_stats.parquet", "").replace(".parquet", ""), gaps or "complete")
ev = pd.read_csv(os.path.expanduser("~/sandbox/wfr/files_events/ENG_M_1st_match_summary.csv"), low_memory=False); g = ev.groupby("Season_End_Year").MatchURL.nunique()
print("ENG_M_1st_match_summary.csv", [(f"{int(k)-1}/{str(int(k))[2:]}", int(v), 380) for k, v in g.items() if int(k) - 1 in POOL_SEASONS and v != 380] or "complete")
u = fbref_union(); u["start"] = pd.to_numeric(u.Season_End_Year).astype(int) - 1
print("union of the five Pos files:")
for lg in LEAGUES:
    g = u[u.lg == lg].groupby("start").MatchURL.nunique(); print(" ", lg, " ".join(f"{k}:{v}" for k, v in g.items()), "| Pool gaps", [(int(k), int(v)) for k, v in g.items() if int(k) in POOL_SEASONS and v != expected(lg, int(k))] or "none")
print("\nPos rows with an empty label:")
for lg in LEAGUES:
    d = fbref_file(lg, "passing", ["Pos", "Min", "Player", "Season_End_Year"]); e = d[d.Pos.map(lambda v: "" in labels(v))]
    print(" ", lg, "passing:", len(e), e.Pos.tolist()[:6], "| Min", e.Min.tolist()[:6], "| null Min rows:", int(d.Min.isna().sum()))
print("\nown goals in shots, Pool seasons, by league:", s.shape[0] and shots(["result", "season"]).query("result == 'OwnGoal' and season >= 2017 and season <= 2023").groupby("lg").size().to_dict())
print("\nPos cells with an empty label, every stat file:")
for f in sorted(glob.glob(f"{CACHE}/*_player_advanced_match_stats.parquet")):
    if "Pos" not in pq.read_schema(f).names: continue
    d = pq.read_table(f, columns=["Pos", "Min"]).to_pandas(); e = d[d.Pos.map(lambda v: "" in labels(v))]
    if len(e): print(" ", f.split("/")[-1][:34], len(e), e.Pos.tolist(), e.Min.tolist())
d = fbref_file("GER", "passing", ["Min"]); print("Min column type in the files:", pq.read_schema(f"{CACHE}/GER_M_1st_passing_player_advanced_match_stats.parquet").field("Min").type, "| sample", d.Min.iloc[0])
```

</details>

<details><summary><code>t3_join.py</code></summary>

```python
"""Criterion 4: joins between the three sources, with match rates by league, Pool seasons 2017/18 to 2023/24."""
import sys
sys.path.insert(0, sys.argv[1])
from t3_common import *
s = shots(["player", "player_id", "season", "result", "situation"]); s = s[s.season.isin(POOL_SEASONS)].copy(); s["start"] = s.season.astype(int)
u = fbref_union(); u["start"] = u.Season_End_Year.astype(int) - 1; u = u[u.start.isin(POOL_SEASONS)]; u["Min"] = pd.to_numeric(u.Min, errors="coerce").fillna(0)
x = hf_xg(); x = x[x.start.isin(POOL_SEASONS)]
m = hf_fbref().copy(); m = m[m.league.isin(HF_LEAGUE)].copy(); m["lg"] = m.league.map(HF_LEAGUE); m["start"] = m.season.str[:4].astype(int); m = m[m.start.isin(POOL_SEASONS)]; m["min"] = pd.to_numeric(m["min"], errors="coerce").fillna(0)
s["name"] = s.player.map(plain); s["key"] = s.name.map(fold)
x["name"] = x.player_name.map(plain); x["key"] = x.name.map(fold)
fb = u.groupby(["lg", "start", "Player", "Player_Href"], as_index=False).Min.sum(); fb["name"] = fb.Player.map(plain); fb["key"] = fb.name.map(fold)
att = u.assign(a=u.Pos.map(lambda p: bool(set(labels(p)) & ATT))).groupby(["lg", "start", "Player_Href", "a"]).Min.sum().unstack(fill_value=0).rename(columns={True: "att", False: "oth"}).reset_index()
fb = fb.merge(att, on=["lg", "start", "Player_Href"], how="left"); fb["candidate"] = (fb.Min >= 900) & (fb.att > fb.oth)
sk = s.groupby(["lg", "start", "name", "key"], as_index=False).agg(rows=("player", "size"), ids=("player_id", "nunique"))
xk = x.groupby(["lg", "start", "name", "key"], as_index=False).agg(minutes=("minutes", "sum"), n=("minutes", "size"))
def rate(label, left, right, on, weight=None):
    print(f"\n{label}")
    print("league | keys | matched | rate" + (" | rows | rows matched | rate" if weight else ""))
    tot = [0, 0, 0, 0]
    keys = set(map(tuple, right[["lg", "start", on]].drop_duplicates().to_numpy()))
    for lg in LEAGUES + ["ALL"]:
        d = left if lg == "ALL" else left[left.lg == lg]
        hit = np.array([(a, b, c) in keys for a, b, c in zip(d.lg, d.start, d[on])], dtype=bool)
        line = f"{lg} | {len(d)} | {hit.sum()} | {hit.mean():.2%}"
        if weight: line += f" | {int(d[weight].sum())} | {int(d[weight][hit].sum())} | {d[weight][hit].sum() / d[weight].sum():.2%}"
        print(line)
rate("A. Shot keys to HF understat_xg, exact unescaped name", sk, xk, "name", "rows")
rate("A2. Shot keys to HF understat_xg, folded name", sk, xk, "key", "rows")
rate("B. Shot keys to FBref, exact unescaped name", sk, fb, "name", "rows")
rate("B2. Shot keys to FBref, folded name", sk, fb, "key", "rows")
rate("C. FBref keys at 900+ to shot keys, folded name", fb[fb.Min >= 900], sk, "key")
rate("D. Pool candidates (900+, attacking > other, subs not removed) to shot keys, exact", fb[fb.candidate], sk, "name")
rate("D2. Pool candidates to shot keys, folded", fb[fb.candidate], sk, "key")
rate("E. Pool candidates to HF understat_xg, folded", fb[fb.candidate], xk, "key")
fbid = fb.assign(pid=fb.Player_Href.str.extract(r"/players/([0-9a-f]{8})/", expand=False))
print("\nhref without an 8-hex id:", int(fbid.pid.isna().sum()))
mk = m.groupby(["lg", "start", "player_id"], as_index=False)["min"].sum()
fbid2 = fbid.groupby(["lg", "start", "pid"], as_index=False).Min.sum()
print("\nF. FBref keys at 900+ to HF master_player_stats, by FBref player id\nleague | keys | matched | rate | identical minutes among matched")
for lg in LEAGUES + ["ALL"]:
    d = fbid2[fbid2.Min >= 900]; d = d if lg == "ALL" else d[d.lg == lg]
    g = d.merge(mk, how="left", left_on=["lg", "start", "pid"], right_on=["lg", "start", "player_id"])
    hit = g.player_id.notna(); print(f"{lg} | {len(g)} | {hit.sum()} | {hit.mean():.2%} | {(g[hit].Min == g[hit]['min']).mean():.2%}")
print("\nambiguity")
print("shot keys (name, league, season) with several player_id:", int((sk.ids > 1).sum()), "rows", int(sk[sk.ids > 1].rows.sum()))
nd = fb.groupby(["lg", "start", "name"]).Player_Href.nunique()
print("FBref keys (name, league, season) with several Player_Href:", int((nd > 1).sum()))
print("HF understat_xg keys with several rows:", int((xk.n > 1).sum()))
print("matched folded keys that hit several exact FBref names:", int(fb.groupby(["lg", "start", "key"]).name.nunique().gt(1).sum()))
print("names holding an HTML entity: shot rows", int(s.player.str.contains(r"&#?\w+;", regex=True).sum()), "| HF rows", int(x.player_name.str.contains(r"&#?\w+;", regex=True).sum()), "| FBref rows", int(u.Player.str.contains(r"&#?\w+;", regex=True, na=False).sum()))
fb.to_parquet(sys.argv[2] + "/fb_keys.parquet")
```

</details>

<details><summary><code>t3_box.py</code></summary>

```python
"""Criterion 5: calibrate box lines from penalties, direct free kicks and shot-density dips. Text heatmaps with the proposed lines."""
import sys
sys.path.insert(0, sys.argv[1])
from t3_common import *
s = shots(["X", "Y", "situation", "result", "season", "shotType"])
for c in "XY": s[c] = s[c].astype(float)
pen = s[s.situation == "Penalty"]
print("penalties", len(pen), "X", pen.X.round(4).value_counts().to_dict(), "Y", pen.Y.round(4).value_counts().to_dict())
print("X decimals: share of rows on a 0.001 grid", round(float(((s.X * 1000).round() - s.X * 1000).abs().lt(1e-3).mean()), 4))
SPOT = pen.X.round(4).mode()[0]
print("scale from the spot: 11 m = 1 -", SPOT, "=> metres per unit", round(11 / (1 - SPOT), 2))
print("laws-of-the-game lines at that scale: box X", round(1 - (1 - SPOT) * 16.5 / 11, 4), "six-yard X", round(1 - (1 - SPOT) * 5.5 / 11, 4))
print("Y lines if width is 68 m: box", round(.5 - 20.16 / 68, 4), round(.5 + 20.16 / 68, 4), "six-yard", round(.5 - 9.16 / 68, 4), round(.5 + 9.16 / 68, 4))
o = s[(s.situation != "Penalty") & (s.result != "OwnGoal")]
fk = s[s.situation == "DirectFreekick"]
print("non-penalty, non-own-goal shots", len(o), "| direct free kicks", len(fk))
def hist(v, lo, hi, w):
    b = np.round(np.arange(lo, hi + w / 2, w), 4); h, _ = np.histogram(v, b); return b, h
def show(name, v, lo, hi, w):
    b, h = hist(v, lo, hi, w); print(name, " ".join(f"{b[i]:.3f}:{h[i]}" for i in range(len(h))))
def trough(v, lo, hi, w=.005):
    """Centre of the emptiest bin in the window. Five 0.001 sub-offsets average out the grid's rounding."""
    best = []
    for off in np.arange(0, w, .001):
        b, h = hist(v, lo + off, hi + off, w); i = int(np.argmin(h)); best.append(float(b[i] + w / 2))
    return round(float(np.mean(best)), 4), round(float(np.min(best)), 4), round(float(np.max(best)), 4)
c = fk[(fk.Y - .5).abs() < .15]
print("\n-- free kicks, central |Y-0.5|<0.15, by X")
show("X", c.X, .80, .86, .0025)
print("share of central free kicks with X >= t:", {t: int((c.X >= t).sum()) for t in [.82, .8225, .825, .8275, .83, .8325, .835]}, "of", len(c))
n = fk[fk.X > .86]
print("\n-- free kicks, X>0.86, by Y")
show("Y low", n.Y, .18, .24, .0025); show("Y high", n.Y, .76, .82, .0025)
print("\n-- all shots, density dips")
show("X near box", o.X, .81, .86, .0025)
show("X near six", o[(o.Y - .5).abs() < .13].X, .925, .96, .0025)
inbox = o[o.X > .8275]; six = o[o.X > .9425]
show("Y low box", inbox.Y, .18, .24, .0025); show("Y high box", inbox.Y, .76, .82, .0025)
show("Y low six", six.Y, .34, .40, .0025); show("Y high six", six.Y, .60, .66, .0025)
T = {"BOX_X_MIN": trough(o.X, .815, .85), "SIX_X_MIN": trough(o[(o.Y - .5).abs() < .13].X, .93, .955),
     "BOX_Y_MIN": trough(inbox.Y, .18, .24), "BOX_Y_MAX": trough(inbox.Y, .76, .82),
     "SIX_Y_MIN": trough(six.Y, .34, .40), "SIX_Y_MAX": trough(six.Y, .60, .66)}
print("\n-- density-dip centre (mean, lowest, highest across bin offsets)"); [print(k, v) for k, v in T.items()]
print("\n-- stability: density-dip centre by league")
ss = shots(["X", "Y", "situation", "result", "season"]); ss = ss[(ss.situation != "Penalty") & (ss.result != "OwnGoal")]
for c2 in "XY": ss[c2] = ss[c2].astype(float)
for f in SHOT_FILES:
    d = ss[ss.file == f]; ib = d[d.X > .8275]; sx = d[d.X > .9425]
    print(f, "box X", trough(d.X, .815, .85)[0], "six X", trough(d[(d.Y - .5).abs() < .13].X, .93, .955)[0], "box Y", trough(ib.Y, .18, .24)[0], trough(ib.Y, .76, .82)[0], "six Y", trough(sx.Y, .34, .40)[0], trough(sx.Y, .60, .66)[0])
print("-- stability by season")
for yr, d in ss.groupby("season"):
    if len(d) < 20000: print(int(yr), "rows", len(d), "too few, skipped"); continue
    ib = d[d.X > .8275]; sx = d[d.X > .9425]
    print(int(yr), "box X", trough(d.X, .815, .85)[0], "six X", trough(d[(d.Y - .5).abs() < .13].X, .93, .955)[0], "box Y", trough(ib.Y, .18, .24)[0], trough(ib.Y, .76, .82)[0], "six Y", trough(sx.Y, .34, .40)[0], trough(sx.Y, .60, .66)[0])
```

</details>

<details><summary><code>t3_box2.py</code></summary>

```python
"""Fine view of the free-kick edges, the proposed lines' effect, and text heatmaps."""
import sys
sys.path.insert(0, sys.argv[1])
from t3_common import *
s = shots(["X", "Y", "situation", "result", "shotType"])
for c in "XY": s[c] = s[c].astype(float)
L = dict(BOX_X_MIN=.8275, SIX_X_MIN=.9425, BOX_Y_MIN=.2075, BOX_Y_MAX=.7925, SIX_Y_MIN=.365, SIX_Y_MAX=.635)
fk = s[s.situation == "DirectFreekick"]; c = fk[(fk.Y - .5).abs() < .15]; n = fk[fk.X > .86]
def grid(v, lo, hi):
    k = (v * 1000).round().astype(int); return " ".join(f"{i/1000:.3f}:{int((k == i).sum())}" for i in range(int(lo * 1000), int(hi * 1000) + 1))
print("free kicks, central, each 0.001 of X:", grid(c.X, .820, .834))
print("free kicks, X>0.86, each 0.001 of Y, low:", grid(n.Y, .198, .216))
print("free kicks, X>0.86, each 0.001 of Y, high:", grid(n.Y, .784, .802))
def inside(d, x, a, b): return (d.X >= x) & (d.Y >= a) & (d.Y <= b)
print("direct free kicks inside the proposed box:", int(inside(fk, L["BOX_X_MIN"], L["BOX_Y_MIN"], L["BOX_Y_MAX"]).sum()), "of", len(fk), f"= {inside(fk, L['BOX_X_MIN'], L['BOX_Y_MIN'], L['BOX_Y_MAX']).mean():.3%}")
print("direct free kicks inside X-only starting estimate (X >= 0.8275):", int((fk.X >= .8275).sum()), f"= {(fk.X >= .8275).mean():.3%}")
print("direct free kicks inside with 68 m Y lines (0.2035, 0.7965):", int(inside(fk, .8275, .2035, .7965).sum()))
o = s[(s.situation != "Penalty") & (s.result != "OwnGoal")]
ib = inside(o, L["BOX_X_MIN"], L["BOX_Y_MIN"], L["BOX_Y_MAX"]); sx = inside(o, L["SIX_X_MIN"], L["SIX_Y_MIN"], L["SIX_Y_MAX"])
print("non-penalty, non-own-goal shots", len(o), f"| inside box {int(ib.sum())} = {ib.mean():.2%} | outside box {int((~ib).sum())} = {(~ib).mean():.2%} | six-yard {int(sx.sum())} = {sx.mean():.2%}")
print(f"X-only starting estimate would give: outside {int((o.X < .8275).sum())} = {(o.X < .8275).mean():.2%} | six-yard {int((o.X >= .9425).sum())} = {(o.X >= .9425).mean():.2%}")
print("shots reclassified by adding Y lines: box", int(((o.X >= .8275) & ~ib).sum()), "| six-yard", int(((o.X >= .9425) & ~sx).sum()))
h = o[o.shotType == "Head"]; print(f"headers inside box {inside(h, L['BOX_X_MIN'], L['BOX_Y_MIN'], L['BOX_Y_MAX']).mean():.2%} of {len(h)}")
print("X and Y out of range:", int(((s.X < 0) | (s.X > 1) | (s.Y < 0) | (s.Y > 1)).sum()))
def heat(d, title):
    xb = np.round(np.arange(.78, 1.0001, .01), 2); yb = np.round(np.arange(.14, .8601, .02), 2)
    H, _, _ = np.histogram2d(d.Y, d.X, bins=[yb, xb]); top = H.max()
    print(f"\n{title}. Rows are Y, columns are X in 0.01 steps from 0.78. Digit = shots on a log scale, 0-9, '.' = none. Peak cell {int(top)}. '|' and '-' mark the proposed lines: the box and the six-yard box.")
    xm = {L["BOX_X_MIN"], L["SIX_X_MIN"]}
    head = "        "
    for i in range(len(xb) - 1):
        head += ("|" if any(xb[i] <= m < xb[i + 1] for m in xm) else " ") + str(int(xb[i] * 100) % 10)
    print(head)
    for r in range(len(yb) - 1):
        for m, name in ((L["BOX_Y_MIN"], "box"), (L["SIX_Y_MIN"], "six"), (L["SIX_Y_MAX"], "six"), (L["BOX_Y_MAX"], "box")):
            if yb[r] <= m < yb[r + 1]: print(f"{name} {m:.4f} " + "-" * (2 * (len(xb) - 1)))
        cells = ""
        for i in range(len(xb) - 1):
            v = H[r, i]; ch = "." if v == 0 else str(min(9, int(np.log(v) / np.log(top) * 10)))
            cells += ("|" if any(xb[i] <= m < xb[i + 1] for m in xm) else " ") + ch
        print(f"{yb[r]:.2f}    " + cells)
heat(o, "All non-penalty, non-own-goal shots")
heat(fk, "Direct free kicks only: these cannot legally start inside the box")
```

</details>

<details><summary><code>t3_fix.py</code></summary>

```python
"""Find one real example of each fixture case. Every choice is a stated rule, so nobody picks by hand. Prints candidate counts and the choice."""
import sys, re
sys.path.insert(0, sys.argv[1])
from t3_common import *
s = shots(["id", "player", "player_id", "season", "result", "date", "match_id", "situation"]); s["start"] = s.season.astype(int); s["name"] = s.player.map(plain); s = s.drop(columns="season")
fb = pd.read_parquet(sys.argv[1] + "/fb_keys.parquet")
x = hf_xg()
pcols = ["MatchURL", "Match_Date", "Team", "Player", "Player_Href", "Pos", "Min", "Season_End_Year"]
pa_ = pd.concat([fbref_file(l, "passing", pcols).assign(lg=l) for l in LEAGUES], ignore_index=True); pa_["start"] = pd.to_numeric(pa_.Season_End_Year).astype(int) - 1; pa_["Min"] = pd.to_numeric(pa_.Min, errors="coerce").fillna(0)
full = {(l, st): n for (l, st), n in pa_.groupby(["lg", "start"]).MatchURL.nunique().items()}
ok = lambda l, st: full.get((l, st), 0) >= (306 if l == "GER" else 380)
pk = pa_.groupby(["lg", "start", "Player", "Player_Href"], as_index=False).agg(rows=("Min", "size"), mins=("Min", "sum"))
sk = s.groupby(["lg", "start", "name"], as_index=False).agg(shots=("id", "size"), ids=("player_id", "nunique"), first=("date", "min"), last=("date", "max"))
xk = x.assign(name=x.player_name.map(plain)).groupby(["lg", "start", "name"], as_index=False).agg(hf=("minutes", "size"), hfmin=("minutes", "sum"))
pool = list(POOL_SEASONS)
print("### league move: same FBref id in two leagues in one Pool season, same name in shots and HF for both, stints do not overlap in the shot dates")
g = pk[pk.start.isin(pool)].groupby(["start", "Player_Href"]).filter(lambda d: d.lg.nunique() == 2)
print("FBref id-seasons in two leagues:", g.groupby(["start", "Player_Href"]).ngroups)
j = g.merge(sk, left_on=["lg", "start", "Player"], right_on=["lg", "start", "name"]).merge(xk, on=["lg", "start", "name"])
j = j.groupby(["start", "Player_Href"]).filter(lambda d: len(d) == 2 and d.shots.min() >= 3 and (d.sort_values("first")["last"].iloc[0] < d.sort_values("first")["first"].iloc[1]) and all(ok(a, b) for a, b in zip(d.lg, d.start)))
at = fb[["lg", "start", "Player_Href", "att", "oth"]]; j = j.merge(at, on=["lg", "start", "Player_Href"]); j = j.groupby(["start", "Player_Href"]).filter(lambda d: (d.att > d.oth).all())
print("and attacking minutes > other minutes in both stints:", j.groupby(["start", "Player_Href"]).ngroups)
print("with both stints in shots and HF, 3+ shots each, no overlap, full passing file:", j.groupby(["start", "Player_Href"]).ngroups)
t = j.groupby(["start", "Player_Href", "Player"], as_index=False).shots.sum().sort_values(["shots", "start", "Player"]).iloc[0]
print("chosen (fewest shots):"); print(j[(j.start == t.start) & (j.Player_Href == t.Player_Href)][["lg", "start", "Player", "Player_Href", "rows", "mins", "shots", "first", "last", "hf", "hfmin", "att", "oth"]].to_string())
print("\n### substitute: ESP 2023/24 match, 11 non-subs per team, sub in event rows, name in passing")
ev = pq.read_table(f"{CACHE}/ESP_M_1st_match_summary.parquet").to_pandas(); ev["start"] = pd.to_numeric(ev.Season_End_Year).astype(int) - 1
print("Event_Type values:", ev.Event_Type.value_counts(dropna=False).to_dict())
pe = pa_[(pa_.lg == "ESP") & (pa_.start == 2023)]
cand = []
for url, d in ev[(ev.start == 2023) & (ev.Event_Type == "Substitute")].groupby("MatchURL"):
    r = pe[pe.MatchURL == url]
    if r.empty: continue
    subs = {plain(v.split(" for ")[0].strip()) for v in d.Event_Players}
    non = r[~r.Player.map(plain).isin(subs)].groupby("Team").size()
    if len(non) == 2 and (non == 11).all() and len(subs & set(r.Player.map(plain))) == len(subs): cand.append((d.Match_Date.iloc[0], url, len(subs), len(r)))
print("candidate matches:", len(cand)); print("chosen (earliest):", sorted(cand)[0])
print("\n### own goal: La Liga Pool season shot row result OwnGoal, same date and name in ESP events")
og = s[(s.lg == "ESP") & s.start.isin(pool) & (s.result == "OwnGoal")].copy(); og["day"] = og.date.str[:10]
eo = ev[ev.Event_Type == "Own Goal"].copy(); eo["nm"] = eo.Event_Players.map(plain).str.replace(r"\s*Own Goal.*$", "", regex=True)
print("shot own goals (La Liga, Pool seasons):", len(og), "| event own goals (ESP):", len(eo))
m = og.merge(eo, left_on=["day", "name"], right_on=["Match_Date", "nm"]); print("matched on date and name:", len(m))
t = m.sort_values(["day", "id"]).iloc[0]; print("chosen (earliest):", t["day"], t["name"], "match_id", int(t.match_id), t.MatchURL, "| shot rows in match", int((s[s.lg == "ESP"].match_id == t.match_id).sum()), "| event rows", int((ev.MatchURL == t.MatchURL).sum()))
print("own goals in shots and events match on team side?", t.Team)
print("\n### under 900: Pool season attacker with FBref minutes under 900 and HF under 900, closest to the line, 3+ shots")
c = fb[fb.start.isin(pool) & (fb.Min < 900) & (fb.Min > 0) & (fb.att > fb.oth)].merge(sk, left_on=["lg", "start", "Player"], right_on=["lg", "start", "name"], suffixes=("", "_s")).merge(xk, left_on=["lg", "start", "Player"], right_on=["lg", "start", "name"], suffixes=("", "_h")).merge(pk[["lg", "start", "Player_Href", "rows", "mins"]], on=["lg", "start", "Player_Href"])
c = c[(c.hfmin < 900) & (c.shots >= 3) & (c.ids == 1) & (c.hf == 1) & (c.mins == c.Min) & c.apply(lambda r: ok(r.lg, r.start), axis=1)]
print("candidates:", len(c)); print(c.sort_values(["Min", "Player"], ascending=[False, True]).head(1)[["lg", "start", "Player", "Player_Href", "Min", "hfmin", "shots", "rows"]].to_string())
print("\n### multi-position: player-season at 900+ with an exact 'FW,LW' row and a non-attacking row, fewest rows")
pp = pa_[pa_.start.isin(pool)].copy(); pp["att"] = pp.Pos.map(lambda v: bool(set(labels(v)) & ATT))
ag = pp.groupby(["lg", "start", "Player", "Player_Href"]).agg(n=("Pos", "size"), mins=("Min", "sum"), fwlw=("Pos", lambda v: (v == "FW,LW").sum()), other=("att", lambda v: (~v).sum())).reset_index()
print("rows with exact Pos 'FW,LW' in passing files:", int((pp.Pos == "FW,LW").sum()))
c = ag[(ag.mins >= 900) & (ag.fwlw > 0) & (ag.other > 0)]; c = c[c.apply(lambda r: ok(r.lg, r.start), axis=1)]
print("candidates:", len(c)); print(c.sort_values(["n", "Player"]).head(1).to_string())
print("\n### LM/RM only: player-season at 900+, every label LM or RM")
ag2 = pp.groupby(["lg", "start", "Player", "Player_Href"]).agg(n=("Pos", "size"), mins=("Min", "sum"), only=("Pos", lambda v: all(set(labels(p)) <= {"LM", "RM"} for p in v))).reset_index()
c = ag2[(ag2.mins >= 900) & ag2.only]; c = c[c.apply(lambda r: ok(r.lg, r.start), axis=1)]
print("candidates:", len(c)); print(c.sort_values(["n", "Player"]).head(1).to_string())
print("\n### HTML entity: shot name holds an entity, HF name too, unescaped name in FBref")
e = s[s.start.isin(pool) & s.player.str.contains(r"&#?\w+;", regex=True)].groupby(["lg", "start", "player", "name"], as_index=False).size()
print("shot name-seasons:", len(e), "| distinct raw names:", e.player.nunique(), "| entities:", sorted(set(sum([re.findall(r"&#?\w+;", v) for v in e.player.unique()], []))))
hr = x[x.player_name.str.contains(r"&#?\w+;", regex=True)]
e2 = e.merge(hr, left_on=["lg", "start", "player"], right_on=["lg", "start", "player_name"]).merge(pk, left_on=["lg", "start", "name"], right_on=["lg", "start", "Player"])
e2 = e2[e2["size"] >= 3]; e2 = e2[e2.apply(lambda r: ok(r.lg, r.start), axis=1)]
print("in all three:", len(e2)); print(e2.sort_values(["size", "player"]).head(1)[["lg", "start", "player", "player_name", "Player", "size", "rows"]].to_string())
print("\n### shared name: one name, two ids, same league-season, in shot file and FBref")
a = sk[sk.start.isin(pool) & (sk.ids > 1)]; b = pk[pk.start.isin(pool)].groupby(["lg", "start", "Player"]).agg(hrefs=("Player_Href", "nunique"), frows=("rows", "sum")).reset_index(); b = b[b.hrefs > 1]
print("shot name-seasons with two ids:", len(a), "| FBref name-seasons with two ids:", len(b))
c = a.merge(b, left_on=["lg", "start", "name"], right_on=["lg", "start", "Player"]).merge(xk, on=["lg", "start", "name"], how="left"); c = c[c.apply(lambda r: ok(r.lg, r.start), axis=1)]
print("in both:", len(c)); print(c.sort_values(["shots", "name"]).head(3)[["lg", "start", "name", "ids", "shots", "hrefs", "frows", "hf", "hfmin"]].to_string())
print("\n### current-season: 2025/26 attacker, in shots and FBref, exact name")
cs = s[s.start == 2025].groupby(["lg", "name"], as_index=False).agg(shots=("id", "size"), ids=("player_id", "nunique"), last=("date", "max"))
pc = pa_[pa_.start == 2025].copy(); pc["att"] = pc.Pos.map(lambda v: bool(set(labels(v)) & ATT))
pg = pc.groupby(["lg", "Player", "Player_Href"]).agg(n=("Pos", "size"), mins=("Min", "sum"), atts=("att", "sum")).reset_index()
c = cs.merge(pg, left_on=["lg", "name"], right_on=["lg", "Player"]); c = c[(c.ids == 1) & (c.atts == c.n) & (c.shots >= 3)]
print("HF rows for 2025-2026:", int((x.season == "2025-2026").sum()), "| candidates:", len(c)); print(c.sort_values(["shots", "n", "name"]).head(1).to_string())
print("max FBref minutes in 2025/26:", pg.mins.max(), "| FBref matches:", pc.MatchURL.nunique(), "| dates", pc.Match_Date.min(), pc.Match_Date.max())
```

</details>

<details><summary><code>t3_verify.py</code></summary>

```python
"""Outside check of the fixtures, using none of cut_fixtures.py. Parse README for source and filter, read the source with a different reader (pyreadr for .rds, the csv module for HF), and compare every cell. Then test each fixture's claim."""
import ast, csv, hashlib, re, sys, warnings
from pathlib import Path
import pandas as pd, pyarrow.parquet as pq, pyreadr
warnings.simplefilter("ignore")
fx, assets = Path(sys.argv[1]), Path(sys.argv[2])
rows = [l for l in (fx / "README.md").read_text().splitlines() if l.startswith("| `") and ".parquet" in l]
print("README fixture rows:", len(rows), "| parquet files:", len(list(fx.glob("*.parquet"))))
cache = {}; bad = cells = 0
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None
for l in rows:
    c = [x.strip() for x in l.strip("|").split(" | ")]
    name, src, sha, filt, n = c[0].strip("`"), c[1].strip("`"), c[2].strip("`"), c[3], int(c[4])
    assert hashlib.sha256((assets / src).read_bytes()).hexdigest() == sha, src
    conds = [(a, ast.literal_eval(b)) for a, b in re.findall(r"`(\w+) == (.+?)`", filt)]
    if src not in cache:
        cache[src] = next(iter(pyreadr.read_r(str(assets / src)).values())) if src.endswith(".rds") else pd.DataFrame(list(csv.DictReader(open(assets / src, encoding="utf8"))))
    d = cache[src]; m = pd.Series(True, index=d.index)
    for col, val in conds:
        m &= (d[col].astype(str) == str(val)) if isinstance(val, str) else (pd.to_numeric(d[col], errors="coerce") == val)
    want = d[m].reset_index(drop=True); got = pq.read_table(fx / name).to_pandas().reset_index(drop=True)
    diffs = 0
    assert list(want.columns) == list(got.columns), name
    for col in got.columns:
        for a, b in zip(want[col], got[col]):
            cells += 1
            na, nb = (pd.isna(a) or a == ""), pd.isna(b)
            if na and nb: continue
            x, y = num(a), num(b)
            if x is not None and y is not None:
                if abs(x - y) > 1e-9 * max(1, abs(x)): diffs += 1
            elif str(a) != str(b): diffs += 1
    ok = len(want) == len(got) == n and diffs == 0; bad += not ok
    print(f"{name}: source rows {len(want)} fixture rows {len(got)} README {n} cell diffs {diffs} {'OK' if ok else 'FAIL'}")
print("fixtures failing:", bad, "| cells compared:", cells)
r = lambda n: pq.read_table(fx / n).to_pandas()
PAS = "_M_1st_passing_player_advanced_match_stats.parquet"
print("\nclaims")
a, b = r("league_move__epl_shot_data.parquet"), r("league_move__ligue_1_shot_data.parquet")
print("league_move: same player_id", set(a.player_id) == set(b.player_id), "| Ligue 1 last", b.date.max(), "before EPL first", a.date.min(), b.date.max() < a.date.min())
h = r("league_move__understat_xg_data.parquet"); print("  HF", h[["league", "team", "minutes", "shots"]].to_dict("records"))
for lg in ("ENG", "FRA"):
    p = r(f"league_move__{lg}{PAS}"); print(" ", lg, "FBref minutes", int(pd.to_numeric(p.Min).sum()), "labels", sorted(set(p.Pos)))
e = r("substitute__ESP_M_1st_match_summary.parquet"); p = r(f"substitute__ESP{PAS}")
sb = e[e.Event_Type == "Substitute"]; print("substitute: event rows", len(e), "| Substitute rows", len(sb), "| sample", sb.Event_Players.iloc[0], "| player rows", len(p), "| 'Sub' in Pos", int((p.Pos == "Sub").sum()))
inc = {v.split(" for ")[0].strip() for v in sb.Event_Players}; print("  incoming in player rows", len(inc & set(p.Player)), "of", len(inc), "| minutes of incoming, max", int(pd.to_numeric(p[p.Player.isin(inc)].Min).max()), "| non-subs by team", p[~p.Player.isin(inc)].groupby("Team").size().to_dict())
s = r("own_goal__la_liga_shot_data.parquet"); e = r("own_goal__ESP_M_1st_match_summary.parquet")
print("own_goal: OwnGoal shot rows", s[s.result == "OwnGoal"][["player", "minute", "home_team", "away_team"]].to_dict("records"), "| Own Goal events", e[e.Event_Type == "Own Goal"][["Event_Players", "Event_Time", "Team"]].to_dict("records"))
p = r(f"under_900__GER{PAS}"); h = r("under_900__understat_xg_data.parquet"); s = r("under_900__bundesliga_shot_data.parquet")
print("under_900: FBref minutes", int(pd.to_numeric(p.Min).sum()), "| HF minutes", int(h.minutes.iloc[0]), "| shots", len(s), "| labels", sorted(set(p.Pos)))
p = r(f"multi_position__ENG{PAS}"); print("multi_position: 'FW,LW' rows", int((p.Pos == "FW,LW").sum()), "| labels", p.Pos.value_counts().to_dict(), "| minutes", int(pd.to_numeric(p.Min).sum()))
p = r(f"lm_rm_only__ENG{PAS}"); print("lm_rm_only: labels", p.Pos.value_counts().to_dict(), "| minutes", int(pd.to_numeric(p.Min).sum()))
s = r("html_entity__epl_shot_data.parquet"); h = r("html_entity__understat_xg_data.parquet"); p = r(f"html_entity__ENG{PAS}")
print("html_entity: shot", repr(s.player.iloc[0]), "| HF", repr(h.player_name.iloc[0]), "| FBref", repr(p.Player.iloc[0]))
s = r("shared_name__la_liga_shot_data.parquet"); p = r(f"shared_name__ESP{PAS}"); h = r("shared_name__understat_xg_data.parquet")
print("shared_name: player_id", s.groupby("player_id").size().to_dict(), "| hrefs", p.groupby("Player_Href").size().to_dict(), "| HF", h[["team", "minutes", "shots"]].to_dict("records"))
s = r("current_season__bundesliga_shot_data.parquet"); p = r(f"current_season__GER{PAS}")
print("current_season: shot season", set(s.season), "dates", s.date.min(), s.date.max(), "| FBref year", set(p.Season_End_Year), "minutes", p.Min.tolist(), "Pos", p.Pos.tolist())
for f in sorted(fx.glob("*.parquet")):
    t = pq.read_schema(f); assert b"pandas" in t.metadata
print("largest file bytes:", max(f.stat().st_size for f in fx.iterdir()), "| over 1 MB:", sum(f.stat().st_size >= 1_000_000 for f in fx.iterdir()))
```

</details>

<details><summary><code>check_release.py</code></summary>

```python
"""Hash each downloaded release asset. Compare with the release notes table, GitHub's digest, and the local original."""
import hashlib, json, re, sys
from pathlib import Path
rel = json.load(open(sys.argv[1])); folder = Path(sys.argv[2]); originals = {Path(l).name: Path(l) for l in Path(sys.argv[3]).read_text().splitlines()}
notes = {m[0]: (int(m[1]), m[2]) for m in re.findall(r"^\| (\S+) \| (\d+) \| `([0-9a-f]{64})` \|", rel["body"], re.M)}
assets = {a["name"]: a for a in rel["assets"]}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(2**20): h.update(b)
    return h.hexdigest()
bad = 0
print("names: notes", len(notes), "assets", len(assets), "on disk", len(list(folder.iterdir())), "only notes", sorted(set(notes) - set(assets)), "only assets", sorted(set(assets) - set(notes)))
for name in sorted(set(notes) | set(assets)):
    p = folder / name
    got = sha(p) if p.exists() else None
    size, want = notes.get(name, (None, None))
    ok_notes, ok_digest, ok_size = got == want, assets.get(name, {}).get("digest") == f"sha256:{got}", p.exists() and p.stat().st_size == size
    ok_local = name in originals and sha(originals[name]) == got
    bad += not (ok_notes and ok_digest and ok_size)
    print(f"{name}\t{size}\t{got}\tnotes {ok_notes}\tdigest {ok_digest}\tsize {ok_size}\tlocal_original {ok_local}")
print("mismatches", bad)
```

</details>

The `.rds` attributes, checked with `rdata.parser.parse_file`:

```
ESP_M_1st_match_summary.rds attribute names: [b'class', b'row.names', b'names', b'scrape_timestamp']
  object-kind columns holding non-scalars: [] | attrs []
epl_shot_data.rds attribute names: [b'names', b'class', b'row.names', b'scrape_timestamp']
  object-kind columns holding non-scalars: [] | attrs []
GER_M_1st_passing_player_advanced_match_stats.rds attribute names: [b'class', b'row.names', b'names', b'scrape_timestamp']
  object-kind columns holding non-scalars: [] | attrs []
```
