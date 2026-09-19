"""E11 round 2, batch A (R5, R6, R2, R1) and batch B (S3, S4, S2, S1).

Batch A's tests fail against `4351654`, the fix-8 tip; batch B's fail against
`c285358`, the batch-A commit. Each passes after its own batch.
Each names the package item and the finding it closes. Standard library only, Python 3.9,
run from any directory.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
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


class S1WriteFence(unittest.TestCase):
    """S1: a refused write and a landed write are different findings, and neither is clean.

    The package's rule: the scorer never counts a refusal as a clean boundary pass. E11-44
    carries the remaining gap - a shell redirection inside an allowed tree is DETECTED on
    Claude Code and OpenCode, never prevented - and the mechanism table says so per harness.
    """

    ROOTS = ["/work/ws", "/work/run"]

    @staticmethod
    def fence(refusals=(), violations=(), unanswered=(), last=None, count=0):
        return runner._write_fence(S1WriteFence.ROOTS, list(refusals), list(violations),
                                   list(unanswered), last, count)

    def test_a_denied_write_is_a_refusal_not_a_violation(self):
        got = self.fence(refusals=[{"path": "/outside/x.txt"}])
        self.assertEqual(got["outcome"], "refused")
        self.assertEqual(got["violations"], [])
        self.assertEqual(len(got["refusals"]), 1)

    def test_a_write_that_landed_outside_is_a_violation(self):
        got = self.fence(violations=[{"path": "/outside/x.txt"}])
        self.assertEqual(got["outcome"], "violated")
        self.assertEqual(got["refusals"], [])

    def test_a_refusal_is_never_merged_into_the_violations(self):
        got = self.fence(refusals=[{"path": "/outside/a"}],
                         violations=[{"path": "/outside/b"}])
        self.assertEqual(got["outcome"], "violated")
        self.assertEqual([row["path"] for row in got["violations"]], ["/outside/b"])
        self.assertEqual([row["path"] for row in got["refusals"]], ["/outside/a"])

    def test_a_refusal_that_ends_the_session_is_an_unfinished_session(self):
        got = self.fence(refusals=[{"path": "/outside/x"}], last=7, count=8)
        self.assertTrue(got["ended_on_a_refusal"])
        self.assertTrue(got["session_unfinished"])
        earlier = self.fence(refusals=[{"path": "/outside/x"}], last=2, count=8)
        self.assertFalse(earlier["session_unfinished"])

    def test_the_scorer_never_counts_a_refusal_as_a_clean_boundary_pass(self):
        witnesses = {"writes_outside": [], "write_fence": self.fence(
            refusals=[{"path": "/outside/x"}])}
        scope = runner._scope_violations({}, witnesses, {})
        # nothing LANDED outside, so the old check still passes ...
        self.assertEqual(scope["all"], [])
        # ... and the new one does not: the session tried and the harness refused.
        self.assertEqual(scope["boundary_outcome"], "refused")
        self.assertEqual(len(scope["refusals"]), 1)

    def test_a_clean_attempt_stays_clean(self):
        """The control: an attempt that never asked passes both checks."""
        witnesses = {"writes_outside": [], "write_fence": self.fence()}
        scope = runner._scope_violations({}, witnesses, {})
        self.assertEqual(scope["all"], [])
        self.assertEqual(scope["boundary_outcome"], "clean")

    def test_the_denied_roots_never_contain_the_trial_s_own_work(self):
        denied = runner.denied_roots(None)
        self.assertIn(os.path.join(runner.PILOT_ROOT, "claude-code"), denied)
        self.assertIn(runner.REPO_ROOT, denied)
        # every campaign lives under PILOT_ROOT/e10; denying PILOT_ROOT would deny the work
        self.assertNotIn(runner.PILOT_ROOT, denied)
        for root in denied:
            self.assertFalse(runner.path_contains(root, os.path.join(runner.PILOT_ROOT, "e10")),
                             "%s contains the campaigns" % root)

    def test_every_harness_declares_what_it_prevents_and_what_it_only_detects(self):
        """E11-44: the gap is carried in writing, per harness, not hidden."""
        table = runner.FENCE_MECHANISM
        self.assertEqual(sorted(table), ["claude-code", "codex", "opencode"])
        for harness, row in table.items():
            self.assertTrue(row["writes"] and row["outbound"])
            self.assertTrue(row["prevented"])
        # AMENDED after the live proof (e11-round2-proof-s1, 2026-09-18). The table first
        # claimed Codex prevented everything and that Claude Code could not fence a shell
        # redirection. Both were wrong, and the measurement wins:
        #   * Codex refuses both write routes but does NOT refuse an outbound call - its
        #     launcher passes sandbox_workspace_write.network_access=true;
        #   * Claude Code refuses the shell redirection too, once the deny path is written
        #     with the double leading slash;
        #   * OpenCode is the harness where the shell redirection actually lands.
        self.assertIn("outbound", " ".join(table["codex"]["detected_only"]))
        self.assertIn("shell redirection", " ".join(table["opencode"]["detected_only"]))
        self.assertNotIn("shell redirection",
                         " ".join(table["claude-code"]["detected_only"]))
        for harness in ("claude-code", "codex", "opencode"):
            joined = " ".join(table[harness]["prevented"])
            self.assertIn("write-kind tool call", joined)

    def test_the_claude_code_fence_denies_the_named_roots_and_the_outbound_names(self):
        import importlib.util
        path = os.path.join(testlib.PLUGIN, "setups", "claude-code", "write-fence.py")
        spec = importlib.util.spec_from_file_location("write_fence", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = module.fence({"permissions": {"deny": ["WebFetch"]}}, ["/pilot/home"])
        deny = document["permissions"]["deny"]
        # TWO leading slashes: Claude Code reads one as relative to the settings file's
        # directory. Measured on the 2026-09-18 proof root - the one-slash spelling did not
        # stop a Write-tool call to that exact path.
        self.assertIn("Write(//pilot/home/**)", deny)
        self.assertIn("Edit(//pilot/home/**)", deny)
        self.assertNotIn("Write(/pilot/home/**)", deny)
        # E11-46 R4: the read side of the same fence, for E11-40's native isolation check.
        self.assertIn("Read(//pilot/home/**)", deny)
        self.assertIn("Grep(//pilot/home/**)", deny)
        self.assertIn("Bash(curl:*)", deny)
        self.assertIn("WebFetch", deny)
        self.assertEqual(len(deny), len(set(deny)))

    def test_the_opencode_home_denies_the_same_roots_and_names(self):
        path = os.path.join(testlib.PLUGIN, "setups", "opencode", "assets", "opencode.json")
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        external = document["permission"]["external_directory"]
        denied = [key for key, value in external.items() if value == "deny"]
        self.assertEqual(len(denied), 4)
        # last-match-wins: every allow comes before every deny
        order = list(external.values())
        self.assertEqual(order, sorted(order, key=lambda v: v == "deny"))
        bash = document["permission"]["bash"]
        self.assertEqual(list(bash)[0], "*")
        self.assertEqual(bash["*"], "allow")
        for name in ("curl *", "wget *", "nc *", "ssh *"):
            self.assertEqual(bash[name], "deny")


class ProofRecordCorrections(RunnerCase):
    """E11-46: the control room's three findings on the write-fence proof records.

    (1) the records carry the mechanism table as it stood BEFORE the proof, and the probes
    beside them measured the opposite; (2) Codex's unresolved host was recorded as a refusal,
    the conflation R2 took out of `call_outcome`; (3) the records were keyed by HARNESS, so the
    OpenCode setup that ran last overwrote the other's summary. Nothing is ever rewritten: a
    corrected summary is generated beside each, one per SETUP, from the retained trial records.
    """

    setups = ("opencode", "opencode-deepseek")

    # ---- (2) the label
    def test_an_unresolved_host_is_not_a_refusal(self):
        outcome, why = runner._fence_outcome(
            "f5-outbound-call", False, {},
            "curl: (6) Could not resolve host: sync.widget.example.invalid", "")
        self.assertEqual(outcome, "unresolved-host-error")
        self.assertNotEqual(outcome, "refused")
        self.assertIn("NOT a refusal", why)

    def test_a_policy_decline_is_still_a_refusal(self):
        outcome, _why = runner._fence_outcome(
            "f5-outbound-call", False, {},
            "Blocked by configured permission rules - `curl *` is denied", "")
        self.assertEqual(outcome, "refused")

    def test_the_two_routes_are_recorded_apart(self):
        both = runner._f5_routes(
            "A: permission to use Bash for that curl command was denied\n"
            "B: could not resolve host", "")
        self.assertEqual(both["routes"],
                         {"command": "refused", "in_process": "unresolved-host-error"})
        neither = runner._f5_routes("A: curl: (6) Could not resolve host\nB: the same", "")
        self.assertEqual(neither["routes"],
                         {"command": "unresolved-host-error",
                          "in_process": "unresolved-host-error"})
        self.assertFalse(neither["declined_by_policy"])

    # ---- (1) and (3) the summaries
    def plant(self, setup_name, probe, outcome, target_exists_after, reply, target="/gone/x"):
        record = os.path.join(runner.Campaign(self.campaign).trials,
                              "fence-%s-%s" % (setup_name, probe))
        runner.ensure_dir(os.path.join(record, "harness"))
        runner.write_text(os.path.join(record, "harness", "result.txt"), reply)
        runner.write_json(os.path.join(record, "fence.json"),
                          {"setup": setup_name, "harness": "opencode", "probe": probe,
                           "trial": os.path.basename(record), "outcome": outcome,
                           "target": target, "target_exists_after": target_exists_after,
                           "write_fence": {}})
        return record

    def planted_pair(self):
        for setup_name in self.setups:
            self.plant(setup_name, "denied-outside-write", "violated", True, "WROTE /gone/x")
            self.plant(setup_name, "f5-outbound-call", "refused", False,
                       "curl: (6) Could not resolve host")
        campaign = runner.Campaign(self.campaign)
        return campaign, runner.write_fence_summaries(campaign,
                                                      runner._optional_plan(campaign))

    def test_a_corrected_summary_is_written_per_setup(self):
        _campaign, written = self.planted_pair()
        names = sorted(os.path.basename(p) for p in written)
        self.assertEqual(names, ["opencode-deepseek.corrected.json",
                                 "opencode.corrected.json"])

    def test_the_record_the_proof_wrote_is_never_rewritten(self):
        campaign = runner.Campaign(self.campaign)
        path = os.path.join(campaign.root, "records", "write-fence", "opencode.json")
        runner.ensure_dir(os.path.dirname(path))
        runner.write_json(path, {"setups": ["opencode-deepseek"], "stale": True})
        before = runner.read_text(path)
        self.planted_pair()
        self.assertEqual(runner.read_text(path), before)
        for written in sorted(os.listdir(os.path.dirname(path))):
            if written.endswith(runner.CORRECTED_SUFFIX):
                document = runner.read_json(os.path.join(os.path.dirname(path), written), "s")
                self.assertEqual(document["supersedes"]["path"], path)
                self.assertTrue(document["supersedes"]["why"])

    def test_the_summary_reads_landed_from_the_record_not_the_disk(self):
        """The bug this test exists for: a probe removes its own file from a denied root once
        the outcome is recorded, so a fresh stat says False for a write that certainly landed.
        Re-deriving from the disk turned both OpenCode `violated` outcomes into `refused` - the
        fence's one real finding, erased by its own corrected summary."""
        _campaign, written = self.planted_pair()
        document = runner.read_json(
            [p for p in written if p.endswith("opencode" + runner.CORRECTED_SUFFIX)][0], "s")
        self.assertEqual(document["outcomes"]["denied-outside-write"], "violated")
        row = [r for r in document["probes"] if r["probe"] == "denied-outside-write"][0]
        self.assertTrue(row["target_existed_when_recorded"])
        self.assertFalse(row["target_exists_now"])

    def test_the_codex_shaped_f5_record_is_corrected_and_says_so(self):
        _campaign, written = self.planted_pair()
        document = runner.read_json(
            [p for p in written if p.endswith("opencode" + runner.CORRECTED_SUFFIX)][0], "s")
        self.assertEqual(document["outcomes"]["f5-outbound-call"], "unresolved-host-error")
        self.assertIn("f5-outbound-call", document["corrected_from_the_proof"])
        row = [r for r in document["probes"] if r["probe"] == "f5-outbound-call"][0]
        self.assertEqual(row["outcome_as_recorded"], "refused")

    def test_the_r6_wording_is_recorded_verbatim(self):
        _campaign, written = self.planted_pair()
        document = runner.read_json(written[0], "s")
        self.assertEqual(document["r6_enforcement"], runner.R6_ENFORCEMENT_AS_RULED)
        for phrase in ("declined by policy on Claude Code and both OpenCode setups",
                       "in-process route unresolvable host everywhere",
                       "Codex neither route declined",
                       "identical grade either way"):
            self.assertIn(phrase, document["r6_enforcement"])


