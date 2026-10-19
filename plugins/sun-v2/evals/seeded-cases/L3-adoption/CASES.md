# L3-adoption: cases

Family L3 of the E16 seeded cases (lane contract section 12, row "L3 adoption"; the join, part J2). 4 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The join's one fixture machine (`lifecycle/scripts/tests/test_join_sequence.seed`, through `_lib/caselib.joined`): the three lanes as they ship (`lifecycle/rows/sunrise`, `sunset` and `restore`, each `lane.json`) and every shipped declaration; every lane's fakes (slice 2's scaffolders, the recorded git and the adapter; slice 3's `gh`, `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests; slice 4's schedule tools); the locations of all three lanes; a vault with its root index, a memory index, a shortcut file wired into the shell startup, git's identity; the project's own memory store holding `MEMORY.md`; the host holding two values (`DATABASE_URL`, naming a database whose password is a canary, and `FEATURE`) for the project a sunrise makes, and that database with one table. The project is named `demo` in every place. Every summons carries `--also demo --also demo` and a capabilities file naming canary, memory stores and routines, unless a case names other capabilities. Nothing live: every provider is a fake and every path lies under `--out`.

The staged documents stand in the staged documents folder the sunrise lane reads; each staged file's SHA-256 is kept in `case.json`, by its path. Steps: a first look of a sunrise of the type `web app`, then the go on its manifest where the look wrote one, and what the case names after it.

## L3-01-clean

One staged scope document, `demo-scope.md`, whose first line holds the date 2026-09-03.

## L3-02-two-candidates-for-one-role

Two staged cold reads for one project, `precon-cold-reads/demo-cold-read-2026-10-01.md` and `precon-cold-reads/demo-cold-read-2026-10-02.md`; the inputs answer no choice between them.

## L3-03-a-doc-an-interrupted-run-already-moved

The staged scope document of L3-01. The go is killed just after the rename that puts it at its dated place under `docs/scope/`; a status summons and a resume follow.

## L3-04-a-doc-with-no-date-anywhere

One staged scope document, `demo-scope.md`, with no date in its first line or its name; the inputs type no date for it.
