"""`visit` (CR-21, ruling E15-7; contract section 3.4): one station visit, traced before and after.

`visit --station NAME`: the station is the one the loop's order names (build-v2 after the hook, signoff-v2 after a
COMPLETE build, recheck-v2 after a lap's fixes; any other name is exit 2: compose by name, never skip or reorder a
station). It is resolved by allowlist identity and its `skill-identity` read through its own CLI BEFORE the visit
(`stations.py`). A station that is not the expected v2 sibling is refused: a `refused` trace line, and the run ends
(`station-refused`), no visit handed over. Otherwise the opening trace line (`visit`, status `visiting`: the station,
its identity, the route, the visit's run directory) is written, and only then is the visit handed to the executor:
the station's `SKILL.md` to run by, the summon line, the run id and run directory the visit uses (`visits/<seq>-<name>`
under this run's directory, which the station's own `check-input` creates), and the caller fields (`ship-v2`,
`station`). Before anything of the station is read, the window since the last step is held, and when the opening line
is written the workspace is pinned (the window rule, `window.py`).

`visit --result`: the station's own result file, `<visit run dir>/result.json`, read after the executor ran the
station by its own `SKILL.md`. Before it is read, the station is resolved and identified again: one that changed
since the visit opened is refused (a `refused` line, `station-refused`). The file must be a regular file in the
visit's run directory; it must validate against that station's own result schema, name this visit's run id and run
directory, this run's slice, doc and workspace where it carries them, and the version of the station visited; on a
report-only run it must be a report-only result that wrote nothing. Anything else is a v1 result file, or not this
visit's: refused, exit 5, nothing written, the run still at the visit. Then the window the visit was open in is held,
net of the station's own listed writes and ship-v2's own (`window.py`): a path inside the footprint nothing names is
refused there, exit 5. A result that holds is recorded with its terminal status on the closing trace line (`visit`,
the station's status); the window's stop (2 or 4), if any, ends the run after it; otherwise the workspace is pinned
again and the loop's next step is decided from the station's own words and the records (contract section 3.4's
table): stop 3 on a build that is not COMPLETE; the run's end on a signoff-v2 or recheck-v2 stop or refusal; the
fixes, ALL CLEAR, a lap or the extra lap exhausted. `judge` is the same reading without a write, for `report` at
`visiting` (slice 2 re-check 1's R1S2-5).
"""
import os
import stat

from station_core import driver, fsio, records_link
from station_core.records_client import ComponentUnavailable
from back_core import trace

from . import common, forms, record, report, stations, window

EXPECT = {"hooked": "build-v2", "built": "signoff-v2", "fixed": "recheck-v2"}
# the window a visit's opening holds, by the stage it opens at (the window rule's words)
BETWEEN = {"built": "between build-v2's result and signoff-v2's visit",
           "fixed": "after the lap's fixes were recorded and before recheck-v2's visit"}
# the `invocation.mode` each station's own input schema takes from a calling station (slice 2 check 1's C2-8):
# build-v2's `station`; signoff-v2 and recheck-v2 take `interactive` or `headless`, and recheck-v2 takes only
# `headless` from a caller other than `direct`
MODES = {"build-v2": "station", "signoff-v2": "headless", "recheck-v2": "headless"}


def _trace_ready(run):
    why = common.irregular(run, trace.path_of(run.run_dir))
    if why is not None:
        raise driver.Defect("the run's trace %s: the run directory has been changed by hand, and the run refuses" % why)


def _append(ctx, run, line):
    _trace_ready(run)
    return trace.append(run.run_dir, line, ctx.skill_root, ctx.prefix)


def _refused(ctx, run, state, name, identity, route, run_dir, rules, reason):
    route = route if route in trace.ROUTES else None
    line = trace.line(kind="refused", caller=common.STATION, expected=name, identity=identity, route=route,
                      run_dir=run_dir, refusal={"rules": sorted(set(rules)), "reason": reason}, at=common.now())
    _append(ctx, run, line)
    return report.ending(ctx, run, state, "station-refused", "%s was refused before the visit: %s; nothing of it ran "
                                                             "but its own skill-identity, and no later visit follows"
                         % (name, reason))


