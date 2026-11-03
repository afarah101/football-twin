# worldfootballR_data vetting: FBref per-match positions and minutes

Run date: 2026-11-03. Source: GitHub repo `JaseZiv/worldfootballR_data`, releases `fb_advanced_match_stats` and `fb_match_summary`. Release assets have no commit to pin, so the files are pinned by the SHA-256 values in Task 2.

**Mode used: NAMES-ONLY.** `config/face_validity_pairs.yaml` is not committed, so this report holds column names, position strings, counts, dates and agreement rates only. It holds no player names and no metric values.

One exception needs your review. The scripts added up minutes and worked out a primary position per player in memory, to test the rule. Only counts were printed, and no per-player value is shown here. A private working table of the FBref rows stays in `~/sandbox/wfr/out_fb/union.pkl`, outside the repo.

## Verdict

| Question | Verdict | Reason |
|---|---|---|
| Task 8: can 2014/15 enter the Pool with these minutes? | **NO** | No FBref row is dated before 2017-08-04. 2015/16 and 2016/17 are missing too. |
| Task 9: usable for the primary-position rule? | **YES, for 2017/18 to 2023/24, with the limits below** | Named positions and minutes exist per player per match. Substitutes are not marked in these files, but they can be worked out from a second release. |

**This is not the plan's rule run as written.** Using it would change three things, and each is Ahmed's decision:

1. **Seasons:** positions start at 2017/18, not 2014/15. The later-season test (Q10) would rest on a 2024/25 season that stops at 2025-02-03.
2. **Position labels:** FBref's labels replace Understat's, and the two have never been compared because the site is down.
3. **Wide players:** FBref `LM` and `RM` are excluded in the mapping below, as Q17 treats `ML` and `MR`. That is 889 PlayerSeasons (453 + 436), against 1,050 for `LW` and `RW` (510 + 540).

## Findings

| Severity | Finding | Evidence |
|---|---|---|
| **Critical** | Positions start at 2017/18. The three earlier seasons in the plan's scope have none, which leaves 137,072 shot rows without a position. | Tasks 3, 7, 8 |
| **Critical** | 2024/25 stops at 2025-02-03 in all five leagues, with 180 to 239 matches. It is the only complete season after the Q10 cut-off that the plan could report on. Only 1,098 PlayerSeasons reach 900 FBref minutes in it, against 1,567 to 1,636 in the full seasons. | Tasks 3, 9 |
| Warning | The `summary` files named in the brief hold only part of 2024/25 and the start of 2025/26, so they were not used. The other stat types go back further, but each has gaps of its own: `passing` has La Liga 2020/21 at 239 of 380, and `possession` has La Liga 2019/20 at 10 of 380. This report uses the union of the five stat types holding `Pos`. | Tasks 1, 3 |
| Warning | Substitutes are not marked. No column names a start, sub, lineup or bench across 30 files, and `Pos` has no `Sub` value. The flag has to come from `fb_match_summary`, joined by name. It gives exactly 11 non-substitutes on 26,808 of 27,659 team-matches (96.92%). It is weakest on Serie A 2019/20 (82.11%) and La Liga 2021/22 to 2023/24 (90.66% to 92.76%), and 2025/26 has no events. | Task 9 |
| Warning | FBref labels do not map cleanly onto the plan's six codes. `LW` and `RW` cover both the FW and AM sides, and `AM` states no side. Pool membership is unaffected, because all these codes are in the Pool, but the exact code cannot be recovered. | Task 6 |
| Warning | `LM` and `RM` are the largest open call. Whether they match Understat's `ML` and `MR` is untested. Q17's list of names cannot be produced in this mode, so only counts are given: 889 PlayerSeasons overall, 107 in 2022/23. | Tasks 6, 9 |
| Warning | 12.03% of rows hold several positions, such as `FW,LW`, with no minutes per position. 646 values (15,975 rows) mix Pool and excluded positions. Using the first listed position is an assumption, since nothing shown here proves FBref lists the main one first. Splitting minutes evenly instead changes Pool membership on 84 of 12,410 PlayerSeasons. | Tasks 4, 9 |
| Warning | No shared id with the shot files, so the join uses names. 264 of 3,300 Pool PlayerSeasons (8.00%) find no shot-file match by name. La Liga is the worst league at 84.41%. A name map would be needed to recover them. | Task 7 |
| Warning | Four Serie A 2023/24 fixtures appear under two URLs, which helps explain 383 matches where 380 are expected, and could count minutes twice. One 2022/23 repeat fits the relegation tie-breaker. Nothing was removed. Serie A 2020/21 and Bundesliga 2021/22 each still lack one match. | Task 3 |
| Warning | No licence, and the repo is archived. Q3 and Q18 stay open, and Sports Reference's terms were not read. These files also do not meet the plan's rule that fixtures are real Understat responses. | Task 1, plan |
| Info | Minutes rarely match Understat exactly (11.40% of keys), but 99.29% fall within 90 minutes and the 900-minute gate agrees on 17,273 of 17,347. The likely cause is that FBref stops at about 90 per match: the highest value is 91. Against HF's own FBref file, joined by id, 95.58% are identical. | Task 5 |
| Info | Keeping substitute minutes changes Pool membership on only 50 of 12,410 PlayerSeasons, so the substitute flag matters little for this decision. | Task 9 |
| Info | FBref's own season-level labels broadly agree with the primary position: all 936 `GK` primaries are `GK`, and 1,589 of 1,671 `FW` primaries are `FW`. This is a sanity check, not independent proof, because both come from FBref. | Task 9 |
| Info | Stat types rarely disagree. For example, England `passing_types` differs from `passing` on 7 `Pos` values and 0 `Min` values. `passing` was kept wherever it had the match. | Task 3 |
| Info | 6 rows have no `Min`, and they count as 0 in the sums. The generic labels `MF` and `DF` appear on 27 and 17 rows. | Tasks 3, 6 |
| Info | Security result is clean: every `.rds` is data-only and the one CSV has 0 formula-style cells. Five `fb_match_summary` files have no GitHub digest, so their sizes were compared instead. | Task 2 |

## Step 0

```
$ pwd
/Users/ahmed.farah/Projects/football-twin
$ git status -sb
## main...origin/main [ahead 1]
?? config/
$ git log --oneline -- config/
(no output: never committed)
$ wc -c config/face_validity_pairs.yaml
       0 config/face_validity_pairs.yaml
```

Hard rules from `CLAUDE.md`: no distance code runs and no metric output is produced or shown until Ahmed has committed `config/face_validity_pairs.yaml`, and nobody else suggests, drafts or edits the pairs. No distance code ran here. The file remains empty and untouched.

**The position rule:**

- Primary position is the position with most minutes, and it must be one of the plan's six codes: **FW, FWL, FWR, AML, AMC, AMR**.
- Q5: it ignores substitute appearances and uses named positions only.
- Q6: a PlayerSeason is player + league + season. The 900-minute minimum applies to each stint, and stints are never merged.
- Q17: the six positions stay as written. STEP 0 lists who `ML` and `MR` exclude in a one-season sample, and Ahmed decides.

**From the shots report:** shot rows are usable for 2014/15 to 2024/25, and combined with HF for 2015/16 to 2024/25. Positions were the remaining gap, and this release was named there as an unvetted lead.

## Task 1: locate the files

```
$ gh release view fb_advanced_match_stats -R JaseZiv/worldfootballR_data --json tagName,publishedAt,assets --jq ... (asset count; Big 5 summary_player assets)
fb_advanced_match_stats
2023-09-02T18:32:41Z
168
ENG_M_1st_summary_player_advanced_match_stats.csv 4791459 2025-09-16T22:37:16Z sha256:63314f4ce44aec176218ddb6e39ca5079703f6c87f18d2367fae7f255e5f2224
ENG_M_1st_summary_player_advanced_match_stats.rds 8041149 2025-09-16T22:37:14Z sha256:ad84fac6b4ecae9376ae3921f4f844ce07ae64d8c7772764ce83491093468211
ESP_M_1st_summary_player_advanced_match_stats.csv 4044495 2025-09-16T22:38:07Z sha256:1cd6242799e42db82cdfa16ef2067b91a0596ef3e6649c17d2649829288d9793
ESP_M_1st_summary_player_advanced_match_stats.rds 6938232 2025-09-16T22:38:06Z sha256:8b9316317b3e123f3e99fce45cebeb42e58b8390b6cd64fdd2d9b76109f9284b
FRA_M_1st_summary_player_advanced_match_stats.csv 3379962 2025-09-16T22:39:07Z sha256:03035798a161055797f4b7880ebdd56188bf8d8ec5d218767737d16fa98f58af
FRA_M_1st_summary_player_advanced_match_stats.rds 6111691 2025-09-16T22:39:05Z sha256:7f035a2ebdb5705decaf4ddd03eb5a48324240c2b9bae8c64fc31a0e9c955b73
GER_M_1st_summary_player_advanced_match_stats.csv 3754220 2025-09-16T22:40:32Z sha256:8b30760346abba72e7b10281eb6ae93b5e8bb08e3ae040b86bdabab90045f754
GER_M_1st_summary_player_advanced_match_stats.rds 6407769 2025-09-16T22:40:31Z sha256:7c15f85c8e02d3181e15bb138b9c002060d79b5017e69bd91f1ad6225e23daa9
ITA_M_1st_summary_player_advanced_match_stats.csv 4036524 2025-09-16T22:42:06Z sha256:5d73450ae994556867e371d8cb801d0ace32c371a1ef3bf7ca4781f8cbf87ae2
ITA_M_1st_summary_player_advanced_match_stats.rds 7337049 2025-09-16T22:42:04Z sha256:7804d70227fbce3c338c002a95d6d47f2de51a31b42f7e035ad61412da5127a4

$ ... --jq (distinct country prefixes and stat types)
ENG_M_1st ESP_M_1st FRA_M_1st GER_M_1st ITA_M_1st USA_M_1st
defense keeper misc passing passing_types possession summary

$ gh release view fb_match_summary ... --jq (Big 5 assets)
24
ENG_M_1st_match_summary.csv 19135823 2025-02-13T18:01:29Z
ESP_M_1st_match_summary.rds 28645985 2025-02-13T18:02:14Z
ESP_M_1st_match_summary.csv 19518943 2025-02-13T18:02:17Z
FRA_M_1st_match_summary.rds 23958653 2025-02-13T18:02:58Z
FRA_M_1st_match_summary.csv 16328880 2025-02-13T18:03:02Z
GER_M_1st_match_summary.rds 24724588 2025-02-13T18:03:44Z
GER_M_1st_match_summary.csv 17656107 2025-02-13T18:03:47Z
ITA_M_1st_match_summary.rds 27662572 2025-02-13T18:04:35Z
ITA_M_1st_match_summary.csv 18879420 2025-02-13T18:04:38Z

$ gh release view fb_advanced_match_stats ... --jq (Big 5 player rds assets of all stat types: name, bytes, updated)
ENG_M_1st_defense_player_advanced_match_stats.rds 71356210 2025-09-16T23:23:30Z
ENG_M_1st_keeper_player_advanced_match_stats.rds 5119293 2025-09-17T11:12:51Z
ENG_M_1st_misc_player_advanced_match_stats.rds 69500306 2025-09-17T10:52:29Z
ENG_M_1st_passing_player_advanced_match_stats.rds 77880394 2025-09-16T22:52:22Z
ENG_M_1st_passing_types_player_advanced_match_stats.rds 72714944 2025-09-16T23:08:01Z
ENG_M_1st_possession_player_advanced_match_stats.rds 73692648 2025-09-16T23:39:17Z
ENG_M_1st_summary_player_advanced_match_stats.rds 8041149 2025-09-16T22:37:14Z
ESP_M_1st_defense_player_advanced_match_stats.rds 68473878 2025-09-16T23:24:28Z
ESP_M_1st_keeper_player_advanced_match_stats.rds 4690105 2025-09-17T11:14:24Z
ESP_M_1st_misc_player_advanced_match_stats.rds 68494697 2025-09-17T10:54:10Z
ESP_M_1st_passing_player_advanced_match_stats.rds 71563880 2025-09-16T22:53:19Z
ESP_M_1st_passing_types_player_advanced_match_stats.rds 69865362 2025-09-16T23:08:57Z
ESP_M_1st_possession_player_advanced_match_stats.rds 67454103 2025-09-16T23:40:13Z
ESP_M_1st_summary_player_advanced_match_stats.rds 6938232 2025-09-16T22:38:06Z
FRA_M_1st_defense_player_advanced_match_stats.rds 64436008 2025-09-16T23:25:32Z
FRA_M_1st_keeper_player_advanced_match_stats.rds 60802303 2025-09-17T11:15:52Z
FRA_M_1st_misc_player_advanced_match_stats.rds 64093040 2025-09-17T10:55:42Z
FRA_M_1st_passing_player_advanced_match_stats.rds 71835961 2025-09-16T22:54:32Z
FRA_M_1st_passing_types_player_advanced_match_stats.rds 71337372 2025-09-16T23:10:02Z
FRA_M_1st_possession_player_advanced_match_stats.rds 75759965 2025-09-16T23:41:20Z
FRA_M_1st_summary_player_advanced_match_stats.rds 6111691 2025-09-16T22:39:05Z
GER_M_1st_defense_player_advanced_match_stats.rds 59848163 2025-09-16T23:27:03Z
GER_M_1st_keeper_player_advanced_match_stats.rds 4095122 2025-09-17T11:17:19Z
GER_M_1st_misc_player_advanced_match_stats.rds 59669628 2025-09-17T10:57:10Z
GER_M_1st_passing_player_advanced_match_stats.rds 65218621 2025-09-16T22:56:02Z
GER_M_1st_passing_types_player_advanced_match_stats.rds 59106802 2025-09-16T23:11:32Z
GER_M_1st_possession_player_advanced_match_stats.rds 63201463 2025-09-16T23:42:50Z
GER_M_1st_summary_player_advanced_match_stats.rds 6407769 2025-09-16T22:40:31Z
ITA_M_1st_defense_player_advanced_match_stats.rds 72737361 2025-09-16T23:28:43Z
ITA_M_1st_keeper_player_advanced_match_stats.rds 64817945 2025-09-17T11:18:55Z
ITA_M_1st_misc_player_advanced_match_stats.rds 61174721 2025-09-17T10:58:51Z
ITA_M_1st_passing_player_advanced_match_stats.rds 79346587 2025-09-16T22:57:41Z
ITA_M_1st_passing_types_player_advanced_match_stats.rds 78742349 2025-09-16T23:13:10Z
ITA_M_1st_possession_player_advanced_match_stats.rds 81039751 2025-09-16T23:44:29Z
ITA_M_1st_summary_player_advanced_match_stats.rds 7337049 2025-09-16T22:42:04Z

$ gh repo view JaseZiv/worldfootballR_data --json isArchived,licenseInfo,pushedAt
{"isArchived":true,"licenseInfo":null,"pushedAt":"2025-09-18T19:54:58Z"}
```

The repo's own backfill script sets the first Big 5 season:

```
$ gh api repos/JaseZiv/worldfootballR_data/contents/R/fb_advanced_match_stats/backfill_fb_advanced_match_stats.R --jq .content | base64 -d | grep -n -A3 first_season_end_year | head -5
61:  first_season_end_year <- ifelse(
62-    group == 'big5',
63-    2018,
64-    2019
--
```

Season coverage of the `summary` files, and of each England stat type:

