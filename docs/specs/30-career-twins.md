# #30 spec: career twins

Parent issue: #1. Ticket: #30. Blocks #31. Part A (this spec and `docs/reports/T30_measurements.md`) writes no model code.

## Decisions

Each decision is copied word for word from the "Decisions" list of issue #30. Source of every one: Ahmed's owner review of 7 Nov 2026, as written in #30, after the reference video (hoopers_stats, "Who is LeBron's statistical twin?") and 3 outside reviews that agree on the career method.

1. Career profile = minutes-weighted mean of a player's Pool season z-scores (Pool rule 900 minutes per season stays).
   Source: #30, decision 1 (owner review, 7 Nov 2026).
2. A career needs 9,000+ total Pool minutes (about 100 full matches; mirrors the video's 10,000-minute bar). Report how many careers pass. Target range 500 to 1,000.
   Source: #30, decision 2 (owner review, 7 Nov 2026).
3. Career twins are the main list. Career closeness uses career pairs only.
   Source: #30, decision 3 (owner review, 7 Nov 2026).
4. Distance stays on z-scores. The fingerprint shows percentiles (0 to 100) for readers.
   Source: #30, decision 4 (owner review, 7 Nov 2026).
5. Add metric 11: finishing = (npG - npxG) per shot, with the same shrinkage as other small-sample values. Report its effect on Kane's and Salah's top 5.
   Source: #30, decision 5 (owner review, 7 Nov 2026).
6. Every career shows "Seasons covered: first-last".
   Source: #30, decision 6 (owner review, 7 Nov 2026).
7. Role groups from display_position: FW = Forward, LW/RW = Wide, AM = Central AM. A "same role" filter is on by default, because this data has no height, defence or rebound-type metrics to separate roles.
   Source: #30, decision 7 (owner review, 7 Nov 2026).
8. z-scores stay within all attackers of one league-season. No era or league adjustment.
   Source: #30, decision 8 (owner review, 7 Nov 2026).
9. One person with 2 ids (cross_season_ids) gets one career.
   Source: #30, decision 9 (owner review, 7 Nov 2026).
10. Check the correlation of xA, key passes and xGBuildup. If any pair is above 0.8, report it and stop for an owner decision.
    Source: #30, decision 10 (owner review, 7 Nov 2026).
11. Site: add "How it works" in plain English: the metrics, compared to league-season peers, averaged over the career, nearest match. State the limits: attacking style only, data 2017/18-2023/24.
    Source: #30, decision 11 (owner review, 7 Nov 2026).
12. Keep the loader and per-90 code reusable for a later Claim Check part. Write no claim code now.
    Source: #30, decision 12 (owner review, 7 Nov 2026).

## Measured in Part A

All numbers are in `docs/reports/T30_measurements.md`, written by `scripts/measure_careers.py` on the full stand-in data. Two of them stop Part B until Ahmed decides:

- Decision 2: 188 careers reach 9,000 Pool minutes, below the 500 to 1,000 target.
- Decision 10: xA per 90 and key passes per 90 correlate at 0.815 on z-scores (0.807 on shrunk values), above 0.8.
