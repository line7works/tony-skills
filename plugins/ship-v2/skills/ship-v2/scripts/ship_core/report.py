"""The end of a run: a stop decided (`ending`), and `report`, the one result and v1's `SHIP:` block (contract sections
3.8, 8 and 9).

`ending(ctx, run, state, tag, reason, condition=None, by=None)` records a stop where it is decided (`ship.json`'s
`ending`) and moves the run to the stage `ending`, where nothing but `report` runs: no later visit, fix, lap or
pause can reach the trace or the records (CR-23). It prints the stop and `next` `report` (exit 0). What the command
staged before the stop (a trace line, `pauses.json`, `fixes.json`, `laps.json`, a receipt finished) lands in the same
save (`common.save`, THE SAVE).

`report --run-dir D --bottom-line TEXT [--skill-note TEXT]` runs at `clean` (ALL CLEAR), `exhausted` (stop condition
1: the extra lap spent without ALL CLEAR), `ending` (any other stop) and `visiting` (a visit that ended without a
result this run can take), and nowhere else: a paused run waits for its answer (exit 2), so a pause is never turned
into a stop. At `clean` and `exhausted` it is a check point of the window rule (`window.py`): what moved since the
last pin is held first (the doc moved is stop 2 and a path outside the footprint stop 4, reported as the run's end; a
path inside it nothing names is refused, exit 5). At `visiting` the station's result is read as `visit --result` reads
it, writing nothing (`visit.judge`): one it would take is refused here (exit 2: run `visit --result` first); one it
would refuse, or none, ends the run `visit-unfinished`, saying which (slice 2 re-check 1's R1S2-5). It reads the slice's card from the doc as it stands (read
twice, CR-27), the findings the records hold open (the `Remains` lines; a report-only run's planned grants are not
in the records), the fixes this run recorded (the `Fixed` lines) and the trace, renders the `SHIP:` block
(`forms.render`) into `chat.md`, assembles `result.json`, validates it against `references/result.schema.json` and
the semantic checks S1 to S4, and ends the run (exit 10): `chat.md`, the state, `result.json` and the stage `done` land
in one save (`common.save`, THE SAVE), the result's `writes` listing the bytes that save writes. A result that fails
either check is a defect of this script (exit 1), never a softened result.
"""
import os

from station_core import driver, fsio, records_link, validate
from back_core import trace

from . import common, doc as docmod, forms, record, window

CONDITION_TAGS = {1: "extra-lap-exhausted", 2: "spec-change", 3: "build-not-complete", 4: "outside-footprint"}


def ending(ctx, run, state, tag, reason, condition=None, by=None):
    state = dict(state)
    state.setdefault("visits", [])
    state["ending"] = {"status": "stopped", "tag": tag, "reason": reason, "condition": condition, "by": by}
    state["visit"] = None
    common.save(run, state, "ending")
    return ctx.emit(ctx.envelope(next="report", run_id=common.run_id(run), stop_tag=tag, reason=reason,
                                 condition=condition))


