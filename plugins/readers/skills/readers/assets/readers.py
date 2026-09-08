#!/usr/bin/env python3
"""readers — the runner behind the loop's reader component.

Standard library only; compatible with Python 3.9.

Usage:
  readers --version
  readers validate <request.json | ->
  readers suggest <row>[,<row>...] --run <run id> [--run-dir <dir>] [--floor <floor>]
  readers compose <request.json | -> [--no-workflow]
                                        host lanes, step 1: pre-send checks, the working directory,
                                        the composed prompt (<call dir>/prompt.md) and, on the
                                        Workflow route, the script (<call dir>/reader.workflow.js)
  readers record <request.json | -> --capture <file> [--tool-calls <n>] [--transport-status <text>]
  readers record <request.json | -> --failed <reason> [--status <status>] [--capture <partial file>]
                                        host lanes, step 2: guards, raw.md, the sidecar
  readers <request.json | ->            run one call (the request on stdin with -)

Slice A carries the contract's pre-send checks, the roster, and the GPT lane
(codex exec). Slice B adds the OpenRouter adapter (deepseek, qwen), the last-pick
memory in the checkout, the `suggest` step, the run-wide freeze (snapshot), and the
canned transport hooks. Slice C adds the host lanes' two steps: `compose` (the skill body
runs the lane with what it prints) and `record` (the body hands the capture back), so a host
sidecar has the same shape and passed the same checks as a portable one.
"""
import errno
import fnmatch
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

PROTOCOL_VERSION = 1
ADAPTER_VERSION = "slice-c-fix-2026-09-06"
HERE = os.path.dirname(os.path.abspath(__file__))
ROSTER_PATH = os.path.join(HERE, "roster.json")
# The last-pick memory lives in the tony-skills checkout (blueprint assumption 1), never in the
# installed plugin cache; the roster is always read beside this script.
DEFAULT_CHECKOUT = os.path.join(os.path.expanduser("~"), "Developer", "tony-skills")
MEMORY_REL = os.path.join("plugins", "readers", "last-picks.json")
MEMORY_SEED = {"protocol_version": PROTOCOL_VERSION, "picks": {}}
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
CODEX_MODELS_CACHE = os.path.join(os.path.expanduser("~"), ".codex", "models_cache.json")
PROFILES = ("starved", "packet-only", "repo", "repo-with-tools")
WORKFLOW_TEMPLATE = os.path.join(HERE, "claude-boxes.workflow.js")
HOST_TRANSPORTS = ("claude-subagent", "antigravity-mcp")
# statuses the skill body may report for a host call that produced no usable capture
HOST_FAIL_STATUSES = ("transport-failed", "lane-unavailable", "timed-out", "cancelled", "empty", "incomplete")
STATUSES = (
    "ok", "empty", "incomplete", "oversize", "invalid-request", "lane-unavailable",
    "unauthorized", "floor-refused", "unknown-model", "profile-unsupported",
    "version-mismatch", "transport-failed", "capture-failed", "cancelled", "timed-out",
)
HOME_PROVIDER = "anthropic"   # Claude rows never need the authorized flag; every other provider is outside
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
# The child's environment is built from this list and nothing else (a credential in the
# parent's environment never reaches the model's sandbox).
CHILD_ENV_KEYS = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "USER", "SHELL", "CODEX_HOME")
BYTES_PER_TOKEN = 3.5
HEADROOM = 1.10
RESULT_FIELDS = (
    "status", "reason", "call_id", "run_id", "run_dir", "row", "transport", "kind",
    "override_source", "requested_model", "effective_model", "requested_effort",
    "effective_effort", "envelope", "budget_method", "budget", "protocol_version",
    "adapter_version", "mandate_hash", "packet_hash", "profile", "workdir",
    "workdir_instruction_files", "isolation", "parity", "raw_text", "raw_file",
    "raw_hash", "raw_path", "diagnostics", "dispatch_log", "exit_code", "generation_id",
    "response_raw", "memory", "snapshot", "snapshot_fault", "canned", "session_model", "sidecar", "started_at",
    "ended_at", "duration_s",
)


class Refuse(Exception):
    def __init__(self, status, reason, extra=None, nowrite=False):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.extra = extra or {}
        # nowrite: the refusal is returned but never written as the call's sidecar, so a composed call whose
        # reader already ran keeps its id free for the real record (a usage slip must not burn a paid reply)
        self.nowrite = nowrite


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_roster():
    with open(ROSTER_PATH) as f:
        return json.load(f)


# ---------- the last-pick memory (Slice B R4) ----------

def checkout_root():
    return os.path.abspath(os.path.expanduser(os.environ.get("READERS_CHECKOUT") or DEFAULT_CHECKOUT))


def memory_path():
    return os.path.join(checkout_root(), MEMORY_REL)


def memory_status():
    """'ok' or 'unavailable: <reason>'. The checkout and the memory file's directory must exist and be
    writable; an existing file must parse. Nothing is created anywhere when it is unavailable."""
    root = checkout_root()
    if not os.path.isdir(root):
        return "unavailable: checkout %s not found" % root
    p = memory_path()
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        return "unavailable: %s not found" % d
    if not os.access(d, os.W_OK):
        return "unavailable: %s not writable" % d
    if os.path.exists(p):
        if not os.access(p, os.R_OK | os.W_OK):
            return "unavailable: %s not readable and writable" % p
        try:
            with open(p) as f:
                data = json.load(f)
            if not isinstance(data, dict) or not isinstance(data.get("picks"), dict):
                return "unavailable: %s is not a picks file" % p
        except (OSError, ValueError) as e:
            return "unavailable: %s unreadable (%s)" % (p, e)
    return "ok"


def memory_read():
    p = memory_path()
    if not os.path.exists(p):
        return json.loads(json.dumps(MEMORY_SEED))
    with open(p) as f:
        return json.load(f)


class MemoryLock(object):
    """Exclusive creation of <memory>.lock beside the file: one writer at a time across processes.
    A lock older than STALE_S is broken (a crashed writer). The lock file never outlives the write."""
    STALE_S = 60.0
    WAIT_S = 5.0

    def __init__(self, path):
        self.lock = path + ".lock"
        self.fd = None

    def __enter__(self):
        deadline = time.time() + self.WAIT_S
        while True:
            try:
                self.fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(self.fd, str(os.getpid()).encode())
                return self
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                try:
                    if time.time() - os.stat(self.lock).st_mtime > self.STALE_S:
                        os.remove(self.lock)
                        continue
                except OSError:
                    continue
                if time.time() > deadline:
                    raise OSError("memory lock %s held for over %ds; pick not remembered" % (self.lock, self.WAIT_S))
                time.sleep(0.02)

    def __exit__(self, *exc):
        try:
            if self.fd is not None:
                os.close(self.fd)
            os.remove(self.lock)
        except OSError:
            pass


def memory_update(mutate):
    """Atomic read-modify-write of the memory file under the lock: read, mutate(data) -> changed?,
    write to a temporary file in the same directory, rename over the original. Returns (data, status);
    every failure (lock not taken in time, unreadable file, failed write) is a status, never an exception,
    so memory trouble degrades to `unavailable` and the call goes on (R4)."""
    status = memory_status()
    if status != "ok":
        return None, status
    p = memory_path()
    try:
        with MemoryLock(p):
            data = memory_read()
            if mutate(data):
                fd, tmp = tempfile.mkstemp(prefix=".last-picks.", suffix=".tmp", dir=os.path.dirname(p))
                try:
                    with os.fdopen(fd, "w") as f:
                        json.dump(data, f, indent=2, sort_keys=True)
                        f.write("\n")
                    os.replace(tmp, p)
                except Exception:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                    raise
    except (OSError, ValueError) as e:
        return None, "unavailable: %s" % e
    return data, "ok"


def typed_pick(req, row):
    """The id Tony typed for this call when it is a real pick: the request's `model`, present and other than the
    row's own default. The resolved `effective_model` is never the test: on claude-session the roster's
    `session` placeholder resolves to the harness-reported id, which is not a pick and is never remembered."""
    m = req.get("model")
    return m if m and m != row["model"] else None


def remember_pick(row, model):
    """Written when a call is dispatched with an explicit pick that differs from the row's default."""
    def mutate(data):
        data.setdefault("picks", {})[row["id"]] = {
            "model": model, "date": now()[:10], "row_default": row["model"], "dropped": None,
        }
        return True
    _, status = memory_update(mutate)
    if status == "ok":
        return "ok: remembered %s for %s at %s" % (model, row["id"], memory_path())
    return "%s; pick %s for %s not remembered" % (status, model, row["id"])


