"""E13 slice 1, the fix round: the outside reviewer's four MAJORs and the control room's finding.

M1  a committed document receipt still reconciles this run's card events (kill before and after
    the card append, and a refused card append as a named stop rather than exit 1).
M2  an edit made before the document plan exists never becomes the baseline (between the append
    and the render, and before an empty-plan resume writes anything).
M3  a definitive refusal of the append is persisted as non-resumable and never retried, and an
    unknown outcome keeps the receipt's expected head rather than adopting a newer one.
M4  a FAILED card-history read is not an empty history: the run stops before any append.
CR-F1 the head the run's open set was read against is pinned at `start`; a rival event past it is
    a named conflict stop before any append.
"""
import copy
import json
import os
import subprocess
import unittest

import shimlib
import testlib

testlib.add_scripts_to_path()
from recheck_core import records_client as rc  # noqa: E402

RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
DOC = "docs/plans/2026-09-18-widget-export.md"


class Base(unittest.TestCase):
    """One F1 case driven to `adjudicating` through a component root the test controls."""

    LANE = "F1-fixed-defect"
    CASE = "F1-01-fixed-clean"
    DISPOSITION = "fixed"
    SHIM = True

    def setUp(self):
        self.dir = testlib.make_scratch("e13-fix-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case(self.LANE, self.CASE, self.dir)
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.input = testlib.prepare_input(self.case)
        self.client = rc.open_client(records_root=RECORDS)
        self.env = {}
        if self.SHIM:
            self.shim, self.fault_path = shimlib.make_shim(self.dir, RECORDS)
            self.env = shimlib.env(self.shim, RECORDS, self.fault_path)

    # ---- driving ---------------------------------------------------------------------------

    def cli(self, args, hooks=None):
        return testlib.recheck(args, cwd=self.dir, hooks=hooks, env=dict(self.env))

    def fault(self, **config):
        shimlib.fault(self.fault_path, **config)

    def disarm(self):
        shimlib.disarm(self.fault_path)

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

    def doc_bytes(self, name=DOC):
        with open(os.path.join(self.workspace, name), "rb") as fh:
            return fh.read()

    def events(self, doc=DOC):
        return [row["event"] for row in self.client.events(self.workspace, doc)["results"]]

    def run_id(self):
        return testlib.load_json(os.path.join(self.run_dir, "input.json"))["invocation"]["run_id"]

    def run_events(self, doc=DOC):
        rid = self.run_id()
        return [e for e in self.events(doc) if (e.get("actor") or {}).get("run_id") == rid]

    def cards(self, doc=DOC):
        return [e for e in self.run_events(doc) if e["kind"] == "card_set"]

    def receipt(self):
        return testlib.load_json(os.path.join(self.run_dir, "receipt.json"))

    def result(self, body):
        return testlib.load_json(body["result"])

    def log_card(self, name="A", doc=DOC):
        state = self.client.state(self.workspace, doc)
        for row in state["slices"]:
            if row["name"] == name:
                return row.get("card_observed") or "none"
        return "none"


# ---- M1: a committed document receipt still reconciles the card events -----------------------

class CardRecovery(Base):
    def test_a_kill_before_the_card_append_is_reconciled_by_resume(self):
        """Astra's `card_kill_before`: every document step landed, the card event never did."""
        self.to_adjudicated()
        self.fault(command="append", kind="card_set", action="kill_before")
        code, doc, err = self.record()
        self.assertEqual(code, -9, "the shim was meant to kill the pilot before the card append")
        self.assertIn(b"Status: signed off", self.doc_bytes(), "the document steps landed")
        self.assertEqual(self.cards(), [], "no card event landed")
        self.disarm()
        code, doc, err = self.resume()
        self.assertEqual(doc and doc["status"], "completed",
                         "a committed document receipt skipped the card recovery: %s" % err)
        result = self.result(doc)
        self.assertIn("card", (result.get("resumed_half") or ""),
                      "the result must name the missing half")
        self.assertEqual(len(self.cards()), 1, "the card event is appended exactly once")
        self.assertEqual(self.log_card(), "signed off", "the log must agree with the document")
        self.assertTrue(self.receipt()["card_append"].get("head"), "the receipt must record the card append")

    def test_a_kill_after_the_card_append_finalises_the_receipt_without_appending_again(self):
        """Astra's `card_kill_after`: the card event landed, its record in the receipt did not."""
        self.to_adjudicated()
        self.fault(command="append", kind="card_set", action="kill_after")
        code, doc, err = self.record()
        self.assertEqual(code, -9)
        self.assertEqual(len(self.cards()), 1, "the card append landed")
        self.assertIsNone(self.receipt()["card_append"].get("head"), "the receipt holds the intent only")
        self.disarm()
        code, doc, err = self.resume()
        self.assertEqual(doc and doc["status"], "completed", err)
        block = self.receipt()["card_append"]
        self.assertTrue(block.get("head"), "resume left card_append intent-only")
        self.assertTrue(block.get("recovered"), "a recovered block says so")
        self.assertTrue(block.get("seqs"), "the recovered block names the seqs the log holds")
        result = self.result(doc)
        self.assertIn("card", (result.get("resumed_half") or ""), "resumed_half was null")
        self.assertEqual(len(self.cards()), 1, "the card event was appended twice")

    def test_a_refused_card_append_is_a_named_stop_and_never_exit_1(self):
        """Astra's `card_fail`: a card-append refusal escaped as exit 1."""
        self.to_adjudicated()
        self.fault(command="append", kind="card_set", action="fail", exit=7, error="conflict",
                   reason="injected: the log is unavailable at append")
        code, doc, err = self.record()
        self.assertNotEqual(code, 1, "the refusal escaped as exit 1: %s" % err)
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed",
                         "a definitive refusal of the card append is a named stop")
        result = self.result(doc)
        self.assertIn("card", result["stop_reason"], "the stop names the half that is missing")
        self.assertEqual(self.cards(), [])

    def test_a_definitive_card_refusal_is_not_retried_by_resume(self):
        """M3's rule applied to the second append: a received conflict is non-resumable."""
        self.to_adjudicated()
        self.fault(command="append", kind="card_set", action="fail", exit=7)
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertTrue((self.receipt().get("card_append") or {}).get("refused"),
                        "the receipt must persist the refusal as non-resumable")
        self.disarm()
        code, doc, err = self.resume()
        self.assertNotEqual(doc and doc.get("status"), "completed",
                            "resume retried a definitive refusal")
        self.assertEqual(self.cards(), [], "resume appended after a definitive refusal")


