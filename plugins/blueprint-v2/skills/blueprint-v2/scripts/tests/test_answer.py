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
