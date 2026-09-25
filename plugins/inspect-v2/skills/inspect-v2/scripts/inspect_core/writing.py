"""`write`: the two writes, both additive, and the verdict mirror (contract section 8; pick P8).

In this order, each step checked before the next:

1. **Checks before any write.** The build doc still holds the bytes `harvest` read (else stop
   `write-refused`, nothing written); the stamp, every QUESTION line and the clean line render
   through `station_core/templates.py` and parse back to themselves (else `write-refused`).
2. **The records** (only when a finding survived): one `finding_raised` event per surviving
   finding, `raised_by` the effective model of the call that found it, `slice` the slice whose
   section holds the cited build-doc line (`plan` for any other line), `source` the workspace's
   identity as the component computes it; appended through `records.py append` with
   `--expect-head` the head `harvest` pinned. A head that moved, or any other refusal, is the stop
   `records-refused` with the component's own sentence. Then `records.py render --run-id` gives the
   block text. The station never writes a finding line of its own, and never a clear.
3. **The build doc**, one atomic rewrite of insertions only: at the punch list's tail (the
   `## Punch list` section, created at the end when absent) the component's rendered text, then the
   station's QUESTION lines, or the clean line when there are no findings and no questions; and the
   stamp, placed by v1's rule: directly below the previous `Plan: inspected` line; else directly
   after the `Out of scope:` block (its line and the list lines continuing it); else directly
   above the first `## Slice` heading. A prior stamp is never rewritten.
4. **The banner** on each outside call's raw copy under `docs/reviews/` is already on: `record-answer`
   prepends it before any triage (`banner_raw_copies`, v1 Step 3) and its writes open the receipt.
5. **The verdict mirror** `docs/reviews/<date>-inspect-<feature>.md` (`-2`, `-3` on a same-day
   repeat, never an overwrite), holding the block's bytes, then `records.py mirrors` asked.

Every write is in `receipt.json` with its bytes' hash before and after (the log's hashes are the
component's to keep: the receipt names the log and the result carries the heads the component
reported). Report-only computes all of it and writes none of it: `write.json` says what would have
been written.
"""
import os
import re

from station_core import driver, fsio, records_link, templates
from station_core.records_client import RecordsRefusal

from . import common, reporting

D = "\u2014"
BANNER = ("Raw inspector output \u2014 unverified. Findings absent from the chat verdict were refuted or could not "
          "be verified. Nothing in this file has standing.")


def _refuse(ctx, run, reason, extra=None):
    doc = {"stamp": None, "stamp_written": False, "records": None, "mirror": None}
    doc.update(extra or {})
    common.write(run, "write.json", doc)
    reporting.finish(ctx, run, "stopped", "write-refused", reason)


def station_lines(triage, date, ctx, run):
    """(stamp, question lines, clean line or None), each rendered and parsed back."""
    counts = triage["counts"]
    model = triage["stamp_model"]
    stamp = templates.render_stamp(date, model, counts["blocker"], counts["major"], counts["minor"],
                                   counts["questions"])
    parsed = templates.parse_line(stamp)
    if not parsed or parsed["kind"] != "stamp" or parsed["model"] != model or templates.render_line(parsed) != stamp:
        _refuse(ctx, run, "the stamp %r does not read back as the stamp form; nothing was written" % stamp)
    questions = []
    for q in triage["questions"]:
        path, _, span = q["location"].rpartition(":")
        line = span.split("-")[0]   # the QUESTION form carries one line: a range is cited by its first
        text = templates.render_question(path, line, q["what"], q["model"])
        parsed = templates.parse_line(text)
        if not parsed or parsed["kind"] != "question" or templates.render_line(parsed) != text:
            _refuse(ctx, run, "the QUESTION line %r does not read back as its form; nothing was written" % text)
        questions.append(text)
    clean = None
    if not triage["findings"] and not triage["questions"]:
        clean = templates.render_clean(model)
        parsed = templates.parse_line(clean)
        if not parsed or parsed["kind"] != "clean":
            _refuse(ctx, run, "the clean line %r does not read back as its form; nothing was written" % clean)
    return stamp, questions, clean


