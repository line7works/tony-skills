"""Shared facts the Claude Code adapter helpers of this core read from harness records.

Not a CLI. Copied from the recheck-v2 pilot's `adapters/claude-code/_common.py` (E9 lane C, the
seam E13 ruling E13-3 copies) and cut down to what the build and signoff cores need: the
session's own transcript, found through the harness's `CLAUDE_CODE_SESSION_ID` and bound to
this session (ruling E9-28), the model it records, its permission mode and entrypoint, and the
`claude` binary's own `--version`. There is no turn map here: neither core takes a user-channel
field (see the profile's section 4). This file is byte-identical in `build-v2` and `signoff-v2`;
the core it serves is read from its own location, never configured.

Python 3.9, standard library only, no network, no model call, nothing written.
"""

import json
import os
import re
import subprocess
import sys

HARNESS = "claude-code"
HERE = os.path.dirname(os.path.abspath(__file__))
# <plugin>/skills/<core>/adapters/claude-code/_common.py
CORE = os.path.basename(os.path.dirname(os.path.dirname(HERE)))
PREFIX = re.sub(r"[^A-Z0-9]", "_", CORE.upper())            # BUILD_V2 or SIGNOFF_V2
TEST_FLAG = PREFIX + "_ADAPTER_TEST"
SESSION_ID_VAR = "CLAUDE_CODE_SESSION_ID"

# Ruling E9-3's Claude classes, the pilot's map unchanged (none of them is provisional). The
# v1 floor both cores inherit is "Opus-class or better" (signoff v1 Step 0; P5 keeps it).
FLOOR_CLASSES = (
    ("claude-opus-", "opus"),
    ("claude-fable-", "opus"),
    ("claude-mythos-", "opus"),
    ("claude-sonnet-", "sonnet"),
    ("claude-haiku-", "haiku"),
)
CLASS_RANK = {"haiku": 1, "sonnet": 2, "opus": 3}
# Harness-authored error records carry this in place of a model (guide L135).
SYNTHETIC_MODEL = "<synthetic>"


class HelperError(Exception):
    """Raised with an exit code: 2 usage, 3 missing record or binary, 1 other."""

    def __init__(self, message, code=1):
        Exception.__init__(self, message)
        self.code = code


def config_dir(explicit=None):
    """The active Claude Code configuration directory."""
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), ".claude")


def test_mode():
    return os.environ.get(TEST_FLAG) == "1"


def assert_fixture_allowed(explicit, session_id):
    """Ruling E9-28: the fixture flags are a usage error outside the tests."""
    if (explicit or session_id) and not test_mode():
        raise HelperError(
            "--transcript and --session-id are the fixture interface and are accepted only "
            "under %s=1 (ruling E9-28); at run time the session's own record is found through "
            "%s" % (TEST_FLAG, SESSION_ID_VAR), 2)


def project_slug(path):
    """The folder Claude Code gives a cwd under ``<config>/projects/`` (the pilot's rule)."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(path))


def _records(path):
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _transcript_hits(root, session_id, workspace=None):
    """Named slug folders first, then a scan of ``<root>/projects``; never another id."""
    projects = os.path.join(root, "projects")
    hits = []
    for base in (os.getcwd(), workspace):
        if not base:
            continue
        named = os.path.join(projects, project_slug(base), "%s.jsonl" % session_id)
        if os.path.isfile(named) and named not in hits:
            hits.append(named)
    if hits:
        return hits
    try:
        names = sorted(os.listdir(projects))
    except OSError:
        return hits
    for name in names:
        candidate = os.path.join(projects, name, "%s.jsonl" % session_id)
        if os.path.isfile(candidate):
            hits.append(candidate)
    return hits


def _first_session_id(path):
    for record in _records(path):
        if record.get("type") in ("user", "assistant") and record.get("sessionId"):
            return record["sessionId"]
    return None


def _bind_session(path, session_id):
    """Every turn record must carry this session's own id (ruling E9-28)."""
    seen, turns = set(), 0
    for record in _records(path):
        if record.get("type") not in ("user", "assistant"):
            continue
        turns += 1
        if record.get("sessionId"):
            seen.add(record["sessionId"])
    foreign = sorted(value for value in seen if value != session_id)
    if foreign:
        raise HelperError(
            "%s holds records of another session (sessionId %s, expected %s); ruling E9-28 "
            "binds the facts to this session's own record" % (path, ", ".join(foreign),
                                                             session_id), 3)
    return turns


