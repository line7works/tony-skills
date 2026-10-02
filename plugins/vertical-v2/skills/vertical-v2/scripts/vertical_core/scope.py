"""`scope`: the depth, the lenses, the planned packets and their lists (contract section 3.3; ruling E15-8
with A2's Q1 and the design round's A4).

Everything a reviewer receives is decided by `packet.py`, the one packet builder, from the reviewed
commit's objects (the commit `gate.json` records): never the working tree, never an earlier copy. `scope`
reads that commit once (`packet.Snapshot`), takes the inspection sheet from it (an untracked or changed
`REVIEW.md` in the working tree is never read, B1), sets the lenses from the depth and that sheet, records
the working tree's untracked, ignored and changed names (names only) for every withheld list, and cuts
each planned packet once under `packets/<name>/` through the builder, so the executor and an observer can
see what each reviewer will receive: its material, `files.json` (every file, its size and sha256) and
`withheld.json` (everything left out, named with why). Each packet's fingerprint (`packet.digest`) goes
into `scope.json`.

These are previews. No request ever points at them: `request` cuts a FRESH copy for every summons, the
first send and every retry alike, under `summons/<call id>/`, from the same function, holds it to that
function's output and to the fingerprint `scope` recorded immediately before the request file is written,
and so a reader's scratch, or anything planted in an earlier copy, never reaches a later one.
vertical-v2 never runs `git worktree`.
"""
import os
import shutil

from station_core import driver

from . import ask as askmod, common, packet, sheet as sheetmod


def handler(ctx, args):
    """`scope --run-dir D`."""
    run = common.open_run(ctx, args.run_dir, ("asked",), "scope")
    gate = common.read(run, "gate.json")
    ask = common.read(run, "ask.json")
    ws = common.workspace(run)
    snap = packet.Snapshot(ws, gate["head"], gate["doc"])
    worktree = packet.worktree_names(ws)
    depth = common.station(run).get("depth") or "LEAN"
    lenses = sheetmod.lenses(depth, snap.sheet)
    previews = common.path_of(run, "packets")
    if os.path.lexists(previews):
        shutil.rmtree(previews)
    packets = []
    for spec in packet.plan(ask, lenses, askmod.OUTSIDE_ROWS):
        built = packet.build(snap, spec, gate, ctx.skill_root, worktree)
        dest = os.path.join(previews, spec["name"])
        paths = packet.cut(built, dest)
        problems = packet.check(built, dest)
        if problems:
            raise driver.Defect("the preview of %s does not hold what the packet builder decided: %s"
                                % (spec["name"], "; ".join(problems)))
        packets.append(dict(spec, dir=paths["dir"], workspace=paths["workspace"], documents=paths["documents"],
                            mandate=paths["mandate"], files=paths["files"], withheld=paths["withheld"],
                            left_out=built["left_out"], digest=packet.digest(built)))
    sheet = snap.sheet
    scope = {"depth": depth, "lenses": lenses, "commit": snap.commit, "doc": snap.doc, "removed": snap.removed,
             "exported": sorted(snap.tree), "worktree": worktree,
             "review_sheet": {"state": sheet["state"], "skipped": sheet["skipped"], "checks": sheet["checks"],
                              "unknown": sheet["unknown"], "bar": sheet["bar"], "entry": snap.sheet_entry},
             "packets": packets,
             "staged_names": dict((name, path) for path, name in snap.staged.items())}
    common.write(run, "scope.json", scope)
    common.advance(run, "scoped")
    return ctx.emit(ctx.envelope(next="request", run_id=run.checkpoint["run_id"], depth=depth, lenses=lenses,
                                 review_sheet=sheet["state"], packets=[p["name"] for p in packets],
                                 depth_line="depth %s: %s" % (depth, ", ".join(lenses))))
