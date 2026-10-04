# H1-the-record-over-the-recollection: cases

Family H1 of the E15 seeded cases (lane contract section 12, row "H1 the record over the recollection"; handoff-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree: `main` holds the base (`README.md`, `src/turnstile.py`); the branch `feat` holds the build (a changed `src/turnstile.py` and the build doc `docs/plans/2026-09-20-turnstile.md`, made from the build-doc form, with `## Handoffs` before `## Punch list`). A case that commits a records log names it. The drive step runs the station from `select` (by the name `turnstile`) to `report`, on the case's recorded answer: its questions go to `gate` and its answers, perishables and assertions to `record-answer`.

## H1-01-clean

The records log (committed) holds slice A's card `signed off with conditions` and its one MAJOR at `src/turnstile.py:2`, open. The recorded answer waives that MAJOR in the owner's words (a chat ruling) and asserts slice A's and slice B's cards, the open item, the branch `feat`, two commits ahead and a clean tree.

## H1-02-asserted-card

The same build and log. The recorded answer waives the MAJOR and asserts slice A's card as `signed off`.

## H1-03-asserted-open-item

The same build and log. The recorded answer waives the MAJOR and asserts `src/turnstile.py:9` open.

## H1-04-asserted-branch

The same build and log. The recorded answer waives the MAJOR and asserts the branch `main`.
