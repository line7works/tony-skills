#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""build.py: the phase driver of build-v2 (E13 lane contract section 9).

    uv run build.py check-input <input.json>
    uv run build.py contract --run-dir D
    uv run build.py preflight --run-dir D
    uv run build.py record-answer --run-dir D --answer FILE
    uv run build.py report --run-dir D
    uv run build.py identity <workspace>
    uv run build.py skill-identity

The executor (the model running SKILL.md) builds the slice and supplies its judgment ONCE, as
the recorded answer handed to `record-answer`. Every deterministic step is this script's: the
input's schema and its path rules, the slice's contract read from the build doc, the source set
computed from git, the records the component holds, the comparison of the source set with the
paths the slice names, the checks' results, the card decision, the one event and the one
document line, the result and its validation. This script never judges code (E13-4): what the
executor concluded is recorded with who concluded it.

stdout: one JSON document and nothing else, carrying `interface_version`, `plugin_version` and
`next` (contract, preflight, record-answer, report, done). stderr: diagnostics.

Exit codes (the A7a set of docs/plans/2026-09-13-recheck-v2-e8-core.md section 6; see
build_core/exits.py):

    0   an intermediate phase finished and the run has more to do
    2   usage: a bad argument, a file that is not there or is not JSON, a phase command against
        the wrong phase
    3   missing dependency: `jsonschema`, or the records component missing or at another
        interface version. One line on stderr, nothing on stdout
    4   validation: a supplied FILE failed its schema (`check-input`, `record-answer`). The
        errors are on stdout, nothing is written, and the run stays where it was, so a corrected
        file can be supplied and the command rerun
    10  the run reached a terminal status: a completion (`completed`, `checks_not_passed`,
        `not_complete`, `answer_refused`) or a stop (`stopped`). A refused records call ends the
        run here, carrying the component's own sentence
    1   anything else: a defect of this script, a git failure, an unreadable run directory

Side effects, per command. `check-input` creates the run directory and writes `input.json`,
`checkpoint.json` and `checkpoint.log`. `contract` writes `contract.json` and rewrites the
checkpoint. `preflight` levels the document's log through the records component
(`import-legacy`, which writes only under `docs/records/` and only when the run is not
report-only) and rewrites the checkpoint. `record-answer` writes `answer.json` and rewrites the
checkpoint. `report` writes `receipt.json` and `receipt.log`, appends at most ONE `card_set`
event through the component, writes the slice's `Status:` line in the build doc, and writes
`result.json`. A report-only run writes none of the last three and says so.

Partial effects a failed command may leave. `check-input` interrupted after validation leaves
the run directory with `input.json` and a seq-0 checkpoint. `report` interrupted inside the
transaction leaves `receipt.json` naming which half landed; running `report` again settles it,
against the head the receipt already names, and never appends twice. A checkpoint or receipt
rewrite interrupted between its log line and the rename leaves the one tolerated state, which
the next read drops.

Repeating a command is safe. A phase command against a run that already ended reports the
recorded outcome, writes nothing, and exits 10 — except `report`, which always reconciles the
card event with the log first, because completing the document step is not on its own a
completed transaction.

--skill-root DIR and --records-root DIR (test hooks): load the references from DIR, and resolve
the records component at DIR instead of through the four lookups.

Test hooks, honored only with BUILD_TEST=1 in the environment. Each makes the real failure
happen rather than simulating its message:
  BUILD_TEST_NO_JSONSCHEMA=1   behave as if jsonschema were not importable (exit 3)
  BUILD_TEST_NO_RECORDS=1      behave as if no records component were installed (exit 3)

There is no hook for the transaction's two crash windows. `tests/shimlib.py` puts a stand-in
`records.py` in front of the component through the resolver's own `RECORDS_ROOT` route and kills
this process with SIGKILL on either side of the append, which is the real kill rather than an
exception raised in its place.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_core import answer as answermod  # noqa: E402
from build_core import canon, checks as checksmod, doc as docmod, exits, inputs  # noqa: E402
from build_core import records_link as link, result as resultmod, scope, sources  # noqa: E402
from build_core import statefile, transaction, validate, view  # noqa: E402
from build_core.records_client import ComponentUnavailable, RecordsRefusal  # noqa: E402

INTERFACE_VERSION = 1

# The phase a run is at, and the command that follows it. `references/checkpoint.schema.json`
# publishes the same list, and a phase command against the wrong phase names the next one.
NEXT_OF = {"checked": "contract", "contracted": "preflight", "preflighted": "record-answer",
           "answered": "report", "reported": "done", "stopped": "done"}

RECORDS = []


def records():
    return RECORDS[0]


