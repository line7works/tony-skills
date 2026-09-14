"""verifier.py: the readers request block, and the sidecar mapped onto the
record-call flags under the adapter test hook."""

import json
import os
import shutil
import tempfile
import unittest

import testlib

SIDECAR_OK = os.path.join(testlib.FIXTURES, "readers-sidecar-ok.json")


def canned(sidecar, raw_text=None):
    """A canned readers reply on disk, as the test hook reads it."""
    directory = tempfile.mkdtemp(prefix="recheck-adapter-canned-")
    with open(SIDECAR_OK, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    document.update(sidecar)
    if raw_text is not None:
        raw = os.path.join(directory, "raw.md")
        with open(raw, "w", encoding="utf-8") as handle:
            handle.write(raw_text)
        document["raw_file"] = raw
        document["raw_path"] = raw
    with open(os.path.join(directory, "sidecar.json"), "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
    return directory


class RequestBlockTest(unittest.TestCase):
    def setUp(self):
        self.run_dir = tempfile.mkdtemp(prefix="recheck-adapter-run-")
        self.addCleanup(shutil.rmtree, self.run_dir, True)
        self.brief = os.path.join(self.run_dir, "checklist.md")
        with open(self.brief, "w", encoding="utf-8") as handle:
            handle.write("the brief\n")
        self.scratch = os.path.join(self.run_dir, "verifier")
        os.makedirs(self.scratch)
        self.args = [
            "--brief", self.brief,
            "--workspace", "/tmp/widget-workspace",
            "--scratch", self.scratch,
            "--raw", os.path.join(self.scratch, "raw.md"),
            "--transcript", testlib.TRANSCRIPT,
        ]

    def request(self, extra):
        return testlib.run_json("verifier.py", self.args + extra)["request"]

    def test_the_block_matches_verifier_md_section_6(self):
        block = self.request(["--call-id", "recheck-a-20260920-7f3c-verify"])
        self.assertEqual(
            sorted(block),
            sorted([
                "protocol_version", "run_id", "call_id", "run_dir", "row", "mandate",
                "workspace", "profile", "raw_path", "floor", "session_model",
            ]),
        )
        self.assertEqual(block["protocol_version"], 1)
        self.assertEqual(block["row"], "claude-session")
        self.assertEqual(block["profile"], "repo-with-tools")
        self.assertEqual(block["run_id"], "recheck-a-20260920-7f3c")
        self.assertEqual(block["mandate"], self.brief)
        self.assertEqual(block["run_dir"], self.scratch)
        self.assertEqual(block["floor"], "opus")

    def test_authorized_is_omitted_and_no_pick_is_written(self):
        document = testlib.run_json(
            "verifier.py", self.args + ["--call-id", "r-verify"]
        )
        self.assertNotIn("authorized", document["request"])
        for field in ("model", "effort", "output_budget", "isolation"):
            self.assertNotIn(field, document["request"])
            self.assertIn(field, document["_sources"]["never_written"])

    def test_session_model_comes_from_the_harness_record(self):
        block = self.request(["--call-id", "r-verify"])
        self.assertEqual(block["session_model"], "claude-opus-5")

    def test_the_raw_path_of_a_re_send(self):
        block = self.request([
            "--call-id", "recheck-a-20260920-7f3c-verify-2",
            "--run-id", "recheck-a-20260920-7f3c",
        ])
        self.assertEqual(block["call_id"], "recheck-a-20260920-7f3c-verify-2")
        self.assertEqual(block["run_id"], "recheck-a-20260920-7f3c")

    def test_a_call_id_without_the_verify_suffix_is_a_usage_slip(self):
        code, out, err = testlib.run("verifier.py", self.args + ["--call-id", "nope"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("pass --run-id", err)

    def test_the_floor_travels_from_the_input(self):
        block = self.request(["--call-id", "r-verify", "--floor", "sonnet"])
        self.assertEqual(block["floor"], "sonnet")


class SidecarMapTest(unittest.TestCase):
    def map_of(self, directory):
        return testlib.run_json(
            "verifier.py",
            [],
            env={"RECHECK_ADAPTER_TEST": "1", "RECHECK_ADAPTER_CANNED": directory},
        )

    def test_ok_with_a_report_on_disk(self):
        directory = canned({"status": "ok"}, raw_text="prose\n```json\n{}\n```\n")
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertEqual(document["status"], "ok")
        self.assertTrue(os.path.isfile(document["raw"]))
        self.assertEqual(document["model"], "claude-opus-5")
        self.assertEqual(document["kind"], "claude-subagent")
        self.assertIsNone(document["note"])

    def test_ok_without_a_report_becomes_capture_failed(self):
        directory = canned({"status": "ok", "raw_file": "/nope/raw.md", "raw_path": "/nope/raw.md"})
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertEqual(document["status"], "capture-failed")
        self.assertIn("missing or empty", document["note"])

    def test_empty(self):
        directory = canned({"status": "empty", "reason": "no content", "raw_file": None,
                            "raw_path": None})
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertEqual(document["status"], "empty")
        self.assertEqual(document["note"], "no content")

    def test_transport_failed_keeps_the_transport_error(self):
        directory = canned({"status": "transport-failed", "reason": "the tool failed: boom",
                            "raw_file": None, "raw_path": None})
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertEqual(document["status"], "transport-failed")
        self.assertEqual(document["note"], "the tool failed: boom")

    def test_timed_out(self):
        directory = canned({"status": "timed-out", "reason": "1800 s elapsed",
                            "raw_file": None, "raw_path": None})
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertEqual(document["status"], "timed-out")
        self.assertEqual(document["note"], "1800 s elapsed")

    def test_oversize_becomes_invalid_request_with_the_numbers(self):
        directory = canned({
            "status": "oversize", "reason": "packet too large",
            "budget": {"estimate_tokens": 900000, "limit": 200000},
            "raw_file": None, "raw_path": None,
        })
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertEqual(document["status"], "invalid-request")
        self.assertIn("900000", document["note"])
        self.assertIn("200000", document["note"])

    def test_injected_channels_are_the_measured_list_plus_the_sidecar_files(self):
        directory = canned(
            {"status": "ok", "workdir_instruction_files": ["AGENTS.md"]},
            raw_text="x\n",
        )
        self.addCleanup(shutil.rmtree, directory, True)
        document = self.map_of(directory)
        self.assertIn("workdir instruction file: AGENTS.md", document["injected"])
        self.assertEqual(len(document["injected"]), 7)
        self.assertTrue(any("git-status block" in entry for entry in document["injected"]))
        self.assertTrue(any("userEmail" in entry for entry in document["injected"]))

    def test_a_status_outside_the_vocabulary_is_refused(self):
        directory = canned({"status": "weird", "raw_file": None, "raw_path": None})
        self.addCleanup(shutil.rmtree, directory, True)
        code, out, err = testlib.run(
            "verifier.py",
            [],
            env={"RECHECK_ADAPTER_TEST": "1", "RECHECK_ADAPTER_CANNED": directory},
        )
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("outside the verifier.md section 4 vocabulary", err)

    def test_a_canned_response_outside_a_test_is_refused(self):
        directory = canned({"status": "ok"}, raw_text="x\n")
        self.addCleanup(shutil.rmtree, directory, True)
        code, out, err = testlib.run(
            "verifier.py", [], env={"RECHECK_ADAPTER_CANNED": directory}
        )
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("canned response outside test", err)

    def test_the_real_sidecar_fixture_maps(self):
        document = testlib.run_json("verifier.py", ["--sidecar", SIDECAR_OK])
        # its raw file does not exist under /tmp, so ok is downgraded honestly
        self.assertEqual(document["status"], "capture-failed")
        self.assertEqual(document["model"], "claude-opus-5")
        self.assertEqual(document["kind"], "claude-subagent")
        self.assertIn("never here", document["_sources"]["retry"])


if __name__ == "__main__":
    unittest.main()
