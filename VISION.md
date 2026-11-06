# Vision

Football Twin finds players whose seasons look statistically alike in how they shoot and create. Type a player and season and get their closest style twins, a 2D map and a Fingerprint. It matches how they shoot and create, not how they move, and a twin is a Style twin, never a level twin.

The value is a twin list a football reader trusts. Trust comes from a self-match test against a Random baseline and an outside review, not from our own grading (`docs/phase-1-plan.md`, Validation).

## Subdomains

- **Core:** MetricProfiles and TwinMatches. The 10 metrics, their shrinkage and standardising within each PeerGroup (`twin/domain/profiles.py`), and the distance and closeness percentiles (#9). Most effort goes here.
- **Supporting:** the Pool rule (`twin/domain/pool.py`), the stand-in join of shots to players (`twin/infrastructure/standin/`), the Build that writes the files (`twin/application/build.py`), and the validation report (#10).
- **Generic:** fetching Understat (`understatapi`, #15), file formats (Parquet, JSON), and the static site's hosting (#13). Reused, not built.
