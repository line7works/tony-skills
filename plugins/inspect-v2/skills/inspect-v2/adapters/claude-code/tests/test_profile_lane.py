"""The profile sections lane I filled (E14 slice 2, brief CR-14), held to the code they describe.

The twelve E9 sections stay in order; no section is left for a lane to fill; section 2's "no
request carries `floor`" and section 6's clock hook are what `inspect_core/` does. `PROFILE_UNDER_TEST`
points the test at another copy of the profile (the red run read the frame's).
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.dirname(HERE)
SKILL = os.path.dirname(os.path.dirname(ADAPTER))
CORE = os.path.join(SKILL, "scripts", "inspect_core")


def profile():
    path = os.environ.get("PROFILE_UNDER_TEST") or os.path.join(ADAPTER, "profile.md")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def source(name):
    with open(os.path.join(CORE, name), encoding="utf-8") as fh:
        return fh.read()


class TheFilledProfile(unittest.TestCase):

    def test_twelve_sections_in_order_none_left_for_a_lane(self):
        numbers = [int(n) for n in re.findall(r"^## (\d+)\. ", profile(), re.M)]
        self.assertEqual(numbers, list(range(1, 13)))
        self.assertNotIn("fills this", profile())

    def test_no_request_carries_a_floor(self):
        self.assertIn("no request carries `floor`", profile())
        self.assertNotIn("floor=", source("request.py"))
        self.assertNotIn('"floor"', source("request.py"))

    def test_the_clock_hook_is_the_codes(self):
        self.assertIn("INSPECT_V2_TEST_NOW", profile())
        self.assertIn('PREFIX + "_TEST_NOW"', source("common.py"))

    def test_the_installed_route_is_named(self):
        self.assertIn("route 3b", profile())


if __name__ == "__main__":
    unittest.main()
