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
ASSUMED = "One module, no package"
CGJ = chr(0x34F)      # COMBINING GRAPHEME JOINER, default-ignorable (the frame's invisibles drop it)
VS16 = chr(0xFE0F)    # VARIATION SELECTOR-16, the same


class _Born(unittest.TestCase):
    """Run 1 births the doc with a decided line, an assumed line, a parked line and one open line
    (waits-on set)."""

    WAITS = WAITS

    def setUp(self):
        self.tmp = testlib.make_scratch("twins-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)
        run = self.fx.new_run()
        run.select()
        self.assertEqual(run.harvest()[0], 0)
        code, doc, err = run.record(preconlib.answer(run, doc=preconlib.new_doc_fields(), lines=[
            preconlib.owner_line("Python 3.9 standard library only", "no dependencies on the bench"),
            {"text": ASSUMED, "tag": "assumed", "trace": {"kind": "assumed", "ref": "small and reversible"}},
            {"text": PARKED, "tag": "parked", "reason": "needs research",
             "trace": {"kind": "owner_words", "ref": "I need to look into storage"}},
            {"text": OPEN, "tag": "open", "waits_on": self.WAITS,
             "trace": {"kind": "owner_words", "ref": "ask me later"}}],
            sitting="continues"))
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.report()[0], 10)
        self.path = os.path.join(self.fx.ws, preconlib.SCOPE_REL)
        self.text = preconlib.read(self.path)
        self.item = "%s (waits on: %s)" % (OPEN, self.WAITS)
        self.assertIn("Open: %s\n" % self.item, self.text, "precon-v2 wrote its open line with the suffix")
        self.ids = preconlib.ids(self.text)
        self.run_ = self.fx.new_run()
        self.run_.select()
        self.assertEqual(self.run_.harvest()[0], 0)

    def refused(self, answer, rule="retagged"):
        digest = testlib.tree_digest(self.fx.ws)
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 5, "%s %s %s" % (json.dumps([line["text"] for line in answer["lines"]]),
                                                json.dumps(doc, ensure_ascii=False), err))
        rules = sorted(set(r["rule"] for r in doc["refusals"]))
        if rule is not None:
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


class _Traces(object):
    """The three traces of the round 3 checker's matrix: the owner's words, a repo path, and an
    unrelated answered question."""

    def under_each_trace(self, text):
        q = {"id": "Q1", "text": "Where does the counter print?", "touches": [], "answer": "stdout"}
        for extra, trace in (({}, {"kind": "owner_words", "ref": "he said so"}),
                             ({}, {"kind": "repo_path", "ref": "src/turnstile.py"}),
                             ({"questions": [q]}, {"kind": "question", "ref": "Q1"})):
            self.refused(self.answer(lines=[{"text": text, "tag": "decided", "trace": trace}], **extra),
                         rule=None)


class TheAssumedRow(_Born, _Traces):
    """CP1-1 (round 4, R1): the assumed row's words behind a decoration the frame strips (a period, a
    label, a bullet, a parenthesis), under every trace, are its twin (retagged); precon reads the
    words through the frame's own readings, so no decoration the frame sees through escapes here."""

    FORMS = (ASSUMED + ".", "R2 " + ASSUMED, "- " + ASSUMED, ASSUMED + " (parked: x)", ASSUMED + ";",
             "R2 %s." % ASSUMED, "- %s." % ASSUMED, ASSUMED + " (assumed: small)")

    def test_every_decoration_under_every_trace_is_refused(self):
        for text in self.FORMS:
            self.under_each_trace(text)


class TheOpenRowWithAnInvisible(_Born, _Traces):
    """CP1-1 (round 4, R1): the open row's words with a default-ignorable the frame drops (U+034F
    inside, U+FE0F at the end), bare and with its own suffix, under every trace, are refused; and
    the parked row the same."""

    def test_the_open_row(self):
        for words in (OPEN.replace(" ", " " + CGJ, 1), OPEN + VS16):
            for text in (words, "%s (waits on: %s)" % (words, self.WAITS)):
                self.under_each_trace(text)

    def test_the_parked_row(self):
        for text in (PARKED.replace(" ", CGJ + " ", 1), PARKED + VS16, "%s (waits on: x)." % PARKED):
            self.under_each_trace(text)

    def test_an_item_carrying_one_is_unrenderable(self):
        for text in ("Colour" + CGJ + " of the case", "Colour of the case" + VS16):
            rules = self.refused(self.answer(lines=[preconlib.owner_line(text, "blue")]), rule="unrenderable")
            self.assertEqual(rules, ["unrenderable"])


