"""The verifier protocol (E8 lane contract section 7; pilot contract section 7): the brief,
the structured report tail, the status vocabulary (E8-27, E8-A1), call bookkeeping, and the
mapping of the tail onto item results.

The core never dispatches a model: the executor summons the verifier through the adapter and
hands the report back with `record-call`. What the checkpoint's closed schema cannot hold about
a call (the adapter's kind, model, injected channels, refused actions, note) lives in the
sidecar `run_dir/verifier/calls.json`, a run artifact of the core's own.
"""
import json
import os
import re

from . import brief, canon

VERSION = 1
COMPLETE = "complete"
OK = "ok"
RETRYABLE = ("empty", "incomplete", "transport-failed", "timed-out", "capture-failed", "cancelled")
DETERMINISTIC = ("unknown-model", "floor-refused", "profile-unsupported", "version-mismatch",
                 "lane-unavailable", "invalid-request", "unauthorized")
STATUSES = (OK,) + RETRYABLE + DETERMINISTIC
REASONS = ("reproduces", "missed_case", "verification_blocked", "missing_evidence")
EVIDENCE_KINDS = ("command", "read", "diff", "artifact")
SEP = " · "
SIDECAR = "calls.json"
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


def classify_status(status):
    """complete | retryable | deterministic | None (not in the vocabulary)."""
    if status in (OK, COMPLETE):
        return COMPLETE
    if status in RETRYABLE:
        return "retryable"
    if status in DETERMINISTIC:
        return "deterministic"
    return None


def stored_status(status):
    return COMPLETE if status == OK else status


def call_id_for(run_id, k):
    return "%s-verify" % run_id if k == 1 else "%s-verify-%d" % (run_id, k)


def next_call_id(run_id, existing_ids):
    """The next unused suffix (E8-27): -verify, -verify-2, ... skipping any id already used."""
    k = 1
    while call_id_for(run_id, k) in existing_ids:
        k += 1
    return call_id_for(run_id, k), k


def raw_path_for(run_dir, k):
    return os.path.join(run_dir, "verifier", "raw.md" if k == 1 else "raw-%d.md" % k)


def scratch_dir(run_dir):
    return os.path.join(run_dir, "verifier")


def render_brief(workspace, run_dir, items, review_sheet_path=None, indexes=None):
    """The brief for the whole checklist, or, on a resume's fresh call, for the pending items only
    (`indexes`), which keep their original numbers (E8-A15)."""
    return brief.render(workspace, scratch_dir(run_dir), items, review_sheet_path, indexes=indexes)


# ---- the report tail -----------------------------------------------------------------------

def last_fenced_block(text):
    """The body of the last fenced block in the text, or None."""
    blocks, current, marker = [], None, None
    for line in text.split("\n"):
        m = FENCE.match(line)
        if m and (current is None or m.group(1)[0] == marker and not m.group(2).strip()):
            if current is None:
                current, marker = [], m.group(1)[0]
            else:
                blocks.append("\n".join(current))
                current, marker = None, None
            continue
        if current is not None:
            current.append(line)
    return blocks[-1] if blocks else None


def _one_line(value, what, problems):
    if value is None:
        return
    if not isinstance(value, str):
        problems.append("%s is not a string" % what)
        return
    if "\n" in value or "\r" in value or SEP in value or "·" in value:
        problems.append("%s spans lines or contains the separator" % what)


ANY_INDEXES = "any"


