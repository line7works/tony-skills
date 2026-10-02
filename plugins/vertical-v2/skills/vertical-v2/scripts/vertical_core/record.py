"""`record-local` and `record-outside`: the fleets' answers, merged and verified by the executor,
held to the run by the script (contract sections 3.5 and 3.7; readings CR-5, CR-7 and CR-9).

Each call's facts come from readers' own sidecar under `<run dir>/readers/<call id>/sidecar.json`, never
from the answer: its status, effective model, profile, parity line, isolation label, reason and raw file.
A call with no sidecar is refused (record it through readers first). Every summons, whatever its status,
is a trace line with readers' identity as `request` read it.

The local review always completes or the run does not: a lens whose last call is not `ok` stops the run
(`local-incomplete`) once its one re-send is spent or its refusal is deterministic, and a retryable failure
not yet re-sent is refused with the command to re-send it; a floor refusal stops the run
(`floor-refused`). An outside call that is not `ok` is a dropped reviewer, recorded with its status and
reason, never retried, and no finding may be credited to it.

The findings are the executor's merge (deduped on file:line and claim) and verification (the stamp:
CONFIRMED, PLAUSIBLE or REFUTED); the script refuses, exit 5 and nothing written: a CONFIRMED or
PLAUSIBLE finding whose file:line does not exist in the reviewed copy (the export; a packet-only staged
name with `__` for `/` is read back to its path), a REFUTED one with no reason, a severity or confidence
changed from what the reviewer stated with no reason, a finding credited to a call that is not this
phase's or did not come back `ok`, a text holding the line form's separator, and (local) a lens credited
with no finding that does not say what it tried to break.
"""
import os

from station_core import validate
from back_core import trace

from . import common, forms, report

RETRYABLE = ("transport-failed", "empty", "incomplete")


def _refuse(ctx, run, refusals):
    return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"], refusals=refusals,
                                 reason="the answer is refused, nothing was written: %s" % "; ".join(refusals)), 5)


def _answer(ctx, run, path, kind):
    doc = common.load_json_file(path, "answer")
    errors = validate.errors_for(doc, common.schema("answer.schema.json", ctx), ctx.prefix)
    if not errors and doc.get("kind") != kind:
        errors = [{"path": "/kind", "message": "this phase records a %s answer" % kind}]
    return doc, errors


def sidecar_of(run, call):
    path = common.path_of(run, os.path.join("readers", call["call_id"], "sidecar.json"))
    if not os.path.isfile(path):
        return None, "%s has no sidecar at %s: record the call through readers first" % (call["call_id"], path)
    try:
        from station_core import fsio
        body = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        return None, "%s's sidecar cannot be read: %s" % (call["call_id"], exc)
    if (body.get("call_id"), body.get("run_id"), body.get("row")) != (call["call_id"], run.checkpoint["run_id"], call["row"]):
        return None, "%s's sidecar names call %r, run %r, row %r" % (call["call_id"], body.get("call_id"),
                                                                    body.get("run_id"), body.get("row"))
    return body, None


def call_record(call, body):
    return {"call_id": call["call_id"], "row": call["row"], "lens": call.get("lens"), "status": body.get("status"),
            "model": body.get("effective_model"), "profile": body.get("profile"), "parity": body.get("parity"),
            "isolation": body.get("isolation"), "reason": body.get("reason"), "raw_file": body.get("raw_file"),
            "raw_hash": body.get("raw_hash")}


def resolve_location(export, location):
    """(the location as it reads in the reviewed copy, or None when it names nothing there)."""
    path, _, lines = location.rpartition(":")
    first = int(lines.split("-")[0])
    last = int(lines.split("-")[-1])
    for candidate in (path, path.replace("__", "/")):
        full = os.path.normpath(os.path.join(export, candidate))
        if not full.startswith(export.rstrip(os.sep) + os.sep) or not os.path.isfile(full):
            continue
        with open(full, "rb") as fh:
            data = fh.read()
        count = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
        if 1 <= first <= last <= count:
            return "%s:%s" % (candidate, lines)
        return None
    return None