```
ENG (8464, 58)
{'MatchURL': 'str', 'League': 'str', 'Match_Date': 'str', 'Matchweek': 'str', 'Home_Team': 'str', 'Home_Formation': 'str', 'Home_Score': 'str', 'Home_xG': 'float64', 'Home_Goals': 'str', 'Home_Yellow_Cards': 'str', 'Home_Red_Cards': 'str', 'Away_Team': 'str', 'Away_Formation': 'str', 'Away_Score': 'str', 'Away_xG': 'float64', 'Away_Goals': 'str', 'Away_Yellow_Cards': 'str', 'Away_Red_Cards': 'str', 'Game_URL': 'str', 'Team': 'str', 'Home_Away': 'str', 'Player': 'str', 'Player_Href': 'str', 'Player_Num': 'str', 'Nation': 'str', 'Pos': 'str', 'Age': 'str', 'Min': 'str', 'Gls': 'str', 'Ast': 'str', 'PK': 'str', 'PKatt': 'str', 'Sh': 'str', 'SoT': 'str', 'CrdY': 'str', 'CrdR': 'str', 'Touches': 'str', 'Tkl': 'str', 'Int': 'str', 'Blocks': 'str', 'xG_Expected': 'float64', 'npxG_Expected': 'float64', 'xAG_Expected': 'float64', 'SCA_SCA': 'str', 'GCA_SCA': 'str', 'Cmp_Passes': 'str', 'Att_Passes': 'str', 'Cmp_percent_Passes': 'float64', 'PrgP_Passes': 'str', 'Carries_Carries': 'str', 'PrgC_Carries': 'str', 'Att_Take_Ons': 'str', 'Succ_Take_Ons': 'str', 'Competition_Name': 'str', 'Gender': 'str', 'Country': 'str', 'Tier': 'str', 'Season_End_Year': 'int32'}
ESP (8163, 58)
{'MatchURL': 'str', 'League': 'str', 'Match_Date': 'str', 'Matchweek': 'str', 'Home_Team': 'str', 'Home_Formation': 'str', 'Home_Score': 'float64', 'Home_xG': 'float64', 'Home_Goals': 'str', 'Home_Yellow_Cards': 'str', 'Home_Red_Cards': 'str', 'Away_Team': 'str', 'Away_Formation': 'str', 'Away_Score': 'float64', 'Away_xG': 'float64', 'Away_Goals': 'str', 'Away_Yellow_Cards': 'str', 'Away_Red_Cards': 'str', 'Game_URL': 'str', 'Team': 'str', 'Home_Away': 'str', 'Player': 'str', 'Player_Href': 'str', 'Player_Num': 'float64', 'Nation': 'str', 'Pos': 'str', 'Age': 'str', 'Min': 'float64', 'Gls': 'float64', 'Ast': 'float64', 'PK': 'float64', 'PKatt': 'float64', 'Sh': 'float64', 'SoT': 'float64', 'CrdY': 'float64', 'CrdR': 'float64', 'Touches': 'float64', 'Tkl': 'float64', 'Int': 'float64', 'Blocks': 'float64', 'xG_Expected': 'float64', 'npxG_Expected': 'float64', 'xAG_Expected': 'float64', 'SCA_SCA': 'float64', 'GCA_SCA': 'float64', 'Cmp_Passes': 'float64', 'Att_Passes': 'float64', 'Cmp_percent_Passes': 'float64', 'PrgP_Passes': 'float64', 'Carries_Carries': 'float64', 'PrgC_Carries': 'float64', 'Att_Take_Ons': 'float64', 'Succ_Take_Ons': 'float64', 'Competition_Name': 'str', 'Gender': 'str', 'Country': 'str', 'Tier': 'str', 'Season_End_Year': 'int32'}
FRA (6659, 66)
{'MatchURL': 'str', 'League': 'str', 'Match_Date': 'str', 'Matchweek': 'str', 'Home_Team': 'str', 'Home_Formation': 'str', 'Home_Score': 'float64', 'Home_xG': 'float64', 'Home_Goals': 'str', 'Home_Yellow_Cards': 'str', 'Home_Red_Cards': 'str', 'Away_Team': 'str', 'Away_Formation': 'str', 'Away_Score': 'float64', 'Away_xG': 'float64', 'Away_Goals': 'str', 'Away_Yellow_Cards': 'str', 'Away_Red_Cards': 'str', 'Game_URL': 'str', 'Team': 'str', 'Home_Away': 'str', 'Player': 'str', 'Player_Href': 'str', 'Player_Num': 'float64', 'Nation': 'str', 'Pos': 'str', 'Age': 'str', 'Min': 'float64', 'Gls': 'float64', 'Ast': 'float64', 'PK': 'float64', 'PKatt': 'float64', 'Sh': 'float64', 'SoT': 'float64', 'CrdY': 'float64', 'CrdR': 'float64', 'Touches': 'float64', 'Tkl': 'float64', 'Int': 'float64', 'Blocks': 'float64', 'xG_Expected': 'float64', 'npxG_Expected': 'float64', 'xAG_Expected': 'float64', 'SCA_SCA': 'float64', 'GCA_SCA': 'float64', 'Cmp_Passes': 'float64', 'Att_Passes': 'float64', 'Cmp_percent_Passes': 'float64', 'PrgP_Passes': 'float64', 'Carries_Carries': 'float64', 'PrgC_Carries': 'float64', 'Att_Take_Ons': 'float64', 'Succ_Take_Ons': 'float64', 'Competition_Name': 'str', 'Gender': 'str', 'Country': 'str', 'Tier': 'str', 'Season_End_Year': 'int32', 'Fls': 'float64', 'Fld': 'float64', 'Off': 'float64', 'Crs': 'float64', 'TklW': 'float64', 'OG': 'float64', 'PKwon': 'float64', 'PKcon': 'float64'}
GER (6469, 66)
{'MatchURL': 'str', 'League': 'str', 'Match_Date': 'str', 'Matchweek': 'str', 'Home_Team': 'str', 'Home_Formation': 'str', 'Home_Score': 'float64', 'Home_xG': 'float64', 'Home_Goals': 'str', 'Home_Yellow_Cards': 'str', 'Home_Red_Cards': 'str', 'Away_Team': 'str', 'Away_Formation': 'str', 'Away_Score': 'float64', 'Away_xG': 'float64', 'Away_Goals': 'str', 'Away_Yellow_Cards': 'str', 'Away_Red_Cards': 'str', 'Game_URL': 'str', 'Team': 'str', 'Home_Away': 'str', 'Player': 'str', 'Player_Href': 'str', 'Player_Num': 'float64', 'Nation': 'str', 'Pos': 'str', 'Age': 'str', 'Min': 'float64', 'Gls': 'float64', 'Ast': 'float64', 'PK': 'float64', 'PKatt': 'float64', 'Sh': 'float64', 'SoT': 'float64', 'CrdY': 'float64', 'CrdR': 'float64', 'Touches': 'float64', 'Tkl': 'float64', 'Int': 'float64', 'Blocks': 'float64', 'xG_Expected': 'float64', 'npxG_Expected': 'float64', 'xAG_Expected': 'float64', 'SCA_SCA': 'float64', 'GCA_SCA': 'float64', 'Cmp_Passes': 'float64', 'Att_Passes': 'float64', 'Cmp_percent_Passes': 'float64', 'PrgP_Passes': 'float64', 'Carries_Carries': 'float64', 'PrgC_Carries': 'float64', 'Att_Take_Ons': 'float64', 'Succ_Take_Ons': 'float64', 'Competition_Name': 'str', 'Gender': 'str', 'Country': 'str', 'Tier': 'str', 'Season_End_Year': 'int32', 'Fls': 'float64', 'Fld': 'float64', 'Off': 'float64', 'Crs': 'float64', 'TklW': 'float64', 'OG': 'float64', 'PKwon': 'float64', 'PKcon': 'float64'}
ITA (8087, 66)
{'MatchURL': 'str', 'League': 'str', 'Match_Date': 'str', 'Matchweek': 'str', 'Home_Team': 'str', 'Home_Formation': 'str', 'Home_Score': 'str', 'Home_xG': 'float64', 'Home_Goals': 'str', 'Home_Yellow_Cards': 'str', 'Home_Red_Cards': 'str', 'Away_Team': 'str', 'Away_Formation': 'str', 'Away_Score': 'str', 'Away_xG': 'float64', 'Away_Goals': 'str', 'Away_Yellow_Cards': 'str', 'Away_Red_Cards': 'str', 'Game_URL': 'str', 'Team': 'str', 'Home_Away': 'str', 'Player': 'str', 'Player_Href': 'str', 'Player_Num': 'str', 'Nation': 'str', 'Pos': 'str', 'Age': 'str', 'Min': 'str', 'Gls': 'str', 'Ast': 'str', 'PK': 'str', 'PKatt': 'str', 'Sh': 'str', 'SoT': 'str', 'CrdY': 'str', 'CrdR': 'str', 'Touches': 'str', 'Tkl': 'str', 'Int': 'str', 'Blocks': 'str', 'xG_Expected': 'float64', 'npxG_Expected': 'float64', 'xAG_Expected': 'float64', 'SCA_SCA': 'str', 'GCA_SCA': 'str', 'Cmp_Passes': 'str', 'Att_Passes': 'str', 'Cmp_percent_Passes': 'float64', 'PrgP_Passes': 'str', 'Carries_Carries': 'str', 'PrgC_Carries': 'str', 'Att_Take_Ons': 'str', 'Succ_Take_Ons': 'str', 'Fls': 'object', 'Fld': 'object', 'Off': 'object', 'Crs': 'object', 'TklW': 'object', 'OG': 'object', 'PKwon': 'object', 'PKcon': 'object', 'Competition_Name': 'str', 'Gender': 'str', 'Country': 'str', 'Tier': 'str', 'Season_End_Year': 'int32'}
```

```
ENG rows 8464 | matches 279 | rows and matches by season: {2025: (7246, 239), 2026: (1218, 40)} | latest 2025-09-14
ESP rows 8163 | matches 261 | rows and matches by season: {2025: (6877, 220), 2026: (1286, 41)} | latest 2025-09-15
FRA rows 6659 | matches 216 | rows and matches by season: {2025: (5540, 180), 2026: (1119, 36)} | latest 2025-09-14
GER rows 6469 | matches 207 | rows and matches by season: {2025: (5625, 180), 2026: (844, 27)} | latest 2025-09-14
ITA rows 8087 | matches 259 | rows and matches by season: {2025: (7138, 229), 2026: (949, 30)} | latest 2025-09-15
```

```
defense_p rows 83515 | cols 49 | has Pos True | has Min True | matches by season: {2018: 380, 2019: 378, 2020: 380, 2021: 380, 2022: 379, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
keeper_p rows 5938 | cols 52 | has Pos False | has Min True | matches by season: {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
misc_p rows 81328 | cols 49 | has Pos True | has Min True | matches by season: {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 305, 2023: 373, 2024: 380, 2025: 239, 2026: 40}
passing_p rows 83613 | cols 55 | has Pos True | has Min True | matches by season: {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
passing_types_p rows 83613 | cols 48 | has Pos True | has Min True | matches by season: {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
possession_p rows 81667 | cols 55 | has Pos True | has Min True | matches by season: {2018: 380, 2019: 380, 2020: 310, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
```

| Item | Value |
|---|---|
| Files | `{ENG,ESP,FRA,GER,ITA}_M_1st_{stat type}_player_advanced_match_stats` |
| Stat types used | `passing`, `passing_types`, `defense`, `possession`, `misc`. `keeper` has no `Pos`, and `summary` is too short. |
| Formats | `.rds` and `.csv`. `.rds` used, so the byte-level check could run. |
| Substitution events | `fb_match_summary`: `.rds`, except England, where only `.csv` is listed for the men's top division |
| Last update | Stat files 2025-09-16 and 2025-09-17. Event files 2025-02-13. |
| Seasons | Season end years 2018 to 2026. 2025 and 2026 are partial. |
| Licence | None found, as shown in the shots report |

## Task 2: download and data-only check

Sizes and hashes for all 36 downloaded files, in `~/sandbox/wfr`:

```
$ shasum -a 256 <every downloaded file>, compared with the GitHub digest. Result, bytes, SHA-256, file. NO_DIGEST = GitHub reports null; size is compared instead.
MATCH 8041149 ad84fac6b4ecae9376ae3921f4f844ce07ae64d8c7772764ce83491093468211 ENG_M_1st_summary_player_advanced_match_stats.rds
MATCH 6938232 8b9316317b3e123f3e99fce45cebeb42e58b8390b6cd64fdd2d9b76109f9284b ESP_M_1st_summary_player_advanced_match_stats.rds
MATCH 6111691 7f035a2ebdb5705decaf4ddd03eb5a48324240c2b9bae8c64fc31a0e9c955b73 FRA_M_1st_summary_player_advanced_match_stats.rds
MATCH 6407769 7c15f85c8e02d3181e15bb138b9c002060d79b5017e69bd91f1ad6225e23daa9 GER_M_1st_summary_player_advanced_match_stats.rds
MATCH 7337049 7804d70227fbce3c338c002a95d6d47f2de51a31b42f7e035ad61412da5127a4 ITA_M_1st_summary_player_advanced_match_stats.rds
MATCH 77880394 9cc109613af0c89624ffdf845dcffcb5e1c48b779d160fd4a592fd7c4f6dcf1f ENG_M_1st_passing_player_advanced_match_stats.rds
MATCH 71563880 0915ccb4f6c964f7f3b5d829b9a6079c4bc79a0bcee6f1dc4777fb0a3a020230 ESP_M_1st_passing_player_advanced_match_stats.rds
MATCH 71835961 9312d576021d26b5ea8c14a6cdee28638c118e22a921bf6c861afd6eec6f2623 FRA_M_1st_passing_player_advanced_match_stats.rds
MATCH 65218621 64f2488bf5358bb7011368d047def48c099f44244e3642bd9fb4b0aa5a1e2fc4 GER_M_1st_passing_player_advanced_match_stats.rds
MATCH 79346587 96e8e99ce2b8f7cb91d6af87752ce0dd363d8f1627ccfe7f9a14ac25d575ca43 ITA_M_1st_passing_player_advanced_match_stats.rds
MATCH 68473878 6c6edcb327338fb1fdc2fcab428dbbb47ed9cc401b91df3146edb689cb02a6d6 ESP_M_1st_defense_player_advanced_match_stats.rds
MATCH 68494697 e06350efd8e4e4f7bf6b729b78399a012176fc598121f2772b4b9660027f8b9f ESP_M_1st_misc_player_advanced_match_stats.rds
MATCH 69865362 01a1a30460e92e7ce362bab5338907f52504d1e120b1a05d7293f1f09256f0e4 ESP_M_1st_passing_types_player_advanced_match_stats.rds
MATCH 67454103 00bcb883f245a4c73c61851bee7bb4818d66f2bd97844ba94c5e54a715bc03fe ESP_M_1st_possession_player_advanced_match_stats.rds
MATCH 64436008 9948a5e024dbc37dc7231f870604f97f0bc2813b23d20a7152a4784808a04e32 FRA_M_1st_defense_player_advanced_match_stats.rds
MATCH 64093040 aafe3c5e59d8ba35e5510a4143bc1eb0bd6af62e721bf2bb5426687abc0d3e2d FRA_M_1st_misc_player_advanced_match_stats.rds
MATCH 71337372 f071c00d319a8a8562be8164fc6347dcbb9737dcf1d3f939cc8ff96f633f5ae6 FRA_M_1st_passing_types_player_advanced_match_stats.rds
MATCH 75759965 39539d465b5a21253d0540155316b73c8653d5ed6e47ef6400ceadc212e9238f FRA_M_1st_possession_player_advanced_match_stats.rds
MATCH 59848163 6c5286f084a7c69b94264585accc1cfaab022c63f0bd130da08bdb0068722ca0 GER_M_1st_defense_player_advanced_match_stats.rds
MATCH 59669628 eacb8d76af227e2a60f1ed8b70e967da6a23398f254b229809ac45919198de03 GER_M_1st_misc_player_advanced_match_stats.rds
MATCH 59106802 f79a66cad851e0df013d149436372320191b848864ff5119b9f304acd5bb73ac GER_M_1st_passing_types_player_advanced_match_stats.rds
MATCH 63201463 9506d49cd2af4bc48a4fefd1389867363cff207b51c87d0c04b4644645ff2da3 GER_M_1st_possession_player_advanced_match_stats.rds
MATCH 72737361 b75b2819e1dbf6f811fa9b00c6d1b20136692c1acbb374b194e5fa675b70531b ITA_M_1st_defense_player_advanced_match_stats.rds
MATCH 61174721 fdbaaef29028309c925c2fe870101db8be8711b475f368acbc6951375ed4cbbb ITA_M_1st_misc_player_advanced_match_stats.rds
MATCH 78742349 e0fae3c5ce6eaa8260b610505a0f201dd32938e0518a3446525faac1ee275e72 ITA_M_1st_passing_types_player_advanced_match_stats.rds
MATCH 81039751 2a09ba7cf18e3e83f5b7332a5fd36f2728607fb6a04b56d50f95b664af8bdd3a ITA_M_1st_possession_player_advanced_match_stats.rds
MATCH 71356210 a7ef11574455db1aa086377ef90a6a87239365538c3ee7e038725d9bfe47d9b9 ENG_M_1st_defense_player_advanced_match_stats.rds
MATCH 5119293 963ea839deabf5866bf25f1c21b49124b0fc79b71254f9b6ad1b199ee78c063c ENG_M_1st_keeper_player_advanced_match_stats.rds
MATCH 69500306 9c8b96b0bf1166c51cd996b0b16eaebfaa633c0981d028feca71d6ea04e738c2 ENG_M_1st_misc_player_advanced_match_stats.rds
MATCH 72714944 26c3cb1c949d29a52be80774ea8c3f181f089ba386ec77658a90049df14005b5 ENG_M_1st_passing_types_player_advanced_match_stats.rds
MATCH 73692648 0380e5719d050847bda441983e8ec9560cd6529d74d74a10efd6cb36403d0c7d ENG_M_1st_possession_player_advanced_match_stats.rds
NO_DIGEST_SIZE_MATCH 19135823 50d6f42a81bba279f734439d356e0512ab7e9d2ef9e74db98856dd3db2b45861 ENG_M_1st_match_summary.csv
NO_DIGEST_SIZE_MATCH 28645985 f8d0532f1110f3bdeea10fd6a164c00a1f57c6dcc1d7484f5feb818ba4697c6e ESP_M_1st_match_summary.rds
NO_DIGEST_SIZE_MATCH 23958653 7cb154acdc243cb252a48091fe586b0e7ca0cf85f103b9af2b2677c053eff56c FRA_M_1st_match_summary.rds
NO_DIGEST_SIZE_MATCH 24724588 dc9356a544132e92c6e9831e4d5fbfa176abab82c347209b6380b8014fdbb913 GER_M_1st_match_summary.rds
NO_DIGEST_SIZE_MATCH 27662572 2b09168c196fc4004b6ba3992c30f1883589bc50d2c28570389a70166ad56a2c ITA_M_1st_match_summary.rds
```

The same walker as the shots vetting (`tools/rds_walk.py`), on every `.rds`:

