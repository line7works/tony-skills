"""Slice 2 re-check 1's MINORs that ride in fix round 2 (the E15 lane contract A28), each by its stated replacement.

- R1S2-3: a kill inside a pause answer's bookkeeping (after `pauses.json` records the answer, before the run leaves
  `paused`) wedged the run: every later `pause --answer` was refused ("the open pause is None") and no command reached
  a terminal status. Now the next `pause --answer` finishes the cut-off bookkeeping from the recorded answer and its
  receipt, writes nothing twice, and the run goes on to its end. Since the E15 lane contract A29 (1) the answer, the
  receipt finished, the state and the stage land in one save, so a kill leaves either none of the bookkeeping (the
  next answer settles the grant and saves it once) or a journal the next command finishes; the run directory re-check
  1 reproduced (an answer recorded while still `paused`) is still finished by the next answer.
- R1S2-5: `report` at `visiting` with a result standing that `visit --result` never refused said the result "was not
  accepted (`visit --result` refused it)". Now it refuses (exit 2) and names `visit --result` as the command to run
  first; a result `visit --result` would refuse, or none, still ends the run `visit-unfinished`, saying which.
(R1S2-4 falls out of the window rule: `test_window.py`.)
"""
import os
import signal
import subprocess
import sys
import time
import unittest

import cr25lib
import slib
import testlib
from test_card_with_grant import ours, status_of


def receipt_path(run_dir):
    names = sorted(n for n in os.listdir(run_dir) if n.startswith("receipt-") and n.endswith(".json"))
    return os.path.join(run_dir, names[-1]) if names else None


def phase(run):
    return testlib.load_json(os.path.join(run.run_dir, "checkpoint.json"))["phase"]


