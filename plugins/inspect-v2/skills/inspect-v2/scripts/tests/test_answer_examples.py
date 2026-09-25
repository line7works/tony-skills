"""The recorded answer's schema and its examples (lane contract section 5; brief CR-8).

`references/answer.schema.json` is the shape of inspect-v2's one recorded answer: the executor's
document and, inside it, the readers' results (`results`). Every file under
`references/examples/answer/valid/` validates; every file under `invalid/` is refused by the schema
(each is named for the one thing wrong with it); dropping any required field of a valid example,
at the top and inside a result and a finding, is refused. The shared `validate-examples.py` knows
only the input and the result, so this test holds the answer's examples.
"""
import copy
import glob
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import validate  # noqa: E402

SCHEMA = os.path.join(testlib.REF, "answer.schema.json")
FOLDER = os.path.join(testlib.EX, "answer")


def load_schema():
    with open(SCHEMA, encoding="utf-8") as fh:
        return json.load(fh)


def errors(doc):
    return validate.errors_for(doc, load_schema(), testlib.PREFIX)


class TheSchema(unittest.TestCase):

    def test_it_is_closed_at_every_level(self):
        def walk(node, where):
            if isinstance(node, dict):
                if node.get("type") == "object" or "properties" in node:
                    self.assertIs(node.get("additionalProperties"), False, where)
                for key, value in node.items():
                    walk(value, where + "/" + key)
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, "%s/%d" % (where, index))
        walk(load_schema(), "")

    def test_the_shared_fields_are_required(self):
        required = set(load_schema()["required"])
        for field in ("answer_version", "run_id", "session_id", "questions", "lines", "row",
                      "lanes", "results"):
            self.assertIn(field, required)

    def test_the_seeded_reader_names_are_kept(self):
        result = load_schema()["$defs"]["result"]["properties"]
        for field in ("call_id", "row", "effective_model", "findings"):
            self.assertIn(field, result)
        finding = load_schema()["$defs"]["finding"]["properties"]
        for field in ("severity", "location", "claim", "scenario", "confidence"):
            self.assertIn(field, finding)


class TheExamples(unittest.TestCase):

    def valid(self):
        return sorted(glob.glob(os.path.join(FOLDER, "valid", "*.json")))

    def invalid(self):
        return sorted(glob.glob(os.path.join(FOLDER, "invalid", "*.json")))

    def test_there_are_examples_both_ways(self):
        self.assertGreaterEqual(len(self.valid()), 3)
        self.assertGreaterEqual(len(self.invalid()), 8)

    def test_every_valid_example_validates(self):
        for path in self.valid():
            self.assertEqual(errors(testlib.load_json(path)), [], os.path.basename(path))

    def test_every_invalid_example_is_refused(self):
        for path in self.invalid():
            self.assertNotEqual(errors(testlib.load_json(path)), [], os.path.basename(path))

    def test_dropping_any_required_field_is_refused(self):
        schema = load_schema()
        result_required = schema["$defs"]["result"]["required"]
        finding_required = schema["$defs"]["finding"]["required"]
        for path in self.valid():
            doc = testlib.load_json(path)
            for field in schema["required"]:
                dropped = copy.deepcopy(doc)
                del dropped[field]
                self.assertNotEqual(errors(dropped), [], "%s without %s" % (path, field))
            for field in result_required:
                dropped = copy.deepcopy(doc)
                del dropped["results"][0][field]
                self.assertNotEqual(errors(dropped), [], "%s result without %s" % (path, field))
            if doc["results"][0]["findings"]:
                for field in finding_required:
                    dropped = copy.deepcopy(doc)
                    del dropped["results"][0]["findings"][0][field]
                    self.assertNotEqual(errors(dropped), [], "%s finding without %s" % (path, field))

    def test_no_clear_can_be_carried(self):
        """Inspect clears nothing: a disposition or a waiver in the answer is refused by the schema."""
        doc = testlib.load_json(self.valid()[0])
        for key, value in (("disposition", "fixed"), ("waived", True)):
            smuggled = copy.deepcopy(doc)
            smuggled[key] = value
            self.assertNotEqual(errors(smuggled), [], key)
            if smuggled["results"][0]["findings"]:
                inner = copy.deepcopy(doc)
                inner["results"][0]["findings"][0][key] = value
                self.assertNotEqual(errors(inner), [], key)


if __name__ == "__main__":
    unittest.main()
