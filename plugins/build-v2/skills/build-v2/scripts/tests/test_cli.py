"""The A7a helper interface, for every command of this CLI.

`docs/plans/2026-09-13-recheck-v2-e8-core.md` section 6, as the control room ruled it for this
lane on 2026-09-22: `--help` with the arguments, the defaults, an example and the side effects,
and working without the dependency; JSON on stdout and nothing else; diagnostics on stderr;
exit 0 an intermediate phase, 2 usage, 3 missing dependency, 4 validation, 10 a terminal status,
1 anything else. Every response carries `interface_version` and `plugin_version`.
"""
import json
import os
import unittest

import testlib

COMMANDS = ("check-input", "contract", "preflight", "record-answer", "report", "identity",
            "skill-identity")


class Help(unittest.TestCase):
    """`--help` works with no dependency at all, and says what the phases take."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-help-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.without = testlib.base_env({"PYTHONPATH": testlib.stub_without_jsonschema(self.scratch)})

    def test_the_top_level_help_names_every_phase_and_its_inputs(self):
        code, out, err = testlib.run_build(["--help"], env=self.without)
        self.assertEqual(code, 0, err)
        for command in COMMANDS:
            self.assertIn(command, out, command)
        for word in ("input.json", "--run-dir", "--answer", "exit"):
            self.assertIn(word, out, word)

    def test_the_help_shows_an_example_and_the_side_effects(self):
        code, out, _ = testlib.run_build(["--help"], env=self.without)
        self.assertEqual(code, 0)
        self.assertIn("uv run build.py check-input", out)
        self.assertIn("references/input.schema.json", out)

    def test_every_command_has_its_own_help_without_the_dependency(self):
        for command in COMMANDS:
            code, out, err = testlib.run_build([command, "--help"], env=self.without)
            self.assertEqual(code, 0, "%s: %s" % (command, err))
            self.assertIn("usage:", out, command)

    def test_an_argument_check_works_without_the_dependency(self):
        code, out, err = testlib.run_build(["contract"], env=self.without)
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("--run-dir", err)


class MissingDependency(unittest.TestCase):
    """Exit 3, one line on stderr, nothing on stdout."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-dep-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.workspace = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")
        self.input = os.path.join(self.scratch, "input.json")
        testlib.write_json(self.input, testlib.make_input(self.run_dir, self.workspace))

    def test_a_missing_jsonschema_exits_three_with_the_pilots_message(self):
        env = testlib.base_env({"PYTHONPATH": testlib.stub_without_jsonschema(self.scratch)})
        code, out, err = testlib.run_build(["check-input", self.input], env=env)
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_the_hook_reports_the_same_thing(self):
        env = testlib.base_env({"BUILD_TEST": "1", "BUILD_TEST_NO_JSONSCHEMA": "1"})
        code, out, err = testlib.run_build(["check-input", self.input], env=env)
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)