def check_findings(run, findings, calls_ok, side):
    """(the findings with their locations as they read in the copy, [refusal])."""
    export = common.read(run, "scope.json")["export"]
    out, refusals = [], []
    for index, f in enumerate(findings):
        where = "finding %d (%s)" % (index + 1, f["location"])
        for key in ("claim", "scenario", "regrade_reason", "refuted_because", "note"):
            if isinstance(f.get(key), str) and forms.SEP in f[key]:
                refusals.append("%s: its %s holds the line form's separator ' %s '" % (where, key, forms.M))
        strangers = [c for c in f["found_by"] if c not in calls_ok]
        if strangers:
            refusals.append("%s: credited to %s, not a call of this %s fleet that came back ok"
                            % (where, ", ".join(strangers), side))
        if f.get("reported_severity") and f["reported_severity"] != f["severity"] and common.blank(f.get("regrade_reason")):
            refusals.append("%s: the reviewer graded %s and the merge %s, a re-grade with no reason"
                            % (where, f["reported_severity"], f["severity"]))
        if f.get("reported_confidence") and f["reported_confidence"] != f["confidence"] and common.blank(f.get("regrade_reason")):
            refusals.append("%s: the reviewer's confidence %s became %s, a re-grade with no reason"
                            % (where, f["reported_confidence"], f["confidence"]))
        entry = dict(f)
        if f["stamp"] == "REFUTED":
            if common.blank(f.get("refuted_because")):
                refusals.append("%s: REFUTED with no reason" % where)
        else:
            found = resolve_location(export, f["location"])
            if found is None:
                refusals.append("%s: stamped %s at %s, which does not exist in the reviewed copy; a hallucinated "
                                "location is a refutation unless the real site is located and named"
                                % (where, f["stamp"], f["location"]))
            else:
                entry["location"] = found
        out.append(entry)
    return out, refusals


def _summons_lines(ctx, run, requests, records):
    readers = requests["readers"]
    for rec in records:
        line = trace.line(kind="summons", caller=common.STATION, expected="readers", identity=readers["identity"],
                          route=readers["route"], run_dir=requests["run_dir"], status=rec["status"] or "unknown",
                          call_id=rec["call_id"], row=rec["row"], at=common.now())
        trace.append(run.run_dir, line, ctx.skill_root, ctx.prefix)


