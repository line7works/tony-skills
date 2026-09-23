"""build-v2 on Claude Code: invocation.py (E13 slice 3, brief 3.1 and required test 1).

A7a: `--help`, JSON on stdout and nothing else, exit 2 on an unknown argument, exit 3 when the
harness record or the `claude` binary is absent, the same answer from another working directory,
and the printed `invocation` composed into a real input validates against the core's own
`references/input.schema.json` while a `measurement` key placed under `invocation` does not.
"""

import copy
import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "invocation.py"


def minimal_input(invocation):
    """The smallest accepted build-v2 input, around the helper's invocation object."""
    return {"input_version": 1, "run_id": "build-a-20260923-0001",
            "workspace": "/tmp/widget-workspace", "run_dir": "/tmp/build-v2/build-a-20260923-0001",
            "build_doc": "docs/plans/2026-09-18-widget.md", "slice": "A", "base": "base",
            "invocation": invocation}


class InterfaceTest(unittest.TestCase):
    def test_help_is_json_on_stdout(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        text = json.loads(out)["help"]
        self.assertIn("Side effects", text)
        self.assertIn("Exit", text)

    def test_an_unknown_argument_is_exit_2(self):
        code, out, err = testlib.run(HELPER, ["--no-such-flag"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.strip())

    def test_the_fixture_flags_are_refused_at_run_time(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args(),
                                     env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 2, err)
        self.assertIn("fixture interface", err)

    def test_no_session_variable_is_exit_3(self):
        code, out, err = testlib.run(HELPER, [], env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 3, err)
        self.assertIn("CLAUDE_CODE_SESSION_ID", json.loads(out)["error"])

    def test_an_absent_transcript_is_exit_3(self):
        home = tempfile.mkdtemp(prefix="fake-claude-home-")
        try:
            os.makedirs(os.path.join(home, "projects", "-tmp-somewhere"))
            code, out, err = testlib.run(HELPER, [], env={
                testlib.TEST_FLAG: None, "CLAUDE_CONFIG_DIR": home,
                "CLAUDE_CODE_SESSION_ID": "00000000-0000-0000-0000-000000000000"})
            self.assertEqual(code, 3, err)
            self.assertIn("no transcript", json.loads(out)["error"])
        finally:
            shutil.rmtree(home)

    def test_an_absent_binary_is_exit_3(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args(), with_claude=False)
        self.assertEqual(code, 3, err)
        self.assertIn("claude", json.loads(out)["error"])

    def test_the_same_answer_from_another_working_directory(self):
        elsewhere = tempfile.mkdtemp(prefix="elsewhere-")
        try:
            one = testlib.run_json(HELPER, testlib.fixture_args())
            two = testlib.run_json(HELPER, testlib.fixture_args(), cwd=elsewhere)
            self.assertEqual(one["invocation"], two["invocation"])
            self.assertEqual(one["answer_fields"], two["answer_fields"])
        finally:
            shutil.rmtree(elsewhere)


class FactsTest(unittest.TestCase):
    def test_a_direct_run(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args())
        self.assertEqual(doc["invocation"], {"harness": "claude-code", "caller": "user",
                                             "mode": "direct", "session_id": testlib.SESSION})
        self.assertEqual(doc["answer_fields"], {"session_id": testlib.SESSION})
        m = doc["measurement"]
        self.assertEqual(m["harness_version"], testlib.FAKE_VERSION)
        self.assertEqual(m["model_id"], "claude-opus-5")
        self.assertEqual(m["sandbox"], "acceptEdits")
        self.assertEqual(m["session_id"], testlib.SESSION)

    def test_a_station_route(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args() + ["--caller", "ship"])
        self.assertEqual(doc["invocation"], {"harness": "claude-code", "caller": "ship",
                                             "mode": "station", "session_id": testlib.SESSION})

    def test_a_caller_named_user_is_refused(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--caller", "user"])
        self.assertEqual(code, 2, err)

    def test_the_live_route_finds_the_session_by_its_own_id(self):
        home = tempfile.mkdtemp(prefix="fake-claude-home-")
        try:
            folder = os.path.join(home, "projects", "-tmp-widget-workspace")
            os.makedirs(folder)
            shutil.copyfile(testlib.TRANSCRIPT, os.path.join(folder, testlib.SESSION + ".jsonl"))
            code, out, err = testlib.run(HELPER, ["--workspace", "/tmp/widget-workspace"], env={
                testlib.TEST_FLAG: None, "CLAUDE_CONFIG_DIR": home,
                "CLAUDE_CODE_SESSION_ID": testlib.SESSION})
            self.assertEqual(code, 0, err)
            doc = json.loads(out)
            self.assertEqual(doc["answer_fields"]["session_id"], testlib.SESSION)
            self.assertIn("CLAUDE_CODE_SESSION_ID", doc["measurement"]["_sources"]["session"])
        finally:
            shutil.rmtree(home)

    def test_a_foreign_record_is_refused(self):
        work = tempfile.mkdtemp(prefix="foreign-")
        try:
            rows = testlib.records()
            for row in rows:
                if row.get("type") == "assistant":
                    row["sessionId"] = "11111111-2222-3333-4444-555555555555"
                    break
            path = testlib.write_records(work, rows)
            code, out, err = testlib.run(HELPER, ["--transcript", path,
                                                  "--session-id", testlib.SESSION])
            self.assertEqual(code, 3, err)
            self.assertIn("another session", json.loads(out)["error"])
        finally:
            shutil.rmtree(work)

    def test_another_workspace_is_refused(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args()
                                     + ["--workspace", "/tmp/another-workspace"])
        self.assertEqual(code, 3, err)


class SchemaCompositionTest(unittest.TestCase):
    """The helper's output composed into the core's input validates both ways."""

    def test_the_invocation_validates_and_a_measurement_key_does_not(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args())
        good = minimal_input(doc["invocation"])
        self.assertEqual(testlib.validate(good), [])
        bad = minimal_input(copy.deepcopy(doc["invocation"]))
        bad["invocation"]["measurement"] = doc["measurement"]
        errors = testlib.validate(bad)
        self.assertTrue(errors)
        self.assertTrue(any("measurement" in message for message in errors), errors)
        with open(testlib.SCHEMA, "r", encoding="utf-8") as handle:
            schema = json.load(handle)
        allowed = set(schema["properties"]["invocation"]["properties"])
        self.assertEqual(sorted(set(doc["invocation"]) - allowed), [])
        self.assertEqual(sorted(allowed - set(doc["invocation"])), [])


if __name__ == "__main__":
    unittest.main()
