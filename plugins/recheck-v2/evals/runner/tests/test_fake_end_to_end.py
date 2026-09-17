"""The fake harness end to end: every subcommand that launches, with no model.

`run`, `campaign`, `rerun`, `grade`, `routing`, `routing-score`, `continuation`, `scan` and
`report` are exercised against the stub launchers under `fake/`, which drive the real core on
fixtures the E7 generators build. Grading uses the test's own stand-in key (E10-21).
"""
import json
import os
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, CASE, TWO_ITEM_CASE


class ThreeSetupsTest(RunnerCase):
    setups = ("claude-code", "codex", "opencode")

    def test_one_trial_per_setup_completes_and_validates(self):
        for harness in self.setups:
            tid, got = self.run_trial(harness=harness)
            self.assertEqual(got.returncode, 0, "%s: %s" % (harness, got.stderr))
            document = parse_stdout(got)
            self.assertEqual(document["status"], "complete", harness)
            self.assertEqual(document["validate_last_line"], "exit 0",
                             "%s did not validate: %s" % (harness, document))
            self.assertEqual(document["scan_hits"], 0)

    def test_the_model_and_the_cost_come_from_each_harness_s_own_record(self):
        expected = {
            "claude-code": ("claude-opus-5", "high", 0.1234),
            "codex": ("gpt-6-astra", "max", None),
            "opencode": ("openrouter/qwen/qwen3.8-flash", None, 0.00123456),
        }
        for harness in self.setups:
            tid, got = self.run_trial(harness=harness)
            self.assertEqual(got.returncode, 0, got.stderr)
            model = runner.read_json(os.path.join(self.campaign, "trials", tid, "model.json"))
            cost = runner.read_json(os.path.join(self.campaign, "trials", tid, "cost.json"))
            want_id, want_effort, want_cost = expected[harness]
            self.assertEqual(model["id"], want_id, harness)
            self.assertEqual(model["effort"], want_effort, harness)
            self.assertEqual(cost["total_cost_usd"], want_cost, harness)
            self.assertIsNotNone(model["source"], "%s names no record for the model" % harness)

    def test_activation_is_detected_from_each_harness_s_own_delivery_marker(self):
        for harness in self.setups:
            tid, got = self.run_trial(harness=harness)
            self.assertEqual(got.returncode, 0, got.stderr)
            command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
            activation = command["activated"]
            self.assertTrue(activation["activated"], "%s: no activation detected" % harness)
            self.assertIn("profile.md section 8", activation["profile_section"], harness)
            self.assertTrue(activation["marker"], harness)

    def test_the_codex_marker_is_the_installed_skill_read(self):
        tid, got = self.run_trial(harness="codex")
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        reads = command["activated"]["marker"]["installed_skill_reads"]
        self.assertTrue(reads)
        self.assertIn("SKILL.md", reads[0]["command"])

    def test_the_opencode_marker_is_the_skill_tool_call(self):
        tid, got = self.run_trial(harness="opencode")
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        calls = command["activated"]["marker"]["skill_tool_calls"]
        self.assertTrue(calls)
        self.assertEqual(calls[0]["input"]["name"], "recheck-v2")

    def test_the_claude_marker_is_the_skill_call_plus_the_delivered_body_record(self):
        tid, got = self.run_trial(harness="claude-code")
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        marker = command["activated"]["marker"]
        self.assertTrue(marker["skill_tool_calls"])
        self.assertTrue(marker["delivered_body_records"])

    def test_the_opencode_store_separation_witness_says_unavailable_with_no_child_rows(self):
        """E10-49 (finding 17): an empty or absent capture is `unavailable`, never `measured`.

        The old reader scanned the DRIVING session's rows and reported `measured: true`
        whatever it found; the real compaction record has exactly this empty shape.
        """
        tid, got = self.run_trial(harness="opencode")
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        witness = command["store_separation_witness"]
        self.assertFalse(witness["measured"])
        self.assertIn("unavailable", witness["verdict"])
        self.assertEqual(witness["child_rows_inspected"], 0)

    def test_the_store_separation_witness_reads_the_verifier_child_s_own_rows(self):
        """E10-59 (17): the rows are selected by the child session id the RECORDED CALL names.

        The driving session's own store carries the `task` call that spawned the verifier and
        the child session id in its output; the capture beside the trial carries that child's
        rows. Both halves have to agree before anything is `measured`.
        """
        tid, got = self.run_trial(harness="opencode")
        harness = os.path.join(self.campaign, "trials", tid, "harness")
        session = runner.read_json(os.path.join(harness, "session.json"))
        session["records"].append({"message_id": "msg_task", "parts": [
            {"id": "prt_task", "data": {"type": "tool", "tool": "task", "callID": "call_v1",
                                        "state": {"status": "completed",
                                                  "input": {"description": "verify"},
                                                  "output": "ses_child000000000000000001"}}}]})
        runner.write_json(os.path.join(harness, "session.json"), session)
        # the verifier child's own rows, retained beside the trial the way E10-49 asks
        runner.write_json(os.path.join(harness, "verifier-child.json"), {
            "session_id": "ses_child000000000000000001",
            "records": [{"session_id": "ses_child000000000000000001",
                         "message_id": "msg_child", "parts": [
                             {"id": "prt_c", "data": {"type": "tool", "tool": "read", "state": {
                                 "input": {"filePath": "/x/xdg-data/opencode/opencode.db"},
                                 "status": "completed"}}}]}]})
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "opencode", "harness": "opencode"})
        witness = setup.store_separation_witness(harness)
        self.assertEqual(witness["child_sessions_the_calls_name"],
                         ["ses_child000000000000000001"])
        self.assertTrue(witness["measured"])
        self.assertEqual(witness["child_rows_inspected"], 1)
        self.assertEqual(len(witness["reads_of_the_driving_store"]), 1)
        self.assertIn("read the driving store", witness["verdict"])

    def test_rows_of_a_session_no_recorded_call_names_are_not_a_measurement(self):
        """E10-59 (17): the reviewer's probe — a capture whose rows belong to some other
        session established a measurement, because the reader took any file whose name looked
        like a verifier capture."""
        tid, got = self.run_trial(harness="opencode")
        harness = os.path.join(self.campaign, "trials", tid, "harness")
        session = runner.read_json(os.path.join(harness, "session.json"))
        session["records"].append({"message_id": "msg_task", "parts": [
            {"id": "prt_task", "data": {"type": "tool", "tool": "task", "callID": "call_v1",
                                        "state": {"status": "completed",
                                                  "input": {"description": "verify"},
                                                  "output": "ses_expected00000000000001"}}}]})
        runner.write_json(os.path.join(harness, "session.json"), session)
        runner.write_json(os.path.join(harness, "verifier-unrelated.json"), {
            "records": [{"session_id": "ses_unrelated0000000000001",
                         "message_id": "other", "parts": []}]})
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "opencode", "harness": "opencode"})
        witness = setup.store_separation_witness(harness)
        self.assertEqual(witness["child_sessions_the_calls_name"],
                         ["ses_expected00000000000001"])
        self.assertEqual(witness["child_rows_inspected"], 0)
        self.assertFalse(witness["measured"])
        self.assertIn("unavailable", witness["verdict"])
        self.assertEqual(witness["child_rows_rejected_count"], 1)
        self.assertEqual(witness["child_rows_rejected"][0]["session_id"],
                         "ses_unrelated0000000000001")


