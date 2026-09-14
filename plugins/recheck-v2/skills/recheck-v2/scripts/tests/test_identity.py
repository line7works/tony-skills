"""recheck_core.identity: the six fields equal manifest.identity on every built case (E8 lane
contract section 5), pins (pilot contract section 6), and the work-tree test.

Expectations are manifest.json facts (a fact file) and the CASES.md sentences cited on each test.
Set RECHECK_TEST_ALL_LANES=1 to build every lane; the default builds the ten slice-2 lanes.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import identity  # noqa: E402

EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class IdentityEqualsManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lanes = testlib.all_lanes() if os.environ.get("RECHECK_TEST_ALL_LANES") == "1" else list(testlib.DEFAULT_LANES)

    def test_every_case(self):
        n = 0
        for lane in self.lanes:
            for cid, cdir in testlib.lane_cases(lane):
                manifest = testlib.load_json(os.path.join(cdir, "manifest.json"))
                got = identity.identity_of(os.path.join(cdir, manifest["workspace"]))
                self.assertEqual(got, manifest["identity"], "%s/%s: identity differs from manifest.identity" % (lane, cid))
                n += 1
        self.assertGreaterEqual(n, 80, "the ten lanes hold more than eighty cases")

    def test_submodule_list_is_real(self):
        """S34 CASES.md, S4-04: `git submodule status` prints one line for theme; the helper's own output carries it."""
        for cid, cdir in testlib.lane_cases("S34-cards-identity"):
            if cid.startswith("S4-04"):
                got = identity.identity_of(os.path.join(cdir, "workspace"))
                self.assertEqual(got["submodules"], ["theme"])
                self.assertEqual(identity.reported(got)["submodules"], [], "a result reports an empty list (E8-2)")


class Pins(unittest.TestCase):
    def case(self, lane, prefix):
        for cid, cdir in testlib.lane_cases(lane):
            if cid.startswith(prefix):
                return cdir
        raise AssertionError(prefix)

    def test_s4_05_clean_match(self):
        """S34 CASES.md, S4-05: every pin field equals the workspace identity as built."""
        cdir = self.case("S34-cards-identity", "S4-05")
        ws = os.path.join(cdir, "workspace")
        pin = testlib.load_json(os.path.join(cdir, "input.json"))["source_identity"]
        ok, reasons = identity.pin_matches(ws, identity.identity_of(ws), pin)
        self.assertTrue(ok, reasons)

    def test_s4_mismatches(self):
        """S4-01: dirty true and tracked_diff differs; S4-02: dirty true and tracked_diff differs;
        S4-03: untracked_sha256 differs while the path list is identical (S34 CASES.md)."""
        for prefix, field in (("S4-01", "tracked_diff_sha256"), ("S4-02", "tracked_diff_sha256"), ("S4-03", "untracked_sha256")):
            cdir = self.case("S34-cards-identity", prefix)
            ws = os.path.join(cdir, "workspace")
            pin = testlib.load_json(os.path.join(cdir, "input.json"))["source_identity"]
            actual = identity.identity_of(ws)
            ok, reasons = identity.pin_matches(ws, actual, pin)
            self.assertFalse(ok, prefix)
            self.assertTrue(any(field in r for r in reasons), (prefix, reasons))
            if prefix != "S4-03":
                self.assertTrue(any("dirty" in r for r in reasons), (prefix, reasons))
            else:
                self.assertEqual(actual["untracked"], ["notes.txt"])

    def test_i3_pins(self):
        """IA CASES.md, I3-01: the pinned base hash resolves and differs from HEAD; I3-02: the pin does not
        resolve (a mismatch); I3-03: dirty computes to true while the pinned commit equals HEAD."""
        c1 = self.case("IA-input-authorization", "I3-01")
        ws = os.path.join(c1, "workspace")
        pin = testlib.load_json(os.path.join(c1, "input.json"))["source_identity"]
        self.assertEqual(identity.normalize_pin(ws, pin["commit"]), pin["commit"])
        ok, reasons = identity.pin_matches(ws, identity.identity_of(ws), pin)
        self.assertFalse(ok); self.assertTrue(any("expected commit" in r for r in reasons), reasons)
        c2 = self.case("IA-input-authorization", "I3-02")
        ws2 = os.path.join(c2, "workspace")
        self.assertIsNone(identity.normalize_pin(ws2, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"))
        ok, reasons = identity.pin_matches(ws2, identity.identity_of(ws2), {"commit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"})
        self.assertFalse(ok); self.assertIn("does not resolve", reasons[0])
        c3 = self.case("IA-input-authorization", "I3-03")
        ws3 = os.path.join(c3, "workspace")
        actual = identity.identity_of(ws3)
        self.assertTrue(actual["dirty"]); self.assertNotEqual(actual["tracked_diff_sha256"], EMPTY)
        ok, reasons = identity.pin_matches(ws3, actual, testlib.load_json(os.path.join(c3, "input.json"))["source_identity"])
        self.assertFalse(ok); self.assertTrue(any("dirty" in r for r in reasons), reasons)

    def test_short_pin_normalizes(self):
        cdir = self.case("S34-cards-identity", "S4-05")
        ws = os.path.join(cdir, "workspace")
        full = identity.identity_of(ws)["commit"]
        self.assertEqual(identity.normalize_pin(ws, full[:8]), full)
        ok, _ = identity.pin_matches(ws, identity.identity_of(ws), {"commit": full[:8]})
        self.assertTrue(ok)


class WorkTree(unittest.TestCase):
    def test_root_and_not_root(self):
        cdir = testlib.lane_cases("F1-fixed-defect")[0][1]
        ws = os.path.join(cdir, "workspace")
        self.assertEqual(identity.is_work_tree_root(ws), (True, ""))
        ok, why = identity.is_work_tree_root(os.path.join(ws, "src"))
        self.assertFalse(ok); self.assertIn("root", why)
        ok, why = identity.is_work_tree_root(os.path.join(cdir, "run"))
        self.assertFalse(ok)
        ok, why = identity.is_work_tree_root(os.path.join(cdir, "nowhere"))
        self.assertFalse(ok); self.assertIn("does not exist", why)


if __name__ == "__main__":
    unittest.main()
