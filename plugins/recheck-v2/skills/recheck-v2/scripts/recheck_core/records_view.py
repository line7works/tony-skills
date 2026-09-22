"""The open set, the cards and the record addresses, read from the records component.

E13 slice 1, brief 3.2. What recheck DECIDES is unchanged (contract ruling E13-1); where it reads
the decision from is not. The open set, the finding rows and the cards come from
`records.py state`, and `records.py events` supplies the addresses a document record needs (the
line a legacy record sits on, the heading it sits under, and its date). The document itself is
still read, but only for its STRUCTURE — headings, slice names, `Status:` lines, the ledger home —
which is what places a rendered block and moves a card.

CR-F3, a finding raised natively. A station that raises through `append` (signoff after amendment
A4, or this pilot's own fix-introduced defect) leaves no `origin.line` behind. Its address is
where the component's rendering of the event sits: `records.py render --run-id <run>` gives the
line and its heading, the document's structure gives the line number and the heading it sits
under. One `render` per run, per view build. See `native_addresses`.

CR-1, the document can be ahead of its log. v1 signoff still writes findings into the Markdown by
hand, so at the start of every phase that used to parse the document for records the pilot runs
`import-legacy` for that document. The importer is idempotent: it appends only what the log lacks,
and a second pass over an unchanged document appends nothing at all. An ambiguous document
(component exit 5), or a record that changed above the imported tail (exit 7), stops the run with
the importer's own explanation and writes nothing to the document.

CR-2, a command that is read-only today stays read-only: it runs `import-legacy --dry-run`, which
takes no lock and writes nothing, and reports what the log lacks instead of adding it.

The refusal map (brief 3.4), named here once and used by the driver:

| component | pilot status     | why |
|---|---|---|
| exit 4 `invalid`            | `recording_failed` | the event the pilot built was refused; nothing landed |
| exit 5 `ambiguous_identity` | `missing_input`    | an ambiguity the run cannot decide goes to the user (RB6, section 10 row 1) |
| exit 6 `stale_source`       | `stale_source`     | a clear against a source that is not the workspace (section 10 row 4) |
| exit 7 `conflict`           | `recording_failed` | a moved head or a live lock; never retried, never merged (section 10 row 9) |

Anything else the component reports (exit 1, exit 2, exit 3) is `recording_failed` when it happens
inside the transaction and `missing_input` when it happens while scope is being read, each carrying
the component's own sentence.
"""
import os

from . import ledger, records_client as rcl

# brief 3.4: the one place the mapping lives
REFUSAL_STATUS = {4: "recording_failed", 5: "missing_input", 6: "stale_source", 7: "conflict"}
CONFLICT_STATUS = "recording_failed"


class RecordsStop(RuntimeError):
    """A component refusal as a pilot stop: the status, and everything the stop needs to report."""

    def __init__(self, status, reason, fields=None, ambiguity=None, question=None, refusal=None):
        RuntimeError.__init__(self, reason)
        self.status = status
        self.reason = reason
        self.fields = list(fields or [])
        self.ambiguity = list(ambiguity or [])
        self.question = question
        self.refusal = refusal

    @property
    def exit_code(self):
        return self.refusal.exit_code if self.refusal is not None else None


def status_for(code):
    """The pilot status a component exit code maps to (brief 3.4)."""
    if code == 7:
        return CONFLICT_STATUS
    return REFUSAL_STATUS.get(code, "recording_failed")


def stop_for(refusal, field="target.build_doc", reading=None):
    """Turn a RecordsRefusal into a RecordsStop carrying the component's own explanation."""
    status = status_for(refusal.exit_code)
    sentence = refusal.sentence()
    reason = "%s: %s" % (refusal.command, sentence) if sentence else refusal.command
    if reading:
        reason = "%s; %s" % (reason, reading)
    if status == "missing_input":
        lines = [reason]
        for row in refusal.body.get("ambiguities") or []:
            lines.append("%s:%s: %s: %s" % (refusal.body.get("doc"), row.get("line"),
                                            row.get("reason"), row.get("raw")))
        return RecordsStop(status, reason, fields=[field], ambiguity=lines,
                           question=lines[-1] + "; which entry is meant?", refusal=refusal)
    return RecordsStop(status, reason, refusal=refusal)


# ---- CR-1 and CR-2: keeping the log level with the document ---------------------------------

def sync(client, workspace, document, dry_run=False, field="target.build_doc"):
    """Run `import-legacy` for one document before its records are read (CR-1).

    Idempotent: a pass that finds no news appends nothing at all. With `dry_run` it takes no lock
    and writes nothing (CR-2), and the caller reads what the log still lacks from `would_import`.
    """
    try:
        return client.import_legacy(workspace, document, dry_run=dry_run)
    except rcl.RecordsRefusal as refusal:
        raise stop_for(refusal, field=field)


def behind(report):
    """How many records a dry run says the log lacks (CR-2); 0 when it is level."""
    if not report or not report.get("dry_run"):
        return 0
    return int(report.get("would_import") or 0)


# ---- the view -------------------------------------------------------------------------------

