"""The body's steps followed literally on three lanes (E8 lane contract section 9, slice 3 row): the
command templates are read out of SKILL.md's fenced blocks, their placeholders filled, and run in the
body's order (start, record-call with a canned report written from CASES.md facts, adjudicate,
record); chat.md then opens with the Appendix A first line and result.json passes validate-result.py.
Also the body's one-question path (a fresh run id after the answer) and its resume command, and one test per
adjudication branch of step 6 (downgraded, upgraded, disputed under session_wrote_fix, new-defect from a
candidate and driver-supplied) plus step 5's --refused and --note flags."""
import json
import os
import re
import shlex
import unittest

import testlib

testlib.add_scripts_to_path()

SKILL_MD = os.path.join(testlib.SKILL, "SKILL.md")
DOC = "docs/plans/2026-09-18-widget-export.md"
# contract section 14, the default table's MAJOR row, quoted as the body's new-defect command asks
BASIS = "default table: MAJOR: a real defect with a concrete failure path, contained and fixable in place"
FIRST_LINE = re.compile(r"^RECHECK: \S+ — \d+ items \(\+\d+ new\)$")


def templates():
    """{subcommand: tokens} from SKILL.md's fenced `uv run scripts/recheck.py ...` lines (the first of each)."""
    with open(SKILL_MD, "r", encoding="utf-8") as fh:
        text = fh.read()
    out, fence = {}, False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
            continue
        if fence and line.strip().startswith("uv run scripts/recheck.py"):
            tokens = shlex.split(line.strip())[3:]
            out.setdefault(tokens[0], tokens)
    return out


def fill(tokens, values):
    """Replace every <placeholder> token with its value; a placeholder valued None drops it and its flag."""
    out = []
    for t in tokens:
        m = re.match(r"^<(.+)>$", t)
        if not m:
            out.append(t)
        elif values[m.group(1)] is None:
            if out and out[-1].startswith("--"):
                out.pop()
        else:
            out.append(values[m.group(1)])
    return out


