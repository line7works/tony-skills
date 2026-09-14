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
`{"id": "V<n>", "path": "<json pointer>", "message": "..."}`. Every check of lane contract
section 8 runs when what it needs was supplied (the input for cardinality, slices, grants, and
the run-block rule; the run directory for the receipt, the checkpoint, the retained report, and
artifact containment; the workspace for the ledger, the cards, and the round trip); a check that
needs something not supplied reports "skipped: needs input" / "needs run directory" / "needs
workspace" and nothing else is ever skipped.
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

    The result-only part (no card moved, no status line written, result not_clear) runs here;
    check_v12_full adds the cancelled flags read from the receipt when the run directory is
    supplied."""
    findings = []
    skip = None
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


NEEDS_NAME = {"run_dir": "run directory", "workspace": "workspace", "input": "input"}


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


def _accepted_grants(result, inp):
    auth = (inp or {}).get("authorization") or {}
    waivers = [g for i, g in enumerate(auth.get("waivers") or []) if not _grant_named_rejected(result, "authorization.waivers[%d]" % i)]
    reopenings = [g for i, g in enumerate(auth.get("reopen") or []) if not _grant_named_rejected(result, "authorization.reopen[%d]" % i)]
    return waivers, reopenings


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
    """Every record write targets an authorized destination; the list is in write order."""
    run_dir = _run_dir(result, ctx)
    if run_dir is None:
        return [], _skip("run_dir")
    findings = []
    writes = result.get("records_written") or []
    seen_record, seen_result = False, False
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
        elif kind in RECORD_KINDS:
            if os.path.isabs(path) or any(seg == ".." for seg in path.split("/")):
                findings.append(_f("V3", "/records_written/%d/path" % i, "project record %r is not a workspace-relative path" % path))
            elif ctx.get("workspace") is not None and not os.path.isfile(os.path.join(ctx["workspace"], path)):
                findings.append(_f("V3", "/records_written/%d/path" % i, "project record %r does not exist under the workspace" % path))
            if kind == "verdict_doc_copy" and not path.startswith("docs/reviews/"):
                findings.append(_f("V3", "/records_written/%d/path" % i, "a verdict-doc copy outside docs/reviews/"))
            if seen_result:
                findings.append(_f("V3", "/records_written/%d" % i, "a project record is listed after result.json"))
            seen_record = True
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


def check_v6(result, ctx):
    """The card mapping reproduces each after value over the slice's open set now (E8-4)."""
    if ctx.get("workspace") is None:
        return [], _skip("workspace")
    if result.get("status") != "completed":
        return [], None
    from . import ledger
    findings = []
    doc_rel = _build_doc(result, ctx)
    path = os.path.join(ctx["workspace"], doc_rel) if doc_rel else None
    if not path or not os.path.isfile(path):
        return [_f("V6", "/cards", "the build doc %r does not exist under the workspace" % doc_rel)], None
    with open(path, "r", encoding="utf-8") as fh:
        parsed = ledger.parse_document(fh.read(), doc_rel)
    opened = ledger.open_set(parsed)
    want_slices = ledger.sort_slices(it["slice"] for it in result.get("items") or [] if it.get("slice") != "none")
    got_slices = [c["slice"] for c in result.get("cards") or []]
    if got_slices != want_slices:
        findings.append(_f("V6", "/cards", "cards list slices %r; the checklist's slices are %r" % (got_slices, want_slices)))
    violated = bool(result.get("boundary_violations"))
    for i, c in enumerate(result.get("cards") or []):
        open_here = [e for e in opened["entries"] if e["slice"] == c["slice"] and e["state"] == "open"]
        mapped = ledger.card_after(c["before"], open_here)
        current = ledger.slice_card(parsed, c["slice"])
        if violated:
            if c["after"] != c["before"]:
                findings.append(_f("V6", "/cards/%d" % i, "a card moved beside a boundary violation"))
        elif c["after"] != mapped:
            findings.append(_f("V6", "/cards/%d/after" % i, "after is %r; the mapping over the slice's open set gives %r" % (c["after"], mapped)))
        if c["after"] != current and c["before"] in ledger.MOVABLE_CARDS:
            findings.append(_f("V6", "/cards/%d/after" % i, "after is %r but the document's status line reads %r" % (c["after"], current)))
    return findings, None


