"""Shared facts the Codex adapter helpers of this core read from harness records.

Not a CLI. Copied from the recheck-v2 pilot's `adapters/codex/turns.py` (E9 lane R and the sealed
bench's SB-2, SB-8 and SB-12 repairs) and cut down to what the build and signoff cores need: the
executor's own rollout, found by `CODEX_THREAD_ID` under the sessions root of the home this helper
is INSTALLED in (E9-40), refused under `CODEX_HOME` (E9-36), refused when this process could append
to it (E9-37) unless the sealed bench's wall witness holds (SB-8), and the facts its
`session_meta` and `turn_context` records carry. No turn map: neither core takes a user-channel
field. Byte-identical in `build-v2` and `signoff-v2`; the core is read from this file's location.

Python 3.9, standard library only, no network, no model call, nothing written.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HARNESS = "codex-cli"
HERE = Path(__file__).resolve().parent
CORE = HERE.parent.parent.name                     # <plugin>/skills/<core>/adapters/codex
PREFIX = re.sub(r"[^A-Z0-9]", "_", CORE.upper())
TEST_FLAG = PREFIX + "_ADAPTER_TEST"
RECORD_VAR = PREFIX + "_ADAPTER_RECORD"
WALL_MARKER = "sandbox-exec"

# Ruling E9-3's Codex map as the pilot's lane settled it (E10-62), PROVISIONAL: each id Tony
# pinned is class `opus` with `floor_met` true; every other id is `unknown` with `floor_met` null
# and is never elevated. Each lane keeps its own map.
FLOOR_MAP = {"gpt-6-astra": "opus", "gpt-5.6-sol": "opus"}
UNKNOWN_CLASS = "unknown"


class Missing(Exception):
    """A harness record or binary this helper needs is absent: exit 3."""


class Usage(Exception):
    """A usage slip the parser could not see: exit 2."""


class JsonParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        sys.stdout.write(json.dumps({"help": self.format_help()}) + "\n")

    def error(self, message):
        sys.stderr.write("%s: %s\n" % (self.prog, message))
        raise SystemExit(2)


def parser(prog, description, epilog):
    return JsonParser(prog=prog, description=description, epilog=epilog,
                      formatter_class=argparse.RawDescriptionHelpFormatter)


def run(prog, main):
    """One JSON document on stdout, diagnostics on stderr, exit 0/2/3/1 (A7a)."""
    try:
        document = main()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    except Usage as exc:
        sys.stderr.write("%s: %s\n" % (prog, exc))
        return 2
    except Missing as exc:
        sys.stderr.write("%s: %s\n" % (prog, exc))
        sys.stdout.write(json.dumps({"error": str(exc), "exit": 3}) + "\n")
        return 3
    except Exception as exc:  # noqa: BLE001 - JSON, never a traceback
        sys.stderr.write("%s: %s: %s\n" % (prog, type(exc).__name__, exc))
        sys.stdout.write(json.dumps({"error": "%s: %s" % (type(exc).__name__, exc),
                                     "exit": 1}) + "\n")
        return 1
    sys.stdout.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    return 0


def codex_version():
    """`codex --version`'s last token (it prints `codex-cli <version>`)."""
    try:
        out = subprocess.run(["codex", "--version"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    except OSError as exc:
        raise Missing("missing binary: codex is not on PATH (%s)" % exc)
    text = out.stdout.decode("utf-8", "replace").strip()
    if out.returncode != 0 or not text:
        raise Missing("codex --version failed (exit %s)" % out.returncode)
    return text.splitlines()[0].split()[-1]


def read_records(path):
    try:
        with open(str(path), encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
    except FileNotFoundError:
        raise Missing("absent harness record: %s" % path)


# ---- the sealed bench's wall witness (SB-2, SB-12 N4), the pilot's code unchanged ----------

def wall_refuses(path):
    if not path:
        return False, "the wall probe names no path"
    try:
        with open(path, "rb") as handle:
            handle.read(1)
    except PermissionError as exc:
        return True, "the probe read was refused: %s" % exc
    except OSError as exc:
        return False, "the probe read failed for another reason: %s" % exc
    return False, "the probe read SUCCEEDED, so no wall refused it"


def applied_sandbox():
    try:
        import ctypes
        import ctypes.util
    except ImportError as exc:
        return None, "ctypes is unavailable here: %s" % exc
    try:
        library = ctypes.CDLL(ctypes.util.find_library("System") or "/usr/lib/libSystem.B.dylib")
        check = library.sandbox_check
    except (OSError, AttributeError) as exc:
        return None, "sandbox_check is unavailable in libsystem here: %s" % exc
    check.restype = ctypes.c_int
    check.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint64]
    try:
        value = check(os.getpid(), None, 0)
    except Exception as exc:  # noqa: BLE001
        return None, "sandbox_check could not be called: %s" % exc
    return bool(value), "sandbox_check(getpid(), NULL, 0) = %s" % value


def wall_witness():
    """Declared, applied, and refusing: all three halves or no witness (SB-2, SB-12 N4)."""
    if os.environ.get("RECHECK_HARNESS_SANDBOX") != WALL_MARKER:
        return False, "RECHECK_HARNESS_SANDBOX does not declare %s" % WALL_MARKER
    applied, how = applied_sandbox()
    if not applied:
        return False, "no sandbox policy is applied to this process: %s" % how
    refused, why = wall_refuses(os.environ.get("RECHECK_WALL_PROBE"))
    if not refused:
        return False, "the wall does not refuse: %s" % why
    return True, "a sandbox policy is applied (%s) and %s" % (how, why)


WALL_SANDBOX_NOTE = ("confined by the launcher's %s wall (SB-2), which is the sandbox here "
                     "because Codex's own is off; the executor rollout is writable by the "
                     "session under it" % WALL_MARKER)


# ---- the executor's own rollout (E9-31, E9-36, E9-37, E9-40) --------------------------------

def installed_home():
    """E9-40: the resolved helper path, never the environment, selects the home."""
    helper = Path(__file__).resolve()
    for ancestor in helper.parents:
        if ancestor.name == "cache" and ancestor.parent.name == "plugins":
            return ancestor.parent.parent
    for ancestor in helper.parents:
        if ancestor.name == CORE and ancestor.parent.name == "skills":
            home = ancestor.parent.parent
            if home.parent.name != "plugins":      # a source plugin's skills/ is packaging
                return home
    return None


def locate(workspace=None):
    """(rollout path, note, discovery). The note is set when a writable rollout was accepted."""
    home_root = installed_home()
    if home_root is None:
        override = os.environ.get(RECORD_VAR)
        if os.environ.get(TEST_FLAG) == "1" and override:
            return Path(override).resolve(), None, "fixture interface: %s under %s=1" % (
                RECORD_VAR, TEST_FLAG)
        raise Missing("absent harness record: helper outside an installed location: %s (E9-40)"
                      % Path(__file__).resolve())
    root = home_root / "sessions"
    thread = os.environ.get("CODEX_THREAD_ID", "").strip()
    if not thread:
        raise Missing("absent harness record: no CODEX_THREAD_ID under %s (E9-31/E9-40)" % root)
    if not re.fullmatch(r"[A-Za-z0-9-]+", thread):
        raise Usage("invalid CODEX_THREAD_ID")
    home = os.environ.get("CODEX_HOME")
    resolved_home = Path(home).expanduser().resolve() if home else None

    def outside_home(path):
        resolved = path.resolve()
        if resolved_home is not None and (resolved == resolved_home
                                          or resolved_home in resolved.parents):
            raise Missing("refused executor rollout path under CODEX_HOME: %s (E9-36)" % resolved)
        return resolved

    root = outside_home(root)
    found, writable = set(), set()
    if root.is_dir():
        for path in root.rglob("rollout-*" + thread + ".jsonl"):
            resolved = outside_home(path)
            try:
                open(str(resolved), "ab").close()
            except PermissionError:
                found.add(resolved)
            except OSError as error:
                raise Missing("executor rollout append check failed: %s: %s (E9-37)"
                              % (resolved, error))
            else:
                witness, _why = wall_witness()
                if not witness:
                    raise Missing("writable executor rollout refused: %s (E9-37)" % resolved)
                found.add(resolved)
                writable.add(resolved)
    if len(found) > 1:
        raise Missing("ambiguous executor rollout for thread %s under %s" % (thread, root))
    if not found:
        raise Missing("absent harness record: no rollout named by CODEX_THREAD_ID %s under %s"
                      % (thread, root))
    one = next(iter(found))
    return one, (WALL_SANDBOX_NOTE if one in writable else None), (
        "CODEX_THREAD_ID under the sessions root of the home this helper is installed in (E9-40)")


def facts(records):
    meta, context = {}, {}
    for record in records:
        if record.get("type") == "session_meta":
            meta = record.get("payload", {})
        if record.get("type") == "turn_context":
            context = record.get("payload", {})
    if not meta or not context:
        raise Missing("absent session_meta or turn_context record")
    return meta, context


def model_facts(context, records=()):
    """id, floor_class, floor_met from `turn_context.model`; effort and window beside them."""
    name = context.get("model")
    if not name:
        raise Missing("absent model in turn_context")
    klass = FLOOR_MAP.get(name, UNKNOWN_CLASS)
    model = {"id": name, "floor_class": klass,
             "floor_met": True if klass != UNKNOWN_CLASS else None}
    extra = {}
    effort = (context.get("effort")
              or (context.get("collaboration_mode") or {}).get("settings", {}).get(
                  "reasoning_effort"))
    if effort:
        extra["effort"] = effort
    for record in records:
        payload = record.get("payload", {})
        if record.get("type") == "event_msg" and payload.get("type") == "token_count":
            window = (payload.get("info") or {}).get("model_context_window")
            if isinstance(window, int):
                extra["context_tokens"] = window
    return model, extra


def interaction_mode(meta):
    """E9-33/E9-36: `codex exec` is headless; the CLI's own originator is interactive."""
    originator = meta.get("originator")
    mode = {"codex_exec": "headless", "codex_cli_rs": "interactive"}.get(originator)
    if mode is None:
        raise Missing("unknown session_meta.originator: %r" % (originator,))
    return mode, "session_meta.originator %s" % originator


def sandbox_of(context, wall_note):
    policy = context.get("sandbox_policy") or {}
    sandbox = policy.get("type")
    if not sandbox:
        raise Missing("absent sandbox_policy in turn_context")
    home = Path(os.environ.get("CODEX_HOME", "/absent")).resolve()
    roots = [Path(x).resolve() for x in policy.get("writable_roots", [])]
    if sandbox == "workspace-write" and any(home == r or r in home.parents for r in roots):
        sandbox = "workspace-write plus the isolated home"
    if policy.get("network_access") is True:
        sandbox += ", network on"
    if wall_note:
        sandbox += "; " + wall_note
    return sandbox


def entry_kind(home):
    real = str(Path(__file__).resolve())
    if "/plugins/cache/" in real:
        return "plugin"
    if home is not None and ("/skills/%s/" % CORE) in real:
        return "host skill"
    return "explicit path"


def check_workspace(meta, workspace):
    if workspace is None:
        return "not checked: no --workspace was given"
    if Path(meta.get("cwd", "")).resolve() != Path(workspace).resolve():
        raise Missing("the rollout's cwd %s is not the workspace %s" % (meta.get("cwd"),
                                                                        workspace))
    return "session_meta.cwd is the workspace"
