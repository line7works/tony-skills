"""CR-22, the lap counter (contract section 3.6): one initial pass and at most one extra fix-and-recheck lap.

A third lap is refused (exit 5, nothing written) unless the input carries the owner's words for it; the extra lap
exhausted without ALL CLEAR is stop condition 1. The owner's words for more laps are recorded verbatim (the trace's
line shape is a frozen back-frame file with no field for them: contract section 3.6 says where they are kept).
"""
import os
import unittest

import slib
import testlib


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheLapCounter(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-laps-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)

    def through_signoff(self, **station):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws, **station)
        slib.through_hook(self, drive, self.tmp, run_dir)
        code, out, err = slib.visit(self, drive, run_dir, "build-v2", "completed", self.ws)
        self.assertEqual(code, 0, (out, err))
        self.finding = slib.raise_finding(self.tmp, self.ws)
        code, out, err = slib.visit(self, drive, run_dir, "signoff-v2", "findings", self.ws)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        return drive, run_dir

    def lap(self, drive, run_dir, number):
        text = "def spin(count):\n    return count + %d\n" % (number + 10)
        testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"), text)
        code, out, err = drive(["fix", "--run-dir", run_dir, "--fixes", slib.fixes_file(
            self.tmp, run_dir, number, [{"finding": self.finding, "paths": ["src/turnstile.py"],
                                         "summary": "attempt %d" % number}])])
        self.assertEqual(code, 0, (out, err))
        return slib.visit(self, drive, run_dir, "recheck-v2", "not_clear", self.ws)

    def test_the_extra_lap_then_a_third_is_refused_and_the_run_stops_at_condition_1(self):
        drive, run_dir = self.through_signoff()
        code, out, err = self.lap(drive, run_dir, 1)
        self.assertEqual((code, out["next"]), (0, "lap"), (out, err))
        code, out, err = drive(["lap", "--run-dir", run_dir])
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        self.assertEqual(out["lap"], 2)
        code, out, err = self.lap(drive, run_dir, 2)
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        before = (slib.trace(run_dir), slib.snapshot(self.ws), sorted(os.listdir(run_dir)),
                  testlib.load_json(os.path.join(run_dir, "checkpoint.json")))
        code, out, err = drive(["lap", "--run-dir", run_dir])
        self.assertEqual(code, 5, (out, err))
        after = (slib.trace(run_dir), slib.snapshot(self.ws), sorted(os.listdir(run_dir)),
                 testlib.load_json(os.path.join(run_dir, "checkpoint.json")))
        self.assertEqual(before, after, "a refused third lap writes nothing")
        code, out, err = drive(["fix", "--run-dir", run_dir, "--fixes", slib.fixes_file(self.tmp, run_dir, 3, [
            {"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "attempt 3"}])])
        self.assertEqual(code, 2, "no fix without a lap")
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 2, "no recheck without a lap")
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "extra-lap-exhausted"))
        chat = out["station_result"]["chat"].split("\n")
        self.assertTrue(chat[2].startswith("Result: STOPPED (condition 1: "), chat[2])
        self.assertTrue(chat[3].endswith("Laps: 2"), chat[3])
        self.assertEqual(slib.validate_trace(run_dir)[0], 0)
        self.assertEqual(len([l for l in slib.trace(run_dir) if l["expected"] == "recheck-v2"
                              and l["status"] != "visiting"]), 2)

    def test_the_owners_words_allow_a_third_lap_and_are_recorded_verbatim(self):
        words = "Take one more lap on slice A, I want it closed today"
        drive, run_dir = self.through_signoff(extra_laps={"count": 1, "words": words})
        self.lap(drive, run_dir, 1)
        drive(["lap", "--run-dir", run_dir])
        self.lap(drive, run_dir, 2)
        code, out, err = drive(["lap", "--run-dir", run_dir])
        self.assertEqual((code, out["lap"]), (0, 3), (out, err))
        self.assertEqual(out["owner_words"], words)
        laps = testlib.load_json(os.path.join(run_dir, "laps.json"))
        self.assertEqual(laps["laps"][-1]["owner_words"], words)
        code, out, err = self.lap(drive, run_dir, 3)
        self.assertEqual(out["next"], "report")
        code, out, err = drive(["lap", "--run-dir", run_dir])
        self.assertEqual(code, 5, "the owner's words name one more lap, not more")
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual(out["station_result"]["laps"]["owner_words"], words)
        self.assertEqual(out["station_result"]["laps"]["taken"], 3)

    def test_a_lap_before_its_recheck_is_refused(self):
        drive, run_dir = self.through_signoff()
        code, out, err = drive(["lap", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))


if __name__ == "__main__":
    unittest.main()
