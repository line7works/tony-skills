"""Schema loading and validation, plus the semantic checks of E8 lane contract section 8.

Schemas are loaded from the skill root (the directory holding SKILL.md), resolved from this
package's own location (scripts/recheck_core -> scripts -> skill root) unless a root is given
explicitly; never from a repo checkout or a plugin cache (pilot contract section 15, E8-17).

jsonschema is the one declared dependency (jsonschema==4.25.1 through `uv run`; the newest release
that installs under the 3.9.6 floor, amendment E8-A3). It is imported lazily:
`require_jsonschema()` exits 3 with the lane contract's one-line message on stderr and nothing on
stdout when it cannot be imported. The test hook RECHECK_TEST_NO_JSONSCHEMA=1, honored only
together with RECHECK_TEST=1 (lane contract section 9, slice 3), makes it behave as if the import
had failed.

Semantic checks: `run_semantic(result, input_doc=None, run_dir=None, workspace=None, records=None)` returns
`{"semantic": [findings], "skipped": [{"id", "reason"}]}`. Each finding is
`{"id": "V<n>", "path": "<json pointer>", "message": "..."}`. Every check of lane contract
section 8 runs when what it needs was supplied (the input for cardinality, slices, grants, and
the run-block rule; the run directory for the receipt, the checkpoint, the retained report, and
artifact containment; the workspace for the ledger, the cards, and the round trip); a check that
needs something not supplied reports "skipped: needs input" / "needs run directory" / "needs
workspace" and nothing else is ever skipped (the one other skip, V13's legacy report without a
structured tail, applies only to a call record that carries no raw_sha256, E8-A26).

After Astra's review (section 12 of the lane contract): every validator carries jsonschema's
FormatChecker (E8-A34); V3 tests resolved containment and the run directory's inventory (E8-A19,
E8-A31); V7 and V14 recompute each grant's channel verdict with the core's own rule (E8-A24); V8
holds the receipt's entries to the state they prove and fully-done targets to their resting hash
(E8-A21); V12 admits a card moved before the violation was found only against boundary.json's
before_step (E8-A44); V13 re-proves every complete call's retained report (E8-A26, E8-A40); V17
compares a written defect line's slice with charged_to_slice (E8-A25); V18 holds a refused resume
to a checkpoint that fails at the named step (E8-A33).
"""
import json
import os
import re
import sys

MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"

try:  # the guarded import: a missing jsonschema is reported once, at the first use
    from jsonschema import Draft202012Validator as _Validator, FormatChecker as _FormatChecker
except ImportError:  # pragma: no cover - exercised by the exit-3 tests through a subprocess
    _Validator = None
    _FormatChecker = None

SCHEMA_FILES = {
    "input": "input.schema.json",
    "result": "result.schema.json",
    "checkpoint": "checkpoint.schema.json",
    "receipt": "receipt.schema.json",
}
SEP = " · "
RECORD_KINDS = ("reopened_line", "punch_list_block", "waived_line", "verdict_doc_copy", "status_line")
MOVED_BEFORE_VIOLATION = "moved before the violation was found"  # E8-A44: the card reason the core writes
CHECK_IDS = ["V%d" % i for i in range(1, 19)]


class ReferenceUnavailable(RuntimeError):
    """A schema under the skill root is missing, unreadable, or not a schema (pilot contract section 15)."""

    def __init__(self, relative_path, cause):
        RuntimeError.__init__(self, "reference unavailable: %s (%s)" % (relative_path, cause))
        self.relative_path = relative_path


class SkillRootMissing(ValueError):
    """An explicit --skill-root that is not a directory: a usage error (exit 2), never exit 1."""


def jsonschema_unavailable() -> bool:
    """True when jsonschema did not import, or the gated test hook says to act as if it had not."""
    hooked = os.environ.get("RECHECK_TEST") == "1" and os.environ.get("RECHECK_TEST_NO_JSONSCHEMA") == "1"
    return _Validator is None or hooked


def require_jsonschema():
    """Return the Draft 2020-12 validator class, or exit 3 with the contract's message."""
    if jsonschema_unavailable():
        sys.stderr.write(MISSING_DEPENDENCY + "\n")
        sys.stderr.flush()
        sys.exit(3)
    return _Validator


def skill_root(explicit=None) -> str:
    """The directory holding SKILL.md: given explicitly, else two levels above this file. An
    explicit root that is not a directory raises SkillRootMissing (a usage error, exit 2)."""
    if explicit:
        path = os.path.abspath(explicit)
        if not os.path.isdir(path):
            raise SkillRootMissing("--skill-root is not a directory: %s" % path)
        return path
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def references_dir(root=None) -> str:
    return os.path.join(skill_root(root), "references")


def _read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


class Schemas:
    """The four schema documents and their validators, loaded from one skill root."""

    def __init__(self, root=None):
        V = require_jsonschema()
        self.root = skill_root(root)
        self.docs = {}
        for key, name in SCHEMA_FILES.items():
            rel = os.path.join("references", name)
            path = os.path.join(self.root, rel)
            try:
                self.docs[key] = _read_json(path)
            except (OSError, ValueError) as exc:
                raise ReferenceUnavailable(rel, exc)
            try:
                V.check_schema(self.docs[key])
            except Exception as exc:  # noqa: BLE001 - a file that parses but is not a schema is the same stop
                raise ReferenceUnavailable(rel, "not a valid schema: %s" % exc)
        # E8-A34: every validator carries jsonschema's FormatChecker, so `format: date` rejects a
        # non-calendar date (2026-99-99, 2026-02-30); in 4.25.1 the date checker is datetime.date.fromisoformat,
        # stdlib only (date-time stays unchecked without rfc3339-validator, as before)
        fc = format_checker()
        self.input = V(self.docs["input"], format_checker=fc)
        self.result = V(self.docs["result"], format_checker=fc)
        self.checkpoint = V(self.docs["checkpoint"], format_checker=fc)
        self.receipt = V(self.docs["receipt"], format_checker=fc)
        # the result schema's item definition on its own (section 11 step 4)
        self.item = V({"$schema": self.docs["result"]["$schema"], "$defs": self.docs["result"]["$defs"],
                       "$ref": "#/$defs/item_result"}, format_checker=fc)


def format_checker():
    """A fresh jsonschema FormatChecker (E8-A34); require_jsonschema() has run by the time it is called."""
    return _FormatChecker()


_CACHE = {}


def load_schemas(root=None) -> Schemas:
    key = skill_root(root)
    if key not in _CACHE:
        _CACHE[key] = Schemas(key)
    return _CACHE[key]


def _pointer(path_parts) -> str:
    return "/" + "/".join(str(p) for p in path_parts) if path_parts else ""


def _walk(doc, parts):
    cur = doc
    for p in parts:
        cur = cur[p]
    return cur


def _error_path(err, doc):
    """The instance path of an error, with the segment jsonschema drops for a `false` schema restored.

    jsonschema 4.25.1's `descend()` yields the error for a `false` subschema before it appends the
    property name (or item index) to the error's path, so a rule such as `"source_identity": false`
    reports at the parent, and the schema path is cut the same way. The offending value is the
    error's instance object; find it in its parent by identity and append its key. An ambiguous
    match (two keys holding the same object) leaves the parent path as jsonschema gave it."""
    parts = list(err.absolute_path)
    if not (err.validator is None and err.schema is False):
        return parts
    try:
        parent = _walk(doc, parts)
    except (KeyError, IndexError, TypeError):
        return parts
    if isinstance(parent, dict):
        hits = [k for k, v in parent.items() if v is err.instance]
    elif isinstance(parent, list):
        hits = [i for i, v in enumerate(parent) if v is err.instance]
    else:
        hits = []
    if len(hits) == 1:
        parts.append(hits[0])
    return parts


def _errors(validator, doc):
    out = [{"path": _pointer(_error_path(err, doc)), "message": err.message} for err in validator.iter_errors(doc)]
    out.sort(key=lambda e: (e["path"], e["message"]))
    return out


def validate_input(doc, schemas=None):
    return _errors((schemas or load_schemas()).input, doc)


def validate_result(doc, schemas=None):
    return _errors((schemas or load_schemas()).result, doc)


def validate_checkpoint(doc, schemas=None):
    return _errors((schemas or load_schemas()).checkpoint, doc)


def validate_receipt(doc, schemas=None):
    return _errors((schemas or load_schemas()).receipt, doc)


def validate_item_result(doc, schemas=None):
    return _errors((schemas or load_schemas()).item, doc)