EXAMPLES = """examples:
  uv run build.py check-input /tmp/build-c-20260922-7f3c/input.json
  -> {"next": "contract", "run_dir": "...", "slice": "C", ...}                       exit 0
  uv run build.py contract --run-dir /tmp/build-c-20260922-7f3c
  -> {"next": "preflight", "contract": {"named_paths": [...], "checks": [...]}, ...}  exit 0
  uv run build.py preflight --run-dir /tmp/build-c-20260922-7f3c
  -> {"next": "record-answer", "source_set": {...}, "card": "not started", ...}       exit 0
  uv run build.py record-answer --run-dir /tmp/build-c-20260922-7f3c --answer answer.json
  -> {"next": "report", "answer_refusals": [], ...}                                   exit 0
  uv run build.py report --run-dir /tmp/build-c-20260922-7f3c
  -> {"next": "done", "status": "checks_not_passed", "result": ".../result.json"}     exit 10
"""

PHASE_HELP = """the phases, in order, and what each takes:

  check-input <input.json>          the one validated input structure (references/input.schema.json):
                                    workspace, run_dir, build_doc, slice, base, report_only,
                                    allow_open_blocker, rerun_checks, invocation. Creates the run.
  contract --run-dir D              reads the slice from the build doc and writes the run's
                                    contract file: the requirements, the paths the slice names,
                                    the checks it names, and its stated boundaries. Before any
                                    edit is recorded.
  preflight --run-dir D             the source set from git (committed, changed, untracked, and
                                    the base), the log levelled with the document, the slice's
                                    open findings and its card, and the six-field identity.
                                    Refuses a slice with an open BLOCKER unless the input says
                                    allow_open_blocker.
  record-answer --run-dir D         the recorded executor answer (references/answer.schema.json):
                --answer FILE       what it claims, the files it says it touched with the reason
                                    for each, and the result and output of each check.
  report --run-dir D                compares the source set with the paths the slice names,
                                    reports every check, decides the card, records the one card
                                    event and writes the slice's `Status:` line, and writes the
                                    result. Settles an unfinished transaction from an earlier run.
  identity <workspace>              the six-field source identity, as the records component
                                    computes it.
  skill-identity                    name, version, commit and content hash of this skill.
"""


# ---- the envelope ----------------------------------------------------------------------------

class Usage(RuntimeError):
    """A usage slip: exit 2 with the sentence on stderr."""


class Defect(RuntimeError):
    """Anything else: exit 1."""


class Terminal(RuntimeError):
    """The run reached a terminal status; the document is already assembled."""

    def __init__(self, document):
        RuntimeError.__init__(self, document.get("status", "terminal"))
        self.document = document


def envelope(root=None, **fields):
    out = {"interface_version": INTERFACE_VERSION, "plugin_version": validate.plugin_version(root)}
    out.update(fields)
    return out


def emit(document, code=exits.SUCCESS):
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return code


def now_utc():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# ---- the run ----------------------------------------------------------------------------------

class Run:
    """One run: its directory, its checkpoint, and the writes it has made."""

    def __init__(self, run_dir, state, root=None):
        self.run_dir = run_dir
        self.state = state
        self.root = root

    # -- construction -----------------------------------------------------------------------

    @classmethod
    def create(cls, run_dir, doc, root=None):
        os.makedirs(run_dir, exist_ok=True)
        path, log_path = statefile.checkpoint_paths(run_dir)
        if os.path.exists(path) or os.path.exists(log_path):
            raise Usage("the run directory %s already holds a checkpoint: this run id has been "
                        "used. Use another run id, or `report --run-dir` to settle the run that "
                        "is there." % run_dir)
        at = now_utc()
        state = statefile.StateFile.create(path, log_path, {
            "checkpoint_version": 1,
            "run_id": doc["run_id"],
            "phase": "checked",
            "input_sha256": inputs.input_digest(doc),
            "input": doc,
            "at": at,
            "run_date": at[:10],
            "contract": None,
            "source_set": None,
            "identity": None,
            "card_before": None,
            "records_pin": None,
            "records": None,
            "answer": None,
            "answer_sha256": None,
            "terminal": None,
            "writes": [],
        })
        return cls(run_dir, state, root)

    @classmethod
    def open(cls, run_dir, root=None):
        path, log_path = statefile.checkpoint_paths(run_dir)
        if not os.path.isfile(path):
            raise Usage("no run at %s: its checkpoint.json is not there. Run `check-input` first."
                        % run_dir)
        try:
            state = statefile.StateFile.open(path, log_path)
        except statefile.StateCorrupt as exc:
            raise Usage("the run at %s cannot be continued: %s" % (run_dir, exc))
        return cls(run_dir, state, root)

    # -- accessors ---------------------------------------------------------------------------

    @property
    def doc(self):
        return self.state.doc

    @property
    def input(self):
        return self.doc["input"]

    @property
    def workspace(self):
        return self.input["workspace"]

    @property
    def document(self):
        return self.input["build_doc"]

    @property
    def slice_name(self):
        return self.input["slice"]

    @property
    def report_only(self):
        return bool(self.input.get("report_only"))

    @property
    def run_id(self):
        return self.doc["run_id"]

    def require_phase(self, command, *allowed):
        """A phase command out of turn is a usage slip that names the command to run instead."""
        phase = self.doc.get("phase")
        if phase not in allowed:
            raise Usage("this run is at phase %r; `%s` runs at %s. Run `%s` next."
                        % (phase, command, " or ".join(repr(a) for a in allowed),
                           NEXT_OF.get(phase, "report")))

    def artifact(self, name):
        return os.path.join(self.run_dir, name)

    def record_write(self, path, kind, digest=None):
        writes = list(self.doc.get("writes") or [])
        for entry in writes:
            if entry["path"] == path and entry["kind"] == kind:
                entry["sha256_after"] = digest
                self.doc["writes"] = writes
                return
        writes.append({"path": path, "kind": kind, "sha256_after": digest})
        self.doc["writes"] = writes

    def write_artifact(self, name, body):
        path = self.artifact(name)
        canon.write_json(path, body)
        self.record_write(path, "run_artifact", canon.sha256_file(path))
        return path

    def save(self, phase=None):
        if phase:
            self.doc["phase"] = phase
        self.state.save()

    # -- terminal ----------------------------------------------------------------------------

    def deliver(self, result):
        """Validate the result, write it, mark the checkpoint, and raise Terminal."""
        path = self.artifact("result.json")
        result["writes"] = list(self.doc.get("writes") or []) + [
            {"path": path, "kind": "run_artifact", "sha256_after": None}]
        errors = []
        try:
            schema = validate.load_schema("result", self.root)
            errors = validate.errors_for(result, schema)
            semantic = validate.run_semantic(result, self.input, self.run_dir)
        except validate.ReferenceUnavailable as exc:
            semantic = {"semantic": [{"id": "-", "path": "/", "message": str(exc)}], "skipped": []}
        canon.write_json(path, result)
        self.record_write(path, "run_artifact", canon.sha256_file(path))
        self.doc["terminal"] = {"status": result["status"],
                                "terminal_status": result["terminal_status"],
                                "reason": result["reason"], "result": path}
        self.save("reported" if result["status"] != "stopped" else "stopped")
        document = envelope(self.root, next="done", status=result["status"],
                            terminal_status=result["terminal_status"],
                            reason=result["reason"], result=path,
                            run_id=self.run_id)
        if errors or semantic["semantic"]:
            document["validation"] = {"schema": errors, "semantic": semantic["semantic"]}
        raise Terminal(document)

    def recorded_outcome(self):
        terminal = self.doc.get("terminal") or {}
        return envelope(self.root, next="done", status=terminal.get("status"),
                        terminal_status=terminal.get("terminal_status"),
                        reason="the run ended as %s: %s" % (terminal.get("status"),
                                                            terminal.get("reason")),
                        result=terminal.get("result"), run_id=self.run_id)


