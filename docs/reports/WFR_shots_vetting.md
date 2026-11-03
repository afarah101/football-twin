# worldfootballR_data vetting: pre-scraped Understat shot rows

Run date: 2026-11-03. Source: GitHub repo `JaseZiv/worldfootballR_data`, release `understat_shots`. There is no commit to pin for release assets, so the files are pinned by the SHA-256 values in Task 2.

**Mode used: NAMES-ONLY.** `config/face_validity_pairs.yaml` is not committed, so this report holds column names, category labels, counts, dates and agreement rates only. It holds no player names and no player values.

One exception needs your review. To test whether fields can be derived, the scripts added up shots, xG and key passes per player in memory, then compared them with the Hugging Face (HF) file. Only the number of agreeing rows was printed, and no per-player total was saved or shown. The report also shows counts by season and league, and league-wide X/Y quartiles, which describe no player.

## Verdict

| Use | Verdict | Reason |
|---|---|---|
| (a) Shot profile | **YES, as a temporary stand-in** | X/Y, `lastAction`, `situation`, `shotType` and `result` are present for all five leagues, 2014/15 to 2024/25, with 0 nulls. Limits: Serie A 2024/25 lacks 6 matches, and the file will not be updated again. |
| (b) Output metrics, combined with HF | **YES, for 2015/16 to 2024/25 only** | Minutes and xGBuildup come from HF, and everything else is present or rebuilt from shots. Outside 2024/25, rebuilt shots, xA and npxG agree with HF on 99.92% of joined keys. There are no HF minutes for 2014/15. |
| (c) Positions | **NO** | No file column holds a position and no Understat file in the repo holds rosters. HF has only broad labels. |

**The Phase 1 method still cannot run as written.** All 10 metrics now have a source, but the Pool rule (Q5 and the FW, FWL, FWR, AML, AMC, AMR list) has none. Choosing a stand-in for positions, or waiting for Understat, is Ahmed's decision. This report does not make it.

**Outside check and its limit.** The check is agreement between two separately published copies of Understat data. That shows they match each other. It does not show that either matches Understat today, because the site could not be reached.

## Findings

| Severity | Finding | Evidence |
|---|---|---|
| **Critical** | No per-match or per-player position, so the Pool rule cannot be applied. Attacking midfielders cannot be separated from other midfielders. | Task 6 |
| Warning | The repo is archived and the files stop at matches on 2025-09-15. They cannot support the current-season search (Q7), the Monday job (Q25, Q28) or new seasons. Season 2025 holds only 27 to 41 matches per league. | Tasks 1, 3 |
| Warning | Serie A 2024/25 has 374 of 380 matches. On its 522 joined keys, rebuilt shots are below HF on 95 and above on 0, which fits the missing matches. This matters because Q10 reports the self-match rate on seasons after 2023/24, and 2024/25 is the only complete one. | Tasks 3, 5 |
| Warning | Combining with HF removes 2014/15, because HF starts at 2015. The 45,721 shot rows from that season have no minutes and no xGBuildup, so the season cannot enter the Pool. | Tasks 3, 5 |
| Warning | No licence. The repo reports `licenseInfo: null`, has no licence file, and its README states no terms. Q3 and Q18 stay open. The README credits a third party's data dump for 2014/15 to 2021/22, so those seasons were not scraped by this repo's own job. | Task 1 |
| Warning | These files are not "real Understat responses recorded during STEP 0", which the plan requires of all test fixtures. Using them as fixtures would need a decision. | Plan, Decisions |
| Warning | `Throughball` counts fall in two seasons: 714 in 2019 and 579 in 2020, against 928 to 1,034 in the other full seasons. In 2020, every league is below its own 2018 and 2021 counts. It is one of the 10 metrics. The cause is unknown, and HF has no column to test it. Z-scoring within league-season would reduce this but may not remove it, and it could affect self-match across those seasons. | Task 4 |
| Warning | Rebuilt key passes are only approximate. At 900+ minutes, 1,209 of 15,399 keys differ, mostly with HF higher by 1 (1,000 keys). Rank correlation per season is at least 0.9995. xA still agrees on 1,146 of those 1,209, so these extra key passes carry little or no xG. The cause is unknown. Use HF `key_passes`, not the rebuilt count, where HF exists. | Task 5 |
| Warning | HF has no player id, so the join uses names. 42 (name, season, league) keys in the shot file hold several `player_id` values, covering 1,836 shot rows, and the join cannot separate them. For this test, HF rows sharing a key were summed. One name is spelled differently in the two files on 9 keys (304 shot rows), and removing accents does not fix it. | Tasks 5, 7 |
| Info | Shot counts on EPL 2024/25 all match HF, yet 17 of its keys differ on xA by more than 0.05, all below HF. That suggests xG values changed between the two snapshots. It is an inference, since names-only mode rules out looking at rows. | Task 5 |
| Info | This settles a question left open in the HF report: HF `shots` keeps penalties and leaves out own goals. Counting that way matches HF on 99.51% of keys, against 93.71% with own goals counted. | Task 5 |
| Info | Five 2014/15 matches have fewer goal rows than their scoreline. The other 19,997 of 20,002 matches agree. | Task 7 |
| Info | 98 rows repeat the same match, player, minute, X and Y under a different `id`, and 39 of them also repeat the result. They were not removed. The cause is unknown. | Task 7 |
| Info | 117 non-own-goal rows have xG of exactly 0. One row has Y of exactly 0. No X or Y falls outside 0 to 1. | Task 7 |
| Info | The file changes format at season 2022. `h_a` becomes `home_away` and labels such as `Serie_A` become `Serie A`. Exactly one of the two columns is filled on every row, and there is no team column. A loader must merge them and take the league from the file name. | Tasks 3, 4 |
| Info | Names hold HTML entities on 2,308 `player` cells and 1,586 `player_assisted` cells. HF has 148 such keys. Unescape names before joining. | Task 5 |
| Info | The exact labels the plan relies on all exist: `TakeOn`, `Throughball`, `Head`, `Penalty`, `OwnGoal`. | Task 4 |
| Info | The repo also holds smaller files with the same names at `data/understat_shots/` (about 2 MB each, last changed 2025-01-05). They were not opened. This report uses the release files. | Task 1 |
| Info | Security result is clean for the data. Semgrep made 1 finding in `pyreadr`, on a URL helper that my scripts never call. | Task 2 |

