"""build-v2 on Codex: invocation.py (E13 slice 3, brief 3.1 and required test 1)."""

import copy
import json
import os
import shutil
import stat
import tempfile
import unittest

import testlib

HELPER = "invocation.py"


def minimal_input(invocation):
    return {"input_version": 1, "run_id": "build-a-20260923-0001",
            "workspace": "/tmp/neutral-workspace", "run_dir": "/tmp/build-v2/build-a-20260923-0001",
            "build_doc": "docs/plans/2026-09-18-widget.md", "slice": "A", "base": "base",
            "invocation": invocation}


class InterfaceTest(unittest.TestCase):
    def test_help_is_json_on_stdout(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])

    def test_an_unknown_argument_is_exit_2(self):
        code, out, err = testlib.run(HELPER, ["--no-such-flag"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.strip())

    def test_outside_an_install_without_the_fixture_is_exit_3(self):
        code, out, err = testlib.run(HELPER, [], env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 3, err)
        self.assertIn("E9-40", json.loads(out)["error"])

    def test_an_absent_fixture_record_is_exit_3(self):
        code, out, err = testlib.run(HELPER, [], env={testlib.RECORD_VAR: "/nonexistent/r.jsonl"})
        self.assertEqual(code, 3, err)
        self.assertIn("absent harness record", json.loads(out)["error"])

    def test_an_absent_binary_is_exit_3(self):
        code, out, err = testlib.run(HELPER, [], with_codex=False)
        self.assertEqual(code, 3, err)
        self.assertIn("codex", json.loads(out)["error"])

    def test_the_same_answer_from_another_working_directory(self):
        elsewhere = tempfile.mkdtemp(prefix="elsewhere-")
        try:
            one = testlib.run_json(HELPER, [])
            two = testlib.run_json(HELPER, [], cwd=elsewhere)
            self.assertEqual(one["invocation"], two["invocation"])
            self.assertEqual(one["answer_fields"], two["answer_fields"])
        finally:
            shutil.rmtree(elsewhere)


class FactsTest(unittest.TestCase):
    def test_a_direct_run(self):
        doc = testlib.run_json(HELPER, ["--workspace", testlib.WORKSPACE])
        self.assertEqual(doc["invocation"], {"harness": "codex-cli", "caller": "user",
                                             "mode": "direct", "session_id": testlib.THREAD})
        self.assertEqual(doc["answer_fields"], {"session_id": testlib.THREAD})
        m = doc["measurement"]
        self.assertEqual(m["harness_version"], testlib.FAKE_VERSION)
        self.assertEqual(m["harness_version_in_record"], "0.154.0")
        self.assertEqual(m["model_id"], "gpt-6-astra")
        self.assertEqual(m["interaction_mode"], "headless")

    def test_a_station_route(self):
        doc = testlib.run_json(HELPER, ["--caller", "ship"])
        self.assertEqual(doc["invocation"], {"harness": "codex-cli", "caller": "ship",
                                             "mode": "station", "session_id": testlib.THREAD})

    def test_another_workspace_is_refused(self):
        code, out, err = testlib.run(HELPER, ["--workspace", "/tmp/another-workspace"])
        self.assertEqual(code, 3, err)


class InstalledLocatorTest(unittest.TestCase):
    """E9-40, E9-36 and E9-37 on a copy of this adapter in a fake installed home."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="installed-")
        self.home, self.adapter = testlib.installed_copy(self.work)
        self.child = os.path.join(self.home, "child")
        os.makedirs(self.child)

    def tearDown(self):
        for root, dirs, files in os.walk(self.work):
            for name in files:
                os.chmod(os.path.join(root, name), stat.S_IRUSR | stat.S_IWUSR)
        shutil.rmtree(self.work, ignore_errors=True)

    def call(self, extra=None):
        env = {testlib.TEST_FLAG: None, testlib.RECORD_VAR: None,
               "CODEX_THREAD_ID": testlib.THREAD, "CODEX_HOME": self.child}
        env.update(extra or {})
        return testlib.run(HELPER, [], env=env, adapter=self.adapter)

    def test_a_read_only_rollout_under_the_installed_home_is_found(self):
        testlib.plant_rollout(self.home)
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["answer_fields"]["session_id"], testlib.THREAD)
        self.assertEqual(doc["measurement"]["entry"], "plugin")

    def test_a_writable_rollout_is_refused_without_the_wall(self):
        testlib.plant_rollout(self.home, read_only=False)
        code, out, err = self.call()
        self.assertEqual(code, 3, err)
        self.assertIn("E9-37", json.loads(out)["error"])

    def test_no_thread_variable_is_exit_3(self):
        testlib.plant_rollout(self.home)
        code, out, err = self.call({"CODEX_THREAD_ID": None})
        self.assertEqual(code, 3, err)

    def test_the_installed_helper_ignores_the_fixture_variables(self):
        code, out, err = self.call({testlib.TEST_FLAG: "1", testlib.RECORD_VAR: testlib.ROLLOUT})
        self.assertEqual(code, 3, err)
        self.assertIn("no rollout named", json.loads(out)["error"])

    def test_a_home_that_is_codex_home_is_refused(self):
        testlib.plant_rollout(self.home)
        code, out, err = self.call({"CODEX_HOME": self.home})
        self.assertEqual(code, 3, err)
        self.assertIn("E9-36", json.loads(out)["error"])


class SchemaCompositionTest(unittest.TestCase):
    def test_the_invocation_validates_and_a_measurement_key_does_not(self):
        doc = testlib.run_json(HELPER, [])
        self.assertEqual(testlib.validate(minimal_input(doc["invocation"])), [])
        bad = minimal_input(copy.deepcopy(doc["invocation"]))
        bad["invocation"]["measurement"] = doc["measurement"]
        errors = testlib.validate(bad)
        self.assertTrue(any("measurement" in message for message in errors), errors)


if __name__ == "__main__":
    unittest.main()
