"""Shared facts the Claude Code adapter helpers read from harness records.

Not a CLI. `invocation.py`, `turns.py`, and `verifier.py` import it from this
directory. Python 3.9, standard library only, no network, no model call.

Every value here is read from something the harness wrote (the session
transcript under the active config directory, the environment the harness gave
the tool shell, or the `claude` binary's own `--version`). Nothing is composed
by the executor and nothing is guessed; a value that cannot be read is reported
as missing, never filled in.
"""

import json
import os
import re
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


TEST_FLAG = "RECHECK_ADAPTER_TEST"
SESSION_ID_VAR = "CLAUDE_CODE_SESSION_ID"


def project_slug(path):
    """The folder name Claude Code gives a session's cwd under ``<config>/projects/``.

    Every character that is not a letter or a digit becomes ``-``. This is the SAME rule
    ``setups/claude-code/launch.sh`` uses to copy a session's transcript back, and the two are
    tested against each other; if one is wrong they are wrong together and the test says so.
    """
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(path))


def transcript_hits(root, session_id, workspace=None):
    """``(hits, searched, refused)`` for one session id under ``<root>/projects``.

    The NAMED slug folders first, then the scan. Behind the sealed bench's wall a session may
    read only its own slug folder under ``~/.claude/projects``; LISTING the parent is refused,
    and `glob` swallows that refusal and returns nothing, so the helper reported "no
    transcript" for a file that was sitting there readable. Measured 2026-09-19 (live proof 5,
    root ``wall-proof-20260919T171050Z``): ``invocation.py`` exited 3 with
    ``CLAUDE_CODE_SESSION_ID is <id> but no transcript named <id>.jsonl exists under
    ~/.claude/projects`` and the whole trial stopped on it.

    Ruling E9-28 is untouched. Every route here is keyed on the session id the HARNESS set, so
    no named folder and no scan can reach another session's record; what changed is that the
    helper looks where the file actually is before it tries to list a directory it may not be
    allowed to list, and that a refused directory is RECORDED rather than read as absence.
    """
    projects = os.path.join(root, "projects")
    hits, searched, refused = [], [], []
    for source, base in (("the helper's own working directory", os.getcwd()),
                         ("the workspace it was given", workspace)):
        if not base:
            continue
        try:
            named = os.path.join(projects, project_slug(base), "%s.jsonl" % session_id)
        except OSError:
            continue
        row = {"slug_from": source, "path": named}
        try:
            row["found"] = os.path.isfile(named)
        except OSError as exc:
            row["found"] = False
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
        searched.append(row)
        if row["found"] and named not in hits:
            hits.append(named)
    if hits:
        return hits, searched, refused

    try:
        names = sorted(os.listdir(projects))
    except OSError as exc:
        refused.append({"path": projects, "error": "%s: %s" % (type(exc).__name__, exc)})
        return hits, searched, refused
    for name in names:
        candidate = os.path.join(projects, name, "%s.jsonl" % session_id)
        try:
            if os.path.isfile(candidate):
                hits.append(candidate)
        except OSError as exc:
            refused.append({"path": os.path.dirname(candidate),
                            "error": "%s: %s" % (type(exc).__name__, exc)})
    return sorted(hits), searched, refused


def _not_found(session_id, root, searched, refused, prefix):
    """The refusal, saying where it looked and what refused it."""
    where = "; ".join("%s -> %s%s" % (r["slug_from"], r["path"],
                                      "" if r.get("found") else " (absent)")
                      for r in searched) or "no named slug folder could be derived"
    denied = ("; ".join("%s (%s)" % (r["path"], r["error"]) for r in refused)
              or "nothing was refused")
    return HelperError(
        "%s no transcript named %s.jsonl exists under %s/projects. Named folders tried: %s. "
        "Directories that refused to be read: %s."
        % (prefix, session_id, root, where, denied), 3)


def test_mode():
    """The fixture interface of ruling E9-28, never on at run time."""
    return os.environ.get(TEST_FLAG) == "1"


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


