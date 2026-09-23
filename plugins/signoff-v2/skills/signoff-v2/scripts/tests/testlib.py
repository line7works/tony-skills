"""Shared paths and helpers for the signoff-v2 script tests (stdlib only).

Every path derives from this file's location, so the suite runs from any working directory:

    uv run --with jsonschema==4.25.1 python3 -m unittest discover -s <this directory> -v

Seeded cases are built with their own generators (read and run, never modified) into a temporary
directory under SIGNOFF_TEST_SCRATCH when that variable names a directory, else under the system
temporary directory; never into the worktree and never under evals/. Every test that builds
cleans up what it built.

The root follows the pilot's E8-A48 rule: REPO is `git rev-parse --show-toplevel` run in the
scripts directory when that succeeds, else the plugin root (the first directory above this file
holding `.claude-plugin/`, as in a standalone copy of the plugin folder).
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


PLUGIN = _plugin_root()


def _worktree_root():
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=SCRIPTS,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        proc = None
    if proc is not None and proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.decode("utf-8", "replace").strip()
    return PLUGIN


REPO = _worktree_root()
EVALS = os.path.join(PLUGIN, "evals")
SEEDED = os.path.join(EVALS, "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
FAMILIES = ("S1-review-scope", "S2-evidence", "S3-independence")
GEN_PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"
RECORDS_ROOT = os.path.normpath(os.path.join(PLUGIN, os.pardir, "records"))


def add_scripts_to_path():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)


def load_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return path


def scratch_base():
    base = os.environ.get("SIGNOFF_TEST_SCRATCH")
    if base and os.path.isdir(base):
        return base
    return tempfile.gettempdir()


def make_scratch(prefix):
    return tempfile.mkdtemp(prefix=prefix, dir=scratch_base())


def rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


def other_cwd(parent, name="elsewhere"):
    """A working directory for the "from another working directory" tests: outside the worktree
    root and outside the plugin root, so a test cannot pass by accident of the current directory."""
    path = os.path.join(parent, name)
    real = os.path.realpath(path)
    for label, root in (("worktree", REPO), ("plugin", PLUGIN)):
        r = os.path.realpath(root)
        if real == r or real.startswith(r + os.sep):
            raise AssertionError("the other working directory %s is inside the %s root %s"
                                 % (real, label, r))
    os.makedirs(path, exist_ok=True)
    return path


def build_case(family, case_id, out):
    """Build one seeded case into `out` with the family's own generator; return the case dir."""
    build = os.path.join(SEEDED, family, "build.py")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([GEN_PYTHON, build, "--out", out, "--case", case_id, "--json"],
                          env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("build of %s/%s failed (%d): %s"
                           % (family, case_id, proc.returncode,
                              proc.stderr.decode("utf-8", "replace")[-500:]))
    return json.loads(proc.stdout.decode("utf-8"))["cases"][0]["path"]


def family_of(case_id):
    for family in FAMILIES:
        if case_id.startswith(family.split("-")[0] + "-"):
            return family
    raise KeyError(case_id)


def case_ids(family):
    build = os.path.join(SEEDED, family, "build.py")
    proc = subprocess.run([GEN_PYTHON, build, "--list"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if proc.returncode != 0:
        raise RuntimeError("--list of %s failed: %s" % (family, proc.stderr.decode("utf-8", "replace")))
    return [line for line in proc.stdout.decode("utf-8").split("\n") if line.strip()]


def all_case_ids():
    out = []
    for family in FAMILIES:
        out.extend(case_ids(family))
    return out


def stub_without_jsonschema(parent):
    """A directory holding a jsonschema package that refuses to import; put it first on
    PYTHONPATH. The real failure rather than a simulation of its message."""
    stub = os.path.join(parent, "no-jsonschema")
    os.makedirs(os.path.join(stub, "jsonschema"), exist_ok=True)
    with open(os.path.join(stub, "jsonschema", "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write('raise ImportError("jsonschema stubbed out for the exit-3 test")\n')
    return stub


# Astra's F5: the core enforces the Opus-class floor from the adapter's observed model and the
# readers result. The recorded-answer replays these suites run have neither a live harness nor a
# live reader, so they supply SYNTHETIC facts through the core's one explicit test interface
# (`signoff_core/floor.py`): honoured only with SIGNOFF_TEST=1, and named as synthetic in the
# result. A test that exercises the real rule passes {"SIGNOFF_TEST_REPLAY_MODEL": ""}.
REPLAY_MODEL = "claude-opus-5-5"
REPLAY_ENV = {"SIGNOFF_TEST": "1", "SIGNOFF_TEST_REPLAY_MODEL": REPLAY_MODEL}


def run_script(script, args, cwd=None, python=None, env=None):
    """Run a CLI script of this skill; return (exit code, stdout, stderr)."""
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    e.update(REPLAY_ENV)
    if env:
        e.update(env)
    cmd = [python or sys.executable, os.path.join(SCRIPTS, script)] + [str(a) for a in args]
    proc = subprocess.run(cmd, cwd=cwd or tempfile.gettempdir(), env=e,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def signoff(args, cwd=None, env=None, python=None):
    """Run signoff.py; return (exit code, parsed stdout JSON or None, stderr)."""
    code, out, err = run_script("signoff.py", args, cwd=cwd, env=env, python=python)
    doc = None
    if out.strip():
        try:
            doc = json.loads(out)
        except ValueError:
            doc = {"_raw": out}
    return code, doc, err


def git(cwd, *args):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    return subprocess.run(["git"] + list(args), cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8")


def project_status(cwd):
    """`git status --porcelain` with `docs/records/` excluded (CR-2, CR-3).

    The component's log is an authorized write OF THE COMPONENT, never of this script, and the
    source identity excludes exactly that prefix, so a test that means "the run wrote nothing
    into the project's documents" asks for the status the identity sees."""
    return git(cwd, "status", "--porcelain", "--", ".", ":(exclude)docs/records")


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def tree_hash(root, exclude=()):
    """A hash over every file under `root` (path and content), for "nothing was written" tests."""
    import hashlib
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__"))
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if any(rel == e or rel.startswith(e.rstrip("/") + os.sep) for e in exclude):
                continue
            h.update(rel.encode("utf-8") + b"\0")
            try:
                with open(full, "rb") as fh:
                    h.update(fh.read())
            except OSError:
                h.update(b"<unreadable>")
            h.update(b"\0")
    return h.hexdigest()
