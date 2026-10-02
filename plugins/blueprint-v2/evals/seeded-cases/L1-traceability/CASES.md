# L1-traceability: cases

Family L1 of the E14 seeded cases (lane contract section 14, row "traceability"; blueprint-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree holding `README.md`, `src/turnstile.py` and the scope doc `docs/scope/2026-09-20-turnstile.md` (precon's P1 scope doc). The recorded answer's `lines` are the build doc's requirements, constraints and out-of-scope lines, each with its trace; its `criteria` are the acceptance criteria, each with its `verify` form when it has one.

## L1-01-clean

Four lines, traced to Q1 (answered), to the decided ledger line, to the repo path `src/turnstile.py`, and to the out-of-scope ledger item; one criterion with its `verify` form.

Recorded answer: `answers/L1-01-clean.json`.

## L1-02-requirement-untraced

The requirement `R2 ... counts are exported as CSV` carries no trace.

Recorded answer: `answers/L1-02-requirement-untraced.json`.

## L1-03-criterion-without-verify (lane)

LANE CASE. The one criterion carries no `verify` form. Every line is traced.

Recorded answer: `answers/L1-03-criterion-without-verify.json`.

## L1-04-repo-path-missing

The one requirement traces to the repo path `src/reset.py`, which the workspace does not hold.

Recorded answer: `answers/L1-04-repo-path-missing.json`.
