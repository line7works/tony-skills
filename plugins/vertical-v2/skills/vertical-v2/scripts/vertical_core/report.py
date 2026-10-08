"""The result and the `VERTICAL:` block (contract sections 3.9 and 9).

`finish` ends a run at a stop (or at its completion): it assembles `result.json` from the run's own
artifacts, validates it against `references/result.schema.json` and the semantic checks S1 to S4,
writes it, and raises the driver's Terminal (exit 10); before that it removes every packet's workspace and
documents (`drop_copies`: scope's previews and every summons copy; the mandates and the two lists stay), so a
run that stops after `scope` leaves no copy of the reviewed tree behind (C1A3-6). A result that fails either check is a defect of
this script (exit 1), never a softened result. `handler` is the `report` phase: the completion, the
`VERTICAL:` block rendered from the result by `forms.py`, and `chat.md`.
"""
import os
import shutil

from station_core import driver, validate
from back_core import trace

from . import common


def _gate_summary(run):
    if not common.has(run, "gate.json"):
        return None
    gate = common.read(run, "gate.json")
    return gate


def _calls(run):
    out = []
    for name, side in (("requests-local.json", "local"), ("requests-outside.json", "outside")):
        if not common.has(run, name):
            continue
        recorded = {}
        record_name = "local.json" if side == "local" else "outside.json"
        if common.has(run, record_name):
            for call in common.read(run, record_name).get("calls") or []:
                recorded[call["call_id"]] = call
        for call in common.read(run, name)["calls"]:
            seen = recorded.get(call["call_id"], {})
            out.append({"call_id": call["call_id"], "row": call["row"], "lens": call.get("lens"), "side": side,
                        "status": seen.get("status"), "model": seen.get("model"), "profile": seen.get("profile"),
                        "reason": seen.get("reason")})
    return out


def build_result(ctx, run, status, tag, reason, selection=None, gate=None, extra=None):
    """The result document, from the run's artifacts and what the caller passes."""
    gate = gate if gate is not None else _gate_summary(run)
    if selection is None:
        selection = {}
        if common.has(run, "selection-build.json"):
            selection["build"] = common.read(run, "selection-build.json")
        elif gate and gate.get("doc"):
            selection["build"] = {"outcome": "one", "named": gate["doc"]}
    ask = common.read(run, "ask.json").get("answer") if common.has(run, "ask.json") else None
    scope = common.read(run, "scope.json") if common.has(run, "scope.json") else {}
    verdict = common.read(run, "verdict.json") if common.has(run, "verdict.json") else {}
    common.check_trace(run)
    lines = trace.read(run.run_dir)
    station_result = {
        "gate": gate, "ask": {"rows": ask["rows"], "words": ask["words"]} if ask else None,
        "depth": scope.get("depth"), "lenses": list(scope.get("lenses") or []), "calls": _calls(run),
        "verdict": verdict.get("verdict"), "findings": verdict.get("findings_count"),
        "refuted": verdict.get("refuted"), "verdict_doc": verdict.get("doc"),
        "review_sheet": scope.get("review_sheet", {}).get("state") if scope else None,
        "method": list(verdict.get("method") or []), "chat": None}
    station_result.update(extra or {})
    writes = list(verdict.get("writes") or [])
    if lines:
        writes.append({"path": trace.path_of(run.run_dir), "kind": "run_artifact", "sha256_before": None,
                       "sha256_after": _sha(trace.path_of(run.run_dir))})
    outside = [w for w in writes if not validate._under(w["path"], run.run_dir)]
    invocation = dict(run.input.get("invocation") or {})
    return ctx.envelope(run_id=run.checkpoint["run_id"], run_dir=run.run_dir, status=status, stop_tag=tag,
                        reason=reason, report_only=common.report_only(run), wrote_nothing=not outside,
                        writes=writes, selection=selection, invocation=invocation,
                        trace={"path": trace.path_of(run.run_dir), "lines": len(lines)},
                        station_result=station_result)


def _sha(path):
    from station_core import fsio
    return fsio.sha256_file(path)


def check(ctx, result):
    errors = validate.errors_for(result, validate.load_schema("result", ctx.prefix, ctx.skill_root), ctx.prefix)
    semantic = validate.semantic(result) if not errors else []
    if errors or semantic:
        raise driver.Defect("the result this run would write does not hold (a defect of the script): %s"
                            % "; ".join("%s %s" % (e.get("path"), e.get("message")) for e in (errors or semantic)[:4]))


def _inside(path, top):
    return os.path.realpath(path).startswith(top.rstrip(os.sep) + os.sep)


def drop_copies(run):
    """Remove every packet's workspace and documents, scope's previews and every summons copy alike; the
    mandates and the two lists stay. The removal never follows a link (C1A4-3): a link at `packets` or
    `summons`, at an entry in either, or at an entry's `workspace` or `documents` is removed as a link, never
    its target, and a folder is removed only when its real path lies inside the run directory's."""
    top = os.path.realpath(run.run_dir)
    for folder in ("packets", "summons"):
        root = common.path_of(run, folder)
        if os.path.islink(root):
            os.unlink(root)
            continue
        if not os.path.isdir(root) or not _inside(root, top):
            continue
        for name in sorted(os.listdir(root)):
            entry = os.path.join(root, name)
            if os.path.islink(entry):
                os.unlink(entry)
                continue
            if not os.path.isdir(entry) or not _inside(entry, top):
                continue
            for part in ("workspace", "documents"):
                target = os.path.join(entry, part)
                if os.path.islink(target):
                    os.unlink(target)
                elif os.path.isdir(target) and _inside(target, top):
                    shutil.rmtree(target, ignore_errors=True)


def finish(ctx, run, status, tag, reason, selection=None, gate=None, extra=None):
    """Write the run's result and end it (exit 10). A run that ends, at a stop or at its completion,
    removes every packet's copies first (C1A3-6): no step after it would."""
    drop_copies(run)
    result = build_result(ctx, run, status, tag, reason, selection=selection, gate=gate, extra=extra)
    check(ctx, result)
    common.write(run, "result.json", result)
    common.advance(run, "done")
    raise driver.Terminal(dict(result, next="done"))
