"""The back loop's phase driver: a back core's own phase table over the station_core driver's seams.

    main(station, phases, argv=None, hunts=None) -> exit code

The E14 driver (`station_core/driver.py`, copied byte for byte, ruling E15-3) fixes the front loop's
four lane phases. A back core's phases are its own (vertical: gate, ask, scope, request, record-local,
record-outside, verdict, report; handoff and ship: their contracts'), so this module builds the parser
from the core's table, in the table's order, and reuses everything else the E14 driver owns unchanged:
the run directory and its checkpoint (`Run`), the context and its envelope (`Context`), the checked
dispatch every command passes through (`checked_dispatch`), `identity`, `skill-identity`, the error
mapping onto the exit codes, and the placeholder stop of a phase not built yet (`phase-not-built`).

A phase is `{"name", "help", "arguments", "handler"}`; `arguments` are argparse entries in the shape
the E14 driver's `check_commands` holds (`{"flags": [...], ...}`), and `--run-dir` is added to every
phase. A `handler` of None is a phase this hand-back has not built: it answers `phase-not-built` with
exit 10 and reads and writes nothing. `check-input` validates the input against the core's
`references/input.schema.json` (closed), applies the path rules, creates the run and names the table's
first phase as `next`. Every command's stdout is one JSON document carrying `interface_version` (1),
`plugin_version` and `station`.

Exit codes are the E14 table's: 0 the command did its work, 1 a defect, 2 usage, 3 a missing
dependency (jsonschema, the records component, readers), 4 validation, 5 refused (nothing written),
10 the run reached a terminal status. Shared by the three back cores (`references/back-files.txt`).
"""
import argparse
import os
import sys

from station_core import driver, exits, inputs, validate
from station_core.records_client import ComponentUnavailable

SHARED = ("check-input", "identity", "skill-identity")
RUN_DIR = {"flags": ["--run-dir"], "metavar": "D", "required": True, "help": "the run directory"}

EPILOG = """Exit codes:
  0   the command did its work; an intermediate phase has more to do
  1   anything else: a defect of the script, an unreadable run directory
  2   usage: a bad argument, a file that is not there or not JSON, the wrong phase
  3   missing dependency: jsonschema, the records component, or readers. One line on stderr
  4   validation: a supplied file failed its schema; nothing is written
  5   refused: an answer, a request or an input a rule of this core refuses; nothing is written
  10  the run reached a terminal status (a completion or a stop, phase-not-built included)

Side effects:
  check-input     creates the run directory; writes input.json and checkpoint.json in it
  the phases      the run directory, and what the core's contract says each phase writes
  identity, skill-identity
                  none
  No network, no model call, no harness, no reader summoned, no station invoked by a script.
"""


def check_phases(phases):
    """The phase table, checked for shape: names unique, none a shared command's, each with a help
    line, a list of arguments and a callable handler or None. A malformed table is a defect of the
    calling script (ValueError)."""
    out = []
    seen = set()
    for phase in phases or ():
        for key in ("name", "help", "arguments", "handler"):
            if key not in phase:
                raise ValueError("a phase is missing %r: %r" % (key, phase))
        name = phase["name"]
        if not isinstance(name, str) or not driver.OWN_NAME.match(name):
            raise ValueError("a phase needs a name of lowercase letters, digits and hyphens: %r" % (name,))
        if name in SHARED or name in seen:
            raise ValueError("a phase may not reuse the name %r" % name)
        if phase["handler"] is not None and not callable(phase["handler"]):
            raise ValueError("the handler of %r is not callable" % name)
        seen.add(name)
        out.append(dict(phase, arguments=[RUN_DIR] + list(phase["arguments"])))
    if not out:
        raise ValueError("a back core has at least one phase")
    # the arguments are held to the E14 driver's own rules for a core's commands; the names were checked
    # above (a back core's phase may carry a name the front loop uses, such as `report`)
    driver.check_commands([{"name": "phase-%d" % index, "help": p["help"], "arguments": p["arguments"],
                            "handler": (lambda ctx, args: 0)} for index, p in enumerate(out)])
    return out


