"""Fixtures for handoff-v2's own tests (not a back-frame file): a synthetic build in a git work tree.

Every fixture is built under a temporary directory and removed; git runs only there, with a fixed author and
date (`testlib.git`). The build is a made-up bench-rig turn counter. A records log is written through the
records component's own CLI (`import-legacy`), never by hand.

    build_doc(slices=..., punch=..., handoffs=..., ...) -> the build doc's text
    make_repo(tmp, doc_text, records=False, dirt=None, ...) -> (workspace, info)
    Driver(tmp) -> a callable running this core's CLI with the test hooks on: (exit, document or None, stderr)
    start(tmp, ws, ...) -> (driver, run_dir) after check-input
    through_gate(drive, tmp, run_dir, ...) -> the gate's document, after select and photograph
"""
import hashlib
import json
import os
import subprocess
import sys

import testlib

D = "\u2014"                    # the dash of the v1 forms; carried as an escape, never typed
M = "\u00b7"
DOC = "docs/plans/2026-09-20-turnstile.md"
FEATURE = "turnstile"
NOW = "2026-10-04T12:00:00Z"
TODAY = NOW[:10]
PREFIX = "HANDOFF_V2"
HEADING = "### %s " + D + " handoff"


def slice_lines(name, short, status, depends="nothing", questions=None):
    lines = ["## Slice %s %s %s" % (name, D, short), "Goal: one sentence about %s." % short,
             "Requirements:", "- R1 %s the %s counts every turn" % (D, short), "Acceptance criteria:",
             "- AC1: a turn adds one %s verify: new test at tests/test_turnstile.py" % D,
             "Footprint: src/turnstile.py", "Not in this slice: the encoder"]
    if depends is not None:
        lines.append("Depends on: %s" % depends)
    for question in questions or []:
        lines.append("Questions: %s" % question)
    if status is not None:
        lines.append("Status: %s" % status)
    return lines


def review_block(date="2026-09-24", slice_name="A", findings=None):
    findings = findings if findings is not None else [("MAJOR", "src/turnstile.py:2", "the counter skips a turn",
                                                       "a double tap loses one")]
    lines = ["", "### %s %s review: Slice %s" % (date, D, slice_name)]
    for severity, location, claim, scenario in findings:
        lines.append("- %s %s %s %s %s %s %s %s Slice %s review" % (severity, M, location, M, claim, M, scenario, M,
                                                                    slice_name))
    return lines


def handoff_block(date="2026-09-25", lines=None):
    return ["", HEADING % date] + list(lines or ["- Next: /ship-v2 B %s" % DOC, "- Perishable: the bench clock drifts"])


def build_doc(slices=None, punch=None, handoffs=None, with_handoffs=True, with_punch=True, extra_sections=None,
              title=None):
    """The build doc's text. `slices`: [(name, short, status, depends, questions)] (status None omits the line);
    `punch`: lines under `## Punch list`; `handoffs`: lines under `## Handoffs`."""
    slices = slices if slices is not None else [("A", "the counter", "signed off", "nothing", None),
                                                ("B", "the spinner", "not started", "Slice A", None)]
    lines = [title or "# Turnstile %s build plan (2026-09-20)" % D, "",
             "Intent: a small turn counter for the bench rig, so one bench session reports its turns.",
             "Constraints: Python 3.9 standard library only; test command `python3 -m unittest`.",
             "Out of scope: a web dashboard %s the owner declined it for the first version" % D]
    for row in slices:
        name, short, status = row[:3]
        depends = row[3] if len(row) > 3 else "nothing"
        questions = row[4] if len(row) > 4 else None
        lines += [""] + slice_lines(name, short, status, depends, questions)
    lines += ["", "## Build assumptions", "- the bench clock is monotonic", "## Deviations", "## Discovered"]
    for section in extra_sections or []:
        lines += section
    if with_handoffs:
        lines += ["## Handoffs"] + list(handoffs or [])
    if with_punch:
        lines += ["## Punch list"] + list(punch or [])
    return "\n".join(lines) + "\n"


BASE_FILES = {
    "README.md": "# Turnstile\n\nA bench-rig turn counter.\n",
    "src/turnstile.py": "def spin(count):\n    return count\n",
}


def make_repo(tmp, doc_text=None, records=False, dirt=None, extra_files=None, on_main=False, name="workspace",
              doc=DOC):
    ws = testlib.git_workspace(tmp, name, dict(BASE_FILES))
    base = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
    if not on_main:
        testlib.git(ws, ["checkout", "-q", "-b", "feat"])
    files = {"src/turnstile.py": "def spin(count):\n    return count + 1\n",
             doc: doc_text if doc_text is not None else build_doc()}
    files.update(extra_files or {})
    for rel, text in sorted(files.items()):
        testlib.write_text(os.path.join(ws, rel), text)
    testlib.git(ws, ["add", "-A"])
    testlib.git(ws, ["commit", "-q", "-m", "the build"], when="2026-09-20T10:00:00-07:00")
    if records:
        import_log(ws, doc)
        testlib.git(ws, ["add", "-A"])
        testlib.git(ws, ["commit", "-q", "-m", "the records log"], when="2026-09-20T11:00:00-07:00")
    for rel, text in sorted((dirt or {}).items()):
        testlib.write_text(os.path.join(ws, rel), text)
    head = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
    return ws, {"base": base, "head": head, "doc": doc}