class Literal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = templates()
        for sub in ("start", "record-call", "adjudicate", "new-defect", "record", "resume"):
            if sub not in cls.t:
                raise AssertionError("SKILL.md names no fenced %s command" % sub)

    def setUp(self):
        self.dir = testlib.make_scratch("e8-slice3-e2e-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    def run_step(self, sub, values, expect):
        code, doc, err = testlib.recheck(fill(self.t[sub], values), cwd=self.dir)
        self.assertEqual(code, expect, "%s: exit %d\n%s\n%s" % (sub, code, err, doc))
        return doc

    def run_tokens(self, sub, values, extra, expect):
        """A fenced template filled, plus the flags the prose beside it names (--reason, --note, --upgrade-evidence,
        --location/--claim/--scenario/--caused-by, --refused, --note)."""
        code, doc, err = testlib.recheck(fill(self.t[sub], values) + list(extra), cwd=self.dir)
        self.assertEqual(code, expect, "%s: exit %d\n%s\n%s" % (sub, code, err, doc))
        return doc

    def drive(self, lane, cid, report, expect_status="completed", mutate=None, actions=None, defects=(), call_extra=()):
        """Steps 2 (the fixture's input, the adapter objects added, `mutate` for a trial condition), 3, 4 (canned), 5
        (with `call_extra` flags), 6 (`actions`: {index: [action, extra flags...]}, default confirmed; then each
        `defects` entry: ("index", k) for a candidate or ("supplied", [flags]) for the driver-supplied form), 7, 8."""
        cdir = testlib.build_case(lane, cid, os.path.join(self.dir, lane))
        input_path = testlib.prepare_input(cdir, mutate=mutate)
        run_dir = os.path.join(cdir, "run")
        started = self.run_step("start", {"input.json": input_path}, 0)
        self.assertEqual(started["next"], "verify")
        self.assertEqual(started["run_dir"], run_dir); self.assertEqual(started["brief"], os.path.join(run_dir, "checklist.md"))
        self.assertTrue(os.path.isfile(started["brief"]) and os.path.getsize(started["brief"]) > 0)
        # step 4 stands in: the verifier's report is canned from CASES.md facts and lands in the scratch directory
        raw = testlib.write_report(run_dir, report)
        called = self.run_tokens("record-call", {"run_dir": run_dir, "call_id": started["call_id"], "status": "ok", "report": raw,
                                                 "model": "test-verifier", "kind": "canned", "channel": "AGENTS.md"}, call_extra, 0)
        self.assertEqual(called["next"], "adjudicate")
        self.last_called = called
        pending = [it["index"] for it in called["items"]]
        self.adjudicated = {}
        for index in pending:
            action, extra = (actions or {}).get(index, ["confirmed"])[0], (actions or {}).get(index, ["confirmed"])[1:]
            adj = self.run_tokens("adjudicate", {"run_dir": run_dir, "index": str(index), "action": action}, extra, 0)
            self.adjudicated[index] = adj
        self.assertEqual(adj["next"], "record"); self.assertEqual(adj["pending"], [])
        for form, arg in defects:
            if form == "index":
                nd = self.run_tokens("new-defect", {"run_dir": run_dir, "k": str(arg), "severity": "MAJOR", "bar line or default table row": BASIS}, (), 0)
            else:
                nd = self.run_tokens("new-defect", {"run_dir": run_dir, "k": None, "severity": "MAJOR", "bar line or default table row": BASIS}, arg, 0)
            self.assertEqual(nd["next"], "record")
        recorded = self.run_step("record", {"run_dir": run_dir}, 10)
        self.assertEqual(recorded["next"], "done"); self.assertEqual(recorded["status"], expect_status)
        # step 8: chat.md is the verdict; result.json validates
        chat = testlib.read_text(recorded["chat"])
        self.assertTrue(chat.strip(), "chat.md non-empty")
        self.assertRegex(chat.split("\n")[0], FIRST_LINE)
        args = [recorded["result"], "--input", os.path.join(run_dir, "input.json"), "--run-dir", run_dir]
        code, out, err = testlib.run_script("validate-result.py", args, cwd=self.dir)
        got = json.loads(out)
        self.assertEqual(code, 0, "%s\n%s" % (err, out)); self.assertEqual(got["semantic"], []); self.assertEqual(got["skipped"], [])
        return cdir, testlib.load_json(recorded["result"]), chat

    def kinds(self, result):
        return [w["kind"] for w in result["records_written"] if w["kind"] != "run_artifact"]

    # F1 CASES.md, F1-01: at HEAD the scenario prints "Bolt, hex",3 and columns=2; the row write is at export.py:20
    F1 = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed",
                                  "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed \"Bolt, hex\",3 and columns=2",
                                  "location_after_fix": "src/widget/export.py:20"}])
    # F2 CASES.md, F2-01: at HEAD the scenario prints Widgets, large,3 and columns=2,3 (three columns), so it reproduces
    F2 = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:9", "disposition": "not_fixed", "reason": "reproduces",
                                  "detail": "PYTHONPATH=src python3 -m widget.export \"Widgets, large\" 3 printed Widgets, large,3 and columns=2,3"}])
    # S2 CASES.md, S2-01: at HEAD line 11 returns the row unquoted; the scenario prints Bolt, hex,3 and columns: 3
    S2 = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:11", "disposition": "not_fixed", "reason": "reproduces",
                                  "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed Bolt, hex,3 and columns: 3"}])

    def test_f1_01(self):
        """Sections 4 and 9: the one BLOCKER fixed, all_clear, the card rejected -> signed off, block plus status line."""
        cdir, result, chat = self.drive("F1-fixed-defect", "F1-01-fixed-clean", self.F1)
        self.assertEqual(chat.split("\n")[0], "RECHECK: A — 1 items (+0 new)")
        self.assertTrue(chat.split("\n")[1].startswith("Result: ALL CLEAR · Status: rejected → signed off"), chat)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["items"][0]["disposition"], "fixed")
        self.assertEqual([(c["before"], c["after"]) for c in result["cards"]], [("rejected", "signed off")])
        self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        self.assertIn("Status: signed off", testlib.read_text(os.path.join(cdir, "workspace", DOC)))

    def test_f2_01(self):
        """R6: the item not_fixed (reproduces), not_clear, the card unchanged, the block alone written."""
        cdir, result, chat = self.drive("F2-unfixed-defect", "F2-01-reproduces", self.F2)
        self.assertEqual(chat.split("\n")[0], "RECHECK: A — 1 items (+0 new)")
        self.assertTrue(chat.split("\n")[1].startswith("Result: NOT CLEAR · Status: unchanged (rejected)"), chat)
        self.assertEqual(result["result"], "not_clear"); self.assertEqual(result["items"][0]["reason"], "reproduces")
        self.assertEqual(self.kinds(result), ["punch_list_block"])
        self.assertIn("Status: rejected", testlib.read_text(os.path.join(cdir, "workspace", DOC)))

    def test_s2_01(self):
        """R42, R29: the BLOCKER not_fixed but waived by the accepted grant: block line not fixed, waiver line after it,
        item marked waived, all_clear, card rejected -> signed off."""
        cdir, result, chat = self.drive("S2-waivers-reopening", "S2-01-waived-clearance", self.S2)
        self.assertEqual(chat.split("\n")[0], "RECHECK: A — 1 items (+0 new)")
        self.assertTrue(chat.split("\n")[1].startswith("Result: ALL CLEAR · Status: rejected → signed off"), chat)
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(result["items"][0]["disposition"], "not_fixed")
        self.assertEqual(result["items"][0]["waived"]["quoted_words"], "waive the comma one, we ship slice A without it")
        self.assertEqual(self.kinds(result), ["punch_list_block", "waived_line", "status_line"])
        text = testlib.read_text(os.path.join(cdir, "workspace", DOC))
        self.assertLess(text.index("· not fixed ·"), text.index("- WAIVED (per user) · 2026-09-20 · BLOCKER · src/widget/export.py:11"))

    def test_one_question_then_a_fresh_run_id(self):
        """Step 3 of the body: a direct interactive run missing its reopening grant (S2 CASES.md, S2-03 without
        authorization; contract section 3) answers next: done with one question; after the answer the input is
        rebuilt under a fresh run id and directory, and the spent directory would have refused a restart (E8-23)."""
        cdir = testlib.build_case("S2-waivers-reopening", "S2-03-reopened", os.path.join(self.dir, "S2"))
        full = testlib.load_json(os.path.join(cdir, "input.json"))
        input_path = testlib.prepare_input(cdir, mutate=lambda d: d.pop("authorization"))
        doc = self.run_step("start", {"input.json": input_path}, 10)
        self.assertEqual(doc["next"], "done"); self.assertEqual(doc["status"], "missing_input")
        self.assertTrue(doc["question"], "the one question")
        self.assertEqual(testlib.load_json(doc["result"])["missing_input"]["fields"], ["authorization.reopen"])
        # the same id again is refused: the directory holds a result
        again = self.run_step("start", {"input.json": input_path}, 10)
        self.assertIn("reused run id", again["document"]["stop_reason"])
        # rebuilt from the answer under a fresh id and directory
        def rebuild(d):
            d["authorization"] = full["authorization"]
            d["invocation"]["run_id"] = "S2-03-reopened-run-2"
            d["invocation"]["run_dir"] = os.path.join(cdir, "run-2")
        rebuilt = testlib.prepare_input(cdir, mutate=rebuild, path=os.path.join(cdir, "input-2.json"))
        started = self.run_step("start", {"input.json": rebuilt}, 0)
        self.assertEqual(started["next"], "verify"); self.assertEqual(started["call_id"], "S2-03-reopened-run-2-verify")

    def test_resume_command_after_a_recording_failure(self):
        """The body's Resume path: the same document with resume: true completes a run the transaction left as
        recording_failed (section 9, R34), with no duplicate append."""
        cdir = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean", os.path.join(self.dir, "F1"))
        input_path = testlib.prepare_input(cdir)
        run_dir = os.path.join(cdir, "run")
        started = self.run_step("start", {"input.json": input_path}, 0)
        raw = testlib.write_report(run_dir, self.F1)
        self.run_step("record-call", {"run_dir": run_dir, "call_id": started["call_id"], "status": "ok", "report": raw,
                                      "model": "test-verifier", "kind": "canned", "channel": "AGENTS.md"}, 0)
        self.run_step("adjudicate", {"run_dir": run_dir, "index": "0", "action": "confirmed"}, 0)
        code, doc, err = testlib.recheck(fill(self.t["record"], {"run_dir": run_dir}), cwd=self.dir, hooks={"RECHECK_TEST_FAIL_AFTER_STEP": "1"})
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "recording_failed")
        resume_path = testlib.prepare_input(cdir, model=False, harness=False, run_date=None, mutate=lambda d: d["invocation"].__setitem__("resume", True),
                                            path=os.path.join(cdir, "input.resume.json"))
        resumed = self.run_step("resume", {"input.json": resume_path}, 10)
        self.assertEqual(resumed["next"], "done"); self.assertEqual(resumed["status"], "completed")
        text = testlib.read_text(os.path.join(cdir, "workspace", DOC))
        self.assertEqual(text.count("### 2026-09-20 — recheck: Slice A"), 1); self.assertIn("Status: signed off", text)
        chat = testlib.read_text(resumed["chat"])
        self.assertEqual(chat.split("\n")[0], "RECHECK: A — 1 items (+0 new)")


    # ---- step 6, one test per adjudication branch, and step 5's --refused and --note (slice 3 fix round) ----

    def test_adjudicate_downgraded_with_reason_and_note(self):
        """Step 6 `downgraded`: F1-01 with a verifier saying fixed; the executor holds evidence the scenario still holds
        and downgrades to not_fixed / reproduces with --reason and --note (section 7). The item stays open, no card moves."""
        note = "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed Bolt, hex,3 and columns=3 in my run"
        cdir, result, chat = self.drive("F1-fixed-defect", "F1-01-fixed-clean", self.F1,
                                        actions={0: ["downgraded", "--reason", "reproduces", "--note", note]})
        self.assertEqual(self.adjudicated[0]["disposition"], "not_fixed"); self.assertEqual(self.adjudicated[0]["driver_action"], "downgraded")
        item = result["items"][0]
        self.assertEqual(item["disposition"], "not_fixed"); self.assertEqual(item["reason"], "reproduces")
        self.assertEqual(item["adjudication"], {"verifier_said": "fixed", "driver_action": "downgraded", "session_wrote_fix": False, "note": note})
        self.assertEqual(result["result"], "not_clear"); self.assertEqual(self.kinds(result), ["punch_list_block"])
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "rejected"}])
        self.assertTrue(chat.split("\n")[1].startswith("Result: NOT CLEAR · Status: unchanged (rejected)"), chat)
        self.assertIn("· not fixed ·", testlib.read_text(os.path.join(cdir, "workspace", DOC)))

    def test_adjudicate_upgraded_with_evidence(self):
        """Step 6 `upgraded`: F2-01 with a verifier saying not_fixed; the executor holds evidence the verifier lacked and
        session_wrote_fix is false, so the item is fixed with the evidence recorded (section 7)."""
        evidence = "the CI log of the fix commit shows columns=2,2 for \"Widgets, large\" 3 under the pinned csv module"
        cdir, result, chat = self.drive("F2-unfixed-defect", "F2-01-reproduces", self.F2,
                                        actions={0: ["upgraded", "--upgrade-evidence", evidence]})
        self.assertEqual(self.adjudicated[0]["disposition"], "fixed"); self.assertEqual(self.adjudicated[0]["driver_action"], "upgraded")
        item = result["items"][0]
        self.assertEqual(item["disposition"], "fixed"); self.assertNotIn("reason", item)
        self.assertEqual(item["adjudication"], {"verifier_said": "not_fixed", "driver_action": "upgraded", "session_wrote_fix": False,
                                                "upgrade_evidence": evidence})
        self.assertFalse(result["run"]["session_wrote_fix"])
        self.assertEqual(result["result"], "all_clear"); self.assertEqual(self.kinds(result), ["punch_list_block", "status_line"])
        self.assertEqual([(c["before"], c["after"]) for c in result["cards"]], [("rejected", "signed off")])
        self.assertTrue(chat.split("\n")[1].startswith("Result: ALL CLEAR · Status: rejected → signed off"), chat)

    def test_adjudicate_disputed_when_the_session_wrote_the_fix(self):
        """Step 6 `disputed`: F2-02 under its trial condition session_wrote_fix true; an attempted upgrade with evidence
        lands as disputed and the item stays open (section 7, E8-13)."""
        cdir, result, chat = self.drive("F2-unfixed-defect", "F2-02-session-wrote-fix", self.F2,
                                        mutate=lambda d: d["invocation"].__setitem__("session_wrote_fix", True),
                                        actions={0: ["upgraded", "--upgrade-evidence", "I ran it myself after the fix"]})
        self.assertEqual(self.adjudicated[0]["disposition"], "not_fixed"); self.assertEqual(self.adjudicated[0]["driver_action"], "disputed")
        item = result["items"][0]
        self.assertEqual(item["disposition"], "not_fixed"); self.assertEqual(item["reason"], "reproduces")
        self.assertEqual(item["adjudication"]["driver_action"], "disputed"); self.assertTrue(item["adjudication"]["session_wrote_fix"])
        self.assertIn("cannot upgrade", item["adjudication"]["note"]); self.assertNotIn("upgrade_evidence", item["adjudication"])
        self.assertTrue(result["run"]["session_wrote_fix"])
        self.assertEqual(result["result"], "not_clear"); self.assertEqual(self.kinds(result), ["punch_list_block"])
        self.assertEqual(result["cards"], [{"slice": "A", "before": "rejected", "after": "rejected"}])

    # F1 CASES.md, F1-02: the comma scenario holds at HEAD ("Bolt, hex",3, columns=2); Bolt 0 prints Bolt, (an empty qty
    # cell, the base commit printed Bolt,0) on the row write the fix added at export.py:20
    F1_02_ITEM = {"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed",
                  "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed \"Bolt, hex\",3 and columns=2",
                  "location_after_fix": "src/widget/export.py:20"}
    F1_02_DEFECT = {"location": "src/widget/export.py:20", "claim": "a zero quantity exports as an empty qty cell",
                    "scenario": "PYTHONPATH=src python3 -m widget.export Bolt 0 prints the data line Bolt, with an empty qty cell where the base printed Bolt,0"}

    def check_f1_02(self, cdir, result, chat):
        d = result["new_defects"][0]
        self.assertEqual(len(result["new_defects"]), 1)
        self.assertEqual((d["severity"], d["severity_basis"], d["charged_to_slice"], d["source"]), ("MAJOR", BASIS, "A", "fix_introduced"))
        self.assertEqual(d["location"], {"file": "src/widget/export.py", "line": 20}); self.assertEqual(d["claim"], self.F1_02_DEFECT["claim"])
        self.assertEqual(result["items"][0]["disposition"], "fixed")
        self.assertEqual(result["result"], "partial")
        self.assertEqual([(c["before"], c["after"]) for c in result["cards"]], [("rejected", "signed off with conditions")])
        self.assertEqual(result["still_open"], ["MAJOR · src/widget/export.py:20 · broke: %s" % self.F1_02_DEFECT["claim"]])
        self.assertEqual(chat.split("\n")[0], "RECHECK: A — 1 items (+1 new)")
        self.assertTrue(chat.split("\n")[1].startswith("Result: PARTIAL (1 open) · Status: rejected → signed off with conditions"), chat)
        text = testlib.read_text(os.path.join(cdir, "workspace", DOC))
        self.assertIn("- MAJOR · src/widget/export.py:20 · broke: %s — %s\n" % (self.F1_02_DEFECT["claim"], self.F1_02_DEFECT["scenario"]), text)
        self.assertIn("Status: signed off with conditions", text)

    def test_new_defect_from_a_verifier_candidate(self):
        """Step 6 `new-defect --index`: F1-02, the verifier's candidate confirmed as MAJOR under the default table
        (section 14), charged to slice A; the card moves to signed off with conditions and the result is partial."""
        report = testlib.canned_report([self.F1_02_ITEM], new_defects=[{"caused_by_index": 0, "location": self.F1_02_DEFECT["location"],
                                                                        "claim": self.F1_02_DEFECT["claim"], "failure_scenario": self.F1_02_DEFECT["scenario"],
                                                                        "evidence": [{"kind": "command", "detail": "PYTHONPATH=src python3 -m widget.export Bolt 0 printed Bolt,", "artifact": None}]}])
        cdir, result, chat = self.drive("F1-fixed-defect", "F1-02-regression", report, defects=[("index", 0)])
        self.assertEqual(len(self.last_called["new_defects"]), 1)
        self.check_f1_02(cdir, result, chat)

    def test_new_defect_driver_supplied(self):
        """Step 6, the driver-supplied form: F1-02 with a report that describes the regression in its prose but left it
        out of the block; --location, --claim, --scenario, --caused-by in place of --index give the same record."""
        prose = ("Ran every scenario from the workspace root. The comma scenario holds. Running the neighboring path "
                 "PYTHONPATH=src python3 -m widget.export Bolt 0 printed Bolt, (an empty qty cell) where the base commit printed Bolt,0.")
        report = testlib.canned_report([self.F1_02_ITEM], prose=prose)
        supplied = ["--location", self.F1_02_DEFECT["location"], "--claim", self.F1_02_DEFECT["claim"], "--scenario", self.F1_02_DEFECT["scenario"],
                    "--caused-by", "0"]
        cdir, result, chat = self.drive("F1-fixed-defect", "F1-02-regression", report, defects=[("supplied", supplied)])
        self.assertEqual(self.last_called["new_defects"], [], "the block carried no candidate")
        self.check_f1_02(cdir, result, chat)

    def test_record_call_refused_and_note_flags(self):
        """Step 5: --refused lands in run.verifier.refused_actions (merged with the report's own list, no duplicate) and,
        with --note, in the call record verifier/calls.json (E8-5, E8-A7)."""
        report = testlib.canned_report([{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed",
                                         "detail": "PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3 printed \"Bolt, hex\",3 and columns=2",
                                         "location_after_fix": "src/widget/export.py:20"}],
                                       refused_actions=["declined to fetch the csv spec from the web", "declined to write README.md"])
        refused = ["declined to write README.md", "the sandbox stopped a curl to the payments host; no side effect"]
        note = "one prohibited action stopped by the sandbox, run completed"
        cdir, result, chat = self.drive("F1-fixed-defect", "F1-01-fixed-clean", report,
                                        call_extra=["--refused"] + refused + ["--note", note])
        ver = result["run"]["verifier"]
        self.assertEqual(ver["refused_actions"], refused + ["declined to fetch the csv spec from the web"])
        self.assertEqual(ver["kind"], "canned"); self.assertEqual(ver["model"], "test-verifier"); self.assertEqual(ver["injected_channels"], ["AGENTS.md"])
        calls = testlib.load_json(os.path.join(cdir, "run", "verifier", "calls.json"))["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["call_id"], ver["calls"][0]["call_id"]); self.assertEqual(calls[0]["status"], "ok")
        self.assertEqual(calls[0]["refused"], refused); self.assertEqual(calls[0]["note"], note)
        self.assertIn(os.path.join(cdir, "run", "verifier", "calls.json"), [w["path"] for w in result["records_written"]])
        self.assertEqual(result["result"], "all_clear")


if __name__ == "__main__":
    unittest.main()