class Usage(unittest.TestCase):
    """Exit 2: a bad argument, a file that is not there, a phase against the wrong phase."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-usage-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.workspace = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")
        self.input = os.path.join(self.scratch, "input.json")
        testlib.write_json(self.input, testlib.make_input(self.run_dir, self.workspace))

    def test_an_unknown_command_is_usage(self):
        code, out, err = testlib.run_build(["fly"])
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")

    def test_no_command_is_usage(self):
        code, out, err = testlib.run_build([])
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("usage:", err)

    def test_an_input_file_that_is_not_there_is_usage(self):
        code, out, err = testlib.run_build(["check-input", os.path.join(self.scratch, "nope.json")])
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("no such input file", err)

    def test_an_input_file_that_is_not_json_is_usage(self):
        path = os.path.join(self.scratch, "bad.json")
        testlib.write_text(path, "not json at all")
        code, out, err = testlib.run_build(["check-input", path])
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("not JSON", err)

    def test_a_phase_against_a_run_that_is_not_there_is_usage(self):
        code, out, err = testlib.run_build(["contract", "--run-dir", os.path.join(self.scratch, "gone")])
        self.assertEqual(code, 2, err)
        self.assertIn("no run at", err)

    def test_a_phase_against_the_wrong_phase_is_usage(self):
        code, out, err = testlib.run_build(["check-input", self.input])
        self.assertEqual(code, 0, err)
        code, out, err = testlib.run_build(["preflight", "--run-dir", self.run_dir])
        self.assertEqual(code, 2, err)
        self.assertIn("phase", err)

    def test_a_reused_run_id_is_refused_before_any_work(self):
        code, _, err = testlib.run_build(["check-input", self.input])
        self.assertEqual(code, 0, err)
        code, out, err = testlib.run_build(["check-input", self.input])
        self.assertEqual(code, 2, err)
        self.assertIn("already holds a checkpoint", err)

    def test_a_skill_root_that_is_not_a_directory_is_usage(self):
        code, out, err = testlib.run_build(["--skill-root", os.path.join(self.scratch, "nope"),
                                            "skill-identity"])
        self.assertEqual(code, 2, err)
        self.assertIn("--skill-root", err)


class Validation(unittest.TestCase):
    """Exit 4: a supplied file failed its schema. The errors are on stdout; nothing is written."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-valid-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.workspace = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")

    def _check(self, body):
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, body)
        return testlib.run_build(["check-input", path])

    def test_an_input_missing_a_required_field_is_validation(self):
        body = testlib.make_input(self.run_dir, self.workspace)
        del body["slice"]
        code, out, err = self._check(body)
        self.assertEqual(code, 4, err)
        document = json.loads(out)
        self.assertFalse(document["ok"])
        self.assertEqual(document["error"], "invalid")
        self.assertTrue(document["errors"])
        self.assertFalse(os.path.exists(self.run_dir), "nothing is written on a validation failure")

    def test_an_unknown_key_is_refused_rather_than_ignored(self):
        body = testlib.make_input(self.run_dir, self.workspace)
        body["reprot_only"] = True
        code, out, _ = self._check(body)
        self.assertEqual(code, 4)
        self.assertIn("reprot_only", json.dumps(json.loads(out)["errors"]))

    def test_a_run_dir_inside_the_workspace_is_a_path_rule_failure(self):
        body = testlib.make_input(os.path.join(self.workspace, "run"), self.workspace)
        code, out, _ = self._check(body)
        self.assertEqual(code, 4)
        self.assertIn("/run_dir", json.dumps(json.loads(out)["errors"]))

    def test_a_workspace_that_is_not_a_git_work_tree_is_a_path_rule_failure(self):
        other = os.path.join(self.scratch, "plain")
        os.makedirs(other)
        body = testlib.make_input(self.run_dir, other)
        code, out, _ = self._check(body)
        self.assertEqual(code, 4)
        self.assertIn("/workspace", json.dumps(json.loads(out)["errors"]))

    def test_a_build_doc_under_docs_records_is_refused(self):
        body = testlib.make_input(self.run_dir, self.workspace, doc="docs/records/a.md")
        code, out, _ = self._check(body)
        self.assertEqual(code, 4)
        self.assertIn("/build_doc", json.dumps(json.loads(out)["errors"]))

    def test_an_answer_that_fails_its_schema_is_validation_and_writes_nothing(self):
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.workspace))
        self.assertEqual(testlib.run_build(["check-input", path])[0], 0)
        self.assertEqual(testlib.run_build(["contract", "--run-dir", self.run_dir])[0], 0)
        code, _, err = testlib.run_build(["preflight", "--run-dir", self.run_dir])
        self.assertEqual(code, 0, err)
        answer = dict(testlib.ANSWER)
        answer["claimed_status"] = "finished"          # outside the enum
        answer_path = os.path.join(self.scratch, "answer.json")
        testlib.write_json(answer_path, answer)
        code, out, err = testlib.run_build(["record-answer", "--run-dir", self.run_dir,
                                            "--answer", answer_path])
        self.assertEqual(code, 4, err)
        self.assertIn("/claimed_status", json.dumps(json.loads(out)["errors"]))
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "answer.json")))
        # the run stays where it was, so a corrected answer can be supplied
        checkpoint = testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))
        self.assertEqual(checkpoint["phase"], "preflighted")


