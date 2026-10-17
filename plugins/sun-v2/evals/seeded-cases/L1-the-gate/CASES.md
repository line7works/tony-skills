# L1-the-gate: cases

Family L1 of the E16 seeded cases (lane contract section 12, row "L1 the gate"; the lifecycle frame, slice 1). 5 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case.

## Shared shape

A fixture machine: a home with a settings file, a vault with its marker file and its projects folder, a developer root, and the fake rows of the reference run (eight rows: two checks, a build, a swap, a move, a create, a compare-and-swap, a refusing call). One step is driven: a first look of a sunrise named `demo`.

## L1-01-clean

Nothing planted.

## L1-02-no-vault

The vault folder is removed.

## L1-03-stub-without-its-marker

The vault's marker file is removed; the folder and its projects folder stay.

## L1-04-vault-in-a-synced-folder

The vault is moved under a folder the settings file lists as synced, and the settings file names it there.

## L1-05-marker-but-no-projects-folder

The vault's projects folder is removed; its marker file stays.
