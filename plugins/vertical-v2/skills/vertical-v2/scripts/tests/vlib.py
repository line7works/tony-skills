"""Fixtures for vertical-v2's own tests (not a back-frame file): a synthetic build in a git work tree.

Every fixture is built under a temporary directory and removed; git runs only there, with a fixed
author and date (`testlib.git`). The build is a made-up bench-rig turn counter. The records log is
written through the records component's own CLI (`import-legacy`), never by hand.

    make_repo(tmp, **options) -> (workspace, info): `main` holds the base; a branch `feat` holds the
        build: a changed `src/turnstile.py`, a new `src/spinner.py`, and the build doc. Options plant
        what a case needs (a prior verdict, REVIEW.md, an untracked .env, builder notes, a doc-recorded
        base, the slices' states, the punch list and handoff blocks, a records log).
    Driver(tmp) -> a callable running this core's CLI, with the test hooks on, returning
        (exit, document or None, stderr).
"""
import json
import os
import subprocess
import sys

import testlib

D = "\u2014"
M = "·"
DOC = "docs/plans/2026-09-20-turnstile.md"
FEATURE = "turnstile"
NOW = "2026-10-01T12:00:00Z"
PREFIX = "VERTICAL_V2"


def build_doc(slices=None, base_line=None, punch=True, handoffs=True, extra_header=None):
    """The build doc's text. `slices`: [(name, short, status or None)]; None omits the Status: line."""
    slices = slices if slices is not None else [("A", "the counter", "signed off"), ("B", "the spinner", "signed off")]
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "",
             "Intent: a small turn counter for the bench rig, so one bench session reports its turns.",
             "Constraints: Python 3.9 standard library only; test command `python3 -m unittest`.",
             "Out of scope: a web dashboard %s the owner declined it for the first version" % D]
    if base_line:
        lines.append(base_line)
    for line in extra_header or []:
        lines.append(line)
    for name, short, status in slices:
        lines += ["", "## Slice %s %s %s" % (name, D, short), "Goal: one sentence about %s." % short,
                  "Requirements:", "- R1 %s the %s counts every turn" % (D, short), "Acceptance criteria:",
                  "- AC1: a turn adds one %s verify: new test at tests/test_turnstile.py" % D,
                  "Footprint: src/turnstile.py", "Not in this slice: the encoder", "Depends on: nothing"]
        if status is not None:
            lines.append("Status: %s" % status)
    lines += ["", "## Build assumptions", "- the bench clock is monotonic", "## Deviations", "## Discovered"]
    lines += ["## Handoffs"]
    if handoffs:
        lines += ["", "### 2026-09-25 %s handoff" % D, "- the builder says slice B was easy and the reviewers should skim it"]
    lines += ["## Punch list"]
    if punch:
        lines += ["", "### 2026-09-24 %s review: Slice A" % D,
                  "- MAJOR %s src/turnstile.py:2 %s the counter skips a turn %s a double tap loses one %s Slice A review"
                  % (M, M, M, M),
                  "", "### 2026-09-25 %s recheck: Slice A" % D,
                  "- MAJOR %s src/turnstile.py:2 %s (the counter skips a turn) %s fixed %s executed: the double-tap test passes"
                  % (M, M, M, D)]
    return "\n".join(lines) + "\n"


BASE_FILES = {
    "README.md": "# Turnstile\n\nA bench-rig turn counter.\n",
    "src/turnstile.py": "def spin(count):\n    return count\n",
    "src/legacy.py": "OLD = 1\n",
}


