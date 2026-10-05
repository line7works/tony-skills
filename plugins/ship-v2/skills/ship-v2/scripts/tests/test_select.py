"""`select`, the narrowed hunt (ruling E15-10; contract section 3.1): a pause, never a wider hunt.

The doc named in the invocation is the doc. Otherwise the sources are exactly two: the repo's tiers (by the name the
invocation gives) and the plan established in the session (`--doc`). Nothing named, nothing found, several found, or a
slice the doc does not hold is a pause that asks the owner what he wants built: exit 0, `paused`, the run still at
`select`, nothing written anywhere (never a stop, never the lone doc on disk, never a pick among several).
"""
import os
import unittest

import slib
import testlib


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheNarrowedHunt(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-select-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.ws = slib.make_repo(self.tmp)

    def paused(self, drive, run_dir, args):
        before = (slib.snapshot(self.ws), sorted(os.listdir(run_dir)),
                  testlib.load_json(os.path.join(run_dir, "checkpoint.json")))
        code, out, err = drive(["select", "--run-dir", run_dir] + args)
        self.assertEqual(code, 0, (out, err))
        self.assertTrue(out["paused"], out)
        self.assertEqual(out["next"], "select")
        self.assertTrue(out["question"])
        self.assertEqual(before, (slib.snapshot(self.ws), sorted(os.listdir(run_dir)),
                                  testlib.load_json(os.path.join(run_dir, "checkpoint.json"))))
        return out

    def test_a_named_doc_is_the_doc(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--doc", slib.DOC])
        self.assertEqual((code, out["next"]), (0, "hook"), (out, err))
        self.assertEqual((out["doc"], out["slice"]), (slib.DOC, "A"))
        self.assertEqual(out["footprint"], ["src/turnstile.py", "tests/"])

    def test_the_repo_tiers_by_name(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", slib.FEATURE])
        self.assertEqual((code, out["doc"]), (0, slib.DOC), (out, err))

    def test_nothing_named_is_a_pause_never_the_lone_doc(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        out = self.paused(drive, run_dir, [])
        self.assertEqual(out["why"], "selection-unnamed")

    def test_nothing_found_is_a_pause(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        out = self.paused(drive, run_dir, ["--name", "widget"])
        self.assertEqual(out["why"], "selection-none")

    def test_several_found_is_a_pause_listing_them(self):
        testlib.write_text(os.path.join(self.ws, "docs", "plans", "2026-09-21-turnstile.md"), slib.build_doc())
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        out = self.paused(drive, run_dir, ["--name", slib.FEATURE])
        self.assertEqual(out["why"], "selection-several")
        self.assertEqual(len(out["candidates"]), 2)

    def test_a_slice_the_doc_does_not_hold_is_a_pause(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws, slice="Z")
        out = self.paused(drive, run_dir, ["--doc", slib.DOC])
        self.assertEqual(out["why"], "slice-unknown")

    def test_no_slice_named_is_a_pause_and_select_takes_his_answer(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws, slice=None)
        self.paused(drive, run_dir, ["--doc", slib.DOC])
        code, out, err = drive(["select", "--run-dir", run_dir, "--doc", slib.DOC, "--slice", "B"])
        self.assertEqual((code, out["slice"]), (0, "B"), (out, err))

    def test_a_doc_outside_the_workspace_is_refused(self):
        outside = os.path.join(self.tmp, "elsewhere.md")
        testlib.write_text(outside, slib.build_doc())
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--doc", outside])
        self.assertEqual(code, 5, (out, err))


if __name__ == "__main__":
    unittest.main()
