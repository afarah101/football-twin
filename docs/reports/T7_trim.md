# T7: stand-in backfill, trim into private Parquet

Run date: 2026-11-04, the re-trim and the rule 3 measurement. First trim: 2026-11-03. Issue: #7. Repo position at the first trim: `39b1c3a`, level with origin. This version is the re-trim Ahmed asked for after `8c93206`. Numbers come from output shown in this report, or from the script, file or commit the text names. The audit sections say where theirs come from. The check scripts are in the appendix, because they sit outside this task's scope, except `link_and_check.py` from Step 0, the hash, file size and old shot column check under "Re-trim with `h_a` and `home_away`", and the club map re-check in section 9.

## Verdict

| Criterion of #7 (word for word) | Result |
|---|---|
| The vetted worldfootballR, FBref and HF files are stored privately as Parquet, with only the columns the build needs | **Met**: 17 Parquet files in `data/standin/`, private repo, plus `club_map.csv`. One of them, `master_player_stats`, has no planned use, see Findings |
| The kept columns are listed for each file | **Met**: section 2 and `MANIFEST.md` |
| The hash of each original file is recorded | **Met**: all 38 in `MANIFEST.md` |
| The trim script is committed, and running it again on the originals gives the same rows and columns | **Met**: all 19 output files byte-identical across two runs. "Committed" is met by this commit. |
| Nothing is fetched from the network | **Met**: both runs had network access denied |
| Counts per league-season match the STEP 0 coverage report | **Met, with one stated exception**: ITA 2023/24 goes from 383 to 379 URLs, because the de-duplication asked for removes 4 spellings. All other counts match. |

**Ready for #6: YES.** The date link is decided and `data/standin/` holds what it needs. Ahmed has reviewed and approved the club map, see section 9.

## Findings

| Severity | Finding | Section |
|---|---|---|
| Warning for #6 | Rule 2 must use the decided link, not an exact date. An exact-date link leaves 19 Pool matches unmatched. The decided link leaves 3 (73 shot rows), which have no rows in the FBref player stat files. FBref's event files do hold 2 of them (Bochum v Borussia M.Gladbach 6 rows, Verona v Roma 10 rows), so those 2 are in FBref but have no minutes. The other 16 (384 shot rows) link with gaps of 1, 2 or 11 days. | 10 |
| Warning, **approved by Ahmed**, see section 9 | Club map: 43 mappings are not exact name matches, and 14 clubs are unmapped. All 14 are Understat-only clubs, and none has a Pool-season match. Both lists are in section 9. Two were flagged for the review: `Real Oviedo` to `Oviedo` rests on 4 matches, and `Parma` and `Parma Calcio 1913` both reach `Parma`, in different seasons. | 9 |
| Warning | Combining per player would have been wrong. One player can have different hrefs in different files for one match, which gives 201 cases of one name counted twice in a team's match, and team-match minutes up to 1170. Each match therefore comes whole from one file, and the maximum is 990. | 4 |
| Warning | Majority `Pos` matches players by the 8-character id only, as asked. A player with different ids in different files gets fewer votes, which `Pos_Files_Voted` shows. | 4 |
| Warning for #6 | Key players on the 8-character id inside `Player_Href`, not the whole value. 40 id-seasons hold several spellings of the href. | 7 |
| Warning for #6 | Event files were not de-duplicated, so their counts stay equal to T3. 45 match ids hold two URLs, all in 2023/24, on 1416 event rows. 47 event URLs are not in the positions files. Join on the 8-character match id and handle repeats. | 8 |
| Info | Rule 4 changes little. The majority changes `Pos` on 3 rows, all ENG 2024/25, so 0 in Pool seasons. One row ties and keeps the chosen file's value: Gabriel Strefezza, ITA 2022/23. The files disagree on 365 player-match keys, but the first file in the order is nearly always the majority. | 4 |
| Info | The plan line for rule 4 still says "Rule for #6". The trim now applies it, so #6 reads `Pos` as given and cannot recompute it. Only the rule 2 line was in scope to edit. | 4 |
| Info | 101 Pool-season matches have positions but no event rows, so the rule that ignores substitute appearances cannot apply to them. T3 reported the gaps by file. | 8 |
| Info | T3 says `Min` is text. In fact it is text in some files and float in others, even within a league. Both cast cleanly to integer. | 4 |
| Info | 5 rows have no `Min` and no file gives a value. They stay null. | 4 |
| Info | No FBref stat file has a `player_id` column, 0 of 25. `Player_Href` holds the FBref id, and it is kept. Understat `player_id` is kept in shot files. | 2 |
| Info | No planned field reads `master_player_stats.csv`. It is stored in 7 columns because the criterion names the HF files and T3 counts it. It includes NED rows. It could be dropped later. | 2 |
| Info | `Season_End_Year` is `int64` in the ENG event file, from CSV, and `int32` in the other four. `id`, `season`, `match_id` and `player_id` in shot files are doubles, as stored. | 2 |
| Info | `requirements.txt` pins 4 direct libraries. Transitive packages are not pinned (`packaging`, `python-dateutil`, `typing_extensions`, `tzdata`, `xarray`). Byte identity was tested only on Python 3.15.0, macOS arm64. | 5 |
| Info | The outside check used `pyreadr`, which the project does not allow, inside `~/sandbox` only, as T3 did. It is not in the repo or in `requirements.txt`. | 3 |

**Decided by Ahmed, now in the plan's Stand-in source decisions:**

1. Tie-breaker matches are excluded from minutes and shots, by filtering on `Matchweek`. #6 does this. The shot file has no rows on that date, so only minutes change.
2. Pool seasons only (2017/18-2023/24): shot rows for matches with no FBref minutes are dropped, and #6 reports the rows per league-season. 2014/15-2016/17 shot rows stay unchanged. **The date link is decided:** same home club and same away club, in that order, in the same season, nearest FBref date, at most 14 days. Over 14 days is no link, and the rows are dropped and counted. #6 records `date_gap_days` on every linked row and lists every gap over 1 day. `home_team` and `away_team` in the shot files, and `Home_Team` and `Away_Team` in the positions files, are there for this.
3. One player under two FBref ids merges only when name, team and season match and their matches never overlap. #6 does this and lists every merge. Before merging, #6 should note that Strefezza's two ids total 1113 minutes. The merge moves the Pool to 3,109, see F3 in the audit of `6666192..811d245`.
4. Majority `Pos`. The trim applies it, because `data/standin/` holds one `Pos` per row and #6 would have nothing to count. Each row records `Pos_Files_Voted` and `Pos_Tie`.
5. #6 re-cuts `tests/fixtures/standin/` from `data/standin/`. Those fixtures still hold the original schema.

**Open for Ahmed:** the 55 rows Ahmed has not checked, out of the 50 pairs in `docs/reports/name_map_sample.csv` and the 14 anchors, and the `partial_join` player-seasons and Bamo Meïté FRA 2023/24 under "Joining shots to players". Decisions go in `data/standin/review_decisions.csv`, which the plan's rule 3 defines. Row 1 is the Ezzalzouli approval. `scripts/measure_rule3.py` reads the file. It applies only `approve` on a link, at the guard rather than after rule 3, so its "After the minutes guard" line already holds the 30 Ezzalzouli rows. It prints any other row, including `merge_ids`, as not applied, so its numbers are otherwise before the decisions.

Review of the 50 sample pairs and 14 anchors, 2026-11-04: Ahmed checked 3 players on the FBref website, covering 9 rows. Gabriel (4 rows): FBref id 67ac5bb8 is Gabriel Magalhães, centre-back. Kiké (4 rows): the player is Enrique García Martínez, and the FBref website minutes equal the stand-in FBref minutes in all 4 seasons (2,460, 3,087, 1,862, 1,021). Raúl García (1 row): the player is Raúl García de Haro, Osasuna. All 9 rows are the same player. The other 55 rows were read by Claude from memory, with no source opened; none looked wrong. This is weak evidence, not a check. No row was marked N, so no reject rows were added.

## Known limits, from the audit of `6666192`

Logged, not fixed. The numbers here come from that audit, not from output in this report. Its findings F1, F3 and F5 became plan rules, and F6, F7 and F12 were wording fixes in this report. Plan terms from those rules are not in `GLOSSARY.md` yet, and `name_map.csv` and `review_decisions.csv` sit outside the generated `MANIFEST.md`. #6 settles both.

| Finding | Limit |
|---|---|
| F1, wording | The finding above says 101 Pool matches have no event rows. That count includes the tie-breaker, so it is 100 once rule 1 removes it. |
| F2 | 305 of 91,589 Pool substitute events do not match a `Player` exactly in that match and team, for example `Kike`, `Randy Ntekja` and `Martinelli`. One event, `Chris Smalling`, has no " for ". Event rows hold no ids. A rough name repair flipped 0 Pool memberships. |
| F4 | The shot `league` column has two spellings in 3 files: `La_liga` and `La liga`, `Ligue_1` and `Ligue 1`, `Serie_A` and `Serie A`. Take the league from the file name, as T3 does. |
| F8 | The opening line said the check scripts are in the appendix, but `link_and_check.py` from Step 0 is not. It now says so. The audit reproduced its result separately: 38 of 38 hashes agree. |
| F9 | The audit did not re-run the `pyreadr` check, the mutation test or the fresh-venv run, and has no record to check the code review log against. Ahmed's two re-date checks are not from the data files. An outside source confirms Caen v Toulouse. For Udinese v Roma, only the shot minutes are consistent with it. |
| F10 | Closed. "Ready for #6: YES" stood while the club map review was open, and Ahmed has since approved the map, see section 9. |
| F11 | The plan's "Each ordered pair plays once per season" holds only after the tie-breaker filter. Spezia v Hellas Verona appears twice in 2022/23. The nearest date still picks the right match. |

## Audit of `6666192..811d245`

Run 2026-11-04. Verdict FAIL: 0 Critical, 1 Major, 11 Minor. Its F numbers are its own, not those in the table above. Its numbers come from that audit, except where a line says they were re-measured.

**Fixed or stated:**

| Finding | State |
|---|---|
| F1, Major | The plan's step 2 said two shot names reaching one roster player block each other, but the code lets a name with 2+ candidates link no one and block no one. "Ángel" links to Ángel Rodríguez, ESP 2020/21 Getafe, while "Chema Rodríguez" has Chema and Ángel Rodríguez as candidates. Under the old wording id 4136 falls to 30 of 38 rows, gets `partial_join = yes` and the Pool is 3,107. The plan now matches the code. `tests/test_measure_rule3.py` holds the case. Patching `name_map_links` to drop any link to a candidate of a 2+ candidate name, the old wording's behaviour, makes 2 of its 4 tests fail. |
| F2 | The script's docstrings no longer read as if every stale or invalid row stops. Today a stale key stops only for `approve` on a link. Unknown values and two rows on one key stop for every row. The plan's other stops are #6 work. |
| F3 | **#6's id merges move the Pool.** Re-measured, see the output below: applying the plan's merge rule in memory and running the script gives 3 merges (Abdoul Meité, Joseph Nduquidi and Gabriel Strefezza, all 2023/24), 3,137 candidates and a Pool of **3,109**, not 3,108. The only new candidate is Strefezza ITA 2023/24. The audit found all 28 of his shot rows join. Joined rows stay 315,073. |
| F4 | `MIN_JOINED_ROWS` is now 315,073. The script now fails unless the Pool is 3,108 and the candidates are 3,136. #6 changes those two numbers when it runs the merges. |
| F6 | "After the guard" under "Change from taking the club from rosters" now compares like with like. |
| F7 | The opening line no longer claims every number comes from this report's output, and the run date is current. Still missing: two checks show a result but have no script in the appendix, the hash, file size and old shot column check under "Re-trim with `h_a` and `home_away`", and the club map re-check in section 9. The opening line now says so. |
| F8 | The 144 player-seasons have no FBref link. They were wrongly described as having no FBref id. |
| F9 | **`merge_ids` today:** the script accepts the word in `review_decisions.csv`, prints the row as not applied, and applies nothing. The subject of `811d245`, "add merge_ids", overstates this. #6 applies it. |

