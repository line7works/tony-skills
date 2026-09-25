"""The phase driver every front core runs (station-loop.md sections 2 and 3).

A library: `scripts/<station>.py` calls `main(station, hunts, handlers, argv)` with its own station
name, its hunt table, and the phases its lane has built. This module owns the parser, the
envelope, the run directory and its checkpoint, `check-input`, `select`, `identity`,
`skill-identity`, the error mapping onto the exit codes, and the placeholder stop of a phase no
lane has built yet (`phase-not-built`).

A handler is `handler(ctx, args) -> exit code`; `ctx` carries the station, the prefix, the skill
root, `envelope(**fields)`, `open_run(run_dir)` and `emit(document, code)`. A handler may raise
`Usage` (exit 2), `Defect` (exit 1), `Terminal(document)` (exit 10) or let
`records_client.ComponentUnavailable` through (exit 3).

A core's own commands (station-loop.md section 3.8) come through `commands`: a list of
`{"name", "help", "arguments", "handler"}`, each `arguments` entry `{"flags": [...], ...argparse
keyword arguments}`. The driver adds each as a subcommand with the common options, lists it under
"Commands of this core" in `--help`, and dispatches it exactly as a phase. A name that collides with
a shared command, or an entry missing a field, is a defect of the calling script (`ValueError`).
"""
import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

from . import exits, fsio, hunt as huntmod, inputs, validate
from .records_client import ComponentUnavailable

INTERFACE_VERSION = 1
# A driver named for its station would shadow a standard-library module of the same name when the
# scripts folder is first on the path (inspect.py shadows `inspect`, which jsonschema imports).
SHADOWED = ("inspect",)
LANE_PHASES = ("harvest", "record-answer", "write", "report")


class Usage(RuntimeError):
    """A usage slip: exit 2 with the sentence on stderr."""


class Defect(RuntimeError):
    """Anything else: exit 1."""


class Terminal(RuntimeError):
    """The run reached a terminal status; the document is already assembled."""

    def __init__(self, document):
        RuntimeError.__init__(self, document.get("status", "terminal"))
        self.document = document


def emit(document, code=exits.SUCCESS):
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return code


def now_utc():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class Context(object):
    """What a handler needs from the driver."""

    def __init__(self, station, hunts, skill_root):
        self.station = station
        self.hunts = hunts
        self.skill_root = skill_root
        self.prefix = validate.prefix_of(station)

    def envelope(self, **fields):
        out = {"interface_version": INTERFACE_VERSION,
               "plugin_version": validate.plugin_version(self.skill_root), "station": self.station}
        out.update(fields)
        return out

    def emit(self, document, code=exits.SUCCESS):
        return emit(document, code)

    def open_run(self, run_dir):
        return Run.open(run_dir)


class Run(object):
    """One run directory: `input.json` and `checkpoint.json`, written through a rename."""

    def __init__(self, run_dir, checkpoint):
        self.run_dir = run_dir
        self.checkpoint = checkpoint

    @classmethod
    def create(cls, run_dir, doc):
        if os.path.exists(os.path.join(run_dir, "checkpoint.json")):
            raise Usage("the run directory %s already holds a run: this run id has been used. Use "
                        "another run id and run directory." % run_dir)
        os.makedirs(run_dir, exist_ok=True)
        at = now_utc()
        fsio.write_json(os.path.join(run_dir, "input.json"), doc)
        checkpoint = {"checkpoint_version": 1, "run_id": doc["run_id"], "phase": "checked",
                      "input_sha256": inputs.input_digest(doc), "at": at, "selections": {}}
        fsio.write_json(os.path.join(run_dir, "checkpoint.json"), checkpoint)
        return cls(run_dir, checkpoint)

    @classmethod
    def open(cls, run_dir):
        path = os.path.join(run_dir or "", "checkpoint.json")
        if not run_dir or not os.path.isfile(path):
            raise Usage("no run at %s: its checkpoint.json is not there. Run `check-input` first." % run_dir)
        try:
            checkpoint = fsio.read_json(path)
            doc = fsio.read_json(os.path.join(run_dir, "input.json"))
        except (OSError, ValueError) as exc:
            raise Defect("the run at %s cannot be read: %s" % (run_dir, exc))
        if checkpoint.get("input_sha256") != inputs.input_digest(doc):
            raise Usage("the run at %s cannot be continued: its input.json no longer matches the "
                        "input the run checked" % run_dir)
        run = cls(run_dir, checkpoint)
        run.input = doc
        return run

    def save(self):
        fsio.write_json(os.path.join(self.run_dir, "checkpoint.json"), self.checkpoint)


