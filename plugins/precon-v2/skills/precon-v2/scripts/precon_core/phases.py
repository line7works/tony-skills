"""The phases precon-v2 builds on the frame (`harvest`, `record-answer`, `write`, `report`) and its
own commands (`state`, `request`). Each is `handler(ctx, args) -> exit code` for
`station_core/driver.py`; `references/precon-v2-contract.md` states what each reads, writes and
prints, and its exits.
"""
import datetime
import functools
import glob
import json
import os
import subprocess

from station_core import answer as answermod
from station_core import driver, exits, fsio, ledger, readers_request, templates, validate

from . import exit_test, rules, run as runmod, scopedoc

ALLOWED_TRACES = ("ledger", "repo_path", "question", "owner_words", "assumed")
TAG_NO_SCOPE_DOC = "no-scope-doc"
TAG_FORM_REFUSED = "form-refused"
TAG_DOC_CHANGED = "doc-changed"
TAG_LEDGER_REFUSED = "ledger-refused"
TAG_SELECTION_SEVERAL = "selection-several"
HOMES = {"repo-scope": "repo", "repo-flat": "repo", "staging": "staging"}


def handler(fn):
    """A phase: an ended run prints its recorded result again (exit 10) and writes nothing."""
    @functools.wraps(fn)
    def wrapped(ctx, args):
        try:
            return fn(ctx, args)
        except runmod.Ended as ended:
            return runmod.emit(ended.document, exits.TERMINAL)
    return wrapped


def _plugin_root(ctx):
    return os.path.dirname(os.path.dirname(ctx.skill_root))


def _is_git_root(path):
    try:
        proc = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    except OSError:
        return False
    out = proc.stdout.decode("utf-8", "replace").strip()
    return proc.returncode == 0 and os.path.realpath(out) == os.path.realpath(path)


def _read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _selection(run, hunt):
    return runmod.read_json(run, "selection-%s.json" % hunt)


def _summary(tag_counts):
    return {"counts": tag_counts, "board": scopedoc.board(tag_counts)}


def _base_result(harvest):
    harvest = harvest or {}
    doc = harvest.get("doc") or {}
    return {"idea": harvest.get("idea"), "doc": doc.get("path"), "home": doc.get("home") or harvest.get("home")}


# ---- harvest -------------------------------------------------------------------------------------

