# T7: stand-in backfill, trim into private Parquet

Run date: 2026-11-03. Issue: #7. Repo position at the start: `39b1c3a`, level with origin. Every number below comes from output shown in this report. The check scripts are in the appendix, because they sit outside this task's scope.

## Verdict

| Criterion of #7 (word for word) | Result |
|---|---|
| The vetted worldfootballR, FBref and HF files are stored privately as Parquet, with only the columns the build needs | **Met**: 17 files in `data/standin/`, private repo |
| The kept columns are listed for each file | **Met**: section 2 and `MANIFEST.md` |
| The hash of each original file is recorded | **Met**: all 38 in `MANIFEST.md` |
| The trim script is committed, and running it again on the originals gives the same rows and columns | **Met**: all 18 output files byte-identical across two runs. "Committed" is met by this commit. |
| Nothing is fetched from the network | **Met**: both runs had network access denied |
| Counts per league-season match the STEP 0 coverage report | **Met, with one stated exception**: ITA 2023/24 goes from 383 to 379 URLs, because the de-duplication asked for removes 4 spellings. All other counts match. |

**Ready for #6: YES.** The findings below tell #6 what to handle.

## Findings

| Severity | Finding | Section |
|---|---|---|
| Warning, **needs Ahmed** | The ITA 2022/23 extra URL is **not a duplicate**. It is a real match: Spezia v Hellas Verona, 2023-06-11, `Serie A (Relegation tie-breaker)`. It was kept, so this one extra URL was not removed as the task's wording asked. No player reaches 900 minutes because of it. It can be filtered on `Matchweek`. | 6 |
| Warning, **needs Ahmed** | After de-duplication ITA 2023/24 has **379 of 380** matches. Atalanta v Fiorentina, 2024-06-02, is in no FBref or event file, though the shot file has 20 rows for it. T3 could not show this gap, because the 4 extra spellings hid it. The effect on minutes for the two clubs was not measured. | 6 |
| Warning, **needs Ahmed** | Three name-team-seasons sit under two FBref ids. Gabriel Strefezza, Lecce 2023/24, has 703 and 410 minutes, 1113 together. Grouped by id, the player falls under 900 twice. Nothing was changed. | 7 |
| Warning | Combining per player would have been wrong. One player can have different hrefs in different files for one match, which gives 201 cases of one name counted twice in a team's match, and team-match minutes up to 1170. Each match therefore comes whole from one file, and the maximum is 990. | 4 |
| Warning | The five files disagree on values for one match and href: `Pos` on 365 keys, 227 in Pool seasons, and 85 of them change attacking or not, 55 in Pool seasons. `Min` on 37 keys, 13 in Pool seasons. Stored values come from the chosen file, and nothing is reconciled. | 4 |
| Warning for #6 | Key players on the 8-character id inside `Player_Href`, not the whole value. 40 id-seasons hold several spellings of the href. | 7 |
| Warning for #6 | Event files were not de-duplicated, so their counts stay equal to T3. 45 match ids hold two URLs, all in 2023/24, on 1416 event rows. 47 event URLs are not in the positions files. Join on the 8-character match id and handle repeats. | 8 |
| Warning for #6 | `tests/fixtures/standin/` holds the original schema: all columns, `Min` as stored. The trimmed files have fewer columns and `Min` as an integer. That folder was out of scope, so #6 has to bridge this or re-cut. | 2 |
| Info | 101 Pool-season matches have positions but no event rows, so the rule that ignores substitute appearances cannot apply to them. T3 reported the gaps by file. | 8 |
| Info | T3 says `Min` is text. In fact it is text in some files and float in others, even within a league. Both cast cleanly to integer. | 4 |
| Info | 5 rows have no `Min` and no file gives a value. They stay null. | 4 |
| Info | No FBref stat file has a `player_id` column, 0 of 25. `Player_Href` holds the FBref id, and it is kept. Understat `player_id` is kept in shot files. | 2 |
| Info | No planned field reads `master_player_stats.csv`. It is stored in 7 columns because the criterion names the HF files and T3 counts it. It includes NED rows. It could be dropped later. | 2 |
| Info | `Season_End_Year` is `int64` in the ENG event file, from CSV, and `int32` in the other four. `id`, `season`, `match_id` and `player_id` in shot files are doubles, as stored. | 2 |
| Info | `requirements.txt` pins 4 direct libraries. Transitive packages are not pinned (`packaging`, `python-dateutil`, `typing_extensions`, `tzdata`, `xarray`). Byte identity was tested only on Python 3.15.0, macOS arm64. | 5 |
| Info | The outside check used `pyreadr`, which the project does not allow, inside `~/sandbox` only, as T3 did. It is not in the repo or in `requirements.txt`. | 3 |

**Decisions for Ahmed, none blocking #6:**

1. Do tie-breaker minutes count toward a PlayerSeason? The shot file has no rows on that date, so counting them adds minutes with no shots. Suggested: leave them out, by filtering on `Matchweek`.
2. How to treat the missing Atalanta v Fiorentina match. Both clubs' players are short of that match's FBref minutes in 2023/24, a season used for the self-match report.
3. Whether to merge the three players with two FBref ids. Strefezza is the one that can change the Pool.

## Step 0

```
$ pwd
/Users/ahmed.farah/Projects/football-twin
$ git status -sb | head -1
## main...origin/main
$ git rev-parse HEAD origin/main
39b1c3ac84fd6b32b2a4c8e33168bb750b6735a5
39b1c3ac84fd6b32b2a4c8e33168bb750b6735a5
$ git log --oneline -3
39b1c3a docs: settle public-launch terms and live re-validation rules
b81c51f docs: make the stand-in site private and re-validate on live data
aeb7168 docs: record box constants and keep FBref data private
```

Read first: `gh issue view 7`, `gh issue view 6`, `docs/phase-1-plan.md`, `docs/reports/T3_step0_facts.md`, `scripts/cut_fixtures.py`.

Release digests against the `~/sandbox` originals, and against the release notes:

```
$ python3 -I link_and_check.py release.json originals
assets 38 match 38 mismatch 0
```

Each of the 38 lines of that command printed `match notes`. The `originals` folder holds links to those files, and the script checks each hash again before use.

## 1. Stored as Parquet

> The vetted worldfootballR, FBref and HF files are stored privately as Parquet, with only the columns the build needs

**Met.** The repo is private: `gh repo view --json owner,isPrivate,isFork` gives `"isPrivate":true`, owner `afarah101`. Written by `scripts/trim_standin.py`, final run:

```
$ sandbox-exec -f noNet.sb fresh/bin/python3 -B scripts/trim_standin.py originals
bundesliga_shot_data.parquet	88214	14	1452223
epl_shot_data.parquet	107838	14	1770367
la_liga_shot_data.parquet	100188	14	1652200
ligue_1_shot_data.parquet	96140	14	1596515
serie_a_shot_data.parquet	110026	14	1810032
ENG_M_1st_positions.parquet	83613	9	414035
ENG positions rows: before 413736, after URL de-duplication 413736, after 83613
ESP_M_1st_positions.parquet	87400	9	449435
ESP positions rows: before 421890, after URL de-duplication 421890, after 87400
FRA_M_1st_positions.parquet	79421	9	416754
FRA positions rows: before 395313, after URL de-duplication 395313, after 79421
GER_M_1st_positions.parquet	69868	9	350367
GER positions rows: before 348924, after URL de-duplication 348924, after 69868
ITA_M_1st_positions.parquet	87300	9	445964
ITA positions rows: before 425429, after URL de-duplication 425045, after 87300
ENG_M_1st_match_summary.parquet	37734	6	283373
ESP_M_1st_match_summary.parquet	44873	6	324327
FRA_M_1st_match_summary.parquet	37503	6	291091
GER_M_1st_match_summary.parquet	34742	6	262761
ITA_M_1st_match_summary.parquet	43180	6	320377
understat_xg_data.parquet	27182	12	807726
master_player_stats.parquet	34246	7	351084
exit 0
```

