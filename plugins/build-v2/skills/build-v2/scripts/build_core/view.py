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
document carries can disagree, and the disagreement is reported, never repaired. The test is an
ordering one, because the importer records every hand edit of a `Status:` line as a
`card_observed`:

    the last card_set for the slice sits AFTER every card_observed for it, and its `after`
    differs from the document's current `Status:` text

That is the state a run leaves when its card event landed and its document write did not. The
other direction — a `Status:` line moved after the last `card_set` — is a legitimate hand edit
(a v1 station, or a person), the importer absorbs it as a `card_observed` at a higher seq, and
it is not drift.
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
                "imported": 0, "unparsed": unparsed}
    try:
        report = client.import_legacy(workspace, document, dry_run=False)
    except RecordsRefusal as refusal:
        raise stop_for(refusal, "the log could not be levelled with %s before its records were read"
                       % document)
    return {"ran": True, "dry_run": False, "would_import": preview.get("would_import"),
            "imported": report.get("imported"), "unparsed": _unparsed(report)}


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
    last_set, last_observed = last_card_events(rows, slice_name)
    if last_set is None:
        return None
    if last_observed is not None and last_observed["seq"] > last_set["seq"]:
        return None
    recorded = last_set["event"].get("after")
    if recorded == document_text_card:
        return None
    return {"log": recorded, "document": document_text_card, "seq": last_set["seq"],
            "run_id": (last_set["event"].get("actor") or {}).get("run_id")}


def drift_sentence(slice_name, document, drift):
    return ("the log of %s records the card of slice %s at %r (event seq %d, written by run %r) "
            "and the document's `Status:` line reads %r. One of the two halves of a card move did "
            "not land. This core reports the disagreement and repairs neither: read both, decide "
            "which is right, and run again."
            % (document, slice_name, drift["log"], drift["seq"], drift["run_id"], drift["document"]))
