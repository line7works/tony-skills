# A2-candidates-and-the-razor: cases

Family A2 of the E14 seeded cases (lane contract section 14, row "candidates and the razor"; architect-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `/usr/bin/python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

LANE CASES (the razor and the candidates are lane A's behavior). The workspace holds the scope doc `docs/scope/2026-09-20-turnstile.md`. The recorded answer carries `exit_ramp`, `walkthrough` (`who`, `when`, `must`), `candidates` (each `name`, `categories`, `assumes`, `later_cost`), `pick`, `rejected` (each `name`, `why`) and `components` (each `name`, `serves`).

## A2-01-clean (lane)

Two candidates that differ in the `platform` category (and `storage`); both components name a walkthrough item.

Recorded answer: `answers/A2-01-clean.json`.

## A2-02-one-candidate (lane)

One candidate only.

Recorded answer: `answers/A2-02-one-candidate.json`.

## A2-03-same-category (lane)

Two candidates whose `categories` are the same single value: they differ in no one-way-door category.

Recorded answer: `answers/A2-03-same-category.json`.

## A2-04-component-serves-nothing (lane)

Two valid candidates; the component `metrics exporter` names no walkthrough item (`serves` empty).

Recorded answer: `answers/A2-04-component-serves-nothing.json`.
