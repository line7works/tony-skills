---
name: inspect-v2
description: >-
  The plan-check station: adversarial review of a blueprint build doc BEFORE build runs it, by
  fresh inspectors chosen at summon, their packet built by script from the permitted documents
  alone and their surviving findings kept in the shared records. Use only when the owner types
  /inspect-v2 by name. Strictly user-invoked: never auto-invoke or suggest-invoke, no matter how
  ready a fresh blueprint looks. Not a review of built code (signoff-v2), not a fix, and not the
  v1 inspect station.
disable-model-invocation: true
---

# Inspect v2

The building department's plan check. blueprint-v2 draws the plans, build-v2 frames them,
signoff-v2 inspects the framing; this station checks the blueprints before ground breaks. A bad
plan approved is the loop's most expensive defect, because the builder builds the mistake
faithfully. Its slot: precon-v2, architect-v2, blueprint-v2, **inspect-v2**, build-v2.

**The spine.** There is no spec above the spec, so the rubric is three fixed lenses (traceability,
the code book, repo reality) and the findings come from fresh inspectors, never from you: the
session that summons may be the one that drafted the doc, and the drafter does not stamp his own
plans. The inspectors' mandate is to find reasons to REJECT the plan; a clean verdict states what
was hunted and not found.

**The one unforgivable move is inspecting the doc yourself and calling it a plan check,** or its
quieter twin, feeding the inspectors a summary instead of the record. The packet is built by the
script from the documents' bytes; you never add to it.

**You decide, the script records.** `scripts/inspect_v2.py` (resolve it against this file's
directory; run every command with `uv run`) validates, finds, packs, builds the readers requests,
verifies citations, talks to the records component and writes. You ask, summon, adjudicate and
hand your judgment over once, as the recorded answer. `references/inspect-v2-contract.md` says
what every command does; read it before Step 1 and again before Step 5.

Every command prints one JSON document and exits 0 (go on), 10 (the run reached a terminal
status: print the chat block it carries and stop), 2 (a usage slip of yours: read stderr, fix, rerun),
3 (a missing dependency: `jsonschema`, the records component or readers; read stderr), 4 (a file you
supplied failed its schema: fix it), 5 (refused on its content: nothing written; read the refusals),
or 1 (a defect: report it, never work around it).

## Step 1: The ask, and the input

The owner's word for an outside inspector is data in this run's input, so the ask comes first.
Mint a run id. Summon `/readers suggest claude-session,gpt-astra,gemini,deepseek,qwen --run <run id>`
and ask ONE plain-text numbered question (never a harness question tool), each row beside the
model `suggest` shows for it, whether it is outside, and any drop note:

1. **Claude** (recommended): row `claude-session`, fresh readers on this account, the three lenses
   as one fleet. Needs no word.
2. **GPT**: row `gpt-astra`, at the model `suggest` showed; another GPT model is an id the owner
   types against this row, never another row.
3. **Gemini**: row `gemini`. 4. **DeepSeek**: row `deepseek`. 5. **Qwen**: row `qwen`.

Rows 2 to 5 are outside: each runs only on the owner's answer in this run naming it. Wait for the
answer; silence never proceeds and the recommendation is not a trigger. One paper inspector per
run: an answer naming several lanes is several runs, one after another, each with its own run id,
its own `suggest` and everything after it. Nothing is remembered between runs.

Then write the input (`references/input.schema.json`): `workspace` the repository root,
`run_dir` a fresh absolute directory outside it, `staging` the pre-repository home when the owner
keeps scope docs there, `report_only` when he asked what an inspection WOULD find. Take the
`invocation` block whole from your harness's adapter (`adapters/README.md`), typing none of it.
Under `station`: `row` the row he named, `displayed_model` the model the ask showed for it,
`model` only when he typed an id, `session_model` your own model id as your system prompt states
it. For an outside row, `owner_word` is `{"rows": [<the row>], "words": "<his words, verbatim>"}`.

```sh
uv run scripts/inspect_v2.py check-input <input.json>
```

## Step 2: Gate and hunt

```sh
uv run scripts/inspect_v2.py select --run-dir D --hunt build --name <topic>
uv run scripts/inspect_v2.py select --run-dir D --hunt scope
```

