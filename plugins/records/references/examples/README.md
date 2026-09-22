# Examples

Every file here is synthetic. The document `docs/plans/2026-04-01-widget.md`, the widget and
gauge sources, the commits and the hashes are invented for these examples; nothing is copied
from a real ledger, and no example carries personal, legal, or financial content.

Run the checker from any directory:

```sh
uv run ../../scripts/validate-examples.py
```

## What is here

- `valid/` — one event per kind of contract section 6.2, plus the location shapes the reader has
  to carry: a line range, a legacy tag glued to the location, a location the field never
  resolved to a `file:line`, and several locations in one field. Each file is one event as it
  lands in the log, `seq` and `prev` included.
- `invalid/` — one event per rule that must reject it, each wrapped as
  `{"reason": "<the rule>", "event": {…}}`. The reason is part of the fixture: a checker that
  rejects the event for some other reason still passes, so the reason is what a reader consults
  to see what the case is about.
- `example.events.jsonl` — a nine-line log whose chain is real: every `prev` is the SHA-256 of
  the line before, and `seq` equals the line index. It is what `records.py verify` walks.
- `state/`, `import-report/`, `resolutions/` — the same `valid/` and `invalid/` pair for the
  other three schemas of contract section 1, with an invalid example wrapped as
  `{"reason": "<the rule>", "document": {…}}`. The `state/` and `import-report/` examples are
  real responses: they were produced by running `state`, `import-legacy` (a dry run, a landed
  import, a pass that recovered a stale lock, and each of its four refusals) and `survey`
  against the fixture workspace `fixtures/build.py` builds, with the survey's absolute workspace
  path replaced by `/workspace`. The `resolutions/`
  examples are the input file of section 11.5, written by hand.

## The A2 clears the examples cover

Raise one finding, then append matching-source fixed and waived events, separately or in one
batch. State reports waived, with the waiver deciding; a later reopened reports open.
Fixed-over-fixed, fixed-over-waived and waived-over-waived return exit 6. Wrong or unknown
verified source returns 6, unknown finding returns 5, and importer impersonation returns 4.
Refused batches append nothing. Interface version remains 1.

## What the checker proves

1. Every `valid/` example validates.
2. Every `invalid/` example is rejected.
3. Dropping any one field the schema requires of a valid example makes it fail. A `required`
   list that stops being enforced is caught here rather than in production.
4. `example.events.jsonl` walks clean under the chain rules of section 10.
5. The same three passes for the other three schemas. Where a schema is a `oneOf` over branches
   (an import report is one of five shapes), the dropped-field pass uses the required list of the
   branch the example matches as well as the top level's, so a branch that quietly stopped
   requiring a field is caught.
6. Every `required` list of all four schemas — `event.schema.json` included — matches the list
   pinned in `validate-examples.py`, the lists reached through an array inside `$defs` included.
   The pins are literals written from the contract and `references/interface.md`, never read from
   the schema under test: a required field removed from any of those lists is a failure here, not
   a silently weaker check, and a `required` list that nothing pins is a failure too.
