"""The command line of the lifecycle frame (the contract's E16-15: the A7a helper interface).

    sun.py look    --kind K --name N [--also N ...] --inputs FILE [--capabilities FILE]
    sun.py go      --kind K --name N [--also N ...] --run ID --manifest-sha256 H [--capabilities FILE]
    sun.py resume  --name N [--also N ...] [--run ID] [--kind K] --position P [--capabilities FILE]
                   [--word "go on" | --done OP | --leave OP | --answer OP=VALUE]
    sun.py status  --name N [--also N ...] [--run ID] [--kind K] [--capabilities FILE]
    sun.py replan  --name N [--also N ...] [--run ID] [--kind K] --inputs FILE [--capabilities FILE]
    sun.py close   --name N [--also N ...] [--run ID] [--kind K] [--word close]
    sun.py skill-identity

Standard output carries one JSON document and nothing else (`--help` aside); diagnostics go to
standard error. Exit 0 success (a preview awaits his go), 2 usage, 4 a supplied file or a lane's
rows failed validation, 10 the invocation reached an ending the frame names (`refused`, `waiting`,
`stopped`, `complete`, `ended with exceptions`, `closed`), 1 anything else. The fixed number of a
start that could not run the tool's first code is the entry point's, never this module's
(`exits.py`).

`main` is reached through `sun.py`, which has made the withheld read and hands it on as `view`.
"""
import argparse
import hashlib
import json
import os
import sys

from . import exits, journal as journalmod, out, schemas, startup, texts
from . import world as worldmod

SUMMONSES = ("look", "go", "resume", "status", "replan", "close")
KINDS = ("sunrise", "sunset", "restore")

HELP = """sun.py: the lifecycle frame of sun-v2 (sunrise, sunset and restore as runs of explicit operations).

Commands (each is one invocation working on one run; `--name` is the project's name as the owner gave it,
`--also` each further name he gave, `--kind` one of sunrise, sunset, restore):

  look     the first look of a run: reads only, builds the plan and renders the preview.
           --kind K --name N [--also N ...] --inputs FILE [--capabilities FILE]
           Side effects: a new run directory with the saved inputs, the manifest and the preview; nothing
           outside it. A refusal after the startup checks leaves a refusal form and no manifest.
  go       records the owner's go on the manifest the preview showed, then runs operations.
           --kind K --name N [--also N ...] --run ID --manifest-sha256 H [--capabilities FILE]
           Side effects: the journal, the record of open runs, and every effect the approved manifest holds.
           A failed command may leave a staged object in the run directory and an operation with a start
           record and no completion; the next resume probes it and never applies an effect twice.
  resume   goes on with an open run on the owner's word, given in answer to the latest status form.
           --name N [--run ID] [--kind K] --position P [--word "go on" | --done OP | --leave OP | --answer OP=VALUE]
           Without his word, without --position, or with a stale one, it renders the status form and does nothing.
  status   renders the status form of an open run and does nothing else.
           --name N [--run ID] [--kind K] [--capabilities FILE]
  replan   a new plan in the same run: a full look, a new manifest, a new preview awaiting a new go.
           --name N [--run ID] [--kind K] --inputs FILE [--capabilities FILE]
  close    records an open run closed on the owner's word. Changes nothing outside the run directory.
           --name N [--run ID] [--kind K] --word close
  skill-identity   name, version, commit and content hash of this plugin's lifecycle code. No arguments.
  check-examples   checks every example of every schema the tool ships with the tool's own check.
           [--references DIR] [--verbose]. Side effects: none; it only reads.

Defaults: --also none; --run the run open under the name; --capabilities none declared (every capability a row
needs is then absent and said so in the preview).

Example:
  /bin/sh lifecycle/scripts/sun look --kind sunrise --name "Tide Table" --inputs /tmp/tide/inputs.json

Output: one JSON object on standard output with interface_version, plugin_version, tool, command, exit, ending and
lines; forms are files named in it. Exit: 0 a preview awaits the go; 2 usage; 4 a supplied
file or a lane's rows failed validation; 10 the invocation ended (refused, waiting, stopped, complete, ended with
exceptions, closed); 1 anything else. Reruns are safe: a look creates a new run directory each time and changes
nothing else; every other command reads the journal first.
"""