def _resolve(ctx, run, state, name, run_dir):
    """(found, identity) for a station that holds, or (None, the emitted ending) for one refused."""
    try:
        found = stations.resolve(name)
    except stations.RootRefused as exc:
        return None, _refused(ctx, run, state, name, None, exc.route, run_dir, [exc.rule], str(exc))
    except LookupError as exc:
        raise ComponentUnavailable("missing dependency: %s" % exc)
    identity = stations.identify(name, found)
    problems = stations.refusals(name, identity, found)
    if problems:
        return None, _refused(ctx, run, state, name, identity, found["route"], run_dir,
                              [p["rule"] for p in problems], "; ".join(p["message"] for p in problems))
    return (found, identity), None


def open_visit(ctx, run, args):
    stage = run.checkpoint.get("phase")
    expected = EXPECT[stage]
    if args.station != expected:
        raise driver.Usage("compose by name, never skip or reorder a station: this run's next station is %s, not %r; "
                           "run `visit --station %s`" % (expected, args.station, expected))
    state = common.state(run)
    _trace_ready(run)
    seq = len(trace.read(run.run_dir))
    run_dir = os.path.join(run.run_dir, "visits", "%d-%s" % (seq, expected))
    run_id = "%s-%d-%s" % (common.run_id(run), seq, expected)
    if os.path.lexists(run_dir):
        raise driver.Defect("the visit's run directory %s already exists: the run directory has been changed by hand"
                            % run_dir)
    between = window.hold(run, state, BETWEEN.get(stage, "before %s's visit" % expected))
    if between.stop is not None:
        return report.ending(ctx, run, state, between.stop[0], between.stop[1], condition=between.stop[2])
    if between.refuse is not None:
        return common.refuse(ctx, run, between.refuse)
    held, ended = _resolve(ctx, run, state, expected, run_dir)
    if held is None:
        return ended
    found, identity = held
    skill_md, why = _skill_md(found, expected)
    if why is not None:
        return _refused(ctx, run, state, expected, identity, found["route"], run_dir, [why[0]], why[1])
    line = trace.line(kind="visit", caller=common.STATION, expected=expected, identity=identity, route=found["route"],
                      run_dir=run_dir, status="visiting", at=common.now())
    written = _append(ctx, run, line)
    os.makedirs(os.path.join(run.run_dir, "visits"), exist_ok=True)
    state["visit"] = {"station": expected, "seq": written["seq"], "run_id": run_id, "run_dir": run_dir,
                      "identity": identity, "route": found["route"], "root": found["root"], "skill_md": skill_md}
    window.take(run, state)                 # what the workspace holds when the visit opens
    common.save(run, state)
    common.advance(run, "visiting")
    return ctx.emit(ctx.envelope(
        next="visit --result", run_id=common.run_id(run), visited=expected, identity=identity, route=found["route"],
        root=found["root"], skill_md=skill_md, summon=forms.summon(expected, state["slice"], state["doc"]),
        visit_run_id=run_id, visit_run_dir=run_dir, caller=common.STATION, mode=MODES[expected],
        report_only=common.report_only(run), workspace=common.workspace(run), doc=state["doc"], slice=state["slice"],
        trace_seq=written["seq"],
        how=("run %s by its own SKILL.md (%s), with run_id %s and run_dir %s in its input, invocation.caller %s and "
             "invocation.mode %s (the mode %s's own input schema takes from a calling station); a question it puts "
             "to the owner is a pause (`pause --question`); when it has written its result, run `visit --result` "
             "(a station that ends without a result it can give: `report`, which ends the run visit-unfinished)"
             % (expected, skill_md, run_id, run_dir, common.STATION, MODES[expected], expected))))


def _skill_md(found, name):
    """(path, None) for the station's `SKILL.md` when it resolves inside the station root by identity and is a regular
    file; (None, (rule, reason)) otherwise (slice 2 check 1's C2-5: every file of the root ship-v2 hands over or runs
    resolves inside it)."""
    relative = os.path.join("skills", name, "SKILL.md")
    try:
        path = stations.inside(found["root"], relative, found["route"])
    except stations.RootRefused as exc:
        return None, (exc.rule, "the SKILL.md it would hand over is not the station's own: %s" % exc)
    try:
        regular = stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        regular = False
    if not regular:
        return None, ("no-identity", "the station root %s holds no SKILL.md as a regular file at %s (a link, a folder "
                                     "or nothing), so there is no rulebook of its own to hand over" % (found["root"],
                                                                                                       relative))
    return path, None


