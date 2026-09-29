"""The twin rule (precon-v2-contract.md section 5, `retagged`), through the real CLI.

A line's words repeating a `Decisions:` or `Open:` ledger line under anything but that line's id
would leave the doc holding the line and its twin. The match reads every form of both texts in the
frame's readings (`answer.forms` against `answer.row_forms`): the whole text (whitespace collapsed,
case folded, invisibles dropped), the text bare of every decoration the frame knows (a trailing
` (waits on: <call>)` among them), and each whole field of a dashed or middle-dot line. An `Open:`
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



class OutOfScopeByRow(_Born):
    """R8b (3b): an out-of-scope item may name the row it rules out by `row`, the id being the trace
    (A5(4)); the view hands it to the frame, which refuses an unknown row (`unknown-line`), and
    precon's own `retagged` refuses a row ruled out with no answered question of this run touching
    it, whatever the item's words; with its answered question the write removes the row."""

    def oos(self, text, row, trace=None):
        return [{"text": text, "reason": "the owner ruled it out", "row": row,
                 "trace": trace or {"kind": "owner_words", "ref": "drop it"}}]

    def test_an_unknown_row_is_unknown_line(self):
        self.assertEqual(self.refused(self.answer(out_of_scope=self.oos("The storage question", "dec-000000000000")),
                                      rule="unknown-line"), ["unknown-line"])
        self.assertEqual(preconlib.read(self.path), self.text)

    def test_a_parked_row_by_row_with_no_answered_question_is_refused(self):
        for text in ("The storage question", PARKED):
            self.assertEqual(self.refused(self.answer(out_of_scope=self.oos(text, self.ids[PARKED]))), ["retagged"])
        self.assertEqual(preconlib.read(self.path), self.text)

    def test_the_open_assumed_and_decided_rows_by_row_are_refused(self):
        for key in (self.item, ASSUMED, "Python 3.9 standard library only"):
            self.assertEqual(self.refused(self.answer(out_of_scope=self.oos("Something else entirely",
                                                                            self.ids[key]))), ["retagged"], key)

    def test_a_decided_row_by_row_is_refused_with_its_own_sentence(self):
        """R2 of 3b round 2 (wording only): an item naming a decided row by `row` is refused `retagged` with a
        sentence true of a decided row, with or without a question of this run touching it (the frame's
        `re-asked-decided` beside it then); never the word-twin sentence about an untouched question."""
        decided = self.ids["Python 3.9 standard library only"]
        q = {"id": "Q1", "text": "Still on the standard library?", "touches": [decided], "answer": "yes"}
        for questions, want in (([], ["retagged"]), ([q], ["re-asked-decided", "retagged"])):
            answer = self.answer(questions=questions, out_of_scope=self.oos("Something else entirely", decided))
            digest = testlib.tree_digest(self.fx.ws)
            code, doc, err = self.run_.record(answer)
            self.assertEqual(code, 5, json.dumps(doc, ensure_ascii=False))
            self.assertEqual(sorted(set(r["rule"] for r in doc["refusals"])), want)
            mine = [r for r in doc["refusals"] if r["rule"] == "retagged"]
            self.assertEqual(len(mine), 1, json.dumps(doc["refusals"], ensure_ascii=False))
            self.assertEqual(mine[0].get("out_of_scope"), 0)
            message = mine[0]["message"]
            self.assertNotIn("no answered question", message)
            self.assertIn("names the decided ledger line %s" % decided, message)
            self.assertIn("a decided line is settled in place and is not ruled out", message)
            self.assertEqual(testlib.tree_digest(self.fx.ws), digest)
            self.assertFalse(os.path.exists(self.run_.run_file("answer.json")))
        self.assertEqual(preconlib.read(self.path), self.text)

    def test_an_unanswered_or_research_question_does_not_open_the_way(self):
        for q in ({"id": "Q1", "text": "Keep the storage question?", "touches": [self.ids[PARKED]]},
                  {"id": "Q1", "text": "Keep the storage question?", "touches": [self.ids[PARKED]],
                   "answer": "park it", "needs_research": True}):
            self.refused(self.answer(questions=[q], out_of_scope=self.oos("The storage question", self.ids[PARKED])),
                         rule=None)

    def test_a_parked_row_ruled_out_by_row_with_its_answered_question_is_removed(self):
        q = {"id": "Q1", "text": "Keep the storage question?", "touches": [self.ids[PARKED]], "answer": "no, drop it"}
        code, doc, err = self.run_.record(self.answer(questions=[q], out_of_scope=self.oos(
            "The storage question", self.ids[PARKED], {"kind": "question", "ref": "Q1"})))
        self.assertEqual(code, 0, "%s %s" % (json.dumps(doc, ensure_ascii=False), err))
        self.assertEqual(self.run_.write()[0], 0)
        after = preconlib.read(self.path)
        self.assertNotIn(PARKED, after)
        self.assertEqual(after.split("Out of scope:")[1].split("Research:")[0].count(
            "- The storage question %s the owner ruled it out\n" % D), 1, after)