class Usage(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage()

    def exit(self, status=0, message=None):
        raise Usage()


def parser_for(command):
    p = _Parser(prog="sun.py " + command, add_help=False)
    p.add_argument("--name", required=True)
    p.add_argument("--also", action="append", default=[])
    p.add_argument("--capabilities", default=None)
    if command in ("look", "go"):
        p.add_argument("--kind", required=True, choices=KINDS)
    else:
        p.add_argument("--kind", default=None, choices=KINDS)
    if command == "go":
        p.add_argument("--run", required=True)
        p.add_argument("--manifest-sha256", dest="manifest_sha256", required=True)
    else:
        p.add_argument("--run", default=None)
    if command in ("look", "replan"):
        p.add_argument("--inputs", required=True)
    if command == "resume":
        p.add_argument("--position", type=int, default=None)
        p.add_argument("--word", default=None)
        p.add_argument("--done", default=None)
        p.add_argument("--leave", default=None)
        p.add_argument("--answer", default=None)
    if command == "close":
        p.add_argument("--word", default=None)
    return p


def _names_as_values(rest):
    """The word after `--name` or `--also` is that name, whatever it begins with: a name that starts with a hyphen is
    handed to RUN-2's name check, which refuses it with its fixed text (the owner's pick on PS47), and is not read here
    as another option. `--name=N` is the same argument, written as the parser reads it either way."""
    out, items = [], list(rest)
    while items:
        item = items.pop(0)
        if item in ("--name", "--also") and items:
            out.append(item + "=" + items.pop(0))
        else:
            out.append(item)
    return out


def _help_asked(rest):
    """`--help` or `-h` among a command's arguments, a name's own word apart (`_names_as_values`): `--name --help` names
    a project "--help", which RUN-2's name check refuses (PS47), and asks for no help."""
    return any(item in ("--help", "-h") for item in _names_as_values(rest))


def _valid(args):
    names = [args.name] + list(args.also)
    # what a name may hold is RUN-2 part (a)'s to say, after the gate, with its own fixed text (A135, PS47): a name that
    # folds to no key, which this line once refused as malformed, is one of its causes, and nothing of a name is checked here
    if any(not isinstance(n, str) for n in names):
        raise Usage()
    if args.run is not None and startup.run_kind_of(args.run) not in KINDS:
        raise Usage()
    if getattr(args, "answer", None) is not None and "=" not in args.answer:
        raise Usage()
    if sum(1 for x in (getattr(args, "done", None), getattr(args, "leave", None), getattr(args, "answer", None)) if x) > 1:
        raise Usage()
    return names


def tool_files(plugin):
    """The tool's own files, relative to the plugin's folder, in a fixed order: what the content hash covers and what
    the identity's commit must hold (SEC-12)."""
    out = []
    for base, dirs, files in os.walk(plugin):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "evals", ".git"))
        for entry in sorted(files):
            if entry.endswith(".pyc") or entry in (".DS_Store", ".git"):
                continue          # a repository's own folder, or a worktree's `.git` file, is no file of the tool
            out.append(os.path.relpath(os.path.join(base, entry), plugin).replace(os.sep, "/"))
    return out


# The identity command's one child: git, through the one runner like every other program (SEC-3; brief-2 section 2),
# its answer read by SEC-4's parser from git's own structured line, the commit an `equal` field against the tool's own
# read. A start that is no summons has no run directory, so the child is given no TMPDIR (SEC-3, A53).
GIT_COMMIT = {"tool": "git", "time_limit": 30, "trace_flags": ["--verbose", "-v", "--trace"],
              "exits": {"0": "success", "128": "not-found"}, "definite": {"success": ["success"], "refusals": ["not-found"]},
              "fields": [{"name": "commit", "place": ["commit"], "type": "hash", "form": "^[0-9a-f]{40}$", "disposition": "equal",
                          "required_in": ["success"]}]}


def git_answer(world, printer, plugin, own):
    """What a git child answers of the commit, kept as SEC-4 keeps an `equal` field: the tool's own copy where it equals
    the tool's own read, the fixed fact that it differs where it does not, and the fixed words for no answer where git
    gave none. A child's answer alone is held, and a start that is no summons has no protected record to name it by
    (SEC-6), so it is in no output (SEC-12)."""
    from . import facts as factsmod, results, runner
    decl = dict(GIT_COMMIT, fields=[dict(GIT_COMMIT["fields"][0], equals_value=own)])
    argv = ["-C", plugin, "log", "-1", '--format={"commit":"%H"}', "HEAD"]
    try:
        context = runner.Context(printer.register, None, factsmod.Facts(world.env).search_list(world.fs, world.system_folders))
        raw = runner.run(world, context, decl, argv, {}, plugin)
    except runner.Refused:
        return texts.NO_ANSWER
    result = results.Parser(decl, raw, printer.register).finish()
    kept = result.fields.get("commit") if result.kind == "success" else None
    if kept is None:
        return texts.NO_ANSWER
    return kept.safe            # the tool's own copy where equal; results.DIFFERS where not


