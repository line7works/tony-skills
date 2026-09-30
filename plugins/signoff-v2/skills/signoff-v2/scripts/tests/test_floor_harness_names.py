"""The floor's class map and the roster's harness model names (E14 punch list, item 4(a); contract A11).

readers' roster names a pinned row's model by its harness name (`claude-opus-cli` and `claude-opus`: `opus`;
`claude-fable`: `fable`), and readers reports that name as the reader's effective model, which the adapter's
sidecar map hands the core as the answer's `model`. `class_of` accepts exactly the harness names of the roster's
rows that readers holds eligible at the Opus floor, and nothing wider: `session` is the claude-session row's
placeholder (that reader reports the session's own id), and no roster row is named `sonnet` or `haiku`.

Item 4(b): the same-model rule holds for a `claude-session` reader, which inherits the session's model; a
portable row dispatched from a Codex session names its own model and is judged by its class alone. What tells
the core which row answered is the answer's `session_id`, the adapter's `answer_identity.session_id`,
`<readers transport>:<call id>` from readers' sidecar: `claude-cli` is the portable Claude row's transport.
"""
import importlib.util
import json
import os
import sys
import unittest

import testlib
from test_full_fix_signoff import OPUS, _Floor

FABLE = "claude-fable-5-1"

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location(
    "signoff_floor_under_test", os.path.join(testlib.SCRIPTS, "signoff_core", "floor.py"))
floor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(floor)

ROSTER = os.path.join(os.path.dirname(testlib.PLUGIN), "readers", "skills", "readers", "assets", "roster.json")


class TheHarnessNames(unittest.TestCase):

    def test_opus_and_fable_are_class_opus(self):
        self.assertEqual(floor.class_of("opus"), ("opus", True))
        self.assertEqual(floor.class_of("fable"), ("opus", True))

    def test_nothing_wider_is_accepted(self):
        for name in ("session", "sonnet", "haiku", "Opus", "OPUS", "opus ", " opus", "opus-cli", "claude-opus",
                     "fable-x", "gemini-3.1-pro-high", "deepseek/deepseek-v4-pro-0813"):
            self.assertEqual(floor.class_of(name), (floor.UNKNOWN, None), name)

    def test_the_full_ids_keep_their_classes(self):
        self.assertEqual(floor.class_of("claude-opus-5-5"), ("opus", True))
        self.assertEqual(floor.class_of("gpt-6-astra"), ("opus", True))
        self.assertEqual(floor.class_of("claude-sonnet-4-6"), ("sonnet", False))
        self.assertEqual(floor.class_of("claude-haiku-4-5"), ("haiku", False))

    def test_a_reviewer_named_by_a_harness_name_meets_the_floor_by_its_class(self):
        facts = floor.reviewer_facts({"model": "opus"}, None)
        self.assertEqual((facts["model"], facts["class"], facts["met"]), ("opus", "opus", True))



class WhichRowAnswered(unittest.TestCase):
    """Item 4(b), read from the answer's `session_id` (`answer_identity.session_id`)."""

    CODEX = {"model": "gpt-6-astra", "class": "opus", "met": True, "source": "s"}
    CLAUDE = {"model": "claude-opus-5-5", "class": "opus", "met": True, "source": "s"}

    def test_a_portable_row_from_a_codex_session_is_judged_by_its_class_alone(self):
        facts = floor.reviewer_facts({"model": "opus", "session_id": "claude-cli:run-1-review"}, self.CODEX)
        self.assertEqual((facts["model"], facts["class"], facts["met"]), ("opus", "opus", True))
        self.assertIn("claude-cli", facts["source"])

    def test_a_portable_row_below_the_floor_is_still_refused(self):
        for model in ("claude-sonnet-4-6", "session", "unknown-model"):
            with self.assertRaises(floor.FloorRefused):
                floor.reviewer_facts({"model": model, "session_id": "claude-cli:run-1-review"}, self.CODEX)

    def test_a_claude_session_reader_is_held_to_the_sessions_model(self):
        with self.assertRaises(floor.FloorRefused) as caught:
            floor.reviewer_facts({"model": "opus", "session_id": "claude-subagent:run-1-review"}, self.CLAUDE)
        self.assertIn("claude-session", str(caught.exception))
        facts = floor.reviewer_facts({"model": "claude-opus-5-5", "session_id": "claude-subagent:run-1-review"},
                                     self.CLAUDE)
        self.assertTrue(facts["met"])

    def test_an_answer_whose_session_names_no_portable_transport_keeps_the_same_model_rule(self):
        for session_id in ("sess-review-1", "claude-cli", ":run-1", "CLAUDE-CLI:run-1", "codex-exec:run-1",
                           "claude-subagent:claude-cli:run-1"):
            with self.assertRaises(floor.FloorRefused):
                floor.reviewer_facts({"model": "opus", "session_id": session_id}, self.CLAUDE)

    def test_a_model_handed_over_with_no_session_id_keeps_the_same_model_rule(self):
        # the E14 punch-list check's O-1, ruled fail closed: an answer with no `session_id` key names no row, so it
        # keeps the same-model rule; `record` hands the recorded reviewer's `session_id` with its model since round
        # 2 (TheRecordReCheckAppliesTheFullRule), so no caller hands a model alone
        with self.assertRaises(floor.FloorRefused) as caught:
            floor.reviewer_facts({"model": FABLE}, self.CLAUDE)
        self.assertIn("claude-session", str(caught.exception))
        with self.assertRaises(floor.FloorRefused):
            floor.reviewer_facts({"model": "opus"}, self.CODEX)
        with self.assertRaises(floor.FloorRefused):
            floor.reviewer_facts({"model": "claude-haiku-4-5"}, self.CODEX)
        facts = floor.reviewer_facts({"model": "claude-opus-5-5"}, self.CLAUDE)
        self.assertEqual((facts["model"], facts["class"], facts["met"]), ("claude-opus-5-5", "opus", True))


