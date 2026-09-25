"""Fixtures and drivers for precon-v2's own tests (lane P; not a shared file).

Every fixture is built under a temporary directory and removed by the caller's cleanup. The
content is the made-up bench-rig turn counter the seeded cases use; nothing here is copied from
another repository. The dash of the v1 scope-doc form is carried as an escape, never typed.
"""
import json
import os

import testlib

D = chr(0x2014)
IDEA = "turnstile"
DATE = "2026-09-20"
SCOPE_REL = "docs/scope/%s-%s.md" % (DATE, IDEA)

SCOPE_DOC = (
    "# Turnstile %(D)s scope doc (2026-09-20)\n"
    "\n"
    "Intent: a small turn counter for the owner's bench rig, so one bench session can report how many turns a fixture made.\n"
    "Decisions:\n"
    "- Python 3.9 standard library only %(D)s decided (the owner's words: \"no dependencies on the bench\")\n"
    "- One module, no package %(D)s assumed (small and reversible; nothing imports it yet)\n"
    "- Where the count is kept between sessions %(D)s parked: needs research\n"
    "- A second counting mode for reverse turns %(D)s parked: waiting on the bench rig's encoder spec\n"
    "Out of scope: a web dashboard %(D)s the owner declined it for the first version\n"
    "Research:\n"
    "Open:\n"
    "- how often the counter resets\n"
    "Next: /blueprint when ready.\n"
) % {"D": D}

# the ledger ids of SCOPE_DOC (station_core/ledger.py: section, then the item text)
DECIDED_ID = "dec-4858c7412180"
ASSUMED_ID = "dec-d1a443ce9edb"
PARKED_RESEARCH_ID = "dec-e4907eb8a1ce"
PARKED_WAITING_ID = "dec-95c8bc68ce67"
OPEN_ID = "open-7e7c35c7b17c"
OOS_ID = "oos-936fd940e2a6"


def ids(text=SCOPE_DOC):
    """{tag or item text: id} for a doc, read through the real ledger reader."""
    testlib.add_scripts_to_path()
    from station_core import ledger
    out = {}
    for row in ledger.read(text):
        out[row["text"]] = row["id"]
    return out


class Fixture(object):
    """A workspace (a git work tree), a staging home and a run directory under one scratch."""

    def __init__(self, tmp, files=None, staging_files=None, git=True):
        self.tmp = tmp
        self.cwd = os.path.join(tmp, "elsewhere")
        os.makedirs(self.cwd, exist_ok=True)
        files = dict(files if files is not None else {"README.md": "# Turnstile\n\nA bench-rig turn counter.\n",
                                                      "src/turnstile.py": "def spin(count):\n    return count + 1\n"})
        if git:
            self.ws = testlib.git_workspace(tmp, "ws", files)
        else:
            self.ws = os.path.join(tmp, "ws")
            os.makedirs(self.ws)
            for rel, text in files.items():
                testlib.write_text(os.path.join(self.ws, rel), text)
        self.staging = os.path.join(tmp, "staging")
        os.makedirs(self.staging, exist_ok=True)
        for rel, text in (staging_files or {}).items():
            testlib.write_text(os.path.join(self.staging, rel), text)
        self.runs = os.path.join(tmp, "runs")
        os.makedirs(self.runs, exist_ok=True)
        self.count = 0

    def cli(self, args, env=None):
        return testlib.run_driver(args, cwd=self.cwd, env=env)

    def new_run(self, station=None, report_only=False, owner_word=None, run_id=None, session_id="session-test-1",
                staging=True):
        self.count += 1
        run_id = run_id or "run-%04d" % self.count
        run_dir = os.path.join(self.runs, run_id)
        extra = {"run_id": run_id, "station": dict({"date": DATE}, **(station or {}))}
        if staging:
            extra["staging"] = self.staging
        if report_only:
            extra["report_only"] = True
        if owner_word is not None:
            extra["owner_word"] = owner_word
        doc = testlib.make_input(self.ws, run_dir, **extra)
        doc["invocation"]["session_id"] = session_id
        path = os.path.join(self.tmp, "input-%s.json" % run_id)
        testlib.write_json(path, doc)
        code, out, err = self.cli(["check-input", path])
        if code != 0:
            raise AssertionError("check-input exit %d: %s%s" % (code, out, err))
        return Run(self, run_id, run_dir, doc)


class Run(object):

    def __init__(self, fixture, run_id, run_dir, doc):
        self.fx = fixture
        self.run_id = run_id
        self.run_dir = run_dir
        self.input = doc

    def cli(self, args, env=None):
        return self.fx.cli(args, env=env)

    def phase(self, name, *extra):
        return self.cli([name, "--run-dir", self.run_dir] + list(extra))

    def select(self, hunt="scope", name=IDEA):
        args = ["select", "--run-dir", self.run_dir, "--hunt", hunt]
        if name:
            args += ["--name", name]
        code, out, err = self.cli(args)
        if code != 0:
            raise AssertionError("select exit %d: %s%s" % (code, out, err))
        return json.loads(out)

    def harvest(self):
        code, out, err = self.phase("harvest")
        return code, (json.loads(out) if out.strip() else None), err

    def record(self, answer):
        path = os.path.join(self.fx.tmp, "answer-%s.json" % self.run_id)
        testlib.write_json(path, answer)
        code, out, err = self.phase("record-answer", "--answer", path)
        return code, (json.loads(out) if out.strip() else None), err

    def write(self):
        code, out, err = self.phase("write")
        return code, (json.loads(out) if out.strip() else None), err

    def report(self):
        code, out, err = self.phase("report")
        return code, (json.loads(out) if out.strip() else None), err

    def state(self):
        code, out, err = self.phase("state")
        return code, (json.loads(out) if out.strip() else None), err

    def run_file(self, name):
        return os.path.join(self.run_dir, name)


def answer(run, **fields):
    """A clean answer for `run`: nothing asked, nothing asserted, a gate line, the sitting ends."""
    doc = {"answer_version": 1, "run_id": run.run_id,
           "session_id": run.input["invocation"].get("session_id"),
           "triage": {"tier": "bounded", "why": "a normal feature with known edges"},
           "questions": [], "lines": [], "out_of_scope": [], "research": [], "open_items": [],
           "sitting": "ends",
           "gate": "every branch was visited or parked: storage parked for research, the rest decided"}
    doc.update(fields)
    return doc


def new_doc_fields():
    return {"title": "Turnstile",
            "intent": "a small turn counter for the owner's bench rig, so one bench session can report how many turns a fixture made."}


def owner_line(text, words):
    return {"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": words}}


def ensure_scope_doc(fx, text=SCOPE_DOC, rel=SCOPE_REL, staged=False):
    root = fx.staging if staged else fx.ws
    path = os.path.join(root, rel)
    testlib.write_text(path, text)
    return path


def read(path):
    return testlib.read_text(path)