def _doc_structure(workspace, document):
    """The document's headings, slices and `Status:` lines: structure, never records."""
    path = os.path.join(workspace, document)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return ledger.parse_document(fh.read(), document)


def _address(seq, event, headings, natives):
    """(line_no, heading text, date) of one event.

    A legacy event carries the line it was imported from. A NATIVE raise (`finding_raised`,
    `defect_raised`) is addressed where the component's rendering of it sits (CR-F3,
    `native_addresses`). Any other native event carries no document line.
    """
    origin = event.get("origin") or {}
    at = event.get("at") or ""
    if origin.get("kind") == "legacy":
        heading_line = origin.get("heading_line")
        return origin.get("line"), headings.get(heading_line), at[:10]
    if seq in natives:
        return natives[seq]
    return None, None, at[:10]


# ---- CR-F3: where a natively raised finding sits ---------------------------------------------

RAISE_KINDS = ("finding_raised", "defect_raised")
_REVIEW_KIND = "finding_raised"
_BLOCK_KINDS = ("disposition", "defect_raised")  # the events `render` writes one recheck-block line for


def _is_native_raise(event):
    return event.get("kind") in RAISE_KINDS and (event.get("origin") or {}).get("kind") != "legacy"


def _pairs(text):
    """[(heading, line)] of rendered block text: every non-blank line under the `###` heading above it."""
    out, heading = [], None
    for line in (text or "").split("\n"):
        if line.startswith("### "):
            heading = line
        elif line.strip():
            out.append((heading, line))
    return out


def _rendered_by_seq(rendered, run_events):
    """{seq: (heading, line)} for the raises of one run, from its `render` response.

    `render` writes the review blocks one per slice in `review_slices` order with each slice's
    `finding_raised` events in seq order, and the recheck block one line per `disposition` or
    `defect_raised` in seq order. A response whose line count disagrees with the run's events
    places nothing (the raise keeps no address, and the checkpoint's own validation says so).
    """
    out = {}
    slices = list(rendered.get("review_slices") or [])
    review = [e for e in run_events if e[1].get("kind") == _REVIEW_KIND]
    review.sort(key=lambda row: (slices.index(row[1].get("slice") or "none")
                                 if (row[1].get("slice") or "none") in slices else len(slices), row[0]))
    block = [e for e in run_events if e[1].get("kind") in _BLOCK_KINDS]
    for events, text in ((review, rendered.get("review")), (block, rendered.get("block"))):
        pairs = _pairs(text)
        if len(pairs) != len(events):
            continue
        for (seq, event), pair in zip(events, pairs):
            if event.get("kind") in RAISE_KINDS:
                out[seq] = pair
    return out


def _heading_date(heading, fallback):
    m = ledger.RECORD_HEADING_RE.match(heading or "")
    return m.group(1) if m else fallback


def native_addresses(client, workspace, document, by_seq, structure):
    """{seq: (line_no, heading text, date)} for every native raise the log holds (CR-F3).

    The component says what line each raise renders to and under which heading
    (`render --run-id <the raise's actor.run_id>`, one call per run, cached for this build). The
    document says where that line SITS: the first record line of the document's own structure with
    exactly that text, not already answering for another event, gives the line number and the
    heading it sits under, and the document's heading wins. A raise whose line the document does
    not carry (the station's append landed, its document write did not) keeps the heading the
    component's render carries and no line.
    """
    wanted = [seq for seq in sorted(by_seq) if _is_native_raise(by_seq[seq])]
    if not wanted:
        return {}
    renders, rendered = {}, {}
    for seq in wanted:
        run_id = (by_seq[seq].get("actor") or {}).get("run_id")
        if not run_id or run_id in renders:
            continue
        try:
            renders[run_id] = client.render(workspace, document, run_id)
        except rcl.RecordsRefusal as refusal:
            raise stop_for(refusal)
        run_events = [(s, by_seq[s]) for s in sorted(by_seq)
                      if (by_seq[s].get("actor") or {}).get("run_id") == run_id]
        rendered.update(_rendered_by_seq(renders[run_id], run_events))
    records = (structure or {}).get("records") or []
    claimed = set()
    for event in by_seq.values():
        origin = event.get("origin") or {}
        if origin.get("kind") == "legacy" and origin.get("line") is not None:
            claimed.add(origin.get("line"))
    out = {}
    for seq in wanted:
        at = (by_seq[seq].get("at") or "")[:10]
        if seq not in rendered:
            continue
        heading, line = rendered[seq]
        text = line.rstrip()
        placed = None
        for rec in records:
            if rec.get("text") == text and rec.get("heading") and rec["line_no"] not in claimed:
                placed = rec
                break
        if placed is not None:
            claimed.add(placed["line_no"])
            out[seq] = (placed["line_no"], placed["heading"]["text"], placed["heading"]["date"])
        else:
            out[seq] = (None, heading, _heading_date(heading, at))
    return out