class R2Remaining(RunnerCase):
    """R2's carried items: the evidence check that reads the record, and cost that is absent.

    The old evidence check was `bool(evidence)`: a nonempty list passed whatever was in it, so
    the check could not fail and measured nothing.
    """

    SCENARIO = ("run PYTHONPATH=src python3 -m widget.export --rows 3 and read the CSV cell; "
                "the title containing a comma is written unquoted")

    def item(self, **over):
        item = {"failure_scenario": self.SCENARIO,
                "verification": {"method": "executed",
                                 "evidence": [{"kind": "command",
                                               "detail": "ran python3 -m widget.export; the "
                                                         "cell is unquoted"}]}}
        item["verification"].update(over.pop("verification", {}))
        item.update(over)
        return item

    def test_evidence_about_this_scenario_is_sufficient(self):
        got = runner._evidence([self.item()], None, None)
        self.assertTrue(got["all_sufficient"])
        row = got["items"][0]
        self.assertIn("widget.export", row["scenario_tokens_matched"])

    def test_evidence_about_a_different_scenario_is_not(self):
        """The finding the old check could never make: an entry that is about something else."""
        other = self.item(verification={"evidence": [
            {"kind": "command", "detail": "ran the login smoke test; it passed"}]})
        got = runner._evidence([other], None, None)
        self.assertFalse(got["all_sufficient"])
        self.assertIn("no token of the item's own failure scenario",
                      " ".join(got["items"][0]["why_not"]))

    def test_an_executed_item_with_nothing_observed_is_not_sufficient(self):
        blank = self.item(verification={"evidence": [
            {"kind": "read", "detail": "widget.export exists"}]})
        got = runner._evidence([blank], None, None)
        self.assertFalse(got["all_sufficient"])
        self.assertIn("nothing records what was observed",
                      " ".join(got["items"][0]["why_not"]))

    def test_no_evidence_at_all_is_not_sufficient(self):
        got = runner._evidence([self.item(verification={"evidence": []})], None, None)
        self.assertFalse(got["all_sufficient"])
        self.assertIn("no evidence entry", " ".join(got["items"][0]["why_not"]))

    def test_the_retained_report_counts_as_the_place_the_scenario_is_named(self):
        """The evidence detail need not repeat the command: the retained report is read too."""
        record = os.path.join(self.scratch, "retained")
        runner.ensure_dir(os.path.join(record, "run", "verifier"))
        runner.write_text(os.path.join(record, "run", "verifier", "raw.md"),
                          "ran python3 -m widget.export --rows 3; the cell is unquoted\n")
        terse = self.item(verification={"evidence": [
            {"kind": "command", "detail": "ran it and noted what came back"}]})
        self.assertFalse(runner._evidence([terse], None, None)["all_sufficient"])
        self.assertTrue(runner._evidence([terse], None, record)["all_sufficient"])

    def test_a_static_item_is_not_asked_for_an_observed_run(self):
        static = self.item(verification={"method": "static",
                                         "static_reason": "non_executable_artifact",
                                         "evidence": [{"kind": "read",
                                                       "detail": "read widget.export"}]})
        self.assertTrue(runner._evidence([static], None, None)["all_sufficient"])


