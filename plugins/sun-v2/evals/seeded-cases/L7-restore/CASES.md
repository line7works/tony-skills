# L7-restore: cases

Family L7 of the E16 seeded cases (lane contract section 12, row "L7 restore"; the join, part J2). 5 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case and prints, with the rest, a snapshot of the fixture home, the fakes and the named facts (the schedule layers among them, by name) after the sunrise and again after the sunset.

## Shared shape

The join's one fixture machine (`lifecycle/scripts/tests/test_join_sequence.seed`, through `_lib/caselib.joined`): the three lanes as they ship (`lifecycle/rows/sunrise`, `sunset` and `restore`, each `lane.json`) and every shipped declaration; every lane's fakes (slice 2's scaffolders, the recorded git and the adapter; slice 3's `gh`, `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests; slice 4's schedule tools); the locations of all three lanes; a vault with its root index, a memory index, a shortcut file wired into the shell startup, git's identity; the project's own memory store holding `MEMORY.md`; the host holding two values (`DATABASE_URL`, naming a database whose password is a canary, and `FEATURE`) for the project a sunrise makes, and that database with one table. The project is named `demo` in every place. Every summons carries `--also demo --also demo` and a capabilities file naming canary, memory stores and routines, unless a case names other capabilities. Nothing live: every provider is a fake and every path lies under `--out`.

After the sunrise, the set lane's schedule layers are planted for the project as its own fixture plants them: a launch agent `com.fixture.demo` whose program stands in the project's folder and another's `com.fixture.other`, both loaded at the fake launchd; a crontab of two lines, another's and one running a script in the project's folder; two routines of the fake adapter, one whose text names the project's folder.

Steps: the sunrise of the type `web app` (look, go), the schedule layers planted, a snapshot, the sunset (look, go, with his reason the sunrise's description), a snapshot, what the case plants, then the restore (look, go) and what the case names after it.

## L7-01-clean

Nothing planted.

## L7-02-an-expired-provider-state

After the sunset, the project is gone from the fake host, as a provider removes a thing whose time ran out.

## L7-03-a-line-someone-edited-after-sunset

After the sunset, the status line of the archived vault folder's index file, `status: archived`, is edited by hand to `status: archived, edited by hand`.

## L7-04-the-old-name-taken

After the sunset, a new folder stands at the project's old place under the developer root, holding another project's file.

## L7-05-a-kill-mid-restore

The restore's go is killed just after the start record of the operation that moves the vault folder back (`V02`) is on disk; a status summons and a resume follow.