Shot, event and HF files keep every source row, in source order. All seasons stay, including those outside the Pool, because T3's counts cover them and #6 needs a current-season case.

Not stored: `ENG_M_1st_keeper_player_advanced_match_stats.rds`. It has no `Pos` column and goalkeepers are out of scope. Its hash is still recorded.

## 2. Kept columns

> The kept columns are listed for each file

**Met.** `MANIFEST.md` lists them per file. Why each one stays:

| Source | Kept | Why | Dropped |
|---|---|---|---|
| Shot files, 5 | `id`, `league`, `season`, `match_id`, `date`, `player`, `player_id` | Identity, league-season, names are not unique | `minute`, `h_a`, `home_away`, `home_team`, `away_team`, `home_goals`, `away_goals`, `player_assisted` |
| | `X`, `Y` | Box shares, Q16 | |
| | `xG` | npxG per shot | |
| | `situation`, `shotType`, `lastAction`, `result` | Metrics, Q15, npg | |
| FBref positions, 5 files per league | `MatchURL`, `Match_Date`, `Season_End_Year`, `Team` | Identity, league-season | Passing, defence and other match stats |
| | `Matchweek` | Picks out the tie-breaker | |
| | `Player`, `Player_Href` | Name, FBref id | |
| | `Pos`, `Min` | Position rule, 900-minute gate, per-90 | |
| Match events, 5 | `MatchURL`, `Match_Date`, `Season_End_Year`, `Team`, `Event_Type`, `Event_Players` | `Substitute` rows name who came on (Q5) | `Event_Time` and match summary columns |
| HF `understat_xg_data.csv` | `player_name`, `team`, `league`, `season` | Identity, display | `apps`, `xG`, `xGChain`, `xG90`, `xA90`, `npxG90` |
| | `minutes`, `shots`, `key_passes`, `xA`, `npxG`, `xGBuildup` | Planned fields, T3 section 3 | |
| | `goals`, `assists` | Display only | |
| HF `master_player_stats.csv` | `player`, `player_id`, `league`, `season`, `squad`, `pos`, `min` | The id join in T3 section 4 | The other columns |

Names are stored exactly as in the source, with no entity decoding: 2308 shot rows still hold `&#039;`. The literal text `None` in `lastAction` stays text, on 59088 rows, the count T3 gives.

```
### schema of Season_End_Year in event files {'ENG': 'int64', 'ESP': 'int32', 'FRA': 'int32', 'GER': 'int32', 'ITA': 'int32'}
schema of positions ['MatchURL:large_string', 'Match_Date:large_string', 'Matchweek:large_string', 'Season_End_Year:int32', 'Team:large_string', 'Player:large_string', 'Player_Href:large_string', 'Pos:large_string', 'Min:int64']
schema of shots ['id:double', 'league:large_string', 'season:double', 'match_id:double', 'date:large_string', 'player:large_string', 'player_id:double', 'X:double', 'Y:double', 'xG:double', 'situation:large_string', 'shotType:large_string', 'lastAction:large_string', 'result:large_string']
FBref files holding a player_id column: 0 of 25
lastAction text None in trimmed shots: 59088
names holding &#039; in trimmed shots: 2308
```

## 3. Hashes, and values against the originals

> The hash of each original file is recorded

**Met.** `MANIFEST.md` has one row per source asset: source asset, original SHA-256, trimmed file, trimmed SHA-256, source rows, rows kept, source columns, rdata version.

```
MANIFEST vs shasum: files checked 55 name and hash on one line 55 missing 0
files over 100 MB: 0
trimmed files 17 mismatches 0 | source rows in manifest 38
schemas differ within group: {'*_shot_data.parquet': 1, '*_positions.parquet': 1, '*_match_summary.parquet': 2}
```

The 55 files are the 17 trimmed files and the 38 originals.

**Values.** An outside check shares no code with the script. It reads originals with `pyreadr` and the `csv` module, and trimmed files with `pyarrow`, and compares every kept cell.

```
### A. plain files: same rows, same order, every kept cell
bundesliga_shot_data: source rows 88214 trimmed rows 88214 columns 14 cells 1234996 differences 0 
epl_shot_data: source rows 107838 trimmed rows 107838 columns 14 cells 1509732 differences 0 
la_liga_shot_data: source rows 100188 trimmed rows 100188 columns 14 cells 1402632 differences 0 
ligue_1_shot_data: source rows 96140 trimmed rows 96140 columns 14 cells 1345960 differences 0 
serie_a_shot_data: source rows 110026 trimmed rows 110026 columns 14 cells 1540364 differences 0 
ENG_M_1st_match_summary: source rows 37734 trimmed rows 37734 columns 6 cells 226404 differences 0 
ESP_M_1st_match_summary: source rows 44873 trimmed rows 44873 columns 6 cells 269238 differences 0 
FRA_M_1st_match_summary: source rows 37503 trimmed rows 37503 columns 6 cells 225018 differences 0 
GER_M_1st_match_summary: source rows 34742 trimmed rows 34742 columns 6 cells 208452 differences 0 
ITA_M_1st_match_summary: source rows 43180 trimmed rows 43180 columns 6 cells 259080 differences 0 
understat_xg_data: source rows 27182 trimmed rows 27182 columns 12 cells 326184 differences 0 
master_player_stats: source rows 34246 trimmed rows 34246 columns 7 cells 239722 differences 0 

### B. positions: every match equals one source file's rows for that URL, none lost
ENG: rows before 413736 after 83613 | matches 2939 source ids 2939 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['str'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ESP: rows before 421890 after 87400 | matches 2921 source ids 2921 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['str'], 'possession': ['str'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
FRA: rows before 395313 after 79421 | matches 2701 source ids 2701 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['str'], 'misc': ['str']}
GER: rows before 348924 after 69868 | matches 2348 source ids 2348 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ITA: rows before 425429 after 87300 | matches 2917 source ids 2917 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['str'], 'passing': ['str'], 'defense': ['str'], 'misc': ['float']}
total rows before 2005292 after 407602 | matches equal to no source file 0 | source ids lost 0
identical-match credit, first file in order that equals the output (a match can equal several): {'passing_types': 406333, 'misc': 704, 'possession': 216, 'defense': 349}
```

It can fail. Run on a copy with 5 planted faults (a 1e-9 change to one `xG`, a changed `Event_Type`, a dropped HF row, a changed `Pos`, a removed match), it reports each one. That copy came from an earlier run, so its manifest also fails on those 5 files:

```
$ t7_verify.py mutant originals T3_step0_facts.md | grep -E 'differences [1-9]|lost [1-9]|equal to no source file [1-9]|plain-file|mismatches'
epl_shot_data: source rows 107838 trimmed rows 107838 columns 14 cells 1509732 differences 1 [('xG', 5, 0.03097105498774147, 0.03097105398774147)]
ESP_M_1st_match_summary: source rows 44873 trimmed rows 44873 columns 6 cells 269238 differences 1 [('Event_Type', 3, 'Goalx', 'Substitute')]
understat_xg_data: source rows 27182 trimmed rows 27181 columns 12 cells 326172 differences 1 
FRA: rows before 395313 after 79393 | matches 2700 source ids 2701 lost 1 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['str'], 'misc': ['str']}
GER: rows before 348924 after 69868 | matches 2348 source ids 2348 lost 0 | matches equal to no source file 1 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
total rows before 2005292 after 407574 | matches equal to no source file 1 | source ids lost 1
plain-file cells compared 8787770 differences 3
trimmed files 17 mismatches 5 | source rows in manifest 38
```

## 4. FBref: combining the five files

Rows before and after, from the script:

| League | Before | After URL de-duplication | After |
|---|---:|---:|---:|
| ENG | 413736 | 413736 | 83613 |
| ESP | 421890 | 421890 | 87400 |
| FRA | 395313 | 395313 | 79421 |
| GER | 348924 | 348924 | 69868 |
| ITA | 425429 | 425045 | 87300 |
| All | 2005292 | | 407602 |

Rules, in order:

1. **Cast `Min`** to integer on read, in each file. The cast raises on anything that is not a whole number.
2. **One URL per match id.** Where a match id has two URL spellings, keep the one in the most files. This removes 384 rows and only touches 4 ITA 2023/24 matches, where `Monza-Brianza` loses to `Monza`. Within a file the two spellings hold the same values.
3. **Each match comes whole from one file**: the most rows, then the most `Min` values, then the first in the order `passing_types`, `possession`, `passing`, `defense`, `misc`.

**Why whole matches.** A union per player would mix files inside a match, and files can give one player different hrefs in that match:

```
### player-level union, the rule NOT used
rows 408623 | team-match minutes max 1170 | same name twice in one team-match 201
examples:
              mid       Team         Player                         Player_Href  Min           kind
1255244  0043c6e9   Dortmund    Mateu Morey    /en/players/5fd5e542/Mateu-Morey    4  passing_types
1464632  0043c6e9   Dortmund    Mateu Morey    /en/players/749b49a1/Mateu-Morey    4        defense
1267593  0355d66e  Stuttgart  Omar Marmoush  /en/players/0e0102eb/Omar-Marmoush   75  passing_types
1477040  0355d66e  Stuttgart  Omar Marmoush  /en/players/589449ec/Omar-Marmoush   75        defense
```

After the rule, the same FBref id never appears twice in one match, and team-match minutes are at most 990:

```
team-match minutes max 990 min 825 | same FBref id twice in a match 0
null Min rows {('ENG', 2018): 1, ('FRA', 2023): 1, ('FRA', 2026): 1, ('ITA', 2022): 1, ('ITA', 2024): 1} | empty Pos rows 0 | null Pos 0
```

**Why most rows first.** 4 matches are partial in some file, and in one of them the first file in the order is the partial one:

```
### matches whose row count differs between files
kind                          defense  misc  passing  passing_types  possession
lg  Season_End_Year mid                                                        
ENG 2019            698db309     13.0  27.0     27.0           27.0        27.0
    2020            bd102a2b     25.0  25.0     25.0           25.0        13.0
FRA 2020            4bbf91db     14.0  28.0     14.0           14.0        14.0
GER 2024            7eb884e7     32.0  16.0     32.0           32.0        32.0
```

**Why that file order.** `passing_types` differs least from the other four on `Pos`, and the order follows that count:

```
### C. what the five files disagree on, same match id and same Player_Href, present in 2+ files
Pos: keys differing 365 in Pool seasons 227 | rows off the most common value, by file {'possession': 8, 'misc': 215, 'passing_types': 3, 'passing': 53, 'defense': 102}
Min: keys differing 37 in Pool seasons 13 | rows off the most common value, by file {'possession': 6, 'misc': 26, 'passing_types': 8, 'passing': 8, 'defense': 3}
Player: keys differing 94 in Pool seasons 94 | rows off the most common value, by file {'misc': 94}
Pos: keys where one file says attacking and another not 85 in Pool seasons 55
```

**Why most `Min` values next.** In FRA match `0f7c086f`, four files give Steve Mounié 91 and Martin Satriano no value. `misc` gives 17 and 73, which add up to 90. Without this step Mounié gains 74 minutes. The code review found this. The other 5 null `Min` rows have no value in any file. Serge Gnabry's 69 v 77 is in a match where the rule takes the 77 that 4 of 5 files hold. Mateu Morey's 6 empty `Pos` rows, in `defense` only, are not used, so the trimmed files hold 0 empty `Pos`.

```
### Min values that differ by 3+ or are null in some files only, by file
kind                          defense  misc  passing  passing_types  possession
lg  mid      Player                                                            
FRA 0f7c086f Martin Satriano     <NA>    73     <NA>           <NA>        <NA>
             Steve Mounié          91    17       91             91          91
GER 4277ef38 Serge Gnabry          69    77       77             77          77

### empty Pos in the originals
{('GER', 'defense', '/en/players/749b49a1/Mateu-Morey'): 6}
```

Whole-match equality with a source file, and no lost match, are shown in section 3.

## 5. Repeat

> The trim script is committed, and running it again on the originals gives the same rows and columns

**Met.** Two runs of the final code, one in a new venv built only from `requirements.txt`, one in the sandbox venv, gave byte-identical files, including `MANIFEST.md`:

```
$ sandbox-exec -f noNet.sb fresh/bin/python3 -B scripts/trim_standin.py originals
$ sandbox-exec -f noNet.sb parquet-vet/venv/bin/python3 -B scripts/trim_standin.py originals run4
exit 0
exit 0
run A (fresh venv) vs run B (second venv), all 18 files: same 18 different 0
```

`requirements.txt` against the wheels, with no network:

```
$ fresh/bin/pip install --no-index --find-links wheels -r requirements.txt
Successfully installed numpy-2.5.4 packaging-26.3 pandas-3.1.0 pyarrow-26.0.1 python-dateutil-4.0.0 rdata-1.1.0 typing_extensions-4.16.0 tzdata-2026.6 xarray-2026.9.0
```

The script reuses `read_source` from `scripts/cut_fixtures.py`, so `.rds` files follow the plan's three rules. On the CSVs, pandas' default parsing equals round-trip parsing:

```
understat_xg_data.csv default vs round_trip differing cells 0 {}
master_player_stats.csv default vs round_trip differing cells 0 {}
ENG_M_1st_match_summary.csv default vs round_trip differing cells 0 {}
```

## 6. Network, and the Serie A extras

> Nothing is fetched from the network

**Met.** Both runs and the outside check ran under a profile denying network access. The script imports only `sys`, `platform`, `pathlib`, `pandas`, `pyarrow`, `rdata` and `cut_fixtures`. `gh` and `git fetch` were used only in Step 0, to read the issue and the release notes.

```
$ cat noNet.sb
(version 1)
(allow default)
(deny network*)
$ sandbox-exec -f noNet.sb curl -sS -m 5 -o /dev/null -w '%{http_code}\n' https://example.com
curl: (6) Could not resolve host: example.com
000
```