@handler
def harvest(ctx, args):
    run = runmod.open_run(ctx, args)
    runmod.need(run, ("selected", "harvested"), "harvest", "after `select --hunt scope --name <idea>` and before "
                                                          "`record-answer`")
    sel = _selection(run, "scope")
    if sel is None:
        raise driver.Usage("no scope selection in this run: run `select --run-dir D --hunt scope --name <idea>` first")
    idea = sel.get("name")
    if not idea:
        raise driver.Usage("the scope selection ran without --name: the idea's slug is what the doc is found and "
                           "named by; run `select --hunt scope --name <idea>` again")
    station = runmod.station_input(run)
    date = station.get("date") or datetime.date.today().isoformat()
    home = station.get("home") or "repo"
    workspace, staging = run.input["workspace"], run.input.get("staging")
    out = {"idea": idea, "date": date, "home": home, "doc": None, "ledger": [],
           "new_doc": scopedoc.new_doc_path(station, workspace, staging, date, idea), "cold_read": None,
           "report_only": runmod.report_only(run)}
    if sel["outcome"] == "several":
        return runmod.stop(ctx, run, TAG_SELECTION_SEVERAL,
                           "the idea %r has a scope doc in several homes; they are listed for the owner and never "
                           "picked: %s" % (idea, ", ".join(c["path"] for c in sel["candidates"])),
                           dict(_base_result(out), candidates=sel["candidates"], gate=None))
    untaken = _untaken(ctx, run, idea, sel)
    if untaken:
        raise driver.Usage("the idea %r matches %s in a scope home, which the hunt cannot take (a symlink leaving "
                           "its home, a broken link, or not a file): one living doc, so this run neither forks a "
                           "second doc beside it nor continues it; the owner resolves it. Nothing was written"
                           % (idea, ", ".join(untaken)))
    if sel["outcome"] == "one":
        cand = sel["candidates"][0]
        text = _read_text(cand["path"])
        try:
            rows = ledger.read(text)
        except ledger.LedgerRefused as exc:
            quoted = "; ".join("line %d %r (%s)" % (r["line"], r["raw"], r["why"]) for r in exc.lines)
            return runmod.stop(ctx, run, TAG_LEDGER_REFUSED,
                               "the scope doc holds line(s) the ledger reader cannot tag: %s" % quoted,
                               dict(_base_result(out), doc=cand["path"], ledger_refused=exc.lines, gate=None))
        findings = templates.check("scope-doc", text) + scopedoc.comment_findings(text)
        if findings:
            quoted = "; ".join("line %d: %s" % (f["line"], f["message"]) for f in findings)
            return runmod.stop(ctx, run, TAG_FORM_REFUSED,
                               "the scope doc departs from the form, so nothing can be placed in it: %s" % quoted,
                               dict(_base_result(out), doc=cand["path"], form_findings=findings, gate=None))
        head = scopedoc.header(text)
        out["doc"] = dict(head, path=cand["path"], home=HOMES.get(cand["home"], cand["home"]),
                          sha256=fsio.sha256_bytes(text.encode("utf-8")))
        out["ledger"] = rows
        fsio.atomic_write(runmod.path(run, "harvest-scope-doc.md"), text.encode("utf-8"))
    elif home == "repo" and not _is_git_root(workspace):
        raise driver.Usage("the input's home is repo, and the workspace %s is not a git work tree root: a new scope "
                           "doc goes into the repository the idea belongs to, or set station.home to staging"
                           % workspace)
    doc_home = (out["doc"] or {}).get("home") or home
    root = staging if doc_home == "staging" else workspace
    # the new doc's folder is checked here; the cold-read doc's only in the run that builds the cold read
    # (`request`), so a stray docs/reviews never blocks a run that has no exit test (CP1-17)
    if out["doc"] is None:
        _contained_or_usage(out["new_doc"], root)
    out.update(_summary(scopedoc.counts(out["ledger"])))
    cold = _selection(run, "cold-read")
    if cold is not None:
        candidates = []
        for cand in cold["candidates"]:
            text = _read_text(cand["path"])
            candidates.append({"path": cand["path"], "home": cand["home"], "sha256": fsio.sha256_bytes(text.encode("utf-8")),
                               "rows": sorted(exit_test.section_rows(text))})
        out["cold_read"] = {"outcome": cold["outcome"], "candidates": candidates}
    runmod.write_json(run, "harvest.json", out)
    runmod.advance(run, "harvested")
    return runmod.emit(ctx.envelope(next="record-answer", run_id=run.checkpoint["run_id"],
                                    harvest=runmod.path(run, "harvest.json"), **out), exits.SUCCESS)


def _contained_or_usage(target, root):
    if root and not scopedoc.contained(target, root):
        raise driver.Usage("the folder of %s resolves outside %s (a symlinked folder?): this station writes only "
                           "inside the workspace and the staging home; nothing was written" % (target, root))


def _untaken(ctx, run, idea, sel):
    """Every entry the scope hunt's globs match that the hunt did not take as a candidate."""
    roots = {"workspace": run.input.get("workspace"), "staging": run.input.get("staging")}
    taken = set(os.path.normpath(c["path"]) for c in sel.get("candidates") or [])
    out = []
    for home in ctx.hunts.get("scope") or []:
        root = roots.get(home["root"])
        if not root:
            continue
        for pattern in home["globs"]:
            for path in glob.glob(os.path.join(glob.escape(root), pattern.replace("{name}", idea))):
                if os.path.lexists(path) and os.path.normpath(path) not in taken:
                    out.append(os.path.normpath(path))
    return sorted(set(out))


# ---- state ---------------------------------------------------------------------------------------

