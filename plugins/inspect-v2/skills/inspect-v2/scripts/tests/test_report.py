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
        self.assertTrue(chat.startswith("INSPECT: %s\nSelected: " % os.path.join(self.ws, ilib.BUILD_REL)), chat)
        self.assertIn("\nVerdict: REJECTED\n", chat)
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

    def test_the_chat_names_the_doc_taken_and_how(self):
        # CI1-11: v1 "the verdict says which doc it took" when both tiers match by filename
        self.ws = ilib.workspace(self.tmp, extra={"docs/turnstile-build-plan.md": ilib.BUILD_DOC})
        self.run = ilib.Runner(self.tmp, self.ws)
        code, doc, out, err = self.run.upto("report", answer=ilib.answer(R, ilib.claude_fleet(R, model=MODEL)))
        self.assertEqual(code, 10, out + err)
        line = [l for l in doc["chat"].splitlines() if l.startswith("Selected: ")]
        self.assertEqual(len(line), 1, doc["chat"])
        self.assertIn("docs/plans/ (tier 1, repo-plans)", line[0])
        self.assertIn("docs/turnstile-build-plan.md", line[0])
        self.assertIn("also matched by filename", line[0])

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

    def test_an_answer_without_the_hunt_line_is_refused_by_its_schema(self):
        # R3 (CI1-3): v1 rule 10 is mandatory, every run; no "not recorded" fallback is printed
        base = self.tmp
        for key in ("hunted_and_held", "bottom_line"):
            with self.subTest(key=key):
                self.tmp = os.path.join(base, key)
                os.makedirs(self.tmp)
                code, doc, out, err = self.go(ilib.claude_fleet(R, model=MODEL), last="record-answer",
                                              **{key: ilib.DROP})
                self.assertEqual(code, 4, out + err)
                self.assertIn(key, json.dumps(doc["errors"]))
                self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")))

    def test_a_clean_run_prints_the_hunt_line_it_was_given(self):
        code, doc, out, err = self.go(ilib.claude_fleet(R, model=MODEL))
        self.assertEqual(code, 10, out + err)
        sr = self.validate()["station_result"]
        self.assertEqual(sr["hunted_and_held"], ilib.HUNTED)
        self.assertIn("Hunted and held: %s\n" % ilib.HUNTED, doc["chat"])
        self.assertNotIn("Hunted and held: not recorded", doc["chat"])
        self.assertNotIn("Bottom line: not recorded", doc["chat"])
        mirror = testlib.read_text(os.path.join(self.ws, "docs", "reviews", "%s-inspect-turnstile.md" % ilib.TODAY))
        self.assertIn("Hunted and held: %s\n" % ilib.HUNTED, mirror)
        self.assertIn("Bottom line: %s\n" % ilib.BOTTOM, mirror)
        self.assertNotIn("Hunted and held: not recorded", mirror)

if __name__ == "__main__":
    unittest.main()
