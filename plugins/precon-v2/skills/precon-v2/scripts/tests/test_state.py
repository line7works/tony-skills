"""precon-v2's own command `state` (precon-v2-contract.md section 3; required test 4 of lane P): the counted board.

The board is read from the doc as it stands, through the ledger reader, never remembered: a doc
holding every tag, then the same doc after a `write` added lines, then a run that starts with no
doc and creates one.
"""
import json
import os
import unittest

import preconlib
import testlib
from preconlib import D

EVERY_TAG = preconlib.SCOPE_DOC.replace(
    "Research:\n", "Research:\n- notes/encoder-survey.md\n").replace(
    "Open:\n- how often the counter resets\n", "Open:\n- how often the counter resets\n- who owns the bench log\n")


class State(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("state-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)

    def test_every_tag_counted(self):
        preconlib.ensure_scope_doc(self.fx, text=EVERY_TAG)
        run = self.fx.new_run()
        run.select()
        code, doc, err = run.state()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["counts"], {"decided": 1, "assumed": 1, "parked": 2, "open": 2, "out-of-scope": 1,
                                         "research": 1})
        self.assertEqual(doc["board"], "decided 1 · assumed 1 · parked 2 · open your-calls 2")
        self.assertEqual(doc["doc"], os.path.join(self.fx.ws, preconlib.SCOPE_REL))
        self.assertEqual(doc["interface_version"], 1)

    def test_state_before_select_is_usage(self):
        run = self.fx.new_run()
        self.assertEqual(run.state()[0], 2)

    def test_the_counts_change_after_a_write(self):
        preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run()
        run.select()
        self.assertEqual(run.harvest()[0], 0)
        first = run.state()[1]["counts"]
        answer = preconlib.answer(run, lines=[
            preconlib.owner_line("Counts print to stdout", "print it, nothing fancy"),
            {"text": "Reverse turns count as negative", "tag": "parked", "reason": "needs prototype",
             "trace": {"kind": "owner_words", "ref": "I want to see it on the rig first"}}])
        code, out, err = run.record(answer)
        self.assertEqual(code, 0, json.dumps(out))
        code, out, err = run.write()
        self.assertEqual(code, 0, err)
        code, doc, err = run.state()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["counts"]["decided"], first["decided"] + 1)
        self.assertEqual(doc["counts"]["parked"], first["parked"] + 1)

    def test_a_new_doc_is_counted_once_written(self):
        run = self.fx.new_run()
        run.select()
        run.harvest()
        code, doc, err = run.state()
        self.assertEqual((code, doc["doc"]), (0, None))
        self.assertEqual(doc["counts"]["decided"], 0)
        answer = preconlib.answer(run, doc=preconlib.new_doc_fields(),
                                  lines=[preconlib.owner_line("Python 3.9 standard library only", "no dependencies")])
        self.assertEqual(run.record(answer)[0], 0)
        self.assertEqual(run.write()[0], 0)
        code, doc, err = run.state()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["doc"], os.path.join(self.fx.ws, preconlib.SCOPE_REL))
        self.assertEqual(doc["counts"]["decided"], 1)

    def test_state_on_a_doc_the_reader_refuses_names_the_lines(self):
        preconlib.ensure_scope_doc(self.fx, text=preconlib.SCOPE_DOC.replace("parked: needs research", "parked: later"))
        run = self.fx.new_run()
        run.select()
        code, doc, err = run.state()
        self.assertEqual(code, 0, err)
        self.assertIsNone(doc["counts"])
        self.assertEqual([row["line"] for row in doc["ledger_refused"]], [7])
        self.assertIn("parked: later", json.dumps(doc["ledger_refused"], ensure_ascii=False))

    def test_state_writes_nothing(self):
        preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run()
        run.select()
        before = sorted(os.listdir(run.run_dir))
        digest = testlib.tree_digest(self.fx.ws)
        run.state()
        self.assertEqual(sorted(os.listdir(run.run_dir)), before)
        self.assertEqual(testlib.tree_digest(self.fx.ws), digest)


if __name__ == "__main__":
    unittest.main()
