# L8-no-clock: cases

Family L8 of the E16 seeded cases (lane contract section 12, row "L8 no clock"; the join, part J2). 5 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The join's one fixture machine (`lifecycle/scripts/tests/test_join_sequence.seed`, through `_lib/caselib.joined`): the three lanes as they ship (`lifecycle/rows/sunrise`, `sunset` and `restore`, each `lane.json`) and every shipped declaration; every lane's fakes (slice 2's scaffolders, the recorded git and the adapter; slice 3's `gh`, `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests; slice 4's schedule tools); the locations of all three lanes; a vault with its root index, a memory index, a shortcut file wired into the shell startup, git's identity; the project's own memory store holding `MEMORY.md`; the host holding two values (`DATABASE_URL`, naming a database whose password is a canary, and `FEATURE`) for the project a sunrise makes, and that database with one table. The project is named `demo` in every place. Every summons carries `--also demo --also demo` and a capabilities file naming canary, memory stores and routines, unless a case names other capabilities. Nothing live: every provider is a fake and every path lies under `--out`.

Steps: the sunrise of the type `web app` (look, go), what the case plants, then a default sunset (look, go: no layer dropped, no flag), and where named a status summons.

## L8-01-clean

Nothing planted.

## L8-02-a-dump-cut-off

Before the sunset's look, the fake `pg_dump` is planned to write half of its dump.

## L8-03-a-failed-tag-push

Before the sunset's look, the fake GitHub's repository is given a hook of its own that turns away every tag pushed to it.

## L8-04-a-dump-of-another-database

After the sunrise, the fake `pg_dump` in the case's own program folder is a wrapper that, when it runs, first turns the fake database into another database (another identity, the table `beta` in place of `alpha`) and then dumps it; the inventory read made before it (`psql`) sees the database the project's env file names.

## L8-05-a-dump-that-cannot-be-bound

After the sunrise, the fake database answers no identity (its identity is none), so the source of the dump cannot be identified.

## Not buildable on fakes

Section 12's row names a clean case whose dump is "bound to the idled database", and for an unbindable dump "the dump kept, no idle call made, the preview saying so, and the rest of the run going on". The joined sunset lane holds no row that idles the database: its tombstone row's own words are "a database this run backed up is not paused by it (v1 never paused it itself)" (the owner's ruling "Keep as v1"). So no case holds an idle, an idle call or a binding of the dump to one. L8-04 and L8-05 hold the two source conditions against the database the run backs up, the condition alone, with no idle in them.