def parse_report_tail(text, n_items, indexes=None):
    """{"ok": bool, "reason": str, "tail": dict or None}: the last fenced JSON block, version 1,
    indexes covering every expected item exactly once, the field rules of section 7.

    `indexes` names the items the call covered (E8-A15: a resume's fresh call covers the pending
    items only, under their original numbers); None means every index 0..n_items-1; ANY_INDEXES
    accepts any set of distinct indexes within range (a reader that matches items itself)."""
    body = last_fenced_block(text)
    if body is None:
        return {"ok": False, "reason": "the report carries no fenced JSON block", "tail": None}
    try:
        tail = json.loads(body)
    except ValueError as exc:
        return {"ok": False, "reason": "the report's last fenced block is not JSON (%s)" % exc, "tail": None}
    if not isinstance(tail, dict) or tail.get("recheck_verifier_report") != VERSION:
        return {"ok": False, "reason": "the report's last fenced block is not a recheck_verifier_report version %d" % VERSION, "tail": None}
    items = tail.get("items")
    if not isinstance(items, list):
        return {"ok": False, "reason": "the report's items is not a list", "tail": None}
    found = [it.get("index") if isinstance(it, dict) else None for it in items]
    ints = sorted(i for i in found if isinstance(i, int) and not isinstance(i, bool))
    if indexes == ANY_INDEXES:
        if len(ints) != len(found) or len(set(ints)) != len(ints) or any(i < 0 or i >= n_items for i in ints):
            return {"ok": False, "reason": "the report's items carry an index outside 0..%d or a repeated one (got %r)" % (n_items - 1, found), "tail": None}
    else:
        expected = list(range(n_items)) if indexes is None else sorted(set(indexes))
        if ints != expected or len(found) != len(expected):
            what = "every index 0..%d" % (n_items - 1) if indexes is None else "exactly the indexes %s" % ", ".join(str(i) for i in expected)
            return {"ok": False, "reason": "the report's items do not cover %s exactly once (got %r)" % (what, found), "tail": None}
    problems = []
    for it in items:
        idx = it.get("index")
        disp, reason = it.get("disposition"), it.get("reason")
        if disp not in ("fixed", "not_fixed"):
            problems.append("item %s: disposition %r" % (idx, disp))
        if disp == "fixed" and reason is not None:
            problems.append("item %s: a fixed item carries a reason" % idx)
        if disp == "not_fixed" and reason not in REASONS:
            problems.append("item %s: reason %r is not one of %s" % (idx, reason, ", ".join(REASONS)))
        if (reason == "missed_case") != bool(it.get("missed_case")):
            problems.append("item %s: missed_case must be named exactly for reason missed_case" % idx)
        if (reason == "verification_blocked") != bool(it.get("blocked")):
            problems.append("item %s: blocked must be non-null exactly for reason verification_blocked" % idx)
        if (reason == "missing_evidence") != bool(it.get("missing")):
            problems.append("item %s: missing must be non-null exactly for reason missing_evidence" % idx)
        method = it.get("method")
        if method not in ("executed", "static"):
            problems.append("item %s: method %r" % (idx, method))
        if method == "static" and it.get("static_reason") not in ("mutates_real_state", "non_executable_artifact"):
            problems.append("item %s: static needs static_reason" % idx)
        if method == "executed" and it.get("static_reason"):
            problems.append("item %s: executed carries a static_reason" % idx)
        ev = it.get("evidence")
        if not isinstance(ev, list) or not ev:
            problems.append("item %s: evidence is empty" % idx)
        else:
            for n, e in enumerate(ev):
                if not isinstance(e, dict) or e.get("kind") not in EVIDENCE_KINDS or not e.get("detail"):
                    problems.append("item %s: evidence[%d] lacks a kind in %s or a detail" % (idx, n, ", ".join(EVIDENCE_KINDS)))
                else:
                    _one_line(e.get("detail"), "item %s evidence[%d].detail" % (idx, n), problems)
                    _one_line(e.get("artifact"), "item %s evidence[%d].artifact" % (idx, n), problems)
        for f in ("location", "missed_case", "blocked", "missing", "location_after_fix"):
            _one_line(it.get(f), "item %s %s" % (idx, f), problems)
    for n, d in enumerate(tail.get("new_defects") or []):
        for f in ("location", "claim", "failure_scenario"):
            if not d.get(f):
                problems.append("new_defects[%d] lacks %s" % (n, f))
            _one_line(d.get(f), "new_defects[%d].%s" % (n, f), problems)
    for f in ("grant_claims", "injection_attempts", "refused_actions"):
        v = tail.get(f)
        if v is not None and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
            problems.append("%s is not a list of strings" % f)
        elif v:
            for n, x in enumerate(v):
                _one_line(x, "%s[%d]" % (f, n), problems)
    if problems:
        return {"ok": False, "reason": "the report's tail breaks the field rules: " + "; ".join(problems[:5]), "tail": None}
    return {"ok": True, "reason": "", "tail": tail}