<details><summary>F3: the check script and its output</summary>

```python
"""Apply the plan's id merge in memory, then run scripts/measure_rule3.py unchanged. Run from the repo root, with a scratch folder as argument."""
import contextlib, io, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import measure_rule3 as m

m.ROOT = Path(sys.argv[1])
m.SAMPLE_FILE = m.ROOT / "sample.csv"
unmerged = m.load_positions

def merged():
    rows = unmerged()
    for (league, year, team, player), part in rows.groupby(["league", "Season_End_Year", "Team", "Player"]):
        ids = sorted(part["fbref_id"].unique())
        matches = [set(part.loc[part["fbref_id"] == i, "match"]) for i in ids]
        if len(ids) > 1 and sum(map(len, matches)) == len(set().union(*matches)):
            print("merge", league, year, team, player, ids)
            rows.loc[(rows["league"] == league) & (rows["Season_End_Year"] == year) & rows["fbref_id"].isin(ids), "fbref_id"] = ids[0]
    return rows

m.load_positions = merged
out = io.StringIO()
with contextlib.redirect_stdout(out), contextlib.suppress(SystemExit):
    m.main()
print("\n".join(line for line in out.getvalue().splitlines() if line.startswith(("merge", "After id collisions", "Pool until"))))
with contextlib.redirect_stdout(io.StringIO()):
    after = set(m.pool_candidates(merged()))
print("new candidates:", sorted(after - set(m.pool_candidates(unmerged()))))
```

```
merge FRA 2024 Marseille Abdoul Meité ['8eb68164', 'cb9ef70f']
merge FRA 2024 Metz Joseph Nduquidi ['1d039497', 'f365b837']
merge ITA 2024 Lecce Gabriel Strefezza ['674cfc5a', 'ac4a4508']
After id collisions: 315073 (99.27%)
Pool until Ahmed's review: 3109 of 3137 candidates
new candidates: [('ITA', 2024, '674cfc5a')]
```

</details>

**F10, changes no message or report had stated:**

- `021e499` removed `minutes_check = approved` from the plan's `name_map.csv` line. It is back: the line now names `minutes_check = none` and `minutes_check = approved`, which matches the 1,117 pairs, including Ezzalzouli, whose check is `approved`.
- `approved_keys` in `scripts/measure_rule3.py` holds `approve` rows of both link item types, so an `approve` on a `name_map` key also approves a `season_anchor` link with the same key, and the reverse.
- `read_review_decisions` reads with `utf-8-sig`, so a byte order mark from a spreadsheet save does not break the first column. The plan does not ask for this.

**Listed limits, not fixed:**

| Finding | Limit |
|---|---|
| F5 | Substitute detection has gaps, with 0 Pool flips across 3 separate repairs. `pool_candidates` combines both URLs of a match, which marks 4 players as substitutes when one URL alone would not, including Carlton Morris (90 minutes). The 305 off-roster names are F2 in the table above. |
| F11 | The repo cannot prove "approved by Ahmed" (section 9, and row 1 of the review decisions, which arrived in `021e499`, co-authored by Claude). Ahmed can confirm. The fresh-venv run, mutation test, code-review log and the Caen and Udinese re-date checks were not re-run. |
| F12 | Already disclosed: plan terms missing from `GLOSSARY.md`, `review_decisions.csv` outside `MANIFEST.md`, `approve` applied at the guard rather than after rule 3 (it changes exactly 30 rows, so no anchor spillover), and "plays once per season" holding only after the tie-breaker filter. `self_check` and `tests/test_measure_rule3.py` still leave most of the guard, the id collision rule, the date link and the decision reader without tests. |

## Audit of `6666192..main`

Run 2026-11-04. Verdict FAIL: 0 Critical, 1 Major, 9 Minor. Its F numbers are its own, not those in the sections above, and the numbers in its limits come from that audit.

**Fixed:**

| Finding | State |
|---|---|
| F1, Major | **Word order.** The code's step 2 compares name words as a set, and the plan's step 2 did not say so. It does now. Step 1 still compares in order. Re-measured by patching step 2 to keep word order, see the output below: the rule reaches 261 shot groups, 24 player-seasons and 433 rows. Without it, joined rows are 314,640 and the Pool is 3,099, against 315,073 and 3,108. `tests/test_measure_rule3.py` holds Hee-Chan Hwang to Hwang Hee-chan (ENG 2021/22 to 2023/24), and Abdul Rahman Baba to Baba Rahman (8 rows, 3 player-seasons), the only real rows that need the roster name inside the shot name as a set. The other direction has 0 real rows out of order, so `self_check` holds it. |
| F2 | The "2+ FBref ids" check is keyed on league, season and Understat id, not also the name, and it counts exact, step 1 and step 2 links together. Only step 2 links stop. 0 conflicts today, and no number changed. Guirassy GER 2023 has two spellings and one FBref id. A `self_check` assert fails on the old behaviour. **Printed label:** the line in `scripts/measure_rule3.py` changed from "One Understat id and name on 2+ FBref ids:" to "One Understat id on 2+ FBref ids:", and its keys no longer hold the name. |
| F3 | The plan now says exact and step 1 do not link when 2+ roster players match, and that 2+ exact matches skip step 1. Step 2 now says a shot name with 2+ roster matches after step 1 also goes to step 2. 0 groups today, so this is plan text only. |
| F4 | Bamo Meïté FRA 2023/24 is listed for Ahmed's review under "Joining shots to players", with "same player" stated as an inference from minutes. |
| F8 | The plan's `name_map.csv` line names `minutes_check = approved` again, and the first bullet under "F10, changes no message or report had stated" in the audit above matches it. |

<details><summary>F1: the check script and its output</summary>

```python
"""Run scripts/measure_rule3.py unchanged, with step 2 keeping word order. Run from the repo root, with a scratch folder as argument."""
import contextlib, io, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import measure_rule3 as m

def held_in_order(a, b):
    return any(b[i:i + len(a)] == a for i in range(len(b) - len(a) + 1))

positions, shots = m.load_positions(), m.load_shots()
links, _, _ = m.link_matches(shots, positions, m.understat_to_fbref_clubs())
rows_of, _ = m.shot_groups(shots, links, positions)
groups, rosters = sorted(rows_of), m.build_rosters(positions)
joined = m.join_by_name(groups, rosters)
with_rule = m.name_map_links(groups, rosters, joined)[0]
m.is_name_map_candidate = lambda shot, roster: roster[-1] == shot[-1] or held_in_order(shot, roster) or held_in_order(roster, shot)
without_rule = m.name_map_links(groups, rosters, joined)[0]
lost = [group for group in with_rule if without_rule.get(group) != with_rule[group]]
print("groups", len(lost), "| player-seasons", len({group.player_season for group in lost}), "| rows", sum(rows_of[group] for group in lost))
m.self_check = lambda: None  # its asserts hold the rule this script removes
m.ROOT = Path(sys.argv[1])
m.SAMPLE_FILE = m.ROOT / "sample.csv"
out = io.StringIO()
with contextlib.redirect_stdout(out), contextlib.suppress(SystemExit):
    m.main()
print("\n".join(line for line in out.getvalue().splitlines() if line.startswith(("After id collisions", "Pool until"))))
```

```
groups 261 | player-seasons 24 | rows 433
After id collisions: 314640 (99.14%)
Pool until Ahmed's review: 3099 of 3136 candidates
```

</details>

**Listed limits, not fixed:**

- F5: Most of rule 3 has no committed test: the date link, the decision reader and most of the guard. Collision removal has never run on real data.
- F6: 6 of 10 review_decisions changes exit 0, and approve with an fbref_id prints nothing. Given to #6 by plan:143.
- F7: Some report claims are not reproducible from the repo: Ahmed's approvals (club map, row 1), the re-date checks, the code review log, the t7_verify.py comparison and the planted-fault run.
- F9: Substitute detection has gaps: 305 of 91,589 events match no roster name, and 4 players are marked as substitutes through two-URL matches (including Carlton Morris, 90 minutes). 0 Pool flips.
- F10: Plan terms are missing from GLOSSARY.md, including partial_join and name_match. Left for #6.
- The 2+ roster matches clauses (exact and step 1, plan:130) have 0 real cases and no test. The 2+ candidates rule in step 2 is separate: it has 109 real groups and the Chema test. #6 ticket 1 must test every rule 3 clause in the new join module.

## Joining shots to players, measured for #6

Measured on the current `data/standin/`, with the plan's rule, on the 317,385 Pool shot rows in linked matches. The club comes from `h_a` plus the linked match. `scripts/measure_rule3.py` prints these numbers, reading `data/standin/` only. The block below is an excerpt of its output. It measures before any FBref id merges, which #6 runs before the guard. `name_map.csv` does not exist yet, because #6 writes it.

```
$ python3 scripts/measure_rule3.py
Pool shot rows in linked matches: 317385
Exact: 262838 (82.81%)
After step 1: 295066 (92.97%)
After step 2: 314845 (99.20%)
After the minutes guard: 314844 (99.20%)
After season anchors: 315073 (99.27%)
After the guard on anchors: 315073 (99.27%)
After id collisions: 315073 (99.27%)
Unjoined: 2312
ENG: exact 90.47 / step 1 97.19 / step 2 99.62 / final 99.65
ESP: exact 80.38 / step 1 87.17 / step 2 98.35 / final 98.60
FRA: exact 75.65 / step 1 88.83 / step 2 99.41 / final 99.49
GER: exact 87.62 / step 1 95.81 / step 2 99.60 / final 99.60
ITA: exact 80.01 / step 1 95.43 / step 2 99.06 / final 99.05
Name map player-seasons 1118, rows 19779 | {'agree': 1109, 'approved': 1, 'disagree': 1, 'none': 7}
Keep their link: 1117 player-seasons, 19778 rows
Wrong same-club players who would pass the limit: 3104 of 32474 (9.6%)
2+ candidate groups 109, rows 235 | linked groups 105, rows 229
Guard on 14 anchor player-seasons: {'agree': 14}
Partly joined before anchors: 20, holding 255 unjoined rows | now fully joined 14 | still partly joined 6, holding 26 unjoined rows
partial_join = yes: 149 player-seasons | some rows joined 5, holding 25 unjoined rows | no rows joined 144, holding 2286 rows
Collisions: 0
Pool candidates with shots: 3109 of 3136 (99.14%)
Pool until Ahmed's review: 3108 of 3136 candidates
```

- **Change from taking the club from rosters:** compared with the measurement in `03a9277`, which the script no longer reproduces, joined rows after the guard go from 314,806 to 314,844, and id collisions from 3 to 0. Once collisions are removed, before season anchors, rows go from 314,630 to 314,844. Luis Suárez ESP 2021/22, Raúl García ESP 2023/24 and Danilo ITA 2019/20 no longer collide.
- **`h_a` against the rosters, the outside check:** in only 4 shot groups (6 rows) is the name on the other club's roster and not on the `h_a` club's. All 4 are those former collisions, where FBref's name differs from the shot's: Luis Suárez at Granada (2 groups), Raul García at Osasuna and Danilo at Bologna. In these, `h_a` is right and the roster reading was wrong.
- **Minutes guard:** the limit is the larger of 90 minutes or 10%.
  - **Not linked, 1:** André Anderson to Djavan Anderson, ITA 2019/20 (49 v 167, 1 row), a false link.
  - **Approved by Ahmed, 1:** Abdessamad Ezzalzouli to Abde Ezzalzouli, ESP 2023/24 (839 v 933, gap 94, limit 93.3, 30 rows).
  - **`minutes_check = none`, 7:** all Sehrou Guirassy, whom the season file spells Serhou, on 298 rows.
  - **What the guard cannot catch:** tried against every other same-club player, 9.6% of wrong pairs still pass the limit. It is a filter, not proof.
