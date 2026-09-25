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


if __name__ == "__main__":
    unittest.main()
