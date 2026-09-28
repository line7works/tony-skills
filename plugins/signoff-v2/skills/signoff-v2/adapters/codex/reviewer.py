#!/usr/bin/env python3
"""The Codex reviewer capability for signoff-v2: the readers request, and the sidecar readers
hands back (E13 full-review fix round, Astra's F6; the roster lookup, E14 contract A3).

This helper carries no reviewer transport. The contract's sections 3 and 10 and the repository
invariant say the reviewer is summoned through `readers` and a core's helper never launches a
harness; floor, isolation, no-web and retry policy live in readers.

*Request mode* (`--run-dir D`): the run's own readers request is checked (its mandate and every
document under D, its run_dir D/readers/calls). Then the roster lookup, through readers as its
contract defines it. The readers component is found beside this plugin (route 3a, the checkout
sibling `<plugin root>/../readers`; route 3b, the installed `<plugin root>/../../readers/<version>`,
the highest dotted version whose folder name is its manifest's version). The rows a Codex session
can dispatch are its roster's portable rows (a host row runs through Claude Code's own tools) of
provider anthropic (signoff carries no owner word for an outside row), `eligibility: eligible`,
not marked unavailable, offering a workspace profile (`repo-with-tools`, the core's, else `repo`).
readers' own `suggest` step runs for them at the Opus-class floor with the request's run id and
run directory, which freezes the run's roster; the first row it reports eligible, available and
needing no word is the reviewer's row. One request per lens is written where readers' SKILL.md
says a caller writes one, `<request run_dir>/<call id>.json`, and printed with the command that
dispatches it (`status: ready`, exit 0); the executor hands it to readers. `lane-unavailable`
(exit 3, the missing capability named, nothing written) only when readers is not found or no row
is eligible at the floor; a refusal of `suggest` itself is printed with readers' own status and
reason (exit 3). The one child process is readers' `suggest`, which dispatches nothing.

*Record mode* (`--sidecar FILE --run-dir D`): readers' sidecar mapped onto what the answer carries
about its reviewer (`answer_identity`: `session_id`, `model`) and the `record-answer` flags, the
same map as the Claude Code helper's. It never retries: SKILL.md step 3 decides the one re-send.

stdout: one JSON document; diagnostics on stderr. Exit 0 success, 2 usage, 3 no qualified readers
route for this harness (the document says which capability is missing, or carries readers' own
refusal) or the run's request is missing, 1 anything else. Python 3.9, standard library only, no
network, no model call, no launch of a harness or a reader.
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

LENS_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# readers' status vocabulary (the pilot's verifier.md section 4), plus readers' own `oversize`.
KNOWN_STATUSES = {"ok", "empty", "incomplete", "transport-failed", "timed-out", "capture-failed",
                  "cancelled", "unknown-model", "floor-refused", "profile-unsupported",
                  "version-mismatch", "lane-unavailable", "invalid-request", "unauthorized",
                  "oversize"}
FLOOR = "opus"
HOME_PROVIDER = "anthropic"
# the core's profile first, then the one workspace profile a read-only portable row offers
WORKSPACE_PROFILES = ("repo-with-tools", "repo")
NEVER_WRITTEN = ("model", "effort", "output_budget", "isolation", "session_model", "raw_path",
                 "authorized")
READERS = "readers"
ASSETS = os.path.join("skills", "readers", "assets")
ROOT_VAR = _common.PREFIX + "_READERS_ROOT"
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
SUGGEST_TIMEOUT_S = 120
NO_ROW = ("no row of readers' roster can be dispatched from a Codex session at the Opus-class "
          "floor: that needs a portable row (a host row runs through Claude Code's own Agent and "
          "Workflow tools) of provider anthropic (signoff carries no owner word for an outside "
          "row), `eligibility: eligible` at floor `opus`, not marked unavailable, offering a "
          "workspace profile (repo-with-tools or repo). A qualified row is readers' to add (a "
          "roster PR on Tony's word), never this adapter's")

EPILOG = """\
Request mode: --run-dir D [--workspace WS] [--lens NAME]... checks that D/request.json is the
run's own (its mandate D/readers/mandate.md, its documents under D, its run_dir
D/readers/calls, its workspace WS when given; a run whose core wrote no request is exit 3 naming
independence). Then it finds readers (route 3a, then 3b), runs `readers suggest <rows> --run
<run id> --run-dir D/readers/calls --floor opus` for the roster rows a Codex session can
dispatch, writes one request per lens (default one, the core's call id; with --lens,
<call id>-<lens>) to D/readers/calls/<call id>.json for the row it names, and prints
{"status": "ready", "row", "profile", "requests": [...], "request_files": [...], "dispatch":
[{"call_id", "argv", "sidecar"}], "suggest": {...}}: exit 0. No row eligible at the floor, or
no readers: {"status": "lane-unavailable", "missing_capability": "...", "requests": []}, exit 3,
nothing written. suggest refused: readers' own status and reason, exit 3.