def check_v7(result, ctx):
    """Markers correspond to accepted grants and to waived_line / reopened_line writes."""
    if "input" not in ctx:
        return [], _skip("input")
    from . import ledger
    findings = []
    waivers, reopenings = _accepted_grants(result, ctx["input"])
    writes = result.get("records_written") or []
    n_waived = len([w for w in writes if w.get("kind") == "waived_line"])
    n_reopened = len([w for w in writes if w.get("kind") == "reopened_line"])
    if result.get("status") == "completed":
        if n_waived != len(waivers):
            findings.append(_f("V7", "/records_written", "%d waived_line writes for %d accepted waivers" % (n_waived, len(waivers))))
        if n_reopened != len(reopenings):
            findings.append(_f("V7", "/records_written", "%d reopened_line writes for %d accepted reopenings" % (n_reopened, len(reopenings))))
    for i, it in enumerate(result.get("items") or []):
        for marker, grants in (("waived", waivers), ("reopened", reopenings)):
            if marker not in it:
                continue
            m = it[marker]
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
    done = set(e["step"] for e in rc.get("entries") or [] if e.get("type") == "done")
    landed = [s for s in rc.get("plan") or [] if s["step"] in done and not s.get("cancelled")]
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
    return findings, None


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
    for s in rc.get("plan") or []:
        if s.get("kind") == "status_line" and s.get("cancelled") is not True:
            findings.append(_f("V12", "/receipt_path", "status-line step %d is not cancelled beside a boundary violation" % s.get("step")))
    return findings, None


NO_TAIL_SKIP = "skipped: the retained report carries no structured tail (a report written before E8-12)"


def check_v13(result, ctx):
    """verifier_said per item equals the retained report's tail disposition for that index (E8-12).

    Each item is held to the last complete call that covered it (E8-A15: a resume's fresh call
    covers the pending items only, under their original numbers; the items a call covered come
    from the checkpoint, and a call the checkpoint does not record covers every item). The
    report of call k is its raw_path, else the fixed path of E8-27. An item whose report carries
    no structured tail (a report written before E8-12) is skipped with that reason."""
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    items = result.get("items") or []
    if not items:
        return [], None
    from . import verifier as vmod
    ver = (result.get("run") or {}).get("verifier") or {}
    calls = ver.get("calls") or []
    if not calls:
        raw = ver.get("raw_path")
        if not raw or not os.path.isfile(raw):
            return [_f("V13", "/run/verifier/raw_path", "the retained report %r does not exist" % raw)], None
        calls = [{"call_id": None, "status": "ok", "raw_path": raw}]
    covered = {}
    cp_path = os.path.join(ctx["run_dir"], "checkpoint.json")
    if os.path.isfile(cp_path):
        try:
            for c in _read_json(cp_path).get("verifier_calls") or []:
                if isinstance(c.get("items"), list):
                    covered[c.get("call_id")] = [i for i in c["items"] if isinstance(i, int)]
        except (OSError, ValueError, AttributeError):
            pass
    findings = []
    said_by_index, no_tail = {}, set()
    for k, c in enumerate(calls, 1):
        if c.get("status") not in ("ok", vmod.COMPLETE):
            continue
        raw = c.get("raw_path") or vmod.raw_path_for(ctx["run_dir"], k)
        if not os.path.isfile(raw):
            if c.get("raw_path"):
                findings.append(_f("V13", "/run/verifier/calls/%d/raw_path" % (k - 1), "the retained report %r does not exist" % raw))
            continue
        with open(raw, "r", encoding="utf-8") as fh:
            text = fh.read()
        idx = covered.get(c.get("call_id"), list(range(len(items))))
        parsed = vmod.parse_report_tail(text, len(items), idx)
        if not parsed["ok"]:
            if vmod.last_fenced_block(text) is None:
                no_tail.update(idx)
                continue
            findings.append(_f("V13", "/run/verifier/calls/%d/raw_path" % (k - 1), "the retained report %s has no usable tail: %s" % (raw, parsed["reason"])))
            continue
        for i in idx:
            tail = vmod.tail_item(parsed["tail"], i)
            if tail is not None:
                said_by_index[i] = tail.get("disposition")
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
    """Every accepted grant maps to a write or a marker; every rejected grant object appears in rejected_grants."""
    if "input" not in ctx:
        return [], _skip("input")
    findings = []
    auth = (ctx["input"] or {}).get("authorization") or {}
    writes = result.get("records_written") or []
    n_waived = len([w for w in writes if w.get("kind") == "waived_line"])
    n_reopened = len([w for w in writes if w.get("kind") == "reopened_line"])
    items = result.get("items") or []
    if result.get("status") != "completed":
        return findings, None
    for kind, key, count, marker in (("waivers", "waivers", n_waived, "waived"), ("reopen", "reopen", n_reopened, "reopened")):
        for i, g in enumerate(auth.get(key) or []):
            path = "/authorization/%s/%d" % (key, i)
            if _grant_named_rejected(result, "authorization.%s[%d]" % (key, i)):
                continue  # E8-A12: matched by the grant's JSON path, never by location alone
            marked = any(marker in it and _item_key(it) == _item_key(g["item"]) for it in items)
            if count == 0 and not marked:
                findings.append(_f("V14", path, "an accepted %s grant maps to no write and no marker" % marker))
    return findings, None


