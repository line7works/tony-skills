"""The owner's mid-run grant and the card it moves (the E15 lane contract A27 (1): E15-9 as amended for ship-v2;
contract section 6).

    plan(run, kind, finding_id, words, records_root) -> the plan, or GrantRefused (exit 5, nothing written)
    execute(ctx, run, plan, given, records_root) -> ("done", receipt) | ("ended", the emitted stop)
    pending(run) -> the receipt of a transaction this run began and never finished, or None
    receipt_of(run, pause) -> the receipt of that pause's grant, finished or not, or None
    settle(ctx, run, receipt, records_root) -> ("done", receipt) | ("ended", the emitted stop) | ("replan", None)

THE GRANT. For each grant ship-v2 writes the `waived` or `reopened` event with the owner's words and, when the slice's
card changes by v1's rule after the grant, a `card_set` event and its `Status:` line, as handoff-v2 does (A23 (2)). v1's
rule (the records component's `card_derived` implements it): a slice whose card is a verdict (`rejected`, `signed off
with conditions`, `signed off`) takes the card its open findings give after the grant, waived ones excluded: any
BLOCKER open gives `rejected`, else any MAJOR open gives `signed off with conditions`, else `signed off`; any other
card is kept (a grant never gives a verdict to a slice that has none). The card a grant moves is the one the records
hold (`card_observed`, else the slice's `Status:` line) and its `Status:` line must read the same card, or the grant is
refused before any write: the owner settles the line first.

THE TRANSACTION (build-v2's, build-contract sections 9 and 10, as A24 (1) applies it to handoff-v2). The whole plan
goes into `receipt-<pause>.json` in the run directory before the append (the events, the card move, the log's head and
the seq the append expects, the doc's hash before and the hash the plan produces); then ONE `records.py append` of
the grant event and its `card_set`, all or none, against that head; the outcome into the receipt; then the doc, once:
the one `Status:` line set, the rest of the doc byte for byte, checked to read cleanly by both readings with the slice
at the new card, then replaced whole; then the receipt records the write. A refusal the component returns writes
nothing anywhere: the doc and the log stay byte-equal, and the run ends `records-refused`.

THE CRASH WINDOW (A24 (1)'s two rules). A run killed between the append and the doc write settles on its next
command (`pause --answer`, the one command a paused run takes) before anything else, against the head the receipt
names and never a head read afresh: its own events found there (each at the seq the plan named, the first carrying
the receipt's head as its `prev`, every one under this run's id, this station and the planned kind) are recorded as
landed, never appended again; not found there, nothing of the grant landed and it is planned again from the top.
The doc half is finished against the receipt's doc hash: at the bytes the plan read, the line is written; at the
bytes the plan produces (or the receipt records the write), it is this run's own write and is not written again; at
any other bytes the run stops `outside-edit`, naming what the slice's `Status:` line holds, the events reported as
landed, nothing reverted. Once the log holds this run's events no stop says that nothing was written. A fresh run
whose slice's last `card_set` differs from its `Status:` line while that line equals the event's `before` stops
`card-drift` at `select` (`drift`).

SHIP-V2'S OWN WRITE IS NO FIX. Each grant's `Status:` write (its receipt's doc hash before and after) is recorded
against the window rule's pin (`window.own`), and every check point takes it as ship-v2's own sanctioned write: a link
in the chain the doc's hashes must run along from the pin, so it is never a station's or a fix's move, and a hand edit
before, between or after it still is (the E15 lane contract A28 (1); slice 2 re-check 1's R1S2-4).

THE WRITES. Each receipt write and the doc's write go through `common.put` (a temporary file beside it, then a
rename), so a kill leaves the old bytes or the new; a temporary file a cut-off doc write left beside the doc is
removed before the doc half runs again. The receipt finished is staged and lands in the answer's one save (`finished`;
THE SAVE in `common.py`).

The test hook `SHIP_V2_TEST_HOLD` (honored only with `SHIP_V2_TEST=1`) holds the process at one named point so a test
can kill it there: `intent` (the append landed, the receipt holds no outcome), `outcome` (the receipt holds the
outcome, the doc is not written), `written` (the doc is written, the run's bookkeeping is not), `answered` (the
answer's bookkeeping is decided and staged, and none of it is saved: `pause.py`).
"""
import os
import time

