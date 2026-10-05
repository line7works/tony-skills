# S4-pause-and-waiver: cases

Family S4 of the E15 seeded cases (lane contract section 12, row "S4 pause and waiver"; ship-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`, `src/spinner.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form: slice A `not started`, its footprint `src/turnstile.py` and `tests/`; slice B `not started`). The input names slice A. As S2's.

## S4-01-clean

The recorded answer: build, a clean signoff, the report.

## S4-02-station-question

The recorded answer: the build visit, during which build-v2 puts a question to the owner; the owner has not answered.

## S4-03-mid-run-waiver

The recorded answer: build, signoff with the MAJOR, then ship-v2's own waive-or-hold question about it, answered with the owner's waiver in his words, then an empty fixes file, a recheck that finds nothing open, the report.
