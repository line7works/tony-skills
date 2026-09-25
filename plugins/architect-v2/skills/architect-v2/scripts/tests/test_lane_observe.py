"""The lane's observer (CR-7, required test 9).

`evals/seeded-cases/lane_observe.py` fills every name the families' `lane` steps list, from a
real drive (A2: the library functions `record-answer` calls; A4: the CLI itself, `check-input` to
`report`, in the case's own built tree, each phase with its exit under `_phases`), with no
`_lane_pending` and no `_errors` left in any `observed.json`. The test reads facts only; what a fact should be is the
answer key's, never this suite's.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")


@unittest.skipIf(testlib.checkout_sibling("readers") is None,
                 "no readers component beside this core (the installed shape): observe.py reads its roster")
class LaneObserve(unittest.TestCase):

    def test_every_pending_name_is_filled(self):
        self.assertTrue(os.path.isfile(os.path.join(SEEDED, "lane_observe.py")))
        tmp = testlib.make_scratch("lane-observe-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, OBSERVE, "--all", "--out", tmp], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-2000:] + proc.stderr.decode()[-2000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        lane_steps = 0
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            self.assertNotIn("_lane_pending", observed, row["case"])
            drive = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "drive.json"))
            for step in drive["steps"]:
                if step["kind"] != "lane":
                    continue
                lane_steps += 1
                for name in step["pending"]:
                    self.assertIn(name, observed, (row["case"], name))
                    self.assertIn(name, observed["_via"], (row["case"], name))
        self.assertGreater(lane_steps, 0)
        a4 = [r for r in rows if r["case"].startswith("A4-")]
        self.assertEqual(len(a4), 3)
        for row in a4:
            observed = testlib.load_json(row["observed"])
            phases = [p["phase"] for p in observed["_phases"]]
            self.assertEqual(phases, ["check-input", "select", "select", "harvest", "record-answer", "write",
                                      "render-visual", "record-publish", "report"], row["case"])
            self.assertEqual(observed["_phases"][-1]["exit"], 10, row["case"])
            self.assertIn("cli", observed["_via"]["terminal_status"], row["case"])
            # R2 (CA2-2): the drive runs in the case's OWN built tree, never a copy, so the frame's
            # writes_none measures the real run; the visual the drive rendered is in that tree
            self.assertIn("the case's own tree", observed["_via"]["visual_rendered"], row["case"])
            self.assertNotIn("copy", observed["_via"]["visual_rendered"], row["case"])
            neutral = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "input.json"))
            visuals = [os.path.join(base, n) for base, _, names in os.walk(neutral["workspace"])
                       for n in names if n.endswith("-architecture.html")]
            self.assertEqual(len(visuals), 1, (row["case"], visuals))


DOC = ("# Turnstile %(D)s architecture (2026-09-21)\n\n"
       "Scope doc: docs/scope/2026-09-20-turnstile.md\nBlind review: declined 2026-09-21\n\n"
       "## Walkthrough target\nWho: Sam Bench  %(M)s  When: 2026-10-01  %(M)s  Must be able to: count turns\n\n"
       "## v0 drawing\nComponents: turnstile.py (serves: count turns)\nData flow: the fixture calls it\n"
       "Diagram: fixture -> turnstile.py\n\n## Poured concrete (one-way doors)\n\n## Deferred\n\n## Run log\n"
       "### Run 1 %(D)s 2026-09-21 %(D)s trigger: first run\nExit ramp: system %(D)s the interview continued; yes\n"
       "Step 3.1 (walkthrough target): Sam Bench\n"
       "Step 3.2 (candidates): module (platform:library); service (platform:server); chosen: module; "
       "rejected: service %(D)s the bench imports\n"
       "Step 3.3 (one-way doors): platform\nRulings: declined\nChanged this run: first run\n") % {"D": "\u2014",
                                                                                                "M": "\u00b7"}


class TheTranslationChoices(unittest.TestCase):
    """CA2-8: every translation choice is stated in the docstring as a choice; the candidates'
    `assumes` and `later_cost`, which the doc's form does not record, are a named placeholder."""

    def test_the_placeholder_is_stated_and_used(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("lane_observe_under_test", os.path.join(SEEDED, "lane_observe.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        words = "not recorded by the doc's form"
        self.assertIn(words, " ".join(module.__doc__.split()))
        answer = module.translate(DOC, "docs/architecture/2026-09-21-turnstile.md", {"questions": []}, True,
                                  "2026-09-25")
        self.assertTrue(answer["candidates"])
        for c in answer["candidates"]:
            self.assertEqual((c["assumes"], c["later_cost"]), (words, words))


if __name__ == "__main__":
    unittest.main()
