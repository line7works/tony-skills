"""E11 round 2, batch A: the readers and the records (R5's check, R6, R2, R1).

Every test here fails against `4351654` — the repair branch's fix-8 tip — and passes after.
Each names the package item and the finding it closes. Standard library only, Python 3.9,
run from any directory.
"""
import json
import os
import subprocess
import sys
import threading
import unittest

import testlib
from testlib import RunnerCase, cli, parse_stdout, runner


class R6F5Method(unittest.TestCase):
    """R6: the outbound scenario is a deterministic POLICY refusal, written down."""

    @staticmethod
    def plugin():
        return testlib.PLUGIN

    def contract(self):
        path = os.path.join(self.plugin(), "skills", "recheck-v2", "references",
                            "pilot-contract.md")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_the_contract_says_method_records_the_attempt(self):
        text = self.contract()
        self.assertIn("`method` records what the verifier ATTEMPTED", text)
        self.assertIn("the method stays `executed`", text)

    def test_the_contract_names_the_policy_refusal_and_keeps_the_item_open(self):
        text = self.contract()
        self.assertIn("deterministic POLICY REFUSAL", text)
        self.assertIn("without the named service observation", text)
        self.assertIn("a declined attempt is never a static clearance", text)

    def test_the_fixture_declares_the_refusal_and_the_required_observation(self):
        path = os.path.join(self.plugin(), "evals", "fixtures", "F5-blocked-execution",
                            "build.py")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn('"outbound_refusal": "policy"', text)
        self.assertIn('"required_service_observation"', text)
        self.assertIn("stays open without the named service observation", text)
        self.assertIn("declined by policy", text)