# ---- semantic checks (lane contract section 8) -------------------------------------------------

def _f(check_id, path, message):
    return {"id": check_id, "path": path, "message": message}


def _loc(item):
    loc = item.get("location") or {}
    return "%s:%s" % (loc.get("file"), loc.get("line"))


def _key(entry):
    return (_loc(entry), entry.get("claim"))


def effective_open_set(result):
    """Section 4: the not_fixed items without a waived marker, plus every new defect.

    Returns (open_items, open_defects) as lists of (index, entry)."""
    items = [(i, it) for i, it in enumerate(result.get("items") or [])
             if it.get("disposition") == "not_fixed" and "waived" not in it]
    defects = list(enumerate(result.get("new_defects") or []))
    return items, defects


def expected_result_value(result):
    """Section 4 over the effective open set, with the boundary override."""
    if result.get("boundary_violations"):
        return "not_clear"
    open_items, open_defects = effective_open_set(result)
    if not open_items and not open_defects:
        return "all_clear"
    if any(it.get("disposition") == "fixed" for it in result.get("items") or []):
        return "partial"
    return "not_clear"


def check_v1(result, ctx):
    """Items correspond one-to-one to the checklist entries."""
    findings, skip = [], None
    items = result.get("items")
    checklist = result.get("checklist")
    if items is None:
        return findings, None
    if checklist is not None and checklist.get("count") != len(items):
        findings.append(_f("V1", "/checklist/count", "checklist.count is %r but the result carries %d items"
                           % (checklist.get("count"), len(items))))
    keys = [_key(it) for it in items]
    if len(set(keys)) != len(keys):
        # the key is a (location, claim) tuple: wrap it so % formats one value instead of unpacking it
        findings.append(_f("V1", "/items", "two items share a location and claim: %r"
                           % ([k for k in keys if keys.count(k) > 1][0],)))
    inp = ctx.get("input")
    target = (inp or {}).get("target") or {}
    if inp is not None and isinstance(target.get("items"), list):
        want = [_key(it) for it in target["items"]]
        if keys != want:
            findings.append(_f("V1", "/items", "items do not match the input's explicit items in order: result %r, input %r"
                               % (keys, want)))
    else:
        skip = _needs_skip(ctx, "run_dir", "checkpoint scope for the key order")
    return findings, skip


def check_v2(result, ctx):
    """Every item and new defect carries a slice that exists in the input, or `none`.

    Slice 1 (amendment E8-A5) implements the workspace-free part for an explicit-items input:
    each result item's slice equals the slice of the input item with the same location and
    claim, and every new_defects[].charged_to_slice is one of those slices or `none`. A build_doc
    input needs the workspace (the document's slices) and is slice 2's; an item the input does
    not carry is V1's finding, not this check's."""
    inp = ctx.get("input")
    if inp is None:
        return [], "skipped: needs input"
    target = inp.get("target") or {}
    if not isinstance(target.get("items"), list):
        return [], _needs_skip(ctx, "workspace", "build doc and its slices")
    findings = []
    slice_of = {}
    for entry in target["items"]:
        slice_of.setdefault(_key(entry), entry.get("slice"))
    for i, it in enumerate(result.get("items") or []):
        want = slice_of.get(_key(it))
        if want is not None and it.get("slice") != want:
            findings.append(_f("V2", "/items/%d/slice" % i, "slice %r but the input item with the same location and claim carries %r"
                               % (it.get("slice"), want)))
    allowed = sorted(set(slice_of.values()) | {"none"})
    for i, d in enumerate(result.get("new_defects") or []):
        if d.get("charged_to_slice") not in allowed:
            findings.append(_f("V2", "/new_defects/%d/charged_to_slice" % i, "charged_to_slice %r is not one of the input's slices %r"
                               % (d.get("charged_to_slice"), allowed)))
    return findings, None


def check_v5(result, ctx):
    """still_open equals the effective open set, one line each."""
    findings = []
    if result.get("status") != "completed":
        return findings, None
    lines = result.get("still_open") or []
    open_items, open_defects = effective_open_set(result)
    expected = []
    for i, it in open_items:
        expected.append(("/items/%d" % i, it.get("severity"), _loc(it), [it.get("claim")]))
    for i, d in open_defects:
        expected.append(("/new_defects/%d" % i, d.get("severity"), _loc(d), [d.get("claim"), "broke: %s" % d.get("claim")]))
    used = [False] * len(lines)
    for path, severity, loc, claims in expected:
        hit = None
        for n, line in enumerate(lines):
            if used[n]:
                continue
            fields = line.split(SEP)
            if len(fields) >= 3 and fields[0] == severity and fields[1] == loc and fields[2] in claims:
                hit = n
                break
        if hit is None:
            findings.append(_f("V5", path, "open entry %s %s has no still_open line" % (severity, loc)))
        else:
            used[hit] = True
    for n, line in enumerate(lines):
        if not used[n]:
            findings.append(_f("V5", "/still_open/%d" % n, "still_open line matches no entry of the effective open set: %r" % line))
    return findings, None


def check_v9(result, ctx):
    """Disposition agrees with adjudication (section 7 pairs); upgraded never under session_wrote_fix."""
    findings = []
    run_wrote = (result.get("run") or {}).get("session_wrote_fix")
    for i, it in enumerate(result.get("items") or []):
        adj = it.get("adjudication") or {}
        said, action = adj.get("verifier_said"), adj.get("driver_action")
        disp = it.get("disposition")
        path = "/items/%d/adjudication" % i
        ok = {
            "fixed": [("fixed", "confirmed"), ("not_fixed", "upgraded")],
            "not_fixed": [("not_fixed", "confirmed"), ("not_fixed", "disputed"), ("fixed", "downgraded")],
        }.get(disp, [])
        if (said, action) not in ok:
            findings.append(_f("V9", path, "disposition %r with verifier_said %r and driver_action %r is not a section 7 pair"
                               % (disp, said, action)))
        if action == "upgraded":
            if adj.get("session_wrote_fix") is True or run_wrote is True:
                findings.append(_f("V9", path, "upgraded while the session wrote the fix (E8-13: recorded as disputed, item stays open)"))
            if not adj.get("upgrade_evidence"):
                findings.append(_f("V9", path, "upgraded without upgrade_evidence"))
        if run_wrote is not None and "session_wrote_fix" in adj and adj["session_wrote_fix"] != run_wrote:
            findings.append(_f("V9", path + "/session_wrote_fix", "disagrees with run.session_wrote_fix (%r)" % run_wrote))
    return findings, None


def check_v10(result, ctx):
    """`result` follows section 4 from the effective open set; violations force not_clear."""
    findings = []
    if "result" not in result:
        if result.get("status") == "completed":
            findings.append(_f("V10", "/result", "a completed run carries no result value"))
        return findings, None
    want = expected_result_value(result)
    if result["result"] != want:
        findings.append(_f("V10", "/result", "result is %r but section 4 over the effective open set gives %r"
                           % (result["result"], want)))
    return findings, None


def check_v11(result, ctx):
    """A fixed item carries no block and no missing field, and observes what it must (S2)."""
    from . import verifier
    findings = []
    for i, it in enumerate(result.get("items") or []):
        if it.get("disposition") != "fixed":
            continue
        ver = it.get("verification") or {}
        for field in ("blocked", "missing"):
            if field in ver:
                findings.append(_f("V11", "/items/%d/verification/%s" % (i, field), "a fixed item carries %s" % field))
        if "reason" in it:
            findings.append(_f("V11", "/items/%d/reason" % i, "a fixed item carries a reason"))
        # E11-45 S2: an item the INPUT declares needs a service observation is never `fixed`
        # without one bound to it. The declaration is read from the input; without an input
        # document the rule cannot be checked and the check says so rather than passing it.
        required = _required_observation(it, ctx.get("input"))
        if required is None:
            continue
        if verifier.bound_service_observation(it.get("verification"), required["service"]) is None:
            findings.append(_f("V11", "/items/%d" % i,
                               "fixed, but the item requires an observation of %s (%s) and the "
                               "record carries no executed command whose retained output "
                               "observes it" % (required["service"],
                                                required.get("observe") or "the named state")))
    if ctx.get("input") is None:
        return findings, "skipped: needs the input document for the service-observation rule"
    return findings, None


