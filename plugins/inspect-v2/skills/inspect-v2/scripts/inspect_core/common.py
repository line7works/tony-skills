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


VARIANT = re.compile(r"^-(?:[2-9]|[1-9][0-9]+)$")


def raw_variant(path, want):
    """Whether `path` is a member of readers' same-day family of the request's `raw_path` `want`:
    `want` itself, or readers' `-2`, `-3`, ... `-10`, `-11`, ... variant of it (round 4, R1)."""
    if path == want:
        return True
    base, ext = os.path.splitext(want)
    if not (path.startswith(base) and path.endswith(ext)) or len(path) <= len(base) + len(ext):
        return False
    return VARIANT.match(path[len(base):len(path) - len(ext)]) is not None


def _member_number(path, want):
    base, ext = os.path.splitext(want)
    return 1 if path == want else int(path[len(base) + 1:len(path) - len(ext)])


def _variants(want):
    """Every existing `-N` variant of `want` in its folder, in readers' filing order."""
    folder = os.path.dirname(want)
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    found = [os.path.join(folder, n) for n in names
             if os.path.join(folder, n) != want and raw_variant(os.path.join(folder, n), want)]
    return sorted(found, key=lambda p: _member_number(p, want))


def raw_families(run, ws):
    """Per outside call whose request named a `raw_path` (recorded at `request`): the request's path,
    the existing members of its same-day family (the path itself and every `-N` variant readers may
    have filed on a same-day repeat, each a plain file under `docs/reviews/`), and the path the result
    names, if any, as an absolute path. The members never depend on what the result names (round 4,
    R1); an answer not yet recorded names nothing."""
    reviews = os.path.join(ws, "docs", "reviews")
    answer = read(run, "answer.json") if has(run, "answer.json") else {}
    named = dict((r.get("call_id"), r.get("raw_path")) for r in answer.get("results") or [])
    out = []
    for call in read(run, "requests.json")["calls"] if has(run, "requests.json") else []:
        want = call.get("raw_path")
        if not want:
            continue
        members = [p for p in [want] + _variants(want)
                   if os.path.isfile(p) and not os.path.islink(p) and fsio.inside(p, reviews)]
        given = named.get(call["call_id"])
        if given:
            given = os.path.normpath(given if os.path.isabs(given) else os.path.join(ws, given))
        out.append({"call_id": call["call_id"], "raw_path": want, "members": members, "named": given})
    return out


def raw_copies(run, ws):
    """Every raw copy the banner goes on (round 4, R1; `writing._raw_copies` states the rule): each
    outside request's own `raw_path` and every existing variant of it, whatever the result names. The
    banner is idempotent, so a copy an earlier run bannered is left as it is."""
    out = []
    for family in raw_families(run, ws):
        for path in family["members"]:
            if path not in out:
                out.append(path)
    return out