def _fenced(lines):
    """Per line: True when it sits inside a fenced block (or is a fence)."""
    out, fence = [], None
    for raw in lines:
        line = raw.rstrip("\r\n")
        stripped = line.lstrip(" ")
        marker = stripped[:3] if stripped[:3] in ("```", "~~~") and len(line) - len(stripped) <= 3 else None
        if marker:
            out.append(True)
            fence = None if fence == marker[0] else (fence or marker[0])
            continue
        out.append(fence is not None)
    return out


def stamp_index(lines):
    """Where the stamp goes (v1's placement rule), as an index into `lines` to insert before: directly
    below the previous `Plan: inspected` line (any unfenced line that starts so, parsed strictly or
    not, so history reads top to bottom); else directly after the `Out of scope:` block (its line
    and the `- ` lines continuing it), looked for in every unfenced line above the first `## Slice`
    heading, a header section's included; else directly above the first `## Slice` heading."""
    fenced = _fenced(lines)
    body = [l.rstrip("\r\n") for l in lines]
    stamps = [i for i, l in enumerate(body) if not fenced[i] and l.startswith("Plan: inspected ")]
    if stamps:
        return stamps[-1] + 1
    first_slice = next((i for i, l in enumerate(body) if not fenced[i] and l.startswith("## Slice")), None)
    first_section = next((i for i, l in enumerate(body) if not fenced[i] and l.startswith("## ")), len(body))
    limit = first_slice if first_slice is not None else first_section
    oos = next((i for i in range(limit) if not fenced[i] and body[i].startswith("Out of scope:")), None)
    if oos is not None:
        at = oos + 1
        while at < limit and not fenced[at] and body[at].startswith("- "):
            at += 1
        return at
    return limit


def punch_tail(lines):
    """(index to insert at, whether the `## Punch list` heading must be created)."""
    fenced = _fenced(lines)
    body = [l.rstrip("\r\n") for l in lines]
    heading = next((i for i, l in enumerate(body) if not fenced[i] and l.rstrip() == "## Punch list"), None)
    if heading is None:
        return len(lines), True
    end = next((i for i in range(heading + 1, len(body)) if not fenced[i] and body[i].startswith("## ")), len(body))
    while end - 1 > heading and not body[end - 1].strip():
        end -= 1
    return end, False