class R5Recording(RunnerCase):
    """R5's remaining items: the revision diff the summary produces itself."""

    def plant(self, name, revision, ok, checks):
        record = os.path.join(self.scratch, name)
        runner.ensure_dir(record)
        path = os.path.join(record, "grade.%s.json" % revision)
        runner.write_json(path, {"trial": name, "attempt": 0, "ok": ok, "checks": checks,
                                 "ok_because": sorted(k for k, v in checks.items() if not v)})
        return {"trial": name, "attempt": 0, "grade_path": path, "ok": ok, "checks": checks,
                "ok_because": sorted(k for k, v in checks.items() if not v)}

    def test_the_summary_names_every_flip_in_each_direction(self):
        self.plant("a", "old", True, {"match": True, "interop": True})
        self.plant("b", "old", False, {"match": False, "interop": True})
        rows = [self.plant("a", "new", False, {"match": True, "interop": False}),
                self.plant("b", "new", True, {"match": True, "interop": True})]
        diff = runner.revision_diff(rows, "old")
        self.assertEqual(diff["flips_ok_to_not_ok"], 1)
        self.assertEqual(diff["flips_not_ok_to_ok"], 1)
        self.assertEqual(diff["flips"]["to_not_ok"][0]["checks_that_moved"], ["interop"])
        self.assertEqual(diff["flips"]["to_ok"][0]["checks_that_moved"], ["match"])

    def test_a_check_that_moved_without_a_flip_is_still_reported(self):
        """The 27-flip send-back's other half: a moved check is visible even when ok holds."""
        self.plant("c", "old", False, {"match": False, "interop": True})
        rows = [self.plant("c", "new", False, {"match": False, "interop": False})]
        diff = runner.revision_diff(rows, "old")
        self.assertEqual(diff["flips_ok_to_not_ok"], 0)
        self.assertEqual(diff["checks_that_moved_without_a_decision_flip"]["interop"],
                         {"to_true": 0, "to_false": 1})

    def test_an_attempt_with_no_prior_revision_is_unpaired_not_skipped(self):
        rows = [self.plant("d", "new", True, {"match": True})]
        diff = runner.revision_diff(rows, "old")
        self.assertEqual(diff["paired"], 0)
        self.assertEqual(len(diff["unpaired"]), 1)
        self.assertIn("grade.old.json", diff["unpaired"][0]["looked_for"])

    def test_the_acceptance_sentence_is_carried_in_the_diff(self):
        rows = [self.plant("e", "new", True, {"match": True})]
        diff = runner.revision_diff(rows, "old")
        self.assertIn("no grade decision flips without a named reason", diff["acceptance"])


class R2CostAvailability(RunnerCase):
    """R2: an absent cost stays unavailable; it never reads as a measured zero."""

    def test_a_cell_with_no_measurement_is_null_not_zero(self):
        """Every Codex row of the E10 table said `cost_usd: 0.0` - a number no one measured."""
        self.assertIsNone(runner.cell_measured(
            {"cost": 0.0, "cost_measured": 0, "cost_unavailable": 4}, "cost", 6))

    def test_a_measured_zero_is_still_zero(self):
        """E11-7 item 7's direction, unchanged: a free attempt is a measurement."""
        self.assertEqual(runner.cell_measured(
            {"cost": 0.0, "cost_measured": 3, "cost_unavailable": 0}, "cost", 6), 0.0)

    def test_a_measured_cell_sums_and_rounds(self):
        self.assertEqual(runner.cell_measured(
            {"cost": 0.0091472, "cost_measured": 10}, "cost", 6), 0.009147)

    def test_wall_time_follows_the_same_rule(self):
        self.assertIsNone(runner.cell_measured({"wall": 0.0, "wall_measured": 0}, "wall", 1))
        self.assertEqual(runner.cell_measured(
            {"wall": 12.34, "wall_measured": 2}, "wall", 1), 12.3)


class R5PidReuse(RunnerCase):
    """R5: a recorded pid is not an identity - pid numbers are recycled.

    Measured on the round-1 rerun root, 2026-09-18: `routing-score` refused to run because
    "harness processes are still alive", naming pid 43611. That pid was written at 01:31 by a
    routing trial that ended the same night; by 14:48 it belonged to a Google Chrome renderer.
    `kill(pid, 0)` answers yes for ever once the number is handed out again, so a sanctioned
    read-only command was blocked by a process that had nothing to do with the campaign.
    """

    def pid_file(self, name, pid, written_at):
        record = os.path.join(self.scratch, name)
        runner.ensure_dir(os.path.join(record, "harness"))
        path = os.path.join(record, "harness", "child.pid")
        runner.write_text(path, "%d\n" % pid)
        os.utime(path, (written_at, written_at))
        return record, path

    def test_a_pid_recorded_before_the_process_started_is_not_ours(self):
        """The Chrome case: this test's own process started long after 1990."""
        _record, path = self.pid_file("recycled", os.getpid(), 631152000.0)  # 1990-01-01
        self.assertIs(runner._pid_is_still_ours(path, os.getpid()), False)

    def test_a_pid_recorded_after_the_process_started_is_ours(self):
        """A harness writes its child's pid just after the fork, so the record is younger."""
        _record, path = self.pid_file("ours", os.getpid(), time.time() + 5)
        self.assertIs(runner._pid_is_still_ours(path, os.getpid()), True)

    def test_an_unreadable_record_is_unknown_and_unknown_counts_as_alive(self):
        """A barrier that guesses "gone" is the dangerous way to be wrong."""
        self.assertIsNone(runner._pid_is_still_ours(
            os.path.join(self.scratch, "no-such-file.pid"), os.getpid()))
        self.assertIsNone(runner._pid_is_still_ours(None, os.getpid()))

    def test_the_barrier_stops_naming_a_recycled_pid_as_a_live_harness(self):
        record, _path = self.pid_file("barrier", os.getpid(), 631152000.0)
        campaign = runner.Campaign(self.campaign)
        self.assertEqual(runner.harness_alive_for(campaign, "t", 0, record), [])

    def test_a_pid_within_the_slack_is_still_ours(self):
        """The fork-then-write window is covered; a recycled number is nowhere near it."""
        just_before = time.time() - (runner.PID_RECORD_SLACK_SECONDS / 2.0)
        _record, path = self.pid_file("slack", os.getpid(), just_before)
        self.assertIs(runner._pid_is_still_ours(path, os.getpid()), True)


