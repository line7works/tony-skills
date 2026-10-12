"""The E15 lane contract A29 (2): a kill at every line between each saving command's first and last write.

For each ship command that saves (`select`, `hook`, `visit` open and result for each of the three stations, `fix`,
`lap`, `pause --question`, `pause --answer` with a grant, `report`), the test stops a PID it started at EVERY line of
this core's own scripts that runs between that command's first and last write of the state, the checkpoint, a
receipt, a run file, the trace or the records log (`killpoint.py`, the lines numbered as the interpreter runs them),
SIGKILLs it there, runs the same command again (the executor's next command), and requires that the run then holds
exactly what the uninterrupted command left, byte for byte (nothing written twice, nothing left half written, no
journal or temporary file left), and that the rest of the flow ends the run at the reference's terminal status
(`killlib.Sweep`; replayed once per distinct state a kill leaves). Every kill restores the case first, so each point
starts from the same bytes.

The kill points of a command run side by side (the E15 punch list, item 4; the E15 lane contract A34 (4);
`killlib.Fleet`, THE WORKERS): `SHIP_V2_SWEEP_WORKERS` workers (unset: a quarter of the machine's processors, at
least 1 and at most 8), each with its own case in its own temporary folder, built by its own reference run. The same
kill points as one worker runs, none dropped: every test here fails when the lines its workers killed at are not
exactly the window the tracer recorded in the same run, each line once. `SHIP_V2_SWEEP_WORKERS=1` starts no thread
and runs the points one after another, in order.

The number of kill points per command is printed to stderr (`kill sweep:` lines), for the report. The sweep is the
slowest part of the suite by design: it runs a few thousand commands per flow.
"""
import sys
import unittest

import killlib
import slib

SWEEPS = {}


def sweep(flow):
    """The flow's workers, each with its reference run, built once per process and shared by its commands' tests."""
    if flow.__name__ not in SWEEPS:
        SWEEPS[flow.__name__] = killlib.Fleet(unittest.TestCase(), flow)
    return SWEEPS[flow.__name__]


def tearDownModule():
    for fleet in SWEEPS.values():
        fleet.close()
    SWEEPS.clear()


def index_of(run, name):
    return next(i for i in run.swept() if run.steps[i].name == name)


class _Sweeps(unittest.TestCase):
    FLOW = None

    def everywhere(self, name):
        run = sweep(type(self).FLOW)
        failures = run.kill_everywhere(index_of(run, name))
        row = run.ran[name]
        sys.stderr.write("kill sweep: %s: %d kill points (lines %d to %d of %d), %d distinct states replayed to the "
                         "end, %d failed, %d worker(s)\n" % (name, row["kill_points"], row["window"][0],
                                                              row["window"][1], row["lines"], row["states"],
                                                              row["failed"], row["workers"]))
        self.assertGreater(row["kill_points"], 0)
        self.assertEqual(row["recorded"], row["window"][1] - row["window"][0] + 1)
        self.assertEqual(row["kill_points"], row["recorded"],
                         "%s: the workers killed at %d lines and the tracer recorded %d in this run"
                         % (name, row["kill_points"], row["recorded"]))
        self.assertEqual(failures, [], "%s: %d of %d kill points failed:\n%s"
                         % (name, len(failures), row["kill_points"], "\n".join(failures[:12])))


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class EveryLineOfTheGrantFlow(_Sweeps):
    FLOW = staticmethod(killlib.grant_flow)

    def test_select(self):
        self.everywhere("select")

    def test_hook(self):
        self.everywhere("hook")

    def test_visit_open_build(self):
        self.everywhere("visit --station build-v2")

    def test_visit_result_build(self):
        self.everywhere("visit --result (build-v2)")

    def test_visit_open_signoff(self):
        self.everywhere("visit --station signoff-v2")

    def test_visit_result_signoff(self):
        self.everywhere("visit --result (signoff-v2)")

    def test_pause_question(self):
        self.everywhere("pause --question")

    def test_pause_answer_with_a_grant(self):
        self.everywhere("pause --answer (a waiver)")

    def test_fix(self):
        self.everywhere("fix")

    def test_visit_open_recheck(self):
        self.everywhere("visit --station recheck-v2")

    def test_visit_result_recheck(self):
        self.everywhere("visit --result (recheck-v2)")

    def test_report(self):
        self.everywhere("report")


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class EveryLineOfTheLapFlow(_Sweeps):
    FLOW = staticmethod(killlib.lap_flow)

    def test_lap(self):
        self.everywhere("lap")


