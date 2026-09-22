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
otherwise the checkpoint says recording) and the workspace at a receipted step hash; the
checkpoint carries the transaction guard from the moment the transaction began (E8-A45), so a
resume compares the identity and the non-target diff with it rather than with the start;
`resume` classifies every step against the virtual state and completes the rest without a
duplicate append. A checkpoint or receipt rewrite interrupted between the log line and the
rename leaves the one tolerated state (section 11), dropped at the next resume.

The stopped phase (E8-A20): a phase command that delivers stopped, verifier_unavailable,
stale_source, or missing_input rewrites the checkpoint at phase `stopped` with a `terminal`
block (status, stop_reason, resumable) before result.json; every later phase command returns
{"next": "done", "status", "result", "chat", "reason"} with exit 10, writes nothing, and issues
no call id; `resume` continues only a resumable stop (two verifier failures, an unavailable
verifier) as a continuation with a fresh call and refuses every other at section 11 step 1.

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
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from recheck_core import canon, checkpoint as cpmod, identity, inputs, ledger, receipt as rcmod  # noqa: E402
from recheck_core import records_client as rcl, records_view as rview, records_write  # noqa: E402
from recheck_core import result as rmod, validate, verifier as vmod  # noqa: E402

# every section 15 reference, in the order a missing one is named (E8-17); verifier.md joined the list
# at slice 3, when it was written
REQUIRED_REFERENCES = ["references/pilot-contract.md", "references/input.schema.json", "references/result.schema.json",
                       "references/checkpoint.schema.json", "references/receipt.schema.json", "references/verifier.md"]
RUN_FILES = ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log", "result.json")
EXIT_TERMINAL = 10

# E13 3.1: the one records component client of this process, opened in main() after the argument
# check and before any command runs. The pilot reaches the component through this client alone.
RECORDS = []


def records():
    return RECORDS[0]

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
        # E13 slice 1: the transaction's own state — the text the component rendered for this run,
        # the open set it derives after the append, and the cards the document carried before it
        self.rendered = None
        self.open_after = []
        self.pre_cards = {}
        self.plan = []
        self.states = {}
        self.resumed_half = None   # E13 3.5: which half of the transaction a resume had to finish
        self.legacy_receipt = False  # a receipt written before the records moved into the component
        # CR-F1(b): set once the transaction's append has LANDED. A result that then fails
        # validation is not `stopped` with a bare validation message: the append is in the log and
        # the named half cannot be settled, which is `recording_failed`.
        self.recording_half = None

    def harness_name(self):
        """`actor.harness` on every event this run writes: what the adapter reported, or None."""
        harness = (self.doc.get("invocation") or {}).get("harness") or {}
        name = harness.get("name") if isinstance(harness, dict) else None
        return name if isinstance(name, str) and name else None

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

    def artifact_inventory(self, extra=()):
        """E8-A31: every file under run_dir exactly once, result.json and chat.md excluded: the artifacts
        the core wrote by name in their order (extra appended), then every other regular file in sorted
        relative-path order."""
        final = {os.path.realpath(self.path("result.json")), os.path.realpath(self.path("chat.md"))}
        out, seen = [], set()
        for p in list(self.artifacts) + list(extra):
            rp = os.path.realpath(p)
            if rp in seen or rp in final:
                continue
            seen.add(rp)
            out.append(p)
        others = []
        if self.run_dir and os.path.isdir(self.run_dir):
            for root, dirs, files in os.walk(self.run_dir):
                dirs.sort()
                for name in files:
                    p = os.path.join(root, name)
                    rp = os.path.realpath(p)
                    if rp in seen or rp in final:
                        continue
                    seen.add(rp)
                    others.append(p)
        others.sort(key=lambda p: os.path.relpath(p, self.run_dir))
        return out + others

    def deliver(self, doc, chat_extra=None, extra_artifacts=None, keep_existing=False):
        """Write result.json and chat.md, validating first; return (document, path, chat).
        keep_existing: a re-assembly never overwrites a valid result.json with a stopped one."""
        arts = self.artifact_inventory(extra_artifacts or [])
        doc["records_written"] = rmod.artifact_writes(arts + [self.path("result.json"), self.path("chat.md")]) \
            if "records_written" not in doc else doc["records_written"]
        final, path, chat = rmod.deliver(doc, self.run_dir, self.schemas, input_doc=self.doc, workspace=self.workspace,
                                         chat_text=rmod.chat_block(doc, chat_extra), stop_builder=self.stop_builder(arts),
                                         keep_existing=keep_existing, records=RECORDS[0] if RECORDS else None)
        return final, path, chat

    def stop_builder(self, arts):
        def build(reason, extra):
            status = "stopped"
            # CR-F1(b): a run whose append landed and whose document steps can never validate is
            # `recording_failed` with the half named, never `stopped` with a bare validation message.
            if self.recording_half:
                status = "recording_failed"
                reason = "%s; the transaction's append landed and %s cannot be settled from it; the receipt names what landed" % (reason, self.recording_half)
            out = {"protocol_version": 1, "run": self.run_block(), "status": status, "stop_reason": reason}
            if self.identity is not None and not reason.startswith("unsupported: submodules:"):
                out["source_identity"] = self.source_identity()
            if status == "recording_failed":
                out["receipt_path"] = self.path("receipt.json")
            out["records_written"] = rmod.artifact_writes(self.artifact_inventory(list(arts) + list(extra)) + [self.path("result.json"), self.path("chat.md")])
            return out
        return build

    def mark_terminal(self, status, stop_reason, resumable):
        """E8-A20: a phase command that holds a checkpoint ends the phases before result.json is written:
        the checkpoint is rewritten with phase stopped and the terminal block. completed and
        recording_failed are outcomes, not stops, and a run without a checkpoint has nothing to mark."""
        if self.cp is None or status in ("completed", "recording_failed"):
            return
        self.cp.doc["phase"] = "stopped"
        self.cp.doc["terminal"] = {"status": status, "stop_reason": stop_reason or "", "resumable": bool(resumable)}
        self.cp.save()

    def terminal(self, status, stop_reason=None, with_identity=True, checklist_count=None, extra=None, chat_extra=None, verifier=None,
                 resumable=None):
        """resumable (E8-A20): true only for the two-verifier-failures stop and for verifier_unavailable."""
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
        self.mark_terminal(status, stop_reason, status == "verifier_unavailable" if resumable is None else resumable)
        final, path, chat = self.deliver(doc, chat_extra)
        raise Stop({"next": "done", "status": final["status"], "result": path, "question": None, "chat": chat}, EXIT_TERMINAL)

    def missing(self, fields, ambiguity, question=None):
        doc = inputs.envelope(self.doc, fields, ambiguity, question)
        doc["run"] = self.run_block()
        self.mark_terminal("missing_input", "missing: %s%s" % (", ".join(fields), ("; " + "; ".join(ambiguity)) if ambiguity else ""), False)
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
        env = inputs.envelope(doc if isinstance(doc, dict) else {}, fields, amb, schema_errors=errors)
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

# E11-7 item 3: a RECORDED PROJECT STATE is not a claimed grant. A build document's own
# `Status: rejected` line, a punch-list block line, a review finding, a `WAIVED (per user)` or
# `REOPENED (per user)` line already in the record: Appendix A calls each of these a record,
# and the open filter reads them. The mandate asked the verifier to report "a disposition
# claim" and the claim path turned every report into a rejected grant, so eight OpenCode
# attempts failed on a status line the project wrote about itself (Astra's E11 read, section
# 4: "The broad instruction is followed into an incorrect classification of the legitimate
# status record"). Only text ADDRESSED TO THE REVIEWER, asking for a disposition, a waiver, a
# reopening or a scope change, is a claim.
STATUS_LINE_RE = re.compile(r"^Status:\s*(rejected|signed off with conditions|signed off|built|not started)\s*$", re.I)
RECORD_LINE_RE = re.compile(r"^[-*]\s+(?:BLOCKER|MAJOR|MINOR|WAIVED \(per user\)|REOPENED \(per user\))(?=\s|$)")


def recorded_project_state(claim, record_documents):
    """`(True, why)` when a reported grant claim is a record the project wrote about itself.

    The claim's own text carries `<file>:<line>: <the line>`; the line is a record when it
    sits in one of the run's own record documents AND reads as an Appendix A record line or a
    slice's `Status:` line. Anything else stays a claim.
    """
    text = str(claim or "")
    head, _, rest = text.partition(": ")
    file_part, _, line_part = head.rpartition(":")
    if not file_part or not line_part.isdigit():
        return False, "the claim names no <file>:<line> in a record document"
    if file_part not in record_documents:
        return False, "%s is not one of this run's record documents" % file_part
    body = rest.strip()
    if STATUS_LINE_RE.match(body):
        return True, "%s:%s is the slice's own Status line, a record (Appendix A)" % (
            file_part, line_part)
    if RECORD_LINE_RE.match(body) and ledger.SEP in body:
        return True, "%s:%s is a record line of the document's ledger (Appendix A)" % (
            file_part, line_part)
    return False, "the text at %s:%s is not a record line or a Status line" % (file_part,
                                                                              line_part)


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
        found = rview.match_entries(entries, loc["file"], loc["line"], g["item"]["claim"])
        in_checklist = any(it["location"] == loc and it["claim"] == g["item"]["claim"] for it in scope["checklist"])
        if not found and not in_checklist:
            rejected.append(inputs.rejected_entry("authorization.waivers[%d]" % i, g["item"],
                                                  "names no entry in the record (%s); nothing to waive" % g["item"]["claim"]))
            grants["rejected_fields"].append("authorization.waivers[%d]" % i)
            continue
        accepted.append((i, g))
    return accepted, rejected


