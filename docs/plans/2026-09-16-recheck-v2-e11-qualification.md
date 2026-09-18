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
- **E11-17, Astra's narrow re-check of `9368509` and the control room's send-back (2026-09-17 about 10:30 AM).**
  Astra (GPT-6 at high, `launch.sh recheck2`, mandate `mandate-recheck2.md`, 8 minutes, exit 0; packet
  `astra-outputs/e11/recheck2/` with her probe scripts) on the three E11-15 items: C FIXED (a retained
  failed allow-rule check refuses the launch, exit 2, with the unseparated state accepted; a passed
  preflight on a fresh campaign permits it). A PARTLY, NEW MAJOR: X2-01 stays `fixed` and the F5 refused
  and structured-tail cases still downgrade, but the new negation guard cancels a declaration on any
  negation within four words, so "No output because execution was refused" reads as no block and a later
  prose-only clearance passes as `fixed`; the previous verifier downgraded it. B PARTLY, NEW MAJOR: staging
  carries the evidence, `artifact_path` and content are checked and swapped item states fail, but
  `_artifact_rows` pairs the consumer's references by list position while `_same_evidence` accepts any
  order, so two correct references in the other order fail `evidence_artifacts_recovered` with both files
  unchanged. No new BLOCKER. Her runner E11 suite showed four failures from her sandbox refusing the fake
  producer's uv cache; the control room's chain I ran the same suite green from `/private/tmp`. The
  control room read both findings against the code and confirms them: both sit inside the items E11-15
  ordered fixed and both change what a live trial records (a real refusal graded fixed; a live consumer
  trial failed on evidence order). The control room's call, made on E11-15's intent and flagged to Tony
  rather than put to him: the narrow round is not complete until the three items hold, so the two go back
  to the same builder as a send-back within the round (brief `briefs/e11-repair-fix3.md`: A2 the guard
  negates only the phrase itself, B2 the rows pair by the named artifact; one failing-then-passing test
  each against `9368509`), then the control room's gates, commit, derived revision 7, Astra's re-check on
  the two, then the rerun. About an hour. The rerun stays behind its gate; Tony can rule to launch at
  `9368509` instead at any point, carrying the two with the affected subset named. Nothing else changes.
- **E11-18, the send-back gated, committed and re-derived (2026-09-17 about 11:35 AM).** The builder delivered
  A2 and B2 as four files on top of `9368509` (report section 14). A2's rule, written into the verifier's
  module comment: the guard walks back from the phrase across determiners and copulas only
  (`BLOCK_NEGATION_CARRIERS`, at most four); a negation reached that way negates the phrase; any other word
  between them means the negation belongs to that word and the block stands. B2: `_artifact_rows` pairs each
  producer reference with the consumer reference naming the same `artifact_path`, each spent once; an
  unpaired producer reference leaves `consumer_named` null. The builder re-drove Astra's probes: the
  "No output because execution was refused" case now downgrades; the reversed two-reference case now
  recovers; every other probe unchanged; item C unchanged. Gate chain J green end to end
  (`control-room/verify/gates-J.log`): runner 471 under both interpreters, `check` clean under both, core
  364 twice, the three adapters, the examples, E7 nine for nine; the runner E11 suite fails on `9368509`
  (2 failures) and passes after, the core E11 suite fails on the `9368509` core (2 failures) and passes
  after. Commit `8b6beda` on `feat/recheck-v2-e11-repair`. Derived revision `e11-native-reparse-7` on the
  real E10 root: 143 grades and four routing files beside the originals, the 150 originals byte-identical
  (`rescore-real-root-7.log`, `after-originals-7.sha256`); revision 7 equals revision 6 on every grade
  field except the derived file's own path, no flip against revisions 6 or 3, routing identical to
  revision 6 (`grade-flips-e11-native-reparse-7.txt`, `routing-rates-e11-native-reparse-7.txt`). Next:
  the verify copy refreshed at `8b6beda` behind the E11-1 wall, Astra's re-check limited to A2 and B2
  (`mandate-recheck3.md`, `launch.sh recheck3`), her verdict filed as E11-19, then the rerun on Tony's
  standing goal line. The 10:34 AM push to Tony offering a launch at `9368509` instead drew no answer; the
  send-back stood.
- **E11-19, Astra's re-check of the send-back: BOTH CLEARED (2026-09-17 about 11:40 AM).** Astra (GPT-6 at
  high, `launch.sh recheck3`, mandate `mandate-recheck3.md`, 5 minutes, exit 0; packet
  `astra-outputs/e11/recheck3/` with her probe scripts) on A2 and B2 against `8b6beda`: A2 FIXED (the guard
  stops at unrelated words: "No output because execution was refused" is a block and downgrades the later
  static clearance; "no execution was refused", "the execution was not blocked" and X2-01 stay fixed,
  confirmed, no refusal; F5 and the structured tail still downgrade). B2 FIXED (reversed references recover
  with both files unchanged; a wrong file, changed content and a missing reference fail; swapped item
  states still fail `continuation_state`). No new BLOCKER, no new MAJOR. Her runner E11 suite again showed
  four failures from her sandbox refusing the fake producer's uv cache, confirmed by her own diagnostic;
  chain J ran the same suite green. That closes the E11-15 narrow round: the three live-record items hold on
  the reviewer's own probes, the runner and the skill at `8b6beda` are what the rerun runs, and everything
  E11-14 carried still carries to the reconvene. The rerun starts now on Tony's standing goal line
  ("finish the build and Astra check, then run the rerun"), the control room staging, planning, installing,
  verifying, probing and preflighting the new root `e11-repair-qualification` before the operator is launched.
- **E11-20, the rerun bench staged; held on the qwen route (2026-09-17 about 11:50 AM).** On the standing goal line
  the control room created `~/.local/share/skills-v2-pilot/e10/e11-repair-qualification` and ran, from
  `/private/tmp` with the repair worktree's runner: `stage` (exit 0, commit `8b6beda`, no links, tree hash
  recorded), `plan --plan astra-kit/plan.json` (exit 0: comparison 96, continuation 8, routing 240,
  manual-only 4, consumer 12, total 360; four setups, the pinned models), `install` (exit 0, twelve homes,
  every `home_leak_scan` empty, the four absent homes `never installed`, the key passed once to the OpenCode
  install script), `verify` (exit 0, twelve rows, identity equal on the eight installed homes, the four
  absent homes failing to find a skill as required), `probe-env` (exit 1: nine of twelve probes ok with no
  banned name the runner passed and none nobody measured; the three `opencode` probes, the qwen setup,
  exited 1 with no environment name because OpenRouter answered HTTP 429 for every call: "[Alibaba]
  qwen/qwen3.8-flash is temporarily rate-limited upstream. Please retry shortly"; the three failed probe
  records stay on disk under `probes/opencode-*/`). A one-token ping of the route from the control room
  answered 429 again. OpenRouter balance read: total 110.00, used 14.96, available 95.04. Under the E10
  outage lesson nothing launches into a failing provider: the control room holds before `preflight`, polls
  the route every two minutes, and on a 200 runs `probe-env --setup opencode --refresh` (new records beside
  the failed ones, E10-43), then `preflight`, then the operator. Every control-room record of these steps is
  under `astra-kit/s/rerun-cr/` and is copied to the packet at the launch. If the route stays down past
  about fifty minutes the hold goes to Tony with the options (wait longer; run the other three lanes first;
  something he names), not decided here.
