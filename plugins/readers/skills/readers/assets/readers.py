#!/usr/bin/env python3
"""readers — the runner behind the loop's reader component.

Standard library only; compatible with Python 3.9.

Usage:
  readers --version
  readers validate <request.json | ->
  readers <request.json | ->            run one call (the request on stdin with -)

Slice A carries the contract's pre-send checks, the roster, and the GPT lane
(codex exec). The OpenRouter adapter, the last-pick memory, `suggest`, and the
run-wide freeze land in Slice B; the host lanes (Claude, Gemini) run from the
skill body and hand their capture to `record` in Slice C.
"""
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

PROTOCOL_VERSION = 1
ADAPTER_VERSION = "slice-a-2026-09-06"
HERE = os.path.dirname(os.path.abspath(__file__))
ROSTER_PATH = os.path.join(HERE, "roster.json")
PROFILES = ("starved", "packet-only", "repo", "repo-with-tools")
STATUSES = (
    "ok", "empty", "incomplete", "oversize", "invalid-request", "lane-unavailable",
    "unauthorized", "floor-refused", "unknown-model", "profile-unsupported",
    "version-mismatch", "transport-failed", "capture-failed", "cancelled", "timed-out",
)
OUTSIDE_PROVIDERS = ("openai", "google", "deepseek", "alibaba")
BYTES_PER_TOKEN = 3.5
HEADROOM = 1.10
RESULT_FIELDS = (
    "status", "reason", "call_id", "run_id", "run_dir", "row", "transport", "kind",
    "override_source", "requested_model", "effective_model", "requested_effort",
    "effective_effort", "envelope", "budget_method", "budget", "protocol_version",
    "adapter_version", "mandate_hash", "packet_hash", "profile", "workdir",
    "workdir_instruction_files", "isolation", "parity", "raw_text", "raw_file",
    "raw_hash", "raw_path", "diagnostics", "dispatch_log", "exit_code", "generation_id",
    "response_raw", "memory", "snapshot", "sidecar", "started_at", "ended_at",
    "duration_s",
)


class Refuse(Exception):
    def __init__(self, status, reason, extra=None):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.extra = extra or {}


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


def read_request(arg):
    if arg == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(arg) as f:
                text = f.read()
        except OSError as e:
            raise Refuse("invalid-request", "request file unreadable: %s" % e)
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
        "raw_text": "", "started_at": now(),
    })
    return r


# ---------- pre-send checks, in the contract's order ----------

def check_validity(req, roster):
    """1. request validity -> invalid-request"""
    for k in ("row", "mandate", "profile"):
        if not req.get(k):
            raise Refuse("invalid-request", "missing required field: %s" % k)
    if "protocol_version" not in req:
        raise Refuse("invalid-request", "missing required field: protocol_version")
    if not (req.get("documents") or req.get("workspace")):
        raise Refuse("invalid-request", "a request needs documents and/or workspace")
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
    if req.get("workspace") and not os.path.isdir(req["workspace"]):
        raise Refuse("invalid-request", "workspace not a directory: %s" % req["workspace"])
    if req.get("isolation") not in (None, "worktree"):
        raise Refuse("invalid-request", "isolation must be absent or 'worktree'")
    return row


def check_version(req):
    """2. version -> version-mismatch"""
    if req.get("protocol_version") != PROTOCOL_VERSION:
        raise Refuse("version-mismatch", "request protocol_version %r, runner %d" % (req.get("protocol_version"), PROTOCOL_VERSION))


def is_outside(row):
    return row["provider"] in OUTSIDE_PROVIDERS


def check_authorization(req, row):
    """3. authorization -> unauthorized"""
    if is_outside(row) and req.get("authorized") is not True:
        raise Refuse("unauthorized", "outside row %s without the authorized flag (Tony's word in this run)" % row["id"])


def check_profile(req, row):
    """4. profile support -> profile-unsupported"""
    if req["profile"] not in row["supported_profiles"]:
        raise Refuse("profile-unsupported", "row %s does not support profile %s (supports %s)" % (row["id"], req["profile"], row["supported_profiles"]))


def check_floor(req, row, roster):
    """5. floor and classification -> floor-refused | unknown-model"""
    floor = req.get("floor")
    if not floor:
        return
    if req.get("model") and req["model"] != row["model"]:
        raise Refuse("unknown-model", "typed id %s is not classified against floor %s" % (req["model"], floor))
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
    if row["credential_env"] and not os.environ.get(row["credential_env"]):
        raise Refuse("lane-unavailable", "credential %s not set in the environment" % row["credential_env"])
    if row["transport"] == "openrouter" and dispatching:
        raise Refuse("lane-unavailable", "OpenRouter adapter lands in Slice B")


def mandate_text(req):
    m = req["mandate"]
    if isinstance(m, str) and os.path.isfile(m):
        with open(m) as f:
            return f.read()
    return str(m)


def compose(req):
    """The mandate at the top, then each document delimited as evidence."""
    parts = [mandate_text(req).rstrip("\n"), ""]
    for d in req.get("documents") or []:
        with open(d) as f:
            body = f.read()
        parts += ["<<<DOCUMENT %s>>>" % os.path.basename(d), body.rstrip("\n"), "<<<END DOCUMENT>>>", ""]
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