## Step 0

```
$ pwd
/Users/ahmed.farah/Projects/football-twin
$ git status -sb
## main...origin/main
?? config/
$ git log --oneline -- config/
(no output: never committed)
$ wc -c config/face_validity_pairs.yaml
       0 config/face_validity_pairs.yaml
```

Hard rules from `CLAUDE.md`: no distance code runs and no metric output is produced or shown until Ahmed has committed `config/face_validity_pairs.yaml`, and nobody else suggests, drafts or edits the pairs. No distance code ran here. The file remains empty and untouched.

The 12 fields the plan needs (`docs/phase-1-plan.md`, Data, Metrics, Pool rules, Decisions):

- Player-season (8): time, shots, npg, npxG, xA, key_passes, xGBuildup, position.
- Shot rows (4): location X/Y, lastAction, situation, shotType.
- Also named in the plan, outside the 12: shot `result` and per-match position from match rosters.

What HF already covers, from `docs/reports/HF_dataset_vetting.md`: time, shots, npxG, xA, key_passes and xGBuildup are present, and npg is derivable through an FBref join. Position and all four shot-row fields are missing. HF covers 2015-16 to 2024-25, with no player id.

## Task 1: locate the files

```
$ gh repo view JaseZiv/worldfootballR_data --json owner,name,description,licenseInfo,isArchived,pushedAt,stargazerCount
{"description":"Project holding various data for the worldfootballR R package","isArchived":true,"licenseInfo":null,"name":"worldfootballR_data","owner":{"id":"MDQ6VXNlcjMxNDcxNzgz","login":"JaseZiv"},"pushedAt":"2025-09-18T19:54:58Z","stargazerCount":81}

$ gh release list -R JaseZiv/worldfootballR_data --limit 100
fb_match_summary	Latest	fb_match_summary	2023-09-03T10:00:07Z
fb_advanced_match_stats		fb_advanced_match_stats	2023-09-02T18:32:41Z
old_fb_big5_advanced_season_stats		old_fb_big5_advanced_season_stats	2023-02-16T12:50:31Z
old_fb_match_shooting		old_fb_match_shooting	2023-02-15T20:37:48Z
fb_match_shooting		fb_match_shooting	2023-01-26T14:39:29Z
understat_shots		understat_shots	2022-11-03T19:33:14Z
match_results_cups		match_results_cups	2022-11-02T10:20:59Z
match_results		match_results	2022-11-02T08:59:20Z
fb_big5_advanced_season_stats		fb_big5_advanced_season_stats	2022-11-02T01:39:23Z
fotmob_match_details		fotmob_match_details	2022-10-15T14:20:26Z
fotmob_matches_by_date		fotmob_matches_by_date	2022-10-15T13:54:40Z

$ gh release view understat_shots -R JaseZiv/worldfootballR_data --json tagName,publishedAt,assets --jq ...
understat_shots
2022-11-03T19:33:14Z
bundesliga_shot_data.rds 25319943 2025-09-18T18:43:39Z sha256:7481d4eea7a32c261ae45711e735a074c23aa4530a181c7f3c490150e8639bee
epl_shot_data.rds 29646577 2025-09-18T18:43:31Z sha256:c51e6661029a2b0f2b770bd9fc0a54da1913b303d6c6c908d11008f5c526ab60
la_liga_shot_data.rds 27526464 2025-09-18T18:43:36Z sha256:1a3a80f5e42c797ad056cb38fa10ca7c27b11f90987ee1921347eeba0728a803
ligue_1_shot_data.rds 26342221 2025-09-18T18:43:47Z sha256:bbc5bc4e6f0ffc94f01ec016e4df45dc6d53264f92c917e113c0c5b9ecdbc49a
rfpl_shot_data.rds 19133380 2025-09-18T18:43:51Z sha256:5ce54bf53ec86195b034fee6caae5cb283e98f019c364634fdf983fd67719901
serie_a_shot_data.rds 30103636 2025-09-18T18:43:43Z sha256:fb024cc8fc8aa72edf6b826629ffe1f36dc3f2e20645f3aade85a4f2ec36b559

$ gh api repos/JaseZiv/worldfootballR_data/git/trees/HEAD?recursive=1 --jq (paths matching understat)
blob .github/workflows/automated_understat_shots.yml 1593
tree R/understat_league_shots 
blob R/understat_league_shots/backup_understat_local.R 778
blob R/understat_league_shots/update_understat_shots.R 3900
tree data/understat_shots 
blob data/understat_shots/bundesliga_shot_data.rds 1815901
blob data/understat_shots/epl_shot_data.rds 2211252
blob data/understat_shots/la_liga_shot_data.rds 2077614
blob data/understat_shots/ligue_1_shot_data.rds 2009561
blob data/understat_shots/rfpl_shot_data.rds 1399523
blob data/understat_shots/serie_a_shot_data.rds 2290583

$ gh api repos/JaseZiv/worldfootballR_data/git/trees/HEAD?recursive=1 --jq (paths matching licen[cs]e|copying)
(end of list)

$ gh api repos/JaseZiv/worldfootballR_data/commits?per_page=1 --jq ...
2df143967509ff45584e261a2a033687346d654b 2025-09-18T19:54:57Z Archive package

$ gh api repos/JaseZiv/worldfootballR_data/commits?path=data/understat_shots&per_page=1 --jq ...
ab98278d27256d2eedc36312af4e93b39143a736 2025-01-05T03:50:09Z reinstate EPL and update local backups

$ gh api repos/JaseZiv/worldfootballR_data/contents/README.md --jq .content | base64 -d > README; grep -ciE "licen[cs]e|terms" README
0
$ grep -o "original data dump of the seasons for all big 5 leagues from 2014/15 to 2021/22" README
original data dump of the seasons for all big 5 leagues from 2014/15 to 2021/22
```

