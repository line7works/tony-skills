"""`write` (contract section 3.5; CR-13, CR-14): the next move from the record and the sanctioned writes, exhaustively.

Before any write, in this order, each a stop with nothing written:

1. the doc: every handoff block `select` read is still there byte for byte (`block-edited`), and the doc still
   holds the bytes `select` read (`photograph-moved`);
2. git: the branch is the photographed one, and HEAD is the photographed commit or exactly one commit on it whose
   subject starts `handoff checkpoint` (the executor's named step, A2 Q2: read and recorded here, never made), taken
   on a tree the photograph saw dirty, changing at least one path (an empty commit checkpoints nothing: the slice 1b
   re-check's R1B1-6) and only paths the photograph saw dirty (the slice 1b check's C1B1-8); anything else moved
   (`photograph-moved`, naming the extra paths);
3. the records: the log's head is the photographed one (`photograph-moved`);
4. the plan: the next move resolved from the record after this run's grants (`nextmove.resolve`; an unresolved move
   never reaches here, `record-answer` refuses it), the block rendered from the script's reads (the cards, the open
   set, the branch, the commits ahead and the tree read now, the suite record as photographed; the answer supplies
   no photograph line), the card moves (A23 (2): for each slice a grant of this run names whose card changes by
   v1's rule after the grants, from the card the records and its `Status:` line agree on), and the doc planned with
   the card moves and the block, which must read cleanly by the line rules and the second reading (A25), hold every earlier block unchanged, hold
   one more block, under `## Handoffs`, and differ from the doc only by the inserted lines and the moved `Status:`
   lines (`write-refused`);
5. the records' tail rule (A23 (1)): when the log holds record lines it imported from the doc, the component's own
   `import-legacy --dry-run` (which writes nothing and takes no lock) must not refuse the doc as it stands with a
   conflict (`photograph` checks it first, before the gate, the slice 1b re-check's R1B1-5; the stop names the way
   out), and the planned doc must keep every imported line in its order and add no line byte-equal to one
   (`doc.levelling_problem`); a write that would leave a doc the widened rule refuses is `write-refused`.

Then the writes, in order, each with its hash before and after in `receipt.json` and the result, in the one records
transaction build-v2 uses for a card (its contract sections 9 and 10: the whole plan in the receipt before the
append, one append all or none against the photographed head, the outcome in the receipt, then the doc): (1) the
`waived` and `reopened` events, each with the owner's words, and after them one `card_set` per card move, all in ONE
`records.py append`; the grant lines as the component renders them (`render --run-id`); (2) the doc, once: the moved
`Status:` lines, the grant lines at the ledger home's tail and the block at the tail of `## Handoffs`, checked again
as in 4 and 5, then replaced whole. A refusal of the append writes nothing anywhere: the doc and the log stay
byte-equal. The pointer's text is left in the run directory (`pointer.json`) for the Claude Code adapter's step; on
Codex, and on a report-only run, it says no memory pointer is written. Nothing else is written, ever: no earlier
block, no punch-list history, no `Status:` line but a moved card's, no event but the grants and their card moves
(E15-9 as A23 amends it). A report-only run plans and checks everything, leaves the plan in the run directory
(`planned-doc.md`, `events.json`) and writes nothing else.

THE CRASH WINDOW (the E15 lane contract A24 (1): build-v2's two rules for its card write, build-contract sections 9
and 10, applied to this transaction). The receipt holds the whole plan before the append (the events, the card
moves, the doc's hash before, the block and the record it renders, the seq and head the append expects) and, before
the doc is replaced, the hash the final doc has. A `write` that finds a receipt of its own run settles first:

- a refusal the component returned, or a stop after the append, is definitive: it is given again, never retried;
- an intent with no outcome is the crash window, settled against the head the receipt names, never against a head
  read afresh: this run's events found there (each at the seq the plan named, the first carrying the receipt's head
  as its `prev`, every one under this run's id, station and planned kind) are recorded as landed and the doc half is
  finished; not found there, the log either still stands at the receipt's head (the append never landed, and the
  run plans again from the top) or moved for another reason (`photograph-moved`, nothing of this run's written);
- the doc half is finished against the receipt's doc hash: at the bytes the run read, the doc takes the `Status:`
  lines, the grant lines the component renders for this run and the block, checked as above; at the bytes the final
  plan produces (or the receipt records the write), it is this run's own write and is not written again; at any
  other bytes it stops `outside-edit`, naming what each moved slice's `Status:` line holds, the events reported as
  landed, nothing reverted. Once the log holds this run's events no stop says that nothing was written.
"""
import os

