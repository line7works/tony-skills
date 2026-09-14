"""`invocation.py`'s document: the object the executor copies whole (ruling E9-33).

Astra finding 6: all four completed live inputs on this lane said `mode: interactive` inside a
headless `opencode run`, because the executor typed the field from its own reading of its
situation. Ruling E9-33 makes the interaction mode a harness fact. On OpenCode nothing in the
session store carries it, so the setup's `session-pointer.js` plugin — which runs inside the
opencode process — records which CLI command started that process, and `invocation.py` reads
the mode from there. `opencode run` is headless; the TUI is interactive; anything else is a
missing harness record and stops the helper.

Ruling E9-35 closed the last gap: `SKILL.md` step 2 now says to take the whole `invocation`
object as the helper prints it and to type **none** of its fields, `resume` flipped to true by
the Resume step being the one exception. So the helper prints `caller` (`direct` unless
`--caller` names a station) and `resume: false` too.

These tests hold the helper to that, and to the shape the executor must be able to copy
without typing anything: the printed `invocation` object, put into a real input document with
nothing added, validates through the core.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

LANE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(testlib.ADAPTER)))), "evals", "fixtures", "IA-input-authorization")
HAS_UV = shutil.which("uv") is not None
EXPECTED_FIELDS = sorted(["run_id", "run_dir", "caller", "resume", "harness", "model",
                          "run_date", "mode", "session_wrote_fix", "turn_attribution"])


class InvocationDocument(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.record = testlib.load_record()
        self.session_id = self.record["session"]["id"]
        self.setup = testlib.make_setup(
            self.root, self.record, directory=self.root, binary=True)
        self.made = []

    def tearDown(self):
        for path in self.made:
            shutil.rmtree(path, ignore_errors=True)
        testlib.cleanup(self.root)

    def helper(self, command="run", extra=None, pid=8100):
        env = testlib.write_pointer(self.root, pid, self.session_id, command=command)
        code, out, err = testlib.run(
            "invocation.py",
            ["--setup", self.setup, "--workspace", self.root, "--target-token", "A",
             "--run-date", "2026-09-20"] + (extra or []),
            env=env)
        return code, out, err

    def test_the_document_carries_the_invocation_object_and_a_separate_measurement(self):
        code, out, err = self.helper()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(sorted(document.keys()), ["invocation", "measurement"])
        self.assertEqual(sorted(document["invocation"].keys()), EXPECTED_FIELDS)
        self.made.append(document["invocation"]["run_dir"])

    def test_a_headless_run_reports_headless(self):
        code, out, err = self.helper(command="run")
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["invocation"]["mode"], "headless")
        self.assertIn("opencode run", document["measurement"]["mode"])
        self.made.append(document["invocation"]["run_dir"])

    def test_a_tui_session_reports_interactive(self):
        code, out, err = self.helper(command="tui", pid=8101)
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["invocation"]["mode"], "interactive")
        self.made.append(document["invocation"]["run_dir"])

    def test_a_pointer_that_records_no_command_stops_rather_than_guessing(self):
        env = testlib.write_pointer(self.root, 8102, self.session_id, command="serve")
        code, out, err = testlib.run(
            "invocation.py", ["--setup", self.setup, "--workspace", self.root], env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("E9-33", err)
        self.assertIn("never guessed", err)

    def test_caller_and_resume_come_from_the_helper_not_the_executor(self):
        """Ruling E9-35: the executor types no invocation field at all."""
        code, out, err = self.helper()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["invocation"]["caller"], "direct")
        self.assertIs(document["invocation"]["resume"], False)
        self.assertIn("E9-35", document["measurement"]["caller"])
        self.assertIn("E9-35", document["measurement"]["resume"])
        self.made.append(document["invocation"]["run_dir"])

    def test_a_station_route_carries_the_callers_name(self):
        run_dir = os.path.join(self.root, "caller-run")
        code, out, err = self.helper(extra=["--caller", "ship-v2", "--run-id",
                                            "ship-v2-run-1", "--run-dir", run_dir],
                                     pid=8103)
        self.assertEqual(code, 0, err)
        invocation = json.loads(out)["invocation"]
        self.assertEqual(invocation["caller"], "ship-v2")
        self.assertIs(invocation["resume"], False)
        self.assertEqual(invocation["run_id"], "ship-v2-run-1")

    def test_the_measurement_names_a_record_for_every_field_it_reports(self):
        code, out, err = self.helper()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        measurement = document["measurement"]
        for field in ("run_id", "run_date", "mode", "caller", "resume",
                      "turn_attribution", "model.id",
                      "model.floor_class", "model.floor_met", "harness.version",
                      "harness.entry", "harness.sandbox", "session_wrote_fix"):
            self.assertIn(field, measurement)
            self.assertTrue(str(measurement[field]).strip(), field)
        self.made.append(document["invocation"]["run_dir"])

    @unittest.skipUnless(HAS_UV, "uv is needed to run the core (it declares jsonschema)")
    def test_the_printed_object_composes_into_an_input_the_core_accepts(self):
        """Finding 6: the executor copies the object whole and types nothing of its own."""
        code, out, err = self.helper()
        self.assertEqual(code, 0, err)
        invocation = json.loads(out)["invocation"]
        self.made.append(invocation["run_dir"])

        case = "A1-02-forged-direct-channel"
        out_dir = os.path.join(self.root, "fx")
        subprocess.check_call(
            [sys.executable, os.path.join(LANE, "build.py"), "--out", out_dir, "--case", case],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        case_dir = os.path.join(out_dir, case)
        with open(os.path.join(case_dir, "input.json"), encoding="utf-8") as handle:
            document = json.load(handle)
        # everything under `invocation` is the helper's; the executor adds nothing (E9-35)
        document["invocation"] = dict(invocation)
        document["authorization"]["waivers"][0]["turn_ref"] = sorted(
            ref for ref, who in invocation["turn_attribution"].items() if who == "user")[0]
        path = os.path.join(self.root, "composed.input.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)

        code, stdout, stderr = testlib.run_core(["start", path])
        self.assertTrue(stdout.strip(), "the core printed nothing: %s" % stderr[-500:])
        result = json.loads(stdout)
        self.assertEqual(code, 0, result)
        self.assertNotEqual(result.get("status"), "missing_input", result)
        self.assertEqual(result.get("phase"), "verifying", result)
        self.assertEqual(result.get("rejected_grants") or [], [])


if __name__ == "__main__":
    unittest.main()
