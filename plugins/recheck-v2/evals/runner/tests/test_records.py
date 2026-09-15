"""The record layout of E10-10, the refusal to overwrite, the timeout path, the scan, the
report's counts, and campaign resume from disk."""
import json
import os
import shutil
import subprocess
import sys
import time
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, CASE, FAKE

RECORD_FILES = ("command.json", "prompt.txt", "model.json", "cost.json", "chat.md",
                "validate.txt", "scan.json")
COMMAND_FIELDS = ("argv", "cwd", "allowlisted_env_names", "started_at", "ended_at",
                  "wall_seconds", "exit", "timeout_verdict", "condition_witness", "setup_home",
                  "staged_commit", "plugin_tree_sha256", "setup_tree_sha256", "fixture")


class RecordLayoutTest(RunnerCase):
    def setUp(self):
        RunnerCase.setUp(self)
        self.tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        self.record = os.path.join(self.campaign, "trials", self.tid)

    def test_every_file_E10_10_names_is_in_the_record(self):
        for name in RECORD_FILES:
            self.assertTrue(os.path.isfile(os.path.join(self.record, name)),
                            "the record has no %s" % name)
        for name in ("harness", "run", "fixture"):
            self.assertTrue(os.path.isdir(os.path.join(self.record, name)),
                            "the record has no %s/" % name)

    def test_command_json_carries_every_field_E10_10_names(self):
        command = runner.read_json(os.path.join(self.record, "command.json"))
        for field in COMMAND_FIELDS:
            self.assertIn(field, command)
        self.assertEqual(command["fixture"]["lane"], "F1-fixed-defect")
        self.assertTrue(command["fixture"]["opaque"], "the fixture was not built opaque")
        self.assertEqual(command["staged_commit"], "test-commit")

    def test_the_fixture_path_the_model_saw_names_neither_the_lane_nor_the_case(self):
        command = runner.read_json(os.path.join(self.record, "command.json"))
        case_dir = os.path.basename(command["fixture"]["case_dir"])
        self.assertNotIn("F1", case_dir)
        self.assertNotIn("fixed-clean", case_dir)
        self.assertEqual(case_dir, runner.hashlib.sha256(CASE.encode()).hexdigest()[:12])

    def test_model_json_states_what_the_harness_recorded(self):
        model = runner.read_json(os.path.join(self.record, "model.json"))
        self.assertEqual(model["id"], "claude-opus-5")
        self.assertEqual(model["effort"], "high")
        self.assertIn("transcript", model["source"])

    def test_cost_json_carries_what_the_harness_printed(self):
        cost = runner.read_json(os.path.join(self.record, "cost.json"))
        self.assertEqual(cost["total_cost_usd"], 0.1234)
        self.assertIn("total_cost_usd", cost["source"])

    def test_the_run_directory_was_copied_whole(self):
        run = os.path.join(self.record, "run")
        for name in ("result.json", "input.json", "chat.md", "checkpoint.json", "checkpoint.log",
                     "receipt.json", "result.schema.json"):
            self.assertTrue(os.path.isfile(os.path.join(run, name)), "run/%s is missing" % name)

    def test_the_canonical_result_schema_was_copied_in_before_the_launch(self):
        copied = runner.read_text(os.path.join(self.record, "run", "result.schema.json"))
        canonical = runner.read_text(os.path.join(runner.SKILL_DIR, "references",
                                                  "result.schema.json"))
        self.assertEqual(copied, canonical)

    def test_validate_txt_ends_with_the_exit_status(self):
        text = runner.read_text(os.path.join(self.record, "validate.txt"))
        self.assertTrue(text.strip().splitlines()[-1].startswith("exit "))

    def test_the_trial_line_landed_in_trials_jsonl(self):
        lines = [json.loads(l) for l in
                 runner.read_text(os.path.join(self.campaign, "trials.jsonl")).splitlines() if l]
        self.assertEqual([l["id"] for l in lines], [self.tid])
        self.assertEqual(lines[0]["status"], "complete")
        for field in ("id", "attempt", "status", "exit", "wall", "cost", "model", "effort",
                      "activated", "record"):
            self.assertIn(field, lines[0])

    def test_the_prompt_names_no_plugin_no_harness_and_no_condition_outside_its_paths(self):
        """E10-4, checked on the prompt's own words.

        The absolute paths the prompt must carry (the workspace, the run directory) are the one
        place a name can leak: the run root is the adapter's `${TMPDIR}/recheck-v2` and the
        trial directory carries the setup and the condition. The words are checked here; the
        path leak is checked, and recorded as a breach, by the next test.
        """
        prompt = runner.read_text(os.path.join(self.record, "prompt.txt"))
        words = " ".join(w for w in prompt.lower().split() if not w.startswith("/"))
        for banned in ("recheck-v2", "plugin", "claude", "codex", "opencode", "available",
                       "absent", "skill"):
            self.assertNotIn(banned, words, "the prompt's own words name %r" % banned)
        self.assertNotIn("do not use", prompt.lower())
        self.assertIn("a fresh verifier proves", prompt)

    def test_the_default_run_root_is_neutral_and_the_note_says_so(self):
        # E10-22: the setups name the run root ${TMPDIR}/runs, so the default plan breaches
        # nothing; the note still records the name and the rule that ties the launchers to it.
        command = runner.read_json(os.path.join(self.record, "command.json"))
        note = command["run_root_note"]
        self.assertEqual(note["run_root_name"], "runs")
        self.assertFalse(note["prompt_names_the_skill"])
        self.assertIn("external_directory", note["reason"])
        prompt = runner.read_text(os.path.join(self.record, "prompt.txt"))
        self.assertNotIn("recheck-v2", prompt, "the run-directory path names the skill")

    def test_a_plan_that_names_the_old_run_root_records_the_breach_rather_than_hiding_it(self):
        note = runner.run_root_note({"run_root_name": "recheck-v2"})
        self.assertEqual(note["run_root_name"], "recheck-v2")
        self.assertTrue(note["prompt_names_the_skill"])
        self.assertIn("breached", note["reason"])

    def test_a_neutral_run_root_name_in_the_plan_removes_the_name_from_the_prompt(self):
        self.campaign = os.path.join(self.scratch, "neutral-campaign")
        self.make_campaign({"run_root_name": "runs"})
        tid, got = self.run_trial(rep=1, case=CASE)
        self.assertEqual(got.returncode, 0, got.stderr)
        prompt = runner.read_text(os.path.join(self.campaign, "trials", tid, "prompt.txt"))
        self.assertNotIn("recheck-v2", prompt)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertFalse(command["run_root_note"]["prompt_names_the_skill"])

    def test_the_two_conditions_get_the_same_prompt_bytes(self):
        other = self.make_campaign({"conditions": ["available", "absent"]})
        second, got = self.run_trial(condition="absent")
        self.assertEqual(got.returncode, 0, got.stderr)
        first = runner.read_text(os.path.join(self.record, "prompt.txt"))
        theirs = runner.read_text(os.path.join(self.campaign, "trials", second, "prompt.txt"))
        # the run directory and the opaque fixture path differ per trial; the job sentence does not
        self.assertEqual(first.splitlines()[0].split(" in ")[0],
                         theirs.splitlines()[0].split(" in ")[0])


