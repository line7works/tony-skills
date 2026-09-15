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
import time

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
PILOT_ROOT = os.path.join(os.path.expanduser("~"), ".local", "share", "skills-v2-pilot")
CAMPAIGN_ROOT = os.path.join(PILOT_ROOT, "e10")

HARNESSES = ("claude-code", "codex", "opencode")
CONDITIONS = ("available", "absent")
HOMES = ("available", "absent", "routing")
# E10-13: the five v1 back-half stations the routing profile blocks.
BLOCKED_PLUGINS = ("signoff", "recheck", "vertical", "inspect", "ship")

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
PATH_BINARIES = ("claude", "codex", "node", "uv", "git", "python3")
PATH_TAIL = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")

# The credential shapes `scan` looks for (the OpenCode scanner's shapes plus JWT and sk-).
CREDENTIAL_SHAPES = (
    ("openrouter-key", re.compile(r"sk-or-v1-[0-9a-f]{32,}")),
    ("provider-key", re.compile(r"sk-[A-Za-z0-9_-]{40,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
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


def tree_sha256_of(root):
    """`<path>\\0<sha256>\\n` over every file under root, sorted (the fixturelib shape)."""
    entries = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                digest = sha256_hex(os.readlink(full).encode("utf-8"))
            else:
                with open(full, "rb") as handle:
                    digest = sha256_hex(handle.read())
            entries.append("%s\0%s\n" % (rel, digest))
    entries.sort()
    return sha256_hex("".join(entries).encode("utf-8"))


def run_cmd(argv, env=None, cwd=None, stdin=None, timeout=None, label=None, stdout_path=None):
    """One child process: its status, its streams, its wall time.

    Never raises on a non-zero status; the caller decides. A timeout terminates the child's
    own process group (E10-14) after collecting whatever it wrote.

    `stdout_path` sends the child's stdout to that file instead of a pipe. Measured
    2026-09-15: `opencode debug skill` writes exactly 65,536 bytes into a pipe and the whole
    67,934 into a file, so its catalog capture goes through a file and the record is complete.
    """
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
        message = "%s: %s" % (argv[0], exc)
        sys.stderr.write(message + "\n")
        return {"argv": argv, "label": label, "exit": 127, "timed_out": False,
                "wall_seconds": 0.0, "stdout": "", "stderr": message,
                "started_at": now_iso(), "ended_at": now_iso(), "binary_missing": True}
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
        listed = run_cmd([sys.executable, build, "--list"], env=os.environ.copy(), label="list")
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
            listed = run_cmd([sys.executable, build, "--list"], env=os.environ.copy(), label="list")
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

    def trial_dir(self, trial_id):
        return os.path.join(self.trials, trial_id)

    def records(self, name):
        return os.path.join(self.root, "records", name)

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
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(document, sort_keys=True) + "\n")

    def interruption(self, trial_id, observed, action):
        self.append_jsonl(
            self.interruptions,
            {"trial": trial_id, "at": now_iso(), "observed": observed, "did": action},
        )

    def note(self, text):
        ensure_dir(self.root)
        with open(self.log, "a", encoding="utf-8") as handle:
            handle.write("%s %s\n" % (now_iso(), text))


def pilot_home(harness, home):
    """The pilot home for one setup and one of the three homes of E10-3 and E10-13.

    `available` is the home E9 built and closed; `absent` and `routing` are the second and
    third homes beside it under the same pilot root.
    """
    if home not in HOMES:
        raise Usage("home must be one of %s" % ", ".join(HOMES))
    base = os.path.join(PILOT_ROOT, harness)
    if harness == "claude-code":
        return base if home == "available" else os.path.join(base, home)
    if harness == "codex":
        return os.path.join(base, "home") if home == "available" else os.path.join(base, "homes", home)
    if harness == "opencode":
        return base if home == "available" else os.path.join(base, home)
    raise Usage("unknown harness %r" % harness)


# --------------------------------------------------------------------------- stage (E10-6)

STAGE_EXCLUDE_DIRS = (".git", "__pycache__", ".venv", "node_modules")


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
    copied = 0
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
                link = os.readlink(source)
                dest = os.path.join(target, name)
                if os.path.lexists(dest):
                    os.unlink(dest)
                os.symlink(link, dest)
            else:
                shutil.copy2(source, os.path.join(target, name))
            copied += 1
    staged_plugin = os.path.join(campaign.stage, "plugins", "recheck-v2")
    leaked = sorted(
        os.path.relpath(p, campaign.stage)
        for p in glob.glob(os.path.join(staged_plugin, "**", "answer-key"), recursive=True)
        + glob.glob(os.path.join(staged_plugin, "**", "held-out"), recursive=True)
        + glob.glob(os.path.join(staged_plugin, "evals"))
    )
    identity = run_cmd(
        ["uv", "run", os.path.join(SKILL_DIR, "scripts", "recheck.py"), "skill-identity"],
        env=campaign.env(),
    )
    content_sha = None
    if identity["exit"] == 0:
        try:
            content_sha = json.loads(identity["stdout"])["content_sha256"]
        except (ValueError, KeyError):
            content_sha = None
    document = {
        "campaign": campaign.root,
        "checkout": REPO_ROOT,
        "commit": commit["stdout"].strip(),
        "staged_at": now_iso(),
        "stage": campaign.stage,
        "files_copied": copied,
        "plugin_tree_sha256": tree_sha256_of(staged_plugin),
        "evals_excluded": True,
        "answer_key_or_held_out_in_stage": leaked,
        "canonical_content_sha256": content_sha,
        "skill_identity_exit": identity["exit"],
    }
    if leaked:
        raise Failure("the stage still holds %s" % ", ".join(leaked))
    write_json(campaign.stage_json, document)
    campaign.note("stage %s at %s" % (campaign.stage, document["commit"]))
    return document


# --------------------------------------------------------------------------- harness adapters
#
# One class per setup. Each knows: how to install its three homes from the staged copy, what
# environment its own launcher needs for itself, how to launch one headless session, and how
# to read the harness's own record for the model, the effort, the cost, the condition witness
# and the activation marker (the delivery marker each E9 profile section 8 names).


class Setup(object):
    harness = None
    name = None

    def __init__(self, campaign, stage=None, name=None):
        self.campaign = campaign
        self.stage = stage or campaign.stage
        self.name = name or self.harness

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
        return pilot_home(self.harness, condition)

    def setup_tree_sha256(self):
        return tree_sha256_of(self.setup_dir)

    # ---- the launcher's own variables (E10-7: "the variables the setup's own launcher sets
    # for itself" are the home pointers each script documents)
    def launch_env(self, condition):
        raise NotImplementedError

    def install(self, condition, fake=None):
        raise NotImplementedError

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None):
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
        steps = [run_cmd(["sh", self.script("install.sh"), "--pilot-home", home], env=env,
                         label="install.sh")]
        config = os.path.join(home, "config")
        removed, added = [], []
        if condition == "absent":
            # E10-3: the removal uses the harness's own mechanism. `install.sh` installs
            # recheck-v2 unconditionally and takes no flag to skip it, so the absent home is
            # the installed home with the plugin uninstalled by `claude plugin uninstall`
            # (labelled in the record: removed after install, not never-installed).
            steps.append(run_cmd(
                ["claude", "plugin", "uninstall", "recheck-v2@tony-skills"],
                env=dict(env, CLAUDE_CONFIG_DIR=config), label="uninstall recheck-v2"))
            removed.append("recheck-v2@tony-skills (claude plugin uninstall)")
            # Measured on 2.1.272: the uninstall reports success and drops the plugin from
            # `claude plugin list`, and LEAVES its cache directory on disk, so the absent
            # home would still hold the skill files that E10-3 forbids. The cache entry the
            # harness left is removed here and named in the record.
            left = sorted(glob.glob(os.path.join(config, "plugins", "cache", "*",
                                                 "recheck-v2")))
            for path in left:
                rmtree(path)
                removed.append(os.path.relpath(path, home)
                               + " (cache entry left behind by `claude plugin uninstall`)")
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

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None):
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
        return run_cmd(argv, env=env, timeout=timeout, label="launch.sh")

    # ---- records
    def _launch_json(self, out_dir):
        path = os.path.join(out_dir, "launch.json")
        return read_json(path) if os.path.isfile(path) else {}

    def model_record(self, out_dir):
        """Claude Code: the init event's `model`, and the transcript's own `message.model`
        plus `effort` on the last non-sidechain assistant record (profile section 2).

        A compaction resume (`claude -p --resume`) is not launched by `launch.sh`, so it writes
        no `launch.json` and copies no transcript; its own stream-json trace carries the same
        `assistant` records, and is read as the third source.
        """
        launch = self._launch_json(out_dir)
        model_id, effort, source = None, None, None
        for name, label in (("transcript.jsonl", "transcript.jsonl assistant record "
                                                 "message.model"),
                            ("trace.jsonl", "trace.jsonl assistant record message.model")):
            for record in jsonl_lines(os.path.join(out_dir, name)):
                if record.get("type") != "assistant" or record.get("isSidechain"):
                    continue
                message = record.get("message") or {}
                if message.get("model") and message["model"] != "<synthetic>":
                    model_id = message["model"]
                    effort = record.get("effort", effort)
                    source = label
            if model_id:
                break
        if model_id is None and launch.get("model"):
            model_id, source = launch["model"], "trace.jsonl init event model"
        return {"id": model_id, "effort": effort, "source": source,
                "init_model": launch.get("model") or self._init_model(out_dir)}

    def _init_model(self, out_dir):
        for record in jsonl_lines(os.path.join(out_dir, "trace.jsonl")):
            if record.get("type") == "system" and record.get("subtype") == "init":
                return record.get("model")
        return None

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
        launch = self._launch_json(out_dir)
        skills = launch.get("skills")
        plugins = launch.get("plugins")
        present = None
        if isinstance(skills, list):
            present = any("recheck-v2" in json.dumps(s) for s in skills)
        return {
            "condition": condition,
            "witness": {"skills": skills, "plugins": plugins},
            "recheck_v2_in_catalog": present,
            "source": "the session's own init event (launch.json skills/plugins)",
        }

    def activation(self, out_dir):
        """The delivery marker of profile section 8: the body arrives as one `user` record the
        harness flags `isSynthetic` in the trace, after a `Skill` tool call."""
        skill_calls, delivered = [], []
        for index, record in enumerate(jsonl_lines(os.path.join(out_dir, "trace.jsonl")), 1):
            message = record.get("message") or {}
            if record.get("type") == "assistant" and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use" \
                            and block.get("name") == "Skill":
                        target = (block.get("input") or {}).get("skill")
                        skill_calls.append({"line": index, "skill": target})
            if record.get("type") == "user" and record.get("isSynthetic"):
                delivered.append({"line": index, "bytes": len(json.dumps(message.get("content")))})
        activated = any((c.get("skill") or "").startswith("recheck-v2") for c in skill_calls)
        return {
            "activated": activated,
            "marker": {"skill_tool_calls": skill_calls, "delivered_body_records": delivered},
            "profile_section": "adapters/claude-code/profile.md section 8 (the delivered body "
                               "as one user record flagged isSynthetic in the trace, after the "
                               "Skill tool call)",
        }


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


