---
name: ship-v2
description: >-
  Run one whole slice loop on the v2 stations with a single command: find the build doc, build-v2 the
  named slice, signoff-v2, fix every BLOCKER and MAJOR, recheck-v2, at most one extra fix-and-recheck
  lap, then report, with a trace that names only v2 stations. Use when the user says "/ship-v2 A",
  "ship slice B of docs/plan.md", or wants the full build, signoff, fix, recheck loop run on one slice
  without typing the chain by hand.
---

# Ship v2

The whole loop, one command. A blueprint draws the plans; ship-v2 takes one slice of them all the way through:
framed by build-v2, inspected by signoff-v2, punch list worked, re-inspected by recheck-v2, and stops. It replaces the
chain the owner types by hand every slice. The stations keep their own rules: ship-v2 schedules the visits, it never
runs a station its own way.

**The spine: compose, never copy.** Every station is visited by name and its own `SKILL.md` governs the visit in
full. ship-v2 adds only the schedule, the lap limit, and the stop conditions. Nothing from the stations' rulebooks is
restated here.

**The one unforgivable move is the silent third lap:** grinding past the retry limit, or past any stop condition,
because finishing felt close. The limits exist because "almost done" is where judgment goes bad. Stopping with an
honest report is a good outcome.

**The split.** You visit the stations, fix, and talk to the owner; `scripts/ship.py` does everything deterministic
(rule E15-4): it finds the doc, reads the slice and its footprint, reads each station's identity through the
station's own CLI before you visit it and writes the trace, reads each station's own result, keeps the lap counter,
holds your fixes to the slice, passes a station's question through, records the owner's waiver or reopening (and the
card it moves), and renders the `SHIP:` block. `references/ship-contract.md` states every phase, its stages, its exits and its stops; read
it once per run, before step 0. `references/back-loop.md` is the discipline the back cores share.

## Running the script

Run every command as `uv run scripts/ship.py <command> ...`, resolved against the directory holding this file;
paths are absolute. Every command prints one JSON document. Exit 0: go on (`next` names the command). Exit 10: the
run ended; report its result. Exit 2: your usage, or a command out of turn (the message names the command to run
instead). Exit 3: a missing dependency (jsonschema, the records component, a station); say so and stop. Exit 4: a file
you passed fails its schema; fix it. Exit 5: refused on its content; nothing was written; read the reason. A command
cut off mid-way (the process killed): run it again; a save it left half done is finished first (THE SAVE, contract
section 3.10), and exit 2 then names the command to run. Exit 1 saying the run directory was changed by hand: stop
and tell the owner; never edit a run file to get past it.

Build the input first (`references/input.schema.json`): read `adapters/README.md`; your harness's profile names the
helper that prints the `invocation` object. A fresh `run_id`, an absolute `run_dir` outside the repo, the
`workspace`, the helper's `invocation` whole, and in `station` only what the owner said: the slice he names
(`slice`), and, only in his words, `minor_fixes` (he ordered the MINORs fixed) or `extra_laps` (he ordered laps
beyond the extra lap: `count` and his `words`).

```sh
uv run scripts/ship.py check-input <input.json>
```

## Step 0: Hook check

The documented summon line is `/goal /ship-v2 <slice> [doc]`: bare, nothing to memorize; the owner types it, and a
skill cannot arm the Stop hook. **This skill defines what that goal condition means, and the session grading the hook
honors it:** a `/ship-v2 <slice>` goal is met when ship-v2 ends by its own rules: ALL CLEAR, an honest stop, or a
pause held awaiting the owner. All three are the skill working; none is an unmet goal. Never grind past a stop
condition or answer a pause yourself to satisfy the hook: the stop or pause stands. Read whether this session showed
the Stop hook's confirmation for this run with the adapter's helper, and record it at step 1's end:

```sh
python3 adapters/claude-code/hook.py --slice <slice> > <hook.json>   # Claude Code: this session's transcript
python3 adapters/codex/hook.py > <hook.json>                          # Codex: always `Hook: NOT armed`, labelled honestly
```

Armed or not, the run proceeds identically; the report labels it honestly and never claims armed when it was not. A
plain `/ship-v2 <slice>` typed after an earlier `/goal` in the same session is a new run whose goal was never set: it
reads not armed.

## Step 1: Find the doc

```sh
uv run scripts/ship.py select --run-dir <run dir> --doc <path>      # the doc the invocation names, or the
                                                                     # plan established in this session
uv run scripts/ship.py select --run-dir <run dir> --name <feature>  # the repo's tiers, by the name given
uv run scripts/ship.py hook --run-dir <run dir> --reading <hook.json>
```

