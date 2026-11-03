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
3. Face validity: Ahmed's pre-registered pairs in config/face_validity_pairs.yaml.
4. Outside model reviews code and results.
5. The winning distance method = highest self-match rate that also passes face validity.

## Online
- GitHub Actions every Monday → one JSON per league-season → Vercel static site.
- Data stays in the private repo.

## Code
- pipeline (ingest, profiles, twins, build) and web. DDD terms: PlayerSeason, MetricProfile, PeerGroup, TwinMatch.
- Allowed libraries: understatapi, pandas, numpy, scipy, scikit-learn, pyyaml, pytest.

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
- Q12: If no method passes, the site does not launch. We revisit the metrics and do not lower the bar.
- Q19: The PASS, WEAK and FAIL bands apply to the later-season rate, judged on the point estimate. A confidence interval is shown beside it.
- Q20: The Basketball method uses the same 10 shrunk metrics and replaces only the z-score and clip step with percentiles. It appears in the validation report, not on the public site.
- Q21: The stability test is report-only, with no pass or fail. Any metric whose removal changes the rankings most is flagged for the outside review.
- Q22: The outside review is a non-Claude model on a free tier, such as Gemini. It sees code and results, never raw Understat data. It runs once, after validation and before launch, in addition to the evaluator skill.

### Data source
- Q13: `understatapi` goes through vetting steps 1–5 in `~/sandbox`. No other library is considered unless it fails. It sits behind one adapter that adds the 2-second delay and retries.
- Q14: The backfill fetches by player, if STEP 0 proves on a sample that it matches the match data. Match-level fetching is the fallback.
- Q15: Shot shares, npxG per shot and shots per 90 all use non-penalty shots with own goals excluded.
- Q16: STEP 0 calibrates the box boundaries from real shot data and saves them as named constants. Starting estimates: X ≥ 0.8275 inside the box, X ≥ 0.9425 six-yard box. A heatmap checks them, and the Y limits are checked the same way.
- Q17: The six positions stay as written. STEP 0 counts and lists who `ML`/`MR` excludes in a one-season sample, and Ahmed decides from that list.
- Q18: If Understat's terms are silent or unreadable, the site launches with derived values only, a visible Understat credit and link, no ads, and a takedown contact. If the terms prohibit it, the site stays private.

### Stand-in source (while understat.com is down)
These also override earlier decisions where they differ.
- Pool seasons are 2017/18-2023/24, from worldfootballR shot files + FBref positions and minutes. Extend to 2014/15 from live Understat when it returns.
- Q10 split: choose the method on 2017/18-2021/22. Report PASS, WEAK or FAIL on the 2022/23 and 2023/24 transitions.
- Position source: FBref per-match Pos. Compare with Understat positions when the "Understat is back" issue opens.
- Multi-position rows: count as attacking if any label is FW, LW, RW or AM.
- LM/RM: decided by Ahmed from the names list after the pairs are committed.
- Position rule: a match row is "attacking" if any Pos label is FW, LW, RW or AM, else "other". Sub appearances ignored (Q5). A PlayerSeason joins the Pool if attacking minutes > other minutes.
- The 6 codes are display-only: show the most frequent first-listed attacking label. Position is never used in distance.

### Site and code
- Q23: The build precomputes everything, including both twin lists (all leagues and same league) and closeness percentiles. The site is plain static HTML and JS with inline SVG, no framework, and no distance maths in the browser. Two files join the per-league-season JSON: a name index and the map points.
- Q24: One context, `twin/`: `domain/` (profiles, twins), `application/` (build), `infrastructure/understat/` (ingest, behind the anti-corruption layer), `interface/web/` (site). Plus `VISION.md` and `CONTEXT_MAP.md`.
- Q25: Raw data is gzipped files committed to the private repo. The Monday job fails and keeps the last good site if any league-season's player count or minutes drop, or any request returns 404.
- Q26: All tests go through three seams: Build (recorded Understat data in, public site files out), Understat adapter (recorded responses and errors in, records or a failure out) and Validation report (Pool and pairs file in, PASS, WEAK or FAIL for each method out). The site gets one browser smoke test against a small fixture.
- Q27: The pairs rule is literal and includes tests on made-up data. Every ticket touching distance is blocked by a ticket assigned to Ahmed. The Validation report refuses to run unless the file has 12 twin pairs and 5 not-twin pairs and is committed unchanged. Ahmed writes the pairs before looking at any metric output.
- Metric output is gated like distance code: the "Public MetricProfiles" ticket is also blocked by the pairs ticket, because Ahmed's pairs must be committed before Ahmed can see any metric output. This replaces the Q27 note that z-scores can be built first. STEP 0 reports show no per-player metric values until then.
- Q28: A league-season joins the Pool on the first Monday job after its last scheduled match. Shortened seasons count as completed. The site shows the date of the last data update.
- All test fixtures must be real Understat responses recorded during STEP 0. No invented or hand-written fixture data.
- Q29: Three inputs fall outside the fixture rule because they are not Understat data. PASS, WEAK and FAIL bands are tested with plain rates. Connection failures and retries are simulated as no response at all, while real 404s are recorded. The pairs file refusal is tested with empty or wrong-count files that name no players. The site smoke test uses Build output from STEP 0 recordings.
- Q30: STEP 0 records real examples of a mid-season league move, `Sub` appearances, an own goal, a player under 900 minutes, a current-season player and a real 404. If a case cannot be found on Understat, the ticket reports it and that test is left out. It is never invented.
