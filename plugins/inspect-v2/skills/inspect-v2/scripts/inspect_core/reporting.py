"""`report` and every terminal stop: the result, validated, and the chat block (contract section 9).

`finish` is the one way a run ends: it assembles the result from the run's artifacts, validates it
against `references/result.schema.json` and the semantic checks S1 to S4, writes `result.json`,
marks the checkpoint `done`, and raises the driver's `Terminal` (exit 10) with the result, the chat
block and `next: done`. A stop at any phase goes through it, so every run ends in a terminal status
with its result on disk.
"""
import os

from station_core import driver, fsio, validate

from . import common

D = "\u2014"
M = "·"
SKIP_DIRS = ("readers",)   # readers' own run directory: its writes, not this core's


def _artifact(run, name):
    return common.read(run, name) if common.has(run, name) else None


def run_writes(run):
    """Every file this core wrote in the run directory (readers' own subtree left out)."""
    out = []
    for base, dirs, files in os.walk(run.run_dir):
        rel_base = os.path.relpath(base, run.run_dir)
        dirs[:] = sorted(d for d in dirs if not (rel_base == "." and d in SKIP_DIRS))
        for name in sorted(files):
            full = os.path.join(base, name)
            if rel_base == "." and name == "result.json":
                continue
            out.append({"path": full, "kind": "run_artifact", "sha256_before": None,
                        "sha256_after": fsio.sha256_file_or_none(full)})
    return out


def _selection(run):
    out = {}
    for hunt in ("build", "scope"):
        doc = _artifact(run, "selection-%s.json" % hunt)
        if doc is not None:
            out[hunt] = doc
    return out


def station_result(run, stopped):
    harvest = _artifact(run, "harvest.json") or {}
    packet = _artifact(run, "packet.json") or {}
    requests = _artifact(run, "requests.json") or {}
    triage = _artifact(run, "triage.json") or {}
    wrote = _artifact(run, "write.json") or {}
    sr = {}
    if harvest:
        sr["build_doc"] = harvest["build_doc"]["path"]
        sr["scope_doc"] = harvest["scope_doc"]["path"] if harvest.get("scope_doc") else None
        sr["no_record"] = harvest["no_record"]
        sr["weaker"] = harvest["no_record"]
        sr["code_book"] = {"path": harvest["code_book"]["path"], "route": harvest["code_book"]["route"]}
        sr["construction_started"] = list(harvest.get("construction_started") or [])
    if packet:
        sr["packet"] = [{"lens": d["lens"], "dir": d["dir"], "files": d["files"]} for d in packet["dirs"]]
    if requests:
        sr["requests"] = [{"lens": c["lens"], "call_id": c["call_id"], "row": c["row"], "profile": c["profile"],
                           "documents": c["documents"], "authorized": c["authorized"]} for c in requests["calls"]]
    if triage:
        for key in ("counts", "verdict", "findings", "questions", "refuted", "calls", "lenses_not_run",
                    "hunted_and_held", "bottom_line", "weaker"):
            if key in triage:
                sr[key] = triage[key]
    stamp_written = bool(wrote.get("stamp_written"))
    sr["stamp"] = wrote.get("stamp") if wrote else None
    sr["stamp_written"] = stamp_written
    if wrote:
        sr["records"] = wrote.get("records")
        sr["mirror"] = wrote.get("mirror")
    if not stopped:
        for key, default in (("records", None), ("mirror", None)):
            sr.setdefault(key, default)
    return sr


