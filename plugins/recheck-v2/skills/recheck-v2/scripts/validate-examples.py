#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Validate the example documents against the schemas and run the negative suite (A7a, E8-A37).

    uv run validate-examples.py [--skill-root DIR] [--verbose]      (from any directory)

Resolves references/ (the four schemas and references/examples/) from the skill root, which is
this script's own location (scripts/.. holds SKILL.md) unless --skill-root names another
directory (test only). Every schema is loaded through recheck_core.validate, so each validator
carries jsonschema's FormatChecker (E8-A34: a non-calendar `format: date` is rejected).

Checks: every positive example validates; every negative case is rejected; every positive
mutation is accepted; the checkpoint example passes its item-state and integrity checks
(log-before-rename and the one tolerated state with its predecessor link, pilot-contract.md
section 11 and lane contract E8-15); the receipt example passes the same integrity checks and is
consistent with result-recording-failed.json.

stdout: one JSON object {"ok": bool, "positive": {"files", "failing"}, "negative": {"total",
"rejected"}, "mutations": {"total", "accepted"}, "checkpoint": {"total", "passed"}, "receipt":
{"total", "passed"}, "failures": [strings]} and nothing else. stderr: diagnostics; with --verbose,
one line per check (PASS/FAIL, REJECTED/ACCEPTED (BUG), ACCEPTED/REJECTED (BUG), CHECKPOINT OK/(BUG),
RECEIPT OK/(BUG)). Exit 0 when ok; 4 when any check fails; 2 on an unknown argument or a
--skill-root that is not a directory; 3 when jsonschema cannot be imported (nothing on stdout);
1 when a schema under the skill root is missing or unreadable.
E8-A51: a positive example, a mutation base, or the checkpoint or receipt example that fails to
load (not JSON), fails its schema, or raises during a mutation (KeyError, TypeError, ...) is a
failure named `<file>: <error>` in `failures`, the JSON still printed with `ok` false, exit 4;
exit 1 is reserved for a missing or unreadable schema.
Side effects: none (read-only). Reruns are safe.
"""
import argparse
import copy
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from recheck_core import validate  # noqa: E402

EXAMPLE = """example:
  uv run %(prog)s
  -> {"ok": true, "positive": {"files": 17, "failing": 0}, "negative": {"total": 150, "rejected": 150}, ...,
      "failures": []}
  uv run %(prog)s --verbose 2>checks.log

exit status: 0 every check passed; 4 a check failed (the failures list names each, an example that does
  not load, fails its schema, or breaks a mutation included); 2 usage (an unknown argument, a --skill-root
  that is not a directory); 3 jsonschema missing (nothing on stdout); 1 a schema under the skill root
  missing or unreadable.
side effects: none (read-only). Reruns are safe."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        sys.exit(2)


def build_parser():
    p = Parser(prog="validate-examples.py",
               description="Validate the recheck-v2 example documents against their schemas and run the negative suite, "
                           "the positive mutations, and the checkpoint and receipt integrity checks.",
               epilog=EXAMPLE, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--skill-root", metavar="DIR", default=None,
                   help="test only: load references (the schemas and references/examples) from DIR instead of the script's own skill root")
    p.add_argument("--verbose", action="store_true", help="print one line per check on stderr (stdout stays the one JSON object)")
    return p


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def set_path(d, path, value):
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


def del_path(d, path):
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    del cur[path[-1]]


def resign(c):
    body = copy.deepcopy(c)
    del body["integrity"]["self"]
    c["integrity"]["self"] = hashlib.sha256(canon(body)).hexdigest()


def check_integrity(doc, log_lines):
    """Section 11 integrity of a checkpoint or a receipt against its log.

    Returns 'ok', 'repair' (the one tolerated state: the log announced a write whose rename
    never landed, and the checkpoint's prev equals the line before its own, E8-15), or the
    first defect found."""
    body = copy.deepcopy(doc)
    self_ = body["integrity"].pop("self")
    if hashlib.sha256(canon(body)).hexdigest() != self_:
        return "self digest does not recompute"
    seq, prev = doc["integrity"]["seq"], doc["integrity"]["prev"]
    rows = [l.split() for l in log_lines if l.strip()]
    if any(len(r) != 2 or not r[0].isdigit() for r in rows):
        return "log line with a shape other than <seq> <self>"
    if [int(r[0]) for r in rows] != list(range(len(rows))):
        return "log has a gap or a repeated seq"
    if rows and rows[-1] == [str(seq), self_]:
        if seq == 0:
            return "ok" if prev is None and len(rows) == 1 else "prev must be null at seq 0"
        return "ok" if len(rows) >= 2 and rows[-2][1] == prev else "prev is not the line before"
    if len(rows) >= 2 and rows[-2] == [str(seq), self_] and int(rows[-1][0]) == seq + 1:
        # the log announced a write whose rename never landed: tolerated only with the predecessor link intact (E8-15)
        if seq == 0:
            return "repair" if prev is None else "prev must be null at seq 0"
        if len(rows) >= 3 and rows[-3][1] == prev:
            return "repair"
        return "announced write ahead of the checkpoint, but prev is not the line before its own (E8-15)"
    return "(seq, self) is not the log's last line"


