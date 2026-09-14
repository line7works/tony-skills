"""`turns.py` over a real OpenCode session record (E9 section 9.1).

The record in `fixtures/session-record.json` was captured from a live opencode 1.18.31 session
of this lane on 2026-09-14; its user and assistant text were replaced with a neutral token and
no credential-looking string is present (the fixture's own `_comment` says so). The two
constructed rows it carries are labelled there and are used only for the unmapped cases.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

TOKEN = "ALPHA-TOKEN"


class TurnMap(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.record = testlib.load_record()
        self.session_id = self.record["session"]["id"]

    def tearDown(self):
        testlib.cleanup(self.root)

    def map_of(self, include_constructed=False):
        setup = testlib.make_setup(self.root, self.record,
                                   include_constructed=include_constructed)
        code, out, _err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id])
        self.assertEqual(code, 0)
        return json.loads(out)

    def test_the_turn_ref_shape_is_the_one_the_profile_fixes(self):
        document = self.map_of()
        self.assertEqual(document["turn_ref_shape"],
                         "opencode:session <session id>:message <message id>")
        for ref in document["turn_attribution"]:
            self.assertTrue(ref.startswith("opencode:session %s:message msg_" % self.session_id),
                            ref)

    def test_roles_come_from_the_records_own_role_field(self):
        document = self.map_of()
        roles = sorted(document["turn_attribution"].values())
        self.assertEqual(roles, ["assistant", "user"])
        for message in self.record["messages"]:
            role = json.loads(message["data"])["role"]
            ref = "opencode:session %s:message %s" % (self.session_id, message["id"])
            self.assertEqual(document["turn_attribution"][ref], role)

    def test_a_row_with_an_unmapped_role_stays_out_of_the_map(self):
        document = self.map_of(include_constructed=True)
        ref = "opencode:session %s:message msg_constructed_unknown_role" % self.session_id
        self.assertNotIn(ref, document["turn_attribution"])
        why = [u["why"] for u in document["unmapped"]
               if u["message_id"] == "msg_constructed_unknown_role"]
        self.assertEqual(why, ["role is not user or assistant"])

    def test_a_row_written_by_an_internal_agent_stays_out_of_the_map(self):
        document = self.map_of(include_constructed=True)
        ref = "opencode:session %s:message msg_constructed_internal_agent" % self.session_id
        self.assertNotIn(ref, document["turn_attribution"])
        why = [u["why"] for u in document["unmapped"]
               if u["message_id"] == "msg_constructed_internal_agent"]
        self.assertEqual(len(why), 1)
        self.assertIn("summary agent", why[0])

    def test_find_returns_the_user_turn_and_not_the_assistant_turn_holding_the_same_words(self):
        setup = testlib.make_setup(self.root, self.record)
        code, out, _err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id, "--find", TOKEN])
        self.assertEqual(code, 0)
        document = json.loads(out)
        user_refs = [t["turn_ref"] for t in document["turns"] if t["role"] == "user"]
        assistant_refs = [t["turn_ref"] for t in document["turns"] if t["role"] == "assistant"]
        # the record's own text: both turns carry the token
        self.assertTrue(any(TOKEN in json.loads(p["data"]).get("text", "")
                            for p in self.record["parts"]
                            if json.loads(p["data"]).get("type") == "text"))
        self.assertEqual(document["found"], user_refs)
        for ref in assistant_refs:
            self.assertNotIn(ref, document["found"])

    def test_find_returns_nothing_for_words_no_user_turn_holds(self):
        setup = testlib.make_setup(self.root, self.record)
        code, out, _err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id,
                         "--find", "words that appear in no turn of this session"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["found"], [])

    def test_the_newest_session_in_the_workspace_is_resolved_and_the_count_is_reported(self):
        setup = testlib.make_setup(self.root, self.record, directory=self.root)
        code, out, _err = testlib.run("turns.py", ["--setup", setup, "--workspace", self.root])
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["resolved_by"], "newest-in-directory")
        self.assertEqual(document["candidates"], 1)
        self.assertEqual(document["session_id"], self.session_id)

    def test_the_plugin_pointer_resolves_the_session_when_opencode_pid_is_set(self):
        setup = testlib.make_setup(self.root, self.record, directory="/nowhere")
        pointer_dir = os.path.join(self.root, "tmp", "recheck-v2", "opencode")
        os.makedirs(pointer_dir)
        with open(os.path.join(pointer_dir, "4242.json"), "w", encoding="utf-8") as handle:
            json.dump({"session_id": self.session_id, "message_id": "msg_x", "role": "user",
                       "opencode_pid": 4242}, handle)
        code, out, _err = testlib.run(
            "turns.py", ["--setup", setup],
            env={"OPENCODE_PID": "4242", "TMPDIR": os.path.join(self.root, "tmp")})
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["resolved_by"], "pointer")
        self.assertEqual(document["session_id"], self.session_id)

    def test_a_pointer_naming_an_absent_session_falls_back_and_says_so(self):
        setup = testlib.make_setup(self.root, self.record, directory=self.root)
        pointer_dir = os.path.join(self.root, "tmp", "recheck-v2", "opencode")
        os.makedirs(pointer_dir)
        with open(os.path.join(pointer_dir, "4243.json"), "w", encoding="utf-8") as handle:
            json.dump({"session_id": "ses_gone", "opencode_pid": 4243}, handle)
        code, out, err = testlib.run(
            "turns.py", ["--setup", setup, "--workspace", self.root],
            env={"OPENCODE_PID": "4243", "TMPDIR": os.path.join(self.root, "tmp")})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["resolved_by"], "newest-in-directory")
        self.assertIn("is not in the store", err)


if __name__ == "__main__":
    unittest.main()