def ask(run, finding):
    code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--question", slib.question_file(
        run.tmp, run.run_dir, "Only you can rule this finding: waive it or hold?", source="ship", station=None,
        finding=finding, name="q-%d.json" % len(os.listdir(run.tmp)))])
    run.test.assertEqual(code, 0, (out, err))
    return out["pause"]


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class R1S2_3_ACutOffAnswerSettles(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-r1s2-3-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def to_the_end(self, run):
        """The run goes on to a terminal status: the waived MAJOR leaves nothing to fix, recheck-v2 finds nothing
        open, `report` ends it."""
        code, out, err = run.drive(["fix", "--run-dir", run.run_dir, "--fixes", slib.fixes_file(
            run.tmp, run.run_dir, 1, [], name="fixes-after.json")])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))
        out = run.recheck("nothing_open")
        self.assertEqual(out["next"], "report", out)
        out = run.end()
        self.assertEqual(out["status"], "completed", out)
        return out

    def test_the_state_a_kill_after_the_answer_was_recorded_leaves(self):
        """Re-check 1's `g3_wedge.py`: the run directory as a kill right after `pauses.json`'s write leaves it
        (the checkpoint and `ship.json` at their bytes before the bookkeeping, the receipt unfinished)."""
        run = cr25lib.Run(self, self.tmp, "wedge")
        run.build()
        run.signoff()
        number = ask(run, run.findings[0])
        answer = slib.answer_file(run.tmp, run.run_dir, number, "Waive it", {"kind": "waive",
                                                                             "finding": run.findings[0]},
                                  name="a-wedge.json")
        keep = {}
        for name in ("checkpoint.json", "ship.json"):
            with open(os.path.join(run.run_dir, name), "rb") as fh:
                keep[name] = fh.read()
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        for name, data in keep.items():
            with open(os.path.join(run.run_dir, name), "wb") as fh:
                fh.write(data)
        path = receipt_path(run.run_dir)
        doc = testlib.load_json(path)
        doc["finished"] = False
        testlib.write_json(path, doc)
        self.assertEqual(phase(run), "paused")
        events = ours(run.ws)
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual((code, out.get("next")), (0, "fix"), (out, err))
        self.assertIn("settled", out)
        self.assertEqual(ours(run.ws), events, "nothing appended twice")
        self.assertEqual(status_of(run.ws), "Status: signed off")
        self.assertTrue(testlib.load_json(path)["finished"])
        pauses = testlib.load_json(os.path.join(run.run_dir, "pauses.json"))["pauses"]
        self.assertEqual([p["answer"]["words"] for p in pauses], ["Waive it"])
        self.to_the_end(run)

    def test_a_real_kill_inside_the_bookkeeping(self):
        """A real SIGKILL on the `pause --answer` process the test starts, held (`SHIP_V2_TEST_HOLD=answered`) once the
        grant's doc half is written and the answer's bookkeeping is decided and staged, before its one save (A29)."""
        run = cr25lib.Run(self, self.tmp, "kill")
        run.build()
        run.signoff()
        number = ask(run, run.findings[0])
        answer = slib.answer_file(run.tmp, run.run_dir, number, "Waive it", {"kind": "waive",
                                                                             "finding": run.findings[0]},
                                  name="a-kill.json")
        pauses_path = os.path.join(run.run_dir, "pauses.json")
        receipt = os.path.join(run.run_dir, "receipt-%d.json" % number)
        env = dict(run.drive.env, SHIP_V2_TEST_HOLD="answered")
        proc = subprocess.Popen([sys.executable, run.drive.script, "pause", "--run-dir", run.run_dir, "--answer",
                                 answer], cwd=run.tmp, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 60
        while time.time() < deadline:
            written = testlib.load_json(receipt).get("doc_written") if os.path.exists(receipt) else False
            if written:
                time.sleep(0.5)
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait()
                break
            if proc.poll() is not None:
                self.fail("the answer process ended (exit %s) before the bookkeeping window" % proc.returncode)
            time.sleep(0.01)
        else:
            proc.kill()
            proc.wait()
            self.fail("the bookkeeping window was never reached")
        self.assertEqual(phase(run), "paused", "the kill left the run paused")
        self.assertIsNone(testlib.load_json(pauses_path)["pauses"][-1]["answer"], "none of the bookkeeping saved")
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "save.json")), "no save had begun")
        events = ours(run.ws)
        self.assertEqual([e["kind"] for e in events], ["waived", "card_set"])
        for attempt in range(2):
            code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
            if attempt == 0:
                self.assertEqual((code, out.get("next")), (0, "fix"), (out, err))
            else:
                self.assertEqual(code, 2, "the run left `paused`: a second answer is out of turn")
        self.assertEqual(ours(run.ws), events, "nothing appended twice")
        self.to_the_end(run)


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class R1S2_5_ReportAtVisiting(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-r1s2-5-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir)
        code, self.visit, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "build-v2"])
        self.assertEqual(code, 0, (self.visit, err))

    def test_a_result_never_refused_makes_report_name_visit_result_first(self):
        slib.put_result(self.visit, slib.station_result("build-v2", "partial", self.visit, self.ws))
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual(code, 2, (out, err))
        self.assertIn("visit --result", err + str(out))
        self.assertEqual(testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))["phase"], "visiting")
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual((code, out.get("stop_tag")), (0, "build-not-complete"), (out, err))
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "build-not-complete"), (out, err))

    def test_a_refused_result_ends_the_run_visit_unfinished_naming_why(self):
        doc = slib.station_result("build-v2", "partial", self.visit, self.ws)
        doc["run_id"] = "another-run"
        slib.put_result(self.visit, doc)
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual(code, 5, (out, err))
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "visit-unfinished"), (out, err))
        self.assertIn("another-run", out["reason"])
        self.assertIn("visit --result", out["reason"])

    def test_no_result_ends_the_run_visit_unfinished(self):
        code, out, err = slib.report(self.drive, self.run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "visit-unfinished"), (out, err))
        self.assertIn("left no result", out["reason"])


if __name__ == "__main__":
    unittest.main()
