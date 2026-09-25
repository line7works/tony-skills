"""architect-v2's phases and own commands: the handlers `scripts/architect.py` hands the driver.

The run's own state rides in `checkpoint.json` beside the driver's `phase`: the `architect` block
(`round`, the doc `written` at, whether the visual was `rendered` after the last write, the
`published` outcome after the last render). The phases, in order:

    harvest        selected -> harvested            (or a stop: stopped)
    record-answer  harvested | answered | written -> answered
    write          answered -> written              (or a stop)
    render-visual  written, after a write
    record-publish written, after a render
    request        written (a run with a scope doc)
    save-take      written (a run with a scope doc)
    report         written, rendered, and published when the answer publishes -> reported
                   (or stopped: review-pending); a stopped or reported run prints its result again

A command out of turn is exit 2 naming what to run instead. `references/architect-v2-contract.md`
is the contract of each.
"""
import os
import re

from station_core import driver, exits, fsio, ledger, readers_request

from . import docs, harvesting, publishing, recording, results, review, schema, visual
from .common import blank, display, inside, read_text, today
from .receipt import Changed, Receipt

A = "architect"
ROW = re.compile(r"^[a-z0-9][a-z0-9-]*$")


# ---- helpers ------------------------------------------------------------------------------------

def _state(run):
    return run.checkpoint.setdefault(A, {"round": 0, "doc": None, "rendered": False, "visual": None,
                                         "published": None, "publish_url": None})


def _phase(run):
    return run.checkpoint.get("phase")


def _load(run, name):
    path = os.path.join(run.run_dir, name)
    return fsio.read_json(path) if os.path.isfile(path) else None


def _living_text(run):
    path = os.path.join(run.run_dir, "harvested-doc.md")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _report_only(run):
    return bool(run.input.get("report_only"))


def _preview(run, path):
    """Where a document write lands: the path itself, or the run's preview folder in report-only."""
    if not _report_only(run):
        return path
    return os.path.join(run.run_dir, "preview", os.path.basename(path))


def _stop(ctx, run, tag, reason, station_result=None, receipt=None):
    receipt = receipt or Receipt(run.run_dir)
    sr = station_result or results.empty_station_result()
    doc = results.build(ctx.envelope(), run, "stopped", tag, reason, sr, receipt)
    results.write(doc, ctx.skill_root)
    run.checkpoint["phase"] = "stopped"
    run.save()
    out = dict(doc, next="done", chat=results.chat(doc), result=os.path.join(run.run_dir, "result.json"))
    return driver.emit(out, exits.TERMINAL)


def _need(run, *phases):
    phase = _phase(run)
    if phase in ("stopped", "reported"):
        raise driver.Usage("this run has ended (%s); run `report` to print its result, and start a new run for "
                           "anything more" % phase)
    if phase not in phases:
        raise driver.Usage("this run is at phase %r; this command runs at %s" % (phase, " or ".join(phases)))


def _session(run):
    return (run.input.get("invocation") or {}).get("session_id")


def _station(run):
    return run.input.get("station") or {}


# ---- harvest ------------------------------------------------------------------------------------

