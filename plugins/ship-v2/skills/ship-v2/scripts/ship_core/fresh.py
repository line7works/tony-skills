"""The signoff visit in a fresh session (E18 slice C; contract sections 3.4, 4 and 11).

On the Claude Code harness, `visit --station signoff-v2` keeps everything it does and also makes the visit's launch
(`make`): a fresh random session id (a UUID), recorded in the visit's state in `ship.json` (`visit.launch`); the child
session's brief, composed here from this run's own files and nothing else (`brief`) and staged under this run's
directory, outside the visit's run directory and outside the workspace, through `common.stage_text`, so THE SAVE
writes it and `report` lists it; and the `launch_step` the visit prints, naming the adapter helper
(`adapters/claude-code/launch.py`) that prints the launch and, after the child ends, its check reading. No command
option takes free text for the brief, so nothing from the ship session's conversation can reach it. The core launches
nothing and reads no transcript: the reading is a file the ship session gets from the helper and hands over (`visit
--result --reading FILE`), the trust shape of the hook reading, so the core stays harness-blind. On Codex nothing
changes: no launch, no `launch_step`.

With the clock fixed for a test (`SHIP_V2_TEST_NOW` under `SHIP_V2_TEST=1`) the session id is derived from the visit's
run id, its run directory and that instant (a name-based UUID), so a test run stays byte for byte reproducible, as
everything else it writes is; otherwise it is `uuid4`.

`problems(run, visit, reading_path)`: why `visit --result` refuses a launched visit's result (exit 5, nothing
written, the run still `visiting`), or []. The reading must be the helper's check reading for this launch (kind
`launch_check`, this run's harness, the recorded session id, the launch prompt's sha256) and hold; and the reviewing
session the visit's own `input.json` records (`invocation.sessions.reviewing`, written by signoff-v2's `check-input`)
must be the recorded id. Each problem names what failed and both ids. With no reading (`report` at `visiting` given
none) only the reviewing session is held.

`child_said(run, visit)`: the child's `subtype` and `result` from its standard-output file, when that file holds them,
for the reason of a run that ends `visit-unfinished`.
"""
import hashlib
import json
import os
import stat
import uuid

from station_core import fsio, validate

from . import common

HARNESS = "claude-code"
STATION = "signoff-v2"
KIND = "launch_check"
HELPER = ("adapters", "claude-code", "launch.py")
READING_KEYS = ("reading_version", "kind", "harness", "session_id", "prompt_sha256", "holds", "how", "transcript")


def applies(run, name):
    """Whether a visit to `name` on this run is launched in a fresh session: signoff-v2 on Claude Code."""
    return name == STATION and common.harness(run) == HARNESS


def launched(visit):
    return isinstance(visit, dict) and isinstance(visit.get("launch"), dict)


def session_id(visit_run_id, visit_run_dir, environ=None):
    """A fresh random session id (module docstring: a name-based one with a test's fixed clock)."""
    environ = os.environ if environ is None else environ
    if common.test_mode(environ) and environ.get(common.PREFIX + "_TEST_NOW"):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "ship-v2:%s:%s:%s" % (visit_run_id, visit_run_dir,
                                                                        common.now(environ))))
    return str(uuid.uuid4())


def _build_result(state):
    rows = [v for v in state.get("visits") or [] if v.get("station") == "build-v2"]
    return rows[-1]["result"] if rows else None


def fields(run, state, visit, mode):
    """The brief's fields, in order, each (label, value): this run's own files and nothing else."""
    identity = visit["identity"] or {}
    out = [("Workspace", common.workspace(run)),
           ("Build doc", state["doc"]),
           ("Slice", state["slice"]),
           ("Build result", _build_result(state)),
           ("Run id", visit["run_id"]),
           ("Run directory", visit["run_dir"]),
           ("invocation.caller", common.STATION),
           ("invocation.mode", mode),
           ("signoff-v2 SKILL.md", visit["skill_md"]),
           ("signoff-v2 name", identity.get("name")),
           ("signoff-v2 version", identity.get("version")),
           ("signoff-v2 content hash", identity.get("content_sha256"))]
    if common.report_only(run):
        out.append(("Report only", "true"))
    depth = common.station(run).get("signoff_depth")
    if depth:
        out.append(("Depth", depth["depth"]))
    return out


def brief(run, state, visit, mode):
    """The child session's brief (module docstring), composed from this run's own files."""
    rows = fields(run, state, visit, mode)
    depth = common.station(run).get("signoff_depth")
    lines = ["# Signoff visit for ship-v2 run %s" % common.run_id(run), "",
             "ship-v2 launched this session to run one signoff-v2 visit. Run signoff-v2 by its own SKILL.md (the "
             "path below) on the slice below, with the run id, run directory and invocation fields below in its "
             "input, and its own rules governing the visit in full. Take the build result below as `--build-result` "
             "on its adapter's helper. Do nothing else.", "",
             "## The visit", ""]
    lines += ["- %s: %s" % (label, value) for label, value in rows]
    if depth:
        lines += ["", "## The owner's depth order", "",
                  "The owner ordered a DEEP signoff through ship-v2's input, which may carry DEEP and never LIGHT. "
                  "His words, verbatim, are the lines between the two markers:", "", "<<<", depth["words"], ">>>"]
    else:
        lines += ["", "## Depth", "",
                  "The owner gave no depth order: signoff-v2's own rules choose it (LEAN, or DEEP on its content "
                  "triggers). LIGHT never reaches this session through ship-v2."]
    if common.report_only(run):
        lines += ["", "## Report only", "",
                  "The ship run is report-only: run signoff-v2 report-only, writing nothing outside its run "
                  "directory."]
    lines += ["", "## No owner is present", "",
              "No owner is present in this session.", "",
              "- Do not take Step 1's first-run `REVIEW.md` write: it needs the owner's word.",
              "- Step 5's second-failure append stays signoff-v2's own, as its rules say.",
              "- Answer no question on the owner's behalf: a question signoff-v2 would put to the owner goes in "
              "your final message, unanswered.",
              "- End with the lines signoff-v2's Step 6 adds by hand in your final message: the questions rule 5 "
              "raised, the `Next:` line, and any `SKILL NOTE:`.",
              "- Commit nothing, push nothing, and edit nothing beyond signoff-v2's own writes."]
    return "\n".join(lines) + "\n"


