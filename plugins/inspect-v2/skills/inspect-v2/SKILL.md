---
name: inspect-v2
description: >-
  The plan-check station: adversarial review of a blueprint build doc BEFORE build runs it, by
  fresh inspectors chosen at summon, their packet built by script from the permitted documents
  alone and their surviving findings kept in the shared records. Use only when the owner types
  /inspect-v2 by name. Strictly user-invoked: never auto-invoke or suggest-invoke, no matter how
  ready a fresh blueprint looks. Not a review of built code (signoff-v2), not a fix, and not the
  v1 inspect station.
disable-model-invocation: true
---

# Inspect v2

This station is the plan check: fresh inspectors read the build doc against its scope doc, the code book and the repo before a slice is built, and the verified findings are raised in the shared records with a stamp naming the model that inspected. It reads the build doc, its scope doc, and blueprint-v2's installed SKILL.md as the code book; it writes the stamp and its own QUESTION and clean lines in the build doc, findings through the records component, and a verdict mirror.

**This file is the frame (E14 slice 1).** The station's own steps, rules and gates arrive in its
slice 2 lane; until then the phases a lane fills stop as `phase-not-built` and this station does
nothing for the owner. Say so and stop.

**When to run.** Run it only when the owner types it by name. Never invoke it on your own, never suggest invoking it, and never start it because a discussion looks ready.

**The spine.** The executor decides, the script records (rule E14-4). You talk to the owner and
judge; `scripts/inspect_v2.py` does everything deterministic: it validates the input, finds the
documents, reads the scope doc's ledger, renders and parses the load-bearing forms, checks your one
recorded answer, and writes. It opens the shared records component, and only it among the front stations: its surviving findings are raised there through the component's CLI, never written into a log by hand (`references/station-loop.md` section 10).

## The loop

Every run walks the same phases, each a command of `scripts/inspect_v2.py` (run with `uv run`):

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
