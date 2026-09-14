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
    """Run one helper and return (returncode, stdout, stderr)."""
    environment = dict(os.environ)
    environment.pop("CLAUDE_CODE_SESSION_ID", None)
    environment.pop("RECHECK_ADAPTER_CANNED", None)
    environment.pop("RECHECK_ADAPTER_TEST", None)
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
