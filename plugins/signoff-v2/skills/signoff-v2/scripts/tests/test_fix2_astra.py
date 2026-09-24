"""E13 slice 2 fix round: Astra's findings against the signoff core, rebuilt as tests.

Each class rebuilds the SHAPE of one of her probes through the real CLI (her probe scripts are not
available to this round; `astra-review-slice-2.md` names each probe's shape and output). The class
docstring names the finding. They were written red first; the red output is kept in the fix
round's scratch folder.
"""
import json
import os
import unittest

import shimlib
import testlib

testlib.add_scripts_to_path()

DOC = "docs/plans/2026-09-18-signpost-rows.md"
LOG = "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl"


def read_log(workspace):
    path = os.path.join(workspace, LOG)
    if not os.path.isfile(path):
        return []
    return [json.loads(line) for line in testlib.read_text(path).split("\n") if line.strip()]


def kinds(workspace, kind):
    return [e for e in read_log(workspace) if e.get("kind") == kind]


class _Case(unittest.TestCase):
    """One seeded case with the station pointed at a shim in front of the real component."""

    CASE = "S1-02-untracked-defect"

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-fix2-")
        self.addCleanup(testlib.rmtree, self.dir)
        family = testlib.family_of(self.CASE)
        self.case = testlib.build_case(family, self.CASE, os.path.join(self.dir, family))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.shim, self.fault = shimlib.make_shim(self.dir, testlib.RECORDS_ROOT)
        self.env = shimlib.env(self.shim, testlib.RECORDS_ROOT, self.fault)
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        self.seeded = seeded
        doc = {
            "protocol_version": 1,
            "invocation": {
                "mode": "headless", "caller": "test", "run_id": "signoff-fix2-run",
                "run_dir": self.run_dir, "run_date": "2026-09-21", "harness": "test-harness",
                "sessions": {"building": seeded["sessions"]["building"],
                             "reviewing": seeded["sessions"]["reviewing"]},
            },
            "workspace": self.workspace,
            "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                       "base": seeded["base"]},
            "report_only": False,
            "review": {"depth": "LEAN", "route": "readers:claude-session"},
        }
        self.input_path = testlib.write_json(os.path.join(self.case, "signoff-input.json"), doc)

    def phase(self, args):
        return testlib.signoff(args, env=self.env)

    def to_scope(self):
        code, doc, err = self.phase(["check-input", self.input_path])
        self.assertEqual(code, 0, err or json.dumps(doc))
        return self.phase(["scope", "--run-dir", self.run_dir])

    def through_answer(self, answer=None):
        code, doc, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["request", "--run-dir", self.run_dir])
        self.assertEqual(code, 0, err or json.dumps(doc))
        path = os.path.join(self.case, "answer.json")
        if answer is not None:
            path = testlib.write_json(os.path.join(self.case, "answer-fix2.json"), answer)
        return self.phase(["record-answer", "--run-dir", self.run_dir, "--answer", path])

    def record(self):
        return self.phase(["record", "--run-dir", self.run_dir])

    def result(self):
        return testlib.load_json(os.path.join(self.run_dir, "result.json"))

    def answer(self):
        return testlib.load_json(os.path.join(self.case, "answer.json"))

    def doc_text(self):
        return testlib.read_text(os.path.join(self.workspace, DOC))

    def write(self, rel, text):
        path = os.path.join(self.workspace, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)


class F3SignoffNeverSignsSourceAbsentFromItsPacket(_Case):
    """F3 (BLOCKER). Before the first project-record write, the identity now is compared with the
    identity pinned when the packet was built; a mismatch ends `stale_source` with both
    identities and no project record. Astra's `probe_windows.py` changed source, added
    `src/never-reviewed.py`, or edited the document after the answer: each signed off."""

    def assert_stale(self, before_doc):
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "stale_source", json.dumps(result)[:1200])
        self.assertEqual(result["stop_reason_code"], "source_moved")
        self.assertTrue(result["source_identity"])
        self.assertTrue(result["identity_now"])
        self.assertNotEqual(result["source_identity"], result["identity_now"])
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(read_log(self.workspace), [], "no project record, not even a levelling")
        self.assertEqual(self.doc_text(), before_doc)
        self.assertFalse(os.path.isdir(os.path.join(self.workspace, "docs", "reviews")) and
                         any(n.endswith(".md") and "signoff" in n for n in
                             os.listdir(os.path.join(self.workspace, "docs", "reviews"))))

    def test_a_source_file_changed_after_the_answer(self):
        self.through_answer()
        self.write("src/signpost/pad.py", "def pad(text, width):\n    return text.ljust(width)\n")
        self.assert_stale(self.doc_text())

    def test_an_untracked_file_added_after_the_answer(self):
        self.through_answer()
        self.write("src/never-reviewed.py", "UNREVIEWED = True\n")
        self.assert_stale(self.doc_text())

    def test_the_document_edited_after_the_answer(self):
        self.through_answer()
        self.write(DOC, self.doc_text() + "\nA sentence added after the review.\n")
        self.assert_stale(self.doc_text())

    def test_the_events_carry_the_reviewed_identity(self):
        self.through_answer()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "completed")
        for event in kinds(self.workspace, "finding_raised") + kinds(self.workspace, "card_set"):
            self.assertEqual(event["source"]["identity"], result["source_identity"])


