# The back-of-the-loop replay (E15 slice 3, the lane contract section 11, item 5)

One fixture project taken through ship-v2's loop with the real build-v2, signoff-v2 and recheck-v2, then
handoff-v2's photograph, then vertical-v2's gate, packets and summons, each through its real phase driver, on recorded
answers, with the script's own assertions. No model is called, no reader is launched and no harness runs.

## Run it

From this folder, in a checkout (the stations are found beside `ship-v2` under `plugins/`):

```sh
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh replay.py
PYTHONDONTWRITEBYTECODE=1 uv run --offline --python /usr/bin/python3 --with jsonschema==4.25.1 python replay.py
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh replay.py --path findings --keep <a new folder>
```

`../../setups/safe-python.sh` starts `/usr/bin/python3` with TMPDIR, TEMP and TMP cleared and hands their values to
the script's guard. It prints one JSON document and exits 0 only when every assertion held, 1 otherwise. Each path's
tree is built in a fresh temporary folder and removed at the end (`--keep DIR` keeps them in DIR, which must not
exist). `--root STATION=DIR` runs ship-v2, handoff-v2, vertical-v2, readers or records from another plugin root
(`../../setups/trace-proof.sh` runs the installed copies this way); `--trace-out FILE` writes every trace line.

The stations run with a fake HOME inside the tree and `READERS_CHECKOUT` naming a folder there, so readers'
last-pick memory and its lock are the tree's own, never a checkout under the real home.

## What it proves

- `loop`: ship-v2's run ends as the recorded answers say: clean, `completed`, ALL CLEAR, Recheck not run, Laps 0;
  findings, `completed`, ALL CLEAR, Signoff signed off with conditions, Recheck ALL CLEAR, Laps 1; Card signed off;
  every command exits as its contract says. On the findings path ship-v2's `fix` names the save step for exactly the
  verdict mirror signoff-v2 wrote, the executor runs its commands as printed, and the commit holds exactly that file
  (`save_step` in the summary).
- `trace`: ship-v2's trace holds each visit's opening and closing line in the loop's order, every line a v2 identity
  (interface 1, route 3a or 3b, its version its root's manifest's, under no v1 folder), and `validate-trace.py` holds
  it; vertical-v2's trace holds one `ok` readers summons per call.
- `photograph`: handoff-v2's cards and open set are the records component's `state`, its branch and tree git's; the
  block carries those cards; the loop complete gives no kickoff line.
- `vertical`: the gate passes; every packet `scope` cut and every summons copy `request` released holds no file
  under `docs/reviews/` or `docs/records/`, no history, no withheld heading or `Status:` line, and no line of the review
  record (the verdict docs, the records log, the doc's ledger sections), its `files.json` hashes match the copy, and
  its `withheld.json` names each of those; no outside request exists before `record-local`; `Refuted:` counts the
  refuted outside finding on the findings path.
- `confined`: this checkout's plugins tree is unchanged (paths, sizes, modification times).

## The fixture

`fixtures/turnstile/workspace/` is the project (a bench-rig turn counter, one slice); its build doc is
`docs/plans/2026-10-06-turnstile.md.in`, written out with the slice heading's dash at run time. `edits/` holds the
executor's files (the right build, the wrong build, the fix). `answers.json` holds every model's part: the build's
claim and reasons, the reviewer's findings, the verifier's dispositions, handoff-v2's perishables, vertical-v2's ask
answer, lens replies and merged findings. Every check output is captured by running the check the slice names.

On the findings path the executor takes ship-v2's named save step after the lap's `fix` and before the recheck visit,
as `fix` printed it (`save_step`: `git add` and `git commit --only` of signoff-v2's verdict mirror under
`docs/reviews/`, a local commit of that file alone; ship-v2's SKILL.md step 5 and its contract's section 3.11, the E15
lane contract A30 (1)): recheck-v2's own stated precondition for the loop (its contract section 9, E13's F8). The
commands run through this replay's git, which adds only the fixture repository's hooks-off and no-signing settings.
Without the step ship-v2 refuses the recheck visit, naming the step and the file
(`skills/ship-v2/scripts/tests/test_save_step.py`, the join's probe shape on the real stations). The
build doc's `Footprint:` is the one-line form ship-v2 reads; build-v2 reads it as empty today (the first item on the
E15 punch list), so its result lists the slice's paths as out of scope, each with the reason the answer gives.
