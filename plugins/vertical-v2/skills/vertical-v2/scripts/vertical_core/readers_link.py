"""readers, found and identified before any summons (the E15 lane contract A5 (1); rulings E15-6, E15-7 and
E15-12; reading CR-9; B5, C1A3-2).

A readers root is used only by ALLOWLIST IDENTITY. The allowlist holds the expected readers plugin and
nothing else: the checkout sibling `<plugin root>/../readers` (route 3a) and each installed
`<plugin root>/../../readers/<version>` folder of the plugin cache (route 3b, a canonical dotted version
name), each found the records way and each taken only when it is a real directory (never a symbolic link)
listed under its exact name by its parent, so a link, or a folder whose name differs only in letter case,
is never on it. A folder's identity is the disk's own: its device and inode (`os.stat`). This core's own
plugin root is read by its real path first.

Before anything of a readers root is opened (`preflight`), every candidate the resolver could take is held
to the allowlist: the explicit `--readers-root` must have the identity of an allowlisted folder (a link to
the real readers is therefore accepted: the folder it reaches IS the expected plugin, and every file is
then held to that folder); route 3a's path, when anything is there, must be the allowlisted sibling;
route 3b's folder, when anything is there, must be a real `readers` directory, and each canonical version
entry in it must be allowlisted (an entry that is not a canonical version is never a candidate and never
opened). Then every file vertical-v2 opens or runs from the root it takes (`.claude-plugin/plugin.json`,
`skills/readers/assets/roster.json`, `skills/readers/assets/readers.py`) must resolve, by its real path,
inside that root, compared by identity: each parent of the file's real path is stat'ed until one is the
root (a link into a v1 folder, or anywhere else, never is). Anything else raises RootRefused BEFORE the
file, or any file of that root, is opened or run; the caller writes the `refused` trace line and stops
the run `station-refused`.

The name-based v1 screen stays as a second line behind the allowlist (`screen`): a root whose real path
or own path, compared without regard to letter case, sits under a v1 plugin folder (`back_core/trace.py`'s
`v1_root`), or holds a v1 station's name followed by a dotted version anywhere in it (an installed v1
version folder, however deep the root is nested inside it), is refused too. A refusal carries the trace
rule `v1-root` when that screen names a v1 station for the root or the file, and `no-identity` otherwise
(nothing of the root was read, so no identity exists to name; the trace's rules are a frozen back-frame
file, so no new rule is added).

The identity is read from the root taken: the name and version its own manifest carries, its real path,
and the protocol version its own CLI prints (`readers.py --version`, which prints one number and writes
nothing; no reader is summoned by it). The identity is held to the trace's refusal rule; a refused
readers stops the run with a `refused` trace line before any request.
"""
import json
import os
import stat
import subprocess
import sys

from station_core import readers_roster
from station_core.records_client import ComponentUnavailable
from station_core.sibling import manifest, version_key
from back_core import trace

from . import common, report

KNOWN_PROTOCOLS = (1,)
NAME = "readers"
MANIFEST = os.path.join(".claude-plugin", "plugin.json")
ROSTER = readers_roster.ROSTER
SCRIPT = os.path.join("skills", "readers", "assets", "readers.py")


class RootRefused(Exception):
    """A readers root (or a file of it) refused before any of its files was opened or run."""

    def __init__(self, route, path, why, under=None):
        real = os.path.realpath(path)
        rule = "v1-root" if under is not None else "no-identity"
        Exception.__init__(self, "the readers root %s (route %s; real path %s) %s%s: refused before its manifest, "
                                 "roster or any executable was opened or run"
                           % (path, route, real, why,
                              "; it sits under the v1 plugin folder of %s" % under if under is not None else ""))
        self.route, self.path, self.real, self.under, self.rule, self.why = route, path, real, under, rule, why


# ---- the allowlist -----------------------------------------------------------------------------

