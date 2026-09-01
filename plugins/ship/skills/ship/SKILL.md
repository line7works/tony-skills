---
name: ship
description: Run one whole slice loop with a single command — find the build doc, /build the named slice, /signoff, fix every BLOCKER and MAJOR, /recheck, at most one extra fix-and-recheck lap, then report. Use when the user says "/ship A", "ship slice B of docs/plan.md", or wants the full build→signoff→fix→recheck loop run on one slice without typing the chain by hand.
---

# Ship

The whole loop, one command. `/blueprint` draws the plans; `/ship` takes one slice of them all the way through: framed by /build, inspected by /signoff, punch list worked, re-inspected by /recheck — and stops. It replaces the chain Tony types by hand every slice. The stations keep their own rules: /ship schedules the visits, it never runs a station its own way.

**The spine — compose, never copy.** Every station is invoked by name and its own SKILL.md governs it in full. /ship adds only the schedule, the lap limit, and the stop conditions. Nothing from the stations' rulebooks is restated here, so their upstream changes flow through.

**The one unforgivable move is the silent third lap:** grinding past the retry limit — or past any stop condition — because finishing felt close. The limits exist because "almost done" is where judgment goes bad. Stopping with an honest report is a good outcome.

## Step 0 — Hook check

The documented summon line is `/goal /ship <slice> [doc]` — bare, nothing to memorize; Tony types it, and a skill cannot arm the Stop hook. **This skill defines what that goal condition means, and the session grading the hook honors it:** a "/ship <slice>" goal is met when /ship ends by its own rules — ALL CLEAR, an honest stop, or a pause held awaiting Tony. All three are the skill working; none is an unmet goal (per Tony, 2026-08-20, after two live runs where a bare condition read literally made the hook block honest endings). Never grind past a stop condition or answer a pause yourself to satisfy the hook — the stop or pause stands. Check whether this session showed the "Stop hook is now active" confirmation for this run and record the answer. Armed or not, the run proceeds identically — the report labels it honestly, never claims armed when it wasn't.

## Step 1 — Find the doc

