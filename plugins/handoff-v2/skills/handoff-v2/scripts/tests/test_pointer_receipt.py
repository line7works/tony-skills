"""`report` and the Claude Code adapter's pointer step (A2 Q3, CR-13 (4)): on Claude Code the adapter's
`pointer.py` writes the pointer under the folder it is given and leaves a receipt, and `report` records its two
writes with their hashes; a receipt that does not hold is refused (exit 5, nothing recorded); on Codex no pointer is
written, a receipt is refused, and the result says no memory pointer was written.
"""
import json
import os
import subprocess
import sys
import unittest

import hlib
import testlib

POINTER = os.path.join(testlib.SKILL, "adapters", "claude-code", "pointer.py")


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class ThePointerStep(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-receipt-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.memory = os.path.join(self.tmp, "memory")
        os.makedirs(self.memory)

    def written(self, harness):
        ws, _ = hlib.make_repo(self.tmp)
        drive, run_dir = hlib.start(self.tmp, ws, harness=harness)
        hlib.through_write(self, drive, self.tmp, run_dir)
        return ws, drive, run_dir

    def pointer(self, run_dir):
        proc = subprocess.run([sys.executable, POINTER, "--run-dir", run_dir, "--memory-dir", self.memory],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()

    def test_on_claude_code_report_records_the_two_pointer_writes(self):
        ws, drive, run_dir = self.written("claude-code")
        code, out, err = self.pointer(run_dir)
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Captured."])
        self.assertEqual(code, 10, (out, err))
        kinds = [w["kind"] for w in out["writes"]]
        self.assertEqual(kinds.count("memory_pointer"), 2)
        self.assertTrue(out["station_result"]["pointer"]["written"])
        names = sorted(os.path.basename(w["path"]) for w in out["writes"] if w["kind"] == "memory_pointer")
        self.assertEqual(names, ["MEMORY.md", "handoff-turnstile.md"])

    def test_a_receipt_that_does_not_hold_is_refused(self):
        ws, drive, run_dir = self.written("claude-code")
        self.assertEqual(self.pointer(run_dir)[0], 0)
        with open(os.path.join(self.memory, "handoff-turnstile.md"), "a", encoding="utf-8") as fh:
            fh.write("edited by hand\n")
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Captured."])
        self.assertEqual(code, 5, (out, err))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "result.json")))

    def test_on_codex_no_pointer_is_written_and_a_receipt_is_refused(self):
        ws, drive, run_dir = self.written("codex-cli")
        code, out, err = self.pointer(run_dir)
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(os.listdir(self.memory), [])
        receipt = os.path.join(run_dir, "pointer-receipt.json")
        testlib.write_json(receipt, {"receipt_version": 1, "writes": []})
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Captured."])
        self.assertEqual(code, 5, (out, err))
        os.remove(receipt)
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Captured."])
        self.assertEqual(code, 10, (out, err))
        pointer = out["station_result"]["pointer"]
        self.assertFalse(pointer["written"])
        self.assertIn("no memory pointer", pointer["note"])
        self.assertNotIn("memory_pointer", json.dumps(out["writes"]))


if __name__ == "__main__":
    unittest.main()
