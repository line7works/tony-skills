# I1-primary-evidence: cases

Family I1 of the E14 seeded cases (lane contract section 14, row "primary evidence"; inspect-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

LANE CASES (the packet and `request` are lane I's). The workspace holds the build doc `docs/plans/2026-09-22-turnstile.md` and the scope doc `docs/scope/2026-09-20-turnstile.md`. The case directory holds `packet/`, a lane directory as the station would hand it to `request`, each document line-numbered (`N: `).

## I1-01-clean (lane)

`packet/` holds exactly `build-doc.md`, `scope-doc.md` and `code-book.md`.

## I1-02-summary-file (lane)

`packet/` holds the three files and `summary.md`.

## I1-03-prior-verdict (lane)

`packet/` holds the three files and `prior-verdict.md`.

## I1-04-repo-file (lane)

`packet/` holds the three files and `turnstile.py`, a copy of repo code.
