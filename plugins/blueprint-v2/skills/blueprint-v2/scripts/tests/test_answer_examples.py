"""The recorded answer's schema and its examples (lane L, reading CR-8, required test 2).

Every file under `references/examples/answer/valid/` validates against
`references/answer.schema.json` and every file under `invalid/` is refused by it (each invalid file
is named for the one thing wrong with it, and a test holds the name to the finding's path). The
dropped-field pass drops each required top-level field of every valid example in turn, and the
result must be refused. The shared `validate-examples.py` knows only the input and the result;
this suite is the answer's.
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
# the path each invalid example's finding lands on: its one thing wrong, where it is
WHERE = {
    "answer-version-2.json": "/answer_version",
    "ceremony-without-why.json": "/ceremony",
    "criteria-not-a-list.json": "/criteria",
    "footprint-empty.json": "/slices/0/footprint",
    "goal-blank.json": "/slices/0/goal",
    "goal-on-two-lines.json": "/slices/0/goal",
    "line-tag-outside-the-enum.json": "/lines/0/tag",
    "needs-build-doc-without-a-feature.json": "/",
    "needs-build-doc-without-a-constraint-line.json": "/lines",
    "question-without-touches.json": "/questions/0",
    "requirements-empty.json": "/slices/0/requirements",
    "slice-name-not-a-name.json": "/slices/0/name",
    "trace-kind-outside-the-enum.json": "/lines/0/trace/kind",
    "trace-ref-not-a-string.json": "/lines/0/trace/ref",
    "unknown-key.json": "/",
    "verify-not-a-string.json": "/criteria/0/verify",
}


def schema():
    with open(SCHEMA, encoding="utf-8") as fh:
        return json.load(fh)


def files(kind):
    return sorted(glob.glob(os.path.join(FOLDER, kind, "*.json")))


class TheSchema(unittest.TestCase):

    def test_it_is_closed_at_every_level(self):
        def walk(node, where):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False, where)
                for key, value in node.items():
                    walk(value, where + "/" + key)
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, "%s/%d" % (where, index))
        walk(schema(), "")

    def test_the_trace_kinds_are_the_shared_five_and_only_three_are_allowed_by_the_core(self):
        kinds = schema()["$defs"]["trace"]["properties"]["kind"]["enum"]
        self.assertEqual(sorted(kinds), sorted(["ledger", "repo_path", "question", "assumed", "owner_words"]))
        from blueprint_core import checks
        self.assertEqual(checks.ALLOWED_TRACES, ("ledger", "repo_path", "question"))


class TheExamples(unittest.TestCase):

    def test_every_valid_example_validates(self):
        found = files("valid")
        self.assertGreaterEqual(len(found), 3)
        for path in found:
            self.assertEqual(validate.errors_for(testlib.load_json(path), schema(), testlib.PREFIX), [], path)

    def test_every_invalid_example_is_refused_where_its_name_says(self):
        found = files("invalid")
        self.assertEqual(sorted(os.path.basename(p) for p in found), sorted(WHERE))
        for path in found:
            errors = validate.errors_for(testlib.load_json(path), schema(), testlib.PREFIX)
            self.assertTrue(errors, path)
            paths = [e["path"] for e in errors]
            self.assertIn(WHERE[os.path.basename(path)], paths, (path, errors))

    def test_dropping_any_required_field_is_refused(self):
        required = schema()["required"]
        for path in files("valid"):
            doc = testlib.load_json(path)
            for field in required:
                dropped = copy.deepcopy(doc)
                dropped.pop(field, None)
                self.assertTrue(validate.errors_for(dropped, schema(), testlib.PREFIX), (path, field))


if __name__ == "__main__":
    unittest.main()
