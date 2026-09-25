"""The lane's observer (CR-7, required test 9).

`evals/seeded-cases/lane_observe.py` fills every name the families' `lane` steps list, from a
real drive (A2: the library functions `record-answer` calls; A4: the CLI itself, `check-input` to
`report`, on a copy of the case, each phase with its exit under `_phases`), with no
`_lane_pending` and no `_errors` left in any `observed.json`. The test reads facts only; what a fact should be is the
answer key's, never this suite's.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")


@unittest.skipIf(testlib.checkout_sibling("readers") is None,
                 "no readers component beside this core (the installed shape): observe.py reads its roster")
class LaneObserve(unittest.TestCase):

    def test_every_pending_name_is_filled(self):
        self.assertTrue(os.path.isfile(os.path.join(SEEDED, "lane_observe.py")))
        tmp = testlib.make_scratch("lane-observe-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, OBSERVE, "--all", "--out", tmp], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-2000:] + proc.stderr.decode()[-2000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        lane_steps = 0
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            self.assertNotIn("_lane_pending", observed, row["case"])
            drive = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "drive.json"))
            for step in drive["steps"]:
                if step["kind"] != "lane":
                    continue
                lane_steps += 1
                for name in step["pending"]:
                    self.assertIn(name, observed, (row["case"], name))
                    self.assertIn(name, observed["_via"], (row["case"], name))
        self.assertGreater(lane_steps, 0)
        a4 = [r for r in rows if r["case"].startswith("A4-")]
        self.assertEqual(len(a4), 3)
        for row in a4:
            observed = testlib.load_json(row["observed"])
            phases = [p["phase"] for p in observed["_phases"]]
            self.assertEqual(phases, ["check-input", "select", "select", "harvest", "record-answer", "write",
                                      "render-visual", "record-publish", "report"], row["case"])
            self.assertEqual(observed["_phases"][-1]["exit"], 10, row["case"])
            self.assertIn("cli", observed["_via"]["terminal_status"], row["case"])


if __name__ == "__main__":
    unittest.main()