# ---- M2: an edit before the document plan never becomes the baseline -------------------------

class PrePlanEdit(Base):
    def test_an_edit_between_the_append_and_the_render_stops_the_run(self):
        """Astra's `preplan-edit`: the document is edited after the append, before the plan."""
        self.to_adjudicated()
        self.fault(command="render", action="mutate", path=os.path.join(self.workspace, DOC),
                   text="\nManual edit between append and planning.\n")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed",
                         "an outside edit before the plan was accepted as the baseline")
        result = self.result(doc)
        self.assertIn("outside edit", result["stop_reason"])
        self.assertIn(b"Manual edit between append and planning.", self.doc_bytes(),
                      "the edit stands; the run wrote nothing over it")
        self.assertNotIn(b"recheck: Slice A", self.doc_bytes(), "a block was placed over an edited baseline")

    def test_an_edit_before_an_empty_plan_resume_stops_it(self):
        """Astra's `intent_manual_edit`: the append landed, the receipt shows the intent only, the
        document is edited, and the resume must not plan against the edited bytes."""
        self.to_adjudicated()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_AFTER_APPEND": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        with open(os.path.join(self.workspace, DOC), "a", encoding="utf-8") as fh:
            fh.write("\nManual edit in crash window.\n")
        before = self.doc_bytes()
        receipt_before = testlib.read_text(os.path.join(self.run_dir, "receipt.json"))
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertNotEqual(doc["status"], "completed", "the edited document became the baseline")
        self.assertEqual(doc["status"], "recording_failed")
        result = self.result(doc)
        self.assertIn("outside edit", result["stop_reason"])
        self.assertEqual(self.doc_bytes(), before, "the resume wrote over an outside edit")
        self.assertEqual(testlib.read_text(os.path.join(self.run_dir, "receipt.json")), receipt_before,
                         "the resume wrote the receipt after finding an outside edit")

    def test_a_post_plan_edit_still_refuses(self):
        """The control that already passed: once the plan exists, section 11's classification stands."""
        self.to_adjudicated()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_BEFORE_STEP": "1"})
        self.assertEqual(code, 10, err)
        with open(os.path.join(self.workspace, DOC), "a", encoding="utf-8") as fh:
            fh.write("\nManual edit after the plan.\n")
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")


