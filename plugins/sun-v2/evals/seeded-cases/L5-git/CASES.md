# L5-git: cases

Family L5 of the E16 seeded cases (lane contract section 12, row "L5 git"; the join, part J2). 4 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py --out <dir> --all` drives each case and prints, with the rest, the recorded git calls that change a repository, every push, the scaffolder's calls, the git commands each operation of the manifest lists, and the fake GitHub's refs.

## Shared shape

The join's one fixture machine (`lifecycle/scripts/tests/test_join_sequence.seed`, through `_lib/caselib.joined`): the three lanes as they ship (`lifecycle/rows/sunrise`, `sunset` and `restore`, each `lane.json`) and every shipped declaration; every lane's fakes (slice 2's scaffolders, the recorded git and the adapter; slice 3's `gh`, `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests; slice 4's schedule tools); the locations of all three lanes; a vault with its root index, a memory index, a shortcut file wired into the shell startup, git's identity; the project's own memory store holding `MEMORY.md`; the host holding two values (`DATABASE_URL`, naming a database whose password is a canary, and `FEATURE`) for the project a sunrise makes, and that database with one table. The project is named `demo` in every place. Every summons carries `--also demo --also demo` and a capabilities file naming canary, memory stores and routines, unless a case names other capabilities. Nothing live: every provider is a fake and every path lies under `--out`.

Steps: a first look of a sunrise of the type `web app`, then the go on its manifest where the look wrote one, and what the case names after it.

## L5-01-clean

Nothing planted.

## L5-02-a-remote-that-already-has-a-commit

A repository named `demo` stands at the fake GitHub under the fixture account, with another's commit on its `main`.

## L5-03-a-tracked-edit-after-the-push

The go is killed just after the push operation's final record is on disk; then a tracked file of the project, `README.md`, is edited by hand; a status summons and a resume follow.

## L5-04-a-secret-in-a-commit-to-be-pushed

His folder stands at the project's place and the inputs adopt it: a repository on `main` whose one commit holds `notes.txt` with a canary, and an ignored `.env.local` whose `DATABASE_URL` is that canary.

## Not buildable on fakes

Section 12's row names "a tracked edit needed after the push". No row of the joined sunrise lane edits a tracked file after the push: the rows after it write the env file (ignored) and the layers outside the project. L5-03 holds what the fakes can hold, the edit made by another hand after the push.
