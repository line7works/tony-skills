"""`write` (contract section 3.5; CR-13, CR-14): the next move from the record and the sanctioned writes, exhaustively.

Before any write, in this order, each a stop with nothing written:

1. the doc: every handoff block `select` read is still there byte for byte (`block-edited`), and the doc still
   holds the bytes `select` read (`photograph-moved`);
2. git: the branch is the photographed one, and HEAD is the photographed commit or exactly one commit on it whose
   subject starts `handoff checkpoint` (the executor's named step, A2 Q2: read and recorded here, never made);
   anything else moved (`photograph-moved`);
3. the records: the log's head is the photographed one (`photograph-moved`);
4. the plan: the next move resolved from the record after this run's grants (`nextmove.resolve`; an unresolved move
   never reaches here, `record-answer` refuses it), the block rendered from the script's reads (the cards, the open
   set, the branch, the commits ahead and the tree read now, the suite record as photographed; the answer supplies
   no photograph line), and the doc planned with the block alone, which must read cleanly by the line rules, hold
   every earlier block unchanged, hold one more block, under `## Handoffs`, and differ from the doc only by the
   inserted lines (`write-refused`).

Then the writes, in order, each with its hash before and after in `receipt.json` and the result: (1) the `waived` and
`reopened` events, all or none, through `records.py append` against the photographed head, each with the owner's
words; their lines as the component renders them (`render --run-id`); (2) the doc, once: the grant lines at the
ledger home's tail and the block at the tail of `## Handoffs`, checked again as in 4, then replaced whole. The
pointer's text is left in the run directory (`pointer.json`) for the Claude Code adapter's step; on Codex, and on a
report-only run, it says no memory pointer is written. Nothing else is written, ever: no earlier block, no punch-list
history, no `Status:` line, no card event (E15-9). A report-only run plans and checks everything, leaves the plan in
the run directory (`planned-doc.md`, `events.json`) and writes nothing else.
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


def _check_plan(before, after, inserted, earlier, heading):
    """Why the planned doc does not hold (section 4 of this module's docstring), or None."""
    if not docmod.additive(before, after, inserted):
        return "the plan changes a line it did not insert"
    try:
        planned = docmod.read(after)
    except docmod.DocUnreadable as exc:
        return "the planned doc would not read by the line rules at line %d: %s" % (exc.line, exc.words)
    texts = [docmod.block_text(planned, b) for b in planned.blocks]
    if texts[:len(earlier)] != earlier or len(texts) != len(earlier) + 1:
        return "the planned doc does not hold every earlier block unchanged and exactly one more"
    new = planned.blocks[-1]
    if planned.handoffs is None or new["section"] != planned.handoffs or planned.misplaced:
        return "the new block would not sit under ## Handoffs"
    if planned.raw[new["line"] - 1].rstrip("\r\n") != heading:
        return "the new block is not the last block of ## Handoffs"
    return None


def handler(ctx, args):
    """`write --run-dir D [--records-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("answered",), "write")
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
    cards = [{"name": r["name"], "card": r["observed"], "after": r["card"] if r["card"] != r["observed"] else None}
             for r in rows]
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
    planned, inserted = docmod.plan(text, block, [])
    why = _check_plan(text, planned, inserted, earlier, heading)
    if why:
        _stop(ctx, run, "write-refused", "%s; nothing was written" % why)
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
    record = {"next_move": move_out, "repo": repo, "checkpoint": checkpoint, "open_after": open_after,
              "cards_after": cards, "pointer": pointer, "events": events, "writes": [],
              "block": {"heading": heading, "text": "\n".join(block) + "\n", "line": None}}
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
    receipt = {"receipt_version": 1, "run_id": run.checkpoint["run_id"], "doc": doc_path,
               "doc_sha256_before": view["sha256"], "log": None, "log_sha256_before": None,
               "expect_head": photo["records"]["head"], "events": events, "appended": None, "doc_written": False}
    writes = []
    grant_lines = []
    if events:
        log_path = os.path.join(ws, verify["log"])
        receipt.update(log=log_path, log_sha256_before=fsio.sha256_file_or_none(log_path))
        common.write(run, "receipt.json", receipt)
        try:
            appended = client.append(ws, doc_rel, events, photo["records"]["head"], run.run_dir)
        except records_link.RecordsRefusal as refusal:
            receipt["appended"] = {"refused": records_link.refusal_sentence(refusal, "appending the grants")}
            common.write(run, "receipt.json", receipt)
            _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "appending the grants") +
                  "; the component wrote nothing, and nothing else was written")
        receipt["appended"] = appended.get("appended")
        common.write(run, "receipt.json", receipt)
        writes.append({"path": log_path, "kind": "records_log", "sha256_before": receipt["log_sha256_before"],
                       "sha256_after": fsio.sha256_file(log_path)})
        try:
            rendered = client.render(ws, doc_rel, run.checkpoint["run_id"])
        except records_link.RecordsRefusal as refusal:
            _stop(ctx, run, "records-refused", records_link.refusal_sentence(refusal, "rendering the grant lines") +
                  "; the events landed (receipt.json) and the doc was not written", writes=writes)
        grant_lines = [g.rstrip("\r\n") for g in rendered.get("grants") or []]
    else:
        common.write(run, "receipt.json", receipt)
    final, inserted = docmod.plan(text, block, grant_lines)
    why = _check_plan(text, final, inserted, earlier, heading)
    if why is None and sum(1 for i in inserted if _bare(final, i) in grant_lines) < len(grant_lines):
        why = "the final plan does not hold every rendered grant line"
    if why is None and fsio.sha256_file(doc_path) != view["sha256"]:
        why = "the build doc changed while the events were appended"
    if why:
        receipt["refused"] = why
        common.write(run, "receipt.json", receipt)
        _stop(ctx, run, "write-refused", "%s; %s" % (why, "the events landed (receipt.json) and the doc was not "
              "written" if events else "nothing was written"), writes=writes)
    fsio.atomic_write(doc_path, final.encode("utf-8"))
    receipt["doc_written"] = True
    receipt["doc_sha256_after"] = fsio.sha256_file(doc_path)
    common.write(run, "receipt.json", receipt)
    writes.append({"path": doc_path, "kind": "build_doc", "sha256_before": view["sha256"],
                   "sha256_after": receipt["doc_sha256_after"]})
    if events:
        try:
            after = client.state(ws, doc_rel)
            derived = dict((s["name"], s.get("card_derived")) for s in after.get("slices") or [])
            for card in cards:
                card["component"] = derived.get(card["name"])
        except records_link.RecordsRefusal:
            pass
    common.write(run, "pointer.json", pointer)
    record.update(writes=writes, events=events, cards_after=cards)
    record["block"]["line"] = next(i + 1 for i in inserted if _bare(final, i) == heading)
    common.write(run, "write.json", record)
    common.advance(run, "written")
    return ctx.emit(ctx.envelope(next="report", run_id=run.checkpoint["run_id"], report_only=False,
                                 next_move=move_out, block=record["block"], writes=writes, events=events,
                                 pointer=pointer, checkpoint=checkpoint))