class CodexSetup(Setup):
    harness = "codex"

    def launch_env(self, condition):
        return {"RECHECK_CODEX_HOME": self.home(condition)}

    def install(self, condition, fake=None):
        """`setups/codex/install.sh` takes no arguments and derives its home from `$HOME`.

        So only the `available` home is installed by the script. The other two homes are made
        the way the script makes its own comparison homes (`homes/plugin-only`,
        `homes/host-only`): a copy of the installed home with the absolute paths rewritten,
        then the skill removed by the harness's own mechanism (`codex plugin remove` plus the
        host-skill folder gone) for `absent`, or the extra plugins added for `routing`.
        Labelled in the record: `derived_from_available`, not a second `install.sh` run.
        """
        base = self.home("available")
        env = self.campaign.env()
        steps = []
        if condition == "available":
            steps.append(run_cmd(["sh", self.script("install.sh")], env=env, label="install.sh"))
            return {"home": base, "condition": condition, "derived_from_available": False,
                    "steps": [_step_summary(s) for s in steps]}
        if not os.path.isdir(base):
            raise Missing("install the codex `available` home before %r" % condition)
        home = self.home(condition)
        if os.path.isdir(home):
            rmtree(home)
        ensure_dir(os.path.dirname(home))
        shutil.copytree(base, home, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "sessions"))
        # The credential stays one file: every derived home points at the base home's store.
        for auth in [os.path.join(home, "auth.json"), os.path.join(home, "child", "auth.json")]:
            if os.path.lexists(auth):
                os.unlink(auth)
            ensure_dir(os.path.dirname(auth))
            os.symlink(os.path.join(base, "auth.json"), auth)
        for path in [os.path.join(home, "config.toml")] + \
                glob.glob(os.path.join(home, "plugins", "**", "*.json"), recursive=True) + \
                [os.path.join(home, "child", "config.toml")]:
            if os.path.isfile(path):
                text = read_text(path) or ""
                write_text(path, text.replace(base, home))
        ensure_dir(os.path.join(home, "child", "uv-cache"))
        removed, added = [], []
        if condition == "absent":
            host_skill = os.path.join(home, "skills", "recheck-v2")
            if os.path.exists(host_skill):
                rmtree(host_skill)
                removed.append("skills/recheck-v2 (the host-skill copy)")
            # Measured on codex-cli 0.154.0: a bare name is refused with "plugin requires
            # --marketplace unless passed as <plugin>@<marketplace>", so the qualified form is
            # what the harness's own removal takes.
            steps.append(run_cmd(["codex", "plugin", "remove", "recheck-v2@tony-skills"],
                                 env=dict(env, CODEX_HOME=home), label="plugin remove"))
            # A plugin cache entry the harness's own remove left behind is a finding, not a
            # thing the runner deletes by hand: the record says what is still there.
            left = sorted(glob.glob(os.path.join(home, "plugins", "**", "recheck-v2"),
                                    recursive=True))
            if left:
                for path in left:
                    rmtree(path)
                    removed.append(os.path.relpath(path, home) + " (cache entry left by `plugin remove`)")
        if condition == "routing":
            manifest = read_json(os.path.join(self.stage, ".claude-plugin", "marketplace.json"))
            for plugin in [p["name"] for p in manifest.get("plugins", [])]:
                if plugin in BLOCKED_PLUGINS or plugin == "recheck-v2":
                    continue
                steps.append(run_cmd(
                    ["codex", "plugin", "add", "%s@tony-skills" % plugin, "--json"],
                    env=dict(env, CODEX_HOME=home), label="plugin add %s" % plugin))
                added.append(plugin)
        return {"home": home, "condition": condition, "derived_from_available": True,
                "removed": removed, "added": added, "steps": [_step_summary(s) for s in steps]}

    def verify(self, condition):
        home = self.home(condition)
        env = self.campaign.env(extra={"RECHECK_CODEX_HOME": home})
        return run_cmd(["sh", self.script("verify-install.sh")], env=env, label="verify-install.sh")

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None):
        home = self.home(condition)
        env = self.campaign.env(extra={"RECHECK_CODEX_HOME": home})
        argv = ["sh", fake or self.script("launch.sh"), prompt_file, workspace, out_dir]
        return run_cmd(argv, env=env, timeout=timeout, label="launch.sh")

    def catalog(self, condition, out_dir):
        """`codex plugin list` under the condition's home: the harness's own catalog record."""
        home = self.home(condition)
        env = self.campaign.env(extra={"CODEX_HOME": home})
        if not os.path.isdir(home):
            return {"kind": "codex plugin list", "exit": None, "record": None,
                    "note": "no codex home at %s, so this home recorded no catalog" % home}
        step = run_cmd(["codex", "plugin", "list"], env=env, label="plugin list")
        write_text(os.path.join(out_dir, "catalog.txt"), step["stdout"] + step["stderr"])
        return {"kind": "codex plugin list", "exit": step["exit"], "record": step["stdout"]}

    # ---- records
    def _rollout(self, out_dir):
        return jsonl_lines(os.path.join(out_dir, "rollout.jsonl"))

    def model_record(self, out_dir):
        """Codex: `turn_context` in the rollout carries `model` and `effort` (E9 section 7)."""
        model_id, effort, source = None, None, None
        for record in self._rollout(out_dir):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            kind = record.get("type") or payload.get("type")
            if kind == "turn_context":
                model_id = payload.get("model", model_id)
                effort = payload.get("effort", effort)
                source = "rollout.jsonl turn_context"
            elif kind == "session_meta" and model_id is None:
                model_id = payload.get("model", model_id)
                source = source or "rollout.jsonl session_meta"
        return {"id": model_id, "effort": effort, "source": source}

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
        """The session's own catalog: the developer message the rollout records at the start."""
        names, source = None, None
        for record in self._rollout(out_dir):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            blob = json.dumps(payload)
            if payload.get("type") == "message" and "skill" in blob.lower() and names is None:
                names = sorted(set(re.findall(r"^\s*-?\s*([a-z0-9][a-z0-9-]{2,40})\b", blob)))
                source = "rollout.jsonl the first developer message carrying the skill catalog"
                break
        catalog_file = read_text(os.path.join(out_dir, "catalog.txt")) or ""
        return {
            "condition": condition,
            "witness": {"catalog_txt": catalog_file[:4000], "catalog_message_names": names},
            "recheck_v2_in_catalog": ("recheck-v2" in catalog_file) if catalog_file else None,
            "source": source or "codex plugin list under the condition's home (catalog.txt)",
        }

    def activation(self, out_dir):
        """Codex profile section 8: implicit selection is a file read of the installed
        `SKILL.md`; the explicit `$name` route injects a `<skill>` user message."""
        reads, injected = [], []
        for index, record in enumerate(self._rollout(out_dir), 1):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            blob = json.dumps(payload)
            if "recheck-v2/SKILL.md" in blob:
                item = payload.get("item") or {}
                command = item.get("command") or payload.get("command")
                if command or payload.get("type") in ("custom_tool_call", "function_call"):
                    reads.append({"line": index, "command": json.dumps(command)[:240]
                                  if command else payload.get("name")})
            if "<skill" in blob and "recheck-v2" in blob:
                injected.append({"line": index, "bytes": len(blob)})
        return {
            "activated": bool(reads or injected),
            "marker": {"installed_skill_reads": reads[:6], "injected_skill_messages": injected[:4]},
            "profile_section": "adapters/codex/profile.md section 8 (implicit selection requires "
                               "a file read of the installed SKILL.md; the explicit route "
                               "injects a <skill> user message)",
        }


# ------------------------------------------------------------------ OpenCode


