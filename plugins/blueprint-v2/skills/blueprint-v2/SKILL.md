---
name: blueprint-v2
description: >-
  Draft a build document in dependency-ordered, verifiable slices from a feature discussion: the
  doc that build executes slice by slice and signoff grades against, every requirement carrying
  its trace to the scope doc, the repo, or a question answered in the run. Use when the user says
  draft a build doc, blueprint this, slice this up, write the build plan, or finishes discussing
  a feature and wants it scoped into slices. Not a plan check (inspect-v2), not the build itself,
  and not the bare /blueprint command, which belongs to the v1 station.
---

# Blueprint v2

The front of the build loop: this station draws the plans, the build station frames them one slice
at a time, the signoff station inspects the work. It turns a feature discussion into the build doc
the downstream stations (build, signoff, recheck, inspect) consume, written for a builder who was
never in the room.

**The spine.** The doc records what was decided; it does not decide. Every requirement traces to
the scope doc, the repository, or a question asked and answered in this run. The most useful doc
is self-contained: real files, real interfaces, explicit out-of-scope, every criterion checkable,
because a fresh session with no memory of this conversation must be able to execute it.

**The one unforgivable move is faux context:** padding the doc with plausible requirements,
rationales or criteria the discussion never established. The build station treats this doc as the
only source of requirements and signoff grades against it, so invented detail becomes law. When
something is unknown, ask or mark it open; never make it up.

**You decide, the script records** (E14-4). You talk to the owner, ask, slice and judge, and hand
your judgment to `scripts/blueprint.py` ONCE, as the recorded answer. The script finds the
documents, reads the ledger, checks your answer, renders the doc through the shared templates,
guards its protected lines, writes, and reports. You never type the doc; the script renders every
load-bearing form. It writes no event and never opens the records component.

`references/blueprint-v2-contract.md` is this station's contract; `references/station-loop.md` is
the one the four front stations share. Read both before a first run.

## Running the script

Run every command as `uv run scripts/blueprint.py <command> ...`, the script resolved against this
skill's root (the directory holding this file); `uv run` supplies the one declared dependency. Every
command prints one JSON document. Exit 0: continue. Exit 10: the run reached its terminal status
(a completion or a stop): read `status`, `stop_tag` and `reason`. Exit 2: a usage slip of yours:
read stderr, fix the command, run it again. Exit 4 or 5: your answer was refused (step 4). Exit 3:
`jsonschema` is missing: use `uv run`. Exit 1: a defect: report it, never work around it.

## Step 1: Harvest

Mine what already exists before asking anything.

1. **The input.** Read `adapters/README.md`: it names the helper of the harness you run in. Run it
   and put its `invocation` object into the input whole; type none of its fields. Write the rest
   (`input_version` 1, a fresh `run_id`, the workspace (the repository root), a fresh `run_dir`
   outside the workspace, `report_only` when the owner asked what the doc WOULD be) and run
   `check-input <input.json>`. Exit 4 lists what is wrong; fix the file and run it again.
2. **The documents.** Name the feature's slug (lowercase letters, digits, `-`, `.`, `_`), then run
   `select` three times: `select --run-dir D --hunt scope`, `select --run-dir D --hunt architecture`
   (add `--name <slug>` to narrow either to the feature), and `select --run-dir D --hunt build
   --name <feature>` (the name is required: the living doc is looked for under it). An outcome
   `several` is listed for the owner and never picked by you or the script: put the candidates to
   him, and record his pick with `choose --run-dir D --hunt <hunt> --path <the candidate> --words
   "<his words, verbatim>"`. Only `several` takes a choice. `none` is not a stop: no scope doc is an
   empty ledger, no build doc means a new one.
3. **Read it.** Run `harvest --run-dir D`. It prints the scope doc's ledger (every line with its id
   and tag: its decided lines are settled ground, its out-of-scope lines are descope evidence), the
   architecture doc's poured-concrete lines (decided) and deferred lines (still open), and an
   existing build doc's slices, `Status:` lines, `Plan: inspected` lines and ledger sections. A
   stop here (`selection-several`, `ledger-refused`) ends the run: report it to the owner.
4. **The rest is yours to read:** the discussion (decisions made, options rejected, constraints
   stated, names used), the repository (the test command, the components and conventions to reuse,
   real file paths), a wargame doc if one exists (its verified failure modes become constraints and
   criteria). An existing build doc is extended, never forked.

## Step 2: Interview

Ask about load-bearing gaps only: choices that shape the architecture, the data, a user-visible
contract or a slice boundary. Batch them into one round of a few questions, each with your
recommendation attached. Never ask about a decided ledger line or a poured-concrete line: they pass
forward by their id, and a question that touches one, or repeats its text, is refused. Small
reversible gaps do not earn a question: decide, and record the assumption. Invoked cold with no
prior discussion, this step is the discussion: interview until the shape is settled.

Keep, for the answer, every question you put with the ledger ids it touches and the owner's
answer (a question he left unanswered settles nothing).

## Step 3: Slice

- **Size:** one slice is one build session: a coherent piece one session completes and verifies in
  a sitting. When in doubt, smaller.
- **Order:** dependency-ordered: data before services, services before surfaces. The earliest slice
  that can prove the feature end to end comes as early as possible. A slice depends only on
  earlier slices.
