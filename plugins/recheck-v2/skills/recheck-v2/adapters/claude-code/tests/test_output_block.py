"""S4 (E11-45): the generated output block checked against Claude Code's real final message.

Every test fails against the batch-A commit `c285358` (the module does not exist there) and
passes after batch B. The two controls that pass on both trees are named as such.
"""
import json
import os
import shutil
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


class S4OutputBlock(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="s4-claude-code-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def trace(self, rows):
        path = os.path.join(self.dir, "trace.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        return path

    def test_a_trace_with_the_block_passes(self):
        self.trace([{"type": "user", "message": {"content": USER_REQUEST}},
                    {"type": "result", "result": GOOD}])
        text, source = output_block.final_assistant_text(self.dir)
        self.assertIn("result event", source)
        got = output_block.check_output_block(BLOCK, text)
        self.assertTrue(got["ok"], got)

    def test_a_trace_without_the_block_fails(self):
        self.trace([{"type": "result", "result": NO_BLOCK}])
        text, _source = output_block.final_assistant_text(self.dir)
        got = output_block.check_output_block(BLOCK, text)
        self.assertFalse(got["ok"])
        self.assertTrue(got["why"].startswith("no block"), got["why"])

    def test_a_block_contradicting_the_result_fails(self):
        self.trace([{"type": "result", "result": CONTRADICTS}])
        text, _source = output_block.final_assistant_text(self.dir)
        got = output_block.check_output_block(BLOCK, text)
        self.assertFalse(got["ok"])
        self.assertIn("contradicts", got["why"])
        self.assertEqual(got["items"][0]["block_disposition"], "not_fixed")
        self.assertEqual(got["items"][0]["reply_disposition"], "fixed")

    def test_the_user_request_is_never_read_as_the_reply(self):
        """No result event at all: the session produced no assistant text."""
        self.trace([{"type": "user", "message": {"content": USER_REQUEST}}])
        text, source = output_block.final_assistant_text(self.dir)
        self.assertEqual(text, "")
        self.assertIsNone(source)
        got = output_block.check_output_block(BLOCK, text)
        self.assertFalse(got["ok"])
        self.assertTrue(got["why"].startswith("no reply"), got["why"])

    def test_no_assistant_text_is_no_reply_never_no_block(self):
        got = output_block.check_output_block(BLOCK, "")
        self.assertTrue(got["why"].startswith("no reply"))
        self.assertNotIn("no block", got["why"])


if __name__ == "__main__":
    unittest.main()