```
$ venv/bin/python3 -I tools/rds_walk.py files_fb/*.rds
ENG_M_1st_summary_player_advanced_match_stats.rds: bytes=8041149 format_version=2 consumed=8041149 trailing=0 types={'CHAR': 431746, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 7, 'REF': 2, 'STR': 57, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ESP_M_1st_summary_player_advanced_match_stats.rds: bytes=6938232 format_version=2 consumed=6938232 trailing=0 types={'CHAR': 212320, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 32, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_summary_player_advanced_match_stats.rds: bytes=6111691 format_version=2 consumed=6111691 trailing=0 types={'CHAR': 173224, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 40, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_summary_player_advanced_match_stats.rds: bytes=6407769 format_version=2 consumed=6407769 trailing=0 types={'CHAR': 168284, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 40, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_summary_player_advanced_match_stats.rds: bytes=7337049 format_version=2 consumed=7337049 trailing=0 types={'CHAR': 412527, 'INT': 17, 'LGL': 3, 'LIST': 8, 'NIL': 2, 'REAL': 7, 'REF': 2, 'STR': 57, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
$ venv/bin/python3 -I tools/rds_walk.py files_passing/*.rds
ENG_M_1st_passing_player_advanced_match_stats.rds: bytes=77880394 format_version=2 consumed=77880394 trailing=0 types={'CHAR': 3846277, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 9, 'REF': 2, 'STR': 52, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ESP_M_1st_passing_player_advanced_match_stats.rds: bytes=71563880 format_version=2 consumed=71563880 trailing=0 types={'CHAR': 3822955, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 9, 'REF': 2, 'STR': 52, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_passing_player_advanced_match_stats.rds: bytes=71835961 format_version=2 consumed=71835961 trailing=0 types={'CHAR': 3632853, 'INT': 26, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 10, 'REF': 2, 'STR': 52, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_passing_player_advanced_match_stats.rds: bytes=65218621 format_version=2 consumed=65218621 trailing=0 types={'CHAR': 3214007, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 9, 'REF': 2, 'STR': 52, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_passing_player_advanced_match_stats.rds: bytes=79346587 format_version=2 consumed=79346587 trailing=0 types={'CHAR': 3996023, 'INT': 26, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 10, 'REF': 2, 'STR': 52, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
$ venv/bin/python3 -I tools/rds_walk.py files_fb_other/*.rds files_fb_eng/*.rds files_events/*.rds
ESP_M_1st_defense_player_advanced_match_stats.rds: bytes=68473878 format_version=2 consumed=68473878 trailing=0 types={'CHAR': 2270263, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ESP_M_1st_misc_player_advanced_match_stats.rds: bytes=68494697 format_version=2 consumed=68494697 trailing=0 types={'CHAR': 2270913, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ESP_M_1st_passing_types_player_advanced_match_stats.rds: bytes=69865362 format_version=2 consumed=69865362 trailing=0 types={'CHAR': 3933072, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 3, 'REF': 2, 'STR': 51, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ESP_M_1st_possession_player_advanced_match_stats.rds: bytes=67454103 format_version=2 consumed=67454103 trailing=0 types={'CHAR': 3452889, 'INT': 16, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 10, 'REF': 2, 'STR': 51, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_defense_player_advanced_match_stats.rds: bytes=64436008 format_version=2 consumed=64436008 trailing=0 types={'CHAR': 3237970, 'INT': 15, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 8, 'REF': 2, 'STR': 47, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_misc_player_advanced_match_stats.rds: bytes=64093040 format_version=2 consumed=64093040 trailing=0 types={'CHAR': 3494598, 'INT': 12, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 5, 'REF': 2, 'STR': 50, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_passing_types_player_advanced_match_stats.rds: bytes=71337372 format_version=2 consumed=71337372 trailing=0 types={'CHAR': 2053386, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 38, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_possession_player_advanced_match_stats.rds: bytes=75759965 format_version=2 consumed=75759965 trailing=0 types={'CHAR': 2053393, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 45, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_defense_player_advanced_match_stats.rds: bytes=59848163 format_version=2 consumed=59848163 trailing=0 types={'CHAR': 1816641, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_misc_player_advanced_match_stats.rds: bytes=59669628 format_version=2 consumed=59669628 trailing=0 types={'CHAR': 1811441, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_passing_types_player_advanced_match_stats.rds: bytes=59106802 format_version=2 consumed=59106802 trailing=0 types={'CHAR': 1811024, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 22, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_possession_player_advanced_match_stats.rds: bytes=63201463 format_version=2 consumed=63201463 trailing=0 types={'CHAR': 1816647, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 29, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_defense_player_advanced_match_stats.rds: bytes=72737361 format_version=2 consumed=72737361 trailing=0 types={'CHAR': 3570730, 'INT': 19, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 8, 'REF': 2, 'STR': 47, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_misc_player_advanced_match_stats.rds: bytes=61174721 format_version=2 consumed=61174721 trailing=0 types={'CHAR': 2021209, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_passing_types_player_advanced_match_stats.rds: bytes=78742349 format_version=2 consumed=78742349 trailing=0 types={'CHAR': 2258656, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 38, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_possession_player_advanced_match_stats.rds: bytes=81039751 format_version=2 consumed=81039751 trailing=0 types={'CHAR': 3909160, 'INT': 31, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 11, 'REF': 2, 'STR': 51, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ENG_M_1st_defense_player_advanced_match_stats.rds: bytes=71356210 format_version=2 consumed=71356210 trailing=0 types={'CHAR': 2171463, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ENG_M_1st_keeper_player_advanced_match_stats.rds: bytes=5119293 format_version=2 consumed=5119293 trailing=0 types={'CHAR': 148526, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 27, 'REF': 2, 'STR': 31, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ENG_M_1st_misc_player_advanced_match_stats.rds: bytes=69500306 format_version=2 consumed=69500306 trailing=0 types={'CHAR': 2114601, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 23, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ENG_M_1st_passing_types_player_advanced_match_stats.rds: bytes=72714944 format_version=2 consumed=72714944 trailing=0 types={'CHAR': 3762657, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 3, 'REF': 2, 'STR': 51, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ENG_M_1st_possession_player_advanced_match_stats.rds: bytes=73692648 format_version=2 consumed=73692648 trailing=0 types={'CHAR': 2123421, 'INT': 11, 'LGL': 1, 'LIST': 8, 'NIL': 2, 'REAL': 29, 'REF': 2, 'STR': 32, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ESP_M_1st_match_summary.rds: bytes=28645985 format_version=2 consumed=28645985 trailing=0 types={'CHAR': 1077009, 'INT': 11, 'LGL': 2, 'LIST': 8, 'NIL': 2, 'REAL': 8, 'REF': 2, 'STR': 30, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
FRA_M_1st_match_summary.rds: bytes=23958653 format_version=2 consumed=23958653 trailing=0 types={'CHAR': 900129, 'INT': 11, 'LGL': 2, 'LIST': 8, 'NIL': 2, 'REAL': 8, 'REF': 2, 'STR': 30, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
GER_M_1st_match_summary.rds: bytes=24724588 format_version=2 consumed=24724588 trailing=0 types={'CHAR': 833865, 'INT': 11, 'LGL': 2, 'LIST': 8, 'NIL': 2, 'REAL': 8, 'REF': 2, 'STR': 30, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
ITA_M_1st_match_summary.rds: bytes=27662572 format_version=2 consumed=27662572 trailing=0 types={'CHAR': 1036377, 'INT': 11, 'LGL': 2, 'LIST': 8, 'NIL': 2, 'REAL': 8, 'REF': 2, 'STR': 30, 'SYM': 6, 'VEC': 2} CODE_TYPES=0
```

Every file was read to its last byte (`trailing=0`) with no code types, so all are data-only. Positive control, with files that must be refused and one plain vector that must pass:

```
closure: exit=1 closure.rds: CODE TYPE FOUND: CLOSURE
language: exit=1 language.rds: CODE TYPE FOUND: LANG
bytecode: exit=1 bytecode.rds: CODE TYPE FOUND: BYTECODE
environment: exit=1 environment.rds: CODE TYPE FOUND: ENV
plain int vector: exit=0 plain_int_vector.rds: bytes=30 format_version=2 consumed=30 trailing=0 types={'INT': 1} CODE_TYPES=0
```

The one CSV:

```
$ grep -cE "(^|,)\"?[=+@]" files_events/ENG_M_1st_match_summary.csv   (formula-style cells in the one CSV file)
0
```

No new package was installed. The venv is the one vetted in the shots report.

## Task 3: coverage

Gap filling across stat types, then the union:

```
ENG defense True True {2018: 380, 2019: 378, 2020: 380, 2021: 380, 2022: 379, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
ENG misc True True {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 305, 2023: 373, 2024: 380, 2025: 239, 2026: 40}
ENG passing_types True True {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
ENG possession True True {2018: 380, 2019: 380, 2020: 310, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
ESP defense True True {2018: 380, 2019: 378, 2020: 380, 2021: 380, 2022: 380, 2023: 379, 2024: 380, 2025: 220, 2026: 41}
ESP misc True True {2018: 380, 2019: 380, 2020: 378, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 220, 2026: 41}
ESP passing_types True True {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 220, 2026: 41}
ESP possession True True {2018: 380, 2019: 380, 2020: 10, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 220, 2026: 41}
FRA defense True True {2018: 380, 2019: 380, 2020: 278, 2021: 377, 2022: 380, 2023: 370, 2024: 306, 2025: 180, 2026: 36}
FRA misc True True {2018: 380, 2019: 380, 2020: 279, 2021: 380, 2022: 380, 2023: 380, 2024: 306, 2025: 180, 2026: 36}
FRA passing_types True True {2018: 380, 2019: 380, 2020: 278, 2021: 377, 2022: 380, 2023: 370, 2024: 306, 2025: 180, 2026: 36}
FRA possession True True {2018: 380, 2019: 380, 2020: 278, 2021: 377, 2022: 380, 2023: 370, 2024: 306, 2025: 180, 2026: 36}
GER defense True True {2018: 306, 2019: 306, 2020: 306, 2021: 306, 2022: 305, 2023: 306, 2024: 306, 2025: 180, 2026: 27}
GER misc True True {2018: 306, 2019: 306, 2020: 306, 2021: 306, 2022: 305, 2023: 306, 2024: 300, 2025: 180, 2026: 27}
GER passing_types True True {2018: 306, 2019: 306, 2020: 306, 2021: 305, 2022: 299, 2023: 306, 2024: 306, 2025: 180, 2026: 27}
GER possession True True {2018: 306, 2019: 306, 2020: 306, 2021: 306, 2022: 305, 2023: 306, 2024: 306, 2025: 180, 2026: 27}
ITA defense True True {2018: 380, 2019: 380, 2020: 377, 2021: 376, 2022: 379, 2023: 381, 2024: 379, 2025: 228, 2026: 30}
ITA misc True True {2018: 380, 2019: 380, 2020: 379, 2021: 379, 2022: 380, 2023: 381, 2024: 74, 2025: 228, 2026: 30}
ITA passing_types True True {2018: 380, 2019: 380, 2020: 377, 2021: 376, 2022: 379, 2023: 370, 2024: 383, 2025: 228, 2026: 30}
ITA possession True True {2018: 380, 2019: 380, 2020: 377, 2021: 376, 2022: 379, 2023: 370, 2024: 383, 2025: 228, 2026: 30}
ENG passing True True {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 380, 2025: 239, 2026: 40}
ESP passing True True {2018: 380, 2019: 380, 2020: 380, 2021: 239, 2022: 380, 2023: 380, 2024: 380, 2025: 220, 2026: 41}
FRA passing True True {2018: 380, 2019: 380, 2020: 278, 2021: 377, 2022: 380, 2023: 370, 2024: 306, 2025: 180, 2026: 36}
GER passing True True {2018: 306, 2019: 306, 2020: 306, 2021: 306, 2022: 305, 2023: 306, 2024: 306, 2025: 180, 2026: 27}
ITA passing True True {2018: 380, 2019: 380, 2020: 377, 2021: 376, 2022: 379, 2023: 370, 2024: 383, 2025: 228, 2026: 30}

union of stat types, matches per season end year
                 ENG  ESP  FRA  GER  ITA
Season_End_Year                         
2018             380  380  380  306  380
2019             380  380  380  306  380
2020             380  380  279  306  380
2021             380  380  380  306  379
2022             380  380  380  305  380
2023             380  380  380  306  381
2024             380  380  306  306  383
2025             239  220  180  180  228
2026              40   41   36   27   30
```

```
$ venv/bin/python3 -I tools/fb_union.py .. ../out_fb/union.pkl
ENG passing: matches in file 2939 | matches added 2939
ENG passing_types vs passing: common rows 83613 | Pos differs 7 | Min differs 0
ENG passing_types: matches in file 2939 | matches added 0
ENG defense vs passing: common rows 83514 | Pos differs 10 | Min differs 6
ENG defense: matches in file 2936 | matches added 0
ENG possession vs passing: common rows 81666 | Pos differs 18 | Min differs 12
ENG possession: matches in file 2869 | matches added 0
ENG misc vs passing: common rows 81326 | Pos differs 18 | Min differs 20
ENG misc: matches in file 2857 | matches added 0
ESP passing: matches in file 2780 | matches added 2780
ESP passing_types vs passing: common rows 83106 | Pos differs 24 | Min differs 0
ESP passing_types: matches in file 2921 | matches added 141
ESP defense vs passing: common rows 82688 | Pos differs 48 | Min differs 2
ESP defense: matches in file 2918 | matches added 0
ESP possession vs passing: common rows 72435 | Pos differs 24 | Min differs 0
ESP possession: matches in file 2551 | matches added 0
ESP misc vs passing: common rows 82893 | Pos differs 40 | Min differs 0
ESP misc: matches in file 2919 | matches added 0
FRA passing: matches in file 2687 | matches added 2687
FRA passing_types vs passing: common rows 78973 | Pos differs 2 | Min differs 0
FRA passing_types: matches in file 2687 | matches added 0
FRA defense vs passing: common rows 78971 | Pos differs 2 | Min differs 2
FRA defense: matches in file 2687 | matches added 0
FRA possession vs passing: common rows 78970 | Pos differs 2 | Min differs 2
FRA possession: matches in file 2687 | matches added 0
FRA misc vs passing: common rows 78697 | Pos differs 66 | Min differs 11
FRA misc: matches in file 2701 | matches added 14
GER passing: matches in file 2348 | matches added 2348
GER passing_types vs passing: common rows 69652 | Pos differs 15 | Min differs 0
GER passing_types: matches in file 2341 | matches added 0
GER defense vs passing: common rows 69676 | Pos differs 29 | Min differs 1
GER defense: matches in file 2348 | matches added 0
GER possession vs passing: common rows 69868 | Pos differs 15 | Min differs 0
GER possession: matches in file 2348 | matches added 0
GER misc vs passing: common rows 69654 | Pos differs 43 | Min differs 0
GER misc: matches in file 2342 | matches added 0
ITA passing: matches in file 2903 | matches added 2903
ITA passing_types vs passing: common rows 86868 | Pos differs 2 | Min differs 0
ITA passing_types: matches in file 2903 | matches added 0
ITA defense vs passing: common rows 86682 | Pos differs 61 | Min differs 0
ITA defense: matches in file 2910 | matches added 11
ITA possession vs passing: common rows 86868 | Pos differs 2 | Min differs 0
ITA possession: matches in file 2903 | matches added 0
ITA misc vs passing: common rows 77081 | Pos differs 100 | Min differs 3
ITA misc: matches in file 2611 | matches added 7

rows 407716 | matches 13830 | duplicates on match, team, player: 0

=== matches per season end year, union
lg      ENG  ESP  FRA  GER  ITA
season                         
2018    380  380  380  306  380
2019    380  380  380  306  380
2020    380  380  279  306  380
2021    380  380  380  306  379
2022    380  380  380  305  380
2023    380  380  380  306  381
2024    380  380  306  306  383
2025    239  220  180  180  228
2026     40   41   36   27   30

=== same home and away team, same season, under different URLs
lg   season
ITA  2023      1
     2024      4

=== Matchweek labels with numbers masked
Matchweek
Premier League (Matchweek #)        2939
La Liga (Matchweek #)               2921
Serie A (Matchweek #)               2920
Ligue # (Matchweek #)               2701
Fußball-Bundesliga (Matchweek #)    2348
Serie A (Relegation tie-breaker)       1

=== expected and actual, excess or shortfall
FRA 2020: 279 of 380
ITA 2021: 379 of 380
GER 2022: 305 of 306
ITA 2023: 381 of 380
ITA 2024: 383 of 380
```

| Season | Premier League | La Liga | Ligue 1 | Bundesliga | Serie A |
|---|---|---|---|---|---|
| Expected | 380 | 380 | 380, or 306 from 2023/24 | 306 | 380 |
| 2017/18 | 380 | 380 | 380 | 306 | 380 |
| 2018/19 | 380 | 380 | 380 | 306 | 380 |
| 2019/20 | 380 | 380 | 279, stopped early | 306 | 380 |
| 2020/21 | 380 | 380 | 380 | 306 | **379** |
| 2021/22 | 380 | 380 | 380 | **305** | 380 |
| 2022/23 | 380 | 380 | 380 | 306 | **381** |
| 2023/24 | 380 | 380 | 306 | 306 | **383** |
| 2024/25, to 2025-02-03 | **239** | **220** | **180** | **180** | **228** |
| 2025/26, to 2025-09-15 | 40 | 41 | 36 | 27 | 30 |

Across all five leagues, the first season is 2017/18 and the last is 2025/26, which is partial. Total 407,716 rows and 13,830 matches.

