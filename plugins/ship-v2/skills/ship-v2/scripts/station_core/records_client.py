# Origin (E13 lane contract, ruling E13-3; lane B brief, "The pattern"): everything from the
# docstring below to the end of this file is a copy of the qualified recheck pilot's
# plugins/recheck-v2/skills/recheck-v2/scripts/recheck_core/records_client.py, taken from the
# branch point of this lane, commit a80cdd04432c5f4662ed415d6a72d54f9b8208c1, and moved with the
# pilot's file once since: E13 amendment A7 (records interface version 2) changed that file's
# docstring and KNOWN_INTERFACE_VERSIONS, and this copy took the same bytes. The records wiring is
# copied, not reinvented. `tests/test_records_client.py` compares
# the two files byte for byte and fails when they differ, the way the records component holds its
# own copied region (plugins/records/scripts/tests/test_parity.py).
#
# Two module constants in the copy belong to the pilot and are NOT this station's: STATION
# ("recheck-v2") and NO_RECORDS_HOOK ("RECHECK_TEST_NO_RECORDS"). This station never reads them;
# build_core/records_link.py holds its own STATION ("build-v2") and its own test hook, and opens
# the client through this module's `open_client` with its own plugin root. Changing either
# constant here would break the byte comparison, which is the point: the copy moves only when the
# pilot's file moves.
"""Reaching the records component (E13 slice 1, brief 3.1; records interface version 2).

The pilot never opens a log file, never imports `records_core`, and never copies the component's
code: it resolves the component root with the interface's own snippet, confirms the interface
version with `component-identity`, and then runs `<root>/scripts/records.py` as a subprocess, one
function per command it uses. Every caller value is an argv item; nothing is ever pasted into
shell text.

The station plugin root the resolver is given is derived from THIS FILE's location, not from
`--skill-root`, which is a test hook for reference loading alone: route 3a must keep resolving
when a test points the references at a copy.

Records interface version 2 since E13 amendment A7 (Astra's F10): the component's A4 response
shapes (`native_rendered` on an import report, the review block on `render`) are version 2, which
is what this client reads. A component at version 1 is refused like any other version.

Refusals. A component that cannot be found, or that speaks an interface version this station was
not written against, is the pilot's exit 3 shape: one line on stderr, nothing on stdout
(`ComponentUnavailable`). Every other refusal of a command is a `RecordsRefusal` carrying the
component's exit code, its `error`, its `reason`, and the whole body, which the driver maps to the
pilot's own statuses (brief 3.4, pilot contract section 9 as amended in Appendix B):

    component exit 4 (invalid)             -> recording_failed   (the event the pilot built was refused)
    component exit 5 (ambiguous_identity)  -> missing_input      (an ambiguity the run cannot decide, RB6)
    component exit 6 (stale_source)        -> stale_source       (a clear against another revision)
    component exit 7 (conflict)            -> recording_failed   (a moved head or a live lock; never retried, never merged)

Test hook (honored only with RECHECK_TEST=1): RECHECK_TEST_NO_RECORDS=1 behaves as if no component
were installed anywhere, which is the real failure rather than a simulation of the message.
"""

# ---- BEGIN resolver snippet (copied from the records component's references/interface.md, unchanged) ----
import json
import os
import subprocess
import sys

def refusal_line(value):
    return "".join("\\u%04x" % ord(ch) if ord(ch) < 32 or ord(ch) == 127 else ch for ch in str(value))

COMPONENT = "records"                                    # the component's plugin name
MANIFEST = os.path.join(".claude-plugin", "plugin.json")
DIGITS = "0123456789"


def version_key(name):
    """(int, ...) for a dotted-integer name, else None. Text is never compared as text.

    A component with a leading zero (`01`, `1.00`) is not a dotted integer: it would give two
    differently named folders one key, and then the highest version would not be one folder.
    """
    parts = name.split(".")
    for part in parts:
        if not part or [ch for ch in part if ch not in DIGITS]:
            return None
        if len(part) > 1 and part[0] == "0":
            return None
    return tuple(int(part) for part in parts)


