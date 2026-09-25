"""Fixtures and a run helper for architect-v2's own tests (lane A; not a shared file).

Every fixture is synthetic: a made-up bench-rig turn counter. A run is driven through the real
CLI (`scripts/architect.py`), from a working directory outside the worktree, with the date pinned
by the core's test hook (`ARCHITECT_V2_TEST=1`, `ARCHITECT_V2_TEST_TODAY`).
"""
import copy
import hashlib
import json
import os

import testlib

testlib.add_scripts_to_path()

from station_core import ledger  # noqa: E402

D = "\u2014"
M = "·"
TODAY = "2026-09-25"
SCOPE_REL = "docs/scope/2026-09-20-turnstile.md"
SCOPE = ("# Turnstile %(D)s scope doc (2026-09-20)\n\n"
         "Intent: a small turn counter for the bench rig, so one session can report how many turns a fixture made.\n"
         "Decisions:\n"
         "- Python 3.9 standard library only %(D)s decided (the owner's words: \"no dependencies on the bench\")\n"
         "- One module, no package %(D)s assumed (small and reversible; nothing imports it yet)\n"
         "- Where the count is kept between sessions %(D)s parked: needs research\n"
         "Out of scope: a web dashboard\n"
         "Research:\n"
         "Open:\n"
         "- how often the counter resets\n"
         "Next: /blueprint when ready.\n") % {"D": D}
MANDATE = ("You are the architect. Read the attached precon scope doc and return your own full "
           "architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component "
           "list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way "
           "decisions, and the deferred list. You have no other input; do not ask for any.")


def ids():
    rows = ledger.read(SCOPE)
    return {"decided": next(r["id"] for r in rows if r["tag"] == "decided"),
            "assumed": next(r["id"] for r in rows if r["tag"] == "assumed"),
            "parked": next(r["id"] for r in rows if r["tag"] == "parked"),
            "oos": next(r["id"] for r in rows if r["tag"] == "out-of-scope"),
            "open": next(r["id"] for r in rows if r["tag"] == "open"),
            "decided_text": next(r["text"] for r in rows if r["tag"] == "decided")}


def clean_answer(run_id="run-0001", session_id="session-test-1", **overrides):
    """A clean first-run answer against SCOPE."""
    i = ids()
    doc = {
        "answer_version": 1, "run_id": run_id, "session_id": session_id,
        "project": "Turnstile", "trigger": "first run", "changed": "first run",
        "questions": [
            {"id": "Q1", "text": "Is there a system here at all?", "touches": [], "answer": "yes, a system"},
            {"id": "Q2", "text": "Where is the count kept between sessions?", "touches": [i["parked"]],
             "answer": "in memory for v0"},
            {"id": "Q3", "text": "Who first touches it, and when?", "touches": [],
             "answer": "Sam Bench, on 2026-10-01, counting and resetting"},
            {"id": "Q4", "text": "Which candidate?", "touches": [], "answer": "the module"}],
        "exit_ramp": {"continued": True, "why": "the owner said yes, a system"},
        "walkthrough": {"who": "Sam Bench", "when": "2026-10-01", "must": ["count turns", "reset the count"],
                        "trace": {"kind": "question", "ref": "Q3"}},
        "candidates": [
            {"name": "module", "categories": ["platform:library"], "assumes": "the bench imports it",
             "later_cost": "a CLI later wraps it"},
            {"name": "service", "categories": ["platform:server", "storage:database"],
             "assumes": "a network on the bench", "later_cost": "hosting"}],
        "pick": "module",
        "rejected": [{"name": "service", "why": "the bench imports a module"}],
        "components": [{"name": "turnstile.py", "serves": "count turns"},
                       {"name": "reset()", "serves": "reset the count"}],
        "data_flow": "the fixture calls turnstile.py; reset() zeroes the count",
        "diagram": "fixture -> turnstile.py -> count",
        "doors": {"settled": "language, storage and platform settled for the full vision"},
        "poured_concrete": [
            {"text": "language %s Python 3.9 %s every bench script imports it" % (D, D), "tag": "decided",
             "trace": {"kind": "ledger", "ref": i["decided"]}},
            {"text": "storage %s none in v0 %s nothing is remembered" % (D, D), "tag": "decided",
             "trace": {"kind": "question", "ref": "Q2"}}],
        "deferred": [
            {"text": "a web dashboard %s door stays open because the module has no I/O" % D, "tag": "deferred",
             "trace": {"kind": "ledger", "ref": i["oos"]}}],
        "lines": [],
        "review": {"outcome": "pending"},
        "rulings": [],
        "publish": True,
        "publish_url": None,
    }
    doc.update(copy.deepcopy(overrides))
    return doc