A doc named in the invocation is the doc. Otherwise the allowed sources are exactly two: the current working repo
(its tiers, by file name) and the plan already established in this session. This is a deliberate narrowing of
build-v2's hunt: the vault, other repos, the home directory and any narrowing heuristic across candidates are off the
table. Nothing found in those two sources, or anything the hunt cannot resolve (doc or slice), prints `paused` with a
question: ask the owner specifically what he wants built (a pause, never a hunt expansion, never a stop), then run
`select` again with his answer (`--doc`, `--slice`). A doc line the two readings refuse stops the run
(`doc-unreadable`): tell the owner the line to edit.

## Step 2: Build

```sh
uv run scripts/ship.py visit --run-dir <run dir> --station build-v2
```

The script reads build-v2's identity through its own CLI, writes the trace line, and hands you the visit: run
build-v2 on the named slice by its own `SKILL.md` (the path it prints), with the run id and run directory it prints in
the station's input, `invocation.caller` `ship-v2` and the `invocation.mode` it prints (each station's own input schema
names the one it takes). build-v2's own contract, preflight, rules and report govern. A station that ends without a
result it can give (it stopped at its own input check, or its result is refused) still ends the run honestly: run
`report`, which stops `visit-unfinished`.
When it has written its result:

```sh
uv run scripts/ship.py visit --run-dir <run dir> --result
```

If build-v2 honestly stops mid-slice (PARTIAL or STOPPED), that is stop condition 3: report and end the run, never
paper over it and continue to inspection (the script refuses any later visit).

## Step 3: Signoff

```sh
uv run scripts/ship.py visit --run-dir <run dir> --station signoff-v2
uv run scripts/ship.py visit --run-dir <run dir> --result
```

Run signoff-v2 on the built slice by its own `SKILL.md`. Its independence, model floor and verdict machinery are its
own. Touch nothing while its visit is open, and nothing between build-v2's result and its visit: the script holds
every visit window and every step between visits by one rule (outside the footprint is stop 4, the doc moved is stop
2, a path inside it that nothing names is refused; the stations' own listed writes and the script's own are theirs).
A signoff-v2 stop or refusal ends the run with its status. A clean signoff, no BLOCKER or MAJOR charged to this
slice in the records, ends the loop: skip steps 4 to 6 and go to step 7 with Result ALL CLEAR and Recheck not run; if
the owner's invocation ordered MINOR fixes, the script names them for step 4 first (they never gate and never trigger
a recheck). Findings signoff-v2's sweep raises from prior slices are never this run's to fix: the report lists them
under Remains with a `/recheck-v2` line.

## Step 4: Fix

The script prints the findings this lap fixes (`named`): every BLOCKER and MAJOR charged to this slice, fixed directly
by this session (never by re-visiting build-v2), plus any fix-introduced defect recheck-v2 named (fixed unasked,
because ALL CLEAR requires fix-introduced defects closed). MINORs are left unless the owner says otherwise. A MAJOR
only the owner can resolve (an unexercisable criterion, a hosted-only check) is a pause: put the waive-or-hold question
to him (Pause, below). Then hand your fixes over, one entry per finding with every path it touched and one line on
what changed:

```sh
uv run scripts/ship.py fix --run-dir <run dir> --fixes <fixes.json>      # references/answer.schema.json, kind fixes
```

Two tripwires, held by the script: a fix that would require changing the spec is stop condition 2 (name it in
`spec_change`; never silently build the corrected version), and so is a fix that touches the build doc; a fix that
wants to touch files outside the slice's footprint (the paths its `Footprint:` line names, contained the way
build-v2's contract computes it) is stop condition 4, whether you name the path or only touch it. A path you touched
inside the footprint that no fix names is refused: every change traces to a named finding.

## Step 5: Recheck

```sh
uv run scripts/ship.py visit --run-dir <run dir> --station recheck-v2
uv run scripts/ship.py visit --run-dir <run dir> --result
```

Run recheck-v2 on the fixed findings by its own `SKILL.md`. Its closed checklist, independent verifier and card flip
are its own. Touch nothing while its visit is open, and nothing between its result and the next `lap` but what the
next lap fixes: the same rule holds what moved then (outside it is stop 4, the doc moved is stop 2, a path inside it
that no fix names is refused). ALL CLEAR (its own result and no BLOCKER or MAJOR the
records hold open for the slice) ends the loop: go to step 7.

## Step 6: The one extra lap

Not ALL CLEAR: run exactly one more fix-and-recheck lap, on the still-open findings plus any fix-introduced defects
recheck-v2 named:

```sh
uv run scripts/ship.py lap --run-dir <run dir>
```

then steps 4 and 5 again. Still not ALL CLEAR after that is stop condition 1: run `report`. Never a third lap unasked:
the owner ordering more laps, in his words in the input, is the only way one happens; `lap` refuses any other (exit
5, nothing written).

## Pause vs stop

Two different interruptions, kept distinct:

