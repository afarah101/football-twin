# Library vetting: pyarrow, rdata and pyreadr

Run date: 2026-11-03. Repo position at the start: `70d590f`, level with origin.

## Verdict

| Library | Version | Licence | Verdict | Allowed list |
|---|---|---|---|---|
| pyarrow | 26.0.1 | Apache-2.0 | **SAFE** | **Added** |
| rdata | 1.1.0 | MIT | **PENDING.** No security blocker, but no file meets the strict comparison rule. | **Not added**, waits for Ahmed |
| pyreadr | 0.5.9 | AGPL-3.0-or-later | **No security blocker, not allowed.** AGPL needs Ahmed's approval. | **Not added** |

**rdata did not MATCH under the decision rule.** All 35 files are `DIFF`, because every file has dtype differences. The data agrees on every comparison: rows, column names, nulls and values are the same in all 35 files. Under the rule, pyarrow is added, rdata stays PENDING, and the work stops for Ahmed.

**Issue #3 is still blocked.** No allowed library can read `.rds` files until Ahmed decides.

**Release assets:** all 38 hashes match.

## Decision for Ahmed

The rule treats any dtype difference as a difference, so it cannot pass rdata as it stands. The options are:

| Option | What changes | Cost |
|---|---|---|
| **A. Accept rdata (recommended)** | Add rdata to the allowed list. Accept that its dtypes differ, and fix one target schema in the trim. | Reads about 5 times slower here, and needs `default_encoding="utf8"`. The Parquet round-trip must be repeated on rdata's output. |
| B. Approve pyreadr | Add pyreadr to the allowed list. | AGPL enters the stack, which is your call. |
| C. Keep both out | Find another reader. | More vetting, and #3 stays blocked. |

Why A: every value agrees, and pyreadr is the one with the awkward types here. It returns 68 columns as `object`, holding Python ints mixed with float `NaN`, where rdata returns `Int32`.

## Findings

| Severity | Finding | Evidence |
|---|---|---|
| Critical | No allowed library can read the 35 `.rds` originals, so #3 and the trim cannot start. | Decision rule, comparison table |
| Warning | The Parquet round-trip was proven on pyreadr's output only. rdata returns different dtypes (`string`, `Int32`, `boolean`), and these have not been written to Parquet. | `probe.py` reads `.rds` with `pyreadr.read_r` |
| Warning | rdata crashes on real data without `default_encoding="utf8"`: `UnicodeDecodeError` on a GER file. | `out/peek_ger.txt` |
| Warning | rdata's index starts at 1 and pyreadr's at 0. Index matched in 0 of 35 files. Any code using the index would be off by one, so the trim must drop it. | Tally; the offset of exactly 1 was checked on the 7 files below |
| Warning | The first `gitleaks` wheel scan was invalid: it scanned about 0 bytes and reported no leaks. Results below come from a rescan of unpacked wheels. | `sweep/gitleaks.txt` vs rescan |
| Warning | Issue #1 also holds an allowed libraries list. It was out of scope, so it now differs from the plan. | Scope of this task |
| Info | The pyarrow wheel was uploaded on the day of this vetting, so a clean CVE check says little yet. | PyPI: 2026-11-03T10:52:41 |
| Info | Everything ran on Python 3.15 on macOS arm64. Nothing was tested on the Python or OS the build will use. | Wheel names |
| Info | The 3 `.csv` originals are not part of the comparison, because neither library reads them. | `release_files.txt`: 38 files, 35 `.rds` |
| Info | Both readers could share a mistake and still agree. They are separate code (Python in rdata, the C library librdata in pyreadr), which makes this unlikely, but neither is a reference copy from R. | R was not used |

## Comparison: rdata vs pyreadr

Command, with network and home writes blocked:

```
caffeinate -i sandbox-exec -f nonet.sb venv/bin/python3 -I -B compare.py release_files.txt out/compare.log
```

Totals across 35 files: 2673934 rows, 129,153,920 cells, 1,157 dtype differences, 0 null differences, 0 value differences. Reading took 642 s with rdata and 125 s with pyreadr. Peak memory was 2.78 GiB.

There are no cell-level differences to list, so no file has a row index or a pair of values to show. Each dtype difference covers a whole column.