| Item | Value |
|---|---|
| Release tag | `understat_shots`, published 2022-11-03 |
| Format | `.rds`, one file per league. A sixth file, `rfpl_shot_data.rds`, is out of scope and was not downloaded. |
| Five-league size | 138,938,841 bytes |
| Last updated | Assets 2025-09-18. Repo archived the same day, with the commit "Archive package". |
| Licence | None found |

## Task 2: download and security

Downloaded to `~/sandbox/wfr/files`. All five hashes match the digests GitHub reports in Task 1.

```
$ cd ~/sandbox/wfr/files; for f in bundesliga epl la_liga ligue_1 serie_a; do gh release download understat_shots -R JaseZiv/worldfootballR_data -p "${f}_shot_data.rds"; done
$ wc -c *.rds
 25319943 bundesliga_shot_data.rds
 29646577 epl_shot_data.rds
 27526464 la_liga_shot_data.rds
 26342221 ligue_1_shot_data.rds
 30103636 serie_a_shot_data.rds
 138938841 total
$ shasum -a 256 *.rds
7481d4eea7a32c261ae45711e735a074c23aa4530a181c7f3c490150e8639bee  bundesliga_shot_data.rds
c51e6661029a2b0f2b770bd9fc0a54da1913b303d6c6c908d11008f5c526ab60  epl_shot_data.rds
1a3a80f5e42c797ad056cb38fa10ca7c27b11f90987ee1921347eeba0728a803  la_liga_shot_data.rds
bbc5bc4e6f0ffc94f01ec016e4df45dc6d53264f92c917e113c0c5b9ecdbc49a  ligue_1_shot_data.rds
fb024cc8fc8aa72edf6b826629ffe1f36dc3f2e20645f3aade85a4f2ec36b559  serie_a_shot_data.rds
$ head -c 6 <file> | xxd -p  (58 0a = uncompressed XDR, 00000002 = format version 2)
bundesliga_shot_data.rds 580a00000002
epl_shot_data.rds 580a00000002
la_liga_shot_data.rds 580a00000002
ligue_1_shot_data.rds 580a00000002
serie_a_shot_data.rds 580a00000002
```

`file` calls these plain "data". They are R serialized objects, and R objects can carry code, so reading them with a library is not proof that they are safe. `tools/rds_walk.py` walks the raw bytes without R and refuses any type that can hold or reach code: closures, language objects, promises, environments, bytecode, external pointers, and namespace or package references.

```
$ venv/bin/python3 -I tools/rds_walk.py files/*.rds
bundesliga_shot_data.rds: bytes=25319943 format_version=2 consumed=25319943 trailing=0 types={'CHAR': 1058612, 'INT': 10, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 11, 'REF': 2, 'STR': 18, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
epl_shot_data.rds: bytes=29646577 format_version=2 consumed=29646577 trailing=0 types={'CHAR': 1294100, 'INT': 10, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 11, 'REF': 2, 'STR': 18, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
la_liga_shot_data.rds: bytes=27526464 format_version=2 consumed=27526464 trailing=0 types={'CHAR': 1202300, 'INT': 10, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 11, 'REF': 2, 'STR': 18, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ligue_1_shot_data.rds: bytes=26342221 format_version=2 consumed=26342221 trailing=0 types={'CHAR': 1153724, 'INT': 10, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 11, 'REF': 2, 'STR': 18, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
serie_a_shot_data.rds: bytes=30103636 format_version=2 consumed=30103636 trailing=0 types={'CHAR': 1320356, 'INT': 10, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 11, 'REF': 2, 'STR': 18, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
```

Each file was read to its last byte (`trailing=0`), and only data types appear, so all five are data-only. Positive control, using hand-built files that must be refused, plus one plain vector that must pass:

```
closure: exit=1 closure.rds: CODE TYPE FOUND: CLOSURE
language: exit=1 language.rds: CODE TYPE FOUND: LANG
bytecode: exit=1 bytecode.rds: CODE TYPE FOUND: BYTECODE
environment: exit=1 environment.rds: CODE TYPE FOUND: ENV
plain int vector: exit=0 plain_int_vector.rds: bytes=30 format_version=2 consumed=30 trailing=0 types={'INT': 1} CODE_TYPES=0
```

Text cells were also checked, with counts in the first block of the `derive.py` output: 0 cells start with `=`, `+`, `@` or `-`, and 0 hold a URL or `<script`.

Reader and scanners, with `pip install --only-binary :all:` into a sandbox venv so no build scripts ran:

```
$ venv/bin/pip freeze
narwhals==2.28.0
numpy==2.5.4
pandas==3.1.0
pyreadr==0.5.9
python-dateutil==4.0.0
tzdata==2026.6

$ osv-scanner scan --lockfile requirements.txt:out/requirements.txt
End status: 0 dirs visited, 1 inodes visited, 1 Extract calls, 1.431ms elapsed, 1.431ms wall time

No issues found

$ gitleaks dir files --no-banner --no-color
INF scanned ~138938841 bytes (138.94 MB) in 4.95s
INF no leaks found

$ semgrep --config auto --quiet venv/lib/python*/site-packages/pyreadr
│ 1 Code Finding │
    venv/lib/python3.15/site-packages/pyreadr/pyreadr.py
    ❯❱ python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
          262┆ response = urlopen(url)

$ grep -n "download_file\|urlopen" tools/*.py   (does my code call the flagged helper?)
grep exit=1 (1 = no match)
```

The Semgrep finding is on `pyreadr.download_file`. My scripts call only `read_r` on local paths, and they make no network calls.

## Tasks 3, 4, 6, 7: profile

Coverage is Task 3, columns and categories are Task 4, position-like columns are Task 6 and integrity is Task 7.

