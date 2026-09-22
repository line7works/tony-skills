"""The schemas, the two validator scripts, and the places the documents must agree with the code.

The guide's rule for schemas is that each one is tested with an accepted example for every
legitimate outcome and rejected examples for forbidden states, including absent optional fields;
`validate-examples.py` is that check and this suite runs it. What this file adds is the
agreement between the SHIPPED DOCUMENTS and the CODE, in both directions, so a document that
describes behaviour the code does not have (or misses behaviour it does) fails here.
"""
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()

from build_core import exits, result as resultmod, validate  # noqa: E402

CONTRACT = os.path.join(testlib.REF, "build-contract.md")


def uv_run(script, args):
    """Run a script THROUGH `uv run`, which supplies the pinned dependency.

    One `uv run` costs a lock and a resolution, and the whole example corpus through it is ~76 of
    them. Two suites doing that at once race on uv's cache, which is what made the control room's
    first check round show a spurious exit-3 failure that did not reproduce when it ran the floor
    suite alone. So the corpus goes through `plain_run` and a named handful goes through here:
    the dependency path is still exercised, and the suite stops being a way to make the checker's
    own runs flake.
    """
    argv = testlib.uv_python() + [os.path.join(testlib.SCRIPTS, script)] + list(args)
    proc = subprocess.run(argv, cwd=testlib.scratch_base(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=testlib.base_env())
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def plain_run(script, args):
    """Run a script under this interpreter, for the per-example sweeps."""
    return testlib.run_script(script, args, cwd=testlib.scratch_base())


class EveryExampleHolds(unittest.TestCase):

    def test_validate_examples_passes_under_the_floor_interpreter(self):
        code, out, err = uv_run("validate-examples.py", [])
        self.assertEqual(code, 0, out + err)
        report = json.loads(out)
        self.assertTrue(report["ok"])
        self.assertGreater(report["counts"]["accepted"], 20)
        self.assertGreater(report["counts"]["rejected"], 20)
        self.assertGreater(report["counts"]["dropped"], 100)
        self.assertEqual(report["semantic_checks_without_an_example"], [])

    def test_validate_examples_reports_a_usage_slip(self):
        code, out, err = uv_run("validate-examples.py", ["--nope"])
        self.assertEqual(code, exits.USAGE, out + err)

    def test_validate_examples_helps_without_the_dependency(self):
        env = testlib.base_env({"PYTHONPATH": testlib.stub_without_jsonschema(
            testlib.make_scratch("build-v2-schema-help-"))})
        code, out, err = testlib.run_script("validate-examples.py", ["--help"], env=env)
        self.assertEqual(code, 0, err)
        self.assertIn("references/examples", out)

    def test_validate_examples_exits_three_without_the_dependency(self):
        env = testlib.base_env({"PYTHONPATH": testlib.stub_without_jsonschema(
            testlib.make_scratch("build-v2-schema-dep-"))})
        code, out, err = testlib.run_script("validate-examples.py", [], env=env)
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)


class TheResultValidator(unittest.TestCase):

    def setUp(self):
        self.valid = os.path.join(testlib.EX, "result", "valid")
        self.invalid = os.path.join(testlib.EX, "result", "invalid")

    def test_every_accepted_example_passes_it(self):
        for name in sorted(os.listdir(self.valid)):
            code, out, err = plain_run("validate-result.py", [os.path.join(self.valid, name)])
            self.assertEqual(code, 0, "%s: %s%s" % (name, out, err))
            self.assertTrue(json.loads(out)["ok"], name)

    def test_every_rejected_example_fails_it_with_exit_four(self):
        for name in sorted(os.listdir(self.invalid)):
            code, out, err = plain_run("validate-result.py", [os.path.join(self.invalid, name)])
            self.assertEqual(code, exits.VALIDATION, "%s: %s%s" % (name, out, err))
            report = json.loads(out)
            self.assertFalse(report["ok"], name)
            self.assertTrue(report["schema"] or report["semantic"], name)

    def test_a_result_that_is_not_there_is_a_usage_slip(self):
        code, out, err = plain_run("validate-result.py", ["/no/such/result.json"])
        self.assertEqual(code, exits.USAGE, out)
        self.assertIn("no such result file", err)

    def test_a_check_it_could_not_make_says_it_was_skipped(self):
        stopped = os.path.join(self.valid, "stopped-no-base.json")
        code, out, _ = plain_run("validate-result.py", [stopped])
        self.assertEqual(code, 0)
        skipped = [row["id"] for row in json.loads(out)["skipped"]]
        self.assertTrue(skipped, "a stop before the checks ran skips V4")

    def test_one_of_each_outcome_goes_through_uv_run_with_the_pinned_dependency(self):
        """The dependency path, exercised on a named handful rather than on all 76 examples."""
        for name, expect in (("completed-card-moved.json", 0), ("answer-refused.json", 0),
                             ("stopped-no-base.json", 0)):
            code, out, err = uv_run("validate-result.py", [os.path.join(self.valid, name)])
            self.assertEqual(code, 0, "%s: %s%s" % (name, out, err))
            self.assertTrue(json.loads(out)["ok"], name)
        for name in ("no-status.json", "semantic-card-moved-over-a-failing-check.json"):
            code, out, err = uv_run("validate-result.py", [os.path.join(self.invalid, name)])
            self.assertEqual(code, exits.VALIDATION, "%s: %s%s" % (name, out, err))


