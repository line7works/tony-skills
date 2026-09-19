# recheck-v2 E11 round 2: the frozen repair package

Status: FROZEN when this file's first commit lands on `docs/recheck-v2-e11`. After that, the text
changes only by an amendment Tony rules and the control room records in the E11 contract
(`2026-09-16-recheck-v2-e11-qualification.md`, section 7). A builder never edits this file.

## 1. Authority and bounds

- Tony's ruling E11-40 (2026-09-18): "Do what Astra said." Her recommendation, verbatim: accept this
  round's failure and keep its records; authorize one frozen repair package covering the four
  safeguards and her six rig repairs, one independent verification, and the rerun only after a native
  isolation check passes, with any narrower target written down explicitly; stop after that round,
  report each tool's demonstrated capabilities and gaps, and leave production eligibility unchanged.
- Ruling 17 binds the shape: one fix round, one verification round, then carry. There is no round 3.
- D2 (no ceiling) pays for the trials and the reviewer; it does not license tuning until a number rises.
- D4 is untouched: reviewer counts, model floors, suite reruns and production review eligibility stay
  as they are.
- The plan's E11 words bind: no instructions added to manufacture an uplift; a failure produces a
  bounded repair and a disclosed rerun set, not indefinite prompt tuning.
- Sources: Astra's read of the rerun (`astra-outputs/e11/read2/read2.md`, sections 6 and 7) and her
  weigh-in (`astra-outputs/e11/weigh-in/weigh-in.md`), both in Clerk's packet.

## 2. Scope amendment E11-41: the narrower target, written down

Round 2 qualifies the recheck-v2 pilot on **claude-code and codex**. A pass means, for each of those
two setups, every mandatory check of the E11 matrix has evidence and holds, and these hand-off pairs
pass the repaired consumer test: **claude-code to codex** and **codex to claude-code**, one directed
pair each, plus both continuation kinds (handoff and compaction) on each of the two setups, with the
compaction boundary shown before resumed work.

**opencode (Qwen) and opencode-deepseek** run the full set under the same bench. They qualify only if
they pass every mandatory check on their own. Otherwise each is reported as a capability gap with its
measured numbers, and the two OpenCode consumer pairs toward the qualified setups are reported, not
required. Headless compaction on OpenCode stays a recorded gap unless a supported mechanism is
demonstrated independently; it is never called a pass.

The result of round 2 is reported as **partial qualification on the named setups**, never as the
portability target achieved. This amendment changes the experiment's scope. It changes nothing about
production review eligibility.

## 3. The repair list (frozen)

Every item is executable support or necessary contract wording. No item adds prose meant to make a
model behave. Each item names the failure it removes, the coverage it must have, what it must not
hide, and its acceptance check. "Before" means the repair branch at `4351654`; "after" means the
round-2 tip.

### S1. The adapter refuses writes outside the fenced folder

- Removes: claude-code's writes of `/tmp/inv.json` and `/tmp/inv-resume.json` (three comparison
  attempts and both continuation halves); opencode-deepseek's write into the installed skill.
- Behavior: every setup's launch denies writes outside the trial's writable roots, by the harness's own
  permission mechanism where one exists (Claude Code deny rules, Codex sandbox writable roots, OpenCode
  permission rules), and by the wrapper for paths the harness cannot fence. A denied write is recorded
  as a **refusal** with the path; a write that lands outside is recorded as a **violation**. The two
  are never merged.
- Coverage: tool calls, shell commands, subprocesses the session starts, and the verifier the core
  launches. A check that a shell redirection can bypass does not count.
- Must not hide: a refusal that ends the session is an unfinished session, recorded as such; the
  scorer never counts a refused write as a clean pass of the boundary check.
- Acceptance: a per-harness live proof of one denied outside write, one allowed inside write and one
  verifier write, each recorded; a unit test on the wrapper's classification (refusal vs violation)
  that fails before and passes after.

### S2. The core refuses "fixed" on an outbound-required item without a service observation

- Removes: codex's two static clearances on F5.
- Behavior: for an item whose contract declares an outbound observation required, the core's result
  writer rejects disposition `fixed` unless the evidence carries a service observation bound to the
  item (the named endpoint or service, the observed state, the command or call that produced it, and
  its retained output). A static code read never satisfies it. The requirement comes from the contract
  field, not from an F5-specific patch.
- Must not hide: a rejected `fixed` becomes `verification_blocked` with reason `missing_evidence` and
  the rejected claim retained in the record, so the model's claim stays visible.