def pick_entry(picks, row):
    """The remembered pick for a row when one exists, is not dropped, differs from the row's default,
    and was made against the row's current default (a bumped row's pick is not used; suggest drops it)."""
    if not isinstance(picks, dict):
        return None
    e = (picks.get("picks") or {}).get(row["id"])
    if not isinstance(e, dict) or e.get("dropped") or not e.get("model"):
        return None
    if e.get("row_default") != row["model"] or e["model"] == row["model"]:
        return None
    return e


# ---------- the run-wide freeze (Slice B R6) ----------

def snapshot_dir(run_dir):
    return os.path.join(run_dir, "snapshot")


def read_snapshot(sd):
    with open(os.path.join(sd, "roster.json")) as f:
        roster = json.load(f)
    with open(os.path.join(sd, "meta.json")) as f:
        meta = json.load(f)
    picks = None
    mp = os.path.join(sd, "memory.json")
    if os.path.exists(mp):
        with open(mp) as f:
            picks = json.load(f)
    return roster, picks, meta.get("memory"), sd


def resolve_sources(run_dir, create, picks_override=None):
    """The roster and picks every step resolves from. With a snapshot under the run dir, that snapshot;
    else the live files, and when `create` is set the live files are frozen into <run dir>/snapshot/
    first (created exclusively: two concurrent first calls produce one snapshot, the loser reads the
    winner's). `picks_override` is the memory as the caller has already resolved it (suggest, after its
    drop pass) and is what gets frozen when this call creates the snapshot, so a drop the live file could
    not take still binds the run. Returns (roster, picks, memory status, snapshot path or None)."""
    sd = snapshot_dir(run_dir)
    if os.path.isfile(os.path.join(sd, "meta.json")):
        return read_snapshot(sd)
    roster = load_roster()
    status = memory_status()
    picks = memory_read() if status == "ok" else None
    if picks_override is not None:
        picks = picks_override
    if not create:
        return roster, picks, status, None
    os.makedirs(run_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="snapshot.tmp-", dir=run_dir)
    try:
        with open(os.path.join(tmp, "roster.json"), "w") as f:
            json.dump(roster, f, indent=2, sort_keys=True)
        if picks is not None:
            with open(os.path.join(tmp, "memory.json"), "w") as f:
                json.dump(picks, f, indent=2, sort_keys=True)
        with open(os.path.join(tmp, "meta.json"), "w") as f:
            json.dump({
                "created_at": now(), "adapter_version": ADAPTER_VERSION,
                "roster_source": ROSTER_PATH,
                "memory_source": memory_path() if status == "ok" else None,
                "memory": status if status != "ok" else "ok: %s" % memory_path(),
            }, f, indent=2, sort_keys=True)
        os.rename(tmp, sd)
    except OSError:
        # the other first call won the rename; its snapshot is complete (rename is atomic)
        shutil.rmtree(tmp, ignore_errors=True)
        if not os.path.isfile(os.path.join(sd, "meta.json")):
            raise
    return read_snapshot(sd)


def read_request(arg):
    if arg == "-":
        try:
            text = sys.stdin.read()
        except ValueError as e:
            raise Refuse("invalid-request", "request on stdin is not UTF-8 text: %s" % e)
    else:
        try:
            with open(arg, encoding="utf-8") as f:
                text = f.read()
        except (OSError, ValueError) as e:
            # ValueError covers UnicodeDecodeError (a request that is not UTF-8) and a NUL in the path
            raise Refuse("invalid-request", "request file unreadable as UTF-8 text: %s" % e)
    try:
        req = json.loads(text)
    except ValueError as e:
        raise Refuse("invalid-request", "malformed JSON: %s" % e)
    if not isinstance(req, dict):
        raise Refuse("invalid-request", "request must be a JSON object")
    return req


def resolve_run_dir(req):
    run_id = req.get("run_id") or "adhoc-%s" % uuid.uuid4().hex[:8]
    if req.get("run_dir"):
        return run_id, os.path.abspath(req["run_dir"])
    root = os.environ.get("READERS_RUN_ROOT")
    if root:
        return run_id, os.path.join(os.path.abspath(root), run_id)
    return run_id, os.path.join(os.environ.get("TMPDIR", "/tmp"), "readers", run_id)


def new_result(req, run_id, run_dir, call_id):
    r = {k: None for k in RESULT_FIELDS}
    r.update({
        "call_id": call_id, "run_id": run_id, "run_dir": run_dir,
        "row": req.get("row"), "profile": req.get("profile"),
        "protocol_version": PROTOCOL_VERSION, "adapter_version": ADAPTER_VERSION,
        "requested_model": req.get("model"), "requested_effort": req.get("effort"),
        "session_model": req.get("session_model") or None,
        "raw_text": "", "started_at": now(),
    })
    return r


# ---------- pre-send checks, in the contract's order ----------

def valid_id(s):
    """A run or call id is one path segment: no separators, not . or .., only [A-Za-z0-9._-]."""
    return isinstance(s, str) and 0 < len(s) <= 128 and set(s) <= ID_CHARS and s not in (".", "..") and not s.startswith(".")


def path_shaped(s):
    """A mandate string that looks like a path and not like prose: no whitespace, and either a path
    separator or a .md/.txt ending."""
    if not isinstance(s, str) or not s or any(ch.isspace() for ch in s):
        return False
    return "/" in s or s.lower().endswith((".md", ".txt"))


def check_validity(req, roster):
    """1. request validity -> invalid-request"""
    for k in ("row", "mandate", "profile"):
        if not req.get(k):
            raise Refuse("invalid-request", "missing required field: %s" % k)
    if "protocol_version" not in req:
        raise Refuse("invalid-request", "missing required field: protocol_version")
    for k in ("row", "profile", "run_dir", "raw_path", "workspace", "effort", "model", "floor", "session_model"):
        if req.get(k) is not None and not isinstance(req[k], str):
            raise Refuse("invalid-request", "%s must be a string" % k)
    if not isinstance(req["mandate"], str):
        raise Refuse("invalid-request", "mandate must be a string (text or a file path)")
    for k in ("run_id", "call_id"):
        if req.get(k) is not None and not valid_id(req[k]):
            raise Refuse("invalid-request", "%s must be one path segment of [A-Za-z0-9._-], not starting with a dot: %r" % (k, req[k]))
    docs = req.get("documents")
    if docs is not None and (not isinstance(docs, list) or not all(isinstance(d, str) for d in docs)):
        raise Refuse("invalid-request", "documents must be a list of file paths")
    if not (docs or req.get("workspace")):
        raise Refuse("invalid-request", "a request needs documents and/or workspace")
    if req.get("run_dir") and os.path.exists(req["run_dir"]) and not os.path.isdir(req["run_dir"]):
        raise Refuse("invalid-request", "run_dir exists and is not a directory: %s" % req["run_dir"])
    rows = {x["id"]: x for x in roster["rows"]}
    row = rows.get(req["row"])
    if row is None:
        raise Refuse("invalid-request", "unknown row id: %s" % req["row"])
    if req["profile"] not in PROFILES:
        raise Refuse("invalid-request", "unknown profile: %s" % req["profile"])
    if req.get("effort") is not None and req["effort"] not in row["efforts"]:
        raise Refuse("invalid-request", "effort %r not in row %s efforts %s" % (req["effort"], row["id"], row["efforts"]))
    ob = req.get("output_budget")
    if ob is not None:
        if not isinstance(ob, int) or isinstance(ob, bool) or ob <= 0:
            raise Refuse("invalid-request", "output_budget must be a positive integer")
        if isinstance(row["max_output"], int) and ob > row["max_output"]:
            raise Refuse("invalid-request", "output_budget %d above row max_output %d" % (ob, row["max_output"]))
    for d in req.get("documents") or []:
        if not os.path.isfile(d):
            raise Refuse("invalid-request", "document not found: %s" % d)
        try:
            with open(d, encoding="utf-8") as f:
                f.read()
        except (OSError, UnicodeDecodeError) as e:
            raise Refuse("invalid-request", "document unreadable as UTF-8 text: %s (%s)" % (d, e))
    if os.path.isfile(req["mandate"]):
        try:
            with open(req["mandate"], encoding="utf-8") as f:
                f.read()
        except (OSError, UnicodeDecodeError) as e:
            raise Refuse("invalid-request", "mandate file unreadable as UTF-8 text: %s (%s)" % (req["mandate"], e))
    elif path_shaped(req["mandate"]):
        # Tony, 2026-09-06 (Slice B handoff gate): a path-shaped mandate that is not a readable file is
        # refused, never sent verbatim as mandate text.
        raise Refuse("invalid-request", "mandate %r looks like a path (a separator or a .md/.txt ending) but is not a readable file; pass the text or an existing file" % req["mandate"])
    if req.get("workspace") and not os.path.isdir(req["workspace"]):
        raise Refuse("invalid-request", "workspace not a directory: %s" % req["workspace"])
    if req["profile"] in ("repo", "repo-with-tools") and not req.get("workspace"):
        raise Refuse("invalid-request", "profile %s needs a workspace" % req["profile"])
    if req.get("isolation") not in (None, "worktree"):
        raise Refuse("invalid-request", "isolation must be absent or 'worktree'")
    m = req.get("model")
    if m is not None and not m.strip():
        raise Refuse("invalid-request", "model is empty or whitespace; omit it or pass an id")
    if m is not None and ":online" in m:
        raise Refuse("invalid-request", "model %r: a web-search suffix (:online) is never sent by readers (parity: no :online suffix); pass the bare id" % m)
    return row


