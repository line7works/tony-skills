"""`packet`: the permitted primary evidence, one fresh directory per lens (contract section 6).

Each lens of the lane the owner named gets its own new directory under `<run dir>/packet/<lens>/`
holding exactly three files, each line-numbered `N: ` so a citation has ground truth:
`build-doc.md` (the build doc), `scope-doc.md` (the scope doc) or `no-record.md` (the station's one
line when no scope doc exists), and `code-book.md` (blueprint-v2's installed SKILL.md). They are
numbered from the copies `harvest` kept, so the packet is the record exactly as harvested. Never in
a packet: a summary, a prior verdict, repo code, another reader's output, this session's account.

`check_dir` is the rule `request` applies before it builds anything: the directory holds exactly
its three named files, regular files, no link, no folder, no dotfile, and (when the hashes
`packet` recorded are given) each file's bytes as `packet` wrote them.
"""
import os

from station_core import driver, fsio

from . import common, mandates, readers_link

NAMES = ("build-doc.md", "code-book.md")
SCOPE = "scope-doc.md"
NO_RECORD = "no-record.md"


def expected(no_record):
    return sorted(NAMES + ((NO_RECORD,) if no_record else (SCOPE,)))


def check_dir(folder, no_record, hashes=None):
    """(files present, refusals); a refusal is `{"rule", "message", "file", "dir"}`."""
    refusals = []
    try:
        present = sorted(os.listdir(folder))
    except OSError as exc:
        return [], [{"rule": "packet-missing", "message": "the packet directory cannot be read: %s" % exc,
                     "file": None, "dir": folder}]
    want = expected(no_record)
    for name in present:
        full = os.path.join(folder, name)
        if name not in want:
            what = "a folder" if os.path.isdir(full) and not os.path.islink(full) else "a file"
            refusals.append({"rule": "packet-extra", "file": name, "dir": folder,
                             "message": "the packet holds %s the station never put there: %s. The packet is the "
                                        "record and nothing else (no summary, no prior verdict, no repo code, no "
                                        "other reader's output)" % (what, name)})
        elif os.path.islink(full) or not os.path.isfile(full):
            refusals.append({"rule": "packet-extra", "file": name, "dir": folder,
                             "message": "%s in the packet is not a regular file" % name})
        elif hashes is not None and fsio.sha256_file(full) != hashes.get(name):
            refusals.append({"rule": "packet-changed", "file": name, "dir": folder,
                             "message": "%s changed after `packet` wrote it: the packet is the record as "
                                        "harvested" % name})
    for name in want:
        if name not in present:
            refusals.append({"rule": "packet-missing", "file": name, "dir": folder,
                             "message": "the packet is missing %s" % name})
    return present, refusals


def lenses_for(roster, row):
    provider = readers_link.provider(roster, row)
    if provider is None:
        raise driver.Usage("the row %r is not in readers' roster: name a row the ask offered" % row)
    return (common.CLAUDE_LENSES if provider == common.ANTHROPIC else common.OUTSIDE_LENSES), provider


def row_of(run):
    row = common.station(run).get("row")
    if not row:
        raise driver.Usage("the input names no row (station.row): the ask comes before check-input, and the "
                           "row the owner named is data in this run's input")
    return row


def handler(ctx, args):
    """`packet --run-dir D [--readers-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("harvested",), "packet")
    row = row_of(run)
    found, roster = readers_link.load(common.plugin_root(), args.readers_root)
    lenses, provider = lenses_for(roster, row)
    harvest = common.read(run, "harvest.json")
    sources = os.path.join(run.run_dir, "sources")
    with open(os.path.join(sources, "build-doc.md"), "rb") as fh:
        build = fh.read().decode("utf-8")
    with open(os.path.join(sources, "code-book.md"), "rb") as fh:
        book = fh.read().decode("utf-8")
    if harvest["no_record"]:
        record_name, record_text = NO_RECORD, mandates.NO_RECORD_LINE + "\n"
    else:
        with open(os.path.join(sources, "scope-doc.md"), "rb") as fh:
            record_name, record_text = SCOPE, fh.read().decode("utf-8")
    bodies = {"build-doc.md": common.number(build), "code-book.md": common.number(book),
              record_name: common.number(record_text)}
    root = os.path.join(run.run_dir, "packet")
    dirs = []
    for lens in lenses:
        folder = os.path.join(root, lens)
        if os.path.exists(folder):
            raise driver.Usage("the packet directory %s already exists: a packet is built once per lens per run"
                               % folder)
        os.makedirs(folder)
        hashes = {}
        for name in sorted(bodies):
            data = bodies[name].encode("utf-8")
            fsio.atomic_write(os.path.join(folder, name), data)
            hashes[name] = fsio.sha256_bytes(data)
        dirs.append({"lens": lens, "dir": folder, "files": sorted(bodies), "sha256": hashes})
    doc = {"row": row, "provider": provider, "readers": found, "no_record": harvest["no_record"], "dirs": dirs}
    common.write(run, "packet.json", doc)
    run.checkpoint["phase"] = "packeted"
    run.save()
    return ctx.emit(ctx.envelope(next="request", run_id=run.checkpoint["run_id"], row=row, provider=provider,
                                 dirs=[{"lens": d["lens"], "dir": d["dir"], "files": d["files"]} for d in dirs]))