Record mode: --sidecar FILE --run-dir D maps readers' sidecar: status (oversize reported as
invalid-request), raw, model (effective_model), kind (transport); an `ok` whose raw report is
missing or empty becomes capture-failed; an `ok` that names no effective_model, transport or
call_id is exit 2. answer_identity is {"session_id": "<transport>:<call_id>", "model":
effective_model}; record_answer.argv is the record-answer command for this run.

Exit 0 success, 2 usage, 3 no qualified readers route for this harness or no request, 1 anything
else.

Side effects: request mode writes the request files under D/readers/calls, and readers' suggest
freezes the run there (D/readers/calls/snapshot/). Record mode writes nothing. No network, no
model call, no launch of a harness or a reader.
"""


def under(path, root):
    real, base = os.path.realpath(path), os.path.realpath(root)
    return real == base or real.startswith(base + os.sep)


class LaneUnavailable(Exception):
    """No qualified readers route for this harness, or readers refused the lookup: the document is
    printed, exit 3."""

    def __init__(self, document):
        Exception.__init__(self, document.get("missing_capability") or document.get("reason"))
        self.document = document


def _manifest(folder):
    try:
        with open(os.path.join(folder, ".claude-plugin", "plugin.json"), "r",
                  encoding="utf-8") as handle:
            body = json.load(handle)
    except (OSError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _why_not(folder):
    """None when `folder` is a usable readers root, else the reason it is not."""
    body = _manifest(folder)
    if body is None:
        return "no plugin.json" if os.path.isdir(folder) else "no such directory"
    if body.get("name") != READERS:
        return "its manifest names %r" % (body.get("name"),)
    for name in ("roster.json", "readers.py"):
        if not os.path.isfile(os.path.join(folder, ASSETS, name)):
            return "no %s" % name
    return None


def _version_key(text):
    if not re.match(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*$", text or ""):
        return None
    return tuple(int(part) for part in text.split("."))


def find_readers():
    """(root, route, looked): the test hook under the test flag, route 3a, then route 3b."""
    looked = []
    hooked = os.environ.get(ROOT_VAR)
    if hooked and os.environ.get(_common.TEST_FLAG) == "1":
        why = _why_not(hooked)
        if why is None:
            return hooked, "test hook", looked + [hooked]
        looked.append("%s (%s)" % (hooked, why))
    beside = os.path.normpath(os.path.join(PLUGIN_ROOT, os.pardir, READERS))
    why = _why_not(beside)
    if why is None:
        return beside, "3a", looked + [beside]
    looked.append("%s (%s)" % (beside, why))
    base = os.path.normpath(os.path.join(PLUGIN_ROOT, os.pardir, os.pardir, READERS))
    accepted = []
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            folder = os.path.join(base, entry)
            if not os.path.isdir(folder):
                continue
            why = _why_not(folder)
            version = (_manifest(folder) or {}).get("version")
            if why is None and version != entry:
                why = "name differs from version %s" % version
            if why is None and _version_key(entry) is None:
                why = "version not dotted integers"
            if why is None:
                accepted.append((_version_key(entry), folder))
            else:
                looked.append("%s (%s)" % (folder, why))
    else:
        looked.append("%s (no such directory)" % base)
    if accepted:
        return max(accepted)[1], "3b", looked
    return None, None, looked


def candidates(roster, core_profile):
    """[(row id, profile)] in roster order: the rows a Codex session can dispatch at the floor."""
    order = [core_profile] + [p for p in WORKSPACE_PROFILES if p != core_profile]
    out = []
    for row in roster.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if (row.get("kind") != "portable" or row.get("provider") != HOME_PROVIDER
                or row.get("eligibility") != "eligible" or row.get("available") is False):
            continue
        offered = row.get("supported_profiles") or []
        profile = next((p for p in order if p in WORKSPACE_PROFILES and p in offered), None)
        if profile and isinstance(row.get("id"), str):
            out.append((row["id"], profile))
    return out


def unavailable(capability, path, **extra):
    document = {"status": "lane-unavailable", "missing_capability": capability, "requests": [],
                "call_id": None, "answer_identity": None,
                "note": "SKILL.md step 3: a reviewer the harness cannot summon through readers "
                        "leaves the review incomplete, which is a STOP with this as the reason; "
                        "never a review by any other route",
                "_sources": dict({"request": path, "launch": "none: nothing was dispatched"},
                                 **extra)}
    return LaneUnavailable(document)


def suggest(runner, rows, run_id, calls):
    """readers' own `suggest` step: (exit code, document or None, stderr tail)."""
    argv = [sys.executable, runner, "suggest", ",".join(rows), "--run", run_id,
            "--run-dir", calls, "--floor", FLOOR]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, timeout=SUGGEST_TIMEOUT_S)
    try:
        document = json.loads(proc.stdout.decode("utf-8"))
    except ValueError:
        document = None
    return proc.returncode, document, proc.stderr.decode("utf-8", "replace")[-400:], argv


