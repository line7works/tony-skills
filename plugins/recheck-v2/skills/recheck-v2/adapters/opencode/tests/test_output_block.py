"""S4 (E11-45): the generated output block checked against OpenCode's real final message.

Every test fails against the batch-A commit `c285358` (the module does not exist there) and
passes after batch B. The store here is a minimal one built in the test, with the two columns
the reader uses; the adapter's own `turns.message_text` reads the parts.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import output_block  # noqa: E402

BLOCK = """RECHECK: A — 1 items (+0 new)
Result: PARTIAL (1 open) · Status: rejected → rejected
Source: 0578c62 dirty · Verifier: subagent, test-model
Method: item 0 — executed the scenario command
BLOCKER · src/widget/export.py:9 · (titles with a comma are unquoted) · not fixed (missed_case) · executed the scenario"""

GOOD = BLOCK + "\n\nBottom line: one item stays open.\n"
NO_BLOCK = "I looked at the export code and it seems fine now.\n"
CONTRADICTS = """RECHECK: A — 1 items (+0 new)
Result: PARTIAL (1 open) · Status: rejected → rejected
Source: 0578c62 dirty · Verifier: subagent, test-model
Method: item 0 — executed the scenario command
BLOCKER · src/widget/export.py:9 · (titles with a comma are unquoted) · fixed · executed the scenario"""
USER_REQUEST = "Please recheck slice A of docs/plans/widget-export.md and flip the card.\n"

SESSION = "ses_s4"


class S4OutputBlock(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="s4-opencode-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "opencode.db")
        con = sqlite3.connect(self.path)
        con.execute("create table message (id text, session_id text, time_created integer, "
                    "data text)")
        con.execute("create table part (id text, message_id text, session_id text, "
                    "time_created integer, data text)")
        con.commit()
        con.close()

    def add(self, message_id, role, text, when):
        con = sqlite3.connect(self.path)
        con.execute("insert into message (id, session_id, time_created, data) values (?,?,?,?)",
                    (message_id, SESSION, when, json.dumps({"role": role})))
        con.execute("insert into part (id, message_id, session_id, time_created, data) "
                    "values (?,?,?,?,?)",
                    (message_id + "-p", message_id, SESSION, when,
                     json.dumps({"type": "text", "text": text})))
        con.commit()
        con.close()

    def con(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        self.addCleanup(con.close)
        return con

    def test_a_trace_with_the_block_passes(self):
        self.add("m1", "user", USER_REQUEST, 1)
        self.add("m2", "assistant", GOOD, 2)
        text, source = output_block.final_assistant_text(self.con(), SESSION)
        self.assertIn("assistant text part", source)
        got = output_block.check_output_block(BLOCK, text)
        self.assertTrue(got["ok"], got)

    def test_a_trace_without_the_block_fails(self):
        self.add("m1", "assistant", NO_BLOCK, 1)
        text, _source = output_block.final_assistant_text(self.con(), SESSION)
        got = output_block.check_output_block(BLOCK, text)
        self.assertFalse(got["ok"])
        self.assertTrue(got["why"].startswith("no block"), got["why"])

    def test_a_block_contradicting_the_result_fails(self):
        self.add("m1", "assistant", CONTRADICTS, 1)
        text, _source = output_block.final_assistant_text(self.con(), SESSION)
        got = output_block.check_output_block(BLOCK, text)
        self.assertFalse(got["ok"])
        self.assertIn("contradicts", got["why"])

    def test_the_user_request_is_never_read_as_the_reply(self):
        """Read2's false positive, closed: a user row carrying the block is not the reply."""
        self.add("m1", "user", GOOD, 1)
        text, source = output_block.final_assistant_text(self.con(), SESSION)
        self.assertEqual(text, "")
        self.assertIsNone(source)
        got = output_block.check_output_block(BLOCK, text)
        self.assertTrue(got["why"].startswith("no reply"), got["why"])

    def test_no_assistant_text_is_no_reply_never_no_block(self):
        got = output_block.check_output_block(BLOCK, "")
        self.assertTrue(got["why"].startswith("no reply"))


if __name__ == "__main__":
    unittest.main()