def chat_block(run, result):
    """v1's read-back, rendered from the result (the form is v1's, its dashes included)."""
    sr = result.get("station_result") or {}
    doc = sr.get("build_doc") or "(no build doc selected)"
    lines = ["INSPECT: %s" % doc]
    selected = selected_line(run, result)
    if selected:
        lines.append(selected)
    if result["status"] == "stopped":
        lines.append("Stopped: %s" % result["stop_tag"])
        lines.append("Reason: %s" % result["reason"])
        if sr.get("stamp_written") is False:
            lines.append("Stamp: none written")
        lines.append("Next: %s" % _next_after_stop(result["stop_tag"]))
        return "\n".join(lines) + "\n"
    counts = sr["counts"]
    calls = sr.get("calls") or []
    paper = [c for c in calls if c["lens"] in common.PAPER_LENSES]
    row = paper[0]["row"] if paper else (calls[0]["row"] if calls else "none")
    model = _stamp_model(sr)
    isolation = _isolation(run, paper)
    scope = sr["scope_doc"] if sr.get("scope_doc") else "none %s no-record rule applied" % D
    lines.append("Verdict: %s" % sr["verdict"])
    lines.append("Inspector: %s %s %s %s %s  %s  Scope doc: %s  %s  Refuted: %d"
                 % (row, M, model, M, isolation, M, scope, M, counts["refuted"]))
    lines.append("Raw: %s" % _raw_line(run))
    lines.append("Findings: %d BLOCKER %s %d MAJOR %s %d MINOR" % (counts["blocker"], M, counts["major"], M,
                                                                    counts["minor"]))
    lines.append("")
    lines.append("Bottom line: %s" % sr["bottom_line"])
    lines.append("")
    for severity, head in (("BLOCKER", "BLOCKERS"), ("MAJOR", "MAJOR"), ("MINOR", "MINOR")):
        rows = [f for f in sr["findings"] if f["severity"] == severity]
        for index, f in enumerate(rows):
            lines.append("%-10s %s %s %s %s %s %s %s %s %s" % (head if index == 0 else "", f["severity"], M,
                                                            f["location"], M, f["claim"], M, f["scenario"], M, f["label"]))
    if sr["questions"]:
        lines.append("Questions: %s" % "; ".join("%s %s %s" % (q["location"], M, q["what"]) for q in sr["questions"]))
    if sr.get("weaker"):
        lines.append("Record: no scope doc exists for this feature, so this run is weaker: untraceable items are "
                     "questions for the owner, never blockers (the no-record rule).")
    if sr.get("construction_started"):
        lines.append("Note: construction already started on slice %s." % ", ".join(sr["construction_started"]))
    lines.append("Hunted and held: %s" % sr["hunted_and_held"])
    if sr["verdict"] == "APPROVED":
        lines.append("Next: build-v2 when ready.")
    else:
        lines.append("Next: the owner adjudicates the findings, the drafting session amends the doc on his word, "
                     "then a fresh inspect-v2 run.")
    return "\n".join(lines) + "\n"


def selected_line(run, result):
    """v1 Step 1: the verdict says which doc it took. How the build doc was taken (the one candidate of
    its home's tier, the executor's Intent match, the owner's pick, or named by the invocation), and
    every doc another tier matched by filename that the lower tier outranked. None before `harvest`."""
    harvest = _artifact(run, "harvest.json")
    build = (result.get("selection") or {}).get("build")
    if not harvest or not build:
        return None
    ws = run.input["workspace"]
    taken = harvest["build_doc"]["path"]
    how = harvest["build_doc"].get("how")
    home = next((c for c in build.get("candidates") or [] if os.path.normpath(c["path"]) == os.path.normpath(taken)),
                {"home": "unknown", "tier": 0})
    where = os.path.dirname(harvest["build_doc"]["rel"]).replace(os.sep, "/")
    words = {"one": "the one doc its tier holds", "named": "named by the invocation",
             "chosen by intent": "matched by its Intent: line", "chosen by owner": "the owner's pick"}
    line = "Selected: %s/ (tier %d, %s), %s" % (where or ".", home.get("tier", 0), home.get("home"),
                                                words.get(how, how))
    others = []
    for row in build.get("searched") or []:
        if row.get("tier", 0) > home.get("tier", 0):
            others.extend("%s (tier %d, %s)" % (os.path.relpath(p, ws), row["tier"], row["home"])
                          for p in row.get("found") or [])
    if others:
        line += "; also matched by filename, outranked by the lower tier: %s" % ", ".join(others)
    return line


def _stamp_model(sr):
    stamp = sr.get("stamp") or ""
    marker = " by "
    if marker in stamp:
        return stamp.split(marker, 1)[1].split(" ", 1)[0]
    return "none"


def _isolation(run, paper):
    answer = _artifact(run, "answer.json") or {}
    wanted = set(c["call_id"] for c in paper)
    for result in answer.get("results") or []:
        if result.get("call_id") in wanted and result.get("isolation"):
            return result["isolation"]
    return "isolation not recorded"


def _raw_paths(run):
    """The outside raw copies the chat names (round 4, R1): per outside call, the member of the request's
    same-day family the result names when that member exists, else every existing member, so an earlier
    run's copy is never listed as this run's when the result names this run's."""
    out = []
    for family in common.raw_families(run, run.input["workspace"]):
        members = family["members"]
        picks = [family["named"]] if family["named"] in members else members
        for path in picks:
            if path not in out:
                out.append(path)
    return out


