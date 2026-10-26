"""E18 slice C: ship-v2 runs the signoff visit in a fresh session (the core's half).

On the Claude Code harness `visit --station signoff-v2` records a session id that is a UUID and differs on each visit,
stages a brief under this ship run's directory that holds exactly the named fields (and, when the input carries one,
the owner's DEEP order with his words verbatim), and prints a `launch_step`. An input `signoff_depth` of `LIGHT` or
`LEAN` is refused. `visit --result` refuses a result whose recorded reviewing session is not the recorded id, refuses
a check reading that does not hold, and accepts a result with both. A visit whose child left no result reports
`visit-unfinished` with the child's `subtype` and `result`. A Codex visit prints no `launch_step`.

The child is never launched: what a real child leaves (the visit's `input.json`, a fixture child transcript under a
fixture home) is planted by `slib.plant_child`, and the reading is the real helper's check mode over it.
"""
import json
import os
import re
import unittest
import uuid

import slib
import testlib

FIELDS = ["Workspace", "Build doc", "Slice", "Build result", "Run id", "Run directory", "invocation.caller",
          "invocation.mode", "signoff-v2 SKILL.md", "signoff-v2 name", "signoff-v2 version",
          "signoff-v2 content hash"]
WORDS = "Go deep on this one: it moves money.\nSecond line, kept as typed."


def brief_fields(text):
    """The `## The visit` section's bullets as [(label, value)]."""
    section = text.split("## The visit\n", 1)[1].split("\n## ", 1)[0]
    return [tuple(line[2:].split(": ", 1)) for line in section.split("\n") if line.startswith("- ")]


def state(run_dir):
    return testlib.load_json(os.path.join(run_dir, "ship.json"))


