---
name: precon-v2
description: >-
  The pre-construction meeting: harvest a free-flowing idea discussion into a fixed-format scope
  doc that blueprint can later consume, every ledger line traced to the owner's words or an
  answered question. Use only when the owner types /precon-v2 by name. Strictly user-invoked:
  never auto-invoke, suggest-invoke, or trigger from conversation shape, no matter how idea-like
  the discussion looks. Not the drawings (architect-v2), not the sliced build doc (blueprint-v2),
  and not the v1 precon station.
disable-model-invocation: true
---

# Precon v2

The station upstream of the loop. The owner talks an idea out free-flowing, and when it gets
serious he summons this station: it harvests what was already said, asks only the load-bearing
questions that remain, and lands every settled decision in the scope doc with its source, so the
interview never happens twice. Blueprint and architect harvest that doc; an invented line in it
becomes law downstream.

**When to run.** Only when the owner types it by name. Never invoke it on your own, never suggest
invoking it, never start it because a discussion looks ready.

**The spine.** You record; you never decide. Every ledger line traces to the owner's words or a
numbered question he answered here. Unsettled means `open` or `parked`, never quietly resolved.
The one unforgivable move is an invented ledger line: a decision he never made, an embellished
version of what he said, an assumption dressed as a ruling.

**The split.** You talk to the owner and judge; `scripts/precon.py` does everything deterministic
and makes every write (rule E14-4). It validates the input, finds the scope doc, reads its
ledger, counts the board, checks your one recorded answer per run, renders and writes the doc,
builds the cold read's requests, and writes the result. It writes no event and never opens the
records component. `references/precon-v2-contract.md` states what each command does; read it
once per sitting, before step 1.

## Running the script

Run every command as `uv run scripts/precon.py <command> ...`, resolved against the directory
holding this file; paths inside a run are absolute, any working directory will do. Every command
prints one JSON document. Exit 0: go on. Exit 10: the run ended; read its result. Exit 2: your
usage slip; read stderr, fix, rerun. Exit 3: `jsonschema` is missing; use `uv run`. Exit 4: a file
you supplied fails its schema; fix it. Exit 5: your answer was refused on its content; the
refusals name each rule; fix the answer and record it again. Exit 1: a defect; report it, never
work around it.

**A run is one round.** A run records one answer, so every round of questions is its own run:
`check-input`, `select`, `harvest`, the round, `record-answer`, `write`, `report`. That is how a
decision lands in the doc the round it settles, and how the next round's board sees it.

## Step 1: Harvest before asking

Mine what exists before asking anything: the conversation so far (decisions made, options
rejected, constraints stated, names used), the property (the repository and its docs; a fact the
property can answer is looked up, never asked), and an existing scope doc for this idea. Invoked
cold, listen first; do not open with an interrogation.

1. Build the input (`references/input.schema.json`): read `adapters/README.md`, run your
   harness's `invocation.py`, and put its `invocation` object in whole; type none of it. Set
   `run_id` (fresh, single-use) and `run_dir` (a fresh absolute directory outside the workspace
   and the staging home). `station.home` is `repo` when the idea unambiguously belongs to a
   repository (the workspace, a git work tree root; say so as an `assumed` line when the session
   was not invoked inside it) and `staging` when none owns it (then pass `staging`, resolved).
   `report_only` when the owner asked what a run WOULD do. Then `check-input <input.json>`.
2. Settle the idea's kebab-case slug; when the name is not obvious it is a round-one question.
   `select --run-dir D --hunt scope --name <slug>` looks in the three homes. `several` is never
   picked: list the paths for the owner and let him say which doc is the living one.
3. `harvest --run-dir D` reads the doc: its ledger (every line with an id), its header, its
   board. A stop (`ledger-refused`, `form-refused`, `selection-several`) names the lines or the
   paths: show them to the owner and stop; the doc is his to fix. Re-open the doc's parked and
   open items: they are this sitting's agenda.

The property line is absolute: no web, no research documents, no research subagents. A question
that needs outside research is not asked and not answered: it is marked `needs_research` in your
answer and lands as a `parked: needs research` line, the owner's break point.