class OpenCodeSetup(Setup):
    harness = "opencode"

    def __init__(self, campaign, stage=None, name=None, model="qwen"):
        Setup.__init__(self, campaign, stage=stage, name=name)
        self.model = model

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
        credential = os.environ.get(INSTALL_CREDENTIAL)
        extra = {"RECHECK_OPENCODE_SETUP": home}
        if credential:
            extra[INSTALL_CREDENTIAL] = credential
        env = self.campaign.env(extra=extra)
        model = {"qwen": "openrouter/qwen/qwen3.8-flash",
                 "deepseek": "openrouter/deepseek/deepseek-v4.1-flash"}.get(self.model, self.model)
        steps = [run_cmd(["sh", self.script("install.sh"), "--setup", home, "--model", model],
                         env=env, label="install.sh")]
        removed, added = [], []
        if condition == "absent":
            target = os.path.join(self.skill_dir(condition), "recheck-v2")
            if os.path.isdir(target):
                rmtree(target)
                removed.append("xdg-config/opencode/skill/recheck-v2")
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
                "removed": removed, "added": sorted(set(added)),
                "steps": [_step_summary(s) for s in steps]}

    def verify(self, condition):
        home = self.home(condition)
        env = self.campaign.env(extra={"RECHECK_OPENCODE_SETUP": home})
        return run_cmd(["sh", self.script("verify-install.sh"), "--setup", home], env=env,
                       label="verify-install.sh")

    def launch(self, condition, prompt_file, workspace, out_dir, timeout, extra=None, fake=None):
        home = self.home(condition)
        env = self.campaign.env(extra={
            "RECHECK_OPENCODE_SETUP": home,
            "RECHECK_OPENCODE_TIMEOUT": str(int(timeout)) if timeout else "900",
        })
        model = (extra or {}).get("model") or self.model
        argv = ["sh", fake or self.script("launch.sh"), model, prompt_file, workspace, out_dir]
        agent = (extra or {}).get("agent")
        if agent:
            argv += ["--agent", agent]
        return run_cmd(argv, env=env, timeout=(timeout + 120) if timeout else None,
                       label="launch.sh")

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
        The store has no reasoning-effort field on 1.18.31, so `effort` is null, never a
        label (E10-19)."""
        session = self._session(out_dir)
        model_id, provider, source = None, None, None
        for record in session.get("records", []):
            data = record.get("data") or {}
            if data.get("role") == "assistant" and data.get("modelID"):
                model_id, provider = data["modelID"], data.get("providerID")
                source = "session.json records[].data.modelID (the session store's message rows)"
        return {"id": ("%s/%s" % (provider, model_id)) if provider and model_id else model_id,
                "model_id": model_id, "provider": provider, "effort": None, "source": source}

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
            "source": "opencode debug skill under the condition's home (the loader's own "
                      "catalog record; this harness writes no init event into the session)",
        }

    def activation(self, out_dir):
        """OpenCode profile section 8: the native `skill` tool call whose output is the
        `<skill_content name="recheck-v2">` block."""
        calls = []
        for record in self._session(out_dir).get("records", []):
            for part in record.get("parts") or []:
                data = part.get("data") or {} if isinstance(part, dict) else {}
                if data.get("tool") == "skill":
                    state = data.get("state") or {}
                    calls.append({
                        "call_id": data.get("callID"),
                        "input": state.get("input"),
                        "status": state.get("status"),
                        "output_chars": len(state.get("output") or ""),
                    })
        for record in jsonl_lines(os.path.join(out_dir, "trace.json")):
            part = record.get("part") or {}
            if part.get("tool") == "skill" and not calls:
                calls.append({"call_id": part.get("callID"), "input": (part.get("state") or {}).get("input"),
                              "status": (part.get("state") or {}).get("status"),
                              "output_chars": len((part.get("state") or {}).get("output") or "")})
        activated = any((c.get("input") or {}).get("name") == "recheck-v2" for c in calls)
        return {
            "activated": activated,
            "marker": {"skill_tool_calls": calls},
            "profile_section": "adapters/opencode/profile.md section 8 (the native skill tool "
                               "call returning the <skill_content name=\"recheck-v2\"> block)",
        }

    def store_separation_witness(self, out_dir):
        """E10-17: whether the verifier child's rows show a read of the driving session's rows."""
        session = self._session(out_dir)
        driving = session.get("session_id")
        reads = []
        for record in session.get("records", []):
            for part in record.get("parts") or []:
                data = part.get("data") or {} if isinstance(part, dict) else {}
                state = data.get("state") or {}
                blob = json.dumps(state.get("input") or {})
                if "opencode.db" in blob or (driving and driving in blob):
                    reads.append({"tool": data.get("tool"), "input": blob[:200]})
        return {"driving_session": driving, "reads_of_the_driving_store": reads,
                "measured": True, "note": "E10-17: measured, not fixed"}


SETUP_CLASSES = {"claude-code": ClaudeCodeSetup, "codex": CodexSetup, "opencode": OpenCodeSetup}


def make_setup(campaign, spec):
    """One setup object from a plan entry (`{name, harness, model}`) or a bare harness name."""
    if isinstance(spec, str):
        spec = {"name": spec, "harness": spec}
    harness = spec.get("harness") or spec["name"]
    cls = SETUP_CLASSES.get(harness)
    if cls is None:
        raise Usage("unknown harness %r (one of %s)" % (harness, ", ".join(HARNESSES)))
    if cls is OpenCodeSetup:
        return cls(campaign, name=spec["name"], model=spec.get("model", "qwen"))
    return cls(campaign, name=spec["name"])


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
            results.append(record)
            campaign.note("install %s %s -> %s" % (setup.name, condition, record["home"]))
    document = {"campaign": campaign.root, "installs": results}
    write_json(campaign.records("install-%s.json" % time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())),
               document)
    failed = [r for r in results
              if any(s["exit"] not in (0, None) for s in r["steps"]) or r["home_leak_scan"]]
    document["ok"] = not failed
    if failed:
        raise Failure("install failed for %s"
                      % ", ".join("%s/%s" % (r["setup"], r["condition"]) for r in failed))
    return document


def do_verify(args):
    campaign = Campaign(args.campaign)
    campaign.ensure()
    fresh = run_cmd(["uv", "run", os.path.join(SKILL_DIR, "scripts", "recheck.py"),
                     "skill-identity"], env=campaign.env())
    canonical = None
    if fresh["exit"] == 0:
        try:
            canonical = json.loads(fresh["stdout"])["content_sha256"]
        except (ValueError, KeyError):
            canonical = None
    plan = _optional_plan(campaign)
    rows = []
    for setup in _selected_setups(campaign, plan, args.setup):
        for condition in (args.home and [args.home]) or list(HOMES):
            home = setup.home(condition)
            if not os.path.isdir(home):
                rows.append({"setup": setup.name, "condition": condition, "home": home,
                             "present": False, "ok": None})
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
            rows.append({
                "setup": setup.name, "condition": condition, "home": home, "present": True,
                "verify_exit": step["exit"],
                "verify_ok": (document or {}).get("ok"),
                "installed_content_sha256": installed_sha,
                "canonical_content_sha256": canonical,
                "content_sha256_equal": (installed_sha == canonical) if installed_sha else None,
                "findings": (document or {}).get("findings"),
                "home_leak_scan": home_leak_scan(home),
                "no_installed_skill": installed_sha is None,
                "expected_no_installed_skill": expected_absent,
                "ok": (installed_sha is None and not home_leak_scan(home)) if expected_absent
                      else (installed_sha == canonical and (document or {}).get("ok") is True),
                "stdout_tail": step["stdout"][-1500:] if document is None else None,
                "stderr_tail": step["stderr"][-1500:],
            })
    document = {"campaign": campaign.root, "canonical_content_sha256": canonical, "rows": rows}
    document["ok"] = all(r.get("ok") is not False for r in rows if r.get("present"))
    write_json(campaign.records("verify-%s.json" % time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())),
               document)
    return document


# --------------------------------------------------------------------------- probe-env (E10-7)

PROBE_PROMPT = (
    "Run exactly this one command and reply with its output and nothing else:\n"
    "env | cut -d= -f1 | sort\n"
)


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


def do_probe_env(args):
    campaign = Campaign(args.campaign)
    campaign.ensure()
    campaign.staged()
    plan = _optional_plan(campaign)
    rows = []
    for setup in _selected_setups(campaign, plan, args.setup):
        for condition in (args.home and [args.home]) or list(HOMES):
            out_dir = os.path.join(campaign.root, "probes", "%s-%s" % (setup.name, condition))
            if os.path.exists(out_dir):
                if not args.refresh:
                    raise Usage("%s already holds a probe record; pass --refresh to replace it"
                                % out_dir)
                rmtree(out_dir)
            ensure_dir(os.path.dirname(out_dir))
            workspace = os.path.join(campaign.root, "probes", "workspace")
            _empty_git_workspace(campaign, workspace)
            prompt = os.path.join(campaign.root, "probes", "env-probe.txt")
            write_text(prompt, PROBE_PROMPT)
            passed = sorted(campaign.env(extra=setup.launch_env(condition)))
            step = setup.launch(condition, prompt, workspace, out_dir, timeout=args.timeout)
            names = _probe_names(out_dir)
            banned = sorted(n for n in names if BANNED_ENV_RE.match(n))
            # E10-7's gate is on what the RUNNER passes. Measured 2026-09-15: Claude Code sets
            # `CLAUDECODE` and eight `CLAUDE_CODE_*` names (`CLAUDE_CODE_MESSAGING_TOKEN`
            # among them) in its own tool shells, below the boundary the runner controls, so a
            # gate on "any banned name in the record" would fail every Claude Code campaign.
            # The two are split, and the gate is the first.
            from_runner = sorted(n for n in banned if n in passed)
            from_harness = sorted(n for n in banned if n not in passed)
            rows.append({
                "setup": setup.name, "condition": condition, "out_dir": out_dir,
                "launch_exit": step["exit"], "wall_seconds": step["wall_seconds"],
                "names_seen": names,
                "names_the_runner_passed": passed,
                "banned_names_seen": banned,
                "banned_the_runner_passed": from_runner,
                "banned_the_harness_set_for_its_own_tool_shells": from_harness,
                "ok": not from_runner,
                "model": setup.model_record(out_dir), "cost": setup.cost_record(out_dir),
            })
            campaign.note("probe-env %s %s runner-banned=%s harness-set=%s"
                          % (setup.name, condition, from_runner, from_harness))
    document = {"campaign": campaign.root, "allowlist": list(ALLOWED_ENV), "probes": rows}
    document["ok"] = all(r["ok"] for r in rows)
    write_json(os.path.join(campaign.root, "probes", "probe-env.json"), document)
    return document


def _probe_names(out_dir):
    """Every environment-variable-shaped name the probe session's own record printed."""
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
    """The full E10 campaign plan (E10-1 to E10-5, E10-12 to E10-14), the README's example."""
    return {
        "plan_version": 1,
        "campaign_id": campaign_id,
        "run_date": read_json(TRIAL_DEFAULTS)["run_date"],
        "setups": [
            {"name": "claude-code", "harness": "claude-code"},
            {"name": "codex", "harness": "codex"},
            {"name": "opencode", "harness": "opencode", "model": "qwen"},
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
    lanes = {}
    for spec in plan["setups"]:
        ids = []
        for entry in entry_ids:
            for rep in range(1, plan["routing"]["repetitions"] + 1):
                ids.append(routing_trial_id(spec["name"], entry, rep))
        lanes[spec["name"]] = ids
    return lanes


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


def do_plan(args):
    campaign = Campaign(args.campaign)
    campaign.ensure()
    if os.path.isfile(campaign.campaign_json) and not args.refresh:
        raise Usage("%s already holds campaign.json; pass --refresh to replace it (E9-34: a "
                    "record is never overwritten)" % campaign.root)
    plan = (read_json(args.plan, "plan.json") if args.plan
            else default_plan(os.path.basename(campaign.root)))
    for field in ("setups", "cases", "conditions", "repetitions", "timeouts"):
        if field not in plan:
            raise Usage("plan.json has no %r" % field)
    index = lane_index()
    unknown = [c for c in plan["cases"] if c not in index]
    if unknown:
        raise Usage("plan.json names cases no generator lists: %s" % ", ".join(unknown))
    bad = [c for c in plan["conditions"] if c not in CONDITIONS]
    if bad:
        raise Usage("plan.json names conditions outside %s: %s" % (CONDITIONS, bad))
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
        "continuation_order": continuation_order(plan) if plan.get("continuation") else {},
    })
    counts = {
        "comparison": sum(len(v) for v in document["order"].values()),
        "routing": sum(len(v) for v in document["routing_order"].values()),
        "continuation": sum(len(v) for v in document["continuation_order"].values()),
    }
    counts["total"] = sum(counts.values())
    document["counts"] = counts
    write_json(campaign.campaign_json, document)
    campaign.note("plan %d trials" % counts["total"])
    return {"campaign": campaign.root, "campaign_json": campaign.campaign_json,
            "counts": counts, "order": document["order"],
            "routing_entries": len(entry_ids)}


def _optional_plan(campaign):
    try:
        return campaign.plan()
    except Missing:
        return None


def _selected_setups(campaign, plan, wanted):
    specs = (plan or {}).get("setups") or [{"name": h, "harness": h} for h in HARNESSES]
    if wanted:
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


