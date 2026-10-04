"""The Codex adapter writes no memory pointer (A2 Q3, ruling E15-12): on Codex the block in the build doc is the
pointer, and the result says no memory pointer was written. This adapter carries no pointer helper, and its
profile says so in the sections that name the seam.
"""
import os
import unittest

import testlib


class NoPointerOnCodex(unittest.TestCase):

    def test_the_adapter_carries_no_pointer_helper(self):
        names = sorted(n for n in os.listdir(testlib.ADAPTER) if n.endswith(".py"))
        self.assertEqual(names, ["_common.py", "invocation.py"])

    def test_the_profile_names_the_seam_and_its_result(self):
        with open(os.path.join(testlib.ADAPTER, "profile.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("no memory pointer", text)
        self.assertIn("the block in the build doc is the pointer", text)
        self.assertIn("E15-12", text)


if __name__ == "__main__":
    unittest.main()
