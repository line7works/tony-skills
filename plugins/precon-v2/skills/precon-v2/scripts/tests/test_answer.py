"""`record-answer`'s shared refusals (E14-11, reading CR-3, required test 7).

A question that re-asks a `decided` ledger line, and an asserted line that traces to no ledger
line, no repo path and no answered question of this run, are refused with exit 5 and nothing
written; a `parked` line passed forward as `decided` with no question that settled it is refused
the same way; the clean answer is accepted and recorded.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import answer, ledger  # noqa: E402

D = "\u2014"
SCOPE = ("# Widget %s scope doc (2026-09-20)\n\nIntent: turns\nDecisions:\n"
         "- Python 3.9 standard library only %s decided (the owner's words)\n"
         "- The storage format %s parked: needs research\n"
         "Out of scope: a web view %s declined\nResearch:\nOpen: how often it resets\n"
         "Next: /blueprint when ready.\n") % (D, D, D, D)


class _Answer(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("answer-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 0\n")
        self.run_dir = os.path.join(self.tmp, "run")
        os.makedirs(self.run_dir)
        self.ledger = ledger.read(SCOPE)
        self.ids = {row["text"]: row["id"] for row in self.ledger}

    def clean(self):
        return {"questions": [{"id": "Q1", "text": "Where does the count live?",
                               "touches": [self.ids["The storage format"]],
                               "answer": "in memory only"}],
                "lines": [{"text": "Python 3.9 standard library only", "tag": "decided",
                           "trace": {"kind": "ledger", "ref": self.ids["Python 3.9 standard library only"]}},
                          {"text": "The count lives in memory", "tag": "decided",
                           "trace": {"kind": "question", "ref": "Q1"}},
                          {"text": "spin() lives in src/widget.py", "tag": "decided",
                           "trace": {"kind": "repo_path", "ref": "src/widget.py"}},
                          {"text": "The storage format", "tag": "decided",
                           "trace": {"kind": "ledger", "ref": self.ids["The storage format"]}}]}

    def check(self, doc, **kw):
        return answer.check(doc, self.ledger, workspace=self.ws, **kw)

    def record(self, doc, **kw):
        return answer.record(self.run_dir, doc, self.ledger, workspace=self.ws, **kw)


class TheCleanAnswer(_Answer):

    def test_accepted_and_recorded(self):
        result = self.check(self.clean())
        self.assertEqual((result["exit"], result["refusals"]), (0, []))
        code, report = self.record(self.clean())
        self.assertEqual(code, 0, report)
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "answer.json")))
        self.assertEqual(testlib.load_json(os.path.join(self.run_dir, "answer.json")), self.clean())

    def test_parked_and_open_lines_passed_forward_as_themselves_are_accepted(self):
        doc = {"questions": [], "lines": [
            {"text": "The storage format", "tag": "parked",
             "trace": {"kind": "ledger", "ref": self.ids["The storage format"]}},
            {"text": "how often it resets", "tag": "open",
             "trace": {"kind": "ledger", "ref": self.ids["how often it resets"]}}]}
        self.assertEqual(self.check(doc)["refusals"], [])


class ReAskedDecidedLine(_Answer):

    def test_a_question_touching_a_decided_line_is_exit_5_and_nothing_written(self):
        doc = self.clean()
        doc["questions"].append({"id": "Q2", "text": "Python or something else?",
                                 "touches": [self.ids["Python 3.9 standard library only"]],
                                 "answer": "Python"})
        code, report = self.record(doc)
        self.assertEqual(code, 5)
        self.assertEqual(os.listdir(self.run_dir), [], "nothing written")
        (refusal,) = report["refusals"]
        self.assertEqual(refusal["rule"], "re-asked-decided")
        self.assertEqual(refusal["question"], "Q2")
        self.assertIn("Python 3.9 standard library only", refusal["message"])

    def test_a_question_touching_an_unknown_line_is_refused(self):
        doc = self.clean()
        doc["questions"][0]["touches"] = ["dec-00000000"]
        self.assertEqual(self.check(doc)["exit"], 5)


class ReAskedDecidedText(_Answer):
    """Finding 2 of the reviewer's short look (round 3): the decided line's text asked again with
    its id left out of `touches` (or another id named in its place) is still a re-ask."""

    def with_question(self, q):
        doc = self.clean()
        doc["questions"].append(q)
        return doc

    def test_the_decided_text_with_no_touches_is_exit_5_and_nothing_written(self):
        doc = self.with_question({"id": "Q999", "text": "Python 3.9 standard library only", "touches": [],
                                  "answer": "something else"})
        code, report = self.record(doc)
        self.assertEqual(code, 5, report)
        self.assertEqual(os.listdir(self.run_dir), [], "nothing written")
        (refusal,) = report["refusals"]
        self.assertEqual((refusal["rule"], refusal["question"], refusal["line_id"]),
                         ("re-asked-decided", "Q999", self.ids["Python 3.9 standard library only"]))
        self.assertIn("Python 3.9 standard library only", refusal["message"])

    def test_whitespace_and_case_do_not_hide_the_repeat(self):
        doc = self.with_question({"id": "Q999", "text": "  python 3.9\tSTANDARD   library only ",
                                  "answer": "something else"})
        self.assertEqual([r["rule"] for r in self.check(doc)["refusals"]], ["re-asked-decided"])

    def test_the_decided_text_touching_another_valid_line_is_refused(self):
        doc = self.with_question({"id": "Q999", "text": "Python 3.9 standard library only",
                                  "touches": [self.ids["The storage format"]], "answer": "something else"})
        refusals = self.check(doc)["refusals"]
        self.assertEqual([(r["rule"], r["line_id"]) for r in refusals],
                         [("re-asked-decided", self.ids["Python 3.9 standard library only"])])

    def test_the_decided_text_naming_its_line_is_refused_once_as_before(self):
        ident = self.ids["Python 3.9 standard library only"]
        doc = self.with_question({"id": "Q2", "text": "Python 3.9 standard library only", "touches": [ident],
                                  "answer": "Python"})
        (refusal,) = self.check(doc)["refusals"]
        self.assertEqual((refusal["rule"], refusal["question"], refusal["line_id"]), ("re-asked-decided", "Q2", ident))
        self.assertIn("re-asks a decided line", refusal["message"])

    def test_different_text_is_accepted(self):
        for text in ("Python 3.9 standard library only, or 3.12?", "The storage format"):
            doc = self.with_question({"id": "Q2", "text": text, "touches": [], "answer": "3.9"})
            self.assertEqual(self.check(doc), {"exit": 0, "refusals": []}, text)
        code, report = self.record(doc)
        self.assertEqual(code, 0, report)


class UntracedLine(_Answer):

    def refused_rule(self, line, **kw):
        doc = self.clean()
        doc["lines"].append(line)
        code, report = self.record(doc, **kw)
        self.assertEqual(code, 5, report)
        self.assertEqual(os.listdir(self.run_dir), [], "nothing written")
        return [r["rule"] for r in report["refusals"]]

    def test_no_trace(self):
        self.assertEqual(self.refused_rule({"text": "An invented constraint", "tag": "decided"}),
                         ["untraced"])

    def test_a_ledger_id_that_names_nothing(self):
        self.assertEqual(self.refused_rule({"text": "x", "tag": "decided",
                                            "trace": {"kind": "ledger", "ref": "dec-deadbeef"}}),
                         ["untraced"])

    def test_a_repo_path_that_does_not_exist(self):
        self.assertEqual(self.refused_rule({"text": "x", "tag": "decided",
                                            "trace": {"kind": "repo_path", "ref": "src/missing.py"}}),
                         ["untraced"])

    def test_a_parked_or_open_line_asserted_decided_by_text_under_another_trace(self):
        """CP1-1 (lane P's checker): the parked line's words as a decided line under owner_words or a repo
        path, no question touching it: quietly-resolved, the same as by ledger id."""
        allowed = ("ledger", "repo_path", "question", "owner_words")
        opened = [row for row in self.ledger if row["tag"] == "open"][0]
        parked = [row for row in self.ledger if row["tag"] == "parked"][0]
        for trace in ({"kind": "owner_words", "ref": "he said so"}, {"kind": "repo_path", "ref": "src/widget.py"}):
            rules = self.refused_rule({"text": "  " + opened["text"].upper() + " ", "tag": "decided", "trace": trace},
                                      allowed=allowed)
            self.assertEqual(rules, ["quietly-resolved"], trace)
        # the parked line the same way, once no answered question of this run touches it
        doc = self.clean()
        doc["questions"] = []
        doc["lines"] = [line for line in doc["lines"] if line["trace"]["kind"] != "question"
                        and line["text"] != "The storage format"]
        doc["lines"].append({"text": parked["text"], "tag": "decided", "trace": {"kind": "owner_words", "ref": "his words"}})
        result = self.check(doc, allowed=allowed)
        self.assertEqual([r["rule"] for r in result["refusals"]], ["quietly-resolved"])
        # and settled by an answered question, it is accepted
        doc["questions"] = [{"id": "Q9", "text": "Which storage?", "touches": [parked["id"]], "answer": "none"}]
        self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [])

    def test_the_quiet_upgrade_rule_sees_through_every_known_decoration(self):
        """The class, not the instance (four escapes in slice 2): a label in front, a waits-on or parked
        parenthesis behind, a tag tail behind, a bullet, invisibles, and the row itself decorated."""
        opened = [row for row in self.ledger if row["tag"] == "open"][0]
        words = opened["text"]
        shapes = [u"R2 \u2014 %s" % words, "AC1: %s" % words, "Q7 %s" % words, "- %s" % words,
                  "%s (waits on: the owner's call)" % words, "%s (parked: needs research)" % words,
                  u"%s \u2014 decided (his words)" % words, u"%s \u00b7 parked: needs prototype" % words,
                  u"%s\u200b" % words, u"R3 \u2014 %s (waits on: x)" % words]
        allowed = ("ledger", "repo_path", "question", "owner_words")
        for text in shapes:
            rules = self.refused_rule({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}},
                                      allowed=allowed)
            self.assertEqual(rules, ["quietly-resolved"], repr(text))
        # two decorations at once, list marks, wrappers, the wider invisibles (lane L's round 3 checker)
        for text in ["%s (parked: needs research)." % words, "%s (waits on: Q2);" % words, "1. %s" % words,
                     u"\u2022 %s" % words, "(R2) %s" % words, "[R2] %s" % words, "R-2: %s" % words, "AC-1: %s" % words,
                     "**%s**" % words, "`%s`" % words, '"%s"' % words, u"%s\u200e" % words, u"\u2063%s" % words,
                     u"%s\u034f" % words, "%s (waits on: the owner (Q2))." % words]:
            rules = self.refused_rule({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}},
                                      allowed=allowed)
            self.assertEqual(rules, ["quietly-resolved"], repr(text))
        # the ledger's own parenthesis wordings, a trailing question mark, more invisibles (lane A's round 3 checker)
        for text in ["%s (waiting on the bench rig)" % words, "%s (needs research)." % words, "%s?" % words,
                     u"%s\ufe0f" % words, "+ %s" % words, "2) %s" % words]:
            rules = self.refused_rule({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}},
                                      allowed=allowed)
            self.assertEqual(rules, ["quietly-resolved"], repr(text))
        # round 4 (lanes L and A): more decorations, a bracket parenthesis to any nesting, a tag tail with no spaces
        for text in ["%s [parked: needs research]" % words, "*%s*" % words, "_%s_" % words, "~~%s~~" % words,
                     "R2a: %s" % words, "R12.3 %s" % words, "AC1.2: %s" % words, u"\u2013 %s" % words, "a) %s" % words,
                     "(1) %s" % words, "### %s" % words, "> %s" % words, "- [ ] %s" % words, u"%s\u2026" % words,
                     u"%s\u2014decided (x)" % words, u"%s\u17b4" % words, u"%s\u180b" % words, "i. %s" % words, "[x] %s" % words, u"\u25e6 %s" % words,
                     # the seam 11 reader (CS11-2, CS11-5): a bold label, a fullwidth full stop, brackets, marks, guillemets,
                     # a five-digit label, a hyphen field, a section label, unassigned default-ignorables
                     "- **R2** %s" % words, "**R2:** %s" % words, u"%s\uff0e" % words, "(%s)" % words, "[%s]" % words,
                     u"\u2713 %s" % words, u"\u2192 %s" % words, u"\u2705 %s" % words, u"\u00ab%s\u00bb" % words,
                     "R10000 %s" % words, "storage - %s - one-way" % words, "Open: %s" % words, "Constraint: %s" % words,
                     u"%s\u2065" % words, u"%s\U000e0000" % words, u"%s\ufff0" % words, u"%s\u180f" % words,
                     # CS11-4: a second label behind a marked one, a re-cased marked label, a relabel with marks
                     "R2: %s" % words, "AC1: %s" % words, "r2: %s" % words, u"r2 \u2014 %s" % words, "D1: %s" % words,
                     u"R7 \u2014 %s" % words, "R7: %s" % words,
                     # the seam 12 reader (CS12-1, CS12-2): wrappers, labels, marks, section labels and tails by category
                     u"\u201e%s\u201c" % words, u"\u300c%s\u300d" % words, u"\uff08%s\uff09" % words, u"\u2039%s\u203a" % words,
                     "__R2__ %s" % words, "***R2*** %s" % words, "%s (R2)" % words, u"\u2610 %s" % words, u"\u2717 %s" % words,
                     u"\u21d2 %s" % words, u"\u2014 %s" % words, ">> %s" % words, "(a) %s" % words, "A. %s" % words, "1.1. %s" % words,
                     u"\u25cf %s" % words, "Deferred: %s" % words, "Poured concrete: %s" % words, "Not in this slice: %s" % words,
                     u"%s\u3001" % words, u"%s \u2014" % words, u"%s\u2014later" % words, "%s (deferred)" % words,
                     u"%s\uff08waits on: x\uff09" % words,
                     "%s (waits on: the bench call (see (Q2) first))" % words]:
            rules = self.refused_rule({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}},
                                      allowed=allowed)
            self.assertEqual(rules, ["quietly-resolved"], repr(text))
        # the false-positive side: a content token that looks like a label is not stripped (CS3-2 of lane A)
        self.ledger.append({"id": "prk-2", "tag": "parked", "section": "Decisions", "text": "R2 storage"})
        for text in ("S3 storage", "IPv6 support", "H264 encoding"):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [], text)
        doc = self.clean(); doc["lines"].append({"text": "storage", "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
        self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"], "R2 storage's words are storage")
        self.ledger.pop()
        # the false-positive side: a row's REASON field is not its words (CS3-2)
        self.ledger.append({"id": "defer-1", "tag": "parked", "section": "Decisions", "text": u"a web view \u2014 the module has no I/O"})
        doc = self.clean(); doc["lines"].append({"text": u"R4 \u2014 the module has no I/O", "tag": "decided",
                                                "trace": {"kind": "owner_words", "ref": "he said"}})
        self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [], "a reason field is not the row's words")
        doc = self.clean(); doc["lines"].append({"text": u"a web view", "tag": "decided",
                                                "trace": {"kind": "owner_words", "ref": "he said"}})
        self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"],
                         "the row's first field is its words")
        self.ledger.pop()
        # an owner_words ref of invisibles only is untraced
        doc = self.clean(); doc["lines"].append({"text": "a brand new line", "tag": "decided",
                                                "trace": {"kind": "owner_words", "ref": u"\u200b\u200e\u2065\U000e0000"}})
        self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["untraced"])
        # round 4 (lanes L and A, CS4-1, CS4-2, CS4-4): a label is part of the words when both sides carry one;
        # a field that is only a label has no words; a one-word later field of a line is no item
        self.ledger.append({"id": "prk-3", "tag": "parked", "section": "Decisions", "text": u"R5 \u2014 keep the tally in memory"})
        self.ledger.append({"id": "prk-4", "tag": "parked", "section": "Decisions", "text": "Q3 budget"})
        self.ledger.append({"id": "prk-5", "tag": "parked", "section": "Decisions", "text": u"Cost \u2014 the why"})
        self.ledger.append({"id": "prk-6", "tag": "parked", "section": "Decisions", "text": u"Firmware \u00b7 update path"})
        self.ledger.append({"id": "prk-7", "tag": "parked", "section": "Decisions", "text": u"Display \u00b7 10 inch"})
        for text in (u"R5 \u2014 a brand new requirement", "Q4 budget", "A3 budget", u"queue \u2014 SQS \u2014 cost",
                     u"Queue \u00b7 SQS \u00b7 cost", "R5", "R7 budget", "Firmware", u"Display \u00b7 7 inch", u"R5 \u2014 new"):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [], text)
        for text in ("Q3 budget", "budget", "Q3 budget.", u"R5 \u2014 keep the tally in memory", "keep the tally in memory",
                     u"cost \u2014 nothing else", u"storage \u2014 keep the tally in memory \u2014 one-way"):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"], text)
        # the seam 11 reader (CS11-3, CS11-7, CS11-4, CS11-5): composed and decomposed read the same; a mark is part of
        # a word; a second label behind a marked one is carried; a dotted label is its own key
        self.ledger.append({"id": "prk-8", "tag": "parked", "section": "Decisions", "text": u"r\u00e9sum\u00e9 storage"})
        self.ledger.append({"id": "prk-9", "tag": "parked", "section": "Decisions", "text": u"\u0e01\u0e34\u0e19"})
        self.ledger.append({"id": "prk-10", "tag": "parked", "section": "Decisions", "text": "A4 paper labels"})
        self.ledger.append({"id": "prk-11", "tag": "parked", "section": "Decisions", "text": "R2.1 storage"})
        for text in (u"re\u0301sume\u0301 storage", "C1: A4 paper labels", "Q3 budget."):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"], repr(text))
        self.ledger.append({"id": "prk-12", "tag": "parked", "section": "Decisions", "text": "keep the tally in memory"})
        self.ledger.append({"id": "prk-13", "tag": "parked", "section": "Decisions", "text": "use init hooks"})
        for text in ("**keep the tally** in memory", "keep the *tally* in memory", "keep the `tally` in memory"):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"], repr(text))
        doc = self.clean(); doc["lines"].append({"text": "use __init__ hooks", "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
        self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [], "an underscored name keeps its underscores")
        del self.ledger[-2:]
        for text in (u"\u0e01\u0e35\u0e19", u"n\u0303", "R21 storage", u"%s\u0301" % words):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [], repr(text))
        del self.ledger[-4:]
        for text in (u"Firmware \u00b7 update path", u"Display \u00b7 10 inch."):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"], text)
        del self.ledger[-5:]
        # and a plain line whose words are NOT a parked or open row is untouched by the rule
        doc = self.clean(); doc["lines"].append({"text": "R9 \u2014 a brand new requirement", "tag": "decided",
                                                "trace": {"kind": "owner_words", "ref": "he said"}})
        self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [])

    def test_the_seam_13_reader_shapes(self):
        """The seam 13 reader (CS13-1 to CS13-6): a wrapper pair with an apostrophe or a parenthesis inside, mark-like
        tokens of the Sm, Sk and quote categories, the ledger's tag tail with every parenthesis word, the templates'
        own section labels, a fullwidth colon, the highlight mark, a line break read as a space; on the row side
        too. And the other way: a sign token that is the line's meaning is part of its words on both sides."""
        allowed = ("ledger", "repo_path", "question", "owner_words")
        words = "keep the tally in memory"

        def refused(text, note=""):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["quietly-resolved"], repr(text) + note)

        def accepted(text, note=""):
            doc = self.clean(); doc["lines"].append({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [], repr(text) + note)

        # CS13-1: a typographic apostrophe or a parenthesis inside the wrapper pair
        self.ledger.append({"id": "prk-s14a", "tag": "parked", "section": "Decisions", "text": u"keep the owner\u2019s tally in memory"})
        apos = u"keep the owner\u2019s tally in memory"
        for text in (u"\u201e%s\u201c" % apos, u"\u300c%s\u300d" % apos, u"\uff08%s\uff09" % apos, u"\u2039%s\u203a" % apos,
                     u"\u3010%s\u3011" % apos, "{%s}" % apos, u"\u00bb%s\u00ab" % apos, '"%s"' % apos, u"\u201c%s\u201d" % apos,
                     "(%s)" % apos, "<%s>" % apos, u"\u00ab%s\u00bb" % apos):
            refused(text)
        self.ledger.pop()
        self.ledger.append({"id": "prk-s14b", "tag": "parked", "section": "Decisions", "text": "keep the tally (in memory)"})
        for text in (u"\u201ekeep the tally (in memory)\u201c", "(keep the tally (in memory))", "[keep the tally (in memory)]"):
            refused(text)
        self.ledger.pop()
        self.ledger.append({"id": "prk-s14c", "tag": "parked", "section": "Decisions", "text": words})
        for text in ("%s {parked: x}" % words, u"%s \u3014parked: x\u3015" % words, "%s <parked: x>" % words,
                     u"%s \u3008waits on: Q2\u3009" % words):
            refused(text)
        # CS13-2: Sm, Sk and quote glyphs as a leading or trailing token
        for mark in (u"=>", u"==>", u"<-", u"<=", u"\u25b7", u"\uff1e", u"\u226b", u"\u2212", u"\u2217", u"\u2218", u"\u22c5",
                     u"\u22b3", u"\u22c6", u"~", u"\u00d7", u"\u00bb", u"\u203a", u"\U0001f44d\U0001f3fd"):
            refused(u"%s %s" % (mark, words))
            refused(u"%s %s" % (words, mark))
        # CS13-4: the tag tail carries every word the parenthesis does
        for text in ("%s, tbd" % words, "%s; not now" % words, u"%s\u2014pending" % words, "%s, pending" % words,
                     "%s, not now" % words, "%s, undecided" % words, u"%s\u2014tbd" % words, "%s, to decide" % words,
                     "%s, to be decided" % words, "%s (to be decided)" % words):
            refused(text)
        # CS13-5: the templates' own section labels, a fullwidth colon, the highlight mark, a line break
        for text in ("Footprint: %s" % words, "Components: %s" % words, "Status: %s" % words, "Depends on: %s" % words,
                     "Handoffs: %s" % words, "Data flow: %s" % words, "Exit ramp: %s" % words, "Run log: %s" % words,
                     u"Deferred\uff1a %s" % words, u"Open\uff1a%s" % words, "==%s==" % words, "keep the ==tally== in memory",
                     u"keep the tally\u2028in memory", u"keep the tally\x85in memory", u"keep the tally\u2029in memory"):
            refused(text)
        # CS13-3, the guard: a marked line still meets an unmarked row and the reverse
        for text in (u"%s \u2014" % words, u"%s \u2713" % words, u"%s +" % words, u"\u2191 %s" % words):
            refused(text)
        self.ledger.pop()
        self.ledger.append({"id": "prk-s14d", "tag": "parked", "section": "Decisions", "text": u"%s \u2014" % words})
        refused(words, " (a marked row meets an unmarked line)")
        self.ledger.pop()
        # CS13-6: the seam 13 shapes and this round's wrapper shapes decorating the ROW, the line plain
        for shape in (u"\u201e%s\u201c", u"\u300c%s\u300d", u"\uff08%s\uff09", u"\u2039%s\u203a", "__R2__ %s", "***R2*** %s",
                      "%s (R2)", u"\u2610 %s", u"\u2717 %s", u"\u21d2 %s", u"\u2014 %s", ">> %s", "(a) %s", "A. %s", "1.1. %s",
                      u"\u25cf %s", "Deferred: %s", "Poured concrete: %s", "Not in this slice: %s", u"%s\u3001", u"%s \u2014",
                      u"%s\u2014later", "%s (deferred)", u"%s\uff08waits on: x\uff09", "%s (waits on: the bench call (see (Q2) first))",
                      "=> %s", u"\u25b7 %s", u"\u00bb %s", "%s, tbd", "%s; not now", "Footprint: %s", "==%s==",
                      "%s {parked: x}", u"\u3010%s\u3011"):
            self.ledger.append({"id": "prk-s14r", "tag": "parked", "section": "Decisions", "text": shape % words})
            refused(words, " (row side)")
            self.ledger.pop()
        self.ledger.append({"id": "prk-s14r", "tag": "parked", "section": "Decisions", "text": u"\u201ekeep the owner\u2019s tally in memory\u201c"})
        refused(apos, " (row side, apostrophe inside)")
        self.ledger.pop()
        # CS13-3: a sign token that carries the meaning is part of the words on both sides (a status mark is not: the
        # seam 14 reader's CS14-1, re-ruled in slice 3a; `status` with a check meets `status` with a cross)
        pairs = (("zoom -", "zoom +"), (u"sort \u2193", u"sort \u2191"), (u"units \u2032", u"units \u00b0"),
                 (u"rating \u2605", u"rating \u2605\u2605\u2605"), ("volume --", "volume ++"),
                 ("(US) data residency", "(EU) data residency"), ("(12V) supply", "(5V) supply"), ("(v1) API", "(v2) API"),
                 ("(CLI) rate limit", "(API) rate limit"),
                 # a sign that is part of the words (the seam 13 brief's accepted list) still holds
                 ("5 a month", "$5 a month"), ("use C", "use C++"), ("hashtag", "#hashtag"), ("name", "@name"),
                 ("20 of them", "20% of them"), ("logs", "~/logs"))
        for row, line in pairs:
            self.ledger.append({"id": "prk-s14p", "tag": "parked", "section": "Decisions", "text": row})
            accepted(line, " vs row %r" % row)
            self.ledger.pop()
        # and the list marks the parenthesis alternative still takes
        self.ledger.append({"id": "prk-s14c", "tag": "parked", "section": "Decisions", "text": words})
        for text in ("(a) %s" % words, "(i) %s" % words, "(12) %s" % words, "(iv) %s" % words, "(B) %s" % words):
            refused(text)
        self.ledger.pop()

    def test_an_open_line_asserted_decided_as_one_field_of_a_dashed_line(self):
        """CS-1 (lane A's round 2 checker): the open line's words as the decision field of a three-part line."""
        opened = [row for row in self.ledger if row["tag"] == "open"][0]
        for text in (u"storage \u2014 %s \u2014 one-way" % opened["text"], u"storage \u00b7 %s \u00b7 why" % opened["text"]):
            rules = self.refused_rule({"text": text, "tag": "decided", "trace": {"kind": "owner_words", "ref": "his words"}},
                                      allowed=("ledger", "repo_path", "question", "owner_words"))
            self.assertEqual(rules, ["quietly-resolved"], text)

    def test_an_open_line_asserted_decided_by_text_under_an_unrelated_ledger_trace(self):
        """CS-4 (lane L's round 2 checker): the open line's words traced to some OTHER ledger id."""
        opened = [row for row in self.ledger if row["tag"] == "open"][0]
        other = [row for row in self.ledger if row["tag"] == "decided"][0]
        rules = self.refused_rule({"text": opened["text"], "tag": "decided",
                                   "trace": {"kind": "ledger", "ref": other["id"]}})
        self.assertEqual(rules, ["quietly-resolved"])

    def test_a_repo_path_that_names_the_workspace_itself_or_git(self):
        """CS observation (lane L's checker): `.`, `./` and anything under `.git` are not traces."""
        for ref in (".", "./", ".git", ".git/HEAD", "src/.."):
            self.assertEqual(self.refused_rule({"text": "the whole repository", "tag": "decided",
                                                "trace": {"kind": "repo_path", "ref": ref}}),
                             ["untraced"], ref)

    def test_a_repo_path_that_leaves_the_workspace(self):
        self.assertEqual(self.refused_rule({"text": "x", "tag": "decided",
                                            "trace": {"kind": "repo_path", "ref": "../outside.txt"}}),
                         ["untraced"])

    def test_a_question_not_answered_in_this_run(self):
        self.assertEqual(self.refused_rule({"text": "x", "tag": "decided",
                                            "trace": {"kind": "question", "ref": "Q7"}}),
                         ["untraced"])

    def test_a_question_asked_and_not_answered(self):
        doc = self.clean()
        doc["questions"].append({"id": "Q3", "text": "later?", "touches": [], "answer": ""})
        doc["lines"].append({"text": "x", "tag": "decided", "trace": {"kind": "question", "ref": "Q3"}})
        self.assertEqual([r["rule"] for r in self.check(doc)["refusals"]], ["untraced"])

    def test_a_trace_kind_the_core_does_not_allow(self):
        self.assertEqual(self.refused_rule({"text": "x", "tag": "assumed",
                                            "trace": {"kind": "assumed", "ref": "small"}}),
                         ["untraced"])

    def test_a_trace_kind_the_core_allows(self):
        doc = self.clean()
        doc["lines"].append({"text": "x", "tag": "assumed", "trace": {"kind": "assumed", "ref": "small"}})
        allowed = answer.DEFAULT_TRACES + ("assumed",)
        self.assertEqual(self.check(doc, allowed=allowed)["refusals"], [])
        doc["lines"][-1]["trace"]["ref"] = "  "
        self.assertEqual([r["rule"] for r in self.check(doc, allowed=allowed)["refusals"]], ["untraced"])


class ParkedQuietlyResolved(_Answer):

    def test_a_parked_line_passed_forward_as_decided_without_its_question(self):
        doc = self.clean()
        doc["questions"] = []
        doc["lines"] = [l for l in doc["lines"] if l["trace"]["kind"] != "question"]
        code, report = self.record(doc)
        self.assertEqual(code, 5)
        self.assertEqual([r["rule"] for r in report["refusals"]], ["quietly-resolved"])
        self.assertEqual(os.listdir(self.run_dir), [])


    # C1-9 (the E14 slice 1 checker): only an ANSWERED question of this run settles a line; a
    # question asked and left without an answer that touches the parked or open line settles nothing.
    def unanswered(self, text):
        doc = {"questions": [{"id": "Q1", "text": "Is it settled?", "touches": [self.ids[text]],
                              "answer": ""}],
               "lines": [{"text": text, "tag": "decided", "trace": {"kind": "ledger", "ref": self.ids[text]}}]}
        return doc

    def test_a_parked_line_touched_only_by_an_unanswered_question(self):
        for empty in ("", "   ", None):
            doc = self.unanswered("The storage format")
            doc["questions"][0]["answer"] = empty
            code, report = self.record(doc)
            self.assertEqual(code, 5, (empty, report))
            self.assertEqual([r["rule"] for r in report["refusals"]], ["quietly-resolved"])
            self.assertEqual(os.listdir(self.run_dir), [], "nothing written")

    def test_an_open_line_touched_only_by_an_unanswered_question(self):
        code, report = self.record(self.unanswered("how often it resets"))
        self.assertEqual(code, 5, report)
        self.assertEqual([r["rule"] for r in report["refusals"]], ["quietly-resolved"])
        self.assertEqual(os.listdir(self.run_dir), [], "nothing written")

    def test_the_same_lines_touched_by_an_answered_question_are_accepted(self):
        for text in ("The storage format", "how often it resets"):
            doc = self.unanswered(text)
            doc["questions"][0]["answer"] = "settled: in memory only"
            self.assertEqual(self.check(doc), {"exit": 0, "refusals": []}, text)
        code, report = self.record(doc)
        self.assertEqual(code, 0, report)
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "answer.json")))


