"""Fixtures and a CLI runner for blueprint-v2's own tests (lane L; not a shared file).

Every fixture is the made-up bench-rig turn counter, built under a temporary directory through
`testlib`, and removed by the caller's cleanup. Nothing here is written into the worktree.
"""
import json
import os
import sys

import testlib

testlib.add_scripts_to_path()

from station_core import ledger  # noqa: E402

D = "\u2014"
M = "\u00b7"

SCOPE = (
    "# Turnstile %(D)s scope doc (2026-09-20)\n\n"
    "Intent: a small turn counter for the owner's bench rig.\n"
    "Decisions:\n"
    "- Python 3.9 standard library only %(D)s decided (the owner's words: \"no dependencies\")\n"
    "- One module, no package %(D)s assumed (small and reversible)\n"
    "- Where the count is kept between sessions %(D)s parked: needs research\n"
    "Out of scope: a web dashboard %(D)s the owner declined it\n"
    "Research:\n"
    "Open:\n"
    "- how often the counter resets\n"
    "Next: /blueprint when ready.\n") % {"D": D}

ARCH = (
    "# Turnstile %(D)s architecture (2026-09-21)\n\n"
    "Scope doc: docs/scope/2026-09-20-turnstile.md\n"
    "Blind review: none yet\n\n"
    "## Walkthrough target\n"
    "Who: Sam Bench  %(M)s  When: 2026-10-01  %(M)s  Must be able to: count turns, reset\n\n"
    "## v0 drawing\n"
    "Components: one module `turnstile.py`\n"
    "Data flow: the bench script calls `spin()` and prints the count.\n"
    "Diagram: bench -> turnstile\n\n"
    "## Poured concrete (one-way doors)\n"
    "- language %(D)s Python 3.9 %(D)s every caller imports it\n"
    "- ~~storage %(D)s a file %(D)s superseded~~\n\n"
    "## Deferred\n"
    "- a web view %(D)s the module has no I/O\n\n"
    "## Run log\n"
    "### Run 1 %(D)s 2026-09-21 %(D)s trigger: first run\n"
    "Exit ramp: system; the interview continued\n"
    "Step 3.1 (walkthrough target): Sam Bench, 2026-10-01, count and reset\n"
    "Step 3.2 (candidates): module; CLI. chosen: module; rejected: CLI %(D)s no need\n"
    "Step 3.3 (one-way doors): language settled\n"
    "Rulings: none\n"
    "Changed this run: first run\n") % {"D": D, "M": M}

BUILD_FILLED = (
    "# Turnstile %(D)s build plan (2026-09-22)\n\n"
    "Intent: count turns for the owner's bench rig.\n"
    "Constraints: Python 3.9 standard library; `python3 -m unittest`.\n"
    "Out of scope: a web dashboard %(D)s declined in the scope doc\n"
    "Plan: inspected 2026-09-23 by gpt-6-astra %(M)s 0 BLOCKER %(M)s 1 MAJOR %(M)s 0 MINOR\n\n"
    "## Slice A %(D)s Count turns\n"
    "Goal: `spin()` returns the count after one more turn.\n"
    "Requirements:\n"
    "- R1 %(D)s `spin(n)` returns `n + 1`\n"
    "Acceptance criteria:\n"
    "- AC1: `spin(2)` returns 3 %(D)s verify: new test at tests/test_turnstile.py\n"
    "Footprint: src/turnstile.py, tests/test_turnstile.py\n"
    "Not in this slice: the reset\n"
    "Depends on: nothing\n"
    "Status: in progress\n\n"
    "## Build assumptions\n"
    "- The bench rig runs Python 3.9 (assumed at build).\n"
    "## Deviations\n"
    "## Discovered\n"
    "## Handoffs\n"
    "## Punch list\n"
    "### 2026-09-23 %(D)s review: A\n"
    "- MAJOR %(M)s docs/plans/2026-09-22-turnstile.md:8 %(M)s the reset is named nowhere else %(M)s gpt-6-astra\n"
) % {"D": D, "M": M}

BUILD_PATH = "docs/plans/2026-09-22-turnstile.md"
SCOPE_PATH = "docs/scope/2026-09-20-turnstile.md"
ARCH_PATH = "docs/architecture/2026-09-21-turnstile.md"
SESSION = "session-test-1"


def base_files(scope=True, arch=False, build=None):
    files = {"README.md": "# Turnstile\n\nA bench-rig turn counter.\n",
             "src/turnstile.py": "def spin(count):\n    return count + 1\n"}
    if scope:
        files[SCOPE_PATH] = SCOPE
    if arch:
        files[ARCH_PATH] = ARCH
    if build is not None:
        files[BUILD_PATH] = build
    return files


def ledger_ids(text=SCOPE):
    return dict((row["text"], row["id"]) for row in ledger.read(text))


