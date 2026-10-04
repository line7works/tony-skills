"""`photograph` (contract section 3.2; CR-11): the record, read by the script now, never from the session's memory.

Every card and the open set come from the records component's `state` for the build doc (the latest-record rule the
component implements; never recomputed by hand): a slice's card is its `card_observed` when the log observed or set
one, else its `Status:` line as the line rules read it, and the photograph says which. The branch, the commits ahead
of the default branch, the tree state and the HEAD commit come from read-only git; the last-recorded suite state
comes from the record the executor names (`--suite-record`, a build-v2 result read with its provenance), else "none
recorded". No test suite is ever run. Before any of that: the doc must still hold the bytes `select` read, and every
handoff block the doc held at HEAD must be unchanged in the working copy (`block-edited`). Writes `photograph.json`
in the run directory and nothing else.
"""
import datetime
import os

from station_core import driver, fsio, records_link

from . import common, doc as docmod, gitio, nextmove, report


def _moved(ctx, run, what):
    report.finish(ctx, run, "stopped", "photograph-moved",
                  "%s since this run read it: the photograph is read once, now, and the run never writes from a "
                  "record that moved under it; nothing was written. Run handoff again" % what)


def blocks_edited(ws, commit, doc_rel, current):
    """The first handoff block the doc held at `commit` that the current reading does not hold byte for byte, in
    order, as (its line at the commit, its date), or None. A doc the commit does not hold, or that the line rules
    refuse there, has no baseline (None)."""
    data = gitio.show(ws, commit, doc_rel)
    if data is None:
        return None
    try:
        then = docmod.read(data.decode("utf-8"))
    except (UnicodeDecodeError, docmod.DocUnreadable):
        return None
    earlier = [docmod.block_text(then, b) for b in then.blocks]
    now = [docmod.block_text(current, b) for b in current.blocks]
    for index, text in enumerate(earlier):
        if index >= len(now) or now[index] != text:
            return then.blocks[index]["line"], then.blocks[index]["date"]
    return None


def suite_of(path):
    if path is None:
        return {"state": "none recorded", "provenance": None, "path": None, "sha256": None}
    if not os.path.isfile(path):
        raise driver.Usage("no such suite record: %s" % path)
    real = os.path.realpath(path)
    stamp = datetime.datetime.utcfromtimestamp(os.stat(real).st_mtime).replace(microsecond=0).isoformat() + "Z"
    digest = fsio.sha256_file(real)
    try:
        body = fsio.read_json(real)
    except (OSError, ValueError, UnicodeDecodeError):
        body = None
    checks = body.get("checks") if isinstance(body, dict) else None
    if isinstance(checks, list) and isinstance(body.get("run_id"), str) and all(isinstance(c, dict) for c in checks):
        counts = {"passed": 0, "failing": 0, "not_run": 0}
        for check in checks:
            if check.get("result") in counts:
                counts[check["result"]] += 1
        state = "%d passed, %d failing, %d not run" % (counts["passed"], counts["failing"], counts["not_run"])
        provenance = "build-v2 run %s%s, result %s, %s" % (body["run_id"], ", slice %s" % body["slice"]
                                                          if isinstance(body.get("slice"), str) else "", real, stamp)
    else:
        state = "recorded at %s, not read as a suite state (not a build-v2 result)" % real
        provenance = "%s, %s" % (real, stamp)
    return {"state": state, "provenance": provenance, "path": real, "sha256": digest}


def repo_of(ws):
    head = gitio.head(ws)
    ref, base = gitio.default_branch(ws)
    dirt = gitio.dirt(ws)
    return {"branch": gitio.branch(ws), "head": head, "base": base, "ahead": gitio.ahead(ws, ref) if ref else None,
            "tree": "clean" if not dirt else "dirty", "dirt": dirt, "checkpoint": None}


def cards_of(doc_view, state):
    rows = dict((row["name"], row) for row in state.get("slices") or [])
    out = []
    for item in doc_view["slices"]:
        row = rows.get(item["name"])
        if row is not None and row.get("card_observed") is not None:
            card = row["card_observed"] if row["card_observed"] != "none" else row.get("card_observed_text")
            out.append({"name": item["name"], "card": card, "source": "records", "status_line": item["status"],
                        "card_derived": row.get("card_derived")})
        else:
            out.append({"name": item["name"], "card": item["status"] or "none", "source": "status-line",
                        "status_line": item["status"], "card_derived": None})
    return out


def findings_of(state):
    return [{"id": f["id"], "slice": f["slice"], "severity": f["severity"], "status": f["status"],
             "location": f["location"]["raw"], "claim": f["claim"]} for f in state.get("findings") or []]


def read_records(ctx, run, ws, doc_rel, records_root, what):
    client = records_link.open_client(common.STATION, records_root=records_root)
    try:
        return client, client.state(ws, doc_rel)
    except records_link.RecordsRefusal as refusal:
        report.finish(ctx, run, "stopped", "records-refused", records_link.refusal_sentence(refusal, what))


def handler(ctx, args):
    """`photograph --run-dir D [--suite-record FILE] [--records-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("selected",), "photograph")
    ws = common.workspace(run)
    view = common.read(run, "doc.json")
    if not gitio.is_work_tree_root(ws) or gitio.head(ws) is None:
        report.finish(ctx, run, "stopped", "not-git",
                      "the workspace is not a git work tree root with a commit: there is no branch, no tree state and "
                      "no checkpoint to photograph, so handoff-v2 cannot run here; nothing was written")
    data = common.read_doc_bytes(ws, view["doc"])
    if fsio.sha256_bytes(data) != view["sha256"]:
        _moved(ctx, run, "the build doc changed")
    current = docmod.read(common.decode(data))
    edited = blocks_edited(ws, gitio.head(ws), view["doc"], current)
    if edited is not None:
        report.finish(ctx, run, "stopped", "block-edited",
                      "the handoff block of %s (line %d at HEAD) is not in the working copy byte for byte: an earlier "
                      "block is never edited, so the owner settles the edit before this run writes; nothing was "
                      "written" % (edited[1], edited[0]))
    suite = suite_of(args.suite_record)
    client, state = read_records(ctx, run, ws, view["doc"], args.records_root, "reading the cards and the open set")
    try:
        verify = client.verify(ws, view["doc"])
    except records_link.RecordsRefusal as refusal:
        report.finish(ctx, run, "stopped", "records-refused",
                      records_link.refusal_sentence(refusal, "reading the log's head"))
    cards = cards_of(view, state)
    findings = findings_of(state)
    names = [c["name"] for c in cards]
    given = common.station(run).get("slice")
    if given is not None and given not in names:
        report.finish(ctx, run, "stopped", "slice-unknown",
                      "the input names slice %r as the one just finished, and the build doc holds no such slice (it "
                      "holds %s); nothing was written" % (given, ", ".join(names) or "none"))
    rows = [{"name": c["name"], "card": c["card"]} for c in cards]
    photo = {"doc": view["doc"], "cards": cards, "open": [f for f in findings if f["status"] == "open"],
             "findings": findings, "repo": repo_of(ws), "suite": suite,
             "records": {"log": verify.get("log"), "head": verify.get("head"), "events": verify.get("events"),
                         "exists": bool(verify.get("exists"))},
             "finished": nextmove.finished_of(rows, given), "doc_sha256": view["sha256"]}
    common.write(run, "photograph.json", photo)
    common.advance(run, "photographed")
    return ctx.emit(ctx.envelope(next="gate", run_id=run.checkpoint["run_id"], cards=cards, open=photo["open"],
                                 repo=photo["repo"], suite=suite, records=photo["records"], finished=photo["finished"]))
