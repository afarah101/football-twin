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

## Owner decisions after Part A

Source of every one: Ahmed, 7 Nov 2026, after `docs/reports/T30_measurements.md`, given in the #30 Part B1 brief. Where one differs from a decision above, this one wins.

- **D30-1.** Career bar: 6,000+ total Pool minutes (replaces 9,000). The 500-1,000 target is dropped.
- **D30-2.** Drop key passes per 90. Keep xA per 90. Add finishing = (npG - npxG) per non-penalty shot. The model keeps 10 metrics.
- **D30-3.** Finishing shrinkage: the same method as npxG per shot.
- **D30-4.** Career role group: the role group with the most career minutes.
- **D30-5.** Career list: role filter only, on by default. Same-league filter stays on season lists only.
- **D30-6.** Career fingerprint percentiles: percentile among all careers.
- **D30-7.** Each stint keeps its own minutes. "Seasons covered" counts distinct seasons.
- **D30-8.** Players under 6,000 minutes keep season twins, labelled "season twins".

## Build choices in Part B1

No decision covered these in B1. D30-9 and D30-10 below settle them: same-role closeness changes, and the other three are accepted.

- **Same-role closeness.** On the same-role list, closeness is measured against career pairs inside that role group, as the same-league season list uses same-league pairs (Ahmed, 6 Nov 2026). The all-roles list uses all career pairs (decision 3).
- **Role group tie.** Two role groups with equal career minutes: the group of the latest Pool season wins. The full data holds 0 such ties (T30).
- **Career name.** A career shows the name of its latest Pool PlayerSeason.
- **Career methods.** Career lists are built for every Candidate method, as season lists are. The Basketball method stays on season lists for the validation report.

## Owner decisions after Part B1

Source of every one: Ahmed, 7 Nov 2026, given in the #30 Part B2 brief. Where one differs from a decision or choice above, this one wins.

- **D30-9.** Career closeness is always measured against all career pairs, with the role filter on or off. Label: "closer than X% of all careers".
- **D30-10.** Accept: a role tie goes to the latest season; a career shows its latest name; career lists exist for all 3 methods. The site shows Euclidean.
- **D30-11.** No data file loaded for one player view may exceed 1 MB. Split careers.json as needed.
- **D30-12.** Fingerprint labels in plain English. finishing shows as "Finishing (goals vs xG per shot)".
