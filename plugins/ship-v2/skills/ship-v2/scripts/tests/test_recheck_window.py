"""Slice 2 check 1's C2-1: what moves while recheck-v2's visit is open, or after a not-clear result and before the next
lap, is held to the slice's footprint and the doc before ALL CLEAR or the next lap (contract sections 3.4 to 3.6).

The pin a lap's fixes are held to is not taken again at `lap`: when recheck-v2's result holds, every path that moved
since the lap's fixes were recorded (the station's own writes aside: the project files its result lists in
`records_written`, each still at the hash it gives) is checked first (the doc moved is stop 2, a path outside the
footprint stop 4, an unnamed path inside it refused, exit 5, nothing written), and the next lap's pin is taken there,
after the station's writes. `lap` keeps that pin: a move since it outside the footprint is stop 4 and the doc moved is
stop 2, before the lap opens; a move inside it is the next lap's to name. The shapes are the checker's: `README.md`
and slice B's `src/spinner.py` edited after a not-clear result, and `src/spinner.py` edited while the visit is open.
"""
import os
import unittest

import slib
import testlib


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheRecheckWindow(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-window-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir)
        code, out, err = slib.visit(self, self.drive, self.run_dir, "build-v2", "completed", self.ws,
                                    before_result=lambda visit: slib.set_status(self.ws, "A", "built"))
        self.assertEqual(code, 0, (out, err))
        found = []

        def signoff_writes(visit):          # what signoff-v2 itself writes while it runs
            found.append(slib.raise_finding(self.tmp, self.ws))
            slib.set_status(self.ws, "A", "signed off with conditions")
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "findings", self.ws,
                                    before_result=signoff_writes)
        self.finding = found[0]
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        self.fix(1)

    def write(self, rel, text):
        testlib.write_text(os.path.join(self.ws, rel), text)

    def fix(self, lap, paths=("src/turnstile.py",)):
        self.write("src/turnstile.py", "def spin(count):\n    return count + %d\n" % (lap + 1))
        code, out, err = self.drive(["fix", "--run-dir", self.run_dir, "--fixes", slib.fixes_file(
            self.tmp, self.run_dir, lap, [{"finding": self.finding, "paths": list(paths), "summary": "lap %d" % lap}],
            name="fixes-%d-%d.json" % (lap, len(os.listdir(self.tmp))))])
        return code, out, err

    def cleared(self):
        """What recheck-v2 itself writes on ALL CLEAR: its disposition and card through the records, its `Status:`."""
        slib.fix_finding(self.tmp, self.ws, self.finding)
        slib.set_status(self.ws, "A", "signed off")

    def recheck(self, which="all_clear", during=None, station_writes=True):
        def before_result(visit):
            if during is not None:
                during()
            if station_writes and which == "all_clear":
                self.cleared()
        return slib.visit(self, self.drive, self.run_dir, "recheck-v2", which, self.ws, before_result=before_result)

    def ended(self, tag, condition):
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", tag), out["reason"])
        self.assertTrue(out["station_result"]["result_line"].startswith("STOPPED (condition %d: " % condition), out)
        self.assertNotIn("ALL CLEAR", out["station_result"]["result_line"])
        self.assertEqual(slib.validate_trace(self.run_dir)[0], 0)
        return out

    # ---- while the visit is open --------------------------------------------------------------------------

    def test_a_path_outside_the_footprint_edited_while_the_visit_is_open_is_stop_4(self):
        code, out, err = self.recheck(during=lambda: self.write("src/spinner.py", "def twice(c):\n    return 2 * c\n"))
        self.assertEqual((code, out["next"], out.get("stop_tag")), (0, "report", "outside-footprint"), (out, err))
        self.assertIn("src/spinner.py", out["reason"])
        lines = [(l["expected"], l["status"]) for l in slib.trace(self.run_dir) if l["kind"] == "visit"]
        self.assertEqual(lines[-1], ("recheck-v2", "completed"), "the station's own result closes its visit")
        self.ended("outside-footprint", 4)

    def test_the_readme_edited_while_the_visit_is_open_is_stop_4(self):
        code, out, err = self.recheck(during=lambda: self.write("README.md", "# Turnstile\n\nEdited.\n"))
        self.assertEqual((code, out.get("stop_tag")), (0, "outside-footprint"), (out, err))
        self.ended("outside-footprint", 4)

    def test_the_doc_edited_by_hand_while_the_visit_is_open_is_stop_2(self):
        """The hand edit lands first; the station then writes its `Status:` line and lists its own write, from the
        bytes it found to the bytes it left: its write does not start from the doc the fixes left, so it does not
        cover the hand edit."""
        path = os.path.join(self.ws, slib.DOC)
        code, visit, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 0, (visit, err))
        testlib.write_text(path, testlib.read_text(path).replace("counts every turn", "counts most turns"))
        found = slib.sha(path)
        self.cleared()
        listed = slib.doc_write(self.ws, found)
        slib.put_result(visit, slib.station_result("recheck-v2", "all_clear", visit, self.ws, writes=[listed]))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual((code, out.get("stop_tag")), (0, "spec-change"), (out, err))
        self.ended("spec-change", 2)

    def test_the_stations_own_status_write_not_listed_in_its_result_is_stop_2(self):
        def unlisted(visit):
            self.cleared()
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 0, (out, err))
        unlisted(out)
        slib.put_result(out, slib.station_result("recheck-v2", "all_clear", out, self.ws, writes=[]))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual((code, out.get("stop_tag")), (0, "spec-change"), (out, err))

    def test_the_doc_edited_after_the_stations_listed_write_is_stop_2(self):
        path = os.path.join(self.ws, slib.DOC)
        code, visit, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        before = slib.sha(path)
        self.cleared()
        listed = slib.doc_write(self.ws, before)
        testlib.write_text(path, testlib.read_text(path).replace("counts every turn", "counts most turns"))
        slib.put_result(visit, slib.station_result("recheck-v2", "all_clear", visit, self.ws, writes=[listed]))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual((code, out.get("stop_tag")), (0, "spec-change"), (out, err))

    def test_an_unnamed_path_inside_the_footprint_moved_during_the_visit_is_refused(self):
        code, visit, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 0, (visit, err))
        before = slib.sha(os.path.join(self.ws, slib.DOC))
        self.cleared()
        listed = slib.doc_write(self.ws, before)
        self.write("tests/test_more.py", "x = 2\n")
        slib.put_result(visit, slib.station_result("recheck-v2", "all_clear", visit, self.ws, writes=[listed]))
        before = (slib.trace(self.run_dir), testlib.load_json(os.path.join(self.run_dir, "checkpoint.json")))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("tests/test_more.py", out["reason"])
        self.assertEqual(before, (slib.trace(self.run_dir),
                                  testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))),
                         "a refusal writes nothing")
        os.remove(os.path.join(self.ws, "tests", "test_more.py"))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))

    def test_the_stations_listed_write_is_its_own_and_all_clear_holds(self):
        code, out, err = self.recheck()
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual((code, out["status"]), (10, "completed"), (out, err))

    # ---- after a not-clear result, before the next lap ----------------------------------------------------

    def test_the_checkers_shape_readme_and_spinner_after_a_not_clear_result_are_stop_4_at_lap(self):
        code, out, err = self.recheck("not_clear")
        self.assertEqual((code, out["next"]), (0, "lap"), (out, err))
        self.write("README.md", "# Turnstile\n\nEdited outside the footprint.\n")
        self.write("src/spinner.py", "def twice(count):\n    return count * 2\n")
        code, out, err = self.drive(["lap", "--run-dir", self.run_dir])
        self.assertEqual((code, out["next"], out.get("stop_tag")), (0, "report", "outside-footprint"), (out, err))
        self.assertIn("README.md", out["reason"])
        self.assertIn("src/spinner.py", out["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "laps.json")) and
                         len(testlib.load_json(os.path.join(self.run_dir, "laps.json"))["laps"]) > 1,
                         "no lap opened")
        self.ended("outside-footprint", 4)

    def test_the_doc_edited_after_a_not_clear_result_is_stop_2_at_lap(self):
        self.recheck("not_clear")
        path = os.path.join(self.ws, slib.DOC)
        testlib.write_text(path, testlib.read_text(path).replace("counts every turn", "counts most turns"))
        code, out, err = self.drive(["lap", "--run-dir", self.run_dir])
        self.assertEqual((code, out.get("stop_tag")), (0, "spec-change"), (out, err))
        self.ended("spec-change", 2)

    def test_an_inside_path_edited_before_the_lap_is_the_next_laps_to_name(self):
        self.recheck("not_clear")
        self.write("tests/test_turnstile.py", "import unittest\n")
        code, out, err = self.drive(["lap", "--run-dir", self.run_dir])
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        code, out, err = self.fix(2)
        self.assertEqual(code, 5, "an inside path moved before the lap and named by no fix is refused")
        self.assertIn("tests/test_turnstile.py", out["reason"])
        code, out, err = self.fix(2, paths=("src/turnstile.py", "tests/test_turnstile.py"))
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))


if __name__ == "__main__":
    unittest.main()
