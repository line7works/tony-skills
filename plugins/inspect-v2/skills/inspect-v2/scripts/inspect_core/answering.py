"""`record-answer`: the executor's one recorded answer, checked in three layers (contract section 7).

1. The schema, `references/answer.schema.json`: exit 4, the findings on stdout, nothing written.
2. The shared E14-11 refusals, through `station_core.answer.check` (one implementation for the four
   cores): a question that re-asks a decided ledger line, an asserted line with no trace. Exit 5.
3. This core's own content rules, in the same `{"rule", "message", ...}` shape, exit 5:

   run-mismatch          the answer names another run
   session-mismatch      the answer's session is not the input's `invocation.session_id`
   row-mismatch          the answer's row is not the input's `station.row`, or a result's row is not
                         the row its request was built for
   owner-word-mismatch   an owner word on a Claude row, or one that differs from the input's
   independence          a result whose findings carry no reader call id, or a call id this run's
                         `request` never built (the session that drafted the plan never originates
                         a finding)
   duplicate-call        two results for one call
   lanes-mismatch        `lanes` is not the set of lenses of the calls this run's `request` BUILT
                         (round 5, R2: never compared with the results, so a short fleet cannot
                         declare itself whole by listing fewer lenses)
   field-separator       a claim, scenario, location or effective model the records line or the
                         stamp cannot carry (a line break, the ` · ` separator, a space in a model)
   unknown-finding       an adjudication names no finding of the results, or names one twice
   refuted-citation      an adjudication keeps (confirmed, plausible) a finding whose citation
                         matches nothing in the packet
   missing-adjudication  a verified finding (every outside finding, every Claude-lane BLOCKER and
                         MAJOR) whose citation holds carries no adjudication of the executor's
                         (round 5, R1: a matching citation shows only that the cited text exists;
                         the executor judges the claim, the script never does)
   ledger-incomplete     `harvest` refused a scope-doc row (`ledger.refused`) and the answer carries a
                         question or an asserted line (round 5, R4: an incomplete ledger is not an
                         empty one, so the shared E14-11 guard cannot vouch for either); a
                         findings-only answer, both arrays empty, is still recorded
   unauthorized-send     a status-ok result of an outside row's paper call whose request was built
                         without `authorized` (no owner word in this run's input names the row):
                         readers sends no such call, so nothing of it is raised or stamped

Only then is `answer.json` written, by `station_core.answer.record`; then, before anything is
triaged, the banner goes on each outside raw copy (`writing.banner_raw_copies`, `banner.json`; never in
report-only), and the mechanical triage (`verify.triage`) follows. A refusal at layer 2 or 3 (exit 5)
records nothing, and still puts the banner on each outside raw copy (the owner's ruling C4), so an
executor who abandons the run after a refusal leaves no bare copy; `banner.json` is written only when
a copy got the banner, and a later accepted answer keeps those writes in it. Two outcomes end the run instead of
refusing the answer: a short fleet, that is a call `request` built with no result, or a result whose
status is not `ok` (stop `lane-down`, naming the missing call ids and the down calls: nothing is
triaged, raised or stamped, the ask is re-asked; round 5, R2), and a result with no effective model,
or paper calls that report two (stop `no-effective-model`: no stamp). A run that ends in either stop
is not held to `missing-adjudication`: nothing of it is triaged.
"""
import os

from station_core import answer as sharedanswer
from station_core import driver, validate

from . import common, reporting, verify, writing

SEP = " · "


def _refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


def _bad_field(value):
    return isinstance(value, str) and ("\n" in value or "\r" in value or SEP in value)


def missing_calls(doc, requests):
    """The call ids `request` built that no result answers (round 5, R2), in the order built."""
    answered = set(r["call_id"] for r in doc["results"])
    return [c["call_id"] for c in requests["calls"] if c["call_id"] not in answered]


def stops(doc, requests):
    """Whether the recorded answer ends the run in a stop (`lane-down` or `no-effective-model`)."""
    if missing_calls(doc, requests) or [r for r in doc["results"] if r.get("status", "ok") != "ok"]:
        return True
    if [r for r in doc["results"] if r["effective_model"] is None]:
        return True
    return len(verify.paper_models(doc, requests)) != 1


