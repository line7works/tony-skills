# H2-the-question-gate: cases

Family H2 of the E15 seeded cases (lane contract section 12, row "H2 the question gate"; handoff-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form, with `## Handoffs` before `## Punch list`). A case that commits a records log names it. The drive step runs the station from `select` (by the name `turnstile`) to `report`, on the case's recorded answer: its questions go to `gate` and its answers, perishables and assertions to `record-answer`.

## H2-01-clean

Slice A `signed off`, slice B `not started` and depending on A. No records log. The recorded answer brings two session questions (a session question and a chat ruling) and answers both with notes in the owner's words, and one perishable.

## H2-02-one-unanswered

The same build. The recorded answer brings the same two questions, answers the first and marks the second not answered.

## H2-03-question-left-out

The same build. The recorded answer brings the same two questions and answers only the first; the second has no entry.

## H2-04-record-question-unanswered

Slice B's section holds one `Questions:` line. The recorded answer brings no session question and no answer.
