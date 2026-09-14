"""Shared helpers for the Claude Code adapter tests.

Every test runs the helpers as child processes from a temporary working
directory, so nothing depends on where the suite was started.
"""

import json
import os
import subprocess
import sys

ADAPTER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TRANSCRIPT = os.path.join(FIXTURES, "session-transcript.jsonl")
SKILL_ROOT = os.path.dirname(os.path.dirname(ADAPTER))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
RECHECK = os.path.join(SKILL_ROOT, "scripts", "recheck.py")


def run(helper, args, cwd=None, env=None):
    """Run one helper and return (returncode, stdout, stderr).

    `RECHECK_ADAPTER_TEST=1` is on by default because the suite drives the
    helpers through the fixture interface of ruling E9-28 (`--transcript`,
    `--session-id`); a test that means to exercise the run-time refusal passes
    `env={"RECHECK_ADAPTER_TEST": None}`.
    """
    environment = dict(os.environ)
    # The suite must answer the same from any session, so the ambient session's
    # own harness variables are dropped and each test supplies what it means to
    # measure; the fixture record decides the rest.
    for name in (
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_SESSION_ATTENDED",
        "CLAUDE_CODE_ENTRYPOINT",
        "RECHECK_ADAPTER_CANNED",
        "RECHECK_HARNESS_SANDBOX",
        "CLAUDE_CODE_PERMISSION_MODE",
    ):
        environment.pop(name, None)
    environment["RECHECK_ADAPTER_TEST"] = "1"
    if env:
        for key, value in env.items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
    process = subprocess.Popen(
        [sys.executable, os.path.join(ADAPTER, helper)] + list(args),
        cwd=cwd or os.path.join(os.sep, "tmp"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    out, err = process.communicate()
    return process.returncode, out.decode("utf-8"), err.decode("utf-8")


def run_json(helper, args, cwd=None, env=None):
    code, out, err = run(helper, args, cwd=cwd, env=env)
    if code != 0:
        raise AssertionError("%s exited %d: %s" % (helper, code, err.strip()))
    return json.loads(out)


def records(path=None):
    """The fixture transcript's records, for a test that mutates a copy."""
    with open(path or TRANSCRIPT, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_transcript(directory, rows, name="session.jsonl"):
    """Write records to <directory>/<name> and return the path."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


def uv_recheck(args):
    """Drive the core through `uv run recheck.py`, as SKILL.md does."""
    process = subprocess.Popen(
        ["uv", "run", RECHECK] + list(args),
        cwd=os.path.join(os.sep, "tmp"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    return process.returncode, out.decode("utf-8"), err.decode("utf-8")
