# S2-the-lap-counter: cases

Family S2 of the E15 seeded cases (lane contract section 12, row "S2 the lap counter"; ship-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`, `src/spinner.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form: slice A `not started`, its footprint `src/turnstile.py` and `tests/`; slice B `not started`). The input names slice A. As S1's, every station a stand-in. signoff-v2's visit records one MAJOR at src/turnstile.py:2 for slice A (the records events and the Status: line signoff-v2 writes), and each recheck-v2 visit records its disposition of it.

## S2-01-clean

The recorded answer: build, signoff with the MAJOR, one fix, a recheck that fixes it (all clear), the report.

## S2-02-third-lap-unworded

The recorded answer: build, signoff with the MAJOR, then two fix and recheck rounds that do not fix it, with a lap between them, then one more lap, then the report. The input carries no words for more laps.

## S2-03-third-lap-worded

As S2-02, with the owner's words for one more lap in the input; after the third lap, one more fix and a recheck that does not fix it, then the report.
