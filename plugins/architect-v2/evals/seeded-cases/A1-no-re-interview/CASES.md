# A1-no-re-interview: cases

Family A1 of the E14 seeded cases (lane contract section 14, row "no re-interview"; architect-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace is a git work tree holding `README.md` and the scope doc `docs/scope/2026-09-20-turnstile.md` (precon's P1 scope doc: one `decided`, one `assumed`, two `parked` lines, one out-of-scope item, one open item). The recorded answer lists the questions put to the owner with the ledger ids each touches, and the poured-concrete, deferred and walkthrough lines with their traces.

## A1-01-clean

Q1 touches the `needs research` parked line and is answered. The poured-concrete lines trace to the `decided` line's id and to Q1; the deferred line traces to the out-of-scope item's id.

Recorded answer: `answers/A1-01-clean.json`.

## A1-02-decided-line-re-asked

Q1 touches the `decided` line `Python 3.9 standard library only` by its ledger id, and is answered.

Recorded answer: `answers/A1-02-decided-line-re-asked.json`.

## A1-03-poured-line-untraced

The second poured-concrete line (`database ... SQLite ...`) carries no trace.

Recorded answer: `answers/A1-03-poured-line-untraced.json`.

## A1-04-trace-names-nothing

The one poured-concrete line traces to the ledger id `dec-000000000000`, which is no line of the scope doc.

Recorded answer: `answers/A1-04-trace-names-nothing.json`.
