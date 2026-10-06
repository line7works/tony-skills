"""The E15 lane contract A27 (1) with A24 (1)'s crash rules: ship-v2 settles its own grant transaction, and a fresh run
stops `card-drift`.

build-v2's two rules for its card write (build-contract sections 9 and 10), as handoff-v2 applies them (A24 (1)):

- a run killed between the records append and the doc write settles on its next command (`pause --answer`, the one
  command a paused run takes): its own events found at the receipt's head by seq and run id are recorded as landed,
  never appended again, and the doc half is finished against the receipt's doc hash; a doc that moved meanwhile stops
  `outside-edit`, naming what the slice's `Status:` line holds, the events reported as landed, nothing reverted, and
  never "nothing was written" once the log holds the run's events;
- a run whose slice's last `card_set` has an `after` that differs from its `Status:` line, while that line equals the
  event's `before`, stops `card-drift` before any visit, naming both values and both ways out.

Every kill is a real SIGKILL on a `pause --answer` process the test starts. The test hook `SHIP_V2_TEST_HOLD`
(honored only with `SHIP_V2_TEST=1`) holds the process at one named point of the transaction (`intent`: the append
landed and the receipt holds no outcome; `outcome`: the receipt holds the outcome and the doc is not written;
`written`: the doc is written and the run's bookkeeping is not), so the kill lands in that window every time.
"""
import json
import os
import signal
import subprocess
import sys
import time
import unittest

import cr25lib
import slib
import testlib
from test_card_with_grant import blocker_cleared, log_path, ours, status_of


def receipt(run_dir):
    names = sorted(n for n in os.listdir(run_dir) if n.startswith("receipt-") and n.endswith(".json"))
    if not names:
        return None
    try:
        return testlib.load_json(os.path.join(run_dir, names[-1]))
    except (OSError, ValueError):
        return None


def asked(run, finding, text="Only you can rule this finding: waive it or hold?"):
    code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--question", slib.question_file(
        run.tmp, run.run_dir, text, source="ship", station=None, finding=finding,
        name="q-kill-%d.json" % len(os.listdir(run.tmp)))])
    run.test.assertEqual(code, 0, (out, err))
    return out["pause"]


