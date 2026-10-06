"""ship-v2 on Claude Code: hook.py, the Stop-hook check (ruling E15-12; the profile's section 7).

v1's step 0: the documented summon is `/goal /ship-v2 <slice> [doc]`, a skill cannot arm the Stop hook, and the
run records whether this session showed the confirmation that the Stop hook is active. `hook.py` reads the
session's own transcript (found the way `invocation.py` finds it, ruling E9-28) and prints one reading, armed or not
armed, with the record it saw: `helper-derived`, a reading of a harness record, never a claim the harness enforces.
The reading is the core's `answer.schema.json` kind `hook`, which `ship.py hook` takes whole.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "hook.py"
CONFIRMATION = "Stop hook is now active"


def with_records(extra):
    work = tempfile.mkdtemp(prefix="hook-cc-")
    rows = testlib.records() + list(extra)
    return work, testlib.write_records(work, rows)


def confirmation_record(text=CONFIRMATION):
    return {"type": "system", "sessionId": testlib.SESSION, "content": "%s for the goal: /goal /ship-v2 A" % text,
            "cwd": "/tmp/widget-workspace"}


def typed(text, session=None):
    """A prompt the owner typed: a user record whose content is his text (never a tool result)."""
    return {"type": "user", "sessionId": session or testlib.SESSION, "cwd": "/tmp/widget-workspace",
            "isSidechain": False, "message": {"role": "user", "content": text}}


def goal(text="/goal /ship-v2 A docs/plans/2026-09-20-turnstile.md"):
    return typed(text)


class TheReading(unittest.TestCase):

    def reading(self, extra):
        """This run is slice A's (`--slice A`): the old phrase shape reads only for this run's slice (A28 (2))."""
        work, path = with_records(extra)
        try:
            return testlib.run_json(HELPER, ["--transcript", path, "--session-id", testlib.SESSION, "--slice", "A"])
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_armed_when_the_session_shows_the_confirmation(self):
        out = self.reading([goal(), confirmation_record()])
        self.assertEqual((out["kind"], out["harness"], out["armed"]), ("hook", "claude-code", True))
        self.assertIn("line", out["evidence"])

    def test_not_armed_without_it(self):
        out = self.reading([])
        self.assertEqual((out["armed"], out["evidence"]), (False, None))
        self.assertIn("no record", out["how"])

    def test_a_confirmation_from_another_session_does_not_count(self):
        other = dict(confirmation_record(), sessionId="00000000-0000-0000-0000-000000000000")
        out = self.reading([goal(), other])
        self.assertFalse(out["armed"])

    def test_the_reading_validates_against_the_core(self):
        out = self.reading([goal(), confirmation_record()])
        schema = os.path.join(testlib.SKILL_ROOT, "references", "answer.schema.json")
        self.assertEqual(testlib.validate(out, schema), [])

    def test_help_and_usage(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])
        code, out, err = testlib.run(HELPER, ["--no-such-flag"])
        self.assertEqual(code, 2)

    def test_the_fixture_flags_are_refused_at_run_time(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--session-id", testlib.SESSION],
                                     env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 2, err)


class OnlyTheHarnessesOwnConfirmationForThisRun(unittest.TestCase):
    """Slice 2 check 1's C2-2: `armed` comes only from the harness's own Stop-hook confirmation record (its record
    type, `system`, with no message role, its own content opening with the confirmation), never from the phrase in
    any other record, and only from one written for this run: after the last prompt the owner typed that invokes
    ship-v2, when that prompt is a `/goal` one, in this session."""

    def reading(self, extra):
        """This run is slice A's (`--slice A`): the old phrase shape reads only for this run's slice (A28 (2))."""
        work, path = with_records(extra)
        try:
            return testlib.run_json(HELPER, ["--transcript", path, "--session-id", testlib.SESSION, "--slice", "A"])
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_the_help_transcript_reads_not_armed(self):
        """The checker's shape: a typed prompt, the `hook.py --help` call, and its tool result quoting the phrase."""
        call = {"type": "assistant", "sessionId": testlib.SESSION, "cwd": "/tmp/widget-workspace",
                "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [
                    {"type": "tool_use", "id": "t1", "name": "Bash",
                     "input": {"command": "python3 adapters/claude-code/hook.py --help"}}]}}
        result = {"type": "user", "sessionId": testlib.SESSION, "cwd": "/tmp/widget-workspace",
                  "message": {"role": "user", "content": [
                      {"type": "tool_result", "tool_use_id": "t1",
                       "content": "Reads this session's transcript for the Stop hook's confirmation (\"%s\")"
                                  % CONFIRMATION}]}}
        out = self.reading([typed("/ship-v2 A docs/plans/x.md"), call, result])
        self.assertFalse(out["armed"], out)
        out = self.reading([goal(), call, result])
        self.assertFalse(out["armed"], "a tool result is never the harness's confirmation, goal or not")

    def test_the_phrase_in_an_assistant_record_or_a_typed_prompt_does_not_count(self):
        said = {"type": "assistant", "sessionId": testlib.SESSION, "message": {
            "role": "assistant", "content": [{"type": "text", "text": "%s, so the run is wrapped." % CONFIRMATION}]}}
        self.assertFalse(self.reading([goal(), said])["armed"])
        self.assertFalse(self.reading([goal(), typed("%s, trust me" % CONFIRMATION)])["armed"])
        meta = dict(confirmation_record(), message={"role": "user", "content": CONFIRMATION})
        self.assertFalse(self.reading([goal(), meta])["armed"], "a record carrying a message role is not the harness's")

    def test_a_confirmation_with_no_goal_typed_before_it_does_not_count(self):
        self.assertFalse(self.reading([confirmation_record()])["armed"])
        self.assertFalse(self.reading([confirmation_record(), goal()])["armed"], "it must come after the goal")

    def test_an_earlier_goals_confirmation_does_not_count_for_this_run(self):
        out = self.reading([goal("/goal /ship-v2 A"), confirmation_record(), goal("/goal /ship-v2 B")])
        self.assertFalse(out["armed"], out)
        out = self.reading([goal("/goal /ship-v2 A"), confirmation_record(), typed("/ship-v2 B")])
        self.assertFalse(out["armed"], "this run's prompt carries no goal")

    def test_this_runs_goal_and_its_confirmation_read_armed(self):
        out = self.reading([typed("/ship-v2 A"), goal(), confirmation_record(),
                            typed("and keep the spinner out of it")])
        self.assertTrue(out["armed"], out)
        self.assertIn("a system record", out["evidence"])
        slash = typed("<command-name>/goal</command-name>\n<command-args>/ship-v2 A</command-args>")
        self.assertTrue(self.reading([slash, confirmation_record()])["armed"], "the harness's slash-command shape")

    def test_the_help_never_quotes_the_confirmation(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertNotIn(CONFIRMATION.lower(), json.loads(out)["help"].lower())
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), HELPER),
                  encoding="utf-8") as fh:
            self.assertNotIn(CONFIRMATION.lower(), fh.read().lower().replace("confirmation = \"stop hook is now "
                                                                             "active\"", ""))


