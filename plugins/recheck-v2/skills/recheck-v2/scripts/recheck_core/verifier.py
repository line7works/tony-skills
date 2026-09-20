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
# and a plain substring scan matches both. So a match is refused when a negation NEGATES THE
# PHRASE ITSELF. (The other permitted route, keeping only phrases that cannot be negated, does
# not exist for this vocabulary: contract section 5 and verifier.md write the block in exactly
# these words.)
#
# THE RULE (E11-15 send-back, A2). Walk backwards from the phrase, word by word, without
# leaving the sentence (the scan stops at . ; : ! ? or a newline):
#   - a negation word reached this way negates the phrase: no block;
#   - a word from BLOCK_NEGATION_CARRIERS — the determiners and copulas a negation may legally
#     carry across — is stepped over, up to BLOCK_NEGATION_WINDOW of them;
#   - ANY other word (a noun, a verb, a connector: "output", "because", "required") means the
#     negation, if there is one further back, belongs to something else, and the block stands.
# So "no execution was refused" is not a block, and "No output because execution was refused"
# is: the "no" there negates the output, not the refusal. The first form was the sent case;
# the second was Astra's adjacent one.
BLOCK_NEGATIONS = ("no", "not", "never", "nothing", "none", "without", "nor", "neither",
                   "cannot", "n't")
BLOCK_NEGATION_CARRIERS = ("the", "a", "an", "any", "such", "actual", "real", "this", "that",
                           "its", "their", "ever", "been", "being", "be", "was", "were",
                           "is", "are")
BLOCK_NEGATION_WINDOW = 4          # carrier words a negation may reach across
_SENTENCE_BREAK = ".;:!?\n\r"

# E11-45 S3/N2 (batch B): the reports are MARKDOWN, and the block vocabulary is what a careful
# report quotes when it says the case is NOT one. Two of the eight round-2 F4 reports wrote
# "so this is not `verification_blocked`" and "This is not `verification_blocked` - nothing in
# the sandbox stopped an execution": the backtick before the phrase was left on the preceding
# word by the old strip set, so the scan met a word that was neither a negation nor a carrier
# and stopped one word short of the "not" that was right there. Markdown emphasis (`*`, `_`,
# `~`) is stripped for the same reason. A punctuation-only token strips to nothing and is
# dropped by the `if w` filter, so the walk continues past it rather than ending on it.
_WORD_TRIM = "\"'(),[]{}`*_~"


def _negated_before(text_lower, at):
    """Does a negation before `at`, in the same sentence, negate the phrase AT `at`?"""
    start = 0
    for index in range(at - 1, -1, -1):
        if text_lower[index] in _SENTENCE_BREAK:
            start = index + 1
            break
    words = [w.strip(_WORD_TRIM) for w in text_lower[start:at].split()]
    carried = 0
    for word in reversed([w for w in words if w]):
        if word in BLOCK_NEGATIONS or word.endswith("n't"):
            return True
        if word not in BLOCK_NEGATION_CARRIERS:
            return False         # the negation, if any, negates that word, not the phrase
        carried += 1
        if carried > BLOCK_NEGATION_WINDOW:
            return False
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


# ---- S3: the stop reason derived from execution (E11-45 S3) ----------------------------------
#
# Contract section 5 names the four reasons; until now the core took the one the verifier TYPED.
# The E10 campaign's F5 lane is the record of why that is not enough: a session whose own report
# showed the operation declined still typed `missing_evidence`, and the core wrote it down. S3
# derives the reason from what the run can OBSERVE and keeps the typed one beside it.
#
# What counts as an observation, in order of authority:
#   1. the record-call transport status - a call that did not complete is a blocked verification
#      whatever the report says;
#   2. a policy refusal or an unreachable service in the RETAINED output of the item's own
#      command evidence, or in the report's own `blocked` text;
#   2(c). an absent required input that the command's own retained output reported (batch B);
#   3. whether the item's method was `executed` and a command-kind evidence entry exists;
#   4. an absent required input, where no command ran at all.
# Anything else is UNRESOLVED: recorded, never defaulted.
#
# The derivation reads execution facts and the report's FACTUAL fields (method, evidence kinds,
# the narrower case it names). It never reads the item's `reason` word - that is the claim under
# test, and mapping it onto itself would derive nothing.