from station_core import fsio, records_link

from . import answer as answermod, common, doc as docmod, fences, forms, gitio, photograph, report

CHECKPOINT = "handoff checkpoint"


def _stop(ctx, run, tag, reason, writes=None, extra=None):
    report.finish(ctx, run, "stopped", tag, reason, writes=writes, extra=extra)


def _event(run, grant, identity, at, date, doc_rel):
    event = {"v": 1, "kind": grant["kind"], "at": at, "ledger_doc": doc_rel,
             "actor": records_link.actor(common.STATION, run.checkpoint["run_id"], common.harness(run)),
             "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
             "finding": grant["finding"], "words": grant["words"], "grant_date": date}
    if grant["kind"] == "waived":
        event.update(severity=grant["severity"], verified_source={"known": True, "identity": identity},
                     join_basis=None)
    return event


def _bare(text, index):
    return fences.bare(fences.split_lines(text)[index])


def _card_event(run, move, identity, at, doc_rel):
    """build-v2's card event shape (its `card_event`): the card a grant of this run moved."""
    return {"v": 1, "kind": "card_set", "at": at, "ledger_doc": doc_rel,
            "actor": records_link.actor(common.STATION, run.checkpoint["run_id"], common.harness(run)),
            "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
            "slice": move["slice"], "before": move["before"], "after": move["after"]}


def card_moves(rows, view, grants):
    """A23 (2): [{slice, line, before, after}] for each slice a grant of this run names whose card after the grants
    (v1's rule, `nextmove.effective`) differs from the card it stands at; or (None, why) when one cannot move: its
    `Status:` line is missing or does not read the card the records hold."""
    granted = set(g["slice"] for g in grants)
    lines = dict((s["name"], s) for s in view["slices"])
    out = []
    for row in rows:
        if row["name"] not in granted or row["card"] == row["observed"]:
            continue
        item = lines.get(row["name"])
        if item is None or item.get("status_at") is None:
            return None, "slice %s has no Status: line for the card this run's grants move" % row["name"]
        if item.get("status") != row["observed"]:
            return None, ("slice %s's Status: line reads %r and the records hold the card %r: the card a grant moves "
                          "is the one the line and the records agree on, so the owner settles the line first"
                          % (row["name"], item.get("status"), row["observed"]))
        out.append({"slice": row["name"], "line": item["status_at"], "before": row["observed"], "after": row["card"]})
    return out, None


def _check_plan(before, after, inserted, earlier, heading):
    """Why the planned doc does not hold (section 4 of this module's docstring), or None. `before` is the doc with
    this run's card moves already set, so every other difference must be an inserted line."""
    if not docmod.additive(before, after, inserted):
        return "the plan changes a line it did not insert"
    try:
        planned = docmod.read(after)
    except docmod.DocUnreadable as exc:
        return "the planned doc would not read cleanly (the line rules and the second reading) at line %d: %s" % (exc.line, exc.words)
    texts = [docmod.block_text(planned, b).rstrip("\r\n") for b in planned.blocks]
    earlier = [text.rstrip("\r\n") for text in earlier]
    if texts[:len(earlier)] != earlier or len(texts) != len(earlier) + 1:
        return "the planned doc does not hold every earlier block unchanged and exactly one more"
    new = planned.blocks[-1]
    if planned.handoffs is None or new["section"] != planned.handoffs or planned.misplaced:
        return "the new block would not sit under ## Handoffs"
    if planned.raw[new["line"] - 1].rstrip("\r\n") != heading:
        return "the new block is not the last block of ## Handoffs"
    return None