class TheOwnSuffixTheFrameCannotRead(_Born, _Traces):
    """R1: precon's own ` (waits on: <call>)` with a call the frame's parenthesis rule cannot strip
    (a parenthesis two deep): `without_waits` stays for this suffix only."""

    WAITS = "the bench call (see (Q2) first)"

    def test_the_bare_words_are_refused(self):
        self.assertIn("Open: %s\n" % self.item, self.text)
        for text in (OPEN, OPEN + ".", "- " + OPEN):
            self.under_each_trace(text)


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


class OneAnswerDecorated(_Born):
    """CP2-2 (round 4, R2): two entries of one answer whose frame readings meet are twins, whatever
    decoration one carries (the round 3 checker's section 2 rows)."""

    def colour(self, second):
        return self.answer(lines=[preconlib.owner_line("Colour", "blue"), second])

    def test_a_decided_line_and_a_decorated_parked_twin(self):
        for text in ("Colour.", "R2 Colour", "Colour" + CGJ, "- Colour"):
            self.refused(self.colour({"text": text, "tag": "parked", "reason": "needs prototype",
                                      "trace": {"kind": "owner_words", "ref": "try one"}}), rule=None)

    def test_a_line_and_a_decorated_out_of_scope_or_open_item(self):
        self.refused(self.answer(lines=[preconlib.owner_line("Colour", "blue")], out_of_scope=[
            {"text": "Colour.", "reason": "declined", "trace": {"kind": "owner_words", "ref": "no colour"}}]))
        self.refused(self.answer(lines=[preconlib.owner_line("Colour", "blue")], open_items=["Colour."]))

    def test_a_needs_research_park_and_a_decorated_decided_twin(self):
        q = {"id": "Q1", "text": "Which sensor is accurate enough?", "touches": [], "answer": "park it",
             "needs_research": True}
        self.refused(self.answer(questions=[q], lines=[
            {"text": "Sensor accuracy", "tag": "parked", "reason": "needs research",
             "trace": {"kind": "question", "ref": "Q1"}},
            preconlib.owner_line("Sensor accuracy.", "the cheap one")]))


class OneAnswerLabels(_Born):
    """R3 of round 5 (the outside reviewer's P-3, the lane half): inside one answer a line is read
    against the other entries as a row is (`forms(a) & row_forms(b)`, both ways), never two line-side
    readings against each other, whose unlabelled alternatives collide. Two new lines whose bare
    labels differ are two lines; the same words twice, or a labelled line beside its unlabelled
    words, still refuse. (`Q3:` against `Q4:`, the marked labels, is the frame's reading, E14-4.)"""

    def accepted(self, answer):
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 0, "%s %s" % (json.dumps(doc, ensure_ascii=False), err))

    def test_two_new_lines_with_different_bare_labels_are_two_lines(self):
        self.accepted(self.answer(lines=[preconlib.owner_line("Q3 budget", "three"),
                                         preconlib.owner_line("Q4 budget", "four")]))

    def test_different_bare_labels_across_a_line_and_an_out_of_scope_item(self):
        self.accepted(self.answer(lines=[preconlib.owner_line("R1 cache warmup", "keep it")], out_of_scope=[
            {"text": "R2 cache warmup", "reason": "declined", "trace": {"kind": "owner_words", "ref": "not that one"}}]))

    def test_different_bare_labels_across_a_line_and_an_open_item(self):
        self.accepted(self.answer(lines=[preconlib.owner_line("AC1 reset shown", "yes")], open_items=["AC2 reset shown"]))

    def test_the_same_labelled_words_twice_are_refused(self):
        self.refused(self.answer(lines=[preconlib.owner_line("Q4 budget", "four"),
                                        preconlib.owner_line("Q4 budget", "again")]))
        self.refused(self.answer(lines=[preconlib.owner_line("Q4 budget", "four"),
                                        preconlib.owner_line("q4  BUDGET.", "again")]))

    def test_a_labelled_line_beside_its_unlabelled_words_is_refused(self):
        for first, second in (("Q3 budget", "budget"), ("budget", "Q3 budget"), ("R2 Colour", "- Colour"),
                              ("Colour", "Colour \u2014 decided (x)")):
            self.refused(self.answer(lines=[preconlib.owner_line(first, "one"),
                                            preconlib.owner_line(second, "two")]))
        self.refused(self.answer(lines=[preconlib.owner_line("Q3 budget", "three")], out_of_scope=[
            {"text": "budget", "reason": "declined", "trace": {"kind": "owner_words", "ref": "no budget"}}]))


