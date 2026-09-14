#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""recheck.py: the phase driver of recheck-v2 (E8 lane contract sections 5 and 6).

    uv run recheck.py start <input.json>
    uv run recheck.py record-call --run-dir D --call-id ID --status S [--raw FILE] [--model ID] [--kind K]
                                  [--injected NAME ...] [--refused TEXT ...] [--note TEXT]
    uv run recheck.py adjudicate --run-dir D --item N --action confirmed|downgraded|upgraded|disputed
                                 [--reason R] [--note T] [--upgrade-evidence T]
    uv run recheck.py new-defect --run-dir D (--index K | --location F:L --claim C --scenario T --caused-by N)
                                 --severity S --severity-basis TEXT
    uv run recheck.py record --run-dir D
    uv run recheck.py resume <input.json>
    uv run recheck.py identity <workspace>
    uv run recheck.py ledger <doc> [--workspace W]
    uv run recheck.py skill-identity

The executor (the model running SKILL.md) drives the phases assembling -> verifying ->
adjudicating -> recording -> committed and supplies judgment at three points only: building
the input on the direct route, asking the one question, and adjudicating. Every deterministic
step is this script's: reference loading (E8-17), validation and path rules (E8-6), the reused
run id (E8-23), the floor (E8-18), identity and the submodule refusal (E8-2), the review sheet,
scope and grants, the brief (E8-11), the checkpoint, the verifier call bookkeeping (E8-27),
the recording transaction (section 9), result assembly and validation, and the chat block.

stdout: one JSON document and nothing else; every document carries "next" (verify,
adjudicate, record, resume, done). stderr: diagnostics. Exit 0 success; 10 the run reached a
terminal status (start, record, resume, and record-call on a stop; a reference under the skill
root that is missing or does not parse stops every command this way, `stop_reason`
`reference unavailable: references/<name>`, the envelope on stdout and nothing written, E8-17,
E8-A10); 2 usage (a bad argument, an input file that does not exist or is not JSON, a
--skill-root that is not a directory, a phase command against the wrong phase or call id,
record-call --status ok without a readable --raw); 3 missing dependency (jsonschema); 1 anything
else (a defect of this script, a git failure inside the workspace, an unreadable run directory).

Side effects: `start` creates the run directory (only after schema and path validation) and
writes input.json, checklist.md, checkpoint.json and checkpoint.log; every terminal branch
that reached a run directory writes result.json and chat.md (verifier_unavailable included,
E8-A14); a schema-valid payload that fails a path rule gets its envelope on stdout only, with
the run block from the presented invocation and an empty write list (E8-A6). `record-call`
writes verifier/raw.md (or raw-<k>.md) and verifier/calls.json and rewrites the checkpoint;
with --status ok it validates --raw before writing anything. `adjudicate` and `new-defect`
rewrite the checkpoint. `record` writes receipt.json and receipt.log and appends to the
project's ledger (the build doc, its verdict doc, the status lines) inside the receipted
transaction; when the boundary check finds a violation it writes run_dir/boundary.json (a run
artifact, listed after receipt.log and before the transaction's steps in records_written since
it is written during the transaction; a re-assembly after the commit point reads it back,
E8-A11). `resume` continues wherever the checkpoint stopped: at the first pending item (a
retained report, else a fresh call whose brief lists the pending items only under their
original numbers, E8-A15), else at the first plan step not done (a checkpoint at recording with
no receipt plans the transaction afresh), else it re-assembles the result, never overwriting a
valid result.json with a stopped one. Nothing else in the workspace is ever written; git runs
read-only inside the workspace.

Partial effects a failed command may leave: `start` interrupted after validation leaves the run
directory with input.json and possibly checklist.md and a seq-0 checkpoint (a new run under the
same id is then refused as reused; use resume). `record` interrupted inside the transaction
leaves receipt.json naming what landed (status recording_failed when the failure was caught;
otherwise the checkpoint says recording) and the workspace at a receipted step hash; `resume`
classifies every step against the virtual state and completes the rest without a duplicate
append. A checkpoint or receipt rewrite interrupted between the log line and the rename leaves
the one tolerated state (section 11), dropped at the next resume.

Every phase command is idempotent against the checkpoint: repeating a completed command reports
the current phase and changes nothing (a call id already recorded, an item already done, a
committed run).

--skill-root DIR (test only): load references from DIR instead of this script's own skill root.

Test hooks (honored only with RECHECK_TEST=1 in the environment):
  RECHECK_TEST_FAIL_AFTER_STEP=<n>   raise after step n's target landed and before its done entry
  RECHECK_TEST_FAIL_BEFORE_STEP=<n>  raise after step n's intent entry and before its target lands
  RECHECK_TEST_INJECT_BEFORE_STEP=<n> with RECHECK_TEST_INJECT_FILE=<workspace-relative path> and
    RECHECK_TEST_INJECT_TEXT=<text>: overwrite that workspace file just before step n's intent
    entry (a boundary-violation stand-in for the harness edit of check W4)
  RECHECK_TEST_NO_JSONSCHEMA=1       behave as if jsonschema were not importable (exit 3)
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from recheck_core import canon, checkpoint as cpmod, identity, inputs, ledger, receipt as rcmod  # noqa: E402
from recheck_core import result as rmod, validate, verifier as vmod  # noqa: E402

# every section 15 reference, in the order a missing one is named (E8-17); verifier.md joined the list
# at slice 3, when it was written
REQUIRED_REFERENCES = ["references/pilot-contract.md", "references/input.schema.json", "references/result.schema.json",
                       "references/checkpoint.schema.json", "references/receipt.schema.json", "references/verifier.md"]
RUN_FILES = ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log", "result.json")
EXIT_TERMINAL = 10

EXAMPLES = """examples:
  uv run recheck.py start /tmp/recheck-a-20260920-7f3c/input.json
  -> {"next": "verify", "run_dir": "...", "call_id": "recheck-a-20260920-7f3c-verify", "brief": ".../checklist.md", ...}
  uv run recheck.py record-call --run-dir /tmp/recheck-a-20260920-7f3c --call-id recheck-a-20260920-7f3c-verify \\
      --status ok --raw /tmp/recheck-a-20260920-7f3c/verifier/raw.md --kind subagent --model claude-fable-5-1
  uv run recheck.py adjudicate --run-dir /tmp/recheck-a-20260920-7f3c --item 0 --action confirmed
  uv run recheck.py record --run-dir /tmp/recheck-a-20260920-7f3c
  -> {"next": "done", "status": "completed", "result": ".../result.json", "chat": ".../chat.md"}

exit status: 0 success; 10 the run reached a terminal status; 2 usage; 3 jsonschema missing; 1 anything else.
side effects, partial effects, and test hooks: see the module docstring (python3 -c "import recheck; print(recheck.__doc__)")
"""


class Usage(Exception):
    pass


class Stop(Exception):
    """Unwinds to main with a stdout document and an exit code."""

    def __init__(self, document, code):
        Exception.__init__(self, "stop")
        self.document, self.code = document, code


def emit(doc, code=0):
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return code


def log(msg):
    sys.stderr.write(msg.rstrip("\n") + "\n")


# ---- references (E8-17) ------------------------------------------------------------------------

def load_references(root):
    """Read every reference at run start; return the first missing or unparseable relative path
    or None (a `.json` reference must parse as JSON; the schema check follows in load_schemas)."""
    for rel in REQUIRED_REFERENCES:
        path = os.path.join(root, rel)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            if rel.endswith(".json"):
                json.loads(data.decode("utf-8"))
        except (OSError, ValueError):
            return rel
    return None


