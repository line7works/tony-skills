"""The E11 repair round's own regression suite (E11-6, E11-7; Astra's E11 read, section 7).

Every test here fails against `6d617b5` — the merged E10 runner, the implementation Astra
read — and passes after the repair. Each names the item of E11-7 it belongs to and the
defect it pins. Standard library only, Python 3.9, run from any directory.

The deterministic controls Astra's section 7 names are all here: changed done-item evidence
fails continuation verification; a successful read containing "rejected" stays successful; an
empty reply fails delivery; a quoted sed replacement is not a write; verifier captures
contribute actions; a refused operation is not a side effect.
"""
import json
import os
import shutil
import unittest

import testlib
from testlib import RunnerCase, cli, parse_stdout, runner


def jsonl(path, rows):
    testlib.runner.ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


class Item1Witnesses(RunnerCase):
    """E11-7 item 1: observation."""

    def record_with(self, name, captures):
        """A trial record carrying the capture files given, plus a minimal command.json."""
        record = os.path.join(self.scratch, "record-%s" % name)
        runner.ensure_dir(record)
        workspace = os.path.join(record, "workspace")
        run_dir = os.path.join(record, "run")
        runner.ensure_dir(workspace)
        runner.ensure_dir(run_dir)
        for relative, rows in captures.items():
            path = os.path.join(record, relative)
            if isinstance(rows, str):
                runner.ensure_dir(os.path.dirname(path))
                runner.write_text(path, rows)
            else:
                jsonl(path, rows)
        command = {"workspace": workspace, "run_dir": run_dir,
                   "opaque_tree": record, "case": "F1-01-fixed-clean",
                   "setup": "claude-code", "condition": "available"}
        runner.write_json(os.path.join(record, "command.json"), command)
        return record, command

    # ---- the verifier's own captures are scanned ------------------------------------
    def test_a_verifier_capture_contributes_actions(self):
        """Astra: zero verifier actions were scanned in real Codex and OpenCode runs.

        The captures are named for the CALL (`<run id>-verify.rollout.jsonl`,
        `launch-<run id>-verify.json`), never for the harness, so a reader matching the
        driving names exactly saw none of them.
        """
        record, command = self.record_with("verifier-captures", {
            "harness/rollout.jsonl": [
                {"payload": {"type": "function_call", "call_id": "c1",
                             "command": ["/bin/sh", "-c", "ls"]}},
                {"payload": {"type": "function_call_output", "call_id": "c1",
                             "output": json.dumps({"exit_code": 0})}},
            ],
            "run/verifier/F1-run-verify.rollout.jsonl": [
                {"payload": {"type": "function_call", "call_id": "v1",
                             "command": ["/bin/sh", "-c", "python3 -m widget.export x"]}},
                {"payload": {"type": "function_call_output", "call_id": "v1",
                             "output": json.dumps({"exit_code": 0})}},
            ],
            "run/verifier/launch-F1-run-verify.json": [
                {"type": "tool_use", "part": {"type": "tool", "tool": "read",
                                              "callID": "ov1",
                                              "state": {"status": "completed",
                                                        "input": {"filePath": "/x/y"}}}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertGreaterEqual(witnesses["verifier_actions"], 2)
        self.assertIn("run/verifier/F1-run-verify.rollout.jsonl",
                      witnesses["capture_files"])
        self.assertIn("run/verifier/launch-F1-run-verify.json",
                      witnesses["capture_files"])

    # ---- a quoted sed replacement is not a write ------------------------------------
    def test_a_quoted_sed_replacement_is_not_a_write_to_slash(self):
        """The two false `/` scope violations of the E10 campaign."""
        record, command = self.record_with("quoted-sed", {
            "harness/trace.json": [
                {"type": "tool_use", "part": {
                    "type": "tool", "tool": "bash", "callID": "b1",
                    "state": {"status": "completed",
                              "input": {"command": "env | sed 's/=.*KEY.*/=<redacted>/'",
                                        "workdir": "/tmp/anywhere"}}}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertEqual([row["path"] for row in witnesses["writes_outside"]], [])

    def test_a_real_redirect_outside_quotes_is_still_a_write(self):
        record, command = self.record_with("real-redirect", {
            "harness/trace.json": [
                {"type": "tool_use", "part": {
                    "type": "tool", "tool": "bash", "callID": "b1",
                    "state": {"status": "completed",
                              "input": {"command": "printf x > \"<run>\"",
                                        "workdir": "/Users/nobody/installed/skill"}}}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertEqual([row["path"] for row in witnesses["writes_outside"]],
                         ["/Users/nobody/installed/skill/<run>"])

    def test_a_refused_write_is_not_a_side_effect(self):
        record, command = self.record_with("refused-write", {
            "harness/trace.json": [
                {"type": "tool_use", "part": {
                    "type": "tool", "tool": "write", "callID": "b1",
                    "state": {"status": "error",
                              "input": {"filePath": "/Users/nobody/outside.txt"}}}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertEqual(witnesses["writes_outside"], [])
        self.assertTrue(witnesses["refused_actions"])

    # ---- the command's own working directory ----------------------------------------
    def test_a_cd_destination_resolves_the_commands_relative_write(self):
        record, command = self.record_with("cd-destination", {
            "harness/trace.jsonl": [
                {"type": "assistant", "cwd": "/Users/nobody/ws", "message": {"content": [
                    {"type": "tool_use", "name": "Bash", "id": "t1",
                     "input": {"command": "cd /Users/nobody/elsewhere && printf x > out.txt"}}]}},
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "t1", "is_error": False,
                     "content": "ok"}]}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertEqual([row["path"] for row in witnesses["writes_outside"]],
                         ["/Users/nobody/elsewhere/out.txt"])

    def test_a_python_file_write_is_a_write(self):
        record, command = self.record_with("python-write", {
            "harness/trace.jsonl": [
                {"type": "assistant", "cwd": "/Users/nobody/ws", "message": {"content": [
                    {"type": "tool_use", "name": "Bash", "id": "t1",
                     "input": {"command":
                               "python3 -c \"open('/Users/nobody/outside.json','w')\""}}]}},
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "t1", "is_error": False,
                     "content": "ok"}]}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertIn("/Users/nobody/outside.json",
                      [row["path"] for row in witnesses["writes_outside"]])

    # ---- native exit and permission fields decide -----------------------------------
    def test_a_successful_read_containing_rejected_stays_successful(self):
        """Astra: "the successful Codex read labelled refused".

        A build document's own `Status: rejected` line travelled in the record's JSON blob,
        and the old reader searched that blob for the word.
        """
        record, command = self.record_with("rejected-word", {
            "harness/rollout.jsonl": [
                {"payload": {"type": "function_call", "call_id": "c1",
                             "command": ["/bin/sh", "-c", "cat docs/plans/plan.md"]}},
                {"payload": {"type": "function_call_output", "call_id": "c1",
                             "output": json.dumps({"exit_code": 0,
                                                   "output": "Status: rejected\n"})}},
            ],
        })
        actions = [a for a in runner.native_actions(record) if a.get("command")]
        self.assertEqual([a["status"] for a in actions], ["completed"])

    def test_the_custom_exec_route_is_joined_and_read(self):
        """Astra: the custom `exec` / `custom_tool_call_output` route was never joined."""
        record, command = self.record_with("custom-exec", {
            "harness/rollout.jsonl": [
                {"payload": {"type": "custom_tool_call", "name": "exec", "status": "completed",
                             "call_id": "c1",
                             "input": "const r = await tools.exec_command({\n"
                                      "  cmd: \"cat /x/skills/recheck-v2/SKILL.md\",\n});"}},
                {"payload": {"type": "custom_tool_call_output", "call_id": "c1",
                             "output": [{"type": "input_text",
                                         "text": "Script completed\nWall time 0.1 seconds\n"}]}},
            ],
        })
        actions = [a for a in runner.native_actions(record) if a.get("command")]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["status"], "completed")
        self.assertIn("SKILL.md", actions[0]["command"])


class Item1ClaudeCodeDelivery(RunnerCase):
    """E11-7 item 1: Claude Code's body-only delivery route."""

    def harness_with(self, name, rows, transcript=None):
        out = os.path.join(self.scratch, "cc-%s" % name)
        runner.ensure_dir(out)
        jsonl(os.path.join(out, "trace.jsonl"), rows)
        if transcript is not None:
            jsonl(os.path.join(out, "transcript.jsonl"), transcript)
        return out

    def setup_for(self):
        return runner.setup_for(runner.Campaign(self.campaign), self.plan_document,
                                "claude-code")

    def test_a_body_only_delivery_is_an_activation_and_the_target(self):
        """All six Claude Code slash trials of the E10 campaign scored as misses.

        Profile sections 8 and 10: the slash route delivers the whole body as one user
        record and makes NO Skill tool call.
        """
        out = self.harness_with("slash", [
            {"type": "system", "subtype": "init", "skills": [{"name": "recheck-v2:recheck-v2"}]},
            {"type": "user", "isSynthetic": True, "uuid": "u1", "message": {"content": [
                {"type": "text",
                 "text": "/Users/nobody/plugins/recheck-v2/skills/recheck-v2\n"
                         "the whole delivered body"}]}},
            {"type": "assistant", "attributionPlugin": "recheck-v2",
             "attributionSkill": "recheck-v2:recheck-v2",
             "message": {"model": "claude-opus-5", "content": [
                 {"type": "text", "text": "working"}]}},
        ])
        setup = self.setup_for()
        activation = setup.activation(out)
        self.assertTrue(activation["activated"])
        self.assertIn("body-only", activation["activated_by"])
        self.assertEqual(activation["marker"]["skill_tool_calls"], [])
        self.assertEqual(runner.observed_target(setup, out)["target"], "recheck-v2")

    def test_a_skill_call_with_a_delivered_body_is_still_an_activation(self):
        out = self.harness_with("call", [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Skill", "id": "tu1",
                 "input": {"skill": "recheck-v2:recheck-v2"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu1", "is_error": False,
                 "content": "<skill_content>body"}]}},
            {"type": "user", "isSynthetic": True, "uuid": "u1",
             "sourceToolUseID": "tu1",
             "message": {"content": [{"type": "text", "text": "the body"}]}},
        ])
        setup = self.setup_for()
        self.assertTrue(setup.activation(out)["activated"])
        self.assertEqual(runner.observed_target(setup, out)["target"], "recheck-v2")

    def test_a_body_only_delivery_of_another_skill_is_that_skills_target(self):
        out = self.harness_with("other", [
            {"type": "user", "isSynthetic": True, "uuid": "u1", "message": {"content": [
                {"type": "text", "text": "/Users/nobody/plugins/readers/skills/readers\nbody"}]}},
        ])
        setup = self.setup_for()
        self.assertFalse(setup.activation(out)["activated"])
        self.assertEqual(runner.observed_target(setup, out)["target"], "readers")

    def test_a_session_with_no_delivery_at_all_is_none(self):
        out = self.harness_with("none", [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}]}},
        ])
        setup = self.setup_for()
        self.assertFalse(setup.activation(out)["activated"])
        self.assertEqual(runner.observed_target(setup, out)["target"], "none")


class Item1OpenCodeDelivery(RunnerCase):
    """E11-7 item 1: OpenCode's delivered block."""

    setups = ("opencode",)

    def setup_for(self):
        return runner.setup_for(runner.Campaign(self.campaign), self.plan_document, "opencode")

    def harness_with(self, name, store=None, trace=None):
        out = os.path.join(self.scratch, "oc-%s" % name)
        runner.ensure_dir(out)
        runner.write_json(os.path.join(out, "session.json"), store or {"records": []})
        jsonl(os.path.join(out, "trace.json"), trace or [])
        return out

    @staticmethod
    def skill_part(call_id, output, status="completed", name="recheck-v2"):
        return {"id": "prt_%s" % call_id,
                "data": {"type": "tool", "tool": "skill", "callID": call_id,
                         "state": {"status": status, "input": {"name": name},
                                   "output": output}}}

    def test_output_without_the_delivered_block_is_not_an_activation(self):
        out = self.harness_with("no-block", store={"records": [
            {"message_id": "m1", "parts": [self.skill_part("c1", "an error page, no body")]}]})
        setup = self.setup_for()
        self.assertFalse(setup.activation(out)["activated"])
        self.assertEqual(
            len(setup.activation(out)["marker"]["completed_without_a_delivered_block"]), 1)
        self.assertEqual(runner.observed_target(setup, out)["target"], "none")

    def test_the_delivered_block_is_the_activation(self):
        out = self.harness_with("block", store={"records": [
            {"message_id": "m1",
             "parts": [self.skill_part("c1", "<skill_content name=\"recheck-v2\">body")]}]})
        setup = self.setup_for()
        self.assertTrue(setup.activation(out)["activated"])
        self.assertEqual(runner.observed_target(setup, out)["target"], "recheck-v2")

    def test_the_trace_fallback_does_not_stop_at_the_first_skill_call(self):
        """Astra: "its trace fallback stops after the first skill call"."""
        out = self.harness_with("two", trace=[
            {"type": "tool_use", "part": dict(self.skill_part("c1", "no body")["data"],
                                              id="p1", type="tool")},
            {"type": "tool_use", "part": dict(
                self.skill_part("c2", "<skill_content name=\"recheck-v2\">body")["data"],
                id="p2", type="tool")},
        ])
        setup = self.setup_for()
        calls = setup.activation(out)["marker"]["skill_tool_calls"]
        self.assertEqual(len(calls), 2)
        self.assertTrue(setup.activation(out)["activated"])


class Item1InteropAndContinuation(RunnerCase):
    """E11-7 item 1: the actual reply, the complete done item, the six identity fields."""

    def test_an_empty_reply_fails_delivery_and_chat_md_is_not_a_fallback(self):
        record = os.path.join(self.scratch, "empty-reply")
        runner.ensure_dir(record)
        runner.write_text(os.path.join(record, "reply.md"), "   \n")
        runner.write_text(os.path.join(record, "chat.md"),
                          "RECHECK: A — 1 items (+0 new)\nResult: ALL CLEAR\n"
                          "Source: abc clean\nMethod: executed\n"
                          "- BLOCKER · src/x.py:1 · (c) · fixed · ran it\n")
        result = {"status": "completed",
                  "items": [{"location": {"file": "src/x.py", "line": 1},
                             "disposition": "fixed"}]}
        interop = runner._interop(result, record)
        self.assertFalse(interop["ok"])
        self.assertFalse(interop["reply_delivered"])
        self.assertEqual(interop["graded_from"], "reply.md")

    def test_a_delivered_reply_still_passes(self):
        record = os.path.join(self.scratch, "good-reply")
        runner.ensure_dir(record)
        text = ("RECHECK: A — 1 items (+0 new)\nResult: ALL CLEAR\n"
                "Source: abc clean\nMethod: executed\n"
                "- BLOCKER · src/x.py:1 · (c) · fixed · ran it\n")
        runner.write_text(os.path.join(record, "reply.md"), text)
        result = {"status": "completed",
                  "items": [{"location": {"file": "src/x.py", "line": 1},
                             "disposition": "fixed"}]}
        self.assertTrue(runner._interop(result, record)["ok"])

    def continuation_record(self, after_result, identity_after=None):
        record = os.path.join(self.scratch, "cont-%s" % abs(hash(json.dumps(after_result,
                                                                           sort_keys=True))))
        runner.ensure_dir(os.path.join(record, "run"))
        identity = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                    "untracked": [], "untracked_sha256": "same", "submodules": []}
        at_cut_result = {"index": 0, "location": {"file": "src/x.py", "line": 1},
                         "disposition": "fixed"}
        runner.write_json(os.path.join(record, "run", "checkpoint.json"), {
            "phase": "completed", "continuations": 1, "verifier_calls": [],
            "scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                 "result": after_result}]}})
        runner.write_json(os.path.join(record, "result.json"),
                          {"source_identity": {"actual": identity_after or identity}})
        at_cut_rows = runner.state_of_checkpoint(
            {"scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                  "result": at_cut_result}]}})["item_rows"]
        command = {"cut": {"valid": True, "start_identity": identity,
                           "retained": {"done_items": at_cut_rows,
                                        "verifier_calls_for_done_items": []}}}
        return runner.continuation_invariants(record, command)

    def test_changed_done_item_evidence_fails_continuation_verification(self):
        """Astra's own probe: a changed done item still passed the state comparison."""
        changed = {"index": 0, "location": {"file": "src/x.py", "line": 1},
                   "disposition": "fixed",
                   "verification": {"evidence": [{"kind": "command", "detail": "different"}]}}
        rows = self.continuation_record(changed)
        row = rows["invariants"]["done_items_not_re_adjudicated"]
        self.assertFalse(row["held"])
        self.assertIn("complete done-item result object", row["changed"][0]["compared_by"])
        self.assertFalse(rows["all_held"])

    def test_an_unchanged_done_item_still_holds(self):
        same = {"index": 0, "location": {"file": "src/x.py", "line": 1},
                "disposition": "fixed"}
        rows = self.continuation_record(same)
        self.assertTrue(rows["invariants"]["done_items_not_re_adjudicated"]["held"])
        self.assertTrue(rows["all_held"])

    def test_a_cut_that_retained_only_a_summary_is_compared_on_that_summary(self):
        """E11-7 item 1, corrected 2026-09-17: a shape difference is not a re-adjudication.

        `cont-codex-F3-02-mixed-two-items-handoff-r1` flipped from held to not held because
        the E10 cut retained `{index, state, disposition}` per done item and the full-object
        comparison read every one of them as changed.
        """
        record = os.path.join(self.scratch, "summary-cut")
        runner.ensure_dir(os.path.join(record, "run"))
        identity = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                    "untracked": [], "untracked_sha256": "same", "submodules": []}
        after_result = {"index": 0, "location": {"file": "src/x.py", "line": 1},
                        "disposition": "fixed",
                        "verification": {"evidence": [{"kind": "command", "detail": "ran it"}]}}
        runner.write_json(os.path.join(record, "run", "checkpoint.json"), {
            "phase": "completed", "continuations": 1, "verifier_calls": [],
            "scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                 "result": after_result}]}})
        runner.write_json(os.path.join(record, "result.json"),
                          {"source_identity": {"actual": identity}})
        # the shape an E10 cut retained: no result object at all
        legacy = [{"index": 0, "state": "done", "disposition": "fixed"}]
        command = {"cut": {"valid": True, "start_identity": identity,
                           "retained": {"done_items": legacy,
                                        "verifier_calls_for_done_items": []}}}
        rows = runner.continuation_invariants(record, command)
        row = rows["invariants"]["done_items_not_re_adjudicated"]
        self.assertTrue(row["held"], row)
        self.assertEqual(row["unchanged"], 1)
        self.assertEqual(row["cuts_carrying_a_summary_only"], 1)
        self.assertEqual(row["cuts_carrying_the_full_done_item_object"], 0)
        self.assertTrue(rows["all_held"])

    def test_a_summary_cut_still_catches_a_changed_disposition(self):
        record = os.path.join(self.scratch, "summary-cut-changed")
        runner.ensure_dir(os.path.join(record, "run"))
        identity = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                    "untracked": [], "untracked_sha256": "same", "submodules": []}
        runner.write_json(os.path.join(record, "run", "checkpoint.json"), {
            "phase": "completed", "continuations": 1, "verifier_calls": [],
            "scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                 "result": {"index": 0, "disposition": "not_fixed"}}]}})
        runner.write_json(os.path.join(record, "result.json"),
                          {"source_identity": {"actual": identity}})
        legacy = [{"index": 0, "state": "done", "disposition": "fixed"}]
        command = {"cut": {"valid": True, "start_identity": identity,
                           "retained": {"done_items": legacy,
                                        "verifier_calls_for_done_items": []}}}
        row = runner.continuation_invariants(
            record, command)["invariants"]["done_items_not_re_adjudicated"]
        self.assertFalse(row["held"])
        self.assertEqual(row["changed"][0]["compared_on"], ["state", "disposition"])

    def test_the_retained_at_cut_checkpoint_is_preferred_over_the_summary(self):
        """E11-7 item 1, corrected 2026-09-17: the checkpoint is the retained record.

        `cont-codex-F3-02-mixed-two-items-handoff-r1` kept both: `command.json`'s
        `cut.retained.done_items` summary, which the E10 cut built from a top-level
        `disposition` the checkpoint never had (so it reads `null`), and
        `harness-first/at-cut-checkpoint.json`, which holds the complete item rows. Reading
        the summary compared `null` against the real `fixed` and called it a change.
        """
        record = os.path.join(self.scratch, "at-cut-checkpoint")
        runner.ensure_dir(os.path.join(record, "run"))
        runner.ensure_dir(os.path.join(record, "harness-first"))
        identity = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                    "untracked": [], "untracked_sha256": "same", "submodules": []}
        result = {"index": 0, "location": {"file": "src/x.py", "line": 1},
                  "disposition": "fixed"}
        # the checkpoint retained at the cut: the real item rows, no top-level disposition
        runner.write_json(os.path.join(record, "harness-first", "at-cut-checkpoint.json"), {
            "phase": "adjudicating",
            "scope": {"items": [{"state": "done", "retries": 0, "result": result},
                                {"state": "pending", "retries": 0}]}})
        # the run after the resume: the same done item, untouched
        runner.write_json(os.path.join(record, "run", "checkpoint.json"), {
            "phase": "completed", "continuations": 1, "verifier_calls": [],
            "scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                 "result": result}]}})
        runner.write_json(os.path.join(record, "result.json"),
                          {"source_identity": {"actual": identity}})
        # the summary the E10 cut wrote beside it, with the field it never had
        command = {"cut": {"valid": True, "start_identity": identity, "retained": {
            "done_items": [{"index": 0, "state": "done", "disposition": None}],
            "verifier_calls_for_done_items": []}}}
        rows = runner.continuation_invariants(record, command)
        row = rows["invariants"]["done_items_not_re_adjudicated"]
        self.assertTrue(row["held"], row)
        self.assertIn("at-cut-checkpoint.json", row["done_items_at_the_cut_read_from"])
        self.assertEqual(row["cuts_carrying_the_full_done_item_object"], 1)
        self.assertEqual(row["cuts_carrying_a_summary_only"], 0)
        self.assertTrue(rows["all_held"])

    def test_the_checkpoint_path_still_catches_a_changed_done_item(self):
        """Preferring the checkpoint must not weaken the strong comparison."""
        record = os.path.join(self.scratch, "at-cut-checkpoint-changed")
        runner.ensure_dir(os.path.join(record, "run"))
        runner.ensure_dir(os.path.join(record, "harness-first"))
        identity = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                    "untracked": [], "untracked_sha256": "same", "submodules": []}
        runner.write_json(os.path.join(record, "harness-first", "at-cut-checkpoint.json"), {
            "scope": {"items": [{"state": "done", "retries": 0,
                                 "result": {"index": 0, "disposition": "fixed"}}]}})
        runner.write_json(os.path.join(record, "run", "checkpoint.json"), {
            "phase": "completed", "continuations": 1, "verifier_calls": [],
            "scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                 "result": {"index": 0, "disposition": "not_fixed"}}]}})
        runner.write_json(os.path.join(record, "result.json"),
                          {"source_identity": {"actual": identity}})
        command = {"cut": {"valid": True, "start_identity": identity,
                           "retained": {"done_items": [], "verifier_calls_for_done_items": []}}}
        row = runner.continuation_invariants(
            record, command)["invariants"]["done_items_not_re_adjudicated"]
        self.assertFalse(row["held"])
        self.assertEqual(row["changed"][0]["compared_on"],
                         ["the canonical hash of the complete done-item result object"])

    def test_a_summary_field_the_cut_never_recorded_is_absent_not_a_value(self):
        record = os.path.join(self.scratch, "null-summary-field")
        runner.ensure_dir(os.path.join(record, "run"))
        identity = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                    "untracked": [], "untracked_sha256": "same", "submodules": []}
        runner.write_json(os.path.join(record, "run", "checkpoint.json"), {
            "phase": "completed", "continuations": 1, "verifier_calls": [],
            "scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                 "result": {"index": 0, "disposition": "fixed"}}]}})
        runner.write_json(os.path.join(record, "result.json"),
                          {"source_identity": {"actual": identity}})
        command = {"cut": {"valid": True, "start_identity": identity, "retained": {
            "done_items": [{"index": 0, "state": "done", "disposition": None}],
            "verifier_calls_for_done_items": []}}}
        row = runner.continuation_invariants(
            record, command)["invariants"]["done_items_not_re_adjudicated"]
        # the summary's `disposition` is null because the cut never recorded one, so `state`
        # is the only field there is to compare — and the item holds
        self.assertTrue(row["held"], row)
        self.assertEqual(row["unchanged"], 1)
        self.assertEqual(row["changed"], [])
        self.assertEqual(row["cuts_carrying_a_summary_only"], 1)
        self.assertIn("command.json", row["done_items_at_the_cut_read_from"])

    def test_a_fresh_cut_retains_the_complete_done_item_object(self):
        """So the full comparison applies to the rerun, not the summary one."""
        rows = runner.state_of_checkpoint(
            {"scope": {"items": [{"index": 0, "state": "done", "retries": 0,
                                  "result": {"index": 0, "disposition": "fixed"}},
                                 {"index": 1, "state": "pending", "retries": 0}]}})["item_rows"]
        done = [r for r in rows if r["state"] == "done"]
        self.assertEqual(len(done), 1)
        self.assertIsNotNone(done[0]["result"])
        self.assertIsNotNone(done[0]["result_sha256"])

    def test_all_six_identity_fields_are_compared(self):
        same = {"index": 0, "location": {"file": "src/x.py", "line": 1},
                "disposition": "fixed"}
        moved = {"commit": "same", "dirty": False, "tracked_diff_sha256": "same",
                 "untracked": ["a-new-file"], "untracked_sha256": "different",
                 "submodules": []}
        rows = self.continuation_record(same, identity_after=moved)
        row = rows["invariants"]["start_identity_preserved"]
        self.assertFalse(row["held"])
        self.assertEqual(sorted(row["fields_that_differ"]),
                         ["untracked", "untracked_sha256"])
        self.assertEqual(len(row["compared_on"]), 6)


class Item1ModelBindingAfterTheRealRun(RunnerCase):
    """E11-7 item 1, corrected 2026-09-17: the provider route is not the model's identity.

    The control room ran the derived grade on the E10 root and 13 qwen plus 11 DeepSeek
    attempts read `ids_agree: false` over a prefix: the native witness joins `providerID` to
    `modelID` for its own display (`openrouter/deepseek/deepseek-v4.1-flash`) while the result
    reports the profile's own form (`deepseek/deepseek-v4.1-flash`). The Codex mismatch must
    stay a failure.
    """

    OPENCODE_NATIVE = {"id": "openrouter/deepseek/deepseek-v4.1-flash",
                       "model_id": "deepseek/deepseek-v4.1-flash", "provider": "openrouter"}
    OPENCODE_RESULT = {"id": "deepseek/deepseek-v4.1-flash"}

    def test_the_provider_route_is_not_part_of_the_identity(self):
        native, how = runner.canonical_model_id(self.OPENCODE_NATIVE)
        reported, _how = runner.canonical_model_id(self.OPENCODE_RESULT)
        self.assertEqual(native, "deepseek/deepseek-v4.1-flash")
        self.assertEqual(native, reported)
        self.assertIn("canonical form", how)

    def test_qwen_agrees_the_same_way(self):
        native, _ = runner.canonical_model_id(
            {"id": "openrouter/qwen/qwen3.8-flash", "model_id": "qwen/qwen3.8-flash",
             "provider": "openrouter"})
        reported, _ = runner.canonical_model_id({"id": "qwen/qwen3.8-flash"})
        self.assertEqual(native, reported)

    def test_a_session_misreporting_its_own_model_is_still_a_mismatch(self):
        """Codex: the result says `gpt-5`, the native witness says `gpt-5.6-sol`."""
        native, _ = runner.canonical_model_id({"id": "gpt-5.6-sol"})
        for reported_id in ("gpt-5", "GPT-5"):
            reported, _ = runner.canonical_model_id({"id": reported_id})
            self.assertNotEqual(native, reported, reported_id)

    def test_an_id_with_no_route_and_no_model_id_is_untouched(self):
        value, how = runner.canonical_model_id({"id": "claude-opus-5"})
        self.assertEqual(value, "claude-opus-5")
        self.assertIn("as recorded", how)

    def test_identical_ids_never_disagree(self):
        """The two OpenCode ABSENT attempts: both sides read the same string.

        The session hand-wrote a minimal `run.model` — `openrouter/qwen/qwen3.8-flash` with no
        `provider_route` — so a rule that strips only a side's OWN named route canonicalised
        the observed side and left the reported side joined, and two identical strings
        disagreed (the control room's second derived run on the E10 root).
        """
        native = {"id": "openrouter/qwen/qwen3.8-flash",
                  "model_id": "qwen/qwen3.8-flash", "provider": "openrouter"}
        reported = {"id": "openrouter/qwen/qwen3.8-flash", "floor_class": "opus"}
        route = runner.model_provider_route(native, reported)
        self.assertEqual(route, "openrouter")
        observed, _ = runner.canonical_model_id(native, native["id"], route=route)
        got, how = runner.canonical_model_id(reported, reported["id"], route=route)
        self.assertEqual(observed, "qwen/qwen3.8-flash")
        self.assertEqual(got, "qwen/qwen3.8-flash")
        self.assertIn("trial's provider route", how)

    def test_the_route_is_read_from_whichever_record_names_it(self):
        """The reported side need not name its own route; the trial has one."""
        self.assertEqual(
            runner.model_provider_route({"id": "openrouter/qwen/qwen3.8-flash"},
                                        {"id": "x", "provider_route": "openrouter"}),
            "openrouter")
        self.assertIsNone(
            runner.model_provider_route({"id": "gpt-5.6-sol"}, {"id": "gpt-5"}))

    def test_a_route_is_only_stripped_when_the_record_names_it(self):
        """Nothing is stripped by shape: only the record's OWN provider route comes off."""
        value, _ = runner.canonical_model_id({"id": "openrouter/qwen/qwen3.8-flash"})
        self.assertEqual(value, "openrouter/qwen/qwen3.8-flash")
        value, _ = runner.canonical_model_id(
            {"id": "openrouter/qwen/qwen3.8-flash", "provider": "anthropic"})
        self.assertEqual(value, "openrouter/qwen/qwen3.8-flash")


class Item2Separation(RunnerCase):
    """E11-7 item 2: the shared resources and the absent condition."""

    def test_each_trial_gets_its_own_scratch(self):
        campaign = runner.Campaign(self.campaign)
        a = runner.trial_scratch(campaign, "setup-case-available-r1", 0)
        b = runner.trial_scratch(campaign, "setup-case-absent-r1", 0)
        self.assertNotEqual(a, b)
        self.assertTrue(os.path.isdir(a) and os.path.isdir(b))
        self.assertNotEqual(a, campaign.tmp)
        env = campaign.env(scratch=a, require_binaries=False)
        self.assertEqual(env["TMPDIR"], a)

    def test_the_read_boundary_preflight_fails_when_a_sentinel_is_readable(self):
        """A trial that can read another trial's sentinel is not a controlled comparison."""
        got = cli(["preflight", "--campaign", self.campaign])
        self.assertNotEqual(got.returncode, 0, got.stdout)
        self.assertIn("read-boundary preflight failed", got.stderr)

    def test_the_preflight_records_the_acceptance_when_it_is_accepted(self):
        got = cli(["preflight", "--campaign", self.campaign, "--accept-unseparated"])
        self.assertEqual(got.returncode, 0, got.stderr)
        document = parse_stdout(got)
        self.assertTrue(document["accepted_unseparated"])
        self.assertFalse(document["separated"])
        self.assertTrue(document["rows"][0]["read_the_other_trials_sentinel"])

    def test_both_conditions_receive_the_same_record_contract(self):
        """Twenty schema-valid absent results failed a protocol nobody had stated to them."""
        run_dir = os.path.join(self.scratch, "prepared-run")
        runner.prepare_run_dir(run_dir)
        for name in ("result.schema.json", "checkpoint.schema.json", "receipt.schema.json",
                     "record-contract.md"):
            self.assertTrue(os.path.isfile(os.path.join(run_dir, name)), name)
        contract = runner.read_text(os.path.join(run_dir, "record-contract.md"), "")
        for wanted in ("checkpoint.json", "receipt.json", "RECHECK:",
                       "recheck_verifier_report"):
            self.assertIn(wanted, contract)
        self.assertNotIn("recheck-v2", contract)

    def test_the_prompt_names_the_record_contract(self):
        self.assertIn("record-contract.md", runner.PROMPT_TEMPLATE)

    def test_a_trial_that_read_another_trials_records_is_not_comparison_evidence(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(campaign.trials, "setup-case-absent-r1")
        other = os.path.join(campaign.trials, "setup-case-available-r1")
        runner.ensure_dir(record)
        runner.ensure_dir(other)
        witnesses = {"records_reached": {"reads": [
            {"path": os.path.join(other, "result.json"), "status": "completed",
             "tool": "bash"}]}}
        command = {"opaque_tree": os.path.join(campaign.tmp, "mine")}
        verdict = runner.comparison_evidence(campaign, record, witnesses, command)
        self.assertFalse(verdict["usable"])
        self.assertEqual(verdict["completed_foreign_reads"], 1)
        self.assertEqual(verdict["foreign_reads"][0]["what"],
                         "another trial's record directory")

    def test_a_trial_that_read_only_its_own_tree_is_comparison_evidence(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(campaign.trials, "setup-case-absent-r1")
        tree = os.path.join(campaign.tmp, "mine")
        runner.ensure_dir(record)
        witnesses = {"records_reached": {"reads": [
            {"path": os.path.join(tree, "fixture", "input.json"), "status": "completed"}]}}
        verdict = runner.comparison_evidence(campaign, record, witnesses,
                                             {"opaque_tree": tree})
        self.assertTrue(verdict["usable"])


class Item2AllowRules(RunnerCase):
    """E11-7 item 2, found live: an OpenCode home carries the INSTALLER's allow rule."""

    setups = ("opencode",)

    def test_a_home_written_for_another_campaign_fails_the_preflight(self):
        campaign = runner.Campaign(self.campaign)
        plan = campaign.plan()
        setup = runner.setup_for(campaign, plan, "opencode")
        config = os.path.join(setup.home("available"), "xdg-config", "opencode",
                              "opencode.json")
        runner.ensure_dir(os.path.dirname(config))
        self.addCleanup(lambda: os.path.isfile(config) and os.remove(config))
        runner.write_text(config, '{"permission": {"external_directory": '
                                  '{"/some/other/campaign/tmp/**": "allow"}}}')
        check = runner.allow_rule_check(campaign, plan)
        self.assertFalse(check["ok"])
        self.assertEqual([r["home"] for r in check["homes_written_for_another_campaign"]],
                         ["available"])
        self.assertIn("installed it", check["why"])

    def test_a_home_written_for_this_campaign_passes(self):
        campaign = runner.Campaign(self.campaign)
        plan = campaign.plan()
        setup = runner.setup_for(campaign, plan, "opencode")
        config = os.path.join(setup.home("available"), "xdg-config", "opencode",
                              "opencode.json")
        runner.ensure_dir(os.path.dirname(config))
        self.addCleanup(lambda: os.path.isfile(config) and os.remove(config))
        runner.write_text(config, '{"permission": {"external_directory": '
                                  '{"%s/**": "allow"}}}' % campaign.tmp)
        self.assertTrue(runner.allow_rule_check(campaign, plan)["ok"])


class Item5ManualOnlyGuard(RunnerCase):
    """E11-7 item 5: a real manual-only selection guard, or an honest `unqualified`."""

    setups = ("claude-code", "codex", "opencode")

    def test_every_harness_declares_what_it_supplies(self):
        for harness in ("claude-code", "codex", "opencode"):
            guard = runner.MANUAL_ONLY_GUARD[harness]
            self.assertIn("mechanism", guard)
            self.assertTrue(guard["covers_discovery_by_file_read"])
            self.assertTrue(guard["measured_in"])
        # the two harnesses whose own mechanism does not cover a file read get the runner's
        self.assertFalse(runner.MANUAL_ONLY_GUARD["claude-code"]["runner_closes_the_station"])
        self.assertTrue(runner.MANUAL_ONLY_GUARD["codex"]["runner_closes_the_station"])
        self.assertTrue(runner.MANUAL_ONLY_GUARD["opencode"]["runner_closes_the_station"])

    def test_the_barrier_closes_and_restores_the_installed_station(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, self.plan_document, "codex")
        # the pilot root is shared by the whole suite: everything this test creates in it is
        # removed again, or a later test reads a home this test invented.
        station = os.path.join(setup.home("routing"), "skills", "manual-only-probe")
        self.addCleanup(shutil.rmtree, os.path.join(setup.home("routing"), "skills"), True)
        runner.ensure_dir(station)
        runner.write_text(os.path.join(station, "SKILL.md"), "the station's body")
        # the copy the live Codex proof found: the setup's own probe marketplace, beside the
        # homes rather than inside one
        beside = os.path.join(os.path.dirname(os.path.dirname(setup.home("routing"))),
                              "probe-marketplace", "plugins", "manual-only-probe",
                              "skills", "manual-only-probe")
        self.addCleanup(shutil.rmtree,
                        os.path.join(os.path.dirname(os.path.dirname(setup.home("routing"))),
                                     "probe-marketplace"), True)
        runner.ensure_dir(beside)
        runner.write_text(os.path.join(beside, "SKILL.md"), "the same body, elsewhere")
        before = os.stat(station).st_mode & 0o7777
        with runner.manual_only_barrier(setup, "a test") as barrier:
            self.assertEqual(os.stat(station).st_mode & 0o7777, 0o000)
            with self.assertRaises(OSError):
                os.listdir(station)
            # the copy the live Codex proof found is unreachable too: its own parent copy
            # is closed, so the body cannot be read by walking to it
            with self.assertRaises(OSError):
                open(os.path.join(beside, "SKILL.md")).read()
        self.assertEqual(os.stat(station).st_mode & 0o7777, before)
        record = barrier.record()
        self.assertTrue(record["enforced"])
        applied = [row for row in record["stations"] if row.get("applied")]
        self.assertEqual(len(applied), 3, record["stations"])
        self.assertTrue(all(row["restored"] for row in applied))
        self.assertTrue(record["roots_searched"])

    def test_a_harness_that_enforces_it_itself_is_not_touched(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, self.plan_document, "claude-code")
        with runner.manual_only_barrier(setup, "a test") as barrier:
            pass
        record = barrier.record()
        self.assertTrue(record["enforced"])
        self.assertFalse(record["stations"][0]["applied"])


class Item6Consumer(RunnerCase):
    """E11-7 item 6: the consumer test, end to end on the fake harness."""

    setups = ("claude-code", "codex")

    def producer_trial(self):
        tid = runner.trial_id("claude-code", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        return tid

    def test_the_plan_mints_every_ordered_pair(self):
        order = runner.consumer_order(self.plan_document)
        pairs = sorted(t for rows in order.values() for t in rows)
        self.assertEqual(pairs, ["consumer-claude-code-to-codex-r1",
                                 "consumer-codex-to-claude-code-r1"])
        parts = runner.parse_consumer_id(self.plan_document,
                                         "consumer-claude-code-to-codex-r1")
        self.assertEqual((parts["producer"], parts["consumer"]),
                         ("claude-code", "codex"))

    def test_a_consumer_trial_runs_and_grades_end_to_end(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        got = cli(["consumer", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        document = parse_stdout(got)
        grade = document["consumer_grade"]
        self.assertTrue(grade["ok"], grade.get("why"))
        for name in ("original_scope", "item_identity", "evidence_references",
                     "card_interpretation", "unrelated_records_unavailable"):
            self.assertTrue(grade["checks"][name], name)
        # only ONE producer's records are in reach
        pair = document["pair"]
        self.assertEqual(pair["unrelated_records_present"], [])
        self.assertIn("result.json", pair["copied"])
        self.assertTrue(os.path.isdir(pair["workspace"]))

    def test_a_consumer_that_recovers_the_wrong_scope_fails(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        got = cli(["consumer", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("codex")])
        document = parse_stdout(got)
        answer = os.path.join(document["pair"]["pair_dir"], "consumer.json")
        content = runner.read_json(answer)
        content["items"] = []
        runner.write_json(answer, content)
        campaign = runner.Campaign(self.campaign)
        plan = campaign.plan()
        producer = runner.producer_record_for(campaign, plan, "claude-code")
        grade = runner.consumer_grade(document["pair"], producer, answer)
        self.assertFalse(grade["ok"])
        self.assertIn("original_scope", grade["why"])


class Item4ContinuationControl(RunnerCase):
    """E11-7 item 4: the real child group, the cut's own proof, the zero count."""

    def test_the_harnesss_own_child_group_is_found_from_child_pid(self):
        import subprocess
        out = os.path.join(self.scratch, "groups")
        runner.ensure_dir(out)
        child = subprocess.Popen(["/bin/sh", "-c", "sleep 30"], start_new_session=True)
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        grandchild = subprocess.Popen(["/bin/sh", "-c", "sleep 30"], start_new_session=True)
        self.addCleanup(grandchild.wait)
        self.addCleanup(grandchild.kill)
        runner.write_text(os.path.join(out, "child.pid"), "%d\n" % grandchild.pid)
        groups, rows = runner.launched_child_groups(out, child)
        self.assertEqual(len(groups), 2, rows)
        self.assertIn(os.getpgid(grandchild.pid), groups)
        self.assertFalse(rows[1]["same_group_as_the_launcher"])

    def test_one_group_is_found_when_the_launcher_keeps_its_child(self):
        import subprocess
        out = os.path.join(self.scratch, "one-group")
        runner.ensure_dir(out)
        child = subprocess.Popen(["/bin/sh", "-c", "sleep 30"], start_new_session=True)
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        groups, rows = runner.launched_child_groups(out, child)
        self.assertEqual(len(groups), 1, rows)

    def test_every_group_is_ended_and_proved_gone(self):
        import subprocess
        child = subprocess.Popen(["/bin/sh", "-c", "sleep 30"], start_new_session=True)
        pgid = os.getpgid(child.pid)
        rows = runner._end_groups([pgid])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["gone"], rows)
        child.wait()

    def test_a_writer_that_progressed_after_the_cut_fails_the_invariant(self):
        record = os.path.join(self.scratch, "progressed")
        run_dir = os.path.join(record, "run")
        runner.ensure_dir(run_dir)
        runner.write_json(os.path.join(run_dir, "checkpoint.json"),
                          {"phase": "completed", "continuations": 1, "scope": {"items": []}})
        at_cut = runner.run_dir_fingerprint(run_dir)
        runner.write_json(os.path.join(run_dir, "checkpoint.json"),
                          {"phase": "committed", "continuations": 1, "scope": {"items": []}})
        after = runner.run_dir_fingerprint(run_dir)
        moved = sorted(set([n for n in at_cut if at_cut[n] != after.get(n)]
                           + [n for n in after if n not in at_cut]))
        self.assertEqual(moved, ["checkpoint.json"])
        runner.write_json(os.path.join(record, "result.json"), {})
        command = {"cut": {"valid": True, "start_identity": {}, "retained": {},
                           "no_writer_progressed": {"held": False, "files_that_moved": moved,
                                                    "files_at_the_cut": len(at_cut),
                                                    "files_before_the_resume": len(after)}}}
        rows = runner.continuation_invariants(record, command)
        row = rows["invariants"]["no_writer_progressed_after_the_cut"]
        self.assertFalse(row["held"])
        self.assertEqual(row["observed"], ["checkpoint.json"])
        self.assertFalse(rows["all_held"])

    def test_a_zero_continuation_count_stays_zero(self):
        """A count of 0 is the measurement; `a or b` turned it into null."""
        state = runner.state_of_checkpoint({"continuations": 0, "scope": {"items": []}})
        self.assertEqual(state["continuations"], 0)
        self.assertIsNotNone(state["continuations"])

    def test_item_results_are_read_from_items_result(self):
        state = runner.state_of_checkpoint({"scope": {"items": [
            {"index": 0, "state": "done", "retries": 0,
             "result": {"index": 0, "disposition": "fixed"}}]}})
        row = state["item_rows"][0]
        self.assertEqual(row["disposition"], "fixed")
        self.assertTrue(row["result_sha256"])


class Item4Compaction(RunnerCase):
    """E11-7 item 4: the ordering check starts at the resumed turn and tests `witness.ok`."""

    setups = ("codex",)

    def rollout(self, name, rows):
        out = os.path.join(self.scratch, "compaction-%s" % name)
        runner.ensure_dir(out)
        jsonl(os.path.join(out, "rollout.jsonl"), rows)
        return out

    def setup_for(self):
        return runner.setup_for(runner.Campaign(self.campaign), self.plan_document, "codex")

    def test_the_first_sessions_work_no_longer_decides_the_order(self):
        """X compaction: compaction at 155 really preceded the resumed work at 171."""
        rows = [
            {"payload": {"type": "function_call", "call_id": "c0",
                         "command": ["sh", "-c", "the first session's own work"]}},
            {"payload": {"type": "compacted"}},
            {"payload": {"type": "message", "role": "user",
                         "content": "resume the recheck run F3-02-run in /r"}},
            {"payload": {"type": "function_call", "call_id": "c1",
                         "command": ["sh", "-c", "the resumed work"]}},
        ]
        out = self.rollout("ordered", rows)
        witness = runner.compaction_witness(
            self.setup_for(), out,
            resume_text="resume the recheck run F3-02-run in /r for slice A")
        self.assertTrue(witness["ok"], witness)
        self.assertEqual(witness["resumed_turn_line"], 3)
        self.assertEqual(witness["line"], 2)
        self.assertEqual(witness["first_resumed_work_line"], 4)

    def test_a_compaction_after_the_resumed_work_is_not_ok(self):
        rows = [
            {"payload": {"type": "message", "role": "user",
                         "content": "resume the recheck run F3-02-run in /r"}},
            {"payload": {"type": "function_call", "call_id": "c1",
                         "command": ["sh", "-c", "the resumed work"]}},
            {"payload": {"type": "compacted"}},
        ]
        out = self.rollout("late", rows)
        witness = runner.compaction_witness(
            self.setup_for(), out, resume_text="resume the recheck run F3-02-run in /r")
        self.assertFalse(witness["ok"], witness)


class Item7Reporting(RunnerCase):
    """E11-7 item 7: honest labels, honest columns, honest counts."""

    def test_exit_124_is_a_timeout_in_both_the_verdict_and_the_status(self):
        step = {"exit": 124, "timed_out": False}
        self.assertIn("timed_out", runner.timeout_verdict(step))
        self.assertIn("124", runner.timeout_verdict(step))
        self.assertEqual(runner.outcome_status(step, False), "timed_out")

    def test_a_clean_exit_is_still_within_limit(self):
        self.assertEqual(runner.timeout_verdict({"exit": 0, "timed_out": False}),
                         "within limit")

    def test_the_gap_clock_restarts_when_a_trial_ends(self):
        source = runner.read_text(testlib.RUNNER, "")
        body = source[source.index("def _lane_work"):source.index("    workers = []")]
        gap_at = body.index("gap = time.time() - last")
        reset_at = body.rindex("last = time.time()")
        self.assertGreater(reset_at, gap_at,
                           "the clock must be reset AFTER the trial, not before it")
        self.assertIn("the preceding trials' own", body)

    def test_the_response_cookie_shape_is_scanned(self):
        path = os.path.join(self.scratch, "cookie.json")
        runner.write_text(path, 'set-cookie: __cf_bm=' + 'A1b2C3d4' * 6 + '-1789-0-Ab; path=/')
        found = runner.scan_paths([path])
        self.assertEqual([h["shape"] for h in found["hits"]], ["response-cookie"])

    def test_scrub_copy_sanitises_the_copy_and_leaves_the_original_alone(self):
        root = os.path.join(self.scratch, "records")
        runner.ensure_dir(root)
        path = os.path.join(root, "trace.json")
        runner.write_text(path, "x\nset-cookie: __cf_bm=" + "A1b2C3d4" * 6 + "; path=/\ny\n")
        before = runner.file_sha256(path)
        hits = runner.scan_paths([path])["hits"]
        destination = os.path.join(self.scratch, "review-copy")
        report = runner.do_scrub_copy([root], destination, (), hits)
        self.assertTrue(report["copy_is_clean"], report)
        self.assertEqual(report["values_replaced"], 1)
        self.assertEqual(runner.file_sha256(path), before, "the original changed")
        copied = os.path.join(destination, "records", "trace.json")
        self.assertIn("<redacted: response-cookie", runner.read_text(copied, ""))
        self.assertNotIn("__cf_bm=A1b2", runner.read_text(copied, ""))

    def test_a_scrub_copy_never_writes_over_an_existing_directory(self):
        destination = os.path.join(self.scratch, "taken")
        runner.ensure_dir(destination)
        with self.assertRaises(runner.Usage):
            runner.do_scrub_copy([self.scratch], destination, (), [])


class Item7Table(RunnerCase):
    """E11-7 item 7: the table's own columns."""

    def test_the_table_separates_no_result_from_timeouts_and_launch_failures(self):
        campaign = runner.Campaign(self.campaign)
        rows = [
            {"id": "a", "attempt": 0, "status": "no_result", "cost": 0.0, "wall": 1.0},
            {"id": "b", "attempt": 0, "status": "timed_out", "cost": 0.0, "wall": 1.0},
            {"id": "c", "attempt": 0, "status": "launch_failed", "cost": None, "wall": 1.0},
        ]
        for row in rows:
            campaign.append_jsonl(campaign.trials_jsonl, row)
        got = cli(["report", "--campaign", self.campaign])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        document = parse_stdout(got)
        table = runner.read_json(document["table_json"])
        totals = {"no_result": 0, "timed_out": 0, "launch_failed": 0}
        for row in table["table"]:
            for name in totals:
                totals[name] += row[name]
        self.assertEqual(totals, {"no_result": 1, "timed_out": 1, "launch_failed": 1})
        self.assertEqual(table["distinct_trials"], 3)
        self.assertIn("more than one row",
                      table["trial_counts_are_not_additive_across_activation_buckets"])

    def test_a_measured_zero_cost_stays_zero_and_an_absent_activation_is_unknown(self):
        campaign = runner.Campaign(self.campaign)
        campaign.append_jsonl(campaign.trials_jsonl,
                              {"id": "z", "attempt": 0, "status": "complete", "cost": 0.0,
                               "wall": 2.0})
        document = parse_stdout(cli(["report", "--campaign", self.campaign]))
        table = runner.read_json(document["table_json"])
        row = [r for r in table["table"] if "z" in r["attempt_ids"][0]][0]
        self.assertEqual(row["cost_usd"], 0.0)
        self.assertIsNone(row["activated"])
        self.assertIn("| unknown |", runner.read_text(document["table_md"], ""))

    def test_the_cost_line_counts_positive_cost_attempts(self):
        campaign = runner.Campaign(self.campaign)
        for name, cost in (("p1", 0.5), ("p2", 0.0), ("p3", None)):
            campaign.append_jsonl(campaign.trials_jsonl,
                                  {"id": name, "attempt": 0, "status": "complete",
                                   "cost": cost, "wall": 1.0})
        document = parse_stdout(cli(["report", "--campaign", self.campaign]))
        table = runner.read_json(document["table_json"])
        self.assertEqual(table["totals"]["positive_cost_attempts"], 1)
        self.assertEqual(table["totals"]["zero_cost_attempts"], 1)
        self.assertEqual(table["totals"]["cost_unavailable_attempts"], 1)
        self.assertIn("a launched session is not a charge", table["totals"]["cost_line"])


if __name__ == "__main__":
    unittest.main()