```
$ venv/bin/python3 -I tools/profile.py files
epl: rows=107838 cols=22
la_liga: rows=100188 cols=22
bundesliga: rows=88214 cols=22
serie_a: rows=110026 cols=22
ligue_1: rows=96140 cols=22

=== columns per file identical: True
epl ['league', 'id', 'minute', 'result', 'X', 'Y', 'xG', 'player', 'h_a', 'player_id', 'situation', 'season', 'shotType', 'match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date', 'player_assisted', 'lastAction', 'home_away']
la_liga ['league', 'id', 'minute', 'result', 'X', 'Y', 'xG', 'player', 'h_a', 'player_id', 'situation', 'season', 'shotType', 'match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date', 'player_assisted', 'lastAction', 'home_away']
bundesliga ['league', 'id', 'minute', 'result', 'X', 'Y', 'xG', 'player', 'h_a', 'player_id', 'situation', 'season', 'shotType', 'match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date', 'player_assisted', 'lastAction', 'home_away']
serie_a ['league', 'id', 'minute', 'result', 'X', 'Y', 'xG', 'player', 'h_a', 'player_id', 'situation', 'season', 'shotType', 'match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date', 'player_assisted', 'lastAction', 'home_away']
ligue_1 ['league', 'id', 'minute', 'result', 'X', 'Y', 'xG', 'player', 'h_a', 'player_id', 'situation', 'season', 'shotType', 'match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date', 'player_assisted', 'lastAction', 'home_away']

=== dtypes
_file                  str
league                 str
id                 float64
minute             float64
result                 str
X                  float64
Y                  float64
xG                 float64
player                 str
h_a                    str
player_id          float64
situation              str
season             float64
shotType               str
match_id           float64
home_team              str
away_team              str
home_goals         float64
away_goals         float64
date                   str
player_assisted        str
lastAction             str
home_away              str

=== position-like columns: []

=== nulls per column (all files)
_file                   0
league                  0
id                      0
minute                  0
result                  0
X                       0
Y                       0
xG                      0
player                  0
h_a                139625
player_id               0
situation               0
season                  0
shotType                0
match_id                0
home_team               0
away_team               0
home_goals              0
away_goals              0
date                    0
player_assisted    132795
lastAction              0
home_away          362781

=== blank strings per text column
_file 0
league 0
result 0
player 0
h_a 0
situation 0
shotType 0
home_team 0
away_team 0
date 0
player_assisted 0
lastAction 0
home_away 0

=== league: distinct=8
league
EPL           107838
Bundesliga     88214
Serie_A        80802
La_liga        71450
Ligue_1        70416
Serie A        29224
La liga        28738
Ligue 1        25724

=== h_a: distinct=3
h_a
h      199217
a      163564
NaN    139625

=== situation: distinct=5
situation
OpenPlay          367276
FromCorner         76256
SetPiece           32247
DirectFreekick     20357
Penalty             6270

=== shotType: distinct=4
shotType
RightFoot        254429
LeftFoot         159845
Head              86060
OtherBodyPart      2072

=== lastAction: distinct=41
lastAction
Pass               178832
Cross               70665
None                59088
Aerial              38676
Standard            26627
TakeOn              25240
Chipped             24981
Rebound             22377
BallRecovery        12002
HeadPass            11780
Throughball         10153
BallTouch            9339
LayOff               4009
Dispossessed         2714
Tackle               1153
Foul                  919
CornerAwarded         881
BlockedPass           668
Interception          491
Goal                  357
End                   346
Challenge             228
Clearance             211
OffsidePass           142
Card                  127
Save                  101
GoodSkill              85
SubstitutionOn         79
OffsideProvoked        27
KeeperPickup           26
FormationChange        23
Start                  16
Error                  14
Punch                   7
ShieldBallOpp           6
ChanceMissed            5
KeeperSweeper           4
PenaltyFaced            3
CrossNotClaimed         2
SubstitutionOff         1
Smother                 1

=== result: distinct=6
result
MissedShots    192120
BlockedShot    128473
SavedShot      116763
Goal            53720
ShotOnPost       9684
OwnGoal          1646

=== result by file
result      BlockedShot   Goal  MissedShots  OwnGoal  SavedShot  ShotOnPost
_file                                                                      
bundesliga        21825  10019        33446      264      20942        1718
epl               30613  11420        38766      406      24635        1998
la_liga           23968  10782        39450      303      23637        2048
ligue_1           23374  10297        37547      327      22764        1831
serie_a           28693  11202        42911      346      24785        2089

=== season or date not parsed: 0 0

=== coverage per file
bundesliga: first_season=2014 last_season=2025 seasons=12 first_date=2014-08-22 19:30:00 latest_date=2025-09-14 15:30:00 rows=88214 matches=3391
epl: first_season=2014 last_season=2025 seasons=12 first_date=2014-08-16 12:45:00 latest_date=2025-09-14 15:30:00 rows=107838 matches=4220
la_liga: first_season=2014 last_season=2025 seasons=12 first_date=2014-08-23 18:00:00 latest_date=2025-09-15 19:00:00 rows=100188 matches=4221
ligue_1: first_season=2014 last_season=2025 seasons=12 first_date=2014-08-08 19:30:00 latest_date=2025-09-14 18:45:00 rows=96140 matches=3966
serie_a: first_season=2014 last_season=2025 seasons=12 first_date=2014-08-30 17:00:00 latest_date=2025-09-15 18:45:00 rows=110026 matches=4204

=== rows per season
_file    bundesliga    epl  la_liga  ligue_1  serie_a
_season                                              
2014           7986   9914     9046     8696    10079
2015           7915   9819     9082     8808     9849
2016           7646   9760     9162     9164    10146
2017           7737   9287     9174     9467     9794
2018           8264   9661     9273     9416    10587
2019           8148   9427     8604     6812    10898
2020           7590   9235     8132     8921     9517
2021           7949   9775     8977     9132     9932
2022           7815   9644     9374     9345     9675
2023           8506  10524     9311     7827     9728
2024           7945   9878     9056     7647     9066
2025            713    914      997      905      755

=== matches per season
_file    bundesliga  epl  la_liga  ligue_1  serie_a
_season                                            
2014.0          305  380      380      380      380
2015.0          306  380      380      380      380
2016.0          306  380      380      379      380
2017.0          306  380      380      380      380
2018.0          306  380      380      380      380
2019.0          306  380      380      279      380
2020.0          306  380      380      380      380
2021.0          306  380      380      380      380
2022.0          306  380      380      380      380
2023.0          306  380      380      306      380
2024.0          305  380      380      306      374
2025.0           27   40       41       36       30

=== latest match date per season
_file    bundesliga         epl     la_liga     ligue_1     serie_a
_season                                                            
2014.0   2015-05-23  2015-05-24  2015-05-23  2015-05-23  2015-05-31
2015.0   2016-05-14  2016-05-17  2016-05-15  2016-05-14  2016-05-15
2016.0   2017-05-20  2017-05-21  2017-05-21  2017-05-20  2017-05-28
2017.0   2018-05-12  2018-05-13  2018-05-20  2018-05-19  2018-05-20
2018.0   2019-05-18  2019-05-12  2019-05-19  2019-05-24  2019-05-26
2019.0   2020-06-27  2020-07-26  2020-07-19  2020-03-08  2020-08-02
2020.0   2021-05-22  2021-05-23  2021-05-23  2021-05-23  2021-05-23
2021.0   2022-05-14  2022-05-22  2022-05-22  2022-05-21  2022-05-22
2022.0   2023-05-27  2023-05-28  2023-06-04  2023-06-03  2023-06-04
2023.0   2024-05-18  2024-05-19  2024-05-26  2024-05-19  2024-06-02
2024.0   2025-05-17  2025-05-25  2025-05-25  2025-05-17  2025-05-24
2025.0   2025-09-14  2025-09-14  2025-09-15  2025-09-14  2025-09-15

=== integrity
bundesliga: exact duplicate rows=0 duplicate id=0
epl: exact duplicate rows=0 duplicate id=0
la_liga: exact duplicate rows=0 duplicate id=0
ligue_1: exact duplicate rows=0 duplicate id=0
serie_a: exact duplicate rows=0 duplicate id=0
all files: exact duplicate rows 0 | duplicate id 0
rows sharing an id: 0 | ids with differing data: 0
match_id in more than one file: 0
X: not numeric=0 <0=0 >1=0 exactly0=0 exactly1=0
Y: not numeric=0 <0=0 >1=0 exactly0=1 exactly1=0
xG: not numeric=0 <0=0 >1=0 exactly0=1763 exactly1=0
own goals (result=OwnGoal): 1646
penalties (situation=Penalty): 6270
rows with player_assisted filled: 369611 | filled and lastAction != None: 367134
player_id null: 0
rows with assister == shooter: 3
```