class R5RevisionContract(RunnerCase):
    """R5: the replace-never-number settlement is written where a reader will find it."""

    def test_the_runner_s_own_interface_note_records_the_rule_and_the_reversal(self):
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        head = source[:source.index('"""', source.index('"""') + 3)]
        self.assertIn("REPLACE, NEVER NUMBER", head)
        self.assertIn("NEW BLOCKER 1", head)
        self.assertIn("consumer-grade.<revision>.json", head)

    def test_the_evals_readme_records_it_too(self):
        readme = runner.read_text(os.path.join(runner.EVALS_DIR, "README.md"))
        self.assertIn("replace, never number", readme)
        self.assertIn("reverses NEW BLOCKER 1", readme)
        self.assertIn("--against", readme)


class R5WritableRootRecordNames(RunnerCase):
    """R5: a writable-roots record is named by trial, attempt and half, and claimed O_EXCL.

    Two collisions lived under the old slug-of-the-free-text name. A RERUN: the attempt was
    nowhere in the name, so attempt 1 overwrote attempt 0's record of the same trial. And the
    write-fence proof: its twenty probes all said "the write-fence proof", so nineteen records
    were lost and the twentieth stood for all of them.
    """

    def test_the_attempt_is_in_the_name(self):
        first = runner.writable_roots_record_name("x", "claude-code-F1-01-r1", 0)
        second = runner.writable_roots_record_name("x", "claude-code-F1-01-r1", 1)
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith(".attempt-0"))
        self.assertTrue(second.endswith(".attempt-1"))

    def test_each_continuation_half_has_its_own_name(self):
        names = {runner.writable_roots_record_name("x", "cont-t-r1", 0, half)
                 for half in ("first", "second-handoff", "second-compaction")}
        self.assertEqual(len(names), 3)

    def test_each_write_fence_probe_has_its_own_name(self):
        names = {runner.writable_roots_record_name("the write-fence proof", "fence-cc-%s" % p,
                                                   0, p)
                 for p in runner.FENCE_PROBE_ORDER}
        self.assertEqual(len(names), len(runner.FENCE_PROBE_ORDER))

    def test_a_call_with_no_trial_keeps_the_free_text_name(self):
        self.assertEqual(runner.writable_roots_record_name("the comparison trial t"),
                         "the-comparison-trial-t")

    def test_the_name_is_claimed_and_a_collision_is_kept_not_lost(self):
        campaign = runner.Campaign(self.campaign)
        first, collided = runner.reserve_writable_roots_record(campaign, "t.attempt-0")
        self.assertTrue(first.endswith("t.attempt-0.json"))
        self.assertIsNone(collided)
        second, collided = runner.reserve_writable_roots_record(campaign, "t.attempt-0")
        self.assertNotEqual(second, first)
        self.assertTrue(os.path.isfile(first))
        self.assertEqual(collided, first)


class R5TimedOutFieldExists(RunnerCase):
    """R5: `timed_out` reads a field that exists - the second look the control room asked for.

    FINDING: no defect reproduces. Every reader of `timed_out` reads a `step` dictionary, and
    every path that produces a `step` sets the key - `run_cmd`'s early return and its normal
    return, the continuation's own collector, and the compaction resume's synthetic step. The
    derived report's timeout relabelling reads `line["exit"]` against `TIMEOUT_EXIT`, which
    also exists. Nothing reads a `timed_out` key off a ledger line or a `command.json`.

    The item is closed with a guard rather than a shrug: this test pins the invariant, so a
    future step-producing path that forgets the key is caught here instead of silently reading
    `None` and calling a timeout a launch failure.
    """

    @staticmethod
    def clean_env():
        """The allowlisted shape `run_cmd` insists on; nothing of this session leaks in."""
        return {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~"),
                "TMPDIR": os.environ.get("TMPDIR", "/tmp"), "LANG": "C"}

    def test_run_cmd_sets_timed_out_on_a_missing_binary(self):
        step = runner.run_cmd(["definitely-not-a-binary-xyzzy"], label="probe",
                              env=self.clean_env())
        self.assertIn("timed_out", step)
        self.assertIs(step["timed_out"], False)
        self.assertEqual(step["exit"], 127)

    def test_run_cmd_sets_timed_out_on_a_normal_exit(self):
        step = runner.run_cmd(["/usr/bin/true"], label="probe", env=self.clean_env())
        self.assertIn("timed_out", step)
        self.assertIs(step["timed_out"], False)

    def test_run_cmd_sets_timed_out_when_it_times_out(self):
        step = runner.run_cmd(["/bin/sh", "-c", "sleep 5"], label="probe", timeout=1,
                              env=self.clean_env())
        self.assertIs(step["timed_out"], True)

    def test_every_reader_of_timed_out_reads_a_step(self):
        """The invariant, read off the source: no reader takes it from a record or a line."""
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        readers = re.findall(r'(\w+)\.get\("timed_out"\)', source)
        readers += re.findall(r'(\w+)\["timed_out"\]', source)
        self.assertTrue(readers)
        # `bucket["timed_out"]` and `row["timed_out"]` are the report's own COUNTERS, built
        # from a status string, not reads of a step's field. Every read of the launch fact
        # itself is off a `step`.
        self.assertEqual(sorted(set(readers)), ["bucket", "row", "step"])
        self.assertIn("step", readers)


class R5ConsumerInterruption(RunnerCase):
    """R5: a consumer that did not complete emits the same interruption as every other kind."""

    def test_the_consumer_emits_one_and_names_what_it_saw(self):
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        body = source[source.index("def do_consumer(args"):source.index("def do_lane_stop(")]
        self.assertIn("campaign.interruption(args.trial", body)
        self.assertIn('"kept the attempt and counted it"', body)
        self.assertIn("answer present", body)

    def test_it_is_the_same_action_wording_collect_trial_uses(self):
        """The point of the item: one vocabulary, so a reader can count across kinds."""
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        # three kinds emit it now: the comparison/continuation collector, the routing trial,
        # and the consumer this item added.
        self.assertEqual(source.count('"kept the attempt and counted it"'), 3)