# ---- result assembly -------------------------------------------------------------------------

REPORT_ONLY_RERUN = ("report-only: a check command is an unrestricted child process that could "
                     "write to the workspace, and a report-only run writes nothing there, so no "
                     "check command was run")
REFUSED_ANSWER_RERUN = ("the recorded answer was refused, and a refused answer is honoured before "
                        "any check subprocess is launched, so no check command was run")


def stop(run, tag, reason, **extra):
    """Assemble and deliver a stop: the tool could not proceed."""
    run.deliver(resultmod.assemble(run, status="stopped", reason=reason, stop_tag=tag,
                                   stop_reason=reason, root=run.root, **extra))


# ---- the phases --------------------------------------------------------------------------------

def phase_check_input(args):
    """Validate the input, create the run, and write the resolved input."""
    schemas = {"input": validate.load_schema("input", args.skill_root)}
    try:
        doc = inputs.read(args.input)
    except inputs.InputUnreadable as exc:
        raise Usage(str(exc))
    doc = inputs.with_defaults(doc)
    errors = inputs.validate_input(doc, schemas, args.skill_root)
    if errors:
        return emit(envelope(args.skill_root, ok=False, error="invalid",
                             reason="the input does not validate: %d finding(s); nothing was "
                                    "written and no run was created" % len(errors),
                             errors=errors), exits.VALIDATION)
    run = Run.create(doc["run_dir"], doc, args.skill_root)
    run.write_artifact("input.json", doc)
    run.save("checked")
    return emit(envelope(args.skill_root, next="contract", run_id=run.run_id, run_dir=run.run_dir,
                         workspace=run.workspace, build_doc=run.document, slice=run.slice_name,
                         base=doc["base"], report_only=run.report_only,
                         input=run.artifact("input.json")))


def phase_contract(args):
    """Read the slice from the build doc and fix the scope before any edit is recorded."""
    run = Run.open(args.run_dir, args.skill_root)
    if run.doc.get("terminal"):
        return emit(run.recorded_outcome(), exits.TERMINAL)
    run.require_phase("contract", "checked")
    try:
        text = docmod.read(run.workspace, run.document)
        entry = docmod.find_slice(text, run.slice_name)
    except docmod.DocumentError as exc:
        tag = "no_doc" if "not in the workspace" in str(exc) else "no_slice"
        return stop(run, tag, str(exc))
    contract = {
        "path": run.artifact("contract.json"),
        "named_paths": docmod.named_paths(entry),
        "requirements": docmod.requirements(entry),
        "checks": docmod.checks(entry),
        "not_in_slice": docmod.not_in_slice(entry),
    }
    run.doc["contract"] = contract
    run.doc["card_before"] = (entry["status"] or "").strip() or "none"
    run.write_artifact("contract.json", {
        "run_id": run.run_id, "build_doc": run.document, "slice": run.slice_name,
        "slice_title": entry["title"], "status_line": entry["status_line"],
        "card": run.doc["card_before"],
        "named_paths": contract["named_paths"], "requirements": contract["requirements"],
        "checks": contract["checks"], "not_in_slice": contract["not_in_slice"],
    })
    run.save("contracted")
    return emit(envelope(args.skill_root, next="preflight", run_id=run.run_id,
                         contract=contract, card=run.doc["card_before"]))