```
$ venv/bin/python3 -I tools/fb_profile.py ../out_fb/union.pkl

=== nulls (all files)
MatchURL            0
League              0
Match_Date          0
Team                0
Home_Away           0
Player              0
Player_Href         0
Player_Num         31
Pos                 0
Min                 6
Season_End_Year     0
Min not numeric: 6 | date not parsed: 0

=== coverage per league
ENG: first_season_end=2018 last_season_end=2026 first_date=2017-08-11 latest_date=2025-09-14 rows=83613 matches=2939
ESP: first_season_end=2018 last_season_end=2026 first_date=2017-08-18 latest_date=2025-09-15 rows=87400 matches=2921
FRA: first_season_end=2018 last_season_end=2026 first_date=2017-08-04 latest_date=2025-09-14 rows=79407 matches=2701
GER: first_season_end=2018 last_season_end=2026 first_date=2017-08-18 latest_date=2025-09-14 rows=69868 matches=2348
ITA: first_season_end=2018 last_season_end=2026 first_date=2017-08-19 latest_date=2025-09-15 rows=87428 matches=2921

=== matches per season end year
lg      ENG  ESP  FRA  GER  ITA
season                         
2018    380  380  380  306  380
2019    380  380  380  306  380
2020    380  380  279  306  380
2021    380  380  380  306  379
2022    380  380  380  305  380
2023    380  380  380  306  381
2024    380  380  306  306  383
2025    239  220  180  180  228
2026     40   41   36   27   30

=== latest match date per season end year
lg             ENG         ESP         FRA         GER         ITA
season                                                            
2018    2018-05-13  2018-05-20  2018-05-19  2018-05-12  2018-05-20
2019    2019-05-12  2019-05-19  2019-05-24  2019-05-18  2019-05-26
2020    2020-07-26  2020-07-19  2020-03-08  2020-06-27  2020-08-02
2021    2021-05-23  2021-05-23  2021-05-23  2021-05-22  2021-05-23
2022    2022-05-22  2022-05-22  2022-05-21  2022-05-14  2022-05-22
2023    2023-05-28  2023-06-04  2023-06-03  2023-05-27  2023-06-11
2024    2024-05-19  2024-05-26  2024-05-19  2024-05-18  2024-05-26
2025    2025-02-03  2025-02-03  2025-02-02  2025-02-02  2025-02-03
2026    2025-09-14  2025-09-15  2025-09-14  2025-09-14  2025-09-15

=== League label values: {'ENG': 1, 'ESP': 1, 'FRA': 1, 'GER': 1, 'ITA': 1}

=== Pos: distinct=993 (every value is listed with its count in fb_join.py section C)

=== tokens per Pos value, rows
n_tok
1    358658
2     45608
3      3340
4       108
5         2
rows with several positions: 49058 of 407716 (12.03%)

=== single tokens, rows containing each
Pos
CB    74141
FW    65259
CM    60053
DM    28378
RB    28344
AM    28121
GK    27983
LB    27756
RM    25916
LM    25861
RW    24797
LW    24795
WB    18888
MF       27
DF       17

=== first token, rows
Pos
CB    71461
FW    60585
CM    51898
GK    27977
RB    25362
LB    25099
DM    23772
AM    23670
RW    20538
LW    20502
LM    20175
RM    20172
WB    16469
MF       19
DF       17

=== rows with several positions by season
season
2018    13.21%
2019    15.57%
2020    13.37%
2021    10.65%
2022    11.18%
2023    10.42%
2024     9.89%
2025    12.56%
2026    13.26%
Sub or bench label in Pos: 0

=== Min: per player per match
rows 407716 | duplicates on match, team, player href: 0 | href null: 0
Min: <=0 0 | >90 1 | >120 0 | max 91.0
team-matches: 27659 | total minutes 980-1000: 26021 | below 980: 1638 | above 1000: 0
players per team-match, distribution: {11: 42, 12: 283, 13: 1800, 14: 11969, 15: 4189, 16: 9337, 17: 38, 19: 1}

=== is a substitute marked?
columns naming start, sub, lineup, bench: []
Player cells with leading whitespace: 0 | with non-breaking space anywhere: 0
not-indented players per team-match: {11: 42, 12: 283, 13: 1800, 14: 11969, 15: 4189, 16: 9376} | team-matches with exactly 11: 42 of 27659
team-matches with exactly 11 by season: {2018: 6, 2019: 6, 2020: 7, 2021: 9, 2022: 7, 2023: 2, 2024: 4, 2025: 1, 2026: 0}
not-indented rows, Min <45: 96859 | indented rows, Min >=80: 0
not-indented rows sum to full team minutes? first row per team-match always not indented: True
```

## Task 4: position field

- **Column:** `Pos`. It has 0 nulls and **993 distinct values**, built from 15 single labels.
- **Several positions in one match: YES.** 49,058 of 407,716 rows (12.03%) hold 2 to 5 positions, such as `FW,LW`. Minutes are not split between them.

Every value is listed with its count and mapping in Task 6.

## Task 5: minutes field

**`Min` is present per player per match**, with 6 nulls and no duplicate player rows within a match. Team totals are 980 to 1,000 minutes on 26,021 of 27,659 team-matches.

| Sum per player-season vs HF, 2017/18 to 2023/24 | Keys | Same | Within 5 | Within 90 |
|---|---|---|---|---|
| HF Understat minutes, name join | 17,347 | 11.40% | 43.59% | 99.29% |
| HF Understat minutes, HF 900+ | 10,380 | 10.86% | 38.58% | 98.99% |
| HF FBref minutes, id join | 19,052 | 95.58% | 98.67% | 99.89% |
| HF FBref minutes, HF 900+ | 11,320 | 94.74% | 98.39% | 99.86% |

- **900-minute gate:** FBref and HF Understat agree on 17,273 of 17,347 keys.
- **Trend:** agreement with Understat falls with time. Within 90 minutes it is 99.88% in 2017/18 and 96.99% in 2023/24.
- **2024/25:** FBref stops in February, so only 27.36% are within 90 minutes, and these minutes cannot be used for that season.
- **Name join coverage:** 11,781 of 12,834 HF keys at 900+ minutes were joined (91.80%). This count includes 2024/25.

Raw output is under Task 9, in the `fb_join.py` block, section B.

## Task 6: proposed mapping

This table is a proposal. Nothing in the plan has changed.

| FBref label | Rows containing it | Maps to | Clean? |
|---|---|---|---|
| `FW` | 65,259 | FW | Yes |
| `LW` | 24,795 | FWL or AML | **No:** Pool membership is clear, but the side of the code is not |
| `RW` | 24,797 | FWR or AMR | **No:** same as `LW` |
| `AM` | 28,121 | AMC | **No:** Pool membership is clear, but FBref states no left, centre or right |
| `LM` | 25,861 | excluded | **No:** Q17 decision |
| `RM` | 25,916 | excluded | **No:** Q17 decision |
| `CM` | 60,053 | excluded | Yes |
| `DM` | 28,378 | excluded | Yes |
| `CB` | 74,141 | excluded | Yes |
| `LB` | 27,756 | excluded | Yes |
| `RB` | 28,344 | excluded | Yes |
| `WB` | 18,888 | excluded | Yes |
| `GK` | 27,983 | excluded | Yes |
| `MF` | 27 | excluded | **No:** generic, could be an attacking midfielder |
| `DF` | 17 | excluded | Yes in effect: generic, but not a Pool position |

**Values with several positions** use the first label, as an assumption:

| Type | Values | Rows |
|---|---|---|
| Every label in the Pool, such as `FW,LW` | 38 | 9,483 |
| Every label excluded, such as `DM,CM` | 294 | 23,600 |
| Mixed: **cannot be mapped cleanly** | 646 | 15,975 |

The list below marks all 993 values. In its note column, "clean" means Pool membership is clear. It says nothing about the exact code for `LW` and `RW` within a composite. `Q17` marks any value that contains `LM` or `RM`.

