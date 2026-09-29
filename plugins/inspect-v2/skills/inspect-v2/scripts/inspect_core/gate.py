"""`named`, `choose` and `harvest`: the gate and the hunt (contract sections 3, 5 and 6).

`named` takes the build doc the invocation names by path (v1 Step 1: "the invocation names a build
doc, or the skill hunts"): one existing `.md` inside the workspace by its real path, never through a
link out, recorded as the build hunt's `one` with home `named`. When that doc lies outside every
build home, this run's scope hunt adds the doc's own directory's `scope/*.md` and `*-scope.md`
(`hunts_for_run`, read by the driver script before the shared `select` runs).
`choose` records the executor's Intent match, or the owner's pick, among the candidates a hunt
listed as `several`; it never picks by itself and takes nothing that was not listed. `harvest`
takes the build doc and the scope doc the hunts settled (or the no-record rule when the scope hunt
found none), reads the scope doc's ledger, resolves the code book (blueprint-v2's installed
SKILL.md, a v2 sibling by route 3a then 3b), confirms the records component at interface version 2
(exit 3 otherwise), pins the log's head, and keeps a copy of each source in the run directory so
the packet is the record exactly as harvested.
"""
import argparse
import glob
import json
import os
import re

from station_core import driver, fsio, ledger, records_link, sibling, templates
from station_core.records_client import RecordsRefusal

from . import common, reporting

CODE_BOOK_PLUGIN = "blueprint-v2"
SLICE = re.compile(r"^##\s+Slice\s+(.+?)(?:\s+[\u2014\u2013-]+\s*(.*?))?\s*$")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


# the directories the build hunt's homes glob in: a named doc in one of them is inside a home
BUILD_HOME_DIRS = ("docs/plans", "docs", "plan")


def _inside_a_build_home(ws, folder):
    for rel in BUILD_HOME_DIRS:
        home = os.path.join(ws, rel)
        if os.path.isdir(home) and os.path.samefile(home, folder):
            return True
    return False


def named(ctx, args):
    """`named --run-dir D --path P`: the build doc the invocation names, taken as the build hunt's one."""
    run = common.open_run(ctx, args.run_dir, ("checked", "selected"), "named")
    if common.has(run, "selection-scope.json"):
        raise driver.Usage("run `named` before `select --hunt scope`: the scope hunt of a doc named outside every "
                           "build home adds that doc's own directory's homes, so this run's scope hunt already ran "
                           "without them. Start a fresh run: check-input, named, then select --hunt scope")
    ws = common.workspace(run)
    given = args.path
    path = given if os.path.isabs(given) else os.path.join(ws, given)
    real, real_ws = os.path.realpath(path), os.path.realpath(ws)
    if not fsio.inside(real, real_ws) or real == real_ws:
        raise driver.Usage("%s lies outside the workspace %s (by its real path): the named build doc is a "
                           "document of this repository, never one reached through a link out" % (given, ws))
    if not (path.endswith(".md") and real.endswith(".md")):
        raise driver.Usage("%s is not a Markdown build doc (`.md`)" % given)
    if not os.path.isfile(real):
        raise driver.Usage("no such build doc: %s (a named doc must exist and be a file)" % given)
    rel = os.path.relpath(real, real_ws)
    taken = os.path.normpath(os.path.join(ws, rel))
    folder = os.path.dirname(real)
    scope_dir = None if _inside_a_build_home(real_ws, folder) else os.path.dirname(rel).replace(os.sep, "/")
    selection = {"outcome": "one", "candidates": [{"path": taken, "home": "named", "tier": 0}],
                 "searched": [{"home": "named", "root": "workspace", "globs": [], "tier": 0, "given": True,
                               "found": [taken]}],
                 "hunt": "build", "name": None, "path": given}
    fsio.write_json(common.path_of(run, "selection-build.json"), selection)
    run.checkpoint["phase"] = "selected"
    run.checkpoint.setdefault("selections", {})["build"] = "one"
    run.checkpoint["named"] = {"path": taken, "rel": rel.replace(os.sep, "/"), "given": given, "scope_dir": scope_dir}
    run.save()
    return ctx.emit(ctx.envelope(next="select --hunt scope", run_id=run.checkpoint["run_id"], build_doc=taken,
                                 home="named", scope_dir=scope_dir,
                                 scope_homes_added=[] if scope_dir is None else [
                                     "%s/scope/*.md" % scope_dir if scope_dir else "scope/*.md",
                                     "%s/*-scope.md" % scope_dir if scope_dir else "*-scope.md"],
                                 **{"outcome": "one", "candidates": selection["candidates"]}))