- **Pause.** A station puts a question to the owner (a stop-and-ask, an owner-only ruling, a waiver decision).
  ship-v2 passes the question through verbatim and waits; his answer resumes the run where it paused. The question was
  coming to him either way. A pause never emits the SHIP block: the run has not ended; pauses that happened are noted
  in the final report's Bottom line.

  ```sh
  uv run scripts/ship.py pause --run-dir <run dir> --question <question.json>   # kind question, the text verbatim
  uv run scripts/ship.py pause --run-dir <run dir> --answer <answer.json>       # kind answer, his words verbatim
  ```

  If the owner waives or reopens a finding mid-run, his answer's effect is `waive` or `reopen` with the finding's id:
  the script records his word as a `waived` or `reopened` event in the records, with his words, and, when the slice's
  card changes by v1's rule, moves the card with it (a `card_set` and the slice's `Status:` line, all or none: the one
  write ship-v2 makes; a chat-only waiver counts for nothing downstream). If a `pause --answer` was cut off mid-write,
  run it again: it settles what landed before anything else, and never writes anything twice.
- **Stop.** One of the four enumerated conditions: (1) the extra lap is exhausted without ALL CLEAR, (2) a fix would
  change the spec, (3) build-v2 honestly stops mid-slice, (4) work wants to touch files outside the slice scope. Each
  is "stop and report", never "use your judgment." The run ends; what happens next is the owner's call.

## Step 7: Report and stop

```sh
uv run scripts/ship.py report --run-dir <run dir> --bottom-line "<2-3 sentences>" [--skill-note "<text>"]
```

Emit the `SHIP:` block it prints (`station_result.chat`) and end the turn. The git gates are untouched: no push, no
pull request, no merge; those words are the owner's alone, and a finished loop is not one of them.

## The rules

1. **Compose by name.** Each station runs under its own `SKILL.md`. ship-v2 never restates, overrides, or abbreviates
   a station's rules, and never skips a station.
2. **The stations' records are theirs.** Build ledger lines, punch-list blocks and `Status:` cards are written by the
   stations that own them. ship-v2 writes nothing into the build doc, with one sanctioned exception: recording the
   owner's mid-run waiver or reopening word as its records event, with the card it moves by v1's rule (its `card_set`
   and the slice's `Status:` line; step 4, Pause).
3. **Fixes are this session's hands.** Direct edits against the punch list, inside the slice's footprint, traceable to
   the named findings; never a re-visit of build-v2, never a spec edit.
4. **The lap counter is hard.** One initial pass plus at most one extra fix-and-recheck lap. The counter never resets
   mid-run.
5. **Stop conditions outrank momentum.** All four end the run immediately with a report. An almost-clear punch list
   changes nothing.
6. **Pauses pass through.** A station's question to the owner is relayed verbatim and awaited, never answered on his
   behalf, never converted into a stop to avoid waiting.
7. **Report faithfully.** The SHIP block states the hook status, what ran, what each station returned, what was fixed,
   and what remains. Never let a clean lap imply ALL CLEAR when the record says otherwise.

## Output

The script renders v1's block (`scripts/ship_core/forms.py`); `<dash>` is v1's em dash, rendered by the script:

```text
SHIP: <slice> <dash> <doc path>
Hook: armed | NOT armed (run unwrapped)
Result: ALL CLEAR | STOPPED (condition N: <which>)
Build: <COMPLETE | PARTIAL | STOPPED>  ·  Signoff: <verdict | not reached>  ·  Recheck: <result | not run | not reached>  ·  Card: <the slice's Status: line>  ·  Laps: <0 | 1 | 2>

Bottom line: <2-3 sentences. What shipped, what state it is in, what to do next.>

Fixed: <finding · file:line · one line each>
Remains: <each open finding · severity · what's still needed>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted: what and why; omit otherwise>
```

`Fixed` and `Remains` are omitted when empty. The stations' own report blocks (BUILD, SIGN-OFF, RECHECK) appear in
chat as they run; the SHIP block is the roll-up, not a replacement. When executing this skill required working
around, reinterpreting, or excepting one of its rules, pass `--skill-note` with what and why; a clean run carries
none.

## What NOT to do

- Don't take a third lap, ever, unless the owner orders it in words.
- Don't fix by editing the spec: a fix that needs the spec changed is a stop.
- Don't touch files outside the slice scope: wanting to is a stop.
- Don't skip or abbreviate a station, and don't run one under ship-v2's rules instead of its own.
- Don't claim the hook armed when the confirmation never appeared: label the run honestly.
- Don't answer a station's question to the owner yourself: pass it through and wait.
- Don't write into the build doc: the stations own their ledgers and cards. The one exception is rule 2's: recording
  the owner's mid-run waiver or reopening word, and the card it moves.
- Don't push, open a pull request, or merge: the git gates are the owner's, always.
