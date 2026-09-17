# recheck-v2 E11: the qualification decision (lane contract)

Control room (Clerk; Fable 5.1 at max under ruling R1f), written 2026-09-16 evening in a fresh
window opened from `~/Documents/handoffs/2026-09-16-skills-v2-e11-handoff.md`, after the negative
test (9 of 9) and before any reading was written down. E11 builds nothing. It reads the E10
records, produces the capability matrix and the diagnosis, obtains the reviewer's independent read,
and puts the go/no-go to Tony. Precedence: the plan of record binds everything here (the E11 step,
amendments A6b, A6c and A12a, decisions D2 and D4, ruling 17, crew ruling R1f); the pilot contract
(`plugins/recheck-v2/skills/recheck-v2/references/pilot-contract.md`, revision 5) outranks this
document; the E10 lane contract (`docs/plans/2026-09-14-recheck-v2-e10-runner.md`) is the record
of the campaign this step reads, and its ruling E10-73 is the campaign's own record.

## 1. What E11 delivers

- **The control room's reading**, in chat before any file: the capability matrix by mandatory
  check and setup, with the record behind every cell; the diagnosis of every grade that is not
  `ok` into one of four classes (section 4, E11-4); the routing reading per A6c.
- **The reviewer's independent read**: Astra (GPT-6) at max (R1f) on a review copy, with a
  mandate that carries the plan's criteria and none of the control room's findings. Verdict in
  Clerk's packet under `astra-outputs/e11/`.
- **The two readings side by side** to Tony, then his go/no-go. A failure produces a bounded
  repair proposal with a disclosed, priced rerun set; it is a proposal, never a change (D2, D4).
- **After the decision:** A12a, the first compile of the guide findings log, reported in chat,
  written on Tony's word.

## 2. Evidence every participant reads

This document; the plan's E11 step, A6b, A6c, A12a, D2, D4 and ruling 17 (quoted in section 6 so
the reviewer's copy carries them); the E10 lane contract sections 3 and 4 and amendments E10-40 to
E10-73; the pilot contract sections 2, 4, 7, 8, 9, 11, 13, 14 and 16; `SKILL.md`; the three
profiles (sections 1, 2, 4, 7, 8, 9); `evals/README.md`, `evals/answer-key/README.md` and every
answer-key lane file the campaign graded; `evals/trigger-set/README.md` and the tuning set; the
runner's grading half (`grade_one`, `trace_witnesses`, `_scope_violations`, `_unauthorized`,
`_interop`, `_dispositions`, `_false_fixed`, `_evidence`, `continuation_invariants`, each setup's
`activation` and `observed_target`, `routing_score`); the campaign root
`~/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/`: `operator/report.md` whole,
`tables/1/table.md`, the four score records under `routing/`, the ledgers, and every comparison
and continuation trial record with its `grade.json`.

## 3. The wall at E11

Until E11, no reviewer saw a `grade.json`, a comparison table, a routing score record or the answer
key (E10 section 3). E11 is the step that reads them, so the wall narrows by Tony's ruling below
to exactly the held-out request text.

- **Opens to the reviewer (E11-1):** every comparison and continuation trial directory as
  recorded (104 trials, their `attempts/`, about 257 MB and 12,000 files: `command.json`,
  `prompt.txt`, `result.json`, `reply.md`, `chat.md`, `validate.*`, `grade.json`, `model.json`,
  `cost.json`, `scan.json`, the harness captures with transcripts and traces, the fixture snapshot
  and the run directory); the ledgers (`trials.jsonl`, `attempts.jsonl`, `interruptions.jsonl`,
  `processes.jsonl`), `campaign.json`, `stage.json`, `runner.log`; `records/`, `probes/`,
  `stage/`; `tables/1/`; the four score records; the operator's report and her summary files;
  the plugin at `main` `6d617b5` including `evals/answer-key/`; the control room's recount script.
- **Stays closed, and is never reconstructed:** `evals/trigger-set/held-out/`, `routing-requests/`
  (the cached held-out text), every `trials/routing-*` directory (each `prompt.txt` carries one
  request's text, held-out or tuning; the whole class stays out so the copy rule needs no
  per-entry judgment), the operator's `log.md` and every `*.stderr.txt` (not needed and not
  checked line by line), and `tmp/` (the live fixture workspaces; the trial directories hold their
  own snapshots). Routing reaches the reviewer through the four score records, the ledger's
  routing rows, and the runner's routing code.
