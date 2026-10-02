---
name: ship-v2
description: >-
  Run one whole slice loop on the v2 stations with a single command: find the build doc, build-v2 the
  named slice, signoff-v2, fix every BLOCKER and MAJOR, recheck-v2, at most one extra fix-and-recheck
  lap, then report, with a trace that names only v2 stations. Use when the user says "/ship-v2 A",
  "ship slice B of docs/plan.md", or wants the full build, signoff, fix, recheck loop run on one slice
  without typing the chain by hand.
---

# Ship v2 (the back frame's skeleton)

This core is not built yet. Its contract, references/ship-contract.md, is to be written by slice 2 of
the E15 step (the E15 lane contract, section 10). Until then every phase of `scripts/ship.py` answers
`phase-not-built` (exit 10) and reads and writes nothing.

**When summoned now:** say that ship-v2 is not built yet, write nothing, and stop. Do not run the loop
by hand and do not reach for any other station in its place.

What exists today is the back frame this core shares with vertical-v2 and handoff-v2:
`references/back-loop.md` (the discipline), `references/back-files.txt` (the shared files),
`references/trace.schema.json`, the adapters for Claude Code and Codex (`adapters/README.md`), and
the setups beside the skill.
