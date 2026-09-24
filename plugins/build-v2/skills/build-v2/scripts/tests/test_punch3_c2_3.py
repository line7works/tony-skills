"""punch3-C2-3: an `outside_edit` stop said the slice's `Status:` line "was not written" while
this run's line was on disk (E13 punch list round 3, from the round 2 checker's report, MINOR,
NEW-1's class on another stop).

The checker's shape (`probe_f1.py <tree> docedit@after_step` and `docedit@after_write`): `report`
is killed after this run's `Status: built` bytes reached the build doc (after the document step is
receipted done, or right after the write and before the receipt), an unrelated line is then added
to the build doc by hand, `report` again: `stopped / outside_edit` with "... the `Status:` line
was not written", while the document reads `Status: built`.

The stop stays (the document holds an edit this run did not make); its words now say what is on
disk, read from the document: the line reads `built`, whether the receipt records this run's write
of it, and that it is left as it is, neither written again nor reverted. Control: an edit that
lands between the plan and the write (the line never written) still says the line was not
written.

Real `build.py` in front of the real records component; the kill comes from the test-only
injector in `punch2_docwindow.py`, the edit between plan and write from `shimlib.py`.
"""
import os
import unittest

import punch2_docwindow as docwindow
import shimlib
import testlib
from test_transaction import _Transaction, card_sets

EDIT = "\nA paragraph nobody in this run wrote.\n"


class _DocEdit(_Transaction):

    def kill(self, mode):
        self.to_report()
        env = docwindow.env(self.env, self.scratch, mode, testlib.DOC_PATH)
        code, out, err = self.report(env=env)
        self.assertTrue(docwindow.fired(self.scratch, mode), out + err)
        self.assertEqual(self.status_line(), "built")
        with open(os.path.join(self.ws, testlib.DOC_PATH), "a", encoding="utf-8") as fh:
            fh.write(EDIT)

    def stopped(self):
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual((result["status"], result.get("stop_tag")), ("stopped", "outside_edit"),
                         out)
        self.assertEqual(self.status_line(), "built", "the line is left as it is")
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        return result["reason"]


class Punch3C23TheWordsSayWhatIsOnDisk(_DocEdit):

    def test_after_the_receipted_step(self):
        self.kill("after_step")
        reason = self.stopped()
        self.assertNotIn("was not written", reason)
        self.assertIn("already reads `built`", reason)
        self.assertIn("its receipt records that write", reason)
        self.assertIn("neither written again nor reverted", reason)

    def test_after_the_write_before_its_receipt(self):
        self.kill("after_write")
        reason = self.stopped()
        self.assertNotIn("was not written", reason)
        self.assertIn("already reads `built`", reason)
        self.assertIn("neither written again nor reverted", reason)


class Punch3C23Control(_DocEdit):

    def test_an_edit_between_the_plan_and_the_write(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="mutate",
                      path=os.path.join(self.ws, testlib.DOC_PATH), text=EDIT)
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["stop_tag"], "outside_edit")
        self.assertIn("the `Status:` line was not written", result["reason"])
        self.assertIn("between the plan and the write", result["reason"])
        self.assertEqual(self.status_line(), "not started")


if __name__ == "__main__":
    unittest.main()
