"""The wall of lane contract section 3 and E10-40, and the E10-21 stand-in.

E10-40 is the predicate here: the three harnesses run every trial as this user with no read
sandbox, so the wall is `instruction-bound + measured`, not enforced. What the runner does and
what these tests prove:

1. the answer key and the held-out set are held at mode **000 for the whole of every launch**,
   by the launch path itself, and a real launched child cannot read them while they are closed;
2. they are reopened only inside `grade` and `routing-score`, and only after every registered
   process of the attempt has ended;
3. a crash leaves them closed and `campaign start` refuses until `--reopen-key`;
4. the grader measures every read of a campaign record outside the trial's own opaque tree
   (`records_reached`) and every read of the skill files under the absent condition
   (`skill_file_reached`);
5. no launch path can reach a reader, by the AST;
6. a key stand-in is honoured only under `RECHECK_RUNNER_TEST=1` **and** only for a campaign
   the runner itself marked synthetic.

Finding 25: the old `UnreadableCopy` built a copy of the plugin whose `answer-key/` was mode
000 and then ran `cli`, which never looked at that copy — the launch paths ran against the
real, readable directories and the proof was empty. Every test below acts on the directories
the runner actually opens.
"""
import json
import os
import subprocess
import sys
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, FAKE, CASE


class KeyClosedDuringEveryLaunchTest(RunnerCase):
    """The launch paths themselves close the two directories, and a child cannot read them."""

    def assert_closed(self):
        state = [row for row in runner.key_state() if row["present"]]
        self.assertTrue(state, "neither key directory exists; the proof would be empty")
        for row in state:
            self.assertTrue(row["closed"], "%s is mode %s after the launch, not 000"
                            % (row["path"], row["mode"]))

    def assert_a_child_cannot_read_them(self):
        """A real child process, from the same allowlisted environment a launcher gets."""
        for path in runner.key_paths():
            if not os.path.isdir(path):
                continue
            probe = subprocess.run(
                [sys.executable, "-c", "import os,sys;os.listdir(sys.argv[1])", path],
                capture_output=True, text=True,
                env=runner.tool_env())
            self.assertNotEqual(probe.returncode, 0,
                                "a child listed %s while it was supposed to be closed" % path)
            self.assertIn("Permission denied", probe.stderr)

    def test_the_comparison_launch_path_closes_both_directories_and_keeps_them_closed(self):
        runner.open_key(None, "the test opens them first")
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(parse_stdout(got)["status"], "complete")
        self.assert_closed()
        self.assert_a_child_cannot_read_them()

    def test_the_routing_launch_path_closes_both_directories(self):
        runner.open_key(None, "the test opens them first")
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assert_closed()

    def test_the_continuation_launch_path_closes_both_directories(self):
        runner.open_key(None, "the test opens them first")
        tid = runner.continuation_trial_id("claude-code", "F3-02-mixed-two-items", "handoff", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        self.assert_closed()

    def test_grade_opens_them_only_for_the_grade_and_closes_them_again(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assert_closed()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)
        # the grade read a key and put the directories back the way it found them
        self.assert_closed()

    def test_campaign_start_refuses_while_the_key_is_closed_and_reopen_key_clears_it(self):
        runner.close_key(None, "a crashed run")
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--skip-probe-gate", "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("--reopen-key", got.stderr)


class RecordsReachedTest(RunnerCase):
    """E10-40: the grader measures what a trial actually read, since it cannot prevent it."""

    def test_a_read_of_a_campaign_record_outside_the_trial_s_tree_is_recorded(self):
        outside = os.path.join(self.campaign, "reviewer-only-sentinel.txt")
        runner.write_text(outside, "a record outside the trial's own opaque tree\n")
        stub = self.stub_launcher("claude-code", "reads-a-record",
                                  RECHECK_FAKE_PLANT_READ=outside)
        tid, got = self.run_trial(extra_args=())
        self.assertEqual(got.returncode, 0, got.stderr)
        # a second trial, this one reading the sentinel
        second = runner.trial_id("claude-code", CASE, "available", 2)
        self.make_campaign({"repetitions": 2})
        ran = cli(["run", "--campaign", self.campaign, second, "--fake-launcher", stub])
        self.assertEqual(ran.returncode, 0, ran.stderr)
        record = os.path.join(self.campaign, "trials", second)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertTrue(witnesses["records_reached"]["reached"],
                        "the read of %s was not measured" % outside)
        self.assertIn(outside, json.dumps(witnesses["records_reached"]["reads"]))

    def test_a_read_inside_the_trial_s_own_tree_is_not_a_record_read(self):
        command = {"workspace": "/x/ws", "run_dir": "/x/tree/runs/r",
                   "opaque_tree": "/x/tree"}
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(self.campaign, "trials", "none")
        runner.ensure_dir(record)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertFalse(witnesses["records_reached"]["reached"])

    def test_the_absent_condition_s_skill_read_is_recorded(self):
        stub = self.stub_launcher(
            "claude-code", "reads-the-skill",
            RECHECK_FAKE_PLANT_READ="/Users/x/.local/share/skills-v2-pilot/claude-code/absent/"
                                    "config/plugins/cache/tony-skills/recheck-v2/SKILL.md")
        self.make_campaign({"conditions": ["available", "absent"]})
        tid = runner.trial_id("claude-code", CASE, "absent", 1)
        ran = cli(["run", "--campaign", self.campaign, tid, "--fake-launcher", stub])
        self.assertEqual(ran.returncode, 0, ran.stderr)
        record = os.path.join(self.campaign, "trials", tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertTrue(witnesses["skill_file_reached"]["reached"],
                        "the absent condition's read of the skill files was not measured")


class WallStructureTest(unittest.TestCase):
    """Which functions in `runner.py` can reach the key or the held-out set, by the AST."""

    READERS = ("key_dir", "heldout_file", "key_entry", "heldout_entry_ids", "request_text",
               "expectation_of", "_routing_entry_ids")
    ALLOWED = {
        # the readers themselves
        "key_dir", "heldout_file", "key_entry", "heldout_entry_ids", "request_text",
        "expectation_of", "_routing_entry_ids",
        # the grading half (E10-11) and the scorer (E10-13)
        "grade_one", "do_grade", "do_routing_score", "key_file_sha256",
        # `routing` at launch time, for the one entry it is launching (E10-13)
        "do_routing", "routing_request",
        # `plan` needs the entry ids to write the order; the ids come from a subprocess
        "do_plan",
        # E10-68 defect 1: the campaign caches every planned held-out request once, before its
        # first launch, through a subprocess that writes the file itself
        "cache_routing_requests",
    }
    # E10-40's lock. These name the two DIRECTORIES to change their mode or report it; none of
    # them opens a file inside either one.
    LOCK = {"key_paths", "sentinel_probe"}

    def setUp(self):
        import ast
        self.tree = ast.parse(runner.read_text(runner.__file__))
        self.ast = ast

    def _functions_naming(self, names):
        found = {}
        for node in self.ast.walk(self.tree):
            if not isinstance(node, (self.ast.FunctionDef, self.ast.AsyncFunctionDef)):
                continue
            for inner in self.ast.walk(node):
                if isinstance(inner, self.ast.Name) and inner.id in names:
                    found.setdefault(node.name, set()).add(inner.id)
                if isinstance(inner, self.ast.Attribute) and inner.attr in names:
                    found.setdefault(node.name, set()).add(inner.attr)
        return found

    def test_only_the_allowed_functions_name_a_reader(self):
        found = self._functions_naming(set(self.READERS))
        extra = sorted(set(found) - self.ALLOWED)
        self.assertEqual(extra, [], "these functions reach the key or the held-out set: %s"
                         % {k: sorted(found[k]) for k in extra})

    def test_only_the_readers_and_the_lock_name_the_key_constants(self):
        found = self._functions_naming({"KEY_DIR", "TRIGGER_HELDOUT"})
        self.assertEqual(sorted(found), sorted(["key_dir", "heldout_file"] + sorted(self.LOCK)),
                         "an unexpected function names a key constant: %s" % sorted(found))

    def test_the_launch_helpers_name_no_reader_and_no_key_constant(self):
        launchers = ("do_run", "_one_trial", "collect_trial", "do_probe_env", "do_continuation",
                     "_launch_and_cut", "_compaction_resume", "do_install", "do_verify",
                     "do_stage", "do_campaign", "_campaign_loop", "do_rerun", "do_scan",
                     "do_report", "trace_witnesses", "native_actions")
        found = self._functions_naming(set(self.READERS) | {"KEY_DIR", "TRIGGER_HELDOUT"})
        for name in launchers:
            self.assertNotIn(name, found, "%s reaches the key or the held-out set" % name)

    def test_the_wall_marker_is_in_the_file_and_the_readers_sit_below_it(self):
        source = runner.read_text(runner.__file__)
        marker = "# ------------------------------------------------------------" \
                 "--------------- the wall"
        self.assertIn(marker, source)
        above = source.split(marker, 1)[0]
        for reader in ("def key_entry", "def request_text", "def heldout_entry_ids",
                       "def expectation_of", "def _routing_entry_ids", "def key_dir",
                       "def heldout_file"):
            self.assertNotIn(reader, above, "%s is defined above the wall marker" % reader)

    def test_the_grade_path_never_prints_a_grade_document(self):
        source = runner.read_text(runner.__file__)
        body = source.split("def grade_summary", 1)[1].split("\ndef ", 1)[0]
        for field in ("expected", "must_not", "dispositions\"]"):
            self.assertNotIn('"%s"' % field, body.replace('"by_condition"', ""),
                             "grade_summary leaks %s" % field)

    def test_every_launch_path_closes_the_key_before_it_launches(self):
        """By the AST: each launch entry point calls `close_key` before its launch."""
        source = runner.read_text(runner.__file__)
        for name in ("_one_trial", "do_routing", "do_continuation", "do_probe_env"):
            body = source.split("def %s(" % name, 1)[1].split("\ndef ", 1)[0]
            self.assertIn("close_key(", body, "%s launches without closing the key" % name)


class StandInTest(RunnerCase):
    """E10-21 and E10-45: the flag AND a campaign the runner marked synthetic."""

    def test_a_stand_in_without_the_test_flag_is_refused(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        environment = self.child_env({"RECHECK_RUNNER_KEY_DIR": directory})
        environment.pop("RECHECK_RUNNER_TEST", None)
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 2, graded.stdout)
        self.assertIn("key stand-in outside test", graded.stderr)

    def test_a_held_out_stand_in_without_the_test_flag_is_refused(self):
        environment = self.child_env({"RECHECK_RUNNER_HELDOUT": os.path.join(self.scratch, "x.json")})
        environment.pop("RECHECK_RUNNER_TEST", None)
        got = cli(["routing-score", "--campaign", self.campaign], env=environment)
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn("key stand-in outside test", got.stderr)

    def test_a_stand_in_is_refused_for_a_campaign_the_runner_did_not_mark_synthetic(self):
        """Finding 9: the test flag alone must never grade a real trial against a stand-in."""
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        # take the synthetic marks away: this is now an ordinary campaign
        os.unlink(os.path.join(self.campaign, "SYNTHETIC"))
        document = runner.read_json(os.path.join(self.campaign, "campaign.json"))
        document["synthetic"] = False
        runner.write_json(os.path.join(self.campaign, "campaign.json"), document)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 2, graded.stdout)
        self.assertIn("outside a synthetic campaign", graded.stderr)

    def test_a_launch_with_a_fake_launcher_marks_the_campaign_synthetic(self):
        os.unlink(os.path.join(self.campaign, "SYNTHETIC"))
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.campaign, "SYNTHETIC")),
                        "the runner did not mark the campaign synthetic")

    def test_a_key_that_does_not_run_at_E10_is_refused_before_matching(self):
        directory = self.stand_in_key(runs_at="E7")
        tid, got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 1, graded.stdout)
        self.assertIn("not E10", graded.stderr)
        self.assertFalse(os.path.isfile(os.path.join(self.campaign, "trials", tid, "grade.json")),
                         "a grade file was written for a key that does not run at E10")

    def test_a_stand_in_under_the_test_flag_grades(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)
        document = parse_stdout(graded)
        self.assertEqual(document["graded"], 1)
        self.assertEqual(document["summary"]["graded"], 1)
        grade = runner.read_json(os.path.join(self.campaign, "trials", tid, "grade.json"))
        self.assertTrue(grade["key_stand_in"], "the grade does not say a stand-in was used")
        self.assertTrue(grade["inputs_bound_to"]["result_sha256"],
                        "the grade does not bind its inputs")
        self.assertEqual(grade["inputs_bound_to"]["case"], CASE)

    def test_grade_summary_prints_counts_and_never_a_grade_document(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)
        self.assertNotIn("must_not", graded.stdout)
        self.assertNotIn('"expected"', graded.stdout)
        self.assertNotIn('"reasons"', graded.stdout)