class F4BuilderNotesAreNeverEvidence(_Case):
    """F4 (MAJOR). Builder-conversation provenance reaches answer validation: a citation of a
    builder-notes path, or a quotation of its withheld content, anywhere in the answer (prose,
    findings, `checks_executed`) is refused as `independence`. Astra's `probe_signoff.py` got
    `Evidence: builder-notes.md:2 confirms this verdict.` and a notes-citing check through."""

    CASE = "S3-03-builder-notes-untracked"

    def assert_refused(self, answer):
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["refusal_reason"], "independence", json.dumps(result["problems"]))
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(read_log(self.workspace), [])
        return result

    def test_an_explicit_citation_in_the_prose(self):
        answer = self.answer()
        answer["notes"] = "Evidence: BUILDER-NOTES.md:2 confirms this verdict."
        self.assert_refused(answer)

    def test_a_citation_by_its_full_path(self):
        answer = self.answer()
        answer["notes"] = "Evidence: docs/BUILDER-NOTES.md:3 says the separator case was run."
        self.assert_refused(answer)

    def test_a_check_that_reads_the_notes(self):
        answer = self.answer()
        answer["checks_executed"].append({"name": "read the builder's account",
                                          "command": "cat docs/BUILDER-NOTES.md",
                                          "exit_code": 0, "output": "the separator case passed"})
        self.assert_refused(answer)

    def test_a_short_attributed_quotation(self):
        answer = self.answer()
        answer["notes"] = 'The builder wrote "no need to re-run the separator" and I agree.'
        self.assert_refused(answer)

    def test_the_clean_answer_still_signs(self):
        code, doc, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(doc))


class F6RecoveryChecksEveryCompletedTarget(_Case):
    """F6 (MAJOR). On recovery and before commit, every fully completed target must match its
    final planned hash; an outside edit is `recording_failed/outside_edit` and is left intact;
    the card values come from the receipt. Astra's `probe_signoff_recovery_edit.py` killed after
    the card append, set `Status:` to `rejected`, recovered, and got `completed`."""

    def kill_after_the_card(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        code, doc, err = self.record()
        self.assertNotEqual(code, 10, "the run was killed")
        shimlib.disarm(self.fault)

    def test_an_edit_to_the_card_line_during_the_crash_window(self):
        self.kill_after_the_card()
        text = self.doc_text()
        self.assertIn("Status: signed off with conditions", text)
        edited = text.replace("Status: signed off with conditions", "Status: rejected")
        self.write(DOC, edited)
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "recording_failed", json.dumps(result)[:1500])
        self.assertEqual(result["stop_reason_code"], "outside_edit")
        self.assertEqual(self.doc_text(), edited, "the outside edit is left intact")

    def test_a_clean_recovery_reports_the_card_from_the_receipt(self):
        self.kill_after_the_card()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["card"]["before"], "built")
        self.assertEqual(result["card"]["after"], "signed off with conditions")
        self.assertTrue(result["card"]["moved"])
        self.assertEqual(len(kinds(self.workspace, "card_set")), 1)