def assert_fixture_allowed(explicit, session_id):
    """Ruling E9-28: the fixture flags are a usage error outside the tests."""
    if (explicit or session_id) and not test_mode():
        raise HelperError(
            "--transcript and --session-id are the fixture interface and are accepted only "
            "under %s=1 (ruling E9-28); at run time the session's own record is found through "
            "%s" % (TEST_FLAG, SESSION_ID_VAR),
            2,
        )


def _first_session_id(path):
    """The `sessionId` of the file's first turn-shaped record, if it has one."""
    for record in _records(path):
        if record.get("type") in ("user", "assistant") and record.get("sessionId"):
            return record["sessionId"]
    return None


def _bind_session(path, session_id):
    """Every turn-shaped record of the file must carry this session's own id.

    Ruling E9-28: the record is the session's or the helper refuses. A file
    whose `user` or `assistant` records name another `sessionId` is another
    session's record however it got there.
    """
    seen = set()
    turns = 0
    for record in _records(path):
        if record.get("type") not in ("user", "assistant"):
            continue
        turns += 1
        other = record.get("sessionId")
        if other:
            seen.add(other)
    foreign = sorted(value for value in seen if value != session_id)
    if foreign:
        raise HelperError(
            "%s holds records of another session (sessionId %s, expected %s); ruling E9-28 "
            "binds the turn list to this session's own record" % (path, ", ".join(foreign), session_id),
            3,
        )
    return turns


def _bind_workspace(path, workspace):
    """One record of this session must name the workspace as its `cwd`.

    Measured 2026-09-14 over the packet's six sessions: records with no `cwd`
    field exist in every transcript (the bookkeeping types `queue-operation`,
    `atis-latch`, `last-prompt` and `ai-title`), so the binding is "a record of
    this session names the workspace", never "every record does", and the loop
    below skips a record without the field rather than reading it as a
    mismatch.
    """
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
        % (path, target, ", ".join(seen) or "none"),
        3,
    )


def find_transcript(explicit=None, session_id=None, cfg=None, workspace=None):
    """Locate the running session's own transcript (ruling E9-28).

    Returns (path, session_id, discovery, note). One route at run time: the
    harness's own ``CLAUDE_CODE_SESSION_ID`` in the tool shell's environment
    (measured 2026-09-14 in an interactive session and in a headless
    ``claude -p`` session), resolved to ``<config>/projects/*/<id>.jsonl``,
    bound to the session by every turn record's ``sessionId`` and by a record
    whose ``cwd`` is the workspace. Absent, ambiguous or mismatched: exit 3
    naming it. There is no fallback to another workspace's transcript, to the
    newest file, or to a hook payload.

    ``--transcript`` and ``--session-id`` are the fixture interface and are
    accepted only under ``RECHECK_ADAPTER_TEST=1``; at run time they are a
    usage error (exit 2).
    """
    root = cfg or config_dir()
    assert_fixture_allowed(explicit, session_id)

    if explicit:
        path = os.path.abspath(os.path.expanduser(explicit))
        if not os.path.isfile(path):
            raise HelperError("transcript not found: %s" % path, 3)
        # A fixture file is not named for its session, so the id comes from the
        # record itself and the binding below still holds every turn record to
        # it.
        sid = (
            session_id
            or _first_session_id(path)
            or os.path.splitext(os.path.basename(path))[0]
        )
        discovery = "fixture interface: --transcript under %s=1" % TEST_FLAG
    elif session_id:
        hits, searched, refused = transcript_hits(root, session_id, workspace)
        if not hits:
            raise _not_found(session_id, root, searched, refused,
                             "no transcript for session %s:" % session_id)
        path, sid = hits[0], session_id
        discovery = "fixture interface: --session-id under %s=1" % TEST_FLAG
    else:
        env_sid = os.environ.get(SESSION_ID_VAR)
        if not env_sid:
            raise HelperError(
                "%s is not set in this tool shell, so the session's own record cannot be "
                "identified; ruling E9-28 takes no other route (no newest-file fallback, no "
                "other workspace's transcript)" % SESSION_ID_VAR,
                3,
            )
        hits, searched, refused = transcript_hits(root, env_sid, workspace)
        if not hits:
            raise _not_found(env_sid, root, searched, refused,
                             "%s is %s but" % (SESSION_ID_VAR, env_sid))
        if len(hits) > 1:
            raise HelperError(
                "%s is %s and %d transcripts under %s/projects are named for it (%s); the "
                "discovery is ambiguous and ruling E9-28 refuses it"
                % (SESSION_ID_VAR, env_sid, len(hits), root, ", ".join(hits)),
                3,
            )
        path, sid = hits[0], env_sid
        discovery = ("the harness's own %s, bound to this session's records, found in %s"
                     % (SESSION_ID_VAR,
                        "the session's own named slug folder"
                        if any(r.get("found") for r in searched)
                        else "a scan of %s/projects" % root))

    turns = _bind_session(path, sid)
    if not turns:
        raise HelperError(
            "unusable session record: no user or assistant turns in %s (ruling E9-29)" % path, 3
        )
    note = _bind_workspace(path, workspace)
    return path, sid, discovery, note


