# #29 spec: career twins with the 1,350-minute twin rule

Parent issue: #1. Ticket: #29. Source of every decision: issue #29, owner review of 7 Nov 2026, with 3 outside reviews.

**Conflict with #30.** #30 (closed, PR #34) was built after the same review. Its owner decision D30-1 sets a 6,000-minute career bar
(`docs/specs/30-career-twins.md`). #29's decisions 2 and 3 set a different rule. This branch builds #29 as written, so it replaces D30-1.
Ahmed decides which rule stands (PR label needs-ahmed). Every other #29 decision is already on `main` from #30.

## Decisions (copied from #29)

1. Career profile = minutes-weighted mean of a player's twin-eligible season z-scores. **Built here:** only twin-eligible stints are averaged.
2. A season is twin-eligible at 1,350+ minutes (source: FBref comparison pool minimum). Pool rule (900) and the #6 pinned numbers do not change.
   **Built here:** `TWIN_MINUTES = 1350`. No season or career list holds a twin under 1,350 minutes. Every Pool season still gets its own lists.
3. A career needs twin-eligible seasons in 3 or more different seasons. **Built here:** `CAREER_SEASONS = 3`. There is no total-minutes bar (`CAREER_MINUTES = 0`).
4. Career twins are their own list. Career closeness uses career pairs only. On `main` (#30 decision 3, D30-9).
5. Every career shows "Seasons covered: first–last". On `main` (#30 decision 6).
6. Role groups from display_position: FW = Forward, LW/RW = Wide, AM = Central AM. A "same role" filter is on by default. On `main` (#30 decision 7).
7. z-scores stay within all attackers of one league-season. No era or league adjustment. On `main` (#30 decision 8).
8. One person with 2 ids (cross_season_ids) gets one career. On `main` (#30 decision 9). `data/standin/review_decisions.csv` holds 0 such rows.
9. Check the correlation of xA, key passes and xGBuildup. If any pair is above 0.8, report it and stop for an owner decision.
   **Reported:** xA per 90 and key passes per 90 correlate at 0.815 (`docs/reports/T30_measurements.md`). Ahmed decided D30-2: key passes is dropped.
10. Site: a short "How it works" section in plain English. On `main` (#30 decision 11). **Changed here:** its limits line now states the #29 rules.
11. Keep the loader and per-90 code reusable for a later Claim Check part. Write no claim code now. Kept: this branch changes no loader or per-90 code.

## Order note

The issue asks for this spec before code. In this overnight run the spec and the code are in one PR. The spec is the PR's first file to read.
