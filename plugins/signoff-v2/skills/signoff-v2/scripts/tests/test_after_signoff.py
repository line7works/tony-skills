"""What happens to a document AFTER a signoff run: the seam amendment A4 repaired.

Before A4 the answer was "nothing good": the station's own rendered line read back as a second
raise of the finding that produced it, so the next levelling of that document stopped with exit
5 and neither a second signoff nor a `/recheck` could run. Both are proven here, end to end,
through the real CLIs and the real records component — no stubs, no fixture logs.

1. **A second signoff on one document.** A different run id, the reviewing session still
   independent. Its `scope` levels the log without a stop, the component's derived state still
   shows the first run's finding OPEN, a clean second answer records its verdict, and the log
   holds no duplicate `finding_raised` for the first run's finding.

2. **A `/recheck` after a signoff**, through the pilot's own `recheck.py start` in the same
   workspace, with a `{build_doc, slice}` target so the pilot reads its open set from the
   records rather than from a caller-held list. Nothing is imported twice, and the records half
   of the handover holds: the component's derived state carries one open MAJOR at the location
   the reviewer named, charged to the slice.

   The pilot half does NOT yet hold, and this suite says so rather than hiding it. The pilot
   reads the finding — it assembles `scope.checklist[0]` from it — and then refuses its own
   checkpoint because that item's `record.heading` is empty, because
   `recheck_core/records_view.py:_address` returns no heading for a NATIVE event. That is a
   different defect from the one A4 repaired, it lives in the pilot, which this lane may not
   write, and the test pins the observed refusal by name so the day it is closed it fails.
"""
import json
import os
import subprocess
import unittest

import testlib

DOC = "docs/plans/2026-09-18-signpost-rows.md"
LOG = "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl"
PILOT = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "recheck-v2", "skills",
                                      "recheck-v2", "scripts", "recheck.py"))


def log_events(workspace):
    path = os.path.join(workspace, LOG)
    if not os.path.isfile(path):
        return []
    return [json.loads(line) for line in testlib.read_text(path).split("\n") if line.strip()]


