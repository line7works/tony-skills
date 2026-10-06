"""`lap` (CR-22; contract section 3.6): the lap counter, hard.

One initial pass (lap 1: the fixes after signoff-v2, then recheck-v2) and at most one extra fix-and-recheck lap
(lap 2). `lap` opens the next lap after a recheck that is not ALL CLEAR: the run goes back to `fixing`, with the
findings the records still hold open for the slice named. The pin is NOT taken again here (slice 2 check 1's C2-1):
recheck-v2's result took the next lap's pin, after the station's own writes, and `lap` keeps it, so what moved since
is held first: the doc moved is stop 2 and a path outside the footprint is stop 4, before the lap opens; a path
inside it is the next lap's fix to name (`fix` refuses it unnamed). A run that never took a pin (a reopening after a
clean signoff) takes it here. A lap beyond the allowed count
is refused (exit 5, nothing written, the run where it was); the allowed count is two, plus the count the owner's
words in the input give (`station.extra_laps`: `count` and his `words`, verbatim), and a lap those words open
records them verbatim in `laps.json` and the result. The counter never resets. The trace's line shape is a frozen
back-frame file with no field for words, so the words are not on the trace (the slice 2 report's numbered question).
"""
from station_core import records_link
from back_core import trace

from . import common, doc as docmod, pin, record, report


def handler(ctx, args):
    """`lap --run-dir D`."""
    run = common.open_run(ctx, args.run_dir, ("lap-needed", "exhausted"), "lap")
    state = common.state(run)
    allowed = common.laps_allowed(run)
    rechecks = len([l for l in trace.read(run.run_dir) if l["kind"] == "visit" and l["expected"] == "recheck-v2"
                    and l["status"] != "visiting"])
    taken = max(state["lap"], rechecks, len(common.listing(run, "laps.json", "laps")))
    if taken >= allowed:
        return common.refuse(ctx, run, "lap %d would be beyond the %d the run allows (one initial pass and one extra "
                                       "fix-and-recheck lap%s): a further lap happens only on the owner's words in the "
                                       "input, never on momentum; run `report`, which ends at stop condition 1"
                             % (taken + 1, allowed, "" if allowed == 2 else ", and the laps the owner's words named"))
    ws = common.workspace(run)
    if state.get("pin"):
        moved = pin.moved(ws, state["pin"])
        if state["doc"] in moved:
            return report.ending(ctx, run, state, "spec-change", "the build doc %s moved after recheck-v2's result and "
                                                                  "before the next lap: a fix is never a spec edit, so "
                                                                  "the run stops at condition 2" % state["doc"],
                                 condition=2)
        outside = [p for p in moved if not docmod.in_footprint(p, state["footprint"])]
        if outside:
            return report.ending(ctx, run, state, "outside-footprint", "after recheck-v2's result and before the next "
                                                                       "lap, files outside slice %s's footprint moved: "
                                                                       "%s; the run stops at condition 4"
                                 % (state["slice"], ", ".join(outside)), condition=4)
    lap = taken + 1
    words = (common.station(run).get("extra_laps") or {}).get("words") if lap > 2 else None
    laps = common.listing(run, "laps.json", "laps")
    laps.append({"lap": lap, "opened_at": common.now(), "owner_words": words})
    common.write(run, "laps.json", {"laps": laps})
    try:
        named = state["named"] if common.report_only(run) else record.named(run, state["slice"], args.records_root)
    except records_link.RecordsRefusal as exc:
        return report.ending(ctx, run, state, "records-refused", records_link.refusal_sentence(
            exc, "reading the findings the next lap fixes"))
    state.update(lap=lap, named=named, pin=state.get("pin") or pin.take(ws), fixed_pin=None, minors_only=False)
    common.save(run, state)
    common.advance(run, "fixing")
    return ctx.emit(ctx.envelope(next="fix", run_id=common.run_id(run), lap=lap, named=named, owner_words=words))