```
$ venv/bin/python3 -I tools/derive.py files ~/sandbox/hf_dump/files/data/understat_xg/understat_xg_data.csv
=== text cell safety (counts, all text columns)
starts = + @ {}
starts - {}
http {}
<script {}
html entity {'player': 2308, 'player_assisted': 1586}

=== schema eras: rows with h_a filled / home_away filled, by season
          h_a  home_away
season                  
2014    45721          0
2015    45473          0
2016    45878          0
2017    45459          0
2018    47201          0
2019    43889          0
2020    43395          0
2021    45765          0
2022        0      45853
2023        0      45896
2024        0      43592
2025        0       4284
rows with both filled: 0 | neither: 0
home_away values: {'h': 76747, 'a': 62878}

=== league label by season
league  Bundesliga    EPL  La liga  La_liga  Ligue 1  Ligue_1  Serie A  Serie_A
season                                                                         
2014          7986   9914        0     9046        0     8696        0    10079
2015          7915   9819        0     9082        0     8808        0     9849
2016          7646   9760        0     9162        0     9164        0    10146
2017          7737   9287        0     9174        0     9467        0     9794
2018          8264   9661        0     9273        0     9416        0    10587
2019          8148   9427        0     8604        0     6812        0    10898
2020          7590   9235        0     8132        0     8921        0     9517
2021          7949   9775        0     8977        0     9132        0     9932
2022          7815   9644     9374        0     9345        0     9675        0
2023          8506  10524     9311        0     7827        0     9728        0
2024          7945   9878     9056        0     7647        0     9066        0
2025           713    914      997        0      905        0      755        0

=== category stability: counts by season
lastAction  TakeOn  Throughball  None   Pass  Cross
season                                             
2014          2675         1034  5513  15705   6645
2015          2639         1019  5293  16101   6801
2016          2496          946  5357  16033   6879
2017          2512          953  5271  16078   6344
2018          2278          984  5391  16820   6029
2019          2245          714  4962  15900   5831
2020          2026          579  5076  15718   6202
2021          2044          928  5601  16336   6458
2022          1998          997  5511  16395   6544
2023          2165          938  5476  16466   6418
2024          1968          966  5119  15756   5956
2025           194           95   518   1524    558
shotType  Head  LeftFoot  OtherBodyPart  RightFoot
season                                            
2014      7318     14113            148      24142
2015      7254     14245            147      23827
2016      7720     14360            153      23645
2017      7587     14602            171      23099
2018      8305     15020            215      23661
2019      7405     13895            206      22383
2020      7728     13741            204      21722
2021      7944     14451            215      23155
2022      8124     14852            217      22660
2023      8146     15019            208      22523
2024      7742     14185            173      21492
2025       787      1362             15       2120
situation  DirectFreekick  FromCorner  OpenPlay  Penalty  SetPiece
season                                                            
2014                 2366        6201     33502      511      3141
2015                 2230        6378     33285      487      3093
2016                 2244        6711     33214      587      3122
2017                 2028        6602     33353      541      2935
2018                 1928        7143     34557      585      2988
2019                 1902        6700     31916      589      2782
2020                 1753        6528     31563      688      2863
2021                 1610        7336     33300      583      2936
2022                 1522        7421     33635      573      2702
2023                 1414        7542     33581      550      2809
2024                 1243        6958     32260      511      2620
2025                  117         736      3110       65       256
distinct lastAction by season: {2014: 35, 2015: 36, 2016: 36, 2017: 33, 2018: 34, 2019: 35, 2020: 34, 2021: 32, 2022: 32, 2023: 34, 2024: 35, 2025: 29}

=== X and Y scale by season (league-wide quartiles, not player values)
            X                    Y              
         0.25   0.50   0.75   0.25   0.50   0.75
season                                          
2014    0.773  0.857  0.906  0.410  0.503  0.599
2015    0.777  0.860  0.907  0.410  0.501  0.598
2016    0.781  0.862  0.909  0.412  0.503  0.598
2017    0.778  0.861  0.907  0.412  0.501  0.596
2018    0.782  0.865  0.909  0.415  0.501  0.597
2019    0.785  0.865  0.910  0.416  0.502  0.597
2020    0.791  0.868  0.910  0.421  0.503  0.594
2021    0.791  0.868  0.912  0.418  0.501  0.593
2022    0.793  0.869  0.912  0.416  0.501  0.593
2023    0.796  0.869  0.912  0.417  0.501  0.591
2024    0.801  0.871  0.912  0.417  0.500  0.588
2025    0.793  0.870  0.913  0.415  0.500  0.588

=== integrity extras
same match, player, minute, X, Y (near duplicates): 98
matches: 20002 | goal rows match the scoreline: 19997 | differ: 5 | fewer goal rows than scoreline: 5
differ by season: {2014: 5}
differ by league: {'ESP': 1, 'FRA': 3, 'GER': 1}
minute: min 0.0 max 106.0

=== identity
(name, season, league) keys: 26016 | keys with more than one player_id: 42
distinct player_id: 7432 | player_id with more than one name: 1
rows with assister name holding html entity or not matching any shooter name: 858

hf seasons: 2015 2024 | hf rows 27182
hf keys: 27124
name spellings changed by html unescape: hf 148 | shots 2308

=== join on (name, season, league)
wfr keys, all seasons: 27639 | in hf seasons: 23777
in both: 23768 | hf only: 3356 | wfr only: 9
hf only, with shots > 0 or key_passes > 0: 9
hf rows with minutes >= 900: 16053 | of those in both: 15456 | of those hf only: 597
hf only at >= 900 minutes, with shots > 0: 5
wfr only: 9 | shot rows on them: 304 of 452401
wfr only by league: {'FRA': 5, 'GER': 4} | by season: {2015: 1, 2016: 1, 2017: 1, 2018: 1, 2019: 1, 2020: 1, 2021: 1, 2022: 1, 2023: 1}

=== rebuilt totals vs hf, on 23768 joined keys
shots incl own goals vs hf shots: same 22274 (93.71%) | differ 1494
shots excl own goals vs hf shots: same 23651 (99.51%) | differ 117
goals vs hf goals: same 23747 (99.91%) | differ 21
assists vs hf assists: same 23718 (99.79%) | differ 50
key passes incl own goals vs hf: same 22433 (94.38%) | differ 1335
key passes excl own goals vs hf: same 22433 (94.38%) | differ 1335
xG vs hf xG: within 0.01 23540 (99.04%) | outside 228
npxG vs hf npxG: within 0.01 23540 (99.04%) | outside 228
xA incl own goals vs hf xA: within 0.01 23573 (99.18%) | outside 195
xA excl own goals vs hf xA: within 0.01 23573 (99.18%) | outside 195
xG vs hf xG: within 0.05 23625 (99.40%) | outside 143
npxG vs hf npxG: within 0.05 23626 (99.40%) | outside 142
xA incl own goals vs hf xA: within 0.05 23648 (99.50%) | outside 120
xA excl own goals vs hf xA: within 0.05 23648 (99.50%) | outside 120

=== same checks at hf minutes >= 900
keys: 15456
shots incl own goals: same 14161 (91.62%) | differ 1295
key passes excl own goals: same 14247 (92.18%) | differ 1209
xA excl own goals: within 0.05 15348 (99.30%) | outside 108
npxG: within 0.05 15335 (99.22%) | outside 121

=== agreement rate by season, all joined keys
 season  keys  shots_same  kp_same  xA_0.05  npxG_0.05
   2015  2382      0.9387   0.8955   1.0000     1.0000
   2016  2365      0.9501   0.9235   1.0000     1.0000
   2017  2301      0.9405   0.9296   0.9970     0.9970
   2018  2281      0.9434   0.9294   1.0000     1.0000
   2019  2331      0.9438   0.9404   1.0000     1.0000
   2020  2380      0.9378   0.9660   0.9996     0.9996
   2021  2465      0.9404   0.9696   1.0000     1.0000
   2022  2440      0.9340   0.9721   1.0000     1.0000
   2023  2408      0.9385   0.9722   0.9967     0.9958
   2024  2415      0.9052   0.9371   0.9569     0.9487

=== agreement rate by league
league  keys  shots_same  kp_same  xA_0.05  npxG_0.05
   EPL  4695      0.9282   0.9410   0.9962     0.9949
   ESP  4942      0.9444   0.9478   0.9980     0.9976
   FRA  4828      0.9439   0.9530   0.9973     0.9979
   GER  4286      0.9461   0.9484   0.9977     0.9974
   ITA  5017      0.9243   0.9298   0.9862     0.9831

=== size of disagreement (counts only)
shots: rebuilt below hf 112 | above hf 1382
key passes: rebuilt below hf 1299 | above hf 36
wfr 2014 season keys with no hf row: 2325 | 2025 season keys with no hf row: 1537
non-penalty shot rows excl own goals: 494490 of 502406
```