def _current_doc(run):
    receipt = runmod.read_json(run, "receipt.json") or {}
    if receipt.get("scope_doc") and os.path.isfile(receipt["scope_doc"]):
        return receipt["scope_doc"]
    sel = _selection(run, "scope")
    if sel and sel.get("outcome") == "one":
        return sel["candidates"][0]["path"]
    return None


def state(ctx, args):
    run = ctx.open_run(args.run_dir)
    runmod.need(run, runmod.PHASES[1:], "state", "after `select`")
    sel = _selection(run, "scope")
    out = {"ok": True, "run_id": run.checkpoint["run_id"], "doc": None}
    if sel and sel.get("outcome") == "several":
        out.update(counts=None, board=None, candidates=sel["candidates"])
        return runmod.emit(ctx.envelope(**out), exits.SUCCESS)
    path = _current_doc(run)
    rows = []
    if path:
        out["doc"] = path
        try:
            rows = ledger.read(_read_text(path))
        except ledger.LedgerRefused as exc:
            out.update(counts=None, board=None, ledger_refused=exc.lines)
            return runmod.emit(ctx.envelope(**out), exits.SUCCESS)
    out.update(_summary(scopedoc.counts(rows)))
    return runmod.emit(ctx.envelope(**out), exits.SUCCESS)


# ---- request -------------------------------------------------------------------------------------

@handler
def request(ctx, args):
    run = runmod.open_run(ctx, args)
    runmod.need(run, ("harvested",), "request", "after `harvest` and before `record-answer`")
    index_path = runmod.path(run, runmod.EXIT_TEST_DIR, "requests.json")
    if os.path.exists(index_path):
        raise driver.Usage("this run already built its exit-test requests (%s); a new cold read is a new run"
                           % index_path)
    harvest_doc = runmod.read_json(run, "harvest.json")
    if not harvest_doc.get("doc"):
        raise driver.Usage("the exit test reads the scope doc, and this run has none: the cold read is offered when "
                           "the doc exists")
    doc = harvest_doc["doc"]
    workspace, staging = run.input["workspace"], run.input.get("staging")
    _contained_or_usage(exit_test.cold_read_path(doc["home"], workspace, staging, harvest_doc["date"],
                                                 harvest_doc["idea"]),
                        scopedoc.root_of(doc["path"], doc["home"], workspace, staging))
    try:
        roster = readers_request.load_roster(exit_test.roster_path(_plugin_root(ctx)))
    except (exit_test.RosterMissing, OSError, ValueError) as exc:
        raise driver.Usage("readers' roster cannot be read: %s" % exc)
    models = {}
    for item in args.model or []:
        row, sep, model = item.partition("=")
        if not sep or not row or not model:
            raise driver.Usage("--model takes ROW=ID, not %r" % item)
        models[row] = model
    rows = list(args.row or [])
    built, refusals = exit_test.plan_requests(rows, run.input, roster, run.checkpoint["run_id"], run.run_dir,
                                              harvest_doc["doc"]["path"], session_model=args.session_model,
                                              models=models)
    if refusals:
        raise driver.Usage("no request was built: " + "; ".join(refusals))
    listed = []
    for req in built:
        target = runmod.path(run, runmod.EXIT_TEST_DIR, "%s.json" % req["call_id"])
        fsio.write_json(target, req)
        listed.append({"row": req["row"], "call_id": req["call_id"], "path": target,
                       "authorized": req.get("authorized") is True})
    index = {"requests": listed, "readers_run_dir": runmod.path(run, runmod.READERS_DIR), "mandate": exit_test.MANDATE}
    fsio.write_json(index_path, index)
    return runmod.emit(ctx.envelope(ok=True, next="summon readers with each request, then record-answer",
                                    run_id=run.checkpoint["run_id"], **index), exits.SUCCESS)


# ---- the plan every write follows ------------------------------------------------------------------

def _load(run):
    return (runmod.read_json(run, "harvest.json") or {}, runmod.read_json(run, "answer.json"),
            runmod.read_json(run, os.path.join(runmod.EXIT_TEST_DIR, "requests.json")))


