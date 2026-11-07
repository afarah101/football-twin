---
status: accepted
---

# Claim Check is a Conformist to Twin's stand-in join

Claim Check needs match-level rows, but Twin's `LoadedSource` doesn't carry them: a Shot has no match, team or opponent, and a PlayerSeason has season minutes only. Claim Check's own stand-in adapter calls the stand-in join functions read-only and builds its own PlayerMatch and TeamMatch records. Twin code is never changed for Claim Check, and the join's rules are taken as they are, with no translation (owner, Q11, 7 Nov 2026).

## Considered Options

- **Copy the join into Claim Check.** Rejected: two versions of the join is what the #6 spec was written to prevent.
- **Add match and team to Twin's Shot.** Rejected: the owner's brief forbids changing Twin code for Claim Check.

## Consequences

- Two pin tests keep the contexts in step. (1) Claim Check sees 315,073 joined shots, and `scripts/measure_rule3.py` still prints both pinned Pool lines. (2) Per-match minutes summed per PlayerSeason equal Twin's season minutes for every Pool PlayerSeason.
- A change to the join reaches Claim Check with no translation. If a pin breaks, that's a Fault, never a Verdict.
- With live Understat (#15), the live adapter feeds both contexts.
