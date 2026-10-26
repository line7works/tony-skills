#!/usr/bin/env python3
"""The signoff visit's launch on Claude Code, and its check reading (E18 slice C; the profile's section 7).

`visit --station signoff-v2` on Claude Code records a fresh session id and stages the child session's brief under
this ship run's directory, and prints a `launch_step` naming this helper. Given that run directory, this helper:

- (launch mode) finds the ship session's own transcript from the ship input's `invocation.session_id`, the way
  `invocation.py` finds a session's transcript (`<config>/projects/*/<id>.jsonl`, every turn record bound to that id,
  ruling E9-28), reads from it the model id and the effort (the values `invocation.py` reports as
  `measurement.model_id` and `measurement.effort`), and prints `launch`: the argv, the working directory (the
  workspace), the recorded session id and the file under this ship run's directory that receives the child's
  standard output. The argv is a list, run with no shell. `--effort` and its value are left out when the transcript
  records none, or a value `claude --effort` does not take (`EFFORTS`), so the child then runs at the harness
  default effort. `--settings` carries the memory-off object as one element, with no shell quotes in it (a quoted
  element reads as a settings file path). A transcript with no model, or a model below the Opus floor by
  `_common.floor_for`, prints no launch and exits 3, naming why.
- (`--check`, after the child ended) finds the child's transcript (the recorded session id's record, found the same
  way and bound to the workspace as its cwd) and prints the reading `visit --result --reading FILE` takes: it holds
  only when that record exists and its first prompt is exactly the launch's prompt.

The ship session runs the argv in the background from the workspace, standard output to the named file, and waits
for it to end; this helper launches nothing, reads no network and writes nothing.

Exit 0 success, 2 usage (no launch recorded in the run directory), 3 a harness record this helper needs is missing or
refused (the ship session's transcript, its model, the floor), 1 anything else. stdout carries one JSON document and
nothing else; diagnostics go to stderr. Python 3.9, standard library only.
"""

import hashlib
import json
import os
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402
from hook import typed_text  # noqa: E402

EFFORTS = ("low", "medium", "high", "xhigh", "max")
SETTINGS = json.dumps({"autoMemoryEnabled": False}, separators=(",", ":"))
BANNED = ("bypassPermissions", "--dangerously-skip-permissions", "--bare")
KIND = "launch_check"
EPILOG = """\
Given a ship-v2 run directory whose open visit is a signoff-v2 visit launched on Claude Code (`visit --station
signoff-v2` recorded its session id and staged its brief), prints the launch: the argv (run with no shell), the
working directory, the recorded session id and the standard-output file. With --check, after the child ended, prints
the check reading for `visit --result --reading FILE`.

The model id and the effort come from the ship session's own transcript, found from the ship input's
invocation.session_id; the Opus floor is _common.floor_for's.

Exit 0 success, 2 usage, 3 a harness record is missing or refused, 1 anything else.

Example:
  launch.py --run-dir /tmp/ship-run > launch.json
  launch.py --run-dir /tmp/ship-run --check > check.json

Side effects: none. Nothing is written, no network, no model call, no process started.
"""


def _regular(path, what):
    try:
        mode = os.lstat(path).st_mode
    except OSError:
        raise _common.HelperError("%s %s is not there" % (what, path), 2)
    if not stat.S_ISREG(mode):
        raise _common.HelperError("%s %s is not a regular file (a link, a folder or a pipe)" % (what, path), 2)
    with open(path, "rb") as handle:
        try:
            doc = json.loads(handle.read().decode("utf-8"))
        except ValueError as exc:
            raise _common.HelperError("%s %s is not JSON (%s)" % (what, path, exc), 2)
    if not isinstance(doc, dict):
        raise _common.HelperError("%s %s is not a JSON object" % (what, path), 2)
    return doc


def the_run(run_dir):
    """(ship input, the open visit's launch) from the ship run directory, or exit 2 naming what is missing."""
    run_dir = os.path.abspath(run_dir)
    ship_input = _regular(os.path.join(run_dir, "input.json"), "the ship input")
    state = _regular(os.path.join(run_dir, "ship.json"), "the ship run's state")
    visit = state.get("visit")
    launch = visit.get("launch") if isinstance(visit, dict) else None
    if not isinstance(launch, dict) or visit.get("station") != "signoff-v2":
        raise _common.HelperError(
            "the run at %s has no open signoff-v2 visit with a launch recorded: run `ship.py visit --run-dir %s "
            "--station signoff-v2` on Claude Code first" % (run_dir, run_dir), 2)
    for key in ("session_id", "brief", "prompt", "stdout"):
        if not isinstance(launch.get(key), str) or not launch[key]:
            raise _common.HelperError("the visit's launch in %s carries no %s" % (run_dir, key), 2)
    return ship_input, launch


