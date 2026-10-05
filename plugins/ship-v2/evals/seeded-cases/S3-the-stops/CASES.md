# S3-the-stops: cases

Family S3 of the E15 seeded cases (lane contract section 12, row "S3 the stops"; ship-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`, `src/spinner.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form: slice A `not started`, its footprint `src/turnstile.py` and `tests/`; slice B `not started`). The input names slice A. As S2's. Slice A's footprint names `src/turnstile.py` and `tests/`.

## S3-01-clean

The recorded answer: build, a clean signoff, the report.

## S3-02-build-partial

The recorded answer: build-v2 returns its not-complete example (the answer claims partial), then a signoff visit, then the report.

## S3-03-fix-outside-footprint

The recorded answer: build, signoff with the MAJOR, then one fix that touches and names `src/spinner.py` as well, then the report.

## S3-04-fix-spec-change

The recorded answer: build, signoff with the MAJOR, then a fixes file that names a fix needing the spec changed, then the report.
