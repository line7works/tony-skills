"""`record-local` and `record-outside`: the fleets' answers, merged and verified by the executor,
held to the run by the script (contract sections 3.5 and 3.7; readings CR-5, CR-7 and CR-9; the design
round's A4, class (b)).

Each call's facts come from readers' own sidecar under `<run dir>/readers/<call id>/sidecar.json`, never
from the answer: its status, effective model, profile, parity line, isolation label, reason and raw file.
A call with no sidecar is refused (record it through readers first), and so is an `ok` call whose capture
(`raw.md`) is not where readers puts it or no longer matches readers' `raw_hash`. Every summons, whatever
its status, is a trace line with readers' identity as `request` read it.

The local review always completes or the run does not: a lens whose last call is not `ok` stops the run
(`local-incomplete`) once its one re-send is spent or its refusal is deterministic, and a retryable failure
not yet re-sent is refused with the command to re-send it; a floor refusal stops the run
(`floor-refused`). An outside call that is not `ok` is a dropped reviewer, recorded with its status and
reason, never retried, and no finding may be credited to it.

`record-local` is the only writer of the local verdict. When it completes it writes `local.json` and then
`local-receipt.json` (`references/local-receipt.schema.json`, closed): the run id, each local call's id,
row and lens with the sha256 of the sidecar and the capture readers wrote for it, the sha256 of
`local.json`, and the time, which `local.json` records too. `local_receipt_problem` is what
`request --outside` and `verdict` hold the run to: every field of the receipt checked, the receipt present,
valid, naming exactly the local calls this run requested, every hash in it matching the file on disk now,
its time the one `local.json` records, and the record it covers still holding the way `record-local` holds
an answer. The run directory is the station's; a hand edit there is not prevented, it is detected, and the
run refuses.

The findings are the executor's merge (deduped on file:line and claim) and verification (the stamp:
CONFIRMED, PLAUSIBLE or REFUTED); the script refuses, exit 5 and nothing written: a CONFIRMED or
PLAUSIBLE finding whose file:line does not exist in the reviewed copy (the workspace the packet builder
cuts from the reviewed commit, `packet.Snapshot`; a packet-only staged name is read back to the path it
was staged from, C1A-6, else with `__` read as `/`), a REFUTED one with no reason, a severity or
confidence changed from what the reviewer stated with no reason, a finding credited to a call that is
not this phase's or did not come back `ok`, a text holding the line form's separator, and (local) a lens
credited with no finding that does not say what it tried to break.
"""
import os

from station_core import driver, fsio, validate
from back_core import trace

from . import common, forms, packet, report

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


def sidecar_path(run, call_id):
    return common.path_of(run, os.path.join("readers", call_id, "sidecar.json"))


def capture_path(run, call_id):
    return common.path_of(run, os.path.join("readers", call_id, "raw.md"))


def sidecar_of(run, call):
    path = sidecar_path(run, call["call_id"])
    if not os.path.isfile(path):
        return None, "%s has no sidecar at %s: record the call through readers first" % (call["call_id"], path)
    try:
        body = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        return None, "%s's sidecar cannot be read: %s" % (call["call_id"], exc)
    if not isinstance(body, dict):
        return None, "%s's sidecar is not a JSON object" % call["call_id"]
    if (body.get("call_id"), body.get("run_id"), body.get("row")) != (call["call_id"], run.checkpoint["run_id"], call["row"]):
        return None, "%s's sidecar names call %r, run %r, row %r" % (call["call_id"], body.get("call_id"),
                                                                    body.get("run_id"), body.get("row"))
    if body.get("status") == "ok":
        capture = capture_path(run, call["call_id"])
        if not body.get("raw_file") or os.path.realpath(body["raw_file"]) != os.path.realpath(capture):
            return None, "%s's sidecar names its capture at %r, not where readers writes it (%s)" % (
                call["call_id"], body.get("raw_file"), capture)
        if not os.path.isfile(capture) or fsio.sha256_file(capture) != body.get("raw_hash"):
            return None, "%s's capture %s does not match the raw_hash readers recorded" % (call["call_id"], capture)
    return body, None


def call_record(call, body):
    return {"call_id": call["call_id"], "row": call["row"], "lens": call.get("lens"), "status": body.get("status"),
            "model": body.get("effective_model"), "profile": body.get("profile"), "parity": body.get("parity"),
            "isolation": body.get("isolation"), "reason": body.get("reason"), "raw_file": body.get("raw_file"),
            "raw_hash": body.get("raw_hash")}