def killed(run, finding, kind, words, window):
    """`pause --answer` started with the hold at `window`, SIGKILLed the moment the window is reached. Returns the
    answer file (the same one the settle runs with)."""
    number = asked(run, finding)
    answer = slib.answer_file(run.tmp, run.run_dir, number, words, {"kind": kind, "finding": finding},
                              name="a-kill-%d.json" % number)
    log = log_path(run.ws)
    size = os.path.getsize(log) if os.path.exists(log) else 0
    doc = os.path.join(run.ws, slib.DOC)
    doc_before = slib.sha(doc)
    env = dict(run.drive.env, SHIP_V2_TEST_HOLD=window)
    proc = subprocess.Popen([sys.executable, run.drive.script, "pause", "--run-dir", run.run_dir, "--answer", answer],
                            cwd=run.tmp, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    reached = {
        "intent": lambda: os.path.getsize(log) > size and not os.path.exists(log + ".lock")
        and (receipt(run.run_dir) or {}).get("appended") is None,
        "outcome": lambda: isinstance((receipt(run.run_dir) or {}).get("appended"), list),
        "written": lambda: slib.sha(doc) != doc_before and (receipt(run.run_dir) or {}).get("doc_written") is True,
    }[window]
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if os.path.exists(log) and reached():
                time.sleep(0.2)          # the hold is a sleep: the process sits in the window
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait()
                break
            if proc.poll() is not None:
                run.test.fail("the answer process ended (exit %s) before the %s window" % (proc.returncode, window))
            time.sleep(0.01)
        else:
            run.test.fail("the %s window was never reached" % window)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    run.test.assertEqual(proc.returncode, -signal.SIGKILL)
    return answer


@unittest.skipUnless(slib.usable() and cr25lib.vertical_skill() is not None,
                     "needs jsonschema, the records component, the three stations and vertical-v2 beside this core")
class KilledBetweenTheAppendAndTheDocWrite(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-kill-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def waived_and_killed(self, name, window="intent"):
        run = cr25lib.Run(self, self.tmp, name)
        run.build()
        run.signoff()
        answer = killed(run, run.findings[0], "waive", "Waive it, a bench quirk", window)
        return run, answer

    def test_the_kill_leaves_the_events_landed_and_the_status_line_not_written(self):
        run, answer = self.waived_and_killed("left")
        self.assertEqual([e["kind"] for e in ours(run.ws)], ["waived", "card_set"])
        self.assertEqual(status_of(run.ws), "Status: signed off with conditions")
        self.assertIsNone(receipt(run.run_dir)["appended"])
        self.assertEqual(testlib.load_json(os.path.join(run.run_dir, "checkpoint.json"))["phase"], "paused")

    def test_the_next_command_settles_a_waiver_and_finishes_the_doc_half(self):
        run, answer = self.waived_and_killed("settle")
        log_before = slib.sha(log_path(run.ws))
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        self.assertTrue(out.get("settled"), out)
        self.assertEqual(out["next"], "fix", out)
        self.assertEqual(slib.sha(log_path(run.ws)), log_before, "nothing is appended again")
        self.assertEqual([e["kind"] for e in ours(run.ws)], ["waived", "card_set"])
        self.assertEqual(status_of(run.ws), "Status: signed off")
        rec = receipt(run.run_dir)
        self.assertEqual([row["kind"] for row in rec["appended"]], ["waived", "card_set"])
        self.assertTrue(rec["doc_written"])
        events = testlib.load_json(os.path.join(run.run_dir, "events.json"))
        self.assertEqual([e["kind"] for e in events["events"]], ["waived", "card_set"], "recorded once")
        run.fix(1)
        run.recheck("nothing_open")
        out = run.end()
        self.assertEqual(out["status"], "completed", out)
        self.assertEqual([w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"], ["records_log", "build_doc"])
        slib.commit_all(run.ws, "after the settle")
        code, gate = cr25lib.vertical_gate(run.tmp, run.ws, "vertical-after-settle")
        self.assertEqual((code, (gate or {}).get("next")), (0, "ask"), gate)

    def test_the_next_command_settles_a_reopened_blocker_and_vertical_v2_stops_it(self):
        run, finding = blocker_cleared(self, self.tmp, "reopen")
        answer = killed(run, finding, "reopen", "Reopen it, it came back", "outcome")
        self.assertEqual(status_of(run.ws), "Status: signed off")
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        self.assertTrue(out.get("settled"), out)
        self.assertEqual(out["next"], "lap", out)
        self.assertEqual(status_of(run.ws), "Status: rejected")
        self.assertEqual([e["kind"] for e in ours(run.ws)], ["reopened", "card_set"])
        slib.commit_all(run.ws, "after the reopen settle")
        code, gate = cr25lib.vertical_gate(run.tmp, run.ws, "vertical-after-reopen-settle")
        self.assertEqual(code, 10, gate)
        self.assertEqual(gate["stop_tag"], "gate-short", gate)

    def test_a_kill_after_the_doc_write_completes_without_writing_again(self):
        run, answer = self.waived_and_killed("written", window="written")
        doc_before, log_before = slib.sha(os.path.join(run.ws, slib.DOC)), slib.sha(log_path(run.ws))
        self.assertEqual(status_of(run.ws), "Status: signed off")
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual((slib.sha(os.path.join(run.ws, slib.DOC)), slib.sha(log_path(run.ws))),
                         (doc_before, log_before))
        self.assertEqual(out["next"], "fix", out)

    def test_a_doc_edited_between_the_kill_and_the_resume_stops_outside_edit(self):
        run, answer = self.waived_and_killed("edited")
        path = os.path.join(run.ws, slib.DOC)
        edited = testlib.read_text(path).replace("- the bench clock is monotonic", "- the bench clock is monotonic, "
                                                                                 "checked")
        testlib.write_text(path, edited)
        log_before = slib.sha(log_path(run.ws))
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual((code, out.get("stop_tag")), (0, "outside-edit"), (out, err))
        reason = out["reason"]
        self.assertIn("Status: signed off with conditions", reason, "what the Status: line holds")
        self.assertIn("landed", reason)
        self.assertNotIn("nothing was written", reason)
        self.assertEqual(testlib.read_text(path), edited, "nothing reverted")
        self.assertEqual(slib.sha(log_path(run.ws)), log_before)
        code, out, err = slib.report(run.drive, run.run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "outside-edit"), (out, err))
        self.assertFalse(out["wrote_nothing"], "the events landed and are reported as landed")
        self.assertEqual([w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"], ["records_log"])

    def fresh_select(self, run, name="fresh"):
        drive, run_dir = slib.start(self, run.tree, run.tmp, run.ws, run=name)
        return drive, run_dir, drive(["select", "--run-dir", run_dir, "--doc", slib.DOC])

    def test_a_fresh_run_after_the_kill_stops_card_drift_before_any_visit(self):
        run, answer = self.waived_and_killed("drift")
        snap = slib.snapshot(run.ws)
        drive, run_dir, (code, out, err) = self.fresh_select(run)
        self.assertEqual((code, out.get("stop_tag")), (0, "card-drift"), (out, err))
        reason = out["reason"]
        self.assertIn("slice A", reason)
        self.assertIn("'signed off with conditions'", reason)
        self.assertIn("'signed off'", reason)
        self.assertIn("pause --run-dir", reason, "the first way out: run the interrupted run's next command")
        self.assertIn("Status: signed off", reason, "the second way out: set the line to the card the records hold")
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual(code, 2, "no visit after the stop")
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "card-drift"), (out, err))
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(slib.trace(run_dir), [])
        self.assertEqual(slib.snapshot(run.ws), snap)

    def test_a_fresh_run_after_a_killed_reopening_stops_card_drift_too(self):
        run, finding = blocker_cleared(self, self.tmp, "drift-reopen")
        killed(run, finding, "reopen", "Reopen it", "intent")
        drive, run_dir, (code, out, err) = self.fresh_select(run)
        self.assertEqual((code, out.get("stop_tag")), (0, "card-drift"), (out, err))
        self.assertIn("'rejected'", out["reason"])

    def test_a_hand_edit_to_a_third_value_is_no_drift(self):
        run, answer = self.waived_and_killed("third")
        slib.set_status(run.ws, "A", "built")
        drive, run_dir, (code, out, err) = self.fresh_select(run)
        self.assertEqual((code, out.get("next")), (0, "hook"), (out, err))


if __name__ == "__main__":
    unittest.main()