- **Ends wired in:** every slice leaves the system integrated and demonstrable.
- **Independently verifiable:** each slice carries criteria checkable at that slice, never "will
  be tested later".
- **Ceremony scales:** a change describable in one sentence gets told so: "this does not need a
  build doc" is a valid outcome (`needs_build_doc: false`, with the why). A modest feature gets two
  or three slices, not eight.

## Step 4: Record the answer

Write ONE answer in the shape of `references/answer.schema.json` (examples under
`references/examples/answer/valid/`) and run `record-answer --run-dir D --answer <file>`:

- `session_id`: the adapter helper's `answer_fields.session_id`, never typed; `run_id`: this run's.
- `feature` (the build hunt's name), `title`, `intent`: the why the builder needs.
- `lines`: every requirement (`tag: requirement`, with the `id` its slice names; its text is
  rendered verbatim, so write it as the doc should read, `R1 <dash> ...`), constraint (stack,
  conventions, test command, hard requirements) and out-of-scope line (the deferred item and the
  reason it was deferred). Each carries its `trace`: `{"kind": "ledger", "ref": <line id>}`,
  `{"kind": "repo_path", "ref": <a path that exists>}` or `{"kind": "question", "ref": <an answered
  question's id>}`. Nothing else traces a line here.
- `criteria`: one measurable end state each, with its `verify` form (`existing test`, `new test at
  <path>`, `manual: <steps>`).
- `slices`: each `name` (A, B, ...), `short`, `goal`, the requirement and criterion ids it carries,
  `footprint` (the files expected to change), `not_in_slice`, `depends_on`. Reuse an existing
  slice's name only to revise a slice whose status is `not started`.
- `assumptions`, `open_questions`: one line each. An unanswered load-bearing question stays open.
- `ceremony`: `needs_build_doc` and why. `collapsed_gate`: only when the owner's invocation
  collapsed the gate, with his words.

Exit 4 (the schema) or exit 5 (the content: an untraced line, a re-asked decided line, a parked or
open line asserted with no question that settled it, a criterion with no check, a slice naming
what is not there, a feature the build hunt did not look for) lists every refusal and writes
nothing: fix the answer, or go back to the owner, and record it again.

## Step 5: Write, read back and stop

1. Run `write --run-dir D`. The script renders the doc (a new one at
   `docs/plans/<date>-<feature>.md`, or the living doc extended where it lies), the last five
   sections scaffolded empty and never pre-filled, and refuses before anything is written any
   change to a ledger-section line, a `Status:` line or a `Plan: inspected` line
   (`write-refused`), a doc edited after harvest (`stale-harvest`), or a path that leaves the
   workspace (`unsafe-path`). With `needs_build_doc: false` it writes nothing and stops
   `no-build-doc`.
2. Run `report --run-dir D`. It validates and writes `result.json` and prints it.
3. **Read back.** Post `station_result.readback` in chat as it is: the `BLUEPRINT:` block with the
   slice map, the open questions and every assumption. The owner corrects the map cheaply here; a
   wrong doc costs a build. When you worked around, reinterpreted or excepted a rule of this
   procedure, add one line `SKILL NOTE: <what and why>`; a clean run carries none.
4. **Stop.** Never start building. "Blueprint it and build slice A" in the owner's invocation
   collapses that gate: it is recorded in the answer (`collapsed_gate`), and acting on it is yours;
   the script never assumes it.

## The rules

1. **Record, never invent.** Every line traces to the scope doc's ledger, the repository, or an
   answered question. An unanswered load-bearing question stays visibly open.
2. **Write for a builder who was not in the room.** No "as discussed", no vocabulary the chat
   invented without defining it, no pronouns pointing at the conversation. Real paths, real names.
3. **Criteria are checkable or they are not criteria.** One measurable end state plus the stated
   check. "Works correctly" is a goal: make it observable or leave it in the intent.
4. **Requirements say what, slices say when, the builder decides how.** Never prescribe
   implementation detail the builder is better placed to choose.
5. **Descoping is recorded with reasons.** Rejected options and deferred work are out-of-scope
   lines with the why: that written evidence keeps signoff from flagging them as failures.
6. **Tests are part of the plan.** Criteria that can be tests name them; a slice with no runnable
   check is a smell to flag to the owner before the doc ships.
7. **One living doc.** One build doc per feature, revised in place. Never fork a parallel plan;
   never rewrite the ledger sections' history; the `Plan: inspected` lines are the inspect
   station's records and survive every revision.

## What NOT to do

- Do not invent requirements, rationales or criteria the discussion never established.
- Do not write criteria a grader could not check.
- Do not prescribe implementation detail, and do not leave load-bearing decisions unstated.
- Do not explode a small change into ceremony: recommend skipping the doc when it is not needed.
- Do not fork a second plan when one exists, and never pick among several candidates yourself.
- Do not pre-fill the ledger sections, type the doc by hand, or write anything shaped like a verdict.
- Do not start building. That gate is the owner's.

## Boundaries

- No web, no research, no model call and no harness launch from the script. This station summons
  no reader.
- The references: `references/blueprint-v2-contract.md` (this station), `references/station-loop.md`
  (the shared loop), `references/templates/build-doc.md` (the form, with its reading),
  `references/answer.schema.json`, `references/input.schema.json`, `references/result.schema.json`,
  and `adapters/README.md` (which adapter serves your harness).
