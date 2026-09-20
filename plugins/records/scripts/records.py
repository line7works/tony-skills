#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""records.py: the one CLI of the shared records component (records E12 contract section 12).

    uv run records.py verify --workspace W --doc D
    uv run records.py events --workspace W --doc D [--finding ID] [--kind K] [--from N]
    uv run records.py identity --workspace W
    uv run records.py append --workspace W --doc D --events FILE --expect-head H [--break-lock]
    uv run records.py component-identity
    uv run records.py state --workspace W --doc D [--at-source F] [--slice S]
    uv run records.py render --workspace W --doc D --run-id R
    uv run records.py import-legacy --workspace W --doc D [--resolutions R] [--dry-run]
    uv run records.py mirrors --workspace W --doc D
    uv run records.py survey --workspace W

Section 12.2's ten commands, all of them. `import-legacy` is the only one slice 2 adds that
writes; `state`, `render`, `mirrors` and `survey` are read-only.

Every command: JSON on stdout and nothing else; diagnostics on stderr; safe to run from any
working directory; paths in arguments are absolute or resolved from the current working
directory. Every response carries `interface_version` and `component_version`, and, where a log
is involved, `log` (its workspace-relative path), `head` (the hash of the last line) and
`events` (the count). Section 6.1's two addresses are returned as `spec` ({doc, slice}) and, per
event, `history` ({log, seq}).

Exit status (section 12.3): 0 success; 1 anything else (an unsupported workspace, a git failure,
a defect of this script); 2 usage; 3 missing dependency (jsonschema); 4 an input, an event, or a
log line failed validation; 5 ambiguous identity; 6 `stale_source`; 7 `conflict` (chain break,
head mismatch, lock held).

`append` writes native events only. A legacy record enters a log through `import-legacy`
(slice 2), which reads it from the document itself; an event presented to `append` carrying
`origin.kind: "legacy"` or the importer's station `records-import` is refused (exit 4) before
anything else about it is judged, so owner ruling O4's unbound-clear exemption cannot be claimed
by a station that declares itself the importer. The library keyword that admits those events,
`importer=True`, has no flag on this CLI and never will; slice 2's `importer.py` is its one
caller.

Side effects: only `append` and `import-legacy` write, and only two files, both under
`docs/records/` inside the workspace: the log (replaced whole with its old bytes plus the new
lines, through a temporary file beside it and a rename over it) and `<log>.lock`, taken before
the walk and removed on exit. A pass that refuses any event writes nothing at all.
`import-legacy` never writes to the ledger document, to a verdict doc, or to anything outside
`docs/records/`, and `--dry-run` writes nothing and takes no lock. `verify`, `events`,
`identity`, `component-identity`, `state`, `render`, `mirrors` and `survey` write nothing. Git
runs read-only (`rev-parse`, `status`, `diff`, `ls-files`, `submodule status`, `blame`), and
only inside the workspace given.

Partial effects: a process killed between taking the lock and releasing it leaves `<log>.lock`
behind; the next `append` reports it (exit 7) with its contents, and `--break-lock` removes it
once its pid is not alive. The log itself is never left half-written: the rename is atomic.

Test hooks (honored only with RECORDS_TEST=1): RECORDS_TEST_NO_JSONSCHEMA=1 behaves as if
jsonschema were not importable (exit 3).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from records_core import (canon, events as events_mod, identity as identity_mod,  # noqa: E402
                          importer as importer_mod, render as render_mod, state as state_mod,
                          validate)

INTERFACE_VERSION = 1
SKIP_DIRS = ("__pycache__",)
SKIP_FILES = (".DS_Store",)