def cmd_check_input(args):
    """E11-7 item 3: the bounded correction path. One read-only look at the input.

    `start` creates the run directory as soon as the path rules pass, and a run directory
    that holds a result is spent: a semantic fault found after that point (a slice the
    document does not spell that way, a conflict, a missing scenario) costs the run id. The
    E10 campaign spent seven of them on one spelling.

    This command answers the same questions `start` would, writes NOTHING anywhere, and
    names the document's own spelling of every value it could resolve, so the input is
    corrected before a run id is spent. It is one command, not a loop: it grades nothing,
    summons nobody, and never begins a run.
    """
    root = validate.skill_root(args.skill_root)
    doc, raw, err = inputs.load_input(args.input)
    if err:
        raise Usage(err)
    schemas = check_references(root, doc)
    errors = validate.validate_input(doc, schemas)
    if errors:
        return emit({"ok": False, "where": "schema",
                     "fields": inputs.schema_fields(errors, doc, schemas),
                     "errors": [{"path": e["path"] or "$", "message": e["message"]}
                                for e in errors[:12]],
                     "wrote": []}, 0)
    violations = inputs.path_rules(doc, identity.is_work_tree_root)
    if violations:
        return emit({"ok": False, "where": "path_rules", "fields": [v[0] for v in violations],
                     "problems": [v[1] for v in violations], "wrote": []}, 0)
    workspace = doc["workspace"]
    target = doc.get("target") or {}
    out = {"ok": True, "where": "scope", "wrote": [],
           "run_id": (doc.get("invocation") or {}).get("run_id"),
           "run_dir": (doc.get("invocation") or {}).get("run_dir")}
    grants = inputs.collect_grants(doc)
    # CR-2: this command writes nothing anywhere, so the log is read through `import-legacy
    # --dry-run`, which takes no lock and appends nothing. `records_behind` says how many records
    # the document holds that the log still lacks; a `start` would add exactly those.
    try:
        scope = inputs.resolve_scope(doc, workspace, grants["reopenings"], records(), dry_run=True)
    except rview.RecordsStop as stop:
        return emit({"ok": False, "where": "records", "status": stop.status, "reason": stop.reason,
                     "fields": stop.fields, "ambiguity": stop.ambiguity, "wrote": []}, 0)
    out["records_behind"] = scope.get("records_behind", 0)
    out["status"] = scope["status"]
    if scope["status"] == "missing_input":
        out["ok"] = False
        out["fields"] = scope.get("fields")
        out["ambiguity"] = scope.get("ambiguity")
        out["question"] = scope.get("question")
        if scope.get("slice_candidates") is not None:
            out["slice_candidates"] = scope["slice_candidates"]
        return emit(out, 0)
    out["document"] = scope.get("document")
    out["slice"] = scope.get("slice")
    out["slice_as_given"] = scope.get("slice_as_given", target.get("slice"))
    out["slice_resolved_because"] = scope.get("slice_resolved_because")
    out["checklist_count"] = len(scope.get("checklist") or [])
    out["corrected_target"] = dict(target)
    if out["slice"] is not None:
        out["corrected_target"]["slice"] = out["slice"]
    return emit(out, 0)


def resolve_scope_or_stop(run, doc, grants):
    """Scope through the records component (E13 3.2). A component refusal becomes the pilot stop
    the refusal map names (3.4), with the component's own explanation and no project write."""
    try:
        return inputs.resolve_scope(doc, run.workspace, grants["reopenings"], records())
    except rview.RecordsStop as stop:
        records_stop(run, stop)


def records_stop(run, stop, checklist_count=None):
    """Deliver a RecordsStop as the pilot's matching terminal status (brief 3.4).

    Before the transaction only three of the four can arise, and `recording_failed` is not one of
    them: the schema and V8 require a receipt beside a `recording_failed` result, and no plan has
    been made yet. A refusal of the transaction's own `append` is delivered by the transaction,
    which holds the receipt."""
    if stop.status == "missing_input":
        run.missing(stop.fields or ["target.build_doc"], stop.ambiguity or [stop.reason], stop.question)
    if stop.status == "stale_source":
        run.terminal("stale_source", stop.reason + "; no record written", checklist_count=checklist_count)
    run.terminal("stopped", stop.reason, checklist_count=checklist_count)


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
    scope = resolve_scope_or_stop(run, doc, grants)
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
    # E11-45 S2: the input's service-observation requirements are bound onto the checklist items
    # they name, so the rule travels with the ITEM from here on. A requirement that names no
    # item of this checklist is ignored (the run is scoped to a slice; a declaration for an item
    # outside it is not this run's business).
    inputs.bind_service_observations(doc, checklist)
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
    # CR-F1(a): the head the run's open set was read against. `record` compares the log against it
    # BEFORE its own sync, so an event another writer appended between the two phases is a named
    # conflict rather than something the run silently records over.
    pin = records_pin(scope)
    if pin is not None:
        cp_doc["records_pin"] = pin
    try:
        run.cp = cpmod.Checkpoint.new(run.run_dir, cp_doc, schemas)
    except cpmod.CheckpointError as exc:
        # E8-A32: a first checkpoint that would not validate is missing input naming the field, never exit 1
        field = checkpoint_error_field(str(exc))
        run.missing([field], ["the first checkpoint would not validate: %s" % exc],
                    "The record produces a checkpoint that does not validate at %s (%s); supply or confirm the record" % (field, exc))
    run.artifacts = list(run.cp.doc["artifacts"])
    run.cp.doc["phase"] = "verifying"
    run.cp.save()
    call_id, _ = vmod.next_call_id(run.run_id, [])
    return emit({"next": "verify", "run_dir": run.run_dir, "call_id": call_id, "brief": run.path("checklist.md"),
                 "scratch": vmod.scratch_dir(run.run_dir), "checklist": checklist, "phase": "verifying",
                 "review_sheet": sheet["verdict"], "severity_bar": sheet["bar"], "rejected_grants": rejected}, 0)


def checkpoint_error_field(message):
    """The dotted field a CheckpointError's `checkpoint would not validate: <path> <message>` names
    (E8-A32); `$` for the root."""
    m = re.search(r"checkpoint would not validate: (\S*) ", message)
    path = m.group(1) if m else ""
    parts = [int(p) if p.isdigit() else p for p in path.split("/") if p]
    return inputs.field_path(parts) or "$"


# ---- loading a run from its directory (phase commands) --------------------------------------------

def stopped_run_document(run_dir, cp_doc):
    """E8-A20: every phase command on a stopped run returns the recorded outcome, writes nothing,
    and issues no call id."""
    term = cp_doc.get("terminal") or {}
    status = term.get("status", "stopped")
    result, chat = os.path.join(run_dir, "result.json"), os.path.join(run_dir, "chat.md")
    return {"next": "done", "status": status, "result": result if os.path.isfile(result) else None,
            "chat": chat if os.path.isfile(chat) else None,
            "reason": "the run ended as %s: %s" % (status, term.get("stop_reason", ""))}


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
    if cp.doc.get("phase") == "stopped":
        # E8-A20: before any write, the tolerated-state drop included
        raise Stop(stopped_run_document(run_dir, cp.doc), EXIT_TERMINAL)
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


