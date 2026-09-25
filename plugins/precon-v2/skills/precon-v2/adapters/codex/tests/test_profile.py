"""This harness's profile, read against the core (lane P, reading CR-14).

The twelve sections of the E9 seam, in order, and nothing left for a lane to fill; the station's
own values the profile states (the exit test's profile and mandate source, the date field, the
invocation facts it never types) are the ones the core's code and schemas carry.
"""
import json
import os
import re
import unittest

import testlib

PROFILE = os.path.join(testlib.ADAPTER, "profile.md")
SECTIONS = ("Identity", "Model and floor", "Run id and directory", "The user channel", "`session_wrote_fix`",
            "Run date", "The verifier capability", "Delivery", "Sidecars and invocation restrictions",
            "Negative tests", "Installed-package verification", "Capability labels")


def text():
    with open(PROFILE, encoding="utf-8") as fh:
        return fh.read()


class TheProfile(unittest.TestCase):

    def test_twelve_sections_in_order(self):
        found = re.findall(r"^## (\d+)\. (.+)$", text(), flags=re.M)
        self.assertEqual([int(n) for n, _ in found], list(range(1, 13)))
        self.assertEqual(tuple(title for _, title in found), SECTIONS)

    def test_nothing_left_for_the_lane(self):
        self.assertNotIn("lane P fills this", text())
        self.assertNotIn("(lane", text())

    def test_the_stated_values_are_the_cores(self):
        body = text()
        schema = json.load(open(testlib.SCHEMA, encoding="utf-8"))
        self.assertIn("date", schema["properties"]["station"]["properties"])
        self.assertIn("`station.date`", body)
        self.assertIn("`profile: starved`", body)
        self.assertIn("`owner_word`", body)
        contract = os.path.join(testlib.SKILL_ROOT, "references", "precon-v2-contract.md")
        self.assertTrue(os.path.isfile(contract))
        self.assertIn("references/precon-v2-contract.md", body)


if __name__ == "__main__":
    unittest.main()