EXAMPLES = """examples:
  uv run records.py verify --workspace ~/Developer/thing --doc docs/plans/2026-09-06-readers.md
  -> {"interface_version": 1, "component_version": "0.1.0", "ok": true,
      "log": "docs/records/docs__plans__2026-09-06-readers.events.jsonl", "head": "9f2c...", "events": 12}

  uv run records.py events --workspace . --doc docs/punch-list.md --kind disposition --from 4
  uv run records.py identity --workspace .
  uv run records.py append --workspace . --doc docs/punch-list.md --events batch.json \\
      --expect-head 0000000000000000000000000000000000000000000000000000000000000000
  uv run records.py component-identity

  uv run records.py survey --workspace .
  uv run records.py import-legacy --workspace . --doc docs/plans/2026-09-06-readers.md --dry-run
  uv run records.py import-legacy --workspace . --doc docs/punch-list.md --resolutions answers.json
  uv run records.py state --workspace . --doc docs/punch-list.md --slice A
  uv run records.py state --workspace . --doc docs/punch-list.md --at-source identity.json
  uv run records.py render --workspace . --doc docs/punch-list.md --run-id recheck-2026-09-20-a
  uv run records.py mirrors --workspace . --doc docs/plans/2026-09-06-readers.md

exit status: 0 success; 1 anything else; 2 usage; 3 jsonschema missing; 4 an input, an event, or a
  log line failed validation; 5 ambiguous identity; 6 stale_source; 7 conflict.
side effects: only `append` and `import-legacy` write, and only the log and its lock under
  docs/records/ inside the workspace; `import-legacy --dry-run` and every other command are
  read-only. Reruns of the read-only commands are safe; an `append` that already landed fails the
  next identical run on the head it no longer matches, and a second `import-legacy` over an
  unchanged document appends nothing."""


class Usage(ValueError):
    """A usage error: exit 2 through the parser."""


# ---- the component's own identity -------------------------------------------------------------

def component_meta(root):
    """{name, version} from `.claude-plugin/plugin.json` at the component root, with fallbacks.

    `plugin.json` is slice 3's file; until it lands the component reports itself as unversioned
    rather than inventing a version.
    """
    name, version = "records", "unversioned"
    path = os.path.join(root, ".claude-plugin", "plugin.json")
    if os.path.isfile(path):
        try:
            with open(path, "rb") as fh:
                meta = json.loads(fh.read().decode("utf-8"))
            name = meta.get("name") or name
            version = meta.get("version") or version
        except (OSError, ValueError):
            pass
    return {"name": name, "version": version}


def content_sha256(root):
    """SHA-256 over the sorted lines `<relative path>\\0<sha256 of the file>` under the root.

    The whole component, not one file: the same shape `identity.untracked_sha256` uses. Compiled
    caches and `.DS_Store` are left out; nothing else is.
    """
    lines = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name in SKIP_FILES or name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if os.path.islink(full):
                digest = canon.sha256_hex(os.readlink(full).encode("utf-8", "surrogateescape"))
            else:
                digest = canon.sha256_file(full)
            lines.append(rel + "\0" + digest + "\n")
    lines.sort()
    return canon.sha256_hex("".join(lines).encode("utf-8"))


def component_identity(root):
    meta = component_meta(root)
    commit = "unversioned"
    if os.path.isdir(root):
        top = identity_mod.git(root, ["rev-parse", "--show-toplevel"], check=False)
        if top is not None:
            head = identity_mod.git(root, ["rev-parse", "HEAD"], check=False)
            if head:
                commit = head.strip()
    return {"name": meta["name"], "version": meta["version"], "commit": commit,
            "content_sha256": content_sha256(root) if os.path.isdir(root) else "0" * 64}


# ---- argument helpers --------------------------------------------------------------------------

def emit(doc, code):
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()
    return code


def log(message):
    sys.stderr.write(message.rstrip("\n") + "\n")
    sys.stderr.flush()


def envelope(root, body=None):
    """The two fields every response carries, the body, and `ok` (false on every refusal)."""
    doc = {"interface_version": INTERFACE_VERSION, "component_version": component_meta(root)["version"]}
    if body:
        doc.update(body)
    doc.setdefault("ok", True)
    return doc


def resolve_workspace(given):
    path = os.path.abspath(os.path.expanduser(given))
    if not os.path.isdir(path):
        raise Usage("--workspace is not a directory: %s" % path)
    return os.path.realpath(path)


