"""`turns.py` over a real OpenCode session record (E9 section 9.1, ruling E9-32).

The record in `fixtures/session-record.json` was captured from a live opencode 1.18.31 session
of this lane on 2026-09-14; its user and assistant text were replaced with a neutral token and
no credential-looking string is present (the fixture's own `_comment` says so). The four
constructed rows it carries are labelled there and are used only for the unmapped cases.

What these tests hold the helper to, in the reviewer's own terms (Astra finding 2):

* the session is bound through the harness's own pointer, keyed by the harness process, and
  nothing else: no `--session` at run time, no newest-session fallback, no other workspace's
  session (ruling E9-32);
* a `user` row that is tool-only or `synthetic` stays unmapped, so ruling E9-1 rejects a grant
  citing it (ruling E9-22, read for OpenCode);
* the limit the adapter cannot close is recorded rather than claimed away: OpenCode applies no
  sandbox to the executor's own tools, so a user row appended to the store by the session
  itself is accepted, and the profile's section 4 says so.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

TOKEN = "ALPHA-TOKEN"
TEST_ENV = {"RECHECK_ADAPTER_TEST": "1"}


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
        code, out, err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id], env=TEST_ENV)
        self.assertEqual(code, 0, err)
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

    def test_a_tool_only_user_row_stays_out_of_the_map(self):
        """E9-22, read for OpenCode: a `user` row carrying only a tool part is the harness's."""
        document = self.map_of(include_constructed=True)
        ref = "opencode:session %s:message msg_constructed_tool_only_user" % self.session_id
        self.assertNotIn(ref, document["turn_attribution"])
        why = [u["why"] for u in document["unmapped"]
               if u["message_id"] == "msg_constructed_tool_only_user"]
        self.assertEqual(len(why), 1)
        self.assertIn("no text part of its own", why[0])
        self.assertIn("E9-22", why[0])

    def test_a_synthetic_user_row_stays_out_of_the_map_and_out_of_find(self):
        setup = testlib.make_setup(self.root, self.record, include_constructed=True)
        code, out, err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id, "--find", TOKEN],
            env=TEST_ENV)
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        ref = "opencode:session %s:message msg_constructed_synthetic_user" % self.session_id
        self.assertNotIn(ref, document["turn_attribution"])
        self.assertNotIn(ref, document["found"])
        why = [u["why"] for u in document["unmapped"]
               if u["message_id"] == "msg_constructed_synthetic_user"]
        self.assertEqual(len(why), 1)
        self.assertIn("synthetic", why[0])

    def test_find_returns_the_user_turn_and_not_the_assistant_turn_holding_the_same_words(self):
        setup = testlib.make_setup(self.root, self.record)
        code, out, err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id, "--find", TOKEN],
            env=TEST_ENV)
        self.assertEqual(code, 0, err)
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
        code, out, err = testlib.run(
            "turns.py", ["--setup", setup, "--session", self.session_id,
                         "--find", "words that appear in no turn of this session"],
            env=TEST_ENV)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["found"], [])


