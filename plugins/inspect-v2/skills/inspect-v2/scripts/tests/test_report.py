"""`report` (lane contract section 9, required test 8), through the real CLI.

The result validates against `references/result.schema.json` and the semantic checks
(`validate-result.py`); its counts equal the answer's survivors, questions and refutations as the
triage recorded them; the chat block is v1's read-back rendered from the result; a stopped run's
result is already written and `report` prints it again; a report before `write` is usage.
"""
import json
import os
import unittest

import ilib
import testlib

NEEDS = testlib.checkout_sibling("blueprint-v2") is None or testlib.records_root() is None or \
    testlib.checkout_sibling("readers") is None
R = "run-0001"
MODEL = "claude-test-model"


@unittest.skipIf(NEEDS, "the installed shape: no blueprint-v2, records or readers beside this core")
class Report(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("report-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def go(self, fleet, scope=ilib.SCOPE_DOC, last="report", **extra):
        self.ws = ilib.workspace(self.tmp, scope=scope)
        self.run = ilib.Runner(self.tmp, self.ws)
        return self.run.upto(last, answer=ilib.answer(R, fleet, **extra))

    def validate(self):
        path = os.path.join(self.run.run_dir, "result.json")
        code, out, err = testlib.run_script("validate-result.py", [path])
        self.assertEqual(code, 0, out + err)
        return testlib.load_json(path)

    def test_the_result_validates_and_its_counts_are_the_survivors(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[
            ilib.finding("build-doc.md:12", quote="AC1"),
            ilib.finding("build-doc.md:13", severity="BLOCKER", claim="the footprint misses the fixture"),
            ilib.finding("build-doc.md:99", claim="line 99 says the reset is required"),
            ilib.finding(None, claim="the plan reads long"),
            ilib.finding("build-doc.md:14", severity="QUESTION", claim="was the reset deferred on purpose")])
        code, doc, out, err = self.go(fleet, bottom_line="Fix the footprint first.", hunted_and_held="slice order held")
        self.assertEqual(code, 10, out + err)
        result = self.validate()
        self.assertEqual((result["status"], result["stop_tag"]), ("completed", None))
        sr = result["station_result"]
        tri = self.run.artifact("triage.json")
        self.assertEqual(sr["counts"], tri["counts"])
        self.assertEqual(sr["counts"]["blocker"], 1)
        self.assertEqual(sr["counts"]["major"], 1)
        self.assertEqual(sr["counts"]["refuted"], 1)
        self.assertEqual(sr["counts"]["questions"], 1)
        self.assertEqual(sr["counts"]["locationless"], 1)
        self.assertEqual(sr["verdict"], "REJECTED")
        self.assertEqual(len(sr["findings"]), 2)
        self.assertEqual(sr["stamp"], "Plan: inspected %s by %s · 1 BLOCKER · 1 MAJOR · 0 MINOR · 1 QUESTION"
                         % (ilib.TODAY, MODEL))
        self.assertTrue(sr["stamp_written"])
        self.assertEqual([c["call_id"] for c in sr["calls"]],
                         ["%s-traceability" % R, "%s-code-book" % R, "%s-repo-reality" % R])
        self.assertEqual(sr["packet"][0]["files"], ["build-doc.md", "code-book.md", "scope-doc.md"])
        self.assertEqual(sr["records"]["appended"], 2)
        self.assertEqual(len(sr["records"]["head_after"]), 64)
        kinds = set(w["kind"] for w in result["writes"])
        self.assertEqual(kinds, {"run_artifact", "document", "records_log"})
        self.assertFalse(result["wrote_nothing"])
        chat = doc["chat"]
        self.assertTrue(chat.startswith("INSPECT: %s\nVerdict: REJECTED\n" % os.path.join(self.ws, ilib.BUILD_REL)))
        self.assertIn("Refuted: 1", chat)
        self.assertIn("Findings: 1 BLOCKER · 1 MAJOR · 0 MINOR", chat)
        self.assertIn("Hunted and held: slice order held", chat)
        self.assertIn("Bottom line: Fix the footprint first.", chat)
        self.assertEqual(sr["chat"], chat)

    def test_the_no_record_run_says_it_is_weaker(self):
        fleet = ilib.claude_fleet(R, model=MODEL, traceability=[ilib.finding(
            "build-doc.md:10", severity="BLOCKER", claim="R1 traces to nothing in the record")])
        code, doc, out, err = self.go(fleet, scope=None)
        self.assertEqual(code, 10, out + err)
        sr = self.validate()["station_result"]
        self.assertTrue(sr["weaker"])
        self.assertEqual(sr["verdict"], "APPROVED")
        self.assertIn("Scope doc: none \u2014 no-record rule applied", doc["chat"])
        self.assertIn("weaker", doc["chat"])

    def test_report_prints_a_stopped_run_again(self):
        fleet = ilib.claude_fleet(R, model=None)
        code, doc, out, err = self.go(fleet, last="record-answer")
        self.assertEqual(code, 10, out + err)
        first = self.validate()
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["status"], "stopped")
        self.assertEqual(testlib.load_json(os.path.join(self.run.run_dir, "result.json")), first)

    def test_report_before_write_is_usage(self):
        self.go(ilib.claude_fleet(R, model=MODEL), last="record-answer")
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 2, out + err)
        self.assertIn("write", err)

    def test_a_clean_run_without_a_hunt_line_says_so(self):
        code, doc, out, err = self.go(ilib.claude_fleet(R, model=MODEL))
        self.assertEqual(code, 10, out + err)
        sr = self.validate()["station_result"]
        self.assertIsNone(sr["hunted_and_held"])
        self.assertIn("Hunted and held: not recorded", doc["chat"])
        self.assertEqual(json.loads(json.dumps(sr["verdict"])), "APPROVED")


if __name__ == "__main__":
    unittest.main()