| File | Result | Rows (pyreadr/rdata) | Columns (pyreadr/rdata) | Same names | Dtype diffs | Null diffs | Value diffs | First 5 differing columns (all `str` vs `string`) | rdata s |
|---|---|---|---|---|---|---|---|---|---|
| bundesliga_shot_data.rds | DIFF | 88214 / 88214 | 22 / 22 | yes | 12 | 0 | 0 | league, result, player, h_a, situation | 8 |
| epl_shot_data.rds | DIFF | 107838 / 107838 | 22 / 22 | yes | 12 | 0 | 0 | league, result, player, h_a, situation | 10 |
| la_liga_shot_data.rds | DIFF | 100188 / 100188 | 22 / 22 | yes | 12 | 0 | 0 | league, result, player, h_a, situation | 9 |
| ligue_1_shot_data.rds | DIFF | 96140 / 96140 | 22 / 22 | yes | 12 | 0 | 0 | league, result, player, h_a, situation | 9 |
| serie_a_shot_data.rds | DIFF | 110026 / 110026 | 22 / 22 | yes | 12 | 0 | 0 | league, result, player, h_a, situation | 10 |
| ENG_M_1st_passing_player_advanced_match_stats.rds | DIFF | 83613 / 83613 | 55 / 55 | yes | 47 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 31 |
| ESP_M_1st_passing_player_advanced_match_stats.rds | DIFF | 83106 / 83106 | 55 / 55 | yes | 47 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 32 |
| FRA_M_1st_passing_player_advanced_match_stats.rds | DIFF | 78973 / 78973 | 71 / 71 | yes | 62 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 27 |
| GER_M_1st_passing_player_advanced_match_stats.rds | DIFF | 69868 / 69868 | 55 / 55 | yes | 47 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 26 |
| ITA_M_1st_passing_player_advanced_match_stats.rds | DIFF | 86868 / 86868 | 71 / 71 | yes | 62 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 30 |
| ESP_M_1st_defense_player_advanced_match_stats.rds | DIFF | 87315 / 87315 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 18 |
| ESP_M_1st_misc_player_advanced_match_stats.rds | DIFF | 87340 / 87340 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 18 |
| ESP_M_1st_passing_types_player_advanced_match_stats.rds | DIFF | 87400 / 87400 | 48 / 48 | yes | 46 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 32 |
| ESP_M_1st_possession_player_advanced_match_stats.rds | DIFF | 76729 / 76729 | 60 / 60 | yes | 51 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 28 |
| FRA_M_1st_defense_player_advanced_match_stats.rds | DIFF | 78973 / 78973 | 53 / 53 | yes | 46 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 26 |
| FRA_M_1st_misc_player_advanced_match_stats.rds | DIFF | 79421 / 79421 | 50 / 50 | yes | 46 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 28 |
| FRA_M_1st_passing_types_player_advanced_match_stats.rds | DIFF | 78973 / 78973 | 64 / 64 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 17 |
| FRA_M_1st_possession_player_advanced_match_stats.rds | DIFF | 78973 / 78973 | 71 / 71 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 16 |
| GER_M_1st_defense_player_advanced_match_stats.rds | DIFF | 69868 / 69868 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 14 |
| GER_M_1st_misc_player_advanced_match_stats.rds | DIFF | 69668 / 69668 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 14 |
| GER_M_1st_passing_types_player_advanced_match_stats.rds | DIFF | 69652 / 69652 | 48 / 48 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 14 |
| GER_M_1st_possession_player_advanced_match_stats.rds | DIFF | 69868 / 69868 | 55 / 55 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 14 |
| ITA_M_1st_defense_player_advanced_match_stats.rds | DIFF | 87089 / 87089 | 57 / 57 | yes | 50 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 29 |
| ITA_M_1st_misc_player_advanced_match_stats.rds | DIFF | 77736 / 77736 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 16 |
| ITA_M_1st_passing_types_player_advanced_match_stats.rds | DIFF | 86868 / 86868 | 64 / 64 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 18 |
| ITA_M_1st_possession_player_advanced_match_stats.rds | DIFF | 86868 / 86868 | 76 / 76 | yes | 66 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 30 |
| ENG_M_1st_defense_player_advanced_match_stats.rds | DIFF | 83515 / 83515 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 18 |
| ENG_M_1st_keeper_player_advanced_match_stats.rds | DIFF | 5938 / 5938 | 52 / 52 | yes | 26 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 1 |
| ENG_M_1st_misc_player_advanced_match_stats.rds | DIFF | 81328 / 81328 | 49 / 49 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 18 |
| ENG_M_1st_passing_types_player_advanced_match_stats.rds | DIFF | 83613 / 83613 | 48 / 48 | yes | 46 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 31 |
| ENG_M_1st_possession_player_advanced_match_stats.rds | DIFF | 81667 / 81667 | 55 / 55 | yes | 27 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 17 |
| ESP_M_1st_match_summary.rds | DIFF | 44873 / 44873 | 33 / 33 | yes | 26 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 8 |
| FRA_M_1st_match_summary.rds | DIFF | 37503 / 37503 | 33 / 33 | yes | 26 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 7 |
| GER_M_1st_match_summary.rds | DIFF | 34742 / 34742 | 33 / 33 | yes | 26 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 6 |
| ITA_M_1st_match_summary.rds | DIFF | 43180 / 43180 | 33 / 33 | yes | 26 | 0 | 0 | MatchURL, League, Match_Date, Matchweek, Home_Team | 8 |