def plan(run, harvest_doc, answer, requests):
    """[{path, kind, role, sha256_before, text}] and the calls, or a PlanError."""
    triage = answer.get("triage") or {}
    if triage.get("no_scope_doc"):
        return [], []
    tier = triage.get("tier")
    parts = scopedoc.classify(answer, harvest_doc.get("ledger") or [], answer.get("run_id"))
    if parts["problems"]:
        raise scopedoc.PlanError(parts["problems"])
    workspace, staging = run.input["workspace"], run.input.get("staging")
    doc = harvest_doc.get("doc")
    idea, date = harvest_doc["idea"], harvest_doc["date"]
    writes, calls = [], []
    et = answer.get("exit_test") or {}
    if et.get("rows"):
        for req in (requests or {}).get("requests") or []:
            call = exit_test.read_call(run.run_dir, exit_test.read_request(req["path"]))
            if isinstance(call, str):
                raise scopedoc.PlanError([{"message": call}])
            calls.append(call)
    cold_path = None
    if doc is not None and any(c["status"] == "ok" for c in calls):
        root = scopedoc.root_of(doc["path"], doc["home"], workspace, staging)
        cold_path = exit_test.cold_read_path(doc["home"], workspace, staging, date, idea)
        pointer = scopedoc.COLD_POINTER % os.path.relpath(cold_path, root)
        if not any(row["tag"] == "research" and row["text"] == pointer for row in harvest_doc.get("ledger") or []):
            parts["research"].append(pointer)
        existing = _read_text(cold_path) if os.path.isfile(cold_path) else None
        text = exit_test.render_cold_read(existing, idea, date, os.path.relpath(doc["path"], root),
                                          answer.get("run_id"), calls)
        writes.append({"path": cold_path, "kind": "document", "role": "cold-read",
                       "sha256_before": fsio.sha256_bytes(existing.encode("utf-8")) if existing is not None else None,
                       "text": text})
    if doc is None:
        if scopedoc.settles_anything(parts):
            fields = answer.get("doc") or {}
            problems = []
            scopedoc.one_line(fields.get("title"), "the doc's title", problems)
            scopedoc.one_line(fields.get("intent"), "the doc's intent", problems)
            if problems:
                raise scopedoc.PlanError(problems)
            text = scopedoc.render_new(fields["title"], date, fields["intent"], tier, parts)
            writes.insert(0, {"path": harvest_doc["new_doc"], "kind": "document", "role": "scope",
                              "sha256_before": None, "text": text})
    else:
        before = _read_text(runmod.path(run, "harvest-scope-doc.md"))
        text = scopedoc.render_continued(before, tier, parts)
        if text != before:
            writes.insert(0, {"path": doc["path"], "kind": "document", "role": "scope", "sha256_before": doc["sha256"],
                              "text": text})
    for item in writes:
        if item["role"] == "scope":
            problems = scopedoc.check_rendered(item["text"])
            if problems:
                raise scopedoc.PlanError(problems)
    if et.get("dispositions") is not None:
        target = et["cold_read_doc"]
        cand = [c for c in (harvest_doc.get("cold_read") or {}).get("candidates") or [] if c["path"] == target][0]
        existing = _read_text(target)
        if fsio.sha256_bytes(existing.encode("utf-8")) != cand["sha256"]:
            raise scopedoc.PlanError([{"message": "the cold-read doc %s changed after harvest" % target}])
        text = exit_test.render_disposition(existing, date, answer.get("run_id"), et["summary"], et["dispositions"])
        writes.append({"path": target, "kind": "document", "role": "disposition", "sha256_before": cand["sha256"],
                       "text": text})
    return writes, calls


# ---- record-answer --------------------------------------------------------------------------------

def _answer_schema(ctx):
    validate.require_jsonschema(ctx.prefix)
    path = os.path.join(validate.references_dir(ctx.skill_root), "answer.schema.json")
    try:
        with open(path, "rb") as fh:
            schema = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/answer.schema.json (%s)" % exc)
    return schema


