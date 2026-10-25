"""E17 fix round 1, slice A's MAJOR: the reviewing session's own full run reaches the record.

Slice A moved the full test run from every reviewer to the reviewing session (Step 3.5), but the
session's run had no route into the answer, the verdict or the verdict doc: a red suite the
reviewers never ran could not stop a clean verdict. The answer now carries the session's checks
in their own field, `session_checks`, apart from the reviewer's `checks_executed`:

- a session check whose exit code is not 0 stops the run at `record-answer` before anything is
  recorded (`session_check_failed`, the answer-refusal path), whatever the reviewers raised, a
  BLOCKER included; the stopped result and the chat block still list what the reviewers raised;
- passing session checks are listed apart from the reviewer's, in the verdict doc and in the chat
  block's Method line, and they never count toward Step 4 rule 3 (a clean review lists ITS checks);
- a session check is held to the builder-conversation provenance rules like a reviewer check;
- an answer with no `session_checks` behaves as before, the verdict doc's empty list aside.
"""
import copy
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import answer as ans  # noqa: E402
from signoff_core import result as resultmod  # noqa: E402

CASE = "S1-01-clean"
DOC = "docs/plans/2026-09-18-signpost-rows.md"
LOG = "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl"
SUITE = "uv run python3 -m unittest discover -s tests -p 'test_*.py'"

PASSING = {"name": "full suite", "command": SUITE, "exit_code": 0,
           "output": "Ran 4 tests in 0.010s\n\nOK"}
FAILING = {"name": "full suite", "command": SUITE, "exit_code": 1,
           "output": "Ran 4 tests in 0.010s\n\nFAILED (failures=1)"}
BLOCKER = {"location": "src/signpost/pad.py:2", "severity": "BLOCKER",
           "claim": "pad() drops the last character of every name",
           "scenario": "render a 12-character name; the field holds 11 characters",
           "evidence_kind": "executed"}


def card_of(workspace):
    for line in testlib.read_text(os.path.join(workspace, DOC)).split("\n"):
        if line.startswith("Status:"):
            return line[len("Status:"):].strip()
    return None


def log_events(workspace):
    path = os.path.join(workspace, LOG)
    if not os.path.isfile(path):
        return []
    return [json.loads(line) for line in testlib.read_text(path).split("\n") if line.strip()]


