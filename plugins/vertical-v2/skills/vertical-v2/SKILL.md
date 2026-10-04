---
name: vertical-v2
description: >-
  The whole-build adversarial review, the capstone of the loop, on the v2 foundation. Runs only after
  ALL slices of a build doc are signed off; reviews the entire vertical against its base with fresh
  Claude reviewers at full scope plus, on the owner's word in the run, outside reviewers from readers'
  roster under a reject-it mandate, and writes one verified verdict doc. Use when the user says
  "/vertical-v2", "vertical review", "run the vertical", or "whole-build signoff" on a completed build.
  Stops at the verdict; never fixes.
---

# Vertical v2

The final inspection before a build is called done. A slice review inspects one slice; this inspects
the whole structure once every slice's card stands `signed off`: fresh reviewers read the entire
vertical against its base, joined on the owner's word by outside reviewers with a mandate to reject it.
Every reviewer is a call on `/readers` (`readers-protocol: 1`). One verdict doc comes out. Nothing gets
fixed here.

**The split.** You talk to the owner, summon readers, verify findings and judge; `scripts/vertical.py`
does everything deterministic and makes the one write (rule E15-4). It finds the build doc, reads every
card from the records component and every `Status:` line, computes the base and the boundary, checks
the tree, renders the ask, cuts the review copies from the commit's tree, builds the cold packets and their
lists, builds every readers request, holds your recorded answers to the run, merges, counts, writes the
verdict doc and the trace, and renders the `VERTICAL:` block. `references/vertical-contract.md` states
every phase, its exits and its stops; read it once per run, before step 1. `references/back-loop.md` is
the discipline it shares with the other back cores.

**The one unforgivable move is an unverified outside finding reaching the verdict.** Outside models
hallucinate file paths and invent plausible defects. You verify every finding against the source before
you stamp it; the script refuses a CONFIRMED or PLAUSIBLE stamp at a location that does not exist in
the reviewed copy, and what you refute is counted and stays only in the raw appendix.

## Running the script

Run every command as `uv run scripts/vertical.py <command> ...`, resolved against the directory
holding this file; paths are absolute. Every command prints one JSON document. Exit 0: go on, the
document's `next` names the command. Exit 10: the run ended; read its result and report it. Exit 2:
your usage (the message names the command to run instead). Exit 3: a missing dependency (jsonschema,
the records component, readers); say so and stop. Exit 4: a file you passed fails its schema; fix the
file. Exit 5: refused on its content; nothing was written, read the reason, and offer a corrected file
or stop.

## Step 1: The gate

First read `adapters/README.md`: it names the profile for the harness you run in, and that profile names
the helper that prints the `invocation` object. Build the input (`references/input.schema.json`): a
fresh `run_id` (one path segment), an absolute `run_dir` outside the repo, the `workspace`, the helper's
`invocation` whole, `station.session_model` (the model id your system prompt says you are), and
`station.depth` (LEAN unless the owner said deep, thorough or full, or the build touches auth, money or
user data; then DEEP). Only the owner's own words go in `station.owner_words`, verbatim: a collapsed gate
("run it anyway"), a committed-state-only order, a base he named. Never propose a collapse.

```sh
uv run scripts/vertical.py check-input <input.json>
uv run scripts/vertical.py gate --run-dir <run dir> [--doc <path> | --name <feature>]
```