class OutOfScopeDecorated(_Born):
    """CP2-3 (round 4, R2): an out-of-scope item whose frame readings meet a parked, open or assumed
    row's, behind any decoration, is refused unless an answered question of this run touched it."""

    def oos(self, text):
        return [{"text": text, "reason": "the owner ruled it out", "trace": {"kind": "owner_words", "ref": "drop it"}}]

    def test_every_decoration_is_refused(self):
        for text in (PARKED + ".", "- " + PARKED, "R2 " + PARKED, PARKED.replace(" ", CGJ + " ", 1),
                     PARKED + " (parked: needs research)", OPEN + ".", OPEN + VS16, ASSUMED + "."):
            self.refused(self.answer(out_of_scope=self.oos(text)), rule=None)


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


class RuledOutAfterAQuestion(_Born):
    """CP3-2 (round 4, R4): an answered question of this run settles a parked, open or assumed row and
    the answer records that item as out of scope: the write removes the row, the doc holds the
    out-of-scope line and not the row, and the report and the next board count it once, under out of
    scope (the round 3 checker's probes/31 shapes)."""

    def rule_out(self, row_text, words):
        before = self.run_.state()[1]["counts"]
        q = {"id": "Q1", "text": "Keep this one?", "touches": [self.ids[row_text]], "answer": "no, drop it"}
        code, doc, err = self.run_.record(self.answer(questions=[q], out_of_scope=[
            {"text": words, "reason": "the owner dropped it", "trace": {"kind": "question", "ref": "Q1"}}]))
        self.assertEqual(code, 0, json.dumps(doc, ensure_ascii=False))
        code, doc, err = self.run_.write()
        self.assertEqual(code, 0, err)
        after = preconlib.read(self.path)
        ruled = "- %s %s the owner dropped it\n" % (words, D)
        self.assertEqual(after.count(ruled), 1, after)
        self.assertEqual(after.split("Out of scope:")[1].split("Research:")[0].count(ruled), 1, after)
        self.assertNotIn(row_text, after.replace(ruled, ""), after)
        code, result, err = self.run_.report()
        self.assertEqual(code, 10, err)
        counts = result["station_result"]["counts"]
        self.assertEqual(counts["out_of_scope"], 1)
        nxt = self.fx.new_run()
        nxt.select()
        code, harvest, err = nxt.harvest()
        self.assertEqual(code, 0, err)
        oos = "%s %s the owner dropped it" % (words, D)
        rows = [row for row in harvest["ledger"] if row["text"] in (row_text, oos)]
        self.assertEqual([(row["tag"], row["text"]) for row in rows], [("out-of-scope", oos)])
        now = nxt.state()[1]["counts"]
        self.assertEqual(now["out-of-scope"], before["out-of-scope"] + 1)
        return before, now

    def test_the_parked_row(self):
        before, now = self.rule_out(PARKED, PARKED)
        self.assertEqual(now["parked"], before["parked"] - 1)

    def test_the_open_row(self):
        before, now = self.rule_out(self.item, OPEN)
        self.assertEqual(now["open"], before["open"] - 1)
        self.assertIn("\nOpen:\nNext:", preconlib.read(self.path))

    def test_the_assumed_row(self):
        before, now = self.rule_out(ASSUMED, ASSUMED)
        self.assertEqual(now["assumed"], before["assumed"] - 1)

    def test_the_row_with_a_decoration(self):
        before, now = self.rule_out(PARKED, PARKED + ".")
        self.assertEqual(now["parked"], before["parked"] - 1)


if __name__ == "__main__":
    unittest.main()
