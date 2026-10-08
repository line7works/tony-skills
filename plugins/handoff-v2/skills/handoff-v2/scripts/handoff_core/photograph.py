"""`photograph` (contract section 3.2; CR-11): the record, read by the script now, never from the session's memory.

Every card and the open set come from the records component's `state` for the build doc (the latest-record rule the
component implements; never recomputed by hand): a slice's card is its `card_observed` when the log observed or set
one, else its `Status:` line as the line rules read it, and the photograph says which. The branch, the commits ahead
of the default branch, the tree state and the HEAD commit come from read-only git; the last-recorded suite state
comes from the record the executor names (`--suite-record`, a build-v2 result read with its provenance), else "none
recorded". No test suite is ever run. Before any of that: the doc must still hold the bytes `select` read, and every
handoff block the doc held at HEAD must be unchanged in the working copy (`block-edited`). Writes `photograph.json`
in the run directory and nothing else.

Two stops come here, before the gate, so no answer is ever given to a run that cannot write:

- `card-drift` (the E15 lane contract A24 (1), build-v2's drift rule, build-contract section 10): a slice whose last
  `card_set` in the log has an `after` that differs from its `Status:` line, while that line equals the event's
  `before`, is the state a run leaves when its card event landed and its `Status:` line did not. The run stops,
  nothing written, naming both values and both ways out: resume the interrupted run's `write` with its run
  directory (it settles the doc half), or set the line to the card the records hold. A line holding any other value
  is a hand edit, which is no drift.
- the records' tail rule (A23 (1), the slice 1b re-check's R1B1-5): when the log holds record lines it imported from
  the doc, the component's `import-legacy --dry-run` (which writes nothing and takes no lock) must not refuse the
  doc as it stands with a conflict (exit 7); a doc it refuses stops `write-refused` here, nothing written, the stop
  ending with the way out (`doc.tail_rule_way_out`). `write` checks the same again.
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


def imported_lines(client, ws, doc_rel):
    """([(line, raw)], {line: heading line}) of every record line the log imported from the doc (`events`: legacy
    origin, cards left out), with the line of the record block heading each was read under then."""
    seen, headings = {}, {}
    for row in client.events(ws, doc_rel).get("results") or []:
        event = row.get("event") or {}
        origin = event.get("origin") or {}
        if origin.get("kind") != "legacy" or origin.get("doc") != doc_rel or event.get("kind") == "card_observed":
            continue
        if isinstance(origin.get("line"), int) and isinstance(origin.get("raw"), str):
            seen.setdefault(origin["line"], origin["raw"])
            headings.setdefault(origin["line"], origin.get("heading_line"))
    return sorted(seen.items()), headings


def tail_rule_refusal(client, ws, doc_rel, text, imported, headings=None):
    """The stop reason when the records component's own dry run already refuses the doc with a conflict (exit 7), or
    None. A dry run refused for another reason is not this rule's, and passes (a write does not cause it)."""
    try:
        client.import_legacy(ws, doc_rel, dry_run=True)
    except records_link.RecordsRefusal as refusal:
        if refusal.exit_code == 7:
            return ("the records component already refuses this doc's next levelling pass (records section 11.7: %s), "
                    "and a write would leave it so; nothing was written. The owner settles the doc first: %s"
                    % (refusal.sentence(), docmod.tail_rule_way_out(text, imported, refusal.body, headings)))
    return None


def card_drift(rows, view):
    """The first slice whose `Status:` line reads the `before` of its last `card_set` while that event's `after` is
    another card, as (slice, the line's card, the event), or None. `rows` are `events --kind card_set` results."""
    last = {}
    for row in rows:
        event = row.get("event") or {}
        if event.get("kind") == "card_set" and isinstance(event.get("slice"), str):
            last[event["slice"]] = dict(event, seq=row.get("seq"))
    for item in view["slices"]:
        event = last.get(item["name"])
        if event is None or item.get("status") is None:
            continue
        if event.get("after") != item["status"] and item["status"] == event.get("before"):
            return item["name"], item["status"], event
    return None


def drift_reason(name, line, event):
    actor = event.get("actor") or {}
    return ("slice %s's Status: line reads %r, the card the records' last card move for it started from, and that "
            "move (a card_set at seq %s by %s run %s, %r to %r) is in the log: its event landed and its Status: line did "
            "not, so the doc contradicts the record and this run writes nothing over it; nothing was written. Two ways "
            "out: resume the interrupted run's write with its run directory (for a handoff-v2 run, `handoff.py write "
            "--run-dir <the run directory of run %s>`), which settles the doc half; or set the line to the card the "
            "records hold, `Status: %s`, by hand. Then run handoff again"
            % (name, line, event.get("seq"), actor.get("station") or "a station", actor.get("run_id"),
               event.get("before"), event.get("after"), actor.get("run_id"), event.get("after")))


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
    try:
        drift = card_drift(client.events(ws, view["doc"], kind="card_set").get("results") or [], view)
        imported, headings = imported_lines(client, ws, view["doc"])
    except records_link.RecordsRefusal as refusal:
        report.finish(ctx, run, "stopped", "records-refused",
                      records_link.refusal_sentence(refusal, "reading the card moves and the imported lines"))
    if drift is not None:
        report.finish(ctx, run, "stopped", "card-drift", drift_reason(*drift))
    if imported:
        why = tail_rule_refusal(client, ws, view["doc"], common.decode(data), imported, headings)
        if why is not None:
            report.finish(ctx, run, "stopped", "write-refused", why)
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
