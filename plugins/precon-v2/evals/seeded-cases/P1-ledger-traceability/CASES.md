# P1-ledger-traceability: cases

Family P1 of the E14 seeded cases (lane contract section 14, row "ledger traceability"; precon-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree holding `README.md`, `src/turnstile.py` and the scope doc `docs/scope/2026-09-20-turnstile.md`, whose `Decisions:` holds one `decided` line, one `assumed` line and two `parked` lines (`needs research`; `waiting on the bench rig's encoder spec`), whose `Out of scope:` holds one item and whose `Open:` holds one item.

## P1-01-clean

The recorded answer asks one question (Q1, answered) touching the `needs research` parked line, and asserts five lines: the decided line by its ledger id; the parked line as decided by its ledger id; one line traced to Q1; one line traced to the repo path `src/turnstile.py`; one `assumed` line with its why.

Recorded answer: `answers/P1-01-clean.json`.

## P1-02-no-source

The recorded answer asks no question and asserts two lines: the decided line by its ledger id, and the line `Counts are written to the bench log` tagged `decided` with no `trace` key at all.

Recorded answer: `answers/P1-02-no-source.json`.

## P1-03-parked-quietly-resolved

The recorded answer asks no question and asserts the `waiting on` parked line as `decided`, traced to that parked line's own ledger id.

Recorded answer: `answers/P1-03-parked-quietly-resolved.json`.

## P1-04-untaggable-ledger-line

The scope doc is P1's with one change: the third `Decisions:` line ends `parked: later` (line 7).