class RefuseToOverwriteTest(RunnerCase):
    def test_a_used_trial_directory_is_exit_2(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        again = cli(["run", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 2, again.stdout)
        self.assertIn("used trial directory", again.stderr)

    def test_a_used_routing_directory_is_exit_2(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        first = cli(["routing", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(first.returncode, 0, first.stderr)
        again = cli(["routing", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 2, again.stdout)

    def test_stage_refuses_to_replace_a_stage_without_refresh(self):
        campaign = os.path.join(self.scratch, "stage-test")
        runner.Campaign(campaign).ensure()
        os.makedirs(os.path.join(campaign, "stage"))
        got = cli(["stage", "--campaign", campaign])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("already holds a stage", got.stderr)

    def test_probe_env_refuses_to_replace_a_probe_record_without_refresh(self):
        base = os.path.join(self.campaign, "probes", "claude-code-available")
        runner.write_json(os.path.join(base, "probe-20260915T000000Z.json"),
                          {"setup": "claude-code", "condition": "available", "ok": True})
        got = cli(["probe-env", "--campaign", self.campaign, "--setup", "claude-code",
                   "--home", "available"])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("already holds a probe record", got.stderr)

    def test_a_probe_record_is_never_replaced_even_with_refresh(self):
        """E10-43 (finding 7) and E10-53(5): `--refresh` runs another probe BESIDE the old one.

        The pre-E10-30 Codex probes were lost because `--refresh` removed the directory.
        """
        base = os.path.join(self.campaign, "probes", "claude-code-available")
        first = os.path.join(base, "probe-20260915T000000Z.json")
        runner.write_json(first, {"setup": "claude-code", "condition": "available", "ok": True})
        before = runner.read_text(first)
        cli(["probe-env", "--campaign", self.campaign, "--setup", "claude-code",
             "--home", "available", "--refresh"])
        self.assertEqual(runner.read_text(first), before,
                         "the earlier probe record was replaced")

    def test_rerun_keeps_the_failed_attempt_and_counts_it(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        again = cli(["rerun", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 0, again.stderr)
        document = parse_stdout(again)
        self.assertTrue(document["record"].endswith(os.path.join("attempts", "1")))
        # the first attempt's record is untouched
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "trials", tid,
                                                    "command.json")))
        lines = [json.loads(l) for l in
                 runner.read_text(os.path.join(self.campaign, "trials.jsonl")).splitlines() if l]
        self.assertEqual([l["attempt"] for l in lines], [0, 1])
        interruptions = runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"), "")
        self.assertIn("rerun asked for attempt 1", interruptions)

    def test_a_second_rerun_makes_attempt_two(self):
        tid, _ = self.run_trial()
        for expected in (1, 2):
            again = cli(["rerun", "--campaign", self.campaign, tid,
                         "--fake-launcher", self.fake_launcher("claude-code")])
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertTrue(parse_stdout(again)["record"].endswith(str(expected)))


class TimeoutTest(RunnerCase):
    """E9-41: 124 only when the child was still running when the limit was reached."""

    def test_a_child_that_finished_first_keeps_its_own_status_under_a_one_second_limit(self):
        step = runner.run_cmd([sys.executable, "-c", "import sys; sys.exit(7)"],
                              env=runner.tool_env(), timeout=1)
        self.assertFalse(step["timed_out"])
        self.assertEqual(step["exit"], 7)

    def test_a_child_still_running_at_the_limit_is_terminated_and_marked(self):
        started = time.time()
        step = runner.run_cmd([sys.executable, "-c", "import time; time.sleep(30)"],
                              env=runner.tool_env(), timeout=1)
        self.assertTrue(step["timed_out"])
        self.assertLess(time.time() - started, 20, "the child was not terminated promptly")

    def test_a_timed_out_trial_records_the_verdict(self):
        """Finding 25: the sleeping child comes from a stub launcher, not from an environment
        variable the runner's own allowlist (E10-7) strips before the launcher ever runs."""
        campaign = self.make_campaign({"timeouts": {"comparison": 1, "continuation": 1,
                                                    "routing": 1}})
        stub = self.stub_launcher("claude-code", "slow", sleep=30)
        tid, got = self.run_trial(launcher=stub)
        self.assertIn(got.returncode, (0, 1), got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertEqual(command["timeout_verdict"], "timed_out")
        self.assertEqual(command["status"], "timed_out")
        interruptions = runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"), "")
        self.assertIn("timed_out", interruptions)


class CredentialScanTest(RunnerCase):
    def test_a_planted_key_shape_in_a_capture_is_a_hit(self):
        capture = os.path.join(self.campaign, "trials", "fake", "harness", "trace.jsonl")
        runner.write_text(capture, '{"text": "sk-or-v1-%s"}\n' % ("a1b2c3d4" * 8))
        got = cli(["scan", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 1, got.stdout)
        self.assertIn("credential-shaped", got.stderr)

    def test_a_jwt_shape_and_a_bare_sk_shape_are_hits(self):
        # The shapes are assembled at run time rather than written as literals: this repo is
        # public, and a credential-shaped string checked into it is the very thing `scan`
        # exists to catch (it would flag this file on every run).
        jwt = ".".join(["ey" + "J" + "hbGciOiJIUzI1NiJ9", "ey" + "JzdWIiOiIxMjM0NTYifQ",
                        "abcdefghijk"])
        runner.write_text(os.path.join(self.campaign, "records", "a.txt"), jwt + "\n")
        runner.write_text(os.path.join(self.campaign, "records", "b.txt"),
                          "sk" + "-" + ("x" * 48) + "\n")
        got = cli(["scan", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 1, got.stdout)
        record = runner.read_json(sorted(
            __import__("glob").glob(os.path.join(self.campaign, "records", "scan*.json")))[-1])
        self.assertEqual(sorted({h["shape"] for h in record["hits"]}),
                         ["jwt", "provider-key"])

    def test_a_capture_with_a_leading_nul_is_scanned_anyway(self):
        """E10-52 (finding 24): a NUL in the first bytes no longer buys a free pass.

        `K_probe.py` planted a key in a capture with an initial NUL and the old scanner skipped
        the whole file for being "a compiled binary".
        """
        path = os.path.join(self.campaign, "trials", "fake", "harness", "capture.bin")
        runner.ensure_dir(os.path.dirname(path))
        with open(path, "wb") as handle:
            handle.write(b"\x00\x01\x02" + ("sk" + "-" + "y" * 60).encode("utf-8"))
        got = cli(["scan", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 1, got.stdout)
        record = runner.read_json(sorted(
            __import__("glob").glob(os.path.join(self.campaign, "records", "scan*.json")))[-1])
        self.assertEqual([h["shape"] for h in record["hits"]], ["provider-key"])
        self.assertGreaterEqual(record["files_with_a_nul_scanned_anyway"], 1)

    def test_an_assignment_delimiter_is_a_boundary(self):
        """Finding 24: `OPENROUTER_API_KEY=<key>` was missed because `=` counted as base64."""
        path = os.path.join(self.scratch, "assigned.txt")
        runner.write_text(path, "OPENROUTER_API_KEY=sk-or-v1-%s\n" % ("a1b2c3d4" * 8))
        result = runner.scan_paths([path])
        self.assertEqual([h["shape"] for h in result["hits"]], ["openrouter-key"])

    def test_a_key_shaped_run_inside_a_base64_blob_is_still_not_a_hit(self):
        """E10-37's classification is unchanged: the false hit sat in
        `/payload/encrypted_content` at verifier rollout line 26, mid-token in a base64 blob."""
        path = os.path.join(self.scratch, "blob.txt")
        runner.write_text(path, "AAAAsk-" + "b" * 60 + "CCCC\n")
        self.assertEqual(runner.scan_paths([path])["hits"], [])

    def test_claude_code_has_no_exempt_auth_store(self):
        """E10-52: Claude Code signs in through the Keychain, so a file named `auth.json` under
        its pilot home is a planted credential and is scanned like any other capture."""
        exempt = runner.auth_store_exemptions()
        for path in exempt:
            self.assertNotIn("skills-v2-pilot/claude-code", path)

    def test_a_clean_campaign_scans_clean_and_names_the_exempt_stores(self):
        tid, _ = self.run_trial()
        got = cli(["scan", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertTrue(document["ok"])
        self.assertGreater(document["files_scanned"], 5)
        self.assertIn("exempt_auth_stores", document)

    def test_only_the_setups_own_auth_stores_are_exempt_by_resolved_path(self):
        store = os.path.join(self.scratch, "auth.json")
        runner.write_text(store, "sk-or-v1-%s\n" % ("f" * 64))
        with_exempt = runner.scan_paths([store], exempt=[store])
        without = runner.scan_paths([store], exempt=[])
        self.assertEqual(with_exempt["hits"], [])
        self.assertEqual(len(without["hits"]), 1)
        self.assertNotIn("f" * 64, json.dumps(without["hits"]))

    def test_a_scan_hit_names_the_shape_and_the_offset_never_the_value(self):
        path = os.path.join(self.scratch, "c.txt")
        secret = "sk-or-v1-" + ("9" * 64)
        runner.write_text(path, "before %s after\n" % secret)
        result = runner.scan_paths([path])
        self.assertEqual(len(result["hits"]), 1)
        hit = result["hits"][0]
        self.assertEqual(hit["shape"], "openrouter-key")
        self.assertEqual(hit["offset"], 7)
        self.assertNotIn(secret, json.dumps(hit))


class ReportCountsTest(RunnerCase):
    """The report's counts reproduce from a small `trials.jsonl` written by hand."""

    def test_the_counts_come_from_the_lines_and_each_row_names_its_records(self):
        campaign = runner.Campaign(self.campaign)
        lines = [
            {"id": "claude-code-F1-01-fixed-clean-available-r1", "attempt": 0,
             "status": "complete", "exit": 0, "wall": 10.0, "cost": 0.1, "model": "m",
             "effort": "high", "activated": True, "record": "r1"},
            {"id": "claude-code-F1-01-fixed-clean-available-r2", "attempt": 0,
             "status": "no_result", "exit": 1, "wall": 20.0, "cost": 0.2, "model": "m",
             "effort": "high", "activated": False, "record": "r2"},
            {"id": "claude-code-F1-01-fixed-clean-absent-r1", "attempt": 0,
             "status": "complete", "exit": 0, "wall": 30.0, "cost": 0.3, "model": "m",
             "effort": "high", "activated": False, "record": "r3"},
        ]
        for line in lines:
            campaign.append_jsonl(campaign.trials_jsonl, line)
        for line in lines:
            command = {"setup": "claude-code", "condition":
                       "absent" if "absent" in line["id"] else "available",
                       "case": "F1-01-fixed-clean", "workspace": "/nowhere",
                       "status": line["status"]}
            runner.write_json(os.path.join(campaign.trials, line["id"], "command.json"), command)
        got = cli(["report", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertEqual(document["trials_seen"], 3)
        table = runner.read_json(os.path.join(self.campaign, "tables", "table.json"))
        self.assertEqual(table["trials_seen"], 3)
        self.assertEqual(table["sources"]["lines"], os.path.join(self.campaign, "trials.jsonl"))
        rows = {(r["setup"], r["condition"], r["activated"]): r for r in table["table"]}
        self.assertEqual(rows[("claude-code", "available", True)]["trials"], 1)
        self.assertEqual(rows[("claude-code", "available", False)]["no_result"], 1)
        self.assertEqual(rows[("claude-code", "absent", False)]["wall_seconds"], 30.0)
        self.assertAlmostEqual(rows[("claude-code", "available", True)]["cost_usd"], 0.1)
        for row in table["table"]:
            self.assertTrue(row["records"], "a row names no record")
        table = runner.read_text(os.path.join(self.campaign, "tables", "table.md"))
        self.assertIn("| setup | condition | activated |", table)
        # E10-43 (finding 7): the generated skeleton is a table, kept apart from the
        # operator's own `report.md`, which `report` never writes.
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "tables",
                                                    "report-skeleton.md")))
        self.assertFalse(os.path.isfile(os.path.join(self.campaign, "report.md")))


class CampaignResumeTest(RunnerCase):
    """E10-9: a restart skips every complete trial and reruns nothing on its own."""

    cases = (CASE,)
    conditions = ("available",)
    repetitions = 2

    def test_a_complete_trial_is_skipped_and_an_incomplete_one_is_not_rerun(self):
        plan = runner.Campaign(self.campaign).plan()
        first, second = plan["order"]["claude-code"]
        got = cli(["run", "--campaign", self.campaign, first,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        # an incomplete record: the directory exists, its command.json says timed_out
        record = os.path.join(self.campaign, "trials", second)
        os.makedirs(record)
        runner.write_json(os.path.join(record, "command.json"),
                          {"status": "timed_out", "setup": "claude-code",
                           "condition": "available", "case": CASE})
        status = parse_stdout(cli(["campaign", "status", "--campaign", self.campaign]))
        self.assertEqual(status["complete"], 1)
        # E10-9 and E10-15 together: a trial that RAN and ended badly is `recorded` with its
        # status, and the loop skips it; only a record with no terminal status is `partial`.
        self.assertEqual(status["recorded"], 2)
        self.assertEqual([r["id"] for r in status["recorded_with_a_failed_outcome"]], [second])
        self.assertEqual(status["partial_records"], [])
        loop = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                    "--skip-probe-gate", "--reopen-key",
                    "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(loop.returncode, 0, loop.stderr)
        document = parse_stdout(loop)
        self.assertIn(first, document["skipped"])
        self.assertIn(second, document["skipped"])
        # the incomplete record's own command.json is untouched
        self.assertEqual(runner.read_json(os.path.join(record, "command.json"))["status"],
                         "timed_out")
        interruptions = runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"), "")
        self.assertIn("a record already stands with status timed_out", interruptions)
        self.assertIn("rerun` is the operator's call", interruptions)

    def test_campaign_status_reports_the_next_trial_and_the_planned_count(self):
        status = parse_stdout(cli(["campaign", "status", "--campaign", self.campaign]))
        self.assertEqual(status["planned"], self.plan_document["counts"]["total"])
        self.assertEqual(status["complete"], 0)
        self.assertEqual(status["recorded"], 0)
        self.assertEqual(status["status"], "stopped")
        self.assertIsNotNone(status["next"])

    def test_campaign_stop_with_no_pid_file_says_so(self):
        document = parse_stdout(cli(["campaign", "stop", "--campaign", self.campaign]))
        self.assertFalse(document["stopped"])
        self.assertIn("campaign.pid", document["reason"])

    def test_campaign_start_refuses_while_a_pid_file_stands(self):
        runner.write_text(os.path.join(self.campaign, "campaign.pid"), "%d\n" % os.getpid())
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--skip-probe-gate"])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("campaign.pid", got.stderr)


if __name__ == "__main__":
    unittest.main()
