"""recheck.py: full runs with a canned verifier report (F1, F2, S2, S1), the transaction
interrupted by the test hooks and resumed, retries and refusals, the reused id, idempotent phase
commands, a live boundary violation, and the disputed upgrade. Expectations are CASES.md facts
plus the contract sections named on each test; the canned reports are written from those facts."""
import json
import os
import re
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import ledger  # noqa: E402

DOC = "docs/plans/2026-09-18-widget-export.md"
BASIS = "default table: a real defect with a concrete failure path, contained and fixable in place"


class Runs(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e8-slice2-runs-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    # ---- helpers ----

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

    def verify(self, cdir, call_id, report, status="ok", extra=()):
        run_dir = os.path.join(cdir, "run")
        if report and "export-comma.log" in report:
            testlib.write_report(run_dir, 'title,qty\n"Bolt, hex",3\ncolumns=2\n', "export-comma.log")
        args = ["record-call", "--run-dir", run_dir, "--call-id", call_id, "--status", status, "--kind", "subagent", "--model", "claude-fable-5-1", "--injected", "CLAUDE.md"]
        if status == "ok":
            args += ["--raw", testlib.write_report(run_dir, report, "report-%s.md" % call_id)]
        return self.rc(args + list(extra))

    def adjudicate(self, cdir, index, action="confirmed", extra=()):
        return self.rc(["adjudicate", "--run-dir", os.path.join(cdir, "run"), "--item", str(index), "--action", action] + list(extra))

    def record(self, cdir, hooks=None, expect=10):
        return self.rc(["record", "--run-dir", os.path.join(cdir, "run")], hooks=hooks, expect=expect)

    def resume(self, cdir, expect=10):
        """Present the same document with resume: true (the binding hash excludes invocation, E8-9)."""
        path = testlib.prepare_input(cdir, model=False, harness=False, run_date=None, mutate=lambda d: d["invocation"].__setitem__("resume", True),
                                     path=os.path.join(cdir, "input.resume.json"))
        return self.rc(["resume", path], expect=expect)

    def validate(self, cdir, strict=True):
        run_dir = os.path.join(cdir, "run")
        args = [os.path.join(run_dir, "result.json"), "--input", os.path.join(run_dir, "input.json"), "--run-dir", run_dir]
        code, out, err = testlib.run_script("validate-result.py", args, cwd=self.dir)
        got = json.loads(out)
        self.assertEqual(code, 0, "%s\n%s" % (err, out))
        self.assertEqual(got["semantic"], [])
        if strict:
            self.assertEqual(got["skipped"], [], "every check runs: the input names the workspace, the run directory is supplied")
        return testlib.load_json(args[0])

    def doc_text(self, cdir):
        return testlib.read_text(os.path.join(cdir, "workspace", DOC))

    def full_run(self, lane, cid, report, adjudications, defects=(), prep=None, hooks=None):
        """start -> record-call ok -> adjudicate each -> [new-defect] -> record; returns (cdir, start doc, record doc)."""
        cdir = self.case(lane, cid, **(prep or {}))
        started = self.start(cdir)
        self.assertEqual(started["next"], "verify")
        code, called, err = self.verify(cdir, started["call_id"], report)
        self.assertEqual(code, 0, err); self.assertEqual(called["next"], "adjudicate")
        for index, action, extra in adjudications:
            code, doc, err = self.adjudicate(cdir, index, action, extra)
            self.assertEqual(code, 0, err)
        for extra in defects:
            code, doc, err = self.rc(["new-defect", "--run-dir", os.path.join(cdir, "run")] + list(extra))
            self.assertEqual(code, 0, err)
        code, recorded, err = self.record(cdir, hooks=hooks)
        return cdir, started, recorded

    def kinds(self, result):
        return [w["kind"] for w in result["records_written"] if w["kind"] != "run_artifact"]

    # ---- F1-01: a fixed item, the block, the card moves (F1 CASES.md; sections 4, 9) ----

    F1_REPORT = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed",
                                         "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed \"Bolt, hex\",3 and columns=2",
                                         "artifact": "export-comma.log", "location_after_fix": "src/widget/export.py:20"}])

    def test_f1_01_full_run(self):
        cdir, started, recorded = self.full_run("F1-fixed-defect", "F1-01-fixed-clean", self.F1_REPORT, [(0, "confirmed", ())])
        before = testlib.git(os.path.join(cdir, "workspace"), "show", "HEAD:" + DOC)
        self.assertEqual(recorded["status"], "completed")
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off", "reason": result["cards"][0]["reason"]}])
        self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        self.assertEqual(result["checklist"], {"source": "build_doc", "build_doc": DOC, "slice": "A", "review_sheet": "absent", "count": 1})
        self.assertEqual(result["run"]["invocation"]["run_date"], "2026-09-20")
        self.assertEqual(result["still_open"], []); self.assertEqual(result["other_open_slices"], [])
        after = self.doc_text(cdir)
        # earlier bytes identical: the ledger home's original text is a prefix of the new one; only the status line moved above it
        home = before.index("## Punch list")
        self.assertTrue(after[after.index("## Punch list"):].startswith(before[home:]))
        self.assertEqual(before[:home].replace("Status: rejected", "Status: signed off"), after[:after.index("## Punch list")])
        tail = after[after.index("\n### 2026-09-20"):]
        self.assertTrue(tail.startswith("\n### 2026-09-20 — recheck: Slice A\n- BLOCKER · src/widget/export.py:17 · (CSV export writes a title containing a comma without quoting) · fixed · executed "), repr(tail))
        self.assertIn("; now at src/widget/export.py:20\n", tail)
        self.assertTrue(after.endswith("\n") and not after.endswith("\n\n"))
        # the artifacts the result names exist and the write list has the E8-29 order
        names = [os.path.basename(w["path"]) for w in result["records_written"] if w["kind"] == "run_artifact"]
        self.assertEqual(names[:4], ["input.json", "checklist.md", "checkpoint.json", "checkpoint.log"])
        self.assertEqual(names[-2:], ["result.json", "chat.md"])
        self.assertIn("raw.md", names); self.assertIn("export-comma.log", names) if os.path.exists(os.path.join(cdir, "run", "verifier", "export-comma.log")) else None
        chat = testlib.read_text(recorded["chat"])
        self.assertTrue(chat.startswith("RECHECK: A — 1 items (+0 new)\nResult: ALL CLEAR · Status: rejected → signed off\nVerdict doc: none found, build doc only\nReview sheet: absent — defaults\n"), chat)
        self.assertIn("Verifier: subagent, claude-fable-5-1 · injected: CLAUDE.md", chat)
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["phase"], "committed")
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual(rc["phase"], "committed"); self.assertEqual([e["type"] for e in rc["entries"]], ["intent", "done", "intent", "done"])
        self.assertEqual(rc["plan"][1]["value"], "signed off")
        # the ledger round-trips: the recheck line parses back to the item, fixed
        o = ledger.open_set(ledger.parse_document(after, DOC))
        self.assertEqual([(e["line"], e["state"]) for e in o["entries"]], [(17, "fixed")])
        # the verifier's brief lists item 0 and the scratch only
        self.assertIn("### Item 0", testlib.read_text(started["brief"]))

    def test_f1_06_and_07_verdict_doc(self):
        """F1 CASES.md, F1-06: the glob matches exactly one verdict doc (the block copied); F1-07: two (none)."""
        cdir, _, recorded = self.full_run("F1-fixed-defect", "F1-06-verdict-one", self.F1_REPORT, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(self.kinds(result), ["punch_list_block", "verdict_doc_copy", "status_line"])
        copy = testlib.read_text(os.path.join(cdir, "workspace", "docs/reviews/2026-09-19-signoff-widget-export-a.md"))
        self.assertIn("\n\n## Punch list\n\n### 2026-09-20 — recheck: Slice A\n- BLOCKER", copy)
        self.assertIn("Verdict doc: docs/reviews/2026-09-19-signoff-widget-export-a.md — appended", testlib.read_text(recorded["chat"]))
        cdir, _, recorded = self.full_run("F1-fixed-defect", "F1-07-verdict-many", self.F1_REPORT, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        self.assertIn("Verdict doc: none found, build doc only", testlib.read_text(recorded["chat"]))

    def test_f1_09_other_open_slices(self):
        """F1 CASES.md, F1-09: slice B's BLOCKER stays open and untouched; the result names B with its card (E8-4)."""
        cdir, _, recorded = self.full_run("F1-fixed-defect", "F1-09-two-slices", self.F1_REPORT, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual([c["slice"] for c in result["cards"]], ["A"])
        self.assertEqual(result["other_open_slices"], ["B: rejected"])
        self.assertEqual(result["result"], "all_clear")

    def test_f1_02_fix_introduced_defect(self):
        """F1 CASES.md, F1-02: the comma scenario no longer holds; Bolt 0 prints Bolt, (a regression on the fix's own
        line). The verifier's candidate is confirmed as MAJOR under the default table (section 4, R17)."""
        report = testlib.canned_report(
            [{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed", "detail": "the scenario printed \"Bolt, hex\",3 and columns=2", "location_after_fix": "src/widget/export.py:20"}],
            new_defects=[{"caused_by_index": 0, "location": "src/widget/export.py:20", "claim": "a zero quantity exports as an empty cell",
                          "failure_scenario": "run PYTHONPATH=src python3 -m widget.export Bolt 0; the data line reads Bolt, with an empty qty cell",
                          "evidence": [{"kind": "command", "detail": "PYTHONPATH=src python3 -m widget.export Bolt 0 printed Bolt,", "artifact": None}]}])
        cdir, _, recorded = self.full_run("F1-fixed-defect", "F1-02-regression", report, [(0, "confirmed", ())],
                                          defects=[["--index", "0", "--severity", "MAJOR", "--severity-basis", BASIS]])
        result = self.validate(cdir)
        self.assertEqual(result["result"], "partial")
        self.assertEqual(result["new_defects"][0]["charged_to_slice"], "A"); self.assertEqual(result["new_defects"][0]["severity"], "MAJOR")
        self.assertEqual(result["cards"][0]["after"], "signed off with conditions")
        self.assertEqual(result["still_open"], ["MAJOR · src/widget/export.py:20 · broke: a zero quantity exports as an empty cell"])
        self.assertIn("- MAJOR · src/widget/export.py:20 · broke: a zero quantity exports as an empty cell — run PYTHONPATH=src python3 -m widget.export Bolt 0; the data line reads Bolt, with an empty qty cell\n", self.doc_text(cdir))

    # ---- F2-01: an unfixed item (F2 CASES.md; R6) ----

    F2_REPORT = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:9", "disposition": "not_fixed", "reason": "reproduces",
                                         "detail": "PYTHONPATH=src python3 -m widget.export \"Widgets, large\" 3 printed Widgets, large,3 and columns=2,3"}])

    def test_f2_01_not_fixed(self):
        cdir, _, recorded = self.full_run("F2-unfixed-defect", "F2-01-reproduces", self.F2_REPORT, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(result["result"], "not_clear")
        self.assertEqual(result["items"][0]["disposition"], "not_fixed"); self.assertEqual(result["items"][0]["reason"], "reproduces")
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "rejected"}])
        self.assertEqual(self.kinds(result), ["punch_list_block"], "no status step when the card does not move")
        self.assertEqual(len(result["still_open"]), 1)
        self.assertIn("· not fixed · executed", self.doc_text(cdir))
        self.assertIn("Result: NOT CLEAR · Status: unchanged (rejected)", testlib.read_text(recorded["chat"]))

    def test_f2_02_upgrade_under_session_wrote_fix(self):
        """F2 CASES.md, F2-02 with its trial condition session_wrote_fix true: an upgrade is recorded as disputed and
        the item stays open (section 7, E8-13, R16)."""
        cdir = self.case("F2-unfixed-defect", "F2-02-session-wrote-fix", mutate=lambda d: d["invocation"].__setitem__("session_wrote_fix", True))
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F2_REPORT)
        code, doc, err = self.adjudicate(cdir, 0, "upgraded", ["--upgrade-evidence", "I ran it myself"])
        self.assertEqual(code, 0, err); self.assertEqual(doc["driver_action"], "disputed"); self.assertEqual(doc["disposition"], "not_fixed")
        self.record(cdir)
        result = self.validate(cdir)
        self.assertTrue(result["run"]["session_wrote_fix"])
        self.assertEqual(result["items"][0]["adjudication"]["driver_action"], "disputed")
        self.assertIn("cannot upgrade", result["items"][0]["adjudication"]["note"])
        self.assertEqual(result["result"], "not_clear")
        # without the flag, the same upgrade is accepted and the item is fixed
        cdir = self.case("F2-unfixed-defect", "F2-01-reproduces")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F2_REPORT)
        code, doc, err = self.adjudicate(cdir, 0, "upgraded", ["--upgrade-evidence", "the CI log shows columns=2,2"])
        self.assertEqual(doc["driver_action"], "upgraded"); self.assertEqual(doc["disposition"], "fixed")
        self.record(cdir)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        # the pairs section 7 forbids are usage errors
        cdir = self.case("F2-unfixed-defect", "F2-01-reproduces")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F2_REPORT)
        code, doc, err = self.adjudicate(cdir, 0, "downgraded", ["--reason", "reproduces", "--note", "x"])
        self.assertEqual(code, 2); self.assertIn("downgraded needs a verifier fixed", err)
        code, doc, err = self.adjudicate(cdir, 0, "upgraded")
        self.assertEqual(code, 2); self.assertIn("upgrade-evidence", err)

    # ---- S2: waivers and reopening (S2 CASES.md; sections 4 and 8; R29, R42) ----

    S2_NOT_FIXED = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:11", "disposition": "not_fixed", "reason": "reproduces",
                                            "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed Bolt, hex,3 and columns: 3"}])
    S2_FIXED = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:11", "disposition": "fixed",
                                        "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed \"Bolt, hex\",3 and columns: 2"}])

    def test_s2_01_waived_clearance(self):
        """S2-01: the BLOCKER's latest record is its finding, the MAJOR was rechecked fixed; the waiver names the
        BLOCKER. R42: the block line reads not fixed, the waiver line lands after it, the item is marked waived,
        the result is all_clear, the card moves by the mapping (rejected -> signed off)."""
        cdir, _, recorded = self.full_run("S2-waivers-reopening", "S2-01-waived-clearance", self.S2_NOT_FIXED, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(result["checklist"]["count"], 1)
        self.assertEqual(result["items"][0]["disposition"], "not_fixed")
        self.assertEqual(result["items"][0]["waived"], {"date": "2026-09-20", "quoted_words": "waive the comma one, we ship slice A without it", "turn_ref": "claude-code:session 3b1f:turn 14"})
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["still_open"], [])
        self.assertEqual(result["cards"][0]["after"], "signed off")
        self.assertEqual(self.kinds(result), ["punch_list_block", "waived_line", "status_line"])
        text = self.doc_text(cdir)
        block = text.index("### 2026-09-20 — recheck: Slice A")
        self.assertIn("· not fixed ·", text[block:])
        waiver = text.index("- WAIVED (per user) · 2026-09-20 · BLOCKER · src/widget/export.py:11 · a title containing a comma is exported unquoted · \"waive the comma one, we ship slice A without it\"\n")
        self.assertGreater(waiver, block, "the waiver line lands after the block")
        self.assertTrue(text.endswith("without it\"\n"), "directly after the ledger home's last line")
        o = ledger.open_set(ledger.parse_document(text, DOC))
        self.assertEqual({e["line"]: e["state"] for e in o["entries"]}, {11: "waived", 19: "fixed"})

    def test_s2_02_waiver_outside_checklist(self):
        """S2-02: the waiver names report.py:9 in slice B; it is written and marks nothing; B keeps its card and is
        named under other_open_slices (E8-4); A moves on its fixed BLOCKER."""
        cdir, _, recorded = self.full_run("S2-waivers-reopening", "S2-02-waiver-outside-checklist", self.S2_FIXED, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(self.kinds(result), ["punch_list_block", "waived_line", "status_line"])
        self.assertNotIn("waived", result["items"][0])
        self.assertEqual([c["slice"] for c in result["cards"]], ["A"]); self.assertEqual(result["cards"][0]["after"], "signed off")
        self.assertEqual(result["other_open_slices"], ["B: rejected"])
        self.assertEqual(result["result"], "all_clear")
        self.assertIn("- WAIVED (per user) · 2026-09-20 · MAJOR · src/widget/report.py:9 ·", self.doc_text(cdir))

    def test_s2_03_reopened(self):
        """S2-03: the named entry was cleared and the card reads signed off; the reopening grant puts it in scope
        (source named_items, E8-26), its REOPENED line is the first write, the block follows, the card is demoted."""
        cdir, started, recorded = self.full_run("S2-waivers-reopening", "S2-03-reopened", self.S2_NOT_FIXED, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(result["checklist"]["source"], "named_items")
        self.assertEqual(result["items"][0]["reopened"]["quoted_words"], "reopen the comma finding, the export still splits it")
        self.assertEqual(self.kinds(result), ["reopened_line", "punch_list_block", "status_line"])
        self.assertEqual(result["cards"], [{"slice": "A", "before": "signed off", "after": "rejected", "reason": result["cards"][0]["reason"]}])
        self.assertEqual(result["result"], "not_clear")
        text = self.doc_text(cdir)
        self.assertLess(text.index("- REOPENED (per user) · 2026-09-20 · src/widget/export.py:11 ·"), text.index("### 2026-09-20 — recheck"))
        self.assertIn("read format_row; titles are passed through the csv writer\n- REOPENED (per user)", text, "the reopening line directly after the last ledger line")
        # a named cleared entry without the grant is missing input naming the grant (section 3)
        cdir = self.case("S2-waivers-reopening", "S2-03-reopened", mutate=lambda d: d.pop("authorization"))
        doc = self.start(cdir, expect=10)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertEqual(res["missing_input"]["fields"], ["authorization.reopen"])

    def test_s2_04_open_minor(self):
        """S2-04: the MINOR is not named and joins nothing; it never moves the card (R23)."""
        cdir, _, recorded = self.full_run("S2-waivers-reopening", "S2-04-open-minor", self.S2_FIXED, [(0, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(result["checklist"]["count"], 1); self.assertEqual(result["cards"][0]["after"], "signed off")

    def test_s2_05_legacy_waiver(self):
        """S2-05: the legacy waiver closes the BLOCKER (file order); the MAJOR at :17 is the checklist."""
        report = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed", "detail": "PYTHONPATH=src python3 -m widget.export - 3 printed ,3 and columns: 2"}])
        cdir, started, recorded = self.full_run("S2-waivers-reopening", "S2-05-legacy-waiver-no-words", report, [(0, "confirmed", ())])
        self.assertEqual([it["location"]["line"] for it in started["checklist"]], [17])
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["cards"][0]["after"], "signed off")

    # ---- S1: co-located findings (S1 CASES.md; R11, R36) ----

    def test_s1_01_two_claims_one_location(self):
        report = testlib.canned_report([
            {"index": 0, "location": "src/widget/export.py:11", "disposition": "fixed", "detail": "--title 'Bolt, hex' printed 7,\"Bolt, hex\",3 and columns=3"},
            {"index": 1, "location": "src/widget/export.py:11", "disposition": "not_fixed", "reason": "reproduces", "detail": "--id 7 --qty 3 printed 7,None,3"}])
        cdir, started, recorded = self.full_run("S1-colocated", "S1-01-two-claims-one-location", report, [(0, "confirmed", ()), (1, "confirmed", ())])
        result = self.validate(cdir)
        self.assertEqual(result["result"], "partial"); self.assertEqual(result["cards"][0]["after"], "signed off with conditions")
        o = ledger.open_set(ledger.parse_document(self.doc_text(cdir), DOC))
        self.assertEqual({e["claim"][:9]: e["state"] for e in o["entries"]}, {"CSV expor": "fixed", "a missing": "open"}, "each entry keeps its own disposition")

    def test_s1_02_shared_claimless_is_missing_input(self):
        cdir = self.case("S1-colocated", "S1-02-legacy-claimless-shared")
        doc = self.start(cdir, expect=10)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertIn("claim-less finding at a location several entries share", res["missing_input"]["ambiguity"][0])

    def test_s1_03_claimless_unique(self):
        """S1-03: one claim-less entry at a location no other holds: matched on location alone; the recheck line
        writes () as its claim field (E8-22) and parses back to the entry."""
        report = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:11", "disposition": "fixed", "detail": "--title 'Bolt, hex' printed 7,\"Bolt, hex\",3 and columns=3"}])
        cdir, started, recorded = self.full_run("S1-colocated", "S1-03-legacy-claimless-unique", report, [(0, "confirmed", ())])
        self.assertEqual(started["checklist"][0]["claim"], "()")
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        text = self.doc_text(cdir)
        self.assertIn("- BLOCKER · src/widget/export.py:11 · () · fixed · executed", text)
        o = ledger.open_set(ledger.parse_document(text, DOC))
        self.assertEqual([(e["claim"], e["state"]) for e in o["entries"]], [(None, "fixed")])

    # ---- the transaction interrupted after every step and resumed (section 9, R34) ----

    def interrupted(self, lane, cid, report, steps, hooks_for):
        for n in steps:
            cdir = self.case(lane, cid)
            started = self.start(cdir)
            self.verify(cdir, started["call_id"], report)
            self.adjudicate(cdir, 0)
            code, doc, err = self.record(cdir, hooks=hooks_for(n))
            self.assertEqual(doc["status"], "recording_failed", (n, err))
            failed = testlib.load_json(doc["result"])
            self.assertIn("step %d" % n, failed["stop_reason"])
            self.assertEqual(failed["status"], "recording_failed")
            rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
            self.assertEqual(rc["phase"], "recording")
            landed_before = [w["kind"] for w in failed["records_written"] if w["kind"] != "run_artifact"]
            code, doc, err = self.resume(cdir)
            self.assertEqual(doc["status"], "completed", (n, err, doc))
            result = self.validate(cdir)
            text = self.doc_text(cdir)
            self.assertEqual(text.count("### 2026-09-20 — recheck: Slice A"), 1, "no duplicate block (%d)" % n)
            self.assertEqual(text.count("- WAIVED (per user)"), 1 if "waived_line" in self.kinds(result) else 0, n)
            self.assertEqual(text.count("Status:"), 1)
            rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
            self.assertEqual(rc["phase"], "committed")
            self.assertEqual(sorted(set(e["step"] for e in rc["entries"] if e["type"] == "done")), [s["step"] for s in rc["plan"]])
            self.assertEqual(len([e for e in rc["entries"] if e["type"] == "done"]), len(rc["plan"]), "one done entry per step, never two")
            self.assertTrue(set(landed_before) <= set(self.kinds(result)))
            self.assertEqual(result["run"]["invocation"]["continuations"], 1)

    def test_f1_01_interrupted_after_each_step(self):
        self.interrupted("F1-fixed-defect", "F1-01-fixed-clean", self.F1_REPORT, [1, 2], lambda n: {"RECHECK_TEST_FAIL_AFTER_STEP": str(n)})

    def test_f1_01_interrupted_before_each_step(self):
        self.interrupted("F1-fixed-defect", "F1-01-fixed-clean", self.F1_REPORT, [1, 2], lambda n: {"RECHECK_TEST_FAIL_BEFORE_STEP": str(n)})

    def test_s2_01_interrupted_after_each_step(self):
        self.interrupted("S2-waivers-reopening", "S2-01-waived-clearance", self.S2_NOT_FIXED, [1, 2, 3], lambda n: {"RECHECK_TEST_FAIL_AFTER_STEP": str(n)})

    def test_s2_01_interrupted_before_each_step(self):
        self.interrupted("S2-waivers-reopening", "S2-01-waived-clearance", self.S2_NOT_FIXED, [2, 3], lambda n: {"RECHECK_TEST_FAIL_BEFORE_STEP": str(n)})

    def test_hooks_inert_without_recheck_test(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir, 0)
        code, doc, err = testlib.recheck(["record", "--run-dir", os.path.join(cdir, "run")], cwd=self.dir, env={"RECHECK_TEST_FAIL_AFTER_STEP": "1"})
        self.assertEqual(doc["status"], "completed", "the hook counts only with RECHECK_TEST=1")

    # ---- retries, refusal, reused id, idempotency (sections 2 and 7; E8-23, E8-27) ----

    def test_retry_once_then_success(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        code, doc, err = self.verify(cdir, started["call_id"], None, status="empty")
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "verify"); self.assertEqual(doc["call_id"], "F1-01-fixed-clean-run-verify-2")
        code, doc, err = self.verify(cdir, doc["call_id"], self.F1_REPORT)
        self.assertEqual(doc["next"], "adjudicate")
        self.adjudicate(cdir, 0); self.record(cdir)
        result = self.validate(cdir)
        self.assertEqual([c["status"] for c in result["run"]["verifier"]["calls"]], ["empty", "ok"])
        self.assertTrue(result["run"]["verifier"]["raw_path"].endswith("verifier/raw-2.md"))
        self.assertEqual(result["run"]["verifier"]["calls"][1]["raw_path"], result["run"]["verifier"]["raw_path"])

    def test_retry_twice_then_stopped(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], None, status="empty")
        code, doc, err = self.verify(cdir, "F1-01-fixed-clean-run-verify-2", None, status="transport-failed")
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "stopped")
        result = self.validate(cdir)
        self.assertEqual(result["status"], "stopped")
        self.assertIn("F1-01-fixed-clean-run-verify returned empty, the one re-send F1-01-fixed-clean-run-verify-2 returned transport-failed", result["stop_reason"])
        self.assertEqual([c["status"] for c in result["run"]["verifier"]["calls"]], ["empty", "transport-failed"])
        self.assertEqual(self.kinds(result), [], "nothing graded, no record write")
        self.assertEqual(testlib.project_status(os.path.join(cdir, "workspace")), "")

    def test_incomplete_report_is_retryable(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        code, doc, err = self.verify(cdir, started["call_id"], "# Verifier report\n\nno tail here\n")
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "verify"); self.assertIn("no fenced JSON block", doc["reason"])
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["verifier_calls"][0]["status"], "incomplete"); self.assertEqual(cp["items"][0]["retries"], 1)
        bad = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed"}, {"index": 0, "location": "x:1", "disposition": "fixed"}])
        code, doc, err = self.verify(cdir, doc["call_id"], bad)
        self.assertEqual(code, 10); self.assertEqual(doc["status"], "stopped")

    def test_deterministic_refusal(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        code, doc, err = self.verify(cdir, started["call_id"], None, status="invalid-request", extra=["--note", "the request named no workspace"])
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "verifier_unavailable")
        result = self.validate(cdir)
        self.assertEqual(result["stop_reason"], "invalid-request: the request named no workspace; nothing graded, no retry")
        self.assertEqual(len(result["run"]["verifier"]["calls"]), 1)

    def test_reused_run_id_after_start(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        self.start(cdir)
        listing = sorted(os.listdir(os.path.join(cdir, "run")))
        doc = self.start(cdir, expect=10)
        self.assertEqual(doc["status"], "stopped"); self.assertIn("reused run id", doc["document"]["stop_reason"])
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), listing)

    def test_idempotent_phase_commands(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        code, first, err = self.verify(cdir, started["call_id"], self.F1_REPORT)
        cp_bytes = testlib.read_text(os.path.join(cdir, "run", "checkpoint.json"))
        code, again, err = self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.assertEqual(code, 0); self.assertEqual(again["next"], "adjudicate"); self.assertIn("already recorded", again["reason"])
        self.assertEqual(testlib.read_text(os.path.join(cdir, "run", "checkpoint.json")), cp_bytes, "changes nothing")
        code, doc, err = self.rc(["record-call", "--run-dir", os.path.join(cdir, "run"), "--call-id", "F1-01-fixed-clean-run-verify-9", "--status", "empty"])
        self.assertEqual(code, 0); self.assertEqual(doc["phase"], "adjudicating")
        self.adjudicate(cdir, 0)
        cp_bytes = testlib.read_text(os.path.join(cdir, "run", "checkpoint.json"))
        code, doc, err = self.adjudicate(cdir, 0)
        self.assertEqual(code, 0); self.assertEqual(doc["next"], "record"); self.assertIn("already done", doc["reason"])
        self.assertEqual(testlib.read_text(os.path.join(cdir, "run", "checkpoint.json")), cp_bytes)
        code, doc, err = self.rc(["record", "--run-dir", os.path.join(cdir, "run")], expect=10)
        text = self.doc_text(cdir)
        code, doc, err = self.rc(["record", "--run-dir", os.path.join(cdir, "run")], expect=0)
        self.assertEqual(doc["next"], "done"); self.assertEqual(doc["status"], "completed")
        self.assertEqual(self.doc_text(cdir), text, "a committed run's record changes nothing")
        code, doc, err = self.resume(cdir, expect=10)
        self.assertEqual(doc["status"], "completed"); self.assertEqual(self.doc_text(cdir), text, "a resume after the commit point re-assembles only")

    # ---- W4: a boundary violation found before the status line (W CASES.md; section 9; R40) ----

    def test_w4_01_boundary_violation(self):
        cdir = self.case("W-recording", "W4-01-boundary-violation")
        report = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:9", "disposition": "fixed", "detail": "C1 printed \"Widgets, large\",3 and columns=2,2"}])
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], report)
        self.adjudicate(cdir, 0)
        src = testlib.read_text(os.path.join(cdir, "workspace", "src/widget/export.py")).split("\n")
        self.assertEqual(src[33], '        sys.stderr.write("usage: python3 -m widget.export <title> <qty>\\n")')
        src[33] = '        sys.stderr.write("usage: python3 -m widget.export TITLE QTY\\n")'
        hooks = {"RECHECK_TEST_INJECT_BEFORE_STEP": "2", "RECHECK_TEST_INJECT_FILE": "src/widget/export.py", "RECHECK_TEST_INJECT_TEXT": "\n".join(src)}
        code, doc, err = self.record(cdir, hooks=hooks)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "not_clear"); self.assertTrue(result["boundary_violations"])
        self.assertIn("src/widget/export.py", result["boundary_violations"][0])
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "rejected", "reason": "a boundary violation froze the card"}])
        self.assertEqual(self.kinds(result), ["punch_list_block"])
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual(rc["plan"][1]["kind"], "status_line"); self.assertTrue(rc["plan"][1]["cancelled"]); self.assertEqual(rc["phase"], "committed")
        self.assertIn("Status: rejected", self.doc_text(cdir))
        self.assertIn("A boundary violation froze every card", testlib.read_text(doc["chat"]))

    # ---- the slice 2 fix round: E8-A8, E8-A11, E8-A12, E8-A13, E8-A16, E8-4, and the checker's findings ----

    def commit_workspace(self, cdir, message):
        ws = os.path.join(cdir, "workspace")
        testlib.git(ws, "add", "-A")
        testlib.git(ws, "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message)
        self.assertEqual(testlib.project_status(ws), "", "the edit is committed")

    def rewrite_doc(self, cdir, fn):
        path = os.path.join(cdir, "workspace", DOC)
        text = testlib.read_text(path)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(fn(text))

    def test_not_started_card_moves(self):
        """E8-A8: F1-01 with `Status: not started` committed: the card moves by the mapping to signed off; a status
        step is planned and landed."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        self.rewrite_doc(cdir, lambda t: t.replace("Status: rejected", "Status: not started"))
        self.commit_workspace(cdir, "slice A not started")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir, 0)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        self.assertEqual(result["cards"], [{"slice": "A", "before": "not started", "after": "signed off", "reason": result["cards"][0]["reason"]}])
        self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual([(s["kind"], s.get("value")) for s in rc["plan"]], [("punch_list_block", None), ("status_line", "signed off")])
        self.assertEqual([(e["step"], e["type"]) for e in rc["entries"]], [(1, "intent"), (1, "done"), (2, "intent"), (2, "done")])
        self.assertIn("Status: signed off", self.doc_text(cdir)); self.assertNotIn("Status: not started", self.doc_text(cdir))

    S3_REPORT = testlib.canned_report([
        {"index": 0, "location": "src/widget/export.py:11", "disposition": "fixed", "detail": "--title 'Widget, large' --qty 3 printed \"Widget, large\",3 (two columns)"},
        {"index": 1, "location": "src/widget/export.py:7", "disposition": "fixed", "detail": "--qty 3 printed ,3 (an empty title cell)"}])

    def test_s3_01_boundary_check_runs_without_a_status_step(self):
        """E8-A11: S3-01's card is built, so the plan holds no status-line step; the boundary check still runs,
        before the done entry of the last step. An edit to README.md injected before step 1: completed, not_clear,
        the violation named, the card built stays built, boundary.json a listed run artifact after receipt.log."""
        cdir = self.case("S34-cards-identity", "S3-01-built-card")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.S3_REPORT)
        self.adjudicate(cdir, 0); self.adjudicate(cdir, 1)
        hooks = {"RECHECK_TEST_INJECT_BEFORE_STEP": "1", "RECHECK_TEST_INJECT_FILE": "README.md", "RECHECK_TEST_INJECT_TEXT": "# widget\n\nedited during the transaction\n"}
        code, doc, err = self.record(cdir, hooks=hooks)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "not_clear")
        self.assertTrue(any("README.md" in v for v in result["boundary_violations"]), result["boundary_violations"])
        self.assertEqual(result["cards"], [{"slice": "A", "before": "built", "after": "built", "reason": "a boundary violation froze the card"}])
        self.assertEqual(self.kinds(result), ["punch_list_block"])
        run_dir = os.path.join(cdir, "run")
        # E8-A44: boundary.json carries the step the check preceded; with no status step, the last step's done entry
        self.assertEqual(testlib.load_json(os.path.join(run_dir, "boundary.json")), {"before_step": 1, "violations": result["boundary_violations"]})
        paths = [w["path"] for w in result["records_written"]]
        self.assertIn(os.path.join(run_dir, "boundary.json"), paths)
        self.assertEqual(paths.index(os.path.join(run_dir, "boundary.json")), paths.index(os.path.join(run_dir, "receipt.log")) + 1, "after receipt.log, before the transaction steps (E8-29)")
        self.assertLess(paths.index(os.path.join(run_dir, "boundary.json")), paths.index(DOC))
        self.assertIn(os.path.join(run_dir, "boundary.json"), testlib.load_json(os.path.join(run_dir, "checkpoint.json"))["artifacts"])
        rc = testlib.load_json(os.path.join(run_dir, "receipt.json"))
        self.assertEqual(rc["phase"], "committed"); self.assertEqual([e["type"] for e in rc["entries"]], ["intent", "done"])
        self.assertIn("Status: built", self.doc_text(cdir))
        self.assertIn("A boundary violation froze every card", testlib.read_text(doc["chat"]))
        # a clean transaction writes no boundary.json
        cdir = self.case("S34-cards-identity", "S3-01-built-card")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.S3_REPORT)
        self.adjudicate(cdir, 0); self.adjudicate(cdir, 1)
        code, doc, err = self.record(cdir)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["boundary_violations"], [])
        self.assertFalse(os.path.exists(os.path.join(cdir, "run", "boundary.json")))

    def test_w4_01_resume_after_violated_commit(self):
        """E8-A11: W4-01 driven to completed not_clear, the harness edit reverted, then resumed: the re-assembly
        reads boundary.json back, so result.json is still completed and not_clear with the same violation text,
        the cards frozen, V6 passing."""
        cdir = self.case("W-recording", "W4-01-boundary-violation")
        report = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:9", "disposition": "fixed", "detail": "C1 printed \"Widgets, large\",3 and columns=2,2"}])
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], report)
        self.adjudicate(cdir, 0)
        src = testlib.read_text(os.path.join(cdir, "workspace", "src/widget/export.py")).split("\n")
        src[33] = '        sys.stderr.write("usage: python3 -m widget.export TITLE QTY\\n")'
        hooks = {"RECHECK_TEST_INJECT_BEFORE_STEP": "2", "RECHECK_TEST_INJECT_FILE": "src/widget/export.py", "RECHECK_TEST_INJECT_TEXT": "\n".join(src)}
        code, doc, err = self.record(cdir, hooks=hooks)
        self.assertEqual(doc["status"], "completed", err)
        first = self.validate(cdir)
        self.assertEqual(first["result"], "not_clear"); self.assertTrue(first["boundary_violations"])
        ws = os.path.join(cdir, "workspace")
        testlib.git(ws, "checkout", "--", "src/widget/export.py")
        self.assertEqual(testlib.project_status(ws).strip(), "M " + DOC, "only the build doc differs now")
        code, doc, err = self.resume(cdir)
        self.assertEqual(doc["status"], "completed", err)
        again = self.validate(cdir)
        self.assertEqual(again["status"], "completed"); self.assertEqual(again["result"], "not_clear")
        self.assertEqual(again["boundary_violations"], first["boundary_violations"], "the same violation text, read back from boundary.json")
        self.assertEqual(again["cards"], first["cards"]); self.assertEqual(again["cards"][0]["after"], "rejected")
        self.assertEqual(self.kinds(again), ["punch_list_block"])
        self.assertEqual(again["run"]["invocation"]["continuations"], 1)
        self.assertIn(os.path.join(cdir, "run", "boundary.json"), [w["path"] for w in again["records_written"]])
        self.assertIn("Status: rejected", self.doc_text(cdir))

    def test_reassembly_never_overwrites_a_valid_result(self):
        """E8-A11: on the re-assembly path an assembly that fails validation is kept beside the valid result.json,
        which stands with its chat.md; without keep_existing the stopped document replaces it (section 5)."""
        from recheck_core import result as rmod, validate
        schemas = validate.load_schemas()
        run_dir = os.path.join(self.dir, "keep")
        os.makedirs(run_dir)
        good = testlib.load_json(os.path.join(testlib.EX, "result-nothing-open.json"))
        with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as fh:
            json.dump(good, fh)
        with open(os.path.join(run_dir, "chat.md"), "w", encoding="utf-8") as fh:
            fh.write("kept\n")
        bad = dict(good); bad["status"] = "completed"
        final, path, chat = rmod.deliver(dict(bad), run_dir, schemas, keep_existing=True)
        self.assertEqual(final, good); self.assertEqual(testlib.load_json(path), good)
        self.assertEqual(testlib.read_text(chat), "kept\n")
        self.assertTrue(os.path.isfile(os.path.join(run_dir, "result.invalid.json")))
        final, path, chat = rmod.deliver(dict(bad), run_dir, schemas)
        self.assertEqual(final["status"], "stopped"); self.assertEqual(testlib.load_json(path)["status"], "stopped")

    def test_receipt_announced_write_dropped_at_resume(self):
        """The receipt's one tolerated state (E8-15), mirroring C5-01: after an interruption an extra line announces
        a receipt write that never landed; the resume drops it before its first write and completes with contiguous
        receipt seqs, V8 passing."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir, 0)
        code, doc, err = self.record(cdir, hooks={"RECHECK_TEST_FAIL_AFTER_STEP": "1"})
        self.assertEqual(doc["status"], "recording_failed", err)
        log = os.path.join(cdir, "run", "receipt.log")
        rows = testlib.read_text(log).splitlines()
        seq = int(rows[-1].split()[0])
        with open(log, "a", encoding="utf-8") as fh:
            fh.write("%d %s\n" % (seq + 1, "b" * 64))
        code, doc, err = self.resume(cdir)
        self.assertEqual(doc["status"], "completed", err)
        rows = testlib.read_text(log).splitlines()
        seqs = [int(r.split()[0]) for r in rows]
        self.assertEqual(seqs, list(range(len(seqs))), "contiguous receipt seqs: the announced line was dropped")
        self.assertNotIn("b" * 64, "\n".join(rows))
        rc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
        self.assertEqual(rc["integrity"]["seq"], seqs[-1]); self.assertEqual(rc["phase"], "committed")
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])

    def test_recording_phase_without_receipt_plans_afresh(self):
        """A checkpoint at phase recording with no receipt.json and no pending item: `record` and `resume` fall
        through to the planning path (the plan, the receipt, the transaction) instead of answering next: resume."""
        from recheck_core import checkpoint as cpmod, validate
        for command in ("record", "resume"):
            cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
            started = self.start(cdir)
            self.verify(cdir, started["call_id"], self.F1_REPORT)
            self.adjudicate(cdir, 0)
            cp, _ = cpmod.load(os.path.join(cdir, "run"), validate.load_schemas())
            cp.doc["phase"] = "recording"
            cp.save()
            self.assertFalse(os.path.exists(os.path.join(cdir, "run", "receipt.json")))
            code, doc, err = self.record(cdir) if command == "record" else self.resume(cdir)
            self.assertEqual(doc["status"], "completed", (command, err, doc))
            result = self.validate(cdir)
            self.assertEqual(result["result"], "all_clear", command)
            self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"], command)
            self.assertEqual(testlib.load_json(os.path.join(cdir, "run", "receipt.json"))["phase"], "committed")

    def test_s2_01_rejected_reopening_beside_the_accepted_waiver(self):
        """E8-A12: a rejected grant object is listed as `<its JSON path>: <file:line> · <why>`, and V7 / V14 match
        grant objects by path, never by location alone: the waiver for the item is accepted and written, the
        reopening for the same item (an assistant turn, dated 2026-09-19) rejected and listed, the run all_clear."""
        def mutate(d):
            w = d["authorization"]["waivers"][0]
            d["authorization"]["reopen"] = [{"item": w["item"], "by": "user", "channel": "user-turn", "turn_ref": "claude-code:session 3b1f:turn 15",
                                             "quoted_words": "reopen the comma one", "date": "2026-09-19"}]
            d["invocation"]["turn_attribution"] = {"claude-code:session 3b1f:turn 14": "user", "claude-code:session 3b1f:turn 15": "assistant"}
        cdir, started, recorded = self.full_run("S2-waivers-reopening", "S2-01-waived-clearance", self.S2_NOT_FIXED, [(0, "confirmed", ())], prep={"mutate": mutate})
        self.assertEqual(len(started["rejected_grants"]), 1)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        self.assertEqual(self.kinds(result), ["punch_list_block", "waived_line", "status_line"])
        self.assertIn("waived", result["items"][0]); self.assertNotIn("reopened", result["items"][0])
        self.assertEqual(len(result["rejected_grants"]), 1)
        entry = result["rejected_grants"][0]
        self.assertTrue(entry.startswith("authorization.reopen[0]: src/widget/export.py:11 · turn_ref "), entry)
        self.assertIn("maps to assistant", entry)
        self.assertNotIn("REOPENED", self.doc_text(cdir))
        self.assertIn("Rejected grants: authorization.reopen[0]: src/widget/export.py:11 · ", testlib.read_text(recorded["chat"]))

    def test_ledger_home_is_the_last_place_in_file_order(self):
        """E8-A13: a 2026-09-20 recheck block committed under `## Notes` before `## Punch list` (records in two
        places): the run appends at the Punch list's tail (the place whose tail comes last in the file), the open
        filter sees the new line, all_clear, the card moves."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        # E13 slice 1: the planted block carries the review finding its recheck line clears. The
        # records component refuses a clearing line that names no finding of the document (exit 5,
        # an ambiguity for the user), where the core's own reader made a standalone entry of it;
        # that divergence is report finding 3 and is not what this test is about, which is where
        # the home sits when records live in two places.
        notes = ("## Notes\n\n### 2026-09-19 — review: Slice A\n"
                 "- MAJOR · src/widget/export.py:30 · an earlier note · run it once and read the tail · Slice A\n"
                 "\n### 2026-09-20 — recheck: Slice A\n"
                 "- MAJOR · src/widget/export.py:30 · (an earlier note) · fixed · executed ran it once\n\n")
        self.rewrite_doc(cdir, lambda t: t.replace("## Punch list", notes + "## Punch list"))
        self.commit_workspace(cdir, "notes block before the punch list")
        started = self.start(cdir)
        self.assertEqual([it["location"]["line"] for it in started["checklist"]], [17])
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir, 0)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear")
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "signed off", "reason": result["cards"][0]["reason"]}])
        after = self.doc_text(cdir)
        self.assertGreater(after.rindex("### 2026-09-20 — recheck: Slice A"), after.index("## Punch list"), "appended at the Punch list tail")
        self.assertTrue(after.endswith("; now at src/widget/export.py:20\n"), repr(after[-120:]))
        o = ledger.open_set(ledger.parse_document(after, DOC))
        self.assertEqual({(e["line"], e["state"]) for e in o["entries"]}, {(30, "fixed"), (17, "fixed")}, "the open filter sees the new line")

    def test_s2_02_waived_slice_named_with_nothing_else_open(self):
        """E8-4: with slice B's other MAJOR (report.py:13) removed from the record, the out-of-checklist waiver for
        report.py:9 leaves B nothing open; B is still named under other_open_slices with its unchanged card."""
        cdir = self.case("S2-waivers-reopening", "S2-02-waiver-outside-checklist")
        self.rewrite_doc(cdir, lambda t: "\n".join(l for l in t.split("\n") if "src/widget/report.py:13" not in l))
        self.commit_workspace(cdir, "drop the report.py:13 finding")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.S2_FIXED)
        self.adjudicate(cdir, 0)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["other_open_slices"], ["B: rejected"])
        self.assertEqual(self.kinds(result), ["punch_list_block", "waived_line", "status_line"])
        self.assertEqual([c["slice"] for c in result["cards"]], ["A"]); self.assertEqual(result["result"], "all_clear")

    def test_record_call_ok_without_raw_writes_nothing(self):
        """record-call --status ok validates --raw before writing verifier/calls.json or anything else."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        run_dir = os.path.join(cdir, "run")
        cp_bytes = testlib.read_text(os.path.join(run_dir, "checkpoint.json"))
        listing = sorted(os.listdir(run_dir))
        self.assertNotIn("verifier", listing)
        for extra in ([], ["--raw", os.path.join(self.dir, "absent.md")]):
            code, doc, err = self.rc(["record-call", "--run-dir", run_dir, "--call-id", started["call_id"], "--status", "ok"] + extra)
            self.assertEqual(code, 2, err); self.assertIsNone(doc); self.assertIn("--raw", err)
            self.assertEqual(sorted(os.listdir(run_dir)), listing, "verifier/ unchanged: never created")
            self.assertEqual(testlib.read_text(os.path.join(run_dir, "checkpoint.json")), cp_bytes, "checkpoint unchanged")
        code, doc, err = self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "adjudicate")

    def test_marker_quoted_words_in_the_ledger_form(self):
        """E8-A16: a grant whose quoted words contain a double quote: the ledger line and the waived marker carry
        the single-quote form and compare directly (V7, V17); the original words stay in input.json."""
        words = 'waive the "comma" one, we ship slice A without it'
        cdir, _, _ = self.full_run("S2-waivers-reopening", "S2-01-waived-clearance", self.S2_NOT_FIXED, [(0, "confirmed", ())],
                                   prep={"mutate": lambda d: d["authorization"]["waivers"][0].__setitem__("quoted_words", words)})
        result = self.validate(cdir)
        self.assertEqual(result["items"][0]["waived"]["quoted_words"], "waive the 'comma' one, we ship slice A without it")
        self.assertIn("· \"waive the 'comma' one, we ship slice A without it\"\n", self.doc_text(cdir))
        self.assertEqual(testlib.load_json(os.path.join(cdir, "run", "input.json"))["authorization"]["waivers"][0]["quoted_words"], words)

    def test_inject_hook_inert_without_recheck_test(self):
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], self.F1_REPORT)
        self.adjudicate(cdir, 0)
        readme = os.path.join(cdir, "workspace", "README.md")
        before = testlib.read_text(readme)
        env = dict(os.environ, RECHECK_TEST_INJECT_BEFORE_STEP="1", RECHECK_TEST_INJECT_FILE="README.md", RECHECK_TEST_INJECT_TEXT="edited\n")
        env.pop("RECHECK_TEST", None)
        code, out, err = testlib.run_script("recheck.py", ["record", "--run-dir", os.path.join(cdir, "run")], cwd=self.dir, env=env)
        self.assertEqual(code, 10, err); self.assertEqual(json.loads(out)["status"], "completed")
        result = self.validate(cdir)
        self.assertEqual(result["boundary_violations"], []); self.assertEqual(result["result"], "all_clear")
        self.assertEqual(testlib.read_text(readme), before, "the hook counts only with RECHECK_TEST=1")

    def test_w1_01_authorized_writes_only(self):
        """W CASES.md, W1-01 (R18): util.py, docs/notes.md, and the empty docs/reviews/ are untouched; after a
        completed run `git status --porcelain` shows only the build doc."""
        cdir = self.case("W-recording", "W1-01-authorized-writes-only")
        ws = os.path.join(cdir, "workspace")
        util, notes = os.path.join(ws, "src/widget/util.py"), os.path.join(ws, "docs/notes.md")
        util_before, notes_before = testlib.read_text(util), testlib.read_text(notes)
        self.assertEqual(os.listdir(os.path.join(ws, "docs", "reviews")), [])
        report = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:9", "disposition": "fixed", "detail": "C1 printed \"Widgets, large\",3 and columns=2,2"}])
        started = self.start(cdir)
        self.verify(cdir, started["call_id"], report)
        self.adjudicate(cdir, 0)
        code, doc, err = self.record(cdir)
        self.assertEqual(doc["status"], "completed", err)
        result = self.validate(cdir)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        self.assertEqual(testlib.project_status(ws).strip(), "M " + DOC, "only the build doc changed (R18)")
        self.assertEqual(testlib.read_text(util), util_before); self.assertEqual(testlib.read_text(notes), notes_before)
        self.assertEqual(os.listdir(os.path.join(ws, "docs", "reviews")), [])
        self.assertIn("Verdict doc: none found, build doc only", testlib.read_text(doc["chat"]))


if __name__ == "__main__":
    unittest.main()
