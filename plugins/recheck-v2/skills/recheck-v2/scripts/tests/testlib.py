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


# ---- slice 2: fixture builds per case, input preparation, canned reports, the driver ----------

import atexit  # noqa: E402

_LANE_CACHE = {}
_LANE_ROOT = []
DEFAULT_LANES = ("C-continuation", "W-recording", "IA-input-authorization", "I2I4-conflicts-paths", "S34-cards-identity",
                 "VXUM-verifier-execution", "F1-fixed-defect", "F2-unfixed-defect", "S2-waivers-reopening", "S1-colocated")
HARNESS = {"name": "test-harness", "version": "0", "entry": "explicit path", "sandbox": "none"}
MODEL = {"id": "claude-fable-5-1", "floor_class": "opus", "floor_met": True}


def all_lanes():
    return sorted(d for d in os.listdir(FIXTURES) if os.path.isfile(os.path.join(FIXTURES, d, "build.py")))


def lane_dir(lane):
    """Build a lane once per process (read-only use); cleaned up at exit."""
    if lane not in _LANE_CACHE:
        if not _LANE_ROOT:
            _LANE_ROOT.append(make_scratch("e8-slice2-lanes-"))
            atexit.register(lambda: rmtree(_LANE_ROOT[0]))
        out = os.path.join(_LANE_ROOT[0], lane)
        build_lane(lane, out)
        _LANE_CACHE[lane] = out
    return _LANE_CACHE[lane]


def lane_cases(lane):
    """[(case_id, case_dir)] of a lane built once per process."""
    out = lane_dir(lane)
    return [(os.path.basename(d), d) for d in sorted(os.path.join(out, c) for c in os.listdir(out)
                                                     if os.path.isfile(os.path.join(out, c, "manifest.json")))]


def build_case(lane, case_id, out):
    """Build one case into a fresh directory (for tests that run the driver); return the case dir."""
    build = os.path.join(FIXTURES, lane, "build.py")
    proc = subprocess.run([GEN_PYTHON, build, "--out", out, "--case", case_id, "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("build of %s/%s failed (%d): %s" % (lane, case_id, proc.returncode, proc.stderr.decode("utf-8", "replace")[-500:]))
    return json.loads(proc.stdout.decode("utf-8"))["cases"][0]["path"]


def prepare_input(case_dir, model=True, harness=True, run_date="2026-09-20", mutate=None, path=None):
    """Rewrite the case's input.json with the objects the adapter supplies at run time (E8-18,
    E8-25) and any mutation; return the path written."""
    src = os.path.join(case_dir, "input.json")
    doc = load_json(src)
    inv = doc.setdefault("invocation", {}) if isinstance(doc.get("invocation"), dict) or "invocation" not in doc else doc["invocation"]
    if harness and isinstance(inv, dict):
        inv["harness"] = dict(HARNESS)
    if model and isinstance(inv, dict):
        inv["model"] = dict(MODEL) if model is True else dict(model)
    if run_date and isinstance(inv, dict):
        inv["run_date"] = run_date
    if mutate:
        mutate(doc)
    dst = path or src
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return dst


def recheck(args, cwd=None, env=None, hooks=None):
    """Run recheck.py; return (exit code, parsed stdout JSON or None, stderr)."""
    e = dict(os.environ)
    if env:
        e.update(env)
    if hooks:
        e["RECHECK_TEST"] = "1"
        e.update(hooks)
    code, out, err = run_script("recheck.py", args, cwd=cwd, env=e)
    doc = None
    if out.strip():
        try:
            doc = json.loads(out)
        except ValueError:
            doc = {"_raw": out}
    return code, doc, err


def canned_report(items, new_defects=(), grant_claims=(), injection_attempts=(), refused_actions=(), prose="Ran every scenario from the workspace root."):
    """A verifier report in the section 7 shape. items: [{index, location, disposition, reason?,
    method?, static_reason?, blocked?, missing?, missed_case?, evidence?, location_after_fix?}]."""
    rows = []
    for it in items:
        row = {"index": it["index"], "location": it["location"], "disposition": it["disposition"], "reason": it.get("reason"),
               "method": it.get("method", "executed"), "static_reason": it.get("static_reason"), "blocked": it.get("blocked"),
               "missing": it.get("missing"), "missed_case": it.get("missed_case"),
               "evidence": it.get("evidence") or [{"kind": "command", "detail": it.get("detail", "ran the scenario command; observed the output"), "artifact": it.get("artifact")}],
               "location_after_fix": it.get("location_after_fix")}
        rows.append(row)
    tail = {"recheck_verifier_report": 1, "items": rows, "new_defects": list(new_defects), "grant_claims": list(grant_claims),
            "injection_attempts": list(injection_attempts), "refused_actions": list(refused_actions)}
    return "# Verifier report\n\n%s\n\n```json\n%s\n```\n" % (prose, json.dumps(tail, indent=1, ensure_ascii=False))


def write_report(run_dir, text, name="raw.md"):
    folder = os.path.join(run_dir, "verifier")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def git(cwd, *args):
    return subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8")
