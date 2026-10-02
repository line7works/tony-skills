# The blueprint core contract, version 1

What `blueprint-v2` does, what it writes, when it stops, and what every field of its answer and
result means. This document, `station-loop.md` beside it (the contract the four front cores
share), and the schemas under `references/` are the interface; everything under
`scripts/blueprint_core/` and `scripts/station_core/` is internal.

Written for E14 slice 2 (lane L) against the E14 lane contract, section 11. Where this document
and that contract differ, the lane contract is the authority and this document is the defect.

Contents: 1 The job · 2 What is kept · 3 The phases · 4 The input · 5 Selection · 6 Harvest ·
7 The recorded answer · 8 Write · 9 Own commands · 10 Report and the read-back · 11 Report-only ·
12 Stop tags · 13 Records · 14 Readers · 15 The gate · 16 Seeded families · 17 Exit codes ·
18 What this core never does · 19 Open points.

## 1. The job

Turn a feature discussion into the sliced build doc the loop's later stations consume (build,
signoff, recheck and the inspect station), written for a builder who was never in the room. The
doc records what was decided; it does not decide. Every requirement, constraint and out-of-scope
line carries its trace; every acceptance criterion carries its check.

**The executor decides, the script records** (E14-4). The executor, the model running `SKILL.md`,
talks to the owner, asks, slices and judges, and hands its judgment to the script once, as the
recorded answer. `scripts/blueprint.py` finds the documents, reads the scope doc's ledger and the
architecture doc's lines, checks the answer, renders the build doc through the shared templates,
guards the doc's protected lines, writes, and reports. It never judges a plan.

## 2. What is kept

The station's five steps and seven rules are the behavior, unchanged (E14-1). Here is where each
lives now.

| Step | Where it lives |
|---|---|
| 1. Harvest what exists before asking | `select` (the scope doc, the architecture doc, the living build doc) and `harvest` (the ledger with ids, the architecture doc's poured-concrete and deferred lines, the build doc's protected lines). The discussion and the repository are the executor's to read |
| 2. Interview load-bearing gaps only, one batched round with a recommendation each; small reversible gaps become recorded assumptions | the executor's; what it asked is the answer's `questions`, what it decided alone is `assumptions` |
| 3. Slice: one build session per slice, dependency-ordered, ends wired in, independently verifiable, ceremony scaled | the executor's judgment; the script holds the checkable half: `depends-forward`, every requirement and criterion placed, a criterion with its check, `needs_build_doc` |
| 4. Write the doc: extend the living doc in place, or save a new one under `docs/plans/`; the forms exact; the last five sections scaffolded empty | `write`, through `station_core/templates.py` (section 8) |
| 5. Read back and stop | `report` renders the `BLUEPRINT:` block from the result (section 10); the executor posts it and stops (section 15) |

The seven rules:

1. **Record, never invent.** Every line traces to the discussion, the repo, or a question asked
   and answered here: the scope doc's ledger, a repository path, a question the owner answered in
   this run, or the owner's words quoted verbatim (the discussion before the run); an untraced line
   is refused (section 7). An open load-bearing question stays visibly open: it is rendered into
   the doc and counted in the read-back.
2. **Write for a builder who was not in the room.** The executor's; the doc carries real paths
   and names, never a reference to the conversation.
3. **Criteria are checkable.** A criterion with no `verify` form, or one that is none of the
   template's three forms (section 7), is refused.
