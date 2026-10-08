"""handoff-v2's own observer of its facts (not a back-frame file; the E14 seam `observe.py` calls).

    observe_lane(step, case_dir, neutral, facts, via, scratch)

`observe.py` (precon-v2's, byte for byte) calls this for every `lane` step of a case of this core. It translates the
case's neutral input and recorded answer into handoff-v2's own input, questions and answers (by renaming, by
substituting the run id, and by turning a `finding_at` location into the id the gate printed for it), drives the REAL
phase driver (`scripts/handoff.py`, as a subprocess) through `select`, `photograph`, `gate`, `record-answer`, `write`
and `report`, stopping where the run stops, and fills, from what the driver did and what the workspace holds after it,
exactly the names the step lists under `pending` that it has a fact for (`via` is `cli` for each). A name it has no fact
for is left out, so `observe.py` keeps it under `_lane_pending`; nothing is guessed, and nothing is read from the answer
file as an outcome.

The step may carry `name` (select's `--name`; default the case's feature), `doc` (select's `--doc` instead), and
`edit_before_write` (`{"old", "new"}`: the session's own edit of the build doc, made after `record-answer` and before
`write`, standing for an executor that touched the doc between the gate and the write).

Run directories live under `scratch`; the case's workspace is written only by the driver's own writes. Standard
library only; the driver needs jsonschema (run under uv), and without it every name stays pending.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(PLUGIN, "skills", "handoff-v2", "scripts")
DRIVER = os.path.join(SCRIPTS, "handoff.py")
DOC = "docs/plans/2026-09-20-turnstile.md"


class _Driver(object):

    def __init__(self, scratch, facts):
        self.scratch = scratch
        self.facts = facts

    def __call__(self, args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HANDOFF_V2_TEST="1",
                   HANDOFF_V2_TEST_NOW="2026-10-04T12:00:00Z")
        proc = subprocess.run([sys.executable, DRIVER] + [str(a) for a in args], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=self.scratch, env=env)
        out = proc.stdout.decode("utf-8", "replace")
        self.facts.setdefault("_phases", []).append({"phase": str(args[0]), "exit": proc.returncode, "via": "lane"})
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


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _blocks(data):
    """The handoff blocks of a doc's bytes, as the core itself reads them, or None when it cannot read them."""
    if data is None:
        return None
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    from handoff_core import doc as docmod  # the core's own reading
    try:
        parsed = docmod.read(data.decode("utf-8"))
    except (UnicodeDecodeError, docmod.DocUnreadable):
        return None
    return [(docmod.block_text(parsed, b), b["section"] == parsed.handoffs) for b in parsed.blocks]


def _log_lines(ws):
    folder = os.path.join(ws, "docs", "records")
    out = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.endswith(".events.jsonl"):
                with open(os.path.join(folder, name), encoding="utf-8") as fh:
                    out += [json.loads(line) for line in fh if line.strip()]
    return out


