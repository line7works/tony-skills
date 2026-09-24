# The build core contract, version 1

What `build-v2` does, what it is allowed to write, when it stops, and what every word in its
result means. This document and the schemas beside it are the interface a caller writes against;
everything under `scripts/build_core/` is internal, and a caller that imports the library instead
of running `scripts/build.py` is outside this interface.

Written for E13 slice 2 of the skills v2 rebuild, against the E13 lane contract
(`docs/plans/2026-09-21-stations-e13.md`, sections 8 and 9, with amendments A1 to A6). The slice 2
fix round (amendment A6) changed the behaviour described in sections 5, 7, 8, 9, 10, 12, 13, 14
and 15 after Astra's review of slice 2; each change names her finding (F1, F2, F11, F12, F14, F15). The last
fix round of that review loop (after her recheck) changed sections 7, 10 and 14 again, for her N1,
N2 and F15's remainder, each named where it applies. Where this
document and that contract differ, the contract is the authority and this document is the defect.

Contents: 1 The job · 2 What is kept from v1 · 3 The phases · 4 The input · 5 The source set ·
6 Scope adherence · 7 The checks · 8 The recorded answer · 9 The card · 10 The records ·
11 Authorized writes · 12 The result · 13 Stops · 14 Report-only · 15 The semantic checks ·
16 Exit codes · 17 What this core never does · 18 Open points · 19 Interface.

## 1. The job

One slice of a build doc, made true, inside the scope the slice draws, with plain reporting when
something did not pass. The same procedure on every harness.

**The executor decides, this core records** (lane contract ruling E13-4). The executor is the
model running `SKILL.md`: it reads the slice, writes the code, runs the checks, and hands back
ONE recorded answer. This core validates inputs, computes the source set and the identities,
talks to the records component, compares, validates the result, and writes exactly two things
into a project: one `card_set` event and one `Status:` line. It never judges code, and what the
executor concluded is recorded with who concluded it.

## 2. What is kept from v1

v1 build's five steps and its rules are the behaviour, unchanged (ruling E13-1):

| v1 step | Where it lives now |
|---|---|
| 1. Contract | the `contract` phase: the slice's requirements, named paths, checks and stated boundaries, written to the run's contract file BEFORE any edit is recorded |
| 2. Preflight | the `preflight` phase: the prior standing from the records (an open BLOCKER refuses the run), the source set, the identity |
| 3. Build | the executor's, outside this core. No subagent ceremony: independence belongs to the inspector |
| 4. Verify | the `checks` of the result: the checks the SLICE names, each with its result and its output |
| 5. Report and stop | the `report` phase: the card, the one event, the `Status:` line, and the result |