REFUSAL_OBSERVATIONS = (
    "permission denied",
    "operation not permitted",
    "operation was declined",
    "declined by policy",
    "blocked by policy",
    "denied by policy",
    "not permitted by the sandbox",
    "sandbox denied",
    "refused by the sandbox",
    "outbound network is blocked",
    "network access is disabled",
    "eacces",
    "eperm",
)

UNREACHABLE_OBSERVATIONS = (
    "could not resolve host",
    "name or service not known",
    "nodename nor servname provided",
    "temporary failure in name resolution",
    "getaddrinfo",
    "connection refused",
    "network is unreachable",
    "no route to host",
    "connection timed out",
)

ABSENT_INPUT_OBSERVATIONS = (
    "no such file or directory",
    "does not exist",
    "is not present",
    "was not provided",
    "not found",
)

# E11-45 N2 (batch B): the same observation as it reaches the RETAINED OUTPUT of a command that
# actually ran. An interpreter names an absent input in its own words - `FileNotFoundError`,
# `ENOENT`, `[Errno 2]` - and those are the words the six defaulted round-2 F4 reports carried
# (one of them, `codex` r1, carried only "exited 1 with FileNotFoundError" and none of the
# prose forms above). The list is closed and every entry is an operating-system or interpreter
# report of an absent path, never prose about one.
ABSENT_INPUT_IN_OUTPUT = ABSENT_INPUT_OBSERVATIONS + (
    "filenotfounderror",
    "no such file",
    "enoent",
    "errno 2",
)

UNRESOLVED = "unresolved"


def _observed_in(texts, phrases):
    """The first phrase of `phrases` observed, unnegated, in any of `texts`."""
    for text in texts:
        if not text:
            continue
        lowered = text.lower()
        for phrase in phrases:
            at = lowered.find(phrase)
            while at != -1:
                if not _negated_before(lowered, at):
                    return phrase, text[max(0, at - 60):at + len(phrase) + 60].strip()
                at = lowered.find(phrase, at + 1)
    return None, None


def _evidence_outputs(item, run_dir):
    """The retained output of the item's command evidence, plus the details it carries."""
    texts, commands = [], 0
    for e in item.get("evidence") or []:
        if not isinstance(e, dict):
            continue
        if e.get("kind") == "command":
            commands += 1
        if e.get("detail"):
            texts.append(e["detail"])
        art = e.get("artifact")
        if not art:
            continue
        path = artifact_abs(run_dir, art)
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    texts.append(fh.read(200000))
            except (IOError, OSError):
                pass
    return texts, commands