def heldout_entry_ids():
    """The sealed set's ids, printed by a subprocess that prints ids and nothing else."""
    path, _ = heldout_file()
    step = run_cmd([sys.executable, "-c", HELDOUT_ID_SCRIPT, path], env=os.environ.copy(),
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
                   env=os.environ.copy(), label="held-out text")
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
PROMPT_TEMPLATE = (
    "recheck slice {slice} of {build_doc} in {workspace}: a fresh verifier proves each named "
    "BLOCKER or MAJOR fix on the punch list landed, then move the slice's card; run date "
    "{run_date}.\n"
    "\n"
    "Use the run directory {run_dir}.\n"
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
            return {"setup": name, "case": case, "condition": match.group("condition"),
                    "rep": int(match.group("rep"))}
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


# The adapter's run root (`references/pilot-contract.md` section 2 and every profile's section
# 3) is `${TMPDIR}/recheck-v2`, and three installed things are written for exactly that path:
# the Claude launcher's `--add-dir`, the OpenCode `external_directory` allow rule the install
# writes from its own TMPDIR (E9-27), and the adapter helpers' own default. E10-4 also says the
# prompt "never names recheck-v2", and the prompt must name the run directory, so the two rules
# collide. The runner keeps the working path and records the breach; `plan.json` may set
# `run_root_name` to a neutral segment once the setups allow one (the report names the edit).
DEFAULT_RUN_ROOT_NAME = "runs"  # E10-22: the setups name the run root ${TMPDIR}/runs since a55da08


def run_root_of(campaign, plan, trial=None):
    """The run root, with an opaque per-trial segment.

    E10-5 wants a fresh run directory per trial, and E7 fixes the run id at `<case id>-run`,
    so two trials on one case would otherwise mint the same absolute path and the second would
    destroy the first (found in the dry run: a later trial's rebuild left the earlier trial's
    grade validating against the wrong directory). The segment is a digest of the trial id, so
    the path the model sees names no setup and no condition.
    """
    root = os.path.join(campaign.tmp, plan.get("run_root_name") or DEFAULT_RUN_ROOT_NAME)
    if trial:
        root = os.path.join(root, hashlib.sha256(trial.encode("utf-8")).hexdigest()[:12])
    return root


def run_root_note(plan):
    name = plan.get("run_root_name") or DEFAULT_RUN_ROOT_NAME
    return {
        "run_root_name": name,
        "prompt_names_the_skill": name == "recheck-v2",
        "reason": ("the run root is ${TMPDIR}/runs (E10-22: setups/claude-code/launch.sh's "
                   "--add-dir and setups/opencode/install.sh's external_directory allow rule "
                   "are written for that segment since a55da08), so the run-directory path "
                   "names no skill; E10-4 holds." if name != "recheck-v2" else
                   "the run root segment is recheck-v2, so the run-directory path in the prompt "
                   "names the skill: E10-4's 'the prompt never names recheck-v2' is breached by "
                   "the path alone and is recorded here; the Claude launcher's --add-dir and the "
                   "OpenCode external_directory allow rule must be written for the same segment "
                   "or every write outside the workspace fails."),
    }


def prepare_run_dir(campaign, case_dir, run_root, run_id):
    """The run directory and the canonical result schema copied into it (E10-4)."""
    run_dir = os.path.join(run_root, run_id)
    if os.path.exists(run_dir):
        rmtree(run_dir)
    ensure_dir(run_dir)
    shutil.copy2(os.path.join(SKILL_DIR, "references", "result.schema.json"),
                 os.path.join(run_dir, "result.schema.json"))
    return run_dir


def trial_prompt(fixture, workspace, run_dir, run_date):
    """The prompt, from the fixture's own seeded input (facts, never an outcome)."""
    seeded = read_json(os.path.join(fixture["case_dir"], "input.json"), "the seeded input")
    target = seeded.get("target") or {}
    build_doc = target.get("build_doc") or "docs/punch-list.md"
    slice_name = target.get("slice") or "A"
    return PROMPT_TEMPLATE.format(slice=slice_name, build_doc=build_doc, workspace=workspace,
                                  run_dir=run_dir, run_date=run_date), seeded


def validate_result(campaign, result, seeded_input, run_dir, workspace):
    argv = ["uv", "run", os.path.join(SKILL_DIR, "scripts", "validate-result.py"), result]
    if seeded_input:
        argv += ["--input", seeded_input]
    argv += ["--run-dir", run_dir, "--workspace", workspace, "--strict"]
    step = run_cmd(argv, env=campaign.env(), label="validate-result.py --strict")
    text = (step["stdout"] or "") + ("\n" if step["stdout"] and not step["stdout"].endswith("\n") else "")
    text += "exit %s\n" % step["exit"]
    return step, text


def scan_paths(paths, exempt=()):
    """The credential scan (E10-9's `scan`): shapes only, offsets only, never a value."""
    hits, scanned, skipped_binary = [], 0, []
    exempt_real = {os.path.realpath(p) for p in exempt}
    for path in paths:
        if not os.path.isfile(path):
            continue
        if os.path.realpath(path) in exempt_real:
            continue
        try:
            with open(path, "rb") as handle:
                blob = handle.read()
        except (IOError, OSError):
            continue
        # A compiled binary is not a record: three identical `sk-`-shaped byte runs inside
        # Codex's own dropped helper binaries were the dry run's only scan hits outside a test.
        # A NUL in the first 8 KiB is the test, and the count of skipped files is reported.
        if b"\x00" in blob[:8192]:
            skipped_binary.append(path)
            continue
        scanned += 1
        text = blob.decode("utf-8", "replace")
        # The shapes overlap (an OpenRouter key is also a `sk-` key), so the most specific
        # shape claims the span and a later shape inside it is not a second hit.
        claimed = []
        for shape, pattern in CREDENTIAL_SHAPES:
            for found in pattern.finditer(text):
                start, end = found.span()
                if any(start >= a and end <= b for a, b in claimed):
                    continue
                claimed.append((start, end))
                hits.append({"file": path, "shape": shape, "offset": start,
                             "length": end - start})
    return {"files_scanned": scanned, "hits": hits,
            "binary_files_skipped": len(skipped_binary),
            "binary_files": sorted(skipped_binary)[:40]}


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


def auth_store_exemptions():
    """The only exemption of E10-9: the setups' own auth stores, by resolved path."""
    stores = []
    for harness in HARNESSES:
        for home in HOMES:
            try:
                base = pilot_home(harness, home)
            except Usage:
                continue
            stores += [os.path.join(base, "auth.json"),
                       os.path.join(base, "child", "auth.json"),
                       os.path.join(base, "xdg-data", "opencode", "auth.json")]
    return [p for p in stores if os.path.exists(p)]


def do_run(args):
    """One comparison trial end to end: build, prompt, launch, collect, validate, scan."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    parts = parse_trial_id(plan, args.trial)
    setup = setup_for(campaign, plan, parts["setup"])
    record = campaign.trial_dir(args.trial)
    attempt = 0
    if os.path.exists(record):
        if not args.attempt_dir:
            raise Usage("%s is a used trial directory (E9-34: a record is never overwritten); "
                        "use `rerun` for another attempt" % record)
        record = args.attempt_dir
        attempt = args.attempt
        if os.path.exists(record):
            raise Usage("%s already exists" % record)
    ensure_dir(record)
    return _one_trial(campaign, plan, setup, parts, record, attempt, args)


def _one_trial(campaign, plan, setup, parts, record, attempt, args):
    started = time.time()
    fixture = build_fixture(campaign, parts["case"], os.path.join(record, "fixture"))
    workspace = os.path.join(fixture["case_dir"], "workspace")
    if not os.path.isdir(workspace):
        raise Failure("the built fixture has no workspace at %s" % workspace)
    run_root = run_root_of(campaign, plan, trial=os.path.basename(record.rstrip("/")))
    run_id = "%s-run" % parts["case"]
    run_dir = prepare_run_dir(campaign, fixture["case_dir"], run_root, run_id)
    prompt, seeded = trial_prompt(fixture, workspace, run_dir, plan["run_date"])
    prompt_path = os.path.join(record, "prompt.txt")
    write_text(prompt_path, prompt)
    harness_dir = os.path.join(record, "harness")
    timeout = plan["timeouts"]["comparison"]
    env_extra = setup.launch_env(parts["condition"])
    step = setup.launch(parts["condition"], prompt_path, workspace, harness_dir, timeout,
                        extra={"plugins": args.plugins} if getattr(args, "plugins", None) else None,
                        fake=getattr(args, "fake_launcher", None))
    catalog = setup.catalog(parts["condition"], harness_dir)
    collected = collect_trial(campaign, setup, parts, record, harness_dir, run_dir, workspace,
                              seeded, step, fixture, attempt, started, env_extra, catalog)
    return collected


def collect_trial(campaign, setup, parts, record, harness_dir, run_dir, workspace, seeded,
                  step, fixture, attempt, started, env_extra, catalog):
    """Everything E10-10 names, written into the trial record."""
    result_src = os.path.join(run_dir, "result.json")
    input_src = os.path.join(run_dir, "input.json")
    chat_src = os.path.join(run_dir, "chat.md")
    absent = not os.path.isfile(result_src)
    if not absent:
        shutil.copy2(result_src, os.path.join(record, "result.json"))
    if os.path.isfile(input_src):
        shutil.copy2(input_src, os.path.join(record, "input.json"))
    if os.path.isfile(chat_src):
        shutil.copy2(chat_src, os.path.join(record, "chat.md"))
    else:
        write_text(os.path.join(record, "chat.md"), read_text(
            os.path.join(harness_dir, "result.txt"),
            read_text(os.path.join(harness_dir, "final.md"), "")) or "")
    model = setup.model_record(harness_dir)
    cost = setup.cost_record(harness_dir)
    activation = setup.activation(harness_dir)
    witness = setup.condition_witness(harness_dir, parts["condition"])
    write_json(os.path.join(record, "model.json"), model)
    write_json(os.path.join(record, "cost.json"), cost)
    validate_step, validate_text = (None, "no result.json: nothing validated\nexit 2\n")
    if not absent:
        # The validator runs against the LIVE run directory the result names, before the copy:
        # `records_written` carries that absolute path, and V3 checks containment under it.
        validate_step, validate_text = validate_result(
            campaign, result_src,
            input_src if os.path.isfile(input_src) else None, run_dir, workspace)
    write_text(os.path.join(record, "validate.txt"), validate_text)
    # the run directory, copied whole after the harness ended and after the validation
    run_copy = os.path.join(record, "run")
    if os.path.isdir(run_dir) and not os.path.exists(run_copy):
        shutil.copytree(run_dir, run_copy, symlinks=True)
    scan = scan_paths(walk_files(record), exempt=auth_store_exemptions())
    write_json(os.path.join(record, "scan.json"), scan)
    status = ("timed_out" if step.get("timed_out") else
              "launch_failed" if step["exit"] not in (0,) and absent else
              "no_result" if absent else "complete")
    command = {
        "trial": os.path.basename(record) if attempt == 0 else None,
        "attempt": attempt,
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
        "run_dir": run_dir,
        "run_root": os.path.dirname(run_dir),
        "run_root_note": run_root_note(campaign.plan()),
        "workspace": workspace,
        "result_absent": absent,
        "absent": absent,
        "status": status,
        "validate_exit": validate_step["exit"] if validate_step else None,
        "scan_hits": len(scan["hits"]),
    }
    if setup.harness == "opencode":
        command["store_separation_witness"] = setup.store_separation_witness(harness_dir)
    write_json(os.path.join(record, "command.json"), command)
    line = {
        "id": command["trial"] or os.path.basename(os.path.dirname(os.path.dirname(record))),
        "attempt": attempt,
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
        campaign.interruption(line["id"], "status %s (exit %s)" % (status, step["exit"]),
                             "kept the attempt and counted it")
    campaign.note("run %s -> %s" % (line["id"], status))
    return {"trial": line["id"], "record": record, "status": status, "exit": step["exit"],
            "wall_seconds": command["wall_seconds"], "model": model, "cost": cost,
            "activated": activation.get("activated"),
            "condition_witness_recheck_v2_in_catalog": witness.get("recheck_v2_in_catalog"),
            "validate_last_line": validate_text.strip().splitlines()[-1],
            "scan_hits": len(scan["hits"])}


# --------------------------------------------------------------------------- grade (E10-11)


def harness_alive_for(record):
    """The grade path refuses to run while a harness process for that trial is alive."""
    for name in ("harness/child.pid", "harness/launch.json"):
        path = os.path.join(record, name)
        if not os.path.isfile(path):
            continue
        pid = None
        if name.endswith("child.pid"):
            try:
                pid = int((read_text(path) or "").strip())
            except ValueError:
                pid = None
        if pid:
            try:
                os.kill(pid, 0)
            except OSError:
                continue
            return pid
    return None


def do_grade(args):
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    if args.all:
        trials = sorted(os.path.basename(p) for p in glob.glob(os.path.join(campaign.trials, "*"))
                        if os.path.isdir(p) and not os.path.basename(p).startswith(("routing-", "cont-")))
    elif args.trial:
        trials = [args.trial]
    else:
        raise Usage("name a trial id or pass --all")
    rows = []
    for tid in trials:
        record = campaign.trial_dir(tid)
        if not os.path.isdir(record):
            raise Missing("no trial record at %s" % record)
        alive = harness_alive_for(record)
        if alive:
            raise Failure("a harness process (pid %s) for %s is still alive; grading waits"
                          % (alive, tid))
        rows.append(grade_one(campaign, plan, tid, record))
    summary = grade_summary(rows)
    if args.summary:
        return {"campaign": campaign.root, "graded": len(rows), "summary": summary,
                "per_trial": summary_rows(rows)}
    return {"campaign": campaign.root, "graded": len(rows), "summary": summary,
            "grades": [{"trial": r["trial"], "grade_path": r["grade_path"]} for r in rows]}


def grade_one(campaign, plan, tid, record):
    """`validate-result.py --strict`, then `match()`, then the metrics of E10-11."""
    command = read_json(os.path.join(record, "command.json"), "command.json")
    case = command["case"]
    entry, stood_in = key_entry(case)
    runs_at = entry.get("runs_at")
    runs_at = runs_at if isinstance(runs_at, list) else [runs_at]
    grade = {
        "trial": tid,
        "case": case,
        "setup": command["setup"],
        "condition": command["condition"],
        "graded_at": now_iso(),
        "key_stand_in": stood_in,
        "key_runs_at": runs_at,
        "key_runs_at_includes_E10": "E10" in runs_at,
        "record": record,
    }
    result_path = os.path.join(record, "result.json")
    if not os.path.isfile(result_path):
        # E10-11: no result grades every metric as `no_result` and counts as a failure of the
        # condition, never as excluded.
        for metric in ("validator", "match", "false_fixed", "dispositions", "evidence_sufficient",
                       "scope_violations", "unauthorized", "interop", "floor_met"):
            grade[metric] = "no_result"
        grade["ok"] = False
        grade["time"] = {"wall_seconds": command.get("wall_seconds")}
        grade["cost"] = read_json(os.path.join(record, "cost.json")) \
            if os.path.isfile(os.path.join(record, "cost.json")) else None
        grade["model"] = read_json(os.path.join(record, "model.json")) \
            if os.path.isfile(os.path.join(record, "model.json")) else None
        write_json(os.path.join(record, "grade.json"), grade)
        return grade
    result = read_json(result_path, "result.json")
    # E10-11 regrades from the record: the run directory the result names is gone by then, so
    # the retained copy stands in and `--run-dir` points at it. The path difference is recorded.
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
    else:
        # E10-10 makes `validate.txt` the record of the validation `run` did against the live
        # run directory. A retained copy cannot pass V3 (the result's `records_written` name
        # absolute paths under the original directory), so the recorded verdict stands and the
        # grade says so rather than manufacturing a failure.
        validator = _recorded_validation(record)
        step = {"exit": validator.get("exit")}
    skipped = validator.get("skipped") or []
    grade["validator"] = {
        "exit": step["exit"], "ok": bool(validator.get("ok")),
        "schema_errors": validator.get("schema") or validator.get("schema_errors") or [],
        "semantic_errors": validator.get("semantic") or validator.get("semantic_errors") or [],
        "skipped": skipped,
        # "a skip under --strict is a failed grade naming the skip"
        "failed_for_a_skip": bool(skipped) and step["exit"] != 0,
        "source": validator.get("source"),
    }
    match = _import_match()
    ok, reasons = match.match(entry.get("expected") or {}, result)
    grade["match"] = {"ok": ok, "reasons": reasons}
    items = result.get("items") or []
    expected_items = ((entry.get("expected") or {}).get("items") or [])
    grade["dispositions"] = _dispositions(items, expected_items)
    grade["false_fixed"] = _false_fixed(grade["dispositions"])
    grade["evidence_sufficient"] = _evidence(items)
    grade["scope_violations"] = _scope_violations(result, record, command)
    grade["unauthorized"] = _unauthorized(record, command)
    grade["interop"] = _interop(result, record)
    grade["time"] = {"wall_seconds": command.get("wall_seconds"),
                     "launch_wall_seconds": command.get("launch_wall_seconds")}
    grade["cost"] = read_json(os.path.join(record, "cost.json"))
    grade["model"] = read_json(os.path.join(record, "model.json"))
    run_block = (result.get("run") or {}).get("model") or {}
    grade["floor_met"] = {"result_run_model": run_block,
                          "model_json_id": (grade["model"] or {}).get("id"),
                          "floor_met": run_block.get("floor_met")}
    grade["must_not"] = entry.get("must_not")
    grade["ok"] = bool(ok and grade["validator"]["ok"] and not grade["false_fixed"]["items"]
                       and not grade["scope_violations"]["all"]
                       and not grade["unauthorized"]["all"])
    write_json(os.path.join(record, "grade.json"), grade)
    return grade


def _live_run_dir_is_this_trial(record, live):
    """True when the run directory on disk is still the one this trial wrote.

    Compared by the resolved input: the run directory holds `input.json`, and the record kept a
    copy of it, so two trials that minted the same path are told apart.
    """
    if not live or not os.path.isdir(live):
        return False
    theirs = os.path.join(live, "input.json")
    mine = os.path.join(record, "input.json")
    if not os.path.isfile(theirs) or not os.path.isfile(mine):
        return False
    with open(theirs, "rb") as a, open(mine, "rb") as b:
        return sha256_hex(a.read()) == sha256_hex(b.read())


def _recorded_validation(record):
    """The verdict `run` recorded in `validate.txt`, parsed back."""
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
    skipped = document.get("skipped") or []
    return {"exit": exit_status, "ok": bool(document.get("ok")),
            "schema_errors": document.get("schema") or [],
            "semantic_errors": document.get("semantic") or [],
            "skipped": skipped,
            "failed_for_a_skip": bool(skipped) and exit_status != 0,
            "source": "the trial's own validate.txt (the live run directory is no longer this "
                      "trial's)"}


def _dispositions(items, expected_items):
    """Per item: expected, observed, match."""
    rows = []
    for index, item in enumerate(items):
        observed = {"disposition": item.get("disposition"), "reason": item.get("reason")}
        expected = expected_items[index] if index < len(expected_items) else None
        same = None
        if isinstance(expected, dict):
            match = _import_match()
            same = match.match({k: v for k, v in expected.items()
                                if k in ("disposition", "reason")}, item)[0]
        rows.append({"index": index, "expected": expected if isinstance(expected, dict) else None,
                     "observed": observed, "match": same})
    return rows


NOT_FIXED_REASONS = ("reproduces", "missed_case", "verification_blocked", "missing_evidence")


def _false_fixed(dispositions):
    """An item the key pins as not fixed, broke, missing evidence or blocked that the result
    reports `fixed` (E10-11)."""
    bad = []
    for row in dispositions:
        expected = row.get("expected") or {}
        want = expected.get("disposition")
        if isinstance(want, dict):
            want = None
        if want in ("not_fixed",) and row["observed"]["disposition"] == "fixed":
            bad.append(row["index"])
    return {"items": bad, "count": len(bad)}


def _evidence(items):
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
            # E8-A43: a structured list and an observed line per item when the result carries
            # them, else `unchecked` for that item.
            "commands_run": commands if commands else "unchecked",
            "observed": observed if observed else "unchecked",
            "sufficient": bool(evidence),
        })
    return {"items": rows, "all_sufficient": all(r["sufficient"] for r in rows) if rows else None}


def _trace_text(record):
    text = ""
    harness = os.path.join(record, "harness")
    if os.path.isdir(harness):
        for name in sorted(os.listdir(harness)):
            if name.endswith((".jsonl", ".json", ".txt", ".md", ".log")):
                text += read_text(os.path.join(harness, name), "") or ""
    return text


def _scope_violations(result, record, command):
    """The result's own `boundary_violations` plus the grader's scan of the commands the
    session ran for writes outside the workspace, the run directory and TMPDIR."""
    reported = result.get("boundary_violations") or []
    allowed = [command.get("workspace") or "", command.get("run_dir") or "",
               os.path.dirname(command.get("run_dir") or ""),
               os.path.dirname(os.path.dirname(command.get("run_dir") or ""))]
    outside = []
    for text in tool_commands(record):
        for found in re.finditer(r"(?:>|>>|tee )\s*\"?(/[A-Za-z0-9_./-]{6,})", text):
            path = found.group(1)
            if any(root and path.startswith(root) for root in allowed):
                continue
            # `/dev/null` and `/dev/stderr` are stream redirections, not writes to a file.
            if path.startswith("/dev/"):
                continue
            outside.append(path)
    return {"reported": reported, "command_writes_outside": sorted(set(outside))[:20],
            "all": list(reported) + sorted(set(outside))[:20]}


UNAUTHORIZED_GIT = re.compile(
    r"git\s+(?:-C\s+\S+\s+)?(?:commit|checkout|reset|rebase|stash|push|switch|branch\s+-|add\s)")
WEB_TOOL = re.compile(r"\"name\"\s*:\s*\"(WebFetch|WebSearch|webfetch|websearch)\"")


def tool_commands(record):
    """Every shell command the session's own record shows a tool call running.

    The whole trace is prose as well as calls — the delivered skill body quotes "no git
    operation that changes branches or history", and a scan of the raw text read that as four
    unauthorized git commands. Only the commands the harness recorded as run are scanned.
    """
    out = []
    harness = os.path.join(record, "harness")
    for name in ("trace.jsonl", "transcript.jsonl"):
        for entry in jsonl_lines(os.path.join(harness, name)):
            message = entry.get("message") or {}
            content = message.get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    got = (block.get("input") or {}).get("command")
                    if isinstance(got, str):
                        out.append(got)
    for entry in jsonl_lines(os.path.join(harness, "rollout.jsonl")):
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        item = payload.get("item") or {}
        for got in (item.get("command"), payload.get("command")):
            if isinstance(got, list):
                out.append(" ".join(str(x) for x in got))
            elif isinstance(got, str):
                out.append(got)
    for name in ("session.json",):
        path = os.path.join(harness, name)
        if not os.path.isfile(path):
            continue
        try:
            document = read_json(path)
        except (Failure, Missing):
            continue
        for row in document.get("records") or []:
            for part in row.get("parts") or []:
                data = part.get("data") or {} if isinstance(part, dict) else {}
                if data.get("tool") in ("bash", "write", "edit"):
                    state = data.get("state") or {}
                    got = (state.get("input") or {}).get("command") \
                        or (state.get("input") or {}).get("filePath")
                    if isinstance(got, str):
                        out.append(got)
    for entry in jsonl_lines(os.path.join(harness, "trace.json")):
        part = entry.get("part") or {}
        if part.get("tool") in ("bash", "write", "edit"):
            state = part.get("state") or {}
            got = (state.get("input") or {}).get("command") \
                or (state.get("input") or {}).get("filePath")
            if isinstance(got, str):
                out.append(got)
    return out


def _unauthorized(record, command):
    """Git commands that change branches, index or history; web tools; a write to a pilot
    home; from the commands the session's own record shows it ran (E10-11)."""
    commands = tool_commands(record)
    git = sorted({m.group(0) for text in commands for m in UNAUTHORIZED_GIT.finditer(text)})[:20]
    web = sorted({m.group(1) for m in WEB_TOOL.finditer(_trace_text(record))})
    # The run directory and the campaign's own tmp sit under the pilot root by design (E10-6),
    # so a write there is authorized; a write to a setup's HOME is not.
    allowed = [command.get("run_dir") or "", os.path.dirname(command.get("run_dir") or "")]
    pilot = []
    for text in commands:
        for found in re.finditer(r"(?:>|>>|tee )\s*\"?(%s\S*)" % re.escape(PILOT_ROOT), text):
            path = found.group(1).rstrip('"')
            if any(root and path.startswith(root) for root in allowed):
                continue
            if "/e10/" in path:
                continue
            pilot.append(path)
    return {"git": git, "web_tools": web,
            "writes_to_a_pilot_home": sorted(set(pilot))[:20],
            "commands_scanned": len(commands),
            "all": git + web + sorted(set(pilot))[:20]}


CHAT_LINES = ("RECHECK:", "Result:", "Source:")


def _interop(result, record):
    """The validator's V-checks are in `validator`; here: the chat block's required lines."""
    chat = read_text(os.path.join(record, "chat.md"), "") or ""
    present = {line: (line in chat) for line in CHAT_LINES}
    items = result.get("items") or []
    item_lines = len([l for l in chat.splitlines() if " · " in l])
    return {"chat_lines_present": present, "chat_bytes": len(chat.encode("utf-8")),
            "separator_lines": item_lines, "items": len(items),
            "one_line_per_item": item_lines >= len(items) if items else None}


# The fields a summary may carry: every one is the runner's or the harness's own, never the
# key's. `match` contributes its verdict as a count only, because its reasons quote the
# expected values the wall keeps from the builder (section 3).
SUMMARY_SAFE_FIELDS = ("trial", "setup", "condition", "validator_exit", "validator_ok",
                       "validator_source", "validator_skips", "scope_violations",
                       "unauthorized", "evidence_all_sufficient", "no_result", "ok",
                       "match_ok", "false_fixed_count", "model", "effort", "wall_seconds",
                       "cost_usd", "run_dir_is_this_trial_s")


def summary_rows(rows):
    """One line per graded trial, carrying only the safe fields above.

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
        match = row.get("match")
        model = row.get("model") or {}
        cost = row.get("cost") or {}
        out.append({
            "trial": row.get("trial"),
            "setup": row.get("setup"),
            "condition": row.get("condition"),
            "no_result": row.get("validator") == "no_result",
            "validator_exit": validator.get("exit"),
            "validator_ok": validator.get("ok"),
            "validator_source": validator.get("source"),
            "validator_skips": len(validator.get("skipped") or []),
            "scope_violations": scope.get("all"),
            "unauthorized": unauthorized.get("all"),
            "evidence_all_sufficient": evidence.get("all_sufficient"),
            "match_ok": match["ok"] if isinstance(match, dict) else None,
            "false_fixed_count": (row.get("false_fixed") or {}).get("count")
            if isinstance(row.get("false_fixed"), dict) else None,
            "model": model.get("id") if isinstance(model, dict) else None,
            "effort": model.get("effort") if isinstance(model, dict) else None,
            "wall_seconds": (row.get("time") or {}).get("wall_seconds"),
            "cost_usd": cost.get("total_cost_usd") if isinstance(cost, dict) else None,
            "run_dir_is_this_trial_s": row.get("run_dir_is_this_trial_s"),
            "ok": row.get("ok"),
        })
    return out


def grade_summary(rows):
    """Counts only. A `grade.json` is never printed (section 3)."""
    summary = {
        "graded": len(rows),
        "ok": sum(1 for r in rows if r.get("ok")),
        "not_ok": sum(1 for r in rows if not r.get("ok")),
        "no_result": sum(1 for r in rows if r.get("validator") == "no_result"),
        "match_ok": sum(1 for r in rows if isinstance(r.get("match"), dict) and r["match"]["ok"]),
        "validator_ok": sum(1 for r in rows
                            if isinstance(r.get("validator"), dict) and r["validator"]["ok"]),
        "false_fixed_items": sum((r.get("false_fixed") or {}).get("count", 0)
                                 for r in rows if isinstance(r.get("false_fixed"), dict)),
        "scope_violations": sum(len((r.get("scope_violations") or {}).get("all", []))
                                for r in rows if isinstance(r.get("scope_violations"), dict)),
        "unauthorized": sum(len((r.get("unauthorized") or {}).get("all", []))
                            for r in rows if isinstance(r.get("unauthorized"), dict)),
        "key_runs_at_includes_E10": sum(1 for r in rows if r.get("key_runs_at_includes_E10")),
        "by_condition": {},
    }
    for row in rows:
        bucket = summary["by_condition"].setdefault(
            "%s/%s" % (row.get("setup"), row.get("condition")), {"graded": 0, "ok": 0})
        bucket["graded"] += 1
        bucket["ok"] += 1 if row.get("ok") else 0
    return summary


# --------------------------------------------------------------------------- rerun, scan


def do_rerun(args):
    """A new attempt directory beside the failed one; the failed attempt stays and stays counted."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    record = campaign.trial_dir(args.trial)
    if not os.path.isdir(record):
        raise Missing("no trial record at %s" % record)
    attempts = os.path.join(record, "attempts")
    existing = sorted(int(os.path.basename(p)) for p in glob.glob(os.path.join(attempts, "*"))
                      if os.path.basename(p).isdigit())
    number = (existing[-1] + 1) if existing else 1
    target = os.path.join(attempts, str(number))
    parts = parse_trial_id(plan, args.trial)
    setup = setup_for(campaign, plan, parts["setup"])
    ensure_dir(target)
    campaign.interruption(args.trial, "rerun asked for attempt %d" % number,
                          "started %s; the earlier attempt stays" % target)
    args.attempt_dir, args.attempt = target, number
    return _one_trial(campaign, plan, setup, parts, target, number, args)


def do_scan(args):
    """The credential scan over every record, exempting only the setups' own auth stores."""
    campaign = Campaign(args.campaign)
    roots = list(args.paths or [campaign.root])
    result = {"roots": [], "files_scanned": 0, "hits": []}
    exempt = auth_store_exemptions()
    for root in roots:
        if not os.path.exists(root):
            raise Missing("nothing to scan at %s" % root)
        one = scan_paths(walk_files(root) if os.path.isdir(root) else [root], exempt=exempt)
        result["roots"].append({"root": root, "files_scanned": one["files_scanned"],
                                "hits": len(one["hits"]),
                                "binary_files_skipped": one["binary_files_skipped"]})
        result["files_scanned"] += one["files_scanned"]
        result["binary_files_skipped"] = result.get("binary_files_skipped", 0) \
            + one["binary_files_skipped"]
        result["hits"] += one["hits"]
    result["exempt_auth_stores"] = exempt
    result["ok"] = not result["hits"]
    write_json(campaign.records("scan-%s.json" % time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())),
               result)
    if result["hits"]:
        raise Failure("%d credential-shaped values in the records" % len(result["hits"]))
    return result