def not_built(phase):
    def handler(ctx, args):
        reason = ("the `%s` phase of %s is not built yet: the back frame fixes its command line, and a later "
                  "hand-back builds what it does. Nothing was read or written." % (phase, ctx.station))
        return driver.emit(ctx.envelope(next="done", status="stopped", stop_tag="phase-not-built", reason=reason,
                                        run_dir=getattr(args, "run_dir", None)), exits.TERMINAL)
    return handler


def check_input(first):
    def handler(ctx, args):
        schema = validate.load_schema("input", ctx.prefix, ctx.skill_root)
        try:
            doc = inputs.read(args.input)
        except inputs.InputUnreadable as exc:
            raise driver.Usage(str(exc))
        doc = inputs.with_defaults(doc)
        errors = inputs.validate_input(doc, schema, ctx.prefix)
        if errors:
            return driver.emit(ctx.envelope(ok=False, error="invalid",
                                            reason="the input does not validate: %d finding(s); nothing was "
                                                   "written and no run was created" % len(errors),
                                            errors=errors), exits.VALIDATION)
        run = driver.Run.create(doc["run_dir"], doc)
        return driver.emit(ctx.envelope(next=first, run_id=doc["run_id"], run_dir=doc["run_dir"],
                                        workspace=doc["workspace"], report_only=bool(doc.get("report_only")),
                                        input=os.path.join(run.run_dir, "input.json")))
    return handler


def build_parser(station, phases):
    prog = driver.script_name(station)
    order = ", ".join(["check-input"] + [p["name"] for p in phases])
    lines = "\n".join("  %-16s %s%s" % (p["name"], p["help"], "" if p["handler"] else " (not built yet: phase-not-built)")
                      for p in phases)
    epilog = ("The phases, in order: %s.\nidentity and skill-identity answer at any time.\n\n"
              "Phases of this core (its contract under references/ says what each reads, writes and prints):\n%s\n\n%s\n"
              "Example:\n  uv run %s check-input /tmp/run-0001/input.json\n  uv run %s %s --run-dir /tmp/run-0001\n"
              % (order, lines, EPILOG, prog, prog, phases[0]["name"]))
    parser = argparse.ArgumentParser(prog=prog, description="The phase driver of %s." % station, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--skill-root", metavar="DIR", default=None,
                        help="test only: load the references from DIR instead of this script's skill root")
    common.add_argument("--records-root", metavar="DIR", default=None,
                        help="the records component's root; without it the component's four lookups are used")
    sub = parser.add_subparsers(dest="command")
    one = sub.add_parser("check-input", parents=[common], help="validate the input and create the run")
    one.add_argument("input", metavar="input.json", help="the input document (references/input.schema.json)")
    for phase in phases:
        cmd = sub.add_parser(phase["name"], parents=[common], help=phase["help"])
        for argument in phase["arguments"]:
            keywords = dict(argument)
            cmd.add_argument(*keywords.pop("flags"), **keywords)
    ident = sub.add_parser("identity", parents=[common], help="the workspace as this station sees it")
    ident.add_argument("workspace", help="a directory")
    sub.add_parser("skill-identity", parents=[common], help="name, version, commit and content hash")
    return parser


def main(station, phases, argv=None, hunts=None):
    phases = check_phases(phases)
    parser = build_parser(station, phases)
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return exits.USAGE
    try:
        skill_root = validate.skill_root(args.skill_root)
    except validate.SkillRootMissing as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    ctx = driver.Context(station, hunts or {}, skill_root)
    commands = {"check-input": check_input(phases[0]["name"]), "identity": driver.command_identity,
                "skill-identity": driver.command_skill_identity}
    for phase in phases:
        commands[phase["name"]] = phase["handler"] or not_built(phase["name"])
    try:
        return driver.checked_dispatch(commands[args.command], ctx, args)
    except driver.Terminal as terminal:
        return driver.emit(terminal.document, exits.TERMINAL)
    except driver.Usage as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except ComponentUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.MISSING_DEPENDENCY
    except driver.Defect as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.GENERAL
