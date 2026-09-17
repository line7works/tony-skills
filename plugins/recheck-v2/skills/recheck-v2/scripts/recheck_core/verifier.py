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
STATIC_REASONS = ("mutates_real_state", "non_executable_artifact")
EVIDENCE_KINDS = ("command", "read", "diff", "artifact")
SEP = " · "
SIDECAR = "calls.json"
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


def is_complete(status):
    """E8-A40: the one decision "is this call complete" wherever a call record is read; the
    checkpoint stores `complete` (E8-A1) and the transport vocabulary says `ok`."""
    return status in (COMPLETE, OK)


def classify_status(status):
    """complete | retryable | deterministic | None (not in the vocabulary)."""
    if is_complete(status):
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


def _nullable_text(value, what, problems):
    """E8-A47: null or a non-empty one-line string; a boolean, a number, or any other type is a violation
    naming the key."""
    if value is None:
        return
    if not isinstance(value, str):
        problems.append("%s is not a string or null (got %s)" % (what, type(value).__name__))
        return
    if not value.strip():
        problems.append("%s is an empty string" % what)
        return
    _one_line(value, what, problems)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


# E8-A27: the block, each item, each evidence entry, and each candidate are closed shapes; E8-A47: every one of
# the six top-level keys is required (the four lists may be empty, never null)
TOP_KEYS = ("recheck_verifier_report", "items", "new_defects", "grant_claims", "injection_attempts", "refused_actions")
TOP_REQUIRED = TOP_KEYS
ITEM_KEYS = ("index", "location", "disposition", "reason", "method", "static_reason", "blocked", "missing",
             "missed_case", "evidence", "location_after_fix")
EVIDENCE_KEYS = ("kind", "detail", "artifact")
CANDIDATE_KEYS = ("caused_by_index", "location", "claim", "failure_scenario", "evidence")
STRING_LISTS = ("grant_claims", "injection_attempts", "refused_actions")


def _closed(obj, keys, what, problems):
    """Every listed key present, no other key; returns False when the object is not even a dict."""
    if not isinstance(obj, dict):
        problems.append("%s is not an object" % what)
        return False
    ok = True
    for k in keys:
        if k not in obj:
            problems.append("%s lacks the key %s" % (what, k))
            ok = False
    for k in obj:
        if k not in keys:
            problems.append("%s carries the unknown key %s" % (what, k))
            ok = False
    return ok