class ConditionWitnessTest(RunnerCase):
    conditions = ("available", "absent")

    def test_the_available_condition_s_witness_shows_the_skill_in_the_catalog(self):
        tid, got = self.run_trial(condition="available")
        self.assertEqual(got.returncode, 0, got.stderr)
        witness = runner.read_json(
            os.path.join(self.campaign, "trials", tid, "command.json"))["condition_witness"]
        self.assertTrue(witness["recheck_v2_in_catalog"])
        self.assertIn("init event", witness["source"])

    def test_the_absent_condition_s_witness_shows_the_skill_out_of_the_catalog(self):
        tid, got = self.run_trial(condition="absent")
        self.assertEqual(got.returncode, 0, got.stderr)
        witness = runner.read_json(
            os.path.join(self.campaign, "trials", tid, "command.json"))["condition_witness"]
        self.assertFalse(witness["recheck_v2_in_catalog"])

    def test_the_absent_condition_loads_no_recheck_v2_plugin(self):
        tid, got = self.run_trial(condition="absent")
        names = runner.read_json(os.path.join(self.campaign, "trials", tid, "harness",
                                              "env-names.json"))
        self.assertNotIn("--plugin recheck-v2", " ".join(names["argv"]))


class GradeTest(RunnerCase):
    def test_a_matching_stand_in_key_grades_ok(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = parse_stdout(cli(["grade", "--campaign", self.campaign, tid, "--summary"],
                                  env=environment))
        self.assertEqual(graded["summary"]["ok"], 1)
        self.assertEqual(graded["summary"]["validator_ok"], 1)
        self.assertEqual(graded["summary"]["match_ok"], 1)
        self.assertEqual(graded["summary"]["false_fixed_items"], 0)
        self.assertEqual(graded["summary"]["key_runs_at_includes_E10"], 1)

    def test_a_stand_in_that_pins_not_fixed_scores_a_false_fixed(self):
        directory = self.stand_in_key(expected={"status": "completed",
                                                "items": [{"disposition": "not_fixed"}]})
        tid, got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = parse_stdout(cli(["grade", "--campaign", self.campaign, tid, "--summary"],
                                  env=environment))
        self.assertEqual(graded["summary"]["false_fixed_items"], 1)
        self.assertEqual(graded["summary"]["ok"], 0)

    def test_a_trial_with_no_result_grades_every_metric_no_result_and_counts_as_a_failure(self):
        directory = self.stand_in_key()
        tid = runner.trial_id("claude-code", CASE, "available", 1)
        record = os.path.join(self.campaign, "trials", tid)
        runner.write_json(os.path.join(record, "command.json"),
                          {"case": CASE, "setup": "claude-code", "condition": "available",
                           "workspace": "/nowhere", "status": "no_result", "wall_seconds": 1.0})
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = parse_stdout(cli(["grade", "--campaign", self.campaign, tid, "--summary"],
                                  env=environment))
        self.assertEqual(graded["summary"]["no_result"], 1)
        self.assertEqual(graded["summary"]["ok"], 0)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        for metric in ("validator", "match", "false_fixed", "dispositions", "interop"):
            self.assertEqual(grade[metric], "no_result")

    def test_grade_all_grades_every_comparison_record(self):
        directory = self.stand_in_key()
        first, _ = self.run_trial()
        again = cli(["rerun", "--campaign", self.campaign, first,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 0, again.stderr)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = parse_stdout(cli(["grade", "--campaign", self.campaign, "--all", "--summary"],
                                  env=environment))
        # E10-44 (finding 6): every ATTEMPT is graded, the rerun's own included, and the two
        # grades join on (trial id, attempt).
        self.assertEqual(graded["graded"], 2)
        self.assertEqual(sorted(g["attempt"] for g in graded["grades"]), [0, 1])
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "trials", first,
                                                    "attempts", "1", "grade.json")))
        for row in graded["grades"]:
            self.assertTrue(row["grade_path"], "grade returned no written path")

    def test_the_grade_records_the_evidence_and_the_interop_fields(self):
        directory = self.stand_in_key()
        tid, _ = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        cli(["grade", "--campaign", self.campaign, tid], env=environment)
        grade = runner.read_json(os.path.join(self.campaign, "trials", tid, "grade.json"))
        self.assertTrue(grade["evidence_sufficient"]["all_sufficient"])
        # E8-A43: `commands_run` and `observed` are `unchecked` when the result carries neither
        self.assertEqual(grade["evidence_sufficient"]["items"][0]["commands_run"], "unchecked")
        self.assertTrue(grade["interop"]["chat_lines_present"]["RECHECK:"])
        self.assertTrue(grade["interop"]["chat_lines_present"]["Result:"])
        self.assertTrue(grade["interop"]["chat_lines_present"]["Source:"])
        self.assertEqual(grade["scope_violations"]["all"], [])
        self.assertEqual(grade["unauthorized"]["all"], [])


