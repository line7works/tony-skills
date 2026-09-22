"""Assembling the one result, and the chat block a person reads.

Every run ends in a result with a terminal status, including every stop. The result is written to
the run directory the input names, which is outside the workspace, so the record of a run is
never part of the source the next run reviews.

The chat block is v1 signoff's Output section, kept: the same fields in the same order, with the
two lines this station can now fill from measurement rather than from prose — the source set it
computed, and what it withheld from the reviewer.
"""
from . import verdict as vdmod
from .constants import INTERFACE_VERSION

TERMINAL = {"completed": "completion"}


def assemble(resolved, plugin_version, status, **parts):
    """One result document. `parts` supplies whatever the phase that stopped had computed."""
    invocation = resolved.get("invocation") or {}
    target = resolved.get("target") or {}
    review = resolved.get("review") or {}
    raised = parts.get("findings") or []
    result = {
        "protocol_version": 1,
        "interface_version": INTERFACE_VERSION,
        "plugin_version": plugin_version,
        "status": status,
        "terminal_status": TERMINAL.get(status, "stop"),
        "stop_reason": parts.get("stop_reason"),
        "stop_reason_code": parts.get("stop_reason_code"),
        "refusal_reason": parts.get("refusal_reason"),
        "answer_refused": bool(parts.get("answer_refused")),
        "report_only": bool(resolved.get("report_only")),
        "writes_none": bool(parts.get("writes_none")),
        "run": {
            "run_id": invocation.get("run_id"),
            "run_dir": invocation.get("run_dir"),
            "workspace": resolved.get("workspace"),
            "build_doc": target.get("build_doc"),
            "slice": target.get("slice"),
            "run_date": invocation.get("run_date"),
            "caller": invocation.get("caller"),
            "harness": invocation.get("harness"),
            "route": review.get("route"),
            "depth": review.get("depth"),
            "lenses": list(review.get("lenses") or []),
        },
        "reviewer": parts.get("reviewer"),
        "review_sheet": parts.get("review_sheet"),
        "source_identity": parts.get("source_identity"),
        "source_set": parts.get("source_set"),
        "packet": parts.get("packet"),
        "findings": raised,
        "notes": parts.get("notes") or [],
        "checks_executed": parts.get("checks_executed") or [],
        "clean_review_checks_listed": bool(parts.get("clean_review_checks_listed")),
        "verdict": parts.get("verdict"),
        "verdict_stated": parts.get("verdict_stated"),
        "verdict_matches_mapping": parts.get("verdict_matches_mapping"),
        "verdict_recorded": bool(parts.get("verdict_recorded")),
        "verdict_doc": parts.get("verdict_doc"),
        "card": parts.get("card"),
        "records": parts.get("records"),
        "records_written": parts.get("records_written") or [],
        "recovered": parts.get("recovered") or [],
        "receipt": parts.get("receipt"),
        "problems": parts.get("problems") or [],
    }
    return result


def chat_block(result):
    """v1 signoff's Output block, filled from what this run measured."""
    run = result["run"]
    raised = result["findings"]
    counts = vdmod.counts([row["severity"] for row in raised])
    source = result.get("source_set") or {}
    packet = result.get("packet") or {}
    lines = []
    lines.append("SIGN-OFF: %s" % run.get("slice"))
    lines.append("Verdict: %s" % (result.get("verdict") or "NONE RECORDED (%s)" % result["status"]))
    scope = ("%d committed, %d changed, %d untracked since %s"
             % (len(source.get("committed", [])), len(source.get("changed", [])),
                len(source.get("untracked", [])), source.get("base_ref"))
             if source else "not computed")
    lines.append("Scope: %s  ·  Spec: %s" % (scope, run.get("build_doc")))
    reviewer = result.get("reviewer") or {}
    lines.append("Depth: %s%s  ·  Route: %s  ·  Reviewer: %s  ·  Independent: %s"
                 % (run.get("depth"), (" + " + ", ".join(run.get("lenses") or [])) if run.get("lenses") else "",
                    reviewer.get("route") or "none", reviewer.get("session_id") or "none",
                    "yes" if reviewer.get("independent") else "NO"))
    lines.append("Method: %d check(s) executed by the reviewer  ·  Withheld from the packet: %d"
                 % (len(result.get("checks_executed") or []), len(packet.get("withheld") or [])))
    lines.append("Verdict doc: %s" % (result.get("verdict_doc") or "none — nothing recorded"))
    got_sheet = result.get("review_sheet")
    if got_sheet:
        from . import sheet as sheetmod
        lines.append(sheetmod.chat_line(got_sheet))
    card = result.get("card") or {}
    lines.append("Card: %s"
                 % ("%s → %s" % (card.get("before"), card.get("after")) if card.get("moved")
                    else "unchanged"))
    if result.get("report_only"):
        lines.append("Report-only: nothing was written to the workspace and nothing to the log.")
    lines.append("")
    lines.append("Bottom line: %s" % bottom_line(result, counts))
    lines.append("")
    for severity in ("BLOCKER", "MAJOR", "MINOR"):
        rows = [row for row in raised if row["severity"] == severity]
        if rows:
            lines.append(severity)
            for row in rows:
                lines.append("- %s · %s · %s · evidence: %s"
                             % (row["severity"], row["location"], row["claim"],
                                row["evidence_kind"]))
    notes = result.get("notes") or []
    if notes:
        lines.append("Kept as notes, not raised")
        for row in notes:
            lines.append("- %s · %s · %s" % (row.get("location"), row.get("claim"), row.get("why")))
    lines.append("Tried and failed to break:")
    for row in (result.get("checks_executed") or []):
        head = (row.get("output") or "").strip().split("\n")[0]
        lines.append("- %s (%s) → %s" % (row.get("name"), row.get("command") or "no command", head))
    if not (result.get("checks_executed") or []):
        lines.append("- nothing was executed; this review lists no check it ran")
    for row in (result.get("problems") or []):
        lines.append("Refused: %s" % row.get("why", row))
    return "\n".join(lines) + "\n"


def bottom_line(result, counts):
    if result["status"] != "completed":
        return ("The run stopped: %s No verdict was recorded and nothing was repaired."
                % (result.get("stop_reason") or "no reason given."))
    if result.get("report_only"):
        return ("Report-only. The review covered the slice's source set and raised %d finding(s) "
                "in its report; nothing was written to the workspace or the log."
                % len(result["findings"]))
    if not result["findings"]:
        return ("The slice holds against the checks the reviewer ran, listed above. Nothing was "
                "found to raise.")
    return ("%d BLOCKER, %d MAJOR, %d MINOR raised against the slice's source set, each with a "
            "location inside it and a scenario. Fix them, then /recheck verifies the fixes and "
            "flips the card." % (counts["BLOCKER"], counts["MAJOR"], counts["MINOR"]))
