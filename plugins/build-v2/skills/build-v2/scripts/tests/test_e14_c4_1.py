"""E14 C4-1: an `outside_edit` stop of a run whose document step has no receipt still said the edit
came "between the plan and the write" and that "the `Status:` line was not written" (the E13 round
4 checker's C4-1, MINOR, words only; carried by A16 to the next step, pick P7 of E14).

The shape: `report` is killed right after the build doc's new bytes are written and before the
receipt records the document step (`after_write`), then the person changes the document so the
slice's `Status:` line no longer reads the value this run writes: a third value (`otherstatus`),
the line put back with another edit (`revertedit`), the document put back with CRLF line endings
(`revertcrlf`), or the line removed (`nostatus`). `report` again, twice: `stopped / outside_edit`.

The run was interrupted before its receipt recorded a write, so it cannot know whether the line
was ever its own. The old words asserted a history it cannot know. The new words are hedged: the
run cannot know whether the line was ever its own, this run did not write the line as it now
reads, and it is left as it is, neither written again nor reverted. The receipted windows keep
their words (punch4-C2-3 pins them), and so does an edit a first pass meets between its own plan
and its own write (punch3-C2-3's control pins that).

Real `build.py` in front of the real records component; the kill comes from the test-only
injector in `punch2_docwindow.py`.
"""
import unittest

import testlib
from test_punch4_c2_3 import HAND_LINE, _LineChangedByHand

OLD_WORDS = ("between the plan and the write", "was not written")


class E14C41TheUnreceiptedWindowIsHedged(_LineChangedByHand):

    def hedged(self, reason, reads):
        for words in OLD_WORDS:
            self.assertNotIn(words, reason)
        self.assertNotIn("its receipt records that write", reason)
        self.assertIn("interrupted before its receipt recorded a write", reason)
        self.assertIn("cannot know whether the slice's `Status:` line was ever its own", reason)
        if reads is None:
            self.assertIn("can no longer be read in %s" % testlib.DOC_PATH, reason)
        else:
            self.assertIn("reads `%s` in %s now" % (reads, testlib.DOC_PATH), reason)
        self.assertIn("this run did not write the line as it now reads", reason)
        self.assertIn("left as it is, neither written again nor reverted", reason)

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


if __name__ == "__main__":
    unittest.main()
