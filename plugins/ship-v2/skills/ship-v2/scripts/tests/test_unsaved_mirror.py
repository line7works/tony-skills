"""The E15 lane contract A31 (1) (contract sections 3.3, 3.8 and 3.11): an unsaved verdict mirror ends the run as
recheck stopped.

When THE SAVE STEP (A30 (1)) cannot be taken (the owner declines it, a pre-commit hook refuses the commit, git cannot
commit), the run sat at `fixed` for ever before this round: the recheck-v2 visit refuses, `report` was out of turn,
and a pause's answer put the run back at `fixed` (slice 3 check 1's C3-1). Now `report` at `fixed` while a recorded
mirror is unsaved ends the run STOPPED with the existing `recheck-stopped` tag, its reason naming the unsaved file
and why the step was not taken, in the refusal's own words; no new stop word. THE WINDOW RULE holds first, as at
every report (a doc moved is stop 2, a path outside the footprint stop 4, an unnamed path inside it refused).
`report` at `fixed` with the mirror saved still refuses as before (exit 2): the next move is the recheck visit.

The stand-in tests reuse `test_save_step.Loop` (a copy of this core beside stand-in stations, the mirror written
untracked by the stand-in signoff-v2); the real-loop test drives the real build-v2, signoff-v2 and recheck-v2 through
the replay's own path (the control room's probe shapes s6 and s7)."""
import os
import shlex
import subprocess
import unittest

import slib
import testlib
from test_save_step import COPY_TEXT, MIRROR, MIRROR_TEXT, STEP, Loop, _replay, run_dir_digest

BOTTOM = "The save step was not taken. The owner decides what comes next."
REFUSING_HOOK = "#!/bin/sh\necho 'pre-commit: refused (a test hook)' >&2\nexit 1\n"


