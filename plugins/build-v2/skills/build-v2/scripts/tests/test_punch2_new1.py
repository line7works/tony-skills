"""punch2-NEW-1: a `source_changed` stop said the `Status:` line "was not written" while the build
doc read `Status: built` (E13 punch list round 2, from the independent checker, MINOR).

The checker's shape (`probe_f1.py new restore@after_write`): `report` is killed right after the
build doc's `Status: built` bytes are written and before the receipt marks the document step done;
the source then moves (a tracked deletion restored, or an executable bit flipped); `report` again.
The stop is right (`stopped / source_changed`, card not moved, the landed card event kept and
reported, nothing appended again), but its reason said "the card was not moved and the slice's
`Status:` line was not written" while the document on disk reads `Status: built`.

The reason now says what is on disk, read from the build doc against the receipt's planned bytes:
this run's own document step wrote the line before the interruption and it is left as it is
(neither written again nor reverted). Controls: the kill after the append (before the document
half) still says the line was not written, and the document still reads `not started`.

Real `build.py` in front of the real records component; the kill in the document half comes from
the test-only injector in `punch2_docwindow.py`, the append kill from `shimlib.py`.
"""
import os
import stat
import unittest

import punch2_docwindow as docwindow
import shimlib
import testlib
from test_transaction import _Transaction, card_sets

WIDGET = "src/widget.py"
HEAD_BYTES = "def spin():\n    return 0\n"


class _NewOne(_Transaction):

    def kill_after_write(self):
        env = docwindow.env(self.env, self.scratch, "after_write", testlib.DOC_PATH)
        code, out, err = self.report(env=env)
        self.assertTrue(docwindow.fired(self.scratch, "after_write"), out + err)
        self.assertNotEqual(code, 10, "the first pass is killed in the document half")
        self.assertEqual(self.status_line(), "built", "the bytes landed before the kill")
        self.assertFalse(self.receipt()["document_step"]["done"])
        self.assertEqual(len(card_sets(self.events(), "A")), 1)

    def stopped(self):
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual((result["status"], result.get("stop_tag")), ("stopped", "source_changed"),
                         out)
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "never a second append")
        self.assertEqual(len(result["records"]["appended"]), 1, "the landed append is reported")
        return result


class Punch2New1TheWordsSayWhatIsOnDisk(_NewOne):

    def test_a_restored_deletion_after_the_document_bytes(self):
        os.remove(os.path.join(self.ws, WIDGET))
        self.to_report()
        self.kill_after_write()
        testlib.write_text(os.path.join(self.ws, WIDGET), HEAD_BYTES)
        result = self.stopped()
        reason = result["reason"]
        self.assertNotIn("`Status:` line was not written", reason)
        self.assertIn("already reads `built`", reason)
        self.assertIn("neither written again nor reverted", reason)
        self.assertEqual(self.status_line(), "built", "the line on disk is left as it is")
        self.assertEqual(self.stopped()["reason"], reason, "a second resume says the same")

    def test_an_exec_bit_after_the_document_bytes(self):
        testlib.write_text(os.path.join(self.ws, WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        self.kill_after_write()
        path = os.path.join(self.ws, WIDGET)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        reason = self.stopped()["reason"]
        self.assertNotIn("`Status:` line was not written", reason)
        self.assertIn("already reads `built`", reason)


class Punch2New1Control(_NewOne):

    def test_a_kill_before_the_document_half_still_says_not_written(self):
        testlib.write_text(os.path.join(self.ws, WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        shimlib.disarm(self.fault)
        path = os.path.join(self.ws, WIDGET)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        reason = self.stopped()["reason"]
        self.assertIn("`Status:` line was not written", reason)
        self.assertEqual(self.status_line(), "not started")


if __name__ == "__main__":
    unittest.main()
