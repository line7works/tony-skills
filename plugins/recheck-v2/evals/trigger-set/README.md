# Trigger set (check T1, amendment A6a, requirement R27)

Twenty requests in Tony's voice that decide whether `recheck-v2` activates on a recheck
request and stays quiet on a near miss. Written at E7 by lane T of
`docs/plans/2026-09-13-recheck-v2-e7-fixtures.md` (section 7, subsection T). No harness has
run them yet; E10 does.

## Files

| File | Count | Use |
|---|---|---|
| `requests.json` | 12 (6 activate, 6 near miss) | the tuning set: read while writing and adjusting the skill description at E10 and E11 |
| `held-out/requests.json` | 8 (4 activate, 4 near miss) | sealed: read only by the E10 scorer, never by anyone tuning the description |

## Entry shape

```json
{
  "id": "T-05-card-still-rejected",
  "text": "<the request, verbatim, as Tony would type or dictate it>",
  "expected": { "activate": true, "target": "recheck-v2" },
  "competitors": ["recheck (blocked)", "handoff"],
  "exclusion": null,
  "notes": "<why this entry is in the set>"
}
```

- `expected.target` is `recheck-v2`, another skill's name, `none` (plain conversation, no
  skill), or `none: v1 station blocked in this profile` (the request belongs to a v1 back-half
  station that the profile blocks; nothing may claim it).
- `competitors` lists skills in the v2 test profile that a naive description could match on
  this text. A `(blocked)` suffix marks a v1 station the profile does not load; it is listed so
  the scorer can tell a false trigger of the pilot from a leak of a blocked station.
- `exclusion` is `null` on an activate entry and, on a near miss, the reason the request is not
  a recheck, with the contract section where possible.

## The v2 test profile

Expectations are written for the profile the E10 harness loads: every skill in this
marketplace plus `recheck-v2`, with the v1 back-half stations (`signoff`, `recheck`,
`vertical`, `inspect`, `ship`) blocked. A request for an initial review, a whole-build review,
or a plan check therefore expects no activation at all; a request that names v1 `/recheck` by
its slash command and says nothing else about the job is a near miss (`T-12`). A request that
uses the v1 slash command and then describes recheck-v2's job (verify named fixes, flip the
card) expects `recheck-v2` (`H-05`); the two are a deliberate pair and E10 reports them side by
side.

## Sealing rule for `held-out/`

1. The tuning loop at E10 and E11 reads only `requests.json`. Nobody adjusting the skill
   description, its trigger phrases, or its front-matter opens `held-out/requests.json`, quotes
   it, or pastes it into a prompt.
2. The held-out set is run once per description revision by the scorer, after the description
   is frozen for that revision, and its results are recorded (below). Its entries are never
   edited to fit a description; a held-out entry that turns out wrong against the contract is
   reported as a finding and replaced by the control room, with the replacement logged here.
3. If a held-out request or its wording leaks into a description, a test prompt, or a tuning
   note, that entry is burned: it moves to `requests.json` and the control room writes a fresh
   replacement into `held-out/`.
4. The file carries `"sealed": true` so a scanner can refuse to load it outside the scorer.

## How E10 records rates

Per harness and per description revision, the scorer runs every request as a fresh session
opening line with the v2 test profile loaded and records, for each entry, which skill (if any)
activated. Two rates per set, tuning and held-out kept separate:

| Rate | Numerator | Denominator |
|---|---|---|
| activation rate | activate entries where `recheck-v2` activated | activate entries (6 tuning, 4 held-out) |
| false-trigger rate | near-miss entries where `recheck-v2` activated | near-miss entries (6 tuning, 4 held-out) |

Also recorded, per near miss: whether the observed target matched `expected.target` (a leak of
a blocked v1 station is its own row, distinct from a pilot false trigger). The record goes in
`evals/answer-key/` alongside the other E10 results as
`trigger-set-<harness>-<revision>.json`: one row per entry with `observed_target`,
`activated`, and `matches_expected`, plus the two rates per set. R27 passes for a harness when
the held-out activation rate and false-trigger rate are both recorded; the pass threshold is
the plan's to set at E10, not this README's.

## What the set does not test

Whether recheck-v2 does the job once activated (the fixture lanes cover that), and how a
station caller invokes the core (a caller passes the input structure and never goes through
description matching).