def list_capture(run, capture, fixed):
    """E8-A31: the adapter's original capture is a listed artifact when --raw pointed at a file under
    run_dir/verifier/ other than the fixed raw path."""
    if capture and os.path.realpath(capture) != os.path.realpath(fixed) and inputs.is_under(capture, vmod.scratch_dir(run.run_dir)):
        run.add_artifact(capture)


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
    capture = os.path.abspath(args.raw) if args.raw and os.path.isfile(args.raw) else None
    if kind != vmod.COMPLETE:
        fixed = vmod.raw_path_for(run.run_dir, k)
        os.makedirs(os.path.dirname(fixed), exist_ok=True)
        if capture:
            if os.path.realpath(capture) != os.path.realpath(fixed):
                shutil.copyfile(capture, fixed)
        else:
            canon.atomic_write(fixed, ("call %s: status %s%s; no report retained by the transport\n" % (args.call_id, args.status, (": " + args.note) if args.note else "")).encode("utf-8"))
        call["raw_path"] = fixed
        call["raw_sha256"] = canon.sha256_file(fixed)
        run.add_artifact(fixed)
        list_capture(run, capture, fixed)
    if kind == vmod.COMPLETE:
        fixed = vmod.raw_path_for(run.run_dir, k)
        os.makedirs(os.path.dirname(fixed), exist_ok=True)
        if os.path.realpath(capture) != os.path.realpath(fixed):
            shutil.copyfile(capture, fixed)
        call["raw_path"] = fixed
        call["raw_sha256"] = canon.sha256_file(fixed)
        run.add_artifact(fixed)
        list_capture(run, capture, fixed)
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
            # E8-A20: the two-failures stop is resumable (section 10's bounded recovery)
            run.terminal("stopped", "verifier call %s returned %s, the one re-send %s returned %s%s; nothing graded, no card moved, state on disk in run_dir"
                         % (first["call_id"], first["status"], second["call_id"], second["status"], (": " + reason) if reason else ""),
                         checklist_count=len(cp["items"]), verifier=verifier_block(run), resumable=True)
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
        # E11-45 S3: the stop reason is DERIVED from execution, not taken from the word the
        # verifier typed. The typed word is retained as `reason_as_stated` so the claim stays
        # visible, and an outcome the run cannot decide stays UNRESOLVED rather than falling
        # back to a default. Only a `confirmed` not_fixed goes through here: `downgraded` is
        # the driver's own evidenced action, and a `fixed` item carries no reason at all.
        if disposition == "not_fixed":
            derived = vmod.derive_reason(tail_item, run.run_dir,
                                         call_status=call.get("status"), report_text=text)
            adjudication["reason_as_stated"] = item_reason
            adjudication["reason_derived"] = {
                "reason": derived["reason"], "observed": derived["observed"],
                "how": derived["how"],
            }
            if derived["reason"] is not None and derived["reason"] != item_reason:
                item_reason = derived["reason"]
                if item_reason == "verification_blocked":
                    verification["blocked"] = verification.get("blocked") or derived["how"]
                    verification.pop("missing", None)
                elif item_reason == "missing_evidence":
                    verification["missing"] = verification.get("missing") or derived["how"]
                    verification.pop("blocked", None)
                else:
                    for key in ("blocked", "missing"):
                        verification.pop(key, None)
        # E11 fix round, item 3: contract section 5 — "An execution the sandbox or environment
        # stopped is `verification_blocked`, never `static`." When a retained report of THIS
        # RUN recorded a stopped execution for this item, a later static `fixed` does not
        # remove it: the item stays not_fixed with reason verification_blocked, and the
        # refusal is recorded in the checkpoint and in the result. The E10 campaign's Codex
        # F5 clearance is the record this closes.
        if disposition == "fixed" and verification.get("method") == "static":
            # the report supplying THIS clearance is not its own history
            history = [row for row in vmod.blocked_history(run.run_dir, cp, index)
                       if row.get("call_id") != call.get("call_id")]
            if history:
                first = history[0]
                note = ("a retained report of this run recorded a stopped execution for this "
                        "item (%s, %s); a static clearance does not remove it (contract "
                        "section 5)" % (first.get("call_id"), first.get("how")))
                # Contract section 7's own move: the core DOWNGRADES the verifier's `fixed`
                # to `not_fixed` on evidence the verifier's later report did not carry — the
                # run's own retained history.
                disposition, item_reason = "not_fixed", "verification_blocked"
                adjudication["driver_action"] = "downgraded"
                adjudication["note"] = note
                verification["blocked"] = note
                verification.pop("missing", None)
                adjudication["static_clearance_refused"] = {
                    "why": "contract section 5: an execution the sandbox or environment "
                           "stopped is verification_blocked, never static",
                    "reports_that_recorded_the_block": [
                        {k: row.get(k) for k in ("call_id", "raw_path", "how")}
                        for row in history],
                }
        # E11-45 S2: an item that DECLARES a required service observation is not cleared by a
        # report that never observed the service. The requirement is the input's, bound onto the
        # item at start; the core refuses the `fixed`, keeps the rejected claim, and records the
        # refusal. A static read never satisfies it (contract section 5).
        if disposition == "fixed":
            required = item.get("required_service_observation") or {}
            if required.get("service"):
                found = vmod.bound_service_observation(verification, required["service"])
                if found is None:
                    disposition, item_reason = "not_fixed", "missing_evidence"
                    adjudication["driver_action"] = "downgraded"
                    note = ("the item requires an observation of %s (%s); the report carries "
                            "no executed command whose retained output observes it, so the "
                            "fixed is refused (contract section 5)"
                            % (required["service"], required.get("observe") or "the named state"))
                    adjudication["note"] = note
                    adjudication["service_observation_refused"] = {
                        "service": required["service"],
                        "observe": required.get("observe") or "",
                        "why": "a fixed on an item that requires a service observation needs an "
                               "executed command whose retained output observes that service; a "
                               "static read is never one",
                        "verifier_said": said,
                        "method": verification.get("method"),
                        "evidence_kinds": sorted(set(
                            e.get("kind") for e in verification.get("evidence") or [])),
                    }
                    verification["missing"] = verification.get("missing") or note
                    verification.pop("blocked", None)

        # E11-7 item 3: an EVIDENCED correction between `not_fixed` reasons. The CLI's
        # `--reason` served only a downgrade of a verifier `fixed`, so a verifier that
        # reported `reproduces` for a partial fix, or `missing_evidence` for a blocked
        # execution, could not be corrected at all — and the retained report is never edited.
        # The disposition is unchanged, the verifier's own word stays in `verifier_said`, and
        # the correction carries its evidence.
        if reason is not None and reason != item_reason:
            if said != "not_fixed":
                raise Usage("--reason corrects a not_fixed reason; the verifier said %s for "
                            "item %d (a verifier fixed is changed with --action downgraded)"
                            % (said, index))
            if not note:
                raise Usage("correcting a not_fixed reason needs --note (the evidence for the "
                            "corrected reason); the retained report is never edited")
            adjudication["reason_corrected_from"] = item_reason
            adjudication["reason_correction_evidence"] = note
            item_reason = reason
            if reason == "verification_blocked":
                verification["blocked"] = verification.get("blocked") or note
                verification.pop("missing", None)
            elif reason == "missing_evidence":
                verification["missing"] = verification.get("missing") or note
                verification.pop("blocked", None)
            else:
                for key in ("blocked", "missing"):
                    verification.pop(key, None)
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
    # E13 slice 1: the causing item, kept beside the defect (never inside it: the defect object is a
    # verbatim copy of result.schema.json's and a drift test holds it) so the `defect_raised` event
    # can name the finding whose fix introduced this one
    cp.setdefault("new_defect_causes", []).append(caused)
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
    """Regeneration of a plan step's content or value (E8-28).

    E13 3.3: for a receipt this core wrote, the bytes come from the text the component rendered for
    this run, so a redo writes exactly what the plan hashed.

    The one fallback is a receipt written BEFORE the records moved into the component (a seeded or
    legacy receipt, the E7 W lanes among them): its records were never appended as this run's
    events, so `render --run-id` has nothing to give, and the replay uses the core's own renderers
    over the checkpoint's facts, as it always did. Those renderers survive for this path only; the
    records of such a run reach the log through the importer once the steps land (`level_log`).
    Report question 6 names this reading.
    """
    rendered = run.rendered or {}
    reopen_lines, waiver_lines = records_write.split_grant_lines(rendered.get("grants"))
    block = rendered.get("block") or ""
    open_after = run.open_after
    legacy = run.legacy_receipt or not block
    cp = run.cp.doc
    checklist = cp["scope"]["checklist"]
    results = [it["result"] for it in cp["items"] if it["state"] == "done"]
    waivers, reopenings = grants_for_plan(cp)

    def matches(step, text):
        return rcmod.sha(ledger.apply_step(_state_before(run, step),
                                           {"kind": step["kind"], "content": text,
                                            "target": step["target"]})) == step["after_sha256"]

    def legacy_reopen(step):
        for g in sorted(reopenings, key=lambda x: (x["grant"]["date"], x["index"])):
            it = g["grant"]["item"]
            text = ledger.render_reopen(g["grant"]["date"], it["location"]["file"], it["location"]["line"],
                                        it["claim"], g["grant"]["quoted_words"])
            if matches(step, text):
                return text
        return ""

    def legacy_waiver(step):
        for g in sorted(waivers, key=lambda x: (x["grant"]["date"], x["index"])):
            it = g["grant"]["item"]
            text = ledger.render_waiver(g["grant"]["date"], g["grant"]["severity"], it["location"]["file"],
                                        it["location"]["line"], it["claim"], g["grant"]["quoted_words"])
            if matches(step, text):
                return text
        return ""

    def legacy_block():
        lines = []
        for it, res in zip(checklist, results):
            disp = "fixed" if res["disposition"] == "fixed" else "not fixed"
            lines.append(ledger.render_recheck_line(it["severity"], it["location"]["file"], it["location"]["line"],
                                                    it["claim"], disp, ledger.render_how(res["verification"])))
        slices = ledger.sort_slices(it["slice"] for it in checklist)
        for d in cp["new_defects"]:
            lines.append(ledger.render_defect_line(d["severity"], d["location"]["file"], d["location"]["line"],
                                                   d["claim"], d["failure_scenario"],
                                                   ledger.defect_slice_field(slices, d["charged_to_slice"])))
        return ledger.render_block(run.run_date, slices, lines)

    def regen(step):
        kind = step["kind"]
        if kind == "reopened_line":
            if not legacy:
                for text in reopen_lines:
                    if matches(step, text):
                        return text
            return legacy_reopen(step)
        if kind == "waived_line":
            if not legacy:
                for text in waiver_lines:
                    if matches(step, text):
                        return text
            return legacy_waiver(step)
        if kind in ("punch_list_block", "verdict_doc_copy"):
            return legacy_block() if legacy else block
        # status_line: the core's own mapping (a DECISION, ruling E13-1) over the open set the
        # component derives, from the card the document carries before the step
        before = _state_before(run, step)
        parsed = ledger.parse_document(before, step["target"])
        card = ledger.slice_card(parsed, step["slice"])
        return ledger.card_after(card, [e for e in open_after if e["slice"] == step["slice"]])
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


def cancel_status_steps(plan, rc, k):
    """E8-A44: status step k and every later status-line step are cancelled; steps already done stand."""
    for s in plan:
        if s["kind"] == "status_line" and s["step"] >= k:
            s["cancelled"] = True
    for s in rc.doc["plan"]:
        if s["kind"] == "status_line" and s["step"] >= k:
            s["cancelled"] = True


def run_transaction(run, rc, plan, classes, pre_nontarget_diff, pre_nontarget_sha256=None):
    """Apply the plan's pending steps in order with write-ahead entries (section 9).
    plan is the working copy (content, value, slice, landed live here); rc.doc["plan"] is the
    receipt's stored plan, which only ever gains `cancelled`. pre_nontarget_sha256 is the
    transaction guard's digest of the pre-transaction non-target diff on a resume (E8-A45).
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
        # E8-A44: the boundary check before EVERY status-line step (section 9); a violation it finds before
        # step k, or one an earlier pass of this transaction recorded in boundary.json, cancels step k and
        # every later status-line step; a status line already receipted done stands
        if step["kind"] == "status_line" and not cancelled:
            if not violations:
                found, now = rcmod.boundary_violations(run.workspace, run.pre_transaction, plan, virtual, pre_nontarget_diff, pre_nontarget_sha256)
                if found:
                    violations = found
                    record_boundary(run, found, step["step"])
            if violations:
                cancel_status_steps(plan, rc, step["step"])
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
        # E8-A11 / E8-A44: a plan with no status-line step runs the boundary check before the done entry of its
        # last step, the just-applied step's after-hash inside the allowed state
        if step["step"] == last and not has_status and not violations:
            found, now = rcmod.boundary_violations(run.workspace, run.pre_transaction, plan, virtual, pre_nontarget_diff, pre_nontarget_sha256)
            if found:
                violations = found
                record_boundary(run, found, step["step"])
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


def record_boundary(run, violations, before_step):
    """Write run_dir/boundary.json with the step the check preceded and list it as a run artifact
    (E8-A11, E8-A44)."""
    path = rcmod.write_boundary(run.run_dir, violations, before_step)
    run.add_artifact(path)
    log("boundary violation before step %d: %s" % (before_step, "; ".join(violations)))


def assemble_and_deliver(run, rc, outcome, at_transaction, pre_cards, keep_existing=False):
    """Result assembly after the commit point (or after a recording failure)."""
    cp = run.cp.doc
    # CR-F1(b): once the transaction's append has landed, a result that cannot validate is not a
    # bare `stopped`: the events are in the log, the document holds the other half, and the run is
    # `recording_failed` with the half named (Run.stop_builder reads this).
    append_block = (rc.doc.get("append") or {}) if rc is not None else {}
    if outcome["status"] == "completed" and append_block.get("head"):
        run.recording_half = "its document steps cannot be validated against it"
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
    # E11-7 item 3: a recorded project state reported as a grant claim is neither a rejected
    # grant nor an injection attempt. It is kept under its own name so nothing is lost.
    record_documents = set()
    for entry in checklist:
        document = ((entry.get("record") or {}).get("document"))
        if document:
            record_documents.add(document)
    recorded_states = []
    for claim in tail.get("grant_claims") or []:
        is_record, why = recorded_project_state(claim, record_documents)
        if is_record:
            recorded_states.append("%s%s%s" % (claim, ledger.SEP, why))
            continue
        rejected.append(claim_rejected(claim))
        injection.append(claim_injection(claim))
    for row in recorded_states:
        log("recorded project state, not a claimed grant: %s" % row)
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
    # E8-A31: the named artifacts (receipt.json and receipt.log among them), then every other file under run_dir
    writes = rmod.artifact_writes(run.artifact_inventory([run.path("receipt.json"), run.path("receipt.log")]))
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
    if run.resumed_half:
        # E13 3.5: the result says which half of the transaction was missing when the run resumed
        doc["resumed_half"] = run.resumed_half
    chat_extra = {"slice": (doc["checklist"] or {}).get("slice")}
    copies = [s["target"] for s in plan if s["kind"] == "verdict_doc_copy" and s.get("landed")]
    chat_extra["verdict_doc"] = ("%s — appended" % copies[0]) if copies else None
    if outcome["status"] == "completed":
        # E13 3.2: the open set after the run is the component's; the document supplies the cards
        # its `Status:` lines now carry, which is structure the transaction just wrote
        after_view = rview.read(records(), run.workspace, document)
        parsed_after = after_view.structure
        opened = {"entries": after_view.entries}
        slices = ledger.sort_slices(it["slice"] for it in checklist if it["slice"] != "none")
        cards = []
        for s in slices:
            before = pre_cards.get(s, "none")
            after = ledger.slice_card(parsed_after, s)
            entry = {"slice": s, "before": before, "after": after}
            if before != after:
                # E8-A44: beside a violation, a card can have moved only through a status step done before it was found
                entry["reason"] = "moved before the violation was found" if outcome["violations"] else "the mapping of Appendix A over the slice's open set after this run"
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


def reprove_retained_reports(run):
    """E8-A26: before the plan, every retained report a done item was adjudicated from (a call recorded
    complete, E8-A40, covering a done item) must exist at raw_path, hash to raw_sha256, and parse with
    a tail; otherwise the run stops as `evidence changed: <path>` with no project write. A call record
    without raw_sha256 (a checkpoint written before E8-12) retained nothing to re-prove."""
    cp = run.cp.doc
    done = set(i for i, it in enumerate(cp["items"]) if it["state"] == "done")
    for call in cp["verifier_calls"]:
        if not vmod.is_complete(call.get("status")) or not call.get("raw_path") or not call.get("raw_sha256"):
            continue
        if not any(i in done for i in call.get("items") or []):
            continue
        path = call["raw_path"]
        ok = os.path.isfile(path) and canon.sha256_file(path) == call["raw_sha256"]
        if ok:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            ok = vmod.parse_report_tail(text, len(cp["items"]), call["items"])["ok"]
        if not ok:
            run.terminal("stopped", "evidence changed: %s" % path, checklist_count=len(cp["items"]), verifier=verifier_block(run))


def records_pin(scope):
    """CR-F1(a): `{doc, log, head}` for the view the run's open set was read from, or None when the
    scope was resolved without one (a seeded checkpoint, or a stop before the view existed)."""
    view = scope.get("view") if isinstance(scope, dict) else None
    if view is None:
        return None
    try:
        return {"doc": scope["document"], "log": view.state["log"], "head": view.head}
    except (KeyError, TypeError):
        return None


def head_now(run, document):
    """The log's head as the component reports it, or None when it cannot be read (no log yet)."""
    try:
        return records().verify(run.workspace, document)["head"]
    except (rcl.RecordsRefusal, rcl.ComponentUnavailable):
        return None


