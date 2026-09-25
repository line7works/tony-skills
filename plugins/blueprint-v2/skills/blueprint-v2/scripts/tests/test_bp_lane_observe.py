"""The lane's facts for its seeded families (lane L, reading CR-7, required test 9).

`evals/seeded-cases/lane_observe.py` (lane-owned) fills every name the L1 to L3 `lane` steps list,
from a real drive of this core's phases, and `observe.py` leaves no `_lane_pending` and no
`_errors` for those cases. This suite states no outcome: it holds only that each fact exists, came
from a drive (`_via` names it), and has the vocabulary's type.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

import bplib
import testlib

sys.dont_write_bytecode = True

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
LANE_CASES = {"L1-03-criterion-without-verify": {"answer_refused": bool, "refusal_reason": str},
              "L2-02-inspected-and-filled": {"extended_in_place": bool, "protected_lines_identical": bool,
                                             "importer_reads": bool}}


@unittest.skipIf(testlib.checkout_sibling("readers") is None or testlib.records_root() is None,
                 "no readers or records beside this core (the installed shape): observe.py and the "
                 "importer fact need them, and this is reported as skipped")
class LaneFacts(unittest.TestCase):

    def test_every_pending_name_is_filled_from_a_drive(self):
        tmp = testlib.make_scratch("bp-observe-")
        self.addCleanup(testlib.rmtree, tmp)
        args = [sys.executable, OBSERVE, "--out", tmp]
        for case in sorted(LANE_CASES):
            args += ["--case", case]
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-2000:] + proc.stderr.decode()[-2000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        self.assertEqual(sorted(r["case"] for r in rows), sorted(LANE_CASES))
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            self.assertNotIn("_lane_pending", observed, row["case"])
            for name, kind in LANE_CASES[row["case"]].items():
                self.assertIsInstance(observed[name], kind, (row["case"], name))
                self.assertTrue(observed["_via"].get(name), (row["case"], name))

    def test_the_observer_writes_nothing_into_the_worktree(self):
        before = testlib.tree_digest(SEEDED)
        tmp = testlib.make_scratch("bp-observe-")
        self.addCleanup(testlib.rmtree, tmp)
        subprocess.run([sys.executable, OBSERVE, "--out", tmp, "--case", "L2-02-inspected-and-filled"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(before, testlib.tree_digest(SEEDED))


class TheProtectedFactIsMeasured(unittest.TestCase):
    """R6 (CL1-8): `protected_lines_identical` is read from the doc's bytes in every branch, a write
    that did not write included; never set from an exit code."""

    def load(self):
        spec = importlib.util.spec_from_file_location("bp_lane_observe_under_test",
                                                      os.path.join(SEEDED, "lane_observe.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def observe_with_a_write_that(self, changes_the_doc):
        module = self.load()
        tmp = testlib.make_scratch("bp-observe-bytes-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = testlib.git_workspace(tmp, "ws", bplib.base_files(build=bplib.BUILD_FILLED))
        real = module.Drive.cli

        def cli(drive, args):
            if args[0] != "write":
                return real(drive, args)
            if changes_the_doc:
                doc = os.path.join(drive.workspace, bplib.BUILD_PATH)
                testlib.write_text(doc, bplib.read(doc).replace("Status: in progress", "Status: not started"))
            drive.phases.append({"phase": "write", "exit": 10})
            return 10, {"status": "stopped", "stop_tag": "write-refused"}

        module.Drive.cli = cli
        facts, via = {"_phases": [], "_errors": []}, {}
        module.observe_lane({"kind": "lane", "pending": ["protected_lines_identical"]}, tmp,
                            {"case": "probe-case", "workspace": ws}, facts, via, os.path.join(tmp, "scratch"))
        return facts, via

    def test_a_write_that_stopped_and_left_the_doc_changed_is_measured_false(self):
        facts, via = self.observe_with_a_write_that(changes_the_doc=True)
        self.assertIs(facts["protected_lines_identical"], False)
        self.assertIn("bytes", via["protected_lines_identical"])

    def test_a_write_that_stopped_and_left_the_doc_as_found_is_measured_true(self):
        facts, via = self.observe_with_a_write_that(changes_the_doc=False)
        self.assertIs(facts["protected_lines_identical"], True)
        self.assertIn("bytes", via["protected_lines_identical"])


if __name__ == "__main__":
    unittest.main()