class RoutingTest(RunnerCase):
    setups = ("claude-code", "codex", "opencode")

    def test_one_routing_trial_per_setup_records_its_observed_target(self):
        for harness in self.setups:
            tid = runner.routing_trial_id(harness, "T-01-slash-v2-slice", 1)
            got = cli(["routing", "--campaign", self.campaign, tid,
                       "--fake-launcher", self.fake_launcher(harness)])
            self.assertEqual(got.returncode, 0, "%s: %s" % (harness, got.stderr))
            document = parse_stdout(got)
            self.assertEqual(document["observed_target"]["target"], "recheck-v2", harness)
            self.assertTrue(document["observed_target"]["how"], harness)
            self.assertFalse(document["profile_breach"]["breached"], harness)

    def test_the_routing_workspace_is_an_empty_git_work_tree_with_no_build_doc(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        workspace = command["workspace"]
        # E10-41: the workspace sits inside the trial's own opaque tree, and its path names
        # neither the setup nor the entry.
        self.assertTrue(workspace.startswith(command["opaque_tree"]))
        self.assertNotIn("claude-code", workspace)
        self.assertNotIn("T-01", workspace)
        self.assertTrue(os.path.isdir(os.path.join(workspace, ".git")))
        self.assertEqual(sorted(n for n in os.listdir(workspace) if n != ".git"), [".gitkeep"])

    def test_the_prompt_is_the_request_text_alone(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        cli(["routing", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        prompt = runner.read_text(os.path.join(self.campaign, "trials", tid, "prompt.txt"))
        self.assertEqual(prompt.strip(), "/recheck-v2 slice A")

    def test_the_turn_limit_is_recorded_as_absent_with_its_reason(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        cli(["routing", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertIsNone(command["turn_limit"]["flag"])
        self.assertIn("max-turns", command["turn_limit"]["reason"])

    def test_routing_score_writes_one_file_per_setup_with_the_two_rates(self):
        for harness in ("claude-code", "codex"):
            tid = runner.routing_trial_id(harness, "T-01-slash-v2-slice", 1)
            cli(["routing", "--campaign", self.campaign, tid,
                 "--fake-launcher", self.fake_launcher(harness)])
        got = cli(["routing-score", "--campaign", self.campaign, "--revision", "rev0"])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertEqual(len(document["written"]), 2)
        for row in document["written"]:
            self.assertTrue(row["path"].endswith("rev0.json"))
            scored = runner.read_json(row["path"])
            self.assertEqual(scored["rates"]["tuning"]["activate_entries"], 1)
            self.assertEqual(scored["rates"]["tuning"]["activation_rate"], 1.0)
            self.assertIsNone(scored["rates"]["held-out"]["activation_rate"])
            self.assertEqual(scored["rows"][0]["observed_target"], "recheck-v2")
            self.assertTrue(scored["rows"][0]["matches_expected"])
            self.assertFalse(scored["rows"][0]["blocked_station_leak"])
            self.assertIn("manual_only_row", scored)

    def test_a_blocked_station_in_the_observed_target_is_a_leak_row(self):
        """E11-7 item 1: the leak is read from the NATIVE capture, not from the cached value.

        The score used to reuse `command.json.observed_target`, the value the witness this
        repair replaces had written. The trace is what a blocked station's selection
        actually leaves behind, so this test plants it there.
        """
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        cli(["routing", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        record = os.path.join(self.campaign, "trials", tid)
        trace = os.path.join(record, "harness", "trace.jsonl")
        rows = [json.loads(line) for line in open(trace) if line.strip()]
        for row in rows:
            for block in ((row.get("message") or {}).get("content") or []):
                if isinstance(block, dict) and block.get("name") == "Skill":
                    block["input"]["skill"] = "signoff:signoff"
        with open(trace, "w") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        document = parse_stdout(cli(["routing-score", "--campaign", self.campaign]))
        scored = runner.read_json(document["written"][0]["path"])
        self.assertEqual(scored["rows"][0]["observed_target"], "signoff")
        self.assertEqual(scored["rows"][0]["observed_target_recomputed"], "signoff")
        self.assertEqual(scored["rows"][0]["observed_target_as_recorded"], "recheck-v2")
        self.assertFalse(scored["rows"][0]["recomputed_agrees_with_the_record"])
        self.assertTrue(scored["rows"][0]["blocked_station_leak"])
        self.assertEqual(len(scored["blocked_station_leaks"]), 1)
        self.assertEqual(len(scored["recomputed_differs_from_the_record"]), 1)


class ContinuationTest(RunnerCase):
    cases = (TWO_ITEM_CASE,)

    def test_the_handoff_path_launches_a_fresh_session_and_records_the_cut(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertIn("cut", document)
        self.assertIn("cut_made", document["cut"])
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertEqual(command["kind"], "continuation:handoff")
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "trials", tid,
                                                    "resume-prompt.txt")))
        resume = runner.read_text(os.path.join(self.campaign, "trials", tid, "resume-prompt.txt"))
        self.assertIn("resume the recheck run", resume)

    def test_the_compaction_path_records_every_attempt_with_its_command(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "compaction", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        compaction = command["compaction"]
        self.assertIsNotNone(compaction)
        self.assertIn("mechanism", compaction)
        self.assertIn("attempts", compaction)
        self.assertIn("verdict", compaction)

    def test_the_compaction_mechanism_table_states_what_each_harness_offers(self):
        self.assertEqual(runner.COMPACTION["claude-code"]["smallest_window"], "100000")
        self.assertIsNone(runner.COMPACTION["opencode"]["flag"])
        self.assertIn("model_auto_compact_token_limit", runner.COMPACTION["codex"]["flag"])

    def test_the_cut_is_read_from_the_retained_pair_and_is_valid_when_they_agree(self):
        """E10-47: the claim comes from the checkpoint/log pair retained AFTER the stop."""
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        stub = self.cut_stub("valid")
        got = cli(["continuation", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        cut = command["cut"]
        self.assertTrue(cut["cut_made"])
        self.assertTrue(cut["valid"], cut.get("invalid_because"))
        self.assertEqual(cut["seq"], 3)
        self.assertEqual((cut["done"], cut["pending"]), (1, 1))
        self.assertEqual(cut["checkpoint_log_lines"], 4)
        self.assertEqual(cut["poll_interval_seconds"], 0.1)
        # E10-55: the pair was captured while the group was frozen
        self.assertTrue(cut["freeze"]["captured_while_frozen"], cut["freeze"])
        retained = os.path.join(self.campaign, "trials", tid, "harness-first",
                                "at-cut-checkpoint.json")
        self.assertEqual(runner.read_json(retained)["integrity"]["seq"], 3)
        self.assertEqual(cut["start_identity"], {"commit": "cut-commit"})

    def test_the_race_of_finding_15_no_longer_reaches_the_retained_pair(self):
        """E10-55 replaces what this test used to prove.

        Finding 15's race, made deterministic: the session advances to `done, done` as it dies.
        Before E10-55 it won — the dry run claimed seq 3 with one item done while both retained
        `at-cut-checkpoint.json` files were seq 4 with both done — and the cut was recorded
        INVALID. The group is now frozen with SIGSTOP before the capture, so the same stub
        cannot advance until the pair is retained, and the cut is valid at the state the poller
        saw. A retained pair that still disagrees is still an invalid cut
        (`test_findings.FrozenCutTest`).
        """
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        stub = self.cut_stub("race", advance_on_term=True)
        got = cli(["continuation", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        cut = command["cut"]
        self.assertTrue(cut["cut_made"], "the poller never saw the mixed state")
        self.assertTrue(cut["freeze"]["confirmed"], cut["freeze"])
        self.assertTrue(cut["valid"], cut.get("invalid_because"))
        self.assertEqual(cut["seq"], 3)
        self.assertEqual(cut["observed_at_the_poll"]["seq"], 3)

    def test_a_poll_interval_coarser_than_a_tenth_of_a_second_is_refused(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid, "--poll-interval", "1.0",
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("ten times a second", got.stderr)

    def test_a_compaction_witness_is_a_native_event_before_the_resumed_work(self):
        """E10-47: never prose. `G_probe.py` made a diagnostic SENTENCE count as a witness."""
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "claude-code", "harness": "claude-code"})
        out = os.path.join(self.scratch, "second")
        runner.ensure_dir(out)
        # prose that mentions compaction, in the file the old reader also grepped
        runner.write_text(os.path.join(out, "resume.err"),
                          "the session was compacted before the turn; subtype: compact\n")
        self.assertIsNone(runner.compaction_witness(setup, out))
        # the native event, in the harness's own record
        runner.write_text(os.path.join(out, "trace.jsonl"), "\n".join([
            '{"type": "system", "subtype": "compact_boundary", "session_id": "s"}',
            '{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",'
            ' "id": "t1", "input": {"command": "ls"}}]}}']) + "\n")
        witness = runner.compaction_witness(setup, out)
        self.assertEqual(witness["file"], "trace.jsonl")
        self.assertEqual(witness["line"], 1)
        self.assertEqual(witness["first_resumed_work_line"], 2)
        self.assertTrue(witness["before_the_resumed_work"])

    def test_a_compaction_event_after_the_resumed_work_is_not_ok(self):
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "claude-code", "harness": "claude-code"})
        out = os.path.join(self.scratch, "late")
        runner.ensure_dir(out)
        runner.write_text(os.path.join(out, "trace.jsonl"), "\n".join([
            '{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",'
            ' "id": "t1", "input": {"command": "ls"}}]}}',
            '{"type": "system", "subtype": "compact_boundary", "session_id": "s"}']) + "\n")
        witness = runner.compaction_witness(setup, out)
        self.assertFalse(witness["before_the_resumed_work"])
        self.assertFalse(witness["ok"])

    def test_the_cut_predicate_is_one_item_done_and_one_pending_in_the_right_phase(self):
        self.assertTrue(runner.cut_point_reached(
            {"done": 1, "pending": 1, "phase": "adjudicating", "seq": 4}))
        self.assertTrue(runner.cut_point_reached(
            {"done": 1, "pending": 1, "phase": "verifying", "seq": 4}))
        self.assertFalse(runner.cut_point_reached(
            {"done": 2, "pending": 0, "phase": "adjudicating", "seq": 4}))
        self.assertFalse(runner.cut_point_reached(
            {"done": 1, "pending": 1, "phase": "recording", "seq": 4}))
        self.assertFalse(runner.cut_point_reached(None))

    def test_the_checkpoint_reader_counts_the_item_states_and_the_seq(self):
        run_dir = os.path.join(self.scratch, "run")
        runner.write_json(os.path.join(run_dir, "checkpoint.json"), {
            "phase": "adjudicating", "integrity": {"seq": 7},
            "scope": {"items": [{"state": "done"}, {"state": "pending"}]},
            "continuations": 1})
        state = runner.checkpoint_state(run_dir)
        self.assertEqual(state["seq"], 7)
        self.assertEqual(state["done"], 1)
        self.assertEqual(state["pending"], 1)
        self.assertEqual(state["continuations"], 1)


class CampaignLoopTest(RunnerCase):
    setups = ("claude-code",)
    cases = (CASE,)
    conditions = ("available", "absent")
    repetitions = 1

    def test_the_whole_small_plan_runs_in_the_foreground_and_reports(self):
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--skip-probe-gate", "--reopen-key",
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertEqual(len(document["ran"]), document["planned"] - len(document["failed"])
                         - len(document["skipped"]))
        status = parse_stdout(cli(["campaign", "status", "--campaign", self.campaign]))
        self.assertGreaterEqual(status["complete"], 2)
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertGreaterEqual(report["trials_seen"], 2)
        scanned = parse_stdout(cli(["scan", "--campaign", self.campaign]))
        self.assertTrue(scanned["ok"])


if __name__ == "__main__":
    unittest.main()
