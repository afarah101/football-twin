# Context map

Two bounded contexts. Their words are in `GLOSSARY.md`: Twin's in the main sections, Claim Check's in the Claim Check section.

| Context | Folder | Model |
|---|---|---|
| Twin (Q24) | `twin/` | PlayerSeasons, MetricProfiles and TwinMatches |
| Claim Check (designed 7 Nov 2026, `docs/specs/claim-check.md`; no code yet) | `claim_check/`, planned | Claims, ClaimQueries, Reference groups and Verdicts |

## Twin

| Layer | Folder | Holds |
|---|---|---|
| Domain | `twin/domain/` | PlayerSeason, Shot, LoadedSource and the Source interface (`records.py`), the Pool rule (`pool.py`), MetricProfiles (`profiles.py`). Twins come in #9. No pandas, no source word |
| Application | `twin/application/` | The Build (`build.py`): a LoadedSource in, one MetricProfile file per league-season out |
| Infrastructure | `twin/infrastructure/standin/` | The stand-in loader, now. `twin/infrastructure/understat/` holds the live adapter in #15 |
| Interface | `twin/interface/web/` | The static site, from #11 |

## Claim Check (planned)

Planned layers: `claim_check/domain/`, `application/` (the LangGraph graph), `infrastructure/`, `interface/`. The layer contents come from `/to-spec`.

## Between the contexts

| Upstream | Downstream | Relationship | Translation point |
|---|---|---|---|
| Twin's stand-in join (`twin/infrastructure/standin/player_join.py`) and records (`twin/domain/records.py`) | Claim Check | **Conformist.** Claim Check takes the join as it is and translates none of its rules. Its own adapter calls the join functions read-only and builds PlayerMatch and TeamMatch records. Twin code is never changed for Claim Check | Claim Check's stand-in adapter, planned in `claim_check/infrastructure/`. Two pin tests keep it in step: 315,073 joined shots plus `scripts/measure_rule3.py`'s two pinned Pool lines, and per-match minutes summed per PlayerSeason equal Twin's season minutes for every Pool PlayerSeason |

## Outside systems

| System | Context | Relationship | Translation point |
|---|---|---|---|
| Stand-in source (worldfootballR Understat shots, FBref positions and minutes, HF season totals) | Twin | Anti-corruption layer | `twin/infrastructure/standin/loader.py` returns a `LoadedSource` with no source word. It may never publish |
| Understat, live (#15) | Twin | Anti-corruption layer | The live adapter returns the same `LoadedSource`. Only it can set `may_publish`, through the publishing gate |
| The site and its host (#13) | Twin | Published language: the per-league-season JSON | `twin/application/build.py`. A public file is written only through `write_public_files`, which fails unless `may_publish` is True. A stand-in run writes only under `build/private/` |
| Groq (Llama-3) | Claim Check | Anti-corruption layer | Planned. It fills the Extraction and writes the final 2 lines from given numbers. It never computes a number |
| LangFuse | Claim Check | Anti-corruption layer | Planned. One trace per Claim, with spans named in Claim Check's words |
| Free RSS headline feeds (later) | Claim Check | Anti-corruption layer | Planned. Headlines become Claims. No paywalled or terms-restricted site |