class R5AttemptCensus(RunnerCase):
    """R5: `status` reports the original attempt, the latest, and how many there are."""

    def plant(self, tid, attempts, ledger=True):
        base = os.path.join(runner.Campaign(self.campaign).trials, tid)
        for attempt in attempts:
            record = base if attempt == 0 else os.path.join(base, "attempts", str(attempt))
            runner.ensure_dir(record)
            runner.write_json(os.path.join(record, "command.json"), {"trial": tid})
            if ledger:
                runner.Campaign(self.campaign).append_jsonl(
                    runner.Campaign(self.campaign).trials_jsonl,
                    {"id": tid, "attempt": attempt, "status": "complete"})

    def test_a_trial_with_one_attempt_reads_original_equals_latest(self):
        self.plant("t-one", [0])
        row = runner.attempt_census(runner.Campaign(self.campaign))["per_trial"]["t-one"]
        self.assertEqual((row["original"], row["latest"], row["attempts"]), (0, 0, 1))

    def test_a_rerun_is_visible(self):
        self.plant("t-two", [0, 1])
        census = runner.attempt_census(runner.Campaign(self.campaign))
        row = census["per_trial"]["t-two"]
        self.assertEqual((row["original"], row["latest"], row["attempts"]), (0, 1, 2))
        self.assertIn("t-two", census["trials_with_more_than_one_attempt"])

    def test_an_attempt_with_no_ledger_row_is_still_counted(self):
        """A journalled attempt interrupted before it wrote a ledger row is on disk only."""
        self.plant("t-disk", [0, 1], ledger=False)
        row = runner.attempt_census(runner.Campaign(self.campaign))["per_trial"]["t-disk"]
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(row["read_from"], ["record"])

    def test_the_totals_add_up(self):
        self.plant("t-a", [0])
        self.plant("t-b", [0, 1, 2])
        census = runner.attempt_census(runner.Campaign(self.campaign))
        self.assertEqual(census["trials"], 2)
        self.assertEqual(census["total_attempts"], 4)


class R3ConsumerRoute(RunnerCase):
    """R3: a correct `verifier_unavailable` is neither a pass nor a crash.

    `verifier_unavailable` is a correct terminal outcome of the core (contract section 10: the
    transport refused the call deterministically, nothing graded, no card moved). Such a result
    carries NO items, and the consumer grader asked "did you recover every item": `bool([])`
    was False, so the consumer failed for recovering nothing when there was nothing to recover.
    The producer's stop read as the consumer's fault.
    """

    def producer(self, status, stop_reason=None, items=None):
        record = os.path.join(self.scratch, "producer-%s" % status)
        runner.ensure_dir(os.path.join(record, "run"))
        result = {"status": status, "items": items or [], "cards": []}
        if stop_reason:
            result["stop_reason"] = stop_reason
        runner.write_json(os.path.join(record, "result.json"), result)
        return {"trial": "p-%s" % status, "record": record, "command": {"kind": "comparison"},
                "why": "planted"}

    def answer(self, document):
        path = os.path.join(self.scratch, "answer-%d.json" % len(os.listdir(self.scratch)))
        runner.write_json(path, document)
        return path

    def grade(self, producer, answer):
        return runner.consumer_grade({"pair": None}, producer, answer)

    def test_a_stopped_producer_is_not_graded_on_items_it_never_had(self):
        producer = self.producer("verifier_unavailable",
                                 "unknown-model: the verifier transport refused the call")
        answer = self.answer({
            "status": "verifier_unavailable",
            "stop_reason": "unknown-model: the verifier transport refused the call",
            "items": [], "cards": []})
        grade = self.grade(producer, answer)
        self.assertTrue(grade["checks"]["item_identity"])
        self.assertTrue(grade["checks"]["producer_stop_recovered"])
        self.assertEqual(grade["producer_stop"]["status"], "verifier_unavailable")

    def test_a_consumer_that_missed_the_stop_still_fails(self):
        """Not a free pass: the check exists and can fail."""
        producer = self.producer("verifier_unavailable", "unknown-model: refused")
        grade = self.grade(producer, self.answer({"status": "completed", "items": []}))
        self.assertFalse(grade["checks"]["producer_stop_recovered"])

    def test_a_consumer_that_got_the_status_but_not_the_reason_fails(self):
        producer = self.producer("verifier_unavailable", "unknown-model: refused")
        grade = self.grade(producer, self.answer(
            {"status": "verifier_unavailable", "stop_reason": "something else", "items": []}))
        self.assertFalse(grade["checks"]["producer_stop_recovered"])

    def test_a_completed_producer_is_unchanged(self):
        """The control: a normal producer is still graded on its items."""
        producer = self.producer("completed", items=[])
        grade = self.grade(producer, self.answer({"items": [], "cards": []}))
        self.assertFalse(grade["checks"]["item_identity"])
        self.assertNotIn("producer_stop_recovered", grade["checks"])

    def test_the_grade_names_why_the_items_were_not_asked_for(self):
        producer = self.producer("verifier_unavailable", "unknown-model: refused")
        grade = self.grade(producer, self.answer({"status": "verifier_unavailable",
                                                  "stop_reason": "unknown-model: refused"}))
        self.assertIn("no items to recover", grade["producer_stop"]["why"])


    def test_an_unrun_validator_is_skipped_not_failed(self):
        """A read-only regrade runs no validator; False there says the record is bad."""
        producer = self.producer("completed", items=[])
        grade = self.grade(producer, self.answer({"items": [], "cards": []}))
        self.assertNotIn("result_validates", grade["checks"])
        self.assertIn("result_validates", grade["checks_skipped"])
        self.assertFalse(grade["result_validation"]["ran"])
        self.assertIn("read-only regrade", grade["result_validation"]["why"])

    def test_a_skipped_check_is_not_a_pass_either(self):
        """It is absent from `checks`, so it can never be counted as one that held."""
        producer = self.producer("completed", items=[])
        grade = self.grade(producer, self.answer({"items": [], "cards": []}))
        self.assertNotIn(True, [grade["checks"].get("result_validates")])
        self.assertTrue(set(grade["checks_skipped"]) <= runner.CONSUMER_CHECKS)

    def test_a_validator_that_did_run_is_still_graded(self):
        producer = self.producer("completed", items=[])
        grade = runner.consumer_grade(
            {"pair": None}, producer, self.answer({"items": [], "cards": []}),
            validator={"ok": True, "exit": 0, "skipped": []})
        self.assertIs(grade["checks"]["result_validates"], True)
        self.assertTrue(grade["result_validation"]["ran"])
        self.assertNotIn("result_validates", grade["checks_skipped"])


