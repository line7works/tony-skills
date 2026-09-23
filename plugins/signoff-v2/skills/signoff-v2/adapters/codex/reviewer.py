#!/usr/bin/env python3
"""The Codex reviewer capability for signoff-v2: the readers request, and the sidecar readers
hands back (E13 full-review fix round, Astra's F6).

This helper carries no reviewer transport. The contract's sections 3 and 10 and the repository
invariant say the reviewer is summoned through `readers` and a core's helper never launches a
harness; floor, isolation, no-web and retry policy live in readers. The slice 3 helper launched a
private `codex exec` per call (the pilot's Codex `verifier.py` shape, which the slice 3 brief asked
for in error); that path is gone.

*Request mode* (`--run-dir D`): the run's own readers request is checked (its mandate and every
document under D, its run_dir D/readers/calls). Then the route: readers has NO route a Codex
session can dispatch at the Opus-class floor. Its floor-qualified rows (`claude-session`,
`claude-fable`, `claude-opus`) run on the `claude-subagent` transport through Claude Code's own
Agent and Workflow tools, which a Codex session does not have, and its `codex-exec` rows
(`gpt-astra`, `gpt-sol`) are `eligibility: not classified`, which readers refuses as
`unknown-model` whenever a floor is passed. So request mode prints `status: lane-unavailable`
with the missing capability named, writes nothing, launches nothing, and exits 3: the run stops
there, honestly, rather than reviewing through a route readers does not own.

*Record mode* (`--sidecar FILE --run-dir D`): readers' sidecar mapped onto what the answer carries
about its reviewer (`answer_identity`: `session_id`, `model`) and the `record-answer` flags, the
same map as the Claude Code helper's. It never retries: SKILL.md step 3 decides the one re-send.

stdout: one JSON document; diagnostics on stderr. Exit 0 success, 2 usage, 3 no qualified readers
route for this harness (the document says which capability is missing) or the run's request is
missing, 1 anything else. Python 3.9, standard library only, no network, no model call, no launch.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

LENS_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# readers' status vocabulary (the pilot's verifier.md section 4), plus readers' own `oversize`.
KNOWN_STATUSES = {"ok", "empty", "incomplete", "transport-failed", "timed-out", "capture-failed",
                  "cancelled", "unknown-model", "floor-refused", "profile-unsupported",
                  "version-mismatch", "lane-unavailable", "invalid-request", "unauthorized",
                  "oversize"}
MISSING_CAPABILITY = (
    "readers has no floor-qualified reader route a Codex session can dispatch: the rows that meet "
    "the Opus-class floor (claude-session, claude-fable, claude-opus) run on the claude-subagent "
    "transport through Claude Code's Agent and Workflow tools, and readers' codex-exec rows "
    "(gpt-astra, gpt-sol) are `eligibility: not classified`, which readers refuses as "
    "`unknown-model` under a floor. A qualified Codex route is readers' to add (a roster PR on "
    "Tony's word), never this adapter's")

EPILOG = """\
Request mode: --run-dir D [--workspace WS] [--lens NAME]... checks that D/request.json is the
run's own (its mandate D/readers/mandate.md, its documents under D, its run_dir
D/readers/calls, its workspace WS when given; a run whose core wrote no request is exit 3 naming
independence), then prints {"status": "lane-unavailable", "missing_capability": "...",
"requests": []} and exits 3: readers has no floor-qualified route for this harness. Nothing is
written and nothing is launched.

Record mode: --sidecar FILE --run-dir D maps readers' sidecar: status (oversize reported as
invalid-request), raw, model (effective_model), kind (transport); an `ok` whose raw report is
missing or empty becomes capture-failed; an `ok` that names no effective_model, transport or
call_id is exit 2. answer_identity is {"session_id": "<transport>:<call_id>", "model":
effective_model}; record_answer.argv is the record-answer command for this run.

Exit 0 success, 2 usage, 3 no qualified readers route for this harness or no request, 1 anything
else.

Side effects: none. Nothing is written, no network, no model call, no launch.
"""


def under(path, root):
    real, base = os.path.realpath(path), os.path.realpath(root)
    return real == base or real.startswith(base + os.sep)


class LaneUnavailable(Exception):
    """No qualified readers route for this harness: the document is printed, exit 3."""

    def __init__(self, document):
        Exception.__init__(self, document["missing_capability"])
        self.document = document


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
    raise LaneUnavailable({
        "status": "lane-unavailable",
        "missing_capability": MISSING_CAPABILITY,
        "requests": [],
        "call_id": None,
        "answer_identity": None,
        "note": "SKILL.md step 3: a reviewer the harness cannot summon through readers leaves the "
                "review incomplete, which is a STOP with this as the reason; never a review by "
                "any other route",
        "_sources": {"request": path, "route": "readers' roster and contract (floor rules, host "
                                               "rows); this helper launches nothing",
                     "launch": "none: the adapter carries no reader transport"},
    })


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
                                      "and the sidecar map. Launches nothing.", EPILOG)
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
        sys.stderr.write("reviewer.py: lane-unavailable: %s\n" % unavailable)
        sys.stdout.write(json.dumps(unavailable.document, indent=2, ensure_ascii=False) + "\n")
        raise SystemExit(3)


if __name__ == "__main__":
    sys.exit(_common.run("reviewer.py", main))
