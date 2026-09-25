---
name: blueprint-v2
description: >-
  Draft a build document in dependency-ordered, verifiable slices from a feature discussion: the
  doc that build executes slice by slice and signoff grades against, every requirement carrying
  its trace to the scope doc, the repo, or a question answered in the run. Use when the user says
  draft a build doc, blueprint this, slice this up, write the build plan, or finishes discussing
  a feature and wants it scoped into slices. Not a plan check (inspect-v2), not the build itself,
  and not the bare /blueprint command, which belongs to the v1 station.
---

# Blueprint v2

This station is the front of the build loop: it turns a feature discussion into the sliced build doc the downstream stations consume, written for a builder who was never in the room. It reads the scope doc, the architecture doc, and an existing build doc for the feature; it writes the build doc.

**This file is the frame (E14 slice 1).** The station's own steps, rules and gates arrive in its
slice 2 lane; until then the phases a lane fills stop as `phase-not-built` and this station does
nothing for the owner. Say so and stop.

**When to run.** Run it when the owner asks for a build document in the words its description names.

**The spine.** The executor decides, the script records (rule E14-4). You talk to the owner and
judge; `scripts/blueprint.py` does everything deterministic: it validates the input, finds the
documents, reads the scope doc's ledger, renders and parses the load-bearing forms, checks your one
recorded answer, and writes. It writes no event and never opens the shared records component (`references/station-loop.md` section 10).

## The loop

Every run walks the same phases, each a command of `scripts/blueprint.py` (run with `uv run`):

1. `check-input <input.json>`: one validated input (`references/input.schema.json`). The
   `invocation` block comes from your harness's adapter (`adapters/README.md`); type none of it.
2. `select --run-dir D --hunt <hunt>`: find the documents this station reads. `several` is listed
   for the owner and never picked.
3. `harvest --run-dir D`: read what exists before asking anything (slice 2).
4. `record-answer --run-dir D --answer FILE`: your one recorded answer, checked; a question that
   re-asks a decided ledger line, or a line with no trace, is refused (slice 2).
5. `write --run-dir D`: the documents, rendered from the templates in `references/templates/`
   (slice 2).
6. `report --run-dir D`: the result, validated, and the chat block rendered from it (slice 2).

`identity <workspace>` and `skill-identity` answer at any time.

## The references

- `references/station-loop.md`: the contract every front station shares: the phases, the exit
  codes, the input and result, report-only, the stop vocabulary, the rules, the hand-offs.
- `references/templates/scope-doc.md`, `references/templates/architecture-doc.md`,
  `references/templates/build-doc.md`, `references/templates/inspect-lines.md`: the load-bearing
  forms, byte for byte, with v1's reading beside each.
- `references/input.schema.json`, `references/result.schema.json` and `references/examples/`.
- `adapters/README.md`: which adapter serves the harness you run in.

## Boundaries

- No web, no research, no model call and no harness launch from a script. A reader, where this
  station uses one, is summoned through `/readers` with the request the script builds.
- Never write a document by hand: the script renders every load-bearing form.
- The gate is real: read back and stop. Never start the next station.