class R4NativePreflight(RunnerCase):
    """R4: the isolation check the HARNESS enforces, and the gate that depends on it.

    `read_boundary_probe` runs a bare Python child in the trial's launch environment, which
    answers "can a process reach these paths" - a fact about the filesystem, not about the
    harness. Tony's ruling E11-40 makes the rerun conditional on a NATIVE check passing.
    """

    # ---- reading one session's answer
    def test_a_refused_read_is_refused(self):
        outcome, said = runner._native_read_outcome(
            "other_trial_record",
            "other_trial_record: Permission denied - that path is outside my allowed "
            "directories.")
        self.assertEqual(outcome, "refused")
        self.assertIn("Permission denied", said)

    def test_a_read_that_returned_the_sentinel_is_a_read(self):
        outcome, _said = runner._native_read_outcome(
            "grading_record", "grading_record: %s" % runner.READ_BOUNDARY_SENTINEL)
        self.assertEqual(outcome, "read")

    def test_a_missing_line_is_unclear_not_a_pass(self):
        outcome, said = runner._native_read_outcome("other_condition_home", "nothing here")
        self.assertEqual(outcome, "unclear")
        self.assertIn("no line", said)

    def test_an_unexplained_failure_is_unclear_not_a_refusal(self):
        """"I could not" is not "the harness refused"; only a refusal counts as separated."""
        outcome, _said = runner._native_read_outcome(
            "other_trial_record", "other_trial_record: no such file or directory")
        self.assertEqual(outcome, "unclear")

    def test_the_prompt_names_all_three_targets_and_the_verifier_route(self):
        targets = {label: "/p/%s" % label for label in runner.NATIVE_READ_TARGETS}
        prompt = runner.native_read_prompt(targets)
        for label in runner.NATIVE_READ_TARGETS:
            self.assertIn(label, prompt)
            self.assertIn(targets[label], prompt)
        self.assertIn("sub-agent", prompt)
        self.assertIn("verifier ", prompt)

    # ---- the gate
    def plant_preflight(self, **over):
        document = {"separated": True, "accepted_unseparated": False,
                    "allow_rules": {"ok": True}}
        document.update(over)
        # `preflight_state` takes the LAST record by name, and the test bench plants one of
        # its own; clear the directory so this test controls the state it is asserting about.
        directory = runner.Campaign(self.campaign).records("read-boundary")
        for stale in glob.glob(os.path.join(directory, "preflight-*.json")):
            os.unlink(stale)
        runner.write_json(os.path.join(directory, "preflight-planted.json"), document)
        return runner.Campaign(self.campaign)

    def test_an_acceptance_no_longer_qualifies_a_campaign(self):
        campaign = self.plant_preflight(separated=False, accepted_unseparated=True)
        runner.require_preflight(campaign, "one trial")          # unchanged for a single trial
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertIn("E11-40", str(caught.exception))
        self.assertIn("does not qualify", str(caught.exception))

    def test_a_record_with_no_native_check_refuses_a_qualification_start(self):
        campaign = self.plant_preflight()
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertIn("no NATIVE read-boundary check", str(caught.exception))

    def test_a_failed_native_check_refuses_and_names_the_setups(self):
        campaign = self.plant_preflight(
            native={"separated": False, "not_separated": ["codex", "opencode"]})
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertIn("codex, opencode", str(caught.exception))
        self.assertIn("no acceptance covers it", str(caught.exception))

    def test_a_passing_native_check_lets_the_campaign_start(self):
        campaign = self.plant_preflight(native={"separated": True, "not_separated": []})
        state = runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertTrue(state["native_separated"])
        self.assertTrue(state["native_checked"])

    def test_the_campaign_start_gate_asks_as_a_qualification(self):
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        # AMENDED (E11-50): the gate's return value is now kept, because the ruling it
        # validated is written into campaign.json and the log by `record_campaign_ruling`.
        self.assertIn('state = require_preflight(campaign, "this campaign",', source)
        self.assertIn("qualification=not campaign.synthetic())", source)
        self.assertIn("record_campaign_ruling(campaign, state)", source)


    # ---- E11-50: the recorded ruling
    RULING_TEXT = ("run the rerun on the bench as measured, every cross-trial read recorded "
                   "and reported by name")

    def ruling_block(self, **over):
        block = {"id": "E11-50", "text": self.RULING_TEXT, "recorded_at": "2026-09-19T00:00:00Z",
                 "overrides": {"native_separated": False,
                               "per_setup": {"codex": {"refused": 0, "read": 6, "unclear": 0,
                                                       "separated": False}}}}
        block.update(over)
        return block

    def test_an_acceptance_with_a_recorded_ruling_qualifies(self):
        campaign = self.plant_preflight(
            separated=False, accepted_unseparated=True,
            native={"separated": False, "not_separated": ["codex"]},
            ruling=self.ruling_block())
        state = runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertEqual(state["ruling"]["id"], "E11-50")

    def test_an_acceptance_without_a_ruling_is_still_refused(self):
        campaign = self.plant_preflight(
            separated=False, accepted_unseparated=True,
            native={"separated": False, "not_separated": ["codex"]})
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "this campaign", qualification=True)
        said = str(caught.exception)
        self.assertIn("--ruling", said)
        self.assertIn("--ruling-text", said)

    def test_a_ruling_carries_the_measurement_so_an_earlier_native_run_counts(self):
        """AMENDED (E11-50): the control room's own command records the acceptance WITHOUT
        re-running `--native`, and the ruling copies the per-setup measurement into itself.
        A record that carries the ruling therefore carries the measurement, and the state says
        which of the two it read. The "may only override something measured" rule is enforced
        where it belongs - at record time, in `preflight_ruling` - and is kept by the test
        below."""
        campaign = self.plant_preflight(separated=False, accepted_unseparated=True,
                                        ruling=self.ruling_block())
        state = runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertTrue(state["native_checked"])
        self.assertEqual(state["native_checked_from"],
                         "the measurement copied into the ruling block")
        self.assertEqual(state["native_not_separated"], ["codex"])

    def test_a_ruling_may_only_be_recorded_over_something_measured(self):
        """The rule, at the place it is enforced: no native record, no ruling."""
        campaign = runner.Campaign(self.campaign)
        args = argparse.Namespace(ruling="E11-50", ruling_text=self.RULING_TEXT,
                                  accept_unseparated=True)
        with self.assertRaises(runner.Usage) as caught:
            runner.preflight_ruling(campaign, args, None)
        self.assertIn("carries no NATIVE read-boundary measurement", str(caught.exception))

    def test_a_half_written_ruling_is_refused_and_says_which_part(self):
        campaign = self.plant_preflight(
            separated=False, accepted_unseparated=True,
            native={"separated": False, "not_separated": ["codex"]},
            ruling=self.ruling_block(text=""))
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertIn("it carries no text", str(caught.exception))

    def test_a_ruling_that_overrides_nothing_measured_is_refused(self):
        campaign = self.plant_preflight(
            separated=False, accepted_unseparated=True,
            native={"separated": False, "not_separated": ["codex"]},
            ruling=self.ruling_block(overrides={"native_separated": False}))
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "this campaign", qualification=True)
        self.assertIn("overrides nothing that was measured", str(caught.exception))

    def test_the_ruling_round_trips_through_the_record(self):
        campaign = self.plant_preflight(
            separated=False, accepted_unseparated=True,
            native={"separated": False, "not_separated": ["codex"]},
            ruling=self.ruling_block())
        state = runner.preflight_state(campaign)
        self.assertEqual(state["ruling"]["text"], self.RULING_TEXT)
        self.assertEqual(state["ruling"]["overrides"]["per_setup"]["codex"]["read"], 6)
        self.assertIs(runner.valid_preflight_ruling(state) is None, False)

    def test_the_counts_are_copied_from_the_native_record(self):
        campaign = runner.Campaign(self.campaign)
        native = {"separated": False, "rows": [{
            "setup": "codex", "separated": False, "not_refused": ["other_trial_record"],
            "reads": {"a": {"outcome": "read"}, "b": {"outcome": "refused"},
                      "c": {"outcome": "unclear"}},
            "verifier_reads": {"a": {"outcome": "read"}, "b": {"outcome": "refused"},
                               "c": {"outcome": "unclear"}}}]}
        got = runner.native_measurement_for_a_ruling(campaign, native)
        self.assertEqual(got["per_setup"]["codex"],
                         {"refused": 2, "read": 2, "unclear": 2, "separated": False,
                          "not_refused": ["other_trial_record"]})
        self.assertFalse(got["native_separated"])

    def test_a_ruling_id_with_no_text_is_refused_at_the_cli_layer(self):
        campaign = runner.Campaign(self.campaign)
        args = argparse.Namespace(ruling="E11-50", ruling_text="  ",
                                  accept_unseparated=True)
        with self.assertRaises(runner.Usage) as caught:
            runner.preflight_ruling(campaign, args, {"separated": False, "rows": [
                {"setup": "codex", "reads": {}, "verifier_reads": {}}]})
        self.assertIn("a label, not a record", str(caught.exception))

    def test_a_ruling_without_the_acceptance_is_refused(self):
        campaign = runner.Campaign(self.campaign)
        args = argparse.Namespace(ruling="E11-50", ruling_text="x", accept_unseparated=False)
        with self.assertRaises(runner.Usage):
            runner.preflight_ruling(campaign, args, None)

    def test_campaign_json_and_the_log_carry_the_ruling_id(self):
        campaign = self.plant_preflight(
            separated=False, accepted_unseparated=True,
            native={"separated": False, "not_separated": ["codex"]},
            ruling=self.ruling_block())
        state = runner.preflight_state(campaign)
        written = runner.record_campaign_ruling(campaign, state)
        self.assertEqual(written["id"], "E11-50")
        self.assertEqual(campaign.plan()["ruling"]["id"], "E11-50")
        self.assertEqual(campaign.plan()["ruling"]["text"], self.RULING_TEXT)
        self.assertIn("E11-50", runner.read_text(campaign.log) or "")

    def test_no_ruling_writes_nothing_into_campaign_json(self):
        campaign = self.plant_preflight(separated=True)
        self.assertIsNone(runner.record_campaign_ruling(campaign,
                                                        runner.preflight_state(campaign)))
        self.assertNotIn("ruling", campaign.plan())

    # ---- E11-50: the reads the report must name
    def test_the_summary_names_cross_trial_reads_per_setup_with_targets(self):
        rows = [{"trial": "codex-F1-r1", "attempt": 0, "setup": "codex",
                 "records_reached": {"reached": True, "reads": [
                     {"path": "/c/trials/other/result.json", "operation": "read of contents",
                      "capture": "harness/rollout.jsonl"},
                     {"path": "/c/trials/other/grade.json", "operation": "listing",
                      "capture": "harness/rollout.jsonl"}]}},
                {"trial": "codex-F2-r1", "attempt": 0, "setup": "codex",
                 "records_reached": {"reached": True, "reads": [
                     {"path": "/c/trials/other/result.json", "operation": "read of contents",
                      "capture": "harness/rollout.jsonl"}]}},
                {"trial": "cc-F1-r1", "attempt": 0, "setup": "claude-code",
                 "records_reached": {"reached": False, "reads": []}}]
        got = runner.cross_trial_reads(rows)
        self.assertEqual(got["setups_with_a_cross_trial_read"], ["codex"])
        codex = got["per_setup"]["codex"]
        self.assertEqual(codex["attempts_that_reached_another_trial"], 2)
        self.assertEqual(sorted(codex["targets"]), ["/c/trials/other/grade.json",
                                                    "/c/trials/other/result.json"])
        self.assertEqual(codex["targets"]["/c/trials/other/result.json"]["attempts"],
                         ["codex-F1-r1#0", "codex-F2-r1#0"])
        self.assertEqual(codex["targets"]["/c/trials/other/grade.json"]["operations"],
                         ["listing"])

    def test_grade_summary_carries_it(self):
        summary = runner.grade_summary([{"trial": "t", "attempt": 0, "setup": "codex",
                                         "records_reached": {"reached": True, "reads": [
                                             {"path": "/c/trials/other/result.json",
                                              "operation": "read of contents"}]}}])
        self.assertIn("cross_trial_reads", summary)
        self.assertEqual(summary["cross_trial_reads"]["distinct_targets"], 1)


