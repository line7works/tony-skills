"""`record-answer` (CR-11, CR-12): any question unanswered ends the run `gate-open` with NOTHING written (the doc,
the log, the run's pointer output, a memory folder) and the result in v1's gate-open form; an answer asserting a
card, an open item or a branch fact the script's read contradicts is refused (exit 5, nothing written); a waiver
or a reopening names a finding the record holds in a state it can take, in the owner's words.
"""
import os
import unittest

import hlib
import testlib

PUNCHED = dict(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                       ("B", "the spinner", "not started", "Slice A")],
               punch=hlib.review_block() + hlib.review_block(findings=[("MINOR", "src/turnstile.py:5",
                                                                         "the name is vague", "a reader guesses")],
                                                             date="2026-09-23"))


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheAnswer(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-answer-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.memory = os.path.join(self.tmp, "memory")
        os.makedirs(self.memory)
        testlib.write_text(os.path.join(self.memory, "MEMORY.md"), "# Memory Index\n")

    def ready(self, questions=(), records=True, **doc):
        ws, _ = hlib.make_repo(self.tmp, hlib.build_doc(**(doc or PUNCHED)), records=records)
        drive, run_dir = hlib.start(self.tmp, ws)
        gate = hlib.through_gate(self, drive, self.tmp, run_dir, questions=questions)
        return ws, drive, run_dir, gate

    def answer(self, drive, run_dir, answers=(), perishables=(), asserts=None):
        path = hlib.answers_file(self.tmp, run_dir, answers, perishables, asserts, name="a-%d.json" % len(os.listdir(self.tmp)))
        return drive(["record-answer", "--run-dir", run_dir, "--answer", path])

    def open_id(self, gate, location="src/turnstile.py:2"):
        return next(o["id"] for o in gate["open"] if o["location"] == location)

    def test_one_unanswered_question_is_gate_open_and_writes_nothing(self):
        ws, drive, run_dir, gate = self.ready(questions=[{"source": "session-question", "text": "is the wrap at 99"},
                                                         {"source": "chat-ruling", "text": "waive the MAJOR?"}])
        before = hlib.snapshot(ws, run_dir, extra=[self.memory])
        code, out, err = self.answer(drive, run_dir, answers=[
            {"question": "q1", "answered": True, "words": "yes, at 99", "effect": {"kind": "note"}},
            {"question": "q2", "answered": False}])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "gate-open"))
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(out["writes"] and [w["kind"] for w in out["writes"]] or [], ["run_artifact"] * len(out["writes"]))
        self.assertEqual(hlib.snapshot(ws, run_dir, extra=[self.memory]), before)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "pointer.json")))
        chat = out["station_result"]["chat"]
        self.assertTrue(chat.startswith("HANDOFF: turnstile \u2014 GATE OPEN, nothing written\n"), chat)
        self.assertIn("Unanswered: waive the MAJOR?", chat)
        self.assertNotIn("Thread is safe to clear", chat)

    def test_a_question_left_out_of_the_answers_is_unanswered(self):
        ws, drive, run_dir, gate = self.ready(questions=[{"source": "session-question", "text": "is the wrap at 99"}])
        before = hlib.snapshot(ws, run_dir)
        code, out, err = self.answer(drive, run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "gate-open"))
        self.assertEqual(hlib.snapshot(ws, run_dir), before)

    def test_an_asserted_card_the_records_contradict_is_refused(self):
        ws, drive, run_dir, gate = self.ready()
        before = hlib.snapshot(ws, run_dir)
        code, out, err = self.answer(drive, run_dir, asserts={"cards": {"A": "signed off"}})
        self.assertEqual(code, 5, (out, err))
        self.assertIn("A", out["reason"])
        self.assertEqual(hlib.snapshot(ws, run_dir), before)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "answers.json")))

    def test_an_asserted_open_item_the_records_do_not_hold_is_refused(self):
        ws, drive, run_dir, gate = self.ready()
        code, out, err = self.answer(drive, run_dir, asserts={"open": ["src/turnstile.py:9"]})
        self.assertEqual(code, 5, (out, err))

    def test_an_asserted_branch_fact_git_contradicts_is_refused(self):
        ws, drive, run_dir, gate = self.ready()
        code, out, err = self.answer(drive, run_dir, asserts={"branch": "main"})
        self.assertEqual(code, 5, (out, err))
        code, out, err = self.answer(drive, run_dir, asserts={"ahead": 7})
        self.assertEqual(code, 5, (out, err))
        code, out, err = self.answer(drive, run_dir, asserts={"tree": "dirty"})
        self.assertEqual(code, 5, (out, err))

    def test_assertions_that_agree_are_taken(self):
        ws, drive, run_dir, gate = self.ready()
        code, out, err = self.answer(drive, run_dir, asserts={"cards": {"A": "signed off with conditions"},
                                                              "open": ["src/turnstile.py:2"], "branch": "feat",
                                                              "ahead": 2, "tree": "clean"})
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "write")

    def test_a_waiver_of_a_finding_the_record_does_not_hold_open_is_refused(self):
        ws, drive, run_dir, gate = self.ready(questions=[{"source": "chat-ruling", "text": "waive it?"}])
        code, out, err = self.answer(drive, run_dir, answers=[
            {"question": "q1", "answered": True, "words": "waive it", "effect": {"kind": "waive",
                                                                                 "finding": "f1:00000000000000000000"}}])
        self.assertEqual(code, 5, (out, err))

    def test_a_reopening_of_an_open_finding_is_refused(self):
        ws, drive, run_dir, gate = self.ready(questions=[{"source": "chat-ruling", "text": "reopen it?"}])
        code, out, err = self.answer(drive, run_dir, answers=[
            {"question": "q1", "answered": True, "words": "reopen it",
             "effect": {"kind": "reopen", "finding": self.open_id(gate)}}])
        self.assertEqual(code, 5, (out, err))

    def test_words_the_ledger_line_cannot_carry_are_refused(self):
        ws, drive, run_dir, gate = self.ready(questions=[{"source": "chat-ruling", "text": "waive it?"}])
        for words in ("waive %s it" % hlib.M, "waive\u200bit", "two\nlines"):
            code, out, err = self.answer(drive, run_dir, answers=[
                {"question": "q1", "answered": True, "words": words,
                 "effect": {"kind": "waive", "finding": self.open_id(gate)}}])
            self.assertIn(code, (4, 5), (words, out, err))

    def test_a_next_slice_answer_must_name_a_candidate(self):
        doc = dict(slices=[("A", "the counter", "signed off", "nothing"), ("B", "the spinner", "not started", "Slice A"),
                           ("C", "the encoder", "not started", "nothing")])
        ws, drive, run_dir, gate = self.ready(records=False, **doc)
        code, out, err = self.answer(drive, run_dir, answers=[
            {"question": "r-next", "answered": True, "words": "do A again", "effect": {"kind": "next-slice", "slice": "A"}}])
        self.assertEqual(code, 5, (out, err))
        code, out, err = self.answer(drive, run_dir, answers=[
            {"question": "r-next", "answered": True, "words": "C first", "effect": {"kind": "next-slice", "slice": "C"}}])
        self.assertEqual(code, 0, (out, err))

    def test_an_answer_to_a_question_never_asked_is_refused(self):
        ws, drive, run_dir, gate = self.ready()
        code, out, err = self.answer(drive, run_dir, answers=[
            {"question": "q9", "answered": True, "words": "yes", "effect": {"kind": "note"}}])
        self.assertEqual(code, 5, (out, err))


if __name__ == "__main__":
    unittest.main()