def write_request(path, block):
    text = json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            if handle.read() == text:
                return
        raise _common.Usage("%s already holds another request: a call id is single-use" % path)
    tmp = path + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def request_mode(args, run_dir):
    for lens in args.lens:
        if not LENS_RE.match(lens):
            raise _common.Usage("--lens %r is not a lens name" % lens)
    path = os.path.join(run_dir, "request.json")
    if not os.path.isfile(path):
        raise _common.Missing("%s holds no request: the core wrote none, which it does when the "
                              "reviewing session is the building session (independence), or "
                              "`request` has not run" % run_dir)
    with open(path, "r", encoding="utf-8") as handle:
        core_request = json.load(handle)
    readers = os.path.join(run_dir, "readers")
    problems = []
    if os.path.realpath(core_request.get("mandate") or "/") != os.path.realpath(
            os.path.join(readers, "mandate.md")):
        problems.append("the mandate %r is not this run's readers/mandate.md"
                        % core_request.get("mandate"))
    for document in core_request.get("documents") or []:
        if not under(document, run_dir):
            problems.append("the document %r is outside the run" % document)
    if os.path.realpath(core_request.get("run_dir") or "/") != os.path.realpath(
            os.path.join(readers, "calls")):
        problems.append("the request's run_dir is not %s" % os.path.join(readers, "calls"))
    if args.workspace and os.path.realpath(core_request.get("workspace") or "/") != \
            os.path.realpath(args.workspace):
        problems.append("the request's workspace %r is not %r"
                        % (core_request.get("workspace"), args.workspace))
    if problems:
        raise _common.Usage("the request is not bound to this run: " + "; ".join(problems))

    root, route, looked = find_readers()
    if root is None:
        raise unavailable("the readers component is not installed beside this plugin (looked in: "
                          "%s); signoff's reviewer is summoned through readers only"
                          % ", ".join(looked), path, readers_looked=looked)
    runner = os.path.join(root, ASSETS, "readers.py")
    try:
        with open(os.path.join(root, ASSETS, "roster.json"), "r", encoding="utf-8") as handle:
            roster = json.load(handle)
    except (OSError, ValueError) as exc:
        raise unavailable("the readers component at %s has no readable roster (%s)" % (root, exc),
                          path, readers_root=root, readers_route=route)
    profiles = dict(candidates(roster if isinstance(roster, dict) else {},
                               core_request.get("profile") or WORKSPACE_PROFILES[0]))
    if not profiles:
        raise unavailable(NO_ROW, path, readers_root=root, readers_route=route)
    calls = os.path.join(readers, "calls")
    code, suggested, tail, argv = suggest(runner, list(profiles), core_request["run_id"], calls)
    if code != 0 or not isinstance(suggested, dict) or "suggestions" not in suggested:
        refused = suggested if isinstance(suggested, dict) else {}
        raise LaneUnavailable({
            "status": refused.get("status") or "invalid-request",
            "reason": refused.get("reason") or ("readers' suggest exited %s: %s" % (code, tail)),
            "requests": [], "call_id": None, "answer_identity": None,
            "note": "readers refused the lookup; SKILL.md step 3: a STOP with this as the reason",
            "_sources": {"request": path, "readers_root": root, "readers_route": route,
                         "suggest": argv[1:], "launch": "none: nothing was dispatched"}})
    chosen = next((s for s in suggested["suggestions"]
                   if isinstance(s, dict) and s.get("row") in profiles
                   and s.get("eligibility") == "eligible" and s.get("available") is not False
                   and not s.get("needs_word")), None)
    if chosen is None:
        raise unavailable(NO_ROW + "; readers' suggest reported none of %s eligible at the floor"
                          % ", ".join(profiles), path, readers_root=root, readers_route=route,
                          suggest=suggested)
    row, profile = chosen["row"], profiles[chosen["row"]]
    requests, files, dispatch = [], [], []
    for lens in args.lens or [None]:
        call_id = "%s-%s" % (core_request["call_id"], lens) if lens else core_request["call_id"]
        block = {key: value for key, value in core_request.items() if key not in NEVER_WRITTEN}
        block.update({"call_id": call_id, "row": row, "profile": profile, "floor": FLOOR,
                      "run_dir": calls, "protocol_version": 1})
        target = os.path.join(calls, "%s.json" % call_id)
        write_request(target, block)
        requests.append(block)
        files.append(target)
        dispatch.append({"call_id": call_id,
                         "argv": [os.path.join(root, ASSETS, READERS), target],
                         "sidecar": os.path.join(calls, call_id, "sidecar.json")})
    return {
        "status": "ready",
        "row": row,
        "profile": profile,
        "requests": requests,
        "request_files": files,
        "dispatch": dispatch,
        "suggest": chosen,
        "call_id": requests[0]["call_id"],
        "answer_identity": None,
        "note": "the executor dispatches each request through readers (its `argv`), then hands "
                "the sidecar to record mode; SKILL.md step 3 decides the one re-send",
        "_sources": {
            "request": path,
            "readers_root": root,
            "readers_route": route,
            "suggest": argv[1:],
            "row": "the first row readers' suggest reported eligible at floor opus among the "
                   "roster's portable anthropic rows (%s)" % ", ".join(profiles),
            "profile": ("the core's" if profile == core_request.get("profile") else
                        "the row offers no %s; %s is its workspace profile"
                        % (core_request.get("profile"), profile)),
            "never_written": list(NEVER_WRITTEN),
            "launch": "none: readers dispatches the request, never this helper",
        },
    }