# The decorations the quiet-upgrade guard reads through (the shapes of
# `test_the_quiet_upgrade_rule_sees_through_every_known_decoration`), as formats of a row's words.
DECORATED = (u"R2 \u2014 %s", "AC1: %s", "Q7 %s", "- %s", "%s (waits on: the owner's call)", "%s (parked: needs research)",
             u"%s \u2014 decided (his words)", u"%s \u00b7 parked: needs prototype", u"%s\u200b", u"R3 \u2014 %s (waits on: x)",
             "%s (parked: needs research).", "%s (waits on: Q2);", "1. %s", u"\u2022 %s", "(R2) %s", "[R2] %s", "R-2: %s",
             "AC-1: %s", "**%s**", "`%s`", '"%s"', u"%s\u200e", u"\u2063%s", u"%s\u034f", "%s (waits on: the owner (Q2)).",
             "%s (waiting on the bench rig)", "%s (needs research).", "%s?", u"%s\ufe0f", "+ %s", "2) %s",
             "%s [parked: needs research]", "*%s*", "_%s_", "~~%s~~", "R2a: %s", "R12.3 %s", "AC1.2: %s", u"\u2013 %s",
             "a) %s", "(1) %s", "### %s", "> %s", "- [ ] %s", u"%s\u2026", u"%s\u2014decided (x)", "i. %s", "[x] %s",
             "- **R2** %s", "**R2:** %s", u"%s\uff0e", "(%s)", "[%s]", u"\u2713 %s", u"\u2192 %s", u"\u00ab%s\u00bb",
             "R10000 %s", "Open: %s", "Constraint: %s", u"%s\U000e0000", "r2: %s", "D1: %s",
             u"\u201e%s\u201c", u"\u300c%s\u300d", "__R2__ %s", "***R2*** %s", "%s (R2)", u"\u2610 %s", u"\u21d2 %s",
             ">> %s", "(a) %s", "A. %s", "Deferred: %s", "Poured concrete: %s", u"%s\u3001", u"%s \u2014",
             "%s (deferred)", u"%s\uff08waits on: x\uff09", "%s (waits on: the bench call (see (Q2) first))",
             "%s, tbd", "Footprint: %s", "==%s==", "%s {parked: x}")


