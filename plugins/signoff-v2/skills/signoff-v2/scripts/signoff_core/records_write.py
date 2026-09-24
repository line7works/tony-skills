"""The recording transaction: level, pin, append, render, place, mirror, card.

The order is the brief's, and every step of it is receipted:

1. **Level the log (CR-1).** v1 signoff writes findings into the Markdown by hand, so a document
   can be ahead of its log. Every phase that reads the document's records runs `import-legacy`
   for it first — a dry run for a read-only command, the real thing before a write. The importer
   is idempotent and a pass that finds no news appends nothing.

   Amendment A3 item 3: the importer reads hand-written records more loosely than the pilot's
   stop rule and refuses an orphan clearing line. This station stops on ANY importer signal —
   `legacy_unparsed` above zero in the dry run, exit 5, or any refusal — rather than trusting the
   importer's silence. It does not build a second record grammar and it changes nothing in the
   records component.

2. **Pin the head.** The head the run read its state against is pinned at `scope`. At `record`,
   BEFORE this run's own levelling, the log must still be at that head; an event another writer
   appended between the two phases is a named conflict stop before any append. The comparison is
   taken before the levelling precisely so CR-1's own import events are never the ones it flags,
   and the pin then advances to the head the levelling produced.

3. **Append the findings**, one batch, `--expect-head` the pinned head: a `finding_raised` per
   raised finding. All or none. Signoff never clears a finding.

4. **Render** the block with `render --run-id`, so the Markdown is the component's bytes.

5. **Place** the block at the ledger home's tail, then **copy** it to the verdict doc under
   `docs/reviews/`, then check the copy with `mirrors`.

6. **The card**: the slice's `Status:` line, and a `card_set` append under the same receipt
   pattern, made only for a status line that actually landed.

Every refusal the component returned is persisted as `refused` before the named stop is
delivered, and no later pass retries it. Every unknown outcome is settled against the head the
receipt already names. A read that failed is a stop, never an empty set.
"""
import os

from . import canon, ledger, receipt as rcpt
from . import native_lines as native
from . import records_client as rcl
from .constants import STATION

FINDINGS = "findings"
CARD = "card"


class Stop(RuntimeError):
    """A named terminal stop of the transaction."""

    def __init__(self, status, reason_code, reason, extra=None):
        RuntimeError.__init__(self, reason)
        self.status = status
        self.reason_code = reason_code
        self.reason = reason
        self.extra = dict(extra or {})


def _refusal_stop(status, reason_code, refusal, extra=None):
    body = dict(extra or {})
    body.update({"records_exit": refusal.exit_code, "records_error": refusal.error,
                 "records_command": refusal.command})
    return Stop(status, reason_code, refusal.sentence(), body)


# ---- 1. levelling ------------------------------------------------------------------------

def unplaceable(workspace, doc, client=None):
    """Appendix A's stop check, unchanged, over the document's hand-written records (Astra's F12).

    `record_grammar.py` is the recheck pilot's `recheck_core/ledger.py` byte for byte, and a test
    holds the two equal: the pilot's own reader, which E13 slice 1 kept as an ambiguity DETECTOR
    (`inputs.strict_ambiguities`) and never as a source of records. Nothing here reads a finding,
    an open set or a card from it — those stay the component's. It answers one question before
    the log is levelled: does the document carry a record line Appendix A cannot place? The
    importer reads more loosely, so its silence is not an answer.

    Astra's N1: the lines the records component ITSELF rendered for native events (a review line
    keeps a ranged location since A7's F9, which the legacy grammar has no shape for) are not
    hand-written. With a `client`, `native_lines.hand_written_ambiguities` asks the records CLI
    which lines those are, consumes each native occurrence once, and applies the unchanged check to
    the rest; only lines the component rendered are set aside, and only when its own
    `native_rendered` agrees.

    Returns `[{doc, line, raw, reason}]`, empty when every record line is placeable.
    """
    text = ledger.read_text(workspace, doc)
    if text is None:
        return []
    lines, found = native.hand_written_ambiguities(client, workspace, doc, text)
    return [{"doc": doc, "line": row["line_no"], "raw": lines[row["line_no"] - 1],
             "reason": row.get("reason") or "matches no Appendix A shape"}
            for row in found]