def clean_answer(run_id="run-0001", session=SESSION, feature="turnstile"):
    ids = ledger_ids()
    return {
        "answer_version": 1, "run_id": run_id, "session_id": session,
        "feature": feature, "title": "Turnstile",
        "intent": "count turns for the owner's bench rig, so a bench session reports its turns.",
        "questions": [{"id": "Q1", "text": "Where is the count kept between sessions?",
                       "touches": [ids["Where the count is kept between sessions"]],
                       "answer": "in memory only for the first version"}],
        "lines": [
            {"id": "R1", "tag": "requirement", "text": "R1 %s `spin(n)` returns `n + 1`" % D,
             "trace": {"kind": "repo_path", "ref": "src/turnstile.py"}},
            {"id": "R2", "tag": "requirement", "text": "R2 %s the count lives in memory only" % D,
             "trace": {"kind": "question", "ref": "Q1"}},
            {"id": "C1", "tag": "constraint", "text": "Python 3.9 standard library only",
             "trace": {"kind": "ledger", "ref": ids["Python 3.9 standard library only"]}},
            {"id": "O1", "tag": "out-of-scope", "text": "a web dashboard %s the owner declined it" % D,
             "trace": {"kind": "ledger", "ref": ids["a web dashboard %s the owner declined it" % D]}}],
        "criteria": [{"id": "AC1", "text": "AC1: `spin(2)` returns 3",
                      "verify": "new test at tests/test_turnstile.py"}],
        "slices": [{"name": "A", "short": "Count turns",
                    "goal": "`spin()` returns the count after one more turn.",
                    "requirements": ["R1", "R2"], "criteria": ["AC1"],
                    "footprint": ["src/turnstile.py", "tests/test_turnstile.py"],
                    "not_in_slice": "the reset", "depends_on": []}],
        "assumptions": ["the bench script prints the count itself"],
        "open_questions": ["how often the counter resets"],
        "ceremony": {"needs_build_doc": True, "why": "three requirements across one slice"},
    }


def extension_answer(run_id="run-0001", session=SESSION):
    """A second slice for BUILD_FILLED, traced to an answered question and a repo path."""
    return {
        "answer_version": 1, "run_id": run_id, "session_id": session,
        "feature": "turnstile", "title": "Turnstile", "intent": "count turns for the owner's bench rig.",
        "questions": [{"id": "Q1", "text": "Does reset return the old count?", "touches": [],
                       "answer": "no, it returns 0"}],
        "lines": [
            {"id": "R2", "tag": "requirement", "text": "R2 %s `reset()` returns 0" % D,
             "trace": {"kind": "question", "ref": "Q1"}},
            {"id": "C1", "tag": "constraint", "text": "Python 3.9 standard library",
             "trace": {"kind": "repo_path", "ref": "src/turnstile.py"}},
            {"id": "O2", "tag": "out-of-scope", "text": "a reverse-turn mode %s waiting on the encoder spec" % D,
             "trace": {"kind": "question", "ref": "Q1"}}],
        "criteria": [{"id": "AC2", "text": "AC2: `reset()` then `spin(0)` returns 1",
                      "verify": "new test at tests/test_turnstile.py"}],
        "slices": [{"name": "B", "short": "Reset the count", "goal": "`reset()` puts the count back to zero.",
                    "requirements": ["R2"], "criteria": ["AC2"], "footprint": ["src/turnstile.py"],
                    "not_in_slice": "persistence", "depends_on": ["A"]}],
        "assumptions": [], "open_questions": [],
        "ceremony": {"needs_build_doc": True, "why": "one more slice on the living doc"},
    }


class Run(object):
    """One run of the real driver over a fixture workspace."""

    def __init__(self, tmp, ws, run_id="run-0001", report_only=False, session=SESSION, name="run"):
        self.tmp, self.ws, self.run_id = tmp, ws, run_id
        self.run_dir = os.path.join(tmp, name)
        self.cwd = os.path.join(tmp, "elsewhere")
        os.makedirs(self.cwd, exist_ok=True)
        self.report_only = report_only
        self.session = session

    def cli(self, args, env=None):
        code, out, err = testlib.run_driver(args, cwd=self.cwd, env=env)
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        return code, doc, err

    def check_input(self, **extra):
        path = os.path.join(self.tmp, "input-%s.json" % self.run_id)
        doc = testlib.make_input(self.ws, self.run_dir, run_id=self.run_id, report_only=self.report_only,
                                 **extra)
        doc["invocation"]["session_id"] = self.session
        testlib.write_json(path, doc)
        code, out, err = self.cli(["check-input", path])
        assert code == 0, (code, out, err)
        return out

    def select(self, hunt, name=None):
        args = ["select", "--run-dir", self.run_dir, "--hunt", hunt]
        if name:
            args += ["--name", name]
        return self.cli(args)

    def select_all(self, feature="turnstile", scope_name=None, arch_name=None):
        for hunt, name in (("scope", scope_name), ("architecture", arch_name), ("build", feature)):
            code, out, err = self.select(hunt, name)
            assert code == 0, (hunt, code, out, err)

    def harvest(self):
        return self.cli(["harvest", "--run-dir", self.run_dir])

    def record(self, answer):
        path = os.path.join(self.tmp, "answer-%s.json" % self.run_id)
        testlib.write_json(path, answer)
        return self.cli(["record-answer", "--run-dir", self.run_dir, "--answer", path])

    def write(self):
        return self.cli(["write", "--run-dir", self.run_dir])

    def report(self):
        return self.cli(["report", "--run-dir", self.run_dir])

    def to_harvest(self, feature="turnstile", **select):
        self.check_input()
        self.select_all(feature=feature, **select)
        code, out, err = self.harvest()
        assert code == 0, (code, out, err)
        return out

    def listing(self):
        return sorted(os.listdir(self.run_dir))


def read(path):
    return testlib.read_text(path)


def sha256_text(text):
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
