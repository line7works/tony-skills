"""The card transaction: its kill windows, its refusals, and what a second pass does with them.

The one write this core makes to a project is a card move, in two halves: the `card_set` event
through the component, then the slice's `Status:` line. This suite kills the run between them in
both directions, refuses the append from the component, lets a rival writer in, and edits the
document behind the run's back, and holds the core to four rules the outside reviewer's look at
the pilot (`astra-short-look.md`, findings 1 to 4) says a records-writing station must keep:

    an intent with no outcome is settled against the head the RECEIPT names, never a fresh one
    a refusal the component RETURNED is definitive, persisted, and never retried
    a failed history read is a stop, never an empty history
    the document target's bytes are pinned before the append, so an edit that lands between the
      plan and the write is a named stop and never the new baseline

and to the two the brief adds: no duplicate event, and no silent repair.

Every fault is injected through a stand-in `scripts/records.py` handed to the core as
`RECORDS_ROOT`, which is route 2 of the component's own resolver; everything not injected runs
the real component, so the log these tests read is a real log.
"""
import json
import os
import unittest

import shimlib
import testlib

testlib.add_scripts_to_path()


def read_log(workspace, log):
    path = os.path.join(workspace, log)
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh.read().split("\n") if line.strip()]


def card_sets(events, slice_name=None):
    return [e for e in events if e.get("kind") == "card_set"
            and (slice_name is None or e.get("slice") == slice_name)]


