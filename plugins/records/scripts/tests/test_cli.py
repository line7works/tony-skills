"""The CLI's shape: help, usage, the missing dependency, JSON-only stdout, component identity.

The A7a interface tests for every command are slice 3's; these are the ones the commands on the
CLI need to keep honest meanwhile. Slice 2 added `state`, `render`, `import-legacy`, `mirrors`
and `survey` to `COMMANDS`; the slice 1 test that held those five absent was replaced by
`test_the_slice_2_commands_are_here_and_are_not_stubs`, which drives each of them against a real
fixture and requires a real answer.
"""
import json
import os
import unittest

import testlib

DOC = testlib.DOC
COMMANDS = ("verify", "events", "identity", "append", "component-identity",
            "state", "render", "import-legacy", "mirrors", "survey")
SLICE_2 = ("state", "render", "import-legacy", "mirrors", "survey")


class Help(unittest.TestCase):
    def test_the_top_level_help_names_every_command(self):
        code, out, err = testlib.run_cli(["--help"])
        self.assertEqual(code, 0, err)
        for name in COMMANDS:
            self.assertIn(name, out, name)

    def test_each_command_documents_arguments_defaults_an_example_and_side_effects(self):
        for name in COMMANDS:
            code, out, err = testlib.run_cli([name, "--help"])
            self.assertEqual(code, 0, "%s: %s" % (name, err))
            self.assertIn("side effects:", out, name)
            self.assertIn("exit:", out, name)
        code, out, _ = testlib.run_cli(["--help"])
        self.assertIn("uv run records.py append", out, "the top-level help carries the examples")

    def test_the_slice_2_commands_are_here_and_are_not_stubs(self):
        """Each answers from a real fixture workspace, with the fields section 12.2 names."""
        scratch = testlib.make_scratch("records-cli-slice2-")
        try:
            workspace = testlib.fixture_workspace(scratch)
            doc = "docs/plans/2026-05-12-history.md"
            code, imported, err = testlib.run_json(
                ["import-legacy", "--workspace", workspace, "--doc", doc])
            self.assertEqual(code, 0, err)
            self.assertGreater(imported["imported"], 0)
            calls = {
                "state": ["state", "--workspace", workspace, "--doc", doc],
                "render": ["render", "--workspace", workspace, "--doc", doc,
                           "--run-id", imported["run_id"]],
                "mirrors": ["mirrors", "--workspace", workspace, "--doc", doc],
                "survey": ["survey", "--workspace", workspace],
            }
            for name, args in sorted(calls.items()):
                code, body, err = testlib.run_json(args)
                self.assertEqual(code, 0, "%s: %s" % (name, err))
                self.assertTrue(body["ok"], name)
                self.assertEqual(body["interface_version"], 1, name)
                self.assertIn("component_version", body, name)
            self.assertGreater(len(testlib.run_json(calls["state"])[1]["findings"]), 0)
            self.assertTrue(testlib.run_json(calls["render"])[1]["text"])
            self.assertTrue(testlib.run_json(calls["survey"])[1]["documents"])
        finally:
            testlib.rmtree(scratch)

    def test_every_command_names_its_side_effects_and_its_exit_codes(self):
        for name in SLICE_2:
            code, out, err = testlib.run_cli([name, "--help"])
            self.assertEqual(code, 0, "%s: %s" % (name, err))
            self.assertIn("side effects:", out, name)
            self.assertIn("exit:", out, name)

    def test_a_slice_2_command_without_its_arguments_is_a_usage_error(self):
        for name in SLICE_2:
            code, out, err = testlib.run_cli([name])
            self.assertEqual(code, 2, name)
            self.assertEqual(out, "", name)

    def test_help_works_without_jsonschema(self):
        """The guide: keep --help available when an execution dependency is missing."""
        scratch = testlib.make_scratch("records-help-")
        try:
            stub = testlib.stub_without_jsonschema(scratch)
            code, out, err = testlib.run_cli(["--help"], env={"PYTHONPATH": stub})
            self.assertEqual(code, 0, err)
            self.assertIn("records.py", out)
        finally:
            testlib.rmtree(scratch)


