---
name: sunset-v2
description: Skeleton only (E16 slice 1). Retires a project as a run of explicit operations on the sun-v2 lifecycle frame, with a restore that is a run of its own. Its contract is to be written by the sunset lane; do not use this skill yet.
---

# sunset-v2 (skeleton)

This file is a placeholder written with the lifecycle frame (E16 slice 1). **Its contract is to be written**
by the lane that builds the rows of a retirement and of a restore (E16 slice 4); nothing here is a
procedure, and no executor should act on it. Whether a restore is a third skill or a summons of this
one is that lane's to say; the list of skills is data, in `../../lifecycle/skills.json`.

What exists today, and where:

- The lifecycle frame both skills of this plugin run on: `../../lifecycle/scripts/sun.py` (run it with
  `--help` for its commands, arguments, defaults, side effects and exit codes).
- The frozen schemas of every record a lane writes or reads: `../../lifecycle/references/`.
- No rows: `../../lifecycle/rows/` is the lanes' to write. Until it holds a lane for this kind of run, a
  look ends with exit 4 and the finding that no lane has written rows.
