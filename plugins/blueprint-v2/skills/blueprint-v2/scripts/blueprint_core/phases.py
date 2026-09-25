"""blueprint-v2's lane phases and its own command (contract sections 5 to 10).

Handlers for `station_core/driver.py`: `harvest`, `record-answer`, `write` and `report` (the four
phases the frame left to this lane) and `choose` (this core's own command). Each is
`handler(ctx, args) -> exit code`. The run moves through the checkpoint's phases

    checked -> selected -> harvested -> answered -> written -> done

and a command against the wrong phase is exit 2 naming the command to run instead. A run that
reached a terminal status (`done`) answers every lane command with its recorded result, exit 10,
and writes nothing. Every stop writes `result.json` (validated) before it is printed. In
report-only mode nothing is written outside the run directory; the proposed doc is kept in the run
directory as `proposed-build-doc.md`. This module never opens the records component.
"""
import datetime
import json
import os

from station_core import answer as answermod
from station_core import driver, exits, fsio, ledger, templates, validate

from . import buildoc, checks, harvest as harvestmod, readback

HUNTS_NEEDED = ("scope", "architecture", "build")
PROPOSED = "proposed-build-doc.md"
ANSWER_SCHEMA = "answer.schema.json"


# ---- the run -----------------------------------------------------------------------------------

def _open(ctx, args):
    return ctx.open_run(args.run_dir)


def _path(run, name):
    return os.path.join(run.run_dir, name)


def _terminal(ctx, run):
    """The recorded result of a run that already ended, exit 10."""
    path = _path(run, "result.json")
    try:
        doc = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        raise driver.Defect("the run at %s ended but its result.json cannot be read: %s" % (run.run_dir, exc))
    return driver.emit(doc, exits.TERMINAL)


def _require(run, phases, command, instead):
    phase = run.checkpoint.get("phase")
    if phase not in phases:
        raise driver.Usage("this run is at phase %r; `%s` runs %s" % (phase, command, instead))


def _report_only(run):
    return bool(run.input.get("report_only"))


def _selections(run):
    out = {}
    for hunt in HUNTS_NEEDED:
        path = _path(run, "selection-%s.json" % hunt)
        if os.path.isfile(path):
            out[hunt] = fsio.read_json(path)
    return out


def _writes(run, receipt=None):
    rows = []
    for name in sorted(os.listdir(run.run_dir)):
        full = os.path.join(run.run_dir, name)
        if not os.path.isfile(full) or name.startswith(".tmp-"):
            continue
        rewritten = name in ("result.json", "checkpoint.json")
        rows.append({"path": full, "kind": "run_artifact", "sha256_before": None,
                     "sha256_after": None if rewritten else fsio.sha256_file(full)})
    if not any(r["path"] == _path(run, "result.json") for r in rows):
        rows.append({"path": _path(run, "result.json"), "kind": "run_artifact",
                     "sha256_before": None, "sha256_after": None})
    for write in (receipt or {}).get("writes") or []:
        rows.append(dict(write))
    return rows


def _load_json_schema(ctx, name):
    validate.require_jsonschema(ctx.prefix)
    path = os.path.join(validate.references_dir(ctx.skill_root), name)
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/%s (%s)" % (name, exc))


def _finish(ctx, run, status, reason, sr, tag=None, receipt=None):
    """Write the validated result, mark the run done, print the result; exit 10."""
    run.checkpoint["phase"] = "done"
    run.checkpoint["terminal"] = {"status": status, "stop_tag": tag}
    run.save()
    result = {"interface_version": driver.INTERFACE_VERSION,
              "plugin_version": validate.plugin_version(ctx.skill_root), "station": ctx.station,
              "run_id": run.checkpoint["run_id"], "run_dir": run.run_dir, "status": status,
              "stop_tag": tag, "reason": reason, "report_only": _report_only(run),
              "wrote_nothing": not any(w.get("kind") != "run_artifact" for w in (receipt or {}).get("writes") or []),
              "writes": _writes(run, receipt), "selection": _selections(run),
              "invocation": run.input.get("invocation"), "station_result": sr}
    schema = validate.load_schema("result", ctx.prefix, ctx.skill_root)
    problems = validate.errors_for(result, schema, ctx.prefix) + validate.semantic(result)
    if problems:
        raise driver.Defect("the result this run built does not validate: %s" % json.dumps(problems[:4]))
    fsio.write_json(_path(run, "result.json"), result)
    return driver.emit(result, exits.TERMINAL)


