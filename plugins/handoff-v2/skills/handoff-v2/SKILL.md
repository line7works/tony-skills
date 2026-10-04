---
name: handoff-v2
description: >-
  End-of-slice thread prep for the build loop on the v2 foundation: the photograph rebuilt from the
  records and git, the question gate, one dated block in the build doc and the kickoff line for the
  fresh session. STRICTLY user-invoked, only when the owner summons it ("/handoff-v2", "prep for the
  next slice", "prep the repo for slice X", "clear the thread and prep", "get ready for slice X",
  "get ready for the next slice"); never auto-invoke, suggest-invoke, or trigger from conversation
  shape. Not for machine settle-up or account switches, and not for cross-machine hand-offs.
disable-model-invocation: true
---

# Handoff v2

The end-of-phase walkthrough. When the thread is about to be cleared, everything a clear would destroy gets asked,
recorded, or written down, and the owner leaves with the exact line to type in the fresh session.

**Photograph, never gate.** Open cards never stop this run; they change its output. The one sanctioned pause is the
question gate: unanswered questions stop the run before any write. **The one unforgivable move is the invented
photograph**: state written from what the session remembers instead of the record read now. Here the script reads the
record (the records component's `state` and git) and renders every photograph line; an answer of yours that asserts
a card, an open item or a branch fact the record contradicts is refused.

**The split.** You talk to the owner and pass his words; `scripts/handoff.py` does everything deterministic and every
write (rule E15-4). `references/handoff-contract.md` states every phase, its exits and its stops; read it once per run,
before step 1. `references/back-loop.md` is the discipline the back cores share.

## Running the script

Run every command as `uv run scripts/handoff.py <command> ...`, resolved against the directory holding this file;
paths are absolute. Every command prints one JSON document. Exit 0: go on (`next` names the command). Exit 10: the
run ended; report its result. Exit 2: your usage (the message names the command to run instead). Exit 3: a missing
dependency (jsonschema, the records component); say so and stop. Exit 4: a file you passed fails its schema; fix it.
Exit 5: refused on its content; nothing was written; read the reason and offer a corrected file, or stop.

## Step 1: Find the doc

Read `adapters/README.md`; its profile for your harness names the helper that prints the `invocation` object. Build
the input (`references/input.schema.json`): a fresh `run_id`, an absolute `run_dir` outside the repo, the
`workspace`, the helper's `invocation` whole, and in `station` only what the owner said: the slice he names as just
finished (`slice`), the doc's name when he gave one (`feature`, with his words).

```sh
uv run scripts/handoff.py check-input <input.json>
uv run scripts/handoff.py select --run-dir <run dir> --name <feature>
```

`--name` is what the invocation names; `--doc <path>` instead when it names the doc, or when the hunt found none and
this session established the plan. The hunt is the repo's tiers only. It stops on: nothing named (ask the owner which
doc, never take the lone doc on disk), nothing found, several found (list them, never pick), a doc line the line rules
refuse (tell the owner the line to edit), a handoff block outside `## Handoffs`, no identity (ask him to name it, then
run again with `station.feature`). Report the stop and STOP.

## Step 2: Read the record

```sh
uv run scripts/handoff.py photograph --run-dir <run dir> [--suite-record <the last build-v2 result.json>]
```

Every card and the open set come from the records component, the branch, the commits ahead and the tree from git,
read now. Pass `--suite-record` only when this session has a recorded suite run (a station's `result.json`); never run
the suite.

## Step 3: The question gate

Before ANY write, assemble the open questions from the session's two sources and write them to a questions file
(`references/answer.schema.json`, kind `questions`):

1. Unanswered `Questions:` lines from this session's signoff and recheck outputs (`source: session-question`).
2. Rulings the owner gave in chat this session that never became dated ledger lines (`source: chat-ruling`): a
   chat-only waiver counts for nothing downstream.

```sh
uv run scripts/handoff.py gate --run-dir <run dir> --questions <questions.json>
```

The script adds the record's own: which slice is next when the cards and `Depends on:` chains do not yield exactly
one (`r-next`), and the open questions the build doc records for the slice about to be built (`r-q1`, ...). It prints
every question with its id. Any found: present them all in one batch and pause; nothing has been written yet. Every
question answered: record the answers (step 4) and continue the run. Any question unanswered, some or all, whether
the owner skipped it or never replied: the run ends with nothing written, reported in the gate-open form, never the
standard block; a partial set of answers never buys a partial handoff. Never answer a gate question on the owner's
behalf, and never write around one.

## Step 4: Record the answers

Write the answers file (kind `answers`): per question its id, `answered`, his words verbatim and the effect: `note`
(lands in the block as question and answer), `waive` or `reopen` with the finding's id from the gate's output (the
records event with his words and its dated ledger line), `next-slice` with the slice he named, or null when he holds
the next move. Step 5's perishables go in the same file. Put in `asserts` what you believe of the photograph only if
you want it checked.

```sh
uv run scripts/handoff.py record-answer --run-dir <run dir> --answer <answers.json>
```

Any question unanswered ends the run (exit 10, `gate-open`): report its gate-open form and stop.

## Step 5: Harvest the perishables

Collect from this session what dies at the clear: seam notes for the next slice, workarounds found, items pending the
owner's word (a migration he must push, a deploy he must trigger), open MINORs worth the next builder's attention. One
line each, in the answers file's `perishables`. Nothing shaped like a requirement: the block is ledger, never spec.

## Step 6: Photograph the repo

When step 2 showed a dirty tree, take the local checkpoint commit now, your named step (the script never commits):

```sh
git -C <workspace> add -A
git -C <workspace> commit -m "handoff checkpoint (local): <feature> after <slice>"
```

Local only; never push, open a pull request or merge. Skip it on a report-only run.

## Step 7: Resolve the next move and write

```sh
uv run scripts/handoff.py write --run-dir <run dir>
```

The script resolves the next move from the record: a clean boundary gives `/ship-v2 <slice> <doc>` (and `/build-v2`
once, by hand); an open card gives the fix list, then `/recheck-v2`; a complete loop gives no kickoff line. It appends
the grants through the records component, then writes one dated block at the tail of `## Handoffs` (created before
`## Punch list` when missing), recording the checkpoint commit it finds. It stops, writing nothing, when anything
moved since the photograph or an earlier block was edited.

**The memory pointer.** On Claude Code, the adapter's step: `python3 adapters/claude-code/pointer.py --run-dir <run
dir> --memory-dir <this project's auto-memory folder>`. On Codex there is none: the block is the pointer, and the
result says so.

## Step 8: Report and stop

```sh
uv run scripts/handoff.py report --run-dir <run dir> --bottom-line "<2-3 sentences>" [--skill-note "<text>"]
```

Emit the `HANDOFF:` block it prints (`station_result.chat`) and end the turn, closing with the statement that the
thread is safe to clear. The skill never runs a clear, never starts the next slice, and never invokes another station.

## The rules

1. **Photograph, never gate.** Open BLOCKERs and MAJORs change the kickoff line, never stop the run.
2. **Nothing is written before the gate resolves.** An abandoned gate leaves the doc, the ledger and memory as found.
3. **The record over the recollection.** Cards, open items and repo state come from the script's read, never yours.
4. **The block is ledger, never spec.** Requirements live in the slices alone.
5. **Additive only.** The sanctioned writes, exhaustively: the grant events and their lines, the one block, the
   checkpoint commit (yours), the memory pointer (the Claude Code adapter's).
6. **The git gates are the owner's.** Local checkpoint commits only; never push, open a pull request, or merge.
7. **Report faithfully.** The kickoff line matches the record; an open card's fix list is never rounded up.
