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

**Face validity pair**:
A pair of PlayerSeasons Ahmed names in advance as twins or not-twins. Only Ahmed writes these.
_Avoid_: Test case, example, ground truth