def installed_versions(base):
    """Route 3b: (accepted, rejected) under `base`, one folder per version.

    accepted is [(version key, folder)]; rejected is [(folder, why)], both in name order.
    """
    accepted, rejected = [], []
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return accepted, rejected
    for name in names:
        folder = os.path.join(base, name)
        if not os.path.isdir(folder):
            continue
        manifest = os.path.join(folder, MANIFEST)
        if not os.path.isfile(manifest):
            rejected.append((folder, "no plugin.json"))
            continue
        try:
            with open(manifest, encoding="utf-8") as fh:
                manifest_body = json.load(fh)
                if not isinstance(manifest_body, dict):
                    raise ValueError("plugin.json is not an object")
                version = manifest_body.get("version")
        except (ValueError, OSError):
            rejected.append((folder, "plugin.json unreadable"))
            continue
        if not isinstance(version, str) or not version:
            rejected.append((folder, "no version"))
        elif version != name:
            rejected.append((folder, "name differs from version %s" % version))
        elif version_key(name) is None:
            rejected.append((folder, "version not dotted integers"))
        elif not os.path.isfile(os.path.join(folder, "scripts", "records.py")):
            rejected.append((folder, "no scripts/records.py"))
        else:
            accepted.append((version_key(name), folder))
    return accepted, rejected


def records_root(argument=None, station_plugin_root=None, environ=None):
    """Routes 1, 2, 3a, 3b, in that order. Raises LookupError naming every candidate."""
    environ = os.environ if environ is None else environ
    looked = []
    for candidate in (argument, environ.get("RECORDS_ROOT")):
        if not candidate:
            continue
        looked.append(candidate)
        if os.path.isfile(os.path.join(candidate, "scripts", "records.py")):
            return candidate
    if station_plugin_root:
        beside = os.path.join(station_plugin_root, os.pardir, COMPONENT)          # route 3a
        looked.append(beside)
        if os.path.isfile(os.path.join(beside, "scripts", "records.py")):
            return beside
        base = os.path.join(station_plugin_root, os.pardir, os.pardir, COMPONENT)  # route 3b
        looked.append(base if os.path.isdir(base) else "%s (no such directory)" % base)
        accepted, rejected = installed_versions(base)
        for folder, why in rejected:
            looked.append("%s (%s)" % (folder, why))
        if accepted:
            return max(accepted, key=lambda pair: pair[0])[1]
    raise LookupError("missing dependency: records component (looked in: %s)"
                      % (", ".join(looked) or "nothing given"))


def confirm_interface(root, known_versions, python=None):
    """The picked root must report an interface version the caller knows. Returns it."""
    command = [python or sys.executable, os.path.join(root, "scripts", "records.py"),
               "component-identity"]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version = None
    if proc.returncode == 0:
        try:
            version = json.loads(proc.stdout.decode("utf-8"))["interface_version"]
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            version = None
    if type(version) is not int:
        raise LookupError("missing dependency: records component at %s did not report an "
                          "interface version" % root)
    if version not in known_versions:
        raise LookupError("missing dependency: records component at %s speaks interface version "
                          "%s, not %s" % (root, version,
                                          ", ".join(str(known) for known in known_versions)))
    return version
# ---- END resolver snippet ----


SNIPPET_BEGIN = "# ---- BEGIN resolver snippet (copied from the records component's references/interface.md, unchanged) ----"
SNIPPET_END = "# ---- END resolver snippet ----"

STATION = "recheck-v2"                       # actor.station on every event this pilot writes
KNOWN_INTERFACE_VERSIONS = (2,)             # E13 amendment A7: A4's response shapes are version 2
NO_RECORDS_HOOK = "RECHECK_TEST_NO_RECORDS"  # gated by RECHECK_TEST=1


def snippet_region(block):
    """The region of the interface's python snippet this module copies: `import json` through the
    end of `confirm_interface`, without the shebang, the module docstring, or the `__main__` guard."""
    lines = block.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("import json"))
    end = next(i for i, line in enumerate(lines) if line.startswith("if __name__"))
    return "\n".join(lines[start:end])


def station_plugin_root():
    """`plugins/recheck-v2` from this file: recheck_core -> scripts -> skills/recheck-v2 -> skills -> the plugin."""
    scripts = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill = os.path.dirname(scripts)
    return os.path.dirname(os.path.dirname(skill))


class ComponentUnavailable(RuntimeError):
    """The pilot's exit 3: the component is missing or speaks another interface version."""


