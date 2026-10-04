"""`select`: the doc hunt, the reading, the identity (contract section 3.1; rulings E15-10, CR-15, CR-17; A2 Q4).

The hunt is v1's repo tiers through the copied `hunt.py` (three outcomes, never a silent pick), with v1's order:
the file names of `docs/plans/` and of the older flat build plans first (a `docs/plans/` match wins over a flat one,
and the result names the flat doc it passed over), then an `Intent:` line, consulted only when no file name in
either matches, then a phase or slice doc under `docs/` or `plan/`. No vault tier (A2, Q4). `--doc` takes the doc
the invocation names, or the plan this session established when the hunt found none. An invocation that names
nothing to match against stops and asks (`selection-unnamed`), never the lone doc on disk.

The doc is then read by vertical-v2's line rules (`doc.read`, CR-17): any line they refuse stops the run
(`doc-unreadable`) before anything else, naming it. A handoff block outside `## Handoffs` stops it
(`block-misplaced`). The identity is derived one way (`doc.identity`); none stops and asks (`identity-unnamed`); an
owner's name in the input is taken only when none derives, and one that differs from a derived identity stops
(`identity-conflict`).
"""
import glob
import os
import re

from station_core import driver, fsio, hunt as huntmod

from . import common, doc as docmod, fences, report

