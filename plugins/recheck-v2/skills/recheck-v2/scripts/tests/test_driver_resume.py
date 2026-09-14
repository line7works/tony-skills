"""recheck.py resume on the seeded W2 and C fixtures (pilot contract sections 9 and 11; E8-7,
E8-9, E8-14, E8-15; W-recording/CASES.md and C-continuation/CASES.md facts)."""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import ledger  # noqa: E402

DOC = "docs/plans/2026-09-18-widget-export.md"
RL_E1 = '- BLOCKER · src/widget/export.py:9 · (CSV export writes an unescaped comma inside the title column) · fixed · executed PYTHONPATH=src python3 -m widget.export "Widgets, large" 3; the data row reads "Widgets, large",3 and columns=2,2; format_title now at src/widget/export.py:7-11'
RL_E2 = '- MAJOR · src/widget/export.py:14 · (a negative qty is exported unchanged) · fixed · executed PYTHONPATH=src python3 -m widget.export Widget -3; stderr reads error: qty must be zero or more, got -3 and the exit status is 1; format_qty now at src/widget/export.py:14-18'
RL_E3 = '- MAJOR · src/widget/export.py:21 · (a title containing a newline is exported as two rows) · fixed · executed PYTHONPATH=src python3 -m widget.export "$(printf \'Widget\\nlarge\')" 3; the output is one quoted data row and columns=2,2'
RO_E2 = '- REOPENED (per user) · 2026-09-21 · src/widget/export.py:14 · a negative qty is exported unchanged · "reopen the negative qty one, I want it rechecked"'
WV_E4 = '- WAIVED (per user) · 2026-09-21 · MINOR · src/widget/export.py:32 · the usage message omits what the exit status means · "waive the usage message one, the exit status note can wait"'
WV_E1 = '- WAIVED (per user) · 2026-09-21 · BLOCKER · src/widget/export.py:9 · CSV export writes an unescaped comma inside the title column · "waive the comma one either way, I am happy with the quoting"'


