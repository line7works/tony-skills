"""The recording transaction: the log, the document, the mirror, the card — and the kill windows.

Revision 7 of the pilot contract is the law this suite enforces, because both cores copied the
same wiring and the outside reviewer broke the earlier version of it in four places:

- the receipt records an append's INTENT (the log and the head read at plan time) before the
  call and its OUTCOME after;
- a refusal the component RETURNED is definitive: it is persisted as `refused` before the named
  stop is delivered, and no later pass retries it;
- an unknown outcome (a kill with no answer) is settled against the head the RECEIPT names,
  never against a head read afresh — a head that moved since is a conflict, not permission;
- a read that failed is a stop, never an empty set;
- the head the run read its state against is pinned, and another writer between two phases is a
  named conflict before any append.

Every fault is injected through `shimlib`, a wrapper `scripts/records.py` the station resolves
by `--records-root`: the station reaches the component through the CLI only, so a wrapper is
enough to refuse a command, to kill the station around an append, or to let a rival writer in.

And the standing rule of this station: **signoff never clears a finding.** No pass of this suite
may leave a `disposition`, a `waived` or a `reopened` event in any log.
"""
import json
import os
import subprocess
import unittest

import shimlib
import testlib

testlib.add_scripts_to_path()

DOC = "docs/plans/2026-09-18-signpost-rows.md"
LOG = "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl"
CLEAR_KINDS = ("disposition", "waived", "reopened")


def read_log(workspace):
    path = os.path.join(workspace, LOG)
    if not os.path.isfile(path):
        return []
    return [json.loads(line) for line in testlib.read_text(path).split("\n") if line.strip()]


class TransactionCase(unittest.TestCase):
    """One built case, with the station pointed at a shim in front of the real component."""

    CASE = "S1-02-untracked-defect"
    SLICE = "D"

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-tx-")
        self.addCleanup(testlib.rmtree, self.dir)
        family = testlib.family_of(self.CASE)
        self.case = testlib.build_case(family, self.CASE, os.path.join(self.dir, family))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.shim, self.fault = shimlib.make_shim(self.dir, testlib.RECORDS_ROOT)
        self.env = shimlib.env(self.shim, testlib.RECORDS_ROOT, self.fault)
        self.input_path = self.write_input()

    def write_input(self, **over):
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        doc = {
            "protocol_version": 1,
            "invocation": {
                "mode": "headless", "caller": "test", "run_id": "signoff-test-run",
                "run_dir": self.run_dir, "run_date": "2026-09-21",
                "harness": "test-harness",
                "sessions": {"building": seeded["sessions"]["building"],
                             "reviewing": seeded["sessions"]["reviewing"]},
            },
            "workspace": self.workspace,
            "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                       "base": seeded["base"]},
            "report_only": bool(seeded.get("report_only")),
            "review": {"depth": "LEAN", "route": "readers:claude-session"},
        }
        for key, value in over.items():
            doc[key] = value
        path = os.path.join(self.case, "signoff-input.json")
        return testlib.write_json(path, doc)

    def phase(self, args, env=None):
        e = dict(self.env)
        if env:
            e.update(env)
        return testlib.signoff(args, env=e)

    def through_answer(self, answer=None):
        """check-input -> scope -> request -> record-answer, with the case's recorded reply."""
        code, doc, err = self.phase(["check-input", self.input_path])
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["scope", "--run-dir", self.run_dir])
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["request", "--run-dir", self.run_dir])
        self.assertEqual(code, 0, err or json.dumps(doc))
        path = answer or os.path.join(self.case, "answer.json")
        code, doc, err = self.phase(["record-answer", "--run-dir", self.run_dir, "--answer", path])
        return code, doc, err

    def record(self, env=None):
        return self.phase(["record", "--run-dir", self.run_dir], env=env)

    def receipt(self):
        return testlib.load_json(os.path.join(self.run_dir, "receipt.json"))

    def raised(self):
        return [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]

    def assertNothingRaised(self, why="nothing was appended"):
        """The log may legitimately hold CR-1's levelling events (`log_opened`,
        `import_started`, `card_observed`, `import_finished`) — the importer writes those, and
        writing them is the point of levelling. What must be absent is this run's own work."""
        self.assertEqual(self.raised(), [], why)
        for event in read_log(self.workspace):
            self.assertNotEqual(event.get("kind"), "card_set", why)

    def assertNothingCleared(self):
        for event in read_log(self.workspace):
            self.assertNotIn(event["kind"], CLEAR_KINDS,
                             "signoff never clears a finding; recheck does")


