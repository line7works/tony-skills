"""The E15 lane contract A24 (1): handoff-v2 settles its own crash window, and `photograph` stops `card-drift`.

build-v2's two rules for its card write (build-contract sections 9 and 10) apply to handoff's grant transaction:

- a `write` whose receipt holds an intent and no outcome settles first: this run's events found at the receipt's head
  by seq and run id are recorded as landed, and the doc half is finished against the receipt's doc hash (the
  `Status:` lines, the grant lines, the block); a doc that moved stops `outside-edit` naming what the `Status:` lines
  hold, the events reported as landed, nothing reverted; never "nothing was written" once the log holds this run's
  events;
- `photograph` stops `card-drift`, nothing written, when a slice's last `card_set` after differs from its `Status:`
  line and that line equals the `card_set` before, naming both values and both ways out.

Every kill here is a real SIGKILL on a `write` process the test starts, sent between the records append and the doc
write by polling the log the way the slice 1b re-check's kill probe does (the log has grown and its lock is gone: the
append child is done and the parent has not written the doc). A kill that misses the window is retried on a fresh
fixture; one that never lands in it fails the test.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import unittest

import hlib
import testlib
from test_card_with_grant import CONDITIONS, REOPENABLE, commit_all, vertical_gate, vertical_skill

ATTEMPTS = 8


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def receipt_of(run_dir):
    path = os.path.join(run_dir, "receipt.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def ours(ws):
    return [e for e in hlib.events(ws) if e["actor"]["station"] == "handoff-v2"]


def status_of(text, name):
    section = text[text.index("## Slice %s" % name):]
    return next(line for line in section.splitlines() if line.startswith("Status:"))


def kill_when(tmp, run_dir, until, timeout=60):
    """Start this run's `write` and SIGKILL it the moment `until()` holds; True when the kill was sent."""
    proc = subprocess.Popen([sys.executable, testlib.DRIVER, "write", "--run-dir", run_dir], cwd=tmp, env=hlib.env(),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if until():
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait()
                return True
            if proc.poll() is not None:
                return False
            time.sleep(0.0005)
        return False
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        time.sleep(0.3)   # the append child, orphaned by the kill, finishes its own exit


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class KilledBetweenTheAppendAndTheDocWrite(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-kill-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def answered(self, tmp, doc, kind):
        ws, info = hlib.make_repo(tmp, hlib.build_doc(**doc), records=True)
        state = hlib.state(ws)
        finding = next(f["id"] for f in state["findings"] if f["location"]["raw"] == "src/turnstile.py:2")
        drive, run_dir = hlib.start(tmp, ws)
        hlib.through_gate(self, drive, tmp, run_dir, questions=[{"source": "chat-ruling", "text": "the grant"}])
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer", hlib.answers_file(
            tmp, run_dir, [{"question": "q1", "answered": True, "words": "the owner's words",
                            "effect": {"kind": kind, "finding": finding}}])])
        self.assertEqual(code, 0, (out, err))
        return ws, drive, run_dir

    def killed(self, doc, kind, window="intent"):
        """A run killed in the named window, on a fresh fixture per attempt: `intent` (the log holds this run's events
        and the receipt holds no outcome), `outcome` (the receipt holds the outcome, the doc is not written) or `doc`
        (the doc is written, the run never finished)."""
        seen = []
        for attempt in range(ATTEMPTS):
            tmp = os.path.join(self.tmp, "a%d" % attempt)
            os.makedirs(tmp)
            ws, drive, run_dir = self.answered(tmp, doc, kind)
            log = hlib.log_path(ws)
            size = os.path.getsize(log)
            before = hlib.read_doc(ws)
            doc_path = os.path.join(ws, hlib.DOC)
            if window == "intent":
                until = lambda: os.path.getsize(log) > size and not os.path.exists(log + ".lock")  # noqa: E731
            elif window == "outcome":
                until = lambda: isinstance((receipt_of(run_dir) or {}).get("appended"), list)  # noqa: E731
            else:
                until = lambda: hlib.sha(doc_path) != sha_text(before)  # noqa: E731
            sent = kill_when(tmp, run_dir, until)
            receipt = receipt_of(run_dir) or {}
            landed = [e["kind"] for e in ours(ws)]
            unchanged = hlib.read_doc(ws) == before
            seen.append((sent, receipt.get("appended") is None, unchanged, landed))
            if not sent or len(landed) != 2:
                continue
            if window == "intent" and receipt.get("appended") is None and unchanged:
                return ws, drive, run_dir, before, tmp
            if window == "outcome" and isinstance(receipt.get("appended"), list) and unchanged:
                return ws, drive, run_dir, before, tmp
            if window == "doc" and not unchanged:
                return ws, drive, run_dir, before, tmp
        self.fail("no kill landed in the %s window in %d attempts: %r" % (window, ATTEMPTS, seen))

    def test_the_kill_leaves_the_state_the_recheck_found(self):
        ws, drive, run_dir, before, tmp = self.killed(CONDITIONS, "waive")
        self.assertEqual([e["kind"] for e in ours(ws)], ["waived", "card_set"])
        self.assertEqual(status_of(hlib.read_doc(ws), "A"), "Status: signed off with conditions")
        self.assertIsNone(receipt_of(run_dir)["appended"])

    def test_the_same_runs_write_settles_a_waiver_and_finishes_the_doc_half(self):
        ws, drive, run_dir, before, tmp = self.killed(CONDITIONS, "waive")
        log_before = hlib.sha(hlib.log_path(ws))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(hlib.sha(hlib.log_path(ws)), log_before, "nothing is appended again")
        self.assertEqual([e["kind"] for e in ours(ws)], ["waived", "card_set"])
        after = hlib.read_doc(ws)
        self.assertEqual(status_of(after, "A"), "Status: signed off")
        self.assertEqual(len([l for l in after.splitlines() if "WAIVED (per user)" in l]), 1)
        self.assertEqual(after.count(hlib.HEADING % hlib.TODAY), 1)
        self.assertEqual([w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"], ["records_log", "build_doc"])
        self.assertTrue(out.get("settled"), out)
        receipt = receipt_of(run_dir)
        self.assertEqual([row["kind"] for row in receipt["appended"]], ["waived", "card_set"])
        self.assertTrue(receipt["doc_written"])
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "The waiver is recorded."])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "completed", out)
        body = hlib.records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", hlib.DOC, "--dry-run"])
        self.assertEqual(body["would_import"], 0, body)
        if vertical_skill() is not None:
            commit_all(ws)
            code, out, err = vertical_gate(tmp, ws, "vertical-after-settle")
            self.assertEqual(code, 0, (out, err))
            self.assertEqual(out.get("next"), "ask", out)

    def test_the_same_runs_write_settles_a_reopened_blocker_and_vertical_v2_stops_it(self):
        ws, drive, run_dir, before, tmp = self.killed(REOPENABLE, "reopen")
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(status_of(hlib.read_doc(ws), "A"), "Status: rejected")
        self.assertEqual([e["kind"] for e in ours(ws)], ["reopened", "card_set"])
        if vertical_skill() is not None:
            commit_all(ws)
            code, out, err = vertical_gate(tmp, ws, "vertical-after-reopen-settle")
            self.assertEqual(code, 10, (out, err))
            self.assertEqual(out["stop_tag"], "gate-short", out)
            self.assertIn("slice A (rejected)", out["reason"])

    def test_a_fresh_run_after_the_kill_stops_card_drift_naming_both_values_and_both_ways_out(self):
        ws, drive, run_dir, before, tmp = self.killed(CONDITIONS, "waive")
        snap = hlib.snapshot(ws)
        fresh, fresh_dir = hlib.start(tmp, ws, run="fresh")
        code, out, err = fresh(["select", "--run-dir", fresh_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 0, (out, err))
        code, out, err = fresh(["photograph", "--run-dir", fresh_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "card-drift", out["reason"])
        self.assertTrue(out["wrote_nothing"])
        reason = out["reason"]
        self.assertIn("slice A", reason)
        self.assertIn("'signed off with conditions'", reason)
        self.assertIn("'signed off'", reason)
        self.assertIn("write --run-dir", reason, "the first way out: resume the interrupted run's write")
        self.assertIn("Status: signed off", reason, "the second way out: set the line to the card the records hold")
        self.assertEqual(hlib.snapshot(ws), snap)

    def test_a_fresh_run_after_a_killed_reopening_stops_card_drift_too(self):
        ws, drive, run_dir, before, tmp = self.killed(REOPENABLE, "reopen")
        fresh, fresh_dir = hlib.start(tmp, ws, run="fresh")
        code, out, err = fresh(["select", "--run-dir", fresh_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 0, (out, err))
        code, out, err = fresh(["photograph", "--run-dir", fresh_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "card-drift", out["reason"])
        self.assertIn("'rejected'", out["reason"])

    def test_a_doc_edited_between_the_kill_and_the_resume_stops_outside_edit(self):
        ws, drive, run_dir, before, tmp = self.killed(CONDITIONS, "waive")
        edited = before.replace("- the bench clock is monotonic\n", "- the bench clock is monotonic, checked\n")
        self.assertNotEqual(edited, before)
        testlib.write_text(os.path.join(ws, hlib.DOC), edited)
        log_before = hlib.sha(hlib.log_path(ws))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "outside-edit", out["reason"])
        reason = out["reason"]
        self.assertIn("Status: signed off with conditions", reason, "what the Status: line holds")
        self.assertIn("landed", reason)
        self.assertNotIn("nothing was written", reason)
        self.assertFalse(out["wrote_nothing"], "the events landed and are reported as landed")
        self.assertEqual([w["kind"] for w in out["writes"]], ["records_log"])
        self.assertEqual(hlib.read_doc(ws), edited, "nothing reverted")
        self.assertEqual(hlib.sha(hlib.log_path(ws)), log_before)

    def test_a_kill_after_the_outcome_is_recorded_settles_too(self):
        ws, drive, run_dir, before, tmp = self.killed(CONDITIONS, "waive", window="outcome")
        log_before = hlib.sha(hlib.log_path(ws))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(hlib.sha(hlib.log_path(ws)), log_before)
        self.assertEqual(status_of(hlib.read_doc(ws), "A"), "Status: signed off")

    def test_a_kill_after_the_doc_write_completes_without_writing_again(self):
        ws, drive, run_dir, before, tmp = self.killed(CONDITIONS, "waive", window="doc")
        doc_before, log_before = hlib.sha(os.path.join(ws, hlib.DOC)), hlib.sha(hlib.log_path(ws))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual((hlib.sha(os.path.join(ws, hlib.DOC)), hlib.sha(hlib.log_path(ws))), (doc_before, log_before))
        self.assertEqual(hlib.read_doc(ws).count(hlib.HEADING % hlib.TODAY), 1)
        self.assertEqual([w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"], ["records_log", "build_doc"])


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheDriftCheck(unittest.TestCase):
    """`photograph`'s `card-drift` is a comparison of facts: a `Status:` line holding any value but the `card_set`'s
    before is no drift (a hand edit the importer absorbs), and a line that reads the after is none either."""

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-drift-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def waived(self):
        ws, info = hlib.make_repo(self.tmp, hlib.build_doc(**CONDITIONS), records=True)
        finding = hlib.state(ws)["findings"][0]["id"]
        drive, run_dir = hlib.start(self.tmp, ws)
        hlib.through_write(self, drive, self.tmp, run_dir, questions=[{"source": "chat-ruling", "text": "waive?"}],
                           answers=[{"question": "q1", "answered": True, "words": "ship it",
                                     "effect": {"kind": "waive", "finding": finding}}])
        return ws

    def photograph(self, ws, run):
        drive, run_dir = hlib.start(self.tmp, ws, run=run)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 0, (out, err))
        return drive(["photograph", "--run-dir", run_dir])

    def test_a_completed_waiver_is_no_drift(self):
        ws = self.waived()
        code, out, err = self.photograph(ws, "next")
        self.assertEqual(code, 0, (out, err))

    def test_a_line_put_back_to_the_before_is_drift(self):
        ws = self.waived()
        path = os.path.join(ws, hlib.DOC)
        text = hlib.read_doc(ws)
        a = text.index("## Slice A")
        b = text.index("## Slice B")
        testlib.write_text(path, text[:a] + text[a:b].replace("Status: signed off\n",
                                                             "Status: signed off with conditions\n") + text[b:])
        code, out, err = self.photograph(ws, "next")
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "card-drift", out["reason"])

    def test_a_line_set_to_a_third_value_is_no_drift(self):
        ws = self.waived()
        path = os.path.join(ws, hlib.DOC)
        text = hlib.read_doc(ws)
        a = text.index("## Slice A")
        b = text.index("## Slice B")
        testlib.write_text(path, text[:a] + text[a:b].replace("Status: signed off\n", "Status: built\n") + text[b:])
        code, out, err = self.photograph(ws, "next")
        self.assertEqual(code, 0, (out, err))


if __name__ == "__main__":
    unittest.main()