- **E11-21, the qwen lane held for three hours; the call put to Tony (2026-09-17 about 2:35 PM).** Since the E11-20
  hold the control room pinged the route (one-token completion) every one to two minutes: HTTP 429 on all
  but eight of about a hundred pings between 11:48 AM and 2:30 PM; the windows (12:00, 12:30, 1:18, 1:46,
  1:57, 2:08, 2:28) each closed within the minute. `probe-env --setup opencode --home <h> --refresh` ran
  inside every caught window from 1:46 PM on: every probe session got 429 from the same provider within
  its 80 seconds (six failed records each under `probes/opencode-absent/` and `probes/opencode-routing/`,
  all retained). The `available` home holds its one ok probe from the 12:00 window. OpenRouter lists one
  provider for `qwen/qwen3.8-flash` (Alibaba) and reports its uptime at 100 for the last 30 minutes, a
  metric that does not count rate limiting. Two control-room loops before the Python one wasted the 12:30
  and 1:18 windows on a zsh word-splitting defect of the control room's own (an unquoted variable handed
  the runner one malformed `--home` value, which it correctly refused); recorded here as the control room's
  slip, not the runner's. The other three setups have every probe current. `campaign start` needs one
  current successful probe per home, so the campaign cannot start with this lane as planned. The choice is
  Tony's, put to him at 12:33 PM in chat, on the board's You card at 1:31 PM, by the Board window's push,
  and again now by a picker: keep waiting; add his own Qwen key on OpenRouter (the provider's own advice);
  drop or swap the lane (a plan change, his ruling). Nothing launched; no record changed.
- **E11-22, Tony's ruling on the qwen lane (2026-09-17 about 3:50 PM; the picker was put at 2:35 PM and his answer arrived about an hour later): "Add my own Qwen key."** Tony adds an Alibaba
  Model Studio key under OpenRouter's integrations so the lane runs on his own rate limit instead of the
  shared one, the provider's own advice in its 429 text. The plan is unchanged: the same four setups, the
  same pinned model for the lane. The control room keeps pinging the route every minute; on a window that
  holds for two consecutive pings it re-probes the two remaining qwen homes (new records beside the failed
  ones), then `preflight` with the allow rules read by hand, the OpenRouter balance, `s/out` moved aside,
  and the operator (Astra at high) via `operate.sh`. No record changes; nothing else is decided here.
- **E11-23, the rerun launched (2026-09-17 about 4:37 PM).** Tony's first key, created in Model Studio's US (Virginia)
  region, drew HTTP 401 from Alibaba through OpenRouter ("Incorrect API key provided"); Alibaba's own docs
  scope keys to their region and OpenRouter's international entry uses the Singapore endpoint. His second
  key, created in the Singapore region and placed as the prioritized BYOK key, answered three consecutive
  one-token pings at 4:35 PM with Alibaba as the provider. The control room then ran, from `/private/tmp`:
  `probe-env --setup opencode --home absent --refresh` and the same for `routing` (both ok, 22 names, no
  banned name the runner passed, none nobody measured; every home of the plan now holds one current
  successful probe, twelve in all, beside the retained failed ones); `preflight` (exit 1: `separated`
  false on all four setups, the bench-layout fact E11-14 carries to the reconvene; `allow_rules.ok` true,
  `homes_written_for_another_campaign` empty, the very defect item 2 found in E10 not present); `preflight
  --accept-unseparated` (exit 0; the record says the acceptance covers the read-boundary state and nothing
  else); the OpenRouter balance (total 110.00, used 14.98, available 95.02); `s/out` moved to
  `s/out-attempt1`; `operate.sh <root> start` at 4:37 PM, Astra (GPT-6) at high operating under
  `mandate-operate.md` with `-s danger-full-access` and the E10-7 environment, the key never in her
  environment. The control room's records of every bench step are in the packet under
  `astra-outputs/e11/control-room/rerun/`. From here the operator's log and report are the record; the
  control room watches `operate.sh status`, touches no trial, and recounts from the raw records at the end.
- **E11-24, the first operator stopped on the mandate's wording; the mandate corrected; relaunched (2026-09-17 about 4:45 PM).**
  Astra's first operator run (launched 4:37 PM, exit 0 at 4:39 PM, packet
  `astra-outputs/e11/rerun/operate-attempt1/`) stopped at step 1 before `campaign start`: the mandate said a
  probe-env record whose top-level `ok` is false is a stop, and ten retained aggregate records
  (`records/probe-env.json` through `probe-env-9.json`, the rate-limited rounds of E11-20 and E11-21) carry
  `ok: false`. Her stop note states that the two later records are `ok: true`, names the current successful
  probes of 4:36 PM, and says the stop is about the mandate as written, not a failing gate; she launched
  nothing, wrote only under `operator/`, and no record changed. The control room's reading: the runner's own
  gate is the authority and it reads the current probe per setup and home (README `probe-env`; `campaign
  start` refuses without one current successful record each), and earlier rounds are retained beside it by
  design (E10-43, E10-53(5)); the mandate's sentence predated a bench that had ever kept failed rounds, so
  it was out of step with the runner, the same class as the two E10 operator stops (E10-73). The control
  room reworded step 1 of `mandate-operate.md` to read the current probe as the runner does, to treat older
  rounds and older aggregates as history, and to add a false `allow_rules.ok` to the stop list; nothing else
  in the mandate changed. Attempt 1's outputs stay on record. `s/out` moved to `s/out-operate-attempt1`;
  `operate.sh <root> start` again. Decided by the control room as kit maintenance inside the standing goal
  line and flagged to Tony.