class ACleanRecordWritesAllFourThings(TransactionCase):
    def test_the_log_the_block_the_mirror_and_the_card(self):
        code, doc, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed", json.dumps(doc))

        events = read_log(self.workspace)
        raised = [e for e in events if e["kind"] == "finding_raised"]
        self.assertEqual(len(raised), 1)
        self.assertEqual(raised[0]["location"]["raw"], "src/signpost/pad.py:6")
        self.assertEqual(raised[0]["severity"], "MAJOR")
        self.assertEqual(raised[0]["actor"]["station"], "signoff-v2")
        self.assertEqual(raised[0]["actor"]["run_id"], "signoff-test-run")

        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertIn("### 2026-09-21 — review: D", build_doc)
        self.assertIn("src/signpost/pad.py:6", build_doc)

        verdict_doc = doc["verdict_doc"]
        self.assertTrue(verdict_doc.startswith("docs/reviews/"), verdict_doc)
        mirror = testlib.read_text(os.path.join(self.workspace, verdict_doc))
        self.assertIn("src/signpost/pad.py:6", mirror)
        self.assertIn("signed off with conditions", mirror)
        self.assertEqual(doc["mirrors"]["counts"]["differs"], 0, json.dumps(doc["mirrors"]))

        self.assertIn("Status: signed off with conditions", build_doc)
        cards = [e for e in events if e["kind"] == "card_set"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["after"], "signed off with conditions")
        self.assertEqual(cards[0]["before"], "built")
        self.assertNothingCleared()

    def test_raised_by_is_the_slice_and_nothing_else(self):
        """Send-back 1. `raised_by` is interface version 1's field and Appendix A's fifth one:
        "which slice's review found it". Nothing else goes in it.

        WHO reviewed is recorded elsewhere, and the run id is the join between the two: the
        event's `actor.run_id` names this run, and this run's result and verdict doc name the
        reviewer's session and route. So "recorded with who concluded it" (E13-4) holds without
        the record line carrying a session id it was never meant to carry.
        """
        self.through_answer()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))

        raised = [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]
        self.assertEqual(len(raised), 1)
        self.assertEqual(raised[0]["raised_by"], self.SLICE)
        self.assertEqual(raised[0]["actor"]["run_id"], "signoff-test-run")

        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        line = [row for row in build_doc.split("\n")
                if row.startswith("- ") and "src/signpost/pad.py:6" in row]
        self.assertEqual(len(line), 1, build_doc)
        fields = line[0][2:].split(" · ")
        self.assertEqual(len(fields), 5, line[0])
        self.assertEqual(fields[4], self.SLICE,
                         "Appendix A's fifth field is the slice, not the reviewer")
        self.assertNotIn("sess-review-1", build_doc,
                         "the reviewer's session id never reaches the record line")
        self.assertNotIn("readers:claude-session", build_doc)

        result = testlib.load_json(doc["result"])
        self.assertEqual(result["reviewer"]["session_id"], "sess-review-1")
        self.assertEqual(result["reviewer"]["route"], "readers:claude-session")
        mirror = testlib.read_text(os.path.join(self.workspace, doc["verdict_doc"]))
        self.assertIn("sess-review-1", mirror,
                      "the verdict doc names who reviewed and by what route")
        self.assertIn("readers:claude-session", mirror)

    def test_the_block_is_the_components_rendering_not_this_scripts_prose(self):
        self.through_answer()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertIn(doc["rendered"]["text"].strip(), build_doc)

    def test_a_second_record_over_a_committed_receipt_changes_nothing(self):
        self.through_answer()
        self.record()
        before = testlib.read_text(os.path.join(self.workspace, DOC))
        log_before = read_log(self.workspace)
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "completed")
        self.assertEqual(testlib.read_text(os.path.join(self.workspace, DOC)), before)
        self.assertEqual(read_log(self.workspace), log_before)


