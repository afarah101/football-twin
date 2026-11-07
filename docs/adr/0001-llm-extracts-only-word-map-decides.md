---
status: accepted
---

# The LLM only extracts; a versioned word map in code decides

Claim Check's LLM (Groq Llama-3) fills a fixed Extraction from a Claim: subjects, claim words, polarity, tense, form, and named seasons and Reference group, all copied verbatim. Deterministic code then builds the ClaimQuery: a versioned word map gives each word its Readings, Main metrics and threshold, and a versioned Level scale gives the level. An unmapped word gives "Can't check with this data", reason "claim word not in catalogue". The LLM's only other job is the 2 Summary lines, which a code Guard checks.

We chose this over letting the LLM pick the metric (as the first owner brief wrote it, "the LLM parses the claim into subject, metric, window, peer group"). When the LLM picks the metric, an ambiguous word like "defensive" gets one meaning chosen silently inside a prompt. That can't be tested, and it changes when the model changes. With the map in code, the ambiguity rule (every Reading is checked and shown) holds by construction, verdict tests run as pure code, and a model change touches only the Extraction tests (owner, Q5, 7 Nov 2026, `docs/specs/claim-check.md`).

## Consequences

- The catalogue grows only by editing the map, never by prompting. Unmapped words are logged in LangFuse so the map can grow.
- Every Verdict cites the word-map and Level-scale versions, and changing either one triggers the outside review again (Q16).
