"""Shared paths and helpers for the front cores' script tests (standard library only).

This file is identical in precon-v2, architect-v2, blueprint-v2 and inspect-v2
(`references/shared-files.txt`). Every path derives from this file's location, so the suite runs
from any working directory and in any of the four cores:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s <this directory> -t <this directory>

Fixtures are built under a temporary directory (under `STATION_TEST_SCRATCH` when that names a
directory) and removed; nothing is written into the worktree.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(TESTS)
SKILL = os.path.dirname(SCRIPTS)
CORE = os.path.basename(SKILL)                         # precon-v2, architect-v2, ...
STATION = CORE.split("-")[0]                           # precon, architect, ...
PREFIX = re.sub(r"[^A-Z0-9]", "_", CORE.upper())       # PRECON_V2, ...
# The driver is scripts/<station>.py, except where that name would shadow a standard-library
# module on the scripts folder's own path: inspect.py would, so inspect-v2's is inspect_v2.py.
SHADOWED = ("inspect",)
DRIVER = os.path.join(SCRIPTS, "%s%s" % (STATION, "_v2.py" if STATION in SHADOWED else ".py"))
REF = os.path.join(SKILL, "references")
EX = os.path.join(REF, "examples")
TEMPLATES = os.path.join(REF, "templates")
PLUGIN = os.path.dirname(os.path.dirname(SKILL))
PLUGINS = os.path.dirname(PLUGIN)                      # the checkout's plugins/ folder, when there is one
REPO = os.path.dirname(PLUGINS)
CORES = ("precon-v2", "architect-v2", "blueprint-v2", "inspect-v2")
MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"


def add_scripts_to_path():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)


def checkout_sibling(name):
    """`plugins/<name>` of the checkout this core sits in, or None in the installed shape."""
    path = os.path.join(PLUGINS, name)
    if os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json")) and \
            os.path.isdir(os.path.join(REPO, "plugins")):
        return path
    return None


def records_root():
    """The records component of this checkout (route 3a's folder), or None."""
    return checkout_sibling("records")


def readers_entry():
    """The readers shell entry of this checkout, or None."""
    root = checkout_sibling("readers")
    if root is None:
        return None
    path = os.path.join(root, "skills", "readers", "assets", "readers")
    return path if os.path.isfile(path) else None


def readers_roster():
    root = checkout_sibling("readers")
    if root is None:
        return None
    return os.path.join(root, "skills", "readers", "assets", "roster.json")


def load_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def write_json(path, doc):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def write_text(path, text, newline="\n"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def scratch_base():
    base = os.environ.get("STATION_TEST_SCRATCH")
    if base and os.path.isdir(base):
        return base
    return tempfile.gettempdir()


def make_scratch(prefix="station-"):
    return os.path.realpath(tempfile.mkdtemp(prefix=prefix, dir=scratch_base()))


def rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


def base_env(extra=None):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"),
           "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
    for key in ("STATION_TEST_SCRATCH", "TMPDIR"):
        if key in os.environ:
            env[key] = os.environ[key]
    env.update(extra or {})
    return env


def run_driver(args, cwd=None, env=None, python=None):
    """Run this core's phase driver; return (exit code, stdout, stderr)."""
    cmd = [python or sys.executable, DRIVER] + [str(a) for a in args]
    proc = subprocess.run(cmd, cwd=cwd or tempfile.gettempdir(), env=env or base_env(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def run_script(name, args, cwd=None, env=None, python=None):
    cmd = [python or sys.executable, os.path.join(SCRIPTS, name)] + [str(a) for a in args]
    proc = subprocess.run(cmd, cwd=cwd or tempfile.gettempdir(), env=env or base_env(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def stub_without_jsonschema(parent):
    """A directory holding a jsonschema package that refuses to import; first on PYTHONPATH."""
    stub = os.path.join(parent, "no-jsonschema")
    os.makedirs(os.path.join(stub, "jsonschema"), exist_ok=True)
    write_text(os.path.join(stub, "jsonschema", "__init__.py"),
               'raise ImportError("jsonschema stubbed out for the exit-3 test")\n')
    return stub


GIT_CONFIG_ARGS = ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                   "-c", "core.autocrlf=false", "-c", "core.fileMode=true"]


def git(cwd, args, when="2026-09-19T09:00:00-07:00"):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"),
           "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.invalid",
           "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.invalid",
           "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    proc = subprocess.run(["git"] + GIT_CONFIG_ARGS + list(args), cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("git %s failed (%d): %s" % (args, proc.returncode,
                                                       proc.stderr.decode("utf-8", "replace")))
    return proc.stdout.decode("utf-8")


def git_workspace(parent, name="workspace", files=None):
    """A git work tree with one commit holding `files` ({relative path: text})."""
    ws = os.path.join(parent, name)
    os.makedirs(ws)
    git(ws, ["init", "-q", "-b", "main"])
    for rel, text in sorted((files or {"README.md": "# A project\n"}).items()):
        write_text(os.path.join(ws, rel), text)
    git(ws, ["add", "-A"])
    git(ws, ["commit", "-q", "-m", "base"])
    return ws


def make_input(workspace, run_dir, **extra):
    doc = {"input_version": 1, "run_id": "run-0001", "workspace": workspace, "run_dir": run_dir,
           "invocation": {"harness": "claude-code", "caller": "user", "mode": "direct",
                          "session_id": "session-test-1"}}
    doc.update(extra)
    return doc


def tree_digest(root):
    """A digest over every file under `root` (path, mode, content), `.git` skipped."""
    entries = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            st = os.lstat(full)
            if os.path.islink(full):
                mode, content = "link", os.readlink(full).encode("utf-8", "surrogateescape")
            else:
                mode = "%04o" % (st.st_mode & 0o777)
                with open(full, "rb") as fh:
                    content = fh.read()
            entries.append(rel + "\0" + mode + "\0" + hashlib.sha256(content).hexdigest())
    entries.sort()
    return hashlib.sha256(("\n".join(entries) + "\n").encode("utf-8")).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