def _check_evidence(ev, what, problems):
    """A non-empty list of closed evidence entries: kind in the vocabulary, a non-empty one-line detail,
    artifact a string or null."""
    if not isinstance(ev, list) or not ev:
        problems.append("%s evidence is empty" % what)
        return
    for n, e in enumerate(ev):
        label = "%s evidence[%d]" % (what, n)
        if not _closed(e, EVIDENCE_KEYS, label, problems):
            continue
        if e.get("kind") not in EVIDENCE_KINDS:
            problems.append("%s kind %r is not one of %s" % (label, e.get("kind"), ", ".join(EVIDENCE_KINDS)))
        if not isinstance(e.get("detail"), str) or not e["detail"].strip():
            problems.append("%s detail is not a non-empty string" % label)
        else:
            _one_line(e["detail"], label + ".detail", problems)
        if e.get("artifact") is not None:
            _one_line(e.get("artifact"), label + ".artifact", problems)


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
    if not isinstance(tail, dict) or not _is_int(tail.get("recheck_verifier_report")) or tail.get("recheck_verifier_report") != VERSION:
        return {"ok": False, "reason": "the report's last fenced block is not a recheck_verifier_report version %d (recheck_verifier_report must be the integer %d)" % (VERSION, VERSION), "tail": None}
    problems = []
    for k in TOP_REQUIRED:
        if k not in tail:
            problems.append("the block lacks the key %s" % k)
    for k in tail:
        if k not in TOP_KEYS:
            problems.append("the block carries the unknown key %s" % k)
    if problems:
        return {"ok": False, "reason": "the report's tail breaks the field rules: " + "; ".join(problems[:5]), "tail": None}
    items = tail.get("items")
    if not isinstance(items, list):
        return {"ok": False, "reason": "the report's items is not a list", "tail": None}
    found = [it.get("index") if isinstance(it, dict) else None for it in items]
    ints = sorted(i for i in found if _is_int(i))
    if indexes == ANY_INDEXES:
        if len(ints) != len(found) or len(set(ints)) != len(ints) or any(i < 0 or i >= n_items for i in ints):
            return {"ok": False, "reason": "the report's items carry an index outside 0..%d or a repeated one (got %r)" % (n_items - 1, found), "tail": None}
    else:
        expected = list(range(n_items)) if indexes is None else sorted(set(indexes))
        if ints != expected or len(found) != len(expected):
            what = "every index 0..%d" % (n_items - 1) if indexes is None else "exactly the indexes %s" % ", ".join(str(i) for i in expected)
            return {"ok": False, "reason": "the report's items do not cover %s exactly once (got %r)" % (what, found), "tail": None}
    for it in items:
        idx = it.get("index")
        if not _closed(it, ITEM_KEYS, "item %s" % idx, problems):
            continue
        if parse_location_text(it.get("location")) is None:
            problems.append("item %s: location %r is not file:line" % (idx, it.get("location")))
        disp, reason = it.get("disposition"), it.get("reason")
        if disp not in ("fixed", "not_fixed"):
            problems.append("item %s: disposition %r" % (idx, disp))
        # E8-A47: every nullable field is typed; a boolean or a number where a string or null is expected is a violation
        if reason is not None and reason not in REASONS:
            problems.append("item %s: reason %r is not null or one of %s" % (idx, reason, ", ".join(REASONS)))
        if disp == "fixed" and reason is not None:
            problems.append("item %s: a fixed item carries a reason" % idx)
        if disp == "not_fixed" and reason not in REASONS:
            problems.append("item %s: reason %r is not one of %s" % (idx, reason, ", ".join(REASONS)))
        for f, r in (("missed_case", "missed_case"), ("blocked", "verification_blocked"), ("missing", "missing_evidence")):
            _nullable_text(it.get(f), "item %s %s" % (idx, f), problems)
            if (reason == r) != (it.get(f) is not None):
                problems.append("item %s: %s must be non-null exactly for reason %s" % (idx, f, r))
        method = it.get("method")
        if method not in ("executed", "static"):
            problems.append("item %s: method %r" % (idx, method))
        static_reason = it.get("static_reason")
        if static_reason is not None and static_reason not in STATIC_REASONS:
            problems.append("item %s: static_reason %r is not null or one of %s" % (idx, static_reason, ", ".join(STATIC_REASONS)))
        if method == "static" and static_reason is None:
            problems.append("item %s: static needs static_reason" % idx)
        if method == "executed" and static_reason is not None:
            problems.append("item %s: executed carries a static_reason" % idx)
        _check_evidence(it.get("evidence"), "item %s" % idx, problems)
        for f in ("location", "location_after_fix"):
            _one_line(it.get(f), "item %s %s" % (idx, f), problems)
    defects = tail.get("new_defects")
    if not isinstance(defects, list):
        problems.append("new_defects is not a list (null is not an empty list)")
        defects = []
    for n, d in enumerate(defects):
        label = "new_defects[%d]" % n
        if not _closed(d, CANDIDATE_KEYS, label, problems):
            continue
        cb = d.get("caused_by_index")
        if not _is_int(cb) or cb < 0 or cb >= n_items:
            problems.append("%s caused_by_index %r is not an integer in 0..%d" % (label, cb, n_items - 1))
        if parse_location_text(d.get("location")) is None:
            problems.append("%s location %r is not file:line" % (label, d.get("location")))
        for f in ("claim", "failure_scenario"):
            if not isinstance(d.get(f), str) or not d[f].strip():
                problems.append("%s %s is not a non-empty string" % (label, f))
            else:
                _one_line(d[f], "%s.%s" % (label, f), problems)
        _check_evidence(d.get("evidence"), label, problems)
    for f in STRING_LISTS:
        v = tail.get(f)
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            problems.append("%s is not a list of strings (null is not an empty list)" % f)
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


# E11 fix round, item 3 (Astra's verification of 31329cd). Contract section 5: "An execution
# the sandbox or environment stopped is `verification_blocked`, never `static`." The core
# retained a first report for an item saying the required execution was refused, took the
# permitted retry's static `fixed`, and completed — the block was in the run's own history
# and nothing read it.
#
# A block is recognised two ways, both from the RETAINED REPORT itself, never from a reply or
# the executor's account:
#   - structured: the report's own tail gives that item reason `verification_blocked`;
#   - declared: the retained text carries the vocabulary contract section 5 and verifier.md
#     fix for a stopped execution. The list is closed and is quoted from those two documents.
# E11 second fix, NEW 9 (Astra's re-check of the fix round). "no service observation" was in
# this list and is not a declaration of a stopped execution: her prose-only X2-01 report says
# "It needs no service observation", a sentence stating that NO execution was needed, and the
# core downgraded the ordinary static clearance that followed. A declared block is a statement
# that a REQUIRED EXECUTION WAS REFUSED OR STOPPED, never a vocabulary word that can appear in
# a sentence saying no execution was needed. Dropped, with "execution the sandbox stopped",
# which only ever matched where the shorter "the sandbox stopped" already did.
BLOCK_DECLARATIONS = (
    "verification blocked",
    "verification_blocked",
    "execution was refused",
    "execution was stopped",
    "the sandbox stopped",
    "the environment stopped",
)

