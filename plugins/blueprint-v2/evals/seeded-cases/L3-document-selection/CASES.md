# L3-document-selection: cases

Family L3 of the E14 seeded cases (lane contract section 14, row "document selection"; blueprint-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

Every case holds a git workspace with `README.md`; the run selects with the hunt it names.

## L3-01-clean

One scope doc, `docs/scope/2026-09-20-turnstile.md`; the hunt `scope` with no name.

## L3-02-two-scope-docs-match

Two scope docs under `docs/scope/`, both about the turnstile (their `Intent:` lines both name the counter); the hunt `scope` with no name.

## L3-03-two-scope-homes-one-tier

One scope doc under `docs/scope/` and one at the older flat `docs/turnstile-scope.md`.

## L3-04-existing-build-doc

A build doc exists at `docs/plans/2026-09-22-turnstile.md`; the hunt `build` with the name `turnstile`.