def check_version(req):
    """2. version -> version-mismatch"""
    if req.get("protocol_version") != PROTOCOL_VERSION:
        raise Refuse("version-mismatch", "request protocol_version %r, runner %d" % (req.get("protocol_version"), PROTOCOL_VERSION))


def is_outside(row):
    return row.get("provider") != HOME_PROVIDER


def check_authorization(req, row):
    """3. authorization -> unauthorized"""
    if is_outside(row) and req.get("authorized") is not True:
        raise Refuse("unauthorized", "outside row %s without the authorized flag (Tony's word in this run)" % row["id"])


def check_profile(req, row):
    """4. profile support -> profile-unsupported"""
    if req["profile"] not in row["supported_profiles"]:
        raise Refuse("profile-unsupported", "row %s does not support profile %s (supports %s)" % (row["id"], req["profile"], row["supported_profiles"]))


def check_floor(req, row, roster, picks=None):
    """5. floor and classification -> floor-refused | unknown-model"""
    floor = req.get("floor")
    if not floor:
        return
    if req.get("model") and req["model"] != row["model"]:
        raise Refuse("unknown-model", "typed id %s is not classified against floor %s" % (req["model"], floor))
    remembered = None if req.get("model") else pick_entry(picks, row)
    if remembered:
        # a remembered pick is a typed id too (suggest --floor drops it; a floor-bound dispatch never uses it)
        raise Refuse("unknown-model", "remembered pick %s for row %s is a typed id, not classified against floor %s" % (remembered["model"], row["id"], floor))
    elig = row["eligibility"]
    if elig == "eligible":
        return
    if elig == "not eligible":
        raise Refuse("floor-refused", "row %s is below floor %s" % (row["id"], floor))
    if elig == "not classified":
        raise Refuse("unknown-model", "row %s (%s) is not classified against floor %s" % (row["id"], row["model"], floor))
    # session-dependent
    sm = req.get("session_model")
    if not sm:
        raise Refuse("floor-refused", "session model unknown")
    if not any(fnmatch.fnmatch(sm, pat) for pat in roster.get("eligible_session_models", [])):
        raise Refuse("floor-refused", "session model %s is below floor %s" % (sm, floor))


def check_lane(req, row, dispatching):
    """6. lane availability -> lane-unavailable"""
    if row.get("available") is not True:
        raise Refuse("lane-unavailable", "row %s marked unavailable: %s" % (row["id"], row.get("available")))
    if row["kind"] == "host":
        if dispatching:
            raise Refuse("lane-unavailable", "host lane %s (%s) cannot run from the shell entry; summon /readers from the skill body" % (row["id"], row["transport"]))
        return
    if row["transport"] == "codex-exec" and shutil.which("codex") is None:
        raise Refuse("lane-unavailable", "codex CLI not on PATH")
    if row["credential_env"]:
        key = os.environ.get(row["credential_env"], "")
        if not key:
            raise Refuse("lane-unavailable", "credential %s not set in the environment" % row["credential_env"])
        # A value with a CR, LF, or NUL cannot be a header (http.client would raise with the value in its
        # message); refuse pre-send so a malformed credential never reaches an exception text, a sidecar, or stdout.
        if any(ch in key for ch in "\r\n\0") or not key.strip():
            raise Refuse("lane-unavailable", "credential %s is malformed (a line break, NUL, or only whitespace); fix the exported value" % row["credential_env"])


def mandate_text(req):
    m = req["mandate"]
    if isinstance(m, str) and os.path.isfile(m):
        with open(m, encoding="utf-8") as f:
            return f.read()
    return str(m)


def packet_names(req):
    """One name per document, unique within the request: the basename, then -2, -3 on a collision.
    The prompt's DOCUMENT labels and the packet-only copies use the same names, so they agree."""
    names, seen = [], {}
    for d in req.get("documents") or []:
        base = os.path.basename(d)
        n = seen.get(base, 0) + 1
        seen[base] = n
        if n == 1:
            names.append(base)
        else:
            stem, ext = os.path.splitext(base)
            names.append("%s-%d%s" % (stem, n, ext))
    return names


CLAUDE_PREFIX = """READER INSTRUCTIONS (fixed by readers; the mandate follows them):
- You are a cold reader. Report everything you find, low-confidence findings included; never self-censor or pre-filter. Your final message is the report and is captured verbatim.
- Use no web tool of any kind (no search, no fetch, no browser), under any profile.
- Use no other model, no MCP tool, and no outbound service.
- Do not summon /readers, do not use the Skill tool, and do not spawn agents."""
CLAUDE_PROFILE_LINES = {
    "starved": "- Access profile starved: read no files and use no tools at all; answer from this message alone.",
    "packet-only": "- Access profile packet-only: read no files and use no tools at all; the documents are in this message.",
    "repo": "- Access profile repo: you may read files inside the workspace %s and nowhere else; run nothing.",
    "repo-with-tools": "- Access profile repo-with-tools: you may read files and run tests inside the workspace %s; writes only to scratch and ignored caches, never a tracked file. When the sandbox stops an execution you needed, report \"verification blocked\" for that check and never mark it checked.",
}
GEMINI_PREFIX = """READER INSTRUCTIONS (fixed by readers; the mandate follows them):
- You are a cold reader. Report everything you find; your reply is captured verbatim.
- Use no web search or fetch tool.
- Use no other model, no MCP tool, and no outbound service.
- %s"""
GEMINI_PROFILE_LINES = {
    "starved": "Access profile starved: your working directory is empty on purpose; answer from this message alone.",
    "packet-only": "Access profile packet-only: your working directory holds copies of the documents in this message and nothing else.",
    "repo": "Access profile repo: your working directory is the workspace to read.",
}


def host_prefix(req, row):
    """The fixed instruction a host reader receives ahead of the mandate (Slice C R3, R4); portable rows get none."""
    if row is None:
        return None
    if row["transport"] == "claude-subagent":
        line = CLAUDE_PROFILE_LINES[req["profile"]]
        if "%s" in line:
            line = line % os.path.abspath(req["workspace"])
        return CLAUDE_PREFIX + "\n" + line
    if row["transport"] == "antigravity-mcp":
        return GEMINI_PREFIX % GEMINI_PROFILE_LINES[req["profile"]]
    return None


def compose(req, row=None):
    """The mandate at the top (a host row's fixed prefix above it), then each document delimited as evidence."""
    prefix = host_prefix(req, row)
    parts = ([prefix, ""] if prefix else []) + [mandate_text(req).rstrip("\n"), ""]
    for d, name in zip(req.get("documents") or [], packet_names(req)):
        with open(d, encoding="utf-8") as f:
            body = f.read()
        parts += ["<<<DOCUMENT %s>>>" % name, body.rstrip("\n"), "<<<END DOCUMENT>>>", ""]
    if req.get("workspace") and not req.get("documents"):
        parts += ["<<<WORKSPACE>>>", "Your working directory holds the material to read.", "<<<END WORKSPACE>>>", ""]
    return "\n".join(parts)


def check_budget(req, row, prompt, result):
    """7. budget -> oversize"""
    window = row["context_window"]
    ob = req.get("output_budget")
    est = int(len(prompt.encode("utf-8")) / BYTES_PER_TOKEN * HEADROOM)
    if not isinstance(window, int):
        result["budget_method"] = "skipped (window unknown)"
        result["budget"] = {"estimate_tokens": est, "limit": None}
        return
    if ob is not None:
        limit = window - ob
        method = "bytes/3.5 +10%% headroom vs window %d minus output_budget %d" % (window, ob)
    elif isinstance(row["max_output"], int):
        limit = window - row["max_output"]
        method = "bytes/3.5 +10%% headroom vs window %d minus max_output %d" % (window, row["max_output"])
    else:
        limit = window
        method = "window-only (row max_output unknown): bytes/3.5 +10%% headroom vs window %d" % window
    result["budget_method"] = method
    result["budget"] = {"estimate_tokens": est, "limit": limit}
    if est > limit:
        raise Refuse("oversize", "estimated %d tokens exceeds limit %d (%s)" % (est, limit, method),
                     {"budget": result["budget"]})