# ---- M3: a definitive refusal is never retried ----------------------------------------------

class RefusedAppend(Base):
    SHIM = False

    def test_a_refused_append_is_persisted_non_resumable_and_never_retried(self):
        """The control room's M3 reproduction: the pilot sends a stale expected head, the component
        refuses with exit 7, and a plain resume must NOT complete against a newer head."""
        self.to_adjudicated()
        before = self.doc_bytes()
        code, doc, err = self.record(hooks={"RECHECK_TEST_RECORDS_STALE_HEAD": "1"})
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        self.assertEqual(self.run_events(), [])
        self.assertTrue((self.receipt().get("append") or {}).get("refused"),
                        "the received conflict must be persisted as non-resumable")
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertNotEqual(doc["status"], "completed", "resume retried a refused append")
        self.assertEqual(self.run_events(), [], "resume appended after a definitive refusal")
        self.assertEqual(self.doc_bytes(), before)


class RivalAppendBetweenReadAndAppend(Base):
    def test_a_rival_append_between_the_read_and_the_append_is_a_conflict(self):
        """Astra's `competing_head`, with the resume asked to finish it: the rival's event moved the
        head, so the run's own append is refused and the resume must not refresh the head."""
        self.to_adjudicated()
        self.fault(command="append", kind="disposition", action="compete")
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "recording_failed")
        self.assertEqual(self.run_events(), [])
        code, doc, err = self.resume()
        self.assertEqual(code, 10, err)
        self.assertNotEqual(doc["status"], "completed",
                            "resume adopted the newer head after a conflict")
        self.assertEqual(self.run_events(), [], "resume appended against a head it never read")


# ---- M4: a failed card-history read is not an empty history ----------------------------------