The rules that survive as rules of this core, rather than as advice to the executor: every change
traces to a spec line (section 6); no stubs (section 8's refusal); descoping is a deviation,
reported (section 6); report faithfully (sections 7 and 12). The rest — reuse before writing, the
thrash limit, the blast radius, the gap protocol — stay in `SKILL.md`, where the executor reads
them, because they govern judgment this core does not make.

## 3. The phases

```text
check-input <input.json>            validate, create the run
contract    --run-dir D            read the slice, fix the scope
preflight   --run-dir D            the source set, the records, the identity
record-answer --run-dir D --answer FILE     what the executor concluded
report      --run-dir D            compare, decide, record, write the result
identity    <workspace>            the six-field source identity
skill-identity                     what this skill is
```

They run in that order and each one refuses to run out of turn (exit 2). Repeating a command is
safe. A command against a run that already ended reports the recorded outcome and writes nothing,
with ONE exception: `report` always reconciles the card event with the log first, because
completing the document step is not on its own a completed transaction (section 10).

## 4. The input

One validated structure per run (`references/input.schema.json`), supplied as a FILE. Every
caller value is bound as data — an argv item or a file — and nothing is ever pasted into shell
text.

**Path rules**, which a schema cannot state and `build_core/inputs.py` enforces:

- the workspace is an absolute git work tree ROOT with a HEAD commit;
- the run directory is absolute and OUTSIDE the workspace, so a run's own artifacts are never
  part of the source it judges, and a report-only run can write them while writing nothing to the
  workspace;
- the build doc is workspace-relative, normalized, inside the workspace, ends in `.md`, and is not
  under `docs/records/` (the records component's history) or `docs/reviews/` (a mirror).

A failure of the schema or of a path rule is reported the same way, as `{"path", "message"}` in
one list, with exit 4 and nothing written: the run does not exist yet, so there is no result to
write it into, and a corrected input can be supplied and the command rerun.

## 5. The source set

Computed by script from git, never guessed (lane contract section 8):

| List | How |
|---|---|
| `committed` | `git diff --name-only <base>..HEAD` |
| `changed` | `git diff --name-only HEAD` — staged or not, against HEAD |
| `untracked` | `git ls-files --others --exclude-standard` — an ignored file is in no list |

plus `base` (the ref the input named) and `base_commit` (what it resolved to). The base arrives
as a ref; a ref that does not resolve is a STOP (`no_base`), and a workspace that is not a git
work tree root is a STOP (`no_git`). Never a guess, never an empty set standing in for an
unanswerable question.

**One prefix is excluded** from all three lists, and `source_set.excluded` publishes it:
`docs/records/` (CR-3), the records component's own history. The component excludes exactly that
prefix from the identity it computes, so the two agree field for field, and a log this run wrote
never reads as a change to the source it describes.

**One path is SANCTIONED**, and `source_set.sanctioned` publishes it with its reason: the ledger
document this run is executing. It stays IN the three lists, because section 8 is the truth of
what changed and a reader must see that the build doc moved; the scope comparison passes over it,
so it never appears in `out_of_scope`. The loop writes into that document by design — v1 build's
step 5 has the executor write its assumptions, deviations and discoveries there, and `report`
writes the slice's `Status:` line — so without this the scope stop would fire on a change the
loop itself sanctions, on every run after the first. Sanctioning says so out loud; excluding
would have hidden it.

**The set is computed twice, and the second one decides** (Astra's F1). `preflight` computes it
to read the slice's standing; `report` computes it AGAIN, after any requested check reruns and
before the scope decision, against the base COMMIT preflight resolved (so a ref that moved in
between does not move the base). That second set is the one the result publishes, the one the
scope comparison runs over, and the one whose six-field identity the card event carries: an
untracked file added, a tracked file changed or an out-of-scope commit made after preflight is in
it, and is out of scope like any other path. A set or an identity that cannot be computed at
report stops the run (`no_git`, `no_base`, or the records stop the refusal maps to). The decision
is persisted before the card transaction opens, so a settling pass re-delivers that set and that
identity and reruns no check. The ledger document stays in the set, sanctioned.

Git runs read-only, only inside the workspace, under a fixed clean configuration
(`GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, LANG C, TZ UTC), so no user
configuration changes what is reported.

## 6. Scope adherence

The `contract` phase writes the slice's requirements and its named paths — the `Footprint:` list
— to `<run_dir>/contract.json` BEFORE any edit is recorded, so the scope is fixed before the
comparison rather than fitted to it afterwards.

At `report`, every path of the source set that the slice does not name, and that is not
sanctioned (section 5), is listed in `out_of_scope`, each with:

| Field | Meaning |
|---|---|
| `path` | the workspace-relative path |
| `lists` | which of the three lists hold it |
| `reason` | the reason the recorded answer's `edits[]` gives for touching it |
| `reason_given` | whether there is one |
| `named_in_not_in_slice` | the slice states this path as a boundary |

A path is inside the slice's named paths when it equals one, when it sits under one as a
directory, or when a named path ends in `/` and the path starts with it. A shared prefix of a
file name is not a relationship: `src/a.py` is not inside `src/a`. Only literal leading `./`
segments are removed before the comparison; a filename-leading dot is part of the name, so
`.config.env` and `config.env` are two distinct paths (Astra's F14).

**A path outside them with no stated reason is a STOP** (`scope_unexplained`), naming every such
path. A stated reason does not put the path back in scope and this core never judges whether the
reason is a good one — that is the inspector's job. It means the executor said why, in writing,
and the reason travels with the path into the result. Never silently either way.

## 7. The checks

The slice's `Checks:` list is the closed set that gates the card. Each row of `checks` carries
`name`, `command`, `result` (`passed`, `failing`, `not_run`), `exit_code`, `output`, `source`, and
`named_by_slice`.

- A check the slice names that the answer does not report is `not_run` with an empty output.
- A check the answer reports that the slice does not name is carried with `named_by_slice: false`
  so it is visible, and it never gates the card.
- `source` is `recorded` (from the answer) or `rerun` (this core ran the command the SLICE names,
  in the workspace). The default is `recorded`; `rerun_checks` in the input asks for the other.
  A rerun that disagrees with the answer keeps both: `result` is what this core observed and
  `recorded_result` is what the answer claimed.
- A rerun binds the command as an argv list and never runs it through a shell. A command carrying
  shell syntax is NOT rerun.
- **A requested rerun that cannot execute is `not_run`** (Astra's F2): shell syntax, an executable
  that is not there, a timeout. `rerun_refused` keeps the reason and `output` whatever the attempt
  captured; the executor's claim is kept SEPARATELY in `recorded_result` and `recorded_output` and
  never stands in for the observation. The run finishes `checks_not_passed` and the card stays.
- **One command's output is never attributed to another named command** (F2). When the answer's
  `command` for a check does not split into the same arguments as the command the slice names, the
  row is `not_run`, `attribution_refused` says why, and the answer's command, result and output are
  kept in `recorded_command`, `recorded_result` and `recorded_output`. When a rerun was asked for and
  the NAMED command executes (Astra's N2), the row reports that observation (`source: "rerun"`, its
  exit code and output, `passed` or `failing`), and the rejected recorded evidence stays apart in
  those three fields with `attribution_refused` saying so; a rerun that cannot execute stays
  `not_run`. V11 requires `not_run` only when no executed observation of the named command exists.
- **A refused answer runs nothing** (F15): the contents rules of section 8 are applied BEFORE any
  check subprocess is launched, so a refused answer's rows are the recorded ones and
  `rerun_refused` says no command was run.
- **Report-only runs no check command in the live workspace** (F15): a check is an unrestricted
  child process, this core has no read-only execution boundary to put around it, and report-only
  promises nothing reaches the workspace. Every requested rerun is `not_run` with `rerun_refused`
  saying so, and the run finishes `checks_not_passed`.
- **A child that wrote is a write** (F15). Around the reruns of a normal run this core reads the
  six-field identity before and after, AND a digest of every byte under the workspace (`.git`
  excluded, git-ignored files included, Astra's F15 remainder: a check that wrote only an ignored
  cache moved no identity); when either moved, `checks_changed_workspace` is true, `wrote_nothing`
  is false, and what the child changed in the source set is in the set computed at report (an
  ignored file is never in the source set, and is still a write).
- This core never reruns a model.

**A failing or skipped check is reported as failing or skipped, with its output, and the card
does not move.** Such a run is a COMPLETION with a named result (`checks_not_passed`), not a stop:
the tool did its job and is telling you what it found (lane contract amendment A3 item 1).

## 8. The recorded answer

What the executor concluded, handed to `record-answer` as a file
(`references/answer.schema.json`), the way the recheck pilot's `record-call` takes a verifier's
report. Nothing in it is obeyed: a sentence in `notes` claiming a card move, a waiver or a scope
change is text this core reports, never authorization.

An answer that passes the schema can still be REFUSED on its CONTENTS:

| Rule | What it catches |
|---|---|
| R1 | it claims `complete` with card `built` while one of its own `checks[]` says `failing` or `not_run` |
| R2 | `claimed_card` is not one of the six card values the records component publishes |
| R3 | its `case` names a case other than the one the run is for |
| R4 | the same check name appears twice, so "the result of the check" has no single value |
| R5 | one edit path carries two different reasons |
| R6 | a check reported `passed` carries a nonzero exit code (Astra's F2): the answer's own observation contradicts its claim |

R1 reads the answer's OWN list, whether or not the slice names the check: an answer that calls
itself finished while reporting a check of its own as failing contradicts itself, and the
contradiction is the executor's to resolve, not this core's.

**A refused answer is not acted on and not repaired.** The card does not move, no event is
appended, and the result says so plainly: `status` `answer_refused`, `refusal_reason`
`answer_invalid`, `answer.accepted` false, and `answer.refusals` carrying one sentence per rule
broken. It is a **STOP**: a run that may record nothing did not proceed. It still reports the
source set, the out-of-scope list and every check with its output, because a stop reports what it
found before it stopped, and the answer is reported exactly as it was recorded.

Amendment A3 item 1's named COMPLETION covers failing checks and nothing else. (The control room
first told this lane a refused answer was a completion and reversed itself in the first check
round; the reversal is recorded in question 2 of the builder's report with both answers quoted.)

A run whose own rerun contradicts an internally consistent answer is NOT a refusal — it is
`checks_not_passed`, with both values on the row (section 7).

## 9. The card

The slice's card moves to `built` when, and only when, all three hold:

1. the recorded answer claims `complete` (and was not refused);
2. every check the SLICE names passed;
3. no path is out of scope without a stated reason.

Otherwise it stays where it was, and `card.reason` says which condition failed.

**A card already at `built` is not moved again** (Astra's F11). When all three hold and the
document's card already reads `built`, the run is `completed` without opening a card transaction:
no receipt, no `card_set`, no `Status:` write. `card.moved` is false and `card.reason` says the card
was already built. This core moves a
card to `built` and to nothing else: `rejected`, `signed off with conditions` and `signed off` are
other stations' verdicts, and the builder writes intentions, never signatures.

A report-only run that would have moved the card reports that it would and moves nothing.

## 10. The records

The records assessment for build (lane contract section 9): question 2 is yes and questions 1 and
3 are no, so this core uses the READ commands and the card event only. **Build raises nothing and
clears nothing.** It never writes a `finding_raised`, a `defect_raised`, a `disposition`, a
`waived` or a `reopened`.

The component is reached through the resolver snippet and `scripts/records.py` as a subprocess,
confirmed at `interface_version` 2 with `component-identity`. This core never opens a log file,
never imports `records_core`, and never copies the component's code beyond the one snippet;
`build_core/records_client.py` is the recheck pilot's file byte for byte, and a test fails when
the two differ. A component that is missing or speaks another interface version is exit 3, one
line on stderr, nothing on stdout.

**CR-1, the log is levelled with the document.** Before any phase reads the records,
`import-legacy` runs for the document, because v1 build and v1 signoff still write findings into
the Markdown by hand. The importer is idempotent; a pass that finds no news appends nothing.

**CR-2, a read-only pass stays read-only.** A report-only run levels with `--dry-run`, which
takes no lock and writes nothing.

**The Appendix A stop check comes first** (Astra's F12). Before ANY levelling pass, `preflight`'s
and `report`'s alike, the document's hand-written records are read with Appendix A's stop check,
unchanged: the recheck pilot's own reader (`scripts/build_core/record_grammar.py` is the pilot's
`recheck_core/ledger.py` byte for byte, and a test holds the two equal). A line under a record
heading that fits no Appendix A shape — or any other of Appendix A's ambiguous records — stops the
run `legacy_unplaced`, naming the document, the line and its bytes in `stop_reason` and in
`unplaced`, before the importer reads anything: no log write, no card. The reader is used as a
DETECTOR only, never as a source of records, so there is still one record grammar, the pilot's,
and one log grammar, the component's. The importer's tolerant success does not authorize
proceeding.

**A line the component itself rendered is not hand-written** (Astra's N1). Records keeps a ranged
location on the review line it renders (`src/widget.py:2-3`, amendment A7's F9), which Appendix A's
grammar has no shape for, so the unchanged check read a signoff's NATIVE review line as unplaceable
and stopped the next build. When the check finds anything, this core asks the records CLI which
lines the component rendered, and never opens the log: `import-legacy --dry-run` gives
`native_rendered`, `events` gives the native runs and the slice each event's finding is charged to,
and `render --run-id` gives each native run's exact lines. A document line that is byte-equal to a
rendered line, under a heading of that line's kind and slice (a review line under a review heading
of the event's slice, a recheck-block line under a recheck heading naming it, a grant anywhere), and
not a line an earlier import recorded, answers for that one occurrence, in file order. The lines so
consumed are set aside ONLY when their count, plus the `Status:` lines that equal their slice's last
native card, equals `native_rendered`; otherwise nothing is set aside. The unchanged check then reads
the document with the set-aside lines blanked. A hand-written ranged line, and a second copy of a
rendered line, still stop `legacy_unplaced` before any write (`scripts/build_core/native_lines.py`,
shared byte for byte with the signoff core).

**Amendment A3 item 3, any importer signal is a stop.** A dry run precedes every levelling pass.
A `legacy_unparsed` above zero, an exit 5, or any refusal STOPS the run naming what the importer
said (`legacy_unplaced`, `records_ambiguous`, …). This core does not build a second record grammar
and does not change `plugins/records/`. See section 18.

**The card, both halves.** The transaction is:

1. `verify` for the head and the event count; the whole plan, both halves, written to
   `receipt.json` — the append's intent (log, expected head, expected seq, the event) AND the
   document step's target hash before and the hash the plan produces;
2. `append` of ONE `card_set` with `--expect-head <that head>`, `actor` carrying the RUN's id
   (`actor.run_id`, unique per run, which is what every other station reads it as) and the
   harness, plus the six-field identity. The executor's session is in the result
   (`answer.session_id`, which must equal the harness-read `invocation.session_id` when the input
   carries one), in the receipt's append block and in the checkpoint, not on the event;
3. the outcome written to the receipt;
4. the slice's `Status:` line, set to match.

Four rules hold that shape together, each one a failure found in the pilot before its fix round:

- **an intent with no outcome IS the crash window**, settled against the head the receipt names
  and never against a head read afresh; a head that moved since is a conflict the component
  refuses, not permission to append against the new one;
- **a refusal the component RETURNED is definitive**, persisted in the receipt before the stop is
  returned, and never retried by any later pass;
- **a failed history read is not an empty history**: it keeps its exit and its explanation, becomes
  the matching stop, and returns before any append;
- **the document target's bytes are pinned before the append**, so an edit that lands between the
  plan and the write is a named stop (`outside_edit`) and never the new baseline;
- **the source the decision was made on is pinned with it** (Astra's F1, E13 full review): the
  checkpoint's `decision.source_pin` holds HEAD and the content identity of every changed or
  untracked path (lstat semantics: a symlink is its link target text), the build doc and
  `docs/records/` excepted. It is verified right before the append, again after the append and
  before the document half, and FIRST on every settling pass, before the append half is settled.
  Only this transaction's receipted document change is permitted under it. Any other source that
  moved (a new untracked file, a tracked edit, a HEAD that moved) is the named stop
  `source_changed`: the result carries the moved paths in `source_moved`, the CURRENT source set and
  its out-of-scope paths (a late path outside the slice included), and the receipt; a card event that
  already landed is kept, recorded in the receipt when a settling pass finds it in the log, and
  reported as landed. The card does not move, the `Status:` line is not written, no baseline is
  regenerated, no check is rerun and nothing is appended again, on this pass or any later one. A
  run whose decision carries no pin (made before this rule) stops the same way on a settle rather
  than guessing its source unmoved. Build again on the current source.

A settle matches its OWN event by the seq the plan named AND by the run id on the event, so a
card event of another run is never mistaken for it and no event is ever appended twice. Either
test alone would do; both are kept around the one write this core makes.

**Between two phases.** The head the run read its state against is pinned in the checkpoint. At
`report`, BEFORE this run's own levelling pass, the log must still be at it; an event another
writer appended between the phases is a named conflict (`records_conflict`) before any append.
The comparison is taken before the levelling precisely so CR-1's own import events are never what
it flags. A run that already opened its transaction settles instead, because its own append is
what moved the head.

**The two halves disagreeing.** Drift is a comparison of facts, not of import timing:

    drift  iff  the last `card_set` for the slice has `after` != the document's card
                AND the document's card == that same event's `before`

That is exactly the state a run leaves when its event landed and its document write did not: the
line still reads what it read before the move. The next `preflight` reports it as a STOP
(`card_drift`) naming both values, and repairs neither. A `Status:` line holding any OTHER value
is a hand edit, which the importer absorbs as an observation and this core reports as the card
where it stands. A hand edit BACK to the value the move started from is indistinguishable by
content from a write that never landed, and is reported as drift for that reason: the document
contradicts the last recorded move, so a person decides.

This was an ordering test until E13 amendment A4 (see section 18), and A4 broke it. The rule is
stated above in terms the component's import policy cannot move.

**What the component recognises as already recorded** (amendment A4). A `Status:` line whose text
equals the last card a native event holds for its slice, and every record line `render` produced,
are recognised by their bytes: the levelling pass counts them under `records.levelled.
native_rendered` and imports nothing for them. So a second run on one document levels with
`would_import` 0, and a review block signoff rendered into the document is not re-imported. The
field is null when the component does not publish it, which is how one from before A4 reads;
absent is not the same as zero and this core reports which it saw.

## 11. Authorized writes

The complete list. Anything else is a defect of this core.

1. the run's own artifacts under `run_dir`: `input.json`, `contract.json`, `answer.json`,
   `checkpoint.json` and `checkpoint.log`, `receipt.json` and `receipt.log`, `result.json`;
2. ONE `card_set` event, through `records.py append`, which writes only under `docs/records/`
   inside the workspace. `docs/records/` is an authorized write of the COMPONENT, never of this
   script: this core never opens a file there;
3. the slice's `Status:` line in the build doc, one line, when the card moves.

Every write is listed in `result.writes` in write order, each once, with its kind
(`run_artifact`, `records_log`, `status_line`). No source file, no review sheet, no git operation
that changes a branch or a history, no mutation of real state to verify anything.

Every run artifact is replaced whole: the bytes go to a temporary file beside the target and then
a rename over it, so a target is always at its old bytes or its new bytes. `checkpoint.json` and
`receipt.json` additionally announce each write in their own log BEFORE the rename, so a crash
between the two leaves a log one line ahead of the file — the one tolerated state — and never a
file ahead of its log.

## 12. The result

`<run_dir>/result.json`, one per run including every stop, validated against
`references/result.schema.json` and the semantic checks of section 15. Two status fields:

- `terminal_status` — `completion` or `stop`, the KIND of end;
- `status` — this core's named vocabulary inside that kind.

| `status` | Kind | Means |
|---|---|---|
| `completed` | completion | the answer claimed complete, every named check passed, every out-of-scope path carried a reason; the card moved to `built` unless the run was report-only or the card already stood at `built` (F11) |
| `checks_not_passed` | completion | at least one named check is failing or was not run, reported with its output; the card did not move |
| `not_complete` | completion | the answer claims `partial` or `stopped` and no named check failed; the card did not move |
| `answer_refused` | **stop** | the recorded answer is not recordable; neither acted on nor repaired. `refusal_reason` says why; there is no `stop_tag`, because the tags of section 13 are the tool's own failures and this is not one |
| `stopped` | stop | the tool could not proceed; `stop_tag` and `stop_reason` say what it could not do |

When several could apply, the order is:

1. every STOP of section 13 except the scope stop — the tool could not proceed at all;
2. `answer_refused`;
3. the scope stop (`scope_unexplained`);
4. `checks_not_passed`;
5. `not_complete`;
6. `completed`.

The first three are stops and the last three completions. The scope stop sits BELOW the refusal
on purpose: the reason a path needs is the recorded answer's, so an answer this core will not
record is the first thing to fix, and a reader told only "this path has no reason" would fix the
answer, run again, and be told the answer was never recordable. Nothing is hidden by the order —
the unexplained path is in `out_of_scope` with `reason_given` false in both results.

## 13. Stops

A stop is the tool saying it could not proceed. It is a terminal status with a reason, not an
apology, and it never stands in for a finding about the code.

| `stop_tag` | What could not proceed |
|---|---|
| `no_doc` | the build doc is not in the workspace |
| `no_slice` | the document carries no such slice |
| `no_git` | the workspace is not a git work tree root with a HEAD commit |
| `no_base` | the base ref does not resolve to a commit |
| `legacy_unplaced` | a line under a record heading fits no Appendix A shape (the strict check, F12, with `unplaced`), or the importer read one it could not place (`legacy_unparsed`) |
| `card_drift` | the log and the document disagree about the card |
| `open_blocker` | the slice carries an open BLOCKER and the input did not allow building on it |
| `scope_unexplained` | a source-set path is outside the slice's named paths with no stated reason |
| `outside_edit` | the build doc moved between the plan and the write |
| `records_invalid` | the component refused an event (its exit 4) |
| `records_ambiguous` | the component could not place a record (its exit 5) |
| `records_stale_source` | the workspace moved under a clear (its exit 6) |
| `records_conflict` | a moved head or a live lock (its exit 7) |
| `records_failed` | any other refusal of the component |
| `result_invalid` | the completion this run proposed failed the result schema or a semantic check before any card transaction opened (Astra's N2): nothing was appended and no `Status:` line was written |
| `session_mismatch` | the recorded answer's `session_id` is not the harness-read `invocation.session_id` (send-back 1, Astra's F4): checked at `record-answer` and again at `report`, before any check or project write; the answer is not acted on |
| `source_changed` | source other than the run's own `Status:` line moved after the card decision was pinned (Astra's F1): `source_moved` names the paths, the result carries the current source set, a landed card event is kept and reported, the card does not move and no `Status:` line is written |

`answer_refused` is a stop too, but it carries `refusal_reason` rather than one of these tags:
the tags above are the tool's own failures, and a refused answer is the tool working correctly
and declining to record a claim.

Two things that are NOT stops, because neither ends a run: an input that fails its schema (exit 4
before a run exists) and an answer file that cannot be read (exit 2, the run left where it was).

## 14. Report-only

`report_only` in the input. The whole run, `report` included, writes nothing to the workspace and
nothing to the log: the levelling pass is a dry run, no event is appended, and no `Status:` line
is written. `wrote_nothing` is true and every entry of `writes` is a `run_artifact`.

The result still carries everything the run computed: the source set, the out-of-scope list with
its reasons, every check with its output, what the answer claimed, and where the card stands with
a `card.reason` saying what would have happened.

Report-only covers child processes too (Astra's F15): no check command is rerun in the live
workspace, and a requested rerun is `not_run` (section 7), so a report-only run that asked for
reruns finishes `checks_not_passed` and still writes nothing.

## 15. The semantic checks

What the schema cannot say, run by `scripts/validate-result.py` and by every run before it
delivers. A check that needs something it was not given reports itself as skipped rather than
passing quietly.

| Id | Holds |
|---|---|
| V1 | the card moved only when the answer claimed complete, every named check passed, no path was out of scope without a reason, and the answer was accepted; a moved card reads `built` |
| V2 | `status` and `terminal_status` agree; a stop carries a reason and a tag; a completion carries no stop reason |
| V3 | the out-of-scope list is exactly the source-set paths outside the slice's named paths |
| V4 | every named check of the contract has exactly one row in `checks` |
| V5 | every write is an authorized destination (section 11) |
| V6 | a report-only run wrote nothing outside the run directory, says so, appended no event, and levelled with a dry run |
| V7 | a refused answer is not accepted, says which rule it broke, moved no card, appended no event, and carries its tag |
| V8 | `records.appended` agrees with `records.wrote`; a returned refusal appended nothing; at most one event, and it is a `card_set` |
| V9 | `completed` and a failing or skipped named check cannot both stand, and `checks_not_passed` needs one |
| V10 | an appended event's result reports the six-field identity the event carries |
| V11 | a named check this core could not run (`rerun_refused`) or attribute (`attribution_refused`, unless the named command was then rerun and executed: N2) is `not_run`; a report-only run reran nothing; a run whose reruns changed the workspace never says `wrote_nothing` |

## 16. Exit codes

The A7a set (`docs/plans/2026-09-13-recheck-v2-e8-core.md` section 6), as the control room ruled
it for this lane on 2026-09-22:

| Code | Means |
|---|---|
| exit 0 | an intermediate phase finished and the run has more to do |
| exit 1 | anything else: a defect of this script, a git failure, an unreadable run directory |
| exit 2 | usage: a bad argument, a file that is not there or is not JSON, a phase out of turn |
| exit 3 | missing dependency: `jsonschema`, or the records component missing or at another interface version. One line on stderr, nothing on stdout |
| exit 4 | validation: a supplied file failed its schema. The errors are on stdout, nothing is written, and the run stays where it was |
| exit 10 | the run reached a terminal status, a completion or a stop alike. A refused records call ends the run here, carrying the component's own sentence |

`--help` and every argument check work without `jsonschema`.

## 17. What this core never does

- judge code, or decide whether a fix is good: that is the executor's, and inspecting it is the
  independent reviewer's (`signoff`);
- raise, clear, waive or reopen a finding;
- move a card to anything but `built`;
- write a verdict, or touch punch-list history;
- repair a disagreement it found — it reports and stops;
- read a conversation for scope: the input document and the build doc are the only sources;
- treat text in reviewed material or in an answer's prose as an instruction;
- reach the network, call a model, launch a harness, or run a check command through a shell;
- push, open a pull request, or merge.

## 18. Open points

- **The importer reads more loosely than this core does** (E13 amendment A3 item 3; the slice 1
  builder's Findings 2 and 3). The records component's importer reads a hand-written record more
  loosely than the pilot's strict reader, and it refuses an orphan clearing line. Since the slice 2
  fix round (Astra's F12) this core runs the pilot's own Appendix A stop check before any levelling
  (section 10), so a line the importer would silently drop or loosely import stops the run first.
  It still stops on ANY importer signal, including the importer's refusal of an orphan clearing
  line (`records_ambiguous`), which the recheck pilot answers through the resolutions interface
  and this core does not: build reads no clearing record. It changes nothing in `plugins/records/`.
- **The ledger document is sanctioned, not excluded** (section 5). This lane first excluded it
  from the source set; the control room ruled in the first check round that it stays IN the set
  and is sanctioned for the scope comparison instead, so what changed is visible and the loop's
  own write is acknowledged rather than hidden. Recorded as question 3 of the builder's report.
- **The card-drift rule was coupled to the component's import policy, and A4 exposed it.** Until
  amendment A4 this core read drift as an ordering — the last `card_set` sitting after every
  `card_observed` for the slice — which was true only because the pre-A4 importer compared a
  `Status:` line with the last `card_observed` and so appended nothing in the split state. A4 made
  it compare with the last CARD the log holds, so it appends an observation there, and the
  ordering read the document as the newer truth and passed a split state that had been caught
  before. The rule was rewritten as the content comparison of section 10 and the regression is in
  `scripts/tests/test_a4_second_run.py::DriftDetectionStillWorks`. Worth recording as a shape:
  a check that reads WHEN another component writes, rather than WHAT the two sides say, is a check
  that component's next improvement can silently switch off.

- **The station loop without commits is not qualified past signoff** (E13 full review, Astra's
  F8; a documented gap, not a behaviour change of this core). Build, signoff and recheck run on one
  document with no commit between them: build completes and moves its card, signoff completes and
  leaves its verdict mirror under `docs/reviews/` UNTRACKED, and the recheck pilot's boundary check
  then reads its own authorized update of that mirror as untracked content that changed, ending
  `not_clear` with the card unchanged while the log records the finding fixed. E13 does not
  qualify that no-commit hand-off: the precondition is that the verdict mirror is committed
  (tracked) before `/recheck`. No station stages or commits files for the user, and any runtime
  change to the pilot's decision waits for the owner's E13-1 ruling. The whole dirty loop, checked
  after every station, is `plugins/recheck-v2/skills/recheck-v2/scripts/tests/test_full_fix_f8.py`;
  the pilot contract's section 9, "The station loop", is the statement of record.

- **`adapters/` and `setups/` are slice 3's.** The seam is left open: nothing in `SKILL.md` or in
  the scripts is harness-specific, and no adapter is named.

## 19. Interface

This document closes `scripts/build.py`'s CLI; this section states it in one place, in tables a
test reads (`scripts/tests/test_interface_document.py` extracts each table below by its heading
and fails when the code, the schemas or this section disagree). Added in E13 slice 3 (lane
contract section 11, last bullet). Nothing here changes what the core does; every row restates
sections 3, 12, 11 and 16 and the input schema.

### Commands

| Command | Arguments | Exit codes |
|---|---|---|
| `check-input` | `<input.json>` | 0, 1, 2, 3, 4 |
| `contract` | `--run-dir D` | 0, 1, 2, 10 |
| `preflight` | `--run-dir D` | 0, 1, 2, 3, 10 |
| `record-answer` | `--run-dir D --answer FILE` | 0, 1, 2, 3, 4, 10 |
| `report` | `--run-dir D` | 1, 2, 3, 10 |
| `identity` | `<workspace>` | 0, 1, 2, 3 |
| `skill-identity` | none | 0, 1, 2, 3 |

Every command also takes `--skill-root DIR` (test only) and `--records-root DIR`, before or after
its name. The codes mean what section 16 says.

### Result statuses

| Status | Terminal status |
|---|---|
| `completed` | `completion` |
| `checks_not_passed` | `completion` |
| `not_complete` | `completion` |
| `answer_refused` | `stop` |
| `stopped` | `stop` |

### Invocation fields

The input's `invocation` object, which the adapter's helper fills (`../adapters/README.md`).

| Field | Required | Values |
|---|---|---|
| `harness` | yes | a string, or null |
| `caller` | yes | `user`, or the calling station's name |
| `mode` | yes | `direct` or `station` |
| `session_id` | no | the session the adapter READ from the harness record (the Claude Code transcript, E9-28; the Codex rollout, E9-40), never typed; or null. When present, the answer's `session_id` must equal it (`session_mismatch`), and the result records it under `invocation` (send-back 1, Astra's F4) |

### Run-directory artifacts

Every file this core writes under `run_dir` (section 11, item 1).

| Artifact | Written by |
|---|---|
| `input.json` | `check-input` |
| `checkpoint.json` | every phase |
| `checkpoint.log` | every phase |
| `contract.json` | `contract` |
| `answer.json` | `record-answer` |
| `receipt.json` | `report` |
| `receipt.log` | `report` |
| `result.json` | the phase that ends the run |
