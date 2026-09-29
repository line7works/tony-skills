"""`request`: one readers request per lens (contract section 6; the ask, section 2).

Before anything is built: every packet directory is held to the three-file rule (`packet.check_dir`,
exit 5 with the extra or changed file named, nothing built), and, when the ask displayed a model for
the row, the later `suggest` must show the same one (stop `model-changed` otherwise; the run waits
for the owner). Then each request is built by `station_core.readers_request.build`, the one place
`authorized` is decided (from the input's owner word, on an outside row only), with the fixed
mandates verbatim. The script builds and records; the executor summons readers.

The Claude lane is three calls, one fleet: traceability (build doc and the record), code book
(code book and build doc), both `packet-only`, and repo reality (the build doc, `repo` profile on
the workspace). An outside row is one paper call (the outside mandate with its three slots filled
from the packet, as its one document `packet.md`, kept outside the packet directory) plus the
repo-reality call as the Claude lane sends it, never both origins for one lens.
"""
import os

from station_core import driver, fsio, readers_request, validate

from . import common, mandates, packet as packetmod, readers_link, reporting

CLAUDE_ROW = "claude-session"
DOCS = {"traceability": ("build-doc.md", "RECORD"), "code-book": ("code-book.md", "build-doc.md"),
        "repo-reality": ("build-doc.md",)}


def _suggested_model(path, row):
    doc = common.load_json_file(path, "suggest")
    for entry in doc.get("suggestions") or []:
        if isinstance(entry, dict) and entry.get("row") == row:
            return entry.get("model")
    raise driver.Usage("the suggest file %s names no suggestion for the row %r" % (path, row))


def outside_packet(run, folder, call_id, record_name, references):
    """`packet.md`: v1's outside mandate with its three slots filled from the lens's packet."""
    with open(os.path.join(references, "inspect-mandate.md"), encoding="utf-8") as fh:
        body = fh.read()
    parts = {}
    for slot, name in zip(mandates.SLOTS, ("code-book.md", "build-doc.md", record_name)):
        with open(os.path.join(folder, name), encoding="utf-8") as fh:
            parts[slot] = fh.read().rstrip("\n")
    for slot in mandates.SLOTS:
        body = body.replace(slot, parts[slot])
    target = os.path.join(run.run_dir, "outside", call_id, "packet.md")
    fsio.atomic_write(target, (body.rstrip("\n") + "\n").encode("utf-8"))
    return target


def handler(ctx, args):
    """`request --run-dir D [--suggest FILE] [--readers-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("packeted",), "request")
    row = packetmod.row_of(run)
    st = common.station(run)
    pkt = common.read(run, "packet.json")
    refusals = []
    for entry in pkt["dirs"]:
        _, found = packetmod.check_dir(entry["dir"], pkt["no_record"], entry["sha256"])
        refusals.extend(found)
    if refusals:
        return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"], refusals=refusals,
                                     reason="the packet is refused (%d refusal(s)): it holds only the build doc, the "
                                            "record and the code book; nothing was built" % len(refusals)), 5)
    if st.get("displayed_model"):
        if not args.suggest:
            raise driver.Usage("the ask displayed %r for %s: pass --suggest with this run's later `readers suggest` "
                               "output so the send goes out under the model the owner saw" % (st["displayed_model"], row))
        shown = _suggested_model(args.suggest, row)
        if shown != st["displayed_model"]:
            reporting.finish(ctx, run, "stopped", "model-changed",
                             "the ask displayed %s for the row %s and this run's suggest now shows %s: show the owner "
                             "that line and wait for his word before anything is sent" % (st["displayed_model"], row, shown))
    found, roster = readers_link.load(common.plugin_root(), args.readers_root)
    harvest = common.read(run, "harvest.json")
    record_name = packetmod.NO_RECORD if pkt["no_record"] else packetmod.SCOPE
    run_id = run.input["run_id"]
    readers_dir = os.path.join(run.run_dir, "readers")
    calls = []
    for entry in pkt["dirs"]:
        lens, folder = entry["lens"], entry["dir"]
        if lens == "paper":
            call_row, call_id = row, "%s-%s" % (run_id, row)
            documents = [outside_packet(run, folder, call_id, record_name, validate.references_dir(ctx.skill_root))]
            mandate, profile, workspace = mandates.OUTSIDE_LINE, "packet-only", None
            raw_path = None
            if not common.report_only(run):
                raw_path = os.path.join(common.workspace(run), "docs", "reviews", "%s-inspect-%s-%s.md"
                                        % (common.now()[:10], harvest["feature"], common.lane_name(row)))
        else:
            call_row = row if lens != "repo-reality" or pkt["provider"] == common.ANTHROPIC else CLAUDE_ROW
            call_id = "%s-%s" % (run_id, lens)
            documents = [os.path.join(folder, record_name if n == "RECORD" else n) for n in DOCS[lens]]
            mandate = mandates.claude(lens)
            profile, workspace = ("repo", common.workspace(run)) if lens == "repo-reality" else ("packet-only", None)
            raw_path = None
        req = readers_request.build(call_row, run.input, roster, mandate=mandate, profile=profile, run_id=run_id,
                                    call_id=call_id, documents=documents, workspace=workspace,
                                    session_model=st.get("session_model"),
                                    model=st.get("model") if call_row == row else None,
                                    raw_path=raw_path, run_dir=readers_dir)
        path = os.path.join(run.run_dir, "requests", "%s.json" % call_id)
        fsio.write_json(path, req)
        calls.append({"lens": lens, "call_id": call_id, "row": call_row, "profile": profile,
                      "documents": [os.path.basename(d) for d in documents], "authorized": req.get("authorized") is True,
                      "request_file": path, "raw_path": raw_path})
    common.write(run, "requests.json", {"readers": found, "run_dir": readers_dir, "calls": calls})
    run.checkpoint["phase"] = "requested"
    run.save()
    return ctx.emit(ctx.envelope(next="record-answer", run_id=run_id, readers_run_dir=readers_dir, calls=calls,
                                 summon="summon /readers with these requests as one fleet under run id %s; then "
                                        "record the answer" % run_id))