- **Sample for Ahmed's check:** `docs/reports/name_map_sample.csv` holds 50 of the 1,117 pairs, drawn with a fixed seed. Pairs are drawn equally, so a pair with 1 shot row counts as much as one with 61.
- **Season anchors, step 3:** 229 rows gained, on 105 shot groups and 14 player-seasons. 14 of the 20 partly joined player-seasons are now fully joined, and all 14 agree with the guard.
  - **What they rest on:** all 14 player-seasons are anchored on `name_match = map` links, not exact ones. A wrong map link with 2+ matches would spread, and the guard is the only check on that.
  - **Club check:** 0 links where `h_a` disagrees with the club, but that holds by construction, because the club comes from `h_a` and anchors stay inside it. The separate checks also find 0: no link has a player without minutes in that match, and no link's club is missing from the Understat season file's team list.
  - **Not linked, 4 groups, 6 rows:** Chema Rodríguez ESP 2019/20 (2 rows) and 2020/21 (3 rows), and Tariqe Fosu-Henry ENG 2021/22 (1 row).
- **`partial_join = yes`, 149 player-seasons:** counted per Understat `player_id`, over shot rows in linked matches.
  - **Some rows joined, 5, 25 unjoined rows:** Jeffinho FRA 2022/23 (1 of 10), Chema Rodríguez ESP 2019/20 (1 of 3), Rasmus Kristensen ITA 2023/24 (4 of 10), Randy Nteka ESP 2023/24 (8 of 15) and Dennis Johnsen ITA 2021/22 (14 of 15, 93.3%). Only Johnsen is a Pool candidate.
  - **No rows joined, 144, 2,286 rows:** listed below. These have no FBref link, because none of their shot rows joined an FBref id, for example Isi Palazón, Ruslan Malinovskiy, Juan Camilo Hernández and Simy.
  - **Above the line, no flag:** Marc Cardona ESP 2023/24 has 21 of 22 rows joined (95.5%).
  - **Pool candidates, 28, out of the Pool until Ahmed reviews them:** this leaves 3,108 of 3,136, before #6's id merges. They are Dennis Johnsen above and the 27 Pool candidates with no joined shots, which the plan's rule also flags because they hold no link to their Understat rows. They include Ruslan Malinovskyi, Isaac Palazón Camacho, Cucho and Javier Hernández. Some are the same people as the 144, seen from the FBref side, so the two counts do not add up to a total.
- **One Understat id on 2+ FBref ids:** Joseph N'Duquidi FRA 2023/24 and Gabriel Strefezza ITA 2023/24. These are the known two-id players that the plan's id merge handles.
- **Bamo Meïté FRA 2023/24, for Ahmed's review:** Understat gives 761 minutes. FBref gives Bamo Meïté `04ac78d2` 481 (Lorient 146, Marseille 335) and Abdoul Meité 303 (Marseille, `8eb68164` 296 and `cb9ef70f` 7). Source: Understat's is `minutes` in `data/standin/understat_xg_data.parquet`, season `2023-2024`. FBref's are `Min` summed from `data/standin/FRA_M_1st_positions.parquet`, `Season_End_Year` 2024, read through `load_positions` in the script, which takes the id from `Player_Href`. The script does not print these numbers.
  - **"Same player" is an inference from minutes.** No file says so, and no outside source was checked. Together FBref's two names give 784, a gap of 23 to Understat, against a gap of 280 for Bamo alone. Also consistent with it: the 3 ids share no match, and Understat's season file holds no other Meité that season.
  - **What it changes today:** nothing in the numbers. The 1 shot row joins `04ac78d2` at the exact step, so the guard never compares these minutes. The plan's id merge joins Abdoul's 2 ids but not Bamo's, because the names differ. Neither name is a Pool candidate, and 784 is under the 900-minute gate.
  - **If they are the same player:** in `review_decisions.csv`, no row type merges two non-Pool FBref ids with different names, so #6 would need one.
- **Still unjoined:** 2,312 rows. The largest are Ruslan Malinovskiy (261 rows in ITA), Isi Palazón (224), Juan Camilo Hernández (153), Simy (128) and Silas Wamangituka (112). 27 Pool candidates have no joined shots, for example Javier Hernández ("Chicharito"), Cucho and Silas Katompa.
- **Named cases:** Raul García 8042 to FBref's Raúl `18f0a9f0`; Raúl García 5114 to `1a317a1b`; Bruno 2302 to Bruno Soriano `09332647`; Ousmane Camara 11016 to `7d3dfdfd` and 11249 to `5a6b06cd`; Luis Suárez 2098 to `a6154613` and 8978 to Luis Javier Suárez `eeba07f8`; Danilo 2244 to `94b2001f` and 1140 to Danilo Larangeira `fed5f993`.

<details><summary>The 144 player-seasons with no rows joined: league, Understat season, id, name, rows, Understat minutes</summary>

```
ESP 2022 9812 ['Isi Palazón'] 94 3041
ESP 2018 6954 ['Juan Camilo Hernández'] 80 2171
ITA 2019 7947 ['Ruslan Malinovskiy'] 79 1500
ESP 2023 9812 ['Isi Palazón'] 72 2854
ITA 2020 7947 ['Ruslan Malinovskiy'] 67 1896
ITA 2020 1362 ['Simy'] 64 2935
ESP 2021 9812 ['Isi Palazón'] 58 2330
ITA 2021 7947 ['Ruslan Malinovskiy'] 57 1594
ITA 2022 6434 ['Franck Zambo'] 50 3077
FRA 2023 11782 ['Mousa Al Tamari'] 47 1969
ESP 2019 6954 ['Juan Camilo Hernández'] 45 1506
GER 2020 8807 ['Silas Wamangituka'] 45 1949
ESP 2023 11322 ['Viktor Tsygankov'] 44 2118
ESP 2023 12305 ['Isaac Romero'] 42 1079
GER 2022 8807 ['Silas Wamangituka'] 42 2020
ITA 2023 7947 ['Ruslan Malinovskiy'] 39 1551
ENG 2018 191 ['Chicharito'] 37 1336
GER 2023 3682 ['Jordan Siebatcheu'] 36 1475
ESP 2023 2551 ['Pepelu'] 35 3314
ENG 2020 6434 ['Franck Zambo'] 34 2582
ENG 2021 6954 ['Juan Camilo Hernández'] 34 1125
FRA 2017 6434 ['Franck Zambo'] 34 2429
FRA 2022 7947 ['Ruslan Malinovskiy'] 34 1242
GER 2022 3682 ['Jordan Siebatcheu'] 34 1336
ITA 2023 6434 ['Franck Zambo'] 33 2793
ESP 2020 8933 ['Marcos de Sousa'] 32 1159
ESP 2022 8461 ['Nicolás Melamed'] 32 1254
ITA 2017 1362 ['Simy'] 31 1199
ESP 2019 6434 ['Franck Zambo'] 30 2582
ESP 2021 8933 ['Marcos de Sousa'] 30 933
ENG 2017 191 ['Chicharito'] 29 1524
ESP 2020 6954 ['Juan Camilo Hernández'] 28 1479
ITA 2022 3785 ['Kelvin Adou'] 26 2374
ITA 2021 3785 ['Kelvin Adou'] 25 2656
GER 2023 8807 ['Silas Wamangituka'] 24 861
FRA 2021 5773 ['Zaydou Youssef'] 22 1566
ENG 2018 6434 ['Franck Zambo'] 21 1515
ITA 2019 1927 ['Berat Gjimshiti'] 21 2800
ITA 2020 1927 ['Berat Gjimshiti'] 21 2623
ESP 2021 8461 ['Nicolás Melamed'] 20 1058
ESP 2022 11322 ['Viktor Tsygankov'] 20 1501
FRA 2018 3682 ['Jordan Siebatcheu'] 20 605
ITA 2021 1362 ['Simy'] 20 839
ITA 2021 6434 ['Franck Zambo'] 20 1915
ITA 2022 7947 ['Ruslan Malinovskiy'] 19 525
ESP 2023 8410 ['Rodrigo Sánchez'] 18 988
FRA 2018 3785 ['Kelvin Adou'] 18 2880
ESP 2022 8933 ['Marcos de Sousa'] 17 416
ESP 2023 11746 ['Pejiño'] 17 489
ITA 2021 1927 ['Berat Gjimshiti'] 17 2250
ESP 2021 8410 ['Rodrigo Sánchez'] 15 884
ESP 2022 8410 ['Rodrigo Sánchez'] 15 1625
FRA 2017 3785 ['Kelvin Adou'] 15 3155
FRA 2020 5773 ['Zaydou Youssef'] 15 1219
ENG 2017 3979 ['Ahmed Hegazy'] 14 3389
ESP 2021 2551 ['Pepelu'] 14 1998
FRA 2021 9661 ['Igor Silva'] 14 1567
ENG 2017 6030 ['Zanka'] 13 3420
ENG 2022 10750 ['Rasmus Kristensen'] 13 1964
ESP 2019 191 ['Chicharito'] 13 452
ITA 2023 1362 ['Simy'] 13 679
ITA 2023 1927 ['Berat Gjimshiti'] 13 2829
FRA 2021 10387 ['Danylo Ignatenko'] 12 683
ENG 2023 11772 ['Yehor Yarmolyuk'] 11 619
FRA 2023 11399 ['Jeffinho'] 11 293
ITA 2018 1927 ['Berat Gjimshiti'] 11 1804
FRA 2019 3682 ['Jordan Siebatcheu'] 10 429
ITA 2017 1927 ['Berat Gjimshiti'] 9 2700
ENG 2018 6030 ['Zanka'] 8 2151
ENG 2023 6030 ['Zanka'] 8 1082
FRA 2019 3785 ['Kelvin Adou'] 8 1625
FRA 2019 5773 ['Zaydou Youssef'] 8 1063
ESP 2023 10576 ['Álvaro Fernández'] 7 452
ENG 2022 6030 ['Zanka'] 6 1082
ESP 2022 7981 ['Nianzou Kouassi'] 6 1370
ESP 2022 11121 ['Nicolás Fernández Mercau'] 6 451
FRA 2018 5773 ['Zaydou Youssef'] 6 439
FRA 2023 9317 ['Oussama Targhaline'] 6 1053
GER 2021 7981 ['Nianzou Kouassi'] 6 569
GER 2022 9704 ['Vasilios Lampropoulos'] 6 618
ENG 2020 8723 ['Ian Poveda-Ocampo'] 5 322
ESP 2020 8410 ['Rodrigo Sánchez'] 5 527
ESP 2023 7226 ['Chumi'] 5 2427
FRA 2023 11763 ['Abduqodir Khusanov'] 5 819
GER 2021 9704 ['Vasilios Lampropoulos'] 5 1170
GER 2023 9714 ['Odilon Kossounou'] 5 1822
ITA 2019 7941 ['André Anderson'] 5 49
ESP 2019 8461 ['Nicolás Melamed'] 4 178
ESP 2021 5198 ['Martín Aguirregabiria'] 4 1624
ESP 2023 10981 ['Malcom Adu'] 4 238
FRA 2022 9661 ['Igor Silva'] 4 455
FRA 2022 10830 ['Jean Négoce'] 4 254
GER 2021 9714 ['Odilon Kossounou'] 4 1787
ITA 2022 1927 ['Berat Gjimshiti'] 4 1791
ITA 2023 12341 ['Lautaro Giannetti'] 4 630
ENG 2019 191 ['Chicharito'] 3 107
ESP 2017 5198 ['Martín Aguirregabiria'] 3 1828
ESP 2019 5198 ['Martín Aguirregabiria'] 3 2090
ESP 2019 7780 ['Gaizka Larrazabal'] 3 243
ESP 2019 8353 ['Antoñin'] 3 168
ESP 2020 2350 ['Cifuentes'] 3 436
ESP 2020 5124 ['Alberto Rodríguez'] 3 851
ESP 2020 6216 ['Chema Rodríguez'] 3 552
ESP 2022 7226 ['Chumi'] 3 1481
FRA 2017 5773 ['Zaydou Youssef'] 3 125
GER 2021 6595 ['Paul Jäckel'] 3 2044
GER 2021 10363 ['Dong-Jun Lee'] 3 113
GER 2022 9714 ['Odilon Kossounou'] 3 1518
ITA 2022 10938 ['Emanuel Aiwu'] 3 1637
ITA 2023 12380 ['Dani Silva'] 3 415
ENG 2021 6030 ['Zanka'] 2 514
ESP 2018 2574 ['Miguelón'] 2 544
ESP 2018 6120 ['Bono'] 2 2864
ESP 2020 5198 ['Martín Aguirregabiria'] 2 1547
ESP 2020 6120 ['Bono'] 2 2970
ESP 2020 9170 ['John Finn'] 2 54
ESP 2021 7251 ['Robert'] 2 124
ESP 2021 9918 ['Alex Petxarromán'] 2 369
ESP 2022 10981 ['Malcom Adu'] 2 68
ESP 2022 11186 ['Alvaro Rodríguez'] 2 69
ESP 2023 12139 ['Yarek Gasiorowski'] 2 714
FRA 2019 7981 ['Nianzou Kouassi'] 2 454
GER 2017 6595 ['Paul Jäckel'] 2 270
GER 2022 6595 ['Paul Jäckel'] 2 1204
ENG 2021 10092 ['Tariqe Fosu-Henry'] 1 15
ESP 2018 5198 ['Martín Aguirregabiria'] 1 2036
ESP 2020 9457 ['José Boacho'] 1 21
ESP 2021 9268 ['Koffi'] 1 70
ESP 2021 10155 ['Rubén Iranzo'] 1 132
ESP 2022 11266 ['Manu Bueno'] 1 151
ESP 2022 11419 ['Jorge Pascual'] 1 5
ESP 2023 7981 ['Nianzou Kouassi'] 1 309
ESP 2023 11266 ['Manu Bueno'] 1 114
ESP 2023 11503 ['Marciano Sanca'] 1 24
ESP 2023 11834 ['Adrià Alti'] 1 792
ESP 2023 12197 ['Rachad Dhimi'] 1 13
FRA 2023 3785 ['Kelvin Adou'] 1 813
FRA 2023 9661 ['Igor Silva'] 1 251
FRA 2023 12004 ['Joel Mvuka'] 1 189
GER 2018 7436 ['Alfons Amade'] 1 4
GER 2019 6030 ['Zanka'] 1 489
GER 2021 8807 ['Silas Wamangituka'] 1 265
ITA 2018 5195 ['Nicolás Schiappacase'] 1 82
ITA 2021 7941 ['André Anderson'] 1 56
```

