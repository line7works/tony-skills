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
    fixed        the lap's fixes recorded            -> visit --station recheck-v2 (after the save step); report
                                                        when the save step was not taken (`recheck-stopped`)
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

THE SAVE (the E15 lane contract A29 (1); contract section 3.10): one routine, `save`, writes the run's state and its
checkpoint, and with them everything else the command writes into its run directory (its trace lines, `pauses.json`,
`laps.json`, `fixes.json`, `events.json`, a receipt finished, `chat.md`, `result.json`), as one transaction. A command
stages what it writes (`stage`, `stage_text`, `stage_trace`; `read`, `listing` and `state` see the staged bytes at
once) and `save` writes it all: first the journal `save.json`, replaced whole by one rename, naming each file, the
sha256 of the bytes it holds now (or none), the bytes it will hold and their sha256, with the journal's own sha256;
then each file replaced whole (`put`: a temporary file beside it, then a rename), `ship.json` and `checkpoint.json`
last; then the journal removed. A kill before the journal lands leaves the run as it was, so the command runs again
from the top; a kill after it leaves the journal. Before any command reads anything of the run (`open_run`, then
`recover`), a journal left by a kill is finished when every file it names holds the bytes it held before the save or
the bytes the save was writing (both this run's), and the run goes on from the stage the save wrote; a file at any
other bytes, or a journal whose own sha256, version or run id does not hold, is the run directory changed by hand, and
the run refuses (exit 1) with nothing written. A temporary file a cut-off `put` left (`.<name>.ship-v2-tmp`) is
removed first. `ship.json` stays held to the sha256 its checkpoint recorded (`state`), so a hand edit after a clean
save refuses as before. A grant's own transaction (its receipt, the records append and the `Status:` line, `grant.py`)
keeps its own crash rules; its receipt writes go through `put` as they happen, and its finished receipt is staged.
"""
import copy
import datetime
import json
import os
import re
import stat
import sys

from station_core import driver, fsio, validate
from back_core import trace

STATION = "ship-v2"
PREFIX = "SHIP_V2"
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STATIONS = ("build-v2", "signoff-v2", "recheck-v2")
STATE = "ship.json"
CHECKPOINT = "checkpoint.json"
JOURNAL = "save.json"
TEMP = ".ship-v2-tmp"
SHA = re.compile(r"^[0-9a-f]{64}$")
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
    """The run, an interrupted save finished first (`recover`), at one of `stages`, or exit 2 naming the command to run
    instead."""
    run = ctx.open_run(run_dir)
    recover(run)
    stage = run.checkpoint.get("phase")
    if stage not in stages:
        raise driver.Usage("this run is at stage %r: `%s` runs at %s; run `%s` instead"
                           % (stage, command, " or ".join(repr(s) for s in stages), NEXT.get(stage, "check-input")))
    return run


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
    return name in _staged(run) or os.path.lexists(path_of(run, name))


def read(run, name):
    if name in _staged(run):
        return copy.deepcopy(run.staged[name])
    why = irregular(run, path_of(run, name))
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run directory has been changed by hand, and the run "
                            "refuses; nothing was opened and nothing was written" % (name, why))
    try:
        return fsio.read_json(path_of(run, name))
    except (OSError, ValueError) as exc:
        raise driver.Defect("the run artifact %s cannot be read: %s" % (name, exc))


def write(run, name, doc):
    """A run file written at once, through `put` (a grant's receipt, its transaction's own record: `grant.py`)."""
    why = irregular(run, path_of(run, name))
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run refuses to write over it" % (name, why))
    put(path_of(run, name), _bytes(doc))
    return path_of(run, name)


def state(run):
    """`ship.json`, held to the hash the checkpoint recorded when the run last saved it: a hand edit of the run's
    state (its lap counter, its pin, its named findings) is detected and refused, never acted on. A state this command
    staged is read as staged."""
    if STATE in _staged(run):
        return copy.deepcopy(run.staged[STATE])
    if not has(run, STATE):
        return {}
    why = irregular(run, path_of(run, STATE))
    if why is None and fsio.sha256_file(path_of(run, STATE)) != run.checkpoint.get("state_sha256"):
        why = "does not hold the bytes this run last saved (the checkpoint's state_sha256)"
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run directory has been changed by hand, and the run refuses; "
                            "nothing was written" % (STATE, why))
    return read(run, STATE)


# ---- THE SAVE (module docstring) ------------------------------------------------------------------------------------

def _staged(run):
    if not hasattr(run, "staged"):
        run.staged = {}
        run.staged_trace = []
    return run.staged


def _bytes(doc):
    return doc.encode("utf-8") if isinstance(doc, str) else fsio.dumps(doc).encode("utf-8")


def _stageable(run, name):
    why = irregular(run, path_of(run, name))
    if why is not None:
        raise driver.Defect("the run artifact %s %s: the run refuses to write over it" % (name, why))


def stage(run, name, doc):
    """A JSON run file this command writes, held until `save`."""
    _stageable(run, name)
    _staged(run)[name] = copy.deepcopy(doc)


def stage_text(run, name, text):
    """A text run file this command writes, held until `save`."""
    _stageable(run, name)
    _staged(run)[name] = text


def staged_bytes(run):
    """{name: the bytes `save` will write} for every run file staged so far (`report` lists them in its writes)."""
    return dict((name, _bytes(doc)) for name, doc in _staged(run).items())


def trace_line_bytes(numbered):
    """One numbered trace line as `trace.append` writes it."""
    return (json.dumps(numbered, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _numbered(one, seq, skill_root, prefix):
    """`one` numbered `seq` and checked as `trace.append` checks it (its shape rules, then the schema)."""
    problems = trace.check_line(one)
    if problems:
        raise trace.TraceError("the trace line does not hold: %s" % "; ".join(problems))
    numbered = dict(one, seq=seq)
    errors = trace.schema_errors(numbered, skill_root, prefix)
    if errors:
        raise trace.TraceError("the trace line fails references/trace.schema.json: %s"
                               % "; ".join("%s %s" % (e["path"], e["message"]) for e in errors[:4]))
    return numbered


def trace_bytes(run_dir, lines, skill_root=None, prefix="TRACE"):
    """The trace file's bytes with `lines` appended, each numbered and checked as `trace.append` does it."""
    have = len(trace.read(run_dir))
    path = trace.path_of(run_dir)
    old = b""
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            old = fh.read()
    return old + b"".join(trace_line_bytes(_numbered(one, have + index, skill_root, prefix))
                          for index, one in enumerate(lines))


def stage_trace(run, line, skill_root=None, prefix="TRACE"):
    """One trace line this command writes, numbered and checked now and held until `save`; returns it numbered."""
    _staged(run)
    numbered = _numbered(line, len(trace.read(run.run_dir)) + len(run.staged_trace), skill_root, prefix)
    run.staged_trace.append(numbered)
    return numbered


def temp_of(path):
    return os.path.join(os.path.dirname(path), "." + os.path.basename(path) + TEMP)


def clear_temp(tmp):
    """A temporary file a cut-off `put` left, removed; True when there was one. Anything but a regular file there is
    the run directory changed by hand."""
    try:
        mode = os.lstat(tmp).st_mode
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(mode):
        raise driver.Defect("%s is not a regular file: it has been changed by hand, and the run refuses; nothing was "
                            "written" % tmp)
    os.remove(tmp)
    return True


def put(path, data):
    """`data` (bytes) into `path`, replaced whole: written to `temp_of(path)` first, then renamed over `path`, so a
    kill leaves the old bytes or the new, never a part; a temporary file a cut-off put left is cleared first."""
    tmp = temp_of(path)
    clear_temp(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.lexists(tmp):
            os.remove(tmp)
        raise


def drop(path):
    """The journal removed, once every file it names holds the bytes its save was writing."""
    os.remove(path)


def _journal_sha(body):
    return fsio.sha256_bytes(fsio.canonical_json(body).encode("utf-8"))


def _by_hand(name, why):
    return ("the run artifact %s %s: the run directory has been changed by hand, and the run refuses; nothing was "
            "written" % (name, why))


def _apply(run, rows):
    """Each file of a save replaced by the bytes the save writes, unless it holds them already; a file at bytes that
    are neither its bytes before the save nor the save's is the run directory changed by hand."""
    for row in rows:
        path = path_of(run, row["name"])
        why = irregular(run, path)
        if why is not None:
            raise driver.Defect(_by_hand(row["name"], why))
        now = fsio.sha256_file_or_none(path)
        if now == row["after"]:
            continue
        if now != row["before"]:
            raise driver.Defect(_by_hand(row["name"], "holds neither the bytes it held before the save a kill "
                                                      "interrupted nor the bytes that save was writing"))
        put(path, row["text"].encode("utf-8"))


def save(run, state=None, stage=None):
    """THE SAVE (module docstring): everything this command staged, `state` as `ship.json` and `stage` as the
    checkpoint's phase, in one transaction. Every write of the run's state and its checkpoint goes through here."""
    staged = _staged(run)
    if state is not None:
        staged[STATE] = copy.deepcopy(state)
    checkpoint = dict(run.checkpoint)
    if stage is not None:
        checkpoint["phase"] = stage
    writes = [(name, _bytes(staged[name])) for name in sorted(staged) if name not in (STATE, CHECKPOINT, JOURNAL)]
    if run.staged_trace:
        writes.append((trace.FILE, trace_bytes(run.run_dir, []) + b"".join(trace_line_bytes(one)
                                                                            for one in run.staged_trace)))
    if STATE in staged:
        data = _bytes(staged[STATE])
        writes.append((STATE, data))
        checkpoint["state_sha256"] = fsio.sha256_bytes(data)
    writes.append((CHECKPOINT, _bytes(checkpoint)))
    rows = []
    for name, data in writes:
        _stageable(run, name)
        rows.append({"name": name, "before": fsio.sha256_file_or_none(path_of(run, name)),
                     "after": fsio.sha256_bytes(data), "text": data.decode("utf-8")})
    journal = path_of(run, JOURNAL)
    if os.path.lexists(journal):
        raise driver.Defect(_by_hand(JOURNAL, "is there before this save began"))
    body = {"journal_version": 1, "run_id": run.checkpoint.get("run_id"), "writes": rows}
    put(journal, _bytes(dict(body, sha256=_journal_sha(body))))
    _apply(run, rows)
    drop(journal)
    run.checkpoint = checkpoint
    run.staged, run.staged_trace = {}, []


def _rows_hold(run, rows):
    """Whether a journal's rows are a save of this run: plain names in the run directory, hashes of 64 hex characters,
    each text at its own `after`, and a checkpoint for this run and its input."""
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, dict) or sorted(row) != ["after", "before", "name", "text"]:
            return False
        name, text = row["name"], row["text"]
        if not isinstance(name, str) or not name or os.sep in name or name.startswith(".") or name == JOURNAL:
            return False
        if row["before"] is not None and not (isinstance(row["before"], str) and SHA.match(row["before"])):
            return False
        if not isinstance(text, str) or fsio.sha256_bytes(text.encode("utf-8")) != row["after"]:
            return False
        if name == CHECKPOINT:
            try:
                doc = json.loads(text)
            except ValueError:
                return False
            if not isinstance(doc, dict) or doc.get("run_id") != run.checkpoint.get("run_id") or \
                    doc.get("input_sha256") != run.checkpoint.get("input_sha256"):
                return False
    return rows[-1]["name"] == CHECKPOINT


def recover(run):
    """THE SAVE's other half (module docstring), before a command reads anything of the run: a cut-off `put`'s
    temporary file removed; a journal a kill left finished, or refused as the run directory changed by hand. True
    when a save was finished."""
    for name in sorted(os.listdir(run.run_dir)):
        if name.startswith(".") and name.endswith(TEMP):
            clear_temp(path_of(run, name))
    journal = path_of(run, JOURNAL)
    if not os.path.lexists(journal):
        return False
    why = irregular(run, journal)
    if why is not None:
        raise driver.Defect(_by_hand(JOURNAL, why))
    try:
        doc = fsio.read_json(journal)
    except (OSError, ValueError) as exc:
        raise driver.Defect(_by_hand(JOURNAL, "cannot be read (%s)" % exc))
    body = dict(doc) if isinstance(doc, dict) else {}
    claimed = body.pop("sha256", None)
    if claimed != _journal_sha(body) or body.get("journal_version") != 1 or \
            body.get("run_id") != run.checkpoint.get("run_id") or not _rows_hold(run, body.get("writes")):
        raise driver.Defect(_by_hand(JOURNAL, "is not a save this run began (its own sha256, its version, its run id "
                                              "or its rows do not hold)"))
    rows = body["writes"]
    for row in rows:
        path = path_of(run, row["name"])
        why = irregular(run, path)
        if why is not None:
            raise driver.Defect(_by_hand(row["name"], why))
        if fsio.sha256_file_or_none(path) not in (row["before"], row["after"]):
            raise driver.Defect(_by_hand(row["name"], "holds neither the bytes it held before the save a kill "
                                                      "interrupted nor the bytes that save was writing"))
    _apply(run, rows)
    drop(journal)
    run.checkpoint = fsio.read_json(path_of(run, CHECKPOINT))
    sys.stderr.write("ship-v2: a save a kill interrupted (%s) was finished first, from the bytes it was writing; the "
                     "run goes on from the stage %r\n" % (JOURNAL, run.checkpoint.get("phase")))
    return True


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
