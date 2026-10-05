"""The run, its stages, the clock and the artifacts (ship-v2's own; contract sections 3 and 4).

THE STAGES. ship-v2's phases are not a straight line: a station is visited three times, a fix comes after a signoff
and after a lap, and a pause can come at any time. The checkpoint's `phase` holds the run's stage, and every command
names the stages it runs at; a command against another stage is exit 2 naming the command to run instead:

    checked      after check-input                 -> select
    selected     the doc and the slice read          -> hook
    hooked       the hook reading recorded           -> visit --station build-v2
    built        build-v2 COMPLETE                   -> visit --station signoff-v2
    visiting     a visit handed to the executor      -> visit --result
    fixing       findings to fix in this lap         -> fix
    fixed        the lap's fixes recorded            -> visit --station recheck-v2
    lap-needed   recheck not clear, a lap remains    -> lap
    exhausted    recheck not clear, no lap remains   -> report (stop condition 1); `lap` is refused, exit 5
    clean        ALL CLEAR                           -> report
    ending       a stop decided                      -> report
    paused       a question waits for the owner      -> pause --answer
    done         the result is written               -> nothing

A stop is decided where it happens (the stage `ending`, nothing but `report` after it, so no later visit can reach
the trace); `report` writes the one result with the executor's bottom line. Every run file this core reads or
writes is checked with `os.lstat` first: a link, a pipe or a file outside the run directory is refused, never
followed.
"""
import datetime
import json
import os
import re
import stat

from station_core import driver, fsio, validate

STATION = "ship-v2"
PREFIX = "SHIP_V2"
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STATIONS = ("build-v2", "signoff-v2", "recheck-v2")
STATE = "ship.json"
NEXT = {"checked": "select", "selected": "hook", "hooked": "visit --station build-v2",
        "built": "visit --station signoff-v2", "visiting": "visit --result", "fixing": "fix",
        "fixed": "visit --station recheck-v2", "lap-needed": "lap", "exhausted": "report", "clean": "report",
        "ending": "report", "paused": "pause --answer", "done": "nothing: the run is over"}
# the stages a pause may be asked at: every stage of a live run after the doc is read
PAUSABLE = ("selected", "hooked", "built", "visiting", "fixing", "fixed", "lap-needed", "exhausted", "clean")
BLOCKING = ("BLOCKER", "MAJOR")


def test_mode(environ=None):
    environ = os.environ if environ is None else environ
    return environ.get(PREFIX + "_TEST") == "1"


def now(environ=None):
    """The UTC instant this run writes. `SHIP_V2_TEST_NOW` fixes it, honored only with `SHIP_V2_TEST=1`."""
    environ = os.environ if environ is None else environ
    fixed = environ.get(PREFIX + "_TEST_NOW")
    if test_mode(environ) and fixed:
        if not INSTANT.match(fixed):
            raise driver.Usage("%s_TEST_NOW is %r, not an instant like 2026-10-01T12:00:00Z" % (PREFIX, fixed))
        return fixed
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def open_run(ctx, run_dir, stages, command):
    """The run, at one of `stages`, or exit 2 naming the command to run instead."""
    run = ctx.open_run(run_dir)
    stage = run.checkpoint.get("phase")
    if stage not in stages:
        raise driver.Usage("this run is at stage %r: `%s` runs at %s; run `%s` instead"
                           % (stage, command, " or ".join(repr(s) for s in stages), NEXT.get(stage, "check-input")))
    return run


def advance(run, stage):
    run.checkpoint["phase"] = stage
    run.save()


def path_of(run, name):
    return os.path.join(run.run_dir, name)


def irregular(run, path):
    """Why the run file at `path` must not be opened, or None (a link, a pipe, a file outside the run directory)."""
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return None
    except OSError as exc:
        return "cannot be examined (%s)" % exc
    if stat.S_ISLNK(mode):
        return "is a link, not a regular file in the run directory"
    if not stat.S_ISREG(mode):
        return "is not a regular file (a named pipe, a socket, a device or a folder)"
    if not fsio.inside(path, run.run_dir):
        return "is not a regular file in the run directory (its real path lies outside it)"
    return None


def has(run, name):
    return os.path.lexists(path_of(run, name))