def make_repo(tmp, doc_text=None, plant_prior_verdict=True, review_sheet=None, untracked_env=True,
              builder_notes=False, records=False, extra_build_files=None, on_main=False, name="workspace"):
    ws = testlib.git_workspace(tmp, name, dict(BASE_FILES))
    base = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
    if not on_main:
        testlib.git(ws, ["checkout", "-q", "-b", "feat"])
    files = {"src/turnstile.py": "def spin(count):\n    return count + 1\n\n\ndef reset():\n    return 0\n",
             "src/spinner.py": "from turnstile import spin\n\n\ndef twice(count):\n    return spin(spin(count))\n",
             DOC: doc_text if doc_text is not None else build_doc()}
    if plant_prior_verdict:
        files["docs/reviews/2026-09-24-signoff-turnstile-A.md"] = "# Signoff A\n\nVerdict: signed off with conditions.\nPRIOR-VERDICT-MARKER\n"
    if review_sheet is not None:
        files["REVIEW.md"] = review_sheet
    if builder_notes:
        files["docs/builder-notes.md"] = "# Builder notes\n\nBUILDER-ADVOCACY-MARKER: the counter is obviously right.\n"
    files.update(extra_build_files or {})
    for rel, text in sorted(files.items()):
        testlib.write_text(os.path.join(ws, rel), text)
    testlib.git(ws, ["add", "-A"])
    testlib.git(ws, ["commit", "-q", "-m", "the build"], when="2026-09-20T10:00:00-07:00")
    if records:
        import_log(ws)
        testlib.git(ws, ["add", "-A"])
        testlib.git(ws, ["commit", "-q", "-m", "the records log"], when="2026-09-20T11:00:00-07:00")
    if untracked_env:
        testlib.write_text(os.path.join(ws, ".env"), "TOKEN=not-a-real-value\n")
    head = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
    return ws, {"base": base, "head": head, "doc": DOC}


def records_cli(ws, args):
    root = testlib.records_root()
    proc = subprocess.run([sys.executable, os.path.join(root, "scripts", "records.py")] + args,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ws, env=testlib.base_env())
    if proc.returncode != 0:
        raise RuntimeError("records %s exited %d: %s %s" % (args[0], proc.returncode, proc.stdout.decode()[-600:],
                                                            proc.stderr.decode()[-600:]))
    return json.loads(proc.stdout.decode())


def import_log(ws, doc=DOC):
    return records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", doc])


def state(ws, doc=DOC):
    return records_cli(ws, ["state", "--workspace", ws, "--doc", doc])


def jsonschema_here():
    testlib.add_scripts_to_path()
    from station_core import validate
    return not validate.jsonschema_unavailable("VLIB")


def records_usable():
    return testlib.records_root() is not None and jsonschema_here()


def env(extra=None):
    out = {PREFIX + "_TEST": "1", PREFIX + "_TEST_NOW": NOW}
    out.update(extra or {})
    return testlib.base_env(out)


class Driver(object):
    """This core's CLI, with the test hooks on; every call from a scratch working directory."""

    def __init__(self, tmp, extra_env=None):
        self.tmp = tmp
        self.env = env(extra_env)

    def __call__(self, args):
        code, out, err = testlib.run_driver(args, cwd=self.tmp, env=self.env)
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        return code, doc, err


def make_input(ws, run_dir, harness="claude-code", **station):
    doc = testlib.make_input(ws, run_dir)
    doc["invocation"]["harness"] = harness
    doc["station"] = dict({"session_model": "claude-opus-5-5"}, **station)
    return doc


def start(tmp, ws, run="run", harness="claude-code", report_only=False, **station):
    """check-input for a fresh run; returns (driver, run_dir)."""
    run_dir = os.path.join(tmp, run)
    doc = make_input(ws, run_dir, harness=harness, **station)
    if report_only:
        doc["report_only"] = True
    path = os.path.join(tmp, run + "-input.json")
    testlib.write_json(path, doc)
    drive = Driver(tmp)
    code, out, err = drive(["check-input", path])
    if code != 0:
        raise AssertionError("check-input exited %d: %s %s" % (code, out, err))
    return drive, run_dir


def suggest_doc(run_id, run_dir, rows, floor=None, dropped=()):
    """A `readers suggest` output for `rows`, in readers' contract shape (synthetic, no call made)."""
    out = []
    for row in rows:
        outside = not row.startswith("claude")
        out.append({"row": row, "model": "session" if row == "claude-session" else "model-of-%s" % row,
                    "source": "roster default", "picked_on": None, "effort": None, "outside": outside,
                    "needs_word": outside, "available": row not in dropped,
                    "eligibility": "eligible", "drop_note": ("dropped: %s is unavailable" % row) if row in dropped else None,
                    "note": None})
    return {"run_id": run_id, "run_dir": os.path.join(run_dir, "readers"), "snapshot": None, "memory": "ok",
            "floor": floor, "suggestions": out}