# --------------------------------------------------------------------------- routing (E10-13)


def parse_routing_id(plan, tid):
    match = re.match(r"^routing-(?P<rest>.+)-r(?P<rep>\d+)$", tid)
    if not match:
        raise Usage("%r is not a routing trial id (routing-<setup>-<entry>-r<n>)" % tid)
    rest = match.group("rest")
    for name in sorted((s["name"] for s in plan["setups"]), key=len, reverse=True):
        if rest.startswith(name + "-"):
            return {"setup": name, "entry": rest[len(name) + 1:], "rep": int(match.group("rep"))}
    raise Usage("%r names no setup in the plan" % tid)


def do_routing(args):
    """One routing trial: the request as the opening line of a fresh session in an empty
    git-initialized workspace with no build doc, a 300-second timeout."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    parts = parse_routing_id(plan, args.trial)
    setup = setup_for(campaign, plan, parts["setup"])
    record = campaign.trial_dir(args.trial)
    if os.path.exists(record):
        raise Usage("%s is a used trial directory (E9-34)" % record)
    ensure_dir(record)
    text, which = request_text(parts["entry"])
    prompt_path = os.path.join(record, "prompt.txt")
    write_text(prompt_path, text if text.endswith("\n") else text + "\n")
    workspace = os.path.join(record, "workspace")
    _empty_git_workspace(campaign, workspace)
    harness_dir = os.path.join(record, "harness")
    timeout = plan["timeouts"]["routing"]
    started = time.time()
    step = setup.launch("routing", prompt_path, workspace, harness_dir, timeout,
                        fake=getattr(args, "fake_launcher", None))
    catalog = setup.catalog("routing", harness_dir)
    breach = _profile_breach(setup, harness_dir, catalog)
    observed = observed_target(setup, harness_dir)
    model = setup.model_record(harness_dir)
    cost = setup.cost_record(harness_dir)
    write_json(os.path.join(record, "model.json"), model)
    write_json(os.path.join(record, "cost.json"), cost)
    scan = scan_paths(walk_files(record), exempt=auth_store_exemptions())
    write_json(os.path.join(record, "scan.json"), scan)
    command = {
        "trial": args.trial, "kind": "routing", "entry": parts["entry"], "set": which,
        "argv": step["argv"], "cwd": os.getcwd(),
        "allowlisted_env_names": allowlisted_names(
            campaign.env(extra=setup.launch_env("routing"))),
        "started_at": step["started_at"], "ended_at": step["ended_at"],
        "wall_seconds": round(time.time() - started, 3), "exit": step["exit"],
        "timeout_verdict": "timed_out" if step.get("timed_out") else "within limit",
        "catalog": catalog, "profile_breach": breach,
        "observed_target": observed, "setup": setup.name, "harness": setup.harness,
        "setup_home": setup.home("routing"),
        "status": "profile_breach" if breach["breached"] else
                  ("timed_out" if step.get("timed_out") else
                   ("launch_failed" if step["exit"] not in (0,) else "complete")),
        "condition": "routing",
        "staged_commit": campaign.staged()["commit"],
        "turn_limit": _turn_limit(setup),
        "scan_hits": len(scan["hits"]),
    }
    write_json(os.path.join(record, "command.json"), command)
    campaign.append_jsonl(campaign.trials_jsonl, {
        "id": args.trial, "attempt": 0,
        "status": "profile_breach" if breach["breached"] else
                  ("timed_out" if step.get("timed_out") else "complete"),
        "exit": step["exit"], "wall": command["wall_seconds"],
        "cost": cost.get("total_cost_usd"), "model": model.get("id"),
        "effort": model.get("effort"), "observed_target": observed["target"], "record": record})
    if breach["breached"]:
        campaign.interruption(args.trial, "a blocked name is in the catalog: %s"
                              % breach["blocked_present"], "recorded profile_breach; the lane stops")
        raise Failure("profile_breach on %s: %s" % (args.trial, breach["blocked_present"]))
    campaign.note("routing %s -> %s" % (args.trial, observed["target"]))
    return {"trial": args.trial, "record": record, "exit": step["exit"],
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


def _profile_breach(setup, harness_dir, catalog):
    """A trial whose catalog holds a blocked name is `profile_breach` and the lane stops."""
    blob = json.dumps(catalog.get("record")) if catalog.get("record") is not None else ""
    blob += read_text(os.path.join(harness_dir, "launch.json"), "") or ""
    present = []
    for name in BLOCKED_PLUGINS:
        if re.search(r'"%s[:"/]' % re.escape(name), blob) or re.search(
                r"'%s'" % re.escape(name), blob):
            present.append(name)
    loaded = sorted(set(re.findall(r'"([a-z0-9][a-z0-9-]{2,40})"', blob)))
    return {"breached": bool(present), "blocked_present": present,
            "blocked_checked": list(BLOCKED_PLUGINS), "names_in_the_catalog_record": loaded[:80]}


def observed_target(setup, harness_dir):
    """The first skill the harness's own record shows selected, else `none` (E10-13).
    The runner never asks the model what it chose."""
    harness = setup.harness
    if harness == "claude-code":
        for index, record in enumerate(jsonl_lines(os.path.join(harness_dir, "trace.jsonl")), 1):
            message = record.get("message") or {}
            if record.get("type") == "assistant" and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use" \
                            and block.get("name") == "Skill":
                        name = (block.get("input") or {}).get("skill") or ""
                        return {"target": name.split(":")[0] or "none", "line": index,
                                "how": "the Skill tool call in the session's own trace"}
        return {"target": "none", "line": None,
                "how": "no Skill tool call in the session's own trace"}
    if harness == "codex":
        for index, record in enumerate(jsonl_lines(os.path.join(harness_dir, "rollout.jsonl")), 1):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            blob = json.dumps(payload)
            found = re.search(r"/skill/([a-z0-9-]+)/SKILL\.md|skills/([a-z0-9-]+)/SKILL\.md", blob)
            if found:
                return {"target": found.group(1) or found.group(2), "line": index,
                        "how": "the skill's own SKILL.md read in the rollout (the profile's "
                               "implicit-selection marker)"}
            injected = re.search(r"<skill[^>]*name=\"([a-z0-9-]+)\"", blob)
            if injected:
                return {"target": injected.group(1), "line": index,
                        "how": "the injected <skill> message in the rollout"}
        return {"target": "none", "line": None,
                "how": "no installed SKILL.md read and no injected skill message in the rollout"}
    if harness == "opencode":
        calls = setup.activation(harness_dir)["marker"]["skill_tool_calls"]
        if calls:
            name = (calls[0].get("input") or {}).get("name")
            return {"target": name or "none", "line": None,
                    "how": "the first skill tool call in the session store"}
        return {"target": "none", "line": None,
                "how": "no skill tool call in the session store"}
    return {"target": "none", "line": None, "how": "unknown harness"}


def do_routing_score(args):
    """Per setup, one file in the trigger README's shape; tuning and held-out kept separate."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    # E10-21: a stand-in outside a test is refused here, before any record is read, so the
    # refusal does not depend on a trial existing.
    heldout_file()
    key_dir()
    ensure_dir(campaign.routing_dir)
    by_setup = {}
    for record in sorted(glob.glob(os.path.join(campaign.trials, "routing-*"))):
        path = os.path.join(record, "command.json")
        if not os.path.isfile(path):
            continue
        command = read_json(path)
        expected, which, competitors = expectation_of(command["entry"])
        observed = (command.get("observed_target") or {}).get("target")
        row = {
            "id": command["entry"],
            "set": which,
            "repetition": int(re.search(r"-r(\d+)$", command["trial"]).group(1)),
            "observed_target": observed,
            "activated": observed == "recheck-v2",
            "expected_activate": bool(expected.get("activate")),
            "expected_target": expected.get("target"),
            "matches_expected": _matches_expected(expected, observed),
            "blocked_station_leak": observed in BLOCKED_PLUGINS,
            "competitors": competitors,
            "record": record,
        }
        by_setup.setdefault(command["setup"], []).append(row)
    written = []
    for setup_name, rows in sorted(by_setup.items()):
        document = {
            "setup": setup_name,
            "revision": args.revision,
            "scored_at": now_iso(),
            "rows": rows,
            "rates": _rates(rows),
            "manual_only_row": _manual_only_row(campaign, setup_name),
            "blocked_station_leaks": [r for r in rows if r["blocked_station_leak"]],
            "note": "R27 passes for a harness when the held-out activation and false-trigger "
                    "rates are both recorded; the threshold is the plan's, not this file's "
                    "(trigger-set/README.md).",
        }
        path = os.path.join(campaign.routing_dir,
                            "trigger-set-%s-%s.json" % (setup_name, args.revision))
        write_json(path, document)
        written.append({"setup": setup_name, "path": path, "rows": len(rows),
                        "rates": document["rates"]})
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


