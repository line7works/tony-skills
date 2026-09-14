"""The floor map (E9-3) and `verifier.py` (E9 section 9.1, ruling E9-32).

The floor map is exercised through `invocation.py`'s own classifier, every class the ruling
names for this lane included and the null case. `verifier.py` is exercised through its test
hook: `RECHECK_ADAPTER_TEST=1` with `RECHECK_ADAPTER_CANNED=<dir>` replaces the launch with
saved files, and the hook set without the test flag is refused.

What these tests hold the helper to, in the reviewer's own terms:

* finding 3 — there is no `--model` and no `--agent`; the model is the bound driving session's
  own, read from the harness's record, and an `ok` needs the child's actual model row;
* finding 4 — the brief must be `<run_dir>/checklist.md`, the scratch `<run_dir>/verifier`,
  every capture inside it after symlinks, the call id a call id, and no destination is ever
  overwritten; each of those is exit 2 with nothing created;
* finding 5 — a refusal is the harness's own recorded permission outcome (a denied `bash`
  counts), and any other tool error is reported with an **unknown** side effect;
* finding 13 — an absent binary is exit 3, not a status.
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

DENIED = "The user rejected permission to use this specific tool call."


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
        # the run directory shape the contract fixes: <run_dir>/checklist.md, <run_dir>/verifier
        self.run_dir = os.path.join(self.root, "recheck-a-20260920-0001")
        os.makedirs(self.run_dir)
        self.brief = os.path.join(self.run_dir, "checklist.md")
        with open(self.brief, "w", encoding="utf-8") as handle:
            handle.write("the mandate and the items\n")
        self.scratch = os.path.join(self.run_dir, "verifier")
        self.raw = os.path.join(self.scratch, "raw.md")
        self.setup = testlib.make_setup(self.root, testlib.load_record(), binary=True)
        self.session_id = testlib.load_record()["session"]["id"]

    def tearDown(self):
        testlib.cleanup(self.root)

    def write(self, name, text):
        with open(os.path.join(self.canned, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def trace(self, *events):
        self.write("trace.json", "\n".join(json.dumps(e) for e in events) + "\n")

    def call(self, extra=None, env=None, raw=None, scratch=None, brief=None, call_id="run-verify"):
        environment = {"RECHECK_ADAPTER_TEST": "1", "RECHECK_ADAPTER_CANNED": self.canned}
        if env is not None:
            environment = env
        args = ["--brief", brief or self.brief, "--workspace", self.root,
                "--scratch", scratch or self.scratch, "--raw", raw or self.raw,
                "--setup", self.setup, "--call-id", call_id,
                "--session", self.session_id]
        return testlib.run("verifier.py", args + (extra or []), env=environment)

    # ---- finding 3: no model or agent choice, and the model is a fact -------------------

    def test_a_model_flag_is_refused(self):
        code, out, err = self.call(extra=["--model", "deepseek"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("not an argument of this helper", err)
        self.assertIn("E9-32", err)

    def test_an_agent_flag_is_refused(self):
        code, out, err = self.call(extra=["--agent", "build"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("not an argument of this helper", err)

    def test_ok_retains_the_report_and_reads_the_model_from_the_record(self):
        self.write("raw.md", "prose\n\n```json\n{\"recheck_verifier_report\": 1}\n```\n")
        self.write("rc.txt", "0\n")
        self.trace({"type": "step_start", "sessionID": self.session_id,
                    "part": {"type": "step-start"}})
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["status"], "ok")
        self.assertEqual(document["raw"], self.raw)
        self.assertEqual(document["kind"], "opencode-session")
        self.assertEqual(document["model"], "openrouter/qwen/qwen3.8-flash")
        self.assertIn("the bound driving session", err)
        self.assertTrue(os.path.isfile(self.raw))
        with open(self.raw, encoding="utf-8") as handle:
            self.assertIn("recheck_verifier_report", handle.read())

    def test_without_the_childs_model_row_an_ok_becomes_lane_unavailable(self):
        """Finding 3: a requested model never becomes reported fact without a record."""
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace({"type": "step_start", "sessionID": "ses_no_record",
                    "part": {"type": "step-start"}})
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["status"], "lane-unavailable")
        self.assertIsNone(document["raw"])
        self.assertIn("ses_no_record", document["note"])
        self.assertIn("no model record", document["note"])
        self.assertFalse(os.path.isfile(self.raw))

    def test_a_driving_session_with_no_model_record_stops_the_helper(self):
        testlib.add_session(self.setup, "ses_modelless", self.root, "msg_m", "words",
                            model={})
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace({"type": "step_start", "sessionID": self.session_id})
        args = ["--brief", self.brief, "--workspace", self.root, "--scratch", self.scratch,
                "--raw", self.raw, "--setup", self.setup, "--call-id", "run-verify",
                "--session", "ses_modelless"]
        code, out, err = testlib.run(
            "verifier.py", args,
            env={"RECHECK_ADAPTER_TEST": "1", "RECHECK_ADAPTER_CANNED": self.canned})
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("carries no model id", err)
        self.assertIn("never defaulted", err)

    # ---- finding 4: the path rules, before anything is created --------------------------

    def assert_nothing_created(self):
        self.assertFalse(os.path.isdir(self.scratch))
        self.assertFalse(os.path.isfile(self.raw))

    def test_a_brief_that_is_not_the_runs_checklist_is_refused(self):
        outside = os.path.join(self.root, "outside-brief.md")
        with open(outside, "w", encoding="utf-8") as handle:
            handle.write("someone else's mandate\n")
        code, out, err = self.call(brief=outside)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("must be the core's own brief", err)
        self.assert_nothing_created()

    def test_a_scratch_that_is_not_the_runs_verifier_directory_is_refused(self):
        code, out, err = self.call(scratch=os.path.join(self.run_dir, "elsewhere"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("must be <run_dir>/verifier", err)
        self.assert_nothing_created()

    def test_a_raw_path_outside_the_scratch_is_refused(self):
        code, out, err = self.call(raw=os.path.join(self.run_dir, "input.json"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("resolves outside the scratch directory", err)
        self.assert_nothing_created()

    def test_a_raw_path_that_escapes_through_a_symlink_is_refused(self):
        os.makedirs(self.scratch)
        os.symlink(self.run_dir, os.path.join(self.scratch, "out"))
        code, out, err = self.call(raw=os.path.join(self.scratch, "out", "input.json"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("resolves outside the scratch directory", err)

    def test_an_existing_destination_is_never_overwritten(self):
        os.makedirs(self.scratch)
        with open(self.raw, "w", encoding="utf-8") as handle:
            handle.write("the first call's retained report\n")
        code, out, err = self.call()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("already exists", err)
        with open(self.raw, encoding="utf-8") as handle:
            self.assertIn("the first call's retained report", handle.read())

    def test_an_existing_trace_is_never_overwritten(self):
        os.makedirs(self.scratch)
        with open(os.path.join(self.scratch, "launch-run-verify.json"), "w") as handle:
            handle.write("the first call's trace\n")
        code, out, err = self.call()
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)

    def test_a_call_id_that_is_not_a_call_id_is_refused(self):
        for bad in ("../escape", "call id", ""):
            code, out, err = self.call(call_id=bad)
            self.assertEqual(code, 2, bad)
            self.assertEqual(out, "")
            self.assertIn("is not a call id", err)
        self.assert_nothing_created()

    # ---- finding 5: refusals from the recorded permission outcome -----------------------

    def test_a_denied_bash_is_a_refusal(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace(
            {"type": "tool", "sessionID": self.session_id,
             "part": {"type": "tool", "tool": "bash",
                      "state": {"status": "error", "error": DENIED,
                                "input": {"command": "curl https://example.invalid/x"}}}},
        )
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        refused = json.loads(out)["refused"]
        self.assertEqual(len(refused), 1, refused)
        self.assertIn("bash", refused[0])
        self.assertIn("no side effect", refused[0])
        self.assertIn("curl https://example.invalid/x", refused[0])

    def test_a_denied_webfetch_is_a_refusal_and_a_completed_one_is_not(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace(
            {"type": "tool", "sessionID": self.session_id,
             "part": {"type": "tool", "tool": "webfetch",
                      "state": {"status": "error", "error": DENIED,
                                "input": {"url": "https://example.invalid/x"}}}},
            {"type": "tool", "sessionID": self.session_id,
             "part": {"type": "tool", "tool": "read",
                      "state": {"status": "completed"}}},
        )
        code, out, _err = self.call()
        refused = json.loads(out)["refused"]
        self.assertEqual(len(refused), 1)
        self.assertIn("webfetch", refused[0])

    def test_an_error_after_a_completed_request_is_never_no_side_effect(self):
        """Finding 5: 'response parsing failed' is not proof the request never happened."""
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace(
            {"type": "tool", "sessionID": self.session_id,
             "part": {"type": "tool", "tool": "webfetch",
                      "state": {"status": "error",
                                "error": "failed to parse the response after the request completed",
                                "input": {"url": "https://example.invalid/x"}}}},
        )
        code, out, _err = self.call()
        document = json.loads(out)
        self.assertEqual(document["refused"], [])
        self.assertIn("unknown side effect", document["note"])
        self.assertNotIn("no side effect", document["note"])

    def test_an_aborted_call_is_neither_a_refusal_nor_an_error(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace(
            {"type": "tool", "sessionID": self.session_id,
             "part": {"type": "tool", "tool": "unknown",
                      "state": {"status": "error", "error": "Tool execution aborted",
                                "metadata": {"interrupted": True}}}},
        )
        code, out, _err = self.call()
        document = json.loads(out)
        self.assertEqual(document["refused"], [])
        self.assertIn("aborted tool call", document["note"])

    # ---- the status vocabulary ----------------------------------------------------------

    def test_exit_zero_with_no_report_is_empty(self):
        self.write("rc.txt", "0\n")
        self.write("trace.json", "")
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["status"], "empty")
        self.assertIsNone(document["raw"])
        self.assertIn("no text in its final message", document["note"])
        self.assertFalse(os.path.isfile(self.raw))

    def test_a_non_zero_exit_is_transport_failed_with_the_stderr_tail_as_the_note(self):
        self.write("rc.txt", "1\n")
        self.write("stderr.txt", "opencode: the provider returned an error\n")
        self.write("trace.json", "")
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["status"], "transport-failed")
        self.assertIn("exited 1", document["note"])
        self.assertIn("the provider returned an error", document["note"])

    def test_the_timeout_exit_is_timed_out(self):
        self.write("rc.txt", "124\n")
        self.write("trace.json", "")
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["status"], "timed-out")
        self.assertIn("timeout", document["note"])

    def test_a_deterministic_refusal_is_named_from_the_stderr(self):
        for message, status in (("error: unknown model qwen/nope\n", "unknown-model"),
                                ("401 unauthorized\n", "unauthorized"),
                                ("unknown agent recheck-verifier\n", "lane-unavailable")):
            self.setUp()
            self.write("rc.txt", "1\n")
            self.write("stderr.txt", message)
            self.write("trace.json", "")
            code, out, err = self.call()
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["status"], status, message)

    def test_the_injected_list_names_the_instruction_files_that_exist(self):
        self.write("raw.md", "prose\n")
        self.write("rc.txt", "0\n")
        self.trace({"type": "step_start", "sessionID": self.session_id})
        code, out, err = self.call()
        self.assertEqual(code, 0, err)
        injected = json.loads(out)["injected"]
        self.assertEqual(injected,
                         ["opencode system prompt (the harness's own, for the configured agent)"])
        with open(os.path.join(self.root, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("repo instructions\n")
        with open(os.path.join(self.setup, "xdg-config", "opencode", "AGENTS.md"),
                  "w", encoding="utf-8") as handle:
            handle.write("global instructions\n")
        code, out, err = self.call(call_id="run-verify-2",
                                   raw=os.path.join(self.scratch, "raw-2.md"))
        self.assertEqual(code, 0, err)
        injected = json.loads(out)["injected"]
        self.assertEqual(len(injected), 3)
        self.assertTrue(injected[1].endswith("xdg-config/opencode/AGENTS.md"))
        self.assertTrue(injected[2].endswith(os.path.join(self.root, "AGENTS.md")))

    def test_the_canned_hook_is_refused_outside_a_test(self):
        self.write("raw.md", "prose\n")
        args = ["--brief", self.brief, "--workspace", self.root, "--scratch", self.scratch,
                "--raw", self.raw, "--setup", self.setup, "--call-id", "run-verify"]
        code, out, err = testlib.run(
            "verifier.py", args, env={"RECHECK_ADAPTER_CANNED": self.canned})
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("canned response outside test", err)


if __name__ == "__main__":
    unittest.main()
