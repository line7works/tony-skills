"""The stations ship-v2 visits, found and identified before any visit, and their own results (CR-21; rulings E15-6
and E15-7; the E15 lane contract A5 (1)'s allowlist identity, which vertical-v2 uses for readers; contract section 3.4).

    resolve(name) -> {"root", "route", "looked"}; RootRefused before any file of a refused root is opened or run
    identify(name, found) -> the station's identity, read through its own CLI (`skill-identity`, the one command)
    refusals(name, identity, found) -> [{"rule", "message"}]: the trace's refusal rule, the v1 screen, the version
    result_problems(name, found, identity, doc, visit, run_facts) -> [why]: the result is not the visit's own
    outcome(name, doc) -> the station's terminal status and what ship-v2 reads of it

ALLOWLIST IDENTITY. A station root is used only when it is the expected v2 sibling by the disk's own identity: the
checkout sibling `<plugin root>/../<name>` (route 3a) or an installed `<plugin root>/../../<name>/<version>` folder
of the plugin cache (route 3b, a canonical dotted version name), each taken only when it is a real directory (never
a link) listed under its exact name by its parent, compared with the candidate by device and inode. This core's own
plugin root is read by its real path first. Before anything of a root is opened or run, every candidate the
resolver could take is held to the allowlist; then each file ship-v2 opens or runs from the root it takes (its
manifest, `skills/<name>/scripts/<script>`, `skills/<name>/references/result.schema.json`) must resolve, by its real
path, inside that root, compared by identity. A root whose manifest names another plugin is refused without running
anything of it (`v1-name` when it names a v1 station, else `name-mismatch`). The name-based v1 screen stays as a
second line: a root whose real path or own path, compared without regard to letter case, sits under a v1 plugin
folder (`back_core/trace.py`'s `v1_root`), or holds a v1 station's name over a dotted version anywhere in it, is
refused (`v1-root`). A refusal is a `refused` trace line and the stop `station-refused`, written by the caller.

THE IDENTITY. The station's own CLI, `scripts/<script> skill-identity`, run isolated (`-I`: neither its folder nor
the user site is on `sys.path` and no `PYTHON*` variable is read; `-B`: no bytecode written), from its root, with a
fixed environment and a timeout: its `name`, `version`, `commit`, `content_sha256` and `interface_version`, with the
root's real path. Held to the trace's refusal rule (`trace.refusals`: a v1 name, a name that is not the expected
one, a root under a v1 plugin folder, an interface version the caller does not know: `KNOWN`), to the screen, and to
the plugin version: the version the CLI reports must be the version the root's own manifest carries (`no-identity`
otherwise: the answer is not the root's). `skill-identity` is the one station command ship-v2 runs; it never runs a
station's phases (E15-4).
"""
import json
import os
import re
import stat
import subprocess
import sys

from station_core import records_client, validate
from station_core.sibling import manifest, version_key
from back_core import trace

KNOWN = {"build-v2": (1,), "signoff-v2": (1,), "recheck-v2": (1,)}
SCRIPTS = {"build-v2": "build.py", "signoff-v2": "signoff.py", "recheck-v2": "recheck.py"}
COMMAND = "skill-identity"
MANIFEST = os.path.join(".claude-plugin", "plugin.json")
TIMEOUT = 120
SHA = re.compile(r"^[0-9a-f]{64}$")


class RootRefused(Exception):
    """A station root (or a file of it) refused before any of its files was opened or run."""

    def __init__(self, route, path, why, under=None, rule=None):
        real = os.path.realpath(path)
        rule = rule or ("v1-root" if under is not None else "no-identity")
        Exception.__init__(self, "the station root %s (route %s; real path %s) %s%s: refused before any of its files "
                                 "was run" % (path, route, real, why, "; it sits under the v1 plugin folder of %s"
                                              % under if under is not None else ""))
        self.route, self.path, self.real, self.under, self.rule, self.why = route, path, real, under, rule, why


def plugin_root():
    """This core's own plugin root, by its real path (the frame's station_core reckons it from its own location)."""
    return os.path.realpath(records_client.station_plugin_root())


def _identity_of(path, follow=True):
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