def record_mode(args, run_dir):
    path = os.path.abspath(args.sidecar)
    if not os.path.isfile(path):
        raise _common.Missing("sidecar not found: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            sidecar = json.load(handle)
    except ValueError as exc:
        raise ValueError("sidecar is not JSON (%s): %s" % (exc, path))
    if not isinstance(sidecar, dict):
        raise ValueError("sidecar is not a JSON object: %s" % path)
    status = sidecar.get("status")
    if status not in KNOWN_STATUSES:
        raise _common.Usage("sidecar status %r is outside readers' vocabulary" % (status,))
    raw = sidecar.get("raw_path") or sidecar.get("raw_file")
    note = sidecar.get("reason")
    if status == "oversize":
        budget = sidecar.get("budget") or {}
        status, note = "invalid-request", "oversize: estimate %s, limit %s" % (
            budget.get("estimate_tokens"), budget.get("limit"))
    if status == "ok" and (not raw or not os.path.isfile(raw) or os.path.getsize(raw) == 0):
        status, note = "capture-failed", ("readers reported ok but the raw report is missing or "
                                          "empty: %s" % raw)
    identity = None
    if status == "ok":
        blank = [name for name in ("effective_model", "transport", "call_id")
                 if not (isinstance(sidecar.get(name), str) and sidecar.get(name).strip())]
        if blank:
            raise _common.Usage("the sidecar reports ok but names no %s, so the answer cannot say "
                                "which reviewer ran" % ", ".join(blank))
        identity = {"session_id": "%s:%s" % (sidecar["transport"], sidecar["call_id"]),
                    "model": sidecar["effective_model"]}
    answer = args.answer or os.path.join(run_dir, "reviewer-answer.json")
    return {
        "status": status,
        "raw": raw,
        "model": sidecar.get("effective_model"),
        "kind": sidecar.get("transport"),
        "note": note,
        "answer_identity": identity,
        "record_answer": {"argv": ["record-answer", "--run-dir", run_dir, "--answer", answer],
                          "answer_file": answer,
                          "why": "SKILL.md step 4: the executor writes the answer from the "
                                 "reviewer's report, with answer_identity as its session_id "
                                 "and model, and hands it over with these flags"},
        "_sources": {"status": "the sidecar's status", "sidecar": path,
                     "retry": "never here: SKILL.md step 3 decides the one re-send",
                     "launch": "none: the adapter carries no reader transport"},
    }


def main():
    p = _common.parser("reviewer.py", "The readers request for signoff-v2's reviewer on Codex, "
                                      "looked up through readers' suggest at the floor, and the "
                                      "sidecar map. Launches no harness and no reader.", EPILOG)
    p.add_argument("--run-dir", required=True, help="the signoff run directory")
    p.add_argument("--workspace", default=None,
                   help="the repository root under review; the request must name it (default: "
                        "not checked)")
    p.add_argument("--lens", action="append", default=[],
                   help="a lens; repeatable (default: review)")
    p.add_argument("--sidecar", default=None, help="record mode: the readers sidecar")
    p.add_argument("--answer", default=None,
                   help="record mode: the answer file record-answer will read (default: "
                        "<run dir>/reviewer-answer.json)")
    args = p.parse_args()
    run_dir = os.path.abspath(args.run_dir)
    if args.sidecar:
        return record_mode(args, run_dir)
    try:
        return request_mode(args, run_dir)
    except LaneUnavailable as unavailable:
        sys.stderr.write("reviewer.py: %s: %s\n" % (unavailable.document["status"], unavailable))
        sys.stdout.write(json.dumps(unavailable.document, indent=2, ensure_ascii=False) + "\n")
        raise SystemExit(3)


if __name__ == "__main__":
    sys.exit(_common.run("reviewer.py", main))