def digest(run_dir):
    out = {}
    for dirpath, dirnames, filenames in os.walk(run_dir):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            out[os.path.relpath(full, run_dir)] = slib.sha(full)
    return out


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class FreshSignoff(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-e18c-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.tree = slib.Tree(self.tmp)

    def built(self, run="run", harness="claude-code", clock=True, **station):
        """A fresh run through build-v2 COMPLETE, at `built`: (driver, run dir, workspace)."""
        ws = slib.make_repo(self.tmp, name="ws-" + run)
        drive, run_dir = slib.start(self, self.tree, self.tmp, ws, run=run, harness=harness, **station)
        if not clock:
            drive.env.pop(slib.PREFIX + "_TEST_NOW")
        slib.through_hook(self, drive, self.tmp, run_dir, harness=harness)
        code, out, err = slib.visit(self, drive, run_dir, "build-v2", "completed", ws,
                                    before_result=lambda visit: slib.set_status(ws, "A", "built"))
        self.assertEqual((code, out["next"]), (0, "visit --station signoff-v2"), (out, err))
        return drive, run_dir, ws

    def open_signoff(self, drive, run_dir):
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "signoff-v2"])
        self.assertEqual(code, 0, (out, err))
        return out

    # ---- the visit's opening -----------------------------------------------------------------------------------------

    def test_a_signoff_visit_records_a_uuid_session_and_prints_a_launch_step(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        launch = state(run_dir)["visit"]["launch"]
        self.assertEqual(str(uuid.UUID(launch["session_id"])), launch["session_id"])
        step = out["launch_step"]
        self.assertEqual(step["session_id"], launch["session_id"])
        self.assertTrue(step["helper"].endswith(os.path.join("adapters", "claude-code", "launch.py")))
        self.assertTrue(os.path.isfile(step["helper"]))
        self.assertEqual(step["launch"], ["python3", step["helper"], "--run-dir", run_dir])
        self.assertEqual(step["check"], ["python3", step["helper"], "--run-dir", run_dir, "--check"])
        for path in (launch["brief"], launch["stdout"]):
            self.assertEqual(os.path.dirname(path), run_dir)
            self.assertFalse(path.startswith(out["visit_run_dir"] + os.sep))
            self.assertFalse(path.startswith(ws + os.sep))
        self.assertEqual(launch["prompt"], "Read %s and follow it." % launch["brief"])
        self.assertTrue(os.path.isfile(launch["brief"]), "THE SAVE wrote the brief")
        self.assertFalse(os.path.exists(launch["stdout"]), "the child's output is the ship session's to collect")

    def test_the_session_id_differs_on_each_visit(self):
        ids = []
        for run in ("run-1", "run-2"):
            drive, run_dir, ws = self.built(run=run, clock=False)
            self.open_signoff(drive, run_dir)
            ids.append(uuid.UUID(state(run_dir)["visit"]["launch"]["session_id"]))
        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual([i.version for i in ids], [4, 4], "a fresh random id")
        clocked = []
        for run in ("run-3", "run-4"):
            drive, run_dir, ws = self.built(run=run)
            self.open_signoff(drive, run_dir)
            clocked.append(state(run_dir)["visit"]["launch"]["session_id"])
        self.assertNotEqual(clocked[0], clocked[1], "a test's fixed clock still gives each visit its own id")

    def test_the_brief_holds_exactly_the_named_fields(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        held = state(run_dir)
        visit = held["visit"]
        build = [v for v in held["visits"] if v["station"] == "build-v2"][-1]
        text = testlib.read_text(visit["launch"]["brief"])
        rows = brief_fields(text)
        self.assertEqual([label for label, _ in rows], FIELDS)
        self.assertEqual(dict(rows), {
            "Workspace": ws, "Build doc": slib.DOC, "Slice": "A", "Build result": build["result"],
            "Run id": out["visit_run_id"], "Run directory": out["visit_run_dir"], "invocation.caller": "ship-v2",
            "invocation.mode": out["mode"], "signoff-v2 SKILL.md": out["skill_md"],
            "signoff-v2 name": visit["identity"]["name"], "signoff-v2 version": visit["identity"]["version"],
            "signoff-v2 content hash": visit["identity"]["content_sha256"]})
        self.assertEqual(build["result"], os.path.join(held["visits"][0]["run_dir"], "result.json"))
        self.assertIn("No owner is present in this session.", text)
        for words in ("first-run `REVIEW.md` write", "second-failure append stays signoff-v2's own",
                      "Answer no question on the owner's behalf", "the `Next:` line", "`SKILL NOTE:`",
                      "Commit nothing, push nothing"):
            self.assertIn(words, text)
        self.assertNotIn("## The owner's depth order", text)
        self.assertIn("signoff-v2's own rules choose it", text)
        self.assertNotIn("\u2014", text)

    def test_a_deep_order_reaches_the_brief_with_the_owners_words_verbatim(self):
        drive, run_dir, ws = self.built(signoff_depth={"depth": "DEEP", "words": WORDS})
        self.open_signoff(drive, run_dir)
        text = testlib.read_text(state(run_dir)["visit"]["launch"]["brief"])
        rows = brief_fields(text)
        self.assertEqual([label for label, _ in rows], FIELDS + ["Depth"])
        self.assertEqual(rows[-1], ("Depth", "DEEP"))
        self.assertIn("<<<\n%s\n>>>\n" % WORDS, text)

    def test_an_input_depth_of_light_or_lean_is_refused(self):
        ws = slib.make_repo(self.tmp)
        for value in ("LIGHT", "LEAN", "deep"):
            doc = slib.make_input(ws, os.path.join(self.tmp, "run-" + value), run_id="run-" + value, slice="A",
                                  signoff_depth={"depth": value, "words": "my words"})
            path = os.path.join(self.tmp, "input-%s.json" % value)
            testlib.write_json(path, doc)
            code, out, err = slib.Driver(self.tree, self.tmp)(["check-input", path])
            self.assertEqual(code, 4, (value, out, err))
            self.assertFalse(os.path.exists(os.path.join(self.tmp, "run-" + value)))
        doc = slib.make_input(ws, os.path.join(self.tmp, "run-blank"), run_id="run-blank", slice="A",
                              signoff_depth={"depth": "DEEP", "words": "  "})
        testlib.write_json(os.path.join(self.tmp, "input-blank.json"), doc)
        code, out, err = slib.Driver(self.tree, self.tmp)(["check-input", os.path.join(self.tmp, "input-blank.json")])
        self.assertEqual(code, 4, (out, err))

    # ---- the visit's close -----------------------------------------------------------------------------------------

    def signoff_result(self, drive, run_dir, ws, out, which="clean"):
        slib.put_result(out, slib.station_result("signoff-v2", which, out, ws))

    def refused(self, drive, run_dir, args, code=5):
        before = digest(run_dir)
        got, out, err = drive(["visit", "--run-dir", run_dir, "--result"] + args)
        self.assertEqual(got, code, (out, err))
        self.assertEqual(digest(run_dir), before, "nothing written")
        self.assertEqual(testlib.load_json(os.path.join(run_dir, "checkpoint.json"))["phase"], "visiting")
        return out, err

    def test_visit_result_refuses_a_reviewing_session_that_is_not_the_recorded_id(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        sid = state(run_dir)["visit"]["launch"]["session_id"]
        other = "11111111-2222-4333-8444-555555555555"
        args = slib.plant_child(drive.script, self.tmp, run_dir, reviewing=other)
        said, err = self.refused(drive, run_dir, args)
        self.assertIn(other, said["reason"])
        self.assertIn(sid, said["reason"])
        self.assertIn("reviewing session", said["reason"])

    def test_visit_result_refuses_a_check_reading_that_does_not_hold(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        sid = state(run_dir)["visit"]["launch"]["session_id"]
        args = slib.plant_child(drive.script, self.tmp, run_dir, prompt="Run signoff-v2 on slice A yourself.")
        reading = testlib.load_json(args[1])
        self.assertIs(reading["holds"], False)
        said, err = self.refused(drive, run_dir, args)
        self.assertIn("does not hold", said["reason"])
        self.assertIn(sid, said["reason"])

    def test_visit_result_refuses_a_reading_of_another_session(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        args = slib.plant_child(drive.script, self.tmp, run_dir)
        reading = testlib.load_json(args[1])
        reading["session_id"] = "11111111-2222-4333-8444-555555555555"
        testlib.write_json(args[1], reading)
        said, err = self.refused(drive, run_dir, args)
        self.assertIn("11111111-2222-4333-8444-555555555555", said["reason"])

    def test_visit_result_without_a_reading_is_a_usage_slip_naming_the_check(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        slib.plant_child(drive.script, self.tmp, run_dir)
        said, err = self.refused(drive, run_dir, [], code=2)
        self.assertIn("--reading", err)
        self.assertIn("--check", err)

    def test_visit_result_accepts_a_result_with_both(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        args = slib.plant_child(drive.script, self.tmp, run_dir)
        self.assertIs(testlib.load_json(args[1])["holds"], True)
        code, done, err = drive(["visit", "--run-dir", run_dir, "--result"] + args)
        self.assertEqual((code, done["next"]), (0, "report"), (done, err))
        self.assertEqual(state(run_dir)["visits"][-1]["station"], "signoff-v2")
        code, result, err = slib.report(drive, run_dir)
        self.assertEqual((code, result["status"]), (10, "completed"), (result, err))
        brief = state(run_dir)["visits"][-1]["launch"]["brief"]
        self.assertIn(brief, [w["path"] for w in result["writes"] if w["kind"] == "run_artifact"])

    # ---- the visit that ends with no result ------------------------------------------------------------------------

    def test_a_child_that_left_no_result_reports_visit_unfinished_with_its_subtype_and_result(self):
        drive, run_dir, ws = self.built()
        self.open_signoff(drive, run_dir)
        stdout = state(run_dir)["visit"]["launch"]["stdout"]
        testlib.write_json(stdout, {"type": "result", "subtype": "error_max_turns", "is_error": True,
                                    "result": "I reached my turn limit before the verdict."})
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual((code, out["status"], out["stop_tag"]), (10, "stopped", "visit-unfinished"), (out, err))
        self.assertIn('subtype "error_max_turns"', out["reason"])
        self.assertIn('result "I reached my turn limit before the verdict."', out["reason"])

    def test_a_child_with_no_output_file_still_ends_visit_unfinished(self):
        drive, run_dir, ws = self.built()
        self.open_signoff(drive, run_dir)
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "visit-unfinished"), (out, err))
        self.assertNotIn("standard output", out["reason"])

    def test_report_ends_a_visit_whose_reading_does_not_hold(self):
        """The way to a terminal status from the new refusals (the E15 lane contract A31 (2)): `report` at `visiting`
        refuses while the result stands and no reading is given (exit 2, naming both commands), and ends the run
        `visit-unfinished` given a reading that does not hold."""
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        args = slib.plant_child(drive.script, self.tmp, run_dir, prompt="Another prompt.")
        before = digest(run_dir)
        code, said, err = slib.report(drive, run_dir)
        self.assertEqual(code, 2, (said, err))
        self.assertIn("visit --result --reading", err)
        self.assertEqual(digest(run_dir), before)
        code, done, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "The visit ended unread.",
                                 "--reading", args[1]])
        self.assertEqual((code, done["stop_tag"]), (10, "visit-unfinished"), (done, err))
        self.assertIn("does not hold", done["reason"])

    def test_report_ends_a_visit_whose_reviewing_session_is_another(self):
        drive, run_dir, ws = self.built()
        out = self.open_signoff(drive, run_dir)
        self.signoff_result(drive, run_dir, ws, out)
        slib.plant_child(drive.script, self.tmp, run_dir, reviewing="11111111-2222-4333-8444-555555555555")
        code, done, err = slib.report(drive, run_dir)
        self.assertEqual((code, done["stop_tag"]), (10, "visit-unfinished"), (done, err))
        self.assertIn("reviewing session", done["reason"])

    # ---- Codex -----------------------------------------------------------------------------------------------------

    def test_a_codex_visit_prints_no_launch_step(self):
        drive, run_dir, ws = self.built(harness="codex-cli")
        out = self.open_signoff(drive, run_dir)
        self.assertNotIn("launch_step", out)
        self.assertNotIn("launch", state(run_dir)["visit"])
        self.assertFalse([n for n in os.listdir(run_dir) if n.startswith("brief-")])
        self.assertEqual(slib.plant_child(drive.script, self.tmp, run_dir), [])
        slib.put_result(out, slib.station_result("signoff-v2", "clean", out, ws))
        code, done, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual((code, done["next"]), (0, "report"), (done, err))


if __name__ == "__main__":
    unittest.main()