def allowlist(name):
    """[(route, path, identity)]: the folders that are the expected station, 3a first, then each installed version in
    name order. Only listings and lstat are read."""
    own = plugin_root()
    out = []
    beside = _real_entry(os.path.dirname(own), name)
    if beside is not None:
        out.append(("3a", beside[0], beside[1]))
    base = _real_entry(os.path.dirname(os.path.dirname(own)), name)
    if base is not None:
        for entry in sorted(os.listdir(base[0])):
            if version_key(entry) is None:
                continue
            found = _real_entry(base[0], entry)
            if found is not None:
                out.append(("3b", found[0], found[1]))
    return out


def v1_under(path):
    """The v1 station a path sits under by name, or None: `trace.v1_root` on its real path and its own path, each also
    lower-cased, and a v1 name followed by a dotted version anywhere in either."""
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


def candidates(name):
    """[(route, path)]: every folder the resolver could take, in its order; nothing is opened here."""
    own = plugin_root()
    out = []
    beside = os.path.join(os.path.dirname(own), name)
    if os.path.lexists(beside):
        out.append(("3a", beside))
    base = os.path.join(os.path.dirname(os.path.dirname(own)), name)
    if os.path.lexists(base):
        out.append(("3b-folder", base))
        if os.path.isdir(base) and not os.path.islink(base):
            out += [("3b", os.path.join(base, e)) for e in sorted(os.listdir(base)) if version_key(e) is not None]
    return out


def _check(name, route, path, allowed):
    if route == "3b-folder":
        if _real_entry(os.path.dirname(path), name) is None:
            raise RootRefused("3b", path, "is not the plugin cache's real %s folder (a link, or another spelling)"
                              % name, v1_under(path))
        return
    ident = _identity_of(path, follow=False)
    on_list = [a for a in allowed if a[2] == ident and a[1] == path]
    if ident is None or not on_list:
        raise RootRefused(route, path, "is not the expected %s plugin (a real folder beside this core or installed in "
                                       "the plugin cache, compared by device and inode)" % name, v1_under(path))
    under = v1_under(path)
    if under is not None:
        raise RootRefused(route, path, "is named for a v1 station's folder", under)


def inside(root, relative, route):
    """The path of `relative` under `root` when its real path lies inside `root` by identity; RootRefused otherwise
    (nothing is opened)."""
    path = os.path.join(root, relative)
    target = _identity_of(root)
    real = os.path.realpath(path)
    current = os.path.dirname(real)
    while True:
        if _identity_of(current) == target:
            break
        parent = os.path.dirname(current)
        if parent == current:
            raise RootRefused(route, root, "holds %s, which resolves outside it (%s)" % (relative, real), v1_under(real))
        current = parent
    under = v1_under(real)
    if under is not None:
        raise RootRefused(route, root, "holds %s, whose real path %s is named for a v1 station's folder"
                          % (relative, real), under)
    return path


def _regular(path):
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        return False


def _manifest(root, route):
    path = inside(root, MANIFEST, route)
    if not _regular(path):
        return None
    return manifest(root)


def resolve(name):
    """The station's root, by allowlist identity (module docstring); RootRefused or LookupError."""
    if name not in KNOWN:
        raise LookupError("%r is not a station ship-v2 visits (%s)" % (name, ", ".join(sorted(KNOWN))))
    allowed = allowlist(name)
    for route, path in candidates(name):
        _check(name, route, path, allowed)
    looked = []
    order = [(r, p) for r, p, i in allowed if r == "3a"]
    order += [("3b", p) for k, p in sorted(((version_key(os.path.basename(p)), p) for r, p, i in allowed if r == "3b"),
                                           reverse=True)]
    for route, root in order:
        body = _manifest(root, route)
        if body is None:
            looked.append("%s (no plugin.json)" % root)
            continue
        named = body.get("name")
        if named != name:
            rule = "v1-name" if named in trace.v1_names() else "name-mismatch"
            raise RootRefused(route, root, "carries a manifest naming %r, not %s" % (named, name), rule=rule)
        if route == "3b" and body.get("version") != os.path.basename(root):
            looked.append("%s (name differs from version %s)" % (root, body.get("version")))
            continue
        script = inside(root, os.path.join("skills", name, "scripts", SCRIPTS[name]), route)
        if not _regular(script):
            looked.append("%s (no %s)" % (root, os.path.relpath(script, root)))
            continue
        return {"root": root, "route": route, "looked": looked + [root], "manifest_version": body.get("version")}
    raise LookupError("missing station: %s (looked in: %s)" % (
        name, ", ".join(looked) or "nowhere: no %s folder beside this core or installed" % name))


