# T1: understatapi vetting report

Issue: afarah101/football-twin#2. Parent spec: #1. Run date: 2026-11-03. Library vetted: `understatapi` 0.7.1 at commit `d1252d9734e94ba98c681d2e41d467f1edb7aaf5`.

## Verdict: UNSURE

| Question | Answer |
|---|---|
| Is the library's own code malicious or risky? | No evidence of that. All 16 package files read. No exec, eval, subprocess, pickle, base64 or file writes. Network calls go only to `https://understat.com/`. |
| Is the default install safe? | **No.** `pip install understatapi` forces hard pins that carry 14 known advisories, CVSS up to 9.1. |
| Is there a clean way to install it? | Yes, offline evidence only. `--no-deps` plus current dependency versions gives 0 advisories and all 31 library tests pass. |
| Does it still work against Understat today? | **Not known.** Ahmed approved one live call. It ran and failed at the network: a Virgin Media router refuses any route to Understat's hosting range, so no HTTP request reached the site. This says nothing about the library. |

**Safe to wire in at ticket 5 (issue #6, Understat adapter): NO, not yet.** It becomes YES when all of these are true:

1. One live call reaches understat.com from a network that can route to it, and works (vetting step 5).
2. The install is hash-pinned with `--no-deps` and uses patched dependency pins, not the library's pins.
3. Issue #6 handles the two adapter findings below: masked HTTP errors and no timeout.

Plan header:

- Altitude: a go or no-go on `understatapi` that issue #6 can act on without re-vetting.
- Depth: read every file that runs, audit-hook the runtime, test the install on patched dependencies. Outside judges are osv-scanner, semgrep and gitleaks.
- Range: supply-chain security, dependency management, API contract testing. Adversarial reviewer: the evaluator skill, not yet run.

## Findings

| Severity | Finding | Evidence | Action for issue #6 |
|---|---|---|---|
| **Critical** | Hard pins in `install_requires` bring 14 advisories: urllib3 1.26.5 (10), idna 2.10 (2), certifi 2025.11.12 (1, CVSS 9.1), requests 2.32.5 (1). Exploitability for our use was not assessed. | Step 3, Step 6d | Never use the default install. Use `--no-deps` with own pins. |
| **Critical** | Understat is unreachable from this machine's network. This is a project problem, not a library problem. It also blocks #3 (real fixtures) and the plan's laptop backfill (#7), not only this check. One GitHub Actions run also failed to connect, which matters for the Monday job (#13); see "GitHub Actions probe". | Step 4, GitHub Actions probe | Ahmed chooses a network that can reach it. |
| Warning | Live behaviour is unverified. Every library test is mocked, the one live call never reached the site, and the last release is 8 months old. | Step 4 | Repeat the live call first. |
| Warning | Player, match and team endpoints turn **every** HTTP error into `InvalidPlayer`, `InvalidMatch` or `InvalidTeam`. A 429 or 503 looks like a bad ID. League endpoints raise a plain `HTTPError`. This matters for Q25 (fail on 404) and for retries. | Step 4, error probe. Team reads the same in code, but was not probed. | Read the status from `err.__cause__.response.status_code`. |
| Warning | No timeout on any request. A hung connection blocks the backfill forever. | Step 4, `timeout passed by library: False` | Pass `timeout=` on each call. Kwargs reach `session.get`. |
| Warning | Depends on Understat's undocumented AJAX routes, with one active maintainer. A site change broke all endpoints in Dec 2025. The dependency-update PR #14 has been open 11 months. | Step 5 | Keep the Q25 failure checks. Expect breakage. |
| Warning | PyPI ships only an sdist, so installing runs a build with unpinned `setuptools>=61.0.0` and `setuptools_scm`. There is no `setup.py`, so no custom install code runs. | Step 1, Step 3 | Pin by hash. Consider building one wheel and storing it. |
| Info | Each getter refetches the whole payload. `get_shot_data` plus `get_season_data` for one player costs 2 identical requests, which doubles time at a 2 s delay. | Step 4, requests list | Consider this in Q14 and the rate test in #3. |
| Info | An `AttributeError` inside `with UnderstatClient()` that has no "Endpoint" in its text comes out as `IndexError`, and the session is not closed. | Step 4, error probe | Do not rely on the context manager's error handling. |
| Info | PyPI licence metadata is blank because `setup.cfg` names `LICENSE.txt` while the file is `LICENSE`. The file itself is MIT. The README's Travis badge is stale; real CI is CircleCI. | Step 1, Step 5 | None. |
| Info | The library's own test fixtures contain real Understat data of unknown date. | `test/resources/` | Do not reuse. Project fixtures must be recorded in STEP 0. |

## Issue #2 done criteria

Quoted word for word from issue #2.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | "Every file that runs has been read, and the report states what it changes on the machine and every network call" | **Met**, for understatapi's own files. Source of its 5 runtime dependencies and of the build backends was not read; the dependencies were covered by osv-scanner only. | Step 6a |
| 2 | "Engagement-farming check is reported: stars vs commits, last commit, issues answered, tests, licence, and whether the code does what the README claims" | **Met**. The README claim is confirmed offline only. | Step 5, Step 4 |
| 3 | "Cloned only into `~/sandbox/`, pinned to a commit hash, installed with `pip install --no-deps` into a venv" | **Met** | Step 6b |
| 4 | "osv-scanner, semgrep --config auto and gitleaks have run, with every finding reported" | **Met** | Step 6d |
| 5 | "A minimal example matching our use case runs in the sandbox, or the blocker is reported" | **Met by reporting the blocker**: the approved live call could not reach Understat from this network. An offline example did run. | Step 4 |
| 6 | "Work stops and Ahmed is asked before anything is wired into the project" | **Met**. Nothing is wired in. Decision for Ahmed is at the end of this report. | Decision for Ahmed |

## Step 0: read first

```
$ pwd
/Users/ahmed.farah/Projects/football-twin
$ git status
* main...origin/main
?? config/
$ git rev-parse --short origin/main; git rev-parse --short HEAD
1fd702c
1fd702c
```

`config/` holds an empty `face_validity_pairs.yaml`. It was untracked before this run and was not touched. The hard rule therefore still applies: no distance code ran, and this report holds no per-player metric values. The sweep prints at most about 40 characters around a hit, and the probes print field names only.

### Vetting steps

Q13 in `docs/phase-1-plan.md` reads: "`understatapi` goes through vetting steps 1–5 in `~/sandbox`. No other library is considered unless it fails. It sits behind one adapter that adds the 2-second delay and retries."

Q13 names the steps but does not list them. They are in `~/.claude/CLAUDE.md`, section "Before anything is installed":

1. "Vet the repo. Read every file that runs: install scripts, hooks, postinstall, plugins, MCP servers, CI. Report what it changes on my machine and any network calls."
2. "Reject engagement farming. Check: stars vs real commit history, last commit date, open issues answered, tests present, licence, and whether the code actually does what the README claims. If it is thin, abandoned or a wrapper around a paid service, say so and stop."
3. "Sandbox it. Clone into ~/sandbox/<repo-name> only. Pin to a commit hash. Install with scripts disabled (npm install --ignore-scripts, pip install --no-deps into a venv)."
4. "Security sweep in the sandbox, with free tools: osv-scanner (dependency CVEs), semgrep --config auto (code), gitleaks (secrets). Install them with brew if missing. Report every finding."
5. "Prove it works in the sandbox: run its own tests or a minimal example that matches my use case."

### Blocking links

Command: `gh api repos/afarah101/football-twin/issues/<n>/dependencies/blocked_by`. Issue bodies contain no "Blocked by" lines, so these native links are the only record.

| Issue | Title | Blocked by |
|---|---|---|
| #2 | Vet understatapi in the sandbox | none |
| #3 | STEP 0 data facts and recorded fixtures | #2 |
| #4 | [Ahmed] Decide on ML/MR wide midfielders | #3 |
| #5 | [Ahmed] Commit the face validity pairs | none |
| #6 | Understat adapter | #3 |
| #7 | Full backfill | #6 |
| #8 | Public MetricProfiles for one league-season | #3, #4, #5 |
| #9 | Twin lists | #5, #8 |
| #10 | Validation report and outside review | #7, #9 |
| #11 | Site: search, twins, Fingerprint | #9 |
| #12 | Site: map and same-league filter | #11 |
| #13 | Monday job and launch | #7, #10, #12 |

**Mismatch against the spec comment: could not be fully checked.** The task refers to a table in the spec comment, but issue #1's only comment has no table. It is one sentence saying #8 is also blocked by #5, and the native links agree. Nothing was changed.

## Step 1: download

```
$ curl -sS https://pypi.org/pypi/understatapi/json
name = understatapi
version = 0.7.1
license = None
author = collinb9 <brendan.m.collins@outlook.com>
maintainer = None
home_page = https://github.com/collinb9/understatAPI
requires_python = >=3.10
requires_dist = ['certifi==2025.11.12', 'charset-normalizer==3.4.4', 'idna==2.10', 'requests==2.32.5', 'urllib3==1.26.5']
understatapi-0.7.1.tar.gz uploaded 2026-02-21 sha256 7e50751ad1189e82acc6afea596733d00d7a0d74cbd492238b092d137c1ed334 size 537687

$ git clone https://github.com/collinb9/understatAPI.git ~/sandbox/understatapi/repo
$ git -C repo checkout d1252d9734e94ba98c681d2e41d467f1edb7aaf5
d1252d9734e94ba98c681d2e41d467f1edb7aaf5 2026-02-21 Brendan Collins Bump version to 0.7.1 (#20)
tag v0.7.1 -> d1252d9734e94ba98c681d2e41d467f1edb7aaf5 (also master HEAD)

$ gh api repos/collinb9/understatAPI --jq ...license.spdx_id
MIT

$ gh api repos/collinb9/understatAPI/commits/d1252d9... --jq .commit.verification
{"reason":"valid","verified":true}

$ diff -rq repo sdist/understatapi-0.7.1 -x .git
Only in SDIST: PKG-INFO
Files repo/setup.cfg and SDIST/setup.cfg differ
Only in SDIST: understatapi.egg-info
```

| Item | Value |
|---|---|
| Version | 0.7.1 |
| Licence | MIT (`LICENSE`, copyright 2021 Brendan Collins). PyPI field is blank. |
| Last release | 2026-02-21 |
| Maintainer | collinb9 (Brendan Collins) |
| Sdist vs tag | Same files apart from packaging metadata. The `setup.cfg` difference is whitespace and an added `[egg_info]` block. |
| Wheel on PyPI | None for 0.7.1, sdist only |

## Step 2: security sweep

Scope: all 75 tracked files at the pinned commit, plus all 81 files in the PyPI sdist. `.git` was excluded here because gitleaks scans history. The only files skipped as binary are the empty `.gitkeep` files, two in each tree. Script: `~/sandbox/understatapi/probes/sweep.sh`. Search is case-insensitive substring, so words like "evaluation" count as hits.

| Pattern | Hits | Result |
|---|---|---|
| `exec` | 4 | Harmless. A `.pylintrc` comment and "executable" in `docs/make.bat`. The `init-hook` line in `.pylintrc` is commented out. |
| `eval` | 14 | No `eval()` call. "evaluation" text in `.pylintrc` and fixture HTML. `.pylintrc:83` is a score formula used only if someone runs pylint in the repo. |
| `subprocess` | 0 | **0 hits** |
| `os.system` | 0 | **0 hits** |
| `pickle` | 4 | Harmless. A `.pylintrc` comment and a `.gitignore` entry. |
| `base64` | 0 | **0 hits** |
| `socket` | 4 | Harmless. The word "websockets" in a CSS class list in saved Understat HTML. |

Every hit, as `file:line:context`:

```
[exec] 4 hits
repo/.pylintrc:19:# Python code to execute, usually for sys.path manipulation s
repo/docs/make.bat:20:.to the full path of the 'sphinx-build' executable. Alternatively you
sdist/understatapi-0.7.1/.pylintrc:19:# Python code to execute, usually for sys.path manipulation s
sdist/understatapi-0.7.1/docs/make.bat:20:.to the full path of the 'sphinx-build' executable. Alternatively you
[eval] 14 hits
repo/.pylintrc:82:# global evaluation report (RP0004).
repo/.pylintrc:83:evaluation=10.0 - ((float(5 * error + warnin
repo/.pylintrc:97:# Activate the evaluation score.
repo/.pylintrc:356:return multiple potential results while evaluating a Python object, but
repo/.pylintrc:357:# some branches might not be evaluated, which results in partial inferenc
repo/test/resources/home.html:190:ry football metric, which allows you to evaluate team
repo/test/resources/home.html:202:he most precise method for shot quality evaluation.
sdist/understatapi-0.7.1/.pylintrc:82:# global evaluation report (RP0004).
sdist/understatapi-0.7.1/.pylintrc:83:evaluation=10.0 - ((float(5 * error + warnin
sdist/understatapi-0.7.1/.pylintrc:97:# Activate the evaluation score.
sdist/understatapi-0.7.1/.pylintrc:356:return multiple potential results while evaluating a Python object, but
sdist/understatapi-0.7.1/.pylintrc:357:# some branches might not be evaluated, which results in partial inferenc
sdist/understatapi-0.7.1/test/resources/home.html:190:ry football metric, which allows you to evaluate team
sdist/understatapi-0.7.1/test/resources/home.html:202:he most precise method for shot quality evaluation.
[subprocess] 0 hits
[ossystem] 0 hits
[pickle] 4 hits
repo/.pylintrc:36:# Pickle collected data for later comparisons.
repo/.gitignore:39:*.pickle
sdist/understatapi-0.7.1/.pylintrc:36:# Pickle collected data for later comparisons.
sdist/understatapi-0.7.1/.gitignore:39:*.pickle
[base64] 0 hits
[socket] 4 hits
repo/test/resources/home.html:2:xeddb hashchange history draganddrop websockets rgba hsla multiplebgs backgroundsize b
repo/test/resources/minimal.html:2:xeddb hashchange history draganddrop websockets rgba hsla multiplebgs backgroundsize b
sdist/understatapi-0.7.1/test/resources/home.html:2:xeddb hashchange history draganddrop websockets rgba hsla multiplebgs backgroundsize b
sdist/understatapi-0.7.1/test/resources/minimal.html:2:xeddb hashchange history draganddrop websockets rgba hsla multiplebgs backgroundsize b
```

IPv4-shaped matches: 6, all version numbers, none real IPs. IPv6-shaped matches: 0.

```
repo/test_requirements.txt:64:2.31.0.6
repo/test_requirements.txt:66:1.26.25.14
repo/test_requirements.in:7:2.31.0.6
sdist/understatapi-0.7.1/test_requirements.txt:64:2.31.0.6
sdist/understatapi-0.7.1/test_requirements.txt:66:1.26.25.14
sdist/understatapi-0.7.1/test_requirements.in:7:2.31.0.6
```

Domains. Only `understat.com` appears in package code; every other host is in docs, README, CI, packaging metadata or saved Understat HTML that no code executes. `sdist` files match the repo, so its hits repeat at the same lines; only sdist-only files are listed separately. A separate search for any `scheme://host` URL, regardless of TLD, found no host outside this list.

```
understat.com (93)
  repo/README.md: 7,7,13,34,38,39,40,41
  repo/docs/source/README.md: 7,7,13,34,38,39,40,41
  repo/docs/source/glossary.rst: 3
  repo/setup.cfg: 4
  repo/test/resources/home.html: 5,288,288,304
  repo/test/resources/league_epl.html: 5,6,113,271,271,287
  repo/test/resources/match.html: 5,6,34,35,101,242,399,568,571,594,597,613,616,625,628,644,702,702,718
  repo/test/resources/minimal.html: 5
  repo/test/resources/player.html: 5,6,98,300,300,316
  repo/test/resources/team.html: 5,6,151,266,266,282
  repo/understatapi/__init__.py: 1
  repo/understatapi/api.py: 80,107,133,159
  repo/understatapi/endpoints/base.py: 24,29
  repo/understatapi/endpoints/league.py: 13
  repo/understatapi/endpoints/match.py: 14
  repo/understatapi/endpoints/player.py: 14
  repo/understatapi/endpoints/team.py: 14
  repo/understatapi/parsers/league.py: 10
  repo/understatapi/parsers/match.py: 10
  repo/understatapi/parsers/player.py: 10
  repo/understatapi/parsers/team.py: 10
  sdist/understatapi-0.7.1/PKG-INFO: 4,26,26,32,53,57,58,59,60
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 4,26,26,32,53,57,58,59,60
github.com (26)
  repo/README.md: 28,85,93,94,95
  repo/docs/source/README.md: 28,85,93,94,95
  repo/setup.cfg: 9,12
  sdist/understatapi-0.7.1/PKG-INFO: 5,9,47,104,112,113,114
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 5,9,47,104,112,113,114
ajax.googleapis.com (10)
  repo/test/resources/home.html: 293,294
  repo/test/resources/league_epl.html: 276,277
  repo/test/resources/match.html: 707,708
  repo/test/resources/player.html: 305,306
  repo/test/resources/team.html: 271,272
code.jquery.com (10)
  repo/test/resources/home.html: 308,309
  repo/test/resources/league_epl.html: 291,292
  repo/test/resources/match.html: 722,723
  repo/test/resources/player.html: 320,321
  repo/test/resources/team.html: 286,287
img.shields.io (8)
  repo/README.md: 2,3
  repo/docs/source/README.md: 2,3
  sdist/understatapi-0.7.1/PKG-INFO: 21,22
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 21,22
travis-ci.com (8)
  repo/README.md: 1,1
  repo/docs/source/README.md: 1,1
  sdist/understatapi-0.7.1/PKG-INFO: 20,20
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 20,20
collinb9.github.io (7)
  repo/README.md: 79
  repo/docs/source/README.md: 79
  repo/setup.cfg: 11
  sdist/understatapi-0.7.1/PKG-INFO: 8,98
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 8,98
www.google-analytics.com (7)
  repo/test/resources/home.html: 54,328
  repo/test/resources/league_epl.html: 311
  repo/test/resources/match.html: 742
  repo/test/resources/minimal.html: 10
  repo/test/resources/player.html: 340
  repo/test/resources/team.html: 306
cdnjs.cloudflare.com (5)
  repo/test/resources/home.html: 311
  repo/test/resources/league_epl.html: 294
  repo/test/resources/match.html: 725
  repo/test/resources/player.html: 323
  repo/test/resources/team.html: 289
pagead2.googlesyndication.com (5)
  repo/test/resources/home.html: 307
  repo/test/resources/league_epl.html: 290
  repo/test/resources/match.html: 721
  repo/test/resources/player.html: 319
  repo/test/resources/team.html: 285
semver.org (4)
  repo/README.md: 112
  repo/docs/source/README.md: 112
  sdist/understatapi-0.7.1/PKG-INFO: 131
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 131
outlook.com (3)
  repo/setup.cfg: 8
  sdist/understatapi-0.7.1/PKG-INFO: 7
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 7
pypi.org (3)
  repo/setup.cfg: 13
  sdist/understatapi-0.7.1/PKG-INFO: 10
  sdist/understatapi-0.7.1/understatapi.egg-info/PKG-INFO: 10
api.github.com (1)
  repo/cd/make_release.sh: 32
fonts.googleapis.com (1)
  repo/test/resources/home.html: 23
sphinx-doc.org (1)
  repo/docs/make.bat: 24
```

Other checks over `repo/understatapi`, for `environ|getenv|open(|verify|Path(|.write|shutil|tempfile|ctypes|importlib|__import__|compile(|marshal|http://`: **0 hits**. Package imports are only `requests`, `json`, `sys`, `inspect`, `re`, `typing` and `types`.

## Step 3: dependencies

Source: `requirements.in`, `requirements.txt`, `test_requirements.in`, `pyproject.toml`. `setup.cfg` sets `install_requires = file: requirements.txt`, so these exact pins are forced on every user. None have hashes.

| Dependency | Version | Used at | Flag |
|---|---|---|---|
| requests | ==2.32.5 (source: `>=2.31.0`) | runtime | 1 advisory |
| urllib3 | ==1.26.5 | runtime | **Old major line, 10 advisories** |
| idna | ==2.10 | runtime | **Old, 2 advisories** |
| certifi | ==2025.11.12 | runtime | **1 advisory, CVSS 9.1** |
| charset-normalizer | ==3.4.4 | runtime | none |
| setuptools | >=61.0.0 | build | **Unpinned** |
| setuptools_scm | no version | build | **Unpinned** |

Dev only, not installed by users, and not installed here:

```
test: astroid==4.0.2 black==25.12.0 click==8.3.1 coverage==7.13.0 dill==0.4.0 exceptiongroup==1.3.1 iniconfig==2.3.0 isort==5.7.0 librt==0.7.3 mccabe==0.6.1 mypy==1.19.0 mypy-extensions==1.1.0 packaging==25.0 pathspec==0.9.0 platformdirs==2.4.0 pluggy==1.6.0 pygments==2.19.2 pylint==4.0.4 pytest==9.0.2 pytokens==0.3.0 tomli==2.3.0 tomlkit==0.13.3 types-requests==2.31.0.6 types-urllib3==1.26.25.14 typing-extensions==4.15.0
docs: alabaster==0.7.12 babel==2.10.3 certifi==2023.7.22 chardet==4.0.0 commonmark==0.9.1 docutils==0.17 idna==2.10 imagesize==1.2.0 jinja2==2.11.3 m2r2==0.2.7 markupsafe==1.1.1 minimock==1.2.8 mistune==0.8.4 packaging==20.9 pygments==2.8.1 pyparsing==2.4.7 pytz==2021.1 recommonmark==0.7.1 requests==2.25.1 snowballstemmer==2.1.0 sphinx==5.0.2 sphinx-autodoc-typehints==1.11.1 sphinx-rtd-theme==0.5.1 sphinxcontrib-applehelp==1.0.2 sphinxcontrib-devhelp==1.0.2 sphinxcontrib-htmlhelp==2.1.0 sphinxcontrib-jsmath==1.0.1 sphinxcontrib-qthelp==1.0.3 sphinxcontrib-serializinghtml==2.0.0 urllib3==1.26.11
```

Unusual packages: none spotted, judged by name only. `numpy`, `pandas` and the like are not pulled in.

## Step 4: value check

**Live call to understat.com: RUN once, approved by Ahmed. FAILED at the network. No HTTP response.**

This is real output, using `venv2` (patched dependencies) and the library's public `get_shot_data`, with one request, no redirects and a 30 s timeout. Player id 2371 comes from the library's docstring. Script: `~/sandbox/understatapi/probes/live_probe.py`. Nothing was saved.

```
$ venv2/bin/python -I probes/live_probe.py
understatapi 0.7.1 requests 2.34.2 urllib3 2.8.0
outcome: ConnectionError (status via chain: None)
http requests sent: 0
hosts resolved: ['understat.com']
get_shot_data returned rows: False
```

`http requests sent: 0` counts responses received, through a response hook. The failure came at connect, before any HTTP was sent.

Diagnosis used DNS, traceroute and bare TCP connects only, with no further HTTP request. No connection to Understat succeeded.

```
$ socket connect, understat.com:443
dns 45.90.32.72
FAILED OSError [Errno 51] Network is unreachable

$ socket connect + TLS, pypi.org:443 (control)
dns 151.101.64.223
tcp ok ('151.101.192.223', 443)
tls ok TLSv1.3 GlobalSign nv-sa

$ dig +short understat.com / dig +short understat.com @1.1.1.1
45.90.32.72
45.90.32.72

$ route -n get 45.90.32.72
   route to: 45.90.32.72
    gateway: 192.168.0.1
  interface: en0

$ TCP connects to other hosts
example.com 443 tcp ok 172.66.147.243
wikipedia.org 443 tcp ok 185.15.59.224
45.90.32.72 443 FAILED OSError [Errno 51] Network is unreachable
45.90.32.72 80 FAILED OSError [Errno 51] Network is unreachable
understat.com 80 FAILED OSError [Errno 51] Network is unreachable
45.90.32.1 FAILED OSError [Errno 51] Network is unreachable
beget.com 178.248.236.146 tcp ok

$ traceroute -n -m 14 -q 1 -w 2 45.90.32.72
traceroute to 45.90.32.72 (45.90.32.72), 14 hops max, 40 byte packets
 1  192.168.0.1  6.298 ms
 2  10.53.32.89  12.260 ms
 3  80.255.193.64  13.905 ms !N

$ whois 80.255.193.64
inetnum:        80.255.192.0 - 80.255.223.255
netname:        UK-NTLI-20011228
country:        GB
descr:          Virgin Media

$ whois -h whois.ripe.net 45.90.32.72
inetnum:        45.90.32.0 - 45.90.32.255
netname:        BEGET-NET-84
country:        RU
origin:         AS198610
descr:          BEGET.RU

$ tailscale status
backend NeedsLogin, exit node in use: False
```

What this shows:

- Hop 3, a Virgin Media router, answers `!N` (network unreachable) for Understat's IP. A second address in the same /24 fails the same way. So the refusal covers at least part of that hosting range and is not specific to Understat.
- This machine's routing, DNS and internet access are fine. Beget's own website, on a different range, connects.
- It fits the spec's note that "Understat could not be reached from the planning session".

What this does not show:

- Why Virgin Media refuses the route. It could be deliberate or a routing fault.
- Whether Understat is up or reachable from other networks.
- Web searches found no report of this block. The only related lead is that [soccerdata's Understat docs](https://soccerdata.readthedocs.io/en/stable/datasources/Understat.html) mention a proxy option.

No VPN, proxy or other route was tried. Whether to route around a possibly deliberate ISP block is Ahmed's decision.

The one live fact gained: a connection failure comes through as a plain `requests` `ConnectionError`, not as `InvalidPlayer`.

Everything below is offline evidence and does not prove the library works against the site today.

Offline example matching our use case, with `requests.Session.get` stubbed to return the library's own recorded fixtures. Field names only. Script: `~/sandbox/understatapi/probes/offline_probe.py`.

```
$ venv/bin/python -I probes/offline_probe.py repo/test/resources/data
understatapi 0.7.1 from /Users/ahmed.farah/sandbox/understatapi/venv/lib/python3.12/site-packages/understatapi
after import: {'socket': 2, 'subprocess': 0, 'write': 0, 'exec_outside_stdlib': 0}

requests the library would send (Session.get stubbed):
  https://understat.com/getLeagueData/EPL/2019 {'headers': {'X-Requested-With': 'XMLHttpRequest'}}
  https://understat.com/getPlayerData/0000 {'headers': {'X-Requested-With': 'XMLHttpRequest'}}
  https://understat.com/getPlayerData/0000 {'headers': {'X-Requested-With': 'XMLHttpRequest'}}
  https://understat.com/getMatchData/0000 {'headers': {'X-Requested-With': 'XMLHttpRequest'}}
  https://understat.com/getMatchData/0000 {'headers': {'X-Requested-With': 'XMLHttpRequest'}}
session default headers: {'User-Agent': 'python-requests/2.32.5', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'}
adapter retries default: 0
timeout passed by library: False

league.get_player_data fields: ['assists', 'games', 'goals', 'id', 'key_passes', 'npg', 'npxG', 'player_name', 'position', 'red_cards', 'shots', 'team_title', 'time', 'xA', 'xG', 'xGBuildup', 'xGChain', 'yellow_cards']
  plan's PlayerSeason fields missing: []
player.get_shot_data fields: ['X', 'Y', 'a_goals', 'a_team', 'date', 'h_a', 'h_goals', 'h_team', 'id', 'lastAction', 'match_id', 'minute', 'player', 'player_assisted', 'player_id', 'result', 'season', 'shotType', 'situation', 'xG']
  plan's shot fields missing: []
match.get_shot_data fields: ['X', 'Y', 'a_goals', 'a_team', 'date', 'h_a', 'h_goals', 'h_team', 'id', 'lastAction', 'match_id', 'minute', 'player', 'player_assisted', 'player_id', 'result', 'season', 'shotType', 'situation', 'xG']
  plan's shot fields missing: []
match.get_roster_data fields: ['assists', 'goals', 'h_a', 'id', 'key_passes', 'own_goals', 'player', 'player_id', 'position', 'positionOrder', 'red_card', 'roster_in', 'roster_out', 'shots', 'team_id', 'time', 'xA', 'xG', 'xGBuildup', 'xGChain', 'yellow_card']
  position present: True
player.get_season_data top keys: ['position', 'season', 'shotTypes', 'shotZones', 'situation']

audit events:
  socket: 2 [('socket.__new__', '(<socket.socket fd=-1, family=0, type=0, proto=0>, 30, 1, 0)'), ('socket.bind', "(<socket.socket fd=3, family=30, type=1, proto=0, laddr=('::', 0, 0, 0)>, ('::1', 0))")]
  subprocess: 0 []
  write: 0 []
  exec_outside_stdlib: 0 []
```

The 2 socket events are urllib3's local IPv6 check at import (`urllib3/util/connection.py:140,150`). It binds `::1` and makes no connection. The spec's required `X-Requested-With` header is sent. All planned fields exist in these fixtures; #3 must confirm them on live data.

Error handling, with in-memory responses. Script: `~/sandbox/understatapi/probes/error_probe.py`.

```
404 player: InvalidPlayer (status via exception chain: 404)
404 match : InvalidMatch (status via exception chain: 404)
404 league: HTTPError (status via exception chain: 404)
429 player: InvalidPlayer (status via exception chain: 429)
429 match : InvalidMatch (status via exception chain: 429)
429 league: HTTPError (status via exception chain: 429)
500 player: InvalidPlayer (status via exception chain: 500)
500 match : InvalidMatch (status via exception chain: 500)
500 league: HTTPError (status via exception chain: 500)
503 player: InvalidPlayer (status via exception chain: 503)
503 match : InvalidMatch (status via exception chain: 503)
503 league: HTTPError (status via exception chain: 503)
200 with HTML body, player: JSONDecodeError (status via exception chain: None)
AttributeError inside `with`: IndexError (status via exception chain: None)
```

## Step 5: engagement-farming check

Result: **not engagement farming, not a paid wrapper.** It is small, real and thinly maintained.

```
$ gh api repos/collinb9/understatAPI
{"archived":false,"created":"2021-02-20T11:06:14Z","default_branch":"master","disabled":false,"fork":false,"forks":9,"license":"MIT","open_issues":1,"owner":"collinb9","owner_type":"User","pushed":"2026-02-21T16:50:42Z","stars":48,"updated":"2026-09-26T11:20:15Z","watchers":3}

$ git rev-list --count HEAD
158

$ git log --format=%ad --date=format:%Y | sort | uniq -c
 119 2021
  32 2022
   2 2023
   1 2024
   2 2025
   2 2026

$ gh api repos/collinb9/understatAPI/stargazers
{"message":"Not Found","documentation_url":"https://docs.github.com/rest/activity/starring#list-stargazers","status":"404"}

$ curl https://pypistats.org/api/packages/understatapi/recent
{"data":{"last_day":500,"last_month":16595,"last_week":4167},"package":"understatapi","type":"recent_downloads"}

$ gh api search/code: "understatapi filename:requirements.txt" / "\"from understatapi\" language:python"
62 / 160
```

| Check | Result |
|---|---|
| Stars vs real use | 48 stars, 9 forks, 16,595 downloads last month (may include bots and CI), 62 requirements files and 160 Python files found by code search. Use outweighs stars. |
| Commit history | 158 commits, 155 by the owner per the contributors API. 151 of them date from 2021 to 2022, then 7 since. |
| Last commit | 2026-02-21, about 8 months before this run |
| Open issues | 0 issues, 1 PR (#14, dependency upgrade, open since 2025-12-06; the owner commented on 2025-12-17 and it remains unmerged) |
| Issues answered | All 5 issues are closed, each with comments |
| Broken-master reports | #15, Dec 2025: all endpoints broke with `JSONDecodeError` after Understat moved to AJAX. Fixed in 0.7.0 in 6 days using a contributor's PR. #18, Jan 2026: `get_match_info` broke. Fixed in 0.7.1 in 29 days. No break report is open now. |
| Abandonment | A contributor called it "dead" on 2025-12-14. The owner replied 3 days later that it is not dead but is checked rarely. |
| Tests | 31, all mocked, none touch the live site. |
| CI | `ci/circleci: test` and `ci/circleci: deploy` both success at the pinned commit |
| Does what README says | Offline: the endpoints, URLs and returned JSON shapes match. Live: unverified, the call could not reach the site. |

A maintained fork, `jeke-understat-scrapper`, exists. It was not vetted because Q13 rules out other libraries unless this one fails.

## Step 6: remaining vetting steps

### 6a. Step 1 of Q13: every file that runs

| Group | Files read in full | When it runs |
|---|---|---|
| Package | `understatapi/` all 16 `.py` files | Import and calls |
| Build | `pyproject.toml`, `setup.cfg`. No `setup.py`, `MANIFEST`, `.pth` or `conftest.py`. | Install |
| CI and release | `.circleci/config.yml`, `ci/*.sh`, `cd/*.sh` | Upstream's CI only, not on install |
| Docs | `docs/source/conf.py`, `docs/Makefile`, `docs/make.bat` | Docs build only |
| Tests | `test/__init__.py`, `test/mock_requests.py`, `test/test_api.py` | Test runs only |
| Tool config | `.pylintrc` (hooks and plugins lines only), `.coveragerc`, `.mypy.ini`, `.gitattributes` | Dev tools only |

Git hooks: none active in the clone. `cd/*.sh` and CI write `~/.pypirc`, publish to PyPI and push to gh-pages, but only in upstream's own CI when a tag is pushed. Nothing here ran them.

**What it changes on the machine**

- Install: pure Python files in the venv's `site-packages`. No console scripts, entry points or `.pth` files. `pip show -f` lists only `understatapi/` and its `dist-info`.
- Install, build step: pip fetches `setuptools` and `setuptools_scm` into a temporary build environment. The build succeeded with `requests` absent from that environment, which implies the `attr:` version lookup did not import package code. That is an inference, not a direct observation.
- Runtime: audit hook shows 0 file writes and 0 subprocesses. The library reads no environment variables itself.

**Every network call**

All are `GET` through a `requests.Session` to `https://understat.com/`. There is no telemetry and no other host.

| URL | Called by | Seen in |
|---|---|---|
| `getLeagueData/{league}/{season}` | `league.*` | Probe and code |
| `getPlayerData/{player}` | `player.*` | Probe and code |
| `getMatchData/{match}` | `match.get_shot_data`, `get_roster_data` | Probe and code |
| `getTeamData/{team}/{season}` | `team.*` | Code, `endpoints/team.py:65` |
| `match/{match}` (HTML) | `match.get_match_info` | Code, `endpoints/match.py:82` |

`requests` defaults still apply: TLS verification on, redirects followed, and proxy and `.netrc` settings honoured.

### 6b. Step 3 of Q13: sandbox

```
$ python3.12 -m venv venv
$ venv/bin/pip install --no-deps --no-cache-dir ./repo
Successfully installed understatapi-0.7.1

# The package cannot import without requests, so its pinned runtime set went in separately, wheels only, no scripts:
$ venv/bin/pip install --no-deps --no-cache-dir --only-binary :all: -r repo/requirements.txt
Successfully installed certifi-2025.11.12 charset-normalizer-3.4.4 idna-2.10 requests-2.32.5 urllib3-1.26.5
```

Python 3.12 was used, matching the version named in `requirements.txt`. The machine default is 3.15, which was not tested.

### 6c. Step 5 of Q13: prove it works

Own test suite, with `socket.connect` blocked by an audit hook. Script: `~/sandbox/understatapi/probes/nonet_conftest.py`.

```
# venv: library's pins
Ran 31 tests in 0.043s
OK
tests run: 31 failures: 0 errors: 0 skipped: 0
socket.connect attempts: []

# venv2: current dependencies
certifi==2026.10.23 charset-normalizer==3.5.2 idna==3.20 requests==2.34.2 urllib3==2.8.0
OK
tests run: 31 failures: 0 errors: 0 skipped: 0
socket.connect attempts: []
```

Live proof is still missing (Step 4). The `venv2` result covers the mocked suite only, so urllib3 2.x has not been tested against the real site.

### 6d. Step 4 of Q13: scanners

**osv-scanner 2.7.0.** `osv-scanner scan source -r repo` (exit 1 means vulnerabilities found). Totals by manifest, counting distinct advisories:

| Manifest | Advisories | Installed for users? |
|---|---|---|
| `requirements.txt` | 14 | **Yes** |
| `test_requirements.txt` | 6 | No |
| `docs_requirements.txt` | 40 | No |

Runtime set only, as installed in each venv. `osv-scanner scan source --lockfile requirements.txt:<freeze file>`:

```
# venv: library's pins
certifi==2025.11.12 charset-normalizer==3.4.4 idna==2.10 requests==2.32.5 urllib3==1.26.5
certifi 2025.11.12  PYSEC-2026-4320,GHSA-6q48-6c7w-9gw2  CVSS 9.1
idna 2.10.0  PYSEC-2024-60,GHSA-jjg7-2v4v-x38h  CVSS 7.5
idna 2.10.0  PYSEC-2026-215,GHSA-65pc-fj4g-8rjx  CVSS 6.9
requests 2.32.5  PYSEC-2026-2275,GHSA-gc5v-m9x4-r6x2  CVSS 5.5
urllib3 1.26.5  PYSEC-2023-192,GHSA-v845-jxx5-vc9f  CVSS 8.1
urllib3 1.26.5  PYSEC-2023-212,GHSA-g4mx-q9vg-27p4  CVSS 5.7
urllib3 1.26.5  PYSEC-2026-141,GHSA-qccp-gfcp-xxvc  CVSS 8.2
urllib3 1.26.5  PYSEC-2026-1994,GHSA-2xpw-w6gg-jr37  CVSS 8.9
urllib3 1.26.5  PYSEC-2026-1995,GHSA-34jh-p97f-mpxf  CVSS 4.4
urllib3 1.26.5  PYSEC-2026-1996,GHSA-38jv-5279-wg99  CVSS 8.9
urllib3 1.26.5  PYSEC-2026-1998,GHSA-gm62-xv2j-4w53  CVSS 8.9
urllib3 1.26.5  PYSEC-2026-1999,GHSA-pq67-6m6q-mj2v  CVSS 5.3
urllib3 1.26.5  PYSEC-2026-4175,GHSA-8988-9cw3-xx77  CVSS 7.6
urllib3 1.26.5  PYSEC-2026-4177,GHSA-vxq7-64xx-v4gw  CVSS 8.9
distinct advisories: 14
```

```
# venv2: current dependencies
certifi==2026.10.23 charset-normalizer==3.5.2 idna==3.20 requests==2.34.2 urllib3==2.8.0
distinct advisories: 0
```

Every finding, raw scanner output:

```
Scanning dir repo
Starting filesystem walk for root: /
Scanned /Users/ahmed.farah/sandbox/understatapi/repo/test_requirements.txt file and found 25 packages
Scanned /Users/ahmed.farah/sandbox/understatapi/repo/requirements.txt file and found 5 packages
Scanned /Users/ahmed.farah/sandbox/understatapi/repo/docs_requirements.txt file and found 30 packages
End status: 32 dirs visited, 135 inodes visited, 3 Extract calls, 2.739209ms elapsed, 2.739ms wall time

Total 15 packages affected by 60 known vulnerabilities (3 Critical, 24 High, 30 Medium, 2 Low, 1 Unknown) from 1 ecosystem.
60 vulnerabilities can be fixed.

+-------------------------------------+------+-----------+----------+------------+---------------+----------------------------+
| OSV URL                             | CVSS | ECOSYSTEM | PACKAGE  | VERSION    | FIXED VERSION | SOURCE                     |
+-------------------------------------+------+-----------+----------+------------+---------------+----------------------------+
| https://osv.dev/PYSEC-2024-230      | 7.5  | PyPI      | certifi  | 2023.7.22  | 2024.7.4      | repo/docs_requirements.txt |
| https://osv.dev/GHSA-248v-346w-9cwc |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-4320     | 9.1  | PyPI      | certifi  | 2023.7.22  | 2026.10.18    | repo/docs_requirements.txt |
| https://osv.dev/GHSA-6q48-6c7w-9gw2 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2024-60       | 7.5  | PyPI      | idna     | 2.10.0     | 3.7           | repo/docs_requirements.txt |
| https://osv.dev/GHSA-jjg7-2v4v-x38h |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-215      | 6.9  | PyPI      | idna     | 2.10.0     | 3.15          | repo/docs_requirements.txt |
| https://osv.dev/GHSA-65pc-fj4g-8rjx |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1471     | 5.4  | PyPI      | jinja2   | 2.11.3     | 3.1.6         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-cpwx-vrp4-4pq7 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1473     | 5.4  | PyPI      | jinja2   | 2.11.3     | 3.1.3         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-h5c8-rqwp-cp95 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1474     | 5.4  | PyPI      | jinja2   | 2.11.3     | 3.1.4         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-h75v-3vvj-5mfj |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1475     | 7.8  | PyPI      | jinja2   | 2.11.3     | 3.1.5         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-q2x7-8rv6-6q7h |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-168      | 6.1  | PyPI      | mistune  | 0.8.4      | 3.2.1         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-58cw-g322-p94v |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2206     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.2.1         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-8g87-j6q8-g93x |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2207     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.2.1         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-v87v-83h2-53w7 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2208     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.2.1         | repo/docs_requirements.txt |
| https://osv.dev/PYSEC-2026-2209     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.2.1         | repo/docs_requirements.txt |
| https://osv.dev/PYSEC-2026-2210     | 7.5  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-c8j7-8cv4-2xmq |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2211     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-8c25-4j27-2rv3 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2212     | 5.9  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-r4rv-85jg-w4mf |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2213     | 7.5  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-4j32-57v6-6g45 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2214     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-g97x-gvcm-x72h |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2215     | 5.3  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-8mpj-m6qm-5qr8 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2216     | 7.5  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-ffq3-xpv3-j92q |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2217     | 6.1  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-qfrw-5rxm-mhh2 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2218     | 4.3  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-2hm2-hc3v-44h9 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2652     | 8.7  | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-qcq2-496w-v96p |      |           |          |            |               |                            |
| https://osv.dev/GHSA-h7ww-273w-6cm8 |      | PyPI      | mistune  | 0.8.4      | 3.3.0         | repo/docs_requirements.txt |
| https://osv.dev/PYSEC-2023-117      | 6.8  | PyPI      | pygments | 2.8.1      | 2.15.1        | repo/docs_requirements.txt |
| https://osv.dev/GHSA-mrwq-x4v8-fh7p |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2987     | 3.3  | PyPI      | pygments | 2.8.1      | 2.20.0        | repo/docs_requirements.txt |
| https://osv.dev/GHSA-5239-wwwm-4pmq |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2023-74       | 6.1  | PyPI      | requests | 2.25.1     | 2.31.0        | repo/docs_requirements.txt |
| https://osv.dev/GHSA-j8r2-6x86-q33q |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1872     | 5.3  | PyPI      | requests | 2.25.1     | 2.32.4        | repo/docs_requirements.txt |
| https://osv.dev/GHSA-9hjg-9r4m-mvj7 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1873     | 5.6  | PyPI      | requests | 2.25.1     | 2.32.0        | repo/docs_requirements.txt |
| https://osv.dev/GHSA-9wx4-h78v-vm56 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2275     | 5.5  | PyPI      | requests | 2.25.1     | 2.33.0        | repo/docs_requirements.txt |
| https://osv.dev/GHSA-gc5v-m9x4-r6x2 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2023-192      | 8.1  | PyPI      | urllib3  | 1.26.11    | 1.26.17       | repo/docs_requirements.txt |
| https://osv.dev/GHSA-v845-jxx5-vc9f |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2023-212      | 5.7  | PyPI      | urllib3  | 1.26.11    | 1.26.18       | repo/docs_requirements.txt |
| https://osv.dev/GHSA-g4mx-q9vg-27p4 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-141      | 8.2  | PyPI      | urllib3  | 1.26.11    | 2.7.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-qccp-gfcp-xxvc |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1994     | 8.9  | PyPI      | urllib3  | 1.26.11    | 2.6.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-2xpw-w6gg-jr37 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1995     | 4.4  | PyPI      | urllib3  | 1.26.11    | 1.26.19       | repo/docs_requirements.txt |
| https://osv.dev/GHSA-34jh-p97f-mpxf |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1996     | 8.9  | PyPI      | urllib3  | 1.26.11    | 2.6.3         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-38jv-5279-wg99 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1998     | 8.9  | PyPI      | urllib3  | 1.26.11    | 2.6.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-gm62-xv2j-4w53 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1999     | 5.3  | PyPI      | urllib3  | 1.26.11    | 2.5.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-pq67-6m6q-mj2v |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-4175     | 7.6  | PyPI      | urllib3  | 1.26.11    | 2.8.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-8988-9cw3-xx77 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-4177     | 8.9  | PyPI      | urllib3  | 1.26.11    | 2.8.0         | repo/docs_requirements.txt |
| https://osv.dev/GHSA-vxq7-64xx-v4gw |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-4320     | 9.1  | PyPI      | certifi  | 2025.11.12 | 2026.10.18    | repo/requirements.txt      |
| https://osv.dev/GHSA-6q48-6c7w-9gw2 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2024-60       | 7.5  | PyPI      | idna     | 2.10.0     | 3.7           | repo/requirements.txt      |
| https://osv.dev/GHSA-jjg7-2v4v-x38h |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-215      | 6.9  | PyPI      | idna     | 2.10.0     | 3.15          | repo/requirements.txt      |
| https://osv.dev/GHSA-65pc-fj4g-8rjx |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2275     | 5.5  | PyPI      | requests | 2.32.5     | 2.33.0        | repo/requirements.txt      |
| https://osv.dev/GHSA-gc5v-m9x4-r6x2 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2023-192      | 8.1  | PyPI      | urllib3  | 1.26.5     | 1.26.17       | repo/requirements.txt      |
| https://osv.dev/GHSA-v845-jxx5-vc9f |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2023-212      | 5.7  | PyPI      | urllib3  | 1.26.5     | 1.26.18       | repo/requirements.txt      |
| https://osv.dev/GHSA-g4mx-q9vg-27p4 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-141      | 8.2  | PyPI      | urllib3  | 1.26.5     | 2.7.0         | repo/requirements.txt      |
| https://osv.dev/GHSA-qccp-gfcp-xxvc |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1994     | 8.9  | PyPI      | urllib3  | 1.26.5     | 2.6.0         | repo/requirements.txt      |
| https://osv.dev/GHSA-2xpw-w6gg-jr37 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1995     | 4.4  | PyPI      | urllib3  | 1.26.5     | 1.26.19       | repo/requirements.txt      |
| https://osv.dev/GHSA-34jh-p97f-mpxf |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1996     | 8.9  | PyPI      | urllib3  | 1.26.5     | 2.6.3         | repo/requirements.txt      |
| https://osv.dev/GHSA-38jv-5279-wg99 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1998     | 8.9  | PyPI      | urllib3  | 1.26.5     | 2.6.0         | repo/requirements.txt      |
| https://osv.dev/GHSA-gm62-xv2j-4w53 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-1999     | 5.3  | PyPI      | urllib3  | 1.26.5     | 2.5.0         | repo/requirements.txt      |
| https://osv.dev/GHSA-pq67-6m6q-mj2v |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-4175     | 7.6  | PyPI      | urllib3  | 1.26.5     | 2.8.0         | repo/requirements.txt      |
| https://osv.dev/GHSA-8988-9cw3-xx77 |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-4177     | 8.9  | PyPI      | urllib3  | 1.26.5     | 2.8.0         | repo/requirements.txt      |
| https://osv.dev/GHSA-vxq7-64xx-v4gw |      |           |          |            |               |                            |
| https://osv.dev/PYSEC-2026-2120     | 9.8  | PyPI      | black    | 25.12.0    | 26.3.0        | repo/test_requirements.txt |
| https://osv.dev/PYSEC-2026-2121     | 8.7  | PyPI      | black    | 25.12.0    | 26.3.1        | repo/test_requirements.txt |
| https://osv.dev/GHSA-3936-cmfr-pm3m |      |           |          |            |               |                            |
| https://osv.dev/GHSA-cg8m-r9f2-5wm2 | 8.7  | PyPI      | black    | 25.12.0    | 26.10.1       | repo/test_requirements.txt |
| https://osv.dev/PYSEC-2026-2987     | 3.3  | PyPI      | pygments | 2.19.2     | 2.20.0        | repo/test_requirements.txt |
| https://osv.dev/GHSA-5239-wwwm-4pmq |      |           |          |            |               |                            |
| https://osv.dev/GHSA-22qq-2fwx-7p67 | 5.4  | PyPI      | pylint   | 4.0.4      | 4.0.9         | repo/test_requirements.txt |
| https://osv.dev/PYSEC-2026-1845     | 6.8  | PyPI      | pytest   | 9.0.2      | 9.0.3         | repo/test_requirements.txt |
| https://osv.dev/GHSA-6w46-j5rx-g56g |      |           |          |            |               |                            |
+-------------------------------------+------+-----------+----------+------------+---------------+----------------------------+
```

**semgrep 1.157.0.** `semgrep scan --config auto repo`:

```
Findings: 0 (0 blocking)
Rules run: 328
Targets scanned: 50
Files matching .semgrepignore patterns: 25
```

The 25 skipped files are all of `test/`, because semgrep ignores tests by default. A second run on a copy with the ignore list emptied scanned 96 files and returned 24 findings, all one rule, all in saved Understat HTML that no code executes. They describe third-party resources on Understat's own pages loaded without integrity attributes. None affect us, because the library never loads these files outside its tests and does not render HTML.

```
html.security.audit.missing-integrity.missing-integrity test/resources/home.html:293 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/home.html:294 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/home.html:307 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/home.html:308 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/home.html:309 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/home.html:311 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/match.html:707 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/match.html:708 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/match.html:721 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/match.html:722 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/match.html:723 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/match.html:725 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/player.html:305 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/player.html:306 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/player.html:319 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/player.html:320 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/player.html:321 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/player.html:323 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/team.html:271 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/team.html:272 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/team.html:285 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/team.html:286 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/team.html:287 WARNING
html.security.audit.missing-integrity.missing-integrity test/resources/team.html:289 WARNING
```

**gitleaks 8.30.1.** Redacted reports, both exit 0:

```
$ gitleaks git repo
12:01AM INF 202 commits scanned.
12:01AM INF scanned ~14235066 bytes (14.24 MB) in 2.2s
12:01AM INF no leaks found

$ gitleaks dir sdist/understatapi-0.7.1
12:01AM INF scanned ~4782799 bytes (4.78 MB) in 431ms
12:01AM INF no leaks found
```

Scanner network use: `api.osv.dev` received package names and versions, and `semgrep.dev` served rules (`--config auto` also sends semgrep usage metrics). The other hosts contacted during vetting were `pypi.org`, `files.pythonhosted.org`, `github.com`, `api.github.com` and `pypistats.org`, plus the network diagnosis hosts in Step 4. None of this included project data.

## Step 7: verdict reasons

**UNSURE**, because the code evidence is good but two things are still open.

For SAFE:

- Small, readable code: 16 files, 997 lines including docstrings. All read.
- The seven-pattern sweep found only harmless text, semgrep is clean on package code, and gitleaks is clean across the 202 commits it scanned.
- PyPI sdist matches the signed tag. No install-time code of its own. Only contacts Understat.

Against:

- The default install brings 14 advisories. This has a tested offline workaround.
- Vetting step 5 is not complete on live data, because Understat is unreachable from this network. The library has also broken before when Understat changed.

Not UNSAFE: nothing suggests malicious behaviour, and the dependency issue is avoidable.

## Limits of this check

- Source of `requests`, `urllib3`, `idna`, `certifi` and `charset-normalizer` was not read or pattern-swept.
- Patterns were swept on the current tree and sdist, not on git history. gitleaks covered history for secrets only.
- The advisories were listed, not assessed for reachability in our use.
- The audit hook ran with `Session.get` stubbed, so the real HTTP path was covered by reading code only.
- Understat's reachability was tested from this one network only.
- Star patterns were not checked. The stargazers API returned 404, so star dates and accounts are unknown. The stars-vs-use judgement rests on downloads and code search.
- The Understat terms and the rate test are out of scope here and belong to #3.

## Scope

- Changed in the repo: this report only.
- Not touched: `config/`, `CLAUDE.md`, `GLOSSARY.md`, `docs/phase-1-plan.md`, any issue. Nothing pushed. Issue #2 not closed.
- Sandbox kept at `~/sandbox/understatapi` (47M) so the live call can run without repeating setup, and so these results can be reproduced. It also holds `scans/` and `probes/`. Remove with `rm -rf ~/sandbox/understatapi`.

## Decision for Ahmed

Repeat the live call on a phone hotspot? It would complete vetting step 5, print field names only and show no per-player values. It needs no repo changes. It uses a different ISP, so this is Ahmed's choice to make.

Issue #2's own criteria are met either way, but ticket 5 stays NO until a live call passes. The plan's "Full backfill runs once on the laptop" and #3's fixture recording need a working route too.

"Ticket 5" is read here as issue #6, on the basis that "Ticket 1" is issue #2. Tell me if that mapping is wrong.

## GitHub Actions probe

Run URL: https://github.com/afarah101/football-twin/actions/runs/41552470787

Commit `85372ec`, event `workflow_dispatch`, conclusion `failure`, one run, not retried. Files: `.github/workflows/understat-probe.yml` and `scripts/probe_understat.py`.

**Result: the runner could not connect to Understat.** The call timed out after the 20 s connect limit, with no HTTP response.

| Question | Answer |
|---|---|
| Can GitHub Actions reach Understat? | **No, in this one run.** |
| Does the library return real shot rows? | **Not shown.** The request never reached the site, so this says nothing about the library. |
| Did the install work on the runner? | Yes. The hash-pinned `understatapi` and all five patched dependencies installed and imported. |

Two networks have now failed, in different ways:

| Network | Failure | Meaning |
|---|---|---|
| Home (Virgin Media) | `Network is unreachable`, router answers `!N` at hop 3 | A router refuses the route |
| GitHub-hosted runner | `ConnectTimeout` after 20 s | No answer to the connection attempt |

What this does not show: why the runner got no answer. Understat could be down, its host could be dropping cloud addresses, or something on the route could be dropping traffic. One run also cannot rule out a passing fault. A hotspot test helps separate these: if it works, the site is up and the problem is specific to these networks.

If the failure persists, a GitHub-hosted Monday job (#13) cannot fetch data, so that design would need Ahmed's decision. This workflow runs only by hand, so it stays inactive until someone starts it.

Full raw log from `gh run view 41552470787 --log`, with ANSI colour codes removed:

```
probe	Set up job	2026-11-03T00:23:20.1194801Z Current runner version: '2.338.2'
probe	Set up job	2026-11-03T00:23:20.1264915Z ##[group]Runner Image Provisioner
probe	Set up job	2026-11-03T00:23:20.1268205Z Hosted Compute Agent
probe	Set up job	2026-11-03T00:23:20.1269241Z Version: 20261021.618
probe	Set up job	2026-11-03T00:23:20.1270412Z Commit: 21505ad2541d5be6135ed84fc33697146cf75b8e
probe	Set up job	2026-11-03T00:23:20.1271836Z Build Date: 2026-10-21T00:45:21Z
probe	Set up job	2026-11-03T00:23:20.1273049Z Worker ID: {12986e8c-4fa7-4032-b29d-3429ae8aab67}
probe	Set up job	2026-11-03T00:23:20.1274357Z Region: eastus
probe	Set up job	2026-11-03T00:23:20.1275402Z Cloud: Azure
probe	Set up job	2026-11-03T00:23:20.1277298Z ##[endgroup]
probe	Set up job	2026-11-03T00:23:20.1279994Z ##[group]Operating System
probe	Set up job	2026-11-03T00:23:20.1281145Z Ubuntu
probe	Set up job	2026-11-03T00:23:20.1282230Z 26.04.1
probe	Set up job	2026-11-03T00:23:20.1283131Z LTS
probe	Set up job	2026-11-03T00:23:20.1283933Z ##[endgroup]
probe	Set up job	2026-11-03T00:23:20.1285033Z ##[group]Runner Image
probe	Set up job	2026-11-03T00:23:20.1306604Z Image: ubuntu-26.04
probe	Set up job	2026-11-03T00:23:20.1307642Z Version: 20261025.179.1
probe	Set up job	2026-11-03T00:23:20.1309492Z Included Software: https://github.com/actions/runner-images/blob/ubuntu26/20261025.179/images/ubuntu/Ubuntu2604-Readme.md
probe	Set up job	2026-11-03T00:23:20.1312750Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu26%2F20261025.179
probe	Set up job	2026-11-03T00:23:20.1314618Z ##[endgroup]
probe	Set up job	2026-11-03T00:23:20.1337439Z ##[group]GITHUB_TOKEN Permissions
probe	Set up job	2026-11-03T00:23:20.1340496Z Contents: read
probe	Set up job	2026-11-03T00:23:20.1341666Z Metadata: read
probe	Set up job	2026-11-03T00:23:20.1342727Z ##[endgroup]
probe	Set up job	2026-11-03T00:23:20.1346179Z Secret source: Actions
probe	Set up job	2026-11-03T00:23:20.1347903Z Cache mode: write
probe	Set up job	2026-11-03T00:23:20.1349365Z Prepare workflow directory
probe	Set up job	2026-11-03T00:23:20.2072538Z Prepare all required actions
probe	Set up job	2026-11-03T00:23:20.2148285Z Getting action download info
probe	Set up job	2026-11-03T00:23:20.3750512Z Download action repository 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1' (SHA:3d3c42e5aac5ba805825da76410c181273ba90b1)
probe	Set up job	2026-11-03T00:23:20.6074462Z Download action repository 'actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0' (SHA:6d4fd22b20465ccc0f7354476588e8df7c9ca0e0)
probe	Set up job	2026-11-03T00:23:20.8692579Z Complete job name: probe
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9630696Z ##[group]Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9631843Z with:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9632328Z   persist-credentials: false
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9632918Z   repository: afarah101/football-twin
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9637822Z   token: ***
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9638292Z   ssh-strict: true
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9638761Z   ssh-user: git
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9639207Z   clean: true
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9639683Z   sparse-checkout-cone-mode: true
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9640244Z   fetch-depth: 1
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9640711Z   fetch-tags: false
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9641178Z   show-progress: true
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9641650Z   lfs: false
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9642085Z   submodules: false
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9642562Z   set-safe-directory: true
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9643104Z   allow-unsafe-pr-checkout: false
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:20.9643911Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3490238Z Syncing repository: afarah101/football-twin
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3493112Z ##[group]Getting Git version info
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3494550Z Working directory is '/home/runner/work/football-twin/football-twin'
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3652583Z [command]/usr/bin/git version
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3724952Z git version 2.56.0
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3899040Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3909236Z Temporarily overriding HOME='/home/runner/work/_temp/06b2761c-acb5-4ab8-8598-20cce1045841' before making global git config changes
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3912463Z Adding repository directory to the temporary git global config as a safe directory
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3915052Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/football-twin/football-twin
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3920731Z Deleting the contents of '/home/runner/work/football-twin/football-twin'
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3923187Z ##[group]Determining repository object format
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3925340Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3927450Z ##[group]Initializing the repository
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.3930092Z [command]/usr/bin/git init /home/runner/work/football-twin/football-twin
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4063195Z hint: Using 'master' as the name for the initial branch. This default branch name
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4066336Z hint: will change to "main" in Git 3.0. To configure the initial branch name
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4069154Z hint: to use in all of your new repositories, which will suppress this warning,
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4071255Z hint: call:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4072552Z hint:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4074159Z hint: 	git config --global init.defaultBranch <name>
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4092764Z hint:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4097081Z hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4099590Z hint: 'development'. The just-created branch can be renamed via this command:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4101280Z hint:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4102596Z hint: 	git branch -m <name>
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4103838Z hint:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4105894Z hint: Disable this message with "git config set advice.defaultBranchName false"
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4110311Z Initialized empty Git repository in /home/runner/work/football-twin/football-twin/.git/
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4113219Z [command]/usr/bin/git remote add origin https://github.com/afarah101/football-twin
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4173171Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4174897Z ##[group]Disabling automatic garbage collection
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4223376Z [command]/usr/bin/git config --local gc.auto 0
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4228310Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4272154Z ##[group]Setting up auth
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4307767Z Removing SSH command configuration
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4309497Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4323490Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4940008Z Removing HTTP extra header
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4942448Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.4974815Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5271105Z Removing includeIf entries pointing to credentials config files
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5273718Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5311263Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5619157Z [command]/usr/bin/git config --file /home/runner/work/_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config http.https://github.com/.extraheader AUTHORIZATION: basic ***
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5659001Z [command]/usr/bin/git config --local includeIf.gitdir:/home/runner/work/football-twin/football-twin/.git.path /home/runner/work/_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5698081Z [command]/usr/bin/git config --local includeIf.gitdir:/home/runner/work/football-twin/football-twin/.git/worktrees/*.path /home/runner/work/_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5740419Z [command]/usr/bin/git config --local includeIf.gitdir:/github/workspace/.git.path /github/runner_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5778821Z [command]/usr/bin/git config --local includeIf.gitdir:/github/workspace/.git/worktrees/*.path /github/runner_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5815980Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5817996Z ##[group]Fetching the repository
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.5824197Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +85372ec0d08fdc79e1df5ea20a312883a98dc2b4:refs/remotes/origin/main
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8785350Z From https://github.com/afarah101/football-twin
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8789382Z  * [new ref]         85372ec0d08fdc79e1df5ea20a312883a98dc2b4 -> origin/main
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8795940Z [command]/usr/bin/git branch --list --remote origin/main
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8828727Z   origin/main
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8835324Z [command]/usr/bin/git rev-parse refs/remotes/origin/main
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8864153Z 85372ec0d08fdc79e1df5ea20a312883a98dc2b4
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8874285Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8877170Z ##[group]Determining the checkout info
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8879827Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8881937Z [command]/usr/bin/git sparse-checkout disable
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8933738Z [command]/usr/bin/git config --local --unset-all extensions.worktreeConfig
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8972617Z ##[group]Checking out the ref
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.8976344Z [command]/usr/bin/git checkout --progress --force -B main refs/remotes/origin/main
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9055088Z Switched to a new branch 'main'
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9067464Z branch 'main' set up to track 'origin/main'.
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9075814Z ##[endgroup]
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9132718Z [command]/usr/bin/git log -1 --format=%H
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9175063Z 85372ec0d08fdc79e1df5ea20a312883a98dc2b4
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9179779Z ##[group]Removing auth
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9180913Z Removing SSH command configuration
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9182558Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9225009Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9519712Z Removing HTTP extra header
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9524378Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9566192Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9860581Z Removing includeIf entries pointing to credentials config files
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9864398Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9889475Z includeif.gitdir:/home/runner/work/football-twin/football-twin/.git.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9898400Z includeif.gitdir:/home/runner/work/football-twin/football-twin/.git/worktrees/*.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9903553Z includeif.gitdir:/github/workspace/.git.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9907077Z includeif.gitdir:/github/workspace/.git/worktrees/*.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9917937Z [command]/usr/bin/git config --local --get-all includeif.gitdir:/home/runner/work/football-twin/football-twin/.git.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9935225Z /home/runner/work/_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:21.9952720Z [command]/usr/bin/git config --local --unset includeif.gitdir:/home/runner/work/football-twin/football-twin/.git.path \/home\/runner\/work\/_temp\/git\-credentials\-eb557ed9\-df3e\-40d4\-8335\-ae322b6fe0f7\.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0008696Z [command]/usr/bin/git config --local --get-all includeif.gitdir:/home/runner/work/football-twin/football-twin/.git/worktrees/*.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0029348Z /home/runner/work/_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0045548Z [command]/usr/bin/git config --local --unset includeif.gitdir:/home/runner/work/football-twin/football-twin/.git/worktrees/*.path \/home\/runner\/work\/_temp\/git\-credentials\-eb557ed9\-df3e\-40d4\-8335\-ae322b6fe0f7\.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0109021Z [command]/usr/bin/git config --local --get-all includeif.gitdir:/github/workspace/.git.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0139610Z /github/runner_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0151689Z [command]/usr/bin/git config --local --unset includeif.gitdir:/github/workspace/.git.path \/github\/runner_temp\/git\-credentials\-eb557ed9\-df3e\-40d4\-8335\-ae322b6fe0f7\.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0196324Z [command]/usr/bin/git config --local --get-all includeif.gitdir:/github/workspace/.git/worktrees/*.path
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0214611Z /github/runner_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0231128Z [command]/usr/bin/git config --local --unset includeif.gitdir:/github/workspace/.git/worktrees/*.path \/github\/runner_temp\/git\-credentials\-eb557ed9\-df3e\-40d4\-8335\-ae322b6fe0f7\.config
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0275562Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0575451Z Removing credentials config '/home/runner/work/_temp/git-credentials-eb557ed9-df3e-40d4-8335-ae322b6fe0f7.config'
probe	Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:22.0584198Z ##[endgroup]
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0979303Z ##[group]Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0981410Z with:
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0982229Z   python-version: 3.12
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0983235Z   check-latest: false
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0994810Z   token: ***
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0996313Z   mirror: https://raw.githubusercontent.com/actions/python-versions/main
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0998286Z   update-environment: true
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.0999386Z   allow-prereleases: false
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.1000451Z   freethreaded: false
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.1001395Z ##[endgroup]
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.2299025Z ##[group]Installed versions
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.2591877Z Successfully set up CPython (3.12.15)
probe	Run actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0	2026-11-03T00:23:22.2619927Z ##[endgroup]
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.2831579Z ##[group]Run echo "understatapi==0.7.1 --hash=sha256:7e50751ad1189e82acc6afea596733d00d7a0d74cbd492238b092d137c1ed334" > "$RUNNER_TEMP/understatapi.txt"
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.2838908Z ^[[36;1mecho "understatapi==0.7.1 --hash=sha256:7e50751ad1189e82acc6afea596733d00d7a0d74cbd492238b092d137c1ed334" > "$RUNNER_TEMP/understatapi.txt"^[[0m
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.2844415Z ^[[36;1mpython -m pip install --no-deps --require-hashes -r "$RUNNER_TEMP/understatapi.txt"^[[0m
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.2850223Z ^[[36;1mpython -m pip install --no-deps --only-binary :all: certifi==2026.10.23 charset-normalizer==3.5.2 idna==3.20 requests==2.34.2 urllib3==2.8.0^[[0m
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3014343Z shell: /usr/bin/bash -e {0}
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3015814Z env:
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3017076Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3019218Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.15/x64/lib/pkgconfig
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3021369Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3023357Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3025325Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3027434Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.15/x64/lib
probe	Install understatapi and patched dependencies	2026-11-03T00:23:22.3029090Z ##[endgroup]
probe	Install understatapi and patched dependencies	2026-11-03T00:23:25.4906270Z Collecting understatapi==0.7.1 (from -r /home/runner/work/_temp/understatapi.txt (line 1))
probe	Install understatapi and patched dependencies	2026-11-03T00:23:25.7793953Z   Downloading understatapi-0.7.1.tar.gz (537 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:25.9964470Z      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 537.7/537.7 kB 4.5 MB/s  0:00:00
probe	Install understatapi and patched dependencies	2026-11-03T00:23:26.0516593Z   Installing build dependencies: started
probe	Install understatapi and patched dependencies	2026-11-03T00:23:28.6498855Z   Installing build dependencies: finished with status 'done'
probe	Install understatapi and patched dependencies	2026-11-03T00:23:28.6506546Z   Getting requirements to build wheel: started
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.2304187Z   Getting requirements to build wheel: finished with status 'done'
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.2326747Z   Preparing metadata (pyproject.toml): started
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.4808554Z   Preparing metadata (pyproject.toml): finished with status 'done'
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.4834362Z Building wheels for collected packages: understatapi
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.4845186Z   Building wheel for understatapi (pyproject.toml): started
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.7655053Z   Building wheel for understatapi (pyproject.toml): finished with status 'done'
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.7671680Z   Created wheel for understatapi: filename=understatapi-0.7.1-py3-none-any.whl size=15443 sha256=d593d683620356800cdc18f7a6a89c1b0e1b547c2c709bf4c7bcf72a1c286c0b
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.7691847Z   Stored in directory: /home/runner/.cache/pip/wheels/38/de/d6/f84cd8cb7746c9685b36beb27b8840f43e8b3f93cf288343c5
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.7698261Z Successfully built understatapi
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.7836647Z Installing collected packages: understatapi
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.8037870Z Successfully installed understatapi-0.7.1
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.8063479Z 
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.8064241Z [notice] A new release of pip is available: 26.2.2 -> 26.3
probe	Install understatapi and patched dependencies	2026-11-03T00:23:29.8067375Z [notice] To update, run: pip install --upgrade pip
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.0087125Z Collecting certifi==2026.10.23
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.2376823Z   Downloading certifi-2026.10.23-py3-none-any.whl.metadata (2.5 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.5418769Z Collecting charset-normalizer==3.5.2
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.6139321Z   Downloading charset_normalizer-3.5.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (46 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.7607166Z Collecting idna==3.20
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.8322986Z   Downloading idna-3.20-py3-none-any.whl.metadata (7.2 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.9204823Z Collecting requests==2.34.2
probe	Install understatapi and patched dependencies	2026-11-03T00:23:31.9947204Z   Downloading requests-2.34.2-py3-none-any.whl.metadata (4.8 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.0698959Z Collecting urllib3==2.8.0
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.1420849Z   Downloading urllib3-2.8.0-py3-none-any.whl.metadata (7.4 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.2249191Z Downloading certifi-2026.10.23-py3-none-any.whl (135 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.3823818Z Downloading charset_normalizer-3.5.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (257 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.5299280Z Downloading idna-3.20-py3-none-any.whl (69 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.6076397Z Downloading requests-2.34.2-py3-none-any.whl (73 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.6853447Z Downloading urllib3-2.8.0-py3-none-any.whl (135 kB)
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.7226031Z Installing collected packages: urllib3, requests, idna, charset-normalizer, certifi
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.9591013Z 
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.9591060Z 
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.9606079Z [notice] A new release of pip is available: 26.2.2 -> 26.3
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.9607053Z Successfully installed certifi-2026.10.23 charset-normalizer-3.5.2 idna-3.20 requests-2.34.2 urllib3-2.8.0
probe	Install understatapi and patched dependencies	2026-11-03T00:23:32.9646660Z [notice] To update, run: pip install --upgrade pip
probe	Run one live call	2026-11-03T00:23:33.0096125Z ##[group]Run python scripts/probe_understat.py
probe	Run one live call	2026-11-03T00:23:33.0096650Z ^[[36;1mpython scripts/probe_understat.py^[[0m
probe	Run one live call	2026-11-03T00:23:33.0130027Z shell: /usr/bin/bash -e {0}
probe	Run one live call	2026-11-03T00:23:33.0130341Z env:
probe	Run one live call	2026-11-03T00:23:33.0130679Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Run one live call	2026-11-03T00:23:33.0131251Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.15/x64/lib/pkgconfig
probe	Run one live call	2026-11-03T00:23:33.0131821Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Run one live call	2026-11-03T00:23:33.0132356Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Run one live call	2026-11-03T00:23:33.0132919Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.15/x64
probe	Run one live call	2026-11-03T00:23:33.0133521Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.15/x64/lib
probe	Run one live call	2026-11-03T00:23:33.0133992Z ##[endgroup]
probe	Run one live call	2026-11-03T00:23:53.5277384Z python 3.12.15
probe	Run one live call	2026-11-03T00:23:53.5278616Z understatapi 0.7.1
probe	Run one live call	2026-11-03T00:23:53.5279329Z requests 2.34.2
probe	Run one live call	2026-11-03T00:23:53.5279928Z urllib3 2.8.0
probe	Run one live call	2026-11-03T00:23:53.5280467Z idna 3.20
probe	Run one live call	2026-11-03T00:23:53.5281174Z certifi 2026.10.23
probe	Run one live call	2026-11-03T00:23:53.5281782Z charset-normalizer 3.5.2
probe	Run one live call	2026-11-03T00:23:53.5282482Z error type: ConnectTimeout
probe	Run one live call	2026-11-03T00:23:53.5283162Z http status from err.__cause__: None
probe	Run one live call	2026-11-03T00:23:53.5285812Z error detail: HTTPSConnectionPool(host='understat.com', port=443): Max retries exceeded with url: /getPlayerData/2371 (Caused by ConnectTimeoutError(<HTTPSConnection(host='understat.com', port=443) at 0x704e83206450>, 'Connection to understat.com timed out. (connect timeout=20)'))
probe	Run one live call	2026-11-03T00:23:53.5289773Z http status: None
probe	Run one live call	2026-11-03T00:23:53.5290508Z http responses received: 0
probe	Run one live call	2026-11-03T00:23:53.5291299Z rows returned: no
probe	Run one live call	2026-11-03T00:23:53.5498278Z ##[error]Process completed with exit code 1.
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.5656091Z Post job cleanup.
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6646645Z [command]/usr/bin/git version
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6769037Z git version 2.56.0
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6849648Z Temporarily overriding HOME='/home/runner/work/_temp/7bea692d-be0e-4c4b-9c77-bd0528cdc399' before making global git config changes
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6866586Z Adding repository directory to the temporary git global config as a safe directory
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6886911Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/football-twin/football-twin
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6888917Z Removing SSH command configuration
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6889634Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.6946011Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.7432773Z Removing HTTP extra header
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.7448941Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.7473525Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.8187164Z Removing includeIf entries pointing to credentials config files
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.8206569Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
probe	Post Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1	2026-11-03T00:23:53.8266862Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
probe	Complete job	2026-11-03T00:23:53.8882713Z Cleaning up orphan processes
```

## Outage evidence

Other projects report the same problem. All three pull requests were read on 2026-11-03 with `gh api repos/<owner>/<repo>/pulls/<n>`, and all were opened on 2026-11-02.

| Pull request | State | What it reports |
|---|---|---|
| [AkshitPareek/fpl-lineup-optimizer#32](https://github.com/AkshitPareek/fpl-lineup-optimizer/pull/32) | Closed, not merged | Requests time out from Cloud Run and from a local machine. |
| [hediblk/football-predictions#81](https://github.com/hediblk/football-predictions/pull/81) | Merged | On 2 November, all five league endpoints and the EPL page still time out. |
| [fantasy-database/fantasy-database.github.io#15](https://github.com/fantasy-database/fantasy-database.github.io/pull/15) | Merged | GitHub's servers could not look up understat.com, and a second run three minutes later failed the same way. Other sites were fine. |

What this changes:

- **An outage on Understat's side is now the likeliest explanation.** Unrelated projects on different networks report failures from 2 November, and our two failures are on 3 November.
- **The home failure may be the same outage, not a Virgin Media block.** A whole /24 failed from home, which could fit a hosting-side network problem. This is an inference and was not tested.
- **The symptoms differ.** One project reports failed DNS lookups, while our probes resolved the name and then could not connect. All of them got no answer from the site.
- **The hotspot test is now worth less,** because it would probably fail too. The daily watch in `.github/workflows/understat-probe.yml` replaces it for finding out when the site returns.

These are other project authors' reports, not a statement from Understat. The cause and expected return date are unknown.

The verdict in this report does not change: UNSURE, and not safe to wire in at ticket 5 until a live call passes.