class TheShares(unittest.TestCase):
    """The E15 punch list, item 4 (the E15 lane contract A34 (4)): the kill points of a command are dealt to the
    workers in whole, none dropped and none twice; one worker takes them in the order the sweep always ran them; the
    worker count comes from one environment name; and a sweep that ran another set of points than the tracer
    recorded in the same run is a failure with words. None of this needs a station or jsonschema."""

    POINTS = list(range(2315, 2398))        # `hook` on 5cf37d5: lines 2315 to 2397, 83 kill points

    def test_the_shares_hold_every_point_once_and_in_order(self):
        for count in (1, 2, 3, 7, 8, 83, 84, 500):
            shares = killlib.shares(self.POINTS, count)
            self.assertEqual([line for share in shares for line in share], self.POINTS, count)
            self.assertEqual(len(shares), min(count, len(self.POINTS)), count)
            self.assertTrue(all(shares), "no worker is dealt an empty share (%d)" % count)
            sizes = [len(share) for share in shares]
            self.assertLessEqual(max(sizes) - min(sizes), 1, (count, sizes))

    def test_one_worker_takes_the_points_in_the_order_the_sweep_always_ran_them(self):
        self.assertEqual(killlib.shares(self.POINTS, 1), [self.POINTS])
        self.assertEqual(killlib.shares([], 4), [])

    def test_the_worker_count_comes_from_one_environment_name(self):
        self.assertEqual(killlib.WORKERS, "SHIP_V2_SWEEP_WORKERS")
        self.assertEqual(killlib.worker_count({"SHIP_V2_SWEEP_WORKERS": "1"}), 1)
        self.assertEqual(killlib.worker_count({"SHIP_V2_SWEEP_WORKERS": " 6 "}), 6)
        self.assertEqual(killlib.worker_count({}, cpus=36), killlib.default_workers(36))
        self.assertEqual(killlib.worker_count({"SHIP_V2_SWEEP_WORKERS": ""}, cpus=8), killlib.default_workers(8))

    def test_the_default_leaves_room_for_the_other_runtime(self):
        # the two runtimes run their suites at once (the lane contract A33): two sweeps, each with this many workers
        for cpus, want in ((None, 1), (1, 1), (2, 1), (4, 1), (8, 2), (10, 2), (16, 4), (36, 8), (128, 8)):
            self.assertEqual(killlib.default_workers(cpus), want, cpus)
            self.assertLessEqual(2 * killlib.default_workers(cpus), max(2, (cpus or 1) // 2), cpus)

    def test_a_count_that_is_no_positive_whole_number_is_refused(self):
        for bad in ("0", "-2", "two", "1.5", "0x4"):
            with self.assertRaises(ValueError, msg=bad) as caught:
                killlib.worker_count({"SHIP_V2_SWEEP_WORKERS": bad})
            self.assertIn("SHIP_V2_SWEEP_WORKERS", str(caught.exception))

    def test_a_sweep_that_ran_other_points_than_the_tracer_recorded_is_named(self):
        self.assertIsNone(killlib.count_problem(self.POINTS, list(self.POINTS)))
        self.assertIsNone(killlib.count_problem(self.POINTS, list(reversed(self.POINTS))), "the order is the workers'")
        dropped = killlib.count_problem(self.POINTS, self.POINTS[:40] + self.POINTS[41:])
        self.assertIn("82 of 83", dropped)
        self.assertIn("2355", dropped)
        twice = killlib.count_problem(self.POINTS, self.POINTS + [2397])
        self.assertIn("twice", twice)
        self.assertIn("2397", twice)
        other = killlib.count_problem(self.POINTS, self.POINTS[1:] + [2398])
        self.assertIn("2315", other)
        self.assertIn("2398", other)


if __name__ == "__main__":
    unittest.main()