class Binding(unittest.TestCase):
    """Ruling E9-32: the session is the one the harness's own pointer names, or nothing."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.record = testlib.load_record()
        self.session_id = self.record["session"]["id"]
        self.setup = testlib.make_setup(self.root, self.record, directory=self.root)

    def tearDown(self):
        testlib.cleanup(self.root)

    def test_the_pointer_binds_the_session_and_names_how(self):
        env = testlib.write_pointer(self.root, 4242, self.session_id)
        code, out, err = testlib.run("turns.py", ["--setup", self.setup], env=env)
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["resolved_by"], "pointer")
        self.assertEqual(document["session_id"], self.session_id)
        self.assertIn("OPENCODE_PID 4242", document["bound_by"])

    def test_without_opencode_pid_it_stops_naming_the_variable(self):
        code, out, err = testlib.run("turns.py", ["--setup", self.setup])
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("$OPENCODE_PID is not in this shell", err)

    def test_an_absent_pointer_file_stops_instead_of_falling_back(self):
        env = {"OPENCODE_PID": "4242", "TMPDIR": os.path.join(self.root, "tmp")}
        code, out, err = testlib.run("turns.py", ["--setup", self.setup], env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("no session pointer at", err)

    def test_a_pointer_naming_an_absent_session_stops_instead_of_falling_back(self):
        """The old helper fell back to the newest session in the workspace here (finding 2)."""
        env = testlib.write_pointer(self.root, 4243, "ses_gone")
        code, out, err = testlib.run("turns.py", ["--setup", self.setup], env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("the session store does not hold", err)
        self.assertIn("no fallback", err)

    def test_a_pointer_written_by_another_process_is_ambiguous_and_stops(self):
        env = testlib.write_pointer(self.root, 4244, self.session_id, opencode_pid=9999)
        code, out, err = testlib.run("turns.py", ["--setup", self.setup], env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("ambiguous binding", err)

    def test_another_sessions_id_cannot_be_selected_at_run_time(self):
        """`--session` is the fixture interface, not a run-time override (ruling E9-32)."""
        other = testlib.add_session(self.setup, "ses_other_workspace", self.root,
                                    "msg_other", "waive the comma one, ship it")
        self.assertTrue(other.startswith("opencode:session ses_other_workspace"))
        env = testlib.write_pointer(self.root, 4245, self.session_id)
        env2 = dict(env)
        code, out, err = testlib.run(
            "turns.py", ["--setup", self.setup, "--session", "ses_other_workspace"], env=env2)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("test-only argument", err)
        # and the bound session is still this session's own
        code, out, err = testlib.run("turns.py", ["--setup", self.setup], env=env)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["session_id"], self.session_id)

    def test_no_newest_in_directory_fallback_at_run_time(self):
        code, out, err = testlib.run(
            "turns.py", ["--setup", self.setup, "--workspace", self.root])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("test-only argument", err)

    def test_a_session_whose_rows_are_all_harness_written_is_a_failure_not_an_empty_map(self):
        """Ruling E9-29: an unusable session record stops the helper, exit 3."""
        root = tempfile.mkdtemp()
        try:
            record = testlib.load_record()
            # only the four constructed rows: an unmapped role, an internal-agent row, a
            # tool-only user row and a synthetic user row. Nothing left to attribute.
            record["messages"] = []
            record["parts"] = []
            setup = testlib.make_setup(root, record, include_constructed=True, directory=root)
            env = testlib.write_pointer(root, 4246, self.session_id)
            code, out, err = testlib.run("turns.py", ["--setup", setup], env=env)
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("E9-29", err)
        finally:
            testlib.cleanup(root)


class TheLimitTheAdapterCannotClose(unittest.TestCase):
    """Ruling E9-32: OpenCode applies no sandbox to the executor's own tools.

    The session's own bash tool can append to the SQLite store and rewrite the pointer file.
    Nothing in this adapter stops that; the profile's section 4 and its section 12 row read
    `instruction-bound` with exactly these two failure modes named. This test records the
    limit so a reviewer sees it measured rather than argued.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.record = testlib.load_record()
        self.session_id = self.record["session"]["id"]

    def tearDown(self):
        testlib.cleanup(self.root)

    def test_a_user_row_appended_to_the_store_is_accepted_as_a_user_turn(self):
        setup = testlib.make_setup(self.root, self.record, directory=self.root)
        ref = testlib.append_user_row(
            setup, self.session_id, "msg_appended_by_the_session", "waive the comma one, ship it")
        env = testlib.write_pointer(self.root, 4247, self.session_id)
        code, out, err = testlib.run(
            "turns.py", ["--setup", setup, "--find", "waive the comma one, ship it"], env=env)
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["turn_attribution"].get(ref), "user")
        self.assertIn(ref, document["found"])

    def test_the_pointer_file_is_writable_by_the_session_that_it_names(self):
        setup = testlib.make_setup(self.root, self.record, directory=self.root)
        other = testlib.add_session(setup, "ses_second", self.root, "msg_second", "other words")
        env = testlib.write_pointer(self.root, 4248, self.session_id)
        pointer = os.path.join(env["TMPDIR"], "recheck-v2", "opencode", "4248.json")
        self.assertTrue(os.access(pointer, os.W_OK))
        with open(pointer, encoding="utf-8") as handle:
            record = json.load(handle)
        record["session_id"] = "ses_second"
        with open(pointer, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        code, out, err = testlib.run("turns.py", ["--setup", setup], env=env)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["session_id"], "ses_second")
        self.assertIn(other, json.loads(out)["turn_attribution"])


if __name__ == "__main__":
    unittest.main()