from station_core import fsio, records_link

from . import common, doc as docmod, fences, record

VERDICT = ("rejected", "signed off with conditions", "signed off")
HOLDS = ("intent", "outcome", "written", "answered")


class GrantRefused(Exception):
    """A grant the record cannot take: refused (exit 5) with nothing written."""


def effective(card, open_rows):
    """v1's rule for the card after a grant (module docstring)."""
    if card not in VERDICT:
        return card
    severities = set(r.get("severity") for r in open_rows)
    if "BLOCKER" in severities:
        return "rejected"
    if "MAJOR" in severities:
        return "signed off with conditions"
    return "signed off"


def hold_point(where):
    """The test hook (module docstring): sleep at `where` when the test asked for it, so its kill lands there."""
    value = os.environ.get(common.PREFIX + "_TEST_HOLD")
    if common.test_mode() and value == where and where in HOLDS:
        time.sleep(120)


_hold = hold_point


def set_status(text, line, before, after):
    """The text with line `line` (1-based), which must read exactly `Status: <before>`, set to `Status: <after>`; every
    other byte kept. ValueError otherwise."""
    raw = fences.split_lines(text)
    if not 0 < line <= len(raw):
        raise ValueError("line %d is not a line of the doc" % line)
    bare = fences.bare(raw[line - 1], line)
    match = fences.STATUS_EXACT.match(bare)
    if match is None or match.group(1) != before:
        raise ValueError("line %d reads %r, not `Status: %s`" % (line, bare, before))
    ending = raw[line - 1][len(raw[line - 1].rstrip("\r\n")):]
    raw[line - 1] = "Status: %s%s%s" % (after, bare[match.end(1):], ending)
    return "".join(raw)


def _read_doc(ws, rel):
    """(text, parsed) of the doc as it stands, read twice (CR-27); GrantRefused when it cannot be read cleanly."""
    try:
        text = common.read_doc_bytes(ws, rel).decode("utf-8")
        return text, docmod.read(text)
    except (OSError, UnicodeDecodeError) as exc:
        raise GrantRefused("the build doc %s cannot be read now (%s), so the card the grant moves cannot be read"
                           % (rel, exc))
    except docmod.DocUnreadable as exc:
        raise GrantRefused("the build doc %s cannot be read cleanly at line %d now, so the card the grant moves cannot "
                           "be read: %s" % (rel, exc.line, exc.words))