def _view(answer):
    """The shared checks' view: the questions, and every asserted line with the out-of-scope items."""
    lines = list(answer.get("lines") or [])
    for item in answer.get("out_of_scope") or []:
        row = {"text": item.get("text"), "tag": "out-of-scope"}
        if "trace" in item:
            row["trace"] = item["trace"]
        lines.append(row)
    return {"questions": answer.get("questions"), "lines": lines}


@handler
def record_answer(ctx, args):
    run = runmod.open_run(ctx, args)
    phase = run.checkpoint.get("phase")
    if phase in ("answered", "written"):
        raise driver.Usage("this run already recorded its one answer; a corrected answer is a new run")
    runmod.need(run, ("harvested",), "record-answer", "after `harvest`")
    if not os.path.isfile(args.answer):
        raise driver.Usage("no such answer file: %s" % args.answer)
    try:
        with open(args.answer, "rb") as fh:
            answer = json.loads(fh.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise driver.Usage("the answer file is not JSON: %s (%s)" % (args.answer, exc))
    schema = _answer_schema(ctx)
    errors = validate.errors_for(answer, schema, ctx.prefix)
    if errors:
        return runmod.emit(ctx.envelope(ok=False, accepted=False, error="invalid",
                                        reason="the answer does not validate against references/answer.schema.json: "
                                               "%d finding(s); nothing was written" % len(errors), errors=errors),
                           exits.VALIDATION)
    harvest_doc, _, requests = _load(run)
    shared = answermod.check(_view(answer), harvest_doc.get("ledger") or [], workspace=run.input["workspace"],
                             allowed=ALLOWED_TRACES)
    refusals = list(shared["refusals"]) + rules.check(answer, run.input, harvest_doc, requests, run.run_dir)
    if not refusals:
        try:
            plan(run, harvest_doc, answer, requests)
        except scopedoc.PlanError as exc:
            refusals += [rules.refusal("unrenderable", p["message"], **dict((k, v) for k, v in p.items()
                                                                            if k != "message")) for p in exc.problems]
    if refusals:
        return runmod.emit(ctx.envelope(ok=False, accepted=False, refusals=refusals,
                                        reason="the recorded answer was refused on its content (%d refusal(s)); "
                                               "nothing was written" % len(refusals)), exits.REFUSED)
    code, report = answermod.record(run.run_dir, answer, harvest_doc.get("ledger") or [],
                                    workspace=run.input["workspace"], allowed=ALLOWED_TRACES)
    if code != exits.SUCCESS:
        return runmod.emit(ctx.envelope(ok=False, accepted=False, refusals=report["refusals"], reason=report["reason"]),
                           exits.REFUSED)
    runmod.advance(run, "answered")
    return runmod.emit(ctx.envelope(ok=True, accepted=True, next="write", run_id=run.checkpoint["run_id"],
                                    answer=report["answer"], sha256=report["sha256"]), exits.SUCCESS)


# ---- write ---------------------------------------------------------------------------------------

@handler
def write(ctx, args):
    run = runmod.open_run(ctx, args)
    phase = run.checkpoint.get("phase")
    if phase == "written":
        receipt = runmod.read_json(run, "receipt.json") or {}
        return runmod.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], repeated=True,
                                        writes=receipt.get("writes", []), planned=receipt.get("planned", []),
                                        reason=receipt.get("reason")), exits.SUCCESS)
    runmod.need(run, ("answered",), "write", "after an accepted `record-answer`")
    harvest_doc, answer, requests = _load(run)
    try:
        writes, calls = plan(run, harvest_doc, answer, requests)
    except scopedoc.PlanError as exc:
        raise driver.Defect("the accepted answer no longer plans: %s" % exc)
    changed = []
    workspace, staging = run.input["workspace"], run.input.get("staging")
    for item in writes:
        if not (scopedoc.contained(item["path"], workspace) or (staging and scopedoc.contained(item["path"], staging))):
            changed.append("%s (its folder now resolves outside the workspace and the staging home)" % item["path"])
            continue
        now = fsio.sha256_file_or_none(item["path"])
        if now != item["sha256_before"]:
            changed.append("%s (%s at harvest, %s now)" % (item["path"], item["sha256_before"] or "absent",
                                                           now or "absent"))
    if changed:
        return runmod.stop(ctx, run, TAG_DOC_CHANGED,
                           "a document changed after harvest, so nothing was written and every byte is as found: %s"
                           % "; ".join(changed), dict(_base_result(harvest_doc), gate=answer.get("gate")))
    scope = [w["path"] for w in writes if w["role"] == "scope"]
    receipt = {"writes": [], "planned": [], "scope_doc": scope[0] if scope else None,
               "cold_read_doc": next((w["path"] for w in writes if w["role"] in ("cold-read", "disposition")), None),
               "calls": [dict((k, v) for k, v in c.items() if k != "raw_text") for c in calls]}
    receipt.update(_left(run, harvest_doc, writes))
    if runmod.report_only(run):
        for number, item in enumerate(writes, 1):
            preview = runmod.path(run, runmod.PREVIEW_DIR, "%d-%s" % (number, os.path.basename(item["path"])))
            fsio.atomic_write(preview, item["text"].encode("utf-8"))
            receipt["planned"].append({"path": item["path"], "kind": item["kind"], "preview": preview,
                                       "sha256_before": item["sha256_before"]})
        receipt["reason"] = "report-only: nothing was written outside the run directory; %d document(s) would be " \
                            "written, previewed under %s" % (len(writes), runmod.path(run, runmod.PREVIEW_DIR))
    else:
        for item in writes:
            fsio.atomic_write(item["path"], item["text"].encode("utf-8"))
            receipt["writes"].append({"path": item["path"], "kind": item["kind"],
                                      "sha256_before": item["sha256_before"],
                                      "sha256_after": fsio.sha256_file(item["path"])})
        receipt["reason"] = _write_reason(answer, harvest_doc, writes)
    runmod.write_json(run, "receipt.json", receipt)
    runmod.advance(run, "written")
    return runmod.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], writes=receipt["writes"],
                                    planned=receipt["planned"], reason=receipt["reason"]), exits.SUCCESS)


