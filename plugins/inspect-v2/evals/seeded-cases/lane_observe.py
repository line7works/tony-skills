#!/usr/bin/env python3
"""inspect-v2's lane facts for the seeded cases (E14 slice 2, lane I; brief CR-7).

Not shared: `observe.py` (shared) calls `observe_lane(step, case_dir, neutral, facts, via, scratch)`
for every `lane` step of this core's families and keeps, as the lane's facts, the names this
function fills. It fills only the names the step lists under `pending`, and only from what a REAL
drive of this core did, never from what a case expects; `via` says how each fact was observed.

    I2, I3   the real CLI end to end, in a scratch run directory against the case's own git
             workspace: check-input, select (build, then scope), harvest, packet, request,
             record-answer with the case's recorded reader answer translated into this core's answer
             (a renaming: the reader's `row`, `call_id`, `effective_model` and `findings` carried
             over unchanged, inside the executor's envelope with no question, no line and no
             adjudication of its own), then write and report when the run has not stopped. The facts
             are read from the run's `result.json` and the build doc as written. `write` appends to
             the case workspace's records log and writes the build doc, so these cases observe
             `writes_none: false`: a fact of the run, measured by observe.py.
    I1       the real CLI up to harvest (so the record the packet must hold is the core's own
             answer), then `inspect_core.packet.check_dir`, the three-file rule `request` applies
             before it builds anything, on the case's `packet/` directory as the station would hand
             it to `request`.

The fact names are the neutral vocabulary of `README.md`: `refused_at_request`, `packet_files`,
`question_locations`, `blocker_count`, `no_record_noted`, `raised_locations`, `refuted_count`,
`stamp_written`, `stamp_model`, `terminal_status`. A location is written as the core writes it
(the build doc's workspace path and line). Standard library only; no network, no model call.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(PLUGIN, "skills", "inspect-v2")
SCRIPTS = os.path.join(SKILL, "scripts")
DRIVER = os.path.join(SCRIPTS, "inspect_v2.py")
RUN_ID = "run"
CLI = "cli: check-input, select, harvest, packet, request, record-answer, write, report"


def _cli(args, scratch):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key in ("INSPECT_V2_TEST", "INSPECT_V2_TEST_NO_RECORDS", "INSPECT_V2_TEST_NOW"):
        env.pop(key, None)
    proc = subprocess.run([sys.executable, DRIVER] + [str(a) for a in args], cwd=scratch, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    try:
        doc = json.loads(out) if out.strip() else None
    except ValueError:
        doc = None
    return proc.returncode, doc, proc.stderr.decode("utf-8", "replace")


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Drive(object):
    """One run of the real CLI in `scratch`; `trail` keeps each step's exit for the record."""

    def __init__(self, neutral, scratch, row=None):
        self.scratch = scratch
        self.run_dir = os.path.join(scratch, "run")
        self.trail = []
        station = {"row": row} if row else {}
        self.input = {"input_version": 1, "run_id": RUN_ID, "workspace": neutral["workspace"],
                      "run_dir": self.run_dir, "report_only": bool(neutral.get("report_only")),
                      "invocation": {"harness": "seeded-case", "caller": "user", "mode": "direct",
                                     "session_id": "seeded-session"},
                      "station": station}
        if neutral.get("staging"):
            self.input["staging"] = neutral["staging"]
        if neutral.get("owner_word"):
            self.input["owner_word"] = neutral["owner_word"]

    def step(self, name, *args):
        if name == "check-input":
            path = os.path.join(self.scratch, "input.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.input, fh)
            code, doc, err = _cli(["check-input", path], self.scratch)
        else:
            code, doc, err = _cli([name, "--run-dir", self.run_dir] + list(args), self.scratch)
        self.trail.append({"phase": name, "exit": code})
        return code, doc, err

    def through(self, phases, facts):
        """Run the phases in order; stop at the first that does not exit 0. (last code, last doc)."""
        code, doc = 0, None
        for phase in phases:
            name, args = phase[0], phase[1:]
            code, doc, err = self.step(name, *args)
            if code != 0:
                if code not in (10, 5):
                    facts["_errors"].append({"step": "lane", "phase": name, "exit": code, "stderr": err[-600:]})
                return code, doc
        return code, doc

    def artifact(self, name):
        path = os.path.join(self.run_dir, name)
        return _read_json(path) if os.path.isfile(path) else None


def translate(reader, requests, session_id):
    """The neutral reader answer as this core's answer: a renaming, nothing invented."""
    lens_of = dict((c["call_id"], c["lens"]) for c in (requests or {}).get("calls", []))
    result = {"call_id": reader.get("call_id"), "row": reader.get("row"),
              "effective_model": reader.get("effective_model"),
              "findings": [dict((k, f.get(k)) for k in ("severity", "location", "claim", "scenario", "confidence"))
                           for f in reader.get("findings") or []]}
    lanes = [lens_of[result["call_id"]]] if result["call_id"] in lens_of else []
    return {"answer_version": 1, "run_id": RUN_ID, "session_id": session_id, "questions": [], "lines": [],
            "row": reader.get("row"), "lanes": lanes, "results": [result]}


def _fill(step, facts, via, found, how):
    for name in step.get("pending", []):
        if name in found:
            facts[name] = found[name]
            via[name] = how


def _stamp_in(doc_path, stamp):
    if not stamp or not os.path.isfile(doc_path):
        return False
    with open(doc_path, encoding="utf-8") as fh:
        return any(line.rstrip("\r\n") == stamp for line in fh)


def observe_i1(step, case_dir, neutral, facts, via, scratch):
    drive = Drive(neutral, scratch)
    code, _ = drive.through([("check-input",), ("select", "--hunt", "build"), ("select", "--hunt", "scope"),
                             ("harvest",)], facts)
    facts["_phases"].extend(drive.trail)
    harvest = drive.artifact("harvest.json")
    if code != 0 or harvest is None:
        return
    sys.path.insert(0, SCRIPTS)
    try:
        from inspect_core import packet as packetmod
    finally:
        sys.path.pop(0)
    present, refusals = packetmod.check_dir(os.path.join(case_dir, "packet"), harvest["no_record"])
    found = {"refused_at_request": bool(refusals), "packet_files": present}
    _fill(step, facts, via, found, "library: inspect_core.packet.check_dir, the rule `request` applies, on the "
                                   "case's packet/ after check-input, select and harvest through the CLI")


def observe_run(step, case_dir, neutral, facts, via, scratch):
    reader = _read_json(os.path.join(case_dir, neutral["answer"]))
    drive = Drive(neutral, scratch, row=reader.get("row"))
    code, doc = drive.through([("check-input",), ("select", "--hunt", "build"), ("select", "--hunt", "scope"),
                               ("harvest",), ("packet",), ("request",)], facts)
    if code == 0:
        answer = translate(reader, drive.artifact("requests.json"), drive.input["invocation"]["session_id"])
        path = os.path.join(scratch, "answer.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(answer, fh)
        code, doc = drive.through([("record-answer", "--answer", path), ("write",), ("report",)], facts)
    facts["_phases"].extend(drive.trail)
    result = drive.artifact("result.json")
    if result is None:
        return
    sr = result.get("station_result") or {}
    counts = sr.get("counts") or {}
    found = {"terminal_status": result["status"]}
    stamp = sr.get("stamp")
    doc_path = sr.get("build_doc") or ""
    found["stamp_written"] = bool(sr.get("stamp_written")) and _stamp_in(doc_path, stamp)
    if found["stamp_written"]:
        found["stamp_model"] = stamp.split(" by ", 1)[1].split(" ", 1)[0]
    if "findings" in sr:
        found["raised_locations"] = sorted(f["location"] for f in sr["findings"] if f.get("finding_id"))
        found["blocker_count"] = counts.get("blocker", 0)
        found["refuted_count"] = counts.get("refuted", 0)
        found["question_locations"] = sorted(q["location"] for q in sr.get("questions") or [])
    if "weaker" in sr:
        found["no_record_noted"] = bool(sr["weaker"]) and "weaker" in (sr.get("chat") or "")
    _fill(step, facts, via, found, "%s (result.json, and the build doc as written for the stamp)" % CLI)


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    case = neutral.get("case", "")
    if case.startswith("I1-"):
        observe_i1(step, case_dir, neutral, facts, via, scratch)
    elif case.startswith(("I2-", "I3-")):
        observe_run(step, case_dir, neutral, facts, via, scratch)
