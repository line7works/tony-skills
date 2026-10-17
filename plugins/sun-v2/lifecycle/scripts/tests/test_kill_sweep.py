"""The kill sweep over every fake row (the contract's section 12, L6; E16-6; the frame's LOG-1 and OP-6 test lines).

A kill at every write boundary of every operation of the reference run's fake rows: a real SIGKILL
of a child process, a write that was not yet synced lost with it. After each, a status summons and
a resume on its position, as an executor would make them. No effect is applied twice, and each
rerun ends in the reference end state, in that state with an operation listed as `not proven` where
OP-6 says so, or stops plainly as outstanding (OP-7). The counts are printed for the report.
"""
import os
import sys
import unittest

import harness
import killlib
import rowlib


def prepare(machine):
    rowlib.install(machine, rowlib.clean_lane())
    machine.put("shortcuts.txt", "alias other\n")
    machine.put("dev/demo-scope.md", "scope\n")


class EveryBoundaryOfTheReferenceRun(harness.Case):
    def test_LOG1_OP6_E16_6_a_kill_at_every_write_boundary_of_every_fake_row(self):
        sweep = killlib.Sweep(self, self.tmp, prepare)
        failures = sweep.everywhere()
        row = sweep.ran
        sys.stderr.write("kill sweep: the reference run of %d fake rows: %d kill points of %d recorded, %d failed, %d worker(s); "
                         "outcomes: %s\n" % (len(rowlib.clean_rows()), row["kill_points"], row["recorded"], row["failed"],
                                             row["workers"], ", ".join("%s %d" % kv for kv in sorted(row["outcomes"].items()))))
        self.assertGreater(row["recorded"], 40)
        self.assertEqual(row["kill_points"], row["recorded"])
        self.assertEqual(failures, [], "%d of %d kill points failed:\n%s" % (len(failures), row["recorded"], "\n".join(failures[:15])))
        self.assertIn("complete", row["outcomes"], "no kill point's rerun ended in the reference end state")
        # SEC-11 over the sweep's executions (the reviewer's S1): the scan ran at every kill point, over every invocation of
        # it and the fixture home it left, for the run's canary token and every value a fake issued, and found nothing
        self.assertEqual(row["scanned"], row["recorded"], "the scan did not run at every kill point")
        self.assertTrue(row["scanned_reference"], "the reference run was not scanned")


class TheHelper(unittest.TestCase):
    def test_the_worker_count_comes_from_one_environment_name(self):
        self.assertEqual(killlib.WORKERS, "SUN_V2_SWEEP_WORKERS")
        self.assertEqual(killlib.worker_count({"SUN_V2_SWEEP_WORKERS": " 3 "}), 3)
        self.assertEqual(killlib.worker_count({}, cpus=36), 8)
        self.assertEqual(killlib.worker_count({}, cpus=2), 1)
        for bad in ("0", "-1", "two", "1.5"):
            with self.assertRaises(ValueError):
                killlib.worker_count({"SUN_V2_SWEEP_WORKERS": bad})

    def test_a_sweep_that_killed_at_other_points_than_the_reference_recorded_is_named(self):
        points = list(range(10))
        self.assertIsNone(killlib.count_problem(points, list(reversed(points))))
        self.assertIn("9 of 10", killlib.count_problem(points, points[:9]))
        self.assertIn("twice", killlib.count_problem(points, points + [3]))
        self.assertIn("did not record", killlib.count_problem(points, points + [11]))

    def test_SEC11_S1_the_sweeps_scan_reports_a_value_left_where_SEC7_gives_it_no_place(self):
        """The sweep's own scan is the SEC-11 scan: a value a kill point's machine left outside SEC-7's places, or one printed
        by an invocation of it, is a failure of that point."""
        import tempfile
        tmp = tempfile.mkdtemp(prefix="sunv2-")
        try:
            machine = harness.Machine(tmp, "home", "s1")
            token = killlib.sweep_token()
            self.assertEqual(killlib.scan_point(machine, [harness.Result(0, "clean", "", [])]), [])
            machine.put("dev/leak.txt", "a %s b\n" % token)
            self.assertTrue(killlib.scan_point(machine, []), "a value left in a file was not reported")
            os.remove(machine.path("dev/leak.txt"))
            self.assertTrue(killlib.scan_point(machine, [harness.Result(0, "out " + token, "", [])]), "a value printed was not reported")
        finally:
            import shutil
            shutil.rmtree(tmp, True)

    def test_an_effect_applied_twice_is_seen(self):
        facts = {"files": {}, "fakes": {"fakehost": {"things": {"demo": ("repo", "active"), "demo#2": ("repo", "active")}, "refs": {},
                                                    "sets": [{"name": "demo", "state": "paused"}, {"name": "demo", "state": "paused"}]}}}
        self.assertEqual(len(killlib.twice(facts)), 2)


if __name__ == "__main__":
    unittest.main()