def _station_result(run, harvest=None, answer=None, **fields):
    answer = answer or {}
    harvest = harvest or {}
    sr = {"feature": answer.get("feature") or harvest.get("build_name"),
          "doc": None, "doc_action": "none", "slices": 0, "slice_names": [], "new_slices": [],
          "open_questions": len(answer.get("open_questions") or []),
          "assumptions": len(answer.get("assumptions") or []),
          "questions_asked": len(answer.get("questions") or []),
          "scope_doc": (harvest.get("scope") or {}).get("path"),
          "architecture_doc": (harvest.get("architecture") or {}).get("path"),
          "needs_build_doc": (answer.get("ceremony") or {}).get("needs_build_doc"),
          "collapsed_gate": (answer.get("collapsed_gate") or {}).get("words")}
    sr.update(fields)
    return sr


def _stop(ctx, run, tag, reason, harvest=None, answer=None, receipt=None, **fields):
    sr = _station_result(run, harvest, answer, **fields)
    answer = answer or {}
    if tag == "no-build-doc":
        sr_view = dict(sr, why=(answer.get("ceremony") or {}).get("why"))
        sr["readback"] = readback.render(sr_view, run.input.get("workspace"), stop_tag=tag, reason=reason,
                                         open_items=answer.get("open_questions") or [],
                                         assumed=answer.get("assumptions") or [])
    else:
        sr["readback"] = readback.render(sr, run.input.get("workspace"), stop_tag=tag, reason=reason)
    return _finish(ctx, run, "stopped", reason, sr, tag=tag, receipt=receipt)


# ---- choose (this core's own command) ------------------------------------------------------------

def command_choose(ctx, args):
    """Record the owner's pick among a `several` outcome; the script never picks."""
    run = _open(ctx, args)
    if run.checkpoint.get("phase") == "done":
        return _terminal(ctx, run)
    _require(run, ("selected",), "choose", "after `select` and before `harvest`")
    if args.hunt not in HUNTS_NEEDED:
        raise driver.Usage("no hunt %r in this core (its hunts: %s)" % (args.hunt, ", ".join(HUNTS_NEEDED)))
    words = args.words or ""
    if not words.strip() or "\n" in words or "\r" in words:
        raise driver.Usage("--words carries the owner's words that picked the document, verbatim, on one line")
    try:
        selection = harvestmod.selected(run.run_dir, args.hunt)
    except harvestmod.NotSelected:
        raise driver.Usage("the %s hunt has not run: run `select --hunt %s` first" % (args.hunt, args.hunt))
    if selection.get("outcome") != "several":
        raise driver.Usage("the %s hunt's outcome is %r: `choose` settles a `several` outcome only"
                           % (args.hunt, selection.get("outcome")))
    wanted = os.path.normpath(os.path.abspath(args.path))
    paths = [c["path"] for c in selection.get("candidates") or []]
    if wanted not in paths:
        raise driver.Usage("%s is not one of the %s hunt's candidates (%s)" % (wanted, args.hunt, ", ".join(paths)))
    selection["chosen"] = {"path": wanted, "by": "owner", "words": words}
    fsio.write_json(_path(run, "selection-%s.json" % args.hunt), selection)
    return driver.emit(ctx.envelope(next="harvest", run_id=run.checkpoint["run_id"], hunt=args.hunt,
                                    chosen=selection["chosen"], candidates=paths))


# ---- harvest -----------------------------------------------------------------------------------

def _read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _read_selected(path, hunt):
    """A selected document's text; one that vanished or is not UTF-8 is a usage slip, nothing written."""
    try:
        return _read_text(path)
    except (OSError, UnicodeDecodeError) as exc:
        raise driver.Usage("the %s doc %s cannot be read as UTF-8 text (%s): fix it, or run `select --hunt %s` "
                           "again" % (hunt, path, exc, hunt))


