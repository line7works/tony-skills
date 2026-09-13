#!/usr/bin/env python3
"""Validate the example documents against the schemas and run the negative suite.

Run from the examples folder: uvx --with jsonschema python3 validate-examples.py
Exit status 0 when every positive example validates, every negative case is rejected, every
positive mutation is accepted, and the checkpoint example passes its item-state and integrity
checks, log-before-rename included (pilot-contract.md section 11).
"""
import copy, glob, hashlib, json, os, sys
from jsonschema import Draft202012Validator as V

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.dirname(HERE)
result_schema = json.load(open(os.path.join(REF, "result.schema.json")))
inp = V(json.load(open(os.path.join(REF, "input.schema.json"))))
res = V(result_schema)
item = V({"$schema": result_schema["$schema"], "$defs": result_schema["$defs"], "$ref": "#/$defs/item_result"})
for s in ("input.schema.json", "result.schema.json"):
    V.check_schema(json.load(open(os.path.join(REF, s))))

def load(name):
    return json.load(open(os.path.join(HERE, name)))

failures = 0
for f in sorted(glob.glob(os.path.join(HERE, "*.json"))):
    base = os.path.basename(f)
    if base.startswith("checkpoint-"):
        continue  # checked below against section 11, not against a schema (checkpoint.schema.json arrives at E8)
    v = inp if base.startswith("input-") else res
    errs = list(v.iter_errors(json.load(open(f))))
    print(("PASS " if not errs else "FAIL ") + base + ("" if not errs else ": " + "; ".join(e.message[:110] for e in errs[:3])))
    failures += bool(errs)

# Negative suite: each entry mutates a valid document into one the contract forbids.
completed = load("result-completed.json")
blocked = load("result-completed-blocked.json")
stopped = load("result-stopped.json")
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

def write_index(d, kind):
    idx = [i for i, w in enumerate(d["records_written"]) if w["kind"] == kind]
    assert len(idx) == 1, (kind, idx)
    return idx[0]

BLOCK = write_index(completed, "punch_list_block")
STATUS = write_index(completed, "status_line")
MARK = {"date": "2026-09-20", "quoted_words": "waive the undefined-title one, ship it", "turn_ref": "codex:thread 01a0a1b2:turn 9"}
DEFECT = {"severity": "MAJOR", "location": {"file": "src/export.ts", "line": 150}, "claim": "broke: quoted commas now double their quotes", "failure_scenario": "export a title with a comma; the cell carries four quote marks", "source": "fix_introduced", "charged_to_slice": "A"}

def waive_item1(d):
    set_path(d, ["items", 1, "waived"], MARK)

