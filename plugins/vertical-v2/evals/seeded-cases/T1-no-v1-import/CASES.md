# T1-no-v1-import: cases

Family T1 of the E15 seeded cases (lane contract section 12, row "T1 no v1 import"; vertical-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

A scratch copy of this core's skill folder, scanned by `scripts/tests/test_no_v1_import.py`'s scan, with the case's plant appended to one file. The plant's text is assembled from parts, so no case file names a v1 folder.

## T1-01-clean

No plant.

## T1-02-back-half-folder

`references/vertical-contract.md` gains a line naming the v1 vertical plugin folder as a place to read.

## T1-03-deference

`SKILL.md` gains a sentence deferring to another skill's file as law where this file is silent.

## T1-04-codex-mention

`scripts/vertical.py` gains a subprocess call whose argv names the v1 ship skill as a Codex skill mention.
