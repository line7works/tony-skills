"""Shared helpers for this core's Codex adapter tests (standard library only).

Helpers run as child processes from a temporary directory. `codex` is a stand-in script on a
private PATH that answers `--version` and nothing else: no test launches the real harness, reads a
live `~/.codex`, or makes a model call.
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
ROLLOUT = os.path.join(FIXTURES, "real-rollout.jsonl")
THREAD = "01a0a1be-7b64-7383-9974-3e586fec7fb3"
WORKSPACE = "/tmp/neutral-workspace"
SKILL_ROOT = os.path.dirname(os.path.dirname(ADAPTER))
CORE = os.path.basename(SKILL_ROOT)
PREFIX = re.sub(r"[^A-Z0-9]", "_", CORE.upper())
TEST_FLAG = PREFIX + "_ADAPTER_TEST"
RECORD_VAR = PREFIX + "_ADAPTER_RECORD"
SCHEMA = os.path.join(SKILL_ROOT, "references", "input.schema.json")
FAKE_VERSION = "0.155.1"
AMBIENT = ("CODEX_THREAD_ID", "CODEX_HOME", "CODEX_SANDBOX", "RECHECK_HARNESS_SANDBOX",
           "RECHECK_WALL_PROBE", PREFIX + "_ADAPTER_CANNED")


def fake_bin(parent, with_codex=True):
    path = os.path.join(parent, "bin")
    os.makedirs(path, exist_ok=True)
    if with_codex:
        script = os.path.join(path, "codex")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\n[ \"$1\" = \"--version\" ] && echo 'codex-cli %s' && exit 0\n"
                         "echo 'stand-in codex: only --version' >&2; exit 64\n" % FAKE_VERSION)
        os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR)
    return path


def env_for(work, with_codex=True, extra=None):
    environment = dict(os.environ)
    for name in AMBIENT:
        environment.pop(name, None)
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", TEST_FLAG: "1", RECORD_VAR: ROLLOUT,
                        "TMPDIR": work,
                        "PATH": fake_bin(work, with_codex) + os.pathsep + "/usr/bin:/bin"})
    for key, value in (extra or {}).items():
        if value is None:
            environment.pop(key, None)
        else:
            environment[key] = value
    return environment


def run(helper, args, env=None, cwd=None, with_codex=True, adapter=None):
    work = tempfile.mkdtemp(prefix="adapter-codex-")
    try:
        proc = subprocess.run([sys.executable, os.path.join(adapter or ADAPTER, helper)]
                              + list(args), cwd=cwd or work, env=env_for(work, with_codex, env),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_json(helper, args, env=None, cwd=None, adapter=None):
    code, out, err = run(helper, args, env=env, cwd=cwd, adapter=adapter)
    if code != 0:
        raise AssertionError("%s exited %d: %s" % (helper, code, err.strip()))
    return json.loads(out)


def records(path=None):
    with open(path or ROLLOUT, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_records(directory, rows, name="rollout.jsonl"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


def installed_copy(parent):
    """This adapter folder copied into a fake installed plugin cache under `parent/home`.

    Returns (home, adapter directory in the copy). The skill root above it is not copied: the
    helpers read nothing of it, and E9-40 derives the home from the helper's own path.
    """
    home = os.path.join(parent, "home")
    adapter = os.path.join(home, "plugins", "cache", "fake-market", CORE, "0.1.0", "skills", CORE,
                           "adapters", "codex")
    shutil.copytree(ADAPTER, adapter, ignore=shutil.ignore_patterns("tests", "__pycache__"))
    return home, adapter


def plant_rollout(home, thread=THREAD, rows=None, read_only=True):
    folder = os.path.join(home, "sessions", "2026", "09", "23")
    os.makedirs(folder, exist_ok=True)
    path = write_records(folder, rows or records(), "rollout-2026-09-23T00-00-00-%s.jsonl" % thread)
    if read_only:
        os.chmod(path, 0o444)
    return path


def validate(document, schema_path=SCHEMA):
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