def turn_ref(session_id, uuid):
    return "claude-code:session %s:msg %s" % (session_id, uuid)


# A `user` record the harness wrote itself rather than the person typing. The
# skill body a Skill call delivers arrives as a `user` record of text blocks
# carrying isMeta, turnCompanion and sourceToolUseID (measured 2026-09-14: the
# delivery probe's 25,659-byte body landed that way in the installed probe's
# transcript.jsonl:20), so the E9 section 6 rule on its own would attribute a
# delivered skill body to the user and let a grant cite it. These keys keep it
# out of the map.
HARNESS_WRITTEN_KEYS = ("isMeta", "turnCompanion", "sourceToolUseID", "toolUseResult")


def harness_written(record):
    """Ruling E9-22: the marker's PRESENCE, not its truthiness.

    `toolUseResult: {}`, `isMeta: false` and `sourceToolUseID: null` are the
    harness's marks as much as a truthy value is, and a truthiness test let a
    record carrying `toolUseResult: {}` become a user grant (Astra's finding 3).
    Recounted 2026-09-14 over every `transcript.jsonl` in the lane's packet --
    21 files, 1,554 records, 263 `user` records, of which 243 carry at least one
    of the four keys (`toolUseResult` 223, `isMeta` 20, `turnCompanion` 20,
    `sourceToolUseID` 17) and not one carries any of them with an empty, false
    or null value; the other 20 carry no marker and are the real user turns. So
    presence changes nothing on the harness's real records and closes the forged
    one. The file list and per-file counts are the packet's own
    `targeted/marker-presence-witness.txt`.
    """
    for key in HARNESS_WRITTEN_KEYS:
        if key in record:
            return key
    return None


def _message_content(record):
    """The `content` of a record's message, or None when `message` is not an object.

    E10-68 defect 2: Claude Code writes `system` events of subtype `permission_denied` whose
    `message` is a plain STRING, and `(record.get("message") or {}).get("content")` raises
    `AttributeError: 'str' object has no attribute 'get'` on one.
    """
    message = record.get("message")
    return message.get("content") if isinstance(message, dict) else None


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
    # E10-68 defect 2: a `message` that is not an object (Claude Code's system
    # `permission_denied` events carry a plain string) is read as carrying no content.
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
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
    """Build the turn map and the model facts from one transcript.

    Every reference is composed from the session id the discovery bound
    (ruling E9-28), never from a value inside the record, so a record smuggled
    in under another `sessionId` cannot name a turn of another session. The
    harness fields the session's own records carry are collected too:
    `permissionMode`, `entrypoint` and `version` (measured 2026-09-14 on the
    `user` records of every live session).
    """
    attribution = {}
    users = []
    models = []
    efforts = []
    permission_modes = []
    entrypoints = []
    versions = []
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
        if record.get("permissionMode"):
            permission_modes.append(record["permissionMode"])
        if record.get("entrypoint"):
            entrypoints.append(record["entrypoint"])
        if record.get("version"):
            versions.append(record["version"])
        uuid = record.get("uuid")
        if not uuid:
            counts["unmapped_other"] += 1
            continue
        if record.get("isSidechain"):
            counts["unmapped_sidechain"] += 1
            continue
        ref = turn_ref(session_id, uuid)
        if kind == "assistant":
            attribution[ref] = "assistant"
            counts["assistant_turns"] += 1
            message = record.get("message")
            message = message if isinstance(message, dict) else {}
            if message.get("model"):
                models.append(message["model"])
            if record.get("effort"):
                efforts.append(record["effort"])
            continue
        if is_user_turn(record):
            attribution[ref] = "user"
            counts["user_turns"] += 1
            users.append((ref, record.get("timestamp"), user_text(record)))
        elif "toolUseResult" in record:
            counts["unmapped_tool_results"] += 1
        elif harness_written(record):
            counts["unmapped_harness_written"] += 1
        elif isinstance(_message_content(record), list):
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
        "permission_modes": permission_modes,
        "entrypoints": entrypoints,
        "versions": versions,
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