def find(cfg, session_id, workspace):
    """The transcript named for `session_id` under `<cfg>/projects`, the way `invocation.py` finds one; exit 3 when it
    is absent or ambiguous, or holds another session's records."""
    hits = _common._transcript_hits(cfg, session_id, workspace)
    if not hits:
        raise _common.HelperError("no transcript named %s.jsonl exists under %s/projects" % (session_id, cfg), 3)
    if len(hits) > 1:
        raise _common.HelperError("%d transcripts under %s/projects are named for session %s (%s); the discovery is "
                                  "ambiguous" % (len(hits), cfg, session_id, ", ".join(hits)), 3)
    path = hits[0]
    if not _common._bind_session(path, session_id):
        raise _common.HelperError("unusable session record: no user or assistant turns in %s (ruling E9-29)" % path,
                                  3)
    return path


def launch(args):
    ship_input, recorded = the_run(args.run_dir)
    invocation = ship_input.get("invocation") if isinstance(ship_input.get("invocation"), dict) else {}
    ship_session = invocation.get("session_id")
    workspace = ship_input.get("workspace")
    if not ship_session:
        raise _common.HelperError("the ship input carries no invocation.session_id, so the ship session's own "
                                  "transcript cannot be found", 3)
    cfg = _common.config_dir(args.config_dir)
    path = find(cfg, ship_session, workspace)
    session = _common.read_session(path)
    model = session["models"][-1] if session["models"] else None
    if not model:
        raise _common.HelperError("the ship session's transcript %s records no model (no non-sidechain, "
                                  "non-synthetic assistant record carries message.model), so no launch is printed"
                                  % path, 3)
    klass, met = _common.floor_for(model, "opus")
    if met is not True:
        raise _common.HelperError("the ship session runs %r, class %r: below the Opus floor (_common.floor_for), so "
                                  "no launch is printed" % (model, klass), 3)
    effort = session["efforts"][-1] if session["efforts"] else None
    argv = ["claude", "-p", "--model", model]
    if effort in EFFORTS:
        argv += ["--effort", effort]
    argv += ["--permission-mode", "auto", "--session-id", recorded["session_id"], "--settings", SETTINGS,
             "--output-format", "json", recorded["prompt"]]
    banned = [word for word in BANNED for item in argv if word in item]
    if banned:
        raise _common.HelperError("the launch would carry %s, which it never carries" % ", ".join(banned), 1)
    return {
        "launch": {"argv": argv, "cwd": workspace, "session_id": recorded["session_id"],
                   "stdout": recorded["stdout"]},
        "measurement": {
            "transcript": path,
            "model_id": model,
            "floor_class": klass,
            "effort": effort,
            "effort_passed": effort in EFFORTS,
            "_sources": {
                "session": "the ship input's invocation.session_id, resolved under %s/projects and bound to that "
                           "session's records (ruling E9-28)" % cfg,
                "model_id": "the last non-sidechain, non-synthetic assistant record's message.model in %s" % path,
                "effort": "the last assistant record's effort in %s; passed only when claude --effort takes it (%s)"
                          % (path, ", ".join(EFFORTS)),
            },
        },
    }


def first_prompt(path, session_id):
    """The first prompt typed in the record (a user record of this session, its content text, no tool result), or
    None."""
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("sessionId") != session_id:
                continue
            text = typed_text(record)
            if text is not None:
                return text
    return None


def check(args):
    ship_input, recorded = the_run(args.run_dir)
    child, prompt = recorded["session_id"], recorded["prompt"]
    workspace = ship_input.get("workspace")
    cfg = _common.config_dir(args.config_dir)
    reading = {"reading_version": 1, "kind": KIND, "harness": _common.HARNESS, "session_id": child,
               "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "holds": False, "how": None,
               "transcript": None}
    try:
        path = find(cfg, child, workspace)
        binding = _common._bind_workspace(path, workspace)
    except _common.HelperError as exc:
        reading["how"] = "the launched session's record cannot be read: %s" % exc
        return reading
    reading["transcript"] = path
    said = first_prompt(path, child)
    if said is None:
        reading["how"] = "the launched session's record %s holds no prompt" % path
    elif said != prompt:
        reading["how"] = ("the launched session's record %s opens with another prompt (%d characters), not the "
                          "launch's prompt" % (path, len(said)))
    else:
        reading["holds"] = True
        reading["how"] = ("the launched session's record %s exists, is bound to session %s (%s), and its first prompt "
                          "is exactly the launch's prompt" % (path, child, binding))
    return reading


def main():
    parser = _common.JsonParser(prog="launch.py", epilog=EPILOG,
                                description="The signoff visit's launch on Claude Code, and its check reading.",
                                formatter_class=__import__("argparse").RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True, help="the ship-v2 run directory whose signoff visit is open")
    parser.add_argument("--check", action="store_true", default=False,
                        help="after the child ended: print the check reading instead of the launch")
    parser.add_argument("--config-dir", default=None, help="the Claude Code config directory (default: "
                                                           "$CLAUDE_CONFIG_DIR, else ~/.claude)")
    args = parser.parse_args()
    return check(args) if args.check else launch(args)


if __name__ == "__main__":
    sys.exit(_common.run("launch.py", main))