def all_not_fixed_waived(d):
    set_path(d, ["items", 0, "disposition"], "not_fixed"); set_path(d, ["items", 0, "reason"], "reproduces")
    set_path(d, ["items", 0, "adjudication", "verifier_said"], "not_fixed")
    set_path(d, ["items", 0, "waived"], dict(MARK, quoted_words="waive the escaping one too")); waive_item1(d)

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
    ("stale_source listing a status line", load("result-stale-source.json"), res, lambda d: d["records_written"].append({"kind": "status_line", "path": "docs/x.md", "appended": False})),
    ("stale_source with matched true", load("result-stale-source.json"), res, lambda d: set_path(d, ["source_identity", "matched"], True)),
    ("stale_source without expected identity", load("result-stale-source.json"), res, lambda d: del_path(d, ["source_identity", "expected"])),
    ("verifier_unavailable carrying a result", load("result-verifier-unavailable.json"), res, lambda d: d.__setitem__("result", "all_clear")),
    ("verifier_unavailable listing a verdict-doc copy", load("result-verifier-unavailable.json"), res, lambda d: d["records_written"].append({"kind": "verdict_doc_copy", "path": "docs/reviews/x.md", "appended": True})),
    ("stopped run listing a punch-list block", stopped, res, lambda d: d["records_written"].append({"kind": "punch_list_block", "path": "docs/plans/2026-09-18-widget-export.md", "appended": True})),
    ("nothing_open listing a waiver line", load("result-nothing-open.json"), res, lambda d: d["records_written"].append({"kind": "waived_line", "path": "docs/plans/x.md", "appended": True})),
    ("completed without verifier metadata", completed, res, lambda d: del_path(d, ["run", "verifier"])),
    ("completed without session_wrote_fix", completed, res, lambda d: del_path(d, ["run", "session_wrote_fix"])),
    ("completed with zero items", completed, res, lambda d: (d.__setitem__("items", []), set_path(d, ["checklist", "count"], 0))),
    ("completed without a receipt", completed, res, lambda d: del_path(d, ["receipt_path"])),
    ("completed without boundary_violations", completed, res, lambda d: del_path(d, ["boundary_violations"])),
    ("completed without rejected_grants", completed, res, lambda d: del_path(d, ["rejected_grants"])),
    ("completed without transaction identities", completed, res, lambda d: del_path(d, ["source_identity", "at_transaction"])),
    ("new defect not charged to a slice", blocked, res, lambda d: del_path(d, ["new_defects", 0, "charged_to_slice"])),
    ("punch-list block written non-append", completed, res, lambda d: set_path(d, ["records_written", BLOCK, "appended"], False)),
    ("status line written as an append", completed, res, lambda d: set_path(d, ["records_written", STATUS, "appended"], True)),
    ("record write of a forbidden kind", completed, res, lambda d: d["records_written"].append({"kind": "source_edit", "path": "src/x.ts", "appended": False})),
    ("headless envelope carrying a question", load("result-missing-input-headless.json"), res, lambda d: set_path(d, ["missing_input", "question"], "which one?")),
    ("no-run envelope carrying a question", load("result-invalid-input-envelope.json"), res, lambda d: set_path(d, ["missing_input", "question"], "which one?")),
    ("nothing_open with count 1", load("result-nothing-open.json"), res, lambda d: set_path(d, ["checklist", "count"], 1)),
    ("nothing_open carrying items", load("result-nothing-open.json"), res, lambda d: d.__setitem__("items", [])),
    ("recording_failed carrying cards", load("result-recording-failed.json"), res, lambda d: d.__setitem__("cards", [])),
    ("recording_failed carrying a result", load("result-recording-failed.json"), res, lambda d: d.__setitem__("result", "partial")),
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
    ("fixed carrying a block explanation", completed, res, lambda d: set_path(d, ["items", 0, "verification", "blocked"], "sandbox")),
    ("fixed carrying a missing-evidence field", completed, res, lambda d: set_path(d, ["items", 0, "verification", "missing"], "fixture")),
    ("fixed from a verifier not_fixed merely confirmed", completed, res, lambda d: set_path(d, ["items", 0, "adjudication", "verifier_said"], "not_fixed")),
    ("not_fixed from a verifier fixed merely confirmed", completed, res, lambda d: set_path(d, ["items", 1, "adjudication", "verifier_said"], "fixed")),
    ("all_clear with an unwaived open item", completed, res, lambda d: d.__setitem__("result", "all_clear")),
    ("all_clear by waiver beside a new defect", completed, res, lambda d: (waive_item1(d), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), d.__setitem__("new_defects", [DEFECT]))),
    ("not_clear with a fixed item", completed, res, lambda d: d.__setitem__("result", "not_clear")),
    ("not_clear with every item waived and no new defect", completed, res, lambda d: (all_not_fixed_waived(d), d.__setitem__("result", "not_clear"))),
    ("partial with every item fixed and no new defect", completed, res, lambda d: (set_path(d, ["items", 1, "disposition"], "fixed"), del_path(d, ["items", 1, "reason"]), set_path(d, ["items", 1, "adjudication", "verifier_said"], "fixed"))),
    ("partial with a fixed item and only a waived item beside it", completed, res, lambda d: waive_item1(d)),
    ("boundary violation with a promoted result", completed, res, lambda d: d.__setitem__("boundary_violations", ["wrote src/x.ts"])),
    ("waived marker without quoted words", completed, res, lambda d: set_path(d, ["items", 1, "waived"], {"date": "2026-09-20"})),
    ("waived marker with quoted words spanning lines", completed, res, lambda d: set_path(d, ["items", 1, "waived"], dict(MARK, quoted_words="waive\nit"))),
    ("reopened marker with an unknown field", blocked, res, lambda d: set_path(d, ["items", 2, "reopened", "by"], "model")),
    ("claim with a trailing line feed", completed, res, lambda d: set_path(d, ["items", 0, "claim"], "claim\n")),
    ("claim with a carriage return", completed, res, lambda d: set_path(d, ["items", 0, "claim"], "cla\rim")),
    ("actual identity without the submodule check", completed, res, lambda d: del_path(d, ["source_identity", "actual", "submodules"])),
    ("actual identity with an initialized submodule", completed, res, lambda d: set_path(d, ["source_identity", "actual", "submodules"], ["vendor/lib"])),
    ("input: claim with a trailing line feed", caller, inp, lambda d: set_path(d, ["target", "items", 0, "claim"], "claim\n")),
    ("input: failure scenario spanning lines", caller, inp, lambda d: set_path(d, ["target", "items", 0, "failure_scenario"], "one\ntwo")),
    ("input: quoted words spanning lines", caller, inp, lambda d: set_path(d, ["authorization", "waivers", 0, "quoted_words"], "waive\nit")),
    ("input: pin with an initialized submodule", caller, inp, lambda d: set_path(d, ["source_identity", "submodules"], ["vendor/lib"])),
]
rejected = sum(neg(*c) for c in cases)