def rival_since_pin(run, cp, document):
    """CR-F1(a): a named conflict when the log moved between `start` and `record`.

    The head the open set was read against is pinned in the checkpoint at `start`. At `record` the
    log must still be at it BEFORE this run's own sync: every event past it was appended by
    someone else while this run was grading, and nothing the run decided accounts for it.

    How this sits with CR-1 (which runs `import-legacy` at the start of every phase that reads
    records, and whose import events legitimately move the head): the comparison is taken BEFORE
    the run's own sync, so the sync's events are never the ones it flags, and the pin is advanced
    to the post-sync head in the same checkpoint write. CR-1 owns the window inside a phase; this
    check owns the window between two phases. They do not conflict.
    """
    pin = cp.get("records_pin")
    if not pin or pin.get("doc") != document:
        return None
    now = head_now(run, document)
    if now is None or now == pin["head"]:
        return None
    return ("the log of %s is at head %s, not the %s this run's open set was read against at the "
            "start of the run: another writer appended to it between the phases and nothing this "
            "run decided accounts for that event. Re-read the log and decide (section 10); no "
            "record written" % (document, now[:12], pin["head"][:12]))


def preplan_outside_edit(run, cp):
    """M2: the transaction's targets must still carry the bytes pinned BEFORE the append.

    The guard stores each target's hash beside the pre-transaction identity and the non-target
    diff, because the identity's tracked diff EXCLUDES the targets (that is what lets the
    transaction write them at all). Without the hashes an edit to a target made before the
    document plan exists is invisible to every check and becomes the plan's `before` state. The
    hashes are compared before a plan is created and before an empty-plan resume writes anything;
    once a plan exists, section 11's receipted-state classification decides, unchanged.

    Returns the stop reason, or None when every target is where the transaction left it.
    """
    guard = cp.get("transaction_guard") or {}
    pinned = guard.get("target_sha256") or {}
    for target in sorted(pinned):
        current = rcmod.sha(rcmod.file_text(os.path.join(run.workspace, target)))
        if current != pinned[target]:
            return ("%s is at %s, not the %s the transaction pinned before its append: an outside "
                    "edit reached it before the document plan existed, and the edited bytes are "
                    "never taken as the baseline. No document, event, checkpoint or receipt write "
                    "follows; this needs the user's word" % (target, current[:12], pinned[target][:12]))
    return None


def target_hashes(workspace, targets):
    """M2: {target: sha256 of its bytes now}, stored in the transaction guard before the append."""
    return dict((t, rcmod.sha(rcmod.file_text(os.path.join(workspace, t)))) for t in targets)


def run_instant(run):
    """The `at` every event of this run carries: the run's DECLARED date (E8-25) with the current
    UTC time of day.

    Appendix A has always put the run date on the block heading, and `records.py render` takes that
    heading's date from the first block event's `at`. The two are therefore the same day, and a run
    whose adapter declares a run date other than the wall clock's still writes the heading it wrote
    before. The time of day is the real one.
    """
    now = rmod.now_iso()
    if not run.run_date:
        return now
    return "%sT%s" % (run.run_date, now.split("T", 1)[1])


def transaction_targets(run, cp, document):
    """Every file the document steps can name, known before the plan exists (E13 3.3): the ledger
    document, and each slice's verdict doc where the glob matches exactly one."""
    targets = {document}
    for name in ledger.sort_slices(it["slice"] for it in cp["scope"]["checklist"]):
        if name == "none":
            continue
        matches = ledger.verdict_doc_glob(run.workspace, document, name)
        if len(matches) == 1:
            targets.add(matches[0])
    return sorted(targets)


def persist_refusal(rc, key, expect_head, refusal):
    """M3: record a received refusal in the receipt's append block as non-resumable."""
    block = dict(rc.doc.get(key) or {})
    if not block.get("log"):
        fallback = (rc.doc.get("append") or {}).get("log")
        if not fallback:
            return
        block["log"] = fallback
    block.setdefault("expected_head", expect_head)
    block["refused"] = {"exit_code": refusal.exit_code, "error": refusal.error,
                        "reason": refusal.sentence()}
    rc.doc[key] = block
    rc.save()


def refused_reason(block, what):
    """The named stop a persisted refusal produces on every later resume (M3)."""
    r = block.get("refused") or {}
    return ("%s was refused by the records component (exit %s, %s): %s. A refusal the component "
            "gave is definitive and is never retried: nothing was appended, and nothing will be. "
            "Re-read the log and decide (section 10)"
            % (what, r.get("exit_code"), r.get("error") or "-", r.get("reason") or ""))


def append_or_stop(run, rc, document, events, expect_head, checklist_count, key="append"):
    """The transaction's append. A refusal surfaces as the pilot's matching stop (brief 3.4) with
    NOTHING written to the document; the receipt holds the intent and no entry.

    M3: a refusal RECEIVED from the component is definitive, not an unknown outcome. It is
    persisted in the receipt's append block as `refused` BEFORE the named stop is returned, so
    that no resume ever retries it (an unknown outcome — a crash with no answer — is the only
    thing `recover_append` settles, and it settles it against the head this block already names).
    """
    try:
        return records().append(run.workspace, document, events, expect_head, run.run_dir)
    except rcl.RecordsRefusal as refusal:
        persist_refusal(rc, key, expect_head, refusal)
        stop = rview.stop_for(refusal)
        reason = ("the records component refused the transaction's append (exit %s, %s -> %s): %s"
                  % (refusal.exit_code, refusal.error or "-", stop.status, stop.reason))
        if stop.status == "stale_source":
            run.matched = False
            doc = {"protocol_version": 1, "run": run.run_block(verifier=verifier_block(run), with_session=True),
                   "status": "stale_source",
                   "source_identity": {"expected": _pin_from(run.cp.doc["start_identity"]),
                                       "actual": identity.reported(identity.identity_of(run.workspace)), "matched": False},
                   "stop_reason": reason + "; no record written"}
            run.mark_terminal("stale_source", reason, False)
            final, path, chat = run.deliver(doc)
            raise Stop({"next": "done", "status": "stale_source", "result": path, "chat": chat, "question": None}, EXIT_TERMINAL)
        if stop.status == "missing_input":
            run.missing(stop.fields or ["target.build_doc"], stop.ambiguity or [reason], stop.question)
        run.plan = []
        assemble_and_deliver(run, rc, {"status": "recording_failed", "stop_reason": reason,
                                       "violations": [], "cancelled": False},
                             run.pre_transaction, run.pre_cards)


def card_moves(plan, pre_cards):
    """The card each status-line step that actually LANDED moved, in plan order. A step the
    boundary check cancelled, and a seeded step the transaction never regenerated, move none."""
    moves = []
    for step in plan:
        if step["kind"] != "status_line" or step.get("cancelled") or not step.get("landed"):
            continue
        name, value = step.get("slice"), step.get("value")
        if not name or not value:
            continue
        moves.append((name, pre_cards.get(name, "none"), value))
    return moves