def require_work_tree(workspace):
    """The workspace is a git work tree root with a HEAD commit, and holds no submodule.

    A workspace with an initialized submodule is refused the way the pilot refuses it (pilot
    contract section 6: a submodule's working contents can change without its pinned commit
    changing, and the diff sees only the commit), here as exit 1 `unsupported`.
    """
    ok, reason = identity_mod.is_work_tree_root(workspace)
    if not ok:
        raise Usage("--workspace %s %s" % (workspace, reason))
    modules = identity_mod.identity_of(workspace)["submodules"]
    if modules:
        raise Refusal(1, {"ok": False, "error": "unsupported",
                          "reason": "unsupported: submodules: %s" % ", ".join(modules),
                          "workspace": workspace, "submodules": modules})


class Refusal(Exception):
    def __init__(self, code, document):
        Exception.__init__(self, document.get("reason", "refused"))
        self.code = code
        self.document = document


def resolve_doc(workspace, given):
    """A ledger document's workspace-relative path: inside the workspace, normalized, `.md`."""
    raw = given.replace("\\", "/")
    if raw.startswith("/") or raw.startswith("~"):
        raise Usage("--doc is a workspace-relative path, not an absolute one: %s" % given)
    rel = os.path.normpath(raw).replace(os.sep, "/")
    if rel == "." or rel.startswith("../") or rel == "..":
        raise Usage("--doc resolves outside the workspace: %s" % given)
    if not rel.endswith(".md"):
        raise Usage("--doc names a Markdown ledger document (a build doc or docs/punch-list.md): %s" % given)
    full = os.path.realpath(os.path.join(workspace, *rel.split("/")))
    root = os.path.realpath(workspace)
    if full != root and not full.startswith(root + os.sep):
        raise Usage("--doc resolves outside the workspace: %s" % given)
    return rel


