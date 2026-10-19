# L0-the-verified-baseline: cases

Family L0 of the E16 seeded cases (lane contract section 12, row "L0 the verified baseline"; the join, part J2). 5 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome. Section 12 gives this family no planted condition ("the clean case is the family"): each case is one sunrise of one of the sunrise lane's four project types, the scaffold the type's own, with hosting, end to end.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The join's one fixture machine (`lifecycle/scripts/tests/test_join_sequence.seed`, through `_lib/caselib.joined`): the three lanes as they ship (`lifecycle/rows/sunrise`, `sunset` and `restore`, each `lane.json`) and every shipped declaration; every lane's fakes (slice 2's scaffolders, the recorded git and the adapter; slice 3's `gh`, `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests; slice 4's schedule tools); the locations of all three lanes; a vault with its root index, a memory index, a shortcut file wired into the shell startup, git's identity; the project's own memory store holding `MEMORY.md`; the host holding two values (`DATABASE_URL`, naming a database whose password is a canary, and `FEATURE`) for the project a sunrise makes, and that database with one table. The project is named `demo` in every place. Every summons carries `--also demo --also demo` and a capabilities file naming canary, memory stores and routines, unless a case names other capabilities. Nothing live: every provider is a fake and every path lies under `--out`.

Steps: a first look of a sunrise, then the go on its manifest.

## L0-01-clean

The type `web app`, its scaffold `web app`.

## L0-02-a-static-site

The type `static site`, its scaffold `static site`.

## L0-03-a-desktop-app

The type `desktop app`, its scaffold `desktop app`.

## L0-04-a-script-or-cli

The type `script or CLI`, its scaffold `script or CLI`.

## L0-05-a-harness-that-declares-no-canary

The type `web app`. The capabilities file of every summons names memory stores and routines, and no canary.

## Not buildable on fakes

Section 12's row: "the kit check passes (on a harness without the canary capability the canary line is `unavailable` and the summary says so; the frame's OP-8)". What a fixture can hold is the harness's declaration: L0-05's capabilities file names no canary. A harness itself, found without the capability by anything other than what it declares, is not on this machine; no case holds one.