- **The copy** is made by `astra-outputs/e11/astra-kit/launch.sh copy` in Clerk's packet: rsync
  with the exclusions above, a check that fails the copy if a `held-out` directory, a
  `routing-requests` directory or a `routing-` trial directory is present, and a credential-shaped
  string scan. The copy records the commit and the file count.
- The control room's own reading opens the same files and no more.

## 4. Rulings (control room, 2026-09-16 evening, before the reading)

- **E11-1, the opening (Tony, 2026-09-16 evening).** Put to Tony as three options (full records;
  grades and keys only; hold until the control room has read). His ruling: **"Open: full
  records"**, the recommended option: "Review copy with the 104 comparison and continuation trial
  directories as recorded, the table, the four score records and the answer key. Never the
  held-out text or any routing trial directory." Section 3 is that ruling written out.
- **E11-2, the order of the two readings (control room).** The hand-off said the control room
  reads first and the reviewer after. The control room instead launches the reviewer's read on the
  copy at the same time as its own reading, with a mandate that carries the plan's criteria, the
  evidence list and the checks to run, and none of the control room's findings. Reason:
  independence is served by the reviewer not seeing the control room's reading, not by waiting for
  it; and the reviewer's read at max is the long pole. Neither reading is amended by the other
  before both exist; then they go side by side to Tony. Flagged to Tony as the control room's call.
- **E11-3, nothing changes.** No builders, no subagents, no new trials, and no change to the skill,
  the runner, the answer key, the fixtures or the campaign records in E11 without Tony's word (D2
  for trials, D4 before any change to production review eligibility). Every root under
  `~/.local/share/skills-v2-pilot/e10/` is a record. A repair is a proposal with a priced rerun set.
- **E11-4, the diagnosis classes.** Every grade that is not `ok` is classified into exactly one of:
  (1) **the model**: its judgment or behavior in the session (a wrong disposition or reason, a
  false `fixed`, a boundary crossing of its own choosing, a session that returned nothing);
  (2) **the skill text**: `SKILL.md`, the core's CLI and scripts, an adapter or profile (a
  procedure the session followed into a wrong result, a CLI rule the session could not satisfy);
  (3) **the answer key or the grading apparatus**: the key's expectations, the runner's checks and
  witnesses, the campaign's design (an expectation stricter than the contract, a witness that does
  not measure what the profile says, a shared resource across lanes);
  (4) **the run's conditions**: the provider outage, a timeout, a launch failure. A grade is read
  against its own record, never against the operator's report, a grade's `ok_because` alone, or a
  reply's prose. When a grade fails for reasons in more than one class, the class of the reason
  that alone would have failed it is recorded, and the others are noted.
- **E11-5, the numbers Tony reads.** OpenRouter charges only (his standing ruling of 2026-09-16);
  the Claude Code lane's metered dollars are never reported. Trial percentages are of settled
  trials. Every count in the reading is reproduced from `trials.jsonl` and the grade files by the
  control room's own script, and the script is kept.

## 5. Boundaries the control room keeps

- The E10 worktree `~/Developer/tony-skills-e10` stays until E11 rules on the runner. This
  document lives on branch `docs/recheck-v2-e11` in `~/Developer/tony-skills-e11`, cut from `main`
  `6d617b5`; local commits only; `git push` and a PR on Tony's "PR", merge on "merge".
- The board (`~/Developer/spine-board/state.js`) gets one write per state change, all seven
  fields, `round` moved, `plain_lint.py` PASS, the feed entry through `note.py`, then a message to
  the board window; the board window builds, publishes and commits.
- The review copy lives in the session scratchpad and is deleted with it; the kit, the mandate as
  sent, the verdict, the event stream and the exit code go into Clerk's packet.

## 6. The plan's own words (so the reviewer's copy carries the criteria)