</details>

## Re-trim with `h_a` and `home_away`, 2026-11-04

The 5 shot files now keep `h_a` and `home_away`, so they hold 18 columns, not 16. Sections 1, 2, 3 and 5 and the appendix's full output show the earlier run. Where they differ, the numbers here and `MANIFEST.md` are current. The 5 shot files and `MANIFEST.md` changed, and the 13 other output files are byte-identical to the last commit.

Run A wrote to one scratch folder and run B, with `PYTHONHASHSEED=12345`, to another. Both used the sandbox venv with network access denied, and neither used the fresh venv from section 5. Both exited 0. Run A was then copied into `data/standin/`, and all 19 files there equal run B's byte for byte.

```
bundesliga_shot_data.parquet	88214	18	1472562
epl_shot_data.parquet	107838	18	1795242
la_liga_shot_data.parquet	100188	18	1676484
ligue_1_shot_data.parquet	96140	18	1619184
serie_a_shot_data.parquet	110026	18	1834366
```

**#7 checks, re-run.** `t7_verify.py` from the appendix, unchanged, still shares no code with the script and reads the originals with `pyreadr`. Against its earlier output, only the shot files' column and cell counts and the shot column list differ.

```
bundesliga_shot_data: source rows 88214 trimmed rows 88214 columns 18 cells 1587852 differences 0
epl_shot_data: source rows 107838 trimmed rows 107838 columns 18 cells 1941084 differences 0
la_liga_shot_data: source rows 100188 trimmed rows 100188 columns 18 cells 1803384 differences 0
ligue_1_shot_data: source rows 96140 trimmed rows 96140 columns 18 cells 1730520 differences 0
serie_a_shot_data: source rows 110026 trimmed rows 110026 columns 18 cells 1980468 differences 0
plain-file cells compared 10797406 differences 0
```

A separate check found all 18 trimmed files' hashes in `MANIFEST.md`, no file over 100 MB, and the old 16 shot columns equal to the last commit in all 5 shot files.

**The two columns.** Every shot row in all seasons fills exactly one of them, with `h` or `a`. No row fills both or neither.

| File | `h_a` filled | `home_away` filled |
|---|---:|---:|
| `bundesliga_shot_data` | 63,235 | 24,979 |
| `epl_shot_data` | 76,878 | 30,960 |
| `la_liga_shot_data` | 71,450 | 28,738 |
| `ligue_1_shot_data` | 70,416 | 25,724 |
| `serie_a_shot_data` | 80,802 | 29,224 |

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

Re-trim start: `8c93206`, then 2 commits ahead of origin. `6666192` is 5 ahead, `03a9277`, which adds the rule 3 measurements, is 6 ahead, and the `h_a` re-trim commit is 7 ahead, with nothing pushed.

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
bundesliga_shot_data.parquet	88214	16	1464469
epl_shot_data.parquet	107838	16	1785331
la_liga_shot_data.parquet	100188	16	1666821
ligue_1_shot_data.parquet	96140	16	1610098
serie_a_shot_data.parquet	110026	16	1824619
ENG_M_1st_positions.parquet	83613	13	425249
ENG positions rows: before 413736, after URL de-duplication 413736, after 83613, Pos changed by majority 3
ESP_M_1st_positions.parquet	87400	13	460470
ESP positions rows: before 421890, after URL de-duplication 421890, after 87400, Pos changed by majority 0
FRA_M_1st_positions.parquet	79421	13	426753
FRA positions rows: before 395313, after URL de-duplication 395313, after 79421, Pos changed by majority 0
GER_M_1st_positions.parquet	69868	13	359567
GER positions rows: before 348924, after URL de-duplication 348924, after 69868, Pos changed by majority 0
ITA_M_1st_positions.parquet	87300	13	456423
ITA positions rows: before 425429, after URL de-duplication 425045, after 87300, Pos changed by majority 0
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
| Shot files, 5 | `id`, `league`, `season`, `match_id`, `date`, `player`, `player_id` | Identity, league-season, names are not unique | `minute`, `home_goals`, `away_goals`, `player_assisted`. No planned metric uses `minute`, so section 11 reads it from the original. |
| | `home_team`, `away_team` | Rule 2 links shots to FBref matches, and the club map | |
| | `h_a`, `home_away` | Added by the `h_a` re-trim: rule 3 takes the club from the side | |
| | `X`, `Y` | Box shares, Q16 | |
| | `xG` | npxG per shot | |
| | `situation`, `shotType`, `lastAction`, `result` | Metrics, Q15, npg | |
| FBref positions, 5 files per league | `MatchURL`, `Match_Date`, `Season_End_Year`, `Team` | Identity, league-season | Passing, defence and other match stats |
| | `Home_Team`, `Away_Team` | The date link in rule 2 needs the order | |
| | `Matchweek` | Picks out the tie-breaker | |
| | `Player`, `Player_Href` | Name, FBref id | |
| | `Pos`, `Min` | Position rule, 900-minute gate, per-90 | |
| | `Pos_Files_Voted`, `Pos_Tie` | Added by the trim: how many files voted on `Pos`, and whether the top count tied | |
| Match events, 5 | `MatchURL`, `Match_Date`, `Season_End_Year`, `Team`, `Event_Type`, `Event_Players` | `Substitute` rows name who came on (Q5) | `Event_Time` and match summary columns |
| HF `understat_xg_data.csv` | `player_name`, `team`, `league`, `season` | Identity, display | `apps`, `xG`, `xGChain`, `xG90`, `xA90`, `npxG90` |
| | `minutes`, `shots`, `key_passes`, `xA`, `npxG`, `xGBuildup` | Planned fields, T3 section 3 | |
| | `goals`, `assists` | Display only | |
| HF `master_player_stats.csv` | `player`, `player_id`, `league`, `season`, `squad`, `pos`, `min` | No planned field reads it. The criterion names the HF files, T3 counts it, and T3 section 4 measured an id join on it | The other columns |

Names are stored exactly as in the source, with no entity decoding: 2308 shot rows still hold `&#039;`. The literal text `None` in `lastAction` stays text, on 59088 rows, the count T3 gives.

```
### schema of Season_End_Year in event files {'ENG': 'int64', 'ESP': 'int32', 'FRA': 'int32', 'GER': 'int32', 'ITA': 'int32'}
schema of positions ['MatchURL:large_string', 'Match_Date:large_string', 'Matchweek:large_string', 'Season_End_Year:int32', 'Home_Team:large_string', 'Away_Team:large_string', 'Team:large_string', 'Player:large_string', 'Player_Href:large_string', 'Pos:large_string', 'Min:int64', 'Pos_Files_Voted:int64', 'Pos_Tie:bool']
schema of shots ['id:double', 'league:large_string', 'season:double', 'match_id:double', 'date:large_string', 'player:large_string', 'player_id:double', 'home_team:large_string', 'away_team:large_string', 'X:double', 'Y:double', 'xG:double', 'situation:large_string', 'shotType:large_string', 'lastAction:large_string', 'result:large_string']
FBref files holding a player_id column: 0 of 25
lastAction text None in trimmed shots: 59088
names holding &#039; in trimmed shots: 2308
```

## 3. Hashes, and values against the originals

> The hash of each original file is recorded

**Met.** `MANIFEST.md` has one row per source asset: source asset, original SHA-256, trimmed file, trimmed SHA-256, source rows, rows kept, source columns, rdata version.

```
MANIFEST vs shasum: files checked 56 name and hash on one line 56 missing 0
files over 100 MB: 0
trimmed files 17 mismatches 0 | source rows in manifest 38
schemas differ within group: {'*_shot_data.parquet': 1, '*_positions.parquet': 1, '*_match_summary.parquet': 2}
```

The 56 files are the 17 trimmed files, `club_map.csv` and the 38 originals.

**Values.** An outside check shares no code with the script. It reads originals with `pyreadr` and the `csv` module, and trimmed files with `pyarrow`, and compares every kept cell. For positions, it applies the file rule itself, checks each match against that file with `Pos` aside, then recounts `Pos`, `Pos_Files_Voted` and `Pos_Tie` by id.

