# Running the seeded cases against a front core

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 observe.py --all --out /tmp/observe
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --case <case id> --out /tmp/observe
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --list
```

Each case is built by its family's `build.py` into `--out/<family>/`, the steps of its
`drive.json` are run, and `observed.json` is written beside the case. `observe.py` prints one JSON
document naming every observation, and exits 1 when a step could not run (its `_errors` say why).

`select` steps drive the REAL CLI (`check-input`, then `select`), so the interpreter needs
`jsonschema` (the `uv run` form above supplies the pin). The other steps drive the shared library
the lanes' phases call (`_via` in each observation says which). `request` steps read readers'
roster beside this core (`plugins/readers/`), so they run in the checkout.

## What `observed.json` holds

The neutral vocabulary of `README.md`, only the names the run has a fact for; `_case`, `_family`,
`_core`, `_phases`, `_via` and `_lane_pending` are the observer's own bookkeeping. A `lane` step's facts come from the core's own `lane_observe.py` beside `observe.py`, when it
exists: only the names the step lists under `pending` that no frame step observed are taken from
it; every name it did not fill stays under `_lane_pending`; a name it fills outside that list is
recorded under `_errors` and never merged.

## What is NOT here

No expected value. The control room grades `observed.json` against the answer key and reports pass
or fail per case with the assertion name that failed.