- **E11-25, the campaign stopped by the control room at 4:55 PM: the codex lane cannot write its run directory (a repair regression).**
  Attempt 2's campaign ran fourteen minutes. Every codex trial ended `no_result` in about 150 seconds with the
  skill's own STOPPED message: the Codex sandbox refused the first write into the run directory ("patch
  rejected: writing outside of the project; rejected by user approval settings", `harness/stderr.log`).
  Diagnosis from the records, nothing changed: E10's codex sessions wrote the same sibling `run/` leaf
  under the same launch argv, the same `workspace-write` policy with the child home as the only writable
  root, the same git root (the workspace) and the same CLI 0.154.0; the one difference is `TMPDIR`. Every
  E10 launch received `TMPDIR=<campaign>/tmp`, which contains the fixture's `run/` leaf, and Codex treats
  `TMPDIR` as writable (`exclude_tmpdir_env_var: false` in both sessions' turn context); the E11-7 item 2
  fix (`trial_scratch`: one private scratch per trial-attempt handed to the launch as `TMPDIR`, so no session
  can list another's) moved `TMPDIR` to `<opaque tree>/scratch`, a sibling of `fixture/<12 hex>/run`, so
  the run directory is now outside every writable root of a Codex session. Claude Code and OpenCode reach
  it by their own routes (the `--add-dir` and the `external_directory` allow rule are written for the
  campaign scratch root) and complete. The fix round's live proofs never launched a Codex comparison trial
  after that change, so the regression reached the rerun. Ledger at the stop (`trials.jsonl`): claude-code
  3 complete; opencode 1 complete; opencode-deepseek 2 complete and 4 `no_result` (its absent-condition
  replies end within 25 seconds with no result, to be read separately); codex 3 `no_result`; the four
  trials in flight at the stop recorded `launch_failed`, one per lane. `campaign stop` terminated four trial
  processes and left the key closed; every record stays. The operator's session was left to end its turn
  on its own. The choice is Tony's, put to him by picker: repair the runner so a Codex session can write the
  fixture's run leaf (the control room's reading: hand the launch the opaque case directory, or place the
  scratch above the fixture, with a live Codex proof this time), gate, a fresh root and a full restart; or
  something he names. Charges so far this rerun: OpenRouter under a dollar (read at the reconvene from the
  records); the Claude lane is on his plan and is not reported (E11-5).
- **E11-26, Tony's ruling on the stopped rerun (2026-09-17 about 4:58 PM): "Fix and restart."** The same builder
  (Opus 5 at high) on the brief `astra-outputs/e11/briefs/e11-repair-fix4.md`: a Codex session must be able
  to write the fixture's run leaf without re-sharing the campaign scratch (the control room's reading: the
  opaque case directory as a second `--add-dir` through the runner's launch call), a runner-level guard that
  records per trial whether the run directory lies inside a root the setup's session may write and refuses
  the launch otherwise, one failing-then-passing test, and a live proof with real Codex comparison trials
  under a new proof root, the step the fix round skipped; the four opencode-deepseek absent `no_result`
  records read and explained, not fixed. Then the control room's gates, commit, Astra's narrow re-check on
  the fix, a fresh campaign root and the full restart of 360 trials. The stopped root
  `e11-repair-qualification` stays as a record.
- **E11-27, fix 4 delivered, gated and committed (2026-09-17 about 7:05 PM, control room).** The builder's
  section 15 (about 6:25 PM): the cause verified from the stopped root's own records before any change
  (`harness/stderr.log` "patch rejected: writing outside of the project"; the rollout's `sandbox_policy`
  `writable_roots` holding only the child home, `exclude_tmpdir_env_var` false, cwd the workspace; the run
  leaf a sibling of the workspace, outside cwd, `--add-dir` and `TMPDIR` at once). The change, commit
  `ff54644` on the repair branch: `setups/codex/launch.sh` and `setups/claude-code/launch.sh` take
  `--writable <dir>` and pass each as `--add-dir`; the runner names the opaque case directory (the parent
  of the run leaf, holding exactly `run` and `workspace`) for comparison trials, the continuation resume and
  the consumer path; a per-harness `writable_roots` and `require_writable_run_dir` refuse a launch whose run
  directory lies inside no root (exit 2, a record per trial under `records/writable-roots/`); OpenCode
  unchanged, its allow rule read by the guard; `ensure_dir` made race-safe after the guard exposed two lanes
  colliding on one new record directory. `Fix4WritableRunLeaf`, 8 tests: FAILED (failures=2, errors=5) on
  `8b6beda`, OK after. Live proof on the new root `e11-repair-proof-2026-09-17`: codex 2 of 2 complete with
  the validator `ok`, claude-code 2 of 2, opencode-deepseek 2 `no_result`; OpenRouter charge $0.0244. The
  deepseek `no_result` read, not fixed (the brief's scope): the model ends its turn with no assistant text
  part after OpenCode refuses its read of a skill copy outside its home; beside it a bench fault, the
  runner's `harness_reply` takes the last `text` part with no role filter, so `reply.md` is the request text
  byte for byte; carried to the reconvene. Control room gates K on `ff54644` from outside the worktree
  (`control-room/verify/gates-K.log`): runner 479 OK on both runtimes, `check` ok on both, core 364 OK on
  both jsonschema pins, three adapters OK, validate-examples clean, E7 check runner 9 of 9, runner E11 suite
  121 before FAILED (2+5) and after OK, core E11 suite 36 OK both. Derived revision `e11-native-reparse-8` on
  the E10 root: 143 graded, every record equal to revision 7 on every field but `grade_path`, no flips,
  150 originals byte-identical. Its routing re-score is held: the runner's live-harness check reads a
  day-old `child.pid` from the finished E10 campaign and finds that pid number alive again, taken at 7:00 PM
  by an unrelated process of another session, so `routing-score` refuses ("harness processes are still
  alive"); the check tests pid existence only, not the process's start against the record's. A retry waits
  on that pid; the routing files for revision 8 follow when it frees. That liveness reading is a bench
  finding for the reconvene, not fixed in this round. Next: Astra's narrow re-check of fix 4 (mandate
  `astra-kit/mandate-recheck4.md`, mode `recheck4`; the copy carries the fix-4 proof root and the stopped
  root's records), then the fresh root `e11-repair-qualification-2` and the restart.
- **E11-28, Astra's recheck4 on fix 4: PARTLY, sent back inside the round (2026-09-17 about 7:30 PM, control
  room, decided on Tony's behalf as E11-17 was, flagged).** Verdict `astra-outputs/e11/recheck4/recheck4.md`
  (12 minutes at high, exit 0): the cause confirmed from the stopped root's own rollout (the run leaf inside
  none of cwd, the child home, the per-trial scratch or `/private/tmp`); the comparison repair proven on the
  fix-4 proof root (both Codex trials `complete`, the available one's validator `ok`, six writable-roots
  records true); her own re-drive of the eight new tests OK and of the guard by hand (unnamed refused with
  exit 2, named accepted). Still open, D as MAJOR: of the runner's four launch sites only the comparison
  and the consumer call the guard and pass the root; the first continuation launch and the Codex
  compaction resume pass no root and call no guard, the handoff resume passes the root without the guard,
  so the restart's eight continuation trials would fail on Codex exactly as the comparisons did. NEW MAJOR
  D-G: `Setup.writable_roots` counts a runner-named root for every harness, and OpenCode's launcher never
  forwards it, so with no allow rule the guard records writable instead of refusing. NEW MINOR D-T: the
  isolation test asserts `["run", "workspace"]` against a layout it built; a real case directory also holds
  `input.json` and `manifest.json`, a consumer's `producer/`. Her design answer, carried: naming the case
  directory makes the case's `manifest.json` and a consumer's local `producer/` copies writable too, no
  other trial's tree, no shorter opaque segment. The deepseek reply-capture read CONFIRMED by hash (the
  first record's role is `user`; `harness_reply` has no role filter); no restart blocker, carried. The
  control room read all three against the code and confirms them (guard calls at runner.py 4665 and 11091
  only; 8418 root without guard; 8489 and 8738 neither; base reader 1468-1485 appends `extra` for every
  harness; test 1730-1735). Brief `astra-outputs/e11/briefs/e11-repair-fix5.md` to the same builder: every
  launch site names the root and calls the guard through one helper, per-setup `forwards_writable` so the
  record counts only roots the session receives, a real-fixture isolation test, tests fail-then-pass on
  `ff54644`, a live Codex and Claude Code continuation proof on a new root
  `e11-repair-proof-2026-09-17-b`. The restart waits on that fix, the control room's gates and Astra's
  recheck5.
- **E11-29, fix 5 delivered, gated and committed (2026-09-17 about 10:25 PM, control room).** The builder's
  section 16 (about 9:45 PM): the three findings each confirmed at the lines before any change. The change,
  commit `aa5a244` on the repair branch: one helper, `guarded_launch_roots`, names the run leaf's parent,
  calls `require_writable_run_dir` and returns the roots, and every launch site goes through it (the
  comparison trial, the consumer, the first continuation launch through `_launch_argv`, which now forwards
  `--writable`, the handoff resume, and both hand-built compaction resumes, `--add-dir <case dir>` before
  the Codex `resume` subcommand); one record per launch under `records/writable-roots/`, named per half; a
  fake launcher records `enforced: false` and proceeds, every real launch is enforced (the builder's
  decision, to be judged by Astra). D-G: `forwards_writable` per setup (True on Codex and Claude Code,
  False on OpenCode and the base), the base reader counting a runner-named root only when the launcher
  forwards it and recording `roots_named_but_not_forwarded`; an OpenCode home with no `opencode.json` reads
  `bounded: false` and is refused nothing (uninstalled, the install and verify gates own it), a config that
  exists and grants nothing is judged and refused (the builder's second decision, to be judged). D-T: the
  synthetic isolation test deleted, two tests staging a real fixture and a real consumer pair through the
  runner's own staging in its place. `Fix5EveryLaunchNamesTheRoot`, 10 tests: FAILED (failures=3, errors=5)
  on `ff54644`, OK after; the two real-fixture tests pass on `ff54644` too, correctly, D-T being a defect in
  a test. Live proof on the new root `e11-repair-proof-2026-09-17-b`, continuation only (the planner refuses
  an empty `cases` list, so `F1-01-fixed-clean` is named and nothing ran from it; `campaign start` does not
  run continuation trials, so each was run with `runner.py continuation`): the four trials on
  `F3-02-mixed-two-items` (codex and claude-code, handoff and compaction) all `complete`, both Codex resumes
  carrying the case directory in `sandbox_policy.writable_roots`, the resumed halves writing `result.json`,
  `receipt.json`, `receipt.log` and `chat.md` into the run leaf with `validate_exit 0`, the at-cut and
  before-resume fingerprints identical, eight writable-roots records all true, wall 2000 s, OpenRouter
  charge $0.00 (no OpenCode lane). Control room gates L on `aa5a244` from outside the worktree
  (`control-room/verify/gates-L.log`): runner 488 OK on both runtimes, `check` ok on both, core 364 OK on
  both jsonschema pins, three adapters OK, validate-examples clean, E7 check runner 9 of 9, runner E11 suite
  130 before FAILED (3+5) and after OK, core E11 suite 36 OK both. Derived revision `e11-native-reparse-9`
  on the E10 root: 143 graded, every record equal to revision 8 on every field but `grade_path`, no flips,
  150 originals byte-identical; its routing re-score ran without the liveness refusal this time (the reused
  pid had freed at 8:16 PM, when revision 8's own routing files were also written and filed), all four
  setups' records equal to revision 8. Next: Astra's recheck5 (mandate `astra-kit/mandate-recheck5.md`,
  mode `recheck5`, narrowed to D, D-G, D-T and the continuation proof; the copy carries the fix-5 proof root
  and her recheck4 probe scripts), then, if cleared, the fresh root `e11-repair-qualification-2` and the
  restart.
- **E11-30, Astra's recheck5 on fix 5: D still PARTLY, sent back inside the round (2026-09-17 about
  10:45 PM, control room, decided on Tony's behalf as E11-17 and E11-28 were, flagged).** Verdict
  `astra-outputs/e11/recheck5/recheck5.md` (9 minutes at high, exit 0). D-G FIXED: OpenCode's unforwarded
  root is recorded under `roots_named_but_not_forwarded`, contributes no writability, and an existing
  config with no allow rule is refused (her `opencode-guard.py` now reads REFUSED, exit 2). D-T FIXED: the
  two replacement tests use the runner's own staging and check the real listings. D PARTLY: all five
  launch sites go through the helper and pass the case root where the harness takes it (her `paths.py`
  reads `guard_calls=1` at every site, the persisted records `enforced: true`), and the continuation
  proof stands (four trials `complete`, validators ok, both Codex resumes carrying the case directory,
  eight records true, the at-cut and before-resume fingerprints equal), but the two decisions the builder
  made without the brief naming them each let a real launch proceed with writability unestablished. NEW
  MAJOR D-F (`runner.py:8758`): the compaction resume's `enforced` is keyed to the first half's
  `fake_launcher` flag while the resume argv names the real binary; her probe reaches the process
  boundary with `enforced: false` and a real `opencode run --session ...` argv. NEW MAJOR D-U
  (`runner.py:2676`, `10458`): a home with no `opencode.json` reads `bounded: false` and the guard raises
  only on a bounded record, so a real launch proceeds with `run_dir_is_writable: false`; she drove
  `setups/opencode/launch.sh` with a stand-in binary and an empty auth file and it never requires
  `opencode.json`, so the install and verify gates do not close that path. NEW MINOR P: section 16's
  sentence that `campaign start` does not run continuation trials is wrong (`campaign_queue` includes
  `continuation_order`, `_campaign_loop` dispatches to `do_continuation`); running the four individually
  was a valid method, the explanation was not. She also notes the fix-5 proof records carry no `enforced`
  field. The control room confirmed all three against the code (the `enforced=not
  getattr(args, "fake_launcher", None)` at the compaction resume; `bounded: false` returned before any
  root is read and the raise guarded by `record.get("bounded", True)`; `campaign_queue` at 9079; the
  eight proof records written about 8:00 PM, before the field existed in the committed tree). Brief
  `astra-outputs/e11/briefs/e11-repair-fix6.md` to the same builder: `enforced` follows the executable
  the launch itself selects at every site through one predicate; a real launch is refused whenever
  writability cannot be established, the fake exception the only pass-through; the P correction as a
  dated note in section 17; tests fail-then-pass on `aa5a244`; one live Codex compaction continuation on
  a new root `e11-repair-proof-2026-09-17-c` showing `enforced: true` on both halves' records, and the
  config-less OpenCode refusal driven at the process boundary with no model. The restart waits on that
  fix, the control room's gates and Astra's recheck6.
- **E11-31, fix 6 delivered, gated and committed (2026-09-18 about 12:15 AM, control room).** The builder's
  section 17 (about 11:30 PM): both findings confirmed at the lines before any change. The change, commit
  `485e92a` on the repair branch: one predicate, `launch_is_fake(setup, launcher)` (False for None and for
  the setup's own `launch.sh`, True for any other executable), consulted by `guarded_launch_roots`, which now
  takes `launcher=` and computes enforcement itself, so no site decides for itself; the compaction resume
  passes None because it always builds its argv from the harness's own binary. The refusal is now
  `if enforced and not run_dir_is_writable`, `bounded: false` and `why_unbounded` kept on the record and
  the message naming the case; the fake-launcher pass-through is the only exception and only when the
  launch itself is fake. P corrected as a dated note in section 17, section 16 left as written. A third
  file, `tests/test_e10_62.py`: its OpenCode resume helper drove `_compaction_resume` against a home with
  no `opencode.json`, a launch no campaign can make now, so it writes the `external_directory` rule a real
  installed home has and removes it after; the control room read it and confirms the suites run under the
  test pilot root (`RECHECK_PILOT_ROOT` set by `testlib`), never the real homes. No fabricated OpenCode home
  anywhere. `Fix6EnforcementFollowsTheLaunch`, 6 tests: FAILED (failures=3, errors=1) on `aa5a244`, OK
  after; (b) and (d), the pass-through cases, pass on both, correctly. Her `decisions.py` re-run: decision
  (a) REFUSED with `enforced: true` under either value of the first half's flag, no argv reaching the
  process boundary; decision (b) real launch REFUSED, CLI exit 2, `enforced: true`, `bounded: false`, the
  record written; the same home under the fake launcher proceeds with `enforced: false`. Live proof on the
  new root `e11-repair-proof-2026-09-17-c`, one trial through `runner.py continuation`
  (`cont-codex-F3-02-mixed-two-items-compaction-r1`): `complete`, `validate_exit 0`, both halves' records
  `enforced: true` and `run_dir_is_writable: true`, the resume's rollout carrying the case directory in all
  12 turn contexts, the run leaf gaining `result.json`, `receipt.json`, `receipt.log` and `chat.md` across
  the resume, wall 643 s, OpenRouter charge $0.00. Control room gates M on `485e92a` from outside the
  worktree (`control-room/verify/gates-M.log`): runner 494 OK on both runtimes, `check` ok on both, core 364
  OK on both jsonschema pins, three adapters OK, validate-examples clean, E7 check runner 9 of 9, runner E11
  suite 136 before FAILED (3+1) and after OK, core E11 suite 36 OK both. Derived revision
  `e11-native-reparse-10` on the E10 root: 143 graded, every record equal to revision 9 on every field but
  `grade_path`, no flips, routing equal to revision 9 on all four setups, 150 originals byte-identical.
  Next: Astra's recheck6 (mandate `astra-kit/mandate-recheck6.md`, mode `recheck6`, narrowed to D-F, D-U, P
  and the one-trial proof; the copy carries the fix-6 proof root and her recheck5 probe scripts), then, if
  D clears, the fresh root `e11-repair-qualification-2` and the restart.
- **E11-32, Astra's recheck6 on fix 6: D CLEARED (2026-09-18 about 12:30 AM, control room).** Verdict
  `astra-outputs/e11/recheck6/recheck6.md` (7 minutes at high, exit 0): D-F FIXED (each site's enforcement
  follows the launcher selected for that launch; her `decisions.py` re-run reads REFUSED with `enforced: true`
  under either value of the first half's flag, and no argv reaches the process boundary; her new
  `cli-proof.py` shows a fake handoff continuation through the CLI recording `enforced: false` on both halves
  with the reason, the resume argv selecting the fake); D-U FIXED (a real launch with unestablished
  writability refused with exit 2 even when `bounded: false`, the record written with `why_unbounded` naming
  the missing `opencode.json`; a fake launch on the same home proceeds with `enforced: false`; the CLI exit
  confirmed by staging the real OpenCode launch script, no model); P FIXED (section 17's dated correction
  accurate; `campaign_queue` on the proof plan reads 2 comparison and 4 continuation rows). D as a whole
  CLEARED on the closed checklist. The fix-6 proof read from its own records: one trial `complete`,
  `validate_exit 0`, both halves' records `enforced: true` and `run_dir_is_writable: true`, the case
  directory present in all 12 resumed turn contexts. Her fresh-copy re-drive of the fix-4, fix-5 and fix-6
  classes: 23 tests OK; the two test-file tails as before (the four consumer tests her sandbox cannot run,
  gates-M.log read for them; core 36 OK). No new BLOCKER. NEW MINOR P2, report only: section 17 overstates
  the `test_e10_62.py` bench (on a clean test root its helper also creates the missing home directories
  under the isolated test pilot root, and the older resume test selects the real binary at a captured
  boundary); the runtime repair stands, the statement is to be corrected; carried to the reconvene with the
  other carried items. Two notes of hers for the record: the literal `runner.py continuation` command of
  the proof is not witnessed by the root's records (the runner log shows the continuation handler and the
  cut), and the builder's config-less refusal output lives in section 17 rather than as a probe log under
  the proof root; her own re-drives reproduce it. The restart follows on this commit, `485e92a`, on the
  fresh root `e11-repair-qualification-2` under Tony's standing goal of 2026-09-17 ("finish the build and
  Astra check, then run the rerun"); the two in-round send-backs, E11-28 and E11-30, were decided on his
  behalf and are flagged for the reconvene.
- **E11-33, the rerun (attempt 2) finished; two runner defects surfaced from its records; fix 7 briefed
  (2026-09-18 about 6:30 AM, control room).** The operator exited at 6:14 AM (exit 0, 247 events, 5 hours
  51 minutes from launch); her report is `astra-outputs/e11/rerun-2/operator/report.md`, the control room's
  own recount, status and scan beside it under `rerun-2/control-room/`. Counts (her recount and
  `recount.py` agree): planned 360, recorded 348, attempts 370, complete 326, no result 39, timed out 4,
  launch failed 1, reruns 22, unrun 12. By setup: claude-code 87 of 87 complete; codex 87 of 87 complete
  plus one `launch_failed` ("Selected model is at capacity") retried to complete; opencode 82 complete,
  4 no result, 4 timed out; opencode-deepseek 70 complete, 35 no result (comparison absent 22 of 23
  attempts, available 13 of 19). Zero writable-root refusals; every `records/writable-roots/` record
  `run_dir_is_writable: true`. `campaign status` complete, no live process; scan ok, 0 hits over 15,380
  files. Routing rev1, held-out activation / false-trigger: claude-code 0.667 / 0, codex 1.0 / 0,
  opencode 1.0 / 0, opencode-deepseek 1.0 / 0. Manual-only: codex UNQUALIFIED for the catalog requirement
  (the station was selected from a worded request in its one completed session, the runner's read barrier
  applied over 24 station paths); the other three qualified. OpenRouter: the ledger's harness-computed sum
  for the two OpenCode lanes is 4.63 (probes 0.008 more); the key's own counters read at 6:25 AM are
  unchanged from the launch reading (used 14.98), so no charge is confirmed landed yet; to be re-read at
  the reconvene. Defects: (Q) `campaign_queue` (runner.py 9076) never schedules `consumer_order`, so the
  twelve consumer trials, the measurement of the plan's "all three consume each other's records", were
  never launched (`campaign status` reads planned 348 for a 360 plan; the E10 plan carried none, so the
  gap never showed); (G) `grade --all` aborted at 75 of 104 comparison and continuation attempts on
  `native_actions` (runner.py 6158) reading a pretty-printed `launch-*.record-call-flags.json` sidecar in
  trial `opencode-F5-01-outbound-required-available-r2` as JSONL, leaving the 24 opencode-deepseek and 5
  opencode grades unwritten; routing-score completed on its own. Partial grades as written: available
  claude-code 7 of 12 ok, codex 8 of 12, opencode 8 of 9; absent 0 ok in the three graded setups;
  continuation codex 1 of 2, opencode 1 of 2, opencode-deepseek 1 of 2, claude-code 0 of 2 (both on
  `no_scope_violations`). Fix 7 briefed to the same builder (`briefs/e11-repair-fix7.md`): the queue
  schedules the consumer rows after routing, the reader selects the verifier capture exactly and every
  JSONL reader skips non-object rows, the grader continues past a per-attempt exception and lists it;
  tests failing on 485e92a and passing after, two read-only proofs, nothing written under any root; after
  Astra's re-check the control room rescores the real root to a derived revision. Decided on Tony's behalf
  and flagged: briefing fix 7 under his standing goal (the build is not finished while its grader aborts
  on real records). Put to him in chat: whether the twelve consumer trials run on this root after fix 7
  (added attempts, the 348 untouched), on a fresh root, or are carried unrun into the reading. Carried
  unchanged: the E11-28 and E11-30 send-backs, deepseek reply capture, pid-reuse liveness, the OpenCode
  allow rule's breadth, the unseparated bench, the P2 wording, Astra's design note; new: the codex
  manual-only selection and the opencode-deepseek no-result rate.
- **E11-34, Tony's ruling on the twelve unrun consumer trials: same bench (2026-09-18 about 6:45 AM, Tony).**
  After fix 7 is gated and re-checked by Astra, the twelve consumer trials run on the finished rerun root
  `e11-repair-qualification-2` as added attempts; the 348 recorded trials are never rewritten. The
  producer records they read are the root's own comparison records. Sequence: gates, recheck7, the
  regrade of every comparison and continuation attempt to a derived revision, then the twelve consumer
  launches, their grades in the same revision, the inspection board republished, then Astra's independent
  read of the rerun and the reconvene.
- **E11-35, fix 7 delivered, gated and committed; every card regraded (2026-09-18 about 8:20 AM, control
  room).** The builder's section 18: `campaign_queue` appends the consumer rows last (a consumer reads a
  producer's records); `graded_attempts` skips `consumer-` directories (their grade is the consumer grade,
  not a comparison card, and `grade_one` reads a `case` field the consumer handler never writes);
  `capture_files` selects `launch-<call>.json` with no further dot; `jsonl_lines` keeps object rows only;
  `grade --all` records a raising attempt under `grade_errors` (no grade written), grades the rest and
  exits non-zero naming them, re-raising the wall's own `Usage` and `Missing`. The sidecar was written by
  the session under trial (its trace line 78 redirects the adapter helper's printed flags into the file);
  nothing in the repo writes that name. `producer_record_for` ranks (continuation first, trial id,
  attempt) over recorded attempts, reads no clock, so a consumer launched after the campaign's end binds
  the record it would have bound in-queue. Seven tests in `Fix7QueueAndReaders`: E11 file 143 FAILED
  (failures=5, errors=2) on 485e92a, OK after. Control room gates N (`control-room/verify/gates-N.log`):
  runner 501 OK on both runtimes, check ok on both, core 364 OK on both pins, adapters 90/34/96 OK on
  both, E7 checks 9 PASS, core E11 36 OK before and after. Committed `1d84b31` on
  `feat/recheck-v2-e11-repair`. The real root regraded to derived revision `e11-rerun2-fix7-1`
  (`rescore11.sh`): 126 of 126 attempts graded, exit 0, routing-score 4 files, originals byte-identical
  (86 files), key reopened. Revision tallies: available claude-code 7 of 12, codex 8 of 13 attempts,
  opencode 9 of 12, opencode-deepseek 5 of 19 attempts (6 complete); absent 0 ok in every setup;
  continuation 4 of 8 (codex compaction, opencode handoff, opencode-deepseek handoff ok; claude-code both
  on `no_scope_violations`, codex handoff on `match`, both OpenCode compactions on `interop` and
  `model_binding`); no flip against the 79 original grades; routing held-out rates identical to rev1.
  Astra's recheck7 launched on a fresh scrubbed copy at 1d84b31 (`mandate-recheck7.md`, closed checklist
  Q, G, H); the twelve consumer launches follow her clearance per E11-34. The inspection board republished
  (V5) from the revision.
- **E11-36, Astra's recheck7 on fix 7: PARTLY; the twelve consumer trials launched on the finished root;
  fix 8 briefed for after them (2026-09-18 about 8:30 AM, control room).** Verdict
  `astra-outputs/e11/recheck7/recheck7.md` (exit 0, 59 events): H FIXED (a reader exception is recorded,
  later attempts graded, only written grades counted, exit 1 naming the error; she reversed the order so
  the error came first); Q PARTLY (queue, counts and producer selection correct; NEW MAJOR Q-S: the loop
  runs lanes concurrently, so a fast lane's consumer can select before another lane's producer is
  recorded; her event-controlled probe picked a comparison record in-queue and the continuation record
  after the end); G PARTLY (the copied trial reads, the shared JSONL reader keeps objects, but the other
  suffix rules still admit dotted sidecars, `launch-x.trace.json` among them, and `do_report`'s ledger
  reader indexes unfiltered rows). She read the sidecar's authorship from the trial's own trace (lines 78
  and 84 redirect the adapter helper's stdout into the file): the session under trial wrote it. Her
  fresh-copy re-drive of the fix-4 to fix-7 classes: 30 OK; the E11 file's four `Item6Consumer` failures
  are her sandbox's uv cache, as every round. No new BLOCKER. Control room reading against the code:
  Q-S is real for an in-queue campaign and does not bear on this root, where every producer attempt is
  recorded and `producer_record_for` is deterministic (her own finding); G's remaining cases are grading
  readers, not launch behaviour. Decided on Tony's behalf and flagged: (1) the twelve consumer trials
  launched at 8:26 AM on the finished root through the fix-7 runner (`campaign start`, pid 27948, the
  queue's twelve unrun rows, one live per lane; the campaign's staged tree stays 485e92a, the probe gate
  passed against it) rather than waiting for fix 8, because the remaining items do not touch this
  root's consumer run and E11-34 asked for the twelve after the re-check; (2) fix 8 briefed
  (`briefs/e11-repair-fix8.md`: a campaign-wide producer-completion boundary before any consumer row
  runs, with a regression over unequal lane progress; every capture suffix rule exact; `do_report`'s
  ledger through the shared reader) and held until the twelve are recorded, because the builder's
  gates open and close the real answer-key wall and never overlap live trials. On the twelve's end:
  their consumer grades, a second derived revision, E11-37, the board, then Astra's read of the rerun.
- **E11-37, the twelve consumer trials recorded; Astra's read of the rerun launched; fix 8 with the builder
  (2026-09-18 about 9:05 AM, control room).** `campaign start` on the finished root through the fix-7
  runner ran the queue's twelve unrun rows, one live per lane, from 8:26 AM to 8:44 AM; the loop exited
  with `campaign status` reading recorded 360 of 360. Outcomes: 8 complete, 4 `no_result` (the three
  DeepSeek consumers, 68 to 80 seconds each, replying in prose with no result record; and Qwen reading
  DeepSeek's record). One rerun each of the four through `runner.py rerun` (the `consumer` subcommand
  refuses a used trial directory, E9-34; the first attempt at reruns was refused and is on record):
  the three DeepSeek consumers `no_result` again, the Qwen rerun complete. Final: 16 attempts, 9 complete,
  3 `no_result`; consumer grades ok 0 of 12. Every one of the 9 complete attempts fails the same three
  checks: `continuation_state` (expected continuations 1, done 2, phase committed; observed done indexes
  empty), `evidence_artifacts_recovered` (the producer's named artifact lives under its own tmp fixture
  run, `producer_sha256: null`, `in_the_pair: false`) and `unrelated_records_unavailable` (the isolation
  sentinel read by a child in the consumer's launch environment, `separated: false`, the same unseparated
  bench the preflight recorded); two carry one more (`source_identity_matches_the_producer` on
  opencode-deepseek-to-codex, `evidence_references` on opencode-to-codex). Producers bound: every consumer
  took its setup's `cont-…-compaction-r1` record, deterministic. Control room reading, for Astra's read
  and the reconvene, not a fix: two of the three universal failures look like the bench's conditions and
  the pair folder's contents rather than the consumer model, the third needs her read. OpenRouter cost of
  the consumer attempts as recorded: 0.28; wall 3,776 s summed. The key was left closed by the loop and
  reopened by hand; every launch closed it. Astra's independent read of the rerun launched at 9:02 AM at
  effort max (`mandate-read2.md`, copy2 at 1d84b31: 116 trial directories, 126 revision grades, 16
  consumer grades, scrubbed, rescan 0 hits, wall checks clean, the repair history beside it); fix 8
  briefed to the builder at 9:02 AM once no trial was live. Decided on Tony's behalf and flagged: the read
  runs on the fix-7 tree with fix 8 in flight (its brief in her copy; the fixes change the apparatus, not
  a record). Next: fix 8 gated and committed, recheck8, then the reconvene with her read.
- **E11-38, Astra's independent read of the rerun landed (2026-09-18 9:42 AM, control room).** `read2` at
  effort max exited 0 after 42 minutes and 182 events; verdict, prompt, stderr, exit, events and her 25
  scratch files filed at the packet's `astra-outputs/e11/read2/` (the 95 MB native-actions dump gzipped;
  no key-shaped strings in the filing). Her verdict lines: claude-code, codex, opencode and
  opencode-deepseek each DOES NOT QUALIFY; the pilot DOES NOT QUALIFY, "correcting the apparatus can
  recover some measurements; it cannot make these records satisfy the whole predicate." Her diagnosis
  classes 110 failed grades: 88 comparison/continuation model failures, 5 apparatus, 1 run condition; the
  16 consumer attempts 9 model (the seven DeepSeek-side no-results plus two Codex consumers that read other
  consumers' grades), 7 apparatus. What she confirms of the control room's reading: all nine complete
  consumer attempts fail the same three checks, two of them apparatus (the artifact staging rejects the
  producer's original live paths while the files were copied; the isolation probe measures the unseparated
  bench from a runner child, not the harness), the third (`continuation_state`) an underspecified shape
  the prompt never gave a schema for. What she corrects: E11-33's "75 of 104" is 79 of 126; E11-35's "4 of
  8" continuation grades is 3 ok (the eight invariant sets pass, a separate number); the saved recount's
  `timed_out: 0` reads a ledger field that does not exist (four routing timeouts on Qwen); DeepSeek's 35
  no-result sessions did work in their traces (no matching outage, so model failure to finish, not a
  proven provider failure); eight of the 28 scope violations are Codex `file:` cwd false detections and one
  more is a here-document, leaving 19 real outside destinations across 12 attempts; the codex manual-only
  UNQUALIFIED is a guard failure (a completed read of the manual-only probe's SKILL.md at rollout line 51
  despite 24 station paths closed). What she flags on fix 7 and fix 8: the "no further dot" capture
  selector discards valid dotted run ids and still selects an unrelated `launch-x.trace.json`; the fix-8
  brief repeats the dotted-id restriction and "needs correcting before implementation is accepted" (fix 8
  is uncommitted, its gates running since 9:30 AM; recheck8 will read this). Her bounded repair proposal,
  six items, all class A: finish fix 8 against the real shapes and replay all 126 + 16 grades into a new
  derived revision (0 live trials); repair the measurements (Codex URI/argv, here-docs, refusal vs error,
  evidence checks from the raw report, reply/result agreement, OpenCode resume capture); repair the
  consumer test (a real caller payload, a published answer schema, path binding through the producer's
  run_dir, grade only after every consumer session ends); a clean independently measured bench with a
  native read-boundary preflight before any rerun (layout changes need Tony's ruling; 360 trials + 12
  probes, planning range 6 to 11 OpenRouter dollars, not a reconciled charge); recording completeness
  (writable-root records by attempt and half, consumer failure interruptions, honest status counts, a
  copy manifest: 26 claude-code run-tree hashes do not reproduce in her copy, to be resolved on the
  original root with her read-only `live-record-check.py`); and the F5 method ambiguity settled before
  another campaign. No model-prompt repair proposed; "additional instructions are not evidence that they
  have been cured." OpenRouter as recorded: attempts 4.91 plus probes 0.01, 4.92; balance read again at
  9:44 AM, used 14.98, unchanged since before the rerun (harness estimates, not reconciled charges). Next:
  the reconvene in chat with both readings; fix 8's gates, then recheck8 with this read beside it.
- **E11-39, Astra's weigh-in on the round-2 shape; fix 8 gated and committed; recheck8 launched (2026-09-18
  about 10:15 AM, control room).** Tony asked, after the reconvene, why the pilot fails and how the skills become
  model-agnostic, then had Astra at high weigh in on the control room's proposed shape (accept this round's
  result; one bounded round 2 with a hard stop; narrow the target to Claude Code and Codex with the OpenCode
  lanes as gaps; move four judgment calls into code: deny outside writes in the adapter, refuse "fixed" on an
  outbound-required item without a service observation, derive the stop reason from execution, generate and
  check the output block). Her weigh-in (`astra-outputs/e11/weigh-in/`, Clerk 7f8409cf): the control room
  overstated "the model-agnostic part worked" (the whole package was tested, the core's contribution never
  isolated; the baseline comparison was not clean; DeepSeek's refusals are a plausible contributor, not
  established for all 35; the words discipline, honesty, stamina supply motives the records cannot show);
  all four code changes are executable support the plan permits, each only if it covers every path including
  shell and subprocess, plus what the proposal missed (reviewed-source accounting, corrected consumer inputs,
  routing witnesses, immutable attempt records, compaction before resumed work); she would not call Claude
  Code or Codex likely to pass on the four alone, and "a couple of days" is unsupported. Decisions: accept
  HOLD; one bounded round CHANGE (freeze the repair list, acceptance checks and rerun set before building; one
  repair round, one independent verification, then stop or carry, per ruling 17; D2's no ceiling is not a
  licence to tune); narrowing CHANGE (an explicit E11 scope amendment naming the hand-off pairs that must
  pass; reported as partial qualification; not itself a D4 matter, production eligibility is). On "are we
  getting anywhere": the diagnosis converges, demonstrated reliability does not yet; stop if the repair round
  cannot produce a clean bench or the clean rerun still fails a mandatory check. Tony's ruling PENDING.
  Meanwhile fix 8's gates-O ran green 9:30 to 10:05 AM (runner 506/506 on both interpreters, check ok on
  both, core 364/364 both jsonschema pins, adapters 90/34/96 both interpreters, validate-examples, E7 checks 9
  of 9, E11 runner suite 148: 4 failures on 1d84b31, 0 after; core E11 36/36 both) and fix 8 is committed on
  `feat/recheck-v2-e11-repair` as `4351654` (the commit message carries the E11-35 label nit and read2's
  dotted-id point); gates filed at `control-room/verify/`. copy8 built by `verify-copy` at 4351654 with
  `COPY_DIR` (repair tree 2,226 files), its six campaign roots scrub-swapped and rescanned 0 hits, no
  routing directory, key-shaped grep clean apart from chance substrings inside Codex's encrypted reasoning
  blobs; her read2 placed at `repair/read2.md` and the recheck8 mandate amended to ask whether read2's
  dotted-id concern is cleared by the exact-stem selector. recheck8 launched at high on copy8 at about
  10:14 AM (outputs `s/out/recheck8.*`). Decided on Tony's behalf and flagged: committing fix 8 locally and
  launching recheck8 while his ruling on round 2 is pending (both inside the standing goal, both reversible,
  no OpenRouter spend). Next: recheck8's verdict; Tony's ruling on the three decisions; then either the
  frozen round-2 package or the E11 close.
