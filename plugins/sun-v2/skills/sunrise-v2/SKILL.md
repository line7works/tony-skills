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
- No rows: `../../lifecycle/rows/` is the lanes' to write. Until it holds a lane for this kind of run, a
  look ends with exit 4 and the finding that no lane has written rows.