def hunts_for_run(hunts, argv):
    """The hunt table for this invocation: the core's own, plus, for `select --run-dir D` on a run whose
    build doc was `named` outside every build home, the named doc's directory's two scope homes (v1
    Step 1). Anything unreadable leaves the table as it is; the driver then reports the run itself."""
    argv = list(argv or [])
    if not argv or argv[0] != "select":
        return hunts
    run_dir = _select_run_dir(argv[1:])
    if not run_dir:
        return hunts
    try:
        with open(os.path.join(run_dir, "checkpoint.json"), encoding="utf-8") as fh:
            checkpoint = json.load(fh)
        with open(os.path.join(run_dir, "selection-build.json"), encoding="utf-8") as fh:
            build = json.load(fh)
    except (OSError, ValueError):
        return hunts
    chosen = (checkpoint.get("named") or {}) if isinstance(checkpoint, dict) else {}
    scope_dir = chosen.get("scope_dir")
    homes = [c.get("home") for c in build.get("candidates") or [] if isinstance(c, dict)] \
        if isinstance(build, dict) else []
    if scope_dir is None or homes != ["named"]:
        return hunts
    prefix = glob.escape(scope_dir) + "/" if scope_dir else ""
    out = dict(hunts)
    out["scope"] = list(hunts["scope"]) + [
        {"home": "named-dir-scope", "root": "workspace", "globs": [prefix + "scope/*.md"], "tier": 1},
        {"home": "named-dir-flat", "root": "workspace", "globs": [prefix + "*-scope.md"], "tier": 1}]
    return out


class _Unparsed(Exception):
    pass


class _Mirror(argparse.ArgumentParser):
    def error(self, message):
        raise _Unparsed(message)


def _select_run_dir(args):
    """`--run-dir` of a `select` argv, read the way the shared driver's parser reads it (round 3, R3,
    CI2-1): the same options, so an abbreviation argparse accepts (`--run D`, `--run-d=D`) is accepted
    here too, and one it refuses (`--r`, ambiguous with `--records-root`) is refused here too. None
    when the argv does not parse; the driver then reports it itself."""
    mirror = _Mirror(add_help=False)
    for flag in ("--skill-root", "--records-root", "--run-dir", "--hunt", "--name"):
        mirror.add_argument(flag, default=None)
    try:
        known, _ = mirror.parse_known_args(args)
    except _Unparsed:
        return None
    return known.run_dir


def _named_scope_homes_missed(run):
    """Whether this run's build doc was `named` outside every build home and the scope selection
    `harvest` would take never searched that doc's own directory's homes (round 3, R3, CI2-1)."""
    chosen = run.checkpoint.get("named") or {}
    if chosen.get("scope_dir") is None:
        return False
    build = common.read(run, "selection-build.json") if common.has(run, "selection-build.json") else {}
    if [c.get("home") for c in build.get("candidates") or []] != ["named"]:
        return False
    scope = common.read(run, "selection-scope.json") if common.has(run, "selection-scope.json") else {}
    homes = set(r.get("home") for r in scope.get("searched") or [])
    return not {"named-dir-scope", "named-dir-flat"} <= homes


def _selection(run, hunt):
    if not common.has(run, "selection-%s.json" % hunt):
        raise driver.Usage("`harvest` needs both hunts: run `select --hunt %s` first" % hunt)
    return common.read(run, "selection-%s.json" % hunt)


