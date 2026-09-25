---
name: architect-v2
description: >-
  The drawings step: one interview after precon that produces the architecture-and-delivery doc
  the downstream stations consume, plus a visual of what was decided, with the scope doc's
  decided lines passed forward by script and never re-asked. Use only when the owner types
  /architect-v2 by name. Strictly user-invoked: never auto-invoke, suggest-invoke, or trigger
  from conversation shape, no matter how architecture-shaped the discussion looks. Not the scope
  doc (precon-v2), not the sliced plan (blueprint-v2), not provisioning, and not the v1 architect
  station.
disable-model-invocation: true
---

# Architect v2

This station is the drawings step: from the scope doc it draws the least structure that serves a named first user's walkthrough, settles the one-way doors for the whole vision, and keeps one living architecture doc with its run log. It reads the scope doc (precon's) and an existing architecture doc for the slug; it writes the architecture doc, its local visual, and the blind reviews' files.

**This file is the frame (E14 slice 1).** The station's own steps, rules and gates arrive in its
slice 2 lane; until then the phases a lane fills stop as `phase-not-built` and this station does
nothing for the owner. Say so and stop.

**When to run.** Run it only when the owner types it by name. Never invoke it on your own, never suggest invoking it, and never start it because a discussion looks ready.

**The spine.** The executor decides, the script records (rule E14-4). You talk to the owner and
judge; `scripts/architect.py` does everything deterministic: it validates the input, finds the
documents, reads the scope doc's ledger, renders and parses the load-bearing forms, checks your one
recorded answer, and writes. It writes no event and never opens the shared records component (`references/station-loop.md` section 10).

## The loop

Every run walks the same phases, each a command of `scripts/architect.py` (run with `uv run`):

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