def resolve_model(req, row, result, picks=None):
    """An explicit pick first (Tony's word: a typed id, the row's own default included), then the
    remembered pick from the run's snapshot, then the roster default. A typed id that equals the row
    default is an explicit pick of the default (recorded so, envelope the row) and is never remembered."""
    remembered = pick_entry(picks, row)
    if req.get("model"):
        result["override_source"] = "explicit pick"
        result["effective_model"] = req["model"]
        result["envelope"] = row["id"] if req["model"] == row["model"] else "inherited from %s" % row["id"]
    elif remembered:
        result["override_source"] = "remembered pick"
        result["effective_model"] = remembered["model"]
        result["envelope"] = "inherited from %s" % row["id"]
    else:
        result["override_source"] = "roster default"
        result["effective_model"] = row["model"]
        result["envelope"] = row["id"]
    if row["id"] == "claude-session" and result["effective_model"] == row["model"] and req.get("session_model"):
        # the row inherits the session (the roster default, or its placeholder typed by mistake): the id the
        # harness reports for the session is the effective model
        result["effective_model"] = req["session_model"]
    result["effective_effort"] = req.get("effort") or row["effort_default"] or None
    result["transport"] = row["transport"]
    result["kind"] = row["kind"]
    result["isolation"] = row["isolation"].get(req["profile"], "unmeasured")
    if req.get("isolation") == "worktree":
        # the request asked for the Agent tool's worktree isolation; the sidecar says so (Slice C R3)
        result["isolation"] = "worktree"
    result["parity"] = row["parity"].get(req["profile"])


# ---------- transport test hooks (Slice B R8) ----------

def canned_hook(env_key, result):
    """A canned transport reply stands in for the network or the child only under READERS_TEST=1.
    Set without it, the call is transport-failed and nothing is sent. The sidecar records the hook."""
    v = os.environ.get(env_key)
    if not v:
        return None
    if os.environ.get("READERS_TEST") != "1":
        raise Refuse("transport-failed", "canned response outside test (%s is set without READERS_TEST=1); nothing sent" % env_key)
    result["canned"] = "%s=%s" % (env_key, v)
    return v


def log_dispatch(call_dir, line):
    with open(os.path.join(call_dir, "dispatch.log"), "a") as f:
        f.write("%s %s\n" % (now(), line))


# ---------- the GPT adapter (codex exec) ----------

def prepare_workdir(req, call_dir):
    profile = req["profile"]
    if profile == "starved":
        wd = os.path.join(call_dir, "work")
        os.makedirs(wd, exist_ok=True)
        return wd
    if profile == "packet-only":
        wd = os.path.join(call_dir, "packet")
        os.makedirs(wd, exist_ok=True)
        for d, name in zip(req.get("documents") or [], packet_names(req)):
            shutil.copyfile(d, os.path.join(wd, name))
        return wd
    return os.path.abspath(req["workspace"])


def instruction_files(wd):
    return [n for n in ("AGENTS.md", "CLAUDE.md") if os.path.exists(os.path.join(wd, n))]


def child_env():
    return {k: os.environ[k] for k in CHILD_ENV_KEYS if k in os.environ}


def read_events(events):
    """Parse the codex --json stream. Returns (parsed objects, non-JSON lines)."""
    objs, other = [], []
    try:
        with open(events, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    objs.append(json.loads(line))
                except ValueError:
                    other.append(line)
    except OSError:
        pass
    return objs, other


def walk(obj):
    """Every dict reachable from obj (the event, its item, its usage ...)."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            for d in walk(v):
                yield d
    elif isinstance(obj, list):
        for v in obj:
            for d in walk(v):
                yield d


def truncation_signal(objs):
    """A structural signal only, never a scan of the answer text: an event or item whose own
    status/finish/stop field says the output was cut, or a stream that never reached
    turn.completed (interrupted). Returns the signal's description or None."""
    completed = False
    for ev in objs:
        t = ev.get("type") if isinstance(ev, dict) else None
        if t == "turn.completed":
            completed = True
        for d in walk(ev):
            if d.get("finish_reason") == "length" or d.get("stop_reason") in ("max_tokens", "length"):
                return "finish_reason/stop_reason: output cap"
            if d.get("status") == "incomplete" or d.get("incomplete_details"):
                return "status: incomplete (%s)" % (d.get("incomplete_details") or "no detail")
            if d.get("truncated") is True:
                return "truncated: true"
    if objs and not completed:
        return "stream ended without turn.completed (interrupted)"
    return None


def transport_messages(objs, other, stderr_f):
    """The CLI's own error text, wherever it put it: error / turn.failed events on stdout,
    non-JSON stdout lines, then the stderr tail."""
    msgs = []
    for ev in objs:
        if not isinstance(ev, dict):
            continue
        if ev.get("type") in ("error", "turn.failed"):
            err = ev.get("error") or ev.get("message") or ev
            msgs.append(err.get("message") if isinstance(err, dict) and err.get("message") else json.dumps(err))
    msgs += other[-5:]
    try:
        with open(stderr_f, errors="replace") as f:
            tail = f.read()[-2000:].strip()
        if tail:
            msgs.append(tail)
    except OSError:
        pass
    return " | ".join(m for m in msgs if m)


def run_codex(req, row, prompt, result, call_dir, diag):
    wd = prepare_workdir(req, call_dir)
    result["workdir"] = wd
    result["workdir_instruction_files"] = instruction_files(wd)
    out_file = os.path.join(call_dir, "output.md")
    events = os.path.join(diag, "events.jsonl")
    stderr_f = os.path.join(diag, "stderr.txt")
    # R5: never read a stale file from an earlier attempt (a crashed attempt leaves no sidecar,
    # so the reuse guard does not fire); the output and partial files are removed before launch.
    for stale in (out_file, os.path.join(diag, "partial.md")):
        if os.path.exists(stale):
            os.remove(stale)
    cmd = [
        "codex", "exec", "-m", result["effective_model"],
        "-c", "model_reasoning_effort=%s" % result["effective_effort"],
        "-c", "web_search=disabled",
        "-s", "read-only", "-C", wd, "--skip-git-repo-check", "--json",
        "-o", out_file, "-",
    ]
    with open(os.path.join(diag, "command.txt"), "w") as f:
        f.write(" ".join(cmd) + "\n")
    log_dispatch(call_dir, "dispatch codex exec model=%s effort=%s profile=%s" % (result["effective_model"], result["effective_effort"], req["profile"]))
    canned = canned_hook("READERS_CANNED_CODEX", result)
    if canned:
        # the saved child: events.jsonl, output.md, stderr.txt, exit, read in place of a launch
        for name, dest in (("events.jsonl", events), ("stderr.txt", stderr_f), ("output.md", out_file)):
            src = os.path.join(canned, name)
            if os.path.exists(src):
                shutil.copyfile(src, dest)
            elif name != "output.md":
                open(dest, "wb").close()
        try:
            with open(os.path.join(canned, "exit")) as f:
                returncode = int(f.read().strip() or "0")
        except (OSError, ValueError) as e:
            raise Refuse("transport-failed", "canned codex directory %s: exit file unreadable (%s)" % (canned, e))
    else:
        with open(events, "wb") as ev, open(stderr_f, "wb") as er:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=ev, stderr=er, cwd=wd, env=child_env())
            try:
                proc.communicate(prompt.encode("utf-8"), timeout=row["timeout_s"])
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                result["exit_code"] = proc.returncode
                raise Refuse("timed-out", "codex exec exceeded timeout_s %d and was killed" % row["timeout_s"])
            except KeyboardInterrupt:
                proc.kill()
                proc.communicate()
                result["exit_code"] = proc.returncode
                raise Refuse("cancelled", "interrupted; child killed")
        returncode = proc.returncode
    result["exit_code"] = returncode
    # guards, in the contract's order
    objs, other = read_events(events)
    if returncode != 0:
        msg = transport_messages(objs, other, stderr_f)
        raise Refuse("transport-failed", "codex exec exit %d: %s" % (returncode, msg or "(no message on stdout or stderr)"))
    text = ""
    if os.path.exists(out_file):
        with open(out_file, encoding="utf-8", errors="replace") as f:
            text = f.read()
    signal = truncation_signal(objs)
    if signal:
        with open(os.path.join(diag, "partial.md"), "w", encoding="utf-8") as f:
            f.write(text)
        os.remove(out_file) if os.path.exists(out_file) else None
        raise Refuse("incomplete", "truncation signal in the event stream (%s); partial text kept in diagnostics only" % signal)
    if not text.strip():
        raise Refuse("empty", "no content or whitespace only")
    return text


# ---------- the OpenRouter adapter (Slice B R1, R2) ----------

def openrouter_message(data, raw, status):
    """The provider's own message, wherever it put it."""
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return "%s (code %s)" % (err["message"], err.get("code"))
        if err:
            return json.dumps(err)
    head = raw[:300].decode("utf-8", errors="replace").strip() if isinstance(raw, bytes) else str(raw)[:300]
    return "HTTP %s: %s" % (status, head or "(empty body)")