# ---- the commands ------------------------------------------------------------------------------

def command_check_input(ctx, args):
    """Validate the input, create the run, and write the resolved input."""
    schema = validate.load_schema("input", ctx.prefix, ctx.skill_root)
    try:
        doc = inputs.read(args.input)
    except inputs.InputUnreadable as exc:
        raise Usage(str(exc))
    doc = inputs.with_defaults(doc)
    errors = inputs.validate_input(doc, schema, ctx.prefix)
    if errors:
        return emit(ctx.envelope(ok=False, error="invalid",
                                 reason="the input does not validate: %d finding(s); nothing was "
                                        "written and no run was created" % len(errors),
                                 errors=errors), exits.VALIDATION)
    run = Run.create(doc["run_dir"], doc)
    return emit(ctx.envelope(next="select", run_id=doc["run_id"], run_dir=doc["run_dir"],
                             workspace=doc["workspace"], staging=doc.get("staging"),
                             report_only=bool(doc.get("report_only")),
                             input=os.path.join(run.run_dir, "input.json")))


def command_select(ctx, args):
    """The hunt, over the homes this core's table names (E14-10)."""
    run = Run.open(args.run_dir)
    if run.checkpoint.get("phase") not in ("checked", "selected"):
        raise Usage("this run is at phase %r; `select` runs after `check-input` and before `harvest`"
                    % run.checkpoint.get("phase"))
    names = sorted(ctx.hunts)
    hunt_name = args.hunt or (names[0] if len(names) == 1 else None)
    if hunt_name is None:
        raise Usage("this core has several hunts (%s): name one with --hunt" % ", ".join(names))
    if hunt_name not in ctx.hunts:
        raise Usage("no hunt %r in this core (its hunts: %s)" % (hunt_name, ", ".join(names)))
    roots = {"workspace": run.input.get("workspace"), "staging": run.input.get("staging")}
    try:
        result = huntmod.hunt(ctx.hunts[hunt_name], roots, name=args.name)
    except huntmod.HuntRefused as exc:
        raise Usage(str(exc))
    result = dict(result, hunt=hunt_name, name=args.name)
    fsio.write_json(os.path.join(run.run_dir, "selection-%s.json" % hunt_name), result)
    run.checkpoint["phase"] = "selected"
    run.checkpoint.setdefault("selections", {})[hunt_name] = result["outcome"]
    run.save()
    return emit(ctx.envelope(next="harvest", run_id=run.checkpoint["run_id"], **result))


def command_identity(ctx, args):
    """The workspace as this station sees it, without the records component."""
    path = os.path.abspath(args.workspace)
    if not os.path.isdir(path):
        raise Usage("the workspace is not a directory: %s" % path)
    head = None
    kind = "directory"
    try:
        proc = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel", "HEAD"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace").split()
        if proc.returncode == 0 and len(out) == 2 and os.path.realpath(out[0]) == os.path.realpath(path):
            kind, head = "git", out[1]
    except OSError:
        pass
    return emit(ctx.envelope(ok=True, workspace=os.path.realpath(path), kind=kind, head=head))


