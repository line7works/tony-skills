# H3-additive: cases

Family H3 of the E15 seeded cases (lane contract section 12, row "H3 additive"; handoff-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form, with `## Handoffs` before `## Punch list`). A case that commits a records log names it. The drive step runs the station from `select` (by the name `turnstile`) to `report`, on the case's recorded answer: its questions go to `gate` and its answers, perishables and assertions to `record-answer`.

## H3-01-clean

The build doc's `## Handoffs` holds one earlier block, dated 2026-09-25, committed. The recorded answer brings no question and one perishable.

## H3-02-earlier-block-edited

The same committed doc; the working copy (uncommitted) changes one line inside the earlier block.

## H3-03-block-outside-handoffs

A handoff block dated 2026-09-25 sits under `## Punch list`, committed; `## Handoffs` is empty.

## H3-04-block-edited-before-write

The same committed doc as H3-01; the drive step edits one line inside the earlier block after the answers are recorded and before the write, as a session's own edit would.
