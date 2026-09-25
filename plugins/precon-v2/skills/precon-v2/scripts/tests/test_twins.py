"""The twin rule (precon-v2-contract.md section 5, `retagged`), through the real CLI.

A line's words repeating a `Decisions:` or `Open:` ledger line under anything but that line's id
would leave the doc holding the line and its twin. The match reads every form of both texts: the
whole text (whitespace collapsed, case folded, invisibles dropped), the text with a trailing
` (waits on: <call>)` removed, and each whole field of a dashed or middle-dot line. An `Open:`
line this core wrote itself always carries that suffix (ruling R1 of round 3, CP1-1), so the
fixture here is a doc precon-v2 births. Twins inside one answer (CP2-2) and an out-of-scope item
repeating a parked or open line (CP2-3) are refused the same way.
"""
import json
import os
import unittest

import preconlib
import testlib
from preconlib import D

WAITS = "the owner's call on logging"
OPEN = "Whether resets are logged"
PARKED = "Where the count is kept between sessions"


class _Born(unittest.TestCase):
    """Run 1 births the doc with a decided line, a parked line and one open line (waits-on set)."""

    def setUp(self):
        self.tmp = testlib.make_scratch("twins-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)
        run = self.fx.new_run()
        run.select()
        self.assertEqual(run.harvest()[0], 0)
        code, doc, err = run.record(preconlib.answer(run, doc=preconlib.new_doc_fields(), lines=[
            preconlib.owner_line("Python 3.9 standard library only", "no dependencies on the bench"),
            {"text": PARKED, "tag": "parked", "reason": "needs research",
             "trace": {"kind": "owner_words", "ref": "I need to look into storage"}},
            {"text": OPEN, "tag": "open", "waits_on": WAITS, "trace": {"kind": "owner_words", "ref": "ask me later"}}],
            sitting="continues"))
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.report()[0], 10)
        self.path = os.path.join(self.fx.ws, preconlib.SCOPE_REL)
        self.text = preconlib.read(self.path)
        self.item = "%s (waits on: %s)" % (OPEN, WAITS)
        self.assertIn("Open: %s\n" % self.item, self.text, "precon-v2 wrote its open line with the suffix")
        self.ids = preconlib.ids(self.text)
        self.run_ = self.fx.new_run()
        self.run_.select()
        self.assertEqual(self.run_.harvest()[0], 0)

    def refused(self, answer, rule="retagged"):
        digest = testlib.tree_digest(self.fx.ws)
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 5, "%s %s" % (json.dumps(doc, ensure_ascii=False), err))
        rules = sorted(set(r["rule"] for r in doc["refusals"]))
        self.assertIn(rule, rules, json.dumps(doc["refusals"], ensure_ascii=False))
        self.assertEqual(testlib.tree_digest(self.fx.ws), digest)
        self.assertFalse(os.path.exists(self.run_.run_file("answer.json")))
        return rules

    def answer(self, **fields):
        return preconlib.answer(self.run_, **fields)


class TheOwnOpenLine(_Born):
    """CP1-1: the open line precon-v2 wrote, asserted as decided by its words, under any trace."""

    FORMS = (OPEN, "%s (waits on: %s)" % (OPEN, WAITS), OPEN.upper(), "  whether   RESETS are\tlogged  ",
             "Logging \u00b7 %s" % OPEN, "%s \u2013 the bench tech reads it" % OPEN, "%s -- yes" % OPEN,
             "Whether\u200b resets are logged")

    def test_every_form_of_its_words_under_owner_words_is_refused(self):
        for text in self.FORMS:
            self.refused(self.answer(lines=[preconlib.owner_line(text, "the bench tech reads it")]))

    def test_under_a_ledger_trace_to_another_line(self):
        decided = self.ids["Python 3.9 standard library only"]
        for text in (OPEN, self.item):
            self.refused(self.answer(lines=[{"text": text, "tag": "decided",
                                             "trace": {"kind": "ledger", "ref": decided}}]))

    def test_under_a_question_or_a_repo_path(self):
        q = {"id": "Q1", "text": "Who reads the bench log?", "touches": [], "answer": "the bench tech"}
        self.refused(self.answer(questions=[q], lines=[{"text": OPEN, "tag": "decided",
                                                        "trace": {"kind": "question", "ref": "Q1"}}]))
        self.refused(self.answer(lines=[{"text": OPEN, "tag": "decided",
                                         "trace": {"kind": "repo_path", "ref": "src/turnstile.py"}}]))

    def test_even_after_a_question_touched_it(self):
        q = {"id": "Q1", "text": "Are resets logged?", "touches": [self.ids[self.item]], "answer": "yes"}
        self.assertEqual(self.refused(self.answer(questions=[q], lines=[preconlib.owner_line(OPEN, "yes")])),
                         ["retagged"])

    def test_as_a_new_open_item_or_open_line(self):
        self.refused(self.answer(open_items=[OPEN.lower()]))
        self.refused(self.answer(lines=[{"text": OPEN, "tag": "open", "waits_on": "another call",
                                         "trace": {"kind": "owner_words", "ref": "still open"}}]))

    def test_settled_by_its_id_with_an_answered_question_is_accepted(self):
        q = {"id": "Q1", "text": "Are resets logged?", "touches": [self.ids[self.item]], "answer": "yes"}
        code, doc, err = self.run_.record(self.answer(questions=[q], lines=[
            {"text": self.item, "tag": "decided", "trace": {"kind": "ledger", "ref": self.ids[self.item]}}]))
        self.assertEqual(code, 0, json.dumps(doc))

    def test_a_line_that_only_shares_words_is_not_a_twin(self):
        code, doc, err = self.run_.record(self.answer(lines=[
            preconlib.owner_line("Resets are counted, never logged", "count them")]))
        self.assertEqual(code, 0, json.dumps(doc))

    def test_the_doc_never_holds_the_open_line_and_a_decided_twin(self):
        self.refused(self.answer(lines=[preconlib.owner_line(OPEN, "the bench tech reads it")]))
        self.assertEqual(preconlib.read(self.path), self.text)