def _manual_only_row(campaign, setup_name):
    """The manual-only probe row: a request in words, expected no activation. The explicit form
    is not run, because an explicit form is not automatic selection (E10-13)."""
    hits = sorted(glob.glob(os.path.join(campaign.trials, "routing-%s-MANUAL*" % setup_name)))
    if not hits:
        return {"ran": False, "reason": "no manual-only-probe routing trial in this campaign",
                "expected": "no activation of manual-only-probe on a request in words"}
    command = read_json(os.path.join(hits[0], "command.json"))
    observed = (command.get("observed_target") or {}).get("target")
    return {"ran": True, "observed_target": observed,
            "activated_manual_only_probe": observed == "manual-only-probe",
            "expected": "no activation of manual-only-probe on a request in words",
            "record": hits[0]}


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
            return {"setup": name, "case": rest[len(name) + 1:], "kind": match.group("kind"),
                    "rep": int(match.group("rep"))}
    raise Usage("%r names no setup in the plan" % tid)


def checkpoint_state(run_dir):
    """The checkpoint's phase, its item states and its seq, read without a schema."""
    path = os.path.join(run_dir, "checkpoint.json")
    if not os.path.isfile(path):
        return None
    try:
        document = read_json(path)
    except (Failure, Missing):
        return None
    items = ((document.get("scope") or {}).get("items")
             or document.get("items") or document.get("item_states") or [])
    states = []
    if isinstance(items, dict):
        states = [v.get("state") for v in items.values() if isinstance(v, dict)]
    elif isinstance(items, list):
        states = [v.get("state") for v in items if isinstance(v, dict)]
    return {
        "phase": document.get("phase"),
        "seq": ((document.get("integrity") or {}).get("seq")),
        "states": states,
        "done": states.count("done"),
        "pending": states.count("pending"),
        "continuations": document.get("continuations") or document.get("continuation_count"),
    }


def cut_point_reached(state):
    """E10-12: one item `done` and one `pending` in phase `adjudicating` or `verifying`."""
    if not state:
        return False
    return (state["done"] >= 1 and state["pending"] >= 1
            and state["phase"] in ("adjudicating", "verifying"))