def sandbox_mode(session=None):
    """The permission mode in force, read from the harness's own record.

    Measured 2026-09-14 over the packet's six `claude -p` sessions: the
    transcript's `user` records carry `permissionMode`, `acceptEdits` on the
    first `user` record of every one of the six. That is a harness record the
    session can read about itself, so it is the source; the launcher's
    `RECHECK_HARNESS_SANDBOX` is kept only as a cross-check, and a disagreement
    is reported rather than resolved. The field is sparse, not per-record: one
    `user` record carries it in five of the six sessions and two do in the
    sixth, every other `user` record carries none, and the stream-json trace
    carries it on no `user` record at all -- which is why this reads the
    recorded values rather than the last record. Every session in the packet is
    headless, so the packet supports no claim about what an interactive
    session's first user record carries and none is made here. Where no
    permission-mode record is reachable the launcher's value, or `unknown`,
    stands.
    """
    recorded = (session or {}).get("permission_modes") or []
    launcher = os.environ.get("RECHECK_HARNESS_SANDBOX") or os.environ.get(
        "CLAUDE_CODE_PERMISSION_MODE"
    )
    if recorded:
        value = recorded[-1]
        source = "the session transcript's own permissionMode record"
        if launcher and launcher != value:
            source += " (the launcher's RECHECK_HARNESS_SANDBOX says %r; the record wins)" % launcher
        elif launcher:
            source += " (cross-checked against the launcher's RECHECK_HARNESS_SANDBOX)"
        return value, source
    if launcher:
        return launcher, "the launcher's RECHECK_HARNESS_SANDBOX (no permissionMode in the record)"
    return "unknown (no permission-mode record reachable from the session)", None


def mode_hint(session=None):
    """Whether a person can answer a question in this session.

    Measured 2026-09-14: a headless `claude -p` session's tool shell carries
    CLAUDE_CODE_SESSION_ATTENDED=0 and CLAUDE_CODE_ENTRYPOINT=sdk-cli. The
    session's own transcript records carry `entrypoint` too, `sdk-cli` on every
    record that has it in all six of the packet's sessions, which is the second
    reading. Every session in the packet is headless, so the `1`/`cli` half of
    each map below is the documented interactive value and not something the
    packet measures. Under rulings E9-33 and E9-35 the executor types no
    invocation field at all: this helper supplies `invocation.mode` from the
    harness's own record, so a headless run does not ask a question into a
    channel nobody reads.
    """
    recorded = (session or {}).get("entrypoints") or []
    record_mode = None
    if recorded:
        record_mode = {"sdk-cli": "headless", "cli": "interactive"}.get(recorded[-1])
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
        source = "%s, cross-checked against the transcript's entrypoint record %r" % (
            env_source, recorded[-1],
        )
        if env_mode != record_mode:
            return "unknown", (
                "%s says %s and the transcript's entrypoint record %r says %s; they disagree"
                % (env_source, env_mode, recorded[-1], record_mode)
            )
        return env_mode, source
    if env_mode:
        return env_mode, env_source
    if record_mode:
        return record_mode, "the transcript's own entrypoint record %r" % recorded[-1]
    return "unknown", "no attended or entrypoint record in the environment or the transcript"


def provider_route():
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK"):
        return "bedrock"
    if os.environ.get("CLAUDE_CODE_USE_VERTEX"):
        return "vertex"
    if os.environ.get("CLAUDE_CODE_USE_FOUNDRY"):
        return "foundry"
    return "anthropic"