def _required_observation(item_result, input_doc):
    """The service observation the input declares for this result item, or None (E11-45 S2)."""
    if not isinstance(input_doc, dict):
        return None
    loc = item_result.get("location") or {}
    for row in input_doc.get("required_service_observations") or []:
        if not isinstance(row, dict):
            continue
        where = row.get("location") or {}
        if where.get("file") == loc.get("file") and where.get("line") == loc.get("line"):
            if row.get("claim") is not None and row.get("claim") != item_result.get("claim"):
                continue
            return row
    target = (input_doc.get("target") or {})
    for row in target.get("items") or []:
        if not isinstance(row, dict):
            continue
        where = row.get("location") or {}
        declared = row.get("required_service_observation")
        if isinstance(declared, dict) and where.get("file") == loc.get("file") \
                and where.get("line") == loc.get("line"):
            return declared
    return None


def _moved_before(result):
    """[(index, card)] of the cards listed as moved before the violation was found (E8-A44), in order."""
    return [(i, c) for i, c in enumerate(result.get("cards") or []) if c.get("before") != c.get("after") and c.get("reason") == MOVED_BEFORE_VIOLATION]


def check_v12(result, ctx):
    """A run with boundary violations changed no card and cancelled its status-line steps.

    E8-A44: the one exception is a card whose status-line step was receipted done before the violation
    was found, listed with the reason `moved before the violation was found`. The result-only part runs
    here: any other moved card is a finding, a status line written beyond those cards is a finding, and
    the result must be not_clear. check_v12_full holds the exception to boundary.json's before_step and
    the receipt when the run directory is supplied."""
    findings = []
    if not result.get("boundary_violations"):
        return findings, None
    moved_before = _moved_before(result)
    for i, card in enumerate(result.get("cards") or []):
        if card.get("before") != card.get("after") and card.get("reason") != MOVED_BEFORE_VIOLATION:
            findings.append(_f("V12", "/cards/%d" % i, "card moved from %r to %r beside a boundary violation"
                               % (card.get("before"), card.get("after"))))
    status_writes = [i for i, w in enumerate(result.get("records_written") or []) if w.get("kind") == "status_line"]
    for n, i in enumerate(status_writes):
        if n >= len(moved_before):
            findings.append(_f("V12", "/records_written/%d" % i, "a status line was written beside a boundary violation"))
    if result.get("result") not in (None, "not_clear"):
        findings.append(_f("V12", "/result", "boundary violations force not_clear, found %r" % result.get("result")))
    return findings, None


def check_v15(result, ctx):
    """Status rules for the write list."""
    findings = []
    status = result.get("status")
    writes = result.get("records_written")
    if "run" not in result and writes:
        findings.append(_f("V15", "/records_written", "a status that never reached a run directory lists writes"))
    if status not in ("completed", "recording_failed"):
        for i, w in enumerate(writes or []):
            if w.get("kind") in RECORD_KINDS:
                findings.append(_f("V15", "/records_written/%d" % i, "status %r lists a project-record write (%s)"
                                   % (status, w.get("kind"))))
    return findings, None


def check_v16(result, ctx):
    """The run block is present exactly when the input validates (E8-6)."""
    if "input" not in ctx:
        return [], "skipped: needs input"
    errors = ctx.get("input_errors")
    if errors is None:
        errors = validate_input(ctx["input"], ctx.get("schemas"))
    valid = not errors
    has_run = "run" in result
    if valid != has_run:
        return [_f("V16", "/run", "run block %s but the input %s the schema"
                   % ("present" if has_run else "absent", "validates against" if valid else "fails"))], None
    return [], None


NEEDS_NAME = {"run_dir": "run directory", "workspace": "workspace", "input": "input",
              "records": "the records component"}


def _skip(what):
    return "skipped: needs %s" % NEEDS_NAME[what]


def _needs_skip(ctx, what_supplied, what=None):
    """The skip reason when the thing a check needs was not supplied (only then)."""
    return _skip(what_supplied)


def _run_dir(result, ctx):
    return ctx.get("run_dir") or (result.get("run") or {}).get("run_dir")


def _read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def _under(path, root):
    rp, rr = os.path.realpath(path), os.path.realpath(root)
    return rp == rr or rp.startswith(rr.rstrip(os.sep) + os.sep)


def _item_key(entry):
    return (entry["location"]["file"], entry["location"]["line"], entry["claim"])


def _grant_named_rejected(result, path):
    """True when rejected_grants lists the grant object at this JSON path in the input (E8-A12:
    an entry reads `<path>: <file:line> · <why>`; a location alone never identifies a grant)."""
    prefix = path + ":"
    return any(r.startswith(prefix) for r in result.get("rejected_grants") or [])


OTHER_REASONS = ("no entry", "matched no", "conflict", "already used")  # a rejection the channel rule does not decide


def _rejected_why(result, path):
    """The `why` field of the rejected_grants entry listed under this JSON path (E8-A12 shape), or None."""
    prefix = path + ":"
    for r in result.get("rejected_grants") or []:
        if r.startswith(prefix):
            return r.split(SEP)[-1] if SEP in r else r[len(prefix):].strip()
    return None


def _other_reason(why):
    return why is not None and any(w in why for w in OTHER_REASONS)


def grant_verdicts(result, inp):
    """E8-A24: every grant object of the input with the channel rule's own verdict, recomputed here with
    inputs.grant_channel_ok (continuation_grant_ok for extra_continuation) from the input's turn_attribution
    and route rules. Returns [{path, kind, grant, ok, why, named, listed_why}] where `named` says whether
    rejected_grants lists the grant under its JSON path and `listed_why` is that entry's reason."""
    from . import inputs
    auth = (inp or {}).get("authorization") or {}
    out = []
    for key, kind in (("waivers", "waived"), ("reopen", "reopened")):
        for i, g in enumerate(auth.get(key) or []):
            path = "authorization.%s[%d]" % (key, i)
            ok, why = inputs.grant_channel_ok(g, inp)
            out.append({"path": path, "kind": kind, "grant": g, "ok": ok, "why": why,
                        "named": _grant_named_rejected(result, path), "listed_why": _rejected_why(result, path)})
    present, ok, why = inputs.continuation_grant_ok(inp)
    if present:
        path = "authorization.extra_continuation"
        out.append({"path": path, "kind": "continuation", "grant": auth.get("extra_continuation"), "ok": ok, "why": why,
                    "named": _grant_named_rejected(result, path), "listed_why": _rejected_why(result, path)})
    return out


def _accepted_grants(result, inp):
    """The grants that count (E8-A24): the channel rule accepts them (the result's own rejected_grants is
    never the proof) and rejected_grants does not list them for another reason (no entry, a conflict)."""
    waivers, reopenings = [], []
    for v in grant_verdicts(result, inp):
        if v["kind"] == "continuation" or not v["ok"]:
            continue
        if v["named"] and _other_reason(v["listed_why"]):
            continue
        (waivers if v["kind"] == "waived" else reopenings).append(v["grant"])
    return waivers, reopenings


def _marker_matches(item, marker, g):
    """The item's marker derives from grant g: same item (location and claim, or location alone for a
    claim-less entry) and the grant's date and words in the ledger form (E8-A16)."""
    from . import ledger
    same = _item_key(g["item"]) == _item_key(item) or (item["claim"] == "()" and (g["item"]["location"]["file"], g["item"]["location"]["line"]) == (item["location"]["file"], item["location"]["line"]))
    return same and g.get("date") == marker.get("date") and ledger.ledger_words(g.get("quoted_words") or "") == marker.get("quoted_words")


def _build_doc(result, ctx):
    inp = ctx.get("input") or {}
    target = inp.get("target") or {}
    if target.get("build_doc"):
        return target["build_doc"]
    return (result.get("checklist") or {}).get("build_doc")