def _card(run, state):
    """The slice's `Status:` line as the doc holds it now, read twice; or why it cannot be read."""
    try:
        parsed = docmod.read(common.read_doc_bytes(common.workspace(run), state["doc"]).decode("utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return None, "the doc cannot be read now (%s)" % exc
    except docmod.DocUnreadable as exc:
        return None, "the doc cannot be read cleanly now at line %d" % exc.line
    row = docmod.slice_of(parsed, state["slice"])
    if row is None:
        return None, "the doc holds no slice %s now" % state["slice"]
    return row["status"], None


def _remains(run, state, records_root):
    """Every finding the records hold open: this slice's, and other slices' (raised by a sweep, never this run's
    to fix), each with what is still needed."""
    if not state.get("doc"):
        return []
    try:
        rows = record.open_findings(run, None, records_root)
    except records_link.RecordsRefusal as exc:     # named, never hidden: the run is over either way
        return [{"finding": "the records could not be read at report", "severity": "-",
                 "needed": " ".join(exc.sentence().split())[:300].replace(forms.M, ",") or "the component refused",
                 "id": None, "slice": None}]
    out = []
    for row in rows:
        severity = row.get("severity") or "-"
        name = row.get("slice") or "none"
        if name == state.get("slice"):
            needed = ("fix it and run %s" % forms.summon("recheck-v2", name, state["doc"])
                      if severity in common.BLOCKING else "a MINOR, never gates; fixed when the owner orders it")
        else:
            needed = "charged to slice %s, not this run's to fix: %s" % (name, forms.summon("recheck-v2", name,
                                                                                         state["doc"]))
        claim = (row.get("claim") or (row.get("location") or {}).get("raw") or row.get("id")).replace(forms.M, ",")
        out.append({"finding": claim, "severity": severity, "needed": needed, "id": row.get("id"), "slice": name})
    return out


def _fixed(run, state):
    out = []
    for lap in common.listing(run, "fixes.json", "laps"):
        if lap.get("outcome") != "recorded":
            continue
        for fix in lap["fixes"]:
            named = next((n for n in lap["named"] if n["id"] == fix["finding"]), {})
            out.append({"finding": (named.get("claim") or fix["finding"]).replace(forms.M, ","),
                        "location": (named.get("location") or ", ".join(fix["paths"]) or "-").replace(forms.M, ","),
                        "line": fix["summary"].replace(forms.M, ","), "id": fix["finding"], "lap": lap["lap"]})
    return out


def _writes(run):
    """The run's own files as they stand once this report's save lands (the staged bytes over the bytes on disk), and
    the records log and the build doc each grant reached."""
    staged = common.staged_bytes(run)
    names = set(n for n in os.listdir(run.run_dir) if os.path.isfile(os.path.join(run.run_dir, n))
                and not os.path.islink(os.path.join(run.run_dir, n))) | set(staged)
    out = []
    for name in sorted(names):
        if name in (common.CHECKPOINT, "result.json", common.JOURNAL) or name.endswith(common.TEMP):
            continue
        path = os.path.join(run.run_dir, name)
        after = fsio.sha256_bytes(staged[name]) if name in staged else fsio.sha256_file(path)
        out.append({"path": path, "kind": "run_artifact", "sha256_before": None, "sha256_after": after})
    for row in common.listing(run, "events.json", "grants"):
        if row.get("log"):
            out.append({"path": row["log"]["path"], "kind": "records_log", "sha256_before": row["log"]["sha256_before"],
                        "sha256_after": row["log"]["sha256_after"]})
        if row.get("doc"):
            out.append({"path": row["doc"]["path"], "kind": "build_doc", "sha256_before": row["doc"]["sha256_before"],
                        "sha256_after": row["doc"]["sha256_after"]})
    return out


def build_result(ctx, run, status, tag, reason, state, chat, fields):
    lines = trace.read(run.run_dir)
    writes = _writes(run)
    outside = [w for w in writes if not validate._under(w["path"], run.run_dir)]
    laps = common.listing(run, "laps.json", "laps")
    station_result = {
        "doc": state.get("doc"), "slice": state.get("slice"), "hook": state.get("hook"),
        "result_line": fields["result"], "condition": (state.get("ending") or {}).get("condition"),
        "build": fields["build"], "signoff": fields["signoff"], "recheck": fields["recheck"], "card": fields["card"],
        "laps": {"taken": fields["laps"], "allowed": common.laps_allowed(run),
                 "owner_words": (common.station(run).get("extra_laps") or {}).get("words"),
                 "opened": [{"lap": l["lap"], "owner_words": l.get("owner_words")} for l in laps]},
        "visits": [{"station": v["station"], "status": v["status"], "word": v["word"], "run_dir": v["run_dir"],
                    "lap": v["lap"]} for v in state.get("visits") or []],
        "fixed": fields["fixed"], "remains": fields["remains"],
        "pauses": [{"pause": p["pause"], "source": p["question"]["source"], "station": p["question"].get("station"),
                    "question": p["question"]["text"], "answered": p.get("answer") is not None,
                    "words": (p.get("answer") or {}).get("words")} for p in common.listing(run, "pauses.json",
                                                                                           "pauses")],
        "events": [{"kind": g["kind"], "finding": g["finding"], "words": g["words"], "appended": bool(g["appended"]),
                    "card": g.get("card")} for g in common.listing(run, "events.json", "grants")],
        "chat": chat}
    return ctx.envelope(run_id=common.run_id(run), run_dir=run.run_dir, status=status, stop_tag=tag, reason=reason,
                        report_only=common.report_only(run), wrote_nothing=not outside, writes=writes,
                        invocation=dict(run.input.get("invocation") or {}),
                        trace={"path": trace.path_of(run.run_dir), "lines": len(lines),
                               "visits": len([l for l in lines if l["kind"] == "visit" and l["status"] != "visiting"]),
                               "refused": len([l for l in lines if l["kind"] == "refused"])},
                        station_result=station_result)


def check(ctx, result):
    errors = validate.errors_for(result, validate.load_schema("result", ctx.prefix, ctx.skill_root), ctx.prefix)
    semantic = validate.semantic(result) if not errors else []
    if errors or semantic:
        raise driver.Defect("the result this run would write does not hold (a defect of the script): %s"
                            % "; ".join("%s %s" % (e.get("path"), e.get("message")) for e in (errors or semantic)[:4]))


def _unfinished(run, state, prefix):
    """`report` at `visiting` (slice 2 check 1's C2-6, re-check 1's R1S2-5): the station ended without a result
    `visit --result` takes, so the run ends `visit-unfinished`, the visit's opening trace line left as the record that
    it was handed over; a result standing that `visit --result` would take is refused here, exit 2."""
    from . import visit as visitmod
    visit = state.get("visit") or {}
    name = visit.get("station") or "the station"
    verdict, detail = visitmod.judge(run, state, prefix)
    if verdict == "take":
        raise driver.Usage("%s's result in %s stands and `visit --result` takes it: run `visit --result` first (the "
                           "run ends `visit-unfinished` only when the station left no result this run can take)"
                           % (name, visit.get("run_dir")))
    if verdict == "missing":
        why = "it left no result in %s" % (visit.get("run_dir") or "its run directory")
    elif verdict == "refuse":
        why = "`visit --result` refuses the result it left: %s" % detail
    else:
        why = "`visit --result` refuses the station at its result: %s" % detail[3]
    state = dict(state, visit=None)
    state["ending"] = {"status": "stopped", "tag": "visit-unfinished", "condition": None, "by": name,
                       "reason": "the visit to %s ended without a result this run can take: %s (no result holds, so "
                                 "the run ends here; the trace's opening line for the visit is the record that it "
                                 "was handed over)" % (name, why)}
    return state


def _laps_taken(state):
    """Fix-and-recheck laps taken: a lap counts once its recheck visit closed (a minors-only fix has no recheck)."""
    return len(set(v["lap"] for v in state.get("visits") or [] if v["station"] == "recheck-v2"))


def handler(ctx, args):
    """`report --run-dir D --bottom-line TEXT [--skill-note TEXT]`."""
    run = common.open_run(ctx, args.run_dir, ("clean", "exhausted", "ending", "visiting"), "report")
    if not args.bottom_line or not args.bottom_line.strip() or "\n" in args.bottom_line:
        raise driver.Usage("report needs --bottom-line: two or three sentences on one line (what shipped, what state "
                           "it is in, what to do next)")
    if args.skill_note is not None and (not args.skill_note.strip() or "\n" in args.skill_note):
        raise driver.Usage("--skill-note is one line, given only when a rule was worked around, reinterpreted or "
                           "excepted")
    state = common.state(run)
    stage = run.checkpoint["phase"]
    if stage == "visiting":
        state = _unfinished(run, state, ctx.prefix)
        stage = "ending"
    if stage in ("clean", "exhausted"):
        held = window.hold(run, state, "after the last station's result and before the report")
        if held.refuse is not None:
            return common.refuse(ctx, run, held.refuse)
        if held.stop is not None:
            state["ending"] = {"status": "stopped", "tag": held.stop[0], "reason": held.stop[1],
                               "condition": held.stop[2], "by": None}
            stage = "ending"
    if stage == "clean":
        status, tag, reason, result = "completed", None, "ALL CLEAR: the loop ended by its own rules", "ALL CLEAR"
    elif stage == "exhausted":
        state["ending"] = {"status": "stopped", "tag": CONDITION_TAGS[1], "condition": 1, "by": None,
                           "reason": "the extra lap is exhausted without ALL CLEAR (stop condition 1)"}
        status, tag, reason, result = "stopped", CONDITION_TAGS[1], state["ending"]["reason"], forms.result_line(1)
    else:
        end = state["ending"]
        status, tag, reason = "stopped", end["tag"], end["reason"]
        if end.get("condition"):
            result = forms.result_line(end["condition"])
        else:
            result = "STOPPED (%s: %s)" % (end.get("by") or tag, tag)
    card, unread = _card(run, state) if state.get("doc") and state.get("slice") else (None, "no slice was selected")
    reached = [v["station"] for v in state.get("visits") or []]
    fields = {"slice": state.get("slice") or "none", "doc": state.get("doc") or "none",
              "hook": (state.get("hook") or {}).get("label") or "not recorded",
              "result": result, "build": state.get("build") or "not reached",
              "signoff": state.get("signoff") or "not reached",
              "recheck": state.get("recheck") or ("not run" if "signoff-v2" in reached and
                                                  run.checkpoint["phase"] == "clean" else "not reached"),
              "card": card or "unread (%s)" % unread, "laps": _laps_taken(state),
              "bottom_line": args.bottom_line.strip(), "fixed": _fixed(run, state),
              "remains": _remains(run, state, args.records_root), "skill_note": args.skill_note}
    try:
        chat = forms.render(fields)
    except forms.FormError as exc:
        raise driver.Usage("the SHIP: block cannot carry a value given: %s" % exc)
    common.stage_text(run, "chat.md", chat)
    common.stage(run, common.STATE, state)
    result_doc = build_result(ctx, run, status, tag, reason, state, chat, fields)
    check(ctx, result_doc)
    common.stage(run, "result.json", result_doc)
    common.save(run, stage="done")
    raise driver.Terminal(dict(result_doc, next="done"))