def records_cli(ws, args):
    root = testlib.records_root()
    proc = subprocess.run([sys.executable, os.path.join(root, "scripts", "records.py")] + args,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ws, env=testlib.base_env())
    if proc.returncode != 0:
        raise RuntimeError("records %s exited %d: %s %s" % (args[0], proc.returncode, proc.stdout.decode()[-600:],
                                                            proc.stderr.decode()[-600:]))
    return json.loads(proc.stdout.decode())


def import_log(ws, doc=DOC):
    return records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", doc])


def state(ws, doc=DOC):
    return records_cli(ws, ["state", "--workspace", ws, "--doc", doc])


def log_path(ws, doc=DOC):
    slug = doc[:-3].replace("%", "%25").replace("_", "%5F").replace("/", "__")
    return os.path.join(ws, "docs", "records", slug + ".events.jsonl")


def jsonschema_here():
    testlib.add_scripts_to_path()
    from station_core import validate
    return not validate.jsonschema_unavailable("HLIB")


def records_usable():
    return testlib.records_root() is not None and jsonschema_here()


def env(extra=None):
    out = {PREFIX + "_TEST": "1", PREFIX + "_TEST_NOW": NOW}
    out.update(extra or {})
    return testlib.base_env(out)


class Driver(object):
    """This core's CLI, with the test hooks on; every call from a scratch working directory."""

    def __init__(self, tmp, extra_env=None):
        self.tmp = tmp
        self.env = env(extra_env)

    def __call__(self, args):
        code, out, err = testlib.run_driver(args, cwd=self.tmp, env=self.env)
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        return code, doc, err


def make_input(ws, run_dir, harness="claude-code", report_only=False, **station):
    doc = testlib.make_input(ws, run_dir)
    doc["invocation"]["harness"] = harness
    doc["station"] = dict(station)
    if report_only:
        doc["report_only"] = True
    return doc


def start(tmp, ws, run="run", harness="claude-code", report_only=False, **station):
    """check-input for a fresh run; returns (driver, run_dir)."""
    run_dir = os.path.join(tmp, run)
    doc = make_input(ws, run_dir, harness=harness, report_only=report_only, **station)
    doc["run_id"] = run
    path = os.path.join(tmp, run + "-input.json")
    testlib.write_json(path, doc)
    drive = Driver(tmp)
    code, out, err = drive(["check-input", path])
    if code != 0:
        raise AssertionError("check-input exited %d: %s %s" % (code, out, err))
    return drive, run_dir


def questions_file(tmp, run_dir, questions=(), name="questions.json"):
    path = os.path.join(tmp, name)
    testlib.write_json(path, {"answer_version": 1, "kind": "questions", "run_id": os.path.basename(run_dir),
                              "questions": [dict(q) for q in questions]})
    return path


def answers_file(tmp, run_dir, answers=(), perishables=(), asserts=None, name="answers.json"):
    path = os.path.join(tmp, name)
    doc = {"answer_version": 1, "kind": "answers", "run_id": os.path.basename(run_dir),
           "answers": [dict(a) for a in answers], "perishables": list(perishables)}
    if asserts is not None:
        doc["asserts"] = asserts
    testlib.write_json(path, doc)
    return path


def through_gate(test, drive, tmp, run_dir, questions=(), name=FEATURE, doc=None, records_root=None):
    args = ["select", "--run-dir", run_dir] + (["--doc", doc] if doc else ["--name", name])
    code, out, err = drive(args)
    test.assertEqual(code, 0, (out, err))
    code, out, err = drive(["photograph", "--run-dir", run_dir])
    test.assertEqual(code, 0, (out, err))
    code, out, err = drive(["gate", "--run-dir", run_dir, "--questions", questions_file(tmp, run_dir, questions)])
    test.assertEqual(code, 0, (out, err))
    return out


def through_write(test, drive, tmp, run_dir, answers=(), perishables=(), questions=(), asserts=None):
    gate = through_gate(test, drive, tmp, run_dir, questions=questions)
    code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer",
                            answers_file(tmp, run_dir, answers, perishables, asserts)])
    test.assertEqual(code, 0, (out, err))
    code, out, err = drive(["write", "--run-dir", run_dir])
    test.assertEqual(code, 0, (out, err))
    return gate, out


def sha(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def snapshot(ws, run_dir=None, extra=()):
    """The hashes the sanctioned-write tests compare: the doc, the log, the run's pointer output, the git HEAD and
    every file of the work tree, plus any extra path."""
    out = {"doc": sha(os.path.join(ws, DOC)), "log": sha(log_path(ws)), "tree": testlib.tree_digest(ws)}
    try:
        out["head"] = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
        out["commits"] = testlib.git(ws, ["rev-list", "--count", "HEAD"]).strip()
    except RuntimeError:
        out["head"] = out["commits"] = None
    if run_dir is not None:
        out["pointer"] = sha(os.path.join(run_dir, "pointer.json"))
    for path in extra:
        out[path] = testlib.tree_digest(path) if os.path.isdir(path) else sha(path)
    return out


def read_doc(ws, doc=DOC):
    return testlib.read_text(os.path.join(ws, doc))


def events(ws, doc=DOC):
    path = log_path(ws, doc)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
