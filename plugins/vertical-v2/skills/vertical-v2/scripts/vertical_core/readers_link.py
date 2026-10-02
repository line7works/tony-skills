"""readers, found and identified before any summons (rulings E15-6, E15-7 and E15-12; reading CR-9; B5).

Before anything of a readers root is opened, every candidate the shared resolver could take is resolved
to its real path (`preflight`): the explicit `--readers-root`, route 3a (`<plugin root>/../readers`), and
route 3b (`<plugin root>/../../readers` and each folder in it, whose names a listing reads without
opening any of them). A candidate whose real path, a symbolic link's target included, or whose own path
sits under a v1 plugin folder (`back_core/trace.py`'s `v1_root`) is refused right there: no manifest, no
roster and no executable of it is opened or run, the refusal is a `refused` trace line (rule `v1-root`),
and the run stops `station-refused`. Only then does the shared resolver
(`station_core/readers_roster.py`: the explicit root, then 3a, then 3b) read the manifests and the
roster; nothing found is exit 3. The identity is read from the root it found, checked once more by its
real path first: the name and version its own manifest carries, its resolved root, and the protocol
version its own CLI prints (`readers.py --version`, which prints one number and writes nothing; no reader
is summoned by it). The identity is held to the trace's refusal rule; a refused readers stops the run
with a `refused` trace line before any request.
"""
import os
import subprocess
import sys

from station_core import readers_roster
from station_core.records_client import ComponentUnavailable
from station_core.sibling import manifest
from back_core import trace

from . import common, report

KNOWN_PROTOCOLS = (1,)
NAME = "readers"


class RootRefused(Exception):
    """A candidate readers root under a v1 plugin folder, refused before any of its files was opened."""

    def __init__(self, route, path, real, under):
        Exception.__init__(self, "the readers root %s (route %s; real path %s) sits under the v1 plugin folder of "
                                 "%s: refused before its manifest, roster or any executable was opened"
                           % (path, route, real, under))
        self.route, self.path, self.real, self.under = route, path, real, under


def candidates(argument=None):
    """[(route, path)] for every folder the resolver could open, in its order; nothing is opened here."""
    root = common.plugin_root()
    out = []
    if argument:
        out.append(("argument", argument))
    out.append(("3a", os.path.join(root, os.pardir, NAME)))
    base = os.path.join(root, os.pardir, os.pardir, NAME)
    out.append(("3b", base))
    if os.path.isdir(base):
        out += [("3b", os.path.join(base, entry)) for entry in sorted(os.listdir(base))]
    return out


def screen(route, path):
    """Raise RootRefused when `path`, by its real path or its own, sits under a v1 plugin folder."""
    real = os.path.realpath(path)
    for shape in (real, os.path.normpath(os.path.abspath(path))):
        under = trace.v1_root(shape)
        if under is not None:
            raise RootRefused(route, path, real, under)


def preflight(argument=None):
    for route, path in candidates(argument):
        screen(route, path)


def find(argument=None):
    """(found, roster): every candidate screened first, then the shared resolver."""
    preflight(argument)
    try:
        found, roster = readers_roster.load(common.plugin_root(), argument)
    except readers_roster.RosterMissing as exc:
        raise ComponentUnavailable(str(exc))
    screen(found["route"], found["root"])
    return found, roster


def identity(root):
    """The identity readers' own manifest and CLI give for `root` (screened by its real path first)."""
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


def refuse_root(ctx, run, exc):
    """A preflight refusal: one `refused` trace line (no identity was read: nothing of the root was opened)
    and the stop `station-refused`."""
    line = trace.line(kind="refused", caller=common.STATION, expected="readers", identity=None, route=exc.route,
                      run_dir=common.path_of(run, "readers"), refusal={"rules": ["v1-root"], "reason": str(exc)},
                      at=common.now())
    trace.append(run.run_dir, line, ctx.skill_root, ctx.prefix)
    report.finish(ctx, run, "stopped", "station-refused", "%s; nothing was requested" % exc)


def find_or_stop(ctx, run, argument=None):
    try:
        return find(argument)
    except RootRefused as exc:
        refuse_root(ctx, run, exc)


def resolve_or_stop(ctx, run, argument=None):
    try:
        return resolve(run, argument)
    except RootRefused as exc:
        refuse_root(ctx, run, exc)
