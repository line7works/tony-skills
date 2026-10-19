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
- The rows of a retirement and of a restore (E16 slice 4): `../../lifecycle/rows/sunset/lane.json` and
  `../../lifecycle/rows/restore/lane.json`, with the declarations of the schedule tools and the adapter in
  `../../lifecycle/rows/providers/`. Slice 3's rows join them at slice 5.

What the lane's rows need of this skill (rows-set C2, C3, C10, section 4, and the owner's ruling on trackers, A152):

- A restore is a summons of this skill, `--kind restore`, with the same names as the sunset, on the machine that
  holds the sunset's run directory.
- The names go in this order: the repository folder (`--name`), then the vault folder and the memory note's stem
  (`--also`, in that order). Resolve them and confirm them with the owner before the summons.
- His one-line reason is the input `description`. A not-proven line he asks the restore to reverse goes in its
  input `restore_lines`. His "archive it as it is" is the flag `archive_as_is`.
- His `--keep-github`, `--keep-vercel` and `--keep-db` are the layers they keep out of the run, given in `drop_layers` as
  `github`, `hosting` and `database`; `--keep-local` drops `repository`, `memory store` and `shortcut`.
- In the summary you give the owner, mention any other tracker you notice in the repository, beyond the hosting config files the tool lists; add no tool step for it and do not act on it.