def phase_preflight(args):
    """The source set, the log levelled with the document, the slice's standing, the identity."""
    run = Run.open(args.run_dir, args.skill_root)
    if run.doc.get("terminal"):
        return emit(run.recorded_outcome(), exits.TERMINAL)
    run.require_phase("preflight", "contracted")

    try:
        source = sources.source_set(run.workspace, run.input["base"], run.document)
    except sources.GitError as exc:
        tag = "no_base" if "base ref" in str(exc) else "no_git"
        return stop(run, tag, str(exc))
    run.doc["source_set"] = source

    client = records()
    try:
        levelled = view.level(client, run.workspace, run.document, dry_run=run.report_only)
        state = view.state_of(client, run.workspace, run.document)
        rows = view.card_events(client, run.workspace, run.document)
        walked = view.head_of(client, run.workspace, run.document)
        identity = client.identity(run.workspace)["identity"]
    except view.RecordsStop as exc:
        return stop(run, exc.tag, exc.reason, records_extra={"refused": exc.refused_block()},
                    unplaced=exc.detail.get("unplaced"))
    except RecordsRefusal as refusal:
        exc = view.stop_for(refusal, "preflight could not read the records of %s" % run.document)
        return stop(run, exc.tag, exc.reason, records_extra={"refused": exc.refused_block()})

    card, _written = view.document_card(run.workspace, run.document, run.slice_name)
    card = card or "none"
    opened = view.open_counts(state, run.slice_name)
    drift = view.card_drift(rows, run.slice_name, card)
    records_block = {
        "log": state.get("log"), "levelled": levelled, "head_before": walked["head"],
        "head_after": walked["head"], "pinned_head": walked["head"], "open": opened,
        "appended": [], "wrote": bool(levelled.get("imported")), "refused": None,
    }
    run.doc["records"] = records_block
    run.doc["identity"] = identity
    run.doc["card_before"] = card
    run.doc["records_pin"] = {"doc": run.document, "log": state.get("log"), "head": walked["head"]}
    if records_block["wrote"]:
        run.record_write(state.get("log"), "records_log")

    if drift is not None:
        return stop(run, "card_drift", view.drift_sentence(run.slice_name, run.document, drift))

    if opened.get("BLOCKER") and not run.input.get("allow_open_blocker"):
        return stop(run, "open_blocker",
                    "slice %s of %s carries %d open BLOCKER finding(s) in the records. A slice "
                    "with an open BLOCKER is not a foundation to frame on: clear or waive them "
                    "through the loop's clearing stations, or set `allow_open_blocker` in the "
                    "input to build on it anyway."
                    % (run.slice_name, run.document, opened["BLOCKER"]))

    run.save("preflighted")
    return emit(envelope(args.skill_root, next="record-answer", run_id=run.run_id,
                         source_set=source, card=card, open=opened, records=records_block,
                         identity=identity))


def phase_record_answer(args):
    """Store what the executor concluded, and say at once which contents rules it breaks."""
    run = Run.open(args.run_dir, args.skill_root)
    if run.doc.get("terminal"):
        return emit(run.recorded_outcome(), exits.TERMINAL)
    run.require_phase("record-answer", "preflighted")

    try:
        body = answermod.read(args.answer)
    except answermod.AnswerUnreadable as exc:
        raise Usage(str(exc))
    errors = answermod.validate_answer(body, root=args.skill_root)
    if errors:
        return emit(envelope(args.skill_root, ok=False, error="invalid",
                             reason="the recorded answer does not validate: %d finding(s); nothing "
                                    "was written and the run stays at `preflighted`, so a corrected "
                                    "answer can be supplied and this command rerun" % len(errors),
                             errors=errors), exits.VALIDATION)
    refusals = answermod.contents_refusals(body, case=(run.input.get("case")))
    run.doc["answer"] = body
    run.doc["answer_sha256"] = answermod.digest(body)
    run.write_artifact("answer.json", body)
    run.save("answered")
    return emit(envelope(args.skill_root, next="report", run_id=run.run_id,
                         answer_accepted=not refusals, answer_refusals=refusals,
                         session_id=body.get("session_id"),
                         claimed_status=body.get("claimed_status"),
                         claimed_card=body.get("claimed_card")))