`--name` is the topic the invocation names (`docs/plans/<date>-<topic>.md`, then the flat
`docs/<topic>-build-plan.md`, then a phase or slice doc; nowhere else). Read both results. The
build hunt: `none` means there is nothing to inspect (a plan that lives only in this conversation
is not inspectable; point at blueprint-v2 and stop); `several` is a list-and-ask, never a silent
pick. The scope hunt is by glob, never by a guessed slug: match its candidates to the feature by
their `Intent:` lines; an ambiguous match is a list-and-ask. Record a match or the owner's pick:

```sh
uv run scripts/inspect_v2.py choose --run-dir D --hunt scope --path <candidate> --by intent
uv run scripts/inspect_v2.py choose --run-dir D --hunt build --path <candidate> --by owner --words "<his words>"
```

Then harvest (the documents, the scope doc's ledger, the code book, the records component):

```sh
uv run scripts/inspect_v2.py harvest --run-dir D
```

Only a scope hunt that found nothing applies the no-record rule: the run still inspects, and is
weaker without a precon doc. A doc with missing sections or malformed forms still inspects: that is
what the code-book lens exists to find. Slices past `not started` still inspect, with a note.

## Step 3: The lenses

```sh
uv run scripts/inspect_v2.py packet --run-dir D
uv run scripts/inspect_v2.py request --run-dir D --suggest <this run's suggest output, saved as JSON>
```

`packet` builds one fresh directory per lens, holding exactly the numbered build doc, scope doc (or
the no-record line) and code book. Never add, remove or edit a file there: `request` refuses a
packet holding anything else (exit 5, the file named, nothing built). `request` prints one request
file per lens; if it stops `model-changed`, show the owner the line and wait for his word.

Summon `/readers` with those request files, unchanged, as one fleet under the run id: in the Claude
lane, the traceability, code-book and repo-reality calls; in an outside lane, the one paper call
(its `authorized` set by the script from his word, never by you) and the repo-reality call. Keep
each call's `READERS:` line and result JSON. An outside call's raw copy lands under
`docs/reviews/`; the script prepends its banner at `write`.

**The lane-down rule.** A `READERS:` status other than `ok` on any call of the fleet means the lane
cannot run: record the answer with that status and reason (the run stops `lane-down`, nothing
triaged), report it, and re-ask. The lane he names runs as a fresh run. Never substitute a lane,
never retry without his word.

## Step 4: Verify and adjudicate

Read every reader's reply. Then write ONE answer file (`references/answer.schema.json`) and hand it
over:

```sh
uv run scripts/inspect_v2.py record-answer --run-dir D --answer <answer.json>
```

It carries `session_id` (the adapter's `answer_fields.session_id`, typed by no one), `run_id`,
`row` (and `owner_word` for an outside row, as the input carried it), `lanes`, `questions` you put
to the owner this run (none re-asking a decided scope line), and `results`: one per call, copied
from its `READERS:` line and reply: `call_id`, `row`, `effective_model`, `status`, `raw_path`,
`isolation`, `parity`, and every finding the reader reported (`severity`, `location` as the
reader cited it, `claim`, `scenario`, `confidence`, `quote` when the reader quoted the line, `lens`
when an outside reply says which paper lens). A concern without a location goes in with a null
location; it never reaches the verdict.

Verify every BLOCKER and MAJOR, and every outside finding of any severity, against the cited
lines yourself, and record each verdict in `adjudications` (`<call id>#<n>`: `confirmed`,
`plausible`, `refuted` or `question`, each with its why). The script refutes, mechanically, every
citation that matches nothing in the numbered packet, and turns untraceable items into questions
when there is no scope doc; it never keeps a refuted citation on your word. Dedupe is the
script's. Add `hunted_and_held` (what the inspectors attacked that held up) and `bottom_line`.

Exit 5 lists what was refused; nothing was written, so fix the answer and record it again. Exit
10 is a stop: print the chat block and stop.

## Step 5: The verdict and the two writes

```sh
uv run scripts/inspect_v2.py write --run-dir D
uv run scripts/inspect_v2.py report --run-dir D
```

`write` raises each surviving finding in the records component (`raised_by` the reader's effective
model), places the component's rendered block at the punch list's tail with the station's QUESTION
lines, or the clean line on a clean run, writes the stamp `Plan: inspected <date> by <model> ·
<counts>` by v1's placement rule, and files the verdict mirror under `docs/reviews/`. `report`
validates the result and prints the chat block. Print it, add nothing a script did not say, and stop.

Never: a `Status:` line, a verdict word in the build doc, an edit to the plan, a fix, a re-slice, a
clear of any finding. The owner adjudicates; the drafting session amends on his word; a
re-inspection is a fresh run. No invocation wording collapses that gate.

## The rules

1. **Summon only.** The owner types it; never because a blueprint landed.
2. **Fresh inspectors originate; you merge, verify and adjudicate.** Never a finding of your own.
3. **The packet is the record.** The documents by their bytes, never a summary or chat context.
4. **The ask is real.** Every run; wait for the answer; per run only.
5. **Evidence or it does not count.** Every finding carries its location; every BLOCKER and MAJOR
   is verified before the owner sees it.
6. **No record is not invention.** Untraceable items without a scope doc are questions, never
   automatic BLOCKERs.
7. **Stop at the verdict.** The records block, the station's lines, the stamp and the mirror;
   nothing else is touched.
8. **The stamp names the model** the readers' result carries; never an id you did not launch.
9. **The review mechanics are this station's contract** (`references/inspect-v2-contract.md`
   section 2): the finding shape, verify before reporting, severity to verdict, report and never
   repair, the additive ledger. One stated exception: signoff's model floor does not bind here; the
   lane the owner picks is the floor and the stamp is the trust label.
10. **Anti-rubber-stamp.** A clean verdict states what was hunted and failed to find.

## Output

The chat block `report` prints (v1's read-back, rendered from the result):

```text
INSPECT: <doc path>
Verdict: APPROVED | APPROVED WITH CONDITIONS | REJECTED
Inspector: <row · effective model id · isolation label>  ·  Scope doc: <path | none — no-record rule applied>  ·  Refuted: N
Raw: <raw path | n/a — Claude lane>
Findings: N BLOCKER · N MAJOR · N MINOR

Bottom line: <2-3 sentences: the plan's state and what to do next>

BLOCKERS   <severity · path:line · claim · scenario · CONFIRMED/PLAUSIBLE>
MAJOR
MINOR
Questions: <no-record confirmations and calls for the owner>
Hunted and held: <what the inspectors attacked that held up>
Next: <APPROVED: build-v2 when ready; else the owner adjudicates, the drafter amends, a fresh inspect-v2>
SKILL NOTE: <only when a rule was worked around, reinterpreted or excepted: what and why>
```

## What NOT to do

- Don't auto-invoke or suggest this station; don't inspect the doc yourself and call it a plan check.
- Don't put anything in a packet directory, and don't summarize the discussion for a reader.
- Don't proceed without the ask's answer, and don't remember it between runs.
- Don't type `authorized`, a model id, an effort, a sandbox or a transport: the request files and
  readers' roster carry them.
- Don't substitute a lane when the chosen one is down: report the status and reason, and re-ask.
- Don't let a locationless or unverified BLOCKER or MAJOR reach the verdict.
- Don't auto-BLOCKER untraceable items when no scope doc exists: those are questions.
- Don't borrow signoff's verdict words: APPROVED-family here, SIGNED OFF-family there.
- Don't edit the build doc, a `Status:` line, the records log or a raw copy by hand.

## References

| File | Read it | For |
|---|---|---|
| `references/inspect-v2-contract.md` | before Step 1 and before Step 5 | every command, the mandates, the verify rules, the writes, the stops |
| `references/station-loop.md` | once | what the four front stations share |
| `references/input.schema.json`, `references/answer.schema.json` | before Steps 1 and 4 | the two documents you write |
| `references/result.schema.json` | when a result is unclear | what each field means |
| `references/inspect-mandate.md` | never needed at run time | the outside mandate the script fills |
| `adapters/README.md` | before Step 1 | the helper that prints your `invocation` block |
