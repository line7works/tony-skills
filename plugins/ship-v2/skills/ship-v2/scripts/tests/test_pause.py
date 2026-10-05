"""CR-23's pause and CR-24's one sanctioned write (contract sections 3.7 and 6).

A station's question to the owner is a pause: passed through verbatim, never answered by the script, never turned
into a stop; the run waits with nothing written outside its run directory (the trace untouched: a pause is no
visit), and every phase but the answer is refused while it waits. The owner's answer resumes the run where it
paused; a waiver or a reopening in his answer is the one write ship-v2 makes: a `waived` or `reopened` event through
`records.py append`, carrying his words verbatim (planned, never appended, on a report-only run).
"""
import os
import unittest

import slib
import testlib


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class ThePause(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-pause-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)

    def begin(self, report_only=False):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws, report_only=report_only)
        slib.through_hook(self, drive, self.tmp, run_dir)
        return drive, run_dir

    def test_a_station_question_is_passed_through_verbatim_and_nothing_is_written(self):
        drive, run_dir = self.begin()
        code, visit, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        question = "The slice carries an open BLOCKER at src/turnstile.py:2. Build on it anyway? (yes/no)"
        before = (slib.trace(run_dir), slib.snapshot(self.ws))
        code, out, err = drive(["pause", "--run-dir", run_dir, "--question",
                                slib.question_file(self.tmp, run_dir, question, station="build-v2")])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["question"], question)
        self.assertEqual(out["next"], "pause --answer")
        self.assertNotIn("stop_tag", out)
        self.assertNotIn("chat", out)
        self.assertEqual(before, (slib.trace(run_dir), slib.snapshot(self.ws)),
                         "the pause writes nothing outside the run directory and adds no trace line")
        for args in (["report", "--run-dir", run_dir, "--bottom-line", "The owner did not answer."],
                     ["visit", "--run-dir", run_dir, "--result"],
                     ["lap", "--run-dir", run_dir],
                     ["visit", "--run-dir", run_dir, "--station", "signoff-v2"]):
            code, out, err = drive(args)
            self.assertEqual(code, 2, (args, out, err))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "result.json")), "a pause never ends the run")
        code, out, err = drive(["pause", "--run-dir", run_dir, "--answer",
                                slib.answer_file(self.tmp, run_dir, 1, "yes, build on it")])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "visit --result")
        self.assertEqual(before, (slib.trace(run_dir), slib.snapshot(self.ws)))
        slib.put_result(visit, slib.station_result("build-v2", "completed", visit, self.ws))
        code, out, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual((code, out["next"]), (0, "visit --station signoff-v2"), (out, err))
        pauses = testlib.load_json(os.path.join(run_dir, "pauses.json"))["pauses"]
        self.assertEqual((pauses[0]["question"]["text"], pauses[0]["answer"]["words"]), (question, "yes, build on it"))

    def test_an_answer_needs_the_owners_words(self):
        drive, run_dir = self.begin()
        drive(["pause", "--run-dir", run_dir, "--question", slib.question_file(self.tmp, run_dir, "Which mode?")])
        for pause, words in ((1, " "), (2, "the second")):
            code, out, err = drive(["pause", "--run-dir", run_dir, "--answer",
                                    slib.answer_file(self.tmp, run_dir, pause, words)])
            self.assertIn(code, (4, 5), (pause, words, out, err))

    def through_findings(self, drive, run_dir):
        slib.visit(self, drive, run_dir, "build-v2", "completed", self.ws)
        finding = slib.raise_finding(self.tmp, self.ws)
        code, out, err = slib.visit(self, drive, run_dir, "signoff-v2", "findings", self.ws)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        return finding

    def waive(self, drive, run_dir, finding, words, kind="waive"):
        code, out, err = drive(["pause", "--run-dir", run_dir, "--question", slib.question_file(
            self.tmp, run_dir, "Only you can rule the MAJOR at %s: waive it or hold?" % slib.MAJOR_AT, source="ship",
            station=None, finding=finding)])
        self.assertEqual(code, 0, (out, err))
        return drive(["pause", "--run-dir", run_dir, "--answer", slib.answer_file(
            self.tmp, run_dir, out["pause"], words, {"kind": kind, "finding": finding})])

    def test_a_mid_run_waiver_is_a_waived_event_with_the_owners_words(self):
        drive, run_dir = self.begin()
        finding = self.through_findings(drive, run_dir)
        words = "Waive it, the double tap is a bench quirk"
        before = len(slib.log_lines(self.ws))
        code, out, err = self.waive(drive, run_dir, finding, words)
        self.assertEqual(code, 0, (out, err))
        added = slib.log_lines(self.ws)[before:]
        self.assertEqual([e["kind"] for e in added], ["waived"])
        event = added[0]
        self.assertEqual((event["finding"], event["words"], event["actor"]["station"]), (finding, words, "ship-v2"))
        self.assertEqual(event["actor"]["run_id"], "run")
        self.assertEqual(event["grant_date"], slib.TODAY)
        self.assertEqual(out["next"], "fix")
        self.assertEqual(next(f for f in slib.state(self.ws)["findings"] if f["id"] == finding)["status"], "waived")

    def test_a_mid_run_reopening_is_a_reopened_event_with_the_owners_words(self):
        drive, run_dir = self.begin()
        finding = self.through_findings(drive, run_dir)
        slib.fix_finding(self.tmp, self.ws, finding, card=None)
        code, out, err = self.waive(drive, run_dir, finding, "Reopen it, it came back on the bench", kind="reopen")
        self.assertEqual(code, 0, (out, err))
        event = slib.log_lines(self.ws)[-1]
        self.assertEqual((event["kind"], event["words"]), ("reopened", "Reopen it, it came back on the bench"))

    def test_a_waiver_the_record_cannot_take_is_refused(self):
        drive, run_dir = self.begin()
        finding = self.through_findings(drive, run_dir)
        before = slib.snapshot(self.ws)
        code, out, err = self.waive(drive, run_dir, finding, "Reopen it", kind="reopen")
        self.assertEqual(code, 5, "an open finding cannot be reopened")
        self.assertEqual(before, slib.snapshot(self.ws))

    def test_report_only_plans_the_waiver_and_writes_nothing(self):
        drive, run_dir = self.begin(report_only=True)
        slib.visit(self, drive, run_dir, "build-v2", "report-only", self.ws)
        finding = slib.raise_finding(self.tmp, self.ws)
        code, out, err = slib.visit(self, drive, run_dir, "signoff-v2", "report-only", self.ws)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        before = slib.snapshot(self.ws)
        code, out, err = self.waive(drive, run_dir, finding, "Waive it")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(before, slib.snapshot(self.ws), "report-only: nothing outside the run directory")
        planned = testlib.load_json(os.path.join(run_dir, "events.json"))
        self.assertEqual([(e["kind"], e["words"]) for e in planned["events"]], [("waived", "Waive it")])


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class ReportOnly(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-ro-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)

    def test_a_report_only_run_writes_nothing_and_says_so(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws, report_only=True)
        before = slib.snapshot(self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        code, out, err = slib.visit(self, drive, run_dir, "build-v2", "report-only", self.ws)
        self.assertEqual(code, 0, (out, err))
        code, out, err = slib.visit(self, drive, run_dir, "signoff-v2", "clean", self.ws)
        self.assertEqual(code, 5, "a station that wrote is refused on a report-only run")
        visit = testlib.load_json(os.path.join(run_dir, "ship.json"))["visit"]
        os.remove(os.path.join(visit["run_dir"], "result.json"))
        code, out, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual(code, 2)
        named = {"visit_run_id": visit["run_id"], "visit_run_dir": visit["run_dir"]}
        clean = slib.station_result("signoff-v2", "report-only", named, self.ws)
        clean.update(findings=[], verdict_stated="signed off")
        slib.put_result(named, clean)
        code, out, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual(code, 0, (out, err))
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertTrue(out["wrote_nothing"])
        self.assertTrue(all(w["kind"] == "run_artifact" for w in out["writes"]))
        self.assertEqual(before, slib.snapshot(self.ws))


if __name__ == "__main__":
    unittest.main()
