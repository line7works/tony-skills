#!/usr/bin/env python3
"""Validate the example documents against the schemas and run the negative suite.

Run from the examples folder: uvx --with jsonschema python3 validate-examples.py
Exit status 0 when every positive example validates and every negative case is rejected.
"""
import copy, glob, json, os, sys
from jsonschema import Draft202012Validator as V

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.dirname(HERE)
inp = V(json.load(open(os.path.join(REF, "input.schema.json"))))
res = V(json.load(open(os.path.join(REF, "result.schema.json"))))
for s in ("input.schema.json", "result.schema.json"):
    V.check_schema(json.load(open(os.path.join(REF, s))))

def load(name):
    return json.load(open(os.path.join(HERE, name)))

failures = 0
for f in sorted(glob.glob(os.path.join(HERE, "*.json"))):
    v = inp if os.path.basename(f).startswith("input-") else res
    errs = list(v.iter_errors(json.load(open(f))))
    print(("PASS " if not errs else "FAIL ") + os.path.basename(f) + ("" if not errs else ": " + "; ".join(e.message[:110] for e in errs[:3])))
    failures += bool(errs)

# Negative suite: each entry mutates a valid document into one the contract forbids.
completed = load("result-completed.json")
blocked = load("result-completed-blocked.json")
caller = load("input-caller.json")
direct = load("input-direct.json")

def neg(name, doc, validator, mutate):
    d = copy.deepcopy(doc); mutate(d)
    ok = not validator.is_valid(d)
    print(("REJECTED " if ok else "ACCEPTED (BUG) ") + name)
    return ok

def set_path(d, path, value):
    cur = d
    for k in path[:-1]: cur = cur[k]
    cur[path[-1]] = value

def del_path(d, path):
    cur = d
    for k in path[:-1]: cur = cur[k]
    del cur[path[-1]]

