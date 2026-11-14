# Overnight report, 14 Nov 2026

Queue: #43 → #44 → #46 → #45 → #29 → #12 → #10. One issue per PR. Stand-in data only. Nothing published or deployed. No failure limit reached.

## Status

| Issue | Status | PR | The one thing Ahmed must check |
|---|---|---|---|
| #43 pooled player Verdicts | merged | [#58](https://github.com/afarah101/football-twin/pull/58) | Nothing. It merged by auto-merge after `verify` and `review` passed. |
| #44 per-season player Verdicts | needs-ahmed | [#59](https://github.com/afarah101/football-twin/pull/59) | The Availability denominator (minutes / 90 × the most club matches in the league-season). |
| #46 team and league Verdicts | needs-ahmed | [#60](https://github.com/afarah101/football-twin/pull/60) | The new fail-safe reason "too few matches", and the rule that a league rank meets only if the whole range is inside the top k. |
| #45 season-totals Verdicts | needs-ahmed | [#61](https://github.com/afarah101/football-twin/pull/61) | The Mixed reason "within 5 points of the line" for the 5-point band. |
| #29 career twins, 1,350-minute rule | needs-ahmed | [#65](https://github.com/afarah101/football-twin/pull/65) | Choose the career rule: #29 (1,350+ minute seasons in 3+ seasons, 342 careers) or #30's D30-1 (6,000 minutes, 338 careers, on `main`). Merge #65 for #29, or close it. |
| #12 site map | needs-ahmed | [#63](https://github.com/afarah101/football-twin/pull/63) | The map's look on the season view (a public site change). |
| #10 validation report, local parts | needs-ahmed | [#64](https://github.com/afarah101/football-twin/pull/64) | **The stand-in self-match FAILS:** 7.8% for the winner (cosine) against the 40% target. Q12 says do not launch. |

Merge order: #59, then #60, then #61. Each PR is built on the one before it, and GitHub moves the base when the PR below it merges. #63, #64 and #65 are on `main`. #63 and #65 both touch `site/index.html` and `tests/test_site_data.py`, so the second one to merge may need `main` merged in.

## Notes outside the issues' scope (not fixed)

- Ahmed's pivot: the Twin fails its own launch test on the stand-in (#64). This supports moving to Claim Check.
- Comparison Claims ("Rice is better than Bellingham") still stop with an error: the verdict rule is not designed yet (Q5).
- "Rice plays in his own half" needs event data that the free sources do not have.

## Review

### Code Review: YES

- **Only the issue's files:** YES. Every PR changed only its issue's files.
  - #29 changed the Twin tests that need sample careers or exact twin lists: they now lower the new rules to the Pool's 900 minutes, as they lowered the 6,000 bar before.
  - #12 and #10 also changed one test helper each. `data_files` and `built_files` now leave out the new map file. This is needed for the existing tests to read only league-season files.
  - The #45 PR also changed one old test that expected #45 not to be built.
- **Tests for new behaviour:** YES.
  - #44: 14 tests. #46: 21. #45: 6. #29: 2 new. #12: 6, plus smoke checks. #10: 10.
  - Claim Check tests are synthetic. Twin tests use the loader sample, or are named `hand_made` where the sample has 0 real cases (the rule in `tests/test_build.py`).
- **Verify checks green:** YES. When this report was written, `verify` and `review` had passed on #58-#62. #63 and #64 were re-run after review fixes.
  - All Claude reviews said VERDICT: OK. None found a Critical issue.
- **Review Warnings fixed:**
  - #59: a peer in 2 leagues was counted twice.
  - #63: the plan's loadings print was missing.
  - #64: tied Spearman ranks were not averaged, and the CSV id check was fragile.

### Evaluation: YES, with the gaps below named

- **#43** (merged): every criterion met in #58.
- **#44** (#59): every criterion met, with one test per qualifying season, the match bootstrap and the strict rule. Its needs-ahmed choices are listed in #59 (Availability denominator, 2 leagues in a season, a season with too small a peer group).
- **#46** (#60): every criterion met.
  - Team per-season tests (D5, 10 teams) and Pooled ratios.
  - League ranks with the rank range (D4).
  - "defensive" gives 2 Verdicts, each with its meaning (Q4).
  - Its needs-ahmed choices are listed in #60 (8 choices).
- **#45** (#61): every criterion met.
  - Borderline within 5 points.
  - The label "Range not available: this metric has season totals only.", with a test.
  - The reason "season totals missing".
  - The method version names the band (stand-in-3).
  - Its needs-ahmed choices are listed in #61 (3 choices).
- **#29** (#65): 7 of 7 criteria met. The spec came in the same PR, not before the code (noted in the spec). needs-ahmed because it replaces D30-1.
- **#12** (#63): every criterion met: the PCA map file, the marked player and twins, no axis named, the same-league filter, and a passing smoke test. needs-ahmed because it changes the public site.
- **#10** (#64): **2 of 9 criteria are not met.** The outside review and the blind spot-check need a non-Claude model key, which this queue may not use, so the PR does not close #10. Its needs-ahmed choices are listed in #64 (Wilson interval, baseline, stint rule, stability sampling, tie-break).

Not run: a fresh-session evaluator. Run the evaluator skill on #60 and #64 before you merge them.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