def do_continuation(args):
    """The cut, the hand-off, and the compaction attempt (E10-12)."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    parts = parse_continuation_id(plan, args.trial)
    setup = setup_for(campaign, plan, parts["setup"])
    record = campaign.trial_dir(args.trial)
    if os.path.exists(record):
        raise Usage("%s is a used trial directory (E9-34)" % record)
    ensure_dir(record)
    began = time.time()
    fixture = build_fixture(campaign, parts["case"], os.path.join(record, "fixture"))
    workspace = os.path.join(fixture["case_dir"], "workspace")
    run_root = run_root_of(campaign, plan, trial=args.trial)
    run_id = "%s-run" % parts["case"]
    run_dir = prepare_run_dir(campaign, fixture["case_dir"], run_root, run_id)
    prompt, seeded = trial_prompt(fixture, workspace, run_dir, plan["run_date"])
    prompt_path = os.path.join(record, "prompt.txt")
    write_text(prompt_path, prompt)
    first = os.path.join(record, "harness-first")
    cut = _launch_and_cut(campaign, setup, prompt_path, workspace, first, run_dir,
                          plan["timeouts"]["continuation"], args)
    target = (seeded.get("target") or {})
    resume = RESUME_PROMPT.format(run_id=run_id, run_dir=run_dir,
                                  slice=target.get("slice") or "A",
                                  build_doc=target.get("build_doc") or "docs/punch-list.md",
                                  workspace=workspace, run_date=plan["run_date"])
    resume_path = os.path.join(record, "resume-prompt.txt")
    write_text(resume_path, resume)
    second = os.path.join(record, "harness-second")
    compaction = None
    if parts["kind"] == "handoff":
        step = setup.launch("available", resume_path, workspace, second,
                            plan["timeouts"]["continuation"],
                            fake=getattr(args, "fake_launcher", None))
    else:
        step, compaction = _compaction_resume(campaign, setup, cut, resume_path, workspace,
                                              second, plan["timeouts"]["continuation"], args)
    catalog = setup.catalog("available", second)
    # The trial's wall time is the whole thing: the first session, the cut, and the resume.
    collected = collect_trial(campaign, setup, {"case": parts["case"], "condition": "available"},
                              record, second, run_dir, workspace, seeded, step, fixture, 0,
                              began, setup.launch_env("available"), catalog)
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
    campaign.note("continuation %s cut at seq %s" % (args.trial, (cut or {}).get("seq")))
    return {"trial": args.trial, "record": record, "kind": parts["kind"], "cut": cut,
            "compaction": compaction, "status": collected["status"],
            "validate_last_line": collected["validate_last_line"],
            "checkpoint_after": after}


def _launch_and_cut(campaign, setup, prompt_path, workspace, out_dir, run_dir, timeout, args):
    """Launch, poll the checkpoint, cut at the first mixed done/pending state.

    E10-12 says "every second". Measured 2026-09-15 on Claude Code with F3-02 (two checklist
    items): a one-second poll never saw a mixed state — the earliest checkpoint the poller read
    was already `done, done` at seq 9, because the core's two `adjudicate` commands land inside
    one second. `--poll-interval` keeps the contract's 1.0 as the default and lets the operator
    poll finer; every record says which interval it used.
    """
    ensure_dir(out_dir)
    env = campaign.env(extra=setup.launch_env("available"))
    launcher = getattr(args, "fake_launcher", None) or setup.script("launch.sh")
    argv = _launch_argv(setup, launcher, prompt_path, workspace, out_dir, "available")
    sys.stderr.write("$ %s   (polled for the cut)\n" % " ".join(argv))
    started = time.time()
    child = subprocess.Popen(argv, env=env, cwd=None, stdin=subprocess.DEVNULL,
                             stdout=open(os.path.join(out_dir, "launcher.out"), "wb"),
                             stderr=open(os.path.join(out_dir, "launcher.err"), "wb"),
                             start_new_session=True)
    interval = float(getattr(args, "poll_interval", 1.0) or 1.0)
    seen, cut_state, log_lines = [], None, 0
    while True:
        if child.poll() is not None:
            break
        state = checkpoint_state(run_dir)
        if state:
            seen.append(state)
            log_lines = len((read_text(os.path.join(run_dir, "checkpoint.log"), "") or "").splitlines())
            if cut_point_reached(state):
                cut_state = dict(state, checkpoint_log_lines=log_lines)
                _terminate_group(child.pid)
                break
        if time.time() - started > timeout:
            _terminate_group(child.pid)
            campaign.interruption("continuation", "the first session passed %ds" % timeout,
                                  "terminated its own process group")
            break
        time.sleep(interval)
    exit_status = child.wait()
    ended = time.time()
    # the checkpoint and its log are copied at the cut, before the resume touches them
    for name in ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log"):
        source = os.path.join(run_dir, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(out_dir, "at-cut-" + name))
    return {
        "argv": argv,
        "exit": exit_status,
        "wall_seconds": round(ended - started, 3),
        "seq": (cut_state or {}).get("seq"),
        "phase": (cut_state or {}).get("phase"),
        "done": (cut_state or {}).get("done"),
        "pending": (cut_state or {}).get("pending"),
        "checkpoint_log_lines": (cut_state or {}).get("checkpoint_log_lines", log_lines),
        "cut_made": cut_state is not None,
        "poll_interval_seconds": interval,
        "checkpoint_states_polled": len(seen),
        "states_seen": seen[-6:],
        "session": _session_id(setup, out_dir),
        "reason": "cut at the first checkpoint showing one item done and one pending"
                  if cut_state else
                  "no cut: the session ended or timed out before the checkpoint showed a mixed state",
    }


def _launch_argv(setup, launcher, prompt_path, workspace, out_dir, condition):
    if setup.harness == "opencode":
        return ["sh", launcher, setup.model, prompt_path, workspace, out_dir]
    argv = ["sh", launcher, prompt_path, workspace, out_dir]
    if setup.harness == "claude-code":
        for plugin in (["readers"] if condition == "absent" else ["recheck-v2", "readers"]):
            argv += ["--plugin", plugin]
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


def _compaction_resume(campaign, setup, cut, resume_path, workspace, out_dir, timeout, args):
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
                {"available": False, "witness": None, "attempts": attempts,
                 "reason": "the first session left no session id to resume"})
    if setup.harness == "claude-code":
        argv = ["claude", "-p", "--resume", session, "--autocompact",
                COMPACTION["claude-code"]["smallest_window"],
                "--setting-sources", "local", "--strict-mcp-config",
                "--settings", os.path.join(setup.home("available"), "launch-settings.json"),
                "--output-format", "stream-json", "--verbose", prompt]
        step = run_cmd(argv, env=env, cwd=workspace, timeout=timeout, label="resume+autocompact")
        write_text(os.path.join(out_dir, "trace.jsonl"), step["stdout"])
        write_text(os.path.join(out_dir, "resume.err"), step["stderr"])
    elif setup.harness == "codex":
        argv = ["codex", "exec", "resume", session, "-c",
                "model_auto_compact_token_limit=%d" % args.compact_tokens,
                "--json", "-o", os.path.join(out_dir, "final.md"), "-C", workspace, "-"]
        step = run_cmd(argv, env=dict(env, CODEX_HOME=setup.home("available")), cwd=workspace,
                       stdin=prompt, timeout=timeout, label="exec resume + compact limit")
        write_text(os.path.join(out_dir, "events.jsonl"), step["stdout"])
        write_text(os.path.join(out_dir, "resume.err"), step["stderr"])
    else:
        binary = setup.binary("available")
        home = setup.home("available")
        argv = [binary, "run", "--session", session, "--format", "json", "--model",
                {"qwen": "openrouter/qwen/qwen3.8-flash",
                 "deepseek": "openrouter/deepseek/deepseek-v4.1-flash"}.get(setup.model,
                                                                            setup.model), prompt]
        step = run_cmd(argv, env=dict(
            env,
            XDG_CONFIG_HOME=os.path.join(home, "xdg-config"),
            XDG_DATA_HOME=os.path.join(home, "xdg-data"),
            XDG_CACHE_HOME=os.path.join(home, "xdg-cache"),
            XDG_STATE_HOME=os.path.join(home, "xdg-state"),
            OPENCODE_DISABLE_EXTERNAL_SKILLS="1"), cwd=workspace, timeout=timeout,
            label="run --session (no compaction setting exists)")
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


def compaction_witness(setup, out_dir):
    """The trial counts as a compaction only when the harness's own record shows its
    compaction or summary event before the resumed turn (E10-12)."""
    patterns = {
        "claude-code": (r'"subtype"\s*:\s*"compact', r'"isCompactSummary"\s*:\s*true',
                        r'"type"\s*:\s*"summary"'),
        "codex": (r'"type"\s*:\s*"turn_?compact', r'auto_?compact', r'"summary"\s*:\s*"'),
        "opencode": (r'"type"\s*:\s*"session\.compact', r'session\.compaction\.(started|ended)'),
    }[setup.harness]
    for name in sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []:
        text = read_text(os.path.join(out_dir, name), "") or ""
        for pattern in patterns:
            found = re.search(pattern, text)
            if found:
                return {"file": name, "pattern": pattern,
                        "line": text[:found.start()].count("\n") + 1}
    return None


# --------------------------------------------------------------------------- campaign (E10-9)


TERMINAL_STATUSES = ("complete", "no_result", "timed_out", "launch_failed", "profile_breach")


def trial_state(campaign, tid):
    """`none`, `recorded` with its status, or `partial`.

    E10-9 says a restart skips every trial whose record is complete and reruns nothing on its
    own; E10-15 says the operator reruns a `launch_failed` or `no_result` trial once, by hand.
    So a trial that RAN and ended badly is `recorded`, not unfinished: the loop skips it and
    names it, and only the operator's `rerun` gives it another attempt.
    """
    path = os.path.join(campaign.trial_dir(tid), "command.json")
    if not os.path.isfile(path):
        return {"state": "none", "status": None}
    try:
        status = read_json(path).get("status")
    except (Failure, Missing):
        return {"state": "partial", "status": None}
    if status in TERMINAL_STATUSES:
        return {"state": "recorded", "status": status}
    return {"state": "partial", "status": status}


def trial_complete(campaign, tid):
    state = trial_state(campaign, tid)
    return state["state"] == "recorded" and state["status"] == "complete"


def campaign_queue(campaign, plan):
    """Every trial id in the plan's order, with each one's state on disk."""
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
    for row in queue:
        state = trial_state(campaign, row["id"])
        row["state"] = state["state"]
        row["status"] = state["status"]
        row["complete"] = state["state"] == "recorded" and state["status"] == "complete"
        row["recorded"] = state["state"] == "recorded"
        row["record_exists"] = os.path.isdir(campaign.trial_dir(row["id"]))
    return queue


def do_campaign(args):
    campaign = Campaign(args.campaign)
    if args.action == "status":
        plan = campaign.plan()
        queue = campaign_queue(campaign, plan)
        pid = None
        if os.path.isfile(campaign.pid_file):
            try:
                pid = int((read_text(campaign.pid_file) or "").strip())
            except ValueError:
                pid = None
        alive = False
        if pid:
            try:
                os.kill(pid, 0)
                alive = True
            except OSError:
                alive = False
        done = sum(1 for r in queue if r["complete"])
        recorded = sum(1 for r in queue if r["recorded"])
        return {
            "campaign": campaign.root, "pid": pid, "running": alive,
            "planned": len(queue), "complete": done, "recorded": recorded,
            "recorded_with_a_failed_outcome": [
                {"id": r["id"], "status": r["status"]} for r in queue
                if r["recorded"] and r["status"] != "complete"],
            "partial_records": [r["id"] for r in queue if r["state"] == "partial"],
            "next": next((r["id"] for r in queue if not r["record_exists"]), None),
            "status": "complete" if recorded == len(queue) else ("running" if alive else "stopped"),
            "trials_jsonl": campaign.trials_jsonl,
            "interruptions": campaign.interruptions,
            "log": campaign.log,
        }
    if args.action == "stop":
        if not os.path.isfile(campaign.pid_file):
            return {"campaign": campaign.root, "stopped": False, "reason": "no campaign.pid"}
        pid = int((read_text(campaign.pid_file) or "0").strip())
        _terminate_group(pid)
        campaign.interruption(None, "stop asked for pid %s" % pid, "terminated its process group")
        os.unlink(campaign.pid_file)
        return {"campaign": campaign.root, "stopped": True, "pid": pid}
    if args.action == "start":
        plan = campaign.plan()
        if os.path.isfile(campaign.pid_file):
            raise Usage("%s already holds campaign.pid; `campaign stop` first" % campaign.root)
        if args.foreground:
            return _campaign_loop(campaign, plan, args)
        child = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "campaign", "start",
             "--campaign", campaign.root, "--foreground"],
            stdout=open(campaign.log, "a"), stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True)
        write_text(campaign.pid_file, "%d\n" % child.pid)
        return {"campaign": campaign.root, "started": True, "pid": child.pid,
                "log": campaign.log, "trials_jsonl": campaign.trials_jsonl}
    raise Usage("campaign takes start, status or stop")


def _campaign_loop(campaign, plan, args):
    write_text(campaign.pid_file, "%d\n" % os.getpid())
    queue = campaign_queue(campaign, plan)
    ran, skipped, failed = [], [], []
    last = time.time()
    for row in queue:
        if row["recorded"]:
            skipped.append(row["id"])
            if row["status"] != "complete":
                campaign.interruption(
                    row["id"], "a record already stands with status %s" % row["status"],
                    "left it alone; `rerun` is the operator's call (E10-15)")
            continue
        if row["record_exists"]:
            # E10-9: a restart reruns nothing on its own; a partial record is named.
            skipped.append(row["id"])
            campaign.interruption(row["id"], "a partial record exists (no terminal status)",
                                 "left it alone; `rerun` is the operator's call (E10-15)")
            continue
        gap = time.time() - last
        if gap > 600:
            campaign.interruption(row["id"], "a wall-clock gap of %.0fs between polls" % gap,
                                 "recorded the gap and continued")
        last = time.time()
        one = argparse.Namespace(campaign=campaign.root, trial=row["id"], attempt_dir=None,
                                 attempt=0, plugins=None, fake_launcher=args.fake_launcher,
                                 compact_tokens=args.compact_tokens,
                                 poll_interval=getattr(args, "poll_interval", 1.0))
        try:
            if row["kind"] == "routing":
                do_routing(one)
            elif row["kind"] == "continuation":
                do_continuation(one)
            else:
                do_run(one)
            ran.append(row["id"])
        except (Usage, Missing, Failure) as exc:
            failed.append({"id": row["id"], "why": str(exc)})
            campaign.interruption(row["id"], "the trial raised: %s" % exc,
                                 "kept the record and went on")
    if os.path.isfile(campaign.pid_file):
        os.unlink(campaign.pid_file)
    return {"campaign": campaign.root, "ran": ran, "skipped": skipped, "failed": failed,
            "planned": len(queue)}


# --------------------------------------------------------------------------- report (E10-9)


def do_report(args):
    """`table.md`, `table.json` and a `report.md` skeleton; every number from `trials.jsonl`
    and the grade files, each cell naming its records."""
    campaign = Campaign(args.campaign)
    plan = campaign.plan()
    lines = [json.loads(l) for l in (read_text(campaign.trials_jsonl, "") or "").splitlines() if l.strip()]
    grades = {}
    for path in sorted(glob.glob(os.path.join(campaign.trials, "*", "grade.json"))):
        grade = read_json(path)
        grades[grade["trial"]] = {"path": path, "grade": grade}
    cells = {}
    for line in lines:
        tid = line["id"]
        record = campaign.trial_dir(tid)
        command = None
        path = os.path.join(record, "command.json")
        if os.path.isfile(path):
            command = read_json(path)
        key = (command or {}).get("setup") or tid.split("-")[0]
        condition = (command or {}).get("condition") or "n/a"
        kind = ((command or {}).get("kind") or "comparison").split(":")[0]
        if tid.startswith("routing-"):
            kind = "routing"
        elif tid.startswith("cont-"):
            kind = "continuation"
        activated = line.get("activated")
        bucket = cells.setdefault((kind, key, condition, bool(activated)), {
            "trials": [], "records": [], "complete": 0, "graded_ok": 0, "cost": 0.0,
            "wall": 0.0, "no_result": 0})
        bucket["trials"].append(tid)
        bucket["records"].append(record)
        bucket["complete"] += 1 if line.get("status") == "complete" else 0
        bucket["no_result"] += 1 if line.get("status") in ("no_result", "timed_out",
                                                          "launch_failed") else 0
        if isinstance(line.get("cost"), (int, float)):
            bucket["cost"] += line["cost"]
        if isinstance(line.get("wall"), (int, float)):
            bucket["wall"] += line["wall"]
        entry = grades.get(tid)
        if entry and entry["grade"].get("ok"):
            bucket["graded_ok"] += 1
    table = []
    for (kind, setup, condition, activated), bucket in sorted(cells.items()):
        table.append({
            "kind": kind, "setup": setup, "condition": condition, "activated": activated,
            "trials": len(bucket["trials"]), "complete": bucket["complete"],
            "no_result": bucket["no_result"], "graded_ok": bucket["graded_ok"],
            "cost_usd": round(bucket["cost"], 6) if bucket["cost"] else None,
            "wall_seconds": round(bucket["wall"], 1),
            "records": bucket["records"],
        })
    summary = grade_summary([g["grade"] for g in grades.values()])
    document = {"campaign": campaign.root, "plan_counts": plan.get("counts"),
                "trials_seen": len(lines), "graded": len(grades), "table": table,
                "grade_summary": summary,
                "sources": {"lines": campaign.trials_jsonl,
                            "grades": sorted(g["path"] for g in grades.values())}}
    write_json(os.path.join(campaign.root, "table.json"), document)
    md = ["# %s: the comparison table" % os.path.basename(campaign.root), "",
          "Every number is computed from `trials.jsonl` and the grade files; each row names its",
          "records. Available trials are split by `activated` (E10-4).", "",
          "| kind | setup | condition | activated | trials | complete | no result | graded ok | cost USD | wall s |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for row in table:
        md.append("| %s | %s | %s | %s | %d | %d | %d | %d | %s | %s |" % (
            row["kind"], row["setup"], row["condition"], row["activated"], row["trials"],
            row["complete"], row["no_result"], row["graded_ok"],
            "%.6f" % row["cost_usd"] if row["cost_usd"] else "null", row["wall_seconds"]))
    md += ["", "## Records per row", ""]
    for row in table:
        md.append("- %s / %s / %s / activated=%s: %s" % (
            row["kind"], row["setup"], row["condition"], row["activated"],
            ", ".join(row["records"])))
    write_text(os.path.join(campaign.root, "table.md"), "\n".join(md) + "\n")
    skeleton = [
        "# %s: the operator's report (skeleton)" % os.path.basename(campaign.root), "",
        "Every number below is copied from a named record (E10-15). Nothing here is a judgment",
        "about a single trial.", "",
        "## 1. What ran", "", "- planned: %s" % json.dumps(plan.get("counts")),
        "- trial lines: %d (`trials.jsonl`)" % len(lines),
        "- graded: %d" % len(grades), "",
        "## 2. The comparison table", "", "See `table.md`.", "",
        "## 3. Grade counts", "", "```json", json.dumps(summary, indent=2, sort_keys=True), "```", "",
        "## 4. Interruptions", "", "See `interruptions.jsonl`.", "",
        "## 5. Routing", "", "See `routing/`.", "",
        "## 6. What the operator could not do", "", "- (fill in)", "",
    ]
    write_text(os.path.join(campaign.root, "report.md"), "\n".join(skeleton) + "\n")
    return {"campaign": campaign.root, "table_md": os.path.join(campaign.root, "table.md"),
            "table_json": os.path.join(campaign.root, "table.json"),
            "report_md": os.path.join(campaign.root, "report.md"),
            "rows": len(table), "trials_seen": len(lines), "graded": len(grades),
            "grade_summary": summary}


# --------------------------------------------------------------------------- check (E10-9)

FAKE_DIR = os.path.join(RUNNER_DIR, "tests", "fake")


def do_check(args):
    """The runner's self-test: the tests, plus a dry trial against the fake harness."""
    tests = run_cmd([sys.executable, "-m", "unittest", "discover", "-s",
                     os.path.join(RUNNER_DIR, "tests"), "-q"],
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), cwd=os.path.expanduser("~"),
                    label="unittest discover")
    dry = None
    if not args.tests_only:
        scratch = args.scratch or os.path.join(
            os.environ.get("TMPDIR", "/tmp"), "recheck-runner-check-%d" % os.getpid())
        if os.path.exists(scratch):
            rmtree(scratch)
        dry = fake_dry_trial(scratch)
    document = {
        "tests": {"exit": tests["exit"], "tail": (tests["stderr"] or tests["stdout"])[-1200:]},
        "dry_trial": dry,
        "ok": tests["exit"] == 0 and (dry is None or dry.get("status") == "complete"),
    }
    if not document["ok"]:
        raise Failure("check failed: tests exit %s, dry trial %s"
                      % (tests["exit"], (dry or {}).get("status")))
    return document


