"""Slice 3, the providers: a kill at every write boundary of the lane's end-to-end runs, through slice 1's kill-sweep
helper (`killlib.Sweep`; the contract's section 12, L6; the frame's LOG-1 and OP-6).

`killlib` drives the go in a child (`tests/drive.py`) that knows only what the fixture's files say. This lane's runs need
the fixture's own system folder (no real curl, no network), the frame's requests answered by the fake host, and the
hosting token in the session: so the child here is this file run with `--drive`, which builds the same machine the
in-process tests build (`provlib.rewire`) and then runs the code the entry point runs, exactly as `drive.py` does.
"""
import json
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import killlib  # noqa: E402

ME = os.path.abspath(__file__)
TOKEN = "VERCEL_TOKEN"


class ProvMachine(harness.Machine):
    """A fixture machine whose real-kill drive is this file's child, wired as `provlib.wire` wires it; its look takes the
    inputs its preparation wrote."""

    def look(self, name="demo", kind="sunrise", also=(), inputs=None, caps=None, **kw):
        return harness.Machine.look(self, name, kind, also, inputs or getattr(self, "inputs_path", None), caps, **kw)

    def drive(self, *argv, **kw):
        self.drives += 1
        config = {"root": self.root, "name": self.name, "seed": "%s/drive-%d" % (self.seed, self.drives),
                  "rows_root": self.rows_root, "kill_at": kw.get("kill_at"), "torn": bool(kw.get("torn")),
                  "events": kw.get("events"), "env": kw.get("env") or {}, "clock": self.clock + 1000 * self.drives,
                  "system": list(self.system_folders)}
        path = os.path.join(self.root, "drive-%s-%d.json" % (self.seed.replace("/", "_"), self.drives))
        with open(path, "w") as fh:
            json.dump(config, fh)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([sys.executable, ME, "--drive", path] + [str(a) for a in argv], env=env, cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        return harness.Result(proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8"), [], proc.returncode == -9)


def child(config_path, argv):
    """`tests/drive.py`'s `main`, with this lane's wiring: the fixture's system folder, the fake host of the frame's own
    requests (state on disk, so the child and the parent see one host), and the session's token."""
    with open(config_path) as fh:
        config = json.load(fh)
    machine = harness.Machine(config["root"], config["name"], config["seed"], create=False)
    machine.rows_root = config.get("rows_root")
    machine.clock = int(config.get("clock") or 0)
    machine.env.update(config.get("env") or {})
    machine.system_folders = tuple(config["system"])
    machine.transport = provlib.prov_fake.VercelAPI(machine.home, machine.env.get(TOKEN))
    sink = os.open(config["events"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600) if config.get("events") else None
    recorder = harness.Recorder(sink)
    recorder.torn = bool(config.get("torn"))
    machine.recorder = recorder
    world = machine.world()
    world.output = harness.worldmod.Output()
    if config.get("kill_at") is not None:
        seen = {"n": -1}

        def boundary(event):
            if event["stage"] in ("pre", "mid", "post"):
                seen["n"] += 1
                return seen["n"] == config["kill_at"]
            return False
        recorder.kill_at = boundary
        recorder.on_kill = lambda event: os.kill(os.getpid(), signal.SIGKILL)
    import sun
    return sun.start(argv, world)


class Sweep(killlib.Sweep):
    def __init__(self, test, tmp, prepare, kind, token):
        self.token = token
        # the plain stops these flows name: a create killed between its send and its answer (OP-7); and a need at the `made`
        # level on an operation a kill left `not proven` (OP-6, ORD-1: `not proven` meets no `made` need), SR16's on `push`
        killlib.Sweep.__init__(self, test, tmp, prepare, kind=kind, plain_stops=("an outstanding create", "need unmet"))
        self.env = dict(self.env, **{TOKEN: token})

    def fresh(self, label):
        machine = ProvMachine(os.path.join(self.tmp, label), "home", "sweep")
        provlib.wire(machine, self.token)
        self.prepare(machine)
        self.env = dict(self.env, **{TOKEN: self.token})
        return machine


def rise(machine):
    from test_lane_prov_rise import env_values, sunrise
    repo, _commit = sunrise(machine)
    provlib.forget_index(repo)
    env_values(machine)
    machine.inputs_path = provlib.rise_inputs(machine)


class EveryBoundary(harness.Case):
    def sweep(self, prepare, kind, words):
        token = harness.canary("sweep-vercel-token")
        sweep = Sweep(self, self.tmp, prepare, kind, token)
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
        row = self.sweep(rise, "sunrise", "the sunrise rows")
        self.assertGreater(row["recorded"], 60)

    def test_LOG1_OP6_T01s_T01_T03_T04_T04c_T20_T21_a_kill_at_every_write_boundary_of_the_sunset_run(self):
        def prepare(machine):
            repo, _commit, _password = provlib.sunset_world(machine, custom=[{"id": "env_customone", "slug": "staging"}])
            provlib.forget_index(repo)
            state = provlib.state(machine, "vercel")
            state["envs"]["demo"].append({"key": "STAGE_ONLY", "value": "staging-value-1", "type": "encrypted", "custom": "env_customone"})
            provlib.put_state(machine, "vercel", envs=state["envs"])
            provlib.install(machine, provlib.set_lane(tombstone=False))     # its journal render differs by kill (KEEP-5)
            machine.inputs_path = provlib.set_inputs(machine)
        row = self.sweep(prepare, "sunset", "the sunset rows")
        self.assertGreater(row["recorded"], 60)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--drive":
        sys.exit(child(sys.argv[2], sys.argv[3:]))
    import unittest
    unittest.main()