# The same trap in the other direction: every remaining phrase reads naturally negated with
# the negator in FRONT of it — "no execution was refused", "nothing the environment stopped" —
# and a plain substring scan matches both. So a match is refused when a negation stands within
# a few words before the phrase inside the same sentence. (The other permitted route, keeping
# only phrases that cannot be negated, does not exist for this vocabulary: contract section 5
# and verifier.md write the block in exactly these words.)
BLOCK_NEGATIONS = ("no", "not", "never", "nothing", "none", "without", "nor", "neither",
                   "cannot", "n't")
BLOCK_NEGATION_WINDOW = 4          # words between the negation and the phrase
_SENTENCE_BREAK = ".;:!?\n\r"


def _negated_before(text_lower, at):
    """Does a negation stand within a few words before `at`, in the same sentence?"""
    start = 0
    for index in range(at - 1, -1, -1):
        if text_lower[index] in _SENTENCE_BREAK:
            start = index + 1
            break
    words = [w.strip("\"'(),[]{}") for w in text_lower[start:at].split()]
    for word in [w for w in words if w][-BLOCK_NEGATION_WINDOW:]:
        if word in BLOCK_NEGATIONS or word.endswith("n't"):
            return True
    return False


def declared_block(text):
    """The first phrase in `text` that DECLARES a stopped execution, with its quote.

    Returns `(phrase, quote)`, or `(None, None)` when the text carries none — including a
    text where every occurrence is negated.
    """
    lowered = text.lower()
    for phrase in BLOCK_DECLARATIONS:
        at = lowered.find(phrase)
        while at != -1:
            if not _negated_before(lowered, at):
                return phrase, text[max(0, at - 40):at + len(phrase) + 40].strip()
            at = lowered.find(phrase, at + 1)
    return None, None


def blocked_history(run_dir, checkpoint_doc, index):
    """Every retained report of this run that recorded a blocked execution for `index`.

    Returns a list of `{call_id, raw_path, how, quote}`; empty when none did.
    """
    found = []
    for call in checkpoint_doc.get("verifier_calls") or []:
        path = call.get("raw_path")
        if not path or not os.path.isfile(path):
            continue
        covers = call.get("items")
        if covers and index not in covers:
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (IOError, OSError):
            continue
        how, quote = None, None
        # the history scan reads whatever tail is there; it never grades coverage, so the
        # index bound is only "at least this item".
        parsed = parse_report_tail(text, index + 1, ANY_INDEXES)
        tail = parsed.get("tail") if isinstance(parsed, dict) else None
        if tail:
            for row in tail.get("items") or []:
                if row.get("index") == index and row.get("reason") == "verification_blocked":
                    how = "the retained report's own structured tail"
                    quote = row.get("blocked") or "reason verification_blocked"
                    break
        if how is None:
            phrase, said = declared_block(text)
            if phrase:
                how = "the retained report declares a stopped execution"
                quote = said
        if how:
            found.append({"call_id": call.get("call_id") or call.get("id"),
                          "raw_path": path, "how": how, "quote": quote})
    return found


def retained_report(run_dir, checkpoint_doc, index=None):
    """The call whose retained report adjudication uses (E8-7): the last call recorded complete
    whose file still hashes to raw_sha256 and, when `index` is given, whose items cover it
    (E8-A15). Returns (call, text) or (None, None)."""
    for call in reversed(checkpoint_doc.get("verifier_calls") or []):
        if not is_complete(call.get("status")) or not call.get("raw_path") or not call.get("raw_sha256"):
            continue
        if index is not None and index not in (call.get("items") or []):
            continue
        path = call["raw_path"]
        if not os.path.isfile(path) or canon.sha256_file(path) != call["raw_sha256"]:
            continue
        with open(path, "r", encoding="utf-8") as fh:
            return call, fh.read()
    return None, None