- **E11-40, Tony's ruling on the reconvene: "Do what Astra said" (2026-09-18 about 10:25 AM).** His words,
  verbatim, set as the standing goal: "Her recommendation, three sentences: accept this round's failure and
  keep its records. Authorize one frozen repair package covering the four safeguards and her six rig repairs,
  one independent verification, and the rerun only after a native isolation check passes, with any narrower
  target written down explicitly. Stop after that round, report each tool's demonstrated capabilities and
  gaps, and leave production eligibility unchanged." Effect: (1) E11 round 1 closes with the result as read
  by both readers, DOES NOT QUALIFY on claude-code, codex, opencode and opencode-deepseek and for the pilot;
  the rerun root `e11-repair-qualification-2` (360 of 360), the stopped root, the proof roots, every grade
  revision and every review in the packet are the record and are never rewritten. (2) One round 2, bounded
  by ruling 17: a frozen repair package written and committed before any building, one repair round by the
  builder, one independent verification by Astra, a native read-boundary preflight that must pass on all
  four setups before the rerun, the rerun once, then stop or carry. (3) The narrower target is written
  explicitly as an E11 scope amendment in the package (E11-41), reported as partial qualification, never as
  the portability target achieved. (4) Production review eligibility does not change in this round (D4
  untouched). (5) No prompt or skill-text change is in the package; executable support and necessary
  contract wording only. The package is the next entry; nothing is built until it is committed.
