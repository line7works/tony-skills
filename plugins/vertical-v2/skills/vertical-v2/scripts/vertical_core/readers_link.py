"""readers, found and identified before any summons (rulings E15-7 and E15-12; reading CR-9).

The root is found by the shared resolver (`station_core/readers_roster.py`: `--readers-root`, then
route 3a beside this core, then route 3b, the installed shape); nothing found is exit 3. Its identity is
read before the summons: the name and version its own manifest carries, its resolved root, and the
protocol version its own CLI prints (`readers.py --version`, which prints one number and writes
nothing; no reader is summoned by it). The identity is held to the trace's refusal rule
(`back_core/trace.py`); a refused readers stops the run with a `refused` trace line before any request.
"""
import os
import subprocess
import sys

from station_core import readers_roster
from station_core.records_client import ComponentUnavailable
from station_core.sibling import manifest
from back_core import trace

from . import common

KNOWN_PROTOCOLS = (1,)


def find(argument=None):
    try:
        return readers_roster.load(common.plugin_root(), argument)
    except readers_roster.RosterMissing as exc:
        raise ComponentUnavailable(str(exc))


def identity(root):
    """The identity readers' own manifest and CLI give for `root`."""
    body = manifest(root) or {}
    script = os.path.join(root, "skills", "readers", "assets", "readers.py")
    version = None
    try:
        proc = subprocess.run([sys.executable, script, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=root, env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1",
                                             "LANG": "C", "LC_ALL": "C"}, timeout=60)
        text = proc.stdout.decode("utf-8", "replace").strip()
        if proc.returncode == 0 and text.isdigit():
            version = int(text)
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return {"name": body.get("name") or "(no manifest)", "version": body.get("version") or "(none)",
            "root": os.path.realpath(root), "interface_version": version, "commit": None, "content_sha256": None}


def resolve(run, argument=None):
    """(found, roster, identity, refusals): the readers this run summons through, checked."""
    found, roster = find(argument)
    ident = identity(found["root"])
    return found, roster, ident, trace.refusals("readers", ident, KNOWN_PROTOCOLS)


def refused_line(run, ctx, found, ident, refusals):
    line = trace.line(kind="refused", caller=common.STATION, expected="readers", identity=ident,
                      route=found["route"], run_dir=common.path_of(run, "readers"),
                      refusal={"rules": sorted(set(r["rule"] for r in refusals)),
                               "reason": "; ".join(r["message"] for r in refusals)}, at=common.now())
    trace.append(run.run_dir, line, ctx.skill_root, ctx.prefix)