class OneAnswer(_Born):
    """CP2-2: two lines of one answer with the same words (any tags) are refused."""

    def test_the_same_words_under_two_tags(self):
        for second in ({"text": "Colour", "tag": "parked", "reason": "needs prototype",
                        "trace": {"kind": "owner_words", "ref": "try one"}},
                       {"text": "  colour ", "tag": "decided", "trace": {"kind": "owner_words", "ref": "again"}},
                       {"text": "COLOUR", "tag": "assumed", "trace": {"kind": "assumed", "ref": "small"}},
                       {"text": "Colour", "tag": "open", "waits_on": "the owner's call",
                        "trace": {"kind": "owner_words", "ref": "later"}}):
            self.refused(self.answer(lines=[preconlib.owner_line("Colour", "blue"), second]))

    def test_an_open_line_and_its_suffixed_twin(self):
        self.refused(self.answer(lines=[
            {"text": "Colour", "tag": "open", "waits_on": "the owner's call",
             "trace": {"kind": "owner_words", "ref": "later"}},
            preconlib.owner_line("Colour (waits on: the owner's call)", "blue")]))

    def test_a_line_and_an_out_of_scope_item_or_an_open_item(self):
        self.refused(self.answer(lines=[preconlib.owner_line("Colour", "blue")], out_of_scope=[
            {"text": "colour", "reason": "declined", "trace": {"kind": "owner_words", "ref": "no colour"}}]))
        self.refused(self.answer(lines=[preconlib.owner_line("Colour", "blue")], open_items=["Colour"]))

    def test_a_needs_research_park_and_a_decided_twin(self):
        q = {"id": "Q1", "text": "Which sensor is accurate enough?", "touches": [], "answer": "park it",
             "needs_research": True}
        self.refused(self.answer(questions=[q], lines=[
            {"text": "Sensor accuracy", "tag": "parked", "reason": "needs research",
             "trace": {"kind": "question", "ref": "Q1"}},
            preconlib.owner_line("Sensor accuracy", "the cheap one")]))


class OutOfScope(_Born):
    """CP2-3: an out-of-scope item repeating a parked or open line's words, unless an answered
    question of this run touched that line."""

    def oos(self, text):
        return [{"text": text, "reason": "the owner ruled it out", "trace": {"kind": "owner_words", "ref": "drop it"}}]

    def test_a_twin_of_a_parked_or_open_line_is_refused(self):
        for text in (PARKED, PARKED.upper(), OPEN, self.item):
            self.refused(self.answer(out_of_scope=self.oos(text)))

    def test_a_twin_of_a_decided_line_is_refused(self):
        self.refused(self.answer(out_of_scope=self.oos("Python 3.9 standard library only")))

    def test_after_an_answered_question_touched_the_line_it_is_accepted(self):
        q = {"id": "Q1", "text": "Keep the storage question?", "touches": [self.ids[PARKED]],
             "answer": "no, drop it"}
        code, doc, err = self.run_.record(self.answer(questions=[q], out_of_scope=self.oos(PARKED)))
        self.assertEqual(code, 0, json.dumps(doc))

    def test_an_unanswered_or_research_question_does_not_open_the_way(self):
        for q in ({"id": "Q1", "text": "Keep the storage question?", "touches": [self.ids[PARKED]]},
                  {"id": "Q1", "text": "Keep the storage question?", "touches": [self.ids[PARKED]],
                   "answer": "park it", "needs_research": True}):
            self.refused(self.answer(questions=[q], out_of_scope=self.oos(PARKED)))


if __name__ == "__main__":
    unittest.main()