def choose(ctx, args):
    """`choose --run-dir D --hunt build|scope --path P --by intent|owner [--words TEXT]`."""
    run = common.open_run(ctx, args.run_dir, ("selected",), "choose")
    if args.hunt not in ("build", "scope"):
        raise driver.Usage("--hunt is build or scope, not %r" % args.hunt)
    selection = _selection(run, args.hunt)
    if selection["outcome"] != "several":
        raise driver.Usage("the %s hunt found %s, not several: there is nothing to choose between"
                           % (args.hunt, selection["outcome"]))
    listed = [os.path.normpath(c["path"]) for c in selection["candidates"]]
    chosen = os.path.normpath(os.path.abspath(args.path))
    if chosen not in listed:
        raise driver.Usage("%s is not one of the listed candidates (%s): a choice is made among them, never "
                           "beside them" % (args.path, ", ".join(listed)))
    if args.by == "owner" and not (args.words or "").strip():
        raise driver.Usage("an owner's pick carries his words verbatim: pass --words")
    row = {"path": chosen, "by": args.by, "words": args.words if args.by == "owner" else None}
    run.checkpoint.setdefault("choices", {})[args.hunt] = row
    run.save()
    return ctx.emit(ctx.envelope(next="harvest", run_id=run.checkpoint["run_id"], hunt=args.hunt, chosen=chosen,
                                 by=args.by, words=row["words"]))


def _settled(ctx, run, hunt):
    """(path or None, how) for one hunt; a stop for `none` (build) or an unresolved `several`."""
    selection = _selection(run, hunt)
    choice = (run.checkpoint.get("choices") or {}).get(hunt)
    if selection["outcome"] == "one":
        first = selection["candidates"][0]
        return first["path"], ("named" if first.get("home") == "named" else "one")
    if selection["outcome"] == "several":
        listed = [os.path.normpath(c["path"]) for c in selection["candidates"]]
        if choice and os.path.normpath(choice["path"]) in listed:
            return choice["path"], "chosen by %s" % choice["by"]
        if choice:
            raise driver.Usage("the %s choice %s is not among the candidates the latest `select` listed: run "
                               "`choose` again" % (hunt, choice["path"]))
        listed = "; ".join(c["path"] for c in selection["candidates"])
        reporting.finish(ctx, run, "stopped", "selection-several",
                         "the %s hunt found %d candidates and none is picked by the script: %s. Put them to the "
                         "owner (the scope doc by its Intent line first), then a fresh run that records the "
                         "choice with `choose`" % (hunt, len(selection["candidates"]), listed))
    if hunt == "build":
        reporting.finish(ctx, run, "stopped", "selection-none",
                         "no build doc was found in docs/plans/, the flat docs/<name>-build-plan.md or a phase or "
                         "slice doc: a plan that lives only in the conversation is not inspectable. Write it with "
                         "blueprint-v2, then run inspect-v2")
    return None, "none"