def phase_report(args):
    """Compare, decide, record, write, and deliver the result."""
    run = Run.open(args.run_dir, args.skill_root)
    client = records()

    # A transaction that was opened is SETTLED, never re-planned. This is the first thing every
    # pass does, before the head comparison and before any fresh plan, for three reasons the
    # outside reviewer's look at the pilot names: a re-plan would read a fresh head and append
    # against it (finding 3); it would take the document's current bytes as its baseline
    # (finding 2); and a committed document step is not on its own a completed transaction, so a
    # run that already reported still owes the reconciliation (finding 1). The head this run read
    # its state against moved when its OWN append landed, so the between-the-phases check below
    # must not see that event either — the settle owns this window, the pin owns the other.
    receipt = _existing_receipt(run)
    if receipt is not None and receipt.doc.get("card_append"):
        block = receipt.doc["card_append"]
        finished = bool(block.get("head")) and bool((receipt.doc.get("document_step") or {}).get("done"))
        if not finished:
            return _settle(run, client, receipt)

    if run.doc.get("terminal"):
        return emit(run.recorded_outcome(), exits.TERMINAL)
    run.require_phase("report", "answered")

    body = run.doc["answer"]
    contract = run.doc["contract"]
    source = run.doc["source_set"]
    records_block = dict(run.doc["records"])

    # The head the open set was read against must still be the log's head, taken BEFORE this
    # run's own levelling pass, so CR-1's import events are never what this flags.
    pin = run.doc.get("records_pin") or {}
    try:
        walked = view.head_of(client, run.workspace, run.document)
        if pin.get("head") and walked["head"] != pin["head"]:
            return stop(run, "records_conflict",
                        "the log of %s is at head %s, not the %s this run read the slice's state "
                        "against. Another writer appended to it between preflight and report, and "
                        "nothing this run decided accounts for that event. Re-read the log and "
                        "decide; no record was written."
                        % (run.document, walked["head"][:12], pin["head"][:12]),
                        records_extra=records_block)
        levelled = view.level(client, run.workspace, run.document, dry_run=run.report_only)
        state = view.state_of(client, run.workspace, run.document)
        rows = view.card_events(client, run.workspace, run.document)
    except view.RecordsStop as exc:
        records_block["refused"] = exc.refused_block()
        return stop(run, exc.tag, exc.reason, records_extra=records_block,
                    unplaced=exc.detail.get("unplaced"))

    card_before, _written = view.document_card(run.workspace, run.document, run.slice_name)
    card_before = card_before or "none"
    drift = view.card_drift(rows, run.slice_name, card_before)
    records_block["levelled"] = levelled
    records_block["head_before"] = state["head"]
    records_block["head_after"] = state["head"]
    records_block["pinned_head"] = state["head"]
    records_block["log"] = state.get("log")
    records_block["open"] = view.open_counts(state, run.slice_name)
    if levelled.get("imported"):
        records_block["wrote"] = True
        run.record_write(state.get("log"), "records_log")
    run.doc["records_pin"] = {"doc": run.document, "log": state.get("log"), "head": state["head"]}
    run.doc["card_before"] = card_before

    if drift is not None:
        return stop(run, "card_drift", view.drift_sentence(run.slice_name, run.document, drift),
                    records_extra=records_block)

    # Astra's F15: a refused answer is honoured BEFORE any check subprocess is launched, and a
    # report-only run launches none in the live workspace (report-only covers child writes too).
    refusals = answermod.contents_refusals(body, case=run.input.get("case"))
    wants_rerun = bool(run.input.get("rerun_checks"))
    blocked = REPORT_ONLY_RERUN if (wants_rerun and run.report_only) else None
    reruns = wants_rerun and not refusals and not blocked
    before_checks = before_bytes = None
    if reruns:
        before_bytes = checksmod.workspace_digest(run.workspace)
        try:
            before_checks = client.identity(run.workspace)["identity"]
        except RecordsRefusal as refusal:
            exc = view.stop_for(refusal, "the identity of %s could not be read before the check "
                                         "reruns" % run.workspace)
            records_block["refused"] = exc.refused_block()
            return stop(run, exc.tag, exc.reason, records_extra=records_block)
    check_rows = checksmod.rows(contract["checks"], body.get("checks"), workspace=run.workspace,
                                rerun=wants_rerun and not refusals, rerun_blocked=blocked)
    after_bytes = checksmod.workspace_digest(run.workspace) if before_bytes is not None else None
    if wants_rerun and refusals:
        for row in check_rows:
            if row.get("named_by_slice"):
                row["rerun_refused"] = REFUSED_ANSWER_RERUN

    # Astra's F1: the source set and the identity the card is decided and recorded on are the
    # ones AT REPORT, after any rerun and before the scope decision, against the base commit
    # preflight pinned. Preflight's set is what the run started from; what reaches the card is
    # what is on disk now. A set or an identity that cannot be computed stops the run.
    pinned = run.doc["source_set"]
    try:
        source = sources.source_set(run.workspace, pinned["base_commit"], run.document)
    except sources.GitError as exc:
        tag = "no_base" if "base ref" in str(exc) else "no_git"
        return stop(run, tag, "at report: %s" % exc, records_extra=records_block,
                    checks=check_rows)
    source["base"] = pinned["base"]
    try:
        identity = client.identity(run.workspace)["identity"]
    except RecordsRefusal as refusal:
        exc = view.stop_for(refusal, "the identity of %s could not be read at report"
                            % run.workspace)
        records_block["refused"] = exc.refused_block()
        return stop(run, exc.tag, exc.reason, records_extra=records_block, checks=check_rows)
    run.doc["source_set"] = source
    run.doc["identity"] = identity
    # Astra's F15 remainder: the identity misses a git-IGNORED file, so the bytes are measured too
    # (`checks.workspace_digest`, `.git` excluded, ignored files included). Either moving is a
    # child write, and the result never claims `wrote_nothing` over it.
    run.doc["checks_changed_workspace"] = bool(
        (before_checks is not None and before_checks != identity)
        or (before_bytes is not None and before_bytes != after_bytes))

    # Scope adherence: every source-set path the slice does not name, with the stated reason.
    out_rows = scope.out_of_scope(source, contract["named_paths"],
                                  answermod.reasons_by_path(body), contract["not_in_slice"])

    common = {"out_of_scope": out_rows, "checks": check_rows, "records_extra": records_block,
              "answer_refusals": refusals}

    if scope.unexplained(out_rows) and not refusals:
        return stop(run, "scope_unexplained", scope.stop_sentence(out_rows), **common)

    if refusals:
        return run.deliver(resultmod.assemble(
            run, status="answer_refused", refusal_reason=answermod.REFUSAL_TAG,
            reason="the recorded answer is not recordable: %s. It was neither acted on nor "
                   "repaired: the card stays at %r and no event was appended."
                   % (refusals[0], card_before),
            root=run.root, **common))

    not_passed = checksmod.not_passed(check_rows)
    claims_complete = body.get("claimed_status") == "complete"

    if not_passed:
        names = ", ".join("%s (%s)" % (row["name"], row["result"]) for row in not_passed)
        return run.deliver(resultmod.assemble(
            run, status="checks_not_passed",
            reason="%d of the slice's named checks did not pass: %s. Each is reported with its "
                   "output and the card stays at %r; this is a completed run that says so, not a "
                   "stop." % (len(not_passed), names, card_before),
            root=run.root, **common))

    if not claims_complete:
        return run.deliver(resultmod.assemble(
            run, status="not_complete",
            reason="the recorded answer claims %r, so the slice is not finished and the card stays "
                   "at %r; every named check passed." % (body.get("claimed_status"), card_before),
            root=run.root, **common))

    # The card moves — unless it already stands at `built` (Astra's F11): then there is nothing
    # to move, so no transaction is opened, no `card_set` is appended and no `Status:` line is
    # written, and the result says the card was already built.
    after = "built"
    if card_before == after:
        return run.deliver(resultmod.assemble(
            run, status="completed",
            reason="the slice is complete, every named check passed, and every out-of-scope path "
                   "carries a reason. The card already stands at `built`, so nothing was moved: no "
                   "card event was appended and no `Status:` line was written.",
            card_after=card_before, card_moved=False,
            card_reason="the card was already `built`; a build moves it to `built` and nowhere "
                        "else, so there was no move to make",
            root=run.root, **common))
    if run.report_only:
        return run.deliver(resultmod.assemble(
            run, status="completed",
            reason="the slice is complete, every named check passed, and every out-of-scope path "
                   "carries a reason. This is a report-only run: nothing was written to the "
                   "workspace and nothing to the log, so the card stays at %r." % card_before,
            card_after=card_before, card_moved=False,
            card_reason="report-only: the card would move to `built`, and this run writes nothing",
            root=run.root, **common))

    try:
        text = docmod.read(run.workspace, run.document)
        entry = docmod.find_slice(text, run.slice_name)
    except docmod.DocumentError as exc:
        return stop(run, "no_slice", str(exc), **common)

    # Astra's N2: the completion this run is about to make is validated BEFORE the card
    # transaction opens, against the same schema and semantic checks `deliver` and
    # `validate-result.py` apply. An invalid completion is never committed: the run stops with
    # `result_invalid`, nothing appended and no `Status:` line written.
    proposed = resultmod.assemble(
        run, status="completed", reason="the proposed completion, before the card transaction",
        card_after=after, card_moved=True, card_reason="proposed", root=run.root, **common)
    invalid = proposed_findings(run, proposed)
    if invalid:
        return stop(run, "result_invalid",
                    "the completion this run would record does not validate (%s), so no card "
                    "transaction was opened: no event was appended and the `Status:` line was not "
                    "written" % "; ".join(invalid), **common)

    # The facts the card decision was made on, kept before the transaction opens. A settling pass
    # re-delivers THESE, and never recomputes them: rerunning a check command on a settle could
    # observe something else, and the decision the receipt is settling was made on what is here.
    run.doc["decision"] = {"out_of_scope": out_rows, "checks": check_rows,
                           "card_before": card_before, "card_after": after,
                           "source_set": source, "identity": identity}
    run.save()          # persisted BEFORE the transaction opens, or a kill would lose it
    receipt, _ = transaction.open_receipt(run.run_dir, run.run_id, run.document, run.slice_name)
    run.record_write(receipt.path, "run_artifact")
    event = transaction.plan(receipt, client, run.workspace, run.document, entry, run.slice_name,
                             card_before, after, run.run_id, body["session_id"],
                             (run.input.get("invocation") or {}).get("harness"),
                             run.doc["at"], run.doc["identity"])
    try:
        appended = transaction.append_card(receipt, client, run.workspace, run.document, event,
                                           receipt.doc["card_append"]["expected_head"], run.run_dir)
    except view.RecordsStop as exc:
        records_block["refused"] = exc.refused_block()
        common["records_extra"] = records_block
        return stop(run, exc.tag, exc.reason, receipt=receipt.path, **common)
    return _finish(run, client, receipt, appended, after, card_before, common, resumed_half=None)


