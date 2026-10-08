"""The E15 lane contract A30 (contract sections 3.4 and 3.11): ship-v2 names recheck-v2's save step, and reads
recheck-v2's other endings as `recheck-stopped`.

A30 (1), THE SAVE STEP. recheck-v2's own contract (its section 9, E13's F8) requires the signoff verdict mirror under
`docs/reviews/` to be committed before a recheck: its boundary check reads a change to an untracked mirror as a
violation. Before every recheck-v2 visit the executor commits the mirror locally (exactly that file, nothing else), a
named step outside any ship script; `visit --station recheck-v2` refuses, exit 5 and nothing written, while the mirror
is untracked or differs from its committed bytes, naming the step and the file; the window rule takes that commit as
the session's sanctioned step when it holds exactly the mirror as it stood, and holds any other file in it as it holds
any move.

A30 (2). recheck-v2's `missing_input` result, and any status other than `completed` or `nothing_open`, carries its
own envelope (no checklist); `visit --result` takes it, bound by its run block, and the run ends `recheck-stopped`
(section 3.4's table), never `visit-unfinished`.

The stand-in tests drive a copy of this core beside stand-in stations (`slib`); the real-loop tests drive the real
build-v2, signoff-v2 and recheck-v2 through the replay's own path (`evals/replay/replay.py`), the join's probe shape.
"""
import copy
import json
import os
import shlex
import subprocess
import sys
import unittest

import slib
import testlib

MIRROR = "docs/reviews/2026-09-24-signoff-turnstile-a.md"
MIRROR_TEXT = "# Signoff: turnstile, slice A\n\nVerdict: signed off with conditions\n"
COPY_TEXT = "\n### 2026-09-25 recheck: slice A\n- not fixed: the counter skips a turn\n"
FIXED = "def spin(count):\n    return count + %d\n"
REPLAY = os.path.join(testlib.PLUGIN, "evals", "replay", "replay.py")
STEP = "save the verdict mirror"


def run_dir_digest(run_dir):
    return testlib.tree_digest(run_dir)


