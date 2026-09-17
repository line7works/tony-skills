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
        # a real witness classifies the operation (NEW BLOCKER 3); a completed read of
        # CONTENTS is what excludes a trial
        witnesses = {"records_reached": {"reads": [
            {"path": os.path.join(other, "result.json"), "status": "completed",
             "tool": "bash", "operation": "read of contents"}]}}
        command = {"opaque_tree": os.path.join(campaign.tmp, "mine")}
        verdict = runner.comparison_evidence(campaign, record, witnesses, command)
        self.assertFalse(verdict["usable"])
        self.assertEqual(verdict["completed_foreign_reads"], 1)
        self.assertEqual(verdict["foreign_reads"][0]["what"],
                         "another trial's record directory")

    def test_a_foreign_path_whose_operation_is_unknown_does_not_exclude(self):
        """An unclassified row is named, never counted — that is the listing defect's shape."""
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(campaign.trials, "setup-case-absent-r1")
        other = os.path.join(campaign.trials, "setup-case-available-r1")
        runner.ensure_dir(record)
        runner.ensure_dir(other)
        witnesses = {"records_reached": {"reads": [
            {"path": os.path.join(other, "result.json"), "status": "completed",
             "tool": "bash", "operation": "named, operation unknown"}]}}
        verdict = runner.comparison_evidence(
            campaign, record, witnesses, {"opaque_tree": os.path.join(campaign.tmp, "mine")})
        self.assertTrue(verdict["usable"])
        self.assertEqual(len(verdict["foreign_paths_named_but_not_read"]), 1)

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

    def test_a_consumer_trial_proves_the_whole_adopted_contract(self):
        """E11 fix round item 6: end to end on the fake harness, real producer record.

        Every check of the adopted contract passes except isolation, which is the bench's own
        measured state: a child in the consumer's launch environment CAN read a record
        outside its pair, so the flag is false and the grade says so (item 6(f)).
        """
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        got = cli(["consumer", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        document = parse_stdout(got)
        grade = document["consumer_grade"]
        checks = grade["checks"]
        for name in ("answer_present", "original_scope", "item_identity",
                     "evidence_references", "card_interpretation",
                     # item 6(b): a validating result and a delivered reply
                     "result_present", "result_validates", "reply_delivered",
                     "reply_carries_the_output_block",
                     # item 6(c) and 6(d)
                     "source_identity_matches_the_producer", "producer_history_preserved"):
            self.assertTrue(checks[name], name)
        self.assertEqual(grade["source_identity"]["fields_that_differ"], [])
        self.assertEqual(grade["producer_history"]["files_that_moved"], [])
        # item 6(f): read access, measured in the consumer's own launch environment
        self.assertTrue(grade["isolation"]["child_read_it"])
        self.assertFalse(checks["unrelated_records_unavailable"])
        self.assertEqual(grade["why"], ["unrelated_records_unavailable"])
        self.assertFalse(grade["ok"])

    def test_the_consumer_runs_the_job_through_the_declared_input_route(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        pair = document["pair"]
        payload = runner.read_json(pair["input"])
        self.assertIn("items", payload["target"])
        self.assertTrue(payload["target"]["items"])
        for item in payload["target"]["items"]:
            for field in ("severity", "location", "claim", "failure_scenario", "record",
                          "slice"):
                self.assertIn(field, item)
        self.assertTrue(os.path.isfile(os.path.join(pair["run_dir"], "record-contract.md")))
        self.assertEqual(pair["unrelated_records_present"], [])

    def test_changed_evidence_after_forty_characters_is_caught(self):
        """NEW MAJOR 5: the grader compared only the first forty characters."""
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        campaign = runner.Campaign(self.campaign)
        plan = campaign.plan()
        producer = runner.producer_record_for(campaign, plan, "claude-code")
        pair = document["pair"]
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        answer = runner.read_json(answer_path)
        expected = runner._consumer_expected(producer)
        changed = False
        for item, reference in zip(answer["items"], expected["items"]):
            if reference["evidence"]:
                detail = str(reference["evidence"][0]["detail"])
                item["evidence"] = [dict(reference["evidence"][0],
                                         detail=detail[:40] + " DIFFERENT OBSERVATION")]
                changed = True
        self.assertTrue(changed, "the producer record carried no evidence to change")
        runner.write_json(answer_path, answer)
        regraded = runner.consumer_grade(pair, producer, answer_path)
        self.assertFalse(regraded["checks"]["evidence_references"])
        self.assertIn("first forty characters", regraded["evidence"][0]["why"])
        self.assertFalse(regraded["ok"])

    def test_a_consumer_that_recovers_the_wrong_scope_fails(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        answer = os.path.join(document["pair"]["pair_dir"], "consumer.json")
        content = runner.read_json(answer)
        content["items"] = []
        runner.write_json(answer, content)
        campaign = runner.Campaign(self.campaign)
        producer = runner.producer_record_for(campaign, campaign.plan(), "claude-code")
        grade = runner.consumer_grade(document["pair"], producer, answer)
        self.assertFalse(grade["ok"])
        self.assertIn("original_scope", grade["why"])
        self.assertIn("item_identity", grade["why"])


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


# ---------------------------------------------------------------- the fix round (Astra's
# verification of 31329cd). Every test below fails on 31329cd and passes after.


class FixItem8DerivedGrades(RunnerCase):
    """NEW BLOCKER 1: a derived measurement is never replaced."""

    def test_a_repeated_revision_takes_the_next_free_name(self):
        record = os.path.join(self.scratch, "trial")
        runner.ensure_dir(record)
        first = runner.reserve_derived_grade(record, "review-derived")
        self.assertTrue(first.endswith("grade.review-derived.json"))
        runner.write_json(first, {"first": True})
        second = runner.reserve_derived_grade(record, "review-derived")
        self.assertNotEqual(first, second)
        self.assertTrue(second.endswith("grade.review-derived-1.json"))
        self.assertEqual(runner.read_json(first), {"first": True},
                         "the earlier derived measurement was replaced")

    def test_the_name_is_claimed_before_anything_is_written(self):
        record = os.path.join(self.scratch, "claimed")
        runner.ensure_dir(record)
        taken = runner.reserve_derived_grade(record, "rev")
        self.assertTrue(os.path.isfile(taken))
        self.assertNotEqual(runner.reserve_derived_grade(record, "rev"), taken)


class FixItem1Observation(RunnerCase):
    """Item 1(a), 1(b), 1(c): the three observation defects she probed."""

    def record_with(self, name, rows):
        record = os.path.join(self.scratch, name)
        runner.ensure_dir(os.path.join(record, "workspace"))
        command = {"workspace": os.path.join(record, "workspace"),
                   "run_dir": os.path.join(record, "run"), "opaque_tree": record,
                   "setup": "codex", "case": testlib.CASE, "condition": "available"}
        runner.write_json(os.path.join(record, "command.json"), command)
        jsonl(os.path.join(record, "harness", "rollout.jsonl"), rows)
        return record, command

    @staticmethod
    def call(cmd, output=None, workdir=None):
        argument = {"cmd": cmd}
        if workdir:
            argument["workdir"] = workdir
        rows = [{"payload": {"type": "function_call", "name": "exec_command", "call_id": "a",
                             "arguments": json.dumps(argument)}}]
        if output is not None:
            rows.append({"payload": {"type": "function_call_output", "call_id": "a",
                                     "output": json.dumps(output)}})
        return rows

    def test_an_unanswered_write_request_is_not_a_completed_write(self):
        """Her probe: `printf done > /outside/...` with no result record joined."""
        record, command = self.record_with(
            "unanswered", self.call("printf done > /outside/standin.txt"))
        self.assertEqual(runner.native_actions(record)[0]["status"], "unknown")
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual(witnesses["writes_outside"], [])
        self.assertEqual(len(witnesses["requested_outside_never_answered"]), 1)
        self.assertEqual(
            witnesses["requested_outside_never_answered"][0]["path"],
            "/outside/standin.txt")

    def test_a_completed_write_request_is_still_a_write(self):
        record, command = self.record_with(
            "answered", self.call("printf done > /outside/standin.txt", {"exit_code": 0}))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual([r["path"] for r in witnesses["writes_outside"]],
                         ["/outside/standin.txt"])

    def test_the_calls_own_workdir_resolves_its_relative_destination(self):
        """Her probe: `workdir=/outside` in the call's own arguments."""
        record, command = self.record_with(
            "per-call-dir",
            self.call("printf done > standin.txt", {"exit_code": 0}, workdir="/outside"))
        witnesses = runner.trace_witnesses(runner.Campaign(self.campaign), record, command)
        self.assertEqual([r["path"] for r in witnesses["writes_outside"]],
                         ["/outside/standin.txt"])
        self.assertEqual(witnesses["relative_destinations_resolved"][0]["cwd_source"],
                         "the call's own workdir argument")

    def test_reading_the_scenario_source_is_not_executing_it(self):
        """Her probe: `cat src/demo/check.py` plus matching output text."""
        record, _command = self.record_with(
            "read-only", self.call("cat src/demo/check.py",
                                   {"exit_code": 0, "output": "observed=7"}))
        entry = {"records_after": {"verifier_raw_report": {
            "scenario_command": "python3 -m demo.check", "observed_output": "observed=7"}}}
        witness = runner._scenario_execution(
            record, {"items": [{"verification": {"method": "executed"}}]}, entry)
        self.assertFalse(witness["held"])
        self.assertEqual(witness["commands_that_ran_it"], [])
        self.assertEqual(len(witness["reads_of_the_source_only"]), 1)

    def test_an_interpreter_running_the_module_is_an_execution(self):
        record, _command = self.record_with(
            "real-exec", self.call("PYTHONPATH=src python3 -m demo.check",
                                   {"exit_code": 0, "output": "observed=7"}))
        entry = {"records_after": {"verifier_raw_report": {
            "scenario_command": "python3 -m demo.check", "observed_output": "observed=7"}}}
        witness = runner._scenario_execution(
            record, {"items": [{"verification": {"method": "executed"}}]}, entry)
        self.assertTrue(witness["held"])
        self.assertTrue(witness["output_bound_to_the_execution"])
        self.assertIn("to run", witness["the_execution"]["how"])

    def test_the_file_itself_run_is_an_execution(self):
        ran, how = runner.command_executes("./src/demo/check.py", r"demo[./]check")
        self.assertTrue(ran)
        self.assertIn("the file itself", how)

    def test_a_read_utility_naming_the_file_is_not(self):
        for text in ("cat src/demo/check.py", "sed -n '1,20p' src/demo/check.py",
                     "grep -n x src/demo/check.py", "head src/demo/check.py"):
            ran, _how = runner.command_executes(text, r"demo[./]check")
            self.assertFalse(ran, text)

    # The control room's gate on section 11: three real E10 executions read as
    # `reads_of_the_source_only`. `command_word_lists` hands back ONE layer for a whole
    # compound line, so the head rule saw `S=...;`, `cd` or `mkdir` and never reached the
    # `python3 -m widget.export` simple command inside it. Every command below is quoted
    # from the launch capture of the trial named beside it.
    E10_R1_LINE_18 = (
        "S=/Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "e219dfd7bb96a644/fixture/ca8c359f89da/run/verifier; "
        "W=/Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "e219dfd7bb96a644/fixture/ca8c359f89da/workspace; "
        "{ echo \"\\$ PYTHONPATH=src python3 -m widget.export 'Widget, deluxe'\"; "
        "PYTHONPATH=src python3 -m widget.export 'Widget, deluxe' 2>&1; "
        "echo \"exit=$?\"; } > \"$S/export-comma.log\" 2>&1; cat \"$S/export-comma.log\"")
    E10_R2_LINE_18 = (
        "cd /Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "071f7ea0ee1b2237/fixture/ca8c359f89da/workspace && "
        "V=/Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "071f7ea0ee1b2237/fixture/ca8c359f89da/run/verifier && "
        "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m widget.export 'Widget, deluxe' "
        "> \"$V/export-comma.log\" 2>&1; echo \"exit=$?\"; cat \"$V/export-comma.log\"")
    E10_R2_LINE_23 = (
        "cd /Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "071f7ea0ee1b2237/fixture/ca8c359f89da/workspace && "
        "V=/Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "071f7ea0ee1b2237/fixture/ca8c359f89da/run/verifier && "
        "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m widget.export 'PlainWidget' "
        "> \"$V/export-nocomma.log\" 2>&1; echo \"exit=$?\"; "
        "cat \"$V/export-nocomma.log\"; echo \"---\"; git status --porcelain; "
        "echo \"git-clean-exit=$?\"; ls \"$V\"")
    E10_DEEPSEEK_R2_LINE_17 = (
        "mkdir -p /Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "25ef5f0cd72d8a02/fixture/ca8c359f89da/run/verifier && "
        "cd /Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "25ef5f0cd72d8a02/fixture/ca8c359f89da/workspace && "
        "PYTHONPATH=src python3 -m widget.export 'Widget, deluxe' 2>&1 | tee "
        "/Users/tonycoon/.local/share/skills-v2-pilot/e10/e10-rerun-2026-09-16/tmp/"
        "25ef5f0cd72d8a02/fixture/ca8c359f89da/run/verifier/export-comma.log; "
        "echo \"EXIT=$?\"")
    CONTROL = ("cd /w && V=/v && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "
               "python3 -m widget.export 'x' > \"$V/a.log\" 2>&1; echo \"exit=$?\"; "
               "cat \"$V/a.log\"")

    def test_an_interpreter_inside_a_compound_command_is_an_execution(self):
        """The three real E10 shapes plus the control room's one-line control."""
        for label, text in (("e10-rerun r1 line 18", self.E10_R1_LINE_18),
                            ("e10-rerun r2 line 18", self.E10_R2_LINE_18),
                            ("e10-rerun r2 line 23", self.E10_R2_LINE_23),
                            ("e10-rerun deepseek r2 line 17", self.E10_DEEPSEEK_R2_LINE_17),
                            ("the control", self.CONTROL)):
            ran, how = runner.command_executes(text, r"widget[./]export")
            self.assertTrue(ran, "%s: %s" % (label, how))
            self.assertIn("python3", how, label)
            self.assertNotIn("read-only", how, label)

    def test_a_read_in_the_same_line_does_not_cancel_the_execution(self):
        """Every one of those lines also `cat`s the log; the run still happened."""
        ran, _how = runner.command_executes(
            "PYTHONPATH=src python3 -m widget.export 'x' > a.log; cat a.log",
            r"widget[./]export")
        self.assertTrue(ran)

    def test_a_compound_line_that_only_reads_names_the_heads_it_saw(self):
        """(3): the reason says what was observed, and no invented read-only utility."""
        ran, how = runner.command_executes(
            "cd /w && cat src/widget/export.py; echo src/widget/export.py",
            r"widget[./]export")
        self.assertFalse(ran)
        self.assertIn("cat", how)
        self.assertIn("echo", how)
        ran, how = runner.command_executes("cd /w && cat src/widget/export.py",
                                           r"widget[./]export")
        self.assertFalse(ran)
        self.assertIn("read-only", how)
        self.assertIn("cat", how)

    def test_a_one_liner_given_the_module_is_the_interpreter_running_it(self):
        ran, how = runner.command_executes(
            "PYTHONPATH=src python3 -c 'from widget.export import to_csv; print(to_csv([]))'",
            r"widget[./]export")
        self.assertTrue(ran)
        self.assertIn("python3", how)

    def test_the_simple_commands_of_a_compound_line_are_each_separated(self):
        heads = [argv[0] for argv in runner.simple_commands(self.CONTROL) if argv]
        self.assertIn("cd", heads)
        self.assertIn("echo", heads)
        self.assertIn("cat", heads)
        self.assertTrue(any(argv[:2] == ["python3", "-m"]
                            for argv in
                            [runner._argv_without_assignments(a)
                             for a in runner.simple_commands(self.CONTROL)]))


class Fix2ConsumerEvidence(RunnerCase):
    """The narrow second fix, item B (Astra's re-check of the fix round).

    The pair carried no evidence files, the grade read `artifact` while the result schema
    names `artifact_path`, and the continuation comparison counted done and pending instead
    of keying them by item index.
    """

    setups = ("claude-code", "codex")

    def producer_with_an_artifact(self, name="producer"):
        """A stand-in producer record whose evidence names a real file, as her probe does."""
        record = os.path.join(self.scratch, name)
        runner.ensure_dir(os.path.join(record, "workspace"))
        artifact = os.path.join(record, "run", "verifier", "observation.txt")
        runner.ensure_dir(os.path.dirname(artifact))
        runner.write_text(artifact, "observed seven\n")
        runner.write_json(os.path.join(record, "result.json"), {
            "items": [{"location": {"file": "src/demo.py", "line": 7},
                       "claim": "a stand-in claim", "failure_scenario": "run the counter",
                       "severity": "MAJOR", "disposition": "not_fixed",
                       "reason": "reproduces",
                       "verification": {"evidence": [
                           {"kind": "command", "artifact_path": artifact,
                            "detail": "The observed counter remained at seven after the "
                                      "operation; expected eight."}]}}],
            "cards": []})
        runner.write_json(os.path.join(record, "run", "checkpoint.json"),
                          {"phase": "completed", "continuations": 0, "scope": {"items": []}})
        return {"record": record, "trial": "standin-producer",
                "command": {"workspace": os.path.join(record, "workspace")}}, artifact

    def staged(self, producer, leaf="pair"):
        campaign = runner.Campaign(self.campaign)
        return runner.stage_consumer_pair(campaign, producer,
                                          os.path.join(self.scratch, leaf))

    def test_the_pair_carries_the_file_the_evidence_names(self):
        """Her artifact_recovery probe: `artifact_copied` was false."""
        producer, artifact = self.producer_with_an_artifact()
        pair = self.staged(producer)
        copy = os.path.join(pair["producer_dir"], "run", "verifier", "observation.txt")
        self.assertTrue(os.path.isfile(copy), pair["copied"])
        self.assertEqual(runner.file_sha256(copy), runner.file_sha256(artifact))
        rows = pair["artifacts"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["copied"])
        self.assertEqual(rows[0]["artifact_path"], artifact)
        self.assertEqual(rows[0]["sha256"], runner.file_sha256(artifact))
        self.assertIn(os.path.join("run", "verifier", "observation.txt"), pair["copied"])

    def test_the_expected_reference_reads_the_schemas_field(self):
        producer, artifact = self.producer_with_an_artifact("named")
        expected = runner._consumer_expected(producer)
        reference = expected["items"][0]["evidence"][0]
        self.assertEqual(reference["artifact_path"], artifact)
        self.assertEqual(reference["named_by"], "artifact_path")

    def test_a_changed_artifact_path_fails_the_evidence_check(self):
        """Her probe: `changed_path_accepted` was true."""
        producer, _artifact = self.producer_with_an_artifact("changed")
        pair = self.staged(producer, "changed-pair")
        expected = runner._consumer_expected(producer)
        answer = {"items": expected["items"], "cards": []}
        answer["items"][0]["evidence"][0]["artifact_path"] = "different-observation.txt"
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        runner.write_json(answer_path, answer)
        grade = runner.consumer_grade(pair, producer, answer_path)
        self.assertFalse(grade["checks"]["evidence_references"])
        self.assertFalse(grade["checks"]["evidence_artifacts_recovered"])
        self.assertFalse(grade["ok"])

    def test_the_honest_answer_recovers_the_reference_and_the_file(self):
        producer, _artifact = self.producer_with_an_artifact("honest")
        pair = self.staged(producer, "honest-pair")
        expected = runner._consumer_expected(producer)
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        runner.write_json(answer_path, {"items": expected["items"], "cards": []})
        grade = runner.consumer_grade(pair, producer, answer_path)
        self.assertTrue(grade["checks"]["evidence_references"])
        self.assertTrue(grade["checks"]["evidence_artifacts_recovered"])
        row = grade["evidence_artifacts"][0]
        self.assertTrue(row["content_matches"])
        self.assertEqual(row["producer_sha256"], row["consumer_sha256"])

    def producer_with_two_artifacts(self, name="two-artifacts"):
        """Her consumer-artifact-order.py producer: two references, two distinct files."""
        producer, first = self.producer_with_an_artifact(name)
        record = producer["record"]
        second = os.path.join(record, "run", "verifier", "second.txt")
        runner.write_text(second, "a second distinct observation\n")
        result = runner.read_json(os.path.join(record, "result.json"))
        result["items"][0]["verification"]["evidence"].append(
            {"kind": "command", "detail": "a second observation", "artifact_path": second})
        runner.write_json(os.path.join(record, "result.json"), result)
        return producer, first, second

    def test_two_references_given_in_the_other_order_still_recover(self):
        """E11-15 send-back, B2: `_artifact_rows` paired by list position.

        `_same_evidence` accepts the consumer's references in any order, so an answer that
        listed two CORRECT references reversed passed `evidence_references` and failed
        `evidence_artifacts_recovered` with both files unchanged.
        """
        producer, _first, _second = self.producer_with_two_artifacts()
        pair = self.staged(producer, "order-pair")
        expected = runner._consumer_expected(producer)
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        # the control: both references, in the producer's own order
        runner.write_json(answer_path, {"items": expected["items"], "cards": []})
        grade = runner.consumer_grade(pair, producer, answer_path)
        self.assertTrue(grade["checks"]["evidence_references"])
        self.assertTrue(grade["checks"]["evidence_artifacts_recovered"])
        # the same two references, reversed
        answer = runner.read_json(answer_path)
        answer["items"][0]["evidence"].reverse()
        runner.write_json(answer_path, answer)
        grade = runner.consumer_grade(pair, producer, answer_path)
        self.assertTrue(grade["checks"]["evidence_references"])
        self.assertTrue(grade["checks"]["evidence_artifacts_recovered"])
        # and both staged files really are the producer's, untouched
        self.assertTrue(all(runner.file_sha256(row["staged"]) == row["sha256"]
                            for row in pair["artifacts"]))
        for row in grade["evidence_artifacts"]:
            self.assertEqual(row["producer_named"], row["consumer_named"])
            self.assertTrue(row["content_matches"])

    def test_one_of_two_references_naming_the_wrong_file_still_fails(self):
        """The pairing is by name, so a wrong name has no counterpart at all."""
        producer, _first, _second = self.producer_with_two_artifacts("wrong-of-two")
        pair = self.staged(producer, "wrong-of-two-pair")
        expected = runner._consumer_expected(producer)
        answer = {"items": expected["items"], "cards": []}
        answer["items"][0]["evidence"][1]["artifact_path"] = "different-observation.txt"
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        runner.write_json(answer_path, answer)
        grade = runner.consumer_grade(pair, producer, answer_path)
        self.assertFalse(grade["checks"]["evidence_artifacts_recovered"])
        unpaired = [r for r in grade["evidence_artifacts"] if r["consumer_named"] is None]
        self.assertEqual(len(unpaired), 1)

    def test_an_answer_naming_a_file_the_pair_does_not_hold_fails(self):
        """The reference is right, the file is gone: the content check is what catches it."""
        producer, _artifact = self.producer_with_an_artifact("missing")
        pair = self.staged(producer, "missing-pair")
        expected = runner._consumer_expected(producer)
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        runner.write_json(answer_path, {"items": expected["items"], "cards": []})
        os.remove(os.path.join(pair["producer_dir"], "run", "verifier", "observation.txt"))
        grade = runner.consumer_grade(pair, producer, answer_path)
        self.assertTrue(grade["checks"]["evidence_references"])
        self.assertFalse(grade["checks"]["evidence_artifacts_recovered"])

    # ---- the continuation comparison, keyed by item index
    def continuation_producer(self):
        record = os.path.join(self.scratch, "cont-producer")
        runner.ensure_dir(os.path.join(record, "workspace"))
        items = [{"location": {"file": "src/demo.py", "line": line},
                  "claim": "stand-in claim %d" % line,
                  "failure_scenario": "run the counter", "severity": "MAJOR",
                  "disposition": "not_fixed", "reason": "reproduces",
                  "verification": {"evidence": [{"kind": "command",
                                                 "detail": "observed counter at seven"}]}}
                 for line in (7, 8)]
        runner.write_json(os.path.join(record, "result.json"),
                          {"items": items, "cards": []})
        runner.write_json(os.path.join(record, "run", "checkpoint.json"),
                          {"phase": "adjudicating", "continuations": 1,
                           "items": [{"state": "done", "result": items[0]},
                                     {"state": "pending", "result": None}]})
        return {"record": record, "trial": "standin-producer",
                "command": {"workspace": os.path.join(record, "workspace"),
                            "kind": "continuation-handoff"}}

    def graded_continuation(self, mutate=None, leaf="cont-pair"):
        import copy
        producer = self.continuation_producer()
        pair = self.staged(producer, leaf)
        expected = runner._consumer_expected(producer)
        answer = {"items": expected["items"], "cards": [],
                  "continuation": copy.deepcopy(expected["continuation"])}
        if mutate:
            mutate(answer["continuation"])
        answer_path = os.path.join(pair["pair_dir"], "consumer.json")
        runner.write_json(answer_path, answer)
        return runner.consumer_grade(pair, producer, answer_path), answer, expected

    def test_the_honest_continuation_answer_still_passes(self):
        grade, _answer, _expected = self.graded_continuation(leaf="cont-control")
        self.assertTrue(grade["checks"]["continuation_state"])

    def test_a_swapped_done_and_pending_fails_the_continuation_state(self):
        """Her consumer_swapped_item_states: counts unchanged, the assignment reversed."""
        def swap(state):
            state["states"] = ["pending", "done"]
            for row, value in zip(state["item_rows"], ["pending", "done"]):
                row["state"] = value
        grade, answer, expected = self.graded_continuation(swap, "cont-swapped")
        # the counts really are unchanged: this is what passed before
        for field in ("continuations", "phase", "done", "pending"):
            self.assertEqual(answer["continuation"][field],
                             expected["continuation"][field], field)
        self.assertTrue(grade["continuation"]["counts_held"])
        self.assertFalse(grade["continuation"]["indexes_held"])
        self.assertFalse(grade["checks"]["continuation_state"])
        self.assertEqual(grade["continuation"]["expected_indexes"]["done"], [0])
        self.assertEqual(grade["continuation"]["observed_indexes"]["done"], [1])


class Fix2PreflightAllowRules(RunnerCase):
    """The narrow second fix, item C: an acceptance never covers a failed allow rule."""

    setups = ("opencode",)
    preflight_accepted = False

    def record_preflight(self, allow, separated=False, accepted=True):
        campaign = runner.Campaign(self.campaign)
        document = {"separated": separated, "accepted_unseparated": accepted, "rows": [],
                    "not_separated": [] if separated else ["opencode"]}
        if allow is not None:
            document["allow_rules"] = allow
        runner.write_json(os.path.join(campaign.records("read-boundary"),
                                       "preflight-check.json"), document)
        return campaign

    FOREIGN = {"ok": False, "rows": [], "homes_written_for_another_campaign": [
        {"setup": "opencode", "home": "available",
         "config": "/some/home/xdg-config/opencode/opencode.json",
         "present": True, "covers_this_campaigns_scratch_root": False,
         "carries_allow_rules_for": ["/some/other/campaign/tmp/**"]}]}

    def test_a_failed_allow_rule_refuses_every_launch(self):
        """Her failed_allow_rules case: the preflight refused, the launch proceeded."""
        campaign = self.record_preflight(self.FOREIGN)
        state = runner.preflight_state(campaign)
        self.assertTrue(state["accepted_unseparated"])
        self.assertFalse(state["allow_rules_ok"])
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "a trial")
        message = str(caught.exception)
        self.assertIn("allow-rule preflight", message)
        self.assertIn("opencode/available", message)
        self.assertIn("/some/other/campaign/tmp/**", message)
        self.assertIn("install", message)
        self.assertIn("accept-unseparated accepts only", message)

    def test_the_launch_itself_is_refused(self):
        self.record_preflight(self.FOREIGN)
        tid = runner.trial_id("opencode", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("opencode")])
        self.assertEqual(got.returncode, 2, got.stdout[-800:])
        self.assertIn("allow-rule preflight", got.stderr)

    def test_a_passed_allow_rule_still_launches(self):
        campaign = self.record_preflight({"ok": True, "rows": [],
                                          "homes_written_for_another_campaign": []})
        state = runner.require_preflight(campaign, "a trial")
        self.assertTrue(state["allow_rules_checked"])
        self.assertTrue(state["allow_rules_ok"])

    def test_a_record_with_no_allow_rules_key_is_not_checked(self):
        """The older record shape: `.get("ok", True)` read it as passing."""
        campaign = self.record_preflight(None)
        state = runner.preflight_state(campaign)
        self.assertFalse(state["allow_rules_checked"])
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "a trial")
        message = str(caught.exception)
        self.assertIn("predates the allow-rule check", message)
        self.assertIn("never covers an unchecked allow rule", message)

    def test_the_acceptance_says_what_it_does_not_cover(self):
        got = cli(["preflight", "--campaign", self.campaign, "--accept-unseparated"])
        said = got.stdout + got.stderr
        self.assertIn("never covers a failed or unchecked allow rule", said)


class FixItem2Separation(RunnerCase):
    """Item 2(a)-(d): the preflight gate, the exclusion, the report, the listing."""

    # the gate's own tests build a campaign with no preflight record
    preflight_accepted = False

    def test_a_listing_of_another_trials_path_is_not_a_read_of_contents(self):
        """Her probe: a successful `ls` naming another trial's result path."""
        campaign = runner.Campaign(self.campaign)
        foreign = os.path.join(campaign.trials, "other", "result.json")
        record = os.path.join(self.scratch, "listing")
        runner.ensure_dir(os.path.join(record, "workspace"))
        command = {"workspace": os.path.join(record, "workspace"),
                   "run_dir": os.path.join(record, "run"), "opaque_tree": record,
                   "setup": "codex", "case": testlib.CASE, "condition": "available"}
        runner.write_json(os.path.join(record, "command.json"), command)
        jsonl(os.path.join(record, "harness", "rollout.jsonl"),
              [{"payload": {"type": "function_call", "name": "exec_command", "call_id": "a",
                            "arguments": json.dumps({"cmd": "ls " + foreign})}},
               {"payload": {"type": "function_call_output", "call_id": "a",
                            "output": json.dumps({"exit_code": 0, "output": foreign})}}])
        witnesses = runner.trace_witnesses(campaign, record, command)
        verdict = runner.comparison_evidence(campaign, record, witnesses, command)
        self.assertTrue(verdict["usable"])
        self.assertEqual(verdict["completed_foreign_reads"], 0)
        self.assertEqual(verdict["foreign_paths_named_but_not_read"][0]["operation"],
                         "listing")

    def test_a_completed_read_of_contents_still_excludes_the_trial(self):
        campaign = runner.Campaign(self.campaign)
        foreign = os.path.join(campaign.trials, "other", "result.json")
        record = os.path.join(self.scratch, "content-read")
        runner.ensure_dir(os.path.join(record, "workspace"))
        command = {"workspace": os.path.join(record, "workspace"),
                   "run_dir": os.path.join(record, "run"), "opaque_tree": record,
                   "setup": "codex", "case": testlib.CASE, "condition": "available"}
        runner.write_json(os.path.join(record, "command.json"), command)
        jsonl(os.path.join(record, "harness", "rollout.jsonl"),
              [{"payload": {"type": "function_call", "name": "exec_command", "call_id": "a",
                            "arguments": json.dumps({"cmd": "cat " + foreign})}},
               {"payload": {"type": "function_call_output", "call_id": "a",
                            "output": json.dumps({"exit_code": 0, "output": "{}"})}}])
        witnesses = runner.trace_witnesses(campaign, record, command)
        verdict = runner.comparison_evidence(campaign, record, witnesses, command)
        self.assertFalse(verdict["usable"])
        self.assertEqual(verdict["completed_reads_of_contents"][0]["operation"],
                         "read of contents")

    def test_comparison_evidence_is_a_condition_of_the_grade(self):
        source = runner.read_text(testlib.RUNNER, "")
        block = source[source.index('    checks = {'):source.index('    grade["checks"]')]
        self.assertIn('"usable_as_comparison_evidence": grade["comparison_evidence"]["usable"]',
                      block)

    def test_every_launch_refuses_without_a_preflight_record(self):
        tid = runner.trial_id("claude-code", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("read-boundary preflight", got.stderr)
        self.assertIn("preflight --campaign", got.stderr)

    def test_an_accepted_preflight_lets_a_launch_run(self):
        accepted = cli(["preflight", "--campaign", self.campaign, "--accept-unseparated"])
        self.assertEqual(accepted.returncode, 0, accepted.stderr[-800:])
        state = runner.preflight_state(runner.Campaign(self.campaign))
        self.assertTrue(state["accepted_unseparated"])
        tid = runner.trial_id("claude-code", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])

    def test_the_report_carries_the_package_limit_and_the_separation_state(self):
        campaign = runner.Campaign(self.campaign)
        campaign.append_jsonl(campaign.trials_jsonl,
                              {"id": "a", "attempt": 0, "status": "complete", "cost": 0.0,
                               "wall": 1.0})
        document = parse_stdout(cli(["report", "--campaign", self.campaign]))
        table = runner.read_text(document["table_md"], "")
        self.assertIn("NO PREFLIGHT RECORD", table)
        self.assertIn("benefit of the WHOLE PACKAGE", table)
        skeleton = runner.read_text(
            os.path.join(document["tables_dir"], "report-skeleton.md"), "")
        self.assertIn("never of instruction text alone", skeleton)
        self.assertIn("rejected as comparison evidence", skeleton)


class FixItem5Qualification(RunnerCase):
    """NEW BLOCKER 2: qualification needs a completed, witnessed manual-only trial."""

    GUARD = {"enforced": True, "guard": {"runner_closes_the_station": True},
             "stations": [{"applied": True, "path": "/a/station"}],
             "roots_searched": ["/a"]}

    def test_a_provider_failed_manual_only_launch_does_not_qualify(self):
        """Her stand-in: one failed launch, no completed session, no delivered station."""
        rows = [{"trial": "routing-codex-MANUAL-ONLY-PROBE-r1", "attempt": 0,
                 "activated_manual_only_probe": False, "completed_session": False,
                 "provider_failure": {"why": "the launch failed"},
                 "manual_only_guard": self.GUARD}]
        verdict = runner._manual_only_qualification(rows)
        self.assertFalse(verdict["qualified_for_the_catalog_requirement"])
        self.assertEqual(verdict["completed_sessions"], 0)
        self.assertIn("never ran", verdict["why"])

    def test_a_completed_guarded_non_selection_qualifies(self):
        rows = [{"trial": "routing-opencode-MANUAL-ONLY-PROBE-r1", "attempt": 0,
                 "activated_manual_only_probe": False, "completed_session": True,
                 "provider_failure": None, "manual_only_guard": self.GUARD}]
        verdict = runner._manual_only_qualification(rows)
        self.assertTrue(verdict["qualified_for_the_catalog_requirement"])
        self.assertEqual(verdict["witnessed_non_selections"], 1)

    def test_a_completed_session_with_no_guard_applied_does_not_qualify(self):
        rows = [{"trial": "t", "attempt": 0, "activated_manual_only_probe": False,
                 "completed_session": True, "provider_failure": None,
                 "manual_only_guard": {"enforced": False, "guard": {}, "stations": []}}]
        verdict = runner._manual_only_qualification(rows)
        self.assertFalse(verdict["qualified_for_the_catalog_requirement"])
        self.assertIn("no guard was recorded as applied", verdict["why"])

    def test_a_selected_station_never_qualifies(self):
        rows = [{"trial": "t", "attempt": 0, "activated_manual_only_probe": True,
                 "completed_session": True, "provider_failure": None,
                 "manual_only_guard": self.GUARD}]
        self.assertFalse(runner._manual_only_qualification(
            rows)["qualified_for_the_catalog_requirement"])

    def test_the_score_names_the_roots_the_guard_covered_per_attempt(self):
        rows = [{"trial": "t", "attempt": 0, "activated_manual_only_probe": False,
                 "completed_session": True, "provider_failure": None,
                 "manual_only_guard": dict(self.GUARD,
                                           roots_beyond_the_campaign="the checkout")}]
        verdict = runner._manual_only_qualification(rows)
        coverage = verdict["guard_coverage_per_attempt"][0]
        self.assertEqual(coverage["roots_searched"], ["/a"])
        self.assertEqual(coverage["roots_beyond_the_campaign"], "the checkout")
        self.assertEqual(coverage["stations_closed"], ["/a/station"])


class FixItem7RetainedTimeout(RunnerCase):
    """Item 7: a replayed exit-124 row is relabelled in the derived report."""

    def test_a_retained_exit_124_row_is_derived_as_a_timeout(self):
        campaign = runner.Campaign(self.campaign)
        campaign.append_jsonl(campaign.trials_jsonl,
                              {"id": "old", "attempt": 0, "status": "launch_failed",
                               "exit": 124, "cost": 0.0, "wall": 306.0})
        document = parse_stdout(cli(["report", "--campaign", self.campaign]))
        table = runner.read_json(document["table_json"])
        self.assertEqual(sum(r["timed_out"] for r in table["table"]), 1)
        self.assertEqual(sum(r["launch_failed"] for r in table["table"]), 0)
        relabelled = table["relabelled_from_the_retained_status"]
        self.assertEqual(len(relabelled), 1)
        self.assertEqual(relabelled[0]["retained_status"], "launch_failed")
        self.assertEqual(relabelled[0]["derived_status"], "timed_out")
        self.assertIn("relabelled from their retained status",
                      runner.read_text(document["table_md"], ""))

    def test_the_retained_ledger_row_is_never_edited(self):
        campaign = runner.Campaign(self.campaign)
        campaign.append_jsonl(campaign.trials_jsonl,
                              {"id": "old", "attempt": 0, "status": "launch_failed",
                               "exit": 124, "cost": 0.0, "wall": 306.0})
        before = runner.file_sha256(campaign.trials_jsonl)
        cli(["report", "--campaign", self.campaign])
        self.assertEqual(runner.file_sha256(campaign.trials_jsonl), before)


class FixItem4Compaction(RunnerCase):
    """NEW MAJOR 4: the ordering witness, from the real resumed turn."""

    setups = ("codex",)

    def rollout(self, name, rows):
        out = os.path.join(self.scratch, "compaction-%s" % name)
        runner.ensure_dir(out)
        jsonl(os.path.join(out, "rollout.jsonl"), rows)
        return out

    def setup_for(self):
        return runner.setup_for(runner.Campaign(self.campaign), self.plan_document, "codex")

    RESUME = "resume the recheck run standin-run in /r"

    def test_her_four_line_probe_reads_not_ok(self):
        """Resumed user turn, work, compaction, then an assistant line naming the run."""
        out = self.rollout("late", [
            {"payload": {"type": "message", "role": "user", "content": self.RESUME}},
            {"payload": {"type": "function_call", "call_id": "c",
                         "command": "printf resumed-work"}},
            {"payload": {"type": "compacted"}},
            {"payload": {"type": "message", "role": "assistant",
                         "content": "Finished standin-run"}}])
        witness = runner.compaction_witness(self.setup_for(), out, resume_text=self.RESUME)
        self.assertFalse(witness["ok"])
        self.assertEqual(witness["resumed_turn_line"], 1)
        self.assertEqual(witness["first_resumed_work_line"], 2)
        self.assertFalse(witness["ordering_witness"]["in_order"])

    def test_the_three_lines_in_order_are_the_witness(self):
        out = self.rollout("ordered", [
            {"payload": {"type": "function_call", "call_id": "c0",
                         "command": "the first session's work"}},
            {"payload": {"type": "compacted"}},
            {"payload": {"type": "message", "role": "user", "content": self.RESUME}},
            {"payload": {"type": "function_call", "call_id": "c1",
                         "command": "the resumed work"}}])
        witness = runner.compaction_witness(self.setup_for(), out, resume_text=self.RESUME)
        self.assertTrue(witness["ok"])
        self.assertEqual(witness["ordering_witness"],
                         {"compaction_line": 2, "resumed_turn_line": 3,
                          "first_resumed_tool_line": 4, "in_order": True,
                          "why": "compaction 2 < resumed turn 3 < first resumed tool 4"})

    def test_an_assistant_line_naming_the_run_is_not_the_resumed_turn(self):
        records = list(enumerate([
            {"payload": {"type": "message", "role": "user", "content": self.RESUME}},
            {"payload": {"type": "message", "role": "assistant",
                         "content": "Finished standin-run"}}], 1))
        line, how = runner._resumed_turn_line(records, self.RESUME)
        self.assertEqual(line, 1)
        self.assertIn("USER turn", how)

    def test_no_resumed_work_is_not_a_pass(self):
        out = self.rollout("no-work", [
            {"payload": {"type": "compacted"}},
            {"payload": {"type": "message", "role": "user", "content": self.RESUME}}])
        witness = runner.compaction_witness(self.setup_for(), out, resume_text=self.RESUME)
        self.assertFalse(witness["ok"])
        self.assertIn("no resumed tool call", witness["ordering_witness"]["why"])


if __name__ == "__main__":
    unittest.main()