def proposed_findings(run, proposed):
    """The schema errors and semantic findings of a proposed result, as short sentences."""
    try:
        errors = validate.errors_for(proposed, validate.load_schema("result", run.root))
        semantic = validate.run_semantic(proposed, run.input, run.run_dir)["semantic"]
    except validate.ReferenceUnavailable as exc:
        return [str(exc)]
    out = ["%s: %s" % (row.get("path") or "/", row.get("message")) for row in errors or []
           if isinstance(row, dict)]
    out.extend("%s %s: %s" % (row["id"], row["path"], row["message"]) for row in semantic)
    return out


def _finish(run, client, receipt, appended, after, card_before, common, resumed_half):
    """The document half, then the result. Shared by a first pass and a settling one."""
    records_block = dict(common["records_extra"])
    records_block["log"] = receipt.doc["card_append"]["log"]
    records_block["head_after"] = receipt.doc["card_append"].get("head")
    records_block["wrote"] = True
    rows = []
    for index, seq in enumerate(receipt.doc["card_append"].get("seqs") or []):
        row = {"kind": "card_set", "seq": seq}
        if receipt.doc["card_append"].get("recovered"):
            row["recovered"] = True
        rows.append(row)
    records_block["appended"] = rows
    run.record_write(records_block["log"], "records_log")
    common = dict(common)
    common["records_extra"] = records_block

    try:
        wrote, step = transaction.write_document_step(receipt, run.workspace)
    except transaction.OutsideEdit as exc:
        return stop(run, "outside_edit", str(exc), receipt=receipt.path,
                    resumed_half=resumed_half, **common)
    if step is not None:
        run.record_write(run.document, "status_line", step.get("sha256_after"))

    return run.deliver(resultmod.assemble(
        run, status="completed",
        reason="the slice is complete, every named check passed, and every out-of-scope path "
               "carries a reason: the card event was recorded at seq %s and the slice's `Status:` "
               "line was set to %r."
               % (", ".join(str(r["seq"]) for r in rows) or "-", after),
        card_after=after, card_moved=True,
        card_reason="the answer claimed `complete`, every named check passed, and no path is out "
                    "of scope without a reason",
        card_line=(step or {}).get("line"), receipt=receipt.path, resumed_half=resumed_half,
        root=run.root, **common))