def check_v17(result, ctx):
    """Every ledger line the run wrote parses back under Appendix A to the item it records."""
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    if ctx.get("workspace") is None:
        return [], _skip("workspace")
    if result.get("status") not in ("completed", "recording_failed"):
        return [], None
    from . import ledger
    findings = []
    writes = result.get("records_written") or []
    docs = sorted(set(w["path"] for w in writes if w.get("kind") in RECORD_KINDS))
    if not docs:
        return findings, None
    parsed_docs = {}
    for rel in docs:
        path = os.path.join(ctx["workspace"], rel)
        if not os.path.isfile(path):
            findings.append(_f("V17", "/records_written", "%s does not exist under the workspace" % rel))
            continue
        with open(path, "r", encoding="utf-8") as fh:
            parsed_docs[rel] = ledger.parse_document(fh.read(), rel)
    block_written = any(w.get("kind") == "punch_list_block" for w in writes)
    main_doc = next((w["path"] for w in writes if w.get("kind") == "punch_list_block"), None)
    parsed = parsed_docs.get(main_doc) if main_doc else None
    if block_written and parsed is not None:
        for i, it in enumerate(result.get("items") or []):
            want_claim = None if it["claim"] == "()" else it["claim"]
            want_disp = "fixed" if it.get("disposition") == "fixed" else "not fixed"
            hits = [r for r in parsed["records"] if r["kind"] == "recheck" and r["file"] == it["location"]["file"] and r["line"] == it["location"]["line"]
                    and r["claim"] == want_claim and r["disposition"] == want_disp]
            if not hits:
                findings.append(_f("V17", "/items/%d" % i, "no recheck line in %s parses back to this item with disposition %r" % (main_doc, want_disp)))
        for i, d in enumerate(result.get("new_defects") or []):
            hits = [r for r in parsed["records"] if r["kind"] == "defect" and r["file"] == d["location"]["file"] and r["line"] == d["location"]["line"] and r["claim"] == d["claim"]]
            if not hits:
                findings.append(_f("V17", "/new_defects/%d" % i, "no fix-introduced defect line in %s parses back to this defect" % main_doc))
    for i, it in enumerate(result.get("items") or []):
        for marker, kind in (("waived", "waiver"), ("reopened", "reopening")):
            if marker in it and any(w.get("kind") == marker + "_line" for w in writes) and parsed is not None:
                m = it[marker]
                # the marker already carries the ledger form of the words (E8-A16), so the two compare directly
                hits = [r for r in parsed["records"] if r["kind"] == kind and r["file"] == it["location"]["file"] and r["line"] == it["location"]["line"]
                        and r.get("date") == m.get("date") and r.get("words") == m.get("quoted_words")]
                if not hits:
                    findings.append(_f("V17", "/items/%d/%s" % (i, marker), "no %s line in %s parses back to this marker" % (kind, main_doc)))
    for a in (parsed["ambiguities"] if parsed else []):
        findings.append(_f("V17", "/records_written", "%s:%d is ambiguous after the run: %s" % (main_doc, a["line_no"], a["reason"])))
    return findings, None


def check_v18(result, ctx):
    """Checkpoint integrity holds and its run id equals the result's."""
    if ctx.get("run_dir") is None:
        return [], _skip("run_dir")
    if "run" not in result:
        return [], None
    from . import checkpoint as cpmod
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