def identify(name, found):
    """The identity the station's own CLI gives for its root (module docstring, THE IDENTITY); None when it gives
    none (it failed, printed no JSON object, or timed out)."""
    root = found["root"]
    script = inside(root, os.path.join("skills", name, "scripts", SCRIPTS[name]), found["route"])
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C", "LC_ALL": "C",
           "HOME": os.environ.get("HOME", "/")}
    try:
        proc = subprocess.run([sys.executable, "-I", "-B", script, COMMAND], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=root, env=env, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        doc = json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("name"), str) or not doc.get("name") \
            or not isinstance(doc.get("version"), str) or not doc.get("version"):
        return None
    version = doc.get("interface_version")
    sha = doc.get("content_sha256")
    commit = doc.get("commit")
    return {"name": doc["name"], "version": doc["version"], "root": os.path.realpath(root),
            "interface_version": version if type(version) is int else None,
            "commit": commit if isinstance(commit, str) else None,
            "content_sha256": sha if isinstance(sha, str) and SHA.match(sha) else None}


def refusals(name, identity, found=None):
    """[{"rule", "message"}] for every way `identity` is not the expected v2 sibling; [] when it is."""
    out = trace.refusals(name, identity, KNOWN[name])
    if not isinstance(identity, dict):
        return out
    under = v1_under(identity["root"])
    if under is not None and not any(r["rule"] == "v1-root" for r in out):
        out.append({"rule": "v1-root", "message": "its root %s is named for the v1 station %s" % (identity["root"],
                                                                                                  under)})
    expected = (found or {}).get("manifest_version")
    if found is not None and identity.get("version") != expected:
        out.append({"rule": "no-identity", "message": "its CLI reports version %r and its root's manifest carries %r, "
                                                      "so the answer is not the root's own" % (identity.get("version"),
                                                                                               expected)})
    return out


# ---- the station's own result ------------------------------------------------------------------------

def result_schema(name, found):
    path = inside(found["root"], os.path.join("skills", name, "references", "result.schema.json"), found["route"])
    if not _regular(path):
        raise LookupError("the station %s at %s has no result schema" % (name, found["root"]))
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def _same_dir(a, b):
    return isinstance(a, str) and isinstance(b, str) and os.path.realpath(a) == os.path.realpath(b)


def run_block(name, doc):
    """The fields that bind a result to its run: (run_id, run_dir, slice, doc, workspace), None where absent.
    recheck-v2's run block names no slice or doc: its `checklist` does (slice 2 check 1's C2-4)."""
    if name == "build-v2":
        return doc.get("run_id"), doc.get("run_dir"), doc.get("slice"), doc.get("build_doc"), doc.get("workspace")
    run = doc.get("run") if isinstance(doc.get("run"), dict) else {}
    if name == "signoff-v2":
        return run.get("run_id"), run.get("run_dir"), run.get("slice"), run.get("build_doc"), run.get("workspace")
    checklist = doc.get("checklist") if isinstance(doc.get("checklist"), dict) else {}
    return run.get("run_id"), run.get("run_dir"), checklist.get("slice"), checklist.get("build_doc"), None


def named_station(name, doc):
    """(the station name, the plugin version) the result itself states: build-v2 and signoff-v2 at the top level
    (`plugin_version`; the name is the schema's), recheck-v2 in its run block's `skill` (C2-4)."""
    if name == "recheck-v2":
        run = doc.get("run") if isinstance(doc.get("run"), dict) else {}
        skill = run.get("skill") if isinstance(run.get("skill"), dict) else {}
        return skill.get("name"), skill.get("version")
    return name, doc.get("plugin_version")