class Usage(unittest.TestCase):
    def test_no_command_is_a_usage_error(self):
        code, out, err = testlib.run_cli([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_an_unknown_argument_is_a_usage_error(self):
        code, out, err = testlib.run_cli(["verify", "--workspace", ".", "--doc", DOC, "--nope"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("error:", err)

    def test_a_workspace_that_is_not_a_directory_is_a_usage_error(self):
        code, out, err = testlib.run_cli(["verify", "--workspace", "/no/such/place", "--doc", DOC])
        self.assertEqual(code, 2)
        self.assertIn("--workspace", err)

    def test_a_doc_outside_the_workspace_is_a_usage_error(self):
        scratch = testlib.make_scratch("records-usage-")
        try:
            workspace = testlib.make_workspace(scratch)
            for doc in ("/etc/passwd.md", "../elsewhere.md", "docs/../../out.md"):
                code, out, err = testlib.run_cli(["verify", "--workspace", workspace, "--doc", doc])
                self.assertEqual(code, 2, doc)
                self.assertEqual(out, "", doc)
        finally:
            testlib.rmtree(scratch)

    def test_a_doc_that_is_not_markdown_is_a_usage_error(self):
        scratch = testlib.make_scratch("records-usage-")
        try:
            workspace = testlib.make_workspace(scratch)
            code, out, err = testlib.run_cli(["verify", "--workspace", workspace, "--doc", "docs/plans/thing"])
            self.assertEqual(code, 2)
            self.assertIn("Markdown", err)
        finally:
            testlib.rmtree(scratch)

    def test_a_component_root_that_is_not_a_directory_is_a_usage_error(self):
        code, out, err = testlib.run_cli(["--component-root", "/no/such/root", "component-identity"])
        self.assertEqual(code, 2)
        self.assertIn("--component-root", err)


class MissingDependency(unittest.TestCase):
    def test_every_command_exits_3_without_jsonschema(self):
        scratch = testlib.make_scratch("records-dep-")
        try:
            stub = testlib.stub_without_jsonschema(scratch)
            workspace = testlib.make_workspace(scratch)
            calls = {
                "verify": ["verify", "--workspace", workspace, "--doc", DOC],
                "events": ["events", "--workspace", workspace, "--doc", DOC],
                "identity": ["identity", "--workspace", workspace],
                "component-identity": ["component-identity"],
            }
            for name, args in calls.items():
                code, out, err = testlib.run_cli(args, env={"PYTHONPATH": stub})
                self.assertEqual(code, 3, "%s: %s" % (name, err))
                self.assertEqual(out, "", name)
                self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY, name)
        finally:
            testlib.rmtree(scratch)

    def test_the_test_hook_reaches_the_same_exit(self):
        code, out, err = testlib.run_cli(["component-identity"],
                                         env={"RECORDS_TEST": "1", "RECORDS_TEST_NO_JSONSCHEMA": "1"})
        self.assertEqual(code, 3)
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_the_hook_is_ignored_without_its_gate(self):
        code, out, err = testlib.run_cli(["component-identity"], env={"RECORDS_TEST_NO_JSONSCHEMA": "1"})
        self.assertEqual(code, 0, err)


class ComponentIdentity(unittest.TestCase):
    def test_it_names_the_component_and_hashes_its_content(self):
        code, doc, err = testlib.run_json(["component-identity"])
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["name"], "records")
        self.assertEqual(len(doc["content_sha256"]), 64)
        self.assertEqual(doc["interface_version"], 1)
        self.assertEqual(doc["component_version"], doc["version"])

    def test_the_content_hash_moves_with_the_content(self):
        scratch = testlib.make_scratch("records-ci-")
        try:
            import shutil
            copy_root = os.path.join(scratch, "records")
            shutil.copytree(testlib.ROOT, copy_root,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            code, first, err = testlib.run_json(["--component-root", copy_root, "component-identity"])
            self.assertEqual(code, 0, err)
            testlib.write(os.path.join(copy_root, "references", "examples", "valid", "extra.json"), "{}\n")
            code, second, err = testlib.run_json(["--component-root", copy_root, "component-identity"])
            self.assertEqual(code, 0, err)
            self.assertNotEqual(first["content_sha256"], second["content_sha256"])
        finally:
            testlib.rmtree(scratch)


class StdoutIsJsonOnly(unittest.TestCase):
    def test_every_successful_command_prints_one_json_document(self):
        scratch = testlib.make_scratch("records-out-")
        try:
            workspace = testlib.make_workspace(scratch)
            for args in (["verify", "--workspace", workspace, "--doc", DOC],
                         ["events", "--workspace", workspace, "--doc", DOC],
                         ["identity", "--workspace", workspace],
                         ["component-identity"]):
                code, out, err = testlib.run_cli(args, cwd=workspace)
                self.assertEqual(code, 0, err)
                document = json.loads(out)
                self.assertIn("interface_version", document)
                self.assertIn("component_version", document)
                self.assertEqual(err, "", args[0])
        finally:
            testlib.rmtree(scratch)

    def test_every_response_carries_ok(self):
        scratch = testlib.make_scratch("records-ok-")
        try:
            workspace = testlib.make_workspace(scratch)
            code, doc, err = testlib.run_json(["verify", "--workspace", workspace, "--doc", DOC])
            self.assertEqual(code, 0, err)
            self.assertTrue(doc["ok"])
            batch = testlib.events_file(scratch, [testlib.opened()])
            code, doc, _ = testlib.run_json(["append", "--workspace", workspace, "--doc", DOC,
                                             "--events", batch, "--expect-head", "a" * 64])
            self.assertEqual(code, 7)
            self.assertFalse(doc["ok"])
            self.assertEqual(doc["log"], "docs/records/docs__plans__2026-04-01-widget.events.jsonl")
            self.assertEqual(doc["events"], 0)
        finally:
            testlib.rmtree(scratch)

    def test_a_refusal_also_prints_one_json_document(self):
        scratch = testlib.make_scratch("records-out-")
        try:
            workspace = testlib.make_workspace(scratch)
            batch = testlib.events_file(scratch, [testlib.opened()])
            code, out, err = testlib.run_cli(["append", "--workspace", workspace, "--doc", DOC,
                                              "--events", batch, "--expect-head", "a" * 64])
            self.assertEqual(code, 7)
            document = json.loads(out)
            self.assertEqual(document["error"], "conflict")
            self.assertIn("interface_version", document)
        finally:
            testlib.rmtree(scratch)


class Examples(unittest.TestCase):
    def test_the_example_suite_passes(self):
        code, out, err = testlib.run_cli([], script=testlib.EXAMPLES_CLI)
        document = json.loads(out)
        self.assertEqual(code, 0, document.get("failures"))
        self.assertTrue(document["ok"])
        self.assertGreater(document["valid"]["files"], 0)
        self.assertEqual(document["invalid"]["total"], document["invalid"]["rejected"])
        self.assertEqual(document["mutations"]["total"], document["mutations"]["rejected"])
        self.assertTrue(document["log"]["ok"])

    def test_the_example_suite_reports_a_broken_example(self):
        scratch = testlib.make_scratch("records-ex-")
        try:
            import shutil
            copy_root = os.path.join(scratch, "records")
            shutil.copytree(testlib.ROOT, copy_root,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            testlib.write(os.path.join(copy_root, "references", "examples", "valid", "broken.json"),
                          json.dumps({"v": 1, "kind": "card_set"}) + "\n")
            code, out, err = testlib.run_cli(["--component-root", copy_root], script=testlib.EXAMPLES_CLI)
            self.assertEqual(code, 4)
            document = json.loads(out)
            self.assertFalse(document["ok"])
            self.assertTrue(any("broken.json" in f for f in document["failures"]))
        finally:
            testlib.rmtree(scratch)

    def test_the_example_suite_exits_3_without_jsonschema(self):
        scratch = testlib.make_scratch("records-ex-")
        try:
            stub = testlib.stub_without_jsonschema(scratch)
            code, out, err = testlib.run_cli([], script=testlib.EXAMPLES_CLI, env={"PYTHONPATH": stub})
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
        finally:
            testlib.rmtree(scratch)


class NoWritesIntoTheWorktree(unittest.TestCase):
    def test_the_component_root_is_unchanged_by_a_run(self):
        code, before, err = testlib.run_json(["component-identity"])
        self.assertEqual(code, 0, err)
        scratch = testlib.make_scratch("records-clean-")
        try:
            workspace = testlib.make_workspace(scratch)
            batch = testlib.events_file(scratch, [testlib.opened()])
            testlib.run_cli(["append", "--workspace", workspace, "--doc", DOC, "--events", batch,
                             "--expect-head", testlib.ZERO])
            testlib.run_cli(["verify", "--workspace", workspace, "--doc", DOC])
        finally:
            testlib.rmtree(scratch)
        code, after, err = testlib.run_json(["component-identity"])
        self.assertEqual(code, 0, err)
        self.assertEqual(before["content_sha256"], after["content_sha256"])


if __name__ == "__main__":
    unittest.main()
