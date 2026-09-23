#!/usr/bin/env python3
"""The Claude Code reviewer capability for signoff-v2: the readers request, and the sidecar
readers hands back (E13 slice 3; the recheck-v2 pilot's lane C `verifier.py` shape).

*Request mode* (`--run-dir D`): the readers request block(s) for the reviewer, one per lens, built
from the request the core's `request` phase wrote at `D/request.json`, with `session_model` read
from the harness's own record of this session. Row `claude-session`, profile `repo-with-tools`,
floor `opus` are the core's; `model`, `effort`, `output_budget` and `isolation` are never written.
This helper launches nothing: the executor hands each block to `/readers`, which runs the fresh
subagent.

*Record mode* (`--sidecar FILE --run-dir D`): readers' sidecar mapped onto what the answer
carries about its reviewer (`answer_identity`: `session_id`, `model`) and the `record-answer`
flags. It never retries: SKILL.md step 3 decides the one re-send.

stdout: one JSON document; diagnostics on stderr. Exit 0 success, 2 usage, 3 a harness record or
the run's request is missing, 1 anything else. Python 3.9, standard library only.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

ROW, PROFILE, FLOOR = "claude-session", "repo-with-tools", "opus"
NEVER_WRITTEN = ("model", "effort", "output_budget", "isolation")
# readers' status vocabulary (the pilot's verifier.md section 4), plus readers' own `oversize`.
KNOWN_STATUSES = {"ok", "empty", "incomplete", "transport-failed", "timed-out", "capture-failed",
                  "cancelled", "unknown-model", "floor-refused", "profile-unsupported",
                  "version-mismatch", "lane-unavailable", "invalid-request", "unauthorized",
                  "oversize"}
LENS_RE = re.compile(r"^[a-z][a-z0-9-]*$")

EPILOG = """\
Request mode: --run-dir D [--lens NAME]... prints {"requests": [...]} with one block per lens
(default one lens, "review"): call_id <run_id>-review-<lens>, raw_path
D/readers/calls/<call_id>/raw.md, every other field as the core's request.json wrote it except
session_model, which is read from this session's transcript (the record wins over the file and a
difference is reported in _sources). The request must be the run's own: its mandate and every
document under D, its run_dir D/readers/calls. A run whose core wrote no request (the reviewing
session is the building session, so nothing is summoned) is exit 3 naming independence.

Record mode: --sidecar FILE --run-dir D maps readers' sidecar: status (oversize reported as
invalid-request), raw, model (effective_model), kind (transport); an `ok` whose raw report is
missing or empty becomes capture-failed; an `ok` that names no effective_model or transport is
exit 2. answer_identity is {"session_id": "<transport>:<call_id>", "model": effective_model},
the reviewer the answer names; record_answer.argv is the record-answer command for this run.

--transcript and --session-id are the fixture interface, test mode only (SIGNOFF_V2_ADAPTER_TEST=1).

Exit 0 success, 2 usage, 3 a harness record or the run's request is missing, 1 anything else.

Examples:
  reviewer.py --run-dir /tmp/signoff-v2/signoff-f-20260923-ab12 --lens spec --lens correctness
  reviewer.py --sidecar /tmp/signoff-v2/<run>/readers/calls/<call>/sidecar.json --run-dir <D>