def git_with_hooks(ws, args, hooks):
    """git as the executor runs it in a repository whose hooks are on (`testlib.git` turns them off)."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"), "LANG": "C", "LC_ALL": "C",
           "TZ": "UTC", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.invalid",
           "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    proc = subprocess.run(["git", "-c", "core.hooksPath=%s" % hooks, "-c", "commit.gpgsign=false"] + list(args),
                          cwd=ws, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stderr.decode("utf-8", "replace")


class Ending(Loop):
    """A run at `fixed` (lap 1) whose mirror the stand-in signoff-v2 wrote untracked."""

    def phase(self):
        return testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))["phase"]

    def report(self):
        return slib.report(self.drive, self.run_dir, BOTTOM)

    def assert_ended_recheck_stopped(self, why, laps=0, recheck="not reached"):
        ws_head = testlib.git(self.ws, ["rev-parse", "HEAD"])
        lines = len(slib.trace(self.run_dir))
        code, out, err = self.report()
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "recheck-stopped"), out)
        self.assertIn(MIRROR, out["reason"])
        self.assertIn(why, out["reason"])
        self.assertIn(STEP, out["reason"])
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "result.json")))
        self.assertEqual(self.phase(), "done")
        result = out["station_result"]
        self.assertEqual(result["result_line"], "STOPPED (recheck-v2: recheck-stopped)")
        self.assertEqual((result["recheck"], result["laps"]["taken"]), (recheck, laps), result)
        self.assertIn("Result: STOPPED (recheck-v2: recheck-stopped)", result["chat"])
        self.assertEqual(len(slib.trace(self.run_dir)), lines, "no visit and no trace line")
        self.assertEqual(slib.validate_trace(self.run_dir)[0], 0)
        self.assertEqual(testlib.git(self.ws, ["rev-parse", "HEAD"]), ws_head, "no commit made by the script")
        return out


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class AnUnsavedMirrorEndsTheRun(Ending):

    def test_the_owner_declines_the_step_and_report_ends_recheck_stopped(self):
        """s6: the step is never taken; `report` at `fixed` ends the run, naming the file and why (untracked)."""
        status = testlib.git(self.ws, ["status", "--porcelain"])
        out = self.assert_ended_recheck_stopped("untracked")
        self.assertEqual(testlib.git(self.ws, ["status", "--porcelain"]), status, "the workspace as it stood")
        self.assertEqual(out["station_result"]["build"], "COMPLETE")

    def test_a_pause_answered_then_report_ends_recheck_stopped(self):
        """s6 as the probe ran it: the owner is asked, says no; the answer returns the run to `fixed`, and `report`
        ends it there."""
        code, out, err = self.drive(["pause", "--run-dir", self.run_dir, "--question", slib.question_file(
            self.tmp, self.run_dir, "May I commit the verdict mirror?", source="ship", station=None)])
        self.assertEqual((code, out["next"]), (0, "pause --answer"), (out, err))
        code, out, err = self.drive(["pause", "--run-dir", self.run_dir, "--answer", slib.answer_file(
            self.tmp, self.run_dir, 1, "No, do not commit it.")])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))
        out = self.assert_ended_recheck_stopped("untracked")
        self.assertEqual(out["station_result"]["pauses"][0]["words"], "No, do not commit it.")

    def test_a_pre_commit_hook_refuses_the_commit_and_report_ends_recheck_stopped(self):
        """s7: `git add` lands, the hook refuses `git commit`; the visit refuses (staged, never committed), and
        `report` ends the run with those words. The hook is never bypassed."""
        hooks = os.path.join(self.tmp, "hooks")
        testlib.write_text(os.path.join(hooks, "pre-commit"), REFUSING_HOOK)
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)
        exits = [git_with_hooks(self.ws, shlex.split(c)[1:], hooks)[0] for c in self.fixed["save_step"]["commands"]]
        self.assertEqual(exits, [0, 1])
        self.assert_refused_naming_the_step("staged, never committed")
        self.assert_ended_recheck_stopped("staged, never committed")

    def test_a_mirror_committed_at_other_bytes_ends_recheck_stopped_with_those_words(self):
        self.write(MIRROR, MIRROR_TEXT + "a line the executor added\n")
        testlib.git(self.ws, ["add", "--", MIRROR])
        testlib.git(self.ws, ["commit", "-q", "-m", "other bytes", "--", MIRROR])
        self.write(MIRROR, MIRROR_TEXT)
        self.assert_ended_recheck_stopped("differs from its committed bytes")

    def test_the_extra_lap_unsaved_ends_recheck_stopped(self):
        """Lap 2: recheck-v2 appended its copy, the step is not taken again, `report` ends it; one lap closed."""
        self.take(self.fixed["save_step"])
        code, out, err = self.open_recheck()
        self.assertEqual(code, 0, (out, err))
        before = slib.sha(self.path(MIRROR))
        with open(self.path(MIRROR), "a", encoding="utf-8") as fh:
            fh.write(COPY_TEXT)
        row = {"kind": "verdict_doc_copy", "path": self.path(MIRROR), "appended": True, "sha256_before": before,
               "sha256_after": slib.sha(self.path(MIRROR))}
        slib.put_result(out, slib.station_result("recheck-v2", "not_clear", out, self.ws, writes=[row]))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual((code, out["next"]), (0, "lap"), (out, err))
        code, out, err = self.drive(["lap", "--run-dir", self.run_dir])
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        self.fix(2)
        self.assert_ended_recheck_stopped("differs from its committed bytes", laps=1, recheck="NOT CLEAR")

    def test_the_window_holds_first_a_path_outside_the_footprint_is_stop_4(self):
        self.write("README.md", "# Turnstile\n\nedited after the fix\n")
        code, out, err = self.report()
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "outside-footprint", out)
        self.assertIn("README.md", out["reason"])

    def test_the_window_holds_first_an_unnamed_path_inside_the_footprint_is_refused(self):
        self.write("src/turnstile.py", "def spin(count):\n    return count + 9\n")
        digest = run_dir_digest(self.run_dir)
        code, out, err = self.report()
        self.assertEqual(code, 5, (out, err))
        self.assertIn("src/turnstile.py", out["reason"])
        self.assertEqual((run_dir_digest(self.run_dir), self.phase()), (digest, "fixed"))


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class ASavedMirrorStillRefusesTheReport(Ending):

    def test_report_at_fixed_with_the_mirror_saved_is_out_of_turn(self):
        self.take(self.fixed["save_step"])
        digest = run_dir_digest(self.run_dir)
        code, out, err = self.report()
        self.assertEqual(code, 2, (out, err))
        self.assertIn("visit --station recheck-v2", err)
        self.assertEqual((run_dir_digest(self.run_dir), self.phase()), (digest, "fixed"))
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["next"]), (0, "visit --result"), (out, err))


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class AnIgnoredMirrorUnsaved(Ending):

    ignore_reviews = True

    def test_report_names_the_ignore_rules(self):
        out = self.assert_ended_recheck_stopped("untracked")
        self.assertIn("ignore", out["reason"])


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheRealLoopEndsWhenTheStepIsNotTaken(unittest.TestCase):
    """The control room's probe shapes s6 and s7 through the real build-v2, signoff-v2 and recheck-v2."""

    def setUp(self):
        self.R = _replay()
        self.tmp = testlib.make_scratch("ship-unsaved-real-")
        self.addCleanup(testlib.rmtree, self.tmp)
        python, note = self.R.interpreter()
        answers = self.R.read_json(os.path.join(self.R.FIXTURE, "answers.json"))
        roots = dict((s, os.path.join(self.R.PLUGINS, s)) for s in self.R.OWN_ROOTS + ("readers", "records"))
        self.p = self.R.Path(os.path.join(self.tmp, "findings"), "findings", roots, answers, python, note)
        self.p.setup()
        self.p.begin()
        self.p.build_visit()
        after = self.p.signoff_visit()
        self.assertEqual(after.get("next"), "fix", after)
        self.fixed = self.p.fix(after)
        self.mirror = self.fixed["save_step"]["files"][0]

    def test_declined_then_report_ends_recheck_stopped(self):
        ended = self.p.ship(["report", "--bottom-line", BOTTOM], 10)
        self.assertEqual((ended["status"], ended["stop_tag"]), ("stopped", "recheck-stopped"), ended)
        self.assertIn(self.mirror, ended["reason"])
        self.assertIn("untracked", ended["reason"])
        self.assertEqual(ended["station_result"]["recheck"], "not reached")

    def test_a_refusing_hook_then_report_ends_recheck_stopped(self):
        hooks = os.path.join(self.tmp, "hooks")
        testlib.write_text(os.path.join(hooks, "pre-commit"), REFUSING_HOOK)
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)
        exits = [git_with_hooks(self.p.ws, shlex.split(c)[1:], hooks)[0] for c in self.fixed["save_step"]["commands"]]
        self.assertEqual(exits, [0, 1])
        self.p.ship(["visit", "--station", "recheck-v2"], 5)
        ended = self.p.ship(["report", "--bottom-line", BOTTOM], 10)
        self.assertEqual((ended["status"], ended["stop_tag"]), ("stopped", "recheck-stopped"), ended)
        self.assertIn("staged, never committed", ended["reason"])


if __name__ == "__main__":
    unittest.main()
