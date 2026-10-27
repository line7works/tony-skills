"""E18 fix round 1, Slice A, requirements 4 and 5: every value the answer schema allows records.

The first signoff run of Slice A (signoff-a-20261027-a796) found three more ways a result could
break on what the answer carried. `answer.schema.json` lets a reviewer's check carry a null or
missing `output`, and lets every field of a kept note (`$defs/reported`) be null or any string, a
severity such as `minor`, `NOTE` or `info` and an evidence kind such as `inferred` included. The
result schema refused each of them, so `record` stopped or exited 4. And the stop the check before
any project-record write makes dropped the raised findings and the notes, so a raised MAJOR
vanished from result.json and chat.md. These tests drive the real CLI through the seeded case the
F16 tests use. They were written red first.
"""
import json
import os
import shutil
import unittest

import testlib
from test_fix2_astra import _Case, read_log

testlib.add_scripts_to_path()

from signoff_core import inputs, result as resultmod, validate  # noqa: E402

NO_OUTPUT = [{"name": "probe with a null output", "command": None, "exit_code": None,
              "output": None},
             {"name": "probe with no output field"}]

BASE = {"location": "src/signpost/pad.py:1", "severity": "MINOR",
        "claim": "pad() could read the width as a byte count",
        "scenario": "pad a multibyte string; the reviewer's own run showed the width holds",
        "evidence_kind": "executed"}

ODD_NOTES = [
    dict(BASE, severity="minor", claim="a lower-case severity"),
    dict(BASE, severity="NOTE", claim="a NOTE severity"),
    dict(BASE, severity="info", claim="an info severity"),
    dict(BASE, location=None, claim="a null location"),
    dict(BASE, location="", claim="an empty location"),
    dict(BASE, scenario=None, claim="a null scenario"),
    dict(BASE, scenario="", claim="an empty scenario"),
    dict(BASE, evidence_kind=None, claim="a null evidence kind"),
    dict(((k, v) for k, v in BASE.items() if k != "evidence_kind"), claim="no evidence kind"),
    dict(BASE, evidence_kind="inferred", claim="an inferred evidence kind"),
    dict(BASE, claim=None, severity=None),
    {},
]

FIELDS = ("location", "severity", "claim", "scenario", "evidence_kind")


def result_schema():
    return inputs.load_schema(testlib.REF, "result.schema.json")


def kept_of(result):
    return [row for row in result["notes"] if row.get("why") == "the reviewer kept it as a note"]


def strict_skill_root(parent):
    """A copy of the references whose result schema refuses any result that records a verdict, so
    the proposed completion fails the schema the check before any project-record write runs, while
    the stop it makes (no verdict recorded) still passes."""
    root = os.path.join(parent, "strict-skill")
    shutil.copytree(testlib.REF, os.path.join(root, "references"))
    path = os.path.join(root, "references", "result.schema.json")
    schema = testlib.load_json(path)
    schema["allOf"].append({"if": {"required": ["verdict_recorded"],
                                   "properties": {"verdict_recorded": {"const": True}}},
                            "then": {"required": ["fr1_test_refusal"]}})
    testlib.write_json(path, schema)
    return root


class AResultValidates(_Case):

    def assert_valid(self, result):
        self.assertEqual(validate.schema_errors(result, result_schema()), [],
                         json.dumps(result)[:1500])
        self.assertEqual(validate.semantic(result), [])

    def assert_no_none(self, text, label):
        for line in text.splitlines():
            self.assertNotIn("None", line, "%s prints None: %r" % (label, line))


class ACheckWithNoOutputRecords(AResultValidates):
    """Requirement 4: a reviewer's check whose `output` is null or missing is recorded as written,
    the run completes, and the chat block and the verdict doc's method lines print it without
    "None"."""

    def test_null_and_missing_output(self):
        answer = self.answer()
        answer["checks_executed"] = list(answer["checks_executed"]) + [dict(r) for r in NO_OUTPUT]
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["verdict_recorded"])
        self.assert_valid(result)
        self.assertEqual(result["checks_executed"], answer["checks_executed"],
                         "the checks are recorded as the answer wrote them")
        self.assertNotIn("output", result["checks_executed"][-1])
        chat = testlib.read_text(os.path.join(self.run_dir, "chat.md"))
        for row in NO_OUTPUT:
            self.assertIn(row["name"], chat)
        self.assert_no_none(chat, "chat.md")
        verdict_doc = testlib.read_text(os.path.join(self.workspace, result["verdict_doc"]))
        lines = [line for line in verdict_doc.splitlines()
                 if any(row["name"] in line for row in NO_OUTPUT)]
        self.assertEqual(len(lines), 2, verdict_doc)
        self.assert_no_none("\n".join(lines), "the verdict doc's method lines")


