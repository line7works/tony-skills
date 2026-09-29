# I2-the-no-record-rule: cases

Family I2 of the E14 seeded cases (lane contract section 14, row "the no-record rule"; inspect-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace holds the build doc `docs/plans/2026-09-22-turnstile.md`. The recorded reader answer is the traceability lens's reply, with its `findings` (each `severity`, `location`, `claim`, `scenario`, `confidence`), its `row`, `call_id` and `effective_model`. The run selects with the hunt `scope`.

## I2-01-clean (lane)

A scope doc exists at `docs/scope/2026-09-20-turnstile.md`; the reader answer holds no finding.

Recorded answer: `answers/I2-01-clean.json`.

## I2-02-no-scope-doc (lane)

No scope doc exists in any home. The reader answer holds one `BLOCKER` at `build-doc.md:8` claiming R1 traces to nothing in the record.

Recorded answer: `answers/I2-02-no-scope-doc.json`.

## I2-03-no-scope-doc-no-finding (lane)

No scope doc exists in any home. The reader answer holds no finding.

Recorded answer: `answers/I2-03-no-scope-doc-no-finding.json`.
