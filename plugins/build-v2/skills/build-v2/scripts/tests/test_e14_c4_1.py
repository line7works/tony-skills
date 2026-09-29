"""E14 C4-1: an `outside_edit` stop of a run whose document step has no receipt still said the edit
came "between the plan and the write" and that "the `Status:` line was not written" (the E13 round
4 checker's C4-1, MINOR, words only; carried by A16 to the next step, pick P7 of E14).

The shape: `report` is killed right after the build doc's new bytes are written and before the
receipt records the document step (`after_write`), then the person changes the document so the
slice's `Status:` line no longer reads the value this run writes: a third value (`otherstatus`),
the line put back with another edit (`revertedit`), the document put back with CRLF line endings
(`revertcrlf`), or the line removed (`nostatus`). `report` again, twice: `stopped / outside_edit`.

The receipt records no write, so the pass cannot know whether the line was ever its own. The old
words asserted a history it cannot know. The new words are hedged and say only what the receipt
shows: its receipt records no write, so this pass cannot know whether the line was ever its own,
this run did not write the line as it now reads, and it is left as it is, neither written again
nor reverted. The receipted windows keep their words (punch4-C2-3 pins them), and so does an edit
a first pass meets between its own plan and its own write (punch3-C2-3's control pins that).

E14 slice 1 round 2 (the checker's C1-1 and C1-4): the words no longer say the run "was
interrupted", because a SECOND `report` after a first pass that stopped itself on an edit between
its plan and its write reaches the same branch and nothing was interrupted; and a line that can no
longer be read is not followed by "not the `built` this run writes".

Real `build.py` in front of the real records component; the kill comes from the test-only
injector in `punch2_docwindow.py`, the edit between plan and write from `shimlib.py`.
"""
import os
import unittest

import shimlib
import testlib
from test_punch3_c2_3 import EDIT, _DocEdit
from test_punch4_c2_3 import HAND_LINE, _LineChangedByHand

OLD_WORDS = ("between the plan and the write", "was not written", "interrupted")
HEDGE = ("its receipt records no write, so this pass cannot know whether the slice's `Status:` line "
         "was ever its own; the line ")
TAIL = "so this run did not write the line as it now reads, and it is left as it is, neither " \
       "written again nor reverted."


def assert_hedged(case, reason, reads):
    for words in OLD_WORDS:
        case.assertNotIn(words, reason)
    case.assertNotIn("its receipt records that write", reason)
    case.assertIn(HEDGE, reason)
    if reads is None:
        case.assertIn("the line can no longer be read in %s, %s" % (testlib.DOC_PATH, TAIL), reason)
        case.assertNotIn("this run writes", reason)
    else:
        case.assertIn("the line reads `%s` in %s now, not the `built` this run writes, %s"
                      % (reads, testlib.DOC_PATH, TAIL), reason)


class E14C41TheUnreceiptedWindowIsHedged(_LineChangedByHand):

    def hedged(self, reason, reads):
        assert_hedged(self, reason, reads)

    def test_otherstatus(self):
        self.kill("after_write")
        text = self.doc_bytes().decode("utf-8").replace("Status: built", "Status: in progress")
        self.put(text.encode("utf-8"))
        self.hedged(self.stopped_twice("in progress"), "in progress")

    def test_revertedit(self):
        self.kill("after_write")
        self.put((testlib.BUILD_DOC + HAND_LINE).encode("utf-8"))
        self.hedged(self.stopped_twice("not started"), "not started")

    def test_revertcrlf(self):
        self.kill("after_write")
        self.put(testlib.BUILD_DOC.replace("\n", "\r\n").encode("utf-8"))
        self.hedged(self.stopped_twice("not started"), "not started")

    def test_nostatus(self):
        self.kill("after_write")
        text = self.doc_bytes().decode("utf-8").replace("Status: built\n", "")
        self.put(text.encode("utf-8"))
        self.hedged(self.stopped_twice(None), None)



class E14C41ASecondPassAfterAStopOfItsOwn(_DocEdit):
    """C1-1: pass 1 meets an edit between its own plan and its own write and stops (punch3's words,
    true for that pass); pass 2 reopens a receipt with no recorded write, and nothing was
    interrupted, so its words say only what the receipt shows."""

    def test_the_second_pass_says_what_the_receipt_shows(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="mutate",
                      path=os.path.join(self.ws, testlib.DOC_PATH), text=EDIT)
        reasons = []
        for _ in range(2):
            code, out, err = self.report()
            self.assertEqual(code, 10, err)
            result = self.result()
            self.assertEqual((result["status"], result.get("stop_tag")), ("stopped", "outside_edit"), out)
            self.assertEqual(self.status_line(), "not started")
            reasons.append(result["reason"])
        self.assertIn("between the plan and the write", reasons[0])
        self.assertIn("the `Status:` line was not written", reasons[0])
        assert_hedged(self, reasons[1], "not started")

if __name__ == "__main__":
    unittest.main()
