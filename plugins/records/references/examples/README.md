# Example events

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

## What the checker proves

1. Every `valid/` example validates.
2. Every `invalid/` example is rejected.
3. Dropping any one field the schema requires of a valid example makes it fail. A `required`
   list that stops being enforced is caught here rather than in production.
4. `example.events.jsonl` walks clean under the chain rules of section 10.

Slice 2 adds the examples for `state.schema.json`, `import-report.schema.json` and
`resolutions.schema.json` beside these.
