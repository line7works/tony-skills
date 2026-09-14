"""scripts/validate-examples.py: passes from another directory, prints every count, exits 3 without jsonschema."""
import os
import re
import unittest

import testlib

COUNTS = re.compile(r"positive: (\d+) files, (\d+) failing; negative: (\d+)/(\d+) rejected; positive mutations: (\d+)/(\d+) accepted; "
                    r"checkpoint checks: (\d+)/(\d+); receipt checks: (\d+)/(\d+)")
# the cases the suite defines after the fix round that followed slice 1's check; a suite that
# lost cases would still report counts equal to totals, so the floor catches that
NEGATIVE_FLOOR = 124
POSITIVE_FLOOR = 24
# the case names the fix round added: finding 1 (E8-2), finding 4 (E8-A2), finding 5 (receipt plan steps)
NEW_NEGATIVE_CASES = (
    "stopped submodule result carrying source_identity (E8-2)",
    "run.model with floor_met as a string (E8-A2)",
    "receipt: a plan target with a .. segment",
    "receipt: a cancelled flag on a punch-list step",
    "receipt: a value on a punch-list step",
    "receipt: content on a status-line step",
)
NEW_POSITIVE_CASES = (
    "a stopped submodule result without source_identity (E8-2)",
    "run.model carrying floor_met true (E8-A2)",
    "a receipt plan target whose segment merely starts with two dots",
    "a receipt status-line step carrying cancelled false beside its value",
    "a receipt reopened-line step carrying content",
)


class ValidateExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e8-slice1-examples-")

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def test_passes_from_another_directory(self):
        code, out, err = testlib.run_script("validate-examples.py", [], cwd=self.dir)
        self.assertEqual(code, 0, err + out[-2000:])
        last = out.strip().splitlines()[-1]
        m = COUNTS.match(last)
        self.assertTrue(m, last)
        files, failing, rej, rej_n, acc, acc_n, cp, cp_n, rc, rc_n = (int(x) for x in m.groups())
        self.assertEqual(failing, 0)
        self.assertEqual(rej, rej_n); self.assertEqual(acc, acc_n); self.assertEqual(cp, cp_n); self.assertEqual(rc, rc_n)
        self.assertGreaterEqual(rej_n, NEGATIVE_FLOOR, "the negative suite lost cases")
        self.assertGreaterEqual(acc_n, POSITIVE_FLOOR, "the positive mutations lost cases")
        self.assertEqual(files, len([f for f in os.listdir(testlib.EX) if f.endswith(".json")]))
        self.assertNotIn("(BUG)", out); self.assertNotIn("FAIL ", out)
        for needle in ("receipt-partial.json", "checkpoint-partial.json", "E8-15", "harness given as a string",
                       "model without floor_met", "turn_attribution", "refused_actions", "raw_sha256", "every new invocation field"):
            self.assertIn(needle, out, needle)
        lines = out.splitlines()
        for name in NEW_NEGATIVE_CASES:
            self.assertIn("REJECTED " + name, lines, name)
        for name in NEW_POSITIVE_CASES:
            self.assertIn("ACCEPTED " + name, lines, name)

    def test_exit_3_without_jsonschema(self):
        env = dict(os.environ, PYTHONPATH=testlib.stub_without_jsonschema(self.dir))
        code, out, err = testlib.run_script("validate-examples.py", [], cwd=self.dir, env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_old_location_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(testlib.EX, "validate-examples.py")))
        self.assertTrue(os.path.exists(os.path.join(testlib.SCRIPTS, "validate-examples.py")))


if __name__ == "__main__":
    unittest.main()