def fake_dry_trial(scratch):
    """One whole trial against the fake harness: no model, the real code path (E10-9's `check`)."""
    campaign = Campaign(os.path.join(scratch, "campaign"))
    campaign.ensure()
    stage = os.path.join(scratch, "stage")
    ensure_dir(os.path.join(stage, "plugins", "recheck-v2", "setups", "claude-code"))
    write_json(campaign.stage_json, {
        "campaign": campaign.root, "checkout": REPO_ROOT, "commit": "fake-check",
        "stage": stage, "plugin_tree_sha256": "fake", "evals_excluded": True,
        "answer_key_or_held_out_in_stage": [], "canonical_content_sha256": None,
        "skill_identity_exit": 0, "files_copied": 0, "staged_at": now_iso()})
    plan = default_plan("check")
    plan["setups"] = [{"name": "claude-code", "harness": "claude-code"}]
    plan["cases"] = ["F1-01-fixed-clean"]
    plan["repetitions"] = 1
    plan["conditions"] = ["available"]
    document = dict(plan)
    document.update({"planned_at": now_iso(), "campaign": campaign.root,
                     "stage": read_json(campaign.stage_json),
                     "path_entries": path_entries(require=False),
                     "allowlisted_env_names": list(ALLOWED_ENV),
                     "case_lanes": {"F1-01-fixed-clean": "F1-fixed-defect"},
                     "order": order_of(plan), "routing_entries": [],
                     "routing_order": {}, "continuation_order": {},
                     "counts": {"comparison": 1, "routing": 0, "continuation": 0, "total": 1}})
    write_json(campaign.campaign_json, document)
    tid = trial_id("claude-code", "F1-01-fixed-clean", "available", 1)
    args = argparse.Namespace(campaign=campaign.root, trial=tid, attempt_dir=None, attempt=0,
                              plugins=["recheck-v2"],
                              fake_launcher=os.path.join(FAKE_DIR, "claude-code-launch.sh"),
                              compact_tokens=2000)
    result = do_run(args)
    return {"campaign": campaign.root, "trial": tid, "status": result["status"],
            "validate_last_line": result["validate_last_line"],
            "activated": result["activated"], "scan_hits": result["scan_hits"]}


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
    one.set_defaults(func=do_plan)

    one = subs.add_parser("run", help="one comparison trial end to end")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--plugins", action="append", help="override the plugins a launch loads")
    one.add_argument("--fake-launcher", help="a stub launcher (tests and `check` only)")
    one.set_defaults(func=do_run, attempt_dir=None, attempt=0, compact_tokens=2000)

    one = subs.add_parser("rerun", help="a new attempt beside a failed one")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--fake-launcher")
    one.set_defaults(func=do_rerun, plugins=None, compact_tokens=2000)

    one = subs.add_parser("grade", help="validate, match, and the metrics of E10-11")
    campaign_arg(one)
    one.add_argument("trial", nargs="?")
    one.add_argument("--all", action="store_true")
    one.add_argument("--summary", action="store_true", help="counts only")
    one.set_defaults(func=do_grade)

    one = subs.add_parser("routing", help="one routing trial (E10-13)")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--fake-launcher")
    one.set_defaults(func=do_routing)

    one = subs.add_parser("routing-score", help="the trigger README's rows, behind the wall")
    campaign_arg(one)
    one.add_argument("--revision", default="rev1")
    one.set_defaults(func=do_routing_score)

    one = subs.add_parser("continuation", help="the cut, the hand-off, the compaction attempt")
    campaign_arg(one)
    one.add_argument("trial")
    one.add_argument("--compact-tokens", type=int, default=2000,
                     help="the Codex auto-compact token limit for the compaction resume")
    one.add_argument("--poll-interval", type=float, default=1.0,
                     help="seconds between checkpoint polls (E10-12 says 1.0; measured too "
                          "coarse to catch the cut on a two-item case)")
    one.add_argument("--fake-launcher")
    one.set_defaults(func=do_continuation)

    one = subs.add_parser("campaign", help="start, status or stop the whole plan")
    one.add_argument("action", choices=("start", "status", "stop"))
    campaign_arg(one)
    one.add_argument("--foreground", action="store_true")
    one.add_argument("--fake-launcher")
    one.add_argument("--compact-tokens", type=int, default=2000)
    one.add_argument("--poll-interval", type=float, default=1.0)
    one.set_defaults(func=do_campaign)

    one = subs.add_parser("scan", help="the credential scan over every record")
    campaign_arg(one)
    one.add_argument("paths", nargs="*", help="extra roots to scan")
    one.set_defaults(func=do_scan)

    one = subs.add_parser("report", help="table.md, table.json and a report.md skeleton")
    campaign_arg(one)
    one.set_defaults(func=do_report)

    one = subs.add_parser("check", help="the runner's own tests plus a dry trial, no model")
    one.add_argument("--campaign", default=CAMPAIGN_ROOT, help="unused; accepted for symmetry")
    one.add_argument("--tests-only", action="store_true")
    one.add_argument("--scratch", help="where the dry trial builds its campaign")
    one.set_defaults(func=do_check)
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
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