class Loop(unittest.TestCase):
    """A run brought to the recheck-v2 visit with a stand-in signoff-v2 that wrote the verdict mirror untracked."""

    ignore_reviews = False

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-save-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        if self.ignore_reviews:
            testlib.write_text(os.path.join(self.ws, ".gitignore"), "docs/reviews/\n")
            slib.commit_all(self.ws, "ignore the reviews")
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir)
        code, out, err = slib.visit(self, self.drive, self.run_dir, "build-v2", "completed", self.ws,
                                    before_result=lambda visit: slib.set_status(self.ws, "A", "built"))
        self.assertEqual(code, 0, (out, err))
        code, out, err = self.signoff()
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        self.fixed = self.fix(1)

    # ---- the stations, as they write -----------------------------------------------------------------------

    def path(self, rel):
        return os.path.join(self.ws, rel)

    def write(self, rel, text):
        testlib.write_text(self.path(rel), text)

    def signoff(self):
        """signoff-v2's visit: its finding and card through the records, its `Status:` line, and the verdict mirror
        under `docs/reviews/`, untracked, listed in its result (`verdict_doc`) and in its receipt's document steps."""
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "signoff-v2"])
        self.assertEqual(code, 0, (out, err))
        before = slib.sha(self.path(slib.DOC))
        self.finding = slib.raise_finding(self.tmp, self.ws)
        slib.set_status(self.ws, "A", "signed off with conditions")
        self.write(MIRROR, MIRROR_TEXT)
        after = slib.sha(self.path(slib.DOC))
        result = slib.station_result("signoff-v2", "findings", out, self.ws, doc_move=(before, after))
        result["records_written"].append({"kind": "verdict_doc", "path": self.path(MIRROR)})
        receipt = testlib.load_json(result["receipt"])
        receipt["steps"].append({"kind": "verdict_doc", "target": MIRROR, "before_sha256": None,
                                 "after_sha256": slib.sha(self.path(MIRROR)), "state": "done"})
        testlib.write_json(result["receipt"], receipt)
        slib.put_result(out, result)
        return self.drive(["visit", "--run-dir", self.run_dir, "--result"])

    def fix(self, lap):
        self.write("src/turnstile.py", FIXED % (lap + 1))
        code, out, err = self.drive(["fix", "--run-dir", self.run_dir, "--fixes", slib.fixes_file(
            self.tmp, self.run_dir, lap, [{"finding": self.finding, "paths": ["src/turnstile.py"],
                                           "summary": "lap %d" % lap}], name="fixes-%d.json" % lap)])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))
        return out

    def take(self, step):
        """The named step, run as ship-v2 printed it (every command a git command, run in the workspace)."""
        for command in step["commands"]:
            argv = shlex.split(command)
            self.assertEqual(argv[0], "git", command)
            testlib.git(self.ws, argv[1:])

    def head_files(self):
        return sorted(testlib.git(self.ws, ["show", "--name-only", "--format=", "HEAD"]).split())

    def open_recheck(self):
        return self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])

    def assert_refused_naming_the_step(self, why):
        digest, ws_head = run_dir_digest(self.run_dir), testlib.git(self.ws, ["rev-parse", "HEAD"])
        lines = len(slib.trace(self.run_dir))
        code, out, err = self.open_recheck()
        self.assertEqual(code, 5, (out, err))
        self.assertFalse(out["accepted"])
        self.assertIn(MIRROR, out["reason"])
        self.assertIn(STEP, out["reason"])
        self.assertIn(why, out["reason"])
        self.assertEqual(out["save_step"]["files"], [MIRROR])
        self.assertEqual(run_dir_digest(self.run_dir), digest, "nothing written")
        self.assertEqual(len(slib.trace(self.run_dir)), lines)
        self.assertEqual(testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))["phase"], "fixed")
        self.assertEqual(testlib.git(self.ws, ["rev-parse", "HEAD"]), ws_head)
        return out


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheSaveStep(Loop):

    def test_fix_names_the_step_and_the_mirror(self):
        step = self.fixed["save_step"]
        self.assertEqual(step["files"], [MIRROR])
        self.assertIn(STEP, step["step"])
        self.assertEqual([shlex.split(c)[:2] for c in step["commands"]], [["git", "add"], ["git", "commit"]])
        for command in step["commands"]:
            self.assertEqual(shlex.split(command)[-2:], ["--", MIRROR], command)
            self.assertNotIn("push", shlex.split(command))

    def test_an_untracked_mirror_refuses_the_recheck_visit_naming_the_step_and_the_file(self):
        self.assert_refused_naming_the_step("untracked")

    def test_a_mirror_staged_but_not_committed_still_refuses(self):
        testlib.git(self.ws, ["add", "--", MIRROR])
        self.assert_refused_naming_the_step("committed")

    def test_a_mirror_committed_at_other_bytes_refuses(self):
        self.write(MIRROR, MIRROR_TEXT + "a line the executor added\n")
        testlib.git(self.ws, ["add", "--", MIRROR])
        testlib.git(self.ws, ["commit", "-q", "-m", "other bytes", "--", MIRROR])
        self.write(MIRROR, MIRROR_TEXT)
        self.assert_refused_naming_the_step("differs from its committed bytes")

    def test_the_step_taken_as_printed_opens_the_visit_and_commits_exactly_the_mirror(self):
        self.take(self.fixed["save_step"])
        self.assertEqual(self.head_files(), [MIRROR])
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["next"], out["visited"]), (0, "visit --result", "recheck-v2"), (out, err))
        self.assertIn("src/turnstile.py", testlib.git(self.ws, ["status", "--porcelain"]))

    def test_the_step_printed_by_the_refusal_is_the_same_step(self):
        out = self.assert_refused_naming_the_step("untracked")
        self.assertEqual(out["save_step"], self.fixed["save_step"])
        self.take(out["save_step"])
        code, out, err = self.open_recheck()
        self.assertEqual(code, 0, (out, err))

    def test_a_commit_carrying_a_file_outside_the_footprint_beside_the_mirror_is_stop_4(self):
        self.write("README.md", "# Turnstile\n\nedited beside the mirror\n")
        testlib.git(self.ws, ["add", "--", MIRROR, "README.md"])
        testlib.git(self.ws, ["commit", "-q", "-m", "the mirror and more"])
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["next"], out["stop_tag"]), (0, "report", "outside-footprint"), (out, err))
        self.assertIn("README.md", out["reason"])
        self.assertNotIn(MIRROR, out["reason"])

    def test_a_commit_carrying_the_lap_fix_as_it_stood_beside_the_mirror_is_held_as_today(self):
        testlib.git(self.ws, ["add", "--", MIRROR, "src/turnstile.py"])
        testlib.git(self.ws, ["commit", "-q", "-m", "the mirror and the fix as it stood"])
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["next"]), (0, "visit --result"), (out, err))

    def test_a_commit_carrying_an_unnamed_change_inside_the_footprint_is_refused(self):
        self.write("src/turnstile.py", FIXED % 9)
        testlib.git(self.ws, ["add", "--", MIRROR, "src/turnstile.py"])
        testlib.git(self.ws, ["commit", "-q", "-m", "the mirror and an unnamed change"])
        digest = run_dir_digest(self.run_dir)
        code, out, err = self.open_recheck()
        self.assertEqual(code, 5, (out, err))
        self.assertIn("src/turnstile.py", out["reason"])
        self.assertEqual(run_dir_digest(self.run_dir), digest)

    def test_a_hand_edit_of_the_mirror_then_committed_is_stop_4(self):
        self.write(MIRROR, MIRROR_TEXT + "a hand edit\n")
        testlib.git(self.ws, ["add", "--", MIRROR])
        testlib.git(self.ws, ["commit", "-q", "-m", "an edited mirror", "--", MIRROR])
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["stop_tag"]), (0, "outside-footprint"), (out, err))
        self.assertIn(MIRROR, out["reason"])

    def test_the_next_lap_needs_the_step_again_after_recheck_appended_its_copy(self):
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
        fixed = self.fix(2)
        self.assertEqual(fixed["save_step"]["files"], [MIRROR])
        self.assert_refused_naming_the_step("differs from its committed bytes")
        self.take(fixed["save_step"])
        self.assertEqual(self.head_files(), [MIRROR])
        code, out, err = self.open_recheck()
        self.assertEqual(code, 0, (out, err))


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class AnIgnoredMirror(Loop):
    """A repository that ignores `docs/reviews/`: the pin never sees the mirror, so only the save step's own rule
    takes its commit; a hand edit before that commit is held as any move."""

    ignore_reviews = True

    def force(self):
        testlib.git(self.ws, ["add", "--force", "--", MIRROR])
        testlib.git(self.ws, ["commit", "-q", "-m", "the mirror", "--", MIRROR])

    def test_the_refusal_says_the_repository_ignores_it(self):
        out = self.assert_refused_naming_the_step("untracked")
        self.assertIn("ignore", out["reason"])

    def test_the_mirror_committed_as_it_stood_is_the_sanctioned_step(self):
        self.force()
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["next"]), (0, "visit --result"), (out, err))

    def test_a_hand_edit_before_the_commit_is_held_as_a_move(self):
        self.write(MIRROR, MIRROR_TEXT + "a hand edit\n")
        self.force()
        code, out, err = self.open_recheck()
        self.assertEqual((code, out["stop_tag"]), (0, "outside-footprint"), (out, err))


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class RecheckEndsWithItsOwnEnvelope(unittest.TestCase):
    """A30 (2): each recheck-v2 status other than completed or nothing_open, in its own envelope (no checklist where
    its schema gives none), is taken at `visit --result` and ends the run `recheck-stopped`."""

    EXAMPLES = (("missing_input", "result-missing-input-headless.json"), ("stale_source", "result-stale-source.json"),
                ("verifier_unavailable", "result-verifier-unavailable.json"), ("stopped", "result-stopped.json"))

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-stops-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir)
        code, out, err = slib.visit(self, self.drive, self.run_dir, "build-v2", "completed", self.ws,
                                    before_result=lambda visit: slib.set_status(self.ws, "A", "built"))
        self.assertEqual(code, 0, (out, err))
        found = []

        def signoff_writes(visit):
            found.append(slib.raise_finding(self.tmp, self.ws))
            slib.set_status(self.ws, "A", "signed off with conditions")
        code, out, err = slib.visit(self, self.drive, self.run_dir, "signoff-v2", "findings", self.ws,
                                    before_result=signoff_writes)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        testlib.write_text(os.path.join(self.ws, "src/turnstile.py"), FIXED % 2)
        code, out, err = self.drive(["fix", "--run-dir", self.run_dir, "--fixes", slib.fixes_file(
            self.tmp, self.run_dir, 1, [{"finding": found[0], "paths": ["src/turnstile.py"], "summary": "lap 1"}])])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))
        code, self.visit, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 0, (self.visit, err))

    def envelope(self, name):
        """The real recheck-v2's own example, its run block set to this visit's (the station names itself there)."""
        real = slib.real_station("recheck-v2")
        doc = copy.deepcopy(testlib.load_json(os.path.join(real, "skills", "recheck-v2", "references", "examples",
                                                           name)))
        run_dir = self.visit["visit_run_dir"]
        doc["run"].update(run_id=self.visit["visit_run_id"], run_dir=run_dir)
        doc["run"]["invocation"].update(mode="headless", caller="ship-v2")
        doc["run"]["skill"].update(name="recheck-v2", version=slib.real_version("recheck-v2"))
        doc["records_written"] = [dict(row, path=os.path.join(run_dir, os.path.basename(row["path"])))
                                  for row in doc.get("records_written") or [] if row["kind"] == "run_artifact"]
        if "checklist" in doc:
            doc["checklist"].update(build_doc=slib.DOC, slice="A")
        return doc

    def test_each_other_ending_is_recheck_stopped(self):
        for status, name in self.EXAMPLES:
            with self.subTest(status=status):
                if status != self.EXAMPLES[0][0]:
                    self.setUp()
                doc = self.envelope(name)
                self.assertEqual(doc["status"], status)
                slib.put_result(self.visit, doc)
                code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
                self.assertEqual((code, out["next"], out.get("stop_tag")), (0, "report", "recheck-stopped"),
                                 (status, out, err))
                code, out, err = slib.report(self.drive, self.run_dir)
                self.assertEqual(code, 10, (out, err))
                self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "recheck-stopped"), out)
                self.assertEqual(out["station_result"]["recheck"], status)
                self.assertNotIn("visit-unfinished", json.dumps(out))
                self.assertEqual(slib.validate_trace(self.run_dir)[0], 0)
                closing = slib.trace(self.run_dir)[-1]
                self.assertEqual((closing["expected"], closing["status"]), ("recheck-v2", status))

    def test_a_missing_input_result_for_another_run_is_still_refused(self):
        doc = self.envelope("result-missing-input-headless.json")
        doc["run"]["run_id"] = "another-run"
        slib.put_result(self.visit, doc)
        digest = run_dir_digest(self.run_dir)
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("another-run", out["reason"])
        self.assertEqual(run_dir_digest(self.run_dir), digest)

    def test_a_result_with_no_run_block_is_still_refused(self):
        real = slib.real_station("recheck-v2")
        doc = testlib.load_json(os.path.join(real, "skills", "recheck-v2", "references", "examples",
                                             "result-invalid-input-envelope.json"))
        self.assertNotIn("run", doc)
        slib.put_result(self.visit, doc)
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual(code, 5, (out, err))


