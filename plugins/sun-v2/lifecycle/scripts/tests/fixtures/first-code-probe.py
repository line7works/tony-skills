"""A probe started by the entry point's own start line in the place of `sun.py` (RUN-1's test line, A52): it loads the
file the start hands to the interpreter as a module, then runs the code that file runs for a start, with the real
file system and the real output, and at every read the withheld read makes of the tool's own folder it lists the
tool's files then loaded. It writes its list to the file named by its second argument, outside the fixture home.
Test-only; never shipped as a start.

    first-code-probe.py <scripts folder> <report file> <the start's arguments...>
"""
import json
import os
import sys

scripts, report = os.path.realpath(sys.argv[1]), sys.argv[2]
sys.path.insert(0, scripts)
import sun  # noqa: E402  (the file the start hands to the interpreter: it loads the first code and nothing else)

world = sun.worldmod.real()
home = os.path.realpath(world.env.get("HOME") or "")
tool_home = os.path.join(home, ".sun-v2")
reads = []


def loaded():
    out = set()
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path:
            path = os.path.realpath(path)
            if path.startswith(scripts + os.sep) and os.sep + "tests" + os.sep not in path:
                out.add(path)
    return sorted(out)


def hook(stage, op, subject, **more):
    if stage == "read" and isinstance(subject, str) and os.path.realpath(subject).startswith(tool_home):
        reads.append(loaded())


world.fs.hook = hook
code = sun.start(sys.argv[3:], world, lambda: sun._first_code_ran(world))
with open(report, "w") as fh:
    json.dump({"reads": reads, "code": code}, fh)
sys.exit(code)