### Every dtype pair

`compare.log` keeps the first 5 dtype differences per file. A separate pass counted all 1,693 columns:

| pyreadr | rdata | Columns | Result |
|---|---|---:|---|
| `str` | `string` | 1,055 | different |
| `float64` | `float64` | 536 | same |
| `object` | `Int32` | 68 | different |
| `int32` | `Int32` | 30 | different |
| `bool` | `boolean` | 4 | different |

That is 1,157 differing columns, which matches the total from `compare.log`.

### Second check with `pandas.equals`

This check does not use the `compare.py` code. After casting rdata's columns to pyreadr's dtypes and dropping the index, `pandas.equals` passed on 28 of 35 files.

The other 7 files needed explaining, because `compare.py` found no value differences in them:

- FRA passing, defense and misc
- ITA passing, defense and possession
- ESP possession

Exactly 68 columns fail across those 7 files, and they are the 68 `object` vs `Int32` columns. In all 68:

- Nulls are in the same positions.
- Non-null cells are equal as numbers.
- The only difference is how a null is stored: float `NaN` in pyreadr, `pd.NA` in rdata.

So this is a representation difference, not a data difference.

### What the comparison can't see

- `NaN` and `NA` both count as null, so it cannot tell them apart.
- `-0.0` and `0.0` count as equal.
- Where dtypes are not both numeric, cells are compared as text.

### Checks on the comparison itself

- `compare.py` runs a self-check on every start. It must detect a changed value, a changed null, a changed string, a changed dtype, a renamed column and a missing row.
- Resume on a full log: `already logged 35`, and the log's hash is unchanged.
- Resume on a damaged copy with the last line cut short: `already logged 34`, the file ran again, and the name and status columns hash the same as the real log.

The run needed one pass. The tool's 10-minute limit moved the same process to the background at 10 minutes. It finished with exit code 0 and was not restarted.

### Why the earlier run left an empty log

The earlier command piped output through `cut` before writing to `compare.log`. `cut` holds its output in a buffer when writing to a file, so nothing had reached the log when the run was stopped at 16:19. The notice records `killed` and gives no reason. `compare.py` now writes and syncs each line itself.

## pyarrow 26.0.1: SAFE

| Check | Result |
|---|---|
| Source | `apache/arrow` at `9e5d6978e9acf372cc989aaaf94e863fe8582c90` |
| Wheel | SHA-256 `2c118754a0abe0bf20ef17432f95534ebb0ded37a48b6e8690cdd02625a86d97`, matches PyPI |
| Licence | Apache-2.0 |
| CVEs | `osv-scanner` on `pyarrow==26.0.1`: no issues |
| Semgrep | 6 findings on the source, none on a path we use (below) |
| Gitleaks | 5 `generic-api-key` hits in the wheel, none a real secret (below) |
| Own Parquet tests | 323 passed, 14 skipped, 1 xfailed, 1 xpassed, 16 errors |
| Parquet round-trip | 38 of 38 files `same True`, 0 differences, 2,773,096 rows, 1.88 GiB down to 0.024 GiB |
| Network or subprocess during the round-trip | None: `audit events (network, subprocess): []` |