def check_v2_workspace(result, ctx, findings):
    """The rest of V2 (needs the workspace): every item's slice has a `## Slice <name>` heading in
    its document, or is `none`; every new defect's charged_to_slice likewise in the checklist's
    document. The document is result.checklist.build_doc (the input's target.build_doc when it
    has one), or, for an item, its own record.document (E8-A16: explicit items included)."""
    from . import ledger
    items = result.get("items") or []
    defects = result.get("new_defects") or []
    if not (items or defects):
        return
    main_doc = _build_doc(result, ctx)
    cache = {}

    def names_of(doc_rel, path):
        if doc_rel in cache:
            return cache[doc_rel]
        full = os.path.join(ctx["workspace"], doc_rel) if doc_rel else None
        if not full or not os.path.isfile(full):
            findings.append(_f("V2", path, "the document %r does not exist under the workspace" % doc_rel))
            cache[doc_rel] = None
            return None
        with open(full, "r", encoding="utf-8") as fh:
            parsed = ledger.parse_document(fh.read(), doc_rel)
        cache[doc_rel] = set(ledger.slice_names(parsed)) | {"none"}
        return cache[doc_rel]

    for i, it in enumerate(items):
        doc_rel = (it.get("record") or {}).get("document") or main_doc
        names = names_of(doc_rel, "/checklist/build_doc" if doc_rel == main_doc else "/items/%d/record/document" % i)
        if names is not None and it.get("slice") not in names:
            findings.append(_f("V2", "/items/%d/slice" % i, "slice %r has no heading in %s" % (it.get("slice"), doc_rel)))
    for i, d in enumerate(defects):
        names = names_of(main_doc, "/checklist/build_doc")
        if names is not None and d.get("charged_to_slice") not in names:
            findings.append(_f("V2", "/new_defects/%d/charged_to_slice" % i, "charged_to_slice %r has no heading in %s" % (d.get("charged_to_slice"), main_doc)))


def check_v2_full(result, ctx):
    findings, skip = check_v2(result, ctx)
    if ctx.get("workspace") is not None:
        # the workspace part runs whenever a workspace is supplied, explicit items included (E8-A16)
        if skip == "skipped: needs workspace":
            skip = None
        check_v2_workspace(result, ctx, findings)
    return findings, skip


def check_v1_full(result, ctx):
    findings, skip = check_v1(result, ctx)
    if skip and ctx.get("run_dir") is not None:
        skip = None
        path = os.path.join(ctx["run_dir"], "checkpoint.json")
        if os.path.isfile(path):
            try:
                cp = _read_json(path)
                want = [_key(it) for it in cp["scope"]["checklist"]]
                got = [_key(it) for it in result.get("items") or []]
                if got and got != want:
                    findings.append(_f("V1", "/items", "items do not match the checkpoint scope in order: result %r, checkpoint %r" % (got, want)))
            except (OSError, ValueError, KeyError) as exc:
                findings.append(_f("V1", "/items", "the checkpoint scope cannot be read: %s" % exc))
        elif result.get("items"):
            findings.append(_f("V1", "/items", "the run directory holds no checkpoint.json to check the key order against"))
    return findings, skip


def check_v3(result, ctx):
    """Every record write targets an authorized destination; the list is in write order.

    E8-A19: with the workspace, every project-record path must resolve (realpath, symlinks followed)
    inside the workspace's real path, not only be relative and existing. E8-A31: with the run
    directory supplied, every regular file under it (recursively) appears in the write list exactly
    once and every listed run artifact exists under it; a file present but unlisted, a path listed
    twice, and a listed artifact that does not exist are findings. The inventory runs only for a
    result that lists writes: a status that never reached the run directory lists nothing (section 9,
    E8-A42; a refused resume's envelope beside its untouched run directory is the case), and V15
    holds that list empty."""
    run_dir = _run_dir(result, ctx)
    if run_dir is None:
        return [], _skip("run_dir")
    findings = []
    writes = result.get("records_written") or []
    workspace = ctx.get("workspace")
    seen_record, seen_result = False, False
    listed = {}
    for i, w in enumerate(writes):
        path, kind = w.get("path", ""), w.get("kind")
        if kind == "run_artifact":
            if not os.path.isabs(path) or not _under(path, run_dir):
                findings.append(_f("V3", "/records_written/%d/path" % i, "run artifact %r is not under run_dir %s" % (path, run_dir)))
            base = os.path.basename(path)
            if base in ("result.json", "chat.md") and os.path.dirname(os.path.realpath(path)) == os.path.realpath(run_dir):
                seen_result = True
            elif seen_result:
                findings.append(_f("V3", "/records_written/%d" % i, "a run artifact is listed after result.json"))
            elif seen_record:
                findings.append(_f("V3", "/records_written/%d" % i, "a run artifact is listed after a project-record write (E8-29 order)"))
            real = os.path.realpath(path) if os.path.isabs(path) else path
            if real in listed:
                findings.append(_f("V3", "/records_written/%d" % i, "run artifact %r is listed twice (first at /records_written/%d)" % (path, listed[real])))
            else:
                listed[real] = i
        elif kind in RECORD_KINDS:
            if os.path.isabs(path) or any(seg == ".." for seg in path.split("/")):
                findings.append(_f("V3", "/records_written/%d/path" % i, "project record %r is not a workspace-relative path" % path))
            elif workspace is not None:
                full = os.path.join(workspace, path)
                if not _under(full, workspace):
                    findings.append(_f("V3", "/records_written/%d/path" % i, "project record %r resolves outside the workspace's real path (E8-A19)" % path))
                elif not os.path.isfile(full):
                    findings.append(_f("V3", "/records_written/%d/path" % i, "project record %r does not exist under the workspace" % path))
            if kind == "verdict_doc_copy" and not path.startswith("docs/reviews/"):
                findings.append(_f("V3", "/records_written/%d/path" % i, "a verdict-doc copy outside docs/reviews/"))
            if seen_result:
                findings.append(_f("V3", "/records_written/%d" % i, "a project record is listed after result.json"))
            seen_record = True
    if ctx.get("run_dir") is not None and writes:
        # E8-A31: the inventory of the supplied run directory against the listed run artifacts. result.json and
        # chat.md are listed at their first write, which follows this validation (result.deliver validates the
        # assembled result before writing either), so their absence is not a finding.
        deferred = {os.path.realpath(os.path.join(ctx["run_dir"], n)) for n in ("result.json", "chat.md")}
        for i, w in enumerate(writes):
            path = w.get("path", "")
            if w.get("kind") == "run_artifact" and os.path.isabs(path) and not os.path.isfile(path) and os.path.realpath(path) not in deferred:
                findings.append(_f("V3", "/records_written/%d/path" % i, "run artifact %r does not exist under run_dir" % path))
        present = []
        for root, dirs, files in os.walk(ctx["run_dir"]):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(root, name)
                if os.path.isfile(full):
                    present.append(full)
        for full in present:
            if os.path.realpath(full) not in listed:
                findings.append(_f("V3", "/records_written", "%s is under run_dir but not in the write list (E8-A31: every file once)" % full))
    return findings, None


def check_v4(result, ctx):
    """Every artifact path the result names is in the write list and under run_dir."""
    run_dir = _run_dir(result, ctx)
    if run_dir is None:
        return [], _skip("run_dir")
    findings = []
    listed = set(w.get("path") for w in result.get("records_written") or [] if w.get("kind") == "run_artifact")
    named = []
    ver = (result.get("run") or {}).get("verifier") or {}
    if ver.get("raw_path"):
        named.append(("/run/verifier/raw_path", ver["raw_path"]))
    for i, c in enumerate(ver.get("calls") or []):
        if c.get("raw_path"):
            named.append(("/run/verifier/calls/%d/raw_path" % i, c["raw_path"]))
    if result.get("receipt_path"):
        named.append(("/receipt_path", result["receipt_path"]))
    for i, it in enumerate(result.get("items") or []):
        for n, e in enumerate((it.get("verification") or {}).get("evidence") or []):
            if e.get("artifact_path"):
                named.append(("/items/%d/verification/evidence/%d/artifact_path" % (i, n), e["artifact_path"]))
    for path, value in named:
        if not _under(value, run_dir):
            findings.append(_f("V4", path, "%r is not under run_dir %s" % (value, run_dir)))
        if value not in listed:
            findings.append(_f("V4", path, "%r is not in the write list" % value))
    return findings, None


def _state_of(ctx, doc_rel, check_id, path):
    """`records.py state` for one ledger document, or a finding naming why it could not be read."""
    from . import records_client as rcl
    client = ctx.get("records")
    try:
        return client.state(ctx["workspace"], doc_rel), None
    except rcl.RecordsRefusal as refusal:
        return None, _f(check_id, path, "the records component refused `state` for %s: %s"
                        % (doc_rel, refusal.sentence()))


