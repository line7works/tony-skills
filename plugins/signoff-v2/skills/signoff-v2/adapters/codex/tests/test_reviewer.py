"""signoff-v2 on Codex: reviewer.py (E13 slice 3, brief 3.1: the pilot's Codex verifier shape).

The helper launches ONE fresh `codex exec` reviewer with the core's mandate on stdin, captures
the child's own rollout, and prints the reviewer identity the answer carries and the
`record-answer` flags; the core never launches. Every test here uses the canned transport
(test mode only): no test launches Codex or calls a model.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "reviewer.py"
CHILD = os.path.join(testlib.FIXTURES, "child-rollout.jsonl")
CHILD_THREAD = "01a0a1e3-1b19-7d23-8225-c251b82329dc"


def fake_run(parent, request=True):
    run_dir = os.path.join(parent, "signoff-f-20260923-ab12")
    readers = os.path.join(run_dir, "readers")
    os.makedirs(os.path.join(run_dir, "packet"))
    os.makedirs(readers)
    with open(os.path.join(readers, "mandate.md"), "w") as handle:
        handle.write("# Reviewer mandate\n")
    if request:
        with open(os.path.join(run_dir, "request.json"), "w") as handle:
            json.dump({"protocol_version": 1, "run_id": "signoff-f-20260923-ab12",
                       "call_id": "signoff-f-20260923-ab12-review",
                       "run_dir": os.path.join(readers, "calls"), "row": "claude-session",
                       "profile": "repo-with-tools", "workspace": parent,
                       "documents": [], "mandate": os.path.join(readers, "mandate.md"),
                       "floor": "opus", "session_model": "gpt-6-astra"}, handle)
    return run_dir


def canned(parent, exit_code=0, raw="the reviewer's report\n", child=True):
    folder = os.path.join(parent, "canned")
    os.makedirs(folder)
    with open(os.path.join(folder, "transport.json"), "w") as handle:
        json.dump({"exit": exit_code}, handle)
    with open(os.path.join(folder, "events.jsonl"), "w") as handle:
        handle.write(json.dumps({"type": "thread.started", "thread_id": CHILD_THREAD}) + "\n")
    if raw is not None:
        with open(os.path.join(folder, "raw.md"), "w") as handle:
            handle.write(raw)
    if child:
        shutil.copyfile(CHILD, os.path.join(folder, "child-rollout.jsonl"))
    return folder


class ReviewerTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="codex-reviewer-")
        self.run_dir = fake_run(self.work)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def call(self, extra_args=(), env=None):
        return testlib.run(HELPER, ["--run-dir", self.run_dir, "--workspace", self.work]
                           + list(extra_args), env=env)

    def test_help_and_usage(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])
        self.assertEqual(testlib.run(HELPER, ["--bogus"])[0], 2)

    def test_a_canned_ok_names_the_child_and_the_record_answer_flags(self):
        code, out, err = self.call(["--lens", "spec"],
                                   env={testlib.PREFIX + "_ADAPTER_CANNED": canned(self.work)})
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["answer_identity"], {"session_id": CHILD_THREAD,
                                                  "model": "gpt-6-astra"})
        self.assertEqual(doc["call_id"], "signoff-f-20260923-ab12-review-spec")
        self.assertTrue(os.path.isfile(doc["raw"]))
        self.assertEqual(doc["record_answer"]["argv"][:3], ["record-answer", "--run-dir",
                                                            self.run_dir])
        self.assertTrue(doc["injected"])

    def test_a_call_id_is_single_use(self):
        env = {testlib.PREFIX + "_ADAPTER_CANNED": canned(self.work)}
        self.assertEqual(self.call(env=env)[0], 0)
        code, out, err = self.call(env=env)
        self.assertEqual(code, 2, err)

    def test_a_failed_transport_has_no_identity(self):
        code, out, err = self.call(env={testlib.PREFIX + "_ADAPTER_CANNED":
                                        canned(self.work, exit_code=1, raw=None)})
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["status"], "transport-failed")
        self.assertIsNone(doc["answer_identity"])

    def test_ok_without_the_childs_record_is_lane_unavailable(self):
        code, out, err = self.call(env={testlib.PREFIX + "_ADAPTER_CANNED":
                                        canned(self.work, child=False)})
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["status"], "lane-unavailable")

    def test_canned_outside_test_mode_is_refused(self):
        code, out, err = self.call(env={testlib.PREFIX + "_ADAPTER_CANNED": canned(self.work),
                                        testlib.TEST_FLAG: None})
        self.assertNotEqual(code, 0)

    def test_no_confinement_witness_launches_nothing(self):
        code, out, err = self.call(env={"CODEX_HOME": self.work})
        self.assertEqual(code, 3, err)
        self.assertIn("nothing launched", json.loads(out)["error"])

    def test_no_request_is_exit_3_naming_independence(self):
        os.remove(os.path.join(self.run_dir, "request.json"))
        code, out, err = self.call(env={testlib.PREFIX + "_ADAPTER_CANNED": canned(self.work)})
        self.assertEqual(code, 3, err)
        self.assertIn("independence", json.loads(out)["error"])


if __name__ == "__main__":
    unittest.main()