def read(run, name):
    why = irregular(run, path_of(run, name))
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run directory has been changed by hand, and the run "
                            "refuses; nothing was opened and nothing was written" % (name, why))
    try:
        return fsio.read_json(path_of(run, name))
    except (OSError, ValueError) as exc:
        raise driver.Defect("the run artifact %s cannot be read: %s" % (name, exc))


def write(run, name, doc):
    why = irregular(run, path_of(run, name))
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run refuses to write over it" % (name, why))
    fsio.write_json(path_of(run, name), doc)
    return path_of(run, name)


def write_text(run, name, text):
    why = irregular(run, path_of(run, name))
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run refuses to write over it" % (name, why))
    fsio.atomic_write(path_of(run, name), text.encode("utf-8"))
    return path_of(run, name)


def state(run):
    """`ship.json`, held to the hash the checkpoint recorded when the run last saved it: a hand edit of the run's
    state (its lap counter, its pin, its named findings) is detected and refused, never acted on."""
    if not has(run, STATE):
        return {}
    why = irregular(run, path_of(run, STATE))
    if why is None and fsio.sha256_file(path_of(run, STATE)) != run.checkpoint.get("state_sha256"):
        why = "does not hold the bytes this run last saved (the checkpoint's state_sha256)"
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run directory has been changed by hand, and the run refuses; "
                            "nothing was written" % (STATE, why))
    return read(run, STATE)


def save(run, doc):
    write(run, STATE, doc)
    run.checkpoint["state_sha256"] = fsio.sha256_file(path_of(run, STATE))
    run.save()


def listing(run, name, key):
    return list(read(run, name)[key]) if has(run, name) else []


def station(run):
    value = run.input.get("station")
    return value if isinstance(value, dict) else {}


def workspace(run):
    return run.input["workspace"]


def report_only(run):
    return bool(run.input.get("report_only"))


def harness(run):
    return (run.input.get("invocation") or {}).get("harness")


def run_id(run):
    return run.checkpoint["run_id"]


def date_of(run):
    return now()[:10]


def load_json_file(path, what):
    """A caller's JSON file: exit 2 when it is not there, not JSON or not an object."""
    if not path or not os.path.isfile(path):
        raise driver.Usage("no such %s file: %s" % (what, path))
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise driver.Usage("the %s file is not JSON: %s (%s)" % (what, path, exc))
    if not isinstance(doc, dict):
        raise driver.Usage("the %s file is not a JSON object: %s" % (what, path))
    return doc


def schema(name, ctx):
    """One of this core's own schemas under references/ (the shared loader knows input and result)."""
    validate.require_jsonschema(ctx.prefix)
    path = os.path.join(validate.references_dir(ctx.skill_root), name)
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/%s (%s)" % (name, exc))


def answer_file(ctx, run, path, kind, what):
    """A file the executor hands over (`references/answer.schema.json`, kind `kind`): exit 2 when it cannot be read,
    exit 4 (the caller emits) when it fails the schema, refused (exit 5) when it names another run."""
    doc = load_json_file(path, what)
    errors = validate.errors_for(doc, schema("answer.schema.json", ctx), ctx.prefix)
    if not errors and doc.get("kind") != kind:
        errors = [{"path": "/kind", "message": "a %s file is kind %r, not %r" % (what, kind, doc.get("kind"))}]
    if errors:
        return None, ctx.emit(ctx.envelope(ok=False, error="invalid", run_id=run_id(run),
                                           reason="the %s file does not validate; nothing was written and the run "
                                                  "stays where it was" % what, errors=errors), 4)
    if "run_id" in doc and doc["run_id"] != run_id(run):
        return None, refuse(ctx, run, "the %s file names the run %r, not this run %r" % (what, doc["run_id"],
                                                                                         run_id(run)))
    return doc, None


def refuse(ctx, run, reason):
    """Exit 5: refused on its content; nothing written, the run where it was."""
    return ctx.emit(ctx.envelope(accepted=False, run_id=run_id(run), reason=reason + "; nothing was written and the "
                                                                                    "run stays where it was"), 5)


def laps_allowed(run):
    """One initial pass and one extra lap, plus the laps the owner's words in the input order (CR-22): read from the
    input itself, never from a run file."""
    return 2 + int((station(run).get("extra_laps") or {}).get("count") or 0)


def read_doc_bytes(ws, rel):
    with open(os.path.join(ws, rel), "rb") as fh:
        return fh.read()
