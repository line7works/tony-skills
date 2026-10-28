"""E18 fix round 2, Slice A: a quoted separator never breaks recording.

The second live run's reviewer quoted a `/fb` line, which always carries the records separator
` · `, in a finding's claim and scenario. `record-answer` accepted the answer, and only the records
component refused the events at `record` (exit 4, nothing appended), so the run stopped
`recording_failed` after the review had finished. These tests drive the real CLI through the
seeded case the earlier fix rounds use. They were written red first.
"""
import json
import os
import unittest

import testlib
from test_fix2_astra import _Case, kinds

testlib.add_scripts_to_path()

FB_LINE = "- 2026-10-28 · GUIDE · pad() leaves the name field one short"
CLAIM = "pad() returns width - 1 characters; the feedback log says `%s`" % FB_LINE
SCENARIO = ("run sh checks/field-widths.sh from the workspace root; it prints the short field, "
            "as the line `%s` reports" % FB_LINE)
HYPHEN_FB = "- 2026-10-28 - GUIDE - pad() leaves the name field one short"


def quoting_answer(answer):
    answer = json.loads(json.dumps(answer))
    answer["findings"][0]["claim"] = CLAIM
    answer["findings"][0]["scenario"] = SCENARIO
    return answer


class AQuotedSeparatorRecords(_Case):
    """Requirements 1 and 3: the run records, the log and the verdict doc hold the hyphen form, the
    verdict doc says so once, and the run's answer.json keeps the reviewer's words."""

    def test_the_run_records_with_the_separator_written_as_a_hyphen(self):
        code, doc, err = self.through_answer(quoting_answer(self.answer()))
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["verdict_recorded"])

        raised = kinds(self.workspace, "finding_raised")
        self.assertEqual(len(raised), 1)
        self.assertNotIn(" · ", raised[0]["claim"])
        self.assertNotIn(" · ", raised[0]["scenario"])
        self.assertIn(HYPHEN_FB, raised[0]["claim"])
        self.assertIn(HYPHEN_FB, raised[0]["scenario"])

        verdict = testlib.read_text(os.path.join(self.workspace, result["verdict_doc"]))
        self.assertIn(HYPHEN_FB, verdict)
        self.assertNotIn(FB_LINE, verdict)
        self.assertEqual(verdict.count("written as a hyphen"), 1, verdict)

        build_doc = self.doc_text()
        self.assertIn(HYPHEN_FB, build_doc)
        self.assertNotIn(FB_LINE, build_doc)

        kept = testlib.load_json(os.path.join(self.run_dir, "answer.json"))
        self.assertEqual(kept["findings"][0]["claim"], CLAIM)
        self.assertEqual(kept["findings"][0]["scenario"], SCENARIO)

    def test_a_review_without_the_separator_says_nothing_about_it(self):
        code, doc, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        verdict = testlib.read_text(os.path.join(self.workspace, result["verdict_doc"]))
        self.assertNotIn("written as a hyphen", verdict)


class AnAnswerTheRecordsWouldRefuseIsRefusedAtRecordAnswer(_Case):
    """Requirement 2: an answer that breaks another records rule (a claim over two lines) is
    refused at `record-answer`, naming the field and the rule, with nothing receipted."""

    def test_a_two_line_claim_is_refused_before_anything_is_receipted(self):
        answer = self.answer()
        answer["findings"][0]["claim"] = "pad() returns width - 1 characters\nso the field is short"
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1500])
        self.assertEqual(result["refusal_reason"], "answer_invalid")
        self.assertTrue(result["answer_refused"])
        whys = " ".join(row.get("why", "") for row in result["problems"])
        self.assertIn("/claim", whys)
        self.assertIn("records event schema", whys)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "receipt.json")))
        self.assertEqual(kinds(self.workspace, "finding_raised"), [])
        self.assertEqual(kinds(self.workspace, "card_set"), [])

        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(self.result()["status"], "stopped")
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "receipt.json")))
        self.assertEqual(kinds(self.workspace, "finding_raised"), [])


if __name__ == "__main__":
    unittest.main()
