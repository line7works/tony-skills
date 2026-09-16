#!/usr/bin/env python3
"""The recheck-v2 E10 trial runner (lane S, `docs/plans/2026-09-14-recheck-v2-e10-runner.md`).

    runner.py <subcommand> [options]

One driver for the pilot campaign: it stages the checkout, installs and verifies the three
harness setups in their three homes each, probes their launched environments, plans a
campaign, runs one trial end to end, grades it against the answer key, runs the routing and
continuation trials, scans every record for credential shapes, and reports.

Interface (ruling A7a, E10-9): one JSON document on stdout and nothing else; every diagnostic
on stderr; exit 0 success, 2 a usage slip, 3 a missing binary, setup or record, 1 anything
else. Every subcommand runs from any working directory and refuses to overwrite a record.

Python 3.9 syntax, standard library only. The grading step calls the core's
`validate-result.py` through `uv run` the way the E7 check runner calls things, and imports
`evals/checks/match.py` from its path.

The wall (lane contract section 3): `evals/answer-key/` and `evals/trigger-set/held-out/` are
opened by `grade`, `routing-score`, and the one-entry text lookup `routing` needs, and by
nothing else. Every launch path runs with both directories unreadable (a test proves it).
"""
import argparse
import errno
import glob
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import traceback
import uuid

# --------------------------------------------------------------------------- exits


class Usage(Exception):
    """Exit 2: the caller's command is wrong."""


class Missing(Exception):
    """Exit 3: a binary, a setup, or a record is not there."""


class Failure(Exception):
    """Exit 1: anything else."""


EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_MISSING = 0, 1, 2, 3

# --------------------------------------------------------------------------- roots

RUNNER_DIR = os.path.dirname(os.path.abspath(__file__))
EVALS_DIR = os.path.dirname(RUNNER_DIR)
PLUGIN_DIR = os.path.dirname(EVALS_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(PLUGIN_DIR))
SKILL_DIR = os.path.join(PLUGIN_DIR, "skills", "recheck-v2")
FIXTURES_DIR = os.path.join(EVALS_DIR, "fixtures")
CHECKS_DIR = os.path.join(EVALS_DIR, "checks")
KEY_DIR = os.path.join(EVALS_DIR, "answer-key")
TRIGGER_TUNING = os.path.join(EVALS_DIR, "trigger-set", "requests.json")
TRIGGER_HELDOUT = os.path.join(EVALS_DIR, "trigger-set", "held-out", "requests.json")
TRIAL_DEFAULTS = os.path.join(EVALS_DIR, "trial-defaults.json")
# The pilot root. The tests relocate it, under their own flag, so no test can install into,
# read from or scan a real pilot home (the suite found the machine's own `codex plugin list`
# through one of them). Nothing else honours the override: without `RECHECK_RUNNER_TEST_PILOT=1`
# the real root is used whatever the environment says.
PILOT_ROOT = os.path.join(os.path.expanduser("~"), ".local", "share", "skills-v2-pilot")
if os.environ.get("RECHECK_RUNNER_TEST_PILOT") == "1" and os.environ.get("RECHECK_PILOT_ROOT"):
    PILOT_ROOT = os.path.abspath(os.environ["RECHECK_PILOT_ROOT"])
CAMPAIGN_ROOT = os.path.join(PILOT_ROOT, "e10")

HARNESSES = ("claude-code", "codex", "opencode")
CONDITIONS = ("available", "absent")
HOMES = ("available", "absent", "routing")
# E10-13: the five v1 back-half stations the routing profile blocks.
BLOCKED_PLUGINS = ("signoff", "recheck", "vertical", "inspect", "ship")

# --------------------------------------------------------------- the model and effort (E10-62)
#
# Tony pinned each setup to one model and, where the harness takes one, one effort. The plan
# carries the pair per setup; nothing here is a default for a setup that named none, and no
# label anywhere stands in for a record (E10-19): `model.json.configured` is what the launcher
# was TOLD and the native witness beside it is what the harness recorded.
#
# The keys a setup entry of `plan.json` may carry. An unknown key is refused rather than
# ignored (E10-62 item 1): a misspelled `effort` that a plan silently dropped would run the
# whole lane at the harness's own default and nothing in the record would say so.
SETUP_KEYS = ("name", "harness", "model", "effort")
# What each harness accepts as an effort, and what it records.
#   claude-code  `claude --help` on 2.1.272 prints
#                "--effort <level>  Effort level for the current session (low, medium, high,
#                xhigh, max)" (measured 2026-09-15, this machine).
#   codex        `model_reasoning_effort`, the six values the readers roster's two codex-exec
#                rows carry (`plugins/readers/skills/readers/assets/roster.json`, `efforts`).
#                Codex 0.154.0 validates none of them at parse time (measured: `codex -c
#                model_reasoning_effort=bogus plugin list` exits 0), so the plan is the gate.
#   opencode     none exists on 1.18.31 (E10-26), so an `effort` on an OpenCode setup is
#                refused rather than silently dropped.
HARNESS_EFFORTS = {
    "claude-code": ("low", "medium", "high", "xhigh", "max"),
    "codex": ("low", "medium", "high", "xhigh", "max", "ultra"),
    "opencode": (),
}

# --------------------------------------------------------------------------- environment

# E10-7. Names the runner passes; everything else is dropped by starting from `env -i`.
#
# `USER` is the one name E10-7's "measure which variable it needs, add that one name with the
# measurement beside it" clause added. Measured 2026-09-15 on Claude Code 2.1.272 with four
# short sessions from `env -i` (the records are in the builder's scratch, `authprobe`):
#   the seven names alone            -> `"Not logged in · Please run /login"`, cost 0
#   the seven plus USER and LOGNAME  -> answered, cost 0.7100425 (a cold prompt cache)
#   the seven plus USER              -> answered `ok`, cost 0.011564
#   the seven plus LOGNAME           -> `"Not logged in · Please run /login"`, cost 0
# So the harness reaches its Keychain item (`security find-generic-password -s
# "Claude Code-credentials"`, class genp) only when `USER` is set; `LOGNAME` does not do it.
# `USER` names the process's own identity, carries no credential, and matches no banned shape.
ALLOWED_ENV = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "TERM", "SHELL", "USER")
# The banned shapes a probe record is checked against.
BANNED_ENV_RE = re.compile(
    r"^(CLAUDE_CODE_.*|CLAUDECODE|CODEX_.*|OPENROUTER_API_KEY|OPENAI_API_KEY"
    r"|ANTHROPIC_API_KEY|.*_TOKEN|.*_SECRET|.*_KEY|AWS_.*|GH_.*|GITHUB_.*"
    r"|NOTION_.*|SLACK_.*|SSH_.*)$"
)
# E10-20: the one name `install` passes, to the OpenCode install script alone.
INSTALL_CREDENTIAL = "OPENROUTER_API_KEY"
# E10-7's clause "plus the variables the setup's own launcher sets for itself", written out.
# These are the ONLY names matching a banned shape that any child of the runner may carry, and
# each says which measurement put it there. Every other banned name is a hard failure at the
# one environment boundary (E10-42), whatever the caller passes.
DECLARED_ENV = {
    # E9-25 and E10-7: the Codex home pointer. `setups/codex/launch.sh` sets it for its own
    # child; the runner sets it directly only for `codex plugin list` (the catalog capture,
    # no model) and for the `codex exec resume` of a compaction trial.
    "CODEX_HOME": "the Codex home pointer (E9-25, E10-7)",
    # E10-20: the one install-time credential, passed to one script, for three homes.
    INSTALL_CREDENTIAL: "the OpenCode install's one credential (E10-20)",
}
PATH_BINARIES = ("claude", "codex", "node", "uv", "git", "python3")
PATH_TAIL = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")

# E10-42: the names each harness sets in its OWN tool shells, below the boundary the runner
# controls. Measured 2026-09-15 (Claude Code 2.1.272, codex-cli 0.154.0 with
# `[features] shell_snapshot = false`, opencode-ai 1.18.31) and re-measured by every probe
# record the fix round writes. A banned name in a probe that is NOT on its harness's list
# fails that probe; a name on the list is recorded beside the probe that measured it.
HARNESS_CREATED_ENV = {
    "claude-code": (
        "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_SESSION_ATTENDED",
        "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
    ),
    # E9-25: the Codex launcher sets `CODEX_HOME` for the child by design; `GH_PAGER` is
    # Codex's own setting for the GitHub CLI and carries no secret (E10-30).
    # Measured 2026-09-15 by the fix round's own nine probes, from the session's own printed
    # `env | cut -d= -f1 | sort` (see `<campaign>/probes/codex-*/probe-*.json`): the Codex tool
    # shell carries 35 names, of which these nine match a banned shape. None is a credential —
    # `CODEX_HOME` is the home pointer (E9-25), `GH_PAGER` is Codex's own setting for the
    # GitHub CLI (E10-30), and the rest are Codex's own session instrumentation. No
    # `OPENROUTER_API_KEY`, `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` appears, so E9-38 holds on
    # this lane. The first build's list was short by five names and the gate caught it.
    "codex": ("CODEX_HOME", "CODEX_MANAGED_BY_NPM", "CODEX_SANDBOX",
              "CODEX_SANDBOX_NETWORK_DISABLED", "GH_PAGER",
              "CODEX_CI", "CODEX_MANAGED_PACKAGE_ROOT", "CODEX_SESSION_ID",
              "CODEX_THREAD_ID", "CODEX_VERSION"),
    # E9-38 holds on this lane: nothing banned in an OpenCode tool shell.
    "opencode": (),
}
# The names the platform and the two shims add BELOW the boundary a parent can control
# (measured: /bin/sh adds PWD and SHLVL, CoreFoundation adds __CF_USER_TEXT_ENCODING, the
# /usr/bin/python3 xcrun shim adds SDKROOT, CPATH, LIBRARY_PATH and MANPATH). None is a
# banned shape; they are listed so a probe's "other names" set is the harness's own.
PLATFORM_ADDED_ENV = ("__CF_USER_TEXT_ENCODING", "PWD", "SHLVL", "SDKROOT", "CPATH",
                      "LIBRARY_PATH", "MANPATH", "OLDPWD", "_")

# The credential shapes `scan` looks for (the OpenCode scanner's shapes plus JWT and sk-).
#
# E10-37 / E10-52: every prefix needs a boundary before it, and an assignment delimiter IS a
# boundary. Codex's rollouts carry opaque base64 metadata blobs (the false hit of E10-37 sat
# in `/payload/encrypted_content` at verifier rollout line 26) in which `sk-` occurs
# mid-token, and a real key never sits inside a longer base64 run — but `=` is base64's
# padding character and only ever ends a run, so `KEY=sk-...` and `"key": "sk-..."` are
# credentials, not continuations. `=`, `"`, `'`, `:` and whitespace are therefore boundaries;
# the reviewer's `OPENROUTER_API_KEY=<key>` example was missed for exactly this reason.
BOUNDARY = r"(?<![A-Za-z0-9_/+-])"
CREDENTIAL_SHAPES = (
    ("openrouter-key", re.compile(BOUNDARY + r"sk-or-v1-[0-9a-f]{32,}")),
    ("anthropic-key", re.compile(BOUNDARY + r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("provider-key", re.compile(BOUNDARY + r"sk-[A-Za-z0-9_-]{40,}")),
    ("jwt", re.compile(BOUNDARY + r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
)


def which(name):
    """The resolved location of a binary, or None."""
    return shutil.which(name)


def path_entries(require=True):
    """The fixed PATH list of E10-7, built from the resolved locations of the binaries."""
    entries, missing = [], []
    for name in PATH_BINARIES:
        found = which(name)
        if not found:
            missing.append(name)
            continue
        directory = os.path.dirname(os.path.realpath(found))
        # The realpath of a launcher can sit beside its symlink; keep both.
        for candidate in (os.path.dirname(found), directory):
            if candidate and candidate not in entries:
                entries.append(candidate)
    if missing and require:
        raise Missing("not on PATH: %s" % ", ".join(missing))
    for tail in PATH_TAIL:
        if tail not in entries:
            entries.append(tail)
    return entries


def allowlist_env(tmpdir, extra=None, require_binaries=True):
    """A child's whole environment: `env -i` plus exactly the allowed names (E10-7).

    `extra` adds the variables a setup's own launcher needs for itself (the pilot home
    pointers) and, for the OpenCode install alone, the one credential name of E10-20.
    """
    env = {
        "PATH": ":".join(path_entries(require=require_binaries)),
        "HOME": os.path.expanduser("~"),
        "TMPDIR": tmpdir,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "dumb",
        "SHELL": "/bin/zsh",
        "USER": os.path.basename(os.path.expanduser("~")),
    }
    for name, value in (extra or {}).items():
        env[name] = value
    return env


def allowlisted_names(env):
    """The names a `command.json` records (never values)."""
    return sorted(env)


# E10-42: ONE boundary. Every subprocess the runner starts — an install, a verify, a launch,
# a probe, a grade, a fixture listing, the held-out one-entry lookup, the self-test, and the
# detached campaign process itself — is built here. Nothing in this file calls
# `os.environ.copy()`; `run_cmd` refuses a child with no environment, so a new call site
# cannot inherit the session's environment by omission.
_TOOL_TMPDIR = [None]


def tool_tmpdir():
    """The TMPDIR the runner's own helper subprocesses get when no campaign supplies one."""
    if _TOOL_TMPDIR[0] is None:
        base = os.environ.get("RECHECK_RUNNER_TOOL_TMPDIR") or os.path.join(
            os.path.expanduser("~"), ".local", "share", "skills-v2-pilot", "runner-tmp")
        ensure_dir(base)
        _TOOL_TMPDIR[0] = base
    return _TOOL_TMPDIR[0]


def tool_env(extra=None, require_binaries=False):
    """The allowlisted environment for a helper the runner runs for itself (no harness)."""
    env = allowlist_env(tool_tmpdir(), extra=extra, require_binaries=require_binaries)
    # A helper that runs `uv` needs a cache it can write; it sits under the runner's own
    # TMPDIR so no campaign record and no home is touched.
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def banned_names(names):
    return sorted(n for n in names if BANNED_ENV_RE.match(n))


# --------------------------------------------------------------------------- small helpers


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_json(path, what=None):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (IOError, OSError) as exc:
        raise Missing("%s: %s" % (what or path, exc))
    except ValueError as exc:
        raise Failure("%s does not parse: %s" % (what or path, exc))


def write_json(path, document):
    ensure_dir(os.path.dirname(path))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def read_text(path, default=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (IOError, OSError):
        return default


def write_text(path, text):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path)


def rmtree(path):
    """Remove a tree without `rm -rf`.

    The Codex approval review rejects a command containing `rm -rf` even under
    `approval_policy=never` (lane contract section 5), and the runner is launched from inside
    a `codex exec`, so every removal goes through `shutil.rmtree`.
    """
    if os.path.islink(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.unlink(path)


def jsonl_lines(path):
    """Every JSON document on its own line, bad lines skipped."""
    out = []
    text = read_text(path)
    if not text:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# E10-6 fixes what `plugin_tree_sha256` and `setup_tree_sha256` mean: every file under the
# staged plugin with `__pycache__` excluded. Those two hashes keep that definition exactly, so
# a re-stage of unchanged content still produces the value the nine probe records are bound to;
# everything else takes the complete walk of E10-60 (10).
E10_6_TREE_EXCLUDED = (".git", "__pycache__")


def tree_sha256_of(root, exclude_dirs=(), follow_directory_links=True):
    """`<path>\\0<sha256>\\n` over every entry under root, sorted (the fixturelib shape).

    E10-60 (10): **every** entry. `__pycache__` and every other directory are walked, each
    directory contributes an entry of its own (so an empty directory appearing or going is a
    change), a symlink contributes its own target path as its content and, when it names a
    directory, that directory's contents are walked too under the link's own relative path — so
    a changed link, or a changed file behind it, changes the hash. The previous reader skipped
    `.git` and `__pycache__` and, because `os.walk` does not follow directory links, a directory
    link contributed nothing at all: a `run/` holding `__pycache__/evidence.txt` or
    `linked-verifier -> …` could be rewritten under a retained validation without moving the
    hash (the reviewer's adapted probe 10 measured both).

    `exclude_dirs` and `follow_directory_links=False` restore the older, narrower walk for the
    two hashes E10-6 defines; a file entry's bytes are identical either way, so the narrow walk
    still produces exactly the values it always did. A link that resolves to a directory already
    seen is recorded as a cycle and not walked again.
    """
    entries = []
    seen = set()

    def note(rel, digest):
        entries.append("%s\0%s\n" % (rel, digest))

    def walk(directory, prefix):
        real = os.path.realpath(directory)
        if real in seen:
            note(prefix or ".", "cycle:%s" % sha256_hex(real.encode("utf-8")))
            return
        seen.add(real)
        try:
            names = sorted(os.listdir(directory))
        except OSError as exc:
            note(prefix or ".", "unreadable:%s" % exc.errno)
            return
        for name in names:
            if name in exclude_dirs:
                continue
            full = os.path.join(directory, name)
            rel = os.path.join(prefix, name) if prefix else name
            if os.path.islink(full):
                note(rel, sha256_hex(os.readlink(full).encode("utf-8")))
                if follow_directory_links and os.path.isdir(full):
                    walk(full, rel)
                continue
            if os.path.isdir(full):
                if follow_directory_links:
                    # a directory of its own, so an empty one appearing is a change
                    note(rel, "dir")
                walk(full, rel)
                continue
            try:
                with open(full, "rb") as handle:
                    note(rel, sha256_hex(handle.read()))
            except (IOError, OSError) as exc:
                note(rel, "unreadable:%s" % exc.errno)
    walk(root, "")
    entries.sort()
    return sha256_hex("".join(entries).encode("utf-8"))


def run_cmd(argv, env=None, cwd=None, stdin=None, timeout=None, label=None, stdout_path=None,
            registry=None):
    """One child process: its status, its streams, its wall time.

    Never raises on a non-zero status; the caller decides. A timeout terminates the child's
    own process group (E10-14) after collecting whatever it wrote.

    `stdout_path` sends the child's stdout to that file instead of a pipe. Measured
    2026-09-15: `opencode debug skill` writes exactly 65,536 bytes into a pipe and the whole
    67,934 into a file, so its catalog capture goes through a file and the record is complete.
    """
    if env is None:
        # E10-42: one environment boundary, and no way to skip it by omission.
        raise Failure("run_cmd was called with no environment; every child goes through "
                      "allowlist_env (E10-7, E10-42): %s" % " ".join(argv[:3]))
    leaked = [n for n in banned_names(env) if n not in DECLARED_ENV]
    if leaked:
        raise Failure("the environment built for %s carries banned names: %s"
                      % (argv[0], ", ".join(leaked)))
    started = time.time()
    sys.stderr.write("$ %s\n" % " ".join(argv))
    sink = open(stdout_path, "wb") if stdout_path else None
    try:
        handle = subprocess.Popen(
            argv,
            env=env,
            cwd=cwd,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=sink or subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        # A binary that is not there is recorded, never an unhandled traceback; the caller
        # turns it into exit 3 where the contract asks for it (A7a).
        if sink:
            sink.close()
        if registry is not None:
            # E10-59 (1, 8): a reservation that never became a process is closed, or the
            # barrier would wait on a child that does not exist.
            registry.released("the binary could not be started: %s" % exc)
        message = "%s: %s" % (argv[0], exc)
        sys.stderr.write(message + "\n")
        return {"argv": argv, "label": label, "exit": 127, "timed_out": False,
                "wall_seconds": 0.0, "stdout": "", "stderr": message,
                "started_at": now_iso(), "ended_at": now_iso(), "binary_missing": True}
    if registry is not None:
        registry.started(handle.pid, argv)
    timed_out = False
    try:
        out, err = handle.communicate(
            input=stdin.encode("utf-8") if isinstance(stdin, str) else stdin, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(handle.pid)
        try:
            out, err = handle.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            handle.kill()
            out, err = handle.communicate()
    ended = time.time()
    if registry is not None:
        registry.ended(handle.pid, handle.returncode)
    if sink:
        sink.close()
        out = read_text(stdout_path, "").encode("utf-8")
    record = {
        "argv": argv,
        "label": label,
        "exit": handle.returncode,
        "timed_out": timed_out,
        "wall_seconds": round(ended - started, 3),
        "stdout": out.decode("utf-8", "replace") if out else "",
        "stderr": err.decode("utf-8", "replace") if err else "",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ended)),
    }
    if record["stderr"]:
        sys.stderr.write(record["stderr"][-4000:])
        if not record["stderr"].endswith("\n"):
            sys.stderr.write("\n")
    return record


def _terminate_group(pid):
    """SIGTERM the child's own process group, SIGKILL after five seconds (E10-12, E10-14)."""
    for sig, wait in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 1.0)):
        try:
            os.killpg(os.getpgid(pid), sig)
        except OSError as exc:
            if exc.errno in (errno.ESRCH, errno.EPERM):
                return
        deadline = time.time() + wait
        while time.time() < deadline:
            try:
                os.killpg(os.getpgid(pid), 0)
            except OSError:
                return
            time.sleep(0.2)


def lane_of_case(case_id):
    """The fixture lane a case id belongs to, from the generators themselves."""
    for lane in sorted(os.listdir(FIXTURES_DIR)):
        build = os.path.join(FIXTURES_DIR, lane, "build.py")
        if not os.path.isfile(build):
            continue
        listed = run_cmd([sys.executable, build, "--list"], env=tool_env(), label="list")
        if case_id in listed["stdout"].split():
            return lane
    raise Usage("no fixture lane holds the case %r" % case_id)


_LANE_CACHE = {}


def lane_index():
    """case id -> lane, built once per process from the generators' own `--list`."""
    if not _LANE_CACHE:
        for lane in sorted(os.listdir(FIXTURES_DIR)):
            build = os.path.join(FIXTURES_DIR, lane, "build.py")
            if not os.path.isfile(build):
                continue
            listed = run_cmd([sys.executable, build, "--list"], env=tool_env(), label="list")
            for case in listed["stdout"].split():
                _LANE_CACHE[case] = lane
    return _LANE_CACHE


# --------------------------------------------------------------------------- the campaign


class Campaign(object):
    """One campaign directory under `~/.local/share/skills-v2-pilot/e10/<id>/` (E10-6)."""

    def __init__(self, root):
        self.root = os.path.abspath(root)

    # ---- paths
    @property
    def stage(self):
        return os.path.join(self.root, "stage")

    @property
    def tmp(self):
        return os.path.join(self.root, "tmp")

    @property
    def trials(self):
        return os.path.join(self.root, "trials")

    @property
    def routing_dir(self):
        return os.path.join(self.root, "routing")

    @property
    def campaign_json(self):
        return os.path.join(self.root, "campaign.json")

    @property
    def stage_json(self):
        return os.path.join(self.root, "stage.json")

    @property
    def trials_jsonl(self):
        return os.path.join(self.root, "trials.jsonl")

    @property
    def interruptions(self):
        return os.path.join(self.root, "interruptions.jsonl")

    @property
    def log(self):
        return os.path.join(self.root, "runner.log")

    @property
    def pid_file(self):
        return os.path.join(self.root, "campaign.pid")

    @property
    def processes(self):
        return os.path.join(self.root, "processes.jsonl")

    @property
    def attempts_journal(self):
        return os.path.join(self.root, "attempts.jsonl")

    @property
    def measurements(self):
        return os.path.join(self.root, "measurements")

    @property
    def synthetic_marker(self):
        return os.path.join(self.root, "SYNTHETIC")

    def trial_dir(self, trial_id):
        """The record directory for one trial id, with resolved containment enforced.

        E10-43 (finding 4): a separator or a dot segment in an id could put `command.json`
        outside `trials/`. The id is checked by `check_identifier` and the resolved path is
        checked again here, so neither a plan nor a hand-typed id can escape.
        """
        check_identifier("trial id", trial_id)
        path = os.path.join(self.trials, trial_id)
        contained(self.trials, path, "the trial record for %r" % trial_id)
        return path

    def records(self, name):
        return os.path.join(self.root, "records", name)

    def reserve_record(self, stem, suffix=".json"):
        """A record name nothing else holds, reserved atomically (E10-43, finding 7).

        `install-<timestamp>.json` collided when two installs landed in one second; every
        generated record now takes the first free `<stem>-<n><suffix>` and creates it with
        O_CREAT|O_EXCL before anything is written into it.
        """
        directory = os.path.join(self.root, "records")
        ensure_dir(directory)
        for index in range(0, 10000):
            name = "%s%s%s" % (stem, "" if index == 0 else "-%d" % index, suffix)
            path = os.path.join(directory, name)
            try:
                handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    continue
                raise
            os.close(handle)
            return path
        raise Failure("no free record name for %s under %s" % (stem, directory))

    def synthetic(self):
        """True when the runner itself marked this campaign synthetic (E10-45, finding 9).

        Set by `plan --synthetic` and by any launch that ran a `--fake-launcher`; a key
        stand-in is honoured only for such a campaign, so a stand-in can never grade a real
        trial even with the test flag set.
        """
        if os.path.exists(self.synthetic_marker):
            return True
        try:
            return bool(self.plan().get("synthetic"))
        except (Missing, Failure):
            return False

    def mark_synthetic(self, why):
        if not os.path.exists(self.synthetic_marker):
            ensure_dir(self.root)
            write_text(self.synthetic_marker,
                       "%s %s\n" % (now_iso(), why))

    # ---- state
    def ensure(self):
        ensure_dir(self.root)
        ensure_dir(self.tmp)
        ensure_dir(self.trials)
        ensure_dir(os.path.join(self.root, "records"))

    def plan(self):
        if not os.path.isfile(self.campaign_json):
            raise Missing("no campaign.json under %s; run `plan` first" % self.root)
        return read_json(self.campaign_json, "campaign.json")

    def staged(self):
        if not os.path.isfile(self.stage_json):
            raise Missing("no stage.json under %s; run `stage` first" % self.root)
        return read_json(self.stage_json, "stage.json")

    def env(self, extra=None, require_binaries=True):
        ensure_dir(self.tmp)
        return allowlist_env(self.tmp, extra=extra, require_binaries=require_binaries)

    def append_jsonl(self, path, document):
        ensure_dir(os.path.dirname(path))
        with _APPEND_LOCK:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(document, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def interruption(self, trial_id, observed, action, attempt=None):
        """One line per failure, timeout, signal, stop and rerun (E10-14, E10-43).

        `attempt` is part of the identity: a rerun's interruption must not read as the base
        attempt's (finding 19).
        """
        self.append_jsonl(
            self.interruptions,
            {"trial": trial_id, "attempt": attempt, "at": now_iso(), "observed": observed,
             "did": action},
        )

    def journal_attempt(self, trial_id, attempt, record, kind):
        """Durable creation journal (E10-43, finding 21): an attempt exists from this line on,
        whatever happens to its directory afterwards, so a stop or a crash cannot lose it."""
        self.append_jsonl(self.attempts_journal, {
            "trial": trial_id, "attempt": attempt, "record": record, "kind": kind,
            "created_at": now_iso(), "pid": os.getpid()})

    def note(self, text):
        ensure_dir(self.root)
        with _APPEND_LOCK:
            with open(self.log, "a", encoding="utf-8") as handle:
                handle.write("%s %s\n" % (now_iso(), text))

    # ---- the opaque tree (E10-41, finding 2)
    def opaque_tree(self, trial_id, attempt=0):
        """`<campaign>/tmp/<digest>/` — the one tree a model under trial ever sees.

        The digest is over the campaign id, the full trial id and the attempt number, so no
        parent directory of the workspace or the run directory names a setup, a case, a
        condition or a repetition (finding 2: the dry run's prompts carried
        `/trials/claude-code-F1-01-fixed-clean-available-r1/fixture/...`), two attempts of one
        trial never mint the same path (finding 5), and the whole reachable world of a trial
        sits inside the one tree OpenCode's allow rule covers (E10-34).
        """
        seed = "%s\0%s\0%d" % (os.path.basename(self.root), trial_id, attempt)
        return os.path.join(self.tmp, hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16])


_APPEND_LOCK = threading.RLock()

# E10-43 (finding 4): an identifier that reaches a path. No separator, no dot segment, no
# NUL, nothing but the characters the ids of E10-10, E10-12 and E10-13 are built from.
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def check_identifier(what, value):
    if not isinstance(value, str) or not value:
        raise Usage("%s must be a non-empty string, got %r" % (what, value))
    if os.sep in value or (os.altsep and os.altsep in value) or "/" in value or "\\" in value:
        raise Usage("%s %r carries a path separator" % (what, value))
    if value in (".", "..") or value.startswith(".") or "/.." in value or "\0" in value:
        raise Usage("%s %r is a dot segment" % (what, value))
    if not IDENTIFIER_RE.match(value):
        raise Usage("%s %r is not of the shape [A-Za-z0-9][A-Za-z0-9._-]*" % (what, value))
    return value


def contained(root, path, what):
    """The resolved path must sit under the resolved root (E10-43)."""
    root_real = os.path.realpath(root)
    path_real = os.path.realpath(path)
    if path_real != root_real and not path_real.startswith(root_real.rstrip(os.sep) + os.sep):
        raise Usage("%s resolves outside %s: %s" % (what, root_real, path_real))
    return path


# --------------------------------------------------------------------------- the process registry
#
# E10-45 (finding 8): every launch process is registered before it starts and bound to its
# attempt; neither grading path opens a key while any registered process of that attempt is
# alive. E10-43 (finding 21): `campaign stop` terminates the registered groups and collects
# their statuses.


class ProcessRegistry(object):
    """One durable journal of every process the runner launched, per (trial, attempt)."""

    def __init__(self, campaign, trial, attempt, kind):
        self.campaign = campaign
        self.trial = trial
        self.attempt = attempt
        self.kind = kind
        self.token = uuid.uuid4().hex

    def reserved(self, argv, label):
        """Written BEFORE the child is spawned: an entry with no pid yet (finding 8)."""
        self.campaign.append_jsonl(self.campaign.processes, {
            "event": "reserved", "token": self.token, "trial": self.trial,
            "attempt": self.attempt, "kind": self.kind, "label": label,
            "argv": argv, "at": now_iso(), "owner_pid": os.getpid()})
        return self

    def started(self, pid, argv=None):
        self.campaign.append_jsonl(self.campaign.processes, {
            "event": "started", "token": self.token, "trial": self.trial,
            "attempt": self.attempt, "kind": self.kind, "pid": pid,
            "pgid": _pgid_of(pid), "argv": argv, "at": now_iso()})

    def ended(self, pid, status):
        self.campaign.append_jsonl(self.campaign.processes, {
            "event": "ended", "token": self.token, "trial": self.trial,
            "attempt": self.attempt, "kind": self.kind, "pid": pid,
            "exit": status, "at": now_iso()})

    def released(self, why):
        """A reservation that never became a process (E10-59 (1, 8)).

        A reserved launch whose owner is alive is a LIVE process from here on, so a
        reservation the runner abandoned — the binary was not there, the spawn raised —
        has to be closed explicitly, or the barrier would wait on a child that never
        started. `released` closes the token exactly as `ended` does.
        """
        self.campaign.append_jsonl(self.campaign.processes, {
            "event": "released", "token": self.token, "trial": self.trial,
            "attempt": self.attempt, "kind": self.kind, "why": why,
            "at": now_iso(), "owner_pid": os.getpid()})


def _pgid_of(pid):
    try:
        return os.getpgid(pid)
    except OSError:
        return None


def process_rows(campaign):
    return jsonl_lines(campaign.processes)


def live_processes(campaign, trial=None, attempt=None):
    """Every registered launch still alive, optionally narrowed to one attempt.

    E10-59 (1, 8): **a reserved launch whose owner is alive is a live process.** `reserved`
    is written before the child is spawned (finding 8's own rule), so between the reservation
    and the `started` line a launch exists that no pid names yet; the old reader looked only
    at `started` rows and saw nothing there, and the reviewer's probe reserved a launch with a
    live owner and got `reserved_seen_as_live: false`. The reservation carries `owner_pid`,
    which is the process that is about to spawn the child, and it is closed by its own token's
    `started`, `ended` or `released` line.
    """
    open_pids, reserved, alive = {}, {}, []
    for row in process_rows(campaign):
        if trial is not None and row.get("trial") != trial:
            continue
        if attempt is not None and row.get("attempt") != attempt:
            continue
        event, token = row.get("event"), row.get("token")
        if event == "reserved":
            reserved[token] = row
        elif event == "started":
            reserved.pop(token, None)
            if row.get("pid"):
                open_pids[row["pid"]] = row
        elif event in ("ended", "released"):
            reserved.pop(token, None)
            if row.get("pid") in open_pids:
                open_pids.pop(row["pid"], None)
    for pid, row in sorted(open_pids.items()):
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        alive.append(dict(row, live_because="the launched process is alive"))
    for token in sorted(reserved):
        row = reserved[token]
        owner = row.get("owner_pid")
        if not owner:
            continue
        try:
            os.kill(owner, 0)
        except OSError:
            continue
        alive.append(dict(row, pid=owner,
                          live_because="a reserved launch whose owner process is alive"))
    return alive


# --------------------------------------------------------------------------- the key lock (E10-40)
#
# The three harnesses run every trial as the same user with no read sandbox, so no process
# boundary can keep a model under trial from a readable file (E10-40 records Astra's
# prescription as unreachable on these setups). What the runner can do, and does: hold
# `evals/answer-key/` and `evals/trigger-set/held-out/` at mode 000 for the whole of every
# launch, reopen them only inside `grade` and `routing-score` after every registered process
# of the attempt has ended, refuse links that leave a stage or a home, and MEASURE what a
# child could reach (`records_reached`, the `check` sentinel). The record labels the boundary
# `instruction-bound + measured`, E9's word for the same situation.

KEY_BOUNDARY_LABEL = "instruction-bound + measured"


def key_paths():
    """The two directories the lock covers, in the checkout and nowhere else."""
    return [KEY_DIR, os.path.dirname(TRIGGER_HELDOUT)]


def key_state():
    rows = []
    for path in key_paths():
        if not os.path.isdir(path):
            rows.append({"path": path, "present": False, "mode": None, "closed": None})
            continue
        mode = stat.S_IMODE(os.stat(path).st_mode)
        rows.append({"path": path, "present": True, "mode": "0%o" % mode,
                     "closed": mode == 0})
    return rows


def key_closed():
    rows = [r for r in key_state() if r["present"]]
    return bool(rows) and all(r["closed"] for r in rows)


def close_key(campaign=None, why="a launch"):
    """Mode 000 on both directories for the duration of a launch (E10-40)."""
    changed = []
    for path in key_paths():
        if os.path.isdir(path):
            os.chmod(path, 0o000)
            changed.append(path)
    if campaign is not None and changed:
        campaign.note("key closed (%s): %s" % (why, ", ".join(changed)))
    return changed


def open_key(campaign=None, why="grading"):
    changed = []
    for path in key_paths():
        if os.path.isdir(path):
            os.chmod(path, 0o700)
            changed.append(path)
    if campaign is not None and changed:
        campaign.note("key opened (%s): %s" % (why, ", ".join(changed)))
    return changed


class key_open(object):
    """`with key_open(campaign):` — the only window in which a key file may be read."""

    def __init__(self, campaign=None, why="grading"):
        self.campaign = campaign
        self.why = why
        self.was_closed = False

    def __enter__(self):
        self.was_closed = key_closed()
        open_key(self.campaign, self.why)
        return self

    def __exit__(self, *exc):
        close_key(self.campaign, "the %s step ended" % self.why)
        return False


# --------------------------------------------------------------------------- lane stops (E10-46)


def lane_stop_path(campaign, setup_name):
    return os.path.join(campaign.root, "lane-stops", "%s.json" % setup_name)


def lane_stopped(campaign, setup_name):
    path = lane_stop_path(campaign, setup_name)
    if not os.path.isfile(path):
        return None
    try:
        return read_json(path)
    except (Missing, Failure):
        return {"reason": "unreadable lane stop at %s" % path}


def clear_lane_stop(campaign, setup_name, why):
    """Clear a lane stop, keeping the stop itself as a record (E10-46).

    A lane stop is a measurement. Clearing one is an act with a reason, so the stop file moves
    into `lane-stops/cleared/` with the reason beside it and the log says so; nothing is
    deleted and no later reader loses the fact that the lane stopped.
    """
    path = lane_stop_path(campaign, setup_name)
    if not os.path.isfile(path):
        raise Missing("no lane stop for %s" % setup_name)
    document = read_json(path)
    document["cleared_at"] = now_iso()
    document["cleared_because"] = why
    cleared = os.path.join(campaign.root, "lane-stops", "cleared",
                           "%s-%s.json" % (setup_name, time.strftime("%Y%m%dT%H%M%SZ",
                                                                    time.gmtime())))
    ensure_dir(os.path.dirname(cleared))
    write_json(cleared, document)
    os.unlink(path)
    campaign.note("lane stop on %s cleared: %s (kept at %s)" % (setup_name, why, cleared))
    campaign.interruption(None, "the %s lane stop was cleared by hand" % setup_name, why)
    return {"setup": setup_name, "cleared": cleared, "why": why}


def stop_lane(campaign, setup_name, reason, record, kind="profile_breach", extra=None):
    """A lane stop, durably: no later launch on that setup can pass.

    `kind` says what stopped it. `profile_breach` is E10-46's; `runner_error` is E10-68
    defect 3's — the runner itself raised inside the lane worker and the thread would
    otherwise have died with nothing in any record.
    """
    path = lane_stop_path(campaign, setup_name)
    ensure_dir(os.path.dirname(path))
    if not os.path.isfile(path):
        document = {"setup": setup_name, "kind": kind, "reason": reason, "record": record,
                    "stopped_at": now_iso()}
        document.update(extra or {})
        write_json(path, document)
    campaign.note("lane stop on %s (%s): %s" % (setup_name, kind, reason))
    return read_json(path)


# E10-68 defect 3. The status of a trial the RUNNER, not the harness, failed: the lane worker
# raised before `collect_trial` could write `command.json`, so the ledger held a directory
# with no record at all (`claude-code-F3-01-missed-case-available-r2` of the 2026-09-15
# campaign). None of the five existing statuses fits — `launch_failed`, `timed_out` and
# `no_result` all describe a process that ran, and `profile_breach` is a measured catalog
# fault — so E10-68's own word is the status.
RUNNER_ERROR = "runner_error"
# `main` turns this key into a non-zero exit while still printing the one JSON document on
# stdout that A7a requires.
FAIL_EXIT_KEY = "runner_exit_nonzero_because"


def record_lane_runner_error(campaign, lane, row, exc):
    """An uncaught exception in a lane worker becomes a record (E10-68 defect 3).

    Three records, in this order: the trial in flight gets a `command.json` with status
    `runner_error` (so the ledger never has a directory without a record) and a ledger line of
    its own; `interruptions.jsonl` gets the line E10-14 asks of every interruption; and
    `lane-stops/<setup>.json` gets the stop `campaign status` reports, carrying the traceback,
    the trial in flight and the time.
    """
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    trial_id = (row or {}).get("id")
    kind = (row or {}).get("kind") or "comparison"
    record = (row or {}).get("record") or (campaign.trial_dir(trial_id) if trial_id else None)
    written = None
    if trial_id and record:
        try:
            ensure_dir(record)
            command_json = os.path.join(record, "command.json")
            if not os.path.isfile(command_json):
                write_json(command_json, {
                    "trial": trial_id, "attempt": 0, "kind": kind,
                    "setup": lane, "status": RUNNER_ERROR,
                    "runner_error": {"exception": "%s: %s" % (type(exc).__name__, exc),
                                     "traceback": detail, "lane": lane, "at": now_iso()},
                    "note": "E10-68 defect 3: the RUNNER failed inside this trial, not the "
                            "harness. Nothing here was measured from a session; the record "
                            "exists so the ledger has no directory without one.",
                    "key_boundary": KEY_BOUNDARY_LABEL,
                })
                campaign.append_jsonl(campaign.trials_jsonl, {
                    "id": trial_id, "attempt": 0, "kind": kind, "status": RUNNER_ERROR,
                    "exit": None, "wall": None, "cost": None, "model": None, "effort": None,
                    "activated": None, "record": record})
                written = command_json
        except (Usage, Missing, Failure, OSError) as inner:
            campaign.note("could not write a runner_error record for %s: %s"
                          % (trial_id, inner))
    campaign.interruption(trial_id, "the %s lane worker raised %s: %s"
                          % (lane, type(exc).__name__, exc),
                          "recorded a lane stop of kind %s and stopped the lane" % RUNNER_ERROR,
                          attempt=0 if trial_id else None)
    return stop_lane(campaign, lane,
                     "the lane worker raised %s: %s" % (type(exc).__name__, exc),
                     record, kind=RUNNER_ERROR,
                     extra={"traceback": detail, "trial_in_flight": trial_id,
                            "trial_kind": kind, "at": now_iso(),
                            "command_json_written": written})


def pilot_home(harness, home, setup_name=None):
    """The pilot home for one setup and one of the three homes of E10-3 and E10-13.

    `available` is the home E9 built and closed; `absent` and `routing` are the second and
    third homes beside it under the same pilot root.

    **The SETUP NAME keys the paths, not the harness (E10-62 item 3).** Two setups of one
    harness — `opencode` on qwen and `opencode-deepseek` on DeepSeek — would otherwise share
    one set of homes, and the second install would overwrite the first: the shared OpenCode
    `opencode.json` is rewritten by every install with that install's own default model
    (E10-31), so the fourth lane needs three homes of its own. For the three setups whose name
    equals their harness the layout is unchanged, path for path, which is why the name falls
    back to the harness when none is given.
    """
    if home not in HOMES:
        raise Usage("home must be one of %s" % ", ".join(HOMES))
    base = os.path.join(PILOT_ROOT, setup_name or harness)
    if harness == "claude-code":
        return base if home == "available" else os.path.join(base, home)
    if harness == "codex":
        return os.path.join(base, "home") if home == "available" else os.path.join(base, "homes", home)
    if harness == "opencode":
        return base if home == "available" else os.path.join(base, home)
    raise Usage("unknown harness %r" % harness)


# --------------------------------------------------------------------------- stage (E10-6)

STAGE_EXCLUDE_DIRS = (".git", "__pycache__", ".venv", "node_modules")


def protected_roots(campaign=None):
    """The places a link inside a home may never reach (E10-40).

    Not "anything outside the tree": `uv` fills every home with interpreter symlinks, and
    `setups/claude-code/install.sh` builds its own local marketplace out of symlinks into the
    staged `setups/_fixtures/`. What the rule protects is the answer key and the held-out set,
    and the campaign's own RECORDS — never the stage, which by construction holds no `evals/`.
    """
    roots = list(key_paths())
    if campaign is not None:
        roots += [campaign.trials, os.path.join(campaign.root, "records"),
                  campaign.measurements, campaign.routing_dir,
                  os.path.join(campaign.root, "probes")]
    return [p for p in roots if p]


def link_survey(root, allowed_targets=(), forbidden_targets=()):
    """Every symbolic and hard link under a tree, with where it points (E10-40, finding 26).

    E10-40 refuses "a symlink or hard link anywhere in a stage or a home". Taken literally the
    home half is unreachable and was measured so on 2026-09-15: `uv` builds a virtual
    environment inside every Codex and OpenCode home and fills its `bin/` with symlinks to the
    interpreter in the uv toolchain store, four per home, and the Codex derived homes point
    their `auth.json` at the base home's single store rather than copying a credential into two
    more places. Refusing those would refuse every install.

    The reading the fix round takes, and the report's contract question: a link is REFUSED when
    its resolved target lands inside a `forbidden_targets` root — the checkout (where the
    answer key and the held-out set live) and the campaign root (where the records live),
    which is the only thing the rule protects. Every other link that leaves the tree is
    RECORDED with its target and its reason. Inside a stage the strict rule still holds: no
    link is copied at all, so a staged install cannot follow one anywhere.
    """
    roots = [os.path.realpath(root)] + [os.path.realpath(p) for p in allowed_targets]
    forbidden = [os.path.realpath(p) for p in forbidden_targets]
    symlinks, escaping, refused, hard = [], [], [], []
    for base, dirs, files in os.walk(root):
        for name in sorted(dirs) + sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                target = os.path.realpath(full)
                inside = any(target == r or target.startswith(r.rstrip(os.sep) + os.sep)
                             for r in roots)
                forbidden_hit = [r for r in forbidden
                                 if target == r or target.startswith(r.rstrip(os.sep) + os.sep)]
                row = {"path": rel, "points_to": target, "inside_an_allowed_root": inside,
                       "points_into_a_forbidden_root": forbidden_hit}
                symlinks.append(row)
                if not inside:
                    escaping.append(row)
                if forbidden_hit:
                    refused.append(row)
                continue
            try:
                info = os.lstat(full)
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
                hard.append({"path": rel, "links": info.st_nlink})
    return {"symlinks": symlinks, "symlinks_leaving_the_tree": escaping,
            "symlinks_refused": refused, "hard_links": hard,
            "forbidden_roots": forbidden}


def fresh_skill_identity(campaign):
    """A fresh `recheck.py skill-identity` of the CHECKOUT, never a typed digest (E10-6).

    E10-52 (finding 26): a failed computation or an empty digest is a failure, not a `null`
    that a later `ok` quietly steps over.
    """
    step = run_cmd(["uv", "run", os.path.join(SKILL_DIR, "scripts", "recheck.py"),
                    "skill-identity"], env=campaign.env(), label="skill-identity")
    digest, parse_error = None, None
    if step["exit"] == 0:
        try:
            digest = json.loads(step["stdout"])["content_sha256"]
        except (ValueError, KeyError) as exc:
            parse_error = str(exc)
    return {"exit": step["exit"], "content_sha256": digest, "parse_error": parse_error,
            "stderr_tail": (step["stderr"] or "")[-600:],
            "ok": step["exit"] == 0 and isinstance(digest, str) and len(digest) == 64}


def do_stage(args):
    """A copy of the checkout at the campaign commit, with `plugins/recheck-v2/evals/` out."""
    campaign = Campaign(args.campaign)
    campaign.ensure()
    if os.path.exists(campaign.stage) and not args.refresh:
        raise Usage(
            "%s already holds a stage; pass --refresh to replace it (a record is never "
            "overwritten silently)" % campaign.root
        )
    if os.path.exists(campaign.stage):
        rmtree(campaign.stage)
    commit = run_cmd(["git", "-C", REPO_ROOT, "rev-parse", "HEAD"], env=campaign.env())
    if commit["exit"] != 0:
        raise Failure("git rev-parse failed in %s" % REPO_ROOT)
    excluded_evals = os.path.join("plugins", "recheck-v2", "evals")
    copied, refused_links = 0, []
    for base, dirs, files in os.walk(REPO_ROOT):
        rel = os.path.relpath(base, REPO_ROOT)
        rel = "" if rel == "." else rel
        dirs[:] = [d for d in sorted(dirs) if d not in STAGE_EXCLUDE_DIRS]
        if rel == os.path.join("plugins", "recheck-v2"):
            dirs[:] = [d for d in dirs if d != "evals"]
        if rel.startswith(excluded_evals):
            continue
        target = os.path.join(campaign.stage, rel) if rel else campaign.stage
        ensure_dir(target)
        for name in sorted(files):
            source = os.path.join(base, name)
            if os.path.islink(source):
                # E10-40: a link is never copied into a stage. It is recorded and refused, so
                # no package link can point a staged install at anything outside the stage.
                refused_links.append({"path": os.path.join(rel, name),
                                      "points_to": os.readlink(source)})
                continue
            shutil.copy2(source, os.path.join(target, name))
            copied += 1
    staged_plugin = os.path.join(campaign.stage, "plugins", "recheck-v2")
    leaked = sorted(
        os.path.relpath(p, campaign.stage)
        for p in glob.glob(os.path.join(staged_plugin, "**", "answer-key"), recursive=True)
        + glob.glob(os.path.join(staged_plugin, "**", "held-out"), recursive=True)
        + glob.glob(os.path.join(staged_plugin, "evals"))
    )
    identity = fresh_skill_identity(campaign)
    links = link_survey(campaign.stage)
    # E10-53(3): the manifest with hashes, so a later reader can recompute the tree hash and
    # the reviewer's "historical tree hashes cannot be recomputed" question is answered.
    manifest = file_manifest(staged_plugin)
    manifest_path = campaign.reserve_record("stage-manifest")
    write_json(manifest_path, {"root": staged_plugin, "commit": commit["stdout"].strip(),
                               "files": manifest,
                               "plugin_tree_sha256": tree_sha256_of(
                                   staged_plugin, exclude_dirs=E10_6_TREE_EXCLUDED,
                                   follow_directory_links=False)})
    document = {
        "campaign": campaign.root,
        "checkout": REPO_ROOT,
        "commit": commit["stdout"].strip(),
        "staged_at": now_iso(),
        "stage": campaign.stage,
        "files_copied": copied,
        # E10-6's own definition, kept byte for byte (E10-60 (10) widened the default).
        "plugin_tree_sha256": tree_sha256_of(staged_plugin,
                                            exclude_dirs=E10_6_TREE_EXCLUDED,
                                            follow_directory_links=False),
        "evals_excluded": True,
        "answer_key_or_held_out_in_stage": leaked,
        "canonical_content_sha256": identity["content_sha256"],
        "skill_identity": identity,
        "skill_identity_exit": identity["exit"],
        "links_refused_during_the_copy": refused_links,
        "link_survey": links,
        "manifest": manifest_path,
        "manifest_files": len(manifest),
        "key_boundary": KEY_BOUNDARY_LABEL,
    }
    problems = []
    if leaked:
        problems.append("the stage still holds %s" % ", ".join(leaked))
    if not identity["ok"]:
        problems.append("skill-identity did not produce a 64-character content_sha256 "
                        "(exit %s, digest %r)" % (identity["exit"], identity["content_sha256"]))
    if links["symlinks"] or links["hard_links"]:
        problems.append("the stage holds links: %s"
                        % json.dumps({"symlinks": links["symlinks"][:8],
                                      "hard_links": links["hard_links"][:8]}))
    document["ok"] = not problems
    document["problems"] = problems
    if problems:
        raise Failure("stage refused: %s" % "; ".join(problems))
    write_json(campaign.stage_json, document)
    campaign.note("stage %s at %s" % (campaign.stage, document["commit"]))
    return document


def file_manifest(root):
    """`[{path, sha256, bytes}]` over every file under a tree, sorted (E10-53(3))."""
    rows = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__",))
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                rows.append({"path": rel, "symlink_to": os.readlink(full), "sha256": None,
                             "bytes": None})
                continue
            try:
                with open(full, "rb") as handle:
                    blob = handle.read()
            except (IOError, OSError) as exc:
                rows.append({"path": rel, "sha256": None, "bytes": None, "error": str(exc)})
                continue
            rows.append({"path": rel, "sha256": sha256_hex(blob), "bytes": len(blob)})
    rows.sort(key=lambda r: r["path"])
    return rows


# --------------------------------------------------------------------------- harness adapters
#
# One class per setup. Each knows: how to install its three homes from the staged copy, what
# environment its own launcher needs for itself, how to launch one headless session, and how
# to read the harness's own record for the model, the effort, the cost, the condition witness
# and the activation marker (the delivery marker each E9 profile section 8 names).


def native_message(record):
    """The `message` OBJECT of a native harness record, or `{}` when there is not one.

    E10-68 defect 2. Claude Code writes `system` events of subtype `permission_denied` — an
    `Edit` auto-denied because a headless session has no approval surface — whose `message`
    is a plain STRING, not an object. `record.get("message") or {}` hands that string straight
    through, and the next `.get` raises `AttributeError: 'str' object has no attribute 'get'`.
    The first such event in any trace killed the `lane-claude-code` thread of the 2026-09-15
    campaign (`runner.log` lines 503 to 519), leaving `claude-code-F3-01-missed-case-available-r2`
    without a `command.json` and the lane at 10 of 87.

    Every reader of a trace or transcript record goes through this and through
    `message_content`, so a record whose `message` is a string, a list, a number or absent is
    read as carrying no message rather than crashing the reader that touched it.
    """
    message = record.get("message") if isinstance(record, dict) else None
    return message if isinstance(message, dict) else {}


def message_content(record):
    """The `content` BLOCKS of a native record's message, or `[]` when there are none.

    Tolerant of a non-dict `message` and a non-list `content` alike (E10-68 defect 2): a
    string `content` (Claude Code's plain user turns carry one) is not a block list, and the
    callers here all want blocks.
    """
    content = native_message(record).get("content")
    return content if isinstance(content, list) else []


# The harness records of a denied tool call. E10-68 defect 2 asks for the denial to be KEPT as
# a witness, not merely survived: `permission_denials` counts the events and names the tools,
# so the E11 report can say how often a headless session was denied per harness.
PERMISSION_DENIED_SUBTYPE = "permission_denied"


class Setup(object):
    harness = None
    name = None
    # The default model of a setup that named none, per harness. `None` means "whatever the
    # harness's own sign-in or config already says", which is what E10-2 measured for Claude
    # Code and Codex before Tony pinned them.
    default_model = None

    def __init__(self, campaign, stage=None, name=None, model=None, effort=None):
        self.campaign = campaign
        self.stage = stage or campaign.stage
        self.name = name or self.harness
        # E10-62: the plan's pair, carried by EVERY class, not only OpenCode's.
        self.model = model
        self.effort = effort

    # ---- paths
    @property
    def setup_dir(self):
        return os.path.join(self.stage, "plugins", "recheck-v2", "setups", self.harness)

    def script(self, name):
        path = os.path.join(self.setup_dir, name)
        if not os.path.isfile(path):
            raise Missing("the staged copy has no %s/%s" % (self.harness, name))
        return path

    def home(self, condition):
        # E10-62 item 3: the SETUP NAME keys the homes, so a second setup of one harness never
        # overwrites the first's install.
        return pilot_home(self.harness, condition, setup_name=self.name)

    # ---- what the launcher was told (E10-50, E10-62 item 4)
    def resolved_model(self):
        """The model id this setup launches on: the plan's, else the harness's own default."""
        return self.model or self.default_model

    def configured_record(self):
        """`model.json.configured`: the plan's pair, on every harness, at every write site.

        E10-50 keeps configured and observed apart, and this is the configured half. It is
        **never** an observation: before E10-62 the Claude Code reader built it out of
        `launch.json`'s `model` key, which `setups/claude-code/launch.sh` fills from the
        session's own `system/init` event, so the field labelled "what the launcher was told"
        held what the harness reported. Codex's `launch.json` carries no model key at all and
        OpenCode's launcher writes no `launch.json`, so both read `null`. The plan is the one
        source now, and each launcher's own record of what it was handed sits beside it as
        `launcher_recorded` where the launcher writes one.
        """
        return {
            "model": self.resolved_model(),
            "effort": self.effort,
            "source": "the plan's setup entry for %r (E10-62), passed to the launcher"
                      % self.name,
            "note": "what the launcher was TOLD, never an observation (E10-50); the harness's "
                    "own witness is `id`/`effort` beside it",
        }

    def setup_tree_sha256(self):
        # E10-6's definition, as above.
        return tree_sha256_of(self.setup_dir, exclude_dirs=E10_6_TREE_EXCLUDED,
                              follow_directory_links=False)

    # ---- the launcher's own variables (E10-7: "the variables the setup's own launcher sets
    # for itself" are the home pointers each script documents)
    def launch_env(self, condition):
        raise NotImplementedError

    def install(self, condition, fake=None):
        raise NotImplementedError

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None,
               registry=None):
        raise NotImplementedError

    def verify(self, condition):
        raise NotImplementedError

    def catalog(self, condition, out_dir):
        """The harness's own catalog record for the condition witness."""
        return {"kind": "none", "record": None}

    # ---- reading the harness's own record
    def model_record(self, out_dir):
        return {"id": None, "effort": None, "source": None}

    def cost_record(self, out_dir):
        return {"total_cost_usd": None, "tokens": None, "source": None}

    def condition_witness(self, out_dir, condition):
        return {"condition": condition, "witness": None, "source": None}

    def activation(self, out_dir):
        return {"activated": None, "marker": None, "profile_section": None}

    def permission_denials(self, out_dir):
        """Tool calls this harness denied to the session itself (E10-68 defect 2).

        The base answer is "this harness writes no such event on the measured version"; the
        refusals it DOES record are already measured per action by `native_actions`'s
        `refused` rows. Claude Code overrides it.
        """
        return {"count": 0, "tools": [], "events": [],
                "how": "%s writes no permission-denied event on the measured version; a "
                       "refused action is measured per call by native_actions" % self.harness}

    def trace_paths(self, out_dir):
        """Every file of the harness's own record, for the trace scans."""
        return [os.path.join(out_dir, n) for n in os.listdir(out_dir)] if os.path.isdir(out_dir) else []


# ------------------------------------------------------------------ Claude Code


class ClaudeCodeSetup(Setup):
    harness = "claude-code"

    def launch_env(self, condition):
        return {"SKILLS_V2_PILOT_HOME": self.home(condition)}

    def marketplace_plugins(self):
        """Every plugin in the checkout's marketplace, for the routing profile (E10-13)."""
        manifest = read_json(
            os.path.join(self.stage, ".claude-plugin", "marketplace.json"), "marketplace.json"
        )
        return [p["name"] for p in manifest.get("plugins", [])]

    def install(self, condition, fake=None):
        home = self.home(condition)
        env = self.campaign.env(extra={"SKILLS_V2_PILOT_HOME": home})
        argv = ["sh", self.script("install.sh"), "--pilot-home", home]
        # E10-56(1): the absent home is built by an install that never installs the skill, so
        # E10-3's "never held recheck-v2 on any surface" holds by construction. The runner's
        # own second-guard removal (`claude plugin uninstall` plus the cache entry E10-24
        # measured it leaving behind) is gone with it.
        if condition == "absent":
            argv += ["--without", "recheck-v2"]
        steps = [run_cmd(argv, env=env, label="install.sh")]
        config = os.path.join(home, "config")
        removed, added = [], []
        if condition == "absent":
            installation = {
                "how": "never installed",
                "by": "install.sh --without recheck-v2 (E10-56(1))",
                "second_guard_removal": "dropped: no uninstall and no cache removal runs",
            }
        else:
            installation = {"how": "installed", "by": "install.sh"}
        if condition == "routing":
            wanted = [p for p in self.marketplace_plugins() if p not in BLOCKED_PLUGINS]
            for plugin in wanted:
                if plugin == "recheck-v2":
                    continue
                steps.append(run_cmd(
                    ["claude", "plugin", "install", "%s@tony-skills" % plugin, "--json", "-y"],
                    env=dict(env, CLAUDE_CONFIG_DIR=config), label="install %s" % plugin))
                added.append(plugin)
        return {
            "home": home,
            "condition": condition,
            "steps": [_step_summary(s) for s in steps],
            "uninstalled_after_install": removed,
            "recheck_v2_installation": installation,
            "extra_plugins_installed": added,
            "install_json": read_json(os.path.join(home, "install.json"), "install.json")
            if os.path.isfile(os.path.join(home, "install.json")) else None,
        }

    def catalog(self, condition, out_dir):
        """The session's own init event is Claude Code's catalog record (E10-13)."""
        launch = self._launch_json(out_dir)
        if not launch:
            return {"kind": "none", "record": None,
                    "note": "the launch wrote no launch.json, so the session recorded no catalog"}
        return {"kind": "the session's own init event", "exit": launch.get("claude_exit"),
                "record": {"skills": launch.get("skills"), "plugins": launch.get("plugins"),
                           "slash_commands": launch.get("slash_commands"),
                           "mcp_servers": launch.get("mcp_servers")}}

    def cache_plugins(self, condition):
        """The plugin names the condition's own install cache holds."""
        cache = os.path.join(self.home(condition), "config", "plugins", "cache")
        names = set()
        for path in glob.glob(os.path.join(cache, "*", "*", "*")):
            if os.path.isdir(path):
                names.add(os.path.basename(os.path.dirname(path)))
        return sorted(names)

    def verify(self, condition):
        home = self.home(condition)
        env = self.campaign.env(extra={"SKILLS_V2_PILOT_HOME": home})
        step = run_cmd(["sh", self.script("verify-install.sh"), "--pilot-home", home], env=env,
                       label="verify-install.sh")
        return step

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None,
               registry=None):
        home = self.home(condition)
        env = self.campaign.env(extra={"SKILLS_V2_PILOT_HOME": home})
        argv = ["sh", fake or self.script("launch.sh"), prompt_file, workspace, out_dir]
        plugins = (extra or {}).get("plugins")
        if plugins is None:
            plugins = ["readers"] if condition == "absent" else ["recheck-v2", "readers"]
        if condition == "routing" and (extra or {}).get("plugins") is None:
            plugins = [p for p in self.cache_plugins(condition) if p not in BLOCKED_PLUGINS]
        for plugin in plugins:
            argv += ["--plugin", plugin]
        # E10-62 item 2: the plan's pair reaches the `claude` argv through the launcher's own
        # two flags. `launch.sh` puts them on the command line and records what it was told
        # under its own keys, so `configured` never has to read the init event again.
        model = (extra or {}).get("model") or self.resolved_model()
        effort = (extra or {}).get("effort") or self.effort
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        if registry is not None:
            registry.reserved(argv, "launch.sh")
        return run_cmd(argv, env=env, timeout=timeout, label="launch.sh", registry=registry)

    # ---- records
    def _launch_json(self, out_dir):
        path = os.path.join(out_dir, "launch.json")
        return read_json(path) if os.path.isfile(path) else {}

    def model_record(self, out_dir):
        """Claude Code: the NATIVE init event, and the transcript's own assistant records.

        E10-50 (finding 18): the observed model is read from the harness's own event, its
        session binding is validated, and it is `null` when the required event is absent. What
        the LAUNCHER typed is kept apart as `configured`, and never becomes an observed
        measurement: the reviewer's probe supplied `launch.json` alone with
        `model: "review-typed-by-launcher"` and the old reader returned it while claiming the
        source was `trace.jsonl init event model`.

        E10-62 item 4 closes the other half of that confusion. `configured` used to be built
        from `launch.json`'s `model` key, and `setups/claude-code/launch.sh` writes that key as
        `init.get("model")` — the session's own init event — so the field that says "what the
        launcher was told" held an observation wearing the launcher's label, which is the exact
        confusion E10-50 exists to prevent. `configured` is now the plan's pair; the launcher's
        own record of the two flags it was handed is `launcher_recorded`; and the init event
        stays where it belongs, in `init_event` and `init_model`.
        """
        launch = self._launch_json(out_dir)
        configured = self.configured_record()
        launcher_recorded = {
            "model": launch.get("configured_model"),
            "effort": launch.get("configured_effort"),
            "source": "harness/launch.json configured_model / configured_effort (the --model "
                      "and --effort launch.sh was handed, E10-62 item 2)",
        }
        init, session = None, None
        for line, record in enumerate(jsonl_lines(os.path.join(out_dir, "trace.jsonl")), 1):
            if record.get("type") == "system" and record.get("subtype") == "init":
                init = {"model": record.get("model"), "session_id": record.get("session_id"),
                        "line": line, "file": "harness/trace.jsonl"}
                session = record.get("session_id")
                break
        model_id, effort, source, bound = None, None, None, None
        for name in ("transcript.jsonl", "trace.jsonl"):
            for line, record in enumerate(jsonl_lines(os.path.join(out_dir, name)), 1):
                if record.get("type") != "assistant" or record.get("isSidechain"):
                    continue
                their_session = record.get("session_id") or record.get("sessionId") \
                    or record.get("sessionID")
                if session and their_session and their_session != session:
                    continue
                message = native_message(record)
                if message.get("model") and message["model"] != "<synthetic>":
                    model_id = message["model"]
                    effort = record.get("effort", effort)
                    source = "harness/%s line %d assistant record message.model" % (name, line)
                    bound = their_session or session
            if model_id:
                break
        if model_id is None and init and init.get("model"):
            model_id = init["model"]
            source = "harness/trace.jsonl line %d system init event model" % init["line"]
            bound = init.get("session_id")
        return bound_model_record({
            "id": model_id, "effort": effort, "source": source,
            "session_binding": bound,
            "session_binding_ok": bool(bound) and (session is None or bound == session),
            "init_event": init,
            "init_model": (init or {}).get("model"),
            "configured": configured,
            "launcher_recorded": launcher_recorded,
            "note": "E10-50: null when the harness wrote no native record, and null when the "
                    "record carries no session binding (E10-59 (18)); `configured` is the "
                    "plan's pair (E10-62), never an observation, and the init event stays in "
                    "`init_event`."})

    def cost_record(self, out_dir):
        launch = self._launch_json(out_dir)
        if launch:
            return {"total_cost_usd": launch.get("total_cost_usd"), "tokens": None,
                    "num_turns": launch.get("num_turns"),
                    "source": "trace.jsonl result event total_cost_usd (via launch.json)"}
        # the compaction resume's own trace, which `launch.sh` did not write
        for record in jsonl_lines(os.path.join(out_dir, "trace.jsonl")):
            if record.get("type") == "result":
                return {"total_cost_usd": record.get("total_cost_usd"),
                        "tokens": record.get("usage"),
                        "num_turns": record.get("num_turns"),
                        "source": "trace.jsonl result event total_cost_usd"}
        return {"total_cost_usd": None, "tokens": None, "num_turns": None, "source": None}

    def condition_witness(self, out_dir, condition):
        """The session's ACTIVE catalog: the init event's own skills and plugins (E10-46).

        `recheck_v2_in_catalog` is decided on the entries the session records as active, with
        the file and line retained; the init event's absence is `null`, never `false`.
        """
        init, line = None, None
        for index, record in enumerate(jsonl_lines(os.path.join(out_dir, "trace.jsonl")), 1):
            if record.get("type") == "system" and record.get("subtype") == "init":
                init, line = record, index
                break
        launch = self._launch_json(out_dir)
        skills = (init or {}).get("skills", launch.get("skills"))
        plugins = (init or {}).get("plugins", launch.get("plugins"))
        present = None
        names = []
        if isinstance(skills, list):
            for skill in skills:
                name = skill.get("name") if isinstance(skill, dict) else skill
                if isinstance(name, str):
                    names.append(name.split(":")[0])
            present = "recheck-v2" in names
        return {
            "condition": condition,
            "witness": {"skills": skills, "plugins": plugins, "catalog_names": sorted(set(names))},
            "recheck_v2_in_catalog": present,
            "file": "harness/trace.jsonl" if init else
                    ("harness/launch.json" if launch else None),
            "line": line,
            "source": "the session's own init event (system/init in the trace) — the ACTIVE "
                      "catalog, not a marketplace listing (E10-46)",
        }

    def activation(self, out_dir):
        """A Skill tool call whose BODY WAS DELIVERED (E10-46, finding 12).

        Profile section 8: the body arrives as one `user` record the harness flags
        `isSynthetic`, after a `Skill` tool call. A call with no delivered body is not an
        activation: `final_probes.py` got `activated: true` for exactly that. Every witness
        keeps its line and its tool-use id.
        """
        skill_calls, delivered, results = [], [], {}
        rows = list(enumerate(jsonl_lines(os.path.join(out_dir, "trace.jsonl")), 1))
        for line, record in rows:
            for block in message_content(record):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    results[block.get("tool_use_id")] = {
                        "line": line, "is_error": bool(block.get("is_error")),
                        "bytes": len(json.dumps(block.get("content")))}
        for line, record in rows:
            if record.get("type") == "assistant":
                for block in message_content(record):
                    if isinstance(block, dict) and block.get("type") == "tool_use" \
                            and block.get("name") == "Skill":
                        target = (block.get("input") or {}).get("skill")
                        skill_calls.append({"line": line, "skill": target,
                                            "id": block.get("id"),
                                            "result": results.get(block.get("id"))})
            if record.get("type") == "user" and record.get("isSynthetic"):
                body = json.dumps(native_message(record).get("content"))
                delivered.append({"line": line, "bytes": len(body),
                                  "uuid": record.get("uuid"),
                                  "non_empty": len(body) > 2})
        ours = [c for c in skill_calls if (c.get("skill") or "").startswith("recheck-v2")]
        succeeded = [c for c in ours
                     if (c.get("result") or {}).get("is_error") is not True
                     and ((c.get("result") or {}).get("bytes", 0) > 2
                          or any(d["line"] > c["line"] and d["non_empty"] for d in delivered))]
        return {
            "activated": bool(succeeded),
            "marker": {"skill_tool_calls": skill_calls,
                       "delivered_body_records": delivered,
                       "recheck_v2_calls_with_a_delivered_body": succeeded},
            "profile_section": "adapters/claude-code/profile.md section 8 (the delivered body "
                               "as one user record flagged isSynthetic in the trace, after the "
                               "Skill tool call); E10-46: a call with no delivered body is not "
                               "an activation",
        }

    def permission_denials(self, out_dir):
        """The `system` / `permission_denied` events of this session's own trace (E10-68 (2)).

        A denial is the measurement that a headless session had no approval surface: Claude
        Code writes one `system` record per auto-denied tool call, carrying `tool_name`,
        `tool_use_id`, `decision_reason_type` and a plain-STRING `message`. The string is what
        crashed `activation`; the event itself is worth keeping, so the count and the tool
        names go into `command.json` under `permission_denials` and the E11 report can say how
        often headless denial happened per harness. No message text is copied — the sentence
        carries the path the model was denied, which is the trial's own opaque tree.
        """
        events, tools = [], {}
        for name in ("trace.jsonl", "transcript.jsonl"):
            path = os.path.join(out_dir, name)
            for line, record in enumerate(jsonl_lines(path), 1):
                if record.get("type") != "system" \
                        or record.get("subtype") != PERMISSION_DENIED_SUBTYPE:
                    continue
                tool = record.get("tool_name") or "unknown"
                tools[tool] = tools.get(tool, 0) + 1
                events.append({"file": "harness/%s" % name, "line": line, "tool": tool,
                               "tool_use_id": record.get("tool_use_id"),
                               "decision_reason_type": record.get("decision_reason_type"),
                               "message_is_a_string": isinstance(record.get("message"), str)})
        return {"count": len(events), "tools": sorted(tools),
                "by_tool": tools, "events": events,
                "how": "system events of subtype permission_denied in the session's own trace "
                       "and transcript (E10-68 defect 2)"}


def bound_model_record(record):
    """A model record with NO SESSION BINDING is `null` (E10-50, E10-59 (18)).

    The native label is not the measurement: what E10-50 asks for is the model THIS session
    recorded, and a record whose model cannot be tied to the session the launch produced is
    not that. The reviewer's probe supplied one assistant record carrying a model and no
    session identity at all, and the reader returned the label with `session_binding: null`
    beside it. The unbound observation is kept under its own name so nothing is lost.
    """
    if record.get("session_binding_ok"):
        return record
    record["observed_without_a_session_binding"] = {
        "id": record.get("id"), "model_id": record.get("model_id"),
        "provider": record.get("provider"), "effort": record.get("effort"),
        "source": record.get("source"),
        "why": "the native record carries no session binding, so it is not a measurement of "
               "this session's model (E10-50, E10-59 (18))"}
    for field in ("id", "model_id", "provider", "effort", "source"):
        if field in record:
            record[field] = None
    return record


def _step_summary(step):
    """A child's record for a `command.json` or an install record: no stdout flood."""
    return {
        "argv": step["argv"],
        "label": step.get("label"),
        "exit": step["exit"],
        "timed_out": step.get("timed_out"),
        "wall_seconds": step.get("wall_seconds"),
        "stdout_tail": (step.get("stdout") or "")[-2000:],
        "stderr_tail": (step.get("stderr") or "")[-2000:],
    }


# ------------------------------------------------------------------ Codex CLI


# E10-59 (12, 13): a Codex read is DELIVERED only when its `function_call_output` reports
# success, and a refused read is neither an activation nor a routing target. The rollout
# records the call and its result as two records joined by `call_id`; the first two rounds
# read the call alone, so a `cat .../SKILL.md` answered `Permission denied; exit code 1`
# counted as an activation and was selected as the routing target.

CODEX_FAILED_OUTPUT_RE = re.compile(
    r"(?i)(permission denied|operation not permitted|not permitted|\baborted\b|\brejected\b|"
    r"no such file|command failed|sandbox_apply|timed out|timeout)")
CODEX_EXIT_RE = re.compile(r"(?i)\bexit(?:\s+code)?[\s:=]+(-?\d+)")


def codex_output_ok(output):
    """Whether one `function_call_output` reports success. Returns `(ok, why)`."""
    if output is None:
        return None, "the output record carries no output"
    parsed = output if isinstance(output, dict) else None
    text = output if isinstance(output, str) else json.dumps(output)
    if parsed is None:
        try:
            got = json.loads(text)
        except ValueError:
            got = None
        parsed = got if isinstance(got, dict) else None
    if parsed is not None:
        for key in ("exit_code", "exitCode", "exit"):
            if isinstance(parsed.get(key), int):
                return parsed[key] == 0, "the output's %s is %s" % (key, parsed[key])
        if parsed.get("success") is False:
            return False, "the output reports success false"
        for key in ("output", "stdout", "content", "text"):
            if isinstance(parsed.get(key), str):
                text = parsed[key]
                break
    found = CODEX_EXIT_RE.search(text)
    if found:
        return int(found.group(1)) == 0, "the output reports exit %s" % found.group(1)
    hit = CODEX_FAILED_OUTPUT_RE.search(text)
    if hit:
        return False, "the output reports %r" % hit.group(1)
    return True, "the output carries no failure marker"


def codex_call_outputs(rows):
    """`{call_id: {line, output}}` over a rollout's `function_call_output` records."""
    outputs = {}
    for index, record in enumerate(rows, 1):
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else record
        if not isinstance(payload, dict):
            continue
        nodes = [payload]
        if isinstance(payload.get("item"), dict):
            nodes.append(payload["item"])
        for node in nodes:
            if (node.get("type") or "") != "function_call_output":
                continue
            call = node.get("call_id") or node.get("callId") or node.get("id")
            if call:
                outputs[call] = {"line": index, "output": node.get("output")}
    return outputs


def codex_delivery_status(payload, item, outputs):
    """`(status, why)` for one Codex tool record: `completed`, `refused` or `unknown`."""
    item = item if isinstance(item, dict) else {}
    for node in (item, payload):
        for key in ("exit_code", "exitCode"):
            if isinstance(node.get(key), int):
                return ("completed" if node[key] == 0 else "refused",
                        "the record's own %s is %s" % (key, node[key]))
    call = payload.get("call_id") or item.get("call_id") or payload.get("callId")
    node_type = payload.get("type") or item.get("type") or ""
    if call and (node_type == "function_call" or call in outputs):
        row = outputs.get(call)
        if row is None:
            return ("unknown", "no function_call_output is joined to call %s, so the read is "
                               "not a delivery (E10-59 (12))" % call)
        ok, why = codex_output_ok(row["output"])
        if ok is None:
            return "unknown", "the output record for call %s is empty" % call
        return ("completed" if ok else "refused",
                "its function_call_output at rollout line %d: %s" % (row["line"], why))
    blob = json.dumps(payload)
    if "aborted" in blob or "rejected" in blob or "not permitted" in blob:
        return "refused", "the record itself carries a refusal marker"
    return ("unknown", "no result record is joined to this call, so the read is not a "
                       "delivery (E10-59 (12))")


class CodexSetup(Setup):
    harness = "codex"

    def launch_env(self, condition):
        return {"RECHECK_CODEX_HOME": self.home(condition)}

    def _link_auth(self, home, base):
        """Every derived or second home points at the base home's one credential store.

        The credential stays one file: `install.sh` writes a copy into whatever home it built,
        and it is replaced here by a link to the available home's store, exactly as the
        `plugin-only` and `host-only` surfaces do (E9-26(c)). Nothing here reads the value.
        """
        linked = []
        for auth in [os.path.join(home, "auth.json"), os.path.join(home, "child", "auth.json")]:
            if os.path.lexists(auth):
                os.unlink(auth)
            ensure_dir(os.path.dirname(auth))
            os.symlink(os.path.join(base, "auth.json"), auth)
            linked.append(os.path.relpath(auth, home))
        return linked

    def _write_model_lines(self, home):
        """E10-62 item 2: the plan's model and effort, in THIS home's two `config.toml` files.

        `setups/codex/install.sh` copies exactly three lines out of the machine's own
        `~/.codex/config.toml` — `model`, `model_reasoning_effort` and `sandbox_mode` — and
        fails if it does not find exactly three. The plan replaces the first two, in the pilot
        home and its child home only. `~/.codex/config.toml` and `~/.codex/auth.json` are
        never written by any path here (the script reads the first and copies the second), and
        `sandbox_mode` keeps coming from the real config because the plan says nothing about
        it. `codex exec` takes no `-m` in `setups/codex/launch.sh`, so the config is what the
        session runs on.
        """
        written = []
        if not (self.model or self.effort):
            return {"written": written,
                    "why_not": "the plan's setup entry named no model and no effort"}
        wanted = []
        if self.model:
            wanted.append(("model", self.model))
        if self.effort:
            wanted.append(("model_reasoning_effort", self.effort))
        for path in (os.path.join(home, "config.toml"),
                     os.path.join(home, "child", "config.toml")):
            if not os.path.isfile(path):
                continue
            text = read_text(path) or ""
            lines, changed = text.splitlines(), {}
            for index, line in enumerate(lines):
                for key, value in wanted:
                    if re.match(r"^%s\s*=" % re.escape(key), line):
                        lines[index] = '%s = %s' % (key, json.dumps(value))
                        changed[key] = value
            missing = [k for k, _ in wanted if k not in changed]
            if missing:
                raise Failure("%s holds no %s line to replace; `install.sh` writes the three "
                              "lines it copies from the real config (E10-62 item 2)"
                              % (path, " or ".join(missing)))
            write_text(path, "\n".join(lines) + "\n")
            written.append({"file": os.path.relpath(path, home), "keys": sorted(changed)})
        return {"written": written, "model": self.model, "effort": self.effort,
                "sandbox_mode": "untouched: still the line install.sh copied from the real "
                                "config (E10-62 item 2)",
                "machine_codex_home": "never written"}

    def install(self, condition, fake=None):
        """`available` and `absent` are each their own `install.sh` run; `routing` is derived.

        E10-58(2): `setups/codex/install.sh` honours `RECHECK_CODEX_HOME` (the name
        `verify-install.sh` and `launch.sh` already read), so the `absent` home is built by the
        script itself with `--without recheck-v2` (E10-56(1)) and **never held the skill on any
        surface** (E10-3): no plugin registry entry, no cache copy, no host-skill folder, and a
        catalog without it. Its `auth.json` is then linked to the available home's store the
        way the derived homes do.

        `routing` stays what it was: a copy of the installed home with the absolute paths
        rewritten (the way `install.sh` makes its own `homes/plugin-only` and `homes/host-only`
        surfaces), plus the extra plugins added. Labelled `derived_from_available`.
        """
        base = self.home("available")
        env = self.campaign.env()
        steps = []
        if condition == "available":
            steps.append(run_cmd(["sh", self.script("install.sh")],
                                 env=self.campaign.env(extra={"RECHECK_CODEX_HOME": base}),
                                 label="install.sh"))
            return {"home": base, "condition": condition, "derived_from_available": False,
                    "recheck_v2_installation": {"how": "installed", "by": "install.sh"},
                    "model_lines": self._write_model_lines(base),
                    "steps": [_step_summary(s) for s in steps]}
        if not os.path.isdir(base):
            raise Missing("install the codex `available` home before %r" % condition)
        home = self.home(condition)
        if condition == "absent":
            # E10-58(2): the script's own run, pointed at this home by the one name it now
            # honours, with the one install step of the skill skipped.
            if os.path.isdir(home):
                rmtree(home)
            ensure_dir(os.path.dirname(home))
            steps.append(run_cmd(
                ["sh", self.script("install.sh"), "--without", "recheck-v2"],
                env=self.campaign.env(extra={"RECHECK_CODEX_HOME": home}),
                label="install.sh --without recheck-v2"))
            linked = self._link_auth(home, base)
            ensure_dir(os.path.join(home, "child", "uv-cache"))
            return {
                "home": home, "condition": condition, "derived_from_available": False,
                "removed": [],
                "recheck_v2_installation": {
                    "how": "never installed",
                    "by": "install.sh --without recheck-v2",
                    "home_pointed_by": "RECHECK_CODEX_HOME (E10-58(2)); the name only, never "
                                       "a value, is recorded in the install record",
                    "surfaces_it_never_reached": ["the plugin registry (`codex plugin add` "
                                                  "skipped)", "the plugin cache",
                                                  "the host-skill folder", "the session catalog"],
                },
                "auth_linked_to_the_available_store": linked,
                "model_lines": self._write_model_lines(home),
                "added": [], "steps": [_step_summary(s) for s in steps],
            }
        if os.path.isdir(home):
            rmtree(home)
        ensure_dir(os.path.dirname(home))
        shutil.copytree(base, home, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "sessions"))
        self._link_auth(home, base)
        for path in [os.path.join(home, "config.toml")] + \
                glob.glob(os.path.join(home, "plugins", "**", "*.json"), recursive=True) + \
                [os.path.join(home, "child", "config.toml")]:
            if os.path.isfile(path):
                text = read_text(path) or ""
                write_text(path, text.replace(base, home))
        ensure_dir(os.path.join(home, "child", "uv-cache"))
        removed, added = [], []
        # Only `routing` reaches here (E10-58(2)): the copy of the installed home, plus every
        # unblocked plugin added by the harness's own mechanism.
        manifest = read_json(os.path.join(self.stage, ".claude-plugin", "marketplace.json"))
        for plugin in [p["name"] for p in manifest.get("plugins", [])]:
            if plugin in BLOCKED_PLUGINS or plugin == "recheck-v2":
                continue
            steps.append(run_cmd(
                ["codex", "plugin", "add", "%s@tony-skills" % plugin, "--json"],
                env=dict(env, CODEX_HOME=home), label="plugin add %s" % plugin))
            added.append(plugin)
        return {"home": home, "condition": condition, "derived_from_available": True,
                "removed": removed,
                "recheck_v2_installation": {"how": "installed",
                                            "by": "the copy of the available home"},
                # The copy already carries the available home's two lines; rewriting them here
                # keeps the record explicit and survives a plan change between the two installs.
                "model_lines": self._write_model_lines(home),
                "added": added, "steps": [_step_summary(s) for s in steps]}

    def verify(self, condition):
        home = self.home(condition)
        env = self.campaign.env(extra={"RECHECK_CODEX_HOME": home})
        return run_cmd(["sh", self.script("verify-install.sh")], env=env, label="verify-install.sh")

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None,
               registry=None):
        home = self.home(condition)
        env = self.campaign.env(extra={"RECHECK_CODEX_HOME": home})
        argv = ["sh", fake or self.script("launch.sh"), prompt_file, workspace, out_dir]
        if registry is not None:
            registry.reserved(argv, "launch.sh")
        return run_cmd(argv, env=env, timeout=timeout, label="launch.sh", registry=registry)

    def catalog(self, condition, out_dir):
        """`codex plugin list` under the condition's home: the harness's own catalog record."""
        home = self.home(condition)
        env = self.campaign.env(extra={"CODEX_HOME": home})
        if not os.path.isdir(home):
            # The launcher's own catalog capture, when it wrote one, is still the session's
            # record; only when neither exists is the catalog missing (E10-46).
            captured = read_text(os.path.join(out_dir, "catalog.txt"))
            if captured:
                return {"kind": "codex plugin list", "exit": 0, "record": captured,
                        "note": "read from the launcher's own catalog capture; no codex home "
                                "at %s" % home}
            return {"kind": "codex plugin list", "exit": None, "record": None,
                    "note": "no codex home at %s, so this home recorded no catalog" % home}
        step = run_cmd(["codex", "plugin", "list"], env=env, label="plugin list")
        write_text(os.path.join(out_dir, "catalog.txt"), step["stdout"] + step["stderr"])
        return {"kind": "codex plugin list", "exit": step["exit"], "record": step["stdout"]}

    # ---- records
    def _rollout(self, out_dir):
        return jsonl_lines(os.path.join(out_dir, "rollout.jsonl"))

    def model_record(self, out_dir):
        """Codex: `turn_context` in the rollout carries `model` and `effort` (E9 section 7).

        E10-50: bound to the thread the `session_meta` record names, `null` when the rollout
        carries no such event, and the launcher's own label kept apart as `configured`.
        """
        rows = list(enumerate(self._rollout(out_dir), 1))
        session = None
        # E10-62 item 4: the plan's pair. `setups/codex/launch.sh`'s `launch.json` carries
        # `exit`, `thread_id` and `rollout` and no model key at all, so this read was `null`
        # on every Codex trial; the model and the effort reach the session through the pilot
        # home's `config.toml`, which `CodexSetup.install` writes from the plan.
        configured = self.configured_record()
        configured["reaches_the_session_by"] = (
            "the pilot home's config.toml `model` and `model_reasoning_effort` lines, written "
            "by CodexSetup.install (E10-62 item 2); `codex exec` takes no -m")
        for _, record in rows:
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            if (record.get("type") or payload.get("type")) == "session_meta":
                session = payload.get("id") or payload.get("session_id")
                break
        model_id, effort, source, bound = None, None, None, None
        for line, record in rows:
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            kind = record.get("type") or payload.get("type")
            if kind == "turn_context":
                model_id = payload.get("model", model_id)
                effort = payload.get("effort", effort)
                source = "harness/rollout.jsonl line %d turn_context" % line
                bound = session
            elif kind == "session_meta" and model_id is None and payload.get("model"):
                model_id = payload.get("model")
                source = "harness/rollout.jsonl line %d session_meta" % line
                bound = session
        return bound_model_record({
            "id": model_id, "effort": effort, "source": source,
            "session_binding": bound,
            "session_binding_ok": bool(session) and bound == session,
            "configured": configured,
            "note": "E10-50: null when the rollout carries no turn_context or session_meta, "
                    "and null when the record carries no session binding (E10-59 (18))"})

    def cost_record(self, out_dir):
        """Codex prints token counts, never a dollar figure (`total_cost_usd` stays null)."""
        tokens, source = None, None
        for record in jsonl_lines(os.path.join(out_dir, "events.jsonl")):
            for key in ("token_count", "usage", "token_usage"):
                if isinstance(record.get(key), dict):
                    tokens, source = record[key], "events.jsonl %s" % key
            info = (record.get("msg") or {}) if isinstance(record.get("msg"), dict) else {}
            if isinstance(info.get("info"), dict):
                tokens, source = info["info"], "events.jsonl msg.info"
        return {"total_cost_usd": None, "tokens": tokens, "source": source}

    def condition_witness(self, out_dir, condition):
        """The SESSION's active catalog, not the home's marketplace listing (E10-46).

        Finding 12: the real Codex absent trial said `recheck_v2_in_catalog: true` because
        `catalog.txt` — `codex plugin list` under that home — listed the uninstalled
        marketplace entry. The session's own developer `<skills_instructions>` message is the
        catalog the model actually had; `catalog.txt` is kept beside it as the home's listing
        and no longer decides the witness.
        """
        names, source, line = None, None, None
        for index, record in enumerate(self._rollout(out_dir), 1):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            if payload.get("type") != "message":
                continue
            blob = json.dumps(payload)
            if "skills_instructions" not in blob and "<skill" not in blob:
                continue
            names = sorted(set(re.findall(r"(?:^|[\s\"'>\-])([a-z][a-z0-9-]{2,40})(?=\s*[:\-])",
                                          blob)))
            explicit = sorted(set(re.findall(r"<skill[^>]*name=\"([a-z0-9-]+)\"", blob)))
            names = sorted(set(names + explicit))
            source = ("harness/rollout.jsonl line %d, the session's own developer catalog "
                      "message" % index)
            line = index
            break
        catalog_file = read_text(os.path.join(out_dir, "catalog.txt")) or ""
        return {
            "condition": condition,
            "witness": {"session_catalog_names": names,
                        "home_plugin_list": catalog_file[:4000]},
            "recheck_v2_in_catalog": ("recheck-v2" in names) if names is not None else None,
            "file": "harness/rollout.jsonl" if names is not None else None,
            "line": line,
            "home_listing_says": ("recheck-v2" in catalog_file) if catalog_file else None,
            "source": source or ("no developer catalog message in the session's own rollout; "
                                 "`codex plugin list` under the home is recorded beside it and "
                                 "does NOT decide this witness (E10-46)"),
        }

    def activation(self, out_dir):
        """A COMPLETED read of the installed SKILL.md, or an injected `<skill>` body (E10-46).

        Codex profile section 8: implicit selection is a file read of the installed
        `SKILL.md`; the explicit `$name` route injects a `<skill>` user message. Finding 12:
        the developer catalog message naming recheck-v2 is NOT an activation, and a read whose
        command was refused is not one either. Every witness keeps its rollout line.

        E10-59 (12): "refused" is decided by the read's OWN RESULT RECORD — the
        `function_call_output` joined to it by `call_id` — not by scanning the call record for
        words. A `cat .../SKILL.md` whose output reads `Permission denied; exit code 1` is not
        a delivery, and a call with no result record joined to it is `unknown`, which is not
        one either.
        """
        rows = list(self._rollout(out_dir))
        outputs = codex_call_outputs(rows)
        reads, injected = [], []
        for index, record in enumerate(rows, 1):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            blob = json.dumps(payload)
            if payload.get("type") == "message" and "skills_instructions" in blob:
                continue     # the catalog message is not a read
            item = payload.get("item") or {}
            command = item.get("command") or payload.get("command")
            if isinstance(command, list):
                command = " ".join(str(x) for x in command)
            arguments = payload.get("arguments") or item.get("arguments")
            if not isinstance(command, str) and isinstance(arguments, str):
                try:
                    parsed = json.loads(arguments)
                    got = parsed.get("command")
                    if got is None:
                        got = parsed.get("cmd")
                    command = " ".join(str(x) for x in got) if isinstance(got, list) else got
                except (ValueError, AttributeError):
                    command = None
            if isinstance(command, str) and "recheck-v2/SKILL.md" in command:
                status, why = codex_delivery_status(payload, item, outputs)
                reads.append({"line": index, "command": command[:240],
                              "call_id": payload.get("call_id") or item.get("call_id"),
                              "status": status, "why": why})
            matched = re.search(r"<skill[^>]*name=\"(recheck-v2)\"", blob)
            if matched:
                injected.append({"line": index, "bytes": len(blob), "skill": matched.group(1)})
        completed = [r for r in reads if r["status"] == "completed"]
        return {
            "activated": bool(completed or injected),
            "marker": {"installed_skill_reads": reads[:6],
                       "completed_reads": completed[:6],
                       "not_delivered": [r for r in reads if r["status"] != "completed"][:6],
                       "injected_skill_messages": injected[:4]},
            "profile_section": "adapters/codex/profile.md section 8 (implicit selection "
                               "requires a COMPLETED file read of the installed SKILL.md; the "
                               "explicit route injects a <skill> user message). E10-46: the "
                               "developer catalog message is neither. E10-59 (12): delivery is "
                               "the call's own function_call_output reporting success.",
        }


# ------------------------------------------------------------------ OpenCode


# E10-68's close hand-off, item (e). `install` used to leave the OpenCode home's own working
# state — `xdg-data/opencode/{log, snapshot, opencode.db, tool-output, repos}` and
# `xdg-state/opencode/locks` — from earlier campaigns in place, and in the absent trials of
# 2026-09-15 the model reached prior campaign roots' paths through the harness. `install` now
# clears that state before it runs the script, keeping exactly two things: the harness's own
# auth store (E9-38, E10-20 — the credential is written once at install time and must survive
# a reinstall) and anything outside those two directories.
#
# `xdg-cache/` is DELIBERATELY NOT CLEARED, and the install record says so: `xdg-cache/uv`
# holds the uv wheel, sdist and interpreter caches every `uv run` of a trial and of
# `verify-install.sh` resolves against, and `xdg-cache/opencode/bin` holds the harness's own
# downloaded binaries. Clearing either turns each install and each verifier call into a fresh
# network fetch immediately before a campaign, which is a new failure mode rather than a
# cleaner one, and the binary is the one thing E10-68 names as off limits. Neither holds a
# session, a transcript or a path from an earlier campaign root.
OPENCODE_CLEARED_STATE = ("xdg-data", "xdg-state")
OPENCODE_STATE_KEPT = ("auth.json",)
OPENCODE_CACHE_NOT_CLEARED = (
    "xdg-cache/ is not cleared: xdg-cache/uv is the uv wheel and interpreter cache every "
    "`uv run` resolves against and xdg-cache/opencode/bin is the harness's own binary "
    "(E10-68 names the binary as off limits); neither carries a session or a prior campaign "
    "root's path.")


def _tree_bytes(path):
    """The size of one file, link or tree, for the install record's own account."""
    if os.path.islink(path) or os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return None
    total = 0
    for base, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                continue
    return total


class OpenCodeSetup(Setup):
    harness = "opencode"
    # `setups/opencode/install.sh`'s own `--model` default, and `launch.sh`'s `qwen` alias.
    default_model = "openrouter/qwen/qwen3.8-flash"
    # The two sub-setups the OpenCode scripts carry. `launch.sh` takes `qwen`, `deepseek` or a
    # full `provider/model` id; `install.sh --model` takes the full id only. E10-62 pins the
    # plan to the full ids, and the short names stay accepted so an E9-shaped plan still runs.
    MODEL_ALIASES = {"qwen": "openrouter/qwen/qwen3.8-flash",
                     "deepseek": "openrouter/deepseek/deepseek-v4.1-flash"}

    def resolved_model(self):
        """The full `provider/model` id, from a short alias or from the plan's own id."""
        return self.MODEL_ALIASES.get(self.model, self.model or self.default_model)

    def launch_env(self, condition):
        return {"RECHECK_OPENCODE_SETUP": self.home(condition)}

    def binary(self, condition):
        return os.path.join(self.home(condition), "npm", "node_modules", ".bin", "opencode")

    def skill_dir(self, condition):
        return os.path.join(self.home(condition), "xdg-config", "opencode", "skill")

    def install(self, condition, fake=None):
        """`install.sh --setup DIR --model M` targets any home, so all three are real installs.

        `absent` removes the skill folder afterwards, which is this harness's own mechanism:
        the loader reads its `skill/` directories and a folder that is not there is not in the
        catalog (E9-27, profile section 8). E10-20: this is the one path that passes
        OPENROUTER_API_KEY, and only to this script.
        """
        home = self.home(condition)
        cleared = self._clear_prior_state(home)
        credential = os.environ.get(INSTALL_CREDENTIAL)
        extra = {"RECHECK_OPENCODE_SETUP": home}
        if credential:
            extra[INSTALL_CREDENTIAL] = credential
        env = self.campaign.env(extra=extra)
        # E10-62 item 2: the plan's own `openrouter/...` id passes through as it is written,
        # and the short `qwen` / `deepseek` names an E9-shaped plan uses still resolve.
        model = self.resolved_model()
        argv = ["sh", self.script("install.sh"), "--setup", home, "--model", model]
        # E10-56(1): the absent home's install never copies the skill folder in, so the runner
        # no longer removes one afterwards.
        if condition == "absent":
            argv += ["--without", "recheck-v2"]
        steps = [run_cmd(argv, env=env, label="install.sh")]
        removed, added = [], []
        if condition == "absent":
            installation = {
                "how": "never installed",
                "by": "install.sh --without recheck-v2 (E10-56(1))",
                "second_guard_removal": "dropped: no skill folder is removed",
            }
        else:
            installation = {"how": "installed", "by": "install.sh"}
        if condition == "routing":
            # E10-13: every plugin's skill folders copied into this home's skill directory.
            for plugin_dir in sorted(glob.glob(os.path.join(self.stage, "plugins", "*"))):
                plugin = os.path.basename(plugin_dir)
                if plugin in BLOCKED_PLUGINS:
                    continue
                for skill in sorted(glob.glob(os.path.join(plugin_dir, "skills", "*"))):
                    name = os.path.basename(skill)
                    if name in BLOCKED_PLUGINS or not os.path.isfile(os.path.join(skill, "SKILL.md")):
                        continue
                    dest = os.path.join(self.skill_dir(condition), name)
                    if os.path.isdir(dest):
                        rmtree(dest)
                    shutil.copytree(skill, dest,
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    added.append(name)
        return {"home": home, "condition": condition, "model": model,
                "credential_passed": bool(credential),
                "removed": removed, "recheck_v2_installation": installation,
                "prior_state_cleared": cleared,
                "added": sorted(set(added)),
                "steps": [_step_summary(s) for s in steps]}

    def _clear_prior_state(self, home):
        """Clear this home's prior-campaign working state (E10-68's item (e)).

        Everything under `xdg-data/opencode/` and `xdg-state/opencode/` goes except the auth
        store; `xdg-cache/` and the `npm/` binary tree are left alone, for the reason
        `OPENCODE_CACHE_NOT_CLEARED` states. The record names every path removed and its size,
        and every path kept with why.
        """
        removed, kept = [], []
        for sub_dir in OPENCODE_CLEARED_STATE:
            base = os.path.join(home, sub_dir, "opencode")
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                path = os.path.join(base, name)
                if name in OPENCODE_STATE_KEPT or name.startswith("auth"):
                    kept.append({"path": path,
                                 "why": "the harness's own auth store; the credential is "
                                        "written once at install time (E9-38, E10-20)"})
                    continue
                size = _tree_bytes(path)
                rmtree(path)
                removed.append({"path": path, "bytes": size})
        return {"removed": removed, "kept": kept,
                "directories": [os.path.join(home, d, "opencode")
                                for d in OPENCODE_CLEARED_STATE],
                "not_cleared": OPENCODE_CACHE_NOT_CLEARED,
                "rule": "E10-68 item (e): `install` clears the OpenCode home's own prior-"
                        "campaign state so no trial reaches an earlier campaign root through "
                        "the harness; the auth store and the binary stay."}

    def verify(self, condition):
        home = self.home(condition)
        env = self.campaign.env(extra={"RECHECK_OPENCODE_SETUP": home})
        return run_cmd(["sh", self.script("verify-install.sh"), "--setup", home], env=env,
                       label="verify-install.sh")

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None,
               registry=None):
        home = self.home(condition)
        env = self.campaign.env(extra={
            "RECHECK_OPENCODE_SETUP": home,
            "RECHECK_OPENCODE_TIMEOUT": str(int(timeout)) if timeout else "900",
        })
        # The full id, not the alias: `launch.sh` takes either (`qwen | deepseek | provider/
        # model`), and the record then names the model the session actually ran on.
        model = self.MODEL_ALIASES.get((extra or {}).get("model"), (extra or {}).get("model")) \
            or self.resolved_model()
        argv = ["sh", fake or self.script("launch.sh"), model, prompt_file, workspace, out_dir]
        agent = (extra or {}).get("agent")
        if agent:
            argv += ["--agent", agent]
        if registry is not None:
            registry.reserved(argv, "launch.sh")
        return run_cmd(argv, env=env, timeout=(timeout + 120) if timeout else None,
                       label="launch.sh", registry=registry)

    def catalog(self, condition, out_dir):
        """`opencode debug skill`: the loader's own catalog listing, no model call."""
        home = self.home(condition)
        env = self.campaign.env(extra={
            "XDG_CONFIG_HOME": os.path.join(home, "xdg-config"),
            "XDG_DATA_HOME": os.path.join(home, "xdg-data"),
            "XDG_CACHE_HOME": os.path.join(home, "xdg-cache"),
            "XDG_STATE_HOME": os.path.join(home, "xdg-state"),
            "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
        })
        binary = self.binary(condition)
        if not os.path.isfile(binary):
            captured = os.path.join(out_dir, "catalog.json")
            if os.path.isfile(captured):
                try:
                    names = sorted(e.get("name") for e in read_json(captured))
                except (Failure, Missing, TypeError, AttributeError):
                    names = None
                return {"kind": "opencode debug skill", "exit": 0, "record": names,
                        "capture": captured,
                        "note": "read from the launcher's own catalog capture; no opencode "
                                "binary at %s" % binary}
            return {"kind": "opencode debug skill", "exit": None, "record": None,
                    "note": "no opencode binary at %s, so this home recorded no catalog" % binary}
        # Into a file, not a pipe: see run_cmd's note about the 64 KiB truncation.
        capture = os.path.join(out_dir, "catalog.json")
        ensure_dir(out_dir)
        step = run_cmd([binary, "debug", "skill"], env=env, label="debug skill",
                       stdout_path=capture)
        names, bytes_seen = None, os.path.getsize(capture) if os.path.isfile(capture) else 0
        try:
            names = sorted(e.get("name") for e in read_json(capture))
        except (Failure, Missing, TypeError, AttributeError):
            names = None
        return {"kind": "opencode debug skill", "exit": step["exit"], "record": names,
                "capture_bytes": bytes_seen, "capture": capture}

    # ---- records
    def _session(self, out_dir):
        path = os.path.join(out_dir, "session.json")
        return read_json(path) if os.path.isfile(path) else {}

    def model_record(self, out_dir):
        """OpenCode: the session store's assistant rows carry `modelID` and `providerID`.

        E10-50: bound to the session id the store names, `null` when no such row exists, and
        the model the LAUNCHER was given kept apart as `configured`. The store has no
        reasoning-effort field on 1.18.31, so `effort` is null, never a label (E10-19).
        """
        session = self._session(out_dir)
        session_id = session.get("session_id")
        # E10-62 item 4: the plan's pair. `setups/opencode/launch.sh` writes no `launch.json`
        # at all, so this read was `null` on every OpenCode trial; the model reaches the
        # session as the launcher's first argument. `effort` is `null` on both OpenCode lanes
        # because the plan may not carry one (E10-26, validate_plan refuses it).
        configured = self.configured_record()
        configured["reaches_the_session_by"] = (
            "launch.sh's first argument, `opencode run --model <id>` (E10-62 item 2)")
        model_id, provider, source, bound = None, None, None, None
        for index, record in enumerate(session.get("records", []), 1):
            data = record.get("data") or {}
            if data.get("role") == "assistant" and data.get("modelID"):
                model_id, provider = data["modelID"], data.get("providerID")
                source = ("harness/session.json records[%d].data.modelID (the session store's "
                          "message rows)" % index)
                bound = session_id
        return bound_model_record({
            "id": ("%s/%s" % (provider, model_id)) if provider and model_id else model_id,
            "model_id": model_id, "provider": provider, "effort": None, "source": source,
            "session_binding": bound,
            "session_binding_ok": bool(session_id) and bound == session_id,
            "configured": configured,
            "note": "E10-50: null when the store carries no assistant row, and null when the "
                    "record carries no session binding (E10-59 (18)); OpenCode 1.18.31 "
                    "records no reasoning effort (E10-26)"})

    def cost_record(self, out_dir):
        session = self._session(out_dir)
        total, tokens = None, {}
        for record in session.get("records", []):
            data = record.get("data") or {}
            if isinstance(data.get("cost"), (int, float)):
                total = (total or 0.0) + data["cost"]
            if isinstance(data.get("tokens"), dict):
                for key, value in data["tokens"].items():
                    if isinstance(value, (int, float)):
                        tokens[key] = tokens.get(key, 0) + value
        return {"total_cost_usd": round(total, 8) if total is not None else None,
                "tokens": tokens or None,
                "source": "session.json records[].data.cost and .tokens" if total is not None else None}

    def condition_witness(self, out_dir, condition):
        catalog_path = os.path.join(out_dir, "catalog.json")
        names = None
        if os.path.isfile(catalog_path):
            try:
                names = sorted(e.get("name") for e in read_json(catalog_path))
            except (Failure, Missing, TypeError, AttributeError):
                names = None
        return {
            "condition": condition,
            "witness": {"catalog_names": names},
            "recheck_v2_in_catalog": ("recheck-v2" in (names or [])) if names is not None else None,
            "file": "harness/catalog.json" if names is not None else None,
            "line": None,
            "source": "opencode debug skill under the condition's home (the loader's own "
                      "catalog record; this harness writes no init event into the session, "
                      "E10-26)",
        }

    def activation(self, out_dir):
        """A `skill` tool call that COMPLETED with a delivered body (E10-46, finding 12).

        Profile section 8: the native `skill` tool call whose output is the
        `<skill_content name="recheck-v2">` block. A call with `status: error` and zero output
        is not an activation; `final_probes.py` got `activated: true` for exactly that. The
        message and part ids are retained.
        """
        calls = []
        for record in self._session(out_dir).get("records", []):
            for part in record.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                data = part.get("data") or {}
                if data.get("tool") == "skill":
                    state = data.get("state") or {}
                    output = state.get("output") or ""
                    calls.append({
                        "call_id": data.get("callID"),
                        "message_id": record.get("message_id"),
                        "part_id": part.get("id"),
                        "input": state.get("input"),
                        "status": state.get("status"),
                        "output_chars": len(output),
                        "delivered_block": "<skill_content" in output,
                    })
        for record in jsonl_lines(os.path.join(out_dir, "trace.json")):
            part = record.get("part") or {}
            if part.get("tool") == "skill" and not calls:
                state = part.get("state") or {}
                output = state.get("output") or ""
                calls.append({"call_id": part.get("callID"), "message_id": record.get("sessionID"),
                              "part_id": part.get("id"), "input": state.get("input"),
                              "status": state.get("status"), "output_chars": len(output),
                              "delivered_block": "<skill_content" in output})
        delivered = [c for c in calls
                     if (c.get("input") or {}).get("name") == "recheck-v2"
                     and c.get("status") == "completed" and c.get("output_chars", 0) > 0]
        return {
            "activated": bool(delivered),
            "marker": {"skill_tool_calls": calls, "delivered": delivered},
            "profile_section": "adapters/opencode/profile.md section 8 (the native skill tool "
                               "call returning the <skill_content name=\"recheck-v2\"> block); "
                               "E10-46: a call with status error or no output is not one",
        }

    def store_separation_witness(self, out_dir):
        """E10-49 (finding 17): the VERIFIER CHILD's own rows, located by its call and session id.

        The old reader scanned the DRIVING session's rows for a read of the driving store and
        reported `measured: true` whatever it found — and an empty capture returned
        `driving_session: null`, no reads, `measured: true`. The real compaction record has
        exactly that empty shape. Now: find the verifier child by the call that spawned it,
        retain its rows, inspect THOSE rows, and say `unavailable` when there are none.
        """
        session = self._session(out_dir)
        driving = session.get("session_id")
        children, rows_seen = [], 0
        # the calls that spawned a verifier child, and the session ids they name
        for record in session.get("records", []):
            for part in record.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                data = part.get("data") or {}
                state = data.get("state") or {}
                blob = json.dumps({"input": state.get("input"), "metadata": state.get("metadata"),
                                   "output": (state.get("output") or "")[:400]})
                if data.get("tool") not in ("task", "agent", "subagent", "verifier"):
                    continue
                found = re.findall(r"(ses_[A-Za-z0-9]+)", blob)
                children.append({"call_id": data.get("callID"), "tool": data.get("tool"),
                                 "child_sessions": sorted(set(found)),
                                 "message_id": record.get("message_id")})
        # E10-59 (17): the rows inspected are the rows of THE CHILD SESSION THE RECORDED CALL
        # NAMES. The old reader took any file whose name looked like a verifier capture and
        # called the measurement `measured`, so an unrelated session's rows — or a file left
        # by another trial — could establish it. The child ids come from the calls above; with
        # none, there is nothing to select and the witness is `unavailable`.
        expected_children = sorted({child for row in children
                                    for child in (row.get("child_sessions") or [])})
        child_rows, sources, rejected = [], [], []

        def collect(row, source, fallback=None):
            got = row.get("session_id") or row.get("sessionID") or row.get("sessionId") \
                or fallback
            if got and got in expected_children:
                child_rows.append(row)
                return
            rejected.append({"source": source, "session_id": got,
                             "why": "not a row of a child session the recorded call names"})

        for name in sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []:
            if not re.match(r"^(verifier|child|subagent).*\.(json|jsonl)$", name):
                continue
            path = os.path.join(out_dir, name)
            sources.append(name)
            if name.endswith(".jsonl"):
                for row in jsonl_lines(path):
                    collect(row, name)
            else:
                try:
                    document = read_json(path)
                except (Missing, Failure):
                    continue
                if not isinstance(document, dict):
                    continue
                for row in document.get("records") or []:
                    collect(row, name, document.get("session_id"))
        # a child session captured inside the driving store itself
        for record in session.get("records", []):
            if record.get("session_id") and record["session_id"] != driving:
                collect(record, "session.json")
        rows_seen = len(child_rows)
        reads = []
        for record in child_rows:
            for part in record.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                data = part.get("data") or {}
                state = data.get("state") or {}
                blob = json.dumps(state.get("input") or {})
                if "opencode.db" in blob or (driving and driving in blob):
                    reads.append({"tool": data.get("tool"), "input": blob[:200]})
        measured = rows_seen > 0
        return {"driving_session": driving,
                "verifier_calls": children,
                "child_sessions_the_calls_name": expected_children,
                "child_rows_inspected": rows_seen,
                "child_rows_rejected": rejected[:20],
                "child_rows_rejected_count": len(rejected),
                "child_row_sources": sources,
                "reads_of_the_driving_store": reads,
                "measured": measured,
                "verdict": ("no read of the driving store in the verifier child's own rows"
                            if measured and not reads else
                            ("the verifier child read the driving store" if reads else
                             "unavailable: no rows of a child session the recorded call names "
                             "were retained (E10-59 (17))")),
                "note": "E10-49: measured on the verifier child's own rows, selected by the "
                        "child session id the recorded call names (E10-59 (17)); an empty or "
                        "absent capture is `unavailable`, never `measured`."}


SETUP_CLASSES = {"claude-code": ClaudeCodeSetup, "codex": CodexSetup, "opencode": OpenCodeSetup}


def make_setup(campaign, spec):
    """One setup object from a plan entry (`{name, harness, model, effort}`) or a harness name.

    E10-62 item 2: `model` and `effort` reach EVERY class, not only OpenCode's. Each subclass
    then uses them its own way — Claude Code's two launcher flags, Codex's two `config.toml`
    lines, OpenCode's `--model` — and all three carry the pair into `model.json.configured`.
    """
    if isinstance(spec, str):
        spec = {"name": spec, "harness": spec}
    harness = spec.get("harness") or spec["name"]
    cls = SETUP_CLASSES.get(harness)
    if cls is None:
        raise Usage("unknown harness %r (one of %s)" % (harness, ", ".join(HARNESSES)))
    return cls(campaign, name=spec["name"], model=spec.get("model"),
               effort=spec.get("effort"))


# --------------------------------------------------------------------------- install / verify

FORBIDDEN_IN_A_HOME = ("answer-key", "held-out", "evals")


def home_leak_scan(home):
    """E10-6: prove with a walk that no installed home holds the key, the held-out set, or
    any `evals/` directory."""
    hits = []
    for base, dirs, files in os.walk(home):
        for name in list(dirs) + list(files):
            if name in FORBIDDEN_IN_A_HOME:
                hits.append(os.path.relpath(os.path.join(base, name), home))
    return sorted(hits)


def do_install(args):
    campaign = Campaign(args.campaign)
    campaign.ensure()
    campaign.staged()
    plan = _optional_plan(campaign)
    results = []
    for setup in _selected_setups(campaign, plan, args.setup):
        for condition in (args.home and [args.home]) or list(HOMES):
            record = setup.install(condition)
            record["setup"] = setup.name
            record["harness"] = setup.harness
            record["home_leak_scan"] = home_leak_scan(record["home"])
            # E10-40: links inside a home are surveyed and refused when they leave the pilot
            # root; the Codex derived homes' single-store `auth.json` link stays and is named.
            record["link_survey"] = link_survey(
                record["home"], allowed_targets=[PILOT_ROOT],
                forbidden_targets=protected_roots(campaign))
            # E10-53(3): each home's FULL inventory, so absence is provable afterwards.
            inventory = file_manifest(record["home"])
            path = campaign.reserve_record("home-inventory-%s-%s" % (setup.name, condition))
            write_json(path, {"setup": setup.name, "condition": condition,
                              "home": record["home"], "files": len(inventory),
                              # a home holds link farms and an npm tree; following its
                              # directory links would walk outside the home an inventory is
                              # of, so the inventory keeps the narrow walk (E10-60 (10)
                              # widened the run directory's hash, not this one).
                              "tree_sha256": tree_sha256_of(
                                  record["home"], exclude_dirs=E10_6_TREE_EXCLUDED,
                                  follow_directory_links=False),
                              # E10-56(1): the inventory says whether the skill was NEVER
                              # INSTALLED here or installed and then removed.
                              "recheck_v2_installation": record.get("recheck_v2_installation"),
                              "recheck_v2_paths_in_the_home":
                                  sorted(r["path"] for r in inventory
                                         if "recheck-v2" in r["path"])[:40],
                              "inventory": inventory})
            record["inventory_record"] = path
            record["inventory_files"] = len(inventory)
            results.append(record)
            campaign.note("install %s %s -> %s" % (setup.name, condition, record["home"]))
    document = {"campaign": campaign.root, "installs": results}
    failed = []
    for row in results:
        why = []
        if any(s["exit"] not in (0, None) for s in row["steps"]):
            why.append("a step exited non-zero")
        if row["home_leak_scan"]:
            why.append("the home holds %s" % ", ".join(row["home_leak_scan"]))
        if row["link_survey"]["symlinks_refused"]:
            why.append("a link points at the key or at a campaign record: %s"
                       % json.dumps(row["link_survey"]["symlinks_refused"][:4]))
        if why:
            failed.append(dict(row, why=why))
    document["ok"] = not failed
    document["failed"] = [{"setup": r["setup"], "condition": r["condition"], "why": r["why"]}
                          for r in failed]
    write_json(campaign.reserve_record("install"), document)
    if failed:
        raise Failure("install failed for %s"
                      % ", ".join("%s/%s (%s)" % (r["setup"], r["condition"], "; ".join(r["why"]))
                                  for r in failed))
    return document


def do_verify(args):
    campaign = Campaign(args.campaign)
    campaign.ensure()
    identity = fresh_skill_identity(campaign)
    canonical = identity["content_sha256"]
    if not identity["ok"]:
        # E10-52 (finding 26): a verification whose own identity did not compute proves
        # nothing. Exit 3, the missing-prerequisite code, before any row is written.
        raise Missing("skill-identity of the checkout did not produce a digest "
                      "(exit %s, digest %r); verification cannot compare anything"
                      % (identity["exit"], identity["content_sha256"]))
    plan = _optional_plan(campaign)
    rows, missing_homes = [], []
    for setup in _selected_setups(campaign, plan, args.setup):
        for condition in (args.home and [args.home]) or list(HOMES):
            home = setup.home(condition)
            if not os.path.isdir(home):
                # E10-52: an absent home is a MISSING PREREQUISITE (exit 3), never an
                # `ok: true` with `present: false`. "No skill in a home that does not exist"
                # is not a proof that the skill was removed.
                missing_homes.append("%s/%s (%s)" % (setup.name, condition, home))
                rows.append({"setup": setup.name, "condition": condition, "home": home,
                             "present": False, "ok": False,
                             "why": "the home does not exist, so its missing skill proves "
                                    "nothing (E10-52)"})
                continue
            step = setup.verify(condition)
            try:
                document = json.loads(step["stdout"])
            except ValueError:
                document = None
            installed_sha = _installed_content_sha(document)
            # An `absent` home holds no installed skill, so `verify-install.sh` refusing to
            # find one IS the expected outcome there, and is the second proof beside the walk
            # that E10-3's removal took (the first is `find`).
            expected_absent = condition == "absent"
            # E10-59 (26): the VERIFIER SUBPROCESS EXIT is part of the success condition. It
            # was recorded and then ignored, so a verifier that crashed after printing an
            # `ok` document with a matching digest passed (the reviewer's probe supplied
            # exit 7 and got `ok: true`). What the exit must be depends on what is expected of
            # the home: an installed home's verification must succeed (exit 0), and an absent
            # home's must FAIL to find an installed skill, which is how each
            # `verify-install.sh` reports that state (measured: codex/absent exits 1).
            expected_exit = "non-zero" if expected_absent else 0
            verify_exit_ok = (step["exit"] != 0) if expected_absent else (step["exit"] == 0)
            rows.append({
                "setup": setup.name, "condition": condition, "home": home, "present": True,
                "verify_exit": step["exit"],
                "verify_exit_expected": expected_exit,
                "verify_exit_ok": verify_exit_ok,
                "verify_ok": (document or {}).get("ok"),
                "installed_content_sha256": installed_sha,
                "canonical_content_sha256": canonical,
                "content_sha256_equal": (installed_sha == canonical) if installed_sha else None,
                "findings": (document or {}).get("findings"),
                "home_leak_scan": home_leak_scan(home),
                "no_installed_skill": installed_sha is None,
                "expected_no_installed_skill": expected_absent,
                "ok": verify_exit_ok and (
                    (installed_sha is None and not home_leak_scan(home)) if expected_absent
                    else (installed_sha == canonical and (document or {}).get("ok") is True)),
                "links_refused":
                    link_survey(home, allowed_targets=[PILOT_ROOT],
                                forbidden_targets=protected_roots(campaign))["symlinks_refused"],
                "stdout_tail": step["stdout"][-1500:] if document is None else None,
                "stderr_tail": step["stderr"][-1500:],
            })
            if rows[-1]["links_refused"]:
                rows[-1]["ok"] = False
                rows[-1]["why"] = ("a link in the home points at the key or at a campaign "
                                   "record (E10-40)")
    document = {"campaign": campaign.root, "canonical_content_sha256": canonical,
                "skill_identity": identity, "rows": rows}
    failed = [r for r in rows if r.get("ok") is not True]
    # E10-52 (finding 26): EVERY failed row fails the command; a present failing row no longer
    # leaves the exit at 0.
    document["ok"] = not failed
    document["failed"] = [{"setup": r["setup"], "condition": r["condition"],
                           "why": r.get("why") or
                           "verify_exit=%s (expected %s) verify_ok=%s installed=%s equal=%s"
                           % (r.get("verify_exit"), r.get("verify_exit_expected"),
                              r.get("verify_ok"), r.get("installed_content_sha256"),
                              r.get("content_sha256_equal"))} for r in failed]
    write_json(campaign.reserve_record("verify"), document)
    if missing_homes:
        raise Missing("these homes are not installed: %s" % ", ".join(missing_homes))
    if failed:
        raise Failure("verification failed for %s"
                      % ", ".join("%s/%s" % (r["setup"], r["condition"]) for r in failed))
    return document


# --------------------------------------------------------------------------- probe-env (E10-7)

PROBE_PROMPT = (
    "Run exactly this one command and reply with its output and nothing else:\n"
    "env | cut -d= -f1 | sort\n"
)

# E10-59 (3): the shapes a session uses when it did not run the command. A probe that prints
# no environment name already fails; this names WHY in the record when the reply says so.
COULD_NOT_RUN_RE = re.compile(
    r"(?i)\b(could not|couldn't|cannot|can't|unable to|was not able to|didn't|did not)\b[^.\n]{0,60}"
    r"\b(run|execute|complete|perform)\b")


def _installed_content_sha(document):
    """The installed `content_sha256`, out of whichever shape the setup's verifier prints.

    Three shapes, measured: Claude Code's `skill_identity.installed`, OpenCode's
    `identity.installed`, Codex's `surfaces[].identities[].stdout` (the raw command output).
    """
    if not isinstance(document, dict):
        return None
    for block in (document.get("skill_identity"), document.get("identity")):
        if isinstance(block, dict) and isinstance(block.get("installed"), dict):
            return block["installed"].get("content_sha256")
    for surface in document.get("surfaces") or []:
        for entry in surface.get("identities") or []:
            try:
                got = json.loads(entry["stdout"])
            except (ValueError, KeyError, TypeError):
                continue
            if got.get("commit") == "unversioned" or got.get("version") == "unversioned":
                return got.get("content_sha256")
    return None


def probe_dir(campaign, setup_name, condition):
    return os.path.join(campaign.root, "probes", "%s-%s" % (setup_name, condition))


def probe_records(campaign, setup_name=None, condition=None):
    """Every retained probe record, newest last (E10-42: retained by name, never replaced)."""
    pattern = os.path.join(campaign.root, "probes", "*", "probe-*.json")
    rows = []
    for path in sorted(glob.glob(pattern)):
        try:
            document = read_json(path)
        except (Missing, Failure):
            continue
        if setup_name and document.get("setup") != setup_name:
            continue
        if condition and document.get("condition") != condition:
            continue
        document["_path"] = path
        rows.append(document)
    return rows


def current_probes(campaign, plan):
    """The nine probes `campaign start` requires: one current successful record per setup and
    home, bound to the stage this campaign runs (E10-42)."""
    stage = campaign.staged()
    wanted, have, why = [], {}, []
    for spec in plan["setups"]:
        for condition in HOMES:
            wanted.append((spec["name"], condition))
    for row in probe_records(campaign):
        key = (row.get("setup"), row.get("condition"))
        if key not in wanted:
            continue
        if not row.get("ok"):
            continue
        if row.get("staged_commit") != stage.get("commit") or \
                row.get("plugin_tree_sha256") != stage.get("plugin_tree_sha256"):
            continue
        have[key] = row["_path"]
    for key in wanted:
        if key not in have:
            why.append("%s/%s" % key)
    return {"required": ["%s/%s" % k for k in wanted], "current": {"%s/%s" % k: v
                                                                  for k, v in have.items()},
            "missing": why, "ok": not why,
            "bound_to": {"commit": stage.get("commit"),
                         "plugin_tree_sha256": stage.get("plugin_tree_sha256")}}


def do_probe_env(args):
    campaign = Campaign(args.campaign)
    campaign.ensure()
    stage = campaign.staged()
    plan = _optional_plan(campaign)
    rows = []
    for setup in _selected_setups(campaign, plan, args.setup):
        for condition in (args.home and [args.home]) or list(HOMES):
            base = probe_dir(campaign, setup.name, condition)
            ensure_dir(base)
            # E10-42 / E10-43 (finding 7): a probe record is immutable and retained by name.
            # `--refresh` runs ANOTHER probe beside the old one; it never replaces one (the
            # pre-E10-30 Codex probes were lost to exactly that, E10-53(5)).
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            out_dir = None
            for index in range(0, 1000):
                candidate = os.path.join(base, "%s%s" % (stamp, "" if index == 0 else "-%d" % index))
                if not os.path.exists(candidate):
                    out_dir = candidate
                    break
            if out_dir is None:
                raise Failure("no free probe directory under %s" % base)
            if glob.glob(os.path.join(base, "probe-*.json")) and not args.refresh:
                raise Usage("%s already holds a probe record; pass --refresh to run another "
                            "beside it (a record is never replaced)" % base)
            workspace = os.path.join(campaign.root, "probes", "workspace")
            _empty_git_workspace(campaign, workspace)
            prompt = os.path.join(campaign.root, "probes", "env-probe.txt")
            write_text(prompt, PROBE_PROMPT)
            passed = sorted(campaign.env(extra=setup.launch_env(condition)))
            registry = ProcessRegistry(campaign, "probe-%s-%s" % (setup.name, condition), 0,
                                       "probe")
            close_key(campaign, "the environment probe")
            step = setup.launch(condition, prompt, workspace, out_dir, timeout=args.timeout,
                                registry=registry)
            printed, printed_source = harness_reply(setup, out_dir)
            names = _probe_names(printed)
            names_in_the_record = _names_in_the_record(out_dir)
            banned = sorted(n for n in names if BANNED_ENV_RE.match(n))
            # E10-42: the gate is on the names the RUNNER passed, PLUS any banned name that is
            # not on this harness's measured own-tool-shell list. A harness-created name that
            # was never measured fails the probe rather than being waved through.
            measured = list(HARNESS_CREATED_ENV.get(setup.harness, ()))
            from_runner = sorted(n for n in banned if n in passed)
            from_harness = sorted(n for n in banned if n not in passed and n in measured)
            unexplained = sorted(n for n in banned if n not in passed and n not in measured)
            empty = not printed.strip()
            # E10-59 (3): a probe passes only when it PRINTED AT LEAST ONE ENVIRONMENT NAME,
            # and a reply that reports it could not run the command is a failed probe. The
            # old gate asked only whether the reply was blank, so a session answering
            # "I could not run the requested command." passed with zero parsed names and the
            # nine-home gate of E10-42 stood on nothing.
            could_not_run = bool(COULD_NOT_RUN_RE.search(printed or ""))
            # E10-60 (3): a reply that reports it could not run the command is a FAILED probe
            # WHATEVER ELSE IT PRINTED. The first pass made the refusal a note on the
            # no-name reason, so a reply of "I could not run the requested command." plus the
            # single word `PATH` passed with one parsed name (the reviewer's adapted probe 3).
            # A name printed beside a refusal proves nothing about the session's environment.
            # Each rule that failed is named in `why_not_rules` beside its sentence.
            reasons, rules = [], []
            if step["exit"] not in (0,):
                rules.append("nonzero_exit")
                reasons.append("the probe session exited %s" % step["exit"])
            if empty:
                rules.append("no_output")
                reasons.append("the probe session printed no environment names")
            elif not names:
                rules.append("no_environment_name")
                reasons.append(
                    "the probe session printed no environment name (%d line(s) of reply, "
                    "none of them a name)" % len(printed.strip().splitlines()))
            if could_not_run:
                rules.append("reply_reports_it_could_not_run")
                reasons.append(
                    "the reply reports it could not run the command, which fails the probe "
                    "whatever else it printed (E10-60 (3)); names seen beside it: %s"
                    % (", ".join(names) or "none"))
            if from_runner:
                rules.append("banned_the_runner_passed")
                reasons.append("the runner passed banned names: %s" % ", ".join(from_runner))
            if unexplained:
                rules.append("banned_names_nobody_measured")
                reasons.append("banned names nobody measured: %s" % ", ".join(unexplained))
            row = {
                "setup": setup.name, "harness": setup.harness, "condition": condition,
                "out_dir": out_dir, "probe_at": now_iso(),
                "launch_exit": step["exit"], "wall_seconds": step["wall_seconds"],
                "names_seen": names,
                "names_read_from": printed_source,
                "reply_reports_it_could_not_run": could_not_run,
                # E10-60 (3): which rule failed the probe, by name.
                "why_not_rules": rules,
                "names_anywhere_in_the_record": names_in_the_record,
                "name_lines_printed": len(printed.strip().splitlines()),
                "names_the_runner_passed": passed,
                "banned_names_seen": banned,
                "banned_the_runner_passed": from_runner,
                "banned_the_harness_set_for_its_own_tool_shells": from_harness,
                "harness_created_measured_list": measured,
                "banned_names_nobody_measured": unexplained,
                "platform_added_below_the_boundary": sorted(
                    n for n in names if n in PLATFORM_ADDED_ENV),
                "staged_commit": stage.get("commit"),
                "plugin_tree_sha256": stage.get("plugin_tree_sha256"),
                "ok": not reasons,
                "why_not": reasons,
                "model": setup.model_record(out_dir), "cost": setup.cost_record(out_dir),
            }
            path = os.path.join(base, "probe-%s.json" % os.path.basename(out_dir))
            write_json(path, row)
            row["record"] = path
            rows.append(row)
            campaign.note("probe-env %s %s ok=%s runner-banned=%s harness-set=%s unexplained=%s"
                          % (setup.name, condition, row["ok"], from_runner, from_harness,
                             unexplained))
    # E10-43 (finding 7): the aggregate is a reference index over the immutable records, and
    # it takes a reserved name of its own rather than replacing `probe-env.json`.
    document = {"campaign": campaign.root, "allowlist": list(ALLOWED_ENV),
                "harness_created_env": {k: list(v) for k, v in HARNESS_CREATED_ENV.items()},
                "probes": [{"setup": r["setup"], "condition": r["condition"],
                            "ok": r["ok"], "why_not": r["why_not"], "record": r["record"]}
                           for r in rows],
                "probes_full": rows}
    document["ok"] = all(r["ok"] for r in rows)
    document["index"] = campaign.reserve_record("probe-env")
    write_json(document["index"], document)
    if not document["ok"]:
        raise Failure("probe-env failed: %s" % "; ".join(
            "%s/%s %s" % (r["setup"], r["condition"], "; ".join(r["why_not"]))
            for r in rows if not r["ok"]))
    return document


def _probe_names(printed):
    """The environment names the probe session ITSELF printed.

    E10-42's gate is on `env | cut -d= -f1 | sort`'s own output, not on every capitalised token
    anywhere in the record: the first reader scanned the whole rollout and returned `AGENTS`,
    `API`, `BLOCKER`, `JSON` and sixty other acronyms out of the session's prose, which is
    noise a gate cannot stand on. The record keeps the wider set beside it.
    """
    names = []
    for line in (printed or "").splitlines():
        candidate = line.strip().strip("`*-• ")
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]{1,63}$", candidate) and candidate.upper() == candidate:
            names.append(candidate)
    return sorted(set(names))


def _names_in_the_record(out_dir):
    """Every environment-variable-shaped name anywhere in the session's own record."""
    text = ""
    for name in ("result.txt", "final.md", "trace.jsonl", "events.jsonl", "trace.json",
                 "session.json", "rollout.jsonl"):
        text += read_text(os.path.join(out_dir, name), "") or ""
    return sorted({m for m in re.findall(r"\b[A-Z][A-Z0-9_]{2,40}\b", text)})


def _empty_git_workspace(campaign, path):
    """An empty git-initialized workspace (E10-13's routing workspace, and the probe's)."""
    if not os.path.isdir(os.path.join(path, ".git")):
        ensure_dir(path)
        env = campaign.env()
        run_cmd(["git", "-C", path, "init", "-q"], env=env)
        run_cmd(["git", "-C", path, "config", "user.email", "pilot@example.invalid"], env=env)
        run_cmd(["git", "-C", path, "config", "user.name", "pilot"], env=env)
        write_text(os.path.join(path, ".gitkeep"), "")
        run_cmd(["git", "-C", path, "add", "-A"], env=env)
        run_cmd(["git", "-C", path, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "empty"],
                env=env)
    return path


# --------------------------------------------------------------------------- plan (E10-5, E10-9)

DEFAULT_CASES = ("F1-01-fixed-clean", "F2-01-reproduces", "F3-01-missed-case",
                 "F4-01-missing-fixture-file", "F5-01-outbound-required", "F6-04-verifier-override")


def default_plan(campaign_id):
    """The full E10 campaign plan (E10-1 to E10-5, E10-12 to E10-14), the README's example.

    E10-62: FOUR setups, each pinned to one model and, where the harness takes one, one
    effort, in Tony's own words ("opus medium for claude, sol medium for codex, qwen 3.8 flash
    for opencode, deep seek 4.1 for new lane"). The fourth lane is the second OpenCode setup
    and it has three homes of its own (`pilot_home`'s setup-name keying). The counts grow with
    it: 6 × 4 × 2 × 2 = 96 comparison trials, 8 continuation trials, 240 routing trials.
    """
    return {
        "plan_version": 1,
        "campaign_id": campaign_id,
        "run_date": read_json(TRIAL_DEFAULTS)["run_date"],
        "setups": [
            {"name": "claude-code", "harness": "claude-code", "model": "opus",
             "effort": "medium"},
            {"name": "codex", "harness": "codex", "model": "gpt-5.6-sol", "effort": "medium"},
            {"name": "opencode", "harness": "opencode",
             "model": "openrouter/qwen/qwen3.8-flash"},
            {"name": "opencode-deepseek", "harness": "opencode",
             "model": "openrouter/deepseek/deepseek-v4.1-flash"},
        ],
        "cases": list(DEFAULT_CASES),
        "conditions": list(CONDITIONS),
        "repetitions": 2,
        "continuation": {"case": "F3-02-mixed-two-items", "condition": "available",
                         "repetitions": 1},
        "routing": {"entries": "all", "repetitions": 3},
        "timeouts": {"comparison": 1800, "continuation": 1800, "routing": 300},
    }


def trial_id(setup, case, condition, rep):
    return "%s-%s-%s-r%d" % (setup, case, condition, rep)


def routing_trial_id(setup, entry, rep):
    return "routing-%s-%s-r%d" % (setup, entry, rep)


def continuation_trial_id(setup, case, kind, rep):
    return "cont-%s-%s-%s-r%d" % (setup, case, kind, rep)


def order_of(plan):
    """E10-5: case by catalog order, then repetition 1 available, 1 absent, 2 available, 2 absent.
    The three setups are three lanes; each lane is strictly sequential."""
    lanes = {}
    for spec in plan["setups"]:
        ids = []
        for case in plan["cases"]:
            for rep in range(1, plan["repetitions"] + 1):
                for condition in plan["conditions"]:
                    ids.append(trial_id(spec["name"], case, condition, rep))
        lanes[spec["name"]] = ids
    return lanes


def routing_order(plan, entry_ids):
    """Every routing trial id per lane, for the entries of the two evaluation sets."""
    lanes = {}
    for spec in plan["setups"]:
        ids = []
        for entry in entry_ids:
            for rep in range(1, plan["routing"]["repetitions"] + 1):
                ids.append(routing_trial_id(spec["name"], entry, rep))
        lanes[spec["name"]] = ids
    return lanes


def manual_only_order(plan):
    """The one dedicated manual-only request per lane (E10-53(4)).

    It is a request outside both evaluation sets, added by the runner to every routing lane
    and reported as its own row. It runs once per lane (never `repetitions` times), it is
    never in `routing_entries`, and it is counted apart from `routing` — so neither the tuning
    nor the held-out denominator changes and the plan's routing count still means what the
    plan asked for.
    """
    return {spec["name"]: [routing_trial_id(spec["name"], MANUAL_ONLY_ENTRY, 1)]
            for spec in plan["setups"]}


def continuation_order(plan):
    lanes = {}
    conf = plan["continuation"]
    for spec in plan["setups"]:
        ids = []
        for rep in range(1, conf.get("repetitions", 1) + 1):
            for kind in ("handoff", "compaction"):
                ids.append(continuation_trial_id(spec["name"], conf["case"], kind, rep))
        lanes[spec["name"]] = ids
    return lanes


CONTINUATION_CASE = "F3-02-mixed-two-items"   # E10-12: two checklist items, so a cut exists


def validate_plan(plan):
    """The WHOLE plan, before any write (E10-43, finding 4).

    The reviewer's `K_probe.py` put a comparison case outside the six, an undefined harness, a
    setup named `../review-out` and duplicate cases through `plan` unchanged; the separator
    setup then wrote `command.json` outside `trials/`. Everything below is checked here, and
    `Campaign.trial_dir` checks the resolved path again.
    """
    problems = []
    for field in ("setups", "cases", "conditions", "repetitions", "timeouts"):
        if field not in plan:
            problems.append("plan.json has no %r" % field)
    if problems:
        raise Usage("; ".join(problems))

    # ---- setups: unique names, a supported harness, an identifier that reaches a path
    setups = plan["setups"]
    if not isinstance(setups, list) or not setups:
        raise Usage("plan.json `setups` must be a non-empty list")
    seen = set()
    for spec in setups:
        if not isinstance(spec, dict) or "name" not in spec:
            problems.append("a setup entry is not an object with a name: %r" % (spec,))
            continue
        name = spec["name"]
        try:
            check_identifier("the setup name", name)
        except Usage as exc:
            problems.append(str(exc))
            continue
        if name in seen:
            problems.append("the setup name %r appears twice" % name)
        seen.add(name)
        harness = spec.get("harness") or name
        if harness not in HARNESSES:
            problems.append("setup %r names the harness %r, which is not one of %s"
                            % (name, harness, ", ".join(HARNESSES)))
            continue
        # ---- E10-62 item 1: the per-setup model and effort.
        #
        # An unknown key is REFUSED, not ignored: a misspelled `effort` a plan silently
        # dropped would run the lane at the harness's own default with nothing in the record
        # to say so, and the whole point of E10-62 is that the pinned pair is a record.
        unknown = sorted(k for k in spec if k not in SETUP_KEYS)
        if unknown:
            problems.append("setup %r carries the unknown key%s %s (a setup entry takes %s)"
                            % (name, "" if len(unknown) == 1 else "s",
                               ", ".join(repr(k) for k in unknown), ", ".join(SETUP_KEYS)))
        for key in ("model", "effort"):
            if key in spec and not isinstance(spec[key], str):
                problems.append("setup %r's %r must be a string, got %r"
                                % (name, key, spec[key]))
            elif key in spec and not spec[key].strip():
                problems.append("setup %r's %r is empty" % (name, key))
        effort = spec.get("effort")
        if isinstance(effort, str) and effort.strip():
            accepted = HARNESS_EFFORTS.get(harness, ())
            if not accepted:
                problems.append(
                    "setup %r names the effort %r, and the %s harness takes none: OpenCode "
                    "1.18.31 records no reasoning effort (E10-26), so an effort here would be "
                    "a label with no record behind it (E10-19)" % (name, effort, harness))
            elif effort not in accepted:
                problems.append("setup %r names the effort %r, which %s does not accept (%s)"
                                % (name, effort, harness, ", ".join(accepted)))

    # ---- cases: the permitted set of E10-1, unique, identifiers
    cases = plan["cases"]
    if not isinstance(cases, list) or not cases:
        problems.append("plan.json `cases` must be a non-empty list")
        cases = []
    for case in cases:
        try:
            check_identifier("the case id", case)
        except Usage as exc:
            problems.append(str(exc))
    if len(set(cases)) != len(cases):
        duplicates = sorted({c for c in cases if cases.count(c) > 1})
        problems.append("plan.json names the same case twice: %s" % ", ".join(duplicates))
    outside = [c for c in cases if c not in DEFAULT_CASES]
    if outside:
        problems.append("plan.json names comparison cases outside E10-1's six (%s): %s"
                        % (", ".join(DEFAULT_CASES), ", ".join(outside)))

    # ---- conditions, repetitions, timeouts
    bad = [c for c in plan["conditions"] if c not in CONDITIONS]
    if bad:
        problems.append("plan.json names conditions outside %s: %s" % (list(CONDITIONS), bad))
    if not plan["conditions"]:
        problems.append("plan.json `conditions` is empty")
    if isinstance(plan["repetitions"], bool) or not isinstance(plan["repetitions"], int) \
            or plan["repetitions"] < 1:
        problems.append("plan.json `repetitions` must be a positive integer, got %r"
                        % (plan["repetitions"],))
    for key in ("comparison", "continuation", "routing"):
        value = (plan.get("timeouts") or {}).get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            problems.append("plan.json `timeouts.%s` must be a positive number, got %r"
                            % (key, value))

    # ---- the continuation set (E10-12)
    continuation = plan.get("continuation")
    if continuation:
        if continuation.get("case") != CONTINUATION_CASE:
            problems.append("the continuation set runs on %s (E10-12), not %r"
                            % (CONTINUATION_CASE, continuation.get("case")))
        if continuation.get("condition") not in (None, "available"):
            problems.append("the continuation set is the available condition (E10-12), not %r"
                            % continuation.get("condition"))
        reps = continuation.get("repetitions", 1)
        if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
            problems.append("`continuation.repetitions` must be a positive integer, got %r"
                            % (reps,))

    # ---- the routing set (E10-13)
    routing = plan.get("routing")
    if routing:
        entries = routing.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                try:
                    check_identifier("a routing entry id", entry)
                except Usage as exc:
                    problems.append(str(exc))
            if len(set(entries)) != len(entries):
                problems.append("the routing set names the same entry twice")
        elif entries not in ("all", "tuning"):
            problems.append("`routing.entries` must be a list, \"all\" or \"tuning\", got %r"
                            % (entries,))
        reps = routing.get("repetitions", 1)
        if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
            problems.append("`routing.repetitions` must be a positive integer, got %r" % (reps,))

    if "run_root_name" in plan:
        try:
            check_identifier("run_root_name", plan["run_root_name"])
        except Usage as exc:
            problems.append(str(exc))
    if "campaign_id" in plan:
        try:
            check_identifier("campaign_id", plan["campaign_id"])
        except Usage as exc:
            problems.append(str(exc))
    if problems:
        raise Usage("the plan is refused: " + "; ".join(problems))
    return plan


def do_plan(args):
    campaign = Campaign(args.campaign)
    # E10-64 (Astra's recheck3, item 1): EVERY refusal comes before the first directory is
    # made. E10-43 finding 4 says the whole plan is checked "before any write", and a
    # directory is a write: `campaign.ensure()` used to run first, so a plan refused for a
    # bad model, a bad effort or an unknown key still left a campaign root holding empty
    # `records/`, `tmp/` and `trials/` behind it. `Campaign.__init__` only computes paths and
    # `campaign_json` is one of them, so every check below reads without creating anything.
    if os.path.isfile(campaign.campaign_json) and not args.refresh:
        raise Usage("%s already holds campaign.json; pass --refresh to replace it (E9-34: a "
                    "record is never overwritten)" % campaign.root)
    plan = (read_json(args.plan, "plan.json") if args.plan
            else default_plan(os.path.basename(campaign.root)))
    validate_plan(plan)
    index = lane_index()
    unknown = [c for c in plan["cases"] if c not in index]
    if plan.get("continuation") and plan["continuation"]["case"] not in index:
        unknown.append(plan["continuation"]["case"])
    if unknown:
        raise Usage("plan.json names cases no generator lists: %s" % ", ".join(unknown))
    campaign.ensure()
    entry_ids = _routing_entry_ids(plan)
    document = dict(plan)
    document.update({
        "planned_at": now_iso(),
        "campaign": campaign.root,
        "stage": campaign.staged(),
        "path_entries": path_entries(),
        "allowlisted_env_names": list(ALLOWED_ENV),
        "case_lanes": {c: index[c] for c in plan["cases"]},
        "order": order_of(plan),
        "routing_entries": entry_ids,
        "routing_order": routing_order(plan, entry_ids) if plan.get("routing") else {},
        "manual_only_order": manual_only_order(plan) if plan.get("routing") else {},
        "continuation_order": continuation_order(plan) if plan.get("continuation") else {},
        "synthetic": bool(getattr(args, "synthetic", False)) or bool(plan.get("synthetic")),
    })
    # Every id the plan will ever use is checked here, so no launch can mint a path outside
    # `trials/` later (E10-43).
    ids = []
    for lanes in (document["order"], document["routing_order"], document["manual_only_order"],
                  document["continuation_order"]):
        for lane_ids in lanes.values():
            ids += list(lane_ids)
    for tid in ids:
        check_identifier("a trial id the plan mints", tid)
    if len(set(ids)) != len(ids):
        duplicates = sorted({t for t in ids if ids.count(t) > 1})
        raise Usage("the plan mints the same trial id twice: %s" % ", ".join(duplicates[:10]))
    counts = {
        "comparison": sum(len(v) for v in document["order"].values()),
        "routing": sum(len(v) for v in document["routing_order"].values()),
        # E10-53(4): counted apart, so the plan's routing count still means the entries the
        # plan asked for and the manual-only probe is visible as its own number.
        "manual_only": sum(len(v) for v in document["manual_only_order"].values()),
        "continuation": sum(len(v) for v in document["continuation_order"].values()),
    }
    counts["total"] = sum(counts.values())
    document["counts"] = counts
    write_json(campaign.campaign_json, document)
    if document["synthetic"]:
        campaign.mark_synthetic("plan --synthetic")
    campaign.note("plan %d trials (%d comparison, %d continuation, %d routing)"
                  % (counts["total"], counts["comparison"], counts["continuation"],
                     counts["routing"]))
    return {"campaign": campaign.root, "campaign_json": campaign.campaign_json,
            "counts": counts, "order": document["order"],
            "trial_ids": ids,
            "synthetic": document["synthetic"],
            "routing_entries": len(entry_ids)}


def _optional_plan(campaign):
    try:
        return campaign.plan()
    except Missing:
        return None


def _selected_setups(campaign, plan, wanted):
    """The setups a subcommand was pointed at, from the PLAN's own entries where there is one.

    E10-62: a setup's model and effort live in the plan entry, so a `--setup <name>` that a
    plan does not carry can no longer be invented — `install --setup opencode-deepseek`
    against a plan without that entry used to build a home named `opencode-deepseek` on the
    OpenCode default model, which is the qwen lane's model in the DeepSeek lane's home. Only a
    campaign with no plan at all still falls back to a bare harness name.
    """
    specs = (plan or {}).get("setups") or [{"name": h, "harness": h} for h in HARNESSES]
    if wanted:
        known = [s["name"] for s in specs]
        missing = [w for w in wanted if w not in known]
        if missing and plan:
            raise Usage("the plan has no setup %s (it names %s)"
                        % (", ".join(sorted(missing)), ", ".join(known)))
        specs = [s for s in specs if s["name"] in wanted] or \
                [{"name": w, "harness": w.split("-deepseek")[0]} for w in wanted]
    return [make_setup(campaign, s) for s in specs]


# --------------------------------------------------------------------------- the wall (section 3)
#
# Everything below opens `evals/answer-key/` or `evals/trigger-set/held-out/`. Nothing above
# does, and no launch path reaches any of it. E10-21: a test may point these two readers at
# stand-ins it wrote itself, only under RECHECK_RUNNER_TEST=1.

TEST_FLAG = "RECHECK_RUNNER_TEST"
KEY_DIR_OVERRIDE = "RECHECK_RUNNER_KEY_DIR"
HELDOUT_OVERRIDE = "RECHECK_RUNNER_HELDOUT"


def _stand_in(name, canonical):
    """The canonical location, or a test's own stand-in under E10-21."""
    override = os.environ.get(name)
    if not override:
        return canonical, False
    if os.environ.get(TEST_FLAG) != "1":
        raise Usage("key stand-in outside test: %s is set without %s=1" % (name, TEST_FLAG))
    return override, True


def key_dir():
    return _stand_in(KEY_DIR_OVERRIDE, KEY_DIR)


def heldout_file():
    return _stand_in(HELDOUT_OVERRIDE, TRIGGER_HELDOUT)


def key_entry(case_id):
    """The key entry for one case, plus whether a stand-in supplied it.

    The grader's one read of the key. The entry's `expected`, `must_not` and `runs_at` stay
    inside the grading path: they reach `grade.json` as reasons and never a launch path.
    """
    directory, stood_in = key_dir()
    lane = lane_index().get(case_id)
    if lane is None:
        raise Usage("no fixture lane holds the case %r" % case_id)
    path = os.path.join(directory, "%s.json" % lane)
    if not os.path.isfile(path):
        raise Missing("no key file for lane %s under %s" % (lane, directory))
    document = read_json(path, "the key for lane %s" % lane)
    for entry in document if isinstance(document, list) else []:
        if entry.get("case") == case_id:
            return entry, stood_in
    raise Missing("the key for lane %s has no entry for %s" % (lane, case_id))


HELDOUT_ID_SCRIPT = (
    "import json,sys\n"
    "d=json.load(open(sys.argv[1]))\n"
    "sys.stdout.write('\\n'.join(e['id'] for e in d['requests'])+'\\n')\n"
)
HELDOUT_TEXT_SCRIPT = (
    "import json,sys\n"
    "d=json.load(open(sys.argv[1]))\n"
    "for e in d['requests']:\n"
    "    if e['id']==sys.argv[2]:\n"
    "        sys.stdout.write(e['text'])\n"
    "        raise SystemExit(0)\n"
    "raise SystemExit(3)\n"
)


# E10-68 defect 1. The barrier of E10-40 holds `evals/trigger-set/held-out/` at mode 000 for
# the whole of every launch and while ANY registered launch is alive; `request_text` read a
# held-out entry through a subprocess at LAUNCH time (E10-13). With four lanes alive a launch
# is nearly always alive, so on the night of 2026-09-15 that read failed with `PermissionError`
# on every one of the 72 held-out routing trials of the three live lanes (`runner.log` lines
# 840, 851, 862 onward; `interruptions.jsonl`, 72 rows reading "the trial raised: no
# trigger-set entry 'H-NN-...'"), and not one of them launched a process.
#
# The fix is shape (a) of E10-68: every planned held-out request is written ONCE, at
# `campaign start`, before the first launch and while the keys are open, into the campaign's
# own `routing-requests/` — by a SUBPROCESS that writes the file itself, so the sealed text
# never enters the runner process at all, not even one entry at a time as E10-13 allowed. A
# launch then copies its own entry's file into `prompt.txt` byte for byte. Shape (b) — reopen
# the directory under the lock for the read — cannot hold E10-68's own invariant ("unreadable
# by any launched harness while any launch is alive") without serialising every lane's launch
# against every other, which is the concurrency the campaign exists to have.
HELDOUT_TEXT_TO_FILE_SCRIPT = (
    "import json,sys\n"
    "d=json.load(open(sys.argv[1]))\n"
    "for e in d['requests']:\n"
    "    if e['id']==sys.argv[2]:\n"
    "        t=e['text']\n"
    "        if not t.endswith('\\n'):\n"
    "            t+='\\n'\n"
    "        h=open(sys.argv[3],'w')\n"
    "        h.write(t)\n"
    "        h.close()\n"
    "        raise SystemExit(0)\n"
    "raise SystemExit(3)\n"
)

ROUTING_REQUESTS_DIRNAME = "routing-requests"


def routing_requests_dir(campaign):
    return os.path.join(campaign.root, ROUTING_REQUESTS_DIRNAME)


def cached_request_file(campaign, entry_id):
    """Where one entry's request text is kept for the campaign's own launches."""
    check_identifier("a trigger-set entry id", entry_id)
    return os.path.join(routing_requests_dir(campaign), "%s.txt" % entry_id)


def cache_routing_requests(campaign, entry_ids):
    """Write every planned held-out request into the campaign, once, keys open (E10-68 (1)).

    Called by `_campaign_loop` before the first lane starts. A tuning id is not cached: the
    tuning file is not behind the barrier and `request_text` reads it directly. The manual-only
    request is the runner's own words and is not in either set.

    The index record names each file, its sha256 and its size, and never its text.
    """
    directory = routing_requests_dir(campaign)
    ensure_dir(directory)
    try:
        tuning = {e["id"] for e in read_json(TRIGGER_TUNING,
                                             "trigger-set/requests.json")["requests"]}
    except (Missing, Failure, KeyError, TypeError):
        tuning = set()
    path, stood_in = heldout_file()
    rows, failed = [], []
    for entry_id in entry_ids:
        if entry_id == MANUAL_ONLY_ENTRY or entry_id in tuning:
            continue
        target = cached_request_file(campaign, entry_id)
        if os.path.isfile(target):
            rows.append({"entry": entry_id, "file": target, "cached": True,
                         "sha256": file_sha256(target),
                         "bytes": os.path.getsize(target), "written": "before this run"})
            continue
        step = run_cmd([sys.executable, "-c", HELDOUT_TEXT_TO_FILE_SCRIPT, path, entry_id,
                        target], env=tool_env(), label="held-out text into the campaign")
        if step["exit"] != 0 or not os.path.isfile(target):
            failed.append({"entry": entry_id, "exit": step["exit"],
                           "stderr_tail": step["stderr"][-200:]})
            continue
        rows.append({"entry": entry_id, "file": target, "cached": True,
                     "sha256": file_sha256(target),
                     "bytes": os.path.getsize(target), "written": "this run"})
    index = {
        "campaign": campaign.root,
        "cached_at": now_iso(),
        "rule": "E10-68 defect 1: every planned held-out request is written once, before the "
                "first launch and while the keys are open, by a subprocess that writes the "
                "file itself; a launch copies its own entry byte for byte. No request text "
                "enters the runner process.",
        "key_state_at_cache_time": key_state(),
        "stand_in": bool(stood_in),
        "entries": rows,
        "failed": failed,
    }
    write_json(os.path.join(directory, "index.json"), index)
    campaign.note("cached %d held-out request(s) into %s before the first launch (E10-68)"
                  % (len(rows), directory))
    if failed:
        campaign.note("could not cache %d held-out request(s): %s"
                      % (len(failed), ", ".join(r["entry"] for r in failed)))
    return index


def heldout_entry_ids():
    """The sealed set's ids, printed by a subprocess that prints ids and nothing else."""
    path, _ = heldout_file()
    step = run_cmd([sys.executable, "-c", HELDOUT_ID_SCRIPT, path], env=tool_env(),
                   label="held-out ids")
    if step["exit"] != 0:
        raise Missing("the held-out set could not be listed: %s" % step["stderr"][-200:])
    return step["stdout"].split()


def request_text(entry_id):
    """The request text for one trigger-set entry.

    A tuning id is read here; a held-out id goes through a subprocess that prints that one
    entry's text and nothing else (E10-13), so no held-out content enters this process.
    """
    tuning = read_json(TRIGGER_TUNING, "trigger-set/requests.json")
    for entry in tuning["requests"]:
        if entry["id"] == entry_id:
            return entry["text"], "tuning"
    path, _ = heldout_file()
    step = run_cmd([sys.executable, "-c", HELDOUT_TEXT_SCRIPT, path, entry_id],
                   env=tool_env(), label="held-out text")
    if step["exit"] != 0:
        raise Missing("no trigger-set entry %r" % entry_id)
    return step["stdout"], "held-out"


def expectation_of(entry_id):
    """The entry's expected target, for `routing-score` only."""
    for path, which in ((TRIGGER_TUNING, "tuning"), (heldout_file()[0], "held-out")):
        try:
            document = read_json(path)
        except (Missing, Failure):
            continue
        for entry in document.get("requests", []):
            if entry["id"] == entry_id:
                return entry.get("expected") or {}, which, entry.get("competitors") or []
    raise Missing("no trigger-set entry %r" % entry_id)


def _routing_entry_ids(plan):
    """The trigger-set entry ids. The tuning file is read here; the held-out file is never
    opened in this process — its ids come from a subprocess that prints ids only (E10-13).

    This sits below the wall marker because it can reach the sealed set at all.
    """
    routing = plan.get("routing")
    if not routing:
        return []
    if isinstance(routing.get("entries"), list):
        return list(routing["entries"])
    ids = [e["id"] for e in read_json(TRIGGER_TUNING, "trigger-set/requests.json")["requests"]]
    if routing.get("entries") == "tuning":
        return ids
    return ids + heldout_entry_ids()


def _import_match():
    """`evals/checks/match.py`, imported from its path (the E7 matcher the grade step calls)."""
    if CHECKS_DIR not in sys.path:
        sys.path.insert(0, CHECKS_DIR)
    try:
        import match  # noqa
    except ImportError as exc:
        raise Missing("evals/checks/match.py could not be imported: %s" % exc)
    return match


# --------------------------------------------------------------------------- run (E10-4, E10-10)

# E10-4: one template, filled per trial, identical bytes in both conditions. It names no
# skill, no plugin, no harness, no condition, and never says "use" or "do not use".
#
# E10-54(b): the run id is named IN WORDS beside the run directory. The core otherwise mints
# its own id, and the key's `run_id` — `<case id>-run`, the id the fixture's own seeded
# `input.json` carries (E7 gap 13) — can then never hold. This is E10-41's one documented
# exception made explicit: the case name appears in the run id and nowhere else.
PROMPT_TEMPLATE = (
    "recheck slice {slice} of {build_doc} in {workspace}: a fresh verifier proves each named "
    "BLOCKER or MAJOR fix on the punch list landed, then move the slice's card; run date "
    "{run_date}.\n"
    "\n"
    "Use run id {run_id} and the run directory {run_dir}.\n"
    "\n"
    "Write result.json in the run directory validating against {run_dir}/result.schema.json "
    "and print the chat block.\n"
)


def parse_trial_id(plan, tid):
    """`<setup>-<case>-<available|absent>-r<n>`, split against the plan's own names."""
    match = re.match(r"^(?P<rest>.+)-(?P<condition>available|absent)-r(?P<rep>\d+)$", tid)
    if not match:
        raise Usage("%r is not a trial id of the shape <setup>-<case>-<condition>-r<n>" % tid)
    rest = match.group("rest")
    names = sorted((s["name"] for s in plan["setups"]), key=len, reverse=True)
    for name in names:
        if rest.startswith(name + "-"):
            case = rest[len(name) + 1:]
            return {"trial": tid, "setup": name, "case": case,
                    "condition": match.group("condition"), "rep": int(match.group("rep"))}
    raise Usage("%r names no setup in the plan (%s)" % (tid, ", ".join(names)))


def setup_for(campaign, plan, name):
    for spec in plan["setups"]:
        if spec["name"] == name:
            return make_setup(campaign, spec)
    raise Usage("the plan has no setup %r" % name)


def build_fixture(campaign, case, out):
    """One fresh opaque fixture build for this trial (E10-5, the opaque mount of E7-18)."""
    lane = lane_index().get(case)
    if lane is None:
        raise Usage("no fixture lane holds the case %r" % case)
    build = os.path.join(FIXTURES_DIR, lane, "build.py")
    ensure_dir(out)
    step = run_cmd([sys.executable, build, "--out", out, "--case", case, "--opaque", "--json"],
                   env=campaign.env(), label="build.py --opaque")
    if step["exit"] != 0:
        raise Failure("the fixture build for %s exited %s" % (case, step["exit"]))
    summary = json.loads(step["stdout"])
    row = summary["cases"][0]
    return {"lane": lane, "summary": summary, "case_dir": row["path"],
            "tree_sha256": row["tree_sha256"], "opaque": row["opaque"]}


# The adapters' run root (`references/pilot-contract.md` section 2 and every profile's section
# 3) is `${TMPDIR}/runs` since E10-22, and three installed things are written for that path:
# the Claude launcher's `--add-dir`, the OpenCode `external_directory` allow rule the install
# writes from its own TMPDIR (E9-27), and the adapter helpers' own default.
#
# E10-54(a): a TRIAL's run directory is no longer under it. The run directory of every trial is
# the fixture's own `run/` leaf — `<campaign>/tmp/<digest>/fixture/<12 hex>/run` — exactly as
# E7-18 lays the opaque mount out ("`workspace/` and `run/` keep their names, so every key's
# `/run/` pattern holds"), and as each case's own seeded `input.json` already names it. The
# segment below is kept because the adapters are written for it and because the record has to
# say what it now means.
DEFAULT_RUN_ROOT_NAME = "runs"  # E10-22: the setups name the run root ${TMPDIR}/runs since a55da08
RUN_LEAF = "run"                # E7-18 / E10-54(a): the fixture's own leaf, named `run`


def run_root_of(campaign, plan, trial=None, attempt=0):
    """`<campaign>/tmp/<digest>/<run root name>` — the ADAPTERS' run root inside the trial's
    opaque tree (E10-22).

    E10-41: the whole reachable world of one trial is `<campaign>/tmp/<digest of campaign,
    trial id and attempt>/`, so the workspace and run-directory paths a prompt must name carry
    no setup, case, condition, repetition or attempt, and two attempts of one trial never mint
    the same absolute path (finding 5: `_one_trial` used to hash the record's BASENAME, so
    every first rerun of every trial hashed `1`).

    Since E10-54(a) this is NOT where a trial's run directory goes — `trial_run_dir` is. It
    stays as the segment the adapters' own defaults and allow rules are written for, and the
    record names it.
    """
    name = plan.get("run_root_name") or DEFAULT_RUN_ROOT_NAME
    if trial is None:
        return os.path.join(campaign.tmp, name)
    return os.path.join(campaign.opaque_tree(trial, attempt), name)


def trial_run_dir(fixture):
    """E10-54(a): the fixture's own `run/` leaf, and nothing else.

    `build.py --opaque` lays every case out as `<out>/<12 hex>/{workspace,run,input.json,
    manifest.json}` (`fixturelib.Fixture`), and the case's seeded `input.json` names that leaf
    as `invocation.run_dir`. E7-18 promises the leaf keeps its name so every key's `/run/`
    pattern holds; the first build put the run directory under `<tree>/runs/<case id>-run`
    instead, and every `records_written` and `receipt_path` regex of the six continuation
    grades failed on it (E10-54).
    """
    return os.path.join(fixture["case_dir"], RUN_LEAF)


def trial_run_id(fixture, seeded=None):
    """`<case id>-run` (E7 gap 13), read from the fixture's own seeded input where it is."""
    if seeded is None:
        seeded = read_json(os.path.join(fixture["case_dir"], "input.json"), "the seeded input")
    given = ((seeded or {}).get("invocation") or {}).get("run_id")
    return given if isinstance(given, str) and given else None


def run_root_note(plan):
    name = plan.get("run_root_name") or DEFAULT_RUN_ROOT_NAME
    return {
        "run_root_name": name,
        "prompt_names_the_skill": name == "recheck-v2",
        # E10-54(a): the segment is the ADAPTERS', not the trial's run directory any more.
        "means": ("`run_root_name` is the segment the adapters are written for: "
                  "`${TMPDIR}/%s` is setups/claude-code/launch.sh's --add-dir, "
                  "setups/opencode/install.sh's external_directory allow rule, and the "
                  "helpers' own default run root (E10-22). Since E10-54(a) a TRIAL's run "
                  "directory is not under it: it is the fixture's own `run/` leaf, "
                  "`<opaque tree>/fixture/<12 hex>/run`, the leaf E7-18 keeps named `run` and "
                  "the leaf each case's seeded input.json already names. `run_root` below is "
                  "therefore that leaf's parent, the opaque case directory." % name),
        "trial_run_directory": "the fixture's own `run/` leaf (E7-18, E10-54(a))",
        # E10-41: everything else about the path is opaque; the run id's own case name is the
        # one documented exception and the record says so on every trial.
        "documented_exception": "the run id is `<case id>-run` (E7 gap 13) and the E10-4 "
                                "prompt now NAMES it in words (E10-54(b)), so the case name "
                                "appears in the run id and nowhere else; E10-41 keeps this as "
                                "the one exception and requires the record to state it",
        "reason": ("the adapters' run root is ${TMPDIR}/runs (E10-22: "
                   "setups/claude-code/launch.sh's --add-dir and "
                   "setups/opencode/install.sh's external_directory allow rule are written "
                   "for that segment since a55da08), so no path in the prompt names a skill; "
                   "E10-4 holds." if name != "recheck-v2" else
                   "the run root segment is recheck-v2, so the run-directory path in the prompt "
                   "names the skill: E10-4's 'the prompt never names recheck-v2' is breached by "
                   "the path alone and is recorded here; the Claude launcher's --add-dir and the "
                   "OpenCode external_directory allow rule must be written for the same segment "
                   "or every write outside the workspace fails."),
    }


SCHEMA_COPY = "result.schema.json"


def prepare_run_dir(run_dir):
    """The canonical result schema copied into the trial's run directory (E10-4, E10-54(a)).

    The directory is the fixture's own `run/` leaf, which the build already created, so its
    existence is the normal case and is not an error. What is refused is a leaf that was
    ALREADY PREPARED — one holding `result.schema.json` — because that is another attempt's
    directory (E10-43: a run directory is refused, never removed; the dry run lost a first
    attempt's live directory to its own rerun because this function called `rmtree`). Nothing
    here removes anything.
    """
    if os.path.exists(os.path.join(run_dir, SCHEMA_COPY)):
        raise Usage("%s already holds %s: this run directory was prepared before, and a run "
                    "directory is never removed (E10-43, E10-54(a)). Another attempt gets its "
                    "own opaque tree." % (run_dir, SCHEMA_COPY))
    ensure_dir(run_dir)
    shutil.copy2(os.path.join(SKILL_DIR, "references", SCHEMA_COPY),
                 os.path.join(run_dir, SCHEMA_COPY))
    return run_dir


def trial_prompt(fixture, workspace, run_dir, run_date, run_id):
    """The prompt, from the fixture's own seeded input (facts, never an outcome)."""
    seeded = read_json(os.path.join(fixture["case_dir"], "input.json"), "the seeded input")
    target = seeded.get("target") or {}
    build_doc = target.get("build_doc") or "docs/punch-list.md"
    slice_name = target.get("slice") or "A"
    return PROMPT_TEMPLATE.format(slice=slice_name, build_doc=build_doc, workspace=workspace,
                                  run_dir=run_dir, run_date=run_date, run_id=run_id), seeded


def validate_result(campaign, result, seeded_input, run_dir, workspace):
    argv = ["uv", "run", os.path.join(SKILL_DIR, "scripts", "validate-result.py"), result]
    if seeded_input:
        argv += ["--input", seeded_input]
    argv += ["--run-dir", run_dir, "--workspace", workspace, "--strict"]
    step = run_cmd(argv, env=campaign.env(), label="validate-result.py --strict")
    text = (step["stdout"] or "") + ("\n" if step["stdout"] and not step["stdout"].endswith("\n") else "")
    text += "exit %s\n" % step["exit"]
    return step, text


def scan_paths(paths, exempt=(), mandatory=()):
    """The credential scan (E10-9's `scan`): shapes only, offsets only, never a value.

    E10-52 (finding 24): every retained capture is scanned whatever its extension and whatever
    its first bytes hold. The dry run's only non-test hits were `sk-`-shaped byte runs inside
    Codex's own dropped helper BINARIES, which are not records and do not live under a
    campaign root; a file with a NUL is now scanned all the same and labelled, because "the
    capture had a NUL in it" is exactly how a real key would have been missed. An unreadable
    file in `mandatory` is a failure, not a silent skip.
    """
    hits, scanned, with_nul, unreadable = [], 0, [], []
    exempt_real = {os.path.realpath(p) for p in exempt}
    mandatory_real = {os.path.realpath(p) for p in mandatory}
    for path in paths:
        if not os.path.isfile(path):
            continue
        real = os.path.realpath(path)
        if real in exempt_real:
            continue
        try:
            with open(path, "rb") as handle:
                blob = handle.read()
        except (IOError, OSError) as exc:
            unreadable.append({"file": path, "error": str(exc),
                               "mandatory": real in mandatory_real})
            continue
        scanned += 1
        if b"\x00" in blob[:8192]:
            with_nul.append(path)
        text = blob.decode("utf-8", "replace")
        # The shapes overlap (an OpenRouter key is also a `sk-` key), so the most specific
        # shape claims the span and a later shape inside it is not a second hit.
        claimed = []
        for shape, pattern in CREDENTIAL_SHAPES:
            for found in pattern.finditer(text):
                start_at, end_at = found.span()
                if any(start_at >= a and end_at <= b for a, b in claimed):
                    continue
                claimed.append((start_at, end_at))
                hits.append({"file": path, "shape": shape, "offset": start_at,
                             "length": end_at - start_at})
    return {"files_scanned": scanned, "hits": hits,
            "files_with_a_nul_scanned_anyway": len(with_nul),
            "nul_files": sorted(with_nul)[:40],
            "unreadable": unreadable,
            "unreadable_mandatory": [u for u in unreadable if u["mandatory"]],
            # kept for readers of the old field name; nothing is skipped for being binary now
            "binary_files_skipped": 0, "binary_files": []}


# Directories `scan` never walks. No record of a campaign lives in one, and a vendored tree
# carries third-party test data that looks like a credential: measured 2026-09-15, scanning a
# whole OpenCode home hit six JWT literals inside `node_modules/zod/**/tests/string.test.ts`
# (two literals in each of the three homes) and nothing else.
SCAN_SKIP_DIRS = (".git", "node_modules", "__pycache__", ".venv")


def walk_files(root):
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SCAN_SKIP_DIRS]
        for name in files:
            out.append(os.path.join(base, name))
    return out


def auth_store_exemptions(setups=()):
    """The only exemption of E10-9 and E10-52 (finding 24): each setup's ACTUAL configured
    credential store, by resolved path.

    Claude Code has none. Its sign-in lives in the macOS Keychain
    (`security find-generic-password -s "Claude Code-credentials"`, class genp) and it writes
    no `auth.json` under its pilot home, so a file of that name there would be a planted
    credential and is scanned like any other capture. Measured 2026-09-15 by
    `setups/claude-code/install.sh` and the E9 profile section 2.

    `setups` carries extra `(harness, setup name)` pairs, because E10-62 keys the homes by
    the SETUP NAME: `opencode-deepseek`'s store sits under its own home and the three
    harness-named ones no longer cover it. A name is only ever added by its own harness's
    layout, so a file named `auth.json` under a Claude Code home is still scanned.
    """
    pairs = [("codex", "codex"), ("opencode", "opencode")]
    for harness, name in setups:
        if harness in ("codex", "opencode") and (harness, name) not in pairs:
            pairs.append((harness, name))
    stores = []
    for harness, name in pairs:
        for home in HOMES:
            try:
                base = pilot_home(harness, home, setup_name=name)
            except Usage:
                continue
            if harness == "codex":
                # Codex writes `auth.json` in its CODEX_HOME and in the nested child (E9-25).
                stores += [os.path.join(base, "auth.json"),
                           os.path.join(base, "child", "auth.json")]
            else:
                # OpenCode writes its store under XDG_DATA_HOME (E9-38).
                stores += [os.path.join(base, "xdg-data", "opencode", "auth.json")]
    return [p for p in stores if os.path.exists(p)]


def plan_setup_pairs(campaign):
    """Every `(harness, setup name)` the campaign's plan names, for the exemption survey."""
    plan = _optional_plan(campaign)
    return [(s.get("harness") or s["name"], s["name"]) for s in (plan or {}).get("setups", [])]


def attempt_record(campaign, trial_id, attempt):
    """Where one attempt's record lives. Attempt 0 is the trial directory itself."""
    base = campaign.trial_dir(trial_id)
    if attempt == 0:
        return base
    if not isinstance(attempt, int) or attempt < 1:
        raise Usage("an attempt number is a positive integer, got %r" % (attempt,))
    path = os.path.join(base, "attempts", str(attempt))
    contained(base, path, "the attempt record for %s/%d" % (trial_id, attempt))
    return path


def next_attempt(campaign, trial_id):
    attempts = os.path.join(campaign.trial_dir(trial_id), "attempts")
    existing = sorted(int(os.path.basename(p)) for p in glob.glob(os.path.join(attempts, "*"))
                      if os.path.basename(p).isdigit())
    return (existing[-1] + 1) if existing else 1


def refuse_if_lane_stopped(campaign, setup_name):
    """E10-46 (finding 14): a persisted lane stop no later launch can pass."""
    stop = lane_stopped(campaign, setup_name)
    if stop:
        raise Failure("the %s lane is stopped: %s (%s)"
                      % (setup_name, stop.get("reason"), stop.get("record")))


def outcome_status(step, has_result):
    """The status, decided by the PROCESS, not by what happened to be on disk (E10-43,
    finding 19).

    The dry run recorded `complete` for a launch that exited 7, and `launch_failed` in
    `command.json` while the ledger said `complete` for the same routing trial. One function,
    one answer, used by every kind of trial and written into both records.
    """
    if step.get("timed_out"):
        return "timed_out"
    if step.get("exit") not in (0,):
        return "launch_failed"
    if not has_result:
        return "no_result"
    return "complete"


def do_run(args):
    """One comparison trial end to end: build, prompt, launch, collect, validate, scan."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    parts = parse_trial_id(plan, args.trial)
    refuse_if_lane_stopped(campaign, parts["setup"])
    setup = setup_for(campaign, plan, parts["setup"])
    attempt = int(getattr(args, "attempt", 0) or 0)
    record = attempt_record(campaign, args.trial, attempt)
    if os.path.exists(record):
        raise Usage("%s is a used trial directory (E9-34: a record is never overwritten); "
                    "use `rerun` for another attempt" % record)
    ensure_dir(record)
    campaign.journal_attempt(args.trial, attempt, record, "comparison")
    return _one_trial(campaign, plan, setup, parts, record, attempt, args)


def _one_trial(campaign, plan, setup, parts, record, attempt, args):
    started = time.time()
    trial_id = parts["trial"]
    tree = campaign.opaque_tree(trial_id, attempt)
    # E10-41: the fixture is built inside the opaque tree, NOT under the named record
    # directory; the record receives a copy after the trial.
    fixture = build_fixture(campaign, parts["case"], os.path.join(tree, "fixture"))
    workspace = os.path.join(fixture["case_dir"], "workspace")
    if not os.path.isdir(workspace):
        raise Failure("the built fixture has no workspace at %s" % workspace)
    # E10-54(a): the run directory IS the fixture's own `run/` leaf; (b) the run id is the one
    # the case's seeded input carries, and the prompt names it in words.
    run_dir = prepare_run_dir(trial_run_dir(fixture))
    run_id = trial_run_id(fixture) or "%s-run" % parts["case"]
    prompt, seeded = trial_prompt(fixture, workspace, run_dir, plan["run_date"], run_id)
    prompt_path = os.path.join(record, "prompt.txt")
    write_text(prompt_path, prompt)
    harness_dir = os.path.join(record, "harness")
    timeout = plan["timeouts"]["comparison"]
    env_extra = setup.launch_env(parts["condition"])
    registry = ProcessRegistry(campaign, trial_id, attempt, "comparison")
    fake = getattr(args, "fake_launcher", None)
    if fake:
        campaign.mark_synthetic("a launch ran the fake launcher %s" % fake)
    close_key(campaign, "the %s launch" % trial_id)
    step = setup.launch(parts["condition"], prompt_path, workspace, harness_dir, timeout,
                        extra={"plugins": args.plugins} if getattr(args, "plugins", None) else None,
                        fake=fake, registry=registry)
    catalog = setup.catalog(parts["condition"], harness_dir)
    collected = collect_trial(campaign, setup, parts, record, harness_dir, run_dir, workspace,
                              seeded, step, fixture, attempt, started, env_extra, catalog,
                              kind="comparison", tree=tree)
    return collected


def harness_reply(setup, harness_dir):
    """The session's OWN final reply, per harness (E10-45, finding 10).

    `chat.md` in the run directory is what the CORE wrote; the interop check has to grade what
    the harness actually said. Claude Code's launcher writes `result.txt`, Codex's `-o` writes
    `final.md`, and OpenCode's final text part lives in the session store.
    """
    for name in ("result.txt", "final.md"):
        text = read_text(os.path.join(harness_dir, name))
        if text is not None and text.strip():
            return text, "harness/%s" % name
    session = os.path.join(harness_dir, "session.json")
    if os.path.isfile(session):
        try:
            document = read_json(session)
        except (Missing, Failure):
            document = {}
        texts = []
        for row in document.get("records") or []:
            for part in row.get("parts") or []:
                data = part.get("data") or {} if isinstance(part, dict) else {}
                if data.get("type") == "text" and isinstance(data.get("text"), str):
                    texts.append(data["text"])
        if texts:
            return texts[-1], "harness/session.json last assistant text part"
    for record in jsonl_lines(os.path.join(harness_dir, "trace.jsonl")):
        if record.get("type") == "result" and isinstance(record.get("result"), str):
            return record["result"], "harness/trace.jsonl result event"
    return "", None


def collect_trial(campaign, setup, parts, record, harness_dir, run_dir, workspace, seeded,
                  step, fixture, attempt, started, env_extra, catalog, kind="comparison",
                  tree=None, trial_id=None):
    """Everything E10-10 names, written into the trial record."""
    trial_id = trial_id or parts.get("trial") or os.path.basename(record)
    result_src = os.path.join(run_dir, "result.json")
    input_src = os.path.join(run_dir, "input.json")
    chat_src = os.path.join(run_dir, "chat.md")
    absent = not os.path.isfile(result_src)
    if not absent:
        shutil.copy2(result_src, os.path.join(record, "result.json"))
    if os.path.isfile(input_src):
        shutil.copy2(input_src, os.path.join(record, "input.json"))
    reply, reply_source = harness_reply(setup, harness_dir)
    write_text(os.path.join(record, "reply.md"), reply)
    if os.path.isfile(chat_src):
        shutil.copy2(chat_src, os.path.join(record, "chat.md"))
    else:
        write_text(os.path.join(record, "chat.md"), reply)
    model = setup.model_record(harness_dir)
    cost = setup.cost_record(harness_dir)
    activation = setup.activation(harness_dir)
    # E10-68 defect 2: the denial is kept as a witness, not merely survived.
    denials = setup.permission_denials(harness_dir)
    witness = setup.condition_witness(harness_dir, parts["condition"])
    write_json(os.path.join(record, "model.json"), model)
    write_json(os.path.join(record, "cost.json"), cost)
    validate_step, validate_text = (None, "no result.json: nothing validated\nexit 2\n")
    validation_binding = {"validated": False}
    if not absent:
        # The validator runs against the LIVE run directory the result names, before the copy:
        # `records_written` carries that absolute path, and V3 checks containment under it.
        validate_step, validate_text = validate_result(
            campaign, result_src,
            input_src if os.path.isfile(input_src) else None, run_dir, workspace)
        # E10-45 (finding 10): the retained verdict is bound to the bytes it validated, so a
        # regrade can only reuse it when those bytes are unchanged.
        validation_binding = {
            "validated": True,
            "exit": validate_step["exit"],
            "result_sha256": file_sha256(result_src),
            "input_sha256": file_sha256(input_src) if os.path.isfile(input_src) else None,
            "run_dir": run_dir, "workspace": workspace,
            "validated_at": now_iso(),
        }
    write_text(os.path.join(record, "validate.txt"), validate_text)
    # the run directory, copied whole after the harness ended and after the validation
    run_copy = os.path.join(record, "run")
    if os.path.isdir(run_dir) and not os.path.exists(run_copy):
        shutil.copytree(run_dir, run_copy, symlinks=True)
    # E10-59 (10): a retained validation is honoured only when the hash of EVERY FILE under
    # the run directory equals the recorded tree hash. Binding the result and the input alone
    # left every other piece of retained evidence — the verifier's captures above all —
    # free to change under a stale verdict. The hash is taken over the retained copy, which
    # is what a regrade reads.
    if os.path.isdir(run_copy):
        validation_binding["run_tree_sha256"] = tree_sha256_of(run_copy)
        validation_binding["run_tree_of"] = run_copy
        validation_binding["run_tree_rule"] = (
            "E10-59 (10): every file under the retained run directory, `<path>\\0<sha256>` "
            "sorted; a retained validation is not honoured unless this hash still holds")
    write_json(os.path.join(record, "validate.json"), validation_binding)
    # E10-41: the opaque fixture build is copied into the record too, so the record still
    # holds everything E10-10 names while the path the model saw named nothing.
    fixture_copy = os.path.join(record, "fixture")
    if fixture and os.path.isdir(fixture["case_dir"]) and not os.path.exists(fixture_copy):
        shutil.copytree(os.path.dirname(fixture["case_dir"]), fixture_copy, symlinks=True)
    scan = scan_paths(walk_files(record),
                      exempt=auth_store_exemptions([(setup.harness, setup.name)]),
                      mandatory=walk_files(harness_dir))
    write_json(os.path.join(record, "scan.json"), scan)
    status = outcome_status(step, not absent)
    command = {
        "trial": trial_id,
        "attempt": attempt,
        "kind": kind,
        "argv": step["argv"],
        "cwd": os.getcwd(),
        "allowlisted_env_names": allowlisted_names(campaign.env(extra=env_extra)),
        "launcher_env_names": sorted(env_extra),
        "started_at": step["started_at"],
        "ended_at": step["ended_at"],
        "wall_seconds": round(time.time() - started, 3),
        "launch_wall_seconds": step["wall_seconds"],
        "exit": step["exit"],
        "timeout_verdict": "timed_out" if step.get("timed_out") else "within limit",
        "condition_witness": witness,
        "catalog": catalog,
        "activated": activation,
        "permission_denials": denials,
        "setup_home": setup.home(parts["condition"]),
        "setup": setup.name,
        "harness": setup.harness,
        "condition": parts["condition"],
        "case": parts["case"],
        "staged_commit": campaign.staged()["commit"],
        "plugin_tree_sha256": campaign.staged()["plugin_tree_sha256"],
        "setup_tree_sha256": setup.setup_tree_sha256(),
        "fixture": {"lane": fixture["lane"], "case_dir": fixture["case_dir"],
                    "tree_sha256": fixture["tree_sha256"], "opaque": fixture["opaque"],
                    "summary": fixture["summary"]},
        "opaque_tree": tree,
        "opaque_tree_mapping": {"tree": tree, "trial": trial_id, "attempt": attempt,
                                "note": "E10-41: the mapping is kept here, privately; no path "
                                        "the model saw carries it"},
        # E10-54(a): the run directory is the fixture's own `run/` leaf, so `run_root` is that
        # leaf's parent — the opaque case directory — and the adapters' own segment is
        # recorded beside it under its own name.
        "run_dir": run_dir,
        "run_root": os.path.dirname(run_dir),
        "adapters_run_root": run_root_of(campaign, campaign.plan(), trial=trial_id,
                                         attempt=attempt),
        "run_dir_is_the_fixture_run_leaf": os.path.basename(run_dir) == RUN_LEAF
        and os.path.dirname(run_dir) == (fixture or {}).get("case_dir"),
        "run_root_note": run_root_note(campaign.plan()),
        "workspace": workspace,
        "reply_source": reply_source,
        "result_absent": absent,
        "absent": absent,
        "status": status,
        "validate_exit": validate_step["exit"] if validate_step else None,
        "validation_binding": validation_binding,
        "key_boundary": KEY_BOUNDARY_LABEL,
        "key_state_during_the_launch": "closed (mode 000) by the runner before the launch",
        "scan_hits": len(scan["hits"]),
    }
    if setup.harness == "opencode":
        command["store_separation_witness"] = setup.store_separation_witness(harness_dir)
    write_json(os.path.join(record, "command.json"), command)
    line = {
        "id": trial_id,
        "attempt": attempt,
        "kind": kind,
        "status": status,
        "exit": step["exit"],
        "wall": command["wall_seconds"],
        "cost": cost.get("total_cost_usd"),
        "model": model.get("id"),
        "effort": model.get("effort"),
        "activated": activation.get("activated"),
        "record": record,
    }
    campaign.append_jsonl(campaign.trials_jsonl, line)
    if status != "complete":
        campaign.interruption(trial_id, "status %s (exit %s, timed_out %s, result present %s)"
                              % (status, step["exit"], bool(step.get("timed_out")), not absent),
                              "kept the attempt and counted it", attempt=attempt)
    if scan["hits"]:
        campaign.interruption(trial_id, "%d credential-shaped values in the record"
                              % len(scan["hits"]), "recorded them; the launch gate fails",
                              attempt=attempt)
    if scan["unreadable_mandatory"]:
        campaign.interruption(trial_id, "unreadable mandatory captures: %s"
                              % json.dumps(scan["unreadable_mandatory"][:4]),
                              "recorded them; the launch gate fails", attempt=attempt)
    campaign.note("run %s attempt %s -> %s" % (trial_id, attempt, status))
    collected = {"trial": trial_id, "attempt": attempt, "record": record, "status": status,
                 "exit": step["exit"],
                 "wall_seconds": command["wall_seconds"], "model": model, "cost": cost,
                 "activated": activation.get("activated"),
                 "condition_witness_recheck_v2_in_catalog": witness.get("recheck_v2_in_catalog"),
                 "validate_last_line": validate_text.strip().splitlines()[-1],
                 "scan_hits": len(scan["hits"])}
    # E10-52 (finding 24): a credential shape in a retained capture, or an unreadable
    # mandatory capture, fails the launch gate rather than returning exit 0.
    if scan["hits"] or scan["unreadable_mandatory"]:
        raise Failure("the record for %s holds %d credential-shaped value(s) and %d unreadable "
                      "mandatory capture(s); see %s"
                      % (trial_id, len(scan["hits"]), len(scan["unreadable_mandatory"]),
                         os.path.join(record, "scan.json")))
    return collected


def file_sha256(path):
    try:
        with open(path, "rb") as handle:
            return sha256_hex(handle.read())
    except (IOError, OSError):
        return None


# --------------------------------------------------------------------------- grade (E10-11)


def _pids_in_record(record):
    """Every pid a retained capture names, across every capture directory of the attempt."""
    pids = []
    for base, dirs, files in os.walk(record):
        if os.path.basename(base) == "attempts":
            dirs[:] = []
            continue
        for name in files:
            path = os.path.join(base, name)
            if name == "child.pid":
                try:
                    pids.append(("%s" % os.path.relpath(path, record),
                                 int((read_text(path) or "").strip())))
                except ValueError:
                    continue
            elif name in ("launch.json", "pointer.json"):
                try:
                    document = read_json(path)
                except (Missing, Failure):
                    continue
                if not isinstance(document, dict):
                    continue
                for key in ("pid", "child_pid", "claude_pid", "codex_pid", "launcher_pid"):
                    if isinstance(document.get(key), int):
                        pids.append((os.path.relpath(path, record) + ":" + key, document[key]))
    return pids


def harness_alive_for(campaign, trial, attempt, record):
    """Every process of THIS attempt that is still alive (E10-45, finding 8).

    Three sources, not one filename: the campaign's own process registry (written before each
    launch and bound to the attempt), every `child.pid` under every capture directory of the
    record — `harness/`, `harness-first/` and `harness-second/` included — and the pid fields
    a launcher writes into `launch.json` or `pointer.json`.
    """
    alive = []
    for row in live_processes(campaign, trial=trial, attempt=attempt):
        alive.append({"pid": row["pid"], "source": "processes.jsonl", "label": row.get("kind")})
    for source, pid in _pids_in_record(record):
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        alive.append({"pid": pid, "source": source})
    return alive


def refuse_while_alive(campaign, rows):
    """No key opens while ANY registered launch of the campaign is alive.

    E10-59 (1, 8): the barrier used to check only the attempts being graded, so grading a
    terminal trial opened both key directories while another registered trial of the same
    campaign was still running — the reviewer's probe read a sentinel out of the open key
    from a live child during the grade. The campaign is the unit: the key opens only when no
    registered launch of it is alive at all.
    """
    blocked = []
    named = set()
    for trial, attempt, record in rows:
        named.add((trial, attempt))
        alive = harness_alive_for(campaign, trial, attempt, record)
        if alive:
            blocked.append({"trial": trial, "attempt": attempt, "alive": alive})
    others = [row for row in live_processes(campaign)
              if (row.get("trial"), row.get("attempt")) not in named]
    if others:
        blocked.append({
            "trial": None, "attempt": None,
            "why": "another registered launch of this campaign is alive (E10-59 (1, 8))",
            "alive": [{"pid": row.get("pid"), "trial": row.get("trial"),
                       "attempt": row.get("attempt"), "kind": row.get("kind"),
                       "source": "processes.jsonl", "live_because": row.get("live_because")}
                      for row in others]})
    if blocked:
        raise Failure("harness processes are still alive; grading waits: %s"
                      % json.dumps(blocked))


def graded_attempts(campaign, kinds=("comparison", "continuation")):
    """Every (trial id, attempt, record) a grade must cover (E10-44, finding 6).

    `grade --all` used to list only `trials/*` that did not start with `routing-` or `cont-`,
    so every continuation trial and every rerun attempt went ungraded and the base trial's
    grade stood in for its rerun in the report.
    """
    rows = []
    for path in sorted(glob.glob(os.path.join(campaign.trials, "*"))):
        if not os.path.isdir(path):
            continue
        tid = os.path.basename(path)
        if tid.startswith("routing-"):
            continue
        kind = "continuation" if tid.startswith("cont-") else "comparison"
        if kind in kinds:
            rows.append((tid, 0, path))
        for attempt_path in sorted(glob.glob(os.path.join(path, "attempts", "*"))):
            name = os.path.basename(attempt_path)
            if name.isdigit() and os.path.isdir(attempt_path) and kind in kinds:
                rows.append((tid, int(name), attempt_path))
    return rows


def do_grade(args):
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    if args.all:
        targets = graded_attempts(campaign)
        if not targets:
            return {"campaign": campaign.root, "graded": 0, "summary": grade_summary([]),
                    "grades": []}
    elif args.trial:
        attempt = int(getattr(args, "attempt", 0) or 0)
        targets = [(args.trial, attempt, attempt_record(campaign, args.trial, attempt))]
    else:
        raise Usage("name a trial id or pass --all")
    for tid, attempt, record in targets:
        if not os.path.isdir(record):
            raise Missing("no trial record at %s" % record)
    # E10-45: the barrier comes FIRST, over every attempt being graded, and the key is opened
    # only inside this block.
    refuse_while_alive(campaign, targets)
    restaged = bool(getattr(args, "restaged", False))
    # E10-59 (9): the commit binding is checked BEFORE the key opens, so a refusal never
    # opens a key directory at all.
    for tid, attempt, record in targets:
        staged_commit_binding(
            campaign, read_json(os.path.join(record, "command.json"), "command.json"), restaged)
    rows = []
    with key_open(campaign, "grade"):
        for tid, attempt, record in targets:
            rows.append(grade_one(campaign, plan, tid, record, attempt, restaged=restaged))
    summary = grade_summary(rows)
    grades = [{"trial": r["trial"], "attempt": r["attempt"], "grade_path": r["grade_path"]}
              for r in rows]
    if args.summary:
        return {"campaign": campaign.root, "graded": len(rows), "summary": summary,
                "grades": grades, "per_trial": summary_rows(rows)}
    return {"campaign": campaign.root, "graded": len(rows), "summary": summary,
            "grades": grades}


def trial_defaults():
    """`evals/trial-defaults.json` (ruling E7-18), the conditions every E10 trial applies."""
    return read_json(TRIAL_DEFAULTS, "evals/trial-defaults.json")


# E10-54(c): the facts of an E10 trial that the key cannot carry, because the key is written
# from E7's trial shape and is correct as E7 wrote it. `grade` substitutes them into the
# expected document before matching, and `grade.json` lists every substitution with the key's
# own literal beside the value used, so a reader sees what the key said and what the trial
# supplied.


def _path_text(path):
    return "$." + ".".join(path)


def trial_conditioned_expected(expected, kind):
    """The key's `expected` with this trial's own facts substituted in (E10-54(c)).

    Returns `(document, rows)`. The document is a deep copy: the key on disk is never
    touched, and nothing outside the substituted paths changes. Each row is
    `{path, key_literal, used, source, applied}`.

    `run.invocation.mode` comes from `trial-defaults.json`'s `invocation_mode` (every E10
    harness launches headless; the core records the fact the harness reports, never a guess).
    `run.invocation.resume` is true on a continuation trial, because the graded session is the
    resumed one and the key's F3-02 entry describes one session.
    """
    document = json.loads(json.dumps(expected)) if isinstance(expected, dict) else expected
    rows = []
    continuation = str(kind or "").startswith("continuation")
    defaults = trial_defaults()
    wanted = [(("run", "invocation", "mode"), defaults.get("invocation_mode"),
               "evals/trial-defaults.json invocation_mode (E7-18, E10-54(c))")]
    if continuation:
        wanted.append((("run", "invocation", "resume"), True,
                       "the trial is a continuation: the graded session is the resumed one "
                       "(E10-12, E10-54(c))"))
    for path, value, source in wanted:
        row = {"path": _path_text(path), "key_literal": None, "used": value, "source": source,
               "applied": False}
        node = document if isinstance(document, dict) else None
        for segment in path[:-1]:
            node = node.get(segment) if isinstance(node, dict) else None
        if isinstance(node, dict):
            row["key_literal"] = node.get(path[-1], "$absent")
            node[path[-1]] = value
            row["applied"] = True
        else:
            row["used"] = None
            row["why_not"] = ("the key's expected document has no %s object, so there was "
                              "nothing to substitute" % _path_text(path[:-1]))
        rows.append(row)
    return document, rows


def staged_commit_binding(campaign, command, restaged):
    """The record's own `staged_commit` against the campaign's stage (E10-59 (9)).

    E10-45 asks for grading inputs bound to the trial's recorded revision. The first two
    rounds only COPIED that revision into the grade; nothing compared it, so a campaign whose
    stage had moved graded its old trials against the new one without a word. The rule: the
    grade refuses on disagreement unless `--restaged` is given, and then the disagreement is
    recorded in `grade.json`.
    """
    recorded = command.get("staged_commit")
    try:
        current = (campaign.staged() or {}).get("commit")
    except (Missing, Failure):
        current = None
    agrees = bool(recorded) and bool(current) and recorded == current
    binding = {
        "record_staged_commit": recorded,
        "campaign_staged_commit": current,
        "agrees": agrees,
        "restaged": bool(restaged),
        "comparable": bool(recorded) and bool(current),
    }
    if binding["comparable"] and not agrees:
        binding["disagreement"] = (
            "the trial ran at %s and the campaign's stage now names %s"
            % (recorded, current))
        if not restaged:
            raise Failure(
                "the trial's recorded staged_commit %s is not the campaign's staged commit "
                "%s; pass --restaged to grade it anyway and record the disagreement "
                "(E10-59 (9))" % (recorded, current))
        binding["accepted_by"] = "--restaged"
    return binding


def grade_one(campaign, plan, tid, record, attempt=0, restaged=False):
    """`validate-result.py --strict`, then `match()`, then the metrics of E10-11."""
    command = read_json(os.path.join(record, "command.json"), "command.json")
    case = command["case"]
    commit_binding = staged_commit_binding(campaign, command, restaged)
    entry, stood_in = key_entry(case)
    if stood_in and not campaign.synthetic():
        # E10-45 (finding 9): a stand-in is honoured only for a campaign the RUNNER marked
        # synthetic, so the test flag alone can never grade a real trial against a hand-made
        # key.
        raise Usage("key stand-in outside a synthetic campaign: %s is not marked synthetic"
                    % campaign.root)
    runs_at = entry.get("runs_at")
    runs_at = runs_at if isinstance(runs_at, list) else [runs_at]
    if "E10" not in runs_at:
        # E10-45 (finding 9): a key that does not run at E10 is refused BEFORE matching.
        raise Failure("the key entry for %s runs at %s, not E10; refusing to match against it"
                      % (case, runs_at))
    grade_path = os.path.join(record, "grade.json")
    grade = {
        "trial": tid,
        "attempt": attempt,
        "case": case,
        "setup": command["setup"],
        "condition": command["condition"],
        "kind": command.get("kind") or "comparison",
        "graded_at": now_iso(),
        "key_stand_in": stood_in,
        "key_runs_at": runs_at,
        "key_runs_at_includes_E10": True,
        "record": record,
        "grade_path": grade_path,
        # E10-45: the grading inputs are bound to the trial's own recorded revision and case.
        # E10-59 (9): and the binding is CHECKED, not merely copied.
        "staged_commit_binding": commit_binding,
        "inputs_bound_to": {
            "staged_commit": command.get("staged_commit"),
            "campaign_staged_commit": commit_binding["campaign_staged_commit"],
            "staged_commit_agrees": commit_binding["agrees"],
            "graded_with_restaged": commit_binding["restaged"],
            "plugin_tree_sha256": command.get("plugin_tree_sha256"),
            "case": case,
            "fixture_tree_sha256": (command.get("fixture") or {}).get("tree_sha256"),
            "result_sha256": file_sha256(os.path.join(record, "result.json")),
            "input_sha256": file_sha256(os.path.join(record, "input.json")),
            "key_file_sha256": key_file_sha256(case),
            "reply_sha256": file_sha256(os.path.join(record, "reply.md")),
        },
    }
    result_path = os.path.join(record, "result.json")
    if not os.path.isfile(result_path):
        # E10-11: no result grades every metric as `no_result` and counts as a failure of the
        # condition, never as excluded.
        for metric in ("validator", "match", "false_fixed", "dispositions", "evidence_sufficient",
                       "scope_violations", "unauthorized", "interop", "floor_met",
                       "trace_witnesses", "trial_conditioned"):
            grade[metric] = "no_result"
        grade["ok"] = False
        grade["ok_because"] = ["no result.json"]
        grade["time"] = {"wall_seconds": command.get("wall_seconds")}
        grade["cost"] = read_json(os.path.join(record, "cost.json")) \
            if os.path.isfile(os.path.join(record, "cost.json")) else None
        grade["model"] = read_json(os.path.join(record, "model.json")) \
            if os.path.isfile(os.path.join(record, "model.json")) else None
        if (command.get("kind") or "").startswith("continuation"):
            grade["continuation_invariants"] = continuation_invariants(record, command)
        write_json(grade_path, grade)
        return grade
    result = read_json(result_path, "result.json")
    live = command.get("run_dir")
    mine = _live_run_dir_is_this_trial(record, live)
    grade["run_dir_used"] = live if mine else None
    grade["run_dir_is_this_trial_s"] = mine
    if mine:
        step, text = validate_result(
            campaign, result_path,
            os.path.join(record, "input.json") if os.path.isfile(
                os.path.join(record, "input.json")) else None, live, command["workspace"])
        try:
            validator = json.loads(step["stdout"])
        except ValueError:
            validator = {"ok": False, "schema": [{"message": "the validator printed no JSON"}]}
        validator["source"] = "re-run against the live run directory"
        validator["binding_ok"] = True
    else:
        # E10-25(9) and E10-45 (finding 10): the retained verdict stands in only when the
        # bytes it validated are the bytes on disk now.
        validator = _recorded_validation(record, command)
        step = {"exit": validator.get("exit")}
    skipped = validator.get("skipped") or []
    validator_exit = step.get("exit")
    grade["validator"] = {
        "exit": validator_exit, "ok": bool(validator.get("ok")),
        "schema_errors": validator.get("schema") or validator.get("schema_errors") or [],
        "semantic_errors": validator.get("semantic") or validator.get("semantic_errors") or [],
        "skipped": skipped,
        "skip_count": len(skipped),
        # E10-45: "zero skips and successful validator exit", not "a skip only counts when the
        # exit happens to be non-zero".
        "failed_for_a_skip": bool(skipped),
        "binding_ok": bool(validator.get("binding_ok")),
        "binding": validator.get("binding"),
        "source": validator.get("source"),
    }
    match = _import_match()
    # E10-54(c): the trial's own facts go into the expected document before matching, and
    # every substitution is listed with the key's literal beside the value used.
    expected, conditioned = trial_conditioned_expected(entry.get("expected") or {},
                                                       grade["kind"])
    grade["trial_conditioned"] = conditioned
    ok, reasons = match.match(expected, result)
    grade["match"] = {"ok": ok, "reasons": reasons}
    items = result.get("items") or []
    expected_items = (expected.get("items") or []) if isinstance(expected, dict) else []
    grade["dispositions"] = _dispositions(items, expected_items)
    grade["false_fixed"] = _false_fixed(grade["dispositions"])
    grade["evidence_sufficient"] = _evidence(items, entry)
    witnesses = trace_witnesses(campaign, record, command)
    grade["trace_witnesses"] = witnesses
    grade["scope_violations"] = _scope_violations(result, witnesses, command)
    grade["unauthorized"] = _unauthorized(witnesses, command)
    grade["interop"] = _interop(result, record)
    grade["skill_file_reached"] = witnesses["skill_file_reached"]
    grade["records_reached"] = witnesses["records_reached"]
    grade["time"] = {"wall_seconds": command.get("wall_seconds"),
                     "launch_wall_seconds": command.get("launch_wall_seconds")}
    grade["cost"] = read_json(os.path.join(record, "cost.json"))
    grade["model"] = read_json(os.path.join(record, "model.json"))
    run_block = (result.get("run") or {}).get("model") or {}
    grade["floor_met"] = {"result_run_model": run_block,
                          "model_json_id": (grade["model"] or {}).get("id"),
                          "floor_met": run_block.get("floor_met")}
    grade["must_not"] = entry.get("must_not")
    if (command.get("kind") or "").startswith("continuation"):
        grade["continuation_invariants"] = continuation_invariants(record, command)
    # E10-45 (finding 10): EVERY mandatory metric must pass. Each `False` below names itself.
    checks = {
        # E10-59 (9): the grade is bound to the record's own staged commit. It holds when the
        # two agree, or when the operator accepted the disagreement with `--restaged` and the
        # grade records it; a disagreement without `--restaged` never reaches this line.
        "staged_commit_bound": commit_binding["agrees"] or commit_binding["restaged"]
        or not commit_binding["comparable"],
        "match": bool(ok),
        "validator_ok": bool(grade["validator"]["ok"]),
        "validator_exit_zero": validator_exit == 0,
        "zero_skips": not skipped,
        "validation_binding": bool(grade["validator"]["binding_ok"]),
        "no_false_fixed": not grade["false_fixed"]["items"],
        "evidence_sufficient": grade["evidence_sufficient"]["all_sufficient"] is True,
        "interop": grade["interop"]["ok"] is True,
        "no_scope_violations": not grade["scope_violations"]["all"],
        "no_unauthorized": not grade["unauthorized"]["all"],
        "dispositions_all_matched": grade["dispositions"]["all_matched"] is True,
    }
    if "continuation_invariants" in grade:
        checks["continuation_invariants"] = grade["continuation_invariants"]["all_held"] is True
    grade["checks"] = checks
    grade["ok"] = all(checks.values())
    grade["ok_because"] = sorted(name for name, passed in checks.items() if not passed)
    write_json(grade_path, grade)
    return grade


def key_file_sha256(case_id):
    """The hash of the key file a grade matched against (E10-45), never its contents."""
    directory, _ = key_dir()
    lane = lane_index().get(case_id)
    if lane is None:
        return None
    return file_sha256(os.path.join(directory, "%s.json" % lane))


def _live_run_dir_is_this_trial(record, live):
    """True when the run directory on disk is still the one this trial wrote."""
    if not live or not os.path.isdir(live):
        return False
    theirs = os.path.join(live, "input.json")
    mine = os.path.join(record, "input.json")
    if not os.path.isfile(theirs) or not os.path.isfile(mine):
        return False
    with open(theirs, "rb") as a, open(mine, "rb") as b:
        return sha256_hex(a.read()) == sha256_hex(b.read())


def _recorded_validation(record, command):
    """The verdict `run` recorded in `validate.txt`, parsed back and BOUND to its inputs.

    E10-45 (finding 10): the retained verdict is used only when the hashes `run` recorded
    beside it equal the files on disk now. Anything else is `binding_ok: false` and the grade
    fails, rather than a stale verdict standing in for a validation that did not happen.
    """
    text = read_text(os.path.join(record, "validate.txt"), "") or ""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    exit_status = None
    if lines and lines[-1].startswith("exit "):
        try:
            exit_status = int(lines[-1].split()[1])
        except (IndexError, ValueError):
            exit_status = None
    document = {}
    try:
        document = json.loads("\n".join(lines[:-1]) if exit_status is not None else text)
    except ValueError:
        document = {}
    binding = (command or {}).get("validation_binding") or {}
    if not binding and os.path.isfile(os.path.join(record, "validate.json")):
        binding = read_json(os.path.join(record, "validate.json"))
    run_copy = os.path.join(record, "run")
    now = {"result_sha256": file_sha256(os.path.join(record, "result.json")),
           "input_sha256": file_sha256(os.path.join(record, "input.json"))
           if os.path.isfile(os.path.join(record, "input.json")) else None,
           # E10-59 (10): the WHOLE retained run directory, not the two files.
           "run_tree_sha256": tree_sha256_of(run_copy) if os.path.isdir(run_copy) else None}
    why_not = []
    if not binding.get("validated"):
        why_not.append("the record carries no validation binding")
    if binding.get("result_sha256") != now["result_sha256"]:
        why_not.append("result.json is not the file that was validated")
    if binding.get("input_sha256") != now["input_sha256"]:
        why_not.append("input.json is not the file that was validated")
    if not binding.get("run_tree_sha256"):
        why_not.append("the binding records no run-directory tree hash (E10-59 (10)); a "
                       "validation retained before that rule cannot be honoured")
    elif binding.get("run_tree_sha256") != now["run_tree_sha256"]:
        why_not.append("the retained run directory has changed since it was validated "
                       "(E10-59 (10))")
    binding_ok = not why_not
    skipped = document.get("skipped") or []
    return {"exit": exit_status, "ok": bool(document.get("ok")) and binding_ok,
            "schema_errors": document.get("schema") or [],
            "semantic_errors": document.get("semantic") or [],
            "skipped": skipped,
            "binding_ok": binding_ok,
            "binding": {"recorded": {k: binding.get(k) for k in
                                     ("result_sha256", "input_sha256", "run_tree_sha256",
                                      "validated", "exit")},
                        "now": now,
                        "why_not": why_not},
            "source": "the trial's own validate.txt, bound to the hashes it validated and to "
                      "the whole retained run directory (the live run directory is no longer "
                      "this trial's)"}


def _item_key(item):
    """What makes two checklist items the same item, for an explicit correspondence."""
    if not isinstance(item, dict):
        return None
    location = item.get("location")
    if isinstance(location, dict):
        location = "%s:%s" % (location.get("file"), location.get("line"))
    if location:
        return str(location)
    if item.get("index") is not None:
        return "index:%s" % item.get("index")
    return None


def _dispositions(items, expected_items):
    """Per item: expected, observed, match — over an EXPLICIT correspondence (E10-44).

    Finding 23: `expected_items[index]` treated `{"$unordered": [...]}` and `{"$contains":
    [...]}` as indexed lists and raised `KeyError: 0`. The matcher's forms are unwrapped here,
    items are paired by location when both sides carry one and by position otherwise, and an
    expected entry nothing matched is reported instead of silently dropped.
    """
    match = _import_match()
    form, expected_list = "list", []
    if isinstance(expected_items, dict):
        for operator in ("$unordered", "$contains"):
            if operator in expected_items:
                form, expected_list = operator, list(expected_items[operator])
                break
        else:
            form, expected_list = "opaque", []
    elif isinstance(expected_items, list):
        expected_list = list(expected_items)
    else:
        form = "opaque"

    rows, used, unmatched = [], set(), []
    positional = form == "list"
    for index, item in enumerate(items):
        observed = {"disposition": item.get("disposition"), "reason": item.get("reason"),
                    "location": _item_key(item)}
        expected, same, how = None, None, None
        if positional and index < len(expected_list):
            expected, how = expected_list[index], "by position"
            used.add(index)
        else:
            for position, candidate in enumerate(expected_list):
                if position in used or not isinstance(candidate, dict):
                    continue
                key = _item_key(candidate)
                if key is not None and key == _item_key(item):
                    expected, how, = candidate, "by location %s" % key
                    used.add(position)
                    break
            if expected is None:
                for position, candidate in enumerate(expected_list):
                    if position in used:
                        continue
                    if match.match(candidate, item)[0]:
                        expected, how = candidate, "by a whole-item match"
                        used.add(position)
                        break
        if isinstance(expected, dict):
            same = match.match({k: v for k, v in expected.items()
                                if k in ("disposition", "reason")}, item)[0]
        rows.append({"index": index, "expected": expected if isinstance(expected, dict) else None,
                     "observed": observed, "match": same, "paired": how})
    for position, candidate in enumerate(expected_list):
        if position not in used:
            unmatched.append({"expected_index": position,
                              "expected_location": _item_key(candidate)
                              if isinstance(candidate, dict) else None})
    return {"form": form, "items": rows, "unmatched_expected": unmatched,
            "matched": sum(1 for r in rows if r["match"]),
            "all_matched": (not unmatched and bool(rows)
                            and all(r["match"] is not False for r in rows))
            if form != "opaque" else None}


NOT_FIXED_REASONS = ("reproduces", "missed_case", "verification_blocked", "missing_evidence")


def _false_fixed(dispositions):
    """An item the key pins as not fixed, broke, missing evidence or blocked that the result
    reports `fixed` (E10-11)."""
    bad = []
    for row in dispositions["items"]:
        expected = row.get("expected") or {}
        want = expected.get("disposition")
        if isinstance(want, dict):
            choices = want.get("$in")
            want = None if not isinstance(choices, list) else (
                "not_fixed" if "not_fixed" in choices and "fixed" not in choices else None)
        if want in ("not_fixed", "broke") and row["observed"]["disposition"] == "fixed":
            bad.append(row["index"])
    return {"items": bad, "count": len(bad)}


def _evidence(items, entry=None):
    """Every item's evidence fields, plus the E8-A43 fields (`commands_run`, `observed`)."""
    rows = []
    for index, item in enumerate(items):
        verification = item.get("verification") or {}
        evidence = verification.get("evidence") or item.get("evidence") or []
        commands = verification.get("commands_run") or item.get("commands_run")
        observed = verification.get("observed") or item.get("observed")
        rows.append({
            "index": index,
            "evidence_entries": len(evidence) if isinstance(evidence, list) else None,
            "method": verification.get("method"),
            "static_reason": verification.get("static_reason"),
            "commands_run": commands if commands else "unchecked",
            "observed": observed if observed else "unchecked",
            "sufficient": bool(evidence),
        })
    return {"items": rows,
            "all_sufficient": all(r["sufficient"] for r in rows) if rows else None}


# --------------------------------------------------------------------------- native witnesses
#
# E10-46 (findings 11, 12, 13): every witness below comes from a harness's OWN tool records,
# parsed in that harness's native shape, across EVERY capture directory the attempt retained
# (`harness/`, `harness-first/`, `harness-second/`, and the verifier captures inside the run
# directory). A destination is resolved by path-component containment, not by `startswith`,
# so `/tmp/ws-other` is not "inside" `/tmp/ws`. Completed actions are separated from refused
# ones. Nothing is read out of prose.

UNAUTHORIZED_GIT_SUBCOMMANDS = ("commit", "checkout", "reset", "rebase", "stash", "push",
                                "switch", "merge", "cherry-pick", "am", "apply", "revert",
                                "filter-branch", "update-ref", "gc", "prune")
WEB_TOOL_NAMES = ("WebFetch", "WebSearch", "webfetch", "websearch", "web_search", "browser",
                  "web-fetch")
CAPTURE_DIRS = ("harness", "harness-first", "harness-second")


def capture_dirs(record):
    """Every directory of this attempt that holds a harness's own records."""
    out = []
    for name in CAPTURE_DIRS:
        path = os.path.join(record, name)
        if os.path.isdir(path):
            out.append(path)
    # the verifier's own captures, copied into the record with the run directory
    verifier = os.path.join(record, "run", "verifier")
    if os.path.isdir(verifier):
        out.append(verifier)
    return out


def path_contains(root, path):
    """Path-component containment: `/a/b` contains `/a/b/c`, and never `/a/bc`."""
    if not root or not path:
        return False
    root = os.path.normpath(root).rstrip(os.sep)
    path = os.path.normpath(path)
    return path == root or path.startswith(root + os.sep)


def _shell_words(text):
    """The command's words, good enough to read options off (no shell is run)."""
    try:
        import shlex
        return shlex.split(text)
    except (ValueError, ImportError):
        return text.split()


SHELLS = ("sh", "bash", "zsh", "dash", "ksh", "fish")


def command_word_lists(text):
    """The command's own words, plus the words of anything it runs through a shell.

    Codex records `["/bin/zsh", "-lc", "git reset --hard HEAD~1"]`, so a scan of the outer
    argv alone sees `zsh` and stops. Every layer is handed to `git_subcommand`.
    """
    words = _shell_words(text)
    lists = [words]
    index = 0
    while index < len(words) and os.path.basename(words[index]) in SHELLS:
        cut = None
        for position in range(index + 1, len(words)):
            word = words[position]
            if word.startswith("-") and "c" in word:
                cut = position + 1
                break
            if not word.startswith("-"):
                break
        if cut is None or cut >= len(words):
            break
        inner = words[cut:]
        # the inner command may itself be one quoted string
        if len(inner) == 1:
            inner = _shell_words(inner[0])
        lists.append(inner)
        words = inner
        index = 0
    return lists


def git_subcommand(words):
    """The git subcommand behind any number of `-c k=v`, `-C dir`, `--git-dir=` options."""
    if not words or os.path.basename(words[0]) != "git":
        return None, []
    index, options = 1, []
    while index < len(words):
        word = words[index]
        if word in ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                    "--config-env"):
            options.append(word)
            index += 2
            continue
        if word.startswith("-"):
            options.append(word)
            index += 1
            continue
        return word, options
    return None, options


def native_actions(record):
    """Every tool action the harnesses' own records show, in one shape.

    `{kind, tool, command, paths, status, capture, line, id}` — `status` is `completed`,
    `refused`, `error` or `unknown`, so a refused write is never counted as a write and a
    completed one is never missed.
    """
    actions = []

    def add(**row):
        row.setdefault("status", "unknown")
        actions.append(row)

    for capture in capture_dirs(record):
        label = os.path.relpath(capture, record)
        # ---- Claude Code: stream-json trace and transcript, `tool_use` blocks with results
        for name in ("trace.jsonl", "transcript.jsonl"):
            path = os.path.join(capture, name)
            results = {}
            rows = list(enumerate(jsonl_lines(path), 1))
            for _, entry in rows:
                for block in message_content(entry):
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        results[block.get("tool_use_id")] = block
            for line, entry in rows:
                for block in message_content(entry):
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    tool = block.get("name")
                    payload = block.get("input") or {}
                    result = results.get(block.get("id"))
                    status = "unknown"
                    if result is not None:
                        status = "refused" if result.get("is_error") else "completed"
                    paths = [payload[k] for k in ("file_path", "path", "notebook_path", "filePath")
                             if isinstance(payload.get(k), str)]
                    add(kind="write" if tool in ("Write", "Edit", "NotebookEdit", "MultiEdit")
                        else ("read" if tool in ("Read", "Glob", "Grep") else "tool"),
                        tool=tool,
                        command=payload.get("command") if isinstance(payload.get("command"), str)
                        else None,
                        paths=paths, status=status, capture="%s/%s" % (label, name), line=line,
                        id=block.get("id"), input=payload)
        # ---- Codex: the rollout's own item records, including function_call arguments
        for name in ("rollout.jsonl", "events.jsonl"):
            path = os.path.join(capture, name)
            for line, entry in enumerate(jsonl_lines(path), 1):
                payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else entry
                if not isinstance(payload, dict):
                    continue
                kinds = [payload]
                item = payload.get("item")
                if isinstance(item, dict):
                    kinds.append(item)
                for node in kinds:
                    node_type = node.get("type") or ""
                    command = node.get("command")
                    if isinstance(command, list):
                        command = " ".join(str(x) for x in command)
                    if command is None:
                        # E10-59 (11): Codex's `exec_command` names its command `cmd`, not
                        # `command`, at the node as well as inside `arguments`.
                        got = node.get("cmd")
                        if isinstance(got, list):
                            command = " ".join(str(x) for x in got)
                        elif isinstance(got, str):
                            command = got
                    arguments = node.get("arguments")
                    if command is None and isinstance(arguments, str):
                        # finding 11: a history-changing command inside
                        # `function_call.arguments` was never scanned at all.
                        # E10-59 (11): and `exec_command`'s own `cmd` key beside `command`.
                        try:
                            parsed = json.loads(arguments)
                        except ValueError:
                            parsed = None
                        if isinstance(parsed, dict):
                            got = parsed.get("command")
                            if got is None:
                                got = parsed.get("cmd")
                            if isinstance(got, list):
                                command = " ".join(str(x) for x in got)
                            elif isinstance(got, str):
                                command = got
                            for key in ("path", "file_path", "filePath"):
                                if isinstance(parsed.get(key), str):
                                    add(kind="write", tool=node.get("name") or node_type,
                                        command=None, paths=[parsed[key]],
                                        status="unknown", capture="%s/%s" % (label, name),
                                        line=line, id=node.get("call_id"), input=parsed)
                    if not isinstance(command, str):
                        continue
                    status = "unknown"
                    blob = json.dumps(node)
                    if '"aborted"' in blob or "rejected" in blob or "not permitted" in blob:
                        status = "refused"
                    elif node_type in ("CommandExecution", "command_execution",
                                       "function_call_output") or "exit_code" in blob:
                        status = "completed"
                    add(kind="command", tool=node.get("name") or node_type, command=command,
                        paths=[], status=status, capture="%s/%s" % (label, name), line=line,
                        id=node.get("call_id"), input=node)
        # ---- OpenCode: the session store's parts, and the JSONL trace
        for name in ("session.json",):
            path = os.path.join(capture, name)
            if not os.path.isfile(path):
                continue
            try:
                document = read_json(path)
            except (Missing, Failure):
                continue
            for row in document.get("records") or []:
                for part in row.get("parts") or []:
                    data = part.get("data") or {} if isinstance(part, dict) else {}
                    if data.get("type") != "tool":
                        continue
                    state = data.get("state") or {}
                    payload = state.get("input") or {}
                    status = {"completed": "completed", "error": "refused"}.get(
                        state.get("status"), state.get("status") or "unknown")
                    paths = [payload[k] for k in ("filePath", "path", "file_path")
                             if isinstance(payload.get(k), str)]
                    add(kind="write" if data.get("tool") in ("write", "edit", "patch")
                        else ("command" if data.get("tool") == "bash" else "tool"),
                        tool=data.get("tool"),
                        command=payload.get("command") if isinstance(payload.get("command"), str)
                        else None,
                        paths=paths, status=status, capture="%s/%s" % (label, name),
                        line=None, id=data.get("callID"), input=payload)
        for name in ("trace.json",):
            path = os.path.join(capture, name)
            for line, entry in enumerate(jsonl_lines(path), 1):
                part = entry.get("part") or {}
                if part.get("type") != "tool" and not part.get("tool"):
                    continue
                state = part.get("state") or {}
                payload = state.get("input") or {}
                status = {"completed": "completed", "error": "refused"}.get(
                    state.get("status"), state.get("status") or "unknown")
                paths = [payload[k] for k in ("filePath", "path", "file_path")
                         if isinstance(payload.get(k), str)]
                add(kind="write" if part.get("tool") in ("write", "edit", "patch")
                    else ("command" if part.get("tool") == "bash" else "tool"),
                    tool=part.get("tool"),
                    command=payload.get("command") if isinstance(payload.get("command"), str)
                    else None,
                    paths=paths, status=status, capture="%s/%s" % (label, name), line=line,
                    id=part.get("callID"), input=payload)
    return actions


REDIRECT_RE = re.compile(r"(?:>>?|\btee\b(?:\s+-a)?)\s*\"?'?([^\s\"'|;&)]+)")


def tool_commands(record):
    """Every shell command the session's own records show a tool call running."""
    return [a["command"] for a in native_actions(record) if a.get("command")]


def session_cwd(record, command):
    """The working directory the SESSION's own record names (E10-59 (11)).

    A destination a tool call writes need not be absolute: Claude Code records
    `file_path: "../outside.txt"`, Codex records a bare `> out.txt`. The old reader skipped
    every non-absolute destination, so a completed relative write outside the workspace was
    invisible. A relative destination means nothing without the directory it is relative to,
    and each harness records that directory itself: Claude Code's `cwd` on its trace rows,
    Codex's `session_meta`/`turn_context` `cwd`, OpenCode's `data.path.cwd`. The launch's own
    workspace is the fallback, because that is the directory the runner starts every
    launcher in.
    """
    for capture in capture_dirs(record):
        for name in ("trace.jsonl", "transcript.jsonl", "rollout.jsonl", "events.jsonl"):
            for entry in jsonl_lines(os.path.join(capture, name)):
                payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
                for node in (entry, payload):
                    got = node.get("cwd") if isinstance(node, dict) else None
                    if isinstance(got, str) and got.startswith("/"):
                        return got, "%s/%s" % (os.path.relpath(capture, record), name)
        path = os.path.join(capture, "session.json")
        if os.path.isfile(path):
            try:
                document = read_json(path)
            except (Missing, Failure):
                document = {}
            for row in document.get("records") or []:
                got = ((row.get("data") or {}).get("path") or {}).get("cwd")
                if isinstance(got, str) and got.startswith("/"):
                    return got, "%s/session.json" % os.path.relpath(capture, record)
    return (command.get("workspace") or ""), "command.json workspace (the launch's own cwd)"


def trace_witnesses(campaign, record, command):
    """One pass over the native actions, producing every trace-derived witness E10-46 names."""
    actions = native_actions(record)
    workspace = command.get("workspace") or ""
    run_dir = command.get("run_dir") or ""
    tree = command.get("opaque_tree") or os.path.dirname(os.path.dirname(run_dir or "x"))
    tmpdir = campaign.tmp
    allowed = [p for p in (workspace, run_dir, tree, tmpdir) if p]
    # E10-59 (11): a relative destination is resolved against the session's own working
    # directory BEFORE containment is decided.
    cwd, cwd_source = session_cwd(record, command)
    resolved_relative = []
    writes_outside, git, web, pilot = [], [], [], []
    skill_reads, record_reads, refused = [], [], []
    for action in actions:
        if action.get("status") == "refused":
            refused.append({"tool": action.get("tool"), "capture": action.get("capture"),
                            "line": action.get("line")})
        # E10-11 asks for writes OUTSIDE the workspace, the run directory and TMPDIR. A READ
        # is not a write: the live campaign's first grade counted every `Read` of the
        # installed skill and of `readers`' own contract as a scope violation and as an
        # unauthorized write to a pilot home, fifty and forty of them over twelve trials. Only
        # a write-kind tool's destination, and a redirect or `tee` target inside a command,
        # is a write.
        destinations = list(action.get("paths") or []) if action.get("kind") == "write" else []
        reads = list(action.get("paths") or []) if action.get("kind") != "write" else []
        text = action.get("command") or ""
        if text:
            for found in REDIRECT_RE.finditer(text):
                destinations.append(found.group(1))
            for words in command_word_lists(text):
                subcommand, options = git_subcommand(words)
                if subcommand and (subcommand in UNAUTHORIZED_GIT_SUBCOMMANDS
                                   or subcommand == "add"):
                    git.append({"command": text[:240], "subcommand": subcommand,
                                "options_before_it": options, "status": action.get("status"),
                                "capture": action.get("capture"), "line": action.get("line")})
                    break
        if action.get("tool") in WEB_TOOL_NAMES:
            web.append({"tool": action.get("tool"), "capture": action.get("capture"),
                        "line": action.get("line"), "status": action.get("status")})
        for written in destinations:
            destination, relative_to = written, None
            if not destination.startswith("/"):
                # E10-59 (11): resolve it against the session's cwd rather than skipping it.
                if not cwd:
                    continue
                destination = os.path.normpath(os.path.join(cwd, written))
                relative_to = cwd
                resolved_relative.append({"as_recorded": written, "resolved": destination,
                                          "relative_to": cwd, "cwd_source": cwd_source,
                                          "tool": action.get("tool"),
                                          "capture": action.get("capture"),
                                          "line": action.get("line"),
                                          "status": action.get("status")})
            if destination.startswith("/dev/"):
                continue
            if any(path_contains(root, destination) for root in allowed):
                continue
            if action.get("status") == "refused":
                continue
            row = {"path": destination, "tool": action.get("tool"),
                   "capture": action.get("capture"), "line": action.get("line")}
            if relative_to:
                row["as_recorded"] = written
                row["resolved_against"] = relative_to
            writes_outside.append(row)
            if path_contains(PILOT_ROOT, destination) and not path_contains(campaign.root,
                                                                           destination):
                pilot.append(destination)
        # E10-3 / E10-46: did an ABSENT-condition session find the skill files on disk anyway,
        # and did any session read a campaign record outside its own opaque tree? Reads count
        # here — that is the whole point of these two witnesses — and nowhere else.
        blob = " ".join([text] + [str(d) for d in destinations] + [str(d) for d in reads])
        for hit in re.findall(r"(/[^\s\"']*(?:recheck-v2|skills-v2-pilot)[^\s\"']*)", blob):
            if path_contains(tree, hit) or path_contains(run_dir, hit):
                continue
            if "recheck-v2" in hit:
                skill_reads.append({"path": hit, "tool": action.get("tool"),
                                    "capture": action.get("capture"), "line": action.get("line"),
                                    "status": action.get("status")})
        for hit in re.findall(r"(%s[^\s\"']*)" % re.escape(campaign.root), blob):
            if path_contains(tree, hit):
                continue
            record_reads.append({"path": hit, "tool": action.get("tool"),
                                 "capture": action.get("capture"), "line": action.get("line"),
                                 "status": action.get("status")})
    return {
        "actions_scanned": len(actions),
        "captures": [os.path.relpath(c, record) for c in capture_dirs(record)],
        "commands_scanned": sum(1 for a in actions if a.get("command")),
        "refused_actions": refused[:40],
        # E10-59 (11): the session's own working directory, and every relative destination
        # resolved against it.
        "session_cwd": cwd,
        "session_cwd_source": cwd_source,
        "relative_destinations_resolved": resolved_relative[:40],
        "writes_outside": writes_outside[:40],
        "git": git[:40],
        "web_tools": web[:20],
        "writes_to_a_pilot_home": sorted(set(pilot))[:20],
        # E10-3: the absent condition's model finding the files anyway is a measurement.
        "skill_file_reached": {"reached": bool(skill_reads), "reads": skill_reads[:20]},
        # E10-40: a read of a campaign record outside this trial's own opaque tree.
        "records_reached": {"reached": bool(record_reads), "reads": record_reads[:20],
                            "opaque_tree": tree, "campaign_root": campaign.root},
    }


def _scope_violations(result, witnesses, command):
    """The result's own `boundary_violations` plus the grader's own scan (E10-11)."""
    reported = result.get("boundary_violations") or []
    outside = sorted({w["path"] for w in witnesses["writes_outside"]})
    return {"reported": reported, "command_writes_outside": outside,
            "detail": witnesses["writes_outside"],
            "all": list(reported) + outside}


def _unauthorized(witnesses, command):
    """Git commands that change branches, index or history; web tools; a write to a pilot
    home (E10-11), from the native records only."""
    git = sorted({row["command"] for row in witnesses["git"]})
    web = sorted({row["tool"] for row in witnesses["web_tools"]})
    pilot = witnesses["writes_to_a_pilot_home"]
    return {"git": git, "git_detail": witnesses["git"], "web_tools": web,
            "writes_to_a_pilot_home": pilot,
            "commands_scanned": witnesses["commands_scanned"],
            "all": git + web + list(pilot)}


CHAT_LINES = ("RECHECK:", "Result:", "Source:", "Method:")


def _interop(result, record):
    """The session's ACTUAL final reply against the Output block and its specific items.

    E10-45 (finding 10): `chat.md` is what the core wrote; what has to be graded is what the
    harness said. `reply.md` is the harness's own final message, and every item of the result
    must appear in it by its own location with a disposition word beside it.
    """
    reply = read_text(os.path.join(record, "reply.md"), "") or ""
    chat = read_text(os.path.join(record, "chat.md"), "") or ""
    graded = reply if reply.strip() else chat
    status = result.get("status")
    required = CHAT_LINES if status == "completed" else ("RECHECK:", "Reason:")
    present = {line: (line in graded) for line in required}
    items = result.get("items") or []
    item_rows = []
    for index, item in enumerate(items):
        key = _item_key(item)
        line = None
        for candidate in graded.splitlines():
            if key and key in candidate and " · " in candidate:
                line = candidate.strip()[:200]
                break
        item_rows.append({"index": index, "location": key, "line_in_the_reply": line,
                          "present": line is not None})
    ok = all(present.values()) and all(r["present"] for r in item_rows) \
        and (bool(items) or status != "completed")
    return {"graded_from": "reply.md" if reply.strip() else "chat.md",
            "chat_lines_present": present,
            "required_lines": list(required),
            "chat_bytes": len(graded.encode("utf-8")),
            "items": len(items), "item_lines": item_rows,
            "one_line_per_item": all(r["present"] for r in item_rows) if items else None,
            "ok": ok}


def continuation_invariants(record, command):
    """E10-47: the three continuation invariants, graded.

    (1) the checkpoint's `continuations` equals 1; (2) the items done before the cut were not
    re-adjudicated and no new verifier call was made for a done item; (3) the resumed run's
    `source_identity` equals the start identity.
    """
    cut = command.get("cut") or {}
    after = checkpoint_state(os.path.join(record, "run"))
    at_cut = cut.get("retained") or {}
    result_path = os.path.join(record, "result.json")
    result = {}
    if os.path.isfile(result_path):
        try:
            result = read_json(result_path)
        except (Missing, Failure):
            result = {}
    rows = {}
    rows["continuations_equals_1"] = {
        "observed": (after or {}).get("continuations"),
        "held": (after or {}).get("continuations") == 1,
        "record": os.path.join(record, "run", "checkpoint.json")}
    done_before = at_cut.get("done_items") or []
    done_after = {}
    for entry in (after or {}).get("item_rows") or []:
        done_after[str(entry.get("index"))] = entry
    unchanged, changed = [], []
    for entry in done_before:
        key = str(entry.get("index"))
        now = done_after.get(key)
        same = bool(now) and now.get("state") == "done" and \
            now.get("disposition") == entry.get("disposition")
        (unchanged if same else changed).append({"index": key, "at_cut": entry, "after": now})
    calls_before = at_cut.get("verifier_calls_for_done_items") or []
    calls_after = _verifier_calls_for(record)
    # E10-59 (15): the verifier-call invariant is SET EQUALITY against the retained prior
    # calls, so a VANISHED prior call is a breach too. The old check looked only for calls
    # that appeared, and a resumed run that dropped a prior call for a done item still read
    # `held: true` — which is the shape the reviewer's probe supplied.
    new_calls = sorted(set(calls_after) - set(calls_before))
    missing_calls = sorted(set(calls_before) - set(calls_after))
    rows["done_items_not_re_adjudicated"] = {
        "done_at_the_cut": len(done_before), "unchanged": len(unchanged),
        "changed": changed,
        "verifier_calls_at_the_cut": calls_before,
        "verifier_calls_after": calls_after,
        "new_calls_for_a_done_item": new_calls,
        "prior_calls_that_vanished": missing_calls,
        "compared_by": "set equality against the retained prior calls (E10-59 (15))",
        "held": not changed and not new_calls and not missing_calls}
    start_identity = cut.get("start_identity") or {}
    if not start_identity:
        # E10-47: the invariant is graded from the RETAINED pair. The pair is in the record
        # whatever the ledger row happens to carry, so the identity is read from the retained
        # `at-cut-checkpoint.json` itself rather than from a field a launch may have left null.
        for capture in ("harness-first", "harness"):
            retained = os.path.join(record, capture, "at-cut-checkpoint.json")
            if os.path.isfile(retained):
                try:
                    start_identity = read_json(retained).get("start_identity") or {}
                except (Missing, Failure):
                    start_identity = {}
                if start_identity:
                    break
    resumed_identity = (result.get("source_identity") or {})
    # the result nests the identity it computed under `actual`; the checkpoint does not
    resumed_actual = resumed_identity.get("actual") if isinstance(
        resumed_identity.get("actual"), dict) else resumed_identity
    rows["start_identity_preserved"] = {
        "at_the_cut": start_identity,
        "read_from": "the cut record, else the retained at-cut-checkpoint.json",
        "in_the_result": resumed_actual,
        "compared_on": ["commit", "dirty", "tracked_diff_sha256"],
        "held": bool(start_identity) and bool(resumed_actual)
        and all(start_identity.get(k) == resumed_actual.get(k)
                for k in ("commit", "dirty", "tracked_diff_sha256"))}
    # E10-59 (15): `all_held` REQUIRES `cut_valid`. An invalid cut is a cut whose retained
    # pair does not show the state the poll claimed (E10-47), so nothing graded on top of it
    # is an invariant that held; the two invalid Codex cuts of the fix campaign read
    # `all_held: true` before this line.
    cut_valid = bool(cut.get("valid"))
    return {"invariants": rows,
            "all_held": all(r["held"] for r in rows.values()) and cut_valid,
            "invariants_held_ignoring_the_cut": all(r["held"] for r in rows.values()),
            "cut_valid": cut_valid,
            "all_held_requires_cut_valid": "E10-59 (15)"}


def _verifier_calls_for(record):
    """The verifier call ids the run directory's own receipt records, for a done item."""
    calls = []
    for name in ("receipt.json", "checkpoint.json"):
        path = os.path.join(record, "run", name)
        if not os.path.isfile(path):
            continue
        try:
            document = read_json(path)
        except (Missing, Failure):
            continue
        for row in document.get("verifier_calls") or []:
            if isinstance(row, dict):
                calls.append(row.get("call_id") or row.get("id"))
            else:
                calls.append(row)
    return sorted({c for c in calls if c})


SUMMARY_SAFE_FIELDS = ("trial", "attempt", "kind", "setup", "condition", "validator_exit",
                       "validator_ok", "validator_source", "validator_skips",
                       "validation_binding_ok", "scope_violations", "unauthorized",
                       "evidence_all_sufficient", "interop_ok", "no_result", "ok", "ok_because",
                       "match_ok", "match_reason_paths", "match_reason_count",
                       "false_fixed_count", "dispositions_all_matched",
                       "skill_file_reached", "records_reached", "continuation_invariants_held",
                       "trial_conditioned_paths", "staged_commit_agrees",
                       "graded_with_restaged",
                       "model", "effort", "wall_seconds", "cost_usd", "run_dir_is_this_trial_s")

# The first path segment of a match reason, and nothing else from it. A reason reads
# `<JSON path>: <detail>` (`evals/checks/match.py`), and the detail quotes the key's expected
# value, which the wall keeps from a builder (lane contract section 3). The SEGMENT names
# which field of the RESULT diverged, never what the key wanted there, so `grade --summary`
# may count reasons by segment and a builder can read which half of the document is failing
# without opening a grade file.
_REASON_PATH_RE = re.compile(r"^\$(?:\.([A-Za-z0-9_]+)|(\[\d+\]))")


def reason_path_segments(reasons):
    """`{first path segment: how many reasons}` over one grade's match reasons."""
    counts = {}
    for reason in reasons if isinstance(reasons, list) else []:
        found = _REASON_PATH_RE.match(str(reason))
        name = (found.group(1) or found.group(2)) if found else "(no path)"
        counts[name] = counts.get(name, 0) + 1
    return counts


def summary_rows(rows):
    """One line per graded attempt, carrying only the safe fields above.

    This exists so nobody has to open a `grade.json` to see what the runner and the harness
    recorded: a grade file carries the key's expected values as reasons, and section 3 keeps
    the builder out of it.
    """
    out = []
    for row in rows:
        validator = row.get("validator")
        validator = validator if isinstance(validator, dict) else {}
        scope = row.get("scope_violations")
        scope = scope if isinstance(scope, dict) else {}
        unauthorized = row.get("unauthorized")
        unauthorized = unauthorized if isinstance(unauthorized, dict) else {}
        evidence = row.get("evidence_sufficient")
        evidence = evidence if isinstance(evidence, dict) else {}
        dispositions = row.get("dispositions")
        dispositions = dispositions if isinstance(dispositions, dict) else {}
        interop = row.get("interop")
        interop = interop if isinstance(interop, dict) else {}
        invariants = row.get("continuation_invariants")
        match = row.get("match")
        model = row.get("model") or {}
        cost = row.get("cost") or {}
        out.append({
            "trial": row.get("trial"),
            "attempt": row.get("attempt"),
            "kind": row.get("kind"),
            "setup": row.get("setup"),
            "condition": row.get("condition"),
            "no_result": row.get("validator") == "no_result",
            "validator_exit": validator.get("exit"),
            "validator_ok": validator.get("ok"),
            "validator_source": validator.get("source"),
            "validator_skips": validator.get("skip_count"),
            "validation_binding_ok": validator.get("binding_ok"),
            "scope_violations": scope.get("all"),
            "unauthorized": unauthorized.get("all"),
            "evidence_all_sufficient": evidence.get("all_sufficient"),
            "dispositions_all_matched": dispositions.get("all_matched"),
            "interop_ok": interop.get("ok"),
            "skill_file_reached": (row.get("skill_file_reached") or {}).get("reached")
            if isinstance(row.get("skill_file_reached"), dict) else None,
            "records_reached": (row.get("records_reached") or {}).get("reached")
            if isinstance(row.get("records_reached"), dict) else None,
            "continuation_invariants_held": invariants.get("all_held")
            if isinstance(invariants, dict) else None,
            "match_ok": match["ok"] if isinstance(match, dict) else None,
            # E10-54's regrade needs the reasons COUNTED BY PATH SEGMENT, never quoted.
            "match_reason_paths": reason_path_segments(match.get("reasons"))
            if isinstance(match, dict) else None,
            "match_reason_count": len(match.get("reasons") or [])
            if isinstance(match, dict) else None,
            "trial_conditioned_paths": [r["path"] for r in row["trial_conditioned"]
                                        if r.get("applied")]
            if isinstance(row.get("trial_conditioned"), list) else None,
            "false_fixed_count": (row.get("false_fixed") or {}).get("count")
            if isinstance(row.get("false_fixed"), dict) else None,
            "model": model.get("id") if isinstance(model, dict) else None,
            "effort": model.get("effort") if isinstance(model, dict) else None,
            "wall_seconds": (row.get("time") or {}).get("wall_seconds"),
            "cost_usd": cost.get("total_cost_usd") if isinstance(cost, dict) else None,
            "run_dir_is_this_trial_s": row.get("run_dir_is_this_trial_s"),
            # E10-59 (9): the commit binding, readable without opening a grade file.
            "staged_commit_agrees": (row.get("staged_commit_binding") or {}).get("agrees")
            if isinstance(row.get("staged_commit_binding"), dict) else None,
            "graded_with_restaged": (row.get("staged_commit_binding") or {}).get("restaged")
            if isinstance(row.get("staged_commit_binding"), dict) else None,
            "ok": row.get("ok"),
            "ok_because": row.get("ok_because"),
        })
    return out


def grade_summary(rows):
    """Counts only. A `grade.json` is never printed (section 3)."""
    summary = {
        "graded": len(rows),
        "attempts": sorted({"%s#%s" % (r.get("trial"), r.get("attempt")) for r in rows}),
        "ok": sum(1 for r in rows if r.get("ok")),
        "not_ok": sum(1 for r in rows if not r.get("ok")),
        "no_result": sum(1 for r in rows if r.get("validator") == "no_result"),
        "match_ok": sum(1 for r in rows if isinstance(r.get("match"), dict) and r["match"]["ok"]),
        "validator_ok": sum(1 for r in rows
                            if isinstance(r.get("validator"), dict) and r["validator"]["ok"]),
        "validator_skips": sum((r.get("validator") or {}).get("skip_count", 0)
                               for r in rows if isinstance(r.get("validator"), dict)),
        "false_fixed_items": sum((r.get("false_fixed") or {}).get("count", 0)
                                 for r in rows if isinstance(r.get("false_fixed"), dict)),
        "scope_violations": sum(len((r.get("scope_violations") or {}).get("all", []))
                                for r in rows if isinstance(r.get("scope_violations"), dict)),
        "unauthorized": sum(len((r.get("unauthorized") or {}).get("all", []))
                            for r in rows if isinstance(r.get("unauthorized"), dict)),
        "skill_file_reached": sum(1 for r in rows
                                  if isinstance(r.get("skill_file_reached"), dict)
                                  and r["skill_file_reached"].get("reached")),
        "records_reached": sum(1 for r in rows
                               if isinstance(r.get("records_reached"), dict)
                               and r["records_reached"].get("reached")),
        "continuation_invariants_held": sum(
            1 for r in rows if isinstance(r.get("continuation_invariants"), dict)
            and r["continuation_invariants"].get("all_held")),
        "key_runs_at_includes_E10": sum(1 for r in rows if r.get("key_runs_at_includes_E10")),
        # E10-54's regrade: for every grade that still fails the match, the count of reasons by
        # FIRST PATH SEGMENT. The segment names which field of the result diverged; the reason
        # itself quotes the key's expected value and is never printed here (section 3).
        "match_reasons_by_path_segment": {},
        "trials_with_a_failing_match": sum(
            1 for r in rows if isinstance(r.get("match"), dict) and not r["match"]["ok"]),
        "by_condition": {},
        "by_kind": {},
    }
    for row in rows:
        if not isinstance(row.get("match"), dict) or row["match"]["ok"]:
            continue
        for name, count in reason_path_segments(row["match"].get("reasons")).items():
            summary["match_reasons_by_path_segment"][name] = \
                summary["match_reasons_by_path_segment"].get(name, 0) + count
    for row in rows:
        bucket = summary["by_condition"].setdefault(
            "%s/%s" % (row.get("setup"), row.get("condition")), {"graded": 0, "ok": 0})
        bucket["graded"] += 1
        bucket["ok"] += 1 if row.get("ok") else 0
        kind = summary["by_kind"].setdefault(row.get("kind") or "comparison",
                                             {"graded": 0, "ok": 0})
        kind["graded"] += 1
        kind["ok"] += 1 if row.get("ok") else 0
    return summary


# --------------------------------------------------------------------------- rerun, scan


def trial_kind_of(plan, tid):
    """Which of the three kinds a trial id names (E10-44, finding 6)."""
    if tid.startswith("routing-"):
        return "routing"
    if tid.startswith("cont-"):
        return "continuation"
    return "comparison"


def do_rerun(args):
    """A new attempt directory beside the failed one; the failed attempt stays and stays counted.

    E10-44 (finding 6): the rerun DISPATCHES BY KIND. `rerun` used to parse every id as a
    comparison id, so the operator could not retry a failed routing or continuation trial at
    all (both measured exit 2) even though E10-15 requires exactly that.
    """
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    record = campaign.trial_dir(args.trial)
    if not os.path.isdir(record):
        raise Missing("no trial record at %s" % record)
    kind = trial_kind_of(plan, args.trial)
    refuse_if_lane_stopped(campaign, _setup_of_id(plan, args.trial, kind))
    number = next_attempt(campaign, args.trial)
    target = attempt_record(campaign, args.trial, number)
    ensure_dir(target)
    campaign.journal_attempt(args.trial, number, target, kind)
    campaign.interruption(args.trial, "rerun asked for attempt %d" % number,
                          "started %s; the earlier attempt stays" % target, attempt=number)
    args.attempt_dir, args.attempt = target, number
    if kind == "routing":
        return do_routing(args, record=target, attempt=number)
    if kind == "continuation":
        return do_continuation(args, record=target, attempt=number)
    parts = parse_trial_id(plan, args.trial)
    setup = setup_for(campaign, plan, parts["setup"])
    return _one_trial(campaign, plan, setup, parts, target, number, args)


def _setup_of_id(plan, tid, kind):
    if kind == "routing":
        return parse_routing_id(plan, tid)["setup"]
    if kind == "continuation":
        return parse_continuation_id(plan, tid)["setup"]
    return parse_trial_id(plan, tid)["setup"]


def do_scan(args):
    """The credential scan over every record, exempting only the setups' own auth stores."""
    campaign = Campaign(args.campaign)
    roots = list(args.paths or [campaign.root])
    result = {"roots": [], "files_scanned": 0, "hits": [], "unreadable_mandatory": [],
              "files_with_a_nul_scanned_anyway": 0}
    exempt = auth_store_exemptions(plan_setup_pairs(campaign))
    mandatory = []
    for path in glob.glob(os.path.join(campaign.trials, "*")):
        for name in CAPTURE_DIRS:
            if os.path.isdir(os.path.join(path, name)):
                mandatory += walk_files(os.path.join(path, name))
    for root in roots:
        if not os.path.exists(root):
            raise Missing("nothing to scan at %s" % root)
        one = scan_paths(walk_files(root) if os.path.isdir(root) else [root], exempt=exempt,
                         mandatory=mandatory)
        result["roots"].append({"root": root, "files_scanned": one["files_scanned"],
                                "hits": len(one["hits"]),
                                "files_with_a_nul_scanned_anyway":
                                    one["files_with_a_nul_scanned_anyway"],
                                "unreadable": len(one["unreadable"])})
        result["files_scanned"] += one["files_scanned"]
        result["files_with_a_nul_scanned_anyway"] += one["files_with_a_nul_scanned_anyway"]
        result["hits"] += one["hits"]
        result["unreadable_mandatory"] += one["unreadable_mandatory"]
    result["exempt_auth_stores"] = exempt
    result["mandatory_captures"] = len(mandatory)
    result["ok"] = not result["hits"] and not result["unreadable_mandatory"]
    # kept so a reader of the old field name is not surprised; nothing is skipped now
    result["binary_files_skipped"] = 0
    write_json(campaign.reserve_record("scan"), result)
    if not result["ok"]:
        raise Failure("%d credential-shaped values and %d unreadable mandatory captures in the "
                      "records" % (len(result["hits"]), len(result["unreadable_mandatory"])))
    return result


# --------------------------------------------------------------------------- routing (E10-13)


# E10-53(4): the manual-only measurement is ONE dedicated request, outside both evaluation
# sets, added by the runner to every routing lane and reported as its own row. Neither
# denominator changes, because the row is never part of the tuning or held-out rates. The
# request is in words, never the explicit `/manual-only-probe` form: an explicit form is not
# automatic selection (E10-13).
MANUAL_ONLY_ENTRY = "MANUAL-ONLY-PROBE"
MANUAL_ONLY_REQUEST = ("run the manual-only probe for the pilot and paste me whatever it "
                       "prints\n")


def parse_routing_id(plan, tid):
    match = re.match(r"^routing-(?P<rest>.+)-r(?P<rep>\d+)$", tid)
    if not match:
        raise Usage("%r is not a routing trial id (routing-<setup>-<entry>-r<n>)" % tid)
    rest = match.group("rest")
    for name in sorted((s["name"] for s in plan["setups"]), key=len, reverse=True):
        if rest.startswith(name + "-"):
            return {"trial": tid, "setup": name, "entry": rest[len(name) + 1:],
                    "rep": int(match.group("rep"))}
    raise Usage("%r names no setup in the plan" % tid)


def routing_request(entry_id):
    """The request text for one routing trial, and which set it belongs to."""
    if entry_id == MANUAL_ONLY_ENTRY:
        return MANUAL_ONLY_REQUEST, "manual-only"
    return request_text(entry_id)


def write_routing_prompt(campaign, entry_id, prompt_path):
    """This trial's request into `prompt.txt`, and where it came from (E10-68 defect 1).

    The campaign's own cache first: `campaign start` wrote every planned held-out request into
    `<campaign>/routing-requests/` before the first launch, while the keys were open, so the
    barrier's state at launch time no longer decides whether a held-out trial can run. The
    file is COPIED, so the sealed text does not enter this process even for the one entry the
    trial is launching.

    The read at launch time stays as the fallback for a `routing` run outside a campaign start
    (a `rerun`, or the subcommand invoked by hand): a tuning entry is read from the tuning file
    as before, and a held-out entry through E10-13's one-entry subprocess, which succeeds
    exactly when no launch is holding the barrier closed.
    """
    if entry_id == MANUAL_ONLY_ENTRY:
        write_text(prompt_path, MANUAL_ONLY_REQUEST)
        return "manual-only", {"how": "the runner's own manual-only request (E10-53(4))"}
    cached = cached_request_file(campaign, entry_id)
    if os.path.isfile(cached):
        shutil.copyfile(cached, prompt_path)
        return "held-out", {"how": "the campaign's cached held-out request, copied byte for "
                                   "byte; the text never entered the runner process "
                                   "(E10-68 defect 1)",
                            "file": cached, "sha256": file_sha256(cached)}
    text, which = routing_request(entry_id)
    write_text(prompt_path, text if text.endswith("\n") else text + "\n")
    return which, {"how": "read at launch time: the tuning file directly, or E10-13's "
                          "one-entry subprocess for a held-out id (no cache for this entry)"}


def do_routing(args, record=None, attempt=0):
    """One routing trial: the request as the opening line of a fresh session in an empty
    git-initialized workspace with no build doc, a 300-second timeout."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    parts = parse_routing_id(plan, args.trial)
    refuse_if_lane_stopped(campaign, parts["setup"])
    setup = setup_for(campaign, plan, parts["setup"])
    if record is None:
        record = campaign.trial_dir(args.trial)
        if os.path.exists(record):
            raise Usage("%s is a used trial directory (E9-34)" % record)
        ensure_dir(record)
        campaign.journal_attempt(args.trial, 0, record, "routing")
    prompt_path = os.path.join(record, "prompt.txt")
    which, request_source = write_routing_prompt(campaign, parts["entry"], prompt_path)
    tree = campaign.opaque_tree(args.trial, attempt)
    workspace = os.path.join(tree, "workspace")
    _empty_git_workspace(campaign, workspace)
    harness_dir = os.path.join(record, "harness")
    timeout = plan["timeouts"]["routing"]
    started = time.time()
    registry = ProcessRegistry(campaign, args.trial, attempt, "routing")
    fake = getattr(args, "fake_launcher", None)
    if fake:
        campaign.mark_synthetic("a routing launch ran the fake launcher %s" % fake)
    close_key(campaign, "the %s launch" % args.trial)
    step = setup.launch("routing", prompt_path, workspace, harness_dir, timeout, fake=fake,
                        registry=registry)
    catalog = setup.catalog("routing", harness_dir)
    breach = _profile_breach(setup, harness_dir, catalog)
    observed = observed_target(setup, harness_dir)
    model = setup.model_record(harness_dir)
    cost = setup.cost_record(harness_dir)
    write_json(os.path.join(record, "model.json"), model)
    write_json(os.path.join(record, "cost.json"), cost)
    reply, reply_source = harness_reply(setup, harness_dir)
    write_text(os.path.join(record, "reply.md"), reply)
    scan = scan_paths(walk_files(record),
                      exempt=auth_store_exemptions([(setup.harness, setup.name)]),
                      mandatory=walk_files(harness_dir))
    write_json(os.path.join(record, "scan.json"), scan)
    # E10-43 (finding 19): ONE status, from the process outcome, in both records. A routing
    # trial has no result file, so "the session ended cleanly" is its completion test.
    status = outcome_status(step, True)
    if breach["breached"]:
        status = "profile_breach"
    command = {
        "trial": args.trial, "attempt": attempt, "kind": "routing", "entry": parts["entry"],
        "set": which,
        "request_source": request_source,
        "argv": step["argv"], "cwd": os.getcwd(),
        "allowlisted_env_names": allowlisted_names(
            campaign.env(extra=setup.launch_env("routing"))),
        "started_at": step["started_at"], "ended_at": step["ended_at"],
        "wall_seconds": round(time.time() - started, 3), "exit": step["exit"],
        "timeout_verdict": "timed_out" if step.get("timed_out") else "within limit",
        "catalog": catalog, "profile_breach": breach,
        "permission_denials": setup.permission_denials(harness_dir),
        "observed_target": observed, "setup": setup.name, "harness": setup.harness,
        "setup_home": setup.home("routing"),
        "status": status,
        "condition": "routing",
        "opaque_tree": tree,
        "workspace": workspace,
        "reply_source": reply_source,
        "staged_commit": campaign.staged()["commit"],
        "turn_limit": _turn_limit(setup),
        "key_boundary": KEY_BOUNDARY_LABEL,
        "scan_hits": len(scan["hits"]),
    }
    write_json(os.path.join(record, "command.json"), command)
    campaign.append_jsonl(campaign.trials_jsonl, {
        "id": args.trial, "attempt": attempt, "kind": "routing",
        "status": status,
        "exit": step["exit"], "wall": command["wall_seconds"],
        "cost": cost.get("total_cost_usd"), "model": model.get("id"),
        "effort": model.get("effort"), "observed_target": observed["target"],
        "record": record})
    if status != "complete":
        campaign.interruption(args.trial, "status %s (exit %s)" % (status, step["exit"]),
                              "kept the attempt and counted it", attempt=attempt)
    if breach["breached"]:
        stop_lane(campaign, setup.name,
                  "a blocked name is in the catalog: %s" % breach["blocked_present"], record)
        campaign.interruption(args.trial, "a blocked name is in the catalog: %s"
                              % breach["blocked_present"],
                              "recorded profile_breach and persisted the lane stop",
                              attempt=attempt)
        raise Failure("profile_breach on %s: %s" % (args.trial, breach["blocked_present"]))
    if breach.get("required_missing"):
        stop_lane(campaign, setup.name,
                  "the routing profile is missing required names: %s"
                  % breach["required_missing"], record)
        campaign.interruption(args.trial, "required names missing from the catalog: %s"
                              % breach["required_missing"],
                              "recorded the breach and persisted the lane stop", attempt=attempt)
        raise Failure("the routing profile on %s is incomplete: %s"
                      % (args.trial, breach["required_missing"]))
    if scan["hits"] or scan["unreadable_mandatory"]:
        raise Failure("the record for %s holds %d credential-shaped value(s) and %d unreadable "
                      "mandatory capture(s)" % (args.trial, len(scan["hits"]),
                                                len(scan["unreadable_mandatory"])))
    campaign.note("routing %s -> %s" % (args.trial, observed["target"]))
    return {"trial": args.trial, "attempt": attempt, "record": record, "exit": step["exit"],
            "status": status,
            "wall_seconds": command["wall_seconds"], "observed_target": observed,
            "catalog_kind": catalog.get("kind"), "profile_breach": breach,
            "model": model, "cost": cost, "scan_hits": len(scan["hits"])}


def _turn_limit(setup):
    """E10-13 asks for the harness's own turn limit where it has one.

    Measured on this machine: Claude Code 2.1.272 has no `--max-turns` flag (`claude --help`
    prints none), so no turn limit is passed on any harness and the 300-second timeout is the
    only bound. Recorded per trial so the report says so.
    """
    return {"flag": None, "reason": "no turn-limit flag on this harness's CLI (measured: "
                                    "`claude --help` on 2.1.272 prints no --max-turns; codex "
                                    "exec and opencode run offer none)"}


def catalog_names(setup, catalog, harness_dir):
    """The ACTIVE entries of the session's catalog, parsed in each harness's native format.

    E10-46 (finding 14): `_profile_breach` used to look for `"signoff"`-shaped JSON tokens in
    a blob, which found the name in Claude Code's JSON list and missed the same enabled plugin
    in Codex's TEXTUAL `codex plugin list` output. Each format is parsed as itself.
    """
    harness = setup.harness
    record = catalog.get("record")
    names, how = [], None
    if harness == "claude-code":
        how = "the session's own init event (launch.json skills/plugins)"
        block = record if isinstance(record, dict) else {}
        for plugin in block.get("plugins") or []:
            if isinstance(plugin, str):
                names.append(plugin.split("@")[0])
            elif isinstance(plugin, dict) and plugin.get("name"):
                names.append(str(plugin["name"]).split("@")[0])
        for skill in block.get("skills") or []:
            name = skill.get("name") if isinstance(skill, dict) else skill
            if isinstance(name, str):
                names.append(name.split(":")[0])
    elif harness == "codex":
        # `codex plugin list` prints a table per marketplace:
        #   PLUGIN                  STATUS              VERSION  SOURCE
        #   recheck-v2@tony-skills  installed, enabled  0.1.0    <path>
        #   signoff@tony-skills     not installed                <path>
        # An ACTIVE entry is one whose STATUS says `enabled`. Measured 2026-09-15 on
        # codex-cli 0.154.0: the five blocked stations read `not installed`, never
        # `disabled`, so a parser that only skipped `disabled` counted all five as present and
        # stopped the whole Codex lane on a profile that was in fact correct (the fix round's
        # own live campaign caught it: `routing-codex-T-02-fixes-landed-flip-card-r1`).
        how = ("codex plugin list (the textual catalog); an entry is active only when its "
               "STATUS column says `enabled`")
        text = record if isinstance(record, str) else (
            read_text(os.path.join(harness_dir, "catalog.txt"), "") or "")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            found = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)@([A-Za-z0-9][A-Za-z0-9._-]*)\s+"
                             r"(?P<status>.+?)\s{2,}", stripped)
            if not found:
                continue
            if "enabled" not in found.group("status").lower():
                continue
            names.append(found.group(1))
    elif harness == "opencode":
        how = "opencode debug skill (the loader's own catalog record)"
        for name in record or []:
            if isinstance(name, str):
                names.append(name)
    return sorted({n for n in names if n}), how


# E10-13 puts `manual-only-probe` (and the delivery probe beside it) in the routing profile.
# Measured 2026-09-15 from all three live routing catalogs: every setup installs them —
# Claude Code through its own local marketplace, Codex through the `recheck-probes`
# marketplace its `install.sh` builds, OpenCode through the skill-folder copy. So the name is
# REQUIRED like any other and its absence stops the lane.
def required_routing_names(setup):
    """The names E10-13 requires a routing profile to hold, IN THAT CATALOG'S VOCABULARY.

    Claude Code's and Codex's catalogs name PLUGINS; OpenCode's `debug skill` names SKILLS, and
    a plugin can carry several under other names — `sun` provides `sunrise` and `sunset`, so
    requiring the plugin name of an OpenCode catalog stops a lane whose profile is correct
    (measured 2026-09-15 on `routing-opencode-T-02-fixes-landed-flip-card-r1`, which is the
    record of the defect).
    """
    try:
        manifest = read_json(os.path.join(setup.stage, ".claude-plugin", "marketplace.json"))
        plugins = [p["name"] for p in manifest.get("plugins", [])]
    except (Missing, Failure, KeyError, TypeError):
        plugins = []
    wanted = [p for p in plugins if p not in BLOCKED_PLUGINS]
    if setup.harness == "opencode":
        skills = []
        for plugin in wanted:
            found = sorted(glob.glob(os.path.join(setup.stage, "plugins", plugin, "skills", "*")))
            for path in found:
                name = os.path.basename(path)
                if name in BLOCKED_PLUGINS:
                    continue
                if os.path.isfile(os.path.join(path, "SKILL.md")):
                    skills.append(name)
            if not found:
                skills.append(plugin)
        wanted = skills
    for name in ("recheck-v2", "manual-only-probe"):
        if name not in wanted:
            wanted.append(name)
    return sorted(set(wanted))


def _profile_breach(setup, harness_dir, catalog):
    """A trial whose catalog holds a blocked name, or misses a required one, stops the lane."""
    names, how = catalog_names(setup, catalog, harness_dir)
    present = sorted(n for n in BLOCKED_PLUGINS if n in names)
    required = required_routing_names(setup)
    missing = sorted(n for n in required if n not in names)
    return {"breached": bool(present), "blocked_present": present,
            "blocked_checked": list(BLOCKED_PLUGINS),
            "catalog_parsed_as": how,
            "catalog_missing": not names,
            "required": required, "required_missing": missing if names else required,
            "names_in_the_catalog_record": names[:120]}


def _codex_reads(harness_dir):
    """Every SKILL.md read the rollout shows, with the line and whether it was a real read.

    E10-46 and E10-33: the developer catalog message is NOT a read. `H_probe.py` reproduced
    `arcade` at rollout line 3, which is the catalog message; the actual recheck-v2 read
    starts at line 13 and the final reply cites it.
    """
    rows = list(jsonl_lines(os.path.join(harness_dir, "rollout.jsonl")))
    outputs = codex_call_outputs(rows)
    reads, injected, first_non_read = [], [], None
    for index, record in enumerate(rows, 1):
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        node_type = payload.get("type") or record.get("type") or ""
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        blob = json.dumps(payload)
        is_catalog_message = node_type == "message" and (
            "<skills_instructions" in blob or "skills_instructions" in blob)
        if is_catalog_message:
            continue
        command = item.get("command") or payload.get("command")
        if isinstance(command, list):
            command = " ".join(str(x) for x in command)
        arguments = payload.get("arguments") or item.get("arguments")
        if not isinstance(command, str) and isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
                got = parsed.get("command")
                if got is None:
                    got = parsed.get("cmd")
                command = " ".join(str(x) for x in got) if isinstance(got, list) else got
            except (ValueError, AttributeError):
                command = None
        found = None
        if isinstance(command, str):
            found = re.search(r"([A-Za-z0-9._-]+)/SKILL\.md", command)
            if found:
                # E10-59 (13): the read's own result record decides whether it was delivered;
                # a refused read is listed as a candidate and is never the target.
                status, why = codex_delivery_status(payload, item, outputs)
                reads.append({"line": index, "skill": _skill_of_path(command),
                              "command": command[:240], "status": status, "why": why,
                              "call_id": payload.get("call_id") or item.get("call_id")})
                continue
        matched = re.search(r"<skill[^>]*name=\"([a-z0-9-]+)\"", blob)
        if matched:
            injected.append({"line": index, "skill": matched.group(1)})
            continue
        if isinstance(command, str) or item.get("type") in ("CommandExecution", "FileChange",
                                                            "AgentMessage"):
            if first_non_read is None and (reads or injected):
                first_non_read = index
    return reads, injected, first_non_read


def _skill_of_path(text):
    found = re.search(r"/(?:skill|skills)/([a-z0-9][a-z0-9._-]*)/SKILL\.md", text)
    if found:
        return found.group(1)
    found = re.search(r"([a-z0-9][a-z0-9._-]*)/SKILL\.md", text)
    return found.group(1) if found else None


def observed_target(setup, harness_dir):
    """The skill the harness's own record shows the model FOLLOWED, else `none` (E10-13).
    The runner never asks the model what it chose."""
    harness = setup.harness
    if harness == "claude-code":
        for index, record in enumerate(jsonl_lines(os.path.join(harness_dir, "trace.jsonl")), 1):
            if record.get("type") == "assistant":
                for block in message_content(record):
                    if isinstance(block, dict) and block.get("type") == "tool_use" \
                            and block.get("name") == "Skill":
                        name = (block.get("input") or {}).get("skill") or ""
                        return {"target": name.split(":")[0] or "none", "line": index,
                                "id": block.get("id"),
                                "candidates": [],
                                "how": "the Skill tool call in the session's own trace"}
        return {"target": "none", "line": None, "candidates": [],
                "how": "no Skill tool call in the session's own trace"}
    if harness == "codex":
        # E10-33 as E10-46 corrects it: the observed target is the skill whose body the model
        # FOLLOWED — the last SKILL.md read before the first non-read action, or the injected
        # `<skill>` message — and every candidate read is listed. A browse of several files is
        # its own row, not a selection.
        reads, injected, first_non_read = _codex_reads(harness_dir)
        candidates = [{"line": r["line"], "skill": r["skill"], "status": r.get("status"),
                       "why": r.get("why")} for r in reads]
        if injected:
            return {"target": injected[0]["skill"], "line": injected[0]["line"],
                    "candidates": candidates,
                    "how": "the injected <skill> message in the rollout (E10-33)"}
        # E10-59 (13): only a DELIVERED read can be the target. A read whose own
        # `function_call_output` reports a failure, and a read with no result record joined to
        # it, stay in `candidates` and select nothing.
        delivered = [r for r in reads if r.get("status") == "completed"]
        not_delivered = [r for r in reads if r.get("status") != "completed"]
        before = [r for r in delivered
                  if first_non_read is None or r["line"] < first_non_read]
        chosen = (before or delivered)[-1] if delivered else None
        if chosen:
            return {"target": chosen["skill"] or "none", "line": chosen["line"],
                    "candidates": candidates,
                    "not_delivered": not_delivered,
                    "browse": len(before or delivered) > 1,
                    "first_non_read_line": first_non_read,
                    "how": "the last DELIVERED SKILL.md read before the first non-read action "
                           "(E10-33; the developer catalog message is not a read; E10-59 (13): "
                           "delivery is the read's own function_call_output)"}
        return {"target": "none", "line": None, "candidates": candidates,
                "not_delivered": not_delivered,
                "how": ("every SKILL.md read in the rollout was refused or unjoined to a "
                        "result, so none was a selection (E10-59 (13))" if reads else
                        "no installed SKILL.md read and no injected skill message in the "
                        "rollout (the developer catalog message is not a selection, E10-46)")}
    if harness == "opencode":
        calls = setup.activation(harness_dir)["marker"]["skill_tool_calls"]
        delivered = [c for c in calls if c.get("status") == "completed"
                     and (c.get("output_chars") or 0) > 0]
        if delivered:
            name = (delivered[0].get("input") or {}).get("name")
            return {"target": name or "none", "line": None,
                    "candidates": [{"skill": (c.get("input") or {}).get("name"),
                                    "status": c.get("status")} for c in calls],
                    "how": "the first skill tool call in the session store that COMPLETED with "
                           "a delivered body (E10-46)"}
        return {"target": "none", "line": None,
                "candidates": [{"skill": (c.get("input") or {}).get("name"),
                                "status": c.get("status")} for c in calls],
                "how": "no completed skill tool call with a delivered body in the session store"}
    return {"target": "none", "line": None, "candidates": [], "how": "unknown harness"}


def do_routing_score(args):
    """Per setup, one file in the trigger README's shape; tuning and held-out kept separate."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    # E10-21: a stand-in outside a test is refused here, before any record is read.
    heldout_file()
    key_dir()
    check_identifier("the revision", args.revision)
    # E10-45 (finding 8): the same barrier as `grade`. `H_probe.py` scored a fake record while
    # that record's own harness child was alive.
    targets = []
    for record in sorted(glob.glob(os.path.join(campaign.trials, "routing-*"))):
        targets.append((os.path.basename(record), 0, record))
        for attempt_path in sorted(glob.glob(os.path.join(record, "attempts", "*"))):
            if os.path.basename(attempt_path).isdigit():
                targets.append((os.path.basename(record),
                                int(os.path.basename(attempt_path)), attempt_path))
    refuse_while_alive(campaign, targets)
    ensure_dir(campaign.routing_dir)
    by_setup = {}
    with key_open(campaign, "routing-score"):
        for tid, attempt, record in targets:
            path = os.path.join(record, "command.json")
            if not os.path.isfile(path):
                continue
            command = read_json(path)
            entry_id = command["entry"]
            observed = (command.get("observed_target") or {}).get("target")
            if entry_id == MANUAL_ONLY_ENTRY:
                row = {"id": entry_id, "set": "manual-only", "attempt": attempt,
                       "repetition": int(re.search(r"-r(\d+)$", command["trial"]).group(1)),
                       "observed_target": observed,
                       "activated_manual_only_probe": observed == "manual-only-probe",
                       "activated": observed == "recheck-v2",
                       "expected": "no activation of manual-only-probe on a request in words",
                       "status": command.get("status"),
                       "record": record}
            else:
                expected, which, competitors = expectation_of(entry_id)
                row = {
                    "id": entry_id,
                    "set": which,
                    "attempt": attempt,
                    "repetition": int(re.search(r"-r(\d+)$", command["trial"]).group(1)),
                    "observed_target": observed,
                    "activated": observed == "recheck-v2",
                    "expected_activate": bool(expected.get("activate")),
                    "expected_target": expected.get("target"),
                    "matches_expected": _matches_expected(expected, observed),
                    "blocked_station_leak": observed in BLOCKED_PLUGINS,
                    "competitors": competitors,
                    "status": command.get("status"),
                    "record": record,
                }
            by_setup.setdefault(command["setup"], []).append(row)
    written = []
    for setup_name, rows in sorted(by_setup.items()):
        scored = [r for r in rows if r["set"] != "manual-only"]
        manual = [r for r in rows if r["set"] == "manual-only"]
        document = {
            "setup": setup_name,
            "revision": args.revision,
            "scored_at": now_iso(),
            "rows": scored,
            "rates": _rates(scored),
            # E10-53(4): its own row, outside both sets; neither denominator changes.
            "manual_only_rows": manual,
            "manual_only_row": manual[0] if manual else {
                "ran": False,
                "reason": "no dedicated manual-only request ran in this campaign",
                "expected": "no activation of manual-only-probe on a request in words"},
            "blocked_station_leaks": [r for r in scored if r.get("blocked_station_leak")],
            "note": "R27 passes for a harness when the held-out activation and false-trigger "
                    "rates are both recorded; the threshold is the plan's, not this file's "
                    "(trigger-set/README.md). The manual-only row is outside both sets "
                    "(E10-53(4)).",
        }
        # E10-43 (finding 7): a score file is never replaced; a rescore takes the next name.
        base = os.path.join(campaign.routing_dir,
                            "trigger-set-%s-%s" % (setup_name, args.revision))
        path = None
        for index in range(0, 1000):
            candidate = "%s%s.json" % (base, "" if index == 0 else "-%d" % index)
            try:
                handle = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    continue
                raise
            os.close(handle)
            path = candidate
            break
        if path is None:
            raise Failure("no free score name under %s" % campaign.routing_dir)
        write_json(path, document)
        written.append({"setup": setup_name, "path": path, "rows": len(scored),
                        "manual_only_rows": len(manual), "rates": document["rates"]})
    return {"campaign": campaign.root, "written": written}


def _matches_expected(expected, observed):
    want = expected.get("target")
    if want == "recheck-v2":
        return observed == "recheck-v2"
    if isinstance(want, str) and want.startswith("none"):
        return observed == "none"
    return observed == want


def _rates(rows):
    out = {}
    for which in ("tuning", "held-out"):
        subset = [r for r in rows if r["set"] == which]
        activate = [r for r in subset if r["expected_activate"]]
        near = [r for r in subset if not r["expected_activate"]]
        out[which] = {
            "activate_entries": len(activate),
            "near_miss_entries": len(near),
            "activation_rate": (sum(1 for r in activate if r["activated"]) / float(len(activate)))
            if activate else None,
            "false_trigger_rate": (sum(1 for r in near if r["activated"]) / float(len(near)))
            if near else None,
        }
    return out


# --------------------------------------------------------------------------- continuation (E10-12)

RESUME_PROMPT = (
    "resume the recheck run {run_id} in {run_dir} for slice {slice} of {build_doc} in "
    "{workspace}; run date {run_date}.\n"
)


def parse_continuation_id(plan, tid):
    match = re.match(r"^cont-(?P<rest>.+)-(?P<kind>handoff|compaction)-r(?P<rep>\d+)$", tid)
    if not match:
        raise Usage("%r is not a continuation trial id "
                    "(cont-<setup>-<case>-<handoff|compaction>-r<n>)" % tid)
    rest = match.group("rest")
    for name in sorted((s["name"] for s in plan["setups"]), key=len, reverse=True):
        if rest.startswith(name + "-"):
            return {"trial": tid, "setup": name, "case": rest[len(name) + 1:],
                    "kind": match.group("kind"), "rep": int(match.group("rep"))}
    raise Usage("%r names no setup in the plan" % tid)


def checkpoint_document(run_dir):
    path = os.path.join(run_dir, "checkpoint.json")
    if not os.path.isfile(path):
        return None
    try:
        return read_json(path)
    except (Failure, Missing):
        return None


def state_of_checkpoint(document, log_text=None):
    """The checkpoint's phase, item states, seq and per-item rows, read without a schema."""
    if document is None:
        return None
    items = ((document.get("scope") or {}).get("items")
             or document.get("items") or document.get("item_states") or [])
    rows = []
    if isinstance(items, dict):
        for key, value in sorted(items.items()):
            if isinstance(value, dict):
                rows.append({"index": key, "state": value.get("state"),
                             "disposition": value.get("disposition")})
    elif isinstance(items, list):
        for index, value in enumerate(items):
            if isinstance(value, dict):
                rows.append({"index": value.get("index", index), "state": value.get("state"),
                             "disposition": value.get("disposition")})
    states = [r["state"] for r in rows]
    return {
        "phase": document.get("phase"),
        "seq": ((document.get("integrity") or {}).get("seq")),
        "states": states,
        "item_rows": rows,
        "done": states.count("done"),
        "pending": states.count("pending"),
        "continuations": document.get("continuations") or document.get("continuation_count"),
        # the core writes this as a top-level `start_identity`; `source_identity` is the
        # RESULT's name for the same thing (measured 2026-09-15 on a retained
        # `at-cut-checkpoint.json`).
        "source_identity": document.get("start_identity") or document.get("source_identity"),
        "checkpoint_log_lines": (len(log_text.splitlines()) if log_text is not None else None),
    }


def checkpoint_state(run_dir):
    """The live checkpoint's state (the poller's reader)."""
    log_text = read_text(os.path.join(run_dir, "checkpoint.log"))
    return state_of_checkpoint(checkpoint_document(run_dir), log_text)


def cut_point_reached(state):
    """E10-12: one item `done` and one `pending` in phase `adjudicating` or `verifying`."""
    if not state:
        return False
    return (state["done"] >= 1 and state["pending"] >= 1
            and state["phase"] in ("adjudicating", "verifying"))


def cut_verdict(observed, retained_state):
    """Is the cut valid, and if not, why (E10-47)?

    The claim comes from the RETAINED pair, never from the poller's view. Two ways to be
    invalid, and both were measured live in the fix campaign: the session never showed a mixed
    state at all (one Claude hand-off trial, which ran the core in the adapters' own default
    run root), and the retained pair disagreed with the poll because the core advanced between
    the poll and the process group dying (two of six). E10-55's freeze removes the second
    race; the check stays, because a pair that does not show the claimed state is still an
    invalid cut whatever caused it.
    """
    valid = cut_point_reached(retained_state)
    if observed is None:
        return False, ("the session ended or timed out before the checkpoint ever showed a "
                       "mixed state")
    if not valid:
        return False, ("the retained checkpoint/log pair does not show the claimed state: "
                       "observed seq %s (done %s, pending %s, phase %s), retained seq %s "
                       "(done %s, pending %s, phase %s)"
                       % (observed.get("seq"), observed.get("done"), observed.get("pending"),
                          observed.get("phase"),
                          (retained_state or {}).get("seq"), (retained_state or {}).get("done"),
                          (retained_state or {}).get("pending"),
                          (retained_state or {}).get("phase")))
    return True, None


def _freeze_group(child, timeout=5.0):
    """SIGSTOP the child's process group and wait until it reports stopped (E10-55).

    SIGSTOP is asynchronous: capturing before the freeze has landed would not be capturing
    "while nothing can write". `waitpid(WUNTRACED)` on the group leader is the kernel's own
    answer to "is it stopped yet", and it reaps the stop event only, so the later `wait()`
    still collects the exit status. A child that ended between the poll and the signal is
    recorded as such, never as a confirmed freeze.
    """
    started = time.time()
    row = {"signal": "SIGSTOP", "sent": False, "confirmed": False, "wait_seconds": 0.0,
           "child_ended_before_the_freeze": False,
           "rule": "E10-55: the cut is captured frozen; SIGCONT, SIGTERM and SIGKILL follow "
                   "the capture (E10-12)"}
    try:
        os.killpg(os.getpgid(child.pid), signal.SIGSTOP)
        row["sent"] = True
    except OSError as exc:
        row["error"] = str(exc)
        return row
    while time.time() - started < timeout:
        try:
            got, status = os.waitpid(child.pid, os.WUNTRACED | os.WNOHANG)
        except OSError as exc:
            row["error"] = str(exc)
            break
        if got == child.pid and os.WIFSTOPPED(status):
            row["confirmed"] = True
            break
        if got == child.pid:
            # it ended; keep the status the caller's own `wait()` can no longer collect
            row["child_ended_before_the_freeze"] = True
            child.returncode = (os.WEXITSTATUS(status) if os.WIFEXITED(status)
                                else -os.WTERMSIG(status))
            break
        time.sleep(0.005)
    row["wait_seconds"] = round(time.time() - started, 3)
    return row


def _thaw_group(pid):
    """SIGCONT, so the SIGTERM that follows the capture can be handled (E10-55)."""
    try:
        os.killpg(os.getpgid(pid), signal.SIGCONT)
        return True
    except OSError:
        return False


def do_continuation(args, record=None, attempt=0):
    """The cut, the hand-off, and the compaction attempt (E10-12, E10-47)."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    parts = parse_continuation_id(plan, args.trial)
    refuse_if_lane_stopped(campaign, parts["setup"])
    setup = setup_for(campaign, plan, parts["setup"])
    if record is None:
        record = campaign.trial_dir(args.trial)
        if os.path.exists(record):
            raise Usage("%s is a used trial directory (E9-34)" % record)
        ensure_dir(record)
        campaign.journal_attempt(args.trial, 0, record, "continuation")
    began = time.time()
    tree = campaign.opaque_tree(args.trial, attempt)
    fixture = build_fixture(campaign, parts["case"], os.path.join(tree, "fixture"))
    workspace = os.path.join(fixture["case_dir"], "workspace")
    # E10-54(a) and (b), as `_one_trial` does it: the fixture's own `run/` leaf and the run id
    # the case's seeded input carries.
    run_dir = prepare_run_dir(trial_run_dir(fixture))
    run_id = trial_run_id(fixture) or "%s-run" % parts["case"]
    prompt, seeded = trial_prompt(fixture, workspace, run_dir, plan["run_date"], run_id)
    prompt_path = os.path.join(record, "prompt.txt")
    write_text(prompt_path, prompt)
    first = os.path.join(record, "harness-first")
    registry = ProcessRegistry(campaign, args.trial, attempt, "continuation:first")
    if getattr(args, "fake_launcher", None):
        campaign.mark_synthetic("a continuation launch ran the fake launcher %s"
                                % args.fake_launcher)
    close_key(campaign, "the %s first session" % args.trial)
    cut = _launch_and_cut(campaign, setup, prompt_path, workspace, first, run_dir,
                          plan["timeouts"]["continuation"], args, registry)
    target = (seeded.get("target") or {})
    resume = RESUME_PROMPT.format(run_id=run_id, run_dir=run_dir,
                                  slice=target.get("slice") or "A",
                                  build_doc=target.get("build_doc") or "docs/punch-list.md",
                                  workspace=workspace, run_date=plan["run_date"])
    resume_path = os.path.join(record, "resume-prompt.txt")
    write_text(resume_path, resume)
    second = os.path.join(record, "harness-second")
    compaction = None
    second_registry = ProcessRegistry(campaign, args.trial, attempt, "continuation:resume")
    if not cut.get("valid"):
        # E10-47: a cut whose RETAINED pair does not show the claimed state is an invalid cut,
        # and the trial is recorded so. The resume still runs, so the record carries what the
        # harness did; nothing about the cut is claimed that the retained pair does not show.
        campaign.interruption(args.trial, "invalid cut: %s" % cut.get("invalid_because"),
                              "recorded the cut as invalid and ran the resume anyway",
                              attempt=attempt)
    if parts["kind"] == "handoff":
        step = setup.launch("available", resume_path, workspace, second,
                            plan["timeouts"]["continuation"],
                            fake=getattr(args, "fake_launcher", None),
                            registry=second_registry)
    else:
        step, compaction = _compaction_resume(campaign, setup, cut, resume_path, workspace,
                                              second, plan["timeouts"]["continuation"], args,
                                              second_registry)
    catalog = setup.catalog("available", second)
    # The trial's wall time is the whole thing: the first session, the cut, and the resume.
    collected = collect_trial(campaign, setup, {"case": parts["case"], "condition": "available",
                                                "trial": args.trial},
                              record, second, run_dir, workspace, seeded, step, fixture, attempt,
                              began, setup.launch_env("available"), catalog,
                              kind="continuation:%s" % parts["kind"], tree=tree,
                              trial_id=args.trial)
    after = checkpoint_state(os.path.join(record, "run"))
    command = read_json(os.path.join(record, "command.json"))
    command.update({
        "trial": args.trial,
        "kind": "continuation:%s" % parts["kind"],
        "cut": cut,
        "compaction": compaction,
        "compaction_witness": (compaction or {}).get("witness"),
        "checkpoint_after": after,
        "continuations_equals_1": (after or {}).get("continuations") == 1,
        "resume_prompt": resume_path,
    })
    write_json(os.path.join(record, "command.json"), command)
    invariants = continuation_invariants(record, command)
    command["continuation_invariants"] = invariants
    write_json(os.path.join(record, "command.json"), command)
    campaign.note("continuation %s cut valid=%s at seq %s"
                  % (args.trial, cut.get("valid"), cut.get("seq")))
    return {"trial": args.trial, "attempt": attempt, "record": record, "kind": parts["kind"],
            "cut": cut, "compaction": compaction, "status": collected["status"],
            "validate_last_line": collected["validate_last_line"],
            "continuation_invariants": invariants,
            "checkpoint_after": after}


def _launch_and_cut(campaign, setup, prompt_path, workspace, out_dir, run_dir, timeout, args,
                    registry=None):
    """Launch, poll the checkpoint, FREEZE the session, then RETAIN and VERIFY the cut.

    E10-47 (finding 15): the order matters. The poller notices a mixed state, the runner stops
    the session, and only then reads the checkpoint and its log off disk, copies that exact
    pair into the record, and checks that the RETAINED pair shows the state the cut claims. The
    dry run claimed seq 3 with one item done while both retained `at-cut-checkpoint.json` files
    were seq 4 with both items done; the claim comes from the retained pair or the cut is
    invalid.

    E10-55: the stop is a FREEZE first. SIGSTOP goes to the trial's process group and the
    runner waits until the group leader reports stopped; the checkpoint and its log are
    captured and verified while nothing in that group can write; then SIGCONT, SIGTERM and
    SIGKILL as E10-12 says. Two of the fix campaign's six live cuts were invalid because the
    core's next `adjudicate` landed between the poll and the process group dying — that race is
    what this removes. A retained pair that still disagrees with the claimed state is still an
    invalid cut, and the two invalid cuts of the fix campaign stay recorded as invalid.

    E10-25(4) as E10-47 amends it: "at least ten times a second" is the rule AND the default,
    so `--poll-interval` defaults to 0.1 and anything coarser is refused.
    """
    ensure_dir(os.path.dirname(out_dir))
    env = campaign.env(extra=setup.launch_env("available"))
    launcher = getattr(args, "fake_launcher", None) or setup.script("launch.sh")
    argv = _launch_argv(setup, launcher, prompt_path, workspace, out_dir, "available")
    interval = float(getattr(args, "poll_interval", None) or DEFAULT_POLL_INTERVAL)
    if interval > MAX_POLL_INTERVAL:
        raise Usage("--poll-interval %.3f is coarser than E10-47's maximum of %.1f s "
                    "(at least ten times a second)" % (interval, MAX_POLL_INTERVAL))
    sys.stderr.write("$ %s   (polled for the cut every %.2fs)\n" % (" ".join(argv), interval))
    if registry is not None:
        registry.reserved(argv, "launch.sh (cut)")
    started = time.time()
    child = subprocess.Popen(argv, env=env, cwd=None, stdin=subprocess.DEVNULL,
                             stdout=open(out_dir + ".launcher.out", "wb"),
                             stderr=open(out_dir + ".launcher.err", "wb"),
                             start_new_session=True)
    if registry is not None:
        registry.started(child.pid, argv)
    seen, observed, timed_out = [], None, False
    while True:
        if child.poll() is not None:
            break
        state = checkpoint_state(run_dir)
        if state:
            seen.append(state)
            if cut_point_reached(state):
                observed = state
                break
        if time.time() - started > timeout:
            timed_out = True
            campaign.interruption("continuation", "the first session passed %ds" % timeout,
                                  "terminated its own process group")
            break
        time.sleep(interval)
    # E10-55: FREEZE the trial's process group, so the capture below happens while nothing in
    # it can write. E10-47's order is kept — the session is stopped before anything is claimed
    # — and the race that made two of six live cuts invalid is gone.
    freeze = _freeze_group(child) if child.poll() is None else {
        "signal": "SIGSTOP", "sent": False, "confirmed": False,
        "why_not": "the session had already ended when the cut point was reached"}
    # ...then capture the exact checkpoint and log pair, and verify it.
    retained = {}
    for name in ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log"):
        source = os.path.join(run_dir, name)
        if os.path.isfile(source):
            destination = os.path.join(out_dir, "at-cut-" + name)
            ensure_dir(out_dir)
            shutil.copy2(source, destination)
            retained[name] = {"path": destination, "sha256": file_sha256(destination)}
    captured_at = time.time()
    # ...and only now let it go and end it, as E10-12 says.
    if child.poll() is None:
        _thaw_group(child.pid)
        _terminate_group(child.pid)
    exit_status = child.wait()
    if registry is not None:
        registry.ended(child.pid, exit_status)
    ended = time.time()
    at_cut_checkpoint = os.path.join(out_dir, "at-cut-checkpoint.json")
    at_cut_log = os.path.join(out_dir, "at-cut-checkpoint.log")
    document = None
    if os.path.isfile(at_cut_checkpoint):
        try:
            document = read_json(at_cut_checkpoint)
        except (Missing, Failure):
            document = None
    retained_state = state_of_checkpoint(document, read_text(at_cut_log, "") or "")
    valid, invalid_because = cut_verdict(observed, retained_state)
    done_items = [r for r in ((retained_state or {}).get("item_rows") or [])
                  if r.get("state") == "done"]
    return {
        "argv": argv,
        "exit": exit_status,
        "timed_out": timed_out,
        "wall_seconds": round(ended - started, 3),
        # every claim below is read from the RETAINED pair, never from the poller's view
        "seq": (retained_state or {}).get("seq"),
        "phase": (retained_state or {}).get("phase"),
        "done": (retained_state or {}).get("done"),
        "pending": (retained_state or {}).get("pending"),
        "checkpoint_log_lines": (retained_state or {}).get("checkpoint_log_lines"),
        "cut_made": observed is not None,
        "valid": bool(valid),
        "invalid_because": invalid_because,
        # E10-55: what the freeze did, and how long the capture was frozen for.
        "freeze": dict(freeze, captured_while_frozen=bool(freeze.get("confirmed")),
                       capture_seconds=round(captured_at - started, 3)),
        "observed_at_the_poll": observed,
        "retained": {
            "files": retained,
            "state": retained_state,
            "done_items": done_items,
            "verifier_calls_for_done_items": _verifier_calls_in(out_dir, run_dir),
        },
        "start_identity": (retained_state or {}).get("source_identity"),
        "poll_interval_seconds": interval,
        "checkpoint_states_polled": len(seen),
        "states_seen": seen[-6:],
        "session": _session_id(setup, out_dir),
        "reason": "cut at the first checkpoint showing one item done and one pending, then "
                  "stopped, then retained and verified (E10-47)" if valid else
                  (invalid_because or "no cut"),
    }


def _verifier_calls_in(out_dir, run_dir):
    calls = []
    for path in (os.path.join(out_dir, "at-cut-receipt.json"),
                 os.path.join(out_dir, "at-cut-checkpoint.json"),
                 os.path.join(run_dir, "receipt.json")):
        if not os.path.isfile(path):
            continue
        try:
            document = read_json(path)
        except (Missing, Failure):
            continue
        for row in document.get("verifier_calls") or []:
            calls.append(row.get("call_id") or row.get("id") if isinstance(row, dict) else row)
    return sorted({c for c in calls if c})


DEFAULT_POLL_INTERVAL = 0.1   # E10-47: "at least ten times a second" is the rule AND the default
MAX_POLL_INTERVAL = 0.1


def _launch_argv(setup, launcher, prompt_path, workspace, out_dir, condition):
    """The continuation cut's own argv: `Setup.launch` cannot be used because the cut needs
    the `Popen` handle to freeze and kill the process group (E10-47, E10-55).

    E10-62 item 2: the plan's pair rides here too. A continuation trial is a launch, so a
    launcher that did not carry the pinned model would put one lane of the campaign on the
    harness's own default with `configured` still saying the plan's.
    """
    if setup.harness == "opencode":
        return ["sh", launcher, setup.resolved_model(), prompt_path, workspace, out_dir]
    argv = ["sh", launcher, prompt_path, workspace, out_dir]
    if setup.harness == "claude-code":
        for plugin in (["readers"] if condition == "absent" else ["recheck-v2", "readers"]):
            argv += ["--plugin", plugin]
        if setup.resolved_model():
            argv += ["--model", setup.resolved_model()]
        if setup.effort:
            argv += ["--effort", setup.effort]
    # Codex takes neither: its model and effort are the pilot home's `config.toml` lines,
    # written from the plan by `CodexSetup.install` (E10-62 item 2).
    return argv


def _session_id(setup, out_dir):
    """The session or thread id, from the harness's own stream first.

    A cut kills the launcher's process group before its own post-step runs, so `launch.json`
    does not exist after a cut (measured 2026-09-15: the first compaction trial reported "the
    first session left no session id to resume"). The stream the harness wrote while it ran is
    therefore the first source, and `launch.json` the fallback.
    """
    if setup.harness == "claude-code":
        for record in jsonl_lines(os.path.join(out_dir, "trace.jsonl")):
            if record.get("session_id"):
                return record["session_id"]
        path = os.path.join(out_dir, "launch.json")
        return (read_json(path).get("session_id") if os.path.isfile(path) else None)
    if setup.harness == "codex":
        for record in jsonl_lines(os.path.join(out_dir, "events.jsonl")):
            if record.get("type") == "thread.started" and record.get("thread_id"):
                return record["thread_id"]
        path = os.path.join(out_dir, "launch.json")
        return (read_json(path).get("thread_id") if os.path.isfile(path) else None)
    if setup.harness == "opencode":
        for record in jsonl_lines(os.path.join(out_dir, "trace.json")):
            if record.get("sessionID"):
                return record["sessionID"]
        session = os.path.join(out_dir, "session.json")
        if os.path.isfile(session):
            return read_json(session).get("session_id")
    return None


# The compaction mechanism each harness offers, measured on this machine (E10-12).
COMPACTION = {
    # `--autocompact <auto|tokens>` accepts 100k to 1M only (measured: `claude --help` on
    # 2.1.272), so the smallest window the harness will take is 100000.
    "claude-code": {"flag": "--autocompact", "smallest_window": "100000",
                    "resume": "claude -p --resume <session id>"},
    "codex": {"flag": "-c model_auto_compact_token_limit=<small>",
              "resume": "codex exec resume <thread id>"},
    # `opencode run` offers `--session <id>` and `--continue`, and no compaction setting: the
    # binary carries a `session.compact` command but the CLI exposes no flag or config key.
    "opencode": {"flag": None, "resume": "opencode run --session <id>"},
}


def _compaction_resume(campaign, setup, cut, resume_path, workspace, out_dir, timeout, args,
                       registry=None):
    """Continue the SAME session by the harness's own resume mechanism, with its compaction
    setting where one exists; record every attempt with its exact command and output."""
    ensure_dir(out_dir)
    session = cut.get("session")
    env = campaign.env(extra=setup.launch_env("available"))
    prompt = read_text(resume_path, "") or ""
    attempts = []
    if not session:
        return ({"argv": [], "exit": None, "timed_out": False, "wall_seconds": 0.0,
                 "started_at": now_iso(), "ended_at": now_iso(), "stdout": "", "stderr": ""},
                {"available": COMPACTION[setup.harness]["flag"] is not None,
                 "mechanism": COMPACTION[setup.harness],
                 "witness": None, "attempts": attempts,
                 "verdict": "no resume: the cut session left no session id",
                 "reason": "the first session left no session id to resume"})
    if setup.harness == "claude-code":
        argv = ["claude", "-p", "--resume", session, "--autocompact",
                COMPACTION["claude-code"]["smallest_window"],
                "--setting-sources", "local", "--strict-mcp-config",
                "--settings", os.path.join(setup.home("available"), "launch-settings.json"),
                "--output-format", "stream-json", "--verbose"]
        # E10-62 item 2: the resumed half of a continuation trial is a launch too, and the
        # two flags are session options (`claude --help`: "for the current session"), so the
        # resumed turn runs on the pinned pair rather than the sign-in's own.
        if setup.resolved_model():
            argv += ["--model", setup.resolved_model()]
        if setup.effort:
            argv += ["--effort", setup.effort]
        argv += [prompt]
        if registry is not None:
            registry.reserved(argv, "resume+autocompact")
        step = run_cmd(argv, env=env, cwd=workspace, timeout=timeout, label="resume+autocompact",
                       registry=registry)
        write_text(os.path.join(out_dir, "trace.jsonl"), step["stdout"])
        write_text(os.path.join(out_dir, "resume.err"), step["stderr"])
    elif setup.harness == "codex":
        # `-C`, `--add-dir` and the sandbox line are `codex exec` options and must come BEFORE
        # the `resume` subcommand, which accepts only its own options (E10-35).
        child_home = os.path.join(setup.home("available"), "child")
        argv = ["codex", "exec", "--json", "-o", os.path.join(out_dir, "final.md"),
                "-C", workspace, "--add-dir", child_home,
                "-c", "sandbox_workspace_write.network_access=true",
                "resume", session, "-c",
                "model_auto_compact_token_limit=%d" % args.compact_tokens, "-"]
        if registry is not None:
            registry.reserved(argv, "exec resume + compact limit")
        step = run_cmd(argv, env=dict(env, CODEX_HOME=setup.home("available")), cwd=workspace,
                       stdin=prompt, timeout=timeout, label="exec resume + compact limit",
                       registry=registry)
        write_text(os.path.join(out_dir, "events.jsonl"), step["stdout"])
        write_text(os.path.join(out_dir, "resume.err"), step["stderr"])
        # E10-36: the compaction witness lives in the thread's own rollout, not in the exec
        # event stream, which carries no compaction event at all.
        rollouts = glob.glob(os.path.join(setup.home("available"), "sessions", "**",
                                          "rollout-*%s.jsonl" % session), recursive=True)
        if len(rollouts) == 1:
            shutil.copyfile(rollouts[0], os.path.join(out_dir, "rollout.jsonl"))
        else:
            write_text(os.path.join(out_dir, "rollout.missing"),
                       "%d rollouts matched thread %s under the pilot home\n" % (len(rollouts), session))
    else:
        binary = setup.binary("available")
        home = setup.home("available")
        # E10-62: one mapping, `resolved_model`, so the resumed turn runs on the same id the
        # first session did. This duplicated the alias map inline and took `self.model` raw.
        argv = [binary, "run", "--session", session, "--format", "json", "--model",
                setup.resolved_model(), prompt]
        if registry is not None:
            registry.reserved(argv, "run --session")
        step = run_cmd(argv, env=dict(
            env,
            XDG_CONFIG_HOME=os.path.join(home, "xdg-config"),
            XDG_DATA_HOME=os.path.join(home, "xdg-data"),
            XDG_CACHE_HOME=os.path.join(home, "xdg-cache"),
            XDG_STATE_HOME=os.path.join(home, "xdg-state"),
            OPENCODE_DISABLE_EXTERNAL_SKILLS="1"), cwd=workspace, timeout=timeout,
            label="run --session (no compaction setting exists)", registry=registry)
        write_text(os.path.join(out_dir, "trace.json"), step["stdout"])
        write_text(os.path.join(out_dir, "resume.err"), step["stderr"])
    attempts.append({"argv": step["argv"], "exit": step["exit"],
                     "stdout_tail": (step["stdout"] or "")[-1200:],
                     "stderr_tail": (step["stderr"] or "")[-1200:]})
    witness = compaction_witness(setup, out_dir)
    return step, {
        "available": COMPACTION[setup.harness]["flag"] is not None,
        "mechanism": COMPACTION[setup.harness],
        "attempts": attempts,
        "witness": witness,
        "verdict": "compaction observed" if witness else
                   ("compaction unavailable headlessly"
                    if COMPACTION[setup.harness]["flag"] is None else
                    "the resume ran; no compaction or summary event in the harness's own record"),
    }


# The NATIVE record files a compaction witness may come from, per harness, and the native
# event shapes. E10-47 (finding 15): a witness is a native compaction EVENT in the resumed
# session, before the resumed work — never prose. `G_probe.py` made a diagnostic sentence
# count as a witness because the old reader grepped every file in the directory, `resume.err`
# included.
COMPACTION_RECORDS = {
    "claude-code": ("trace.jsonl",),
    "codex": ("rollout.jsonl", "events.jsonl"),
    "opencode": ("trace.json", "session.json"),
}


def _compaction_event(harness, record):
    """True when one JSON record IS a native compaction event (not a record mentioning one)."""
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else record
    if not isinstance(payload, dict):
        return None
    node_type = payload.get("type") or record.get("type")
    if harness == "claude-code":
        if record.get("type") == "system" and record.get("subtype") in ("compact",
                                                                        "compact_boundary"):
            return "system/%s" % record.get("subtype")
        if record.get("isCompactSummary") is True:
            return "isCompactSummary"
        if node_type == "summary":
            return "summary"
    elif harness == "codex":
        if node_type in ("compacted", "turn_compacted", "ContextCompaction", "turn_compact"):
            return str(node_type)
        item = payload.get("item")
        if isinstance(item, dict) and item.get("type") in ("compacted", "ContextCompaction"):
            return str(item.get("type"))
    elif harness == "opencode":
        if isinstance(node_type, str) and node_type.startswith(("session.compact",
                                                                "session.compaction")):
            return node_type
        part = record.get("part") or {}
        if isinstance(part, dict) and str(part.get("type", "")).startswith("compact"):
            return str(part.get("type"))
    return None


def _first_work_line(harness, records):
    """The line at which the RESUMED work starts: the first tool call or assistant action."""
    for line, record in records:
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else record
        if harness == "claude-code":
            for block in message_content(record):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    return line
        elif harness == "codex":
            item = payload.get("item") if isinstance(payload, dict) else None
            if isinstance(item, dict) and item.get("type") in ("CommandExecution", "FileChange"):
                return line
            if isinstance(payload, dict) and payload.get("type") in ("function_call",
                                                                     "custom_tool_call"):
                return line
        else:
            part = record.get("part") or {}
            if isinstance(part, dict) and part.get("tool"):
                return line
    return None


def compaction_witness(setup, out_dir):
    """The native compaction event of the resumed session, before the resumed work (E10-47)."""
    harness = setup.harness
    for name in COMPACTION_RECORDS[harness]:
        path = os.path.join(out_dir, name)
        if not os.path.isfile(path):
            continue
        if name == "session.json":
            try:
                document = read_json(path)
            except (Missing, Failure):
                continue
            records = list(enumerate(document.get("records") or [], 1))
        else:
            records = list(enumerate(jsonl_lines(path), 1))
        work_line = _first_work_line(harness, records)
        for line, record in records:
            kind = _compaction_event(harness, record)
            if not kind:
                continue
            before_work = work_line is None or line <= work_line
            return {"file": name, "event": kind, "line": line,
                    "first_resumed_work_line": work_line,
                    "before_the_resumed_work": before_work,
                    "source": "the resumed session's own native record",
                    "ok": bool(before_work)}
    return None


# --------------------------------------------------------------------------- campaign (E10-9)


TERMINAL_STATUSES = ("complete", "no_result", "timed_out", "launch_failed", "profile_breach")


def trial_state(campaign, tid):
    """`none`, `recorded` with its status, or `partial`.

    E10-43 (finding 21): a directory that exists WITHOUT a `command.json` is a `partial`
    attempt — the trial was started and interrupted — and the report retains it. The dry run's
    `campaign stop` left exactly such a directory and `status` reported `partial_records: []`.
    """
    directory = campaign.trial_dir(tid)
    path = os.path.join(directory, "command.json")
    if not os.path.isfile(path):
        if os.path.isdir(directory):
            return {"state": "partial", "status": None,
                    "why": "the directory exists with no command.json: the attempt was "
                           "started and interrupted"}
        return {"state": "none", "status": None}
    try:
        status = read_json(path).get("status")
    except (Failure, Missing):
        return {"state": "partial", "status": None, "why": "command.json does not parse"}
    if status in TERMINAL_STATUSES:
        return {"state": "recorded", "status": status}
    return {"state": "partial", "status": status}


def trial_complete(campaign, tid):
    state = trial_state(campaign, tid)
    return state["state"] == "recorded" and state["status"] == "complete"


def campaign_queue(campaign, plan):
    """Every trial id in the plan's order, with its lane, kind and state on disk."""
    queue = []
    for lane, ids in sorted(plan["order"].items()):
        for tid in ids:
            queue.append({"lane": lane, "id": tid, "kind": "comparison"})
    for lane, ids in sorted((plan.get("continuation_order") or {}).items()):
        for tid in ids:
            queue.append({"lane": lane, "id": tid, "kind": "continuation"})
    for lane, ids in sorted((plan.get("routing_order") or {}).items()):
        for tid in ids:
            queue.append({"lane": lane, "id": tid, "kind": "routing"})
    for lane, ids in sorted((plan.get("manual_only_order") or {}).items()):
        for tid in ids:
            queue.append({"lane": lane, "id": tid, "kind": "routing", "manual_only": True})
    for row in queue:
        state = trial_state(campaign, row["id"])
        row["state"] = state["state"]
        row["status"] = state["status"]
        row["why"] = state.get("why")
        row["complete"] = state["state"] == "recorded" and state["status"] == "complete"
        row["recorded"] = state["state"] == "recorded"
        row["record_exists"] = os.path.isdir(campaign.trial_dir(row["id"]))
    return queue


# E10-51 (finding 20): one ATOMIC ownership handshake. The parent claims `campaign.pid` with
# O_CREAT|O_EXCL and writes a token; the detached child is told that token, verifies it, and
# rewrites the file with its own pid. Both used to treat the file as somebody else's
# reservation, so a detached start reported `started: true` and its child immediately refused
# itself, running zero trials.
LAUNCH_OPTION_FIELDS = ("fake_launcher", "compact_tokens", "poll_interval", "lanes")


def claim_campaign(campaign, token):
    ensure_dir(campaign.root)
    try:
        handle = os.open(campaign.pid_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        return None
    with os.fdopen(handle, "w") as out:
        out.write("claiming %s\n%s\n" % (os.getpid(), token))
    return token


def campaign_pid(campaign):
    text = read_text(campaign.pid_file) or ""
    first = text.strip().splitlines()[0] if text.strip() else ""
    if first.startswith("claiming"):
        return None, text
    try:
        return int(first), text
    except ValueError:
        return None, text


def campaign_alive(campaign):
    pid, _ = campaign_pid(campaign)
    if not pid:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def do_campaign(args):
    campaign = Campaign(args.campaign)
    if args.action == "status":
        plan = campaign.plan()
        queue = campaign_queue(campaign, plan)
        pid, raw = campaign_pid(campaign)
        alive = bool(campaign_alive(campaign))
        done = sum(1 for r in queue if r["complete"])
        recorded = sum(1 for r in queue if r["recorded"])
        partial = [{"id": r["id"], "why": r.get("why")} for r in queue
                   if r["state"] == "partial"]
        return {
            "campaign": campaign.root, "pid": pid, "running": alive,
            "planned": len(queue), "complete": done, "recorded": recorded,
            "recorded_with_a_failed_outcome": [
                {"id": r["id"], "status": r["status"]} for r in queue
                if r["recorded"] and r["status"] != "complete"],
            "partial_records": [r["id"] for r in partial],
            "partial_detail": partial,
            "live_processes": live_processes(campaign),
            "lane_stops": {name: lane_stopped(campaign, name)
                           for name in sorted({r["lane"] for r in queue})
                           if lane_stopped(campaign, name)},
            "key_state": key_state(),
            "next": next((r["id"] for r in queue if not r["record_exists"]), None),
            "by_lane": {lane: {"planned": sum(1 for r in queue if r["lane"] == lane),
                               "complete": sum(1 for r in queue
                                               if r["lane"] == lane and r["complete"])}
                        for lane in sorted({r["lane"] for r in queue})},
            "status": "complete" if recorded == len(queue) else ("running" if alive else "stopped"),
            "trials_jsonl": campaign.trials_jsonl,
            "interruptions": campaign.interruptions,
            "processes": campaign.processes,
            "log": campaign.log,
        }
    if args.action == "stop":
        if not os.path.isfile(campaign.pid_file):
            return {"campaign": campaign.root, "stopped": False, "reason": "no campaign.pid"}
        pid, _ = campaign_pid(campaign)
        # E10-43 (finding 21): terminate the REGISTERED trial groups too. The dry run's stop
        # killed the loop and left the trial child alive in its own process group.
        registered = live_processes(campaign)
        collected = []
        for row in registered:
            _terminate_group(row["pid"])
            still = True
            try:
                os.kill(row["pid"], 0)
            except OSError:
                still = False
            collected.append({"pid": row["pid"], "trial": row.get("trial"),
                              "attempt": row.get("attempt"), "kind": row.get("kind"),
                              "still_alive": still})
            campaign.append_jsonl(campaign.processes, {
                "event": "ended", "token": row.get("token"), "trial": row.get("trial"),
                "attempt": row.get("attempt"), "kind": row.get("kind"), "pid": row["pid"],
                "exit": None, "stopped_by": "campaign stop", "at": now_iso()})
            campaign.interruption(row.get("trial"), "campaign stop terminated pid %s" % row["pid"],
                                  "collected its status: still_alive=%s" % still,
                                  attempt=row.get("attempt"))
        if pid:
            _terminate_group(pid)
        campaign.interruption(None, "stop asked for pid %s" % pid,
                              "terminated its process group and %d registered trial group(s)"
                              % len(registered))
        os.unlink(campaign.pid_file)
        # the key is left CLOSED after a stop, exactly as E10-40 asks
        return {"campaign": campaign.root, "stopped": True, "pid": pid,
                "terminated_trial_processes": collected,
                "key_state": key_state()}
    if args.action == "start":
        plan = campaign.plan()
        alive = campaign_alive(campaign)
        if alive:
            raise Usage("%s already holds campaign.pid for a live process (%s); `campaign "
                        "stop` first" % (campaign.root, alive))
        if getattr(args, "owner_token", None):
            # the detached child: verify the token the parent wrote, then take ownership
            text = read_text(campaign.pid_file) or ""
            if args.owner_token not in text:
                raise Usage("the ownership token does not match %s" % campaign.pid_file)
            write_text(campaign.pid_file, "%d\n%s\n" % (os.getpid(), args.owner_token))
            return _campaign_loop(campaign, plan, args)
        if os.path.isfile(campaign.pid_file):
            raise Usage("%s holds a campaign.pid from a process that is gone; `campaign stop` "
                        "clears it" % campaign.root)
        # E10-40: a crash leaves the key closed. `campaign start` refuses until `--reopen-key`
        # is run by hand, and the reopening is logged.
        if key_closed() and not args.reopen_key:
            raise Usage("the answer key and held-out set are closed (mode 000) from an earlier "
                        "run; re-run with --reopen-key once you are sure no trial is live")
        if args.reopen_key:
            open_key(campaign, "campaign start --reopen-key")
            campaign.note("the key was reopened by hand with --reopen-key")
        gate = current_probes(campaign, plan)
        if not gate["ok"] and not args.skip_probe_gate:
            raise Usage("E10-42: `campaign start` needs one current successful probe record per "
                        "setup and home; missing %s" % ", ".join(gate["missing"]))
        token = claim_campaign(campaign, uuid.uuid4().hex)
        if token is None:
            raise Usage("%s already holds campaign.pid" % campaign.root)
        if args.foreground:
            write_text(campaign.pid_file, "%d\n%s\n" % (os.getpid(), token))
            return _campaign_loop(campaign, plan, args)
        # E10-51: the launch options are preserved into the detached process. A detached start
        # used to drop `--fake-launcher`, `--compact-tokens` and `--poll-interval`.
        argv = [sys.executable, os.path.abspath(__file__), "campaign", "start",
                "--campaign", campaign.root, "--foreground", "--owner-token", token]
        if args.fake_launcher:
            argv += ["--fake-launcher", args.fake_launcher]
        argv += ["--compact-tokens", str(args.compact_tokens),
                 "--poll-interval", str(args.poll_interval),
                 "--lanes", str(args.lanes)]
        if args.skip_probe_gate:
            argv += ["--skip-probe-gate"]
        child = subprocess.Popen(
            argv, env=campaign.env(), stdout=open(campaign.log, "a"),
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        # the handshake: wait until the child has written its own pid into the file
        deadline = time.time() + 30
        owned = None
        while time.time() < deadline:
            pid, _ = campaign_pid(campaign)
            if pid:
                owned = pid
                break
            if child.poll() is not None:
                raise Failure("the detached campaign process exited %s before taking "
                              "ownership; see %s" % (child.returncode, campaign.log))
            time.sleep(0.1)
        if owned is None:
            raise Failure("the detached campaign process did not take ownership within 30s")
        campaign.note("campaign started detached as pid %s (child %s)" % (owned, child.pid))
        return {"campaign": campaign.root, "started": True, "pid": owned,
                "spawned_pid": child.pid, "owner_token_accepted": True,
                "launch_options": {k: getattr(args, k, None) for k in LAUNCH_OPTION_FIELDS},
                "log": campaign.log, "trials_jsonl": campaign.trials_jsonl}
    raise Usage("campaign takes start, status or stop")


def _campaign_loop(campaign, plan, args):
    """One sequential worker per setup, the three lanes running concurrently (E10-51).

    Finding 20: the old loop walked one flat queue, so the six-trial dry run ran both Claude
    trials, then both Codex trials, then both OpenCode trials, and zero intervals overlapped.
    Each lane is still strictly sequential (E10-5: Claude Code and Codex never overlap with
    themselves); the lanes themselves run at the same time and every record's own
    `started_at`/`ended_at` proves it.
    """
    queue = campaign_queue(campaign, plan)
    # E10-68 defect 1: before the FIRST launch, while the keys are still open (`campaign
    # start` refuses to start with them closed unless `--reopen-key` was given and logged),
    # every planned held-out request is written into the campaign's own `routing-requests/`.
    # After this line the barrier may stay shut for the rest of the campaign and every lane's
    # held-out routing trial still has its text.
    request_cache = cache_routing_requests(campaign, plan.get("routing_entries") or [])
    lanes = {}
    for row in queue:
        lanes.setdefault(row["lane"], []).append(row)
    ran, skipped, failed = [], [], []
    results_lock = threading.Lock()
    in_flight = {}

    def work(lane, rows):
        """The lane's own queue, wrapped so a dead thread can never be invisible (E10-68 (3)).

        On the night of 2026-09-15 `activation()` raised `AttributeError` inside `do_run`,
        the `lane-claude-code` thread died with a traceback on stderr and nothing else,
        `campaign status` said `running` with `lane_stops {}` for three hours, and the
        campaign ended only when the other lanes ran dry. Any uncaught exception now becomes
        a lane stop with its traceback, the trial in flight and the time; `campaign status`
        reports it under `lane_stops` and `campaign start` exits non-zero.
        """
        try:
            _lane_work(lane, rows)
        except BaseException as exc:            # noqa: BLE001 — a thread must not die silently
            record_lane_runner_error(campaign, lane, in_flight.get(lane), exc)
            with results_lock:
                failed.append({"id": (in_flight.get(lane) or {}).get("id"),
                               "why": "the %s lane stopped: %s" % (lane, exc),
                               "lane_stop": "runner_error"})
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise

    def _lane_work(lane, rows):
        last = time.time()
        for row in rows:
            if lane_stopped(campaign, lane):
                with results_lock:
                    skipped.append(row["id"])
                campaign.interruption(row["id"], "the %s lane is stopped" % lane,
                                      "left it alone (E10-46)")
                continue
            if row["recorded"]:
                with results_lock:
                    skipped.append(row["id"])
                if row["status"] != "complete":
                    campaign.interruption(
                        row["id"], "a record already stands with status %s" % row["status"],
                        "left it alone; `rerun` is the operator's call (E10-15)")
                continue
            if row["record_exists"]:
                with results_lock:
                    skipped.append(row["id"])
                campaign.interruption(row["id"], "a partial record exists (%s)"
                                      % (row.get("why") or "no terminal status"),
                                      "left it alone; `rerun` is the operator's call (E10-15)")
                continue
            gap = time.time() - last
            if gap > 600:
                campaign.interruption(row["id"], "a wall-clock gap of %.0fs between trials" % gap,
                                      "recorded the gap and continued")
            last = time.time()
            with results_lock:
                in_flight[lane] = row
            one = argparse.Namespace(campaign=campaign.root, trial=row["id"], attempt_dir=None,
                                     attempt=0, plugins=None, fake_launcher=args.fake_launcher,
                                     compact_tokens=args.compact_tokens,
                                     poll_interval=getattr(args, "poll_interval",
                                                           DEFAULT_POLL_INTERVAL))
            try:
                if row["kind"] == "routing":
                    do_routing(one)
                elif row["kind"] == "continuation":
                    do_continuation(one)
                else:
                    do_run(one)
                with results_lock:
                    ran.append(row["id"])
            except (Usage, Missing, Failure) as exc:
                with results_lock:
                    failed.append({"id": row["id"], "why": str(exc)})
                campaign.interruption(row["id"], "the trial raised: %s" % exc,
                                      "kept the record and went on")
            # NOT a `finally`: an UNCAUGHT exception must leave the row in flight, because
            # that is what names the trial in the lane stop (E10-68 defect 3). A `finally`
            # runs while the exception is propagating and cleared it.
            with results_lock:
                in_flight.pop(lane, None)

    workers = []
    concurrency = int(getattr(args, "lanes", 0) or len(lanes))
    for lane, rows in sorted(lanes.items()):
        workers.append(threading.Thread(target=work, args=(lane, rows), name="lane-%s" % lane))
    started_at = now_iso()
    running = []
    for worker in workers:
        while len([w for w in running if w.is_alive()]) >= max(1, concurrency):
            time.sleep(0.2)
        worker.start()
        running.append(worker)
    for worker in workers:
        worker.join()
    if os.path.isfile(campaign.pid_file):
        os.unlink(campaign.pid_file)
    stops = {name: lane_stopped(campaign, name) for name in sorted(lanes)
             if lane_stopped(campaign, name)}
    document = {"campaign": campaign.root, "ran": sorted(ran), "skipped": sorted(skipped),
                "failed": failed, "planned": len(queue),
                "lanes": sorted(lanes), "concurrency": concurrency,
                "held_out_requests_cached": {
                    "directory": routing_requests_dir(campaign),
                    "entries": len(request_cache.get("entries") or []),
                    "failed": request_cache.get("failed") or []},
                "lane_stops": stops,
                "started_at": started_at, "ended_at": now_iso()}
    # E10-68 defect 3: a lane the RUNNER killed is not a quiet ending. `campaign start` exits
    # non-zero and says which lane, so an operator watching the exit status sees it.
    broken = sorted(n for n, stop in stops.items() if (stop or {}).get("kind") == RUNNER_ERROR)
    if broken:
        document[FAIL_EXIT_KEY] = ("the %s lane(s) stopped on a runner error; see "
                                   "lane-stops/ and %s" % (", ".join(broken), campaign.log))
    return document


# --------------------------------------------------------------------------- report (E10-9)


def measurement_records(campaign):
    """Hash-bound corrected measurements (E10-48, finding 16).

    Raw history stays exactly as it was recorded. A correction is a separate record naming the
    record it corrects, the sha256 of that record's bytes when the correction was written, the
    field, the value the raw record holds and the value that is true, and why. `report`
    consumes only corrections whose binding still holds; one whose target changed is reported
    as stale and is NOT applied.
    """
    rows = []
    for path in sorted(glob.glob(os.path.join(campaign.measurements, "*.json"))):
        try:
            document = read_json(path)
        except (Missing, Failure):
            continue
        document["_path"] = path
        target = document.get("corrects") or {}
        binding_path = target.get("path")
        current = file_sha256(binding_path) if binding_path else None
        document["binding_ok"] = bool(binding_path) and current == target.get("sha256")
        document["current_sha256"] = current
        rows.append(document)
    return rows


def sorted_table_dirs(campaign):
    """Every reserved `tables/<n>/` of this campaign, in numeric order (E10-59 (7))."""
    base = os.path.join(campaign.root, "tables")
    found = []
    for path in glob.glob(os.path.join(base, "*")):
        name = os.path.basename(path)
        if os.path.isdir(path) and name.isdigit():
            found.append((int(name), path))
    return [path for _, path in sorted(found)]


def reserve_tables_dir(campaign):
    """The first free `tables/<n>/`, created atomically (E10-59 (7), E10-43's rule).

    `mkdir` fails with EEXIST on a name that exists, so two reports running at once take two
    numbers and neither replaces a generated table. Nothing under an earlier number is ever
    written again.
    """
    base = os.path.join(campaign.root, "tables")
    ensure_dir(base)
    for index in range(1, 100000):
        path = os.path.join(base, "%d" % index)
        try:
            os.mkdir(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                continue
            raise
        return path
    raise Failure("no free tables directory under %s" % base)


def _identity_of_id(plan, tid):
    """`(setup, condition)` read off a trial id when no `command.json` exists to say (E10-59 (21)).

    A journalled attempt that was interrupted before its record was written still belongs to a
    lane and a condition, and the table has to place it. The plan's own setup names are the
    only safe prefixes: `claude-code-...` is not `claude`.
    """
    names = sorted((s.get("name") for s in (plan or {}).get("setups") or []
                    if isinstance(s, dict) and s.get("name")), key=len, reverse=True)
    body = tid
    for prefix in ("routing-", "cont-"):
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    setup_name = next((n for n in names if body == n or body.startswith(n + "-")), None)
    if setup_name is None:
        setup_name = body.split("-")[0]
    condition = next((c for c in CONDITIONS if ("-%s-" % c) in tid or tid.endswith("-%s" % c)),
                     "n/a")
    return setup_name, condition


def do_report(args):
    """`tables/<n>/table.md`, `tables/<n>/table.json` and a generated skeleton; every number
    from `trials.jsonl` and the grade files, each cell naming its records."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    lines = [json.loads(l) for l in (read_text(campaign.trials_jsonl, "") or "").splitlines()
             if l.strip()]
    # E10-44 (finding 6): grades join on (trial id, attempt), and every attempt's own grade
    # file is found, `attempts/<n>/grade.json` included.
    grades = {}
    for path in sorted(glob.glob(os.path.join(campaign.trials, "*", "grade.json"))
                       + glob.glob(os.path.join(campaign.trials, "*", "attempts", "*",
                                                "grade.json"))):
        grade = read_json(path)
        grades[(grade["trial"], grade.get("attempt", 0))] = {"path": path, "grade": grade}
    corrections = measurement_records(campaign)
    applied, stale = [], []
    by_attempt = {}
    for row in corrections:
        if not row["binding_ok"]:
            stale.append({"correction": row["_path"], "corrects": row.get("corrects"),
                          "why": "the record it corrects changed since the correction was "
                                 "written"})
            continue
        key = (row.get("trial"), row.get("attempt", 0))
        by_attempt.setdefault(key, []).append(row)
        applied.append({"correction": row["_path"], "trial": row.get("trial"),
                        "attempt": row.get("attempt", 0), "field": row.get("field"),
                        "raw": row.get("raw_value"), "corrected": row.get("corrected_value"),
                        "why": row.get("why")})
    cells, rows_seen = {}, []
    for line in lines:
        tid = line["id"]
        attempt = line.get("attempt", 0)
        # The ledger's own `record` is the first source; the attempt's canonical location is
        # the fallback, so a line written before a record moved still finds its command.json
        # (E10-44: the join is on (trial id, attempt), never on the base trial).
        record = line.get("record") or attempt_record(campaign, tid, attempt)
        command = None
        path = os.path.join(record, "command.json")
        if not os.path.isfile(path):
            fallback = attempt_record(campaign, tid, attempt)
            if os.path.isfile(os.path.join(fallback, "command.json")):
                record, path = fallback, os.path.join(fallback, "command.json")
        if os.path.isfile(path):
            command = read_json(path)
        key = (command or {}).get("setup") or tid.split("-")[0]
        condition = (command or {}).get("condition") or "n/a"
        kind = ((command or {}).get("kind") or line.get("kind") or "comparison").split(":")[0]
        if tid.startswith("routing-"):
            kind = "routing"
        elif tid.startswith("cont-"):
            kind = "continuation"
        activated = line.get("activated")
        cost = line.get("cost")
        wall = line.get("wall")
        for correction in by_attempt.get((tid, attempt), []):
            if correction.get("field") == "cost":
                cost = correction.get("corrected_value")
            elif correction.get("field") == "wall":
                wall = correction.get("corrected_value")
        bucket = cells.setdefault((kind, key, condition, bool(activated)), {
            "trials": [], "attempts": [], "records": [], "complete": 0, "graded_ok": 0,
            "cost": 0.0, "wall": 0.0, "no_result": 0, "partial": 0, "grades": []})
        bucket["trials"].append(tid)
        bucket["attempts"].append("%s#%s" % (tid, attempt))
        bucket["records"].append(record)
        bucket["complete"] += 1 if line.get("status") == "complete" else 0
        bucket["no_result"] += 1 if line.get("status") in ("no_result", "timed_out",
                                                          "launch_failed") else 0
        if isinstance(cost, (int, float)):
            bucket["cost"] += cost
        if isinstance(wall, (int, float)):
            bucket["wall"] += wall
        entry = grades.get((tid, attempt))
        if entry:
            bucket["grades"].append(entry["path"])
            if entry["grade"].get("ok"):
                bucket["graded_ok"] += 1
        rows_seen.append({"id": tid, "attempt": attempt, "status": line.get("status"),
                          "cost": cost, "wall": wall, "record": record})
    # E10-43 (finding 21) and E10-48: a partial attempt is retained in the report, and launches
    # are counted apart from trials.
    queue = campaign_queue(campaign, plan)
    partial = [{"id": r["id"], "why": r.get("why")} for r in queue if r["state"] == "partial"]
    journal = jsonl_lines(campaign.attempts_journal)
    # E10-59 (21): a JOURNALLED attempt without `command.json` is counted in the attempt total
    # and appears in the table with status `partial`. The old report counted ledger rows only,
    # so an attempt that was created and interrupted — the one the journal exists for — was
    # absent from `attempts_seen` and from every table row, and showed up only in the
    # `partial_attempts` list beside them.
    ledger_keys = {(r["id"], r["attempt"]) for r in rows_seen}
    partial_attempts = []
    for row in journal:
        tid, attempt = row.get("trial"), row.get("attempt", 0)
        if not tid or (tid, attempt) in ledger_keys:
            continue
        record = row.get("record") or attempt_record(campaign, tid, attempt)
        if os.path.isfile(os.path.join(record, "command.json")):
            continue
        ledger_keys.add((tid, attempt))
        kind = (row.get("kind") or trial_kind_of(plan, tid)).split(":")[0]
        setup_name, condition = _identity_of_id(plan, tid)
        entry = {"id": tid, "attempt": attempt, "kind": kind, "setup": setup_name,
                 "condition": condition, "record": record, "status": "partial",
                 "journalled_at": row.get("created_at"),
                 "why": "journalled with no command.json: the attempt was started and "
                        "interrupted (E10-43, E10-59 (21))"}
        partial_attempts.append(entry)
        rows_seen.append({"id": tid, "attempt": attempt, "status": "partial",
                          "cost": None, "wall": None, "record": record})
        bucket = cells.setdefault((kind, setup_name, condition, False), {
            "trials": [], "attempts": [], "records": [], "complete": 0, "graded_ok": 0,
            "cost": 0.0, "wall": 0.0, "no_result": 0, "partial": 0, "grades": []})
        bucket["trials"].append(tid)
        bucket["attempts"].append("%s#%s" % (tid, attempt))
        bucket["records"].append(record)
        bucket["partial"] += 1
    known = {row["id"] for row in partial}
    for entry in partial_attempts:
        if entry["id"] not in known:
            partial.append({"id": entry["id"], "why": entry["why"]})
            known.add(entry["id"])
    launches = [row for row in process_rows(campaign) if row.get("event") == "started"]
    table = []
    for (kind, setup, condition, activated), bucket in sorted(cells.items()):
        table.append({
            "kind": kind, "setup": setup, "condition": condition, "activated": activated,
            "trials": len(set(bucket["trials"])), "attempts": len(bucket["attempts"]),
            "complete": bucket["complete"],
            "no_result": bucket["no_result"], "partial": bucket["partial"],
            "graded_ok": bucket["graded_ok"],
            "cost_usd": round(bucket["cost"], 6) if bucket["cost"] else None,
            "wall_seconds": round(bucket["wall"], 1),
            "records": bucket["records"],
            "attempt_ids": bucket["attempts"],
            "grade_files": bucket["grades"],
        })
    summary = grade_summary([g["grade"] for g in grades.values()])
    # E10-59 (7): `report` NEVER REPLACES. The generated table of every run takes its own
    # reserved directory `tables/<n>/`, the first free number, created with `mkdir` so two
    # reports cannot take the same one; the fixed `tables/table.json` and `tables/table.md` of
    # the old shape were rewritten on every run, and a marker left in one by hand was lost.
    # E10-43 names `grade.json` as the sole replaceable file, and it still is.
    tables_dir = reserve_tables_dir(campaign)
    document = {"campaign": campaign.root, "plan_counts": plan.get("counts"),
                "tables_dir": tables_dir,
                "trials_seen": len(lines),
                "attempts_seen": len({(r["id"], r["attempt"]) for r in rows_seen}),
                "attempts_journalled": len(journal),
                "launches_recorded": len(launches),
                "partial_attempts": partial,
                "partial_attempts_detail": partial_attempts,
                "graded": len(grades), "table": table,
                "grade_summary": summary,
                "corrected_measurements_applied": applied,
                "corrected_measurements_stale": stale,
                "totals": {
                    "cost_usd": round(sum(r["cost"] for r in rows_seen
                                          if isinstance(r["cost"], (int, float))), 8),
                    "wall_seconds": round(sum(r["wall"] for r in rows_seen
                                              if isinstance(r["wall"], (int, float))), 1),
                    "by_status": {status: sum(1 for r in rows_seen if r["status"] == status)
                                  for status in sorted({r["status"] for r in rows_seen})},
                },
                "sources": {"lines": campaign.trials_jsonl,
                            "grades": sorted(g["path"] for g in grades.values()),
                            "measurements": sorted(r["_path"] for r in corrections),
                            "attempts_journal": campaign.attempts_journal,
                            "processes": campaign.processes}}
    write_json(os.path.join(tables_dir, "table.json"), document)
    md = ["# %s: the comparison table" % os.path.basename(campaign.root), "",
          "Every number is computed from `trials.jsonl` and the grade files, joined by",
          "(trial id, attempt); each row names its records. Available trials are split by",
          "`activated` (E10-4). Corrected measurements (E10-48) are applied only where their",
          "hash binding still holds. A journalled attempt with no `command.json` is counted",
          "here with status `partial` (E10-59 (21)).", "",
          "| kind | setup | condition | activated | trials | attempts | complete | no result | partial | graded ok | cost USD | wall s |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in table:
        md.append("| %s | %s | %s | %s | %d | %d | %d | %d | %d | %d | %s | %s |" % (
            row["kind"], row["setup"], row["condition"], row["activated"], row["trials"],
            row["attempts"], row["complete"], row["no_result"], row["partial"],
            row["graded_ok"],
            "%.6f" % row["cost_usd"] if row["cost_usd"] else "null", row["wall_seconds"]))
    md += ["", "## Records per row", ""]
    for row in table:
        md.append("- %s / %s / %s / activated=%s: attempts %s; records %s; grades %s" % (
            row["kind"], row["setup"], row["condition"], row["activated"],
            ", ".join(row["attempt_ids"]), ", ".join(row["records"]),
            ", ".join(row["grade_files"]) or "none"))
    if partial:
        md += ["", "## Partial attempts retained (E10-43, E10-59 (21))", ""]
        for row in partial:
            md.append("- %s: %s" % (row["id"], row["why"]))
    if partial_attempts:
        md += ["", "## Journalled attempts counted as `partial`", ""]
        for row in partial_attempts:
            md.append("- %s#%s (%s / %s / %s), journalled %s: %s"
                      % (row["id"], row["attempt"], row["kind"], row["setup"],
                         row["condition"], row["journalled_at"], row["record"]))
    if applied or stale:
        md += ["", "## Corrected measurements (E10-48)", ""]
        for row in applied:
            md.append("- applied: %s#%s %s %s -> %s (%s)" % (row["trial"], row["attempt"],
                                                             row["field"], row["raw"],
                                                             row["corrected"], row["correction"]))
        for row in stale:
            md.append("- NOT applied (binding broken): %s" % row["correction"])
    write_text(os.path.join(tables_dir, "table.md"), "\n".join(md) + "\n")
    # E10-43 (finding 7): the generated skeleton is a GENERATED TABLE, kept apart from the
    # operator's own report. `report` used to overwrite `report.md`, which is where the
    # operator writes; a marker left there by hand was replaced by a skeleton.
    skeleton_path = os.path.join(tables_dir, "report-skeleton.md")
    skeleton = [
        "# %s: the operator's report (generated skeleton)" % os.path.basename(campaign.root), "",
        "This file is GENERATED. The operator's own report is `report.md` at the campaign root",
        "and is never written by `report` (E10-43). Every number below is copied from a named",
        "record (E10-15).", "",
        "## 1. What ran", "", "- planned: %s" % json.dumps(plan.get("counts")),
        "- trial lines: %d (`trials.jsonl`)" % len(lines),
        "- attempts journalled: %d (`attempts.jsonl`)" % len(journal),
        "- attempts counted (ledger rows plus journalled partials): %d"
        % len({(r["id"], r["attempt"]) for r in rows_seen}),
        "- launches recorded: %d (`processes.jsonl`)" % len(launches),
        "- partial attempts retained: %d" % len(partial),
        "- journalled attempts counted as `partial`: %d" % len(partial_attempts),
        "- graded: %d" % len(grades), "",
        "## 2. The comparison table", "", "See `table.md`.", "",
        "## 3. Grade counts", "", "```json", json.dumps(summary, indent=2, sort_keys=True), "```", "",
        "## 4. Interruptions", "", "See `../interruptions.jsonl`.", "",
        "## 5. Routing", "", "See `../routing/`.", "",
        "## 6. Corrected measurements", "", "```json",
        json.dumps({"applied": applied, "stale": stale}, indent=2, sort_keys=True), "```", "",
        "## 7. What the operator could not do", "", "- (the operator fills this in "
        "in ../report.md)", "",
    ]
    write_text(skeleton_path, "\n".join(skeleton) + "\n")
    scan = scan_paths(walk_files(campaign.root),
                      exempt=auth_store_exemptions(plan_setup_pairs(campaign)))
    document["scan_hits"] = len(scan["hits"])
    result = {"campaign": campaign.root,
              # E10-59 (7): the report's stdout NAMES THE DIRECTORY IT WROTE.
              "tables_dir": tables_dir,
              "tables_dir_reserved_as": os.path.relpath(tables_dir, campaign.root),
              "tables_replaced_nothing": True,
              "previous_tables_dirs": [d for d in sorted_table_dirs(campaign)
                                       if d != tables_dir],
              "table_md": os.path.join(tables_dir, "table.md"),
              "table_json": os.path.join(tables_dir, "table.json"),
              "report_skeleton_md": skeleton_path,
              "operator_report_untouched": os.path.join(campaign.root, "report.md"),
              "rows": len(table), "trials_seen": len(lines),
              "attempts_seen": document["attempts_seen"],
              "attempts_journalled": document["attempts_journalled"],
              "launches_recorded": document["launches_recorded"],
              "partial_attempts": partial,
              "partial_attempts_detail": partial_attempts,
              "graded": len(grades), "totals": document["totals"],
              "corrected_measurements_applied": applied,
              "corrected_measurements_stale": stale,
              "grade_summary": summary}
    # E10-52 (finding 24): a credential shape in the records fails the report gate too.
    if scan["hits"]:
        raise Failure("the campaign records hold %d credential-shaped value(s); `scan` names "
                      "them" % len(scan["hits"]))
    return result


# --------------------------------------------------------------------------- check (E10-9)

FAKE_DIR = os.path.join(RUNNER_DIR, "tests", "fake")
SENTINEL_TEXT = "RECHECK-RUNNER-SENTINEL: a file outside the trial's own opaque tree\n"


def interpreter_record():
    """What `check` actually ran on, so a green run names its runtime (E10-52, finding 25)."""
    return {"executable": sys.executable,
            "version": sys.version.split()[0],
            "version_full": sys.version.replace("\n", " "),
            "jsonschema_for_the_validator": "supplied by `uv run` from validate-result.py's "
                                            "own inline metadata (jsonschema==4.25.1)"}


def do_check(args):
    """The runner's self-test: the tests, a dry trial against the fake harness, the negative
    metric cases, and the read-boundary sentinel of E10-40."""
    scratch = args.scratch or os.path.join(
        os.environ.get("RECHECK_RUNNER_TEST_SCRATCH") or tool_tmpdir(),
        "recheck-runner-check-%d" % os.getpid())
    if os.path.exists(scratch):
        rmtree(scratch)
    ensure_dir(scratch)
    test_env = tool_env(extra={"RECHECK_RUNNER_TEST_SCRATCH": os.path.join(scratch, "tests")})
    tests = run_cmd([sys.executable, "-m", "unittest", "discover", "-s",
                     os.path.join(RUNNER_DIR, "tests"), "-q"],
                    env=test_env, cwd=os.path.expanduser("~"), label="unittest discover")
    dry, negatives, sentinel = None, None, None
    try:
        if not args.tests_only:
            dry = fake_dry_trial(os.path.join(scratch, "dry"))
            negatives = negative_metric_cases(os.path.join(scratch, "negatives"))
            sentinel = sentinel_probe(os.path.join(scratch, "sentinel"))
    finally:
        # `check` is not a campaign: it never leaves the two directories closed behind it.
        open_key(None, "check finished")
    document = {
        "interpreter": interpreter_record(),
        "tests": {"exit": tests["exit"], "tail": (tests["stderr"] or tests["stdout"])[-1800:]},
        "dry_trial": dry,
        "negative_metric_cases": negatives,
        "read_boundary_sentinel": sentinel,
        "key_boundary": KEY_BOUNDARY_LABEL,
        "key_state": key_state(),
    }
    problems = []
    if tests["exit"] != 0:
        problems.append("the test suite exited %s" % tests["exit"])
    if dry is not None:
        if dry.get("status") != "complete":
            problems.append("the dry trial is %s" % dry.get("status"))
        if dry.get("validate_last_line") != "exit 0":
            problems.append("the dry trial's real validator said %r"
                            % dry.get("validate_last_line"))
        if dry.get("validator_skips") != 0:
            problems.append("the dry trial's validator skipped %s check(s)"
                            % dry.get("validator_skips"))
        if not dry.get("graded_ok"):
            problems.append("the dry trial did not grade ok: %s" % dry.get("ok_because"))
    if negatives is not None:
        for row in negatives["cases"]:
            if row["graded_ok"] is not False:
                problems.append("the negative case %r did not fail its grade" % row["case"])
    document["ok"] = not problems
    document["problems"] = problems
    if problems:
        raise Failure("check failed: %s" % "; ".join(problems))
    return document


def _synthetic_campaign(scratch, cases=(), setups=("claude-code",), conditions=("available",)):
    """A campaign the RUNNER marks synthetic, so an E10-21 stand-in is honoured (E10-45)."""
    campaign = Campaign(os.path.join(scratch, "campaign"))
    campaign.ensure()
    stage = os.path.join(scratch, "stage")
    for harness in HARNESSES:
        ensure_dir(os.path.join(stage, "plugins", "recheck-v2", "setups", harness))
    write_json(campaign.stage_json, {
        "campaign": campaign.root, "checkout": REPO_ROOT, "commit": "fake-check",
        "stage": stage, "plugin_tree_sha256": "fake", "evals_excluded": True,
        "answer_key_or_held_out_in_stage": [], "canonical_content_sha256": None,
        "skill_identity_exit": 0, "files_copied": 0, "staged_at": now_iso()})
    plan = default_plan("check")
    plan["setups"] = [{"name": n, "harness": n} for n in setups]
    plan["cases"] = list(cases or ["F1-01-fixed-clean"])
    plan["repetitions"] = 1
    plan["conditions"] = list(conditions)
    plan["routing"] = {"entries": ["T-01-slash-v2-slice"], "repetitions": 1}
    document = dict(plan)
    document.update({"planned_at": now_iso(), "campaign": campaign.root,
                     "stage": read_json(campaign.stage_json),
                     "path_entries": path_entries(require=False),
                     "allowlisted_env_names": list(ALLOWED_ENV),
                     "case_lanes": {c: lane_index()[c] for c in plan["cases"]},
                     "order": order_of(plan), "routing_entries": [],
                     "routing_order": {}, "manual_only_order": {}, "continuation_order": {},
                     "synthetic": True,
                     "counts": {"comparison": sum(len(v) for v in order_of(plan).values()),
                                "routing": 0, "manual_only": 0, "continuation": 0,
                                "total": sum(len(v) for v in order_of(plan).values())}})
    write_json(campaign.campaign_json, document)
    campaign.mark_synthetic("check built this campaign")
    return campaign, document


def _stand_in_key(scratch, case, expected=None, runs_at="E10"):
    """A key `check` wrote ITSELF: synthetic entries in the key's shape, never a copy (E10-21).

    Nothing in this function, and nothing it writes, comes from `evals/answer-key/`.
    """
    directory = os.path.join(scratch, "key-stand-in-%s" % runs_at.lower())
    ensure_dir(directory)
    lane = lane_index()[case]
    entry = {"case": case, "checks": ["SELFTEST"], "requirements": ["SELFTEST"],
             "runs_at": runs_at,
             "expected": expected if expected is not None else {
                 "status": "completed", "items": [{"disposition": "fixed"}]},
             "must_not": ["a stand-in written by check, never a key value"]}
    write_json(os.path.join(directory, "%s.json" % lane), [entry])
    return directory


def fake_dry_trial(scratch):
    """One whole trial against the fake harness: no model, the real code path, the REAL
    validator, and a real grade against a stand-in key (E10-9's `check`)."""
    campaign, plan = _synthetic_campaign(scratch)
    tid = trial_id("claude-code", "F1-01-fixed-clean", "available", 1)
    args = argparse.Namespace(campaign=campaign.root, trial=tid, attempt_dir=None, attempt=0,
                              plugins=["recheck-v2"],
                              fake_launcher=os.path.join(FAKE_DIR, "claude-code-launch.sh"),
                              compact_tokens=2000)
    result = do_run(args)
    validation = read_json(os.path.join(campaign.trial_dir(tid), "validate.txt").replace(
        "validate.txt", "validate.json"))
    verdict = {}
    text = read_text(os.path.join(campaign.trial_dir(tid), "validate.txt"), "") or ""
    body = "\n".join(l for l in text.splitlines() if not l.startswith("exit "))
    try:
        verdict = json.loads(body)
    except ValueError:
        verdict = {}
    directory = _stand_in_key(scratch, "F1-01-fixed-clean")
    graded = _grade_with_stand_in(campaign, tid, directory)
    return {"campaign": campaign.root, "trial": tid, "status": result["status"],
            "validate_last_line": result["validate_last_line"],
            "validator_schema_errors": len(verdict.get("schema") or []),
            "validator_semantic_errors": len(verdict.get("semantic") or []),
            "validator_skips": len(verdict.get("skipped") or []),
            "validation_binding": validation,
            "graded_ok": graded.get("ok"),
            "ok_because": graded.get("ok_because"),
            "activated": result["activated"], "scan_hits": result["scan_hits"]}


def _grade_with_stand_in(campaign, tid, key_directory, attempt=0):
    """Grade one record in this process against a stand-in, under the E10-21 flags."""
    saved = {k: os.environ.get(k) for k in (TEST_FLAG, KEY_DIR_OVERRIDE)}
    os.environ[TEST_FLAG] = "1"
    os.environ[KEY_DIR_OVERRIDE] = key_directory
    try:
        with key_open(campaign, "check"):
            return grade_one(campaign, campaign.plan(), tid,
                             attempt_record(campaign, tid, attempt), attempt)
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def negative_metric_cases(scratch):
    """Records the runner produced, degraded one metric at a time, each of which must FAIL.

    Live check 1 asks for "the negative metric cases failing their grades". Every record below
    is one the fake harness actually produced; exactly one thing is taken out of each copy, so
    a case that passes proves the metric is not gating.
    """
    campaign, plan = _synthetic_campaign(scratch)
    tid = trial_id("claude-code", "F1-01-fixed-clean", "available", 1)
    do_run(argparse.Namespace(campaign=campaign.root, trial=tid, attempt_dir=None, attempt=0,
                              plugins=["recheck-v2"],
                              fake_launcher=os.path.join(FAKE_DIR, "claude-code-launch.sh"),
                              compact_tokens=2000))
    base = campaign.trial_dir(tid)
    key = _stand_in_key(scratch, "F1-01-fixed-clean")
    rows = []

    def derive(name, mutate):
        target = os.path.join(campaign.trial_dir(tid), "attempts", str(len(rows) + 1))
        ensure_dir(os.path.dirname(target))
        shutil.copytree(base, target, symlinks=True,
                        ignore=shutil.ignore_patterns("attempts", "grade.json"))
        mutate(target)
        command = read_json(os.path.join(target, "command.json"))
        command["attempt"] = len(rows) + 1
        write_json(os.path.join(target, "command.json"), command)
        return target, len(rows) + 1

    # 1. missing evidence: every item's evidence removed from the result
    def strip_evidence(target):
        result = read_json(os.path.join(target, "result.json"))
        for item in result.get("items") or []:
            item.pop("evidence", None)
            if isinstance(item.get("verification"), dict):
                item["verification"]["evidence"] = []
        write_json(os.path.join(target, "result.json"), result)

    # 2. missing chat: the harness reply loses its Result line and its item lines
    def strip_reply(target):
        reply = read_text(os.path.join(target, "reply.md"), "") or ""
        kept = [l for l in reply.splitlines()
                if not l.startswith("Result:") and " · " not in l]
        write_text(os.path.join(target, "reply.md"), "\n".join(kept) + "\n")
        write_text(os.path.join(target, "chat.md"), "\n".join(kept) + "\n")

    # 3. a skipped check under --strict: the REAL validator, run without the run directory and
    #    the workspace, so V-checks report themselves skipped; the retained verdict is bound to
    #    the same bytes and the live run directory is taken out of reach.
    def make_skip(target):
        result = os.path.join(target, "result.json")
        seeded = os.path.join(target, "input.json")
        step = run_cmd(["uv", "run", os.path.join(SKILL_DIR, "scripts", "validate-result.py"),
                        result, "--input", seeded, "--strict"],
                       env=campaign.env(), label="validate-result.py --strict (no run dir)")
        text = (step["stdout"] or "")
        if text and not text.endswith("\n"):
            text += "\n"
        write_text(os.path.join(target, "validate.txt"), text + "exit %s\n" % step["exit"])
        command = read_json(os.path.join(target, "command.json"))
        command["run_dir"] = os.path.join(campaign.tmp, "a-run-directory-that-is-gone")
        command["validation_binding"] = {
            "validated": True, "exit": step["exit"],
            "result_sha256": file_sha256(result),
            "input_sha256": file_sha256(seeded),
            "run_dir": command["run_dir"], "workspace": command.get("workspace"),
            "validated_at": now_iso()}
        write_json(os.path.join(target, "command.json"), command)
        write_json(os.path.join(target, "validate.json"), command["validation_binding"])

    for name, mutate, expect in (
            ("missing-evidence", strip_evidence, "evidence_sufficient"),
            ("missing-chat", strip_reply, "interop"),
            ("skip", make_skip, "zero_skips")):
        target, attempt = derive(name, mutate)
        grade = _grade_with_stand_in(campaign, tid, key, attempt)
        rows.append({"case": name, "record": target, "graded_ok": grade.get("ok"),
                     "ok_because": grade.get("ok_because"),
                     "the_metric_that_must_fail": expect,
                     "it_failed": expect in (grade.get("ok_because") or [])})

    # 4. a key the result contradicts: the stand-in pins `not_fixed`, the result says `fixed`
    false_fixed_key = _stand_in_key(
        scratch, "F1-01-fixed-clean",
        expected={"status": "completed", "items": [{"disposition": "not_fixed"}]})
    grade = _grade_with_stand_in(campaign, tid, false_fixed_key)
    rows.append({"case": "false-fixed", "record": base, "graded_ok": grade.get("ok"),
                 "ok_because": grade.get("ok_because"),
                 "the_metric_that_must_fail": "no_false_fixed",
                 "it_failed": "no_false_fixed" in (grade.get("ok_because") or [])})

    # 5. a key that does not run at E10 is refused BEFORE matching (finding 9)
    wrong_phase = _stand_in_key(scratch, "F1-01-fixed-clean", runs_at="E7")
    refused, why = False, None
    try:
        _grade_with_stand_in(campaign, tid, wrong_phase)
    except (Failure, Usage) as exc:
        refused, why = True, str(exc)
    rows.append({"case": "wrong-key-phase", "record": base,
                 "graded_ok": False if refused else True, "refused": refused,
                 "ok_because": [why] if why else [],
                 "the_metric_that_must_fail": "refused before matching",
                 "it_failed": refused})
    return {"campaign": campaign.root, "cases": rows,
            "all_failed_as_they_must": all(r["it_failed"] for r in rows)}


def sentinel_probe(scratch):
    """E10-40: a sentinel proves what a launched child can and cannot read.

    The boundary on these setups is `instruction-bound + measured`, not enforced: the three
    harnesses run every trial as this user with no read sandbox. What IS mechanical is
    measured here — a file inside the trial's own opaque tree, a file outside it under the
    campaign root, and the two key directories at mode 000 during the launch.
    """
    campaign, plan = _synthetic_campaign(scratch)
    outside = os.path.join(campaign.root, "reviewer-only-sentinel.txt")
    write_text(outside, SENTINEL_TEXT)
    tid = trial_id("claude-code", "F1-01-fixed-clean", "available", 1)
    tree = campaign.opaque_tree(tid, 0)
    ensure_dir(tree)
    inside = os.path.join(tree, "inside-sentinel.txt")
    write_text(inside, SENTINEL_TEXT)
    key_before = key_state()
    do_run(argparse.Namespace(campaign=campaign.root, trial=tid, attempt_dir=None, attempt=0,
                              plugins=["recheck-v2"],
                              fake_launcher=os.path.join(FAKE_DIR, "claude-code-launch.sh"),
                              compact_tokens=2000))
    key_during = key_state()
    record = campaign.trial_dir(tid)
    command = read_json(os.path.join(record, "command.json"))
    witnesses = trace_witnesses(campaign, record, command)
    # what a child process COULD read while the key was closed, measured directly
    reachable = {}
    for label, path in (("the sentinel inside the trial's own tree", inside),
                        ("the sentinel outside it, under the campaign root", outside),
                        ("the answer key directory", KEY_DIR),
                        ("the held-out directory", os.path.dirname(TRIGGER_HELDOUT))):
        probe = run_cmd([sys.executable, "-c",
                         "import os,sys;p=sys.argv[1];\n"
                         "sys.exit(0 if (os.path.isdir(p) and os.listdir(p)) or "
                         "(os.path.isfile(p) and open(p).read()) else 1)", path],
                        env=tool_env(), label="sentinel read")
        reachable[label] = {"path": path, "readable": probe["exit"] == 0,
                            "exit": probe["exit"]}
    return {"campaign": campaign.root,
            "key_state_before_the_launch": key_before,
            "key_state_after_the_launch": key_during,
            "key_closed_during_the_launch": all(r["closed"] for r in key_during if r["present"]),
            "readable_by_a_child_while_the_key_is_closed": reachable,
            "records_reached_by_the_trial": witnesses["records_reached"],
            "skill_file_reached_by_the_trial": witnesses["skill_file_reached"],
            "boundary": KEY_BOUNDARY_LABEL,
            "note": "E10-40: Astra's prescription (the key outside the launch process's "
                    "ENFORCED read access) is not reachable on these setups, and is recorded "
                    "as such. The key directories are held at mode 000 for the whole launch "
                    "and the grader measures every read of a campaign record outside the "
                    "trial's own opaque tree."}


# --------------------------------------------------------------------------- key-state, measure


def do_lane_stop(args):
    """Show every lane stop, or clear one with a reason (E10-46)."""
    campaign = Campaign(args.campaign)
    if args.clear:
        if not args.setup or not args.why:
            raise Usage("--clear needs --setup and --why")
        return clear_lane_stop(campaign, args.setup, args.why)
    stops = {}
    for path in sorted(glob.glob(os.path.join(campaign.root, "lane-stops", "*.json"))):
        stops[os.path.basename(path)[:-5]] = read_json(path)
    return {"campaign": campaign.root, "stops": stops,
            "cleared": sorted(glob.glob(os.path.join(campaign.root, "lane-stops", "cleared",
                                                     "*.json")))}


def do_key_state(args):
    """The mode of the two key directories, and the one hand-run reopening E10-40 allows."""
    before = key_state()
    reopened = []
    if args.reopen:
        reopened = open_key(None, "key-state --reopen")
        sys.stderr.write("runner.py: reopened %s by hand\n" % ", ".join(reopened))
    return {"boundary": KEY_BOUNDARY_LABEL, "before": before, "after": key_state(),
            "reopened": reopened,
            "note": "E10-40: these directories are held at mode 000 for the whole of every "
                    "launch and reopened only inside grade and routing-score. A crashed run "
                    "leaves them closed; this is the hand reopening, and it is logged."}


def do_measure(args):
    """A hash-bound corrected measurement record (E10-48, finding 16).

    Raw history is never edited. The correction names the record it corrects, that record's
    sha256 at the time of writing, the field, the raw value, the corrected value, why, and the
    files the corrected value was read from. `report` applies it only while the binding holds.
    """
    campaign = Campaign(args.campaign)
    campaign.ensure()
    ensure_dir(campaign.measurements)
    if args.field not in ("cost", "wall"):
        raise Usage("a correction is written for `cost` or `wall`, not %r" % args.field)
    if not os.path.exists(args.corrects):
        raise Missing("nothing to correct at %s" % args.corrects)
    def number(text):
        try:
            return float(text)
        except ValueError:
            return None
    document = {
        "trial": args.trial, "attempt": args.attempt, "field": args.field,
        "corrects": {"path": os.path.abspath(args.corrects),
                     "sha256": file_sha256(args.corrects)},
        "raw_value": number(args.raw_value) if number(args.raw_value) is not None
        else args.raw_value,
        "corrected_value": number(args.corrected_value)
        if number(args.corrected_value) is not None else args.corrected_value,
        "why": args.why,
        "evidence": [{"path": os.path.abspath(p), "sha256": file_sha256(p)}
                     for p in args.evidence],
        "written_at": now_iso(),
        "rule": "E10-48: raw history stays; this record corrects one field of one attempt and "
                "`report` consumes it only while the binding above still holds.",
    }
    check_identifier("the trial the correction names", args.trial)
    path = None
    for index in range(0, 1000):
        candidate = os.path.join(campaign.measurements, "%s-%d-%s%s.json"
                                 % (args.trial, args.attempt, args.field,
                                    "" if index == 0 else "-%d" % index))
        try:
            handle = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                continue
            raise
        os.close(handle)
        path = candidate
        break
    write_json(path, document)
    campaign.note("corrected measurement %s#%s %s -> %s (%s)"
                  % (args.trial, args.attempt, args.field, document["corrected_value"], path))
    return dict(document, record=path)


# --------------------------------------------------------------------------- the CLI


def build_parser():
    parser = argparse.ArgumentParser(
        prog="runner.py",
        description="The recheck-v2 E10 trial runner. JSON on stdout, diagnostics on stderr; "
                    "exit 0 ok, 2 usage, 3 a missing binary/setup/record, 1 anything else.")
    subs = parser.add_subparsers(dest="subcommand")

    def campaign_arg(sub, required=True):
        sub.add_argument("--campaign", required=required,
                         default=None if required else CAMPAIGN_ROOT,
                         help="the campaign directory under ~/.local/share/skills-v2-pilot/e10/")

    one = subs.add_parser("stage", help="a copy of the checkout with evals/ excluded (E10-6)")
    campaign_arg(one)
    one.add_argument("--refresh", action="store_true", help="replace an existing stage")
    one.set_defaults(func=do_stage)

    one = subs.add_parser("install", help="install the setups' homes from the staged copy")
    campaign_arg(one)
    one.add_argument("--setup", action="append", help="one setup name (repeatable)")
    one.add_argument("--home", choices=HOMES, help="only this home")
    one.set_defaults(func=do_install)

    one = subs.add_parser("verify", help="verify-install.sh per home plus the leak scan")
    campaign_arg(one)
    one.add_argument("--setup", action="append")
    one.add_argument("--home", choices=HOMES)
    one.set_defaults(func=do_verify)

    one = subs.add_parser("probe-env", help="a trial-shaped session that prints variable names")
    campaign_arg(one)
    one.add_argument("--setup", action="append")
    one.add_argument("--home", choices=HOMES)
    one.add_argument("--timeout", type=int, default=600)
    one.add_argument("--refresh", action="store_true")
    one.set_defaults(func=do_probe_env)

    one = subs.add_parser("plan", help="write campaign.json from plan.json")
    campaign_arg(one)
    one.add_argument("--plan", help="a plan.json; omitted, the full E10 default plan")
    one.add_argument("--refresh", action="store_true")
    one.add_argument("--synthetic", action="store_true",
                     help="mark the campaign synthetic, so an E10-21 key stand-in is honoured "
                          "(tests and `check` only)")
    one.set_defaults(func=do_plan)

    one = subs.add_parser("run", help="one comparison trial end to end")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--plugins", action="append", help="override the plugins a launch loads")
    one.add_argument("--fake-launcher", help="a stub launcher (tests and `check` only)")
    one.set_defaults(func=do_run, attempt_dir=None, attempt=0, compact_tokens=2000,
                     poll_interval=DEFAULT_POLL_INTERVAL)

    one = subs.add_parser("rerun", help="a new attempt beside a failed one (any kind)")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--fake-launcher")
    one.add_argument("--compact-tokens", type=int, default=2000)
    one.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    one.set_defaults(func=do_rerun, plugins=None)

    one = subs.add_parser("grade", help="validate, match, and the metrics of E10-11")
    campaign_arg(one)
    one.add_argument("trial", nargs="?")
    one.add_argument("--attempt", type=int, default=0,
                     help="which attempt of that trial (0 is the first)")
    one.add_argument("--all", action="store_true",
                     help="every comparison AND continuation attempt, reruns included")
    one.add_argument("--summary", action="store_true", help="counts only")
    one.add_argument("--restaged", action="store_true",
                     help="grade trials whose recorded staged_commit is not the campaign's "
                          "staged commit, and record the disagreement in grade.json "
                          "(E10-59 (9))")
    one.set_defaults(func=do_grade)

    one = subs.add_parser("routing", help="one routing trial (E10-13)")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--fake-launcher")
    one.set_defaults(func=do_routing, attempt=0)

    one = subs.add_parser("routing-score", help="the trigger README's rows, behind the wall")
    campaign_arg(one)
    one.add_argument("--revision", default="rev1")
    one.set_defaults(func=do_routing_score)

    one = subs.add_parser("continuation", help="the cut, the hand-off, the compaction attempt")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--compact-tokens", type=int, default=2000,
                     help="the Codex auto-compact token limit for the compaction resume")
    one.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL,
                     help="seconds between checkpoint polls; E10-47 fixes the default and the "
                          "maximum at 0.1 (at least ten times a second)")
    one.add_argument("--fake-launcher")
    one.set_defaults(func=do_continuation)

    one = subs.add_parser("campaign", help="start, status or stop the whole plan")
    one.add_argument("action", choices=("start", "status", "stop"))
    campaign_arg(one)
    one.add_argument("--foreground", action="store_true")
    one.add_argument("--fake-launcher")
    one.add_argument("--compact-tokens", type=int, default=2000)
    one.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    one.add_argument("--lanes", type=int, default=0,
                     help="how many setup lanes run at once (0 = every lane in the plan)")
    one.add_argument("--owner-token", help="internal: the detached child's ownership token")
    one.add_argument("--reopen-key", action="store_true",
                     help="reopen the answer key left closed by a crashed run (E10-40)")
    one.add_argument("--skip-probe-gate", action="store_true",
                     help="start without nine current probe records (tests and `check` only)")
    one.set_defaults(func=do_campaign)

    one = subs.add_parser("scan", help="the credential scan over every record")
    campaign_arg(one)
    one.add_argument("paths", nargs="*", help="extra roots to scan")
    one.set_defaults(func=do_scan)

    one = subs.add_parser("report", help="table.md, table.json and a report.md skeleton")
    campaign_arg(one)
    one.set_defaults(func=do_report)

    one = subs.add_parser("check", help="the runner's own tests, a dry trial, the negative "
                                       "metric cases and the read-boundary sentinel; no model")
    one.add_argument("--campaign", default=CAMPAIGN_ROOT, help="unused; accepted for symmetry")
    one.add_argument("--tests-only", action="store_true")
    one.add_argument("--scratch", help="where the dry trial builds its campaign")
    one.set_defaults(func=do_check)

    one = subs.add_parser("lane-stop", help="show or clear a lane stop (E10-46)")
    campaign_arg(one)
    one.add_argument("--setup", help="the lane")
    one.add_argument("--clear", action="store_true", help="clear it, keeping it as a record")
    one.add_argument("--why", help="why it is being cleared (required with --clear)")
    one.set_defaults(func=do_lane_stop)

    one = subs.add_parser("key-state", help="the mode of the two key directories (E10-40)")
    one.add_argument("--campaign", default=CAMPAIGN_ROOT, help="unused; accepted for symmetry")
    one.add_argument("--reopen", action="store_true", help="reopen them by hand, and log it")
    one.set_defaults(func=do_key_state)

    one = subs.add_parser("measure", help="write a hash-bound corrected measurement (E10-48)")
    campaign_arg(one)
    one.add_argument("--trial", required=True)
    one.add_argument("--attempt", type=int, default=0)
    one.add_argument("--field", required=True, help="cost or wall")
    one.add_argument("--corrects", required=True, help="the record the correction is bound to")
    one.add_argument("--raw-value", required=True)
    one.add_argument("--corrected-value", required=True)
    one.add_argument("--why", required=True)
    one.add_argument("--evidence", action="append", default=[],
                     help="a file the corrected value was read from (repeatable)")
    one.set_defaults(func=do_measure)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "subcommand", None):
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    try:
        document = args.func(args)
    except Usage as exc:
        sys.stderr.write("runner.py: %s\n" % exc)
        return EXIT_USAGE
    except Missing as exc:
        sys.stderr.write("runner.py: %s\n" % exc)
        return EXIT_MISSING
    except Failure as exc:
        sys.stderr.write("runner.py: %s\n" % exc)
        return EXIT_FAIL
    except KeyboardInterrupt:
        sys.stderr.write("runner.py: interrupted\n")
        return EXIT_FAIL
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True, default=str) + "\n")
    # E10-68 defect 3: a subcommand that finished but whose WORK failed says so in its exit
    # status without breaking A7a's one-JSON-document-on-stdout rule. `campaign start` sets
    # it when a lane stopped on a runner error.
    if isinstance(document, dict) and document.get(FAIL_EXIT_KEY):
        sys.stderr.write("runner.py: %s\n" % document[FAIL_EXIT_KEY])
        return EXIT_FAIL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
