# L2-never-clobber: cases

Family L2 of the E16 seeded cases (lane contract section 12, row "L2 never clobber"; the join, part J2). 6 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The join's one fixture machine (`lifecycle/scripts/tests/test_join_sequence.seed`, through `_lib/caselib.joined`): the three lanes as they ship (`lifecycle/rows/sunrise`, `sunset` and `restore`, each `lane.json`) and every shipped declaration; every lane's fakes (slice 2's scaffolders, the recorded git and the adapter; slice 3's `gh`, `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests; slice 4's schedule tools); the locations of all three lanes; a vault with its root index, a memory index, a shortcut file wired into the shell startup, git's identity; the project's own memory store holding `MEMORY.md`; the host holding two values (`DATABASE_URL`, naming a database whose password is a canary, and `FEATURE`) for the project a sunrise makes, and that database with one table. The project is named `demo` in every place. Every summons carries `--also demo --also demo` and a capabilities file naming canary, memory stores and routines, unless a case names other capabilities. Nothing live: every provider is a fake and every path lies under `--out`.

Steps: a first look of a sunrise of the type `web app` (shortcut `dm`); in every case but the clean one, the go on its manifest where the look wrote one.

## L2-01-clean

Nothing planted. The look alone.

## L2-02-an-existing-local-folder

A folder stands at the project's place under the developer root, holding one file of his.

## L2-03-an-existing-remote

A repository named `demo` stands at the fake GitHub under the fixture account, with another's commit on its `main`.

## L2-04-a-taken-project-name-on-the-host

A project named `demo` stands at the fake host under another account id.

## L2-05-a-shortcut-that-shadows-a-program

A program named `dm`, the shortcut's name, stands in a folder that his login file (`~/.zprofile`) puts on his login zsh's path.

## L2-06-the-owners-own-identical-line-already-present

The vault's root index already holds, under its active projects heading, the very line a sunrise of `demo` adds there.
