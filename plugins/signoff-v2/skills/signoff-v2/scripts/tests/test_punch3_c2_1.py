"""punch3-C2-1: the installed package failed its own verification (E13 punch list round 3, from the
round 2 checker's report).

A sentence added to `references/signoff-contract.md` in round 2 held a back-ticked, path-shaped
example of a withheld citation broken at a line's end. `setups/verify-package.py` reads every
back-ticked path whose first segment is `.`, `..` or one of the skill's own folders as a runtime
reference that must resolve inside the installed package, so `verify-install.sh` exited 4 on both
harnesses. The red is that verify log (`punch3/red/C2-1.txt`); this module keeps the class closed
without an install: it runs the verifier's own reference check, unchanged, over this checkout's skill
folder (the documents an install copies and the check reads), and requires no finding.
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))
PLUGIN = os.path.dirname(os.path.dirname(SKILL))
VERIFIER = os.path.join(PLUGIN, "setups", "verify-package.py")


def _verifier():
    spec = importlib.util.spec_from_file_location("punch3_verify_package", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Punch3C21References(unittest.TestCase):

    def test_every_reference_the_verifier_checks_resolves(self):
        checked, findings, _ = _verifier().references(SKILL, PLUGIN)
        self.assertEqual(findings, [])
        self.assertTrue(checked, "the verifier found no reference to check")

    def test_the_contract_carries_no_path_shaped_line_break_example(self):
        with open(os.path.join(SKILL, "references", "signoff-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertFalse("`./builder`" in text, "a back-ticked `./builder` example is back")


if __name__ == "__main__":
    unittest.main()
