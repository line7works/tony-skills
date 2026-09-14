"""Shared facts the Claude Code adapter helpers read from harness records.

Not a CLI. `invocation.py`, `turns.py`, and `verifier.py` import it from this
directory. Python 3.9, standard library only, no network, no model call.

Every value here is read from something the harness wrote (the session
transcript under the active config directory, the environment the harness gave
the tool shell, or the `claude` binary's own `--version`). Nothing is composed
by the executor and nothing is guessed; a value that cannot be read is reported
as missing, never filled in.
"""

import glob
import json
import os
import subprocess

HARNESS = "claude-code"

# Ruling E9-3 (provisional only where the ruling says so; the Claude classes are not).
FLOOR_CLASSES = (
    ("claude-opus-", "opus"),
    ("claude-fable-", "opus"),
    ("claude-mythos-", "opus"),
    ("claude-sonnet-", "sonnet"),
    ("claude-haiku-", "haiku"),
)
CLASS_RANK = {"haiku": 1, "sonnet": 2, "opus": 3}


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


def hook_payload_path(pid=None):
    """Where a shipped SessionStart hook would leave its payload (candidate (a))."""
    tmp = os.environ.get("TMPDIR") or "/tmp"
    key = pid or os.environ.get("CLAUDE_PID") or str(os.getppid())
    return os.path.join(tmp, "recheck-v2", "claude-code", "%s.json" % key)


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


def _cwd_matches(path, workspace):
    target = os.path.realpath(workspace)
    for record in _records(path):
        cwd = record.get("cwd")
        if cwd and os.path.realpath(cwd) == target:
            return True
    return False


def find_transcript(explicit=None, session_id=None, cfg=None, workspace=None):
    """Locate the running session's own transcript.

    Returns (path, session_id, discovery, note). Candidates in order:

    1. ``--transcript PATH``
    2. ``--session-id ID`` under ``<config>/projects/*/<ID>.jsonl``
    3. the harness's own ``CLAUDE_CODE_SESSION_ID`` in the tool shell's
       environment (measured 2026-09-14 in an interactive session and in a
       headless ``claude -p`` session)
    4. a hook payload keyed by ``CLAUDE_PID`` (only when a hook ships one)
    5. the newest transcript under the config directory holding a record whose
       ``cwd`` is the workspace (ambiguous with two sessions in one directory:
       the note says how many matched)
    """
    root = cfg or config_dir()
    if explicit:
        path = os.path.abspath(os.path.expanduser(explicit))
        if not os.path.isfile(path):
            raise HelperError("transcript not found: %s" % path, 3)
        return path, os.path.splitext(os.path.basename(path))[0], "explicit path", None

    if session_id:
        hits = sorted(glob.glob(os.path.join(root, "projects", "*", "%s.jsonl" % session_id)))
        if not hits:
            raise HelperError(
                "no transcript for session %s under %s/projects" % (session_id, root), 3
            )
        return hits[0], session_id, "session id argument", None

    env_sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if env_sid:
        hits = sorted(glob.glob(os.path.join(root, "projects", "*", "%s.jsonl" % env_sid)))
        if hits:
            return hits[0], env_sid, "env CLAUDE_CODE_SESSION_ID", None

    payload = hook_payload_path()
    if os.path.isfile(payload):
        try:
            with open(payload, "r", encoding="utf-8") as handle:
                blob = json.load(handle)
            path = blob.get("transcript_path")
            sid = blob.get("session_id")
            if path and os.path.isfile(path):
                return path, sid or os.path.splitext(os.path.basename(path))[0], "hook payload", None
        except (ValueError, OSError):
            pass

    if workspace:
        hits = glob.glob(os.path.join(root, "projects", "*", "*.jsonl"))
        matched = [p for p in hits if _cwd_matches(p, workspace)]
        if matched:
            matched.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            note = None
            if len(matched) > 1:
                note = "%d transcripts name this workspace; the newest was taken" % len(matched)
            sid = os.path.splitext(os.path.basename(matched[0]))[0]
            return matched[0], sid, "newest transcript whose cwd is the workspace", note

    if env_sid:
        raise HelperError(
            "CLAUDE_CODE_SESSION_ID is %s but no transcript for it under %s/projects"
            % (env_sid, root),
            3,
        )
    raise HelperError(
        "no session transcript reachable: CLAUDE_CODE_SESSION_ID is unset, no hook payload at "
        "%s, and no --transcript, --session-id, or --workspace was given" % payload,
        3,
    )


def turn_ref(session_id, uuid):
    return "claude-code:session %s:msg %s" % (session_id, uuid)


# A `user` record the harness wrote itself rather than the person typing. The
# skill body a Skill call delivers arrives as a `user` record of text blocks
# carrying isMeta, turnCompanion and sourceToolUseID (measured 2026-09-14: the
# 25,770-byte delivery-probe body landed that way), so the E9 section 6 rule on
# its own would attribute a delivered skill body to the user and let a grant
# cite it. These keys keep it out of the map.
HARNESS_WRITTEN_KEYS = ("isMeta", "turnCompanion", "sourceToolUseID", "toolUseResult")


