# V5-the-word: cases

Family V5 of the E15 seeded cases (lane contract section 12, row "V5 the word"; vertical-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

As V2's clean shape; the readers' calls all come back `ok`.

## V5-01-clean

The owner's answer names `gpt-astra`; the executor asks for the outside requests with no row named.

Recorded answer: `answers/V5-01-clean.json`.

## V5-02-claude-row-named

The owner's answer names `claude-opus` as its one outside reviewer.

Recorded answer: `answers/V5-02-claude-row-named.json`.

## V5-03-row-not-named

The owner's answer names `gpt-astra`; the executor asks for an outside request on `gemini`.

Recorded answer: `answers/V5-03-row-not-named.json`.
