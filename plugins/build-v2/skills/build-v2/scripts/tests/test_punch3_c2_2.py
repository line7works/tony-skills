"""punch3-C2-2: a build doc put back by hand after this run's document step was receipted done was
written a second time (E13 punch list round 3, from the round 2 checker's report, MINOR, NEW-2's
neighbour).

The checker's shape (`probe_f1.py new revert@after_step`): `report` is killed after the document
step is receipted done and before `result.json` is written; the build doc is then put back by hand
to the bytes the plan read (`Status: not started`); `report` again. Round 2 settled, found the
document at the plan's `before` bytes, wrote `Status: built` a second time and reported
`completed`. `8133cb3` and `dfe8919` stopped there and left the hand revert. The build contract
names a hand edit BACK to the value the move started from as a case a person decides, and delivers
"the `Status:` line as written", never a second write.

Now the settle stops `outside_edit` for that shape, the line is left as the person put it, the
reason says what is on disk (the line reads `not started` again after this run's receipted write
of `built`) and that this run's card event landed and is reported as landed; nothing is appended
again, and the next `report` returns the recorded outcome. Controls: the untouched document still
completes (NEW-2), and a kill after the append (the document step never done) still writes the line
once and completes.

Real `build.py` in front of the real records component; the kill comes from the test-only
injector in `punch2_docwindow.py`, the append kill from `shimlib.py`.
"""
import os
import unittest

import punch2_docwindow as docwindow
import shimlib
import testlib
from test_transaction import _Transaction, card_sets

WIDGET = "src/widget.py"


class _Revert(_Transaction):

    def doc_bytes(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), "rb") as fh:
            return fh.read()

    def put_back(self, data):
        with open(os.path.join(self.ws, testlib.DOC_PATH), "wb") as fh:
            fh.write(data)

    def kill_after_step(self):
        testlib.write_text(os.path.join(self.ws, WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        planned_from = self.doc_bytes()
        env = docwindow.env(self.env, self.scratch, "after_step", testlib.DOC_PATH)
        code, out, err = self.report(env=env)
        self.assertTrue(docwindow.fired(self.scratch, "after_step"), out + err)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "result.json")))
        self.assertTrue(self.receipt()["document_step"]["done"])
        self.assertEqual(self.status_line(), "built")
        return planned_from


class Punch3C22AHandRevertIsLeftForAPerson(_Revert):

    def test_the_checkers_shape_stops_and_leaves_the_revert(self):
        before = self.kill_after_step()
        seq = self.receipt()["card_append"]["seqs"][0]
        self.put_back(before)
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual((result["status"], result.get("stop_tag")), ("stopped", "outside_edit"),
                         result.get("reason"))
        self.assertEqual(self.doc_bytes(), before, "the line is never written a second time")
        self.assertEqual(self.status_line(), "not started")
        reason = result["reason"]
        self.assertIn("reads `not started` again", reason)
        self.assertIn("wrote `built`", reason)
        self.assertIn("reported as landed", reason)
        self.assertNotIn("was not written", reason)
        self.assertEqual([row["seq"] for row in result["records"]["appended"]], [seq])
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "never a second append")

    def test_a_second_resume_returns_the_recorded_outcome(self):
        self.put_back(self.kill_after_step())
        self.assertEqual(self.report()[0], 10)
        first = self.result()
        self.report()
        self.assertEqual(self.result(), first)
        self.assertEqual(self.status_line(), "not started")
        self.assertEqual(len(card_sets(self.events(), "A")), 1)


class Punch3C22Controls(_Revert):

    def test_the_untouched_document_still_completes(self):
        self.kill_after_step()
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(self.result()["status"], "completed", self.result().get("reason"))
        self.assertEqual(self.status_line(), "built")
        self.assertEqual(len(card_sets(self.events(), "A")), 1)

    def test_a_kill_after_the_append_still_writes_the_line_once(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        shimlib.disarm(self.fault)
        self.assertEqual(self.status_line(), "not started")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(self.result()["status"], "completed", out)
        self.assertEqual(self.status_line(), "built")
        self.assertEqual(len(card_sets(self.events(), "A")), 1)


if __name__ == "__main__":
    unittest.main()
