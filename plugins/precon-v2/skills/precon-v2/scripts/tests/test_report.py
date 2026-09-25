"""precon-v2's `report` (precon-v2-contract.md section 8; required test 8 of lane P), through the real CLI.

The result validates (`validate-result.py`, the schema and S1 to S4); `station_result` carries
the doc, the board counts, the tier, the exit test and the gate, the gate its last field; the chat
block is v1's read-back rendered from the result; `report` on a run that has not written is the
wrong phase (exit 2, the next command named, nothing written), so a run with no gate line never
completes; a report repeated reports the recorded outcome and writes nothing.
"""
import json
import os
import unittest

import preconlib
import testlib
from preconlib import D


class _Report(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("report-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)

    def valid(self, run):
        code, out, err = testlib.run_script("validate-result.py", [run.run_file("result.json")], cwd=self.fx.cwd)
        self.assertEqual(code, 0, out + err)

    def full(self, fields, report_only=False, doc=True):
        if doc:
            preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run(report_only=report_only)
        run.select()
        self.assertEqual(run.harvest()[0], 0)
        code, out, err = run.record(preconlib.answer(run, **fields))
        self.assertEqual(code, 0, json.dumps(out))
        self.assertEqual(run.write()[0], 0)
        code, result, err = run.report()
        self.assertEqual(code, 10, err)
        self.valid(run)
        return run, result


class Completed(_Report):

    def test_a_completed_run(self):
        run, result = self.full({"lines": [preconlib.owner_line("Counts print to stdout", "print it")]})
        self.assertEqual((result["status"], result["stop_tag"]), ("completed", None))
        sr = result["station_result"]
        self.assertEqual(list(sr)[-1], "gate", "the gate is the last field")
        self.assertEqual(sr["gate"], preconlib.answer(run)["gate"])
        self.assertEqual(sr["doc"], os.path.join(self.fx.ws, preconlib.SCOPE_REL))
        self.assertEqual(sr["tier"], "bounded")
        self.assertEqual(sr["counts"], {"decided": 2, "assumed": 1, "parked": 2, "out_of_scope": 1})
        self.assertEqual(sr["board"], "decided 2 · assumed 1 · parked 2 · open your-calls 1")
        block = sr["chat_block"].split("\n")
        self.assertEqual(block[0], "PRECON: turnstile")
        self.assertEqual(block[1], "Doc: %s" % sr["doc"])
        self.assertEqual(block[2], "Counts: decided 2 · assumed 1 · parked 2 · out of scope 1")
        self.assertIn("Parked: Where the count is kept between sessions %s parked: needs research" % D, block)
        self.assertIn("Next: /blueprint when ready.", block)
        self.assertIn("Gate: %s" % sr["gate"], block)
        doc_writes = [w for w in result["writes"] if w["kind"] == "document"]
        self.assertEqual([w["path"] for w in doc_writes], [sr["doc"]])
        self.assertFalse(result["wrote_nothing"])
        self.assertEqual(result["invocation"]["session_id"], "session-test-1")
        self.assertEqual(result["selection"]["scope"]["outcome"], "one")

    def test_a_round_that_hands_on_to_the_next(self):
        run, result = self.full({"sitting": "continues",
                                 "gate": "round 1: storage and resets visited; encoder mode still open",
                                 "lines": [preconlib.owner_line("Counts print to stdout", "print it")]})
        self.assertEqual(result["status"], "completed")
        self.assertIn("Next: the next round (the sitting continues).", result["station_result"]["chat_block"])

    def test_a_repeated_report_writes_nothing(self):
        run, result = self.full({})
        digest = testlib.sha256_file(run.run_file("result.json"))
        code, again, err = run.report()
        self.assertEqual((code, again), (10, result))
        self.assertEqual(testlib.sha256_file(run.run_file("result.json")), digest)

    def test_report_only_says_so(self):
        run, result = self.full({"lines": [preconlib.owner_line("Counts print to stdout", "print it")]},
                                report_only=True)
        self.assertTrue(result["report_only"])
        self.assertTrue(result["wrote_nothing"])
        self.assertEqual([w for w in result["writes"] if w["kind"] != "run_artifact"], [])


class Stopped(_Report):

    def wrong_phase(self, run, next_command):
        before = sorted(os.listdir(run.run_dir))
        code, out, err = run.report()
        self.assertEqual(code, 2, "%s %s" % (out, err))
        self.assertIsNone(out, "nothing on stdout")
        self.assertIn(next_command, err)
        self.assertEqual(sorted(os.listdir(run.run_dir)), before, "nothing written")

    def test_report_on_a_run_with_no_answer_is_the_wrong_phase(self):
        preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run()
        run.select()
        run.harvest()
        self.wrong_phase(run, "record-answer")

    def test_report_on_a_run_only_checked_or_selected_is_the_wrong_phase(self):
        run = self.fx.new_run()
        self.wrong_phase(run, "select")
        run.select()
        self.wrong_phase(run, "harvest")

    def test_a_missing_gate_never_reaches_report(self):
        preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run()
        run.select()
        run.harvest()
        answer = preconlib.answer(run)
        del answer["gate"]
        code, out, err = run.record(answer)
        self.assertEqual(code, 5, json.dumps(out))
        self.assertIn("gate-missing", [r["rule"] for r in out["refusals"]])
        self.wrong_phase(run, "record-answer")

    def test_report_after_an_answer_but_before_write_is_usage(self):
        preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run()
        run.select()
        run.harvest()
        self.assertEqual(run.record(preconlib.answer(run))[0], 0)
        code, out, err = run.report()
        self.assertEqual(code, 2, err)
        self.assertIn("write", err)

    def test_the_napkin_outcome(self):
        run, result = self.full({"triage": {"tier": "napkin", "why": "one sentence", "no_scope_doc": True}},
                                doc=False)
        self.assertEqual((result["status"], result["stop_tag"]), ("stopped", "no-scope-doc"))
        sr = result["station_result"]
        self.assertIsNone(sr["doc"])
        self.assertEqual(sr["counts"], {"decided": 0, "assumed": 0, "parked": 0, "out_of_scope": 0})
        self.assertIn("Doc: none %s napkin, straight to /blueprint" % D, sr["chat_block"].split("\n"))
        self.assertTrue(result["wrote_nothing"])


if __name__ == "__main__":
    unittest.main()