def check_v6(result, ctx):
    """The card mapping reproduces each after value over the slice's open set now (E8-4).

    E13 slice 1, send-back 1: the open set and the card the slice currently carries come from
    `records.py state`, never from a re-parse of the document's records. The MAPPING stays the
    core's own `card_after`, which is a decision and therefore does not move (ruling E13-1);
    `tests/test_validator_records.py::CardMappingAgreement` pins every movable card value and every
    open-set shape on which it and the component's `card_derived` agree, and the one place they are
    designed to differ (a card the skill may not move). `card_observed` is what the run's `card_set`
    event recorded, so a card the result claims that nothing set is caught here; that the FILE holds
    what the run wrote is V8's resting-hash check and V17's.
    """
    if ctx.get("workspace") is None:
        return [], _skip("workspace")
    if result.get("status") != "completed":
        return [], None
    if ctx.get("records") is None:
        return [], _skip("records")
    from . import ledger
    findings = []
    doc_rel = _build_doc(result, ctx)
    if not doc_rel:
        return [_f("V6", "/cards", "the result names no build doc, so the cards cannot be checked")], None
    state, refusal = _state_of(ctx, doc_rel, "V6", "/cards")
    if refusal is not None:
        return [refusal], None
    open_by_slice = {}
    for finding in state.get("findings") or []:
        if finding.get("status") == "open":
            open_by_slice.setdefault(finding.get("slice"), []).append(finding)
    observed = {row["name"]: row.get("card_observed") for row in state.get("slices") or []}
    want_slices = ledger.sort_slices(it["slice"] for it in result.get("items") or [] if it.get("slice") != "none")
    got_slices = [c["slice"] for c in result.get("cards") or []]
    if got_slices != want_slices:
        findings.append(_f("V6", "/cards", "cards list slices %r; the checklist's slices are %r" % (got_slices, want_slices)))
    violated = bool(result.get("boundary_violations"))
    for i, c in enumerate(result.get("cards") or []):
        open_here = open_by_slice.get(c["slice"]) or []
        mapped = ledger.card_after(c["before"], open_here)
        current = observed.get(c["slice"]) or "none"
        if violated and c["after"] == c["before"]:
            pass  # frozen beside the violation: the mapping does not apply (V12 holds the cards)
        elif violated and c.get("reason") != MOVED_BEFORE_VIOLATION:
            pass  # any other card moved beside a violation is V12's finding (E8-A44)
        elif c["after"] != mapped:
            # E8-A44: a card that moved before the violation was found moved by the mapping, so it is held to it
            findings.append(_f("V6", "/cards/%d/after" % i, "after is %r; the mapping over the slice's open set gives %r" % (c["after"], mapped)))
        if c["after"] != current and c["before"] in ledger.MOVABLE_CARDS:
            findings.append(_f("V6", "/cards/%d/after" % i, "after is %r but the last card the log records for the slice is %r" % (c["after"], current)))
    return findings, None


def check_v7(result, ctx):
    """Markers correspond to accepted grants and to waived_line / reopened_line writes.

    E8-A24: "accepted" is the channel rule's own verdict recomputed from the input (grant_verdicts), never
    the result's rejected_grants; a marker that derives from a grant the rule rejects, and a waiver or
    reopening line beyond the accepted count (a line a rejected grant would have produced), are findings."""
    if "input" not in ctx:
        return [], _skip("input")
    from . import ledger
    findings = []
    waivers, reopenings = _accepted_grants(result, ctx["input"])
    rejected = [v for v in grant_verdicts(result, ctx["input"]) if not v["ok"] and v["kind"] != "continuation"]
    writes = result.get("records_written") or []
    n_waived = len([w for w in writes if w.get("kind") == "waived_line"])
    n_reopened = len([w for w in writes if w.get("kind") == "reopened_line"])
    if result.get("status") == "completed":
        if n_waived != len(waivers):
            findings.append(_f("V7", "/records_written", "%d waived_line writes for %d accepted waivers (the channel rule's verdict, E8-A24)" % (n_waived, len(waivers))))
        if n_reopened != len(reopenings):
            findings.append(_f("V7", "/records_written", "%d reopened_line writes for %d accepted reopenings (the channel rule's verdict, E8-A24)" % (n_reopened, len(reopenings))))
    for i, it in enumerate(result.get("items") or []):
        for marker, grants in (("waived", waivers), ("reopened", reopenings)):
            if marker not in it:
                continue
            m = it[marker]
            derived = [v for v in rejected if v["kind"] == marker and _marker_matches(it, m, v["grant"])]
            if derived:
                findings.append(_f("V7", "/items/%d/%s" % (i, marker), "the %s marker derives from %s, a grant the channel rule rejects (%s)" % (marker, derived[0]["path"], derived[0]["why"])))
                continue
            match = [g for g in grants if _item_key(g["item"]) == _item_key(it) or (it["claim"] == "()" and (g["item"]["location"]["file"], g["item"]["location"]["line"]) == (it["location"]["file"], it["location"]["line"]))]
            if not match:
                findings.append(_f("V7", "/items/%d/%s" % (i, marker), "no accepted %s grant in the input names this item" % marker))
            elif not any(g["date"] == m.get("date") and ledger.ledger_words(g["quoted_words"]) == m.get("quoted_words") for g in match):
                findings.append(_f("V7", "/items/%d/%s" % (i, marker), "the marker's date or words (in the ledger form, E8-A16) differ from the grant's"))
            if result.get("status") == "completed" and (n_waived if marker == "waived" else n_reopened) == 0:
                findings.append(_f("V7", "/items/%d/%s" % (i, marker), "a %s marker without a %s_line write" % (marker, marker)))
    return findings, None


def check_v8(result, ctx):
    """The receipt's plan and entries match the write list; its integrity holds against receipt.log."""
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    if result.get("status") not in ("completed", "recording_failed"):
        return [], None
    from . import checkpoint as cpmod
    findings = []
    run_dir = ctx["run_dir"]
    path, log = os.path.join(run_dir, "receipt.json"), os.path.join(run_dir, "receipt.log")
    if not os.path.isfile(path) or not os.path.isfile(log):
        return [_f("V8", "/receipt_path", "receipt.json or receipt.log is missing from %s" % run_dir)], None
    try:
        rc = _read_json(path)
        rows = cpmod.read_log(log)
    except (OSError, ValueError, cpmod.CheckpointError) as exc:
        return [_f("V8", "/receipt_path", "the receipt cannot be read: %s" % exc)], None
    if validate_receipt(rc, ctx.get("schemas")):
        findings.append(_f("V8", "/receipt_path", "receipt.json fails its schema"))
    v = cpmod.verify_integrity(rc, rows, "receipt")
    if not v["ok"]:
        findings.append(_f("V8", "/receipt_path", v["reason"]))
    if rc.get("run_id") != (result.get("run") or {}).get("run_id"):
        findings.append(_f("V8", "/receipt_path", "the receipt's run id is not the result's"))
    plan, entries = rc.get("plan") or [], rc.get("entries") or []
    # E8-A21: the receipt proves the state (the same relationships the resume's step 5 requires): entries in
    # step order, each intent before its done, at most one done per step, every done entry's observed hash
    # equal to its step's planned after-hash; the finding names the entry
    from . import receipt as rcmod
    corrupt = rcmod.check_entries(plan, entries)
    if corrupt:
        findings.append(_f("V8", "/receipt_path", "the receipt's entries do not prove the state (E8-A21): " + corrupt))
    done = set(e["step"] for e in entries if e.get("type") == "done")
    landed = [s for s in plan if s["step"] in done and not s.get("cancelled")]
    writes = [w for w in result.get("records_written") or [] if w.get("kind") in RECORD_KINDS]
    want = [(s["kind"], s["target"]) for s in landed]
    got = [(w["kind"], w["path"]) for w in writes]
    if want != got:
        findings.append(_f("V8", "/records_written", "project-record writes %r do not match the receipt's done steps %r" % (got, want)))
    else:
        for i, (s, w) in enumerate(zip(landed, writes)):
            for key, plan_key in (("sha256_before", "before_sha256"), ("sha256_after", "after_sha256")):
                if key in w and w[key] != s[plan_key]:
                    findings.append(_f("V8", "/records_written/%d/%s" % (i, key), "differs from the receipt's %s" % plan_key))
    if result.get("status") == "completed" and rc.get("phase") != "committed":
        findings.append(_f("V8", "/receipt_path", "a completed run's receipt is not committed"))
    if ctx.get("workspace") is not None and not corrupt:
        # E8-A21 with the workspace: a target whose steps are all done rests at its last step's after-hash; a
        # recording_failed result that reports an outside edit is exempt for the target it names
        exempt = _outside_edit_target(result)
        per_target = {}
        for s in plan:
            if not s.get("cancelled"):
                per_target.setdefault(s["target"], []).append(s)
        for target, steps in per_target.items():
            if target == exempt or not all(s["step"] in done for s in steps):
                continue
            current = rcmod.sha(rcmod.file_text(os.path.join(ctx["workspace"], target)))
            if current != steps[-1]["after_sha256"]:
                findings.append(_f("V8", "/receipt_path", "%s: every step is done but the file rests at %s, not step %d's after-hash %s (E8-A21)"
                                   % (target, current[:12], steps[-1]["step"], steps[-1]["after_sha256"][:12])))
    return findings, None


