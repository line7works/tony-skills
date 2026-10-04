"""`gate` (CR-12): the questions the executor supplies from the session (v1's sources 1 and 2) and the ones the
record raises (sources 3 and 4: a next-slice ambiguity from the cards and the `Depends on:` chains, an open
`Questions:` line the doc records for the next slice). The gate writes nothing outside the run directory.
"""
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import nextmove  # noqa: E402

D = hlib.D


def cards(*pairs):
    return [{"name": name, "card": card, "depends": depends} for name, card, depends in pairs]


class TheCandidates(unittest.TestCase):
    """nextmove's reading of the cards and the chains, with no records involved."""

    def test_one_not_started_slice_whose_chain_is_clear(self):
        found = nextmove.candidates(cards(("A", "signed off", []), ("B", "not started", ["A"])))
        self.assertEqual(found["names"], ["B"])

    def test_two_open_slices_are_ambiguous(self):
        found = nextmove.candidates(cards(("A", "signed off", []), ("B", "not started", ["A"]),
                                          ("C", "not started", [])))
        self.assertEqual(found["names"], ["B", "C"])

    def test_a_chain_to_an_unsigned_slice_blocks(self):
        found = nextmove.candidates(cards(("A", "built", []), ("B", "not started", ["A"])))
        self.assertEqual(found["names"], [])

    def test_an_unreadable_chain_is_named(self):
        found = nextmove.candidates(cards(("A", "signed off", []), ("B", "not started", None)))
        self.assertEqual(found["names"], [])
        self.assertEqual(found["unreadable"], ["B"])

    def test_the_depends_on_values(self):
        names = ["A", "B", "C"]
        self.assertEqual(nextmove.parse_depends("nothing", names), [])
        self.assertEqual(nextmove.parse_depends("Slice A", names), ["A"])
        self.assertEqual(nextmove.parse_depends("Slice A, Slice B", names), ["A", "B"])
        self.assertEqual(nextmove.parse_depends("A and B", names), ["A", "B"])
        self.assertIsNone(nextmove.parse_depends("the encoder work", names))

    def test_asides_and_merge_words_are_set_aside_and_anything_else_is_unreadable(self):
        names = ["A", "B", "C"]
        self.assertEqual(nextmove.parse_depends("Slice A (its counter must be final)", names), ["A"])
        self.assertEqual(nextmove.parse_depends("nothing (runs beside lane 1)", names), [])
        self.assertEqual(nextmove.parse_depends("Slices A, B merged", names), ["A", "B"])
        self.assertEqual(nextmove.parse_depends("Slice C has merged", names), ["C"])
        self.assertIsNone(nextmove.parse_depends("Slice A, and an outside pull request merged", names))
        self.assertIsNone(nextmove.parse_depends("Slice A, after Slice B has merged", names))


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheGate(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-gate-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def gate(self, text, questions=()):
        ws, _ = hlib.make_repo(self.tmp, text)
        drive, run_dir = hlib.start(self.tmp, ws)
        before = hlib.snapshot(ws)
        out = hlib.through_gate(self, drive, self.tmp, run_dir, questions=questions)
        self.assertEqual(hlib.snapshot(ws), before)
        return out

    def test_no_question_anywhere_still_awaits_the_recorded_answer(self):
        out = self.gate(hlib.build_doc())
        self.assertEqual(out["questions"], [])
        self.assertEqual(out["next"], "record-answer")

    def test_the_session_questions_come_first_with_their_ids(self):
        out = self.gate(hlib.build_doc(), questions=[{"source": "session-question", "text": "is the wrap at 99"},
                                                     {"source": "chat-ruling", "text": "the owner said waive the MINOR"}])
        self.assertEqual([(q["id"], q["source"]) for q in out["questions"]],
                         [("q1", "session-question"), ("q2", "chat-ruling")])

    def test_an_ambiguous_next_slice_is_a_record_question_with_its_candidates(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A"),
                                      ("C", "the encoder", "not started", "nothing")])
        out = self.gate(text)
        rows = [q for q in out["questions"] if q["source"] == "next-slice"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "r-next")
        self.assertEqual(rows[0]["candidates"], ["B", "C"])

    def test_one_next_slice_raises_no_record_question(self):
        out = self.gate(hlib.build_doc())
        self.assertFalse([q for q in out["questions"] if q["source"] == "next-slice"])

    def test_an_open_questions_line_of_the_next_slice_is_asked(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A", ["does the spinner wrap at 99?"])])
        out = self.gate(text)
        rows = [q for q in out["questions"] if q["source"] == "doc-question"]
        self.assertEqual([(q["slice"], q["text"]) for q in rows], [("B", "does the spinner wrap at 99?")])

    def test_the_next_slices_questions_are_asked_behind_an_open_card(self):
        """A grant this run records may clear the open card, so the slice after it is the one about to be built."""
        text = hlib.build_doc(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A", ["does the spinner wrap at 99?"])],
                              punch=hlib.review_block())
        ws, _ = hlib.make_repo(self.tmp, text, records=True)
        drive, run_dir = hlib.start(self.tmp, ws)
        out = hlib.through_gate(self, drive, self.tmp, run_dir)
        rows = [q for q in out["questions"] if q["source"] == "doc-question"]
        self.assertEqual([(q["id"], q["slice"]) for q in rows], [("r-q1", "B")])

    def test_a_questions_line_of_a_slice_not_next_is_not_asked(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing", ["was the clock monotonic?"]),
                                      ("B", "the spinner", "not started", "Slice A")])
        out = self.gate(text)
        self.assertFalse([q for q in out["questions"] if q["source"] == "doc-question"])


if __name__ == "__main__":
    unittest.main()