def plan(run, kind, finding_id, words, records_root=None):
    """The grant's events and card move (module docstring, THE GRANT); GrantRefused with nothing written."""
    name = record.GRANTS[kind]
    cli = record.client(run, records_root)
    ws, rel = common.workspace(run), common.state(run)["doc"]
    body = cli.state(ws, rel)
    rows = body.get("findings") or []
    row = next((f for f in rows if f.get("id") == finding_id), None)
    if row is None:
        raise GrantRefused("the records hold no finding %r for %s" % (finding_id, rel))
    if row.get("status") not in record.ADMITS[name]:
        raise GrantRefused("the finding %s stands %r, and a %s takes only a finding that stands %s" % (
            finding_id, row.get("status"), name, " or ".join(repr(s) for s in record.ADMITS[name])))
    identity = cli.identity(ws)["identity"]
    at = common.now()
    events = [record.event(run, name, {"id": finding_id, "severity": row.get("severity")}, words, identity, at)]
    move, text, planned = None, None, None
    slice_name = row.get("slice")
    if slice_name:
        after_status = "waived" if name == "waived" else "open"
        open_after = [f for f in rows if f.get("slice") == slice_name and
                      (after_status if f.get("id") == finding_id else f.get("status")) == "open"]
        held_row = next((s for s in body.get("slices") or [] if s.get("name") == slice_name), None) or {}
        held = held_row.get("card_observed")
        if held in (None, "none") or effective(held, open_after) != held:
            text, parsed = _read_doc(ws, rel)
            item = docmod.slice_of(parsed, slice_name)
            line = item["status"] if item else None
            card = held if held not in (None, "none") else line
            after = effective(card, open_after)
            if card is not None and after != card:
                if item is None or item.get("status_at") is None:
                    raise GrantRefused("slice %s has no Status: line in %s for the card this grant moves (%r to %r)"
                                       % (slice_name, rel, card, after))
                if line != card:
                    raise GrantRefused("slice %s's Status: line reads %r and the records hold the card %r: the card a "
                                       "grant moves is the one the Status: line and the records agree on, so the "
                                       "owner settles the line first" % (slice_name, line, card))
                move = {"slice": slice_name, "line": item["status_at"], "before": card, "after": after}
                planned = set_status(text, move["line"], card, after)
                try:
                    check = docmod.slice_of(docmod.read(planned), slice_name)
                except docmod.DocUnreadable as exc:
                    raise GrantRefused("the doc with slice %s's Status: line moved would not read cleanly at line %d: "
                                       "%s" % (slice_name, exc.line, exc.words))
                if check is None or check["status"] != after:
                    raise GrantRefused("the doc with slice %s's Status: line moved does not read the card %r"
                                       % (slice_name, after))
    if move is not None:
        events.append({"v": 1, "kind": "card_set", "at": at, "ledger_doc": rel,
                       "actor": records_link.actor(common.STATION, common.run_id(run), common.harness(run)),
                       "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                       "slice": move["slice"], "before": move["before"], "after": move["after"]})
    return {"kind": name, "finding": finding_id, "words": words, "events": events, "card": move, "text": text,
            "planned": planned}


def _receipt_name(number):
    return "receipt-%d.json" % number


def grants_row(receipt, appended):
    """The `events.json` row of one grant: what the result reports of it."""
    log = None
    if appended:
        log = {"path": receipt["log"], "sha256_before": receipt["log_sha256_before"],
               "sha256_after": receipt.get("log_sha256_after"), "head_before": receipt["expect_head"]}
    doc = None
    if receipt.get("doc_written"):
        doc = {"path": receipt["doc"], "sha256_before": receipt["doc_sha256_before"],
               "sha256_after": receipt["doc_sha256_after"]}
    return {"pause": receipt["pause"], "kind": receipt["kind"], "finding": receipt["finding"],
            "words": receipt["words"], "card": receipt["card"], "appended": bool(appended), "log": log, "doc": doc}


def execute(ctx, run, planned, given, records_root=None):
    """The transaction (module docstring). Returns ("done", receipt) or ("ended", the emitted stop)."""
    ws, rel = common.workspace(run), common.state(run)["doc"]
    cli = record.client(run, records_root)
    head = cli.verify(ws, rel)
    log = os.path.join(ws, head["log"])
    doc_path = os.path.join(ws, rel)
    receipt = {"receipt_version": 1, "run_id": common.run_id(run), "pause": given["pause"], "answer": given,
               "kind": planned["kind"], "finding": planned["finding"], "words": planned["words"],
               "events": planned["events"], "card": planned["card"], "log": log,
               "log_sha256_before": fsio.sha256_file_or_none(log), "log_sha256_after": None,
               "expect_head": head["head"], "expect_seq": head["events"], "doc": doc_path, "doc_rel": rel,
               "doc_sha256_before": fsio.sha256_bytes(planned["text"].encode("utf-8")) if planned["card"] else None,
               "doc_sha256_planned": fsio.sha256_bytes(planned["planned"].encode("utf-8")) if planned["card"] else None,
               "doc_sha256_after": None, "appended": None, "doc_written": False, "finished": False, "stop": None}
    common.write(run, _receipt_name(given["pause"]), receipt)
    try:
        body = cli.append(ws, rel, planned["events"], head["head"], run.run_dir)
    except records_link.RecordsRefusal as exc:
        sentence = records_link.refusal_sentence(exc, "recording the owner's %s" % planned["kind"])
        receipt.update(appended={"refused": sentence}, stop={"tag": "records-refused", "reason": sentence})
        common.write(run, _receipt_name(given["pause"]), receipt)
        return "refused", sentence
    _hold("intent")
    receipt.update(appended=[{"seq": r.get("seq"), "kind": r.get("kind"), "finding": r.get("finding")}
                             for r in body.get("appended") or []], log_sha256_after=fsio.sha256_file_or_none(log))
    common.write(run, _receipt_name(given["pause"]), receipt)
    _hold("outcome")
    return _doc_half(ctx, run, receipt)


def _status_words(receipt):
    """What the slice's `Status:` line holds on disk now, for an `outside-edit` stop."""
    move = receipt.get("card") or {}
    try:
        with open(receipt["doc"], "rb") as fh:
            item = docmod.slice_of(docmod.read(fh.read().decode("utf-8")), move.get("slice"))
    except (OSError, UnicodeDecodeError, docmod.DocUnreadable):
        return "slice %s's Status: line cannot be read cleanly now" % move.get("slice")
    if item is None or item.get("status_at") is None:
        return "slice %s has no Status: line now" % move.get("slice")
    return "slice %s's line reads `Status: %s`" % (move.get("slice"), item["status"])


def _outside_edit(run, receipt, after_write=False):
    move = receipt["card"]
    landed = ", ".join("seq %s %s" % (row["seq"], row["kind"]) for row in receipt["appended"] or [])
    current = fsio.sha256_file_or_none(receipt["doc"])
    reason = ("the build doc %s is at neither the bytes this run read (%s) nor the bytes its write produces (%s); it "
              "hashes to %s: %s. On disk, %s. This run's events landed in the records log (%s) and are reported as "
              "landed (this run's card_set moved slice %s from %r to %r); the doc is left as it is, neither written by "
              "this run nor reverted. Read the doc and the log, set the line to the card the records hold, "
              "`Status: %s`, then go on"
              % (receipt["doc_rel"], (receipt["doc_sha256_before"] or "")[:12],
                 (receipt["doc_sha256_planned"] or "")[:12], (current or "nothing")[:12],
                 "the doc was edited after this run's own write reached it" if after_write
                 else "the doc was edited after this run planned its write", _status_words(receipt), landed,
                 move["slice"], move["before"], move["after"], move["after"]))
    receipt["stop"] = {"tag": "outside-edit", "reason": reason}
    common.write(run, _receipt_name(receipt["pause"]), receipt)
    return "outside-edit", reason


def _doc_half(ctx, run, receipt):
    """The `Status:` line, written once against the receipt's doc hash; then the receipt records the write."""
    if receipt["card"] is None:
        return "done", receipt
    common.clear_temp(common.temp_of(receipt["doc"]))
    current = fsio.sha256_file_or_none(receipt["doc"])
    if receipt.get("doc_written") or current == receipt["doc_sha256_planned"]:
        if current != (receipt.get("doc_sha256_after") or receipt["doc_sha256_planned"]):
            return _outside_edit(run, receipt, after_write=True)
        receipt.update(doc_written=True, doc_sha256_after=current)
        common.write(run, _receipt_name(receipt["pause"]), receipt)
        return "done", receipt
    if current != receipt["doc_sha256_before"]:
        return _outside_edit(run, receipt)
    with open(receipt["doc"], "rb") as fh:
        text = fh.read().decode("utf-8")
    move = receipt["card"]
    final = set_status(text, move["line"], move["before"], move["after"])
    if fsio.sha256_bytes(final.encode("utf-8")) != receipt["doc_sha256_planned"]:
        return _outside_edit(run, receipt)
    common.put(receipt["doc"], final.encode("utf-8"))
    receipt.update(doc_written=True, doc_sha256_after=fsio.sha256_file(receipt["doc"]))
    common.write(run, _receipt_name(receipt["pause"]), receipt)
    _hold("written")
    return "done", receipt


def pending(run):
    """The receipt of a grant transaction this run began and never finished (the newest), or None."""
    names = sorted((n for n in os.listdir(run.run_dir) if n.startswith("receipt-") and n.endswith(".json")),
                   key=lambda n: int(n[len("receipt-"):-len(".json")]) if n[len("receipt-"):-len(".json")].isdigit()
                   else -1)
    for name in reversed(names):
        receipt = common.read(run, name)
        if not receipt.get("finished") and not receipt.get("abandoned"):
            return receipt
    return None


def receipt_of(run, number):
    """The receipt of pause `number`'s grant, finished or not, or None (a resume, or a report-only grant)."""
    if not common.has(run, _receipt_name(number)):
        return None
    return common.read(run, _receipt_name(number))


def _landed(rows, receipt):
    """This run's own events in the log at the seq the plan named, or None (handoff-v2's test, build-v2's two keys)."""
    planned = receipt["events"]
    want = receipt["expect_seq"]
    found = sorted((r for r in rows if isinstance(r.get("seq"), int) and want <= r["seq"] < want + len(planned)),
                   key=lambda r: r["seq"])
    if len(found) != len(planned):
        return None
    for index, (row, plan_event) in enumerate(zip(found, planned)):
        event = row.get("event") or {}
        actor = event.get("actor") or {}
        if row["seq"] != want + index or event.get("kind") != plan_event["kind"] \
                or actor.get("run_id") != receipt["run_id"] or actor.get("station") != common.STATION:
            return None
        if any(event.get(key) != plan_event.get(key) for key in ("finding", "slice", "before", "after")):
            return None
    if (found[0].get("event") or {}).get("prev") != receipt["expect_head"]:
        return None
    return [{"seq": r["seq"], "kind": r["event"]["kind"], "finding": r["event"].get("finding")} for r in found]


def settle(ctx, run, receipt, records_root=None):
    """The crash window, settled (module docstring). Returns ("done", receipt), ("refused", sentence),
    ("outside-edit", reason) or ("replan", None): nothing of the grant landed."""
    if receipt.get("stop"):
        tag = receipt["stop"]["tag"]
        return ("refused" if tag == "records-refused" else tag), receipt["stop"]["reason"]
    appended = receipt.get("appended")
    if isinstance(appended, dict) and appended.get("refused"):
        return "refused", appended["refused"]
    if appended is None:
        cli = record.client(run, records_root)
        ws, rel = common.workspace(run), receipt["doc_rel"]
        rows = cli.events(ws, rel, from_seq=receipt["expect_seq"]).get("results") or []
        landed = _landed(rows, receipt)
        if landed is None:
            receipt["abandoned"] = True
            common.write(run, _receipt_name(receipt["pause"]), receipt)
            return "replan", None
        receipt.update(appended=landed, settled=True, log_sha256_after=fsio.sha256_file_or_none(receipt["log"]))
        common.write(run, _receipt_name(receipt["pause"]), receipt)
    return _doc_half(ctx, run, receipt)


def finished(run, receipt):
    """The receipt marked finished, staged: it lands in the answer's one save (THE SAVE in `common.py`)."""
    receipt["finished"] = True
    common.stage(run, _receipt_name(receipt["pause"]), receipt)


def drift(rows, item):
    """The slice's last `card_set` when its `after` differs from the slice's `Status:` line while that line equals the
    event's `before` (build-v2's drift rule, build-contract section 10), else None. `rows` are `events --kind card_set`
    results; `item` the slice's row of the doc reading."""
    last = None
    for row in rows:
        event = row.get("event") or {}
        if event.get("kind") == "card_set" and event.get("slice") == item["name"]:
            last = dict(event, seq=row.get("seq"))
    if last is None or item.get("status") is None:
        return None
    if last.get("after") != item["status"] and item["status"] == last.get("before"):
        return last
    return None
