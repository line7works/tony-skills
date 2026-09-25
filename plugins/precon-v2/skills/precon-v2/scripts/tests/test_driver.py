"""The phase driver of this core (required test 12), through the real CLI.

`--help` without jsonschema; `identity` and `skill-identity` at `interface_version` 1;
`check-input` on the valid and invalid examples (their absolute paths pointed at temporary
directories); `select` on a fixture for every hunt the core's table names; the four phases a lane
fills stop as `phase-not-built`; `validate-examples.py` green; `validate-result.py` both ways.
Every run is made from a working directory outside the worktree.
"""
import glob
import importlib.util
import json
import os
import unittest

import testlib

EXAMPLE_PATHS = {"/tmp/widget-workspace": "ws", "/tmp/widget-staging": "staging",
                 "/tmp/station-runs/run-0001": "run"}


def station_module():
    spec = importlib.util.spec_from_file_location("station_driver_under_test", testlib.DRIVER)
    module = importlib.util.module_from_spec(spec)
    testlib.add_scripts_to_path()
    spec.loader.exec_module(module)
    return module


class _Cli(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("driver-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.cwd = os.path.join(self.tmp, "elsewhere")
        os.makedirs(self.cwd)
        self.ws = testlib.git_workspace(self.tmp, "ws")
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        self.run_dir = os.path.join(self.tmp, "run")

    def cli(self, args, env=None):
        return testlib.run_driver(args, cwd=self.cwd, env=env)

    def json_out(self, out):
        doc = json.loads(out)
        self.assertEqual(doc["interface_version"], 1)
        return doc

    def localize(self, doc):
        text = json.dumps(doc)
        for example, name in EXAMPLE_PATHS.items():
            text = text.replace(example, os.path.join(self.tmp, name))
        return json.loads(text)

    def checked(self, **extra):
        path = os.path.join(self.tmp, "input.json")
        testlib.write_json(path, testlib.make_input(self.ws, self.run_dir, staging=self.staging, **extra))
        code, out, err = self.cli(["check-input", path])
        self.assertEqual(code, 0, out + err)
        return self.json_out(out)


class Help(_Cli):

    def test_help_without_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.tmp)
        env = testlib.base_env({"PYTHONPATH": stub})
        code, out, err = self.cli(["--help"], env=env)
        self.assertEqual(code, 0, err)
        for word in ("check-input", "select", "harvest", "record-answer", "write", "report",
                     "identity", "skill-identity", "Exit", "Side effects"):
            self.assertIn(word, out)

    def test_check_input_without_jsonschema_is_exit_3(self):
        stub = testlib.stub_without_jsonschema(self.tmp)
        path = os.path.join(self.tmp, "input.json")
        testlib.write_json(path, testlib.make_input(self.ws, self.run_dir))
        code, out, err = self.cli(["check-input", path], env=testlib.base_env({"PYTHONPATH": stub}))
        self.assertEqual((code, out), (3, ""))
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
        self.assertFalse(os.path.exists(self.run_dir))

    def test_the_jsonschema_hook(self):
        path = os.path.join(self.tmp, "input.json")
        testlib.write_json(path, testlib.make_input(self.ws, self.run_dir))
        env = testlib.base_env({testlib.PREFIX + "_TEST": "1", testlib.PREFIX + "_TEST_NO_JSONSCHEMA": "1"})
        code, out, err = self.cli(["check-input", path], env=env)
        self.assertEqual((code, out), (3, ""))

    def test_no_command_is_usage(self):
        code, out, err = self.cli([])
        self.assertEqual(code, 2)


class Identity(_Cli):

    def test_identity(self):
        code, out, err = self.cli(["identity", self.ws])
        self.assertEqual(code, 0, err)
        doc = self.json_out(out)
        self.assertEqual(doc["kind"], "git")
        self.assertEqual(len(doc["head"]), 40)
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        doc = self.json_out(self.cli(["identity", plain])[1])
        self.assertEqual((doc["kind"], doc["head"]), ("directory", None))
        self.assertEqual(self.cli(["identity", os.path.join(self.tmp, "missing")])[0], 2)

    def test_skill_identity(self):
        code, out, err = self.cli(["skill-identity"])
        self.assertEqual(code, 0, err)
        doc = self.json_out(out)
        self.assertEqual(doc["name"], testlib.CORE)
        self.assertEqual(doc["version"], testlib.load_json(
            os.path.join(testlib.PLUGIN, ".claude-plugin", "plugin.json"))["version"])
        self.assertEqual(len(doc["content_sha256"]), 64)


class CheckInput(_Cli):

    def test_every_valid_example(self):
        for path in sorted(glob.glob(os.path.join(testlib.EX, "input", "valid", "*.json"))):
            testlib.rmtree(os.path.join(self.tmp, "run"))
            doc = self.localize(testlib.load_json(path))
            target = os.path.join(self.tmp, "input.json")
            testlib.write_json(target, doc)
            code, out, err = self.cli(["check-input", target])
            self.assertEqual(code, 0, "%s: %s%s" % (os.path.basename(path), out, err))
            self.assertEqual(self.json_out(out)["next"], "select")

    def test_every_invalid_example(self):
        for path in sorted(glob.glob(os.path.join(testlib.EX, "input", "invalid", "*.json"))):
            doc = self.localize(testlib.load_json(path))
            target = os.path.join(self.tmp, "input.json")
            testlib.write_json(target, doc)
            code, out, err = self.cli(["check-input", target])
            self.assertEqual(code, 4, "%s: %s%s" % (os.path.basename(path), out, err))
            self.assertFalse(os.path.exists(os.path.join(self.tmp, "run")), path)

    def test_the_path_rules(self):
        inside = os.path.join(self.ws, "run")
        for doc in (testlib.make_input(self.ws, inside),
                    testlib.make_input(self.ws, os.path.join(self.staging, "run"), staging=self.staging),
                    testlib.make_input(os.path.join(self.tmp, "missing"), self.run_dir)):
            path = os.path.join(self.tmp, "input.json")
            testlib.write_json(path, doc)
            code, out, err = self.cli(["check-input", path])
            self.assertEqual(code, 4, out + err)

    def test_a_run_directory_already_used(self):
        self.checked()
        path = os.path.join(self.tmp, "input.json")
        code, out, err = self.cli(["check-input", path])
        self.assertEqual(code, 2, out + err)

    def test_a_file_that_is_not_there_or_not_json(self):
        self.assertEqual(self.cli(["check-input", os.path.join(self.tmp, "none.json")])[0], 2)
        bad = os.path.join(self.tmp, "bad.json")
        testlib.write_text(bad, "not json")
        self.assertEqual(self.cli(["check-input", bad])[0], 2)


class Select(_Cli):

    def test_every_hunt_on_an_empty_and_a_one_candidate_fixture(self):
        hunts = station_module().HUNTS
        self.assertTrue(hunts)
        for name, homes in sorted(hunts.items()):
            testlib.rmtree(self.run_dir)
            self.checked()
            code, out, err = self.cli(["select", "--run-dir", self.run_dir, "--hunt", name,
                                       "--name", "widget"])
            self.assertEqual(code, 0, err)
            doc = self.json_out(out)
            self.assertEqual(doc["outcome"], "none", name)
            self.assertEqual(len(doc["searched"]), len(homes))
            first = sorted(homes, key=lambda h: h["tier"])[0]
            root = {"workspace": self.ws, "staging": self.staging}[first["root"]]
            rel = first["globs"][0].replace("{name}", "widget").replace("*", "2026-09-20")
            testlib.write_text(os.path.join(root, rel), "# a doc\n")
            code, out, err = self.cli(["select", "--run-dir", self.run_dir, "--hunt", name,
                                       "--name", "widget"])
            doc = self.json_out(out)
            self.assertEqual((code, doc["outcome"]), (0, "one"), (name, doc))
            self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "selection-%s.json" % name)))
            os.remove(os.path.join(root, rel))

    def test_an_unknown_hunt_and_a_bad_name(self):
        self.checked()
        self.assertEqual(self.cli(["select", "--run-dir", self.run_dir, "--hunt", "nope"])[0], 2)
        hunt = sorted(station_module().HUNTS)[0]
        self.assertEqual(self.cli(["select", "--run-dir", self.run_dir, "--hunt", hunt,
                                   "--name", "../x"])[0], 2)

    def test_select_before_check_input(self):
        os.makedirs(self.run_dir)
        self.assertEqual(self.cli(["select", "--run-dir", self.run_dir])[0], 2)


