"""E18 fix round 1, Slice A: a kept note never breaks the result.

The first live one-command run kept a note whose `severity` was null. `answer.schema.json` allows
that; the result schema gave `notes` the `finding` shape, whose severity must be BLOCKER, MAJOR or
MINOR, so `record` wrote a result its own schema refused, and the check before the first
project-record write ran only the semantic validator, so the verdict doc, the records events and
the card had already landed. These tests drive the real CLI through the seeded case the F16 tests
use. They were written red first.
"""
import json
import os
import unittest

import testlib
from test_fix2_astra import _Case, read_log

testlib.add_scripts_to_path()

from signoff_core import inputs, result as resultmod, validate  # noqa: E402

KEPT = {"location": "src/signpost/pad.py:1", "severity": None,
        "claim": "pad() could read the width as a byte count",
        "scenario": "pad a multibyte string; the reviewer's own run showed the width holds",
        "evidence_kind": "executed"}


def result_schema():
    return inputs.load_schema(testlib.REF, "result.schema.json")


class AKeptNoteWithoutASeverityRecords(_Case):
    """Requirement 1 and 3: a null severity on a kept note is recorded as the reviewer wrote it, the
    result validates, and the chat block prints the note without a severity."""

    def test_the_run_completes_and_the_result_validates(self):
        answer = self.answer()
        answer["notes_kept"] = [dict(KEPT)]
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1200])
        self.assertTrue(result["verdict_recorded"])
        self.assertEqual(validate.schema_errors(result, result_schema()), [])
        self.assertEqual(validate.semantic(result), [])
        kept = [row for row in result["notes"] if row.get("why") == "the reviewer kept it as a note"]
        self.assertEqual(len(kept), 1)
        self.assertIsNone(kept[0]["severity"])
        for key in ("location", "claim", "scenario", "evidence_kind"):
            self.assertEqual(kept[0][key], KEPT[key])
        self.assertTrue(read_log(self.workspace), "the verdict is recorded in the log")
        chat = testlib.read_text(os.path.join(self.run_dir, "chat.md"))
        self.assertIn(KEPT["claim"], chat)
        self.assertNotIn("None", chat)

    def test_the_raised_findings_keep_a_required_severity(self):
        schema = result_schema()
        row = {"location": "src/signpost/pad.py:1", "file": "src/signpost/pad.py", "line": 1,
               "severity": None, "claim": "c", "scenario": "s", "evidence_kind": "read"}
        doc = {"findings": [row]}
        sub = {"type": "object", "properties": {"findings": schema["properties"]["findings"]},
               "$defs": schema["$defs"]}
        self.assertTrue(validate.schema_errors(doc, sub), "a raised finding needs a severity")
        note = dict(row, why="the reviewer kept it as a note")
        sub = {"type": "object", "properties": {"notes": schema["properties"]["notes"]},
               "$defs": schema["$defs"]}
        self.assertEqual(validate.schema_errors({"notes": [note]}, sub), [])
        # Requirement 4 (the owner's "fold and fix"): a note records any severity the answer
        # allows, while a raised finding still refuses one outside BLOCKER, MAJOR and MINOR.
        self.assertEqual(validate.schema_errors({"notes": [dict(note, severity="NOTE")]}, sub), [])
        sub = {"type": "object", "properties": {"findings": schema["properties"]["findings"]},
               "$defs": schema["$defs"]}
        self.assertTrue(validate.schema_errors({"findings": [dict(row, severity="NOTE")]}, sub))


class TheChatBlockPrintsANullSeverityNoteWithoutOne(unittest.TestCase):
    """Requirement 3, at the renderer itself."""

    def test_no_none_and_no_failure(self):
        doc = {"run": {"slice": "A", "build_doc": "docs/plans/x.md", "depth": "LEAN", "lenses": []},
               "status": "completed", "verdict": "signed off", "findings": [],
               "notes": [{"location": "src/a.py:1", "file": "src/a.py", "line": 1,
                          "severity": None, "claim": "a kept note", "scenario": "s",
                          "evidence_kind": "read", "why": "the reviewer kept it as a note"}],
               "checks_executed": [{"name": "unit", "command": "x", "exit_code": 0,
                                    "output": "OK"}]}
        text = resultmod.chat_block(doc)
        self.assertIn("a kept note", text)
        self.assertNotIn("None", text)


class AProposalTheSchemaRefusesWritesNothing(_Case):
    """Requirement 2: the check before any project-record write runs the result schema as well as
    the semantic validator. Since requirement 4 no answer the answer schema accepts fails the
    result schema, so the test points `record` at a copy of the references whose result schema
    refuses a result that records a verdict: the proposal passes the semantic checks and fails the
    schema, and the run stops with no verdict doc, no records event and no card move, naming the
    schema error."""

    def test_nothing_is_recorded_and_the_error_is_named(self):
        from test_fr1_answer_values import strict_skill_root
        answer = self.answer()
        answer["notes_kept"] = [dict(KEPT)]
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        before_doc = self.doc_text()
        root = strict_skill_root(self.dir)
        code, doc, err = self.phase(["record", "--run-dir", self.run_dir, "--skill-root", root])
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1200])
        self.assertEqual(result["refusal_reason"], "answer_invalid")
        self.assertFalse(result["verdict_recorded"])
        self.assertTrue(result["writes_none"])
        self.assertIn("fr1_test_refusal", result["stop_reason"])
        self.assertIn("result.schema.json", result["stop_reason"])
        self.assertEqual(validate.schema_errors(result, result_schema()), [])
        self.assertEqual(read_log(self.workspace), [], "no records event, not even a levelling")
        self.assertEqual(self.doc_text(), before_doc, "no card move, no block placed")
        reviews = os.path.join(self.workspace, "docs", "reviews")
        self.assertFalse(os.path.isdir(reviews) and os.listdir(reviews), "no verdict doc")
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "receipt.json")))


if __name__ == "__main__":
    unittest.main()