def harvest(ctx, args):
    run = ctx.open_run(args.run_dir)
    if _phase(run) == "checked":
        raise driver.Usage("run `select --hunt scope` and `select --hunt architecture --name <slug>` before `harvest`")
    _need(run, "selected")
    ws, staging = run.input["workspace"], run.input.get("staging")
    station = _station(run)
    scope_sel = _load(run, "selection-scope.json")
    arch_sel = _load(run, "selection-architecture.json")
    if arch_sel is None:
        raise driver.Usage("run `select --hunt architecture --name <slug>` before `harvest` (the slug is the scope "
                           "doc's idea, or on a docless run the working name the gate discussion settled)")
    receipt = Receipt(run.run_dir)
    scope_path = station.get("scope_doc")
    if scope_path:
        if not os.path.isfile(scope_path):
            raise driver.Usage("the scope doc the input names is not a file: %s" % scope_path)
        if not harvesting.home_of(scope_path, ws, staging):
            raise driver.Usage("the scope doc the input names lies outside the workspace and the staging home: %s "
                               "(the architecture doc's home follows the scope doc's)" % scope_path)
    elif scope_sel is None:
        raise driver.Usage("run `select --hunt scope` before `harvest` (or name the scope doc in the input's "
                           "`station.scope_doc`)")
    elif scope_sel["outcome"] == "several":
        sr = results.empty_station_result()
        return _stop(ctx, run, "selection-several",
                     "the scope hunt found %d scope docs (%s); they are listed for the owner and never picked: put "
                     "the list to him and start a new run whose input names his pick in `station.scope_doc`"
                     % (len(scope_sel["candidates"]), ", ".join(c["path"] for c in scope_sel["candidates"])), sr, receipt)
    elif scope_sel["outcome"] == "one":
        scope_path = scope_sel["candidates"][0]["path"]
    if scope_path:
        slug = harvesting.slug_of(scope_path)
        if slug is None:
            raise driver.Usage("the scope doc's name %s gives no slug (one path segment of lowercase letters, "
                               "digits, '.', '_' and '-')" % os.path.basename(scope_path))
        if arch_sel.get("name") != slug:
            raise driver.Usage("the architecture hunt ran with --name %r; this scope doc's slug is %r. Run "
                               "`select --hunt architecture --name %s`" % (arch_sel.get("name"), slug, slug))
    else:
        slug = arch_sel.get("name")
        if not slug:
            raise driver.Usage("no scope doc was found (the docless path): run `select --hunt architecture --name "
                               "<slug>` with the working name the gate discussion settled")
    if arch_sel["outcome"] == "several":
        sr = dict(results.empty_station_result(), slug=slug, scope_doc=scope_path)
        return _stop(ctx, run, "selection-several",
                     "the architecture hunt found %d docs for %r (%s); one living doc per project, so they are "
                     "listed for the owner and never picked" % (len(arch_sel["candidates"]), slug,
                                                                ", ".join(c["path"] for c in arch_sel["candidates"])),
                     sr, receipt)
    living_path = arch_sel["candidates"][0]["path"] if arch_sel["outcome"] == "one" else None
    scope_text = read_text(scope_path) if scope_path else None
    living_text = read_text(living_path) if living_path else None
    try:
        record = harvesting.describe(ws, staging, today(), slug, scope_path, scope_text, living_path, living_text,
                                     run_id=run.checkpoint["run_id"], input_publish=station.get("publish", True))
    except ledger.LedgerRefused as exc:
        sr = dict(results.empty_station_result(), slug=slug, scope_doc=scope_path)
        return _stop(ctx, run, "ledger-refused", "the scope doc's ledger holds line(s) the reader cannot tag, quoted "
                     "and never dropped: %s" % "; ".join("line %d %r (%s)" % (r["line"], r["raw"], r["why"])
                                                         for r in exc.lines), sr, receipt)
    living = record["living_doc"]
    if living and living["findings"]:
        sr = dict(results.empty_station_result(), slug=slug, scope_doc=scope_path)
        return _stop(ctx, run, "living-doc-malformed",
                     "the living doc %s does not hold its form, so it cannot be continued without guessing: %s"
                     % (living_path, "; ".join("line %d: %s" % (f["line"], f["message"]) for f in living["findings"])),
                     sr, receipt)
    receipt.write_json(os.path.join(run.run_dir, "harvest.json"), record)
    if living_text is not None:
        receipt.write(os.path.join(run.run_dir, "harvested-doc.md"), living_text)
    run.checkpoint["phase"] = "harvested"
    _state(run)
    run.save()
    reason = ("docless: no scope doc was found; ask the owner once whether one exists where the glob cannot see "
              "(a question `about: scope-doc`), then the docless gate: the answer records its reason"
              if record["docless"] else "the scope doc's ledger is harvested; its decided lines pass forward and "
              "are never asked again")
    return driver.emit(ctx.envelope(
        next="record-answer", run_id=run.checkpoint["run_id"], reason=reason, docless=record["docless"],
        slug=slug, scope_doc=scope_path, target=record["target"]["path"],
        living_doc=None if not living else {"path": living["path"], "runs": living["runs"],
                                            "next_run": living["next_run"], "artifact_url": living["artifact_url"]},
        ledger=[{"id": r["id"], "tag": r["tag"], "text": r["text"], "source": r["source"]} for r in record["ledger"]],
        harvest=os.path.join(run.run_dir, "harvest.json")))


