"""`pause` (CR-23, CR-24; contract section 3.7): a question to the owner, passed through; his answer, recorded.

`pause --question FILE` (`references/answer.schema.json`, kind `question`): a station's question to the owner (a
stop-and-ask, an owner-only ruling, a waiver decision; `source` `station` and the station that asked), or ship-v2's
own waive-or-hold question about a MAJOR only the owner can resolve (`source` `ship`). The text is passed through
verbatim and printed back; the run waits at the stage `paused`; nothing is written outside the run directory and no
trace line is written (a pause is no visit). While it waits every other phase is refused (exit 2): the script never
answers the question, and a pause is never turned into a stop (`report` does not run at `paused`).

`pause --answer FILE` (kind `answer`): the owner's answer to the open pause, his words verbatim, and its effect:
`resume` (the words go back to whoever asked; nothing is written), or `waive` or `reopen` with a finding's id: the
one write ship-v2 makes (ruling E15-9 as the E15 lane contract A27 (1) amends it; `grant.py`), a `waived` or
`reopened` event through `records.py append` carrying his words and, when the slice's card changes by v1's rule, its
`card_set` and the slice's `Status:` line, in build-v2's transaction (planned in `events.json` and never written on a
report-only run). Refused (exit 5, nothing written, the run still paused): an answer to another pause, words that are
blank, a grant on a finding the records do not hold, at a status the grant does not admit, or moving a card whose
`Status:` line disagrees with the records' card. A refusal the records component returns ends the run
(`records-refused`, its own sentence carried); a doc that moved between the append and the `Status:` write ends it
`outside-edit`. A grant transaction a kill cut off is settled by the next `pause --answer` before anything else
(`grant.settle`), and that answer is the receipt's. The run then resumes at the stage it paused at; a grant at
`fixing` renames the lap's findings from the records, and a reopening after ALL CLEAR (`clean`) that leaves a BLOCKER
or MAJOR open sends the run to the next lap (or, with none left, to stop condition 1): the record over the
recollection.
"""
from station_core import records_link

from . import common, grant, record, report


def ask(ctx, run, args):
    question, early = common.answer_file(ctx, run, args.question, "question", "question")
    if early is not None:
        return early
    stage = run.checkpoint["phase"]
    pauses = common.listing(run, "pauses.json", "pauses")
    number = len(pauses) + 1
    pauses.append({"pause": number, "stage": stage, "at": common.now(), "question": question, "answer": None})
    common.write(run, "pauses.json", {"pauses": pauses})
    state = common.state(run)
    state["paused_from"] = stage
    common.save(run, state)
    common.advance(run, "paused")
    return ctx.emit(ctx.envelope(next="pause --answer", run_id=common.run_id(run), pause=number,
                                 source=question["source"], asked_by=question.get("station"),
                                 question=question["text"],
                                 how="put the question to the owner verbatim and wait for his answer; never answer it, "
                                     "never turn it into a stop"))


def answer(ctx, run, args):
    receipt = grant.pending(run)
    settled = None
    if receipt is not None:
        pauses = common.listing(run, "pauses.json", "pauses")
        open_one = pauses[-1] if pauses and pauses[-1]["answer"] is None else None
        if open_one is None or open_one["pause"] != receipt["pause"]:
            grant.finished(run, receipt)       # an older grant whose bookkeeping already landed
        else:
            outcome, detail = grant.settle(ctx, run, receipt, args.records_root)
            if outcome != "replan":
                settled = "this run's grant transaction (receipt-%d.json) was settled before anything else: %s" % (
                    receipt["pause"], "its events were found in the records log and recorded as landed, and the doc "
                    "half was finished against the receipt's doc hash" if receipt.get("settled") else
                    "its outcome was in the receipt, and the doc half was finished against the receipt's doc hash")
                return _after_grant(ctx, run, args, receipt["answer"], outcome, detail, settled)
    given, early = common.answer_file(ctx, run, args.answer, "answer", "answer")
    if early is not None:
        return early
    pauses = common.listing(run, "pauses.json", "pauses")
    open_one = pauses[-1] if pauses and pauses[-1]["answer"] is None else None
    if open_one is None or given["pause"] != open_one["pause"]:
        return common.refuse(ctx, run, "the answer is for pause %r and the open pause is %r"
                             % (given["pause"], open_one and open_one["pause"]))
    if not given["words"].strip():
        return common.refuse(ctx, run, "the answer carries no words of the owner's: his answer is recorded verbatim, "
                                       "never stood in for")
    effect = given["effect"]
    if effect["kind"] not in record.GRANTS:
        return _after_grant(ctx, run, args, given, None, None, None)
    state = common.state(run)
    try:
        planned = grant.plan(run, effect["kind"], effect["finding"], given["words"], args.records_root)
    except grant.GrantRefused as exc:
        return common.refuse(ctx, run, "the owner's %s cannot be recorded: %s" % (effect["kind"], exc))
    except records_link.RecordsRefusal as exc:
        open_one["answer"] = dict(given, recorded=False)
        common.write(run, "pauses.json", {"pauses": pauses})
        return report.ending(ctx, run, state, "records-refused", records_link.refusal_sentence(
            exc, "recording the owner's %s" % effect["kind"]))
    if common.report_only(run):
        events = common.listing(run, "events.json", "events") + planned["events"]
        grants = common.listing(run, "events.json", "grants") + [{
            "pause": given["pause"], "kind": planned["kind"], "finding": planned["finding"], "words": planned["words"],
            "card": planned["card"], "appended": False, "log": None, "doc": None}]
        common.write(run, "events.json", {"events": events, "grants": grants})
        return _after_grant(ctx, run, args, given, None, None, None)
    outcome, detail = grant.execute(ctx, run, planned, given, args.records_root)
    return _after_grant(ctx, run, args, given, outcome, detail, None)