def _receipt_write(run, receipt):
    common.write(run, "receipt.json", receipt)


def _landed(rows, receipt):
    """This run's own events in the log at the seq the plan named, or None: the first at `expect_seq` carrying the
    receipt's head as its `prev`, each the planned kind under this run's id and this station (build-v2's two tests,
    seq and run id, kept together around the one append this core makes)."""
    planned = receipt["events"]
    want = receipt["expect_seq"]
    found = [row for row in rows if isinstance(row.get("seq"), int) and want <= row["seq"] < want + len(planned)]
    found.sort(key=lambda row: row["seq"])
    if len(found) != len(planned):
        return None
    for index, (row, plan) in enumerate(zip(found, planned)):
        event = row.get("event") or {}
        actor = event.get("actor") or {}
        if row["seq"] != want + index or event.get("kind") != plan["kind"] \
                or actor.get("run_id") != receipt["run_id"] or actor.get("station") != common.STATION:
            return None
        if any(event.get(key) != plan.get(key) for key in ("finding", "slice", "before", "after")):
            return None
    if (found[0].get("event") or {}).get("prev") != receipt["expect_head"]:
        return None
    return [{"seq": row["seq"], "kind": row["event"]["kind"], "finding": row["event"].get("finding")} for row in found]


def _status_words(path, receipt):
    """What each slice this run's card events moved holds on its `Status:` line now, for an `outside-edit` stop."""
    try:
        with open(path, "rb") as fh:
            now = docmod.read(common.decode(fh.read()))
        lines = dict((s["name"], s) for s in now.slices)
    except (OSError, UnicodeDecodeError, docmod.DocUnreadable):
        lines = None
    words = []
    for move in receipt.get("card_moves") or []:
        if lines is None:
            held = "cannot be read cleanly now"
        elif lines.get(move["slice"]) is None or lines[move["slice"]].get("status_at") is None:
            held = "has no Status: line now"
        else:
            held = "reads `Status: %s`" % lines[move["slice"]]["status"]
        words.append("slice %s %s (this run's card_set moved the card from %r to %r)"
                     % (move["slice"], held, move["before"], move["after"]))
    return "; ".join(words) or "this run moved no card"


def _outside_edit(ctx, run, receipt, writes, doc_path, after_write=False):
    """`outside-edit`: the doc is at neither the bytes this run read nor the bytes its write produces. The events
    are reported as landed; the doc is left as it is, neither written nor reverted."""
    current = fsio.sha256_file_or_none(doc_path)
    landed = receipt.get("appended") if isinstance(receipt.get("appended"), list) else []
    events = ("This run's events landed in the records log (%s) and are reported as landed"
              % ", ".join("seq %s %s" % (row["seq"], row["kind"]) for row in landed)) if landed else \
        "This run appended no event"
    planned = receipt.get("doc_sha256_planned")
    when = ("this run's own write reached the doc earlier (its receipt records it) and the doc was edited after it"
            if after_write else "the doc was edited after this run planned its write")
    reason = ("the build doc %s is at neither the bytes this run read (%s) nor the bytes its write produces (%s); it "
              "hashes to %s: %s. On disk, %s. %s; the doc is left as it is, neither written by this run nor reverted. "
              "Read the doc and the log: set each moved slice's Status: line to the card the records hold and add "
              "the grant lines `records.py render --run-id %s` gives, then run handoff again"
              % (receipt["doc"], (receipt.get("doc_sha256_before") or "")[:12],
                 planned[:12] if planned else "not planned yet", (current or "nothing")[:12], when,
                 _status_words(doc_path, receipt), events, receipt["run_id"]))
    receipt["stop"] = {"tag": "outside-edit", "reason": reason}
    _receipt_write(run, receipt)
    _stop(ctx, run, "outside-edit", reason, writes=writes)


