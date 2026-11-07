# Claim Check design (grill record)

Status: grill finished 7 Nov 2026 (Q1-Q20, defaults D1-D9). /to-spec ran 7 Nov 2026: ADRs 0001-0003 are written (`docs/adr/`), the shot minimum is measured ("Shot minimum measurement"), word map v1 is drafted (`docs/specs/claim-check-wordmap-v1-draft.md`, DRAFT, NOT FROZEN), and the spec is below ("Spec"). /to-tickets ran the same day, see "Tickets".

A number here is either MEASURED (with the command or file that shows it) or tagged `NOT RUN`.

## Owner input (Ahmed, 7 Nov 2026)

These are fixed. Changing one needs Ahmed.

- Claim Check is a new bounded context beside Twin. It reuses the loader, the per-90 maths and the peer percentiles. It must not change Twin code.
- Input: a typed claim first. Later: headlines from free RSS feeds. No scraping of paywalled or terms-restricted sites.
- The LLM does two jobs only: it parses the claim into a fixed ClaimQuery (subject, metric, window, peer group), and it writes the final 2 lines from numbers it is given. Deterministic code computes every number.
- Every vague word maps to a fixed, written threshold before any check. Example: "elite" = top 10% of the peer group.
- 4 verdicts: Supported, Mixed, Not supported, Can't check with this data.
- Stack: LangGraph, Groq Llama-3, LangFuse traces for every step.
- Data: the stand-in source, 2017/18-2023/24, now. Live Understat later.
- Test claims: "Haaland is an elite finisher", "Arsenal play defensive football", "Rice spends most of his time in his own half" (expected: Can't check with this data).

## Facts from the code and data

Found by reading the repo on `main` at `d36edbd`, 7 Nov 2026. Not decisions.

- **What the stand-in holds.** MEASURED by reading the parquet columns.
  - Shot rows (`*_shot_data.parquet`): match, date, player, Understat id, home team, away team, which side shot (`h_a`), X, Y, xG, situation, shot type, last action, result. Every shot carries both teams, so team xG for and against, per match, can be summed from shot rows.
  - Season totals (`understat_xg_data.parquet`): minutes, goals, assists, shots, key passes, xA, npxG, xG buildup, per player, team, league and season.
  - FBref positions (`*_M_1st_positions.parquet`): every player's minutes and listed position per match, all positions, defenders included.
  - FBref match summaries: goal, card and substitution events with player names. No locations.
  - Not held anywhere: PPDA, deep completions, touches, passes, possession, any event location other than shots.
- **Seasons.** FBref files run to 2025/26 (`Season_End_Year` up to 2026), but the plan fixes the stand-in window at 2017/18-2023/24 (`docs/phase-1-plan.md:102`). Claim Check uses the same window.
- **Test players in the stand-in.** MEASURED from the FBref position files: Haaland has Dortmund 2019/20 (1,063 min), 2020/21 (2,407), 2021/22 (1,911), and Manchester City 2022/23 (2,769), 2023/24 (2,552). Rice has West Ham 2017/18-2022/23 and Arsenal 2023/24 (3,225 min).
- **What Twin code can be reused without change.**
  - `twin.domain.records`: PlayerSeason (every player, all positions), Shot, LoadedSource, the Source interface.
  - `twin.domain.twins.percentiles`: mid-rank percentiles within one group.
  - `twin.domain.profiles.raw_metrics` and `counts_for_metrics`: per-90 values and the non-penalty, no-own-goal shot filter.
  - `twin.domain.pool.in_pool` covers forwards and attacking midfielders only. A Twin PeerGroup is that Pool's league-season. Claim Check needs a Reference group rule of its own for other positions and for teams.
- **Glossary.** The repo has one `GLOSSARY.md` and no `GLOSSARY-MAP.md`. The scope lock allows no new files, so Claim Check terms go in a Claim Check section of the root `GLOSSARY.md`. ADR-grade decisions are recorded here, because `docs/adr/` is outside the scope lock.

## Grill answers

One row per answer, in the order given.

| Q | Question | Answer (Ahmed) |
|---|---|---|
| Q1 | What can a claim be about? | Player, team and league, for now. League claims ("Serie A is a defensive league") use the same shot rows as team claims: goals and xG per match, compared across the 5 leagues. Match and manager claims are out: verdict Can't check with this data, reason "subject type not covered". A single match is too noisy, and the data ends in 2023/24, so current headlines can't be checked anyway. There's no manager tenure data. |
| Q2 | Which seasons does a claim cover when it names none? | Present tense with no season: the last 3 seasons in the data, 2021/22-2023/24. Past tense with no season: every season in the window, 2017/18-2023/24. A named season or range: exactly that, cut to the window. A season outside the window: Can't check with this data, reason "season not in data". Every verdict shows the seasons it used, e.g. "Based on 2021/22-2023/24 · Data to 2023/24". A present-tense verdict also shows "Our data ends in 2023/24. This verdict may not match the current season." For noisy metrics such as finishing, the main verdict pools every shot across the window's seasons, and each season is shown on its own as context only. The catalogue says which metrics are pooled. |
| Q3 | Which player claim types are in the catalogue? | The 11 rows in "Claim-type catalogue, players". Availability covers only "ever-present" and "regular starter". "Injury-prone" is Can't check, reason "no injury data", because missed minutes can mean rotation, form or a ban. Aerial threat uses headed shots per 90 and headed npxG per 90 (attacking headers only). Header share is context only. "Finishing from distance" is added. Chance creation's main metric is xA per 90. Key passes per 90 is context only (correlation 0.815, measured in #30 Part A). Dribbling and the listed items are Can't check. |
| Q4 | Which team and league claim types are in the catalogue? | The 8 team rows and 3 league rows in "Teams" and "Leagues". "Game openness" is added: total npxG per match in the team's games. PPDA, pressing and deep completions are a later option tied to live Understat. Results and points stay out. **Ambiguity rule:** when a word fits more than one Claim type ("defensive" = Defence or Game openness), the parser never picks one silently. The check runs every type the word fits, and the Verdict shows each one with its meaning, e.g. "If 'defensive' means they concede little: Supported. If it means their games have few chances: Not supported." The word-to-types map is in "Ambiguous words". |
| Q5 | Who maps a word to its Claim types? | The LLM only extracts, into the fixed Extraction shape below. A versioned word map in code decides Claim types, metrics and thresholds. An unmapped word gives Can't check, reason "claim word not in catalogue", and is logged in LangFuse. **Polarity:** "affirmed" or "negated". For a negated Claim, code swaps Supported and Not supported. Mixed and Can't check stay as they are. **Name resolution:** a name matching more than one player or team gives Can't check, reason "subject is ambiguous", with the matches listed. Code never picks one. **Claim form:** "absolute" or "comparison" ("Saka creates more than Foden"), with up to 2 subjects. Comparison may be a later build step, but its shape is fixed now. **Word matching:** case-insensitive, handles simple variants (plural, "-ing"), and the map holds phrases ("deadly in front of goal"). The LLM copies words verbatim and never paraphrases. **Test set:** two parts. Extraction tests (Claim text → Extraction) run against the LLM. Verdict tests (Extraction → Verdict) run as pure code. |
| Q6 | What are the level words and their thresholds? | The level scale in "Word-to-threshold rules", including "good" at ≥ 60th and a positive claim-type word with no level word at ≥ 75th. "Decent", "underrated" and "overrated" are Can't check. Majority words stay out for now. Every Verdict shows the threshold and the real value, e.g. "Elite = top 10% of the peer group. Haaland: 94th percentile." A value within 5 percentile points of its threshold is marked borderline (the Mixed question decides what that does). League Claims use ranks among the 5 leagues, not percentiles. The scale is a versioned table in code, like the word map, and every Verdict states the version it used. |
| Q7 | Who is in the peer group? | The defaults, the Line table and the `peers_named` field (now `reference_named`, Q8) in "Reference groups". The subject's Line is the one with the most minutes across the Window, and a tie goes to the latest season. Minimum peer group: 30 peers for players, 10 for teams. Below that, Can't check, reason "peer group too small". A Pooled metric needs at least 40 non-penalty shots in the Window, for the subject and for every peer. This is a starting value with no source: measure the distribution in /to-spec and propose a final value. A subject below it gets Can't check, reason "too few shots". A peer below it is left out. A team peer needs at least 1 full season in the Window. Promoted and relegated teams count only for their seasons in that league. Every Verdict states its peer group in plain words. |
| Q8 | What do we call Claim Check's peer group? | **Reference group.** PeerGroup stays Twin's word only. The ClaimQuery field is `reference_group` and the Extraction field is `reference_named`. "Peer group" is on Reference group's Avoid list. Readers still see plain words on a Verdict ("vs forwards in the top 5 leagues..."). |
| Q9 | When is a Verdict Supported, Mixed or Not supported? | The strict rule in "Verdict rule". Supported needs every test to meet its threshold, Not supported needs every test to miss, and everything else is Mixed. Skipped seasons (< 900 minutes) are shown, not counted as misses. **Borderline is now a bootstrap interval, not a fixed 5-point band.** Resample the subject's matches (per-season metrics) or shots (Pooled metrics) 1,000 times with a fixed seed, recompute the percentile against the fixed Reference group, and take the 80% interval. A test meets if the whole interval clears the threshold, misses if the whole interval misses, and is borderline if the interval crosses it. Every Verdict shows the interval, e.g. "Haaland: 94th percentile (range 91st-97th)". A Mixed Verdict states why in one line, e.g. "2 of 3 seasons meet the threshold" or "the range crosses the line". The Q6 borderline rule points here. |
| Q10 | What does a test do with no per-match rows to resample? | On the stand-in, Chance creation and Build-up use the fixed 5-point band from Q6. The Verdict always says "Range not available: this metric has season totals only.", and a verdict test checks that the label appears. When live Understat per-match xA and xG buildup arrive (#15), these metrics switch to the bootstrap with no rule change, and the method version on the Verdict changes. |
| Q11 | How does Claim Check get match-level rows without changing Twin code? | Claim Check's own adapter calls the stand-in join functions read-only and builds PlayerMatch and TeamMatch records. Twin code stays untouched. Claim Check is a Conformist to Twin's stand-in join, recorded in `CONTEXT_MAP.md`. **Pin 1:** 315,073 joined shots, and `scripts/measure_rule3.py` still prints both pinned Pool lines. **Pin 2:** per-match minutes summed per PlayerSeason equal Twin's season minutes, for every Pool PlayerSeason. **Gate:** no Claim Check Verdict is published until the retrospective on the #17 join findings is done. |
| Q12 | What is the fail-safe for missing data or a failed step? | The 11-step ordered reason list, the held-for-review rule, "faults are never Verdicts", and Verdicts on the remaining seasons, all in "Fail-safe for missing data". **Coverage line:** every Verdict shows how many Window seasons it used, e.g. "Based on 1 of 3 seasons: 2021/22 held for review, 2022/23 too few minutes." If only 1 season remains in a 3-season Window, the Verdict also says "Thin evidence". **Groq:** one retry on a timeout or a bad response, then stop with an error. **LangFuse:** if tracing fails, the run stops. No untraced Verdict is ever shown. The Thin evidence rule was generalised in Q13. |
| Q13 | When is evidence thin in a Window that isn't 3 seasons? | Thin evidence means fewer than half the Window's seasons remain. A fully used 1-season Window is never thin. The same count applies to Pooled metrics (the seasons that contributed shots) and to teams. |
| Q14 | How is the LLM's 2-line summary kept honest? | Code renders every fact. The LLM writes only the 2 Summary lines, and a code guard checks them. The guard result is a LangFuse span. Guard check 5 is added: a versioned blocked-word list of hedges that change a Verdict's meaning ("arguably", "somewhat", "fairly", "partly", "kind of", "sort of"). Any match fails the guard. **After one retry, a failed guard shows a fixed template sentence** that code writes from the same numbers, e.g. "<Subject>, <Claim type>: <Verdict>. <value> vs <Reference group line>.", and LangFuse marks it "template fallback". A Groq outage still stops the run (Q12). Only a failed guard uses the template. |
| Q15 | What is in the test set, and how are expected Verdicts fixed? | The pre-registration rule, the 3-part structure, one Can't check claim per reason, one Fault case per fault type, and real claims 1-6, all in "Test set". Claims 1-6 were written by the agent from memory, so before the first run a non-Claude model reviews each expected Verdict and its Why line. Its verdict is recorded in the spec, and disagreements go to Ahmed. Claim 7 is report-only: the test shows the result with no pass or fail, unless Ahmed adds an expected Verdict before the run. Claim 1's Why line says the Window crosses leagues, so it also tests cross-league pooling. |
| Q16 | How does an outside model review the Verdicts? | The two passes in "Outside review of verdicts". Pass A (Consistency) has a 100% target. Pass B (Blind plausibility) reports agreement against a chance baseline, with no pass mark. Both re-run on every word-map, level-scale or method change. **Claim set:** Part 1 of the test set plus 30 real claims collected by a fixed rule, written by neither Ahmed nor the agent: the first 30 checkable player, team or league claims in BBC Sport football RSS headlines, over a fixed date range set before collection. Each keeps its source link and date. The rule and date range are recorded here before collecting. **Reviewer:** Gemini, free tier via Google AI Studio. The model name and version are recorded on every review. The API key is stored with a hidden-input command and never pasted in chat. **Pass B** tells the reviewer the Window in plain words and to judge only those seasons, not the current season. The BBC source and date-order rule were replaced in Q17. |
| Q17 | What exactly is the collection rule for the 30 headline claims? | "Checkable" means a claim about how a named player, team or league plays or performs. Gemini judges it with a fixed recorded prompt, not our word map. All 30 go through Claim Check, and the report gives the coverage rate. Ahmed spot-checks 10 yeses and 10 nos. **Source:** the Guardian Open Platform Content API (free non-commercial developer key), football section, headline and standfirst only. The article body is never read. **Date range:** 2021-08-01 to 2024-05-31, inside the data window. **Sampling:** headlines are drawn in random order with a fixed recorded seed, and the set is the first 30 that Gemini marks yes. Date order is not used, because it would bunch the claims in 2021. **Terms:** before collecting, read the Guardian's API terms and confirm in the spec that this use is allowed on the free key. If that is not clear, stop and report. **Key:** stored with a hidden-input command, never pasted in chat. BBC Sport RSS stays a later option for live input, after its current terms are checked. |
| Q18 | Where is a Claim typed and a Verdict shown first? | A private CLI, `claim-check "<claim>"`. It prints the rendered Verdict and writes the Verdict as JSON under `build/private/claim_check/`. A web front end is a later option, after the publishing gate. |
| Q19 | Should the ADR-grade decisions get ADRs? | Yes. ADRs 0001-0003 are written at the start of the /to-spec session: the LLM only extracts and the word map decides (Q5), the Conformist to Twin's stand-in join (Q11), and the strict verdict rule with a bootstrap interval (Q9). Until then they live only in this spec, because the scope lock keeps them out of `docs/adr/`. |
| Q20 | Who writes word map v1, and what freezes it? | The agent drafts word map v1 and level scale v1 in /to-spec. Gemini reviews the draft first and flags any line where a word's meaning or threshold looks wrong to a football reader. Ahmed approves the full map in one pass, checking flagged lines closely. His approval freezes v1, and every Verdict cites v1 from then on. |
| D1-D9 | Agent defaults | Accepted by Ahmed as recorded, 7 Nov 2026. |

### Later options

- **Match subjects** (from Q1): out for now because one match is too noisy and the stand-in ends in 2023/24. Could come back with live Understat.
- **Manager subjects** (from Q1): out because there's no tenure data. Would need a source of manager-to-team-to-date spans.
- **BBC Sport RSS for live input** (from Q17): a later option, after its current terms are checked. A fetch of the feed and its terms page was blocked from the grill session on 7 Nov 2026 (`NOT RUN`). RSS holds current items only, with no archive.
- **PPDA, pressing, deep completions** (from Q4): with live Understat team pages (#15).
- **Web front end** (from Q18): after the publishing gate. It would read the Verdict JSON.
- **Comparison Claims** (from Q5): the Extraction shape holds them, and the verdict rule is still to design.

## Agent defaults (owner may change)

Decided by the agent on 7 Nov 2026, where the grill had a clear default. Each is "Agent default, owner may change". Ahmed accepted D1-D9 as recorded.

| Ref | Default | Reason |
|---|---|---|
| D1 | A per-season test ranks the subject against that season's Reference group: peers with ≥ 900 minutes in that season, on the subject's Line. A Pooled test ranks against peers pooled over the same Window. | Each season is judged against the players who played it |
| D2 | A peer's Line uses the same rule as the subject's: most minutes across the Window, a tie to the latest season. | One rule for everyone in the Reference group |
| D3 | For a metric where less is the Claim's direction (npxG against for "solid", total npxG for "defensive football"), the percentile is taken in the Claim's direction, and the Verdict says so in plain words, e.g. "concedes less than 96% of EPL teams". So "defensive" as Defence needs ≥ 75th for conceding little, and "defensive football" as Game openness needs ≤ 25th of total npxG. | The level scale reads one way, and readers see plain words |
| D4 | Team and league tests bootstrap by resampling TeamMatches, the same as player per-season tests. A league rank's interval is the rank range over the 1,000 resamples. | One interval method across Subjects |
| D5 | A team's "full season" is every league match of that season in the data. | Matches the promoted and relegated rule in Q7 |
| D6 | The Groq model is pinned to one exact model id, recorded on every Verdict and LangFuse trace. Changing it re-runs the Extraction tests and counts as a method version change, which triggers re-review (Q16). | The model may change, but the change is never silent |
| D7 | The LangGraph graph has one node per step: extract, resolve subjects, map words, build ClaimQuery, compute tests, decide Verdict, write Summary lines, guard, render. Each node is one LangFuse span named with the glossary word. Every node except extract and write Summary lines is deterministic code. | Owner input: LangFuse traces every step, named in the Ubiquitous Language |
| D8 | Claim Check code lives in `claim_check/` with `domain/`, `application/`, `infrastructure/` and `interface/` folders. The domain imports no LangGraph, Groq, LangFuse or pandas, and its tests run with no network. | The DDD build rules |
| D9 | Claim 1's expected Verdict allows two values ("Not supported or Mixed"). Either one passes, and any other Verdict fails. | Pre-registered from memory, so a range is honest |

## Claim-type catalogue

Sources: **shots** = Understat shot rows, **totals** = Understat season totals, **FBref** = FBref position and minutes files. "Pooled" means the main Verdict counts every shot (or minute) in the Window as one sample (Q2). Context metrics are shown, but they never set the Verdict.

### Players (Q3)

| Claim type | Example words | Main metric | Context only | Source | Pooled |
|---|---|---|---|---|---|
| Finishing | "clinical", "elite finisher", "wasteful" | (non-penalty goals − npxG) per non-penalty shot | each season alone | shots | yes |
| Finishing from distance | "scores from distance", "great from range" | (npG − npxG) per shot, on shots from outside the box | each season alone | shots | yes |
| Shot volume | "shoots a lot", "shy" | non-penalty shots per 90 | | shots + FBref minutes | no |
| Shot quality | "gets into great positions", "takes bad shots" | npxG per shot | each season alone | shots | yes |
| Goal threat | "dangerous", "goal threat" | npxG per 90 | | shots + FBref minutes | no |
| Goalscoring | "prolific", "scores a lot" | non-penalty goals per 90 | | shots + FBref minutes | no |
| Chance creation | "creative", "creator" | xA per 90 | key passes per 90 | totals | no |
| Build-up | "involved in build-up" | xG buildup per 90 | | totals | no |
| Long shots | "shoots from distance" | share of shots from outside the box | each season alone | shots | yes |
| Aerial threat | "good in the air" (attacking headers only) | headed shots per 90, and headed npxG per 90 | header share of shots | shots + FBref minutes | no |
| Availability | "ever-present", "regular starter" | share of league minutes played | | FBref | no |

All shot metrics use Twin's filter: non-penalty shots, own goals excluded (`counts_for_metrics`).

**Can't check with this data, players:** "injury-prone" (reason "no injury data": missed minutes can mean rotation, form or a ban), passing range or accuracy, defending, tackling, pressing, work rate, pace, dribbling (the last action before a shot being a take-on does not measure it), where a player spends time on the pitch, leadership, off-ball movement. Reason "metric not in data" unless one is given.

### Teams (Q4)

Every team metric is summed per match from shot rows. Each shot row names both teams and which side shot, so xG against is the opponent's xG. Per-match values compare fairly across 18- and 20-team leagues.

| Claim type | Example words | Main metric | Context only | Source | Pooled |
|---|---|---|---|---|---|
| Attack | "attacking", "free-scoring", "blunt" | npxG for per match | goals per match, shots per match | shots | no |
| Defence | "solid", "tight at the back", "leaky" | npxG against per match | goals against per match, shots against per match | shots | no |
| Game openness | "defensive football", "boring", "park the bus", "open", "end-to-end" | total npxG per match in the team's games (both teams) | npxG for per match, npxG against per match | shots | no |
| Chances conceded | "give up big chances" | npxG per shot against | | shots | yes |
| Dominance | "dominant", "control games" | npxG difference per match | | shots | no |
| Team finishing | "clinical", "wasteful" | (npG − npxG) per shot | | shots | yes |
| Set-piece threat | "dangerous from set pieces" | set-piece xG for per match (FromCorner + SetPiece + DirectFreekick) | share of xG from set pieces | shots | no |
| Set-piece defence | "weak at set pieces" | set-piece xG against per match | | shots | no |

### Leagues (Q4)

Compared across the 5 leagues, over the same seasons.

| Claim type | Example words | Main metric | Context only | Source |
|---|---|---|---|---|
| Open or high-scoring | "open", "high-scoring", "defensive league" | npxG per match (both teams) | goals per match, shots per match | shots |
| Set-piece league | "set-piece heavy" | share of xG from set pieces | | shots |
| Long-shot league | "lots of long shots" | outside-box share of shots | | shots |

**Can't check with this data, teams and leagues:** PPDA, pressing and deep completions (reason "metric not in data"; later option, since live Understat team pages hold them, #15). Possession, passing style, "direct", "long-ball", high line, formation, counter-attacking (shot situations are only OpenPlay, FromCorner, SetPiece, DirectFreekick and Penalty, with no fast-break tag; MEASURED on `epl_shot_data.parquet`). Results and points stay out (own-goal attribution in shot rows is `NOT RUN`, and "wins games" claims are about results, not style).

### Ambiguous words (Q4)

When a word fits more than one Claim type, every Reading is checked and shown with its meaning. The parser never picks one.

| Subject | Word | Readings (Claim types) | Shown meaning |
|---|---|---|---|
| Team | "defensive" | Defence; Game openness | "they concede little"; "their games have few chances" |

## The Extraction and the word map (Q5)

The LLM's only parsing job is to fill this shape. Every value except `form`, `kind`, `polarity` and `tense` is copied verbatim from the Claim.

```json
{
  "form": "absolute | comparison",
  "subjects": [{"name": "Haaland", "kind": "player | team | league"}],
  "claim_words": ["elite", "finisher"],
  "comparison_words": null,
  "polarity": "affirmed | negated",
  "tense": "present | past",
  "seasons_named": null,
  "reference_named": null
}
```

- `reference_named` (added in Q7 as `peers_named`, renamed in Q8) is the verbatim Reference group phrase ("in the Premier League", "for a midfielder"), and is null when the Claim names none. Code maps it to a fixed Reference group rule. A phrase it can't map gives Can't check, reason "peer group not in catalogue".

- `subjects` holds 1 item for an absolute Claim and 2 for a comparison.
- `comparison_words` is the verbatim comparing phrase ("more than"), and is null for an absolute Claim.
- `seasons_named` is the verbatim season text ("in 2022/23"), and is null when the Claim names none.

Code then builds the ClaimQuery:
1. It resolves each subject name against the data. No match gives Can't check, reason "subject not in data". More than one match gives "subject is ambiguous", with the matches listed.
2. It looks up the claim words in the versioned word map. Matching is case-insensitive, handles plural and "-ing" variants, and also matches phrases. The map gives each word's Readings, their Main metrics and the threshold. No entry gives Can't check, reason "claim word not in catalogue", and the word is logged in LangFuse.
3. It sets the Window from the tense and `seasons_named` (Q2).
4. It applies polarity last. A negated Claim swaps Supported and Not supported.

An Extraction that fails the shape gives Can't check, reason "could not read the claim". Comparison Claims may come in a later build step (Q5), but the shape above already holds them.

## Reference groups (Q7, named in Q8)

Twin's PeerGroup (one league-season of Pool attackers) is not used. Claim Check needs every position, and Windows that cross leagues.

The ClaimQuery field is `reference_group` (Q8). PeerGroup stays Twin's word only. A reason or plain-words line shown to readers may still say "peer group" or "vs forwards in the top 5 leagues".

| Subject | Default Reference group | Minimum size |
|---|---|---|
| Player | every PlayerSeason in all 5 leagues, in the Window's seasons, with ≥ 900 minutes in that season, on the same Line as the subject | 30 peers |
| Team | every team in the same league over the same seasons, with at least 1 full season in the Window. Promoted and relegated teams count only for their seasons in that league | 10 peers |
| League | the 5 leagues | 5 |

- Below the minimum size: Can't check, reason "peer group too small".
- **Line** comes from Primary position. The subject's Line is the one with the most minutes across the Window, and a tie goes to the latest season.

| Line | FBref positions |
|---|---|
| Forward | FW |
| Wide | LW, RW, LM, RM |
| Central AM | AM |
| Central midfielder | CM, DM, MF |
| Full-back | LB, RB, WB |
| Centre-back | CB, DF |
| Goalkeeper | GK. Every catalogue Claim on a goalkeeper is Can't check, reason "metric not in data". |

Forward, Wide and Central AM match #30's Role group names. Line adds LM and RM to Wide, because Line covers every position.

- **Pooled metrics:** each peer's value is pooled over the same Window. Subject and peers each need at least 40 non-penalty shots in the Window. This starting value has no source: /to-spec measures the distribution and proposes a final value. A subject below it gets Can't check, reason "too few shots". A peer below it is left out of the peer group.
- **Named peers** (`reference_named`) replace the default with a fixed Reference group rule from the word map.
- **Shown on every Verdict, in plain words**, e.g. "vs forwards in the top 5 leagues, 2021/22-2023/24, 900+ minutes per season".

## Word-to-threshold rules

### Level scale, players and teams (Q6)

A threshold is a percentile of the Main metric within the Reference group. The percentiles are Twin's mid-rank `percentiles`, unchanged. For a negative word the direction flips: a low value meets it.

| Level words | Threshold |
|---|---|
| "the best", "the worst" | rank 1 (or last) in the Reference group |
| "elite", "world-class", "one of the best" | ≥ 90th percentile (top 10%) |
| "great", "excellent", "very good", "top" | ≥ 75th |
| "good" | ≥ 60th |
| "above average" | > 50th |
| "average" | 25th-75th |
| "below average" | < 50th |
| "poor", "bad" | ≤ 25th |
| "terrible", "one of the worst" | ≤ 10th |
| no level word, positive claim-type word ("clinical", "creative", "prolific", "solid") | ≥ 75th |
| no level word, negative claim-type word ("wasteful", "leaky", "blunt", "boring") | ≤ 25th |

- **Can't check, reason "claim word not in catalogue":** "decent", "underrated", "overrated". "Overrated" compares with reputation, and there's no data for that.
- **Majority words** ("most of his time") are out for now. They are a share threshold, not a percentile, and the only Claim type they fit (the Rice claim) is already Can't check.
- **Borderline:** set in Q6 as a 5-point band, replaced in Q9 by the bootstrap interval in "Verdict rule".
- **Shown on every Verdict:** the threshold and the real value, e.g. "Elite = top 10% of the peer group. Haaland: 94th percentile."
- **Versioned:** the level scale is a versioned table in code, like the word map. Every Verdict states the scale and word-map versions it used.

### League Claims (Q6)

League Claims use ranks among the 5 leagues, not percentiles.

| Level words | Threshold |
|---|---|
| "the most", "the least" | rank 1, or rank 5 |
| "one of the most", "one of the least" | rank 1-2, or rank 4-5 |
| "more than <league>" | a direct comparison of the two leagues |

Any other level word on a league Claim is Can't check, reason "level word does not fit a 5-league comparison".

## Verdict rule (Q9)

Ambiguous words get one Verdict per Reading (Q4). Within one Reading, a Verdict rests on one or more **tests**:
- a Pooled metric: 1 test, the pooled value
- a per-season metric: 1 test per season the subject qualifies in
- a Claim type with 2 Main metrics (Aerial threat): one test per metric

**Each test's interval.** Resample the subject's matches (per-season metrics) or shots (Pooled metrics) 1,000 times with a fixed seed. Recompute the subject's percentile each time against the fixed Reference group, and take the 80% interval.
- **meets**: the whole interval clears the threshold
- **misses**: the whole interval misses it
- **borderline**: the interval crosses it

| Tests | Verdict |
|---|---|
| every test meets | Supported |
| every test misses | Not supported |
| anything else: any borderline, or a mix of meets and misses | Mixed |

Polarity is applied after this (Q5).

- A season where the subject has < 900 minutes is skipped. It is shown as "not enough minutes", never counted as a miss.
- **Shown on every Verdict:** each test's percentile and interval, e.g. "Haaland: 94th percentile (range 91st-97th)".
- **A Mixed Verdict states why in one line**, e.g. "2 of 3 seasons meet the threshold" or "the range crosses the line".
- **Season-totals fallback (Q10).** Chance creation (xA per 90) and Build-up (xG buildup per 90) come from one season-totals row with no per-match split, and the stand-in shot rows don't name the passer. On the stand-in these two use a fixed 5-point band: within 5 percentile points of the threshold is borderline. The Verdict always says "Range not available: this metric has season totals only." When live Understat per-match xA and xG buildup arrive (#15), they switch to the bootstrap with no rule change, and the method version on the Verdict changes.
- **Why strict:** a majority rule would give fewer Mixed verdicts, but it lets a player who was elite in 1 season of 3 come out Supported.

## Match-level data (Q11)

Twin's `LoadedSource` is not enough on its own. Twin's `Shot` has no match id, team or opponent, and `PlayerSeason` has season minutes only. Claim Check's own stand-in adapter calls the join functions in `twin/infrastructure/standin/player_join.py` read-only (`load_shots`, `with_side`, `link_matches`, `load_positions`, the final rule-3 links). It builds two record types:

- **PlayerMatch**: player (FBref id), match, minutes, position, the player's Shots in that match.
- **TeamMatch**: team, opponent, match, npxG for and against, set-piece xG for and against, shots for and against.

The relationship is **Conformist**: Claim Check takes the join as it is and changes no Twin code (`CONTEXT_MAP.md`). With live Understat (#15), the live adapter feeds both contexts.

**Pin tests.** Both run on every build of Claim Check data.
1. Claim Check's joined shot count is 315,073, and `scripts/measure_rule3.py` still prints `Merges off: joined 315073 | Pool 3108 of 3136` and `Merges on: joined 315073 | Pool 3109 of 3137`.
2. Per-match minutes summed per PlayerSeason equal Twin's season minutes, for every Pool PlayerSeason.

**Publishing gate.** No Claim Check Verdict is published until the retrospective on the #17 join findings is done. Until then, every Verdict stays private. Twin's own gate still applies: the stand-in may never publish.

## Team data

Team and league metrics come from TeamMatch records (Q11), summed from shot rows. Every shot row names both teams and the side that shot, so xGA is the opponent's npxG.

- **Held:** npxG for and against, shots for and against, set-piece xG for and against, all per match.
- **Not held:** PPDA, pressing and deep completions. Later option with live Understat team pages (#15). Until then, Can't check, reason "metric not in data".

## Fail-safe for missing data (Q12)

### Can't check reasons, in check order

The first check that fails gives the reason, so each Can't check names exactly one.

1. "could not read the claim": the Extraction fails its shape
2. "subject type not covered": match or manager Claims
3. "subject not in data" or "subject is ambiguous" (the matches are listed)
4. "claim word not in catalogue", "peer group not in catalogue", or "level word does not fit a 5-league comparison"
5. "metric not in data" or "no injury data"
6. "season not in data"
7. "too few minutes": no season in the Window has ≥ 900 minutes
8. "held for review": every season in the Window is a PlayerSeason Twin holds for review
9. "too few shots": a Pooled metric below the shot minimum
10. "season totals missing": xA or xG buildup is None for every season in the Window
11. "peer group too small"

### Rules

- **Held for review comes from Twin.** A held PlayerSeason's shot and per-90 metrics are never used, as in Twin. A held season is skipped and shown as "held for review", and a held peer is left out of the Reference group. Twin's review route stays the only one.
- **Faults are never Verdicts.** A missing, empty or changed stand-in file (Twin's `StandinFileError`), a failed pin test, a Groq or LangFuse outage, or a code error stops the run with an error naming the cause. Can't check always means "the data can't answer this", never "something broke".
- **Groq:** one retry on a timeout or a bad response, then stop with an error.
- **LangFuse:** if tracing fails, the run stops. No untraced Verdict is ever shown.
- **Some seasons skipped:** the Verdict uses the seasons that remain, and lists each skipped season with its reason.
- **Coverage line:** every Verdict shows how many Window seasons it used, e.g. "Based on 1 of 3 seasons: 2021/22 held for review, 2022/23 too few minutes." If fewer than half the Window's seasons remain, the Verdict also says "Thin evidence" (Q13). 1 of 3 is thin, 2 of 3 is not, 3 of 7 is thin, 4 of 7 is not. A fully used 1-season Window is never thin. Pooled metrics count the seasons that contributed shots, and teams count the same way.

## Summary lines and their guard (Q14)

**Code renders every fact:** the Verdict word, threshold, value and interval, the Reference group line, the coverage line, Thin evidence, the season-totals label, the data-end warning, and the word-map, level-scale, method and blocked-word versions.

**The LLM writes only the 2 Summary lines on top**, from a fixed input: the Claim, the Verdict, and the numbers code computed.

**The guard.** Code checks the 2 lines before anything is shown. Any failed check fails the guard.
1. Every number in the text appears in the given numbers, after the same rounding.
2. The Verdict word appears exactly as given, and no other Verdict word appears.
3. The only names are the Claim's Subjects.
4. At most 2 lines and 280 characters.
5. None of the words on the versioned blocked-word list appears. The list holds hedges that change a Verdict's meaning: "arguably", "somewhat", "fairly", "partly", "kind of", "sort of".

**On failure.** The guard's first failure counts as a bad Groq response and gets one retry. If it fails again, code shows a fixed template sentence written from the same numbers: "<Subject>, <Claim type>: <Verdict>. <value> vs <Reference group line>." LangFuse marks the run "template fallback". A Groq outage is a Fault and stops the run (Q12). Only a failed guard uses the template. The guard result is always a LangFuse span.

## Test set (Q15)

**Pre-registration rule.** Every expected Verdict for a real Claim is written down, with a football reason, before the code first runs it. If the computed Verdict differs, it is investigated and the finding recorded. The expected value is never edited to match. Changing it needs Ahmed and a written reason.

**Outside check of the expected Verdicts.** Claims 1-6 were written by the agent from memory. Before the first run, a non-Claude model reviews each expected Verdict and its Why line. Its verdict goes in the "Reviewer" column, and any disagreement goes to Ahmed. Status: `NOT RUN`.

### Part 1: verdict tests on real data

| # | Claim | Readings / Window | Expected Verdict | Why | Reviewer |
|---|---|---|---|---|---|
| 1 | "Haaland is an elite finisher" | Finishing, pooled 2021/22-2023/24, vs Forwards | Not supported or Mixed | His goals roughly match his npxG. His edge is volume, not conversion, and in 2023/24 he scored well below his npxG. The Window crosses leagues (Dortmund 2021/22, Manchester City 2022/23-2023/24), so this also tests cross-league pooling | `NOT RUN` |
| 2 | "Haaland is an elite goalscorer" | Goalscoring, same Window | Supported | npG per 90 near the top of all forwards every season | `NOT RUN` |
| 3 | "Arsenal play defensive football" | Defence; Game openness, EPL 2021/22-2023/24 | Defence: Mixed (2021/22 mid-table xGA). Game openness: Not supported | Low xGA in 2022/23 and 2023/24, but Arsenal create a lot, so their games are not low-chance | `NOT RUN` |
| 4 | "Rice spends most of his time in his own half" | none | Can't check with this data, "metric not in data" | No location data except shots | `NOT RUN` |
| 5 | "Haaland isn't an elite finisher" | as #1, negated | the flip of #1 | Polarity test | `NOT RUN` |
| 6 | "De Bruyne is an elite creator" | Chance creation, 2021/22-2023/24, vs his Line | Supported, with "Range not available: this metric has season totals only." | xA per 90 near the top of the league. Also checks the Q10 label | `NOT RUN` |
| 7 | "Serie A is the most defensive league" | Open or high-scoring, 5-league rank | Report-only: the result is shown with no pass or fail, unless Ahmed adds an expected Verdict before the run | The agent doesn't know this ranking well enough to commit | n/a |

### Part 1b: one Can't check claim per reason, one Fault case per fault type

- One real or synthetic Claim for each of the 11 reasons in "Fail-safe for missing data".
- One case for each fault type: missing file, empty file, changed file, failed pin test, Groq outage, LangFuse outage, code error. Each must stop with an error and never return Can't check.

### Part 2: synthetic verdict tests (pure code)

A fixed Extraction plus fixture numbers, each with its exact expected Verdict built in. Labelled `synthetic` in the test name and a comment, as in the #6 spec, and kept out of `tests/fixtures/`. They cover: meets, misses, borderline, a seasons mix giving Mixed, skipped seasons, Thin evidence, negation, two Readings, the season-totals fallback label, each of the 5 guard checks, and the template fallback.

### Part 3: Extraction tests (against the LLM)

At least claims 1-7, plus negation, comparison, named-season and named-peer variants. Each has an exact expected Extraction JSON, compared field by field.

## Outside review of verdicts (Q16)

The review never self-grades. The reviewer is a model family that builds no part of a Verdict.

**Reviewer.** Gemini, free tier via Google AI Studio. Not Claude, and not Llama, which writes the Summary lines. The model name and version are recorded on every review. The API key is stored with a hidden-input command (e.g. `read -s` into the macOS keychain), never pasted in chat or committed.

**Pass A: Consistency.** The reviewer sees the full rendered Verdict: the Claim, Verdict word, threshold, value and interval, Reference group line, coverage line and Summary lines. It answers two questions: does the Verdict word follow from the numbers shown, and do the Summary lines say anything the numbers don't? Target: 100%. Any "no" is a bug or goes to Ahmed.

**Pass B: Blind plausibility.** The reviewer sees only the Claim, the plain meaning of each Reading, the Window in plain words, and the Reference group in plain words. It is told to judge only those seasons, not the current season. It gives its own Verdict from the same 4 options, plus a confidence. Reported: the agreement rate where the reviewer is confident, against a chance baseline (always picking the most common Verdict), and every disagreement, sent to Ahmed with both sides. There's no pass mark.

**Claim set.** Part 1 of the test set, plus 30 Headline claims collected by the fixed rule below, so neither Ahmed nor the agent picks the exam.

### Headline claim collection rule (Q17), fixed before collecting

- **Source:** the Guardian Open Platform Content API, free non-commercial developer key, football section. Only the headline and the standfirst are read, never the article body.
- **Date range:** 2021-08-01 to 2024-05-31, inside the data window.
- **What counts as checkable:** a headline or standfirst that makes a claim about how a named player, team or league plays or performs. Transfer news, injuries, previews of future matches and plain results do not count. Gemini judges each one yes or no with a fixed prompt, recorded here before collecting. Our word map plays no part, so the set can show gaps in the catalogue.
- **Sampling:** headlines are drawn in random order with a fixed seed, recorded here before collecting. The set is the first 30 that Gemini marks yes. Date order is not used, because it would bunch the claims in 2021.
- **Spot check:** Ahmed checks 10 yeses and 10 nos.
- **Every claim keeps** its source link and date.
- **All 30 go through Claim Check,** Can't check included. The report gives the coverage rate (the share that is not Can't check) as its own number.
- **Terms gate:** before collecting, read the Guardian's own API terms and confirm here that this use is allowed on the free key. If that is not clear, stop and report. Status: `NOT RUN`. A fetch of `open-platform.theguardian.com` was blocked from the grill session on 7 Nov 2026, so the terms are unread.
- **Key:** the Guardian and Gemini keys are stored with a hidden-input command and never pasted in chat or committed.
- **Still to fill before collecting:** the Gemini prompt, the seed, and the terms confirmation.

**When.** Before the publishing gate (Q11), and again on every word-map, level-scale or method version change.

**Where.** A report under `docs/reports/`, at build time.

## Shot minimum measurement (Q7, measured in /to-spec)

**Command** (read-only, run from the repo root on `claim-check-spec`, 7 Nov 2026; the script sits in `/tmp` and writes nothing):

```bash
uv run --no-project --python 3.12 --with-requirements requirements.txt python /tmp/claim-check-measure/shot_minimum.py
```

**What it counts.** For each Window and Line: every player with at least 1 qualifying season (≥ 900 minutes, not held for review) in the Window. Their non-penalty, non-own-goal shots in those seasons (`counts_for_metrics`), summed over the Window. Line comes from start minutes only, as Primary position ignores substitute appearances. The Window Line is the one with the most minutes, and a tie goes to the latest season (D2). The script loads 19,062 PlayerSeasons and 309,961 non-penalty, non-own-goal shots: 315,073 joined shot rows less penalties and own goals. Goalkeepers are left out, because every catalogue Claim on a goalkeeper is Can't check.

**Reading the tables.** "removed by N (left)": how many players fall below N shots, and how many are left. A Reference group needs 30. "<30" marks a Line left with too few. Subjects and peers are the same population, so the count removed is both the subjects who'd get "too few shots" and the peers left out.

#### Window 2017/18-2019/20

| Line | players | median shots | p25 | p75 | removed by 20 (left) | removed by 30 (left) | removed by 40 (left) | removed by 50 (left) | removed by 60 (left) |
|---|---|---|---|---|---|---|---|---|---|
| Forward | 325 | 86 | 44 | 147 | 13 (312) | 39 (286) | 70 (255) | 89 (236) | 116 (209) |
| Wide | 473 | 54 | 29 | 101 | 66 (407) | 123 (350) | 174 (299) | 212 (261) | 257 (216) |
| Central AM | 84 | 54 | 28 | 85 | 9 (75) | 24 (60) | 35 (49) | 40 (44) | 47 (37) |
| Central midfielder | 482 | 33 | 16 | 64 | 156 (326) | 213 (269) | 276 (206) | 320 (162) | 353 (129) |
| Full-back | 474 | 17 | 8 | 34 | 266 (208) | 334 (140) | 372 (102) | 407 (67) | 437 (37) |
| Centre-back | 492 | 17 | 8 | 31 | 273 (219) | 356 (136) | 416 (76) | 451 (41) | 470 (22 <30) |

#### Window 2018/19-2020/21

| Line | players | median shots | p25 | p75 | removed by 20 (left) | removed by 30 (left) | removed by 40 (left) | removed by 50 (left) | removed by 60 (left) |
|---|---|---|---|---|---|---|---|---|---|
| Forward | 335 | 81 | 38 | 143 | 19 (316) | 46 (289) | 88 (247) | 112 (223) | 133 (202) |
| Wide | 431 | 56 | 29 | 102 | 50 (381) | 111 (320) | 158 (273) | 197 (234) | 226 (205) |
| Central AM | 85 | 58 | 27 | 112 | 11 (74) | 24 (61) | 31 (54) | 38 (47) | 45 (40) |
| Central midfielder | 494 | 32 | 16 | 59 | 160 (334) | 230 (264) | 288 (206) | 343 (151) | 370 (124) |
| Full-back | 473 | 16 | 8 | 34 | 263 (210) | 330 (143) | 371 (102) | 411 (62) | 432 (41) |
| Centre-back | 513 | 16 | 8 | 32 | 296 (217) | 368 (145) | 431 (82) | 471 (42) | 489 (24 <30) |

#### Window 2019/20-2021/22

| Line | players | median shots | p25 | p75 | removed by 20 (left) | removed by 30 (left) | removed by 40 (left) | removed by 50 (left) | removed by 60 (left) |
|---|---|---|---|---|---|---|---|---|---|
| Forward | 328 | 78 | 41 | 140 | 15 (313) | 46 (282) | 79 (249) | 108 (220) | 133 (195) |
| Wide | 413 | 58 | 29 | 102 | 51 (362) | 104 (309) | 155 (258) | 189 (224) | 208 (205) |
| Central AM | 96 | 51 | 26 | 97 | 13 (83) | 30 (66) | 38 (58) | 46 (50) | 53 (43) |
| Central midfielder | 485 | 30 | 16 | 57 | 155 (330) | 242 (243) | 296 (189) | 334 (151) | 369 (116) |
| Full-back | 472 | 18 | 10 | 35 | 247 (225) | 321 (151) | 378 (94) | 416 (56) | 430 (42) |
| Centre-back | 528 | 16 | 7 | 31 | 296 (232) | 386 (142) | 450 (78) | 488 (40) | 502 (26 <30) |

#### Window 2020/21-2022/23

| Line | players | median shots | p25 | p75 | removed by 20 (left) | removed by 30 (left) | removed by 40 (left) | removed by 50 (left) | removed by 60 (left) |
|---|---|---|---|---|---|---|---|---|---|
| Forward | 347 | 72 | 39 | 138 | 13 (334) | 49 (298) | 89 (258) | 114 (233) | 141 (206) |
| Wide | 437 | 55 | 28 | 99 | 55 (382) | 115 (322) | 172 (265) | 204 (233) | 228 (209) |
| Central AM | 91 | 50 | 27 | 92 | 11 (80) | 26 (65) | 34 (57) | 44 (47) | 54 (37) |
| Central midfielder | 492 | 31 | 16 | 62 | 163 (329) | 232 (260) | 292 (200) | 329 (163) | 359 (133) |
| Full-back | 470 | 19 | 10 | 35 | 241 (229) | 324 (146) | 366 (104) | 393 (77) | 418 (52) |
| Centre-back | 540 | 16 | 8 | 31 | 311 (229) | 393 (147) | 456 (84) | 491 (49) | 511 (29 <30) |

#### Window 2021/22-2023/24

| Line | players | median shots | p25 | p75 | removed by 20 (left) | removed by 30 (left) | removed by 40 (left) | removed by 50 (left) | removed by 60 (left) |
|---|---|---|---|---|---|---|---|---|---|
| Forward | 350 | 69 | 41 | 132 | 6 (344) | 48 (302) | 86 (264) | 114 (236) | 148 (202) |
| Wide | 431 | 54 | 27 | 102 | 60 (371) | 117 (314) | 163 (268) | 201 (230) | 226 (205) |
| Central AM | 110 | 52 | 29 | 103 | 14 (96) | 29 (81) | 41 (69) | 52 (58) | 59 (51) |
| Central midfielder | 505 | 33 | 16 | 59 | 157 (348) | 229 (276) | 292 (213) | 338 (167) | 380 (125) |
| Full-back | 467 | 21 | 11 | 38 | 224 (243) | 301 (166) | 356 (111) | 394 (73) | 418 (49) |
| Centre-back | 536 | 17 | 8 | 32 | 301 (235) | 391 (145) | 440 (96) | 484 (52) | 512 (24 <30) |

#### Window 2017/18-2023/24

| Line | players | median shots | p25 | p75 | removed by 20 (left) | removed by 30 (left) | removed by 40 (left) | removed by 50 (left) | removed by 60 (left) |
|---|---|---|---|---|---|---|---|---|---|
| Forward | 521 | 97 | 44 | 213 | 20 (501) | 72 (449) | 118 (403) | 144 (377) | 183 (338) |
| Wide | 690 | 68 | 30 | 154 | 85 (605) | 169 (521) | 232 (458) | 278 (412) | 318 (372) |
| Central AM | 134 | 62 | 29 | 129 | 15 (119) | 36 (98) | 52 (82) | 58 (76) | 64 (70) |
| Central midfielder | 777 | 42 | 18 | 91 | 208 (569) | 301 (476) | 372 (405) | 430 (347) | 468 (309) |
| Full-back | 737 | 25 | 11 | 53 | 313 (424) | 416 (321) | 487 (250) | 543 (194) | 574 (163) |
| Centre-back | 794 | 23 | 10 | 47 | 356 (438) | 473 (321) | 545 (249) | 607 (187) | 657 (137) |

**Named test players, 2021/22-2023/24:** Haaland 304 shots over 3 seasons, De Bruyne 187, Rice 119. All three pass any tested minimum.

**Finding.**
- 60 shots leaves Centre-backs below 30 peers in 4 of the 5 three-season Windows.
- 50 keeps every Line at 30 or more, but Centre-backs fall to 40-52 and Full-backs to 56-77.
- 40 keeps the smallest Line, Centre-backs, at 76-96 in every three-season Window. It removes about a quarter of Forwards (70-89 of 325-350) and keeps 75%.

**Proposed final minimum: 40 non-penalty shots in the Window** (unchanged from the starting value). It is the largest tested value that keeps every Line's Reference group at twice the 30-peer minimum or more in every Window. The bootstrap interval (ADR 0003) already makes small samples Borderline, so the minimum only has to stop degenerate cases. Status: proposed. Ahmed decides.

## Spec

### Problem Statement

Pundits, headlines and fans make football claims ("Haaland is an elite finisher", "Arsenal play defensive football") that sound factual but are rarely checked against data, and the vague words in them ("elite", "defensive") have no fixed meaning. A reader can't tell whether a claim holds, holds in part, or can't be tested with public data at all. Ahmed has the Twin model's data and maths, but nothing that turns a sentence into a fair, traceable check.

### Solution

A private command-line tool, Claim Check. A reader types a Claim and gets one Verdict per Reading: Supported, Mixed, Not supported, or Can't check with this data, always with its reason.
- Every Verdict shows the written threshold, the Subject's percentile and interval, the Reference group in plain words, the seasons used, and the versions of the word map, level scale and method.
- The LLM only extracts words from the Claim and writes 2 guarded Summary lines. Deterministic code computes every number and decides every Verdict.
- An outside model (Gemini) reviews the Verdicts, on fixed test claims and on headline claims collected by a fixed rule.

### User Stories

1. As a reader, I want to type a Claim in plain English, so that I can check it without knowing any metric names.
2. As a reader, I want one of 4 fixed Verdicts, so that the answer is never a vague paragraph.
3. As a reader, I want every Verdict to show its threshold in words ("Elite = top 10% of the peer group"), so that I know what the vague word was taken to mean.
4. As a reader, I want the Subject's percentile and its range, so that I can see how close the call was.
5. As a reader, I want the Reference group in plain words ("vs forwards in the top 5 leagues, 2021/22-2023/24, 900+ minutes per season"), so that I know who the Subject was compared with.
6. As a reader, I want the seasons used and the data end date on every Verdict, so that I know it may not match the current season.
7. As a reader, I want "Can't check with this data" with one reason, so that a gap in the data is never shown as a "no".
8. As a reader, I want an ambiguous word ("defensive") checked under each meaning, with each meaning shown, so that the tool never picks a meaning for me.
9. As a reader, I want a negated Claim ("isn't an elite finisher") to get the flipped Verdict, so that wording doesn't change the answer.
10. As a reader, I want a Mixed Verdict to say why in one line, so that I know whether the seasons disagree or the range crosses the line.
11. As a reader, I want skipped seasons listed with their reasons, and "Thin evidence" when fewer than half the Window's seasons remain, so that I know how much the Verdict rests on.
12. As a reader, I want "Range not available: this metric has season totals only." on Chance creation and Build-up, so that I know those two have no bootstrap range.
13. As a reader, I want 2 short Summary lines that never add a number or soften the Verdict, so that the summary can be trusted as much as the table.
14. As a reader, I want a name that matches two players to list both and stop, so that I'm never shown the wrong player.
15. As a reader, I want "in the Premier League" or "for a midfielder" to change the Reference group, so that a Claim's own comparison is honoured.
16. As a reader, I want team Claims judged against the same league, and league Claims ranked among the 5 leagues, so that each Subject is compared like with like.
17. As Ahmed, I want the word map and level scale as versioned tables in code, so that every Verdict can be traced to the exact rules it used.
18. As Ahmed, I want an unmapped claim word logged in LangFuse, so that I can see which words the catalogue should grow to cover.
19. As Ahmed, I want every step of a run traced in LangFuse, named in glossary words, so that any Verdict can be replayed.
20. As Ahmed, I want a Fault (bad file, failed pin, outage, code error) to stop the run with an error, so that "Can't check" always means a data limit and never a bug.
21. As Ahmed, I want two pin tests against Twin's measured numbers, so that Claim Check and Twin can never read the join differently.
22. As Ahmed, I want Twin code left untouched, so that the Twin model and its validation stay exactly as they are.
23. As Ahmed, I want verdict tests that run as pure code from a fixed Extraction, so that a rule change fails a named test with no network.
24. As Ahmed, I want Extraction tests run against the LLM, so that a model change is caught on its own.
25. As Ahmed, I want expected Verdicts written down before the first run, and reviewed by Gemini, so that the tests check the system and not its output.
26. As Ahmed, I want the word map draft reviewed by Gemini before I approve it, so that my approval focuses on flagged lines.
27. As Ahmed, I want 30 headline claims chosen by a fixed rule from Guardian headlines and standfirsts, so that neither of us picks the exam.
28. As Ahmed, I want the Guardian API terms read and confirmed before any collection, so that no terms are broken.
29. As Ahmed, I want a Consistency pass and a Blind plausibility pass by Gemini, with the coverage rate, so that I know whether Verdicts follow from their numbers and match football judgement.
30. As Ahmed, I want no Verdict published until the #17 join retrospective is done, so that nothing goes out on a join with open questions.
31. As Ahmed, I want each Verdict written as JSON under `build/private/claim_check/`, so that a later page can read it without the stand-in ever publishing.
32. As a future live-data ticket (#15), I want the same rules to apply to live Understat, so that only the method version changes.

### Implementation Decisions

All decisions are in the grill record above (Q1-Q20, D1-D9) and ADRs 0001-0003. Their shape, in brief:

- **Modules** (Claim Check context, one folder per layer, D8):
  - **Domain:** Claim, Extraction (the fixed JSON shape), ClaimQuery, word map and level scale (versioned tables), Reference group rules, Line, the test and Verdict rule (ADR 0003), the fail-safe reason order, the Guard. No LangGraph, Groq, LangFuse or pandas imports. Tests run with no network.
  - **Application:** the LangGraph graph, one node per step (D7): extract → resolve subjects → map words → build ClaimQuery → compute tests → decide Verdict → write Summary lines → guard → render.
  - **Infrastructure:** the stand-in adapter (PlayerMatch, TeamMatch, read-only on Twin's join, ADR 0002), the Groq client behind an LLM interface, the LangFuse tracer, and later the Guardian and Gemini clients.
  - **Interface:** the CLI `claim-check "<claim>"` and the Verdict JSON.
- **Reused Twin code, unchanged:** PlayerSeason and Shot records, `percentiles`, `counts_for_metrics`, the stand-in loader and join functions.
- **The Extraction shape** is fixed in "The Extraction and the word map", with `reference_named` (Q8).
- **The Verdict JSON** holds: Claim, Extraction, each Reading's ClaimQuery, tests (value, percentile, interval or the 5-point band label), Verdict, reason, coverage line, Reference group line, Summary lines or "template fallback", and the word-map, level-scale, method, blocked-word and Groq model versions.
- **Bootstrap:** 1,000 resamples, fixed seed, 80% interval. Matches for per-season tests, shots for Pooled tests, TeamMatches for teams and leagues (D4).
- **Shot minimum** for Pooled metrics: 40, proposed above, for Ahmed's decision.
- **Groq model:** one exact model id, pinned (D6).

### Testing Decisions

- A good test checks external behaviour only. Given an Extraction, the Verdict and its rendered facts are fixed. Tests never assert on internal helpers.
- **Seam 1 (main): Extraction → Verdict JSON**, pure code, no network. Every synthetic verdict test (Part 2) and every real-data verdict test (Part 1, 1b) goes through it.
- **Seam 2: Claim text → Extraction**, against the pinned Groq model (Part 3). The only tests that need the network.
- **Seam 3: the stand-in adapter**, with the two pin tests.
- **Prior art:** `tests/test_standin_loader.py` and `tests/test_build.py` for real-data runs and pinned numbers. `tests/test_domain_boundary.py` for "the domain imports no framework". `tests/test_twins.py` for percentile behaviour. The #6 spec's `synthetic` label for hand-made inputs, kept out of `tests/fixtures/`.

### Out of Scope

- Match and manager Subjects, comparison Claims' verdict rule, PPDA, pressing and deep completions, a web front end, BBC Sport RSS live input (all in "Later options").
- Publishing any Verdict (gated on the #17 retrospective).
- Any change to Twin code.
- Live Understat (#15). The rules carry over with a method version change.

### Further Notes

- **Name clash to settle:** #30 added **Finishing** to Twin's glossary: npG − npxG per non-penalty shot for one PlayerSeason, shrunk by normal-normal (D30-2, D30-3). Claim Check's Finishing Claim type uses the same formula, but pooled over a Window and unshrunk, ranked against a Reference group. The Claim type name stays "Finishing" in this spec. A reader of both glossaries could take one for the other. Open for Ahmed.
- Word map v1 is a draft until Ahmed's approval (Q20). No Verdict may cite it before then.

## Tickets (/to-tickets, 7 Nov 2026)

Parent spec issue: #36. All 15 tickets are sub-issues of #36, and their blocking edges are native GitHub dependencies.

| # | Ticket | Label | Blocked by |
|---|---|---|---|
| #37 | Gemini review of the word map v1 draft | ready-for-agent | none |
| #38 | Ahmed approves and freezes word map v1 and level scale v1 | needs-info | #37 |
| #39 | Gemini review of expected Verdicts 1-6 | ready-for-agent | none |
| #40 | Gate: read the Guardian API terms before headline collection | needs-info | none |
| #41 | Gate: #17 join retrospective before any Verdict is published | needs-info | none |
| #42 | Stand-in adapter with PlayerMatch, TeamMatch and two pin tests | ready-for-agent | none |
| #43 | Pooled player Verdicts from an Extraction (tracer bullet) | ready-for-agent | #42 |
| #44 | Per-season player Verdicts with match bootstrap | ready-for-agent | #43 |
| #45 | Season-totals Verdicts with the 5-point band | ready-for-agent | #44 |
| #46 | Team and league Verdicts, with Readings for ambiguous words | ready-for-agent | #43 |
| #47 | Typed Claims end to end (Groq Extraction, LangGraph, LangFuse) | ready-for-agent | #43 |
| #48 | Summary lines, the Guard and the template fallback | ready-for-agent | #47 |
| #49 | Real-data verdict tests on frozen word map v1 | ready-for-agent | #38, #39, #44, #45, #46, #48 |
| #50 | Collect 30 Headline claims from the Guardian API | ready-for-agent | #40 |
| #51 | Outside review of Verdicts by Gemini (Pass A and Pass B) | ready-for-agent | #49, #50 |

Frontier now: #37, #39, #40, #41, #42.