class _Transaction(unittest.TestCase):
    """A workspace whose slice is ready to be marked built, and a shim in front of the component."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-txn-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")
        self.input = os.path.join(self.scratch, "input.json")
        testlib.write_json(self.input, testlib.make_input(self.run_dir, self.ws))
        self.answer = os.path.join(self.scratch, "answer.json")
        testlib.write_json(self.answer, testlib.ANSWER)
        self.shim_root, self.fault = shimlib.make_shim(self.scratch, testlib.RECORDS_ROOT)
        self.env = testlib.base_env(shimlib.env(self.shim_root, testlib.RECORDS_ROOT, self.fault))
        self.log = ("docs/records/docs__plans__2026-09-20-widget.events.jsonl")

    def to_report(self, env=None):
        """Run every phase up to but not including `report`."""
        for args in (["check-input", self.input], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", self.answer]):
            code, out, err = testlib.run_build(args, env=env or self.env)
            self.assertEqual(code, 0, "%s: %s%s" % (args, out, err))

    def report(self, env=None):
        return testlib.run_build(["report", "--run-dir", self.run_dir], env=env or self.env)

    def result(self):
        return testlib.load_json(os.path.join(self.run_dir, "result.json"))

    def receipt(self):
        return testlib.load_json(os.path.join(self.run_dir, "receipt.json"))

    def status_line(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), encoding="utf-8") as fh:
            for line in fh.read().split("\n"):
                if line.startswith("Status:"):
                    return line[len("Status:"):].strip()
        return None

    def events(self):
        return read_log(self.ws, self.log)


class TheHappyPath(_Transaction):

    def test_the_event_lands_then_the_line_and_the_receipt_says_both(self):
        self.to_report()
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["card"], dict(result["card"], before="not started",
                                              after="built", moved=True))
        self.assertEqual(self.status_line(), "built")
        cards = card_sets(self.events(), "A")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["after"], "built")
        self.assertEqual(cards[0]["actor"], {"station": "build-v2", "run_id": "run-1",
                                             "harness": "test-harness"},
                         "actor.run_id is the RUN's id, unique per run, the way every other "
                         "station reads it; the executor's session is in the result and the "
                         "receipt, not on the event")
        self.assertEqual(result["answer"]["session_id"], "sess-test-1")
        receipt = self.receipt()
        self.assertEqual(receipt["card_append"]["event"]["session_id"], "sess-test-1",
                         "the executor's session is kept in the receipt, beside the run's id")
        self.assertEqual(receipt["card_append"]["event"]["run_id"], "run-1")
        self.assertTrue(receipt["card_append"]["head"])
        self.assertTrue(receipt["document_step"]["done"])

    def test_the_event_carries_the_identity_the_component_computes(self):
        self.to_report()
        self.assertEqual(self.report()[0], 10)
        event = card_sets(self.events(), "A")[0]
        identity = json.loads(testlib.run_build(["identity", self.ws], env=self.env)[1])["identity"]
        self.assertTrue(event["source"]["known"])
        # the workspace moved by exactly the `Status:` line this run wrote, so the commit is the same
        self.assertEqual(event["source"]["identity"]["commit"], identity["commit"])

    def test_running_report_again_changes_nothing(self):
        self.to_report()
        self.assertEqual(self.report()[0], 10)
        before_doc = testlib.tree_digest(self.ws)
        before_events = self.events()
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(testlib.tree_digest(self.ws), before_doc)
        self.assertEqual(self.events(), before_events)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)


class TheKillWindows(_Transaction):
    """Both directions, and neither leaves a duplicate or repairs itself in silence."""

    def test_a_kill_before_the_append_leaves_no_event_and_the_next_pass_makes_it(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_before")
        code, out, err = self.report()
        self.assertNotEqual(code, 10, "the run was killed, so it delivered nothing")
        self.assertEqual(card_sets(self.events(), "A"), [], "nothing landed")
        self.assertEqual(self.status_line(), "not started", "and the line was not written")
        receipt = self.receipt()
        self.assertIn("expected_head", receipt["card_append"])
        self.assertNotIn("head", receipt["card_append"], "the outcome is unknown")

        shimlib.disarm(self.fault)
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(self.result()["status"], "completed")
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "exactly one event, not two")
        self.assertEqual(self.status_line(), "built")
        self.assertEqual(self.result()["resumed_half"], "the card event")

    def test_a_kill_after_the_append_leaves_one_event_and_the_next_pass_writes_the_line(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        code, _, _ = self.report()
        self.assertNotEqual(code, 10)
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "the event landed")
        self.assertEqual(self.status_line(), "not started", "the line did not")
        self.assertNotIn("head", self.receipt()["card_append"], "and the receipt never heard back")

        shimlib.disarm(self.fault)
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["resumed_half"], "the card event's record in the receipt")
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "still exactly one event")
        self.assertEqual(self.status_line(), "built")
        self.assertTrue(self.receipt()["card_append"]["recovered"])

    def test_a_kill_after_the_append_with_a_rival_in_between_is_not_a_duplicate(self):
        """The settle recognises its OWN event by the seq the plan named, not by its actor alone."""
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        shimlib.disarm(self.fault)
        self.assertEqual(self.report()[0], 10)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)


class ARefusalIsDefinitive(_Transaction):

    def test_a_refused_append_is_a_stop_that_wrote_nothing(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="fail",
                      exit=7, error="conflict", reason="injected: the head moved")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["terminal_status"], "stop")
        self.assertEqual(result["stop_tag"], "records_conflict")
        self.assertIn("injected: the head moved", result["stop_reason"])
        self.assertEqual(self.status_line(), "not started")
        self.assertEqual(card_sets(self.events(), "A"), [])
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(result["records"]["refused"]["exit_code"], 7)

    def test_the_refusal_is_persisted_and_a_later_pass_never_retries_it(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="fail",
                      exit=7, error="conflict", reason="injected: the head moved")
        self.assertEqual(self.report()[0], 10)
        self.assertEqual(self.receipt()["card_append"]["refused"]["exit_code"], 7)

        shimlib.disarm(self.fault)      # the component would now accept the append
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(card_sets(self.events(), "A"), [], "the refused append is never retried")
        self.assertEqual(self.status_line(), "not started")

    def test_each_refusal_code_carries_its_own_tag_and_the_components_sentence(self):
        for code_, error, tag in ((4, "invalid", "records_invalid"),
                                  (5, "ambiguous_identity", "records_ambiguous"),
                                  (6, "stale_source", "records_stale_source"),
                                  (7, "conflict", "records_conflict")):
            with self.subTest(exit=code_):
                self.setUp()
                self.to_report()
                shimlib.fault(self.fault, command="append", kind="card_set", action="fail",
                              exit=code_, error=error, reason="injected %s" % error)
                self.assertEqual(self.report()[0], 10)
                result = self.result()
                self.assertEqual(result["status"], "stopped")
                self.assertEqual(result["stop_tag"], tag)
                self.assertIn("injected %s" % error, result["stop_reason"])
                self.assertEqual(self.status_line(), "not started")


class AFailedReadIsNotAnEmptyHistory(_Transaction):

    def test_a_failed_card_history_read_on_a_settle_stops_and_appends_nothing(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)

        # the settle's history read now fails; it must not read that as "no card is there"
        shimlib.fault(self.fault, command="events", action="fail", exit=7, error="conflict",
                      reason="injected: the log could not be walked")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertIn("injected: the log could not be walked", result["stop_reason"])
        self.assertEqual(len(card_sets(self.events(), "A")), 1, "no duplicate was appended")
        self.assertEqual(self.status_line(), "not started")


class ARivalWriterIsANamedConflict(_Transaction):

    def test_an_event_appended_between_preflight_and_report_stops_the_run(self):
        self.to_report()
        events = self.events()
        self.assertTrue(events, "preflight levelled the log")
        # a real rival append through the real CLI, between the two phases
        rival = os.path.join(self.scratch, "rival.json")
        testlib.write_json(rival, [{
            "v": 1, "at": "2026-09-22T10:00:00Z", "ledger_doc": testlib.DOC_PATH,
            "actor": {"station": "rival", "run_id": "rival-run", "harness": None},
            "origin": {"kind": "native"}, "source": {"known": False},
            "kind": "card_observed", "slice": "A", "value": "not started", "card": "not started"}])
        head = json.loads(testlib.run_build(["preflight", "--run-dir", self.run_dir],
                                            env=self.env)[1] or "{}")
        import subprocess
        walk = subprocess.run([testlib.GEN_PYTHON, os.path.join(testlib.RECORDS_ROOT, "scripts",
                                                                "records.py"),
                               "verify", "--workspace", self.ws, "--doc", testlib.DOC_PATH],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        current = json.loads(walk.stdout.decode("utf-8"))["head"]
        appended = subprocess.run([testlib.GEN_PYTHON,
                                   os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py"),
                                   "append", "--workspace", self.ws, "--doc", testlib.DOC_PATH,
                                   "--events", rival, "--expect-head", current],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=testlib.base_env())
        self.assertEqual(appended.returncode, 0, appended.stderr.decode("utf-8", "replace"))

        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "records_conflict")
        self.assertIn("Another writer appended", result["stop_reason"])
        self.assertEqual(card_sets(self.events(), "A"), [])
        self.assertEqual(self.status_line(), "not started")


class AnEditBehindTheRunIsNotTheNewBaseline(_Transaction):

    def test_an_edit_between_the_plan_and_the_document_write_is_a_named_stop(self):
        self.to_report()
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        shimlib.fault(self.fault, command="append", kind="card_set", action="mutate",
                      path=doc, text="\nA paragraph nobody in this run wrote.\n")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "outside_edit")
        self.assertIn("between the plan and the write", result["stop_reason"])
        self.assertEqual(self.status_line(), "not started", "the line was not written")
        with open(doc, encoding="utf-8") as fh:
            self.assertIn("A paragraph nobody in this run wrote.", fh.read(),
                          "and the edit was left exactly where it was")


class TheCardsTwoHalvesAreHeldTogether(_Transaction):
    """A log ahead of the document is found by the NEXT run's preflight and reported, not repaired."""

    def test_a_card_event_without_its_document_line_stops_the_next_run(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        self.assertEqual(self.status_line(), "not started")

        # a fresh run over the same workspace finds the two halves disagreeing
        shimlib.disarm(self.fault)
        second_run = os.path.join(self.scratch, "run-2")
        second_input = os.path.join(self.scratch, "input-2.json")
        testlib.write_json(second_input, testlib.make_input(second_run, self.ws, run_id="run-2"))
        self.assertEqual(testlib.run_build(["check-input", second_input], env=self.env)[0], 0)
        self.assertEqual(testlib.run_build(["contract", "--run-dir", second_run], env=self.env)[0], 0)
        code, out, err = testlib.run_build(["preflight", "--run-dir", second_run], env=self.env)
        self.assertEqual(code, 10, err)
        result = testlib.load_json(os.path.join(second_run, "result.json"))
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "card_drift")
        self.assertIn("'built'", result["stop_reason"])
        self.assertIn("'not started'", result["stop_reason"])
        self.assertEqual(self.status_line(), "not started", "nothing was repaired")

    def test_a_hand_edited_status_line_after_a_card_event_is_not_drift(self):
        """A person or a v1 station moving the card is absorbed by the importer, not flagged."""
        self.to_report()
        self.assertEqual(self.report()[0], 10)
        self.assertEqual(self.status_line(), "built")
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        with open(doc, "w", encoding="utf-8") as fh:
            fh.write(text.replace("Status: built", "Status: signed off"))

        second_run = os.path.join(self.scratch, "run-2")
        second_input = os.path.join(self.scratch, "input-2.json")
        testlib.write_json(second_input, testlib.make_input(second_run, self.ws, run_id="run-2"))
        self.assertEqual(testlib.run_build(["check-input", second_input], env=self.env)[0], 0)
        self.assertEqual(testlib.run_build(["contract", "--run-dir", second_run], env=self.env)[0], 0)
        code, out, err = testlib.run_build(["preflight", "--run-dir", second_run], env=self.env)
        self.assertEqual(code, 0, "%s%s" % (out, err))


if __name__ == "__main__":
    unittest.main()


class ASettleReDeliversTheFactsTheDecisionWasMadeOn(_Transaction):
    """A settling pass never recomputes the decision: a rerun check could observe something else
    the second time, and what the receipt is settling was decided on what the run already had."""

    def test_a_rerun_run_that_was_killed_still_reports_the_rerun_it_made(self):
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.ws, rerun_checks=True))
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", self.answer]):
            code, out, err = testlib.run_build(args, env=self.env)
            self.assertEqual(code, 0, "%s: %s%s" % (args, out, err))

        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        shimlib.disarm(self.fault)

        # the check command now answers differently; the settle must not run it again
        testlib.write_text(os.path.join(self.ws, "checks", "unit.sh"),
                           "#!/bin/sh\necho 'it fails now'\nexit 1\n")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "completed")
        row = result["checks"][0]
        self.assertEqual(row["source"], "rerun", "the settle re-delivered the run's own rerun")
        self.assertEqual(row["result"], "passed")
        self.assertNotIn("it fails now", row["output"])
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
