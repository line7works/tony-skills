"""punch2-NEW-2: a run killed after its document step was receipted done, before `result.json`
was delivered, could never complete (E13 punch list round 2, from the independent checker, MINOR,
pre-existing).

The checker's shape (`probe_f1.py <new|old> control@after_step`): `report` is killed after the
document step is receipted done but before `result.json` is written; nothing else changes;
`report` again, twice. Before: `stopped / records_conflict / card.after 'not started' / moved
False / appended []`, "Another writer appended to it between preflight and report ... no record
was written", while the log held this run's own `card_set` and the document read `Status: built`.
The receipt read as finished, so the pass fell through to a fresh decision and met its own event
as a rival.

Now a resume that finds its own receipted, finished steps settles like any other resume and
delivers the result: `completed`, the card event at the seq the log holds (from the receipt),
the `Status:` line as written, no second append (the no-second-append rule holds), and the next
`report` returns the recorded outcome. The pin is still verified first on that pass: a source
that moved after the kill is the named `source_changed` stop, whose reason says the line already
reads `built` (NEW-1's words).

Real `build.py` in front of the real records component; the kill comes from the test-only
injector in `punch2_docwindow.py`.
"""
import os
import unittest

import punch2_docwindow as docwindow
import testlib
from test_transaction import _Transaction, card_sets

WIDGET = "src/widget.py"


class _NewTwo(_Transaction):

    def kill_after_step(self):
        testlib.write_text(os.path.join(self.ws, WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        env = docwindow.env(self.env, self.scratch, "after_step", testlib.DOC_PATH)
        code, out, err = self.report(env=env)
        self.assertTrue(docwindow.fired(self.scratch, "after_step"), out + err)
        self.assertNotEqual(code, 10)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "result.json")))
        self.assertTrue(self.receipt()["document_step"]["done"])
        self.assertTrue(self.receipt()["card_append"]["head"])
        self.assertEqual(self.status_line(), "built")
        cards = card_sets(self.events(), "A")
        self.assertEqual(len(cards), 1)
        return cards[0]


class Punch2New2TheRunFinishes(_NewTwo):

    def test_the_resume_delivers_completed_with_its_own_event(self):
        self.kill_after_step()
        seq = self.receipt()["card_append"]["seqs"][0]
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual((result["status"], result.get("stop_tag")), ("completed", None),
                         result.get("reason"))
        self.assertEqual((result["card"]["before"], result["card"]["after"],
                          result["card"]["moved"]), ("not started", "built", True))
        self.assertEqual([row["seq"] for row in result["records"]["appended"]], [seq])
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "never a second append")
        self.assertEqual(self.status_line(), "built")

    def test_a_second_resume_returns_the_recorded_outcome(self):
        self.kill_after_step()
        self.assertEqual(self.report()[0], 10)
        first = self.result()
        code, out, err = self.report()
        self.assertEqual(self.result(), first, "the result is not rewritten")
        self.assertIn("completed", out)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)


class Punch2New2ThePinStillComesFirst(_NewTwo):

    def test_a_source_move_after_the_kill_is_the_named_stop(self):
        self.kill_after_step()
        testlib.write_text(os.path.join(self.ws, "src/late.py"), "LATE = 1\n")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual((result["status"], result.get("stop_tag")), ("stopped", "source_changed"))
        self.assertIn("src/late.py", result["source_moved"])
        self.assertIn("already reads `built`", result["reason"])
        self.assertEqual(len(card_sets(self.events(), "A")), 1)


if __name__ == "__main__":
    unittest.main()