# ---- record-answer ------------------------------------------------------------------------------

def _context(run, prior=None):
    record = _load(run, "harvest.json")
    takes = _load(run, "takes.json") or []
    return recording.context(record, _living_text(run), session_id=_session(run), takes=takes, prior=prior,
                             run_id=run.checkpoint["run_id"])


def record_answer(ctx, args):
    run = ctx.open_run(args.run_dir)
    if _phase(run) in ("checked", "selected"):
        raise driver.Usage("run `harvest` before `record-answer`: the ledger is read before anything is asked")
    _need(run, "harvested", "answered", "written")
    try:
        answer = fsio.read_json(args.answer)
    except (OSError, ValueError) as exc:
        raise driver.Usage("the answer is not a readable JSON file: %s (%s)" % (args.answer, exc))
    errors = schema.errors(answer, ctx.skill_root)
    if errors:
        return driver.emit(ctx.envelope(ok=False, accepted=False, error="invalid", errors=errors,
                                        reason="the answer does not hold its schema (references/answer.schema.json): "
                                               "%d finding(s); nothing was written" % len(errors)), exits.VALIDATION)
    prior = _load(run, "answer.json") if _phase(run) == "written" else None
    refusals, plan = recording.evaluate(answer, _context(run, prior))
    if refusals:
        return driver.emit(ctx.envelope(accepted=False, refusals=refusals,
                                        reason="the recorded answer was refused on its content (%d refusal(s)); "
                                               "nothing was written, and a corrected answer can be recorded"
                                               % len(refusals)), exits.REFUSED)
    receipt = Receipt(run.run_dir)
    state = _state(run)
    if prior is not None:
        receipt.write_json(os.path.join(run.run_dir, "answer-round-%d.json" % state["round"]), prior)
    row = receipt.write_json(os.path.join(run.run_dir, "answer.json"), answer)
    if prior is not None or state["round"] == 0:
        state["round"] += 1
    run.checkpoint["phase"] = "answered"
    run.save()
    return driver.emit(ctx.envelope(accepted=True, refusals=[], answer=row["path"], sha256=row["sha256_after"],
                                    round=state["round"], amendment=prior is not None, next="write",
                                    doc=plan["doc_path"], run=plan["run"], passed_forward=plan["passed_forward"]))


# ---- write --------------------------------------------------------------------------------------

def _expected(run, receipt, path, record):
    """The hash the bytes at `path` must have before this run writes there."""
    last = receipt.last_after(path)
    if last is not False:
        return last
    if _report_only(run):
        return None
    living = record.get("living_doc")
    if living and living["path"] == path:
        return living["sha256"]
    return None


def write(ctx, args):
    run = ctx.open_run(args.run_dir)
    if _phase(run) == "written":
        raise driver.Usage("this run's doc is written; an amended answer (`record-answer`) comes before another write")
    if _phase(run) in ("checked", "selected", "harvested"):
        raise driver.Usage("run `record-answer` before `write`: the doc is rendered from an accepted answer")
    _need(run, "answered")
    answer = _load(run, "answer.json")
    record = _load(run, "harvest.json")
    state = _state(run)
    receipt = Receipt(run.run_dir)
    living_text = _living_text(run)
    artifact = state.get("publish_url") or (record.get("living_doc") or {}).get("artifact_url")
    plan = recording.plan(answer, record, living_text, _load(run, "takes.json") or [], artifact)
    real = plan["doc_path"]
    target = _preview(run, real)
    if plan["losses"]:
        return _stop(ctx, run, "write-refused", "the write would drop a protected line, so nothing was written: %s"
                     % "; ".join(plan["losses"]), _station_result(run, record, answer, None), receipt)
    try:
        receipt.write(target, plan["doc_text"], expect=_expected(run, receipt, target, record))
    except Changed as exc:
        return _stop(ctx, run, "document-changed", "%s. The living doc moved after this run read it; its bytes are "
                     "left as found. Start a new run on the doc as it stands." % exc,
                     _station_result(run, record, answer, None), receipt)
    state.update(doc=target, real_doc=real, rendered=False, visual=None, published=None)
    run.checkpoint["phase"] = "written"
    run.save()
    return driver.emit(ctx.envelope(next="render-visual", doc=target, run=plan["run"], report_only=_report_only(run),
                                    passed_forward=plan["passed_forward"],
                                    reason="the architecture doc was written%s" % (
                                        " to the run's preview folder (report-only)" if _report_only(run) else "")))