```
ALL POSITION VALUES: value | rows | maps to (first token) | note
CB | 69014 | excluded | clean
FW | 55207 | FW | clean
CM | 45108 | excluded | clean
GK | 27974 | excluded | clean
RB | 22909 | excluded | clean
LB | 22902 | excluded | clean
DM | 19231 | excluded | clean
AM | 19050 | AMC | code assumed: side not stated
RW | 16271 | FWR/AMR | code unclear: FW side or AM side
LW | 16135 | FWL/AML | code unclear: FW side or AM side
LM | 15604 | excluded | Q17
RM | 15539 | excluded | Q17
WB | 13693 | excluded | clean
DM,CM | 2854 | excluded | clean
CM,DM | 2414 | excluded | clean
RM,CM | 1100 | excluded | Q17
CM,RM | 1023 | excluded | Q17
LM,CM | 1022 | excluded | Q17
FW,AM | 1018 | FW | clean
LW,RW | 995 | FWL/AML | clean
CM,LM | 984 | excluded | Q17
FW,LW | 945 | FW | clean
AM,FW | 938 | AMC | clean
RW,RM | 929 | FWR/AMR | Q17; NOT CLEAN: mixed
RM,LM | 917 | excluded | Q17
LW,LM | 909 | FWL/AML | Q17; NOT CLEAN: mixed
RW,LW | 897 | FWR/AMR | clean
LM,RM | 872 | excluded | Q17
FW,RW | 790 | FW | clean
AM,CM | 753 | AMC | NOT CLEAN: mixed
WB,LB | 748 | excluded | clean
LW,FW | 734 | FWL/AML | clean
WB,RB | 722 | excluded | clean
CB,RB | 713 | excluded | clean
RW,FW | 681 | FWR/AMR | clean
FW,LM | 648 | FW | Q17; NOT CLEAN: mixed
RB,CB | 630 | excluded | clean
FW,RM | 606 | FW | Q17; NOT CLEAN: mixed
LB,CB | 599 | excluded | clean
RM,RW | 599 | excluded | Q17; NOT CLEAN: mixed
LM,LW | 581 | excluded | Q17; NOT CLEAN: mixed
CB,LB | 560 | excluded | clean
CM,AM | 558 | excluded | NOT CLEAN: mixed
FW,CM | 537 | FW | NOT CLEAN: mixed
AM,LW | 536 | AMC | clean
LW,AM | 530 | FWL/AML | clean
AM,RW | 529 | AMC | clean
RW,AM | 526 | FWR/AMR | clean
LB,WB | 507 | excluded | clean
LM,FW | 502 | excluded | Q17; NOT CLEAN: mixed
RB,WB | 474 | excluded | clean
AM,DM | 463 | AMC | NOT CLEAN: mixed
RM,FW | 462 | excluded | Q17; NOT CLEAN: mixed
CM,FW | 433 | excluded | NOT CLEAN: mixed
CM,CB | 426 | excluded | clean
RB,LB | 411 | excluded | clean
DM,AM | 409 | excluded | NOT CLEAN: mixed
AM,LM | 364 | AMC | Q17; NOT CLEAN: mixed
RB,RM | 357 | excluded | Q17
AM,RM | 346 | AMC | Q17; NOT CLEAN: mixed
CB,CM | 345 | excluded | clean
LB,RB | 329 | excluded | clean
RM,RB | 318 | excluded | Q17
LB,LM | 308 | excluded | Q17
LM,LB | 291 | excluded | Q17
LM,DM | 274 | excluded | Q17
LM,AM | 268 | excluded | Q17; NOT CLEAN: mixed
WB,CB | 258 | excluded | clean
DM,CB | 242 | excluded | clean
RM,DM | 240 | excluded | Q17
CB,WB | 236 | excluded | clean
RM,AM | 225 | excluded | Q17; NOT CLEAN: mixed
DM,LM | 217 | excluded | Q17
DM,RM | 201 | excluded | Q17
RB,RW | 194 | excluded | NOT CLEAN: mixed
LW,RM | 193 | FWL/AML | Q17; NOT CLEAN: mixed
RW,LM | 191 | FWR/AMR | Q17; NOT CLEAN: mixed
CB,DM | 190 | excluded | clean
RW,RB | 188 | FWR/AMR | NOT CLEAN: mixed
AM,WB | 181 | AMC | NOT CLEAN: mixed
LW,LB | 173 | FWL/AML | NOT CLEAN: mixed
LB,LW | 164 | excluded | NOT CLEAN: mixed
WB,RM | 157 | excluded | Q17
WB,AM | 153 | excluded | NOT CLEAN: mixed
WB,CM | 143 | excluded | clean
RM,LW | 141 | excluded | Q17; NOT CLEAN: mixed
WB,LM | 140 | excluded | Q17
RW,CM | 140 | FWR/AMR | NOT CLEAN: mixed
CM,WB | 138 | excluded | clean
LW,CM | 134 | FWL/AML | NOT CLEAN: mixed
LM,RW | 131 | excluded | Q17; NOT CLEAN: mixed
FW,DM | 131 | FW | NOT CLEAN: mixed
RW,WB | 129 | FWR/AMR | NOT CLEAN: mixed
RM,WB | 123 | excluded | Q17
CM,RB | 120 | excluded | clean
LW,WB | 117 | FWL/AML | NOT CLEAN: mixed
CM,RW | 116 | excluded | NOT CLEAN: mixed
CM,LW | 115 | excluded | NOT CLEAN: mixed
RW,DM | 114 | FWR/AMR | NOT CLEAN: mixed
LW,DM | 110 | FWL/AML | NOT CLEAN: mixed
FW,WB | 105 | FW | NOT CLEAN: mixed
LM,WB | 103 | excluded | Q17
DM,RW | 98 | excluded | NOT CLEAN: mixed
RB,CM | 98 | excluded | clean
DM,FW | 94 | excluded | NOT CLEAN: mixed
CB,FW | 93 | excluded | NOT CLEAN: mixed
FW,CB | 86 | FW | NOT CLEAN: mixed
WB,FW | 83 | excluded | NOT CLEAN: mixed
WB,RW | 83 | excluded | NOT CLEAN: mixed
DM,LW | 80 | excluded | NOT CLEAN: mixed
DM,RB | 79 | excluded | clean
WB,LW | 76 | excluded | NOT CLEAN: mixed
RM,CB | 73 | excluded | Q17
CM,LB | 71 | excluded | clean
CB,RM | 70 | excluded | Q17
FW,RB | 62 | FW | NOT CLEAN: mixed
LM,RB | 62 | excluded | Q17
RB,DM | 59 | excluded | clean
LB,CM | 57 | excluded | clean
LM,CB | 55 | excluded | Q17
LW,RB | 54 | FWL/AML | NOT CLEAN: mixed
RM,LB | 49 | excluded | Q17
RB,LM | 46 | excluded | Q17
CB,LM | 46 | excluded | Q17
RW,LB | 44 | FWR/AMR | NOT CLEAN: mixed
CB,RW | 43 | excluded | NOT CLEAN: mixed
LB,RM | 43 | excluded | Q17
CB,AM | 43 | excluded | NOT CLEAN: mixed
CB,LW | 40 | excluded | NOT CLEAN: mixed
RW,CB | 40 | FWR/AMR | NOT CLEAN: mixed
AM,DM,CM | 39 | AMC | NOT CLEAN: mixed
AM,CB | 37 | AMC | NOT CLEAN: mixed
LM,DM,CM | 35 | excluded | Q17
RB,LW | 35 | excluded | NOT CLEAN: mixed
LW,CB | 33 | FWL/AML | NOT CLEAN: mixed
FW,LB | 32 | FW | NOT CLEAN: mixed
LB,DM | 31 | excluded | clean
RW,LW,LM | 31 | FWR/AMR | Q17; NOT CLEAN: mixed
RB,FW | 31 | excluded | NOT CLEAN: mixed
LB,FW | 30 | excluded | NOT CLEAN: mixed
RM,CM,DM | 29 | excluded | Q17
DM,LB | 29 | excluded | clean
RM,CM,LM | 27 | excluded | Q17
LM,CM,DM | 27 | excluded | Q17
DM,CM,LM | 26 | excluded | Q17
AM,RB | 26 | AMC | NOT CLEAN: mixed
LM,CM,RM | 26 | excluded | Q17
FW,LW,LM | 25 | FW | Q17; NOT CLEAN: mixed
LB,RW | 25 | excluded | NOT CLEAN: mixed
DM,WB | 25 | excluded | clean
FW,LW,AM | 24 | FW | clean
LB,AM | 24 | excluded | NOT CLEAN: mixed
RM,LM,CM | 24 | excluded | Q17
RW,LW,FW | 24 | FWR/AMR | clean
RM,DM,CM | 24 | excluded | Q17
LM,RM,CM | 23 | excluded | Q17
CM,LM,RM | 21 | excluded | Q17
WB,DM | 21 | excluded | clean
FW,RW,RM | 21 | FW | Q17; NOT CLEAN: mixed
FW,RW,LW | 20 | FW | clean
AM,RW,LW | 20 | AMC | clean
AM,LM,CM | 20 | AMC | Q17; NOT CLEAN: mixed
AM,LB | 20 | AMC | NOT CLEAN: mixed
FW,LW,RW | 20 | FW | clean
FW,RM,LM | 20 | FW | Q17; NOT CLEAN: mixed
FW,AM,LW | 19 | FW | clean
LW,RM,RW | 19 | FWL/AML | Q17; NOT CLEAN: mixed
LW,RW,AM | 19 | FWL/AML | clean
MF | 19 | excluded | generic label
AM,LW,RW | 19 | AMC | clean
FW,LM,LW | 18 | FW | Q17; NOT CLEAN: mixed
CM,DM,RM | 18 | excluded | Q17
AM,CM,DM | 18 | AMC | NOT CLEAN: mixed
LW,RW,FW | 18 | FWL/AML | clean
CM,LM,DM | 18 | excluded | Q17
LM,FW,RM | 18 | excluded | Q17; NOT CLEAN: mixed
LW,RW,RM | 18 | FWL/AML | Q17; NOT CLEAN: mixed
DM,CM,RM | 18 | excluded | Q17
RW,LW,AM | 18 | FWR/AMR | clean
DM,RM,CM | 18 | excluded | Q17
CM,DM,CB | 18 | excluded | clean
CM,AM,DM | 17 | excluded | NOT CLEAN: mixed
DM,CM,AM | 17 | excluded | NOT CLEAN: mixed
CM,DM,LM | 17 | excluded | Q17
RW,AM,RM | 17 | FWR/AMR | Q17; NOT CLEAN: mixed
DM,AM,CM | 17 | excluded | NOT CLEAN: mixed
LW,FW,RW | 16 | FWL/AML | clean
LW,RM,LM | 16 | FWL/AML | Q17; NOT CLEAN: mixed
RB,AM | 16 | excluded | NOT CLEAN: mixed
RM,FW,LM | 16 | excluded | Q17; NOT CLEAN: mixed
WB,RM,RB | 16 | excluded | Q17
LM,RW,RM | 16 | excluded | Q17; NOT CLEAN: mixed
LW,LM,FW | 15 | FWL/AML | Q17; NOT CLEAN: mixed
RW,LM,LW | 15 | FWR/AMR | Q17; NOT CLEAN: mixed
CM,RM,DM | 15 | excluded | Q17
FW,LM,RM | 15 | FW | Q17; NOT CLEAN: mixed
FW,AM,RW | 15 | FW | clean
FW,AM,CM | 15 | FW | NOT CLEAN: mixed
CM,DM,AM | 15 | excluded | NOT CLEAN: mixed
AM,FW,CM | 15 | AMC | NOT CLEAN: mixed
LM,RM,FW | 15 | excluded | Q17; NOT CLEAN: mixed
AM,CM,LM | 14 | AMC | Q17; NOT CLEAN: mixed
FW,AM,LM | 14 | FW | Q17; NOT CLEAN: mixed
DM,CM,CB | 14 | excluded | clean
AM,RM,CM | 14 | AMC | Q17; NOT CLEAN: mixed
AM,LM,LW | 14 | AMC | Q17; NOT CLEAN: mixed
RW,AM,FW | 14 | FWR/AMR | clean
CM,RM,LM | 13 | excluded | Q17
FW,CM,RM | 13 | FW | Q17; NOT CLEAN: mixed
DF,FW | 13 | excluded | generic label; NOT CLEAN: mixed
LW,RM,FW | 13 | FWL/AML | Q17; NOT CLEAN: mixed
RW,FW,RM | 13 | FWR/AMR | Q17; NOT CLEAN: mixed
LW,LM,AM | 13 | FWL/AML | Q17; NOT CLEAN: mixed
FW,RM,RW | 13 | FW | Q17; NOT CLEAN: mixed
LW,AM,FW | 13 | FWL/AML | clean
RW,FW,LW | 13 | FWR/AMR | clean
LW,FW,LM | 12 | FWL/AML | Q17; NOT CLEAN: mixed
CM,LM,LW | 12 | excluded | Q17; NOT CLEAN: mixed
LW,RW,LM | 12 | FWL/AML | Q17; NOT CLEAN: mixed
AM,LM,RM | 12 | AMC | Q17; NOT CLEAN: mixed
RW,RM,LM | 12 | FWR/AMR | Q17; NOT CLEAN: mixed
WB,CB,RB | 12 | excluded | clean
LW,LM,RW | 12 | FWL/AML | Q17; NOT CLEAN: mixed
RW,RM,CM | 12 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,RM,FW | 12 | FWR/AMR | Q17; NOT CLEAN: mixed
DM,LM,CM | 12 | excluded | Q17
RW,LM,RM | 11 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,AM,LW | 11 | FWR/AMR | clean
RB,RM,RW | 11 | excluded | Q17; NOT CLEAN: mixed
AM,FW,RW | 11 | AMC | clean
RM,AM,CM | 11 | excluded | Q17; NOT CLEAN: mixed
AM,RW,FW | 11 | AMC | clean
DM,CB,CM | 11 | excluded | clean
AM,CM,RM | 11 | AMC | Q17; NOT CLEAN: mixed
LW,AM,RW | 11 | FWL/AML | clean
AM,RW,RM | 10 | AMC | Q17; NOT CLEAN: mixed
AM,LW,FW | 10 | AMC | clean
LM,RM,LW | 10 | excluded | Q17; NOT CLEAN: mixed
AM,LM,FW | 10 | AMC | Q17; NOT CLEAN: mixed
FW,AM,RM | 10 | FW | Q17; NOT CLEAN: mixed
WB,LB,CB | 10 | excluded | clean
LW,FW,AM | 10 | FWL/AML | clean
FW,RW,AM | 10 | FW | clean
RW,RM,AM | 10 | FWR/AMR | Q17; NOT CLEAN: mixed
WB,LB,LM | 10 | excluded | Q17
WB,LM,LB | 10 | excluded | Q17
RM,CM,FW | 10 | excluded | Q17; NOT CLEAN: mixed
RM,RW,LW | 10 | excluded | Q17; NOT CLEAN: mixed
AM,RM,RW | 10 | AMC | Q17; NOT CLEAN: mixed
LW,CM,LM | 10 | FWL/AML | Q17; NOT CLEAN: mixed
RW,RM,RB | 10 | FWR/AMR | Q17; NOT CLEAN: mixed
LM,LW,RM | 9 | excluded | Q17; NOT CLEAN: mixed
CB,DM,CM | 9 | excluded | clean
AM,LW,LM | 9 | AMC | Q17; NOT CLEAN: mixed
CM,RM,AM | 9 | excluded | Q17; NOT CLEAN: mixed
AM,CM,FW | 9 | AMC | NOT CLEAN: mixed
LM,RW,LW | 9 | excluded | Q17; NOT CLEAN: mixed
AM,RM,LM | 9 | AMC | Q17; NOT CLEAN: mixed
LB,CB,RB | 9 | excluded | clean
LM,LW,CM | 9 | excluded | Q17; NOT CLEAN: mixed
LM,DM,RM | 9 | excluded | Q17
WB,RB,CB | 9 | excluded | clean
AM,FW,RM | 9 | AMC | Q17; NOT CLEAN: mixed
RM,LW,RW | 9 | excluded | Q17; NOT CLEAN: mixed
FW,CM,LM | 9 | FW | Q17; NOT CLEAN: mixed
CM,LM,AM | 9 | excluded | Q17; NOT CLEAN: mixed
FW,LM,AM | 9 | FW | Q17; NOT CLEAN: mixed
FW,CM,AM | 9 | FW | NOT CLEAN: mixed
LW,FW,RM | 9 | FWL/AML | Q17; NOT CLEAN: mixed
CM,CB,DM | 9 | excluded | clean
RW,CM,RM | 8 | FWR/AMR | Q17; NOT CLEAN: mixed
RB,RW,RM | 8 | excluded | Q17; NOT CLEAN: mixed
LM,AM,CM | 8 | excluded | Q17; NOT CLEAN: mixed
RM,LM,DM | 8 | excluded | Q17
LW,LM,RM | 8 | FWL/AML | Q17; NOT CLEAN: mixed
RM,LM,FW | 8 | excluded | Q17; NOT CLEAN: mixed
AM,DM,LW | 8 | AMC | NOT CLEAN: mixed
CM,FW,RM | 8 | excluded | Q17; NOT CLEAN: mixed
AM,FW,LW | 8 | AMC | clean
RM,CM,CB | 8 | excluded | Q17
CM,AM,RM | 8 | excluded | Q17; NOT CLEAN: mixed
RM,AM,RW | 8 | excluded | Q17; NOT CLEAN: mixed
RM,AM,LM | 8 | excluded | Q17; NOT CLEAN: mixed
RW,FW,AM | 8 | FWR/AMR | clean
FW,LW,RM | 8 | FW | Q17; NOT CLEAN: mixed
AM,FW,LM | 7 | AMC | Q17; NOT CLEAN: mixed
WB,RB,RM | 7 | excluded | Q17
RM,FW,RW | 7 | excluded | Q17; NOT CLEAN: mixed
LM,CM,LW | 7 | excluded | Q17; NOT CLEAN: mixed
AM,RM,FW | 7 | AMC | Q17; NOT CLEAN: mixed
RM,RW,FW | 7 | excluded | Q17; NOT CLEAN: mixed
RM,LM,LW | 7 | excluded | Q17; NOT CLEAN: mixed
LW,LM,CM | 7 | FWL/AML | Q17; NOT CLEAN: mixed
LW,AM,LM | 7 | FWL/AML | Q17; NOT CLEAN: mixed
CM,LM,FW | 7 | excluded | Q17; NOT CLEAN: mixed
CM,RW,RM | 7 | excluded | Q17; NOT CLEAN: mixed
RM,LW,LM | 7 | excluded | Q17; NOT CLEAN: mixed
LM,LW,FW | 7 | excluded | Q17; NOT CLEAN: mixed
LM,LW,AM | 7 | excluded | Q17; NOT CLEAN: mixed
WB,RW,RB | 7 | excluded | NOT CLEAN: mixed
CM,AM,LM | 7 | excluded | Q17; NOT CLEAN: mixed
LM,FW,CM | 7 | excluded | Q17; NOT CLEAN: mixed
CM,RM,FW | 7 | excluded | Q17; NOT CLEAN: mixed
LM,CM,AM | 7 | excluded | Q17; NOT CLEAN: mixed
RM,CM,RB | 7 | excluded | Q17
FW,MF | 6 | FW | generic label; NOT CLEAN: mixed
FW,RM,AM | 6 | FW | Q17; NOT CLEAN: mixed
LW,DM,AM | 6 | FWL/AML | NOT CLEAN: mixed
RM,LM,WB | 6 | excluded | Q17
LW,RW,RB | 6 | FWL/AML | NOT CLEAN: mixed
CM,LW,LM | 6 | excluded | Q17; NOT CLEAN: mixed
WB,RB,LB | 6 | excluded | clean
WB,LB,RB | 6 | excluded | clean
LM,AM,LW | 6 | excluded | Q17; NOT CLEAN: mixed
AM,RM,LW | 6 | AMC | Q17; NOT CLEAN: mixed
CB,CM,DM | 6 | excluded | clean
RW,LW,RM | 6 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,LB,LW | 6 | FWR/AMR | NOT CLEAN: mixed
CM,FW,LM | 6 | excluded | Q17; NOT CLEAN: mixed
RM,RW,AM | 6 | excluded | Q17; NOT CLEAN: mixed
LW,AM,RM | 6 | FWL/AML | Q17; NOT CLEAN: mixed
LM,RM,RW | 6 | excluded | Q17; NOT CLEAN: mixed
RM,AM,FW | 6 | excluded | Q17; NOT CLEAN: mixed
CM,RM,WB | 6 | excluded | Q17
RB,CM,DM | 6 | excluded | clean
AM,RW,DM | 5 | AMC | NOT CLEAN: mixed
LW,FW,CM | 5 | FWL/AML | NOT CLEAN: mixed
LM,CM,RB | 5 | excluded | Q17
LM,CM,FW | 5 | excluded | Q17; NOT CLEAN: mixed
RW,LW,CM | 5 | FWR/AMR | NOT CLEAN: mixed
FW,WB,AM | 5 | FW | NOT CLEAN: mixed
RW,RM,LW | 5 | FWR/AMR | Q17; NOT CLEAN: mixed
AM,WB,CM | 5 | AMC | NOT CLEAN: mixed
CM,RM,RW | 5 | excluded | Q17; NOT CLEAN: mixed
AM,RW,CM | 5 | AMC | NOT CLEAN: mixed
LW,LM,WB | 5 | FWL/AML | Q17; NOT CLEAN: mixed
AM,LM,RW | 5 | AMC | Q17; NOT CLEAN: mixed
DM,LM,RM | 5 | excluded | Q17
LM,AM,FW | 5 | excluded | Q17; NOT CLEAN: mixed
LB,WB,RB | 5 | excluded | clean
WB,LW,RW | 5 | excluded | NOT CLEAN: mixed
LW,WB,LM | 5 | FWL/AML | Q17; NOT CLEAN: mixed
WB,RB,RW | 5 | excluded | NOT CLEAN: mixed
LM,RM,DM | 5 | excluded | Q17
CB,RB,WB | 5 | excluded | clean
LW,LB,LM | 5 | FWL/AML | Q17; NOT CLEAN: mixed
RM,RW,RB | 5 | excluded | Q17; NOT CLEAN: mixed
LM,WB,RM | 5 | excluded | Q17
RM,RW,CM | 5 | excluded | Q17; NOT CLEAN: mixed
RM,LM,RB | 5 | excluded | Q17
LM,LW,RW | 5 | excluded | Q17; NOT CLEAN: mixed
RM,RW,LM | 5 | excluded | Q17; NOT CLEAN: mixed
LW,LM,LB | 5 | FWL/AML | Q17; NOT CLEAN: mixed
CM,FW,AM | 5 | excluded | NOT CLEAN: mixed
CM,RM,RB | 5 | excluded | Q17
RM,FW,CM | 5 | excluded | Q17; NOT CLEAN: mixed
RM,WB,RB | 5 | excluded | Q17
AM,CM,CB | 5 | AMC | NOT CLEAN: mixed
RW,CM,DM | 5 | FWR/AMR | NOT CLEAN: mixed
LM,FW,LW | 5 | excluded | Q17; NOT CLEAN: mixed
FW,LW,CM | 5 | FW | NOT CLEAN: mixed
RM,LM,RW | 5 | excluded | Q17; NOT CLEAN: mixed
LM,LW,LB | 4 | excluded | Q17; NOT CLEAN: mixed
LM,DM,LW | 4 | excluded | Q17; NOT CLEAN: mixed
LM,AM,RM | 4 | excluded | Q17; NOT CLEAN: mixed
LW,AM,CM | 4 | FWL/AML | NOT CLEAN: mixed
LB,LW,LM | 4 | excluded | Q17; NOT CLEAN: mixed
LM,RM,AM | 4 | excluded | Q17; NOT CLEAN: mixed
LB,RM,LM | 4 | excluded | Q17
LM,WB,LB | 4 | excluded | Q17
LM,RW,AM | 4 | excluded | Q17; NOT CLEAN: mixed
LM,LB,CM | 4 | excluded | Q17
RM,DM,LM | 4 | excluded | Q17
CM,RW,FW | 4 | excluded | NOT CLEAN: mixed
CM,FW,LW | 4 | excluded | NOT CLEAN: mixed
RW,LM,FW | 4 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,RB,RM | 4 | FWR/AMR | Q17; NOT CLEAN: mixed
RM,LM,LB | 4 | excluded | Q17
CM,LW,RW | 4 | excluded | NOT CLEAN: mixed
CM,DM,LW | 4 | excluded | NOT CLEAN: mixed
CM,RB,RM | 4 | excluded | Q17
RW,AM,DM | 4 | FWR/AMR | NOT CLEAN: mixed
RM,DM,RW | 4 | excluded | Q17; NOT CLEAN: mixed
AM,CM,LW | 4 | AMC | NOT CLEAN: mixed
WB,CM,RB | 4 | excluded | clean
DM,AM,RM | 4 | excluded | Q17; NOT CLEAN: mixed
RW,LB,WB | 4 | FWR/AMR | NOT CLEAN: mixed
RB,WB,CB | 4 | excluded | clean
DM,CM,RB | 4 | excluded | clean
RB,RM,WB | 4 | excluded | Q17
WB,LM,LW | 4 | excluded | Q17; NOT CLEAN: mixed
FW,CM,LW | 4 | FW | NOT CLEAN: mixed
WB,LW,LB | 4 | excluded | NOT CLEAN: mixed
LW,CM,RW | 4 | FWL/AML | NOT CLEAN: mixed
FW,RM,CM | 4 | FW | Q17; NOT CLEAN: mixed
LW,DM,CM | 4 | FWL/AML | NOT CLEAN: mixed
FW,LM,CM | 4 | FW | Q17; NOT CLEAN: mixed
FW,DM,CM | 4 | FW | NOT CLEAN: mixed
CB,LB,WB | 4 | excluded | clean
FW,CM,DM | 4 | FW | NOT CLEAN: mixed
CM,AM,FW | 4 | excluded | NOT CLEAN: mixed
FW,AM,WB | 4 | FW | NOT CLEAN: mixed
DM,RW,CM | 4 | excluded | NOT CLEAN: mixed
CB,WB,LB | 4 | excluded | clean
RW,CM,FW | 4 | FWR/AMR | NOT CLEAN: mixed
RW,FW,LM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,LM,AM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,LM,CM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
LM,DM,AM | 3 | excluded | Q17; NOT CLEAN: mixed
LW,AM,WB | 3 | FWL/AML | NOT CLEAN: mixed
RW,RB,AM | 3 | FWR/AMR | NOT CLEAN: mixed
RW,RM,WB | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,WB,LM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,WB,RM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
WB,AM,FW | 3 | excluded | NOT CLEAN: mixed
LM,AM,WB | 3 | excluded | Q17; NOT CLEAN: mixed
WB,CM,RM | 3 | excluded | Q17
WB,DM,CM | 3 | excluded | clean
WB,LB,CM | 3 | excluded | clean
WB,LM,CM | 3 | excluded | Q17
LM,AM,DM | 3 | excluded | Q17; NOT CLEAN: mixed
RW,DM,CM | 3 | FWR/AMR | NOT CLEAN: mixed
RM,WB,LB | 3 | excluded | Q17
RW,DM,AM | 3 | FWR/AMR | NOT CLEAN: mixed
RM,LB,RB | 3 | excluded | Q17
LW,CM,FW | 3 | FWL/AML | NOT CLEAN: mixed
LW,RB,RW | 3 | FWL/AML | NOT CLEAN: mixed
LW,RM,CM | 3 | FWL/AML | Q17; NOT CLEAN: mixed
LW,WB,LB | 3 | FWL/AML | NOT CLEAN: mixed
RB,AM,WB | 3 | excluded | NOT CLEAN: mixed
RB,CM,RM | 3 | excluded | Q17
RB,DM,RW | 3 | excluded | NOT CLEAN: mixed
RB,WB,RM | 3 | excluded | Q17
RM,CM,AM | 3 | excluded | Q17; NOT CLEAN: mixed
RM,FW,AM | 3 | excluded | Q17; NOT CLEAN: mixed
RM,LM,AM | 3 | excluded | Q17; NOT CLEAN: mixed
RW,CM,LM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
RM,LW,AM | 3 | excluded | Q17; NOT CLEAN: mixed
RM,LW,CM | 3 | excluded | Q17; NOT CLEAN: mixed
RM,RB,CM | 3 | excluded | Q17
RM,RB,WB | 3 | excluded | Q17
LW,CM,DM | 3 | FWL/AML | NOT CLEAN: mixed
RM,WB,RW | 3 | excluded | Q17; NOT CLEAN: mixed
LM,LB,DM | 3 | excluded | Q17
RW,AM,LM | 3 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,AM,WB | 3 | FWR/AMR | NOT CLEAN: mixed
RW,CM,AM | 3 | FWR/AMR | NOT CLEAN: mixed
WB,RM,RW | 3 | excluded | Q17; NOT CLEAN: mixed
LM,LB,RM | 3 | excluded | Q17
DM,AM,RW | 3 | excluded | NOT CLEAN: mixed
DM,AM,LW | 3 | excluded | NOT CLEAN: mixed
DM,LM,AM | 3 | excluded | Q17; NOT CLEAN: mixed
AM,RW,WB | 3 | AMC | NOT CLEAN: mixed
CM,RB,DM | 3 | excluded | clean
AM,WB,RW | 3 | AMC | NOT CLEAN: mixed
DM,CM,WB | 3 | excluded | clean
FW,RW,LM | 3 | FW | Q17; NOT CLEAN: mixed
CB,DM,RB | 3 | excluded | clean
LB,LM,LW | 3 | excluded | Q17; NOT CLEAN: mixed
DM,CM,LB | 3 | excluded | clean
CB,LB,RB | 3 | excluded | clean
CB,RB,RW | 3 | excluded | NOT CLEAN: mixed
CM,AM,RW | 3 | excluded | NOT CLEAN: mixed
FW,RM,LB | 3 | FW | Q17; NOT CLEAN: mixed
CM,AM,WB | 3 | excluded | NOT CLEAN: mixed
CM,DM,RB | 3 | excluded | clean
CM,DM,RW | 3 | excluded | NOT CLEAN: mixed
CM,FW,DM | 3 | excluded | NOT CLEAN: mixed
CM,WB,RB | 3 | excluded | clean
CM,LB,LM | 3 | excluded | Q17
CM,RW,AM | 3 | excluded | NOT CLEAN: mixed
CM,LM,CB | 3 | excluded | Q17
CM,LM,LB | 3 | excluded | Q17
CM,RM,CB | 3 | excluded | Q17
CM,RB,WB | 3 | excluded | clean
FW,RM,LW | 3 | FW | Q17; NOT CLEAN: mixed
CM,RB,LM | 3 | excluded | Q17
FW,LW,WB | 3 | FW | NOT CLEAN: mixed
AM,DM,FW | 3 | AMC | NOT CLEAN: mixed
AM,LB,WB | 3 | AMC | NOT CLEAN: mixed
LB,WB,CM | 3 | excluded | clean
AM,LW,CM | 3 | AMC | NOT CLEAN: mixed
AM,CM,RW | 3 | AMC | NOT CLEAN: mixed
LB,RB,WB | 3 | excluded | clean
FW,DM,AM | 3 | FW | NOT CLEAN: mixed
RB,CB,WB | 2 | excluded | clean
LW,RW,CM | 2 | FWL/AML | NOT CLEAN: mixed
RM,CM,RW | 2 | excluded | Q17; NOT CLEAN: mixed
DF | 2 | excluded | generic label
LW,RM,RB | 2 | FWL/AML | Q17; NOT CLEAN: mixed
DF,MF | 2 | excluded | generic label
DM,AM,FW | 2 | excluded | NOT CLEAN: mixed
DM,AM,LM | 2 | excluded | Q17; NOT CLEAN: mixed
RM,DM,AM | 2 | excluded | Q17; NOT CLEAN: mixed
FW,CM,RW | 2 | FW | NOT CLEAN: mixed
LW,RM,AM | 2 | FWL/AML | Q17; NOT CLEAN: mixed
DM,RW,LM | 2 | excluded | Q17; NOT CLEAN: mixed
CM,RW,LM | 2 | excluded | Q17; NOT CLEAN: mixed
RM,DM,LW | 2 | excluded | Q17; NOT CLEAN: mixed
CM,RW,DM | 2 | excluded | NOT CLEAN: mixed
RM,FW,CB | 2 | excluded | Q17; NOT CLEAN: mixed
CM,RM,LB | 2 | excluded | Q17
RM,FW,LW | 2 | excluded | Q17; NOT CLEAN: mixed
FW,DM,LM | 2 | FW | Q17; NOT CLEAN: mixed
FW,GK | 2 | FW | NOT CLEAN: mixed
LW,RW,DM | 2 | FWL/AML | NOT CLEAN: mixed
LB,WB,LM | 2 | excluded | Q17
LW,RW,WB | 2 | FWL/AML | NOT CLEAN: mixed
DM,RB,LB | 2 | excluded | clean
DM,LM,CB | 2 | excluded | Q17
RB,CB,RM | 2 | excluded | Q17
RB,LB,CB | 2 | excluded | clean
RB,LB,WB | 2 | excluded | clean
RB,CB,LB | 2 | excluded | clean
RB,LM,RM | 2 | excluded | Q17
DM,RB,CM | 2 | excluded | clean
RB,LM,RW | 2 | excluded | Q17; NOT CLEAN: mixed
RB,LM,WB | 2 | excluded | Q17
RB,LW,RW | 2 | excluded | NOT CLEAN: mixed
DM,RM,AM | 2 | excluded | Q17; NOT CLEAN: mixed
DM,RM,RB | 2 | excluded | Q17
RB,RM,LM | 2 | excluded | Q17
RB,RW,DM | 2 | excluded | NOT CLEAN: mixed
LW,WB,RM | 2 | FWL/AML | Q17; NOT CLEAN: mixed
DM,RM,CB | 2 | excluded | Q17
RB,WB,LB | 2 | excluded | clean
DM,CM,LW | 2 | excluded | NOT CLEAN: mixed
DM,RM,LM | 2 | excluded | Q17
DM,CM,FW | 2 | excluded | NOT CLEAN: mixed
RM,AM,DM | 2 | excluded | Q17; NOT CLEAN: mixed
DM,LW,AM | 2 | excluded | NOT CLEAN: mixed
RB,RM,AM | 2 | excluded | Q17; NOT CLEAN: mixed
RM,RB,FW | 2 | excluded | Q17; NOT CLEAN: mixed
RM,LM,CB | 2 | excluded | Q17
AM,LM,DM | 2 | AMC | Q17; NOT CLEAN: mixed
AM,RW,LM | 2 | AMC | Q17; NOT CLEAN: mixed
AM,RM,WB | 2 | AMC | Q17; NOT CLEAN: mixed
WB,AM,RM | 2 | excluded | Q17; NOT CLEAN: mixed
WB,AM,RW | 2 | excluded | NOT CLEAN: mixed
AM,RM,DM | 2 | AMC | Q17; NOT CLEAN: mixed
AM,RB,DM | 2 | AMC | NOT CLEAN: mixed
WB,CM,CB | 2 | excluded | clean
WB,CM,LM | 2 | excluded | Q17
AM,LW,RM | 2 | AMC | Q17; NOT CLEAN: mixed
WB,DM,LB | 2 | excluded | clean
WB,FW,AM | 2 | excluded | NOT CLEAN: mixed
WB,FW,RM | 2 | excluded | Q17; NOT CLEAN: mixed
AM,LM,LB | 2 | AMC | Q17; NOT CLEAN: mixed
WB,LB,LW | 2 | excluded | NOT CLEAN: mixed
RW,WB,AM | 2 | FWR/AMR | NOT CLEAN: mixed
AM,LB,LW | 2 | AMC | NOT CLEAN: mixed
AM,LB,CM | 2 | AMC | NOT CLEAN: mixed
WB,LM,RM | 2 | excluded | Q17
WB,LW,CM | 2 | excluded | NOT CLEAN: mixed
WB,LW,FW | 2 | excluded | NOT CLEAN: mixed
WB,LW,LM | 2 | excluded | Q17; NOT CLEAN: mixed
AM,FW,DM | 2 | AMC | NOT CLEAN: mixed
AM,DM,RW | 2 | AMC | NOT CLEAN: mixed
WB,RB,CM | 2 | excluded | clean
WB,RM,DM | 2 | excluded | Q17
AM,CM,WB | 2 | AMC | NOT CLEAN: mixed
WB,RW,FW | 2 | excluded | NOT CLEAN: mixed
AM,CB,CM | 2 | AMC | NOT CLEAN: mixed
RW,WB,RB | 2 | FWR/AMR | NOT CLEAN: mixed
AM,WB,FW | 2 | AMC | NOT CLEAN: mixed
CM,RB,CB | 2 | excluded | clean
CM,CB,RM | 2 | excluded | Q17
CM,LW,FW | 2 | excluded | NOT CLEAN: mixed
CM,LW,AM | 2 | excluded | NOT CLEAN: mixed
CM,LM,WB | 2 | excluded | Q17
CM,LB,WB | 2 | excluded | clean
RM,RB,CB | 2 | excluded | Q17
CM,LB,RM | 2 | excluded | Q17
FW,LM,CB | 2 | FW | Q17; NOT CLEAN: mixed
RM,RB,RW | 2 | excluded | Q17; NOT CLEAN: mixed
CM,LB,LW | 2 | excluded | NOT CLEAN: mixed
CM,LB,CB | 2 | excluded | clean
RM,WB,LM | 2 | excluded | Q17
RW,AM,CM | 2 | FWR/AMR | NOT CLEAN: mixed
CM,DM,FW | 2 | excluded | NOT CLEAN: mixed
CM,CB,RB | 2 | excluded | clean
AM,WB,LM | 2 | AMC | Q17; NOT CLEAN: mixed
RW,CB,WB | 2 | FWR/AMR | NOT CLEAN: mixed
CB,WB,RB | 2 | excluded | clean
CB,RB,RM | 2 | excluded | Q17
RW,LM,LB | 2 | FWR/AMR | Q17; NOT CLEAN: mixed
CB,LW,CM | 2 | excluded | NOT CLEAN: mixed
RW,LW,DM | 2 | FWR/AMR | NOT CLEAN: mixed
CB,GK | 2 | excluded | clean
RW,LW,WB | 2 | FWR/AMR | NOT CLEAN: mixed
RW,RB,FW | 2 | FWR/AMR | NOT CLEAN: mixed
CB,CM,RM | 2 | excluded | Q17
CB,CM,RB | 2 | excluded | clean
RW,RM,DM | 2 | FWR/AMR | Q17; NOT CLEAN: mixed
AM,WB,RB | 2 | AMC | NOT CLEAN: mixed
LW,LB,WB | 2 | FWL/AML | NOT CLEAN: mixed
WB,RW,RM | 2 | excluded | Q17; NOT CLEAN: mixed
LM,LB,CB | 2 | excluded | Q17
LM,LW,DM | 2 | excluded | Q17; NOT CLEAN: mixed
LM,CM,LB | 2 | excluded | Q17
LM,RM,RB | 2 | excluded | Q17
FW,LW,LB | 2 | FW | NOT CLEAN: mixed
LM,RM,WB | 2 | excluded | Q17
LM,LW,RB | 2 | excluded | Q17; NOT CLEAN: mixed
LM,CM,RW | 2 | excluded | Q17; NOT CLEAN: mixed
LM,RW,LB | 2 | excluded | Q17; NOT CLEAN: mixed
LM,DM,LB | 2 | excluded | Q17
LM,WB,AM | 2 | excluded | Q17; NOT CLEAN: mixed
LB,RB,CM | 2 | excluded | clean
LB,LW,WB | 2 | excluded | NOT CLEAN: mixed
LB,RW,LW | 2 | excluded | NOT CLEAN: mixed
LM,FW,AM | 2 | excluded | Q17; NOT CLEAN: mixed
FW,RM,RB | 2 | FW | Q17; NOT CLEAN: mixed
LW,CM,AM | 2 | FWL/AML | NOT CLEAN: mixed
FW,WB,LW | 2 | FW | NOT CLEAN: mixed
LB,LW,DM | 2 | excluded | NOT CLEAN: mixed
FW,RM,WB | 2 | FW | Q17; NOT CLEAN: mixed
LM,LB,WB | 2 | excluded | Q17
FW,RW,CM | 2 | FW | NOT CLEAN: mixed
LB,LM,WB | 2 | excluded | Q17
LM,LB,LW | 2 | excluded | Q17; NOT CLEAN: mixed
LB,CB,WB | 2 | excluded | clean
LM,RW,FW | 2 | excluded | Q17; NOT CLEAN: mixed
LB,LM,RM | 2 | excluded | Q17
LM,RB,RM | 2 | excluded | Q17
LM,RB,CM | 2 | excluded | Q17
LB,CM,CB | 2 | excluded | clean
LM,CB,CM | 2 | excluded | Q17
FW,LM,DM | 2 | FW | Q17; NOT CLEAN: mixed
LM,RM,LB | 2 | excluded | Q17
CB,LB,RM,RB | 1 | excluded | Q17
CB,LM,CM | 1 | excluded | Q17
RW,LM,WB | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CM,DM,RB,CB | 1 | excluded | clean
LM,RB,RW | 1 | excluded | Q17; NOT CLEAN: mixed
CM,DM,LW,RM | 1 | excluded | Q17; NOT CLEAN: mixed
CB,LM,LB | 1 | excluded | Q17
RW,LM,LW,WB | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,LM,RB | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
LM,LW,CB | 1 | excluded | Q17; NOT CLEAN: mixed
CM,DM,LB | 1 | excluded | clean
LB,LM,CM | 1 | excluded | Q17
RW,AM,DM,CM | 1 | FWR/AMR | NOT CLEAN: mixed
CB,LW,DM | 1 | excluded | NOT CLEAN: mixed
RW,LM,DM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CM,DM,RM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
LB,LM,DM | 1 | excluded | Q17
CB,RB,CM | 1 | excluded | clean
CB,LB,LM | 1 | excluded | Q17
RW,RB,WB | 1 | FWR/AMR | NOT CLEAN: mixed
RW,RB,RM,LW | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CB,DM,FW | 1 | excluded | NOT CLEAN: mixed
RW,RB,LW | 1 | FWR/AMR | NOT CLEAN: mixed
RW,RB,LB | 1 | FWR/AMR | NOT CLEAN: mixed
RM,WB,DM | 1 | excluded | Q17
CB,DM,GK | 1 | excluded | clean
LB,LM,LW,RW | 1 | excluded | Q17; NOT CLEAN: mixed
RW,LW,WB,AM | 1 | FWR/AMR | NOT CLEAN: mixed
LM,LB,RW | 1 | excluded | Q17; NOT CLEAN: mixed
LB,CM,RM | 1 | excluded | Q17
RW,LW,RM,AM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
LM,RB,WB | 1 | excluded | Q17
RM,WB,LW | 1 | excluded | Q17; NOT CLEAN: mixed
RW,LW,RB,FW | 1 | FWR/AMR | NOT CLEAN: mixed
CB,LB,CM | 1 | excluded | clean
RW,LW,LB | 1 | FWR/AMR | NOT CLEAN: mixed
CB,LW,RB | 1 | excluded | NOT CLEAN: mixed
LB,CM,WB | 1 | excluded | clean
CM,DM,FW,AM | 1 | excluded | NOT CLEAN: mixed
CB,RB,DM | 1 | excluded | clean
RW,DM,LM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,AM,RB | 1 | FWR/AMR | NOT CLEAN: mixed
LM,RB,AM | 1 | excluded | Q17; NOT CLEAN: mixed
CM,AM,CB | 1 | excluded | NOT CLEAN: mixed
CM,AM,FW,RW | 1 | excluded | NOT CLEAN: mixed
RW,CM,WB | 1 | FWR/AMR | NOT CLEAN: mixed
RW,AM,RM,CM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CM,AM,LB | 1 | excluded | NOT CLEAN: mixed
RW,CM,LW | 1 | FWR/AMR | NOT CLEAN: mixed
CM,AM,LW | 1 | excluded | NOT CLEAN: mixed
CM,AM,RB,RM | 1 | excluded | Q17; NOT CLEAN: mixed
CM,AM,RM,DM | 1 | excluded | Q17; NOT CLEAN: mixed
LB,FW,LW | 1 | excluded | NOT CLEAN: mixed
LB,DM,LM | 1 | excluded | Q17
LM,LW,RW,FW | 1 | excluded | Q17; NOT CLEAN: mixed
RW,CB,RB | 1 | FWR/AMR | NOT CLEAN: mixed
RW,CB,DM | 1 | FWR/AMR | NOT CLEAN: mixed
RW,DM,LW | 1 | FWR/AMR | NOT CLEAN: mixed
RW,DM,RM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CB,RW,CM | 1 | excluded | NOT CLEAN: mixed
LB,FW,WB | 1 | excluded | NOT CLEAN: mixed
CM,CB,LM | 1 | excluded | Q17
RW,LB,RM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,LB,RB | 1 | FWR/AMR | NOT CLEAN: mixed
CB,RB,LW | 1 | excluded | NOT CLEAN: mixed
LB,GK | 1 | excluded | clean
RW,FW,RM,LW | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,FW,RM,LM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,FW,LW,AM | 1 | FWR/AMR | clean
CB,RM,LB | 1 | excluded | Q17
CM,CB,WB | 1 | excluded | clean
CB,RM,CM | 1 | excluded | Q17
RW,RB,WB,LW | 1 | FWR/AMR | NOT CLEAN: mixed
CB,RM,DM | 1 | excluded | Q17
RW,FW,CM | 1 | FWR/AMR | NOT CLEAN: mixed
RW,FW,AM,CM | 1 | FWR/AMR | NOT CLEAN: mixed
RW,AM,LW,LM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CB,RB,LB | 1 | excluded | clean
LW,LB,RW | 1 | FWL/AML | NOT CLEAN: mixed
LM,LB,CM,RB | 1 | excluded | Q17
LB,RB,RW | 1 | excluded | NOT CLEAN: mixed
LM,CM,CB | 1 | excluded | Q17
AM,FW,LW,LM | 1 | AMC | Q17; NOT CLEAN: mixed
LB,RM,WB | 1 | excluded | Q17
WB,LM,RB | 1 | excluded | Q17
AM,FW,WB | 1 | AMC | NOT CLEAN: mixed
LM,CM,DM,AM | 1 | excluded | Q17; NOT CLEAN: mixed
WB,LM,FW | 1 | excluded | Q17; NOT CLEAN: mixed
AM,LB,RW | 1 | AMC | NOT CLEAN: mixed
WB,LB,RB,CB | 1 | excluded | clean
LB,RB,RM | 1 | excluded | Q17
AM,LM,RW,LW | 1 | AMC | Q17; NOT CLEAN: mixed
LB,RB,LW | 1 | excluded | NOT CLEAN: mixed
WB,LB,DM | 1 | excluded | clean
LM,CM,RM,DM | 1 | excluded | Q17
AM,LM,LB,CM | 1 | AMC | Q17; NOT CLEAN: mixed
AM,LM,RB | 1 | AMC | Q17; NOT CLEAN: mixed
LM,CM,RM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
WB,FW,RB | 1 | excluded | NOT CLEAN: mixed
WB,FW,LW | 1 | excluded | NOT CLEAN: mixed
WB,FW,LM | 1 | excluded | Q17; NOT CLEAN: mixed
LB,RW,CM | 1 | excluded | NOT CLEAN: mixed
AM,FW,LM,RM | 1 | AMC | Q17; NOT CLEAN: mixed
WB,LW,LM,LB | 1 | excluded | Q17; NOT CLEAN: mixed
AM,DM,WB | 1 | AMC | NOT CLEAN: mixed
LB,WB,DM | 1 | excluded | clean
WB,RW,LW | 1 | excluded | NOT CLEAN: mixed
LM,AM,LB | 1 | excluded | Q17; NOT CLEAN: mixed
WB,RW,CM | 1 | excluded | NOT CLEAN: mixed
WB,RW,AM | 1 | excluded | NOT CLEAN: mixed
AM,CM,FW,DM | 1 | AMC | NOT CLEAN: mixed
LB,WB,CB | 1 | excluded | clean
WB,RM,RB,RW | 1 | excluded | Q17; NOT CLEAN: mixed
LM,AM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
WB,RM,LW | 1 | excluded | Q17; NOT CLEAN: mixed
LM,AM,RW,FW | 1 | excluded | Q17; NOT CLEAN: mixed
AM,DM,CB | 1 | AMC | NOT CLEAN: mixed
LM,AM,RW,LW | 1 | excluded | Q17; NOT CLEAN: mixed
AM,DM,RB | 1 | AMC | NOT CLEAN: mixed
AM,DM,RM | 1 | AMC | Q17; NOT CLEAN: mixed
WB,RB,FW | 1 | excluded | NOT CLEAN: mixed
LB,RW,RM | 1 | excluded | Q17; NOT CLEAN: mixed
LB,RW,RB | 1 | excluded | NOT CLEAN: mixed
WB,RB,AM | 1 | excluded | NOT CLEAN: mixed
WB,FW,CM | 1 | excluded | NOT CLEAN: mixed
WB,DM,RW | 1 | excluded | NOT CLEAN: mixed
CB,CM,LB | 1 | excluded | clean
RW,RM,RB,WB | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,WB,LW | 1 | FWR/AMR | NOT CLEAN: mixed
RW,WB,LB | 1 | FWR/AMR | NOT CLEAN: mixed
RW,WB,FW | 1 | FWR/AMR | NOT CLEAN: mixed
RW,WB,DM | 1 | FWR/AMR | NOT CLEAN: mixed
RW,WB,CM | 1 | FWR/AMR | NOT CLEAN: mixed
RW,WB,CB | 1 | FWR/AMR | NOT CLEAN: mixed
LB,LW,CB | 1 | excluded | NOT CLEAN: mixed
LM,FW,RW | 1 | excluded | Q17; NOT CLEAN: mixed
LM,FW,WB | 1 | excluded | Q17; NOT CLEAN: mixed
AM,WB,LW | 1 | AMC | NOT CLEAN: mixed
WB,DM,LW | 1 | excluded | NOT CLEAN: mixed
RW,RM,LW,LM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,RM,LM,FW | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,RM,LM,AM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RM,WB,CM,CB | 1 | excluded | Q17
RW,RM,LB | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,RM,FW,LW | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
RW,RM,FW,LM | 1 | FWR/AMR | Q17; NOT CLEAN: mixed
CB,AM,FW | 1 | excluded | NOT CLEAN: mixed
LB,LM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
LB,LW,RW | 1 | excluded | NOT CLEAN: mixed
RW,WB,RB,FW | 1 | FWR/AMR | NOT CLEAN: mixed
AM,RW,LW,CM | 1 | AMC | NOT CLEAN: mixed
WB,AM,CM | 1 | excluded | NOT CLEAN: mixed
WB,DM,LM | 1 | excluded | Q17
LB,RB,LM | 1 | excluded | Q17
AM,LM,WB | 1 | AMC | Q17; NOT CLEAN: mixed
LB,RB,FW | 1 | excluded | NOT CLEAN: mixed
AM,LW,DM | 1 | AMC | NOT CLEAN: mixed
LM,DM,CB,CM | 1 | excluded | Q17
WB,CM,LW,LB | 1 | excluded | NOT CLEAN: mixed
LB,RB,DM | 1 | excluded | clean
WB,CM,LB | 1 | excluded | clean
LM,DM,CM,RM | 1 | excluded | Q17
AM,RB,WB | 1 | AMC | NOT CLEAN: mixed
WB,CB,LB | 1 | excluded | clean
WB,CB,CM | 1 | excluded | clean
WB,CB,AM | 1 | excluded | NOT CLEAN: mixed
LB,RB,CB | 1 | excluded | clean
LM,DM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
WB,AM,LW | 1 | excluded | NOT CLEAN: mixed
AM,RM,DM,LM | 1 | AMC | Q17; NOT CLEAN: mixed
WB,AM,DM | 1 | excluded | NOT CLEAN: mixed
RM,WB,CM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
CM,LB,AM,RW | 1 | excluded | NOT CLEAN: mixed
RM,WB,CM | 1 | excluded | Q17
DM,LW,RW | 1 | excluded | NOT CLEAN: mixed
FW,RM,DM | 1 | FW | Q17; NOT CLEAN: mixed
RB,DM,CM,RM | 1 | excluded | Q17
RB,DM,CB | 1 | excluded | clean
RB,DM,AM | 1 | excluded | NOT CLEAN: mixed
DM,LW,CM | 1 | excluded | NOT CLEAN: mixed
RB,CM,WB | 1 | excluded | clean
RB,CM,RW,AM | 1 | excluded | NOT CLEAN: mixed
DM,LW,RM | 1 | excluded | Q17; NOT CLEAN: mixed
RB,CM,LB | 1 | excluded | clean
RB,CM,CB | 1 | excluded | clean
RB,FW,AM | 1 | excluded | NOT CLEAN: mixed
DM,RB,AM | 1 | excluded | NOT CLEAN: mixed
FW,RM,AM,RW | 1 | FW | Q17; NOT CLEAN: mixed
FW,RM,AM,LM | 1 | FW | Q17; NOT CLEAN: mixed
LW,DM,LM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,DM,RM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
DM,RB,CM,CB | 1 | excluded | clean
RB,AM,LW | 1 | excluded | NOT CLEAN: mixed
RB,AM,LM | 1 | excluded | Q17; NOT CLEAN: mixed
RB,AM,DM | 1 | excluded | NOT CLEAN: mixed
DM,LM,CM,FW | 1 | excluded | Q17; NOT CLEAN: mixed
RB,FW,CB | 1 | excluded | NOT CLEAN: mixed
DM,RB,WB | 1 | excluded | clean
RB,LW,LM | 1 | excluded | Q17; NOT CLEAN: mixed
DM,FW,WB | 1 | excluded | NOT CLEAN: mixed
DM,FW,WB,LB | 1 | excluded | NOT CLEAN: mixed
RB,RM,LB | 1 | excluded | Q17
RB,RM,FW | 1 | excluded | Q17; NOT CLEAN: mixed
RB,RM,DM | 1 | excluded | Q17
RB,RM,CM | 1 | excluded | Q17
RB,RM,CB | 1 | excluded | Q17
FW,RW,AM,LW | 1 | FW | clean
DM,LB,CM | 1 | excluded | clean
RB,LW,CM | 1 | excluded | NOT CLEAN: mixed
LW,CM,WB | 1 | FWL/AML | NOT CLEAN: mixed
DM,LB,LW | 1 | excluded | NOT CLEAN: mixed
LW,CB,LM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
FW,RM,RB,RW | 1 | FW | Q17; NOT CLEAN: mixed
RB,LM,LB,RM | 1 | excluded | Q17
FW,RM,LM,RW | 1 | FW | Q17; NOT CLEAN: mixed
RB,LB,RW | 1 | excluded | NOT CLEAN: mixed
RB,LB,RM | 1 | excluded | Q17
RB,LB,CM | 1 | excluded | clean
LW,CM,RM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,DM,RW | 1 | FWL/AML | NOT CLEAN: mixed
FW,RB,WB | 1 | FW | NOT CLEAN: mixed
RM,WB,AM | 1 | excluded | Q17; NOT CLEAN: mixed
LW,RB,DM | 1 | FWL/AML | NOT CLEAN: mixed
FW,AM,LM,DM | 1 | FW | Q17; NOT CLEAN: mixed
FW,AM,RM,CM | 1 | FW | Q17; NOT CLEAN: mixed
FW,CM,CB | 1 | FW | NOT CLEAN: mixed
LW,RM,CB | 1 | FWL/AML | Q17; NOT CLEAN: mixed
FW,LM,RB | 1 | FW | Q17; NOT CLEAN: mixed
FW,CM,RB | 1 | FW | NOT CLEAN: mixed
LW,FW,WB | 1 | FWL/AML | NOT CLEAN: mixed
LW,RB,RM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,RB,LM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
FW,CM,WB | 1 | FW | NOT CLEAN: mixed
FW,AM,DM,LM | 1 | FW | Q17; NOT CLEAN: mixed
LW,LB,AM | 1 | FWL/AML | NOT CLEAN: mixed
FW,DM,LW | 1 | FW | NOT CLEAN: mixed
LW,LM,RB | 1 | FWL/AML | Q17; NOT CLEAN: mixed
FW,DM,WB | 1 | FW | NOT CLEAN: mixed
LW,LB,CB | 1 | FWL/AML | NOT CLEAN: mixed
FW,LB,LW | 1 | FW | NOT CLEAN: mixed
LW,LM,AM,CM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
FW,LB,RW | 1 | FW | NOT CLEAN: mixed
FW,LB,WB | 1 | FW | NOT CLEAN: mixed
LW,FW,RM,LM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
FW,AM,DM | 1 | FW | NOT CLEAN: mixed
FW,RB,CM | 1 | FW | NOT CLEAN: mixed
LW,RW,RM,AM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,FW,CB | 1 | FWL/AML | NOT CLEAN: mixed
LW,WB,LB,LM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,FW,DM | 1 | FWL/AML | NOT CLEAN: mixed
LW,WB,FW | 1 | FWL/AML | NOT CLEAN: mixed
LW,WB,CM | 1 | FWL/AML | NOT CLEAN: mixed
LW,WB,CB | 1 | FWL/AML | NOT CLEAN: mixed
LW,WB,AM | 1 | FWL/AML | NOT CLEAN: mixed
LW,FW,LM,AM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,RW,RM,LM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
DM,RW,AM | 1 | excluded | NOT CLEAN: mixed
FW,AM,CM,LM | 1 | FW | Q17; NOT CLEAN: mixed
LW,FW,LM,RM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
LW,RW,LM,RM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
DM,RW,LW | 1 | excluded | NOT CLEAN: mixed
LW,RW,LB,RB | 1 | FWL/AML | NOT CLEAN: mixed
LW,RW,LB | 1 | FWL/AML | NOT CLEAN: mixed
DM,WB,RB | 1 | excluded | clean
LW,FW,RB | 1 | FWL/AML | NOT CLEAN: mixed
FW,LM,WB | 1 | FW | Q17; NOT CLEAN: mixed
LW,RW,AM,CM | 1 | FWL/AML | NOT CLEAN: mixed
DM,FW,LW | 1 | excluded | NOT CLEAN: mixed
RB,RW,AM | 1 | excluded | NOT CLEAN: mixed
FW,RW,DM | 1 | FW | NOT CLEAN: mixed
CM,LW,RM | 1 | excluded | Q17; NOT CLEAN: mixed
LM,RM,LW,RW | 1 | excluded | Q17; NOT CLEAN: mixed
CM,LM,RB | 1 | excluded | Q17
CM,LM,RM,LB | 1 | excluded | Q17
CM,LM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
RM,LM,RW,LW | 1 | excluded | Q17; NOT CLEAN: mixed
LB,CB,CM | 1 | excluded | clean
RM,LM,LW,FW | 1 | excluded | Q17; NOT CLEAN: mixed
CM,LW,AM,FW | 1 | excluded | NOT CLEAN: mixed
CM,LW,DM | 1 | excluded | NOT CLEAN: mixed
RM,LM,CM,DM | 1 | excluded | Q17
RM,LW,CM,RW,LM | 1 | excluded | Q17; NOT CLEAN: mixed
LM,RM,WB,FW | 1 | excluded | Q17; NOT CLEAN: mixed
LB,CB,AM | 1 | excluded | NOT CLEAN: mixed
GK,RB | 1 | excluded | clean
CM,RB,FW,LB | 1 | excluded | NOT CLEAN: mixed
LM,RW,CM | 1 | excluded | Q17; NOT CLEAN: mixed
LM,RW,CM,LB | 1 | excluded | Q17; NOT CLEAN: mixed
RM,FW,RW,AM | 1 | excluded | Q17; NOT CLEAN: mixed
RM,FW,LW,LM | 1 | excluded | Q17; NOT CLEAN: mixed
GK,FW | 1 | excluded | NOT CLEAN: mixed
RM,LW,CM,RB | 1 | excluded | Q17; NOT CLEAN: mixed
RM,LW,FW | 1 | excluded | Q17; NOT CLEAN: mixed
DM,FW,CM | 1 | excluded | NOT CLEAN: mixed
RM,RW,CB | 1 | excluded | Q17; NOT CLEAN: mixed
CM,DM,WB | 1 | excluded | clean
LB,CM,LW | 1 | excluded | NOT CLEAN: mixed
CM,FW,RW,AM | 1 | excluded | NOT CLEAN: mixed
CM,FW,WB | 1 | excluded | NOT CLEAN: mixed
RM,RW,FW,LM | 1 | excluded | Q17; NOT CLEAN: mixed
LW,LB,CM | 1 | FWL/AML | NOT CLEAN: mixed
RM,RW,DM | 1 | excluded | Q17; NOT CLEAN: mixed
RM,RW,CM,AM | 1 | excluded | Q17; NOT CLEAN: mixed
LM,RM,AM,FW | 1 | excluded | Q17; NOT CLEAN: mixed
LB,CM,LM | 1 | excluded | Q17
CM,LM,DM,RM | 1 | excluded | Q17
LB,CM,DM | 1 | excluded | clean
CM,LB,RB | 1 | excluded | clean
LM,RM,FW,CM | 1 | excluded | Q17; NOT CLEAN: mixed
RM,RB,DM,CM | 1 | excluded | Q17
RM,RB,DM | 1 | excluded | Q17
LM,RM,FW,CM,WB | 1 | excluded | Q17; NOT CLEAN: mixed
LM,RM,FW,LW | 1 | excluded | Q17; NOT CLEAN: mixed
RM,LW,WB | 1 | excluded | Q17; NOT CLEAN: mixed
RM,LW,RB | 1 | excluded | Q17; NOT CLEAN: mixed
CM,RM,RB,DM | 1 | excluded | Q17
LM,RW,RB | 1 | excluded | Q17; NOT CLEAN: mixed
GK,DM | 1 | excluded | clean
RB,WB,RW | 1 | excluded | NOT CLEAN: mixed
RM,AM,WB | 1 | excluded | Q17; NOT CLEAN: mixed
DM,CB,LB | 1 | excluded | clean
RM,AM,LW | 1 | excluded | Q17; NOT CLEAN: mixed
DM,CB,LM | 1 | excluded | Q17
DM,CB,LM,CM | 1 | excluded | Q17
FW,RW,WB | 1 | FW | NOT CLEAN: mixed
DM,CB,RB | 1 | excluded | clean
LW,AM,DM | 1 | FWL/AML | NOT CLEAN: mixed
FW,RW,LM,LW | 1 | FW | Q17; NOT CLEAN: mixed
LW,AM,FW,CM | 1 | FWL/AML | NOT CLEAN: mixed
CM,RW,CB | 1 | excluded | NOT CLEAN: mixed
RB,WB,LW | 1 | excluded | NOT CLEAN: mixed
RB,WB,LM | 1 | excluded | Q17
LW,AM,LB | 1 | FWL/AML | NOT CLEAN: mixed
RB,WB,DM | 1 | excluded | clean
RB,WB,CM | 1 | excluded | clean
DM,CM,LW,LM | 1 | excluded | Q17; NOT CLEAN: mixed
RB,WB,AM | 1 | excluded | NOT CLEAN: mixed
LW,AM,LM,RM | 1 | FWL/AML | Q17; NOT CLEAN: mixed
RB,RW,WB | 1 | excluded | NOT CLEAN: mixed
FW,WB,CM | 1 | FW | NOT CLEAN: mixed
RM,CB,CM | 1 | excluded | Q17
RM,CB,DM | 1 | excluded | Q17
RM,CB,LM | 1 | excluded | Q17
LM,RW,RM,LW | 1 | excluded | Q17; NOT CLEAN: mixed
RM,DM,RB | 1 | excluded | Q17
FW,WB,RW | 1 | FW | NOT CLEAN: mixed
RM,DM,LB | 1 | excluded | Q17
LM,WB,CB | 1 | excluded | Q17
RM,DM,AM,LW | 1 | excluded | Q17; NOT CLEAN: mixed
LM,WB,CM | 1 | excluded | Q17
CM,WB,RM | 1 | excluded | Q17
RM,CM,WB | 1 | excluded | Q17
LM,WB,CM,RB | 1 | excluded | Q17
CM,WB,RW | 1 | excluded | NOT CLEAN: mixed
LM,WB,DM | 1 | excluded | Q17
FW,WB,RM | 1 | FW | Q17; NOT CLEAN: mixed
DM,AM,CB | 1 | excluded | NOT CLEAN: mixed
RM,CM,AM,RW | 1 | excluded | Q17; NOT CLEAN: mixed
RM,CM,AM,LM | 1 | excluded | Q17; NOT CLEAN: mixed
LM,WB,RW | 1 | excluded | Q17; NOT CLEAN: mixed
FW,WB,LM | 1 | FW | Q17; NOT CLEAN: mixed
RM,CB,RB | 1 | excluded | Q17
LB,WB,LW | 1 | excluded | NOT CLEAN: mixed
```

