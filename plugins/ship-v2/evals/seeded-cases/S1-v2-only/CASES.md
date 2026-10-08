# S1-v2-only: cases

Family S1 of the E15 seeded cases (lane contract section 12, row "S1 v2 only"; ship-v2). 5 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`, `src/spinner.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form: slice A `not started`, its footprint `src/turnstile.py` and `tests/`; slice B `not started`). The input names slice A. Each case's run is driven against a copy of ship-v2 in a plugins folder of its own, beside a stand-in for each station (the real station's manifest and result schema, and a script that answers skill-identity and nothing else), or, where the case plants one, a v1-shaped station in its place. The drive step runs the station from check-input to report on the case's recorded answer.

## S1-01-clean

No plant. The recorded answer: build-v2 returns its completed example, signoff-v2 its clean example, then the report.

## S1-02-v1-root-link

The build-v2 folder beside ship-v2 is a link to a folder named for the v1 build station, whose script leaves a marker when run. The recorded answer: the build visit, then the report.

## S1-03-v1-name-in-manifest

The build-v2 folder's manifest names the v1 build station; its script leaves a marker when run. The recorded answer: the build visit, then the report.

## S1-04-no-interface-version

The build-v2 stand-in's skill-identity reports no interface version. The recorded answer: the build visit, then the report.

## S1-05-v1-result-file

No plant. The recorded answer: the build visit, whose result file is a v1 station's text-shaped report, not a v2 result document.
