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
from test_fix2_astra import DOC, _Case, kinds

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



# Requirements 4 to 7, added on the owner's ruling after the first signoff run ("yes, fold and
# fix", 2026-10-28). They were written red first.

TAGGED_LOCATION = "src/signpost/pad.py:6 (see 2026-10-28 · GUIDE)"
HYPHEN_LOCATION = "src/signpost/pad.py:6 (see 2026-10-28 - GUIDE)"
ODD_STATUS = "built (awaiting review)"


class ALocationsSeparatorIsWrittenAsAHyphen(_Case):
    """Requirement 4: a finding's location is a single-line text field. A separator inside it, a
    trailing tag included, is written as a hyphen in the records log, the verdict doc and the
    punch list, and counts toward the verdict doc's note. answer.json keeps the original."""

    def test_a_tagged_location_records_in_the_hyphen_form_with_the_note(self):
        answer = self.answer()
        answer["findings"][0]["location"] = TAGGED_LOCATION
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])

        raised = kinds(self.workspace, "finding_raised")
        self.assertEqual(len(raised), 1)
        self.assertEqual(raised[0]["location"]["raw"], HYPHEN_LOCATION)
        self.assertEqual(raised[0]["location"]["file"], "src/signpost/pad.py")
        self.assertEqual(raised[0]["location"]["line"], 6)

        verdict = testlib.read_text(os.path.join(self.workspace, result["verdict_doc"]))
        self.assertIn("(see 2026-10-28 - GUIDE)", verdict)
        self.assertNotIn("(see 2026-10-28 · GUIDE)", verdict)
        self.assertEqual(verdict.count("written as a hyphen"), 1, verdict)

        build_doc = self.doc_text()
        self.assertIn("(see 2026-10-28 - GUIDE)", build_doc)
        self.assertNotIn("(see 2026-10-28 · GUIDE)", build_doc)

        kept = testlib.load_json(os.path.join(self.run_dir, "answer.json"))
        self.assertEqual(kept["findings"][0]["location"], TAGGED_LOCATION)


class AStatusLineOutsideTheCardValuesNeverRefusesTheAnswer(_Case):
    """Requirement 5: a ledger doc whose `Status:` line holds a value outside the six card values
    never refuses the reviewer's answer. The raised findings are accepted and recorded as before
    this slice; only the card move is refused, naming the doc's Status line."""

    def test_the_findings_land_and_only_the_card_move_is_refused(self):
        from signoff_core import ledger
        text = self.doc_text()
        self.write(DOC, ledger.set_card(text, self.seeded["slice"], ODD_STATUS))

        code, doc, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(doc))
        self.assertEqual(doc["next"], "record", json.dumps(doc))
        self.assertEqual(doc["raised"], 1)

        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertNotEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertIsNone(result.get("refusal_reason"), json.dumps(result)[:1500])
        self.assertFalse(result.get("answer_refused"), json.dumps(result)[:1500])
        reason = result["stop_reason"]
        self.assertIn("Status:", reason)
        self.assertIn(ODD_STATUS, reason)
        self.assertNotIn("the answer is refused", reason)

        self.assertEqual(len(kinds(self.workspace, "finding_raised")), 1)
        self.assertEqual(kinds(self.workspace, "card_set"), [])


class AMissingEventSchemaStopsWithTheUsualResult(_Case):
    """Requirement 6: when the records event schema cannot be read, `record-answer` stops with its
    usual JSON on stdout, a result.json and a chat block naming the missing schema."""

    def test_record_answer_stops_with_json_a_result_and_a_chat_block(self):
        # The shim root carries only scripts/records.py, and an empty plugin root leaves no
        # component installed beside the station, so no event schema can be read.
        empty = os.path.join(self.dir, "empty-plugin")
        os.makedirs(empty)
        code, doc, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["request", "--run-dir", self.run_dir])
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["record-answer", "--run-dir", self.run_dir, "--answer",
                                     os.path.join(self.case, "answer.json"),
                                     "--plugin-root", empty])
        self.assertEqual(code, 10, err)
        self.assertIsNotNone(doc, "no JSON on stdout; stderr: %s" % err)
        self.assertEqual(doc["status"], "stopped", json.dumps(doc))
        self.assertEqual(doc["stop_reason_code"], "reference_unavailable", json.dumps(doc))
        self.assertIn("event.schema.json", doc["stop_reason"])

        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertIn("event.schema.json", result["stop_reason"])
        self.assertFalse(result.get("answer_refused"), json.dumps(result)[:1500])
        chat = testlib.read_text(os.path.join(self.run_dir, "chat.md"))
        self.assertIn("event.schema.json", chat)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "receipt.json")))
        self.assertEqual(kinds(self.workspace, "finding_raised"), [])


class ExitsZeroMeansRecordAnswer(_Case):
    """Requirement 7: "exits 0" in requirement 3 means `record-answer` exits 0 and `record` ends
    `completed`; `record` keeps the station's exit convention (10 for every finished run)."""

    def test_record_answer_exits_0_and_record_ends_completed_with_exit_10(self):
        code, doc, err = self.through_answer(quoting_answer(self.answer()))
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed", json.dumps(doc)[:1500])
        self.assertEqual(self.result()["status"], "completed")


if __name__ == "__main__":
    unittest.main()