def run_openrouter(req, row, prompt, result, call_dir, diag):
    # the model has no filesystem: documents travel only in the prompt, there is no working directory
    result["workdir"] = None
    result["workdir_instruction_files"] = []
    if req["profile"] == "packet-only":
        result["profile"] = "packet-only (no workspace)"
    ob = req.get("output_budget")
    if ob is None and isinstance(row["max_output"], int):
        ob = row["max_output"]
    body = {"model": result["effective_model"], "messages": [{"role": "user", "content": prompt}]}
    if ob is not None:
        body["max_tokens"] = ob
    if row.get("reasoning") == "on":
        body["reasoning"] = {"enabled": True}
    # what was sent, minus the prompt (the packet hash covers it) and minus every header
    with open(os.path.join(diag, "request-meta.json"), "w") as f:
        json.dump({"url": OPENROUTER_URL, "model": body["model"], "max_tokens": body.get("max_tokens"),
                   "reasoning": body.get("reasoning"), "prompt_bytes": len(prompt.encode("utf-8"))}, f, indent=2)
    log_dispatch(call_dir, "dispatch openrouter model=%s max_tokens=%s reasoning=%s profile=%s" % (
        body["model"], body.get("max_tokens"), body.get("reasoning"), req["profile"]))
    canned = canned_hook("READERS_CANNED_RESPONSE", result)
    partial_f = os.path.join(diag, "partial.md")
    if os.path.exists(partial_f):
        os.remove(partial_f)
    if canned:
        try:
            with open(canned) as f:
                c = json.load(f)
            status = int(c["http_status"])
            raw = c["body"].encode("utf-8") if isinstance(c["body"], str) else json.dumps(c["body"]).encode("utf-8")
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise Refuse("transport-failed", "canned response %s unusable: %s" % (canned, e))
    else:
        key = os.environ.get(row["credential_env"], "")
        if any(ch in key for ch in "\r\n\0") or not key.strip():  # check_lane refused this already; belt and braces
            raise Refuse("lane-unavailable", "credential %s is malformed; nothing sent" % row["credential_env"])
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": "Bearer " + key}
        rq = urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(rq, timeout=row["timeout_s"]) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            raw = e.read()
        except socket.timeout:
            raise Refuse("timed-out", "OpenRouter request exceeded timeout_s %d" % row["timeout_s"])
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise Refuse("timed-out", "OpenRouter request exceeded timeout_s %d" % row["timeout_s"])
            raise Refuse("transport-failed", "OpenRouter request failed: %s" % reason)
        except (ValueError, UnicodeError):
            # http.client rejected the request (a header or URL it will not send); the message can carry
            # header values, so it is never repeated here
            raise Refuse("transport-failed", "OpenRouter request could not be built (http.client rejected a header or the URL); nothing sent")
        except KeyboardInterrupt:
            raise Refuse("cancelled", "interrupted by the caller")
    response_raw = os.path.join(call_dir, "response.raw")
    with open(response_raw, "wb") as f:
        f.write(raw)
    result["response_raw"] = response_raw
    result["exit_code"] = status
    with open(os.path.join(diag, "http.txt"), "w") as f:
        f.write("%d\n" % status)
    # guards, in the contract's order
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise Refuse("transport-failed", "unparseable response body (%s); %s" % (e, openrouter_message(None, raw, status)))
    if status != 200:
        raise Refuse("transport-failed", openrouter_message(data, raw, status))
    if isinstance(data, dict) and "error" in data:
        raise Refuse("transport-failed", "provider error: %s" % openrouter_message(data, raw, status))
    if not isinstance(data, dict):
        raise Refuse("transport-failed", "response is not a JSON object")
    result["generation_id"] = data.get("id")
    choice = (data.get("choices") or [{}])[0] or {}
    finish = choice.get("finish_reason")
    content = (choice.get("message") or {}).get("content") or ""
    if finish == "length":
        with open(partial_f, "w", encoding="utf-8") as f:
            f.write(content)
        raise Refuse("incomplete", "finish_reason length (output cap); partial text kept in diagnostics only")
    if not content.strip():
        raise Refuse("empty", "no content or whitespace only (finish_reason %r)" % finish)
    if finish != "stop":
        raise Refuse("transport-failed", "finish_reason %r (native %r)" % (finish, choice.get("native_finish_reason")))
    return content


# ---------- capture and evidence ----------

def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s-%d%s" % (base, n, ext)):
        n += 1
    return "%s-%d%s" % (base, n, ext)


def capture(text, req, call_dir, result):
    raw = os.path.join(call_dir, "raw.md")
    try:
        with open(raw, "w", encoding="utf-8") as f:
            f.write(text)
        result["raw_hash"] = sha256_file(raw)
    except OSError as e:
        raise Refuse("capture-failed", "could not write raw.md: %s" % e)
    result["raw_file"] = raw
    result["raw_text"] = text
    if req.get("raw_path"):
        try:
            dest = unique_path(os.path.abspath(req["raw_path"]))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(raw, dest)
            result["raw_path"] = dest
        except (OSError, TypeError, ValueError) as e:
            # not ok: the contract's raw fields are null / empty on every other status; raw.md stays on disk
            result["raw_text"], result["raw_file"], result["raw_hash"] = "", None, None
            raise Refuse("capture-failed", "raw.md is written (%s) but the raw_path copy failed: %s" % (raw, e))


def finish(result, call_dir, status, reason=None, extra=None):
    result["status"] = status
    result["reason"] = reason
    if extra:
        result.update(extra)
    result["ended_at"] = now()
    try:
        t0 = datetime.fromisoformat(result["started_at"])
        t1 = datetime.fromisoformat(result["ended_at"])
        result["duration_s"] = round((t1 - t0).total_seconds(), 3)
    except Exception:
        result["duration_s"] = None
    if call_dir is None:
        # validate: the result is returned, nothing is written (R7: a call's sidecar is never rewritten,
        # and a validate is not a call)
        return result
    sidecar = os.path.join(call_dir, "sidecar.json")
    result["sidecar"] = sidecar
    if os.path.exists(sidecar):
        # R7 backstop: never rewrite. Whatever path reached here with an existing sidecar returns without touching it.
        result["sidecar"] = None
        result["reason"] = "%s (sidecar already present at %s; not rewritten)" % (result["reason"], sidecar)
        return result
    try:
        os.makedirs(call_dir, exist_ok=True)
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
    except OSError as e:
        result["sidecar"] = None
        result["reason"] = "%s (sidecar could not be written: %s)" % (result["reason"], e)
    return result


def check_ids(req):
    """The ids and run_dir name the call directory, so they are checked before any path is joined.
    A request that fails here has no legal call directory: the refusal is returned and nothing is written."""
    for k, v in req.items():
        if isinstance(v, str) and "\0" in v:
            raise Refuse("invalid-request", "%s contains a NUL byte" % k)
        if isinstance(v, list) and any(isinstance(x, str) and "\0" in x for x in v):
            raise Refuse("invalid-request", "%s contains a NUL byte" % k)
    for k in ("run_id", "call_id"):
        if req.get(k) is not None and not valid_id(req[k]):
            raise Refuse("invalid-request", "%s must be one path segment of [A-Za-z0-9._-], not starting with a dot: %r" % (k, req[k]))
    if req.get("run_dir") is not None and not isinstance(req["run_dir"], str):
        raise Refuse("invalid-request", "run_dir must be a string")


# ---------- the host lanes' two steps (Slice C R2-R4) ----------

def claude_route(req):
    """Blueprint assumption 9: starved and packet-only, and any call with a pinned effort, run through the
    Workflow route (its run record carries the per-agent tool-call count the parity line needs); repo and
    repo-with-tools with no effort run as plain subagents through the Agent tool."""
    if req["profile"] in ("starved", "packet-only") or req.get("effort"):
        return "workflow"
    return "agent"


def js_escape(text):
    """The prompt lands in a JS template literal (box-runners.md's rule): backslashes, backticks, ${."""
    return text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def pinned_model(req, row, result):
    """The harness model name the tool receives, or None when the reader inherits the session: a pinned row's
    name always; on claude-session only a real pick (a remembered pick, or a typed id other than the roster's
    `session` placeholder), never the placeholder itself."""
    if row["id"] != "claude-session":
        return result["effective_model"]
    if result["override_source"] == "remembered pick":
        return result["effective_model"]
    if result["override_source"] == "explicit pick" and req.get("model") != row["model"]:
        return result["effective_model"]
    return None