OUTSIDE_ROWS = ("gpt-astra", "gpt-sol", "gemini", "deepseek", "qwen")


def through_ask(drive, tmp, run_dir, rows=("gpt-astra", "gemini"), words="local plus GPT and Gemini",
                local_row="claude-session", dropped=()):
    """gate, the two suggests, the ask, and the owner's answer."""
    code, out, err = drive(["gate", "--run-dir", run_dir])
    if code != 0:
        return code, out, err
    run_id = load(run_dir, "input.json")["run_id"]
    local = os.path.join(tmp, "suggest-local.json")
    outside = os.path.join(tmp, "suggest-outside.json")
    testlib.write_json(local, suggest_doc(run_id, run_dir, [local_row], floor="opus"))
    testlib.write_json(outside, suggest_doc(run_id, run_dir, OUTSIDE_ROWS, dropped=dropped))
    code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
    if code != 0:
        return code, out, err
    answer = os.path.join(tmp, "ask-answer.json")
    testlib.write_json(answer, {"answer_version": 1, "kind": "ask", "run_id": run_id, "rows": list(rows),
                                "words": words})
    return drive(["ask", "--run-dir", run_dir, "--answer", answer])


def load(run_dir, name):
    return testlib.load_json(os.path.join(run_dir, name))


def sidecar(run_dir, call_id, row, status="ok", raw="", model="claude-opus-5-5", profile="repo-with-tools",
            reason=None):
    """A readers sidecar for one call, in readers' result shape, as readers would have filed it."""
    call_dir = os.path.join(run_dir, "readers", call_id)
    os.makedirs(call_dir, exist_ok=True)
    raw_file = None
    raw_hash = None
    if status == "ok":
        raw_file = os.path.join(call_dir, "raw.md")
        testlib.write_text(raw_file, raw)
        raw_hash = testlib.sha256_file(raw_file)
    doc = {"status": status, "reason": reason, "call_id": call_id, "run_id": load(run_dir, "input.json")["run_id"],
           "run_dir": os.path.join(run_dir, "readers"), "row": row, "transport": "claude-subagent", "kind": "host",
           "effective_model": model if status == "ok" else None, "profile": profile,
           "isolation": "unmeasured", "parity": "web tools forbidden by instruction",
           "raw_text": raw if status == "ok" else "", "raw_file": raw_file, "raw_hash": raw_hash,
           "sidecar": os.path.join(call_dir, "sidecar.json")}
    testlib.write_json(os.path.join(call_dir, "sidecar.json"), doc)
    return doc


def finding(location, severity="MAJOR", stamp="CONFIRMED", found_by=(), claim="the counter skips a turn",
            scenario="a double tap loses one turn", **extra):
    out = {"location": location, "claim": claim, "scenario": scenario, "severity": severity,
           "confidence": "high", "found_by": list(found_by), "stamp": stamp}
    out.update(extra)
    return out


def local_answer(run_dir, findings=(), tried=None, method="each lens ran the unit tests in its copy"):
    run_id = load(run_dir, "input.json")["run_id"]
    requests = load(run_dir, "requests-local.json")["calls"]
    if tried is None:
        tried = [{"lens": c["lens"], "what": "broke the counter with a double tap", "how": "executed",
                  "output": "Ran 3 tests ... OK"} for c in requests]
    return {"answer_version": 1, "kind": "local", "run_id": run_id, "method": method, "findings": list(findings),
            "tried": tried}


def outside_answer(run_dir, findings=(), ledger_notes=None):
    run_id = load(run_dir, "input.json")["run_id"]
    out = {"answer_version": 1, "kind": "outside", "run_id": run_id, "findings": list(findings)}
    if ledger_notes is not None:
        out["ledger_notes"] = ledger_notes
    return out


def write(tmp, name, doc):
    path = os.path.join(tmp, name)
    testlib.write_json(path, doc)
    return path