- Acceptance: a core unit test with a fake `fixed` claim lacking the observation (rejected) and one
  with it (accepted), failing before and passing after; the validator rejects a record whose `fixed`
  item has no bound observation.

### S3. The stop reason is derived from execution, not chosen by the model

- Removes: the wrong `missing_evidence` reasons on claude-code F5 r2 and both opencode F5 runs after a
  real, failed execution.
- Behavior: when the core ran the verifier or the named command, it sets the reason from the
  structured execution status and the retained raw output: a policy refusal or unresolvable host is
  `verification_blocked`; a command that ran and showed the defect is `reproduces`; a missing input is
  `missing_evidence`. The model's stated reason is retained beside the derived one. Unknown outcomes
  stay unresolved rather than mapped to a default.
- Depends on R6 (the F5 method ambiguity settled first).
- Must not hide: the distinction between a refused execution, an errored one and one that ran; one
  generic mapping is not acceptable.
- Acceptance: unit tests for each recognised outcome, failing before and passing after; a replay of
  the 12 F5 comparison attempts showing the derived reason per attempt beside the recorded one.

### S4. The output block is generated by the core and checked by the adapter

- Removes: opencode F6 r1's reply without the block; any reply whose dispositions contradict the
  result.
- Behavior: the core emits the output block from the result record; the adapter checks the final
  assistant text (the real one, read from the harness's native trace, never the echoed user request)
  carries that block and that its dispositions agree with the result.
- Must not hide: an unfinished inspection is not made complete by a generated block; the reply
  collector's known false positive (taking the user's text as the reply) is repaired in R2 before this
  check is trusted.
- Acceptance: adapter tests per harness on a trace with the block, without it, and with a
  contradicting block, failing before and passing after.

### R1. Finish fix 8 against the real record shapes

- Fix 8 as committed at `4351654`, plus whatever Astra's recheck8 leaves open, plus read2's point:
  the capture selector must accept valid dotted run ids and must not select an unrelated
  `launch-x.trace.json`.
- Acceptance: the fix-8 tests; a selector test with dotted ids and the unrelated file; replay of all
  126 comparison and continuation grades and 16 consumer records into revision `e11-round2-1` with the
  originals byte-identical; the four routing score records rescored under the same revision.

### R2. Repair the measurements without changing any past session outcome

- Normalise Codex `file:` working-directory paths; preserve shell argv boundaries; parse
  here-documents as data; distinguish completed errors, refusals, interrupted calls and writes that
  preceded an error; cover every call in an exec block.
- Evidence checks read the retained raw report, the actual scenario and the observed output, not a
  required module token in one free-text field.
- The delivered reply's dispositions must agree with the result.
- Collect OpenCode resume text from its native trace; export the bound session-store rows; keep
  absent model, effort and cost values as unavailable, never zero.
- Continuation labels are set independently of grade ok.
- Reviewed-source accounting: every source a session read is listed with its origin (this campaign,
  a prior root, the stage, the installed home).
- Acceptance: the replay in R1 shows the corrected witnesses per attempt; the 19 real outside
  destinations remain, the nine demonstrated false detections are gone; no grade decision flips
  without a named reason in the revision's summary.

### R3. Repair the consumer test as a test of the declared route

- The caller input carries the real harness and model facts and the run date, so "take the payload
  whole" can succeed.
- A consumer-answer schema is published in the contract, tied to the checkpoint's native per-item
  states, not to an undocumented derived shape.
- Each original artifact path is bound through the producer's recorded run directory to its retained
  file and then to the pair copy; content hashes are compared with that explicit relocation allowed.
- History is preserved; the intended completed outcome is checked separately from a valid terminal
  envelope (a correct `verifier_unavailable` is not a pass and not a crash).
- Each pair's manifest, input and run artifacts are retained.
- Consumers are graded only after every consumer session has ended, and no session can read any
  other trial or any grading record.
- Acceptance: the 16 existing consumer records replayed under the repaired grader with the reasons
  per check; a schema test; a staging test on relocated paths.

### R4. A clean, independently measured bench

- Both conditions, prior campaign roots, other setups' installs, cached routing text and grading
  records are isolated from every session.
- Isolation is measured with each harness's actual tool permissions, including its verifier, not with
  a Python child that shares environment variables.
- The preflight is native and must report `separated: true` on all four setups; `accepted_unseparated`
  is not qualification evidence.
- The manual-only guard's uncovered read path is closed and every selection is inspected, not only
  the first target.
- Any change to the deployment layout (where homes, stages and roots live) is written up for Tony
  before it is made.
- Acceptance: the native preflight passes on all four setups on the new root; the 12 environment
  probes pass; the manual-only guard proof per harness.