```
### A. plain files: same rows, same order, every kept cell
bundesliga_shot_data: source rows 88214 trimmed rows 88214 columns 16 cells 1411424 differences 0 
epl_shot_data: source rows 107838 trimmed rows 107838 columns 16 cells 1725408 differences 0 
la_liga_shot_data: source rows 100188 trimmed rows 100188 columns 16 cells 1603008 differences 0 
ligue_1_shot_data: source rows 96140 trimmed rows 96140 columns 16 cells 1538240 differences 0 
serie_a_shot_data: source rows 110026 trimmed rows 110026 columns 16 cells 1760416 differences 0 
ENG_M_1st_match_summary: source rows 37734 trimmed rows 37734 columns 6 cells 226404 differences 0 
ESP_M_1st_match_summary: source rows 44873 trimmed rows 44873 columns 6 cells 269238 differences 0 
FRA_M_1st_match_summary: source rows 37503 trimmed rows 37503 columns 6 cells 225018 differences 0 
GER_M_1st_match_summary: source rows 34742 trimmed rows 34742 columns 6 cells 208452 differences 0 
ITA_M_1st_match_summary: source rows 43180 trimmed rows 43180 columns 6 cells 259080 differences 0 
understat_xg_data: source rows 27182 trimmed rows 27182 columns 12 cells 326184 differences 0 
master_player_stats: source rows 34246 trimmed rows 34246 columns 7 cells 239722 differences 0 

### B. positions: Pos aside, every match equals the source file the rule picks; Pos, votes and ties recomputed by id; none lost
ENG: rows before 413736 after 83613 | matches 2939 source ids 2939 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['str'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ESP: rows before 421890 after 87400 | matches 2921 source ids 2921 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['str'], 'possession': ['str'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
FRA: rows before 395313 after 79421 | matches 2701 source ids 2701 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['str'], 'misc': ['str']}
GER: rows before 348924 after 69868 | matches 2348 source ids 2348 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ITA: rows before 425429 after 87300 | matches 2917 source ids 2917 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['str'], 'passing': ['str'], 'defense': ['str'], 'misc': ['float']}
totals {'before': 2005292, 'after': 407602, 'lost': 0, 'wrong_pick': 0, 'wrong_pos': 0, 'wrong_votes': 0, 'wrong_tie': 0, 'repeated': 0, 'lost_vote_files': 0}
rows by files voted {1: 659, 2: 349, 3: 80, 4: 29519, 5: 376995}
rows whose Pos changed from the picked file 3
  ('ENG', 2025, 'Yves Bissouma', 'CM', 'DM,CM', {'CM': 2, 'DM,CM': 3}, '')
  ('ENG', 2025, 'James Maddison', 'LM', 'AM,LM', {'LM': 2, 'AM,LM': 3}, 'attacking changes')
  ('ENG', 2025, 'Pape Matar Sarr', 'RM', 'DM', {'RM': 2, 'DM': 3}, '')
rows with a tie 1
  ('ITA', 2023, 'Gabriel Strefezza', 'FW', {'FW': 1, 'RW,LW': 1})
```

It can fail. Run on a copy of the final files with planted faults in 6 of them (a 1e-9 change to one `xG`, a changed `Event_Type`, a dropped HF row, a changed `Pos`, a removed match, a flipped `Pos_Tie` with a changed `Pos_Files_Voted`), it reports each one, and the manifest check fails on those 6 files:

```
$ t7_verify.py mutant originals T3_step0_facts.md | grep -E 'differences [1-9]|lost [1-9]|wrong [1-9]|plain-file|mismatches'
epl_shot_data: source rows 107838 trimmed rows 107838 columns 16 cells 1725408 differences 1 [('xG', 5, 0.03097105498774147, 0.03097105398774147)]
ESP_M_1st_match_summary: source rows 44873 trimmed rows 44873 columns 6 cells 269238 differences 1 [('Event_Type', 3, 'Goalx', 'Substitute')]
understat_xg_data: source rows 27182 trimmed rows 27181 columns 12 cells 326172 differences 1 
ENG: rows before 413736 after 83613 | matches 2939 source ids 2939 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 1 tie wrong 1 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['str'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
FRA: rows before 395313 after 79393 | matches 2700 source ids 2701 lost 1 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['str'], 'misc': ['str']}
GER: rows before 348924 after 69868 | matches 2348 source ids 2348 lost 0 | not equal to the picked file 0 | Pos wrong 1 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
plain-file cells compared 9792582 differences 3
trimmed files 17 mismatches 6 | source rows in manifest 38
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
4. **`Pos` is the majority** across the files holding the match, with players matched by the 8-character id. On a tie, the chosen file's value stays. An empty `Pos` is no vote, and `Pos` is compared as stored, so `FW,AM` and `AM,FW` count as different values. Each row records `Pos_Files_Voted` and `Pos_Tie`. The result is in section 3: 3 rows change and 1 row ties.

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
$ sandbox-exec -f noNet.sb parquet-vet/venv/bin/python3 -B scripts/trim_standin.py originals run5
exit 0
exit 0
run A (fresh venv) vs run B (second venv), all files: same 19 different 0
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

**Met.** Both runs and the outside check ran under a profile denying network access. The script imports only `sys`, `platform`, `collections`, `pathlib`, `pandas`, `pyarrow`, `rdata` and `cut_fixtures`. `gh` and `git fetch` were used only in Step 0, to read the issue and the release notes.

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
- **ITA 2022/23, 1 real match, kept.** A different id and date, and its `Matchweek` names a tie-breaker. It stays in the file so the count still equals T3, and #6 leaves it out by filtering on `Matchweek` (rule 1).
- **ITA 2023/24 gap.** Fiorentina and Atalanta have 37 matches and all others 38. #6 drops its 20 shot rows (rule 2).

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
club map rows not exact and mapped 43
Pool matches not linked on the exact date 19 | rows 457
```

## 9. Club map

`data/standin/club_map.csv` is built from the trimmed files: same date, same pair of clubs. Same names map first. Each other club then takes the FBref club most often found opposite an already mapped opponent on the same date, and a tied or absent count leaves it unmapped. Columns: `league`, `understat_club`, `fbref_club`, `exact_name`, `linked_matches`. `linked_matches` covers all seasons and needs the exact date, so it can be lower than the true count.

**Reviewed and approved by Ahmed, 2026-11-04.** Evidence from the independent audit of `6666192`: 0 wrong mappings among the 43 that are not exact name matches, 0 FBref clubs reached by 2 Understat names in the same season, and 0 unmapped clubs with a Pool-season match. The last two, and the counts of 43 and 14, also hold when re-checked on the current `club_map.csv` and shot files:

```
non-exact mapped 43 | unmapped understat 14
unmapped clubs with a Pool-season match 0
FBref clubs reached by 2 names in one season, all seasons 0 | Pool seasons 0
```

The lists below stay for the record: every unmapped club and every mapping that is not an exact name match. No FBref club is unmapped.

## 10. Rule 2 links

The decided link, from the plan: same home club and same away club, in that order, in the same season, nearest FBref date, at most 14 days. The tie-breaker is left out first, because rule 1 excludes it and otherwise Spezia v Hellas Verona appears twice.

```
### H. club map and rule 2 links, Pool seasons
rows 168 | exact 111
unmapped: [('ENG', 'Hull', 'understat only'), ('ENG', 'Middlesbrough', 'understat only'), ('ENG', 'Queens Park Rangers', 'understat only'), ('ESP', 'Cordoba', 'understat only'), ('ESP', 'Sporting Gijon', 'understat only'), ('FRA', 'Evian Thonon Gaillard', 'understat only'), ('FRA', 'GFC Ajaccio', 'understat only'), ('FRA', 'Nancy', 'understat only'), ('FRA', 'SC Bastia', 'understat only'), ('GER', 'Ingolstadt', 'understat only'), ('ITA', 'Carpi', 'understat only'), ('ITA', 'Cesena', 'understat only'), ('ITA', 'Palermo', 'understat only'), ('ITA', 'Pescara', 'understat only')]
not exact:
  ENG | Brighton | Brighton & Hove Albion | 293
  ENG | Cardiff | Cardiff City | 38
  ENG | Huddersfield | Huddersfield Town | 76
  ENG | Ipswich | Ipswich Town | 24
  ENG | Leeds | Leeds United | 118
  ENG | Leicester | Leicester City | 252
  ENG | Luton | Luton Town | 38
  ENG | Norwich | Norwich City | 76
  ENG | Stoke | Stoke City | 38
  ENG | Swansea | Swansea City | 38
  ENG | Tottenham | Tottenham Hotspur | 294
  ENG | West Ham | West Ham United | 294
  ESP | Alaves | Alavés | 254
  ESP | Almeria | Almería | 76
  ESP | Atletico Madrid | Atlético Madrid | 291
  ESP | Cadiz | Cádiz | 152
  ESP | Deportivo La Coruna | Deportivo La Coruña | 38
  ESP | Leganes | Leganés | 135
  ESP | Malaga | Málaga | 38
  ESP | Real Oviedo | Oviedo | 4
  ESP | Real Valladolid | Valladolid | 174
  ESP | SD Huesca | Huesca | 76
  FRA | Nimes | Nîmes | 104
  FRA | Paris Saint Germain | Paris Saint-Germain | 275
  FRA | Saint-Etienne | Saint-Étienne | 200
  GER | Arminia Bielefeld | Arminia | 68
  GER | Borussia Dortmund | Dortmund | 261
  GER | Borussia M.Gladbach | Mönchengladbach | 260
  GER | Darmstadt | Darmstadt 98 | 34
  GER | FC Cologne | Köln | 207
  GER | FC Heidenheim | Heidenheim | 57
  GER | Fortuna Duesseldorf | Düsseldorf | 68
  GER | Greuther Fuerth | Greuther Fürth | 34
  GER | Hertha Berlin | Hertha BSC | 204
  GER | Nuernberg | Nürnberg | 34
  GER | Paderborn | Paderborn 07 | 34
  GER | RasenBallsport Leipzig | RB Leipzig | 261
  GER | VfB Stuttgart | Stuttgart | 227
  ITA | AC Milan | Milan | 291
  ITA | Inter | Internazionale | 291
  ITA | Parma Calcio 1913 | Parma | 140
  ITA | SPAL 2013 | SPAL | 114
  ITA | Verona | Hellas Verona | 253
exact but 0 linked: [('ITA', 'Parma')]
FBref clubs reached by 2+ Understat names: {('ITA', 'Parma'): 2}
mapped on under 10 linked matches: [('ESP', 'Real Oviedo', 'Oviedo', '4')]
Link: same home club and same away club in the same season, nearest FBref date, at most 14 days. Tie-breaker left out.
home or away null 0 | matches whose Home_Team and Away_Team differ from Team 0
ordered pairs twice in one season, FBref: [] | Understat: []
Pool matches 12607 | linked 12604 | no link 3 | gap days to matches {0: 12588, 1: 13, 2: 1, 11: 2}
links with a gap above 0: gap, league, Understat date, clubs, FBref date, shot rows
  (11, 'FRA', '2018-04-14', 'Caen', 'Toulouse', '2018-04-25', 14)
  (11, 'ITA', '2024-04-14', 'Udinese', 'Roma', '2024-04-25', 28)
  (2, 'FRA', '2023-04-30', 'Strasbourg', 'Lyon', '2023-04-28', 18)
  (1, 'ENG', '2018-08-25', 'Fulham', 'Burnley', '2018-08-26', 37)
  (1, 'ESP', '2017-09-16', 'Eibar', 'Leganes', '2017-09-15', 15)
  (1, 'ESP', '2017-10-23', 'Celta Vigo', 'Atletico Madrid', '2017-10-22', 23)
  (1, 'ESP', '2017-11-05', 'Barcelona', 'Sevilla', '2017-11-04', 26)
  (1, 'ESP', '2022-05-15', 'Espanyol', 'Valencia', '2022-05-14', 23)
  (1, 'ESP', '2023-12-12', 'Granada', 'Athletic Club', '2023-12-11', 27)
  (1, 'FRA', '2018-05-12', 'Guingamp', 'Marseille', '2018-05-11', 38)
  (1, 'FRA', '2022-02-02', 'Lyon', 'Marseille', '2022-02-01', 21)
  (1, 'FRA', '2023-08-12', 'Nice', 'Lille', '2023-08-11', 20)
  (1, 'FRA', '2023-08-12', 'Brest', 'Lens', '2023-08-13', 25)
  (1, 'ITA', '2018-01-28', 'Sassuolo', 'Atalanta', '2018-01-27', 27)
  (1, 'ITA', '2018-01-28', 'Chievo', 'Juventus', '2018-01-27', 17)
  (1, 'ITA', '2024-05-24', 'Cagliari', 'Fiorentina', '2024-05-23', 25)
no link, rows dropped: league, season end year, date, clubs, rows, nearest same-order date
  ('GER', 2022, '2022-03-18', 'Bochum', 'Borussia M.Gladbach', 24, [])
  ('ITA', 2021, '2020-09-19', 'Verona', 'Roma', 29, [])
  ('ITA', 2024, '2024-06-02', 'Atalanta', 'Fiorentina', 20, [])
rows dropped 73
```