def _existing_receipt(run):
    """The receipt of a transaction this run already opened, or None. A corrupt one is a stop."""
    path, log_path = statefile.receipt_paths(run.run_dir)
    if not os.path.isfile(path):
        return None
    try:
        return statefile.StateFile.open(path, log_path)
    except statefile.StateCorrupt as exc:
        raise Usage("the receipt at %s cannot be read: %s" % (path, exc))


def _settle(run, client, receipt):
    """Settle an unfinished transaction and deliver the run's result."""
    body = run.doc.get("answer") or {}
    event = link.card_event(run.document, run.slice_name,
                            (receipt.doc["card_append"]["event"])["before"],
                            (receipt.doc["card_append"]["event"])["after"],
                            receipt.doc["card_append"]["event"].get("run_id") or run.run_id,
                            (run.input.get("invocation") or {}).get("harness"),
                            run.doc["at"], run.doc["identity"])
    decision = run.doc.get("decision") or {}
    common = {
        "out_of_scope": list(decision.get("out_of_scope") or []),
        "checks": list(decision.get("checks") or []),
        "records_extra": dict(run.doc.get("records") or {}),
        "answer_refusals": [],
    }
    run.doc["terminal"] = None
    try:
        appended, half = transaction.settle_append(receipt, client, run.workspace, run.document,
                                                   event, run.run_dir)
    except view.RecordsStop as exc:
        block = dict(common["records_extra"])
        block["refused"] = exc.refused_block()
        common["records_extra"] = block
        return stop(run, exc.tag, exc.reason, receipt=receipt.path, **common)
    return _finish(run, client, receipt, appended,
                   receipt.doc["card_append"]["event"]["after"],
                   receipt.doc["card_append"]["event"]["before"], common, resumed_half=half)


