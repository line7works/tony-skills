"""invocation.py: the floor map of ruling E9-3, the ids and the run date, the
values it refuses to guess, and the projection the input schema allows."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import testlib

SCHEMA = os.path.join(testlib.SKILL_ROOT, "references", "input.schema.json")
FIXTURE_ARGS = ["--transcript", testlib.TRANSCRIPT]


def helper(args=(), env=None):
    """(invocation, measurement) from one helper run over the fixture record."""
    document = testlib.run_json("invocation.py", FIXTURE_ARGS + list(args), env=env)
    return document["invocation"], document["measurement"]


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
        sys.path.insert(0, testlib.ADAPTER)
        import _common

        for model_id, klass, met in self.CASES:
            got_class, got_met = _common.floor_for(model_id, "opus")
            self.assertEqual(got_class, klass, model_id)
            self.assertEqual(got_met, met, model_id)

    def test_the_helper_reports_the_transcript_model(self):
        invocation, measurement = helper(["--run-date", "2026-09-20"])
        self.assertEqual(invocation["model"]["id"], "claude-opus-5")
        self.assertEqual(invocation["model"]["floor_class"], "opus")
        self.assertTrue(invocation["model"]["floor_met"])
        self.assertIn("message.model", measurement["_sources"]["model_id"])

    def test_a_higher_floor_than_the_class_is_not_met(self):
        sys.path.insert(0, testlib.ADAPTER)
        import _common

        self.assertEqual(_common.floor_for("claude-sonnet-4-5", "sonnet"), ("sonnet", True))
        self.assertEqual(_common.floor_for("claude-haiku-4-5", "sonnet"), ("haiku", False))
        self.assertEqual(_common.floor_for("claude-opus-5", "nonsense"), ("opus", None))


class SchemaProjectionTest(unittest.TestCase):
    """Astra's finding 13: the executor copies `invocation` whole, so every key
    in it must be one `references/input.schema.json` allows (the object is
    closed with additionalProperties: false)."""

    def setUp(self):
        with open(SCHEMA, "r", encoding="utf-8") as handle:
            self.schema = json.load(handle)
        self.allowed = set(self.schema["properties"]["invocation"]["properties"])

    def test_the_invocation_object_carries_only_schema_keys(self):
        invocation, measurement = helper()
        self.assertEqual(
            self.schema["properties"]["invocation"]["additionalProperties"], False
        )
        self.assertEqual(sorted(set(invocation) - self.allowed), [])
        self.assertIn("mode_hint", measurement)
        self.assertNotIn("mode_hint", invocation)
        self.assertNotIn("_sources", invocation)

    def test_the_invocation_object_is_complete_for_the_executor(self):
        """Ruling E9-33: the executor types no invocation field, so every field
        the schema requires is in the helper's object."""
        invocation, _ = helper()
        for name in self.schema["properties"]["invocation"]["required"]:
            self.assertIn(name, invocation)
        self.assertIn(invocation["mode"], ("interactive", "headless"))
        self.assertEqual(invocation["caller"], "direct")
        self.assertFalse(invocation["resume"])

    def test_the_composed_input_validates_and_the_measurement_keys_do_not(self):
        """Compose the helper's output into a fresh input exactly as the
        profile tells the executor to (copy the object whole, type nothing) and
        validate it against the real schema with the core's own pinned
        jsonschema."""
        invocation, measurement = helper(["--run-date", "2026-09-20"])
        composed = dict(invocation)
        document = {
            "protocol_version": 1,
            "invocation": composed,
            "workspace": "/tmp/widget-workspace",
            "target": {"build_doc": "docs/plans/plan.md", "slice": "A"},
        }
        self.assertEqual(self.validate(document), [], "the composed input must validate")

        literal = dict(document)
        literal["invocation"] = dict(composed)
        literal["invocation"]["mode_hint"] = measurement["mode_hint"]
        literal["invocation"]["_sources"] = measurement["_sources"]
        errors = self.validate(literal)
        self.assertTrue(errors, "a literal copy of the whole helper output must be refused")
        self.assertTrue(
            any("mode_hint" in error or "_sources" in error for error in errors), errors
        )

    def validate(self, document):
        directory = tempfile.mkdtemp(prefix="recheck-adapter-schema-")
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, "input.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        script = os.path.join(directory, "check.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(
                "# /// script\n"
                '# requires-python = ">=3.9"\n'
                '# dependencies = ["jsonschema==4.25.1"]\n'
                "# ///\n"
                "import json, sys\n"
                "import jsonschema\n"
                "schema = json.load(open(sys.argv[1]))\n"
                "document = json.load(open(sys.argv[2]))\n"
                "validator = jsonschema.Draft202012Validator(schema)\n"
                "errors = [\n"
                "    '/'.join(str(part) for part in error.absolute_path) + ': ' + error.message\n"
                "    for error in validator.iter_errors(document)\n"
                "]\n"
                "print(json.dumps(errors))\n"
            )
        process = subprocess.Popen(
            ["uv", "run", script, SCHEMA, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.join(os.sep, "tmp"),
        )
        out, err = process.communicate()
        if process.returncode != 0:
            raise AssertionError("schema check failed: %s" % err.decode("utf-8"))
        return json.loads(out.decode("utf-8"))


class IdsTest(unittest.TestCase):
    def test_the_run_id_and_directory_shape(self):
        invocation, _ = helper(["--target-token", "A", "--run-date", "2026-09-20"])
        self.assertTrue(
            re.match(r"^recheck-a-20260920-[0-9a-f]{4}$", invocation["run_id"]),
            invocation["run_id"],
        )
        self.assertTrue(invocation["run_dir"].startswith(os.sep))
        self.assertTrue(invocation["run_dir"].endswith(invocation["run_id"]))
        self.assertIn("recheck-v2", invocation["run_dir"])

    def test_the_run_id_is_fresh_every_call(self):
        first, _ = helper(["--run-date", "2026-09-20"])
        second, _ = helper(["--run-date", "2026-09-20"])
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_the_run_directory_is_named_not_created(self):
        invocation, _ = helper(["--run-date", "2026-09-20"])
        self.assertFalse(os.path.exists(invocation["run_dir"]))

    def test_a_caller_keeps_its_ids(self):
        invocation, measurement = helper(
            [
                "--caller", "ship-v2",
                "--run-id", "ship-a-20260920-1b2e-recheck",
                "--run-dir", "/tmp/ship-a-20260920-1b2e/recheck",
            ]
        )
        self.assertEqual(invocation["run_id"], "ship-a-20260920-1b2e-recheck")
        self.assertEqual(invocation["run_dir"], "/tmp/ship-a-20260920-1b2e/recheck")
        self.assertEqual(measurement["_sources"]["ids"], "the caller's, unchanged")

    def test_a_target_token_is_slugged(self):
        invocation, _ = helper(["--target-token", "Slice B / two"])
        self.assertIn("recheck-slice-b-two-", invocation["run_id"])


class HonestValuesTest(unittest.TestCase):
    def test_session_wrote_fix_defaults_false_and_is_never_guessed(self):
        invocation, measurement = helper()
        self.assertFalse(invocation["session_wrote_fix"])
        self.assertIn("never guessed", measurement["_sources"]["session_wrote_fix"])
        invocation, _ = helper(["--session-wrote-fix"])
        self.assertTrue(invocation["session_wrote_fix"])

    def test_the_run_date_source_is_named(self):
        invocation, measurement = helper(["--run-date", "2026-09-20"])
        self.assertEqual(invocation["run_date"], "2026-09-20")
        self.assertEqual(measurement["_sources"]["run_date"], "--run-date")
        invocation, measurement = helper()
        self.assertRegex(invocation["run_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("local calendar date", measurement["_sources"]["run_date"])

    def test_the_sandbox_comes_from_the_sessions_own_record(self):
        """Astra's finding 7: the transcript's user records carry
        `permissionMode`, so the permission mode is a harness record after all."""
        invocation, measurement = helper(
            env={"RECHECK_HARNESS_SANDBOX": None, "CLAUDE_CODE_PERMISSION_MODE": None}
        )
        self.assertEqual(invocation["harness"]["sandbox"], "acceptEdits")
        self.assertIn("permissionMode record", measurement["_sources"]["sandbox"])

    def test_a_launcher_that_disagrees_with_the_record_is_reported(self):
        invocation, measurement = helper(env={"RECHECK_HARNESS_SANDBOX": "bypass"})
        self.assertEqual(invocation["harness"]["sandbox"], "acceptEdits")
        self.assertIn("the record wins", measurement["_sources"]["sandbox"])

    def test_the_sandbox_reads_unknown_without_any_record(self):
        directory = tempfile.mkdtemp(prefix="recheck-adapter-nomode-")
        self.addCleanup(shutil.rmtree, directory, True)
        rows = testlib.records()
        for row in rows:
            row.pop("permissionMode", None)
        path = testlib.write_transcript(directory, rows, "no-mode.jsonl")
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", path],
            env={"RECHECK_HARNESS_SANDBOX": None, "CLAUDE_CODE_PERMISSION_MODE": None},
        )
        self.assertTrue(document["invocation"]["harness"]["sandbox"].startswith("unknown"))

    def test_the_launcher_record_supplies_the_sandbox_when_the_record_has_none(self):
        directory = tempfile.mkdtemp(prefix="recheck-adapter-nomode2-")
        self.addCleanup(shutil.rmtree, directory, True)
        rows = testlib.records()
        for row in rows:
            row.pop("permissionMode", None)
        path = testlib.write_transcript(directory, rows, "no-mode.jsonl")
        document = testlib.run_json(
            "invocation.py",
            ["--transcript", path],
            env={"RECHECK_HARNESS_SANDBOX": "acceptEdits"},
        )
        self.assertEqual(document["invocation"]["harness"]["sandbox"], "acceptEdits")
        self.assertIn(
            "RECHECK_HARNESS_SANDBOX", document["measurement"]["_sources"]["sandbox"]
        )

    def test_the_harness_version_comes_from_the_command(self):
        invocation, measurement = helper()
        self.assertEqual(invocation["harness"]["name"], "claude-code")
        self.assertRegex(invocation["harness"]["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(measurement["_sources"]["version"], "claude --version")
        self.assertEqual(
            measurement["_sources"]["version_records_in_transcript"], ["2.1.270"]
        )

    def test_the_mode_is_a_harness_fact_inside_the_invocation(self):
        """Ruling E9-33: the helper supplies `mode`, the executor never types
        it. All three of the lane's live inputs said `interactive` inside
        `claude -p` when the executor typed it (Astra's finding 14)."""
        invocation, measurement = helper(env={"CLAUDE_CODE_SESSION_ATTENDED": "0"})
        self.assertEqual(invocation["mode"], "headless")
        self.assertEqual(measurement["mode_hint"], "headless")
        self.assertIn("CLAUDE_CODE_SESSION_ATTENDED=0", measurement["_sources"]["mode"])
        # the fixture's own records say entrypoint sdk-cli, so an interactive
        # environment over a headless record is a disagreement, and a fact that
        # cannot be read is exit 3, never a guess
        code, out, err = testlib.run(
            "invocation.py", FIXTURE_ARGS, env={"CLAUDE_CODE_SESSION_ATTENDED": "1"}
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("they disagree", err)
        self.assertIn("E9-33", err)
        invocation, _ = helper(
            env={"CLAUDE_CODE_SESSION_ATTENDED": None, "CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}
        )
        self.assertEqual(invocation["mode"], "headless")
        invocation, measurement = helper(
            env={"CLAUDE_CODE_SESSION_ATTENDED": None, "CLAUDE_CODE_ENTRYPOINT": None}
        )
        self.assertEqual(invocation["mode"], "headless")
        self.assertIn("entrypoint record", measurement["_sources"]["mode"])

    def test_a_station_route_is_always_headless(self):
        invocation, measurement = helper(
            [
                "--caller", "ship-v2",
                "--run-id", "ship-a-20260920-1b2e-recheck",
                "--run-dir", "/tmp/ship-a-20260920-1b2e/recheck",
            ],
            env={"CLAUDE_CODE_SESSION_ATTENDED": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"},
        )
        self.assertEqual(invocation["caller"], "ship-v2")
        self.assertEqual(invocation["mode"], "headless")
        self.assertIn("caller route fixes mode headless", measurement["_sources"]["mode"])

    def test_no_mode_record_at_all_exits_3(self):
        directory = tempfile.mkdtemp(prefix="recheck-adapter-noentry-")
        self.addCleanup(shutil.rmtree, directory, True)
        rows = testlib.records()
        for row in rows:
            row.pop("entrypoint", None)
        path = testlib.write_transcript(directory, rows, "no-entrypoint.jsonl")
        code, out, err = testlib.run(
            "invocation.py",
            ["--transcript", path],
            env={"CLAUDE_CODE_SESSION_ATTENDED": None, "CLAUDE_CODE_ENTRYPOINT": None},
        )
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("no record of it is reachable", err)

    def test_the_turn_map_travels_with_the_invocation(self):
        invocation, _ = helper()
        self.assertEqual(
            sorted(set(invocation["turn_attribution"].values())), ["assistant", "user"]
        )
        self.assertEqual(len(invocation["turn_attribution"]), 6)


if __name__ == "__main__":
    unittest.main()