def result_problems(name, found, identity, doc, visit, facts, prefix):
    """[why] the result is not this visit's own v2 result (module docstring); [] when it is."""
    problems = ["%s %s" % (e["path"], e["message"]) for e in validate.errors_for(doc, result_schema(name, found),
                                                                               prefix)[:4]]
    if problems:
        return ["it does not validate against %s's own result schema (a v1 station leaves no such document): %s"
                % (name, "; ".join(problems))]
    out = []
    run_id, run_dir, slice_name, build_doc, workspace = run_block(name, doc)
    if run_id != visit["run_id"]:
        out.append("it names the run %r, not this visit's %r" % (run_id, visit["run_id"]))
    if not _same_dir(run_dir, visit["run_dir"]):
        out.append("it names the run directory %r, not this visit's %r" % (run_dir, visit["run_dir"]))
    if slice_name is not None and slice_name != facts["slice"]:
        out.append("it is for slice %r, not %r" % (slice_name, facts["slice"]))
    if build_doc is not None and build_doc != facts["doc"]:
        out.append("it is for the doc %r, not %r" % (build_doc, facts["doc"]))
    if workspace is not None and not _same_dir(workspace, facts["workspace"]):
        out.append("it is for the workspace %r, not %r" % (workspace, facts["workspace"]))
    stated, version = named_station(name, doc)
    if stated != name:
        out.append("it names the station %r, not %s" % (stated, name))
    if name == "recheck-v2" and doc.get("status") in RECHECK_GOES_ON and (slice_name is None or build_doc is None):
        out.append("its checklist names no slice or no doc, so it cannot be this visit's")
    if (version is not None or name == "recheck-v2") and version != identity["version"]:
        out.append("its plugin version %r is not the version of the station visited (%r)" % (version,
                                                                                            identity["version"]))
    if facts["report_only"]:
        if name == "build-v2" and not (doc.get("report_only") and doc.get("wrote_nothing")):
            out.append("this ship run is report-only and the build-v2 result is not a report-only one that wrote "
                       "nothing")
        if name == "signoff-v2" and not (doc.get("report_only") and doc.get("writes_none")):
            out.append("this ship run is report-only and the signoff-v2 result is not a report-only one that wrote "
                       "nothing")
        if name == "recheck-v2" and any((w or {}).get("kind") != "run_artifact" for w in doc.get("records_written")
                                        or []):
            out.append("this ship run is report-only and recheck-v2 (which has no report-only mode) wrote outside its "
                       "run directory")
    return out


# recheck-v2's statuses that go on with the loop: each carries a checklist naming its slice and doc. Every other status
# (`missing_input`, `stale_source`, `verifier_unavailable`, `recording_failed`, `stopped`) carries its own envelope,
# with no checklist where its schema gives none, and is bound to the visit by its run block alone; it ends the run
# `recheck-stopped` (the E15 lane contract A30 (2), contract section 3.4)
RECHECK_GOES_ON = ("completed", "nothing_open")

BUILD_WORDS = {"completed": "COMPLETE", "checks_not_passed": "PARTIAL", "not_complete": "PARTIAL",
               "answer_refused": "STOPPED", "stopped": "STOPPED"}


def outcome(name, doc):
    """What ship-v2 reads of a station's result: {"status", "word", ...}. Never a judgment: the station's own words."""
    status = doc.get("status")
    if name == "build-v2":
        word = BUILD_WORDS.get(status, "STOPPED")
        if status == "not_complete" and ((doc.get("answer") or {}).get("claimed_status") == "stopped"):
            word = "STOPPED"
        return {"status": status, "word": word, "complete": status == "completed"}
    if name == "signoff-v2":
        stopped = status != "completed" or bool(doc.get("answer_refused")) or doc.get("refusal_reason") is not None
        verdict = doc.get("verdict") or doc.get("verdict_stated")
        findings = [{"id": f.get("finding_id") or "at:%s" % f.get("location"), "severity": f.get("severity"),
                     "location": f.get("location"), "claim": f.get("claim")} for f in doc.get("findings") or []]
        return {"status": status, "word": status if stopped else (verdict or "signed off"), "stopped": stopped,
                "verdict": verdict, "findings": findings, "wrote_nothing": bool(doc.get("writes_none"))}
    stopped = status not in RECHECK_GOES_ON
    result = doc.get("result")
    if status == "nothing_open":
        word = "nothing open"
    elif stopped:
        word = status
    else:
        word = (result or "").replace("_", " ").upper()
    return {"status": status, "word": word, "stopped": stopped, "all_clear": status == "nothing_open" or
            result == "all_clear"}