def _result_file(run, visit):
    folder = visit["run_dir"]
    path = os.path.join(folder, "result.json")
    try:
        mode = os.lstat(folder).st_mode
    except FileNotFoundError:
        return None, None
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode) or not fsio.inside(folder, run.run_dir):
        return None, "the visit's run directory %s is not a real folder inside this run's directory" % folder
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return None, None
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or not fsio.inside(path, folder):
        return None, "the station's result %s is not a regular file in the visit's run directory" % path
    return path, None


def judge(run, state, prefix):
    """The station's result read as `visit --result` reads it, writing nothing: ("missing", None) for no result yet;
    ("take", None) for one `visit --result` takes; ("refuse", why) for one it refuses (exit 5), why in its words; or
    ("refused-station", (identity, route, rules, why)) for a station refused at its result."""
    visit = state["visit"]
    name = visit["station"]
    path, wrong = _result_file(run, visit)
    if wrong is not None:
        return "refuse", wrong
    if path is None:
        return "missing", None
    try:
        found = stations.resolve(name)
    except stations.RootRefused as exc:
        return "refused-station", (None, exc.route, [exc.rule], str(exc))
    except LookupError as exc:
        raise ComponentUnavailable("missing dependency: %s" % exc)
    identity = stations.identify(name, found)
    problems = stations.refusals(name, identity, found)
    if problems:
        return "refused-station", (identity, found["route"], [p["rule"] for p in problems],
                                   "; ".join(p["message"] for p in problems))
    if identity != visit["identity"] or found["route"] != visit["route"]:
        return "refused-station", (identity, found["route"], ["no-identity"],
                                   "the station %s changed between the visit and its result (identity %r at the visit, "
                                   "%r now)" % (name, visit["identity"], identity))
    try:
        doc = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        return "refuse", ("the station's result %s is not a JSON document (%s): a v1 station leaves no such document"
                          % (path, exc))
    if not isinstance(doc, dict):
        return "refuse", "the station's result %s is not a JSON object" % path
    facts = {"slice": state["slice"], "doc": state["doc"], "workspace": common.workspace(run),
             "report_only": common.report_only(run)}
    problems = stations.result_problems(name, found, identity, doc, visit, facts, prefix)
    if problems:
        return "refuse", "the result %s is refused as not %s's own result for this visit: %s" % (
            path, name, "; ".join(problems))
    held = window.hold(run, state, "while %s's visit was open" % name,
                       station=window.evidence(run, state, name, doc, visit["run_dir"]))
    if held.refuse is not None:
        return "refuse", held.refuse
    return "take", (found, identity, path, doc, held)


def close_visit(ctx, run, args):
    state = common.state(run)
    visit = state["visit"]
    name = visit["station"]
    verdict, detail = judge(run, state, ctx.prefix)
    if verdict == "missing":
        raise driver.Usage("%s has written no result in %s yet: run the station to its end by its own SKILL.md, then "
                           "run `visit --result` (a question it asks the owner is `pause --question`; a station that "
                           "ends without a result it can give: `report`, which ends the run visit-unfinished)"
                           % (name, visit["run_dir"]))
    if verdict == "refuse":
        return common.refuse(ctx, run, detail)
    if verdict == "refused-station":
        identity, route, rules, why = detail
        return _refused(ctx, run, state, name, identity, route, visit["run_dir"], rules, why)
    found, identity, path, doc, held = detail
    told = stations.outcome(name, doc)
    line = trace.line(kind="visit", caller=common.STATION, expected=name, identity=identity, route=found["route"],
                      run_dir=visit["run_dir"], status=str(doc.get("status")), at=common.now())
    _append(ctx, run, line)
    state["visits"].append({"station": name, "run_id": visit["run_id"], "run_dir": visit["run_dir"],
                            "status": doc.get("status"), "word": told["word"], "result": path,
                            "result_sha256": fsio.sha256_file(path), "lap": state["lap"]})
    state["visit"] = None
    if name == "build-v2":
        state["build"] = told["word"]
    if held.stop is not None:
        return report.ending(ctx, run, state, held.stop[0], held.stop[1], condition=held.stop[2])
    window.take(run, state)                 # after the station's own writes: the next window starts here
    if name == "build-v2":
        if not told["complete"]:
            return report.ending(ctx, run, state, "build-not-complete",
                                 "build-v2 ended %s (%s): the build stopped mid-slice, so the run ends at stop "
                                 "condition 3 and goes on to no inspection" % (told["word"], doc.get("status")),
                                 condition=3)
        common.save(run, state)
        common.advance(run, "built")
        return _next(ctx, run, "visit --station signoff-v2", told)
    try:
        return _decide(ctx, run, args, state, name, doc, told)
    except records_link.RecordsRefusal as exc:
        return report.ending(ctx, run, state, "records-refused", records_link.refusal_sentence(
            exc, "reading the findings %s's result leaves" % name))