class LinesByRow(_Born):
    """R8a (3b): a line naming its row by `row` reads as one naming it by a `ledger` trace. The id is the
    trace (A5(4)), so the line is never twinned against its own row by words; it is passed forward
    under the row's tag, settled as decided in place by an answered question, or refused `retagged`,
    and the doc never holds the line beside its unchanged row (seam 17 O-2)."""

    def accepted(self, answer):
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 0, "%s %s" % (json.dumps(doc, ensure_ascii=False), err))
        self.assertEqual(self.run_.write()[0], 0)
        return preconlib.read(self.path)

    def refusals(self, answer):
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 5, "%s %s" % (json.dumps(doc, ensure_ascii=False), err))
        self.assertFalse(os.path.exists(self.run_.run_file("answer.json")))
        self.assertEqual(preconlib.read(self.path), self.text)
        return doc["refusals"]

    def test_a_parked_row_moved_to_assumed_by_row_is_refused(self):
        for text in ("Storage stays in memory", PARKED):
            rules = self.refused(self.answer(lines=[{"text": text, "tag": "assumed", "row": self.ids[PARKED],
                                                     "trace": {"kind": "assumed", "ref": "small and reversible"}}]))
            self.assertEqual(rules, ["retagged"], text)

    def test_a_parked_row_passed_forward_by_row_with_another_reason_is_refused(self):
        for text in ("The storage question", PARKED):
            refusals = self.refusals(self.answer(lines=[{"text": text, "tag": "parked", "reason": "needs prototype",
                                                         "row": self.ids[PARKED],
                                                         "trace": {"kind": "owner_words", "ref": "build one"}}]))
            self.assertEqual([r["rule"] for r in refusals], ["retagged"], text)
            self.assertIn("passes the parked line", refusals[0]["message"])

    def test_a_parked_row_passed_forward_by_row_with_its_reason_writes_nothing(self):
        for text in (PARKED, "The storage question"):
            self.setUp()
            after = self.accepted(self.answer(lines=[{"text": text, "tag": "parked", "reason": "needs research",
                                                      "row": self.ids[PARKED],
                                                      "trace": {"kind": "owner_words", "ref": "still open"}}]))
            self.assertEqual(after, self.text, text)

    def test_a_decided_row_passed_forward_by_row_is_not_twinned_by_its_own_words(self):
        decided = "Python 3.9 standard library only"
        after = self.accepted(self.answer(lines=[{"text": decided, "tag": "decided", "row": self.ids[decided],
                                                  "trace": {"kind": "owner_words", "ref": "still true"}}]))
        self.assertEqual(after, self.text)

    def test_a_decided_row_moved_back_by_row_is_the_frames_re_asked_decided(self):
        decided = "Python 3.9 standard library only"
        refusals = self.refusals(self.answer(lines=[{"text": decided, "tag": "parked", "reason": "needs research",
                                                     "row": self.ids[decided],
                                                     "trace": {"kind": "owner_words", "ref": "maybe not"}}]))
        self.assertIn("re-asked-decided", [r["rule"] for r in refusals])
        self.assertEqual([r for r in refusals if "repeats the" in r["message"]], [], json.dumps(refusals))

    def test_a_parked_or_open_row_settled_by_row_under_its_question_is_rewritten_in_place(self):
        for key in (PARKED, self.item):
            self.setUp()
            q = {"id": "Q1", "text": "Settle this one?", "touches": [self.ids[key]], "answer": "in memory only"}
            after = self.accepted(self.answer(questions=[q], lines=[
                {"text": "Kept in memory only", "tag": "decided", "row": self.ids[key],
                 "trace": {"kind": "question", "ref": "Q1"}}]))
            self.assertNotIn("Kept in memory only", after)
            settled = "%s %s decided (answer to Q1 (run %s): in memory only)" % (key, D, self.run_.run_id)
            self.assertEqual(after.count(settled), 1, after)
            self.assertNotIn("%s %s parked" % (key, D), after)

    def test_an_assumed_row_settled_by_row_without_a_question_has_no_source(self):
        rules = self.refused(self.answer(lines=[{"text": "One module it is", "tag": "decided",
                                                 "row": self.ids[ASSUMED],
                                                 "trace": {"kind": "owner_words", "ref": "keep it"}}]),
                             rule="decided-without-source")
        self.assertEqual(rules, ["decided-without-source"])

    def test_a_decided_line_by_row_traced_as_an_assumption_has_no_source(self):
        q = {"id": "Q1", "text": "Settle storage?", "touches": [self.ids[PARKED]], "answer": "memory"}
        self.refused(self.answer(questions=[q], lines=[{"text": "Kept in memory only", "tag": "decided",
                                                        "row": self.ids[PARKED],
                                                        "trace": {"kind": "assumed", "ref": "cheapest"}}]),
                     rule="decided-without-source")