## Task 7: join to the Understat shot files

There is no shared player id.

| Key | Population | Matched | Rate |
|---|---|---|---|
| Name, league, season, exact name | 19,351 shot-file keys, 2017/18 on | 15,766 | 81.47% |
| Same, names compared without accents or word order | 19,351 | 17,535 | 90.62% |
| Shot rows on those matched keys | 365,334 | 336,346 | 92.07% |
| FBref keys at 900+ found in the shot file | 12,411 | 10,630 | 85.65% |
| Pool keys under the rule found in the shot file | 3,300 | 3,036 | 92.00% |
| Name, league, date, shot rows without own goals | 364,126 | 319,367 | 87.71% |
| League, date, score: exactly one FBref match | 14,526 shot-file matches | 11,154 | 76.79% |

- **Name join:** the agreement on minutes in Task 5 suggests it finds the right players, though no pair was checked by hand.
- **Match key:** league, date and score alone are weak. 2,657 matches have several candidates. 715 have none, of which 698 are in 2024/25, after FBref stops. Team names differ between sites, so a stronger key would need a team-name map.
- **Seasons before 2017/18:** 6,665 shot-file keys and 137,072 shot rows have no FBref season to join to.

Raw output is under Task 9, in the `fb_join.py` block, section E.

## Task 8: can 2014/15 enter the Pool with these minutes?