class R2Readers(RunnerCase):
    """R2: the measurements, repaired without changing any past session outcome."""

    def test_a_codex_file_uri_workdir_resolves_to_a_path(self):
        self.assertEqual(runner.local_path("file:///Users/nobody/ws"), "/Users/nobody/ws")
        self.assertEqual(runner.local_path("file://localhost/Users/nobody/ws"),
                         "/Users/nobody/ws")
        self.assertEqual(runner.local_path("/Users/nobody/ws"), "/Users/nobody/ws")
        self.assertEqual(
            runner.codex_call_workdir({"cwd": "file:///Users/nobody/ws"}),
            "/Users/nobody/ws")

    def test_a_here_document_body_is_data_not_commands(self):
        text = "\n".join(["python3 - <<'EOF'",
                          "import os",
                          "os.system('rm -rf /')",
                          "EOF",
                          "echo done"])
        heads = [argv[0] for argv in runner.simple_commands(text) if argv]
        self.assertEqual(heads, ["python3", "echo"])
        self.assertNotIn("os.system('rm", heads)

    def test_the_four_call_outcomes_are_told_apart(self):
        self.assertEqual(runner.call_outcome("completed", text="ok"), "completed")
        self.assertEqual(runner.call_outcome("error", text="exit 1: boom"), "error")
        self.assertEqual(
            runner.call_outcome("error",
                                text="permission requested: external_directory; auto-rejecting"),
            "refused")
        self.assertEqual(runner.call_outcome("error", metadata={"interrupted": True}),
                         "interrupted")
        self.assertEqual(runner.call_outcome(None), "unknown")

    def test_an_opencode_error_without_a_refusal_marker_is_an_error(self):
        """read2: 'the runner incorrectly maps every OpenCode error to refused'."""
        self.assertEqual(runner.call_outcome("error", text="ENOSPC: no space left"), "error")

    def test_the_user_request_is_never_read_as_the_reply(self):
        harness = os.path.join(self.scratch, "opencode-harness")
        runner.ensure_dir(harness)
        runner.write_json(os.path.join(harness, "session.json"), {"records": [
            {"parts": [{"data": {"type": "text", "text": "the user's own request"}}]},
            {"parts": [{"data": {"type": "step-start"}},
                       {"data": {"type": "reasoning", "text": "thinking"}},
                       {"data": {"type": "tool"}},
                       {"data": {"type": "step-finish"}}]},
        ]})
        setup = runner.setup_for(runner.Campaign(self.campaign), self.plan_document,
                                 self.setups[0])
        text, source = runner.harness_reply(setup, harness)
        self.assertEqual(text, "")
        self.assertIsNone(source)

    def test_an_assistant_text_part_is_still_the_reply(self):
        harness = os.path.join(self.scratch, "opencode-answered")
        runner.ensure_dir(harness)
        runner.write_json(os.path.join(harness, "session.json"), {"records": [
            {"parts": [{"data": {"type": "text", "text": "the user's own request"}}]},
            {"info": {"role": "assistant"},
             "parts": [{"data": {"type": "text", "text": "RECHECK: the answer"}}]},
        ]})
        setup = runner.setup_for(runner.Campaign(self.campaign), self.plan_document,
                                 self.setups[0])
        text, _source = runner.harness_reply(setup, harness)
        self.assertEqual(text, "RECHECK: the answer")

    def test_a_reply_whose_disposition_contradicts_the_result_fails(self):
        record = os.path.join(self.scratch, "contradicting")
        runner.ensure_dir(record)
        result = {"status": "completed",
                  "items": [{"location": {"file": "src/x.py", "line": 7},
                             "disposition": "not_fixed", "reason": "reproduces"}]}
        lines = ["RECHECK: slice A", "Reason: one item", "Output",
                 "- src/x.py:7 · fixed · it is done"]
        runner.write_text(os.path.join(record, "reply.md"), "\n".join(lines) + "\n")
        runner.write_text(os.path.join(record, "chat.md"), "")
        interop = runner._interop(result, record)
        self.assertFalse(interop["dispositions_agree"])
        self.assertFalse(interop["ok"])

    def test_not_fixed_is_never_read_as_fixed(self):
        """The control room's send-back on batch A: 27 attempts flipped on this.

        The reply grammar writes the two-word form with a space; the first parser tested
        `"fixed" in line`, so every "… · not fixed (missed_case) · …" line read as `fixed`
        and contradicted a `not_fixed` record.
        """
        self.assertEqual(
            runner._reply_disposition(
                "- src/widget/export.py:11 \u00b7 not fixed (missed_case) \u00b7 executed it"),
            "not_fixed")
        self.assertEqual(
            runner._reply_disposition("- src/x.py:7 \u00b7 fixed \u00b7 it no longer holds"),
            "fixed")
        self.assertEqual(
            runner._reply_disposition(
                "- src/x.py:7 \u00b7 NOT FIXED (verification blocked) \u00b7 declined"),
            "not_fixed")

    def test_a_not_fixed_reply_agrees_with_a_not_fixed_record(self):
        record = os.path.join(self.scratch, "not-fixed-agreeing")
        runner.ensure_dir(record)
        result = {"status": "completed",
                  "items": [{"location": {"file": "src/widget/export.py", "line": 11},
                             "disposition": "not_fixed", "reason": "missed_case"}]}
        lines = ["RECHECK: slice A", "Reason: one item", "Output",
                 "- src/widget/export.py:11 \u00b7 not fixed (missed_case) \u00b7 executed it"]
        runner.write_text(os.path.join(record, "reply.md"), "\n".join(lines) + "\n")
        runner.write_text(os.path.join(record, "chat.md"), "")
        interop = runner._interop(result, record)
        self.assertEqual(interop["item_lines"][0]["disposition_in_the_reply"], "not_fixed")
        self.assertTrue(interop["dispositions_agree"])

    def test_a_fixed_reply_against_a_not_fixed_record_still_fails(self):
        record = os.path.join(self.scratch, "really-contradicting")
        runner.ensure_dir(record)
        result = {"status": "completed",
                  "items": [{"location": {"file": "src/widget/export.py", "line": 11},
                             "disposition": "not_fixed", "reason": "missed_case"}]}
        lines = ["RECHECK: slice A", "Reason: one item", "Output",
                 "- src/widget/export.py:11 \u00b7 fixed \u00b7 it no longer holds"]
        runner.write_text(os.path.join(record, "reply.md"), "\n".join(lines) + "\n")
        runner.write_text(os.path.join(record, "chat.md"), "")
        interop = runner._interop(result, record)
        self.assertEqual(interop["item_lines"][0]["disposition_in_the_reply"], "fixed")
        self.assertFalse(interop["dispositions_agree"])

    def test_an_agreeing_reply_still_passes_that_check(self):
        record = os.path.join(self.scratch, "agreeing")
        runner.ensure_dir(record)
        result = {"status": "completed",
                  "items": [{"location": {"file": "src/x.py", "line": 7},
                             "disposition": "not_fixed", "reason": "reproduces"}]}
        lines = ["RECHECK: slice A", "Reason: one item", "Output",
                 "- src/x.py:7 · not_fixed · it still reproduces"]
        runner.write_text(os.path.join(record, "reply.md"), "\n".join(lines) + "\n")
        runner.write_text(os.path.join(record, "chat.md"), "")
        self.assertTrue(runner._interop(result, record)["dispositions_agree"])