class AKeptNoteWithAnyAllowedValueRecords(AResultValidates):
    """Requirement 4: every value `$defs/reported` allows on a kept note is recorded as written."""

    def test_each_odd_value(self):
        answer = self.answer()
        answer["notes_kept"] = [dict(row) for row in ODD_NOTES]
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["verdict_recorded"])
        self.assert_valid(result)
        kept = kept_of(result)
        self.assertEqual(len(kept), len(ODD_NOTES))
        for got, want in zip(kept, ODD_NOTES):
            for key in FIELDS:
                self.assertEqual(got[key], want.get(key), "%s of %r" % (key, want))
        self.assertTrue(read_log(self.workspace), "the verdict is recorded in the log")
        chat = testlib.read_text(os.path.join(self.run_dir, "chat.md"))
        for row in ODD_NOTES:
            if row.get("claim"):
                self.assertIn(row["claim"], chat)
        self.assert_no_none(chat, "chat.md")


class APreWriteStopKeepsWhatWasRaised(AResultValidates):
    """Requirement 5: a stop from the check before any project-record write writes a result that
    passes the result schema whatever the answer carried, and keeps the raised findings and the
    notes in that result and its chat block. Requirement 2 still holds: nothing is recorded."""

    def test_the_stop_validates_and_keeps_findings_and_notes(self):
        answer = self.answer()
        answer["checks_executed"] = list(answer["checks_executed"]) + [dict(r) for r in NO_OUTPUT]
        answer["notes_kept"] = [dict(row) for row in ODD_NOTES]
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        self.assertGreater(doc["raised"], 0, "the seeded answer raises a finding")
        state = testlib.load_json(os.path.join(self.run_dir, "state.json"))
        raised = state["adjudication"]["raised"]
        notes = state["adjudication"]["notes"]
        before_doc = self.doc_text()
        root = strict_skill_root(self.dir)
        code, doc, err = self.phase(["record", "--run-dir", self.run_dir, "--skill-root", root])
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1500])
        self.assertEqual(result["refusal_reason"], "answer_invalid")
        self.assertIn("result.schema.json", result["stop_reason"])
        self.assertFalse(result["verdict_recorded"])
        self.assertTrue(result["writes_none"])
        self.assert_valid(result)
        self.assertEqual(result["findings"], raised)
        self.assertEqual(result["notes"], notes)
        self.assertEqual(len(kept_of(result)), len(ODD_NOTES))
        self.assertEqual(result["checks_executed"], answer["checks_executed"])
        chat = testlib.read_text(os.path.join(self.run_dir, "chat.md"))
        for row in raised:
            self.assertIn(row["claim"], chat)
            self.assertIn(row["severity"], chat)
        self.assertIn("Kept as notes, not raised", chat)
        self.assert_no_none(chat, "chat.md")
        self.assertEqual(read_log(self.workspace), [], "no records event")
        self.assertEqual(self.doc_text(), before_doc, "no card move, no block placed")
        reviews = os.path.join(self.workspace, "docs", "reviews")
        self.assertFalse(os.path.isdir(reviews) and os.listdir(reviews), "no verdict doc")


class TheRenderersHandleEveryAllowedValue(unittest.TestCase):
    """Requirement 4, at the chat block itself."""

    def test_chat_block(self):
        notes = []
        for row in ODD_NOTES:
            notes.append({"location": row.get("location"), "file": None, "line": None,
                          "severity": row.get("severity"), "claim": row.get("claim"),
                          "scenario": row.get("scenario"),
                          "evidence_kind": row.get("evidence_kind"),
                          "why": "the reviewer kept it as a note"})
        doc = {"run": {"slice": "A", "build_doc": "docs/plans/x.md", "depth": "LEAN", "lenses": []},
               "status": "completed", "verdict": "signed off", "findings": [], "notes": notes,
               "checks_executed": [dict(r) for r in NO_OUTPUT],
               "session_checks": [{"name": "suite", "command": None, "exit_code": None,
                                   "output": None}]}
        text = resultmod.chat_block(doc)
        for line in text.splitlines():
            self.assertNotIn("None", line)
        self.assertEqual(validate.schema_errors(
            {"notes": notes, "checks_executed": doc["checks_executed"]},
            {"type": "object", "$defs": result_schema()["$defs"],
             "properties": {"notes": result_schema()["properties"]["notes"],
                            "checks_executed": result_schema()["properties"]["checks_executed"]}}),
            [])


if __name__ == "__main__":
    unittest.main()
