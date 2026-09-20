"""Rendering (records E12 contract section 9.4).

`render` produces, from a run's events, the exact Appendix A text the pilot writes for the same
facts: the block heading, the recheck and defect lines, the waiver and reopening lines. Nothing
in E12 writes that text into a document; E13 decides where a station puts it. This module
returns strings and never touches the workspace.

Every line is built from the pilot's own constants and helpers, which `legacy.py` holds byte for
byte (ruling E12-2): `SEP`, `NO_CLAIM`, `WAIVED`, `REOPENED`, `render_location`, `quoted`,
`sort_slices`, `defect_slice_field`, `render_heading`, `render_block`, `_single_line`. One code
path covers every shape, and `tests/test_parity.py` holds each rendered line byte-equal to what
the pilot's own writer (`render_recheck_line`, `render_defect_line`, `render_waiver`,
`render_reopen`, `render_block`) produces for the same facts, on the E7 fixtures and on
synthetic facts.

A run is named by `actor.run_id`. Its events render in `seq` order (E12-4) as:

- one block, when the run holds any `disposition` or `defect_raised`: a blank line, the heading
  `### <date> — recheck: <slices, ascending>`, then one line per event;
- then the run's `waived` and `reopened` events, one standalone line each, which is where the
  pilot puts them (directly after the ledger home's last line).

Two shapes the pilot's writers never produce, because the pilot never holds the facts, and which
the slice 2 report names as builder's calls: a location the reader could not resolve to
`file:line` renders as the field exactly as it was written (the pilot's `render_location` has no
`file` or `line` to take), and a waiver or reopening whose `words` are null renders in
Appendix A's legacy grant form, the same line without its trailing quoted field.
"""
from . import legacy

DISPOSITION_TEXT = {"fixed": "fixed", "not_fixed": "not fixed"}
BLOCK_KINDS = ("disposition", "defect_raised")
GRANT_KINDS = ("waived", "reopened")
RENDERED_KINDS = BLOCK_KINDS + GRANT_KINDS
RAISE_KINDS = ("finding_raised", "defect_raised")


class RenderError(ValueError):
    """A run whose events cannot be rendered; the CLI turns it into exit 4."""


def date_of(event):
    """The calendar date an event's `at` names, whichever of the two `at` forms it carries."""
    return (event.get("at") or "")[:10]


def location_text(location):
    """`file:line` for a resolved location, the field exactly as written for an unresolved one."""
    if isinstance(location, dict):
        if location.get("resolved") and location.get("file") is not None:
            return legacy.render_location(location["file"], location["line"])
        return legacy._single_line(location.get("raw") or "")
    return legacy._single_line(str(location or ""))


def claim_field(claim):
    """The claim field of a rendered recheck line: `()` when the finding carries none (E8-22)."""
    return legacy.NO_CLAIM if claim in (None, legacy.NO_CLAIM) else "(%s)" % claim


def recheck_text(severity, location, claim, disposition_text, how):
    """`- <severity> · <location> · (<claim>) · fixed | not fixed · <how verified>`."""
    return "- " + legacy.SEP.join([severity, location_text(location), claim_field(claim),
                                   disposition_text, legacy._single_line(how)])


def defect_text(severity, location, claim, scenario, slice_field=None):
    """`- <severity> · <location> · broke: <claim> — <scenario>` [ · <slice> ]."""
    broke = "broke: %s — %s" % (legacy._single_line(claim), legacy._single_line(scenario))
    fields = [severity, location_text(location), broke]
    if slice_field is not None:
        fields.append(legacy.PUNCH_LIST_LABEL if slice_field == "none"
                      else legacy._single_line(str(slice_field)))
    return "- " + legacy.SEP.join(fields)


def grant_text(keyword, middle, claim, words):
    """A standalone grant line; with `words` null it is Appendix A's legacy grant form."""
    fields = [keyword] + list(middle) + [legacy._single_line(claim)]
    if words is not None:
        fields.append(legacy.quoted(legacy._single_line(words)))
    return "- " + legacy.SEP.join(fields) + "\n"


def run_events(events, run_id):
    """The events of one run, in seq order."""
    out = []
    for event in events:
        actor = event.get("actor")
        if isinstance(actor, dict) and actor.get("run_id") == run_id:
            out.append(event)
    return out


def raised_findings(events):
    """{finding id: the event that raised it} across the whole log, for a line's facts."""
    out = {}
    for event in events:
        if event.get("kind") in RAISE_KINDS:
            out.setdefault(event.get("finding"), event)
    return out


def _origin_of(event, raised):
    origin = raised.get(event.get("finding"))
    if origin is None:
        raise RenderError("the event at seq %s names finding %s, which this log never raised"
                          % (event.get("seq"), event.get("finding")))
    return origin


def render_run(doc, events, run_id):
    """The Appendix A text one run's events produce.

    Returns {"run_id", "date", "slices", "block", "lines", "grants", "text", "rendered",
    "skipped", "spec"}: `block` is the block text (empty when the run wrote no block line),
    `grants` the standalone waiver and reopening lines, and `text` what a station would append,
    the block first. `skipped` names every event of the run that carries no Appendix A line.
    """
    selected = run_events(events, run_id)
    raised = raised_findings(events)
    block_events = [e for e in selected if e.get("kind") in BLOCK_KINDS]
    grant_events = [e for e in selected if e.get("kind") in GRANT_KINDS]
    skipped = [{"seq": e["seq"], "kind": e.get("kind")} for e in selected
               if e.get("kind") not in RENDERED_KINDS]
    slices = []
    for event in block_events:
        if event.get("kind") == "defect_raised":
            slices.append(event.get("slice") or "none")
        else:
            slices.append(_origin_of(event, raised).get("slice") or "none")
    heading_slices = legacy.sort_slices(slices) if slices else []
    date = date_of(block_events[0]) if block_events else (
        date_of(grant_events[0]) if grant_events else None)
    lines = []
    for event in block_events:
        if event.get("kind") == "defect_raised":
            charged = legacy.defect_slice_field(heading_slices, event.get("slice"))
            lines.append(defect_text(event.get("severity"), event.get("location"),
                                     event.get("claim") or "", event.get("scenario") or "",
                                     slice_field=charged))
            continue
        origin = _origin_of(event, raised)
        text = DISPOSITION_TEXT.get(event.get("disposition"))
        if text is None:
            raise RenderError("the event at seq %s carries no disposition" % event.get("seq"))
        lines.append(recheck_text(origin.get("severity"), origin.get("location"),
                                  origin.get("claim"), text, event.get("how") or ""))
    block = legacy.render_block(date, heading_slices, lines) if lines else ""
    grants = []
    for event in grant_events:
        origin = _origin_of(event, raised)
        location = origin.get("location")
        claim = legacy.entry_claim_field({"claim": origin.get("claim")})
        if event.get("kind") == "waived":
            middle = [event.get("grant_date"), event.get("severity") or origin.get("severity"),
                      location_text(location)]
            grants.append(grant_text(legacy.WAIVED, middle, claim, event.get("words")))
        else:
            middle = [event.get("grant_date"), location_text(location)]
            grants.append(grant_text(legacy.REOPENED, middle, claim, event.get("words")))
    return {"run_id": run_id, "date": date, "slices": heading_slices, "block": block,
            "lines": lines, "grants": grants, "text": block + "".join(grants),
            "rendered": len(lines) + len(grants), "skipped": skipped,
            "spec": {"doc": doc, "slice": heading_slices[0] if len(heading_slices) == 1 else None}}