class TheDocumentsAgreeWithTheCode(unittest.TestCase):
    """A shipped document that describes behaviour the code does not have is a defect."""

    def setUp(self):
        with open(CONTRACT, encoding="utf-8") as fh:
            self.contract = fh.read()
        self.result_schema = validate.load_schema("result")

    def test_every_stop_tag_of_the_code_is_in_the_schema_and_in_the_contract(self):
        described = self.result_schema["properties"]["stop_tag"]["description"]
        for tag in resultmod.STOP_TAGS:
            self.assertIn("`%s`" % tag, described, tag)
            self.assertIn(tag, self.contract, "%s is not in build-contract.md" % tag)

    def test_the_schema_describes_no_tag_the_code_cannot_emit(self):
        described = [t.strip("`") for t in
                     self.result_schema["properties"]["stop_tag"]["description"].split("`")[1::2]]
        for tag in described:
            self.assertIn(tag, resultmod.STOP_TAGS, tag)

    def test_every_status_of_the_schema_is_in_the_contract(self):
        for status in self.result_schema["properties"]["status"]["enum"]:
            self.assertIn("`%s`" % status, self.contract, status)

    def test_every_semantic_check_is_named_in_the_contract(self):
        for check_id in validate.CHECK_IDS:
            self.assertIn(check_id, self.contract, check_id)

    def test_every_phase_of_the_cli_is_named_in_the_contract(self):
        for phase in ("check-input", "contract", "preflight", "record-answer", "report",
                      "identity", "skill-identity"):
            self.assertIn(phase, self.contract, phase)

    def test_every_exit_code_of_the_code_is_named_in_the_contract(self):
        for code in exits.ALL:
            self.assertIn("exit %d" % code, self.contract.replace("exits ", "exit "), code)

    def test_the_component_commands_the_contract_names_are_the_ones_the_core_calls(self):
        from build_core import records_client
        called = set()
        for name in dir(records_client.Client):
            if name.startswith("_"):
                continue
            called.add(name.replace("_", "-"))
        for command in ("state", "events", "verify", "append", "identity", "import-legacy",
                        "component-identity"):
            self.assertIn(command, called, command)
            self.assertIn(command, self.contract, "%s is not in build-contract.md" % command)

    def test_the_contract_names_the_one_event_kind_this_core_writes(self):
        self.assertIn("card_set", self.contract)
        for kind in ("finding_raised", "disposition", "waived", "reopened"):
            self.assertIn(kind, self.contract, "%s must be named as one this core never writes" % kind)


class TheExclusionListIsTheComponentsOwn(unittest.TestCase):

    def test_the_prefix_matches_what_the_component_publishes(self):
        from build_core import sources
        scratch = testlib.make_scratch("build-v2-exclusion-agree-")
        self.addCleanup(testlib.rmtree, scratch)
        ws = testlib.make_workspace(scratch)
        code, out, err = testlib.run_build(["identity", ws])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["excluded"], list(sources.EXCLUDED_PREFIXES))


