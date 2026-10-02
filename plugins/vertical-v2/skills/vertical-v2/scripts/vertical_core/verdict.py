"""`verdict` and `report`: the merge, `Refuted: N`, the ledger comparison, the one write, the
`VERTICAL:` block (contract sections 3.8 and 3.9; reading CR-8; v1's Steps 5 to 7).

The verified findings (CONFIRMED and PLAUSIBLE, local and outside alike) are deduped on file:line and
claim, each merged finding naming every reviewer that found it; a refuted finding is left out of the
verdict, counted, and visible only in the appendix's raw text. The verdict is the severity mapping over
the verified findings: any BLOCKER is REJECTED, else any MAJOR is SIGNED OFF WITH CONDITIONS, else
SIGNED OFF (arithmetic, not a judgment of code). The repeats and misses are read against the ledger
through the records component's `state` (read only; this core writes no event): a verified finding at a
ledger finding's file and line, or with its claim, is a repeat with the ledger's disposition; a ledger
finding marked fixed that no verified finding re-found is a miss for the executor to verify.

The one write is the verdict doc, `docs/reviews/<date>-vertical-<feature>.md`, found first by glob over
`docs/reviews/*-vertical-<feature>.md`: none, and this run creates it with today's date; one, and this run
appends one dated block at its end, every earlier byte untouched; several, and the run stops
(`verdict-doc-ambiguous`) with nothing written. A report-only run writes nothing. After the verdict the
archive copies and the staged packet files are removed from the run directory.
"""
import glob
import os
import re
import shutil

from station_core import driver, fsio, records_link

from . import ask as askmod, common, forms, report, sheet as sheetmod

SEVERITY_ORDER = ("BLOCKER", "MAJOR", "MINOR")


def _key(location, claim):
    return (location, re.sub(r"\s+", " ", claim.strip().lower()))


def _label(call):
    return "local:%s" % call["lens"] if call.get("lens") else call["row"]


def merge(local, outside):
    """(the verified findings merged, the refuted count)."""
    calls = dict((c["call_id"], c) for c in (local.get("calls") or []) + (outside.get("calls") or []))
    groups = {}
    order = []
    for f in (local.get("findings") or []) + (outside.get("findings") or []):
        key = _key(f["location"], f["claim"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(f)
    verified, refuted = [], 0
    for key in order:
        members = groups[key]
        kept = [m for m in members if m["stamp"] != "REFUTED"]
        if not kept:
            refuted += 1
            continue
        first = kept[0]
        reviewers = sorted(set(_label(calls[c]) for m in kept for c in m["found_by"] if c in calls))
        regrades = [m["regrade_reason"] for m in kept if m.get("regrade_reason")]
        verified.append({"severity": min((m["severity"] for m in kept), key=SEVERITY_ORDER.index),
                         "location": first["location"], "claim": first["claim"], "scenario": first["scenario"],
                         "reviewers": reviewers, "stamp": "CONFIRMED" if any(m["stamp"] == "CONFIRMED" for m in kept)
                         else "PLAUSIBLE", "regrade": "; ".join(regrades) or None})
    verified.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["location"]))
    return verified, refuted


def verdict_of(findings):
    severities = set(f["severity"] for f in findings)
    if "BLOCKER" in severities:
        return "REJECTED"
    if "MAJOR" in severities:
        return "SIGNED OFF WITH CONDITIONS"
    return "SIGNED OFF"


def _file_line(location):
    path, _, lines = location.rpartition(":")
    return path, int(lines.split("-")[0])


