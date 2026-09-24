"""E13 full-review fix round, send-back 1 (Astra's F4, build side): the invocation block carries
the session id the adapter read from the harness record, the same value as `answer_fields`, so the
build run records its harness identity without the executor typing it."""
import json
import unittest

import testlib

HELPER = "invocation.py"


class TheInvocationCarriesTheHarnessSession(unittest.TestCase):
    def test_session_id_in_invocation_equals_answer_fields(self):
        doc = testlib.run_json(HELPER, [])
        self.assertEqual(doc["invocation"].get("session_id"), testlib.THREAD, json.dumps(doc["invocation"]))
        self.assertEqual(doc["invocation"]["session_id"], doc["answer_fields"]["session_id"])


if __name__ == "__main__":
    unittest.main()