def sha(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def listing(root):
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = os.path.join(base, name)
            out.append((os.path.relpath(full, root), sha(full)))
    return out


class ArchRun(object):
    """One run of the core, driven through the real CLI."""

    def __init__(self, tmp, workspace, staging=None, name="run", run_id="run-0001", **extra):
        self.tmp = tmp
        self.ws = workspace
        self.staging = staging
        self.run_id = run_id
        self.run_dir = os.path.join(tmp, name)
        self.cwd = os.path.join(tmp, "elsewhere")
        os.makedirs(self.cwd, exist_ok=True)
        self.extra = extra
        self.env = testlib.base_env({"ARCHITECT_V2_TEST": "1", "ARCHITECT_V2_TEST_TODAY": TODAY})

    def cli(self, *args):
        code, out, err = testlib.run_driver(list(args), cwd=self.cwd, env=self.env)
        doc = None
        if out.strip():
            try:
                doc = json.loads(out)
            except ValueError:
                doc = None
        return code, doc, out, err

    def input_doc(self):
        doc = testlib.make_input(self.ws, self.run_dir, **self.extra)
        doc["run_id"] = self.run_id
        if self.staging:
            doc["staging"] = self.staging
        return doc

    def check_input(self):
        path = os.path.join(self.tmp, "input-%s.json" % os.path.basename(self.run_dir))
        testlib.write_json(path, self.input_doc())
        return self.cli("check-input", path)

    def select(self, hunt, name=None):
        args = ["select", "--run-dir", self.run_dir, "--hunt", hunt]
        if name:
            args += ["--name", name]
        return self.cli(*args)

    def harvest(self):
        return self.cli("harvest", "--run-dir", self.run_dir)

    def to_harvest(self, slug="turnstile", scope=True):
        code, doc, out, err = self.check_input()
        assert code == 0, out + err
        if scope:
            code, doc, out, err = self.select("scope")
            assert code == 0, out + err
        code, doc, out, err = self.select("architecture", slug)
        assert code == 0, out + err
        return self.harvest()

    def record(self, answer):
        path = os.path.join(self.tmp, "answer-%s-%d.json" % (os.path.basename(self.run_dir), len(os.listdir(self.tmp))))
        testlib.write_json(path, answer)
        return self.cli("record-answer", "--run-dir", self.run_dir, "--answer", path)

    def write(self):
        return self.cli("write", "--run-dir", self.run_dir)

    def render(self):
        return self.cli("render-visual", "--run-dir", self.run_dir)

    def publish(self, url=None):
        args = ["record-publish", "--run-dir", self.run_dir]
        if url:
            args += ["--url", url]
        return self.cli(*args)

    def request(self, *rows, **kw):
        args = ["request", "--run-dir", self.run_dir]
        for row in rows:
            args += ["--row", row]
        if kw.get("roster"):
            args += ["--roster", kw["roster"]]
        if kw.get("session_model"):
            args += ["--session-model", kw["session_model"]]
        return self.cli(*args)

    def save_take(self, row, take_path, model="model-x", isolation="sandbox-enforced", sidecar="/tmp/sidecar.json"):
        return self.cli("save-take", "--run-dir", self.run_dir, "--row", row, "--take", take_path,
                        "--model", model, "--isolation", isolation, "--sidecar", sidecar)

    def report(self):
        return self.cli("report", "--run-dir", self.run_dir)

    def full(self, answer, url=None):
        """harvest done; record, write, render, publish (when url or publish), report."""
        steps = [self.record(answer), self.write(), self.render()]
        if answer.get("publish"):
            steps.append(self.publish(url))
        steps.append(self.report())
        return steps


def repo_workspace(tmp, files=None, name="ws"):
    base = {"README.md": "# Turnstile\n\nA bench-rig turn counter.\n", SCOPE_REL: SCOPE}
    base.update(files or {})
    return testlib.git_workspace(tmp, name, base)