class RecordsRefusal(RuntimeError):
    """A command of the component refused. Carries its exit code, `error`, `reason`, and body."""

    def __init__(self, command, code, body, stderr=""):
        self.command, self.exit_code, self.body = command, code, dict(body or {})
        self.error = self.body.get("error")
        self.reason = self.body.get("reason") or (stderr.strip().split("\n")[-1] if stderr.strip() else "")
        self.stderr = stderr
        RuntimeError.__init__(self, "records %s refused (exit %d): %s" % (command, code, self.reason or self.error or ""))

    def sentence(self):
        """The component's own explanation, for a pilot stop reason."""
        return self.reason or self.error or ("records %s exited %d" % (self.command, self.exit_code))


class Client:
    """One resolved, confirmed component root. Every method runs one subprocess."""

    def __init__(self, root, interface_version, python=None):
        self.root = root
        self.interface_version = interface_version
        self.python = python or sys.executable
        self.script = os.path.join(root, "scripts", "records.py")

    # ---- the one place a command line is built -------------------------------------------

    def _run(self, command, args):
        argv = [self.python, self.script, command] + [str(a) for a in args]
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        body = None
        if out.strip():
            try:
                body = json.loads(out)
            except ValueError:
                body = None
        if proc.returncode != 0:
            raise RecordsRefusal(command, proc.returncode, body, proc.stderr.decode("utf-8", "replace"))
        if not isinstance(body, dict):
            raise RecordsRefusal(command, 1, {"reason": "the component printed no JSON document"},
                                 proc.stderr.decode("utf-8", "replace"))
        return body

    # ---- the commands the pilot uses ------------------------------------------------------

    def component_identity(self):
        return self._run("component-identity", [])

    def identity(self, workspace):
        return self._run("identity", ["--workspace", workspace])

    def verify(self, workspace, doc):
        return self._run("verify", ["--workspace", workspace, "--doc", doc])

    def events(self, workspace, doc, finding=None, kind=None, from_seq=None):
        args = ["--workspace", workspace, "--doc", doc]
        if finding is not None:
            args += ["--finding", finding]
        if kind is not None:
            args += ["--kind", kind]
        if from_seq is not None:
            args += ["--from", from_seq]
        return self._run("events", args)

    def state(self, workspace, doc, slice_name=None, at_source=None):
        args = ["--workspace", workspace, "--doc", doc]
        if slice_name is not None:
            args += ["--slice", slice_name]
        if at_source is not None:
            args += ["--at-source", at_source]
        return self._run("state", args)

    def render(self, workspace, doc, run_id):
        return self._run("render", ["--workspace", workspace, "--doc", doc, "--run-id", run_id])

    def mirrors(self, workspace, doc):
        return self._run("mirrors", ["--workspace", workspace, "--doc", doc])

    def import_legacy(self, workspace, doc, dry_run=False, resolutions=None):
        args = ["--workspace", workspace, "--doc", doc]
        if resolutions is not None:
            args += ["--resolutions", resolutions]
        if dry_run:
            args.append("--dry-run")
        return self._run("import-legacy", args)

    def append(self, workspace, doc, events, expect_head, scratch_dir):
        """Write `events` to a file under `scratch_dir` (never the workspace) and append them all
        or none. `expect_head` is the head the caller read at plan time."""
        path = os.path.join(scratch_dir, "records-events.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(list(events), fh, ensure_ascii=False)
            fh.write("\n")
        return self._run("append", ["--workspace", workspace, "--doc", doc, "--events", path,
                                    "--expect-head", expect_head])


def _hooked_off(environ):
    return environ.get("RECHECK_TEST") == "1" and environ.get(NO_RECORDS_HOOK) == "1"


def open_client(records_root=None, environ=None, python=None, plugin_root=None):
    """Resolve, confirm, and return the Client. Raises ComponentUnavailable with the interface's
    own one-line message when nothing is found or the version is not one this station knows."""
    environ = os.environ if environ is None else environ
    station = plugin_root or station_plugin_root()
    if _hooked_off(environ):
        raise ComponentUnavailable("missing dependency: records component (looked in: "
                                   "%s (RECHECK_TEST_NO_RECORDS=1))" % station)
    try:
        root = records_root_of(records_root, station, environ)
        version = confirm_interface(root, list(KNOWN_INTERFACE_VERSIONS), python=python or sys.executable)
    except LookupError as refusal:
        raise ComponentUnavailable(refusal_line(refusal))
    return Client(root, version, python=python)


def records_root_of(argument, station, environ):
    """The snippet's four lookups, with this module's own station plugin root."""
    return records_root(argument, station, environ)
