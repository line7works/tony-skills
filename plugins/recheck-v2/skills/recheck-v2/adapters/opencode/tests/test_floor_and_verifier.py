"""The floor map (E9-3) and `verifier.py`'s status mapping (E9 section 9.1).

The floor map is exercised through `invocation.py`'s own classifier, every class the ruling
names for this lane included and the null case. `verifier.py` is exercised through its test
hook: `RECHECK_ADAPTER_TEST=1` with `RECHECK_ADAPTER_CANNED=<dir>` replaces the launch with
saved files, and the hook set without the test flag is refused.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

sys.path.insert(0, testlib.ADAPTER)
import invocation  # noqa: E402


class FloorMap(unittest.TestCase):
    """Ruling E9-3 for lane Q, provisional for the pilot."""

    def test_the_two_ruled_models_are_class_opus_and_meet_the_default_floor(self):
        for model_id in ("qwen/qwen3.8-flash", "deepseek/deepseek-v4.1-flash"):
            self.assertEqual(invocation.classify(model_id, "opus"), ("opus", True), model_id)

    def test_the_provider_prefixed_form_classifies_the_same_way(self):
        self.assertEqual(
            invocation.classify("openrouter/qwen/qwen3.8-flash", "opus"), ("opus", True))
        self.assertEqual(
            invocation.classify("openrouter/deepseek/deepseek-v4.1-flash", "opus"),
            ("opus", True))

    def test_anything_else_is_unknown_with_floor_met_null(self):
        for model_id in ("google/gemini-3.8-flash", "qwen/qwen3.8-max",
                         "deepseek/deepseek-v4-pro-0813", "anthropic/claude-fable-5-1"):
            self.assertEqual(invocation.classify(model_id, "opus"),
                             ("unknown", None), model_id)

    def test_an_absent_model_id_is_unknown_with_floor_met_null(self):
        self.assertEqual(invocation.classify(None, "opus"), ("unknown", None))
        self.assertEqual(invocation.classify("", "opus"), ("unknown", None))

    def test_a_lower_floor_is_met_and_an_unknown_floor_yields_null(self):
        self.assertEqual(invocation.classify("qwen/qwen3.8-flash", "sonnet"), ("opus", True))
        self.assertEqual(invocation.classify("qwen/qwen3.8-flash", "haiku"), ("opus", True))
        self.assertEqual(invocation.classify("qwen/qwen3.8-flash", "not-a-class"),
                         ("opus", None))

    def test_the_map_is_the_one_the_ruling_names_and_nothing_else(self):
        self.assertEqual(sorted(invocation.FLOOR_MAP),
                         ["deepseek/deepseek-v4.1-flash", "qwen/qwen3.8-flash"])
        self.assertEqual(set(invocation.FLOOR_MAP.values()), {"opus"})


class CannedVerifier(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.canned = os.path.join(self.root, "canned")
        os.makedirs(self.canned)
        self.brief = os.path.join(self.root, "checklist.md")
        with open(self.brief, "w", encoding="utf-8") as handle:
            handle.write("the mandate and the items\n")
        self.scratch = os.path.join(self.root, "run", "verifier")
        self.raw = os.path.join(self.scratch, "raw.md")
        self.setup = testlib.make_setup(self.root, testlib.load_record())
        self.session_id = testlib.load_record()["session"]["id"]

    def tearDown(self):
        testlib.cleanup(self.root)

    def write(self, name, text):
        with open(os.path.join(self.canned, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def call(self, extra=None, env=None):
        environment = {"RECHECK_ADAPTER_TEST": "1", "RECHECK_ADAPTER_CANNED": self.canned}
        if env is not None:
            environment = env
        args = ["--brief", self.brief, "--workspace", self.root, "--scratch", self.scratch,
                "--raw", self.raw, "--setup", self.setup, "--call-id", "run-verify"]
        return testlib.run("verifier.py", args + (extra or []), env=environment)

    def test_ok_retains_the_report_and_reads_the_model_from_the_record(self):
        self.write("raw.md", "prose\n\n```json\n{\"recheck_verifier_report\": 1}\n```\n")
        self.write("rc.txt", "0\n")
        self.write("trace.json",
                   json.dumps({"type": "step_start", "sessionID": self.session_id,
                               "part": {"type": "step-start"}}) + "\n")
        code, out, _err = self.call()
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["status"], "ok")
        self.assertEqual(document["raw"], self.raw)
        self.assertEqual(document["kind"], "opencode-session")
        # the model is the one the session record names, never the flag
        self.assertEqual(document["model"], "openrouter/qwen/qwen3.8-flash")
        self.assertTrue(os.path.isfile(self.raw))
        with open(self.raw, encoding="utf-8") as handle:
            self.assertIn("recheck_verifier_report", handle.read())

    def test_a_model_flag_does_not_override_the_record(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.write("trace.json",
                   json.dumps({"type": "step_start", "sessionID": self.session_id,
                               "part": {"type": "step-start"}}) + "\n")
        code, out, _err = self.call(extra=["--model", "deepseek"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["model"], "openrouter/qwen/qwen3.8-flash")

    def test_exit_zero_with_no_report_is_empty(self):
        self.write("rc.txt", "0\n")
        self.write("trace.json", "")
        code, out, _err = self.call()
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["status"], "empty")
        self.assertIsNone(document["raw"])
        self.assertIn("no text in its final message", document["note"])
        self.assertFalse(os.path.isfile(self.raw))

    def test_a_non_zero_exit_is_transport_failed_with_the_stderr_tail_as_the_note(self):
        self.write("rc.txt", "1\n")
        self.write("stderr.txt", "opencode: the provider returned an error\n")
        self.write("trace.json", "")
        code, out, _err = self.call()
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["status"], "transport-failed")
        self.assertIn("exited 1", document["note"])
        self.assertIn("the provider returned an error", document["note"])

    def test_the_timeout_exit_is_timed_out(self):
        self.write("rc.txt", "124\n")
        self.write("trace.json", "")
        code, out, _err = self.call()
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(document["status"], "timed-out")
        self.assertIn("timeout", document["note"])

    def test_a_deterministic_refusal_is_named_from_the_stderr(self):
        for message, status in (("error: unknown model qwen/nope\n", "unknown-model"),
                                ("401 unauthorized\n", "unauthorized"),
                                ("unknown agent recheck-verifier\n", "lane-unavailable")):
            self.write("rc.txt", "1\n")
            self.write("stderr.txt", message)
            self.write("trace.json", "")
            code, out, _err = self.call()
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], status, message)

    def test_a_denied_tool_in_the_trace_becomes_a_refused_line(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.write("trace.json", "\n".join([
            json.dumps({"type": "tool", "sessionID": self.session_id,
                        "part": {"type": "tool", "tool": "webfetch",
                                 "state": {"status": "error", "error": "permission denied"}}}),
            json.dumps({"type": "tool", "sessionID": self.session_id,
                        "part": {"type": "tool", "tool": "unknown",
                                 "state": {"status": "error", "error": "Tool execution aborted",
                                           "metadata": {"interrupted": True}}}}),
            json.dumps({"type": "tool", "sessionID": self.session_id,
                        "part": {"type": "tool", "tool": "bash",
                                 "state": {"status": "completed"}}}),
        ]) + "\n")
        code, out, _err = self.call()
        self.assertEqual(code, 0)
        refused = json.loads(out)["refused"]
        self.assertEqual(len(refused), 1)
        self.assertIn("webfetch", refused[0])
        self.assertIn("no side effect", refused[0])

    def test_the_injected_list_names_the_instruction_files_that_exist(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.write("trace.json", "")
        code, out, _err = self.call()
        injected = json.loads(out)["injected"]
        self.assertEqual(injected,
                         ["opencode system prompt (the harness's own, for the configured agent)"])
        with open(os.path.join(self.root, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("repo instructions\n")
        with open(os.path.join(self.setup, "xdg-config", "opencode", "AGENTS.md"),
                  "w", encoding="utf-8") as handle:
            handle.write("global instructions\n")
        code, out, _err = self.call()
        injected = json.loads(out)["injected"]
        self.assertEqual(len(injected), 3)
        self.assertTrue(injected[1].endswith("xdg-config/opencode/AGENTS.md"))
        self.assertTrue(injected[2].endswith(os.path.join(self.root, "AGENTS.md")))

    def test_the_canned_hook_is_refused_outside_a_test(self):
        self.write("raw.md", "prose\n")
        code, out, err = self.call(env={"RECHECK_ADAPTER_CANNED": self.canned})
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("canned response outside test", err)


if __name__ == "__main__":
    unittest.main()