class R1CaptureAndSchedule(RunnerCase):
    """R1: recheck8's two NEW MAJORs, the selector and the regrade command."""

    setups = ("claude-code", "codex")

    # ---- G-ID: valid dotted call ids
    def capture_dir(self):
        capture = os.path.join(self.scratch, "captures")
        runner.ensure_dir(capture)
        names = ["launch-run.v1-verify.json", "run.v1-verify.rollout.jsonl",
                 "run.v1-verify-2.events.jsonl", "launch-x.json",
                 "launch-x.record-call-flags.json", "launch-x.trace.json",
                 "launch-x.session.json", "x.record-call-flags.trace.jsonl",
                 "x.record-call-flags.rollout.jsonl", "trace.jsonl", "transcript.jsonl",
                 "rollout.jsonl", "events.jsonl", "session.json", "trace.json"]
        for name in names:
            runner.write_text(os.path.join(capture, name), "{}\n")
        return capture

    def test_a_dotted_call_id_capture_is_selected_on_codex(self):
        selected = [os.path.basename(p)
                    for p in runner.capture_files(self.capture_dir(), "codex")]
        self.assertIn("run.v1-verify.rollout.jsonl", selected)
        self.assertIn("run.v1-verify-2.events.jsonl", selected)

    def test_a_dotted_call_id_capture_is_selected_on_opencode(self):
        selected = [os.path.basename(p)
                    for p in runner.capture_files(self.capture_dir(), "opencode-trace")]
        self.assertIn("launch-run.v1-verify.json", selected)

    def test_every_sidecar_is_still_rejected(self):
        capture = self.capture_dir()
        strays = ["launch-x.record-call-flags.json", "launch-x.trace.json",
                  "launch-x.session.json", "x.record-call-flags.trace.jsonl",
                  "x.record-call-flags.rollout.jsonl"]
        for shape in ("opencode-trace", "opencode-session", "claude-code", "codex"):
            selected = [os.path.basename(p) for p in runner.capture_files(capture, shape)]
            for stray in strays:
                self.assertNotIn(stray, selected, shape)

    def test_the_call_id_grammar_matches_the_cores_own_constructor(self):
        sys.path.insert(0, os.path.join(testlib.PLUGIN, "skills", "recheck-v2", "scripts"))
        from recheck_core import verifier as vmod
        for run_id in ("run", "run.v1", "F5-01-outbound-required-run"):
            for k in (1, 2):
                self.assertTrue(runner._is_call_id(vmod.call_id_for(run_id, k)),
                                vmod.call_id_for(run_id, k))

    # ---- Q-S-L: fewer worker slots than lanes
    def scheduler(self, lanes):
        import argparse
        campaign = runner.Campaign(self.campaign)
        runner.ensure_dir(campaign.trials)
        comparison = "codex-F1-01-fixed-clean-available-r1"
        continuation = "cont-codex-F3-02-mixed-two-items-compaction-r1"
        for tid, kind in ((comparison, "comparison"),):
            directory = campaign.trial_dir(tid)
            runner.ensure_dir(directory)
            runner.write_json(os.path.join(directory, "command.json"),
                              {"setup": "codex", "condition": "available", "kind": kind,
                               "status": "complete"})
            runner.write_json(os.path.join(directory, "result.json"), {})
        plan = {"order": {"codex": [comparison]},
                "continuation_order": {"codex": [continuation]},
                "consumer_order": {"claude-code": ["consumer-codex-to-claude-code-r1"]}}
        selected = []

        def produce(one):
            directory = campaign.trial_dir(continuation)
            runner.ensure_dir(directory)
            runner.write_json(os.path.join(directory, "command.json"),
                              {"setup": "codex", "condition": "available",
                               "kind": "continuation:compaction", "status": "complete"})
            runner.write_json(os.path.join(directory, "result.json"), {})

        def consume(one):
            selected.append(runner.producer_record_for(campaign, plan, "codex")["trial"])

        args = argparse.Namespace(fake_launcher=None, compact_tokens=None, lanes=lanes,
                                  poll_interval=0.01)
        saved = (runner.require_preflight, runner.cache_routing_requests,
                 runner.do_continuation, runner.do_consumer, runner.lane_stopped)
        runner.require_preflight = lambda *a, **k: None
        runner.cache_routing_requests = lambda *a, **k: {}
        runner.do_continuation = produce
        runner.do_consumer = consume
        runner.lane_stopped = lambda *a, **k: None
        done = []

        def drive():
            try:
                runner._campaign_loop(campaign, plan, args)
            finally:
                done.append(True)

        worker = threading.Thread(target=drive, name="scheduler-under-test")
        worker.daemon = True
        worker.start()
        worker.join(20)
        try:
            self.assertTrue(done, "the campaign loop did not finish: the scheduler deadlocked")
        finally:
            (runner.require_preflight, runner.cache_routing_requests,
             runner.do_continuation, runner.do_consumer, runner.lane_stopped) = saved
        return selected[0] if selected else None, continuation

    def test_one_slot_with_two_lanes_completes(self):
        """Her q_deadlock.py: `--lanes 1` used to hang forever."""
        chosen, continuation = self.scheduler(1)
        self.assertEqual(chosen, continuation)

    def test_the_same_record_is_selected_at_one_slot_and_at_two(self):
        one, continuation = self.scheduler(1)
        self.assertEqual(one, continuation)

    # ---- the read-only consumer regrade command
    def test_the_regrade_command_needs_a_revision(self):
        got = cli(["consumer", "--campaign", self.campaign, "--regrade", "--all"])
        self.assertEqual(got.returncode, 2, got.stdout[-400:])
        self.assertIn("--revision", got.stderr)

    def test_the_regrade_command_writes_beside_the_original(self):
        campaign = runner.Campaign(self.campaign)
        tid = "consumer-claude-code-to-codex-r1"
        record = campaign.trial_dir(tid)
        producer = os.path.join(self.scratch, "producer")
        runner.ensure_dir(os.path.join(producer, "workspace"))
        runner.write_json(os.path.join(producer, "result.json"), {"items": [], "cards": []})
        runner.write_json(os.path.join(producer, "run", "checkpoint.json"),
                          {"phase": "completed", "continuations": 0, "scope": {"items": []}})
        runner.write_json(os.path.join(producer, "command.json"),
                          {"setup": "claude-code", "condition": "available",
                           "kind": "comparison", "workspace": os.path.join(producer,
                                                                           "workspace")})
        pair = runner.stage_consumer_pair(
            campaign, {"record": producer, "trial": "p",
                       "command": {"workspace": os.path.join(producer, "workspace")}},
            os.path.join(self.scratch, "pair"))
        runner.write_json(os.path.join(pair["pair_dir"], "consumer.json"),
                          {"items": [], "cards": []})
        runner.ensure_dir(record)
        runner.write_json(os.path.join(record, "command.json"),
                          {"kind": "consumer", "pair": pair, "producer": "claude-code",
                           "producer_trial": "p", "producer_record": producer})
        original = os.path.join(record, "consumer-grade.json")
        runner.write_json(original, {"ok": False, "why": ["the original"]})
        before = runner.read_text(original)
        got = cli(["consumer", "--campaign", self.campaign, "--regrade", "--all",
                   "--revision", "e11-round2-1"])
        self.assertIn(got.returncode, (0, 1), got.stderr[-1200:])
        document = parse_stdout(got)
        self.assertEqual(document["revision"], "e11-round2-1")
        self.assertEqual(document["regraded"], 1)
        self.assertTrue(os.path.isfile(os.path.join(record,
                                                    "consumer-grade.e11-round2-1.json")))
        self.assertEqual(runner.read_text(original), before)
