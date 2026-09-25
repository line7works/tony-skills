---
name: precon-v2
description: >-
  The pre-construction meeting: harvest a free-flowing idea discussion into a fixed-format scope
  doc that blueprint can later consume, every ledger line traced to the owner's words or an
  answered question. Use only when the owner types /precon-v2 by name. Strictly user-invoked:
  never auto-invoke, suggest-invoke, or trigger from conversation shape, no matter how idea-like
  the discussion looks. Not the drawings (architect-v2), not the sliced build doc (blueprint-v2),
  and not the v1 precon station.
disable-model-invocation: true
---

# Precon v2

This station is the idea stage: it harvests a free-flowing discussion into the scope doc, asks only the load-bearing questions that remain, and lands every settled decision in the doc's ledger with its source. It reads an existing scope doc for the idea's slug, to continue it in place; it writes the scope doc (and the cold-read doc of its exit test).

**This file is the frame (E14 slice 1).** The station's own steps, rules and gates arrive in its
slice 2 lane; until then the phases a lane fills stop as `phase-not-built` and this station does
nothing for the owner. Say so and stop.

**When to run.** Run it only when the owner types it by name. Never invoke it on your own, never suggest invoking it, and never start it because a discussion looks ready.

**The spine.** The executor decides, the script records (rule E14-4). You talk to the owner and
judge; `scripts/precon.py` does everything deterministic: it validates the input, finds the
documents, reads the scope doc's ledger, renders and parses the load-bearing forms, checks your one
recorded answer, and writes. It writes no event and never opens the shared records component (`references/station-loop.md` section 10).

## The loop

Every run walks the same phases, each a command of `scripts/precon.py` (run with `uv run`):

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
