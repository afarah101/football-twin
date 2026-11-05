# #6 spec: stand-in loader and rule 3 join module

Parent issue: #6. Tickets: #17, #18, #19, #20, #21. This spec overrides `docs/phase-1-plan.md` where they differ. "Outside scope" lists the plan lines that are now stale, because the plan is read-only for this planning session.

**How to read the evidence.** A number is either MEASURED or tagged `NOT RUN`, with the stage or ticket that proves it.
- `design check` means the script and output in "Appendix: design check". It ran on `data/standin/` at `ad7fddb`, and it writes nothing.
- `T7:n` means line n of `docs/reports/T7_trim.md`. `plan:n` means line n of `docs/phase-1-plan.md`.

## Problem Statement

The Twin model needs PlayerSeason and shot records, but its data sits in three private stand-in sources that share no id: worldfootballR Understat shot files, FBref positions and minutes, and Hugging Face season totals. Understat itself is down, and it answers with a maintenance page and HTTP 200 (#15). The join between these sources lives in a measuring script, with parts of its rules only in the plan and four open questions in #6. Nothing fails loudly when a file is wrong.

## Solution

One join module takes raw rows to the final join, and `scripts/measure_rule3.py` imports it, so only one version exists. A stand-in loader sits behind the interface the live adapter will use, and returns two lists of plain records, plus whether its source may publish. It fails loudly on a wrong file. One command writes a report listing every flagged, barred, stopped or unexplained case, with the key Ahmed would use to review it.

## Fixed facts

The spec keeps these. Changing one needs Ahmed.

- Keep the FBref name join. Understat is down. Switch to Understat-only only after this box on #14 is checked: "Compare real Understat rosters with the stand-in FBref rosters before the Understat-only switch."
- Targets: 315,073 joined shot rows. Pool 3,108 of 3,136 before the id merges, and 3,109 of 3,137 after them.
- Never merge two Understat ids on one FBref id unless a `merge_ids` row in `review_decisions.csv` says so.
- The 28 flagged Pool candidates stay out of the Pool until review.
- Word order does not matter in name step 2.
- Ticket 1 is one join module, with one test for each rule 3 clause. Tests of the module go in `tests/`, and the `self_check` asserts in `scripts/measure_rule3.py` move there.
- `tests/fixtures/` holds real samples only. A clause with 0 real cases may use a small hand-made input, labelled `synthetic` in the test name and in a comment, and kept out of `tests/fixtures/`. A clause with 1 or more real cases must use a real sample.

## The number check

Every stage and every ticket ends with this same check. If a number moves, the build stops and reports it.

```bash
PY=~/sandbox/parquet-vet/venv/bin/python3
export PYTHONDONTWRITEBYTECODE=1
$PY scripts/measure_rule3.py > /tmp/rule3.txt; echo "exit $?"; grep -E '^Merges (off|on):' /tmp/rule3.txt | diff - <(printf 'Merges off: joined 315073 | Pool 3108 of 3136\nMerges on: joined 315073 | Pool 3109 of 3137\n') && echo SAME
```

Expected, exactly:

```
exit 0
SAME
```

**Evidence:** MEASURED on the full design in the design check, under `=== merges off` and `=== merges on, survivor rule`. The script does not print these two lines yet. Stage A of #17 adds them.

## User Stories

1. As Ahmed, I want one join module, so that the measured numbers and the built records can never come from two versions of the join.
2. As Ahmed, I want one test per rule 3 clause, so that a change to any clause fails a named test.
3. As Ahmed, I want every clause table row to say real or `synthetic`, so that I can see what rests on real data.
4. As Ahmed, I want the same three numbers checked after every stage, so that a moved number stops the build at once.
5. As Ahmed, I want a build session able to stop after any stage, so that ticket 1 can span several sessions without losing work.
6. As Ahmed, I want every automatic stop to have a review route, so that a right link can be restored.
7. As Ahmed, I want a stopped player-season to gain no new loose links, so that suspect links do not spread.
8. As Ahmed, I want a merged player to keep one id across seasons, so that the self-match test and own-season exclusion work.
9. As Ahmed, I want any Understat id on 2+ FBref ids to fail the run unless I allow it, so that a split player cannot pass unnoticed.
10. As Ahmed, I want season totals found by one written lookup, so that the guard and the metrics cannot disagree on a player's row.
11. As Ahmed, I want totals checked against shot rows on every run, so that the one source with no id has a check that does not rely on names.
12. As Ahmed, I want unexplained gaps listed with no guessed cause, so that I decide what they mean.
13. As a metric ticket, I want PlayerSeason and Shot records in domain language, so that I never read stand-in columns.
14. As the live adapter in #15, I want an interface with no stand-in words in it, so that I can replace the loader with no domain change.
15. As the Pool rule, I want minutes and attacking minutes on every PlayerSeason, so that one rule works on both sources.
16. As a metric ticket, I want penalties and own goals kept on Shot records, so that #8's own filter stays the only one.
17. As Ahmed, I want a missing, empty, unreadable or changed file to fail with its name and the way back, so that it is never read as missing data.
18. As Ahmed, I want one report with every case and its review key, so that I can write `review_decisions.csv` without reading code.
19. As Ahmed, I want the plan's terms in `GLOSSARY.md`, so that code and docs use one language.
20. As a future reader, I want the publishing gate written down, so that no number goes out before its checks.

## Implementation Decisions

### Decided by Ahmed

| Ref | Decision |
|---|---|
| Q1, open question 3 in #6 | The id merges run first, as one named step on the FBref rows, before exact matching. The join only ever sees merged ids, so the stop runs after the merges. `measure_rule3.py` imports that same path and runs it with merges on and off, checking both Pool counts. |
| Q2, open question 1 in #6 | A link stopped by the 2+ FBref ids rule counts as an existing key. The report lists it with its key and both minutes totals. `approve` restores it for all that player's shots on that key, `reject` leaves it removed, and `link_to` sends the rows to the named id. An approved link that leaves 2 FBref ids also needs a `cross_season_ids` row, and the error says so. |
| Q3, open question 2 in #6 | Two FBref ids with different names do not merge automatically. Both links stand, and the report lists the case. If either id is a Pool candidate, it is flagged and held until reviewed. The run also fails until a `cross_season_ids` row allows it. |
| Q4, open question 4 in #6 | A stopped player-season gains no `season_anchor` links. |
| Q5 | Season totals are found by the player-season's shot names, then the linked FBref name. If 2+ rows match, keep the one with the linked club in its team list. |
| Q5, one lookup | The minutes guard uses this same lookup. MEASURED: 7 Guirassy verdicts go from `none` to `agree`, and no pinned number moves. |
| Q6 | Ticket 1 covers everything from raw rows to the final join, including the whole review decisions file. PlayerSeason and Shot records and the report are later tickets. |
| Q7 | Survivor rule, below. |
| Q8 | Records and interface, below. |
| Stages | Ticket 1 is one ticket in ordered stages A to D. Each stage is one commit, lists its clauses as checkboxes with the test for each, and ends with the number check. A build session can stop after any stage. |
| Shot check | Totals against all shot rows minus own goals. The run fails if a Pool candidate that no other flag holds has a gap over 3 either way, because the gap is the absolute difference. MEASURED: no gap is negative today (design check). It runs after the review decisions. Do not raise the limit. If a later run fails on Roger, the run stops and Ahmed reviews it. |
| No season totals | If a Pool candidate that no other flag holds has no season-totals row, the run fails and names the player, so "stop and ask" is real. See D4. |
| First post | Not in #6. See "Publishing gate (not in #6)". |

### Rule wording, as approved

> **`player_season` with `link_to`.** The candidate's FBref id and `fbref_id` become one PlayerSeason under `fbref_id`, before any PlayerSeason total is worked out. Minutes, position rows and joined shots of both ids are added together. The Pool test and every per-90 metric read the combined record, so #8 never sees the split. If the two ids share a match, #6 stops with an error. If combining puts two Understat ids on one FBref id, #6 stops and names both ids, and the fix is a `merge_ids` row on the link. If the combined record fails the Pool test, it stays out and the report lists it.

> **Stop and anchors.** A player-season stopped by the 2+ FBref ids rule gains no `season_anchor` link. Step 3 still works out the link it would have made and lists it as barred, with its `season_anchor` key. Approving a stopped link does not lift the bar. Each barred link comes back only through its own `approve` or `link_to` row.

> **Which id survives a merge.** The merged player keeps the id they hold in other seasons. If neither id appears in another season, they keep the id with more minutes in that league-season. If neither id appears in another season and both have the same minutes, they keep the id that sorts first, and the #6 report lists the case. If both ids appear in other seasons, #6 does not merge them and lists the case for review.

> **Cross-season check, on every merges-on run.** After the join and the review decisions, the run fails if any Understat id reaches 2+ FBref ids across seasons, unless a review decision allows it. The allowing row is `item_type = cross_season_ids`, key `understat_id`, `decision = approve`. Any other decision on it stops the run. The #6 report lists each case with its seasons and minutes. MEASURED: 0 today, with the survivor rule.

### What a review key covers

These rules settle how the existing rows work. They add no row type and no column.

**`player_season`:** one row per key, and it covers every reason that key is flagged, so no field is needed to say which reason. A key exists if the FBref id is a Pool candidate flagged for any reason (no joined shots, `partial_join`, two ids with different names, a shot gap over 3, no single totals row), or if it is one of the ids in a refused merge. A row on any other key stops as stale, so a normal `approve` for Dennis Johnsen is valid whatever his shot gap.

| Decision | Result |
|---|---|
| `approve` | Back in the Pool. A gap over 3 then passes and is listed. It stops if the candidate has no joined shots (plan:144) or no single totals row (D4). It clears every flag on that player, including `partial_join`, and working `partial_join` out again does not bring the flag back (D36). On a refused merge, it stops and names `reject` and `link_to` (D37) |
| `reject` | Stays held. It clears a gap failure and a no-totals failure, so the run passes unless the cross-season check still fails. That check has its own row, `cross_season_ids`, and its error names it (Q3). On a refused merge, the ids stay apart and the case stays listed |
| `link_to` | The two records combine under `fbref_id`, using the approved wording above. Then every check runs again on the combined record, including the totals lookup with both ids' names. If it still fails, the run fails again and names the player, and Ahmed replaces the row with `reject` |

Refused merges with shared matches stop on `link_to`, because of the shared-match rule, so `reject` is their only route.

**One case, one answer.** Rows on different keys for one case must agree, or the run stops and names both keys: `approve` on a `player_season` key with `reject` on its `partial_join` key, `link_to` A to B with `link_to` B to A, `reject` on one id of a refused merge with `link_to` on the other, `approve` or `reject` with `link_to` or `merge_ids` on two keys that name one shot group, or two `link_to` or `merge_ids` rows with different ids on two keys that name one shot group (D44). One row alone is enough.

**`name_map`:** a key also exists for any link in an id collision, whichever step made it, so an exact or step 1 link can carry `merge_ids` (D38).

**`partial_join`:** a key exists for any player-season with an unjoined row, flagged or not. `link_to` joins those rows. This is the route for 2+ candidate groups on unflagged player-seasons. Marc Cardona's 1 unjoined row takes `reject`, because his FBref id has no row in match `b5b5ee07`, so `link_to` stops (D39). A row on a player-season with no unjoined row stops as stale. On an unflagged key, `approve` stops and names `link_to`, because there is no flag to clear, and `reject` leaves the rows unjoined and the case listed. `link_to` and `merge_ids` stop if `fbref_id` has no FBref row at the shooter's club in every match those shot rows come from (D39).

**When these keys appear:** the flags for no joined shots, `partial_join`, two ids and refused merges exist by stage D of #17. The flags for a shot gap and no totals arrive with #19, which extends the same rule.

### Records and interface

The interface returns one frozen `LoadedSource`, and nothing else: the two lists of frozen dataclass records, `source` and `may_publish`. It holds no stand-in word. `source` is a value, for example `standin`.

**`PlayerSeason`:** every player in the source's seasons, including defenders and players under 900 minutes.

| Field | Stand-in source |
|---|---|
| `player_id`: opaque text, one person across seasons, unless an approved `cross_season_ids` row keeps two ids (D40) | FBref id, after the merges |
| `name`, `league`, `season` (start year, 2023 = 2023/24), `clubs` | FBref rows |
| `minutes`, `attacking_minutes`, `other_minutes` | FBref `Min` and `Pos`, substitute appearances ignored for position |
| `display_position` | Most frequent first-listed attacking label |
| `xa`, `key_passes`, `xg_buildup`, `goals`, `assists` | Season totals, through the Q5 lookup. `None` for a PlayerSeason outside the Pool with no single row. MEASURED: 772 of 15,925, for example Mathias Jørgensen ENG 2017/18 (design check) |
| `held_for_review` | Yes if any review flag keeps it out |

**`Shot`:** joined rows only, carrying `player_id`, `league`, `season`, `x`, `y`, `xg`, `situation`, `shot_type`, `last_action` and `result`. Penalties and own goals stay in, because #8's criteria own that filter.

**Where the rest goes:**
- The Pool rule moves to `twin/domain/`: 900 or more minutes, attacking above other, and not held. `measure_rule3.py` imports it.
- `name_match`, `minutes_check`, `date_gap_days`, `sub_status`, `min_missing` and `partial_join` stay in the stand-in's review output and the report. The domain sees only `held_for_review`.
- `held_for_review` means no shot or per-90 metric may be used (plan:137). It is set on every flagged PlayerSeason, including those outside the candidates. MEASURED: 32 held, 28 of them Pool candidates and 4 outside, for example Jeffinho FRA 2022/23 (design check). Their Shot records stay in the list, and the Pool rule keeps them out of every metric.
- `sub_status` and `min_missing` hold nothing and remove nothing (plan:126, plan:127), so they are listed and need no review row (D41).
- Unjoined and dropped shots are not in the records. They are counted in the report.

**One limit:** `player_id` means the FBref id here and the Understat id on live data. #16 re-validates on live data, so nothing carries over.

### The publishing guard

`may_publish` belongs to the source, so it sits on `LoadedSource` and not on `PlayerSeason` or `Shot`. It defaults to False. `LoadedSource` is frozen and refuses True for any `source` other than `understat`, so `dataclasses.replace` cannot raise it either. A public file records the `source` of the `LoadedSource` it was built from.

| Where | Rule |
|---|---|
| Stand-in loader, #19 | Always False. It never sets the field, and no review row or flag can change it |
| Live adapter, #15 | False by default. True only when `docs/publishing_gate.csv`, read from the commit being run, records every check listed on #13 as done, with reviewer name and date. Those checks include #14, #15 and #16 done, PASS on live data, and no FBref data in the live Pool (plan:113-114). The adapter reads no FBref or stand-in file. Code alone can never set it True |
| Any publishing step, #13 | Fails the run unless `may_publish` is True, and the error names the source. It also fails if the file's `source` differs from the result's. A private local build is not a publishing step |
| Public file, #8 | Any step that writes a public file reads `LoadedSource.may_publish` and fails the run unless it is True, naming the source. |

**What a public file is.** A public file is site or release output: anything the Build writes for the site or a release, or deploys to a host. Generated review files, reports and fixtures in this private repo are not public files, and neither are results sent to the outside reviewer. Stand-in runs write the same site format into `build/private/`, so #8 can finish on the stand-in. No Vercel project is linked until the gate opens, and the Monday job deploys only through the publishing step.

**The gate file.** Columns `check`, `reviewer`, `date`. #13 owns the list of checks, and #15 reads the file. A missing file, a missing column, a blank reviewer or date, or an uncommitted edit each leave `may_publish` False. #15 also requires a signature: "The adapter returns may_publish True only if the last commit that touched docs/publishing_gate.csv has a verified signature from Ahmed's key." Signing is not set up yet.

**Tests.** The stand-in always returning False is `test_standin_loader_may_publish_is_always_false` (#19). The refusal is `test_synthetic_loaded_source_refuses_may_publish_on_any_other_source` (#19). The failing side is `test_public_file_step_fails_on_the_standin_result_and_names_the_source` (#8) and `test_publish_fails_on_the_standin_result_and_names_the_source` (#13). A file from another source is `test_synthetic_publish_fails_on_a_file_from_another_source` (#13). The gate file's cases are on #15.

The stand-in has no way back on purpose: the only route to publishing is the live adapter and the committed gate file. See the open guard item in "Known open items".

### What counts as a wrong file

Each of these fails with one named error that gives the file, the reason and the way back. It is never read as missing data.

| Case | Way back |
|---|---|
| A file the loader reads is missing | `git checkout`, or `scripts/trim_standin.py` |
| It has 0 bytes, or a Parquet file has 0 rows | Same |
| It cannot be read | Same |
| A column the loader needs is missing | Same |
| Its SHA-256 differs from `MANIFEST.md` | Same. The trim rewrites the manifest |
| The folder has no `MANIFEST.md` | Same |
| `review_decisions.csv` is missing or has 0 bytes | Restore it from git |
| `review_decisions.csv` is missing a column | Restore the column by hand or from git. The trim cannot rebuild this file |

A header-only `review_decisions.csv` is valid and means no decisions. All file reads go through one place, `twin/infrastructure/standin/files.py`.

### Layout

| Path | Holds |
|---|---|
| `twin/domain/` | `PlayerSeason`, `Shot`, `LoadedSource`, the interface, the Pool rule |
| `twin/infrastructure/standin/player_join.py` | Rule 2, id merges, rule 3, review decisions |
| `twin/infrastructure/standin/` | The loader and `files.py` |
| `tests/test_player_join.py` | The clause tests |
| `tests/test_standin_loader.py`, `tests/test_standin_files.py`, `tests/test_domain_boundary.py` | Adapter seam, wrong files, domain boundary |
| `tests/fixtures/standin/` | Real samples: `rule3__*` and the 22 existing samples, re-cut, plus `loader_sample/` |

#8 says it creates the `twin` layout. #6 makes only the folders it needs. `VISION.md` and `CONTEXT_MAP.md` stay with #8.

## Tickets

| Ticket | Title | Blocked by | Covers these #6 boxes |
|---|---|---|---|
| #17 | Rule 3 join module, stages A to D | None | Every rule 3 clause tested; all 4 open questions |
| #18 | Re-cut fixtures from the trimmed files | #17 | Tested at the adapter seam, real fixtures |
| #19 | PlayerSeason and Shot records behind the adapter interface | #17, #18 | Records in domain language; takes the live adapter; no network calls; tested at the adapter seam |
| #20 | Loader fails loudly on a wrong file | #19 | A missing, empty or unreadable file is a failure |
| #21 | #6 report, review lists and glossary | #19, #20 | Plan rules asking for the report; T7:53 glossary terms |

The 4 open questions map to these tests in #17:

| Open question in #6 | Tests |
|---|---|
| 1. A stopped link has no review route | `test_b_synthetic_stopped_link_is_listed_with_its_key`, `test_d_synthetic_approve_restores_stopped_link`, `test_d_synthetic_reject_leaves_stopped_link_removed`, `test_d_synthetic_link_to_redirects_stopped_link` |
| 2. Two ids with different names | `test_b_synthetic_two_ids_with_different_names_keep_both_links`, `test_c_synthetic_two_id_candidate_is_held` |
| 3. Stop and merge order | `test_b_synthetic_merged_ids_do_not_trigger_the_stop`, `test_a_merges_off_leaves_two_ids_apart` |
| 4. The stop and season anchors | `test_b_synthetic_stopped_player_season_gains_no_anchor`, `test_d_synthetic_approving_stopped_link_keeps_the_bar`, `test_d_synthetic_barred_link_returns_through_its_own_row` |
| Each barred link is listed with its `season_anchor` key (Q4) | Q4 | B | `test_b_synthetic_barred_link_is_listed_with_its_key` | synthetic: 0 real (design check) |

Every ticket ends with a fresh-session evaluator run, checked by a command in the ticket, before it counts as done.

## Testing Decisions

A good test checks behaviour at a seam, through inputs and outputs, not internal functions it does not need.

| Seam | Input | Output | Test file |
|---|---|---|---|
| Join module | Real samples, or `synthetic` for 0-case clauses | Links, flags, stops | `tests/test_player_join.py` |
| Adapter | `tests/fixtures/standin/loader_sample/` | Records or a failure | `tests/test_standin_loader.py`, `tests/test_standin_files.py` |
| Whole run | `data/standin/` | The pinned numbers | `scripts/measure_rule3.py` |

**Domain boundary test:** `test_domain_imports_no_pandas_pyarrow_infrastructure_or_fbref` in `tests/test_domain_boundary.py`. It fails if `twin/domain/` imports `pandas`, `pyarrow` or anything from infrastructure, or mentions FBref. It checks the structure, and the real proof comes when #15 is built. Ticket: #19.

Prior art: `tests/test_measure_rule3.py` tests the real Chema, Hwang and Baba cases, and its cases move to `tests/test_player_join.py`. The runner stays `unittest`.

### Rule 3 clause table

Stage A also holds the rule 1, 2 and id merge clauses, because Ahmed placed them in ticket 1. MEASURED counts come from the design check or the cited line. 184 clauses: 70 real, 114 `synthetic`. A hand-made decision row on real data rows counts as `synthetic`, because only 1 real decision row exists.

| Clause | Plan line | Ticket 1 stage | Test name | Real or `synthetic` |
|---|---|---|---|---|
| Tie-breaker matches are excluded from minutes | 121 | A | `test_a_tie_breaker_match_is_excluded_from_minutes` | real: Spezia v Hellas Verona `e0449015`, 31 rows (T7:753) |
| Tie-breaker matches are excluded from shots | 121 | A | `test_a_synthetic_tie_breaker_match_is_excluded_from_shots` | synthetic: 0 real, no shot row on that date (T7:750) |
| An Understat match links on same home club, same away club, same season | 122 | A | `test_a_match_links_on_home_away_and_season` | real: 12,604 matches (T7:902) |
| The link follows home then away, so A v B never links to B v A | 122 | A | `test_a_match_links_only_in_home_away_order` | real: both Getafe v Cadiz games, ESP 2023/24 (design check) |
| Club names go through `club_map.csv` | 122 | A | `test_a_club_names_go_through_club_map` | real: 57 of 168 clubs differ, Brighton and Brighton & Hove Albion (`data/standin/club_map.csv`) |
| The nearest FBref date wins when a pair has 2+ matches | 122 | A | `test_a_synthetic_nearest_fbref_date_wins` | synthetic: 0 real ordered pairs on 2+ matches (design check) |
| `date_gap_days` is recorded on every linked row | 122 | A | `test_a_date_gap_days_recorded_on_rescheduled_match` | real: Caen v Toulouse, 11 days (T7:904) |
| Links with a gap over 1 day are listed | 122 | A | `test_a_gap_over_1_day_is_listed` | real: 3 links, gaps of 2 and 11 days (design check, gap days) |
| Over 14 days is no link | 122 | A | `test_a_synthetic_gap_over_14_days_does_not_link` | synthetic: 0 real (design check, gap days) |
| Rows over 14 days are dropped and counted | 122 | A | `test_a_synthetic_gap_over_14_days_drops_and_counts_rows` | synthetic: 0 real (design check, gap days) |
| A gap of exactly 14 days links | 122 | A | `test_a_synthetic_gap_of_exactly_14_days_links` | synthetic: 0 real, largest gap is 11 days (design check, gap days) |
| Two FBref matches at the same date gap: lowest match id wins, and the case is listed (D9) | 122 | A | `test_a_synthetic_equal_date_gap_takes_lowest_match_id` | synthetic: 0 real (design check, ordered pairs) |
| A match with no FBref minutes drops its shot rows | 122 | A | `test_a_match_without_fbref_minutes_drops_its_shots` | real: Atalanta v Fiorentina 2023/24, 20 rows (T7:923) |
| Dropped rows are counted per league-season | 122 | A | `test_a_dropped_shots_are_counted_per_league_season` | real: Atalanta v Fiorentina 2023/24, 20 rows (T7:923) |
| Shot rows from 2014/15 to 2016/17 stay unchanged | 122 | A | `test_a_shots_before_pool_seasons_are_untouched` | real: any 2016/17 shot row (T7:781) |
| The league comes from the file name, not the `league` column | T7:59 | A | `test_a_league_comes_from_the_file_name` | real: `La_liga` and `La liga` (T7:59) |
| Two FBref ids merge when name, team and season match and their matches never overlap | 123 | A | `test_a_two_ids_merge_when_name_team_season_match` | real: Gabriel Strefezza ITA 2023/24 (design check) |
| Every merge is listed | 123 | A | `test_a_every_merge_is_listed` | real: 3 merges (design check) |
| The same name at a different team does not merge | 123 | A | `test_a_same_name_at_different_team_does_not_merge` | real: 22 name-seasons, Juanfran ESP 2017/18 (design check) |
| Ids whose matches overlap do not merge, and the case is listed | 123 | A | `test_a_synthetic_overlapping_ids_do_not_merge_and_are_listed` | synthetic: 0 real (design check, merge results) |
| A merged player keeps the id held in other seasons | Q7 | A | `test_a_merged_player_keeps_id_from_other_seasons` | real: Strefezza keeps `ac4a4508` (design check) |
| If neither id is in another season, the id with more minutes survives | Q7 | A | `test_a_merged_player_keeps_id_with_more_minutes` | real: Abdoul Meité keeps `8eb68164` (design check) |
| Same minutes: the id that sorts first survives, and the case is listed | Q7 | A | `test_a_synthetic_equal_minutes_keeps_id_that_sorts_first` | synthetic: 0 real (design check, merge results) |
| Both ids in other seasons: no merge, and the case is listed | Q7 | A | `test_a_synthetic_both_ids_in_other_seasons_do_not_merge` | synthetic: 0 real (design check, merge results) |
| Merges-off mode returns FBref rows unmerged, for the script's before-merge numbers only | Q1 | A | `test_a_merges_off_leaves_two_ids_apart` | real: Strefezza's two ids (design check) |
| The join uses name + club + season inside the linked match, never name alone | 128 | B | `test_b_same_name_resolves_by_club` | real: Luis Suárez ESP 2021/22, ids 2098 and 8978 (T7:257) |
| The club comes from `h_a` and the linked match | 128 | B | `test_b_club_comes_from_h_a` | real: 224,328 joined rows (design check) |
| `home_away` gives the side where `h_a` is empty | 128 | B | `test_b_club_comes_from_home_away_when_h_a_empty` | real: 90,745 joined rows (design check) |
| Rosters never decide the club | 128 | B | `test_b_roster_does_not_decide_the_club` | real: 4 groups, Luis Suárez at Granada (T7:235) |
| A shot row with no side stops the run, naming the file and row (D30) | D30 | B | `test_b_synthetic_row_with_no_side_stops` | synthetic: 0 real (T7:437) |
| A shot row with an unknown side value stops the run, naming the file and row (D30) | D30 | B | `test_b_synthetic_row_with_unknown_side_stops` | synthetic: 0 real (T7:437) |
| Exact match on the name after `html.unescape` | 129 | B | `test_b_exact_matches_after_html_unescape` | real: 523 groups, Dara O'Shea (design check) |
| 2+ exact roster matches do not link | 130 | B | `test_b_synthetic_two_exact_roster_matches_do_not_link` | synthetic: 0 real (design check) |
| 2+ exact matches skip step 1 | 130 | B | `test_b_synthetic_two_exact_matches_skip_step_1` | synthetic: 0 real (design check) |
| Step 1 ignores case | 130 | B | `test_b_step_1_ignores_case` | real: 915 groups (design check) |
| Step 1 ignores accents (NFKD) | 130 | B | `test_b_step_1_ignores_accents` | real: 15,172 groups (design check) |
| Step 1 ignores punctuation | 130 | B | `test_b_step_1_ignores_punctuation` | real: 161 groups (design check) |
| Step 1 folds ø ð đ ı ł æ þ | 130 | B | `test_b_step_1_folds_letters_nfkd_does_not_reduce` | real: all 7 letters, þ on 1 group (design check) |
| Step 1 folds ß | 130 | B | `test_b_step_1_folds_sharp_s` | real: Pascal Groß, among others. 0 of them need it to link, so the test asserts the compared name `pascal gross`, which fails if the fold goes (design check) |
| Step 1 folds œ | 130 | B | `test_b_synthetic_step_1_folds_oe` | synthetic: 0 real, no name holds œ (design check) |
| Step 1 counts a hyphen as a space | 130 | B | `test_b_step_1_counts_hyphen_as_space` | real: 1,269 groups (design check) |
| 2+ roster matches at step 1 do not link | 130 | B | `test_b_synthetic_two_step_1_roster_matches_do_not_link` | synthetic: 0 real (design check) |
| A shot name with 2+ roster matches after step 1 goes to step 2 | 131 | B | `test_b_synthetic_two_step_1_matches_go_to_step_2` | synthetic: 0 real (design check) |
| Step 2 stays inside the linked match and club | 131 | B | `test_b_step_2_stays_inside_match_and_club` | real: 4 groups named only on the other club (design check) |
| Step 2 links on a shared last name | 131 | B | `test_b_step_2_links_on_shared_last_name` | real: 7,359 groups (design check) |
| Step 2 links a shot name inside the roster name | 131 | B | `test_b_step_2_links_shot_name_inside_roster_name` | real: 4,300 groups, Bruno 2019/20 id 2302 (design check, T7:257) |
| Step 2 links a roster name inside the shot name | 131 | B | `test_b_step_2_links_roster_name_inside_shot_name` | real: 2,995 groups (design check) |
| "Part of the name" means whole words | 131 | B | `test_b_step_2_requires_whole_words` | real: 54 groups with letters inside a word (design check) |
| Word order does not matter in step 2 | 131 | B | `test_b_step_2_ignores_word_order` | real: 270 groups, Hee-Chan Hwang (design check, tests/test_measure_rule3.py:62) |
| A roster name inside the shot name matches in any order | 131 | B | `test_b_step_2_roster_inside_shot_in_any_order` | real: Abdul Rahman Baba, 8 rows (T7:148) |
| A shot name inside the roster name matches in any order | 131 | B | `test_b_synthetic_step_2_shot_inside_roster_in_any_order` | synthetic: 0 real (T7:148) |
| A roster player already matched in that match is not a candidate | 131 | B | `test_b_step_2_skips_roster_player_already_matched` | real: 129 groups (design check) |
| 0 candidates do not link | 131 | B | `test_b_step_2_no_candidate_does_not_link` | real: 1,289 groups (design check) |
| 2+ candidates do not link | 131 | B | `test_b_step_2_two_candidates_do_not_link` | real: 109 groups, Chema Rodríguez (design check) |
| Two shot names block each other if both would link to one roster player | 131 | B | `test_b_synthetic_two_shot_names_on_one_player_block_each_other` | synthetic: 0 real (design check, step 2 stopped) |
| A name with 2+ candidates never blocks | 131 | B | `test_b_two_candidate_name_does_not_block` | real: Ángel and Chema Rodríguez (tests/test_measure_rule3.py:16) |
| A step 2 link is flagged `name_match = map` | 131 | B | `test_b_step_2_link_is_flagged_map` | real: 1,118 player-seasons (design check) |
| One player-season reaching 2+ FBref ids loses all its step 2 links | 131 | B | `test_b_synthetic_two_fbref_ids_stop_step_2_links` | synthetic: 0 real (design check) |
| The stop keeps exact and step 1 links | 131 | B | `test_b_synthetic_stop_keeps_exact_and_step_1_links` | synthetic: 0 real (design check) |
| The stop runs after the merges (Q1) | Q1 | B | `test_b_synthetic_merged_ids_do_not_trigger_the_stop` | synthetic: 0 real (design check) |
| Two spellings on one FBref id do not trigger the stop | 131 | B | `test_b_two_spellings_on_one_id_do_not_stop` | real: Guirassy GER 2023/24 (design check, T7:149) |
| A stopped link is listed with its `name_map` key (Q2) | Q2 | B | `test_b_synthetic_stopped_link_is_listed_with_its_key` | synthetic: 0 real (design check) |
| Two ids with different names both keep their links, and the case is listed (Q3) | Q3 | B | `test_b_synthetic_two_ids_with_different_names_keep_both_links` | synthetic: 0 real (design check) |
| Step 3 links the one FBref id seen in 2+ other matches, same club, among the candidates | 133 | B | `test_b_anchor_links_id_seen_in_two_other_matches` | real: 105 groups (design check) |
| A group with 0 candidates never anchors | 133 | B | `test_b_anchor_never_runs_on_a_zero_candidate_group` | real: 1,289 groups (design check) |
| Under 2 other matches does not link | 133 | B | `test_b_anchor_needs_two_other_matches` | real: 1 group (design check) |
| No links for that club does not link | 133 | B | `test_b_anchor_needs_links_for_that_club` | real: 3 groups (design check) |
| An id that is not a candidate does not link | 133 | B | `test_b_synthetic_anchor_id_must_be_a_candidate` | synthetic: 0 real (design check) |
| Links to 2+ FBref ids do not anchor | 133 | B | `test_b_synthetic_anchor_needs_one_fbref_id` | synthetic: 0 real (design check) |
| An id already linked in that match does not link | 133 | B | `test_b_synthetic_anchor_id_already_linked_in_match` | synthetic: 0 real (design check) |
| Two shot names reaching one player do not link | 133 | B | `test_b_synthetic_anchor_two_names_on_one_player` | synthetic: 0 real (design check) |
| A `season_anchor` link never anchors another | 133 | B | `test_b_synthetic_anchor_link_does_not_anchor` | synthetic: 0 real (the rule runs one pass) |
| A stopped player-season gains no anchor (Q4) | Q4 | B | `test_b_synthetic_stopped_player_season_gains_no_anchor` | synthetic: 0 real (design check) |
| The guard runs once per `name_match = map` player-season, after the merges | 132 | C | `test_c_guard_runs_once_per_name_map_player_season` | real: 1,118 player-seasons (design check) |
| The limit is 90 minutes at low totals | 132 | C | `test_c_limit_is_90_minutes_at_low_totals` | real: André Anderson, limit 90 (T7:237) |
| The limit is 10% of the larger total above that | 132 | C | `test_c_limit_is_10_percent_of_larger_total` | real: Ezzalzouli, limit 93.3 (T7:238) |
| A gap exactly at the limit keeps the link | 132 | C | `test_c_synthetic_gap_at_the_limit_keeps_the_link` | synthetic: 0 real (design check) |
| A link beyond the limit is removed and listed | 132 | C | `test_c_link_beyond_the_limit_is_removed_and_listed` | real: André Anderson (T7:237) |
| The lookup tries the player-season's shot names | Q5 | C | `test_c_lookup_uses_shot_name` | real: 1,109 lookups (design check) |
| The lookup tries every spelling of that player-season | Q5 | C | `test_c_lookup_uses_any_spelling_of_the_player_season` | real: Guirassy GER 2023/24 (design check) |
| The lookup falls back to the linked FBref name | Q5 | C | `test_c_lookup_falls_back_to_fbref_name` | real: Guirassy, 6 lookups (design check) |
| 2+ rows narrow by the linked club | Q5 | C | `test_c_lookup_uses_club_when_two_rows_share_a_name` | real: 17 lookups (design check) |
| No single row: the link stays, flagged `minutes_check = none`, and is listed | 132 | C | `test_c_synthetic_no_season_row_keeps_link_flagged_none` | synthetic: 0 real once the guard uses Q5 (design check) |
| An anchor link goes through the guard | 133 | C | `test_c_anchor_link_passes_the_guard` | real: 14 player-seasons agree (design check) |
| The guard removes an anchor link beyond the limit | 133 | C | `test_c_synthetic_guard_removes_anchor_link` | synthetic: 0 real (design check) |
| A link the guard removed does not count as an anchor | 133 | C | `test_c_synthetic_guard_removed_link_does_not_anchor` | synthetic: 0 real (design check) |
| Every `season_anchor` link is listed | 133 | C | `test_c_every_anchor_link_is_listed` | real: 14 player-seasons (design check) |
| `name_map.csv` holds one row per kept `map` player-season | 135 | C | `test_c_name_map_holds_one_row_per_kept_player_season` | real: 1,117 rows (design check) |
| The run fails if the sample pairs differ from the committed file, read with `git show HEAD:docs/reports/name_map_sample.csv`, because the run rewrites the working copy first | D12 | C | `test_c_synthetic_redrawn_sample_pairs_fail_against_the_committed_file` | synthetic: 0 real redraws (design check) |
| Two Understat ids on one FBref id leave both unjoined and listed | 136 | C | `test_c_synthetic_id_collision_leaves_both_unjoined` | synthetic: 0 real after the guard (design check) |
| The guard runs before the collision check | 136 | C | `test_c_guard_removes_false_link_before_collision_check` | real: André and Djavan Anderson, ITA 2019/20 (T7:237) |
| Under 95% of rows joined sets `partial_join = yes` | 137 | C | `test_c_partial_join_below_95_percent` | real: Dennis Johnsen, 14 of 15 (T7:247) |
| 95.5% does not set the flag | 137 | C | `test_c_no_partial_join_above_95_percent` | real: Marc Cardona, 21 of 22 (T7:249) |
| Exactly 95% does not set the flag | 137 | C | `test_c_synthetic_exactly_95_percent_is_not_flagged` | synthetic: 0 real (design check) |
| No rows joined sets the flag | 137 | C | `test_c_no_joined_rows_is_partial_join` | real: Ruslan Malinovskiy (T7:248) |
| A Pool candidate with no joined shots is flagged | 137 | C | `test_c_candidate_with_no_joined_shots_is_flagged` | real: 27 candidates (design check) |
| A flagged Pool candidate stays out of the Pool | 137 | C | `test_c_flagged_candidates_stay_out` | real: 28 candidates (design check) |
| A `partial_join` player-season outside the candidates is held, so its shot and per-90 metrics are not used | 137 | C | `test_c_partial_join_outside_the_candidates_is_held` | real: Jeffinho FRA 2022/23, 1 of 10, one of 4 such (design check) |
| A two-id Pool candidate with different names is held (Q3) | Q3 | C | `test_c_synthetic_two_id_candidate_is_held` | synthetic: 0 real (design check) |
| The reader reads the file's columns | 138 | D | `test_d_reader_reads_the_real_row` | real: row 1 of `review_decisions.csv` |
| The reader accepts a byte order mark | T7:130 | D | `test_d_synthetic_reader_accepts_byte_order_mark` | synthetic: 0 real (the file has none) |
| `name_map` key form, with the name after `html.unescape` | 139 | D | `test_d_name_map_key_form` | real: `ESP\|2023\|10095\|Abdessamad Ezzalzouli\|bed68338` |
| `season_anchor` key form | 139 | D | `test_d_synthetic_season_anchor_key_form` | synthetic: 0 real rows |
| `partial_join` key form | 140 | D | `test_d_synthetic_partial_join_key_form` | synthetic: 0 real rows |
| `player_season` key form, season is `Season_End_Year` minus 1 | 141 | D | `test_d_synthetic_player_season_key_form` | synthetic: 0 real rows |
| `ITEM_TYPES` holds `player_season`, so `scripts/measure_rule3.py` accepts that row and a row with the old name stops | D35 | D | `test_d_synthetic_measure_rule3_accepts_a_player_season_row` | synthetic: 0 real rows (`data/standin/review_decisions.csv`) |
| `ITEM_TYPES` holds `cross_season_ids`, so `scripts/measure_rule3.py` accepts that row | D35 | D | `test_d_synthetic_measure_rule3_accepts_a_cross_season_row` | synthetic: 0 real rows (`data/standin/review_decisions.csv`) |
| Decisions apply after rule 3 and change exactly the approved link's rows | 142 | D | `test_d_approve_runs_after_rule_3_and_changes_30_rows` | real: Ezzalzouli, 30 rows, 315,043 to 315,073 (design check) |
| `approve` keeps a link the guard removed, flagged `minutes_check = approved` | 134, 142 | D | `test_d_approve_restores_guard_removed_link` | real: Ezzalzouli (`review_decisions.csv` row 1) |
| An approved link stays in `name_map.csv` | 134 | D | `test_d_approved_link_stays_in_name_map_csv` | real: Ezzalzouli (`review_decisions.csv` row 1) |
| `approve` on a `name_map` key does not approve a `season_anchor` key, and the reverse | T7:129 | D | `test_d_synthetic_approve_stays_on_its_own_link_type` | synthetic: 0 real rows |
| `approve` clears a `partial_join` flag | 142 | D | `test_d_synthetic_approve_clears_partial_join` | synthetic: 0 real rows |
| `approve` puts a `player_season` back in the Pool | 142 | D | `test_d_synthetic_approve_returns_player_season` | synthetic: 0 real rows |
| `approve` on a `player_season` clears its `partial_join` flag, and working it out again does not bring the flag back | D36 | D | `test_d_synthetic_approved_player_season_stays_cleared_after_recompute` | synthetic: hand-made row on Dennis Johnsen, 14 of 15 (T7:247) |
| `reject` removes a link and leaves its rows unjoined | 142 | D | `test_d_synthetic_reject_removes_a_link` | synthetic: 0 real rows |
| `reject` keeps a flag in place | 145 | D | `test_d_synthetic_reject_keeps_a_flag` | synthetic: 0 real rows |
| `reject` on a `player_season` does not clear the cross-season failure, and the error names `cross_season_ids` | D31 | D | `test_d_synthetic_reject_does_not_clear_the_cross_season_failure` | synthetic: 0 real (design check) |
| `link_to` joins the item's rows to `fbref_id`, flagged `name_match = reviewed` | 142 | D | `test_d_synthetic_link_to_joins_rows` | synthetic: 0 real rows |
| `player_season` with `link_to` adds both ids' minutes, position rows and joined shots under `fbref_id` before any total | Q3 check 1 | D | `test_d_synthetic_link_to_player_season_combines_records` | synthetic: 0 real rows |
| That combination stops if the two ids share a match | Q3 check 1 | D | `test_d_synthetic_link_to_player_season_stops_on_shared_match` | synthetic: 0 real rows |
| A combined record that fails the Pool test stays out and is listed | Q3 check 1 | D | `test_d_synthetic_combined_record_failing_pool_test_stays_out` | synthetic: 0 real rows |
| `merge_ids` does what `link_to` does, for two Understat ids on one FBref id | 142 | D | `test_d_synthetic_merge_ids_links_second_understat_id` | synthetic: 0 real rows |
| A `name_map` key exists for any link in an id collision, so an exact or step 1 link can carry `merge_ids` | D38 | D | `test_d_synthetic_merge_ids_key_exists_on_an_exact_link` | synthetic: 0 real collisions (design check) |
| The "no id collisions" check reads the state after the decisions, so a `merge_ids` row clears it | D38 | D | `test_d_synthetic_merge_ids_clears_the_no_id_collisions_check` | synthetic: 0 real collisions (design check) |
| Every `merge_ids` row is listed | 144 | D | `test_d_synthetic_merge_ids_row_is_listed` | synthetic: 0 real rows |
| `approve` restores a stopped link (Q2) | Q2 | D | `test_d_synthetic_approve_restores_stopped_link` | synthetic: 0 real rows |
| An approved stopped link that leaves 2 FBref ids also needs a `cross_season_ids` row, and the error says so | Q2 | D | `test_d_synthetic_approved_stopped_link_needs_a_cross_season_row` | synthetic: 0 real rows |
| `reject` leaves a stopped link removed (Q2) | Q2 | D | `test_d_synthetic_reject_leaves_stopped_link_removed` | synthetic: 0 real rows |
| `link_to` sends a stopped link's rows to the named id (Q2) | Q2 | D | `test_d_synthetic_link_to_redirects_stopped_link` | synthetic: 0 real rows |
| Approving a stopped link does not lift the anchor bar | Q4 check 2 | D | `test_d_synthetic_approving_stopped_link_keeps_the_bar` | synthetic: 0 real rows |
| A barred link comes back through its own `approve` or `link_to` row | Q4 check 2 | D | `test_d_synthetic_barred_link_returns_through_its_own_row` | synthetic: 0 real rows |
| A key absent from rule 3's output stops as stale | 143 | D | `test_d_synthetic_stale_key_stops` | synthetic: 0 real rows |
| A link the guard removed counts as an existing key | 143 | D | `test_d_guard_removed_link_is_not_stale` | real: Ezzalzouli |
| A link the id collision rule removed counts as an existing key | 143 | D | `test_d_synthetic_collision_removed_link_is_not_stale` | synthetic: 0 real collisions after the guard (design check) |
| One `player_season` row covers every flag on its key | D31 | D | `test_d_synthetic_one_player_season_row_covers_every_flag` | synthetic: 0 real rows |
| A `player_season` key exists for any flagged candidate | D31 | D | `test_d_synthetic_player_season_key_exists_for_any_flagged_candidate` | synthetic: 0 real rows |
| `link_to` on a `player_season` runs every check again on the combined record | D31 | D | `test_d_synthetic_link_to_player_season_reruns_every_check` | synthetic: 0 real rows |
| A refused merge has a `player_season` key, also for a player outside the Pool | D31 | D | `test_d_synthetic_refused_merge_has_a_player_season_key` | synthetic: 0 real (design check, merge results) |
| `link_to` on a refused merge combines the two ids | D31 | D | `test_d_synthetic_link_to_combines_a_refused_merge` | synthetic: 0 real |
| `reject` on a refused merge keeps the ids apart and the case stays listed | D31 | D | `test_d_synthetic_reject_keeps_a_refused_merge_apart` | synthetic: 0 real |
| `approve` on a refused merge stops, and the error names `reject` and `link_to` | D37 | D | `test_d_synthetic_approve_on_refused_merge_stops` | synthetic: 0 real (design check, merge results) |
| `link_to` A to B with `link_to` B to A on one refused merge stops, naming both | D37 | D | `test_d_synthetic_opposite_link_to_on_refused_merge_stops` | synthetic: 0 real (design check, merge results) |
| `reject` on one id of a refused merge with `link_to` on the other stops, naming both | D37 | D | `test_d_synthetic_reject_and_link_to_on_one_refused_merge_stop` | synthetic: 0 real (design check, merge results) |
| A `partial_join` key exists for any player-season with an unjoined row, and `link_to` joins those rows | D32 | D | `test_d_synthetic_link_to_joins_an_unflagged_unjoined_row` | synthetic: 0 real rows. On Marc Cardona's real data the row stops (D39), so his route is `reject` |
| A `partial_join` row on a player-season with no unjoined row stops as stale | D32 | D | `test_d_synthetic_partial_join_key_with_no_unjoined_row_is_stale` | synthetic: 0 real rows |
| `approve` on an unflagged `partial_join` key stops and names `link_to` | D39 | D | `test_d_synthetic_approve_on_unflagged_partial_join_stops` | synthetic: hand-made row on Marc Cardona, 21 of 22 (design check) |
| `reject` on an unflagged `partial_join` key leaves the rows unjoined and the case listed | D39 | D | `test_d_synthetic_reject_on_unflagged_partial_join_leaves_rows_unjoined` | synthetic: hand-made row on Marc Cardona (design check) |
| An unknown `item_type` stops | 143 | D | `test_d_synthetic_unknown_item_type_stops` | synthetic: 0 real rows |
| An unknown `decision` stops | 143 | D | `test_d_synthetic_unknown_decision_stops` | synthetic: 0 real rows |
| `link_to` with no `fbref_id` stops | 143 | D | `test_d_synthetic_link_to_without_fbref_id_stops` | synthetic: 0 real rows |
| `merge_ids` with no `fbref_id` stops | 143 | D | `test_d_synthetic_merge_ids_without_fbref_id_stops` | synthetic: 0 real rows |
| `link_to` with an `fbref_id` not in that league-season stops | 143 | D | `test_d_synthetic_link_to_fbref_id_outside_league_season_stops` | synthetic: 0 real rows |
| `link_to` or `merge_ids` stops if `fbref_id` has no FBref row at the shooter's club in every match those shot rows come from | D39 | D | `test_d_synthetic_link_to_target_not_in_those_matches_stops` | synthetic: 0 real rows |
| `merge_ids` with an `fbref_id` not in that league-season stops | 143 | D | `test_d_synthetic_merge_ids_fbref_id_outside_league_season_stops` | synthetic: 0 real rows |
| An `fbref_id` on any other decision stops | 143 | D | `test_d_synthetic_fbref_id_on_other_decision_stops` | synthetic: 0 real rows |
| `merge_ids` on a `player_season` stops | 143 | D | `test_d_synthetic_merge_ids_on_player_season_stops` | synthetic: 0 real rows |
| `merge_ids` that puts no second Understat id on that FBref id stops | 143 | D | `test_d_synthetic_merge_ids_without_second_id_stops` | synthetic: 0 real rows |
| Two rows on one key stop | 143 | D | `test_d_synthetic_two_rows_on_one_key_stop` | synthetic: 0 real rows |
| `approve` on a `player_season` key with `reject` on its `partial_join` key stops, naming both | D36 | D | `test_d_synthetic_approve_and_reject_on_two_keys_of_one_player_stop` | synthetic: hand-made rows on Dennis Johnsen |
| A `player_season` returning with no joined shots stops | 144 | D | `test_d_synthetic_player_season_without_shots_stops` | synthetic: 0 real rows |
| Two Understat ids on one FBref id without `merge_ids` stop, naming both | 144 | D | `test_d_synthetic_two_understat_ids_without_merge_ids_stop` | synthetic: 0 real rows |
| An `approve` that puts two Understat ids on one FBref id stops, naming both | 144 | D | `test_d_synthetic_approve_with_two_understat_ids_stops` | synthetic: 0 real rows |
| The result does not depend on row order | 144 | D | `test_d_synthetic_row_order_does_not_change_the_result` | synthetic: 0 real rows |
| `partial_join` is worked out again after the decisions | 145 | D | `test_d_synthetic_partial_join_is_recomputed_after_decisions` | synthetic: 0 real rows |
| The join returns the Pool count before and after the decisions, for #21's report to print | 146 | D | `test_d_pool_count_is_returned_before_and_after_decisions` | real: today's decisions file |
| An Understat id on 2+ FBref ids fails the run | Cross-season | D | `test_d_synthetic_two_fbref_ids_fail_the_run` | synthetic: 0 real with merges on (design check) |
| A `cross_season_ids` row with `approve` allows it, and the case is listed | Cross-season | D | `test_d_synthetic_cross_season_row_allows_two_ids` | synthetic: 0 real rows |
| Any other decision on `cross_season_ids` stops | Cross-season | D | `test_d_synthetic_cross_season_row_accepts_only_approve` | synthetic: 0 real rows |
| A `cross_season_ids` row on an id without 2+ FBref ids stops as stale | Cross-season | D | `test_d_synthetic_cross_season_row_stale_stops` | synthetic: 0 real rows |
| The cross-season check does not run in merges-off mode | Q1 | D | `test_d_merges_off_skips_the_cross_season_check` | real: Strefezza's two ids (design check) |
| A second id that a decision adds keeps `partial_join` until that id is approved | D36 | D | `test_d_synthetic_second_id_from_a_decision_keeps_partial_join` | synthetic: 0 real rows |
| `approve` on a link that agreed survives a `link_to` combine whose verdict is `disagree` | D31 | D | `test_d_synthetic_approve_on_an_agreeing_link_survives_a_combine` | synthetic: 0 real rows |
| The Pool count before the decisions counts a two-id hold, so it matches the count after | 146 | D | `test_d_synthetic_pool_before_counts_the_two_id_hold` | synthetic: 0 real rows |
| A held two-id candidate has a `player_season` key | D31 | D | `test_d_synthetic_held_two_id_candidate_has_a_review_key` | synthetic: 0 real rows |
| `approve` with `link_to` or `merge_ids` on two keys that name one shot group stops, naming both | D44 | D | `test_d_synthetic_approve_and_link_to_on_one_collided_anchor_stop` | synthetic: 0 real rows |
| Two `link_to` or `merge_ids` rows with different ids on two keys that name one shot group stop, naming both. The same id passes | D44 | D | `test_d_synthetic_two_link_to_on_one_collided_anchor_stop` | synthetic: 0 real rows |
| `reject` with `link_to` or `merge_ids` on two keys that name one shot group stops, naming both | D44 | D | `test_d_synthetic_reject_with_a_moving_row_on_one_collided_anchor_stops` | synthetic: 0 real rows |
| `approve` on a link survives two `link_to` combines, whatever the verdict between them | D31 | D | `test_d_synthetic_approve_survives_two_combines` | synthetic: 0 real rows |
| `approve` clears `partial_join` on an id that a decision added | D36 | D | `test_d_synthetic_approve_on_an_id_from_a_decision_clears_partial_join` | synthetic: 0 real rows |
| `approve` clears `partial_join` on an id the player-season reaches only through a combine | D36 | D | `test_d_synthetic_approve_on_a_combined_id_clears_partial_join` | synthetic: 0 real rows |
| `approve` on a `player_season` key with `reject` on its `partial_join` key stops when the id comes from a decision or a combine, on the merges-on run | D36 | D | `test_d_synthetic_approve_and_reject_on_an_id_from_a_decision_stop` | synthetic: 0 real rows |
| `Keep their link` leaves out a rejected link | 142 | D | `test_d_synthetic_keep_their_link_count_leaves_out_a_rejected_link` | synthetic: 0 real rows |
| The merges-off run passes over a row good only on merged ids, and the merges-on run stops on it | D21 | D | `test_d_synthetic_merges_off_run_passes_over_rows_good_only_on_merged_ids` | synthetic: 0 real rows |

## Known open items

| Item | State | Owner |
|---|---:|---|
| Roger ESP 2023/24: totals 36, shot rows minus own goals 33, gap 3 | **Cause unknown.** Ruled out: a missing match, because both files hold all 380 matches and both Getafe v Cadiz games (design check, ESP 2023/24 matches) | Listed by #21, for Ahmed's review |
| David McGoldrick ENG 2020/21: totals 71, rows 70, gap 1 | **Cause unknown** | Listed by #21 |
| Jaime Mata ESP 2023/24: totals 34, rows 33, gap 1 | **Cause unknown** | Listed by #21 |
| Juan Latasa ESP 2023/24: totals 45, rows 44, gap 1 | **Cause unknown** | Listed by #21 |
| Chris Ramos ESP 2023/24: totals 78, rows 77, gap 1 | **Cause unknown** | Listed by #21 |
| The 28 flagged Pool candidates | Held until Ahmed reviews them (T7:250) | Listed by #21 with keys |
| The 149 `partial_join` player-seasons (T7:246) | Awaiting Ahmed's review | Listed by #21 with keys |
| Bamo Meïté and Abdoul Meité, FRA 2023/24: same player is only an inference from minutes (T7:252-255) | **Cause unknown.** No merge and no new row type, because nothing changes today | Listed by #21 |
| Substitute detection gaps: 305 of 91,589 events match no roster name, and 4 players are marked through two-URL matches (T7:58, T7:136) | Known limit, 0 Pool flips measured by the audit | Listed by #21 |
| Name map error rate is not measured. None of the 50 sample pairs has been checked against a source (T7:49) | Open | Publishing gate, comment on #13 |
| The repo cannot prove a person wrote `docs/publishing_gate.csv` (T7:137, F11). Any commit can edit it | **Open.** The requirement is an unchecked box on #15, with `test_live_may_publish_false_without_a_verified_signature_from_ahmeds_key`. Signing is not set up, by Ahmed's decision | #15 |
| An approved `cross_season_ids` row keeps two ids for one person, so self-match and own-season exclusion would read them as two players | 0 real rows. #9 and #10 each stop on a box if a row exists (D40) | #9, #10 |
| `master_player_stats.parquet` has no planned use (T7:34) | The loader does not read it | #20 leaves it outside the wrong-file rule |

## Publishing gate (not in #6)

No first-post ticket exists in #6. Plan line 113 blocks any post until #14, #15 and #16 are done. The same two checks are on #13 as unchecked boxes, with #14, #15 and #16 as blockers: https://github.com/afarah101/football-twin/issues/13#issuecomment-6636942459

- [ ] (a) Each named player's numbers are checked by hand against the live source page.
- [ ] (b) The 50 pairs in `docs/reports/name_map_sample.csv` are checked against FBref.

**Season totals cannot be traced to source.** The Hugging Face dataset gives no scrape date or method (`docs/reports/HF_dataset_vetting.md:27`). No number from it is cleared to publish.

**The guard.** Any publishing step fails unless the source says `may_publish`. See "The publishing guard".

**Nothing in #6 becomes public.** The join, the records, the report, `name_map.csv` and every fixture stay in the private repo. FBref data stays private under plan:113.

## Out of Scope

- Live Understat work (#14, #15), metrics and the Pool's public file (#8), twins (#9), validation (#10), the site (#11 to #13) and live re-validation (#16).
- Any first post or public output.
- Current-season records. `current_season` fixture rows are not returned, and the loader returns Pool seasons only.
- Editing `docs/phase-1-plan.md`, code, tests, data or reports in this planning session.

## Outside scope: found while planning, not touched

**Stale lines in `docs/phase-1-plan.md`:**

| Line | Why it is stale |
|---|---|
| :123 | No survivor rule, tie-breaker or cross-season check |
| :126 | The 7 flips were measured before the merges. `NOT RUN` on merged ids: #21 proves it |
| :128 | No stop for a shot row with no side or an unknown side (D30) |
| :131 | "Left to the id merges" overstates the rule (Q3) |
| :132 | The guard looks up the shot name as stored. It now uses the Q5 lookup |
| :133 | Nothing bars a stopped player-season from anchors (Q4) |
| :134 | Guirassy keeps `minutes_check = none`. MEASURED: he now reads `agree` |
| :135 | `minutes_check = none` now has 0 real rows |
| :137 | `held_for_review` also covers flagged player-seasons outside the candidates. The plan only keeps Pool candidates out |
| :138 | `item_type` has no `cross_season_ids` |
| :138, :141-145 | They use the old name of the review key. It is now `player_season` (D35) |
| :142 | `player_season` with `link_to` does not say the records combine |
| :143 | The stale rule does not name stopped links, barred links, `cross_season_ids`, refused merges, or `partial_join` keys on unflagged player-seasons |
| :145 | Does not say an `approve` stays cleared when `partial_join` is worked out again (D36) |
| :148-152 | The 4 open questions are answered here |
| :157 | Names `infrastructure/understat/` only. The spec adds `infrastructure/standin/` (D16) |
| :159 | Q26 says all tests go through three seams. The join module is a fourth, by Ahmed's decision |
| :163 | "No invented or hand-written fixture data" needs the `synthetic` exception, which stays out of `tests/fixtures/` |

**Other items:**
- `scripts/measure_rule3.py:39` still holds the old name of the review key. Stage D of #17 changes it. The function at `:325` is not the review key and keeps its name, and the design check below still calls it.
- `docs/phase-1-plan.md` does not link this spec, because it is read-only in this session.
- `T7_trim.md:121` prints Strefezza's new candidate under `674cfc5a`. The survivor rule makes it `ac4a4508`.
- #8 says it creates the `twin` layout. #6 now makes part of it.
- #16 is not a sub-issue of #1 (`gh api repos/afarah101/football-twin/issues/1/sub_issues`).
- The boxes in #6 are not ticked, because the `to-tickets` skill does not modify the parent.
- `.gitignore` does not cover `__pycache__`. Stage A of #17 fixes it.
- `scripts/measure_rule3.py:357` and `:597` rewrite `docs/reports/name_map_sample.csv` on every run. #17 keeps that, with the frozen-pairs check in D12.
- System `python3` has no pandas. Every check uses `~/sandbox/parquet-vet/venv`.

## Further Notes

**Exit rule, from Ahmed.** After the next evaluator round, only Critical and Major findings block #17. Minor findings go to the matching ticket as an unchecked box, and the spec does not grow for them. No new stops or clauses unless a Critical or Major finding needs them.

The `grill-with-docs` route ran with Ahmed's own rules where they differ from the skills: questions came one at a time, the glossary waits for #21 under the scope lock, and the spec is this file rather than a tracker issue.

## Appendix: design check

This is the prototype behind every `design check` number. It is a measurement, not project code. It imports `scripts/measure_rule3.py` as it stands at `ad7fddb`, so it stops working once #17 moves that logic. Stage checks take over from there.

<details><summary>Script</summary>

```python
"""Measure the #6 design on data/standin. Read-only: imports scripts/measure_rule3.py at ad7fddb and never calls its main, so it writes nothing.
Run from the repo root: PYTHONDONTWRITEBYTECODE=1 $PY design_check.py"""
import contextlib, csv, hashlib, html, io, random, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "scripts")
import measure_rule3 as m
import pandas as pd
raw, sh, clubs = m.load_positions(), m.load_shots(), m.understat_to_fbref_clubs()
um = m.season_minutes_by_name(clubs)
names_of = defaultdict(set)
for lg, s, i, n in zip(sh["league"], sh["season"], sh["player_id"], sh["player"]): names_of[(lg, s, i)].add(html.unescape(n))
hfi = defaultdict(list)
for r in pd.read_parquet(m.DATA / "understat_xg_data.parquet", columns=["player_name", "team", "league", "season", "shots"]).itertuples():
    lg = "ENG" if r.league == "EPL" else r.league
    hfi[(lg, int(r.season[:4]), html.unescape(r.player_name))].append(({clubs.get((lg, p.strip())) for p in r.team.split(",")}, int(r.shots)))
APPROVED = {row["key"] for row in m.read_review_decisions() if row["decision"] == "approve"}

def merge_with_survivor():
    rows, done = raw.copy(), []
    for (lg, y, _, player), part in raw.groupby(["league", "Season_End_Year", "Team", "Player"]):
        ids = sorted(part["fbref_id"].unique())
        if len(ids) < 2: continue
        ms = [set(part.loc[part["fbref_id"] == i, "match"]) for i in ids]
        if sum(map(len, ms)) != len(set().union(*ms)): done.append((lg, y, player, "matches overlap")); continue
        other = [i for i in ids if ((raw["fbref_id"] == i) & ~((raw["league"] == lg) & (raw["Season_End_Year"] == y))).any()]
        if len(other) > 1: done.append((lg, y, player, "both ids in other seasons")); continue
        minutes = part.groupby("fbref_id")["Min"].sum()
        keep = other[0] if other else sorted(ids, key=lambda i: (-minutes[i], i))[0]
        done.append((lg, y, player, ids, "keeps", keep))
        rows.loc[(rows["league"] == lg) & (rows["Season_End_Year"] == y) & rows["fbref_id"].isin(ids), "fbref_id"] = keep
    return rows, done

def run(pos, label, merged):
    links, gaps, _ = m.link_matches(sh, pos, clubs)
    rows_of, keys = m.shot_groups(sh, links, pos)
    groups, rosters = sorted(rows_of), m.build_rosters(pos)
    fb_names = pos.groupby(["league", "Season_End_Year", "fbref_id"])["Player"].agg(lambda s: sorted(set(s))).to_dict()
    fm = {k: int(v) for k, v in pos.groupby(["league", "Season_End_Year", "fbref_id"])["Min"].sum().items()}
    coc = defaultdict(set)
    for a, b, c, d in zip(pos["league"], pos["Season_End_Year"], pos["Team"], pos["fbref_id"]): coc[(a, b, d)].add(c)
    joined = m.join_by_name(groups, rosters)
    mapped, undecided, stopped, conflicts = m.name_map_links(groups, rosters, joined)
    routes = Counter()
    def guard(pairs):
        out = {}
        for p in sorted(pairs):
            opts = [o for n in sorted(names_of[(p.league, p.season, p.understat_id)]) for o in um.get((p.league, p.season, n), [])]; via = "shot name"
            if not opts: opts = [o for n in fb_names.get((p.league, p.season + 1, p.fbref_id), []) for o in um.get((p.league, p.season, html.unescape(n)), [])]; via = "FBref name"
            if len(opts) > 1: opts = [o for o in opts if o[0] & coc[(p.league, p.season + 1, p.fbref_id)]]; via += " + club"
            routes[via] += 1
            f = fm.get((p.league, p.season + 1, p.fbref_id), 0)
            out[p] = "none" if len(opts) != 1 else "agree" if abs(opts[0][1] - f) <= m.minutes_limit(opts[0][1], f) else "disagree"
        return out
    pair = lambda g, f: m.PlayerSeasonName(g.league, g.season, g.understat_id, g.name, f)
    mp = {g: pair(g, f) for g, f in mapped.items()}
    gd = guard(set(mp.values()))
    after_guard = {**joined, **{g: ("map", f) for g, f in mapped.items() if gd[mp[g]] != "disagree"}}
    anchors, astop = m.season_anchor_links(undecided, after_guard)
    no_guard_anchors, _ = m.season_anchor_links(undecided, {**joined, **{g: ("map", f) for g, f in mapped.items()}})
    ap = {g: pair(g, f) for g, f in anchors.items()}
    ag = guard(set(ap.values()))
    after = {**after_guard, **{g: ("season_anchor", f) for g, f in anchors.items() if ag[ap[g]] != "disagree"}}
    collisions = m.id_collisions(after)
    final = dict(after)
    for g, p in mp.items():
        if gd[p] == "disagree" and m.decision_key(p) in APPROVED: final[g] = ("map", p.fbref_id)
    with contextlib.redirect_stdout(io.StringIO()): pool = m.pool_candidates(pos)
    partial = m.partial_joins(rows_of, final)
    ids_of, nm, uid = defaultdict(set), defaultdict(set), defaultdict(set)
    for g, l in final.items():
        ids_of[(g.league, g.season, g.understat_id)].add(l[1]); k = (g.league, g.season + 1, l[1]); nm[k].add(html.unescape(g.name)); uid[k].add(g.understat_id)
    pset = set(pool)
    partly = {(k[0], k[1] + 1, f) for k, v in partial.items() if v[0] > 0 for f in ids_of[k] if (k[0], k[1] + 1, f) in pset}
    no_shots = {k for k in pool if k not in nm}
    print(f"=== {label}\njoined {sum(rows_of[g] for g in final)} | before decisions {sum(rows_of[g] for g in after)} | Pool {len(pool) - len(no_shots) - len(partly)} of {len(pool)} | no joined shots {len(no_shots)} | partly joined {sorted(partly)}")
    print(f"guard {dict(sorted(Counter(gd.values()).items()))} | routes {dict(sorted(routes.items()))} | anchors {len(anchors)} groups {sum(rows_of[g] for g in anchors)} rows, guard {dict(Counter(ag.values()))}, stopped {dict(astop)} | collisions {collisions} | stopped player-seasons {conflicts}")
    print(f"step 2 stopped {dict(sorted(stopped.items()))} | name map kept {len({mp[g] for g in mp if g in final})} | partial_join {len(partial)}")
    print(f"anchors that rest only on a guard-removed link: {len(set(no_guard_anchors) - set(anchors))}")
    if not merged: return
    u2f, f2u = defaultdict(set), defaultdict(set)
    for g, l in final.items(): u2f[g.understat_id].add(l[1]); f2u[l[1]].add(g.understat_id)
    # Later findings: limit boundary, unflagged unjoined rows, who is held, equal minutes, same name at two teams
    at_limit = 0
    for p in sorted(set(mp.values())):
        opts = [o for n in sorted(names_of[(p.league, p.season, p.understat_id)]) for o in um.get((p.league, p.season, n), [])] or [o for n in fb_names.get((p.league, p.season + 1, p.fbref_id), []) for o in um.get((p.league, p.season, html.unescape(n)), [])]
        if len(opts) > 1: opts = [o for o in opts if o[0] & coc[(p.league, p.season + 1, p.fbref_id)]]
        if len(opts) == 1: at_limit += abs(opts[0][1] - fm.get((p.league, p.season + 1, p.fbref_id), 0)) == m.minutes_limit(opts[0][1], fm.get((p.league, p.season + 1, p.fbref_id), 0))
    counts = m.join_counts(rows_of, final)
    unflagged = {k: v for k, v in counts.items() if v[0] < v[1] and k not in partial}
    held = {(k[0], k[1] + 1, f) for k, v in partial.items() for f in ids_of[k]} | no_shots
    print(f"guard gap exactly at the limit {at_limit} | unjoined rows on unflagged player-seasons {[(k, v, sorted(names_of[k])) for k, v in unflagged.items()]}")
    print(f"PlayerSeasons held by a flag {len(held)}, of them Pool candidates {len(held & pset)}, outside the candidates {sorted(held - pset)}")
    events = pd.concat([pd.read_parquet(m.DATA / f"{lg}_M_1st_match_summary.parquet", columns=["MatchURL", "Team", "Event_Type", "Event_Players"]) for lg in m.SHOT_FILE_OF_LEAGUE])
    subs = events[events["Event_Type"] == "Substitute"].drop_duplicates(["MatchURL", "Team", "Event_Players"])
    came_on = set(zip(subs["MatchURL"].str.extract(r"/matches/([0-9a-f]{8})/", expand=False), subs["Team"], subs["Event_Players"].str.split(" for ").str[0].str.strip()))
    sub_row = pd.Series([key in came_on for key in zip(pos["match"], pos["Team"], pos["Player"])], index=pos.index)
    att_row = pd.Series([bool(set(x.split(",")) & m.ATTACKING_POS) for x in pos["Pos"]], index=pos.index)
    keys3 = ["league", "Season_End_Year", "fbref_id"]
    tot = pd.DataFrame({"total": pos.groupby(keys3)["Min"].sum(), "att": pos[~sub_row & att_row].groupby(keys3)["Min"].sum(), "oth": pos[~sub_row & ~att_row].groupby(keys3)["Min"].sum()}).fillna(0)
    print(f"900+ minutes with equal attacking and other minutes {[(k, int(r.att)) for k, r in tot[(tot.total >= 900) & (tot.att == tot.oth)].iterrows()]}")
    same = pos.groupby(["league", "Season_End_Year", "Player"]).agg(ids=("fbref_id", "nunique"), teams=("Team", "nunique"))
    print(f"same name on 2+ FBref ids at 2+ teams in a league-season {int(((same.ids > 1) & (same.teams > 1)).sum())}, for example {list(same[(same.ids > 1) & (same.teams > 1)].head(3).index)}")
    raw_names = list(pos["Player"].unique()) + list(sh["player"].unique())
    print(f"names holding ß anywhere {[n for n in raw_names if 'ß' in n][:12]} | holding œ {[n for n in raw_names if 'œ' in n.lower()][:12]}")
    print(f"ESP 2023/24 matches: FBref {pos[(pos.league == 'ESP') & (pos.Season_End_Year == 2024)]['match'].nunique()}, shot file {sh[(sh.league == 'ESP') & (sh.season == 2023)]['match_id'].nunique()} | shot file Getafe v Cadiz games {sorted(sh[(sh.league == 'ESP') & (sh.season == 2023) & sh.home_team.isin(['Getafe', 'Cadiz']) & sh.away_team.isin(['Getafe', 'Cadiz'])]['date'].unique().tolist())} | FBref Getafe v Cádiz games {sorted(pos[(pos.league == 'ESP') & (pos.Season_End_Year == 2024) & pos.Home_Team.isin(['Getafe', 'Cádiz']) & pos.Away_Team.isin(['Getafe', 'Cádiz'])]['Match_Date'].unique().tolist())}")
    print(f"Understat ids on 2+ FBref ids {[u for u, v in u2f.items() if len(v) > 1]} | FBref ids on 2+ Understat ids {[f for f, v in f2u.items() if len(v) > 1]}")
    gap, nonzero = Counter(), []
    for k in pool:
        if k in no_shots: continue
        found = [o for x in nm[k] for o in hfi.get((k[0], k[1] - 1, x), [])] or [o for x in fb_names[k] for o in hfi.get((k[0], k[1] - 1, html.unescape(x)), [])]
        if len(found) > 1: found = [o for o in found if o[0] & coc[k]]
        if len(found) != 1: gap["no single totals row"] += 1; continue
        rows = sh[(sh["league"] == k[0]) & (sh["season"] == k[1] - 1) & sh["player_id"].isin(uid[k])]
        d = found[0][1] - (len(rows) - int((rows["result"] == "OwnGoal").sum())); gap[d] += 1
        if d: nonzero.append((k[0], k[1], sorted(nm[k]), d))
    totals_routes = Counter()
    for k in pool:
        if k in no_shots: continue
        found = [o for x in nm[k] for o in hfi.get((k[0], k[1] - 1, x), [])]; via = "shot name"
        if not found: found = [o for x in fb_names[k] for o in hfi.get((k[0], k[1] - 1, html.unescape(x)), [])]; via = "FBref name"
        if len(found) > 1: found = [o for o in found if o[0] & coc[k]]; via += " + club"
        totals_routes[via if len(found) == 1 else "none"] += 1
    print(f"season totals routes {dict(sorted(totals_routes.items()))}")
    held_totals = Counter()
    for k in no_shots:
        found = [o for x in fb_names[k] for o in hfi.get((k[0], k[1] - 1, html.unescape(x)), [])]
        if len(found) > 1: found = [o for o in found if o[0] & coc[k]]
        held_totals["one row" if len(found) == 1 else "no single row"] += 1
    print(f"no-joined-shots candidates through the FBref name {dict(held_totals)}")
    no_totals = []
    for k in fb_names:
        if k in pool: continue
        found = [o for x in nm[k] for o in hfi.get((k[0], k[1] - 1, x), [])] or [o for x in fb_names[k] for o in hfi.get((k[0], k[1] - 1, html.unescape(x)), [])]
        if len(found) > 1: found = [o for o in found if o[0] & coc[k]]
        if len(found) != 1: no_totals.append(k)
    print(f"outside the candidates {sum(k not in pool for k in fb_names)} | no single totals row {len(no_totals)}")
    print(f"shot gap {dict(sorted(gap.items(), key=str))} {nonzero}")
    # Real-case counts per clause
    c, letters = Counter(), Counter()
    for g in groups:
        r, un = rosters[(g.match, g.club)], html.unescape(g.name)
        ex = [p for p in r if p.player == un]; same = [p for p in r if p.compared == m.compared_name(g.name)]
        c["exact 2+"] += len(ex) > 1; c["step 1 2+"] += not ex and len(same) > 1; c["exact via html.unescape"] += len(ex) == 1 and un != g.name
        if not ex and len(same) == 1:
            both = un + same[0].player
            for ch in "øðđıłßæœþ": letters[ch] += ch in both.lower()  # not casefold: it turns ß into ss
            c["step 1 hyphen"] += "-" in both
            c["step 1 punctuation"] += any(not (x.isalnum() or x.isspace() or x == "-" or unicodedata.combining(x)) for x in unicodedata.normalize("NFKD", both))
            c["step 1 accents"] += any(unicodedata.combining(x) for x in unicodedata.normalize("NFKD", both))
            c["step 1 case only"] += un.casefold() == same[0].player.casefold()
    taken = {(g.match, joined[g][1]) for g in joined}
    for g in groups:
        if g in joined: continue
        s = m.compared_name(g.name)
        r = [p for p in rosters[(g.match, g.club)] if p.compared]
        cand = [p for p in r if m.is_name_map_candidate(s.split(), p.compared.split())]
        free = [p for p in cand if (g.match, p.fbref_id) not in taken]
        c["step 2 candidate already matched"] += len(free) != len(cand)
        c["step 2 letters inside a word, no whole-word match"] += not cand and any(s in p.compared or p.compared in s for p in r)
    rost = {p.fbref_id: p for rs in rosters.values() for p in rs}
    for g, f in mapped.items():
        s, r = m.compared_name(g.name).split(), rost[f].compared.split()
        c["step 2 last name"] += r[-1] == s[-1]; c["step 2 shot inside roster"] += set(s) < set(r); c["step 2 roster inside shot"] += set(r) < set(s); c["step 2 same words, other order"] += set(s) == set(r) and s != r
    other_club = sum(1 for g in groups if not any(p.compared == m.compared_name(g.name) for p in rosters[(g.match, g.club)]) and any(p.compared == m.compared_name(g.name) for (mt, cl), rs in ((key, rosters[key]) for key in ((g.match, x) for x in {pos_club for pos_club in (fbm_home[g.match], fbm_away[g.match])} - {g.club})) for p in rs))
    print(f"clauses {dict(sorted(c.items()))}\nfold letters {dict(sorted(letters.items()))} | side from h_a or home_away on joined rows {side_counts(keys, final)} | name only on the other club {other_club}")
    print(f"gap days {dict(sorted(gaps.items()))} | over 14 days {sum(v for k, v in gaps.items() if k > 14)} | exactly 95% {[k for k, v in m.join_counts(rows_of, final).items() if v[0] * 100 == v[1] * 95]}")
    print(f"FBref ids with 2+ names in a league-season {sum(len(v) > 1 for v in fb_names.values())}, in Pool {sum(len(v) > 1 and k in pset for k, v in fb_names.items())} | Pool candidates with 2+ clubs {sum(len(coc[k]) > 1 for k in pool)}")
    att = pos[pos["Pos"].str.split(",").map(lambda p: bool(set(p) & m.ATTACKING_POS))].assign(first=lambda d: d["Pos"].str.split(",").str[0])
    att = att[att["first"].isin(m.ATTACKING_POS)]
    n = att.groupby(["league", "Season_End_Year", "fbref_id", "first"]).size().rename("n").reset_index()
    ties = n[n.groupby(["league", "Season_End_Year", "fbref_id"])["n"].transform("max") == n["n"]].groupby(["league", "Season_End_Year", "fbref_id"]).size()
    print(f"display label ties {int((ties > 1).sum())}, in Pool {sum(k in pset for k in ties[ties > 1].index)}")
    pairs = sorted({mp[g] for g in mp if g in final})
    drawn = {(p.league, p.season, p.understat_id, p.fbref_id) for p in random.Random(m.SAMPLE_SEED).sample(pairs, m.SAMPLE_SIZE)}
    rows = list(csv.DictReader(open(m.SAMPLE_FILE, encoding="utf8")))
    print(f"sample pairs match the committed file {drawn == {(r['league'], int(r['understat_season']), int(r['understat_id']), r['fbref_id']) for r in rows}} | committed rows with minutes_check none {[(r['shot_name'], r['understat_season']) for r in rows if r['minutes_check'] == 'none']}")
    by = defaultdict(list)
    for r in pos.drop_duplicates("match").itertuples(): by[(r.league, r.Season_End_Year, r.Home_Team, r.Away_Team)].append(r.match)
    print(f"ordered pairs on 2+ FBref matches {sum(len(v) > 1 for v in by.values())} | minutes {int(raw['Min'].sum())} before merge, {int(pos['Min'].sum())} after | PlayerSeason keys {len(fm)}")

def side_counts(keys, final):
    t = Counter()
    for g, ha, ho in zip(keys, sh["h_a"], sh["home_away"]):
        if g in final: t["h_a" if (ha if pd.notna(ha) else "") != "" else "home_away"] += 1
    return dict(t)

first = raw.drop_duplicates("match").set_index("match")
fbm_home, fbm_away = first["Home_Team"].to_dict(), first["Away_Team"].to_dict()
run(raw, "merges off", False)
merged, done = merge_with_survivor()
print("merge results", done)
fm2 = merged.drop_duplicates("match").set_index("match"); fbm_home, fbm_away = fm2["Home_Team"].to_dict(), fm2["Away_Team"].to_dict()
run(merged, "merges on, survivor rule", True)
man = Path("data/standin/MANIFEST.md").read_text()
files = sorted(Path("data/standin").glob("*.parquet")) + [Path("data/standin/club_map.csv")]
print(f"hash check: {len(files)} files, not in MANIFEST {[p.name for p in files if hashlib.sha256(p.read_bytes()).hexdigest() not in man]}")
```

</details>

<details><summary>Output</summary>

```
=== merges off
joined 315073 | before decisions 315043 | Pool 3108 of 3136 | no joined shots 27 | partly joined [('ITA', 2022, '66784dee')]
guard {'agree': 1116, 'disagree': 2} | routes {'FBref name': 6, 'shot name': 1109, 'shot name + club': 17} | anchors 105 groups 229 rows, guard {'agree': 14}, stopped {'no links for that club': 3, 'under 2 other matches': 1} | collisions {} | stopped player-seasons []
step 2 stopped {'2+ candidates': 109, 'no candidate': 1289, 'player-seasons reaching 2+ FBref ids': 0} | name map kept 1117 | partial_join 149
anchors that rest only on a guard-removed link: 0
merge results [('FRA', 2024, 'Abdoul Meité', ['8eb68164', 'cb9ef70f'], 'keeps', '8eb68164'), ('FRA', 2024, 'Joseph Nduquidi', ['1d039497', 'f365b837'], 'keeps', '1d039497'), ('ITA', 2024, 'Gabriel Strefezza', ['674cfc5a', 'ac4a4508'], 'keeps', 'ac4a4508')]
=== merges on, survivor rule
joined 315073 | before decisions 315043 | Pool 3109 of 3137 | no joined shots 27 | partly joined [('ITA', 2022, '66784dee')]
guard {'agree': 1116, 'disagree': 2} | routes {'FBref name': 6, 'shot name': 1109, 'shot name + club': 17} | anchors 105 groups 229 rows, guard {'agree': 14}, stopped {'no links for that club': 3, 'under 2 other matches': 1} | collisions {} | stopped player-seasons []
step 2 stopped {'2+ candidates': 109, 'no candidate': 1289, 'player-seasons reaching 2+ FBref ids': 0} | name map kept 1117 | partial_join 149
anchors that rest only on a guard-removed link: 0
guard gap exactly at the limit 0 | unjoined rows on unflagged player-seasons [(('ESP', 2023, 5159), (21, 22), ['Marc Cardona'])]
PlayerSeasons held by a flag 32, of them Pool candidates 28, outside the candidates [('ESP', 2020, '7f203b54'), ('ESP', 2024, 'a6103274'), ('FRA', 2023, '45cce300'), ('ITA', 2024, '39769cff')]
900+ minutes with equal attacking and other minutes []
same name on 2+ FBref ids at 2+ teams in a league-season 22, for example [('ESP', 2018, 'Juanfran'), ('ESP', 2018, 'Raúl García'), ('ESP', 2019, 'Juanfran')]
names holding ß anywhere ['Pascal Groß', 'Stefan Kießling', 'Niko Gießelmann', 'Tim Dierßen', 'Christian Groß', 'Tom Krauß', 'Noah Weißhaupt', 'Connor Noß', 'Pascal Groß', 'Stefan Kießling', 'Niko Gießelmann', 'Christian Groß'] | holding œ []
ESP 2023/24 matches: FBref 380, shot file 380 | shot file Getafe v Cadiz games ['2023-11-06 20:00:00', '2024-05-12 12:00:00'] | FBref Getafe v Cádiz games ['2023-11-06', '2024-05-12']
Understat ids on 2+ FBref ids [] | FBref ids on 2+ Understat ids []
season totals routes {'FBref name': 5, 'shot name': 3093, 'shot name + club': 12}
no-joined-shots candidates through the FBref name {'no single row': 27}
outside the candidates 15925 | no single totals row 772
shot gap {0: 3105, 1: 4, 3: 1} [('ENG', 2021, ['David McGoldrick'], 1), ('ESP', 2024, ['Jaime Mata'], 1), ('ESP', 2024, ['Roger'], 3), ('ESP', 2024, ['Juan Latasa'], 1), ('ESP', 2024, ['Chris Ramos'], 1)]
clauses {'exact 2+': 0, 'exact via html.unescape': 523, 'step 1 2+': 0, 'step 1 accents': 15172, 'step 1 case only': 915, 'step 1 hyphen': 1269, 'step 1 punctuation': 161, 'step 2 candidate already matched': 129, 'step 2 last name': 7359, 'step 2 letters inside a word, no whole-word match': 54, 'step 2 roster inside shot': 2995, 'step 2 same words, other order': 270, 'step 2 shot inside roster': 4300}
fold letters {'ß': 0, 'æ': 123, 'ð': 286, 'ø': 214, 'þ': 1, 'đ': 162, 'ı': 233, 'ł': 178, 'œ': 0} | side from h_a or home_away on joined rows {'h_a': 224328, 'home_away': 90745} | name only on the other club 4
gap days {0: 12588, 1: 13, 2: 1, 11: 2} | over 14 days 0 | exactly 95% []
FBref ids with 2+ names in a league-season 28, in Pool 6 | Pool candidates with 2+ clubs 151
display label ties 918, in Pool 78
sample pairs match the committed file True | committed rows with minutes_check none [('Sehrou Guirassy', '2020')]
ordered pairs on 2+ FBref matches 0 | minutes 24894121 before merge, 24894121 after | PlayerSeason keys 19062
hash check: 18 files, not in MANIFEST []
```

</details>

### C1 check

How the Q5 lookup treats the 27 Pool candidates with no joined shots. Read-only, on `data/standin/` at `ad7fddb`.

<details><summary>Script</summary>

```python
"""Read-only: does the Q5 lookup reach a totals row for the Pool candidates with no joined shots? Count the D4 failure as worded and as scoped."""
import contextlib, html, io, sys
from collections import Counter, defaultdict
sys.path.insert(0, "scripts")
import measure_rule3 as m
import pandas as pd
raw, sh, clubs = m.load_positions(), m.load_shots(), m.understat_to_fbref_clubs()
pos = raw.copy()
for (lg, y, _, player), part in raw.groupby(["league", "Season_End_Year", "Team", "Player"]):
    ids = sorted(part["fbref_id"].unique())
    if len(ids) < 2: continue
    ms = [set(part.loc[part["fbref_id"] == i, "match"]) for i in ids]
    if sum(map(len, ms)) != len(set().union(*ms)): continue
    other = [i for i in ids if ((raw["fbref_id"] == i) & ~((raw["league"] == lg) & (raw["Season_End_Year"] == y))).any()]
    minutes = part.groupby("fbref_id")["Min"].sum()
    keep = other[0] if other else sorted(ids, key=lambda i: (-minutes[i], i))[0]
    pos.loc[(pos["league"] == lg) & (pos["Season_End_Year"] == y) & pos["fbref_id"].isin(ids), "fbref_id"] = keep
links, _, _ = m.link_matches(sh, pos, clubs)
rows_of, _ = m.shot_groups(sh, links, pos)
groups, rosters = sorted(rows_of), m.build_rosters(pos)
joined = m.join_by_name(groups, rosters)
mapped, undecided, _, _ = m.name_map_links(groups, rosters, joined)
after = {**joined, **{g: ("map", f) for g, f in mapped.items()}}
anch, _ = m.season_anchor_links(undecided, after)
final = {**after, **{g: ("season_anchor", f) for g, f in anch.items()}}
with contextlib.redirect_stdout(io.StringIO()): pool = m.pool_candidates(pos)
nm = defaultdict(set)
for g, l in final.items(): nm[(g.league, g.season + 1, l[1])].add(html.unescape(g.name))
fb = pos.groupby(["league", "Season_End_Year", "fbref_id"]).agg(names=("Player", lambda s: sorted(set(s))), cl=("Team", lambda s: set(s)))
hfi = defaultdict(list)
for r in pd.read_parquet(m.DATA / "understat_xg_data.parquet", columns=["player_name", "team", "league", "season"]).itertuples():
    lg = "ENG" if r.league == "EPL" else r.league
    hfi[(lg, int(r.season[:4]), html.unescape(r.player_name))].append(({clubs.get((lg, p.strip())) for p in r.team.split(",")}, r.team))
tally = Counter(); rows = []
for k in pool:
    y = k[1] - 1; has_shots = k in nm
    found = [o for x in nm.get(k, []) for o in hfi.get((k[0], y, x), [])]; via = "shot name"
    if not found: found = [o for x in fb.loc[k, "names"] for o in hfi.get((k[0], y, html.unescape(x)), [])]; via = "FBref name"
    if len(found) > 1: found = [o for o in found if o[0] & set(fb.loc[k, "cl"])]; via += " + club"
    state = "one row" if len(found) == 1 else "no single row"
    tally[("joined shots" if has_shots else "no joined shots", state)] += 1
    if not has_shots: rows.append((k[0], f"{y}/{str(y + 1)[2:]}", k[2], fb.loc[k, "names"], sorted(fb.loc[k, "cl"]), state, via if len(found) == 1 else "", found[0][1] if len(found) == 1 else ""))
print("all candidates", len(pool), dict(sorted(tally.items())))
for r in sorted(rows, key=lambda r: (r[5], r[0], r[1])): print(r)
```

</details>

<details><summary>Output</summary>

```
all candidates 3137 {('joined shots', 'one row'): 3110, ('no joined shots', 'no single row'): 27}
('ENG', '2017/18', '189cee7b', ['Javier Hernández'], ['West Ham United'], 'no single row', '', '')
('ENG', '2018/19', '189cee7b', ['Javier Hernández'], ['West Ham United'], 'no single row', '', '')
('ENG', '2021/22', '71b47ab9', ['Cucho'], ['Watford'], 'no single row', '', '')
('ESP', '2018/19', '71b47ab9', ['Cucho'], ['Huesca'], 'no single row', '', '')
('ESP', '2019/20', '71b47ab9', ['Cucho'], ['Mallorca'], 'no single row', '', '')
('ESP', '2020/21', '71b47ab9', ['Cucho'], ['Getafe'], 'no single row', '', '')
('ESP', '2020/21', 'ae86d473', ['Marcos André'], ['Valladolid'], 'no single row', '', '')
('ESP', '2021/22', '49dbab27', ['Isaac Palazón Camacho'], ['Rayo Vallecano'], 'no single row', '', '')
('ESP', '2021/22', 'ae86d473', ['Marcos André'], ['Valencia'], 'no single row', '', '')
('ESP', '2021/22', 'ce8039aa', ['Nico Ribaudo'], ['Espanyol'], 'no single row', '', '')
('ESP', '2022/23', '49dbab27', ['Isaac Palazón Camacho'], ['Rayo Vallecano'], 'no single row', '', '')
('ESP', '2022/23', '85bed4ee', ['Rodri'], ['Real Betis'], 'no single row', '', '')
('ESP', '2022/23', 'ce8039aa', ['Nico Ribaudo'], ['Espanyol'], 'no single row', '', '')
('ESP', '2023/24', '85bed4ee', ['Rodri'], ['Real Betis'], 'no single row', '', '')
('ESP', '2023/24', 'be719093', ['Isaac Bernal'], ['Sevilla'], 'no single row', '', '')
('ESP', '2023/24', 'f7e87032', ['Viktor Tsyhankov'], ['Girona'], 'no single row', '', '')
('FRA', '2022/23', '48d5bd33', ['Ruslan Malinovskyi'], ['Marseille'], 'no single row', '', '')
('FRA', '2023/24', 'f15f8b2b', ['Musa Al-Taamari'], ['Montpellier'], 'no single row', '', '')
('GER', '2022/23', 'b684a484', ['Jordan Pefok'], ['Union Berlin'], 'no single row', '', '')
('GER', '2022/23', 'de4cac2d', ['Silas Katompa'], ['Stuttgart'], 'no single row', '', '')
('GER', '2023/24', 'b684a484', ['Jordan Pefok'], ['Mönchengladbach', 'Union Berlin'], 'no single row', '', '')
('GER', '2023/24', 'de4cac2d', ['Silas Katompa'], ['Stuttgart'], 'no single row', '', '')
('ITA', '2017/18', '80dbbd10', ['Simeon Nwankwo'], ['Crotone'], 'no single row', '', '')
('ITA', '2019/20', '48d5bd33', ['Ruslan Malinovskyi'], ['Atalanta'], 'no single row', '', '')
('ITA', '2020/21', '48d5bd33', ['Ruslan Malinovskyi'], ['Atalanta'], 'no single row', '', '')
('ITA', '2020/21', '80dbbd10', ['Simeon Nwankwo'], ['Crotone'], 'no single row', '', '')
('ITA', '2021/22', '48d5bd33', ['Ruslan Malinovskyi'], ['Atalanta'], 'no single row', '', '')
```

</details>

## Decision log

Decisions Claude made alone, under Ahmed's standing rules.

**Rule checks:** 1 way back, 2 one path, 3 no silent merge, 4 ties, 5 list do not hide, 6 run check, 7 tests, 8 no guessing.

**Complexity count:** 1 new `item_type` (`cross_season_ids`, whose wiring Ahmed approved). 0 new columns. `player_season` is a rename, not a new row type. The limit that stops for Ahmed is 2 new row types, so it does not fire.

| ID | Decision | Rule checks | Evidence | Real cases today |
|---|---|---|---|---:|
| D1 | A wrong file is the list in "What counts as a wrong file". **New run-failing check. Why no existing route works:** a review row cannot vouch for a changed file, so the way back is restoring or re-trimming it | 1, 2, 5, 6, 7 | MEASURED: 18 hashed files, 0 differ from `MANIFEST.md` (design check). The loader reads 17 of them | 0 |
| D2 | A header-only `review_decisions.csv` is valid. 0 bytes is a failure | 1, 2, 7 | MEASURED: today's file has a header and 1 row | 0 |
| D3 | A shot gap over 3 either way, the absolute difference, uses the existing `player_season` row. `approve` lets that one gap pass, without raising the limit, and the report lists it. `reject` holds the PlayerSeason. It applies only to a candidate no other flag holds. The row follows D31. **New run-failing check, from Ahmed. Why no new row type:** the key and decisions already fit. Tests in #19: `test_synthetic_shot_gap_over_3_fails_the_run`, `test_synthetic_shot_gap_on_held_candidate_does_not_fail`, `test_synthetic_player_season_approve_allows_a_gap`, `test_synthetic_player_season_reject_holds_a_gap`, `test_roger_gap_of_3_passes` | 1, 2, 5, 6, 7 | MEASURED: 3,105 at 0, 4 at 1, 1 at 3, 0 over 3, across the 3,110 with joined shots. The 27 with no joined shots reach no totals row, so they have no gap (design check) | 0 over 3 |
| D4 | Run-failing, by Ahmed's decision: if a Pool candidate that no other flag holds has no single totals row, the run fails and names the player. A candidate another flag already holds is listed and does not fail. The check runs after the review decisions, so a row that clears the other flag and leaves no totals row fails the run. A `player_season` row with `reject` clears the failure and keeps the player held. `approve` stops, because 3 of 10 metrics would read as zero. Ahmed decided no row brings the player back in while no totals row exists ("Yes, leave it"). `link_to` changes the record, so the lookup runs again on it (D31). **New run-failing check. Why no existing route works:** the hold alone could pass unnoticed, and the failure is what makes Ahmed review it. `reject` is the existing row, and the clearing rule is Claude's, so that the run is not stuck for good (rule 1). Tests: `test_candidate_already_held_with_no_totals_row_does_not_fail` (real), `test_synthetic_no_single_totals_row_fails_the_run_and_names_the_player`, `test_synthetic_clearing_a_flag_with_no_totals_row_fails_the_run`, `test_synthetic_player_season_reject_clears_missing_totals_and_holds`, `test_synthetic_approve_on_candidate_without_totals_stops` | 1, 5, 6, 7, 8 | MEASURED: 3,110 candidates with joined shots have one row. All 27 with no joined shots have no single row, and all 27 are already flagged, so the failure count is 27 as first worded and 0 as scoped (C1 check) | 0 failing, 27 held |
| D5 | `cross_season_ids` is the only new row type. **Why no existing route works:** the other item types key on one link or one FBref id, and `merge_ids` covers the opposite direction, two Understat ids on one FBref id | 1, 2, 3, 5, 6, 7 | MEASURED: 0 Understat ids on 2+ FBref ids (design check) | 0 |
| D6 | A cross-season row is stale if the id holds fewer than 2 FBref ids after every decision | 1, 2, 7 | MEASURED: 0 such rows today | 0 |
| D7 | `PlayerSeason.name` is the spelling with most minutes, and a tie goes alphabetically. The report lists every id with 2+ names | 2, 4, 5, 7 | MEASURED: 28 ids, 6 in the Pool (design check) | 28 |
| D8 | Display label ties go alphabetically (plan:120), and the report lists them | 4, 5, 7 | MEASURED: 918 ties, 78 in the Pool (design check) | 918 |
| D9 | Two FBref matches at one date gap: lowest match id wins, and the report lists the case. No row overrules it, because that would need a second new row type for a case with 0 real rows. If one appears, Ahmed decides then | 2, 4, 5, 7 | MEASURED: 0 ordered pairs on 2+ matches (design check) | 0 |
| D10 | Three record checks fail the run, and each failure names the case: record minutes differ from the FBref rows, two records on one key, a Shot with no PlayerSeason. **Why no existing route works:** each means a code fault, not a data case, so the way back is fixing the code | 1, 2, 6, 7 | MEASURED: 24,894,121 minutes before and after the merges, 19,062 keys (design check). `NOT RUN` on records: #19 proves it | 0 |
| D11 | A PlayerSeason in the Pool with no totals fails the run and names it. **Why no existing route works:** D4 already fails the run or holds such a player, so reaching the Pool means a code fault | 1, 2, 6, 7 | MEASURED: 0 (design check) | 0 |
| D12 | Provisional. The run fails if the drawn sample pairs differ from the committed `docs/reports/name_map_sample.csv`, read with `git show HEAD:`, because the run rewrites the working copy first (`scripts/measure_rule3.py:597`). Test: `test_c_synthetic_redrawn_sample_pairs_fail_against_the_committed_file`. **Why no existing route works:** publishing check (b) rests on those 50 pairs, so a redraw needs Ahmed's approval in a commit. Stage C's check fails if more than the one Guirassy row changes | 1, 2, 5, 6 | MEASURED: the pairs match the committed file, and one committed row reads `none` (design check). `NOT RUN` that only that row changes: stage C of #17 proves it | 1 |
| D13 | `name_map.csv` and `review_decisions.csv` stay outside the generated `MANIFEST.md` (T7:53). The first is a join output, and the second is Ahmed's input | 2, 5 | MEASURED: both absent from `MANIFEST.md` | 2 files |
| D14 | Bamo Meïté gets no merge and no new row type | 3, 5, 8 | MEASURED: 1 shot row, 784 minutes together, under the 900 gate (T7:252-254) | 1 |
| D15 | Five tickets, in this order: join, fixtures, records, wrong files, report. Ticket 1 goes first because Ahmed fixed it | 2 | MEASURED: blockers set on the issues | Not applicable |
| D16 | Module and test paths as in "Layout". This is Claude's choice: plan:157 sets `twin/` with `domain/` and `infrastructure/understat/`, and names no stand-in folder or file, so `infrastructure/standin/` extends it by the same pattern | 2 | Plan:157 for `twin/` only | Not applicable |
| D17 | `scripts/cut_fixtures.py` becomes the one path for all fixtures, reading `data/standin/`. `SOURCE_RELEASE`, `read_source` and `sha256_of` stay, because the trim imports them | 2, 7 | MEASURED: `scripts/trim_standin.py:21` | Not applicable |
| D18 | One real sample folder, `loader_sample/`, serves the adapter seam, because the loader needs its file names | 2, 7 | `NOT RUN`: #18 proves it, with `test_loader_sample_holds_every_required_file` | Not applicable |
| D19 | `unittest` stays as the runner | 2 | MEASURED: `requirements.txt` has no pytest, and `tests/test_measure_rule3.py:1` uses unittest | Not applicable |
| D20 | The loader returns Pool seasons only | 2, 7 | MEASURED: 19,062 PlayerSeason keys (design check). `NOT RUN` on records: #19 proves it | 19,062 |
| D21 | Merges-off mode exists only so the script can print the before-merge numbers. The cross-season check does not run there | 2, 7 | MEASURED: the run with merges off holds Strefezza's two ids (`T7:251`) | 2 ids |
| D22 | One command writes the report, `docs/reports/T6_standin_loader.md`, so nothing is typed by hand | 2, 5, 6 | `NOT RUN`: #21 proves it, with the repeat check | Not applicable |
| D23 | Provisional. The worst case for matches with no event rows is re-measured on merged ids. If it is not 7, #21 stops and reports it, and Ahmed sets the new expected number in that ticket. It never changes the Pool (plan:126) | 5, 6, 8 | `NOT RUN`: #21 proves it. Plan:126 measured 7 before the merges | 7 before merges |
| D24 | "Equal attacking and other minutes stays out" has 0 real cases, so its test is `synthetic` | 7 | MEASURED: 0 at 900+ minutes (design check) | 0 |
| D25 | The existing "no id collisions" check stays. Its route is a `merge_ids` row, so stage D makes it read the state after the decisions (D38) | 1, 2, 6 | MEASURED: 0 collisions (design check) | 0 |
| D26 | `minutes_check = none` stays as a clause, now `synthetic`, because the guard's Q5 lookup leaves it 0 real cases | 1, 5, 7 | MEASURED: 0 `none` verdicts (design check) | 0 |
| D27 | The 2+ candidates, stopped and barred lists print review keys, so every route can be used without reading code. A 2+ candidate group prints its player-season's `partial_join` key (D32) | 1, 5 | `NOT RUN`: #21 proves it | 109 groups |
| D28 | The old tests' real cases (Chema, Ángel, Hwang, Baba) move to `tests/test_player_join.py` | 2, 7 | MEASURED: 8 tests pass at `ad7fddb` | 4 cases |
| D29 | The glossary terms go in #21, because this session's scope lock forbids `GLOSSARY.md` | 2, 5 | T7:53 | Not applicable |
| D30 | A shot row with no side or an unknown side stops the run and names the file and row. **New run-failing check. Why no existing route works:** the row has no club, so no review row can place it. The way back is restoring the file or re-trimming | 1, 2, 5, 6, 7 | MEASURED: every shot row fills exactly one side (T7:437). `scripts/measure_rule3.py:143` holds the stop today | 0 |
| D31 | One `player_season` row covers every flag on its key, and a key also exists for an id in a refused merge, including outside the Pool. `link_to` runs every check again. See "What a review key covers". **No new row type:** this widens the existing key, so the count stays at 1 | 1, 2, 3, 5, 7 | MEASURED: 0 refused merges (design check, merge results). 1 flagged candidate with joined shots, Dennis Johnsen | 0 refused |
| D32 | A `partial_join` key exists for any player-season with an unjoined row, flagged or not. **No new row type:** this widens the existing key | 1, 2, 5, 7 | MEASURED: 1 unflagged player-season, Marc Cardona, 21 of 22 (design check) | 1 |
| D33 | `held_for_review` is set on every flagged PlayerSeason, including 4 outside the candidates, and means no shot or per-90 metric may be used | 1, 5, 6, 7 | MEASURED: 32 held, 28 candidates, 4 outside (design check). `NOT RUN` on records: #19 proves it | 32 |
| D34 | `may_publish` sits on the loader result and defaults to False. `LoadedSource` refuses True for any source but `understat`. The stand-in never sets it. The live adapter sets it True only from a committed `docs/publishing_gate.csv` naming reviewer and date for every check on #13, which include #14, #15, #16 and PASS on live data (plan:113-114), and it reads no FBref or stand-in file. A public file records its source. Any publishing step fails unless `may_publish` is True or if the file's source differs, and names the source. **New run-failing check. Why no existing route works:** review rows act on players, so they must not be able to change what a source may do, and until now only written rules guarded this. The way back is the live adapter and the gate file, and the stand-in has none on purpose. **Limit:** until #15's signature box is done, this stops mistakes, not a deliberate edit | 1, 2, 5, 6, 7 | `NOT RUN`: `test_public_file_step_fails_on_the_standin_result_and_names_the_source` (#8), `test_publish_fails_on_the_standin_result_and_names_the_source` (#13) and `test_standin_loader_may_publish_is_always_false` (#19) prove it | 1 source |
| D35 | The review key is `player_season`, because it also applies outside the Pool (D31). **No new row type:** it is the same row under a new name, so the count stays at 1. The plan and `scripts/measure_rule3.py:39` still hold the old name, and stage D of #17 changes the script. It also adds `cross_season_ids`, which the script would refuse today | 2, 5, 7 | MEASURED: 0 rows of this type in `data/standin/review_decisions.csv`, so nothing needs migrating | 0 |
| D36 | `approve` on a `player_season` clears every flag on it, including `partial_join`, and the recompute does not bring it back. `approve` and `reject` on the two keys of one player stop. **New stop. Why no existing route works:** the two-row rule covers one key, and this is two keys for one case. The way back is correcting the row | 1, 2, 3, 7 | MEASURED: 1 such player, Dennis Johnsen, 14 of 15 (T7:247), with 0 decision rows on him | 1 |
| D37 | A refused merge is one case with a key per id. `approve` stops. Opposite `link_to` rows, or `reject` with `link_to`, stop and name both. **New stops. Why no existing route works:** the two-row rule covers one key. The way back is correcting the row | 1, 2, 3, 4, 7 | MEASURED: 0 refused merges (design check, merge results) | 0 |
| D38 | A `name_map` key exists for any link in an id collision, whichever step made it, and the "no id collisions" check reads the state after the decisions. **No new row type:** this widens the existing key (plan:143 already says "a link it made") | 1, 2, 7 | MEASURED: 0 collisions (design check). `scripts/measure_rule3.py:449` and `:602` read the state before decisions today | 0 |
| D39 | On an unflagged `partial_join` key, `approve` stops and `reject` leaves the rows unjoined and listed. `link_to` and `merge_ids` stop if the target has no FBref row at the shooter's club in every match those shot rows come from. **New stops. Why no existing route works:** shots would sit in matches with no minutes, which plan:122 rules out. The way back is correcting the row | 1, 2, 5, 7 | MEASURED: 1 unflagged player-season, Marc Cardona (design check), with 0 decision rows | 1 |
| D40 | An approved `cross_season_ids` row keeps two ids for one person. No new field carries this, because 0 rows exist. #9 and #10 each hold a box that fails while such a row exists, and Ahmed decides then | 1, 5, 6 | MEASURED: 0 such rows in `data/standin/review_decisions.csv` | 0 |
| D41 | `sub_status` and `min_missing` are listed and need no row, because they hold nothing. An automatic merge has no undo row: decisions apply after rule 3 (plan:142) and merges run before it, so an undo would change that order for no known wrong merge. If one is wrong, Ahmed changes the rule | 1, 5 | MEASURED: 3 merges, all listed (design check). Plan:126 and plan:127 set the flags as report-only | 3 merges |
| D42 | The number check compares the output with the pinned numbers using `diff`, so a rise fails. `scripts/measure_rule3.py:603` alone only checks `>=`, and it stays as it is | 6 | MEASURED: the script's line reads `count(final) >= MIN_JOINED_ROWS` | 0 |
| D43 | By Ahmed: a public file is site or release output: anything the Build writes for the site or a release, or deploys to a host. Generated review files, reports and fixtures in this private repo are not public files, and neither are results sent to the outside reviewer. Stand-in runs write the same site format into `build/private/`. No Vercel project is linked until the gate opens, and the Monday job deploys only through the publishing step | 1, 2, 5, 7 | `NOT RUN`: `test_standin_run_writes_only_under_build_private` (#8) and `test_monday_job_deploys_only_through_the_publishing_step` (#15) prove it | 1 source |
| D44 | By Ahmed: rows on different keys that name one shot group must agree. `approve` or `reject` with `link_to` or `merge_ids` stops, and so do two `link_to` or `merge_ids` rows with different ids. Two such rows with the same id pass. `approve` with `reject` passes, and the link stays out, as `test_d_synthetic_approve_on_anchor_key_does_not_restore_a_rejected_link` holds. **New stops, which Ahmed asked for although the exit rule adds none for a Minor. Why no existing route works:** the player would split across two ids, a `reject` would cancel the moving row, or the last row would win, each with no error. The way back is removing one row. `approve` with `merge_ids` to the same id also stops, and that case is open on #17 | 2, 3, 5, 7 | MEASURED: 0 real collisions after the guard (design check), and 0 such decision rows | 0 |