def compose(text, render_text, own_lines, stamp):
    """The new document: insertions only, the original lines kept in order, byte for byte."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] = lines[-1] + nl
    tail, create = punch_tail(lines)
    chunk = render_text.replace("\n", nl) if render_text else ""
    if own_lines:
        joined = "".join(line + nl for line in own_lines)
        chunk = chunk + joined if chunk else nl + joined
    if create:
        chunk = nl + "## Punch list" + nl + chunk
    elif chunk and tail > 0 and not lines[tail - 1].strip() and chunk.startswith(nl):
        chunk = chunk[len(nl):]
    inserts = [(tail, chunk), (stamp_index(lines), stamp + nl)]
    for at, piece in sorted(inserts, key=lambda pair: pair[0], reverse=True):
        if piece:
            lines.insert(at, piece)
    return "".join(lines)


def _additive(before, after):
    """Every line of `before` is in `after`, in order: the write inserts and never changes a line."""
    it = iter(after.splitlines())
    return all(any(line == other for other in it) for line in before.splitlines())


def finding_events(triage, harvest, run, identity, at):
    events = []
    for f in triage["findings"]:
        path, _, line = f["location"].rpartition(":")
        start = line.split("-")[0]
        events.append({
            "v": 1, "kind": "finding_raised", "at": at, "ledger_doc": harvest["build_doc"]["rel"],
            "slice": f["slice"], "severity": f["severity"],
            "location": {"raw": f["location"], "file": path or None, "line": int(start) if start.isdigit() else None,
                         "line_end": int(line.split("-")[1]) if "-" in line and line.split("-")[1].isdigit() else None,
                         "tag": None, "more": [], "resolved": bool(path and start.isdigit())},
            "claim": f["claim"], "scenario": f["scenario"], "raised_by": f["raised_by"],
            "actor": records_link.actor(common.STATION, run.input["run_id"], run.input["invocation"].get("harness")),
            "origin": {"kind": "native"}, "source": {"known": True, "identity": identity}})
    return events


def _unique(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s-%d%s" % (base, n, ext)):
        n += 1
    return "%s-%d%s" % (base, n, ext)


def mirror_text(harvest, triage, date, render_text, own_lines, stamp):
    lines = ["# Inspect verdict: %s (%s)" % (harvest["build_doc"]["rel"], date), "",
             "Verdict: %s" % triage["verdict"],
             "Scope doc: %s" % (harvest["scope_doc"]["label"] if harvest.get("scope_doc") else
                                "none %s no-record rule applied" % D),
             "Refuted: %d" % triage["counts"]["refuted"],
             "Stamp: %s" % stamp]
    if triage.get("lenses_not_run"):
        lines.append("Lenses not run: %s (a short fleet: this run is weaker than a whole one)"
                     % ", ".join(triage["lenses_not_run"]))
    body = "\n".join(lines) + "\n"
    if render_text:
        body += render_text
    if own_lines:
        body += ("" if render_text else "\n") + "".join(line + "\n" for line in own_lines)
    body += "\nHunted and held: %s\n" % triage["hunted_and_held"]
    body += "Bottom line: %s\n" % triage["bottom_line"]
    return body


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _receipt(writes, path, kind, before, after):
    writes.append({"path": path, "kind": kind, "sha256_before": before, "sha256_after": after})


def handler(ctx, args):
    """`write --run-dir D`."""
    run = common.open_run(ctx, args.run_dir, ("answered",), "write")
    harvest = common.read(run, "harvest.json")
    triage = common.read(run, "triage.json")
    ws = common.workspace(run)
    at = common.now()
    date = at[:10]
    stamp, questions, clean = station_lines(triage, date, ctx, run)
    own = questions + ([clean] if clean else [])
    doc_path = harvest["build_doc"]["path"]
    rel = harvest["build_doc"]["rel"]
    mirror_path = _unique(os.path.join(ws, "docs", "reviews", "%s-inspect-%s.md" % (date, harvest["feature"])))
    if common.report_only(run):
        common.write(run, "write.json", {
            "report_only": True, "stamp": stamp, "stamp_written": False, "question_lines": questions,
            "clean_line": clean, "would_raise": triage["findings"], "would_mirror": mirror_path,
            "records": None, "mirror": None})
        common.write(run, "receipt.json", {"writes": []})
        run.checkpoint["phase"] = "written"
        run.save()
        return ctx.emit(ctx.envelope(next="report", run_id=run.input["run_id"], report_only=True, stamp=stamp,
                                     would_raise=len(triage["findings"]), wrote_nothing=True))
    before_bytes = _bytes(doc_path) if os.path.isfile(doc_path) else None
    if before_bytes is None or fsio.sha256_bytes(before_bytes) != harvest["build_doc"]["sha256"]:
        _refuse(ctx, run, "the build doc %s changed after `harvest` read it (an edit by hand, or another station): "
                          "nothing was written; run inspect-v2 again on the doc as it is now" % doc_path)
    text = before_bytes.decode("utf-8")
    client = records_link.open_client(common.STATION, records_root=args.records_root)
    # the banners `record-answer` put on the outside raw copies before any triage come first
    writes = list(common.read(run, "banner.json")["writes"]) if common.has(run, "banner.json") else []
    records = {"log": harvest["records"]["log"], "head_before": harvest["records"]["head"],
               "head_after": harvest["records"]["head"], "appended": 0}
    render_text = ""
    progress = run.checkpoint.setdefault("write_progress", {})
    if triage["findings"]:
        try:
            if not progress.get("appended"):
                identity = client.identity(ws)["identity"]
                events = finding_events(triage, harvest, run, identity, at)
                body = client.append(ws, rel, events, harvest["records"]["head"], run.run_dir)
                ids = [row.get("finding") for row in body.get("appended") or [] if row.get("kind") == "finding_raised"]
                progress["appended"] = {"head": body["head"], "log": body["log"], "findings": ids}
                run.save()
            records["head_after"] = progress["appended"]["head"]
            records["log"] = progress["appended"]["log"]
            records["appended"] = len(progress["appended"]["findings"])
            for f, fid in zip(triage["findings"], progress["appended"]["findings"]):
                f["finding_id"] = fid
            render_text = client.render(ws, rel, run.input["run_id"])["text"]
        except RecordsRefusal as refusal:
            common.write(run, "write.json", {"stamp": None, "stamp_written": False, "records": records,
                                             "mirror": None, "refused": refusal.body})
            reporting.finish(ctx, run, "stopped", "records-refused",
                             records_link.refusal_sentence(refusal, "raising the surviving findings"))
        _receipt(writes, os.path.join(ws, records["log"]), "records_log", None, None)
    after = compose(text, render_text, own, stamp)
    form_before = templates.check("build-doc", text)
    form_after = templates.check("build-doc", after)
    if not _additive(text, after) or (not form_before and form_after):
        _refuse(ctx, run, "the composed build doc would change a line or break the form (%s); nothing was written "
                          "to the doc" % (form_after[:2] or "a line would change"), {"records": records})
    fsio.atomic_write(doc_path, after.encode("utf-8"))
    _receipt(writes, doc_path, "document", fsio.sha256_bytes(before_bytes), fsio.sha256_file(doc_path))
    body = mirror_text(harvest, triage, date, render_text, own, stamp)
    fsio.atomic_write(mirror_path, body.encode("utf-8"))
    _receipt(writes, mirror_path, "document", None, fsio.sha256_file(mirror_path))
    mirror = {"path": mirror_path, "recognised": None, "state": None, "answer": None}
    try:
        answer = client.mirrors(ws, rel)
        mirror["answer"] = answer    # the component's answer, kept whole (contract section 15, point 2)
        rows = answer.get("mirrors") or []
        mine = [r for r in rows if r.get("verdict_doc") == os.path.relpath(mirror_path, ws)]
        mirror["recognised"] = bool(mine)
        mirror["state"] = mine[0]["state"] if mine else "not listed by `mirrors`"
    except RecordsRefusal as refusal:
        mirror["state"] = records_link.refusal_sentence(refusal, "asking `mirrors`")
    common.write(run, "receipt.json", {"writes": writes})
    common.write(run, "triage.json", triage)
    common.write(run, "write.json", {"stamp": stamp, "stamp_written": True, "question_lines": questions,
                                     "clean_line": clean, "records": records, "mirror": mirror,
                                     "render_text": render_text, "mirrors": mirror["state"]})
    run.checkpoint["phase"] = "written"
    run.save()
    return ctx.emit(ctx.envelope(next="report", run_id=run.input["run_id"], stamp=stamp, records=records,
                                 mirror=mirror, questions=questions, clean_line=clean))


def banner_raw_copies(run):
    """v1 Step 3: before any triage, the banner goes on top of each outside raw copy readers filed for
    this run, once, and on nothing else (`record-answer` calls this right after the answer is recorded,
    never in report-only). Returns the writes, each with its bytes' hash before and after."""
    writes = []
    for raw in _raw_copies(run, common.workspace(run)):
        data = _bytes(raw)
        if not data.decode("utf-8", "replace").startswith(BANNER):
            new = (BANNER + "\n\n").encode("utf-8") + data
            fsio.atomic_write(raw, new)
            _receipt(writes, raw, "document", fsio.sha256_bytes(data), fsio.sha256_bytes(new))
    return writes


def _raw_copies(run, ws):
    """The raw copies readers filed for this run's outside calls: a result's `raw_path` is taken only
    when it is the path the call's request named, or readers' `-2`, `-3` variant of it, and the file
    sits under `docs/reviews/`. Any other path is left alone: the banner goes on nothing else."""
    answer = common.read(run, "answer.json")
    named = dict((c["call_id"], c.get("raw_path")) for c in common.read(run, "requests.json")["calls"])
    reviews = os.path.join(ws, "docs", "reviews")
    out = []
    for result in answer.get("results") or []:
        path, want = result.get("raw_path"), named.get(result.get("call_id"))
        if not path or not want or not os.path.isfile(path) or not fsio.inside(path, reviews):
            continue
        base, ext = os.path.splitext(want)
        tail = path[len(base):-len(ext)] if path.startswith(base) and path.endswith(ext) else None
        if path == want or (tail and re.match(r"^-[2-9][0-9]*$", tail)):
            out.append(path)
    return out
