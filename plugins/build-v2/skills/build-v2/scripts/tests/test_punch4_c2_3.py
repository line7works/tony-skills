"""punch4-C2-3: after this run's receipted write, a hand change of the `Status:` line itself was
still reported as an edit "between the plan and the write" and "the `Status:` line was not
written" (E13 punch list round 4, from the round 3 checker's report, C2-3 remainder, MINOR).

The checker's shapes (`probe_f1.py <tree> revertedit@after_step`, `otherstatus@after_step`,
`revertcrlf@after_step`): `report` is killed right after the document step is receipted done
(`document_step.done` true, this run's `Status: built` on disk), then the person changes the line
itself: puts it back to the plan's value and adds another line; changes it to a third value
(`in progress`); puts the document back to the plan's text saved with CRLF line endings. `report`
again: `stopped / outside_edit`, and the reason said the edit came "between the plan and the
write" and that "the `Status:` line was not written". Both clauses are false, and the run knows it
from its own receipt.

The words now decide from the receipt first: a receipted write is this run's write whatever the
line reads now, so the reason says what the line reads on disk now, that this run wrote `built`
there earlier (its receipt records that write), and that the document is left as it is. The stop,
the landed card report and the no-second-write rule do not change.

`otherstatus@after_write` (the kill lands after the bytes are written and before the receipt
records the step): the run cannot know it wrote, so the round 3 words stay there, pinned below.

Real `build.py` in front of the real records component; the kill comes from the test-only
injector in `punch2_docwindow.py`.
"""
import os
import unittest

import punch2_docwindow as docwindow
import testlib
from test_transaction import _Transaction, card_sets

HAND_LINE = "- a punch item added by hand\n"


class _LineChangedByHand(_Transaction):

    def kill(self, mode):
        self.to_report()
        env = docwindow.env(self.env, self.scratch, mode, testlib.DOC_PATH)
        code, out, err = self.report(env=env)
        self.assertTrue(docwindow.fired(self.scratch, mode), out + err)
        self.assertEqual(self.status_line(), "built")
        receipt = self.receipt()
        self.assertEqual(bool(receipt["document_step"]["done"]), mode == "after_step")

    def put(self, data):
        with open(os.path.join(self.ws, testlib.DOC_PATH), "wb") as fh:
            fh.write(data)

    def doc_bytes(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), "rb") as fh:
            return fh.read()

    def stopped_twice(self, reads):
        """Two `report` passes: the same stop, the same words, the document never written."""
        before = self.doc_bytes()
        reasons = []
        for _ in range(2):
            code, out, err = self.report()
            self.assertEqual(code, 10, err)
            result = self.result()
            self.assertEqual((result["status"], result.get("stop_tag")),
                             ("stopped", "outside_edit"), out)
            self.assertEqual(self.doc_bytes(), before, "the document is left as the person left it")
            self.assertEqual(self.status_line(), reads)
            cards = card_sets(self.events(), "A")
            self.assertEqual(len(cards), 1, "one card event, never a second append")
            self.assertEqual([row.get("seq") for row in result["records"]["appended"]], [4],
                             "the landed card event is reported")
            reasons.append(result["reason"])
        self.assertEqual(reasons[0], reasons[1])
        return reasons[0]

    def receipted_words(self, reason, reads):
        self.assertNotIn("between the plan and the write", reason)
        self.assertNotIn("was not written", reason)
        self.assertIn("after this run's own `Status:` line reached it", reason)
        self.assertIn("reads `%s` in %s now" % (reads, testlib.DOC_PATH), reason)
        self.assertIn("this run's own document step wrote `built` there earlier", reason)
        self.assertIn("its receipt records that write", reason)
        self.assertIn("left as it is, neither written again nor reverted", reason)


class Punch4C23TheReceiptDecides(_LineChangedByHand):

    def test_line_put_back_with_another_edit(self):
        self.kill("after_step")
        self.put((testlib.BUILD_DOC + HAND_LINE).encode("utf-8"))
        self.receipted_words(self.stopped_twice("not started"), "not started")

    def test_line_changed_to_a_third_value(self):
        self.kill("after_step")
        text = self.doc_bytes().decode("utf-8").replace("Status: built", "Status: in progress")
        self.put(text.encode("utf-8"))
        self.receipted_words(self.stopped_twice("in progress"), "in progress")

    def test_line_put_back_saved_with_crlf(self):
        self.kill("after_step")
        self.put(testlib.BUILD_DOC.replace("\n", "\r\n").encode("utf-8"))
        self.receipted_words(self.stopped_twice("not started"), "not started")


class Punch4C23NoReceiptNoClaim(_LineChangedByHand):

    def test_third_value_after_the_write_before_its_receipt(self):
        # The receipt records no write, so the run cannot know the line was its: the round 3
        # words stay, and nothing is written.
        self.kill("after_write")
        text = self.doc_bytes().decode("utf-8").replace("Status: built", "Status: in progress")
        self.put(text.encode("utf-8"))
        reason = self.stopped_twice("in progress")
        self.assertIn("between the plan and the write", reason)
        self.assertIn("the `Status:` line was not written", reason)
        self.assertNotIn("its receipt records that write", reason)


if __name__ == "__main__":
    unittest.main()
