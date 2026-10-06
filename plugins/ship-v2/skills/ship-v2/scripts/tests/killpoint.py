"""The kill tests' line tracer (the E15 lane contract A29 (2)): runs one ship-v2 command under `sys.settrace`.

    python3 killpoint.py record OUT.json - <ship.py> <command args...>
    python3 killpoint.py stop   OUT.json K <ship.py> <command args...>

Only lines of this core's own scripts count (the folder `<ship.py>` sits in, its `vendor/` reader left out): every
`line` event there is numbered from 0 in the order the interpreter runs it. `record` runs the command to its end and
writes OUT.json: the number of lines run and, for every call of a function that writes the run's state, its
checkpoint, a receipt, a run file, the trace or the records log, the line number at its call and at its return and
the base name of the file it writes (its `path` argument, when it has one).
`stop` runs the command until line K is about to run and stops the process there (SIGSTOP), so the test that started
it can kill it with a real SIGKILL at that line, as Astra's `kill_at_save.py` did (a stop at a line, not between
commands). A process that ends before line K writes OUT.json with the lines it ran.
"""
import json
import os
import runpy
import signal
import sys

MODE, OUT, WANT = sys.argv[1], sys.argv[2], sys.argv[3]
SCRIPT = os.path.abspath(sys.argv[4])
sys.argv = sys.argv[4:]
ROOT = os.path.dirname(SCRIPT) + os.sep
VENDOR = os.path.join(ROOT, "vendor") + os.sep
STOP_AT = int(WANT) if MODE == "stop" else -1
# (file under the scripts folder, function): every routine that writes the run directory, the trace or the log,
# before and after the crash-safe save (the old ones stay listed so the same test runs red on the old code)
WRITERS = {("ship_core/common.py", "put"), ("ship_core/common.py", "drop"),
           ("station_core/fsio.py", "atomic_write"), ("back_core/trace.py", "append"),
           ("station_core/records_client.py", "append")}

count = [0]
writes = []
where = {}


def ours(filename):
    return filename.startswith(ROOT) and not filename.startswith(VENDOR)


def local(frame, event, arg):
    if event == "line":
        if count[0] == STOP_AT:
            os.kill(os.getpid(), signal.SIGSTOP)
        count[0] += 1
    elif event == "return" and frame in where:
        where.pop(frame)["return"] = count[0]
    return local


def watch(frame, event, arg):
    if event != "call" or not ours(frame.f_code.co_filename):
        return None
    rel = frame.f_code.co_filename[len(ROOT):].replace(os.sep, "/")
    if (rel, frame.f_code.co_name) in WRITERS:
        target = frame.f_locals.get("path")
        where[frame] = {"name": "%s:%s" % (rel, frame.f_code.co_name), "call": count[0], "return": None,
                        "path": os.path.basename(target) if isinstance(target, str) else None}
        writes.append(where[frame])
    return local


def dump():
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"lines": count[0], "writes": writes}, fh)


sys.settrace(watch)
try:
    runpy.run_path(SCRIPT, run_name="__main__")
finally:
    sys.settrace(None)
    dump()
