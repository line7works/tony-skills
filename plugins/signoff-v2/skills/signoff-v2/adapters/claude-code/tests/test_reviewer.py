"""signoff-v2 on Claude Code: reviewer.py (E13 slice 3, brief 3.1: lane C's shape).

Request mode prints the readers request block(s) from the request the core's `request` phase
wrote, with `session_model` read from the harness's own record; record mode maps the readers
sidecar onto the reviewer identity the answer carries and the `record-answer` flags. The helper
launches nothing: `/readers` runs the fresh subagent.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "reviewer.py"
SIDECAR = os.path.join(testlib.FIXTURES, "readers-sidecar-ok.json")


def fake_run(parent, request=True, session_model="claude-opus-5"):
    run_dir = os.path.join(parent, "signoff-f-20260923-ab12")
    readers = os.path.join(run_dir, "readers")
    os.makedirs(os.path.join(run_dir, "packet"))
    os.makedirs(readers)
    with open(os.path.join(readers, "mandate.md"), "w") as handle:
        handle.write("# Reviewer mandate\n")
    with open(os.path.join(run_dir, "packet", "material.md"), "w") as handle:
        handle.write("material\n")
    if request:
        with open(os.path.join(run_dir, "request.json"), "w") as handle:
            json.dump({"protocol_version": 1, "run_id": "signoff-f-20260923-ab12",
                       "call_id": "signoff-f-20260923-ab12-review",
                       "run_dir": os.path.join(readers, "calls"), "row": "claude-session",
                       "profile": "repo-with-tools", "workspace": "/tmp/widget-workspace",
                       "documents": [os.path.join(run_dir, "packet", "material.md")],
                       "mandate": os.path.join(readers, "mandate.md"), "floor": "opus",
                       "session_model": session_model}, handle)
    return run_dir


class RequestModeTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="reviewer-")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def test_help_and_usage(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])
        self.assertEqual(testlib.run(HELPER, ["--bogus"])[0], 2)
        self.assertEqual(testlib.run(HELPER, [])[0], 2)

    def test_one_request_per_lens_with_the_records_model(self):
        run_dir = fake_run(self.work)
        doc = testlib.run_json(HELPER, testlib.fixture_args() + [
            "--run-dir", run_dir, "--lens", "spec", "--lens", "correctness"])
        requests = doc["requests"]
        self.assertEqual([r["call_id"] for r in requests],
                         ["signoff-f-20260923-ab12-review-spec",
                          "signoff-f-20260923-ab12-review-correctness"])
        for request in requests:
            self.assertEqual(request["session_model"], "claude-opus-5")
            self.assertEqual((request["row"], request["profile"], request["floor"]),
                             ("claude-session", "repo-with-tools", "opus"))
            for never in ("model", "effort", "isolation", "output_budget"):
                self.assertNotIn(never, request)
            self.assertTrue(request["raw_path"].startswith(os.path.join(run_dir, "readers",
                                                                        "calls")))

    def test_no_request_file_is_exit_3_and_names_independence(self):
        run_dir = fake_run(self.work, request=False)
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--run-dir", run_dir])
        self.assertEqual(code, 3, err)
        self.assertIn("independence", json.loads(out)["error"])

    def test_a_request_outside_its_run_is_refused(self):
        run_dir = fake_run(self.work)
        path = os.path.join(run_dir, "request.json")
        with open(path) as handle:
            request = json.load(handle)
        request["mandate"] = "/tmp/outside-brief.md"
        with open(path, "w") as handle:
            json.dump(request, handle)
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--run-dir", run_dir])
        self.assertEqual(code, 2, err)

    def test_a_disagreeing_session_model_is_reported_and_the_record_wins(self):
        run_dir = fake_run(self.work, session_model="claude-sonnet-4-5")
        doc = testlib.run_json(HELPER, testlib.fixture_args() + ["--run-dir", run_dir])
        self.assertEqual(doc["requests"][0]["session_model"], "claude-opus-5")
        self.assertIn("claude-sonnet-4-5", doc["_sources"]["session_model"])

    def test_from_another_working_directory(self):
        run_dir = fake_run(self.work)
        elsewhere = tempfile.mkdtemp(prefix="elsewhere-")
        try:
            one = testlib.run_json(HELPER, testlib.fixture_args() + ["--run-dir", run_dir])
            two = testlib.run_json(HELPER, testlib.fixture_args() + ["--run-dir", run_dir],
                                   cwd=elsewhere)
            self.assertEqual(one["requests"], two["requests"])
        finally:
            shutil.rmtree(elsewhere)


class RecordModeTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="reviewer-record-")
        self.run_dir = fake_run(self.work)
        self.raw = os.path.join(self.work, "raw.md")
        with open(self.raw, "w") as handle:
            handle.write("report\n")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def sidecar(self, **changes):
        with open(SIDECAR) as handle:
            doc = json.load(handle)
        doc.update({"raw_path": self.raw, "raw_file": self.raw, "call_id":
                    "signoff-f-20260923-ab12-review-spec"})
        doc.update(changes)
        path = os.path.join(self.work, "sidecar.json")
        with open(path, "w") as handle:
            json.dump(doc, handle)
        return path

    def test_ok_maps_to_the_answer_identity_and_the_record_answer_flags(self):
        doc = testlib.run_json(HELPER, ["--sidecar", self.sidecar(), "--run-dir", self.run_dir])
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["answer_identity"], {
            "session_id": "claude-subagent:signoff-f-20260923-ab12-review-spec",
            "model": "claude-opus-5"})
        self.assertEqual(doc["record_answer"]["argv"][:3], ["record-answer", "--run-dir",
                                                            self.run_dir])
        self.assertEqual(doc["record_answer"]["argv"][3], "--answer")

    def test_ok_without_a_raw_report_is_capture_failed(self):
        os.remove(self.raw)
        doc = testlib.run_json(HELPER, ["--sidecar", self.sidecar(), "--run-dir", self.run_dir])
        self.assertEqual(doc["status"], "capture-failed")
        self.assertIsNone(doc["answer_identity"])

    def test_ok_that_names_no_model_is_exit_2(self):
        code, out, err = testlib.run(HELPER, ["--sidecar", self.sidecar(effective_model=""),
                                              "--run-dir", self.run_dir])
        self.assertEqual(code, 2, err)

    def test_a_status_outside_the_vocabulary_is_exit_2(self):
        code, out, err = testlib.run(HELPER, ["--sidecar", self.sidecar(status="fine"),
                                              "--run-dir", self.run_dir])
        self.assertEqual(code, 2, err)

    def test_an_absent_sidecar_is_exit_3(self):
        code, out, err = testlib.run(HELPER, ["--sidecar", "/nonexistent/sidecar.json",
                                              "--run-dir", self.run_dir])
        self.assertEqual(code, 3, err)


if __name__ == "__main__":
    unittest.main()