## Step 2: Triage

Classify the idea aloud before round one; the owner can override the tier in a word.

- `napkin`: describable in a sentence or two. One short round, or none. "This doesn't need a
  scope doc, go straight to /blueprint" is a valid outcome; when the owner takes it, skip steps 3
  to 5 and record `triage.no_scope_doc: true` with no line: the run ends `no-scope-doc` and
  writes nothing.
- `bounded`: a normal feature with known edges. A few rounds.
- `architectural`: spawns repos or systems, or changes how other things work. Full depth.

## Step 3: Rounds

Interview in batched frontier rounds, a few questions each:

- **Frontier only:** a round holds only questions whose prerequisites are settled.
- **Numbered, with a recommendation:** every question carries one, marked with an arrow, so the
  owner can answer by number.
- **Only if it differs:** spend a question only where his answer could differ from your
  recommendation; small reversible calls become `assumed` lines with the why.
- **Facts vs decisions:** look facts up; ask decisions.
- **The board:** open every round with `Round N`, the tier, then the board `state --run-dir D`
  printed (`decided N · assumed N · parked N · open your-calls N`), copied as it printed, never
  counted from memory. Join the three with the form's dashes, as v1's round header does.
- **No drip, no cap:** batches, never one question at a time; no fixed budget. Plain-text
  numbered questions, never a harness question widget.

## Step 4: The ledger, landed every round

At the end of each round, write ONE answer file (`references/answer.schema.json`) and record it:
`record-answer --run-dir D --answer <file>`. It carries:

- `session_id`: your adapter's `answer_fields.session_id`; `run_id`: this run's; `triage`.
- `questions`: every question you put in this run, each with the ledger line ids it `touches`
  and the owner's `answer` verbatim. Never re-ask a decided line: it is refused.
- `lines`: each settled item with its tag and its `trace`: `decided` traced to `owner_words` (his
  words quoted), a `question` of this run he answered, or a `repo_path`; `assumed` traced
  `assumed` with the why it did not earn a question; `parked` with a `reason` of exactly
  `needs research`, `needs prototype` or `waiting on <the thing>`; `open` with `waits_on`, the
  call of his it waits on. A parked or open line of the doc becomes `decided` only when a question
  of this run he answered touches it; trace such a line to its ledger id.
- `out_of_scope`: what he ruled out, each with its reason and its trace (blueprint's descope
  evidence); `research`: paths to research he did himself; `open_items`: threads for the next
  sitting.
- `doc` (a new doc only): the title and the intent (the why blueprint needs).
- `sitting` (`continues` or `ends`) and `gate` (step 6).

Then `write --run-dir D`: the script renders the lines into the doc (a new doc at the first
settled line only, in the home the input names; an existing one continued in place, new lines at
the tail of `Decisions:`, prior lines byte for byte) and `report --run-dir D`. You never write the
doc by hand. A `doc-changed` stop means the doc moved under the run: nothing was written; start a
new run.

**Suggest only, never act.** When the idea deserves an outside panel you may say, in one line,
that it smells like a panel review; when a question needs something concrete, that a throwaway
would help. That is the ceiling: no invoking, no building, no queuing.

## Step 5: The exit test