def phase_harvest(ctx, args):
    run = _open(ctx, args)
    if run.checkpoint.get("phase") == "done":
        return _terminal(ctx, run)
    _require(run, ("selected",), "harvest", "after `select` has run for the scope, architecture and build hunts")
    selections = {}
    for hunt in HUNTS_NEEDED:
        try:
            selections[hunt] = harvestmod.selected(run.run_dir, hunt)
        except harvestmod.NotSelected:
            raise driver.Usage("the %s hunt has not run: `select --hunt %s` comes before harvest (every run "
                               "hunts scope, architecture and build)" % (hunt, hunt))
    build_name = selections["build"].get("name")
    if not build_name:
        raise driver.Usage("the build hunt ran with no name: run `select --hunt build --name <feature>`, so the "
                           "living doc of this feature is looked for and never forked")
    workspace = run.input["workspace"]
    taken = {}
    several = []
    for hunt in HUNTS_NEEDED:
        path, many, words = harvestmod.taken(selections[hunt])
        if many:
            several.append("%s: %s" % (hunt, ", ".join(os.path.relpath(p, workspace) for p in many)))
        taken[hunt] = (path, words)
    base = {"build_name": build_name}
    if several:
        reason = ("several candidates, listed for the owner and never picked (%s). Ask which one, then start a "
                  "new run and record his pick with `choose` before harvest" % "; ".join(several))
        return _stop(ctx, run, "selection-several", reason, harvest=base)

    run_date = datetime.date.today().isoformat()
    scope = None
    if taken["scope"][0]:
        path = taken["scope"][0]
        try:
            lines = ledger.read(_read_selected(path, "scope"))
        except ledger.LedgerRefused as exc:
            quoted = "; ".join("line %d %r (%s)" % (r["line"], r["raw"], r["why"]) for r in exc.lines)
            return _stop(ctx, run, "ledger-refused", "the scope doc %s holds %d line(s) the ledger reader cannot "
                         "tag: %s" % (os.path.relpath(path, workspace), len(exc.lines), quoted),
                         harvest=dict(base, scope={"path": path}))
        scope = {"path": path, "chosen_by_owner": taken["scope"][1],
                 "ledger": [{"id": r["id"], "tag": r["tag"], "section": r["section"], "text": r["text"],
                             "source": r["source"], "line": r["line"]} for r in lines]}
    architecture = None
    if taken["architecture"][0]:
        path = taken["architecture"][0]
        architecture = dict(harvestmod.architecture_lines(_read_selected(path, "architecture")), path=path,
                            chosen_by_owner=taken["architecture"][1])
    build = None
    if taken["build"][0]:
        path = taken["build"][0]
        build = dict(harvestmod.build_doc(path, _read_selected(path, "build")), chosen_by_owner=taken["build"][1])
        target = path
    else:
        target = os.path.join(workspace, "docs", "plans", "%s-%s.md" % (run_date, build_name))
    doc = {"harvest_version": 1, "run_id": run.checkpoint["run_id"], "run_date": run_date,
           "build_name": build_name, "target": target, "scope": scope, "architecture": architecture,
           "build": build,
           "ledger_view": harvestmod.ledger_view((scope or {}).get("ledger"), architecture)}
    fsio.write_json(_path(run, "harvest.json"), doc)
    run.checkpoint["phase"] = "harvested"
    run.save()
    return driver.emit(ctx.envelope(next="record-answer", harvest=_path(run, "harvest.json"), **doc))


# ---- record-answer ----------------------------------------------------------------------------

