"""recheck.py after Astra's review, fix agent 2 (the phase driver and the transaction): E8-A19, E8-A20,
E8-A21, E8-A22, E8-A23, E8-A26, E8-A30, E8-A31, E8-A32 (the exit-1 part), E8-A35 (the flags), E8-A40,
E8-A44, E8-A45. Expectations are the amendment block of docs/plans/2026-09-13-recheck-v2-e8-core.md
section 12 and pilot-contract.md sections 9 to 11; the canned reports are CASES.md facts."""
import contextlib
import io
import json
import os
import shutil
import unittest
from unittest import mock

import testlib

testlib.add_scripts_to_path()
from recheck_core import checkpoint as cpmod, receipt as rcmod, result as rmod, validate  # noqa: E402

DOC = "docs/plans/2026-09-18-widget-export.md"
BASIS = "default table: a real defect with a concrete failure path, contained and fixable in place"
STATE_FILES = ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log", "result.json", "chat.md")
ITEM = {"severity": "BLOCKER", "location": {"file": "src/widget/export.py", "line": 17},
        "claim": "CSV export writes a title containing a comma without quoting",
        "failure_scenario": "run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two",
        "record": {"document": DOC, "heading": "### 2026-09-19 — review: Slice A", "date": "2026-09-19"},
        "slice": "A"}
GRANT_C302 = "claude-code:session c302:turn 6"