cases = [
    ("fixed with reason verification_blocked", completed, res, lambda d: set_path(d, ["items", 0, "reason"], "verification_blocked")),
    ("not_fixed without reason", completed, res, lambda d: del_path(d, ["items", 1, "reason"])),
    ("verification_blocked without the block named", blocked, res, lambda d: del_path(d, ["items", 0, "verification", "blocked"])),
    ("missing_evidence without what is missing", blocked, res, lambda d: del_path(d, ["items", 2, "verification", "missing"])),
    ("static without reason", blocked, res, lambda d: del_path(d, ["items", 1, "verification", "static_reason"])),
    ("executed with a static reason", completed, res, lambda d: set_path(d, ["items", 0, "verification", "static_reason"], "mutates_real_state")),
    ("empty evidence detail", completed, res, lambda d: set_path(d, ["items", 0, "verification", "evidence", 0, "detail"], "")),
    ("empty block explanation", blocked, res, lambda d: set_path(d, ["items", 0, "verification", "blocked"], "")),
    ("upgrade without evidence", completed, res, lambda d: (set_path(d, ["items", 1, "adjudication", "driver_action"], "upgraded"), set_path(d, ["items", 1, "disposition"], "fixed"), del_path(d, ["items", 1, "reason"]))),
    ("upgrade by the session that wrote the fix", completed, res, lambda d: (set_path(d, ["items", 1, "adjudication", "driver_action"], "upgraded"), set_path(d, ["items", 1, "adjudication", "upgrade_evidence"], "x"), set_path(d, ["items", 1, "adjudication", "session_wrote_fix"], True), set_path(d, ["items", 1, "disposition"], "fixed"), del_path(d, ["items", 1, "reason"]))),
    ("built becomes signed off", completed, res, lambda d: (set_path(d, ["cards", 0, "before"], "built"), set_path(d, ["cards", 0, "after"], "signed off"))),
    ("missing_input carrying cards", load("result-missing-input-headless.json"), res, lambda d: d.__setitem__("cards", [{"slice": "A", "before": "rejected", "after": "signed off"}])),
    ("stale_source carrying records_written", load("result-stale-source.json"), res, lambda d: d.__setitem__("records_written", [{"kind": "status_line", "path": "docs/x.md", "appended": False}])),
    ("stale_source with matched true", load("result-stale-source.json"), res, lambda d: set_path(d, ["source_identity", "matched"], True)),
    ("stale_source without expected identity", load("result-stale-source.json"), res, lambda d: del_path(d, ["source_identity", "expected"])),
    ("verifier_unavailable carrying a result", load("result-verifier-unavailable.json"), res, lambda d: d.__setitem__("result", "all_clear")),
    ("completed without verifier metadata", completed, res, lambda d: del_path(d, ["run", "verifier"])),
    ("completed without session_wrote_fix", completed, res, lambda d: del_path(d, ["run", "session_wrote_fix"])),
    ("completed with zero items", completed, res, lambda d: (d.__setitem__("items", []), set_path(d, ["checklist", "count"], 0))),
    ("completed without a receipt", completed, res, lambda d: del_path(d, ["receipt_path"])),
    ("completed without boundary_violations", completed, res, lambda d: del_path(d, ["boundary_violations"])),
    ("completed without rejected_grants", completed, res, lambda d: del_path(d, ["rejected_grants"])),
    ("completed without transaction identities", completed, res, lambda d: del_path(d, ["source_identity", "at_transaction"])),
    ("new defect not charged to a slice", blocked, res, lambda d: del_path(d, ["new_defects", 0, "charged_to_slice"])),
    ("punch-list block written non-append", completed, res, lambda d: set_path(d, ["records_written", 7, "appended"], False)),
    ("status line written as an append", completed, res, lambda d: set_path(d, ["records_written", 9, "appended"], True)),
    ("record write of a forbidden kind", completed, res, lambda d: d["records_written"].append({"kind": "source_edit", "path": "src/x.ts", "appended": False})),
    ("headless envelope carrying a question", load("result-missing-input-headless.json"), res, lambda d: set_path(d, ["missing_input", "question"], "which one?")),
    ("no-run envelope carrying a question", load("result-invalid-input-envelope.json"), res, lambda d: set_path(d, ["missing_input", "question"], "which one?")),
    ("nothing_open with count 1", load("result-nothing-open.json"), res, lambda d: set_path(d, ["checklist", "count"], 1)),
    ("nothing_open carrying items", load("result-nothing-open.json"), res, lambda d: d.__setitem__("items", [])),
    ("recording_failed carrying cards", load("result-recording-failed.json"), res, lambda d: d.__setitem__("cards", [])),
    ("actual identity with a short commit", completed, res, lambda d: set_path(d, ["source_identity", "actual", "commit"], "9c2f1e4d")),
    ("actual identity missing untracked hash", completed, res, lambda d: del_path(d, ["source_identity", "actual", "untracked_sha256"])),
    ("verifier not fresh", completed, res, lambda d: set_path(d, ["run", "verifier", "fresh"], False)),
    ("verifier restrictions not declared", completed, res, lambda d: set_path(d, ["run", "verifier", "restrictions_declared"], False)),
    ("harness without sandbox", completed, res, lambda d: del_path(d, ["run", "harness", "sandbox"])),
    ("model without floor class", completed, res, lambda d: del_path(d, ["run", "model", "floor_class"])),
    ("claim with a middle dot in a result", completed, res, lambda d: set_path(d, ["items", 0, "claim"], "a · b")),
    ("input: station caller in interactive mode", caller, inp, lambda d: set_path(d, ["invocation", "mode"], "interactive")),
    ("input: relative workspace", direct, inp, lambda d: d.__setitem__("workspace", "Developer/widget")),
    ("input: relative run_dir", direct, inp, lambda d: set_path(d, ["invocation", "run_dir"], "tmp/x")),
    ("input: build_doc escaping the workspace", direct, inp, lambda d: set_path(d, ["target", "build_doc"], "../other/plan.md")),
    ("input: absolute build_doc", direct, inp, lambda d: set_path(d, ["target", "build_doc"], "/etc/plan.md")),
    ("input: empty slice", direct, inp, lambda d: set_path(d, ["target", "slice"], "")),
    ("input: both target forms", direct, inp, lambda d: set_path(d, ["target", "items"], [])),
    ("input: item without provenance", caller, inp, lambda d: del_path(d, ["target", "items", 0, "record"])),
    ("input: item without slice", caller, inp, lambda d: del_path(d, ["target", "items", 0, "slice"])),
    ("input: multiline claim", caller, inp, lambda d: set_path(d, ["target", "items", 0, "claim"], "line one\nline two")),
    ("input: claim containing the separator", caller, inp, lambda d: set_path(d, ["target", "items", 0, "claim"], "a · b")),
    ("input: grant by model", caller, inp, lambda d: set_path(d, ["authorization", "waivers", 0, "by"], "model")),
    ("input: grant without channel", caller, inp, lambda d: del_path(d, ["authorization", "waivers", 0, "channel"])),
    ("input: grant without turn_ref", caller, inp, lambda d: del_path(d, ["authorization", "waivers", 0, "turn_ref"])),
    ("input: grant on a file channel", caller, inp, lambda d: set_path(d, ["authorization", "waivers", 0, "channel"], "file")),
    ("input: waiver without severity", caller, inp, lambda d: del_path(d, ["authorization", "waivers", 0, "severity"])),
    ("input: empty identity pin", caller, inp, lambda d: d.__setitem__("source_identity", {})),
    ("input: unknown top-level field", direct, inp, lambda d: d.__setitem__("fixer_notes", "trust me")),
]
rejected = sum(neg(*c) for c in cases)
print(f"positive: {len(glob.glob(os.path.join(HERE, '*.json')))} files, {failures} failing; negative: {rejected}/{len(cases)} rejected")
sys.exit(1 if failures or rejected != len(cases) else 0)