OUTSIDE_EDIT = re.compile(r"step \d+ \((?:reopened_line|punch_list_block|waived_line|verdict_doc_copy|status_line), (.+?)\) (?:landed but the target now rests at|cannot be classified)")


def _outside_edit_target(result):
    """The target a recording_failed result's stop_reason names as an outside edit (the driver's wording), or None."""
    if result.get("status") != "recording_failed":
        return None
    m = OUTSIDE_EDIT.search(result.get("stop_reason") or "")
    return m.group(1) if m else None


def check_v12_full(result, ctx):
    findings, _ = check_v12(result, ctx)
    if not result.get("boundary_violations"):
        return findings, None
    if ctx.get("run_dir") is None:
        return findings, _skip("run_dir")
    path = os.path.join(ctx["run_dir"], "receipt.json")
    if not os.path.isfile(path):
        findings.append(_f("V12", "/receipt_path", "receipt.json is missing; the cancelled flags cannot be checked"))
        return findings, None
    try:
        rc = _read_json(path)
    except (OSError, ValueError) as exc:
        findings.append(_f("V12", "/receipt_path", "the receipt cannot be read: %s" % exc))
        return findings, None
    # E8-A44: boundary.json carries the step the violation was found before; a card is listed as moved only
    # when its status-line step is receipted done with a step number below it
    from . import receipt as rcmod
    try:
        bdoc = rcmod.read_boundary_doc(ctx["run_dir"])
    except (OSError, ValueError) as exc:
        findings.append(_f("V12", "/boundary_violations", "boundary.json cannot be read: %s" % exc))
        bdoc = None
    # no boundary.json (or no before_step in it): no status step may stand and no card may be listed as moved
    before_step = bdoc.get("before_step") if bdoc else None
    done = set(e.get("step") for e in rc.get("entries") or [] if e.get("type") == "done")
    status_steps = [s for s in rc.get("plan") or [] if s.get("kind") == "status_line"]
    # the status-line steps and the cards are both in ascending slice order (section 9, the cards description), so
    # the moved-before cards are matched to the live status steps in order; a seeded plan carries no value (E8-28),
    # and a step with one must set the card's after value
    claimed = set()
    for i, card in _moved_before(result):
        hit = None
        for s in status_steps:
            if s.get("step") in claimed or s.get("cancelled") is True:
                continue
            if s.get("value") in (None, card.get("after")):
                hit = s
                break
        if hit is None:
            findings.append(_f("V12", "/cards/%d" % i, "listed as moved before the violation was found, but the receipt holds no live status-line step setting %r" % card.get("after")))
            continue
        claimed.add(hit["step"])
        if hit["step"] not in done:
            findings.append(_f("V12", "/cards/%d" % i, "listed as moved before the violation was found, but status-line step %d is not receipted done" % hit["step"]))
        elif before_step is None or hit["step"] >= before_step:
            findings.append(_f("V12", "/cards/%d" % i, "listed as moved before the violation was found, but status-line step %d is not below boundary.json's before_step %r" % (hit["step"], before_step)))
    for s in status_steps:
        if s.get("cancelled") is True or s.get("step") in claimed:
            continue
        findings.append(_f("V12", "/receipt_path", "status-line step %d is not cancelled beside a boundary violation" % s.get("step")))
    return findings, None


NO_TAIL_SKIP = "skipped: the retained report carries no structured tail (a report written before E8-12)"


def _call_records(result, run_dir):
    """The verifier call records V13 holds (E8-A26): the checkpoint's verifier_calls when the run directory
    holds a readable checkpoint (each with the items it covered and, once retained, raw_path and raw_sha256),
    else the result's run.verifier.calls under the same keys, else the one raw_path as a single complete call.
    Each record is returned with the JSON pointer its finding names in the result."""
    ver = (result.get("run") or {}).get("verifier") or {}
    cp_path = os.path.join(run_dir, "checkpoint.json")
    if os.path.isfile(cp_path):
        try:
            calls = _read_json(cp_path).get("verifier_calls") or []
            if isinstance(calls, list):
                out = []
                for k, c in enumerate(calls):
                    pointer = "/run/verifier/calls/%d/raw_path" % k if k < len(ver.get("calls") or []) else "/run/verifier/raw_path"
                    out.append((dict(c), pointer))
                return out
        except (OSError, ValueError, AttributeError):
            pass
    calls = ver.get("calls") or []
    if calls:
        return [(dict(c), "/run/verifier/calls/%d/raw_path" % k) for k, c in enumerate(calls)]
    return [({"call_id": None, "status": "ok", "raw_path": ver.get("raw_path")}, "/run/verifier/raw_path")]


def check_v13(result, ctx):
    """verifier_said per item equals the retained report's tail disposition for that index (E8-12).

    E8-A26 and E8-A40: with the run directory, for every call record the checkpoint holds whose status
    is complete (verifier.is_complete: `complete` and `ok` alike) the file at its raw_path must exist,
    hash to its raw_sha256, and carry a parseable tail whose dispositions match the items' verifier_said;
    a missing file, a hash mismatch, or a missing or unparseable tail is a finding. The legacy skip (a
    report written before E8-12, no structured tail) applies only to a call record that carries no
    raw_sha256. Each item is held to the last complete call that covered it (E8-A15: a resume's fresh
    call covers the pending items only, under their original numbers; a record without an items list
    covers every item). The report of call k is its raw_path, else the fixed path of E8-27."""
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    items = result.get("items") or []
    if not items:
        return [], None
    from . import canon, verifier as vmod
    findings = []
    said_by_index, no_tail = {}, set()
    for k, (c, pointer) in enumerate(_call_records(result, ctx["run_dir"]), 1):
        if not vmod.is_complete(c.get("status")):
            continue
        raw = c.get("raw_path") or vmod.raw_path_for(ctx["run_dir"], k)
        idx = [i for i in c["items"] if isinstance(i, int)] if isinstance(c.get("items"), list) else list(range(len(items)))
        legacy = not c.get("raw_sha256")
        if not os.path.isfile(raw):
            # a missing file is a finding whatever the record carries: the legacy skip is for a report that exists without a tail
            findings.append(_f("V13", pointer, "the retained report %s of complete call %s does not exist (E8-A26)" % (raw, c.get("call_id"))))
            continue
        if not legacy and canon.sha256_file(raw) != c["raw_sha256"]:
            findings.append(_f("V13", pointer, "the retained report %s does not hash to the recorded raw_sha256 (E8-A26: evidence changed)" % raw))
            continue
        with open(raw, "r", encoding="utf-8") as fh:
            text = fh.read()
        parsed = vmod.parse_report_tail(text, len(items), idx)
        if not parsed["ok"]:
            if legacy and vmod.last_fenced_block(text) is None:
                no_tail.update(idx)
                continue
            findings.append(_f("V13", pointer, "the retained report %s has no usable tail: %s" % (raw, parsed["reason"])))
            continue
        for i in idx:
            tail = vmod.tail_item(parsed["tail"], i)
            if tail is not None:
                said_by_index[i] = tail.get("disposition")
                no_tail.discard(i)
    skip = None
    for i, it in enumerate(items):
        said = (it.get("adjudication") or {}).get("verifier_said")
        if i in said_by_index:
            if said_by_index[i] != said:
                findings.append(_f("V13", "/items/%d/adjudication/verifier_said" % i, "%r but the retained report's tail says %r" % (said, said_by_index[i])))
        elif i in no_tail:
            skip = NO_TAIL_SKIP
        else:
            findings.append(_f("V13", "/items/%d/adjudication/verifier_said" % i, "%r but no retained report's tail covers this item" % (said,)))
    return findings, skip


