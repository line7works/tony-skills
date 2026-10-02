# V2-base-and-scope: cases

Family V2 of the E15 seeded cases (lane contract section 12, row "V2 base and scope"; vertical-v2). 5 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

As V1's shape, with no records log. Where a case says so, `main` carries a second commit (changing `src/legacy.py`) before the branch is cut.

## V2-01-clean

The build doc records no base. The branch is cut from `main`'s only commit. The tree is clean.

## V2-02-doc-recorded-base

`main` has two commits; the branch is cut from the second. The build doc's header carries `Base: <the first commit>`.

## V2-03-no-base

The build is committed on `main` itself; there is no other branch, the build doc records no base, and the input carries no base from the owner.

## V2-04-dirt-inside

After the build commit, `src/spinner.py` (a file the build added) is edited and not committed.

## V2-05-dirt-outside

After the build commit, `src/legacy.py` (a base file the build did not touch) is edited and `notes.txt` is created; neither is committed.