The 3 matches with no link are the 2 gaps T3 reported and the ITA 2023/24 gap in section 6.

**The 16-match table, rebuilt from `data/standin/` only.** The first version of this table took home and away from a cache of the originals. This rebuild reads only `data/standin/`, and compares the result with that table, typed into the script:

```
$ table16.py data/standin
('FRA', '2018-04-14', 'Caen', 'Toulouse', '2018-04-25', 11, 14)
  ('ITA', '2024-04-14', 'Udinese', 'Roma', '2024-04-25', 11, 28)
  ('FRA', '2023-04-30', 'Strasbourg', 'Lyon', '2023-04-28', 2, 18)
  ('ENG', '2018-08-25', 'Fulham', 'Burnley', '2018-08-26', 1, 37)
  ('ESP', '2017-09-16', 'Eibar', 'Leganes', '2017-09-15', 1, 15)
  ('ESP', '2017-10-23', 'Celta Vigo', 'Atletico Madrid', '2017-10-22', 1, 23)
  ('ESP', '2017-11-05', 'Barcelona', 'Sevilla', '2017-11-04', 1, 26)
  ('ESP', '2022-05-15', 'Espanyol', 'Valencia', '2022-05-14', 1, 23)
  ('ESP', '2023-12-12', 'Granada', 'Athletic Club', '2023-12-11', 1, 27)
  ('FRA', '2018-05-12', 'Guingamp', 'Marseille', '2018-05-11', 1, 38)
  ('FRA', '2022-02-02', 'Lyon', 'Marseille', '2022-02-01', 1, 21)
  ('FRA', '2023-08-12', 'Nice', 'Lille', '2023-08-11', 1, 20)
  ('FRA', '2023-08-12', 'Brest', 'Lens', '2023-08-13', 1, 25)
  ('ITA', '2018-01-28', 'Sassuolo', 'Atalanta', '2018-01-27', 1, 27)
  ('ITA', '2018-01-28', 'Chievo', 'Juventus', '2018-01-27', 1, 17)
  ('ITA', '2024-05-24', 'Cagliari', 'Fiorentina', '2024-05-23', 1, 25)
rebuilt rows 16 | shown rows 16 | in both 16 | only rebuilt [] | only shown []
matches 12607 linked 12604 no link [('GER', '2022-03-18', 'Bochum', 'Borussia M.Gladbach', 24), ('ITA', '2020-09-19', 'Verona', 'Roma', 29), ('ITA', '2024-06-02', 'Atalanta', 'Fiorentina', 20)]
table matches what was shown: True
```

**The two 11-day gaps are verified real re-dates.** Ahmed verified both, and that check is recorded here. It was not repeated from the data files, which only show the dates.

| Match | Understat date | FBref date | What happened |
|---|---|---|---|
| Caen v Toulouse, 2017/18 | 2018-04-14 | 2018-04-25 | Postponed for weather, 14 to 25 Apr 2018 |
| Udinese v Roma, 2023/24 | 2024-04-14 | 2024-04-25 | Suspended at 72' and finished on 25 Apr 2024 |

## 11. Udinese v Roma 2023/24: shot minutes

`minute` is not in `data/standin/`, so this reads the original `serie_a_shot_data.rds`, with both `pyreadr` and `rdata`.

```
pyreadr: rows 28 | match_id [22621.0] | dates ['2024-04-14 16:00:00']
minutes sorted [8, 14, 15, 16, 20, 22, 25, 31, 38, 48, 50, 55, 58, 60, 62, 62, 63, 67, 67, 78, 78, 80, 82, 82, 84, 91, 94, 94]
minute range 8 94 | rows after minute 72 9 | at 72 0 | at or before 72 19
after 72 by side h_a/home_away Counter({('', 'a'): 6, ('', 'h'): 3})
       minute              player       result   situation home_team away_team
98532    78.0  Lorenzo Pellegrini  BlockedShot    OpenPlay   Udinese      Roma
98533    78.0  Lorenzo Pellegrini  MissedShots    OpenPlay   Udinese      Roma
98516    80.0       Lorenzo Lucca    SavedShot    SetPiece   Udinese      Roma
98517    82.0     Roberto Pereyra  BlockedShot    OpenPlay   Udinese      Roma
98518    82.0     Roberto Pereyra  BlockedShot  FromCorner   Udinese      Roma
98534    84.0       Sardar Azmoun    SavedShot    OpenPlay   Udinese      Roma
98535    91.0        Paulo Dybala  BlockedShot    OpenPlay   Udinese      Roma
98536    94.0  Lorenzo Pellegrini  BlockedShot  FromCorner   Udinese      Roma
98537    94.0     Bryan Cristante         Goal  FromCorner   Udinese      Roma
goals in rows        minute           player
98513    22.0  Roberto Pereyra
98529    63.0    Romelu Lukaku
98537    94.0  Bryan Cristante
other rows same season same clubs, any order [('Roma', '2023-11-26 17:00:00'), ('Udinese', '2024-04-14 16:00:00')]
rdata: rows 28 minute range 8 94 rows after 72 9
```

The 28 shot rows run from minute 8 to minute 94. **9 rows are after minute 72**, including Bryan Cristante's goal at 94, and none is at 72. All 28 rows share one `match_id` and the date 2024-04-14. So Understat holds the whole match, including the part played on 25 Apr, under the first date. Nothing needs to be dropped for it.

## Code review

`/code-review` on `scripts/trim_standin.py`, high effort, once on each version of the script.

Home and away columns, 1 finding: the shot files leave out `minute`, so section 11 has to read the original. Left, because no planned metric uses it.

Re-trim, 7 findings:

| Finding | Outcome |
|---|---|
| Exact-date linking misses re-dated matches | Left. Same date was asked for the map. Flagged for #6 in the first finding. |
| A club can map on one vote | Left. The lists are for review, and the only weak mapping is `Real Oviedo` (4). |
| URL filter can remove a file's vote | No change needed. Measured 0. |
| A repeated id in a file votes arbitrarily | No change needed. Measured 0. |
| Plan wording on majority `Pos` is stale | Left. Out of scope, and noted in the findings. |
| Vote loop scans all FBref pairs per match | Left. It costs seconds. |
| Module docstring wrapped badly | Fixed |

First trim, 8 findings:

| Finding | Outcome |
|---|---|
| File choice ignored missing `Min` (Mounié, above) | Fixed |
| Manifest listed any stale `*.parquet` in the folder | Fixed |
| Manifest hard-coded the Python version | Fixed |
| Manifest loaded whole tables for row counts | Fixed |
| A failure mid-run leaves a mixed folder | Left. Re-running fixes it, and the hashes expose it. |
| Duplicate guard compares the whole href, not the id | Left at the time. The re-trim now checks the id. |
| Sibling import fails under `python -I` | Left. It fails at once, with no bad data. |
| `SHA256` repeats 10 hashes from `cut_fixtures` | Left. The originals are fixed. |

- Only allowed libraries: **YES**. `pandas`, `numpy`, `pyarrow`, `rdata`.
- No columns dropped that the plan needs: **YES**. Section 2, including the team columns rule 2 needs.

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
print("\n### B. positions: Pos aside, every match equals the source file the rule picks; Pos, votes and ties recomputed by id; none lost")
KEPT = ["Match_Date", "Matchweek", "Season_End_Year", "Home_Team", "Away_Team", "Team", "Player", "Player_Href", "Min"]
KINDS = ["passing_types", "possession", "passing", "defense", "misc"]
mid = lambda u: re.search(r"/matches/([0-9a-f]{8})/", u).group(1)
pid = lambda h: re.search(r"/players/([0-9a-f]{8})/", h).group(1)
def norm(row):
    m = row["Min"]
    return (row["Match_Date"], row["Matchweek"], int(row["Season_End_Year"]), row["Home_Team"], row["Away_Team"], row["Team"], row["Player"], row["Player_Href"], None if null(m) else int(float(m)))