def _log_write(receipt, ws):
    return {"path": receipt["log"], "kind": "records_log", "sha256_before": receipt["log_sha256_before"],
            "sha256_after": fsio.sha256_file(receipt["log"])}


def _doc_write(receipt):
    return {"path": receipt["doc"], "kind": "build_doc", "sha256_before": receipt["doc_sha256_before"],
            "sha256_after": receipt["doc_sha256_after"]}


def _doc_half(ctx, run, client, receipt, writes, text, settled=None):
    """The second half: the moved `Status:` lines, the grant lines the component renders for this run and the block,
    checked again, then the doc replaced whole; then the completion."""
    ws = common.workspace(run)
    view = common.read(run, "doc.json")
    earlier = [b["text"] for b in view["blocks"]]
    plan = receipt["plan"]
    block = plan["block_lines"]
    heading = block[0]
    imported = [tuple(item) for item in plan["imported"]]
    events = receipt["events"]
    doc_rel = view["doc"]
    doc_path = receipt["doc"]
    if fsio.sha256_file_or_none(doc_path) != receipt["doc_sha256_before"] and events:
        _outside_edit(ctx, run, receipt, writes, doc_path)
    grant_lines = []
    if events:
        try:
            rendered = client.render(ws, doc_rel, run.checkpoint["run_id"])
        except records_link.RecordsRefusal as refusal:
            _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "rendering the grant lines") +
                  "; the events landed (receipt.json) and the doc was not written", writes=writes)
        grant_lines = [g.rstrip("\r\n") for g in rendered.get("grants") or []]
    try:
        carded = docmod.set_statuses(text, [(m["line"], m["before"], m["after"]) for m in receipt["card_moves"]])
    except ValueError as exc:
        carded, why = None, "the card moves cannot be set on the doc (%s)" % exc
    else:
        why = None
        if fsio.sha256_bytes(carded.encode("utf-8")) != receipt["doc_sha256_carded"]:
            why = "the doc with the card moves set is not the doc the receipt planned"
    if why is None:
        final, inserted = docmod.plan(carded, block, grant_lines)
        why = _check_plan(carded, final, inserted, earlier, heading)
        if why is None and sum(1 for i in inserted if _bare(final, i) in grant_lines) < len(grant_lines):
            why = "the final plan does not hold every rendered grant line"
        if why is None and imported:
            why = docmod.levelling_problem(final, inserted, imported)
    if why is None and fsio.sha256_file_or_none(doc_path) != receipt["doc_sha256_before"]:
        if events:
            _outside_edit(ctx, run, receipt, writes, doc_path)
        why = "the build doc changed while this run planned its write"
    if why:
        tail = "the events landed (receipt.json) and the doc was not written" if events else "nothing was written"
        receipt["refused"] = why
        receipt["stop"] = {"tag": "write-refused", "reason": "%s; %s" % (why, tail)}
        _receipt_write(run, receipt)
        _stop(ctx, run, "write-refused", receipt["stop"]["reason"], writes=writes)
    receipt["doc_sha256_planned"] = fsio.sha256_bytes(final.encode("utf-8"))
    _receipt_write(run, receipt)
    fsio.atomic_write(doc_path, final.encode("utf-8"))
    receipt["doc_written"] = True
    receipt["doc_sha256_after"] = fsio.sha256_file(doc_path)
    _receipt_write(run, receipt)
    writes.append(_doc_write(receipt))
    return _complete(ctx, run, client, receipt, writes, settled)