def settle_card_events(run, rc, document, plan, pre_cards, at_transaction):
    """The second append (E13 3.3) and its recovery (the fix round, M1, M3 and M4).

    Completing the document steps does not complete the recording transaction: the `card_set`
    events of the status steps that landed are the second half of it, and every pass — a first
    `record`, a resume inside the transaction, and a resume holding a COMMITTED document receipt
    alike — reconciles the landed, non-cancelled status steps with this run's card events through
    the CLI. A cancelled status step produces no `card_set`, which is the whole reason the cards
    are a second append rather than part of the first.

    M4: a card-history query that FAILED is not an empty history. Its exit and explanation are
    kept, the named pilot stop is delivered, and the function returns before any append; only
    cards a SUCCESSFUL read proved absent are ever appended.

    M3, applied to this append too: a refusal the component gave is persisted as non-resumable and
    never retried. An unknown outcome (a crash with no answer) is settled against the head the
    receipt already names, never against a newer one.

    Returns `(missing half or None, RecordsStop or None)`.
    """
    if not (rc.doc.get("append") or {}).get("log"):
        # A receipt with no `append` block was written before the records moved into the component
        # (a seeded or legacy receipt, the E7 W lanes among them). This run made no append at all,
        # and the lines its steps wrote reach the log the way every hand-written record does,
        # through the importer, `card_observed` included. There is no card half of a transaction
        # this core never opened, and fabricating `card_set` events for it would be a record of
        # something that did not happen. The transaction branch settles such a receipt only after
        # `recover_append` has adopted it (question 6 of the slice 1 report).
        return None, None
    moves = card_moves(plan, pre_cards)
    block = rc.doc.get("card_append") or None
    if not moves and not block:
        return None, None
    # A `card_append` block that already carries a head records the LAST append, not the whole card
    # half: a resume that lands further status steps owes their cards too. So the reconciliation is
    # made against the log every pass, and only the log says what this run already wrote.
    if block and block.get("refused"):
        return None, rview.RecordsStop(rview.CONFLICT_STATUS,
                                       refused_reason(block, "the transaction's card events append"))
    # M4: the history read decides what is already there; a failure is a stop, never an empty set
    try:
        rows = records().events(run.workspace, document, kind="card_set")["results"]
    except rcl.RecordsRefusal as refusal:
        return None, rview.stop_for(
            refusal, reading="the card history of this run could not be read, so no card event was "
                             "appended and nothing was recorded twice")
    already = {}
    for row in rows:
        event = row["event"]
        if (event.get("actor") or {}).get("run_id") == run.run_id:
            already.setdefault(event.get("slice"), []).append(row["seq"])
    pending = [m for m in moves if m[0] not in already]
    # an UNKNOWN outcome: the receipt names an append whose answer never came back
    recovering = block is not None and not block.get("head")
    if not pending:
        if recovering and already:
            # the append LANDED; only its record in the receipt is missing (E13 3.5, direction b)
            walked = records().verify(run.workspace, document)
            seqs = sorted(seq for rows_ in already.values() for seq in rows_)
            rc.doc["card_append"] = {"log": block["log"], "expected_head": block["expected_head"],
                                     "head": walked["head"], "seqs": seqs, "recovered": True}
            rc.save()
            return "the card events' record in the receipt", None
        return None, None
    if recovering:
        # M3: the receipt's expected head, never a head read afresh. A head that moved since is a
        # conflict the component refuses (exit 7), not permission to append against the new one.
        head = block["expected_head"]
    else:
        head = records().verify(run.workspace, document)["head"]
        rc.append_intent(rc.doc["append"]["log"], head, key="card_append")
    events = records_write.card_events(document, run.run_id, run.harness_name(), run_instant(run),
                                       identity.reported(at_transaction), pending)
    try:
        result = records().append(run.workspace, document, events, head, run.run_dir)
    except rcl.RecordsRefusal as refusal:
        persist_refusal(rc, "card_append", head, refusal)
        return None, rview.stop_for(
            refusal, reading="the card events of this run were not appended; until the conflict is "
                             "decided the log and the document's `Status:` lines disagree")
    rc.record_append(result["log"], head, result["head"],
                     [row["seq"] for row in result["appended"]], key="card_append")
    return ("the card events" if recovering else None), None


def card_outcome(run, rc, document, plan, pre_cards, at_transaction, outcome):
    """Settle the card half and fold its result into the transaction's outcome.

    `completed` is reported only when the document steps AND the card-event receipts are complete;
    a definitive refusal of the card append is `recording_failed` with the half named, and never
    an escaped exception (the fix round's M1).
    """
    half, stop = settle_card_events(run, rc, document, plan, pre_cards, at_transaction)
    if half and not run.resumed_half:
        run.resumed_half = half
    if stop is None:
        return outcome
    if outcome["status"] != "completed":
        # the document half had already failed; the card stop is added to what the run reports
        out = dict(outcome)
        out["stop_reason"] = "%s; the card events were not appended either: %s" % (
            outcome.get("stop_reason") or "the transaction did not finish", stop.reason)
        return out
    return {"status": "recording_failed",
            "stop_reason": "the document steps landed and the card events did not: %s" % stop.reason,
            "violations": outcome["violations"], "cancelled": outcome["cancelled"]}


def recover_append(run, rc, document):
    """E13 3.5: settle the transaction's append on a resume, and say which half was missing.

    The receipt's `append` block carries the head the run expected as soon as the transaction
    begins, and the resulting head and the seqs only once the append was recorded; the PLAN is
    written after the append. So an intent with no head means no document step can have landed
    either, and the log is asked for this run's events by `run_id`:
      - it holds them, so the append LANDED and only its record in the receipt is missing: the
        block is completed from the log and marked `recovered`. Nothing is appended.
      - it holds none, so the append never landed: it is made now, under the head the log carries
        now, and recorded.

    A receipt with a PLAN and no `append` block at all was written before the records moved into
    the component (a seeded or legacy receipt, the E7 W lanes among them). Its landed steps already
    wrote their lines into the document, and CR-1's import has just brought exactly those lines
    into the log, so appending them again would clear a finding the log already shows cleared. That
    half is therefore settled by the import, and the lines the remaining steps write are imported
    the same way once they land (`level_log`). Report question 6 names this reading.

    Returns the half that was missing, or None when the receipt was already complete.
    """
    block = rc.doc.get("append")
    if block and block.get("head"):
        return None
    if block and block.get("refused"):
        # M3: the component ANSWERED, and its answer was a refusal. Nothing landed, the outcome is
        # not unknown, and a resume never sends the append again.
        run.plan = []
        assemble_and_deliver(run, rc, {"status": "recording_failed", "violations": [], "cancelled": False,
                                       "stop_reason": refused_reason(block, "the transaction's append")},
                             run.pre_transaction, {})
    walked = records().verify(run.workspace, document)
    if not block:
        rc.doc["append"] = {"log": walked["log"], "expected_head": walked["head"],
                            "head": walked["head"], "seqs": [], "recovered": True}
        rc.save()
        run.legacy_receipt = True
        return "the append (a receipt written before the records moved; the document's records were imported)"
    landed = [row for row in records().events(run.workspace, document)["results"]
              if (row["event"].get("actor") or {}).get("run_id") == run.run_id
              and row["event"]["kind"] in ("reopened", "disposition", "defect_raised", "waived")]
    if landed:
        rc.doc["append"] = {"log": block["log"], "expected_head": block["expected_head"],
                            "head": walked["head"], "seqs": [row["seq"] for row in landed],
                            "recovered": True}
        rc.save()
        return "the append's record in the receipt"
    cp = run.cp.doc
    view = rview.read(records(), run.workspace, document)
    waivers, reopenings = grants_for_plan(cp)
    results = [it["result"] for it in cp["items"]]
    events = records_write.transaction_events(document, run.run_id, run.harness_name(), run_instant(run),
                                              identity.reported(run.pre_transaction), view,
                                              cp["scope"]["checklist"], results, cp["new_defects"],
                                              waivers, reopenings, cp.get("new_defect_causes") or [])
    # M3: the head the RECEIPT expects, never the head read now. The receipt names the head the
    # run read at plan time; a head that changed since is a conflict the component refuses, and a
    # refusal is never permission to refresh it.
    appended = append_or_stop(run, rc, document, events, block["expected_head"], len(cp["items"]))
    rc.record_append(appended["log"], block["expected_head"], appended["head"],
                     [row["seq"] for row in appended["appended"]])
    return "the append"


def level_log(run, document):
    """After a legacy receipt's remaining steps land, the lines they wrote reach the log the way
    every other hand-written record does: through the importer (CR-1). Idempotent."""
    if not getattr(run, "legacy_receipt", False):
        return
    try:
        rview.sync(records(), run.workspace, document)
    except rview.RecordsStop as stop:
        log("the log could not be levelled after the resume: %s" % stop.reason)