`Throughball` split by league, for the dip in 2019 and 2020:

```
Throughball rows by season and file
f       bundesliga  epl  la_liga  ligue_1  serie_a
season                                            
2014           135  232      258      204      205
2015           106  250      236      227      200
2016           134  206      180      192      234
2017           115  199      225      241      173
2018           175  229      219      198      163
2019           136  188      142      103      145
2020            83  120      126      108      142
2021           153  212      182      203      178
2022           161  240      219      212      165
2023           185  237      211      166      139
2024           159  231      222      173      181
2025            15   15       26       24       15
```

```
$ venv/bin/python3 -I tools/supplement.py files ~/sandbox/hf_dump/files/data/understat_xg/understat_xg_data.csv
=== xG exactly 0, by result
result
OwnGoal        1646
MissedShots      46
BlockedShot      30
SavedShot        27
Goal             11
ShotOnPost        3
rows equal on every column except id: 0
near duplicates on ['match_id', 'player_id', 'minute', 'X', 'Y'] : 98 | same result too: 39 | by season: {2014: 11, 2015: 10, 2016: 7, 2017: 15, 2018: 7, 2019: 14, 2020: 6, 2021: 6, 2022: 8, 2023: 7, 2024: 6, 2025: 1}
(name, season, league) keys with several player_ids, after unescape: 42 | shot rows on them: 1836

joined keys: 23684

=== shots excl own goals (penalties kept), xA and npxG agreement, season x league, seasons 2023 and 2024
                      keys  shots_same  kp_same  xA_0.05  npxG_0.05
season_start league                                                
2023         EPL     485.0      1.0000   0.9691   1.0000     1.0000
             ESP     511.0      0.9706   0.9491   0.9883     0.9843
             FRA     459.0      1.0000   0.9804   1.0000     1.0000
             GER     437.0      0.9977   0.9840   0.9954     0.9954
             ITA     505.0      1.0000   0.9802   1.0000     1.0000
2024         EPL     489.0      1.0000   0.9611   0.9652     0.9530
             ESP     507.0      1.0000   0.9625   0.9921     0.9921
             FRA     461.0      0.9957   0.9740   0.9718     0.9783
             GER     426.0      0.9930   0.9671   0.9812     0.9789
             ITA     522.0      0.8180   0.8314   0.8812     0.8506

=== all seasons except 2024
keys          21279.0000
shots_same        0.9992
kp_same           0.9444
xA_0.05           0.9992
npxG_0.05         0.9992

=== 2024 excluding ITA
keys          1883.0000
shots_same       0.9973
kp_same          0.9660
xA_0.05          0.9777
npxG_0.05        0.9756

=== shots excl own goals, by season (all leagues)
season_start
2015    1.0000
2016    1.0000
2017    1.0000
2018    1.0000
2019    1.0000
2020    0.9996
2021    1.0000
2022    1.0000
2023    0.9933
2024    0.9584

=== key passes: HF minus rebuilt, keys at >= 900 minutes: 15399
diff value counts, clipped to -3..+5: {-1: 28, 0: 14190, 1: 1000, 2: 131, 3: 35, 4: 10, 5: 5}
relative error |diff| / hf key_passes: <=5% 15039 | <=10% 15301 | above 10% 98
spearman rebuilt vs hf key passes, per season: {2015: np.float64(0.9997), 2016: np.float64(0.9998), 2017: np.float64(0.9998), 2018: np.float64(0.9998), 2019: np.float64(0.9998), 2020: np.float64(0.9999), 2021: np.float64(0.9999), 2022: np.float64(0.9999), 2023: np.float64(0.9997), 2024: np.float64(0.9995)}
ITA 2024: shots rebuilt below hf 95 | above hf 0 | xA rebuilt below hf by >0.05 60 | above 2
ESP 2023: shots rebuilt below hf 15 | above hf 0 | xA rebuilt below hf by >0.05 6 | above 0
EPL 2024: shots rebuilt below hf 0 | above hf 0 | xA rebuilt below hf by >0.05 17 | above 0

=== same-sign test: does xA agree on keys where key passes differ?
keys with key pass difference: 1209 | of those xA within 0.05: 1146
share of these in seasons 2015-2019: 808 | 2020-2024: 401

=== shots at >= 900 minutes, excl own goals
same: 15301 of 15399 | excluding ITA 2024: 15053 of 15071

=== name folding: extra joins if accents are removed
wfr only keys: 9 | distinct names: 1
of those matched after accent fold: 0
```

