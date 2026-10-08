# V1-the-gate: cases

Family V1 of the E15 seeded cases (lane contract section 12, row "V1 the gate"; vertical-v2). 5 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`, `src/legacy.py`); the branch `feat` holds the build (a changed `src/turnstile.py`, a new `src/spinner.py`, the build doc `docs/plans/2026-09-20-turnstile.md`). A case that commits a records log names it.

## V1-01-clean

Both slices' `Status:` lines read `signed off`. The branch commits the records log the records component's `import-legacy` wrote for this build doc, naming both slices `signed off`.

## V1-02-slice-built

Slice A's `Status:` line reads `signed off`, slice B's reads `built`. No records log.

## V1-03-zero-slices

The build doc holds no `## Slice` heading: its header, then the five ledger headings. No records log.

## V1-04-card-disagrees

The records log (committed first) names both slices `signed off`; a later commit changes slice B's `Status:` line to `built`.

## V1-05-missing-status

Slice B has every label but `Status:`. No records log.
