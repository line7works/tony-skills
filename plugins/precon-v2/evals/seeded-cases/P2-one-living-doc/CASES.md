# P2-one-living-doc: cases

Family P2 of the E14 seeded cases (lane contract section 14, row "one living doc"; precon-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

Every case holds a git workspace with `README.md` and an empty staging home unless it says otherwise; the run selects with the hunt `scope` and the name `turnstile`.

## P2-01-clean

No scope doc exists anywhere.

## P2-02-one-home

The scope doc exists once, at `docs/scope/2026-09-20-turnstile.md`.

## P2-03-two-homes

The scope doc exists at `docs/scope/2026-09-20-turnstile.md` in the workspace and as `turnstile-scope.md` in the staging home.

## P2-04-flat-home

The scope doc exists only at the older flat name `docs/turnstile-scope.md`.