def _read(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return data, data.decode("utf-8")


def slices_of(text):
    """[{name, heading_line, start, end, status}] of the build doc's `## Slice` sections (1-based)."""
    lines = text.split("\n")
    out, fence = [], None
    for index, raw in enumerate(lines, 1):
        line = raw.rstrip("\r")
        m = FENCE.match(line)
        if m:
            fence = None if fence == m.group(1)[0] else (fence or m.group(1)[0])
            continue
        if fence:
            continue
        if line.startswith("## ") or line.rstrip() == "##":
            if out and out[-1]["end"] is None:
                out[-1]["end"] = index - 1
            s = SLICE.match(line.rstrip())
            if s:
                out.append({"name": s.group(1).strip(), "heading_line": index, "start": index, "end": None,
                            "status": None})
            continue
        if out and out[-1]["end"] is None and out[-1]["status"] is None and line.startswith("Status:"):
            out[-1]["status"] = line[len("Status:"):].strip()
    if out and out[-1]["end"] is None:
        out[-1]["end"] = len(lines)
    return out


def harvest(ctx, args):
    run = common.open_run(ctx, args.run_dir, ("selected",), "harvest")
    ws = common.workspace(run)
    build_path, build_how = _settled(ctx, run, "build")
    _selection(run, "scope")
    if _named_scope_homes_missed(run):
        raise driver.Usage("the build doc was named outside every build home, and this run's scope selection "
                           "never searched its own directory's scope/*.md and *-scope.md: run `select --hunt scope` "
                           "again, then harvest (the no-record rule applies only when every home came up empty)")
    scope_path, scope_how = _settled(ctx, run, "scope")
    try:
        build_bytes, build_text = _read(build_path)
    except (OSError, UnicodeDecodeError) as exc:
        reporting.finish(ctx, run, "stopped", "build-doc-unreadable",
                         "the build doc %s cannot be read as UTF-8 text (%s): report and stop" % (build_path, exc))
    client = records_link.open_client(common.STATION, records_root=args.records_root)
    rel = os.path.relpath(build_path, ws)
    try:
        head = client.events(ws, rel)
    except RecordsRefusal as refusal:
        reporting.finish(ctx, run, "stopped", "records-refused",
                         records_link.refusal_sentence(refusal, "reading the build doc's log at harvest"))
    try:
        found = sibling.resolve(CODE_BOOK_PLUGIN, common.plugin_root())
        book_path = os.path.normpath(sibling.skill_file(found["root"], CODE_BOOK_PLUGIN))
        book_bytes, book_text = _read(book_path)
    except (LookupError, OSError, UnicodeDecodeError, sibling.SiblingRefused) as exc:
        reporting.finish(ctx, run, "stopped", "code-book-missing",
                         "the code book, %s's SKILL.md, resolves by neither route: %s" % (CODE_BOOK_PLUGIN, exc))
    scope = None
    ledger_block = {"lines": [], "refused": []}
    sources = os.path.join(run.run_dir, "sources")
    os.makedirs(sources, exist_ok=True)
    fsio.atomic_write(os.path.join(sources, "build-doc.md"), build_bytes)
    fsio.atomic_write(os.path.join(sources, "code-book.md"), book_bytes)
    if scope_path:
        try:
            scope_bytes, scope_text = _read(scope_path)
        except (OSError, UnicodeDecodeError) as exc:
            raise driver.Defect("the scope doc %s cannot be read: %s" % (scope_path, exc))
        fsio.atomic_write(os.path.join(sources, "scope-doc.md"), scope_bytes)
        inside = fsio.inside(scope_path, ws)
        scope = {"path": scope_path, "rel": os.path.relpath(scope_path, ws) if inside else None,
                 "label": os.path.relpath(scope_path, ws) if inside else os.path.basename(scope_path),
                 "sha256": fsio.sha256_bytes(scope_bytes), "how": scope_how}
        try:
            ledger_block["lines"] = ledger.read(scope_text)
        except ledger.LedgerRefused as refused:
            # quoted, never dropped or guessed; the plan is still inspected, as v1 inspects it
            ledger_block["refused"] = refused.lines
    slices = slices_of(build_text)
    stamps = []
    for number, line in enumerate(build_text.split("\n"), 1):
        parsed = templates.parse_line(line.rstrip("\r"))
        if parsed and parsed["kind"] == "stamp":
            stamps.append({"line": number, "text": line.rstrip("\r")})
    doc = {
        "build_doc": {"path": build_path, "rel": rel, "sha256": fsio.sha256_bytes(build_bytes),
                      "lines": len(common.number(build_text).splitlines()), "how": build_how},
        "scope_doc": scope,
        "no_record": scope is None,
        "code_book": {"path": book_path, "route": found["route"], "sha256": fsio.sha256_bytes(book_bytes)},
        "records": {"root": client.root, "interface_version": client.interface_version, "log": head.get("log"),
                    "head": head.get("head"), "exists": head.get("exists")},
        "ledger": ledger_block,
        "slices": slices,
        "construction_started": [s["name"] for s in slices if s["status"] not in (None, "not started")],
        "stamps": stamps,
        "form_findings": templates.check("build-doc", build_text),
        "feature": common.feature_of(build_path),
    }
    common.write(run, "harvest.json", doc)
    run.checkpoint["phase"] = "harvested"
    run.save()
    return ctx.emit(ctx.envelope(next="packet", run_id=run.checkpoint["run_id"], build_doc=build_path,
                                 scope_doc=scope_path, no_record=scope is None, code_book=doc["code_book"],
                                 records=doc["records"], construction_started=doc["construction_started"],
                                 ledger_refused=ledger_block["refused"], form_findings=doc["form_findings"]))
