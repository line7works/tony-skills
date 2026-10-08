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

THE WINDOW RULE (`window.py`, the E15 lane contract A28 (1)): an answer is a check point, held before the grant,
unless the pause was asked while a visit is open (that visit's close holds its window). A path inside the footprint
nothing names is refused (exit 5, still paused), or, at `fixing` and `lap-needed`, left for `fix`; the doc moved or a
path outside the footprint ends the run (stop 2 or 4) with the answer recorded with that ending and no grant written.
A grant's `Status:` write is recorded against the pin as ship-v2's own (`window.own`).

THE BOOKKEEPING (the E15 lane contract A29 (1), THE SAVE in `common.py`): the answer recorded in `pauses.json`, the
grant's rows in `events.json`, the receipt finished, the state and the stage land in one save, or with the stop that
ends the run there. A kill before that save leaves the run `paused` with nothing of the bookkeeping written, and the
next `pause --answer` settles the grant's transaction from its receipt (`grant.settle`) and saves the bookkeeping
once; a kill after it is finished by `common.recover` before the next command reads the run. A run directory that
holds an answer in `pauses.json` while the run is still `paused` (one a run before A29 could leave: slice 2 re-check
1's R1S2-3) is finished by the next `pause --answer` from the recorded answer and its receipt (`_finish_cut`),
whatever answer file is given, nothing written twice.
"""
from station_core import records_link

from . import common, grant, record, report, window


def ask(ctx, run, args):
    question, early = common.answer_file(ctx, run, args.question, "question", "question")
    if early is not None:
        return early
    stage = run.checkpoint["phase"]
    pauses = common.listing(run, "pauses.json", "pauses")
    number = len(pauses) + 1
    pauses.append({"pause": number, "stage": stage, "at": common.now(), "question": question, "answer": None})
    common.stage(run, "pauses.json", {"pauses": pauses})
    state = common.state(run)
    state["paused_from"] = stage
    common.save(run, state, "paused")
    return ctx.emit(ctx.envelope(next="pause --answer", run_id=common.run_id(run), pause=number,
                                 source=question["source"], asked_by=question.get("station"),
                                 question=question["text"],
                                 how="put the question to the owner verbatim and wait for his answer; never answer it, "
                                     "never turn it into a stop"))


# the stages a pause's answer leaves an unnamed inside path for `fix` to name (a lap's fixes are open)
FIXING = ("fixing", "lap-needed")


def answer(ctx, run, args):
    pauses = common.listing(run, "pauses.json", "pauses")
    last = pauses[-1] if pauses else None
    if last is not None and last["answer"] is not None:
        return _finish_cut(ctx, run, args, last)
    receipt = grant.pending(run)
    if receipt is not None:
        if last is None or last["pause"] != receipt["pause"]:
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
    state = common.state(run)
    stage = state.get("paused_from")
    if stage != "visiting":                 # a pause inside an open visit is that visit's window, held at its close
        held = window.hold(run, state, "before the owner's answer to pause %d" % open_one["pause"],
                           leave_inside=stage in FIXING)
        if held.refuse is not None:
            return common.refuse(ctx, run, held.refuse)
        if held.stop is not None:
            ended = {"tag": held.stop[0], "reason": held.stop[1], "condition": held.stop[2]}
            open_one["answer"] = dict(given, recorded=False, ended=ended)
            common.stage(run, "pauses.json", {"pauses": pauses})
            return report.ending(ctx, run, state, ended["tag"], ended["reason"], condition=ended["condition"])
    effect = given["effect"]
    if effect["kind"] not in record.GRANTS:
        return _after_grant(ctx, run, args, given, None, None, None)
    try:
        planned = grant.plan(run, effect["kind"], effect["finding"], given["words"], args.records_root)
    except grant.GrantRefused as exc:
        return common.refuse(ctx, run, "the owner's %s cannot be recorded: %s" % (effect["kind"], exc))
    except records_link.RecordsRefusal as exc:
        reason = records_link.refusal_sentence(exc, "recording the owner's %s" % effect["kind"])
        open_one["answer"] = dict(given, recorded=False, ended={"tag": "records-refused", "reason": reason,
                                                                 "condition": None})
        common.stage(run, "pauses.json", {"pauses": pauses})
        return report.ending(ctx, run, state, "records-refused", reason)
    if common.report_only(run):
        grants = common.listing(run, "events.json", "grants")
        if not any(r.get("pause") == given["pause"] for r in grants):
            events = common.listing(run, "events.json", "events") + planned["events"]
            grants.append({"pause": given["pause"], "kind": planned["kind"], "finding": planned["finding"],
                           "words": planned["words"], "card": planned["card"], "appended": False, "log": None,
                           "doc": None})
            common.stage(run, "events.json", {"events": events, "grants": grants})
        return _after_grant(ctx, run, args, given, None, None, None)
    outcome, detail = grant.execute(ctx, run, planned, given, args.records_root)
    return _after_grant(ctx, run, args, given, outcome, detail, None)


def _after_grant(ctx, run, args, given, outcome, detail, settled):
    """The answer's bookkeeping, once the grant's transaction (if any) is done or has ended the run: the events and the
    writes recorded in `events.json` once per grant; the answer recorded in `pauses.json`; then `_resume`. A
    transaction that ended the run (`records-refused`, `outside-edit`) records the answer with that ending and ends
    it."""
    pauses = common.listing(run, "pauses.json", "pauses")
    open_one = next((p for p in pauses if p["pause"] == given["pause"]), None)
    receipt = None
    if outcome in ("done", "outside-edit"):
        receipt = detail if outcome == "done" else grant.pending(run)
        rows = common.listing(run, "events.json", "grants")
        if not any(r.get("pause") == given["pause"] for r in rows):
            events = common.listing(run, "events.json", "events") + receipt["events"]
            rows.append(grant.grants_row(receipt, receipt.get("appended")))
            common.stage(run, "events.json", {"events": events, "grants": rows})
    if outcome in ("refused", "outside-edit"):
        tag = "records-refused" if outcome == "refused" else "outside-edit"
        open_one["answer"] = dict(given, recorded=outcome == "outside-edit",
                                  ended={"tag": tag, "reason": detail, "condition": None})
        common.stage(run, "pauses.json", {"pauses": pauses})
        receipt = receipt or grant.pending(run)
        if receipt is not None:
            grant.finished(run, receipt)
        return report.ending(ctx, run, common.state(run), tag, detail)
    open_one["answer"] = dict(given, recorded=True)
    common.stage(run, "pauses.json", {"pauses": pauses})
    grant.hold_point("answered")
    return _resume(ctx, run, args, given, receipt, settled)


def _resume(ctx, run, args, given, receipt, settled):
    """The run resumed where it paused (a grant at `fixing` names the lap's findings again from the records; a
    reopening after ALL CLEAR that leaves a BLOCKER or MAJOR open sends the run to the next lap, or, with none left, to
    `exhausted`); ship-v2's own `Status:` write recorded against the pin (the window rule's sanctioned write); the
    receipt finished, the answer, the state and the stage in one save."""
    state = common.state(run)
    effect = given["effect"]
    stage = state.get("paused_from") or "selected"
    state["paused_from"] = None
    window.own(state, receipt)
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
    if receipt is not None:
        grant.finished(run, receipt)
    common.save(run, state, stage)          # the answer, the receipt finished, the state and the stage: one save
    extra = {"settled": settled} if settled else {}
    if receipt is not None and receipt.get("card"):
        extra["card"] = receipt["card"]
    return ctx.emit(ctx.envelope(next=common.NEXT[stage], run_id=common.run_id(run), pause=given["pause"],
                                 effect=effect["kind"], words=given["words"], **extra))


def _finish_cut(ctx, run, args, last):
    """The run is still `paused` and its last pause already holds an answer: a kill cut the answer's bookkeeping off
    after `pauses.json` recorded it (slice 2 re-check 1's R1S2-3). The bookkeeping is finished from the recorded
    answer and its receipt, whatever answer file is given, and nothing is written twice: an answer that ended the run
    ends it the same way; any other resumes the run where it paused."""
    recorded = last["answer"]
    given = dict((k, v) for k, v in recorded.items() if k not in ("recorded", "ended"))
    receipt = grant.receipt_of(run, last["pause"])
    ended = recorded.get("ended")
    if ended or not recorded.get("recorded"):
        ended = ended or {"tag": "records-refused", "reason": "the owner's answer to pause %d was not recorded"
                                                              % last["pause"], "condition": None}
        if receipt is not None and not receipt.get("finished"):
            grant.finished(run, receipt)
        return report.ending(ctx, run, common.state(run), ended["tag"], ended["reason"],
                             condition=ended.get("condition"))
    usable = receipt if receipt is not None and receipt.get("appended") is not None and not receipt.get("stop") \
        else None
    return _resume(ctx, run, args, given, usable, "the answer to pause %d was recorded and its bookkeeping was cut off "
                                                "before the run left `paused`; it was finished first, from the "
                                                "recorded answer%s, and nothing was written twice"
                   % (last["pause"], " and its receipt" if usable is not None else ""))


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