def _replay():
    sys.path.insert(0, os.path.dirname(REPLAY))
    try:
        import replay  # noqa: E402
    finally:
        sys.path.remove(os.path.dirname(REPLAY))
    return replay


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheJoinsProbeShapeOnTheRealLoop(unittest.TestCase):
    """The join's probe shape (slice 3's Q1): the findings path through the real build-v2, signoff-v2 and recheck-v2,
    the verdict mirror left untracked after the lap's fix. The recheck-v2 visit is refused naming the step, nothing
    written; with the step taken as ship-v2 printed it, the same path reaches ALL CLEAR with the real recheck-v2."""

    def setUp(self):
        self.R = _replay()
        self.tmp = testlib.make_scratch("ship-save-real-")
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
        self.mirrors = sorted(os.path.relpath(row["path"], self.p.ws)
                              for row in self.p.signoff_result["records_written"] if row["kind"] == "verdict_doc")
        self.assertEqual(len(self.mirrors), 1, self.mirrors)

    def test_the_untracked_mirror_is_refused_then_the_step_reaches_all_clear(self):
        digest = run_dir_digest(self.p.ship_run)
        refused = self.p.ship(["visit", "--station", "recheck-v2"], 5)
        self.assertIn(self.mirrors[0], refused["reason"])
        self.assertIn(STEP, refused["reason"])
        self.assertEqual(refused["save_step"]["files"], self.mirrors)
        self.assertEqual(run_dir_digest(self.p.ship_run), digest, "nothing written")
        self.assertEqual(self.fixed["save_step"], refused["save_step"])
        self.p.take_save_step(refused["save_step"])
        self.assertEqual(sorted(self.p.git(["show", "--name-only", "--format=", "HEAD"]).split()), self.mirrors)
        self.p.recheck_visit()
        self.assertEqual(self.p.recheck_result.get("result"), "all_clear", self.p.recheck_result)
        self.assertEqual(self.p.recheck_result.get("boundary_violations"), [])
        self.p.finish()
        loop = self.p.assert_loop()
        self.assertEqual((loop["status"], loop["result_line"], loop["card"], loop["laps"]),
                         ("completed", "ALL CLEAR", "signed off", 1), self.p.problems)

    def test_the_real_recheck_v2_missing_input_ends_recheck_stopped(self):
        self.p.take_save_step(self.fixed["save_step"])
        visit, root = self.p.open_visit("recheck-v2")
        run_dir = visit["visit_run_dir"]
        doc = {"protocol_version": 1, "workspace": self.p.ws, "target": {"build_doc": self.R.DOC, "slice": "Z"},
               "invocation": {"mode": visit["mode"], "caller": visit["caller"], "run_id": visit["visit_run_id"],
                              "run_dir": run_dir, "resume": False, "run_date": self.R.DATE,
                              "harness": {"name": "replay", "version": "0", "entry": "explicit path",
                                          "sandbox": "none"},
                              "model": {"id": self.R.REPLAY_MODEL, "floor_class": "opus", "floor_met": True},
                              "session_wrote_fix": True}}
        path = self.R.write_json(run_dir + ".input.json", doc)
        self.p.cli("recheck-v2", root, ["start", path], None)
        result = self.R.read_json(os.path.join(run_dir, "result.json"))
        self.assertEqual(result["status"], "missing_input", result)
        self.assertNotIn("checklist", result)
        closed = self.p.ship(["visit", "--result"], 0)
        self.assertEqual((closed["next"], closed["stop_tag"]), ("report", "recheck-stopped"), closed)
        ended = self.p.ship(["report", "--bottom-line", "The recheck asked for input."], 10)
        self.assertEqual((ended["status"], ended["stop_tag"]), ("stopped", "recheck-stopped"), ended)
        self.assertEqual(ended["station_result"]["recheck"], "missing_input")


if __name__ == "__main__":
    unittest.main()
