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

F13 (pilot contract Revision 9): an importer stop made ONLY of orphan clearing lines — records the
branch point's reader made entries of their own — is answered `new_finding` through the
component's resolutions interface, so the log holds the branch point's effective state and the
run's stop decision is the branch point's again. See `sync` and `orphan_answers`.

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
import datetime
import json
import os
import tempfile

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

    Astra's F13 (E13-1): the importer stops (exit 5) on an ORPHAN clearing line — a recheck line
    or a waiver whose location and claim match no finding of the document. The pilot at the branch
    point never stopped there: Appendix A's open filter makes such a record an entry of its own
    (`ledger.open_set`, "records that match no entry become entries of their own when they carry a
    severity"), decided by the record itself. When EVERY line the importer stopped on is exactly
    such a record by the pilot's own unchanged reader, the pilot answers each one `new_finding`
    through the component's resolutions interface (`import-legacy --resolutions`), which
    represents the same effective state in the log: a finding at that location with that claim
    and severity, decided by that line. Anything else the importer stopped on stops the run as
    before, with the importer's own explanation, and so does a resolution the component refuses.
    """
    try:
        return client.import_legacy(workspace, document, dry_run=dry_run)
    except rcl.RecordsRefusal as refusal:
        answers = orphan_answers(workspace, document, refusal)
        if answers is None:
            raise stop_for(refusal, field=field)
        handle, path = tempfile.mkstemp(prefix="recheck-v2-resolutions-", suffix=".json")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                json.dump(answers, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            try:
                return client.import_legacy(workspace, document, dry_run=dry_run, resolutions=path)
            except rcl.RecordsRefusal:
                raise stop_for(refusal, field=field)
        finally:
            if os.path.exists(path):
                os.remove(path)


ORPHAN_ANSWERED_BY = ("recheck-v2, by pilot contract Appendix A's open filter: a record that "
                      "matches no entry and carries a severity is an entry of its own")


def orphan_answers(workspace, document, refusal):
    """The resolutions file that answers an importer stop made only of orphan records, or None.

    An orphan record, by the pilot's own reader: a recheck line or a waiver that `ledger.open_set`
    turned into an entry of its own because nothing earlier in the document holds its location
    and claim. A claim-less record at a location another entry holds is NOT one: Appendix A calls
    it ambiguous, and it stays the user's question. Each line the importer stopped on must be one of those, byte for byte, or nothing
    is answered and the run stops as it always did.
    """
    if refusal.exit_code != 5 or not isinstance(refusal.body, dict):
        return None
    asked = refusal.body.get("ambiguities") or []
    if not asked:
        return None
    path = os.path.join(workspace, document)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        parsed = ledger.parse_document(fh.read(), document)
    entries = ledger.open_set(parsed)["entries"]
    orphans = {}
    for entry in entries:
        origin = entry.get("origin") or {}
        if origin.get("kind") not in ("recheck", "waiver"):
            continue
        # Appendix A: a claim-less record at a location other entries hold decides nothing and is
        # the user's question, not an orphan. Only a line no entry could have meant is answered.
        if origin.get("claim") is None and any(
                other is not entry and other["file"] == origin["file"]
                and other["line"] == origin["line"] for other in entries):
            continue
        orphans[origin["line_no"]] = origin
    answers = []
    for row in asked:
        line = row.get("line")
        origin = orphans.get(line)
        if origin is None or row.get("raw") is None:
            return None
        if row["raw"].rstrip() != parsed["lines"][line - 1].rstrip():
            return None
        answers.append({"line": line, "raw": row["raw"], "new_finding": True})
    return {"answered_by": ORPHAN_ANSWERED_BY,
            "answered_on": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
            "doc": document, "answers": answers}


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



# ---- Astra's N1: the record lines the component itself rendered ------------------------------
#
# The same functions as `build_core/native_lines.py` and `signoff_core/native_lines.py` (the two
# cores carry that file byte for byte), with this pilot's own grammar module (`ledger`) and
# client. Records keeps a ranged location on the review line it renders (A7's F9); the legacy
# grammar has no range, so the unchanged strict check (`inputs.strict_ambiguities`) called the
# component's own line unplaceable and stopped `start` with `missing_input`. The records CLI says
# which lines those are (`import-legacy --dry-run`'s `native_rendered`, `events`, `render --run-id`);
# each native occurrence is consumed once, only when the component's count agrees, and the
# unchanged Appendix A check reads what remains. A document with nothing ambiguous costs no CLI
# call, so every decision the baseline made on a document it could read is made the same way
# (E13-1); only a line the component itself rendered is ever set aside.

_GRANT_KINDS = ("waived", "reopened")
_RENDERED_KINDS = (_REVIEW_KIND,) + _BLOCK_KINDS + _GRANT_KINDS
_CARD_KINDS = ("card_set", "card_observed")


def _n1_lines(text):
    """The record lines of rendered block text: every non-blank line that is not a heading."""
    return [line.rstrip() for line in (text or "").split("\n")
            if line.strip() and not line.startswith("### ")]


def _n1_is_legacy(event):
    return (event.get("origin") or {}).get("kind") == "legacy"


def native_runs(rows):
    """The run ids whose events are all native and include a rendered kind, first-seen order."""
    order, legacy_runs, rendering = [], set(), set()
    for row in rows:
        event = row.get("event") or {}
        run_id = (event.get("actor") or {}).get("run_id")
        if not isinstance(run_id, str):
            continue
        if _n1_is_legacy(event):
            legacy_runs.add(run_id)
            continue
        if run_id not in order:
            order.append(run_id)
        if event.get("kind") in _RENDERED_KINDS:
            rendering.add(run_id)
    return [run_id for run_id in order if run_id not in legacy_runs and run_id in rendering]


def occurrences_of_run(rendered, run_events, raised):
    """[{text, where, slice}] for one native run, from its `render` response.

    `run_events` is [(seq, event)] of the run in seq order; `raised` maps a finding id to the
    event that raised it. `render` writes the review blocks one per slice in `review_slices` order,
    each slice's `finding_raised` events in seq order; the recheck block one line per
    `disposition` or `defect_raised` in seq order; then one line per grant. A part whose line
    count disagrees with its events yields nothing (and the count check then fails closed).
    """
    out = []
    slices = list(rendered.get("review_slices") or [])

    def slice_rank(row):
        name = row[1].get("slice") or "none"
        return (slices.index(name) if name in slices else len(slices), row[0])

    review = sorted([row for row in run_events if row[1].get("kind") == _REVIEW_KIND],
                    key=slice_rank)
    lines = _n1_lines(rendered.get("review"))
    if len(lines) == len(review):
        for (_, event), text in zip(review, lines):
            out.append({"text": text, "where": "review", "slice": event.get("slice") or "none"})
    block = [row for row in run_events if row[1].get("kind") in _BLOCK_KINDS]
    lines = _n1_lines(rendered.get("block"))
    if len(lines) == len(block):
        for (_, event), text in zip(block, lines):
            if event.get("kind") == "defect_raised":
                name = event.get("slice")
            else:
                name = (raised.get(event.get("finding")) or {}).get("slice")
            out.append({"text": text, "where": "recheck", "slice": name or "none"})
    grants = [row for row in run_events if row[1].get("kind") in _GRANT_KINDS]
    lines = [line.rstrip() for line in (rendered.get("grants") or [])]
    if len(lines) == len(grants):
        for _row, text in zip(grants, lines):
            out.append({"text": text, "where": None, "slice": None})
    return out


def admits(record, occurrence):
    """Can this document record be the rendering of this occurrence, by kind and slice context?"""
    if occurrence["where"] is None:
        return True  # a grant line is standalone: its grammar names no slice and no heading
    heading = record.get("heading")
    if not heading or heading.get("kind") != occurrence["where"]:
        return False
    names = heading.get("slices") or []
    if occurrence["where"] == "review":
        return bool(names) and names[0] == occurrence["slice"]
    return occurrence["slice"] in names


def match_native(records, occurrences):
    """{record position: occurrence index}: a maximum matching in file order, without recursion.

    Each record takes the lowest free occurrence it admits; only when none is free does a
    breadth-first search look for an augmenting path. A record once matched stays matched, so
    which records are matched is decided in file order.
    """
    options = {}
    for position, record in enumerate(records):
        admitted = [index for index, occ in enumerate(occurrences)
                    if occ["text"] == record["text"] and admits(record, occ)]
        if admitted:
            options[position] = admitted
    owner, matched = {}, {}
    for position in sorted(options):
        free = next((index for index in options[position] if index not in owner), None)
        if free is not None:
            owner[free], matched[position] = position, free
            continue
        parent, seen, queue, head = {}, set(), [position], 0
        while head < len(queue):
            current = queue[head]
            head += 1
            found = None
            for index in options[current]:
                if index in seen:
                    continue
                seen.add(index)
                parent[index] = current
                if index not in owner:
                    found = index
                    break
                queue.append(owner[index])
            if found is not None:
                index = found
                while True:
                    line = parent[index]
                    previous = matched.get(line)
                    owner[index], matched[line] = line, index
                    if line == position:
                        break
                    index = previous
                break
    return matched


def native_card_lines(parsed, rows, document):
    """How many `Status:` lines carry their slice's last card, when a NATIVE event wrote it."""
    last = {}
    for row in rows:
        event = row.get("event") or {}
        kind = event.get("kind")
        if kind not in _CARD_KINDS or event.get("ledger_doc") != document:
            continue
        name = event.get("slice")
        if not isinstance(name, str):
            continue
        value = event.get("value") if kind == "card_observed" else event.get("after")
        last[name] = (value, not _n1_is_legacy(event))
    count = 0
    for entry in parsed.get("slices") or []:
        held = last.get(entry["name"])
        if entry.get("status") is not None and held and held[1] and held[0] == entry["status"]:
            count += 1
    return count


def consumed_lines(client, workspace, document, parsed):
    """The 1-based line numbers of `document` the component itself rendered, confirmed by its
    `native_rendered`; an empty set whenever anything is refused, missing, or disagrees."""
    try:
        preview = client.import_legacy(workspace, document, dry_run=True)
    except rcl.RecordsRefusal:
        return set()
    try:
        expected = int(preview.get("native_rendered") or 0)
    except (TypeError, ValueError):
        return set()
    if expected <= 0:
        return set()
    try:
        rows = client.events(workspace, document).get("results") or []
    except rcl.RecordsRefusal:
        return set()
    by_run, raised, imported = {}, {}, set()
    for row in rows:
        event = row.get("event") or {}
        if event.get("kind") in RAISE_KINDS:
            raised.setdefault(event.get("finding"), event)
        origin = event.get("origin") or {}
        if _n1_is_legacy(event) and origin.get("doc") == document \
                and event.get("kind") != "card_observed" and isinstance(origin.get("line"), int):
            imported.add(origin["line"])
        run_id = (event.get("actor") or {}).get("run_id")
        by_run.setdefault(run_id, []).append((row.get("seq"), event))
    occurrences = []
    for run_id in native_runs(rows):
        try:
            rendered = client.render(workspace, document, run_id)
        except rcl.RecordsRefusal:
            return set()
        occurrences.extend(occurrences_of_run(rendered, sorted(by_run.get(run_id) or [],
                                                               key=lambda row: row[0]), raised))
    records = [record for record in parsed["records"] if record["line_no"] not in imported]
    matched = match_native(records, occurrences)
    if len(matched) + native_card_lines(parsed, rows, document) != expected:
        return set()
    return set(records[position]["line_no"] for position in matched)


def remaining_ambiguities(text, document, consumed):
    """Appendix A's stop check, unchanged, over the document with the consumed lines blanked.

    Returns (the original lines, the ambiguous records `open_set` finds in what remains)."""
    lines = text.split("\n")
    if not consumed:
        return lines, ledger.open_set(ledger.parse_document(text, document))["ambiguities"]
    kept = [("" if number + 1 in consumed else line) for number, line in enumerate(lines)]
    parsed = ledger.parse_document("\n".join(kept), document)
    return lines, ledger.open_set(parsed)["ambiguities"]


def hand_written_ambiguities(client, workspace, document, text):
    """The Appendix A ambiguities of the hand-written records of `document` (N1).

    The unchanged check reads the document whole first; only when it finds something does this
    ask the records CLI which lines the component rendered, and read again without those. A
    document with nothing ambiguous costs no CLI call at all."""
    lines, found = remaining_ambiguities(text, document, None)
    if not found or client is None:
        return lines, found
    consumed = consumed_lines(client, workspace, document, ledger.parse_document(text, document))
    if not consumed:
        return lines, found
    return remaining_ambiguities(text, document, consumed)


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
