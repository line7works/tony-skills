# The front-of-the-loop replay (E14 slice 3c, item 3.8)

One fixture project walked through precon-v2, architect-v2, blueprint-v2, inspect-v2 and build-v2's
`contract`, each through its real phase driver in this checkout, with the script's own assertions.

## Run it

From this folder, in a checkout (the stations are found beside `inspect-v2` under `plugins/`):

```sh
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh replay.py
PYTHONDONTWRITEBYTECODE=1 uv run --offline --python /usr/bin/python3 --with jsonschema==4.25.1 python replay.py
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh replay.py --keep /tmp/front-replay   # keep the tree to look at
```

`../../setups/safe-python.sh` starts `/usr/bin/python3` with TMPDIR, TEMP and TMP cleared and hands their values
to the script, whose guard then holds them: the `/usr/bin/python3` shim writes into the temp folder as it starts
(inside a Codex sandbox, `xcrun_db`), before any line of a script runs, so it is never started on `replay.py`
directly. The `uv run` line stays as it is: uv starts its own environment's interpreter, not the
shim.

It prints one JSON document and exits 0 only when every assertion held, 1 otherwise. The tree is
built in a fresh temporary directory and removed at the end (`--keep DIR` keeps it in DIR, which
must not exist). The stations run through the interpreter running the script when it imports
`jsonschema`, else through `uv run` with the pin; the summary's `stations_run_by` says which.

## What it proves

- `handoffs`: every hand-off is found by `select` with outcome `one` and no `--path`: the scope
  doc by architect-v2, the scope and architecture docs by blueprint-v2, the build doc and the scope
  doc by inspect-v2; each station's own new-doc hunt found nothing before it wrote its doc.
  A hunt whose outcome is not the one wanted (`one` for a hand-off, `none` for a new doc's own
  hunt) stops the replay there: the problem names the station, the hunt, the outcome and the
  candidates, and the summary's `facts` holds every `select` made up to the stop.
- `ids_forward`: every decided line of the scope doc's ledger reaches the build doc by its id (a
  line of blueprint-v2's accepted answer traces to it, and its text is in the build doc), and no
  answered question of architect-v2 or blueprint-v2 touches it.
- `contract`: build-v2's `contract` for slice A holds the slice's requirements exactly as the build
  doc states them.
- `exits`: every command exits as its contract says. inspect-v2's `write` stops `records-refused`
  (exit 10): the records component of this checkout recognises no inspect verdict mirror (ruling
  E14-2), so the stamp and the events are not written; the replay records that outcome.
- `confined`: nothing written outside the fixture workspace and the run directories (the staging
  home unchanged, nothing else in the tree, this checkout's `plugins/` unchanged).

## The fixture

`fixtures/turnstile/workspace/` is the project (the seeded cases' turnstile: a bench-rig turn
counter), made a git work tree with one commit. The four JSON files are the executor's recorded
answers, one per station: `@ledger:<text>@` stands for the id the station's own `harvest` printed
for the ledger line with that text, `@run@`, `@session@` and `@today@` for the run, the session
and the harvest's date. `inspect-reader-results.json` is the recorded reader answer (three clean
lens results); no reader is launched, no model is called, and no harness runs.