- **E11-41, the round-2 package frozen; scope amendment; BF-34 (2026-09-18 about 10:35 AM, control room).**
  The frozen repair package is `docs/plans/2026-09-18-recheck-v2-e11-round2-package.md` on this branch:
  authority and bounds (E11-40, ruling 17, D2, D4, the plan's E11 words); the scope amendment; the repair list
  S1 to S4 (the adapter refuses outside writes with refusal and violation recorded apart; the core refuses
  `fixed` on an outbound-required item without a bound service observation; the stop reason derived from
  execution; the output block generated by the core and checked by the adapter against the native reply) and
  R1 to R6 (Astra's six, with her weigh-in's additions folded in: reviewed-source accounting, the corrected
  consumer input, routing witnesses, immutable attempt records, compaction before resumed work), each with
  coverage, what it must not hide, and an acceptance check that fails before and passes after; the sequence
  (freeze, builder's plan checked against the text, one repair round with the gates-O shape, one verification
  by Astra at high, the native preflight on a fresh root, the rerun once, grade and read, stop); the forbidden
  list; the report shape. **Scope amendment (this entry, under E11-40's "any narrower target written down
  explicitly"):** round 2 qualifies the pilot on claude-code and codex; a pass needs every mandatory check on
  each and the two directed hand-off pairs claude-code to codex and codex to claude-code plus both
  continuation kinds on each; opencode and opencode-deepseek run the full set and qualify only on their own
  merits, otherwise they are reported as capability gaps with their numbers; the result is reported as partial
  qualification on the named setups. Decided on Tony's behalf under his delegation and flagged: the choice of
  those two setups and those two pairs; he can amend either by a recorded ruling. BF-34 executed: the stopped
  root's `operator/stop.md` renamed `stop.attempt-1.md` at 10:12 AM. Next: the builder's plan (step 2 of the
  package), checked here before any code changes; recheck8's verdict feeds R1.
- **E11-42, Astra's recheck8: fix 8 still open on two new MAJORs, folded into round 2's R1 (2026-09-18 about
  10:50 AM, control room).** Her verdict (`astra-outputs/e11/recheck8/`): FIX 8 still open (MAJOR); Q-S PARTLY,
  G-1 FIXED, G-2 PARTLY. G-1: the four suffix controls reject the sidecars and the exact driving names hold. G-2:
  every JSONL row reader keeps object rows only, `do_report` included; read2's dotted-id concern is still open,
  not moot: the input schema accepts dots in `run_id`, the core preserves them in the call id, both adapters
  put them in capture filenames, and `_dotless_stem` returns false on any dot, so `launch-run.v1-verify.json`,
  `run.v1-verify.rollout.jsonl` and `run.v1-verify-2.events.jsonl` are all omitted; the prior Codex branch
  selected the last two, so fix 8 extends OpenCode's omission to Codex (NEW MAJOR G-ID, `runner.py:5939`,
  `5988`). Q-S: consumers wait for producer settlement and stopped lanes release their rows, but with fewer
  worker slots than lanes a waiting consumer holds the only slot and the producer lane never starts; her
  one-lane control times out with the producer never started (NEW MAJOR Q-S-L, `runner.py:9444`, `9566` to
  `9568`; separate producer and consumer phases or release worker capacity while waiting, and test fewer
  slots than lanes). No new BLOCKER. The five fix-8 tests and the 30 fix-4 to fix-7 tests pass on her fresh
  copy; her four `Item6Consumer` failures are her sandbox refusing a uv cache path, confirmed by her
  diagnostic, not the code. Control room reading: both findings are real and both belong to the package's R1
  ("finish fix 8 against the real record shapes"), so under ruling 17 there is no fix 9 round: the builder
  carries Q-S-L and G-ID into the one repair round, and Astra's single verification covers them. Relayed to the
  builder for his plan (section 20). Nothing committed on the repair branch beyond 4351654.
- **E11-43, the builder's plan checked against the package; the one repair round opened in three batches
  (2026-09-18 about 11:05 AM, control room).** Section 20 of the builder's report (filed at the packet's
  `builder/report.md`) maps S1 to S4 and R1 to R6 to files, functions, tests, live proofs, coverage gaps and
  hours, with recheck8's Q-S-L and G-ID folded into R1 (two scheduling phases; a call-id grammar match
  replacing the no-dot rule). Sizes in builder hours: S1 16, S2 11, S3 9, S4 10, R1 12, R2 26, R3 16, R4 14,
  R5 8, R6 5; total 127, about sixteen working days, before the control room's gates, Astra's verification
  and the rerun. The control room read every item against the package text and found no narrowing; the
  carries the builder names are the package's own (OpenCode headless compaction, the two OpenCode resume
  model witnesses if the store rows are gone, no routing threshold to gate on, the core enforcing the shape
  of an observation and not its sufficiency). Answers recorded in `briefs/e11-round2-build.md`: R6 = policy
  refusal; C/F5/A/r1 re-derived with a note; a read-only `consumer --regrade --revision` command inside R1;
  the native preflight launches counted outside the 360 with their OpenRouter cost reported; S1 to S4 on all
  four setups; hash differences in the original root are explained and carried; S2's field on the checklist
  item; Q-S-L by phases. **To Tony:** the builder's coverage item 1: a shell redirection cannot be prevented
  on Claude Code or OpenCode by the harness's own mechanism, only on Codex; closing it needs an OS-level
  sandbox around the launcher, a deployment-layout change. Default until he rules: tool-level denial plus
  post-hoc violation detection, the gap written into the round-2 report. Batches: A (R5 hash check, R6, R2,
  R1 with the replay to `e11-round2-1`), B (S3, S4, S2, S1), C (R5 rest, R3, R4 last with the native
  preflight on a new proof root); the control room gates and commits each batch; Astra's single verification
  follows the third. Decided on Tony's behalf and flagged: starting batch A before he has seen the hour
  count (his E11-40 ruling authorised the round after Astra said "a couple of days" was unsupported).