def helper(ctx):
    """The adapter helper that prints the launch and the check reading, under this skill's own root."""
    return os.path.join(validate.skill_root(ctx.skill_root), *HELPER)


def check_argv(ctx, run):
    return ["python3", helper(ctx), "--run-dir", run.run_dir, "--check"]


def make(ctx, run, state, visit, mode, seq):
    """The visit's launch (module docstring): the session id, the brief staged, the record in the visit's state, and
    the `launch_step` the visit prints. `seq` is the number the visit's run directory carries (`visits/<seq>-<name>`),
    so the brief and the output file name the visit they belong to."""
    name = "brief-%d-%s.md" % (seq, STATION)
    brief_path = common.path_of(run, name)
    stdout = common.path_of(run, "child-%d-%s.json" % (seq, STATION))
    sid = session_id(visit["run_id"], visit["run_dir"])
    launch = {"session_id": sid, "brief": brief_path, "prompt": "Read %s and follow it." % brief_path,
              "stdout": stdout}
    visit["launch"] = launch
    common.stage_text(run, name, brief(run, state, visit, mode))
    path = helper(ctx)
    return {"helper": path,
            "launch": ["python3", path, "--run-dir", run.run_dir],
            "check": check_argv(ctx, run),
            "session_id": sid, "brief": brief_path, "stdout": stdout,
            "how": ("run `launch` and take its `launch` whole; run its argv in the background from its cwd (the "
                    "workspace) with no shell, standard output to %s, and wait for it to end; then run `check` into a "
                    "file and run `visit --result --reading <that file>`; never run signoff-v2 in this session, and "
                    "touch nothing while the visit is open" % stdout)}


def _reviewing(visit):
    """(the reviewing session the visit's own input.json records, or None; why it cannot be read, or None)."""
    folder = visit["run_dir"]
    path = os.path.join(folder, "input.json")
    try:
        mode = os.lstat(path).st_mode
    except OSError:
        return None, "the visit's input.json %s is not there" % path
    if not stat.S_ISREG(mode) or not fsio.inside(path, folder):
        return None, "the visit's input.json %s is not a regular file in the visit's run directory" % path
    try:
        doc = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        return None, "the visit's input.json %s cannot be read (%s)" % (path, exc)
    sessions = ((doc.get("invocation") if isinstance(doc, dict) else None) or {}).get("sessions")
    value = sessions.get("reviewing") if isinstance(sessions, dict) else None
    if not isinstance(value, str) or not value:
        return None, "the visit's input.json %s records no invocation.sessions.reviewing" % path
    return value, None


def _reading(run, launch, path):
    """[why the reading does not hold], or []: read from `path` (exit 2 when it is not there or not JSON)."""
    sid = launch["session_id"]
    doc = common.load_json_file(path, "check reading")
    wrong = sorted(set(doc) - set(READING_KEYS)) + ["no %s" % k for k in READING_KEYS if k not in doc]
    if wrong:
        return ["the check reading %s is not the launch helper's reading (%s)" % (path, ", ".join(wrong))]
    prompt_sha = hashlib.sha256(launch["prompt"].encode("utf-8")).hexdigest()
    out = []
    if doc["reading_version"] != 1 or doc["kind"] != KIND:
        out.append("the check reading %s is kind %r version %r, not the launch helper's %r version 1"
                   % (path, doc["kind"], doc["reading_version"], KIND))
    if doc["harness"] != common.harness(run):
        out.append("the check reading is %r's and this run is driven from %r" % (doc["harness"], common.harness(run)))
    if doc["session_id"] != sid:
        out.append("the check reading reads session %r, not the recorded session id %r" % (doc["session_id"], sid))
    if doc["prompt_sha256"] != prompt_sha:
        out.append("the check reading's prompt is not the launch's prompt (session %r, recorded %r)"
                   % (doc["session_id"], sid))
    if doc["holds"] is not True:
        out.append("the check reading does not hold (session %r, recorded %r): %s" % (doc["session_id"], sid,
                                                                                     doc["how"]))
    return out


def problems(run, visit, reading_path):
    """Why a launched visit's result is refused (module docstring), or []."""
    launch = visit["launch"]
    sid = launch["session_id"]
    out = _reading(run, launch, reading_path) if reading_path is not None else []
    reviewing, why = _reviewing(visit)
    if why is not None:
        out.append("%s, so its reviewing session cannot be held to the recorded session id %r" % (why, sid))
    elif reviewing != sid:
        out.append("the reviewing session the visit's input.json records is %r, not the recorded session id %r: "
                   "signoff-v2 did not run in the launched session" % (reviewing, sid))
    return out


def child_said(run, visit):
    """The child's `subtype` and `result` from its standard-output file, as words, or None."""
    if not launched(visit):
        return None
    path = visit["launch"]["stdout"]
    if common.irregular(run, path) is not None or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(doc, dict):
        return None
    said = ["%s %s" % (key, json.dumps(doc[key], ensure_ascii=False)) for key in ("subtype", "result") if key in doc]
    if not said:
        return None
    return "the launched session's standard output (%s) says: %s" % (path, "; ".join(said))
