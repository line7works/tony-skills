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

Semantic checks: `run_semantic(result, input_doc=None, run_dir=None, workspace=None)` returns
`{"semantic": [findings], "skipped": [{"id", "reason"}]}`. Each finding is
`{"id": "V<n>", "path": "<json pointer>", "message": "..."}`. Slice 1 implements the checks that
need neither a run directory nor a workspace (V1, V5, V9, V10, V11, V15; V16 and the
workspace-free part of V2 when the input is supplied; the result-only part of V12). Every part a
check cannot run yet reports a skip reason worded by what was supplied ("needs run directory" /
"needs workspace" when it was not; "not implemented until slice 2 (needs the run directory's
<what>)" when it was); slice 2 replaces each with the check.
"""
import json
import os
import sys

MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"

try:  # the guarded import: a missing jsonschema is reported once, at the first use
    from jsonschema import Draft202012Validator as _Validator
except ImportError:  # pragma: no cover - exercised by the exit-3 tests through a subprocess
    _Validator = None

SCHEMA_FILES = {
    "input": "input.schema.json",
    "result": "result.schema.json",
    "checkpoint": "checkpoint.schema.json",
    "receipt": "receipt.schema.json",
}
SEP = " · "
RECORD_KINDS = ("reopened_line", "punch_list_block", "waived_line", "verdict_doc_copy", "status_line")
CHECK_IDS = ["V%d" % i for i in range(1, 19)]


class ReferenceUnavailable(RuntimeError):
    """A schema under the skill root is missing or unreadable (pilot contract section 15)."""

    def __init__(self, relative_path, cause):
        RuntimeError.__init__(self, "reference unavailable: %s (%s)" % (relative_path, cause))
        self.relative_path = relative_path


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
    """The directory holding SKILL.md: given explicitly, else two levels above this file."""
    if explicit:
        return os.path.abspath(explicit)
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
            V.check_schema(self.docs[key])
        self.input = V(self.docs["input"])
        self.result = V(self.docs["result"])
        self.checkpoint = V(self.docs["checkpoint"])
        self.receipt = V(self.docs["receipt"])
        # the result schema's item definition on its own (section 11 step 4)
        self.item = V({"$schema": self.docs["result"]["$schema"], "$defs": self.docs["result"]["$defs"],
                       "$ref": "#/$defs/item_result"})


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
    """A fixed item carries no block and no missing field."""
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
    return findings, None


def check_v12(result, ctx):
    """A run with boundary violations changed no card and cancelled its status-line steps.

    The result-only part (no card moved, no status line written, result not_clear) runs here.
    The cancelled flags on the receipt's status-line steps are read in slice 2; until then that
    part is always reported as skipped, whether or not a run directory was supplied, so --strict
    never passes a violated run on this check's word alone."""
    findings = []
    skip = "skipped: cancelled flags on the receipt's status-line steps: slice 2"
    if not result.get("boundary_violations"):
        return findings, skip
    for i, card in enumerate(result.get("cards") or []):
        if card.get("before") != card.get("after"):
            findings.append(_f("V12", "/cards/%d" % i, "card moved from %r to %r beside a boundary violation"
                               % (card.get("before"), card.get("after"))))
    for i, w in enumerate(result.get("records_written") or []):
        if w.get("kind") == "status_line":
            findings.append(_f("V12", "/records_written/%d" % i, "a status line was written beside a boundary violation"))
    if result.get("result") not in (None, "not_clear"):
        findings.append(_f("V12", "/result", "boundary violations force not_clear, found %r" % result.get("result")))
    return findings, skip


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


NEEDS_NAME = {"run_dir": "run directory", "workspace": "workspace"}


def _needs_skip(ctx, what_supplied, what):
    """The skip reason for a part slice 2 implements, worded by what the caller supplied.

    When the needed thing (the run directory or the workspace) was supplied, the check is not
    implemented yet: "not implemented until slice 2 (needs the run directory's <what>)". When it
    was not, the caller can tell at once: "needs run directory" / "needs workspace"."""
    name = NEEDS_NAME[what_supplied]
    if ctx.get(what_supplied) is not None:
        return "skipped: not implemented until slice 2 (needs the %s's %s)" % (name, what)
    return "skipped: needs %s" % name


def _needs(what_supplied, what):
    def stub(result, ctx):
        return [], _needs_skip(ctx, what_supplied, what)
    return stub


CHECKS = {
    "V1": check_v1,
    "V2": check_v2,
    "V3": _needs("run_dir", "artifact list and the workspace's write destinations"),
    "V4": _needs("run_dir", "artifact list"),
    "V5": check_v5,
    "V6": _needs("workspace", "ledger and cards"),
    "V7": _needs("run_dir", "receipt with the waived_line and reopened_line writes"),
    "V8": _needs("run_dir", "receipt.json and receipt.log"),
    "V9": check_v9,
    "V10": check_v10,
    "V11": check_v11,
    "V12": check_v12,
    "V13": _needs("run_dir", "retained verifier report"),
    "V14": _needs("run_dir", "input.json and receipt for the grants against writes and markers"),
    "V15": check_v15,
    "V16": check_v16,
    "V17": _needs("workspace", "ledger lines"),
    "V18": _needs("run_dir", "checkpoint.json and checkpoint.log"),
}


def run_semantic(result, input_doc=None, run_dir=None, workspace=None, schemas=None):
    """Run every semantic check; return {"semantic": [findings], "skipped": [{"id", "reason"}]}."""
    ctx = {"run_dir": run_dir, "workspace": workspace, "schemas": schemas}
    if input_doc is not None:
        ctx["input"] = input_doc
    findings, skipped = [], []
    for check_id in CHECK_IDS:
        got, skip = CHECKS[check_id](result, ctx)
        findings.extend(got)
        if skip:
            skipped.append({"id": check_id, "reason": skip})
    return {"semantic": findings, "skipped": skipped}
