"""The answer schema and its examples (reading CR-8, required test 2).

`references/answer.schema.json` against `references/examples/answer/`: every valid example is
accepted; every invalid example is refused by the schema, at the path its file name names; every
required field of every valid example, dropped in turn, is refused; the schema is closed at every
level (an object without `additionalProperties: false` is a failure).
"""
import copy
import glob
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from station_core import validate  # noqa: E402

SCHEMA = os.path.join(testlib.REF, "answer.schema.json")
EXAMPLES = os.path.join(testlib.EX, "answer")

# each invalid example's one wrong thing: the JSON pointer its schema finding must name
WHERE = {
    "unknown-key.json": "/extra",
    "unknown-answer-version.json": "/answer_version",
    "no-questions.json": "/questions",
    "no-triage.json": "/triage",
    "tier-outside-the-three.json": "/triage/tier",
    "line-tag-outside-the-four.json": "/lines/0/tag",
    "line-with-an-unknown-key.json": "/lines/0/because",
    "question-touches-not-a-list.json": "/questions/0/touches",
    "trace-with-an-unknown-key.json": "/lines/0/trace/why",
    "sitting-outside-the-two.json": "/sitting",
    "disposition-with-an-unknown-key.json": "/exit_test/dispositions/0/note",
    "research-not-strings.json": "/research/0",
}


def schema():
    return testlib.load_json(SCHEMA)


def objects(node, path="#"):
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            yield path, node
        for key, value in node.items():
            for found in objects(value, "%s/%s" % (path, key)):
                yield found
    elif isinstance(node, list):
        for index, value in enumerate(node):
            for found in objects(value, "%s/%d" % (path, index)):
                yield found


class TheExamples(unittest.TestCase):

    def test_every_valid_example_is_accepted(self):
        paths = sorted(glob.glob(os.path.join(EXAMPLES, "valid", "*.json")))
        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            self.assertEqual(validate.errors_for(testlib.load_json(path), schema(), testlib.PREFIX), [], path)

    def test_every_invalid_example_is_refused_where_its_name_says(self):
        paths = sorted(glob.glob(os.path.join(EXAMPLES, "invalid", "*.json")))
        self.assertEqual(sorted(os.path.basename(p) for p in paths), sorted(WHERE))
        for path in paths:
            errors = validate.errors_for(testlib.load_json(path), schema(), testlib.PREFIX)
            self.assertTrue(errors, path)
            where = WHERE[os.path.basename(path)]
            parent, key = where.rsplit("/", 1)
            self.assertTrue(any(e["path"] == where or e["path"].startswith(where + "/") or
                                (e["path"] == (parent or "/") and "'%s'" % key in e["message"]) for e in errors),
                            "%s: %s" % (path, errors))

    def test_dropping_a_required_field_is_refused(self):
        body = schema()
        for path in sorted(glob.glob(os.path.join(EXAMPLES, "valid", "*.json"))):
            doc = testlib.load_json(path)
            for field in body["required"]:
                dropped = copy.deepcopy(doc)
                dropped.pop(field, None)
                self.assertTrue(validate.errors_for(dropped, body, testlib.PREFIX), (path, field))

    def test_closed_at_every_level(self):
        for path, node in objects(schema()):
            if path == "#":
                self.assertIs(node.get("additionalProperties"), False, path)
                continue
            if node.get("type") == "object":
                self.assertIs(node.get("additionalProperties"), False, path)

    def test_the_gate_and_the_sources_are_content_rules_not_schema_rules(self):
        # absent gate, absent trace, blank why: the schema lets them through so record-answer can
        # refuse them by rule (exit 5, named), never as a bare schema finding
        doc = testlib.load_json(sorted(glob.glob(os.path.join(EXAMPLES, "valid", "*.json")))[0])
        doc = copy.deepcopy(doc)
        doc.pop("gate", None)
        doc["lines"] = [{"text": "x", "tag": "decided"}, {"text": "y", "tag": "assumed",
                                                          "trace": {"kind": "assumed", "ref": ""}}]
        self.assertEqual(validate.errors_for(doc, schema(), testlib.PREFIX), [])


if __name__ == "__main__":
    unittest.main()