class Fix4(unittest.TestCase):
    F1_REPORT = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed",
                                         "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed \"Bolt, hex\",3 and columns=2",
                                         "location_after_fix": "src/widget/export.py:20"}])

    def setUp(self):
        self.dir = testlib.make_scratch("e8-fix4-driver-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    # ---- helpers (the shape of test_driver_runs) ----

    def case(self, lane, cid, **prep):
        cdir = testlib.build_case(lane, cid, os.path.join(self.dir, lane))
        testlib.prepare_input(cdir, **prep)
        return cdir

    def rc(self, args, hooks=None, expect=None):
        code, doc, err = testlib.recheck(args, cwd=self.dir, hooks=hooks)
        if expect is not None:
            self.assertEqual(code, expect, "%s\n%s\n%s" % (args, err, doc))
        return code, doc, err

    def start(self, cdir, expect=0):
        return self.rc(["start", os.path.join(cdir, "input.json")], expect=expect)[1]

    def verify(self, cdir, call_id, report, status="ok", extra=(), name=None):
        run_dir = os.path.join(cdir, "run")
        args = ["record-call", "--run-dir", run_dir, "--call-id", call_id, "--status", status, "--kind", "subagent", "--model", "claude-fable-5-1"]
        if status == "ok":
            args += ["--raw", testlib.write_report(run_dir, report, name or "report-%s.md" % call_id)]
        return self.rc(args + list(extra))

    def adjudicate(self, cdir, index=0, action="confirmed", extra=()):
        return self.rc(["adjudicate", "--run-dir", os.path.join(cdir, "run"), "--item", str(index), "--action", action] + list(extra))

    def record(self, cdir, hooks=None, expect=10):
        return self.rc(["record", "--run-dir", os.path.join(cdir, "run")], hooks=hooks, expect=expect)

    def resume(self, cdir, expect=10, hooks=None, mutate=None, name="input.resume.json"):
        """The same document with resume: true (the binding hash excludes invocation, E8-9)."""
        def m(d):
            d["invocation"]["resume"] = True
            if mutate:
                mutate(d)
        path = testlib.prepare_input(cdir, model=False, harness=False, run_date=None, mutate=m, path=os.path.join(cdir, name))
        return self.rc(["resume", path], hooks=hooks, expect=expect)

    def validate(self, cdir, seeded=False):
        run_dir = os.path.join(cdir, "run")
        inp = os.path.join(cdir, "input.json") if seeded else os.path.join(run_dir, "input.json")
        code, out, err = testlib.run_script("validate-result.py", [os.path.join(run_dir, "result.json"), "--input", inp, "--run-dir", run_dir], cwd=self.dir)
        got = json.loads(out)
        self.assertEqual(code, 0, "%s\n%s" % (err, out))
        self.assertEqual(got["semantic"], [])
        allowed = ("skipped: the retained report carries no structured tail (a report written before E8-12)",) if seeded else ()
        self.assertEqual([s for s in got["skipped"] if s["reason"] not in allowed], [], got["skipped"])
        return testlib.load_json(os.path.join(run_dir, "result.json"))

    def doc_text(self, cdir):
        return testlib.read_text(os.path.join(cdir, "workspace", DOC))

    def kinds(self, result):
        return [w["kind"] for w in result["records_written"] if w["kind"] != "run_artifact"]

    def state_bytes(self, run_dir, names=STATE_FILES):
        out = {}
        for n in names:
            p = os.path.join(run_dir, n)
            if os.path.isfile(p):
                with open(p, "rb") as fh:
                    out[n] = fh.read()
        return out

    def cp(self, cdir):
        return testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))

    def append(self, path, text):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)

    # ---- E8-A20: the terminal phase ----

    def test_a20_two_failures_stop_is_terminal_and_resumable(self):
        """After `empty` then `transport-failed` the checkpoint is at phase stopped with a resumable terminal block;
        every phase command returns the recorded outcome (exit 10) and writes nothing; resume continues with a
        fresh call under <run_id>-verify-3, the retry counters standing, and the run completes."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir = os.path.join(cdir, "run")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], None, status="empty")
        code, doc, err = self.verify(cdir, "F1-01-fixed-clean-run-verify-2", None, status="transport-failed")
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "stopped")
        cp = self.cp(cdir)
        self.assertEqual(cp["phase"], "stopped")
        self.assertEqual(cp["terminal"]["status"], "stopped"); self.assertTrue(cp["terminal"]["resumable"])
        self.assertIn("the one re-send F1-01-fixed-clean-run-verify-2 returned transport-failed", cp["terminal"]["stop_reason"])
        self.assertEqual([it["retries"] for it in cp["items"]], [2]); self.assertEqual(len(cp["verifier_calls"]), 2)
        before = self.state_bytes(run_dir)
        expected = {"next": "done", "status": "stopped", "result": os.path.join(run_dir, "result.json"), "chat": os.path.join(run_dir, "chat.md"),
                    "reason": "the run ended as stopped: " + cp["terminal"]["stop_reason"]}
        for args in (["record-call", "--run-dir", run_dir, "--call-id", "F1-01-fixed-clean-run-verify-3", "--status", "empty"],
                     ["adjudicate", "--run-dir", run_dir, "--item", "0", "--action", "confirmed"],
                     ["new-defect", "--run-dir", run_dir, "--location", "src/widget/export.py:20", "--claim", "c", "--scenario", "s",
                      "--caused-by", "0", "--severity", "MAJOR", "--severity-basis", BASIS],
                     ["record", "--run-dir", run_dir]):
            code, doc, err = self.rc(args, expect=10)
            self.assertEqual(doc, expected, args[0])
            self.assertEqual(self.state_bytes(run_dir), before, "%s: nothing written" % args[0])
        self.assertEqual(len(self.cp(cdir)["verifier_calls"]), 2, "no new call in the checkpoint")
        self.assertFalse(os.path.exists(os.path.join(run_dir, "verifier", "raw-3.md")))
        code, doc, err = self.resume(cdir, expect=0)
        self.assertEqual(doc["next"], "verify", err); self.assertEqual(doc["call_id"], "F1-01-fixed-clean-run-verify-3")
        self.assertEqual(doc["continuations"], 1)
        cp = self.cp(cdir)
        self.assertEqual(cp["phase"], "verifying"); self.assertNotIn("terminal", cp); self.assertEqual(cp["continuations"], 1)
        self.assertEqual([it["retries"] for it in cp["items"]], [2], "the per-item retry counters are not reset")
        code, doc, err = self.verify(cdir, "F1-01-fixed-clean-run-verify-3", self.F1_REPORT)
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "adjudicate")
        self.adjudicate(cdir)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["run"]["invocation"]["continuations"], 1)
        self.assertEqual([c["status"] for c in result["run"]["verifier"]["calls"]], ["empty", "transport-failed", "ok"])

    def test_a20_verifier_unavailable_is_terminal_and_resumable(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir = os.path.join(cdir, "run")
        started = self.start(cdir)
        code, doc, err = self.verify(cdir, started["call_id"], None, status="invalid-request", extra=["--note", "the request named no workspace"])
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "verifier_unavailable")
        cp = self.cp(cdir)
        self.assertEqual(cp["phase"], "stopped"); self.assertEqual(cp["terminal"]["status"], "verifier_unavailable"); self.assertTrue(cp["terminal"]["resumable"])
        before = self.state_bytes(run_dir)
        code, doc, err = self.rc(["record-call", "--run-dir", run_dir, "--call-id", "F1-01-fixed-clean-run-verify-2", "--status", "empty"], expect=10)
        self.assertEqual(doc["status"], "verifier_unavailable"); self.assertEqual(doc["next"], "done")
        self.assertEqual(doc["result"], os.path.join(run_dir, "result.json"))
        self.assertTrue(doc["reason"].startswith("the run ended as verifier_unavailable: invalid-request: the request named no workspace"), doc["reason"])
        self.assertEqual(self.state_bytes(run_dir), before)
        self.assertEqual(len(self.cp(cdir)["verifier_calls"]), 1, "no call id issued")
        code, doc, err = self.resume(cdir, expect=0)
        self.assertEqual(doc["next"], "verify", err); self.assertEqual(doc["call_id"], "F1-01-fixed-clean-run-verify-2")
        self.assertEqual(self.cp(cdir)["phase"], "verifying")

    def test_a20_stale_source_stop_is_not_resumable(self):
        """record on a changed identity ends stale_source: phase stopped, resumable false; record again returns the
        recorded outcome; resume is refused at section 11 step 1 with the checkpoint bytes unchanged."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir, ws = os.path.join(cdir, "run"), os.path.join(cdir, "workspace")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir)
        self.append(os.path.join(ws, "README.md"), "\nedited after start\n")
        text = self.doc_text(cdir)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "stale_source", err)
        cp = self.cp(cdir)
        self.assertEqual(cp["phase"], "stopped"); self.assertEqual(cp["terminal"]["status"], "stale_source"); self.assertFalse(cp["terminal"]["resumable"])
        reason = "the identity changed between the start of the run and the recording transaction; no record written"
        self.assertEqual(cp["terminal"]["stop_reason"], reason)
        self.assertEqual(testlib.load_json(doc["result"])["stop_reason"], reason)
        before = self.state_bytes(run_dir)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "stale_source"); self.assertEqual(doc["next"], "done"); self.assertEqual(doc["reason"], "the run ended as stale_source: " + reason)
        self.assertEqual(self.state_bytes(run_dir), before)
        code, doc, err = self.resume(cdir, expect=10)
        self.assertEqual(doc["status"], "stopped"); self.assertIsNone(doc["result"])
        self.assertEqual(doc["document"]["stop_reason"], "resume refused at section 11 step 1: the run ended as stale_source: %s; start a new run" % reason)
        self.assertEqual(self.state_bytes(run_dir), before, "the refusal changes no byte")
        self.assertEqual(self.doc_text(cdir), text)

    # ---- E8-A19: containment in the transaction ----

    def test_a19_target_outside_the_workspace_after_start(self):
        """An explicit-items run whose record.document sits under linked-docs/, excluded through .git/info/exclude so
        the identity holds in both shapes (a trailing-slash ignore pattern never matches a symlink); between start and
        record the directory becomes a symlink to a directory outside the workspace: recording_failed at plan time,
        the stop reason naming the step and target, the outside file byte-identical, nothing landed."""
        cdir = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean", os.path.join(self.dir, "F1"))
        ws, run_dir = os.path.join(cdir, "workspace"), os.path.join(cdir, "run")
        venv = os.path.join(ws, "linked-docs")
        os.makedirs(venv)
        shutil.copyfile(os.path.join(ws, DOC), os.path.join(venv, "plan.md"))
        self.append(os.path.join(ws, ".git", "info", "exclude"), "linked-docs\n")
        self.assertEqual(testlib.git(ws, "status", "--porcelain"), "", "linked-docs is excluded: the identity is unchanged by the copy")
        item = dict(ITEM, record=dict(ITEM["record"], document="linked-docs/plan.md"))
        testlib.prepare_input(cdir, mutate=lambda d: d.__setitem__("target", {"items": [item]}))
        started = self.start(cdir)
        self.assertEqual(started["next"], "verify")
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir)
        outside = os.path.join(self.dir, "outside-venv")
        os.makedirs(outside)
        shutil.copyfile(os.path.join(venv, "plan.md"), os.path.join(outside, "plan.md"))
        shutil.rmtree(venv)
        os.symlink(outside, venv)
        outside_bytes = testlib.read_text(os.path.join(outside, "plan.md"))
        self.assertEqual(testlib.git(ws, "status", "--porcelain"), "", "the symlink is excluded too: the identity still holds")
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "recording_failed", err)
        result = self.validate(cdir)
        self.assertEqual(result["stop_reason"], "step 1 target linked-docs/plan.md resolves outside the workspace; no write")
        self.assertEqual(testlib.read_text(os.path.join(outside, "plan.md")), outside_bytes, "the outside file is byte-identical")
        self.assertEqual(self.kinds(result), [])
        rc = testlib.load_json(os.path.join(run_dir, "receipt.json"))
        self.assertEqual(rc["entries"], []); self.assertEqual(rc["phase"], "recording")
        self.assertEqual([s["target"] for s in rc["plan"]][:1], ["linked-docs/plan.md"])
        self.assertEqual(testlib.git(ws, "status", "--porcelain"), "", "no project write")
        self.assertEqual(self.cp(cdir)["transaction_guard"]["targets"], ["linked-docs/plan.md"])

    def test_a19_apply_refuses_a_target_outside_the_workspace(self):
        """rcmod.apply runs the containment test immediately before the replacement; plan_containment names the step."""
        ws = os.path.join(self.dir, "ws")
        os.makedirs(os.path.join(ws, "docs"))
        outside = os.path.join(self.dir, "elsewhere")
        os.makedirs(outside)
        with open(os.path.join(outside, "plan.md"), "w", encoding="utf-8") as fh:
            fh.write("# x\n")
        os.symlink(outside, os.path.join(ws, "docs", "linked"))
        step = {"step": 2, "kind": "punch_list_block", "target": "docs/linked/plan.md", "before_sha256": rcmod.sha("# x\n"),
                "after_sha256": rcmod.sha("# x\n\nmore\n"), "content": "\nmore\n"}
        with self.assertRaises(rcmod.ReceiptError) as ctx:
            rcmod.apply(ws, step)
        self.assertEqual(str(ctx.exception), "step 2 target docs/linked/plan.md resolves outside the workspace; no write")
        self.assertEqual(testlib.read_text(os.path.join(outside, "plan.md")), "# x\n")
        self.assertEqual(rcmod.plan_containment(ws, [step]), str(ctx.exception))
        self.assertIsNone(rcmod.plan_containment(ws, [dict(step, target="docs/plan.md")]))
        self.assertTrue(rcmod.contained(ws, "docs/plan.md")); self.assertFalse(rcmod.contained(ws, "docs/linked/plan.md"))

    # ---- E8-A21: the receipt proves the state ----

    def test_a21_done_entry_with_a_wrong_observed_hash_is_corrupt(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir = os.path.join(cdir, "run")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir)
        code, doc, err = self.record(cdir, hooks={"RECHECK_TEST_FAIL_BEFORE_STEP": "2"})
        self.assertEqual(doc["status"], "recording_failed", err)
        rc_doc = testlib.load_json(os.path.join(run_dir, "receipt.json"))
        self.assertEqual([(e["step"], e["type"]) for e in rc_doc["entries"]], [(1, "intent"), (1, "done"), (2, "intent")])
        rc_doc["entries"][1]["observed_sha256"] = "0" * 64
        rcmod.Receipt(run_dir, rc_doc, validate.load_schemas()).save()  # re-signed with its log line: only the entry is wrong
        self.assertTrue(rcmod.read_and_verify(run_dir, validate.load_schemas())["ok"] is False)
        before = self.state_bytes(run_dir)
        code, doc, err = self.resume(cdir, expect=10)
        self.assertEqual(doc["status"], "stopped")
        reason = doc["document"]["stop_reason"]
        self.assertIn("resume refused at section 11 step 5", reason); self.assertIn("the receipt is corrupt: entry 1 (done, step 1) observed 000000000000", reason)
        self.assertEqual(self.state_bytes(run_dir), before, "nothing written")
        # the other entry rules, on the plan alone
        plan = rc_doc["plan"]
        ok_entries = [{"step": 1, "type": "intent"}, {"step": 1, "type": "done", "observed_sha256": plan[0]["after_sha256"]}, {"step": 2, "type": "intent"}]
        self.assertIsNone(rcmod.check_entries(plan, ok_entries))
        self.assertIn("out of sequence", rcmod.check_entries(plan, [{"step": 2, "type": "intent"}, {"step": 1, "type": "intent"}]))
        self.assertIn("precedes the step's intent", rcmod.check_entries(plan, [{"step": 1, "type": "done", "observed_sha256": plan[0]["after_sha256"]}]))
        self.assertIn("one done per step", rcmod.check_entries(plan, ok_entries[:2] + [ok_entries[1]]))
        self.assertIn("repeats the step's intent", rcmod.check_entries(plan, [ok_entries[0], ok_entries[0]]))
        self.assertIn("names no plan step", rcmod.check_entries(plan, [{"step": 9, "type": "intent"}]))

    def test_a21_fully_done_target_must_rest_at_its_final_hash(self):
        """W2-02 resumed to completion, then an outside prose edit to the build doc, then another resume with a
        continuation grant: recording_failed (the target's last step is an outside edit), not completed, and the
        checkpoint and receipt are byte-identical (E8-A22)."""
        cdir = self.case("W-recording", "W2-02-landed-without-done", run_date="2026-09-21")
        run_dir = os.path.join(cdir, "run")
        code, doc, err = self.rc(["resume", os.path.join(cdir, "input.json")], expect=10)
        self.assertEqual(doc["status"], "completed", err)
        rc_doc = testlib.load_json(os.path.join(run_dir, "receipt.json"))
        self.assertEqual(rc_doc["phase"], "committed"); self.assertEqual(len([e for e in rc_doc["entries"] if e["type"] == "done"]), 2)
        path = os.path.join(cdir, "workspace", DOC)
        text = testlib.read_text(path)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace("Slice A adds", "Slice A (edited outside the run) adds"))
        before = self.state_bytes(run_dir, ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log"))
        grant = {"by": "user", "channel": "user-turn", "turn_ref": "claude-code:session w202:turn 9", "quoted_words": "one more round", "date": "2026-09-21"}
        second = testlib.prepare_input(cdir, mutate=lambda d: d.setdefault("authorization", {}).__setitem__("extra_continuation", grant),
                                       path=os.path.join(cdir, "input.resume2.json"))
        code, doc, err = self.rc(["resume", second], expect=10)
        self.assertEqual(doc["status"], "recording_failed", err)
        result = testlib.load_json(doc["result"])
        self.assertEqual(result["status"], "recording_failed")
        self.assertIn("step 2 (status_line, %s) landed but the target now rests at" % DOC, result["stop_reason"])
        self.assertEqual(self.state_bytes(run_dir, ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log")), before)
        self.assertEqual(result["run"]["invocation"]["continuations"], 1, "the count did not move")
        self.assertEqual(self.cp(cdir)["continuations"], 1)

    # ---- E8-A22: no state change on a refused or ended resume ----

    def test_a22_outside_edit_changes_no_state(self):
        """The W2-04 shape: checkpoint.json and checkpoint.log (and the receipt) are byte-identical before and after,
        continuations unchanged, status recording_failed; result.json and chat.md are the only writes."""
        cdir = self.case("W-recording", "W2-04-outside-edit", run_date="2026-09-21")
        run_dir = os.path.join(cdir, "run")
        kept = ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log", "input.json", "checklist.md")
        before = self.state_bytes(run_dir, kept)
        listing = sorted(os.listdir(run_dir))
        code, doc, err = self.rc(["resume", os.path.join(cdir, "input.json")], expect=10)
        self.assertEqual(doc["status"], "recording_failed", err)
        self.assertEqual(self.state_bytes(run_dir, kept), before, "the seeded run's input.json included: the active input is written only when the resume continues")
        self.assertEqual(self.cp(cdir)["continuations"], 0)
        result = self.validate(cdir, seeded=True)
        self.assertEqual(result["status"], "recording_failed"); self.assertEqual(result["run"]["invocation"]["continuations"], 0)
        self.assertEqual(sorted(set(os.listdir(run_dir)) - set(listing)), ["chat.md", "result.json"], "result.json and chat.md only")

    # ---- E8-A23: a continuation grant is consumed once ----

    def test_a23_grant_consumed_once(self):
        cdir = self.case("C-continuation", "C3-02-limit-with-grant")
        run_dir = os.path.join(cdir, "run")
        code, doc, err = self.rc(["resume", os.path.join(cdir, "input.json")], expect=0)
        self.assertEqual(doc["next"], "verify", err); self.assertEqual(doc["continuations"], 2)
        cp = self.cp(cdir)
        self.assertEqual(cp["continuation_grants_used"], [GRANT_C302])
        self.assertNotIn("extra_continuation", json.dumps(testlib.load_json(os.path.join(run_dir, "input.json"))), "the active input carries no grant (E8-A30)")
        before = self.state_bytes(run_dir)
        code, doc, err = self.rc(["resume", os.path.join(cdir, "input.json")], expect=10)
        self.assertEqual(doc["status"], "stopped")
        self.assertIn("this would be continuation 3 and extra_continuation: turn_ref '%s' already used for continuation 2" % GRANT_C302, doc["document"]["stop_reason"])
        self.assertEqual(self.state_bytes(run_dir), before, "the checkpoint bytes are unchanged")

        def fresh(d):
            d["authorization"]["extra_continuation"]["turn_ref"] = "claude-code:session c302:turn 8"
            d["invocation"]["turn_attribution"] = {"claude-code:session c302:turn 8": "user"}
        third = testlib.prepare_input(cdir, mutate=fresh, path=os.path.join(cdir, "input.resume3.json"))
        code, doc, err = self.rc(["resume", third], expect=0)
        self.assertEqual(doc["next"], "verify", err); self.assertEqual(doc["continuations"], 3)
        self.assertEqual(self.cp(cdir)["continuation_grants_used"], [GRANT_C302, "claude-code:session c302:turn 8"])

    # ---- E8-A26: retained reports re-proved before the plan ----

    def test_a26_evidence_changed_stops_before_the_plan(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir, ws = os.path.join(cdir, "run"), os.path.join(cdir, "workspace")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir)
        raw = os.path.join(run_dir, "verifier", "raw.md")
        with open(raw, "w", encoding="utf-8") as fh:
            fh.write("plain text, no block\n")
        text = self.doc_text(cdir)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "stopped", err)
        result = testlib.load_json(doc["result"])
        self.assertEqual(result["stop_reason"], "evidence changed: %s" % raw)
        self.assertEqual(self.doc_text(cdir), text, "no project write"); self.assertEqual(testlib.git(ws, "status", "--porcelain"), "")
        self.assertFalse(os.path.exists(os.path.join(run_dir, "receipt.json")), "the transaction never planned")
        cp = self.cp(cdir)
        self.assertEqual(cp["phase"], "stopped"); self.assertEqual(cp["terminal"], {"status": "stopped", "stop_reason": result["stop_reason"], "resumable": False})
        code, doc, err = self.resume(cdir, expect=10)
        self.assertIn("resume refused at section 11 step 1: the run ended as stopped: evidence changed", doc["document"]["stop_reason"])

    # ---- E8-A30: the active invocation (the C1-01 assertions live in test_driver_resume.drive_c) ----

    def test_a30_active_input_helper(self):
        import recheck
        doc = {"protocol_version": 1, "authorization": {"extra_continuation": {"by": "user"}}, "target": {}}
        self.assertEqual(recheck.active_input(doc), {"protocol_version": 1, "target": {}})
        doc = {"authorization": {"waivers": [1], "extra_continuation": {"by": "user"}}}
        self.assertEqual(recheck.active_input(doc), {"authorization": {"waivers": [1]}})
        self.assertEqual(recheck.active_input({"a": 1}), {"a": 1})

    # ---- E8-A31: the artifact inventory ----

    def test_a31_every_file_under_run_dir_listed_once(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir = os.path.join(cdir, "run")
        started = self.start(cdir)
        testlib.write_report(run_dir, "some redirected output\n", "extra-command.log")
        code, doc, err = self.verify(cdir, started["call_id"], self.F1_REPORT, name="transport-capture.md")
        self.assertEqual(code, 0, err)
        self.adjudicate(cdir)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        paths = [w["path"] for w in result["records_written"]]
        run_paths = [w["path"] for w in result["records_written"] if w["kind"] == "run_artifact"]
        capture, extra, fixed = (os.path.join(run_dir, "verifier", n) for n in ("transport-capture.md", "extra-command.log", "raw.md"))
        for p in (capture, extra, fixed):
            self.assertEqual(paths.count(p), 1, p)
            self.assertLess(paths.index(p), paths.index(os.path.join(run_dir, "result.json")), p)
        files = sorted(os.path.join(root, n) for root, _, names in os.walk(run_dir) for n in names)
        self.assertEqual(sorted(run_paths), files, "every file under run_dir exactly once")
        self.assertEqual(run_paths[-2:], [os.path.join(run_dir, "result.json"), os.path.join(run_dir, "chat.md")])
        self.assertEqual(run_paths.index(capture), run_paths.index(fixed) + 1, "the capture is named right after the fixed raw path")
        self.assertGreater(run_paths.index(extra), run_paths.index(os.path.join(run_dir, "receipt.log")), "an unnamed file follows the named artifacts")
        self.assertIn(capture, self.cp(cdir)["artifacts"])

    # ---- E8-A35: repeatable flags ----

    def test_a35_repeated_refused_and_injected_flags(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir = os.path.join(cdir, "run")
        started = self.start(cdir)
        refused = ["declined to write README.md", "the sandbox stopped a curl to the payments host; no side effect"]
        raw = testlib.write_report(run_dir, self.F1_REPORT, "report.md")
        code, doc, err = self.rc(["record-call", "--run-dir", run_dir, "--call-id", started["call_id"], "--status", "ok", "--kind", "subagent",
                                  "--refused", refused[0], "--refused", refused[1], "--injected", "CLAUDE.md", "--injected", "AGENTS.md", "--raw", raw], expect=0)
        self.assertEqual(doc["next"], "adjudicate", err)
        calls = testlib.load_json(os.path.join(run_dir, "verifier", "calls.json"))["calls"]
        self.assertEqual(calls[0]["refused"], refused); self.assertEqual(calls[0]["injected"], ["CLAUDE.md", "AGENTS.md"])
        self.adjudicate(cdir)
        self.record(cdir)
        result = self.validate(cdir)
        self.assertEqual(result["run"]["verifier"]["refused_actions"], refused)
        self.assertEqual(result["run"]["verifier"]["injected_channels"], ["CLAUDE.md", "AGENTS.md"])

    # ---- E8-A32: a checkpoint error at start is missing input ----

    def test_a32_checkpoint_error_at_start_is_missing_input(self):
        import recheck
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        run_dir = os.path.join(cdir, "run")
        message = "checkpoint would not validate: /scope/checklist/0/failure_scenario '' is too short"
        buf = io.StringIO()
        with mock.patch.object(recheck.cpmod.Checkpoint, "new", side_effect=recheck.cpmod.CheckpointError(message)):
            with contextlib.redirect_stdout(buf):
                code = recheck.main(["start", os.path.join(cdir, "input.json")])
        self.assertEqual(code, 10)
        doc = json.loads(buf.getvalue())
        self.assertEqual(doc["next"], "done"); self.assertEqual(doc["status"], "missing_input")
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertEqual(res["missing_input"]["fields"], ["scope.checklist[0].failure_scenario"])
        self.assertIn("the first checkpoint would not validate", res["missing_input"]["ambiguity"][0])
        self.assertTrue(res["missing_input"]["question"])
        self.assertEqual(sorted(os.listdir(run_dir)), ["chat.md", "checklist.md", "input.json", "result.json"], "no checkpoint landed")
        self.assertEqual(recheck.checkpoint_error_field(message), "scope.checklist[0].failure_scenario")
        self.assertEqual(recheck.checkpoint_error_field("checkpoint would not validate:  'run_id' is a required property"), "$")

    # ---- E8-A40: is_complete wherever a call's status is read ----

    def test_a40_ok_reads_as_complete(self):
        calls = [{"call_id": "x-verify", "status": "ok", "items": [0], "raw_path": "/r/verifier/raw.md", "raw_sha256": "0" * 64}]
        block = rmod.verifier_block({"verifier_calls": calls}, {"calls": []}, "/r")
        self.assertEqual(block["calls"][0]["status"], "ok"); self.assertEqual(block["raw_path"], "/r/verifier/raw.md")
        calls[0]["status"] = "complete"
        self.assertEqual(rmod.verifier_block({"verifier_calls": calls}, {"calls": []}, "/r")["calls"][0]["status"], "ok")

    # ---- E8-A44: the boundary check before every status-line step ----

    def test_a44_violation_between_two_status_lines(self):
        """The W2-03 shape: an outside README edit between A's status-step done entry and B's intent: completed not_clear,
        A listed as moved before the violation was found, B frozen, boundary.json before_step = B's step, step 3 cancelled,
        step 2 standing."""
        cdir = self.case("W-recording", "W2-03-between-two-status-lines", run_date="2026-09-21")
        run_dir = os.path.join(cdir, "run")
        hooks = {"RECHECK_TEST_INJECT_BEFORE_STEP": "3", "RECHECK_TEST_INJECT_FILE": "README.md",
                 "RECHECK_TEST_INJECT_TEXT": "# widget\n\nedited between A's status line and B's\n"}
        code, doc, err = self.rc(["resume", os.path.join(cdir, "input.json")], hooks=hooks, expect=10)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir, seeded=True)
        self.assertEqual(result["result"], "not_clear")
        self.assertTrue(any("README.md" in v for v in result["boundary_violations"]), result["boundary_violations"])
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off", "reason": "moved before the violation was found"},
                                           {"slice": "B", "before": "rejected", "after": "rejected", "reason": "a boundary violation froze the card"}])
        self.assertEqual(testlib.load_json(os.path.join(run_dir, "boundary.json")), {"before_step": 3, "violations": result["boundary_violations"]})
        rc_doc = testlib.load_json(os.path.join(run_dir, "receipt.json"))
        self.assertEqual([(s["step"], s["kind"], s.get("cancelled", False)) for s in rc_doc["plan"]],
                         [(1, "punch_list_block", False), (2, "status_line", False), (3, "status_line", True)])
        self.assertEqual([(e["step"], e["type"]) for e in rc_doc["entries"]], [(1, "intent"), (1, "done"), (2, "intent"), (2, "done"), (3, "intent")])
        self.assertEqual(rc_doc["phase"], "committed")
        self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        text = self.doc_text(cdir)
        self.assertIn("## Slice A — CSV export\nStatus: signed off", text); self.assertIn("## Slice B — Quantity and title validation\nStatus: rejected", text)
        chat = testlib.read_text(doc["chat"])
        self.assertIn("A moved before it was found", chat)
        # a re-assembly after the commit point keeps the same cards and reasons (boundary.json read back); the harness
        # edit is reverted first, as in test_w4_01_resume_after_violated_commit, so step 6's identity holds, and the
        # second continuation carries its grant
        testlib.git(os.path.join(cdir, "workspace"), "checkout", "--", "README.md")
        grant = {"by": "user", "channel": "user-turn", "turn_ref": "claude-code:session w203:turn 9", "quoted_words": "one more round", "date": "2026-09-21"}
        second = testlib.prepare_input(cdir, run_date="2026-09-21", mutate=lambda d: d.setdefault("authorization", {}).__setitem__("extra_continuation", grant),
                                       path=os.path.join(cdir, "input.resume2.json"))
        code, doc, err = self.rc(["resume", second], expect=10)
        self.assertEqual(doc["status"], "completed", err)
        again = self.validate(cdir, seeded=True)
        self.assertEqual(again["cards"], result["cards"]); self.assertEqual(again["boundary_violations"], result["boundary_violations"])

    # ---- E8-A45: the transaction guard ----

    def dirty_f1(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        self.append(os.path.join(cdir, "workspace", "README.md"), "\nedited before start (a dirty start)\n")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir)
        code, doc, err = self.record(cdir, hooks={"RECHECK_TEST_FAIL_AFTER_STEP": "1"})
        self.assertEqual(doc["status"], "recording_failed", err)
        return cdir

    def test_a45_guard_catches_a_non_target_change_after_a_dirty_start(self):
        cdir = self.dirty_f1()
        run_dir = os.path.join(cdir, "run")
        cp = self.cp(cdir)
        guard = cp["transaction_guard"]
        self.assertTrue(guard["identity"]["dirty"]); self.assertEqual(guard["targets"], [DOC]); self.assertEqual(guard["identity"], cp["start_identity"])
        self.assertRegex(guard["nontarget_diff_sha256"], r"^[0-9a-f]{64}$")
        self.append(os.path.join(cdir, "workspace", "README.md"), "\nedited again after the interruption\n")
        before = self.state_bytes(run_dir, ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log"))
        code, doc, err = self.resume(cdir, expect=10)
        self.assertEqual(doc["status"], "stale_source", err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "stale_source"); self.assertFalse(res["source_identity"]["matched"])
        self.assertIn("tracked files outside the transaction's targets changed since the transaction began", res["stop_reason"])
        self.assertEqual(res["source_identity"]["expected"], guard["identity"], "the guard is the expected identity")
        self.assertEqual(self.state_bytes(run_dir, ("checkpoint.json", "checkpoint.log", "receipt.json", "receipt.log")), before, "E8-A22: no state change")
        self.assertTrue(os.path.isfile(doc["chat"]))

    def test_a45_guard_lets_the_same_dirty_start_complete(self):
        cdir = self.dirty_f1()
        code, doc, err = self.resume(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["boundary_violations"], [])
        self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"]); self.assertEqual(result["run"]["invocation"]["continuations"], 1)

    def test_a45_guardless_checkpoint_inside_a_transaction_from_a_dirty_start_is_refused(self):
        cdir = self.dirty_f1()
        run_dir = os.path.join(cdir, "run")
        cp, _ = cpmod.load(run_dir, validate.load_schemas())
        cp.doc.pop("transaction_guard")
        cp.save()
        before = self.state_bytes(run_dir)
        code, doc, err = self.resume(cdir, expect=10)
        self.assertEqual(doc["status"], "stopped")
        self.assertEqual(doc["document"]["stop_reason"], "resume refused at section 11 step 6: the checkpoint carries no transaction guard and the run started dirty; start a new run")
        self.assertEqual(self.state_bytes(run_dir), before)

    # ---- the checkpoint schema's new fields ----

    def test_checkpoint_schema_new_fields(self):
        schemas = validate.load_schemas()
        cp = testlib.load_json(os.path.join(testlib.EX, "checkpoint-partial.json"))
        self.assertEqual(validate.validate_checkpoint(cp, schemas), [])
        good = dict(cp, phase="stopped", terminal={"status": "verifier_unavailable", "stop_reason": "x", "resumable": True},
                    continuation_grants_used=["claude-code:session c302:turn 6"],
                    transaction_guard={"identity": cp["start_identity"], "nontarget_diff_sha256": "0" * 64, "targets": [DOC]})
        self.assertEqual(validate.validate_checkpoint(good, schemas), [])
        for bad in (dict(good, terminal={"status": "completed", "stop_reason": "x", "resumable": False}),
                    dict(good, terminal={"status": "stopped", "stop_reason": "x"}),
                    dict(good, terminal=dict(good["terminal"], extra=1)),
                    dict(good, continuation_grants_used=[1]),
                    dict(good, transaction_guard={"identity": cp["start_identity"], "targets": []}),
                    dict(good, transaction_guard=dict(good["transaction_guard"], nontarget_diff_sha256="xyz")),
                    dict(good, transaction_guard=dict(good["transaction_guard"], more=1))):
            self.assertTrue(validate.validate_checkpoint(bad, schemas), bad)


if __name__ == "__main__":
    unittest.main()