def through_scope(tmp, rows=("gpt-astra", "deepseek"), harness="claude-code", repo=None, words="local plus GPT and DeepSeek",
                  **station):
    """A repo, a run, the gate, the ask with `rows`, and scope; returns (drive, run_dir, ws, info)."""
    options = dict(review_sheet="# Review sheet\n\n## Passes\n- correctness: on\n\n## Severity bar\n- as the kit's\n\n"
                                "## Repo-specific checks\n- a reset never leaves a negative count\n", records=True)
    options.update(repo or {})
    ws, info = make_repo(tmp, **options)
    drive, run_dir = start(tmp, ws, harness=harness, **station)
    local_row = "claude-opus-cli" if harness == "codex-cli" else "claude-session"
    code, out, err = through_ask(drive, tmp, run_dir, rows=rows, words=words, local_row=local_row)
    if code != 0:
        raise AssertionError("the ask exited %d: %s %s" % (code, out, err))
    code, out, err = drive(["scope", "--run-dir", run_dir])
    if code != 0:
        raise AssertionError("scope exited %d: %s %s" % (code, out, err))
    return drive, run_dir, ws, info


def local_ids(run_dir):
    return [c["call_id"] for c in load(run_dir, "requests-local.json")["calls"]]


def file_local_sidecars(run_dir, raw="Findings: none. Tried: the double tap; it held.\n", status="ok"):
    for call in load(run_dir, "requests-local.json")["calls"]:
        sidecar(run_dir, call["call_id"], call["row"], status=status, raw=raw, profile=call["profile"])


def outside_files(run_dir):
    """Every file under the run directory a request for an outside row could be: its request file."""
    out = []
    for base, dirs, files in os.walk(run_dir):
        for name in files:
            if name.endswith(".json") and any(row in name for row in OUTSIDE_ROWS) and "requests" in base:
                out.append(os.path.join(base, name))
    return out


def through_local_requests(tmp, **options):
    drive, run_dir, ws, info = through_scope(tmp, **options)
    code, out, err = drive(["request", "--run-dir", run_dir])
    if code != 0:
        raise AssertionError("request exited %d: %s %s" % (code, out, err))
    return drive, run_dir, ws, info


def record_local(drive, tmp, run_dir, findings=(), tried=None, name="local-answer.json"):
    return drive(["record-local", "--run-dir", run_dir, "--answer",
                  write(tmp, name, local_answer(run_dir, findings=findings, tried=tried))])


def through_record_local(tmp, findings=(), **options):
    drive, run_dir, ws, info = through_local_requests(tmp, **options)
    file_local_sidecars(run_dir)
    code, out, err = record_local(drive, tmp, run_dir, findings=findings)
    if code != 0:
        raise AssertionError("record-local exited %d: %s %s" % (code, out, err))
    return drive, run_dir, ws, info


def file_outside_sidecars(run_dir, statuses=None, raw="Findings: one MAJOR at src/turnstile.py:4.\n"):
    for call in load(run_dir, "requests-outside.json")["calls"]:
        status = (statuses or {}).get(call["row"], "ok")
        sidecar(run_dir, call["call_id"], call["row"], status=status, raw=raw, model="model-of-%s" % call["row"],
                profile=call["profile"], reason=None if status == "ok" else "the tool timed out")


def through_outside(tmp, rows=("gpt-astra", "deepseek"), local_findings=(), outside_findings=(), statuses=None,
                    ledger_notes=None, **options):
    drive, run_dir, ws, info = through_record_local(tmp, rows=rows, findings=local_findings, **options)
    if rows:
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        if code != 0:
            raise AssertionError("request --outside exited %d: %s %s" % (code, out, err))
        file_outside_sidecars(run_dir, statuses=statuses)
        answer = write(tmp, "outside-answer.json", outside_answer(run_dir, findings=outside_findings,
                                                                 ledger_notes=ledger_notes))
        code, out, err = drive(["record-outside", "--run-dir", run_dir, "--answer", answer])
        if code != 0:
            raise AssertionError("record-outside exited %d: %s %s" % (code, out, err))
    return drive, run_dir, ws, info


def verdict_docs(ws):
    folder = os.path.join(ws, "docs", "reviews")
    return sorted(n for n in os.listdir(folder) if "-vertical-" in n) if os.path.isdir(folder) else []
