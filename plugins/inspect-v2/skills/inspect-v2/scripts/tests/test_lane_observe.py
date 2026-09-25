"""The lane facts of families I1 to I4 (required test 9; brief CR-7).

`evals/seeded-cases/lane_observe.py` fills every name each `lane` step lists under `pending`, from
a real drive of this core (the CLI, or the library `request` calls, named in `_via`), never from
what the case expects: `observe.py` run on every case of this core's families leaves no
`_lane_pending` and no `_errors`, and every lane fact carries its `_via`. Facts only: this test
asserts no outcome of any case (the outcomes are in an answer key no builder reads).
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
FAMILIES = ("I1-primary-evidence", "I2-the-no-record-rule", "I3-records-and-the-stamp", "I4-no-v1-import")


@unittest.skipIf(testlib.checkout_sibling("readers") is None or testlib.records_root() is None or
                 testlib.checkout_sibling("blueprint-v2") is None,
                 "the installed shape: the lane drive needs records, readers and blueprint-v2 beside this core")
class TheLaneFacts(unittest.TestCase):

    def test_every_pending_name_is_filled_by_a_real_drive(self):
        self.assertTrue(os.path.isfile(os.path.join(SEEDED, "lane_observe.py")))
        tmp = testlib.make_scratch("lane-observe-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, OBSERVE, "--all", "--out", tmp], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-3000:] + proc.stderr.decode()[-3000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        seen = set()
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            if observed["_family"] not in FAMILIES:
                continue
            seen.add(observed["_family"])
            self.assertNotIn("_lane_pending", observed, row["case"])
            drive = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "drive.json"))
            for step in drive["steps"]:
                if step["kind"] != "lane":
                    continue
                for name in step.get("pending", []):
                    self.assertIn(name, observed, (row["case"], name))
                    self.assertIn(name, observed["_via"], (row["case"], name))
                    self.assertTrue(observed["_via"][name].startswith(("cli", "library")), observed["_via"][name])
                    # CI1-12: `_via` names the phases the drive reached, and none it never ran
                    ran = [p["phase"] for p in observed["_phases"] if p.get("phase")]
                    how = observed["_via"][name]
                    named = how.split("cli: ", 1)[1].split(" (", 1)[0] if how.startswith("cli: ") else \
                        how.split(" after ", 1)[1].split(" through", 1)[0]
                    named = [p.strip() for p in named.split(",")]
                    windows = [ran[i:i + len(named)] for i in range(len(ran) - len(named) + 1)]
                    self.assertIn(named, windows, (row["case"], name, how, ran))
        self.assertEqual(seen, set(FAMILIES) - {"I4-no-v1-import"} | ({"I4-no-v1-import"} & seen))


if __name__ == "__main__":
    unittest.main()