class ASignoffHasRun(unittest.TestCase):
    """S1-02 signed off once, with one MAJOR raised and the card moved."""

    CASE = "S1-02-untracked-defect"

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-after-")
        self.addCleanup(testlib.rmtree, self.dir)
        family = testlib.family_of(self.CASE)
        self.case = testlib.build_case(family, self.CASE, os.path.join(self.dir, family))
        self.workspace = os.path.join(self.case, "workspace")
        self.seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        self.first = self.signoff("first")

    def signoff(self, run_id, answer=None, report_only=False):
        run_dir = os.path.join(self.case, "run-%s" % run_id)
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": run_id,
                              "run_dir": run_dir, "run_date": "2026-09-21", "harness": None,
                              "sessions": self.seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": self.seeded["build_doc"], "slice": self.seeded["slice"],
                          "base": self.seeded["base"]},
               "report_only": report_only, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(self.case, "in-%s.json" % run_id), doc)
        answer = answer or os.path.join(self.case, "answer.json")
        for args in (["check-input", path], ["scope", "--run-dir", run_dir],
                     ["request", "--run-dir", run_dir],
                     ["record-answer", "--run-dir", run_dir, "--answer", answer]):
            code, body, err = testlib.signoff(args, env=self.env)
            self.assertEqual(code, 0, "%s: %s" % (args[0], err or json.dumps(body)))
        code, body, err = testlib.signoff(["record", "--run-dir", run_dir], env=self.env)
        self.assertEqual(code, 10, err or json.dumps(body))
        return body

    def records(self, *args):
        proc = subprocess.run(
            [testlib.GEN_PYTHON, os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")]
            + list(args),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")

    def state(self):
        code, out, err = self.records("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def raised_ids(self):
        return [e["finding"] for e in log_events(self.workspace) if e["kind"] == "finding_raised"]


class ASecondSignoffOnOneDocument(ASignoffHasRun):
    def test_the_first_run_left_one_open_finding(self):
        self.assertEqual(self.first["status"], "completed", json.dumps(self.first))
        state = self.state()
        self.assertEqual(state["counts"]["findings"], 1)
        self.assertEqual(state["counts"]["open"], 1)
        self.assertEqual(state["findings"][0]["status"], "open")
        self.assertEqual(state["findings"][0]["location"]["raw"], "src/signpost/pad.py:6")

    def test_a_second_run_levels_the_log_without_a_stop(self):
        run_dir = os.path.join(self.case, "run-second")
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "second",
                              "run_dir": run_dir, "run_date": "2026-09-22", "harness": None,
                              "sessions": self.seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": self.seeded["build_doc"], "slice": self.seeded["slice"],
                          "base": self.seeded["base"]},
               "report_only": False, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(self.case, "in-second.json"), doc)
        code, body, err = testlib.signoff(["check-input", path], env=self.env)
        self.assertEqual(code, 0, err)
        code, body, err = testlib.signoff(["scope", "--run-dir", run_dir], env=self.env)
        self.assertEqual(code, 0,
                         "the second run's levelling stopped: %s" % (err or json.dumps(body)))
        self.assertEqual(body["next"], "request")

    def test_a_clean_second_review_records_its_verdict_and_duplicates_nothing(self):
        before = self.raised_ids()
        self.assertEqual(len(before), 1)
        clean = testlib.write_json(os.path.join(self.case, "clean-answer.json"), {
            "seeded_answer": 1, "case": self.CASE, "role": "reviewer",
            "session_id": self.seeded["sessions"]["reviewing"],
            "checks_executed": [{"name": "unit", "command": "sh checks/unit.sh", "exit_code": 0,
                                 "output": "Ran 4 tests in 0.000s\n\nOK"}],
            "findings": [], "notes_kept": [], "verdict": "signed off",
            "notes": "The padder was read again and the unit check was run from the root."})
        second = self.signoff("second", answer=clean)
        self.assertEqual(second["status"], "completed", json.dumps(second))
        self.assertTrue(second["verdict_recorded"])
        self.assertEqual(second["verdict"], "signed off")
        self.assertEqual(self.raised_ids(), before,
                         "the second run raised the first run's finding again")

    def test_the_first_runs_block_is_still_the_only_one_for_its_finding(self):
        self.signoff("second", answer=testlib.write_json(
            os.path.join(self.case, "clean-answer.json"), {
                "seeded_answer": 1, "case": self.CASE, "role": "reviewer",
                "session_id": self.seeded["sessions"]["reviewing"],
                "checks_executed": [{"name": "unit", "command": "sh checks/unit.sh",
                                     "exit_code": 0, "output": "OK"}],
                "findings": [], "notes_kept": [], "verdict": "signed off", "notes": "clean"}))
        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertEqual(build_doc.count("src/signpost/pad.py:6"), 1,
                         "the finding's line appears more than once in the document")


class ARecheckAfterASignoff(ASignoffHasRun):
    """The loop's handover, through the pilot's own CLI."""

    def recheck(self, args, env=None):
        e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", RECORDS_ROOT=testlib.RECORDS_ROOT)
        if env:
            e.update(env)
        proc = subprocess.run([testlib.GEN_PYTHON, PILOT] + [str(a) for a in args], env=e,
                              cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        body = None
        if out.strip():
            try:
                body = json.loads(out)
            except ValueError:
                body = {"_raw": out}
        return proc.returncode, body, proc.stderr.decode("utf-8", "replace")

    def test_the_pilot_is_where_this_suite_expects_it(self):
        self.assertTrue(os.path.isfile(PILOT), PILOT)

    def test_the_records_half_of_the_handover_holds(self):
        """What signoff leaves for recheck, measured on the component's own derived state: one
        finding, open, at the location the reviewer named, charged to the slice."""
        state = self.state()
        self.assertEqual(state["counts"]["findings"], 1)
        self.assertEqual(state["open"]["MAJOR"], 1)
        self.assertEqual(state["findings"][0]["status"], "open")
        self.assertEqual(state["findings"][0]["location"]["raw"], "src/signpost/pad.py:6")
        self.assertEqual(state["findings"][0]["slice"], "D")

    def test_recheck_start_sees_the_signoffs_finding_as_its_open_set(self):
        run_dir = os.path.join(self.case, "recheck-run")
        os.makedirs(run_dir, exist_ok=True)
        supplied = testlib.write_json(os.path.join(self.case, "recheck-input.json"), {
            "protocol_version": 1,
            "invocation": {"mode": "headless", "caller": "signoff-v2-test",
                           "run_id": "recheck-after-signoff", "run_dir": run_dir,
                           "run_date": "2026-09-22",
                           "harness": {"name": "test-harness", "version": "0",
                                       "entry": "explicit path", "sandbox": "none"},
                           "model": {"id": "claude-opus-5", "floor_class": "opus",
                                     "floor_met": True}},
            "workspace": self.workspace,
            "target": {"build_doc": self.seeded["build_doc"], "slice": self.seeded["slice"]},
        })
        code, body, err = self.recheck(["start", supplied])
        self.assertIn(code, (0, 10), "recheck start failed: %s" % (err or json.dumps(body)))
        self.assertIsInstance(body, dict, err)

        if body.get("checklist"):
            # The seam works: the day the pilot accepts a natively raised finding, this branch
            # runs and the assertions below are the real ones.
            checklist = body["checklist"]
            flat = json.dumps([row.get("location") for row in checklist])
            self.assertIn("src/signpost/pad.py", flat, flat)
            self.assertEqual(len(checklist), 1,
                             "recheck saw %d items where the signoff raised 1: %s"
                             % (len(checklist), flat))
            return

        # KNOWN OPEN POINT, measured, not designed — and NOT what amendment A4 repaired.
        #
        # The pilot DOES read the signoff's finding out of the records: it assembles
        # `scope.checklist[0]` from it. It then refuses its own checkpoint because that item's
        # `record.heading` is empty. The cause is exact and is in the pilot, which this lane
        # may not write: `recheck_core/records_view.py:_address` returns no heading for any
        # NATIVE event — its own docstring says "a native event carries no document line" — and
        # the checkpoint schema requires a non-empty heading.
        #
        # Before A4 no station raised findings natively into a log the pilot reads, so this
        # could not surface; signoff-v2 is the first. The records half of the handover holds
        # (the test above), and a rendered line under a real heading sits in the document, so
        # the heading exists — it is simply not on the event.
        #
        # This test pins the observed refusal by name, the way the exit-5 pin did, so the day
        # the seam is closed it fails and says so.
        self.assertEqual(body.get("status"), "missing_input", json.dumps(body))
        chat = testlib.read_text(body["chat"])
        self.assertIn("scope.checklist[0].record.heading", chat,
                      "the refusal moved; re-read it before trusting this pin: %s" % chat)
        self.assertNotIn("scope.checklist[1]", chat,
                         "one finding was raised, so only item 0 can be named")
        self.assertIn("should be non-empty", chat)

    def test_the_handover_imported_nothing_twice(self):
        raised = self.raised_ids()
        self.assertEqual(len(raised), 1)
        code, out, err = self.records("import-legacy", "--workspace", self.workspace,
                                      "--doc", DOC, "--dry-run")
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["would_import"], 0, json.dumps(report))
        self.assertEqual(report["native_rendered"], 2,
                         "the review line and the `Status:` line the card moved")
        self.assertEqual(self.raised_ids(), raised)


if __name__ == "__main__":
    unittest.main()