Side effects: none. Nothing is written, no network, no model call.
"""


def build_parser():
    p = _common.JsonParser(prog="reviewer.py", epilog=EPILOG,
                           description="The readers request for signoff-v2's reviewer on Claude "
                                       "Code, and the sidecar map.",
                           formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-dir", default=None, help="the signoff run directory (required)")
    p.add_argument("--lens", action="append", default=[], help="a lens; repeatable (default: review)")
    p.add_argument("--sidecar", default=None, help="record mode: the readers sidecar")
    p.add_argument("--answer", default=None,
                   help="record mode: the answer file record-answer will read (default: "
                        "<run dir>/reviewer-answer.json)")
    p.add_argument("--config-dir", default=None, help="the Claude Code config directory")
    p.add_argument("--transcript", default=None, help="fixture interface, test mode only")
    p.add_argument("--session-id", default=None, help="fixture interface, test mode only")
    return p


def under(path, root):
    real, base = os.path.realpath(path), os.path.realpath(root)
    return real == base or real.startswith(base + os.sep)


def request_mode(args, run_dir):
    for lens in args.lens:
        if not LENS_RE.match(lens):
            raise _common.HelperError("--lens %r is not a lens name" % lens, 2)
    path = os.path.join(run_dir, "request.json")
    if not os.path.isfile(path):
        raise _common.HelperError(
            "%s holds no request: the core wrote none, which it does when the reviewing session "
            "is the building session (independence), or `request` has not run" % run_dir, 3)
    with open(path, "r", encoding="utf-8") as handle:
        core_request = json.load(handle)
    readers = os.path.join(run_dir, "readers")
    problems = []
    if not under(core_request.get("mandate") or "/", readers):
        problems.append("the mandate %r is not this run's own" % core_request.get("mandate"))
    for document in core_request.get("documents") or []:
        if not under(document, run_dir):
            problems.append("the document %r is outside the run" % document)
    if os.path.realpath(core_request.get("run_dir") or "/") != os.path.realpath(
            os.path.join(readers, "calls")):
        problems.append("the request's run_dir is not %s" % os.path.join(readers, "calls"))
    if problems:
        raise _common.HelperError("the request is not bound to this run: " + "; ".join(problems), 2)

    cfg = _common.config_dir(args.config_dir)
    tpath, _sid, discovery, _binding = _common.find_transcript(
        explicit=args.transcript, session_id=args.session_id, cfg=cfg)
    session = _common.read_session(tpath)
    if not session["models"]:
        raise _common.HelperError("no assistant record in %s carries message.model, so "
                                  "session_model cannot be filled" % tpath, 3)
    session_model = session["models"][-1]
    written = core_request.get("session_model")
    requests = []
    for lens in args.lens or ["review"]:
        call_id = "%s-%s" % (core_request["call_id"], lens) if args.lens else core_request["call_id"]
        block = {key: value for key, value in core_request.items() if key not in NEVER_WRITTEN}
        block.update({"call_id": call_id, "session_model": session_model,
                      "raw_path": os.path.join(readers, "calls", call_id, "raw.md"),
                      "row": ROW, "profile": PROFILE, "floor": FLOOR})
        requests.append(block)
    return {
        "requests": requests,
        "_sources": {
            "request": path,
            "session_model": ("the last non-sidechain, non-synthetic assistant record's "
                              "message.model in %s (%s)" % (tpath, discovery))
                             + ("" if written == session_model else
                                "; the core's request.json said %r and the record wins" % written),
            "lenses": args.lens or ["review (one call: no --lens given)"],
            "never_written": list(NEVER_WRITTEN),
            "row_profile_floor": "the core's request and v1 Step 0; never the executor's pick",
        },
    }


def record_mode(args, run_dir):
    path = os.path.abspath(args.sidecar)
    if not os.path.isfile(path):
        raise _common.HelperError("sidecar not found: %s" % path, 3)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            sidecar = json.load(handle)
    except ValueError as exc:
        raise _common.HelperError("sidecar is not JSON (%s): %s" % (exc, path), 1)
    if not isinstance(sidecar, dict):
        raise _common.HelperError("sidecar is not a JSON object: %s" % path, 1)
    status = sidecar.get("status")
    if status not in KNOWN_STATUSES:
        raise _common.HelperError("sidecar status %r is outside readers' vocabulary" % (status,), 2)
    raw = sidecar.get("raw_path") or sidecar.get("raw_file")
    note = sidecar.get("reason")
    if status == "oversize":
        budget = sidecar.get("budget") or {}
        status, note = "invalid-request", "oversize: estimate %s, limit %s" % (
            budget.get("estimate_tokens"), budget.get("limit"))
    if status == "ok" and (not raw or not os.path.isfile(raw) or os.path.getsize(raw) == 0):
        status, note = "capture-failed", "readers reported ok but the raw report is missing or " \
                                         "empty: %s" % raw
    identity = None
    if status == "ok":
        blank = [name for name in ("effective_model", "transport", "call_id")
                 if not (isinstance(sidecar.get(name), str) and sidecar.get(name).strip())]
        if blank:
            raise _common.HelperError("the sidecar reports ok but names no %s, so the answer "
                                      "cannot say which reviewer ran" % ", ".join(blank), 2)
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
                     "retry": "never here: SKILL.md step 3 decides the one re-send"},
    }


def main():
    args = build_parser().parse_args()
    if not args.run_dir:
        raise _common.HelperError("--run-dir is required", 2)
    run_dir = os.path.abspath(args.run_dir)
    if args.sidecar:
        return record_mode(args, run_dir)
    return request_mode(args, run_dir)


if __name__ == "__main__":
    sys.exit(_common.run("reviewer.py", main))
