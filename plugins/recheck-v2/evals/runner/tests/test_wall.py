"""The wall of lane contract section 3, and the E10-21 stand-in.

Every launch path runs with `evals/answer-key/` and `evals/trigger-set/held-out/` replaced by
unreadable stand-ins; the grade path refuses while a harness process for that trial is alive;
a key stand-in outside a test is refused.
"""
import os
import shutil
import stat
import subprocess
import sys
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, FAKE, CASE


class UnreadableCopy(object):
    """A copy of the plugin whose answer-key and held-out directories cannot be read.

    The launch paths are exercised against this copy, so a launch that opened either one would
    fail with a permission error instead of passing quietly.
    """

    def __init__(self, scratch):
        self.root = os.path.join(scratch, "walled")
        shutil.copytree(os.path.dirname(runner.RUNNER_DIR), os.path.join(self.root, "evals"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.key = os.path.join(self.root, "evals", "answer-key")
        self.heldout = os.path.join(self.root, "evals", "trigger-set", "held-out")
        for path in (self.key, self.heldout):
            if not os.path.isdir(path):
                os.makedirs(path)
            os.chmod(path, 0o000)

    def release(self):
        for path in (self.key, self.heldout):
            try:
                os.chmod(path, 0o700)
            except OSError:
                pass
        shutil.rmtree(self.root, ignore_errors=True)

    def unreadable(self):
        """True when neither directory can be listed."""
        out = []
        for path in (self.key, self.heldout):
            try:
                os.listdir(path)
                out.append(False)
            except OSError:
                out.append(True)
        return all(out)


class WalledLaunchTest(RunnerCase):
    """Run every launch path with both directories unreadable."""

    def setUp(self):
        RunnerCase.setUp(self)
        self.walled = UnreadableCopy(self.scratch)
        self.addCleanup(self.walled.release)

    def test_the_stand_ins_really_are_unreadable(self):
        self.assertTrue(self.walled.unreadable(),
                        "the test's own stand-ins are readable; the proof would be empty")

    def test_the_comparison_launch_path_runs_with_both_directories_unreadable(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(parse_stdout(got)["status"], "complete")
        self.assertTrue(self.walled.unreadable())

    def test_the_routing_launch_path_runs_with_both_directories_unreadable(self):
        tid = runner.routing_trial_id("claude-code", "T-01-slash-v2-slice", 1)
        got = cli(["routing", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertTrue(self.walled.unreadable())

    def test_the_continuation_launch_path_runs_with_both_directories_unreadable(self):
        tid = runner.continuation_trial_id("claude-code", "F3-02-mixed-two-items", "handoff", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertIn(got.returncode, (0, 1), got.stderr)
        self.assertTrue(self.walled.unreadable())

    def test_the_probe_launch_path_never_reads_either_directory(self):
        """`probe-env` launches too, and its half of the file names no key reader."""
        source = runner.read_text(runner.__file__)
        launch_half = source.split(
            "# --------------------------------------------------------------------------- the wall")[0]
        self.assertIn("def do_probe_env", launch_half)
        for reader in ("key_entry(", "request_text(", "expectation_of(", "heldout_entry_ids(",
                       "key_dir()", "heldout_file()"):
            self.assertNotIn(reader, launch_half, "%s is above the wall marker" % reader)


class WallStructureTest(unittest.TestCase):
    """Which functions in `runner.py` can reach the key or the held-out set, by the AST.

    Only the grading half and the one-entry routing lookup E10-13 allows may name a reader; a
    new launch helper that reached one would show up here as an extra name.
    """

    READERS = ("key_dir", "heldout_file", "key_entry", "heldout_entry_ids", "request_text",
               "expectation_of", "_routing_entry_ids")
    ALLOWED = {
        # the readers themselves
        "key_dir", "heldout_file", "key_entry", "heldout_entry_ids", "request_text",
        "expectation_of", "_routing_entry_ids",
        # the grading half (E10-11) and the scorer (E10-13)
        "grade_one", "do_grade", "do_routing_score",
        # `routing` at launch time, for the one entry it is launching (E10-13)
        "do_routing",
        # `plan` needs the entry ids to write the order; the ids come from a subprocess
        "do_plan",
    }

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

    def test_no_function_names_the_key_or_held_out_constants_outside_the_readers(self):
        found = self._functions_naming({"KEY_DIR", "TRIGGER_HELDOUT"})
        self.assertEqual(sorted(found), sorted(["key_dir", "heldout_file"]),
                         "an unexpected function names a key constant: %s" % sorted(found))

    def test_the_launch_helpers_name_no_reader_and_no_key_constant(self):
        launchers = ("do_run", "_one_trial", "collect_trial", "do_probe_env", "do_continuation",
                     "_launch_and_cut", "_compaction_resume", "do_install", "do_verify",
                     "do_stage", "do_campaign", "_campaign_loop", "do_rerun", "do_scan",
                     "do_report")
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


class StandInTest(RunnerCase):
    """E10-21: the stand-in is honoured only under RECHECK_RUNNER_TEST=1."""

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

    def test_grade_summary_prints_counts_and_never_a_grade_document(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 0, graded.stderr)
        self.assertNotIn("dispositions", graded.stdout)
        self.assertNotIn("must_not", graded.stdout)
        self.assertNotIn("expected", graded.stdout)


class GradeWaitsForTheHarnessTest(RunnerCase):
    """The grade path refuses to run while a harness process for that trial is alive."""

    def test_a_live_child_pid_in_the_record_stops_the_grade(self):
        directory = self.stand_in_key()
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        # a process that is certainly alive: this test's own
        runner.write_text(os.path.join(self.campaign, "trials", tid, "harness", "child.pid"),
                          "%d\n" % os.getpid())
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        graded = cli(["grade", "--campaign", self.campaign, tid, "--summary"], env=environment)
        self.assertEqual(graded.returncode, 1, graded.stdout)
        self.assertIn("still alive", graded.stderr)

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


if __name__ == "__main__":
    unittest.main()