def tail_item(tail, index):
    for it in tail["items"]:
        if it.get("index") == index:
            return it
    return None


def parse_location_text(text):
    m = re.match(r"^(.+?):(\d+)$", (text or "").strip())
    if not m:
        return None
    return {"file": m.group(1), "line": int(m.group(2))}


def artifact_abs(run_dir, artifact):
    """An artifact path made absolute under run_dir/verifier/; None when it escapes the scratch."""
    if not artifact:
        return None
    scratch = scratch_dir(run_dir)
    path = artifact if os.path.isabs(artifact) else os.path.join(scratch, artifact)
    path = os.path.normpath(path)
    if path != scratch and not path.startswith(scratch + os.sep):
        return None
    return path


def map_item(item, run_dir):
    """The tail item onto item_result fields: {verifier_said, reason, verification, notes}. `notes` carries
    what was dropped on the way (an artifact missing from the scratch, E8-A10; a location_after_fix that
    is not file:line) and travels beside the item's evidence in the record-call document."""
    notes = []
    verification = {"method": item["method"], "evidence": []}
    if item["method"] == "static":
        verification["static_reason"] = item["static_reason"]
    if item.get("blocked"):
        verification["blocked"] = item["blocked"]
    if item.get("missing"):
        verification["missing"] = item["missing"]
    for n, e in enumerate(item["evidence"]):
        entry = {"kind": e["kind"], "detail": e["detail"]}
        if n == 0 and item.get("reason") == "missed_case":
            entry["detail"] = "missed case: %s; %s" % (item["missed_case"], e["detail"])
        if e.get("artifact"):
            path = artifact_abs(run_dir, e["artifact"])
            if path is None:
                notes.append("evidence artifact %r escapes the scratch directory; dropped" % e["artifact"])
            elif not os.path.isfile(path):
                notes.append("evidence artifact %r does not exist under the scratch directory; dropped" % e["artifact"])
            else:
                entry["artifact_path"] = path
        verification["evidence"].append(entry)
    after = item.get("location_after_fix")
    loc = parse_location_text(after)
    if loc:
        verification["location_after_fix"] = loc
    elif after is not None:
        notes.append("location_after_fix %r is not file:line; dropped" % (after,))
    return {"verifier_said": item["disposition"], "reason": item.get("reason"), "verification": verification,
            "missed_case": item.get("missed_case"), "notes": notes}


def candidate_defects(tail):
    out = []
    for d in tail.get("new_defects") or []:
        loc = parse_location_text(d.get("location"))
        out.append({"caused_by_index": d.get("caused_by_index"), "location": loc, "claim": d.get("claim"),
                    "failure_scenario": d.get("failure_scenario"), "evidence": d.get("evidence") or []})
    return out


# ---- the sidecar -------------------------------------------------------------------------

def sidecar_path(run_dir):
    return os.path.join(scratch_dir(run_dir), SIDECAR)


def load_sidecar(run_dir):
    path = sidecar_path(run_dir)
    if not os.path.isfile(path):
        return {"calls": []}
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def save_sidecar(run_dir, doc):
    os.makedirs(scratch_dir(run_dir), exist_ok=True)
    canon.atomic_write(sidecar_path(run_dir), (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def retained_report(run_dir, checkpoint_doc, index=None):
    """The call whose retained report adjudication uses (E8-7): the last call recorded complete
    whose file still hashes to raw_sha256 and, when `index` is given, whose items cover it
    (E8-A15). Returns (call, text) or (None, None)."""
    for call in reversed(checkpoint_doc.get("verifier_calls") or []):
        if call.get("status") != COMPLETE or not call.get("raw_path") or not call.get("raw_sha256"):
            continue
        if index is not None and index not in (call.get("items") or []):
            continue
        path = call["raw_path"]
        if not os.path.isfile(path) or canon.sha256_file(path) != call["raw_sha256"]:
            continue
        with open(path, "r", encoding="utf-8") as fh:
            return call, fh.read()
    return None, None