def phase_record_answer(ctx, args):
    run = _open(ctx, args)
    if run.checkpoint.get("phase") == "done":
        return _terminal(ctx, run)
    if run.checkpoint.get("phase") == "answered":
        raise driver.Usage("this run already holds an accepted answer; run `write`")
    _require(run, ("harvested",), "record-answer", "after `harvest`")
    if not os.path.isfile(args.answer):
        raise driver.Usage("no such answer file: %s" % args.answer)
    try:
        answer = fsio.read_json(args.answer)
    except (ValueError, UnicodeDecodeError) as exc:
        raise driver.Usage("the answer file is not JSON: %s (%s)" % (args.answer, exc))
    schema = _load_json_schema(ctx, ANSWER_SCHEMA)
    errors = validate.errors_for(answer, schema, ctx.prefix)
    if errors:
        return driver.emit(ctx.envelope(ok=False, accepted=False, error="invalid", errors=errors,
                                        reason="the answer does not validate against references/%s: %d "
                                               "finding(s); nothing was written" % (ANSWER_SCHEMA, len(errors))),
                           exits.VALIDATION)
    harvest = fsio.read_json(_path(run, "harvest.json"))
    view_ledger = harvest.get("ledger_view") or []
    shared = answermod.check(checks.view(answer), view_ledger, workspace=run.input["workspace"],
                             allowed=checks.ALLOWED_TRACES)
    refusals = list(shared["refusals"]) + checks.own(answer, run.input, harvest)
    if refusals:
        return driver.emit(ctx.envelope(accepted=False, refusals=refusals,
                                        reason="the recorded answer was refused on its content (%d refusal(s)); "
                                               "nothing was written" % len(refusals)), exits.REFUSED)
    code, report = answermod.record(run.run_dir, answer, view_ledger, workspace=run.input["workspace"],
                                    allowed=checks.ALLOWED_TRACES)
    if code != exits.SUCCESS:
        raise driver.Defect("the shared record refused an answer the check accepted: %s" % report)
    run.checkpoint["phase"] = "answered"
    run.save()
    return driver.emit(ctx.envelope(next="write", run_id=run.checkpoint["run_id"], accepted=True,
                                    answer=report["answer"], sha256=report["sha256"]))


# ---- write -------------------------------------------------------------------------------------

def _inside_workspace(target, workspace):
    """The target is no link, and its nearest existing folder resolves inside the workspace."""
    if os.path.islink(target):
        return False
    folder = os.path.dirname(target)
    while True:
        if os.path.islink(folder) and not os.path.exists(folder):
            return False
        if os.path.exists(folder):
            break
        parent = os.path.dirname(folder)
        if parent == folder:
            return False
        folder = parent
    return fsio.inside(folder, workspace)


def _proposal(answer, harvest):
    """(text, action, new slice names) the answer renders to, through the shared templates."""
    lines = answer["lines"]
    requirement_text = dict((l["id"], l["text"]) for l in lines if l.get("tag") == "requirement" and l.get("id"))
    criteria = dict((c["id"], c) for c in answer["criteria"] if c.get("id"))
    values = [buildoc.slice_values(s, requirement_text, criteria) for s in answer["slices"]]
    constraints = [l["text"] for l in lines if l["tag"] == "constraint"]
    out_of_scope = [l["text"] for l in lines if l["tag"] == "out-of-scope"]
    names = [s["name"] for s in answer["slices"]]
    build = harvest.get("build")
    if build is None:
        text = templates.render_build_doc(
            title=answer["title"], date=harvest["run_date"], intent=answer["intent"],
            constraints=buildoc.constraints_value(constraints, answer["assumptions"], answer["open_questions"]),
            out_of_scope=out_of_scope, slices=values)
        return text, "created", names
    before = _read_text(build["path"])
    nl = buildoc.newline_of(before)
    blocks = [(v["name"], buildoc.slice_block(v, nl)) for v in values]
    text = buildoc.extend(before, blocks, constraints=constraints, assumptions=answer["assumptions"],
                          open_questions=answer["open_questions"], out_of_scope=out_of_scope)
    return text, "extended", names


