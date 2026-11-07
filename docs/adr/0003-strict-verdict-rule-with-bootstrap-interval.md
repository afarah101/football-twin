---
status: accepted
---

# Strict verdict rule with a bootstrap interval

Within one Reading, a Verdict rests on one or more tests: the pooled value, or one test per qualifying season, or one per Main metric. Each test's 80% interval comes from resampling the subject's matches (per-season tests) or shots (Pooled tests) 1,000 times with a fixed seed, against a fixed Reference group. A test meets its threshold if the whole interval clears it, misses if the whole interval misses, and is Borderline if the interval crosses it. Supported needs every test to meet. Not supported needs every test to miss. Everything else is Mixed (owner, Q9, 7 Nov 2026).

## Considered Options

- **Majority of seasons.** Fewer Mixed Verdicts, but a player elite in 1 season of 3 could come out Supported. That's the misleading result an adversarial reader would look for.
- **A fixed 5-point band around the threshold** (Q6). Replaced: it ignores sample size, so a 300-shot season and a 40-shot season would get the same margin.

## Consequences

- Chance creation and Build-up have season totals only on the stand-in, with no per-match split. They keep the 5-point band, and the Verdict always says "Range not available: this metric has season totals only." (Q10). They switch to the bootstrap with live Understat (#15), and that changes the method version.
- Mixed will be common. Every Mixed Verdict states its reason in one line.
