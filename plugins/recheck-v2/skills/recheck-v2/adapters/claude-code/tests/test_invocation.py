"""invocation.py: the floor map of ruling E9-3, the ids and the run date, and
the values it refuses to guess."""

import os
import re
import unittest

import testlib


class FloorMapTest(unittest.TestCase):
    """Every class of ruling E9-3 for this lane, the null case included."""

    CASES = (
        ("claude-opus-5", "opus", True),
        ("claude-opus-5[1m]", "opus", True),
        ("claude-fable-5-1", "opus", True),
        ("claude-mythos-1", "opus", True),
        ("claude-sonnet-4-5", "sonnet", False),
        ("claude-haiku-4-5-20251001", "haiku", False),
        ("gpt-6-astra", "unknown", None),
        ("", "unknown", None),
    )

    def test_every_class(self):
        import sys

        sys.path.insert(0, testlib.ADAPTER)
        import _common

        for model_id, klass, met in self.CASES:
            got_class, got_met = _common.floor_for(model_id, "opus")
            self.assertEqual(got_class, klass, model_id)
            self.assertEqual(got_met, met, model_id)

    def test_the_helper_reports_the_transcript_model(self):
        document = testlib.run_json(
            "invocation.py", ["--transcript", testlib.TRANSCRIPT, "--run-date", "2026-09-20"]
        )
        self.assertEqual(document["model"]["id"], "claude-opus-5")
        self.assertEqual(document["model"]["floor_class"], "opus")
        self.assertTrue(document["model"]["floor_met"])
        self.assertIn("message.model", document["_sources"]["model_id"])

    def test_a_higher_floor_than_the_class_is_not_met(self):
        import sys

        sys.path.insert(0, testlib.ADAPTER)
        import _common

        self.assertEqual(_common.floor_for("claude-sonnet-4-5", "sonnet"), ("sonnet", True))
        self.assertEqual(_common.floor_for("claude-haiku-4-5", "sonnet"), ("haiku", False))
        self.assertEqual(_common.floor_for("claude-opus-5", "nonsense"), ("opus", None))


class IdsTest(unittest.TestCase):
    def test_the_run_id_and_directory_shape(self):
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT, "--target-token", "A", "--run-date", "2026-09-20"],
        )
        self.assertTrue(
            re.match(r"^recheck-a-20260920-[0-9a-f]{4}$", document["run_id"]), document["run_id"]
        )
        self.assertTrue(document["run_dir"].startswith(os.sep))
        self.assertTrue(document["run_dir"].endswith(document["run_id"]))
        self.assertIn("recheck-v2", document["run_dir"])

    def test_the_run_id_is_fresh_every_call(self):
        first = testlib.run_json(
            "invocation.py", ["--transcript", testlib.TRANSCRIPT, "--run-date", "2026-09-20"]
        )
        second = testlib.run_json(
            "invocation.py", ["--transcript", testlib.TRANSCRIPT, "--run-date", "2026-09-20"]
        )
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_the_run_directory_is_named_not_created(self):
        document = testlib.run_json(
            "invocation.py", ["--transcript", testlib.TRANSCRIPT, "--run-date", "2026-09-20"]
        )
        self.assertFalse(os.path.exists(document["run_dir"]))

    def test_a_caller_keeps_its_ids(self):
        document = testlib.run_json(
            "invocation.py",
            [
                "--transcript", testlib.TRANSCRIPT,
                "--caller", "ship-v2",
                "--run-id", "ship-a-20260920-1b2e-recheck",
                "--run-dir", "/tmp/ship-a-20260920-1b2e/recheck",
            ],
        )
        self.assertEqual(document["run_id"], "ship-a-20260920-1b2e-recheck")
        self.assertEqual(document["run_dir"], "/tmp/ship-a-20260920-1b2e/recheck")
        self.assertEqual(document["_sources"]["ids"], "the caller's, unchanged")

    def test_a_target_token_is_slugged(self):
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT, "--target-token", "Slice B / two"],
        )
        self.assertIn("recheck-slice-b-two-", document["run_id"])


class HonestValuesTest(unittest.TestCase):
    def test_session_wrote_fix_defaults_false_and_is_never_guessed(self):
        document = testlib.run_json("invocation.py", ["--transcript", testlib.TRANSCRIPT])
        self.assertFalse(document["session_wrote_fix"])
        self.assertIn("never guessed", document["_sources"]["session_wrote_fix"])
        document = testlib.run_json(
            "invocation.py", ["--transcript", testlib.TRANSCRIPT, "--session-wrote-fix"]
        )
        self.assertTrue(document["session_wrote_fix"])

    def test_the_run_date_source_is_named(self):
        document = testlib.run_json(
            "invocation.py", ["--transcript", testlib.TRANSCRIPT, "--run-date", "2026-09-20"]
        )
        self.assertEqual(document["run_date"], "2026-09-20")
        self.assertEqual(document["_sources"]["run_date"], "--run-date")
        document = testlib.run_json("invocation.py", ["--transcript", testlib.TRANSCRIPT])
        self.assertRegex(document["run_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("local calendar date", document["_sources"]["run_date"])

    def test_the_sandbox_reads_unknown_without_a_record(self):
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"RECHECK_HARNESS_SANDBOX": None, "CLAUDE_CODE_PERMISSION_MODE": None},
        )
        self.assertTrue(document["harness"]["sandbox"].startswith("unknown"))

    def test_the_launcher_record_supplies_the_sandbox(self):
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"RECHECK_HARNESS_SANDBOX": "acceptEdits"},
        )
        self.assertEqual(document["harness"]["sandbox"], "acceptEdits")
        self.assertEqual(document["_sources"]["sandbox"], "RECHECK_HARNESS_SANDBOX")

    def test_the_harness_version_comes_from_the_command(self):
        document = testlib.run_json("invocation.py", ["--transcript", testlib.TRANSCRIPT])
        self.assertEqual(document["harness"]["name"], "claude-code")
        self.assertRegex(document["harness"]["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(document["_sources"]["version"], "claude --version")

    def test_the_mode_hint_is_a_fact_from_the_environment(self):
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"CLAUDE_CODE_SESSION_ATTENDED": "0"},
        )
        self.assertEqual(document["mode_hint"], "headless")
        self.assertEqual(document["_sources"]["mode_hint"], "CLAUDE_CODE_SESSION_ATTENDED=0")
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"CLAUDE_CODE_SESSION_ATTENDED": "1"},
        )
        self.assertEqual(document["mode_hint"], "interactive")
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"CLAUDE_CODE_SESSION_ATTENDED": None, "CLAUDE_CODE_ENTRYPOINT": "sdk-cli"},
        )
        self.assertEqual(document["mode_hint"], "headless")
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", testlib.TRANSCRIPT],
            env={"CLAUDE_CODE_SESSION_ATTENDED": None, "CLAUDE_CODE_ENTRYPOINT": None},
        )
        self.assertEqual(document["mode_hint"], "unknown")

    def test_the_turn_map_travels_with_the_invocation(self):
        document = testlib.run_json("invocation.py", ["--transcript", testlib.TRANSCRIPT])
        self.assertEqual(
            sorted(set(document["turn_attribution"].values())), ["assistant", "user"]
        )
        self.assertEqual(len(document["turn_attribution"]), 5)


if __name__ == "__main__":
    unittest.main()
