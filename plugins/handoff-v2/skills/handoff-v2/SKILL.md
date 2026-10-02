---
name: handoff-v2
description: >-
  End-of-slice thread prep for the build loop on the v2 foundation: the photograph rebuilt from the
  records and git, the question gate, one dated block in the build doc and the kickoff line for the
  fresh session. STRICTLY user-invoked, only when the owner summons it ("/handoff-v2", "prep for the
  next slice", "prep the repo for slice X", "clear the thread and prep", "get ready for slice X",
  "get ready for the next slice"); never auto-invoke, suggest-invoke, or trigger from conversation
  shape. Not for machine settle-up or account switches, and not for cross-machine hand-offs.
disable-model-invocation: true
---

# Handoff v2 (the back frame's skeleton)

This core is not built yet. Its contract, references/handoff-contract.md, is to be written by the
hand-back that builds it (the E15 lane contract, section 9). Until then every phase of
`scripts/handoff.py` answers `phase-not-built` (exit 10) and reads and writes nothing.

**When summoned now:** say that handoff-v2 is not built yet, write nothing, and stop. Do not take the
handoff by hand and do not reach for any other station in its place.

What exists today is the back frame this core shares with vertical-v2 and ship-v2:
`references/back-loop.md` (the discipline), `references/back-files.txt` (the shared files),
`references/trace.schema.json`, the adapters for Claude Code and Codex (`adapters/README.md`), and
the setups beside the skill.
