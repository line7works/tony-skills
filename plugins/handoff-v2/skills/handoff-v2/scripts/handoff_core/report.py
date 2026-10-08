"""The result, the `HANDOFF:` block and the end of a run (contract sections 3.7 and 9).

`finish` ends a run at a stop (or at its completion): it assembles `result.json` from the run's own artifacts,
validates it against `references/result.schema.json` and the semantic checks S1 to S4, writes it, and raises the
driver's Terminal (exit 10). A result that fails either check is a defect of this script (exit 1), never a softened
result. `handler` is the `report` phase: the completion, the `HANDOFF:` block rendered by `forms.py`, `chat.md`, and
the Claude Code adapter's pointer receipt, when there is one, checked and recorded as a write.
"""
import os

from station_core import driver, fsio, validate

from . import common, forms


def _artifact(run, name):
    return common.read(run, name) if common.has(run, name) else None


def build_result(ctx, run, status, tag, reason, selection=None, extra=None, writes=None):
    selection = selection if selection is not None else (_artifact(run, "selection.json") or {})
    doc = _artifact(run, "doc.json") or {}
    photo = _artifact(run, "photograph.json")
    gate = _artifact(run, "gate.json")
    answers = _artifact(run, "answers.json")
    written = _artifact(run, "write.json") or {}
    station_result = {
        "doc": doc.get("doc") or selection.get("doc"), "feature": doc.get("feature"),
        "identity_how": doc.get("identity_how"), "after": (photo or {}).get("finished"),
        "photograph": None if photo is None else {
            "cards": photo["cards"], "open": photo["open"], "repo": photo["repo"], "suite": photo["suite"],
            "records": photo["records"]},
        "questions": None if gate is None else gate["questions"],
        "answers": None if answers is None else answers["summary"],
        "next_move": written.get("next_move"), "block": written.get("block"), "events": written.get("events") or [],
        "cards_after": written.get("cards_after"), "checkpoint": written.get("checkpoint"),
        "pointer": written.get("pointer"), "chat": None}
    station_result.update(extra or {})
    if writes is None:
        writes = list(written.get("writes") or [])
    outside = [w for w in writes if not validate._under(w["path"], run.run_dir)]
    invocation = dict(run.input.get("invocation") or {})
    return ctx.envelope(run_id=run.checkpoint["run_id"], run_dir=run.run_dir, status=status, stop_tag=tag,
                        reason=reason, report_only=common.report_only(run), wrote_nothing=not outside, writes=writes,
                        selection=selection, invocation=invocation, trace=None, station_result=station_result)


def check(ctx, result):
    errors = validate.errors_for(result, validate.load_schema("result", ctx.prefix, ctx.skill_root), ctx.prefix)
    semantic = validate.semantic(result) if not errors else []
    if errors or semantic:
        raise driver.Defect("the result this run would write does not hold (a defect of the script): %s"
                            % "; ".join("%s %s" % (e.get("path"), e.get("message")) for e in (errors or semantic)[:4]))


def finish(ctx, run, status, tag, reason, selection=None, extra=None, writes=None):
    """Write the run's result and end it (exit 10)."""
    result = build_result(ctx, run, status, tag, reason, selection=selection, extra=extra, writes=writes)
    check(ctx, result)
    common.write(run, "result.json", result)
    common.advance(run, "done")
    raise driver.Terminal(dict(result, next="done"))


def _receipt(ctx, run, pointer):
    """The Claude Code adapter's pointer receipt, checked: the run's pointer was the adapter's, every write it names
    holds the bytes it says it wrote, and the pointer file holds the text the core rendered. None when there is no
    receipt; exit 5 when one does not hold."""
    if not common.has(run, "pointer-receipt.json"):
        return None
    receipt = common.read(run, "pointer-receipt.json")
    refusal = None
    if not pointer or not pointer.get("for_adapter"):
        refusal = ("this run's pointer is not the adapter's (%s): no memory pointer is written for it, so a receipt "
                   "has nothing to stand for" % ((pointer or {}).get("note") or "report-only"))
    rows = receipt.get("writes") if isinstance(receipt, dict) else None
    if refusal is None and (not isinstance(rows, list) or len(rows) != 2):
        refusal = "the pointer receipt does not name the pointer file and the index"
    if refusal is None:
        for row in rows:
            path = row.get("path") if isinstance(row, dict) else None
            if not isinstance(path, str) or os.path.islink(path) or fsio.sha256_file_or_none(path) != row.get("sha256_after"):
                refusal = "the pointer receipt's write %r does not hold the bytes it names" % (path,)
                break
        if refusal is None:
            target = next((r["path"] for r in rows if os.path.basename(r["path"]) == pointer["file_name"]), None)
            if target is None:
                refusal = "the pointer receipt names no %s" % pointer["file_name"]
            else:
                with open(target, "rb") as fh:
                    if fh.read() != pointer["text"].encode("utf-8"):
                        refusal = "the pointer file does not hold the text this run rendered"
    if refusal is not None:
        ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"], reason=refusal + "; nothing was "
                              "recorded and the run stays where it was"), 5)
        raise _Refused()
    return [{"path": r["path"], "kind": "memory_pointer", "sha256_before": r.get("sha256_before"),
             "sha256_after": r["sha256_after"]} for r in rows]


class _Refused(Exception):
    pass


def _questions_line(answers):
    if not answers:
        return "0 asked %s 0 answered %s none" % (forms.M, forms.M)
    summary = answers["summary"]
    landed = []
    if summary["in_block"]:
        landed.append("%d in the block" % summary["in_block"])
    if summary["as_ledger_lines"]:
        landed.append("%d as ledger lines" % summary["as_ledger_lines"])
    return "%d asked %s %d answered %s %s" % (summary["asked"], forms.M, summary["answered"], forms.M,
                                               ", ".join(landed) or "none")


def handler(ctx, args):
    """`report --run-dir D --bottom-line TEXT [--skill-note TEXT]`."""
    run = common.open_run(ctx, args.run_dir, ("written",), "report")
    if not args.bottom_line or not args.bottom_line.strip() or "\n" in args.bottom_line:
        raise driver.Usage("report needs --bottom-line: two or three sentences on one line (what was captured, the "
                           "state of the record, what to type after clearing)")
    written = common.read(run, "write.json")
    doc = common.read(run, "doc.json")
    photo = common.read(run, "photograph.json")
    answers = _artifact(run, "answers.json")
    try:
        pointer_writes = _receipt(ctx, run, written.get("pointer"))
    except _Refused:
        return 5
    writes = list(written.get("writes") or []) + list(pointer_writes or [])
    move = written["next_move"]
    repo = written["repo"]
    fields = {"feature": doc["feature"], "after": photo.get("finished") or "none", "doc": doc["doc"],
              "next": move["kickoff"] or move["line"], "repo": forms.repo_text(repo),
              "suite": forms.suite_text(photo["suite"]), "questions": _questions_line(answers),
              "perishables": len((answers or {}).get("perishables") or []), "bottom_line": args.bottom_line.strip(),
              "open": [forms.open_text(f) for f in written.get("open_after") or []],
              "skill_note": args.skill_note}
    chat = forms.render_report(fields)
    common.write_text(run, "chat.md", chat)
    pointer = dict(written.get("pointer") or {}, written=bool(pointer_writes))
    reason = ("the handoff is recorded%s; the thread is safe to clear"
              % (" (report only: nothing was written)" if common.report_only(run) else ""))
    finish(ctx, run, "completed", None, reason, writes=writes, extra={"chat": chat, "pointer": pointer})