def command_skill_identity(ctx, args):
    """Name, version, the commit the skill sits in, and its content hash."""
    root = validate.skill_root(ctx.skill_root)
    plugin = os.path.dirname(os.path.dirname(root))
    name, version = ctx.station, "unknown"
    try:
        body = fsio.read_json(os.path.join(plugin, ".claude-plugin", "plugin.json"))
        name, version = body.get("name", name), body.get("version", version)
    except (OSError, ValueError):
        pass
    commit = None
    try:
        proc = subprocess.run(["git", "-C", plugin, "rev-parse", "HEAD"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if proc.returncode == 0:
            commit = proc.stdout.decode("utf-8", "replace").strip() or None
    except OSError:
        pass
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for entry in sorted(files):
            if entry.endswith(".pyc") or entry == ".DS_Store":
                continue
            full = os.path.join(base, entry)
            digest.update(os.path.relpath(full, root).encode("utf-8"))
            digest.update(b"\0")
            with open(full, "rb") as fh:
                digest.update(fh.read())
            digest.update(b"\n")
    return emit(ctx.envelope(ok=True, name=name, version=version, commit=commit or "unversioned",
                             content_sha256=digest.hexdigest()))


def not_built(phase):
    def handler(ctx, args):
        reason = ("the `%s` phase of %s is not built yet: the frame fixes its command line, and the "
                  "station's slice 2 lane builds what it does. Nothing was read or written."
                  % (phase, ctx.station))
        return emit(ctx.envelope(next="done", status="stopped", stop_tag="phase-not-built",
                                 reason=reason, run_dir=getattr(args, "run_dir", None)), exits.TERMINAL)
    return handler


def script_name(station):
    """`precon.py` for precon-v2; `inspect_v2.py` for inspect-v2 (see SHADOWED)."""
    base = station.split("-")[0]
    return "%s%s" % (base, "_v2.py" if base in SHADOWED else ".py")


# ---- the parser --------------------------------------------------------------------------------

EXIT_HELP = """Exit codes:
  0   the command did its work; an intermediate phase has more to do
  1   anything else: a defect of the script, an unreadable run directory
  2   usage: a bad argument, a file that is not there or not JSON, the wrong phase, an unknown hunt
  3   missing dependency: jsonschema, or (inspect-v2) the records component. One line on stderr
  4   validation: a supplied file failed its schema; nothing is written
  5   the recorded answer was refused on its content (E14-11); nothing is written
  10  the run reached a terminal status (a completion or a stop)
"""

SIDE_EFFECTS = """Side effects:
  check-input     creates the run directory; writes input.json and checkpoint.json in it
  select          writes selection-<hunt>.json and rewrites checkpoint.json in the run directory
  harvest, record-answer, write, report
                  the lane's (station-loop.md section 3): the run directory, and the documents `write`
                  renders, each listed in the receipt; a phase the lane has not built writes nothing
  own commands    the lane contract's (station-loop.md section 3.8)
  identity, skill-identity
                  none
  Nothing is written outside the run directory by the frame. No network, no model call, no harness.
"""


def build_parser(station, hunts, commands=None):
    prog = script_name(station)
    commands = check_commands(commands)
    hunt_lines = "\n".join("  %-14s %s" % (name, "; ".join(
        "%s(%s) %s" % (h["home"], h["root"], ", ".join(h["globs"])) for h in homes))
                           for name, homes in sorted(hunts.items()))
    own_lines = "\n".join("  %-16s %s" % (c["name"], c["help"]) for c in commands) or "  (none)"
    epilog = ("The phases, in order: check-input, select, harvest, record-answer, write, report.\n"
              "identity and skill-identity answer at any time.\n\n"
              "Hunts of this core (select --hunt NAME):\n%s\n\n"
              "Commands of this core (station-loop.md section 3.8; its lane contract says what each does):\n%s\n\n%s\n%s\n"
              "Example:\n  uv run %s check-input /tmp/run-0001/input.json\n"
              "  uv run %s select --run-dir /tmp/run-0001 --hunt %s --name widget\n"
              % (hunt_lines, own_lines, EXIT_HELP, SIDE_EFFECTS, prog, prog, sorted(hunts)[0] if hunts else "NAME"))
    parser = argparse.ArgumentParser(prog=prog, description="The phase driver of %s." % station,
                                     epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    skill_help = "test only: load the references from DIR instead of this script's skill root"
    records_help = ("the records component's root (inspect-v2); without it the component's four "
                    "lookups are used")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--skill-root", metavar="DIR", default=None, help=skill_help)
    common.add_argument("--records-root", metavar="DIR", default=None, help=records_help)
    sub = parser.add_subparsers(dest="command")
    one = sub.add_parser("check-input", parents=[common], help="validate the input and create the run")
    one.add_argument("input", metavar="input.json", help="the input document (references/input.schema.json)")
    sel = sub.add_parser("select", parents=[common], help="find the documents this core reads (E14-10)")
    sel.add_argument("--run-dir", metavar="D", required=True, help="the run directory")
    sel.add_argument("--hunt", metavar="NAME", default=None, help="one of this core's hunts")
    sel.add_argument("--name", metavar="NAME", default=None,
                     help="fills {name} in the hunt's globs (default: every name, '*')")
    for phase in LANE_PHASES:
        cmd = sub.add_parser(phase, parents=[common], help="the %s phase (the lane's)" % phase)
        cmd.add_argument("--run-dir", metavar="D", required=True, help="the run directory")
        if phase == "record-answer":
            cmd.add_argument("--answer", metavar="FILE", required=True, help="the recorded answer")
    ident = sub.add_parser("identity", parents=[common], help="the workspace as this station sees it")
    ident.add_argument("workspace", help="a directory")
    sub.add_parser("skill-identity", parents=[common], help="name, version, commit and content hash")
    for own in commands:
        cmd = sub.add_parser(own["name"], parents=[common], help=own["help"])
        for argument in own["arguments"]:
            keywords = dict(argument)
            cmd.add_argument(*keywords.pop("flags"), **keywords)
    return parser


SHARED_COMMANDS = ("check-input", "select", "identity", "skill-identity") + LANE_PHASES


COMMON_FLAGS = ("--skill-root", "--records-root", "-h", "--help")
OWN_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


def check_commands(commands):
    """A core's own commands, checked for shape: every field present, a callable handler, a name of
    lowercase letters, digits and hyphens that is neither a shared command's nor another own command's,
    and no flag that collides with a common option or is not a flag at all."""
    out = []
    for own in commands or ():
        for key in ("name", "help", "arguments", "handler"):
            if key not in own:
                raise ValueError("a core's own command is missing %r: %r" % (key, own))
        name = own["name"]
        if not isinstance(name, str) or not OWN_NAME.match(name):
            raise ValueError("a core's own command needs a name of lowercase letters, digits and hyphens: %r" % (name,))
        if name in SHARED_COMMANDS or any(name == c["name"] for c in out):
            raise ValueError("a core's own command may not reuse the name %r" % name)
        if not callable(own["handler"]):
            raise ValueError("the handler of %r is not callable" % name)
        if not isinstance(own["arguments"], (list, tuple)):
            raise ValueError("the arguments of %r are not a list" % name)
        seen_flags = set()
        for argument in own["arguments"]:
            if not isinstance(argument, dict):
                raise ValueError("an argument of %r is not a mapping: %r" % (name, argument))
            flags = argument.get("flags")
            if not flags or not isinstance(flags, (list, tuple)):
                raise ValueError("an argument of %r has no flags: %r" % (name, argument))
            for flag in flags:
                if not isinstance(flag, str):
                    raise ValueError("an argument flag of %r is not a string: %r" % (name, flag))
                if flag in seen_flags:
                    raise ValueError("an argument flag of %r repeats: %r" % (name, flag))
                seen_flags.add(flag)
            if "help" in argument and not isinstance(argument["help"], str):
                raise ValueError("the help of an argument of %r is not a string" % name)
            if argument.get("action") in ("help", "version"):
                raise ValueError("an argument of %r uses the reserved action %r" % (name, argument["action"]))
            if argument.get("action") in ("store_const", "append_const") and "const" not in argument:
                raise ValueError("an argument of %r has action %r and no const" % (name, argument["action"]))
            if argument.get("action") in ("store_true", "store_false", "count", "store_const"):
                bad = [k for k in ("metavar", "type", "choices", "nargs") if k in argument]
                if bad or (argument.get("action") != "store_const" and "const" in argument):
                    raise ValueError("an argument of %r combines action %r with %s" % (name, argument["action"], ", ".join(bad or ["const"])))
            for flag in flags:
                if not isinstance(flag, str) or not flag.startswith("-"):
                    raise ValueError("an argument flag of %r is not a flag: %r" % (name, flag))
                if flag in COMMON_FLAGS:
                    raise ValueError("an argument of %r reuses the common option %r" % (name, flag))
            unknown = set(argument) - ARGPARSE_KEYS
            if unknown:
                raise ValueError("an argument of %r carries keys argparse does not take: %s" % (name, ", ".join(sorted(unknown))))
            if "dest" in argument and not isinstance(argument["dest"], str):
                raise ValueError("the dest of an argument of %r is not a string" % name)
            dest = argument.get("dest") or [f for f in flags if f.startswith("--")][:1] or [flags[0]]
            dest = (dest if isinstance(dest, str) else dest[0]).lstrip("-").replace("-", "_")
            if dest in RESERVED_DESTS:
                raise ValueError("an argument of %r would fill the reserved destination %r" % (name, dest))
        out.append(own)
    return out


RESERVED_DESTS = ("command", "skill_root", "records_root", "help")
ARGPARSE_KEYS = {"flags", "action", "nargs", "const", "default", "type", "choices", "required", "help",
                 "metavar", "dest"}


def check_handlers(handlers):
    """A core's `HANDLERS` is a mapping of lane phase to a callable; a key outside the four phases (a
    misspelling), a non-mapping, or a value that is not callable is a defect of the calling script."""
    if handlers is None:
        return {}
    if not isinstance(handlers, dict):
        raise ValueError("HANDLERS is a mapping of lane phase to handler, not %r" % type(handlers).__name__)
    for phase, handler in handlers.items():
        if phase not in LANE_PHASES:
            raise ValueError("HANDLERS names %r, which is no lane phase (%s)" % (phase, ", ".join(LANE_PHASES)))
        if not callable(handler):
            raise ValueError("the handler of %r is not callable" % phase)
    return handlers


DIAGNOSTIC_EXITS = (exits.GENERAL, exits.USAGE, exits.MISSING_DEPENDENCY)


def checked_dispatch(handler, ctx, args):
    """Every command's exit code and stdout are checked before either leaves the process (the fifteenth seam
    fix: the outside reviewer's L-3, P-4, A3 and I F7). The handler runs with stdout captured. It may return
    only an exit code the interface documents (`exits.ALL`); on a diagnostic exit (1, 2, 3) it has written
    nothing to stdout; on every other exit its stdout is exactly one JSON object carrying this run's envelope
    (interface_version, plugin_version, station); a SystemExit inside it is allowed only as a diagnostic exit
    with nothing on stdout (the frame's missing-dependency path). Anything else is a
    Defect: exit 1 with the sentence on stderr and nothing released to stdout. A Terminal raised inside is
    emitted as before and then checked the same way; a Usage raised inside propagates as usage. The frame's
    own commands, the lane phases and a core's own commands all pass through here: one rule."""
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            try:
                code = handler(ctx, args)
            except Terminal as terminal:
                code = emit(terminal.document, exits.TERMINAL)
    except SystemExit as exc:
        # the frame's own missing-dependency path exits 3 through SystemExit with nothing on stdout; that is a
        # diagnostic exit like any other; every other SystemExit is a defect
        if type(exc.code) is int and exc.code in DIAGNOSTIC_EXITS and not captured.getvalue().strip():
            return exc.code
        raise Defect("a command handler raised SystemExit: %r" % (exc.code,))
    if type(code) is not int or code not in exits.ALL:
        raise Defect("a command handler returned an exit code the interface does not document: %r" % (code,))
    output = captured.getvalue()
    if code in DIAGNOSTIC_EXITS:
        if output.strip():
            raise Defect("a command handler wrote to stdout on a diagnostic exit %d" % code)
        return code
    try:
        document = json.loads(output)
    except ValueError:
        raise Defect("a command handler did not emit exactly one JSON document on exit %d" % code)
    expected = ctx.envelope()
    if not isinstance(document, dict) or any(document.get(key) != value for key, value in expected.items()):
        raise Defect("a command handler emitted a document without this run's envelope")
    sys.stdout.write(output)
    sys.stdout.flush()
    return code


def main(station, hunts, handlers, argv=None, commands=None):
    commands = check_commands(commands)
    handlers = check_handlers(handlers)
    parser = build_parser(station, hunts, commands)
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return exits.USAGE
    try:
        skill_root = validate.skill_root(args.skill_root)
    except validate.SkillRootMissing as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    ctx = Context(station, hunts, skill_root)
    commands_by_name = {"check-input": command_check_input, "select": command_select,
                        "identity": command_identity, "skill-identity": command_skill_identity}
    for phase in LANE_PHASES:
        commands_by_name[phase] = handlers.get(phase) or not_built(phase)
    for own in commands:
        commands_by_name[own["name"]] = own["handler"]
    try:
        return checked_dispatch(commands_by_name[args.command], ctx, args)
    except Terminal as terminal:
        return emit(terminal.document, exits.TERMINAL)
    except Usage as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except ComponentUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.MISSING_DEPENDENCY
    except Defect as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.GENERAL
