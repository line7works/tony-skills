"""Report-only writes nothing (back-loop section 5): every phase reads, computes and checks, and what `write` would
have written is reported and left in the run directory, never written to the workspace or the log; a waiver it
would have recorded is reported, not appended. A whole run, report-only or not, leaves no `trace.jsonl` (CR-16:
handoff invokes no station, so it has no trace).
"""
import os
import unittest

import hlib
import testlib


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class ReportOnly(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-ro-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_a_report_only_run_writes_nothing_and_reports_what_it_would_have(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A")], punch=hlib.review_block())
        ws, _ = hlib.make_repo(self.tmp, text, records=True)
        before = hlib.snapshot(ws)
        drive, run_dir = hlib.start(self.tmp, ws, report_only=True)
        gate = hlib.through_gate(self, drive, self.tmp, run_dir,
                                 questions=[{"source": "chat-ruling", "text": "waive the double tap MAJOR?"}])
        finding = gate["open"][0]["id"]
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer", hlib.answers_file(
            self.tmp, run_dir, [{"question": "q1", "answered": True, "words": "waive it",
                                 "effect": {"kind": "waive", "finding": finding}}], ["a note"])])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(hlib.snapshot(ws), before)
        self.assertTrue(os.path.isfile(os.path.join(run_dir, "planned-doc.md")))
        self.assertEqual([e["kind"] for e in testlib.load_json(os.path.join(run_dir, "events.json"))],
                         ["waived", "card_set"], "the planned grant and the card it moves (A23 (2))")
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Report only; nothing written."])
        self.assertEqual(code, 10, (out, err))
        self.assertTrue(out["report_only"])
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual([w for w in out["writes"] if w["kind"] != "run_artifact"], [])
        self.assertEqual(hlib.snapshot(ws), before)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "trace.jsonl")))

    def test_a_whole_run_writes_no_trace(self):
        ws, _ = hlib.make_repo(self.tmp)
        drive, run_dir = hlib.start(self.tmp, ws)
        hlib.through_write(self, drive, self.tmp, run_dir)
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Done."])
        self.assertEqual(code, 10, (out, err))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "trace.jsonl")))
        self.assertIsNone(out["trace"])


if __name__ == "__main__":
    unittest.main()