def read_events_file(path):
    """The batch `append` writes: a JSON array of events, or one event object."""
    full = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(full):
        raise Usage("--events is not a file: %s" % full)
    try:
        with open(full, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise Usage("--events does not read as JSON: %s (%s)" % (full, exc))
    if isinstance(doc, dict):
        doc = [doc]
    if not isinstance(doc, list) or not doc:
        raise Usage("--events holds a JSON array of events, or one event object: %s" % full)
    return doc


def check_head(given):
    value = given.strip().lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise Usage("--expect-head is a 64-character hex SHA-256 (64 zeros for a log that does not exist yet)")
    return value


# ---- commands ------------------------------------------------------------------------------------

def cmd_verify(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    path = events_mod.log_path(workspace, doc)
    walked = events_mod.walk(path, schemas)
    body = {"exists": walked["exists"], "log": events_mod.log_relpath(doc),
            "head": walked["head"], "events": len(walked["events"]),
            "spec": events_mod.spec_address(doc)}
    return emit(envelope(root, body), 0)


def cmd_events(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    path = events_mod.log_path(workspace, doc)
    walked = events_mod.walk(path, schemas)
    rows = []
    for event in walked["events"]:
        if args.finding is not None and event.get("finding") != args.finding:
            continue
        if args.kind is not None and event.get("kind") != args.kind:
            continue
        if args.start is not None and event["seq"] < args.start:
            continue
        rows.append({"seq": event["seq"], "event": event,
                     "history": events_mod.history_address(doc, event["seq"]),
                     "spec": events_mod.spec_address(doc, event.get("slice"))})
    body = {"log": events_mod.log_relpath(doc), "head": walked["head"], "events": len(walked["events"]),
            "exists": walked["exists"], "spec": events_mod.spec_address(doc),
            "filters": {"finding": args.finding, "kind": args.kind, "from": args.start},
            "returned": len(rows), "results": rows}
    return emit(envelope(root, body), 0)


def cmd_identity(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    require_work_tree(workspace)
    body = {"workspace": workspace, "identity": identity_mod.source_identity(workspace),
            "excluded": [p + "/" for p in identity_mod.EXCLUDED]}
    return emit(envelope(root, body), 0)


def cmd_append(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    incoming = read_events_file(args.events)
    expect_head = check_head(args.expect_head)
    require_work_tree(workspace)
    body = events_mod.append(workspace, doc, incoming, expect_head, schemas, break_lock=args.break_lock)
    return emit(envelope(root, body), 0)


def cmd_component_identity(args, root, schemas):
    return emit(envelope(root, component_identity(root)), 0)


def read_json_file(path, what):
    full = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(full):
        raise Usage("%s is not a file: %s" % (what, full))
    try:
        with open(full, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise Usage("%s does not read as JSON: %s (%s)" % (what, full, exc))


def cmd_state(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    at_source = None
    if args.at_source is not None:
        given = read_json_file(args.at_source, "--at-source")
        at_source = given.get("identity") if isinstance(given, dict) and "identity" in given else given
        if not isinstance(at_source, dict) or not isinstance(at_source.get("commit"), str):
            raise Usage("--at-source names a JSON file holding a six-field identity, or a response "
                        "carrying one under `identity`: %s" % args.at_source)
    walked = events_mod.walk(events_mod.log_path(workspace, doc), schemas)
    body = state_mod.state_of(doc, walked["events"], at_source=at_source, slice_name=args.slice)
    body.update({"log": events_mod.log_relpath(doc), "head": walked["head"],
                 "events": len(walked["events"]), "exists": walked["exists"]})
    return emit(envelope(root, body), 0)


def cmd_render(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    walked = events_mod.walk(events_mod.log_path(workspace, doc), schemas)
    try:
        body = render_mod.render_run(doc, walked["events"], args.run_id)
    except render_mod.RenderError as exc:
        raise Refusal(4, {"ok": False, "error": "invalid", "reason": str(exc),
                          "log": events_mod.log_relpath(doc), "head": walked["head"],
                          "events": len(walked["events"]), "run_id": args.run_id})
    body.update({"log": events_mod.log_relpath(doc), "head": walked["head"],
                 "events": len(walked["events"]), "exists": walked["exists"]})
    return emit(envelope(root, body), 0)


def cmd_import_legacy(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    resolutions = None
    if args.resolutions is not None:
        resolutions = read_json_file(args.resolutions, "--resolutions")
        errors = validate.validate_document("resolutions", resolutions, schemas)
        if errors:
            raise Refusal(4, {"ok": False, "error": "invalid", "report": "import",
                              "reason": "the resolutions file fails resolutions.schema.json at "
                                        "%s: %s" % (errors[0]["path"] or "/", errors[0]["message"]),
                              "errors": errors, "doc": doc,
                              "log": events_mod.log_relpath(doc)})
        named = resolutions.get("doc")
        if named is not None and named != doc:
            raise Refusal(4, {"ok": False, "error": "invalid", "report": "import",
                              "reason": "the resolutions file answers %r; --doc names %r"
                                        % (named, doc), "doc": doc,
                              "log": events_mod.log_relpath(doc)})
    if not args.dry_run:
        require_work_tree(workspace)
    body = importer_mod.import_legacy(
        workspace, doc, schemas, resolutions=resolutions, dry_run=args.dry_run,
        break_lock=args.break_lock, component_version=component_meta(root)["version"],
        interface_version=INTERFACE_VERSION)
    return emit(envelope(root, body), 0)


def cmd_mirrors(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    doc = resolve_doc(workspace, args.doc)
    return emit(envelope(root, importer_mod.mirrors(workspace, doc)), 0)


def cmd_survey(args, root, schemas):
    workspace = resolve_workspace(args.workspace)
    return emit(envelope(root, importer_mod.survey(workspace)), 0)


COMMANDS = {"verify": cmd_verify, "events": cmd_events, "identity": cmd_identity,
            "append": cmd_append, "component-identity": cmd_component_identity,
            "state": cmd_state, "render": cmd_render, "import-legacy": cmd_import_legacy,
            "mirrors": cmd_mirrors, "survey": cmd_survey}
NEEDS_SCHEMAS = ("verify", "events", "append", "state", "render", "import-legacy")


# ---- argparse --------------------------------------------------------------------------------

class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        sys.exit(2)


def build_parser():
    p = Parser(prog="records.py",
               description="The shared records component's CLI: the append-only event log of a ledger "
                           "document, its chain, its identities, and its addresses (records E12 contract "
                           "section 12). JSON on stdout and nothing else.",
               epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--records-root", metavar="DIR", default=None,
                   help="test only: load references from DIR instead of this script's own component root")
    sub = p.add_subparsers(dest="command", metavar="command")
    sub.required = True

    def add(name, help_text, description, side_effects):
        return sub.add_parser(name, help=help_text, description=description,
                              formatter_class=argparse.RawDescriptionHelpFormatter,
                              epilog="side effects: %s\nexit: 0 success; 1 anything else; 2 usage; "
                                     "3 jsonschema missing; 4 validation; 5 ambiguous identity; "
                                     "6 stale_source; 7 conflict" % side_effects)

    def workspace_doc(sp):
        sp.add_argument("--workspace", metavar="W", required=True,
                        help="the workspace root (a directory; absolute or resolved from the current directory)")
        sp.add_argument("--doc", metavar="D", required=True,
                        help="the ledger document, workspace-relative (a build doc, or docs/punch-list.md); "
                             "its log is docs/records/<D with .md removed and / replaced by __>.events.jsonl")

    sp = add("verify", "walk the log's chain and schema",
             "Walk the log of one ledger document: every line parses and validates, seq equals the line "
             "index, and every prev equals the hash of the line before (section 10). A log that does not "
             "exist yet verifies with head 0000... and 0 events.", "none (read-only); reruns are safe")
    workspace_doc(sp)

    sp = add("events", "the events, filtered, each with its history address",
             "Print the log's events in seq order, each with its history address {log, seq} and its spec "
             "address {doc, slice}. The chain is walked first, so a broken log is refused rather than read.",
             "none (read-only); reruns are safe")
    workspace_doc(sp)
    sp.add_argument("--finding", metavar="ID", default=None, help="only events naming this finding ID")
    sp.add_argument("--kind", metavar="K", default=None, help="only events of this kind")
    sp.add_argument("--from", metavar="N", dest="start", type=int, default=None,
                    help="only events from this seq onward (default: from 0)")

    sp = add("identity", "the source identity of section 8.2",
             "Print the six-field source identity of the workspace, computed with docs/records/ excluded "
             "from the dirty check, the tracked diff, and the untracked list (section 8.2), so that "
             "appending to a log does not change the identity of the source the log describes.",
             "none (read-only); git runs read-only inside the workspace")
    sp.add_argument("--workspace", metavar="W", required=True, help="the workspace root (a git work tree root)")

    sp = add("append", "append a batch of events to the log",
             "Append one or more events to a ledger document's log, all or none (section 10). seq and prev "
             "are assigned by the component, never by the caller, so the events in --events carry neither. "
             "--expect-head is the hash of the last line the caller read (64 zeros for a log that does not "
             "exist yet); a different head on disk is exit 7 and nothing is written. A `fixed` disposition "
             "and a `waived` are refused unless they carry a known source identity equal to the workspace's "
             "and name a finding that is open (section 8.3). Native events only: an event carrying "
             "origin.kind `legacy` or the station `records-import` is refused (exit 4), because a legacy "
             "record enters a log through `import-legacy`, which reads it from the document itself.",
             "writes the log and <log>.lock under docs/records/ inside the workspace; a refusal writes "
             "nothing; a killed process can leave the lock behind, which --break-lock removes once its pid "
             "is not alive")
    workspace_doc(sp)
    sp.add_argument("--events", metavar="FILE", required=True,
                    help="a JSON file holding an array of events (or one event object), each without seq and prev")
    sp.add_argument("--expect-head", metavar="H", required=True,
                    help="the hash of the last line the caller read; 64 zeros for a log that does not exist yet")
    sp.add_argument("--break-lock", action="store_true", default=False,
                    help="remove a stale <log>.lock and say so in the response; refused while its pid is alive")

    sp = add("state", "the derived state of section 9",
             "Print the derived state of one ledger document's log: every finding with its status, "
             "its `cleared_unbound` flag, its join basis and its two addresses, and every slice with "
             "its open counts, its derived card, the card an import observed, and whether they drift. "
             "State is a pure function of the log's bytes: the same log gives the same object on any "
             "machine, and nothing here reads the document or the clock.",
             "none (read-only); reruns are safe and give byte-equal output")
    workspace_doc(sp)
    sp.add_argument("--at-source", metavar="F", default=None,
                    help="a JSON file holding a six-field identity (or a response carrying one under "
                         "`identity`): each cleared finding then carries `cleared_at_this_source`, "
                         "true only when the clear was bound and names that commit (section 8.4). "
                         "It changes no state.")
    sp.add_argument("--slice", metavar="S", default=None,
                    help="only this slice's findings and card")

    sp = add("render", "the Appendix A text one run's events produce",
             "Print the exact Appendix A text the pilot writes for the same facts: the block heading, "
             "the recheck and defect lines, and the waiver and reopening lines of the run named by "
             "--run-id. Nothing in E12 writes that text into a document.",
             "none (read-only); reruns are safe")
    workspace_doc(sp)
    sp.add_argument("--run-id", metavar="R", required=True,
                    help="the run whose events to render (matched against actor.run_id)")

    sp = add("import-legacy", "import one legacy ledger document's records",
             "Read one ledger document and append the events its records represent, in file order, to "
             "that document's log. The document itself is never written, and neither is a verdict doc "
             "or anything outside docs/records/. A second pass over an unchanged document appends "
             "nothing; a document that has only grown at its tail contributes only its new records; a "
             "document whose imported lines changed or moved is exit 7 and nothing is written. Any "
             "ambiguous line stops the whole document with exit 5 and a report that lists every field "
             "an answer needs; --resolutions supplies those answers. Every imported clear keeps its "
             "effect and carries `known: false` (owner ruling O4), which derived state reports as "
             "`cleared_unbound`.",
             "writes the log and <log>.lock under docs/records/ inside the workspace, and nothing "
             "else; --dry-run writes nothing and takes no lock; a refusal writes nothing")
    workspace_doc(sp)
    sp.add_argument("--resolutions", metavar="R", default=None,
                    help="a JSON file of answers to the ambiguous lines (resolutions.schema.json)")
    sp.add_argument("--dry-run", action="store_true", default=False,
                    help="report what would be appended and write nothing")
    sp.add_argument("--break-lock", action="store_true", default=False,
                    help="remove a stale <log>.lock and say so in the response; refused while its pid "
                         "is alive; ignored under --dry-run, which takes no lock")

    sp = add("mirrors", "compare the verdict docs that mirror this document's blocks",
             "Report the verdict docs the pilot's glob associates with this document's slices, each of "
             "their blocks as same, differs or absent against the ledger document, and every record a "
             "verdict doc holds that the ledger document does not. A difference is reported, never "
             "repaired, never imported, and never blocks an import: a verdict doc is a copy, never a "
             "second source.",
             "none (read-only); reruns are safe")
    workspace_doc(sp)

    sp = add("survey", "what every document of the workspace would import",
             "Walk the workspace's Markdown documents, keep the ones carrying Appendix A records, and "
             "report for each the counts by record kind, the counts by join basis, and every line that "
             "would stop an import. Documents under docs/reviews/ are mirrors and are listed as such. "
             "Nothing is imported and nothing is written.",
             "none (read-only); reruns are safe")
    sp.add_argument("--workspace", metavar="W", required=True, help="the workspace root (a directory)")

    add("component-identity", "{name, version, commit, content_sha256} of the component root",
        "Print the component's own identity: its plugin name and version, the commit of the repository it "
        "sits in, and a SHA-256 over every file under the component root.", "none (read-only)")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate.require_jsonschema()
    try:
        root = validate.component_root(args.records_root)
        schemas = validate.load_schemas(root) if args.command in NEEDS_SCHEMAS else None
        return COMMANDS[args.command](args, root, schemas)
    except (Usage, validate.ComponentRootMissing) as exc:
        parser.error(str(exc))
    except events_mod.RecordsError as exc:
        return emit(envelope(validate.component_root(args.records_root), exc.document), exc.code)
    except Refusal as exc:
        return emit(envelope(validate.component_root(args.records_root), exc.document), exc.code)
    except validate.ReferenceUnavailable as exc:
        log(str(exc))
        return 1
    except identity_mod.GitError as exc:
        log("git failed inside the workspace: %s" % exc)
        return 1
    except OSError as exc:
        log("the file system refused an operation: %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