def skill_identity(world, printer, plugin=None):
    from . import gitread
    here = os.path.dirname(os.path.abspath(__file__))
    lifecycle = os.path.dirname(os.path.dirname(here))
    plugin = plugin or os.path.dirname(lifecycle)
    lifecycle = os.path.join(plugin, "lifecycle")
    name, version = texts.TOOL, "unknown"
    try:
        with open(os.path.join(plugin, ".claude-plugin", "plugin.json"), "rb") as fh:
            body = json.loads(fh.read().decode("utf-8"))
        name, version = body.get("name", name), body.get("version", version)
    except (OSError, ValueError):
        pass
    files = tool_files(plugin)
    # the commit of the tool's own files as the tool reads it itself, in its own process (SEC-12, A54)
    own = gitread.commit_holding(plugin, files)
    by_git = git_answer(world, printer, plugin, own)
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        with open(os.path.join(plugin, *rel.split("/")), "rb") as fh:
            digest.update(fh.read())
        digest.update(b"\n")
    try:
        with open(os.path.join(lifecycle, "skills.json"), "rb") as fh:
            skills = [s.get("name") for s in json.loads(fh.read().decode("utf-8")).get("skills", [])]
    except (OSError, ValueError):
        skills = []
    doc = {"interface_version": texts.INTERFACE_VERSION, "plugin_version": version, "tool": texts.TOOL,
           "command": "skill-identity", "exit": 0, "ok": True, "name": name, "version": version,
           "commit": own or texts.NO_COMMIT, "commit_by_git": by_git, "content_sha256": digest.hexdigest(), "skills": skills}
    printer.document(doc)
    return exits.SUCCESS


def summons(world, command, rest, view=None):
    from . import commands
    printer = out.Printer(world, command)
    session = startup.Session(world, printer, command)
    world.invocation = world.new_id("i")
    session.withheld_read(view)             # the first act, before anything is printed
    try:
        args = parser_for(command).parse_args(_names_as_values(rest))
        names = _valid(args)
    except Usage:
        printer.error(texts.USAGE)
        return exits.USAGE
    try:
        try:
            session.gate()
            session.name_check(names)
            code = commands.HANDLERS[command](session, args)
        except startup.Ended as ended:
            code = printer.emit(ended.code, ending=ended.ending, lines=ended.lines, **ended.fields)
        except journalmod.Withheld:
            code = printer.emit(exits.TERMINAL, ending="stopped", lines=[texts.VALUE_WITHHELD_STOP])
    except Exception as exc:            # a defect: its type, never its message (SEC-5)
        session.finish()
        return printer.exception(exc, getattr(session, "operation", None))
    session.finish()
    return code


def _screened_text(printer, text):
    """A text of the tool's own, passed like every other line (SEC-12), first line by line and then whole, before any of it
    is written. Line by line: each complete line, its line break included, as the error writer passes its line
    (`out.Printer.error`; the reviewer's D8-N, A142); a line that holds a value gives way to the fixed words of withholding;
    where the fixed words, written with their own line break, would themselves hold a value, nothing is written in that
    place. A blank line is its line break alone, passed the same way. Then the whole text so made, as one text, as
    `out.Printer.document` passes a whole document (the reviewer's D8-L, check 3): a value that spans the end of one line
    and the start of the next holds no single line. Where the whole text still holds a value, the fixed words of withholding
    with their line break stand in place of the whole text; where they hold one themselves, nothing is written. The text is
    written in one write, so nothing of it is written before the whole is passed."""
    pieces = []
    for line in text.split("\n"):
        shown = printer.text(line) if line else ""
        if line and not shown:
            continue                      # the fixed words would hold a value themselves: nothing in that place
        if not printer._holds(shown + "\n"):
            pieces.append(shown + "\n")
            continue
        words = printer.text(texts.WITHHELD)
        if words and not printer._holds(words + "\n"):
            pieces.append(words + "\n")
    whole = "".join(pieces)
    if not printer._holds(whole):
        if whole:
            printer.world.output.out(whole)
        return
    words = printer.text(texts.WITHHELD)
    if words and not printer._holds(words + "\n"):
        printer.world.output.out(words + "\n")


def check_examples(world, printer, rest):
    from . import examples
    references, verbose = None, False
    items = list(rest)
    while items:
        item = items.pop(0)
        if item == "--references" and items:
            references = items.pop(0)
        elif item == "--verbose":
            verbose = True
        else:
            printer.error(texts.USAGE)
            return exits.USAGE
    lines = [] if verbose else None
    doc, code = examples.check(os.path.abspath(references) if references else schemas.references_dir(), lines)
    for line in lines or []:
        printer.error(line)
    # E16-15: `interface_version` 1 in every CLI response, in the envelope every other response carries
    printer.document(printer.envelope(exit=code, **doc))
    return code


def main(argv=None, world=None, view=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    world = world or worldmod.real()
    command, rest = (argv[0], argv[1:]) if argv else ("help", [])
    if command in SUMMONSES and not _help_asked(rest):
        return summons(world, command, rest, view)
    # every other start has the withheld read first and prints every line against it (SEC-12, D8-A)
    printer = out.Printer(world, command)
    startup.Session(world, printer, command).withheld_read(view)
    if not argv or command in ("-h", "--help", "help") or _help_asked(rest):
        _screened_text(printer, HELP.rstrip("\n"))
        return exits.SUCCESS if argv else exits.USAGE
    if command == "skill-identity" and not rest:
        return skill_identity(world, printer)
    if command == "check-examples":
        return check_examples(world, printer, rest)
    printer.error(texts.USAGE)
    return exits.USAGE