def _raw_line(run):
    """`Raw:` of the chat block: the real raw paths for an outside lane; `n/a` only for the Claude lane."""
    raw = _raw_paths(run)
    if raw:
        return ", ".join(raw)
    packet = _artifact(run, "packet.json") or {}
    if packet.get("provider") in (None, common.ANTHROPIC):
        return "n/a %s Claude lane" % D
    if common.report_only(run):
        return "none: a report-only run files no raw copy"
    wanted = [c["raw_path"] for c in (_artifact(run, "requests.json") or {}).get("calls") or [] if c.get("raw_path")]
    return "none: readers filed no raw copy at %s" % (", ".join(wanted) or "the request's raw_path")


def _next_after_stop(tag):
    return {
        "selection-none": "nothing to inspect: write the plan with blueprint-v2, then run inspect-v2 again.",
        "selection-several": "put the listed candidates to the owner, then a fresh run with `choose`.",
        "lane-down": "re-ask the owner which lane to run; the lane he names runs as a fresh run.",
        "model-changed": "show the owner the model the row would send now and wait for his word.",
        "no-effective-model": "no stamp is written; a fresh run once the reader's model can be read.",
        "records-refused": "read the component's sentence; nothing here repairs the log.",
        "write-refused": "nothing was written; read the reason, then a fresh run.",
    }.get(tag, "read the reason; nothing further runs in this run.")


def assemble(ctx, run, status, stop_tag, reason):
    # the receipt of `write`, which opens with the banner writes; a run that stopped before `write`
    # still names the banners `record-answer` wrote
    receipt = _artifact(run, "receipt.json") or _artifact(run, "banner.json") or {"writes": []}
    writes = run_writes(run) + list(receipt["writes"])
    outside = [w for w in writes if not _under(w["path"], run.run_dir)]
    result = {"interface_version": driver.INTERFACE_VERSION, "plugin_version": validate.plugin_version(ctx.skill_root),
              "station": common.STATION, "run_id": run.input["run_id"], "run_dir": run.run_dir,
              "status": status, "stop_tag": stop_tag, "reason": reason,
              "report_only": common.report_only(run), "wrote_nothing": not outside, "writes": writes,
              "selection": _selection(run), "invocation": run.input["invocation"]}
    sr = station_result(run, status == "stopped")
    result["station_result"] = sr
    sr["chat"] = "(pending)"
    sr["chat"] = chat_block(run, result)
    return result


def _under(path, root):
    a, b = os.path.normpath(path), os.path.normpath(root)
    return a == b or a.startswith(b.rstrip(os.sep) + os.sep)


def check(ctx, result):
    schema = ctx_schema(ctx)
    errors = validate.errors_for(result, schema, ctx.prefix)
    semantic = validate.semantic(result) if not errors else []
    if errors or semantic:
        raise driver.Defect("the result this run assembled does not validate (a defect of the script): %s"
                            % (errors or semantic)[:3])


def ctx_schema(ctx):
    return validate.load_schema("result", ctx.prefix, ctx.skill_root)


def finish(ctx, run, status, stop_tag, reason):
    """End the run: the result assembled, validated, written; the checkpoint `done`; exit 10."""
    result = assemble(ctx, run, status, stop_tag, reason)
    check(ctx, result)
    path = common.write(run, "result.json", result)
    run.checkpoint["phase"] = "done"
    run.checkpoint["status"] = status
    run.save()
    raise driver.Terminal(emitted(ctx, result, path))


def emitted(ctx, result, path):
    doc = dict(result)
    doc["next"] = "done"
    doc["result_file"] = path
    doc["chat"] = result["station_result"]["chat"]
    return doc


def handler(ctx, args):
    """`report --run-dir D`: the result of a run that wrote; a finished run's result printed again."""
    run = common.open_run(ctx, args.run_dir, ("written", "done"), "report")
    if run.checkpoint["phase"] == "done":
        result = common.read(run, "result.json")
        raise driver.Terminal(emitted(ctx, result, common.path_of(run, "result.json")))
    wrote = common.read(run, "write.json")
    triage = common.read(run, "triage.json")
    if common.report_only(run):
        reason = ("report-only: the plan was inspected and nothing was written; the verdict would be %s, "
                  "%d finding(s) would be raised and the stamp would read %r"
                  % (triage["verdict"], len(triage["findings"]), wrote.get("stamp")))
    else:
        reason = ("the plan was inspected: %s; %d finding(s) raised in the records, %d question(s), %d refuted; "
                  "the stamp was written" % (triage["verdict"], len(triage["findings"]), len(triage["questions"]),
                                             triage["counts"]["refuted"]))
    finish(ctx, run, "completed", None, reason)