def _left(run, harvest_doc, writes):
    """The scope doc as this run leaves it, counted from the text the run wrote (or would write, under
    report-only), or from the bytes harvest read when it writes none: `report` reports this, never the
    doc on disk by the time it runs, which a hand may have changed since (CP1-5)."""
    planned = [w for w in writes if w["role"] == "scope"]
    if planned:
        path, text = planned[0]["path"], planned[0]["text"]
    elif harvest_doc.get("doc"):
        path, text = harvest_doc["doc"]["path"], _read_text(runmod.path(run, "harvest-scope-doc.md"))
    else:
        return {"left_doc": None, "left_counts": scopedoc.counts([]), "left_parked": []}
    rows = ledger.read(text)
    return {"left_doc": path, "left_counts": scopedoc.counts(rows), "left_parked": scopedoc.parked_lines(rows)}


def _write_reason(answer, harvest_doc, writes):
    if (answer.get("triage") or {}).get("no_scope_doc"):
        return "napkin: the owner took no scope doc; nothing was written"
    if not writes:
        if harvest_doc.get("doc") is None:
            return "no settled line yet: the scope doc is born at the first settled line, so nothing was written"
        return "nothing new to write: every line of the answer passes a ledger line forward"
    return "written: %s" % ", ".join(w["path"] for w in writes)


# ---- report --------------------------------------------------------------------------------------