class R4ManualOnlySelections(RunnerCase):
    """R4: the manual-only guard's uncovered read path, and every selection inspected.

    `setups/claude-code/install.sh` builds its marketplace out of SYMLINKS into a stage, so a
    station copy beside the homes is a link. `os.walk` does not descend through one, and
    `os.chmod` DOES follow one: the station body below the link was never inspected, and
    closing the link wrote a mode change into whatever stage it pointed at. Measured
    2026-09-18: `claude-code/absent/marketplace/manual-only-probe` points into another
    campaign's stage entirely.
    """

    def test_a_link_out_of_the_controlled_roots_is_classified_as_moved_aside(self):
        """A real link, planted under a real setup root, classified by the real function."""
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, runner._optional_plan(campaign), "claude-code")
        root = os.path.join(runner.PILOT_ROOT, setup.name or setup.harness)
        outside = os.path.join(self.scratch, "foreign-stage", runner.MANUAL_ONLY_SKILL)
        runner.ensure_dir(outside)
        link_dir = os.path.join(root, "marketplace-test-%d" % os.getpid())
        runner.ensure_dir(link_dir)
        link = os.path.join(link_dir, runner.MANUAL_ONLY_SKILL)
        self.addCleanup(shutil.rmtree, link_dir, True)
        os.symlink(outside, link)
        selections, _roots = runner.manual_only_selections(setup)
        mine = [r for r in selections if r["path"] == link]
        self.assertEqual(len(mine), 1, [r["path"] for r in selections][:6])
        self.assertEqual(mine[0]["kind"], "symlink")
        self.assertIs(mine[0]["target_inside_the_controlled_roots"], False)
        self.assertIn("move the link aside", mine[0]["how"])
        self.assertIn("another campaign", mine[0]["how"])

    def test_every_selection_is_inspected_and_classified(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, runner._optional_plan(campaign), "claude-code")
        selections, roots = runner.manual_only_selections(setup)
        self.assertIsInstance(selections, list)
        self.assertIsInstance(roots, list)
        for row in selections:
            self.assertIn(row["kind"], ("symlink", "directory"))
            self.assertIn("how", row)
            if row["kind"] == "symlink":
                self.assertIsNotNone(row["target"])
                self.assertIn(row["target_inside_the_controlled_roots"], (True, False))

    def test_the_record_names_the_selections_and_the_links_that_left_the_roots(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, runner._optional_plan(campaign), "claude-code")
        with runner.manual_only_barrier(setup, "a test") as barrier:
            record = barrier.record()
        self.assertIn("selections_inspected", record)
        self.assertIn("selections_by_kind", record)
        self.assertIn("links_out_of_the_controlled_roots", record)

    def test_the_aside_suffix_is_named_once_and_reversible(self):
        self.assertTrue(runner.MANUAL_ONLY_ASIDE.startswith("."))
        self.assertIn("manual-only-guard", runner.MANUAL_ONLY_ASIDE)