class TheSchemasAreClosed(unittest.TestCase):
    """Every object is closed, so an unknown key is refused rather than ignored (guide L186)."""

    def _walk(self, node, path, found):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                found.append((path, node.get("additionalProperties")))
            for key, value in node.items():
                self._walk(value, "%s/%s" % (path, key), found)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self._walk(value, "%s/%d" % (path, index), found)

    def test_every_object_of_every_schema_is_closed(self):
        for name in validate.SCHEMA_FILES:
            schema = validate.load_schema(name)
            found = []
            self._walk(schema, name, found)
            self.assertTrue(found, name)
            for path, closed in found:
                self.assertIs(closed, False, "%s is not closed" % path)

    def test_every_schema_carries_its_version_field(self):
        for name, field in (("input", "input_version"), ("answer", "seeded_answer"),
                            ("result", "result_version"), ("receipt", "receipt_version"),
                            ("checkpoint", "checkpoint_version")):
            schema = validate.load_schema(name)
            self.assertIn(field, schema["required"], name)
            self.assertEqual(schema["properties"][field]["const"], 1, name)


if __name__ == "__main__":
    unittest.main()


class TheSemanticWalkerNeverCrashes(unittest.TestCase):
    """`validate-result.py` takes any file, so a shape the schema would refuse reaches the
    semantic checks too. A crash there is a validator that cannot say what is wrong with its
    input, so every check reads defensively and reports instead."""

    MALFORMED = [
        {},
        {"status": "completed"},
        {"status": "stopped", "source_set": "not an object"},
        {"status": "completed", "checks": ["not an object"]},
        {"status": "completed", "out_of_scope": [None]},
        {"status": "completed", "writes": ["not an object"]},
        {"status": "completed", "records": {"appended": ["not an object"]}},
        {"status": "completed", "source_set": {"sanctioned": ["a bare string"]}},
        {"status": "completed", "card": "not an object", "answer": 7},
        {"status": "answer_refused", "terminal_status": "completion"},
    ]

    def test_no_malformed_result_raises(self):
        for document in self.MALFORMED:
            try:
                report = validate.run_semantic(document, None, None)
            except Exception as exc:                      # noqa: BLE001 - that is the point
                self.fail("run_semantic raised %s on %r" % (type(exc).__name__, document))
            self.assertIsInstance(report["semantic"], list)
            self.assertIsInstance(report["skipped"], list)

    def test_the_validator_script_reports_rather_than_crashing(self):
        scratch = testlib.make_scratch("build-v2-malformed-")
        self.addCleanup(testlib.rmtree, scratch)
        path = os.path.join(scratch, "malformed.json")
        testlib.write_json(path, {"status": "completed", "source_set": {"sanctioned": ["bare"]}})
        code, out, err = plain_run("validate-result.py", [path])
        self.assertEqual(code, exits.VALIDATION, out + err)
        self.assertFalse(json.loads(out)["ok"])


class TheSanctionedPathIsNeverOutOfScope(unittest.TestCase):

    def test_v3_counts_a_sanctioned_path_as_in_scope(self):
        source = {"base": "base", "base_commit": "0" * 40, "head": "0" * 40,
                  "committed": [], "changed": ["docs/plans/x.md"], "untracked": [],
                  "excluded": ["docs/records/"],
                  "sanctioned": [{"path": "docs/plans/x.md", "reason": "the ledger document"}]}
        result = {"status": "completed", "terminal_status": "completion",
                  "source_set": source, "contract": {"named_paths": [], "checks": []},
                  "out_of_scope": [], "checks": [], "records": {}, "writes": []}
        self.assertEqual([f["id"] for f in validate.run_semantic(result)["semantic"]], [])

    def test_v3_refuses_a_sanctioned_path_that_was_listed_out_of_scope(self):
        source = {"base": "base", "base_commit": "0" * 40, "head": "0" * 40,
                  "committed": [], "changed": ["docs/plans/x.md"], "untracked": [],
                  "excluded": ["docs/records/"],
                  "sanctioned": [{"path": "docs/plans/x.md", "reason": "the ledger document"}]}
        result = {"status": "completed", "terminal_status": "completion",
                  "source_set": source, "contract": {"named_paths": [], "checks": []},
                  "out_of_scope": [{"path": "docs/plans/x.md", "lists": ["changed"],
                                    "reason": None, "reason_given": False}],
                  "checks": [], "records": {}, "writes": []}
        self.assertIn("V3", [f["id"] for f in validate.run_semantic(result)["semantic"]])