def _bind_workspace(path, workspace):
    if not workspace:
        return "not checked: no --workspace was given (ruling E9-28's cwd binding did not run)"
    target = os.path.realpath(os.path.abspath(os.path.expanduser(workspace)))
    seen = []
    for record in _records(path):
        cwd = record.get("cwd")
        if not cwd:
            continue
        real = os.path.realpath(cwd)
        if real == target:
            return "a record of this session names %s as its cwd" % target
        if real not in seen:
            seen.append(real)
    raise HelperError(
        "no record of session transcript %s names the workspace %s as its cwd (the cwds it "
        "names: %s); ruling E9-28 refuses another workspace's transcript"
        % (path, target, ", ".join(seen) or "none"), 3)


def find_transcript(explicit=None, session_id=None, cfg=None, workspace=None):
    """The running session's own transcript: (path, session_id, discovery, workspace_note).

    One route at run time: the harness's ``CLAUDE_CODE_SESSION_ID``, resolved to
    ``<config>/projects/*/<id>.jsonl`` and bound by every turn record's ``sessionId`` and by a
    record whose ``cwd`` is the workspace. Absent, ambiguous or mismatched: exit 3.
    """
    root = cfg or config_dir()
    assert_fixture_allowed(explicit, session_id)
    if explicit:
        path = os.path.abspath(os.path.expanduser(explicit))
        if not os.path.isfile(path):
            raise HelperError("transcript not found: %s" % path, 3)
        sid = session_id or _first_session_id(path) or os.path.splitext(os.path.basename(path))[0]
        discovery = "fixture interface: --transcript under %s=1" % TEST_FLAG
    else:
        sid = session_id or os.environ.get(SESSION_ID_VAR)
        if not sid:
            raise HelperError(
                "%s is not set in this tool shell, so the session's own record cannot be "
                "identified; ruling E9-28 takes no other route" % SESSION_ID_VAR, 3)
        hits = _transcript_hits(root, sid, workspace)
        if not hits:
            raise HelperError("%s is %s but no transcript named %s.jsonl exists under "
                              "%s/projects" % (SESSION_ID_VAR, sid, sid, root), 3)
        if len(hits) > 1:
            raise HelperError("%d transcripts under %s/projects are named for session %s (%s); "
                              "the discovery is ambiguous" % (len(hits), root, sid,
                                                              ", ".join(hits)), 3)
        path = hits[0]
        discovery = ("fixture interface: --session-id under %s=1" % TEST_FLAG if session_id
                     else "the harness's own %s, bound to this session's records"
                     % SESSION_ID_VAR)
    turns = _bind_session(path, sid)
    if not turns:
        raise HelperError("unusable session record: no user or assistant turns in %s "
                          "(ruling E9-29)" % path, 3)
    return path, sid, discovery, _bind_workspace(path, workspace)


def read_session(path):
    """The facts the session's own records carry: models, efforts, permission modes,
    entrypoints and versions, each in record order."""
    facts = {"models": [], "efforts": [], "permission_modes": [], "entrypoints": [],
             "versions": [], "synthetic_records": 0}
    for record in _records(path):
        if record.get("type") not in ("user", "assistant"):
            continue
        for key, bucket in (("permissionMode", "permission_modes"),
                            ("entrypoint", "entrypoints"), ("version", "versions")):
            if record.get(key):
                facts[bucket].append(record[key])
        if record.get("type") != "assistant" or record.get("isSidechain"):
            continue
        message = record.get("message")
        message = message if isinstance(message, dict) else {}
        model = message.get("model")
        if model == SYNTHETIC_MODEL or record.get("isApiErrorMessage") \
                or record.get("is_api_error_message"):
            facts["synthetic_records"] += 1
            continue
        if model:
            facts["models"].append(model)
        if record.get("effort"):
            facts["efforts"].append(record["effort"])
    return facts


def claude_version():
    """`claude --version`, the first whitespace-separated token."""
    try:
        out = subprocess.check_output(["claude", "--version"], stderr=subprocess.STDOUT)
    except OSError as exc:
        raise HelperError("the claude binary is not on PATH: %s" % exc, 3)
    except subprocess.CalledProcessError as exc:
        raise HelperError("claude --version failed (%s)" % exc.returncode, 3)
    text = out.decode("utf-8", "replace").strip()
    if not text:
        raise HelperError("claude --version printed nothing", 3)
    return text.splitlines()[0].split()[0]


def floor_for(model_id, floor="opus"):
    """Ruling E9-3's map. Returns (floor_class, floor_met); unknown is never elevated."""
    if not model_id:
        return "unknown", None
    lowered = model_id.lower()
    for prefix, klass in FLOOR_CLASSES:
        if lowered.startswith(prefix):
            wanted = CLASS_RANK.get(floor)
            if wanted is None:
                return klass, None
            return klass, CLASS_RANK[klass] >= wanted
    return "unknown", None