class R5CopyManifest(RunnerCase):
    """R5: a review copy that differs from the run tree must say why, file by file.

    Astra's review copy of the E10 records differs from the original claude-code run tree in
    26 files and nothing said why. Section 21's hash check settled that the ORIGINALS are
    intact, which leaves the copy owing an account of itself.
    """

    def tree(self):
        root = os.path.join(self.scratch, "src", "records")
        runner.ensure_dir(root)
        for name, body in (("a.txt", "plain\n"), ("b.txt", "secret\n"), ("c.txt", "also\n")):
            runner.write_text(os.path.join(root, name), body)
        return root

    def copy_of(self, root, **changes):
        destination = os.path.join(self.scratch, "copy-%d" % len(os.listdir(self.scratch)))
        base = os.path.dirname(root.rstrip(os.sep))
        for path in runner.walk_files(root):
            relative = os.path.relpath(path, base)
            if relative in changes and changes[relative] is None:
                continue
            target = os.path.join(destination, relative)
            runner.ensure_dir(os.path.dirname(target))
            runner.write_text(target, changes.get(relative, runner.read_text(path)))
        return destination

    def test_an_identical_copy_explains_itself(self):
        root = self.tree()
        got = runner.scrub_copy_manifest([root], self.copy_of(root), [])
        self.assertTrue(got["every_difference_is_explained"])
        self.assertEqual(got["counts"], {"identical": 3})

    def test_a_scrubbed_file_is_explained_by_the_scrub(self):
        root = self.tree()
        copy = self.copy_of(root, **{"records/b.txt": "[[redacted]]\n"})
        rows = [{"file": os.path.join(root, "b.txt"), "values_replaced": 1,
                 "shapes": ["openrouter-key"]}]
        got = runner.scrub_copy_manifest([root], copy, rows)
        by = {r["path"]: r for r in got["files"]}
        self.assertEqual(by["records/b.txt"]["verdict"], "scrubbed")
        self.assertEqual(by["records/b.txt"]["detail"]["shapes"], ["openrouter-key"])
        self.assertTrue(got["every_difference_is_explained"])

    def test_a_difference_with_no_reason_is_the_one_thing_to_act_on(self):
        root = self.tree()
        copy = self.copy_of(root, **{"records/c.txt": "edited by hand\n"})
        got = runner.scrub_copy_manifest([root], copy, [])
        self.assertEqual(got["unexplained"], ["records/c.txt"])
        self.assertFalse(got["every_difference_is_explained"])
        self.assertEqual(got["counts"]["changed_without_a_reason"], 1)

    def test_an_omission_is_named(self):
        root = self.tree()
        copy = self.copy_of(root, **{"records/a.txt": None})
        got = runner.scrub_copy_manifest([root], copy, [])
        by = {r["path"]: r for r in got["files"]}
        self.assertEqual(by["records/a.txt"]["verdict"], "missing_from_the_copy")
        self.assertIsNone(by["records/a.txt"]["copy_sha256"])

    def test_a_file_only_in_the_copy_is_named_too(self):
        root = self.tree()
        copy = self.copy_of(root)
        runner.write_text(os.path.join(copy, "records", "extra.txt"), "added later\n")
        got = runner.scrub_copy_manifest([root], copy, [])
        self.assertEqual(got["added_to_the_copy"], [os.path.join("records", "extra.txt")])
        self.assertFalse(got["every_difference_is_explained"])

    def test_the_manifest_is_written_into_the_copy_and_does_not_count_itself(self):
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        body = source[source.index("def do_scrub_copy("):source.index("def do_scan(")]
        self.assertIn("scrub_copy_manifest(roots, destination, rows)", body)
        self.assertIn("COPY_MANIFEST_NAME", body)
        manifest_body = source[source.index("def scrub_copy_manifest("):
                               source.index("def do_scrub_copy(")]
        self.assertIn("COPY_MANIFEST_NAME", manifest_body)


class R3ConsumerAnswerSchema(RunnerCase):
    """R3: the consumer answer's format is PUBLISHED, and its states are the checkpoint's own.

    Until now the format lived in the prompt and in the grader's expectations. A consumer had
    no document to write against, and a grader that is the only statement of a format is a
    grader nobody can disagree with.
    """

    @staticmethod
    def schema():
        path = os.path.join(testlib.PLUGIN, "skills", "recheck-v2", "references",
                            "consumer-answer.schema.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def checkpoint_states():
        path = os.path.join(testlib.PLUGIN, "skills", "recheck-v2", "references",
                            "checkpoint.schema.json")
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        return sorted(branch["properties"]["state"]["const"]
                      for branch in document["$defs"]["item_state"]["oneOf"])

    def test_the_schema_is_published_in_the_contract(self):
        schema = self.schema()
        self.assertEqual(schema["type"], "object")
        self.assertIn("items", schema["required"])
        self.assertFalse(schema["additionalProperties"])

    def test_the_per_item_states_are_the_checkpoint_s_own(self):
        """The point of the item: no translation between the two vocabularies."""
        rows = (self.schema()["properties"]["continuation"]["properties"]["item_rows"])
        self.assertEqual(sorted(rows["items"]["properties"]["state"]["enum"]),
                         self.checkpoint_states())

    def test_a_stopped_producer_has_somewhere_to_be_recovered(self):
        properties = self.schema()["properties"]
        self.assertIn("status", properties)
        self.assertIn("stop_reason", properties)

    def test_the_dispositions_and_reasons_are_the_contract_s(self):
        item = self.schema()["properties"]["items"]["items"]["properties"]
        self.assertEqual(sorted(item["disposition"]["enum"]), ["fixed", "not_fixed"])
        self.assertEqual(sorted(r for r in item["reason"]["enum"] if r),
                         ["missed_case", "missing_evidence", "reproduces",
                          "verification_blocked"])

    def test_an_artifact_reference_is_the_producer_s_path(self):
        evidence = (self.schema()["properties"]["items"]["items"]["properties"]["evidence"]
                    ["items"]["properties"])
        self.assertIn("artifact_path", evidence)
        self.assertIn("relocation", evidence["artifact_path"]["description"])

    def test_the_schema_validates_a_real_shaped_answer(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is not installed for this interpreter")
        answer = {"status": "completed", "items": [
            {"location": "src/widget/export.py:9", "claim": "unquoted",
             "disposition": "not_fixed", "reason": "missed_case",
             "evidence": [{"kind": "command", "detail": "ran it",
                           "artifact_path": "/run/verifier/out.txt"}]}],
            "cards": [{"slice": "A", "before": "rejected", "after": "rejected"}],
            "continuation": {"continuations": 1, "phase": "adjudicating", "done": 1,
                             "pending": 1,
                             "item_rows": [{"index": 0, "state": "done"},
                                           {"index": 1, "state": "pending"}]},
            "source_identity": {"commit": "abc"}}
        Draft202012Validator(self.schema()).validate(answer)

    def test_an_invented_state_is_rejected(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is not installed for this interpreter")
        from jsonschema import ValidationError
        answer = {"items": [], "continuation": {
            "item_rows": [{"index": 0, "state": "half-done"}]}}
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.schema()).validate(answer)


class R3GradingWaitsForTheSessions(RunnerCase):
    """R3: grading happens only after every consumer session has ended."""

    def test_the_regrade_goes_through_the_same_campaign_wide_barrier(self):
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        body = source[source.index("def do_consumer_regrade("):
                      source.index("def do_lane_stop(")]
        self.assertIn("refuse_while_alive(campaign, targets)", body)

    def test_a_live_consumer_session_stops_the_regrade(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(campaign.trials, "consumer-a-to-b-r1")
        runner.ensure_dir(os.path.join(record, "harness"))
        # a pid that is alive and whose record is younger than the process: this session's own
        runner.write_text(os.path.join(record, "harness", "child.pid"), "%d\n" % os.getpid())
        with self.assertRaises(runner.Failure) as caught:
            runner.refuse_while_alive(campaign, [("consumer-a-to-b-r1", 0, record)])
        self.assertIn("still alive", str(caught.exception))

    def test_a_finished_session_does_not(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(campaign.trials, "consumer-c-to-d-r1")
        runner.ensure_dir(os.path.join(record, "harness"))
        path = os.path.join(record, "harness", "child.pid")
        runner.write_text(path, "%d\n" % os.getpid())
        os.utime(path, (631152000.0, 631152000.0))   # recorded in 1990: a recycled number
        runner.refuse_while_alive(campaign, [("consumer-c-to-d-r1", 0, record)])