def own_checks(doc, run, requests, packet, harvest):
    out = []
    st = common.station(run)
    if doc["run_id"] != run.input["run_id"]:
        out.append(_refusal("run-mismatch", "the answer names the run %r; this run is %r" % (doc["run_id"], run.input["run_id"])))
    session = (run.input.get("invocation") or {}).get("session_id")
    if doc["session_id"] != session:
        out.append(_refusal("session-mismatch", "the answer's session %r is not this run's executor session %r "
                                                "(invocation.session_id, read by the adapter)" % (doc["session_id"], session)))
    if doc["row"] != st.get("row"):
        out.append(_refusal("row-mismatch", "the answer names the row %r; the owner named %r for this run"
                                            % (doc["row"], st.get("row"))))
    if "owner_word" in doc:
        if packet["provider"] == common.ANTHROPIC:
            out.append(_refusal("owner-word-mismatch", "an owner word rides only with an outside row; %r is a Claude row"
                                                       % doc["row"]))
        elif doc["owner_word"] != run.input.get("owner_word"):
            out.append(_refusal("owner-word-mismatch", "the answer's owner word is not the one this run's input carried"))
    built = dict((c["call_id"], c) for c in requests["calls"])
    seen = set()
    for index, result in enumerate(doc["results"]):
        call_id = result["call_id"]
        if call_id is None:
            out.append(_refusal("independence", "result %d carries no reader call id: a finding with no reader call "
                                                "id has no reader, and the session never originates one" % (index + 1),
                                result=index + 1))
            continue
        if call_id not in built:
            out.append(_refusal("independence", "result %d names the call %r, which this run's `request` never built "
                                                "(its calls: %s)" % (index + 1, call_id, ", ".join(sorted(built))),
                                result=index + 1, call_id=call_id))
            continue
        if call_id in seen:
            out.append(_refusal("duplicate-call", "two results name the call %r" % call_id, call_id=call_id))
            continue
        seen.add(call_id)
        if result["row"] != built[call_id]["row"]:
            out.append(_refusal("row-mismatch", "the result of %s names the row %r; its request was built for %r"
                                                % (call_id, result["row"], built[call_id]["row"]), call_id=call_id))
        if built[call_id]["lens"] == "paper" and not built[call_id]["authorized"] and \
                result.get("status", "ok") == "ok":
            out.append(_refusal("unauthorized-send", "the result of %s comes from the outside row %r, whose request "
                                                     "this run built without `authorized`: the input's owner word "
                                                     "names no such row, readers sends no such call, and nothing is "
                                                     "raised or stamped under that row's name"
                                                     % (call_id, built[call_id]["row"]),
                                call_id=call_id, row=built[call_id]["row"]))
        model = result.get("effective_model")
        if isinstance(model, str) and (_bad_field(model) or len(model.split()) != 1 or "·" in model):
            out.append(_refusal("field-separator", "the effective model %r of %s cannot be written into a stamp or a "
                                                   "records line" % (model, call_id), call_id=call_id))
        for number, f in enumerate(result["findings"], 1):
            for field in ("claim", "scenario", "location"):
                if _bad_field(f.get(field)):
                    out.append(_refusal("field-separator", "the %s of %s#%d holds a line break or the %r separator, "
                                                           "which a records line cannot carry" % (field, call_id, number, SEP),
                                        finding="%s#%d" % (call_id, number)))
    built_lenses = set(c["lens"] for c in requests["calls"])
    if not [r for r in out if r["rule"] == "independence"] and not missing_calls(doc, requests) and \
            set(doc["lanes"]) != built_lenses:
        # round 5, R2: compared with the lenses this run's request BUILT, never with the results; a
        # fleet with a missing call is not refused here, it ends the run lane-down after recording
        out.append(_refusal("lanes-mismatch", "`lanes` says %s; this run's `request` built calls for %s"
                                              % (", ".join(sorted(doc["lanes"])), ", ".join(sorted(built_lenses)))))
    findings = {}
    for result in doc["results"]:
        if result["call_id"] in built:
            for number, f in enumerate(result["findings"], 1):
                findings["%s#%d" % (result["call_id"], number)] = (result, f)
    named = set()
    lens_dir = dict((d["lens"], d["dir"]) for d in packet["dirs"])
    for adj in doc.get("adjudications") or []:
        fid = adj["finding"]
        if fid not in findings or fid in named:
            out.append(_refusal("unknown-finding", "the adjudication of %r names %s" % (
                fid, "no finding of the results" if fid not in findings else "a finding already adjudicated"),
                finding=fid))
            continue
        named.add(fid)
        result, f = findings[fid]
        if adj["decision"] in ("confirmed", "plausible") and f.get("location") is not None:
            lens = built[result["call_id"]]["lens"]
            ok, why, _ = verify.check_citation(f, lens_dir.get(lens), lens, common.workspace(run),
                                               verify.carried(built[result["call_id"]]))
            if not ok:
                out.append(_refusal("refuted-citation", "the adjudication keeps %s, but its citation matches nothing "
                                                        "in the packet: %s" % (fid, why), finding=fid))
    if not [r for r in out if r["rule"] in ("independence", "duplicate-call")] and not stops(doc, requests):
        for row in verify.unadjudicated(doc, requests, harvest, packet, common.workspace(run)):
            out.append(_refusal(
                "missing-adjudication",
                "%s (%s %s at %s) carries no adjudication: a citation that holds shows only that the cited "
                "text exists, never that the claim is true. The executor reads the cited lines and records "
                "`confirmed`, `plausible`, `refuted` or `question` with its why before the finding can survive"
                % (row["finding"], "outside" if row["outside"] else "Claude-lane", row["severity"], row["location"]),
                finding=row["finding"], call_id=row["call_id"]))
    refused_rows = harvest["ledger"].get("refused") or []
    if refused_rows and (doc["questions"] or doc["lines"]):
        out.append(_refusal(
            "ledger-incomplete",
            "the scope doc's ledger is incomplete: harvest refused %d row(s) (%s), so the decided-line guard "
            "cannot vouch for this answer's %s. An incomplete ledger is not an empty one: record the findings "
            "with no question and no line, or fix the scope doc's rows and run again"
            % (len(refused_rows), "; ".join("line %s: %s" % (r.get("line"), r.get("raw")) for r in refused_rows),
               " and ".join(w for w, n in (("questions", doc["questions"]), ("lines", doc["lines"])) if n)),
            refused=[r.get("line") for r in refused_rows]))
    return out


