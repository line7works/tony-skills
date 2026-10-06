"""`select`: the narrowed hunt and the reading (contract section 3.1; rulings E15-10, CR-27).

A doc named in the invocation is the doc (`--doc`). Otherwise the sources are exactly two, v1's deliberate narrowing
of the build hunt: the repo's tiers, matched by the name the invocation gives (`--name`; the copied `hunt.py`, three
outcomes, never a silent pick: `docs/plans/*-<name>.md` and `docs/plans/<name>.md`, then the flat
`docs/<name>-build-plan.md`), and the plan established in the session (`--doc`). No vault, no other repository, no
home directory, no narrowing heuristic across candidates. Nothing named, nothing found, several found, or a slice
the doc does not hold (or none named) is a PAUSE that asks the owner what he wants built: exit 0, `paused`, the
question, `next` `select`, and nothing written anywhere, the run still at `checked` (never a stop, never a wider
hunt, never the lone doc on disk). `--slice` takes the owner's answer when the input named no slice.

The doc found is read twice (`doc.read`, CR-27): a line the line rules refuse, or the first line where the second,
CommonMark reading takes a decision differently, stops the run `doc-unreadable` naming it, before any visit and
before any write. Writes `ship.json` (the doc, its hash, the slice, its card and its footprint).
"""
import os

from station_core import driver, fsio, hunt as huntmod, records_link

from . import common, doc as docmod, grant, report

HOMES = [
    {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md", "docs/plans/{name}.md"], "tier": 1},
    {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
]


def _named(ws, path):
    real_ws = os.path.realpath(ws)
    full = path if os.path.isabs(path) else os.path.join(real_ws, path)
    real = os.path.realpath(full)
    if not real.startswith(real_ws.rstrip(os.sep) + os.sep) or not real.endswith(".md") or not os.path.isfile(real):
        return None
    rel = os.path.relpath(real, real_ws)
    if rel.startswith(("docs/records/", "docs/reviews/")):
        return None
    return rel


def drift_reason(row, event):
    """`card-drift`'s words (the E15 lane contract A27 (1) with A24 (1)): both values and both ways out."""
    actor = event.get("actor") or {}
    station, run_id = actor.get("station") or "a station", actor.get("run_id")
    resume = ("run that ship-v2 run's next command, `ship.py pause --run-dir <the run directory of run %s> --answer "
              "<its answer file>`, which settles the doc half first" % run_id if station == common.STATION else
              "resume the interrupted %s run %s by its own SKILL.md, which settles its doc half" % (station, run_id))
    return ("slice %s's Status: line reads %r, the card the records' last card move for it started from, and that move "
            "(a card_set at seq %s by %s run %s, %r to %r) is in the log: its event landed and its Status: line did "
            "not, so the doc contradicts the record and this run visits nothing; nothing was written. Two ways out: "
            "%s; or set the line to the card the records hold, `Status: %s`, by hand. Then run ship-v2 again"
            % (row["name"], row["status"], event.get("seq"), station, run_id, event.get("before"), event.get("after"),
               resume, event.get("after")))


def _pause(ctx, run, why, question, **extra):
    return ctx.emit(ctx.envelope(next="select", run_id=common.run_id(run), paused=True, why=why, question=question,
                                 **extra))


def handler(ctx, args):
    """`select --run-dir D [--doc PATH | --name NAME] [--slice NAME]`."""
    run = common.open_run(ctx, args.run_dir, ("checked",), "select")
    ws = common.workspace(run)
    given = common.station(run).get("slice")
    if args.slice and given and args.slice != given:
        raise driver.Usage("the input names slice %r and --slice names %r: --slice takes the owner's answer only when "
                           "the input named no slice" % (given, args.slice))
    slice_name = given or args.slice
    if args.doc:
        doc = _named(ws, args.doc)
        if doc is None:
            return common.refuse(ctx, run, "the named build doc is not an existing .md file inside the workspace (and "
                                           "not under docs/records/ or docs/reviews/): %s" % args.doc)
        selection = {"how": "named", "candidates": [doc]}
    elif not args.name:
        return _pause(ctx, run, "selection-unnamed", "The invocation names no build doc. Which build doc and which "
                                                     "slice do you want shipped? (the doc on disk is never taken "
                                                     "unasked)")
    else:
        try:
            found = huntmod.hunt(HOMES, {"workspace": ws}, name=args.name)
        except huntmod.HuntRefused as exc:
            raise driver.Usage(str(exc))
        candidates = [os.path.relpath(c["path"], ws) for c in found["candidates"]]
        if found["outcome"] == "none":
            return _pause(ctx, run, "selection-none", "No build doc in this repo matches %r (docs/plans/, then "
                                                      "docs/<name>-build-plan.md). Which build doc do you want "
                                                      "shipped?" % args.name)
        if found["outcome"] == "several":
            return _pause(ctx, run, "selection-several", "Several build docs match %r: %s. Which one do you want "
                                                         "shipped?" % (args.name, ", ".join(candidates)),
                          candidates=candidates)
        doc = candidates[0]
        selection = {"how": "file-name", "candidates": candidates}
    data = common.read_doc_bytes(ws, doc)
    facts = {"doc": doc, "slice": slice_name, "selection": selection, "doc_sha256": fsio.sha256_bytes(data)}
    try:
        parsed = docmod.read(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        return report.ending(ctx, run, facts, docmod.STOP_TAG, "the build doc %s is not UTF-8 text (%s): ship-v2 reads "
                                                                "no other encoding; nothing was visited or written"
                             % (doc, exc))
    except docmod.DocUnreadable as exc:
        return report.ending(ctx, run, facts, docmod.STOP_TAG,
                             "the build doc %s cannot be read cleanly at line %d (vertical-v2's line rules, then its "
                             "second, CommonMark reading), so nothing is decided from it and nothing was visited or "
                             "written: %s. The plan's author edits that line, then run again" % (doc, exc.line,
                                                                                               exc.words))
    names = [s["name"] for s in parsed.slices]
    if not slice_name:
        return _pause(ctx, run, "slice-unnamed", "Which slice of %s do you want shipped? (its slices: %s)"
                      % (doc, ", ".join(names) or "none"), doc=doc, slices=names)
    row = docmod.slice_of(parsed, slice_name)
    if row is None:
        return _pause(ctx, run, "slice-unknown", "%s holds no slice %r (its slices: %s). Which slice do you want "
                                                 "shipped?" % (doc, slice_name, ", ".join(names) or "none"),
                      doc=doc, slices=names)
    try:
        cli = records_link.open_client(common.STATION, records_root=args.records_root)
        moves = cli.events(ws, doc, kind="card_set").get("results") or []
    except records_link.RecordsRefusal as exc:
        return report.ending(ctx, run, facts, "records-refused", records_link.refusal_sentence(
            exc, "reading the card moves of %s" % doc))
    drifted = grant.drift(moves, row)
    if drifted is not None:
        return report.ending(ctx, run, dict(facts, slice=slice_name), "card-drift", drift_reason(row, drifted))
    facts.update(slice=slice_name, card=row["status"], footprint=row["footprint"], footprint_line=row["footprint_at"])
    state = dict(facts, lap=0, laps_allowed=common.laps_allowed(run),
                 visits=[], visit=None, named=[], pin=None, ending=None, build=None, signoff=None, recheck=None,
                 hook=None, minors_only=False, paused_from=None)
    common.save(run, state)
    common.advance(run, "selected")
    return ctx.emit(ctx.envelope(next="hook", run_id=common.run_id(run), doc=doc, slice=slice_name, card=row["status"],
                                 footprint=row["footprint"], selection=selection))
