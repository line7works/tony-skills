"""Slice 3, the providers: a kill at every write boundary of the lane's end-to-end runs, through slice 1's kill-sweep
helper (`killlib.Sweep`; the contract's section 12, L6; the frame's LOG-1 and OP-6), on the joined lanes: a whole sunrise
on slice 2's fixture machine and a whole sunset on slice 4's, slice 3's rows among theirs.

`killlib` drives the go in a child that knows only what the fixture's files say. These runs need the fixture's own system
folder (no real curl, no network), the frame's requests answered by the fake host, and the hosting token in the session:
so the child is `provlib`'s (`provlib.Machine`, `provlib.Sweep`), which builds the same machine the in-process tests build
and then runs the code the entry point runs, exactly as `drive.py` does.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_rise_sweep as rise_sweep  # noqa: E402
import test_lane_set_sweep as set_sweep  # noqa: E402


class SetMachine(provlib.Machine):
    pass


def rise(machine):
    rise_sweep.prepare(machine)
    from test_lane_prov_rise import env_values
    env_values(machine)


class EveryBoundary(harness.Case):
    def sweep(self, prepare, kind, words, machine_kind):
        token = harness.canary("sweep-vercel-token")
        # the plain stops these flows name: a create killed between its send and its answer (OP-7); and a need at the `made`
        # level on an operation a kill left `not proven` (OP-6, ORD-1: `not proven` meets no `made` need)
        sweep = provlib.Sweep(self, self.tmp, prepare, token, machine_kind=machine_kind, kind=kind,
                              plain_stops=("an outstanding create", "need unmet"))
        failures = sweep.everywhere()
        row = sweep.ran
        sys.stderr.write("kill sweep (%s): %d kill points of %d recorded, %d failed, %d worker(s); outcomes: %s\n" % (
            words, row["kill_points"], row["recorded"], row["failed"], row["workers"],
            ", ".join("%s %d" % kv for kv in sorted(row["outcomes"].items()))))
        self.assertEqual(row["kill_points"], row["recorded"])
        self.assertEqual(failures, [], "%d of %d kill points failed:\n%s" % (len(failures), row["recorded"], "\n".join(failures[:15])))
        self.assertIn("complete", row["outcomes"])
        self.assertEqual(row["scanned"], row["recorded"])
        return row

    def test_LOG1_OP6_SR08_SR09_SR15_SR16_SR17_SR17c_SR19_a_kill_at_every_write_boundary_of_the_sunrise_run(self):
        rise_sweep.killlib.world_facts = rise_sweep.world_facts
        try:
            row = self.sweep(rise, "sunrise", "the sunrise rows", rise_sweep.RiseMachine)
        finally:
            rise_sweep.killlib.world_facts = rise_sweep.ORIGINAL
        self.assertGreater(row["recorded"], 60)

    def test_LOG1_OP6_T01s_T01_T03_T04_T04c_T20_T21_a_kill_at_every_write_boundary_of_the_sunset_run(self):
        def prepare(machine):
            set_sweep.prepared(machine, custom=[{"id": "env_customone", "slug": "staging"}])
            state = provlib.state(machine, "vercel")
            state["envs"]["demo"].append({"key": "STAGE_ONLY", "value": "staging-value-1", "type": "encrypted", "custom": "env_customone"})
            provlib.put_state(machine, "vercel", envs=state["envs"])
        set_sweep.killlib.world_facts = set_sweep.world_facts
        try:
            row = self.sweep(prepare, "sunset", "the sunset rows", SetMachine)
        finally:
            set_sweep.killlib.world_facts = set_sweep.REAL_FACTS
        self.assertGreater(row["recorded"], 60)


if __name__ == "__main__":
    import unittest
    unittest.main()
