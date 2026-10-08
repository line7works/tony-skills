# H4-the-next-move: cases

Family H4 of the E15 seeded cases (lane contract section 12, row "H4 the next move"; handoff-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form, with `## Handoffs` before `## Punch list`). A case that commits a records log names it. The drive step runs the station from `select` (by the name `turnstile`) to `report`, on the case's recorded answer: its questions go to `gate` and its answers, perishables and assertions to `record-answer`.

## H4-01-clean

Slice A `signed off`, slice B `not started` and depending on A. No records log. The recorded answer brings nothing.

## H4-02-open-card

The records log (committed) holds slice A's card `signed off with conditions` and its MAJOR at `src/turnstile.py:2`, open; slice B depends on A. The recorded answer brings nothing.

## H4-03-loop-complete

Both slices `signed off`. No records log. The recorded answer brings nothing.

## H4-04-owner-names-the-next-slice

Slice A `signed off`; slice B `not started` depending on A; slice C `not started` depending on nothing. The recorded answer answers the record's next-slice question, in the owner's words, naming slice C.