def _decide(ctx, run, args, state, name, doc, told):
    if name == "signoff-v2":
        state["signoff"] = told["word"]
        if told["stopped"]:
            return report.ending(ctx, run, state, "signoff-stopped",
                                 "signoff-v2 ended %s%s: the run ends with its status" % (
                                     doc.get("status"), " (refused: %s)" % doc.get("refusal_reason")
                                     if doc.get("refusal_reason") else ""), by=name)
        named = _named(run, state, told, args.records_root)
        return _after_review(ctx, run, state, named, told)
    state["recheck"] = told["word"]
    if told["stopped"]:
        return report.ending(ctx, run, state, "recheck-stopped", "recheck-v2 ended %s: the run ends with its status"
                             % doc.get("status"), by=name)
    still = record.blocking(record.named(run, state["slice"], args.records_root))
    return _after_recheck(ctx, run, state, told, still)


def _named(run, state, told, records_root=None):
    """The findings this lap fixes: the records' (record.named), or on a report-only run, where the station wrote
    nothing, the signoff result's own raised findings."""
    if common.report_only(run) and told.get("wrote_nothing"):
        minors = bool(common.station(run).get("minor_fixes"))
        return [dict(f, why="raised by this visit's report-only signoff") for f in told["findings"]
                if f["severity"] in common.BLOCKING or (minors and f["severity"] == "MINOR")]
    return record.named(run, state["slice"], records_root)


def _after_review(ctx, run, state, named, told):
    """After a signoff that did not stop: the lap's fixes when a BLOCKER or MAJOR is charged to the slice (or the
    MINORs the owner ordered, which never gate and never trigger a recheck); ALL CLEAR otherwise."""
    blocking = record.blocking(named)
    if named:
        state.update(named=named, lap=1, minors_only=not blocking)
        common.write(run, "laps.json", {"laps": [{"lap": 1, "opened_at": common.now(), "owner_words": None}]})
        common.save(run, state)
        common.advance(run, "fixing")
        return _next(ctx, run, "fix", told, named=named, lap=1, minors_only=not blocking)
    common.save(run, state)
    common.advance(run, "clean")
    return _next(ctx, run, "report", told, all_clear=True)


def _after_recheck(ctx, run, state, told, still):
    if told["all_clear"] and not still:
        common.save(run, state)
        common.advance(run, "clean")
        return _next(ctx, run, "report", told, all_clear=True)
    state["named"] = still
    common.save(run, state)
    if state["lap"] < common.laps_allowed(run):
        common.advance(run, "lap-needed")
        return _next(ctx, run, "lap", told, still_open=still, lap=state["lap"])
    common.advance(run, "exhausted")
    return _next(ctx, run, "report", told, still_open=still, lap=state["lap"],
                 exhausted="the extra lap is exhausted without ALL CLEAR: `report` ends the run at stop condition 1, "
                           "and a further lap is refused without the owner's words in the input")


def _next(ctx, run, step, told, **extra):
    return ctx.emit(ctx.envelope(next=step, run_id=common.run_id(run), station_status=told["status"],
                                 station_word=told["word"], **extra))


def handler(ctx, args):
    """`visit --run-dir D (--station NAME | --result)`."""
    if bool(args.station) == bool(args.result):
        raise driver.Usage("visit takes one of --station NAME (open a visit) or --result (read the station's result)")
    if args.station:
        run = common.open_run(ctx, args.run_dir, tuple(EXPECT), "visit --station")
        return open_visit(ctx, run, args)
    run = common.open_run(ctx, args.run_dir, ("visiting",), "visit --result")
    return close_visit(ctx, run, args)