def build_entries(state, events, structure, natives=None):
    """The pilot's entry shape, built from the component's state and events.

    One entry per finding the log holds, in the order the records sit in the document (a finding
    raised natively, with no document line, keeps its raise order after them). `state` decides
    `state` (open, fixed, waived); nothing here re-derives it. `natives` is `native_addresses`:
    where each natively raised finding sits (CR-F3).
    """
    natives = natives or {}
    headings = {}
    if structure is not None:
        for block in structure["blocks"]:
            headings[block["line_no"]] = block["text"]
    by_seq = {}
    for row in events.get("results") or []:
        by_seq[row["seq"]] = row["event"]
    entries = []
    for finding in state.get("findings") or []:
        raised = (finding.get("raised") or {}).get("seq")
        raise_event = by_seq.get(raised) or {}
        line_no, heading, date = _address(raised, raise_event, headings, natives)
        history = []
        for seq in finding.get("events") or []:
            event = by_seq.get(seq) or {}
            where, _, when = _address(seq, event, headings, natives)
            history.append({"seq": seq, "kind": event.get("kind"), "line_no": where, "date": when})
        decided = (finding.get("decided") or {}).get("seq")
        last = history[-1] if history else {"seq": raised, "kind": raise_event.get("kind"), "line_no": line_no}
        for row in history:
            if decided is not None and row["seq"] == decided:
                last = row
        location = finding.get("location") or {}
        entries.append({
            "finding": finding["id"],
            "file": location.get("file"), "line": location.get("line"),
            "claim": finding.get("claim"), "severity": finding.get("severity"),
            "scenario": finding.get("scenario"), "slice": finding.get("slice") or "none",
            "document": state["spec"]["doc"], "heading": heading, "date": date,
            "state": finding.get("status"), "raised_by": finding.get("raised_by"),
            "caused_by": finding.get("caused_by"),
            "origin": {"line_no": line_no, "seq": raised, "kind": raise_event.get("kind")},
            "last": {"line_no": last.get("line_no"), "seq": last.get("seq"), "kind": last.get("kind")},
            "history": history,
        })
    entries.sort(key=_order_key)
    return entries


def _order_key(entry):
    line = entry["origin"].get("line_no")
    if line is None:
        return (1, entry["origin"].get("seq") or 0)
    return (0, line)


order_key = _order_key


def where(document, entry):
    """`<doc>:<line>` for a record the document carries, `<doc> (log seq N)` for a native one."""
    line = entry["origin"].get("line_no")
    if line is None:
        return "%s (log seq %s)" % (document, entry["origin"].get("seq"))
    return "%s:%d" % (document, line)


def claim_field(entry):
    """The claim as a record field: `()` for an entry with no claim (Appendix A, was
    `ledger.entry_claim_field`)."""
    return ledger.NO_CLAIM if entry["claim"] is None else entry["claim"]


def match_entries(entries, file, line, claim):
    """Resolve a (location, claim) reference against the whole record (Appendix A's join rules,
    was `ledger.find_entries`). The reference's claim is normalized the way every record's is
    (E8-A28: outer parentheses are not part of the claim)."""
    if isinstance(claim, str):
        claim = ledger.strip_parens(claim)
    same = [e for e in entries if e["file"] == file and e["line"] == line]
    exact = [e for e in same if e["claim"] == claim]
    if exact:
        return exact
    if claim in (None, ledger.NO_CLAIM) or any(e["claim"] is None for e in same):
        return same if len(same) == 1 else []
    return []


def cards_of(state):
    """{slice: card} from the component's `card_observed`; a slice nothing observed reads `none`."""
    out = {}
    for row in state.get("slices") or []:
        out[row["name"]] = row.get("card_observed") or "none"
    return out


def derived_cards(state):
    """{slice: card_derived}: Appendix A's mapping as the component computes it (brief 3.6)."""
    out = {}
    for row in state.get("slices") or []:
        out[row["name"]] = row.get("card_derived")
    return out


class View:
    """One reading of a document's records through the component."""

    def __init__(self, state, events, structure, entries, cards):
        self.state, self.events, self.structure = state, events, structure
        self.entries, self.cards = entries, cards

    @property
    def head(self):
        return self.state["head"]

    @property
    def document(self):
        return self.state["spec"]["doc"]

    def card(self, name):
        return self.cards.get(name, "none")

    def open_entries(self, slice_name=None):
        return [e for e in self.entries
                if e["state"] == "open" and (slice_name is None or e["slice"] == slice_name)]

    def by_finding(self, finding_id):
        for e in self.entries:
            if e["finding"] == finding_id:
                return e
        return None


def read(client, workspace, document):
    """`state` and `events` for one document, joined to the document's structure."""
    try:
        state = client.state(workspace, document)
        events = client.events(workspace, document)
    except rcl.RecordsRefusal as refusal:
        raise stop_for(refusal)
    structure = _doc_structure(workspace, document)
    by_seq = dict((row["seq"], row["event"]) for row in events.get("results") or [])
    natives = native_addresses(client, workspace, document, by_seq, structure)
    entries = build_entries(state, events, structure, natives)
    return View(state, events, structure, entries, cards_of(state))
