"""Shared paths and helpers for the build-v2 script tests (standard library only).

Every path derives from this file's location, so the suite runs from any working directory:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s <this directory> -t <this directory>

Fixtures are built into a temporary directory under BUILD_TEST_SCRATCH when that variable names
a directory, else under the system temporary directory; never into the worktree, never under
`evals/`. Every test that builds cleans up what it built.

The roots follow the pilot's rule (E8-A48): PLUGIN is the first directory above this file
holding `.claude-plugin/`; REPO is `git rev-parse --show-toplevel` run in the scripts directory
when that succeeds, else PLUGIN, so a standalone copy of the plugin folder still runs.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(TESTS)
SKILL = os.path.dirname(SCRIPTS)
REF = os.path.join(SKILL, "references")
EX = os.path.join(REF, "examples")


def _plugin_root():
    d = SCRIPTS
    while True:
        if os.path.isdir(os.path.join(d, ".claude-plugin")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.dirname(os.path.dirname(SKILL))
        d = parent


def _worktree_root():
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=SCRIPTS,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        proc = None
    if proc is not None and proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.decode("utf-8", "replace").strip()
    return PLUGIN


PLUGIN = _plugin_root()
REPO = _worktree_root()
EVALS = os.path.join(PLUGIN, "evals")
SEEDED = os.path.join(EVALS, "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
FAMILIES = ("B1-scope-adherence", "B2-honest-failure")
GEN_PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"

# The records component of this checkout, reached only as a sibling plugin folder (route 3a).
RECORDS_ROOT = os.path.join(os.path.dirname(PLUGIN), "records")


def add_scripts_to_path():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)


def pilot_records_client():
    """The pilot's records_client.py path (read-only; the byte comparison of the copy)."""
    return os.path.join(os.path.dirname(PLUGIN), "recheck-v2", "skills", "recheck-v2",
                        "scripts", "recheck_core", "records_client.py")


def load_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def write_json(path, doc):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def scratch_base():
    base = os.environ.get("BUILD_TEST_SCRATCH")
    if base and os.path.isdir(base):
        return base
    return tempfile.gettempdir()


def make_scratch(prefix):
    return tempfile.mkdtemp(prefix=prefix, dir=scratch_base())


def rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


def other_cwd(parent, name="elsewhere"):
    """A working directory outside the worktree root and the plugin root, for the
    "from another working directory" tests."""
    path = os.path.join(parent, name)
    real = os.path.realpath(path)
    for label, root in (("worktree", REPO), ("plugin", PLUGIN)):
        r = os.path.realpath(root)
        if real == r or real.startswith(r + os.sep):
            raise AssertionError("the other working directory %s is inside the %s root %s"
                                 % (real, label, r))
    os.makedirs(path, exist_ok=True)
    return path


