# Handoff v2 core: behavioral contract

What this station does, what it reads, what it may write, what stops it, and the words it uses for a state. Written
for E15 slice 1, hand-back 2 of the skills v2 rebuild, against the E15 lane contract (sections 6, 9 and 12,
amendments A1, A2, A22 and A23) and the control room's readings CR-11 to CR-17 in the slice 1b brief, as slice 1b's
fix round 1 amended them (A23, and the check's C1B1-3 to C1B1-9). Where this document
and that contract differ, the contract is the authority and this document is the defect. `references/back-loop.md`
is the discipline the three back cores share; this document is this core's own.

Contents: 1 Job · 2 What is kept and what moved · 3 The phases · 4 The input · 5 Reading the build doc · 6 The
sanctioned writes · 7 The next move · 8 The load-bearing forms · 9 The result · 10 The records component · 11 The
harness seams · 12 Stops and exits · 13 The seeded families · 14 What this core never does · 15 Interface.

## 1. Job

A slice boundary has come and the thread is about to be cleared. Everything a clear would destroy is asked, recorded
or written down, and the owner leaves with the exact line to type in the fresh session. The script never judges a
slice, a finding or the wisdom of a next move (ruling E15-4): it finds the doc, reads it by vertical-v2's line rules,
reads the record now (the records component and git), assembles the record's own questions, holds the executor's
recorded answers to the record, resolves the next move by the rule of section 7, renders the forms and makes the
sanctioned writes. The asking, the answering and the perishables are the executor's and the owner's, recorded with
whose words they are.

## 2. What is kept and what moved

Kept from v1 (ruling E15-1): photograph, never gate (open cards change the output, never stop the run); the question
gate as the one pause, its four sources, one batch, and nothing written while any question is unanswered; the record
over the recollection; the dated `WAIVED (per user)` and `REOPENED (per user)` lines for an answer that waives or
reopens, placed at the ledger home's tail, with the card update they carry (v1's step 4, restored by A23 (2)); one
additive block per run at the tail of `## Handoffs`, created before
`## Punch list` when missing; the three shapes of the next move; the checkpoint commit, local only; the memory
pointer, one per feature, overwritten each run; the feature identity derived one way; the `HANDOFF:` block and the
gate-open form; report and stop.

What moved: the deterministic half is a script; the photograph is the script's read, never the executor's (CR-11),
and an answer that asserts a photograph fact the read contradicts is refused; the cards and the open set come from the
records component's `state` (ruling E15-9); a waiver or a reopening is a records event written through
`records.py append`, its line the one the component renders (`render`), and a card it moves is a `card_set` event
and its `Status:` line in the same records transaction build-v2 uses for a card (A23 (2)); the checkpoint commit is
the executor's named
step outside the script, and the script records the commit it finds (A2, Q2); the memory pointer is the Claude Code
adapter's step and is absent on Codex (A2, Q3); the vault tier of v1's hunt is dropped (A2, Q4); the kickoff lines
name the v2 stations (A2, Q5); every line read from the doc goes through vertical-v2's line rules (A22 (1), CR-17).

## 3. The phases

`check-input`, then `select`, `photograph`, `gate`, `record-answer`, `write`, `report`, in that order; `identity`
and `skill-identity` at any time. A phase command against a run at another phase is exit 2 naming the command to run
instead. Every phase reads and writes only the run directory, except `write`'s sanctioned writes (section 6). Every run
file this core reads or writes itself is checked first with `os.lstat`: a link, a pipe or a file outside the run
directory is refused (exit 1), never followed.

### 3.1 `select --run-dir D [--doc PATH | --name NAME]`

