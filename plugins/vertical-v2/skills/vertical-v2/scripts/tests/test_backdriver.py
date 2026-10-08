"""The back loop's driver (the E15 back frame; `back_core/backdriver.py`).

Each back core's `scripts/<station>.py` runs the station_core driver's seams (the run directory and
its checkpoint, the checked dispatch, `identity`, `skill-identity`) with its own phase table, in its
own order; a phase not built yet answers `phase-not-built` with exit 10, the E14 frame's way. Driven
through a probe phase table here, so the test holds in every back core, and through this core's own
driver for the commands every core shares.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

PROBE = """
import sys
sys.path.insert(0, sys.argv[1])
from back_core import backdriver
from station_core import driver

def built(ctx, args):
    run = ctx.open_run(args.run_dir)
    return driver.emit(ctx.envelope(next="second", run_id=run.checkpoint["run_id"], built=True))

PHASES = [
    {"name": "first", "help": "the first phase", "arguments": [], "handler": built},
    {"name": "second", "help": "the second phase", "arguments": [
        {"flags": ["--words"], "default": None, "help": "some words"}], "handler": None},
]
sys.exit(backdriver.main(sys.argv[2], PHASES, sys.argv[3:]))
"""


class _Probe(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("backdriver-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        os.makedirs(self.ws)
        self.run_dir = os.path.join(self.tmp, "run")

    def probe(self, args, env=None):
        proc = subprocess.run([sys.executable, "-c", PROBE, testlib.SCRIPTS, testlib.CORE] + args, cwd=self.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env or testlib.base_env())
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


class TheParser(_Probe):

    def test_help_lists_the_phases_in_order_and_the_exit_codes(self):
        code, out, err = self.probe(["--help"])
        self.assertEqual(code, 0, err)
        self.assertLess(out.index("first"), out.index("second"))
        for word in ("check-input", "identity", "skill-identity", "10", "phase-not-built"):
            self.assertIn(word, out)

    def test_no_command_is_usage(self):
        code, out, err = self.probe([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_a_phase_table_that_reuses_a_shared_name_is_a_defect(self):
        bad = PROBE.replace('"name": "first"', '"name": "identity"')
        proc = subprocess.run([sys.executable, "-c", bad, testlib.SCRIPTS, testlib.CORE, "--help"], cwd=self.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertNotEqual(proc.returncode, 0)


class TheRun(_Probe):

    def setUp(self):
        _Probe.setUp(self)
        testlib.add_scripts_to_path()
        from station_core import validate
        if validate.jsonschema_unavailable("BACKDRIVER_TEST"):
            self.skipTest("jsonschema is not importable here: check-input runs under uv run")
        self.input = os.path.join(self.tmp, "input.json")
        testlib.write_json(self.input, testlib.make_input(self.ws, self.run_dir))

    def test_check_input_names_the_first_phase_and_a_built_phase_runs(self):
        code, out, err = self.probe(["check-input", self.input])
        self.assertEqual(code, 0, out + err)
        doc = json.loads(out)
        self.assertEqual(doc["next"], "first")
        self.assertEqual(doc["station"], testlib.CORE)
        self.assertEqual(doc["interface_version"], 1)
        code, out, err = self.probe(["first", "--run-dir", self.run_dir])
        self.assertEqual(code, 0, out + err)
        self.assertTrue(json.loads(out)["built"])

    def test_a_phase_not_built_answers_phase_not_built(self):
        self.probe(["check-input", self.input])
        code, out, err = self.probe(["second", "--run-dir", self.run_dir, "--words", "x"])
        self.assertEqual(code, 10, out + err)
        doc = json.loads(out)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "phase-not-built"))
        self.assertEqual(os.listdir(self.ws), [])

    def test_a_used_run_directory_is_refused(self):
        self.probe(["check-input", self.input])
        code, out, err = self.probe(["check-input", self.input])
        self.assertEqual(code, 2, out + err)


class ThisCoresDriver(unittest.TestCase):

    def test_skill_identity_names_this_core(self):
        code, out, err = testlib.run_driver(["skill-identity"])
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["name"], testlib.CORE)
        self.assertEqual(doc["interface_version"], 1)
        self.assertEqual(len(doc["content_sha256"]), 64)

    def test_identity_reads_a_directory(self):
        tmp = testlib.make_scratch("identity-")
        self.addCleanup(testlib.rmtree, tmp)
        code, out, err = testlib.run_driver(["identity", tmp])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["kind"], "directory")

    def test_the_version_is_this_plugins(self):
        code, out, err = testlib.run_driver(["skill-identity"])
        manifest = testlib.load_json(os.path.join(testlib.PLUGIN, ".claude-plugin", "plugin.json"))
        self.assertEqual(json.loads(out)["version"], manifest["version"])
        self.assertEqual(json.loads(out)["plugin_version"], manifest["version"])


if __name__ == "__main__":
    unittest.main()
