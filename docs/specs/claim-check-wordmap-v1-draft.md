# Claim Check word map v1 and level scale v1

> **DRAFT, NOT FROZEN.** Drafted by the agent on 7 Nov 2026 from the catalogue's example words in `docs/specs/claim-check.md` (Q3, Q4, Q6, Q7), plus plain variants only. No Verdict may cite this draft. It is frozen as v1 only by Ahmed's approval, after the Gemini review (Q20). Lines marked **⚑** are the agent's own guesses, which the review should check closely.

## Matching rules

These apply to every word and phrase below.

- Case-insensitive.
- Plain variants match: plural (-s, -es), "-ing", and hyphen or space ("end-to-end" = "end to end").
- A phrase matches only as a whole phrase. The longest match wins, so "defensive football" is matched before "defensive".
- The LLM copies words verbatim (Q5). Matching is done by code only.
- A claim word with no row here gives Can't check with this data, reason "claim word not in catalogue", and is logged in LangFuse.

**Direction.** "more" means a high value of the Main metric meets the threshold. "less" means a low value meets it. The percentile is taken in the Claim's direction (D3) and shown in plain words.

**Built-in level.** A word that carries its own level ("clinical") uses the "no level word" row of the level scale: ≥ 75th in its direction. If the Claim also has a level word ("very clinical"), the level word wins.

## Word map v1: players

| Words and phrases | Readings (Claim type) | Direction | Built-in level |
|---|---|---|---|
| "finisher", "finishing" | Finishing | more | none: takes the Claim's level word, else ≥ 75th |
| "clinical" | Finishing | more | ≥ 75th |
| "wasteful" | Finishing | less | ≥ 75th in its direction (≤ 25th) |
| "deadly in front of goal" ⚑ | Finishing; Goalscoring | more | ≥ 75th |
| "scores from distance", "great from range" | Finishing from distance | more | "great": ≥ 75th |
| "shoots a lot" | Shot volume | more | ≥ 75th |
| "shy", "shot-shy" ⚑ | Shot volume | less | ≤ 25th |
| "gets into great positions" | Shot quality | more | "great": ≥ 75th |
| "takes bad shots" | Shot quality | less | "bad": ≤ 25th |
| "dangerous", "goal threat" | Goal threat | more | ≥ 75th |
| "prolific", "scores a lot" | Goalscoring | more | ≥ 75th |
| "goalscorer", "scorer" ⚑ | Goalscoring | more | none: takes the Claim's level word, else ≥ 75th |
| "creative", "creator" | Chance creation | more | ≥ 75th |
| "involved in build-up" | Build-up | more | ≥ 75th |
| "shoots from distance", "long shots" ⚑ | Long shots | more | ≥ 75th |
| "good in the air", "aerial threat" ⚑ | Aerial threat | more | "good": ≥ 60th |
| "ever-present" ⚑ | Availability | more | ≥ 90th. "Ever-present" reads as near-all minutes, so "elite" is used, not the bare 75th |
| "regular starter" | Availability | more | ≥ 75th |

**Players, Can't check with this data:**

| Words | Reason |
|---|---|
| "injury-prone" | "no injury data" |
| "decent", "underrated", "overrated" | "claim word not in catalogue" |
| "dribbler", "dribbling", "presses", "pressing", "work rate", "hard-working", "pace", "quick", "fast", "passer", "passing range", "tackler", "defends well", "leader", "most of his time", "own half", "off the ball" | "metric not in data" |

## Word map v1: teams

| Words and phrases | Readings (Claim type) | Direction | Built-in level |
|---|---|---|---|
| "attacking", "free-scoring" | Attack | more | ≥ 75th |
| "blunt" | Attack | less | ≤ 25th |
| "solid", "tight at the back" | Defence | less npxG against | ≥ 75th in its direction |
| "leaky" | Defence | more npxG against | ≥ 75th in its direction |
| "defensive", "defensive football" | Defence; Game openness | Defence: less npxG against. Game openness: less total npxG | ≥ 75th in each direction (Q4 ambiguity rule, D3) |
| "boring", "park the bus" ⚑ | Game openness | less | ≤ 25th of total npxG |
| "open", "end-to-end" | Game openness | more | ≥ 75th |
| "give up big chances" | Chances conceded | more npxG per shot against | ≥ 75th |
| "dominant", "control games" | Dominance | more | ≥ 75th |
| "clinical" | Team finishing | more | ≥ 75th |
| "wasteful" | Team finishing | less | ≤ 25th |
| "dangerous from set pieces" | Set-piece threat | more | ≥ 75th |
| "weak at set pieces" | Set-piece defence | more set-piece xG against | ≥ 75th in its direction |