agree = {c: Counter() for c in ("Pos", "Min", "Player")}; off = {c: Counter() for c in agree}; flips = pool_flips = 0
ATT = {"FW", "LW", "RW", "AM"}; attacking = lambda p: bool(set(p.split(",")) & ATT)
all_kept = {}; totals = Counter(); votes_dist = Counter(); changed_rows = []; tie_rows = []
for lg in ("ENG", "ESP", "FRA", "GER", "ITA"):
    t = pq.read_table(data / f"{lg}_M_1st_positions.parquet")
    out = defaultdict(list)
    for r in t.to_pylist(): out[r["MatchURL"]].append(r)
    src = {}; before = 0; keys = defaultdict(dict); min_types = {}; repeated = 0
    for k in KINDS:
        n, c = read_source(f"{lg}_M_1st_{k}_player_advanced_match_stats.rds", ["MatchURL", "Pos"] + KEPT)
        min_types[k] = sorted({type(v).__name__ for v in c["Min"] if not null(v)})
        before += n
        rows = defaultdict(list)
        for i in range(n):
            row = {x: c[x][i] for x in KEPT}; row["Pos"] = c["Pos"][i]; row["MatchURL"] = c["MatchURL"][i]
            rows[c["MatchURL"][i]].append(row)
            keys[(mid(c["MatchURL"][i]), row["Player_Href"])][k] = (row["Pos"], None if null(row["Min"]) else int(float(row["Min"])), row["Player"], int(row["Season_End_Year"]))
        src[k] = rows
    src_ids = {mid(u) for k in KINDS for u in src[k]}; out_ids = {mid(u) for u in out}
    assert len(out_ids) == len(out), "one id, two URLs in output"
    wrong_pick = wrong_pos = wrong_votes = wrong_tie = lost_vote_files = 0
    for u, rs in out.items():
        m = mid(u)
        # only the kept spelling counts; note any file holding this id only under another spelling
        holders = [k for k in KINDS if u in src[k]]
        lost_vote_files += sum(1 for k in KINDS if k not in holders and any(mid(x) == m for x in src[k]))
        size = {k: len(src[k][u]) for k in holders}; mins = {k: sum(not null(x["Min"]) for x in src[k][u]) for k in holders}
        pick = min(holders, key=lambda k: (-size[k], -mins[k], KINDS.index(k)))
        have = sorted((norm(r) for r in rs), key=repr)
        if sorted((norm(r) for r in src[pick][u]), key=repr) != have: wrong_pick += 1
        chosen_pos = {pid(x["Player_Href"]): x["Pos"] for x in src[pick][u]}
        per_file = {k: defaultdict(list) for k in holders}
        for k in holders:
            for x in src[k][u]: per_file[k][pid(x["Player_Href"])].append(x["Pos"])
        for r in rs:
            p = pid(r["Player_Href"]); ballots = []
            for k in holders:
                vals = per_file[k].get(p, [])
                if len(vals) > 1: repeated += 1
                if vals and vals[0] != "": ballots.append(vals[0])
            cnt = Counter(ballots); top = max(cnt.values()) if cnt else 0; winners = [v for v, n in cnt.items() if n == top]
            want = winners[0] if len(winners) == 1 else chosen_pos[p]
            wrong_pos += r["Pos"] != want; wrong_votes += r["Pos_Files_Voted"] != len(ballots); wrong_tie += r["Pos_Tie"] != (len(winners) > 1)
            votes_dist[len(ballots)] += 1
            pool = 2018 <= r["Season_End_Year"] <= 2024
            if r["Pos"] != chosen_pos[p]: changed_rows.append((lg, r["Season_End_Year"], r["Player"], chosen_pos[p], r["Pos"], dict(cnt), "attacking changes" if attacking(chosen_pos[p]) != attacking(r["Pos"]) else ""))
            if r["Pos_Tie"]: tie_rows.append((lg, r["Season_End_Year"], r["Player"], r["Pos"], dict(cnt)))
    totals.update(before=before, after=t.num_rows, lost=len(src_ids - out_ids), wrong_pick=wrong_pick, wrong_pos=wrong_pos, wrong_votes=wrong_votes, wrong_tie=wrong_tie, repeated=repeated, lost_vote_files=lost_vote_files)
    print(f"{lg}: rows before {before} after {t.num_rows} | matches {len(out)} source ids {len(src_ids)} lost {len(src_ids - out_ids)} | not equal to the picked file {wrong_pick} | Pos wrong {wrong_pos} votes wrong {wrong_votes} tie wrong {wrong_tie} | id repeated in a file {repeated} | files holding a match only under a dropped spelling {lost_vote_files} | Min types {min_types}")
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
print("totals", dict(totals))
print("rows by files voted", dict(sorted(votes_dist.items())))
print("rows whose Pos changed from the picked file", len(changed_rows)); [print(" ", x) for x in changed_rows]
print("rows with a tie", len(tie_rows)); [print(" ", x) for x in tie_rows]
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
print("\n### H. club map and rule 2 links, Pool seasons")
cm = list(csv.DictReader(open(data / "club_map.csv", encoding="utf8", newline="")))
print("rows", len(cm), "| exact", sum(r["exact_name"] == "True" for r in cm))
print("unmapped:", [(r["league"], r["understat_club"] or r["fbref_club"], "understat only" if r["understat_club"] else "fbref only") for r in cm if not (r["understat_club"] and r["fbref_club"])])
print("not exact:"); [print(f"  {r['league']} | {r['understat_club']} | {r['fbref_club']} | {r['linked_matches']}") for r in cm if r["understat_club"] and r["fbref_club"] and r["exact_name"] != "True"]
print("exact but 0 linked:", [(r["league"], r["understat_club"]) for r in cm if r["exact_name"] == "True" and r["linked_matches"] == "0"])
many = Counter((r["league"], r["fbref_club"]) for r in cm if r["understat_club"] and r["fbref_club"]); print("FBref clubs reached by 2+ Understat names:", {k: v for k, v in many.items() if v > 1})
print("mapped on under 10 linked matches:", [(r["league"], r["understat_club"], r["fbref_club"], r["linked_matches"]) for r in cm if r["understat_club"] and r["fbref_club"] and int(r["linked_matches"]) < 10 and r["exact_name"] != "True"])
from datetime import date as Date
files = {"ENG": "epl", "ESP": "la_liga", "FRA": "ligue_1", "GER": "bundesliga", "ITA": "serie_a"}
gaps = Counter(); over = []; zero_rows = Counter(); dropped = []; dup_f = []; dup_u = []; names_differ = null_ha = totals_m = 0
for lg, f in files.items():
    mp = {r["understat_club"]: r["fbref_club"] for r in cm if r["league"] == lg and r["understat_club"] and r["fbref_club"]}
    by = defaultdict(list); teams = defaultdict(set); first = {}
    for r in all_kept[lg].to_pylist():
        teams[r["MatchURL"]].add(r["Team"]); first.setdefault(r["MatchURL"], r)
    for u, r in first.items():
        null_ha += r["Home_Team"] is None or r["Away_Team"] is None
        names_differ += {r["Home_Team"], r["Away_Team"]} != teams[u]
        if 2018 <= r["Season_End_Year"] <= 2024 and "tie-breaker" not in r["Matchweek"]:
            by[(r["Season_End_Year"], r["Home_Team"], r["Away_Team"])].append(r["Match_Date"])
    dup_f += [(lg, k, v) for k, v in by.items() if len(v) > 1]
    shots = Counter(); info = {}
    for r in pq.read_table(data / f"{f}_shot_data.parquet", columns=["season", "date", "match_id", "home_team", "away_team"]).to_pylist():
        if 2017 <= r["season"] <= 2023: shots[r["match_id"]] += 1; info[r["match_id"]] = r
    seen = Counter()
    for m, r in info.items():
        y = int(r["season"]) + 1; key = (y, mp.get(r["home_team"]), mp.get(r["away_team"])); seen[key] += 1; totals_m += 1
        day = r["date"][:10]
        c = sorted((abs((Date.fromisoformat(d) - Date.fromisoformat(day)).days), d) for d in by.get(key, []))
        if not c or c[0][0] > 14:
            dropped.append((lg, y, day, r["home_team"], r["away_team"], shots[m], c[:1])); continue
        gaps[c[0][0]] += 1
        if c[0][0] > 0: over.append((c[0][0], lg, day, r["home_team"], r["away_team"], c[0][1], shots[m]))
    dup_u += [(lg, k, v) for k, v in seen.items() if v > 1]
print("Link: same home club and same away club in the same season, nearest FBref date, at most 14 days. Tie-breaker left out.")
print(f"home or away null {null_ha} | matches whose Home_Team and Away_Team differ from Team {names_differ}")
print("ordered pairs twice in one season, FBref:", dup_f, "| Understat:", dup_u)
print(f"Pool matches {totals_m} | linked {sum(gaps.values())} | no link {len(dropped)} | gap days to matches {dict(sorted(gaps.items()))}")
print("links with a gap above 0: gap, league, Understat date, clubs, FBref date, shot rows"); [print(" ", x) for x in sorted(over, key=lambda x: (-x[0], x[1], x[2]))]
print("no link, rows dropped: league, season end year, date, clubs, rows, nearest same-order date"); [print(" ", x) for x in dropped]
print("rows dropped", sum(x[5] for x in dropped))

print(f"\nplain-file cells compared {total_cells} differences {total_diffs}")
print("\n### G. MANIFEST rows and columns against the files")
m = (data / "MANIFEST.md").read_text(); mis = 0
for p in sorted(data.glob("*.parquet")):
    md = pq.read_metadata(p)
    ok = re.search(rf"^\| `{re.escape(p.name)}` \| {md.num_rows} \| {md.num_columns} \| {p.stat().st_size} \|", m, re.M) is not None
    mis += not ok
print("trimmed files", len(list(data.glob('*.parquet'))), "mismatches", mis, "| source rows in manifest", len(re.findall(r"^\| `[^`]+\.(?:rds|csv)` \|", m, re.M)))
print("schemas differ within group:", {g: len({str(pq.read_schema(p).remove_metadata()) for p in data.glob(g)}) for g in ("*_shot_data.parquet", "*_positions.parquet", "*_match_summary.parquet")})
print("positions columns", pq.read_schema(data / "ENG_M_1st_positions.parquet").names, "| shot columns", pq.read_schema(data / "epl_shot_data.parquet").names)
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

<details><summary><code>table16.py</code></summary>

```python
"""Rebuild the 16-match link table from data/standin/ only, and compare it with the table shown to Ahmed, typed in below."""
import csv, sys
from collections import Counter, defaultdict
from datetime import date as Date
from pathlib import Path
import pyarrow.parquet as pq
data=Path(sys.argv[1])
SHOWN=[("FRA","2018-04-14","Caen","Toulouse","2018-04-25",11,14),("ITA","2024-04-14","Udinese","Roma","2024-04-25",11,28),("FRA","2023-04-30","Strasbourg","Lyon","2023-04-28",2,18),("ENG","2018-08-25","Fulham","Burnley","2018-08-26",1,37),("ESP","2017-09-16","Eibar","Leganes","2017-09-15",1,15),("ESP","2017-10-23","Celta Vigo","Atletico Madrid","2017-10-22",1,23),("ESP","2017-11-05","Barcelona","Sevilla","2017-11-04",1,26),("ESP","2022-05-15","Espanyol","Valencia","2022-05-14",1,23),("ESP","2023-12-12","Granada","Athletic Club","2023-12-11",1,27),("FRA","2018-05-12","Guingamp","Marseille","2018-05-11",1,38),("FRA","2022-02-02","Lyon","Marseille","2022-02-01",1,21),("FRA","2023-08-12","Nice","Lille","2023-08-11",1,20),("FRA","2023-08-12","Brest","Lens","2023-08-13",1,25),("ITA","2018-01-28","Sassuolo","Atalanta","2018-01-27",1,27),("ITA","2018-01-28","Chievo","Juventus","2018-01-27",1,17),("ITA","2024-05-24","Cagliari","Fiorentina","2024-05-23",1,25)]
cm=list(csv.DictReader(open(data/'club_map.csv',encoding='utf8',newline='')))
files={'ENG':'epl','ESP':'la_liga','FRA':'ligue_1','GER':'bundesliga','ITA':'serie_a'}
built=[]; total=linked=0; no=[]
for lg,f in files.items():
    mp={r['understat_club']:r['fbref_club'] for r in cm if r['league']==lg and r['understat_club'] and r['fbref_club']}
    by=defaultdict(set)
    for r in pq.read_table(data/f'{lg}_M_1st_positions.parquet',columns=['Match_Date','Matchweek','Season_End_Year','Home_Team','Away_Team']).to_pylist():
        if 2018<=r['Season_End_Year']<=2024 and 'tie-breaker' not in r['Matchweek']: by[(r['Season_End_Year'],r['Home_Team'],r['Away_Team'])].add(r['Match_Date'])
    rows=Counter(); info={}
    for r in pq.read_table(data/f'{f}_shot_data.parquet',columns=['season','date','match_id','home_team','away_team']).to_pylist():
        if 2017<=r['season']<=2023: rows[r['match_id']]+=1; info[r['match_id']]=r
    for m,r in info.items():
        total+=1; day=r['date'][:10]
        c=sorted((abs((Date.fromisoformat(d)-Date.fromisoformat(day)).days),d) for d in by.get((int(r['season'])+1,mp.get(r['home_team']),mp.get(r['away_team'])),[]))
        if not c or c[0][0]>14: no.append((lg,day,r['home_team'],r['away_team'],rows[m])); continue
        linked+=1
        if c[0][0]>0: built.append((lg,day,r['home_team'],r['away_team'],c[0][1],c[0][0],rows[m]))
built.sort(key=lambda x:(-x[5],x[0],x[1]))
for x in built: print(' ',x)
print('rebuilt rows',len(built),'| shown rows',len(SHOWN),'| in both',len(set(built)&set(SHOWN)),'| only rebuilt',sorted(set(built)-set(SHOWN)),'| only shown',sorted(set(SHOWN)-set(built)))
print('matches',total,'linked',linked,'no link',no)
print('table matches what was shown:',set(built)==set(SHOWN))
```

</details>

<details><summary><code>udinese.py</code></summary>

