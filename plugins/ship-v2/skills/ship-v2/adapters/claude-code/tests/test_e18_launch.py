"""E18 slice C: the launch helper (`launch.py`) over fixture transcripts.

Given a ship run directory whose open signoff-v2 visit carries a launch (the run's `input.json` and `ship.json`, as
`visit --station signoff-v2` leaves them on Claude Code), the helper finds the ship session's own transcript from the
input's `invocation.session_id` under a fixture home (`CLAUDE_CONFIG_DIR`, the seam these tests already use) and
prints the launch: exactly the argv the plan names, with the transcript's model id and effort, `--effort` left out
when none is recorded or the value is outside the five `claude --effort` takes, the settings element exactly the
memory-off JSON object with no shell quotes, `--permission-mode auto` always, no banned flag ever. A transcript with no
model, or a model below the Opus floor, prints no launch (exit 3). Its check mode holds on a fixture child record
whose first prompt is the launch's prompt, and fails on a missing record or another prompt.
"""
import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import testlib

SHIP_SESSION = testlib.SESSION
CHILD = "6a1f3c2e-0b7d-4e59-9a8c-2d4e6f8a0b1c"
SETTINGS = '{"autoMemoryEnabled":false}'
BANNED = ("bypassPermissions", "--dangerously-skip-permissions", "--bare")


class Fixture(object):
    """A ship run directory with an open launched signoff visit, a workspace, and a fixture Claude Code home."""

    def __init__(self, test):
        self.tmp = tempfile.mkdtemp(prefix="launch-")
        test.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = os.path.join(self.tmp, "workspace")
        os.makedirs(self.ws)
        self.run_dir = os.path.join(self.tmp, "run")
        os.makedirs(self.run_dir)
        self.home = os.path.join(self.tmp, "home")
        self.brief = os.path.join(self.run_dir, "brief-5-signoff-v2.md")
        self.prompt = "Read %s and follow it." % self.brief
        self.stdout = os.path.join(self.run_dir, "child-5-signoff-v2.json")
        self.write(os.path.join(self.run_dir, "input.json"), {
            "input_version": 1, "run_id": "run", "workspace": self.ws, "run_dir": self.run_dir,
            "invocation": {"harness": "claude-code", "caller": "user", "mode": "direct", "session_id": SHIP_SESSION}})
        self.write(os.path.join(self.run_dir, "ship.json"), {"visit": {
            "station": "signoff-v2", "seq": 5, "run_dir": os.path.join(self.run_dir, "visits", "5-signoff-v2"),
            "launch": {"session_id": CHILD, "brief": self.brief, "prompt": self.prompt, "stdout": self.stdout}}})

    @staticmethod
    def write(path, doc):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(doc, handle)

    def ship_transcript(self, mutate=None):
        """The fixture transcript as the ship session's own record, under the fixture home, each assistant record
        passed through `mutate`."""
        rows = []
        for row in testlib.records():
            row = copy.deepcopy(row)
            if row.get("cwd"):
                row["cwd"] = self.ws
            if row.get("type") == "assistant" and mutate is not None:
                mutate(row)
            rows.append(row)
        folder = os.path.join(self.home, "projects", "-ship")
        os.makedirs(folder, exist_ok=True)
        return testlib.write_records(folder, rows, name="%s.jsonl" % SHIP_SESSION)

    def child_transcript(self, prompt=None, session=CHILD, cwd=None):
        rows = [{"type": "user", "sessionId": session, "cwd": cwd or self.ws, "isSidechain": False,
                 "message": {"role": "user", "content": self.prompt if prompt is None else prompt}},
                {"type": "assistant", "sessionId": session, "cwd": cwd or self.ws, "isSidechain": False,
                 "message": {"role": "assistant", "model": "claude-opus-5",
                             "content": [{"type": "text", "text": "NEUTRAL reply."}]}}]
        folder = os.path.join(self.home, "projects", "-child")
        os.makedirs(folder, exist_ok=True)
        return testlib.write_records(folder, rows, name="%s.jsonl" % session)

    def run(self, *extra):
        return testlib.run("launch.py", ["--run-dir", self.run_dir] + list(extra),
                           env={"CLAUDE_CONFIG_DIR": self.home})


def expected(model, effort=None):
    argv = ["claude", "-p", "--model", model]
    if effort is not None:
        argv += ["--effort", effort]
    return argv


