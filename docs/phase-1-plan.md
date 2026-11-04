# Phase 1 plan: Statistical Twin model

## Goal
Type a player and season. Get his 5 closest statistical twins, a 2D map and a fingerprint chart. Runs online, free.

## Scope
- In: Premier League, La Liga, Bundesliga, Serie A, Ligue 1. 2014/15 to now. Forwards and attacking midfielders.
- Out: deep stats engine, trend finder, videos, mentality, defenders.
- On-screen line: "Matches how they shoot and create, not how they move."

## Data
- Source: Understat (free, non-commercial). Library: understatapi.
- Player-season fields: time, shots, npg, npxG, xA, key_passes, xGBuildup, position.
- Shot rows: location X/Y, lastAction, situation, shotType, result.
- Match rosters: per-match position.
- Download: 2 s delay, local cache, resume. Full backfill runs once on the laptop. Weekly job fetches new matches only.

## Pool rules
- Completed seasons only. The current season can be searched but is not in the pool.
- Minimum 900 minutes. Flag "small sample" below 1,500.
- Primary position = position with most minutes, in FW, FWL, FWR, AML, AMC, AMR.

## Metrics (10, equal weight)
- Per 90: shots, xA, key passes, xGBuildup.
- npxG per shot.
- Non-penalty shot shares: six-yard box, outside box, headers, after TakeOn, after Throughball.
- Display only (never in distance): goals, assists, npG − npxG.

## Method
1. Shrink each share to its league-season mean (beta-binomial, method of moments).
2. Z-score each metric within league-season. Clip at ±3.
3. Test 3 distance methods: Euclidean on z, cosine, Pearson.
4. Exclude the player's own seasons.
5. Output top 10 with league, minutes, and "closer than X% of all pairs".
6. 2D map: PCA. Print loadings and explained variance. Name no axis.
7. Twins can cross leagues. Label: "style twin, not level twin". Add a "same league only" filter.

## Validation (not self-graded)
1. Self-match: own next season in top 10 (exclusion lifted for this test). Compare with a random baseline.
2. Stability: rank correlation when each metric is dropped.
3. Blind spot-check, part of the outside review: a non-Claude model gets the metric tables and top-5 twins for 10 randomly chosen players (fixed seed) and rates each list as plausible or not, judging playing style only, not quality, fame or club. The reviewer sees player names and seasons, because judging style needs football knowledge. It runs in a fresh session, before any code review. Report the count. Launch needs at least 7 of 10 rated plausible.
4. Outside model reviews code and results.
5. The winning distance method = highest self-match rate. Launch also needs the outside review.

## Online
- GitHub Actions every Monday → one JSON per league-season → Vercel static site.
- Data stays in the private repo.

## Code
- pipeline (ingest, profiles, twins, build) and web. DDD terms: PlayerSeason, MetricProfile, PeerGroup, TwinMatch.
- Allowed libraries: understatapi, pandas, numpy, scipy, scikit-learn, pyyaml, pytest, pyarrow, rdata. pyreadr is not allowed (AGPL). See `docs/reports/library_vetting.md`.

## Open checks (STEP 0)
Reuse search, understatapi security sweep, rate test, exact lastAction and position strings, season coverage, field check.

## Decisions

These override the plan above where they differ.

### Repo
- Agent file is `CLAUDE.md`. Five default triage labels. Single-context domain docs.
- Private repo `afarah101/football-twin`. Tickets live in GitHub Issues.

### Data and display
- Q3: Raw Understat data and shot rows stay private. Public JSON holds only derived values: z-scores, twin lists, map coordinates and display stats. Subject to the Understat terms check.
- Q4: The site shows 5 twins, with "show more" up to the stored 10.

### Pool
- Q5: Primary position ignores substitute appearances and uses named positions only.
- Q6: A PlayerSeason is player + league + season. The 900-minute minimum applies to each stint. Stints are never merged.
- Q7: A searched current-season player is scored against the last completed season of their league until 30 players have qualified. Under 900 minutes shows "not enough minutes yet" and no twins.

