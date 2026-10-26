"""E18 slice B: ship-v2's `select` reads a plan whose slice headings use a hyphen (the E18 plan, slice B).

The shared plan reader (`station_core/templates.py`, `BUILD["slice"]`, and `ship_core/readings.py`, `FORM`) takes a
slice heading whose dash is one or more em dashes, en dashes or hyphens with one space on each side, so `select` on a
plan written with hyphen headings finds the slice, its card and its footprint. `TheCopies` checks that the seven
`station_core/templates.py` copies and the three `readings.py` copies stay byte for byte equal; in the installed shape
no sibling is there and the comparison is reported as SKIPPED with that reason, never as passed.

Every dash is written as an escape, never typed.
"""
import hashlib
import os
import unittest

import slib
import testlib

EM = "\u2014"
TEMPLATES_COPIES = tuple("%s/skills/%s/scripts/station_core/templates.py" % (core, core)
                         for core in ("architect-v2", "blueprint-v2", "handoff-v2", "inspect-v2", "precon-v2",
                                      "ship-v2", "vertical-v2"))
READINGS_COPIES = ("handoff-v2/skills/handoff-v2/scripts/handoff_core/readings.py",
                   "ship-v2/skills/ship-v2/scripts/ship_core/readings.py",
                   "vertical-v2/skills/vertical-v2/scripts/vertical_core/readings.py")


def with_dash(dash):
    """slib's build doc with every slice heading's em dash replaced by `dash`."""
    text = slib.build_doc()
    for name in ("A", "B"):
        old = "## Slice %s %s " % (name, EM)
        assert text.count(old) == 1, old
        text = text.replace(old, "## Slice %s %s " % (name, dash))
    return text


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheHyphenPlan(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-e18-dashes-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.tree = slib.Tree(self.tmp)

    def selected(self, text, slice_name):
        ws = slib.make_repo(self.tmp, doc_text=text, name="ws-%s" % slice_name)
        drive, run_dir = slib.start(self, self.tree, self.tmp, ws, run="run-%s" % slice_name, slice=slice_name)
        code, out, err = drive(["select", "--run-dir", run_dir, "--doc", slib.DOC])
        self.assertEqual((code, out.get("next")), (0, "hook"), (out, err))
        return out

    def test_select_on_a_hyphen_heading_plan_names_the_slice_its_card_and_its_footprint(self):
        text = with_dash("-")
        self.assertNotIn("## Slice A %s" % EM, text)
        out = self.selected(text, "A")
        self.assertEqual((out["doc"], out["slice"], out["card"]), (slib.DOC, "A", "not started"), out)
        self.assertEqual(out["footprint"], ["src/turnstile.py", "tests/"], out)
        out = self.selected(text, "B")
        self.assertEqual((out["slice"], out["card"], out["footprint"]), ("B", "not started", ["src/spinner.py"]), out)


class TheCopies(unittest.TestCase):

    def assert_equal_copies(self, rels):
        if not os.path.isdir(testlib.PLUGINS) or not all(os.path.isfile(os.path.join(testlib.PLUGINS, rel))
                                                          for rel in rels):
            self.skipTest("the installed shape: the sibling cores' copies are not beside this plugin")
        digests = {}
        for rel in rels:
            with open(os.path.join(testlib.PLUGINS, rel), "rb") as fh:
                digests[rel] = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(len(set(digests.values())), 1, digests)

    def test_the_seven_templates_copies_are_byte_for_byte_equal(self):
        self.assert_equal_copies(TEMPLATES_COPIES)

    def test_the_three_readings_copies_are_byte_for_byte_equal(self):
        self.assert_equal_copies(READINGS_COPIES)


if __name__ == "__main__":
    unittest.main()
