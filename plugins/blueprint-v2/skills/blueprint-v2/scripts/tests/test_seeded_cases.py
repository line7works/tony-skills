"""This core's seeded cases build and observe (E14 slice 1, 3.7).

What the suite holds is only what every case guarantees, never an outcome (the outcomes are in an
answer key no builder reads): every family builds every case it lists, twice to the same tree
hash; `observe.py` runs every case with no step error, emits `writes_none`, and lists the lane's
pending facts for every `lane` step; no shipped case file names an expected value.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
GEN = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable


def families():
    return sorted(n for n in os.listdir(SEEDED) if n[:1].isupper() and os.path.isdir(os.path.join(SEEDED, n)))


class TheFamilies(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("seeded-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def build(self, family, out):
        proc = subprocess.run([GEN, os.path.join(SEEDED, family, "build.py"), "--out", out, "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return dict((row["case"], row["tree_sha256"]) for row in json.loads(proc.stdout.decode())["cases"])

    def test_every_family_builds_deterministically_with_a_clean_case(self):
        names = families()
        self.assertTrue(names)
        for family in names:
            one = self.build(family, os.path.join(self.tmp, "a", family))
            two = self.build(family, os.path.join(self.tmp, "b", family))
            self.assertEqual(one, two, family)
            self.assertGreaterEqual(len(one), 3, family)
            self.assertTrue(any(case.endswith("-01-clean") for case in one), family)
            with open(os.path.join(SEEDED, family, "CASES.md"), encoding="utf-8") as fh:
                text = fh.read()
            for case in one:
                self.assertIn("## %s" % case, text)

    def test_no_case_file_states_an_outcome(self):
        for family in families():
            for base, dirs, files in os.walk(os.path.join(SEEDED, family)):
                for name in files:
                    with open(os.path.join(base, name), encoding="utf-8") as fh:
                        text = fh.read()
                    for word in ('"assert"', "expected_", "Pass:", "must be refused", "should pass"):
                        self.assertNotIn(word, text, os.path.join(base, name))


@unittest.skipIf(testlib.checkout_sibling("readers") is None,
                 "no readers component beside this core (the installed shape): observe.py reads its roster")
class TheObserver(unittest.TestCase):

    def test_every_case_observes_with_no_step_error(self):
        tmp = testlib.make_scratch("observe-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, OBSERVE, "--all", "--out", tmp], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-2000:] + proc.stderr.decode()[-2000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        self.assertTrue(rows)
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            self.assertIn("writes_none", observed, row["case"])
            drive = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "drive.json"))
            if any(step["kind"] == "lane" for step in drive["steps"]):
                self.assertTrue(observed.get("_lane_pending"), row["case"])


if __name__ == "__main__":
    unittest.main()
