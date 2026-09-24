"""F8 (Astra's full review of E13, MAJOR): the dirty station loop, pinned as a documented gap.

Astra's `probe_seams.py` ran build -> signoff -> recheck on one document with NO commit between
the stations. Signoff's verdict doc under `docs/reviews/` (an authorized mirror) is left
UNTRACKED. Recheck appends its block to that mirror (write 5 of pilot-contract section 9), and
its boundary check reads any change to untracked content as a violation, so the run ends
`completed / not_clear`, the card stays at `signed off with conditions`, and the log says the
only finding is fixed. `probe_tracked_mirror.py`, the same loop with the mirror committed before
recheck, ends `all_clear` with the card at `signed off`. She found it inherited, not an E13-1
regression.

This module drives that loop through the REAL CLIs (build-v2 `build.py`, signoff-v2
`signoff.py`, this pilot's `recheck.py`) and the real records component, on one document, and
checks after EVERY station: the station's result, the slice's `Status:` card, the records
`state`, and a dry-run `import-legacy` that finds nothing new.

What `DirtyLoop` asserts is what the pilot does TODAY. It pins the qualification gap the pilot
contract documents (section 9, "The station loop"): E13 does not qualify the no-commit
signoff-to-recheck hand-off while the verdict mirror is untracked. Ruling E13-1 keeps what
recheck decides and stops on, so this assertion changes only on the owner's explicit ruling;
nothing here stages or commits anything in the worktree (the one commit, in `TrackedMirror`, is
in the test's own temporary fixture repository).
"""
import json
import os
import subprocess
import unittest

import testlib

PLUGINS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir))
BUILD = os.path.join(PLUGINS, "build-v2", "skills", "build-v2", "scripts", "build.py")
SIGNOFF = os.path.join(PLUGINS, "signoff-v2", "skills", "signoff-v2", "scripts", "signoff.py")
RECORDS_CLI = os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")