def resolve_model(req, row, result):
    if req.get("model") and req["model"] != row["model"]:
        result["override_source"] = "explicit pick"
        result["effective_model"] = req["model"]
        result["envelope"] = "inherited from %s" % row["id"]
    else:
        result["override_source"] = "roster default"
        result["effective_model"] = row["model"]
        result["envelope"] = row["id"]
    result["effective_effort"] = req.get("effort") or row["effort_default"] or None
    result["transport"] = row["transport"]
    result["kind"] = row["kind"]
    result["isolation"] = row["isolation"].get(req["profile"], "unmeasured")
    result["parity"] = row["parity"].get(req["profile"])


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
        for d in req.get("documents") or []:
            shutil.copyfile(d, os.path.join(wd, os.path.basename(d)))
        return wd
    return os.path.abspath(req["workspace"])


def instruction_files(wd):
    return [n for n in ("AGENTS.md", "CLAUDE.md") if os.path.exists(os.path.join(wd, n))]


TRUNCATION_MARKERS = ('"finish_reason":"length"', '"finish_reason": "length"', '"status":"incomplete"',
                      '"status": "incomplete"', 'max_output_tokens', '"reason":"max_tokens"')


def run_codex(req, row, prompt, result, call_dir, diag):
    wd = prepare_workdir(req, call_dir)
    result["workdir"] = wd
    result["workdir_instruction_files"] = instruction_files(wd)
    out_file = os.path.join(call_dir, "output.md")
    events = os.path.join(diag, "events.jsonl")
    stderr_f = os.path.join(diag, "stderr.txt")
    cmd = [
        "codex", "exec", "-m", result["effective_model"],
        "-c", "model_reasoning_effort=%s" % result["effective_effort"],
        "-c", "web_search=disabled",
        "-s", "read-only", "-C", wd, "--skip-git-repo-check", "--json",
        "-o", out_file, "-",
    ]
    with open(os.path.join(diag, "command.txt"), "w") as f:
        f.write(" ".join(cmd) + "\n")
    with open(os.path.join(call_dir, "dispatch.log"), "a") as f:
        f.write("%s dispatch codex exec model=%s effort=%s profile=%s\n" % (now(), result["effective_model"], result["effective_effort"], req["profile"]))
    with open(events, "wb") as ev, open(stderr_f, "wb") as er:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=ev, stderr=er, cwd=wd)
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
    result["exit_code"] = proc.returncode
    # guards, in the contract's order
    if proc.returncode != 0:
        tail = ""
        try:
            with open(stderr_f, errors="replace") as f:
                tail = f.read()[-2000:].strip()
        except OSError:
            pass
        raise Refuse("transport-failed", "codex exec exit %d: %s" % (proc.returncode, tail or "(no stderr)"))
    text = ""
    if os.path.exists(out_file):
        with open(out_file, errors="replace") as f:
            text = f.read()
    truncated = False
    try:
        with open(events, errors="replace") as f:
            for line in f:
                if any(m in line for m in TRUNCATION_MARKERS):
                    truncated = True
                    break
    except OSError:
        pass
    if truncated:
        with open(os.path.join(diag, "partial.md"), "w") as f:
            f.write(text)
        raise Refuse("incomplete", "truncation signal in the event stream; partial text kept in diagnostics only")
    if not text.strip():
        raise Refuse("empty", "no content or whitespace only")
    return text


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
        with open(raw, "w") as f:
            f.write(text)
        result["raw_hash"] = sha256_file(raw)
    except OSError as e:
        raise Refuse("capture-failed", "could not write raw.md: %s" % e)
    result["raw_file"] = raw
    result["raw_text"] = text
    if req.get("raw_path"):
        dest = unique_path(os.path.abspath(req["raw_path"]))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(raw, dest)
        result["raw_path"] = dest


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
    os.makedirs(call_dir, exist_ok=True)
    sidecar = os.path.join(call_dir, "sidecar.json")
    result["sidecar"] = sidecar
    with open(sidecar, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    return result


def run(req, dispatching):
    roster = load_roster()
    run_id, run_dir = resolve_run_dir(req)
    call_id = req.get("call_id") or "c-%s" % uuid.uuid4().hex[:8]
    call_dir = os.path.join(run_dir, call_id)
    result = new_result(req, run_id, run_dir, call_id)
    try:
        row = check_validity(req, roster)
        result["row"] = row["id"]
        resolve_model(req, row, result)
        check_version(req)
        check_authorization(req, row)
        check_profile(req, row)
        check_floor(req, row, roster)
        check_lane(req, row, dispatching)
        prompt = compose(req)
        result["mandate_hash"] = sha256_text(mandate_text(req))
        result["packet_hash"] = sha256_text(prompt)
        check_budget(req, row, prompt, result)
        if not dispatching:
            return finish(result, call_dir, "ok", "valid (pre-send checks only; nothing dispatched)")
        diag = os.path.join(call_dir, "diagnostics")
        os.makedirs(diag, exist_ok=True)
        result["diagnostics"] = diag
        result["dispatch_log"] = os.path.join(call_dir, "dispatch.log")
        if row["transport"] != "codex-exec":
            raise Refuse("lane-unavailable", "no adapter for transport %s in this slice" % row["transport"])
        text = run_codex(req, row, prompt, result, call_dir, diag)
        capture(text, req, call_dir, result)
        return finish(result, call_dir, "ok")
    except Refuse as r:
        return finish(result, call_dir, r.status, r.reason, r.extra)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if argv[0] == "--version":
        print(PROTOCOL_VERSION)
        return 0
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
        print(json.dumps({"status": r.status, "reason": r.reason}, indent=2))
        return 1
    res = run(req, dispatching=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
