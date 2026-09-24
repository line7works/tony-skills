"""E13 full-review fix round, send-back 1 (Astra's F4, build side).

`invocation.session_id` is the harness-read session the build adapter supplies; the executor's
typed `answer.session_id` must equal it or the run stops `session_mismatch` with no project write,
and the result records the invocation, so a signoff adapter reads the building session from the
build run's harness identity rather than from typed text."""
import json
import os
import unittest

import testlib


class _Run(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-sb1-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")
        self.input = os.path.join(self.scratch, "input.json")
        self.answer = os.path.join(self.scratch, "answer.json")
        testlib.write_json(self.answer, testlib.ANSWER)
        self.env = testlib.base_env({"RECORDS_ROOT": testlib.RECORDS_ROOT})

    def write_input(self, session_id):
        body = testlib.make_input(self.run_dir, self.ws)
        if session_id is not False:
            body["invocation"]["session_id"] = session_id
        testlib.write_json(self.input, body)

    def phase(self, args):
        return testlib.run_build(args, env=self.env)

    def through(self):
        for args in (["check-input", self.input], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir]):
            code, out, err = self.phase(args)
            self.assertEqual(code, 0, "%s: %s%s" % (args[0], out, err))
        self.after_preflight = testlib.tree_digest(self.ws)
        return self.phase(["record-answer", "--run-dir", self.run_dir, "--answer", self.answer])

    def result(self):
        return testlib.load_json(os.path.join(self.run_dir, "result.json"))


class TheInvocationSessionIsTheHarnessRecord(_Run):
    def test_the_schema_takes_it(self):
        self.write_input("sess-test-1")
        code, out, err = self.phase(["check-input", self.input])
        self.assertEqual(code, 0, out + err)

    def test_a_typed_answer_session_that_differs_stops(self):
        self.write_input("sess-harness-9")
        code, out, err = self.through()
        if code == 0:
            code, out, err = self.phase(["report", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, out + err)
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:800])
        self.assertEqual(result["stop_tag"], "session_mismatch")
        self.assertEqual(result["records"]["appended"], [])
        self.assertEqual(testlib.tree_digest(self.ws), self.after_preflight,
                         "no project write after the answer arrived")
        self.assertNotIn("sess-harness-9", json.dumps(result["answer"]), "the typed copy is reported as typed")
        self.assertEqual(result["invocation"]["session_id"], "sess-harness-9")

    def test_the_agreeing_run_completes_and_records_the_invocation(self):
        self.write_input("sess-test-1")
        code, out, err = self.through()
        self.assertEqual(code, 0, out + err)
        code, out, err = self.phase(["report", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, out + err)
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:800])
        self.assertEqual(result["invocation"]["session_id"], "sess-test-1")

    def test_a_run_without_it_records_null(self):
        self.write_input(False)
        self.through()
        self.phase(["report", "--run-dir", self.run_dir])
        self.assertIsNone(self.result()["invocation"].get("session_id"))


if __name__ == "__main__":
    unittest.main()