@unittest.skipUnless(os.path.isfile(ROSTER), "no readers roster beside this core (the installed shape)")
class NeverWiderThanTheRoster(unittest.TestCase):

    def test_the_accepted_harness_names_are_the_rosters_eligible_pinned_names(self):
        with open(ROSTER, encoding="utf-8") as fh:
            rows = json.load(fh)["rows"]
        bare = set(r["model"] for r in rows if isinstance(r.get("model"), str)
                   and "-" not in r["model"] and "/" not in r["model"])
        eligible = set(r["model"] for r in rows if r.get("model") in bare and r.get("provider") == "anthropic"
                       and r.get("eligibility") == "eligible")
        accepted = set(name for name in bare if floor.class_of(name) == ("opus", True))
        self.assertEqual(accepted, eligible)
        self.assertEqual(accepted, set(floor.HARNESS_NAMES))
        self.assertIn("session", bare - accepted, "the claude-session placeholder is never a model")


class TheCodexRouteThroughTheCore(_Floor):
    """Item 4(b) end to end through the real CLI: a Codex session (`gpt-6-astra`) records the answer the
    claude-opus-cli row brought back (`model: opus`, `session_id: claude-cli:<call id>`); a clean review from
    that route lists no executed check (the row offers `repo`, held for a later step by the owner, 4(c)) and
    stops `answer_invalid`."""

    def setUp(self):
        _Floor.setUp(self)
        self.with_model({"id": "gpt-6-astra", "floor_class": "opus", "floor_met": True})

    def portable(self, **changes):
        answer = self.answer_model("opus")
        answer["session_id"] = "claude-cli:signoff-fix2-run-review"
        answer.update(changes)
        return answer

    def test_the_portable_rows_answer_is_recorded(self):
        code, body, err = self.through_answer(self.portable())
        self.assertEqual(code, 0, err or json.dumps(body))
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1200])
        self.assertEqual((result["reviewer"]["model"], result["floor"]["met"]), ("opus", True))
        self.assertEqual(result["floor"]["session_model"], "gpt-6-astra")

    def test_the_same_answer_named_as_a_claude_session_reader_is_a_floor_stop(self):
        code, body, err = self.through_answer(self.portable(session_id="claude-subagent:signoff-fix2-run-review"))
        self.assert_floor_stop(code, body, err)

    def test_a_clean_review_from_this_route_lists_no_check_and_stops_answer_invalid(self):
        code, body, err = self.through_answer(self.portable(findings=[], notes_kept=[], checks_executed=[]))
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1200])
        self.assertEqual(result["refusal_reason"], "answer_invalid", json.dumps(result)[:1200])
        self.assertFalse(result["verdict_recorded"])


class TheRecordReCheckAppliesTheFullRule(_Floor):
    """Round 2 of the E14 punch list (the control room's grant): `record` hands the floor the recorded reviewer's
    `session_id` with its model, so it applies the rule `record-answer` applied. What only the full rule refuses: a
    reviewer model at the floor that is not the session's model, on an answer whose `session_id` names no portable
    transport. `record-answer` never records such a model, so the case is a run whose state was changed between the
    two phases (the re-check exists for that): the class alone passes it, the full rule refuses it."""

    def setUp(self):
        _Floor.setUp(self)
        self.with_model({"id": OPUS, "floor_class": "opus", "floor_met": True})

    def answered_then_changed(self, session_id):
        answer = self.answer_model(OPUS)
        answer["session_id"] = session_id
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(body))
        path = os.path.join(self.run_dir, "state.json")
        state = testlib.load_json(path)
        state["reviewer"]["model"] = FABLE
        state["floor"]["reviewer"]["model"] = FABLE
        testlib.write_json(path, state)

    def test_a_claude_session_answer_changed_to_another_opus_model_is_refused_at_record(self):
        self.answered_then_changed("claude-subagent:signoff-fix2-run-review")
        code, body, err = self.record()
        self.assert_floor_stop(code, body, err)

    def test_the_portable_transport_is_still_judged_by_its_class_at_record(self):
        self.answered_then_changed("claude-cli:signoff-fix2-run-review")
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        self.assertEqual(self.result()["status"], "completed", json.dumps(self.result())[:1200])


if __name__ == "__main__":
    unittest.main()