class GradeBarrierTest(RunnerCase):
    """E10-45 (finding 8): every process of the attempt, from three sources, blocks the grade."""

    def test_a_live_child_pid_in_the_record_stops_the_grade(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        runner.write_text(os.path.join(self.campaign, "trials", tid, "harness", "child.pid"),
                          "%d\n" % os.getpid())
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 1, graded.stdout)
        self.assertIn("still alive", graded.stderr)

    def test_a_live_pid_in_launch_json_stops_the_grade(self):
        """Finding 8: the guard used to look at `harness/child.pid` and nothing else."""
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        path = os.path.join(self.campaign, "trials", tid, "harness", "launch.json")
        launch = runner.read_json(path)
        launch["pid"] = os.getpid()
        runner.write_json(path, launch)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 1, graded.stdout)
        self.assertIn("still alive", graded.stderr)

    def test_a_live_process_in_the_registry_stops_the_grade(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        campaign = runner.Campaign(self.campaign)
        campaign.append_jsonl(campaign.processes, {
            "event": "started", "token": "t", "trial": tid, "attempt": 0,
            "kind": "comparison", "pid": os.getpid(), "at": runner.now_iso()})
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 1, graded.stdout)
        self.assertIn("processes.jsonl", graded.stderr)

    def test_a_continuation_capture_s_live_pid_stops_the_grade(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        runner.write_text(os.path.join(self.campaign, "trials", tid, "harness-first",
                                       "child.pid"), "%d\n" % os.getpid())
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 1, graded.stdout)

    def test_routing_score_refuses_while_a_scored_record_s_process_is_alive(self):
        """Finding 8: `routing-score` opened the held-out set with a child still alive."""
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        runner.write_text(os.path.join(self.campaign, "trials", tid, "harness", "child.pid"),
                          "%d\n" % os.getpid())
        scored = cli(["routing-score", "--campaign", self.campaign])
        self.assertEqual(scored.returncode, 1, scored.stdout)
        self.assertIn("still alive", scored.stderr)

    def test_a_dead_child_pid_does_not_stop_the_grade(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        runner.write_text(os.path.join(self.campaign, "trials", tid, "harness", "child.pid"),
                          "%d\n" % dead.pid)
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)