class ARefusalTheComponentReturnedIsDefinitive(TransactionCase):
    def test_a_conflict_on_the_findings_append_stops_and_is_never_retried(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="fail",
                      exit=7, error="conflict", reason="injected: the head moved")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "recording_failed")
        self.assertIn("injected: the head moved", json.dumps(doc))
        self.assertNothingRaised()
        self.assertNotIn("### 2026-09-21", testlib.read_text(os.path.join(self.workspace, DOC)))

        block = self.receipt()["appends"]["findings"]
        self.assertEqual(block["outcome"], "refused")
        self.assertEqual(block["refused"]["exit_code"], 7)
        self.assertEqual(block["refused"]["error"], "conflict")

        shimlib.disarm(self.fault)
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed",
                         "a refusal the component returned is never retried")
        self.assertNothingRaised("the retry that must not happen would have written here")
        self.assertNothingCleared()

    def test_a_validation_refusal_stops_with_the_components_own_sentence(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="fail",
                      exit=4, error="invalid", reason="injected: the event failed the schema")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        self.assertIn("injected: the event failed the schema", json.dumps(doc))
        self.assertNothingRaised()


class AnUnknownOutcomeIsSettledAgainstTheReceiptsHead(TransactionCase):
    def test_a_kill_before_the_append_lands_appends_once_on_the_next_pass(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="kill_before")
        code, doc, err = self.record()
        self.assertNotEqual(code, 0)
        self.assertNothingRaised()
        block = self.receipt()["appends"]["findings"]
        self.assertEqual(block["outcome"], "unknown")
        self.assertTrue(block["expected_head"])

        shimlib.disarm(self.fault)
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed")
        raised = [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]
        self.assertEqual(len(raised), 1, "appended exactly once")
        self.assertNothingCleared()

    def test_a_kill_after_the_append_lands_recovers_without_a_duplicate(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="kill_after")
        code, doc, err = self.record()
        self.assertNotEqual(code, 0)
        landed = [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]
        self.assertEqual(len(landed), 1, "the component landed it before the kill")
        self.assertEqual(self.receipt()["appends"]["findings"]["outcome"], "unknown")

        shimlib.disarm(self.fault)
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed")
        raised = [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]
        self.assertEqual(len(raised), 1, "no duplicate event")
        self.assertEqual(doc["recovered"], ["findings"])
        self.assertNothingCleared()

    def test_a_head_that_moved_under_an_unknown_outcome_is_a_conflict_not_a_fresh_head(self):
        """Revision 7: settle against the head the RECEIPT names, never one read afresh."""
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="kill_before")
        self.record()
        shimlib.disarm(self.fault)
        # a rival writer moves the head while this run is between passes
        self.rival_append()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "recording_failed", json.dumps(doc))
        raised = [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]
        self.assertEqual(raised, [], "nothing was appended against the rival's head")

    def rival_append(self):
        """A real second writer appends a card_observed through the real CLI."""
        events = [{
            "v": 1, "kind": "card_observed", "at": "2026-09-21T00:00:00Z", "ledger_doc": DOC,
            "slice": self.SLICE, "value": "built", "card": "built",
            "actor": {"station": "rival", "run_id": "rival-run", "harness": None},
            "origin": {"kind": "native"}, "source": {"known": False},
        }]
        path = os.path.join(self.dir, "rival-events.json")
        testlib.write_json(path, events)
        head = self.head()
        proc = subprocess.run(
            [testlib.GEN_PYTHON, os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py"),
             "append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
             "--expect-head", head],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")

    def head(self):
        proc = subprocess.run(
            [testlib.GEN_PYTHON, os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py"),
             "verify", "--workspace", self.workspace, "--doc", DOC],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
        return json.loads(proc.stdout.decode("utf-8"))["head"]


class ARivalWriterBetweenTwoPhasesIsANamedConflict(AnUnknownOutcomeIsSettledAgainstTheReceiptsHead):
    def test_an_event_appended_between_request_and_record_stops_before_any_append(self):
        self.through_answer()
        self.rival_append()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertIn(doc["status"], ("recording_failed", "stopped"))
        self.assertEqual(doc["stop_reason_code"], "log_moved_between_phases", json.dumps(doc))
        raised = [e for e in read_log(self.workspace) if e["kind"] == "finding_raised"]
        self.assertEqual(raised, [])
        self.assertNotIn("### 2026-09-21", testlib.read_text(os.path.join(self.workspace, DOC)))


class AFailedReadIsAStopNeverAnEmptySet(TransactionCase):
    def test_a_failed_events_read_while_settling_stops_and_appends_nothing(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="kill_before")
        self.record()
        shimlib.disarm(self.fault)
        shimlib.fault(self.fault, command="events", action="fail", exit=7, error="conflict",
                      reason="injected: the log could not be walked")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertIn(doc["status"], ("recording_failed", "stopped"))
        self.assertIn("injected: the log could not be walked", json.dumps(doc))
        self.assertNothingRaised("a failed read never stood in for an empty history")

    def test_a_failed_verify_before_the_transaction_stops(self):
        self.through_answer()
        shimlib.fault(self.fault, command="verify", action="fail", exit=7, error="conflict",
                      reason="injected: the chain is broken")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertIn("injected: the chain is broken", json.dumps(doc))


class TheImporterLevelsTheLogAndItsSignalsStop(TransactionCase):
    """CR-1, and amendment A3 item 3: stop on ANY importer signal, never trust its silence."""

    def test_a_hand_written_record_is_imported_before_the_run_reads_state(self):
        doc_path = os.path.join(self.workspace, DOC)
        text = testlib.read_text(doc_path)
        text = text.replace("## Punch list\n",
                            "## Punch list\n\n### 2026-09-20 — review: D\n"
                            "- MINOR · src/signpost/render.py:3 · the width is a bare "
                            "constant · a second caller would repeat it · D\n")
        with open(doc_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.through_answer()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed", json.dumps(doc))
        events = read_log(self.workspace)
        legacy = [e for e in events if e.get("origin", {}).get("kind") == "legacy"]
        self.assertTrue(legacy, "the hand-written record was imported, never missed")
        self.assertNothingCleared()

    def plant(self, block):
        doc_path = os.path.join(self.workspace, DOC)
        text = testlib.read_text(doc_path).replace("## Punch list\n", "## Punch list\n\n" + block)
        with open(doc_path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def scope_after(self, block):
        """The stop fires at the FIRST phase that reads the document's records, which is `scope`
        (CR-1: a dry run for a read-only command). Nothing is written at any phase, and the run
        never reaches the reviewer."""
        self.plant(block)
        code, doc, err = self.phase(["check-input", self.input_path])
        self.assertEqual(code, 0, err or json.dumps(doc))
        return self.phase(["scope", "--run-dir", self.run_dir])

    def test_an_ambiguous_document_stops_the_run(self):
        code, doc, err = self.scope_after(
            "### 2026-09-20 — recheck: D\n"
            "- MAJOR · src/signpost/pad.py:6 · (nothing raised this) · fixed · ran it\n")
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "missing_input")
        self.assertEqual(doc["stop_reason_code"], "importer_ambiguous", json.dumps(doc))
        self.assertEqual(read_log(self.workspace), [],
                         "an ambiguous document stops the import, which writes nothing at all")

    def test_an_unparsed_line_under_a_record_heading_stops_the_run(self):
        code, doc, err = self.scope_after(
            "### 2026-09-20 — review: D\n"
            "- this line fits no shape the reader accepts at all\n")
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["stop_reason_code"], "legacy_unparsed", json.dumps(doc))
        self.assertIn("reports the COUNT and not the line numbers", doc["stop_reason"],
                      "the reason says interface version 1 gives the count, never the lines")
        self.assertEqual(read_log(self.workspace), [])


class TheRefusedAnswerIsNeverRecorded(TransactionCase):
    CASE = "S2-03-no-evidence-kind"
    SLICE = "E"

    def test_an_answer_invalid_refusal_records_nothing(self):
        code, doc, err = self.through_answer()
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "stopped")
        self.assertEqual(doc["refusal_reason"], "answer_invalid")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertNothingRaised()
        self.assertEqual(testlib.project_status(self.workspace).strip(), "")


if __name__ == "__main__":
    unittest.main()