def reread_appendix_a(root):
    """E8-17: the contract is re-read before the recording transaction."""
    with open(os.path.join(root, "references", "pilot-contract.md"), "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    if "Appendix A" not in text:
        raise Usage("reference unavailable: references/pilot-contract.md (no Appendix A)")


# ---- the run context ---------------------------------------------------------------------------

class Run:
    def __init__(self, root, schemas, doc, raw=None):
        self.root, self.schemas, self.doc, self.raw = root, schemas, doc, raw
        inv = doc.get("invocation") or {}
        self.run_id, self.run_dir, self.workspace = inv.get("run_id"), inv.get("run_dir"), doc.get("workspace")
        self.started = rmod.now_iso()
        self.artifacts = []
        self.cp = None
        self.continuations = 0
        self.run_date = inv.get("run_date") or rmod.today()
        self.session_wrote_fix = bool(inv.get("session_wrote_fix", False))
        self.identity = None
        self.pin = doc.get("source_identity")
        self.matched = True

    def path(self, *parts):
        return os.path.join(self.run_dir, *parts)

    def add_artifact(self, path):
        if path not in self.artifacts:
            self.artifacts.append(path)
        if self.cp is not None:
            self.cp.add_artifact(path)

    def run_block(self, verifier=None, with_session=False):
        return rmod.run_block(self.doc, self.root, run_date=self.run_date, continuations=self.continuations, started=self.started,
                              finished=rmod.now_iso(), verifier=verifier, session_wrote_fix=self.session_wrote_fix if with_session else None)

    def source_identity(self, at_transaction=None, after_run=None):
        block = {"actual": identity.reported(self.identity), "matched": bool(self.matched)}
        if self.pin:
            block["expected"] = self.pin
        if at_transaction is not None:
            block["at_transaction"] = identity.reported(at_transaction)
        if after_run is not None:
            block["after_run"] = identity.reported(after_run)
        # the schema orders nothing; keep expected first for readability
        ordered = {}
        for k in ("expected", "actual", "at_transaction", "after_run", "matched"):
            if k in block:
                ordered[k] = block[k]
        return ordered

    def checklist_block(self, count):
        if self.cp is None:
            return None
        scope = self.cp.doc["scope"]
        checklist = scope["checklist"]
        target = self.doc.get("target") or {}
        named = self.doc.get("named_items") or []
        if "items" in target:
            source = "items"
        else:
            source = "build_doc"
            if named and checklist and all(any(n["location"] == it["location"] and n["claim"] == it["claim"] for n in named)
                                           or any(g["item"]["location"] == it["location"] and g["item"]["claim"] == it["claim"]
                                                  for g in scope["grants"]["reopenings"]) for it in checklist):
                source = "named_items"
        block = {"source": source}
        docs = sorted(set(it["record"]["document"] for it in checklist)) if checklist else [target.get("build_doc")]
        if docs and docs[0]:
            block["build_doc"] = docs[0]
        slice_name = target.get("slice")
        if slice_name is None and checklist:
            slice_name = ", ".join(ledger.sort_slices(it["slice"] for it in checklist))
        if slice_name:
            block["slice"] = slice_name
        block["review_sheet"] = scope["review_sheet"]
        block["count"] = count
        return block

    # ---- terminal deliveries ----

    def deliver(self, doc, chat_extra=None, extra_artifacts=None, keep_existing=False):
        """Write result.json and chat.md, validating first; return (document, path, chat).
        keep_existing: a re-assembly never overwrites a valid result.json with a stopped one."""
        arts = list(self.artifacts) + list(extra_artifacts or [])
        doc["records_written"] = rmod.artifact_writes(arts + [self.path("result.json"), self.path("chat.md")]) \
            if "records_written" not in doc else doc["records_written"]
        final, path, chat = rmod.deliver(doc, self.run_dir, self.schemas, input_doc=self.doc, workspace=self.workspace,
                                         chat_text=rmod.chat_block(doc, chat_extra), stop_builder=self.stop_builder(arts),
                                         keep_existing=keep_existing)
        return final, path, chat

    def stop_builder(self, arts):
        def build(reason, extra):
            out = {"protocol_version": 1, "run": self.run_block(), "status": "stopped", "stop_reason": reason}
            if self.identity is not None and not reason.startswith("unsupported: submodules:"):
                out["source_identity"] = self.source_identity()
            out["records_written"] = rmod.artifact_writes(arts + list(extra) + [self.path("result.json"), self.path("chat.md")])
            return out
        return build

    def terminal(self, status, stop_reason=None, with_identity=True, checklist_count=None, extra=None, chat_extra=None, verifier=None):
        doc = {"protocol_version": 1, "run": self.run_block(verifier=verifier, with_session=verifier is not None), "status": status}
        if with_identity and self.identity is not None:
            doc["source_identity"] = self.source_identity()
        if checklist_count is not None:
            cb = self.checklist_block(checklist_count)
            if cb:
                doc["checklist"] = cb
        if stop_reason:
            doc["stop_reason"] = stop_reason
        if extra:
            doc.update(extra)
        final, path, chat = self.deliver(doc, chat_extra)
        raise Stop({"next": "done", "status": final["status"], "result": path, "question": None, "chat": chat}, EXIT_TERMINAL)

    def missing(self, fields, ambiguity, question=None):
        doc = inputs.envelope(self.doc, fields, ambiguity, question)
        doc["run"] = self.run_block()
        final, path, chat = self.deliver(doc)
        raise Stop({"next": "done", "status": "missing_input", "result": path,
                    "question": final.get("missing_input", {}).get("question"), "chat": chat}, EXIT_TERMINAL)


# ---- start (section 5, assembling) -------------------------------------------------------------

def stopped_envelope_without_run_dir(doc, reason, root):
    """A stopped result delivered on stdout only (nothing written): M1, U1."""
    out = {"protocol_version": 1, "status": "stopped", "stop_reason": reason}
    inv = doc.get("invocation") if isinstance(doc, dict) else None
    if isinstance(inv, dict) and isinstance(inv.get("run_id"), str) and isinstance(inv.get("run_dir"), str):
        try:
            out["run"] = rmod.run_block(doc, root, run_date=inv.get("run_date"))
        except Exception:  # noqa: BLE001 - the run block is best effort on this branch
            pass
    out["records_written"] = []
    return out


def reference_stop(doc, missing, root):
    """The stopped envelope for a reference that is missing or does not parse (E8-17, E8-A10):
    delivered on stdout, exit 10, nothing written; unvalidated when the result schema is at fault."""
    reason = "reference unavailable: %s" % missing
    unvalidated = missing == "references/result.schema.json"
    if unvalidated:
        reason += "; the stopped envelope is delivered unvalidated"
    env = stopped_envelope_without_run_dir(doc, reason, root)
    log(reason)
    return Stop({"next": "done", "status": "stopped", "result": None, "question": None, "chat": None,
                 "unvalidated": unvalidated, "document": env}, EXIT_TERMINAL)


def check_references(root, doc):
    """E8-17: every reference loads at run start; the schemas must parse and be schemas."""
    missing = load_references(root)
    if missing:
        raise reference_stop(doc, missing, root)
    try:
        return validate.load_schemas(root)
    except validate.ReferenceUnavailable as exc:
        raise reference_stop(doc, exc.relative_path, root)


def validate_or_envelope(doc, schemas, root):
    """Schema and path rules (E8-6, E8-A6). A schema failure returns the envelope with no run
    block, nothing written. A schema-valid payload that fails a path rule returns the envelope
    with the run block from the presented invocation, the one question on a direct interactive
    run, an empty write list, and no run directory."""
    errors = validate.validate_input(doc, schemas)
    if errors:
        fields = inputs.schema_fields(errors, doc, schemas)
        amb = ["the payload failed schema validation: " + "; ".join("%s: %s" % (e["path"] or "$", e["message"]) for e in errors[:6])]
        env = inputs.envelope(doc if isinstance(doc, dict) else {}, fields, amb)
        env["missing_input"].pop("question", None)
        raise Stop({"next": "done", "status": "missing_input", "result": None, "question": None, "chat": None, "document": env}, EXIT_TERMINAL)
    violations = inputs.path_rules(doc, identity.is_work_tree_root)
    if violations:
        inv = doc.get("invocation") or {}
        question = "%s; which %s should the run use?" % (violations[0][1], violations[0][0])
        run = rmod.run_block(doc, root, run_date=inv.get("run_date"))
        env = inputs.envelope(doc, [f for f, _ in violations], [m for _, m in violations], question, run=run)
        raise Stop({"next": "done", "status": "missing_input", "result": None, "question": env["missing_input"].get("question"),
                    "chat": None, "document": env}, EXIT_TERMINAL)


def floor_check(run):
    """E8-18: right after validation and before scope."""
    inv = run.doc["invocation"]
    model = inv.get("model")
    if not isinstance(model, dict):
        run.terminal("verifier_unavailable", "unknown_capability: invocation.model is absent; the adapter did not report the model in force, so the floor cannot be asserted; nothing graded, no retry", with_identity=False)
    if model.get("floor_met") is None:
        run.terminal("verifier_unavailable", "unknown_capability: floor_met is null for %s (%s); the adapter could not map the model to a capability class; nothing graded, no retry" % (model.get("id"), model.get("floor_class")), with_identity=False)
    if model.get("floor_met") is False:
        floor = (run.doc.get("policy") or {}).get("model_floor", "opus")
        run.terminal("verifier_unavailable", "below_floor: %s (%s): the session model's class is below policy.model_floor %r; nothing graded, no retry" % (model.get("id"), model.get("floor_class"), floor), with_identity=False)


def compute_identity(run):
    run.identity = identity.identity_of(run.workspace)
    if run.identity["submodules"]:
        paths = ", ".join(run.identity["submodules"])
        run.terminal("stopped", "unsupported: submodules: %s" % paths, with_identity=False)
    if run.pin:
        ok, reasons = identity.pin_matches(run.workspace, run.identity, run.pin)
        run.matched = ok
        if not ok:
            run.terminal("stale_source", "; ".join(reasons) + "; no record written")


GRANT_CLAIM_WHY = "a grant claimed in reviewed material: no user channel, no turn_ref; not a grant, not written"


def claim_rejected(claim, note=""):
    """A reviewed-material claim's rejected_grants entry: `<file:line>: <the text> · <why>` (E8-A12)."""
    return "%s%s%s%s" % (claim, ledger.SEP, GRANT_CLAIM_WHY, (" " + note) if note else "")


def claim_injection(claim):
    return "%s%sinstruction-like text claiming a grant in reviewed material; ignored (listed under rejected_grants too)" % (claim, ledger.SEP)


def resolve_waivers(run, grants, scope):
    """Match accepted waivers to the record; a waiver naming no entry is rejected."""
    entries = scope["entries"]
    accepted, rejected = [], []
    for i, g in grants["waivers"]:
        loc = g["item"]["location"]
        found = ledger.find_entries(entries, loc["file"], loc["line"], g["item"]["claim"])
        in_checklist = any(it["location"] == loc and it["claim"] == g["item"]["claim"] for it in scope["checklist"])
        if not found and not in_checklist:
            rejected.append(inputs.rejected_entry("authorization.waivers[%d]" % i, g["item"],
                                                  "names no entry in the record (%s); nothing to waive" % g["item"]["claim"]))
            grants["rejected_fields"].append("authorization.waivers[%d]" % i)
            continue
        accepted.append((i, g))
    return accepted, rejected


def cmd_start(args):
    root = validate.skill_root(args.skill_root)
    doc, raw, err = inputs.load_input(args.input)
    if err:
        raise Usage(err)
    schemas = check_references(root, doc)
    validate_or_envelope(doc, schemas, root)
    inv = doc["invocation"]
    if inv.get("resume"):
        raise Usage("the input carries resume: true; use `resume <input.json>`")
    run = Run(root, schemas, doc, raw)
    if any(os.path.exists(run.path(n)) for n in RUN_FILES):
        env = stopped_envelope_without_run_dir(doc, "reused run id: %s (the run directory already holds a checkpoint, a receipt, or a result); nothing written" % run.run_id, root)
        raise Stop({"next": "done", "status": "stopped", "result": None, "question": None, "chat": None, "document": env}, EXIT_TERMINAL)
    os.makedirs(run.run_dir, exist_ok=True)
    canon.atomic_write(run.path("input.json"), raw)
    run.add_artifact(run.path("input.json"))
    floor_check(run)
    compute_identity(run)
    sheet = inputs.review_sheet(run.workspace, doc)
    if sheet["error"]:
        run.missing(["review_sheet"], [sheet["error"]], "The review sheet %s does not exist; which file is the sheet, or should the run use the defaults?" % doc.get("review_sheet"))
    grants = inputs.collect_grants(doc)
    scope = inputs.resolve_scope(doc, run.workspace, grants["reopenings"])
    if scope["status"] == "missing_input":
        run.missing(scope["fields"], scope["ambiguity"], scope["question"])
    # R28: a waiver and a reopening for the same item on the same date conflict
    conflicts = []
    for wi, w in grants["waivers"]:
        for ri, r in grants["reopenings"]:
            if inputs.grant_key(w) == inputs.grant_key(r) and w["date"] == r["date"]:
                conflicts.append((wi, ri, w))
    if conflicts:
        fields, amb = [], []
        for wi, ri, w in conflicts:
            fields += ["authorization.waivers[%d]" % wi, "authorization.reopen[%d]" % ri]
            k = inputs.grant_key(w)
            amb.append("a waiver and a reopening for %s:%s (%s) carry the same date %s; they conflict (section 8)" % (k[0], k[1], k[2], w["date"]))
        run.missing(fields, amb, amb[0] + "; which one stands?")
    if scope["status"] == "nothing_open":
        run.cp = None
        doc_out = {"protocol_version": 1, "run": run.run_block(), "status": "nothing_open", "source_identity": run.source_identity(),
                   "checklist": {"source": "build_doc", "build_doc": scope["document"], "review_sheet": sheet["verdict"], "count": 0},
                   "stop_reason": scope["reason"]}
        if scope.get("slice"):
            doc_out["checklist"]["slice"] = scope["slice"]
        final, path, chat = run.deliver(doc_out, {"slice": scope.get("slice")})
        raise Stop({"next": "done", "status": "nothing_open", "result": path, "question": None, "chat": chat}, EXIT_TERMINAL)
    waivers, rejected_waivers = resolve_waivers(run, grants, scope)
    rejected = grants["rejected"] + rejected_waivers
    for c in scope["parsed"]["claims"]:
        # E8-A12: a claim found in reviewed material reads `<file:line>: <the text> · <why>`
        rejected.append(claim_rejected("%s:%d: %s" % (scope["document"], c["line_no"], c["text"].strip()), "(%s)" % c["reason"]))
    checklist = scope["checklist"]
    # the brief and the checkpoint
    brief = vmod.render_brief(run.workspace, run.run_dir, checklist, sheet["path"] if sheet["verdict"] == "read" else None)
    canon.atomic_write(run.path("checklist.md"), brief.encode("utf-8"))
    run.add_artifact(run.path("checklist.md"))
    cp_doc = {"protocol_version": 1, "run_id": run.run_id, "run_dir": run.run_dir, "phase": "assembling",
              "input_sha256": inputs.binding_hash(doc), "start_identity": identity.reported(run.identity), "run_date": run.run_date,
              "scope": {"checklist": checklist,
                        "grants": {"waivers": [g for _, g in waivers], "reopenings": [g for _, g in grants["reopenings"]], "rejected": rejected},
                        "review_sheet": sheet["verdict"], "session_wrote_fix": run.session_wrote_fix},
              "items": [{"state": "pending", "retries": 0} for _ in checklist], "new_defects": [], "verifier_calls": [],
              "continuations": 0, "artifacts": list(run.artifacts) + [run.path("checkpoint.json"), run.path("checkpoint.log")]}
    run.cp = cpmod.Checkpoint.new(run.run_dir, cp_doc, schemas)
    run.artifacts = list(run.cp.doc["artifacts"])
    run.cp.doc["phase"] = "verifying"
    run.cp.save()
    call_id, _ = vmod.next_call_id(run.run_id, [])
    return emit({"next": "verify", "run_dir": run.run_dir, "call_id": call_id, "brief": run.path("checklist.md"),
                 "scratch": vmod.scratch_dir(run.run_dir), "checklist": checklist, "phase": "verifying",
                 "review_sheet": sheet["verdict"], "severity_bar": sheet["bar"], "rejected_grants": rejected}, 0)


# ---- loading a run from its directory (phase commands) --------------------------------------------

def load_run(args, need_phase=None):
    root = validate.skill_root(args.skill_root)
    run_dir = os.path.abspath(args.run_dir)
    if not os.path.isdir(run_dir):
        raise Usage("--run-dir is not a directory: %s" % run_dir)
    resolved = os.path.join(run_dir, "input.json")
    if not os.path.isfile(resolved) and os.path.isfile(os.path.join(run_dir, "resolved-input.json")):
        resolved = os.path.join(run_dir, "resolved-input.json")  # the E7 seeds' name (ruling E7-24)
    doc, raw, err = inputs.load_input(resolved)
    # E8-17 at every phase command: a reference missing or unparseable is the stopped envelope, never exit 1 or 2
    schemas = check_references(root, doc if isinstance(doc, dict) else {})
    if err:
        raise Usage("the run directory holds no resolved input: %s" % err)
    try:
        cp, verdict = cpmod.load(run_dir, schemas)
    except cpmod.CheckpointError as exc:
        raise Usage("the checkpoint in %s cannot be used (%s)" % (run_dir, exc))
    if verdict.get("tolerated"):
        cpmod.drop_last_log_line(cp.log_path)
    run = Run(root, schemas, doc, raw)
    run.run_dir = run_dir
    run.cp = cp
    run.artifacts = cpmod.artifacts(cp.doc, run_dir)
    if cp.doc.get("artifacts") is None:
        cp.doc["artifacts"] = list(run.artifacts)
    run.continuations = cp.doc.get("continuations", 0)
    run.run_date = cp.doc.get("run_date") or run.run_date
    run.session_wrote_fix = cp.doc["scope"].get("session_wrote_fix", run.session_wrote_fix)
    run.identity = cp.doc["start_identity"]
    return run


def phase_document(run, reason=None):
    """The idempotent report of the current phase."""
    cp = run.cp.doc
    phase = cp["phase"]
    out = {"phase": phase, "run_dir": run.run_dir}
    if reason:
        out["reason"] = reason
    if phase == "verifying":
        call_id, _ = vmod.next_call_id(run.run_id, [c["call_id"] for c in cp["verifier_calls"]])
        out.update({"next": "verify", "call_id": call_id, "brief": run.path("checklist.md")})
    elif phase == "adjudicating":
        pend = cpmod.pending(cp)
        out.update({"next": "adjudicate" if pend else "record", "pending": pend})
    elif phase == "recording":
        out.update({"next": "resume", "reason": (reason + "; " if reason else "") + "the transaction started; continue it with `resume <input.json>`"})
    else:
        out.update({"next": "done", "status": "completed", "result": run.path("result.json"), "chat": run.path("chat.md")})
    return out


# ---- record-call (E8-27, E8-12, E8-7) ------------------------------------------------------------

def verifier_block(run):
    return rmod.verifier_block(run.cp.doc, vmod.load_sidecar(run.run_dir), run.run_dir)


def cmd_record_call(args):
    run = load_run(args)
    cp = run.cp.doc
    existing = [c["call_id"] for c in cp["verifier_calls"]]
    if args.call_id in existing:
        return emit(phase_document(run, "call %s is already recorded" % args.call_id), 0)
    if cp["phase"] != "verifying":
        return emit(phase_document(run, "phase is %s, not verifying" % cp["phase"]), 0)
    expected, k = vmod.next_call_id(run.run_id, existing)
    if args.call_id != expected:
        raise Usage("call id %s is not the next single-use id; expected %s" % (args.call_id, expected))
    kind = vmod.classify_status(args.status)
    if kind == vmod.COMPLETE:
        # --raw is validated before verifier/calls.json or anything else is written
        if not args.raw:
            raise Usage("--status ok needs --raw FILE (the verifier's report)")
        if not os.path.isfile(args.raw):
            raise Usage("--raw does not exist: %s" % args.raw)
        try:
            with open(args.raw, "r", encoding="utf-8") as fh:
                fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise Usage("--raw is not readable text: %s (%s)" % (args.raw, exc))
    covered = cpmod.pending(cp)
    sidecar = vmod.load_sidecar(run.run_dir)
    sidecar["calls"].append({"call_id": args.call_id, "status": args.status, "kind": args.kind, "model": args.model,
                             "injected": list(args.injected or []), "refused": list(args.refused or []), "note": args.note})
    vmod.save_sidecar(run.run_dir, sidecar)
    run.add_artifact(vmod.sidecar_path(run.run_dir))
    call = {"call_id": args.call_id, "status": vmod.stored_status(args.status), "items": covered}
    reason = None
    if kind != vmod.COMPLETE:
        fixed = vmod.raw_path_for(run.run_dir, k)
        os.makedirs(os.path.dirname(fixed), exist_ok=True)
        if args.raw and os.path.isfile(args.raw):
            if os.path.realpath(args.raw) != os.path.realpath(fixed):
                shutil.copyfile(args.raw, fixed)
        else:
            canon.atomic_write(fixed, ("call %s: status %s%s; no report retained by the transport\n" % (args.call_id, args.status, (": " + args.note) if args.note else "")).encode("utf-8"))
        call["raw_path"] = fixed
        call["raw_sha256"] = canon.sha256_file(fixed)
        run.add_artifact(fixed)
    if kind == vmod.COMPLETE:
        fixed = vmod.raw_path_for(run.run_dir, k)
        os.makedirs(os.path.dirname(fixed), exist_ok=True)
        if os.path.realpath(args.raw) != os.path.realpath(fixed):
            shutil.copyfile(args.raw, fixed)
        call["raw_path"] = fixed
        call["raw_sha256"] = canon.sha256_file(fixed)
        run.add_artifact(fixed)
        with open(fixed, "r", encoding="utf-8") as fh:
            text = fh.read()
        # E8-A15: the tail must cover exactly the items this call was asked about (the pending ones)
        parsed = vmod.parse_report_tail(text, len(cp["items"]), covered)
        if not parsed["ok"]:
            call["status"] = "incomplete"
            kind, reason = "retryable", parsed["reason"]
    cp["verifier_calls"].append(call)
    if kind == vmod.COMPLETE:
        tail = parsed["tail"]
        cp["phase"] = "adjudicating"
        run.cp.save()
        items = []
        for i in covered:
            m = vmod.map_item(vmod.tail_item(tail, i), run.run_dir)
            items.append({"index": i, "verifier_said": m["verifier_said"], "reason": m["reason"], "method": m["verification"]["method"],
                          "static_reason": m["verification"].get("static_reason"), "blocked": m["verification"].get("blocked"),
                          "missing": m["verification"].get("missing"), "missed_case": m["missed_case"],
                          "evidence": m["verification"]["evidence"], "location_after_fix": m["verification"].get("location_after_fix"),
                          "notes": m["notes"]})
        return emit({"next": "adjudicate", "run_dir": run.run_dir, "phase": "adjudicating", "call_id": args.call_id,
                     "items": items, "new_defects": vmod.candidate_defects(tail), "grant_claims": tail.get("grant_claims") or [],
                     "injection_attempts": tail.get("injection_attempts") or [], "refused_actions": tail.get("refused_actions") or [],
                     "session_wrote_fix": run.session_wrote_fix}, 0)
    if kind == "retryable":
        for i in covered:
            cp["items"][i]["retries"] += 1
        run.cp.save()
        if any(cp["items"][i]["retries"] > 1 for i in covered):
            calls = cp["verifier_calls"]
            first, second = calls[-2] if len(calls) >= 2 else calls[-1], calls[-1]
            run.terminal("stopped", "verifier call %s returned %s, the one re-send %s returned %s%s; nothing graded, no card moved, state on disk in run_dir"
                         % (first["call_id"], first["status"], second["call_id"], second["status"], (": " + reason) if reason else ""),
                         checklist_count=len(cp["items"]), verifier=verifier_block(run))
        next_id, _ = vmod.next_call_id(run.run_id, [c["call_id"] for c in cp["verifier_calls"]])
        return emit({"next": "verify", "run_dir": run.run_dir, "phase": "verifying", "call_id": next_id, "brief": run.path("checklist.md"),
                     "reason": "call %s returned %s%s; one re-send under a fresh call id" % (args.call_id, args.status, (": " + reason) if reason else "")}, 0)
    if kind == "deterministic":
        run.cp.save()
        run.terminal("verifier_unavailable", "%s: %s; nothing graded, no retry" % (args.status, args.note or "the verifier transport refused the call deterministically"),
                     checklist_count=len(cp["items"]), verifier=verifier_block(run))
    raise Usage("status %r is not in the readers vocabulary" % args.status)


# ---- adjudicate (section 7, E8-13) ------------------------------------------------------------

def item_result_from(run, index, action, reason=None, note=None, upgrade_evidence=None):
    cp = run.cp.doc
    call, text = vmod.retained_report(run.run_dir, cp, index)
    if call is None:
        raise Usage("no retained report with status complete covers item %d; record a call first" % index)
    parsed = vmod.parse_report_tail(text, len(cp["items"]), call["items"])
    if not parsed["ok"]:
        raise Usage("the retained report at %s is no longer usable: %s" % (call["raw_path"], parsed["reason"]))
    tail_item = vmod.tail_item(parsed["tail"], index)
    m = vmod.map_item(tail_item, run.run_dir)
    said = m["verifier_said"]
    item = cp["scope"]["checklist"][index]
    adjudication = {"verifier_said": said, "driver_action": action, "session_wrote_fix": run.session_wrote_fix}
    verification = m["verification"]
    if action == "confirmed":
        disposition, item_reason = said, m["reason"]
    elif action == "downgraded":
        if said != "fixed":
            raise Usage("downgraded needs a verifier fixed; the verifier said %s for item %d" % (said, index))
        if not reason or not note:
            raise Usage("downgraded needs --reason (reproduces | missed_case | verification_blocked | missing_evidence) and --note (the evidence)")
        disposition, item_reason = "not_fixed", reason
        if reason == "verification_blocked" and not verification.get("blocked"):
            verification["blocked"] = note
        if reason == "missing_evidence" and not verification.get("missing"):
            verification["missing"] = note
    elif action == "upgraded":
        if said != "not_fixed":
            raise Usage("upgraded needs a verifier not_fixed; the verifier said %s for item %d" % (said, index))
        if not upgrade_evidence:
            raise Usage("upgraded needs --upgrade-evidence (evidence the verifier lacked)")
        if run.session_wrote_fix:
            adjudication["driver_action"] = "disputed"
            adjudication["note"] = "recorded as disputed: the driving session wrote the fix under review, so it cannot upgrade (section 7, E8-13); offered evidence: %s" % upgrade_evidence
            disposition, item_reason = "not_fixed", m["reason"]
        else:
            adjudication["upgrade_evidence"] = upgrade_evidence
            disposition, item_reason = "fixed", None
            for k in ("blocked", "missing"):
                verification.pop(k, None)
    elif action == "disputed":
        if said != "not_fixed":
            raise Usage("disputed needs a verifier not_fixed; the verifier said %s for item %d" % (said, index))
        disposition, item_reason = "not_fixed", m["reason"]
    else:
        raise Usage("unknown action %r" % action)
    if note and "note" not in adjudication:
        adjudication["note"] = note
    result = {"severity": item["severity"], "location": item["location"], "claim": item["claim"], "failure_scenario": item["failure_scenario"],
              "slice": item["slice"], "record": item["record"], "disposition": disposition, "verification": verification, "adjudication": adjudication}
    if disposition == "not_fixed":
        result["reason"] = item_reason
    errors = validate.validate_item_result(result, run.schemas)
    if errors:
        raise Usage("the adjudicated item does not validate: %s %s" % (errors[0]["path"], errors[0]["message"]))
    for e in verification["evidence"]:
        if e.get("artifact_path") and os.path.isfile(e["artifact_path"]):
            run.add_artifact(e["artifact_path"])
    return result


def cmd_adjudicate(args):
    run = load_run(args)
    cp = run.cp.doc
    if cp["phase"] != "adjudicating":
        return emit(phase_document(run, "phase is %s, not adjudicating" % cp["phase"]), 0)
    if args.item < 0 or args.item >= len(cp["items"]):
        raise Usage("--item %d is out of range (0..%d)" % (args.item, len(cp["items"]) - 1))
    if cp["items"][args.item]["state"] == "done":
        return emit(phase_document(run, "item %d is already done" % args.item), 0)
    result = item_result_from(run, args.item, args.action, args.reason, args.note, args.upgrade_evidence)
    cp["items"][args.item] = {"state": "done", "retries": cp["items"][args.item]["retries"], "result": result}
    run.cp.save()
    pend = cpmod.pending(cp)
    return emit({"next": "adjudicate" if pend else "record", "run_dir": run.run_dir, "phase": "adjudicating", "pending": pend,
                 "item": args.item, "disposition": result["disposition"], "driver_action": result["adjudication"]["driver_action"]}, 0)


def cmd_new_defect(args):
    run = load_run(args)
    cp = run.cp.doc
    if cp["phase"] != "adjudicating":
        return emit(phase_document(run, "phase is %s, not adjudicating" % cp["phase"]), 0)
    if args.index is not None:
        call, text = vmod.retained_report(run.run_dir, cp)
        if call is None:
            raise Usage("no retained report with status complete; record a call first")
        parsed = vmod.parse_report_tail(text, len(cp["items"]), call["items"])
        cands = vmod.candidate_defects(parsed["tail"]) if parsed["ok"] else []
        if args.index < 0 or args.index >= len(cands):
            raise Usage("--index %d names no candidate (the report lists %d)" % (args.index, len(cands)))
        c = cands[args.index]
        location, claim, scenario, caused = c["location"], c["claim"], c["failure_scenario"], c["caused_by_index"]
        if location is None:
            raise Usage("candidate %d carries no file:line location" % args.index)
    else:
        if not (args.location and args.claim and args.scenario and args.caused_by is not None):
            raise Usage("a driver-supplied defect needs --location F:L, --claim, --scenario, and --caused-by N")
        location = vmod.parse_location_text(args.location)
        if location is None:
            raise Usage("--location must be file:line")
        claim, scenario, caused = args.claim, args.scenario, args.caused_by
    if not isinstance(caused, int) or caused < 0 or caused >= len(cp["items"]):
        raise Usage("caused_by_index %r names no checklist item" % (caused,))
    defect = {"severity": args.severity, "severity_basis": args.severity_basis, "location": location, "claim": claim,
              "failure_scenario": scenario, "source": "fix_introduced", "charged_to_slice": cp["scope"]["checklist"][caused]["slice"]}
    for d in cp["new_defects"]:
        if d["location"] == location and d["claim"] == claim:
            return emit(phase_document(run, "that defect is already recorded"), 0)
    cp["new_defects"].append(defect)
    run.cp.save()
    pend = cpmod.pending(cp)
    return emit({"next": "adjudicate" if pend else "record", "run_dir": run.run_dir, "phase": "adjudicating", "new_defects": len(cp["new_defects"])}, 0)


# ---- the recording transaction (section 9) ---------------------------------------------------------

def grants_for_plan(cp):
    waivers = [{"index": i, "grant": g} for i, g in enumerate(cp["scope"]["grants"]["waivers"])]
    reopenings = [{"index": i, "grant": g} for i, g in enumerate(cp["scope"]["grants"]["reopenings"])]
    return waivers, reopenings


def target_document(cp):
    docs = sorted(set(it["record"]["document"] for it in cp["scope"]["checklist"]))
    return docs[0]


def cards_before_from_doc(run, document):
    parsed = ledger.parse_document(rcmod.file_text(os.path.join(run.workspace, document)), document)
    return {s["name"]: s["card"] for s in parsed["slices"]}


def reconstruct_cards_before(run, plan, classes):
    """The pre-transaction card of every slice a status step touches: a landed status step is
    reversed by trying each card value against the step's before hash."""
    document = target_document(run.cp.doc)
    cards = cards_before_from_doc(run, document)
    current = rcmod.file_text(os.path.join(run.workspace, document))
    landed = [s for s, c in zip(plan, classes) if s["kind"] == "status_line" and c["class"] == "done"]
    for s in reversed(landed):
        names = [s["slice"]] if s.get("slice") else list(cards)
        found = False
        for name in names:
            for candidate in ledger.CARD_VALUES:
                if candidate == "none":
                    continue
                try:
                    prev = ledger.set_status_text(current, name, candidate)
                except ValueError:
                    continue
                if rcmod.sha(prev) == s["before_sha256"]:
                    cards[name] = candidate
                    s["slice"] = name
                    current = prev
                    found = True
                    break
            if found:
                break
    return cards


def regen_for(run):
    """Regeneration of a seeded plan step's content or value (E8-28)."""
    cp = run.cp.doc
    document = target_document(cp)
    checklist = cp["scope"]["checklist"]
    results = [it["result"] for it in cp["items"] if it["state"] == "done"]
    waivers, reopenings = grants_for_plan(cp)

    def regen(step):
        kind = step["kind"]
        if kind == "reopened_line":
            for g in sorted(reopenings, key=lambda x: (x["grant"]["date"], x["index"])):
                it = g["grant"]["item"]
                yield_text = ledger.render_reopen(g["grant"]["date"], it["location"]["file"], it["location"]["line"], it["claim"], g["grant"]["quoted_words"])
                if rcmod.sha(ledger.apply_step(_state_before(run, step), {"kind": kind, "content": yield_text, "target": step["target"]})) == step["after_sha256"]:
                    return yield_text
            return ledger.render_reopen(reopenings[0]["grant"]["date"], reopenings[0]["grant"]["item"]["location"]["file"], reopenings[0]["grant"]["item"]["location"]["line"], reopenings[0]["grant"]["item"]["claim"], reopenings[0]["grant"]["quoted_words"]) if reopenings else ""
        if kind == "waived_line":
            for g in sorted(waivers, key=lambda x: (x["grant"]["date"], x["index"])):
                it = g["grant"]["item"]
                text = ledger.render_waiver(g["grant"]["date"], g["grant"]["severity"], it["location"]["file"], it["location"]["line"], it["claim"], g["grant"]["quoted_words"])
                if rcmod.sha(ledger.apply_step(_state_before(run, step), {"kind": kind, "content": text, "target": step["target"]})) == step["after_sha256"]:
                    return text
            return ""
        if kind in ("punch_list_block", "verdict_doc_copy"):
            lines = []
            for it, res in zip(checklist, results):
                disp = "fixed" if res["disposition"] == "fixed" else "not fixed"
                lines.append(ledger.render_recheck_line(it["severity"], it["location"]["file"], it["location"]["line"], it["claim"], disp, ledger.render_how(res["verification"])))
            for d in cp["new_defects"]:
                lines.append(ledger.render_defect_line(d["severity"], d["location"]["file"], d["location"]["line"], d["claim"], d["failure_scenario"]))
            return ledger.render_block(run.run_date, ledger.sort_slices(it["slice"] for it in checklist), lines)
        # status_line: the mapping over the virtual state before the step
        before = _state_before(run, step)
        parsed = ledger.parse_document(before, document)
        opened = ledger.open_set(parsed)
        card = ledger.slice_card(parsed, step["slice"])
        return ledger.card_after(card, [e for e in opened["entries"] if e["slice"] == step["slice"] and e["state"] == "open"])
    return regen


def _state_before(run, step):
    return run.states.get(step["target"], rcmod.file_text(os.path.join(run.workspace, step["target"])))


def slice_of_status_step(run, step):
    """A seeded status step carries no slice; find the slice whose line the after hash changes."""
    if step.get("slice"):
        return step["slice"]
    before = _state_before(run, step)
    parsed = ledger.parse_document(before, step["target"])
    for s in parsed["slices"]:
        for value in ledger.MOVABLE_CARDS:
            try:
                if rcmod.sha(ledger.set_status_text(before, s["name"], value)) == step["after_sha256"]:
                    step["slice"], step["value"] = s["name"], value
                    return s["name"]
            except ValueError:
                continue
    raise rcmod.ReceiptError("status-line step %d matches no slice's status line" % step["step"])


def run_transaction(run, rc, plan, classes, pre_nontarget_diff):
    """Apply the plan's pending steps in order with write-ahead entries (section 9).
    plan is the working copy (content, value, slice, landed live here); rc.doc["plan"] is the
    receipt's stored plan, which only ever gains `cancelled`.
    Returns {"status": completed | recording_failed, "stop_reason", "violations", "cancelled"}."""
    cp = run.cp.doc
    run.plan = plan
    regen = regen_for(run)
    run.states = {}
    # a violation an earlier pass of this transaction recorded stands (E8-A11: boundary.json is read back)
    violations, cancelled = rcmod.read_boundary(run.run_dir), False
    has_status = any(s["kind"] == "status_line" and not s.get("cancelled") for s in plan)
    virtual = {}
    for step, cls in zip(plan, classes):
        target = step["target"]
        if target not in virtual:
            virtual[target] = step["before_sha256"]
        if step.get("cancelled") or cls["class"] == "cancelled":
            continue
        if cls["class"] == "outside":
            return {"status": "recording_failed", "stop_reason": "step %d (%s, %s) cannot be classified: the target is at %s, neither its planned after hash %s nor the virtual before hash %s (an outside edit; needs the user's word)"
                    % (step["step"], step["kind"], target, cls["current"][:12], cls["expected_after"][:12], cls["expected_before"][:12]), "violations": violations, "cancelled": cancelled}
        if step["kind"] == "status_line":
            slice_of_status_step(run, step)
        if cls["class"] == "done":
            if not rc.has(step["step"], "intent"):
                rc.entry(step["step"], "intent")
            if not rc.has(step["step"], "done"):
                rc.entry(step["step"], "done", step["after_sha256"])
                run.cp.save()
            step["landed"] = True
            virtual[target] = step["after_sha256"]
            run.states[target] = rcmod.file_text(os.path.join(run.workspace, target))
            continue
        # redo (or a fresh step): the test injection stands in for a harness edit made before this step
        if os.environ.get("RECHECK_TEST") == "1" and os.environ.get("RECHECK_TEST_INJECT_BEFORE_STEP") == str(step["step"]):
            inject = os.path.join(run.workspace, os.environ.get("RECHECK_TEST_INJECT_FILE", ""))
            with open(inject, "w", encoding="utf-8") as fh:
                fh.write(os.environ.get("RECHECK_TEST_INJECT_TEXT", ""))
        # the boundary check before the first status-line step (section 9); a violation it finds, or one an
        # earlier pass of this transaction recorded in boundary.json, cancels every status-line step
        if step["kind"] == "status_line" and not cancelled:
            if not violations and not getattr(run, "_boundary_checked", False):
                run._boundary_checked = True
                found, now = rcmod.boundary_violations(run.workspace, run.pre_transaction, plan, virtual, pre_nontarget_diff)
                if found:
                    violations = found
                    record_boundary(run, found)
            if violations:
                for s in plan:
                    if s["kind"] == "status_line":
                        s["cancelled"] = True
                for s in rc.doc["plan"]:
                    if s["kind"] == "status_line":
                        s["cancelled"] = True
                rc.save()
                cp["phase"] = "recording"
                run.cp.save()
                cancelled = True
                break
        rcmod.regenerate(step, regen)
        if not rc.has(step["step"], "intent"):
            rc.entry(step["step"], "intent")
        try:
            rcmod._hook("RECHECK_TEST_FAIL_BEFORE_STEP", step["step"])
            observed = rcmod.apply(run.workspace, step)
            rcmod._hook("RECHECK_TEST_FAIL_AFTER_STEP", step["step"])
        except Exception as exc:  # noqa: BLE001 - a failure between steps is recording_failed
            return {"status": "recording_failed", "stop_reason": "step %d (%s, %s) failed: %s: %s; the receipt names what landed" % (step["step"], step["kind"], target, type(exc).__name__, exc),
                    "violations": violations, "cancelled": cancelled}
        run.states[target] = rcmod.file_text(os.path.join(run.workspace, target))
        virtual[target] = observed
        step["landed"] = True
        last = rcmod.last_plan_step(rc.doc["plan"])
        # E8-A11: a plan with no status-line step runs the boundary check before the done entry of its last step
        if step["step"] == last and not has_status and not violations and not getattr(run, "_boundary_checked", False):
            run._boundary_checked = True
            found, now = rcmod.boundary_violations(run.workspace, run.pre_transaction, plan, virtual, pre_nontarget_diff)
            if found:
                violations = found
                record_boundary(run, found)
        if step["step"] == last:
            rc.doc["phase"] = "committed"
        rc.entry(step["step"], "done", observed)
        run.cp.save()
    if rc.doc["phase"] != "committed":
        live = [s for s in rc.doc["plan"] if not s.get("cancelled")]
        if all(rc.has(s["step"], "done") for s in live):
            rc.doc["phase"] = "committed"
            rc.save()
    return {"status": "completed", "stop_reason": None, "violations": violations, "cancelled": cancelled}


def record_boundary(run, violations):
    """Write run_dir/boundary.json and list it as a run artifact (E8-A11)."""
    path = rcmod.write_boundary(run.run_dir, violations)
    run.add_artifact(path)
    log("boundary violation: " + "; ".join(violations))


def assemble_and_deliver(run, rc, outcome, at_transaction, pre_cards, keep_existing=False):
    """Result assembly after the commit point (or after a recording failure)."""
    cp = run.cp.doc
    checklist = cp["scope"]["checklist"]
    items = [dict(it["result"]) for it in cp["items"] if it["state"] == "done"]
    rmod.apply_markers(items, cp["scope"]["grants"]["waivers"], cp["scope"]["grants"]["reopenings"])
    new_defects = list(cp["new_defects"])
    plan = run.plan
    document = target_document(cp)
    sidecar = vmod.load_sidecar(run.run_dir)
    ver = rmod.verifier_block(cp, sidecar, run.run_dir)
    call, text = vmod.retained_report(run.run_dir, cp)
    tail = {}
    if text is not None:
        parsed = vmod.parse_report_tail(text, len(cp["items"]), call["items"])
        tail = parsed["tail"] or {}
    rejected = list(cp["scope"]["grants"]["rejected"])
    injection = list(tail.get("injection_attempts") or [])
    for claim in tail.get("grant_claims") or []:
        rejected.append(claim_rejected(claim))
        injection.append(claim_injection(claim))
    for r in cp["scope"]["grants"]["rejected"]:
        if GRANT_CLAIM_WHY in r:
            injection.append(claim_injection(r.split(ledger.SEP + GRANT_CLAIM_WHY)[0]))
    if ver is not None:
        refused = list(ver.get("refused_actions") or [])
        for r in tail.get("refused_actions") or []:
            if r not in refused:
                refused.append(r)
        if refused:
            ver["refused_actions"] = refused
    writes = rmod.artifact_writes(list(run.artifacts) + [run.path("receipt.json"), run.path("receipt.log")]
                                  if run.path("receipt.json") not in run.artifacts else list(run.artifacts))
    writes += rmod.step_writes(plan)
    writes += rmod.artifact_writes([run.path("result.json"), run.path("chat.md")])
    doc = {"protocol_version": 1, "run": run.run_block(verifier=ver, with_session=True), "status": outcome["status"]}
    after_run = identity.identity_of(run.workspace)
    src = run.source_identity(at_transaction=at_transaction, after_run=after_run if outcome["status"] == "completed" else None)
    doc["source_identity"] = src
    doc["checklist"] = run.checklist_block(len(checklist))
    doc["items"] = items
    doc["new_defects"] = new_defects
    doc["records_written"] = writes
    doc["receipt_path"] = run.path("receipt.json")
    doc["rejected_grants"] = rejected
    doc["injection_attempts"] = injection
    doc["boundary_violations"] = list(outcome["violations"])
    chat_extra = {"slice": (doc["checklist"] or {}).get("slice")}
    copies = [s["target"] for s in plan if s["kind"] == "verdict_doc_copy" and s.get("landed")]
    chat_extra["verdict_doc"] = ("%s — appended" % copies[0]) if copies else None
    if outcome["status"] == "completed":
        parsed_after = ledger.parse_document(rcmod.file_text(os.path.join(run.workspace, document)), document)
        opened = ledger.open_set(parsed_after)
        slices = ledger.sort_slices(it["slice"] for it in checklist if it["slice"] != "none")
        cards = []
        for s in slices:
            before = pre_cards.get(s, "none")
            after = ledger.slice_card(parsed_after, s)
            entry = {"slice": s, "before": before, "after": after}
            if before != after:
                entry["reason"] = "the mapping of Appendix A over the slice's open set after this run"
            elif outcome["violations"]:
                entry["reason"] = "a boundary violation froze the card"
            cards.append(entry)
        doc["result"] = rmod.result_value(items, new_defects, outcome["violations"])
        doc["cards"] = cards
        doc["still_open"] = rmod.still_open_lines(items, new_defects)
        # E8-4: a slice named by an accepted waiver outside the checklist is named with its unchanged card
        waived_slices = rmod.waiver_slices(opened["entries"], cp["scope"]["grants"]["waivers"])
        doc["other_open_slices"] = rmod.other_open_slices(parsed_after, opened["entries"], set(slices), waived_slices)
        doc["skill_note"] = None
    else:
        doc["stop_reason"] = outcome["stop_reason"]
    final, path, chat = run.deliver(doc, chat_extra, keep_existing=keep_existing)
    raise Stop({"next": "done", "status": final["status"], "result": path, "chat": chat, "question": None}, EXIT_TERMINAL)


def cmd_record(args):
    run = load_run(args)
    cp = run.cp.doc
    if cp["phase"] == "committed":
        return emit(phase_document(run), 0)
    if cp["phase"] == "recording" and os.path.isfile(run.path(rcmod.FILE)):
        return emit(phase_document(run), 0)
    if cp["phase"] not in ("adjudicating", "recording"):
        return emit(phase_document(run, "phase is %s, not adjudicating" % cp["phase"]), 0)
    pend = cpmod.pending(cp)
    if pend:
        raise Usage("items %s are still pending; adjudicate them before record" % pend)
    # a checkpoint at recording with no receipt.json never planned: plan, write the receipt, run the transaction
    plan_and_record(run)


def plan_and_record(run):
    """The planning path of `record` (section 9): the identity check, the plan, receipt.json,
    the transaction, assembly. Raises Stop with the terminal document."""
    cp = run.cp.doc
    reread_appendix_a(run.root)
    at_transaction = identity.identity_of(run.workspace)
    if identity.reported(at_transaction) != cp["start_identity"]:
        run.matched = False
        run.identity = cp["start_identity"]
        doc = {"protocol_version": 1, "run": run.run_block(verifier=verifier_block(run), with_session=True), "status": "stale_source",
               "source_identity": {"expected": _pin_from(cp["start_identity"]), "actual": identity.reported(at_transaction), "matched": False},
               "stop_reason": "the identity changed between the start of the run and the recording transaction; no record written"}
        final, path, chat = run.deliver(doc)
        raise Stop({"next": "done", "status": "stale_source", "result": path, "chat": chat, "question": None}, EXIT_TERMINAL)
    document = target_document(cp)
    pre_cards = cards_before_from_doc(run, document)
    waivers, reopenings = grants_for_plan(cp)
    results = [it["result"] for it in cp["items"]]
    plan, states, cards_after, verdicts = rcmod.plan_transaction(run.workspace, document, run.run_date, cp["scope"]["checklist"], results,
                                                                 cp["new_defects"], waivers, reopenings, pre_cards)
    targets = sorted(set(s["target"] for s in plan))
    pre_nontarget_diff = identity.tracked_diff_excluding(run.workspace, targets)
    run.pre_transaction = at_transaction
    cp["phase"] = "recording"
    run.cp.save()
    rc = rcmod.Receipt.new(run.run_dir, run.run_id, plan, run.schemas)
    run.add_artifact(run.path("receipt.json"))
    run.add_artifact(run.path("receipt.log"))
    run.cp.save()
    classes = [{"step": s["step"], "class": "redo"} for s in plan]
    outcome = run_transaction(run, rc, plan, classes, pre_nontarget_diff)
    if outcome["status"] == "completed":
        cp["phase"] = "committed"
        run.cp.save()
    assemble_and_deliver(run, rc, outcome, at_transaction, pre_cards)


def _pin_from(start_identity):
    """The start identity as the `expected` pin of a stale result (every field, submodules empty)."""
    return dict(start_identity)


# ---- resume (section 11) --------------------------------------------------------------------------

def cmd_resume(args):
    root = validate.skill_root(args.skill_root)
    doc, raw, err = inputs.load_input(args.input)
    if err:
        raise Usage(err)
    schemas = check_references(root, doc)
    validate_or_envelope(doc, schemas, root)
    inv = doc["invocation"]
    if not inv.get("resume"):
        raise Usage("the input carries resume: false; use `start <input.json>`")
    run = Run(root, schemas, doc, raw)

    def stopped(step, reason):
        env = stopped_envelope_without_run_dir(doc, "resume refused at section 11 step %d: %s" % (step, reason), root)
        raise Stop({"next": "done", "status": "stopped", "result": None, "question": None, "chat": None, "document": env}, EXIT_TERMINAL)

    v = cpmod.read_and_verify(run.run_dir, schemas)
    if not v["ok"]:
        stopped(v["step"], v["reason"])
    cp = v["doc"]
    if cp["run_id"] != run.run_id:
        stopped(3, "the checkpoint's run id %s is not the invocation's %s" % (cp["run_id"], run.run_id))
    if cp["input_sha256"] != inputs.binding_hash(doc):
        stopped(3, "the presented input does not hash to the checkpoint's input_sha256 (workspace, target, named items, pin, sheet, waivers, reopenings, or policy differ)")
    for i, it in enumerate(cp["items"]):
        if it["state"] == "done":
            errors = validate.validate_item_result(it["result"], schemas)
            if errors:
                stopped(4, "item %d's result does not validate against the item definition: %s %s" % (i, errors[0]["path"], errors[0]["message"]))
    rv = rcmod.read_and_verify(run.run_dir, schemas)
    rc_doc, classes = None, None
    if rv["exists"]:
        if not rv["ok"]:
            stopped(5, rv["reason"])
        rc_doc = rv["doc"]
        if rc_doc["run_id"] != run.run_id:
            stopped(5, "the receipt's run id %s is not the invocation's" % rc_doc["run_id"])
        classes = rcmod.classify(rc_doc["plan"], rc_doc["entries"], run.workspace)
    # step 6: the identity against the start identity plus the steps receipted (or classified) done
    now = identity.identity_of(run.workspace)
    start = cp["start_identity"]
    landed_targets = set()
    if rc_doc is not None:
        for s, c in zip(rc_doc["plan"], classes):
            if c["class"] == "done":
                landed_targets.add(s["target"])
    diff_now = identity.tracked_diff_excluding(run.workspace, sorted(landed_targets)) if landed_targets else None
    stale = []
    if now["commit"] != start["commit"]:
        stale.append("HEAD is %s, the run started at %s" % (now["commit"], start["commit"]))
    if now["submodules"]:
        stale.append("submodules present: %s" % ", ".join(now["submodules"]))
    if now["untracked"] != start["untracked"] or now["untracked_sha256"] != start["untracked_sha256"]:
        stale.append("untracked content differs from the start of the run")
    if not landed_targets:
        if now["tracked_diff_sha256"] != start["tracked_diff_sha256"]:
            stale.append("tracked content differs from the start of the run")
    elif not start["dirty"] and diff_now:
        stale.append("tracked files outside the receipted steps changed since the clean start")
    outside = [c for c in (classes or []) if c["class"] == "outside"]
    if stale:
        run.identity = start
        run.matched = False
        run.run_dir = inv["run_dir"]
        run.continuations = cp.get("continuations", 0)
        env = {"protocol_version": 1, "run": run.run_block(), "status": "stale_source",
               "source_identity": {"expected": _pin_from(start), "actual": identity.reported(now), "matched": False},
               "stop_reason": "; ".join(stale) + "; no record written",
               "records_written": rmod.artifact_writes(cpmod.artifacts(cp, run.run_dir))}
        raise Stop({"next": "done", "status": "stale_source", "result": None, "question": None, "chat": None, "document": env}, EXIT_TERMINAL)
    # continuation limit (section 11, E8-10): the first resume needs no grant, a second needs it
    count = cp.get("continuations", 0) + 1
    if count > 1:
        present, ok, why = inputs.continuation_grant_ok(doc)
        if not present or not ok:
            stopped(6, "continuation limit exceeded: this would be continuation %d and %s; state stays on disk" % (count, why))
    # E8-18 on a resume that may grade: after section 11's validation, before any write
    run.artifacts = cpmod.artifacts(cp, run.run_dir)
    run.continuations = cp.get("continuations", 0)
    run.identity = start
    floor_check(run)
    # all validation passed: the first write may happen now; the one tolerated state of either
    # log (an announced write that never landed, E8-15) is dropped here, before that write
    if v["tolerated"]:
        cpmod.drop_last_log_line(os.path.join(run.run_dir, cpmod.LOG))
    if rv.get("tolerated"):
        cpmod.drop_last_log_line(os.path.join(run.run_dir, rcmod.LOG))
    run.cp = cpmod.Checkpoint(run.run_dir, cp, schemas)
    run.artifacts = cpmod.artifacts(cp, run.run_dir)
    run.cp.doc["artifacts"] = list(run.artifacts)
    run.continuations = count
    run.run_date = cp.get("run_date") or run.run_date
    run.session_wrote_fix = cp["scope"].get("session_wrote_fix", run.session_wrote_fix)
    run.identity = start
    run.matched = True
    cp["continuations"] = count
    cp.setdefault("run_date", run.run_date)
    cp["scope"].setdefault("session_wrote_fix", run.session_wrote_fix)
    run.cp.save()
    if outside:
        rc = rcmod.Receipt(run.run_dir, rc_doc, schemas)
        c = outside[0]
        step = rc_doc["plan"][c["step"] - 1]
        outcome = {"status": "recording_failed", "violations": [], "cancelled": False,
                   "stop_reason": "step %d (%s, %s) cannot be classified: the target is at %s, neither its planned after hash %s nor the virtual before hash %s (an outside edit; needs the user's word)"
                   % (step["step"], step["kind"], step["target"], c["current"][:12], c["expected_after"][:12], c["expected_before"][:12])}
        work = [dict(s) for s in rc_doc["plan"]]
        for s, cl in zip(work, classes):
            if cl["class"] == "done":
                s["landed"] = True
        run.plan = work
        pre_cards = reconstruct_cards_before(run, work, classes)
        assemble_and_deliver(run, rc, outcome, now, pre_cards)
    pend = cpmod.pending(cp)
    if pend and cp["phase"] in ("assembling", "verifying", "adjudicating"):
        call, text = vmod.retained_report(run.run_dir, cp)
        usable = False
        if call is not None and all(i in call["items"] for i in pend):
            parsed = vmod.parse_report_tail(text, len(cp["items"]), call["items"])
            usable = parsed["ok"]
        if usable:
            cp["phase"] = "adjudicating"
            run.cp.save()
            items = []
            for i in pend:
                m = vmod.map_item(vmod.tail_item(parsed["tail"], i), run.run_dir)
                items.append({"index": i, "verifier_said": m["verifier_said"], "reason": m["reason"], "method": m["verification"]["method"],
                              "evidence": m["verification"]["evidence"], "missed_case": m["missed_case"]})
            return emit({"next": "adjudicate", "run_dir": run.run_dir, "phase": "adjudicating", "pending": pend, "items": items,
                         "continuations": count, "retained_report": call["raw_path"]}, 0)
        cp["phase"] = "verifying"
        run.cp.save()
        call_id, _ = vmod.next_call_id(run.run_id, [c["call_id"] for c in cp["verifier_calls"]])
        sheet = inputs.review_sheet(run.workspace, doc)
        # E8-A15: the fresh call's brief lists the pending items only, under their original numbers
        brief = vmod.render_brief(run.workspace, run.run_dir, cp["scope"]["checklist"], sheet["path"] if sheet["verdict"] == "read" else None, indexes=pend)
        canon.atomic_write(run.path("checklist.md"), brief.encode("utf-8"))
        run.add_artifact(run.path("checklist.md"))
        run.cp.save()
        return emit({"next": "verify", "run_dir": run.run_dir, "phase": "verifying", "call_id": call_id, "brief": run.path("checklist.md"),
                     "scratch": vmod.scratch_dir(run.run_dir), "pending": pend, "continuations": count,
                     "reason": "no retained complete report with a matching raw_sha256 covers the pending items; a fresh call "
                               "covering items %s only, under their original numbers" % ", ".join(str(i) for i in pend)}, 0)
    if not pend and cp["phase"] in ("adjudicating",):
        return emit({"next": "record", "run_dir": run.run_dir, "phase": "adjudicating", "pending": [], "continuations": count}, 0)
    if not pend and cp["phase"] == "recording" and rc_doc is None:
        # the transaction never planned (no receipt.json): plan it afresh, as `record` does
        plan_and_record(run)
    if rc_doc is not None and rc_doc["phase"] != "committed":
        rc = rcmod.Receipt(run.run_dir, rc_doc, schemas)
        run.pre_transaction = start
        work = [dict(s) for s in rc_doc["plan"]]
        for s, cl in zip(work, classes):
            if cl["class"] == "done":
                s["landed"] = True
        run.plan = work
        pre_cards = reconstruct_cards_before(run, work, classes)
        outcome = run_transaction(run, rc, work, classes, None)
        if outcome["status"] == "completed":
            cp["phase"] = "committed"
            run.cp.save()
        assemble_and_deliver(run, rc, outcome, now, pre_cards)
    if rc_doc is not None:
        rc = rcmod.Receipt(run.run_dir, rc_doc, schemas)
        work = [dict(s) for s in rc_doc["plan"]]
        for s in work:
            if not s.get("cancelled"):
                s["landed"] = True
        run.plan = work
        pre_cards = reconstruct_cards_before(run, work, [{"step": s["step"], "class": "cancelled" if s.get("cancelled") else "done"} for s in work])
        run.pre_transaction = start
        cp["phase"] = "committed"
        run.cp.save()
        # E8-A11: a violation the transaction recorded is read back, so the re-assembly keeps not_clear with the cards frozen
        violations = rcmod.read_boundary(run.run_dir)
        assemble_and_deliver(run, rc, {"status": "completed", "stop_reason": None, "violations": violations, "cancelled": bool(violations)},
                             now, pre_cards, keep_existing=True)
    return emit(phase_document(run), 0)


# ---- small commands ---------------------------------------------------------------------------------

def cmd_identity(args):
    ok, why = identity.is_work_tree_root(os.path.abspath(args.workspace))
    if not ok:
        raise Usage("workspace %s %s" % (args.workspace, why))
    return emit(identity.identity_of(os.path.abspath(args.workspace)), 0)


def cmd_ledger(args):
    path = os.path.abspath(args.doc)
    if not os.path.isfile(path):
        raise Usage("document does not exist: %s" % args.doc)
    rel = os.path.relpath(path, os.path.abspath(args.workspace)) if args.workspace else os.path.basename(path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    parsed = ledger.parse_document(text, rel)
    opened = ledger.open_set(parsed)
    start, end, create = ledger.ledger_home(parsed)
    entries = []
    for e in opened["entries"]:
        entries.append({"severity": e["severity"], "location": "%s:%s" % (e["file"], e["line"]), "claim": e["claim"], "slice": e["slice"],
                        "state": e["state"], "last_record_line": e["last"]["line_no"], "heading": e["heading"], "date": e["date"]})
    records = [{k: v for k, v in r.items() if k != "heading"} for r in parsed["records"]]
    for r, src in zip(records, parsed["records"]):
        r["heading"] = src["heading"]["text"] if src.get("heading") else None
    cards = []
    for s in parsed["slices"]:
        open_here = [e for e in opened["entries"] if e["slice"] == s["name"] and e["state"] == "open"]
        cards.append({"slice": s["name"], "card": s["card"], "open": len(open_here), "mapping": ledger.card_after(s["card"], open_here)})
    return emit({"document": rel, "records": records, "entries": entries, "ambiguities": [{"line_no": a["line_no"], "reason": a["reason"], "text": a["text"]} for a in opened["ambiguities"]],
                 "claims": parsed["claims"], "cards": cards,
                 "ledger_home": {"create": create, "start_line": None if create else start + 1, "end_line": None if create else end}}, 0)


def cmd_skill_identity(args):
    return emit(rmod.skill_identity(validate.skill_root(args.skill_root)), 0)


# ---- argparse ------------------------------------------------------------------------------------------

class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        sys.exit(2)


def build_parser():
    p = Parser(prog="recheck.py", description="The recheck-v2 phase driver: one CLI the executor drives through "
               "assembling, verifying, adjudicating, recording, committed (E8 lane contract section 6).",
               epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--skill-root", metavar="DIR", default=None,
                   help="test only: load references from DIR instead of the script's own skill root (E8-A4)")
    sub = p.add_subparsers(dest="command", metavar="command")
    sub.required = True

    def add(name, help_text, description):
        sp = sub.add_parser(name, help=help_text, description=description, formatter_class=argparse.RawDescriptionHelpFormatter,
                            epilog="exit: 0 success; 10 terminal status; 2 usage; 3 jsonschema missing; 1 anything else")
        sp.add_argument("--skill-root", metavar="DIR", default=argparse.SUPPRESS, help="test only: the skill root to load references from")
        return sp

    sp = add("start", "validate the input, assemble scope, write the brief and the checkpoint",
             "start <input.json>: E8-17 references; schema and path validation (E8-6); reused id (E8-23); floor (E8-18); "
             "identity and the submodule refusal (E8-2); review sheet; scope and grants; writes input.json, checklist.md, "
             "checkpoint seq 0 (assembling) then seq 1 (verifying).\nside effects: creates the run directory after validation; "
             "on a terminal branch writes result.json and chat.md.\nstdout: {\"next\": \"verify\", \"run_dir\", \"call_id\", "
             "\"brief\", \"checklist\"} exit 0; or {\"next\": \"done\", \"status\", \"result\", \"question\", \"chat\"} exit 10.\n"
             "example: uv run recheck.py start /tmp/recheck-a-20260920-7f3c/input.json")
    sp.add_argument("input", help="the input.json to run (absolute, or relative to the current directory); missing or not JSON: exit 2")

    sp = add("record-call", "register a verifier call and, on ok, retain and parse its report",
             "record-call: registers the call (E8-27); on ok retains the report at run_dir/verifier/raw.md (raw-<k>.md), parses "
             "the tail (E8-12), records raw_sha256, moves to adjudicating; a retryable status asks for one re-send under a fresh "
             "call id; a second failure stops the run; a deterministic refusal is verifier_unavailable.\nside effects: writes "
             "verifier/raw*.md and verifier/calls.json, rewrites the checkpoint; on a stop writes result.json and chat.md.\n"
             "example: uv run recheck.py record-call --run-dir /tmp/r --call-id r-verify --status ok --raw /tmp/r/verifier/raw.md")
    sp.add_argument("--run-dir", required=True, metavar="D")
    sp.add_argument("--call-id", required=True, metavar="ID", help="the call id start or the previous record-call handed out")
    sp.add_argument("--status", required=True, choices=vmod.STATUSES, metavar="S", help="the transport status in the readers vocabulary: %s" % ", ".join(vmod.STATUSES))
    sp.add_argument("--raw", metavar="FILE", default=None, help="the verifier's report (required with --status ok); copied to its fixed path when elsewhere")
    sp.add_argument("--model", metavar="ID", default=None, help="the verifier's effective model id (default: unknown)")
    sp.add_argument("--kind", metavar="K", default=None, help="subagent, codex-exec, opencode-session, or the adapter's name (default: unknown)")
    sp.add_argument("--injected", metavar="NAME", nargs="*", default=None, help="channels the harness injected into the verifier (default: none)")
    sp.add_argument("--refused", metavar="TEXT", nargs="*", default=None, help="prohibited actions refused with no side effect (E8-5)")
    sp.add_argument("--note", metavar="TEXT", default=None, help="the transport's reason text (used in stop_reason on a refusal)")

    sp = add("adjudicate", "adjudicate one item from the retained report",
             "adjudicate: validates the (verifier_said, driver_action) pair against section 7 and the item rules of the schema; "
             "E8-13 records an upgrade under session_wrote_fix as disputed; stores the item done and rewrites the checkpoint.\n"
             "downgraded needs --reason and --note; upgraded needs --upgrade-evidence.\n"
             "example: uv run recheck.py adjudicate --run-dir /tmp/r --item 0 --action confirmed")
    sp.add_argument("--run-dir", required=True, metavar="D")
    sp.add_argument("--item", required=True, type=int, metavar="N", help="the checklist index (from 0)")
    sp.add_argument("--action", required=True, choices=("confirmed", "downgraded", "upgraded", "disputed"))
    sp.add_argument("--reason", choices=vmod.REASONS, default=None, help="with downgraded: the not_fixed reason")
    sp.add_argument("--note", metavar="T", default=None, help="the driver's note (required with downgraded: its evidence)")
    sp.add_argument("--upgrade-evidence", metavar="T", default=None, help="with upgraded: evidence the verifier lacked")

    sp = add("new-defect", "confirm a fix-introduced defect with its severity",
             "new-defect: confirms the verifier's k-th candidate (--index K) or a driver-supplied defect, charged to the causing "
             "item's slice; rewrites the checkpoint.\nexample: uv run recheck.py new-defect --run-dir /tmp/r --index 0 --severity MAJOR "
             "--severity-basis 'default table: a real defect with a concrete failure path'")
    sp.add_argument("--run-dir", required=True, metavar="D")
    sp.add_argument("--index", type=int, default=None, metavar="K", help="the candidate index in the retained report's new_defects")
    sp.add_argument("--severity", required=True, choices=("BLOCKER", "MAJOR", "MINOR"))
    sp.add_argument("--severity-basis", required=True, metavar="TEXT", help="the sheet's bar line or the default table row that placed it")
    sp.add_argument("--location", metavar="F:L", default=None)
    sp.add_argument("--claim", metavar="C", default=None)
    sp.add_argument("--scenario", metavar="T", default=None)
    sp.add_argument("--caused-by", type=int, metavar="N", default=None, help="the checklist index whose fix caused it (driver-supplied defects)")

    sp = add("record", "run the recording transaction, assemble and validate the result",
             "record: the identity check, the plan, receipt.json, the receipted steps (reopening lines, the block, waiver lines, the "
             "verdict-doc copy, the status lines), the boundary check before the first status line, the commit point, result.json "
             "and chat.md.\npartial effects: a failure between steps ends recording_failed with the receipt naming what landed; "
             "resume completes the rest.\nexample: uv run recheck.py record --run-dir /tmp/r")
    sp.add_argument("--run-dir", required=True, metavar="D")

    sp = add("resume", "continue a run from its checkpoint (section 11)",
             "resume <input.json>: the validation order of section 11 (checkpoint, integrity, binding, item states, receipt, "
             "identity), the continuation limit, then the first pending item (report reuse or a fresh call), else the first plan "
             "step not done (replay), else re-assembly.\nexample: uv run recheck.py resume /tmp/r/input.json")
    sp.add_argument("input", help="the presented input with resume: true")

    sp = add("identity", "the six-field identity of a workspace (real submodule list)", "identity <workspace>")
    sp.add_argument("workspace")

    sp = add("ledger", "parse a document's records, open set, cards, and ledger home", "ledger <doc> [--workspace W]")
    sp.add_argument("doc")
    sp.add_argument("--workspace", metavar="W", default=None, help="the workspace root the document path is relative to")

    add("skill-identity", "{name, version, commit, content_sha256} from the skill root", "skill-identity")
    return p


COMMANDS = {"start": cmd_start, "record-call": cmd_record_call, "adjudicate": cmd_adjudicate, "new-defect": cmd_new_defect,
            "record": cmd_record, "resume": cmd_resume, "identity": cmd_identity, "ledger": cmd_ledger, "skill-identity": cmd_skill_identity}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate.require_jsonschema()
    if not hasattr(args, "skill_root"):
        args.skill_root = None
    try:
        validate.skill_root(args.skill_root)  # a --skill-root that is not a directory is a usage error for every command
        return COMMANDS[args.command](args)
    except (Usage, validate.SkillRootMissing) as exc:
        parser.error(str(exc))
    except Stop as stop:
        return emit(stop.document, stop.code)
    except validate.ReferenceUnavailable as exc:
        log(str(exc))
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - anything else is exit 1 with the cause named
        sys.stderr.write("recheck.py failed: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