"Clinical" and "wasteful" map by Subject kind: Finishing for a player, Team finishing for a team. They are not ambiguous, because the Extraction gives the Subject kind.

**Teams, Can't check with this data, reason "metric not in data":** "press", "pressing", "high press", "PPDA", "possession", "direct", "long-ball", "high line", "counter-attacking", "on the counter", "formation", "wins", "results", "points".

## Word map v1: leagues

| Words and phrases | Readings (Claim type) | Direction |
|---|---|---|
| "open", "high-scoring" | Open or high-scoring | more npxG per match |
| "defensive", "defensive league" | Open or high-scoring | less npxG per match |
| "set-piece heavy" | Set-piece league | more share of xG from set pieces |
| "lots of long shots" | Long-shot league | more outside-box share |

League Claims use ranks, not percentiles (see the league level scale below).

## Reference group phrases v1 (`reference_named`)

| Phrase | Reference group rule |
|---|---|
| "in the Premier League", "in the EPL", "in England" | that league only, same Window, same Line |
| "in La Liga", "in Spain" | that league only |
| "in the Bundesliga", "in Germany" | that league only |
| "in Serie A", "in Italy" | that league only |
| "in Ligue 1", "in France" | that league only |
| "in the league" ⚑ | the Subject's league in the latest season of the Window |
| "in Europe", "in the top 5 leagues" | the default: all 5 leagues |
| "for a forward", "for a striker" ⚑ | Line Forward |
| "for a winger" | Line Wide |
| "for an attacking midfielder", "for a number 10" ⚑ | Line Central AM |
| "for a midfielder" | Line Central midfielder |
| "for a full-back", "for a wing-back" | Line Full-back |
| "for a centre-back", "for a defender" ⚑ | Line Centre-back |

Any other Reference group phrase gives Can't check with this data, reason "peer group not in catalogue".

## Level scale v1: players and teams

A copy of `docs/specs/claim-check.md` Q6. Percentiles are mid-rank within the Reference group, in the Claim's direction.

| Level words | Threshold |
|---|---|
| "the best", "the worst" | rank 1 (or last) |
| "elite", "world-class", "one of the best" | ≥ 90th |
| "great", "excellent", "very good", "top" | ≥ 75th |
| "good" | ≥ 60th |
| "above average" | > 50th |
| "average" | 25th-75th |
| "below average" | < 50th |
| "poor", "bad" | ≤ 25th |
| "terrible", "one of the worst" | ≤ 10th |
| no level word, positive claim-type word | ≥ 75th |
| no level word, negative claim-type word | ≤ 25th |

## Level scale v1: leagues

| Level words | Threshold |
|---|---|
| "the most", "the least" | rank 1, or rank 5 |
| "one of the most", "one of the least" | rank 1-2, or rank 4-5 |
| "more than <league>", "less than <league>" | a direct comparison of the two leagues |
| any other level word | Can't check with this data, reason "level word does not fit a 5-league comparison" |

## Flagged lines (⚑) for the Gemini review

1. "deadly in front of goal": two Readings (Finishing and Goalscoring), because readers use it for both.
2. "shy" alone may be too loose. "Shot-shy" is the usual phrase.
3. "goalscorer" and "scorer" with no level word default to ≥ 75th.
4. "shoots from distance" (Long shots, volume) and "scores from distance" (Finishing from distance, conversion) differ by one word.
5. "good in the air" covers attacking headers only. A reader may mean defensive headers too, which is not in the data.
6. "ever-present" uses ≥ 90th, not the bare 75th.
7. "boring" and "park the bus" both map to few chances in the team's games.
8. "in the league" uses the Subject's latest league in the Window.
9. "for a striker" = Forward, "for a number 10" = Central AM, "for a defender" = Centre-back. A full-back is also a defender.