def _banner(run, always=False):
    """The banner on each outside raw copy, its writes added to `banner.json` after any an earlier refused
    answer of this run made there (the banner is idempotent, so a copy is named once). The file is written
    when a copy got the banner now, or when `always` (the accepted path, as before). Returns this call's
    writes."""
    fresh = writing.banner_raw_copies(run)
    earlier = list(common.read(run, "banner.json")["writes"]) if common.has(run, "banner.json") else []
    if fresh or always:
        common.write(run, "banner.json", {"writes": earlier + fresh})
    return fresh


def handler(ctx, args):
    """`record-answer --run-dir D --answer FILE`."""
    run = common.open_run(ctx, args.run_dir, ("requested",), "record-answer")
    doc = common.load_json_file(args.answer, "answer")
    errors = validate.errors_for(doc, common.schema("answer.schema.json", ctx), ctx.prefix)
    if errors:
        return ctx.emit(ctx.envelope(ok=False, error="invalid", accepted=False,
                                     reason="the answer does not validate against references/answer.schema.json: "
                                            "%d finding(s); nothing was written" % len(errors), errors=errors), 4)
    harvest = common.read(run, "harvest.json")
    requests = common.read(run, "requests.json")
    packet = common.read(run, "packet.json")
    ledger_lines = harvest["ledger"]["lines"]
    shared = sharedanswer.check(doc, ledger_lines, workspace=common.workspace(run), allowed=sharedanswer.DEFAULT_TRACES)
    refusals = list(shared["refusals"]) + own_checks(doc, run, requests, packet, harvest)
    if refusals:
        # the owner's ruling C4: a content refusal leaves no outside raw copy bare either
        banners = _banner(run) if not common.report_only(run) else []
        if banners:
            reason = ("the recorded answer was refused on its content (%d refusal(s)); the answer was not recorded, "
                      "and the one write was the banner on %d outside raw copy(ies), so none is left bare"
                      % (len(refusals), len(banners)))
        else:
            reason = "the recorded answer was refused on its content (%d refusal(s)); nothing was written" % len(refusals)
        return ctx.emit(ctx.envelope(accepted=False, run_id=run.input["run_id"], refusals=refusals,
                                     reason=reason), 5)
    code, report = sharedanswer.record(run.run_dir, doc, ledger_lines, workspace=common.workspace(run),
                                       allowed=sharedanswer.DEFAULT_TRACES)
    if code != 0:
        raise driver.Defect("the shared check refused an answer it had accepted: %s" % report)
    if not common.report_only(run):
        # v1 Step 3: the raw copy carries its banner before anything is triaged, on every run, a stop included
        _banner(run, always=True)
    down = [r for r in doc["results"] if r.get("status", "ok") != "ok"]
    absent = missing_calls(doc, requests)
    if down or absent:
        what = ["%s answered %s (%s)" % (r["call_id"], r["status"], r.get("reason") or "no reason given")
                for r in down]
        if absent:
            what.append("no result for %s, which this run's `request` built (a recorded fleet holds one result "
                        "for every call built)" % ", ".join(absent))
        reporting.finish(ctx, run, "stopped", "lane-down", "the lane cannot run: %s. Nothing from this lane is "
                         "triaged, raised or stamped (a fleet with one failed or missing lens is not a plan check); "
                         "re-ask the owner, and the lane he names runs as a fresh run with a fresh run id"
                         % "; ".join(what))
    missing = [r["call_id"] for r in doc["results"] if r["effective_model"] is None]
    if missing:
        reporting.finish(ctx, run, "stopped", "no-effective-model",
                         "the result of %s carries no effective model, so no stamp can name the model that inspected; "
                         "nothing is raised and no stamp is written" % ", ".join(missing))
    models = verify.paper_models(doc, requests)
    if len(models) != 1:
        reporting.finish(ctx, run, "stopped", "no-effective-model",
                         "the paper calls report %s, not one effective model the stamp can name; nothing is raised "
                         "and no stamp is written" % (", ".join(models) if models else "no result"))
    triage = verify.triage(doc, requests, harvest, packet, common.workspace(run))
    triage["stamp_model"] = models[0]
    common.write(run, "triage.json", triage)
    run.checkpoint["phase"] = "answered"
    run.save()
    return ctx.emit(ctx.envelope(next="write", run_id=run.input["run_id"], accepted=True, answer=report["answer"],
                                 counts=triage["counts"], verdict=triage["verdict"], stamp_model=models[0],
                                 refuted=triage["refuted"], questions=triage["questions"],
                                 lenses_not_run=triage["lenses_not_run"]))