def phase_write(ctx, args):
    run = _open(ctx, args)
    if run.checkpoint.get("phase") == "done":
        return _terminal(ctx, run)
    _require(run, ("answered",), "write", "after an accepted `record-answer`")
    answer = fsio.read_json(_path(run, "answer.json"))
    harvest = fsio.read_json(_path(run, "harvest.json"))
    target = harvest["target"]
    workspace = run.input["workspace"]
    empty = {"receipt_version": 1, "writes": []}
    if not answer["ceremony"]["needs_build_doc"]:
        fsio.write_json(_path(run, "receipt.json"), empty)
        return _stop(ctx, run, "no-build-doc", "this does not need a build doc: %s; nothing was written"
                     % answer["ceremony"]["why"], harvest=harvest, answer=answer, receipt=empty)
    build = harvest.get("build")
    now = fsio.sha256_file_or_none(target)
    expected = build["sha256"] if build else None
    if now != expected:
        fsio.write_json(_path(run, "receipt.json"), empty)
        return _stop(ctx, run, "stale-harvest", "the build doc at %s changed after harvest (sha256 %s then, %s "
                     "now); nothing was written. Start a new run so harvest reads what is there"
                     % (os.path.relpath(target, workspace), expected, now), harvest=harvest, answer=answer,
                     receipt=empty)
    if not _inside_workspace(target, workspace):
        fsio.write_json(_path(run, "receipt.json"), empty)
        return _stop(ctx, run, "unsafe-path", "the build doc's path %s leaves the workspace through a link, or is "
                     "a link itself; nothing was written" % target, harvest=harvest, answer=answer, receipt=empty)
    text, action, names = _proposal(answer, harvest)
    if build is not None:
        before = _read_text(build["path"])
        changes = buildoc.protected_changes(before, text)
        if changes:
            fsio.write_json(_path(run, "receipt.json"), empty)
            quoted = "; ".join("%r: %s" % (c["line"], c["what"]) for c in changes)
            return _stop(ctx, run, "write-refused", "the write would change %d protected line(s) of %s: %s; "
                         "nothing was written" % (len(changes), os.path.relpath(target, workspace), quoted),
                         harvest=harvest, answer=answer, receipt=empty,
                         refused_lines=[c["line"] for c in changes])
        old = set(f["message"] for f in harvest["build"]["form_findings"])
        new = [f for f in templates.check("build-doc", text) if f["message"] not in old]
    else:
        new = templates.check("build-doc", text)
    if new:
        raise driver.Defect("the rendered build doc departs from its form: %s" % json.dumps(new[:4]))
    data = text.encode("utf-8")
    if _report_only(run):
        fsio.atomic_write(_path(run, PROPOSED), data)
        receipt = {"receipt_version": 1, "writes": [],
                   "would_write": {"path": target, "kind": "document", "sha256_before": now,
                                   "sha256_after": fsio.sha256_bytes(data)}}
    else:
        fsio.atomic_write(target, data)
        receipt = {"receipt_version": 1, "writes": [{"path": target, "kind": "document", "sha256_before": now,
                                                     "sha256_after": fsio.sha256_file(target)}]}
    fsio.write_json(_path(run, "receipt.json"), receipt)
    run.checkpoint["phase"] = "written"
    run.checkpoint["write"] = {"doc": target, "action": action, "new_slices": names}
    run.save()
    return driver.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], doc=target, action=action,
                                    new_slices=names, report_only=_report_only(run),
                                    receipt=_path(run, "receipt.json")))


# ---- report ------------------------------------------------------------------------------------

def phase_report(ctx, args):
    run = _open(ctx, args)
    if run.checkpoint.get("phase") == "done":
        return _terminal(ctx, run)
    _require(run, ("written",), "report", "after `write`")
    answer = fsio.read_json(_path(run, "answer.json"))
    harvest = fsio.read_json(_path(run, "harvest.json"))
    receipt = fsio.read_json(_path(run, "receipt.json"))
    written = run.checkpoint["write"]
    report_only = _report_only(run)
    text = _read_text(_path(run, PROPOSED) if report_only else written["doc"])
    st = buildoc.structure(text)
    titles = [(s["name"], s["short"]) for s in st["slices"]]
    sr = _station_result(run, harvest, answer, doc=written["doc"], doc_action=written["action"],
                         slices=len(titles), slice_names=[n for n, _ in titles], new_slices=written["new_slices"])
    view = dict(sr, slice_titles=titles)
    sr["readback"] = readback.render(view, run.input["workspace"], report_only=report_only,
                                     open_items=answer["open_questions"], assumed=answer["assumptions"])
    rel = os.path.relpath(written["doc"], run.input["workspace"])
    if report_only:
        reason = ("report-only: nothing was written; the build doc would be %s at %s"
                  % (written["action"], rel))
    else:
        reason = "the build doc was %s: %s" % ("written" if written["action"] == "created"
                                               else "extended in place", rel)
    return _finish(ctx, run, "completed", reason, sr, receipt=receipt)
