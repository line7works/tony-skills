"""`pause` (CR-23, CR-24; contract section 3.7): a question to the owner, passed through; his answer, recorded.

`pause --question FILE` (`references/answer.schema.json`, kind `question`): a station's question to the owner (a
stop-and-ask, an owner-only ruling, a waiver decision; `source` `station` and the station that asked), or ship-v2's
own waive-or-hold question about a MAJOR only the owner can resolve (`source` `ship`). The text is passed through
verbatim and printed back; the run waits at the stage `paused`; nothing is written outside the run directory and no
trace line is written (a pause is no visit). While it waits every other phase is refused (exit 2): the script never
answers the question, and a pause is never turned into a stop (`report` does not run at `paused`).

`pause --answer FILE` (kind `answer`): the owner's answer to the open pause, his words verbatim, and its effect:
`resume` (the words go back to whoever asked; nothing is written), or `waive` or `reopen` with a finding's id: the
one write ship-v2 makes (ruling E15-9), a `waived` or `reopened` event through `records.py append` carrying his words
(`record.grant`; planned in `events.json` and never appended on a report-only run). Refused (exit 5, nothing written,
the run still paused): an answer to another pause, words that are blank, a grant on a finding the records do not
hold, or at a status the grant does not admit. A refusal the records component returns ends the run
(`records-refused`, its own sentence carried). The run then resumes at the stage it paused at; a grant at `fixing`
renames the lap's findings from the records, and a reopening after ALL CLEAR (`clean`) that leaves a BLOCKER or
MAJOR open sends the run to the next lap (or, with none left, to stop condition 1): the record over the recollection.
"""
from station_core import records_link

from . import common, record, report


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
    state = common.state(run)
    effect = given["effect"]
    if effect["kind"] in record.GRANTS:
        try:
            event, appended, rows = record.grant(run, effect["kind"], effect["finding"], given["words"],
                                                 args.records_root)
        except record.GrantRefused as exc:
            return common.refuse(ctx, run, "the owner's %s cannot be recorded: %s" % (effect["kind"], exc))
        except records_link.RecordsRefusal as exc:
            open_one["answer"] = dict(given, recorded=False)
            common.write(run, "pauses.json", {"pauses": pauses})
            return report.ending(ctx, run, state, "records-refused", records_link.refusal_sentence(
                exc, "recording the owner's %s" % effect["kind"]))
        events = common.listing(run, "events.json", "events")
        outcomes = common.listing(run, "events.json", "outcomes")
        events.append(event)
        if appended:
            outcomes.append(dict(rows[0], appended=True))
        else:
            outcomes.append({"appended": False, "path": None, "kind": None, "sha256_before": None,
                             "sha256_after": None, "head_before": None, "head_after": None})
        common.write(run, "events.json", {"events": events, "outcomes": outcomes})
    open_one["answer"] = dict(given, recorded=True)
    common.write(run, "pauses.json", {"pauses": pauses})
    stage = state.get("paused_from") or "selected"
    state["paused_from"] = None
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
    return ctx.emit(ctx.envelope(next=common.NEXT[stage], run_id=common.run_id(run), pause=given["pause"],
                                 effect=effect["kind"], words=given["words"]))


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