def _input(neutral, run_dir, run_id):
    return {"input_version": 1, "run_id": run_id, "workspace": neutral["workspace"], "run_dir": run_dir,
            "report_only": bool(neutral.get("report_only")),
            "invocation": {"harness": neutral.get("harness") or "claude-code", "caller": "user", "mode": "direct",
                           "session_id": "seeded-session"},
            "station": dict(neutral.get("station") or {})}


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
    ws = neutral["workspace"]
    doc_rel = step.get("doc") or DOC
    doc_path = os.path.join(ws, doc_rel)
    before_doc = _read(doc_path)
    before_blocks = _blocks(before_doc)
    before_log = _log_lines(ws)
    answer = {}
    if neutral.get("answer"):
        answer = _load(os.path.join(case_dir, neutral["answer"]))
    run = _Driver(scratch, facts)

    def after():
        now_doc = _read(doc_path)
        fill("doc_changed", now_doc != before_doc)
        added = _log_lines(ws)[len(before_log):]
        fill("log_events_added", [e["kind"] for e in added])
        fill("pointer_output", os.path.exists(os.path.join(run_dir, "pointer.json")))
        now_blocks = _blocks(now_doc)
        if before_blocks is not None and now_blocks is not None:
            fill("earlier_blocks_unchanged", [t for t, _ in now_blocks[:len(before_blocks)]] ==
                 [t for t, _ in before_blocks])
            fill("new_blocks", len(now_blocks) - len(before_blocks))
            fill("new_blocks_in_handoffs", all(inside for _, inside in now_blocks[len(before_blocks):]))
        return _finish(found, facts, via)

    def ended(out):
        fill("terminal_status", out.get("status"))
        fill("stop_tag", out.get("stop_tag"))
        chat = (out.get("station_result") or {}).get("chat") or ""
        fill("chat_form", "gate-open" if "GATE OPEN" in chat.split("\n", 1)[0] else
             ("handoff" if chat.startswith("HANDOFF: ") else None))
        move = (out.get("station_result") or {}).get("next_move")
        if move:
            fill("next_shape", move["shape"])
            fill("kickoff", move["kickoff"].replace(move["doc"], "<doc>") if move.get("kickoff") else None)
            fill("recheck_slices", list(move.get("recheck") or []))
            fill("fix_list_locations", sorted(f["location"] for f in move.get("fix_list") or []))
        return after()

    code, out, err = run(["check-input", _write(os.path.join(scratch, "input.json"), _input(neutral, run_dir, run_id))])
    if code != 0:
        return _finish(found, facts, via)
    args = ["select", "--run-dir", run_dir] + (["--doc", step["doc"]] if step.get("doc") else
                                                ["--name", step.get("name", "turnstile")])
    code, out, err = run(args)
    fill("selected", code == 0)
    if code == 10 and out:
        return ended(out)
    if code != 0:
        return after()
    code, out, err = run(["photograph", "--run-dir", run_dir])
    if code == 10 and out:
        return ended(out)
    if code != 0:
        return after()
    questions = [dict(q) for q in answer.get("questions") or []]
    code, out, err = run(["gate", "--run-dir", run_dir, "--questions", _write(
        os.path.join(scratch, "questions.json"), {"answer_version": 1, "kind": "questions", "run_id": run_id,
                                                   "questions": questions})])
    if code != 0:
        return after()
    fill("gate_sources", sorted(q["source"] for q in out["questions"]))
    at = dict((f["location"], f["id"]) for f in out["open"])
    held = dict((f["location"], f["id"]) for f in out.get("findings") or [])
    entries = []
    for entry in answer.get("answers") or []:
        entry = json.loads(json.dumps(entry))
        effect = entry.get("effect") or {}
        if "finding_at" in effect:
            effect["finding"] = at.get(effect["finding_at"]) or held.get(effect["finding_at"]) or "f1:" + "0" * 20
            del effect["finding_at"]
        entries.append(entry)
    doc = {"answer_version": 1, "kind": "answers", "run_id": run_id, "answers": entries,
           "perishables": list(answer.get("perishables") or [])}
    if answer.get("asserts") is not None:
        doc["asserts"] = answer["asserts"]
    code, out, err = run(["record-answer", "--run-dir", run_dir, "--answer",
                          _write(os.path.join(scratch, "answers.json"), doc)])
    fill("record_answer_refused", code == 5)
    if code == 10 and out:
        return ended(out)
    if code != 0:
        return after()
    edit = step.get("edit_before_write")
    if edit:
        with open(doc_path, encoding="utf-8", newline="") as fh:
            text = fh.read()
        with open(doc_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace(edit["old"], edit["new"]))
        before_doc = _read(doc_path)        # the session's own edit is not the station's write
        before_blocks = _blocks(before_doc)
    code, out, err = run(["write", "--run-dir", run_dir])
    if code == 10 and out:
        return ended(out)
    if code != 0:
        return after()
    code, out, err = run(["report", "--run-dir", run_dir, "--bottom-line",
                          "The record is captured. Clear the thread and type the next line."])
    if code == 10 and out:
        return ended(out)
    return after()


def _finish(found, facts, via):
    for name, value in found.items():
        facts[name] = value
        if name not in via:
            via[name] = "cli"