HOMES = [
    {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md", "docs/plans/{name}.md"], "tier": 1},
    {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
]
PHASE = [{"home": "phase-or-slice", "root": "workspace", "globs": ["docs/*phase*.md", "docs/*slice*.md", "plan/*.md"],
          "tier": 3}]
INTENT_GLOBS = ("docs/plans/*.md", "docs/*-build-plan.md")


def _named(ws, path):
    real_ws = os.path.realpath(ws)
    full = path if os.path.isabs(path) else os.path.join(real_ws, path)
    real = os.path.realpath(full)
    if not real.startswith(real_ws.rstrip(os.sep) + os.sep) or not real.endswith(".md") or not os.path.isfile(real):
        return None
    return os.path.relpath(real, real_ws)


def _intent_line(path):
    """The doc's first `Intent:` line outside an accepted fence (fences.scan), or None."""
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return None
    lines = fences.split_lines(text)
    fenced = fences.scan(lines).fenced
    for number, raw in enumerate(lines, 1):
        line = fences.bare(raw, number)
        if number not in fenced and line.startswith("Intent:"):
            return line[len("Intent:"):]
    return None


def _intent_hunt(ws, name):
    """The docs whose `Intent:` line holds every word of the name (split on `-`, `.` and `_`), as whole words, in any
    letter case. A literal rule: anything subtler is the executor's `--doc`."""
    words = [w for w in re.split(r"[-._]", name) if w]
    found = []
    for pattern in INTENT_GLOBS:
        for path in sorted(glob.glob(os.path.join(glob.escape(ws), pattern))):
            if not os.path.isfile(path) or not fsio.inside(path, ws):
                continue
            intent = _intent_line(path)
            if intent is None:
                continue
            have = set(re.findall(r"[a-z0-9]+", intent.casefold()))
            if words and all(w.casefold() in have for w in words):
                found.append(os.path.normpath(path))
    return sorted(set(found))


def handler(ctx, args):
    """`select --run-dir D [--doc PATH] [--name NAME]`."""
    run = common.open_run(ctx, args.run_dir, ("checked",), "select")
    ws = common.workspace(run)
    selection = {"how": None, "outcome": None, "candidates": [], "searched": [], "name": args.name}
    notes = []
    if args.doc:
        doc = _named(ws, args.doc)
        if doc is None:
            return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"],
                                         reason="the named build doc is not an existing .md file inside the workspace: %s"
                                                % args.doc), 5)
        selection.update(how="named", outcome="one", candidates=[doc])
    elif not args.name:
        common.write(run, "selection.json", selection)
        report.finish(ctx, run, "stopped", "selection-unnamed",
                      "the invocation names nothing to match a build doc against: ask the owner which build doc this "
                      "handoff is for, and run again with --name or --doc (the lone doc on disk is never taken)",
                      selection=selection)
    else:
        try:
            found = huntmod.hunt(HOMES, {"workspace": ws}, name=args.name)
        except huntmod.HuntRefused as exc:
            raise driver.Usage(str(exc))
        selection.update(how="file-name", outcome=found["outcome"], searched=found["searched"],
                         candidates=[os.path.relpath(c["path"], ws) for c in found["candidates"]])
        if found["outcome"] == "one":
            passed = [os.path.relpath(p, ws) for row in found["searched"] if row["tier"] > found["candidates"][0]["tier"]
                      for p in row["found"]]
            for path in passed:
                notes.append("the docs/plans/ doc wins over the flat doc that also matches by file name: %s" % path)
        if found["outcome"] == "none":
            intent = _intent_hunt(ws, args.name)
            if intent:
                selection.update(how="intent-line", outcome="one" if len(intent) == 1 else "several",
                                 candidates=[os.path.relpath(p, ws) for p in intent])
            else:
                phase = huntmod.hunt(PHASE, {"workspace": ws}, name=args.name)
                selection.update(how="phase-or-slice", outcome=phase["outcome"],
                                 searched=selection["searched"] + phase["searched"],
                                 candidates=[os.path.relpath(c["path"], ws) for c in phase["candidates"]])
        if selection["outcome"] == "none":
            common.write(run, "selection.json", selection)
            report.finish(ctx, run, "stopped", "selection-none",
                          "no build doc matches %r in the repo's tiers (docs/plans/, then docs/<feature>-build-plan.md, "
                          "then an Intent: line, then a phase or slice doc): ask the owner which build doc this is, and "
                          "run again with --doc" % args.name, selection=selection)
        if selection["outcome"] == "several":
            common.write(run, "selection.json", selection)
            report.finish(ctx, run, "stopped", "selection-several",
                          "several build docs match (%s): list them for the owner and run again with --doc naming his "
                          "pick; none is picked here" % ", ".join(selection["candidates"]), selection=selection)
        doc = selection["candidates"][0]
    selection["doc"] = doc
    common.write(run, "selection.json", selection)
    data = common.read_doc_bytes(ws, doc)
    try:
        text = common.decode(data)
        parsed = docmod.read(text)
    except UnicodeDecodeError as exc:
        report.finish(ctx, run, "stopped", docmod.STOP_TAG, "the build doc %s is not UTF-8 text (%s): handoff-v2 "
                      "reads no other encoding; nothing was written" % (doc, exc), selection=selection)
    except docmod.DocUnreadable as exc:
        report.finish(ctx, run, "stopped", docmod.STOP_TAG,
                      "the build doc %s cannot be read by vertical-v2's line rules at line %d, so nothing is decided "
                      "from it and nothing was written: %s. The plan's author edits that line, then run again"
                      % (doc, exc.line, exc.words), selection=selection)
    if parsed.misplaced:
        lines = ", ".join("line %d (%s)" % (b["line"], b["date"]) for b in parsed.misplaced)
        report.finish(ctx, run, "stopped", "block-misplaced",
                      "a handoff block sits outside `## Handoffs` (%s): the blocks live in one section and are never "
                      "moved by a handoff, so the owner settles where they belong before this run writes; nothing was "
                      "written" % lines, selection=selection)
    feature, how = docmod.identity(doc, text)
    given = common.station(run).get("feature")
    if feature is None and given:
        feature, how = given["name"], "owner"
    elif feature is not None and given and given.get("name") != feature:
        report.finish(ctx, run, "stopped", "identity-conflict",
                      "the doc's identity derives as %r (%s) and the input names %r: the identity is derived one way "
                      "per doc, and the owner's name is taken only when none derives; nothing was written"
                      % (feature, how, given.get("name")), selection=selection)
    if feature is None:
        report.finish(ctx, run, "stopped", "identity-unnamed",
                      "the doc %s yields no identity (not a dated plan, not a flat build plan, and no title line to "
                      "slug): ask the owner to name it, and run again with his name in station.feature; never "
                      "guessed" % doc, selection=selection)
    view = {"doc": doc, "sha256": fsio.sha256_bytes(data), "feature": feature, "identity_how": how, "notes": notes,
            "slices": [{"name": s["name"], "line": s["line"], "status": s["status"], "depends": s["depends"],
                        "questions": s["questions"]} for s in parsed.slices],
            "blocks": [{"date": b["date"], "line": b["line"], "text": docmod.block_text(parsed, b)}
                       for b in parsed.blocks],
            "handoffs": parsed.handoffs is not None, "punch": parsed.punch is not None}
    common.write(run, "doc.json", view)
    common.advance(run, "selected")
    return ctx.emit(ctx.envelope(next="photograph", run_id=run.checkpoint["run_id"], doc=doc, feature=feature,
                                 identity_how=how, selection=selection, notes=notes,
                                 slices=[s["name"] for s in parsed.slices]))