def derive_reason(item, run_dir, call_status=None, report_text=None):
    """The reason this item's verification ACTUALLY reached, derived from execution (E11-45 S3).

    Returns `{"reason": one of REASONS or None, "observed": str, "how": str}`. `reason` is None
    exactly when the observation is UNRESOLVED; the caller records that and keeps the reason the
    report stated rather than defaulting to one.
    """
    texts, commands = _evidence_outputs(item, run_dir)
    blocked_text = item.get("blocked")
    missing_text = item.get("missing")
    if blocked_text:
        texts = texts + [blocked_text]
    # 1. the transport itself (the checkpoint spells a finished call `complete`, the transport
    #    vocabulary spells it `ok`; either is "the call completed")
    if call_status is not None and not is_complete(call_status):
        return {"reason": "verification_blocked", "observed": "the call did not complete",
                "how": "the record-call transport status is %r, not %r" % (call_status, OK)}
    # 2. a policy refusal, then an unreachable service, in what the run retained
    phrase, quote = _observed_in(texts, REFUSAL_OBSERVATIONS)
    if phrase:
        return {"reason": "verification_blocked", "observed": "the operation was declined",
                "how": "the retained output carries %r: %s" % (phrase, quote)}
    phrase, quote = _observed_in(texts, UNREACHABLE_OBSERVATIONS)
    if phrase:
        return {"reason": "verification_blocked", "observed": "the service was unreachable",
                "how": "the retained output carries %r: %s" % (phrase, quote)}
    # 2(c). E11-45 N2 (batch B): an ABSENT REQUIRED INPUT that the command's own retained output
    #       reported. This is an observation of the same rank as a policy refusal or an
    #       unreachable service - all three read the run's retained OUTPUT - so it is settled
    #       here, above the report's prose and above the reproduction default of step 3.
    #
    #       The defect it closes (S3 and N2): step 3 returned `reproduces` for ANY executed
    #       command, and step 4 asked for `not commands`, so a command that RAN AND HIT THE
    #       ABSENT INPUT could never reach the absent-input rule. All eight round-2 with-skill
    #       F4 trials had a correct `missing_evidence` from the verifier replaced - six by this
    #       default, two through `declared_block` reading a backticked negation as a
    #       declaration. A command that ran and hit the absent input is `missing_evidence`; a
    #       command that ran and showed the defect is `reproduces`, which is step 3, unchanged.
    #
    #       A policy refusal and an unreachable service still win: they are tested first, so an
    #       F5 block whose output also mentions a missing path stays `verification_blocked`.
    phrase, quote = _observed_in(texts, ABSENT_INPUT_IN_OUTPUT)
    if phrase and commands:
        return {"reason": "missing_evidence", "observed": "a required input is absent",
                "how": "a command ran and its retained output carries %r: %s"
                       % (phrase, quote)}
    if report_text:
        declared, said = declared_block(report_text)
        if declared:
            return {"reason": "verification_blocked", "observed": "the report declares a stopped execution",
                    "how": "the retained report declares %r: %s" % (declared, said)}
    # 3. the command ran
    if item.get("method") == "executed" and commands:
        if item.get("missed_case"):
            return {"reason": "missed_case", "observed": "the command ran and showed a narrower case",
                    "how": "an executed command-kind evidence entry, and the report names the "
                           "narrower case it found"}
        return {"reason": "reproduces", "observed": "the command ran and showed the defect",
                "how": "an executed command-kind evidence entry, and the report names no "
                       "narrower case"}
    # 4. a required input is absent
    phrase, quote = _observed_in(texts + [missing_text], ABSENT_INPUT_OBSERVATIONS)
    if phrase and not commands:
        return {"reason": "missing_evidence", "observed": "a required input is absent",
                "how": "no command ran, and the retained text carries %r: %s" % (phrase, quote)}
    return {"reason": None, "observed": UNRESOLVED,
            "how": "nothing the run retained decides this item: method %r, %d command-kind "
                   "evidence entries, no refusal, unreachable service or absent input observed"
                   % (item.get("method"), commands)}


def bound_service_observation(verification, service):
    """The evidence entry that OBSERVES `service`, or None (E11-45 S2).

    A bound observation is an EXECUTED command-kind evidence entry that names the service and
    retained its output. A read, a static method, or a command with nothing retained is not one:
    the point of the rule is that the service's own answer is on disk, not that someone said so.
    """
    if (verification or {}).get("method") != "executed":
        return None
    needle = (service or "").strip().lower()
    if not needle:
        return None
    for entry in verification.get("evidence") or []:
        if not isinstance(entry, dict) or entry.get("kind") != "command":
            continue
        path = entry.get("artifact_path")
        if not path or not os.path.isfile(path):
            continue
        haystacks = [entry.get("detail") or ""]
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                haystacks.append(fh.read(200000))
        except (IOError, OSError):
            pass
        if any(needle in text.lower() for text in haystacks):
            return entry
    return None


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
