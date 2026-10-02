# I3-records-and-the-stamp: cases

Family I3 of the E14 seeded cases (lane contract section 14, row "records and the stamp"; inspect-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

LANE CASES (verify, the records append and the stamp are lane I's). The workspace is a git work tree holding the build doc `docs/plans/2026-09-22-turnstile.md` and the scope doc `docs/scope/2026-09-20-turnstile.md`. The recorded reader answer carries its `findings`, `row`, `call_id` and `effective_model`.

## I3-01-clean (lane)

One MAJOR at `build-doc.md:10`, which is the doc's `R1` line (the claim names AC1, which is line 12).

Recorded answer: `answers/I3-01-clean.json`.

## I3-02-citation-matches-nothing (lane)

One MAJOR at `build-doc.md:99`; the numbered build doc has 22 lines.

Recorded answer: `answers/I3-02-citation-matches-nothing.json`.

## I3-03-no-effective-model (lane)

The reader answer's `effective_model` is null.

Recorded answer: `answers/I3-03-no-effective-model.json`.