def entry_kind(helper_path, cfg):
    """How this copy of the skill was loaded, from the helper's own location."""
    real = os.path.realpath(helper_path)
    parts = real.split(os.sep)
    in_cache = False
    for index in range(len(parts) - 1):
        if parts[index] == "plugins" and parts[index + 1] == "cache":
            in_cache = True
            cache_root = os.sep.join(parts[: index + 2])
            if os.path.realpath(cache_root).startswith(
                    os.path.realpath(os.path.join(cfg, "plugins", "cache"))):
                return "plugin"
            break
    if (os.sep + ".claude" + os.sep + "skills" + os.sep in real
            or os.sep + ".agents" + os.sep + "skills" + os.sep in real):
        return "host skill"
    if in_cache:
        return "explicit path (installed plugin cache loaded with --plugin-dir)"
    return "explicit path"


def sandbox_mode(session):
    """The permission mode the transcript records, else the launcher's, else unknown."""
    recorded = session.get("permission_modes") or []
    if recorded:
        return recorded[-1], "the session transcript's own permissionMode record"
    launcher = os.environ.get("CLAUDE_CODE_PERMISSION_MODE")
    if launcher:
        return launcher, "CLAUDE_CODE_PERMISSION_MODE (no permissionMode in the record)"
    return "unknown (no permission-mode record reachable from the session)", None


def mode_hint(session):
    """interactive or headless: the environment, cross-checked against the transcript."""
    recorded = session.get("entrypoints") or []
    record_mode = ({"sdk-cli": "headless", "cli": "interactive"}.get(recorded[-1])
                   if recorded else None)
    attended = os.environ.get("CLAUDE_CODE_SESSION_ATTENDED")
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT")
    env_mode, env_source = None, None
    if attended == "0":
        env_mode, env_source = "headless", "CLAUDE_CODE_SESSION_ATTENDED=0"
    elif attended == "1":
        env_mode, env_source = "interactive", "CLAUDE_CODE_SESSION_ATTENDED=1"
    elif entrypoint == "sdk-cli":
        env_mode, env_source = "headless", "CLAUDE_CODE_ENTRYPOINT=sdk-cli"
    elif entrypoint == "cli":
        env_mode, env_source = "interactive", "CLAUDE_CODE_ENTRYPOINT=cli"
    if env_mode and record_mode:
        if env_mode != record_mode:
            return "unknown", ("%s says %s and the transcript's entrypoint record %r says %s; "
                               "they disagree" % (env_source, env_mode, recorded[-1], record_mode))
        return env_mode, "%s, cross-checked against the transcript's entrypoint record %r" % (
            env_source, recorded[-1])
    if env_mode:
        return env_mode, env_source
    if record_mode:
        return record_mode, "the transcript's own entrypoint record %r" % recorded[-1]
    return "unknown", "no attended or entrypoint record in the environment or the transcript"


def provider_route():
    for name, route in (("CLAUDE_CODE_USE_BEDROCK", "bedrock"),
                        ("CLAUDE_CODE_USE_VERTEX", "vertex"),
                        ("CLAUDE_CODE_USE_FOUNDRY", "foundry")):
        if os.environ.get(name):
            return route
    return "anthropic"


class JsonParser(__import__("argparse").ArgumentParser):
    """A7a: `--help` is JSON on stdout like every other answer; a usage slip is exit 2."""

    def print_help(self, file=None):
        sys.stdout.write(json.dumps({"help": self.format_help()}) + "\n")

    def error(self, message):
        sys.stderr.write("%s: %s\n" % (self.prog, message))
        raise SystemExit(2)


def run(prog, main):
    """One JSON document on stdout, diagnostics on stderr, exit 0/2/3/1 (A7a)."""
    try:
        document = main()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    except HelperError as error:
        sys.stderr.write("%s: %s\n" % (prog, error))
        sys.stdout.write(json.dumps({"error": str(error), "exit": error.code}) + "\n")
        return error.code
    except Exception as error:  # noqa: BLE001 - a helper never prints a traceback for JSON
        sys.stderr.write("%s: %s: %s\n" % (prog, type(error).__name__, error))
        sys.stdout.write(json.dumps({"error": "%s: %s" % (type(error).__name__, error),
                                     "exit": 1}) + "\n")
        return 1
    sys.stdout.write(json.dumps(document, indent=2) + "\n")
    return 0