class F7AnIdentityFailureEndsInANamedStop(_Case):
    """F7 (MAJOR). A refusal of `records.py identity` is a named stop with a result. Astra's
    `probe_identity_real_failure.py` hid the fixture's git directory while the real identity CLI
    ran: records exited 2, signoff exited 1 with a traceback and no `result.json`."""

    def test_the_real_identity_failure_at_record(self):
        self.through_answer()
        shimlib.fault(self.fault, command="identity", action="hide_git")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "result.json")), err)
        result = self.result()
        self.assertEqual(result["stop_reason_code"], "identity_refused")
        self.assertEqual(result["status"], "recording_failed")
        self.assertEqual(result["records"]["records_exit"], 2)
        self.assertNotIn("Traceback", err)
        self.assertEqual(kinds(self.workspace, "finding_raised"), [])

    def test_the_real_identity_failure_at_scope(self):
        code, doc, err = self.phase(["check-input", self.input_path])
        self.assertEqual(code, 0, err)
        shimlib.fault(self.fault, command="identity", action="hide_git")
        code, doc, err = self.phase(["scope", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["stop_reason_code"], "identity_refused")
        self.assertNotIn("Traceback", err)


class F8PartialRecordingFailuresAreReportedFromTheReceipt(_Case):
    """F8 (MAJOR). A `recording_failed` result is built from the receipt: landed appends with
    their seqs, the completed document targets, the authorized verdict path, the card's partial
    state and the failing command's exit, error and reason. It validates and exits 10, and a
    definitive refusal is never retried. Astra's `probe_availability.py` refused `mirrors` after
    the writes landed and got `appended: []`, `verdict_doc: null`, exit 4."""

    def test_mirrors_refused_after_the_writes_landed(self):
        self.through_answer()
        shimlib.fault(self.fault, command="mirrors", action="fail", exit=7, error="conflict",
                      reason="injected: mirrors is unavailable")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "recording_failed")
        self.assertEqual(result["stop_reason_code"], "mirrors_refused")
        self.assertTrue(result["verdict_doc"].startswith("docs/reviews/"), result["verdict_doc"])
        appended = result["records"]["appended"]
        self.assertEqual([row["name"] for row in appended], ["findings"])
        self.assertTrue(appended[0]["seqs"])
        self.assertEqual(result["records"]["records_exit"], 7)
        self.assertEqual(result["records"]["records_error"], "conflict")
        self.assertIn("mirrors is unavailable", result["stop_reason"])
        self.assertEqual(result["card"]["after"], "signed off with conditions")
        self.assertTrue(result["card"]["moved"], "the Status line landed")
        done = [row["kind"] for row in result["document_steps"] if row["state"] == "done"]
        self.assertEqual(done, ["block", "verdict_doc", "card"])

    def test_the_card_append_refused(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="card_set", action="fail", exit=7,
                      error="conflict", reason="injected: the log moved")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "recording_failed")
        self.assertEqual(result["stop_reason_code"], "append_refused")
        self.assertEqual([row["name"] for row in result["records"]["appended"]], ["findings"])
        self.assertTrue(result["verdict_doc"])
        self.assertTrue(result["card"]["moved"])
        self.assertEqual(result["records"]["records_exit"], 7)
        self.assertIn("Status: signed off with conditions", self.doc_text())
        # a definitive refusal is never retried: a second pass re-delivers it
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(self.result()["status"], "recording_failed")
        self.assertEqual(kinds(self.workspace, "card_set"), [])


class F12TheStrictLegacyStopBeforeLevelling(_Case):
    """F12 (MAJOR), signoff's half. A hand-written line under a review heading that fits no
    Appendix A shape stops the run with its document, line and raw bytes before the log is
    levelled; no card or verdict is written. Astra's `probe_legacy_parity.py` line below: both
    pilot versions stopped `missing_input`; signoff completed and signed off."""

    LINE = "- MAJOR · src/widget.py:2 · Call spin and observe zero."

    def test_the_reader_is_the_pilots_own_byte_for_byte(self):
        """One record grammar: the stop check is the recheck pilot's `ledger.py`, copied whole and
        held equal here, never a second reader of this station's own."""
        pilot = os.path.join(os.path.dirname(testlib.PLUGIN), "recheck-v2", "skills", "recheck-v2",
                             "scripts", "recheck_core", "ledger.py")
        mine = os.path.join(testlib.SCRIPTS, "signoff_core", "record_grammar.py")
        with open(pilot, "rb") as fh:
            want = fh.read()
        with open(mine, "rb") as fh:
            self.assertEqual(fh.read(), want)

    def test_an_unplaceable_line_stops_scope(self):
        text = self.doc_text() + "\n### 2026-09-19 — review: Slice D\n%s\n" % self.LINE
        self.write(DOC, text)
        line_no = text.split("\n").index(self.LINE) + 1
        testlib.git(self.workspace, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-qam", "a hand-written review")
        code, doc, err = self.to_scope()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "missing_input")
        self.assertEqual(result["stop_reason_code"], "legacy_ambiguous")
        self.assertIn("%s:%d" % (DOC, line_no), result["stop_reason"])
        self.assertIn(self.LINE, result["stop_reason"])
        self.assertEqual(result["unplaced"][0]["raw"], self.LINE)
        self.assertEqual(result["unplaced"][0]["line"], line_no)
        self.assertEqual(read_log(self.workspace), [])


class F16DemotingFindingsNeverBypassesTheCleanReviewCheck(_Case):
    """F16 (MAJOR). The clean-review check applies after findings are partitioned: when no
    finding remains raised and no executed check carries a name and output, `record-answer`
    refuses the answer as `answer_invalid` and no recording starts. Astra's
    `probe_signoff_outside_no_checks.py` supplied one out-of-source finding and no checks."""

    def test_one_out_of_source_finding_and_no_checks(self):
        answer = self.answer()
        answer["findings"] = [{"location": "src/elsewhere/outside.py:3", "severity": "MAJOR",
                               "claim": "a defect outside the slice",
                               "scenario": "call it and observe the wrong value",
                               "evidence_kind": "read"}]
        answer["checks_executed"] = []
        answer["verdict"] = "signed off"
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["refusal_reason"], "answer_invalid")
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(read_log(self.workspace), [])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "receipt.json")))


if __name__ == "__main__":
    unittest.main()