**NO.** The first FBref date in any league is 2017-08-04, and the backfill script starts at season end year 2018. HF has no minutes for 2014/15 either. 2015/16 and 2016/17 have HF minutes but no per-match positions here.

## Task 9: primary-position rule

**YES, for 2017/18 to 2023/24, with the limits in Findings.**

How the test ran, per player + league + season at 900+ FBref minutes:

- **Rule A, the closest to the plan:** started matches only, using the first listed position, and the most minutes wins.
- **Rule B:** the same, keeping substitute appearances.
- **Rule C:** the same as A, with minutes split evenly across listed positions.

Results:

| Check | Result |
|---|---|
| PlayerSeasons at 900+ | 12,411 |
| With a primary position under rule A | 12,410 (1 has no started match) |
| Exact ties | 15 |
| In the Pool under rule A | 3,300 (excluded 9,110) |
| Rule A vs B: Pool membership differs | 50 |
| Rule A vs C: Pool membership differs | 84 |
| Primary `LM` or `RM` | 889 (107 in 2022/23) |

**The substitute flag.** Taking the name on the left of "X for Y" as the incoming player was tested two ways.

- Exactly 11 non-substitutes remain on 96.92% of team-matches. That cannot show direction, since removing either side leaves 11.
- The direction test can: 248 of 100,684 left-side players reached 80 minutes, against 27,073 of 100,663 right-side players. So the left side is the substitute.