def strict_stop(workspace, doc, client=None):
    """The Appendix A stop, as the pilot takes it: `missing_input`, naming each line."""
    rows = unplaceable(workspace, doc, client)
    if not rows:
        return
    raise Stop("missing_input", "legacy_ambiguous",
               "%d record line(s) of %s fit no Appendix A shape, so this run will not level the "
               "log over them or record a verdict against a record it cannot place: %s. The "
               "records component's importer reads more loosely than Appendix A, and its silence "
               "does not authorize proceeding. Fix or answer each line and run again; nothing was "
               "written." % (len(rows), doc, "; ".join("%s:%d: %s (%s)" % (
                   r["doc"], r["line"], r["raw"], r["reason"]) for r in rows)),
               {"doc": doc, "unplaced": rows})


def level(client, workspace, doc, dry_run):
    """Run the importer over `doc` and stop on any signal it gives (CR-1, amendment A3 item 3).

    First the strict Appendix A check over the document's hand-written records (`strict_stop`,
    Astra's F12), before the importer reads anything."""
    strict_stop(workspace, doc, client)
    try:
        report = client.import_legacy(workspace, doc, dry_run=dry_run)
    except rcl.RecordsRefusal as refusal:
        status = "missing_input" if refusal.exit_code == 5 else "recording_failed"
        code = "importer_ambiguous" if refusal.exit_code == 5 else "importer_refused"
        raise _refusal_stop(status, code, refusal,
                            {"doc": doc,
                             "ambiguities": (refusal.body or {}).get("ambiguities", [])})
    unparsed = int((report.get("counts") or {}).get("legacy_unparsed") or 0)
    if unparsed:
        raise Stop("stopped", "legacy_unparsed",
                   "the records component's importer read %d line(s) under a record heading in %s "
                   "that fit no shape it accepts (`legacy_unparsed`). This station stops on a "
                   "record its own reader cannot place rather than trusting the importer's "
                   "silence (amendment A3 item 3). Interface version 1 reports the COUNT and not "
                   "the line numbers, so read the document's record headings yourself, or run "
                   "`records.py survey`, and settle each line before running again."
                   % (unparsed, doc),
                   {"doc": doc, "legacy_unparsed": unparsed, "lines": []})
    return report


def identity_of(client, workspace):
    """The component's six-field identity, or a named stop carrying its refusal (Astra's F7)."""
    try:
        return client.identity(workspace)["identity"]
    except rcl.RecordsRefusal as refusal:
        raise _refusal_stop(_status_for(refusal.exit_code), "identity_refused", refusal)


def head_of(client, workspace, doc):
    """The log's head, or a stop. A read that failed is never an empty log."""
    try:
        return client.verify(workspace, doc)
    except rcl.RecordsRefusal as refusal:
        raise _refusal_stop("recording_failed", "log_unreadable", refusal, {"doc": doc})


def events_of(client, workspace, doc, kind=None):
    try:
        return client.events(workspace, doc, kind=kind)
    except rcl.RecordsRefusal as refusal:
        raise _refusal_stop("recording_failed", "history_unreadable", refusal,
                            {"doc": doc, "kind": kind})


def run_events(client, workspace, doc, run_id, kind):
    """This run's events of one kind. A failed read raises; it never returns an empty set."""
    body = events_of(client, workspace, doc, kind=kind)
    return [row for row in body.get("results", [])
            if ((row.get("event") or {}).get("actor") or {}).get("run_id") == run_id]


# ---- 3. the events this station writes -----------------------------------------------------

def location_object(raw, path, line):
    return {"raw": raw, "file": path, "line": line, "line_end": None, "tag": None,
            "more": [], "resolved": bool(path and line)}


def finding_events(raised, doc, slice_name, at, run_id, harness, identity, raised_by):
    """One `finding_raised` per raised finding, in the order the reviewer reported them."""
    events = []
    for row in raised:
        events.append({
            "v": 1,
            "kind": "finding_raised",
            "at": at,
            "ledger_doc": doc,
            "slice": slice_name,
            "severity": row["severity"],
            "location": location_object(row["location"], row["file"], row["line"]),
            "claim": row["claim"],
            "scenario": row["scenario"],
            "raised_by": raised_by,
            "actor": {"station": STATION, "run_id": run_id, "harness": harness},
            "origin": {"kind": "native"},
            "source": {"known": True, "identity": identity},
        })
    return events


