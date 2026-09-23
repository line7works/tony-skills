"""signoff-v2 on Codex: reviewer.py, the readers request and the sidecar map (Astra's F6).

The helper carries no reviewer transport: it checks the run's own readers request, reports that
readers has no floor-qualified route a Codex session can dispatch (`lane-unavailable`, exit 3,
the missing capability named), and maps a readers sidecar onto the answer's reviewer identity.
No test launches Codex or calls a model; `test_full_fix_f6.py` proves nothing is launched even
with a `codex` on PATH.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "reviewer.py"


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
        self.assertNotIn("codex exec", json.loads(out)["help"])
        self.assertEqual(testlib.run(HELPER, [])[0], 2)

    def test_the_run_request_is_lane_unavailable_with_the_capability_named(self):
        code, out, err = self.call()
        self.assertEqual(code, 3, err)
        doc = json.loads(out)
        self.assertEqual(doc["status"], "lane-unavailable")
        self.assertIn("floor-qualified", doc["missing_capability"])
        self.assertEqual((doc["requests"], doc["answer_identity"]), ([], None))

    def test_a_request_bound_elsewhere_is_usage(self):
        other = tempfile.mkdtemp(prefix="other-")
        try:
            code, out, err = testlib.run(HELPER, ["--run-dir", self.run_dir, "--workspace", other])
            self.assertEqual(code, 2, err)
        finally:
            shutil.rmtree(other)

    def test_no_request_is_exit_3_naming_independence(self):
        shutil.rmtree(self.work)
        os.makedirs(self.work)
        self.run_dir = fake_run(self.work, request=False)
        code, out, err = self.call()
        self.assertEqual(code, 3, err)
        self.assertIn("independence", err)

    def test_an_ok_sidecar_without_a_raw_report_is_capture_failed(self):
        sidecar = os.path.join(self.work, "sidecar.json")
        with open(sidecar, "w") as handle:
            json.dump({"status": "ok", "raw_file": os.path.join(self.work, "absent.md"),
                       "effective_model": "claude-opus-5-5", "transport": "claude-subagent",
                       "call_id": "c-1"}, handle)
        doc = testlib.run_json(HELPER, ["--sidecar", sidecar, "--run-dir", self.run_dir])
        self.assertEqual(doc["status"], "capture-failed")
        self.assertIsNone(doc["answer_identity"])

    def test_a_status_outside_readers_vocabulary_is_usage(self):
        sidecar = os.path.join(self.work, "sidecar.json")
        with open(sidecar, "w") as handle:
            json.dump({"status": "transported"}, handle)
        code, out, err = testlib.run(HELPER, ["--sidecar", sidecar, "--run-dir", self.run_dir])
        self.assertEqual(code, 2, err)


if __name__ == "__main__":
    unittest.main()
