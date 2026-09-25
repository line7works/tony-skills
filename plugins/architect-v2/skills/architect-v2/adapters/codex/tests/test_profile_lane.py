"""The profile's lane sections, held to what they claim (E14 slice 2, lane A; not a shared file).

The profile keeps the E9 seam's twelve sections in order and no section is left for a lane; the
run date section's claim holds (the core reads the local date, and its test hook pins it only under
`ARCHITECT_V2_TEST=1`); the delivery section's measured `SKILL.md` size is the file's size.
"""
import datetime
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True
TESTS = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.dirname(TESTS)
SKILL = os.path.dirname(os.path.dirname(ADAPTER))
PROFILE = os.path.join(ADAPTER, "profile.md")
TITLES = ["Identity", "Model and floor", "Run id and directory", "The user channel", "`session_wrote_fix`",
          "Run date", "The verifier capability", "Delivery", "Sidecars and invocation restrictions",
          "Negative tests", "Installed-package verification", "Capability labels"]


def findings(text):
    out = []
    headings = re.findall(r"(?m)^## (\d+)\. (.+)$", text)
    if [(int(n), t) for n, t in headings] != list(enumerate(TITLES, 1)):
        out.append("the twelve sections are not in the seam's order: %s" % headings)
    if "fills this" in text:
        out.append("a section is still left for a lane")
    return out


class TheProfile(unittest.TestCase):

    def test_twelve_sections_and_none_left_for_a_lane(self):
        with open(PROFILE, encoding="utf-8") as fh:
            self.assertEqual(findings(fh.read()), [])

    def test_the_measured_skill_size_is_the_files(self):
        with open(PROFILE, encoding="utf-8") as fh:
            text = fh.read()
        stated = re.search(r"`SKILL\.md` is ([\d,]+) bytes", text)
        self.assertIsNotNone(stated)
        self.assertEqual(int(stated.group(1).replace(",", "")), os.path.getsize(os.path.join(SKILL, "SKILL.md")))


class TheRunDate(unittest.TestCase):

    def setUp(self):
        scripts = os.path.join(SKILL, "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from architect_core import common
        self.common = common

    def test_the_local_date_outside_a_test(self):
        got = self.common.today({"ARCHITECT_V2_TEST_TODAY": "2001-01-01"})
        self.assertIn(got, (datetime.date.today().isoformat(),
                            (datetime.date.today() + datetime.timedelta(days=1)).isoformat()))

    def test_the_hook_pins_it_only_under_the_test_flag(self):
        self.assertEqual(self.common.today({"ARCHITECT_V2_TEST": "1", "ARCHITECT_V2_TEST_TODAY": "2001-01-01"}),
                         "2001-01-01")
        self.assertNotEqual(self.common.today({"ARCHITECT_V2_TEST": "1", "ARCHITECT_V2_TEST_TODAY": "not-a-date"}),
                            "not-a-date")


if __name__ == "__main__":
    unittest.main()