def card_event(doc, slice_name, before, after, at, run_id, harness, identity):
    return {
        "v": 1, "kind": "card_set", "at": at, "ledger_doc": doc, "slice": slice_name,
        "before": before, "after": after,
        "actor": {"station": STATION, "run_id": run_id, "harness": harness},
        "origin": {"kind": "native"},
        "source": {"known": True, "identity": identity},
    }


def do_append(client, receipt, name, workspace, doc, events, expect_head, scratch_dir, log):
    """One append, receipted both sides. A refusal is persisted before it is raised.

    `log` is the component's OWN reported path for this document's log. This station never
    computes it: the slug rule (the escapes, the separator) is the component's, and duplicating
    it here would be a copy of its code in all but name."""
    receipt.append_intent(name, log, expect_head, events)
    try:
        body = client.append(workspace, doc, events, expect_head, scratch_dir)
    except rcl.RecordsRefusal as refusal:
        receipt.append_refused(name, refusal.exit_code, refusal.error, refusal.sentence())
        raise _refusal_stop(_status_for(refusal.exit_code), "append_refused", refusal,
                            {"append": name})
    receipt.append_landed(name, body["head"], [row["seq"] for row in body.get("appended", [])])
    return body


def _status_for(exit_code):
    """The pilot's mapping of a component refusal onto a station status (Revision 6)."""
    return {4: "recording_failed", 5: "missing_input", 6: "stale_source",
            7: "recording_failed"}.get(exit_code, "recording_failed")


def settle_append(client, receipt, name, workspace, doc, events, run_id, kind, scratch_dir):
    """Make the append, or settle one whose outcome this run never learned.

    Three states, and the difference between them is Revision 7:

    - `landed`  : nothing to do (reported recovered when a stopped pass found it in the log).
    - `refused` : definitive. The same named stop is delivered again and nothing is retried.
    - `unknown` : the crash window. Ask the log for THIS RUN's events of this kind; a failed read
                  is a stop, never an empty set. They are there, so only the receipt's record was
                  missing and the block is completed from the log and marked recovered; there are
                  none, so the append never landed and is made now — against the head the RECEIPT
                  names, never one read afresh.
    """
    block = receipt.append_block(name)
    if block is None:
        return None, False
    if block["outcome"] == rcpt.LANDED:
        # punch-F2: an append an earlier stopped pass found in the log is still a RECOVERED one,
        # and the run's result says so when a later pass completes.
        return block, bool(block.get("recovered"))
    if block["outcome"] == rcpt.REFUSED:
        refused = block["refused"]
        raise Stop(_status_for(refused["exit_code"]), "append_refused", refused["reason"],
                   {"append": name, "records_exit": refused["exit_code"],
                    "records_error": refused["error"],
                    "definitive": True})
    landed = run_events(client, workspace, doc, run_id, kind)
    if landed:
        verified = head_of(client, workspace, doc)
        receipt.append_landed(name, verified["head"],
                              [row["seq"] for row in landed], recovered=True)
        return receipt.append_block(name), True
    try:
        body = client.append(workspace, doc, events, block["expected_head"], scratch_dir)
    except rcl.RecordsRefusal as refusal:
        receipt.append_refused(name, refusal.exit_code, refusal.error, refusal.sentence())
        raise _refusal_stop(_status_for(refusal.exit_code), "append_refused", refusal,
                            {"append": name,
                             "expected_head": block["expected_head"]})
    receipt.append_landed(name, body["head"], [row["seq"] for row in body.get("appended", [])])
    return receipt.append_block(name), False


# ---- 5. the document steps -----------------------------------------------------------------

