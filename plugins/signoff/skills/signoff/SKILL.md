---
name: signoff
description: Independent adversarial review of freshly built work, ending in a signed verdict. Brings in a senior engineer who did not write the code, with a mandate to reject it. Use when the user says "sign off", "have a senior engineer review this", asks for an adversarial review of what was just built, or finishes a phase/slice and wants it inspected before moving on.
---

# Sign-Off

A slice just got built. Before it counts as done, an engineer **who did not write it** inspects it against the spec and either signs the card or writes a punch list.

This is the back half of `/wargame`. War game asks "how will this fail?" before building. Sign-off asks "did you actually build it, and does it hold?" after. Same adversarial posture, pointed backwards.

**The spine — the anti-rubber-stamp rule.** The reviewer's job is to find reasons to REJECT, not to confirm good work. A review that returns no findings must state explicitly what it tried to break and failed to break. Otherwise "looks good" is indistinguishable from "didn't look," and an unearned signature is worse than no signature — the user will trust it.

## Step 0 — Model floor

Reviewers run at **Opus-class or better**. Never pin a review subagent below `opus`; if this session is at or above that, omit the model override so agents inherit it. A weak adversary produces a confident, wrong signature.

If this session itself is below the floor, say so and offer to run anyway as a lightweight check explicitly labeled NOT a sign-off.

## Step 1 — Establish scope and spec

Two questions, both answered before spawning anyone:

**What got built?** Auto-detect, in this order — uncommitted working diff, else the current branch's diff against its base, else the files touched this session. State the detected scope in one line. If the user named a slice or phase, that wins.

**What was it supposed to do?** Look for the build doc: a phase/slice doc under `docs/`, `plan/`, the vault project folder, or the plan established in this session. This is the acceptance criteria, not background reading.

If no spec exists, say so plainly and run in **correctness-only** mode. Never invent acceptance criteria and grade against them — that manufactures both the test and the score.

## Step 2 — Independence (hard rule)

The session that wrote the code cannot review it. It knows what the code *meant* to do and will read intent into what's on disk.

So: reviewers are always fresh subagents. They receive the scope, the spec path, and the mandate. They do **not** receive your reasoning, your justifications, or your account of what you built and why. They read the source themselves and form their own view.

Never review the diff yourself and label it a sign-off.

## Step 3 — Review

**LEAN (default).** Three parallel reviewers, one message, distinct lenses:

- `spec` — does the built thing match the doc? Hunt for silently skipped requirements, quietly narrowed scope, and stubs presented as finished. This lens matters most and is the one a generic code review misses.
- `correctness` — bugs, unhandled edge cases, error paths that swallow failures, state that can desync.
- `seams` — integration with what already shipped. Regressions in prior slices, broken assumptions at the boundary, migrations that don't run twice.

**DEEP.** Add `security` (authz, injection, secrets, trust boundaries) and `tests` (do the tests assert real behavior, or do they pass vacuously?). Use when the user says deep/thorough/full, or the slice touches auth, money, or user data.

State which depth and why in one line before starting.

Each reviewer returns findings as: claim · `file:line` · concrete failure scenario (inputs → wrong outcome) · severity.

## The rules

1. **Evidence or it doesn't count.** Every finding carries `file:line`. A concern without a location is a hunch; cut it or go verify it.
2. **Verify before reporting.** Read the source yourself on every BLOCKER and MAJOR before it reaches the user. Reviewers are fallible and a false blocker costs real time. Stamp CONFIRMED or PLAUSIBLE. Drop what you refute.
3. **Concrete failure scenario, or it's not a finding.** "This could be fragile" is noise. "Two calls in the same tick both pass the check and double-charge" is a finding.
4. **Unbuilt-by-design is not a defect.** Work the spec deliberately deferred goes in Deferred, not the punch list. Ask or flag; never invent product behavior for undesigned areas.
5. **Report, don't repair.** Sign-off is an inspection. Fixing is a separate instruction the user gives after seeing the verdict — offer, don't act.
6. **The signature is real.** Do not sign off to be agreeable. REJECTED on work the user is excited about is the entire value of the skill; a sign-off that never rejects is decoration.
7. **Declare the method.** The verdict states how the work was actually verified — executed and exercised, tests run, or static analysis only. A review that could not run the thing is weaker than one that could, and that belongs in the verdict where the user reads it, not buried in a footnote. Never let "I read the code carefully" pass as "I checked that it works."
8. **Do the arithmetic.** Where a criterion involves numbers — rates, clamps, thresholds, geometry, timing windows — compute it rather than eyeballing the code. The dangerous defect is not the obvious bug; it's the right technique applied so it doesn't achieve the stated requirement. That kind only falls out of math, and it is invisible to a diff review because the code looks textbook.

## Severity → verdict

| Severity | Meaning | Effect |
|---|---|---|
| **BLOCKER** | Spec requirement unmet, or a defect that loses data / corrupts state / breaks a shipped feature | Cannot sign |
| **MAJOR** | Real defect with a concrete failure path, but contained and fixable in place | Conditional |
| **MINOR** | Rough edge, missing guard, thin test | Punch list only |

- **SIGNED OFF** — meets spec, no BLOCKER or MAJOR.
- **SIGNED OFF WITH CONDITIONS** — no BLOCKERs; named MAJORs must be fixed before the next slice.
- **REJECTED** — one or more BLOCKERs.

## Output

Report in chat. Compact — this runs after every slice and must stay fast to read:

```
SIGN-OFF: <slice/phase>
Verdict: SIGNED OFF | WITH CONDITIONS | REJECTED
Scope: <what was reviewed>  ·  Spec: <path, or "none — correctness only">
Depth: LEAN | DEEP  ·  Method: <ran it / tests / static analysis only>

Bottom line: <2-3 sentences. What holds, what doesn't, what to do next.>

BLOCKERS   <severity · file:line · failure scenario · CONFIRMED/PLAUSIBLE>
MAJOR
MINOR
Deferred   <spec items intentionally not built — not defects>
Tried and failed to break: <what the reviewers attacked that held up>
```

Omit empty sections. No artifact file by default — offer to write the verdict into the project's vault notes or `docs/` only if the user asks or the result is REJECTED.

## What NOT to do

- Don't review your own work — always fresh subagents.
- Don't pass the reviewers your rationale for what you built.
- Don't grade against acceptance criteria you invented.
- Don't fix anything during the review.
- Don't pad the punch list to look rigorous. Verified or cut.
- Don't sign off on work you haven't verified against the actual source.
- Don't let a review that couldn't execute the code imply that it did.