### Task 3: coverage

| File | First season | Last season | Latest match | Rows | Matches |
|---|---|---|---|---|---|
| EPL | 2014 | 2025 (partial) | 2025-09-14 | 107,838 | 4,220 |
| La Liga | 2014 | 2025 (partial) | 2025-09-15 | 100,188 | 4,221 |
| Bundesliga | 2014 | 2025 (partial) | 2025-09-14 | 88,214 | 3,391 |
| Serie A | 2014 | 2025 (partial) | 2025-09-15 | 110,026 | 4,204 |
| Ligue 1 | 2014 | 2025 (partial) | 2025-09-14 | 96,140 | 3,966 |

Total 502,406 rows. Seasons are start years, so 2014 means 2014/15.

Match counts per completed season equal a full league season except: Bundesliga 2014 and 2024 (305 of 306), Ligue 1 2016 (379 of 380), Ligue 1 2019 (279, season stopped early, last match 2020-03-08) and Serie A 2024 (374 of 380). Ligue 1 2023 and 2024 show 306, which fits an 18-team league.

### Task 4: columns and categories

22 columns, the same in all five files: `league`, `id`, `minute`, `result`, `X`, `Y`, `xG`, `player`, `h_a`, `player_id`, `situation`, `season`, `shotType`, `match_id`, `home_team`, `away_team`, `home_goals`, `away_goals`, `date`, `player_assisted`, `lastAction`, `home_away`.

| Column | Distinct values |
|---|---|
| `situation` | 5: OpenPlay, FromCorner, SetPiece, DirectFreekick, Penalty |
| `shotType` | 4: RightFoot, LeftFoot, Head, OtherBodyPart |
| `result` | 6: MissedShots, BlockedShot, SavedShot, Goal, ShotOnPost, OwnGoal |
| `lastAction` | 41, with counts in the profile output above |

