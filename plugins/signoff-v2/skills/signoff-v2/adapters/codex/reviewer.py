#!/usr/bin/env python3
"""The Codex reviewer capability for signoff-v2 (E13 slice 3; the recheck-v2 pilot's Codex
`verifier.py` shape).

Launches ONE fresh `codex exec` reviewer per call with the mandate the core's `request` phase
wrote on stdin, captures its events, its final message (the raw report) and its own rollout, and
prints the reviewer identity the answer carries and the `record-answer` flags. The core never
launches; the executor runs this helper once per lens and writes the answer from the reports.

stdout: one JSON document; diagnostics on stderr. Exit 0 the call was made and its status is in
the document (ok, empty, transport-failed, timed-out, lane-unavailable), 2 usage (a spent call id
included), 3 a precondition is missing (the run's request, CODEX_HOME, the confinement witness,
the codex binary) and nothing launched, 1 anything else. Python 3.9, standard library only.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

TIMEOUT = 900
CANNED_VAR = _common.PREFIX + "_ADAPTER_CANNED"
EPILOG = """\
--run-dir D --workspace WS [--lens NAME]: reads D/request.json and D/readers/mandate.md (the
core's; a run whose core wrote no request is exit 3 naming independence), then runs
  codex exec -s danger-full-access -c approval_policy=never -C WS -c web_search=disabled
             --json -o D/readers/calls/<call id>/raw.md -
with the mandate on stdin, once, timeout 900 seconds, no model or effort override, no resume, no
retry. The call id is <request call_id>-<lens> (or the request's own without --lens) and is
single use. Before any launch CODEX_HOME must name a directory and this process must be confined:
CODEX_SANDBOX=seatbelt (E9-26(a)) or the sealed bench's wall witness (SB-2, SB-12 N4);
otherwise exit 3 and nothing launches (the pilot's E9-21: a second seatbelt cannot nest, so the
child runs danger-full-access inside the outer confinement).

The child's thread (thread.started) selects exactly one rollout under CODEX_HOME/sessions whose
session_meta.id is that thread; its turn_context.model is the model observed. answer_identity is
{"session_id": <child thread>, "model": <observed model>}, the reviewer the answer names;
record_answer.argv is the record-answer command for this run.

Test hook: with SIGNOFF_V2_ADAPTER_TEST=1 and SIGNOFF_V2_ADAPTER_CANNED=<dir> the launch is
replaced by <dir>/transport.json, events.jsonl, raw.md and child-rollout.jsonl.

Side effects: creates D/readers/calls/<call id>/ with raw.md, events.jsonl, stderr.log and
rollout.jsonl; launches one child. A failed call may leave its captures. No other write.
"""


def status_of(code, raw, timed_out=False):
    if timed_out:
        return "timed-out"
    if code != 0:
        return "transport-failed"
    return "ok" if raw.is_file() and raw.read_text(errors="replace").strip() else "empty"


def injected_of(records):
    """What the harness put in front of the child besides the mandate (the pilot's reading)."""
    injected = []
    for event in records:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        if event.get("type") == "session_meta" and payload.get("base_instructions"):
            injected.append("session_meta.base_instructions")
        if event.get("type") == "response_item" and payload.get("type") == "message" \
                and payload.get("role") == "developer":
            content = payload.get("content", [])
            text = content if isinstance(content, str) else "\n".join(
                x.get("text", "") for x in content if isinstance(x, dict))
            injected.extend("developer." + tag for tag in re.findall(r"<([a-z_]+)(?:\s[^>]*)?>",
                                                                     text))
    return sorted(set(injected))


def child_records(events, home, canned=None):
    threads = {e["thread_id"] for e in events if e.get("type") == "thread.started"
               and e.get("thread_id")}
    if len(threads) != 1:
        raise _common.Missing("absent or ambiguous child thread.started record")
    thread = next(iter(threads))
    if not re.fullmatch(r"[A-Za-z0-9-]+", thread):
        raise ValueError("invalid child thread id")
    if canned is not None:
        paths = [canned / "child-rollout.jsonl"] if (canned / "child-rollout.jsonl").is_file() else []
    else:
        paths = list((home / "sessions").rglob("rollout-*" + thread + ".jsonl"))
    if len(paths) != 1:
        raise _common.Missing("absent or ambiguous child rollout for " + thread)
    records = _common.read_records(paths[0])
    metas = [r.get("payload", {}) for r in records if r.get("type") == "session_meta"]
    if len(metas) != 1 or metas[0].get("id") != thread:
        raise ValueError("child rollout thread mismatch")
    return thread, records


def confinement():
    if os.environ.get("CODEX_SANDBOX") == "seatbelt":
        return "CODEX_SANDBOX=seatbelt (E9-26(a))"
    ok, why = _common.wall_witness()
    if not ok:
        raise _common.Missing("CODEX_SANDBOX=seatbelt required (E9-26(a)), or the sealed "
                              "bench's wall witness (SB-2, SB-12 N4): %s; nothing launched" % why)
    return why


def main():
    p = _common.parser("reviewer.py", "Launch one fresh codex exec reviewer for signoff-v2 and "
                                      "print the answer's reviewer identity.", EPILOG)
    p.add_argument("--run-dir", required=True, help="the signoff run directory")
    p.add_argument("--workspace", required=True, help="the repository root under review")
    p.add_argument("--lens", default=None, help="the lens this call reviews (default: none)")
    p.add_argument("--answer", default=None,
                   help="the answer file record-answer will read (default: "
                        "<run dir>/reviewer-answer.json)")
    args = p.parse_args()
    if args.lens is not None and not re.match(r"^[a-z][a-z0-9-]*$", args.lens):
        raise _common.Usage("--lens %r is not a lens name" % args.lens)
    run_dir = Path(os.path.abspath(args.run_dir))
    workspace = Path(args.workspace).resolve()
    request_path = run_dir / "request.json"
    if not request_path.is_file():
        raise _common.Missing("%s holds no request: the core wrote none, which it does when the "
                              "reviewing session is the building session (independence), or "
                              "`request` has not run" % run_dir)
    request = json.loads(request_path.read_text())
    mandate = Path(request.get("mandate") or "/").resolve()
    if mandate != (run_dir / "readers" / "mandate.md").resolve() or not mandate.is_file():
        raise _common.Usage("the request's mandate is not this run's readers/mandate.md")
    if not workspace.is_dir():
        raise _common.Missing("absent workspace: %s" % workspace)
    call_id = "%s-%s" % (request["call_id"], args.lens) if args.lens else request["call_id"]
    scratch = run_dir / "readers" / "calls" / call_id
    raw = scratch / "raw.md"
    if raw.exists() or (scratch / "events.jsonl").exists():
        raise _common.Usage("call id %s is spent: its captures exist; call ids are single use"
                            % call_id)
    canned_dir = os.environ.get(CANNED_VAR)
    if canned_dir and os.environ.get(_common.TEST_FLAG) != "1":
        raise ValueError("canned response outside test")
    home = None
    if not canned_dir:
        home = os.environ.get("CODEX_HOME")
        if not home or not Path(home).is_dir():
            raise _common.Missing("CODEX_HOME is not set or not a directory; the inherited "
                                  "child home is required (E9-25); nothing launched")
        confinement()
        if not shutil.which("codex"):
            raise _common.Missing("missing binary: codex; nothing launched")
    scratch.mkdir(parents=True, exist_ok=True)
    events_path, err_path = scratch / "events.jsonl", scratch / "stderr.log"
    timed = False
    if canned_dir:
        source = Path(canned_dir)
        fixture = json.loads((source / "transport.json").read_text())
        code, timed = fixture["exit"], fixture.get("timed_out", False)
        shutil.copyfile(str(source / "events.jsonl"), str(events_path))
        if (source / "raw.md").exists():
            shutil.copyfile(str(source / "raw.md"), str(raw))
        err_path.write_text(fixture.get("stderr", ""))
    else:
        command = ["codex", "exec", "-s", "danger-full-access", "-c", "approval_policy=never",
                   "-C", str(workspace), "-c", "web_search=disabled", "--json", "-o", str(raw),
                   "-"]
        with mandate.open("rb") as stdin, events_path.open("wb") as out, err_path.open("wb") as err:
            try:
                code = subprocess.run(command, stdin=stdin, stdout=out, stderr=err,
                                      timeout=TIMEOUT).returncode
            except subprocess.TimeoutExpired:
                code, timed = -1, True
    status = status_of(code, raw, timed)
    note = err_path.read_text(errors="replace")[-2000:]
    events = _common.read_records(events_path)
    thread, model, injected = None, None, []
    try:
        thread, records = child_records(events, Path(home).resolve() if home else None,
                                        Path(canned_dir) if canned_dir else None)
        (scratch / "rollout.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
        for record in records:
            if record.get("type") == "turn_context":
                model = record.get("payload", {}).get("model", model)
        injected = injected_of(records)
    except (_common.Missing, ValueError) as exc:
        if status == "ok":
            status = "lane-unavailable"
        note = "%s; %s" % (exc, note)
    if status == "ok" and not model:
        status, note = "lane-unavailable", "the child's rollout names no model"
    answer = args.answer or str(run_dir / "reviewer-answer.json")
    return {
        "status": status, "call_id": call_id,
        "raw": str(raw) if raw.exists() else None,
        "model": model, "kind": "codex exec", "session_id": thread, "injected": injected,
        "note": note,
        "answer_identity": {"session_id": thread, "model": model} if status == "ok" else None,
        "record_answer": {"argv": ["record-answer", "--run-dir", str(run_dir), "--answer",
                                   answer], "answer_file": answer,
                          "why": "SKILL.md step 4: the executor writes the answer from the "
                                 "report, with answer_identity as its session_id and model"},
        "_sources": {"launch": "canned (test mode)" if canned_dir else "one codex exec",
                     "session_id": "the child's thread.started, bound to its rollout's "
                                   "session_meta.id",
                     "model": "the child rollout's turn_context.model",
                     "retry": "never here: SKILL.md step 3 decides the one re-send"},
    }


if __name__ == "__main__":
    sys.exit(_common.run("reviewer.py", main))