`--doc` when the invocation names the build doc or this session established the plan; else `--name`
for the hunt (the repo's tiers only: `docs/plans/`, then the older flat build plans, then a phase or
slice doc; no wider hunt). The gate stops on: nothing found or several found (list them, ask the owner,
run again with `--doc`); a build doc holding a fence it does not accept, a raw HTML line or a label it does not take (`doc-unreadable`:
only plain code blocks whose fences open and close at the left margin are read, no line opening with `<`
and a letter, `/`, `!` or `?`, headings and labels only in their plain form at column 0 (no indent, no list or
quote marker, a heading's `#`s then exactly one space), and only an exact `Status:` label per slice and `Base:`
line in the header, each the last line of its paragraph, a label read in any letter case or accent and with any
spaces before its colon; no character outside the character list outside a fence (printable ASCII, a tab and the few
punctuation marks, symbols, curly quotes and accented Latin letters the plans use; the stop names the character's
code point); then the doc is read a second time by a CommonMark
reader, and any slice, card, base or withheld section the two readings take differently stops it too, as does a
rendered `Status:` or `Base:` line in a paragraph whose lines the reader cannot map to source lines, a level 1 or 2
heading that starts with "slice" off the form's slice heading, a heading that starts like a `Status:` or `Base:`
label, a character reference to a character outside the list, and another Markdown file of the commit that a
CommonMark reader declares the builder's notes and the line reading does
not (a file whose opening heading holds a character outside the list is withheld instead, never a stop); tell the owner
the line to edit); zero slices or a slice with no `Status:` line; any slice short of `signed off`
(name each slice and its state; a `built` card's remedy is a fresh slice signoff, never a recheck); a
card in the records that disagrees with its `Status:` line (name both); no git; no base (ask the owner
for the base and run again with his answer in `station.owner_words.base`); dirt touching the boundary or
the build doc (the owner decides: commit first, or a committed-state-only run in his words). Report the
stop and STOP. The gate runs before the ask: no crew is picked for a run that stops.

## Step 2: The ask

```sh
uv run scripts/vertical.py ask --run-dir <run dir>
```

It prints two `suggest` argv lists, in order. Summon `/readers` with each, in that order (the local row
first, under the floor; then the outside rows, with none), save each output to a file, then:

```sh
uv run scripts/vertical.py ask --run-dir <run dir> --local-suggest <file> --outside-suggest <file>
```

Show the owner the `ask` text it prints, exactly, and wait. Silence never proceeds; the recommendation
is not a trigger. His answer must name each row (a bare "outside" or "both" is asked again); it applies
to this run only. Record it, his words verbatim and the rows his words name (empty for local-only), with
any model id he typed against a row he named:

```sh
uv run scripts/vertical.py ask --run-dir <run dir> --answer <answer.json>
```

## Step 3: The base and the packets

```sh
uv run scripts/vertical.py scope --run-dir <run dir>
```

It reads the reviewed commit (never the working tree), takes the inspection sheet from it, and cuts one
preview packet per local lens and per outside row named through the one packet builder (no history, no
untracked file, no review record, the build doc reduced to its spec), each with its file list (with
hashes) and its withheld list. State the depth line it prints before launching anything. The previews are
for you to inspect; every request below gets its own fresh copy from the same builder. A build doc holding a
fence line off the left margin, inside a list item or a block quote, or never closed, or any raw HTML line
(a line opening with `<` and a letter, `/`, `!` or `?`, outside a fence), or any character outside the
character list outside a fence, or any heading or label line off the
plain form (indented, after a list or quote marker, or a heading whose `#`s are not followed by exactly one
space), or any `Status:` or `Base:` line that is not exact and the last line of its paragraph, or any slice,
card, base, withheld section or builder's-notes heading that a CommonMark reader takes differently from those
line rules, stops the run here (`doc-unreadable`, naming the line) before any packet exists: tell the owner the
line to edit.

## Step 4: The reviews, local first

```sh
uv run scripts/vertical.py request --run-dir <run dir>
```

Summon `/readers` with the request files it prints as one fleet: the local lenses, fresh reviewers
with zero shared context, never this session reviewing the code itself. A lens that comes back
`transport-failed`, `empty` or `incomplete` is re-sent once:

```sh
uv run scripts/vertical.py request --run-dir <run dir> --resend <lens> --status <status>
```

and summon that one request. Then merge the local reports: dedupe on `file:line` plus claim, verify
each finding against the source (CONFIRMED, PLAUSIBLE, or REFUTED with the reason), note any re-grade
with one clause of why, and list for each lens what it tried to break and could not. Record it:

```sh
uv run scripts/vertical.py record-local --run-dir <run dir> --answer <local.json>
```

A lens that failed after its re-send, or refused deterministically, stops the run (the local review
always completes or the run does not); a floor refusal stops the run with no verdict. The local verdict
is formed before any outside request exists: `record-local` writes it with a receipt over every file it
rests on, and the outside requests are released, and the verdict written, only while that receipt holds.
Never edit the run directory by hand; an edit is detected and the run refuses. Then, only when the owner named outside rows:

```sh
uv run scripts/vertical.py request --run-dir <run dir> --outside
```

Summon `/readers` with those requests as one fleet; each carries `authorized` on his word in this run.
A row he named that the ask showed as dropped is never sent: the command records it with its reason and
requests the rest (when none is left, it says so and the next command is the verdict). A call that comes
back anything but `ok` is a dropped reviewer, never retried in this run.

## Step 5: Merge and verify

Verify every outside finding against the source before it can land: read the code at the claimed
location, check that the scenario holds, stamp it. A hallucinated location is refuted unless you locate
the real site and name it on the finding. Compare against the per-slice record (the build doc's punch
list and the records): note repeats and misses in the ledger notes. Record it:

```sh
uv run scripts/vertical.py record-outside --run-dir <run dir> --answer <outside.json>
```

## Step 6: The verdict doc

```sh
uv run scripts/vertical.py verdict --run-dir <run dir>
```

It merges, counts `Refuted: N`, reads the repeats and misses against the ledger, and writes the one
file, `docs/reviews/<date>-vertical-<feature>.md`, v1's three sections; a rerun appends a dated block to
the same file. It never touches code, the build doc, a card or `REVIEW.md`.

## Step 7: Stop

```sh
uv run scripts/vertical.py report --run-dir <run dir> --bottom-line "<two or three sentences>"
```

Deliver the `VERTICAL:` block it prints and stop. Offer fixes; never start them. No push, no pull
request, no merge.

## The rules

1. The gate is real: every slice `signed off`, or report and stop; only the owner's words collapse it.
2. The ask is real: every run, wait for the answer; nothing is remembered between runs.
3. Secrets are physically absent: reviewers read copies of the reviewed commit's tracked files, never the live tree.
4. Cold means cold: no prior verdict, no ledger, no chat, no other reviewer's output in any packet.
5. Nothing unverified lands in the verdict; `Refuted: N` is always reported.
6. Survivors continue: a dropped outside reviewer is recorded with its status and reason.
7. One write: the verdict doc, dated, never overwriting.
8. Stops at the verdict: no fixes, ever, from this skill.
9. Interactive only: the owner answers the gate, the ask and the base.

## Output

The `VERTICAL:` block, v1's form, as `report` renders it:

```
VERTICAL: <build doc> @ <base>..<head>
Verdict: <SIGNED OFF | SIGNED OFF WITH CONDITIONS | REJECTED>  ·  per /signoff's mapping
Reviewers: local + <list | none>  ·  Dropped: <who — why | none>  ·  Refuted: N
Doc: <path to the verdict doc>
REVIEW.md: read — passes skipped: <name (reason)> | none skipped · <N> repo-specific checks tried | present but not the kit sheet — defaults | absent — defaults

Bottom line: <2-3 sentences — the build's state and what to do next.>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```
