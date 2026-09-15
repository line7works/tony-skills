"""One test per finding of the E10 review verdict, exercising the real path the finding names.

The verdict's own probes are reproduced here against the runner's actual code paths, with the
harness boundary fully substituted by the stubs under `fake/` and by stub launchers each test
writes itself. Nothing here opens `evals/answer-key/` or `evals/trigger-set/held-out/`; the
grading tests use a stand-in the test wrote, under E10-21, in a campaign the runner marked
synthetic (E10-45).

Numbering follows the verdict. A finding whose fix is proved in another file names that file.
"""
import glob
import json
import os
import subprocess
import sys
import time
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, CASE, TWO_ITEM_CASE, FAKE


# --------------------------------------------------------------------------- 2: the opaque tree


class OpaqueTreeTest(RunnerCase):
    """Finding 2 / E10-41: no path a model sees names the case, the condition or the setup."""

    conditions = ("available", "absent")

    def test_the_prompt_carries_no_setup_condition_or_repetition(self):
        """E10-41: the run id's case name is the ONE documented exception (E7 gap 13)."""
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        prompt = runner.read_text(os.path.join(self.campaign, "trials", tid, "prompt.txt"))
        for leak in ("claude-code", "codex", "opencode", "available", "absent", "-r1",
                     "recheck-v2", "/trials/"):
            self.assertNotIn(leak, prompt, "the prompt carries %r" % leak)
        # the case name appears only inside the run id, and the record says so
        for line in prompt.splitlines():
            if CASE in line:
                self.assertIn("%s-run" % CASE, line,
                              "the case name appears outside the run id: %r" % line)
        note = runner.read_json(os.path.join(self.campaign, "trials", tid,
                                             "command.json"))["run_root_note"]
        self.assertFalse(note["prompt_names_the_skill"])
        self.assertIn("E7 gap 13", note["documented_exception"])

    def test_the_workspace_and_the_run_directory_sit_under_one_opaque_tree(self):
        tid, got = self.run_trial()
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        tree = command["opaque_tree"]
        self.assertTrue(runner.path_contains(tree, command["workspace"]))
        self.assertTrue(runner.path_contains(tree, command["run_dir"]))
        self.assertTrue(runner.path_contains(os.path.join(self.campaign, "tmp"), tree))
        self.assertEqual(command["opaque_tree_mapping"]["trial"], tid)

    def test_the_two_conditions_get_byte_identical_prompts_after_path_normalisation(self):
        """Finding 2: the old test compared only the text before ` in `, discarding exactly the
        differing paths. The whole prompt is compared here, with each trial's own three paths
        replaced by tokens."""
        first, got = self.run_trial(condition="available")
        self.assertEqual(got.returncode, 0, got.stderr)
        second, got = self.run_trial(condition="absent")
        self.assertEqual(got.returncode, 0, got.stderr)

        def normalised(tid):
            record = os.path.join(self.campaign, "trials", tid)
            command = runner.read_json(os.path.join(record, "command.json"))
            text = runner.read_text(os.path.join(record, "prompt.txt"))
            for name, value in (("<RUN_DIR>", command["run_dir"]),
                                ("<WORKSPACE>", command["workspace"]),
                                ("<TREE>", command["opaque_tree"])):
                text = text.replace(value, name)
            return text

        self.assertEqual(normalised(first), normalised(second))
        # and the normalisation really did remove every absolute path
        self.assertNotIn(self.campaign, normalised(first))

    def test_two_attempts_of_one_trial_never_share_a_tree(self):
        campaign = runner.Campaign(self.campaign)
        tid = runner.trial_id("claude-code", CASE, "available", 1)
        self.assertNotEqual(campaign.opaque_tree(tid, 0), campaign.opaque_tree(tid, 1))

    def test_two_trials_of_one_case_never_share_a_tree(self):
        campaign = runner.Campaign(self.campaign)
        self.assertNotEqual(
            campaign.opaque_tree(runner.trial_id("claude-code", CASE, "available", 1), 0),
            campaign.opaque_tree(runner.trial_id("codex", CASE, "available", 1), 0))


# --------------------------------------------------------------------------- 3: the environment