- **E11-44, Tony's ruling on the S1 write fence: "carry the gap" (2026-09-18 about 11:20 AM).** On Claude
  Code and OpenCode, S1 denies writes at the tool level and detects shell writes outside the roots after the
  fact; it does not prevent them. No OS-level sandbox and no deployment-layout change this round. The gap is
  named in the round-2 report as a limit of the measurement on those two setups. Codex's kernel sandbox
  stays the one real fence. The builder's default in `briefs/e11-round2-build.md` (question 3) is now the
  ruling; nothing else in the package changes.
- **E11-45, batch A delivered and sent back inside the round (2026-09-18 about 11:25 AM, control room).** The
  builder's section 21: R5's hash check on the original round-1 rerun root, read-only, 126 checked and zero
  mismatches, so Astra's 26 claude-code run-tree differences live in the review copy, not the original (the
  copy manifest is batch C's); R6 settled as a policy refusal in the contract and the F5 fixture
  (`outbound_refusal: "policy"`, a `required_service_observation` block that doubles as S2's per-item field;
  the answer key's F5-01 entry already expects `not_fixed` / `verification_blocked` / method `executed` with
  `blocked`, so no key value changes; claude-code F5 r1 re-derived as satisfying method); R2's Codex `file:`
  paths, four call outcomes replacing the two-way error-equals-refusal map, here-documents as data, a role
  filter on the reply collector, and reply-versus-result disposition agreement; R1's two scheduling phases
  (Q-S-L), `_call_named_capture` replacing the no-dot rule (G-ID), a read-only `consumer --regrade
  --revision`, and the replay into revision `e11-round2-1` (126 grades, 4 routing records, 16 consumer
  records; originals byte-identical, the control room's own 86-file hash list confirms). Nineteen new tests,
  17 failing on 4351654 and all passing after; three existing tests amended and named. **Sent back:** the
  control room's per-attempt comparison of `grade.e11-rerun2-fix7-1.json` against `grade.e11-round2-1.json`
  shows 27 decisions flipped ok to not ok, none the other way, every one on `interop` with
  `dispositions_agree: false`: the new reply parser reads the word "fixed" inside "not fixed
  (missed_case)". Section 21 reported "0 of 541 originals changed" and "ok 5, not_ok 121" without the flip
  count the package's R2 acceptance requires ("no grade decision flips without a named reason"). Required
  of the builder: whole-token disposition parsing, a test with both lines, the replay rerun into the same
  revision name, and a per-attempt flip table in section 21. The control room's gates run on the sent-back
  tree was stopped; it reruns on the corrected tree. Nothing committed on the repair branch.
- **E11-46, batch A corrected, gated and committed; batch B opened (2026-09-18 about 12:40 PM, control
  room).** The builder's 21a: `_reply_disposition` parses the reply line by its own separator, cuts the
  parenthesised reason and matches whole tokens longest first, so `not_fixed` can never lose to `fixed`;
  three tests added (22 in the round-2 file); the replay rerun into the same revision name after deleting
  this revision's own derived files (0 overlap with the 541-file originals manifest; the three "no key file"
  errors were contention with a concurrent test suite closing the wall, traced, no runner change); per-attempt
  comparison against `e11-rerun2-fix7-1`: 0 flips either way on 126 attempts and 0 on 16 consumer records;
  record-level differences named, notably `no_scope_violations` false to true on four Codex attempts because
  `file:` paths now resolve (all four still not ok for other reasons). The control room's own comparison:
  0 decision flips, ok 32 / not ok 94 as before, originals 86 of 86 byte-identical. Gates-P on the corrected
  tree (filed at `control-room/verify/`): runner 528 on both interpreters, `check` ok on both, core 364 on
  both jsonschema pins, adapters 90/34/96 on both, examples, E7 checks 9 of 9, E11 suite 2 amended tests
  failing on 4351654 and 148 passing after, round-2 suite 22 failing (11 failures, 9 errors) before and
  passing after, core E11 36/36 both. Committed on `feat/recheck-v2-e11-repair` as `c285358`. Two items the
  builder flagged, carried to batch C: a revision diff produced by `grade_summary` itself rather than by
  hand; `grade --revision` spills numbered records instead of replacing, a contract question. Batch B
  briefed (`briefs/e11-round2-batch-b.md`): S3, S4, S2, S1 with R6's enforcement, live proofs on a new
  proof root only on the control room's word. Wall clock from Tony's ruling to this commit: about 2 h 15 m.
