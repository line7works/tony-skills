"""`fix` (CR-23; contract section 3.5): the executor's fixes, recorded against the named findings, held to the slice.

The fixes are the session's own hands, never a re-invocation of build-v2 and never a spec edit (v1's rule 3). The
executor hands one file (`references/answer.schema.json`, kind `fixes`): per fix the finding it answers (one of the
lap's named findings, `ship.json`'s `named`), the paths it touched or wants to touch, and one line on what changed;
and, separately, any fix that needs the spec changed (`spec_change`). In order:

1. **Refused, exit 5, nothing written, the run still at `fixing`:** a file for another lap; a fix naming a finding
   the lap did not name, or one finding twice; a path that is not workspace-relative (absolute, `..`, empty).
2. **The doc read again**, twice (CR-27): a doc that no longer reads cleanly, or no longer holds the slice, stops
   `doc-unreadable`.
3. **Stop 2** (`spec-change`): any `spec_change` entry.
4. **The window rule** (`window.py`, the E15 lane contract A28 (1)) over everything that moved since the last pin,
   with the fixes' declared paths as the paths this step names and the footprint read from the doc as it stands: the
   build doc moved (but by ship-v2's own `Status:` write) or declared is stop 2; a path outside the footprint, moved
   or declared, is stop 4; a path inside it that moved and no fix names is refused (exit 5): every change traces to a
   named finding.
5. Otherwise the lap's fixes are recorded (`fixes.json`), the workspace is pinned again (what moves after it is the
   recheck-v2 window's), and the run goes on to `recheck-v2`, or, for the MINORs the owner ordered after a clean
   signoff, to `report` (they never gate and never trigger a recheck).

`fixes.json` lands in the one save that ends the command (`common.save`, THE SAVE), with the state and the stage, or
with the stop: a kill never leaves the fixes recorded twice or recorded without the stage they moved the run to.
"""
import os

from . import common, doc as docmod, report, window


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
    declared = sorted(set(p for fix in given["fixes"] for p in fix["paths"]))
    held = window.hold(run, state, "since the lap's findings were named", named=declared, footprint=footprint)
    record = {"lap": state["lap"], "fixes": given["fixes"], "spec_change": given["spec_change"],
              "named": state["named"], "moved": held.moved, "declared": declared, "footprint": footprint}
    if given["spec_change"]:
        _keep(run, record, "stopped: spec-change")
        return report.ending(ctx, run, state, "spec-change",
                             "a fix needs the spec changed (%s): the run stops at condition 2 and builds no corrected "
                             "version" % "; ".join("%s: %s" % (s.get("finding") or "a finding", s["why"])
                                                  for s in given["spec_change"]), condition=2)
    if held.stop is not None:
        _keep(run, record, "stopped: %s" % held.stop[0])
        return report.ending(ctx, run, state, held.stop[0], held.stop[1], condition=held.stop[2])
    if held.refuse is not None:
        return common.refuse(ctx, run, held.refuse)
    _keep(run, record, "recorded")
    window.take(run, state)             # the post-fix pin: what moves after it is held at recheck-v2's opening
    if state.get("minors_only"):
        common.save(run, state, "clean")
        return ctx.emit(ctx.envelope(next="report", run_id=common.run_id(run), lap=state["lap"], recorded=declared,
                                     minors_only=True))
    common.save(run, state, "fixed")
    return ctx.emit(ctx.envelope(next="visit --station recheck-v2", run_id=common.run_id(run), lap=state["lap"],
                                 recorded=declared, moved=held.moved))


def _keep(run, record, outcome):
    """The lap's fixes file as handed over, with what became of it: `recorded`, or the stop it ended in (a stopped
    file's fixes are never listed as Fixed)."""
    laps = common.listing(run, "fixes.json", "laps")
    laps.append(dict(record, outcome=outcome))
    common.stage(run, "fixes.json", {"laps": laps})