def record_local(ctx, args):
    run = common.open_run(ctx, args.run_dir, ("requested-local",), "record-local")
    doc, errors = _answer(ctx, run, args.answer, "local")
    if errors:
        return ctx.emit(ctx.envelope(ok=False, error="invalid", run_id=run.checkpoint["run_id"], errors=errors,
                                     reason="the answer does not validate against references/answer.schema.json; "
                                            "nothing was written"), 4)
    if doc["run_id"] != run.checkpoint["run_id"]:
        return _refuse(ctx, run, ["the answer is for run %r, not this run" % doc["run_id"]])
    requests = common.read(run, "requests-local.json")
    records, refusals = [], []
    for call in requests["calls"]:
        body, why = sidecar_of(run, call)
        if why:
            refusals.append(why)
        else:
            records.append(call_record(call, body))
    if refusals:
        return _refuse(ctx, run, refusals)
    last = {}
    for rec in records:
        last[rec["lens"]] = rec
    stop = None
    for lens, rec in last.items():
        if rec["status"] == "ok":
            continue
        if rec["status"] == "floor-refused":
            stop = ("floor-refused", "the local lens %s came back floor-refused (%s): this session is below the floor; "
                                     "no verdict is emitted from below it" % (lens, rec["reason"] or "no reason given"))
            break
        resent = lens in requests.get("resent", [])
        if rec["status"] in RETRYABLE and not resent:
            return _refuse(ctx, run, ["the local lens %s came back %s: re-send it once first (request --resend %s "
                                      "--status %s), then record-local" % (lens, rec["status"], lens, rec["status"])])
        stop = ("local-incomplete", "the local review is incomplete: the lens %s came back %s%s (%s); the local review "
                                    "always completes or the run does not" % (lens, rec["status"],
                                                                              " after its re-send" if resent else "",
                                                                              rec["reason"] or "no reason given"))
        break
    if stop:
        _summons_lines(ctx, run, requests, records)
        common.write(run, "local.json", {"calls": records, "findings": [], "tried": [], "method": None,
                                         "stopped": stop[0]})
        report.finish(ctx, run, "stopped", stop[0], stop[1])
    ok_ids = dict((r["call_id"], r["lens"]) for r in records if r["status"] == "ok")
    findings, refusals = check_findings(run, doc["findings"], ok_ids, "local")
    lenses = set(last)
    for t in doc["tried"]:
        if t["lens"] not in lenses:
            refusals.append("a tried entry names the lens %r, which this run did not summon" % t["lens"])
        if t["how"] == "executed" and common.blank(t.get("output")):
            refusals.append("the lens %s's executed check %r carries no output" % (t["lens"], t["what"]))
    credited = set(ok_ids[c] for f in doc["findings"] for c in f["found_by"] if c in ok_ids)
    for lens in sorted(lenses - credited):
        if not any(t["lens"] == lens for t in doc["tried"]):
            refusals.append("the lens %s is credited with no finding and says nothing it tried to break: a review that "
                            "finds nothing states what it tried (tried)" % lens)
    if refusals:
        return _refuse(ctx, run, refusals)
    _summons_lines(ctx, run, requests, records)
    common.write(run, "local.json", {"calls": records, "findings": findings, "tried": doc["tried"],
                                     "method": doc["method"]})
    common.advance(run, "recorded-local")
    named = common.read(run, "ask.json")["answer"]["rows"]
    return ctx.emit(ctx.envelope(next="request --outside" if named else "verdict", run_id=run.checkpoint["run_id"],
                                 findings=len(findings), calls=[{"call_id": r["call_id"], "status": r["status"]}
                                                                for r in records]))


def record_outside(ctx, args):
    run = common.open_run(ctx, args.run_dir, ("requested-outside",), "record-outside")
    doc, errors = _answer(ctx, run, args.answer, "outside")
    if errors:
        return ctx.emit(ctx.envelope(ok=False, error="invalid", run_id=run.checkpoint["run_id"], errors=errors,
                                     reason="the answer does not validate against references/answer.schema.json; "
                                            "nothing was written"), 4)
    if doc["run_id"] != run.checkpoint["run_id"]:
        return _refuse(ctx, run, ["the answer is for run %r, not this run" % doc["run_id"]])
    requests = common.read(run, "requests-outside.json")
    records, refusals = [], []
    for call in requests["calls"]:
        body, why = sidecar_of(run, call)
        if why:
            refusals.append(why)
        else:
            records.append(call_record(call, body))
    if refusals:
        return _refuse(ctx, run, refusals)
    ok_ids = dict((r["call_id"], r["row"]) for r in records if r["status"] == "ok")
    findings, refusals = check_findings(run, doc["findings"], ok_ids, "outside")
    if refusals:
        return _refuse(ctx, run, refusals)
    _summons_lines(ctx, run, requests, records)
    common.write(run, "outside.json", {"calls": records, "findings": findings,
                                       "ledger_notes": doc.get("ledger_notes")})
    common.advance(run, "recorded-outside")
    return ctx.emit(ctx.envelope(next="verdict", run_id=run.checkpoint["run_id"], findings=len(findings),
                                 dropped=[{"row": r["row"], "status": r["status"], "reason": r["reason"]}
                                          for r in records if r["status"] != "ok"]))