def _chat_block(idea, doc_line, counts, parked, calls, cold, gate, sitting):
    """v1's read-back lines first, in v1's order (PRECON, Doc, Counts, Parked, Next); then, below a
    blank line, the lines this core adds (Exit test, Cold read, Gate) (CP1-13)."""
    lines = ["PRECON: %s" % idea, "Doc: %s" % doc_line,
             "Counts: decided %d %s assumed %d %s parked %d %s out of scope %d" % (
                 counts["decided"], scopedoc.M, counts["assumed"], scopedoc.M, counts["parked"], scopedoc.M,
                 counts["out_of_scope"])]
    lines += ["Parked: %s" % p for p in parked] or ["Parked: none"]
    lines.append("Next: /blueprint when ready." if sitting == "ends" else "Next: the next round (the sitting continues).")
    added = []
    for call in calls:
        added.append("Exit test: %s %s %s %s %s" % (call["row"], scopedoc.M, call["status"], scopedoc.M,
                                                    call["effective_model"] if call["status"] == "ok"
                                                    else (call["reason"] or "no reason given")))
    if cold:
        added.append("Cold read: %s" % cold)
    added.append("Gate: %s" % gate)
    return "\n".join(lines) + "\n\n" + "\n".join(added)


@handler
def report(ctx, args):
    run = runmod.open_run(ctx, args)
    phase = run.checkpoint.get("phase")
    harvest_doc = runmod.read_json(run, "harvest.json") or {}
    next_command = {"checked": "select --run-dir D --hunt scope --name <idea>", "selected": "harvest --run-dir D",
                    "harvested": "record-answer --run-dir D --answer FILE", "answered": "write --run-dir D"}
    if phase in next_command:
        raise driver.Usage("this run is at phase %r; `report` runs after `write` (or a report-only write): run `%s` "
                           "next; nothing was written" % (phase, next_command[phase]))
    answer = runmod.read_json(run, "answer.json")
    receipt = runmod.read_json(run, "receipt.json") or {}
    triage = answer.get("triage") or {}
    idea = harvest_doc.get("idea")
    zero = {"decided": 0, "assumed": 0, "parked": 0, "out_of_scope": 0}
    calls = receipt.get("calls") or []
    exit_calls = [{"row": c["row"], "call_id": c["call_id"], "status": c["status"], "reason": c.get("reason"),
                   "effective_model": c.get("effective_model"), "section": c["status"] == "ok"} for c in calls]
    exit_block = {"calls": exit_calls, "cold_read_doc": receipt.get("cold_read_doc")} if (
        calls or receipt.get("cold_read_doc")) else None
    base = {"idea": idea, "doc": None, "home": None, "tier": triage.get("tier"), "triage_why": triage.get("why"),
            "counts": zero, "board": scopedoc.board(scopedoc.counts([])), "parked": [], "exit_test": exit_block,
            "planned": receipt.get("planned") or [], "sitting": answer.get("sitting")}
    if triage.get("no_scope_doc"):
        base["chat_block"] = _chat_block(idea, "none %s napkin, straight to /blueprint" % scopedoc.D, zero, [], [],
                                         None, answer["gate"], "ends")
        base["gate"] = answer["gate"]
        return runmod.stop(ctx, run, TAG_NO_SCOPE_DOC, "napkin: the owner took no scope doc, straight to /blueprint; "
                                                       "the run wrote no file", base)
    path = receipt.get("left_doc")
    tag_counts = receipt.get("left_counts") or scopedoc.counts([])
    base.update(doc=path, home=((harvest_doc.get("doc") or {}).get("home") or harvest_doc.get("home")) if path else None,
                counts=scopedoc.final_counts(tag_counts), board=scopedoc.board(tag_counts),
                parked=list(receipt.get("left_parked") or []))
    if path is None:
        doc_line = "none (no settled line yet)"
    elif runmod.report_only(run):
        doc_line = "%s (report-only: not written)" % path
    else:
        doc_line = path
    base["chat_block"] = _chat_block(idea, doc_line, base["counts"], base["parked"], exit_calls,
                                     receipt.get("cold_read_doc"), answer["gate"], answer.get("sitting"))
    base["gate"] = answer["gate"]
    return runmod.finish(ctx, run, "completed", receipt.get("reason") or "the run completed", base)