def command_identity(args):
    """The six-field source identity, as the records component computes it."""
    ok, why = sources.is_work_tree_root(args.workspace)
    if not ok:
        raise Usage("the workspace %s %s" % (args.workspace, why))
    try:
        body = records().identity(args.workspace)
    except RecordsRefusal as refusal:
        raise Defect(link.refusal_sentence(refusal, "the identity of %s could not be computed"
                                           % args.workspace))
    return emit(envelope(args.skill_root, ok=True, workspace=body.get("workspace"),
                         identity=body.get("identity"), excluded=body.get("excluded")))


def command_skill_identity(args):
    """What this skill is: name, version, the commit it sits in, and its content hash."""
    root = validate.skill_root(args.skill_root)
    plugin = os.path.dirname(os.path.dirname(root))
    manifest = os.path.join(plugin, ".claude-plugin", "plugin.json")
    name, version = "build-v2", "unknown"
    try:
        with open(manifest, "rb") as fh:
            body = json.loads(fh.read().decode("utf-8"))
        name, version = body.get("name", name), body.get("version", version)
    except (OSError, ValueError):
        pass
    commit = sources.git(plugin, ["rev-parse", "HEAD"], check=False)
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for entry in sorted(files):
            if entry.endswith(".pyc") or entry == ".DS_Store":
                continue
            full = os.path.join(base, entry)
            digest.update(os.path.relpath(full, root).encode("utf-8"))
            digest.update(b"\0")
            with open(full, "rb") as fh:
                digest.update(fh.read())
            digest.update(b"\n")
    return emit(envelope(args.skill_root, ok=True, name=name, version=version,
                         commit=(commit or "unversioned").strip() or "unversioned",
                         content_sha256=digest.hexdigest()))


# ---- the parser ---------------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="The phase driver of build-v2: one slice of a build doc, made true inside the "
                    "scope the slice draws, with plain reporting when a check does not pass.",
        epilog=PHASE_HELP + "\n" + EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    SKILL_ROOT_HELP = ("test only: load the references from DIR instead of this script's skill root")
    RECORDS_ROOT_HELP = ("the records component's root; without it the four lookups of the "
                         "component's interface are used (argument, RECORDS_ROOT, beside this "
                         "plugin, the installed shape below it)")
    parser.add_argument("--skill-root", metavar="DIR", default=None, help=SKILL_ROOT_HELP)
    parser.add_argument("--records-root", metavar="DIR", default=None, help=RECORDS_ROOT_HELP)

    # The same two options after the command name as well, because either order is what a person
    # types. SUPPRESS keeps the subparser's copy from overwriting a value given before the
    # command with its own default, which is argparse's behaviour otherwise.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--skill-root", metavar="DIR", default=argparse.SUPPRESS, help=SKILL_ROOT_HELP)
    common.add_argument("--records-root", metavar="DIR", default=argparse.SUPPRESS, help=RECORDS_ROOT_HELP)

    sub = parser.add_subparsers(dest="command")

    one = sub.add_parser("check-input", parents=[common], help="validate the input and create the run")
    one.add_argument("input", metavar="input.json", help="the input document (references/input.schema.json)")

    for name, helptext in (("contract", "read the slice from the build doc and fix the scope"),
                           ("preflight", "the source set, the records, the identity"),
                           ("report", "compare, decide, record the card, write the result")):
        phase = sub.add_parser(name, parents=[common], help=helptext)
        phase.add_argument("--run-dir", metavar="D", required=True, help="the run directory")

    answer_phase = sub.add_parser("record-answer", parents=[common],
                                  help="store what the executor concluded")
    answer_phase.add_argument("--run-dir", metavar="D", required=True, help="the run directory")
    answer_phase.add_argument("--answer", metavar="FILE", required=True,
                              help="the recorded executor answer (references/answer.schema.json)")

    ident = sub.add_parser("identity", parents=[common],
                           help="the six-field source identity of a workspace")
    ident.add_argument("workspace", help="the git work tree root")

    sub.add_parser("skill-identity", parents=[common],
                   help="name, version, commit and content hash of this skill")
    return parser


COMMANDS = {
    "check-input": phase_check_input,
    "contract": phase_contract,
    "preflight": phase_preflight,
    "record-answer": phase_record_answer,
    "report": phase_report,
    "identity": command_identity,
    "skill-identity": command_skill_identity,
}

NEEDS_RECORDS = ("preflight", "report", "identity", "skill-identity")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return exits.USAGE
    try:
        validate.skill_root(args.skill_root)
    except validate.SkillRootMissing as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE

    if args.command in NEEDS_RECORDS:
        try:
            RECORDS.append(link.open_client(records_root=args.records_root))
        except ComponentUnavailable as exc:
            sys.stderr.write("%s\n" % exc)
            return exits.MISSING_DEPENDENCY

    try:
        return COMMANDS[args.command](args)
    except Terminal as terminal:
        return emit(terminal.document, exits.TERMINAL)
    except Usage as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except ComponentUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.MISSING_DEPENDENCY
    except statefile.StateCorrupt as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except Defect as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.GENERAL


if __name__ == "__main__":
    sys.exit(main())