**The Serie A extras.** T3 called them possible duplicates. Two different things turned out to be behind them:

```
### URL spellings of one match id
{('ITA', 2024, '5778b5c6'): 2, ('ITA', 2024, '6e72c38b'): 2, ('ITA', 2024, '9a8e6c44'): 2, ('ITA', 2024, 'd0fdea52'): 2}
MatchURL
https://fbref.com/en/matches/5778b5c6/Lazio-Monza-Brianza-September-23-2023-Serie-A       3
https://fbref.com/en/matches/5778b5c6/Lazio-Monza-September-23-2023-Serie-A               5
https://fbref.com/en/matches/6e72c38b/Atalanta-Monza-Brianza-September-2-2023-Serie-A     3
https://fbref.com/en/matches/6e72c38b/Atalanta-Monza-September-2-2023-Serie-A             5
https://fbref.com/en/matches/9a8e6c44/Monza-Bologna-September-28-2023-Serie-A             5
https://fbref.com/en/matches/9a8e6c44/Monza-Brianza-Bologna-September-28-2023-Serie-A     3
https://fbref.com/en/matches/d0fdea52/Monza-Brianza-Salernitana-October-8-2023-Serie-A    3
https://fbref.com/en/matches/d0fdea52/Monza-Salernitana-October-8-2023-Serie-A            4
two spellings inside one file, keys with differing values: {'passing': 0, 'passing_types': 0, 'possession': 0}
serie_a shot rows dated 2023-06-11, the tie-breaker date: 0
URLs holding Monza-Brianza kept: 0 | Monza 2023/24 matches: 38
Matchweek values not 'Matchweek N': Counter({'Serie A (Relegation tie-breaker)': 31})
tie-breaker rows 31 https://fbref.com/en/matches/e0449015/Spezia-Hellas-Verona-June-11-2023-Serie-A 2023-06-11 Serie A (Relegation tie-breaker)
players at 900+ only because of the tie-breaker: []
ITA 2023/24 matches per team, not 38: {'Fiorentina': 37, 'Atalanta': 37} | distinct matches 379
shot file match 22585 rows 20 date 2024-06-02 16:00:00
```

- **ITA 2023/24, 4 duplicates, removed.** Same match id, same values, two spellings.
- **ITA 2022/23, 1 real match, kept.** A different id and date, and its `Matchweek` names a tie-breaker. Removing it would drop a real match on a guess, and keeping it costs nothing because #6 can filter on `Matchweek`. Decision 1 above.
- **ITA 2023/24 gap.** Fiorentina and Atalanta have 37 matches and all others 38. Decision 2 above.

## 7. Player identity

```
team-match minutes max 990 min 825 | same FBref id twice in a match 0
same name, team and season under two FBref ids: {('FRA', 2024, 'Marseille', 'Abdoul Meité'): {'8eb68164': 296, 'cb9ef70f': 7}, ('FRA', 2024, 'Metz', 'Joseph Nduquidi'): {'1d039497': 194, 'f365b837': 1}, ('ITA', 2024, 'Lecce', 'Gabriel Strefezza'): {'674cfc5a': 703, 'ac4a4508': 410}}
id-seasons holding several Player_Href spellings: 40
```

## 8. Counts per league-season

> Counts per league-season match the STEP 0 coverage report

**Met, with one exception.** The expected counts are parsed from the text of `docs/reports/T3_step0_facts.md`, not typed in. The only difference is ITA 2023/24, explained in section 6.

```
### D. counts per league-season against the T3 report text
shots bundesliga: seasons 12 differences {}
shots epl: seasons 12 differences {}
shots la_liga: seasons 12 differences {}
shots ligue_1: seasons 12 differences {}
shots serie_a: seasons 12 differences {}
positions ENG: seasons 9 differences (T3, trimmed) {}
positions ESP: seasons 9 differences (T3, trimmed) {}
positions FRA: seasons 9 differences (T3, trimmed) {}
positions GER: seasons 9 differences (T3, trimmed) {}
positions ITA: seasons 9 differences (T3, trimmed) {2023: (383, 379)}
events ENG: seasons 8 differences {}
events ESP: seasons 8 differences {}
events FRA: seasons 8 differences {}
events GER: seasons 8 differences {}
events ITA: seasons 8 differences {}
HF understat_xg_data: rows 27182 league-seasons in T3 50 differences [] | not in T3 table 0
HF master_player_stats: rows 34246 league-seasons in T3 60 differences [] | not in T3 table 0
T3 totals in text: shots 502406 True | trimmed shot rows 502406 | HF 27182 and 34246: 27182 34246
```

Event URLs against positions URLs. The two ids missing from positions, `c34bbc21` (GER 2021/22) and `e0a20cfe` (ITA 2020/21), are the two gaps T3 reported:

```
### F. event URLs against positions URLs
ENG: event URLs 2908 event ids 2899 | URLs not in positions 9 | ids not in positions [] | positions ids not in events 40
ESP: event URLs 2871 event ids 2870 | URLs not in positions 1 | ids not in positions [] | positions ids not in events 51
FRA: event URLs 2656 event ids 2655 | URLs not in positions 1 | ids not in positions [] | positions ids not in events 46
GER: event URLs 2349 event ids 2320 | URLs not in positions 30 | ids not in positions ['c34bbc21'] | positions ids not in events 29
ITA: event URLs 2814 event ids 2809 | URLs not in positions 6 | ids not in positions ['e0a20cfe'] | positions ids not in events 109
### trimmed positions and event files
ENG ids with 2 URLs in events 9 seasons [2024] event rows on those ids 282 | event ids without positions [] | Pool position ids without events {}
ESP ids with 2 URLs in events 1 seasons [2024] event rows on those ids 13 | event ids without positions [] | Pool position ids without events {np.int32(2023): 10}
FRA ids with 2 URLs in events 1 seasons [2024] event rows on those ids 44 | event ids without positions [] | Pool position ids without events {np.int32(2023): 10}
GER ids with 2 URLs in events 29 seasons [2024] event rows on those ids 914 | event ids without positions [['c34bbc21', 2022]] | Pool position ids without events {np.int32(2021): 2}
ITA ids with 2 URLs in events 5 seasons [2024] event rows on those ids 163 | event ids without positions [['e0a20cfe', 2021]] | Pool position ids without events {np.int32(2020): 68, np.int32(2023): 11}
```

Arithmetic used above:

```
rows dropped by URL de-duplication 384
total rows before 2005292 after 407602
event ids with 2 URLs 45 rows on them 1416
event URLs not in positions 47
Pool position ids without events 101
Strefezza minutes 1113
Satriano and Mounie in misc 90 | Mounie other files minus misc 74
```

## Code review

`/code-review` on `scripts/trim_standin.py`, high effort. 8 findings:

| Finding | Outcome |
|---|---|
| File choice ignored missing `Min` (Mounié, above) | Fixed |
| Manifest listed any stale `*.parquet` in the folder | Fixed |
| Manifest hard-coded the Python version | Fixed |
| Manifest loaded whole tables for row counts | Fixed |
| A failure mid-run leaves a mixed folder | Left. Re-running fixes it, and the hashes expose it. |
| Duplicate guard compares the whole href, not the id | Left. The outside check found 0 on hash-pinned originals. |
| Sibling import fails under `python -I` | Left. It fails at once, with no bad data. |
| `SHA256` repeats 10 hashes from `cut_fixtures` | Left. The originals are fixed. |