class StageAndInstallLinkTest(RunnerCase):
    """E10-40: a link is refused by `stage`, and surveyed in a home."""

    def test_the_link_survey_names_a_link_that_leaves_the_tree(self):
        inside = os.path.join(self.scratch, "tree")
        runner.ensure_dir(inside)
        runner.write_text(os.path.join(inside, "a.txt"), "a\n")
        outside = os.path.join(self.scratch, "outside.txt")
        runner.write_text(outside, "b\n")
        os.symlink(outside, os.path.join(inside, "link-out"))
        os.symlink(os.path.join(inside, "a.txt"), os.path.join(inside, "link-in"))
        survey = runner.link_survey(inside)
        self.assertEqual(len(survey["symlinks"]), 2)
        self.assertEqual([r["path"] for r in survey["symlinks_leaving_the_tree"]], ["link-out"])
        self.assertEqual(survey["symlinks_refused"], [])
        allowed = runner.link_survey(inside, allowed_targets=[self.scratch])
        self.assertEqual(allowed["symlinks_leaving_the_tree"], [])

    def test_a_link_into_the_checkout_or_the_campaign_is_refused(self):
        """E10-40 as the fix round reads it: a link is refused when it points at the place the
        rule protects — the checkout, where the key lives, or the campaign records."""
        inside = os.path.join(self.scratch, "home")
        runner.ensure_dir(inside)
        os.symlink(runner.KEY_DIR, os.path.join(inside, "peek"))
        os.symlink("/usr/bin/python3", os.path.join(inside, "python"))
        survey = runner.link_survey(
            inside, allowed_targets=[self.scratch],
            forbidden_targets=runner.protected_roots(runner.Campaign(self.campaign)))
        self.assertEqual([r["path"] for r in survey["symlinks_refused"]], ["peek"])
        self.assertEqual(sorted(r["path"] for r in survey["symlinks_leaving_the_tree"]),
                         ["peek", "python"])

    def test_the_link_survey_names_a_hard_link(self):
        inside = os.path.join(self.scratch, "hard")
        runner.ensure_dir(inside)
        first = os.path.join(inside, "a.txt")
        runner.write_text(first, "a\n")
        os.link(first, os.path.join(inside, "b.txt"))
        survey = runner.link_survey(inside)
        self.assertEqual(sorted(r["path"] for r in survey["hard_links"]), ["a.txt", "b.txt"])


if __name__ == "__main__":
    unittest.main()