### Method
- Q8: npxG per shot also shrinks toward its league-season mean (normal-normal, method of moments). Per-90 metrics stay unshrunk.
- Q9: Keep the planned distance methods. Print the correlation matrix. Any reweighting goes on a Phase 2 list.
- Comparison method: the exact basketball method (percentiles within league-season, Euclidean distance) runs as a 4th method. Its twin lists are reported next to ours. It is for comparison only, is never the default, and cannot be the winning distance method.

### Validation
- Q10: Each self-match test excludes all the player's seasons except the next one. The method is chosen on seasons up to 2023/24, and the rate is reported on later seasons.
- Q10: Self-match target is 40% on top 10. Result 30–39% = WEAK: do not launch, revisit metrics. Below 30% = FAIL. The random baseline is reported alongside.
- Q11: Ahmed writes the pairs. No pairs are suggested by anyone else. Format: 12 twin pairs and 5 not-twin pairs, seasons 2014/15 onwards, forwards or attacking midfielders with 900+ minutes.
- Q11: No distance code runs until Ahmed commits `config/face_validity_pairs.yaml`.
- Q11: A method passes face validity if at least 70% of twin pairs fall in the closest 5% of all pairs and no not-twin pair does.
- Q12: If no method reaches PASS on the self-match test, fewer than 7 of 10 twin lists are rated plausible in the blind spot-check (playing style only, not quality, fame or club), or the outside review rejects the results, the site does not launch. We revisit the metrics and do not lower the bar.
- Q19: The PASS, WEAK and FAIL bands apply to the later-season rate, judged on the point estimate. A confidence interval is shown beside it.
- Q20: The Basketball method uses the same 10 shrunk metrics and replaces only the z-score and clip step with percentiles. It appears in the validation report, not on the public site.
- Q21: The stability test is report-only, with no pass or fail. Any metric whose removal changes the rankings most is flagged for the outside review.
- Q22: The outside review is a non-Claude model on a free tier, such as Gemini. It sees code and results, never raw Understat data. It runs once, after validation and before launch, in addition to the evaluator skill.
- Face-validity pairs dropped. Validation = self-match test (40% target, PASS/WEAK/FAIL bands) + non-Claude outside review. This overrides Q11 and Q27.
- Names-only mode is no longer needed for future reports.

### Data source
- Q13: `understatapi` goes through vetting steps 1–5 in `~/sandbox`. No other library is considered unless it fails. It sits behind one adapter that adds the 2-second delay and retries.
- Q14: The backfill fetches by player, if STEP 0 proves on a sample that it matches the match data. Match-level fetching is the fallback.
- Q15: Shot shares, npxG per shot and shots per 90 all use non-penalty shots with own goals excluded.
- Q16: STEP 0 calibrates the box boundaries from real shot data and saves them as named constants. Starting estimates: X ≥ 0.8275 inside the box, X ≥ 0.9425 six-yard box. A heatmap checks them, and the Y limits are checked the same way.
- Q17: The six positions stay as written. STEP 0 counts and lists who `ML`/`MR` excludes in a one-season sample, and Ahmed decides from that list.
- Q18: If Understat's terms are silent or unreadable, the site launches with derived values only, a visible Understat credit and link, no ads, and a takedown contact. If the terms prohibit it, the site stays private.