class SettledAndRuledOut(_Born):
    """CP4-2 (R2 of 3b): one answer that settles a parked, open or assumed row as decided by its id (a
    `ledger` trace or `row`, with a line text other than the row's words) AND rules the same row out is
    refused `retagged` ("the answer settles <id> as decided and rules it out"), nothing written; the
    same answer without the out-of-scope item is accepted (the checker's probes/31, three row kinds)."""

    def both(self, key, words, by_row=False, rule_out=True):
        q = {"id": "Q9", "text": "Settle this one?", "touches": [self.ids[key]], "answer": "settled"}
        line = {"text": "x", "tag": "decided", "trace": {"kind": "ledger", "ref": self.ids[key]}}
        if by_row:
            line = {"text": "the storage question", "tag": "decided", "row": self.ids[key],
                    "trace": {"kind": "question", "ref": "Q9"}}
        oos = [{"text": words, "reason": "the owner ruled it out", "trace": {"kind": "question", "ref": "Q9"}}]
        return self.answer(questions=[q], lines=[line], out_of_scope=oos if rule_out else [])

    def test_each_row_kind_settled_and_ruled_out_is_refused(self):
        for key, words in ((PARKED, PARKED), (self.item, OPEN), (ASSUMED, ASSUMED)):
            for by_row in (False, True):
                code, doc, err = self.run_.record(self.both(key, words, by_row))
                self.assertEqual(code, 5, "%s %s %s" % (key, by_row, json.dumps(doc, ensure_ascii=False)))
                self.assertTrue(any(r["rule"] == "retagged" and "as decided and rules it out" in r["message"]
                                    for r in doc["refusals"]), json.dumps(doc["refusals"], ensure_ascii=False))
                self.assertFalse(os.path.exists(self.run_.run_file("answer.json")))
                self.assertEqual(preconlib.read(self.path), self.text)

    def test_ruled_out_by_row_while_settled_is_refused(self):
        q = {"id": "Q9", "text": "Settle this one?", "touches": [self.ids[PARKED]], "answer": "settled"}
        code, doc, err = self.run_.record(self.answer(questions=[q], lines=[
            {"text": "x", "tag": "decided", "trace": {"kind": "ledger", "ref": self.ids[PARKED]}}], out_of_scope=[
            {"text": "The storage question", "reason": "the owner ruled it out", "row": self.ids[PARKED],
             "trace": {"kind": "question", "ref": "Q9"}}]))
        self.assertEqual(code, 5, json.dumps(doc, ensure_ascii=False))
        self.assertTrue(any("as decided and rules it out" in r["message"] for r in doc["refusals"]))

    def test_the_same_answer_without_the_out_of_scope_item_is_accepted(self):
        for key, words in ((PARKED, PARKED), (self.item, OPEN), (ASSUMED, ASSUMED)):
            code, doc, err = self.run_.record(self.both(key, words, rule_out=False))
            self.assertEqual(code, 0, "%s %s" % (key, json.dumps(doc, ensure_ascii=False)))
            self.run_ = self.fx.new_run()
            self.run_.select()
            self.assertEqual(self.run_.harvest()[0], 0)



class AWaitsOnInTheMiddle(_Born):
    """CP4-3 (R3 of 3b): with precon's own suffix reader gone, a line holding `(waits on:` in its middle is
    read by the frame's readings alone: the checker's two probe lines (probes/13) no longer meet the open
    row `Who reads the log`, so they are no longer refused `retagged`."""

    PROBES = ("Who reads the log (waits on: nobody now) and who archives it (the bench tech)",
              "Who reads the log (waits on: done) plus a nightly export (cron)")

    def test_the_probe_lines_are_not_twins_of_the_open_row(self):
        run = self.run_
        code, doc, err = run.record(self.answer(lines=[
            {"text": "Who reads the log", "tag": "open", "waits_on": "the owner's call",
             "trace": {"kind": "owner_words", "ref": "later"}}], sitting="continues"))
        self.assertEqual(code, 0, json.dumps(doc, ensure_ascii=False))
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.report()[0], 10)
        self.assertIn("- Who reads the log (waits on: the owner's call)\n", preconlib.read(self.path))
        for text in self.PROBES:
            self.run_ = self.fx.new_run()
            self.run_.select()
            self.assertEqual(self.run_.harvest()[0], 0)
            code, doc, err = self.run_.record(self.answer(lines=[preconlib.owner_line(text, "the bench tech")]))
            self.assertEqual(code, 0, "%s %s" % (text, json.dumps(doc, ensure_ascii=False)))
        for text in ("Who reads the log", "Who reads the log (waits on: the owner's call)", "Who reads the log."):
            self.run_ = self.fx.new_run()
            self.run_.select()
            self.assertEqual(self.run_.harvest()[0], 0)
            self.refused(self.answer(lines=[preconlib.owner_line(text, "the bench tech")]), rule=None)


if __name__ == "__main__":
    unittest.main()
