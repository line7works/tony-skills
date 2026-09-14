"""Shared paths and helpers for the recheck-v2 script tests (stdlib only).

Every path derives from this file's location, so the suite runs from any working directory:

    uv run --with jsonschema==4.25.1 python3 -m unittest discover -s <this directory> -v

Fixtures are built with the E7 generators (read and run, never modified) into a temporary
directory under RECHECK_TEST_SCRATCH when that variable names a directory, else under the
system temporary directory; never into the worktree and never under evals/. Every test that
builds cleans up what it built.
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
PLUGIN = os.path.dirname(os.path.dirname(SKILL))
EVALS = os.path.join(PLUGIN, "evals")
FIXTURES = os.path.join(EVALS, "fixtures")
FIXTURE_LIB = os.path.join(FIXTURES, "_lib")
GEN_PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"
LANES_WITH_SEEDED_RUNS = ("C-continuation", "W-recording")


def add_scripts_to_path():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)


def fixturelib():
    """The E7 shared library, imported read-only from evals/fixtures/_lib."""
    if FIXTURE_LIB not in sys.path:
        sys.path.insert(0, FIXTURE_LIB)
    import fixturelib as lib  # noqa: E402
    return lib


def load_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def scratch_base():
    base = os.environ.get("RECHECK_TEST_SCRATCH")
    if base and os.path.isdir(base):
        return base
    return tempfile.gettempdir()


def make_scratch(prefix):
    return tempfile.mkdtemp(prefix=prefix, dir=scratch_base())


def build_lane(lane, out):
    """Run <lane>/build.py --out <out> under the contract's interpreter; return the case dirs."""
    build = os.path.join(FIXTURES, lane, "build.py")
    proc = subprocess.run([GEN_PYTHON, build, "--out", out, "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("build of %s failed (%d): %s" % (lane, proc.returncode, proc.stderr.decode("utf-8", "replace")[-500:]))
    summary = json.loads(proc.stdout.decode("utf-8"))
    return [row["path"] for row in summary["cases"]]


def case_dirs(out, lane):
    lane_out = os.path.join(out, lane)
    return sorted(os.path.join(lane_out, c) for c in os.listdir(lane_out)
                  if os.path.isfile(os.path.join(lane_out, c, "manifest.json")))


def stub_without_jsonschema(parent):
    """A directory holding a jsonschema package that refuses to import; put it first on PYTHONPATH."""
    stub = os.path.join(parent, "no-jsonschema")
    os.makedirs(os.path.join(stub, "jsonschema"))
    with open(os.path.join(stub, "jsonschema", "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write('raise ImportError("jsonschema stubbed out for the exit-3 test")\n')
    return stub


def run_script(script, args, cwd=None, python=None, env=None):
    """Run a CLI script; return (exit code, stdout, stderr)."""
    cmd = [python or sys.executable, os.path.join(SCRIPTS, script)] + list(args)
    proc = subprocess.run(cmd, cwd=cwd or tempfile.gettempdir(), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def rmtree(path):
    shutil.rmtree(path, ignore_errors=True)
