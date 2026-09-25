"""The run, its phases, the clock and the artifacts (inspect-v2's own; contract section 3)."""
import datetime
import json
import os
import re

from station_core import driver, fsio, validate

STATION = "inspect-v2"
PREFIX = "INSPECT_V2"
CLAUDE_LENSES = ("traceability", "code-book", "repo-reality")
OUTSIDE_LENSES = ("paper", "repo-reality")
PAPER_LENSES = ("traceability", "code-book", "paper")
ANTHROPIC = "anthropic"
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# what each phase follows, and the command to run instead when a run is elsewhere
NEXT = {"checked": "select", "selected": "harvest", "harvested": "packet", "packeted": "request",
        "requested": "record-answer", "answered": "write", "written": "report", "done": "nothing: the run is over"}


def test_mode(environ=None):
    environ = os.environ if environ is None else environ
    return environ.get(PREFIX + "_TEST") == "1"


def now(environ=None):
    """The UTC instant this run writes (`at` on every event; the date of the block, the stamp and the
    mirror). `INSPECT_V2_TEST_NOW` fixes it, honored only with `INSPECT_V2_TEST=1`."""
    environ = os.environ if environ is None else environ
    fixed = environ.get(PREFIX + "_TEST_NOW")
    if test_mode(environ) and fixed:
        if not INSTANT.match(fixed):
            raise driver.Usage("%s_TEST_NOW is %r, not an instant like 2026-09-25T12:00:00Z" % (PREFIX, fixed))
        return fixed
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def open_run(ctx, run_dir, phases, command):
    """The run, at one of `phases`, or exit 2 naming the command to run instead."""
    run = ctx.open_run(run_dir)
    phase = run.checkpoint.get("phase")
    if phase not in phases:
        raise driver.Usage("this run is at phase %r: `%s` runs at %s; run `%s` instead"
                           % (phase, command, " or ".join(repr(p) for p in phases), NEXT.get(phase, "check-input")))
    return run


def path_of(run, name):
    return os.path.join(run.run_dir, name)


def has(run, name):
    return os.path.isfile(path_of(run, name))


def read(run, name):
    try:
        return fsio.read_json(path_of(run, name))
    except (OSError, ValueError) as exc:
        raise driver.Defect("the run artifact %s cannot be read: %s" % (name, exc))


def write(run, name, doc):
    fsio.write_json(path_of(run, name), doc)
    return path_of(run, name)


def station(run):
    return (run.input.get("station") or {}) if isinstance(run.input.get("station"), dict) else {}


def workspace(run):
    return run.input["workspace"]


def report_only(run):
    return bool(run.input.get("report_only"))


def plugin_root():
    """This core's plugin root from this file: inspect_core -> scripts -> skills/inspect-v2 -> skills -> the plugin."""
    scripts = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.dirname(os.path.dirname(scripts)))


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
            body = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/%s (%s)" % (name, exc))
    return body


def number(text):
    """The document with every line prefixed `N: `, the lines counted as an editor counts them
    (split on LF; a CR stays part of its line; the final newline ends the last line)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return "".join("%d: %s\n" % (index, line) for index, line in enumerate(lines, 1))


def feature_of(path):
    """The doc's identity (v1's rule): the `<topic>` of `YYYY-MM-DD-<topic>.md`, else the name
    minus `-build-plan.md`, else the name minus `.md`."""
    base = os.path.basename(path)
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", base)
    if match:
        return match.group(1)
    if base.endswith("-build-plan.md"):
        return base[:-len("-build-plan.md")]
    return base[:-3] if base.endswith(".md") else base


def lane_name(row):
    """The raw copy's lane label (v1): a `gpt-*` row files as `gpt`, any other row as its id."""
    return "gpt" if row.startswith("gpt-") else row