> **E11. Make the pilot qualification decision.** Artifact: A capability matrix and a go/no-go
> decision linked to the failing or passing checks. Done when: Every mandatory check has evidence;
> no tested setup falsely clears an unresolved item or crosses its access boundary; all three
> consume each other's records; continuation checks recover the required contract and state. R
> examines the implementation and grading evidence independently. Runs: R + O. Dependencies: E10.
> Owner gate: D2 for additional trials; D4 before changing production review eligibility.
> If the skill adds no benefit over the baseline, retain only the useful routing, domain contract,
> and executable support. Do not add instructions to manufacture an uplift. A failure produces a
> bounded repair proposal and a disclosed rerun set. It does not produce indefinite prompt tuning.
> Qualification covers these setups and this closed-checklist role. It does not certify the local
> model for general signoff.

> **Amendment A6b.** Run the trigger set at three repetitions per setup, about 180 routing trials
> on top of the 78 above. Measure activation rate and false-trigger rate separately from task
> correctness. Manual-only stations must fail automatic selection; v1 back-half stations stay
> blocked in the v2 test profiles. D2 as ruled: no ceiling.

> **Amendment A6c.** Qualification also needs the measured activation and false-trigger rates for
> this setup's catalog. The directive "ALWAYS invoke" description form stays an experiment: tried
> only after a measured under-trigger, adopted only with a false-trigger count, never as the
> prescribed fallback.

> **E10's measures.** Measure false "fixed" claims, correct dispositions, evidence sufficiency,
> scope violations, unauthorized actions, record interoperability, time, and available token/cost
> data. The comparison is within each setup. It is not a Claude-versus-Astra-versus-Qwen
> leaderboard.