### Stand-in source (while understat.com is down)
These also override earlier decisions where they differ.
- Pool seasons are 2017/18-2023/24, from worldfootballR shot files + FBref positions and minutes + HF season totals. Extend to 2014/15 from live Understat when it returns.
- Q10 split: choose the method on 2017/18-2021/22. Report PASS, WEAK or FAIL on the 2022/23 and 2023/24 transitions.
- Position source: FBref per-match Pos. Compare with Understat positions when the "Understat is back" issue opens.
- Multi-position rows: count as attacking if any label is FW, LW, RW or AM.
- LM/RM: stay "other", so they do not count as attacking labels. Ahmed decided from the names list.
- Position rule: a match row is "attacking" if any Pos label is FW, LW, RW or AM, else "other". Sub appearances ignored (Q5). A PlayerSeason joins the Pool if attacking minutes > other minutes.
- The 6 codes are display-only: show the most frequent first-listed attacking label. Position is never used in distance.
- Display labels: show FBref's own labels (FW, LW, RW, AM). Drop the 6 Understat codes while on the stand-in source.
- STEP 0 answers the data questions from the stand-in files (worldfootballR Understat shot files, FBref positions and minutes, HF season totals). Live Understat checks wait until the "Understat is back" issue opens.
- Stand-in loader: reads the local worldfootballR, FBref and HF files behind the same adapter interface the live Understat adapter will use later.
- Backfill on the stand-in source: trim the vetted stand-in files to the columns the build needs and store them privately as Parquet. Record the hash of each original file and commit the trim script, so the trim can be repeated. No network scraping.
- FBref data is used only for private building and testing. The public site (#13) launches only after positions and minutes come from live Understat (#14, #15), so no FBref data is public.
- Validation before the public launch (#16): re-run self-match, the blind spot-check and the full outside review on the live-Understat Pool. The stand-in PASS does not carry over. So Q22's outside review runs once on the stand-in and again on live data.
- Live self-match split, the original Q10 rule: choose the method on seasons up to 2023/24, and report PASS, WEAK or FAIL on the 2023/24 to 2024/25 and 2024/25 to 2025/26 transitions.
- Original stand-in files: private release https://github.com/afarah101/football-twin/releases/tag/stand-in-originals, with their hashes in its release notes.
- Reading `.rds` with rdata: always pass `default_encoding="utf8"`, drop rdata's 1-based index, and convert nulls to one standard (`pd.NA`) before writing Parquet.
- Box boundaries (Q16, calibrated in `docs/reports/T3_step0_facts.md`, replacing the starting estimates): `BOX_X_MIN` 0.8275, `BOX_Y_MIN` 0.2075, `BOX_Y_MAX` 0.7925, `SIX_X_MIN` 0.9425, `SIX_Y_MIN` 0.365, `SIX_Y_MAX` 0.635. A shot is inside a box when X is at or above the X line and Y is between the two Y lines, both inclusive.
- Site on the stand-in source: a private static site, run locally only and not deployed publicly. It has no Monday job, because the data does not update, and it shows "Data to 2023/24". The public launch uses live Understat data (#15), along with the Monday job and current-season search. The public site uses only live Understat data, so the public-launch terms check is Understat's terms (Q18, read in #14). The FBref (Sports Reference) and HF dataset terms and the worldfootballR repo's licence status apply only to the private stand-in.
- Ties: equal attacking and other minutes stays out of the Pool. Display-label tie: pick alphabetically.
- Rule for #6, tie-breaker matches: excluded from minutes and shots (filter on `Matchweek`).
- Rule for #6, matches with shots but no FBref minutes (e.g. ITA 2023/24 Atalanta v Fiorentina), in Pool seasons only (2017/18-2023/24): drop those shot rows, so shots and minutes always cover the same matches. Link an Understat match to FBref on the same home club and the same away club (in that order, through `club_map.csv`) in the same season. Each ordered pair plays once per season, so the link is unique. Take the nearest FBref date, at most 14 days from the Understat date. Over 14 days is no link, and the rows are dropped and counted. Record `date_gap_days` on every linked row, and list every link with a gap over 1 day in the #6 report. Report how many rows per league-season. 2014/15-2016/17 shot rows stay unchanged for later live-Understat use.
- Rule for #6, one player under two FBref ids: merge ids only when name, team and season match and their matches never overlap. List every merge in the #6 report.
- Rule for #6, Pos disagreements between files: use the majority Pos across the files that hold the match. On a tie, keep the chosen file's value.
- Rule for #6: re-cut `tests/fixtures/standin/` from `data/standin/`, so the fixtures match the trimmed schema.
- Rule for #6, the 100 Pool matches with no event rows (ESP 2022/23 10, FRA 2022/23 10, GER 2020/21 2, ITA 2019/20 68, ITA 2022/23 10): keep the rows and count each appearance as a start, because substitutes cannot be told apart there. Flag those 3,091 rows `sub_status = unknown`. The #6 report also gives the worst case, where every `Min` < 90 row in those matches is a substitute. It is reported only and never changes the Pool. Measured before id merges, it flips 7 PlayerSeasons: out of the Pool, Nico Ribaudo (ESP 2022/23), Giacomo Bonaventura (ITA 2019/20) and Fabio Miretti (ITA 2022/23); into the Pool, Mattias Svanberg and Aaron Ramsey (ITA 2019/20), Darko Lazović and Patrick Ciurria (ITA 2022/23).
- Rule for #6, the 4 Pool rows with null `Min` (Georges-Kévin N'Koudou ENG 2017/18, Jean-Clair Todibo FRA 2022/23, Andrea Petagna ITA 2021/22, Diego Llorente ITA 2023/24): keep the appearance, add 0 minutes, flag `min_missing = yes`, and list the 4 rows in the #6 report.
- Rule for #6, joining shots to players: never join by name alone. Use the id, or name + club + season. `player_id` and `Player_Href` are separate id systems, so a join between shot files and FBref uses name + club + season, inside the linked FBref match. The club comes from `h_a` plus the linked match: `h_a`, or `home_away` where `h_a` is empty, gives the side, and the linked FBref match's `Home_Team` or `Away_Team` gives the club on that side. Rosters never decide the club. `scripts/measure_rule3.py` measures this rule on `data/standin/`. The join runs in this order:
  - Exact: the name as stored, after `html.unescape`.
  - Step 1, name comparison: compare names with case, accents and punctuation removed (Unicode NFKD). Letters NFKD does not reduce are folded too (ø to o, ð to d, đ to dj, ı to i, ł to l, ß to ss, æ to ae, œ to oe, þ to th), and a hyphen counts as a space. This is the standard test.
  - Step 2, name map, within each linked match and club only: if a shot name has no roster match after step 1, and exactly one roster player on that club in that match has no shot name matched yet and either shares the last name, holds the whole shot name as part of their name (for example "Bruno" in "Bruno Fernandes"), or has their whole name inside the shot name (for example "Kylian Mbappé" in "Kylian Mbappe-Lottin"), link them and flag `name_match = map`. "Part of the name" means whole words. With 0 or 2+ candidates, do not link. If two shot names reach the same roster player, neither links. If one player-season's links reach 2+ FBref ids, none of them links, and the case is listed.
  - Minutes guard, on every #6 run, after the FBref id merges, once per `name_match = map` player-season: compare Understat season minutes (`minutes` in `understat_xg_data`, same league and season, the shot name as stored after `html.unescape`, and the linked player's club where 2+ rows share the name) with the FBref minutes of the linked id in that league-season. The limit is the larger of 90 minutes or 10% of the larger total. Beyond the limit, do not link, and list the row for Ahmed's review, unless Ahmed has approved that link, which is flagged `minutes_check = approved`. With no Understat row to compare, keep the link, flag `minutes_check = none` and list the row.
  - Step 3, season anchor, in a match where step 2 found 2+ candidates: link only if the same `player_id` links to one FBref id and no other in at least 2 other matches that season for the same club (`h_a`), and that FBref id is one of the candidates. Flag `name_match = season_anchor`. Only links that survive the minutes guard count as anchors, and a `season_anchor` link never anchors another. If that FBref id is already linked in that match, or two shot names reach the same player, do not link. The minutes guard runs on these links too, and the #6 report lists every one.
  - Decided by Ahmed: the link from Abdessamad Ezzalzouli ESP 2023/24 to FBref's Abde Ezzalzouli is approved (Understat 839 v FBref 933, gap 94, limit 93.3), because FBref uses both spellings that season and the other 8 shot rows join the same id. Sehrou Guirassy's 7 player-seasons keep their links to FBref's Serhou Guirassy, flagged `minutes_check = none`, because the season file spells the name Serhou.
  - Every `name_match = map` that keeps its link after the guard, including `minutes_check = approved` and `minutes_check = none`, is stored as one row per player-season in `data/standin/name_map.csv`, for Ahmed's review. One review covers all that player's shots.
  - Id collisions, two Understat ids on one FBref id in a league-season, checked after step 3 and its guard: never merge. Leave both unjoined and list them.
  - Partial join, after all the steps: a player-season (league, season, `player_id`) with less than 95% of its shot rows in linked matches joined gets `partial_join = yes`, including one with no rows joined. So does a Pool candidate with no joined shots, because it holds no link to its Understat rows. #6 must not use its shot or per-90 metrics. It lists those player-seasons for Ahmed's review instead.
  - The #6 report gives the join rate in 3 steps: exact, after step 1, after step 2. It then gives the rate after the guard, after step 3 and its guard, and after the id collision rule. Rows still unjoined are counted per league-season. It also says how Raúl García 2018/19 (id 5114), Bruno 2019/20 (id 2302) and Ousmane Camara 2022/23 (ids 11016 and 11249) resolved, for Ahmed's review.

### Site and code
- Q23: The build precomputes everything, including both twin lists (all leagues and same league) and closeness percentiles. The site is plain static HTML and JS with inline SVG, no framework, and no distance maths in the browser. Two files join the per-league-season JSON: a name index and the map points.
- Q24: One context, `twin/`: `domain/` (profiles, twins), `application/` (build), `infrastructure/understat/` (ingest, behind the anti-corruption layer), `interface/web/` (site). Plus `VISION.md` and `CONTEXT_MAP.md`.
- Q25: Raw data is gzipped files committed to the private repo. The Monday job fails and keeps the last good site if any league-season's player count or minutes drop, or any request returns 404.
- Q26: All tests go through three seams: Build (recorded Understat data in, public site files out), Understat adapter (recorded responses and errors in, records or a failure out) and Validation report (Pool in, self-match PASS, WEAK or FAIL for each method out). The site gets one browser smoke test against a small fixture.
- Q27: The pairs rule is literal and includes tests on made-up data. Every ticket touching distance is blocked by a ticket assigned to Ahmed. The Validation report refuses to run unless the file has 12 twin pairs and 5 not-twin pairs and is committed unchanged. Ahmed writes the pairs before looking at any metric output.
- Metric output is not gated: trust in the results comes from the self-match test and the outside review. Reports may show per-player metric values.
- Q28: A league-season joins the Pool on the first Monday job after its last scheduled match. Shortened seasons count as completed. The site shows the date of the last data update.
- While on the stand-in source, test fixtures are small real samples cut from the stand-in files (real rows, never invented). Live Understat recordings replace them when Understat returns. This also covers Q26's Build seam and Q30's examples, except the real 404, which waits for live Understat. No invented or hand-written fixture data.
- Q29: Two inputs fall outside the fixture rule because they are not Understat data. PASS, WEAK and FAIL bands are tested with plain rates. Connection failures and retries are simulated as no response at all, while real 404s are recorded. The site smoke test uses Build output from STEP 0 recordings.
- Q30: STEP 0 records real examples of a mid-season league move, `Sub` appearances, an own goal, a player under 900 minutes, a current-season player and a real 404. If a case cannot be found on Understat, the ticket reports it and that test is left out. It is never invented.