def harness_written(record):
    for key in HARNESS_WRITTEN_KEYS:
        if record.get(key):
            return key
    return None


def is_user_turn(record):
    """Contract E9 section 6, with the harness-written records kept out."""
    message = record.get("message")
    if not isinstance(message, dict):
        return False
    if harness_written(record):
        return False
    content = message.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        kinds = set()
        for block in content:
            if isinstance(block, dict):
                kinds.add(block.get("type"))
        return bool(kinds) and kinds <= {"text"}
    return False


def user_text(record):
    message = record.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "\n".join(parts)
    return ""


def read_session(path, session_id, station_refs=()):
    """Build the turn map and the model facts from one transcript."""
    attribution = {}
    users = []
    models = []
    efforts = []
    counts = {
        "user_turns": 0,
        "assistant_turns": 0,
        "unmapped_tool_results": 0,
        "unmapped_sidechain": 0,
        "unmapped_harness_written": 0,
        "unmapped_other": 0,
    }
    for record in _records(path):
        kind = record.get("type")
        if kind not in ("user", "assistant"):
            continue
        uuid = record.get("uuid")
        if not uuid:
            counts["unmapped_other"] += 1
            continue
        if record.get("isSidechain"):
            counts["unmapped_sidechain"] += 1
            continue
        ref = turn_ref(record.get("sessionId") or session_id, uuid)
        if kind == "assistant":
            attribution[ref] = "assistant"
            counts["assistant_turns"] += 1
            message = record.get("message") or {}
            if message.get("model"):
                models.append(message["model"])
            if record.get("effort"):
                efforts.append(record["effort"])
            continue
        if is_user_turn(record):
            attribution[ref] = "user"
            counts["user_turns"] += 1
            users.append((ref, record.get("timestamp"), user_text(record)))
        elif record.get("toolUseResult") is not None:
            counts["unmapped_tool_results"] += 1
        elif harness_written(record):
            counts["unmapped_harness_written"] += 1
        elif isinstance((record.get("message") or {}).get("content"), list):
            counts["unmapped_tool_results"] += 1
        else:
            counts["unmapped_other"] += 1
    for ref in station_refs:
        attribution[ref] = "station"
    return {
        "attribution": attribution,
        "users": users,
        "models": models,
        "efforts": efforts,
        "counts": counts,
    }


def claude_version():
    """`claude --version`, the first whitespace-separated token."""
    try:
        out = subprocess.check_output(
            ["claude", "--version"], stderr=subprocess.STDOUT
        ).decode("utf-8", "replace")
    except OSError as exc:
        raise HelperError("the claude binary is not on PATH: %s" % exc, 3)
    except subprocess.CalledProcessError as exc:
        raise HelperError(
            "claude --version failed (%s): %s"
            % (exc.returncode, exc.output.decode("utf-8", "replace").strip()),
            3,
        )
    text = out.strip().splitlines()[0] if out.strip() else ""
    if not text:
        raise HelperError("claude --version printed nothing", 3)
    return text.split()[0]


def floor_for(model_id, floor="opus"):
    """Ruling E9-3's map. Returns (floor_class, floor_met)."""
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
                os.path.realpath(os.path.join(cfg, "plugins", "cache"))
            ):
                return "plugin"
            break
    if os.sep + ".claude" + os.sep + "skills" + os.sep in real or (
        os.sep + ".agents" + os.sep + "skills" + os.sep in real
    ):
        return "host skill"
    if in_cache:
        return "explicit path (installed plugin cache loaded with --plugin-dir)"
    return "explicit path"


def sandbox_mode():
    """The permission mode in force, from a harness or launcher record."""
    for name in ("CLAUDE_CODE_PERMISSION_MODE", "RECHECK_HARNESS_SANDBOX"):
        value = os.environ.get(name)
        if value:
            return value, name
    return "unknown (no permission-mode record reachable from the session)", None


def mode_hint():
    """Whether a person can answer a question in this session.

    Measured 2026-09-14: a headless `claude -p` session's tool shell carries
    CLAUDE_CODE_SESSION_ATTENDED=0 and CLAUDE_CODE_ENTRYPOINT=sdk-cli; an
    interactive session carries 1 and cli. The executor still types
    `invocation.mode`; this is the fact it types it from, so a headless run
    does not ask a question into a channel nobody reads.
    """
    attended = os.environ.get("CLAUDE_CODE_SESSION_ATTENDED")
    if attended == "0":
        return "headless", "CLAUDE_CODE_SESSION_ATTENDED=0"
    if attended == "1":
        return "interactive", "CLAUDE_CODE_SESSION_ATTENDED=1"
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT")
    if entrypoint == "sdk-cli":
        return "headless", "CLAUDE_CODE_ENTRYPOINT=sdk-cli"
    if entrypoint == "cli":
        return "interactive", "CLAUDE_CODE_ENTRYPOINT=cli"
    return "unknown", "no attended or entrypoint record in the environment"


def provider_route():
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK"):
        return "bedrock"
    if os.environ.get("CLAUDE_CODE_USE_VERTEX"):
        return "vertex"
    if os.environ.get("CLAUDE_CODE_USE_FOUNDRY"):
        return "foundry"
    return "anthropic"