def ledger_comparison(run, ctx, doc, findings, records_root):
    """(repeats, misses) against the ledger's findings, read through `state`."""
    client = records_link.open_client(common.STATION, records_root=records_root)
    try:
        state = client.state(common.workspace(run), doc)
    except records_link.RecordsRefusal as refusal:
        report.finish(ctx, run, "stopped", "records-refused",
                      records_link.refusal_sentence(refusal, "reading the ledger for the repeats and misses"))
    ledger = state.get("findings") or []
    repeats, matched = [], set()
    for f in findings:
        path, line = _file_line(f["location"])
        for item in ledger:
            loc = item.get("location") or {}
            same_place = loc.get("file") == path and loc.get("line") == line
            same_claim = item.get("claim") and _key("", item["claim"]) == _key("", f["claim"])
            if same_place or (same_claim and loc.get("file") == path):
                matched.add(item["id"])
                repeats.append("%s %s (the ledger: %s, %s)" % (f["location"], f["claim"], item["status"],
                                                               loc.get("raw") or "no location"))
                break
    misses = ["%s %s (the ledger: fixed; verify it stayed fixed)" % ((i.get("location") or {}).get("raw") or "no location",
                                                                    i.get("claim") or "(no claim)")
              for i in ledger if i.get("status") == "fixed" and i["id"] not in matched]
    return repeats, misses


def method_lines(run, gate, scope, ask, local, outside):
    base = gate["base"]
    how = {"doc": "the build doc's %s" % base.get("field"), "merge-base": base.get("field"),
           "owner": "the owner's words: \"%s\"" % base.get("words")}[base["how"]]
    out = ["Base: %s (%s)" % (base["commit"], how),
           "Head: %s; boundary: %d files" % (gate["head"], len(gate["boundary"])),
           "Run: %s" % run.checkpoint["run_id"]]
    sources = sorted(set(s["card_source"] for s in gate["slices"]))
    if gate.get("collapse"):
        out.append("Gate: collapsed by the owner's words: \"%s\" (short: %s)"
                   % (gate["collapse"]["words"], ", ".join("%s %s" % (s["name"], s["state"]) for s in gate["collapse"]["short"])))
    else:
        out.append("Gate: every slice signed off (cards from %s)" % " and ".join(
            {"records": "the records component", "status-line": "the Status: lines, no log events"}[s] for s in sources))
    for item in gate["slices"]:
        # the owner's ruling (E15 lane contract A3, C1A-2): a derived card that differs never stops the gate;
        # the slice is named here with both cards
        if item.get("card_source") == "records" and item.get("card_derived") and item["card_derived"] != item["card"]:
            out.append("Card: slice %s: the observed card %r (the card the gate compares with its Status: line) and "
                       "the records component's derived card %r differ" % (item["name"], item["card"],
                                                                          item["card_derived"]))
    dirt = gate.get("dirt") or {"inside": [], "outside": []}
    if gate.get("committed_only"):
        out.append("Tree: committed state only, by the owner's words: \"%s\" (dirt in the boundary: %s)"
                   % (gate["committed_only"]["words"], ", ".join(dirt["inside"])))
    elif dirt["outside"]:
        out.append("Tree: clean where the review looks; unrelated dirt, reviewed at HEAD: %s" % ", ".join(dirt["outside"]))
    else:
        out.append("Tree: clean")
    out.append("Depth: %s; lenses: %s" % (scope["depth"], ", ".join(scope["lenses"])))
    for call in local.get("calls") or []:
        out.append("Local: %s %s %s %s %s %s %s" % (call["lens"], forms.M, call["row"], forms.M, call["model"] or "none",
                                                   forms.M, call["profile"] or "none")
                   + ("" if call["status"] == "ok" else " %s %s, re-sent" % (forms.M, call["status"])))
    local_row = [r for r in ask["rows"] if r["side"] == "local"][0]
    if local_row["profile"] == "repo":
        out.append("Route: the local lenses ran through %s with profile repo: each read the code and ran no check "
                   "(static analysis only)" % local_row["row"])
    left = dict((p["row"], p["left_out"]) for p in scope["packets"] if p["side"] == "outside")
    dropped = ["%s %s %s %s %s" % (d["row"], forms.M, d["status"], forms.M, d["reason"]) for d in askmod.dropped_named(ask)]
    for call in outside.get("calls") or []:
        if call["status"] != "ok":
            dropped.append("%s %s %s %s %s" % (call["row"], forms.M, call["status"], forms.M,
                                               call["reason"] or "no reason given"))
            continue
        line = "Outside: %s %s %s %s %s %s parity: %s %s isolation: %s" % (
            call["row"], forms.M, call["model"] or "none", forms.M,
            "packet-only (no workspace)" if call["profile"] == "packet-only" else call["profile"], forms.M,
            call["parity"] or "none", forms.M, call["isolation"] or "none")
        if call.get("reason"):
            line += " %s anomaly: %s" % (forms.M, call["reason"])
        if left.get(call["row"]):
            line += " %s left out: %s" % (forms.M, ", ".join(left[call["row"]]))
        out.append(line)
    out += ["Dropped: %s" % d for d in dropped] or ["Dropped: none"]
    out.append("Verification: %s" % local["method"])
    out.append("Withheld from every packet: the prior verdicts, the records log, the builder's notes, the build doc's "
               "ledger (punch list, handoffs, Status: lines) and the builder's working records (build assumptions, "
               "deviations, discovered), and every untracked, ignored or changed working-tree file; REVIEW.md reached "
               "the local lenses only; no packet or workspace carried git history")
    return [one.replace("\n", " ") for one in out]


