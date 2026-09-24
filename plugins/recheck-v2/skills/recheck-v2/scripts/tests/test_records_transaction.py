"""E13 slice 1, briefs 3.3, 3.4 and 3.5: the append inside the recording transaction.

Every record the section 9 transaction writes is an event appended through `records.py append
--expect-head <the head read at plan time>`, the Markdown the pilot places is a rendering of those
events, and the receipt records the append before any document step. A refusal of the append is the
pilot's matching stop with NOTHING written to the document. A failure after the append and before
the document steps finish is recoverable, in both directions, and `resume` never appends twice.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import records_client as rc  # noqa: E402

RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
DOC = "docs/plans/2026-09-18-widget-export.md"
LOG = "docs/records/docs__plans__2026-09-18-widget-export.events.jsonl"


class RunBase(unittest.TestCase):
    LANE = "F1-fixed-defect"
    CASE = "F1-01-fixed-clean"
    DISPOSITION = "fixed"

    def setUp(self):
        self.dir = testlib.make_scratch("e13-txn-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case(self.LANE, self.CASE, self.dir)
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.input = testlib.prepare_input(self.case)
        self.client = rc.open_client(records_root=RECORDS)

    # ---- driving ---------------------------------------------------------------------------

    def cli(self, args, hooks=None):
        return testlib.recheck(args, cwd=self.dir, hooks=hooks)

    def to_adjudicated(self):
        code, doc, err = self.cli(["start", self.input])
        self.assertEqual(code, 0, err)
        items = [{"index": i, "location": "%s:%s" % (it["location"]["file"], it["location"]["line"]),
                  "disposition": self.DISPOSITION, "method": "executed"}
                 for i, it in enumerate(doc["checklist"])]
        testlib.write_report(self.run_dir, testlib.canned_report(items))
        code, _, err = self.cli(["record-call", "--run-dir", self.run_dir, "--call-id", doc["call_id"],
                                 "--status", "ok", "--raw", os.path.join(self.run_dir, "verifier", "raw.md"),
                                 "--kind", "subagent", "--model", "claude-fable-5-1"])
        self.assertEqual(code, 0, err)
        for i in range(len(items)):
            code, _, err = self.cli(["adjudicate", "--run-dir", self.run_dir, "--item", str(i), "--action", "confirmed"])
            self.assertEqual(code, 0, err)
        return doc

    def record(self, hooks=None):
        return self.cli(["record", "--run-dir", self.run_dir], hooks=hooks)

    def resume(self, hooks=None):
        path = os.path.join(self.run_dir, "resume-input.json")
        doc = testlib.load_json(os.path.join(self.run_dir, "input.json"))
        doc["invocation"]["resume"] = True
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        return self.cli(["resume", path], hooks=hooks)

    # ---- reading back ----------------------------------------------------------------------

    def doc_bytes(self):
        with open(os.path.join(self.workspace, DOC), "rb") as fh:
            return fh.read()

    def events(self):
        return [row["event"] for row in self.client.events(self.workspace, DOC)["results"]]

    def run_events(self, run_id=None):
        run_id = run_id or testlib.load_json(os.path.join(self.run_dir, "input.json"))["invocation"]["run_id"]
        return [e for e in self.events() if (e.get("actor") or {}).get("run_id") == run_id]

    def receipt(self):
        return testlib.load_json(os.path.join(self.run_dir, "receipt.json"))


class CompletedRun(RunBase):
    def test_the_run_writes_its_records_as_events_and_the_block_is_their_rendering(self):
        self.to_adjudicated()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "completed")
        kinds = [e["kind"] for e in self.run_events()]
        self.assertEqual(kinds.count("disposition"), 1)
        self.assertEqual(kinds.count("card_set"), 1, "the card moved, so one card_set belongs in the log")
        clear = [e for e in self.run_events() if e["kind"] == "disposition"][0]
        self.assertEqual(clear["disposition"], "fixed")
        self.assertTrue(clear["verified_source"]["known"], "a clear carries the six-field source")
        self.assertEqual(sorted(clear["verified_source"]["identity"]),
                         ["commit", "dirty", "submodules", "tracked_diff_sha256", "untracked", "untracked_sha256"])
        self.assertEqual(clear["actor"]["station"], "recheck-v2")
        self.assertEqual(clear["actor"]["run_id"],
                         testlib.load_json(os.path.join(self.run_dir, "input.json"))["invocation"]["run_id"])

    def test_the_log_verifies_and_derives_the_same_open_set_the_document_shows(self):
        self.to_adjudicated()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertTrue(self.client.verify(self.workspace, DOC)["ok"])
        state = self.client.state(self.workspace, DOC)
        self.assertEqual(state["counts"]["open"], 0)
        self.assertEqual(state["slices"][0]["card_observed"], "signed off")
        self.assertIn(b"Status: signed off", self.doc_bytes())

    def test_the_receipt_records_the_append_before_any_document_step(self):
        self.to_adjudicated()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        receipt = self.receipt()
        self.assertIn("append", receipt)
        append = receipt["append"]
        self.assertEqual(len(append["expected_head"]), 64)
        self.assertEqual(len(append["head"]), 64)
        self.assertNotEqual(append["expected_head"], append["head"])
        self.assertTrue(append["seqs"], "the receipt names the seqs the append produced")
        self.assertEqual(append["log"], LOG)
        # the append is recorded, and only then does the first step's intent entry land
        self.assertTrue(receipt["entries"], "no document step ran")
        self.assertEqual(receipt["entries"][0]["type"], "intent")

    def test_the_card_set_is_appended_only_for_a_status_step_that_landed(self):
        self.to_adjudicated()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        cards = [e for e in self.run_events() if e["kind"] == "card_set"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["slice"], "A")
        self.assertEqual(cards[0]["before"], "rejected")
        self.assertEqual(cards[0]["after"], "signed off")
        receipt = self.receipt()
        status_steps = [s for s in receipt["plan"] if s["kind"] == "status_line"]
        self.assertEqual(len(status_steps), 1)
        self.assertTrue(any(e["step"] == status_steps[0]["step"] and e["type"] == "done"
                            for e in receipt["entries"]))


class AppendRefusals(RunBase):
    """3.4: each refusal surfaces as the pilot's matching stop with nothing written."""

    def test_a_head_that_moved_is_recording_failed_with_the_document_untouched(self):
        self.to_adjudicated()
        before = self.doc_bytes()
        code, doc, err = self.record(hooks={"RECHECK_TEST_RECORDS_STALE_HEAD": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        self.assertEqual(self.doc_bytes(), before, "the document was written after a refused append")
        result = testlib.load_json(doc["result"])
        self.assertIn("conflict", result["stop_reason"])
        self.assertEqual(self.run_events(), [], "a refused append left events behind")

    def test_a_clear_against_another_source_is_stale_source(self):
        self.to_adjudicated()
        before = self.doc_bytes()
        code, doc, err = self.record(hooks={"RECHECK_TEST_RECORDS_WRONG_SOURCE": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "stale_source")
        self.assertEqual(self.doc_bytes(), before)
        self.assertEqual(self.run_events(), [])

    def test_an_invalid_event_is_recording_failed(self):
        self.to_adjudicated()
        before = self.doc_bytes()
        code, doc, err = self.record(hooks={"RECHECK_TEST_RECORDS_INVALID_EVENT": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        self.assertEqual(self.doc_bytes(), before)
        self.assertEqual(self.run_events(), [])


class CrashWindow(RunBase):
    """3.5: a failure after the append and before the document steps finish is recoverable."""

    def test_append_landed_and_no_document_step_did(self):
        self.to_adjudicated()
        before = self.doc_bytes()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_BEFORE_STEP": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        self.assertEqual(self.doc_bytes(), before, "no document step landed")
        landed = [e for e in self.run_events() if e["kind"] == "disposition"]
        self.assertEqual(len(landed), 1, "the append did land")
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "completed", err)
        result = testlib.load_json(doc["result"])
        self.assertIn("document", (result.get("resumed_half") or ""))
        again = [e for e in self.run_events() if e["kind"] == "disposition"]
        self.assertEqual(len(again), 1, "resume appended the disposition twice")
        self.assertIn(b"recheck: Slice A", self.doc_bytes())

    def test_append_landed_and_the_receipt_shows_intent_only(self):
        self.to_adjudicated()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_AFTER_APPEND": "1"})
        self.assertEqual(code, 10, err)
        receipt = self.receipt()
        self.assertEqual(receipt["append"].get("head"), None,
                         "the receipt must show the intent only")
        landed = [e for e in self.run_events() if e["kind"] == "disposition"]
        self.assertEqual(len(landed), 1, "the append did land")
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "completed", err)
        result = testlib.load_json(doc["result"])
        self.assertIn("append", (result.get("resumed_half") or ""))
        again = [e for e in self.run_events() if e["kind"] == "disposition"]
        self.assertEqual(len(again), 1, "resume appended the disposition twice")
        self.assertEqual(len([e for e in self.run_events() if e["kind"] == "card_set"]), 1)
        self.assertTrue(self.client.verify(self.workspace, DOC)["ok"])


class ResumeDoesNotReimportItsOwnLines(RunBase):
    """A resume inside the transaction must not import the lines the run itself wrote.

    The document steps place the RENDERING of this run's events. A receipt this core wrote already
    names the append that produced them, so importing those lines again would add a second, legacy
    copy of each record AFTER the run's own events — and file order is time order, so the legacy
    copy would win and undo the run's decision. S2-01 is the case that shows it: the item is
    `not_fixed` and then waived, and a re-import of the block line reopens it.
    """

    LANE = "S2-waivers-reopening"
    CASE = "S2-01-waived-clearance"
    DISPOSITION = "not_fixed"

    def to_adjudicated(self):
        code, doc, err = self.cli(["start", self.input])
        self.assertEqual(code, 0, err)
        items = [{"index": i, "location": "%s:%s" % (it["location"]["file"], it["location"]["line"]),
                  "disposition": "not_fixed", "reason": "reproduces", "method": "executed"}
                 for i, it in enumerate(doc["checklist"])]
        testlib.write_report(self.run_dir, testlib.canned_report(items))
        code, _, err = self.cli(["record-call", "--run-dir", self.run_dir, "--call-id", doc["call_id"],
                                 "--status", "ok", "--raw", os.path.join(self.run_dir, "verifier", "raw.md"),
                                 "--kind", "subagent", "--model", "claude-fable-5-1"])
        self.assertEqual(code, 0, err)
        for i in range(len(items)):
            code, _, err = self.cli(["adjudicate", "--run-dir", self.run_dir, "--item", str(i), "--action", "confirmed"])
            self.assertEqual(code, 0, err)
        return doc

    def test_the_log_still_agrees_with_the_document_after_a_resume(self):
        self.to_adjudicated()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_AFTER_STEP": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "completed", err)
        events = self.events()
        legacy_after_mine = [e for e in events
                             if (e.get("origin") or {}).get("kind") == "legacy"
                             and e["kind"] in ("disposition", "waived", "reopened")
                             and any(m["kind"] == e["kind"] and m.get("finding") == e.get("finding")
                                     for m in self.run_events())]
        self.assertEqual(legacy_after_mine, [],
                         "the resume imported the lines this run wrote as legacy records")
        kinds = [e["kind"] for e in self.run_events()]
        self.assertEqual(kinds.count("disposition"), 1)
        self.assertEqual(kinds.count("waived"), 1)
        state = self.client.state(self.workspace, DOC)
        waived = [f for f in state["findings"] if f["status"] == "waived"]
        self.assertEqual(len(waived), 1, "the document waives the item; the log must agree")
        self.assertEqual(state["open"]["BLOCKER"], 0)
        self.assertIn(b"- WAIVED (per user)", self.doc_bytes())


if __name__ == "__main__":
    unittest.main()