```python
"""Udinese v Roma 2023/24: minute of each shot. minute is not in data/standin, so this reads the original with two readers."""
import sys
from pathlib import Path
from collections import Counter
import pyreadr, warnings, rdata
warnings.simplefilter('ignore')
p=Path(sys.argv[1])/'serie_a_shot_data.rds'
d=pyreadr.read_r(str(p))[None]
u=d[(d.season==2023)&(d.home_team=='Udinese')&(d.away_team=='Roma')]
print('pyreadr: rows',len(u),'| match_id',sorted(set(u.match_id)),'| dates',sorted(set(u.date)))
print('minutes sorted',sorted(int(x) for x in u.minute))
print('minute range',int(u.minute.min()),int(u.minute.max()),'| rows after minute 72',int((u.minute>72).sum()),'| at 72',int((u.minute==72).sum()),'| at or before 72',int((u.minute<=72).sum()))
print('after 72 by side h_a/home_away',Counter(zip(u[u.minute>72].h_a.fillna('').tolist(),u[u.minute>72].home_away.fillna('').tolist())))
print(u[u.minute>=70][['minute','player','result','situation','home_team','away_team']].sort_values('minute').to_string())
print('goals in rows',u[u.result=='Goal'][['minute','player']].to_string())
print('other rows same season same clubs, any order',sorted(set(zip(d[(d.season==2023)&d.home_team.isin(['Udinese','Roma'])&d.away_team.isin(['Udinese','Roma'])].home_team,d[(d.season==2023)&d.home_team.isin(['Udinese','Roma'])&d.away_team.isin(['Udinese','Roma'])].date))))
r=rdata.read_rds(p,default_encoding='utf8'); v=r[(r.season==2023)&(r.home_team=='Udinese')&(r.away_team=='Roma')]
print('rdata: rows',len(v),'minute range',int(v.minute.min()),int(v.minute.max()),'rows after 72',int((v.minute>72).sum()))
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
def pos3(df): df.loc[7,'Pos_Tie']=not df.loc[7,'Pos_Tie']; df.loc[8,'Pos_Files_Voted']=df.loc[8,'Pos_Files_Voted']+1; return df
def pos2(df): u=df.MatchURL.iloc[0]; return df[df.MatchURL!=u]
rw('epl_shot_data.parquet',shot); rw('ESP_M_1st_match_summary.parquet',ev); rw('understat_xg_data.parquet',hf); rw('GER_M_1st_positions.parquet',pos1); rw('FRA_M_1st_positions.parquet',pos2); rw('ENG_M_1st_positions.parquet',pos3)
print('mutated 6 files')
```

</details>

<details><summary>Full output of <code>t7_verify.py</code> on the final files</summary>

```
### A. plain files: same rows, same order, every kept cell
bundesliga_shot_data: source rows 88214 trimmed rows 88214 columns 16 cells 1411424 differences 0 
epl_shot_data: source rows 107838 trimmed rows 107838 columns 16 cells 1725408 differences 0 
la_liga_shot_data: source rows 100188 trimmed rows 100188 columns 16 cells 1603008 differences 0 
ligue_1_shot_data: source rows 96140 trimmed rows 96140 columns 16 cells 1538240 differences 0 
serie_a_shot_data: source rows 110026 trimmed rows 110026 columns 16 cells 1760416 differences 0 
ENG_M_1st_match_summary: source rows 37734 trimmed rows 37734 columns 6 cells 226404 differences 0 
ESP_M_1st_match_summary: source rows 44873 trimmed rows 44873 columns 6 cells 269238 differences 0 
FRA_M_1st_match_summary: source rows 37503 trimmed rows 37503 columns 6 cells 225018 differences 0 
GER_M_1st_match_summary: source rows 34742 trimmed rows 34742 columns 6 cells 208452 differences 0 
ITA_M_1st_match_summary: source rows 43180 trimmed rows 43180 columns 6 cells 259080 differences 0 
understat_xg_data: source rows 27182 trimmed rows 27182 columns 12 cells 326184 differences 0 
master_player_stats: source rows 34246 trimmed rows 34246 columns 7 cells 239722 differences 0 

### B. positions: Pos aside, every match equals the source file the rule picks; Pos, votes and ties recomputed by id; none lost
ENG: rows before 413736 after 83613 | matches 2939 source ids 2939 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['str'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ESP: rows before 421890 after 87400 | matches 2921 source ids 2921 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['str'], 'possession': ['str'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
FRA: rows before 395313 after 79421 | matches 2701 source ids 2701 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['str'], 'misc': ['str']}
GER: rows before 348924 after 69868 | matches 2348 source ids 2348 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['float'], 'passing': ['str'], 'defense': ['float'], 'misc': ['float']}
ITA: rows before 425429 after 87300 | matches 2917 source ids 2917 lost 0 | not equal to the picked file 0 | Pos wrong 0 votes wrong 0 tie wrong 0 | id repeated in a file 0 | files holding a match only under a dropped spelling 0 | Min types {'passing_types': ['float'], 'possession': ['str'], 'passing': ['str'], 'defense': ['str'], 'misc': ['float']}
totals {'before': 2005292, 'after': 407602, 'lost': 0, 'wrong_pick': 0, 'wrong_pos': 0, 'wrong_votes': 0, 'wrong_tie': 0, 'repeated': 0, 'lost_vote_files': 0}
rows by files voted {1: 659, 2: 349, 3: 80, 4: 29519, 5: 376995}
rows whose Pos changed from the picked file 3
  ('ENG', 2025, 'Yves Bissouma', 'CM', 'DM,CM', {'CM': 2, 'DM,CM': 3}, '')
  ('ENG', 2025, 'James Maddison', 'LM', 'AM,LM', {'LM': 2, 'AM,LM': 3}, 'attacking changes')
  ('ENG', 2025, 'Pape Matar Sarr', 'RM', 'DM', {'RM': 2, 'DM': 3}, '')
rows with a tie 1
  ('ITA', 2023, 'Gabriel Strefezza', 'FW', {'FW': 1, 'RW,LW': 1})

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

### H. club map and rule 2 links, Pool seasons
rows 168 | exact 111
unmapped: [('ENG', 'Hull', 'understat only'), ('ENG', 'Middlesbrough', 'understat only'), ('ENG', 'Queens Park Rangers', 'understat only'), ('ESP', 'Cordoba', 'understat only'), ('ESP', 'Sporting Gijon', 'understat only'), ('FRA', 'Evian Thonon Gaillard', 'understat only'), ('FRA', 'GFC Ajaccio', 'understat only'), ('FRA', 'Nancy', 'understat only'), ('FRA', 'SC Bastia', 'understat only'), ('GER', 'Ingolstadt', 'understat only'), ('ITA', 'Carpi', 'understat only'), ('ITA', 'Cesena', 'understat only'), ('ITA', 'Palermo', 'understat only'), ('ITA', 'Pescara', 'understat only')]
not exact:
  ENG | Brighton | Brighton & Hove Albion | 293
  ENG | Cardiff | Cardiff City | 38
  ENG | Huddersfield | Huddersfield Town | 76
  ENG | Ipswich | Ipswich Town | 24
  ENG | Leeds | Leeds United | 118
  ENG | Leicester | Leicester City | 252
  ENG | Luton | Luton Town | 38
  ENG | Norwich | Norwich City | 76
  ENG | Stoke | Stoke City | 38
  ENG | Swansea | Swansea City | 38
  ENG | Tottenham | Tottenham Hotspur | 294
  ENG | West Ham | West Ham United | 294
  ESP | Alaves | Alavés | 254
  ESP | Almeria | Almería | 76
  ESP | Atletico Madrid | Atlético Madrid | 291
  ESP | Cadiz | Cádiz | 152
  ESP | Deportivo La Coruna | Deportivo La Coruña | 38
  ESP | Leganes | Leganés | 135
  ESP | Malaga | Málaga | 38
  ESP | Real Oviedo | Oviedo | 4
  ESP | Real Valladolid | Valladolid | 174
  ESP | SD Huesca | Huesca | 76
  FRA | Nimes | Nîmes | 104
  FRA | Paris Saint Germain | Paris Saint-Germain | 275
  FRA | Saint-Etienne | Saint-Étienne | 200
  GER | Arminia Bielefeld | Arminia | 68
  GER | Borussia Dortmund | Dortmund | 261
  GER | Borussia M.Gladbach | Mönchengladbach | 260
  GER | Darmstadt | Darmstadt 98 | 34
  GER | FC Cologne | Köln | 207
  GER | FC Heidenheim | Heidenheim | 57
  GER | Fortuna Duesseldorf | Düsseldorf | 68
  GER | Greuther Fuerth | Greuther Fürth | 34
  GER | Hertha Berlin | Hertha BSC | 204
  GER | Nuernberg | Nürnberg | 34
  GER | Paderborn | Paderborn 07 | 34
  GER | RasenBallsport Leipzig | RB Leipzig | 261
  GER | VfB Stuttgart | Stuttgart | 227
  ITA | AC Milan | Milan | 291
  ITA | Inter | Internazionale | 291
  ITA | Parma Calcio 1913 | Parma | 140
  ITA | SPAL 2013 | SPAL | 114
  ITA | Verona | Hellas Verona | 253
exact but 0 linked: [('ITA', 'Parma')]
FBref clubs reached by 2+ Understat names: {('ITA', 'Parma'): 2}
mapped on under 10 linked matches: [('ESP', 'Real Oviedo', 'Oviedo', '4')]
Link: same home club and same away club in the same season, nearest FBref date, at most 14 days. Tie-breaker left out.
home or away null 0 | matches whose Home_Team and Away_Team differ from Team 0
ordered pairs twice in one season, FBref: [] | Understat: []
Pool matches 12607 | linked 12604 | no link 3 | gap days to matches {0: 12588, 1: 13, 2: 1, 11: 2}
links with a gap above 0: gap, league, Understat date, clubs, FBref date, shot rows
  (11, 'FRA', '2018-04-14', 'Caen', 'Toulouse', '2018-04-25', 14)
  (11, 'ITA', '2024-04-14', 'Udinese', 'Roma', '2024-04-25', 28)
  (2, 'FRA', '2023-04-30', 'Strasbourg', 'Lyon', '2023-04-28', 18)
  (1, 'ENG', '2018-08-25', 'Fulham', 'Burnley', '2018-08-26', 37)
  (1, 'ESP', '2017-09-16', 'Eibar', 'Leganes', '2017-09-15', 15)
  (1, 'ESP', '2017-10-23', 'Celta Vigo', 'Atletico Madrid', '2017-10-22', 23)
  (1, 'ESP', '2017-11-05', 'Barcelona', 'Sevilla', '2017-11-04', 26)
  (1, 'ESP', '2022-05-15', 'Espanyol', 'Valencia', '2022-05-14', 23)
  (1, 'ESP', '2023-12-12', 'Granada', 'Athletic Club', '2023-12-11', 27)
  (1, 'FRA', '2018-05-12', 'Guingamp', 'Marseille', '2018-05-11', 38)
  (1, 'FRA', '2022-02-02', 'Lyon', 'Marseille', '2022-02-01', 21)
  (1, 'FRA', '2023-08-12', 'Nice', 'Lille', '2023-08-11', 20)
  (1, 'FRA', '2023-08-12', 'Brest', 'Lens', '2023-08-13', 25)
  (1, 'ITA', '2018-01-28', 'Sassuolo', 'Atalanta', '2018-01-27', 27)
  (1, 'ITA', '2018-01-28', 'Chievo', 'Juventus', '2018-01-27', 17)
  (1, 'ITA', '2024-05-24', 'Cagliari', 'Fiorentina', '2024-05-23', 25)
no link, rows dropped: league, season end year, date, clubs, rows, nearest same-order date
  ('GER', 2022, '2022-03-18', 'Bochum', 'Borussia M.Gladbach', 24, [])
  ('ITA', 2021, '2020-09-19', 'Verona', 'Roma', 29, [])
  ('ITA', 2024, '2024-06-02', 'Atalanta', 'Fiorentina', 20, [])
rows dropped 73

plain-file cells compared 9792594 differences 0

### G. MANIFEST rows and columns against the files
trimmed files 17 mismatches 0 | source rows in manifest 38
schemas differ within group: {'*_shot_data.parquet': 1, '*_positions.parquet': 1, '*_match_summary.parquet': 2}
positions columns ['MatchURL', 'Match_Date', 'Matchweek', 'Season_End_Year', 'Home_Team', 'Away_Team', 'Team', 'Player', 'Player_Href', 'Pos', 'Min', 'Pos_Files_Voted', 'Pos_Tie'] | shot columns ['id', 'league', 'season', 'match_id', 'date', 'player', 'player_id', 'home_team', 'away_team', 'X', 'Y', 'xG', 'situation', 'shotType', 'lastAction', 'result']
```

</details>