def _complete(ctx, run, client, receipt, writes, settled=None):
    """The completion after the doc half: the component's derived card beside each card, `pointer.json`,
    `write.json`, the phase moved to `written`."""
    ws = common.workspace(run)
    record = dict(receipt["plan"]["record"])
    events = receipt["events"]
    cards = [dict(card) for card in record["cards_after"]]
    if events:
        try:
            after = client.state(ws, common.read(run, "doc.json")["doc"])
            derived = dict((s["name"], s.get("card_derived")) for s in after.get("slices") or [])
            for card in cards:
                card["component"] = derived.get(card["name"])
        except records_link.RecordsRefusal:
            pass
    pointer = record["pointer"]
    common.write(run, "pointer.json", pointer)
    with open(receipt["doc"], "rb") as fh:
        final = docmod.read(common.decode(fh.read()))
    block = dict(record["block"], line=final.blocks[-1]["line"])
    record.update(writes=writes, events=events, cards_after=cards, block=block, settled=settled)
    common.write(run, "write.json", record)
    common.advance(run, "written")
    return ctx.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], report_only=False,
                                 next_move=record["next_move"], block=block, writes=writes, events=events,
                                 pointer=pointer, checkpoint=record["checkpoint"], settled=settled))


def _settle(ctx, run, args, receipt):
    """A receipt of this run's own, found at `write`: settled before any other check (the module's "THE CRASH
    WINDOW"). Returns None when nothing of this run landed, so the run plans again from the top."""
    appended = receipt.get("appended")
    if isinstance(appended, dict) and appended.get("refused"):
        _stop(ctx, run, "records-refused", appended["refused"] + "; the component wrote nothing, and nothing else "
              "was written (a refusal the component returned is definitive and is never retried)")
    events = receipt.get("events") or []
    if "plan" not in receipt or "expect_seq" not in receipt:
        _stop(ctx, run, "write-refused", "this run's receipt.json holds no plan this core can settle (it was "
              "written by an earlier version of handoff-v2): if the records log holds this run's events (run id %s), "
              "set each moved slice's Status: line to the card the records hold and add the grant lines `records.py "
              "render --run-id %s` gives; otherwise run handoff again" % (receipt.get("run_id"), receipt.get("run_id")))
    ws = common.workspace(run)
    doc_rel = common.read(run, "doc.json")["doc"]
    doc_path = receipt["doc"]
    client = records_link.open_client(common.STATION, records_root=args.records_root)
    writes = []
    if receipt.get("stop"):
        if isinstance(appended, list):
            writes.append(_log_write(receipt, ws))
        _stop(ctx, run, receipt["stop"]["tag"], receipt["stop"]["reason"], writes=writes)
    settled = None
    if events:
        if not isinstance(appended, list):
            try:
                rows = client.events(ws, doc_rel, from_seq=receipt["expect_seq"]).get("results") or []
            except records_link.RecordsRefusal as refusal:
                _stop(ctx, run, "records-refused", records_link.refusal_sentence(
                    refusal, "reading the log for this run's own events") + "; receipt.json holds this run's intent "
                    "with no outcome, so its events may have landed: run write again once the log reads")
            landed = _landed(rows, receipt)
            if landed is None:
                try:
                    verify = client.verify(ws, doc_rel)
                except records_link.RecordsRefusal as refusal:
                    _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "reading the log's head"))
                if verify.get("head") == receipt["expect_head"]:
                    return None
                _stop(ctx, run, "photograph-moved", "the records log moved since the photograph (head %s, was %s), and "
                      "this run's events are not in it (receipt.json holds their intent, never appended): another "
                      "writer appended; nothing was written. Run handoff again"
                      % (str(verify.get("head"))[:12], receipt["expect_head"][:12]))
            receipt["appended"] = landed
            receipt["settled"] = True
            _receipt_write(run, receipt)
            settled = "this run's events were found in the log at seq %d and recorded as landed" % landed[0]["seq"]
        writes.append(_log_write(receipt, ws))
    current = fsio.sha256_file_or_none(doc_path)
    planned = receipt.get("doc_sha256_planned")
    if receipt.get("doc_written") or (planned is not None and current == planned):
        if current != (receipt.get("doc_sha256_after") or planned):
            _outside_edit(ctx, run, receipt, writes, doc_path, after_write=True)
        if not receipt.get("doc_written"):
            receipt.update(doc_written=True, doc_sha256_after=current)
            _receipt_write(run, receipt)
        writes.append(_doc_write(receipt))
        note = "the doc already holds this run's write, which is not made again"
        return _complete(ctx, run, client, receipt, writes, "; ".join(n for n in (settled, note) if n))
    if not events:
        return None
    if current == receipt["doc_sha256_before"]:
        with open(doc_path, "rb") as fh:
            text = common.decode(fh.read())
        note = "the doc half was finished against the receipt's doc hash"
        return _doc_half(ctx, run, client, receipt, writes, text, "; ".join(n for n in (settled, note) if n))
    _outside_edit(ctx, run, receipt, writes, doc_path)


