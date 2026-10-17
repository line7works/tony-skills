"""A probe started by the entry point's own start line: imports every module of the tool, lists the file of
every module then loaded, and the interpreter's flags. Test-only; never shipped as a start."""
import json
import os
import pkgutil
import sys

scripts = sys.argv[1]
sys.path.insert(0, scripts)
import sun_core  # noqa: E402

for info in pkgutil.iter_modules(sun_core.__path__):
    __import__("sun_core." + info.name)
files = sorted(set(os.path.realpath(m.__file__) for m in list(sys.modules.values()) if getattr(m, "__file__", None)))
try:                       # the word the entry point waits for: the probe's code ran (RUN-1's failed start)
    os.write(3, b"r")
    os.close(3)
    os.dup2(5, 2)
    os.close(5)
except OSError:
    pass
print(json.dumps({"files": files, "modules": sorted(sys.modules), "prefix": os.path.realpath(sys.base_prefix),
                  "version": "%d.%d" % sys.version_info[:2], "isolated": sys.flags.isolated}))
