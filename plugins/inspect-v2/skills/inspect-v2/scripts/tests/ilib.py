"""Fixtures and a phase runner for inspect-v2's own tests (lane I; standard library only).

Not a shared file: the shared helpers are `testlib.py`. Everything here builds under a temporary
directory and drives the REAL CLI (`scripts/inspect_v2.py`) from a working directory outside the
worktree. The fixture text is a made-up bench-rig turn counter.
"""
import json
import os
import shutil
import subprocess
import sys

import testlib

D = "\u2014"
NOW = "2026-09-25T12:00:00Z"
TODAY = "2026-09-25"
BUILD_REL = "docs/plans/2026-09-22-turnstile.md"
SCOPE_REL = "docs/scope/2026-09-20-turnstile.md"

BUILD_DOC = "\n".join([
    "# Turnstile %s build plan (2026-09-22)" % D,
    "",
    "Intent: count turns for the owner's bench rig.",
    "Constraints: Python 3.9 standard library; `python3 -m unittest`.",
    "Out of scope: a web dashboard %s declined in the scope doc" % D,
    "",
    "## Slice A %s Count turns" % D,
    "Goal: `spin()` returns the count after one more turn.",
    "Requirements:",
    "- R1 %s `spin(n)` returns `n + 1`" % D,
    "Acceptance criteria:",
    "- AC1: `spin(2)` returns 3 %s verify: new test at tests/test_turnstile.py" % D,
    "Footprint: src/turnstile.py, tests/test_turnstile.py",
    "Not in this slice: the reset",
    "Depends on: nothing",
    "Status: not started",
    "",
    "## Build assumptions",
    "## Deviations",
    "## Discovered",
    "## Handoffs",
    "## Punch list",
    "",
])

SCOPE_DOC = "\n".join([
    "# Turnstile %s scope doc (2026-09-20)" % D,
    "",
    "Intent: a small turn counter for the owner's bench rig.",
    "Decisions:",
    "- Python 3.9 standard library only %s decided (the owner's words: \"no dependencies\")" % D,
    "- One module, no package %s assumed (small and reversible)" % D,
    "Out of scope: a web dashboard %s the owner declined it" % D,
    "Research:",
    "Open:",
    "- how often the counter resets",
    "Next: /blueprint when ready.",
    "",
])

ENV = {"INSPECT_V2_TEST": "1", "INSPECT_V2_TEST_NOW": NOW}


def workspace(parent, build=BUILD_DOC, scope=SCOPE_DOC, extra=None, name="ws"):
    files = {"README.md": "# bench rig\n", "src/turnstile.py": "def spin(n):\n    return n + 1\n"}
    if build is not None:
        files[BUILD_REL] = build
    if scope is not None:
        files[SCOPE_REL] = scope
    files.update(extra or {})
    return testlib.git_workspace(parent, name, files)


def make_input(ws, run_dir, row="claude-session", staging=None, run_id="run-0001", **extra):
    station = {}
    for key in ("model", "displayed_model", "session_model"):
        if key in extra:
            station[key] = extra.pop(key)
    if row is not None:
        station["row"] = row
    doc = testlib.make_input(ws, run_dir, **extra)
    doc["run_id"] = run_id
    doc["station"] = station
    if staging:
        doc["staging"] = staging
    return doc