- **E11-47, batch B gated, proved live and committed; batch C opened (2026-09-18 about 3:15 PM, control
  room).** Section 22 and 22a of the builder's report. S3: `derive_reason` from the transport status and the
  retained raw output, never from the typed reason (a test runs identical evidence under two typed reasons and
  gets identical output); the read-only replay of the 12 F5 attempts: 4 same, 3 changed (all typed
  `missing_evidence` while their own retained output showed the service unreachable), 1 unresolved. S4: the
  core half was already satisfied at c285358 and is claimed as nothing; the adapter check reads each harness's
  native final assistant text, role-filtered, and a session with no assistant text fails as "no reply". S2:
  `required_service_observations` declared on the input and bound onto the item at start (section 20 had it on
  the build-doc item, which has no per-item field; deviation named); a `fixed` needs an executed command whose
  retained output names the service; the validator reports itself skipped without an input. S1: three
  outcomes never merged (violated, refused, unanswered) plus session_unfinished; per-harness fence mechanism;
  Claude Code path-scoped `permissions.deny` written per launch; OpenCode `external_directory` and bash deny
  rules; Codex's sandbox asserted; new check `boundary_not_merely_refused`. Replay: 0 decision flips on 126
  against the fix-7 revision, originals byte-identical, no spills; the 12 attempts failing the new boundary
  check all already failed `no_scope_violations`. **Live proofs** (new root `e11-round2-proof-s1`, 20 trials,
  five probes per setup): tool write outside the roots refused on all four; shell write outside the roots
  refused on Claude Code and Codex, **violated on both OpenCode setups** (the E11-44 gap is OpenCode's only;
  Claude Code moves beside Codex); inside write and verifier write completed everywhere; the F5 outbound call
  declined by policy on the shell route on Claude Code and both OpenCode setups, the in-process route falling
  through to the unresolvable host everywhere, and Codex declining neither route because its launch passes
  `network_access=true`. The proof corrected the builder's own tree twice: Claude Code's deny paths needed
  the `//` form (a single slash reads relative to the settings file, so the first run was `violated /
  violated` and the fence did nothing), and `denied_roots` had missed the opencode-deepseek home. OpenRouter
  for the ten OpenCode proof sessions: 0.009; balance unchanged. Decided on Tony's behalf and flagged: Codex's
  sandbox network stays on this round (cutting it would need every fixture and uv retested), so R6's
  enforcement is recorded as partial in the shape of E11-44. Known and queued first in batch C: the three
  proof summary records carry the pre-proof mechanism claims, the Codex outbound probe is labelled refused for
  an unresolvable host (the R2 conflation reappearing in new code), and the OpenCode summary holds only the
  deepseek setup (the qwen summary was overwritten by the second run; the 20 trial records are intact);
  corrected summaries are written beside, never over. Gates-Q filed at `control-room/verify/`: runner 538 on
  both interpreters, core 383 on both pins, adapters 95/39/101, E7 9 of 9, round-2 suites fail-before
  pass-after (runner 32, core 19), output-block tests per adapter. Committed as `652546b`. Batch C briefed
  (`briefs/e11-round2-batch-c.md`).