def write_workflow(req, row, result, prompt, call_dir):
    """The Workflow script for a Claude call: the committed template with the composed prompt embedded in the
    script body (never via Workflow args, the recorded trap) and the agent options filled from the resolved
    request: the row's harness model name unless the row inherits the session, the pinned effort, worktree
    isolation when asked for."""
    with open(WORKFLOW_TEMPLATE, encoding="utf-8") as f:
        tmpl = f.read()
    target = "`__COMPOSED_PROMPT__`"
    if tmpl.count(target) != 1 or tmpl.count("__AGENT_OPTS__") != 1:
        raise Refuse("lane-unavailable", "workflow template %s is not the committed shape (one prompt placeholder, one options placeholder)" % WORKFLOW_TEMPLATE)
    opts = {"label": "reader:%s" % result["call_id"]}
    pin = pinned_model(req, row, result)
    if pin is not None:
        opts["model"] = pin
    if req.get("effort"):
        opts["effort"] = req["effort"]
    if req.get("isolation") == "worktree":
        opts["isolation"] = "worktree"
    out = tmpl.replace(target, "`" + js_escape(prompt) + "`").replace("__AGENT_OPTS__", json.dumps(opts))
    return os.path.join(call_dir, "reader.workflow.js"), out, opts


def script_path_in_cwd(result):
    """Where the Workflow tool reads the script from: the tool accepts a scriptPath only inside the session's
    working directory (or a directory the session added), never under a temp run dir (measured 2026-09-06,
    docs/evidence/readers/slice-c-host-runs.md). compose writes the script there too; record removes it."""
    return os.path.join(os.getcwd(), ".readers", result["run_id"], "%s.workflow.js" % result["call_id"])


def remove_script_in_cwd(path):
    """The working-directory copy of a Workflow script is transient: gone once the call is recorded, and its
    directories pruned when empty. Never touches anything else."""
    try:
        if path and os.path.isfile(path):
            os.remove(path)
        d = os.path.dirname(path or "")
        for _ in range(2):
            if d and os.path.basename(os.path.dirname(d)) in (".readers",) or os.path.basename(d) == ".readers":
                try:
                    os.rmdir(d)
                except OSError:
                    break
                d = os.path.dirname(d)
    except OSError:
        pass