def _appendix(run, records):
    out = []
    for call in records:
        if call["status"] != "ok" or not call.get("raw_file"):
            continue
        with open(call["raw_file"], "rb") as fh:
            data = fh.read()
        if call.get("raw_hash") and fsio.sha256_bytes(data) != call["raw_hash"]:
            raise driver.Defect("the raw file of %s no longer matches readers' hash" % call["call_id"])
        out.append({"label": "%s (%s)" % (call["call_id"], call["row"]), "raw": data.decode("utf-8", "replace")})
    return out


def handler(ctx, args):
    """`verdict --run-dir D [--records-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("recorded-local", "recorded-outside"), "verdict")
    ask = common.read(run, "ask.json")
    if run.checkpoint["phase"] == "recorded-local" and ask["answer"]["rows"]:
        raise driver.Usage("the owner named outside rows (%s): run `request --outside` and record-outside before the "
                           "verdict" % ", ".join(ask["answer"]["rows"]))
    gate = common.read(run, "gate.json")
    scope = common.read(run, "scope.json")
    local = common.read(run, "local.json")
    outside = common.read(run, "outside.json") if common.has(run, "outside.json") else {}
    findings, refuted = merge(local, outside)
    repeats, misses = ledger_comparison(run, ctx, gate["doc"], findings, args.records_root)
    sheet = scope["review_sheet"]
    sheet_lines = ["skipped: %s (%s)" % (s["pass"], s["reason"]) for s in sheet["skipped"]]
    sheet_lines += ["check tried: %s" % c for c in sheet["checks"]]
    method = method_lines(run, gate, scope, ask, local, outside)
    fields = {"date": common.date_of(run), "run_id": run.checkpoint["run_id"], "verdict": verdict_of(findings),
              "refuted": refuted, "findings": findings, "repeats": repeats, "misses": misses,
              "ledger_notes": outside.get("ledger_notes"), "review_line": sheetmod.line(dict(sheet, passes=[])),
              "sheet_lines": sheet_lines, "method": method,
              "appendix": _appendix(run, (local.get("calls") or []) + (outside.get("calls") or []))}
    block = forms.render_block(fields)
    ws = common.workspace(run)
    feature = gate["feature"]
    hits = sorted(glob.glob(os.path.join(glob.escape(ws), "docs", "reviews", "*-vertical-%s.md" % glob.escape(feature))))
    if len(hits) > 1:
        report.finish(ctx, run, "stopped", "verdict-doc-ambiguous",
                      "several verdict docs exist for this build (%s): one file per build; the owner says which one "
                      "is the build's, and nothing was written" % ", ".join(os.path.relpath(h, ws) for h in hits))
    target = hits[0] if hits else os.path.join(ws, "docs", "reviews", "%s-vertical-%s.md" % (fields["date"], feature))
    real_reviews = os.path.realpath(os.path.join(ws, "docs", "reviews"))
    if os.path.islink(target) or not os.path.realpath(os.path.dirname(target)) == real_reviews or \
            not real_reviews.startswith(os.path.realpath(ws).rstrip(os.sep) + os.sep):
        report.finish(ctx, run, "stopped", "write-refused",
                      "the verdict doc's place is not a plain file under the workspace's docs/reviews/: %s" % target)
    writes = []
    rel = os.path.relpath(target, ws)
    if not common.report_only(run):
        before_bytes = None
        if os.path.isfile(target):
            with open(target, "rb") as fh:
                before_bytes = fh.read()
            text = forms.append(before_bytes.decode("utf-8"), block)
        else:
            text = forms.new_doc(feature, block)
        data = text.encode("utf-8")
        if before_bytes is not None and not data.startswith(before_bytes):
            report.finish(ctx, run, "stopped", "write-refused", "the append would change an earlier block")
        fsio.atomic_write(target, data)
        writes.append({"path": target, "kind": "document",
                       "sha256_before": fsio.sha256_bytes(before_bytes) if before_bytes is not None else None,
                       "sha256_after": fsio.sha256_bytes(data)})
    for name in ("export", "local"):
        shutil.rmtree(common.path_of(run, name), ignore_errors=True)
    for packet in scope["packets"]:
        staged = os.path.join(packet["dir"], "files")
        if os.path.isdir(staged):
            shutil.rmtree(staged, ignore_errors=True)
    common.write(run, "verdict.json", {"verdict": fields["verdict"], "findings_count": len(findings),
                                       "refuted": refuted, "findings": findings, "repeats": repeats, "misses": misses,
                                       "doc": None if common.report_only(run) else rel, "would_write": rel,
                                       "writes": writes, "method": method, "block": block,
                                       "review_line": fields["review_line"]})
    common.advance(run, "verdict-written")
    return ctx.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], verdict=fields["verdict"],
                                 findings=len(findings), refuted=refuted,
                                 doc=None if common.report_only(run) else rel, report_only=common.report_only(run)))


def report_handler(ctx, args):
    """`report --run-dir D --bottom-line TEXT [--skill-note TEXT]`."""
    run = common.open_run(ctx, args.run_dir, ("verdict-written",), "report")
    if common.blank(args.bottom_line) or "\n" in args.bottom_line:
        raise driver.Usage("report needs --bottom-line: two or three sentences on one line, the build's state and "
                           "what to do next")
    gate = common.read(run, "gate.json")
    verdict = common.read(run, "verdict.json")
    outside = common.read(run, "outside.json") if common.has(run, "outside.json") else {}
    calls = outside.get("calls") or []
    dropped = [{"row": d["row"], "why": "%s (%s)" % (d["status"], d["reason"])}
               for d in askmod.dropped_named(common.read(run, "ask.json"))]
    dropped += [{"row": c["row"], "why": "%s (%s)" % (c["status"], c["reason"] or "no reason given")}
                for c in calls if c["status"] != "ok"]
    fields = {"doc": gate["doc"], "base": gate["base"]["commit"], "head": gate["head"], "verdict": verdict["verdict"],
              "reviewers": [c["row"] for c in calls if c["status"] == "ok"],
              "dropped": dropped,
              "refuted": verdict["refuted"],
              "verdict_doc": verdict["doc"] or "none (report-only: nothing written)",
              "review_line": verdict["review_line"], "bottom_line": args.bottom_line,
              "skill_note": args.skill_note or None}
    text = forms.render_vertical(fields)
    fsio.atomic_write(common.path_of(run, "chat.md"), text.encode("utf-8"))
    reason = ("the verdict is %s; %s" % (verdict["verdict"], "the verdict doc is %s" % verdict["doc"] if verdict["doc"]
                                         else "report-only: nothing was written"))
    report.finish(ctx, run, "completed", None, reason, extra={"chat": text})