class Suite:
    def __init__(self, schemas, verbose):
        self.schemas = schemas
        self.verbose = verbose
        self.ex = os.path.join(schemas.root, "references", "examples")
        self.failures = []
        self._names = {}  # id(doc) -> example file name, for the failure lines (E8-A51)

    def say(self, line):
        if self.verbose:
            sys.stderr.write(line + "\n")

    def fail(self, line):
        self.failures.append(line)
        self.say(line)

    def load(self, name):
        with open(os.path.join(self.ex, name), "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))

    def base(self, name):
        """A positive example as a mutation base, or None with the failure recorded once (E8-A51: a base that
        does not load is a failure, not a crash; every case on it counts as not passed)."""
        try:
            doc = self.load(name)
        except (OSError, ValueError) as exc:
            self.fail("%s: does not load: %s: %s" % (name, type(exc).__name__, exc))
            return None
        self._names[id(doc)] = name
        return doc

    def name_of(self, doc):
        return self._names.get(id(doc), "<example>")

    def validator_for(self, base):
        if base.startswith("input-"):
            return self.schemas.input
        if base.startswith("checkpoint-"):
            return self.schemas.checkpoint
        if base.startswith("receipt-"):
            return self.schemas.receipt
        return self.schemas.result

    # ---- the positive examples ----

    def positives(self):
        files = sorted(glob.glob(os.path.join(self.ex, "*.json")))
        failing = 0
        for f in files:
            base = os.path.basename(f)
            try:
                doc = self.load(base)
            except (OSError, ValueError) as exc:  # E8-A51: an example that is not JSON is a failure, not a crash
                failing += 1
                self.fail("FAIL %s: does not load: %s: %s" % (base, type(exc).__name__, exc))
                continue
            errs = list(self.validator_for(base).iter_errors(doc))
            if errs:
                failing += 1
                self.fail("FAIL " + base + ": " + "; ".join(e.message[:110] for e in errs[:3]))
            else:
                self.say("PASS " + base)
        return {"files": len(files), "failing": failing}

    # ---- the negative suite and the positive mutations ----

    def neg(self, name, doc, validator, mutate):
        if doc is None:
            return False  # the base did not load; recorded once by base()
        try:
            d = copy.deepcopy(doc)
            mutate(d)
            ok = not validator.is_valid(d)
        except Exception as exc:  # noqa: BLE001 - E8-A51: a mutation that raises is a failure, not a crash
            self.fail("%s: %s: mutation raised %s: %s" % (self.name_of(doc), name, type(exc).__name__, exc))
            return False
        if ok:
            self.say("REJECTED " + name)
        else:
            self.fail("ACCEPTED (BUG) " + name)
        return ok

    def pos(self, name, doc, validator, mutate):
        if doc is None:
            return False  # the base did not load; recorded once by base()
        try:
            d = copy.deepcopy(doc)
            mutate(d)
            errs = list(validator.iter_errors(d))
        except Exception as exc:  # noqa: BLE001 - E8-A51
            self.fail("%s: %s: mutation raised %s: %s" % (self.name_of(doc), name, type(exc).__name__, exc))
            return False
        if errs:
            self.fail("REJECTED (BUG) " + name + ": " + errs[0].message[:120])
        else:
            self.say("ACCEPTED " + name)
        return not errs

    def mutations(self):
        inp, res, cpv, rcv = self.schemas.input, self.schemas.result, self.schemas.checkpoint, self.schemas.receipt
        load = self.base
        completed = load("result-completed.json")
        blocked = load("result-completed-blocked.json")
        stopped = load("result-stopped.json")
        unavailable = load("result-verifier-unavailable.json")
        failed = load("result-recording-failed.json")
        caller = load("input-caller.json")
        direct = load("input-direct.json")
        cp = load("checkpoint-partial.json")
        rc = load("receipt-partial.json")

        def write_index(d, kind):
            idx = [i for i, w in enumerate(d["records_written"]) if w["kind"] == kind]
            assert len(idx) == 1, (kind, idx)
            return idx[0]

        BLOCK = write_index(completed, "punch_list_block")
        STATUS = write_index(completed, "status_line")
        MARK = {"date": "2026-09-20", "quoted_words": "waive the undefined-title one, ship it", "turn_ref": "codex:thread 01a0a1b2:turn 9"}
        DEFECT = {"severity": "MAJOR", "severity_basis": "default table: a real defect with a concrete failure path, contained and fixable in place",
                  "location": {"file": "src/export.ts", "line": 150}, "claim": "broke: quoted commas now double their quotes",
                  "failure_scenario": "export a title with a comma; the cell carries four quote marks", "source": "fix_introduced", "charged_to_slice": "A"}
        HARNESS = {"name": "claude-code", "version": "2.1.268", "entry": "plugin", "sandbox": "default"}
        MODEL = {"id": "claude-fable-5-1", "floor_class": "opus", "floor_met": True, "effort": "low", "provider_route": "anthropic", "context_tokens": 200000, "settings": {"thinking": True, "temperature": 0}}
        CONTINUATION = {"by": "user", "channel": "user-turn", "turn_ref": "claude-code:session 3b1f:turn 9", "quoted_words": "go one more round", "date": "2026-09-22"}

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
            ("verifier_unavailable carrying a result", unavailable, res, lambda d: d.__setitem__("result", "all_clear")),
            ("verifier_unavailable listing a verdict-doc copy", unavailable, res, lambda d: d["records_written"].append({"kind": "verdict_doc_copy", "path": "docs/reviews/x.md", "appended": True})),
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
            ("recording_failed carrying cards", failed, res, lambda d: d.__setitem__("cards", [])),
            ("recording_failed carrying a result", failed, res, lambda d: d.__setitem__("result", "partial")),
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
            # revision 5 (E8-13, E8-18, E8-24, E8-25, E8-27, E8-5)
            ("input: harness given as a string (E8-18)", direct, inp, lambda d: set_path(d, ["invocation", "harness"], "claude-code 2.1.268")),
            ("input: harness without an entry", direct, inp, lambda d: del_path(d, ["invocation", "harness", "entry"])),
            ("input: model given as a string (E8-18)", direct, inp, lambda d: set_path(d, ["invocation", "model"], "claude-fable-5-1")),
            ("input: model without floor_met (E8-18)", direct, inp, lambda d: del_path(d, ["invocation", "model", "floor_met"])),
            ("input: model with floor_met as a string", direct, inp, lambda d: set_path(d, ["invocation", "model", "floor_met"], "yes")),
            ("input: model with a setting that is an object", caller, inp, lambda d: set_path(d, ["invocation", "model", "settings", "tools"], {"web": False})),
            ("input: turn_attribution with a value outside the enum (E8-24)", caller, inp, lambda d: set_path(d, ["invocation", "turn_attribution"], {"codex:thread 01a0a1b2:turn 7": "tool"})),
            ("input: session_wrote_fix not a boolean (E8-13)", direct, inp, lambda d: set_path(d, ["invocation", "session_wrote_fix"], "no")),
            ("input: run_date not a date (E8-25)", direct, inp, lambda d: set_path(d, ["invocation", "run_date"], "2026/09/20")),
            ("refused_actions holding a non-string (E8-5)", blocked, res, lambda d: set_path(d, ["run", "verifier", "refused_actions"], [42])),
            ("a call entry with a malformed raw_sha256 (E8-27)", blocked, res, lambda d: set_path(d, ["run", "verifier", "calls", 1, "raw_sha256"], "abc")),
            ("a call entry with an empty raw_path", blocked, res, lambda d: set_path(d, ["run", "verifier", "calls", 1, "raw_path"], "")),
            ("run.invocation.run_date not a date (E8-25)", blocked, res, lambda d: set_path(d, ["run", "invocation", "run_date"], "22 Sep 2026")),
            # checkpoint.schema.json (section 11, E8-10)
            ("checkpoint: a pending item carrying a result", cp, cpv, lambda d: d["items"][1].__setitem__("result", d["items"][0]["result"])),
            ("checkpoint: a done item without a result", cp, cpv, lambda d: d["items"][0].pop("result")),
            ("checkpoint: an item with an unknown state", cp, cpv, lambda d: d["items"][1].__setitem__("state", "skipped")),
            ("checkpoint: a done item whose result lacks its adjudication", cp, cpv, lambda d: d["items"][0]["result"].pop("adjudication")),
            ("checkpoint: a stored extra_continuation grant (E8-10)", cp, cpv, lambda d: set_path(d, ["scope", "grants", "extra_continuation"], CONTINUATION)),
            ("checkpoint: a phase outside the enum", cp, cpv, lambda d: d.__setitem__("phase", "grading")),
            ("checkpoint: a start identity with a submodule", cp, cpv, lambda d: set_path(d, ["start_identity", "submodules"], ["vendor/lib"])),
            ("checkpoint: a checklist entry without provenance", cp, cpv, lambda d: del_path(d, ["scope", "checklist", 0, "record"])),
            ("checkpoint: a call without its items", cp, cpv, lambda d: del_path(d, ["verifier_calls", 0, "items"])),
            ("checkpoint: a call with a malformed raw_sha256", cp, cpv, lambda d: set_path(d, ["verifier_calls", 0, "raw_sha256"], "xyz")),
            ("checkpoint: integrity without prev", cp, cpv, lambda d: del_path(d, ["integrity", "prev"])),
            ("checkpoint: negative continuations", cp, cpv, lambda d: d.__setitem__("continuations", -1)),
            ("checkpoint: run_date not a date", cp, cpv, lambda d: d.__setitem__("run_date", "yesterday")),
            # receipt.schema.json (section 9)
            ("receipt: a done entry without its observed hash", rc, rcv, lambda d: del_path(d, ["entries", 1, "observed_sha256"])),
            ("receipt: an intent entry carrying an observed hash", rc, rcv, lambda d: set_path(d, ["entries", 0, "observed_sha256"], "2" * 64)),
            ("receipt: an absolute plan target", rc, rcv, lambda d: set_path(d, ["plan", 0, "target"], "/etc/plan.md")),
            ("receipt: a plan step of kind run_artifact", rc, rcv, lambda d: set_path(d, ["plan", 0, "kind"], "run_artifact")),
            ("receipt: a plan step numbered 0", rc, rcv, lambda d: set_path(d, ["plan", 0, "step"], 0)),
            ("receipt: a phase outside the enum", rc, rcv, lambda d: d.__setitem__("phase", "adjudicating")),
            ("receipt: cancelled as a string", rc, rcv, lambda d: set_path(d, ["plan", 2, "cancelled"], "yes")),
            # the fix round after slice 1's check: E8-2 (finding 1), E8-A2 (finding 4), receipt plan steps (finding 5)
            ("stopped submodule result carrying source_identity (E8-2)", stopped, res, lambda d: set_path(d, ["stop_reason"], "unsupported: submodules: vendor/lib")),
            ("run.model with floor_met as a string (E8-A2)", completed, res, lambda d: set_path(d, ["run", "model", "floor_met"], "yes")),
            ("receipt: a plan target with a .. segment", rc, rcv, lambda d: set_path(d, ["plan", 0, "target"], "../x.md")),
            ("receipt: a plan target with a .. segment in the middle", rc, rcv, lambda d: set_path(d, ["plan", 0, "target"], "docs/../x.md")),
            ("receipt: a cancelled flag on a punch-list step", rc, rcv, lambda d: set_path(d, ["plan", 0, "cancelled"], True)),
            ("receipt: a value on a punch-list step", rc, rcv, lambda d: set_path(d, ["plan", 0, "value"], "signed off")),
            ("receipt: a value on a verdict-doc copy step", rc, rcv, lambda d: set_path(d, ["plan", 1, "value"], "signed off")),
            ("receipt: content on a status-line step", rc, rcv, lambda d: set_path(d, ["plan", 2, "content"], "\nStatus: signed off\n")),
            # the fix round after Astra's review: E8-A34 (finding 16)
            ("stopped result carrying items (E8-A34)", stopped, res, lambda d: d.__setitem__("items", [])),
            ("stopped result carrying still_open (E8-A34)", stopped, res, lambda d: d.__setitem__("still_open", [])),
            ("stopped result carrying new_defects (E8-A34)", stopped, res, lambda d: d.__setitem__("new_defects", [])),
            ("stopped result carrying cards (E8-A34)", stopped, res, lambda d: d.__setitem__("cards", [])),
            ("verifier_unavailable carrying items (E8-A34)", unavailable, res, lambda d: d.__setitem__("items", [])),
            ("verifier_unavailable carrying still_open (E8-A34)", unavailable, res, lambda d: d.__setitem__("still_open", [])),
            ("verifier_unavailable carrying new_defects (E8-A34)", unavailable, res, lambda d: d.__setitem__("new_defects", [])),
            ("stale_source carrying still_open (E8-A34)", load("result-stale-source.json"), res, lambda d: d.__setitem__("still_open", [])),
            ("missing_input carrying still_open (E8-A34)", load("result-missing-input-headless.json"), res, lambda d: d.__setitem__("still_open", [])),
            ("nothing_open carrying still_open (E8-A34)", load("result-nothing-open.json"), res, lambda d: d.__setitem__("still_open", [])),
            ("a completed result with floor_met false (E8-A34)", completed, res, lambda d: set_path(d, ["run", "model", "floor_met"], False)),
            ("a completed result with floor_met null (E8-A34)", completed, res, lambda d: set_path(d, ["run", "model", "floor_met"], None)),
            ("a recording_failed result with floor_met false (E8-A34)", failed, res, lambda d: set_path(d, ["run", "model", "floor_met"], False)),
            ("a new defect without severity_basis (E8-A34)", blocked, res, lambda d: del_path(d, ["new_defects", 0, "severity_basis"])),
            ("a new defect with an empty severity_basis (E8-A34)", blocked, res, lambda d: set_path(d, ["new_defects", 0, "severity_basis"], "")),
            ("checkpoint: a new defect without severity_basis (E8-A34)", cp, cpv, lambda d: d.__setitem__("new_defects", [{k: v for k, v in DEFECT.items() if k != "severity_basis"}])),
            ("checkpoint: seq 0 with a prev string (E8-A34)", cp, cpv, lambda d: (set_path(d, ["integrity", "seq"], 0), set_path(d, ["integrity", "prev"], "0" * 64))),
            ("checkpoint: seq above 0 with prev null (E8-A34)", cp, cpv, lambda d: set_path(d, ["integrity", "prev"], None)),
            ("receipt: seq 0 with a prev string (E8-A34)", rc, rcv, lambda d: (set_path(d, ["integrity", "seq"], 0), set_path(d, ["integrity", "prev"], "0" * 64))),
            ("receipt: seq above 0 with prev null (E8-A34)", rc, rcv, lambda d: set_path(d, ["integrity", "prev"], None)),
            ("receipt: a status_line value of built (E8-A34)", rc, rcv, lambda d: set_path(d, ["plan", 2, "value"], "built")),
            ("receipt: a status_line value of not started (E8-A34)", rc, rcv, lambda d: set_path(d, ["plan", 2, "value"], "not started")),
            ("receipt: a status_line value of none (E8-A34)", rc, rcv, lambda d: set_path(d, ["plan", 2, "value"], "none")),
            ("receipt: an empty status_line value (E8-A34)", rc, rcv, lambda d: set_path(d, ["plan", 2, "value"], "")),
            ("input: a waiver dated 2026-02-30 (E8-A34, FormatChecker)", caller, inp, lambda d: set_path(d, ["authorization", "waivers", 0, "date"], "2026-02-30")),
            ("input: a run_date of 2026-99-99 (E8-A34, FormatChecker)", direct, inp, lambda d: set_path(d, ["invocation", "run_date"], "2026-99-99")),
            ("input: a record date of 2026-13-01 (E8-A34, FormatChecker)", caller, inp, lambda d: set_path(d, ["target", "items", 0, "record", "date"], "2026-13-01")),
            ("run.invocation.run_date 2026-99-99 (E8-A34, FormatChecker)", blocked, res, lambda d: set_path(d, ["run", "invocation", "run_date"], "2026-99-99")),
            ("a waived marker dated 2026-02-30 (E8-A34, FormatChecker)", completed, res, lambda d: set_path(d, ["items", 1, "waived"], dict(MARK, date="2026-02-30"))),
            ("checkpoint: run_date 2026-02-30 (E8-A34, FormatChecker)", cp, cpv, lambda d: d.__setitem__("run_date", "2026-02-30")),
            ("checkpoint: a reopening grant dated 2026-99-99 (E8-A34, FormatChecker)", cp, cpv, lambda d: set_path(d, ["scope", "grants", "reopenings", 0, "date"], "2026-99-99")),
            # the fix round after Astra's verification: E8-A50 (finding 16), the forty-hex pin
            ("input: a seven-hex pin (E8-A50)", caller, inp, lambda d: set_path(d, ["source_identity", "commit"], "9c2f1e4")),
        ]
        rejected = sum(self.neg(*c) for c in cases)

        def boundary_failure(d):
            d["boundary_violations"] = ["src/export.ts changed between the pre-transaction identity and the status-line check; status-line steps cancelled"]
            d["result"] = "not_clear"; set_path(d, ["cards", 0, "after"], d["cards"][0]["before"]); set_path(d, ["cards", 0, "reason"], "boundary violation: no card moves")
            del d["records_written"][STATUS]

        def every_new_invocation_field(d):
            d["invocation"]["harness"] = dict(HARNESS)
            d["invocation"]["model"] = copy.deepcopy(MODEL)
            d["invocation"]["session_wrote_fix"] = True
            d["invocation"]["run_date"] = "2026-09-20"
            d["invocation"]["turn_attribution"] = {"codex:thread 01a0a1b2:turn 7": "user", "codex:thread 01a0a1b2:turn 8": "assistant", "ship-v2:turn 3": "station"}

        positives = [
            ("a not-started card moved by the mapping", completed, res, lambda d: (set_path(d, ["cards", 0, "before"], "not started"), set_path(d, ["cards", 0, "after"], "signed off with conditions"))),
            ("an independent evidence-backed upgrade", completed, res, lambda d: (set_path(d, ["items", 1, "disposition"], "fixed"), del_path(d, ["items", 1, "reason"]), set_path(d, ["items", 1, "adjudication", "driver_action"], "upgraded"), set_path(d, ["items", 1, "adjudication", "upgrade_evidence"], "the verifier lacked fixtures/no-title.json; run with it the cell is empty for null and absent"), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), set_path(d, ["cards", 0, "after"], "signed off"))),
            ("a downgrade with a note", completed, res, lambda d: (set_path(d, ["items", 0, "disposition"], "not_fixed"), set_path(d, ["items", 0, "reason"], "reproduces"), set_path(d, ["items", 0, "adjudication", "verifier_said"], "fixed"), set_path(d, ["items", 0, "adjudication", "driver_action"], "downgraded"), set_path(d, ["items", 0, "adjudication", "note"], "the test the verifier ran does not cover the comma case"), d.__setitem__("result", "not_clear"), set_path(d, ["cards", 0, "after"], "rejected"))),
            ("a waived clearance: the open item waived, all_clear, card signed off", completed, res, lambda d: (waive_item1(d), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), set_path(d, ["cards", 0, "after"], "signed off"), set_path(d, ["cards", 0, "reason"], "BLOCKER cleared; the MAJOR waived per user"))),
            ("every item waived, nothing open, all_clear", completed, res, lambda d: (all_not_fixed_waived(d), d.__setitem__("result", "all_clear"), d.__setitem__("still_open", []), set_path(d, ["cards", 0, "after"], "signed off"))),
            ("a waiver on an item the run found fixed", completed, res, lambda d: set_path(d, ["items", 0, "waived"], dict(MARK, quoted_words="waive the escaping one"))),
            ("a boundary violation beside a verified fix: not_clear, cards frozen", completed, res, boundary_failure),
            ("a verifier_unavailable run listing an extra artifact", unavailable, res, lambda d: d["records_written"].insert(1, {"kind": "run_artifact", "path": "/tmp/recheck-a-20260920-8811/checkpoint.json", "appended": False})),
            # revision 5
            ("an input carrying every new invocation field (E8-13, E8-18, E8-24, E8-25)", caller, inp, every_new_invocation_field),
            ("an input whose model reports floor_met null (unknown capability)", direct, inp, lambda d: set_path(d, ["invocation", "model", "floor_met"], None)),
            ("an input without harness or model (a fixture input)", direct, inp, lambda d: (del_path(d, ["invocation", "harness"]), del_path(d, ["invocation", "model"]))),
            ("a verifier call carrying its retained report path and hash (E8-27)", blocked, res, lambda d: (set_path(d, ["run", "verifier", "calls", 1, "raw_path"], "/tmp/recheck-c-20260922-4e9a/verifier/raw-2.md"), set_path(d, ["run", "verifier", "calls", 1, "raw_sha256"], "0" * 64))),
            ("a run reporting its run_date (E8-25)", completed, res, lambda d: set_path(d, ["run", "invocation", "run_date"], "2026-09-20")),
            ("a checkpoint carrying run_date, artifacts, session_wrote_fix, and a call's raw_path and raw_sha256", cp, cpv, lambda d: (d.__setitem__("run_date", "2026-09-22"), d.__setitem__("artifacts", ["/tmp/recheck-c-20260922-4e9a/input.json", "/tmp/recheck-c-20260922-4e9a/checklist.md"]), set_path(d, ["scope", "session_wrote_fix"], False), set_path(d, ["verifier_calls", 0, "raw_path"], "/tmp/recheck-c-20260922-4e9a/verifier/raw.md"), set_path(d, ["verifier_calls", 0, "raw_sha256"], "0" * 64))),
            ("a checkpoint at seq 0 with prev null and every item pending", cp, cpv, lambda d: (d.__setitem__("items", [{"state": "pending", "retries": 0}] * 3), d.__setitem__("phase", "assembling"), set_path(d, ["integrity", "seq"], 0), set_path(d, ["integrity", "prev"], None))),
            ("a receipt with a cancelled status-line step and phase committed", rc, rcv, lambda d: (set_path(d, ["plan", 2, "cancelled"], True), d.__setitem__("phase", "committed"))),
            ("a seeded receipt whose plan carries no content or value (E8-28)", rc, rcv, lambda d: [(s.pop("content", None), s.pop("value", None), s.pop("heading", None)) for s in d["plan"]]),
            # the fix round after slice 1's check: E8-2 (finding 1), E8-A2 (finding 4), receipt plan steps (finding 5)
            ("a stopped submodule result without source_identity (E8-2)", stopped, res, lambda d: (set_path(d, ["stop_reason"], "unsupported: submodules: vendor/lib"), del_path(d, ["source_identity"]))),
            ("a stopped result with another reason keeps its identity", stopped, res, lambda d: set_path(d, ["stop_reason"], "reference unavailable: references/verifier.md")),
            ("run.model carrying floor_met true (E8-A2)", completed, res, lambda d: set_path(d, ["run", "model", "floor_met"], True)),
            ("a receipt plan target whose segment merely starts with two dots", rc, rcv, lambda d: set_path(d, ["plan", 0, "target"], "docs/..drafts/plan.md")),
            ("a receipt status-line step carrying cancelled false beside its value", rc, rcv, lambda d: set_path(d, ["plan", 2, "cancelled"], False)),
            ("a receipt reopened-line step carrying content", rc, rcv, lambda d: (set_path(d, ["plan", 0, "kind"], "reopened_line"), del_path(d, ["plan", 0, "heading"]))),
            # the fix round after Astra's review: E8-A34 (finding 16); the E8-A2 null case moved to the status that carries it
            ("a verifier_unavailable run.model carrying floor_met null (unknown capability, E8-A2, E8-A34)", unavailable, res, lambda d: set_path(d, ["run", "model", "floor_met"], None)),
            ("a verifier_unavailable run.model carrying floor_met false (below the floor, E8-A34)", unavailable, res, lambda d: set_path(d, ["run", "model", "floor_met"], False)),
            ("a stopped run.model carrying floor_met false (E8-A34)", stopped, res, lambda d: set_path(d, ["run", "model", "floor_met"], False)),
            ("a recording_failed run.model carrying floor_met true (E8-A34)", failed, res, lambda d: set_path(d, ["run", "model", "floor_met"], True)),
            ("a new defect carrying its severity_basis (E8-A34)", completed, res, lambda d: d.__setitem__("new_defects", [dict(DEFECT)])),
            ("a checkpoint new defect carrying its severity_basis (E8-A34)", cp, cpv, lambda d: d.__setitem__("new_defects", [dict(DEFECT)])),
            ("a receipt status_line value of signed off with conditions (E8-A34)", rc, rcv, lambda d: set_path(d, ["plan", 2, "value"], "signed off with conditions")),
            ("a receipt status_line value of rejected (E8-A34)", rc, rcv, lambda d: set_path(d, ["plan", 2, "value"], "rejected")),
            ("input: a leap-day run_date 2028-02-29 (E8-A34, FormatChecker)", direct, inp, lambda d: set_path(d, ["invocation", "run_date"], "2028-02-29")),
            # the fix round after Astra's verification: E8-A50 (finding 16)
            ("input: a forty-hex pin (E8-A50)", direct, inp, lambda d: d.__setitem__("source_identity", {"commit": "9c2f1e4d0b7a6c5d4e3f2a1b0c9d8e7f6a5b4c3d", "dirty": False})),
        ]
        accepted = sum(self.pos(*c) for c in positives)
        self._docs = {"cp": cp, "rc": rc}
        return {"total": len(cases), "rejected": rejected}, {"total": len(positives), "accepted": accepted}

    # ---- the checkpoint example (section 11) ----

    def check_checkpoint(self, cp, log_lines):
        """Return 'ok', 'repair', or the first defect found (item states first, then integrity)."""
        for i, st in enumerate(cp["items"]):
            if st["state"] == "pending" and "result" in st:
                return "item %d: pending with a result" % i
            if st["state"] == "done" and not self.schemas.item.is_valid(st.get("result", {})):
                return "item %d: done without a valid result" % i
            if st["state"] not in ("pending", "done"):
                return "item %d: unknown state" % i
        return check_integrity(cp, log_lines)

    def read_log(self, name):
        """The example log's lines, or None with the failure recorded (E8-A51)."""
        try:
            with open(os.path.join(self.ex, name), "r", encoding="utf-8") as fh:
                return fh.read().splitlines()
        except OSError as exc:
            self.fail("%s: does not load: %s: %s" % (name, type(exc).__name__, exc))
            return None

    def checkpoint_checks(self):
        cp = self._docs["cp"]
        log = self.read_log("checkpoint-partial.log") or []
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
            ("a corrupted earlier line beside an announced next write (E8-15, C4-07)", "corrupt", None, lambda l: (l.__setitem__(2, "2 " + "f" * 64), l.append("4 " + "1" * 64))),
            ("an announced next write whose predecessor line is the wrong hash after a re-sign (E8-15)", "corrupt", lambda c: (c["integrity"].__setitem__("prev", log[0].split()[1]), resign(c)), lambda l: (l.__setitem__(3, "3 " + hashlib.sha256(canon(dict(copy.deepcopy(cp), integrity={"seq": 3, "prev": log[0].split()[1]}))).hexdigest()), l.append("4 " + "1" * 64))),
            ("a log line with three fields", "corrupt", None, lambda l: l.__setitem__(0, l[0] + " extra")),
        ]
        passed = 0
        if cp is None or not log:
            return {"total": len(cp_cases), "passed": 0}  # the example or its log did not load; recorded once
        for name, expect, mutate_cp, mutate_log in cp_cases:
            try:
                c = copy.deepcopy(cp); l = list(log)
                if mutate_cp:
                    mutate_cp(c)
                if mutate_log:
                    mutate_log(l)
                got = self.check_checkpoint(c, l)
            except Exception as exc:  # noqa: BLE001 - E8-A51: a malformed example is a failure, not a crash
                self.fail("checkpoint-partial.json: %s: raised %s: %s" % (name, type(exc).__name__, exc))
                continue
            ok = (got == expect) if expect in ("ok", "repair") else (got not in ("ok", "repair"))
            if ok:
                self.say("CHECKPOINT OK " + name + " -> " + got)
                passed += 1
            else:
                self.fail("CHECKPOINT (BUG) " + name + " -> " + got)
        return {"total": len(cp_cases), "passed": passed}

    # ---- the receipt example (sections 9 and 11) ----

    def rc_consistency(self, rc):
        """The receipt example is the receipt of result-recording-failed.json as it stood when step 3 failed."""
        failed = self.base("result-recording-failed.json")
        if failed is None:
            return ["result-recording-failed.json does not load"]
        problems = []
        if rc["run_id"] != failed["run"]["run_id"]:
            problems.append("run_id differs from the result's")
        project = [w for w in failed["records_written"] if w["kind"] != "run_artifact"]
        for step, write in zip(rc["plan"], project):
            if (step["kind"], step["target"], step["before_sha256"], step["after_sha256"]) != (write["kind"], write["path"], write["sha256_before"], write["sha256_after"]):
                problems.append("plan step %d does not match the result's %s write" % (step["step"], write["kind"]))
        if len(rc["plan"]) != len(project) + 1 or rc["plan"][-1]["kind"] != "status_line":
            problems.append("the plan is not the result's writes plus the failed status line")
        done = [e["step"] for e in rc["entries"] if e["type"] == "done"]
        if done != [s["step"] for s in rc["plan"][:-1]]:
            problems.append("done entries are not exactly the landed steps")
        if [e for e in rc["entries"] if e["type"] == "intent"][-1]["step"] != rc["plan"][-1]["step"]:
            problems.append("the last intent is not the failed step")
        if rc["integrity"]["seq"] != len(rc["entries"]):
            problems.append("final seq is not the entry count")
        return problems

    def receipt_checks(self):
        rc = self._docs["rc"]
        rlog = self.read_log("receipt-partial.log") or []
        rc_cases = [
            ("the example: six writes, digest and chain intact", "ok", None, None),
            ("a truncated log", "corrupt", None, lambda l: l.pop()),
            ("an edited entry with the digest left stale", "corrupt", lambda c: c["entries"].append({"step": 3, "type": "done", "observed_sha256": "3" * 64}), None),
            ("an edited receipt re-signed but the log untouched", "corrupt", lambda c: (c["entries"].append({"step": 3, "type": "done", "observed_sha256": "3" * 64}), resign(c)), None),
            ("a receipt ahead of its log", "corrupt", None, lambda l: l.pop()),
            ("prev pointing at the wrong line", "corrupt", lambda c: (c["integrity"].__setitem__("prev", rlog[0].split()[1]), resign(c)), None),
            ("the log announces a write whose rename never landed: the one tolerated state", "repair", None, lambda l: l.append("6 " + "1" * 64)),
            ("a corrupted earlier line beside an announced next write (E8-15)", "corrupt", None, lambda l: (l.__setitem__(4, "4 " + "f" * 64), l.append("6 " + "1" * 64))),
        ]
        passed = 0
        if rc is None or not rlog:
            return {"total": len(rc_cases) + 1, "passed": 0}  # the example or its log did not load; recorded once
        for name, expect, mutate_rc, mutate_log in rc_cases:
            try:
                c = copy.deepcopy(rc); l = list(rlog)
                if mutate_rc:
                    mutate_rc(c)
                if mutate_log:
                    mutate_log(l)
                got = check_integrity(c, l)
            except Exception as exc:  # noqa: BLE001 - E8-A51
                self.fail("receipt-partial.json: %s: raised %s: %s" % (name, type(exc).__name__, exc))
                continue
            ok = (got == expect) if expect in ("ok", "repair") else (got not in ("ok", "repair"))
            if ok:
                self.say("RECEIPT OK " + name + " -> " + got)
                passed += 1
            else:
                self.fail("RECEIPT (BUG) " + name + " -> " + got)
        try:
            problems = self.rc_consistency(rc)
        except Exception as exc:  # noqa: BLE001 - E8-A51
            problems = ["raised %s: %s" % (type(exc).__name__, exc)]
        if problems:
            self.fail("RECEIPT (BUG) receipt-partial.json is consistent with result-recording-failed.json: " + "; ".join(problems))
        else:
            self.say("RECEIPT OK receipt-partial.json is consistent with result-recording-failed.json")
            passed += 1
        return {"total": len(rc_cases) + 1, "passed": passed}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate.require_jsonschema()  # exit 3 with the contract's message when jsonschema is absent
    try:
        schemas = validate.load_schemas(args.skill_root)
    except validate.SkillRootMissing as exc:
        parser.error(str(exc))
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return 1
    suite = Suite(schemas, args.verbose)
    out = {"ok": False}
    out["positive"] = suite.positives()
    out["negative"], out["mutations"] = suite.mutations()
    out["checkpoint"] = suite.checkpoint_checks()
    out["receipt"] = suite.receipt_checks()
    out["failures"] = list(suite.failures)
    out["ok"] = (out["positive"]["failing"] == 0 and out["negative"]["rejected"] == out["negative"]["total"]
                 and out["mutations"]["accepted"] == out["mutations"]["total"]
                 and out["checkpoint"]["passed"] == out["checkpoint"]["total"]
                 and out["receipt"]["passed"] == out["receipt"]["total"] and not out["failures"])
    sys.stderr.write("positive: %d files, %d failing; negative: %d/%d rejected; positive mutations: %d/%d accepted; checkpoint checks: %d/%d; receipt checks: %d/%d\n"
                     % (out["positive"]["files"], out["positive"]["failing"], out["negative"]["rejected"], out["negative"]["total"],
                        out["mutations"]["accepted"], out["mutations"]["total"], out["checkpoint"]["passed"], out["checkpoint"]["total"],
                        out["receipt"]["passed"], out["receipt"]["total"]))
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0 if out["ok"] else 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - anything else is exit 1 with the cause named
        sys.stderr.write("validate-examples.py failed: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