- Only allowed libraries: **YES**. `pandas`, `numpy`, `pyarrow`, `rdata`.
- No columns dropped that the plan needs: **YES**. Section 2.

## Appendix: check scripts

Not committed as files, because they were outside the scope of this task.

<details><summary><code>t7_verify.py</code></summary>

```python
"""Outside check for #7. Shares no code with scripts/trim_standin.py. Reads originals with pyreadr and csv, trimmed files with pyarrow, expected counts from the T3 report text."""
import csv, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import pyarrow.parquet as pq, pyreadr
data, originals, t3 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]).read_text()
csv.field_size_limit(10**9)
null = lambda v: v is None or v != v
def col(table, name): return table.column(name).to_pylist()
def same(trimmed, source):
    if null(trimmed) or null(source): return (null(trimmed) or trimmed == "") and (null(source) or source == "") and null(trimmed) == (null(source) or source == "")
    if isinstance(trimmed, str): return trimmed == source
    return float(trimmed) == float(source)
def read_source(name, columns):
    if name.endswith(".rds"):
        df = pyreadr.read_r(str(originals / name))[None]
        return len(df), {c: df[c].tolist() for c in columns}
    with open(originals / name, encoding="utf8", newline="") as h:
        rows = list(csv.DictReader(h))
    return len(rows), {c: [r[c] for r in rows] for c in columns}
total_cells = total_diffs = 0
print("### A. plain files: same rows, same order, every kept cell")
plain = [f"{n}_shot_data" for n in ("bundesliga","epl","la_liga","ligue_1","serie_a")] + [f"{l}_M_1st_match_summary" for l in ("ENG","ESP","FRA","GER","ITA")] + ["understat_xg_data", "master_player_stats"]
for stem in plain:
    t = pq.read_table(data / f"{stem}.parquet")
    name = f"{stem}.csv" if (originals / f"{stem}.csv").exists() else f"{stem}.rds"
    n, src = read_source(name, t.column_names)
    diffs = abs(n - t.num_rows); cells = 0; examples = []
    for c in t.column_names:
        for i, (a, b) in enumerate(zip(col(t, c), src[c])):
            cells += 1
            if not same(a, b):
                diffs += 1
                if len(examples) < 3: examples.append((c, i, a, b))
    total_cells += cells; total_diffs += diffs
    print(f"{stem}: source rows {n} trimmed rows {t.num_rows} columns {t.num_columns} cells {cells} differences {diffs} {examples or ''}")
print("\n### B. positions: every match equals one source file's rows for that URL, none lost")
KEPT = ["Match_Date", "Matchweek", "Season_End_Year", "Team", "Player", "Player_Href", "Pos", "Min"]
KINDS = ["passing_types", "possession", "passing", "defense", "misc"]
mid = lambda u: re.search(r"/matches/([0-9a-f]{8})/", u).group(1)
def norm(row):
    row = dict(row); m = row["Min"]; row["Min"] = None if null(m) else int(float(m)); row["Season_End_Year"] = int(row["Season_End_Year"])
    return tuple(row[k] for k in KEPT)
agree = {c: Counter() for c in ("Pos", "Min", "Player")}; off = {c: Counter() for c in agree}; pool_keys = {c: 0 for c in agree}; flips = pool_flips = 0
ATT = {"FW", "LW", "RW", "AM"}; attacking = lambda p: bool(set(p.split(",")) & ATT)
all_kept = {}; bad_matches = lost = total_before = total_after = 0; taken_total = Counter()
for lg in ("ENG", "ESP", "FRA", "GER", "ITA"):
    t = pq.read_table(data / f"{lg}_M_1st_positions.parquet")
    out = defaultdict(list)
    for r in t.to_pylist(): out[r["MatchURL"]].append(r)
    src = {}; before = 0; keys = defaultdict(dict)
    min_types = {}
    for k in KINDS:
        n, c = read_source(f"{lg}_M_1st_{k}_player_advanced_match_stats.rds", ["MatchURL"] + KEPT)
        min_types[k] = sorted({type(v).__name__ for v in c["Min"] if not null(v)})
        before += n
        rows = defaultdict(list)
        for i in range(n):
            row = {x: c[x][i] for x in KEPT}
            rows[c["MatchURL"][i]].append(norm(row))
            keys[(mid(c["MatchURL"][i]), row["Player_Href"])][k] = (row["Pos"], None if null(row["Min"]) else int(float(row["Min"])), row["Player"], int(row["Season_End_Year"]))
        src[k] = rows
    src_ids = {mid(u) for k in KINDS for u in src[k]}
    out_ids = {mid(u) for u in out}
    assert len(out_ids) == len(out), "one id, two URLs in output"
    lost += len(src_ids - out_ids)
    taken = Counter(); bad = 0
    for u, rs in out.items():
        have = sorted((norm({x: r[x] for x in KEPT}) for r in rs), key=repr)
        hits = [k for k in KINDS if sorted(src[k].get(u, []), key=repr) == have]
        if not hits: bad += 1
        else: taken[hits[0]] += len(have)
    bad_matches += bad; total_before += before; total_after += t.num_rows
    taken_total.update(taken)
    print(f"{lg}: rows before {before} after {t.num_rows} | matches {len(out)} source ids {len(src_ids)} lost {len(src_ids - out_ids)} | matches equal to no source file {bad} | Min types {min_types}")
    all_kept[lg] = t
    for key, per in keys.items():
        if len(per) < 2: continue
        pool = 2018 <= next(iter(per.values()))[3] <= 2024
        for j, c in enumerate(("Pos", "Min", "Player")):
            vals = Counter(v[j] for v in per.values())
            if len(vals) > 1:
                agree[c]["all"] += 1; agree[c]["pool"] += pool
                top = vals.most_common(1)[0][0]
                for k, v in per.items():
                    if v[j] != top: off[c][k] += 1
                if c == "Pos" and len({attacking(v[0]) for v in per.values()}) > 1:
                    flips += 1; pool_flips += pool
print(f"total rows before {total_before} after {total_after} | matches equal to no source file {bad_matches} | source ids lost {lost}")
print("identical-match credit, first file in order that equals the output (a match can equal several):", dict(taken_total))
print("\n### C. what the five files disagree on, same match id and same Player_Href, present in 2+ files")
for c in agree: print(f"{c}: keys differing {agree[c]['all']} in Pool seasons {agree[c]['pool']} | rows off the most common value, by file {dict(off[c])}")
print(f"Pos: keys where one file says attacking and another not {flips} in Pool seasons {pool_flips}")
print("\n### D. counts per league-season against the T3 report text")
start = {"ENG": 0}
def t3_line(pattern):
    m = re.search(pattern, t3, re.M); assert m, pattern
    return {int(a): int(b) for a, b in re.findall(r"(\d{4}):(\d+)", m.group(1))}
mism = []
for name, lg in (("bundesliga","GER"),("epl","ENG"),("la_liga","ESP"),("ligue_1","FRA"),("serie_a","ITA")):
    want = t3_line(rf"^{name} ((?:\d{{4}}:\d+ )+)\|")
    t = pq.read_table(data / f"{name}_shot_data.parquet", columns=["season", "match_id"]).to_pylist()
    have = Counter(); seen = set()
    for r in t:
        k = (int(r["season"]), r["match_id"])
        if k not in seen: seen.add(k); have[k[0]] += 1
    d = {y: (want.get(y), have.get(y)) for y in set(want) | set(have) if want.get(y) != have.get(y)}
    print(f"shots {name}: seasons {len(want)} differences {d}"); mism += list(d.items())
for lg in ("ENG", "ESP", "FRA", "GER", "ITA"):
    want = t3_line(rf"^  {lg} ((?:\d{{4}}:\d+ )+)\| Pool gaps")
    have = Counter()
    for u, y in {(r["MatchURL"], r["Season_End_Year"]) for r in pq.read_table(data / f"{lg}_M_1st_positions.parquet", columns=["MatchURL", "Season_End_Year"]).to_pylist()}: have[y - 1] += 1
    d = {y: (want.get(y), have.get(y)) for y in set(want) | set(have) if want.get(y) != have.get(y)}
    print(f"positions {lg}: seasons {len(want)} differences (T3, trimmed) {d}")
for lg in ("ENG", "ESP", "FRA", "GER", "ITA"):
    label = "ENG_M_1st_match_summary.csv" if lg == "ENG" else f"{lg}_M_1st_match_summary"
    want = t3_line(rf"^{re.escape(label)} ((?:\d{{4}}:\d+ )+)\|")
    have = Counter()
    for u, y in {(r["MatchURL"], r["Season_End_Year"]) for r in pq.read_table(data / f"{lg}_M_1st_match_summary.parquet", columns=["MatchURL", "Season_End_Year"]).to_pylist()}: have[int(y)] += 1
    d = {y: (want.get(y), have.get(y)) for y in set(want) | set(have) if want.get(y) != have.get(y)}
    print(f"events {lg}: seasons {len(want)} differences {d}")
block = t3[t3.index("### HF understat_xg_data.csv rows by league"):]
lines = block.splitlines()[1:]
def hf_table(lines):
    seasons = lines[0].split()[1:]
    out = {}
    for l in lines[2:7 if lines[1].strip() in ("lg",) else 8]:
        p = l.split()
        if len(p) == len(seasons) + 1: out[p[0]] = dict(zip(seasons, map(int, p[1:])))
    return out
xg = hf_table(lines[:7]); ms = hf_table(lines[7:15])
for stem, want, lgcol in (("understat_xg_data", xg, "league"), ("master_player_stats", ms, "league")):
    rows = pq.read_table(data / f"{stem}.parquet", columns=["league", "season"]).to_pylist()
    have = Counter((("ENG" if stem == "understat_xg_data" and r["league"] == "EPL" else r["league"]), r["season"]) for r in rows)
    wants = {(l, s): v for l, d in want.items() for s, v in d.items()}
    print(f"HF {stem}: rows {len(rows)} league-seasons in T3 {len(wants)} differences {[(k, wants[k], have.get(k)) for k in wants if wants[k] != have.get(k)]} | not in T3 table {sum(v for k, v in have.items() if k not in wants)}")
print("T3 totals in text: shots 502406", "502406" in t3, "| trimmed shot rows", sum(pq.read_metadata(data / f"{n}_shot_data.parquet").num_rows for n in ("bundesliga","epl","la_liga","ligue_1","serie_a")), "| HF 27182 and 34246:", pq.read_metadata(data / "understat_xg_data.parquet").num_rows, pq.read_metadata(data / "master_player_stats.parquet").num_rows)
print("\n### E. Serie A extras and player identity in the trimmed positions")
ita = all_kept["ITA"].to_pylist()
print("URLs holding Monza-Brianza kept:", len({r["MatchURL"] for r in ita if "Monza-Brianza" in r["MatchURL"] and r["Season_End_Year"] == 2024}), "| Monza 2023/24 matches:", len({r["MatchURL"] for r in ita if r["Season_End_Year"] == 2024 and r["Team"] == "Monza"}))
print("Matchweek values not 'Matchweek N':", Counter(r["Matchweek"] for lg in all_kept for r in all_kept[lg].to_pylist() if not re.search(r"Matchweek \d+\)", r["Matchweek"])))
tb = [r for r in ita if "e0449015" in r["MatchURL"]]; print("tie-breaker rows", len(tb), tb[0]["MatchURL"], tb[0]["Match_Date"], tb[0]["Matchweek"])
pid = lambda h: re.search(r"/players/([0-9a-f]{8})/", h).group(1)
mins = defaultdict(int)
for r in ita:
    if r["Season_End_Year"] == 2023 and r["Min"] is not None: mins[pid(r["Player_Href"])] += r["Min"]
print("players at 900+ only because of the tie-breaker:", [(r["Player"], mins[pid(r["Player_Href"])], r["Min"]) for r in tb if r["Min"] is not None and mins[pid(r["Player_Href"])] >= 900 > mins[pid(r["Player_Href"])] - r["Min"]])
tm = Counter(r["Team"] for r in {(r["MatchURL"], r["Team"]): r for r in ita if r["Season_End_Year"] == 2024}.values()); print("ITA 2023/24 matches per team, not 38:", {k: v for k, v in tm.items() if v != 38}, "| distinct matches", len({r["MatchURL"] for r in ita if r["Season_End_Year"] == 2024}))
sa = [r for r in pq.read_table(data / "serie_a_shot_data.parquet", columns=["season", "date", "match_id", "player"]).to_pylist() if r["season"] == 2023 and r["match_id"] == 22585]; print("shot file match 22585 rows", len(sa), "date", sa[0]["date"] if sa else None)
teammin = Counter(); nullmin = Counter(); twoid = defaultdict(lambda: defaultdict(int)); slugs = defaultdict(set); dupid = 0; seen = set()
for lg, t in all_kept.items():
    for r in t.to_pylist():
        teammin[(r["MatchURL"], r["Team"])] += r["Min"] or 0
        if r["Min"] is None: nullmin[(lg, r["Season_End_Year"])] += 1
        p = pid(r["Player_Href"]); k = (r["MatchURL"], p); dupid += k in seen; seen.add(k)
        twoid[(lg, r["Season_End_Year"], r["Team"], r["Player"])][p] += r["Min"] or 0
        slugs[(r["Season_End_Year"], p)].add(r["Player_Href"])
print("team-match minutes max", max(teammin.values()), "min", min(teammin.values()), "| same FBref id twice in a match", dupid)
print("null Min rows", dict(nullmin), "| empty Pos rows", sum(1 for t in all_kept.values() for p in col(t, "Pos") if p == ""), "| null Pos", sum(1 for t in all_kept.values() for p in col(t, "Pos") if p is None))
print("same name, team and season under two FBref ids:", {k: dict(v) for k, v in twoid.items() if len(v) > 1})
print("id-seasons holding several Player_Href spellings:", sum(1 for v in slugs.values() if len(v) > 1))
print("\n### F. event URLs against positions URLs")
for lg in all_kept:
    ev = {r["MatchURL"] for r in pq.read_table(data / f"{lg}_M_1st_match_summary.parquet", columns=["MatchURL"]).to_pylist()}
    pos = set(col(all_kept[lg], "MatchURL"))
    print(f"{lg}: event URLs {len(ev)} event ids {len({mid(u) for u in ev})} | URLs not in positions {len(ev - pos)} | ids not in positions {sorted({mid(u) for u in ev} - {mid(u) for u in pos})} | positions ids not in events {len({mid(u) for u in pos} - {mid(u) for u in ev})}")
print(f"\nplain-file cells compared {total_cells} differences {total_diffs}")
print("\n### G. MANIFEST rows and columns against the files")
m = (data / "MANIFEST.md").read_text(); mis = 0
for p in sorted(data.glob("*.parquet")):
    md = pq.read_metadata(p)
    ok = re.search(rf"^\| `{re.escape(p.name)}` \| {md.num_rows} \| {md.num_columns} \| {p.stat().st_size} \|", m, re.M) is not None
    mis += not ok
print("trimmed files", len(list(data.glob('*.parquet'))), "mismatches", mis, "| source rows in manifest", len(re.findall(r"^\| `[^`]+\.(?:rds|csv)` \|", m, re.M)))
print("schemas differ within group:", {g: len({str(pq.read_schema(p).remove_metadata()) for p in data.glob(g)}) for g in ("*_shot_data.parquet", "*_positions.parquet", "*_match_summary.parquet")})
```

</details>

<details><summary><code>t7_extra.py</code></summary>

```python
"""Measurements behind the FBref rules in #7. Reads the T3 analysis cache (the originals under the plan's rdata rules, all columns) and the trimmed files."""
import re, sys
from pathlib import Path
import pandas as pd, pyarrow.parquet as pq
pd.set_option('display.width',200,'display.max_columns',20,'display.max_rows',100,'display.max_colwidth',50)
cache=Path.home()/'sandbox/parquet-vet/tmp/t3'; data=Path(sys.argv[1])
kinds=['passing_types','possession','passing','defense','misc']; lgs=['ENG','ESP','FRA','GER','ITA']
keep=['MatchURL','Season_End_Year','Team','Player','Player_Href','Pos','Min']
a=pd.concat([pq.read_table(cache/f'{lg}_M_1st_{k}_player_advanced_match_stats.parquet',columns=keep).to_pandas().astype({'Min':'string'}).assign(kind=k,lg=lg) for lg in lgs for k in kinds],ignore_index=True)
a['mid']=a.MatchURL.str.extract(r'/matches/([0-9a-f]{8})/',expand=False)
a['Min']=pd.to_numeric(a.Min).astype('Int64')
print('### player-level union, the rule NOT used')
u=a.drop_duplicates(['mid','Player_Href'])
print('rows',len(u),'| team-match minutes max',int(u.groupby(['mid','Team']).Min.sum().max()),'| same name twice in one team-match',int(u.groupby(['mid','Team','Player']).size().gt(1).sum()))
print('examples:');print(u[u.duplicated(['mid','Team','Player'],keep=False)].sort_values(['mid','Player'])[['mid','Team','Player','Player_Href','Min','kind']].head(4).to_string())
print('\n### URL spellings of one match id')
s=a.groupby(['lg','Season_End_Year','mid']).MatchURL.nunique(); print(s[s>1].to_dict())
print(a[a.mid.isin(s[s>1].index.get_level_values('mid'))].groupby(['MatchURL']).kind.nunique().to_string())
d=a[a.mid.isin(s[s>1].index.get_level_values('mid'))&a.kind.isin(['passing','passing_types','possession'])]
print('two spellings inside one file, keys with differing values:',{k:int((g.groupby(['mid','Player_Href'])[['Pos','Min','Player','Team']].nunique(dropna=False)>1).sum().sum()) for k,g in d.groupby('kind')})
print('serie_a shot rows dated 2023-06-11, the tie-breaker date:',sum(1 for x in pq.read_table(data/'serie_a_shot_data.parquet',columns=['date']).column(0).to_pylist() if x.startswith('2023-06-11')))
print('\n### matches whose row count differs between files')
b=a[~a.MatchURL.str.contains('Monza-Brianza')]
z=b.groupby(['lg','Season_End_Year','mid','kind']).size().unstack(); print(z[z.nunique(axis=1)>1].to_string())
print('\n### Min values that differ by 3+ or are null in some files only, by file')
n=a.groupby(['lg','mid','Player_Href']).Min.agg(['min','max','count','size']); w=n[((n['max']-n['min'])>=3)|((n['count']<n['size'])&(n['count']>0))]
print(a.merge(w.reset_index()[['lg','mid','Player_Href']]).pivot_table(index=['lg','mid','Player'],columns='kind',values='Min',aggfunc='first',dropna=False).dropna(how='all').to_string())
print('\n### empty Pos in the originals')
print(a[a.Pos==''].groupby(['lg','kind','Player_Href']).size().to_dict())
print('\n### trimmed positions and event files')
for lg in lgs:
    pos=pq.read_table(data/f'{lg}_M_1st_positions.parquet',columns=['MatchURL','Season_End_Year']).to_pandas().drop_duplicates()
    ev=pq.read_table(data/f'{lg}_M_1st_match_summary.parquet',columns=['MatchURL','Season_End_Year']).to_pandas()
    for f in (pos,ev): f['mid']=f.MatchURL.str.extract(r'/matches/([0-9a-f]{8})/',expand=False)
    e=ev.drop_duplicates(['MatchURL','Season_End_Year']); two=e[e.duplicated('mid',keep=False)]
    print(lg,'ids with 2 URLs in events',two.mid.nunique(),'seasons',sorted(two.Season_End_Year.unique().tolist()),'event rows on those ids',int(ev.mid.isin(two.mid).sum()),
      '| event ids without positions',e[~e.mid.isin(pos.mid)].drop_duplicates('mid')[['mid','Season_End_Year']].values.tolist(),
      '| Pool position ids without events',pos[pos.Season_End_Year.between(2018,2024)&~pos.mid.isin(ev.mid)].groupby('Season_End_Year').mid.nunique().to_dict())
print('\n### schema of Season_End_Year in event files', {lg:str(pq.read_schema(data/f'{lg}_M_1st_match_summary.parquet').field('Season_End_Year').type) for lg in lgs})
print('schema of positions', [f'{f.name}:{f.type}' for f in pq.read_schema(data/'ENG_M_1st_positions.parquet')])
print('schema of shots', [f'{f.name}:{f.type}' for f in pq.read_schema(data/'epl_shot_data.parquet')])
print('FBref files holding a player_id column:', sum('player_id' in pq.read_schema(cache/f'{lg}_M_1st_{k}_player_advanced_match_stats.parquet').names for lg in lgs for k in kinds), 'of 25')
print('lastAction text None in trimmed shots:', sum(pq.read_table(data/f'{n}_shot_data.parquet',columns=['lastAction']).column(0).to_pylist().count('None') for n in ('bundesliga','epl','la_liga','ligue_1','serie_a')))
print('names holding &#039; in trimmed shots:', sum(1 for n in ('bundesliga','epl','la_liga','ligue_1','serie_a') for p in pq.read_table(data/f'{n}_shot_data.parquet',columns=['player']).column(0).to_pylist() if '&#039;' in p))
```

</details>

<details><summary><code>mutate.py</code></summary>

```python
import sys
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
d=Path(sys.argv[1])
def rw(n,f):
    t=pq.read_table(d/n); df=t.to_pandas(); df=f(df); pq.write_table(pa.Table.from_pandas(df,preserve_index=False),d/n,compression='zstd')
def shot(df): df.loc[5,'xG']=df.loc[5,'xG']+1e-9; return df
def ev(df): df.loc[3,'Event_Type']='Goalx'; return df
def hf(df): return df.iloc[:-1]
def pos1(df): df.loc[10,'Pos']='ZZ'; return df
def pos2(df): u=df.MatchURL.iloc[0]; return df[df.MatchURL!=u]
rw('epl_shot_data.parquet',shot); rw('ESP_M_1st_match_summary.parquet',ev); rw('understat_xg_data.parquet',hf); rw('GER_M_1st_positions.parquet',pos1); rw('FRA_M_1st_positions.parquet',pos2)
print('mutated 5 files')
```

</details>

<details><summary>Full output of <code>t7_verify.py</code> on the final files</summary>

```
### A. plain files: same rows, same order, every kept cell
bundesliga_shot_data: source rows 88214 trimmed rows 88214 columns 14 cells 1234996 differences 0 
epl_shot_data: source rows 107838 trimmed rows 107838 columns 14 cells 1509732 differences 0 
la_liga_shot_data: source rows 100188 trimmed rows 100188 columns 14 cells 1402632 differences 0 
ligue_1_shot_data: source rows 96140 trimmed rows 96140 columns 14 cells 1345960 differences 0 
serie_a_shot_data: source rows 110026 trimmed rows 110026 columns 14 cells 1540364 differences 0 
ENG_M_1st_match_summary: source rows 37734 trimmed rows 37734 columns 6 cells 226404 differences 0 
ESP_M_1st_match_summary: source rows 44873 trimmed rows 44873 columns 6 cells 269238 differences 0 
FRA_M_1st_match_summary: source rows 37503 trimmed rows 37503 columns 6 cells 225018 differences 0 
GER_M_1st_match_summary: source rows 34742 trimmed rows 34742 columns 6 cells 208452 differences 0 
ITA_M_1st_match_summary: source rows 43180 trimmed rows 43180 columns 6 cells 259080 differences 0 
understat_xg_data: source rows 27182 trimmed rows 27182 columns 12 cells 326184 differences 0 
master_player_stats: source rows 34246 trimmed rows 34246 columns 7 cells 239722 differences 0 

### B. positions: every match equals one source file's rows for that URL, none lost
ENG: rows before 413736 after 83613 | matches 2939 source ids 2939 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['str'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ESP: rows before 421890 after 87400 | matches 2921 source ids 2921 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['str'], 'possession': ['str'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
FRA: rows before 395313 after 79421 | matches 2701 source ids 2701 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['str'], 'misc': ['str']}
GER: rows before 348924 after 69868 | matches 2348 source ids 2348 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ITA: rows before 425429 after 87300 | matches 2917 source ids 2917 lost 0 | matches equal to no source file 0 | Min types {'passing_types': ['float'], 'possession': ['str'], 'passing': ['str'], 'defense': ['str'], 'misc': ['float']}
total rows before 2005292 after 407602 | matches equal to no source file 0 | source ids lost 0
identical-match credit, first file in order that equals the output (a match can equal several): {'passing_types': 406333, 'misc': 704, 'possession': 216, 'defense': 349}

### C. what the five files disagree on, same match id and same Player_Href, present in 2+ files
Pos: keys differing 365 in Pool seasons 227 | rows off the most common value, by file {'possession': 8, 'misc': 215, 'passing_types': 3, 'passing': 53, 'defense': 102}
Min: keys differing 37 in Pool seasons 13 | rows off the most common value, by file {'possession': 6, 'misc': 26, 'passing_types': 8, 'passing': 8, 'defense': 3}
Player: keys differing 94 in Pool seasons 94 | rows off the most common value, by file {'misc': 94}
Pos: keys where one file says attacking and another not 85 in Pool seasons 55

### D. counts per league-season against the T3 report text
shots bundesliga: seasons 12 differences {}
shots epl: seasons 12 differences {}
shots la_liga: seasons 12 differences {}
shots ligue_1: seasons 12 differences {}
shots serie_a: seasons 12 differences {}
positions ENG: seasons 9 differences (T3, trimmed) {}
positions ESP: seasons 9 differences (T3, trimmed) {}
positions FRA: seasons 9 differences (T3, trimmed) {}
positions GER: seasons 9 differences (T3, trimmed) {}
positions ITA: seasons 9 differences (T3, trimmed) {2023: (383, 379)}
events ENG: seasons 8 differences {}
events ESP: seasons 8 differences {}
events FRA: seasons 8 differences {}
events GER: seasons 8 differences {}
events ITA: seasons 8 differences {}
HF understat_xg_data: rows 27182 league-seasons in T3 50 differences [] | not in T3 table 0
HF master_player_stats: rows 34246 league-seasons in T3 60 differences [] | not in T3 table 0
T3 totals in text: shots 502406 True | trimmed shot rows 502406 | HF 27182 and 34246: 27182 34246

### E. Serie A extras and player identity in the trimmed positions
URLs holding Monza-Brianza kept: 0 | Monza 2023/24 matches: 38
Matchweek values not 'Matchweek N': Counter({'Serie A (Relegation tie-breaker)': 31})
tie-breaker rows 31 https://fbref.com/en/matches/e0449015/Spezia-Hellas-Verona-June-11-2023-Serie-A 2023-06-11 Serie A (Relegation tie-breaker)
players at 900+ only because of the tie-breaker: []
ITA 2023/24 matches per team, not 38: {'Fiorentina': 37, 'Atalanta': 37} | distinct matches 379
shot file match 22585 rows 20 date 2024-06-02 16:00:00
team-match minutes max 990 min 825 | same FBref id twice in a match 0
null Min rows {('ENG', 2018): 1, ('FRA', 2023): 1, ('FRA', 2026): 1, ('ITA', 2022): 1, ('ITA', 2024): 1} | empty Pos rows 0 | null Pos 0
same name, team and season under two FBref ids: {('FRA', 2024, 'Marseille', 'Abdoul Meité'): {'8eb68164': 296, 'cb9ef70f': 7}, ('FRA', 2024, 'Metz', 'Joseph Nduquidi'): {'1d039497': 194, 'f365b837': 1}, ('ITA', 2024, 'Lecce', 'Gabriel Strefezza'): {'674cfc5a': 703, 'ac4a4508': 410}}
id-seasons holding several Player_Href spellings: 40

### F. event URLs against positions URLs
ENG: event URLs 2908 event ids 2899 | URLs not in positions 9 | ids not in positions [] | positions ids not in events 40
ESP: event URLs 2871 event ids 2870 | URLs not in positions 1 | ids not in positions [] | positions ids not in events 51
FRA: event URLs 2656 event ids 2655 | URLs not in positions 1 | ids not in positions [] | positions ids not in events 46
GER: event URLs 2349 event ids 2320 | URLs not in positions 30 | ids not in positions ['c34bbc21'] | positions ids not in events 29
ITA: event URLs 2814 event ids 2809 | URLs not in positions 6 | ids not in positions ['e0a20cfe'] | positions ids not in events 109

plain-file cells compared 8787782 differences 0

### G. MANIFEST rows and columns against the files
trimmed files 17 mismatches 0 | source rows in manifest 38
schemas differ within group: {'*_shot_data.parquet': 1, '*_positions.parquet': 1, '*_match_summary.parquet': 2}
```

</details>