class NotBuilt(_Cli):

    def test_the_four_lane_phases_stop_as_phase_not_built(self):
        self.checked()
        before = sorted(os.listdir(self.run_dir))
        answer = os.path.join(self.tmp, "answer.json")
        testlib.write_json(answer, {"questions": [], "lines": []})
        for args in (["harvest"], ["record-answer", "--answer", answer], ["write"], ["report"]):
            code, out, err = self.cli(args + ["--run-dir", self.run_dir])
            self.assertEqual(code, 10, args)
            doc = self.json_out(out)
            self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "phase-not-built"), args)
            self.assertIn(args[0], doc["reason"])
        self.assertEqual(sorted(os.listdir(self.run_dir)), before, "nothing written")


class Validators(_Cli):

    def test_validate_examples_is_green(self):
        code, out, err = testlib.run_script("validate-examples.py", [], cwd=self.cwd)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(json.loads(out)["ok"])

    def test_validate_result_both_ways(self):
        for path in sorted(glob.glob(os.path.join(testlib.EX, "result", "valid", "*.json"))):
            code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.cwd)
            self.assertEqual(code, 0, "%s: %s%s" % (path, out, err))
        for path in sorted(glob.glob(os.path.join(testlib.EX, "result", "invalid", "*.json"))):
            code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.cwd)
            self.assertEqual(code, 4, "%s: %s%s" % (path, out, err))


if __name__ == "__main__":
    unittest.main()