class Runner(object):
    """One run of the real CLI, phase by phase."""

    def __init__(self, tmp, ws, run_dir=None, env=None, driver=None):
        self.tmp = tmp
        self.ws = ws
        self.run_dir = run_dir or os.path.join(tmp, "run")
        self.cwd = os.path.join(tmp, "elsewhere")
        os.makedirs(self.cwd, exist_ok=True)
        self.env = testlib.base_env(dict(ENV, **(env or {})))
        self.driver = driver or testlib.DRIVER

    def cli(self, args, env=None):
        full = dict(self.env)
        full.update(env or {})
        proc = subprocess.run([sys.executable, self.driver] + [str(a) for a in args], cwd=self.cwd,
                              env=full, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        doc = None
        if out.strip():
            try:
                doc = json.loads(out)
            except ValueError:
                doc = None
        return proc.returncode, doc, out, proc.stderr.decode("utf-8", "replace")

    def check(self, doc):
        path = os.path.join(self.tmp, "input-%s.json" % doc["run_id"])
        testlib.write_json(path, doc)
        return self.cli(["check-input", path])

    def phase(self, name, *args, **kw):
        return self.cli([name, "--run-dir", self.run_dir] + list(args), env=kw.get("env"))

    def upto(self, last, doc=None, answer=None, name="turnstile"):
        """Run check-input through `last`, asserting each earlier step's exit."""
        steps = [("check-input", 0), ("select-build", 0), ("select-scope", 0), ("harvest", 0),
                 ("packet", 0), ("request", 0), ("record-answer", 0), ("write", 0), ("report", 10)]
        outcome = None
        for step, want in steps:
            if step == "check-input":
                outcome = self.check(doc or make_input(self.ws, self.run_dir))
            elif step == "select-build":
                outcome = self.phase("select", "--hunt", "build", "--name", name)
            elif step == "select-scope":
                outcome = self.phase("select", "--hunt", "scope")
            elif step == "record-answer":
                path = os.path.join(self.tmp, "answer.json")
                testlib.write_json(path, answer)
                outcome = self.phase("record-answer", "--answer", path)
            else:
                outcome = self.phase(step)
            if step == last:
                return outcome
            assert outcome[0] == want, (step, outcome[0], outcome[2][-2000:], outcome[3][-2000:])
        return outcome

    def artifact(self, name):
        return testlib.load_json(os.path.join(self.run_dir, name))


def reader_result(call_id, row="claude-session", model="claude-test-model", findings=(), **extra):
    doc = {"call_id": call_id, "row": row, "effective_model": model, "findings": list(findings)}
    doc.update(extra)
    return doc


def finding(location, severity="MAJOR", claim="AC1 names no failure case",
            scenario="a grader cannot tell a partial counter", confidence="high", **extra):
    doc = {"severity": severity, "location": location, "claim": claim, "scenario": scenario,
           "confidence": confidence}
    doc.update(extra)
    return doc


def answer(run_id, results, row="claude-session", lanes=None, session_id="session-test-1", **extra):
    lens_of = {"traceability": "traceability", "code-book": "code-book", "repo-reality": "repo-reality"}
    if lanes is None:
        lanes = []
        for result in results:
            tail = (result.get("call_id") or "").split(run_id + "-", 1)[-1]
            lanes.append(lens_of.get(tail, "paper"))
        lanes = sorted(set(lanes))
    doc = {"answer_version": 1, "run_id": run_id, "session_id": session_id, "questions": [],
           "lines": [], "row": row, "lanes": lanes, "results": list(results)}
    doc.update(extra)
    return doc


def claude_fleet(run_id, traceability=(), code_book=(), repo_reality=(), model="claude-test-model"):
    return [reader_result("%s-traceability" % run_id, model=model, findings=traceability),
            reader_result("%s-code-book" % run_id, model=model, findings=code_book),
            reader_result("%s-repo-reality" % run_id, model=model, findings=repo_reality)]


def records_cli(args, python=None):
    """The records component's CLI of this checkout, for a test's own reads and plants."""
    root = testlib.records_root()
    proc = subprocess.run([python or sys.executable, os.path.join(root, "scripts", "records.py")]
                          + [str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    return proc.returncode, (json.loads(out) if out.strip() else None), proc.stderr.decode("utf-8", "replace")


def installed_shape(parent, with_records=True, with_code_book=True, records_version=None):
    """This checkout's inspect-v2 (and its siblings) laid out the way a harness installs plugins:
    `<cache>/<marketplace>/<plugin>/<version>/`. Returns the copied driver's path."""
    base = os.path.join(parent, "cache", "local")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "evals", "setups")

    def version_of(root):
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            return json.load(fh)["version"]

    plugin = testlib.PLUGIN
    target = os.path.join(base, "inspect-v2", version_of(plugin))
    shutil.copytree(plugin, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if with_code_book:
        bp = testlib.checkout_sibling("blueprint-v2")
        shutil.copytree(bp, os.path.join(base, "blueprint-v2", version_of(bp)), ignore=ignore)
    if with_records:
        rec = testlib.records_root()
        shutil.copytree(rec, os.path.join(base, "records", records_version or version_of(rec)),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "fixtures"))
    readers = testlib.checkout_sibling("readers")
    if readers is not None:
        shutil.copytree(readers, os.path.join(base, "readers", version_of(readers)),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "fixtures"))
    return os.path.join(target, "skills", "inspect-v2", "scripts", "inspect_v2.py")


def numbered(text):
    lines = text.split("\n")
    if text.endswith("\n"):
        lines = lines[:-1]
    return "".join("%d: %s\n" % (i, line) for i, line in enumerate(lines, 1))