Rule A uses only team-matches with exactly 11 non-substitutes.

```
files checked: 30 | column counts: [48, 49, 50, 53, 55, 57, 58, 60, 64, 66, 71, 76]
columns naming start, sub, lineup or bench, across all files: []
```

```
ENG (37734, 33) matches by season end: {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 380, 2024: 389, 2025: 239}
ESP (44873, 33) matches by season end: {2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380, 2023: 370, 2024: 381, 2025: 220}
FRA (37503, 33) matches by season end: {2018: 380, 2019: 380, 2020: 279, 2021: 380, 2022: 380, 2023: 370, 2024: 307, 2025: 180}
GER (34742, 33) matches by season end: {2018: 306, 2019: 306, 2020: 306, 2021: 304, 2022: 306, 2023: 306, 2024: 335, 2025: 180}
ITA (43180, 33) matches by season end: {2018: 380, 2019: 380, 2020: 312, 2021: 380, 2022: 380, 2023: 370, 2024: 384, 2025: 228}
columns: ['MatchURL', 'League', 'Match_Date', 'Matchweek', 'Home_Team', 'Home_Formation', 'Home_Score', 'Home_xG', 'Home_Goals', 'Home_Yellow_Cards', 'Home_Red_Cards', 'Away_Team', 'Away_Formation', 'Away_Score', 'Away_xG', 'Away_Goals', 'Away_Yellow_Cards', 'Away_Red_Cards', 'Game_URL', 'Team', 'Home_Away', 'Event_Time', 'Is_Pens', 'Event_Half', 'Event_Type', 'Event_Players', 'Score_Progression', 'Penalty_Number', 'Competition_Name', 'Gender', 'Country', 'Tier', 'Season_End_Year']
Event_Half {2.0: 34343, 1.0: 8837}
Event_Type {'Substitute': 22194, 'Yellow Card': 12376, 'Goal': 6751, 'Penalty': 1008, 'Red Card': 313, 'Second Yellow Card': 299, 'Own Goal': 239}
player-like columns: ['Event_Players']
Event_Players on substitution rows: rows 22194 | contains ' for ': 22193 | null: 0
```

```
$ venv/bin/python3 -I tools/fb_join.py .. ~/sandbox/hf_dump/files/data
(sections A, B and C, with the value list moved to Task 6)
href without an 8-hex id: 0
distinct ids: 7370 | ids with more than one name: 53

=== A. substitute flag from fb_match_summary events
substitution events: 101332 | without ' for ': 1
event incoming names matched to a player row: 100684 of 101332
team-matches: 27659 | in event file: 27109 | exactly 11 non-substitutes: 26808 (96.92%)
non-substitutes per team-match, event matches only: {10: 6, 11: 26808, 12: 289, 13: 6}
=== team-matches with exactly 11 non-substitutes, by season and league
lg         ENG     ESP     FRA     GER     ITA
season                                        
2018    1.0000  0.9882  1.0000  1.0000  1.0000
2019    1.0000  0.9776  1.0000  0.9886  1.0000
2020    0.9895  0.9882  1.0000  1.0000  0.8211
2021    0.9908  0.9947  1.0000  0.9722  1.0000
2022    0.9895  0.9276  1.0000  0.9803  1.0000
2023    0.9961  0.9066  0.9526  0.9984  0.9711
2024    0.9961  0.9171  0.9984  0.9837  0.9961
2025    1.0000  1.0000  1.0000  1.0000  0.9978
2026    0.0000  0.0000  0.0000  0.0000  0.0000
direction test, Min>=80: left of ' for ' (incoming) 248 of 100684 | right of ' for ' (outgoing) 27073 of 100663
direction test, Min>=45: incoming 10344 | outgoing 96953
starter rows, Min<45: 3893 | substitute rows, Min>=80: 248 | substitute rows 100684

=== B. minutes per player-season vs HF
HF Understat file, name join (token set): both 19631 | HF only 2162 | FBref only 1981
HF keys >= 900 minutes: 12834 | of those joined: 11781 (91.80%)
HF Understat minutes, 2017-18 to 2023-24, all joined: keys 17347 | same 1978 (11.40%) | within 5 7562 (43.59%) | within 45 16729 (96.44%) | within 90 17224 (99.29%) | beyond 90 123
HF Understat minutes, 2017-18 to 2023-24, HF >= 900: keys 10380 | same 1127 (10.86%) | within 5 4005 (38.58%) | within 45 9923 (95.60%) | within 90 10275 (98.99%) | beyond 90 105
HF Understat minutes, 2024-25, partial FBref season: keys 2284 | same 75 (3.28%) | within 5 244 (10.68%) | within 45 539 (23.60%) | within 90 625 (27.36%) | beyond 90 1659
  2017-2018: keys 2418 | same 337 (13.94%) | within 5 1350 (55.83%) | within 45 2406 (99.50%) | within 90 2415 (99.88%) | beyond 90 3
  2018-2019: keys 2393 | same 360 (15.04%) | within 5 1276 (53.32%) | within 45 2379 (99.41%) | within 90 2393 (100.00%) | beyond 90 0
  2019-2020: keys 2414 | same 304 (12.59%) | within 5 1115 (46.19%) | within 45 2376 (98.43%) | within 90 2409 (99.79%) | beyond 90 5
  2020-2021: keys 2505 | same 269 (10.74%) | within 5 1135 (45.31%) | within 45 2455 (98.00%) | within 90 2490 (99.40%) | beyond 90 15
  2021-2022: keys 2569 | same 252 (9.81%) | within 5 1035 (40.29%) | within 45 2500 (97.31%) | within 90 2556 (99.49%) | beyond 90 13
  2022-2023: keys 2553 | same 243 (9.52%) | within 5 893 (34.98%) | within 45 2418 (94.71%) | within 90 2541 (99.53%) | beyond 90 12
  2023-2024: keys 2495 | same 213 (8.54%) | within 5 758 (30.38%) | within 45 2195 (87.98%) | within 90 2420 (96.99%) | beyond 90 75
HF >= 900: FBref sum below 900: 31 of 10380 | FBref below HF by >90: 83 | above by >90: 22
agree on the 900-minute gate, 2017-18 to 2023-24: 17273 of 17347

HF FBref file, id join: both 21595 | HF only 240 | match file only 15
HF FBref minutes, 2017-18 to 2023-24, all joined: keys 19052 | same 18209 (95.58%) | within 5 18799 (98.67%) | within 45 18889 (99.14%) | within 90 19031 (99.89%) | beyond 90 21
HF FBref minutes, 2017-18 to 2023-24, HF >= 900: keys 11320 | same 10725 (94.74%) | within 5 11138 (98.39%) | within 45 11185 (98.81%) | within 90 11304 (99.86%) | beyond 90 16

=== C. mapping
distinct Pos values: 993 | tokens outside the map: []
                     values    rows     minutes
single kind                                    
False  all excluded     294   23600   1770248.0
       all in Pool       38    9483    628559.0
       mixed            646   15975    994361.0
True   all excluded      11  251995  18032867.0
       all in Pool        4  106663   5887813.0

mixed values whose first token is in the Pool: rows 9149 | first token excluded: rows 6826

composite values naming LW or RW with AM or FW: 6208 rows

rows in table 407716 of 407716 | values marked clean 167 | not clean 826
rows clean 299320 | rows not clean 108396

=== D. primary position at 900+ FBref minutes, player + league + season (Q6)
PlayerSeasons at 900+: 12411 | by season: {2018: 1630, 2019: 1605, 2020: 1567, 2021: 1631, 2022: 1635, 2023: 1636, 2024: 1609, 2025: 1098}
rule A: first token, started matches only. Keys with a primary: 12410 | keys with no started match: 1 | exact ties: 15

rule A primary position counts
first
CB    2648
CM    1714
FW    1671
GK     936
RB     897
LB     879
DM     652
AM     579
RW     540
LW     510
WB     495
LM     453
RM     436

in the Pool under rule A: 3300 | excluded: 9110
rule A vs B (subs kept): position differs 202 | Pool membership differs 50
rule A vs C (minutes split across tokens): position differs 390 | Pool membership differs 84
Q17: primary LM or RM under rule A: 889 | 2022-23 season only: 107
rule A keys by season, Pool: {2018: 452, 2019: 407, 2020: 414, 2021: 411, 2022: 428, 2023: 449, 2024: 448, 2025: 291}

outside check: HF FBref broad position vs rule A primary, joined keys 12409
hf_pos     DF    FW   GK    MF
primary                       
AM          0    22    0   557
CB       2624     0    0    24
CM          3     1    0  1710
DM          2     0    0   650
FW          0  1589    0    82
GK          0     0  936     0
LB        831     0    0    48
LM          1     3    0   449
LW          1   158    0   351
RB        855     1    0    41
RM          0     2    0   434
RW          0   181    0   359
WB         12     2    0   480

=== E. join to Understat shot files
shot-file seasons before FBref starts (season end < 2018): keys 6665 | shot rows 137072 | keys joined 0
player-season key (name, league, season), shot keys 19351: exact 15766 (81.47%) | token set 17535 (90.62%) | unmatched 1816
shot rows on matched keys: 336346 of 365334 (92.07%)
=== token-set match rate by season end
            size    mean
season_end              
2018        2185  0.9318
2019        2165  0.9247
2020        2206  0.9175
2021        2260  0.9155
2022        2330  0.9069
2023        2309  0.9108
2024        2290  0.9009
2025        2292  0.8508
2026        1314  0.8942
=== token-set match rate by league
     size    mean
lg               
ENG  3844  0.9446
ESP  4080  0.8441
FRA  3877  0.8886
GER  3491  0.9370
ITA  4059  0.9224
FBref keys at 900+, in shot-file seasons: 12411 | found in shot file 10630 (85.65%) | not found 1781
of those, Pool under rule A: 3300 | found in shot file 3036 (92.00%) | not found 264

player-match key (name, league, date), shot rows 364126: same date 319367 (87.71%) | not found 44759
=== same-date rate by season end
season_end
2018    0.9324
2019    0.9372
2020    0.9326
2021    0.9226
2022    0.9129
2023    0.9117
2024    0.9067
2025    0.5468
2026    0.8869

match key (league, date, score), shot-file matches 14526: exactly one FBref match 11154 (76.79%) | several 2657 | none 715
none, by season end: {2018: 6, 2019: 1, 2021: 1, 2022: 2, 2023: 1, 2024: 6, 2025: 698}
```

## Limits of this check

- FBref positions were not compared with Understat's, because the site could not be reached. This is the largest unknown.
- Both HF files and the match files may share origins, so agreement shows consistency, not truth.
- Names-only mode meant no row could be inspected, so causes of odd counts are inferences and are marked as such.
- Q17's list of names and the Q30 examples were not produced.
- Duplicate Serie A fixtures were not removed, so a few minutes may be counted twice.
- The R scripts were read in part and not run. The repo was not cloned. Sports Reference's terms were not read.

## Scope

- Changed in the repo: this report only. No data files in the repo.
- Not touched: `config/`, `CLAUDE.md`, `GLOSSARY.md`, `docs/phase-1-plan.md`, issues, `.github/`. Nothing pushed.
- Sandbox kept at `~/sandbox/wfr` so results can be reproduced. The files for this check are in `files_fb`, `files_passing`, `files_fb_other`, `files_fb_eng`, `files_events` and `out_fb`. Remove them with `rm -rf ~/sandbox/wfr`, which also removes the shots vetting files.
