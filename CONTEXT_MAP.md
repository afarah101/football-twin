# Context map

One bounded context, `twin/` (Q24). Its words are in `GLOSSARY.md`.

| Layer | Folder | Holds |
|---|---|---|
| Domain | `twin/domain/` | PlayerSeason, Shot, LoadedSource and the Source interface (`records.py`), the Pool rule (`pool.py`), MetricProfiles (`profiles.py`). Twins come in #9. No pandas, no source word |
| Application | `twin/application/` | The Build (`build.py`): a LoadedSource in, one MetricProfile file per league-season out |
| Infrastructure | `twin/infrastructure/standin/` | The stand-in loader, now. `twin/infrastructure/understat/` holds the live adapter in #15 |
| Interface | `twin/interface/web/` | The static site, from #11 |

## Outside systems

| System | Relationship | Translation point |
|---|---|---|
| Stand-in source (worldfootballR Understat shots, FBref positions and minutes, HF season totals) | Anti-corruption layer | `twin/infrastructure/standin/loader.py` returns a `LoadedSource` with no source word. It may never publish |
| Understat, live (#15) | Anti-corruption layer | The live adapter returns the same `LoadedSource`. Only it can set `may_publish`, through the publishing gate |
| The site and its host (#13) | Published language: the per-league-season JSON | `twin/application/build.py`. A public file is written only through `write_public_files`, which fails unless `may_publish` is True. A stand-in run writes only under `build/private/` |
