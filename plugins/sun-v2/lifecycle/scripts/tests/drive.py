"""A child process that drives the command line with a fixture machine's seams (test side only).

    python3 drive.py <config.json> <sun.py arguments...>

The tool itself loads nothing from its environment; a test that needs a real kill starts THIS file,
which builds the test world from `harness.py` and calls `sun.start(argv, world)`, the code the entry point runs. With
`kill_at` set, the process ends itself with a real SIGKILL when the write boundary of that number is
reached (a boundary is a recorded act of stage `pre`, `mid` or `post`); a write that was made and
not yet synced at that moment is lost first, as the fake file system of LOG-1's test line loses it.
"""
import json
import os
import signal
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness  # noqa: E402


def main():
    with open(sys.argv[1]) as fh:
        config = json.load(fh)
    machine = harness.Machine(config["root"], config["name"], config["seed"], create=False)
    machine.rows_root = config.get("rows_root")
    machine.clock = int(config.get("clock") or 0)
    machine.env.update(config.get("env") or {})
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
    import sun                          # the code the entry point runs: the withheld read, then the rest of the tool
    return sun.start(sys.argv[2:], world)


if __name__ == "__main__":
    sys.exit(main())