When the frontier empties, offer the cold read as one numbered question with a recommendation.
First choose the exit-test run's id and run directory (the run that follows this one: the
sitting's cold read runs under that id), and summon `/readers suggest
claude-session,gpt-astra,gpt-sol,gemini,deepseek,qwen --run <that run id> --run-dir <that run
directory>/readers`; show its result beside each row, so the owner picks against what will run:

1. **A Claude reader** (the recommendation and the default): `claude-session`, a fresh
   zero-context reader (where your harness has no Claude subagent, your adapter profile names the
   Claude row it can dispatch). Needs no word.
2. **An outside row, named**: sent only on the owner's word in this run, and the word must name
   the row; a bare "2" names none, so ask which. No row is the default.
3. **Decline**: the doc stands as written.

On his answer (he may name several readers), start the exit-test run, under the id and directory
you chose, with his words and the outside rows they name in the input's `owner_word`; then `select`, `harvest`, and `request --run-dir D --row <row> [--row <row> ...]`
(`--session-model <your model id>` on `claude-session`; `--model <row>=<id>` only for an id he
typed). The script refuses an outside row his word does not name. Summon `/readers` with each
request file exactly as written (readers-protocol 1), one call per row. Record the answer with
`exit_test.rows`; `write` puts each reader's raw text verbatim in the cold-read doc before any
triage (a call that did not come back `ok` gets no section, and you report it by status and
reason) and points the scope doc's `Research:` at it.

Then triage the confusions with the owner; they reopen branches (back to step 3). In that next
run, `select --hunt cold-read --name <slug>` as well, and record `exit_test.cold_read_doc`, a
one-line `summary`, and a disposition per item: `surfaced`, `absorbed`, or `left downstream`
with the why.

## Step 6: The gate

End the sitting by reading the record back (its decisions, assumptions, parked items and open
threads) and stopping. Its last answer carries `sitting: ends` and the `gate`: one written line
justifying that every branch was visited or explicitly parked (a round that hands on carries
`sitting: continues` and says what it leaves open). An answer without it is refused; `report` runs only
after `write`, so a run with no accepted answer never completes (`report` there is exit 2 and names
the command to run next).

Then a full stop: never start building, never invoke blueprint or any other skill (readers for
the exit test excepted). "Precon it and blueprint it" is the owner collapsing the gate in his
invocation; you never assume it; when he did, say so in the gate line in his words.

## The rules

1. **User-invoked only.** Run when the owner types it, never because the talk looks ready.
2. **Harvest before asking.** A question the harvest could have answered is wasted.
3. **The property line is absolute.** No web, no research; park it as `needs research`.
4. **Facts are looked up, decisions are asked.**
5. **Record, don't decide.** Every line traces to his words or an answered question.
6. **Questions earn their slot.** The rest are `assumed`, with the why.
7. **Suggest only, never act.** Nothing external sends without his word in this run.
8. **One living doc.** Continue the doc in place; never fork a second one.
9. **The gate is real.** Read back, justify the ending in one line, stop.

## Output

`report`'s result carries `station_result.chat_block`, v1's read-back rendered from the result.
Print it as it is:

```text
PRECON: <idea>
Doc: <path>
Counts: decided N · assumed N · parked N · out of scope N
Parked: <one line each, with its tag>
Exit test: <row · status · model or reason>, when one ran
Gate: <the gate line>
Next: /blueprint when ready.
```

A napkin run prints the napkin line (`Doc: none`, the form's dash, `napkin, straight to
/blueprint`) and zeroed counts. When running this skill required working around, reinterpreting
or excepting one of its rules, add one line `SKILL NOTE: <what and why>`, addressed to the
skill's author; a clean run carries none.

## What not to do

- Don't research or leave the property; park it instead.
- Don't ask what the property can answer.
- Don't invoke any skill except readers for the exit test; a one-line suggestion is the ceiling.
- Don't build anything, prototypes included.
- Don't send anything to an outside model without his word in this run.
- Don't drip questions, and don't cap them.
- Don't invent or embellish a ledger line, and don't type the doc, a count or a board yourself.
- Don't blow the gate.
- Don't move the doc: relocating it is the owner's, or sunrise's.

## References

| File | Read it | For |
|---|---|---|
| `references/precon-v2-contract.md` | once per sitting, before step 1 | what each command reads, writes and prints; the refusals; the stops |
| `references/station-loop.md` | when a shared phase or exit code is unclear | the loop the four front stations share |
| `references/answer.schema.json` | before step 4 | the recorded answer's shape |
| `references/input.schema.json` | before step 1 | the input, with `station.home` and `station.date` |
| `references/templates/scope-doc.md` | when the doc's form is in question | the scope doc's form, v1's byte for byte |
| `references/examples/` | when a shape is unclear | accepted and refused examples |
| `adapters/README.md` | before step 1 | which adapter serves your harness |