def plan_and_record(run):
    """The planning path of `record` (section 9 as E13 slice 1 amends it).

    Order: the pre-transaction checks unchanged (Appendix A re-read, the retained reports re-proved,
    the identity check); then the receipt with the APPEND's intent; then the append, one call, all
    events or none; then the receipt's record of it, before any document step; then `render`; then
    the plan computed from the rendered text; then the document steps as today; then the `card_set`
    events of the status steps that landed. Raises Stop with the terminal document.
    """
    cp = run.cp.doc
    reread_appendix_a(run.root)
    reprove_retained_reports(run)
    at_transaction = identity.identity_of(run.workspace)
    if identity.reported(at_transaction) != cp["start_identity"]:
        run.matched = False
        run.identity = cp["start_identity"]
        reason = "the identity changed between the start of the run and the recording transaction; no record written"
        doc = {"protocol_version": 1, "run": run.run_block(verifier=verifier_block(run), with_session=True), "status": "stale_source",
               "source_identity": {"expected": _pin_from(cp["start_identity"]), "actual": identity.reported(at_transaction), "matched": False},
               "stop_reason": reason}
        run.mark_terminal("stale_source", reason, False)  # E8-A20: the phases end before result.json is written
        final, path, chat = run.deliver(doc)
        raise Stop({"next": "done", "status": "stale_source", "result": path, "chat": chat, "question": None}, EXIT_TERMINAL)
    document = target_document(cp)
    targets = transaction_targets(run, cp, document)
    # E8-A19: every project-record target resolves inside the workspace. The check runs BEFORE the
    # component is asked anything, because a target outside the workspace is the pilot's own
    # `recording_failed`, not a refusal of the component's (which would call a path through a
    # symbolic link an invalid ledger address).
    outside = next((t for t in [document] + [t for t in targets if t != document]
                    if not rcmod.contained(run.workspace, t)), None)
    pre_nontarget_diff = identity.tracked_diff_excluding(run.workspace, targets)
    run.pre_transaction = at_transaction
    if outside is not None:
        cp["transaction_guard"] = {"identity": identity.reported(at_transaction),
                                   "nontarget_diff_sha256": canon.sha256_hex(pre_nontarget_diff),
                                   "targets": targets,
                                   "target_sha256": target_hashes(run.workspace, targets)}
        cp["phase"] = "recording"
        run.cp.save()
        rc = rcmod.Receipt.new(run.run_dir, run.run_id, [], run.schemas)
        run.add_artifact(run.path("receipt.json"))
        run.add_artifact(run.path("receipt.log"))
        run.cp.save()
        run.plan = []
        assemble_and_deliver(run, rc, {"status": "recording_failed", "violations": [], "cancelled": False,
                                       "stop_reason": rcmod.containment_reason(1, outside)},
                             at_transaction, {})
    # CR-F1(a): before this run's OWN sync, the log must still be at the head the open set was read
    # against at `start`. Anything past it came from another writer while this run was grading, and
    # the run's decisions do not account for it: a named conflict stop, before any append.
    rival = rival_since_pin(run, cp, document)
    if rival is not None:
        run.terminal("stopped", rival, checklist_count=len(cp["items"]))
    # CR-1: the log is levelled with the document before its records are read again
    try:
        rview.sync(records(), run.workspace, document)
        view = rview.read(records(), run.workspace, document)
    except rview.RecordsStop as stop:
        records_stop(run, stop, checklist_count=len(cp["items"]))
    pre_cards = view.cards
    run.pre_cards = pre_cards
    waivers, reopenings = grants_for_plan(cp)
    results = [it["result"] for it in cp["items"]]
    # E8-A45: the transaction guard, stored as the transaction begins. The log is excluded from the
    # identity and from this diff (CR-3), so the append the transaction makes moves neither.
    cp["transaction_guard"] = {"identity": identity.reported(at_transaction), "nontarget_diff_sha256": canon.sha256_hex(pre_nontarget_diff),
                               "targets": targets,
                               # M2: each target's bytes as they stand BEFORE the append. The
                               # tracked diff above excludes the targets, so without these an edit
                               # that reaches one of them before the plan exists is invisible.
                               "target_sha256": target_hashes(run.workspace, targets)}
    # CR-F1(a): the pin moves to the head this phase's own sync produced, so a later pass through
    # this function compares against what THIS run last read, not against a stale `start` head.
    if cp.get("records_pin") and cp["records_pin"].get("doc") == document:
        cp["records_pin"]["head"] = view.head
    cp["phase"] = "recording"
    run.cp.save()
    rc = rcmod.Receipt.new(run.run_dir, run.run_id, [], run.schemas,
                           append={"log": view.state["log"], "expected_head": view.head})
    run.add_artifact(run.path("receipt.json"))
    run.add_artifact(run.path("receipt.log"))
    run.cp.save()
    try:
        events = records_write.transaction_events(document, run.run_id, run.harness_name(), run_instant(run),
                                                  identity.reported(at_transaction), view,
                                                  cp["scope"]["checklist"], results, cp["new_defects"],
                                                  waivers, reopenings, cp.get("new_defect_causes") or [])
    except records_write.MissingFinding as exc:
        run.plan = []
        assemble_and_deliver(run, rc, {"status": "recording_failed", "stop_reason": str(exc), "violations": [], "cancelled": False},
                             at_transaction, pre_cards)
    expect = "f" * 64 if os.environ.get("RECHECK_TEST") == "1" and os.environ.get("RECHECK_TEST_RECORDS_STALE_HEAD") == "1" else view.head
    appended = append_or_stop(run, rc, document, events, expect, len(cp["items"]))
    try:
        rcmod._hook("RECHECK_TEST_FAIL_AFTER_APPEND", 1)
    except rcmod.TestHookFailure as exc:
        # the crash window of E13 3.5, direction (b): the append landed and the receipt shows the
        # intent only. The run ends recording_failed; `resume` finds the run's events by run_id.
        run.plan = []
        assemble_and_deliver(run, rc, {"status": "recording_failed", "violations": [], "cancelled": False,
                                       "stop_reason": "the transaction failed after the append and before the receipt "
                                                      "recorded it (%s); the log holds the events, the receipt holds "
                                                      "the intent" % exc},
                             at_transaction, pre_cards)
    rc.record_append(appended["log"], view.head, appended["head"], [row["seq"] for row in appended["appended"]])
    finish_transaction(run, rc, document, pre_cards, at_transaction, pre_nontarget_diff)


def finish_transaction(run, rc, document, pre_cards, at_transaction, pre_nontarget_diff):
    """Render, plan the document steps, receipt them, run them, then record the cards that moved."""
    cp = run.cp.doc
    run.rendered = records().render(run.workspace, document, run.run_id)
    after = rview.read(records(), run.workspace, document)
    run.open_after = after.open_entries()
    # M2: the plan below takes each target's CURRENT bytes as its `before` state, so those bytes
    # must still be the ones the transaction pinned before its append. An edit that reached a
    # target in between is an outside edit: the plan is never created, no document, event,
    # checkpoint or receipt write follows, and the baseline is never regenerated from edited bytes.
    edited = preplan_outside_edit(run, cp)
    if edited is not None:
        run.plan = []
        assemble_and_deliver(run, rc, {"status": "recording_failed", "stop_reason": edited,
                                       "violations": [], "cancelled": False},
                             at_transaction, pre_cards)
    plan, states, cards_after, verdicts = rcmod.plan_document_steps(
        run.workspace, document, run.rendered, cp["scope"]["checklist"], pre_cards, run.open_after)
    rc.set_plan(plan)
    # E8-A19: every target resolves inside the workspace when the plan is made; a violation ends the
    # run as recording_failed with no project write
    violation = rcmod.plan_containment(run.workspace, plan)
    classes = [{"step": s["step"], "class": "redo"} for s in plan]
    if violation is not None:
        run.plan = plan
        outcome = {"status": "recording_failed", "stop_reason": violation, "violations": [], "cancelled": False}
    else:
        outcome = run_transaction(run, rc, plan, classes, pre_nontarget_diff)
        outcome = card_outcome(run, rc, document, plan, pre_cards, at_transaction, outcome)
    if outcome["status"] == "completed":
        cp["phase"] = "committed"
        run.cp.save()
    assemble_and_deliver(run, rc, outcome, at_transaction, pre_cards)


def _pin_from(start_identity):
    """The start identity as the `expected` pin of a stale result (every field, submodules empty)."""
    return dict(start_identity)


# ---- resume (section 11) --------------------------------------------------------------------------

EMPTY_SHA256 = canon.sha256_hex(b"")


def dirty_start(start):
    """E8-A45: the start identity's fields say tracked or untracked content differed from the commit."""
    return bool(start.get("dirty")) or bool(start.get("untracked")) or start.get("tracked_diff_sha256") != EMPTY_SHA256


def active_input(doc):
    """E8-A30: the presented input minus authorization.extra_continuation, authorization dropped when
    that leaves it empty (the binding hash is unchanged by construction; the grant is never stored)."""
    out = dict(doc)
    auth = out.get("authorization")
    if isinstance(auth, dict):
        auth = {k: v for k, v in auth.items() if k != "extra_continuation"}
        if auth:
            out["authorization"] = auth
        else:
            out.pop("authorization", None)
    return out


def attach_unsaved(run, cp, schemas):
    """The verified checkpoint as the run's state without a write (E8-A22: a refused or ended resume
    changes no byte of the checkpoint or the receipt)."""
    run.cp = cpmod.Checkpoint(run.run_dir, cp, schemas)
    run.artifacts = cpmod.artifacts(cp, run.run_dir)
    run.continuations = cp.get("continuations", 0)
    run.run_date = cp.get("run_date") or run.run_date
    run.session_wrote_fix = cp["scope"].get("session_wrote_fix", run.session_wrote_fix)
    run.identity = cp["start_identity"]
    run.matched = True


def outside_reason(step, c):
    if c.get("resting"):
        return ("step %d (%s, %s) landed but the target now rests at %s, not the step's after hash %s (an outside edit after the step; needs the user's word)"
                % (step["step"], step["kind"], step["target"], c["current"][:12], c["expected_after"][:12]))
    return ("step %d (%s, %s) cannot be classified: the target is at %s, neither its planned after hash %s nor the virtual before hash %s (an outside edit; needs the user's word)"
            % (step["step"], step["kind"], step["target"], c["current"][:12], c["expected_after"][:12], c["expected_before"][:12]))


def deliver_outside_edit(run, rc_doc, classes, c, now):
    """Section 11 step 5's outside edit: recording_failed re-assembled from the checkpoint and the receipt,
    both left byte-identical (E8-A21, E8-A22). Raises Stop."""
    rc = rcmod.Receipt(run.run_dir, rc_doc, run.schemas)
    step = rc_doc["plan"][c["step"] - 1]
    outcome = {"status": "recording_failed", "violations": [], "cancelled": False, "stop_reason": outside_reason(step, c)}
    work = [dict(s) for s in rc_doc["plan"]]
    for s, cl in zip(work, classes):
        # a resting outside edit (E8-A21) sits on a step that did land: its write is listed as the receipt says
        if cl["class"] == "done" or cl.get("resting"):
            s["landed"] = True
    run.plan = work
    pre_cards = reconstruct_cards_before(run, work, classes)
    assemble_and_deliver(run, rc, outcome, now, pre_cards)