class TheEnvelope(unittest.TestCase):
    """Every response carries `interface_version` and `plugin_version`, and stdout is one document."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-envelope-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.workspace = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")
        self.input = os.path.join(self.scratch, "input.json")
        testlib.write_json(self.input, testlib.make_input(self.run_dir, self.workspace))
        self.answer = os.path.join(self.scratch, "answer.json")
        testlib.write_json(self.answer, testlib.ANSWER)

    def _document(self, args, expect):
        code, out, err = testlib.run_build(args)
        self.assertEqual(code, expect, "%s: %s%s" % (args, out, err))
        document = json.loads(out)     # one JSON document and nothing else
        self.assertEqual(document["interface_version"], 1)
        self.assertTrue(document["plugin_version"])
        return document

    def test_every_command_of_a_whole_run_carries_the_envelope(self):
        first = self._document(["check-input", self.input], 0)
        self.assertEqual(first["next"], "contract")
        self.assertEqual(self._document(["contract", "--run-dir", self.run_dir], 0)["next"], "preflight")
        self.assertEqual(self._document(["preflight", "--run-dir", self.run_dir], 0)["next"],
                         "record-answer")
        self.assertEqual(self._document(["record-answer", "--run-dir", self.run_dir,
                                         "--answer", self.answer], 0)["next"], "report")
        last = self._document(["report", "--run-dir", self.run_dir], 10)
        self.assertEqual(last["next"], "done")
        self.assertIn(last["terminal_status"], ("completion", "stop"))

    def test_identity_and_skill_identity_carry_it_too(self):
        identity = self._document(["identity", self.workspace], 0)
        self.assertEqual(sorted(identity["identity"]),
                         ["commit", "dirty", "submodules", "tracked_diff_sha256", "untracked",
                          "untracked_sha256"])
        self.assertEqual(identity["excluded"], ["docs/records/"])
        skill = self._document(["skill-identity"], 0)
        self.assertEqual(skill["name"], "build-v2")
        self.assertEqual(len(skill["content_sha256"]), 64)

    def test_a_validation_response_carries_it(self):
        body = testlib.make_input(self.run_dir, self.workspace)
        del body["base"]
        path = os.path.join(self.scratch, "bad-input.json")
        testlib.write_json(path, body)
        self._document(["check-input", path], 4)

    def test_a_command_after_the_run_ended_reports_the_recorded_outcome(self):
        for args, expect in ((["check-input", self.input], 0),
                             (["contract", "--run-dir", self.run_dir], 0),
                             (["preflight", "--run-dir", self.run_dir], 0),
                             (["record-answer", "--run-dir", self.run_dir, "--answer", self.answer], 0),
                             (["report", "--run-dir", self.run_dir], 10)):
            self._document(args, expect)
        before = testlib.tree_digest(self.run_dir)
        again = self._document(["contract", "--run-dir", self.run_dir], 10)
        self.assertEqual(again["next"], "done")
        self.assertIn("the run ended as", again["reason"])
        self.assertEqual(testlib.tree_digest(self.run_dir), before, "it wrote nothing")


class FromAnotherWorkingDirectory(unittest.TestCase):
    """Paths in arguments resolve from the caller's directory; bundled files from the script's."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-cwd-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.workspace = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")

    def test_a_whole_run_works_from_a_directory_outside_the_worktree(self):
        elsewhere = testlib.other_cwd(self.scratch)
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.workspace))
        answer = os.path.join(self.scratch, "answer.json")
        testlib.write_json(answer, testlib.ANSWER)
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", answer]):
            code, out, err = testlib.run_build(args, cwd=elsewhere)
            self.assertEqual(code, 0, "%s: %s%s" % (args, out, err))
        code, out, err = testlib.run_build(["report", "--run-dir", self.run_dir], cwd=elsewhere)
        self.assertEqual(code, 10, err)


class NoBytecodeIsLeftBehind(unittest.TestCase):

    def test_the_skill_tree_holds_no_pycache(self):
        found = []
        for base, dirs, _ in os.walk(testlib.PLUGIN):
            if "__pycache__" in dirs:
                found.append(os.path.join(base, "__pycache__"))
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