class TheRowId(_Answer):
    """Ruling A5(4), the design's R4-1 to R4-4 and C3: a line that decides, settles, passes forward or moves a
    ledger row names that row by its id (`row`, defaulting from a `ledger` trace); a line that names its row is
    judged by the id alone; the text match is only a guard on the id-less path, and its refusal says to name
    the row."""

    allowed = ("ledger", "repo_path", "question", "owner_words")

    def parked(self):
        return self.ids["The storage format"]

    def settled(self, text, **line):
        row = {"text": text, "tag": "decided", "row": self.parked(), "trace": {"kind": "question", "ref": "Q1"}}
        row.update(line)
        return {"questions": [{"id": "Q1", "text": "Where does the count live?", "touches": [self.parked()],
                               "answer": "in memory only"}],
                "lines": [row]}

    def rules(self, doc):
        return [r["rule"] for r in self.check(doc, allowed=self.allowed)["refusals"]]

    def test_a_parked_row_settled_by_its_id_and_an_answered_question_is_accepted(self):
        doc = self.settled("The count lives in memory")
        self.assertEqual(self.check(doc, allowed=self.allowed), {"exit": 0, "refusals": []})
        code, report = self.record(doc, allowed=self.allowed)
        self.assertEqual(code, 0, report)

    def test_the_same_line_with_no_question_is_quietly_resolved(self):
        doc = self.settled("The count lives in memory", trace={"kind": "owner_words", "ref": "he said"})
        doc["questions"] = []
        code, report = self.record(doc, allowed=self.allowed)
        self.assertEqual(code, 5, report)
        self.assertEqual(os.listdir(self.run_dir), [], "nothing written")
        (refusal,) = report["refusals"]
        self.assertEqual(refusal["rule"], "quietly-resolved")
        self.assertIn("its ledger line %s is parked and no question of this run settled it" % self.parked(),
                      refusal["message"])
        # a question asked and left without an answer settles nothing
        doc = self.settled("The count lives in memory", trace={"kind": "owner_words", "ref": "he said"})
        doc["questions"][0]["answer"] = ""
        self.assertEqual(self.rules(doc), ["quietly-resolved"])

    def test_a_row_that_names_no_ledger_line_is_an_unknown_line(self):
        doc = self.settled("The count lives in memory", row="dec-000000000000")
        result = self.check(doc, allowed=self.allowed)
        self.assertEqual([(r["rule"], r.get("line_id")) for r in result["refusals"]],
                         [("unknown-line", "dec-000000000000")])
        self.assertIn("The count lives in memory", result["refusals"][0]["message"])

    def test_a_row_and_a_ledger_trace_that_differ_is_a_shape_refusal(self):
        other = self.ids["Python 3.9 standard library only"]
        doc = self.settled("The count lives in memory", trace={"kind": "ledger", "ref": other})
        result = self.check(doc, allowed=self.allowed)
        self.assertEqual([r["rule"] for r in result["refusals"]], ["shape"])
        self.assertIn("names row %s but traces to ledger row %s" % (self.parked(), other), result["refusals"][0]["message"])
        # the same id twice is one row
        doc = self.settled("The storage format", trace={"kind": "ledger", "ref": self.parked()})
        self.assertEqual(self.check(doc, allowed=self.allowed)["refusals"], [])
        # a row that is not a string is a shape refusal
        doc = self.settled("The count lives in memory", row=5)
        self.assertEqual(self.rules(doc), ["shape"])

    def test_a_line_naming_its_row_is_judged_by_the_id_never_by_its_words(self):
        """The row's own words, decorated every way the guard knows: accepted when a question settled the row;
        unsettled, refused once, by the id (never the id-less guard's message)."""
        words = "The storage format"
        for shape in DECORATED:
            text = shape % words
            doc = self.settled(text, trace={"kind": "owner_words", "ref": "he said"})
            self.assertEqual(self.check(doc, allowed=self.allowed)["refusals"], [], repr(text))
            doc["questions"] = []
            refusals = self.check(doc, allowed=self.allowed)["refusals"]
            self.assertEqual([r["rule"] for r in refusals], ["quietly-resolved"], repr(text))
            self.assertNotIn("without naming it", refusals[0]["message"], repr(text))

    def test_an_id_less_line_restating_another_parked_row_is_told_to_name_it(self):
        """The guard on the id-less path (C2): a decided line under `owner_words` that names no row and restates
        a parked row's words is refused, and the refusal says to name the row's id."""
        doc = {"questions": [], "lines": [{"text": "**The storage format**", "tag": "decided",
                                           "trace": {"kind": "owner_words", "ref": "he said"}}]}
        (refusal,) = self.check(doc, allowed=self.allowed)["refusals"]
        self.assertEqual(refusal["rule"], "quietly-resolved")
        self.assertIn("restates the parked ledger line %s without naming it" % self.parked(), refusal["message"])
        self.assertIn("carries the row's id (`row`)", refusal["message"])
        # a line naming ANOTHER row is on the guard's path for every row but its own
        opened = self.ids["how often it resets"]
        doc = {"questions": [{"id": "Q1", "text": "How often?", "touches": [opened], "answer": "daily"}],
               "lines": [{"text": "The storage format", "tag": "decided", "row": opened,
                          "trace": {"kind": "question", "ref": "Q1"}}]}
        (refusal,) = self.check(doc, allowed=self.allowed)["refusals"]
        self.assertEqual(refusal["rule"], "quietly-resolved")
        self.assertIn("without naming it", refusal["message"])
        # and settled by an answered question touching the row, the id-less line is accepted as before
        doc["questions"][0]["touches"].append(self.parked())
        self.assertEqual(self.check(doc, allowed=self.allowed)["refusals"], [])

    def test_a_decided_row_is_never_moved_back(self):
        """C3, as the control room narrowed it and C3A-2 widened it: a line naming a `decided` row as `parked`, `open`
        or `deferred` (architect's deferred list, which blueprint's ledger view reads as parked) is a re-ask; any other
        tag is the core's own pass-forward vocabulary and is not judged by the frame."""
        decided = self.ids["Python 3.9 standard library only"]
        for tag in ("open", "parked", "deferred"):
            for line in ({"text": "Python 3.9 standard library only", "tag": tag, "row": decided,
                          "trace": {"kind": "owner_words", "ref": "he said"}},
                         {"text": "Python 3.9 standard library only", "tag": tag,
                          "trace": {"kind": "ledger", "ref": decided}}):
                doc = {"questions": [], "lines": [line]}
                refusals = self.check(doc, allowed=self.allowed)["refusals"]
                self.assertEqual([(r["rule"], r.get("line_id")) for r in refusals], [("re-asked-decided", decided)],
                                 (tag, line))
        for tag in ("decided", "assumed", "constraint", "requirement", "poured", "struck", "carried"):
            for line in ({"text": "Python 3.9 standard library only", "tag": tag, "row": decided,
                          "trace": {"kind": "ledger", "ref": decided}},
                         {"text": "Python 3.9 standard library only", "tag": tag,
                          "trace": {"kind": "ledger", "ref": decided}}):
                doc = {"questions": [], "lines": [line]}
                self.assertEqual(self.check(doc, allowed=self.allowed)["refusals"], [], (tag, line))

    def test_a_row_of_any_section_prefix_a_ledger_view_emits(self):
        """The control room's ruling on the row pattern: the schema takes any lower-case section prefix and twelve
        hex digits (blueprint's view holds `arch-` and `defer-` rows); `check` proves the id exists."""
        import json
        import jsonschema
        with open(os.path.join(testlib.REF, "answer.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        rows = []

        def walk(node):
            if isinstance(node, dict):
                props = node.get("properties")
                # the line's row (inspect's top-level `row` is its readers row, another field)
                if isinstance(props, dict) and isinstance(props.get("row"), dict) and \
                        str(props["row"].get("description", "")).startswith("the id of the ledger row"):
                    rows.append(props["row"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(schema)
        cls = jsonschema.validators.validator_for(schema)
        good = "arch-0123456789ab"
        bad = ("ARCH-0123456789ab", "arch_0123456789ab", "0123456789ab")
        for row in rows:
            self.assertTrue(cls(row).is_valid(good))
            self.assertTrue(cls(row).is_valid("defer-0123456789ab-2"))
            for value in bad:
                self.assertFalse(cls(row).is_valid(value), value)
        self.ledger.append({"id": good, "tag": "decided", "section": "Poured concrete", "text": "one queue per tenant"})
        doc = {"questions": [], "lines": [{"text": "one queue per tenant", "tag": "decided", "row": good,
                                           "trace": {"kind": "owner_words", "ref": "he said"}}]}
        self.assertEqual(self.check(doc, allowed=self.allowed)["refusals"], [])
        for value in bad:
            doc["lines"][0]["row"] = value
            self.assertEqual(self.rules(doc), ["unknown-line"], value)

    def test_a_ledger_trace_alone_still_names_its_row(self):
        """R4-1: `row` absent and a `ledger` trace: the row is the trace's ref, so every answer written before
        the id keeps its meaning."""
        doc = {"questions": [], "lines": [{"text": "The storage format", "tag": "decided",
                                           "trace": {"kind": "ledger", "ref": self.parked()}}]}
        (refusal,) = self.check(doc, allowed=self.allowed)["refusals"]
        self.assertEqual(refusal["rule"], "quietly-resolved")
        self.assertNotIn("without naming it", refusal["message"])


class MarkedLabelsAreKeyed(_Answer):
    """Ruling A5(1), E14-4 read again: a MARKED item label (`AC1:`, `(R2)`, `[R2]`, `**R2:**`, `R2 <dash>`, a
    trailing `(R2)`) is part of the words on both sides, as a bare label (`R2 `) is; it is still stripped from
    the words. Each consequence through `forms` and `row_forms`, and through the check a decided line meets."""

    allowed = ("ledger", "repo_path", "question", "owner_words")

    def meets(self, line, row):
        return bool(answer.forms(line) & answer.row_forms(row))

    def rules(self, line, row):
        self.ledger.append({"id": "prk-m", "tag": "parked", "section": "Decisions", "text": row})
        try:
            doc = self.clean()
            doc["lines"].append({"text": line, "tag": "decided", "trace": {"kind": "owner_words", "ref": "he said"}})
            return [r["rule"] for r in self.check(doc, allowed=self.allowed)["refusals"]]
        finally:
            self.ledger.pop()

    def test_two_different_labels_never_meet(self):
        for line, row in (("R2: budget", "R3: budget"), ("AC1: budget", "AC2: budget"), ("Q4: budget", "Q3: budget"),
                          ("**R2:** budget", "**R3:** budget"), ("(R2) budget", "(R3) budget"), ("[R2] budget", "[R3] budget"),
                          ("budget (R2)", "budget (R3)"), (u"R2 \u2014 budget", u"R3 \u2014 budget"),
                          ("R2: budget", "R3 budget"), ("R2 budget", "R3: budget"), ("- **R2** budget", "R3: budget")):
            self.assertFalse(self.meets(line, row), (line, row))
            self.assertEqual(self.rules(line, row), [], (line, row))

    def test_a_marked_label_meets_an_unlabelled_row_and_its_own_label(self):
        for line in ("AC1: budget", "**R2:** budget", "(R2) budget", "[R2] budget", "budget (R2)", u"R2 \u2014 budget",
                     "- **R2** budget", "r2: budget"):
            self.assertTrue(self.meets(line, "budget"), line)
            self.assertEqual(self.rules(line, "budget"), ["quietly-resolved"], line)
            self.assertTrue(self.meets("budget", line), "row %r" % line)
            self.assertEqual(self.rules("budget", line), ["quietly-resolved"], "row %r" % line)
        for line, row in (("R2: budget", "R2: budget"), ("R2: budget", "R2 budget"), ("R2 budget", "(R2) budget"),
                          ("**R2:** budget", "budget [R2]"), ("r2: budget", "R2: budget")):
            self.assertTrue(self.meets(line, row), (line, row))
            self.assertEqual(self.rules(line, row), ["quietly-resolved"], (line, row))

    def test_a_marked_label_is_keyed_and_a_bare_one_behind_it_is_words(self):
        self.assertEqual(answer._split("R2: Q3 budget"), ("r2", "q3 budget"))
        self.assertEqual(answer.bare("R2: Q3 budget"), "q3 budget")
        self.assertEqual(answer._split("**AC-1:** budget"), ("ac1", "budget"))
        self.assertEqual(answer._split("budget (R2)"), ("r2", "budget"))
        self.assertTrue(self.meets("R2: Q3 budget", "Q3 budget"))
        self.assertEqual(self.rules("R2: Q3 budget", "Q3 budget"), ["quietly-resolved"])
        self.assertFalse(self.meets("R2: Q3 budget", "Q4 budget"))
        self.assertEqual(self.rules("R2: Q3 budget", "Q4 budget"), [])

    def test_a_text_that_is_only_a_label_has_no_words(self):
        for text, key in (("R2:", "r2"), ("(AC1)", "ac1"), ("[R2]", "r2"), ("**R2:**", "r2"), ("R2", "r2")):
            self.assertEqual(answer._split(text), (key, ""), text)
            self.assertEqual(answer.forms(text), set(), text)
            self.assertEqual(self.rules(text, "R2: budget"), [], text)

    def test_every_decoration_on_a_labelled_line_still_meets_an_unlabelled_row(self):
        words = "keep the tally in memory"
        for shape in DECORATED:
            self.assertTrue(self.meets(shape % words, words), repr(shape))
            self.assertEqual(self.rules(shape % words, words), ["quietly-resolved"], repr(shape))


class TheGuardsHoles(_Answer):
    """The guard's known holes on the id-less path (the design's C4): the seam 14 reader's CS14-1 and CS14-2, the
    reviewer's underscore emphasis and inline link (lane P's patch, inspect's F2), each line side and row side."""

    allowed = ("ledger", "repo_path", "question", "owner_words")
    W = "keep the tally in memory"

    def rules(self, line, row, trace=None, questions=()):
        self.ledger.append({"id": "prk-h", "tag": "parked", "section": "Decisions", "text": row})
        try:
            doc = self.clean()
            doc["questions"] += list(questions)
            doc["lines"].append({"text": line, "tag": "decided",
                                 "trace": trace or {"kind": "owner_words", "ref": "he said"}})
            return [r["rule"] for r in self.check(doc, allowed=self.allowed)["refusals"]]
        finally:
            self.ledger.pop()

    def refused(self, line, row, **kw):
        self.assertEqual(self.rules(line, row, **kw), ["quietly-resolved"], "line %r, row %r" % (line, row))

    def accepted(self, line, row, **kw):
        self.assertEqual(self.rules(line, row, **kw), [], "line %r, row %r" % (line, row))

    def test_cs14_2_template_labels_line_breaks_and_bracket_tails(self):
        W = self.W
        for text in ("When: %s" % W, "Step 3.1 (walkthrough target): %s" % W, "Step 3.2 (candidates): %s" % W,
                     "Step 3.3 (one-way doors): %s" % W, "Must be able to: %s" % W,
                     u"keep the tally\x0bin memory", u"keep the tally\x0cin memory",
                     u"%s \u2768parked: x\u2769" % W, u"%s \ufe59parked: x\ufe5a" % W, u"%s \u2045parked: x\u2046" % W,
                     u"%s \u2e28parked: x\u2e29" % W):
            self.refused(text, W)
        for row in ("When: %s" % W, u"keep the tally\x0bin memory", u"%s \u2768parked: x\u2769" % W):
            self.refused(W, row)

    def test_p2_f2_underscore_emphasis_and_inline_links(self):
        row = "budget ceiling"
        for line in ("budget _ceiling_", "_budget_ ceiling", "budget _ceiling_."):
            self.refused(line, row)
        self.refused(row, "budget _ceiling_")
        # under an unrelated ledger trace, and beside an answered question touching another row (F2's row-07, row-08)
        decided = self.ids["Python 3.9 standard library only"]
        self.refused("budget _ceiling_", row, trace={"kind": "ledger", "ref": decided})
        self.refused("budget _ceiling_", row, questions=[{"id": "Q8", "text": "Anything else?",
                                                          "touches": [self.ids["how often it resets"]],
                                                          "answer": "no"}])
        # identifiers keep their underscores (F2's three probes)
        self.assertEqual(answer.bare("_ceiling_"), "ceiling")
        self.assertEqual(answer.bare("use __init__ hooks"), "use __init__ hooks")
        self.assertEqual(answer.bare("rename snake_case fields"), "rename snake_case fields")
        self.accepted("use __init__ hooks", "use init hooks")
        self.accepted("rename snake_case fields", "rename snakecase fields")
        # an inline link is read by its visible text; an image is not a link
        self.refused("[keep the tally](https://example.com/a) in memory", self.W)
        self.refused(self.W, "keep the [tally](docs/tally.md) in memory")
        self.assertEqual(answer.bare("see ![chart](c.png) now"), "see ![chart](c.png) now")

    def test_cs14_1_status_marks_and_punctuation_are_decoration(self):
        W = self.W
        for row, line in ((u"%s \u2610" % W, u"%s \u2611" % W), (u"%s \u2610" % W, u"%s \u2705" % W),
                          (u"%s \u2610" % W, u"%s \u2713" % W), (u"%s \u23f3" % W, u"%s \u2705" % W),
                          (u"%s \U0001f44e" % W, u"%s \U0001f44d" % W), ("%s ?" % W, u"%s \u2713" % W),
                          ("%s ?" % W, "%s !" % W), (u"%s \u2026" % W, u"%s \u2713" % W),
                          (u"%s \u2014" % W, u"%s \u2713" % W), (u"%s \u2610 \u2014 parked: x" % W, u"%s \u2713" % W),
                          ("zoom +", u"zoom \uff0b"), (u"%s \u2610" % W, u"%s \u2610 \u2713" % W),
                          (u"%s \u2713" % W, u"%s \u2714" % W), (u"status \u2717", u"status \u2713"),
                          (u"status \u2713", u"status \u2717")):
            self.refused(line, row)
        # a sign that can be the meaning stays keyed
        for row, line in (("zoom -", "zoom +"), (u"sort \u2193", u"sort \u2191"), (u"rating \u2605", u"rating \u2605\u2605\u2605"),
                          ("volume --", "volume ++"), ("(US) data residency", "(EU) data residency"),
                          ("(12V) supply", "(5V) supply"), ("(v1) API", "(v2) API"), ("(CLI) rate limit", "(API) rate limit"),
                          (u"units \u2032", u"units \u00b0")):
            self.accepted(line, row)

class ShapeRefusals(_Answer):

    def test_a_malformed_answer_is_a_refusal_not_a_crash(self):
        for bad in ({}, {"questions": "x", "lines": []}, {"questions": [], "lines": [5]},
                    {"questions": [{"id": "Q1"}, {"id": "Q1"}], "lines": []}):
            result = self.check(bad)
            self.assertEqual(result["exit"], 5, bad)
            self.assertTrue(result["refusals"], bad)


class QuestionWithoutText(_Answer):
    """C3-1 (the round 3 checker): a question with no text, a text that is not a string, or a blank
    text would skip the decided-text match; it is a shape refusal, exit 5 and nothing written."""

    def test_a_question_without_usable_text_is_exit_5_and_nothing_written(self):
        for label, text in (("absent", None), ("an integer", 42), ("whitespace only", " \t\n ")):
            with self.subTest(text=label):
                q = {"id": "Q9", "touches": [], "answer": "yes"}
                if text is not None:
                    q["text"] = text
                doc = self.clean()
                doc["questions"].append(q)
                code, report = self.record(doc)
                self.assertEqual(code, 5, (label, report))
                self.assertEqual(os.listdir(self.run_dir), [], "nothing written: %s" % label)
                self.assertEqual([(r["rule"], r["message"]) for r in report["refusals"]],
                                 [("shape", "question Q9 carries no text")], label)

    def test_the_clean_question_is_still_accepted(self):
        code, report = self.record(self.clean())
        self.assertEqual(code, 0, report)
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "answer.json")))

    def test_every_seeded_recorded_answer_still_passes_the_shape_check(self):
        root = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
        seen = 0
        for family in sorted(os.listdir(root)):
            folder = os.path.join(root, family, "answers")
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                if not name.endswith(".json"):
                    continue
                doc = testlib.load_json(os.path.join(folder, name))
                seen += 1
                if "questions" not in doc:
                    continue
                view = {"questions": doc["questions"], "lines": doc.get("lines", [])}
                self.assertEqual(answer._shape(view), [], name)
        self.assertTrue(seen, "this core ships seeded recorded answers")


if __name__ == "__main__":
    unittest.main()
