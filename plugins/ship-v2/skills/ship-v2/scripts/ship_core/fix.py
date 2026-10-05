"""`fix` (CR-23; contract section 3.5): the executor's fixes, recorded against the named findings, held to the slice.

The fixes are the session's own hands, never a re-invocation of build-v2 and never a spec edit (v1's rule 3). The
executor hands one file (`references/answer.schema.json`, kind `fixes`): per fix the finding it answers (one of the
lap's named findings, `ship.json`'s `named`), the paths it touched or wants to touch, and one line on what changed;
and, separately, any fix that needs the spec changed (`spec_change`). In order:

1. **Refused, exit 5, nothing written, the run still at `fixing`:** a file for another lap; a fix naming a finding
   the lap did not name, or one finding twice; a path that is not workspace-relative (absolute, `..`, empty).
2. **The doc read again**, twice (CR-27): a doc that no longer reads cleanly, or no longer holds the slice, stops
   `doc-unreadable`.
3. **Stop 2** (`spec-change`): any `spec_change` entry, or a fix that touches the build doc (declared, or moved since
   the pin): the doc holds the slice's spec, and ship-v2 writes nothing into it.
4. **Stop 4** (`outside-footprint`): any path declared or moved since the pin (`pin.py`; `docs/records/` aside) that
   lies outside the slice's footprint, read from the doc as it stands, contained by build-v2's rule (`doc.py`).
5. **Refused, exit 5:** a path moved since the pin, inside the footprint, that no fix names: every change traces to a
   named finding.
6. Otherwise the lap's fixes are recorded (`fixes.json`), and the run goes on to `recheck-v2`, or, for the MINORs
   the owner ordered after a clean signoff, to `report` (they never gate and never trigger a recheck).
"""
import os

from . import common, doc as docmod, pin, report


def _relative(path):
    return isinstance(path, str) and path and not os.path.isabs(path) and ".." not in path.split("/") and \
        "\\" not in path and path == os.path.normpath(path)


def handler(ctx, args):
    """`fix --run-dir D --fixes FILE`."""
    run = common.open_run(ctx, args.run_dir, ("fixing",), "fix")
    given, early = common.answer_file(ctx, run, args.fixes, "fixes", "fixes")
    if early is not None:
        return early
    state = common.state(run)
    if given["lap"] != state["lap"]:
        return common.refuse(ctx, run, "the fixes file is for lap %d, and this is lap %d" % (given["lap"], state["lap"]))
    named = dict((n["id"], n) for n in state["named"])
    seen = set()
    for fix in given["fixes"]:
        if fix["finding"] not in named:
            return common.refuse(ctx, run, "the fix %r names %r, which is not a finding this lap named (%s): a fix "
                                           "traces to a named finding" % (fix["summary"], fix["finding"],
                                                                          ", ".join(sorted(named)) or "none"))
        if fix["finding"] in seen:
            return common.refuse(ctx, run, "the finding %s is fixed twice in one file: one entry per finding, every "
                                           "path it touched in it" % fix["finding"])
        seen.add(fix["finding"])
        bad = [p for p in fix["paths"] if not _relative(p)]
        if bad:
            return common.refuse(ctx, run, "the fix of %s names a path that is not workspace-relative: %s"
                                 % (fix["finding"], ", ".join(repr(p) for p in bad)))
    ws = common.workspace(run)
    try:
        parsed = docmod.read(common.read_doc_bytes(ws, state["doc"]).decode("utf-8"))
        row = docmod.slice_of(parsed, state["slice"])
        if row is None:
            raise docmod.DocUnreadable(1, "the doc no longer holds slice %s" % state["slice"])
    except (OSError, UnicodeDecodeError) as exc:
        return report.ending(ctx, run, state, docmod.STOP_TAG, "the build doc %s cannot be read now (%s), so the "
                                                                "footprint cannot be read; nothing was recorded"
                             % (state["doc"], exc))
    except docmod.DocUnreadable as exc:
        return report.ending(ctx, run, state, docmod.STOP_TAG,
                             "the build doc %s cannot be read cleanly at line %d now (vertical-v2's line rules, then "
                             "its second, CommonMark reading), so the slice's footprint cannot be read and no fix is "
                             "recorded: %s" % (state["doc"], exc.line, exc.words))
    footprint = row["footprint"]
    moved = pin.moved(ws, state["pin"])
    declared = sorted(set(p for fix in given["fixes"] for p in fix["paths"]))
    record = {"lap": state["lap"], "fixes": given["fixes"], "spec_change": given["spec_change"],
              "named": state["named"], "moved": moved, "declared": declared, "footprint": footprint}
    if given["spec_change"]:
        _keep(run, record, "stopped: spec-change")
        return report.ending(ctx, run, state, "spec-change",
                             "a fix needs the spec changed (%s): the run stops at condition 2 and builds no corrected "
                             "version" % "; ".join("%s: %s" % (s.get("finding") or "a finding", s["why"])
                                                  for s in given["spec_change"]), condition=2)
    if state["doc"] in moved or state["doc"] in declared:
        _keep(run, record, "stopped: spec-change")
        return report.ending(ctx, run, state, "spec-change",
                             "a fix touches the build doc %s, which holds the slice's spec: a fix is never a spec edit, "
                             "so the run stops at condition 2" % state["doc"], condition=2)
    outside = [p for p in sorted(set(moved) | set(declared)) if not docmod.in_footprint(p, footprint)]
    if outside:
        _keep(run, record, "stopped: outside-footprint")
        return report.ending(ctx, run, state, "outside-footprint",
                             "a fix wants files outside slice %s's footprint (%s): %s; the run stops at condition 4"
                             % (state["slice"], ", ".join(footprint) or "the slice names no path",
                                ", ".join(outside)), condition=4)
    undeclared = [p for p in moved if p not in declared]
    if undeclared:
        return common.refuse(ctx, run, "a path moved since the lap began that no fix names: %s; every change traces to "
                                       "a named finding, so name it in the fix it belongs to" % ", ".join(undeclared))
    _keep(run, record, "recorded")
    if state.get("minors_only"):
        common.save(run, state)
        common.advance(run, "clean")
        return ctx.emit(ctx.envelope(next="report", run_id=common.run_id(run), lap=state["lap"], recorded=declared,
                                     minors_only=True))
    common.advance(run, "fixed")
    return ctx.emit(ctx.envelope(next="visit --station recheck-v2", run_id=common.run_id(run), lap=state["lap"],
                                 recorded=declared, moved=moved))


def _keep(run, record, outcome):
    """The lap's fixes file as handed over, with what became of it: `recorded`, or the stop it ended in (a stopped
    file's fixes are never listed as Fixed)."""
    laps = common.listing(run, "fixes.json", "laps")
    laps.append(dict(record, outcome=outcome))
    common.write(run, "fixes.json", {"laps": laps})