def plan_document_steps(workspace, doc, block_text, verdict_rel, verdict_text, slice_name,
                        card_before, card_after):
    """Every document step, with its target, its content, and the hashes before and after."""
    steps = []
    build_text = ledger.read_text(workspace, doc) or ""
    after_block = build_text
    if block_text.strip():
        # A clean review raises nothing, so there is no block step at all. The verdict doc and
        # the card still land: a signature is a record whether or not it carries findings.
        after_block = ledger.append_at_home(build_text, block_text)
        steps.append({
            "kind": "block", "target": doc, "content": block_text,
            "before_sha256": canon.sha256_hex(build_text),
            "after_sha256": canon.sha256_hex(after_block),
            "text_after": after_block,
        })
    existing = ledger.read_text(workspace, verdict_rel) or ""
    steps.append({
        "kind": "verdict_doc", "target": verdict_rel, "content": verdict_text,
        "before_sha256": canon.sha256_file_or_none(os.path.join(workspace, verdict_rel)),
        "after_sha256": canon.sha256_hex(verdict_text),
        "text_after": verdict_text,
    })
    after_card = ledger.set_card(after_block, slice_name, card_after)
    steps.append({
        "kind": "card", "target": doc, "value": card_after, "before_value": card_before,
        "before_sha256": canon.sha256_hex(after_block),
        "after_sha256": canon.sha256_hex(after_card),
        "text_after": after_card,
    })
    del existing
    return steps


def apply_steps(receipt, workspace):
    """Walk the plan against the VIRTUAL state of each target, not the file at rest.

    Two steps of this plan write the same file — the block, then the card — so "does the target
    hash to this step's planned hash" is the wrong question the moment a later step has already
    moved it. The pilot's rule (section 11) is the right one and this is it: keep a virtual hash
    per target, starting at that target's hash before its FIRST step. A step with a `done` entry
    advances the virtual hash to its planned hash. For a step without one, compare the target's
    CURRENT hash with that step's planned hash after (it landed, and only the `done` entry was
    lost: mark it done and advance) or with the virtual hash before it (redo it, replaying the
    plan's stored content, then advance). A hash matching neither is an outside edit, which stops
    the run rather than becoming the new baseline.

    Completed steps are never repeated, so a settling pass writes nothing twice.
    """
    applied, redone, virtual = [], [], {}
    for step in receipt.steps():
        virtual.setdefault(step["target"], step["before_sha256"])
    for index, step in enumerate(receipt.steps()):
        target_rel = step["target"]
        target = os.path.join(workspace, target_rel)
        now = canon.sha256_file_or_none(target)
        if step["state"] == rcpt.DONE:
            virtual[target_rel] = step["after_sha256"]
            continue
        if now == step["after_sha256"]:
            receipt.step_done(index, now)
            virtual[target_rel] = step["after_sha256"]
            continue
        if now != virtual[target_rel]:
            raise Stop("recording_failed", "outside_edit",
                       "%s changed outside this run between the plan and step %d (%s); the "
                       "baseline is never regenerated from edited bytes"
                       % (target_rel, index, step["kind"]),
                       {"target": target_rel, "step": index,
                        "planned_before": virtual[target_rel],
                        "planned_after": step["after_sha256"], "observed": now})
        receipt.step_intent(index)
        ledger.write_text(workspace, target_rel, step["text_after"])
        observed = canon.sha256_file_or_none(target)
        receipt.step_done(index, observed)
        virtual[target_rel] = step["after_sha256"]
        applied.append(step["kind"])
    verify_targets(receipt, workspace)
    return applied, redone


def verify_targets(receipt, workspace):
    """Every FULLY completed target is at its final planned hash, or the run stops (Astra's F6).

    A target whose steps are all `done` must hash to the planned hash after its last step. Anything
    else is an edit that reached it after this run wrote it — in a crash window, or between the
    write and the card append — and the run stops `outside_edit`, leaving the edited bytes as they
    are: never repaired, never rewritten, never read back as the card this run set. A target with
    a pending or intent step is classified by `apply_steps` before/after as it always was.
    """
    finals, complete = {}, {}
    for step in receipt.steps():
        target = step["target"]
        finals[target] = step["after_sha256"]
        complete[target] = complete.get(target, True) and step["state"] == rcpt.DONE
    for target in sorted(finals):
        if not complete[target]:
            continue
        now = canon.sha256_file_or_none(os.path.join(workspace, target))
        if now != finals[target]:
            raise Stop("recording_failed", "outside_edit",
                       "%s was written by this run and has changed since: it hashes to %s, not the "
                       "%s this run's last step on it left. An outside edit is never repaired and "
                       "never read back as this run's own record; it is left exactly as it is"
                       % (target, (now or "nothing")[:12], (finals[target] or "")[:12]),
                       {"target": target, "planned_after": finals[target], "observed": now})
