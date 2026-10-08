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

The number of kill points per command is printed to stderr (`kill sweep:` lines), for the report. The sweep is the
slowest part of the suite by design: it runs a few hundred commands per flow.
"""
import sys
import unittest

import killlib
import slib
import testlib

SWEEPS = {}


def sweep(flow):
    """The flow's reference run, built once per process and shared by its commands' tests."""
    if flow.__name__ not in SWEEPS:
        tmp = testlib.make_scratch("ship-sweep-")
        SWEEPS[flow.__name__] = (killlib.Sweep(unittest.TestCase(), tmp, flow), tmp)
    return SWEEPS[flow.__name__][0]


def tearDownModule():
    for done, tmp in SWEEPS.values():
        testlib.rmtree(tmp)
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
                         "end, %d failed\n" % (name, row["kill_points"], row["window"][0], row["window"][1],
                                                row["lines"], row["states"], row["failed"]))
        self.assertGreater(row["kill_points"], 0)
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


if __name__ == "__main__":
    unittest.main()
