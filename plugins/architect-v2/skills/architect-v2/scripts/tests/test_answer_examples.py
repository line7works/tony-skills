"""The recorded answer's examples (CR-8, required test 2).

`references/examples/answer/` holds `valid/` and `invalid/` examples and the context they are read
in (`context.json`: the scope doc and, where an example needs one, the living architecture doc,
both files beside it). Every valid example passes the schema and every content check; every
invalid example is named for the one thing wrong with it: a name starting `content-<rule>` passes
the schema and is refused by the content check `<rule>` (exit 5 at `record-answer`), any other
name is refused by the schema (exit 4). There is one content example per refusal of the brief's
3.4 and one schema example per missing walkthrough field.
"""
import glob
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from architect_core import harvesting, recording, schema  # noqa: E402

EX = os.path.join(testlib.EX, "answer")
REQUIRED_CONTENT = ("re-asked-decided", "untraced-poured-line", "untraced-deferred-line", "untraced-walkthrough",
                    "candidates-fewer-than-two", "candidates-not-distinct", "razor-serves-nothing",
                    "razor-serves-no-requirement", "rejected-without-why", "docless-without-reason",
                    "no-loss-run-block", "no-loss-poured-line")
REQUIRED_SCHEMA = ("walkthrough-without-who", "walkthrough-without-when", "walkthrough-without-must")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class _Examples(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("answer-ex-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.context = load(os.path.join(EX, "context.json"))

    def ctx(self, rel):
        conf = dict(self.context["default"])
        conf.update(self.context.get("cases", {}).get(rel, {}))
        ws = os.path.join(self.tmp, rel.replace("/", "_"), "ws")
        staging = os.path.join(self.tmp, rel.replace("/", "_"), "staging")
        os.makedirs(ws)
        os.makedirs(staging)
        scope_path = scope_text = living_path = living_text = None
        if not conf.get("docless"):
            with open(os.path.join(EX, conf["scope_doc"]), encoding="utf-8") as fh:
                scope_text = fh.read()
            scope_path = os.path.join(ws, conf["scope_rel"])
            testlib.write_text(scope_path, scope_text)
        if conf.get("living_doc"):
            with open(os.path.join(EX, conf["living_doc"]), encoding="utf-8") as fh:
                living_text = fh.read()
            living_path = os.path.join(ws, conf["living_rel"])
            testlib.write_text(living_path, living_text)
        harvest = harvesting.describe(ws, staging, conf["today"], conf["slug"], scope_path, scope_text,
                                      living_path, living_text, run_id=conf["run_id"],
                                      input_publish=conf.get("input_publish", True))
        return recording.context(harvest, living_text, session_id=conf["session_id"], takes=conf.get("takes", []))


class Valid(_Examples):

    def test_every_valid_example_is_accepted(self):
        files = sorted(glob.glob(os.path.join(EX, "valid", "*.json")))
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            rel = "valid/" + os.path.basename(path)
            doc = load(path)
            self.assertEqual(schema.errors(doc), [], rel)
            refusals, plan = recording.evaluate(doc, self.ctx(rel))
            self.assertEqual(refusals, [], rel)
            self.assertTrue(plan["doc_text"], rel)


class Invalid(_Examples):

    def test_every_invalid_example_is_refused_for_its_one_reason(self):
        files = sorted(glob.glob(os.path.join(EX, "invalid", "*.json")))
        names = [os.path.basename(p)[:-5] for p in files]
        for required in REQUIRED_CONTENT:
            self.assertIn("content-" + required, names)
        for required in REQUIRED_SCHEMA:
            self.assertIn(required, names)
        rules = recording.RULES
        for path in files:
            rel = "invalid/" + os.path.basename(path)
            name = os.path.basename(path)[:-5]
            doc = load(path)
            errors = schema.errors(doc)
            if name.startswith("content-"):
                self.assertEqual(errors, [], rel)
                rule = max((r for r in rules if name[len("content-"):].startswith(r)), key=len, default=None)
                self.assertIsNotNone(rule, "%s names no rule of %s" % (rel, sorted(rules)))
                refusals, plan = recording.evaluate(doc, self.ctx(rel))
                self.assertEqual(sorted(set(r["rule"] for r in refusals)), [rule], (rel, refusals))
            else:
                self.assertNotEqual(errors, [], rel)


if __name__ == "__main__":
    unittest.main()