def resolve_location(tree, location, staged=None, packet_only=False):
    """(the location as it reads in the reviewed copy, or None when it names nothing there). `tree` is the
    workspace the packet builder cuts ({path: bytes}); `staged` maps each packet-only staged name to the
    path it was staged from; a finding only packet-only reviewers made names a staged file, so its staged
    name is read back first and only."""
    path, _, lines = location.rpartition(":")
    first = int(lines.split("-")[0])
    last = int(lines.split("-")[-1])
    candidates = [path, path.replace("__", "/")]
    if (staged or {}).get(path):
        candidates = [staged[path]] if packet_only else [path, staged[path], path.replace("__", "/")]
    for candidate in candidates:
        data = tree.get(candidate)
        if data is None:
            continue
        count = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
        if 1 <= first <= last <= count:
            return "%s:%s" % (candidate, lines)
        return None
    return None


def reviewed_copy(run):
    """({path: bytes} the reviewed workspace, {staged name: path}), from the reviewed commit only."""
    gate = common.read(run, "gate.json")
    snap = packet.Snapshot(common.workspace(run), gate["head"], gate["doc"])
    return snap.tree, dict((name, path) for path, name in snap.staged.items())


def check_findings(run, findings, calls_ok, side, packet_only=(), copy=None):
    """(the findings with their locations as they read in the copy, [refusal]). `packet_only`: the call ids
    whose reviewer read staged files, not a workspace."""
    tree, staged = copy if copy is not None else reviewed_copy(run)
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
            only_staged = bool(f["found_by"]) and all(c in packet_only for c in f["found_by"])
            found = resolve_location(tree, f["location"], staged, only_staged)
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


def evaluate_local(run, doc):
    """record-local's rule, applied to an answer (or to the record a completed record-local wrote):
    (records, findings, refusals, stop). `stop` is (tag, reason) when the local review cannot complete;
    `refusals` lists every way the answer does not hold."""
    requests = common.read(run, "requests-local.json")
    records, refusals = [], []
    for call in requests["calls"]:
        body, why = sidecar_of(run, call)
        if why:
            refusals.append(why)
        else:
            records.append(call_record(call, body))
    if refusals:
        return records, [], refusals, None
    last = {}
    for rec in records:
        last[rec["lens"]] = rec
    for lens, rec in last.items():
        if rec["status"] == "ok":
            continue
        if rec["status"] == "floor-refused":
            return records, [], [], ("floor-refused", "the local lens %s came back floor-refused (%s): this session is "
                                                      "below the floor; no verdict is emitted from below it"
                                     % (lens, rec["reason"] or "no reason given"))
        resent = lens in requests.get("resent", [])
        if rec["status"] in RETRYABLE and not resent:
            return records, [], ["the local lens %s came back %s: re-send it once first (request --resend %s "
                                 "--status %s), then record-local" % (lens, rec["status"], lens, rec["status"])], None
        return records, [], [], ("local-incomplete", "the local review is incomplete: the lens %s came back %s%s (%s); "
                                                     "the local review always completes or the run does not"
                                 % (lens, rec["status"], " after its re-send" if resent else "",
                                    rec["reason"] or "no reason given"))
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
    return records, findings, refusals, None


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
    records, findings, refusals, stop = evaluate_local(run, doc)
    if refusals:
        return _refuse(ctx, run, refusals)
    if stop:
        _summons_lines(ctx, run, requests, records)
        common.write(run, "local.json", {"calls": records, "findings": [], "tried": [], "method": None,
                                         "stopped": stop[0]})
        report.finish(ctx, run, "stopped", stop[0], stop[1])
    _summons_lines(ctx, run, requests, records)
    at = common.now()
    common.write(run, "local.json", {"calls": records, "findings": findings, "tried": doc["tried"],
                                     "method": doc["method"], "at": at})
    write_receipt(ctx, run, requests, at)
    common.advance(run, "recorded-local")
    named = common.read(run, "ask.json")["answer"]["rows"]
    return ctx.emit(ctx.envelope(next="request --outside" if named else "verdict", run_id=run.checkpoint["run_id"],
                                 findings=len(findings), calls=[{"call_id": r["call_id"], "status": r["status"]}
                                                                for r in records]))


RECEIPT = "local-receipt.json"


def _receipt_calls(run, requests):
    out = []
    for call in requests["calls"]:
        capture = capture_path(run, call["call_id"])
        out.append({"call_id": call["call_id"], "row": call["row"], "lens": call["lens"],
                    "sidecar_sha256": fsio.sha256_file(sidecar_path(run, call["call_id"])),
                    "capture_sha256": fsio.sha256_file(capture) if os.path.isfile(capture) else None})
    return out


def write_receipt(ctx, run, requests, at):
    """The local review's receipt, written by record-local alone, after local.json; its `at` is the time
    local.json records (C1A3-4), so the receipt's every field is checked against the run."""
    doc = {"receipt_version": 1, "run_id": run.checkpoint["run_id"], "calls": _receipt_calls(run, requests),
           "local_sha256": fsio.sha256_file(common.path_of(run, "local.json")), "at": at}
    errors = validate.errors_for(doc, common.schema("local-receipt.schema.json", ctx), ctx.prefix)
    if errors:
        raise driver.Defect("the receipt record-local would write does not validate: %s" % errors[:3])
    common.write(run, RECEIPT, doc)