# ---- render-visual and record-publish -----------------------------------------------------------

def render_visual(ctx, args):
    run = ctx.open_run(args.run_dir)
    if _phase(run) != "written":
        raise driver.Usage("`render-visual` renders the doc this run wrote: run `write` first")
    _need(run, "written")
    state = _state(run)
    record = _load(run, "harvest.json")
    with open(state["doc"], "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    html_path = os.path.join(os.path.dirname(state["doc"]), "%s-architecture.html" % record["slug"])
    receipt = Receipt(run.run_dir)
    receipt.write(html_path, visual.render(text))
    state.update(rendered=True, visual=html_path, published=None)
    run.save()
    return driver.emit(ctx.envelope(next="record-publish", visual=html_path,
                                    reason="the visual was rendered beside the doc; publishing it is the "
                                           "executor's separate step, through the harness's own artifact tool"))


def record_publish(ctx, args):
    run = ctx.open_run(args.run_dir)
    _need(run, "written")
    state = _state(run)
    if not state.get("rendered"):
        raise driver.Usage("run `render-visual` after the last write, before `record-publish`")
    answer = _load(run, "answer.json")
    if args.url is not None and not answer["publish"]:
        raise driver.Usage("the answer says publish: false, so no URL is recorded")
    if args.url is not None and (blank(args.url) or not args.url.startswith("https://") or len(args.url.split()) != 1):
        raise driver.Usage("--url is the https URL the publish returned, one token: %r" % args.url)
    with open(state["doc"], "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    decision = publishing.decide(text, answer["publish"], args.url)
    if decision["refusal"]:
        return driver.emit(ctx.envelope(accepted=False, refusals=[decision["refusal"]],
                                        reason="the publish record was refused; nothing was written"), exits.REFUSED)
    receipt = Receipt(run.run_dir)
    if decision["changed"]:
        record = _load(run, "harvest.json")
        try:
            receipt.write(state["doc"], decision["text"], expect=_expected(run, receipt, state["doc"], record))
        except Changed as exc:
            return _stop(ctx, run, "document-changed", "%s. The doc moved after this run wrote it; its bytes are left "
                         "as found." % exc, _station_result(run, record, answer, None), receipt)
    receipt.write_json(os.path.join(run.run_dir, "publish.json"),
                       {"outcome": decision["outcome"], "url": decision["url"], "reason": decision["reason"]})
    state.update(published=decision["outcome"], publish_url=decision["url"] if decision["outcome"] == "published"
                 else state.get("publish_url"))
    run.save()
    return driver.emit(ctx.envelope(next="report", outcome=decision["outcome"], artifact_url=decision["url"],
                                    reason=decision["reason"]))


# ---- the blind review ---------------------------------------------------------------------------

def _review_ready(run):
    _need(run, "written")
    record = _load(run, "harvest.json")
    if record["docless"]:
        raise driver.Usage("a docless run makes no blind-review offer: there is no scope doc to send")
    return record


def request(ctx, args):
    run = ctx.open_run(args.run_dir)
    record = _review_ready(run)
    rows = []
    for row in args.row or []:
        if row not in rows:
            rows.append(row)
    if not rows:
        raise driver.Usage("name each reviewer the owner named with --row ROW")
    models = {}
    for item in args.model or []:
        if "=" not in item:
            raise driver.Usage("--model takes ROW=ID: %r" % item)
        row, ident = item.split("=", 1)
        models[row] = ident
    try:
        roster_path = args.roster or review.readers_roster(os.path.dirname(os.path.dirname(ctx.skill_root)))
        roster = readers_request.load_roster(roster_path)
    except (review.RosterMissing, OSError, ValueError) as exc:
        raise driver.Usage(str(exc))
    folder = os.path.join(run.run_dir, "requests")
    taken = [n[:-5] for n in os.listdir(folder)] if os.path.isdir(folder) else []
    try:
        built = review.requests(rows, run.input, roster, record["scope_doc"]["path"], run.checkpoint["run_id"],
                                session_model=args.session_model, models=models, taken=taken)
    except readers_request.RequestRefused as exc:
        raise driver.Usage(str(exc))
    receipt = Receipt(run.run_dir)
    out = []
    for call_id, req in built:
        path = os.path.join(folder, "%s.json" % call_id)
        receipt.write_json(path, req)
        out.append({"row": req["row"], "call_id": call_id, "path": path, "authorized": req.get("authorized") is True})
    return driver.emit(ctx.envelope(next="save-take", requests=out, mandate=review.MANDATE,
                                    reason="one readers request per named reviewer, the scope doc its single "
                                           "document; summon /readers with each, and save each take with save-take"))


def save_take(ctx, args):
    run = ctx.open_run(args.run_dir)
    record = _review_ready(run)
    state = _state(run)
    if not ROW.match(args.row or ""):
        raise driver.Usage("--row is a readers roster row id (lowercase letters, digits and '-'): %r" % args.row)
    for flag, value in (("--model", args.model), ("--isolation", args.isolation), ("--sidecar", args.sidecar)):
        if blank(value) or "\n" in value or "\r" in value:
            raise driver.Usage("%s is one line of text, as the readers result carries it: %r" % (flag, value))
    try:
        with open(args.take, "rb") as fh:
            body = fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise driver.Usage("the take is not a readable UTF-8 file: %s (%s)" % (args.take, exc))
    if not body.strip():
        return driver.emit(ctx.envelope(accepted=False, refusals=[{"rule": "take-empty", "message":
                                        "the take is empty; an empty reply is a failed review for that lane, and "
                                        "nothing is saved for it"}], reason="nothing was saved"), exits.REFUSED)
    real_doc = state.get("real_doc") or record["target"]["path"]
    home = "workspace" if inside(real_doc, run.input["workspace"]) else "staging"
    if _report_only(run):
        folder = os.path.join(run.run_dir, "reviews")
    elif home == "workspace":
        folder = os.path.join(run.input["workspace"], "docs", "reviews")
    else:
        folder = os.path.join(run.input["staging"], "architect-reviews")
    lane = review.lane_of(args.row)
    date = today()
    name = review.take_name(home, record["slug"], lane, date, folder)
    path = os.path.join(folder, name)
    text = review.take_text(args.row, args.model, args.isolation, args.sidecar, body)
    receipt = Receipt(run.run_dir)
    receipt.write(path, text, expect=None)
    copy = os.path.join(run.run_dir, "takes", name)
    if copy != path:
        receipt.write(copy, text)
    takes = _load(run, "takes.json") or []
    takes.append({"row": args.row, "lane": lane, "path": path, "copy": copy, "model": args.model,
                  "isolation": args.isolation, "sidecar": args.sidecar, "date": date})
    receipt.write_json(os.path.join(run.run_dir, "takes.json"), takes)
    return driver.emit(ctx.envelope(next="record-answer", path=path, copy=copy, lane=lane,
                                    reason="the take was saved verbatim before any triage; the review file is never "
                                           "edited. Walk the owner through each disagreement, then record the "
                                           "amended answer with the review's outcome and his rulings"))


# ---- report -------------------------------------------------------------------------------------

def _station_result(run, record, answer, state):
    sr = results.empty_station_result()
    if record:
        sr.update(slug=record["slug"], docless=record["docless"],
                  scope_doc=record["scope_doc"]["path"] if record["scope_doc"] else None)
    if answer:
        sr.update(project=answer["project"], candidates=[c["name"] for c in answer["candidates"]],
                  pick=answer["pick"], rulings_count=len(answer["rulings"]), review=answer["review"]["outcome"],
                  review_reason=answer["review"].get("reason"),
                  passed_forward=[r["id"] for r in docs.passed_forward(record["ledger"], answer)] if record else [])
    if state and state.get("doc"):
        with open(state["doc"], "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        living = (record or {}).get("living_doc")
        takes = _load(run, "takes.json") or []
        published = state.get("published")
        sr.update(doc_path=state["doc"], run_number=living["next_run"] if living else 1, visual_path=state.get("visual"),
                  published=published == "published", publish_outcome=published or ("skipped" if answer and not
                                                                                     answer["publish"] else "not-reached"),
                  artifact_url=docs.artifact_url(text), counts=docs.counts(text, answer["components"] if answer else []),
                  review_files=[display(t["path"], run.input["workspace"]) for t in takes])
    return sr


def report(ctx, args):
    run = ctx.open_run(args.run_dir)
    if _phase(run) in ("stopped", "reported"):
        doc = _load(run, "result.json")
        if doc is None:
            raise driver.Defect("the run ended without a result.json: %s" % run.run_dir)
        return driver.emit(dict(doc, next="done", chat=results.chat(doc),
                                result=os.path.join(run.run_dir, "result.json")), exits.TERMINAL)
    if _phase(run) != "written":
        raise driver.Usage("this run is at phase %r; `report` comes after `write`, `render-visual` and, when the "
                           "answer publishes, `record-publish`" % _phase(run))
    state = _state(run)
    answer = _load(run, "answer.json")
    record = _load(run, "harvest.json")
    if not state.get("rendered"):
        raise driver.Usage("run `render-visual` after the last write: every run ends with the visual rendered from "
                           "the doc as it stands")
    if answer["publish"] and state.get("published") is None:
        raise driver.Usage("the answer publishes: record the publish with `record-publish --url URL` (or without "
                           "--url when the publish returned none) before `report`")
    receipt = Receipt(run.run_dir)
    sr = _station_result(run, record, answer, state)
    outcome = answer["review"]["outcome"]
    if outcome == "pending":
        return _stop(ctx, run, "review-pending", "the blind-review offer has no outcome, so the doc's Blind review: "
                     "line still reads none yet; record the amended answer with the owner's answer (declined, "
                     "failed or done) and write again, or start a new run", sr, receipt)
    status, reason = publishing.status_after(sr["publish_outcome"])
    if sr["publish_outcome"] == "published":
        reason += " to %s" % sr["artifact_url"]
    if _report_only(run):
        reason = "report-only: " + reason + "; every write stayed in the run directory"
    doc = results.build(ctx.envelope(), run, status, None, reason, sr, receipt)
    results.write(doc, ctx.skill_root)
    run.checkpoint["phase"] = "reported"
    run.save()
    return driver.emit(dict(doc, next="done", chat=results.chat(doc), result=os.path.join(run.run_dir, "result.json")),
                       exits.TERMINAL)


HANDLERS = {"harvest": harvest, "record-answer": record_answer, "write": write, "report": report}

RUN_DIR = {"flags": ["--run-dir"], "metavar": "D", "required": True, "help": "the run directory"}
COMMANDS = [
    {"name": "render-visual", "help": "write <slug>-architecture.html beside the doc, from the doc (E14-6)",
     "arguments": [dict(RUN_DIR)], "handler": render_visual},
    {"name": "record-publish", "help": "record the publish: the Artifact: line from the URL it returned (E14-6)",
     "arguments": [dict(RUN_DIR), {"flags": ["--url"], "metavar": "URL", "default": None,
                                   "help": "the URL the executor's publish returned; omit when it returned none"}],
     "handler": record_publish},
    {"name": "request", "help": "build one readers request per named reviewer for the blind review",
     "arguments": [dict(RUN_DIR), {"flags": ["--row"], "metavar": "ROW", "action": "append",
                                   "help": "a readers roster row the owner named (repeatable)"},
                   {"flags": ["--session-model"], "metavar": "ID", "default": None,
                    "help": "the session's own model id, for the claude-session row only"},
                   {"flags": ["--model"], "metavar": "ROW=ID", "action": "append",
                    "help": "a model id the owner typed for a row (repeatable)"},
                   {"flags": ["--roster"], "metavar": "FILE", "default": None,
                    "help": "readers' roster.json (default: the readers component beside this core)"}],
     "handler": request},
    {"name": "save-take", "help": "save one reviewer's take verbatim, before any triage (-2, -3 on a repeat)",
     "arguments": [dict(RUN_DIR), {"flags": ["--row"], "metavar": "ROW", "required": True, "help": "the roster row"},
                   {"flags": ["--take"], "metavar": "FILE", "required": True, "help": "the reply's raw text"},
                   {"flags": ["--model"], "metavar": "ID", "required": True, "help": "the effective model"},
                   {"flags": ["--isolation"], "metavar": "LABEL", "required": True, "help": "the isolation label"},
                   {"flags": ["--sidecar"], "metavar": "PATH", "required": True, "help": "the readers sidecar path"}],
     "handler": save_take},
]