### R5. Recording completeness

- Writable-root records are named by trial, attempt and continuation half and reserved without
  replacement.
- Consumers emit the same failure interruption as every other kind.
- `status` reports original, latest and attempt counts explicitly; `timed_out` reads a field that
  exists.
- Null costs stay null; separately bound verifier and resume usage is included when available.
- A source-to-review-copy manifest explains every omission or changed hash.
- The 26 claude-code run-tree hash differences are resolved first on the original root with Astra's
  read-only `live-record-check.py` (mode `hashes`) and explained, never regenerated.
- Acceptance: deterministic tests; the manifest generated for the round-2 copy; the hash check
  output filed.

### R6. Settle the F5 method

- The fixture promises an outbound-blocked verifier; the records alternate between declining the
  prohibited operation and running into an unresolvable host. The round chooses one deterministic
  policy refusal, documents the truthful method representation in the contract, and keeps the
  obligation to leave the item open without the named service evidence.
- Claude-code F5 r1's method-only grade is carried or re-derived under this explicit rule, never
  silently flipped.
- Acceptance: the 16 F5 comparison trials in the rerun show one method; the answer key's F5 entries
  match the documented method; a control-room note records which of the two the round chose and why.

## 4. Sequence, owners and gates

1. **Freeze.** This file committed on `docs/recheck-v2-e11`. Control room.
2. **Builder's plan.** The builder (Opus 5 at high, the same lane as the repair round) maps every
   item S1 to R6 to files, functions and tests, in a plan the control room checks against this text
   before any code changes. Anything the plan cannot cover is carried, in writing, not narrowed
   silently.
3. **One repair round.** The builder implements the plan in the repair worktree on
   `feat/recheck-v2-e11-repair`; per-harness live proofs only where an item names one (S1, R4), never
   overlapping a live campaign; the control room runs the gates (the gates-O shape: runner suite and
   `check` on both interpreters, core on both jsonschema pins, the three adapter suites, examples,
   E7 checks, the E11 suites before and after) and commits. The replay revision `e11-round2-1` is
   produced on the round-1 rerun root with originals byte-identical.
4. **One independent verification.** Astra at high, on a copy behind the wall, against this file:
   every item CLEARED or carried with a label. Ruling 17: no second fix round; a carried item is a
   documented gap in the round-2 report.
5. **The new root and the native preflight.** `stage`, `plan` (360 ids), `install`, `verify`,
   `probe-env`, `preflight` on a fresh root. The preflight must report native `separated: true` on all
   four setups, twelve current probes, matching installed identities and passed allow rules. Any
   failure stops the round here with a report; no rerun.
6. **The rerun.** Once. 360 trials = 96 comparison + 8 continuation + 240 routing + 4 manual-only +
   12 consumers, plus 12 environment probes; the once-only retry rule; no consumer before every
   producer has finished; no grade readable during any session; a failure interruption for every
   unsuccessful attempt. OpenRouter planning range 6 to 11 dollars for the two OpenCode lanes, a
   range, not a cap and not a reconciled charge; the balance is read before and after. Tony's E11-40
   ruling authorises the launch conditional on step 5; the control room reports the preflight result
   and the balance in chat before starting it.
7. **Grade, read, report.** Grading after the run ends; the control room's reading and Astra's
   independent read side by side, in chat; the report names each setup's demonstrated capabilities
   and gaps in the matrix's terms. Verdict in chat, never on a board.
8. **Stop.** E11 closes with that report. Whatever qualified under section 2 is the qualified set for
   E13 onward. Whatever did not is a recorded gap for a later version. Production review eligibility
   is unchanged. Then A12a, the close hand-off and the Phase 4 estimate.

## 5. Forbidden in this round

- Any change to `SKILL.md` prose or the adapters' instruction text beyond the contract wording items
  S2, S3, R3 and R6 name.
- Any change to the sealed trigger set or the held-out requests; any repeated description tuning.
- Lowering a floor, a reviewer count, or a suite rerun; calling an unavailable compaction a pass.
- Editing, deleting or regenerating anything under the round-1 roots
  (`e11-repair-qualification`, `e11-repair-qualification-2`, the proof roots); new revisions are
  written beside the originals.
- A second fix round after the verification; a round 3.

## 6. Reporting after the round

One report, in chat first, then filed: per setup, the mandatory-check matrix with the record behind
each cell; the consumer pairs; the routing rates; the continuation results; the OpenRouter figures for
the two OpenCode lanes only; the list of carried items; the qualified set under section 2; the gaps.
The report says what was demonstrated and what was not. It does not say what a later version might do.