def _after_grant(ctx, run, args, given, outcome, detail, settled):
    """The answer's bookkeeping, once the grant's transaction (if any) is done or has ended the run: the events and the
    writes recorded in `events.json` once per grant, the pause answered, the run resumed where it paused (a grant at
    `fixing` names the lap's findings again from the records; a reopening after ALL CLEAR that leaves a BLOCKER or
    MAJOR open sends the run to the next lap, or, with none left, to `exhausted`), or ended when the transaction
    ended it (`records-refused`, `outside-edit`)."""
    pauses = common.listing(run, "pauses.json", "pauses")
    open_one = next((p for p in pauses if p["pause"] == given["pause"]), None)
    state = common.state(run)
    receipt = None
    if outcome in ("done", "outside-edit"):
        receipt = detail if outcome == "done" else grant.pending(run)
        rows = common.listing(run, "events.json", "grants")
        if not any(r.get("pause") == given["pause"] for r in rows):
            events = common.listing(run, "events.json", "events") + receipt["events"]
            rows.append(grant.grants_row(receipt, receipt.get("appended")))
            common.write(run, "events.json", {"events": events, "grants": rows})
    if outcome == "refused":
        open_one["answer"] = dict(given, recorded=False)
        common.write(run, "pauses.json", {"pauses": pauses})
        receipt = grant.pending(run)
        if receipt is not None:
            grant.finished(run, receipt)
        return report.ending(ctx, run, state, "records-refused", detail)
    if outcome == "outside-edit":
        open_one["answer"] = dict(given, recorded=True)
        common.write(run, "pauses.json", {"pauses": pauses})
        grant.finished(run, receipt)
        return report.ending(ctx, run, state, "outside-edit", detail)
    open_one["answer"] = dict(given, recorded=True)
    common.write(run, "pauses.json", {"pauses": pauses})
    effect = given["effect"]
    stage = state.get("paused_from") or "selected"
    state["paused_from"] = None
    if receipt is not None:
        state = grant.finish_pins(state, common.workspace(run), receipt)
    if effect["kind"] in record.GRANTS and not common.report_only(run):
        try:
            if stage == "fixing":
                state["named"] = record.named(run, state["slice"], args.records_root)
            elif stage == "clean" and state.get("visits"):
                still = record.blocking(record.named(run, state["slice"], args.records_root))
                if still:
                    state["named"] = still
                    stage = "lap-needed" if state["lap"] < common.laps_allowed(run) else "exhausted"
        except records_link.RecordsRefusal as exc:
            return report.ending(ctx, run, state, "records-refused", records_link.refusal_sentence(
                exc, "reading the findings after the owner's %s" % effect["kind"]))
    common.save(run, state)
    common.advance(run, stage)
    if receipt is not None:
        grant.finished(run, receipt)
    extra = {"settled": settled} if settled else {}
    if receipt is not None and receipt.get("card"):
        extra["card"] = receipt["card"]
    return ctx.emit(ctx.envelope(next=common.NEXT[stage], run_id=common.run_id(run), pause=given["pause"],
                                 effect=effect["kind"], words=given["words"], **extra))


def handler(ctx, args):
    """`pause --run-dir D (--question FILE | --answer FILE)`."""
    from station_core import driver
    if bool(args.question) == bool(args.answer):
        raise driver.Usage("pause takes one of --question FILE (a question to the owner) or --answer FILE (his answer)")
    if args.question:
        run = common.open_run(ctx, args.run_dir, common.PAUSABLE, "pause --question")
        return ask(ctx, run, args)
    run = common.open_run(ctx, args.run_dir, ("paused",), "pause --answer")
    return answer(ctx, run, args)