class SessionChecksThroughTheCLI(unittest.TestCase):
    """The real CLI over a seeded case, recording through the real records component."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-e17-session-checks-")
        self.addCleanup(testlib.rmtree, self.dir)
        family = testlib.family_of(CASE)
        self.case = testlib.build_case(family, CASE, os.path.join(self.dir, family))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "e17-session",
                              "run_dir": self.run_dir, "run_date": "2026-10-24",
                              "harness": "test-harness", "sessions": seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": False,
               "review": {"depth": "LEAN", "route": "readers:claude-session"}}
        self.input_path = testlib.write_json(os.path.join(self.case, "e17-input.json"), doc)
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        self.answer = testlib.load_json(os.path.join(self.case, "answer.json"))

    def phase(self, args):
        return testlib.signoff(args, env=self.env)

    def through_answer(self, answer):
        for args in (["check-input", self.input_path], ["scope", "--run-dir", self.run_dir],
                     ["request", "--run-dir", self.run_dir]):
            code, doc, err = self.phase(args)
            self.assertEqual(code, 0, "%s: %s %s" % (args[0], err, json.dumps(doc)))
        path = testlib.write_json(os.path.join(self.case, "e17-answer.json"), answer)
        return self.phase(["record-answer", "--run-dir", self.run_dir, "--answer", path])

    def result(self):
        return testlib.load_json(os.path.join(self.run_dir, "result.json"))

    def chat(self):
        return testlib.read_text(os.path.join(self.run_dir, "chat.md"))

    def assertStoppedOnTheSessionCheck(self, code, doc, err):
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "stopped", json.dumps(doc))
        self.assertEqual(doc["stop_reason_code"], "session_check_failed")
        self.assertEqual(doc["refusal_reason"], "session_check_failed")
        self.assertFalse(doc["verdict_recorded"])
        got = self.result()
        self.assertEqual(got["stop_reason_code"], "session_check_failed")
        self.assertEqual(got["refusal_reason"], "session_check_failed")
        self.assertTrue(got["answer_refused"])
        self.assertFalse(got["verdict_recorded"])
        self.assertIsNone(got["verdict"])
        self.assertTrue(got["writes_none"])
        self.assertEqual(got["session_checks"], [FAILING])
        self.assertIn(SUITE, got["stop_reason"])
        self.assertIn("exit 1", got["stop_reason"])
        chat = self.chat()
        self.assertIn(SUITE, chat)
        self.assertIn("exit 1", chat)
        return got, chat

    def assertNothingRecorded(self, tree_before):
        self.assertEqual(testlib.tree_hash(self.workspace, exclude=("docs/records",)),
                         tree_before, "the run wrote into the project")
        self.assertEqual(testlib.project_status(self.workspace), "")
        self.assertEqual(card_of(self.workspace), "built", "the card moved")
        kinds = [event["kind"] for event in log_events(self.workspace)]
        self.assertNotIn("finding_raised", kinds)
        self.assertNotIn("card_set", kinds)
        self.assertFalse(os.path.exists(os.path.join(self.workspace, "docs", "reviews")))

    def test_a_failing_session_check_stops_a_clean_answer_with_nothing_recorded(self):
        tree_before = testlib.tree_hash(self.workspace, exclude=("docs/records",))
        answer = dict(self.answer, session_checks=[FAILING])
        got, chat = self.assertStoppedOnTheSessionCheck(*self.through_answer(answer))
        self.assertEqual(got["findings"], [])
        # The reviewer's checks are still the reviewer's; nothing was merged into them.
        self.assertEqual(got["checks_executed"], self.answer["checks_executed"])
        code, doc, err = self.phase(["record", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "stopped")
        self.assertEqual(doc["stop_reason_code"], "session_check_failed")
        self.assertFalse(doc["verdict_recorded"])
        self.assertNothingRecorded(tree_before)

    def test_a_failing_session_check_outranks_a_reviewer_blocker(self):
        tree_before = testlib.tree_hash(self.workspace, exclude=("docs/records",))
        answer = dict(self.answer, findings=[BLOCKER], verdict="rejected",
                      session_checks=[PASSING, FAILING])
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["stop_reason_code"], "session_check_failed", json.dumps(doc))
        got = self.result()
        self.assertEqual(got["session_checks"], [PASSING, FAILING])
        # What the reviewers raised is still listed, so the fix sees it.
        self.assertEqual([row["location"] for row in got["findings"]], ["src/signpost/pad.py:2"])
        self.assertEqual(got["findings"][0]["severity"], "BLOCKER")
        self.assertIsNone(got["verdict"])
        self.assertIn("pad() drops the last character", self.chat())
        code, doc, err = self.phase(["record", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["stop_reason_code"], "session_check_failed")
        self.assertNothingRecorded(tree_before)

    def test_a_passing_session_check_and_a_clean_answer_sign_off(self):
        answer = dict(self.answer, session_checks=[PASSING])
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["record", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed", json.dumps(doc))
        self.assertEqual(doc["verdict"], "signed off")
        self.assertEqual(card_of(self.workspace), "signed off")
        got = self.result()
        self.assertEqual(got["session_checks"], [PASSING])
        self.assertEqual(got["checks_executed"], self.answer["checks_executed"])
        verdict_doc = testlib.read_text(os.path.join(self.workspace, got["verdict_doc"]))
        reviewer_at = verdict_doc.index("Checks the reviewer executed:")
        session_at = verdict_doc.index("Checks the reviewing session executed:")
        self.assertLess(reviewer_at, session_at)
        reviewer_list = verdict_doc[reviewer_at:session_at]
        session_list = verdict_doc[session_at:].split("\n\n")[0]
        self.assertNotIn(SUITE, reviewer_list)
        self.assertIn("- full suite (`%s`, exit 0)" % SUITE, session_list)
        self.assertNotIn("sh checks/unit.sh", session_list)
        method = [line for line in self.chat().split("\n") if line.startswith("Method:")]
        self.assertEqual(len(method), 1)
        self.assertIn("3 check(s) executed by the reviewer", method[0])
        self.assertIn("1 check(s) executed by the reviewing session", method[0])

    def test_no_session_checks_is_todays_behavior(self):
        code, doc, err = self.through_answer(copy.deepcopy(self.answer))
        self.assertEqual(code, 0, err or json.dumps(doc))
        code, doc, err = self.phase(["record", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["status"], "completed", json.dumps(doc))
        self.assertEqual(doc["verdict"], "signed off")
        self.assertEqual(card_of(self.workspace), "signed off")
        got = self.result()
        self.assertNotIn("session_checks", got)
        verdict_doc = testlib.read_text(os.path.join(self.workspace, got["verdict_doc"]))
        self.assertIn("Checks the reviewing session executed:\n- none were reported", verdict_doc)
        method = [line for line in self.chat().split("\n") if line.startswith("Method:")]
        self.assertIn("0 check(s) executed by the reviewing session", method[0])

    def test_session_checks_never_count_toward_the_clean_review_rule(self):
        answer = dict(self.answer, checks_executed=[], session_checks=[PASSING])
        code, doc, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assertEqual(doc["stop_reason_code"], "answer_invalid", json.dumps(doc))
        self.assertFalse(doc["verdict_recorded"])


SET = ["src/signpost/pad.py", "src/signpost/render.py"]
SESSIONS = {"building": "sess-build-1", "reviewing": "sess-review-1"}
NOTES = "docs/builder-notes.md"


def an_answer(**over):
    doc = {"role": "reviewer", "session_id": "sess-review-1",
           "checks_executed": [{"name": "unit", "command": "sh checks/unit.sh", "exit_code": 0,
                                "output": "Ran 4 tests\n\nOK"}],
           "findings": [], "verdict": "signed off", "notes": "prose"}
    doc.update(over)
    return doc


class SessionChecksInTheAdjudication(unittest.TestCase):
    def provenance(self):
        return {"paths": [NOTES], "delivered_paths": SET + [DOC], "anchors": [],
                "withheld_text": "", "delivered_text": "", "workspace": "/workspace/signpost"}

    def test_a_session_check_citing_a_withheld_builder_path_is_refused_like_a_reviewer_check(self):
        citing = {"name": "read the notes", "command": "cat %s" % NOTES, "exit_code": 0,
                  "output": "ok"}
        as_reviewer = ans.adjudicate(an_answer(checks_executed=[citing]), SET, SESSIONS,
                                     provenance=self.provenance())
        as_session = ans.adjudicate(an_answer(session_checks=[citing]), SET, SESSIONS,
                                    provenance=self.provenance())
        self.assertEqual(as_reviewer["refusal_reason"], "independence")
        self.assertEqual(as_session["refusal_reason"], "independence")
        self.assertFalse(as_session["ok"])

    def test_a_session_check_repeating_a_withheld_line_is_refused(self):
        line = "the padder was rewritten because the old one was too slow for us"
        echo = {"name": "echo", "command": "true", "exit_code": 0, "output": line}
        got = ans.adjudicate(an_answer(session_checks=[echo]), SET, SESSIONS,
                             withheld_lines=(line,))
        self.assertEqual(got["refusal_reason"], "independence")

    def test_a_clean_answer_with_only_session_checks_is_not_a_clean_review(self):
        got = ans.adjudicate(an_answer(checks_executed=[], session_checks=[PASSING]), SET,
                             SESSIONS)
        self.assertEqual(got["refusal_reason"], "answer_invalid")
        self.assertFalse(got["clean_review_checks_listed"])

    def test_the_adjudication_carries_the_session_checks_apart(self):
        got = ans.adjudicate(an_answer(session_checks=[PASSING]), SET, SESSIONS)
        self.assertTrue(got["ok"])
        self.assertEqual(got["session_checks"], [PASSING])
        self.assertEqual(len(got["checks_executed"]), 1)
        self.assertIsNone(ans.adjudicate(an_answer(), SET, SESSIONS)["session_checks"])

    def test_which_session_checks_fail(self):
        no_code = dict(PASSING, exit_code=None)
        self.assertEqual(ans.failing_session_checks(an_answer(session_checks=[PASSING])), [])
        self.assertEqual(ans.failing_session_checks(an_answer()), [])
        self.assertEqual(ans.failing_session_checks(
            an_answer(session_checks=[PASSING, FAILING, no_code])), [FAILING, no_code])


class TheChatBlockListsThemApart(unittest.TestCase):
    def a_result(self, **over):
        result = {"run": {"slice": "D", "build_doc": DOC, "depth": "LEAN", "lenses": []},
                  "status": "completed", "findings": [], "notes": [],
                  "checks_executed": [{"name": "unit", "command": "sh checks/unit.sh",
                                       "exit_code": 0, "output": "OK"}],
                  "session_checks": [PASSING], "packet": {"withheld": []},
                  "reviewer": {"route": "readers:claude-session", "independent": True},
                  "verdict": "signed off", "problems": []}
        result.update(over)
        return result

    def test_the_method_line_names_both_counts(self):
        chat = resultmod.chat_block(self.a_result())
        method = [line for line in chat.split("\n") if line.startswith("Method:")][0]
        self.assertIn("1 check(s) executed by the reviewer", method)
        self.assertIn("1 check(s) executed by the reviewing session", method)
        tried = chat.split("Tried and failed to break:")[1]
        self.assertNotIn(SUITE, tried.split("Checks the reviewing session executed:")[0])
        self.assertIn("Checks the reviewing session executed:", chat)
        self.assertIn("full suite (%s, exit 0)" % SUITE, chat)

    def test_no_session_checks_counts_none(self):
        result = self.a_result()
        del result["session_checks"]
        method = [line for line in resultmod.chat_block(result).split("\n")
                  if line.startswith("Method:")][0]
        self.assertIn("0 check(s) executed by the reviewing session", method)


if __name__ == "__main__":
    unittest.main()