def base_env(extra=None):
    """A clean environment for a CLI run: no bytecode, the caller's PATH and HOME."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"),
           "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
    if "BUILD_TEST_SCRATCH" in os.environ:
        env["BUILD_TEST_SCRATCH"] = os.environ["BUILD_TEST_SCRATCH"]
    env.update(extra or {})
    return env


def run_script(script, args, cwd=None, python=None, env=None):
    """Run one of this skill's CLI scripts; return (exit code, stdout, stderr)."""
    cmd = [python or sys.executable, os.path.join(SCRIPTS, script)] + [str(a) for a in args]
    proc = subprocess.run(cmd, cwd=cwd or tempfile.gettempdir(), env=env or base_env(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def run_build(args, cwd=None, python=None, env=None):
    return run_script("build.py", args, cwd=cwd, python=python, env=env)


def stub_without_jsonschema(parent):
    """A directory holding a jsonschema package that refuses to import; first on PYTHONPATH."""
    stub = os.path.join(parent, "no-jsonschema")
    os.makedirs(os.path.join(stub, "jsonschema"), exist_ok=True)
    with open(os.path.join(stub, "jsonschema", "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write('raise ImportError("jsonschema stubbed out for the exit-3 test")\n')
    return stub


def fake_component(parent, interface_version=2):
    """A REAL COPY of the records component with `INTERFACE_VERSION` set to another version.

    The brief's own shape for this test: a copy of `records/` whose one constant is changed, not a
    stand-in that prints a number. The component is copied byte for byte (the original is never
    touched) and the single assignment in `scripts/records.py` is rewritten, so every other line
    of the component — its argument parsing, its response envelope, its exit codes — is the real
    one. What the station must do is refuse to speak to it at all.
    """
    root = os.path.join(parent, "records-v%d" % interface_version)
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(RECORDS_ROOT, root,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    script = os.path.join(root, "scripts", "records.py")
    with open(script, encoding="utf-8") as fh:
        text = fh.read()
    changed = text.replace("\nINTERFACE_VERSION = 1\n", "\nINTERFACE_VERSION = %d\n" % interface_version, 1)
    assert changed != text, "the component's INTERFACE_VERSION assignment moved; update this helper"
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(changed)
    return root


# ---- seeded case helpers ---------------------------------------------------------------------

def build_family(family, out):
    """Run <family>/build.py --out <out> under the contract's interpreter; return the case dirs."""
    build = os.path.join(SEEDED, family, "build.py")
    proc = subprocess.run([GEN_PYTHON, build, "--out", out, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=base_env())
    if proc.returncode != 0:
        raise RuntimeError("build of %s failed (%d): %s"
                           % (family, proc.returncode, proc.stderr.decode("utf-8", "replace")[-800:]))
    summary = json.loads(proc.stdout.decode("utf-8"))
    return [row["path"] for row in summary["cases"]]


_FAMILY_CACHE = {}
_FAMILY_ROOT = []


def family_cases(family):
    """[(case id, case dir)] of a family built once per process; cleaned up at exit."""
    import atexit
    if family not in _FAMILY_CACHE:
        if not _FAMILY_ROOT:
            _FAMILY_ROOT.append(make_scratch("build-v2-families-"))
            atexit.register(lambda: rmtree(_FAMILY_ROOT[0]))
        out = os.path.join(_FAMILY_ROOT[0], family)
        build_family(family, out)
        _FAMILY_CACHE[family] = out
    out = _FAMILY_CACHE[family]
    return [(c, os.path.join(out, c)) for c in sorted(os.listdir(out))
            if os.path.isfile(os.path.join(out, c, "manifest.json"))]


def tree_digest(root, skip_git=True):
    """A digest over every file under `root`: path, mode and content.

    The measurement behind "this run wrote nothing": taken before and after a run and compared.
    `.git` is skipped only when `skip_git` is set; the log lives under `docs/records/` and is
    always covered.
    """
    import hashlib
    entries = []
    for base, dirs, files in os.walk(root):
        if skip_git:
            dirs[:] = sorted(d for d in dirs if d != ".git")
        else:
            dirs[:] = sorted(dirs)
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


# ---- a small git workspace, for the tests the seeded cases do not cover ------------------------

GIT_CONFIG_ARGS = ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                   "-c", "core.autocrlf=false", "-c", "core.fileMode=true"]


def git_env():
    return {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"),
            "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.invalid"}


def git(cwd, args, when="2026-09-19T09:00:00-07:00"):
    env = git_env()
    env["GIT_AUTHOR_DATE"] = when
    env["GIT_COMMITTER_DATE"] = when
    proc = subprocess.run(["git"] + GIT_CONFIG_ARGS + list(args), cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("git %s failed (%d): %s" % (args, proc.returncode,
                                                       proc.stderr.decode("utf-8", "replace")))
    return proc.stdout.decode("utf-8")


def write_text(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


DOC_PATH = "docs/plans/2026-09-20-widget.md"

BUILD_DOC = """# Widget

## Slice A — Make the widget spin
Status: not started

Slice A makes the widget spin.

Footprint:
- src/widget.py

Requirements:
- R1. `spin()` returns the number of turns.

Checks:
- unit: sh checks/unit.sh

Not in this slice:
- src/other.py
- checks/

## Punch list
"""


def make_workspace(parent, name="workspace", doc=BUILD_DOC):
    """A git work tree with a build doc, one source file, a .gitignore, and a `base` tag."""
    ws = os.path.join(parent, name)
    os.makedirs(ws, exist_ok=True)
    git(ws, ["init", "-q", "-b", "main"])
    write_text(os.path.join(ws, ".gitignore"), "__pycache__/\n*.pyc\nbuild/\n")
    write_text(os.path.join(ws, "src", "widget.py"), "def spin():\n    return 0\n")
    write_text(os.path.join(ws, "src", "other.py"), "VALUE = 1\n")
    write_text(os.path.join(ws, "checks", "unit.sh"), "#!/bin/sh\necho ok\n")
    write_text(os.path.join(ws, doc if os.path.isabs(doc) else DOC_PATH), doc)
    git(ws, ["add", "-A"])
    git(ws, ["commit", "-q", "-m", "base"])
    git(ws, ["tag", "base"])
    return ws


def commit_work(ws, message="work"):
    git(ws, ["add", "-A"])
    git(ws, ["commit", "-q", "-m", message], when="2026-09-20T09:00:00-07:00")


def make_input(run_dir, workspace, run_id="run-1", slice_name="A", base="base",
               doc=DOC_PATH, **extra):
    body = {"input_version": 1, "run_id": run_id, "workspace": workspace, "run_dir": run_dir,
            "build_doc": doc, "slice": slice_name, "base": base,
            "invocation": {"harness": "test-harness", "caller": "user", "mode": "direct"}}
    body.update(extra)
    return body


ANSWER = {
    "seeded_answer": 1, "case": "unit", "role": "executor", "session_id": "sess-test-1",
    "claimed_status": "complete", "claimed_card": "built",
    "edits": [{"path": "src/widget.py", "reason": "R1"}],
    "checks": [{"name": "unit", "command": "sh checks/unit.sh", "result": "passed",
                "exit_code": 0, "output": "ok"}],
    "notes": "one file touched",
}


def uv_python():
    """The argv that runs a script with the pinned dependency, when uv is on PATH."""
    return ["uv", "run", "--quiet", "--python", "/usr/bin/python3", "--with", "jsonschema==4.25.1"]


PRE_A4_COMMIT = "a80cdd04432c5f4662ed415d6a72d54f9b8208c1"


def pre_a4_component(parent):
    """The records component as it stood BEFORE E13 amendment A4, extracted read-only.

    `git archive` writes nothing to the repository and touches no index, so this is a read of
    history, not a checkout. It exists so the A4 tests can be run RED against the component that
    did not have the fix: before A4 a second build run on one document re-imported the `Status:`
    line this station had written as a fresh `card_observed`, and `native_rendered` did not
    exist at all. Returns the component root, or None when the history is not reachable.
    """
    root = os.path.join(parent, "records-pre-a4")
    if os.path.isdir(root):
        return root
    os.makedirs(root, exist_ok=True)
    try:
        archive = subprocess.run(["git", "archive", PRE_A4_COMMIT, "plugins/records"],
                                 cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if archive.returncode != 0:
            return None
        extract = subprocess.run(["tar", "-x", "-C", root], input=archive.stdout,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if extract.returncode != 0:
            return None
    except OSError:
        return None
    inner = os.path.join(root, "plugins", "records")
    return inner if os.path.isfile(os.path.join(inner, "scripts", "records.py")) else None
