"""The A7a helper interface, for every command of every script this skill ships.

A7a (`docs/plans/2026-09-13-recheck-v2-e8-core.md` section 6, the definition the lane contract
cites): `--help` with arguments, defaults, an example and side effects; JSON on stdout and
nothing else; diagnostics on stderr; exit 0 success, 2 usage, 3 missing dependency, 4 validation,
10 a terminal status, 1 anything else. `--help` and argument checking keep working when the one
declared dependency is missing, so a caller can always find out what a command takes.

The missing dependency is a `PYTHONPATH` directory holding a `jsonschema` package whose
initializer raises `ImportError` — the real failure, not a simulation of its message.

Every command runs from a working directory outside the worktree and outside the plugin root, so
nothing passes by accident of where it was started.
"""
import json
import os
import unittest

import testlib

SCRIPTS = ("signoff.py", "validate-result.py", "validate-examples.py")
PHASES = ("check-input", "scope", "request", "record-answer", "record", "identity",
          "skill-identity")


class Help(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("signoff-cli-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.cwd = testlib.other_cwd(self.dir)
        self.stub = testlib.stub_without_jsonschema(self.dir)

    def without_jsonschema(self, script, args):
        return testlib.run_script(script, args, cwd=self.cwd, python=testlib.GEN_PYTHON,
                                  env={"PYTHONPATH": self.stub})

    def test_every_script_prints_help_without_the_dependency(self):
        for script in SCRIPTS:
            code, out, err = self.without_jsonschema(script, ["--help"])
            self.assertEqual(code, 0, "%s: %s" % (script, err))
            self.assertIn("usage:", out, script)

    def test_signoff_help_names_every_phase_and_the_exit_codes(self):
        code, out, err = self.without_jsonschema("signoff.py", ["--help"])
        self.assertEqual(code, 0, err)
        for phase in PHASES:
            self.assertIn(phase, out, phase)
        for piece in ("exit status", "10", "terminal status", "2 usage", "3 missing dependency"):
            self.assertIn(piece, out, piece)
        self.assertIn("side effects", out)
        self.assertIn("examples:", out)

    def test_every_phase_prints_its_own_help_without_the_dependency(self):
        for phase in PHASES:
            code, out, err = self.without_jsonschema("signoff.py", [phase, "--help"])
            self.assertEqual(code, 0, "%s: %s" % (phase, err))
            self.assertIn("usage:", out, phase)

    def test_argument_checking_works_without_the_dependency(self):
        code, out, err = self.without_jsonschema("signoff.py", ["scope"])
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("--run-dir", err)

    def test_an_unknown_command_is_usage(self):
        code, out, err = self.without_jsonschema("signoff.py", ["not-a-phase"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_no_command_at_all_prints_help_and_exits_usage(self):
        code, out, err = self.without_jsonschema("signoff.py", [])
        self.assertEqual(code, 2)
        self.assertIn("usage:", out)


class MissingDependency(unittest.TestCase):
    """Exit 3, one line on stderr, nothing on stdout — the pilot's shape."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-cli-dep-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.cwd = testlib.other_cwd(self.dir)
        self.stub = testlib.stub_without_jsonschema(self.dir)
        self.input = testlib.write_json(os.path.join(self.dir, "input.json"), {})

    def test_a_command_that_needs_the_dependency_exits_three(self):
        code, out, err = testlib.run_script(
            "signoff.py", ["check-input", self.input], cwd=self.cwd, python=testlib.GEN_PYTHON,
            env={"PYTHONPATH": self.stub, "RECORDS_ROOT": testlib.RECORDS_ROOT})
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_the_validators_exit_three_the_same_way(self):
        for script, args in (("validate-result.py", [self.input]), ("validate-examples.py", [])):
            code, out, err = testlib.run_script(script, args, cwd=self.cwd,
                                                python=testlib.GEN_PYTHON,
                                                env={"PYTHONPATH": self.stub})
            self.assertEqual(code, 3, "%s: %s" % (script, err))
            self.assertEqual(out, "", script)
            self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY, script)


class Usage(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("signoff-cli-usage-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.cwd = testlib.other_cwd(self.dir)
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}

    def phase(self, args):
        return testlib.signoff(args, cwd=self.cwd, env=self.env)

    def test_an_input_file_that_does_not_exist_is_usage(self):
        code, out, err = self.phase(["check-input", os.path.join(self.dir, "nope.json")])
        self.assertEqual(code, 2, err)
        self.assertIn("does not exist", err)

    def test_an_input_file_that_is_not_json_is_usage(self):
        path = os.path.join(self.dir, "bad.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        code, out, err = self.phase(["check-input", path])
        self.assertEqual(code, 2, err)
        self.assertIn("is not JSON", err)

    def test_a_run_directory_with_no_run_in_it_is_usage(self):
        empty = os.path.join(self.dir, "empty-run")
        os.makedirs(empty)
        for phase in ("scope", "request", "record"):
            code, out, err = self.phase([phase, "--run-dir", empty])
            self.assertEqual(code, 2, "%s: %s" % (phase, err))
            self.assertIn("holds no run", err)


class InvalidInput(unittest.TestCase):
    """An input that fails its schema is exit 4 (validation), with the errors in path order."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-cli-invalid-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.cwd = testlib.other_cwd(self.dir)
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}

    def check(self, doc):
        path = testlib.write_json(os.path.join(self.dir, "input.json"), doc)
        return testlib.signoff(["check-input", path], cwd=self.cwd, env=self.env)

    def test_an_empty_object_is_validation(self):
        code, out, err = self.check({})
        self.assertEqual(code, 4, err)
        self.assertFalse(out["ok"])
        self.assertEqual(out["interface_version"], 1)
        self.assertTrue(out["schema_errors"])

    def test_an_unknown_key_is_refused_rather_than_ignored(self):
        code, out, err = self.check({
            "protocol_version": 1, "workspace": "/tmp/x",
            "invocation": {"mode": "headless", "caller": "t", "run_id": "r",
                           "run_dir": "/tmp/r", "sessions": {"reviewing": "s"}},
            "target": {"build_doc": "docs/plans/a.md", "slice": "A", "base": "base"},
            "surprise": True})
        self.assertEqual(code, 4)
        self.assertTrue(any("surprise" in row["message"] for row in out["schema_errors"]),
                        out["schema_errors"])

    def test_a_build_doc_under_docs_records_is_refused(self):
        code, out, err = self.check({
            "protocol_version": 1, "workspace": "/tmp/x",
            "invocation": {"mode": "headless", "caller": "t", "run_id": "r",
                           "run_dir": "/tmp/r", "sessions": {"reviewing": "s"}},
            "target": {"build_doc": "docs/records/x.md", "slice": "A", "base": "base"}})
        self.assertEqual(code, 4)

    def test_a_build_doc_under_docs_reviews_is_refused(self):
        code, out, err = self.check({
            "protocol_version": 1, "workspace": "/tmp/x",
            "invocation": {"mode": "headless", "caller": "t", "run_id": "r",
                           "run_dir": "/tmp/r", "sessions": {"reviewing": "s"}},
            "target": {"build_doc": "docs/reviews/x.md", "slice": "A", "base": "base"}})
        self.assertEqual(code, 4)

    def test_a_run_directory_inside_the_workspace_is_a_named_stop(self):
        workspace = os.path.join(self.dir, "ws")
        os.makedirs(workspace)
        code, out, err = self.check({
            "protocol_version": 1, "workspace": workspace,
            "invocation": {"mode": "headless", "caller": "t", "run_id": "r",
                           "run_dir": os.path.join(workspace, "run"),
                           "sessions": {"reviewing": "s"}},
            "target": {"build_doc": "docs/plans/a.md", "slice": "A", "base": "base"}})
        self.assertEqual(code, 10, err)
        self.assertEqual(out["status"], "stopped")
        self.assertEqual(out["stop_reason_code"], "path_rules")
        self.assertIn("inside the workspace", out["stop_reason"])


class EveryResponseCarriesTheEnvelope(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("signoff-cli-env-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.cwd = testlib.other_cwd(self.dir)
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        self.case = testlib.build_case("S1-review-scope", "S1-01-clean",
                                       os.path.join(self.dir, "S1-review-scope"))

    def test_interface_version_and_plugin_version_on_every_phase(self):
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        run_dir = os.path.join(self.case, "run")
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "env-run",
                              "run_dir": run_dir, "run_date": "2026-09-21", "harness": None,
                              "sessions": seeded["sessions"]},
               "workspace": os.path.join(self.case, "workspace"),
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": True, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(self.case, "in.json"), doc)
        calls = [["check-input", path], ["scope", "--run-dir", run_dir],
                 ["request", "--run-dir", run_dir],
                 ["record-answer", "--run-dir", run_dir, "--answer",
                  os.path.join(self.case, "answer.json")],
                 ["record", "--run-dir", run_dir],
                 ["identity", os.path.join(self.case, "workspace")],
                 ["skill-identity"]]
        for args in calls:
            code, out, err = testlib.signoff(args, cwd=self.cwd, env=self.env)
            self.assertIn(code, (0, 10), "%s: %s" % (args[0], err))
            self.assertIsInstance(out, dict, args[0])
            self.assertEqual(out["interface_version"], 1, args[0])
            self.assertEqual(out["plugin_version"], self.plugin_version(), args[0])

    def plugin_version(self):
        return testlib.load_json(os.path.join(testlib.PLUGIN, ".claude-plugin",
                                              "plugin.json"))["version"]

    def test_stdout_is_one_json_document_and_nothing_else(self):
        code, out, err = testlib.run_script("signoff.py", ["skill-identity"], cwd=self.cwd,
                                            env={"RECORDS_ROOT": testlib.RECORDS_ROOT})
        self.assertEqual(code, 0, err)
        json.loads(out)                                   # parses whole, so nothing else is there
        self.assertEqual(out.count("\n"), out.rstrip("\n").count("\n") + 1)

    def test_skill_identity_names_the_skill_and_hashes_its_content(self):
        code, out, err = testlib.signoff(["skill-identity"], cwd=self.cwd, env=self.env)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["name"], "signoff-v2")
        self.assertEqual(len(out["content_sha256"]), 64)
        self.assertGreater(out["files"], 10)


if __name__ == "__main__":
    unittest.main()
