"""Reading the records through the component, and the three readings slice 1 took.

Every call here goes through `records.py` as a subprocess (the resolver, then the CLI). This
core never opens a log file, never imports `records_core`, and never copies the component's
code beyond the one snippet in `records_client.py`.

**CR-1, the document can be ahead of its log.** v1 build and v1 signoff still write into the
Markdown by hand, so before any phase reads the records, `import-legacy` levels the log with the
document. The importer is idempotent: a pass that finds no news appends nothing at all.

**CR-2, a read-only pass stays read-only.** A report-only run levels with `--dry-run`, which
takes no lock and writes nothing, and reads what the log lacks from `would_import` instead of
adding it.

**Amendment A3 item 3, the importer reads more loosely than this core does.** The slice 1
builder's findings 2 and 3 are open: the importer reads a hand-written record more loosely than
the pilot's strict reader, and it refuses an orphan clearing line. This core does not build a
second record grammar and does not change `plugins/records/`. It STOPS, naming the line, on ANY
importer signal: a `legacy_unparsed` above zero in the dry run, exit 5 (ambiguous), or any
refusal. A line the importer silently drops is the known open point.

**The card, both directions.** A `card_set` this station appended and a `Status:` line the
document carries can disagree, and the disagreement is reported, never repaired. The test is a
comparison of FACTS, not of import timing:

    drift  iff  the last `card_set` for the slice has `after` != the document's card
                AND the document's card == that same event's `before`

That is exactly the state a run leaves when its card event landed and its document write did
not: the line still reads what it read before the move. A `Status:` line holding any OTHER value
is a hand edit — a person, or a v1 station — and the importer absorbs it as an observation; this
core reports the card where it stands and does not stop.

**Why it is not an ordering test.** It was one until E13 amendment A4, and A4 broke it. The rule
read "the last `card_set` sits after every `card_observed` for the slice", which held only
because the pre-A4 importer compared a `Status:` line with the last `card_observed` and so
appended nothing in the split state. A4 made the importer compare with the last CARD the log
holds — the `card_set` — so it now appends a `card_observed` ABOVE the event, and the ordering
read the document as the newer truth and passed the split. The lesson is this core's to learn:
the rule was coupled to WHEN the component appends an observation rather than to what the two
halves actually say. The comparison above needs no import to have happened at all, so it cannot
be moved by a change in that policy.

A run whose halves both landed is recognised by the component itself: A4 counts the `Status:`
line it wrote under `native_rendered` and imports nothing for it.
"""
from . import records_link as link
from .records_client import RecordsRefusal


class RecordsStop(RuntimeError):
    """A component refusal, or a signal from it, as one of this core's stops."""

    def __init__(self, tag, reason, refusal=None, detail=None):
        RuntimeError.__init__(self, reason)
        self.tag = tag
        self.reason = reason
        self.refusal = refusal
        self.detail = detail or {}

    @property
    def exit_code(self):
        return self.refusal.exit_code if self.refusal is not None else None

    def refused_block(self):
        if self.refusal is None:
            return None
        return {"exit_code": self.refusal.exit_code, "error": self.refusal.error,
                "reason": self.refusal.sentence()}


def stop_for(refusal, what):
    return RecordsStop(link.refusal_tag(refusal.exit_code),
                       link.refusal_sentence(refusal, what), refusal=refusal)


# ---- CR-1, CR-2 and amendment A3 item 3 -------------------------------------------------------

def _unparsed(report):
    return int((report.get("counts") or {}).get("legacy_unparsed") or 0)


def _native_rendered(report):
    """How many lines the component recognised as ones the log already records natively (A4).

    None when the component does not publish the field, which is how a pre-A4 component reads:
    absent is not the same as zero, and this core says which it saw.
    """
    value = report.get("native_rendered")
    return None if value is None else int(value)


def level(client, workspace, document, dry_run):
    """Level the log with the document, and stop on any importer signal.

    Always runs a dry run first (the guide: "never import a legacy document without a dry run
    first"), stops when that pass would write a `legacy_unparsed`, and only then makes the real
    pass when one is asked for. Returns the report the caller should report.
    """
    try:
        preview = client.import_legacy(workspace, document, dry_run=True)
    except RecordsRefusal as refusal:
        raise stop_for(refusal, "the log could not be levelled with %s before its records were read"
                       % document)
    unparsed = _unparsed(preview)
    if unparsed:
        raise RecordsStop(
            "legacy_unplaced",
            "the records component's importer reads %d line(s) of %s under a record heading that "
            "fit no record shape (`legacy_unparsed`), so what those lines say is not in the log "
            "and this run will not decide the slice against a record it cannot place. Read the "
            "document, fix the line or answer it, and run again. This core does not carry a second "
            "record grammar (E13 amendment A3 item 3)." % (unparsed, document),
            detail={"unparsed": unparsed, "doc": preview.get("doc"),
                    "lines_read": preview.get("lines_read")})
    if dry_run:
        return {"ran": True, "dry_run": True, "would_import": preview.get("would_import"),
                "imported": 0, "unparsed": unparsed,
                "native_rendered": _native_rendered(preview)}
    try:
        report = client.import_legacy(workspace, document, dry_run=False)
    except RecordsRefusal as refusal:
        raise stop_for(refusal, "the log could not be levelled with %s before its records were read"
                       % document)
    return {"ran": True, "dry_run": False, "would_import": preview.get("would_import"),
            "imported": report.get("imported"), "unparsed": _unparsed(report),
            "native_rendered": _native_rendered(report)}


