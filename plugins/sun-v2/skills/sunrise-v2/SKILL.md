---
name: sunrise-v2
description: Skeleton only (E16 slice 1). Starts a project as a run of explicit operations on the sun-v2 lifecycle frame. Its contract is to be written by the sunrise lane; do not use this skill yet.
---

# sunrise-v2 (skeleton)

This file is a placeholder written with the lifecycle frame (E16 slice 1). **Its contract is to be written**
by the lane that builds sunrise's rows (E16 slices 2 and 3); nothing here is a procedure, and no executor
should act on it.

What exists today, and where:

- The lifecycle frame both skills of this plugin run on: `../../lifecycle/scripts/sun.py` (run it with
  `--help` for its commands, arguments, defaults, side effects and exit codes).
- The frozen schemas of every record a lane writes or reads: `../../lifecycle/references/`.
- Sunrise's local rows (slice 2): `../../lifecycle/rows/sunrise/lane.json`, with the scaffold's declarations in
  `../../lifecycle/rows/providers/scaffold.json`. Git's and the hosting's declarations, and the remote rows, are slice
  3's; until the join adds them a look of this lane ends with exit 4 and the finding that a command has no declaration.

## What an executor gives a sunrise look (slice 2's rows, rows-rise 3.0)

- The three names, by place: `--name <Name> --also <slug> --also <slug_>`, in that order (the rows read them as 0, 1, 2).
- In the inputs file: `description`, his one line (required); `type`, one of `web app`, `static site`, `desktop app`,
  `script or CLI` (another is refused before the look reads anything); `answers.shortcut`, 2 to 5 lowercase letters or
  digits. All three are asked before the preview; nothing is asked after his go.
- `flags.scaffold`: the type's own word, or `static site, single file` or `script or CLI, Python` where he asks for that
  scaffold; where he names an existing folder instead, `adopted`, with that folder's full path as
  `adopt."project folder"`.
- `drop_layers`, `flags.hosting` and `flags.local_proof`, from his flags: `--no-db` drops `database`; `--no-vercel` drops
  `hosting` and `database`; `--no-github` drops `github`, `hosting` and `database`. A static site and a script have no
  `database`; a script has no `hosting`. `flags.hosting` is false where `hosting` is dropped or the type has none, and
  then `flags.local_proof` is, by the scaffold, `build next`, `build astro`, `build electron`, `npm`, `uv` or `html`.
- `flags.public`: `true` only where he asks for a public GitHub repository (v1's `--public`); leave it out otherwise, and
  the repository is private.
- The capabilities file names `canary` where the harness can have a fresh session quote a project's first instruction
  line, and `memory stores` where it keeps memory notes.
- `--dry-run` is the look alone: show its preview and stop.