class Resumes(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e8-slice2-resume-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    def case(self, lane, cid, **prep):
        cdir = testlib.build_case(lane, cid, os.path.join(self.dir, lane))
        testlib.prepare_input(cdir, **prep)
        return cdir

    def resume(self, cdir, expect=None):
        code, doc, err = testlib.recheck(["resume", os.path.join(cdir, "input.json")], cwd=self.dir)
        if expect is not None:
            self.assertEqual(code, expect, "%s\n%s" % (err, doc))
        return code, doc, err

    def validate(self, cdir):
        run_dir = os.path.join(cdir, "run")
        args = [os.path.join(run_dir, "result.json"), "--input", os.path.join(cdir, "input.json"), "--run-dir", run_dir]
        code, out, err = testlib.run_script("validate-result.py", args, cwd=self.dir)
        got = json.loads(out)
        self.assertEqual(code, 0, "%s\n%s" % (err, out))
        # the seeded W2 reports predate E8-12 and carry no structured tail: V13 skips with that reason and nothing else
        allowed = ("skipped: the retained report carries no structured tail (a report written before E8-12)",)
        self.assertEqual([s for s in got["skipped"] if s["reason"] not in allowed], [], got["skipped"])
        return testlib.load_json(args[0])

    def doc_text(self, cdir):
        return testlib.read_text(os.path.join(cdir, "workspace", DOC))

    # ---- W2: the transaction resumed (W CASES.md, run directory facts; section 9; R34) ----

    def test_w2_01_between_steps(self):
        """W2-01: steps 1 (RO-E2) and 2 (the block) landed with done entries; step 3 (WV-E4) has an intent only;
        step 4 moves A to signed off. The resume appends WV-E4 and the status line, nothing twice."""
        cdir = self.case("W-recording", "W2-01-between-steps", run_date="2026-09-21")
        before = self.doc_text(cdir)
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "completed", err)
        after = self.doc_text(cdir)
        self.assertEqual(after, before.replace("Status: rejected", "Status: signed off") + WV_E4 + "\n", "the tail is WV-E4 after the block; the status line moved")
        self.assertEqual(after.count(RO_E2), 1); self.assertEqual(after.count(RL_E1), 1); self.assertEqual(after.count(RL_E2), 1)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off", "reason": result["cards"][0]["reason"]}])
        self.assertEqual([w["kind"] for w in result["records_written"] if w["kind"] != "run_artifact"], ["reopened_line", "punch_list_block", "waived_line", "status_line"])
        self.assertIn("reopened", result["items"][1]); self.assertNotIn("waived", result["items"][1])
        self.assertEqual(result["checklist"]["count"], 2)
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual([(e["step"], e["type"]) for e in rc["entries"]], [(1, "intent"), (1, "done"), (2, "intent"), (2, "done"), (3, "intent"), (3, "done"), (4, "intent"), (4, "done")])
        self.assertEqual(rc["phase"], "committed"); self.assertEqual(rc["integrity"]["seq"], 8)
        self.assertEqual(result["run"]["invocation"]["continuations"], 1)

    def test_w2_02_landed_without_done(self):
        """W2-02: step 2 (the status line) landed on disk with no done entry: marked done, not redone (R34, E7-26)."""
        cdir = self.case("W-recording", "W2-02-landed-without-done", run_date="2026-09-21")
        before = self.doc_text(cdir)
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "completed", err)
        self.assertEqual(self.doc_text(cdir), before, "nothing appended, nothing changed")
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual([(e["step"], e["type"]) for e in rc["entries"]], [(1, "intent"), (1, "done"), (2, "intent"), (2, "done")])
        result = self.validate(cdir)
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off", "reason": result["cards"][0]["reason"]}])
        self.assertEqual(result["result"], "all_clear")

    def test_w2_03_between_two_status_lines(self):
        """W2-03: the two-slice block and A's status line landed; B's status line is pending: the resume moves B
        to signed off; each moved card stands after the block that justifies it."""
        cdir = self.case("W-recording", "W2-03-between-two-status-lines", run_date="2026-09-21")
        before = self.doc_text(cdir)
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "completed", err)
        after = self.doc_text(cdir)
        self.assertEqual(after, before.replace("Status: rejected", "Status: signed off"))
        self.assertEqual(after.count("### 2026-09-21 — recheck: Slice A, Slice B"), 1)
        result = self.validate(cdir)
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off", "reason": result["cards"][0]["reason"]},
                                           {"slice": "B", "before": "rejected", "after": "signed off", "reason": result["cards"][1]["reason"]}])
        self.assertEqual(result["checklist"]["slice"], "A")
        self.assertEqual([w["kind"] for w in result["records_written"] if w["kind"] != "run_artifact"], ["punch_list_block", "status_line", "status_line"])

    def test_w2_04_outside_edit(self):
        """W2-04: the build doc hashes to none of the plan hashes (a prose line was inserted): recording_failed
        again, nothing written, the user's word needed (section 9)."""
        cdir = self.case("W-recording", "W2-04-outside-edit", run_date="2026-09-21")
        before = self.doc_text(cdir)
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "recording_failed", err)
        self.assertEqual(self.doc_text(cdir), before)
        result = self.validate(cdir)
        self.assertIn("outside edit", result["stop_reason"]); self.assertIn("step 2", result["stop_reason"])
        self.assertEqual([w["kind"] for w in result["records_written"] if w["kind"] != "run_artifact"], ["punch_list_block"])
        self.assertNotIn("cards", result)
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual(rc["phase"], "recording"); self.assertEqual(len(rc["entries"]), 3, "the receipt is untouched")

    def test_w2_05_two_steps_same_target(self):
        """W2-05 (carried item 6, E8-14): step 1 landed without a done entry, steps 2 and 3 pending on the same
        target; classified against the virtual state: 1 done, 2 redone (WV-E1 regenerated from the grant), 3 redone."""
        cdir = self.case("W-recording", "W2-05-two-steps-same-target", run_date="2026-09-21")
        before = self.doc_text(cdir)
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "completed", err)
        after = self.doc_text(cdir)
        self.assertEqual(after, before.replace("Status: rejected", "Status: signed off") + WV_E1 + "\n")
        self.assertEqual(after.count(RL_E1), 1)
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual([(e["step"], e["type"]) for e in rc["entries"]], [(1, "intent"), (1, "done"), (2, "intent"), (2, "done"), (3, "intent"), (3, "done")])
        result = self.validate(cdir)
        self.assertIn("waived", result["items"][0], "a checklist item named by an accepted waiver carries the marker (E8-21)")
        self.assertEqual(result["result"], "all_clear")

    # ---- C: the checkpoint resumed (C CASES.md; section 11; E8-7; R20, R35, R41) ----

    # E8-A15: the resume's fresh call covers the pending items only (1 and 2), under their original numbers
    C_REPORT = testlib.canned_report([
        {"index": 1, "location": "src/widget/export.py:11", "disposition": "not_fixed", "reason": "reproduces", "detail": "--qty -1 printed 7,Bolt,-1 and exited 0"},
        {"index": 2, "location": "src/widget/export.py:21", "disposition": "fixed", "detail": "--header printed id,title,qty and columns=3"}])
    C_REPORT_ALL = testlib.canned_report([
        {"index": 0, "location": "src/widget/export.py:16", "disposition": "fixed", "detail": "--title 'Bolt, hex' printed 7,\"Bolt, hex\",3 and columns=3"},
        {"index": 1, "location": "src/widget/export.py:11", "disposition": "not_fixed", "reason": "reproduces", "detail": "--qty -1 printed 7,Bolt,-1 and exited 0"},
        {"index": 2, "location": "src/widget/export.py:21", "disposition": "fixed", "detail": "--header printed id,title,qty and columns=3"}])

    def drive_c(self, cid):
        """C2-01 / C1-01: item 0 is done; the seeded call lacks raw_sha256, so the resume makes a fresh call
        <run_id>-verify-2 (E8-7) whose brief lists the pending items 1 and 2 only, under their original numbers,
        and says so (E8-A15); a canned report from the CASES facts (negative qty reproduces, header fixed)
        covering exactly those two is adjudicated; item 0 is never re-verified, re-adjudicated, or overwritten."""
        cdir = self.case("C-continuation", cid)
        run_dir = os.path.join(cdir, "run")
        code, doc, err = self.resume(cdir, 0)
        self.assertEqual(doc["next"], "verify", err); self.assertEqual(doc["call_id"], "%s-run-verify-2" % cid); self.assertEqual(doc["pending"], [1, 2])
        brief = testlib.read_text(doc["brief"])
        self.assertIn("### Item 1", brief); self.assertIn("### Item 2", brief); self.assertNotIn("### Item 0", brief)
        self.assertIn("original numbers (1, 2)", brief); self.assertIn("do not verify them", brief)
        self.assertNotIn("%s-run" % cid, brief)
        # a report covering every index is incomplete now: it covers more than the call's items (E8-A15)
        raw_all = testlib.write_report(run_dir, self.C_REPORT_ALL, "report-all.md")
        code, doc, err = testlib.recheck(["record-call", "--run-dir", run_dir, "--call-id", "%s-run-verify-2" % cid, "--status", "ok", "--raw", raw_all], cwd=self.dir)
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "verify"); self.assertIn("exactly the indexes 1, 2", doc["reason"])
        self.assertEqual(doc["call_id"], "%s-run-verify-3" % cid)
        raw = testlib.write_report(run_dir, self.C_REPORT, "report.md")
        code, doc, err = testlib.recheck(["record-call", "--run-dir", run_dir, "--call-id", "%s-run-verify-3" % cid, "--status", "ok", "--raw", raw, "--kind", "subagent", "--model", "m"], cwd=self.dir)
        self.assertEqual(code, 0, err); self.assertEqual([it["index"] for it in doc["items"]], [1, 2])
        self.assertTrue(os.path.isfile(os.path.join(run_dir, "verifier", "raw-3.md")), "the retained report of call 3 (E8-27)")
        code, doc, err = testlib.recheck(["adjudicate", "--run-dir", run_dir, "--item", "0", "--action", "confirmed"], cwd=self.dir)
        self.assertEqual(code, 0); self.assertIn("already done", doc["reason"])
        for i in (1, 2):
            code, doc, err = testlib.recheck(["adjudicate", "--run-dir", run_dir, "--item", str(i), "--action", "confirmed"], cwd=self.dir)
            self.assertEqual(code, 0, err)
        self.assertEqual(doc["next"], "record")
        code, doc, err = testlib.recheck(["record", "--run-dir", run_dir], cwd=self.dir)
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "completed")
        result = self.validate(cdir)
        self.assertEqual([it["disposition"] for it in result["items"]], ["fixed", "not_fixed", "fixed"])
        self.assertEqual(result["items"][0]["verification"]["evidence"][0]["artifact_path"], os.path.join(run_dir, "verifier", "export-comma.log"), "item 0's seeded result is kept")
        self.assertEqual(result["result"], "partial")
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off with conditions", "reason": result["cards"][0]["reason"]}])
        self.assertEqual(result["run"]["invocation"]["continuations"], 1)
        self.assertEqual([c["call_id"] for c in result["run"]["verifier"]["calls"]], ["%s-run-verify" % cid, "%s-run-verify-2" % cid, "%s-run-verify-3" % cid])
        self.assertEqual(result["items"][0]["adjudication"]["verifier_said"], "fixed", "item 0's seeded adjudication is untouched")
        text = self.doc_text(cdir)
        o = ledger.open_set(ledger.parse_document(text, DOC))
        self.assertEqual({e["line"]: e["state"] for e in o["entries"]}, {16: "fixed", 11: "open", 21: "fixed"}, "the ledger round-trips")
        names = [os.path.basename(w["path"]) for w in result["records_written"] if w["kind"] == "run_artifact"]
        self.assertEqual(names[:4], ["resolved-input.json", "checklist.json", "checkpoint.json", "checkpoint.log"], "a seeded checkpoint's artifacts are completed by the scan (E8-29)")

    def test_c2_01_handoff(self):
        self.drive_c("C2-01-handoff-run-dir")

    def test_c1_01_compaction(self):
        self.drive_c("C1-01-compaction")

    def test_c3_continuation_limit(self):
        """C3-01: continuations 1 and no grant: stopped; C3-02: the grant on the presented input: continues;
        C3-03: the grant only in the stored input: stopped (E8-10, ruling E7-17)."""
        cdir = self.case("C-continuation", "C3-01-limit-exceeded")
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "stopped"); self.assertIn("continuation limit exceeded", doc["document"]["stop_reason"])
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["continuations"], 1, "state stays on disk, nothing written")
        cdir = self.case("C-continuation", "C3-02-limit-with-grant")
        code, doc, err = self.resume(cdir, 0)
        self.assertEqual(doc["next"], "verify"); self.assertEqual(doc["continuations"], 2)
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["continuations"], 2); self.assertNotIn("extra_continuation", json.dumps(cp["scope"]))
        cdir = self.case("C-continuation", "C3-03-grant-dropped-at-resume")
        code, doc, err = self.resume(cdir, 10)
        self.assertEqual(doc["status"], "stopped"); self.assertIn("continuation limit exceeded", doc["document"]["stop_reason"])

    def test_c4_corrupt_checkpoints_stop_before_any_write(self):
        """C4-01 .. C4-11: every corrupt, mismatched, or missing checkpoint refuses the resume as stopped naming
        the section 11 step, and writes nothing (R35, R41)."""
        expect = {"C4-01-bad-digest": (2, "does not recompute"), "C4-02-checkpoint-ahead-of-log": (2, "ahead of its log"),
                  "C4-03-broken-chain": (2, "not the log line before"), "C4-04-altered-target": (3, "input_sha256"),
                  "C4-05-altered-item-state": (1, "fails its schema"), "C4-06-resigned-ahead": (2, "ahead of its log"),
                  "C4-07-corrupt-earlier-plus-announced": (2, "corrupted earlier line"), "C4-08-run-id-mismatch": (3, "run id"),
                  "C4-09-log-gap": (2, "gap"), "C4-10-missing-checkpoint": (1, "does not exist"), "C4-11-unparseable-checkpoint": (1, "does not parse")}
        for cid, (step, needle) in expect.items():
            cdir = self.case("C-continuation", cid)
            listing = {n: os.path.getmtime(os.path.join(cdir, "run", n)) for n in os.listdir(os.path.join(cdir, "run"))}
            code, doc, err = self.resume(cdir, 10)
            self.assertEqual(doc["status"], "stopped", (cid, err))
            self.assertIn("step %d" % step, doc["document"]["stop_reason"], (cid, doc["document"]["stop_reason"]))
            self.assertIn(needle, doc["document"]["stop_reason"], cid)
            self.assertEqual({n: os.path.getmtime(os.path.join(cdir, "run", n)) for n in os.listdir(os.path.join(cdir, "run"))}, listing, "%s: nothing written" % cid)

    def test_c5_01_announced_write_dropped(self):
        """C5-01: the log announces seq 4 that never landed; the resume drops that line and continues (E8-15, R41)."""
        cdir = self.case("C-continuation", "C5-01-announced-never-landed")
        code, doc, err = self.resume(cdir, 0)
        self.assertEqual(doc["next"], "verify", err)
        log = testlib.read_text(os.path.join(cdir, "run", "checkpoint.log")).splitlines()
        seqs = [int(l.split()[0]) for l in log]
        self.assertEqual(seqs, list(range(len(seqs))), "no gap after the announced line was dropped")
        self.assertNotIn("d1a52b2ea9cec0cff250aa577fd3f354fe96558693d15c0205003d5824462a56", "\n".join(log), "the announced digest is gone (C CASES.md, C5-01)")
        self.assertGreaterEqual(len(seqs), 5, "the resume's own writes follow seq 3")
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["integrity"]["seq"], seqs[-1]); self.assertEqual(cp["continuations"], 1)


if __name__ == "__main__":
    unittest.main()
