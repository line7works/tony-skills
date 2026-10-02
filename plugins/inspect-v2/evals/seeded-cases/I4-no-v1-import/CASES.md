# I4-no-v1-import: cases

Family I4 of the E14 seeded cases (lane contract section 14, row "no v1 import"; inspect-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

Each case scans a scratch copy of this core's skill (SKILL.md, references/, adapters/, scripts/) with the no-v1-import test's scan, after planting the text the case names.

## I4-01-clean

Nothing is planted.

## I4-02-planted-v1-folder

A line naming a v1 plugin folder is appended to `references/station-loop.md`.

## I4-03-planted-deference

A deference sentence is appended to `SKILL.md`.

## I4-04-planted-subprocess

A subprocess call whose argv names a v1 slash command is appended to `scripts/station_core/exits.py`.
