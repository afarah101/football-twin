# Football Twin

Phase 1 plan and all decisions: `docs/phase-1-plan.md`.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `afarah101/football-twin`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Working without Ahmed

- Stand-in data (FBref, HF, worldfootballR) is private. Do not publish or deploy it. Vercel deploys wait for live Understat data (#15).
- Needs Ahmed's sign-off: a change to a statistical method, metric or threshold that `docs/phase-1-plan.md` or an ADR does not already record; anything on the public site; data licensing decisions. For those PRs, add the label `needs-ahmed` and do not turn on auto-merge.
- Everything else (bug fixes, tests, refactors, tickets already decided in the plan): push a feature branch, open a PR and turn on auto-merge. GitHub merges it once `verify` and `review` pass. Never push to `main`.
