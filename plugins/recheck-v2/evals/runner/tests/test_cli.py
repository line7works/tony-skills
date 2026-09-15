"""The interface of A7a and E10-9: --help, JSON on stdout only, and every usage exit code."""
import json
import os
import unittest

from testlib import RunnerCase, cli, parse_stdout, RUNNER_DIR, runner

SUBCOMMANDS = ("stage", "install", "verify", "probe-env", "plan", "run", "rerun", "grade",
               "routing", "routing-score", "continuation", "campaign", "scan", "report", "check")


class HelpTest(unittest.TestCase):
    def test_top_level_help_exits_zero_and_lists_every_subcommand(self):
        got = cli(["--help"])
        self.assertEqual(got.returncode, 0, got.stderr)
        for name in SUBCOMMANDS:
            self.assertIn(name, got.stdout, "%s is not in --help" % name)

    def test_every_subcommand_answers_help(self):
        for name in SUBCOMMANDS:
            got = cli([name, "--help"])
            self.assertEqual(got.returncode, 0, "%s --help: %s" % (name, got.stderr))
            self.assertIn("usage:", got.stdout)

    def test_no_subcommand_is_a_usage_error_with_nothing_on_stdout(self):
        got = cli([])
        self.assertEqual(got.returncode, 2)
        self.assertEqual(got.stdout, "")
        self.assertIn("usage:", got.stderr)

    def test_an_unknown_subcommand_is_a_usage_error(self):
        got = cli(["nonesuch"])
        self.assertEqual(got.returncode, 2)
        self.assertEqual(got.stdout, "")


class UsageErrorTest(RunnerCase):
    def test_a_missing_campaign_flag_is_a_usage_error(self):
        for name in ("stage", "install", "verify", "plan", "report", "scan", "routing-score"):
            got = cli([name])
            self.assertEqual(got.returncode, 2, "%s without --campaign: %s" % (name, got.stdout))
            self.assertEqual(got.stdout, "")

    def test_a_campaign_with_no_campaign_json_is_exit_3(self):
        empty = os.path.join(self.scratch, "empty")
        os.makedirs(empty)
        got = cli(["report", "--campaign", empty])
        self.assertEqual(got.returncode, 3, got.stderr)
        self.assertIn("campaign.json", got.stderr)

    def test_a_campaign_with_no_stage_json_is_exit_3(self):
        empty = os.path.join(self.scratch, "empty2")
        os.makedirs(empty)
        runner.write_json(os.path.join(empty, "campaign.json"), {"setups": []})
        got = cli(["install", "--campaign", empty])
        self.assertEqual(got.returncode, 3, got.stderr)
        self.assertIn("stage.json", got.stderr)

    def test_a_trial_id_of_the_wrong_shape_is_a_usage_error(self):
        for bad in ("nonsense", "claude-code-F1-01-fixed-clean-available", "claude-code--r1",
                    "nosuchsetup-F1-01-fixed-clean-available-r1"):
            got = cli(["run", "--campaign", self.campaign, bad])
            self.assertEqual(got.returncode, 2, "%s: %s" % (bad, got.stdout))
            self.assertEqual(got.stdout, "")

    def test_routing_and_continuation_reject_a_comparison_id(self):
        tid = runner.trial_id("claude-code", "F1-01-fixed-clean", "available", 1)
        for name in ("routing", "continuation"):
            got = cli([name, "--campaign", self.campaign, tid])
            self.assertEqual(got.returncode, 2, "%s %s: %s" % (name, tid, got.stdout))

    def test_grade_with_no_trial_and_no_all_is_a_usage_error(self):
        got = cli(["grade", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 2)

    def test_grade_of_a_record_that_is_not_there_is_exit_3(self):
        got = cli(["grade", "--campaign", self.campaign,
                   runner.trial_id("claude-code", "F1-01-fixed-clean", "available", 1)])
        self.assertEqual(got.returncode, 3, got.stderr)

    def test_scan_of_a_path_that_is_not_there_is_exit_3(self):
        got = cli(["scan", "--campaign", self.campaign,
                   os.path.join(self.scratch, "nowhere")])
        self.assertEqual(got.returncode, 3, got.stderr)

    def test_campaign_takes_only_start_status_stop(self):
        got = cli(["campaign", "restart", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 2)

    def test_plan_refuses_to_overwrite_campaign_json_without_refresh(self):
        got = cli(["plan", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("already holds campaign.json", got.stderr)

    def test_plan_with_a_plan_file_that_is_not_there_is_exit_3(self):
        got = cli(["plan", "--campaign", self.campaign, "--refresh", "--plan",
                   os.path.join(self.scratch, "nowhere.json")])
        self.assertEqual(got.returncode, 3, got.stderr)

    def test_plan_rejects_a_case_no_generator_lists(self):
        path = os.path.join(self.scratch, "plan.json")
        plan = runner.default_plan("test")
        plan["cases"] = ["NOPE-01"]
        runner.write_json(path, plan)
        got = cli(["plan", "--campaign", self.campaign, "--refresh", "--plan", path])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("NOPE-01", got.stderr)

    def test_plan_rejects_a_plan_with_a_field_missing(self):
        path = os.path.join(self.scratch, "thin.json")
        runner.write_json(path, {"setups": [], "cases": []})
        got = cli(["plan", "--campaign", self.campaign, "--refresh", "--plan", path])
        self.assertEqual(got.returncode, 2, got.stdout)

    def test_plan_writes_campaign_json_with_the_order_and_the_counts(self):
        fresh = os.path.join(self.scratch, "fresh")
        runner.Campaign(fresh).ensure()
        runner.write_json(os.path.join(fresh, "stage.json"),
                          runner.read_json(os.path.join(self.campaign, "stage.json")))
        got = cli(["plan", "--campaign", fresh])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        # the full E10 default plan: 6 cases x 3 setups x 2 conditions x 2 repetitions
        self.assertEqual(document["counts"]["comparison"], 72)
        self.assertEqual(document["counts"]["continuation"], 6)
        self.assertEqual(len(document["order"]), 3)

    def test_stdout_is_one_json_document_and_nothing_else(self):
        got = cli(["campaign", "status", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 0, got.stderr)
        json.loads(got.stdout)
        self.assertEqual(got.stdout.count("\n"), got.stdout.rstrip("\n").count("\n") + 1)


class MissingBinaryTest(RunnerCase):
    def test_a_path_with_no_harness_binary_is_exit_3(self):
        environment = self.child_env({"PATH": "/nonexistent"})
        got = cli(["stage", "--campaign", os.path.join(self.scratch, "other"), "--refresh"],
                  env=environment)
        self.assertIn(got.returncode, (1, 3), got.stderr)


if __name__ == "__main__":
    unittest.main()
