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

- one REVIEW block per slice the run's `finding_raised` events name, in ascending slice order
  (E13 amendment A4): a blank line, the heading `### <date> — review: <slice>`, then one review
  finding line per event. Appendix A's review heading names ONE slice, and the reader charges
  every line of a block to the heading's FIRST slice (`legacy.item_slice`), so a single heading
  naming two slices would charge both findings to one and the block would not read back to the
  findings it was written from. One block per slice is the reading that round-trips;
- then one RECHECK block, when the run holds any `disposition` or `defect_raised`: a blank line,
  the heading `### <date> — recheck: <slices, ascending>`, then one line per event;
- then the run's `waived` and `reopened` events, one standalone line each, which is where the
  pilot puts them (directly after the ledger home's last line).

The recheck block's bytes are unchanged by amendment A4; `tests/test_parity.py` holds them.

Three shapes the pilot's writers never produce, because the pilot never holds the facts, and
which the builder's reports name as builder's calls: a location the reader could not resolve to
`file:line` renders as the field exactly as it was written (the pilot's `render_location` has no
`file` or `line` to take); a waiver or reopening whose `words` are null renders in Appendix A's
legacy grant form, the same line without its trailing quoted field; and a `finding_raised` whose
`raised_by` is null renders that last field as `()`, Appendix A's own "no field here" sentinel,
because a rendered line that ended in an empty field would lose it to the reader's trailing
whitespace trim and be read as a four-field line instead.

The review line writes the location field exactly as the raise recorded it, its `raw` (E13
amendment A7, Astra's F9: `review_location_text`), because a review line is the one rendered line
section 7 computes a finding's identity FROM: a range stays a range, and the rendered line reads
back as the finding it was rendered from for every location. The recheck block (its recheck
lines and its fix-introduced defect lines) and the grant lines keep `location_text`, byte for
byte, as A7 rules: a resolved location renders there as its first `file:line`, the pilot's own
form. A recheck or grant line names a finding rather than raising one; a DEFECT line with a
ranged location still reads back, in a log that does not hold it, under another identity, which
is outside A7's three items and is reported rather than changed. The importer recognises a
line it rendered itself by kind, slice context and bytes (`importer.match_native_lines`), and
`rendered_lines` tells it which event each line belongs to.

Under interface version 1 (`--interface-version 1`, E13 amendment A7, F10) `render` answers with
the body version 1 published, `render_run_interface_1`: the lines are the same bytes.
"""
from . import legacy

DISPOSITION_TEXT = {"fixed": "fixed", "not_fixed": "not fixed"}
BLOCK_KINDS = ("disposition", "defect_raised")
GRANT_KINDS = ("waived", "reopened")
REVIEW_KINDS = ("finding_raised",)  # E13 amendment A4: the review block
RENDERED_KINDS = REVIEW_KINDS + BLOCK_KINDS + GRANT_KINDS
RAISE_KINDS = ("finding_raised", "defect_raised")
NO_FIELD = legacy.NO_CLAIM  # Appendix A's "no field here" sentinel, `()`


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


def review_text(severity, location, claim, scenario, raised_by):
    """`- <severity> · <location> · (<claim>) · <failure scenario> · <whose review found it>`.

    Appendix A's review finding line. The claim field is written the way every other Appendix A
    shape writes one, wrapped in parentheses (E8-A28: parentheses wrapping the whole field are
    not part of the claim, in the review shape and in the join key), so a claim that itself looks
    parenthesized survives the round trip and a finding with no claim writes `()`. An empty last
    field would be lost to the reader's trailing whitespace trim, so a null `raised_by` writes
    `()` as well.
    """
    found = legacy._single_line(raised_by or "")
    return "- " + legacy.SEP.join([severity, review_location_text(location), claim_field(claim),
                                   legacy._single_line(scenario or ""), found or NO_FIELD])


def review_location_text(location):
    """The location field of a review line: the raw location the finding carries (E13 A7, F9).

    A review line is the one rendered line section 7 computes a finding's identity FROM, so it
    writes the field exactly as the raise recorded it: a range stays a range, and a field naming
    several locations stays whole. `location_text`'s first `file:line` would read back under
    another identity. The recheck block keeps `location_text`, byte for byte.
    """
    raw = location.get("raw") if isinstance(location, dict) else location
    return legacy._single_line(str(raw or ""))


def review_heading(date, slice_name):
    """`### <YYYY-MM-DD> — review: <slice>`; one slice, which is what Appendix A names."""
    label = legacy.PUNCH_LIST_LABEL if slice_name == "none" else "Slice %s" % slice_name
    return "### %s — review: %s" % (date, label)


def review_block(date, slice_name, lines):
    """One blank line, the review heading, the lines, one trailing newline (`legacy.render_block`
    with the review heading; the shape a station appends at the ledger home's tail)."""
    return "\n" + review_heading(date, slice_name) + "\n" + "\n".join(lines) + "\n"


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


def render_review(selected):
    """(review text, review lines, slice names, (event, line) pairs) for the run's
    `finding_raised` events.

    One block per slice, the slices in ascending order (E13 amendment A4), the findings of each
    in `seq` order. Each block carries the date of its own first finding.
    """
    groups = {}
    for event in selected:
        if event.get("kind") not in REVIEW_KINDS:
            continue
        groups.setdefault(event.get("slice") or "none", []).append(event)
    text, lines, names, pairs = "", [], [], []
    for name in legacy.sort_slices(list(groups)):
        block = [review_text(event.get("severity"), event.get("location"), event.get("claim"),
                             event.get("scenario"), event.get("raised_by"))
                 for event in groups[name]]
        text += review_block(date_of(groups[name][0]), name, block)
        lines.extend(block)
        names.append(name)
        pairs.extend(zip(groups[name], block))
    return text, lines, names, pairs


def render_run(doc, events, run_id):
    """The Appendix A text one run's events produce (the `render` command's body)."""
    return _render(doc, events, run_id)[0]


def rendered_lines(doc, events, run_id):
    """[(event, the one line `render` writes for it)] for every event of the run that carries one.

    The importer's half of E13 amendment A7 (F5): it needs to know WHICH native event a rendered
    line belongs to, not only that some event rendered those bytes, so that a line is matched by
    event kind and by finding identity in its slice context as well as by its bytes. The lines
    are the same strings `render_run` returns, from the same code path.
    """
    return _render(doc, events, run_id)[1]


def _render(doc, events, run_id):
    """(the body `render_run` returns, the (event, line) pairs `rendered_lines` returns).

    The Appendix A text one run's events produce.

    Returns {"run_id", "date", "slices", "review", "review_lines", "review_slices", "block",
    "lines", "grants", "text", "rendered", "skipped", "spec"}: `review` is the review block text
    (empty when the run raised no finding), `block` the recheck block text (empty when the run
    wrote no block line), `grants` the standalone waiver and reopening lines, and `text` what a
    station would append: the review blocks, the recheck block, then the grants. `skipped` names
    every event of the run that carries no Appendix A line.
    """
    selected = run_events(events, run_id)
    raised = raised_findings(events)
    review_events = [e for e in selected if e.get("kind") in REVIEW_KINDS]
    block_events = [e for e in selected if e.get("kind") in BLOCK_KINDS]
    grant_events = [e for e in selected if e.get("kind") in GRANT_KINDS]
    skipped = [{"seq": e["seq"], "kind": e.get("kind")} for e in selected
               if e.get("kind") not in RENDERED_KINDS]
    review, review_lines, review_slices, pairs = render_review(selected)
    slices = []
    for event in block_events:
        if event.get("kind") == "defect_raised":
            slices.append(event.get("slice") or "none")
        else:
            slices.append(_origin_of(event, raised).get("slice") or "none")
    heading_slices = legacy.sort_slices(slices) if slices else []
    dated = block_events or review_events or grant_events
    date = date_of(dated[0]) if dated else None
    lines = []
    for event in block_events:
        if event.get("kind") == "defect_raised":
            charged = legacy.defect_slice_field(heading_slices, event.get("slice"))
            lines.append(defect_text(event.get("severity"), event.get("location"),
                                     event.get("claim") or "", event.get("scenario") or "",
                                     slice_field=charged))
            pairs.append((event, lines[-1]))
            continue
        origin = _origin_of(event, raised)
        text = DISPOSITION_TEXT.get(event.get("disposition"))
        if text is None:
            raise RenderError("the event at seq %s carries no disposition" % event.get("seq"))
        lines.append(recheck_text(origin.get("severity"), origin.get("location"),
                                  origin.get("claim"), text, event.get("how") or ""))
        pairs.append((event, lines[-1]))
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
        pairs.append((event, grants[-1].rstrip("\n")))
    named = legacy.sort_slices(heading_slices + review_slices)
    body = {"run_id": run_id, "date": date, "slices": heading_slices, "review": review,
            "review_lines": review_lines, "review_slices": review_slices, "block": block,
            "lines": lines, "grants": grants,
            "text": review + block + "".join(grants),
            "rendered": len(review_lines) + len(lines) + len(grants), "skipped": skipped,
            "spec": {"doc": doc, "slice": named[0] if len(named) == 1 else None}}
    return body, pairs


INTERFACE_1_FIELDS = ("run_id", "date", "slices", "block", "lines", "grants", "text", "rendered",
                      "skipped", "spec")
"""The body fields `render` published under interface version 1, before E13 amendment A4."""


def render_run_interface_1(doc, events, run_id):
    """The `render` body in interface version 1's shape and meanings (E13 amendment A7, F10).

    Amendment A4 added `review`, `review_lines` and `review_slices` and widened five meanings:
    `text` and `rendered` gained the review block, `skipped` lost `finding_raised`, and `date` and
    `spec.slice` began to count the review blocks. The compatibility response a version-1 reader
    asks for with `--interface-version 1` keeps every one of them as version 1 published it: the
    recheck block, then the grants, and a `finding_raised` is an event that carries no line.
    The recheck and grant lines themselves are the same bytes in both versions.
    """
    body = render_run(doc, events, run_id)
    selected = run_events(events, run_id)
    block_events = [e for e in selected if e.get("kind") in BLOCK_KINDS]
    grant_events = [e for e in selected if e.get("kind") in GRANT_KINDS]
    dated = block_events or grant_events
    heading_slices = body["slices"]
    old = dict((key, body[key]) for key in INTERFACE_1_FIELDS)
    old.update({
        "date": date_of(dated[0]) if dated else None,
        "text": body["block"] + "".join(body["grants"]),
        "rendered": len(body["lines"]) + len(body["grants"]),
        "skipped": [{"seq": e["seq"], "kind": e.get("kind")} for e in selected
                    if e.get("kind") not in BLOCK_KINDS + GRANT_KINDS],
        "spec": {"doc": doc, "slice": heading_slices[0] if len(heading_slices) == 1 else None},
    })
    return old