def handler(ctx, args):
    """`write --run-dir D [--records-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("answered",), "write")
    if common.has(run, "receipt.json") and not common.report_only(run):
        settled = _settle(ctx, run, args, common.read(run, "receipt.json"))
        if settled is not None:
            return settled
    ws = common.workspace(run)
    view = common.read(run, "doc.json")
    photo = common.read(run, "photograph.json")
    answers = common.read(run, "answers.json")
    doc_rel = view["doc"]
    doc_path = os.path.join(ws, doc_rel)
    earlier = [b["text"] for b in view["blocks"]]
    # 1. the doc
    data = common.read_doc_bytes(ws, doc_rel)
    if fsio.sha256_bytes(data) != view["sha256"]:
        try:
            now_doc = docmod.read(common.decode(data))
            now_blocks = [docmod.block_text(now_doc, b) for b in now_doc.blocks]
        except (UnicodeDecodeError, docmod.DocUnreadable):
            now_blocks = None
        if now_blocks is not None and now_blocks[:len(earlier)] != earlier:
            index = next(i for i, text in enumerate(earlier) if i >= len(now_blocks) or now_blocks[i] != text)
            _stop(ctx, run, "block-edited", "the handoff block of %s (line %d when this run read the doc) changed "
                  "after the photograph: an earlier block is never edited, so the owner settles the edit before this "
                  "run writes; nothing was written" % (view["blocks"][index]["date"], view["blocks"][index]["line"]))
        _stop(ctx, run, "photograph-moved", "the build doc changed since this run read it: the photograph is read "
              "once, now, and the run never writes from a record that moved under it; nothing was written. Run "
              "handoff again")
    text = common.decode(data)
    # 2. git
    repo = photograph.repo_of(ws)
    was = photo["repo"]
    checkpoint = None
    if repo["branch"] != was["branch"]:
        _stop(ctx, run, "photograph-moved", "the branch is %r and was %r at the photograph; nothing was written"
              % (repo["branch"], was["branch"]))
    if repo["head"] != was["head"]:
        parents = gitio.parents(ws, repo["head"])
        subject = gitio.subject(ws, repo["head"])
        if parents != [was["head"]] or not subject.startswith(CHECKPOINT):
            _stop(ctx, run, "photograph-moved", "HEAD moved from %s to %s, which is not one commit on it labelled as a "
                  "handoff checkpoint (subject %r): the checkpoint is the one commit a handoff takes; nothing was "
                  "written" % (was["head"][:12], repo["head"][:12], subject))
        if was["tree"] != "dirty":
            _stop(ctx, run, "photograph-moved", "HEAD moved from %s to %s, a handoff checkpoint taken on a tree the "
                  "photograph saw clean: there was nothing to checkpoint, so the commit is not the photographed "
                  "dirt; nothing was written" % (was["head"][:12], repo["head"][:12]))
        changed = gitio.changed_between(ws, was["head"], repo["head"])
        if not changed:
            _stop(ctx, run, "photograph-moved", "the handoff checkpoint %s changes no path: an empty commit holds none "
                  "of the photographed dirt (%s), so it is not the checkpoint the block would name; nothing was "
                  "written. Commit the dirt as the checkpoint, or run handoff again without one (the slice 1b "
                  "re-check's R1B1-6)" % (repo["head"][:12], ", ".join(was["dirt"])))
        extra = [path for path in changed if path not in was["dirt"]]
        if extra:
            _stop(ctx, run, "photograph-moved", "the handoff checkpoint %s changes paths the photograph did not see "
                  "dirty (%s): work landed after the photograph, so the checkpoint is not the photographed tree; "
                  "nothing was written. Run handoff again" % (repo["head"][:12], ", ".join(extra)))
        checkpoint = {"commit": repo["head"], "parent": was["head"], "subject": subject}
        repo["checkpoint"] = repo["head"]
    # 3. the records
    client = records_link.open_client(common.STATION, records_root=args.records_root)
    try:
        verify = client.verify(ws, doc_rel)
    except records_link.RecordsRefusal as refusal:
        _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "reading the log's head"))
    if verify.get("head") != photo["records"]["head"]:
        _stop(ctx, run, "photograph-moved", "the records log moved since the photograph (head %s, was %s): another "
              "writer appended; nothing was written" % (str(verify.get("head"))[:12], photo["records"]["head"][:12]))
    # 4. the plan
    grants = answers["grants"]
    rows, move = answermod.resolve_after(photo, view, grants, answers.get("owner_next"))
    text_of = forms.next_move_text(move)
    open_after = answermod.post_grant_open(photo, grants)
    moves, why = card_moves(rows, view, grants)
    if why is None:
        try:
            carded = docmod.set_statuses(text, [(m["line"], m["before"], m["after"]) for m in moves])
        except ValueError as exc:
            why = "the card moves cannot be set on the doc (%s)" % exc
    if why:
        _stop(ctx, run, "write-refused", "%s; nothing was written" % why)
    moved = set(m["slice"] for m in moves)
    cards = [{"name": r["name"], "card": r["observed"], "after": r["card"] if r["card"] != r["observed"] else None,
              "moved": r["name"] in moved} for r in rows]
    date = common.date_of(run)
    fields = {"date": date, "next": move, "cards": cards, "open": open_after, "repo": repo, "suite": photo["suite"],
              "questions": [{"question": a["text"], "answer": a["words"], "landed": "block"}
                            for a in answers["answers"] if a["landed"] == "block"],
              "perishables": answers["perishables"]}
    try:
        block = forms.block_lines(fields)
    except forms.FormError as exc:
        _stop(ctx, run, "write-refused", "the block cannot be rendered (%s); nothing was written" % exc)
    heading = block[0]
    planned, inserted = docmod.plan(carded, block, [])
    why = _check_plan(carded, planned, inserted, earlier, heading)
    if why:
        _stop(ctx, run, "write-refused", "%s; nothing was written" % why)
    try:
        imported, headings = photograph.imported_lines(client, ws, doc_rel)
    except records_link.RecordsRefusal as refusal:
        _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "reading the imported lines"))
    if imported:
        why = photograph.tail_rule_refusal(client, ws, doc_rel, text, imported, headings)
        if why:
            _stop(ctx, run, "write-refused", why)
        why = docmod.levelling_problem(planned, inserted, imported)
        if why:
            _stop(ctx, run, "write-refused", "%s: a write that would leave a doc the records' tail rule refuses is "
                  "never made; nothing was written" % why)
    move_out = dict(move, line=text_of["line"], kickoff=text_of["kickoff"], alternative=text_of["alternative"])
    feature = view["feature"]
    for_adapter = common.harness(run) == "claude-code" and not common.report_only(run)
    pointer = {"pointer_version": 1, "run_id": run.checkpoint["run_id"], "harness": common.harness(run),
               "feature": feature, "file_name": "handoff-%s.md" % feature, "doc": doc_rel, "block_date": date,
               "kickoff": text_of["kickoff"] or text_of["line"],
               "text": ("---\nname: handoff-%s\ndescription: the build loop's kickoff pointer for %s\ntype: project\n"
                        "---\n\nBuild doc: %s\nHandoff block: %s\nKickoff: %s\n"
                        % (feature, doc_rel, doc_rel, date, text_of["kickoff"] or text_of["line"])),
               "index_line": "- [Build loop kickoff: %s](handoff-%s.md): the kickoff line for %s, from the %s handoff "
                             "block" % (feature, feature, doc_rel, date),
               "for_adapter": for_adapter,
               "note": None if for_adapter else (
                   "report only: no memory pointer is written" if common.report_only(run) else
                   "%s: no memory pointer is written; the block in the build doc is the pointer (E15-12)"
                   % (common.harness(run) or "this harness"))}
    identity = None
    events = []
    if grants:
        try:
            identity = client.identity(ws)["identity"]
        except records_link.RecordsRefusal as refusal:
            _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "reading the source identity"))
        at = common.now()
        events = [_event(run, g, identity, at, date, doc_rel) for g in grants]
        events += [_card_event(run, m, identity, at, doc_rel) for m in moves]
    record = {"next_move": move_out, "repo": repo, "checkpoint": checkpoint, "open_after": open_after,
              "cards_after": cards, "pointer": pointer, "events": events, "writes": [],
              "block": {"heading": heading, "text": "\n".join(block) + "\n", "line": None}}
    record["card_moves"] = moves
    if common.report_only(run):
        common.write_text(run, "planned-doc.md", planned)
        common.write(run, "events.json", events)
        common.write(run, "pointer.json", pointer)
        record["writes"] = [{"path": common.path_of(run, n), "kind": "run_artifact", "sha256_before": None,
                             "sha256_after": fsio.sha256_file(common.path_of(run, n))}
                            for n in ("planned-doc.md", "events.json")]
        record["block"]["line"] = next(i + 1 for i in inserted if _bare(planned, i) == heading)
        common.write(run, "write.json", record)
        common.advance(run, "written")
        return ctx.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], report_only=True,
                                     next_move=move_out, block=record["block"], writes=record["writes"],
                                     events=events, pointer=pointer))
    receipt = {"receipt_version": 2, "run_id": run.checkpoint["run_id"], "doc": doc_path,
               "doc_sha256_before": view["sha256"], "log": None, "log_sha256_before": None,
               "expect_head": photo["records"]["head"], "expect_seq": photo["records"]["events"], "events": events,
               "card_moves": moves, "doc_sha256_carded": fsio.sha256_bytes(carded.encode("utf-8")),
               "plan": {"record": record, "block_lines": block, "imported": imported},
               "appended": None, "doc_written": False}
    writes = []
    if events:
        log_path = os.path.join(ws, verify["log"])
        receipt.update(log=log_path, log_sha256_before=fsio.sha256_file_or_none(log_path))
        _receipt_write(run, receipt)
        try:
            appended = client.append(ws, doc_rel, events, photo["records"]["head"], run.run_dir)
        except records_link.RecordsRefusal as refusal:
            receipt["appended"] = {"refused": records_link.refusal_sentence(refusal, "appending the grants")}
            _receipt_write(run, receipt)
            _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "appending the grants") +
                  "; the component wrote nothing, and nothing else was written")
        receipt["appended"] = appended.get("appended")
        _receipt_write(run, receipt)
        writes.append(_log_write(receipt, ws))
    else:
        _receipt_write(run, receipt)
    return _doc_half(ctx, run, client, receipt, writes, text)
