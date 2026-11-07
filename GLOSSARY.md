# Football Twin

Finds players whose seasons look statistically alike in how they shoot and create.

## Language

### Players and seasons

**PlayerSeason**:
One player's time in one league in one season. A player who changes league mid-season has two.
_Avoid_: Player record, stint row, merged season

**Primary position**:
The named position where a PlayerSeason has the most minutes. Substitute appearances do not count as a position.
_Avoid_: Role, listed position

**Pool**:
The completed-season PlayerSeasons of forwards and attacking midfielders with at least 900 minutes. Only these can be returned as twins.
_Avoid_: Dataset, universe

**Searched season**:
A current-season PlayerSeason that can be looked up but is not in the Pool.
_Avoid_: Live player

### Measuring style

**MetricProfile**:
The 10 standardised metric values that describe a PlayerSeason's style.
_Avoid_: Vector, fingerprint data, feature set

**Fingerprint**:
The on-screen chart of a MetricProfile.
_Avoid_: Radar, profile chart

**PeerGroup**:
The PlayerSeasons a metric is standardised against: the qualifying attackers of one league-season.
_Avoid_: Cohort, comparison set

**Display stat**:
A number shown to the reader that is never part of a MetricProfile, such as goals or assists.
_Avoid_: Extra metric

**Finishing**:
Non-penalty goals minus non-penalty xG, per non-penalty shot, for one PlayerSeason. Own goals do not count. One of the 10 metrics since #30 (D30-2), in place of key passes per 90. It shrinks like npxG per shot, by normal-normal on each shot's goal minus xG (D30-3).
_Avoid_: Clinicality, conversion, overperformance

### Careers

**CareerProfile**:
The minutes-weighted mean of the MetricProfiles of one person's Pool PlayerSeasons, for a person with 6,000+ career minutes (#30). Each season keeps its own PeerGroup z-scores. Code: `twin.domain.careers.CareerProfile`.
_Avoid_: Career vector, career average, player profile

**CareerMatch**:
One CareerProfile returned as close to another, with its distance and closeness percentile. Closeness is against career pairs only (#30 decision 3). Code: `twin.domain.careers.CareerMatch`.
_Avoid_: Career neighbour, similar career

**Season twins**:
The TwinMatches of a PlayerSeason. For a player under 6,000 career minutes they are the only list, labelled "season twins" (D30-8).
_Avoid_: Fallback list, short-career twins

**Career minutes**:
The total minutes of one person's Pool PlayerSeasons, each stint with its own minutes (D30-7). Seasons under 900 minutes do not count. A career needs 6,000 or more (D30-1).
_Avoid_: Total minutes, career length

**Role group**:
Forward, Wide or Central AM, from a PlayerSeason's display position: FW is Forward, LW and RW are Wide, AM is Central AM (#30). A career's role group is the one with the most career minutes (D30-4).
_Avoid_: Role, position group

### Twins

**TwinMatch**:
One PlayerSeason returned as close to another, with its distance and closeness percentile.
_Avoid_: Similar player, neighbour, result

**Style twin**:
A TwinMatch reads as similarity in style, never in level. Twins can come from different leagues.
_Avoid_: Level twin, equivalent

### Validation

**Candidate method**:
A distance method that can become the winning method: Euclidean on z, cosine or Pearson.
_Avoid_: Model, algorithm

**Comparison method**:
A distance method reported beside the Candidate methods that can never win or be the default. The basketball method is one.
_Avoid_: Baseline method, 4th candidate

**Basketball method**:
Percentiles within league-season compared by Euclidean distance.
_Avoid_: NBA model

**Random baseline**:
The self-match rate expected by chance. It is the reference for a self-match result.
_Avoid_: Basketball method, control

**Self-match**:
The test of whether a PlayerSeason's own next season appears in its top 10.
_Avoid_: Backtest, stability

**Blind spot-check**:
The part of the outside review where a non-Claude model rates top-5 twin lists as plausible or not, on playing style alone. The reviewer sees player names and seasons, and has not seen our method, code or validation results.
_Avoid_: Face validity

### Stand-in data and the join

**Stand-in source**:
The private files in `data/standin/` (worldfootballR Understat shots, FBref positions and minutes, Hugging Face season totals) that stand in for live Understat while it is down. It may never publish. Code: `twin/infrastructure/standin/`.
_Avoid_: Test data, mock source

**Understat id**:
Understat's `player_id` on a shot row. It shares no id system with FBref, so a join to FBref goes through name, club and season inside a linked match.
_Avoid_: Player id (alone), shot id

**FBref id**:
The 8-character id in an FBref `Player_Href`. A PlayerSeason is keyed on it.
_Avoid_: Player id (alone), href

**Shot**:
One Understat shot row joined to a PlayerSeason, with its place, xG and outcome. Code: `twin.domain.records.Shot`.
_Avoid_: Attempt, event

**Season totals**:
One player-season's row in the Hugging Face file (`understat_xg_data`): minutes, goals, assists, shots, key passes, xA and xG buildup, found by the one written lookup (Q5).
_Avoid_: Season stats, aggregates

**Id merge**:
Two FBref ids for one player kept as one, only when name, team and season match and their matches never overlap. The merged player keeps the id they hold in other seasons, else the one with more minutes in that league-season.
_Avoid_: Dedupe, combine

**Name map**:
Step 2 of the join: a shot name with no roster match links to the one unmatched roster player on that club in that match who shares a last name or a whole name part. Each kept link is one row per player-season in `data/standin/name_map.csv`.
_Avoid_: Fuzzy match, alias table

**Season anchor**:
Step 3 of the join: in a match where step 2 found 2+ candidates, the link the same Understat id holds to one FBref id in at least 2 other matches that season for the same club.
_Avoid_: Season link, anchor match

**Minutes guard**:
The check on every name map and season anchor link: Understat season minutes against the linked id's FBref minutes, within the larger of 90 minutes or 10%. A link beyond the limit is listed for review and not joined.
_Avoid_: Minutes check (alone), sanity check

**Id collision**:
Two Understat ids on one FBref id in one league-season. Both stay unjoined and listed, unless a `merge_ids` review decision says so.
_Avoid_: Duplicate, clash

**Partial join**:
A player-season with less than 95% of its shot rows in linked matches joined, or a Pool candidate with no joined shots. Its shot and per-90 metrics are not used until review.
_Avoid_: Incomplete player, low coverage

**Held for review**:
A PlayerSeason that a review flag holds out of the Pool, and whose shot and per-90 metrics are not used. Code: `PlayerSeason.held_for_review`.
_Avoid_: Excluded, filtered

**Review decision**:
One row of Ahmed's `data/standin/review_decisions.csv`: an item type, its key, and `approve`, `reject`, `link_to` or `merge_ids`. Only these rows restore a stopped link or release a held PlayerSeason.
_Avoid_: Override, manual fix

**Shot gap**:
The absolute difference between a PlayerSeason's season totals shots and its shot rows minus own goals. A gap over 3 needs a review decision. A non-zero gap is `unexplained` until Ahmed's review gives its cause.
_Avoid_: Shot error, mismatch
