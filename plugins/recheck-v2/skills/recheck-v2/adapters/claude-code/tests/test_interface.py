"""A7a: every helper's --help, stdout, exit codes, and behaviour with the
record absent, run from another working directory."""

import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPERS = ("invocation.py", "turns.py", "verifier.py")


class HelpTest(unittest.TestCase):
    def test_help_names_arguments_defaults_example_and_side_effects(self):
        for helper in HELPERS:
            code, out, err = testlib.run(helper, ["--help"])
            self.assertEqual(code, 0, helper)
            self.assertEqual(err, "", helper)
            lowered = out.lower()
            self.assertIn("usage:", lowered, helper)
            self.assertIn("default", lowered, helper)
            self.assertIn("example", lowered, helper)
            self.assertIn("side effects", lowered, helper)


class StdoutTest(unittest.TestCase):
    def test_stdout_is_one_json_document_and_nothing_else(self):
        code, out, _err = testlib.run(
            "turns.py", ["--transcript", testlib.TRANSCRIPT]
        )
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["harness"], "claude-code")
        self.assertEqual(out.count("\n"), out.rstrip("\n").count("\n") + 1)

    def test_diagnostics_go_to_stderr(self):
        code, out, err = testlib.run("turns.py", ["--transcript", "/nope/missing.jsonl"])
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("transcript not found", err)


class UsageTest(unittest.TestCase):
    def test_unknown_argument_exits_2(self):
        for helper in HELPERS:
            code, out, err = testlib.run(helper, ["--not-a-flag"])
            self.assertEqual(code, 2, helper)
            self.assertEqual(out, "", helper)
            self.assertTrue(err.strip(), helper)

    def test_caller_ids_are_all_or_nothing(self):
        code, out, err = testlib.run("invocation.py", ["--caller", "ship-v2"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("passed together", err)

    def test_bad_run_date_exits_2(self):
        code, _out, err = testlib.run("invocation.py", ["--run-date", "20260920"])
        self.assertEqual(code, 2)
        self.assertIn("YYYY-MM-DD", err)

    def test_verifier_request_mode_needs_its_paths(self):
        code, out, err = testlib.run("verifier.py", ["--brief", testlib.TRANSCRIPT])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--workspace", err)


class MissingRecordTest(unittest.TestCase):
    """Exit 3 with the harness record or binary absent, under a fake home."""

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="recheck-adapter-home-")
        os.makedirs(os.path.join(self.home, "projects"))
        self.addCleanup(shutil.rmtree, self.home, True)

    def test_turns_without_any_record(self):
        code, out, err = testlib.run(
            "turns.py", [], env={"CLAUDE_CONFIG_DIR": self.home, "TMPDIR": self.home}
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("CLAUDE_CODE_SESSION_ID is not set", err)

    def test_turns_with_a_session_id_that_has_no_transcript(self):
        code, _out, err = testlib.run(
            "turns.py",
            [],
            env={
                "CLAUDE_CONFIG_DIR": self.home,
                "TMPDIR": self.home,
                "CLAUDE_CODE_SESSION_ID": "0000-not-a-session",
            },
        )
        self.assertEqual(code, 3)
        self.assertIn("no transcript named 0000-not-a-session.jsonl", err)

    def test_invocation_without_any_record(self):
        code, out, err = testlib.run(
            "invocation.py", [], env={"CLAUDE_CONFIG_DIR": self.home, "TMPDIR": self.home}
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("CLAUDE_CODE_SESSION_ID is not set", err)

    def test_every_helper_refuses_the_fixture_flags_at_run_time(self):
        """Ruling E9-28: `--transcript` and `--session-id` exist for the tests
        and are a usage error without RECHECK_ADAPTER_TEST=1."""
        calls = (
            ("turns.py", ["--transcript", testlib.TRANSCRIPT]),
            ("invocation.py", ["--transcript", testlib.TRANSCRIPT]),
            (
                "verifier.py",
                [
                    "--brief", os.path.join(self.home, "checklist.md"),
                    "--workspace", self.home,
                    "--scratch", os.path.join(self.home, "verifier"),
                    "--raw", os.path.join(self.home, "verifier", "raw.md"),
                    "--call-id", "r-verify",
                    "--transcript", testlib.TRANSCRIPT,
                ],
            ),
        )
        for helper, args in calls:
            code, out, err = testlib.run(
                helper,
                args,
                env={"RECHECK_ADAPTER_TEST": None, "CLAUDE_CONFIG_DIR": self.home},
            )
            self.assertEqual(code, 2, helper)
            self.assertEqual(out, "", helper)
            self.assertIn("fixture interface", err, helper)

    def test_invocation_without_the_claude_binary(self):
        empty = tempfile.mkdtemp(prefix="recheck-adapter-path-")
        self.addCleanup(shutil.rmtree, empty, True)
        code, out, err = testlib.run(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"PATH": empty, "CLAUDE_CONFIG_DIR": self.home},
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("claude binary is not on PATH", err)

    def test_verifier_without_a_brief(self):
        code, out, err = testlib.run(
            "verifier.py",
            [
                "--brief", os.path.join(self.home, "checklist.md"),
                "--workspace", self.home,
                "--scratch", os.path.join(self.home, "verifier"),
                "--raw", os.path.join(self.home, "verifier", "raw.md"),
                "--call-id", "r-verify",
            ],
            env={"CLAUDE_CONFIG_DIR": self.home},
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("the brief is not a file", err)

    def test_verifier_without_a_sidecar(self):
        code, out, err = testlib.run(
            "verifier.py", ["--sidecar", os.path.join(self.home, "sidecar.json")]
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("sidecar not found", err)


class AnotherWorkingDirectoryTest(unittest.TestCase):
    def test_helpers_answer_the_same_from_two_directories(self):
        first = testlib.run_json("turns.py", ["--transcript", testlib.TRANSCRIPT], cwd="/tmp")
        second = testlib.run_json(
            "turns.py", ["--transcript", testlib.TRANSCRIPT], cwd=testlib.FIXTURES
        )
        self.assertEqual(first["turn_attribution"], second["turn_attribution"])

    def test_a_relative_transcript_resolves_from_the_working_directory(self):
        document = testlib.run_json(
            "turns.py", ["--transcript", "session-transcript.jsonl"], cwd=testlib.FIXTURES
        )
        self.assertEqual(document["counts"]["user_turns"], 2)


if __name__ == "__main__":
    unittest.main()
