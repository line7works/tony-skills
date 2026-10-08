"""The loop and its trace (the E15 lane contract section 10's required tests; CR-21, CR-26; contract sections 3 and 8).

The trace on a clean loop: build, signoff ALL CLEAR, recheck not run. The trace on the full loop: build, signoff with
findings, the fix, recheck. Every run's trace validates with the frame's shared validator, every station named in
any line ship-v2 renders is a v2 station, and the `SHIP:` block keeps v1's form.
"""
import os
import re
import unittest

import slib
import testlib

testlib.add_scripts_to_path()
from back_core import trace as tracemod  # noqa: E402


def visits(run_dir):
    """[(station, status)] of every closing visit line."""
    return [(l["expected"], l["status"]) for l in slib.trace(run_dir) if l["kind"] == "visit" and
            l["status"] != "visiting"]


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheLoop(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-loop-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir, armed=True)

    def build(self):
        code, out, err = slib.visit(self, self.drive, self.run_dir, "build-v2", "completed", self.ws,
                                    before_result=lambda visit: slib.set_status(self.ws, "A", "built"))
        self.assertEqual(code, 0, (out, err))

    def test_a_clean_loop_build_signoff_all_clear_recheck_not_run(self):
        self.build()
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "clean", self.ws,
                                    before_result=lambda visit: slib.set_status(self.ws, "A", "signed off"))
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "report")
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 2, "a clean signoff ends the loop: no recheck")
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("completed", None))
        self.assertEqual(visits(self.run_dir), [("build-v2", "completed"), ("signoff-v2", "completed")])
        chat = out["station_result"]["chat"].split("\n")
        self.assertEqual(chat[0], "SHIP: A %s %s" % (slib.D, slib.DOC))
        self.assertEqual(chat[1], "Hook: armed")
        self.assertEqual(chat[2], "Result: ALL CLEAR")
        self.assertEqual(chat[3], "Build: COMPLETE  %s  Signoff: signed off  %s  Recheck: not run  %s  Card: signed off"
                                  "  %s  Laps: 0" % (slib.M, slib.M, slib.M, slib.M))
        self.assertEqual(slib.validate_trace(self.run_dir)[0], 0)

    def test_the_full_loop_build_signoff_findings_fix_recheck(self):
        self.build()
        found = []

        def signoff_writes(visit):          # what signoff-v2 itself writes while it runs
            found.append(slib.raise_finding(self.tmp, self.ws))
            slib.set_status(self.ws, "A", "signed off with conditions")
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "findings", self.ws,
                                    before_result=signoff_writes)
        finding = found[0]
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "fix")
        self.assertEqual([f["id"] for f in out["named"]], [finding])
        testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"), "def spin(count):\n    return count + 2\n")
        code, out, err = self.drive(["fix", "--run-dir", self.run_dir, "--fixes", slib.fixes_file(
            self.tmp, self.run_dir, 1, [{"finding": finding, "paths": ["src/turnstile.py"],
                                        "summary": "the double tap now counts"}])])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "visit --station recheck-v2")
        def recheck_writes(visit):          # what recheck-v2 itself writes during its visit
            slib.fix_finding(self.tmp, self.ws, finding)
            slib.set_status(self.ws, "A", "signed off")
        code, out, err = slib.visit(self, self.drive, self.run_dir, "recheck-v2", "all_clear", self.ws,
                                    before_result=recheck_writes)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "report")
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "completed")
        self.assertEqual(visits(self.run_dir), [("build-v2", "completed"), ("signoff-v2", "completed"),
                                                ("recheck-v2", "completed")])
        chat = out["station_result"]["chat"].split("\n")
        self.assertEqual(chat[2], "Result: ALL CLEAR")
        self.assertIn("Recheck: ALL CLEAR", chat[3])
        self.assertTrue(chat[3].endswith("Laps: 1"), chat[3])
        self.assertTrue(any(l.startswith("Fixed: the counter skips a turn %s %s %s" % (slib.M, slib.MAJOR_AT, slib.M))
                            for l in chat), chat)
        self.assertEqual(slib.validate_trace(self.run_dir)[0], 0)
        self.assertEqual(out["trace"]["lines"], 6)

    def test_every_station_named_is_a_v2_station(self):
        """CR-26: every summon or kickoff line ship-v2 renders names the v2 stations."""
        self.build()
        finding = slib.raise_finding(self.tmp, self.ws, location="src/spinner.py:1", slice_name="B",
                                     card=None)
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "clean", self.ws)
        self.assertEqual(code, 0, (out, err))
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual(code, 10, (out, err))
        chat = out["station_result"]["chat"]
        remains = [l for l in chat.split("\n") if l.startswith("Remains: ")]
        self.assertTrue(remains, chat)
        self.assertIn("/recheck-v2 B %s" % slib.DOC, remains[0])
        named = re.findall(r"/([a-z0-9-]+)", chat + "\n".join(str(c) for c in self.drive.calls))
        for word in named:
            self.assertNotIn(word, tracemod.v1_names())


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheHookIsRecorded(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-hook-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)

    def test_codex_never_reads_armed(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws, harness="codex-cli")
        code, out, err = drive(["select", "--run-dir", run_dir, "--doc", slib.DOC])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["hook", "--run-dir", run_dir, "--reading", slib.hook_file(self.tmp, "codex-cli", True)])
        self.assertEqual(code, 5, "a Codex reading that claims an armed hook is refused")
        code, out, err = drive(["hook", "--run-dir", run_dir, "--reading", slib.hook_file(self.tmp, "codex-cli", False)])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["hook"]["label"], "NOT armed (run unwrapped)")

    def test_a_reading_from_another_harness_is_refused(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        drive(["select", "--run-dir", run_dir, "--doc", slib.DOC])
        code, out, err = drive(["hook", "--run-dir", run_dir, "--reading", slib.hook_file(self.tmp, "codex-cli", False)])
        self.assertEqual(code, 5, (out, err))


if __name__ == "__main__":
    unittest.main()