class TheLaunch(unittest.TestCase):

    def launch(self, fixture):
        code, out, err = fixture.run()
        self.assertEqual(code, 0, err)
        return json.loads(out)["launch"]

    def test_the_argv_is_exactly_the_plans_with_the_transcripts_model_and_effort(self):
        fixture = Fixture(self)
        fixture.ship_transcript()
        launch = self.launch(fixture)
        self.assertEqual(launch["argv"], expected("claude-opus-5", "high") + [
            "--permission-mode", "auto", "--session-id", CHILD, "--settings", SETTINGS, "--output-format", "json",
            fixture.prompt])
        self.assertEqual(launch["cwd"], fixture.ws)
        self.assertEqual(launch["session_id"], CHILD)
        self.assertEqual(launch["stdout"], fixture.stdout)

    def test_the_last_recorded_model_and_effort_are_taken(self):
        fixture = Fixture(self)
        rows = {"n": 0}

        def mutate(row):
            rows["n"] += 1
            row["message"]["model"] = "claude-opus-5-5"
            row["effort"] = "max"
        fixture.ship_transcript(mutate)
        self.assertTrue(rows["n"])
        launch = self.launch(fixture)
        self.assertEqual(launch["argv"][:6], expected("claude-opus-5-5", "max"))

    def test_the_settings_element_is_the_memory_off_object_with_no_shell_quotes(self):
        fixture = Fixture(self)
        fixture.ship_transcript()
        argv = self.launch(fixture)["argv"]
        element = argv[argv.index("--settings") + 1]
        self.assertEqual(element, SETTINGS)
        self.assertEqual(json.loads(element), {"autoMemoryEnabled": False})
        self.assertNotIn("'", element)
        self.assertFalse(element.startswith('"'))

    def test_no_effort_recorded_leaves_the_effort_out(self):
        fixture = Fixture(self)
        fixture.ship_transcript(lambda row: row.pop("effort", None))
        argv = self.launch(fixture)["argv"]
        self.assertNotIn("--effort", argv)
        self.assertEqual(argv[:4], expected("claude-opus-5"))
        self.assertEqual(argv[4:6], ["--permission-mode", "auto"])

    def test_an_effort_outside_the_five_is_left_out(self):
        for value in ("turbo", "HIGH", "none", ""):
            fixture = Fixture(self)
            fixture.ship_transcript(lambda row, value=value: row.__setitem__("effort", value))
            argv = self.launch(fixture)["argv"]
            self.assertNotIn("--effort", argv, value)

    def test_each_of_the_five_efforts_is_passed(self):
        for value in ("low", "medium", "high", "xhigh", "max"):
            fixture = Fixture(self)
            fixture.ship_transcript(lambda row, value=value: row.__setitem__("effort", value))
            argv = self.launch(fixture)["argv"]
            self.assertEqual(argv[argv.index("--effort") + 1], value)

    def test_the_permission_mode_is_always_auto_and_no_banned_flag_is_carried(self):
        for mutate in (None, lambda row: row.pop("effort", None)):
            fixture = Fixture(self)
            fixture.ship_transcript(mutate)
            argv = self.launch(fixture)["argv"]
            self.assertEqual(argv[argv.index("--permission-mode") + 1], "auto")
            self.assertEqual(argv.count("--permission-mode"), 1)
            for word in BANNED:
                self.assertFalse([item for item in argv if word in item], word)

    def test_a_transcript_with_no_model_prints_no_launch(self):
        fixture = Fixture(self)
        fixture.ship_transcript(lambda row: row["message"].pop("model", None))
        code, out, err = fixture.run()
        self.assertEqual(code, 3, (out, err))
        self.assertNotIn("launch", json.loads(out))
        self.assertIn("no model", err)

    def test_a_model_below_the_floor_prints_no_launch(self):
        for model in ("claude-sonnet-4-6", "claude-haiku-4-5", "gpt-5"):
            fixture = Fixture(self)
            fixture.ship_transcript(lambda row, model=model: row["message"].__setitem__("model", model))
            code, out, err = fixture.run()
            self.assertEqual(code, 3, (model, out, err))
            self.assertNotIn("launch", json.loads(out))
            self.assertIn("Opus floor", err)

    def test_no_ship_transcript_is_exit_3(self):
        fixture = Fixture(self)
        code, out, err = fixture.run()
        self.assertEqual(code, 3, (out, err))
        self.assertNotIn("launch", json.loads(out))

    def test_a_run_with_no_launch_recorded_is_a_usage_slip(self):
        fixture = Fixture(self)
        fixture.ship_transcript()
        Fixture.write(os.path.join(fixture.run_dir, "ship.json"), {"visit": None})
        code, out, err = fixture.run()
        self.assertEqual(code, 2, (out, err))


class TheCheck(unittest.TestCase):

    def check(self, fixture):
        code, out, err = fixture.run("--check")
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_it_holds_on_a_child_record_whose_first_prompt_is_the_launchs(self):
        fixture = Fixture(self)
        path = fixture.child_transcript()
        reading = self.check(fixture)
        self.assertIs(reading["holds"], True, reading)
        self.assertEqual(reading["session_id"], CHILD)
        self.assertEqual(reading["kind"], "launch_check")
        self.assertEqual(reading["harness"], "claude-code")
        self.assertEqual(reading["prompt_sha256"], hashlib.sha256(fixture.prompt.encode("utf-8")).hexdigest())
        self.assertEqual(reading["transcript"], path)

    def test_it_fails_on_a_missing_record(self):
        fixture = Fixture(self)
        reading = self.check(fixture)
        self.assertIs(reading["holds"], False)
        self.assertIn("cannot be read", reading["how"])

    def test_it_fails_on_another_prompt(self):
        for tail in (None, " Then answer for the owner.", ""):
            fixture = Fixture(self)
            prompt = "Run signoff-v2 on slice A." if tail is None else (fixture.prompt + tail if tail else "")
            fixture.child_transcript(prompt=prompt)
            reading = self.check(fixture)
            self.assertIs(reading["holds"], False, prompt)

    def test_it_fails_on_another_workspace(self):
        fixture = Fixture(self)
        fixture.child_transcript(cwd=os.path.join(fixture.tmp, "elsewhere"))
        self.assertIs(self.check(fixture)["holds"], False)



if __name__ == "__main__":
    unittest.main()
