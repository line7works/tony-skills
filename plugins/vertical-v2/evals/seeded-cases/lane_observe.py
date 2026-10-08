"""vertical-v2's own observer of its facts (not a back-frame file; the E14 seam `observe.py` calls).

    observe_lane(step, case_dir, neutral, facts, via, scratch)

`observe.py` (precon-v2's, byte for byte) calls this for every `lane` step of a case of this core. It
translates the case's neutral input and recorded answer into vertical-v2's own input and answers, by
renaming and by substituting the run id, drives the REAL phase driver (`scripts/vertical.py`, as a
subprocess) as far as the step's `through` says, and fills, from what the driver did, exactly the names
the step lists under `pending` that it has a fact for (`via` is `cli` for each). A name it has no fact
for is left out, so `observe.py` keeps it under `_lane_pending`; nothing is guessed, and nothing is read
from the answer file as an outcome.

What stands in for readers, since no reader is summoned here: the two `suggest` outputs (synthetic, in
readers' shape, every row available) and one sidecar per call, carrying the status and the raw text the
case's recorded answer gives the call (the reader's half of the answer); the executor's half is the
ask's answer, the local and the outside answers, verbatim with `{RUN}` replaced by the run id.

    through: gate        check-input, gate
    through: scope       ... ask (suggests, then the answer), scope
    through: outside     ... request; with `early_outside`, a `request --outside` before record-local;
                         the local sidecars, record-local, request --outside [--row ...], the outside
                         sidecars, record-outside for each recorded attempt in turn
    through: verdict     ... verdict

Run directories live under `scratch`; the case's workspace is written only by the driver's own verdict
write. Standard library only; the driver needs jsonschema (run under uv), and without it every name stays
pending.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
DRIVER = os.path.join(PLUGIN, "skills", "vertical-v2", "scripts", "vertical.py")
OUTSIDE_ROWS = ("gpt-astra", "gpt-sol", "gemini", "deepseek", "qwen")
MARKERS = ("PRIOR-VERDICT-MARKER", "BUILDER-ADVOCACY-MARKER", "TOKEN=not-a-real-value", "HANDOFF-BLOCK-MARKER",
           "PUNCH-LIST-MARKER", "Status:")


class _Driver(object):

    def __init__(self, scratch, facts):
        self.scratch = scratch
        self.facts = facts

    def __call__(self, args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", VERTICAL_V2_TEST="1",
                   VERTICAL_V2_TEST_NOW="2026-10-01T12:00:00Z")
        proc = subprocess.run([sys.executable, DRIVER] + [str(a) for a in args], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=self.scratch, env=env)
        out = proc.stdout.decode("utf-8", "replace")
        self.facts.setdefault("_phases", []).append({"phase": " ".join(str(a) for a in args[:1] + [a for a in args[1:]
                                                                                               if str(a).startswith("--") and a != "--run-dir"]),
                                                    "exit": proc.returncode, "via": "lane"})
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        return proc.returncode, doc, proc.stderr.decode("utf-8", "replace")


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
    return path


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sub(value, run_id):
    if isinstance(value, str):
        return value.replace("{RUN}", run_id)
    if isinstance(value, list):
        return [_sub(v, run_id) for v in value]
    if isinstance(value, dict):
        return dict((k, _sub(v, run_id)) for k, v in value.items())
    return value


def _suggest(run_id, run_dir, rows, floor=None):
    return {"run_id": run_id, "run_dir": os.path.join(run_dir, "readers"), "snapshot": None, "memory": "ok",
            "floor": floor, "suggestions": [
                {"row": r, "model": "session" if r == "claude-session" else "model-of-%s" % r, "source": "roster default",
                 "picked_on": None, "effort": None, "outside": not r.startswith("claude"), "needs_word": not r.startswith("claude"),
                 "available": True, "eligibility": "eligible", "drop_note": None, "note": None} for r in rows]}


def _sidecar(run_dir, run_id, call, given):
    call_dir = os.path.join(run_dir, "readers", call["call_id"])
    os.makedirs(call_dir, exist_ok=True)
    status = given.get("status", "ok")
    raw_file = raw_hash = None
    if status == "ok":
        raw_file = os.path.join(call_dir, "raw.md")
        with open(raw_file, "w", encoding="utf-8") as fh:
            fh.write(given.get("raw", ""))
        import hashlib
        with open(raw_file, "rb") as fh:
            raw_hash = hashlib.sha256(fh.read()).hexdigest()
    _write(os.path.join(call_dir, "sidecar.json"), {
        "status": status, "reason": given.get("reason"), "call_id": call["call_id"], "run_id": run_id,
        "run_dir": os.path.join(run_dir, "readers"), "row": call["row"], "effective_model": given.get("model", "claude-seeded")
        if status == "ok" else None, "profile": call["profile"], "isolation": "unmeasured",
        "parity": "web tools forbidden by instruction", "raw_text": given.get("raw", "") if status == "ok" else "",
        "raw_file": raw_file, "raw_hash": raw_hash, "sidecar": os.path.join(call_dir, "sidecar.json")})


def _input(neutral, run_dir, run_id):
    doc = {"input_version": 1, "run_id": run_id, "workspace": neutral["workspace"], "run_dir": run_dir,
           "report_only": bool(neutral.get("report_only")),
           "invocation": {"harness": "seeded-case", "caller": "user", "mode": "direct", "session_id": "seeded-session"},
           "station": dict({"session_model": "claude-seeded"}, **(neutral.get("station") or {}))}
    return doc


def _git(ws, args):
    proc = subprocess.run(["git", "-C", ws] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    pending = set(step.get("pending") or [])
    if not pending:
        return
    found = {}

    def fill(name, value):
        if name in pending:
            found[name] = value

    run_id = neutral["case"]
    run_dir = os.path.join(scratch, "run")
    run = _Driver(scratch, facts)
    answer = {}
    if neutral.get("answer"):
        answer = _sub(_load(os.path.join(case_dir, neutral["answer"])), run_id)
    code, out, err = run(["check-input", _write(os.path.join(scratch, "input.json"), _input(neutral, run_dir, run_id))])
    if code != 0:
        return _finish(found, facts, via)
    stages = ["gate", "scope", "outside", "verdict"]
    upto = stages.index(step.get("through", "gate"))
    code, out, err = run(["gate", "--run-dir", run_dir])
    gate_path = os.path.join(run_dir, "gate.json")
    gate = _load(gate_path) if os.path.isfile(gate_path) else None
    fill("gate_passed", code == 0)
    if code == 10 and out:
        fill("terminal_status", out.get("status"))
        fill("stop_tag", out.get("stop_tag"))
    if gate:
        fill("short_slices", sorted(s["name"] for s in gate["short"]))
        fill("disagreeing_slices", sorted(d["name"] for d in gate["disagree"]))
        fill("card_sources", sorted(set(s["card_source"] for s in gate["slices"])))
        if gate.get("base"):
            fill("base_how", gate["base"]["how"])
            refs = dict((name, _git(neutral["workspace"], ["rev-parse", name])) for name in ("main", "main~1", "HEAD"))
            fill("base_ref", next((n for n in ("main~1", "main", "HEAD") if refs[n] == gate["base"]["commit"]), None))
            fill("boundary_paths", sorted(r["path"] for r in gate["boundary"]))
        if gate.get("dirt"):
            fill("dirt_inside", gate["dirt"]["inside"])
            fill("dirt_outside", gate["dirt"]["outside"])
    fill("requests_built", os.path.isdir(os.path.join(run_dir, "requests")))
    if code != 0 or upto < 1:
        return _finish(found, facts, via)
    ask = answer.get("ask") or {"rows": ["gpt-astra"], "words": "local plus GPT"}
    run(["ask", "--run-dir", run_dir])
    local = _write(os.path.join(scratch, "suggest-local.json"), _suggest(run_id, run_dir, ["claude-session"], floor="opus"))
    outside = _write(os.path.join(scratch, "suggest-outside.json"), _suggest(run_id, run_dir, OUTSIDE_ROWS))
    code, out, err = run(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
    if code != 0:
        return _finish(found, facts, via)
    code, out, err = run(["ask", "--run-dir", run_dir, "--answer", _write(os.path.join(scratch, "ask-answer.json"), {
        "answer_version": 1, "kind": "ask", "run_id": run_id, "rows": ask["rows"], "words": ask["words"]})])
    if code != 0:
        return _finish(found, facts, via)
    code, out, err = run(["scope", "--run-dir", run_dir])
    if code != 0:
        return _finish(found, facts, via)
    scope = _load(os.path.join(run_dir, "scope.json"))
    packets = dict((p["name"], p) for p in scope["packets"])
    first_outside = next((p for p in scope["packets"] if p["side"] == "outside"), None)
    if first_outside:
        files = _load(first_outside["files"])["files"]
        fill("outside_packet_files", sorted(f["path"] for f in files))
        fill("outside_withheld", sorted(w["what"] for w in _load(first_outside["withheld"])["withheld"]))
    local_packet = next((p for p in scope["packets"] if p["side"] == "local"), None)
    if local_packet:
        fill("local_packet_documents", sorted(os.path.basename(d) for d in local_packet["documents"]))
    seen = []
    for root in [p["dir"] for p in packets.values()]:
        for base, dirs, names in os.walk(root):
            for name in names:
                if name in ("files.json", "withheld.json"):
                    continue
                with open(os.path.join(base, name), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                seen += [m for m in MARKERS if m in text]
    fill("markers_found", sorted(set(seen)))
    fill("copies_have_git", any(os.path.exists(os.path.join(p["workspace"], ".git")) for p in packets.values()
                                if p.get("workspace")))
    if upto < 2:
        return _finish(found, facts, via)
    code, out, err = run(["request", "--run-dir", run_dir])
    if code != 0:
        return _finish(found, facts, via)
    local_calls = _load(os.path.join(run_dir, "requests-local.json"))["calls"]
    fill("local_authorized_rows", sorted(set(c["row"] for c in local_calls
                                             if _load(c["request_file"]).get("authorized") is True)))
    if step.get("early_outside"):
        code, out, err = run(["request", "--run-dir", run_dir, "--outside"])
        fill("outside_request_refused", code == 5)
        fill("outside_request_files", len([n for n in os.listdir(os.path.join(run_dir, "requests"))
                                           if any(n.endswith("-%s.json" % r) for r in OUTSIDE_ROWS)]))
        return _finish(found, facts, via)
    readers = answer.get("readers") or {}
    for call in local_calls:
        _sidecar(run_dir, run_id, call, readers.get("local", {"status": "ok", "raw": "Nothing found; tried the suite.\n"}))
    local_answer = dict({"answer_version": 1, "kind": "local", "run_id": run_id, "findings": [],
                         "method": "each lens ran the unit tests in its copy",
                         "tried": [{"lens": c["lens"], "what": "a double tap", "how": "executed", "output": "OK"}
                                   for c in local_calls]}, **(answer.get("local") or {}))
    code, out, err = run(["record-local", "--run-dir", run_dir, "--answer",
                          _write(os.path.join(scratch, "local-answer.json"), local_answer)])
    if code != 0:
        return _finish(found, facts, via)
    args = ["request", "--run-dir", run_dir, "--outside"]
    for row in answer.get("request_rows") or []:
        args += ["--row", row]
    code, out, err = run(args)
    fill("outside_request_refused", code == 5)
    if code != 0:
        fill("authorized_rows", [])
        return _finish(found, facts, via)
    outside_calls = _load(os.path.join(run_dir, "requests-outside.json"))["calls"]
    fill("authorized_rows", sorted(c["row"] for c in outside_calls if _load(c["request_file"]).get("authorized") is True))
    for call in outside_calls:
        _sidecar(run_dir, run_id, call, readers.get(call["row"], {"status": "ok", "raw": "Nothing found.\n",
                                                                   "model": "model-of-%s" % call["row"]}))
    refused = False
    for index, attempt in enumerate(answer.get("outside") or [{"findings": []}]):
        doc = dict({"answer_version": 1, "kind": "outside", "run_id": run_id}, **attempt)
        code, out, err = run(["record-outside", "--run-dir", run_dir, "--answer",
                              _write(os.path.join(scratch, "outside-answer-%d.json" % index), doc)])
        refused = refused or code == 5
        if code == 0:
            break
    fill("record_outside_refused", refused)
    if code != 0 or upto < 3:
        return _finish(found, facts, via)
    code, out, err = run(["verdict", "--run-dir", run_dir])
    if code == 0:
        verdict = _load(os.path.join(run_dir, "verdict.json"))
        fill("verdict", verdict["verdict"])
        fill("refuted_count", verdict["refuted"])
        fill("verdict_findings", sorted(f["location"] for f in verdict["findings"]))
        reviews = os.path.join(neutral["workspace"], "docs", "reviews")
        fill("verdict_docs", sorted(n for n in os.listdir(reviews) if "-vertical-" in n) if os.path.isdir(reviews) else [])
    return _finish(found, facts, via)


def _finish(found, facts, via):
    for name, value in found.items():
        facts[name] = value
        if name not in via:
            via[name] = "cli"