# ---- the reads ---------------------------------------------------------------------------------

def head_of(client, workspace, document):
    """The log's head. A read that failed is a stop, never an assumed empty log."""
    try:
        return client.verify(workspace, document)
    except RecordsRefusal as refusal:
        raise stop_for(refusal, "the log of %s could not be read" % document)


def state_of(client, workspace, document, slice_name=None):
    try:
        return client.state(workspace, document, slice_name=slice_name)
    except RecordsRefusal as refusal:
        raise stop_for(refusal, "the state of %s could not be read" % document)


def card_events(client, workspace, document):
    """This document's `card_set` and `card_observed` events, in seq order.

    A failed history read is a STOP, never an empty history (the outside reviewer's finding 4
    against the pilot: `except RecordsRefusal: already = set()` discarded a checked failure and
    appended a duplicate).
    """
    try:
        rows = client.events(workspace, document)["results"]
    except RecordsRefusal as refusal:
        raise stop_for(refusal, "the card history of %s could not be read, so nothing was appended "
                                "and nothing was recorded twice" % document)
    return [row for row in rows
            if (row.get("event") or {}).get("kind") in ("card_set", "card_observed")]


def slice_row(state, slice_name):
    for row in state.get("slices") or []:
        if row.get("name") == slice_name:
            return row
    return None


def card_now(state, slice_name):
    """What the LOG says the card is: the last `card_observed` or `card_set` for the slice.

    Not the document. The component's `card_observed` field is "the last card observed OR SET",
    so it follows a `card_set` this station appended even while the document still carries the
    old text. That is exactly the pair `card_drift` compares, so the two must be read from
    different places: this one from the log, and `document_card` from the document.
    """
    row = slice_row(state, slice_name)
    if row is None:
        return "none"
    return row.get("card_observed") or "none"


def document_card(workspace, document, slice_name):
    """The `Status:` text the DOCUMENT carries for one slice, normalized to a card value.

    Read from the file by this core's own reader, because the document is one of the two things
    the drift check compares and the log is the other. A text outside the six card values reads
    as `none`, the way the component reads one.
    """
    from . import doc as docmod
    try:
        text = docmod.read(workspace, document)
    except docmod.DocumentError:
        return None, None
    for entry in docmod.parse(text):
        if entry["name"] == slice_name:
            written = (entry["status"] or "").strip()
            return (written if written in docmod.CARD_VALUES else "none"), written
    return None, None


def open_counts(state, slice_name):
    row = slice_row(state, slice_name)
    if row is None:
        return {"BLOCKER": 0, "MAJOR": 0, "MINOR": 0}
    return dict(row.get("open") or {"BLOCKER": 0, "MAJOR": 0, "MINOR": 0})


def last_card_events(rows, slice_name):
    """(last card_set, last card_observed) for one slice, each `{seq, event}` or None."""
    last_set = last_observed = None
    for row in rows:
        event = row["event"]
        if event.get("slice") != slice_name:
            continue
        if event.get("kind") == "card_set":
            last_set = row
        elif event.get("kind") == "card_observed":
            last_observed = row
    return last_set, last_observed


def card_drift(rows, slice_name, document_text_card):
    """The disagreement described in this module's docstring, or None.

    `document_text_card` is the card the DOCUMENT carries now, from `document_card`, never the
    component's `card_observed` — that field follows a `card_set` too, so comparing it with the
    last `card_set` would compare a value with itself and could never find the split state this
    check exists for.
    """
    last_set, _last_observed = last_card_events(rows, slice_name)
    if last_set is None:
        return None
    event = last_set["event"]
    recorded, before = event.get("after"), event.get("before")
    if recorded == document_text_card:
        return None                      # both halves landed
    if document_text_card != before:
        return None                      # a hand edit to some other value: an observation, not drift
    return {"log": recorded, "document": document_text_card, "seq": last_set["seq"],
            "run_id": (event.get("actor") or {}).get("run_id")}


def drift_sentence(slice_name, document, drift):
    return ("the log of %s records the card of slice %s moving to %r (event seq %d, written by "
            "run %r) and the document's `Status:` line still reads %r, which is the value that "
            "move started from. The event landed and the document write did not, so one of the "
            "two halves of a card move is missing. This core reports the disagreement and repairs "
            "neither: read both, decide which is right, and run again."
            % (document, slice_name, drift["log"], drift["seq"], drift["run_id"], drift["document"]))