## Task 5: gap table

| # | Plan field | In shot files | How | HF fills it? |
|---|---|---|---|---|
| 1 | time | **MISSING** | `minute` is when the shot happened, not time played. | **Yes:** `minutes` |
| 2 | shots | **DERIVABLE** | Count rows without `OwnGoal`. Q15's non-penalty shots also drop `Penalty`, giving 494,490 rows. | Also present |
| 3 | npg | **DERIVABLE** | Count `result = Goal` with `situation` not `Penalty`. Not checked directly, since HF has no npg, but goals agree on 99.91% of keys. | Only through FBref |
| 4 | npxG | **DERIVABLE** | Sum `xG` with `situation` not `Penalty`. | Also present |
| 5 | xA | **DERIVABLE** | Sum `xG` of shots where `player_assisted` is the player. | Also present |
| 6 | key_passes | **DERIVABLE, approximate** | Count those same shots. Below HF on some keys, as in Findings. | **Prefer HF:** `key_passes` |
| 7 | xGBuildup | **MISSING** | Needs events before the shot, which these rows lack. | **Yes:** `xGBuildup` |
| 8 | position | **MISSING** | See Task 6. | No, broad labels only |
| 9 | shot X/Y | **PRESENT** | `X`, `Y`, 0 nulls | No |
| 10 | lastAction | **PRESENT** | `lastAction`, 0 nulls. `None` is a label on 59,088 rows. | No |
| 11 | situation | **PRESENT** | `situation`, 0 nulls | No |
| 12 | shotType | **PRESENT** | `shotType`, 0 nulls | No |

Totals: 4 present, 5 derivable, 3 missing. HF fills time and xGBuildup. Position stays missing. Outside the 12, shot `result` is present and match rosters are missing.

**Join key to HF:** name, season and league, because HF has no `player_id`.

- Name: `html.unescape` on both sides, with `player` matched to HF `player_name`.
- Season: shot start year 2015 matches HF `2015-2016`.
- League: taken from the file: `epl` = EPL, `la_liga` = ESP, `bundesliga` = GER, `serie_a` = ITA, `ligue_1` = FRA.

| Join result, seasons 2015 to 2024 | Count |
|---|---|
| Keys in both files | 23,768 |
| Shot-file keys with no HF match | 9 (one name, 304 shot rows) |
| HF keys with no shot-file match | 3,356, of which 9 have shots or key passes |
| HF keys at 900+ minutes | 16,053 |
| Of those, joined | 15,456 |
| Of those, not joined | 597, of which 5 have shots. The other 592 have no shots, which suggests goalkeepers. Not confirmed, because of names-only mode. |

| Rebuilt from shots vs HF | All joined keys | Excluding 2024/25 |
|---|---|---|
| Shots, own goals excluded, same | 99.51% | 99.92% |
| Key passes, same | 94.38% | 94.44% |
| xA within 0.05 | 99.50% | 99.92% |
| npxG within 0.05 | 99.40% | 99.92% |

The two columns use slightly different key sets. The "All" column has 23,768 keys, from `derive.py`. The "Excluding" column has 21,279 keys, from `supplement.py`, which drops 2024/25 and also keys whose only rows are own goals.

Effect on the 10 metrics:

| Metric | Source | Seasons |
|---|---|---|
| Shots per 90 | Shot rows, HF minutes | 2015/16 to 2024/25 |
| xA per 90 | Shot rows or HF, HF minutes | 2015/16 to 2024/25 |
| Key passes per 90 | HF | 2015/16 to 2024/25 |
| xGBuildup per 90 | HF | 2015/16 to 2024/25 |
| npxG per shot | Shot rows | 2014/15 to 2024/25 alone. 2015/16 on with the 900-minute rule. |
| Six-yard and outside-box shares | Shot rows. Box limits from Q16 are not calibrated here. | Same |
| Header share | Shot rows, `shotType = Head` | Same |
| After TakeOn and after Throughball shares | Shot rows, `lastAction` | Same |

The display-only values (goals, assists, npG − npxG) can also be derived.

## Task 6: positions

**No per-match or per-player position is present.** The profile's check for columns naming a position, role, roster or lineup returns `[]`, and the full column list in Task 4 confirms it. The repo tree lists only shot files and their scripts under an Understat path, so no Understat roster file exists there.

The repo has a release named `fb_advanced_match_stats`, from FBref rather than Understat. It was not opened, so whether it holds usable positions is unknown, and it would need its own vetting.

## Task 7: integrity

| Check | Result |
|---|---|
| Exact duplicate rows | 0 |
| Duplicate `id` | 0 |
| Rows equal on everything except `id` | 0 |
| Same match, player, minute, X, Y | 98 |
| `match_id` in more than one file | 0 |
| Nulls | 0, except `h_a` (139,625), `home_away` (362,781) and `player_assisted` (132,795). A null `player_assisted` is expected on unassisted shots. |
| X or Y outside 0 to 1 | 0 |
| Own goals present | Yes, 1,646, all with xG of 0. Q15 can remove them by `result`. |
| Penalties present | Yes, 6,270 |
| Goal rows match the scoreline | 19,997 of 20,002 matches |

## Limits of this check

- Nothing was compared with live Understat, because the site could not be reached.
- HF is not fully independent, since both copies come from Understat. Agreement shows consistency, not truth.
- Names-only mode meant no row could be inspected, so causes of odd counts are inferences and are marked as such.
- Box boundaries (Q16) and the `ML`/`MR` list (Q17) were not checked. Q17 cannot be checked here without positions.
- Understat's terms were not read.
- The R scripts and workflow in the repo were read but not run. The repo was not cloned.

## Scope

- Changed in the repo: this report only. No data files in the repo.
- Not touched: `config/`, `CLAUDE.md`, `GLOSSARY.md`, `docs/phase-1-plan.md`, issues, `.github/`. Nothing pushed.
- Sandbox kept at `~/sandbox/wfr` so results can be reproduced. Remove with `rm -rf ~/sandbox/wfr`.