def local_receipt_problem(ctx, run):
    """Why the local verdict is not on record as record-local wrote it, or None when it is (A4, class (b)):
    every field of the receipt checked (C1A3-4): present and valid against its closed schema (its version),
    for this run, naming exactly the local calls this run requested (id, row, lens, in order), every sidecar,
    capture and local.json hash in it matching the file on disk now, its time the time local.json records,
    and local.json still holding the way record-local holds an answer. `request --outside` and `verdict`
    both hold the run to it (C1A3-5)."""
    path = common.path_of(run, RECEIPT)
    if not os.path.isfile(path):
        return "the run holds no %s: record-local writes it when the local review completes" % RECEIPT
    try:
        receipt = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        return "%s cannot be read as JSON (%s)" % (RECEIPT, exc)
    errors = validate.errors_for(receipt, common.schema("local-receipt.schema.json", ctx), ctx.prefix)
    if errors:
        return "%s does not validate against references/local-receipt.schema.json: %s" % (
            RECEIPT, "; ".join("%s %s" % (e["path"], e["message"]) for e in errors[:3]))
    if receipt["run_id"] != run.checkpoint["run_id"]:
        return "%s is for run %r, not this run %r" % (RECEIPT, receipt["run_id"], run.checkpoint["run_id"])
    if not common.has(run, "requests-local.json"):
        return "the run holds no requests-local.json, so %s covers no requested call" % RECEIPT
    requests = common.read(run, "requests-local.json")
    if [(c["call_id"], c["row"], c["lens"]) for c in receipt["calls"]] != \
            [(c["call_id"], c["row"], c["lens"]) for c in requests["calls"]]:
        return "%s does not name exactly the local calls this run requested" % RECEIPT
    local_path = common.path_of(run, "local.json")
    if not os.path.isfile(local_path):
        return "local.json is gone, and %s says record-local wrote it" % RECEIPT
    if fsio.sha256_file(local_path) != receipt["local_sha256"]:
        return "local.json no longer matches the receipt record-local wrote (its sha256 differs)"
    for call in receipt["calls"]:
        side = sidecar_path(run, call["call_id"])
        if not os.path.isfile(side) or fsio.sha256_file(side) != call["sidecar_sha256"]:
            return "%s's sidecar no longer matches the receipt record-local wrote" % call["call_id"]
        capture = capture_path(run, call["call_id"])
        now = fsio.sha256_file(capture) if os.path.isfile(capture) else None
        if now != call["capture_sha256"]:
            return "%s's capture no longer matches the receipt record-local wrote" % call["call_id"]
    try:
        local = fsio.read_json(local_path)
    except (OSError, ValueError) as exc:
        return "local.json cannot be read (%s)" % exc
    if not isinstance(local, dict) or "stopped" in local:
        return "local.json records no completed local review"
    if local.get("at") != receipt["at"]:
        return "the receipt's time %s is not the time local.json records (%s)" % (receipt["at"], local.get("at"))
    answer = {"answer_version": 1, "kind": "local", "run_id": run.checkpoint["run_id"], "method": local.get("method"),
              "findings": local.get("findings"), "tried": local.get("tried")}
    errors = validate.errors_for(answer, common.schema("answer.schema.json", ctx), ctx.prefix)
    if errors:
        return "local.json does not hold a local record record-local would accept: %s" % "; ".join(
            "%s %s" % (e["path"], e["message"]) for e in errors[:3])
    records, findings, refusals, stop = evaluate_local(run, answer)
    if refusals or stop:
        return "local.json does not hold a local record record-local would accept: %s" % "; ".join(
            refusals or [stop[1]])
    if records != local.get("calls") or findings != local.get("findings"):
        return "local.json's calls or findings differ from what record-local derives from readers' sidecars"
    return None


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
    packet_only = set(r["call_id"] for r in records if r["profile"] == "packet-only")
    findings, refusals = check_findings(run, doc["findings"], ok_ids, "outside", packet_only)
    if refusals:
        return _refuse(ctx, run, refusals)
    _summons_lines(ctx, run, requests, records)
    common.write(run, "outside.json", {"calls": records, "findings": findings,
                                       "ledger_notes": doc.get("ledger_notes")})
    common.advance(run, "recorded-outside")
    return ctx.emit(ctx.envelope(next="verdict", run_id=run.checkpoint["run_id"], findings=len(findings),
                                 dropped=[{"row": r["row"], "status": r["status"], "reason": r["reason"]}
                                          for r in records if r["status"] != "ok"]))