def _identity_of(path, follow=True):
    """(st_dev, st_ino) of `path`, or None when nothing is there."""
    try:
        st = os.stat(path) if follow else os.lstat(path)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def _real_entry(parent, name):
    """(path, identity) of `parent/name` when the parent's own listing holds exactly `name` and it is a real
    directory, not a link; None otherwise. Nothing inside it is opened."""
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    if name not in names:
        return None
    path = os.path.join(parent, name)
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if not stat.S_ISDIR(st.st_mode):
        return None
    return path, (st.st_dev, st.st_ino)


def _own_root():
    return os.path.realpath(common.plugin_root())


def allowlist():
    """[(route, path, identity)]: the folders that are the expected readers plugin, 3a first, then each
    installed version in name order. Only listings and lstat are read."""
    own = _own_root()
    out = []
    beside = _real_entry(os.path.dirname(own), NAME)
    if beside is not None:
        out.append(("3a", beside[0], beside[1]))
    base = _real_entry(os.path.dirname(os.path.dirname(own)), NAME)
    if base is not None:
        for entry in sorted(os.listdir(base[0])):
            if version_key(entry) is None:
                continue
            found = _real_entry(base[0], entry)
            if found is not None:
                out.append(("3b", found[0], found[1]))
    return out


# ---- the second line: the name-based v1 screen --------------------------------------------------

def v1_under(path):
    """The v1 station a path sits under by name, or None: `trace.v1_root` on its real path and on its own
    path, each also lower-cased, and a v1 name followed by a dotted version anywhere in either."""
    names = trace.v1_names()
    shapes = []
    for shape in (os.path.realpath(path), os.path.normpath(os.path.abspath(path))):
        shapes += [shape, shape.lower()]
    for shape in shapes:
        under = trace.v1_root(shape)
        if under is not None:
            return under
        parts = [p for p in shape.split(os.sep) if p]
        for index in range(len(parts) - 1):
            if parts[index].lower() in names and trace.VERSION_DIR.match(parts[index + 1]):
                return parts[index].lower()
    return None


def screen(route, path):
    """Raise RootRefused when `path` sits under a v1 plugin folder by name (the second line)."""
    under = v1_under(path)
    if under is not None:
        raise RootRefused(route, path, "is named for a v1 station's folder", under)


# ---- the checks ----------------------------------------------------------------------------------

def candidates(argument=None):
    """[(route, path)]: every folder the resolver could take, in its order; nothing is opened here."""
    own = _own_root()
    out = []
    if argument:
        out.append(("argument", argument))
    beside = os.path.join(os.path.dirname(own), NAME)
    if os.path.lexists(beside):
        out.append(("3a", beside))
    base = os.path.join(os.path.dirname(os.path.dirname(own)), NAME)
    if os.path.lexists(base):
        out.append(("3b-folder", base))
        if os.path.isdir(base) and not os.path.islink(base):
            out += [("3b", os.path.join(base, e)) for e in sorted(os.listdir(base)) if version_key(e) is not None]
    return out


def check(route, path, allowed):
    """Raise RootRefused unless `path` is on the allowlist (then the second line)."""
    if route == "3b-folder":
        if _real_entry(os.path.dirname(path), NAME) is None:
            raise RootRefused("3b", path, "is not the plugin cache's real readers folder (a link, or another "
                                          "spelling)", v1_under(path))
        return
    ident = _identity_of(path, follow=(route == "argument"))
    on_list = [a for a in allowed if a[2] == ident and (route == "argument" or a[1] == path)]
    if ident is None or not on_list:
        raise RootRefused(route, path, "is not the expected readers plugin (the real folder %s, compared by "
                                       "device and inode)" % (" or ".join(a[1] for a in allowed) or
                                                              "beside this core, or installed in the plugin cache"),
                          v1_under(path))
    screen(route, path)


def preflight(argument=None):
    allowed = allowlist()
    for route, path in candidates(argument):
        check(route, path, allowed)
    return allowed


def inside(root, relative, route):
    """The path of `relative` under `root` when its real path lies inside `root` by identity; RootRefused
    otherwise (nothing is opened). A missing file is returned as it is: opening it fails, never elsewhere."""
    path = os.path.join(root, relative)
    target = _identity_of(root)
    real = os.path.realpath(path)
    current = os.path.dirname(real)
    while True:
        if _identity_of(current) == target:
            break
        parent = os.path.dirname(current)
        if parent == current:
            raise RootRefused(route, root, "holds %s, which resolves outside it (%s)" % (relative, real),
                              v1_under(real))
        current = parent
    under = v1_under(real)
    if under is not None:
        raise RootRefused(route, root, "holds %s, whose real path %s is named for a v1 station's folder"
                          % (relative, real), under)
    return path