The 16 test errors come from the test setup, not the library: 12 are `PermissionError` from opening a socket, which the sandbox blocks, and 4 need `PARQUET_TEST_DATA`, which is not installed.

Semgrep findings:

| Rule | Location | Assessment |
|---|---|---|
| `tarfile-extractall-traversal` | `util.py:293` | Inside `download_tzdata_on_windows`, which is deprecated and has no callers outside tests. Not on our path. |
| `dynamic-urllib-use-detected` | `util.py:236` | Download helper used by that same function. |
| `non-literal-import` | `__init__.py:90` | Imports `pyarrow.{module}`, a pyarrow submodule. |
| `dangerous-globals-use` (3) | `compute.py:218`, `compute.py:341` | Reads and fills pyarrow's own function table. |

Gitleaks hits:

| Location | Assessment |
|---|---|
| `pyarrow/_azurefs.pyx:95` | Sample `account_key` in a docstring example |
| `pyarrow/tests/parquet/test_encryption.py:1072`, `1075` | Test `footer_key` values |
| `pyarrow/include/arrow/vendored/xxhash/xxhash.h:5012`, `5061` | Variables named `data_key_lo` and `data_key_hi` in a hash library |

`osv-scanner` on the `arrow/python` folder also lists 4 setuptools advisories against version 9.1.0, from `requirements-build.txt`. That is a build-time file. setuptools is not installed in the test environment.

## rdata 1.1.0: PENDING

| Check | Result |
|---|---|
| Source | `vnmabus/rdata` at `c5a659f327b45447498d1d7c9a6c2ccd4eb93d22` |
| Wheel | SHA-256 `12efb7597725d6db6cc78d84eb522a9634008f8fce1c2733b7fd42b9013bc41f`, matches PyPI |
| Licence | MIT |
| Requires | numpy, xarray, pandas, typing_extensions |
| CVEs | `osv-scanner` on rdata, typing_extensions, xarray, numpy, pandas, packaging, python-dateutil and tzdata pins: no issues |
| Semgrep | 2 findings, 19 files scanned, 0 errors. Both are `python37-compatibility-importlib2` on `importlib.resources` imports, and rdata requires Python 3.11 or later. |
| Gitleaks | 534 commits: no leaks. Unpacked wheel: no leaks. |
| Risky calls | Only `rdata/testing.py`, which runs `Rscript` through `subprocess`. No non-test code calls it. |
| Own tests | 673 passed, 116 skipped, 30 subtests passed, 1 failed |
| Comparison | 35 of 35 `DIFF`, on dtypes only |

The failed test is `test_write.py::test_convert_dataframe_pandas_dtypes`, an `UnboundLocalError` in `rdata/conversion/to_r.py`. It sits in rdata's write path, and the project only reads.

The earlier session recorded that an independent code read found no way for a file to run code in rdata. That read was not repeated here. The vetting in `docs/reports/WFR_shots_vetting.md` also walks the raw bytes of the `.rds` files and refuses types that can hold or reach code.

## pyreadr 0.5.9: not allowed (AGPL)

| Check | Result |
|---|---|
| Source | `ofajardo/pyreadr` at `f0de9ea45b71c5d1274ddcdd1431de60af05f8c5` |
| Wheel | SHA-256 `d64446823fb174ffa17f211f6d092e4323ce51ce9204905e35f5b7657d225f6a`, matches PyPI |
| Licence | **AGPL-3.0-or-later**. The wheel also ships `LICENSE_librdata` and `LICENSE_jamovi_readstat`. |
| CVEs | `osv-scanner` on `pyreadr==0.5.9`: no issues. The C libraries bundled in its source are not covered, because OSV found no package sources there. |
| Semgrep | 1 finding, on `pyreadr.download_file`, which is not used. 7 parse errors on bundled C files, so those files were only partly scanned or not scanned. |
| Gitleaks | 218 commits: no leaks. Unpacked wheel: no leaks. |
| Own tests | 57 run, 1 skipped, 4 errors |

The 4 test errors are the `expanduser` tests, which write to the home folder. The sandbox blocks that, and the errors shown are `PermissionError`.

In this task pyreadr was used only inside `~/sandbox`, as the other side of the comparison. It was not added to the project.

