"""Assembling the one result of a run.

Every run ends in one, including every stop, and it is written to the run directory the input
names (lane contract section 8). Two status fields on purpose:

    terminal_status   `completion` or `stop` — which KIND of end this was
    status            this core's named vocabulary inside that kind

A run whose named checks failed or could not run is a COMPLETION with a named result
(`checks_not_passed`), not a stop; amendment A3 item 1 is the ruling, and the card simply does
not move. That ruling covers FAILING CHECKS and nothing else.

A run whose recorded answer cannot be recorded is a STOP (`answer_refused`). The control room
reversed itself on this in the lane's first check round, and the reversal is right: a run that
may record nothing did not proceed, whatever else it computed. It still reports the source set,
the out-of-scope list and every check, because a stop reports what it found before it stopped.

What every result carries, whatever it ended as, when the run got far enough to know it: the
three lists of the source set and their base, the slice's contract, the out-of-scope list with
each path's stated reason, every named check with its result and its output, what the answer
claimed, where the card stands, and everything the run asked the records component for. A stop
before one of those existed carries it as null rather than as an invention.
"""
from . import checks as checksmod, validate

COMPLETION_STATUSES = ("completed", "checks_not_passed", "not_complete")
STOP_STATUSES = ("stopped", "answer_refused")
"""The two ends. `stopped` is the tool unable to proceed and carries a `stop_tag` from
STOP_TAGS; `answer_refused` is an answer this core may not record and carries `refusal_reason`
instead. Both are `terminal_status: "stop"`."""

STOP_TAGS = (
    "no_doc",                 # the build doc is not in the workspace
    "no_slice",               # the document carries no such slice
    "no_git",                 # the workspace is not a git work tree root
    "no_base",                # the base ref does not resolve to a commit
    "legacy_unplaced",        # the importer could not place a record line (amendment A3 item 3)
    "card_drift",             # the log and the document disagree about the card
    "open_blocker",           # the slice carries an open BLOCKER and the input did not allow it
    "scope_unexplained",      # a path is outside the slice's named paths with no stated reason
    "outside_edit",           # the build doc moved between the plan and the write
    "records_invalid",        # the component refused an event (exit 4)
    "records_ambiguous",      # the component could not place a record (exit 5)
    "records_stale_source",   # the workspace moved under a clear (exit 6)
    "records_conflict",       # a moved head or a live lock (exit 7)
    "records_failed",         # any other refusal of the component
)
"""Every tag a stop of this core can carry, in one place.

An input that fails its schema and an answer file that cannot be read are NOT here: neither
ends a run. The first is exit 4 before a run exists and the second is exit 2 with the run left
where it was, so neither ever reaches a result. `scripts/tests/test_schemas.py` holds this tuple
and the result schema's published list to each other in both directions."""

EMPTY_RECORDS = {"log": None, "levelled": {"ran": False, "dry_run": False, "would_import": None,
                                           "imported": None, "unparsed": None,
                                           "native_rendered": None},
                 "head_before": None, "head_after": None, "appended": [], "wrote": False,
                 "refused": None}


def assemble(run, status, reason, root=None, stop_tag=None, stop_reason=None,
             refusal_reason=None, out_of_scope=None, checks=None, records_extra=None,
             answer_refusals=None, card_after=None, card_moved=False, card_reason=None,
             card_line=None, receipt=None, resumed_half=None):
    """One result document, ready to validate and write."""
    if status == "stopped" and stop_tag not in STOP_TAGS:
        raise ValueError("%r is not one of this core's stop tags; every stop this core can make "
                         "is named in STOP_TAGS and in the result schema" % stop_tag)
    body = run.doc
    answer = body.get("answer") or {}
    contract = body.get("contract")
    source = body.get("source_set")
    card_before = body.get("card_before") or "none"
    check_rows = list(checks or [])
    out_rows = list(out_of_scope or [])
    refusals = list(answer_refusals or [])
    records_block = dict(records_extra or body.get("records") or EMPTY_RECORDS)
    for key, value in EMPTY_RECORDS.items():
        if records_block.get(key) is None and value is not None:
            records_block[key] = value        # `levelled` is an object on every result, never null
        records_block.setdefault(key, value)

    wrote_nothing = not any(entry.get("kind") != "run_artifact" for entry in (body.get("writes") or []))

    result = {
        "result_version": 1,
        "interface_version": 1,
        "plugin_version": validate.plugin_version(root),
        "run_id": run.run_id,
        "status": status,
        "terminal_status": "stop" if status in STOP_STATUSES else "completion",
        "reason": reason,
        "stop_reason": (stop_reason or reason) if status in STOP_STATUSES else None,
        "stop_tag": stop_tag if status == "stopped" else None,
        "refusal_reason": refusal_reason,
        "report_only": bool(run.report_only),
        "wrote_nothing": wrote_nothing,
        "workspace": run.workspace,
        "run_dir": run.run_dir,
        "build_doc": run.document,
        "slice": run.slice_name,
        "checks": check_rows,
        "out_of_scope": out_rows,
        "records": records_block,
        "identity": body.get("identity"),
        "writes": list(body.get("writes") or []),
        "receipt": receipt,
        "resumed_half": resumed_half,
        "next": "done",
    }
    if source:
        result["source_set"] = source
    if contract:
        result["contract"] = contract
    if answer:
        result["answer"] = {
            "session_id": answer.get("session_id"),
            "claimed_status": answer.get("claimed_status"),
            "claimed_card": answer.get("claimed_card"),
            "accepted": not refusals,
            "refusals": refusals,
            "path": run.artifact("answer.json"),
        }
    result["card"] = {
        "before": card_before,
        "after": card_after if card_after is not None else card_before,
        "moved": bool(card_moved),
        "reason": card_reason or _card_reason(status, check_rows, out_rows, answer, card_before),
        "document_line": card_line,
    }
    return result


def _card_reason(status, check_rows, out_rows, answer, card_before):
    """Why the card stands where it does, in one sentence, for every status that did not move it."""
    if status == "stopped":
        return "the run stopped before the card was decided, so it stays at %r" % card_before
    if status == "answer_refused":
        return ("the recorded answer was refused, so it was neither acted on nor repaired and the "
                "card stays at %r" % card_before)
    not_passed = checksmod.not_passed(check_rows)
    if not_passed:
        return ("%d of the slice's named checks did not pass (%s), so the card stays at %r"
                % (len(not_passed), ", ".join(row["name"] for row in not_passed), card_before))
    unexplained = [row for row in out_rows if not row.get("reason_given")]
    if unexplained:
        return ("%d out-of-scope path(s) carry no stated reason, so the card stays at %r"
                % (len(unexplained), card_before))
    if answer.get("claimed_status") != "complete":
        return ("the recorded answer claims %r rather than `complete`, so the card stays at %r"
                % (answer.get("claimed_status"), card_before))
    return "the card stays at %r" % card_before
