"""A fault-injecting stand-in for the records component, for the E13 slice 1 fix round.

The pilot reaches the component through the CLI only, so a wrapper `scripts/records.py` under a
root handed to `--records-root` (or `RECORDS_ROOT`) is enough to answer one command with a
refusal, to kill the pilot around an append, to let a rival writer in, or to edit the document
while the pilot is between two component calls. Everything not injected runs the real component
unchanged.

One fault fires once: the shim drops a `<fault>.used` marker beside the configuration, so a
resume after a killed `record` runs against the real component.
"""
import json
import os
import stat

SHIM = r'''#!/usr/bin/env python3
"""Fault injector; every non-injected call goes to the real records CLI unchanged."""
import json, os, signal, subprocess, sys
args = sys.argv[1:]
real = os.environ["SHIM_REAL_RECORDS"]
config_path = os.environ.get("SHIM_FAULT")
config = json.load(open(config_path)) if config_path and os.path.isfile(config_path) else {}
cmd = args[0] if args else ""
events = []
if cmd == "append" and "--events" in args:
    events = json.load(open(args[args.index("--events") + 1]))
kind = events[0]["kind"] if events else None
matches = bool(config) and config.get("command") == cmd \
    and (not config.get("kind") or config["kind"] == kind) \
    and (not config.get("query_kind") or ("--kind" in args and args[args.index("--kind") + 1] == config["query_kind"]))
used = (config_path + ".used") if config_path else None
if matches and not (config.get("once", True) and used and os.path.exists(used)):
    if used:
        open(used, "w").write("used")
    action = config["action"]
    if action == "fail":
        print(json.dumps({"ok": False, "error": config.get("error", "conflict"),
                          "reason": config.get("reason", "injected: the log is unavailable at " + cmd),
                          "interface_version": 1, "component_version": "0.1.0"}))
        sys.exit(int(config.get("exit", 7)))
    if action == "mutate":
        with open(config["path"], "a") as fh:
            fh.write(config["text"])
    elif action == "compete":
        # a real rival writer: one card_set appended through the real CLI before ours
        rival = {k: events[0][k] for k in ("v", "at", "ledger_doc", "origin", "source")}
        rival.update(kind="card_set", slice=config.get("slice", "A"),
                     before=config.get("before", "rejected"), after=config.get("after", "built"),
                     actor={"station": "rival", "run_id": "rival-run", "harness": None})
        batch = config_path + ".rival-events.json"
        json.dump([rival], open(batch, "w"))
        argv = list(args)
        argv[argv.index("--events") + 1] = batch
        argv[argv.index("--expect-head") + 1] = config["rival_head"] if config.get("rival_head") else argv[argv.index("--expect-head") + 1]
        proc = subprocess.run([sys.executable, real] + argv, capture_output=True)
        open(config_path + ".rival.json", "wb").write(proc.stdout)
        assert proc.returncode == 0, proc.stderr
    elif action == "kill_before":
        os.kill(os.getppid(), signal.SIGKILL)
        sys.exit(0)
    elif action == "kill_after":
        proc = subprocess.run([sys.executable, real] + args, capture_output=True)
        open(config_path + ".landed.json", "wb").write(proc.stdout)
        assert proc.returncode == 0, proc.stderr
        os.kill(os.getppid(), signal.SIGKILL)
        sys.exit(0)
proc = subprocess.run([sys.executable, real] + args, capture_output=True)
sys.stdout.buffer.write(proc.stdout)
sys.stderr.buffer.write(proc.stderr)
sys.exit(proc.returncode)
'''


def make_shim(parent, records_root):
    """A component root whose `scripts/records.py` is the injector. Returns (root, fault_path)."""
    root = os.path.join(parent, "shim-records")
    scripts = os.path.join(root, "scripts")
    os.makedirs(scripts, exist_ok=True)
    path = os.path.join(scripts, "records.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SHIM)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return root, os.path.join(parent, "fault.json")


def fault(fault_path, **config):
    """Arm one fault; clears any earlier one and its `used` marker."""
    for suffix in (".used", ".landed.json", ".rival.json", ".rival-events.json"):
        if os.path.exists(fault_path + suffix):
            os.remove(fault_path + suffix)
    with open(fault_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh)
    return fault_path


def disarm(fault_path):
    """No fault: the shim forwards everything."""
    for suffix in ("", ".used"):
        if os.path.exists(fault_path + suffix):
            os.remove(fault_path + suffix)


def env(shim_root, real_records, fault_path):
    return {"RECORDS_ROOT": shim_root,
            "SHIM_REAL_RECORDS": os.path.join(real_records, "scripts", "records.py"),
            "SHIM_FAULT": fault_path}
