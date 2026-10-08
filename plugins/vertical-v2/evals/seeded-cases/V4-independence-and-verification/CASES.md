# V4-independence-and-verification: cases

Family V4 of the E15 seeded cases (lane contract section 12, row "V4 independence and verification"; vertical-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

As V2's clean shape. The owner's recorded answer names `gpt-astra`. The readers' half of the recorded answer gives each call `ok` and a raw text; the executor's half gives the local answer (no finding, what each lens tried) and the outside answer attempts in order.

## V4-01-clean

The outside answer holds one finding at `src/turnstile.py:4`, stamped CONFIRMED, credited to the gpt-astra call.

Recorded answer: `answers/V4-01-clean.json`.

## V4-02-outside-before-local

After the local requests are built, the executor asks for the outside requests before recording the local answer.

Recorded answer: `answers/V4-02-outside-before-local.json`.

## V4-03-hallucinated-location

The first outside answer stamps a finding at `src/ghost.py:9` (a path the build never had) CONFIRMED; the second attempt stamps the same finding REFUTED with its reason.

Recorded answer: `answers/V4-03-hallucinated-location.json`.
