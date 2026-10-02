# A3-the-living-doc: cases

Family A3 of the E14 seeded cases (lane contract section 14, row "the living doc"; architect-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace holds the scope doc and the architecture doc `docs/architecture/2026-09-21-turnstile.md` with two run-log blocks (Run 1, Run 2) and two poured-concrete lines. The case directory holds `proposed.md`, a whole proposed document after a re-run, and `block.md`, the run block the re-run would append.

## A3-01-clean

`proposed.md` keeps both run blocks byte for byte, strikes the `storage` poured-concrete line through (`~~...~~`), adds a new `storage` line, and appends `### Run 3`. `block.md` is that Run 3 block.

## A3-02-drops-a-run-block

`proposed.md` holds no `### Run 1` and no `### Run 2` block; it holds a `### Run 3` block.

## A3-03-deletes-a-poured-line

`proposed.md` deletes the `storage` poured-concrete line (neither kept nor struck through).

## A3-04-wrong-run-number

`block.md` opens `### Run 2` while the doc already holds Run 1 and Run 2.
