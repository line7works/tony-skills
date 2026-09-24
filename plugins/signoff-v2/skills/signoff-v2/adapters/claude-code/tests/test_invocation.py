"""signoff-v2 on Claude Code: invocation.py (E13 slice 3; brief 3.1, required tests 1 and 2).

A7a interface; `sessions.reviewing` read from the harness's own record; `sessions.building` null
when unknown; the v1 floor map for every id class including the null case; the helper's output
composed into the core's input validates both ways; and the independence refusal reached THROUGH
the core with an adapter-built invocation whose building session is the reviewing one.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

import corelib
import testlib

HELPER = "invocation.py"


def minimal_input(invocation):
    return {"protocol_version": 1, "invocation": invocation,
            "workspace": "/tmp/widget-workspace",
            "target": {"build_doc": "docs/plans/2026-09-18-widget.md", "slice": "A",
                       "base": "base"}}


class InterfaceTest(unittest.TestCase):
    def test_help_is_json_on_stdout(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])

    def test_an_unknown_argument_is_exit_2(self):
        code, out, err = testlib.run(HELPER, ["--no-such-flag"])
        self.assertEqual((code, out), (2, ""))

    def test_no_session_variable_is_exit_3(self):
        code, out, err = testlib.run(HELPER, [], env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 3, err)

    def test_an_absent_binary_is_exit_3(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args(), with_claude=False)
        self.assertEqual(code, 3, err)

    def test_the_same_answer_from_another_working_directory(self):
        elsewhere = tempfile.mkdtemp(prefix="elsewhere-")
        try:
            args = testlib.fixture_args() + ["--caller", "ship", "--run-id", "signoff-a-1",
                                             "--run-dir", "/tmp/signoff-v2/signoff-a-1",
                                             "--run-date", "2026-09-23"]
            one = testlib.run_json(HELPER, args)
            two = testlib.run_json(HELPER, args, cwd=elsewhere)
            self.assertEqual(one["invocation"], two["invocation"])
        finally:
            shutil.rmtree(elsewhere)

    def test_caller_ids_travel_together(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--caller", "ship"])
        self.assertEqual(code, 2, err)


class SessionsTest(unittest.TestCase):
    def test_reviewing_is_the_records_own_session_and_building_is_null(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args())
        sessions = doc["invocation"]["sessions"]
        self.assertEqual(sessions, {"building": None, "reviewing": testlib.SESSION})
        self.assertIn("transcript", doc["measurement"]["_sources"]["sessions.reviewing"])

    def test_building_from_a_bound_build_result(self):
        """The one route (Astra's F4; the typed override is gone, test_full_fix_f4.py)."""
        from test_full_fix_f4 import build_result, session_record_at
        work = tempfile.mkdtemp(prefix="build-result-")
        try:
            workspace = os.path.join(work, "workspace")
            os.makedirs(workspace)
            path = build_result(os.path.join(work, "run"), workspace, "build-session-9",
                                "docs/plans/2026-09-18-widget.md", "A")
            args = session_record_at(work, workspace) + [
                "--build-result", path, "--workspace", workspace,
                "--build-doc", "docs/plans/2026-09-18-widget.md", "--slice", "A"]
            doc = testlib.run_json(HELPER, args)
            self.assertEqual(doc["invocation"]["sessions"]["building"], "build-session-9")
            with open(path) as handle:
                body = json.load(handle)
            body["invocation"].pop("session_id")      # send-back 1: no recorded harness session
            with open(path, "w") as handle:
                json.dump(body, handle)
            code, out, err = testlib.run(HELPER, args)
            self.assertEqual(code, 3, out)                # Astra's N1: refused, not null
            self.assertNotIn("invocation", json.loads(out))
            self.assertIn("no reviewing invocation was emitted", json.loads(out)["error"])
        finally:
            shutil.rmtree(work)


class FloorTest(unittest.TestCase):
    CASES = (("claude-opus-5", "opus", True), ("claude-opus-5[1m]", "opus", True),
             ("claude-fable-5-1", "opus", True), ("claude-mythos-1", "opus", True),
             ("claude-sonnet-4-5", "sonnet", False), ("claude-haiku-4-5", "haiku", False),
             ("gpt-6-astra", "unknown", None), ("", "unknown", None), (None, "unknown", None))

    def test_every_class(self):
        sys.path.insert(0, testlib.ADAPTER)
        try:
            import _common
            for model_id, klass, met in self.CASES:
                self.assertEqual(_common.floor_for(model_id, "opus"), (klass, met), model_id)
        finally:
            sys.path.remove(testlib.ADAPTER)

    def test_the_helper_reports_the_record_model(self):
        model = testlib.run_json(HELPER, testlib.fixture_args())["invocation"]["model"]
        self.assertEqual(model, {"id": "claude-opus-5", "floor_class": "opus", "floor_met": True})

    def test_a_synthetic_error_record_is_never_the_model(self):
        work = tempfile.mkdtemp(prefix="synthetic-")
        try:
            rows = testlib.records()
            last = [r for r in rows if r.get("type") == "assistant"][-1]
            extra = copy.deepcopy(last)
            extra["uuid"] = "99999999-0000-0000-0000-000000000001"
            extra["message"]["model"] = "<synthetic>"
            extra["isApiErrorMessage"] = True
            rows.append(extra)
            path = testlib.write_records(work, rows)
            model = testlib.run_json(HELPER, ["--transcript", path])["invocation"]["model"]
            self.assertEqual(model["id"], "claude-opus-5")
        finally:
            shutil.rmtree(work)

    def test_no_model_record_is_floor_null(self):
        work = tempfile.mkdtemp(prefix="nomodel-")
        try:
            rows = [r for r in testlib.records() if r.get("type") != "assistant"]
            path = testlib.write_records(work, rows)
            model = testlib.run_json(HELPER, ["--transcript", path])["invocation"]["model"]
            self.assertEqual(model, {"id": "unknown", "floor_class": "unknown", "floor_met": None})
        finally:
            shutil.rmtree(work)


class RunIdsTest(unittest.TestCase):
    def test_a_minted_run_is_outside_the_workspace_and_single_use(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args() + ["--target-token", "Slice F",
                                                                 "--run-date", "2026-09-23"])
        inv = doc["invocation"]
        self.assertRegex(inv["run_id"], r"^signoff-slice-f-20260923-[0-9a-f]{4}$")
        self.assertTrue(inv["run_dir"].endswith("/signoff-v2/" + inv["run_id"]))
        self.assertEqual(inv["run_date"], "2026-09-23")
        self.assertEqual((inv["caller"], inv["mode"]), ("direct", "headless"))

    def test_a_caller_route_keeps_its_ids_and_is_headless(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args() + [
            "--caller", "ship", "--run-id", "ship-1", "--run-dir", "/tmp/elsewhere/ship-1"],
            env={"CLAUDE_CODE_SESSION_ATTENDED": "1"})
        inv = doc["invocation"]
        self.assertEqual((inv["caller"], inv["run_id"], inv["run_dir"], inv["mode"]),
                         ("ship", "ship-1", "/tmp/elsewhere/ship-1", "headless"))

    def test_a_bad_date_is_exit_2(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--run-date", "2026-02-30"])
        self.assertEqual(code, 2, err)


class SchemaCompositionTest(unittest.TestCase):
    def test_the_invocation_validates_and_a_measurement_key_does_not(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args())
        self.assertEqual(testlib.validate(minimal_input(doc["invocation"])), [])
        bad = minimal_input(copy.deepcopy(doc["invocation"]))
        bad["invocation"]["measurement"] = doc["measurement"]
        errors = testlib.validate(bad)
        self.assertTrue(any("measurement" in message for message in errors), errors)
        with open(testlib.SCHEMA) as handle:
            allowed = set(json.load(handle)["properties"]["invocation"]["properties"])
        self.assertEqual(set(doc["invocation"]), allowed)


class IndependenceThroughTheCoreTest(unittest.TestCase):
    """The building session reaches the core only from a bound build result (Astra's F4); the
    probe shape itself is `test_full_fix_f4.TheProbeThroughTheCore`."""

    def test_building_equal_to_reviewing_is_refused_by_the_core(self):
        from test_full_fix_f4 import TheProbeThroughTheCore
        TheProbeThroughTheCore.test_a_build_from_this_session_is_refused_on_independence(self)


if __name__ == "__main__":
    unittest.main()