DOC = "docs/plans/2026-09-20-widget.md"
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
"""
MODEL = {"id": "claude-opus-5-5", "floor_class": "opus", "floor_met": True}
CLAIM = "spin() returns 0 whatever the number of turns"

GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.invalid",
           "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.invalid",
           "GIT_AUTHOR_DATE": "2026-09-19T09:00:00Z", "GIT_COMMITTER_DATE": "2026-09-19T09:00:00Z"}


def run(argv, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([testlib.GEN_PYTHON] + argv, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    try:
        body = json.loads(out) if out.strip() else None
    except ValueError:
        body = {"_raw": out}
    return proc.returncode, body, proc.stderr.decode("utf-8", "replace")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path, doc):
    write(path, json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return path


class _Loop(unittest.TestCase):
    """One workspace, one document, the three stations in order with no commit between."""

    COMMIT_MIRROR_BEFORE_RECHECK = False

    def setUp(self):
        self.dir = testlib.make_scratch("e13-f8-loop-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.ws = os.path.join(self.dir, "workspace")
        write(os.path.join(self.ws, ".gitignore"), "__pycache__/\n*.pyc\n")
        write(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 0\n")
        write(os.path.join(self.ws, "src", "other.py"), "VALUE = 1\n")
        write(os.path.join(self.ws, "checks", "unit.sh"), "#!/bin/sh\necho ok\n")
        write(os.path.join(self.ws, DOC), BUILD_DOC)
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("tag", "base")
        # the slice's work, left uncommitted: the loop is dirty from the first station
        write(os.path.join(self.ws, "src", "widget.py"),
              "def spin(turns=0):\n    return turns\n")

    # ---- helpers ----------------------------------------------------------------------------

    def git(self, *args):
        env = dict(os.environ, **GIT_ENV)
        proc = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c",
                               "commit.gpgsign=false"] + list(args), cwd=self.ws, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        return proc.stdout.decode("utf-8")

    def card(self):
        with open(os.path.join(self.ws, DOC), encoding="utf-8") as fh:
            for line in fh.read().split("\n"):
                if line.startswith("Status:"):
                    return line[len("Status:"):].strip()
        return None

    def records(self, *args):
        code, body, err = run([RECORDS_CLI] + list(args), self.dir)
        self.assertEqual(code, 0, "%s: %s %s" % (args[0], json.dumps(body), err))
        return body

    def state(self):
        return self.records("state", "--workspace", self.ws, "--doc", DOC)

    def assert_no_news(self, station):
        """A dry-run levelling after the station finds nothing to import."""
        body = self.records("import-legacy", "--workspace", self.ws, "--doc", DOC, "--dry-run")
        self.assertEqual(body.get("would_import"), 0,
                         "after %s the dry-run import found news: %s" % (station, json.dumps(body)))
        return body

    def open_findings(self, state):
        return [f for f in (state.get("findings") or []) if f.get("status") == "open"]

    # ---- station 1: build -------------------------------------------------------------------

    def build(self):
        run_dir = os.path.join(self.dir, "build-run")
        inp = write_json(os.path.join(self.dir, "build-input.json"), {
            "input_version": 1, "run_id": "f8-build-1", "workspace": self.ws, "run_dir": run_dir,
            "build_doc": DOC, "slice": "A", "base": "base",
            "invocation": {"harness": "test-harness", "caller": "user", "mode": "direct"}})
        answer = write_json(os.path.join(self.dir, "build-answer.json"), {
            "seeded_answer": 1, "case": "f8", "role": "executor", "session_id": "sess-build-1",
            "claimed_status": "complete", "claimed_card": "built",
            "edits": [{"path": "src/widget.py", "reason": "R1"}],
            "checks": [{"name": "unit", "command": "sh checks/unit.sh", "result": "passed",
                        "exit_code": 0, "output": "ok"}],
            "notes": "one file touched"})
        for argv in (["check-input", inp], ["contract", "--run-dir", run_dir],
                     ["preflight", "--run-dir", run_dir],
                     ["record-answer", "--run-dir", run_dir, "--answer", answer]):
            code, body, err = run([BUILD] + argv, self.dir)
            self.assertEqual(code, 0, "build %s: %s %s" % (argv[0], json.dumps(body), err))
        code, body, err = run([BUILD, "report", "--run-dir", run_dir], self.dir)
        self.assertEqual(code, 10, "build report: %s %s" % (json.dumps(body), err))
        return testlib.load_json(os.path.join(run_dir, "result.json"))

    # ---- station 2: signoff -----------------------------------------------------------------

    def signoff(self):
        run_dir = os.path.join(self.dir, "signoff-run")
        inp = write_json(os.path.join(self.dir, "signoff-input.json"), {
            "protocol_version": 1,
            "invocation": {"mode": "headless", "caller": "test", "run_id": "f8-signoff-1",
                           "run_dir": run_dir, "run_date": "2026-09-21",
                           "harness": "test-harness",
                           "sessions": {"building": "sess-build-1", "reviewing": "sess-review-1"},
                           "model": dict(MODEL)},
            "workspace": self.ws,
            "target": {"build_doc": DOC, "slice": "A", "base": "base"},
            "report_only": False,
            "review": {"depth": "LEAN", "route": "readers:claude-session"}})
        answer = write_json(os.path.join(self.dir, "signoff-answer.json"), {
            "role": "reviewer", "session_id": "sess-review-1", "model": MODEL["id"],
            "checks_executed": [{"name": "unit", "command": "sh checks/unit.sh", "exit_code": 0,
                                 "output": "ok"}],
            "findings": [{"location": "src/widget.py:2", "severity": "MAJOR", "claim": CLAIM,
                          "scenario": "call spin(3) and read the return value; it is not 3 "
                                      "when turns is passed positionally as a string",
                          "evidence_kind": "read"}],
            "verdict": "signed off with conditions",
            "notes": "Read the slice's one source file."})
        for argv in (["check-input", inp], ["scope", "--run-dir", run_dir],
                     ["request", "--run-dir", run_dir],
                     ["record-answer", "--run-dir", run_dir, "--answer", answer]):
            code, body, err = run([SIGNOFF] + argv, self.dir)
            self.assertEqual(code, 0, "signoff %s: %s %s" % (argv[0], json.dumps(body), err))
        code, body, err = run([SIGNOFF, "record", "--run-dir", run_dir], self.dir)
        self.assertEqual(code, 10, "signoff record: %s %s" % (json.dumps(body), err))
        return testlib.load_json(os.path.join(run_dir, "result.json"))

    # ---- station 3: recheck -----------------------------------------------------------------

    def recheck(self):
        run_dir = os.path.join(self.dir, "recheck-run")
        inp = write_json(os.path.join(self.dir, "recheck-input.json"), {
            "protocol_version": 1,
            "invocation": {"mode": "interactive", "caller": "direct", "resume": False,
                           "run_id": "f8-recheck-1", "run_dir": run_dir,
                           "harness": dict(testlib.HARNESS), "model": dict(testlib.MODEL),
                           "run_date": "2026-09-21"},
            "target": {"build_doc": DOC, "slice": "A"},
            "workspace": self.ws})
        code, doc, err = testlib.recheck(["start", inp], cwd=self.dir)
        self.assertEqual(code, 0, "recheck start: %s %s" % (json.dumps(doc), err))
        self.assertEqual([item["claim"] for item in doc["checklist"]], [CLAIM], doc)
        items = [{"index": i, "disposition": "fixed", "method": "executed",
                  "location": "%s:%s" % (it["location"]["file"], it["location"]["line"])}
                 for i, it in enumerate(doc["checklist"])]
        testlib.write_report(run_dir, testlib.canned_report(items))
        code, body, err = testlib.recheck(
            ["record-call", "--run-dir", run_dir, "--call-id", doc["call_id"], "--status", "ok",
             "--raw", os.path.join(run_dir, "verifier", "raw.md"), "--kind", "subagent",
             "--model", testlib.MODEL["id"]], cwd=self.dir)
        self.assertEqual(code, 0, "record-call: %s %s" % (json.dumps(body), err))
        for i in range(len(items)):
            code, body, err = testlib.recheck(["adjudicate", "--run-dir", run_dir, "--item",
                                               str(i), "--action", "confirmed"], cwd=self.dir)
            self.assertEqual(code, 0, "adjudicate: %s %s" % (json.dumps(body), err))
        code, body, err = testlib.recheck(["record", "--run-dir", run_dir], cwd=self.dir)
        self.assertEqual(code, 10, "recheck record: %s %s" % (json.dumps(body), err))
        return testlib.load_json(os.path.join(run_dir, "result.json"))

    # ---- the loop ---------------------------------------------------------------------------

    def first_two_stations(self):
        built = self.build()
        self.assertEqual(built["status"], "completed", json.dumps(built)[:1500])
        self.assertTrue(built["card"]["moved"])
        self.assertEqual(self.card(), "built")
        self.assertEqual(self.open_findings(self.state()), [])
        self.assert_no_news("build")

        signed = self.signoff()
        self.assertEqual(signed["status"], "completed", json.dumps(signed)[:2000])
        self.assertTrue(signed["verdict_recorded"])
        self.assertEqual(signed["verdict"], "signed off with conditions")
        self.assertEqual(self.card(), "signed off with conditions")
        opened = self.open_findings(self.state())
        self.assertEqual([f.get("claim") for f in opened], [CLAIM], opened)
        self.assert_no_news("signoff")
        mirror = signed["verdict_doc"]
        self.assertTrue(mirror.startswith("docs/reviews/"), mirror)
        self.assertIn("?? %s" % mirror, self.git("status", "--porcelain", "--untracked-files=all"),
                      "signoff leaves its verdict mirror untracked")
        return mirror


class DirtyLoop(_Loop):
    """The no-commit loop: the documented gap (pilot-contract section 9, "The station loop")."""

    def test_recheck_freezes_on_the_untracked_verdict_mirror(self):
        self.first_two_stations()
        result = self.recheck()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:2000])
        self.assertEqual(result["result"], "not_clear", json.dumps(result)[:2000])
        violations = " ".join(result.get("boundary_violations") or [])
        self.assertIn("untracked content changed during the transaction", violations)
        # the card did not move, though the log now says the finding is fixed
        self.assertEqual(self.card(), "signed off with conditions")
        state = self.state()
        self.assertEqual(self.open_findings(state), [], json.dumps(state)[:2000])
        self.assertEqual([(f.get("claim"), f.get("status")) for f in state.get("findings") or []],
                         [(CLAIM, "fixed")], "the log records the finding fixed")
        self.assert_no_news("recheck")


class TrackedMirror(_Loop):
    """The control: the verdict mirror committed before recheck, in the fixture repository."""

    def test_recheck_clears_once_the_mirror_is_tracked(self):
        self.first_two_stations()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "track the verdict mirror")
        self.assert_no_news("the commit")
        result = self.recheck()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:2000])
        self.assertEqual(result["result"], "all_clear", json.dumps(result)[:2000])
        self.assertEqual(result.get("boundary_violations") or [], [])
        self.assertEqual(self.card(), "signed off")
        self.assertEqual(self.open_findings(self.state()), [])
        self.assert_no_news("recheck")


if __name__ == "__main__":
    unittest.main()
