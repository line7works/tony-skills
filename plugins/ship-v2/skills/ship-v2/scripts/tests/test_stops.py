"""CR-23, the four stops (contract sections 3.4, 3.5 and 7), in v1's words and order.

(3) a build-v2 PARTIAL or STOPPED ends the run with no later visit on the trace; a signoff-v2 stop or refusal ends the
run with its status; (4) a fix outside the slice's footprint (the paths the slice names, contained the way build-v2's
contract computes containment) ends it, whether the executor declares the path or only touches it; (2) a fix that
needs a spec change ends it, and so does a fix that touches the build doc; (1) is in test_laps.py. A stop ends the
run: nothing but `report` follows it.
"""
import os
import unittest

import slib
import testlib


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheStops(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-stops-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir)

    def ended(self, tag, condition_words):
        for args in (["visit", "--run-dir", self.run_dir, "--station", "signoff-v2"],
                     ["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"],
                     ["lap", "--run-dir", self.run_dir]):
            code, out, err = self.drive(args)
            self.assertIn(code, (2, 5), (args, out, err))
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", tag))
        self.assertTrue(out["station_result"]["chat"].split("\n")[2].startswith("Result: STOPPED (%s" % condition_words),
                        out["station_result"]["chat"])
        self.assertEqual(slib.validate_trace(self.run_dir)[0], 0)
        return out

    def stations_visited(self):
        return [l["expected"] for l in slib.trace(self.run_dir) if l["kind"] == "visit" and l["status"] != "visiting"]

    def test_stop_3_a_partial_build_ends_the_run_with_no_signoff_visit(self):
        code, out, err = slib.visit(self, self.drive, self.run_dir, "build-v2", "partial", self.ws)
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        out = self.ended("build-not-complete", "condition 3: ")
        self.assertEqual(self.stations_visited(), ["build-v2"])
        self.assertIn("Build: PARTIAL", out["station_result"]["chat"])
        self.assertIn("Signoff: not reached", out["station_result"]["chat"])

    def test_stop_3_a_stopped_build_and_failing_checks_end_the_run_too(self):
        for which, word in (("stopped", "STOPPED"), ("checks", "PARTIAL")):
            tmp = testlib.make_scratch("ship-stop3-")
            self.addCleanup(testlib.rmtree, tmp)
            drive, run_dir = slib.start(self, self.tree, tmp, self.ws, run="run-" + which)
            slib.through_hook(self, drive, tmp, run_dir)
            code, out, err = slib.visit(self, drive, run_dir, "build-v2", which, self.ws)
            self.assertEqual((code, out["next"]), (0, "report"), (which, out, err))
            code, out, err = slib.report(drive, run_dir)
            self.assertEqual(out["stop_tag"], "build-not-complete")
            self.assertIn("Build: %s" % word, out["station_result"]["chat"])

    def test_a_signoff_stop_ends_the_run_with_its_status(self):
        slib.visit(self, self.drive, self.run_dir, "build-v2", "completed", self.ws)
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "stopped", self.ws)
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        out = self.ended("signoff-stopped", "signoff-v2")
        self.assertIn("Signoff: stopped", out["station_result"]["chat"])
        self.assertEqual(self.stations_visited(), ["build-v2", "signoff-v2"])

    def through_findings(self):
        slib.visit(self, self.drive, self.run_dir, "build-v2", "completed", self.ws)
        self.finding = slib.raise_finding(self.tmp, self.ws)
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "findings", self.ws)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))

    def fix(self, fixes, spec_change=()):
        return self.drive(["fix", "--run-dir", self.run_dir, "--fixes", slib.fixes_file(
            self.tmp, self.run_dir, 1, fixes, spec_change)])

    def test_stop_4_a_declared_path_outside_the_footprint(self):
        self.through_findings()
        code, out, err = self.fix([{"finding": self.finding, "paths": ["src/spinner.py"], "summary": "wants the spinner"}])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        out = self.ended("outside-footprint", "condition 4: ")
        self.assertEqual(self.stations_visited(), ["build-v2", "signoff-v2"])
        self.assertNotIn("Fixed:", out["station_result"]["chat"], "a stopped lap's fixes are never listed as Fixed")

    def test_stop_4_an_undeclared_touch_outside_the_footprint(self):
        self.through_findings()
        testlib.write_text(os.path.join(self.ws, "src", "spinner.py"), "def twice(count):\n    return 2 * count\n")
        testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"), "def spin(count):\n    return count + 2\n")
        code, out, err = self.fix([{"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "the fix"}])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        out = self.ended("outside-footprint", "condition 4: ")
        self.assertIn("src/spinner.py", out["reason"])

    def test_a_footprint_directory_holds_a_new_test(self):
        self.through_findings()
        testlib.write_text(os.path.join(self.ws, "tests", "test_turnstile.py"), "import unittest\n")
        code, out, err = self.fix([{"finding": self.finding, "paths": ["tests/test_turnstile.py"], "summary": "a test"}])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))

    def test_stop_2_a_fix_that_needs_a_spec_change(self):
        self.through_findings()
        code, out, err = self.fix([], spec_change=[{"finding": self.finding, "why": "the slice asks for one turn per "
                                                                                    "tap, and the fix needs two"}])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.ended("spec-change", "condition 2: ")

    def test_stop_2_a_fix_that_touches_the_build_doc(self):
        self.through_findings()
        path = os.path.join(self.ws, slib.DOC)
        testlib.write_text(path, testlib.read_text(path).replace("counts every turn", "counts most turns"))
        code, out, err = self.fix([{"finding": self.finding, "paths": [slib.DOC], "summary": "loosen the requirement"}])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.ended("spec-change", "condition 2: ")

    def fixed(self):
        self.through_findings()
        testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"), "def spin(count):\n    return count + 2\n")
        code, out, err = self.fix([{"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "the fix"}])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))

    def test_stop_4_a_touch_outside_the_footprint_after_the_fixes_were_recorded(self):
        """Written after the code (the slice 2 report says so): the check runs again before recheck-v2 is visited."""
        self.fixed()
        testlib.write_text(os.path.join(self.ws, "src", "spinner.py"), "def twice(count):\n    return 3 * count\n")
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.ended("outside-footprint", "condition 4: ")
        self.assertEqual(self.stations_visited(), ["build-v2", "signoff-v2"])

    def test_stop_2_the_build_doc_touched_after_the_fixes_were_recorded(self):
        self.fixed()
        path = os.path.join(self.ws, slib.DOC)
        testlib.write_text(path, testlib.read_text(path).replace("counts every turn", "counts most turns"))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.ended("spec-change", "condition 2: ")

    def test_an_unnamed_touch_inside_the_footprint_after_the_fixes_is_refused(self):
        self.fixed()
        testlib.write_text(os.path.join(self.ws, "tests", "test_more.py"), "x = 2\n")
        before = slib.trace(self.run_dir)
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(before, slib.trace(self.run_dir))
        os.remove(os.path.join(self.ws, "tests", "test_more.py"))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual((code, out["next"]), (0, "visit --result"), (out, err))

    def test_a_hand_edit_of_the_runs_state_is_refused(self):
        self.through_findings()
        path = os.path.join(self.run_dir, "ship.json")
        doc = testlib.load_json(path)
        doc["laps_allowed"] = 9
        testlib.write_json(path, doc)
        code, out, err = self.fix([{"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "x"}])
        self.assertEqual(code, 1, (out, err))
        self.assertIn("changed by hand", err)

    def test_a_fix_must_trace_to_a_named_finding(self):
        self.through_findings()
        for fixes in ([{"finding": "f1:" + "0" * 20, "paths": ["src/turnstile.py"], "summary": "x"}],
                      [{"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "x"},
                       {"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "again"}]):
            code, out, err = self.fix(fixes)
            self.assertEqual(code, 5, (fixes, out, err))
        testlib.write_text(os.path.join(self.ws, "tests", "test_other.py"), "x = 1\n")
        code, out, err = self.fix([{"finding": self.finding, "paths": ["src/turnstile.py"], "summary": "x"}])
        self.assertEqual(code, 5, "a touched path inside the footprint that no fix names is refused")


if __name__ == "__main__":
    unittest.main()