def check_v14(result, ctx):
    """Every accepted grant maps to a write or a marker; every rejected grant object appears in rejected_grants.

    E8-A24: the verdict is recomputed with the core's own channel rule (grant_verdicts). A grant the rule
    rejects must be listed under its JSON path (E8-A12 shape); a grant the rule accepts must not be listed
    unless the entry's why states another reason (it matched no entry, it conflicted, a continuation grant
    already used); the result's own rejected_grants is never the proof. The mapping check (an accepted
    grant maps to a write or a marker) runs on completed results as before."""
    if "input" not in ctx:
        return [], _skip("input")
    findings = []
    writes = result.get("records_written") or []
    n_waived = len([w for w in writes if w.get("kind") == "waived_line"])
    n_reopened = len([w for w in writes if w.get("kind") == "reopened_line"])
    items = result.get("items") or []
    completed = result.get("status") == "completed"
    graded = "run" in result and result.get("status") not in ("missing_input",)
    for v in grant_verdicts(result, ctx["input"]):
        path = "/" + v["path"].replace(".", "/").replace("[", "/").replace("]", "")
        if not v["ok"]:
            if graded and not v["named"]:
                findings.append(_f("V14", path, "the channel rule rejects this grant (%s) but rejected_grants does not list it under %s (E8-A24)" % (v["why"], v["path"])))
            continue  # a rejected grant maps to nothing: V7 holds the markers and lines
        if v["named"] and not _other_reason(v["listed_why"]):
            findings.append(_f("V14", path, "the channel rule accepts this grant but rejected_grants lists it under %s for no other reason: %r (E8-A24)" % (v["path"], v["listed_why"])))
            continue
        if v["named"] or not completed or v["kind"] == "continuation":
            continue
        count, marker = (n_waived, "waived") if v["kind"] == "waived" else (n_reopened, "reopened")
        marked = any(marker in it and _item_key(it) == _item_key(v["grant"]["item"]) for it in items)
        if count == 0 and not marked:
            findings.append(_f("V14", path, "an accepted %s grant maps to no write and no marker" % marker))
    return findings, None


APPENDED_KINDS = ("reopened_line", "punch_list_block", "waived_line", "verdict_doc_copy")


def check_v17(result, ctx):
    """The run's events, rendered by `records.py render --run-id`, are exactly the lines the
    document holds at the places the receipt names (E13 slice 1, send-back 1).

    This replaces "every ledger line the run wrote parses back under Appendix A", which read the
    document with the core's own grammar and so was a second reader of the record. Four checks:

    A. every line a landed step wrote is text the run's events render to — a log the document has
       drifted from fails here;
    B. the target still holds that text — a line altered after the write fails here;
    C. every piece the render produces belongs to a plan step — an event of this run with no line
       in the document fails here;
    D. each new defect and each waived/reopened marker of the result corresponds to an event of
       this run, and a defect's `charged_to_slice` equals the slice its event charges (E8-A25).

    A, C and D need the run's own events. A receipt written BEFORE the records moved into the
    component carries no appended seqs (its records reached the log through the importer, under the
    importer's actor: question 6 of the builder's report), and for one of those only check B runs —
    and only over the steps that store their bytes, since a seeded plan regenerates them at replay
    (E8-28) and its after-hash is V8's check, not this one.
    """
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    if ctx.get("workspace") is None:
        return [], _skip("workspace")
    if result.get("status") not in ("completed", "recording_failed"):
        return [], None
    writes = result.get("records_written") or []
    if not any(w.get("kind") in RECORD_KINDS for w in writes):
        return [], None
    if ctx.get("records") is None:
        return [], _skip("records")
    from . import records_client as rcl
    findings = []
    run_dir = _run_dir(result, ctx)
    receipt_path = os.path.join(run_dir, "receipt.json") if run_dir else None
    if not receipt_path or not os.path.isfile(receipt_path):
        return [_f("V17", "/receipt_path", "no receipt.json in the run directory, so the places the run wrote are unknown")], None
    try:
        receipt = _read_json(receipt_path)
    except (OSError, ValueError) as exc:
        return [_f("V17", "/receipt_path", "receipt.json does not parse: %s" % exc)], None
    run_id = receipt.get("run_id")
    doc_rel = _build_doc(result, ctx) or next((w["path"] for w in writes if w.get("kind") == "punch_list_block"), None)
    if not doc_rel:
        return [_f("V17", "/records_written", "the result names no ledger document, so its records cannot be read")], None
    done = set(e["step"] for e in receipt.get("entries") or [] if e.get("type") == "done")
    planned = [s for s in receipt.get("plan") or [] if s.get("kind") in APPENDED_KINDS and not s.get("cancelled")]
    landed = [s for s in planned if s["step"] in done]

    # B: the target still holds the text each landed step wrote
    for step in landed:
        content = step.get("content")
        if content is None:
            # a seeded or legacy plan stores no content and regenerates its bytes at replay
            # (E8-28); there is nothing to compare here, and the step's after-hash is V8's check
            continue
        full = os.path.join(ctx["workspace"], step["target"])
        if not os.path.isfile(full):
            findings.append(_f("V17", "/records_written", "%s does not exist under the workspace" % step["target"]))
            continue
        with open(full, "r", encoding="utf-8") as fh:
            text = fh.read()
        if content not in text:
            findings.append(_f("V17", "/records_written", "%s no longer holds the text step %d (%s) wrote; a record was altered after the write"
                               % (step["target"], step["step"], step["kind"])))

    appended_seqs = (receipt.get("append") or {}).get("seqs") or []
    if not appended_seqs:
        # a receipt written before the records moved: its records are in the log as legacy events
        # under the importer's actor, so there is no run of events to render (question 6)
        return findings, None

    try:
        rendered = ctx["records"].render(ctx["workspace"], doc_rel, run_id)
        rows = ctx["records"].events(ctx["workspace"], doc_rel)["results"]
    except rcl.RecordsRefusal as refusal:
        findings.append(_f("V17", "/records_written", "the run's events could not be read back: %s" % refusal.sentence()))
        return findings, None
    mine = [r["event"] for r in rows if (r["event"].get("actor") or {}).get("run_id") == run_id]
    if not mine:
        findings.append(_f("V17", "/records_written", "the receipt records an append of seq %s, and the log holds no event of run %r"
                           % (", ".join(str(n) for n in appended_seqs), run_id)))
        return findings, None
    pieces = ([rendered["block"]] if rendered.get("block") else []) + list(rendered.get("grants") or [])

    # A: every landed line is one the run's events render to
    for step in landed:
        content = step.get("content")
        if content is not None and content not in pieces:
            findings.append(_f("V17", "/records_written", "step %d (%s, %s) wrote text the run's events do not render; the log and the document have diverged"
                               % (step["step"], step["kind"], step["target"])))
    # C: every piece the render produces belongs to a plan step
    for piece in pieces:
        if not any(s.get("content") == piece for s in planned):
            first = piece.strip().split("\n")[0][:120]
            findings.append(_f("V17", "/records_written", "the run's events render text no plan step wrote: %s" % first))

    # D: the defects and the markers correspond to the run's events
    raised = [e for e in mine if e.get("kind") == "defect_raised"]
    for i, d in enumerate(result.get("new_defects") or []):
        where = d.get("location") or {}
        match = [e for e in raised if (e.get("location") or {}).get("file") == where.get("file")
                 and (e.get("location") or {}).get("line") == where.get("line") and e.get("claim") == d.get("claim")]
        if not match:
            findings.append(_f("V17", "/new_defects/%d" % i, "no defect_raised event of this run names this defect"))
        elif match[-1].get("slice") != d.get("charged_to_slice"):
            findings.append(_f("V17", "/new_defects/%d/charged_to_slice" % i,
                               "charged_to_slice is %r but the event charges %r (E8-A25)"
                               % (d.get("charged_to_slice"), match[-1].get("slice"))))
    for i, it in enumerate(result.get("items") or []):
        for marker in ("waived", "reopened"):
            if marker not in it:
                continue
            m = it[marker] or {}
            hits = [e for e in mine if e.get("kind") == marker and e.get("grant_date") == m.get("date")
                    and e.get("words") == m.get("quoted_words")]
            if not hits:
                findings.append(_f("V17", "/items/%d/%s" % (i, marker),
                                   "no %s event of this run matches this marker" % marker))
    return findings, None


REFUSED_RESUME = re.compile(r"^resume refused at section 11 step (\d+)(?:: (.*))?$", re.S)
# E8-A49: the two refusal reasons cmd_resume builds whose named condition V18 checks on the checkpoint
ENDED_RUN = re.compile(r"^the run ended as ([a-z_]+): (.*); start a new run$", re.S)
REUSED_GRANT = re.compile(r"extra_continuation: turn_ref '(.*)' already used for continuation (\d+)")