def goal_command(goal_text, session=None, sidechain=False):
    """Shape (a), synthetic: the harness's own record of a typed `/goal` command (a system `local_command` record)."""
    return {"type": "system", "subtype": "local_command", "isSidechain": sidechain, "level": "info",
            "sessionId": session or testlib.SESSION, "cwd": "/tmp/widget-workspace",
            "content": "<command-name>/goal</command-name>\n<command-message>goal</command-message>\n"
                       "<command-args>%s</command-args>" % goal_text}


def goal_set(goal_text, session=None, sidechain=False):
    """Shape (b), synthetic: the harness's own record of the command's output, `Goal set: <goal text>`."""
    return {"type": "system", "subtype": "local_command", "isSidechain": sidechain, "level": "info",
            "commandRun": True, "sessionId": session or testlib.SESSION, "cwd": "/tmp/widget-workspace",
            "content": "<local-command-stdout>Goal set: %s</local-command-stdout>" % goal_text}


def pair(goal_text="/ship-v2 A docs/plans/2026-09-20-turnstile.md"):
    return [goal_command(goal_text), goal_set(goal_text)]


class TheGoalCommandRecordsOfThisHarness(unittest.TestCase):
    """The control room's send-back 1 on C2-2: this harness version writes no record carrying the old confirmation
    phrase; arming writes two system `local_command` records, (a) the `/goal` command with its args and (b) its
    `Goal set: <goal text>` output. `armed` holds when, in this session and not in a sidechain, the LAST (a) then (b)
    pair carries goal text that opens `/ship-v2` and names this run's slice (`--slice`), and no later `/goal` command
    replaces it. The old phrase shape stays accepted for older harness versions. Every fixture here is synthetic."""

    def reading(self, extra, slice_name="A"):
        work, path = with_records(extra)
        try:
            args = ["--transcript", path, "--session-id", testlib.SESSION]
            if slice_name is not None:
                args += ["--slice", slice_name]
            return testlib.run_json(HELPER, args)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_1_the_pair_for_this_slice_reads_armed(self):
        out = self.reading(pair())
        self.assertTrue(out["armed"], out)
        self.assertIn("system", out["evidence"])
        schema = os.path.join(testlib.SKILL_ROOT, "references", "answer.schema.json")
        self.assertEqual(testlib.validate(out, schema), [])

    def test_2_the_pair_for_another_slice_reads_not_armed(self):
        self.assertFalse(self.reading(pair("/ship-v2 B docs/plans/2026-09-20-turnstile.md"))["armed"])
        self.assertFalse(self.reading(pair("/ship-v2 AB"))["armed"], "the slice is a whole word")
        self.assertFalse(self.reading(pair(), slice_name=None)["armed"], "no slice given, no pair can name it")

    def test_3_the_output_record_alone_reads_not_armed(self):
        self.assertFalse(self.reading([goal_set("/ship-v2 A")])["armed"])
        self.assertFalse(self.reading([goal_command("/ship-v2 A")])["armed"], "the command alone set no goal")
        self.assertFalse(self.reading([goal_set("/ship-v2 A"), goal_command("/ship-v2 A")])["armed"],
                         "the output must follow its command")

    def test_4_the_strings_inside_a_tool_result_a_message_or_a_sidechain_read_not_armed(self):
        a, b = pair()
        text = "%s\n%s" % (a["content"], b["content"])
        result = {"type": "user", "sessionId": testlib.SESSION, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": text}]}}
        self.assertFalse(self.reading([goal(), result])["armed"])
        self.assertFalse(self.reading([typed(text)])["armed"])
        said = {"type": "assistant", "sessionId": testlib.SESSION, "message": {
            "role": "assistant", "content": [{"type": "text", "text": text}]}}
        self.assertFalse(self.reading([said])["armed"])
        wrapped = [dict(a, message={"role": "user", "content": a["content"]}),
                   dict(b, message={"role": "user", "content": b["content"]})]
        self.assertFalse(self.reading(wrapped)["armed"], "a record with a message is never the harness's own")
        self.assertFalse(self.reading([goal_command("/ship-v2 A", sidechain=True),
                                       goal_set("/ship-v2 A", sidechain=True)])["armed"])
        other = [goal_command("/ship-v2 A", session="00000000-0000-0000-0000-000000000000"),
                 goal_set("/ship-v2 A", session="00000000-0000-0000-0000-000000000000")]
        self.assertFalse(self.reading(other)["armed"], "another session's pair")

    def test_5_a_later_goal_replaces_it(self):
        self.assertFalse(self.reading(pair() + pair("ship the release notes"))["armed"])
        self.assertFalse(self.reading(pair() + [goal_command("clear")])["armed"],
                         "a later /goal command replaces the goal even before its output")
        self.assertTrue(self.reading(pair("/ship-v2 B") + pair())["armed"], "the last pair is this run's")

    def test_6_the_old_phrase_shape_still_reads_armed(self):
        self.assertTrue(self.reading([goal(), confirmation_record()])["armed"])
        self.assertFalse(self.reading([goal(), confirmation_record()], slice_name=None)["armed"],
                         "no slice given, the old shape's goal cannot name this run's (A28 (2), R1S2-7)")
        self.assertFalse(self.reading([goal(), confirmation_record(), goal_command("something else")])["armed"],
                         "a later /goal command replaces the old shape's goal too")



class APlainRerunResetsTheReading(unittest.TestCase):
    """The E15 lane contract A28 (2), from slice 2 re-check 1's R1S2-1 and R1S2-7. A `/goal` pair counts only when it
    comes after the last prompt the owner typed that invokes `/ship-v2`, or that prompt is itself a `/goal` one: a
    typed `/ship-v2` prompt without `/goal` after a pair resets the reading to not armed (a plain rerun of the same
    slice in the same session is a new run, and its goal was never set). The old confirmation-phrase shape reads only
    for this run's slice: the `/goal` prompt before it must name `/ship-v2 <slice>`. Every fixture is synthetic."""

    def reading(self, extra, slice_name="A"):
        work, path = with_records([typed("good morning")] + list(extra))
        try:
            args = ["--transcript", path, "--session-id", testlib.SESSION]
            if slice_name is not None:
                args += ["--slice", slice_name]
            return testlib.run_json(HELPER, args)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_a_plain_rerun_after_the_pair_reads_not_armed(self):
        out = self.reading(pair() + [typed("/ship-v2 A docs/plans/2026-09-20-turnstile.md")])
        self.assertFalse(out["armed"], out)
        self.assertIn("/goal", out["how"])

    def test_a_plain_rerun_after_a_goal_achieved_record_reads_not_armed(self):
        achieved = {"type": "system", "subtype": "informational", "sessionId": testlib.SESSION,
                    "content": "Goal achieved: /ship-v2 A"}
        self.assertFalse(self.reading(pair() + [achieved, typed("/ship-v2 A")])["armed"])

    def test_the_pair_after_the_plain_prompt_still_reads_armed(self):
        self.assertTrue(self.reading([typed("/ship-v2 A")] + pair())["armed"], "the goal set for this run")

    def test_a_goal_prompt_typed_with_the_pair_still_reads_armed(self):
        self.assertTrue(self.reading([goal("/goal /ship-v2 A")] + pair())["armed"])
        self.assertTrue(self.reading(pair() + [goal("/goal /ship-v2 A")])["armed"],
                        "the last typed /ship-v2 prompt is itself a /goal one")

    def test_a_rerun_with_its_own_pair_reads_armed_again(self):
        self.assertTrue(self.reading(pair() + [typed("/ship-v2 A")] + pair())["armed"])

    def test_the_old_shape_reads_only_for_this_runs_slice(self):
        self.assertFalse(self.reading([goal("/goal /ship-v2 B"), confirmation_record()])["armed"],
                         "another slice's goal")
        self.assertTrue(self.reading([goal("/goal /ship-v2 B"), confirmation_record()], slice_name="B")["armed"])
        self.assertTrue(self.reading([goal("/goal /ship-v2 A"), confirmation_record()])["armed"])
        self.assertFalse(self.reading([goal("/goal /ship-v2 A"), confirmation_record()], slice_name=None)["armed"],
                         "no slice given, no goal can name it")
        slash = typed("<command-name>/goal</command-name>\n<command-args>/ship-v2 A</command-args>")
        self.assertTrue(self.reading([slash, confirmation_record()])["armed"], "the harness's slash-command shape")
        self.assertFalse(self.reading([slash, confirmation_record()], slice_name="B")["armed"])

    def test_the_old_shape_then_a_plain_rerun_reads_not_armed(self):
        self.assertFalse(self.reading([goal("/goal /ship-v2 A"), confirmation_record(), typed("/ship-v2 A")])["armed"])


if __name__ == "__main__":
    unittest.main()