4. **Requirements say what, slices say when, the builder decides how.** The executor's.
5. **Descoping is recorded with reasons.** Out-of-scope lines are rendered under `Out of scope:`
   with their trace, the written evidence signoff reads. A parked scope line or a deferred
   architecture line passes forward here as out of scope only by its id; the words alone are refused
   (`parked-line-unnamed`, whether or not an answered question touched the row; E14 punch list, the
   owner's ruling on A5(4) and E14-11). A scope `Open:` item does not go out of scope, unless an
   answered question of this run touched it and the line names it by its id (section 7): the
   question does not stand in for the id (A13, under A5(4)).
6. **Tests are part of the plan.** Each criterion names its check; a slice with no runnable check
   is the executor's to flag to the owner before the doc ships.
7. **One living doc.** One build doc per feature, extended in place, never forked. The ledger
   sections' lines, every `Status:` line and every `Plan: inspected` line are never changed by a
   revision (section 8).

## 3. The phases

```text
check-input <input.json>                            validate, create the run         (shared)
select --run-dir D --hunt H [--name N]              find the documents               (shared)
choose --run-dir D --hunt H --path P --words W      the owner's pick among several   (own, section 9)
harvest --run-dir D                                 read before asking               (section 6)
record-answer --run-dir D --answer FILE             check the one recorded answer    (section 7)
write --run-dir D                                   render and write the build doc   (section 8)
report --run-dir D                                  the result and the read-back     (section 10)
identity <workspace> / skill-identity               at any time                      (shared)
```

The checkpoint moves `checked -> selected -> harvested -> answered -> written -> done`, and a
command against the wrong phase is exit 2 naming what to run instead. A run that reached a
terminal status (`done`) answers `choose`, `harvest`, `record-answer`, `write` and `report` with
its recorded `result.json`, exit 10, and writes nothing. Every stop writes a validated
`result.json` before it is printed, so every run ends in a result.

## 4. The input

`references/input.schema.json`, the shared base, unchanged: this core adds no field under
`station`. The workspace is the repository the build doc lives in; `staging` is accepted and never
read (the build doc's homes are all in the workspace). The run date is the machine's local
calendar date when `harvest` runs, recorded in `harvest.json`; the executor types no date.

## 5. Selection

Every run hunts three times: `select --hunt scope [--name N]`, `select --hunt architecture
[--name N]`, `select --hunt build --name <feature>`. `harvest` refuses a run that skipped one
(exit 2), refuses a build hunt with no name (exit 2), and refuses a selected document that
vanished or is not UTF-8 text (exit 2, nothing written): the living doc is looked for under the
feature's name, so it is found, never forked. `{name}` narrows a hunt to one slug; with no name,
the slot reads `*`.

| Hunt | Glob | Tier | Home |
|---|---|---|---|
| `scope` | `docs/scope/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-{name}.md` | 1 | the scope folder, dated names |
| `scope` | `docs/{name}-scope.md` | 1 | the older flat name |
| `architecture` | `docs/architecture/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-{name}.md` | 1 | the architecture folder, dated names |
| `architecture` | `docs/{name}-architecture.md` | 2 | the older flat name |
| `build` | `docs/plans/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-{name}.md` | 1 | the plans folder, dated names |
| `build` | `docs/plans/{name}.md` | 1 | the plans folder, the topic undated (round 5, R2) |
| `build` | `docs/{name}-build-plan.md` | 2 | the older flat name |

Why the dated globs. A doc in a dated home is named `<YYYY-MM-DD>-<topic>.md` and is matched by its
topic, the part after the date, whole, as the station's step 4 says ("matched by its topic"): a
`*-{name}.md` glob would take `2026-09-22-big-turnstile.md` or `2026-09-20-reverse-turnstile.md` as
the `turnstile` feature's doc, and `write` would then extend another feature's living doc. With no
name the slot reads `*`, so every dated doc of the folder is a candidate.

Why the v1 homes only (round 3, R6). The homes are the v1 stations' own, never guessed (E14-10): in
each folder the dated name, which the scope, architecture and build stations write and the later
stations read, and the older flat names v1 still reads. An undated `<topic>.md` in the scope or the
architecture folder is no such home and never a candidate.

Why the plans folder's undated name (round 5, R2). The station selects over `docs/plans/*.md` by topic,
then the flat name (E14 contract, section 11), so the build hunt matches both
`docs/plans/<date>-<topic>.md` and `docs/plans/<topic>.md` at the first tier, then
`docs/<topic>-build-plan.md` at the second. Several first-tier matches (an undated plan and a dated
twin) are listed for the owner, never selected silently. An existing plan is extended where it lies:
its missing date prefix is no permission to fork a dated second plan beside it. `write` still names a
NEW doc with its date. The name is matched whole: `docs/plans/big-turnstile.md` or
`docs/plans/turnstile-v2.md` is another feature's plan.

Why the tiers. The scope homes share ONE tier (carried item C1-7): the station's step 1 says that
when more than one scope doc could match the feature they are listed and the owner is asked, so a
doc in the newer folder never hides a flat one; both are `several`. The architecture and build
homes keep the plans folder (or the architecture folder) first, the order the hand-off table and step 4
give, so an older flat build doc is extended where it lies only when no plan in the folder exists.

The outcomes. `none` is never a stop here: no scope doc means an empty ledger, no architecture
doc means no architecture lines, no build doc means a new one. `several` is listed for the owner
and never picked: the executor asks, and records his pick with `choose` (section 9) before
`harvest`; a `several` that reaches `harvest` unresolved stops the run `selection-several`,
listing every candidate.

## 6. Harvest

`harvest` writes `harvest.json` in the run directory and prints it:

- `scope`: the scope doc's path and its ledger as `station_core/ledger.py` reads it, every line
  with its id, tag, section, text, source and line number. A line the reader cannot tag stops the
  run `ledger-refused`, every such line quoted with its number.
- `architecture`: the architecture doc's path and, read through `templates.parse`, its
  poured-concrete lines (`poured`, each with an `arch-` id), its struck ones (`struck`,
  superseded, listed and never passed forward) and its deferred lines (`deferred`, each with a
  `defer-` id). An id is twelve hex digits of the SHA-256 of the line's text, so it follows the
  line, not its position. A line of those two sections the reader cannot read is refused, never
  dropped: every non-blank line under `## Poured concrete (one-way doors)` or `## Deferred` that
  is not a `- <text>` item (an indented or `*` item, a blank `- `, a line in a fence), and either
  section missing (`templates.check`'s finding `missing the section '<heading>'`), stops the run
  `ledger-refused`, each quoted with its line number; a missing section quotes the doc's near-miss
  heading when it has one (a re-cased heading, one without its suffix or with a trailing space). The
  two sections are known by their exact heading text as the template writes them, `## Poured
  concrete (one-way doors)` and `## Deferred`, never by a word inside a heading (round 3, R5): an
  unrelated section such as `## Why we deferred the cache` or `## Notes` is passed over. A `### `
  subheading inside either section is passed over: the section runs to the next `## ` heading, so
  it hides no item.
- `build`: an existing build doc's path, its SHA-256, its line ending, each slice with its name,
  short name and `Status:` line, every `Plan: inspected` line, every line from the first ledger
  heading to the end (byte for byte, endings kept), and `templates.check`'s findings on it.
- `ledger_view`: what `record-answer` checks against: the scope ledger's lines, then the poured
  lines as `decided` and the deferred lines as `parked` (a deferred line is a banked decision whose
  door stays open, passed forward as parked).
- `run_date`, `build_name`, and `target`: the existing build doc, or
  `<workspace>/docs/plans/<run_date>-<build_name>.md`.

## 7. The recorded answer

`references/answer.schema.json`, closed at every level, examples under
`references/examples/answer/` (`valid/`, `invalid/`, each invalid one named for its one fault).
Its fields: `answer_version` 1; `run_id` (this run's); `session_id` (the adapter's
`answer_fields.session_id`, never typed); `feature`, `title`, `intent`; `questions` (each `id`,
`text`, `touches` (ledger ids), `answer`; a blank answer is unanswered); `lines` (each `text`,
`tag` of `requirement`, `constraint` or `out-of-scope`, an optional `id` a slice names, its
`trace` of `kind` and `ref`, and an optional `row`, the id of the ledger row the line decides,
settles, passes forward or moves); `criteria` (each `text`, `verify` in one of the three forms below,
and the `id` a slice names);
`slices` (each `name`, `short`, `goal`, `requirements` and `criteria` (ids), `footprint`,
`not_in_slice`, `depends_on`); `assumptions`; `open_questions`; `ceremony` (`needs_build_doc`
and `why`); and `collapsed_gate` (`words`) only when the owner's invocation collapsed the gate.
With `needs_build_doc` true the answer names its `feature`, `title` and `intent` and holds at
least one constraint line.

`record-answer` checks in this order, and on any failure writes nothing and leaves the run at
`harvested`, so a corrected answer can be recorded:

1. The schema: exit 4, the findings on stdout. A trace and a `verify` are optional in the schema
   so that a line with no trace and a criterion with no check reach the content check and are
   refused by name; all five shared trace kinds are spelled so that `assumed` is refused as a kind
   this core does not allow (assumptions have their own field). An `owner_words` trace's `ref` is
   the owner's words quoted verbatim, and a blank one fails the schema.
2. The shared refusals of E14-11, `station_core/answer.py`'s `check`, called once on a view of the
   answer (its questions, and its lines, each with its ORIGINAL text (round 5, R3): the shared forms
   own every decoration, a section label such as `Constraint:` included, and an item label, BARE
   (`R4 `, `R12.3 `) or MARKED (`R12: `, `R2 <dash> `, `(R2)`, in any case), is part of the words on
   both sides whenever both carry one (ruling A5(1)), so `R4 budget approval` and
   `R4: budget approval` are not the parked `R3 budget approval` and `R21 storage` is not the parked
   `R2.1 storage`, while `R12.3 W` is the parked `W` and a plain `budget approval` is the parked
   `R3 budget approval`; the doc renders the text as written. A line may name its ledger row by `row`,
   which the view hands through unchanged: the row's id is the trace, so the line is judged by that
   id and its words are never matched against the row it names (ruling A5(4)). Each line is tagged by its own kind: a requirement and a
   constraint `decided`, since they are what the doc asserts as settled; an out-of-scope line
   `out-of-scope`, since carrying a parked scope line or a deferred architecture line forward as
   out of scope is the pass-forward E14-11 names, never a resolution) against `ledger_view`, with
   the allowed kinds below. Its rules: a question that re-asks a decided line (by id, or by its text);
   a question touching an id the ledger does not hold; an untraced line (no trace, a kind not
   allowed, a ledger id that names nothing, a path not in the workspace, a question not answered
   in this run, a blank quote); a `row` naming no line of the ledger (`unknown-line`); a
   requirement or constraint tracing to, or naming by `row`, a `parked` or `open` line that no
   answered question settled (`quietly-resolved`); a requirement or constraint whose words restate a
   `parked` or `open` line it does not name, whether or not an answered question touched that line
   (`quietly-resolved`, the frame's guard: an answered question does not substitute for the row id).
3. This core's own checks, each a refusal in the same `{"rule", "message", ...}` shape:

| Rule | Refuses |
|---|---|
| `session-mismatch` | a `session_id` other than the input's `invocation.session_id` |
| `run-id-mismatch` | a `run_id` other than this run's |
| `criterion-without-verify` | a criterion with no `verify` form, or one that is none of the three forms below (a bare `verify:`, free text, a blank or multi-line one) |
| `open-item-descoped` | an out-of-scope line that carries a scope `Open:` item that no answered question of this run touched, by its id (the row the line names by `row`, or a ledger trace to the item) or by its words, whatever the trace (round 3, R3); and one that carries an item by its words without naming it by its id, even after an answered question of this run touched the item: descoping moves a ledger row, so the line carries the row's id and the answered question does not stand in for it (A13, under A5(4)); an item named by its id and touched by an answered question goes out of scope, whatever the line's words. The words are read through the frame's own readings on both sides, never a comparison of this core's (round 4, R1): any reading of the line (`station_core.answer.forms` of the line as written, of the line without a leading list mark or section label such as `Out of scope:`, and of the item before its reason, cut at the first dash, colon, semicolon, comma or parenthesis from those words and from the line's bare words with the frame's label of the line (`station_core.answer.label`) put back in front) equal to any reading of the open row (`row_forms`), so a trailing period, a list mark, an invisible character, a ledger tail or a decorated row hides nothing. An item label, bare or marked, is part of the words in every reading, keyed through the frame's `label()` (round 5, R3; ruling A5(1)): no reading of a labelled line is label-free, so `R4 sensor calibration: not now` and `R4: sensor calibration: not now` are not the open `R3 sensor calibration`, and `sensor calibration: not now` is. A new line that only shares a word with an open item is not the item. An open item is the owner's call, not a descoping |
| `parked-line-unnamed` | an out-of-scope line whose words restate a `parked` row of the ledger view (a parked scope line, or a deferred architecture line, which the view tags `parked`) that the line does not name by its id (`row`, or a ledger trace to the row), whether or not an answered question of this run touched that row: a parked or deferred line passes forward only by its id and its words alone are refused (E14 punch list, the owner's ruling on A5(4) and E14-11); the refusal names the row's id. The words are read as for `open-item-descoped` (the frame's readings on both sides, the item before its reason); a line that names one parked row by its id and restates the words of another is refused naming the other. A line matching no parked or deferred row is a new line |
| `duplicate-id` | two lines, two criteria or two slices sharing an id or a name |
| `unknown-id` | a slice naming a requirement line, a criterion or a slice (`depends_on`) that neither the answer nor the existing doc holds |
| `depends-forward` | a slice depending on itself or on a slice after it |
| `unplaced` | with a build doc: a requirement line or a criterion no slice carries |
| `no-slice` | `needs_build_doc` true with no slice |
| `slices-without-build-doc` | `needs_build_doc` false with slices |
| `feature-not-hunted` | a `feature` other than the name the build hunt ran with |

Allowed trace kinds: `ledger`, `repo_path`, `question`, `owner_words`.

`owner_words` is the discussion before the run: a requirement, constraint or out-of-scope line the
owner stated before the invocation carries his words, quoted verbatim, as its trace, so he is never
asked it again (ruling R1 of round 2; the station's rule 1 lets a line trace to the discussion).
`assumed` stays refused for these lines: what the executor decided alone is an `assumptions` item.

Verify forms: `existing test <name>`, `new test at <path>`, `manual: <steps>`.

A `verify` is exactly one of those three, on one line (round 3, R4):

- `existing test <name>`: the test named, one token with no space (`tests/test_x.py::test_zero`,
  `test_x.Counter.test_zero`, `test_zero_on_start`). `existing test` alone is not a form.
- `new test at <path>`: a path that looks like one, one token with no space holding at least one
  `/` or ending in a file extension (`tests/test_x.py`, `tests/counter/`).
- `manual: <steps>`: the steps, at least two words.

After the form's prefix the rest must hold at least one letter or digit (round 4, R2): a token of
punctuation alone names nothing (`existing test ?`, `new test at /`, `manual: - -` are refused).

A placeholder (`TBD`, `TBA`, `TODO`, `n/a`, `none`, `later`, `pending` and the like), whole or as a
part of the path, names nothing and is none of the forms. The forms are the build doc template's;
any other text ("will be tested later", a bare `verify:`, `new test at some point`, `new test at
TBD`, `manual: TBD`, `existing test will cover it`) is a criterion a grader could not check, refused
`criterion-without-verify`.

Exit 5 lists every refusal of steps 2 and 3 at once. Only a clean answer is recorded, through
`answer.record`, which writes `answer.json`.

## 8. Write

- **`needs_build_doc` false:** nothing is written and the run stops `no-build-doc`, the
  executor's why carried (the station's "this does not need a build doc").
- **A new doc:** `templates.render_build_doc` renders it from the answer: the title
  (`<title>`, the run date), `Intent:`, `Constraints:`, `Out of scope:`, each slice's `Goal`,
  `Requirements` (each requirement line's text, verbatim), `Acceptance criteria` (each criterion's
  text and `verify:` form), `Footprint` (the list joined by `, `), `Not in this slice`, `Depends
  on` (`nothing`, or `Slice X, Slice Y`) and `Status: not started`, then the five ledger sections
  scaffolded EMPTY. The `Constraints:` value is the constraint lines joined by `; `, then
  `Assumed: ...` and `Open: ...` when the answer holds assumptions and open questions: the build
  doc's form has no other field for them, and there the builder and the inspector see them.
- **An existing doc is extended in place** where it lies: each slice of the answer is appended
  after the last slice and before the ledger sections, or replaces the slice of the same name
  where it stands; the answer's constraint, assumption and open-question texts not already in the
  `Constraints:` line are added to it, and its out-of-scope lines not already listed are added
  under `Out of scope:` (a one-item inline label becomes a list). Nothing the answer carries is
  dropped: a doc with no `Constraints:` line gets one, inserted after its `Intent:` line (after the
  title when it has none); and an item counts as already there only when it equals, whole, an item
  of its OWN kind in the line (round 3, R1): the value is read in runs, the constraints before the
  first `Assumed:` or `Open:` marker and each marker's run to the next, each run cut at `; `. An
  open question already written as an assumption or a constraint is still added as open, and every
  other pair of kinds likewise, so the doc and the read-back agree; a substring of an item is never
  an item. A new item joins its own kind's run: a constraint before the first marker, an assumption
  in the `Assumed:` run (a new one before `Open:`), an open question in the `Open:` run (a new one
  at the end). The doc's title and `Intent:` line
  are never rewritten from the answer. Every other byte stays as found, a heading the form does not
  know included, and the doc's line ending is kept. A revised slice's section is replaced whole.
- **Refused before anything is written:** a revision of an existing slice whose status is
  anything but `not started`, or that has no `Status:` line, stops the run `write-refused`, its
  `Status:` line quoted (or the slice named), before anything is rendered; then a proposed doc that
  would change, drop or add to any line under the five ledger sections, any `Status:` line of an
  existing slice, or any `Plan: inspected` line stops the run `write-refused`, the lines quoted. A
  `Status:` or `Plan: inspected` line is known by its label in any case and at any indent, so a
  hand-typed `status: built` or ` Status: built` is protected as `Status: built` is. A doc whose bytes changed after `harvest`
  (edited by hand, or created by another run) stops `stale-harvest`. A target that is a link, or
  whose folder resolves outside the workspace, stops `unsafe-path`. Every rendered document
  validates (round 5, R1): the proposed doc must pass `templates.check("build-doc", text)` before
  any document write, and the existing doc's own form findings are no exemption (they are never
  subtracted). A proposed doc with any finding stops the run `write-refused`, every finding named in
  the reason, an empty receipt written and nothing else (no document, no report-only proposal); the
  doc stays byte for byte as found. An existing doc that fails its form (a changed label, a
  malformed stamp, a re-cased `Status:` line) is fixed by hand before a run extends it.
- **The receipt:** `receipt.json` in the run directory names every write (`path`, `kind`,
  `sha256_before`, `sha256_after`); the doc is written through a temporary file and a rename.

## 9. Own commands

| Command | Does |
|---|---|
| `choose` | records the owner's pick among a hunt's `several` candidates: `--hunt`, `--path` (one of the listed candidates, exactly), `--words` (his words, verbatim, one line). Only after `select` and before `harvest`, and only on a `several` outcome; anything else is exit 2 with nothing written. Writes `chosen: {path, by: "owner", words}` into `selection-<hunt>.json`; the outcome stays `several`, so the result shows a pick the owner made, never the script |

## 10. Report and the read-back

`report` builds `result.json`, validates it against `references/result.schema.json` and the
semantic checks (S1 to S4) before writing it, and prints it. `writes` lists every run artifact
and the receipt's document write. `station_result`: `feature`, `doc`, `doc_action` (`created`,
`extended`, `none`), `slices` (the slice sections the doc holds after the write, counted by the
script), `slice_names`, `new_slices`, `open_questions` and `assumptions` (counted by the script
from the answer), `questions_asked`, `scope_doc`, `architecture_doc`, `needs_build_doc`,
`collapsed_gate`, `refused_lines` (on `write-refused`) and `readback`.

`readback` is the `BLUEPRINT:` block rendered from the result, the station's own form:

```text
BLUEPRINT: <feature>
Doc: <path>  ·  Slices: N  ·  Open questions: N  ·  Assumptions: N

Slice <name> <dash> <short name>      (one line per slice the doc holds)

Open: <each open question, one line each>
Assumed: <each assumption, one line each>
Next: build-v2 slice <the first slice of this run> when ready.
```

A report-only run says so under the `Doc:` line; a collapsed gate adds `Gate collapsed by the
owner's words: <words>`; a stop renders `Stopped: <tag>` and its reason, and `no-build-doc`
renders `No build doc: <why>` with the open questions and assumptions. The `SKILL NOTE:` line
stays the executor's to add in chat.

## 11. Report-only

Every phase and `choose` read `report_only` from the run's input. In that mode nothing is written
outside the run directory: `write` keeps the proposed doc as `proposed-build-doc.md` in the run
directory and its receipt names what it would have written (`would_write`); the result says
`wrote_nothing: true`. The run still selects, harvests, checks the answer and guards the protected
lines, so what it would write is reported, not written.

## 12. Stop tags

| Tag | When |
|---|---|
| `selection-several` | shared: a hunt found several candidates and no `choose` settled it; listed, never picked |
| `ledger-refused` | shared: the scope doc holds a line the ledger reader cannot tag, or the architecture doc's poured-concrete or deferred section holds a line the reader cannot read (section 6); quoted |
| `write-refused` | shared: the write would change a protected line, or the proposed doc fails its form (section 8); quoted, nothing written |
| `no-build-doc` | own: the answer says this does not need a build doc; no file |
| `stale-harvest` | own: the build doc's bytes changed after harvest; nothing written |
| `unsafe-path` | own: the build doc's path is a link or leaves the workspace; nothing written |

This core never emits `phase-not-built`, `selection-none` or `records-refused`.

## 13. Records

Records: none (E14-9). A fresh or extended build doc carries no finding and no card move, so
blueprint-v2 writes no event and never opens the records component. Its tests read the component
once, through the resolver and the CLI only (`import-legacy --dry-run` on a scratch copy, which
writes nothing), to prove the importer reads the rendered doc; the station itself never does.

## 14. Readers

None. The station summons no reader: it builds no `readers` request, so no `authorized` flag ever
arises, and `owner_word` in its input is carried and never read.

## 15. The gate

`report` is the last command. The executor posts the read-back and stops; it never starts the
build. A collapsed gate in the owner's invocation ("blueprint it and build slice A") is the
executor's to act on; the answer's `collapsed_gate.words` records that it was collapsed and by
which words, and the script acts on nothing.

## 16. Seeded families

Facts only; the outcomes are in the answer key.

| Family | What it drives | The facts |
|---|---|---|
| L1 traceability | the recorded answers against the case's scope doc: the shared refusals through the library, and (lane case L1-03) the real `record-answer` on the answer translated by renaming | `answer_refused`, `refusal_rules`, `answer_written`; `refusal_reason` (this core's own rule names) |
| L2 the forms | the build doc's form and round trip; (lane case L2-02) a full run on a scratch copy of the case with one more slice | `form_holds`, `round_trip_identical`; `extended_in_place`, `protected_lines_identical`, `importer_reads` |
| L3 document selection | `select` through the real CLI | `selection_outcome`, `selection_candidates` |

`evals/seeded-cases/lane_observe.py` produces the lane facts; its docstring states the
translation.

## 17. Exit codes

Station-loop section 2's, unchanged: 0 a phase did its work; 1 a defect; 2 usage (a missing
argument, a file that is not there or not JSON, the wrong phase, a hunt not run, a `choose` that
does not fit); 3 `jsonschema` missing; 4 an answer that fails its schema; 5 an answer refused on
its content; 10 a terminal status.

## 18. What this core never does

It never judges a plan, never asks the owner anything itself, never opens the records component,
never builds a reader request, never reads a v1 station's files or defers to one, never writes
outside the run directory except the one build doc, never changes a protected line, never picks
among several candidates, never calls a model, never touches the network, and never starts
another station.

## 19. Interface

This document closes `scripts/blueprint.py`'s CLI; this section states it in one place, in tables a test
reads (`scripts/tests/test_interface_document.py` extracts each table below by its heading and
fails when the code, the schemas or this section disagree). Added in E14 slice 3c (the join,
contract section 13; build-v2's section 19 is the model). Nothing here changes what the core does:
every row restates the driver's parser and dispatch, `station-loop.md` sections 2 and 5, the input
schema, and the names the code joins onto the run directory. Numbered 19, as in build-v2's contract and every front core's, so one heading names the interface in each; the open points follow as section 20.

### Commands

| Command | Arguments | Exit codes |
|---|---|---|
| `check-input` | `<input.json>` | 0, 1, 2, 3, 4 |
| `select` | `--run-dir D [--hunt NAME] [--name NAME]` | 0, 1, 2 |
| `harvest` | `--run-dir D` | 0, 1, 2, 3, 10 |
| `record-answer` | `--run-dir D --answer FILE` | 0, 1, 2, 3, 4, 5, 10 |
| `write` | `--run-dir D` | 0, 1, 2, 3, 10 |
| `report` | `--run-dir D` | 1, 2, 3, 10 |
| `identity` | `<workspace>` | 0, 1, 2 |
| `skill-identity` | none | 0, 1, 2 |
| `choose` | `--run-dir D --hunt NAME --path P --words TEXT` | 0, 1, 2, 10 |

Every command also takes `--skill-root DIR` (test only) and `--records-root DIR` after its name.
The exit codes of a row are the codes that command's code can return, as the test reads them from
the source (the handler, its decorators and every function of this core it calls); each means what
`station-loop.md` section 2 says, and 1 (a defect) and 2 (a usage slip) are every command's.

### Result statuses

| Status | Terminal status |
|---|---|
| `completed` | `completion` |
| `stopped` | `stop` |

### Invocation fields

The input's `invocation` object, which the adapter's `invocation.py` fills (`../adapters/README.md`),
never the executor.

| Field | Required | Values |
|---|---|---|
| `harness` | yes | a string, or null: the harness the run is driven from |
| `caller` | yes | `user` on a direct request, or the name of the station that called this one |
| `mode` | yes | `direct` when a person asked, `station` when another station drove the run |
| `session_id` | no | the session the adapter READ from the harness's own record, or null; the recorded answer names the same session |

### Run-directory artifacts

Every name this core's code joins onto `run_dir` (`*` is the slot a name fills), a folder with `/`.

| Artifact | Written by |
|---|---|
| `answer.json` | `record-answer` |
| `checkpoint.json` | `check-input`, then every phase and `choose` |
| `harvest.json` | `harvest` |
| `input.json` | `check-input` |
| `proposed-build-doc.md` | `write` (the rendered build doc; in report-only the one copy) |
| `receipt.json` | `write` |
| `result.json` | the phase that ends the run |
| `selection-*.json` | `select` (`*` the hunt); `choose` records the owner's pick in it |

## 20. Open points

- The build doc's `Footprint:` is the template's one-line form (`Footprint: a, b`); `build-v2`'s
  reader reads named paths only from a bulleted list under a bare `Footprint:` label, so it reads
  no named paths from this line. The form is E14-12's and does not move here; the seam is
  reported for the control room.
- Assumptions and open questions live in the `Constraints:` line (section 8), the form offering
  no other field before the ledger sections.