def host_compose(req, row, prompt, result, call_dir, diag, host):
    """Step 1 of a host call: the working directory, the prompt file, the Workflow script, the dispatch line,
    and compose.json (what record reads back). Prints what the skill body needs to run the lane and nothing
    the body has to know on its own: the model id, the effort, the cwd, and the tool all come from here."""
    meta_path = os.path.join(call_dir, "compose.json")
    if os.path.exists(meta_path):
        raise Refuse("invalid-request", "call id %s is already composed (%s); the composed call keeps its id, record it or mint a new id for a retry" % (result["call_id"], meta_path), nowrite=True)
    route = None
    tool = None
    if row["transport"] == "claude-subagent":
        route = claude_route(req)
        if route == "workflow" and not os.path.isfile(WORKFLOW_TEMPLATE):
            raise Refuse("lane-unavailable", "workflow template %s missing" % WORKFLOW_TEMPLATE)
        if route == "workflow" and req["profile"] in ("starved", "packet-only"):
            # the model has no filesystem on this route: the documents travel only in the prompt
            result["workdir"] = None
            result["workdir_instruction_files"] = []
            if req["profile"] == "packet-only":
                result["profile"] = "packet-only (no workspace)"
        else:
            wd = os.path.abspath(req["workspace"]) if req.get("workspace") else None
            result["workdir"] = wd
            result["workdir_instruction_files"] = instruction_files(wd) if wd else []
    else:
        route = "mcp"
        wd = prepare_workdir(req, call_dir)
        result["workdir"] = wd
        result["workdir_instruction_files"] = instruction_files(wd)
    prompt_file = os.path.join(call_dir, "prompt.md")
    workflow_file, workflow_text, script_path = None, None, None
    if route == "workflow":
        # every check before any write: a refused compose leaves sidecar.json alone
        workflow_file, workflow_text, opts = write_workflow(req, row, result, prompt, call_dir)
        script_path = script_path_in_cwd(result)
        tool = {"name": "Workflow", "params": {"scriptPath": script_path}, "prompt_param": None, "prompt_file": prompt_file,
                "omit": ["args", "script"], "agent_options": opts,
                "capture": "the `capture` the run returns; pass the run record's per-agent toolCalls count to `readers record --tool-calls`"}
    elif route == "agent":
        params = {"subagent_type": "general-purpose",
                  "description": "readers %s %s read (%s)" % (row["id"], req["profile"], result["call_id"])}
        pin = pinned_model(req, row, result)
        if pin is not None:
            params["model"] = pin
        if req.get("isolation") == "worktree":
            params["isolation"] = "worktree"
        tool = {"name": "Agent", "params": params, "prompt_param": "prompt", "prompt_file": prompt_file,
                "omit": [], "capture": "the subagent's final message"}
    else:
        tool = {"name": "mcp__antigravity__ask_gemini", "params": {"model": result["effective_model"], "cwd": result["workdir"]},
                "prompt_param": "prompt", "prompt_file": prompt_file,
                "omit": ["effort", "mode", "skip_permissions", "add_dirs", "conversation_id", "timeout_ms"],
                "capture": "the returned text; pass the status flag the tool reported to `readers record --transport-status`"}
    if workflow_text is not None:
        # the working-directory script location is checked before anything is written, so a `.readers` that
        # is a file, or an unwritable working directory, refuses with sidecar.json alone
        sd = os.path.dirname(script_path)
        try:
            os.makedirs(sd, exist_ok=True)
        except OSError as e:
            raise Refuse("lane-unavailable", "cannot create %s for the Workflow script: %s" % (sd, e))
        if not os.access(sd, os.W_OK):
            raise Refuse("lane-unavailable", "%s is not writable for the Workflow script" % sd)
    os.makedirs(diag, exist_ok=True)
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)
    if workflow_text is not None:
        with open(workflow_file, "w", encoding="utf-8") as f:
            f.write(workflow_text)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(workflow_text)
    meta = {
        "call_id": result["call_id"], "run_id": result["run_id"], "run_dir": result["run_dir"], "call_dir": call_dir,
        "row": row["id"], "transport": row["transport"], "route": route, "profile": result["profile"],
        "effective_model": result["effective_model"], "effective_effort": result["effective_effort"],
        "workdir": result["workdir"], "workdir_instruction_files": result["workdir_instruction_files"],
        "prompt_file": prompt_file, "prompt_hash": result["packet_hash"], "workflow_file": workflow_file, "script_path": script_path,
        "tool": tool, "snapshot": result["snapshot"], "started_at": result["started_at"], "composed_at": now(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    log_dispatch(call_dir, "compose %s route=%s model=%s effort=%s profile=%s (the skill body runs the lane; record follows)" % (
        row["transport"], route, result["effective_model"], result["effective_effort"], req["profile"]))
    pick = typed_pick(req, row)
    if pick is not None:
        # Slice B R4 on the host lanes: compose is the dispatch, so the pick is remembered here (the typed id,
        # never the resolved one: a typed `session` placeholder resolves to the harness id and is no pick)
        result["memory"] = remember_pick(row, pick)
    out = dict(meta)
    out["memory"] = result["memory"]
    out["snapshot_fault"] = result["snapshot_fault"]
    out["override_source"] = result["override_source"]
    out["status"] = "composed"
    out["reason"] = "pre-send checks passed; run the lane, then `readers record`"
    return out


def host_record(req, row, prompt, result, call_dir, diag, host):
    """Step 2 of a host call: the guards the portable adapters apply, then the same capture and sidecar."""
    meta_path = os.path.join(call_dir, "compose.json")
    # Every check that can fail on the body's slip (no compose, a different request, an unreadable capture, a
    # missing count) refuses without writing: the call keeps its id free for the real record, nothing is
    # created in its directory, and the .readers/ copy stays until then.
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError) as e:
        raise Refuse("invalid-request", "no compose record for call %s (%s: %s); run `readers compose` first" % (result["call_id"], meta_path, e), nowrite=True)
    if meta.get("prompt_hash") != result["packet_hash"]:
        raise Refuse("invalid-request", "the request does not match the composed call %s (prompt hash differs); record the call with the request compose saw" % result["call_id"], nowrite=True)
    text = None
    if host.get("capture"):
        try:
            with open(host["capture"], encoding="utf-8") as f:
                text = f.read()
        except (OSError, ValueError) as e:
            raise Refuse("invalid-request", "capture file unreadable as UTF-8 text: %s (%s)" % (host["capture"], e), nowrite=True)
    n = host.get("tool_calls")
    if meta.get("route") == "workflow" and not host.get("failed") and n is None:
        raise Refuse("invalid-request", "record needs --tool-calls <count> on the Workflow route (the run record's tool_uses); call %s keeps its id" % result["call_id"], nowrite=True)
    if text is None and not host.get("failed"):
        # REVIEW.md repo check (2), MAJOR for readers: no artefact (diagnostics/, dispatch.log, the .readers/
        # copy removed) before a refusal that records nothing
        raise Refuse("invalid-request", "record needs --capture <file> or --failed <reason>", nowrite=True)
    remove_script_in_cwd(meta.get("script_path"))
    for k in ("started_at", "workdir", "workdir_instruction_files", "profile"):
        result[k] = meta.get(k)
    os.makedirs(diag, exist_ok=True)
    result["diagnostics"] = diag
    result["dispatch_log"] = os.path.join(call_dir, "dispatch.log")
    log_dispatch(call_dir, "record %s" % ("failed: %s" % host["failed"] if host.get("failed") else "capture %s" % host.get("capture")))
    if host.get("transport_status"):
        with open(os.path.join(diag, "transport-status.txt"), "w", encoding="utf-8") as f:
            f.write(host["transport_status"] + "\n")
    if host.get("failed"):
        if text:
            # partial text or a diagnostic string stays in diagnostics only, never raw.md or raw_text
            with open(os.path.join(diag, "partial.md"), "w", encoding="utf-8") as f:
                f.write(text)
        raise Refuse(host.get("status") or "transport-failed", host["failed"])
    if row["transport"] == "claude-subagent" and req["profile"] in ("starved", "packet-only"):
        if n is None:
            result["parity"] = "toolCalls: not reported"
        else:
            with open(os.path.join(diag, "tool-calls.txt"), "w") as f:
                f.write("%d\n" % n)
            if n > 0:
                with open(os.path.join(diag, "capture.md"), "w", encoding="utf-8") as f:
                    f.write(text)
                raise Refuse("transport-failed", "parity violated: the reader made %d tool call(s) under %s (toolCalls: 0 required); capture kept in diagnostics only" % (n, req["profile"]))
    elif n is not None:
        with open(os.path.join(diag, "tool-calls.txt"), "w") as f:
            f.write("%d\n" % n)
    if not text.strip():
        raise Refuse("empty", "no content or whitespace only")
    anomaly = None
    ts = (host.get("transport_status") or "").strip()
    if ts and ts.split()[0].upper() not in ("SUCCESS", "OK"):
        # vertical SKILL.md:58's rule: a complete response under an error status is delivered, anomaly recorded
        anomaly = "ok; transport reported %s (anomaly recorded; content decides)" % ts
    capture(text, req, call_dir, result)
    return finish(result, call_dir, "ok", anomaly)


ADAPTERS = {"codex-exec": None, "openrouter": None}  # filled below, after both adapters are defined
CANNED_HOOK_ENV = {"codex-exec": "READERS_CANNED_CODEX", "openrouter": "READERS_CANNED_RESPONSE"}


def run(req, dispatching, host=None):
    """dispatching: the shell entry runs the call (portable rows). host: the skill body's step for a host row,
    {"step": "compose" | "record", ...options}; the pre-send checks run the same way in every mode."""
    try:
        check_ids(req)
    except Refuse as r:
        result = new_result(req, str(req.get("run_id")), None, str(req.get("call_id")))
        return finish(result, None, r.status, r.reason)
    run_id, run_dir = resolve_run_dir(req)
    call_id = req.get("call_id") or "c-%s" % uuid.uuid4().hex[:8]
    call_dir = os.path.join(run_dir, call_id) if (dispatching or host is not None) else None
    result = new_result(req, run_id, run_dir, call_id)
    if call_dir and os.path.exists(os.path.join(call_dir, "sidecar.json")):
        # R7: a sidecar is never rewritten. A reused call id is refused without touching the call dir.
        result.update({"status": "invalid-request", "reason": "call id %s already has a sidecar under %s; mint a new call id" % (call_id, run_dir), "ended_at": now()})
        return result
    launched = False
    try:
        # R6: a dispatch freezes the roster and memory for its run on the run's first call and resolves
        # from the frozen copy afterwards; validate reads the snapshot when one exists and creates none.
        try:
            roster, picks, mem_status, snap = resolve_sources(run_dir, create=dispatching or host is not None)
        except (OSError, ValueError) as e:
            # The run dir cannot be made or the snapshot cannot be read: resolve from the live files so the
            # pre-send checks still return their own status; the fault is reported beside it, and the
            # sidecar write below says so again if it fails too (a status is never replaced by a path fault).
            roster, picks, mem_status, snap = load_roster(), None, "unavailable: run dir fault (%s)" % e, None
            result["snapshot_fault"] = "run dir %s: %s" % (run_dir, e)
        result["snapshot"] = snap
        result["memory"] = mem_status if mem_status != "ok" else "ok: %s" % memory_path()
        row = check_validity(req, roster)
        result["row"] = row["id"]
        check_version(req)
        check_authorization(req, row)
        check_profile(req, row)
        check_floor(req, row, roster, picks)
        resolve_model(req, row, result, picks)
        check_lane(req, row, dispatching and host is None)
        if host is not None and row["transport"] not in HOST_TRANSPORTS:
            raise Refuse("invalid-request", "compose/record serve host rows only; dispatch row %s (%s) with `readers <request>`" % (row["id"], row["transport"]))
        if host is not None and host.get("no_workflow") and row["transport"] == "claude-subagent" and claude_route(req) == "workflow":
            raise Refuse("lane-unavailable", "Workflow tool absent; a Claude call under %s%s needs it" % (req["profile"], " with a pinned effort" if req.get("effort") else ""))
        prompt = compose(req, row)
        result["mandate_hash"] = sha256_text(mandate_text(req))
        result["packet_hash"] = sha256_text(prompt)
        check_budget(req, row, prompt, result)
        if not dispatching and host is None:
            return finish(result, None, "ok", "valid (pre-send checks only; nothing dispatched, nothing written)")
        if host is not None:
            diag = os.path.join(call_dir, "diagnostics")
            if host["step"] == "compose":
                return host_compose(req, row, prompt, result, call_dir, diag, host)
            launched = True
            return host_record(req, row, prompt, result, call_dir, diag, host)
        adapter = ADAPTERS.get(row["transport"])
        if adapter is None:
            raise Refuse("lane-unavailable", "no adapter for transport %s in this slice" % row["transport"])
        # REVIEW.md repo check (2), MAJOR for readers: a test hook set outside READERS_TEST=1 is a transport-level
        # refusal that sends nothing, so it is raised here, before the diagnostics directory, the dispatch line, or
        # any request metadata exists; the adapter's own hook call below then only reads the reply
        hook_env = CANNED_HOOK_ENV.get(row["transport"])
        if hook_env:
            canned_hook(hook_env, result)
        diag = os.path.join(call_dir, "diagnostics")
        os.makedirs(diag, exist_ok=True)
        result["diagnostics"] = diag
        result["dispatch_log"] = os.path.join(call_dir, "dispatch.log")
        launched = True
        pick = typed_pick(req, row)
        if pick is not None:
            # R4: written when a call is dispatched with an explicit pick (the live file, never the snapshot).
            # Memory trouble never loses the call: the pick is sent regardless and the result says what happened.
            result["memory"] = remember_pick(row, pick)
        text = adapter(req, row, prompt, result, call_dir, diag)
        capture(text, req, call_dir, result)
        return finish(result, call_dir, "ok")
    except Refuse as r:
        return finish(result, None if r.nowrite else call_dir, r.status, r.reason, r.extra)
    except KeyboardInterrupt:
        return finish(result, call_dir, "cancelled", "interrupted by the caller")
    except Exception as e:  # never a traceback in place of a result (contract: JSON in every case)
        status = "capture-failed" if launched else "invalid-request"
        return finish(result, call_dir, status, "runner error (%s): %s" % (type(e).__name__, e))


ADAPTERS["codex-exec"] = run_codex
ADAPTERS["openrouter"] = run_openrouter


# ---------- suggest (Slice B R5) ----------

_catalog_cache = {}


def openrouter_ids():
    """The public model list (no credential). Returns (set of ids, None) or (None, reason)."""
    if "openrouter" not in _catalog_cache:
        try:
            with urllib.request.urlopen(urllib.request.Request(OPENROUTER_MODELS_URL, headers={"Accept": "application/json"}), timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            _catalog_cache["openrouter"] = (set(m["id"] for m in data.get("data", []) if isinstance(m, dict) and m.get("id")), None)
        except Exception as e:
            _catalog_cache["openrouter"] = (None, "OpenRouter model list unreachable (%s)" % e)
    return _catalog_cache["openrouter"]


def codex_ids():
    if "codex" not in _catalog_cache:
        try:
            with open(CODEX_MODELS_CACHE) as f:
                data = json.load(f)
            _catalog_cache["codex"] = (set(m.get("slug") for m in data.get("models", []) if isinstance(m, dict) and m.get("slug")), None)
        except Exception as e:
            _catalog_cache["codex"] = (None, "%s unreadable (%s)" % (CODEX_MODELS_CACHE, e))
    return _catalog_cache["codex"]


def existence(row, model):
    """Whether a remembered id still exists where that can be checked. Returns (True|False|None, note)."""
    if row["transport"] == "openrouter":
        ids, why = openrouter_ids()
    elif row["transport"] == "codex-exec":
        ids, why = codex_ids()
    else:
        return None, "existence not checkable for transport %s" % row["transport"]
    if ids is None:
        return None, "existence unverified: %s" % why
    return model in ids, None


def drop_reason(row, entry, floor):
    """Why a remembered pick is dropped at suggest time, or None. The three rules of R5, in order."""
    if entry.get("row_default") != row["model"]:
        return "roster default changed (%s -> %s) since the pick on %s" % (entry.get("row_default"), row["model"], entry.get("date"))
    exists, _ = existence(row, entry["model"])
    if exists is False:
        return "id %s no longer listed for transport %s" % (entry["model"], row["transport"])
    if floor and entry["model"] != row["model"]:
        return "typed id %s is not classified against floor %s" % (entry["model"], floor)
    return None


def suggest(argv):
    rows_arg, run_id, run_dir_arg, floor = None, None, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--run" and i + 1 < len(argv):
            run_id = argv[i + 1]; i += 2
        elif a == "--run-dir" and i + 1 < len(argv):
            run_dir_arg = argv[i + 1]; i += 2
        elif a == "--floor" and i + 1 < len(argv):
            floor = argv[i + 1]; i += 2
        elif a.startswith("--"):
            print(json.dumps({"status": "invalid-request", "reason": "unknown option %s" % a}))
            return 1
        else:
            rows_arg = a; i += 1
    if not rows_arg or not run_id:
        print(json.dumps({"status": "invalid-request", "reason": "usage: readers suggest <row>[,<row>...] --run <run id> [--run-dir <dir>] [--floor <floor>]"}))
        return 1
    if not valid_id(run_id):
        print(json.dumps({"status": "invalid-request", "reason": "run id must be one path segment of [A-Za-z0-9._-], not starting with a dot: %r" % run_id}))
        return 1
    _, run_dir = resolve_run_dir({"run_id": run_id, "run_dir": run_dir_arg})
    wanted = [r for r in rows_arg.split(",") if r]
    live_rows = {x["id"]: x for x in load_roster()["rows"]}
    unknown = [r for r in wanted if r not in live_rows]
    if unknown:
        print(json.dumps({"status": "invalid-request", "reason": "unknown row id(s): %s" % ", ".join(unknown)}))
        return 1
    notes = {}
    resolved = None
    frozen = os.path.isfile(os.path.join(snapshot_dir(run_dir), "meta.json"))
    if not frozen:
        # drops happen at suggest time and never after, against the live memory, before the freeze
        def mutate(data):
            changed = False
            for rid in wanted:
                e = (data.get("picks") or {}).get(rid)
                if not isinstance(e, dict) or e.get("dropped") or not e.get("model"):
                    continue
                why = drop_reason(live_rows[rid], e, floor)
                if why:
                    e["dropped"] = {"date": now()[:10], "reason": why}
                    notes[rid] = "remembered pick %s dropped: %s" % (e["model"], why)
                    changed = True
            return changed
        data, status = memory_update(mutate)
        if status == "ok":
            resolved = data
        elif memory_status() == "ok":
            # the file is there but the write did not happen (a held lock, a failed write): apply the same
            # drops to a private copy so the run freezes the dropped state, and say the record is missing
            try:
                resolved = memory_read()
                mutate(resolved)
            except (OSError, ValueError):
                resolved = None
            notes["_memory"] = "drop could not be recorded in the memory file (%s); the run's snapshot carries it, the file does not" % status
    try:
        roster, picks, mem_status, snap = resolve_sources(run_dir, create=True, picks_override=resolved)
    except OSError as e:
        print(json.dumps({"status": "invalid-request", "run_id": run_id, "run_dir": run_dir, "reason": "run dir unusable: %s" % e}, indent=2, sort_keys=True))
        return 1
    rows = {x["id"]: x for x in roster["rows"]}
    out = {"run_id": run_id, "run_dir": run_dir, "snapshot": snap, "floor": floor,
           "memory": mem_status if mem_status != "ok" else "ok: %s" % memory_path(), "suggestions": []}
    for rid in wanted:
        row = rows.get(rid) or live_rows[rid]
        e = pick_entry(picks, row)
        exists_note = None
        if e:
            ok_, exists_note = existence(row, e["model"])
        out["suggestions"].append({
            "row": rid, "model": e["model"] if e else row["model"],
            "source": "remembered pick" if e else "roster default",
            "picked_on": e.get("date") if e else None,
            "effort": row["effort_default"] or None,
            "outside": is_outside(row),
            "needs_word": is_outside(row),
            "available": row.get("available"),
            "eligibility": row["eligibility"] if not e else "not classified",
            "drop_note": notes.get(rid),
            "note": exists_note,
        })
    if "_memory" in notes:
        out["note"] = notes["_memory"]
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def host_step(step, argv):
    """`readers compose <request> [--no-workflow]` and `readers record <request> (--capture <file> [--tool-calls <n>]
    [--transport-status <text>] | --failed <reason> [--status <status>] [--capture <partial>])`. JSON on stdout in
    every case; exit 0 on `composed` (compose) or `ok` (record)."""
    host = {"step": step}
    src = None
    i = 0
    usage = "usage: readers compose <request | -> [--no-workflow] | readers record <request | -> (--capture <file> [--tool-calls <n>] [--transport-status <text>] | --failed <reason> [--status <status>] [--capture <partial file>])"
    def fail(reason):
        print(json.dumps({"status": "invalid-request", "reason": reason}, indent=2, sort_keys=True))
        return 2
    while i < len(argv):
        a = argv[i]
        if a == "--no-workflow" and step == "compose":
            host["no_workflow"] = True; i += 1
        elif a in ("--capture", "--failed", "--status", "--transport-status", "--tool-calls") and step == "record" and i + 1 < len(argv):
            host[a[2:].replace("-", "_")] = argv[i + 1]; i += 2
        elif a.startswith("--"):
            return fail("unknown or incomplete option %s; %s" % (a, usage))
        elif src is None:
            src = a; i += 1
        else:
            return fail("one request only; %s" % usage)
    if src is None:
        return fail(usage)
    if step == "record":
        if not host.get("capture") and not host.get("failed"):
            return fail("record needs --capture <file> or --failed <reason>; %s" % usage)
        if host.get("status") and host["status"] not in HOST_FAIL_STATUSES:
            return fail("--status must be one of %s" % ", ".join(HOST_FAIL_STATUSES))
        if host.get("status") and not host.get("failed"):
            return fail("--status goes with --failed")
        if host.get("tool_calls") is not None:
            try:
                host["tool_calls"] = int(host["tool_calls"])
                assert host["tool_calls"] >= 0
            except (ValueError, AssertionError):
                return fail("--tool-calls must be a non-negative integer")
    try:
        req = read_request(src)
    except Refuse as r:
        res = {k: None for k in RESULT_FIELDS}
        res.update({"status": r.status, "reason": r.reason, "protocol_version": PROTOCOL_VERSION,
                    "adapter_version": ADAPTER_VERSION, "raw_text": ""})
        print(json.dumps(res, indent=2, sort_keys=True))
        return 1
    res = run(req, dispatching=False, host=host)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res["status"] in ("ok", "composed") else 1


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if argv[0] == "--version":
        print(PROTOCOL_VERSION)
        return 0
    if argv[0] == "suggest":
        try:
            return suggest(argv[1:])
        except KeyboardInterrupt:
            print(json.dumps({"status": "cancelled", "reason": "interrupted by the caller"}))
            return 1
        except Exception as e:  # JSON in every case, never a traceback
            print(json.dumps({"status": "invalid-request", "reason": "runner error (%s): %s" % (type(e).__name__, e)}, indent=2, sort_keys=True))
            return 1
    if argv[0] in ("compose", "record"):
        return host_step(argv[0], argv[1:])
    if argv[0] == "validate":
        if len(argv) < 2:
            print("invalid-request")
            return 1
        try:
            req = read_request(argv[1])
        except Refuse as r:
            print(r.status)
            return 1
        res = run(req, dispatching=False)
        print("valid" if res["status"] == "ok" else res["status"])
        return 0 if res["status"] == "ok" else 1
    try:
        req = read_request(argv[0])
    except Refuse as r:
        res = {k: None for k in RESULT_FIELDS}
        res.update({"status": r.status, "reason": r.reason, "protocol_version": PROTOCOL_VERSION,
                    "adapter_version": ADAPTER_VERSION, "raw_text": ""})
        print(json.dumps(res, indent=2, sort_keys=True))
        return 1
    res = run(req, dispatching=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