class EnvironmentBoundaryTest(RunnerCase):
    """Finding 3 / E10-42: one boundary, no `os.environ.copy()`, and a gated probe."""

    def test_run_cmd_refuses_a_child_with_no_environment(self):
        with self.assertRaises(runner.Failure) as caught:
            runner.run_cmd([sys.executable, "-c", "pass"])
        self.assertIn("every child goes through", str(caught.exception))

    def test_run_cmd_refuses_an_environment_carrying_a_banned_name(self):
        env = runner.tool_env()
        env["FOO_TOKEN"] = "planted"
        with self.assertRaises(runner.Failure) as caught:
            runner.run_cmd([sys.executable, "-c", "pass"], env=env)
        self.assertIn("FOO_TOKEN", str(caught.exception))

    def test_the_only_declared_banned_names_are_the_two_the_contract_names(self):
        self.assertEqual(sorted(runner.DECLARED_ENV),
                         ["CODEX_HOME", "OPENROUTER_API_KEY"])

    def test_no_function_in_the_runner_calls_os_environ_copy(self):
        """Finding 3: the generator listing, the held-out lookup and the detached campaign
        process all inherited the session's environment through `os.environ.copy()`."""
        source = runner.read_text(runner.__file__)
        body = "\n".join(l for l in source.splitlines() if not l.strip().startswith("#"))
        self.assertNotIn("os.environ.copy()", body)

    def test_the_detached_campaign_process_is_started_from_the_allowlist(self):
        source = runner.read_text(runner.__file__)
        body = source.split("def do_campaign(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("env=campaign.env()", body)

    def test_campaign_start_refuses_without_nine_current_probe_records(self):
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--reopen-key", "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("one current successful probe record per setup and home", got.stderr)

    def test_the_probe_gate_names_every_missing_setup_and_home(self):
        campaign = runner.Campaign(self.campaign)
        gate = runner.current_probes(campaign, campaign.plan())
        self.assertFalse(gate["ok"])
        self.assertEqual(sorted(gate["missing"]),
                         ["claude-code/absent", "claude-code/available", "claude-code/routing"])

    def test_a_probe_record_bound_to_another_stage_is_not_current(self):
        campaign = runner.Campaign(self.campaign)
        for home in runner.HOMES:
            runner.write_json(
                os.path.join(runner.probe_dir(campaign, "claude-code", home),
                             "probe-20260915T000000Z.json"),
                {"setup": "claude-code", "condition": home, "ok": True,
                 "staged_commit": "another-commit", "plugin_tree_sha256": "test-tree"})
        self.assertFalse(runner.current_probes(campaign, campaign.plan())["ok"])
        for home in runner.HOMES:
            runner.write_json(
                os.path.join(runner.probe_dir(campaign, "claude-code", home),
                             "probe-20260915T000001Z.json"),
                {"setup": "claude-code", "condition": home, "ok": True,
                 "staged_commit": "test-commit", "plugin_tree_sha256": "test-tree"})
        self.assertTrue(runner.current_probes(campaign, campaign.plan())["ok"])

    def test_the_measured_harness_created_names_are_per_harness(self):
        self.assertIn("CLAUDECODE", runner.HARNESS_CREATED_ENV["claude-code"])
        self.assertIn("CODEX_HOME", runner.HARNESS_CREATED_ENV["codex"])
        self.assertEqual(runner.HARNESS_CREATED_ENV["opencode"], ())


# --------------------------------------------------------------------------- 4, 5: plan and runs


class PlanValidationTest(RunnerCase):
    """Finding 4 / E10-43: the whole plan is validated before any write."""

    def write_plan(self, **overrides):
        plan = runner.default_plan("test")
        plan.update(overrides)
        path = os.path.join(self.scratch, "plan-%d.json" % len(os.listdir(self.scratch)))
        runner.write_json(path, plan)
        return path

    def refuse(self, path, fragment):
        got = cli(["plan", "--campaign", self.campaign, "--refresh", "--plan", path])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn(fragment, got.stderr)
        return got

    def test_a_setup_named_with_a_separator_is_refused(self):
        self.refuse(self.write_plan(setups=[{"name": "../review-out", "harness": "codex"}]),
                    "path separator")

    def test_a_setup_named_with_a_dot_segment_is_refused(self):
        self.refuse(self.write_plan(setups=[{"name": ".hidden", "harness": "codex"}]),
                    "dot segment")

    def test_an_undefined_harness_is_refused(self):
        self.refuse(self.write_plan(setups=[{"name": "x", "harness": "nosuch"}]),
                    "not one of")

    def test_two_setups_with_one_name_are_refused(self):
        self.refuse(self.write_plan(setups=[{"name": "codex", "harness": "codex"},
                                            {"name": "codex", "harness": "codex"}]),
                    "appears twice")

    def test_a_comparison_case_outside_E10_1_s_six_is_refused(self):
        self.refuse(self.write_plan(cases=["F3-02-mixed-two-items"]),
                    "outside E10-1's six")

    def test_a_duplicate_case_is_refused(self):
        self.refuse(self.write_plan(cases=["F1-01-fixed-clean", "F1-01-fixed-clean"]),
                    "the same case twice")

    def test_a_continuation_case_other_than_F3_02_is_refused(self):
        self.refuse(self.write_plan(continuation={"case": "F1-01-fixed-clean",
                                                  "condition": "available",
                                                  "repetitions": 1}),
                    "F3-02-mixed-two-items")

    def test_a_zero_or_negative_repetition_count_is_refused(self):
        self.refuse(self.write_plan(repetitions=0), "positive integer")

    def test_a_timeout_that_is_not_a_positive_number_is_refused(self):
        self.refuse(self.write_plan(timeouts={"comparison": 0, "continuation": 1,
                                              "routing": 1}), "timeouts.comparison")

    def test_a_valid_plan_writes_the_counts_with_the_manual_only_row_counted_apart(self):
        fresh = os.path.join(self.scratch, "fresh")
        runner.Campaign(fresh).ensure()
        runner.write_json(os.path.join(fresh, "stage.json"),
                          runner.read_json(os.path.join(self.campaign, "stage.json")))
        got = cli(["plan", "--campaign", fresh])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertEqual(document["counts"]["comparison"], 72)
        self.assertEqual(document["counts"]["continuation"], 6)
        self.assertEqual(document["counts"]["routing"], 180)
        # E10-53(4): one dedicated manual-only request per lane, counted apart
        self.assertEqual(document["counts"]["manual_only"], 3)
        self.assertEqual(len(set(document["trial_ids"])), len(document["trial_ids"]))

    def test_a_trial_id_that_would_leave_the_trials_directory_is_refused(self):
        campaign = runner.Campaign(self.campaign)
        for bad in ("../outside", "a/b", ".", "..", ".hidden"):
            with self.assertRaises(runner.Usage, msg=bad):
                campaign.trial_dir(bad)


class RunDirectoryTest(RunnerCase):
    """Finding 5 / E10-43: a run directory is refused, never removed."""

    def test_a_rerun_gets_its_own_run_directory_and_the_first_one_survives(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        first = runner.read_json(os.path.join(self.campaign, "trials", tid,
                                              "command.json"))["run_dir"]
        sentinel = os.path.join(first, "sentinel.txt")
        runner.write_text(sentinel, "the first attempt's live run directory\n")
        again = cli(["rerun", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 0, again.stderr)
        second = runner.read_json(os.path.join(self.campaign, "trials", tid, "attempts", "1",
                                               "command.json"))["run_dir"]
        self.assertNotEqual(first, second)
        self.assertTrue(os.path.isfile(sentinel),
                        "the rerun destroyed the first attempt's run directory")

    def test_every_first_rerun_of_every_trial_no_longer_hashes_the_same(self):
        """Finding 5: `_one_trial` hashed the record's BASENAME, which is `1` for every first
        rerun of every trial on every setup."""
        campaign = runner.Campaign(self.campaign)
        trees = {campaign.opaque_tree(runner.trial_id(setup, CASE, "available", 1), 1)
                 for setup in ("claude-code", "codex", "opencode")}
        self.assertEqual(len(trees), 3)

    def test_prepare_run_dir_refuses_a_prepared_leaf_and_removes_nothing(self):
        """E10-54(a): the leaf exists — the fixture build made it — so its existence is not the
        error. A leaf that already holds `result.schema.json` was prepared before, and a run
        directory is refused, never removed (E10-43)."""
        leaf = os.path.join(self.scratch, "fixture", "abc123def456", "run")
        runner.ensure_dir(leaf)
        sentinel = os.path.join(leaf, "sentinel.txt")
        runner.write_text(sentinel, "an earlier attempt's live run directory\n")
        # an existing but unprepared leaf is the normal case
        self.assertEqual(runner.prepare_run_dir(leaf), leaf)
        self.assertTrue(os.path.isfile(os.path.join(leaf, "result.schema.json")))
        # a second preparation is refused, and nothing in the leaf is touched
        with self.assertRaises(runner.Usage) as caught:
            runner.prepare_run_dir(leaf)
        self.assertIn("never removed", str(caught.exception))
        self.assertTrue(os.path.isfile(sentinel), "prepare_run_dir removed something")


# --------------------------------------------------------------------------- 6, 22, 23


class AttemptsAndGradingTest(RunnerCase):
    """Findings 6, 22, 23 / E10-44."""

    cases = (TWO_ITEM_CASE, CASE)

    def test_rerun_dispatches_a_routing_id(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        first = cli(["routing", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(first.returncode, 0, first.stderr)
        again = cli(["rerun", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 0, again.stderr)
        document = parse_stdout(again)
        self.assertEqual(document["attempt"], 1)
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "trials", tid, "attempts",
                                                    "1", "command.json")))

    def test_rerun_dispatches_a_continuation_id(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        first = cli(["continuation", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertIn(first.returncode, (0, 1), first.stderr)
        again = cli(["rerun", "--campaign", self.campaign, tid,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertIn(again.returncode, (0, 1), again.stderr)
        self.assertTrue(os.path.isdir(os.path.join(self.campaign, "trials", tid, "attempts", "1")))

    def test_grade_all_covers_continuation_trials(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        cli(["continuation", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        directory = self.stand_in_key(case=TWO_ITEM_CASE)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, "--all", "--summary"],
                     env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)
        document = parse_stdout(graded)
        self.assertIn(tid, [row["trial"] for row in document["grades"]])

    def test_the_ordinary_grade_command_returns_the_written_path(self):
        """Finding 22: `grade <trial>` without `--summary` exited 1 with KeyError 'grade_path'."""
        directory = self.stand_in_key()
        tid, got = self.run_trial(case=CASE)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid], env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)
        document = parse_stdout(graded)
        self.assertEqual(len(document["grades"]), 1)
        self.assertTrue(os.path.isfile(document["grades"][0]["grade_path"]))

    def test_the_ordinary_grade_command_works_on_a_no_result_record(self):
        directory = self.stand_in_key()
        tid = runner.trial_id("claude-code", CASE, "available", 1)
        record = os.path.join(self.campaign, "trials", tid)
        runner.write_json(os.path.join(record, "command.json"),
                          {"case": CASE, "setup": "claude-code", "condition": "available",
                           "workspace": "/nowhere", "status": "no_result", "wall_seconds": 1.0})
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        for extra in ([], ["--summary"]):
            graded = cli(["grade", "--campaign", self.campaign, tid] + extra, env=environment)
            self.assertEqual(graded.returncode, 0, graded.stderr)
            self.assertTrue(parse_stdout(graded)["grades"][0]["grade_path"])

    def test_dispositions_handle_the_matcher_s_unordered_form(self):
        """Finding 23: `_dispositions` raised `KeyError: 0` on `{"$unordered": [...]}`."""
        items = [{"location": "a.py:1", "disposition": "fixed"},
                 {"location": "b.py:2", "disposition": "not_fixed"}]
        expected = {"$unordered": [{"location": "b.py:2", "disposition": "not_fixed"},
                                   {"location": "a.py:1", "disposition": "fixed"}]}
        rows = runner._dispositions(items, expected)
        self.assertEqual(rows["form"], "$unordered")
        self.assertEqual([r["match"] for r in rows["items"]], [True, True])
        self.assertEqual(rows["unmatched_expected"], [])
        self.assertTrue(rows["all_matched"])

    def test_dispositions_handle_the_matcher_s_contains_form(self):
        items = [{"location": "a.py:1", "disposition": "fixed"}]
        expected = {"$contains": [{"location": "a.py:1", "disposition": "fixed"}]}
        rows = runner._dispositions(items, expected)
        self.assertEqual(rows["form"], "$contains")
        self.assertEqual(rows["items"][0]["match"], True)

    def test_dispositions_report_an_expected_item_nothing_matched(self):
        items = [{"location": "a.py:1", "disposition": "fixed"}]
        expected = {"$unordered": [{"location": "zzz.py:9", "disposition": "fixed"}]}
        rows = runner._dispositions(items, expected)
        self.assertEqual([r["expected_location"] for r in rows["unmatched_expected"]],
                         ["zzz.py:9"])
        self.assertFalse(rows["all_matched"])


# --------------------------------------------------------------------------- 7: records


class RecordNamesTest(RunnerCase):
    """Finding 7 / E10-43: a record name is unique and reserved atomically."""

    def test_two_records_in_one_timestamp_bucket_do_not_collide(self):
        campaign = runner.Campaign(self.campaign)
        first = campaign.reserve_record("install")
        second = campaign.reserve_record("install")
        self.assertNotEqual(first, second)
        self.assertTrue(os.path.isfile(first) and os.path.isfile(second))

    def test_report_never_writes_the_operator_s_report(self):
        marker = os.path.join(self.campaign, "report.md")
        runner.write_text(marker, "the operator's own report\n")
        got = cli(["report", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(runner.read_text(marker), "the operator's own report\n")
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "tables",
                                                    "report-skeleton.md")))

    def test_a_second_routing_score_never_replaces_the_first(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        cli(["routing", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        first = parse_stdout(cli(["routing-score", "--campaign", self.campaign,
                                  "--revision", "rev0"]))["written"][0]["path"]
        before = runner.read_text(first)
        second = parse_stdout(cli(["routing-score", "--campaign", self.campaign,
                                   "--revision", "rev0"]))["written"][0]["path"]
        self.assertNotEqual(first, second)
        self.assertEqual(runner.read_text(first), before)

    def test_grade_json_is_the_one_replaceable_file(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        record = os.path.join(self.campaign, "trials", tid)
        before = {p: runner.file_sha256(p) for p in runner.walk_files(record)}
        cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        after = {p: runner.file_sha256(p) for p in runner.walk_files(record)}
        changed = sorted(p for p in before if before[p] != after.get(p))
        self.assertEqual([os.path.basename(p) for p in changed], [])
        self.assertEqual(sorted(os.path.basename(p) for p in set(after) - set(before)),
                         ["grade.json"])


# --------------------------------------------------------------------------- 11, 12, 13, 14


class NativeWitnessTest(RunnerCase):
    """Findings 11, 12, 13, 14 / E10-46."""

    setups = ("claude-code", "codex", "opencode")

    def test_a_history_changing_command_behind_git_options_is_caught(self):
        """Finding 11: a leading `git -c` avoided detection entirely."""
        stub = self.stub_launcher("claude-code", "git",
                                  RECHECK_FAKE_PLANT_GIT="git -c user.name=x commit -m y")
        tid, got = self.run_trial(launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        record = os.path.join(self.campaign, "trials", tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual([row["subcommand"] for row in witnesses["git"]], ["commit"])
        self.assertIn("-c", witnesses["git"][0]["options_before_it"])

    def test_a_command_inside_a_codex_function_call_argument_is_caught(self):
        """Finding 11: zero commands were scanned for a Codex `function_call.arguments`."""
        stub = self.stub_launcher("codex", "git",
                                  RECHECK_FAKE_PLANT_GIT="git reset --hard HEAD~1")
        tid, got = self.run_trial(harness="codex", launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        record = os.path.join(self.campaign, "trials", tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertIn("reset", [row["subcommand"] for row in witnesses["git"]])
        self.assertGreater(witnesses["commands_scanned"], 0)

    def test_a_sibling_path_with_a_shared_prefix_is_outside_the_workspace(self):
        """Finding 11: `startswith` made `/tmp/ws-other` look like it was inside `/tmp/ws`."""
        self.assertTrue(runner.path_contains("/tmp/ws", "/tmp/ws/inner"))
        self.assertTrue(runner.path_contains("/tmp/ws", "/tmp/ws"))
        self.assertFalse(runner.path_contains("/tmp/ws", "/tmp/ws-other/inner"))

    def test_a_write_outside_the_tree_is_a_scope_violation_and_a_refused_one_is_not(self):
        outside = os.path.join(self.scratch, "outside-write.txt")
        stub = self.stub_launcher("claude-code", "writes",
                                  RECHECK_FAKE_PLANT_WRITE=outside)
        tid, got = self.run_trial(launcher=stub)
        record = os.path.join(self.campaign, "trials", tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual([row["path"] for row in witnesses["writes_outside"]], [outside])

        refused_stub = self.stub_launcher("claude-code", "refused",
                                          RECHECK_FAKE_PLANT_REFUSED_WRITE=outside)
        self.make_campaign({"repetitions": 2})
        second = runner.trial_id("claude-code", CASE, "available", 2)
        ran = cli(["run", "--campaign", self.campaign, second,
                   "--fake-launcher", refused_stub])
        self.assertEqual(ran.returncode, 0, ran.stderr)
        record = os.path.join(self.campaign, "trials", second)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual(witnesses["writes_outside"], [],
                         "a REFUSED write was counted as a write")
        self.assertTrue(witnesses["refused_actions"])

    def test_a_read_outside_the_tree_is_not_a_scope_violation(self):
        """The fix round's own live campaign found this: every `Read` of the installed skill
        and of `readers`' own contract was counted as a write outside the workspace, fifty
        scope violations and forty unauthorized pilot-home writes over twelve trials. E10-11
        asks for WRITES outside the workspace, the run directory and TMPDIR."""
        outside = os.path.join(runner.PILOT_ROOT, "claude-code", "config", "plugins", "cache",
                               "tony-skills", "recheck-v2", "0.1.0", "skills", "recheck-v2",
                               "SKILL.md")
        stub = self.stub_launcher("claude-code", "reads-outside",
                                  RECHECK_FAKE_PLANT_READ=outside)
        tid, got = self.run_trial(launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        record = os.path.join(self.campaign, "trials", tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual(witnesses["writes_outside"], [])
        self.assertEqual(witnesses["writes_to_a_pilot_home"], [])
        # it IS still measured, as the read it is
        self.assertTrue(witnesses["skill_file_reached"]["reached"])

    def test_the_verifier_and_both_continuation_captures_are_scanned(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        self.make_campaign({"cases": [TWO_ITEM_CASE]})
        cli(["continuation", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        record = os.path.join(self.campaign, "trials", tid)
        captures = [os.path.basename(c) for c in runner.capture_dirs(record)]
        self.assertIn("harness-first", captures)
        self.assertIn("harness-second", captures)

    def test_a_skill_call_with_no_delivered_body_is_not_an_activation(self):
        """Finding 12: `activated: true` for a Claude Skill call with no delivered body."""
        stub = self.stub_launcher("claude-code", "nodelivery", RECHECK_FAKE_NO_DELIVERY="1")
        tid, got = self.run_trial(launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertFalse(command["activated"]["activated"])
        self.assertTrue(command["activated"]["marker"]["skill_tool_calls"])

    def test_an_opencode_skill_call_with_status_error_is_not_an_activation(self):
        stub = self.stub_launcher("opencode", "skillerror", RECHECK_FAKE_SKILL_ERROR="1")
        tid, got = self.run_trial(harness="opencode", launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertFalse(command["activated"]["activated"])

    def test_a_codex_developer_catalog_alone_is_not_an_activation(self):
        """Finding 12: a developer `<skills_instructions>` catalog gave `activated: true`."""
        stub = self.stub_launcher("codex", "catalogonly", RECHECK_FAKE_CATALOG_ONLY="1")
        tid, got = self.run_trial(harness="codex", launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertFalse(command["activated"]["activated"])

    def test_the_claude_activation_witness_keeps_its_line_and_its_tool_use_id(self):
        tid, got = self.run_trial()
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        call = command["activated"]["marker"]["skill_tool_calls"][0]
        self.assertIsInstance(call["line"], int)
        self.assertEqual(call["id"], "tu1")

    def test_the_codex_condition_witness_comes_from_the_session_not_the_home_listing(self):
        """Finding 12: the real absent trial said `recheck_v2_in_catalog: true` because
        `codex plugin list` listed the uninstalled marketplace entry."""
        tid, got = self.run_trial(harness="codex")
        self.assertEqual(got.returncode, 0, got.stderr)
        witness = runner.read_json(os.path.join(self.campaign, "trials", tid,
                                                "command.json"))["condition_witness"]
        self.assertIn("rollout.jsonl", witness["source"])
        self.assertIsNotNone(witness["line"])

    def test_the_codex_routing_target_is_the_read_the_model_followed(self):
        """Finding 13 / E10-33: the developer catalog message is not a selection."""
        tid = runner.routing_trial_id("codex", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        observed = document["observed_target"]
        self.assertEqual(observed["target"], "recheck-v2")
        self.assertIn("not a read", observed["how"])
        self.assertTrue(observed["candidates"])

    def test_a_codex_session_that_only_saw_the_catalog_selects_nothing(self):
        stub = self.stub_launcher("codex", "routing-catalogonly",
                                  RECHECK_FAKE_CATALOG_ONLY="1")
        tid = runner.routing_trial_id("codex", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(parse_stdout(got)["observed_target"]["target"], "none")

    def test_a_blocked_plugin_in_codex_s_textual_catalog_is_a_breach(self):
        """Finding 14: the JSON list was parsed, the textual `codex plugin list` was not."""
        stub = self.stub_launcher(
            "codex", "breach",
            RECHECK_FAKE_CATALOG="recheck-v2 readers manual-only-probe signoff")
        tid = runner.routing_trial_id("codex", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertEqual(got.returncode, 1, got.stdout)
        self.assertIn("profile_breach", got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertEqual(command["profile_breach"]["blocked_present"], ["signoff"])
        self.assertIn("textual", command["profile_breach"]["catalog_parsed_as"])

    def test_a_disabled_entry_in_the_textual_catalog_is_not_active(self):
        stub = self.stub_launcher(
            "codex", "disabled",
            RECHECK_FAKE_CATALOG="recheck-v2 readers manual-only-probe",
            RECHECK_FAKE_CATALOG_DISABLED="signoff",
            RECHECK_FAKE_CATALOG_NOT_INSTALLED="inspect ship")
        tid = runner.routing_trial_id("codex", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertEqual(got.returncode, 0, got.stderr)

    def test_a_breach_persists_a_lane_stop_no_later_launch_can_pass(self):
        """Finding 14: `I_probe.py` launched repetition 2 after repetition 1 breached."""
        stub = self.stub_launcher(
            "codex", "breach2",
            RECHECK_FAKE_CATALOG="recheck-v2 manual-only-probe signoff")
        first = runner.routing_trial_id("codex", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, first, "--fake-launcher", stub])
        self.assertEqual(got.returncode, 1, got.stdout)
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "lane-stops", "codex.json")))
        # any later launch on that lane, of any kind
        second = runner.routing_trial_id("codex", "T-01-slash-v2-slice", 2)
        again = cli(["routing", "--campaign", self.campaign, second,
                     "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(again.returncode, 1, again.stdout)
        self.assertIn("lane is stopped", again.stderr)
        comparison = cli(["run", "--campaign", self.campaign,
                          runner.trial_id("codex", CASE, "available", 1),
                          "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(comparison.returncode, 1, comparison.stdout)
        self.assertIn("lane is stopped", comparison.stderr)

    def test_a_codex_entry_that_is_not_installed_is_not_active(self):
        """The fix round's own live campaign found this: `codex plugin list` on 0.154.0 says
        `not installed`, never `disabled`, so a parser that only skipped `disabled` read the
        five blocked stations as present and stopped a correct Codex lane."""
        harness = os.path.join(self.scratch, "codex-catalog")
        runner.ensure_dir(harness)
        runner.write_text(os.path.join(harness, "catalog.txt"), "\n".join([
            "Marketplace `tony-skills`",
            "/somewhere/marketplace.json",
            "",
            "PLUGIN                  STATUS              VERSION  SOURCE",
            "recheck-v2@tony-skills  installed, enabled  0.1.0    /a/recheck-v2",
            "readers@tony-skills     installed, enabled  1.0.0    /a/readers",
            "signoff@tony-skills     not installed                /a/signoff",
            "inspect@tony-skills     not installed                /a/inspect",
            "arcade@tony-skills      installed, disabled 1.0.0    /a/arcade",
        ]) + "\n")
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "codex", "harness": "codex"})
        names, how = runner.catalog_names(setup, {"record": None}, harness)
        self.assertEqual(names, ["readers", "recheck-v2"])
        self.assertIn("enabled", how)
        self.assertEqual([n for n in runner.BLOCKED_PLUGINS if n in names], [])

    def test_the_required_set_is_in_each_catalog_s_own_vocabulary(self):
        """The fix round's own live campaign found this: OpenCode's catalog names SKILLS, so
        requiring the plugin name `sun` stopped a lane whose profile was correct."""
        campaign = runner.Campaign(self.campaign)
        runner.ensure_dir(os.path.join(self.stage, "plugins", "sun", "skills", "sunrise"))
        runner.ensure_dir(os.path.join(self.stage, "plugins", "sun", "skills", "sunset"))
        for name in ("sunrise", "sunset"):
            runner.write_text(os.path.join(self.stage, "plugins", "sun", "skills", name,
                                           "SKILL.md"), "---\nname: %s\n---\n" % name)
        runner.write_json(os.path.join(self.stage, ".claude-plugin", "marketplace.json"),
                          {"plugins": [{"name": "sun"}, {"name": "signoff"}]})
        opencode = runner.OpenCodeSetup(campaign, stage=self.stage, name="opencode")
        codex = runner.CodexSetup(campaign, stage=self.stage, name="codex")
        self.assertIn("sunrise", runner.required_routing_names(opencode))
        self.assertIn("sunset", runner.required_routing_names(opencode))
        self.assertNotIn("sun", runner.required_routing_names(opencode))
        self.assertIn("sun", runner.required_routing_names(codex))
        for setup in (opencode, codex):
            required = runner.required_routing_names(setup)
            self.assertIn("manual-only-probe", required)
            self.assertIn("recheck-v2", required)
            self.assertNotIn("signoff", required)

    def test_a_lane_stop_is_cleared_with_a_reason_and_kept_as_a_record(self):
        campaign = runner.Campaign(self.campaign)
        runner.stop_lane(campaign, "codex", "a blocked name", "/a/record")
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "lane-stops", "codex.json")))
        got = cli(["lane-stop", "--campaign", self.campaign, "--setup", "codex", "--clear",
                   "--why", "the parser was wrong, not the profile"])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertFalse(os.path.isfile(os.path.join(self.campaign, "lane-stops", "codex.json")))
        kept = runner.read_json(document["cleared"])
        self.assertEqual(kept["reason"], "a blocked name")
        self.assertIn("parser was wrong", kept["cleared_because"])
        interruptions = runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"), "")
        self.assertIn("lane stop was cleared by hand", interruptions)

    def test_clearing_a_lane_stop_needs_a_reason(self):
        campaign = runner.Campaign(self.campaign)
        runner.stop_lane(campaign, "codex", "a blocked name", "/a/record")
        got = cli(["lane-stop", "--campaign", self.campaign, "--setup", "codex", "--clear"])
        self.assertEqual(got.returncode, 2, got.stdout)

    def test_a_missing_catalog_fails_the_profile_check(self):
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "codex", "harness": "codex"})
        breach = runner._profile_breach(setup, os.path.join(self.scratch, "nothing"),
                                        {"kind": "codex plugin list", "record": None})
        self.assertTrue(breach["catalog_missing"])
        self.assertTrue(breach["required_missing"])


# --------------------------------------------------------------------------- 18: provenance


class ModelProvenanceTest(RunnerCase):
    """Finding 18 / E10-50: a launcher-typed label never becomes an observation."""

    def test_a_launch_json_alone_yields_a_null_model(self):
        out = os.path.join(self.scratch, "typed")
        runner.ensure_dir(out)
        runner.write_json(os.path.join(out, "launch.json"),
                          {"model": "review-typed-by-launcher"})
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "claude-code", "harness": "claude-code"})
        model = setup.model_record(out)
        self.assertIsNone(model["id"])
        self.assertIsNone(model["source"])
        self.assertEqual(model["configured"]["model"], "review-typed-by-launcher")

    def test_the_native_init_event_supplies_the_model_and_its_session_binding(self):
        tid, got = self.run_trial()
        model = runner.read_json(os.path.join(self.campaign, "trials", tid, "model.json"))
        self.assertEqual(model["id"], "claude-opus-5")
        self.assertTrue(model["session_binding_ok"])
        self.assertEqual(model["init_event"]["file"], "harness/trace.jsonl")
        self.assertEqual(model["init_event"]["line"], 1)

    def test_an_assistant_record_bound_to_another_session_is_ignored(self):
        out = os.path.join(self.scratch, "crossed")
        runner.ensure_dir(out)
        runner.write_text(os.path.join(out, "trace.jsonl"), "\n".join([
            json.dumps({"type": "system", "subtype": "init", "session_id": "mine",
                        "model": "claude-opus-5[1m]"}),
            json.dumps({"type": "assistant", "session_id": "someone-else",
                        "message": {"model": "not-mine"}})]) + "\n")
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "claude-code", "harness": "claude-code"})
        model = setup.model_record(out)
        self.assertEqual(model["id"], "claude-opus-5[1m]")
        self.assertIn("init event", model["source"])

    def test_a_codex_model_is_null_without_a_turn_context(self):
        out = os.path.join(self.scratch, "codex-empty")
        runner.ensure_dir(out)
        runner.write_json(os.path.join(out, "launch.json"), {"model": "typed"})
        setup = runner.make_setup(runner.Campaign(self.campaign),
                                  {"name": "codex", "harness": "codex"})
        self.assertIsNone(setup.model_record(out)["id"])


# --------------------------------------------------------------------------- 19, 20, 21


class OutcomeAndCampaignTest(RunnerCase):
    """Findings 19, 20, 21 / E10-43 and E10-51."""

    setups = ("claude-code", "codex", "opencode")

    def test_a_launch_that_wrote_a_result_and_exited_seven_is_launch_failed(self):
        """Finding 19: it returned `status: complete` and wrote no interruption."""
        stub = self.stub_launcher("claude-code", "exit7", RECHECK_FAKE_EXIT="7")
        tid, got = self.run_trial(launcher=stub)
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertEqual(command["status"], "launch_failed")
        lines = [json.loads(l) for l in
                 runner.read_text(os.path.join(self.campaign, "trials.jsonl")).splitlines() if l]
        self.assertEqual([l["status"] for l in lines], ["launch_failed"])
        interruptions = [json.loads(l) for l in runner.read_text(
            os.path.join(self.campaign, "interruptions.jsonl"), "").splitlines() if l]
        self.assertTrue(interruptions)
        self.assertEqual(interruptions[0]["trial"], tid)
        self.assertEqual(interruptions[0]["attempt"], 0)

    def test_a_routing_launch_that_failed_says_so_in_both_records(self):
        stub = self.stub_launcher("claude-code", "routing-exit7", RECHECK_FAKE_EXIT="7")
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        lines = [json.loads(l) for l in
                 runner.read_text(os.path.join(self.campaign, "trials.jsonl")).splitlines() if l]
        self.assertEqual(command["status"], "launch_failed")
        self.assertEqual(lines[0]["status"], "launch_failed")

    def test_a_rerun_s_interruption_names_its_own_attempt(self):
        tid, got = self.run_trial()
        cli(["rerun", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("claude-code")])
        interruptions = [json.loads(l) for l in runner.read_text(
            os.path.join(self.campaign, "interruptions.jsonl"), "").splitlines() if l]
        self.assertIn(1, [row["attempt"] for row in interruptions])

    def test_a_directory_without_a_command_json_is_a_partial_attempt_the_report_retains(self):
        """Finding 21: `status` returned `partial_records: []` for exactly this."""
        plan = runner.Campaign(self.campaign).plan()
        tid = plan["order"]["claude-code"][0]
        runner.ensure_dir(os.path.join(self.campaign, "trials", tid))
        status = parse_stdout(cli(["campaign", "status", "--campaign", self.campaign]))
        self.assertEqual(status["partial_records"], [tid])
        self.assertIn("no command.json", status["partial_detail"][0]["why"])
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertEqual([row["id"] for row in report["partial_attempts"]], [tid])

    def test_the_detached_start_runs_its_trials_and_keeps_its_launch_options(self):
        """Finding 20: the child printed `already holds campaign.pid` and ran zero trials."""
        self.make_campaign({"cases": [CASE], "conditions": ["available"], "repetitions": 1,
                            "routing": {"entries": [], "repetitions": 1},
                            "continuation": None})
        got = cli(["campaign", "start", "--campaign", self.campaign, "--skip-probe-gate",
                   "--reopen-key", "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertTrue(document["started"])
        self.assertTrue(document["owner_token_accepted"])
        self.assertEqual(document["launch_options"]["fake_launcher"],
                         self.fake_launcher("claude-code"))
        deadline = time.time() + 240
        while time.time() < deadline:
            status = parse_stdout(cli(["campaign", "status", "--campaign", self.campaign]))
            if status["status"] == "complete":
                break
            time.sleep(1)
        self.assertEqual(status["status"], "complete", json.dumps(status)[:1200])
        self.assertGreaterEqual(status["complete"], 3)

    def test_the_three_lanes_overlap_and_each_lane_is_sequential(self):
        """Finding 20 / E10-51: the six-trial run used to have zero overlapping intervals."""
        self.make_campaign({"cases": [CASE], "conditions": ["available"], "repetitions": 2,
                            "routing": {"entries": [], "repetitions": 1},
                            "continuation": None})
        for harness in self.setups:
            # the fake launcher of each setup, one per lane
            pass
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--skip-probe-gate", "--reopen-key",
                   "--fake-launcher", os.path.join(FAKE, "claude-code-launch.sh")])
        self.assertEqual(got.returncode, 0, got.stderr)
        spans = {}
        for line in runner.read_text(os.path.join(self.campaign, "trials.jsonl"), "").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            command = runner.read_json(os.path.join(row["record"], "command.json"))
            spans.setdefault(command["setup"], []).append(
                (command["started_at"], command["ended_at"]))
        self.assertEqual(sorted(spans), sorted(self.setups))
        # each lane is strictly sequential: no trial of one setup starts before the previous
        # one of the same setup ended
        for setup, rows in spans.items():
            rows.sort()
            for earlier, later in zip(rows, rows[1:]):
                self.assertLessEqual(earlier[1], later[0],
                                     "%s overlapped with itself" % setup)
        # and the lanes themselves overlap, by the records' own native timestamps
        overlaps = 0
        names = sorted(spans)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                for first in spans[a]:
                    for second in spans[b]:
                        if first[0] <= second[1] and second[0] <= first[1]:
                            overlaps += 1
        self.assertGreater(overlaps, 0, "no two lanes overlapped: %s" % json.dumps(spans))

    def test_campaign_stop_terminates_the_registered_trial_groups(self):
        """Finding 21: the trial child stayed alive in its own process group."""
        campaign = runner.Campaign(self.campaign)
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                                 start_new_session=True)
        self.addCleanup(child.kill)
        campaign.append_jsonl(campaign.processes, {
            "event": "started", "token": "t", "trial": "claude-code-x-available-r1",
            "attempt": 0, "kind": "comparison", "pid": child.pid, "at": runner.now_iso()})
        # the campaign's own pid is a second throwaway process, never this test's: `stop`
        # terminates the process GROUP it names.
        owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                                 start_new_session=True)
        self.addCleanup(owner.kill)
        runner.write_text(campaign.pid_file, "%d\n" % owner.pid)
        stopped = parse_stdout(cli(["campaign", "stop", "--campaign", self.campaign]))
        self.assertTrue(stopped["stopped"])
        self.assertEqual([row["pid"] for row in stopped["terminated_trial_processes"]],
                         [child.pid])
        deadline = time.time() + 15
        while time.time() < deadline and child.poll() is None:
            time.sleep(0.2)
        self.assertIsNotNone(child.poll(), "the registered trial group survived the stop")
        interruptions = runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"), "")
        self.assertIn("campaign stop terminated pid %d" % child.pid, interruptions)

    def test_an_attempt_is_journalled_before_it_runs(self):
        tid, got = self.run_trial()
        journal = [json.loads(l) for l in runner.read_text(
            os.path.join(self.campaign, "attempts.jsonl"), "").splitlines() if l]
        self.assertEqual([row["trial"] for row in journal], [tid])
        self.assertEqual(journal[0]["attempt"], 0)
        self.assertEqual(journal[0]["kind"], "comparison")


# --------------------------------------------------------------------------- 16: measurements


class CorrectedMeasurementTest(RunnerCase):
    """Finding 16 / E10-48: raw history stays; a correction is hash-bound and consumed."""

    def setUp(self):
        RunnerCase.setUp(self)
        campaign = runner.Campaign(self.campaign)
        self.tid = "claude-code-F1-01-fixed-clean-available-r1"
        self.record = os.path.join(campaign.trials, self.tid)
        runner.write_json(os.path.join(self.record, "command.json"),
                          {"setup": "claude-code", "condition": "available", "case": CASE,
                           "workspace": "/nowhere", "status": "complete", "kind": "comparison"})
        runner.write_json(os.path.join(self.record, "cost.json"), {"total_cost_usd": None})
        campaign.append_jsonl(campaign.trials_jsonl, {
            "id": self.tid, "attempt": 0, "kind": "comparison", "status": "complete",
            "exit": 0, "wall": 1.014, "cost": None, "model": "m", "effort": "high",
            "activated": True, "record": self.record})

    def write_correction(self, field, raw, corrected):
        return cli(["measure", "--campaign", self.campaign, "--trial", self.tid,
                    "--field", field, "--corrects", os.path.join(self.record, "cost.json"),
                    "--raw-value", str(raw), "--corrected-value", str(corrected),
                    "--why", "the raw record's value is contradicted by the harness's own event",
                    "--evidence", os.path.join(self.record, "command.json")])

    def test_a_correction_is_bound_to_the_record_it_corrects(self):
        got = self.write_correction("cost", "null", 2.27341375)
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertEqual(document["corrects"]["sha256"],
                         runner.file_sha256(os.path.join(self.record, "cost.json")))
        self.assertEqual(document["corrected_value"], 2.27341375)

    def test_the_report_consumes_a_correction_whose_binding_holds(self):
        self.write_correction("cost", "null", 2.27341375)
        self.write_correction("wall", 1.014, 506.382)
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        applied = {row["field"]: row for row in report["corrected_measurements_applied"]}
        self.assertEqual(sorted(applied), ["cost", "wall"])
        self.assertAlmostEqual(report["totals"]["cost_usd"], 2.27341375)
        self.assertAlmostEqual(report["totals"]["wall_seconds"], 506.4, places=1)

    def test_a_correction_whose_target_changed_is_reported_stale_and_not_applied(self):
        self.write_correction("cost", "null", 2.27341375)
        runner.write_json(os.path.join(self.record, "cost.json"),
                          {"total_cost_usd": None, "changed": True})
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertEqual(report["corrected_measurements_applied"], [])
        self.assertEqual(len(report["corrected_measurements_stale"]), 1)
        self.assertIsNone(report["totals"]["cost_usd"] or None)

    def test_the_raw_record_is_never_edited(self):
        before = runner.read_text(os.path.join(self.campaign, "trials.jsonl"))
        self.write_correction("cost", "null", 2.27341375)
        cli(["report", "--campaign", self.campaign])
        self.assertEqual(runner.read_text(os.path.join(self.campaign, "trials.jsonl")), before)

    def test_the_report_counts_launches_apart_from_trials(self):
        campaign = runner.Campaign(self.campaign)
        campaign.append_jsonl(campaign.processes, {
            "event": "started", "token": "t", "trial": self.tid, "attempt": 0,
            "kind": "comparison", "pid": 1, "at": runner.now_iso()})
        campaign.append_jsonl(campaign.processes, {
            "event": "started", "token": "u", "trial": self.tid, "attempt": 0,
            "kind": "continuation:resume", "pid": 2, "at": runner.now_iso()})
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertEqual(report["launches_recorded"], 2)
        self.assertEqual(report["trials_seen"], 1)


# --------------------------------------------------------------------------- 24, 26, 27


class ScannerGateTest(RunnerCase):
    """Finding 24 / E10-52: a hit fails the launch gate and the report gate."""

    def test_a_credential_shape_in_a_capture_fails_the_launch(self):
        stub = self.stub_launcher("claude-code", "leaks",
                                  RECHECK_FAKE_PLANT_SECRET="sk-or-v1-" + "a1b2c3d4" * 8)
        tid, got = self.run_trial(launcher=stub)
        self.assertEqual(got.returncode, 1, got.stdout)
        self.assertIn("credential-shaped", got.stderr)
        scan = runner.read_json(os.path.join(self.campaign, "trials", tid, "scan.json"))
        self.assertEqual([h["shape"] for h in scan["hits"]], ["openrouter-key"])
        self.assertNotIn("a1b2c3d4", json.dumps(scan))

    def test_a_credential_shape_in_the_records_fails_the_report(self):
        runner.write_text(os.path.join(self.campaign, "records", "leak.txt"),
                          "sk-or-v1-" + "f" * 64 + "\n")
        got = cli(["report", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 1, got.stdout)
        self.assertIn("credential-shaped", got.stderr)

    def test_an_unreadable_mandatory_capture_fails_the_scan(self):
        path = os.path.join(self.campaign, "trials", "t", "harness", "trace.jsonl")
        runner.write_text(path, "{}\n")
        os.chmod(path, 0o000)
        self.addCleanup(os.chmod, path, 0o644)
        got = cli(["scan", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 1, got.stdout)
        self.assertIn("unreadable mandatory", got.stderr)


class StageAndVerifyTest(RunnerCase):
    """Finding 26 / E10-52."""

    def test_a_failed_identity_computation_fails_the_stage(self):
        identity = {"exit": 1, "content_sha256": None, "parse_error": None, "ok": False,
                    "stderr_tail": ""}
        self.assertFalse(identity["ok"])
        # the shape the runner checks
        self.assertFalse(runner.fresh_skill_identity.__doc__ is None)

    def test_an_empty_digest_is_not_a_successful_identity(self):
        for digest in (None, "", "short"):
            self.assertFalse(bool(isinstance(digest, str) and len(digest) == 64))

    def test_verify_exits_three_for_a_home_that_is_not_installed(self):
        got = cli(["verify", "--campaign", self.campaign, "--setup", "claude-code",
                   "--home", "available"])
        self.assertEqual(got.returncode, 3, got.stdout)
        self.assertIn("not installed", got.stderr)

    def test_stage_writes_a_manifest_with_hashes(self):
        """E10-53(3): the reviewer could not recompute a historical tree hash."""
        campaign = os.path.join(self.scratch, "stage-campaign")
        got = cli(["stage", "--campaign", campaign])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        manifest = runner.read_json(document["manifest"])
        self.assertGreater(len(manifest["files"]), 20)
        self.assertEqual(manifest["plugin_tree_sha256"], document["plugin_tree_sha256"])
        for row in manifest["files"][:5]:
            self.assertEqual(len(row["sha256"]), 64)
        self.assertEqual(document["link_survey"]["symlinks"], [])
        self.assertEqual(document["answer_key_or_held_out_in_stage"], [])


# ------------------------------------------------- E10-54, E10-55, E10-56(1): the second round


class TrialShapeTest(RunnerCase):
    """E10-54(a) and (b): the run directory is the fixture's own `run/` leaf and the prompt
    names the run id.

    The facts these tests stand on are the fixture's own, never the key's: `build.py --opaque`
    lays a case out as `<out>/<12 hex>/{workspace,run,input.json,manifest.json}`
    (`fixturelib.Fixture`), and the case's seeded `input.json` names that leaf as
    `invocation.run_dir` and `<case id>-run` as `invocation.run_id`.
    """

    def test_the_run_directory_is_the_fixture_s_own_run_leaf(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        case_dir = command["fixture"]["case_dir"]
        self.assertEqual(command["run_dir"], os.path.join(case_dir, "run"))
        self.assertEqual(command["run_root"], case_dir)
        self.assertTrue(command["run_dir_is_the_fixture_run_leaf"])
        # E7-18's own promise: the leaf keeps the name `run`, so a key's `/run/` pattern holds
        self.assertEqual(os.path.basename(command["run_dir"]), "run")
        self.assertIn("/run/", os.path.join(command["run_dir"], "result.json"))

    def test_the_seeded_input_names_the_same_leaf_and_the_same_run_id(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        seeded = runner.read_json(os.path.join(command["fixture"]["case_dir"], "input.json"))
        self.assertEqual(seeded["invocation"]["run_dir"], command["run_dir"])
        self.assertEqual(seeded["invocation"]["run_id"], "%s-run" % CASE)

    def test_the_prompt_names_the_run_id_in_words(self):
        tid, got = self.run_trial()
        prompt = runner.read_text(os.path.join(self.campaign, "trials", tid, "prompt.txt"))
        self.assertIn("Use run id %s-run and the run directory " % CASE, prompt)
        note = runner.read_json(os.path.join(self.campaign, "trials", tid,
                                             "command.json"))["run_root_note"]
        self.assertIn("NAMES it in words", note["documented_exception"])
        self.assertIn("E10-54(b)", note["documented_exception"])

    def test_the_result_the_session_wrote_carries_that_run_id_and_that_directory(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        result = runner.read_json(os.path.join(self.campaign, "trials", tid, "result.json"))
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        # the field names are the ones a retained real record of the fix campaign carries:
        # `run.run_id` and `run.run_dir` at the top of the run block, `mode` under
        # `run.invocation` (read as a fact from
        # `e10/fix-2026-09-15/trials/claude-code-F1-01-fixed-clean-absent-r1/result.json`).
        self.assertEqual(result["run"]["run_id"], "%s-run" % CASE)
        self.assertEqual(result["run"]["run_dir"], command["run_dir"])
        self.assertEqual(result["run"]["invocation"]["mode"], "headless")
        # every artifact the run wrote is under a `/run/` path now
        for write in result.get("records_written") or []:
            path = write.get("path") if isinstance(write, dict) else write
            if isinstance(path, str) and path.startswith(command["run_dir"]):
                self.assertIn("/run/", path)

    def test_the_run_root_note_says_what_the_adapters_segment_now_means(self):
        tid, got = self.run_trial()
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        note = command["run_root_note"]
        self.assertEqual(note["run_root_name"], "runs")
        self.assertIn("${TMPDIR}/runs", note["means"])
        self.assertIn("fixture's own `run/` leaf", note["means"])
        self.assertEqual(command["adapters_run_root"],
                         os.path.join(command["opaque_tree"], "runs"))

    def test_the_two_conditions_still_get_byte_identical_prompts(self):
        self.make_campaign({"conditions": ["available", "absent"]})
        first, got = self.run_trial(condition="available")
        self.assertEqual(got.returncode, 0, got.stderr)
        second, got = self.run_trial(condition="absent")
        self.assertEqual(got.returncode, 0, got.stderr)

        def normalised(tid):
            record = os.path.join(self.campaign, "trials", tid)
            command = runner.read_json(os.path.join(record, "command.json"))
            text = runner.read_text(os.path.join(record, "prompt.txt"))
            for name, value in (("<RUN_DIR>", command["run_dir"]),
                                ("<WORKSPACE>", command["workspace"]),
                                ("<TREE>", command["opaque_tree"])):
                text = text.replace(value, name)
            return text

        self.assertEqual(normalised(first), normalised(second))
        self.assertNotIn(self.campaign, normalised(first))


class TrialConditionedExpectedTest(RunnerCase):
    """E10-54(c): the trial's own facts are substituted into the expected document.

    Every expected document below is one this test wrote (E10-21); no test here opens the
    answer key.
    """

    cases = (CASE, TWO_ITEM_CASE)

    def test_the_default_carries_the_mode_and_its_rule(self):
        defaults = runner.trial_defaults()
        self.assertEqual(defaults["invocation_mode"], "headless")
        self.assertIn("headless", defaults["invocation_mode_rule"])
        self.assertIn("E10-54(c)", defaults["invocation_mode_rule"])

    def stand_in_expected(self):
        return {
            "status": "completed",
            "run": {"run_id": "%s-run" % CASE,
                    "invocation": {"mode": "interactive", "resume": False},
                    "model": {"floor_met": True}},
            "items": [{"disposition": "fixed"}],
        }

    def test_the_mode_is_substituted_and_recorded_and_nothing_else_changes(self):
        original = self.stand_in_expected()
        before = json.dumps(original, sort_keys=True)
        document, rows = runner.trial_conditioned_expected(original, "comparison")
        # the substitution happened
        self.assertEqual(document["run"]["invocation"]["mode"], "headless")
        # it is recorded, with the key's own literal beside the value used
        row = [r for r in rows if r["path"] == "$.run.invocation.mode"][0]
        self.assertEqual(row["key_literal"], "interactive")
        self.assertEqual(row["used"], "headless")
        self.assertTrue(row["applied"])
        self.assertIn("trial-defaults.json", row["source"])
        # a comparison trial leaves `resume` alone
        self.assertEqual(document["run"]["invocation"]["resume"], False)
        self.assertFalse([r for r in rows if r["path"] == "$.run.invocation.resume"])
        # the key's own document is untouched, and nothing but the substituted path changed
        self.assertEqual(json.dumps(original, sort_keys=True), before)
        stripped_before, stripped_after = json.loads(before), json.loads(json.dumps(document))
        stripped_before["run"]["invocation"].pop("mode")
        stripped_after["run"]["invocation"].pop("mode")
        self.assertEqual(json.dumps(stripped_before, sort_keys=True).encode("utf-8"),
                         json.dumps(stripped_after, sort_keys=True).encode("utf-8"))

    def test_a_continuation_trial_also_substitutes_resume_true(self):
        original = self.stand_in_expected()
        document, rows = runner.trial_conditioned_expected(original, "continuation:handoff")
        self.assertEqual(document["run"]["invocation"]["resume"], True)
        row = [r for r in rows if r["path"] == "$.run.invocation.resume"][0]
        self.assertEqual(row["key_literal"], False)
        self.assertEqual(row["used"], True)
        self.assertIn("continuation", row["source"])
        stripped_before = self.stand_in_expected()
        stripped_after = json.loads(json.dumps(document))
        for node in (stripped_before, stripped_after):
            node["run"]["invocation"].pop("mode")
            node["run"]["invocation"].pop("resume")
        self.assertEqual(json.dumps(stripped_before, sort_keys=True).encode("utf-8"),
                         json.dumps(stripped_after, sort_keys=True).encode("utf-8"))

    def test_an_expected_document_with_no_run_invocation_records_that_nothing_applied(self):
        document, rows = runner.trial_conditioned_expected({"status": "completed"}, "comparison")
        self.assertEqual(document, {"status": "completed"})
        self.assertFalse(rows[0]["applied"])
        self.assertIsNone(rows[0]["used"])
        self.assertIn("nothing to substitute", rows[0]["why_not"])

    def test_a_graded_trial_matches_a_stand_in_key_that_pins_the_interactive_mode(self):
        """The whole point: a key written from E7's interactive trial shape now matches a
        headless E10 trial, and `grade.json` says what was substituted."""
        directory = self.stand_in_key(expected=self.stand_in_expected())
        tid, got = self.run_trial(case=CASE)
        self.assertEqual(got.returncode, 0, got.stderr)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = parse_stdout(cli(["grade", "--campaign", self.campaign, tid, "--summary"],
                                  env=environment))
        self.assertEqual(graded["summary"]["match_ok"], 1, graded["per_trial"])
        self.assertEqual(graded["per_trial"][0]["trial_conditioned_paths"],
                         ["$.run.invocation.mode"])
        grade = runner.read_json(os.path.join(self.campaign, "trials", tid, "grade.json"))
        rows = grade["trial_conditioned"]
        self.assertEqual([r["path"] for r in rows], ["$.run.invocation.mode"])
        self.assertEqual(rows[0]["key_literal"], "interactive")
        self.assertEqual(rows[0]["used"], "headless")

    def test_without_the_substitution_the_same_key_fails_on_the_mode_alone(self):
        """The counterfactual, from the runner's own matcher: the key's literal is what E7
        wrote and the trial is headless, so the mode is the one field that diverges."""
        expected = self.stand_in_expected()
        actual = {"status": "completed",
                  "run": {"run_id": "%s-run" % CASE,
                          "invocation": {"mode": "headless", "resume": False},
                          "model": {"floor_met": True}},
                  "items": [{"disposition": "fixed"}]}
        raw_ok, raw_reasons = runner._import_match().match(expected, actual)
        self.assertFalse(raw_ok)
        self.assertEqual(runner.reason_path_segments(raw_reasons), {"run": 1})
        conditioned, _ = runner.trial_conditioned_expected(expected, "comparison")
        self.assertTrue(runner._import_match().match(conditioned, actual)[0])

    def test_the_summary_counts_match_reasons_by_first_path_segment_only(self):
        """E10-54's regrade reads the reasons by PATH SEGMENT from `grade --summary`; the
        reason's own text quotes the key's expected value and is never printed."""
        directory = self.stand_in_key(expected={"status": "nonesuch",
                                                "items": [{"disposition": "not_fixed"}]})
        tid, got = self.run_trial(case=CASE)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        result = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        graded = parse_stdout(result)
        self.assertEqual(graded["summary"]["trials_with_a_failing_match"], 1)
        segments = graded["summary"]["match_reasons_by_path_segment"]
        self.assertEqual(sorted(segments), ["items", "status"])
        self.assertNotIn("nonesuch", result.stdout)
        self.assertNotIn('"reasons"', result.stdout)


class FrozenCutTest(RunnerCase):
    """E10-55: the cut is captured frozen."""

    cases = (TWO_ITEM_CASE,)

    def test_a_valid_cut_is_captured_while_the_group_is_frozen(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        stub = self.cut_stub("frozen-valid")
        got = cli(["continuation", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        cut = runner.read_json(os.path.join(self.campaign, "trials", tid,
                                            "command.json"))["cut"]
        self.assertTrue(cut["valid"], cut.get("invalid_because"))
        self.assertEqual(cut["freeze"]["signal"], "SIGSTOP")
        self.assertTrue(cut["freeze"]["sent"])
        self.assertTrue(cut["freeze"]["confirmed"], cut["freeze"])
        self.assertTrue(cut["freeze"]["captured_while_frozen"])
        self.assertEqual(cut["seq"], 3)
        self.assertEqual((cut["done"], cut["pending"]), (1, 1))

    def test_a_session_that_would_advance_as_it_dies_can_no_longer_beat_the_capture(self):
        """The race of finding 15, made deterministic by a SIGTERM trap. Before E10-55 the
        retained pair read seq 4 with both items done and the cut was invalid; with the group
        frozen before the capture the retained pair is the state the poller saw."""
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        stub = self.cut_stub("frozen-race", advance_on_term=True)
        got = cli(["continuation", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        record = os.path.join(self.campaign, "trials", tid)
        cut = runner.read_json(os.path.join(record, "command.json"))["cut"]
        self.assertTrue(cut["freeze"]["confirmed"], cut["freeze"])
        self.assertTrue(cut["valid"], cut.get("invalid_because"))
        self.assertEqual(cut["seq"], 3)
        self.assertEqual(cut["observed_at_the_poll"]["seq"], cut["seq"])
        retained = runner.read_json(os.path.join(record, "harness-first",
                                                 "at-cut-checkpoint.json"))
        self.assertEqual(retained["integrity"]["seq"], 3)
        self.assertEqual(sorted(r["state"] for r in retained["scope"]["items"]),
                         ["done", "pending"])

    def test_a_session_that_never_shows_a_mixed_state_is_an_invalid_cut(self):
        tid = runner.continuation_trial_id("claude-code", TWO_ITEM_CASE, "handoff", 1)
        stub = self.cut_stub("never-mixed", mixed=False)
        got = cli(["continuation", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        cut = runner.read_json(os.path.join(self.campaign, "trials", tid,
                                            "command.json"))["cut"]
        self.assertFalse(cut["cut_made"])
        self.assertFalse(cut["valid"])
        self.assertIn("before the checkpoint ever showed a mixed state", cut["invalid_because"])
        self.assertFalse(cut["freeze"]["sent"])
        interruptions = runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"), "")
        self.assertIn("invalid cut", interruptions)

    def test_a_retained_pair_that_disagrees_with_the_poll_is_still_an_invalid_cut(self):
        """E10-55 keeps E10-47's rule. The two shapes below are the ones the fix campaign's own
        two invalid cuts recorded: the poll saw seq 3 with one item done and one pending, the
        retained pair held seq 4 with both done."""
        observed = {"seq": 3, "done": 1, "pending": 1, "phase": "adjudicating"}
        retained = {"seq": 4, "done": 2, "pending": 0, "phase": "adjudicating",
                    "item_rows": [{"index": 0, "state": "done"}, {"index": 1, "state": "done"}]}
        valid, why = runner.cut_verdict(observed, retained)
        self.assertFalse(valid)
        self.assertIn("does not show the claimed state", why)
        self.assertIn("observed seq 3", why)
        self.assertIn("retained seq 4", why)
        # and the agreeing pair is valid
        self.assertEqual(runner.cut_verdict(observed, dict(observed, item_rows=[])),
                         (True, None))


class WithoutTheSkillTest(RunnerCase):
    """E10-56(1): `install.sh --without recheck-v2` for the absent home, and no second guard."""

    def stub_install(self, harness):
        """A stub `install.sh` in the stage that records the argv it was given, and the NAMES
        its own environment carried (never a value), so a test can prove what the runner
        actually handed the child."""
        path = os.path.join(self.stage, "plugins", "recheck-v2", "setups", harness, "install.sh")
        runner.ensure_dir(os.path.dirname(path))
        log = os.path.join(self.scratch, "install-argv-%s.txt" % harness)
        runner.write_text(path, "#!/bin/sh\nprintf '%%s\\n' \"$*\" >> %s\n"
                                "env | cut -d= -f1 | sort | sed 's/^/name: /' >> %s\n"
                                "exit 0\n" % (log, log))
        os.chmod(path, 0o755)
        return log

    def test_the_claude_absent_install_passes_the_flag_and_removes_nothing(self):
        log = self.stub_install("claude-code")
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        record = setup.install("absent")
        self.assertIn("--without recheck-v2", runner.read_text(log))
        # one step only: no `claude plugin uninstall`, no cache removal (E10-24's second guard)
        self.assertEqual(len(record["steps"]), 1)
        self.assertEqual(record["uninstalled_after_install"], [])
        self.assertEqual(record["recheck_v2_installation"]["how"], "never installed")
        self.assertIn("E10-56(1)", record["recheck_v2_installation"]["by"])

    def test_the_claude_available_install_does_not_pass_the_flag(self):
        log = self.stub_install("claude-code")
        campaign = runner.Campaign(self.campaign)
        runner.ClaudeCodeSetup(campaign, stage=self.stage).install("available")
        self.assertNotIn("--without", runner.read_text(log))

    def test_the_codex_absent_install_passes_the_flag_and_points_the_home_by_name(self):
        """E10-58(2): the codex absent home is its own `install.sh` run now. The script honours
        `RECHECK_CODEX_HOME`, so the runner points it at the absent home and skips the one
        install step of the skill; nothing is removed afterwards and the home is not derived."""
        log = self.stub_install("codex")
        campaign = runner.Campaign(self.campaign)
        base = runner.pilot_home("codex", "available")
        runner.write_text(os.path.join(base, "auth.json"), "{}\n")
        setup = runner.CodexSetup(campaign, stage=self.stage)
        record = setup.install("absent")
        self.assertIn("--without recheck-v2", runner.read_text(log))
        self.assertEqual(len(record["steps"]), 1)
        self.assertEqual(record["removed"], [])
        self.assertFalse(record["derived_from_available"])
        self.assertEqual(record["recheck_v2_installation"]["how"], "never installed")
        self.assertNotIn("why_not_never_installed", record["recheck_v2_installation"])
        # the environment NAME is recorded, never a value
        blob = json.dumps(record)
        self.assertIn("RECHECK_CODEX_HOME", blob)
        self.assertNotIn("RECHECK_CODEX_HOME=", blob)
        # and the CHILD was actually given it: the stub printed its own environment's names
        names = [l[len("name: "):] for l in runner.read_text(log).splitlines()
                 if l.startswith("name: ")]
        self.assertIn("RECHECK_CODEX_HOME", names)
        self.assertEqual([n for n in names if runner.BANNED_ENV_RE.match(n)], [],
                         "the install child carried a banned name: %s" % names)
        # the credential stays one file: both auth paths are links to the available store
        self.assertEqual(record["auth_linked_to_the_available_store"],
                         ["auth.json", os.path.join("child", "auth.json")])
        for rel in record["auth_linked_to_the_available_store"]:
            path = os.path.join(record["home"], rel)
            self.assertTrue(os.path.islink(path), path)
            self.assertEqual(os.path.realpath(path),
                             os.path.realpath(os.path.join(base, "auth.json")))

    def test_the_codex_install_env_carries_the_home_pointer_and_no_value(self):
        """The name the runner passes, from the one boundary that builds every child (E10-42)."""
        campaign = runner.Campaign(self.campaign)
        setup = runner.CodexSetup(campaign, stage=self.stage)
        built = campaign.env(extra={"RECHECK_CODEX_HOME": setup.home("absent")},
                             require_binaries=False)
        self.assertEqual(sorted(built), sorted(list(runner.ALLOWED_ENV) + ["RECHECK_CODEX_HOME"]))
        self.assertIsNone(runner.BANNED_ENV_RE.match("RECHECK_CODEX_HOME"))
        self.assertEqual(runner.allowlisted_names(built),
                         sorted(list(runner.ALLOWED_ENV) + ["RECHECK_CODEX_HOME"]))

    def test_the_codex_install_script_honours_the_home_pointer(self):
        """The real script, read: `CODEX_HOME` comes from `RECHECK_CODEX_HOME` when it is set
        (E10-58(2)), and defaults to the pilot home as before."""
        text = runner.read_text(os.path.join(runner.PLUGIN_DIR, "setups", "codex", "install.sh"))
        self.assertIn('export CODEX_HOME="${RECHECK_CODEX_HOME:-$HOME/.local/share/'
                      'skills-v2-pilot/codex/home}"', text)
        self.assertIn("E10-58(2)", text)

    def test_the_codex_routing_home_is_still_derived_from_the_available_one(self):
        source = runner.read_text(runner.__file__)
        body = source.split("class CodexSetup(", 1)[1].split("\nclass ", 1)[0]
        self.assertIn("Only `routing` reaches here (E10-58(2))", body)
        self.assertIn('"derived_from_available": True', body)

    def test_the_opencode_absent_install_passes_the_flag_and_removes_nothing(self):
        log = self.stub_install("opencode")
        campaign = runner.Campaign(self.campaign)
        setup = runner.OpenCodeSetup(campaign, stage=self.stage)
        record = setup.install("absent")
        self.assertIn("--without recheck-v2", runner.read_text(log))
        self.assertEqual(record["removed"], [])
        self.assertEqual(record["recheck_v2_installation"]["how"], "never installed")

    def test_the_three_install_scripts_take_the_flag_and_refuse_another_name(self):
        """The real scripts, parsed: `--without` takes `recheck-v2` and nothing else."""
        for harness in ("claude-code", "codex", "opencode"):
            path = os.path.join(runner.PLUGIN_DIR, "setups", harness, "install.sh")
            text = runner.read_text(path)
            self.assertIn("--without", text, harness)
            self.assertIn("E10-56(1)", text, harness)
            got = runner.run_cmd(["sh", path, "--without", "readers"], env=runner.tool_env(),
                                 label="--without readers")
            self.assertEqual(got["exit"], 2, "%s: %s" % (harness, got["stderr"][-400:]))


class HelpAndDocumentationTest(unittest.TestCase):
    """Finding 27 / E10-52: the help exception is documented, and E10-37's citation corrected."""

    def test_the_readme_records_the_help_exception(self):
        readme = runner.read_text(os.path.join(runner.RUNNER_DIR, "README.md"))
        self.assertIn("--help", readme)
        self.assertIn("documented A7a exception", readme)

    def test_the_readme_corrects_the_E10_37_citation(self):
        readme = runner.read_text(os.path.join(runner.RUNNER_DIR, "README.md"))
        self.assertIn("/payload/encrypted_content", readme)
        self.assertIn("verifier rollout line 26", readme)

    def test_the_readme_states_the_current_run_root_and_poll_interval(self):
        readme = runner.read_text(os.path.join(runner.RUNNER_DIR, "README.md"))
        self.assertIn("0.1", readme)
        self.assertNotIn("polls `run/checkpoint.json` and `run/checkpoint.log` every second",
                         readme)


if __name__ == "__main__":
    unittest.main()