def check_v18(result, ctx):
    """Checkpoint integrity holds and its run id equals the result's.

    E8-A33: a stopped result whose stop_reason begins `resume refused at section 11 step N` is held the
    other way round: the checkpoint verification must fail at step N (steps 1 and 2 through
    checkpoint.read_and_verify; step 3 through a run id mismatch, or the binding hash when the input is
    supplied; step 4 through a done item's result failing the item definition; step 5 through the
    receipt's verification; step 6 through the identity against the start identity or the transaction
    guard, which needs the workspace), and the result carries no items, cards, new defects, or
    project-record writes; a refusal beside a checkpoint that verifies is the finding. E8-A49: a step 1
    refusal that says the run ended (`the run ended as <status>: ...; start a new run`) needs the
    checkpoint verified at phase `stopped` with `terminal.resumable` false and `terminal.status` the named
    status; a step 6 refusal naming `extra_continuation: turn_ref '<ref>' already used for continuation
    <n>` needs `<ref>` in the checkpoint's `continuation_grants_used`. Every other status: V18 as before."""
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    if "run" not in result:
        return [], None
    from . import checkpoint as cpmod
    m = REFUSED_RESUME.match(result.get("stop_reason") or "") if result.get("status") == "stopped" else None
    if m:
        return _check_refused_resume(result, ctx, int(m.group(1)), m.group(2) or "")
    if not os.path.isfile(os.path.join(ctx["run_dir"], "checkpoint.json")):
        if result.get("status") in ("completed", "recording_failed", "stopped") and any(
                os.path.basename(w.get("path", "")) == "checkpoint.json" for w in result.get("records_written") or []):
            return [_f("V18", "/run/run_id", "the write list names checkpoint.json but the run directory holds none")], None
        return [], None
    v = cpmod.read_and_verify(ctx["run_dir"], ctx.get("schemas"))
    if not v["ok"]:
        return [_f("V18", "/run/run_id", "checkpoint step %d: %s" % (v["step"], v["reason"]))], None
    if v["doc"].get("run_id") != result["run"].get("run_id"):
        return [_f("V18", "/run/run_id", "the checkpoint's run id %r is not the result's" % v["doc"].get("run_id"))], None
    return [], None


def _check_refused_resume(result, ctx, step, reason=""):
    """E8-A33: the refusal at section 11 step `step` must be real, and the envelope must carry nothing graded;
    E8-A49: a refusal that names its condition (a run that ended, a reused continuation grant) is held to that
    condition on the checkpoint."""
    from . import checkpoint as cpmod, receipt as rcmod, identity
    findings = []
    for key in ("items", "cards", "new_defects"):
        if key in result:
            findings.append(_f("V18", "/" + key, "a refused resume carries %s" % key))
    for i, w in enumerate(result.get("records_written") or []):
        if w.get("kind") in RECORD_KINDS:
            findings.append(_f("V18", "/records_written/%d" % i, "a refused resume lists a project-record write (%s)" % w.get("kind")))
    v = cpmod.read_and_verify(ctx["run_dir"], ctx.get("schemas"))
    skip = None
    ended = ENDED_RUN.match(reason) if step == 1 else None
    if ended:
        # E8-A49: the run ended (section 11 step 1, E8-A20): the checkpoint verifies at phase stopped, its terminal
        # block is not resumable, and its terminal status is the one the refusal names
        named = ended.group(1)
        if not v["ok"]:
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 1 as a run that ended as %s, but the checkpoint fails at step %d: %s" % (named, v["step"], v["reason"])))
            return findings, None
        cp = v["doc"]
        term = cp.get("terminal") or {}
        if cp.get("phase") != "stopped":
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 1 as a run that ended as %s, but the checkpoint's phase is %s, not stopped" % (named, cp.get("phase"))))
        elif term.get("resumable"):
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 1 as a run that ended as %s, but the checkpoint's terminal block says resumable" % named))
        elif term.get("status", "stopped") != named:
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 1 as a run that ended as %s, but the checkpoint's terminal status is %s" % (named, term.get("status", "stopped (no terminal block)"))))
        return findings, None
    if step in (1, 2):
        if v["ok"] or v["step"] != step:
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step %d but the checkpoint %s" % (step, "verifies" if v["ok"] else "fails at step %d: %s" % (v["step"], v["reason"]))))
        return findings, None
    if not v["ok"]:
        findings.append(_f("V18", "/stop_reason", "the resume was refused at step %d but the checkpoint already fails at step %d: %s" % (step, v["step"], v["reason"])))
        return findings, None
    cp = v["doc"]
    if step == 3:
        mismatch = cp.get("run_id") != result["run"].get("run_id")
        if not mismatch and "input" in ctx:
            from . import inputs
            mismatch = inputs.binding_hash(ctx["input"]) != cp.get("input_sha256")
        if not mismatch:
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 3 but the checkpoint's run id is the result's%s" % ("" if "input" in ctx else " (the binding hash needs the input)")))
    elif step == 4:
        bad = [i for i, st in enumerate(cp.get("items") or []) if st.get("state") == "done" and validate_item_result(st.get("result"), ctx.get("schemas"))]
        if not bad:
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 4 but every done item's result validates against the item definition"))
    elif step == 5:
        r = rcmod.read_and_verify(ctx["run_dir"], ctx.get("schemas"))
        if not r["exists"]:
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 5 but the run directory holds no receipt"))
        elif r["ok"]:
            if ctx.get("workspace") is None:
                skip = _skip("workspace")
            elif not any(c["class"] == "outside" for c in rcmod.classify(r["doc"].get("plan") or [], r["doc"].get("entries") or [], ctx["workspace"])):
                findings.append(_f("V18", "/stop_reason", "the resume was refused at step 5 but the receipt verifies and no plan step classifies as an outside edit"))
    elif step == 6 and REUSED_GRANT.search(reason):
        # E8-A49: the presented grant's turn_ref was already consumed (E8-A23): the checkpoint lists it
        ref = REUSED_GRANT.search(reason).group(1)
        if ref not in (cp.get("continuation_grants_used") or []):
            findings.append(_f("V18", "/stop_reason", "the resume was refused at step 6 for a reused continuation grant, but the checkpoint's continuation_grants_used does not list turn_ref %r" % ref))
    elif step == 6:
        if ctx.get("workspace") is None:
            skip = _skip("workspace")
        else:
            now = identity.identity_of(ctx["workspace"])
            guard = cp.get("transaction_guard")
            expected = guard["identity"] if guard else cp.get("start_identity") or {}
            same = all(now.get(k) == expected.get(k) for k in ("commit", "untracked", "untracked_sha256"))
            if guard and same:
                from . import canon
                same = canon.sha256_hex(identity.tracked_diff_excluding(ctx["workspace"], guard.get("targets") or [])) == guard.get("nontarget_diff_sha256")
            elif same and not guard:
                same = now.get("tracked_diff_sha256") == expected.get("tracked_diff_sha256") and now.get("dirty") == expected.get("dirty")
            if same and not now.get("submodules"):
                findings.append(_f("V18", "/stop_reason", "the resume was refused at step 6 but the workspace identity equals the checkpoint's %s" % ("transaction guard" if guard else "start identity")))
    else:
        findings.append(_f("V18", "/stop_reason", "section 11 has no step %d" % step))
    return findings, skip


CHECKS = {
    "V1": check_v1_full,
    "V2": check_v2_full,
    "V3": check_v3,
    "V4": check_v4,
    "V5": check_v5,
    "V6": check_v6,
    "V7": check_v7,
    "V8": check_v8,
    "V9": check_v9,
    "V10": check_v10,
    "V11": check_v11,
    "V12": check_v12_full,
    "V13": check_v13,
    "V14": check_v14,
    "V15": check_v15,
    "V16": check_v16,
    "V17": check_v17,
    "V18": check_v18,
}


def run_semantic(result, input_doc=None, run_dir=None, workspace=None, schemas=None, records=None):
    """Run every semantic check; return {"semantic": [findings], "skipped": [{"id", "reason"}]}.

    `records` is the records component client V6 and V17 read the records through (E13 slice 1).
    Without one those two report themselves skipped rather than falling back to the document."""
    ctx = {"run_dir": run_dir, "workspace": workspace, "schemas": schemas, "records": records}
    if input_doc is not None:
        ctx["input"] = input_doc
    findings, skipped = [], []
    for check_id in CHECK_IDS:
        got, skip = CHECKS[check_id](result, ctx)
        findings.extend(got)
        if skip:
            skipped.append({"id": check_id, "reason": skip})
    return {"semantic": findings, "skipped": skipped}