# Positive mutations: documents the contract allows and the schema must accept.
def pos(name, doc, validator, mutate):
    d = copy.deepcopy(doc); mutate(d)
    errs = list(validator.iter_errors(d))
    print(("ACCEPTED " if not errs else "REJECTED (BUG) ") + name + ("" if not errs else ": " + errs[0].message[:120]))
    return not errs

def boundary_failure(d):
    d["boundary_violations"] = ["src/export.ts changed between the pre-transaction identity and the status-line check; status-line steps cancelled"]
    d["result"] = "not_clear"; set_path(d, ["cards", 0, "after"], d["cards"][0]["before"]); set_path(d, ["cards", 0, "reason"], "boundary violation: no card moves")
    del d["records_written"][STATUS]

positives = [
    ("a not-started card moved by the mapping", completed, res, lambda d: (set_path(d, ["cards", 0, "before"], "not started"), set_path(d, ["cards", 0, "after"], "signed off with conditions"))),
    ("an independent evidence-backed upgrade", completed, res, lambda d: (set_path(d, ["items", 1, "disposition"], "fixed"), del_path(d, ["items", 1, "reason"]), set_path(d, ["items", 1, "adjudication", "driver_action"], "upgraded"), set_path(d, ["items", 1, "adjudication", "upgrade_evidence"], "the verifier lacked fixtures/no-title.json; run with it the cell is empty for null and absent"), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), set_path(d, ["cards", 0, "after"], "signed off"))),
    ("a downgrade with a note", completed, res, lambda d: (set_path(d, ["items", 0, "disposition"], "not_fixed"), set_path(d, ["items", 0, "reason"], "reproduces"), set_path(d, ["items", 0, "adjudication", "verifier_said"], "fixed"), set_path(d, ["items", 0, "adjudication", "driver_action"], "downgraded"), set_path(d, ["items", 0, "adjudication", "note"], "the test the verifier ran does not cover the comma case"), d.__setitem__("result", "not_clear"), set_path(d, ["cards", 0, "after"], "rejected"))),
    ("a waived clearance: the open item waived, all_clear, card signed off", completed, res, lambda d: (waive_item1(d), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), set_path(d, ["cards", 0, "after"], "signed off"), set_path(d, ["cards", 0, "reason"], "BLOCKER cleared; the MAJOR waived per user"))),
    ("every item waived, nothing open, all_clear", completed, res, lambda d: (all_not_fixed_waived(d), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), set_path(d, ["cards", 0, "after"], "signed off"))),
    ("a waiver on an item the run found fixed", completed, res, lambda d: set_path(d, ["items", 0, "waived"], dict(MARK, quoted_words="waive the escaping one"))),
    ("a boundary violation beside a verified fix: not_clear, cards frozen", completed, res, boundary_failure),
    ("a verifier_unavailable run listing an extra artifact", load("result-verifier-unavailable.json"), res, lambda d: d["records_written"].insert(1, {"kind": "run_artifact", "path": "/tmp/recheck-a-20260920-8811/checkpoint.json", "appended": False})),
]
accepted = sum(pos(*c) for c in positives)