> **D2** (Tony): "There is no budget." No ceiling on trials or reviewer calls. **D4** (Tony, with
> Clerk's recommendation): keep reviewer counts, model floors and suite reruns as they are until
> E13 measures an alternative. **Ruling 17**: a step closes when the outside reviewer reports no
> BLOCKER, every MAJOR is fixed or carried in writing, and the deterministic checks pass; one fix
> round, one verification round, then carry. **R1f** (Tony, 2026-09-16): the E11 control room is
> Fable 5.1 at max; Astra at max for E11's independent read of the grading evidence and every E11
> review.

## 7. Amendments (control-room rulings issued while E11 runs)

- **E11-6, the decision (Tony, 2026-09-16 night).** Both readings were put to Tony side by side:
  the control room's (Clerk packet `astra-outputs/e11/control-room/reading.md`) and Astra's
  independent read at max (`astra-outputs/e11/read/read.md`: DOES NOT QUALIFY on claude-code,
  codex, opencode and opencode-deepseek and for the pilot; a seven-item bounded repair proposal;
  a disclosed rerun of 360 trials, OpenRouter estimate $6 to $11). Three options were offered
  (repair and re-run; repair only; stop here). Tony's ruling: **"Repair and re-run"**, the
  recommended option: no-go as it stands; the seven-item repair round (a fresh builder on a brief,
  Astra verifies at max, ruling 17) and the disclosed 360-trial rerun on a clean bench; E11
  reconvenes on the new records. D2 is satisfied for that rerun by this ruling; the launch itself
  still waits for his "go" in the window that runs it. D4 unchanged: production review eligibility
  does not move.
- **E11-7, the crew and the shape of the repair round (Tony, same night: "lets compact before u
  start, prep the thread and hand me a handoff. im going to bump down to fable 5.1 high for fix
  build").** Nothing starts in the E11 reading thread. A fresh window opens the repair round from
  the hand-off `~/Documents/handoffs/2026-09-16-skills-v2-e11-repair-handoff.md`. Crew (ruling R1g
  in the plan note): the control room is **Fable 5.1 at high**; the builder is an Agent-tool
  subagent that inherits the session's effort (high), model per the brief; Astra stays at **max**
  for the verification and every E11 review (R1f). The repair's scope is Astra's seven items as
  written in her section 6, read together with the control room's reading: (1) observation and
  grading: the activation and observed-target witnesses per harness (body-only delivery on Claude
  Code; the Codex custom-tool route; OpenCode's delivered block), verifier captures scanned by the
  boundary witness, resolved working directories, the actual reply required, complete done-item
  comparison, model binding gated, scenario execution judged from the native report and output
  rather than a module-name substring; (2) the shared resources and the absent condition: per-trial
  scratch and run root, other trials' records and other conditions' installs unreadable, a preflight
  read-boundary check, the same neutral output and record contract in both conditions; (3) the
  skill: canonical slice resolution before a run directory is spent, a bounded correction path for
  the input, helper and readers files inside the run's own scratch, the grant-claim rule narrowed so
  a recorded project state is not a claimed grant (`references/verifier.md` lines 24 to 29,
  `scripts/recheck.py` line 1065), the four reason definitions in the fresh verifier's brief with an
  evidenced correction path between `not_fixed` reasons, the resume step required after compaction;
  (4) continuation control and identity: stop the real OpenCode child group at the cut, prove no
  writer progresses between cut and resume, keep zero continuation counts, read item results from
  `items[].result`, start Codex's compaction ordering check at the resumed turn and test
  `witness.ok`, report the stored transaction identity on committed-run reassembly; (5) the catalog:
  after the witness fix, a real manual-only selection guard on Codex and OpenCode that also covers
  discovery by file reads, v1 exclusions preserved, no description tuning; (6) the consumer test:
  twelve directed producer-to-consumer trials through the declared input route; (7) reporting and
  hygiene: honest exit-124 labels, the gap logger reading the previous trial's duration
  (`runner.py` around line 7300), the table's no-result column, `__cf_bm` cookie values (43 files)
  covered by the scan and scrubbed from derivative copies while originals stay untouched, E10-73's
  "222 charged runs" corrected to 197 positive-cost OpenRouter attempts. Deliverables: every change
  with a test that fails before and passes after; the deterministic controls Astra named in her
  section 7 (changed done-item evidence fails, a successful read containing "rejected" stays
  successful, an empty reply fails delivery, a quoted sed replacement is not a write, verifier
  captures contribute actions, a refused operation is not a side effect); a native re-score of the
  existing routing traces (`routing-score --revision e11-native-reparse`, zero new trials, the
  original score files preserved); then Astra's verification at max on a copy, re-checks, close
  under ruling 17; then the rerun in a new root (`e11-repair-qualification`, Astra's saved plan
  `e11-rerun-plan.json` beside her read: 96 comparison, 8 continuation, 240 routing, 4 manual-only,
  plus 12 consumer trials and 12 environment probes) on Tony's "go". The plan's prohibitions stand:
  no instructions to manufacture an uplift, no indefinite prompt tuning, no lowered floors, no
  fewer reviewers, no edited sealed requests. Every root under `~/.local/share/skills-v2-pilot/e10/`
  stays a record.
- **E11-8, Astra's effort for the repair round (Tony, 2026-09-16 night: "and astra high").** Supersedes
  the Astra-at-max sentence of E11-7 and of R1g's first draft: for the repair round, Astra runs at
  **high** for the verification, the re-checks and every review of the repair; R1f's "max" stays the
  record for E11's independent read already delivered. The control room is Fable 5.1 at high, the
  builder inherits high. Every other part of E11-7 stands.
- **E11-9, the builder's model and the "go" (Tony, 2026-09-16 night: "Use opus High as the builder. This
  stays as the control room. Go").** The repair round's builder is Opus 5 at high (the same model and
  effort as the E10 runner's builder, R1c); the control room stays Fable 5.1 at high (R1g); Astra at high
  (E11-8). Launched at once as one Agent-tool subagent in the repair worktree
  `~/Developer/tony-skills-e11-repair` (branch `feat/recheck-v2-e11-repair` from `6d617b5`) on the brief
  at Clerk packet `astra-outputs/e11/briefs/e11-repair-builder.md`. Two control-room readings the brief
  carries, flagged to Tony with the ask and not objected to: the builder never writes under the E10
  campaign root (derived re-grades and the native re-score are proved on a synthetic campaign and run on
  the real root by the control room after the commit); the builder may run at most four live proof
  sessions under a new proof root `e11-repair-proof-2026-09-16` (one OpenCode hand-off cut, one manual-only
  request each on Codex and OpenCode, one Claude Code slash request), proofs of the fix and never
  qualification trials. The rerun still waits for a separate "go".
- **E11-10, the builder's report, the control room's gates and the first derived re-score (control room,
  2026-09-17 about 1:05 AM).** The builder (Opus 5 at high) reported after 3 h 26 min: items 1, 3, 6 and 7
  FIXED; 2, 4 and 5 PARTLY with the remainder carried in writing (cross-setup reads are reported by the new
  `preflight` rather than prevented on this bench; the live OpenCode freeze-and-end is unit-proved and
  live-unproven because the proof home carried the E10 campaign's `external_directory` allow rule; the
  widened manual-only guard is live-unproven on Codex after the one Codex proof reached the station through
  the setup's own marketplace source). Four live proofs under `e11-repair-proof-2026-09-16`, OpenRouter
  $0.0092. The control room re-ran every gate from `/private/tmp` (tails in the packet
  `astra-outputs/e11/control-room/verify/`): runner 410 OK under both runtimes, `check` ok under both, core
  351 OK under both interpreters, adapters 90/34/96 OK, validate-examples ok, E7 nine PASS (its first run
  collided with `check`'s closed key and was re-run), the two E11 suites 52 and 23 failing 46 and 21 on
  `6d617b5` and passing after. Committed `c0e8b55`. Then `grade --all --revision e11-native-reparse` and
  `routing-score --revision e11-native-reparse` on the E10 root: 143 derived grades and four derived score
  files written beside the originals, the 150 original grade, score and table files byte-identical before
  and after (hashes in the packet), keys reopened by `key-state --reopen`. Derived ok 8 of 143 against 20:
  twelve flips, eleven on the new `model_binding` gate comparing `openrouter/<model>` (the native witness)
  with `<model>` (the OpenCode result's id) as different models, one on the Codex hand-off's done-item
  comparison reading the E10 cut's summary shape as a change. Both are control-room findings against the
  repair and went back to the builder before Astra's verification (the control room's own gate on the
  deliverable, not a second fix round under ruling 17; Astra's round has not started). The Codex
  `gpt-5` / `GPT-5` against `gpt-5.6-sol` mismatches (11 attempts, none an ok grade) are real misreports and
  stay failures. Derived routing over completed sessions: held-out activation 0.75 / 1.00 / 0.92 / 0.91,
  false triggers 0 on all four, the recomputed target differs from the record on six Claude Code rows only,
  provider failures 0 / 0 / 58 / 62, manual-only qualified on Claude Code alone. Carried to the E11
  reconvene: the builder's finding 1 (the manual-only guard's reach is a bench-layout decision: the setups'
  homes need a layout where one setup cannot read another's, or the catalog requirement is carried
  unqualified with the guard's boundary stated) and finding 2 (install every home from the campaign that
  launches it; `preflight` now fails by name).
- **E11-11, the two control-room send-backs and the repair's final commit (control room, 2026-09-17 about
  3:20 AM).** The builder closed the E11-10 findings in two passes, each gated by the control room before
  its commit (runner 418 then 423 OK under both runtimes, `check` ok under both, the new tests failing on the
  prior commit and passing after): `d17f52b` (the model-binding gate compares the OpenCode profile's canonical
  model id; the done-item comparison reads what the retained cut carries) and, after the second derived
  revision showed two leftovers (the canonical form applied to one side only, so an absent-condition result
  reporting the id with its route read as a mismatch against an identical string; the E10 cut's summary
  carrying a disposition the cut never recorded while `harness-first/at-cut-checkpoint.json` held the full
  item rows), `31329cd` (the route is a fact of the trial and both ids canonicalise against it, ids identical
  as recorded never disagree; the done-item comparison reads the retained at-cut checkpoint and treats an
  unrecorded summary field as absent). Three derived revisions sit beside the E10 originals, which hash
  byte-identical after each (150 files): `e11-native-reparse` (c0e8b55, ok 8 of 143), `-2` (d17f52b, 19),
  `-3` (31329cd, 20). Against the original grades, revision 3 differs on exactly two attempts, both
  corrections Astra's read called for: `opencode-deepseek-F3-01-missed-case-available-r2` fails on the write
  into the installed adapter, `opencode-deepseek-F6-04-verifier-override-available-r2` attempt 1 passes on
  the native scenario witness. The eleven Codex `gpt-5` / `GPT-5` against `gpt-5.6-sol` misreports stay
  failures (none was an ok grade). All eight continuation records now compare done items against the retained
  checkpoint; the Codex hand-off and compaction hold, the Claude Code compaction fails on the missing resume
  step and the rest on invalid cuts, as the reading found. Derived routing over completed sessions: held-out
  activation 0.75 / 1.00 / 0.92 / 0.91, false triggers 0, the recomputed target differs from the record on six
  Claude Code rows only, manual-only qualified on Claude Code alone. These send-backs are the control room's
  own gate on the deliverable under E11-7 ("verify every gate yourself"), before Astra's round; ruling 17's one
  fix round and one verification round begin with her verification. The builder's own note is recorded: both
  defects came from writing a witness against one record shape and never running it against the shapes the
  absent condition and the E10-era cut produce. Astra's verification at high (E11-8) launches on the copy
  behind the E11-1 wall, scrubbed of the 43 cookie values by the repaired scanner.
- **E11-12, Astra's verification of the repair (delivered 2026-09-17 about 4:05 AM, at high, E11-8; packet
  `astra-outputs/e11/verify/`).** On the scrubbed copy at `31329cd`: every item PARTLY (1 BLOCKER, 2 BLOCKER,
  3 MAJOR, 4 BLOCKER, 5 BLOCKER, 6 BLOCKER, 7 MAJOR) and five NEW findings (BLOCKER: a repeated `grade
  --revision` overwrites the earlier derived file; a provider-failed manual-only launch reads as catalog
  qualification; a directory listing counts as a completed foreign read. MAJOR: the Codex compaction reader
  takes the last record mentioning the run as the resumed turn; the consumer grader compares evidence on a
  40-character prefix). What she confirmed working: the three delivery witnesses, the verifier captures
  scanned (33 / 11 / 12 / 9 actions on four retained trials where E10 read zero), both former `/`
  destinations gone, the F6 scenario witness with the second source still required, the derived revisions
  beside untouched originals (her own hash manifest), the six deterministic controls, canonical slice
  resolution and `check-input`, the status-record rule, the reason definitions and correction, the resume
  requirement, the readers scratch instruction, child-group discovery and the stored transaction identity,
  the six retained full-object done-item comparisons, the guard on this setup's own copies, the consumer
  command's rejection of a dropped item, the new timeout label, the gap clock, the table columns, the cookie
  scanner and scrub; the E10-73 attempt accounting reproduced; the five witness questions resolved by entry
  id (C H-01 is a measured selection under the repaired reader; C H-05 / H-06, Q H-05-r2 and D H-02-r1 are
  completed non-deliveries). Her suite runs failed on her sandbox's limits as every round; she read the
  control room's tails. Rerun set confirmed: 348 plus the 12 consumers the repaired planner now mints itself
  plus 12 probes; requests and repetitions unchanged; "not ready to establish qualification" until the open
  deterministic checks close, the preflight is required before any launch, every home is installed from the
  new campaign, and valid continuation and catalog proofs exist. **The fix round (ruling 17's one):** the same
  builder on the brief `astra-outputs/e11/briefs/e11-repair-fix.md` (eight numbered findings in her order,
  item 5's other-setup readability carried to Tony as the bench-layout decision, one more live OpenCode
  hand-off attempt after the control room installs the proof campaign's own home); then her re-check
  (`launch.sh recheck`); then carry. The control room's reading of item 5 for the rerun, flagged to Tony: run
  with the guard covering this setup's root and the campaign stage, and let the catalog requirement carry
  unqualified on any setup where the station stays reachable, which is Astra's own recommendation; a home
  layout where one setup cannot read another's is a scope change for Tony to rule on, not a fix-round item.
- **E11-13, the fix round's commits, the control room's gate and send-back, and the derived revisions 4 and
  5 (control room, 2026-09-17 about 7:40 AM).** The builder closed the eight E11-12 findings in one pass
  (its report section 11): a derived `grade --revision` claims its name and never overwrites; a write
  counts only when the harness's own record says it completed and the call's own working directory
  resolves its relative destinations; every launch refuses without a passed or accepted read-boundary
  record, `usable_as_comparison_evidence` is a grade check, and only a completed read of another trial's
  contents excludes (a listing is a listing); catalog qualification needs a completed, guarded, witnessed
  non-selection and a provider-failed launch qualifies nothing; the report derives a retained row's label
  from its exit code without editing the ledger; the compaction reader takes the first user turn carrying
  the resume request and records the three-line ordering; the consumer grade compares whole evidence
  references, hands the producer's findings over as explicit items, and reads a validating result and a
  delivered reply; and the core downgrades a static `fixed` to `not_fixed` / `verification_blocked` when a
  retained report of the run recorded a stopped execution for the item. One live OpenCode hand-off rerun
  on the proof root made the cut the E10-era run could not (attempt 1: cut valid, both process groups
  signalled and gone, sixteen files unchanged across the cut, invariants held). The control room gated it
  from another directory (runner 452 OK both runtimes, `check` ok both, core 351 both interpreters,
  adapters 90/34/96, examples clean, E7 nine PASS, the E11 file failing on 31329cd and passing after) and
  committed it as `60a36a1`. The derived revision `e11-native-reparse-4` on the real root (150 originals
  byte-identical) then flipped three real F6-04 verifier runs on the OpenCode setups from ok to not ok on
  `scenario_executed`: the item 1(c) judgement walked a compound line as one command, saw `cd`, `mkdir` or a
  variable assignment as its head, never reached the `python3 -m widget.export` inside, and blamed a
  read-only utility that was not there. Sent back inside the fix round (the E11-10 pattern); the builder
  split a line into its simple commands and applied the head rule to each, with the three real command
  shapes as tests (report section 12), and on the control room's request added the missing
  failing-then-passing core test for the item-3 downgrade (the brief's rule; the addendum). Gated again
  (runner 457 OK both, `check` ok both, core 354 both, adapters, examples, E7; the runner E11 file fails on
  60a36a1 and the core E11 file fails on 31329cd's core, both pass after) and committed as `6013f35`, the
  commit under re-check. Derived revision `e11-native-reparse-5` on the real root: every grade equal to
  revision 3 (the three flips gone, nothing else moved), routing identical to revision 4. **Three
  observations carried to the reviewer, not fixes:** (a) the item-3 downgrade reads a retained report's
  wording against a closed list quoted from contract section 5 when the report has no structured tail, the
  one place the repair reads report text rather than a field, and the record names which signal fired;
  (b) the runner's liveness check before a derived measurement compares a recorded child pid against the
  process table without a start-time check, so a reused pid reads as alive (a stale watcher shell from the
  builder's session had taken an E10 trial's recorded pid and made `routing-score` refuse once; the control
  room stopped the shell and re-ran); (c) claude-code's manual-only qualification now reads unqualified on
  the E10 record because no guard was recorded as applied there, which the rerun's per-attempt guard record
  answers. **Carried to Tony unchanged from E11-12:** the three faces of one bench-layout fact (another
  setup's station copy stays readable; the read-boundary preflight reports `separated: false` and is
  accepted as such; the consumer's isolation check is false because a child in its launch environment can
  read a record outside its pair). The rerun set is unchanged. Astra's re-check (`launch.sh recheck`, E11-8
  high) launches on a fresh verify copy at `6013f35` behind the E11-1 wall; then carry under ruling 17.
- **E11-14, Astra's re-check (delivered 2026-09-17 about 8:00 AM, at high, in twenty-five minutes; packet
  `astra-outputs/e11/recheck/`), the carry under ruling 17, and the scope question put to Tony (control
  room, about 8:10 AM).** On the fresh scrubbed copy at `6013f35`: FIXED 3, 4, 7, and all five NEW findings
  of E11-12 (the repeated revision, the failed manual-only qualification, the listing, the compaction
  reader, the forty-character prefix); no new BLOCKER; open 1, 2, 5, 6 (BLOCKER) and NEW 9 (MAJOR). Her
  own suite runs failed on her sandbox's limits as every round; she read the control room's gates-H tails.
  What remains open, sorted by what it touches. (i) Bench layout, carried to Tony since E11-12: 2, read
  access shared across trials and accepted as unseparated; 5, another setup's station copy readable; 6,
  the consumer's isolation false. (ii) Derived grading, re-derivable on the retained records with a later
  `--revision`, so carried into the rerun's reading without loss: 1, an interpreter told only to print the
  source (`python3 -c "print(open(...).read())"`, `sh -c 'cat ...'`) still satisfies `scenario_executed`; 6,
  the consumer grader compares `artifact` where the schema says `artifact_path`, and the continuation
  comparison accepts swapped done and pending items. (iii) Live behavior or launch control, which the
  rerun's records would carry and no later derivation can undo: NEW 9, the item-3 phrase list treats "no
  service observation" as a stopped execution, so a legitimate prose-only static clearance (X2-01, whose
  first report says it needs no service observation) is downgraded to `not_fixed`; 6, `stage_consumer_pair`
  copies no verifier evidence files, so the twelve live consumer trials would re-inspect pairs missing the
  artifacts their evidence names; 2, `require_preflight` accepts a retained preflight whose allow-rule
  check failed once the unseparated state is accepted (the control room reads the preflight record itself
  before any launch, so this one is operationally controlled either way). Ruling 17's one fix round is
  spent. The control room does not launch the rerun with the (iii) defects in the skill and the runner on
  its own reading, and does not open a second fix round on its own: the choice is Tony's, put to him on
  the board's You card. (A) A narrow second fix of the three (iii) items only, each with a
  failing-then-passing test, the control room's gates, derived revision 6, and Astra's re-check limited to
  those three; then the rerun. About an hour and a half. (B) Carry everything and launch the rerun now at
  `6013f35`, reading the affected subset (prose-only static clearances; the twelve consumer trials) with the
  limitation named. (C) Something else he names. The control room's pick is (A): two of the three change
  what the rerun records, and the rerun costs hours and OpenRouter money to repeat. Until he rules:
  nothing launches, no campaign root is created, the rerun set stays as confirmed (348 plus twelve
  consumers plus twelve probes), the three local branches wait for "PR".
- **E11-15, Tony's ruling on the E11-14 scope question (2026-09-17 about 8:45 AM): "Short fix first."** A narrow
  second fix of the three live-record items only, outside ruling 17's count by his word: NEW 9 (the item-3
  phrase list), item 6's consumer pair staging and its `artifact_path` reading and per-item continuation
  comparison, and item 2's launch gate honoring a failed allow-rule check. The same builder (Opus 5 at high)
  on the brief `astra-outputs/e11/briefs/e11-repair-fix2.md`; each change with a test that fails on `6013f35`
  and passes after; the control room's gates; commit; derived revision 6 on the real root; Astra's re-check
  limited to the three; then the rerun on Tony's standing goal line. Everything else open in E11-14 carries
  to the reconvene unchanged.
- **E11-16, the narrow second fix gated, committed and re-derived (2026-09-17 about 10:10 AM).** The builder
  delivered the three E11-15 items as four files on top of `6013f35` (report section 13). Before gating, the
  control room re-drove Astra's own re-check probes against the working tree: X2-01 now reads `fixed`,
  `confirmed`, no refusal; the F5 refused case still downgrades; the consumer pair copies its artifact and
  refuses a changed path; swapped item states fail the per-item continuation comparison; a failed allow-rule
  check makes the launch exit 2. Gate chain I green end to end (`control-room/verify/gates-I.log`): runner
  469 under both interpreters, `check` clean under both, core 359 twice, the three adapters, the examples,
  E7 nine for nine; the runner E11 suite fails on `6013f35` (5 failures, 6 errors) and passes after, the
  core E11 suite fails on the `6013f35` core (1 failure, 4 errors) and passes after. Commit `9368509` on
  `feat/recheck-v2-e11-repair`. Derived revision `e11-native-reparse-6` on the real E10 root: 143 grades and
  four routing files written beside the originals, the 150 originals byte-identical again
  (`rescore-real-root-6.log`, `after-originals-6.sha256`). Revision 6 equals revision 5 on every grade field
  except the derived file's own path, no flip against revision 5 or revision 3, the same two flips against
  the originals as revisions 3 and 5, the routing files identical to revision 5
  (`grade-flips-e11-native-reparse-6.txt`, `routing-rates-e11-native-reparse-6.txt`). That is the expected
  shape: the three items change what a live consumer trial, a live launch and a live prose-only clearance
  would record, not what the E10 records already hold. Next: the verify copy refreshed at `9368509` behind the
  E11-1 wall, Astra's re-check limited to the three (mandate `mandate-recheck2.md`), her verdict filed as
  E11-17, then the rerun on Tony's standing goal line.
