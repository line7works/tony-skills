"""The lane's facts for its seeded families (lane L, reading CR-7, required test 9).

`evals/seeded-cases/lane_observe.py` (lane-owned) fills every name the L1 to L3 `lane` steps list,
from a real drive of this core's phases, and `observe.py` leaves no `_lane_pending` and no
`_errors` for those cases. This suite states no outcome: it holds only that each fact exists, came
from a drive (`_via` names it), and has the vocabulary's type.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

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


if __name__ == "__main__":
    unittest.main()