## Release assets

Release: <https://github.com/afarah101/football-twin/releases/tag/stand-in-originals>. The repo is private, and the release is neither a draft nor a prerelease. It holds 38 assets, 2,018,792,469 bytes.

Each asset was downloaded and hashed, then compared with the release notes, GitHub's digest, its size, and the local original. Mismatches: 0.

| File | Bytes | SHA-256 of the download | Release notes | GitHub digest | Size | Local original |
|---|---:|---|---|---|---|---|
| ENG_M_1st_defense_player_advanced_match_stats.rds | 71356210 | `a7ef11574455db1aa086377ef90a6a87239365538c3ee7e038725d9bfe47d9b9` | match | match | match | match |
| ENG_M_1st_keeper_player_advanced_match_stats.rds | 5119293 | `963ea839deabf5866bf25f1c21b49124b0fc79b71254f9b6ad1b199ee78c063c` | match | match | match | match |
| ENG_M_1st_match_summary.csv | 19135823 | `50d6f42a81bba279f734439d356e0512ab7e9d2ef9e74db98856dd3db2b45861` | match | match | match | match |
| ENG_M_1st_misc_player_advanced_match_stats.rds | 69500306 | `9c8b96b0bf1166c51cd996b0b16eaebfaa633c0981d028feca71d6ea04e738c2` | match | match | match | match |
| ENG_M_1st_passing_player_advanced_match_stats.rds | 77880394 | `9cc109613af0c89624ffdf845dcffcb5e1c48b779d160fd4a592fd7c4f6dcf1f` | match | match | match | match |
| ENG_M_1st_passing_types_player_advanced_match_stats.rds | 72714944 | `26c3cb1c949d29a52be80774ea8c3f181f089ba386ec77658a90049df14005b5` | match | match | match | match |
| ENG_M_1st_possession_player_advanced_match_stats.rds | 73692648 | `0380e5719d050847bda441983e8ec9560cd6529d74d74a10efd6cb36403d0c7d` | match | match | match | match |
| ESP_M_1st_defense_player_advanced_match_stats.rds | 68473878 | `6c6edcb327338fb1fdc2fcab428dbbb47ed9cc401b91df3146edb689cb02a6d6` | match | match | match | match |
| ESP_M_1st_match_summary.rds | 28645985 | `f8d0532f1110f3bdeea10fd6a164c00a1f57c6dcc1d7484f5feb818ba4697c6e` | match | match | match | match |
| ESP_M_1st_misc_player_advanced_match_stats.rds | 68494697 | `e06350efd8e4e4f7bf6b729b78399a012176fc598121f2772b4b9660027f8b9f` | match | match | match | match |
| ESP_M_1st_passing_player_advanced_match_stats.rds | 71563880 | `0915ccb4f6c964f7f3b5d829b9a6079c4bc79a0bcee6f1dc4777fb0a3a020230` | match | match | match | match |
| ESP_M_1st_passing_types_player_advanced_match_stats.rds | 69865362 | `01a1a30460e92e7ce362bab5338907f52504d1e120b1a05d7293f1f09256f0e4` | match | match | match | match |
| ESP_M_1st_possession_player_advanced_match_stats.rds | 67454103 | `00bcb883f245a4c73c61851bee7bb4818d66f2bd97844ba94c5e54a715bc03fe` | match | match | match | match |
| FRA_M_1st_defense_player_advanced_match_stats.rds | 64436008 | `9948a5e024dbc37dc7231f870604f97f0bc2813b23d20a7152a4784808a04e32` | match | match | match | match |
| FRA_M_1st_match_summary.rds | 23958653 | `7cb154acdc243cb252a48091fe586b0e7ca0cf85f103b9af2b2677c053eff56c` | match | match | match | match |
| FRA_M_1st_misc_player_advanced_match_stats.rds | 64093040 | `aafe3c5e59d8ba35e5510a4143bc1eb0bd6af62e721bf2bb5426687abc0d3e2d` | match | match | match | match |
| FRA_M_1st_passing_player_advanced_match_stats.rds | 71835961 | `9312d576021d26b5ea8c14a6cdee28638c118e22a921bf6c861afd6eec6f2623` | match | match | match | match |
| FRA_M_1st_passing_types_player_advanced_match_stats.rds | 71337372 | `f071c00d319a8a8562be8164fc6347dcbb9737dcf1d3f939cc8ff96f633f5ae6` | match | match | match | match |
| FRA_M_1st_possession_player_advanced_match_stats.rds | 75759965 | `39539d465b5a21253d0540155316b73c8653d5ed6e47ef6400ceadc212e9238f` | match | match | match | match |
| GER_M_1st_defense_player_advanced_match_stats.rds | 59848163 | `6c5286f084a7c69b94264585accc1cfaab022c63f0bd130da08bdb0068722ca0` | match | match | match | match |
| GER_M_1st_match_summary.rds | 24724588 | `dc9356a544132e92c6e9831e4d5fbfa176abab82c347209b6380b8014fdbb913` | match | match | match | match |
| GER_M_1st_misc_player_advanced_match_stats.rds | 59669628 | `eacb8d76af227e2a60f1ed8b70e967da6a23398f254b229809ac45919198de03` | match | match | match | match |
| GER_M_1st_passing_player_advanced_match_stats.rds | 65218621 | `64f2488bf5358bb7011368d047def48c099f44244e3642bd9fb4b0aa5a1e2fc4` | match | match | match | match |
| GER_M_1st_passing_types_player_advanced_match_stats.rds | 59106802 | `f79a66cad851e0df013d149436372320191b848864ff5119b9f304acd5bb73ac` | match | match | match | match |
| GER_M_1st_possession_player_advanced_match_stats.rds | 63201463 | `9506d49cd2af4bc48a4fefd1389867363cff207b51c87d0c04b4644645ff2da3` | match | match | match | match |
| ITA_M_1st_defense_player_advanced_match_stats.rds | 72737361 | `b75b2819e1dbf6f811fa9b00c6d1b20136692c1acbb374b194e5fa675b70531b` | match | match | match | match |
| ITA_M_1st_match_summary.rds | 27662572 | `2b09168c196fc4004b6ba3992c30f1883589bc50d2c28570389a70166ad56a2c` | match | match | match | match |
| ITA_M_1st_misc_player_advanced_match_stats.rds | 61174721 | `fdbaaef29028309c925c2fe870101db8be8711b475f368acbc6951375ed4cbbb` | match | match | match | match |
| ITA_M_1st_passing_player_advanced_match_stats.rds | 79346587 | `96e8e99ce2b8f7cb91d6af87752ce0dd363d8f1627ccfe7f9a14ac25d575ca43` | match | match | match | match |
| ITA_M_1st_passing_types_player_advanced_match_stats.rds | 78742349 | `e0fae3c5ce6eaa8260b610505a0f201dd32938e0518a3446525faac1ee275e72` | match | match | match | match |
| ITA_M_1st_possession_player_advanced_match_stats.rds | 81039751 | `2a09ba7cf18e3e83f5b7332a5fd36f2728607fb6a04b56d50f95b664af8bdd3a` | match | match | match | match |
| bundesliga_shot_data.rds | 25319943 | `7481d4eea7a32c261ae45711e735a074c23aa4530a181c7f3c490150e8639bee` | match | match | match | match |
| epl_shot_data.rds | 29646577 | `c51e6661029a2b0f2b770bd9fc0a54da1913b303d6c6c908d11008f5c526ab60` | match | match | match | match |
| la_liga_shot_data.rds | 27526464 | `1a3a80f5e42c797ad056cb38fa10ca7c27b11f90987ee1921347eeba0728a803` | match | match | match | match |
| ligue_1_shot_data.rds | 26342221 | `bbc5bc4e6f0ffc94f01ec016e4df45dc6d53264f92c917e113c0c5b9ecdbc49a` | match | match | match | match |
| master_player_stats.csv | 7815906 | `96a5379af53321616d727bb49259befc0506755b0e2829859ce191146f65a8c8` | match | match | match | match |
| serie_a_shot_data.rds | 30103636 | `fb024cc8fc8aa72edf6b826629ffe1f36dc3f2e20645f3aade85a4f2ec36b559` | match | match | match | match |
| understat_xg_data.csv | 4246594 | `4e3751c47205c274315bb99f7df983adc4d15fe03c454590299587e7d3b3e475` | match | match | match | match |