class TwoSlices(Base):
    """F1-01 with a second slice and a second finding, so the plan holds two status-line steps."""

    def to_adjudicated(self):
        code, doc, err = self.cli(["start", self.input])
        self.assertEqual(code, 0, err)
        first = copy.deepcopy(testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))["scope"]["checklist"][0])
        testlib.rmtree(self.run_dir)
        testlib.rmtree(os.path.join(self.workspace, "docs", "records"))
        path = os.path.join(self.workspace, DOC)
        text = testlib.read_text(path).replace("## Punch list", "## Slice B — second slice\nStatus: rejected\n\n## Punch list")
        text += ("\n### 2026-09-19 — review: Slice B\n- BLOCKER · src/widget/export.py:31 · "
                 "second CSV finding · run second scenario · Slice B\n")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                   GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        proc = subprocess.run(["git", "-C", self.workspace, "commit", "-q", "-a", "-m", "add slice B"],
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        second = copy.deepcopy(first)
        second["slice"] = "B"
        second["location"]["line"] = 31
        second["claim"] = "second CSV finding"
        second["failure_scenario"] = "run second scenario"
        second["record"]["heading"] = "### 2026-09-19 — review: Slice B"
        doc_in = testlib.load_json(self.input)
        doc_in["target"] = {"items": [first, second]}
        with open(self.input, "w", encoding="utf-8") as fh:
            json.dump(doc_in, fh, indent=2, ensure_ascii=False)
        return Base.to_adjudicated(self)


class CardHistoryRead(TwoSlices):
    def test_a_failed_card_history_read_stops_before_any_append(self):
        """The control room's M4 reproduction: `events --kind card_set` answers exit 7 during the
        resume. Today the pilot treats that as an empty history and appends slice A's card twice."""
        self.to_adjudicated()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_BEFORE_STEP": "3"})
        self.assertEqual(code, 10, err)
        before = sorted(e["slice"] for e in self.cards())
        self.assertEqual(before, ["A"], "the first status step's card landed: %s" % before)
        self.fault(command="events", query_kind="card_set", action="fail", exit=7,
                   reason="injected: the card history is unavailable")
        code, doc, err = self.resume()
        after = sorted(e["slice"] for e in self.cards())
        self.assertEqual(after, before, "a failed card-history read produced duplicate card events")
        self.assertNotEqual(doc and doc.get("status"), "completed",
                            "a failed card-history read was reported as a completed run")
        result = self.result(doc) if doc and doc.get("result") else {}
        self.assertIn("card history", (result.get("stop_reason") or ""),
                      "the stop must name the FAILED card-history read, not some later symptom")
        self.assertIn("injected: the card history is unavailable", (result.get("stop_reason") or ""),
                      "the component's own exit and explanation must be kept")

    def test_a_plain_resume_appends_the_remaining_card_exactly_once(self):
        """The control beside it: with the history readable, the resume owes slice B's card and
        appends it once, even though `card_append` already carries slice A's head."""
        self.to_adjudicated()
        code, doc, err = self.record(hooks={"RECHECK_TEST_FAIL_BEFORE_STEP": "3"})
        self.assertEqual(code, 10, err)
        self.assertEqual(sorted(e["slice"] for e in self.cards()), ["A"])
        code, doc, err = self.resume()
        self.assertEqual(doc and doc.get("status"), "completed", err)
        self.assertEqual(sorted(e["slice"] for e in self.cards()), ["A", "B"],
                         "the resume owed slice B's card event")


# ---- CR-F1: the head the open set was read against is pinned at `start` ----------------------

class RivalBetweenStartAndRecord(Base):
    SHIM = False

    def rival_card_set(self):
        """Append a rival `card_set` (slice A to `built`) through the real CLI, as another writer."""
        events = self.events()
        sample = events[-1]
        rival = {k: sample[k] for k in ("v", "at", "ledger_doc", "origin", "source") if k in sample}
        rival["origin"] = {"kind": "native"}
        rival.update(kind="card_set", slice="A", before="rejected", after="built",
                     actor={"station": "rival", "run_id": "rival-run", "harness": None})
        path = os.path.join(self.dir, "rival-events.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([rival], fh)
        head = self.client.verify(self.workspace, DOC)["head"]
        return self.client.append(self.workspace, DOC, [rival], head, self.dir)

    def test_a_rival_event_past_the_pinned_head_is_a_conflict_stop_before_any_append(self):
        self.to_adjudicated()
        self.rival_card_set()
        before = self.doc_bytes()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err)
        self.assertNotEqual(doc["status"], "completed",
                            "the run recorded over another writer's event")
        result = self.result(doc)
        self.assertIn("re-read the log and decide", result["stop_reason"].lower(),
                      "the stop must tell the user to re-read and decide (section 10)")
        self.assertEqual(self.doc_bytes(), before, "the document was written after a conflict")
        self.assertEqual(self.run_events(), [], "the run appended after a conflict")

    def test_the_checkpoint_pins_the_head_the_open_set_was_read_against(self):
        self.to_adjudicated()
        cp = testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))
        pin = cp.get("records_pin")
        self.assertIsNotNone(pin, "the checkpoint does not pin the head the open set was read against")
        self.assertEqual(pin["doc"], DOC)
        self.assertEqual(len(pin["head"]), 64)


if __name__ == "__main__":
    unittest.main()