The hunt (ruling E15-10, `station_core/hunt.py`, three outcomes, never a silent pick), v1's repo tiers in v1's order:
the file names first (`docs/plans/*-<name>.md` and `docs/plans/<name>.md`, then the flat `docs/<name>-build-plan.md`;
a `docs/plans/` match wins over a flat one and the result's `notes` name the flat doc passed over), then an `Intent:`
line, consulted only when no file name matches (the docs of those two folders whose first `Intent:` line outside an
accepted fence holds every word of the name, split on `-`, `.` and `_`, as whole words in any letter case; anything
subtler is the executor's `--doc`), then a phase or slice doc (`docs/*phase*.md`, `docs/*slice*.md`, `plan/*.md`). No
vault tier (A2, Q4). `--doc` takes the doc the invocation names or the plan the session established (an existing `.md`
inside the workspace; anything else is refused, exit 5). No `--doc` and no `--name` stops (`selection-unnamed`): an
invocation that names nothing is a stop that asks, never the lone doc on disk. `none` stops (`selection-none`);
`several` stops (`selection-several`, the candidates listed).

Then the doc is read (section 5); a line the rules refuse stops (`doc-unreadable`, naming the line), and a handoff
block outside `## Handoffs` stops (`block-misplaced`). Then the identity (CR-15, `doc.identity`): the `<topic>` of
`docs/plans/<YYYY-MM-DD>-<topic>.md`, else the `<feature>` of `docs/<feature>-build-plan.md`, else a slug of the doc's
own title (its first line, a plain `# ` heading, the build-doc form's ` <dash> build plan (<date>)` tail set aside;
folded, every run of characters other than `a-z` and `0-9` read as one `-`), else none: a stop that asks
(`identity-unnamed`); the owner's name (`station.feature`) is taken only then, and a name that differs from a derived
identity stops (`identity-conflict`), so the same doc always yields the same identity. Writes `selection.json` and
`doc.json` (the doc's hash, its slices, `Depends on:` and `Questions:` lines, and every handoff block's text).

### 3.2 `photograph --run-dir D [--suite-record FILE] [--records-root DIR]`

CR-11: read now, by the script. The workspace must be a git work tree root with a commit (`not-git`). The doc must
still hold the bytes `select` read (`photograph-moved`), and every handoff block the doc held at HEAD must be in the
working copy byte for byte, in order (`block-edited`). The cards and the open set: the records component's `state`
for the doc (the latest-record rule the component implements, never recomputed here). A slice's card is its
`card_observed` (its text when the value is not one of the component's six) when the log observed or set one, else
its `Status:` line as the line rules read it; `source` says which. The open set is every finding `state` holds `open`.
The repo: the branch (`git symbolic-ref`), HEAD, the default branch (the remote's HEAD, else `main`, else `master`)
and the commits ahead of it (`git rev-list --count`), the tree (`git status --porcelain`: `clean` or `dirty` with the
paths). The suite: `--suite-record` names the last-recorded suite state, read with its provenance (a build-v2
`result.json`: its checks counted passed, failing and not run, its run id, slice, path and time, and the file's hash;
any other file is named, its state not read); without it, "none recorded". No test suite is ever run. The slice just
finished: `station.slice` (a slice the doc does not hold stops, `slice-unknown`), else the last slice in document
order whose card is not `not started`. Writes `photograph.json`.

### 3.3 `gate --run-dir D --questions FILE`

CR-12. The questions file (kind `questions`) carries the session's questions, v1's sources 1 and 2, with ids `q1`,
`q2`, ... in order; a question that cannot land in the block (section 6, "Text that lands") is refused, exit 5. The
script adds the record's, v1's sources 3 and 4, read on the PROSPECTIVE cards (every open card taken as cleared: an
open card's kickoff is the fix list, the slice about to be built is the one after it, and a grant this run records may
clear it, so the one batch holds every record question the answers could make matter):

- `r-next`, when the cards and the `Depends on:` chains do not yield exactly one next slice (section 7's candidates;
  the just-finished slice must stand `signed off` and exactly one candidate exist), carrying the candidates;
- `r-q1`, `r-q2`, ..., one per `Questions:` line (not `none`) in the section of the slice about to be built: the one
  next slice, or each candidate when `r-next` is asked.

Nothing is answered and nothing is written outside the run directory. Writes `gate.json`; prints every question, the
open set with each finding's id, and every finding the log holds.

### 3.4 `record-answer --run-dir D --answer FILE`

The answers file (kind `answers`): per question `answered` true with the owner's `words` and an `effect` (`note`,
`waive` or `reopen` with a finding id, `next-slice` with a slice or null), or `answered` false; the `perishables`; and,
optionally, `asserts` (what the executor believes of the photograph). In order:

1. **Refused, exit 5, nothing written, the run stays at `asking`:** an asserted card, open item (an id or a location),
   branch, commits-ahead count or tree state the photograph contradicts (CR-11); a question id the gate never asked, a
   question answered twice; a `next-slice` effect on any question but `r-next`, or any other effect on it; a waiver or
   reopening on a record question; a waiver of a finding the log holds neither `open` nor `fixed`, a reopening of one
   it holds neither `waived` nor `fixed` (the component's admissions), two grants on one finding; a `next-slice`
   answer naming no slice of the doc that can start (the slice must be the doc's and stand `not started` or `in
   progress`, a candidate of the record or not: a chain the record cannot read leaves the owner's word the only way
   to name it, the slice 1b check's C1B1-5); words, a perishable that cannot land (section 6); and a set of answers whose grants
   leave the next move unresolved (section 7) with no answer to `r-next`: the refusal names the candidates, and the
   corrected file carries the owner's answer as `r-next` even when the gate did not ask it.
2. **Any question unanswered**, some or all: the run ends (exit 10, `gate-open`) with nothing written anywhere (the
   doc, the log, the pointer), the result's `chat` in v1's gate-open form.
3. Otherwise `answers.json`: each answer with its question and where it lands (`block` for a note and a next-slice
   answer, `ledger line` for a waiver or a reopening), the grants, the perishables, the summary.

### 3.5 `write --run-dir D [--records-root DIR]`

CR-13 and CR-14, in the order of section 6. Prints the next move, the block, the writes with their hashes, the events
and the pointer.

### 3.6 `report --run-dir D --bottom-line TEXT [--skill-note TEXT]`

The completion: the `HANDOFF:` block rendered from the result (section 8) into `chat.md` and `station_result.chat`;
on Claude Code, the adapter's `pointer-receipt.json`, when present, checked (the run's pointer was the adapter's, each
write holds the bytes it names, the pointer file holds the text this run rendered; any failure is exit 5, nothing
recorded) and its two writes recorded as `memory_pointer`; on Codex a receipt is refused (exit 5).

### 3.7 `identity <workspace>` and `skill-identity`

The frame's: the workspace as this station sees it, and this skill's name, version, commit and content hash.

## 4. The input

`references/input.schema.json`, closed. The shared fields (back-loop section 3) and `station`, each optional:
`date` (the block's date, `YYYY-MM-DD`; absent, today's UTC date from the run's clock), `slice` (the slice the
invocation names as just finished), `feature` (`name` and the owner's `words`: his name for the doc, taken only when
none derives, section 3.1). The questions and the answers arrive later, in their own files
(`references/answer.schema.json`).

## 5. Reading the build doc

CR-17 (A22 (1)). Every line this core reads from a build doc to decide anything (where `## Handoffs` and
`## Punch list` stand, the earlier handoff blocks, the record blocks, the `Depends on:` and `Questions:` lines, the
slice headings and their `Status:` lines) goes through vertical-v2's line rules: `scripts/handoff_core/fences.py` is
vertical-v2's `vertical_core/fences.py` byte for byte, held equal by `scripts/tests/test_line_rules.py` (compared with
vertical-v2's file in the checkout, skipped, never passed, in the installed shape; its statement and its character
list checked in both). Its docstring is vertical-v2's statement of A8's strict fences, A9's raw HTML lines, A10 and
A11's exact labels, A12's plain structure, A16's character list and A18's stray `Status:` line and leading marks,
quoted as it is (it names vertical-v2's own files where it says where each rule is used). Any problem it names stops
the run before any write, naming the line (`doc-unreadable`). The second, CommonMark reading of A13 is vertical-v2's
and is not part of this rule (A22 names the line rules). `templates.parse` decides nothing here.

On a doc those rules accept, `scripts/handoff_core/doc.py` reads, outside accepted fences only: the sections (every
`## ` line opens one, which runs to the next plain level 1 or level 2 heading outside an accepted fence, the way
vertical-v2's spec ends a withheld section, so a `# Appendix` after the ledger is no part of it: the slice 1b check's
C1B1-3), `## Handoffs` and `## Punch list` by their exact names (a second of either stops, naming it); the slices
(the line rules' slices, each running to its section's end); this core's own two labels in each slice's section,
read the plain way A12 reads a label (a line that, after any prefix and any leading listed mark, folds to `depends
on` or `questions`, spaces or tabs, then a colon, is read only when it starts at column 0 with exactly `Depends on:`
or `Questions:`; any other such line stops, named; a second `Depends on:` in one slice stops, named; a `Questions:`
line whose value is empty, `none` or `nothing` followed by a list item in its paragraph, or an empty one whose next
non-blank line in the slice is a list item, stops, named, since each open question goes on its own `Questions:`
line, C1B1-4; either label in a paragraph that also holds `<!--` or a link reference definition stops, named, since
CommonMark may hide the label there, C1B1-9);
the handoff blocks (a line reading exactly `### <YYYY-MM-DD> <dash> handoff`, running to the next level 1 to 3
heading or the doc's end); the record blocks (`### <YYYY-MM-DD> <dash> review: ` or `recheck: `). `<dash>` is U+2014,
the constant `forms.D` (section 8).

Measured on the 25 real build docs the control room snapshotted (the evidence corpus, never copied here): the line
rules stop 4, the same 4 vertical-v2's line rules stop, and this core's own reading adds none (the builder's report).

## 6. The sanctioned writes

CR-13, exhaustively. Nothing else is ever written: no earlier block, no punch-list history, no `Status:` line but a
card this run's grants moved, no event but the grants and their card moves (ruling E15-9 as A23 (2) amends it for
handoff-v2: for each grant the `waived` or `reopened` event and, when the slice's card changes by v1's rule after the
grants, a `card_set` event and its `Status:` line, in the same records transaction build-v2 uses for a card, all or
none).

**Before any write**, each a stop with nothing written: every handoff block `select` read is still there byte for byte
(`block-edited`); the doc still holds the bytes `select` read (`photograph-moved`); the branch is the photographed one
and HEAD is the photographed commit or exactly one commit on it whose subject starts `handoff checkpoint`, taken on
a tree the photograph saw dirty and changing only paths it saw dirty (`git diff --name-only`, read-only; the slice 1b
check's C1B1-8) (else `photograph-moved`, naming the extra paths); the records log's head is the photographed one
(`photograph-moved`); every card move (section 7) starts from the card the records and its `Status:` line agree on,
on a slice that has one (`write-refused`); the block renders, and the doc planned with the card moves and the block
reads cleanly by the line rules, holds every earlier block unchanged and exactly one more, under `## Handoffs` and
last there, and differs from the doc only by the inserted lines and the moved `Status:` lines (`write-refused`); and
the records' tail rule (A23 (1)): when the log holds record lines it imported from the doc (`events`, legacy
origin), the component's `import-legacy --dry-run`, which writes nothing and takes no lock, must not refuse the doc as
it stands with a conflict (exit 7), and the planned doc must keep every imported line in its order and add no line
byte-equal to one (`doc.levelling_problem`), or the run stops `write-refused` with nothing written: a write that would
leave a doc the widened section 11.7 still refuses is never made.

**Text that lands** in the doc (a question, an answer's words, a perishable) is one non-blank line, without the line
form's separator ` · `, every character on vertical-v2's character list, so the doc stays readable by the line rules.

**The writes, in order**, each in `receipt.json` and the result with its hash before and after:

1. **The grants and their card moves** (CR-13 (1), A23 (2)), the one records transaction build-v2 uses for a card
   (its contract sections 9 and 10): the whole plan in `receipt.json` first (the events, the card moves, the doc's
   hash before and with the moves set), then one `waived` (with the finding's severity, `verified_source` the
   workspace identity the component computes now, `join_basis` null) or `reopened` event per waiver or reopening,
   each with the owner's words, `grant_date` the run's date, `actor` this station, this run's id and the harness,
   and after them one `card_set` per card move (`slice`, `before`, `after`, `source` that identity, build-v2's
   event shape), ALL in one `records.py append` against the photographed head, all or none (a refusal stops,
   `records-refused`: the component writes nothing and the doc is not written, so both stay byte-equal); the
   outcome in the receipt. The grant lines are the ones `records.py render --run-id <run id>` returns for this run
   (a `card_set` renders no line).
2. **The doc, once** (CR-13 (1) and (2)): each moved card's `Status:` line set to the new card (its prefix, trailing
   spaces and ending kept), the rendered grant lines directly after the last non-blank line of the
   ledger home (the section holding the latest-dated record block, a date tie going to the later in the file; else
   `## Punch list`; else a `## Punch list` created at the doc's end), and the block at the tail of `## Handoffs` (after
   its last non-blank line, a blank line before it and, when a non-blank line follows, one after it), created right
   before `## Punch list` when missing, or at the doc's end when the doc has neither. The plan is checked again as
   above, and the doc's bytes again; then the doc is replaced whole (a temporary file and a rename). A check that
   fails after the events landed stops `write-refused` with the receipt saying so.
3. **The checkpoint commit** (CR-13 (3)): never made by the script (A2, Q2). The executor's named step, between
   `record-answer` and `write`, when the photograph showed a dirty tree; `write` records the commit it finds (`commit`,
   `parent`, `subject`) and the block's `Repo:` line reads `checkpointed <commit>`.
4. **The pointer** (CR-13 (4)): `write` leaves its text in `pointer.json`; the Claude Code adapter's `pointer.py`
   writes it (section 11).

A report-only run plans and checks everything, leaves `planned-doc.md` (the block alone; the grant lines are the
component's and only a real append renders them), `events.json` and `pointer.json` (`for_adapter` false) in the run
directory, and writes nothing else.

**The block** is the script's render of its own reads (CR-11): `- Next:` (section 7), `- Cards:` (each slice's card:
a card this run's grants moved reads as the new card, naming the one it moved from; otherwise the card, and the card
after this run's grants where the records derive another), `- Open:` (one line per finding open after the grants, or
`none`), `- Repo:` (branch, commits ahead of the default branch, `clean`, `checkpointed <commit>` or `dirty (N paths)`,
read at `write`), `- Suite:`, then `- Question:` (question, answer, where it landed) per answer that lands in the block,
and `- Perishable:` per perishable. No line comes from the answer but the questions, the answers and the perishables.

## 7. The next move

CR-14, `scripts/handoff_core/nextmove.py`, resolved from the record after this run's grants.

**The card after the grants** (v1's update rule, which the component's `card_derived` implements; for a slice a grant
of this run names, written as section 6 says, A23 (2); for any other slice, reported only): where the log names the
slice, a verdict card (`rejected`, `signed off with conditions`, `signed off`) takes
the card its open findings give, waived ones excluded (a BLOCKER open: `rejected`; else a MAJOR: `signed off with
conditions`; else `signed off`); any other card is kept (a rebuilt slice never takes a verdict from a grant). A
`Status:` line the log never saw is the card as written. **The candidates**: the slices whose card is `not started` or
`in progress` and whose every `Depends on:` slice stands `signed off` (`nothing` and `none` list none; parts split on
commas and ` and `, a leading `Slice ` set aside; a part naming no slice of the doc makes the chain unreadable and the
slice no candidate).

**The shapes**, in this order: (1) **open card**, any slice's card `rejected` or `signed off with conditions`, or any
BLOCKER or MAJOR open: the fix list (every open BLOCKER and MAJOR), then `/recheck-v2 <slice> <doc>` per such slice,
no kickoff line; (2) **loop complete**, the doc holds slices and every one stands `signed off`: no kickoff line, the
next move the owner's; (3) **the owner's answer** to `r-next`: a slice gives a clean boundary on it (never a slice the
doc does not hold; `record-answer` takes only one that stands `not started` or `in progress`, and the block's `Next:`
line and the result's `how` say the slice came from the owner's words), null gives **owner holds**, no kickoff line; (4) **clean boundary**, the just-finished slice
stands `signed off` (or no slice has started) and exactly one candidate exists: the kickoff `/ship-v2 <slice> <doc>`
and, stated once, the by-hand alternative `/build-v2 <slice> <doc>`; (5) otherwise unresolved, which never reaches
`write` (section 3.4). Never `/ship-v2` of a slice that does not exist.

## 8. The load-bearing forms

Ruling E15-11. Rendered and parsed by one module, `scripts/handoff_core/forms.py`, with a round trip for each
(`scripts/tests/test_forms.py`): the block heading `### <YYYY-MM-DD> <dash> handoff`; the block's lines; v1's
`HANDOFF:` block (its first line `HANDOFF: <feature> <dash> after <slice>`, the `Doc:`/`Next:`, `Repo:`/`Suite:` and
`Questions:`/`Perishables:` lines with v1's double-spaced middle dot, the bottom line, `Open:` and `SKILL NOTE:` lines
only when any, the closer `Thread is safe to clear.`); v1's gate-open form (`HANDOFF: <feature> <dash> GATE OPEN,
nothing written`, `Doc:`, one `Unanswered:` line per question, and the closer `Thread is NOT safe to clear <dash>
answer the questions and re-run /handoff-v2, or clear and accept the loss.`). The `WAIVED (per user)` and
`REOPENED (per user)` lines are the records component's render, carried as it returns them.

**The em-dash exception.** `<dash>` in those forms is U+2014, v1's byte, kept (E15-11): standing rule 10's one named
exception. It is one constant, `forms.D` (and `doc.D` for the reading), written in code as an escape; no file of this
core types the character (`scripts/tests/test_forms.py`, `NoTypedDash`), and this document names it rather than
typing it.

**The station names** in the kickoff lines and the gate-open closer are the v2 stations' (A2, Q5: `ship-v2`,
`build-v2`, `recheck-v2`, `handoff-v2`) while v1 stays installed; the name is a value of the form, the form's bytes
around it are v1's.

## 9. The result

`references/result.schema.json`, closed, with the E14 semantic checks S1 to S4 (`scripts/validate-result.py`). Every
run ends in a terminal status, every stop included. `writes` lists the doc (`build_doc`), the log (`records_log`), the
pointer's two files (`memory_pointer`, from the adapter's receipt) and, on a report-only run, its plan files
(`run_artifact`), each with its hash before and after. `trace` is null: handoff invokes no station and writes no
`trace.jsonl` (CR-16). `station_result` carries the doc, the feature and how it derived, the slice the run is after,
the photograph, the questions, the answers' summary, the next move, the block, the events, the cards after the
grants (with the component's `card_derived` beside each, read after the append), the checkpoint, the pointer
(`for_adapter`, `written`, its `note`) and `chat`.

## 10. The records component

Reached through the resolver snippet and the CLI only (`station_core/records_client.py`, `records_link.py`), confirmed
at `interface_version` 2; exit 3 when missing or at another version. Read: `state` and `verify` (the photograph),
`identity` (the source of a waiver and a card move), `render` (the grant lines), `events` and `import-legacy
--dry-run` (the A23 (1) guard, section 6; a dry run writes nothing and takes no lock). Written: one `append` of the
`waived` and `reopened` events and the `card_set` events they carry (ruling E15-9 as A23 (2) amends it). Never a
levelling pass: a doc whose hand-written records the log does not hold is photographed as the log holds it. Never a
log file opened.

## 11. The harness seams

Ruling E15-12. **The memory pointer**: on Claude Code, the adapter's step `adapters/claude-code/pointer.py --run-dir D
--memory-dir M`, after `write` and before `report`: v1's `handoff-<feature>.md` (type project, the doc path, the
block's date, the kickoff line), overwritten each run, and its `MEMORY.md` line, replacing every earlier line for the
same file, worded as the build loop's kickoff pointer for the named doc; only under the folder it is given (no
default, no environment read), refusing a link at either target and any pointer `for_adapter` false, nothing written.
On Codex no memory pointer is written; the block in the build doc is the pointer and the result says so. **The manual
controls** (owner pick P5): `disable-model-invocation: true` in `SKILL.md` and `allow_implicit_invocation: false` in
`agents/openai.yaml`, measured manual-only by the install proofs (`setups/manual-only.sh`).

## 12. Stops and exits

The exits are the back loop's: 0, 1, 2, 3, 4, 5, 10 (back-loop section 2). A stop is `status: stopped` with one tag:

| Tag | Phase | Means |
|---|---|---|
| `selection-unnamed` | select | the invocation names nothing to match against: ask the owner |
| `selection-none` | select | no doc found in the repo's tiers (shared tag) |
| `selection-several` | select | several docs in one tier, listed, none picked (shared tag) |
| `doc-unreadable` | select | a line vertical-v2's line rules (or this core's own two labels) refuse, named |
| `block-misplaced` | select | a handoff block outside `## Handoffs` |
| `identity-unnamed` | select | no identity derives and the owner named none |
| `identity-conflict` | select | the owner's name differs from the derived identity |
| `not-git` | photograph | the workspace is not a git work tree root with a commit |
| `block-edited` | photograph, write | an earlier handoff block changed |
| `slice-unknown` | photograph | the input names a finished slice the doc does not hold |
| `records-refused` | photograph, write | the records component refused a call, its sentence carried (shared tag) |
| `gate-open` | record-answer | a question unanswered: nothing written, the gate-open form |
| `photograph-moved` | photograph, write | the doc, git or the log moved since it was read, or the checkpoint commit is not the photographed dirt |
| `write-refused` | write | the plan does not hold, a card cannot move from the card the records and the line agree on, or the write would leave a doc the records' tail rule refuses (section 6) |

`phase-not-built` and `station-refused` are the frame's shared tags; this core uses neither.

## 13. The seeded families

`evals/seeded-cases/`: H1 the record over the recollection, H2 the question gate, H3 additive, H4 the next move, and
T1 no v1 import (lane contract section 12), each with a case where nothing is planted; built by script, observed by
`lane_observe.py` through the real CLI; the outcomes live in an answer key outside this repository.

## 14. What this core never does

Run a test suite; run a git command that changes a branch, an index or a worktree (`scripts/tests/test_static.py`);
commit, push, open a pull request or merge; invoke a station or summon a reader; write a trace; write outside the
workspace and the run directory (the pointer is the adapter's); edit an earlier block, the punch-list history or a
`Status:` line other than a card this run's grants moved; write a card event other than a grant's card move, or
import the doc into the log; answer a gate question; read a v1 skill's files.

## 15. Interface

Commands: `check-input <input.json>`, `select`, `photograph`, `gate`, `record-answer`, `write`, `report` (each with
`--run-dir D`), `identity <workspace>`, `skill-identity`; `--help` on each, without `jsonschema`. Runtime:
`/usr/bin/python3` 3.9 syntax, standard library plus `jsonschema==4.25.1` through `uv run` (PEP 723); git 2.50.1.
Run-directory artifacts: `input.json`, `checkpoint.json`, `selection.json`, `doc.json`, `photograph.json`,
`gate.json`, `answers.json`, `receipt.json`, `write.json`, `pointer.json`, `pointer-receipt.json` (the adapter's),
`records-events.json` (the append's input), `planned-doc.md` and `events.json` (report-only), `chat.md`,
`result.json`.