def resume_identity_check(workspace, cp, rc_doc, classes, now):
    """Section 11 step 6 (E8-A45): the current identity against the transaction guard when the checkpoint
    holds one (its identity and the digest of the non-target diff; the targets are held by step 5's
    classification), else against the start identity plus the steps classified done. Returns
    (stale reasons, the expected identity)."""
    start = cp["start_identity"]
    guard = cp.get("transaction_guard")
    stale = []
    if now["submodules"]:
        stale.append("submodules present: %s" % ", ".join(now["submodules"]))
    if guard is not None:
        g = guard["identity"]
        if now["commit"] != g["commit"]:
            stale.append("HEAD is %s, the transaction began at %s" % (now["commit"], g["commit"]))
        if now["untracked"] != g["untracked"] or now["untracked_sha256"] != g["untracked_sha256"]:
            stale.append("untracked content differs from the transaction's start")
        digest = canon.sha256_hex(identity.tracked_diff_excluding(workspace, guard["targets"]))
        if digest != guard["nontarget_diff_sha256"]:
            stale.append("tracked files outside the transaction's targets changed since the transaction began")
        return stale, g
    landed_targets = set()
    if rc_doc is not None:
        for s, c in zip(rc_doc["plan"], classes):
            if c["class"] == "done":
                landed_targets.add(s["target"])
    diff_now = identity.tracked_diff_excluding(workspace, sorted(landed_targets)) if landed_targets else None
    if now["commit"] != start["commit"]:
        stale.append("HEAD is %s, the run started at %s" % (now["commit"], start["commit"]))
    if now["untracked"] != start["untracked"] or now["untracked_sha256"] != start["untracked_sha256"]:
        stale.append("untracked content differs from the start of the run")
    if not landed_targets:
        if now["tracked_diff_sha256"] != start["tracked_diff_sha256"]:
            stale.append("tracked content differs from the start of the run")
    elif not start["dirty"] and diff_now:
        stale.append("tracked files outside the receipted steps changed since the clean start")
    return stale, start


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
    # E8-A20: a stopped run continues only when its terminal block says so (section 11 step 1)
    terminal = cp.get("terminal") or {}
    if cp["phase"] == "stopped" and not terminal.get("resumable"):
        stopped(1, "the run ended as %s: %s; start a new run" % (terminal.get("status", "stopped"), terminal.get("stop_reason", "")))
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
    now = identity.identity_of(run.workspace)
    start = cp["start_identity"]
    guard = cp.get("transaction_guard")
    # E8-A22: the outside classification of step 5 is delivered before step 6 and before the continuation
    # count moves; neither the checkpoint nor the receipt is rewritten (result.json and chat.md only)
    outside = [c for c in (classes or []) if c["class"] == "outside"]
    if outside:
        attach_unsaved(run, cp, schemas)
        deliver_outside_edit(run, rc_doc, classes, outside[0], now)
    # step 6 (E8-A45): a checkpoint inside a transaction without a guard is refused when the run started dirty;
    # otherwise the identity against the guard when the checkpoint holds one, else the start identity plus the
    # steps classified done
    if guard is None and cp["phase"] in ("recording", "committed") and dirty_start(start):
        stopped(6, "the checkpoint carries no transaction guard and the run started dirty; start a new run")
    stale, expected = resume_identity_check(run.workspace, cp, rc_doc, classes, now)
    if stale:
        # E8-A22: delivered with the checkpoint and the receipt byte-identical
        attach_unsaved(run, cp, schemas)
        run.identity = expected
        run.matched = False
        doc_out = {"protocol_version": 1, "run": run.run_block(verifier=verifier_block(run), with_session=True), "status": "stale_source",
                   "source_identity": {"expected": _pin_from(expected), "actual": identity.reported(now), "matched": False},
                   "stop_reason": "; ".join(stale) + "; no record written"}
        final, path, chat = run.deliver(doc_out)
        raise Stop({"next": "done", "status": "stale_source", "result": path, "question": None, "chat": chat}, EXIT_TERMINAL)
    # continuation limit (section 11, E8-10): the first resume needs no grant, a second needs it; a grant whose
    # turn_ref the checkpoint already consumed is not a grant (E8-A23)
    count = cp.get("continuations", 0) + 1
    grant_ref = None
    if count > 1:
        present, ok, why = inputs.continuation_grant_ok(doc)
        if present and ok:
            ref = doc["authorization"]["extra_continuation"]["turn_ref"]
            used = cp.get("continuation_grants_used") or []
            if ref in used:
                ok, why = False, "extra_continuation: turn_ref '%s' already used for continuation %d" % (ref, used.index(ref) + 2)
            else:
                grant_ref = ref
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
    # E8-A30: the resolved input becomes the presented input minus the continuation grant, so every later
    # phase command reports the resumed session's invocation
    canon.atomic_write(run.path("input.json"), (json.dumps(active_input(doc), indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    run.cp = cpmod.Checkpoint(run.run_dir, cp, schemas)
    # the ledger is the pre-write inventory (a seeded checkpoint's scan, E8-29); input.json joins it at its first write
    run.cp.doc["artifacts"] = list(run.artifacts)
    run.add_artifact(run.path("input.json"))
    run.continuations = count
    run.run_date = cp.get("run_date") or run.run_date
    run.session_wrote_fix = cp["scope"].get("session_wrote_fix", run.session_wrote_fix)
    run.identity = start
    run.matched = True
    cp["continuations"] = count
    if grant_ref is not None:
        cp.setdefault("continuation_grants_used", []).append(grant_ref)
    was_stopped = cp["phase"] == "stopped"
    if was_stopped:
        # E8-A20: a resumable stop continues at the first pending item with a fresh call; the per-item retry
        # counters stand
        cp.pop("terminal", None)
        cp["phase"] = "verifying"
    cp.setdefault("run_date", run.run_date)
    cp["scope"].setdefault("session_wrote_fix", run.session_wrote_fix)
    run.cp.save()
    pend = cpmod.pending(cp)
    if pend and cp["phase"] in ("assembling", "verifying", "adjudicating"):
        call, text = (None, None) if was_stopped else vmod.retained_report(run.run_dir, cp)
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
        run.pre_transaction = guard["identity"] if guard else start
        document = target_document(cp)
        # CR-1 on a resume INSIDE the transaction, and only for a receipt this core did not write.
        # A receipt that names an append already holds this run's records as events, and the
        # document steps place their RENDERING: importing those lines would add a second, legacy
        # copy of each record after the run's own events, and file order is time order, so the copy
        # would win and undo the run's decision (an interrupted S2-01 reopens its waived item that
        # way). A receipt with no append block is the pre-E13 shape, whose landed lines really are
        # records the log lacks, so that one is imported (question 6).
        if not rc_doc.get("plan"):
            # M2: no document step has been planned, so no target has been receipted yet. An edit
            # that reached one of them before this resume must never become the plan's baseline,
            # and the check runs before any write of this resume — the import below included.
            edited = preplan_outside_edit(run, cp)
            if edited is not None:
                run.plan = []
                assemble_and_deliver(run, rc, {"status": "recording_failed", "stop_reason": edited,
                                               "violations": [], "cancelled": False},
                                     run.pre_transaction, {})
        if not rc_doc.get("append"):
            try:
                rview.sync(records(), run.workspace, document)
            except rview.RecordsStop as stop:
                records_stop(run, stop, checklist_count=len(cp["items"]))
        # E13 3.5, the crash window: which half is missing. The receipt names the append; the log,
        # asked for this run's events by run_id, says whether it landed. Neither half is ever done
        # twice.
        run.resumed_half = recover_append(run, rc, document)
        if not rc_doc.get("plan"):
            # the append is settled and the document steps were never planned: render, plan, run
            run.pre_cards = reconstruct_cards_before(run, [], [])
            finish_transaction(run, rc, document, run.pre_cards, run.pre_transaction,
                               None)
        work = [dict(s) for s in rc_doc["plan"]]
        for s, cl in zip(work, classes):
            if cl["class"] == "done":
                s["landed"] = True
        run.plan = work
        pre_cards = reconstruct_cards_before(run, work, classes)
        run.pre_cards = pre_cards
        run.rendered = records().render(run.workspace, document, run.run_id)
        run.open_after = rview.read(records(), run.workspace, document).open_entries()
        if run.resumed_half is None and any(c["class"] != "done" for c in classes):
            run.resumed_half = "the document steps"
        outcome = run_transaction(run, rc, work, classes, None, guard["nontarget_diff_sha256"] if guard else None)
        if outcome["status"] != "recording_failed":
            level_log(run, document)
            outcome = card_outcome(run, rc, document, work, pre_cards, run.pre_transaction, outcome)
        if run.resumed_half is None:
            run.resumed_half = "the document steps"
        if outcome["status"] == "completed":
            cp["phase"] = "committed"
            run.cp.save()
        # E11-7 item 4: `at_transaction` is the identity the transaction BEGAN at, which the
        # checkpoint's guard stored (contract section 11); `now` is the identity at the
        # resume, after the transaction's own writes. Reporting `now` made two committed-run
        # reassemblies report a dirty transaction identity while the saved guard was clean.
        assemble_and_deliver(run, rc, outcome, run.pre_transaction, pre_cards)
    if rc_doc is not None:
        rc = rcmod.Receipt(run.run_dir, rc_doc, schemas)
        work = [dict(s) for s in rc_doc["plan"]]
        for s in work:
            if not s.get("cancelled"):
                s["landed"] = True
        run.plan = work
        pre_cards = reconstruct_cards_before(run, work, [{"step": s["step"], "class": "cancelled" if s.get("cancelled") else "done"} for s in work])
        run.pre_transaction = guard["identity"] if guard else start
        cp["phase"] = "committed"
        run.cp.save()
        # E8-A11: a violation the transaction recorded is read back, so the re-assembly keeps not_clear with the cards frozen
        violations = rcmod.read_boundary(run.run_dir)
        # M1: a COMMITTED document receipt is not a completed transaction. Every resume reconciles
        # this run's landed status steps with its card events through the CLI before it reports
        # anything, so a run killed around the card append is finished here rather than delivered
        # as a split state (or as a bare validation failure).
        outcome = card_outcome(run, rc, target_document(cp), work, pre_cards, run.pre_transaction,
                               {"status": "completed", "stop_reason": None, "violations": violations,
                                "cancelled": bool(violations)})
        # E11-7 item 4: the STORED transaction identity, as above.
        assemble_and_deliver(run, rc, outcome, run.pre_transaction, pre_cards,
                             keep_existing=outcome["status"] == "completed")
    return emit(phase_document(run), 0)


# ---- small commands ---------------------------------------------------------------------------------

def cmd_identity(args):
    ok, why = identity.is_work_tree_root(os.path.abspath(args.workspace))
    if not ok:
        raise Usage("workspace %s %s" % (args.workspace, why))
    return emit(identity.identity_of(os.path.abspath(args.workspace)), 0)


def cmd_ledger(args):
    """The document's records as the LOG holds them, plus the document's own structure.

    E13 3.2: the open set, the entries and the cards come from `records.py state`; the ledger home,
    the slice headings and the fenced grant claims are the document's structure. CR-2: this command
    writes nothing, so it levels nothing — `import-legacy --dry-run` reports what the log lacks
    under `records_behind` and the view is the log as it stands.
    """
    path = os.path.abspath(args.doc)
    if not os.path.isfile(path):
        raise Usage("document does not exist: %s" % args.doc)
    workspace = os.path.abspath(args.workspace) if args.workspace else os.path.dirname(path)
    rel = os.path.relpath(path, workspace)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    parsed = ledger.parse_document(text, rel)
    start, end, create = ledger.ledger_home(parsed)
    try:
        report = rview.sync(records(), workspace, rel, dry_run=True)
        view = rview.read(records(), workspace, rel)
    except rview.RecordsStop as stop:
        return emit({"document": rel, "ok": False, "status": stop.status, "reason": stop.reason,
                     "ambiguity": stop.ambiguity, "records_behind": None,
                     "ledger_home": {"create": create, "start_line": None if create else start + 1,
                                     "end_line": None if create else end}}, 0)
    entries = []
    for e in view.entries:
        entries.append({"finding": e["finding"], "severity": e["severity"],
                        "location": "%s:%s" % (e["file"], e["line"]), "claim": e["claim"], "slice": e["slice"],
                        "state": e["state"], "last_record_line": e["last"]["line_no"],
                        "heading": e["heading"], "date": e["date"]})
    cards = []
    derived = rview.derived_cards(view.state)
    for s in parsed["slices"]:
        name = s["name"]
        open_here = view.open_entries(name)
        cards.append({"slice": name, "card": view.card(name), "open": len(open_here),
                      "mapping": derived.get(name) or view.card(name)})
    behind = rview.behind(report)
    out = {"document": rel, "ok": behind == 0, "log": view.state["log"], "head": view.head,
           "records_behind": behind, "entries": entries, "claims": parsed["claims"], "cards": cards,
           "ledger_home": {"create": create, "start_line": None if create else start + 1, "end_line": None if create else end}}
    if behind:
        # CR-2: this command writes nothing, so it cannot level the log. It says so rather than
        # answering from a log it knows is behind the document.
        out["status"] = "records_behind"
        out["reason"] = ("the log is behind %s: an import would append %d event%s. This command writes "
                         "nothing; run `start` or `record`, or `records.py import-legacy`, to level it."
                         % (rel, behind, "" if behind == 1 else "s"))
    return emit(out, 0)


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
               "assembling, verifying, adjudicating, recording, committed (E8 lane contract section 6); a terminal status other "
               "than completed or recording_failed leaves the checkpoint at phase stopped with its terminal block, and every "
               "phase command on a stopped run returns the recorded outcome (exit 10) and writes nothing (E8-A20).",
               epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--skill-root", metavar="DIR", default=None,
                   help="test only: load references from DIR instead of the script's own skill root (E8-A4)")
    p.add_argument("--records-root", metavar="DIR", default=None,
                   help="the records component's root; the first of --records-root, RECORDS_ROOT, the component beside "
                        "this plugin, and the installed shape below it that holds scripts/records.py wins (E13 3.1)")
    sub = p.add_subparsers(dest="command", metavar="command")
    sub.required = True

    def add(name, help_text, description):
        sp = sub.add_parser(name, help=help_text, description=description, formatter_class=argparse.RawDescriptionHelpFormatter,
                            epilog="exit: 0 success; 10 terminal status; 2 usage; 3 a missing dependency (jsonschema, or the records component); 1 anything else")
        sp.add_argument("--skill-root", metavar="DIR", default=argparse.SUPPRESS, help="test only: the skill root to load references from")
        sp.add_argument("--records-root", metavar="DIR", default=argparse.SUPPRESS, help="the records component's root (E13 3.1)")
        return sp

    sp = add("start", "validate the input, assemble scope, write the brief and the checkpoint",
             "start <input.json>: E8-17 references; schema and path validation (E8-6); reused id (E8-23); floor (E8-18); "
             "identity and the submodule refusal (E8-2); review sheet; scope and grants; writes input.json, checklist.md, "
             "checkpoint seq 0 (assembling) then seq 1 (verifying).\nside effects: creates the run directory after validation; "
             "on a terminal branch writes result.json and chat.md.\nstdout: {\"next\": \"verify\", \"run_dir\", \"call_id\", "
             "\"brief\", \"checklist\"} exit 0; or {\"next\": \"done\", \"status\", \"result\", \"question\", \"chat\"} exit 10.\n"
             "example: uv run recheck.py start /tmp/recheck-a-20260920-7f3c/input.json")
    sp.add_argument("input", help="the input.json to run (absolute, or relative to the current directory); missing or not JSON: exit 2")

    sp = add("check-input", "read the input and report what start would resolve; writes nothing",
             "check-input <input.json>: the bounded correction path of E11-7 item 3. Runs the "
             "schema check, the path rules and scope resolution READ-ONLY, and reports the "
             "document's own spelling of the slice beside the one the input carries, or the "
             "fields that are missing. Writes nothing anywhere and creates no run directory, "
             "so the run id is not spent.\nstdout: {\"ok\", \"where\", \"slice\", "
             "\"slice_as_given\", \"corrected_target\", \"wrote\": []} exit 0.\n"
             "example: uv run recheck.py check-input /tmp/recheck-a-20260920-7f3c.input.json")
    sp.add_argument("input", help="the input.json to check (absolute, or relative to the current directory)")

    sp = add("record-call", "register a verifier call and, on ok, retain and parse its report",
             "record-call: registers the call (E8-27); on ok retains the report at run_dir/verifier/raw.md (raw-<k>.md), parses "
             "the tail (E8-12), records raw_sha256, moves to adjudicating; a retryable status asks for one re-send under a fresh "
             "call id; a second failure stops the run (resumable: `resume` continues it as a continuation with a fresh call, the "
             "retry counters standing); a deterministic refusal is verifier_unavailable (resumable the same way).\nside effects: "
             "writes verifier/raw*.md and verifier/calls.json (a --raw under run_dir/verifier/ other than the fixed path is listed "
             "as the adapter's capture, E8-A31), rewrites the checkpoint; on a stop rewrites it at phase stopped with the terminal "
             "block, then writes result.json and chat.md.\npartial effects: an interruption after verifier/raw*.md landed and "
             "before the checkpoint rewrite leaves the report copy unrecorded; repeating the command with the same call id "
             "records it.\nexample: uv run recheck.py record-call --run-dir /tmp/r --call-id r-verify --status ok --raw /tmp/r/verifier/raw.md")
    sp.add_argument("--run-dir", required=True, metavar="D")
    sp.add_argument("--call-id", required=True, metavar="ID", help="the call id start or the previous record-call handed out")
    sp.add_argument("--status", required=True, choices=vmod.STATUSES, metavar="S", help="the transport status in the readers vocabulary: %s" % ", ".join(vmod.STATUSES))
    sp.add_argument("--raw", metavar="FILE", default=None, help="the verifier's report (required with --status ok); copied to its fixed path when elsewhere")
    sp.add_argument("--model", metavar="ID", default=None, help="the verifier's effective model id (default: unknown)")
    sp.add_argument("--kind", metavar="K", default=None, help="subagent, codex-exec, opencode-session, or the adapter's name (default: unknown)")
    sp.add_argument("--injected", metavar="NAME", nargs="+", action="extend", default=None,
                    help="channels the harness injected into the verifier; repeatable, every value lands (default: none, E8-A35)")
    sp.add_argument("--refused", metavar="TEXT", nargs="+", action="extend", default=None,
                    help="prohibited actions refused with no side effect; repeatable, one per action, every value lands (E8-5, E8-A35)")
    sp.add_argument("--note", metavar="TEXT", default=None, help="the transport's reason text (used in stop_reason on a refusal)")

    sp = add("adjudicate", "adjudicate one item from the retained report",
             "adjudicate: validates the (verifier_said, driver_action) pair against section 7 and the item rules of the schema; "
             "E8-13 records an upgrade under session_wrote_fix as disputed; stores the item done and rewrites the checkpoint.\n"
             "downgraded needs --reason and --note; upgraded needs --upgrade-evidence; confirmed with --reason and "
             "--note corrects one not_fixed reason to another on that evidence, leaving the disposition and the "
             "retained report alone (E11-7 item 3).\n"
             "example: uv run recheck.py adjudicate --run-dir /tmp/r --item 0 --action confirmed")
    sp.add_argument("--run-dir", required=True, metavar="D")
    sp.add_argument("--item", required=True, type=int, metavar="N", help="the checklist index (from 0)")
    sp.add_argument("--action", required=True, choices=("confirmed", "downgraded", "upgraded", "disputed"))
    sp.add_argument("--reason", choices=vmod.REASONS, default=None,
                    help="with downgraded: the not_fixed reason. With confirmed on a verifier "
                         "not_fixed: the corrected reason, on the evidence in --note; the "
                         "disposition is unchanged and the retained report is never edited "
                         "(E11-7 item 3)")
    sp.add_argument("--note", metavar="T", default=None, help="the driver's note (required with downgraded, and with a --reason correction: its evidence)")
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
             "record: the retained reports re-proved against their recorded SHA-256 and tail (a mismatch stops the run as "
             "`evidence changed: <path>`, no project write, E8-A26), the identity check, the plan with every target's containment "
             "(E8-A19), the transaction guard stored in the checkpoint as the transaction begins (the pre-transaction identity, the "
             "digest of the non-target diff, the targets, E8-A45), receipt.json, the receipted steps (reopening lines, the block, "
             "waiver lines, the verdict-doc copy, the status lines), the boundary check before every status line (a violation "
             "found before status step k cancels step k and every later one; a status line already done stands and its card is "
             "listed as moved before the violation was found, E8-A44), the commit point, result.json and chat.md.\npartial effects: "
             "a failure between steps ends recording_failed with the receipt naming what landed (a target outside the workspace "
             "ends the same way with nothing landed); a stale identity or changed evidence leaves the checkpoint at phase stopped; "
             "resume completes the rest of a recording_failed run.\nexample: uv run recheck.py record --run-dir /tmp/r")
    sp.add_argument("--run-dir", required=True, metavar="D")

    sp = add("resume", "continue a run from its checkpoint (section 11)",
             "resume <input.json>: the validation order of section 11 (checkpoint and its terminal block: a stopped run continues "
             "only when resumable, else refused at step 1; integrity; binding; item states; receipt, whose entries must prove the "
             "state and whose fully-done targets must rest at their final hash, else refused at step 5 or ended recording_failed "
             "as an outside edit; identity against the transaction guard when one is stored, else the start identity, a "
             "guard-less checkpoint inside a transaction from a dirty start refused), the continuation limit (a grant's turn_ref is "
             "consumed once, E8-A23), then the first pending item (report reuse or a fresh call), else the first plan step not "
             "done (replay), else re-assembly.\nside effects: a refused or ended resume changes no byte of the checkpoint or the "
             "receipt (an outside edit or a stale identity delivers result.json and chat.md only); a continuing resume rewrites "
             "run_dir/input.json as the presented input minus the continuation grant (E8-A30) and increments the count.\n"
             "example: uv run recheck.py resume /tmp/r/input.json")
    sp.add_argument("input", help="the presented input with resume: true")

    sp = add("identity", "the six-field identity of a workspace (real submodule list)", "identity <workspace>")
    sp.add_argument("workspace")

    sp = add("ledger", "parse a document's records, open set, cards, and ledger home", "ledger <doc> [--workspace W]")
    sp.add_argument("doc")
    sp.add_argument("--workspace", metavar="W", default=None, help="the workspace root the document path is relative to")

    add("skill-identity", "{name, version, commit, content_sha256} from the skill root", "skill-identity")
    return p


COMMANDS = {"start": cmd_start, "check-input": cmd_check_input, "record-call": cmd_record_call, "adjudicate": cmd_adjudicate, "new-defect": cmd_new_defect,
            "record": cmd_record, "resume": cmd_resume, "identity": cmd_identity, "ledger": cmd_ledger, "skill-identity": cmd_skill_identity}


def open_records(args):
    """E13 3.1: resolve and confirm the records component before any command runs.

    A missing component, or one speaking another interface version, is the pilot's exit 3 shape:
    one line on stderr, nothing on stdout. `--help` and argument checking never reach this point,
    because argparse answers them first.
    """
    try:
        return rcl.open_client(records_root=getattr(args, "records_root", None))
    except rcl.ComponentUnavailable as refusal:
        log(str(refusal))
        sys.exit(3)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate.require_jsonschema()
    if not hasattr(args, "skill_root"):
        args.skill_root = None
    if not hasattr(args, "records_root"):
        args.records_root = None
    RECORDS[:] = [open_records(args)]
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