def _regular(path):
    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except OSError:
        return False


def _why_not(root, route):
    """None when `root` is a usable readers root (its files held inside it first), else why not."""
    path = inside(root, MANIFEST, route)
    if not _regular(path):
        return "no plugin.json" if os.path.isdir(root) else "no such directory"
    body = manifest(root)
    if body is None:
        return "no plugin.json"
    if body.get("name") != NAME:
        return "its manifest names %r" % (body.get("name"),)
    if route == "3b" and body.get("version") != os.path.basename(root):
        return "name differs from version %s" % body.get("version")
    if not _regular(inside(root, ROSTER, route)):
        return "no roster"
    return None


def find(argument=None):
    """(found, roster): every candidate held to the allowlist first, then the records way among the
    allowlisted folders (the explicit root, then 3a, then the highest installed version)."""
    allowed = preflight(argument)
    looked = []
    order = []
    if argument:
        order.append(("argument", argument))
    order += [(route, path) for route, path, ident in allowed if route == "3a"]
    installed = sorted(((version_key(os.path.basename(p)), p) for r, p, i in allowed if r == "3b"), reverse=True)
    order += [("3b", path) for key, path in installed]
    for route, root in order:
        why = _why_not(root, route)
        if why is None:
            roster_path = inside(root, ROSTER, route)
            try:
                with open(roster_path, encoding="utf-8") as fh:
                    roster = json.load(fh)
            except (OSError, ValueError) as exc:
                raise ComponentUnavailable("missing dependency: readers component at %s has no readable roster (%s)"
                                           % (root, exc))
            if not isinstance(roster, dict):
                raise ComponentUnavailable("missing dependency: readers component at %s has a roster that is not a "
                                           "JSON object" % root)
            return {"root": root, "route": route, "roster": roster_path, "looked": looked + [root]}, roster
        looked.append("%s (%s)" % (root, why))
    raise ComponentUnavailable("missing dependency: readers component (looked in: %s)"
                               % (", ".join(looked) or "nowhere: no readers folder beside this core or installed"))


def identity(root, route="argument"):
    """The identity readers' own manifest and CLI give for `root`; readers.py is held inside the root first, then
    run isolated (`-I`: neither its own folder nor the user site is on `sys.path` and no `PYTHON*` variable is
    read, so a module planted beside it never runs, C1A4-2; `-B`: no bytecode written)."""
    body = manifest(root) or {}
    script = inside(root, SCRIPT, route)
    version = None
    if _regular(script):
        try:
            proc = subprocess.run([sys.executable, "-I", "-B", script, "--version"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=root,
                                  env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1",
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
    ident = identity(found["root"], found["route"])
    return found, roster, ident, trace.refusals("readers", ident, KNOWN_PROTOCOLS)


def refused_line(run, ctx, found, ident, refusals):
    line = trace.line(kind="refused", caller=common.STATION, expected="readers", identity=ident,
                      route=found["route"], run_dir=common.path_of(run, "readers"),
                      refusal={"rules": sorted(set(r["rule"] for r in refusals)),
                               "reason": "; ".join(r["message"] for r in refusals)}, at=common.now())
    common.check_trace(run)
    trace.append(run.run_dir, line, ctx.skill_root, ctx.prefix)


def refuse_root(ctx, run, exc):
    """A refusal before any file of the root was opened or run: one `refused` trace line (no identity was
    read) and the stop `station-refused`."""
    route = exc.route if exc.route in trace.ROUTES else None
    line = trace.line(kind="refused", caller=common.STATION, expected="readers", identity=None, route=route,
                      run_dir=common.path_of(run, "readers"), refusal={"rules": [exc.rule], "reason": str(exc)},
                      at=common.now())
    common.check_trace(run)
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
