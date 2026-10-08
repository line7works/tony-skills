"""The run, its phases, the clock and the artifacts (vertical-v2's own; contract section 3)."""
import datetime
import json
import os
import re
import stat

from station_core import driver, fsio, validate
from back_core import trace

STATION = "vertical-v2"
PREFIX = "VERTICAL_V2"
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ANTHROPIC = "anthropic"
SIGNED_OFF = "signed off"
CARDS = ("not started", "built", "rejected", "signed off with conditions", "signed off")

# the command to run next from each checkpoint phase (a wrong-phase command names it, exit 2)
NEXT = {"checked": "gate", "gated": "ask", "asking": "ask --answer", "asked": "scope", "scoped": "request",
        "requested-local": "record-local", "recorded-local": "request --outside, or verdict when no outside row "
        "was named", "requested-outside": "record-outside", "recorded-outside": "verdict", "verdict-written": "report",
        "done": "nothing: the run is over"}


def test_mode(environ=None):
    environ = os.environ if environ is None else environ
    return environ.get(PREFIX + "_TEST") == "1"


def now(environ=None):
    """The UTC instant this run writes. `VERTICAL_V2_TEST_NOW` fixes it, honored only with `VERTICAL_V2_TEST=1`."""
    environ = os.environ if environ is None else environ
    fixed = environ.get(PREFIX + "_TEST_NOW")
    if test_mode(environ) and fixed:
        if not INSTANT.match(fixed):
            raise driver.Usage("%s_TEST_NOW is %r, not an instant like 2026-10-01T12:00:00Z" % (PREFIX, fixed))
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


def advance(run, phase):
    run.checkpoint["phase"] = phase
    run.save()


def path_of(run, name):
    return os.path.join(run.run_dir, name)


def present(path):
    """Whether anything is at `path`, a link (even a dangling one) included."""
    return os.path.lexists(path)


def irregular(run, path):
    """Why the run file at `path` must not be opened, or None (A12, C1A7-2; contract section 3, "The run files"):
    checked with `os.lstat` before anything opens the path, so a named pipe never hangs a phase. A path with
    nothing at it is None here; each caller says what its absence means."""
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


def check_file(run, path, name):
    """The run's refusal for a damaged run directory (exit 1), before anything opens `path`, when it is irregular."""
    why = irregular(run, path)
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run directory has been changed by hand, and the run "
                            "refuses; nothing was opened and nothing was written" % (name, why))


def has(run, name):
    """Whether the run holds the artifact; anything at its path counts, so a planted pipe or link is refused by
    `read`, never read as absent."""
    return present(path_of(run, name))


def read(run, name):
    check_file(run, path_of(run, name), name)
    try:
        return fsio.read_json(path_of(run, name))
    except (OSError, ValueError) as exc:
        raise driver.Defect("the run artifact %s cannot be read: %s" % (name, exc))


def check_trace(run):
    """`trace.jsonl` checked before the trace module (a back-frame file) reads it or appends to it."""
    check_file(run, trace.path_of(run.run_dir), trace.FILE)


def write(run, name, doc):
    fsio.write_json(path_of(run, name), doc)
    return path_of(run, name)


def station(run):
    value = run.input.get("station")
    return value if isinstance(value, dict) else {}


def owner_words(run):
    value = station(run).get("owner_words")
    return value if isinstance(value, dict) else {}


def workspace(run):
    return run.input["workspace"]


def report_only(run):
    return bool(run.input.get("report_only"))


def harness(run):
    return (run.input.get("invocation") or {}).get("harness")


def plugin_root():
    """This core's plugin root: vertical_core -> scripts -> skills/vertical-v2 -> skills -> the plugin."""
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
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/%s (%s)" % (name, exc))


def feature_of(path):
    """The doc's identity (v1's rule): the `<topic>` of `YYYY-MM-DD-<topic>.md`, else the name minus
    `-build-plan.md`, else the name minus `.md`."""
    base = os.path.basename(path)
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", base)
    if match:
        return match.group(1)
    if base.endswith("-build-plan.md"):
        return base[:-len("-build-plan.md")]
    return base[:-3] if base.endswith(".md") else base


def date_of(run):
    """The verdict doc's date: the input's `station.date`, else today's UTC date from the run's clock."""
    return station(run).get("date") or now()[:10]


def blank(text):
    return not isinstance(text, str) or not text.strip()
