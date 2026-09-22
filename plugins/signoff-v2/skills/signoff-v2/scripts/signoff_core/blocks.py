"""PROVISIONAL: the review block, rendered from this run's events.

**Why this module exists, and why it is marked provisional.** The brief's record step says the
punch-list block is placed "with `records.py render`". At records interface version 1 that
command cannot produce a signoff review block: it renders a block only "when the run holds any
`disposition` or `defect_raised`", it reports a `finding_raised` under `skipped`, and the only
block heading it writes is Appendix A's RECHECK heading. Measured against the real component:
one valid `finding_raised` appended, then `render --run-id` returns
`{"block": "", "rendered": 0, "skipped": [{"kind": "finding_raised", "seq": 0}]}`.

`plugins/records/` is frozen for this step (ruling E13-2), so this station renders the review
block itself, from Appendix A's grammar, until the control room rules otherwise. The question is
with the control room and this module is the one place a ruling has to reach: swap
`review_block` for a `render` call and nothing else moves.

Two things are kept even so, and they are what make this a rendering rather than prose:

1. it renders from THIS RUN'S EVENTS AS THE COMPONENT STORED THEM, read back through
   `events`, not from the adjudication in memory. What the log says is what the document says.
2. it writes Appendix A's shapes and nothing else. The grammar is the pilot contract's and this
   module does not extend it.

Appendix A, the two shapes this module writes:

    ### <YYYY-MM-DD> — review: <slice>
    - <severity> · <file:line> · <claim> · <failure scenario> · <which slice's review found it>

The separator is ` · ` (space, U+00B7, space) and no field may contain it or a line break; the
records component already refuses an event whose claim, scenario or `raised_by` does.
"""
SEPARATOR = " · "


class GrammarBroken(RuntimeError):
    """A field the grammar forbids reached the renderer. The component refuses these too."""


def _field(value, name):
    text = "" if value is None else str(value)
    if "\n" in text or "\r" in text:
        raise GrammarBroken("the %s spans lines; Appendix A's fields are single lines" % name)
    if SEPARATOR in text:
        raise GrammarBroken("the %s carries the field separator %r" % (name, SEPARATOR))
    return text


def finding_line(event):
    """One review finding line from one `finding_raised` event."""
    location = event.get("location") or {}
    raw = _field(location.get("raw"), "location")
    return "- " + SEPARATOR.join([
        _field(event.get("severity"), "severity"),
        raw,
        _field(event.get("claim"), "claim"),
        _field(event.get("scenario"), "scenario"),
        _field(event.get("raised_by"), "raised_by"),
    ])


def review_block(events, run_date, slices):
    """The block a run's `finding_raised` events produce, in `seq` order.

    Returns {"block", "lines", "text", "rendered", "skipped", "date", "slices"}, the shape
    `records.py render` returns, so a caller does not change when this is replaced by it.
    """
    lines, skipped = [], []
    for row in events:
        event = row.get("event") if "event" in row else row
        if event.get("kind") != "finding_raised":
            skipped.append({"seq": row.get("seq", event.get("seq")), "kind": event.get("kind")})
            continue
        lines.append(finding_line(event))
    if not lines:
        return {"block": "", "lines": [], "text": "", "rendered": 0, "skipped": skipped,
                "date": None, "slices": []}
    heading = "### %s — review: %s" % (run_date, ", ".join(slices))
    block = "\n" + heading + "\n" + "\n".join(lines) + "\n"
    return {"block": block, "lines": lines, "text": block, "rendered": len(lines),
            "skipped": skipped, "date": run_date, "slices": list(slices)}