- **E11-48, round 2 PAUSED mid batch C for Tony's Anthropic account switch (2026-09-18 about 3:40 PM, control
  room).** Tony: "i need to switch anthropic accounts. can we get to a spot to pause so i can do so." The
  builder stopped at a clean point (tree parses; round-2 suite 54 and E11 suite 148 OK), launched nothing, and
  wrote report section 23 (in progress, paused), lines 4101 to 4320: done, in progress, not started in the
  brief's order, findings not yet recorded, git status. The control room made a WIP commit on
  `feat/recheck-v2-e11-repair`, `1d4d985` (3 files, +744/-59), so nothing depends on the dying session; it is
  not the batch-C commit. Done in batch C so far: the three proof-record items (a distinct
  `unresolved-host-error` outcome kept out of `refused`; four corrected per-setup fence summaries generated
  from the trial records beside the untouched originals; the OpenCode overwrite confirmed and fixed; R6's
  wording verbatim); `resume-models` read-only on the round-1 root: `assistant_model_rows: []` for both
  OpenCode setups, the gap carried, nothing reconstructed; R2's evidence check now reads the retained report
  (0 changes across 82 retained attempts); cost unavailable separated from measured zero; `grade_summary`'s
  own revision diff via `grade --against`; `grade --revision` settled as replace-never-number (Astra's earlier
  NEW BLOCKER 1 explicitly reversed, its two tests inverted, not deleted, to be put to her in the
  verification); one defect outside the brief found and fixed, a recycled pid counted as a live harness
  forever and blocked `routing-score` (liveness now compares the process start time with the pid file's
  mtime; unknown counts as alive), no test yet. The replay re-ran clean into `e11-round2-1` (126/16/4, no
  spills, originals 541/541), and the tool's own diff reads 126 paired, 0 flips either way. Not started: R2's
  continuation labels and reviewed-source accounting; six R5 items (`timed_out` could not be reproduced as a
  defect, flagged); all of R3; all of R4 and its live preflight. Loose ends named for the next builder: the
  pid-reuse test; the replace-never-number settlement into the contract; gates not rerun since these changes;
  the answer-key wall is closed (mode 000) and a gate run needs `key-state --reopen`. Governing hand-off for
  the resume: `~/Documents/handoffs/2026-09-18-skills-v2-e11-round2-pause-handoff.md` (paste-back line
  inside; negative test at the bottom). The builder's subagent context ends with the session; a fresh builder
  resumes from the worktree, the brief and section 23.
