"""Shared helpers for this core's Claude Code adapter tests (standard library only).

Every helper runs as a child process from a temporary working directory outside the worktree, so
nothing depends on where the suite was started. `claude` is a stand-in script on a private PATH:
the suite never launches the real harness, never reads a live `~/.claude`, and makes no model call.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.dirname(TESTS)
FIXTURES = os.path.join(TESTS, "fixtures")
TRANSCRIPT = os.path.join(FIXTURES, "session-transcript.jsonl")
SESSION = "4cd53208-8cb8-4de2-bb71-be7594182bb1"
SKILL_ROOT = os.path.dirname(os.path.dirname(ADAPTER))
CORE = os.path.basename(SKILL_ROOT)
PREFIX = re.sub(r"[^A-Z0-9]", "_", CORE.upper())
TEST_FLAG = PREFIX + "_ADAPTER_TEST"
SCHEMA = os.path.join(SKILL_ROOT, "references", "input.schema.json")
FAKE_VERSION = "2.1.280"
AMBIENT = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_ENTRYPOINT",
           "CLAUDE_CODE_PERMISSION_MODE", "CLAUDE_CONFIG_DIR", "CLAUDE_EFFORT",
           PREFIX + "_ADAPTER_CANNED")


def fake_bin(parent, with_claude=True):
    """A private PATH directory: a stand-in `claude` that answers `--version`, and nothing else."""
    path = os.path.join(parent, "bin")
    os.makedirs(path, exist_ok=True)
    if with_claude:
        script = os.path.join(path, "claude")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\n[ \"$1\" = \"--version\" ] && echo '%s (Claude Code)' && exit 0\n"
                         "echo 'stand-in claude: only --version' >&2; exit 64\n" % FAKE_VERSION)
        os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR)
    return path


def run(helper, args, env=None, cwd=None, with_claude=True):
    """(exit, stdout, stderr) of one helper run from a temporary directory."""
    work = tempfile.mkdtemp(prefix="adapter-cc-")
    try:
        environment = dict(os.environ)
        for name in AMBIENT:
            environment.pop(name, None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment[TEST_FLAG] = "1"
        environment["PATH"] = fake_bin(work, with_claude) + os.pathsep + "/usr/bin:/bin"
        environment["TMPDIR"] = work
        for key, value in (env or {}).items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        proc = subprocess.run([sys.executable, os.path.join(ADAPTER, helper)] + list(args),
                              cwd=cwd or work, env=environment, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_json(helper, args, env=None, cwd=None):
    code, out, err = run(helper, args, env=env, cwd=cwd)
    if code != 0:
        raise AssertionError("%s exited %d: %s" % (helper, code, err.strip()))
    return json.loads(out)


def records(path=None):
    with open(path or TRANSCRIPT, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_records(directory, rows, name="session.jsonl"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


def validate(document, schema_path=SCHEMA):
    """[] when `document` validates against the schema, else the error messages.

    Runs jsonschema at the pin through `uv run`, so the check is the same under
    /usr/bin/python3 and under uv: the helpers themselves never import it.
    """
    work = tempfile.mkdtemp(prefix="adapter-schema-")
    try:
        doc = os.path.join(work, "doc.json")
        with open(doc, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        code = ("import json,sys,jsonschema\n"
                "s=json.load(open(sys.argv[1]));d=json.load(open(sys.argv[2]))\n"
                "v=jsonschema.Draft202012Validator(s)\n"
                "print(json.dumps([e.message for e in v.iter_errors(d)]))\n")
        proc = subprocess.run(["uv", "run", "--quiet", "--no-project", "--python", "/usr/bin/python3",
                               "--with", "jsonschema==4.25.1", "python3", "-c", code, schema_path,
                               doc], cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if proc.returncode != 0:
            raise AssertionError("schema check could not run: %s" % proc.stderr.decode()[-400:])
        return json.loads(proc.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def fixture_args(path=None):
    return ["--transcript", path or TRANSCRIPT]
