"""E18 fix round 2, Slice B: every saved field is tidied before it is saved.

signoff-v2 tidies a finding's claim, scenario and location with the one rule the record grammar
already has (`_single_line`: a line break becomes a space, the separator and any bare middle dot
become hyphens) before it writes them, so the records log never refuses them. These tests drive
the real CLI through the seeded case the earlier fix rounds use. They were written red first: the
line-break case fails on the code before this slice.
"""
import json
import os
import unittest

import testlib
from test_fix2_astra import _Case, kinds

testlib.add_scripts_to_path()

NOTE_WORD = "was tidied"

LINE_BREAK_CLAIM = "pad() returns width - 1 characters;\nthe name field is one short"
LINE_BREAK_TIDIED = "pad() returns width - 1 characters; the name field is one short"

BARE_DOT_CLAIM = "pad() returns width·1 characters, so the name field is one short"
BARE_DOT_TIDIED = "pad() returns width-1 characters, so the name field is one short"

EDGE_DOT_CLAIM = "· pad() returns width - 1 characters, so the name field is one short ·"
EDGE_DOT_TIDIED = "- pad() returns width - 1 characters, so the name field is one short -"


class _Tidy(_Case):

    def assert_tidied(self, written, tidied):
        answer = self.answer()
        answer["findings"][0]["claim"] = written
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["verdict_recorded"])

        raised = kinds(self.workspace, "finding_raised")
        self.assertEqual(len(raised), 1)
        self.assertEqual(raised[0]["claim"], tidied)

        verdict = testlib.read_text(os.path.join(self.workspace, result["verdict_doc"]))
        self.assertEqual(verdict.count(NOTE_WORD), 1, verdict)
        self.assertIn(tidied, verdict)

        kept = testlib.load_json(os.path.join(self.run_dir, "answer.json"))
        self.assertEqual(kept["findings"][0]["claim"], written)


class ALineBreakIsTidied(_Tidy):

    def test_a_claim_holding_a_line_break_records_as_one_line(self):
        self.assert_tidied(LINE_BREAK_CLAIM, LINE_BREAK_TIDIED)


class ABareMiddleDotIsTidied(_Tidy):

    def test_a_claim_holding_a_bare_middle_dot_records_with_a_hyphen(self):
        self.assert_tidied(BARE_DOT_CLAIM, BARE_DOT_TIDIED)


class AMiddleDotAtAFieldsEdgeIsTidied(_Tidy):

    def test_a_claim_with_a_middle_dot_at_each_edge_records_with_hyphens(self):
        self.assert_tidied(EDGE_DOT_CLAIM, EDGE_DOT_TIDIED)


class AnUntidiedReviewCarriesNoNote(_Case):

    def test_a_review_with_nothing_to_tidy_says_nothing_about_it(self):
        code, doc, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        verdict = testlib.read_text(os.path.join(self.workspace, result["verdict_doc"]))
        self.assertNotIn(NOTE_WORD, verdict)


if __name__ == "__main__":
    unittest.main()