# Checkpoint example (section 11): item-state union, digest, chain, log, and the one allowed repair.
def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def check_checkpoint(cp, log_lines):
    """Return 'ok', 'repair', or the first defect found."""
    for i, st in enumerate(cp["items"]):
        if st["state"] == "pending" and "result" in st: return f"item {i}: pending with a result"
        if st["state"] == "done" and not item.is_valid(st.get("result", {})): return f"item {i}: done without a valid result"
        if st["state"] not in ("pending", "done"): return f"item {i}: unknown state"
    body = copy.deepcopy(cp); self_ = body["integrity"].pop("self")
    if hashlib.sha256(canon(body)).hexdigest() != self_: return "self digest does not recompute"
    seq, prev = cp["integrity"]["seq"], cp["integrity"]["prev"]
    rows = [l.split() for l in log_lines if l.strip()]
    if [int(r[0]) for r in rows] != list(range(len(rows))): return "log has a gap or a repeated seq"
    if rows and rows[-1] == [str(seq), self_]:
        if seq == 0: return "ok" if prev is None and len(rows) == 1 else "prev must be null at seq 0"
        return "ok" if len(rows) >= 2 and rows[-2][1] == prev else "prev is not the line before"
    if len(rows) >= 2 and rows[-2] == [str(seq), self_] and int(rows[-1][0]) == seq + 1:
        return "repair"  # the log announced a write whose rename never landed: drop the line and continue
    return "(seq, self) is not the log's last line"

cp = load("checkpoint-partial.json")
log = open(os.path.join(HERE, "checkpoint-partial.log")).read().splitlines()
cp_checks = 0
def cpcase(name, expect, mutate_cp=None, mutate_log=None):
    global cp_checks
    c = copy.deepcopy(cp); l = list(log)
    if mutate_cp: mutate_cp(c)
    if mutate_log: mutate_log(l)
    got = check_checkpoint(c, l)
    ok = (got == expect) if expect in ("ok", "repair") else (got not in ("ok", "repair"))
    print(("CHECKPOINT OK " if ok else "CHECKPOINT (BUG) ") + name + f" -> {got}")
    cp_checks += ok

def resign(c):
    body = copy.deepcopy(c); del body["integrity"]["self"]
    c["integrity"]["self"] = hashlib.sha256(canon(body)).hexdigest()

cp_cases = [
    ("the example: one done item, two pending, digest and chain intact", "ok", None, None),
    ("a pending item carrying a result", "corrupt", lambda c: c["items"][1].__setitem__("result", c["items"][0]["result"]), None),
    ("a done item without a result", "corrupt", lambda c: c["items"][0].pop("result"), None),
    ("a done item whose result is fixed with a reason", "corrupt", lambda c: (c["items"][0]["result"].__setitem__("disposition", "fixed"), resign(c)), None),
    ("an edited item state with the digest left stale", "corrupt", lambda c: c["items"][0]["result"].__setitem__("disposition", "fixed"), None),
    ("an edited checkpoint re-signed but the log untouched", "corrupt", lambda c: (c["items"][1].__setitem__("retries", 1), resign(c)), None),
    ("a truncated log", "corrupt", None, lambda l: l.pop()),
    ("a re-signed checkpoint one past its log: a forged next write", "corrupt", lambda c: (c["items"][1].__setitem__("state", "done"), c["items"][1].__setitem__("result", c["items"][0]["result"]), c["integrity"].__setitem__("seq", 4), c["integrity"].__setitem__("prev", cp["integrity"]["self"]), resign(c)), None),
    ("a log two lines ahead of the checkpoint", "corrupt", None, lambda l: l.extend(["4 " + "1" * 64, "5 " + "2" * 64])),
    ("a log with a gap", "corrupt", None, lambda l: l.pop(1)),
    ("prev pointing at the wrong line", "corrupt", lambda c: (c["integrity"].__setitem__("prev", log[0].split()[1]), resign(c)), None),
    ("the log announces a write whose rename never landed: the one tolerated state", "repair", None, lambda l: l.append("4 " + "1" * 64)),
]
for c in cp_cases: cpcase(*c)

n_files = len([f for f in glob.glob(os.path.join(HERE, "*.json")) if not os.path.basename(f).startswith("checkpoint-")])
print(f"positive: {n_files} files, {failures} failing; negative: {rejected}/{len(cases)} rejected; positive mutations: {accepted}/{len(positives)} accepted; checkpoint checks: {cp_checks}/{len(cp_cases)}")
sys.exit(1 if failures or rejected != len(cases) or accepted != len(positives) or cp_checks != len(cp_cases) else 0)