A doc named in the invocation is the doc. Otherwise the allowed sources are exactly two: the current working repo (hunted per /build's Step 1 doc tiers, its ask rules unrestated here) and the plan already established in this session. **This is a deliberate /ship-specific narrowing of /build's hunt, said aloud per rule 1:** the vault project folder, other repos, ~/Developer, and the home directory are off the table, and so is inventing narrowing heuristics across candidates (per Tony, 2026-08-20). Nothing found in those two sources — or anything the hunt cannot resolve (doc or slice) — means ask Tony specifically what he wants built: a pause, never a hunt expansion, never a stop.

## Step 2 — Build

Invoke /build on the named slice of the found doc. /build's own contract, preflight, rules, and report govern. If /build honestly stops mid-slice (PARTIAL or STOPPED), that is stop condition 3: report and end the run — never paper over it and continue to inspection.

## Step 3 — Signoff

Invoke /signoff on the built slice. Its independence, model floor, and verdict machinery are its own. A clean SIGNED OFF — no BLOCKER or MAJOR charged to this slice — ends the loop: skip Steps 4–6 and go to Step 7 with Result ALL CLEAR and Recheck marked not run; if Tony's invocation ordered MINOR fixes, run Step 4 for those MINORs first (they never gate and never trigger a recheck). Findings /signoff's sweep raises from prior slices are never this run's to fix (they live outside the slice scope): they go in the report's Remains with a /recheck recommendation.

## Step 4 — Fix

Work the punch list: every BLOCKER and MAJOR charged to this slice, fixed directly by this session (never by re-invoking /build). MINORs are left unless Tony says otherwise in the invocation or mid-run — with one exception: a fix-introduced MINOR /recheck names is fixed unasked, because ALL CLEAR requires fix-introduced defects closed (Step 6). A MAJOR only Tony can resolve (an unexercisable criterion, a hosted-only check) is a pause: put the waive-or-hold question to him. If Tony waives or reopens a finding mid-run, record his word as the standing dated `WAIVED (per user)` / `REOPENED (per user)` line in the build doc's ledger, placed by the siblings' placement rule — the one doc write /ship's rule 2 sanctions, since a chat-only waiver counts for nothing downstream. Two tripwires while fixing: a fix that would require changing the spec is stop condition 2 — stop and report, never silently build the corrected version; a fix that wants to touch files outside the slice scope (what the build doc's slice defines, per /build's boundary rules) is stop condition 4 — stop and report.

## Step 5 — Recheck

Invoke /recheck on the fixed findings. Its closed checklist, independent verifier, and card flip are its own. ALL CLEAR ends the loop: go to Step 7.

## Step 6 — The one extra lap

Not ALL CLEAR: run exactly one more fix-and-recheck lap, on the still-open findings plus any fix-introduced defects /recheck named (its narrow door admits those, and ALL CLEAR requires them closed). Still not ALL CLEAR after that is stop condition 1: stop and report. Never a third lap unasked — Tony ordering more laps is the only way one happens.

## Pause vs stop

Two different interruptions, kept distinct:

- **Pause** — a station puts a question to Tony (a stop-and-ask, a Tony-only ruling, a waiver decision). /ship passes the question through verbatim and waits; his answer resumes the run where it paused. The question was coming to him either way. A pause never emits the SHIP block — the run hasn't ended; pauses that happened are noted in the final report's Bottom line.
- **Stop** — one of the four enumerated conditions: (1) the extra lap is exhausted without ALL CLEAR, (2) a fix would change the spec, (3) /build honestly stops mid-slice, (4) work wants to touch files outside the slice scope. Each is "stop and report", never "use your judgment." The run ends; what happens next is Tony's call.

## Step 7 — Report and stop

Emit the SHIP block and end the turn. The git gates are untouched: no push, no PR, no merge — those words are Tony's alone, and a finished loop is not one of them.

## The rules

1. **Compose by name.** Each station runs under its own SKILL.md. /ship never restates, overrides, or abbreviates a station's rules — and never skips a station.
2. **The stations' records are theirs.** Build ledger lines, punch-list blocks, and `Status:` cards are written by the stations that own them. /ship writes nothing into the build doc itself, with one sanctioned exception: recording Tony's mid-run waiver or reopening word as its dated ledger line (Step 4) — /ship is then the station receiving the user's word, per the loop's own placement rule.
3. **Fixes are this session's hands.** Direct edits against the punch list, inside the slice's footprint, traceable to the named findings — never a re-invocation of /build, never a spec edit.
4. **The lap counter is hard.** One initial pass plus at most one extra fix-and-recheck lap. The counter never resets mid-run.
5. **Stop conditions outrank momentum.** All four end the run immediately with a report. An almost-clear punch list changes nothing.
6. **Pauses pass through.** A station's question to Tony is relayed verbatim and awaited — never answered on his behalf, never converted into a stop to avoid waiting.
7. **Report faithfully.** The SHIP block states the hook status, what ran, what each station returned, what was fixed, and what remains. Never let a clean lap imply ALL CLEAR when the record says otherwise.

## Output

```
SHIP: <slice> — <doc path>
Hook: armed | NOT armed (run unwrapped)
Result: ALL CLEAR | STOPPED (condition N: <which>)
Build: <COMPLETE | PARTIAL | STOPPED>  ·  Signoff: <verdict | not reached>  ·  Recheck: <result | not run | not reached>  ·  Card: <the slice's Status: line>  ·  Laps: <0 | 1 | 2>

Bottom line: <2-3 sentences. What shipped, what state it is in, what to do next.>

Fixed: <finding · file:line · one line each>
Remains: <each open finding · severity · what's still needed>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

Omit `Fixed`/`Remains` when empty. The stations' own report blocks (BUILD, SIGN-OFF, RECHECK) appear in chat as they run; the SHIP block is the roll-up, not a replacement.

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't take a third lap, ever, unless Tony orders it in words.
- Don't fix by editing the spec — a fix that needs the spec changed is a stop.
- Don't touch files outside the slice scope — wanting to is a stop.
- Don't skip or abbreviate a station, and don't run one under /ship's rules instead of its own.
- Don't claim the hook armed when the confirmation never appeared — label the run honestly.
- Don't answer a station's Tony-question yourself — pass it through and wait.
- Don't write into the build doc — the stations own their ledgers and cards. The one exception is rule 2's: recording Tony's mid-run waiver or reopening word as its dated ledger line.
- Don't push, open a PR, or merge — the git gates are Tony's, always.
