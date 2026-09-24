"""signoff-v2 on Codex: invocation.py (E13 slice 3; brief 3.1, required tests 1 and 2)."""

import copy
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

import corelib
import testlib

HELPER = "invocation.py"


def minimal_input(invocation):
    return {"protocol_version": 1, "invocation": invocation, "workspace": testlib.WORKSPACE,
            "target": {"build_doc": "docs/plans/2026-09-18-widget.md", "slice": "A",
                       "base": "base"}}


class InterfaceTest(unittest.TestCase):
    def test_help_is_json_on_stdout(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])

    def test_an_unknown_argument_is_exit_2(self):
        self.assertEqual(testlib.run(HELPER, ["--no-such-flag"])[:2], (2, ""))

    def test_outside_an_install_without_the_fixture_is_exit_3(self):
        code, out, err = testlib.run(HELPER, [], env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 3, err)

    def test_an_absent_binary_is_exit_3(self):
        self.assertEqual(testlib.run(HELPER, [], with_codex=False)[0], 3)

    def test_the_same_answer_from_another_working_directory(self):
        elsewhere = tempfile.mkdtemp(prefix="elsewhere-")
        try:
            args = ["--caller", "ship", "--run-id", "s-1", "--run-dir", "/tmp/sv2/s-1",
                    "--run-date", "2026-09-23"]
            self.assertEqual(testlib.run_json(HELPER, args)["invocation"],
                             testlib.run_json(HELPER, args, cwd=elsewhere)["invocation"])
        finally:
            shutil.rmtree(elsewhere)


class SessionsAndModeTest(unittest.TestCase):
    def test_reviewing_is_the_rollouts_own_thread_and_building_is_null(self):
        inv = testlib.run_json(HELPER, [])["invocation"]
        self.assertEqual(inv["sessions"], {"building": None, "reviewing": testlib.THREAD})
        self.assertEqual((inv["mode"], inv["caller"], inv["harness"]),
                         ("headless", "direct", "codex-cli"))

    def test_building_from_a_bound_build_result(self):
        """The one route (Astra's F4; the typed override is gone, test_full_fix_f4.py)."""
        from test_full_fix_f4 import build_result, rollout_at
        work = tempfile.mkdtemp(prefix="result-")
        try:
            workspace = os.path.join(work, "workspace")
            os.makedirs(workspace)
            path = build_result(os.path.join(work, "run"), workspace, "t-9",
                                "docs/plans/2026-09-18-widget.md", "A")
            self.assertEqual(testlib.run_json(HELPER, [
                "--build-result", path, "--workspace", workspace,
                "--build-doc", "docs/plans/2026-09-18-widget.md", "--slice", "A"],
                env=rollout_at(work, workspace))["invocation"]["sessions"]["building"], "t-9")
        finally:
            shutil.rmtree(work)

    def test_an_unknown_originator_is_exit_3(self):
        work = tempfile.mkdtemp(prefix="originator-")
        try:
            rows = testlib.records()
            rows[0]["payload"]["originator"] = "somewhere_else"
            path = testlib.write_records(work, rows)
            code, out, err = testlib.run(HELPER, [], env={testlib.RECORD_VAR: path})
            self.assertEqual(code, 3, err)
            self.assertIn("originator", json.loads(out)["error"])
        finally:
            shutil.rmtree(work)


class FloorTest(unittest.TestCase):
    CASES = (("gpt-6-astra", "opus", True), ("gpt-5.6-sol", "opus", True),
             ("gpt-5", "unknown", None), ("o3", "unknown", None))

    def test_every_class_including_the_null_case(self):
        sys.path.insert(0, testlib.ADAPTER)
        try:
            import _common
            for model_id, klass, met in self.CASES:
                model, _extra = _common.model_facts({"model": model_id})
                self.assertEqual((model["floor_class"], model["floor_met"]), (klass, met))
            with self.assertRaises(_common.Missing):
                _common.model_facts({})
        finally:
            sys.path.remove(testlib.ADAPTER)

    def test_the_helper_reports_the_record_model(self):
        self.assertEqual(testlib.run_json(HELPER, [])["invocation"]["model"],
                         {"id": "gpt-6-astra", "floor_class": "opus", "floor_met": True})


class SchemaCompositionTest(unittest.TestCase):
    def test_the_invocation_validates_and_a_measurement_key_does_not(self):
        doc = testlib.run_json(HELPER, [])
        self.assertEqual(testlib.validate(minimal_input(doc["invocation"])), [])
        bad = minimal_input(copy.deepcopy(doc["invocation"]))
        bad["invocation"]["measurement"] = doc["measurement"]
        self.assertTrue(any("measurement" in m for m in testlib.validate(bad)))


class InstalledLocatorTest(unittest.TestCase):
    def test_the_installed_helper_reads_its_own_home(self):
        work = tempfile.mkdtemp(prefix="installed-")
        try:
            home, adapter = testlib.installed_copy(work)
            os.makedirs(os.path.join(home, "child"))
            testlib.plant_rollout(home)
            code, out, err = testlib.run(HELPER, [], adapter=adapter, env={
                testlib.TEST_FLAG: None, testlib.RECORD_VAR: None,
                "CODEX_THREAD_ID": testlib.THREAD, "CODEX_HOME": os.path.join(home, "child")})
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["invocation"]["sessions"]["reviewing"],
                             testlib.THREAD)
        finally:
            for root, _d, files in os.walk(work):
                for name in files:
                    os.chmod(os.path.join(root, name), stat.S_IRUSR | stat.S_IWUSR)
            shutil.rmtree(work, ignore_errors=True)


class IndependenceThroughTheCoreTest(unittest.TestCase):
    """The building session reaches the core only from a bound build result (Astra's F4); the
    probe shape itself is `test_full_fix_f4.TheProbeThroughTheCore`."""

    def test_building_equal_to_reviewing_is_refused_by_the_core(self):
        from test_full_fix_f4 import TheProbeThroughTheCore
        TheProbeThroughTheCore.test_a_build_from_this_session_is_refused_on_independence(self)


if __name__ == "__main__":
    unittest.main()
