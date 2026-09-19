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
import sys
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
                              "error": "permission requested: external_directory "
                                       "(/Users/nobody/**); auto-rejecting",
                              "input": {"filePath": "/Users/nobody/outside.txt"}}}},
                # E11-41 R2: an `error` with no refusal marker is a completed ERROR, not a
                # refusal — the conflation read2 named. It is still not a write.
                {"type": "tool_use", "part": {
                    "type": "tool", "tool": "write", "callID": "b2",
                    "state": {"status": "error", "error": "ENOSPC: no space left on device",
                              "input": {"filePath": "/Users/nobody/errored.txt"}}}},
            ],
        })
        campaign = runner.Campaign(self.campaign)
        witnesses = runner.trace_witnesses(campaign, record, command)
        self.assertEqual(witnesses["writes_outside"], [])
        self.assertTrue(witnesses["refused_actions"])
        statuses = {a.get("call_id") or a.get("line"): a.get("status")
                    for a in runner.native_actions(record)}
        self.assertIn("refused", statuses.values())
        self.assertIn("error", statuses.values())

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

        Astra's gap 7: the grade no longer comes back from `consumer`, which leaves the
        attempt ungraded on purpose. The first grade is written by the deferred path, and it
        is the same document this test always read.
        """
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        got = cli(["consumer", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        document = parse_stdout(got)
        self.assertIsNone(document["consumer_grade"])
        self.assertFalse(document["graded"])
        graded = cli(["consumer", "--campaign", self.campaign, "--regrade", "--all"])
        self.assertEqual(graded.returncode, 0, graded.stderr[-3000:])
        grade = runner.read_json(os.path.join(document["record"], "consumer-grade.json"))
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
    """NEW BLOCKER 1, REVERSED by E11-46 R5: a revision REPLACES, and is never numbered.

    The original rule made a rerun of one revision take the next free `-N` so that no derived
    measurement was ever overwritten. E11-45's replay is the record of why that was wrong for a
    NAMED revision: the rerun wrote `grade.e11-round2-1-1.json` and `-2.json` beside the stale
    `grade.e11-round2-1.json`, and the control room read the stale one, because the canonical
    name is where every reader looks. Both tests below are amended, not deleted: what they
    assert is inverted and the reason is named here.
    """

    def test_a_repeated_revision_replaces_that_revision_s_file(self):
        record = os.path.join(self.scratch, "trial")
        runner.ensure_dir(record)
        first = runner.derived_grade_path(record, "review-derived")
        self.assertTrue(first.endswith("grade.review-derived.json"))
        runner.write_json(first, {"first": True})
        second = runner.derived_grade_path(record, "review-derived")
        self.assertEqual(first, second, "one revision name owns exactly one file")
        runner.write_json(second, {"second": True})
        self.assertEqual(runner.read_json(first), {"second": True})
        self.assertEqual(
            sorted(n for n in os.listdir(record) if n.startswith("grade.")),
            ["grade.review-derived.json"], "a revision never spills a numbered file")

    def test_a_second_measurement_takes_a_second_name(self):
        """The way to keep two: name them apart. Nothing is lost, and nothing is ambiguous."""
        record = os.path.join(self.scratch, "claimed")
        runner.ensure_dir(record)
        one = runner.derived_grade_path(record, "rev")
        two = runner.derived_grade_path(record, "rev-b")
        runner.write_json(one, {"a": True})
        runner.write_json(two, {"b": True})
        self.assertNotEqual(one, two)
        self.assertEqual(runner.read_json(one), {"a": True})


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


class Fix4WritableRunLeaf(RunnerCase):
    """Tony's ruling E11-26: a session must be able to write its own run directory.

    The rerun's every Codex comparison trial ended `no_result` in about 150 seconds, the
    harness refusing the skill's first write ("patch rejected: writing outside of the
    project"). The run directory is the fixture's own `run/` leaf, a SIBLING of the workspace
    (E10-54(a)); Codex's sandbox writes cwd, its `--add-dir` roots and `$TMPDIR`. Until E11-7
    item 2 `TMPDIR` was `<campaign>/tmp`, which CONTAINED the leaf by accident of layout; a
    per-trial scratch (`<opaque tree>/scratch`, a sibling of `fixture/`) took that away, and
    nothing checked.
    """

    setups = ("codex", "claude-code", "opencode")

    def layout(self, leaf="tree"):
        """The real shape: `<tree>/fixture/<12 hex>/{workspace,run}` beside `<tree>/scratch`."""
        tree = os.path.join(self.scratch, leaf)
        case_dir = os.path.join(tree, "fixture", "75d13f306773")
        workspace = os.path.join(case_dir, "workspace")
        run_dir = os.path.join(case_dir, "run")
        scratch = os.path.join(tree, "scratch")
        for path in (workspace, run_dir, scratch):
            runner.ensure_dir(path)
        return runner.Campaign(self.campaign), case_dir, workspace, run_dir, scratch

    def test_a_run_leaf_outside_every_root_refuses_the_codex_launch(self):
        """The stopped rerun's configuration, checked instead of launched."""
        campaign, _case, workspace, run_dir, scratch = self.layout("refused")
        setup = runner.setup_for(campaign, self.plan_document, "codex")
        record = runner.writable_roots_record(setup, "available", workspace, run_dir,
                                              scratch, [])
        self.assertFalse(record["run_dir_is_writable"])
        self.assertEqual(record["run_dir_inside"], [])
        with self.assertRaises(runner.Usage) as caught:
            runner.require_writable_run_dir(campaign, setup, "available", workspace, run_dir,
                                            scratch, [], "the comparison trial t")
        message = str(caught.exception)
        self.assertIn(run_dir, message)
        self.assertIn("codex", message)
        self.assertIn("outside every root", message)
        # AMENDED (E11-46 R5): this call passes no trial, so the record keeps the free-text
        # name; the assertion follows the runner's own naming rule either way.
        written = os.path.join(campaign.records("writable-roots"),
                               "%s.json" % runner.writable_roots_record_name(
                                   "the comparison trial t"))
        self.assertTrue(os.path.isfile(written))
        self.assertFalse(runner.read_json(written)["run_dir_is_writable"])

    def test_naming_the_case_directory_makes_the_run_leaf_writable(self):
        campaign, case_dir, workspace, run_dir, scratch = self.layout("named")
        setup = runner.setup_for(campaign, self.plan_document, "codex")
        record = runner.require_writable_run_dir(campaign, setup, "available", workspace,
                                                 run_dir, scratch, [case_dir],
                                                 "the comparison trial u")
        self.assertTrue(record["run_dir_is_writable"])
        self.assertEqual(record["run_dir_inside"], [case_dir])

    def test_the_codex_roots_are_the_ones_its_sandbox_gets(self):
        campaign, case_dir, workspace, run_dir, scratch = self.layout("codex-roots")
        setup = runner.setup_for(campaign, self.plan_document, "codex")
        record = setup.writable_roots("available", workspace, scratch, extra=[case_dir])
        roots = [row["root"] for row in record["roots"]]
        self.assertIn(workspace, roots)
        self.assertIn(scratch, roots)
        self.assertIn(os.path.join(setup.home("available"), "child"), roots)
        self.assertIn(case_dir, roots)
        self.assertIn("exclude_tmpdir_env_var", record["sandbox"])

    def test_the_opencode_roots_come_from_its_own_allow_rule(self):
        campaign, _case, workspace, _run, scratch = self.layout("opencode-roots")
        setup = runner.setup_for(campaign, self.plan_document, "opencode")
        config = os.path.join(setup.home("available"), "xdg-config", "opencode",
                              "opencode.json")
        allowed = os.path.join(self.scratch, "allowed-root")
        runner.ensure_dir(allowed)
        runner.write_json(config, {"permission": {"external_directory": {
            allowed + "/**": "allow"}}})
        record = setup.writable_roots("available", workspace, scratch)
        self.assertIn(allowed, [row["root"] for row in record["roots"]])

    def test_the_codex_launch_is_handed_the_case_directory(self):
        """End to end on the fake launcher: the flag reaches the launcher's own argv."""
        tid = runner.trial_id("codex", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(got.returncode, 0, got.stderr[-2500:])
        record = runner.Campaign(self.campaign).trial_dir(tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        case_dir = os.path.dirname(command["run_dir"])
        argv = runner.read_json(os.path.join(record, "harness", "env-names.json"))["argv"]
        self.assertIn("--writable", argv)
        self.assertIn(case_dir, argv)
        # AMENDED (E11-46 R5): the record is named by trial and attempt now, not by a slug of
        # the free text, so a rerun no longer overwrites the first attempt's record.
        roots = runner.read_json(os.path.join(
            runner.Campaign(self.campaign).records("writable-roots"),
            "%s.json" % runner.writable_roots_record_name("", tid, 0)))
        self.assertTrue(roots["run_dir_is_writable"])
        self.assertEqual(roots["run_dir_inside"], [case_dir])

    def test_the_claude_code_launch_names_it_too(self):
        """Its run leaf is outside `${TMPDIR}/runs` as well; only its permission mode hid it."""
        tid = runner.trial_id("claude-code", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr[-2500:])
        record = runner.Campaign(self.campaign).trial_dir(tid)
        command = runner.read_json(os.path.join(record, "command.json"))
        argv = runner.read_json(os.path.join(record, "harness", "env-names.json"))["argv"]
        self.assertIn("--writable", argv)
        self.assertIn(os.path.dirname(command["run_dir"]), argv)

    def test_two_lanes_creating_the_record_directory_at_once_do_not_collide(self):
        """`ensure_dir` was check-then-act, and the guard made two lanes race for it.

        The per-trial writable-roots record is the first thing parallel lanes write into the
        same NEW directory, and the loser raised FileExistsError and stopped its whole lane
        (seen under 3.12 in test_e10_68's two-lane campaign).
        """
        target = os.path.join(self.scratch, "racing", "writable-roots")
        real_isdir = os.path.isdir
        os.makedirs(target)                      # the winner already made it

        stale = [True]

        def blind(path):
            """Only the loser's OWN check is stale, the way a real race makes it.

            `os.makedirs(exist_ok=True)` recovers by asking `isdir` again after `mkdir`
            raises, so a stub that lies every time would break the recovery instead of
            testing it.
            """
            if path == target and stale[0]:
                stale[0] = False
                return False
            return real_isdir(path)

        os.path.isdir = blind
        try:
            runner.ensure_dir(target)            # must not raise
        finally:
            os.path.isdir = real_isdir
        self.assertTrue(os.path.isdir(target))

    # NEW MINOR D-T: the old test here asserted ["run", "workspace"] against a layout it had
    # built itself, so it proved nothing about a staged fixture. It is replaced by
    # Fix5EveryLaunchNamesTheRoot's two real-fixture tests.


class Fix5EveryLaunchNamesTheRoot(RunnerCase):
    """Astra's recheck4: D PARTLY. Only two of the runner's launch sites named the run leaf.

    The comparison trial and the consumer did both; the FIRST continuation launch passed no
    root and called no guard, the handoff resume passed the root without the guard, and both
    compaction resumes built their argv by hand and named nothing. A Codex continuation would
    have ended `no_result` exactly as the comparison trials did on 8b6beda.
    """

    setups = ("claude-code", "codex", "opencode")
    cases = (testlib.TWO_ITEM_CASE,)

    def restore_later(self, path):
        """The pilot homes are SHARED between tests: put this one back as it was."""
        before = runner.read_text(path, None)

        def restore():
            if before is None:
                if os.path.isfile(path):
                    os.remove(path)
            else:
                runner.write_text(path, before)
        self.addCleanup(restore)

    def records_dir(self):
        return runner.Campaign(self.campaign).records("writable-roots")

    def record_for(self, what, trial=None, attempt=0, half=None):
        """AMENDED (E11-46 R5): the record is named by trial, attempt and half.

        It used to be a slug of the free-text `what`, under which a RERUN overwrote the first
        attempt's record and the write-fence proof's twenty probes left one file. The helper
        asks the runner for the name rather than spelling it again here.
        """
        path = os.path.join(self.records_dir(), "%s.json" % runner.writable_roots_record_name(
            what, trial, attempt, half))
        self.assertTrue(os.path.isfile(path), sorted(os.listdir(self.records_dir())))
        return runner.read_json(path)

    def drive(self, harness, kind, launcher=None):
        """One continuation trial. The compaction path needs a session id to resume, which
        only the cut stub plants, so those tests hand one in."""
        tid = runner.continuation_trial_id(harness, testlib.TWO_ITEM_CASE, kind, 1)
        got = cli(["continuation", "--campaign", self.campaign, tid,
                   "--fake-launcher", launcher or self.fake_launcher(harness)])
        self.assertIn(got.returncode, (0, 1), got.stderr[-2500:])
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        return tid, command

    def launcher_argv(self, tid, half):
        path = os.path.join(self.campaign, "trials", tid, "harness-%s" % half,
                            "env-names.json")
        self.assertTrue(os.path.isfile(path), path)
        return runner.read_json(path)["argv"]

    def case_dir_of(self, command):
        return os.path.dirname(command["run_dir"])

    # ---- (a) the first continuation launch
    def test_the_first_continuation_launch_names_the_root_and_is_guarded(self):
        tid, command = self.drive("claude-code", "handoff")
        case_dir = self.case_dir_of(command)
        argv = self.launcher_argv(tid, "first")
        self.assertIn("--writable", argv)
        self.assertIn(case_dir, argv)
        record = self.record_for("", tid, 0, "first")
        self.assertTrue(record["run_dir_is_writable"])
        self.assertEqual(record["run_dir_inside"], [case_dir])

    # ---- (b) the handoff resume
    def test_the_handoff_resume_is_guarded_too(self):
        tid, command = self.drive("claude-code", "handoff")
        case_dir = self.case_dir_of(command)
        record = self.record_for("", tid, 0, "second-handoff")
        self.assertTrue(record["run_dir_is_writable"])
        self.assertEqual(record["run_dir_inside"], [case_dir])
        self.assertIn(case_dir, self.launcher_argv(tid, "second"))

    # ---- (c) the two compaction resumes
    def test_the_codex_compaction_resume_names_the_root_before_resume(self):
        """E10-35: `--add-dir` is an `exec` option and must precede the `resume` subcommand.

        Driven the way Astra's `paths.py` drives it: the codex resume needs a thread id the
        fake launcher never mints, so the argv is captured at the process boundary instead.
        """
        import argparse
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, self.plan_document, "codex")
        tree = os.path.join(self.scratch, "codex-resume")
        case_dir = os.path.join(tree, "fixture", "75d13f306773")
        workspace, run_dir = os.path.join(case_dir, "workspace"), os.path.join(case_dir, "run")
        for path in (workspace, run_dir):
            runner.ensure_dir(path)
        prompt = os.path.join(self.scratch, "resume.txt")
        runner.write_text(prompt, "Continue the local test.\n")

        class Captured(Exception):
            pass

        seen = {}

        def capture(argv, **kwargs):
            seen["argv"] = argv
            raise Captured()

        args = argparse.Namespace(trial="cont-codex-probe-r1", attempt=0, compact_tokens=2000)
        real = runner.run_cmd
        runner.run_cmd = capture
        try:
            runner._compaction_resume(campaign, setup, {"session": "local-test-session"},
                                      prompt, workspace, os.path.join(self.scratch, "out"),
                                      1, args, run_dir=run_dir)
        except Captured:
            pass
        finally:
            runner.run_cmd = real
        argv = seen["argv"]
        self.assertIn(case_dir, argv)
        self.assertEqual(argv[argv.index(case_dir) - 1], "--add-dir")
        self.assertLess(argv.index(case_dir), argv.index("resume"))
        record = self.record_for("", "cont-codex-probe-r1", 0, "second-compaction")
        self.assertTrue(record["run_dir_is_writable"])
        self.assertEqual(record["run_dir_inside"], [case_dir])

    def test_the_claude_code_compaction_resume_names_the_root(self):
        tid, command = self.drive("claude-code", "compaction",
                                  launcher=self.cut_stub("fix5-claude-code"))
        case_dir = self.case_dir_of(command)
        self.record_for("", tid, 0, "second-compaction")
        argv = ((command.get("compaction") or {}).get("attempts") or [{}])[0].get("argv") or []
        self.assertIn(case_dir, argv)
        self.assertEqual(argv[argv.index(case_dir) - 1], "--add-dir")

    def test_every_launch_site_goes_through_the_one_helper(self):
        """A fifth launch site cannot skip the check by forgetting to call it."""
        import ast
        with open(os.path.join(os.path.dirname(runner.__file__), "runner.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        wanted = {"_one_trial", "do_continuation", "_launch_and_cut", "_compaction_resume",
                  "do_consumer"}
        seen = {}
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                seen[node.name] = [c.lineno for c in ast.walk(node)
                                   if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                                   and c.func.id in ("guarded_launch_roots",
                                                     "require_writable_run_dir")]
        self.assertEqual(sorted(seen), sorted(wanted))
        for name, calls in seen.items():
            self.assertTrue(calls, "%s calls no guard" % name)

    # ---- NEW MAJOR D-G: a root the launcher never forwards is not a root
    def test_a_root_opencode_never_receives_is_not_counted(self):
        """Her opencode-guard.py: with `allow rules: []` the guard said writable anyway."""
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, self.plan_document, "opencode")
        config = os.path.join(setup.home("available"), "xdg-config", "opencode",
                              "opencode.json")
        self.restore_later(config)
        runner.write_json(config, {"permission": {"external_directory": {}}})
        tree = os.path.join(self.scratch, "op-guard")
        case_dir = os.path.join(tree, "fixture", "75d13f306773")
        workspace, run_dir = os.path.join(case_dir, "workspace"), os.path.join(case_dir, "run")
        scratch = os.path.join(tree, "scratch")
        for path in (workspace, run_dir, scratch):
            runner.ensure_dir(path)
        record = runner.writable_roots_record(setup, "available", workspace, run_dir, scratch,
                                              [case_dir])
        self.assertFalse(record["forwards_writable"])
        self.assertEqual(record["roots_named_but_not_forwarded"], [case_dir])
        self.assertNotIn(case_dir, [row["root"] for row in record["roots"]])
        self.assertFalse(record["run_dir_is_writable"])
        with self.assertRaises(runner.Usage):
            runner.require_writable_run_dir(campaign, setup, "available", workspace, run_dir,
                                            scratch, [case_dir], "no-allow-rule")
        self.assertFalse(self.record_for("no-allow-rule")["run_dir_is_writable"])

    def test_the_harnesses_that_do_forward_it_still_count_it(self):
        campaign = runner.Campaign(self.campaign)
        for name in ("codex", "claude-code"):
            setup = runner.setup_for(campaign, self.plan_document, name)
            self.assertTrue(setup.forwards_writable, name)
            record = setup.writable_roots("available", "/w", "/s", extra=["/case"])
            self.assertIn("/case", [row["root"] for row in record["roots"]], name)
            self.assertEqual(record["roots_named_but_not_forwarded"], [])

    def test_an_opencode_launch_with_its_allow_rule_still_passes(self):
        """The rule is how this harness reaches a run leaf, and it is unchanged."""
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, self.plan_document, "opencode")
        tree = os.path.join(self.scratch, "op-allowed")
        case_dir = os.path.join(tree, "fixture", "75d13f306773")
        workspace, run_dir = os.path.join(case_dir, "workspace"), os.path.join(case_dir, "run")
        scratch = os.path.join(tree, "scratch")
        for path in (workspace, run_dir, scratch):
            runner.ensure_dir(path)
        config = os.path.join(setup.home("available"), "xdg-config", "opencode",
                              "opencode.json")
        self.restore_later(config)
        runner.write_json(config, {"permission": {"external_directory": {tree + "/**": "allow"}}})
        record = runner.writable_roots_record(setup, "available", workspace, run_dir, scratch,
                                              [case_dir])
        self.assertTrue(record["run_dir_is_writable"])
        self.assertEqual(record["run_dir_inside"], [tree])

    # ---- NEW MINOR D-T: the isolation claim, against a REAL staged layout
    def test_a_real_case_directory_holds_only_its_own_trials_files(self):
        campaign = runner.Campaign(self.campaign)
        tid = runner.trial_id("codex", testlib.CASE, "available", 1)
        tree = campaign.opaque_tree(tid, 0)
        fixture = runner.build_fixture(campaign, testlib.CASE,
                                       os.path.join(tree, "fixture"))
        case_dir = fixture["case_dir"]
        run_dir = runner.trial_run_dir(fixture)
        self.assertEqual(os.path.dirname(run_dir), case_dir)
        # what `build.py --opaque` really lays out, not a layout this test invented
        self.assertEqual(sorted(os.listdir(case_dir)),
                         ["input.json", "manifest.json", "run", "workspace"])
        self.assertEqual(os.path.basename(case_dir), runner.re.sub(
            r"[^0-9a-f]", "", os.path.basename(case_dir)))
        self.assertEqual(len(os.path.basename(case_dir)), 12)
        # and nothing of any other trial is under it
        other = campaign.opaque_tree(runner.trial_id("codex", testlib.CASE, "absent", 1), 0)
        self.assertFalse(runner.path_contains(case_dir, other))

    def test_a_real_consumer_pair_root_holds_only_that_pair(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(self.scratch, "fix5-producer")
        runner.ensure_dir(os.path.join(record, "workspace"))
        runner.write_json(os.path.join(record, "result.json"), {"items": [], "cards": []})
        runner.write_json(os.path.join(record, "run", "checkpoint.json"),
                          {"phase": "completed", "continuations": 0, "scope": {"items": []}})
        producer = {"record": record, "trial": "fix5-producer",
                    "command": {"workspace": os.path.join(record, "workspace")}}
        pair = runner.stage_consumer_pair(campaign, producer,
                                          os.path.join(self.scratch, "fix5-pair"))
        root = os.path.dirname(pair["run_dir"])
        self.assertEqual(root, pair["pair_dir"])
        # what `stage_consumer_pair` really lays out: the pair's own input, the ONE producer's
        # copied records, the pair's run directory and the workspace it left
        self.assertEqual(sorted(os.listdir(root)),
                         ["input.json", "producer", "run", "workspace"])
        # the producer copy inside it is this pair's own, and the campaign's other records
        # are not under the named root
        self.assertTrue(runner.path_contains(root, pair["producer_dir"]))
        self.assertFalse(runner.path_contains(root, campaign.trials))


class Fix6EnforcementFollowsTheLaunch(RunnerCase):
    """Astra's recheck5: D still PARTLY on the two exceptions fix 5 introduced.

    D-F: `_compaction_resume` disabled the guard on `args.fake_launcher` — the FIRST half's
    flag — while its own argv is built from the real harness binary, so her probe reached the
    process boundary with `enforced: false` and an argv naming `opencode run ... --session`.
    D-U: a home with no `opencode.json` set `bounded: false`, and the refusal skipped it, so a
    REAL launch proceeded with `run_dir_is_writable: false`; she drove that launcher with a
    stand-in binary and an auth file and it never asks for `opencode.json`.
    """

    setups = ("opencode", "claude-code")
    cases = (testlib.TWO_ITEM_CASE,)

    def setUp(self):
        RunnerCase.setUp(self)
        self.campaign_object = runner.Campaign(self.campaign)
        self.setup = runner.setup_for(self.campaign_object, self.plan_document, "opencode")
        self.config = os.path.join(self.setup.home("available"), "xdg-config", "opencode",
                                   "opencode.json")
        before = runner.read_text(self.config, None)

        def restore():
            if before is None:
                if os.path.isfile(self.config):
                    os.remove(self.config)
            else:
                runner.write_text(self.config, before)
        self.addCleanup(restore)
        tree = os.path.join(self.scratch, "fix6")
        self.case_dir = os.path.join(tree, "fixture", "75d13f306773")
        self.workspace = os.path.join(self.case_dir, "workspace")
        self.run_dir = os.path.join(self.case_dir, "run")
        self.trial_scratch = os.path.join(tree, "scratch")
        for path in (self.workspace, self.run_dir, self.trial_scratch):
            runner.ensure_dir(path)
        self.prompt = os.path.join(self.scratch, "fix6-resume.txt")
        runner.write_text(self.prompt, "Continue the local test.\n")

    def stage_launcher(self, harness="opencode"):
        """The setup's OWN `launch.sh` in the stage, so a real launch resolves to it.

        `RunnerCase` stages empty setup directories; without the script the run stops at
        `Missing` (exit 3) before the guard is reached, and the refusal cannot be seen.
        """
        setup = (self.setup if harness == "opencode"
                 else runner.setup_for(self.campaign_object, self.plan_document, harness))
        path = os.path.join(setup.setup_dir, "launch.sh")
        runner.write_text(path, "#!/bin/sh\nexit 0\n")
        os.chmod(path, 0o755)
        return path

    def record_for(self, what, trial=None, attempt=0, half=None):
        """AMENDED with the same reason as the helper above (E11-46 R5)."""
        if trial:
            what = runner.writable_roots_record_name(what, trial, attempt, half)
        path = os.path.join(self.campaign_object.records("writable-roots"),
                            "%s.json" % __import__("re").sub(r"[^A-Za-z0-9_.-]", "-", what))
        self.assertTrue(os.path.isfile(path), path)
        return runner.read_json(path)

    def empty_config(self):
        """A config that EXISTS and grants nothing: her decision (a) bench."""
        runner.write_json(self.config, {"permission": {"external_directory": {}}})

    def no_config(self):
        if os.path.isfile(self.config):
            os.remove(self.config)

    # ---- the predicate itself
    def test_the_predicate_reads_the_executable_not_a_flag(self):
        own = self.stage_launcher()
        self.assertEqual(own, self.setup.script("launch.sh"))
        self.assertFalse(runner.launch_is_fake(self.setup, own))
        self.assertFalse(runner.launch_is_fake(self.setup, None))
        self.assertTrue(runner.launch_is_fake(self.setup,
                                              os.path.join(self.scratch, "stand-in.sh")))

    # ---- (a) D-F: the compaction resume names the real binary, so it is enforced
    def test_a_compaction_resume_is_enforced_even_when_the_first_half_ran_fake(self):
        """Her decision (a): only `fake_launcher` changed between the two runs."""
        import argparse
        self.empty_config()

        class Captured(Exception):
            pass

        seen = {}

        def capture(argv, **kwargs):
            seen["argv"] = argv
            raise Captured()

        outcomes = {}
        real = runner.run_cmd
        runner.run_cmd = capture
        try:
            for fake in (None, os.path.join(self.scratch, "fake-first-launcher.sh")):
                trial = "fix6-a-%s" % bool(fake)
                args = argparse.Namespace(trial=trial, attempt=0, compact_tokens=2000,
                                          fake_launcher=fake)
                seen.clear()
                outcome = "REACHED PROCESS BOUNDARY"
                try:
                    runner._compaction_resume(
                        self.campaign_object, self.setup, {"session": "local-test-session"},
                        self.prompt, self.workspace,
                        os.path.join(self.scratch, "a-%s" % bool(fake)), 1, args,
                        run_dir=self.run_dir)
                except runner.Usage:
                    outcome = "REFUSED"
                except Captured:
                    pass
                outcomes[bool(fake)] = (outcome, self.record_for(
                    "", trial, 0, "second-compaction"))
        finally:
            runner.run_cmd = real
        for fake_first_half, (outcome, record) in outcomes.items():
            self.assertEqual(outcome, "REFUSED", fake_first_half)
            self.assertTrue(record["enforced"], fake_first_half)
            self.assertFalse(record["run_dir_is_writable"], fake_first_half)
        self.assertNotIn("argv", seen)

    # ---- (b) a launch that really runs the fake executable is not enforced
    def test_a_resume_that_itself_runs_the_fake_executable_is_not_enforced(self):
        tid = runner.continuation_trial_id("claude-code", testlib.TWO_ITEM_CASE, "handoff", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertIn(got.returncode, (0, 1), got.stderr[-2000:])
        for half in ("first", "second-handoff"):
            record = self.record_for("", tid, 0, half)
            self.assertFalse(record["enforced"], half)
            self.assertIn("fake launcher", record["why_not_enforced"])

    # ---- (c) D-U: a real launch with no establishable root is refused
    def test_a_real_launch_on_a_config_less_home_is_refused(self):
        import argparse
        self.no_config()
        self.stage_launcher()          # a real launch resolves to the setup's own script
        args = argparse.Namespace(trial="fix6-c", attempt=0, poll_interval=0.1,
                                  fake_launcher=None)
        with self.assertRaises(runner.Usage) as caught:
            runner._launch_and_cut(self.campaign_object, self.setup, self.prompt,
                                   self.workspace,
                                   os.path.join(self.scratch, "c", "harness"),
                                   self.run_dir, 1, args)
        message = str(caught.exception)
        self.assertIn("cannot be established", message)
        self.assertIn("not installed", message)
        record = self.record_for("", "fix6-c", 0, "first")
        self.assertTrue(record["enforced"])
        self.assertFalse(record["bounded"])
        self.assertFalse(record["run_dir_is_writable"])
        self.assertIn("opencode.json", record["why_unbounded"])

    def test_that_refusal_is_exit_2_from_the_cli(self):
        """`Usage` is the runner's exit 2, the same shape as item C's allow-rule gate."""
        self.no_config()
        self.stage_launcher()
        tid = runner.continuation_trial_id("opencode", testlib.TWO_ITEM_CASE, "handoff", 1)
        got = cli(["continuation", "--campaign", self.campaign, tid])
        self.assertEqual(got.returncode, 2, got.stdout[-800:])
        self.assertIn("writability cannot be established", got.stderr)

    # ---- (d) the same home under the fake launcher proceeds
    def test_the_same_home_under_a_fake_launcher_proceeds(self):
        import argparse
        self.no_config()
        fake = os.path.join(self.scratch, "fake-launcher.sh")
        runner.write_text(fake, "#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        args = argparse.Namespace(trial="fix6-d", attempt=0, poll_interval=0.1,
                                  fake_launcher=fake)
        runner._launch_and_cut(self.campaign_object, self.setup, self.prompt, self.workspace,
                               os.path.join(self.scratch, "d", "harness"), self.run_dir, 1,
                               args)
        record = self.record_for("", "fix6-d", 0, "first")
        self.assertFalse(record["enforced"])
        self.assertFalse(record["bounded"])
        self.assertFalse(record["run_dir_is_writable"])
        self.assertIn("fake launcher", record["why_not_enforced"])


class Fix7QueueAndReaders(RunnerCase):
    """The rerun on 485e92a: 348 of 360 scheduled, and `grade --all` died on a sidecar.

    NEW MAJOR Q: `campaign_queue` built rows from `order`, `continuation_order`,
    `routing_order` and `manual_only_order` and never from `consumer_order`, while
    `_campaign_loop` already had a `consumer` branch. NEW MAJOR G: `capture_files` took every
    `launch-*.json` as an OpenCode verifier capture, so a pretty-printed
    `launch-<call>.record-call-flags.json` beside the capture was read line by line and the
    first string raised `AttributeError: 'str' object has no attribute 'get'`.
    """

    setups = ("claude-code", "codex")

    # ---- Q: the queue schedules the consumer trials
    def planned(self):
        """The plan document as `runner.py plan` writes it: with `consumer_order`.

        `testlib` builds its campaign document without that key (no test needed it before),
        so the order and the count are minted here exactly as `do_plan` mints them.
        """
        plan = dict(self.plan_document)
        plan["consumer_order"] = runner.consumer_order(plan)
        counts = dict(plan["counts"])
        counts["consumer"] = sum(len(v) for v in plan["consumer_order"].values())
        counts["total"] = (counts["comparison"] + counts["routing"] + counts["manual_only"]
                           + counts["continuation"] + counts["consumer"])
        plan["counts"] = counts
        return plan

    def test_the_queue_schedules_the_consumer_trials_last(self):
        campaign = runner.Campaign(self.campaign)
        plan = self.planned()
        self.assertTrue(plan.get("consumer_order"), "the test plan mints no consumer trials")
        queue = runner.campaign_queue(campaign, plan)
        kinds = [row["kind"] for row in queue]
        consumers = [row for row in queue if row["kind"] == "consumer"]
        planned = sorted(t for ids in plan["consumer_order"].values() for t in ids)
        self.assertEqual(sorted(row["id"] for row in consumers), planned)
        # after the routing rows: every producer must be recorded before a consumer runs
        self.assertGreater(min(i for i, k in enumerate(kinds) if k == "consumer"),
                           max(i for i, k in enumerate(kinds) if k == "routing"))
        for row in consumers:
            self.assertIn("state", row)
            self.assertIn("status", row)
            self.assertFalse(row["complete"])
            self.assertFalse(row["recorded"])

    def test_the_planned_count_equals_the_plans_total(self):
        campaign = runner.Campaign(self.campaign)
        plan = self.planned()
        self.assertEqual(len(runner.campaign_queue(campaign, plan)),
                         plan["counts"]["total"])

    def test_a_consumer_record_is_not_graded_as_a_comparison_trial(self):
        """A consequence of Q: `consumer-*` directories now exist on a finished root."""
        campaign = runner.Campaign(self.campaign)
        tid = "consumer-claude-code-to-codex-r1"
        runner.ensure_dir(campaign.trial_dir(tid))
        runner.write_json(os.path.join(campaign.trial_dir(tid), "command.json"),
                          {"setup": "codex", "kind": "consumer"})
        self.assertNotIn(tid, [row[0] for row in runner.graded_attempts(campaign)])

    # ---- G: the capture reader and the row filter
    def test_only_the_launch_capture_is_read_as_a_verifier_trace(self):
        capture = os.path.join(self.scratch, "verifier")
        runner.ensure_dir(capture)
        real = os.path.join(capture, "launch-F5-01-outbound-required-run-verify.json")
        runner.write_text(real, '{"part": {"type": "text"}}\n')
        for stray in ("launch-F5-01-outbound-required-run-verify.record-call-flags.json",
                      "launch-F5-01-outbound-required-run-verify.stderr",
                      "launch-x.y.json"):
            runner.write_text(os.path.join(capture, stray), "{\n  \"status\": \"ok\"\n}\n")
        self.assertEqual(runner.capture_files(capture, "opencode-trace"), [real])

    def test_a_pretty_printed_object_yields_no_rows(self):
        path = os.path.join(self.scratch, "pretty.json")
        runner.write_text(path, json.dumps(
            {"injected": ["one"], "refused": [], "note": "a note", "status": "ok"},
            indent=2) + "\n")
        self.assertEqual(runner.jsonl_lines(path), [])

    def test_native_actions_reads_the_capture_and_raises_nothing(self):
        """Her trial's shape: the sidecar beside the capture in run/verifier/."""
        record = os.path.join(self.scratch, "record-with-sidecar")
        runner.ensure_dir(os.path.join(record, "workspace"))
        runner.write_json(os.path.join(record, "command.json"),
                          {"workspace": os.path.join(record, "workspace"),
                           "run_dir": os.path.join(record, "run"), "opaque_tree": record,
                           "setup": "opencode", "case": testlib.CASE,
                           "condition": "available"})
        verifier = os.path.join(record, "run", "verifier")
        runner.ensure_dir(verifier)
        call = "launch-F5-01-outbound-required-run-verify"
        jsonl(os.path.join(verifier, call + ".json"),
              [{"part": {"type": "tool", "tool": "bash", "callID": "a",
                         "state": {"status": "completed", "input": {"command": "ls -la"},
                                   "output": "ok"}}}])
        runner.write_text(os.path.join(verifier, call + ".record-call-flags.json"),
                          json.dumps({"injected": ["opencode system prompt"], "refused": [],
                                      "note": "a harness artifact", "status": "ok"},
                                     indent=2) + "\n")
        runner.write_text(os.path.join(verifier, call + ".stderr"), "")
        actions = runner.native_actions(record)
        self.assertTrue(actions)
        self.assertIn("ls -la", [a.get("command") for a in actions])

    # ---- the guard: one attempt's exception does not end the run
    def test_grade_all_records_the_failing_attempt_and_grades_the_rest(self):
        campaign = runner.Campaign(self.campaign)
        good = runner.trial_id("claude-code", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, good,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        bad = runner.trial_id("codex", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, bad,
                   "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        # the first attempt in the order raises inside the reader, as the sidecar did
        stub = os.path.join(self.scratch, "grade_stub.py")
        runner.write_text(stub, "\n".join([
            "import sys",
            "sys.path.insert(0, %r)" % os.path.dirname(runner.__file__),
            "import runner",
            "real = runner.trace_witnesses",
            "def boom(campaign, record, command):",
            "    if %r in record:" % bad,
            "        raise AttributeError(\"'str' object has no attribute 'get'\")",
            "    return real(campaign, record, command)",
            "runner.trace_witnesses = boom",
            "sys.argv = ['runner.py', 'grade', '--campaign', %r, '--all']" % self.campaign,
            "sys.exit(runner.main())",
            ""]))
        step = runner.run_cmd(
            [sys.executable, stub],
            env=runner.Campaign(self.campaign).env(require_binaries=False),
            cwd=self.scratch, label="grade --all with one reader raising")
        self.assertEqual(step["exit"], 1, step["stderr"][-1500:])
        document = json.loads(step["stdout"])
        self.assertEqual(document["graded"], 1)
        self.assertEqual([e["trial"] for e in document["grade_errors"]], [bad])
        self.assertEqual(document["grade_errors"][0]["exception"], "AttributeError")
        self.assertIn(bad, document[runner.FAIL_EXIT_KEY])
        self.assertIn("AttributeError", step["stderr"])
        self.assertEqual([g["trial"] for g in document["grades"]], [good])
        self.assertFalse(os.path.isfile(os.path.join(campaign.trial_dir(bad), "grade.json")))
        self.assertTrue(os.path.isfile(os.path.join(campaign.trial_dir(good), "grade.json")))


class Fix8ConsumersWaitAndExactCaptures(RunnerCase):
    """Astra's recheck7: Q and G PARTLY.

    Q-S: the flat queue puts the consumer rows last, but `_campaign_loop` partitions it BY
    LANE and runs the lanes at once, so a fast lane reaches its consumers while another lane
    is still producing, and `producer_record_for` ranks over whatever exists at that moment.
    Her probe got the comparison record in-queue and the continuation record after the end.
    G: only the OpenCode `launch-` form was tightened, and `do_report` still read the ledger
    with its own `json.loads` comprehension.
    """

    setups = ("claude-code", "codex")

    # ---- Q-S: the campaign-wide producer boundary
    def scheduler_plan(self, second_producer_row=False):
        """Two lanes: `codex` produces, `claude-code` consumes. Her q.py's shape.

        `second_producer_row` gives the producing lane a row AFTER the one that raises, so
        the lane's thread dies with a row still owed to the boundary.
        """
        continuation = ["cont-codex-F3-02-mixed-two-items-compaction-r1"]
        if second_producer_row:
            continuation.append("cont-codex-F3-02-mixed-two-items-handoff-r1")
        return {"order": {"codex": ["codex-F1-01-fixed-clean-available-r1"]},
                "continuation_order": {"codex": continuation},
                "consumer_order": {"claude-code": ["consumer-codex-to-claude-code-r1"]}}

    def record_producer(self, campaign, tid, kind):
        directory = campaign.trial_dir(tid)
        runner.ensure_dir(directory)
        runner.write_json(os.path.join(directory, "command.json"),
                          {"setup": "codex", "condition": "available", "kind": kind,
                           "status": "complete"})
        # batch C: a producer with NOTHING to recover is refused, so the record this
        # scheduler test places by hand carries a terminal status the way a real one does.
        runner.write_json(os.path.join(directory, "result.json"),
                          {"status": "completed", "items": []})

    def drive_two_lanes(self, slow_seconds=0.6, stop_the_slow_lane=False,
                        kill_the_slow_lane=False):
        """The real queue, loop and selector; no harness and no model.

        The slow lane records the PREFERRED record (a continuation) only after a delay, so a
        consumer that does not wait selects the comparison record instead.
        """
        import argparse
        import threading
        import time as _time
        campaign = runner.Campaign(self.campaign)
        runner.ensure_dir(campaign.trials)
        plan = self.scheduler_plan(second_producer_row=kill_the_slow_lane)
        comparison = "codex-F1-01-fixed-clean-available-r1"
        continuation = "cont-codex-F3-02-mixed-two-items-compaction-r1"
        self.record_producer(campaign, comparison, "comparison")
        selected, started = [], threading.Event()

        def slow_continuation(one):
            started.set()
            if kill_the_slow_lane:
                raise RuntimeError("the slow lane died before recording its producer")
            _time.sleep(slow_seconds)
            self.record_producer(campaign, continuation, "continuation:compaction")

        def consume(one):
            selected.append(
                runner.producer_record_for(campaign, plan, "codex")["trial"])

        args = argparse.Namespace(fake_launcher=None, compact_tokens=None, lanes=2,
                                  poll_interval=0.01)
        saved = (runner.require_preflight, runner.cache_routing_requests,
                 runner.do_continuation, runner.do_consumer, runner.lane_stopped)
        runner.require_preflight = lambda *a, **k: None
        runner.cache_routing_requests = lambda *a, **k: {}
        runner.do_continuation = slow_continuation
        runner.do_consumer = consume
        if stop_the_slow_lane:
            runner.lane_stopped = lambda campaign_, lane: (
                {"kind": "operator", "why": "stopped for the test"} if lane == "codex"
                else None)
        else:
            runner.lane_stopped = lambda *a, **k: None
        try:
            document = runner._campaign_loop(campaign, plan, args)
        finally:
            (runner.require_preflight, runner.cache_routing_requests,
             runner.do_continuation, runner.do_consumer, runner.lane_stopped) = saved
        after = runner.producer_record_for(campaign, plan, "codex")["trial"]
        return {"document": document, "in_queue": selected[0] if selected else None,
                "after_end": after, "comparison": comparison,
                "continuation": continuation}

    def test_a_consumer_waits_for_a_slower_lanes_producer(self):
        """Her q.py's finding, with no deadlock: both selections must agree."""
        got = self.drive_two_lanes()
        self.assertEqual(got["in_queue"], got["after_end"])
        self.assertEqual(got["in_queue"], got["continuation"])
        self.assertEqual(got["document"]["failed"], [])

    def test_a_stopped_lane_does_not_deadlock_the_consumers(self):
        """The boundary's stopped-lane resolution: a stop counts as finished."""
        got = self.drive_two_lanes(stop_the_slow_lane=True)
        self.assertIsNotNone(got["in_queue"], "the consumer never ran")
        self.assertEqual(got["in_queue"], got["after_end"])
        # the slow lane never recorded its continuation, so the comparison is the whole set
        self.assertEqual(got["in_queue"], got["comparison"])

    def test_a_lane_that_dies_releases_the_boundary(self):
        """A producer that can never be recorded must not hold the consumers forever."""
        got = self.drive_two_lanes(kill_the_slow_lane=True)
        self.assertIsNotNone(got["in_queue"], "the consumer never ran")
        self.assertEqual(got["in_queue"], got["comparison"])
        self.assertTrue(any("lane stopped" in (row.get("why") or "")
                            for row in got["document"]["failed"]),
                        got["document"]["failed"])
        note = runner.read_text(runner.Campaign(self.campaign).log, "") or ""
        # the lane died with a row still owed, and the boundary says so rather than hanging
        self.assertIn("producer boundary no longer waits", note)
        # E11-41 R1 (Q-S-L): under the two phases the consumer never waits, so the line that
        # marks the crossing is the consumer phase's own, not the old boundary-opened note.
        self.assertIn("the consumer phase begins", note)

    # ---- G: every capture name exact
    def test_every_shape_selects_only_its_true_captures(self):
        """Her four suffix controls (recheck7/scratch/g.py)."""
        capture = os.path.join(self.scratch, "suffix-controls")
        runner.ensure_dir(capture)
        strays = ["launch-x.record-call-flags.json", "launch-x.trace.json",
                  "launch-x.session.json", "x.record-call-flags.trace.jsonl",
                  "x.record-call-flags.rollout.jsonl", "x.record-call-flags.events.jsonl",
                  "launch-x.stderr"]
        real = {"opencode-trace": ["launch-x.json", "trace.json"],
                "opencode-session": ["session.json"],
                "claude-code": ["trace.jsonl", "transcript.jsonl"],
                "codex": ["rollout.jsonl", "events.jsonl",
                          "F5-01-outbound-required-run-verify.rollout.jsonl",
                          "F5-01-outbound-required-run-verify-2.events.jsonl"]}
        for name in strays + [n for names in real.values() for n in names]:
            runner.write_text(os.path.join(capture, name), "{}\n")
        for shape, names in real.items():
            selected = sorted(os.path.basename(p)
                              for p in runner.capture_files(capture, shape))
            self.assertEqual(selected, sorted(names), shape)
            for stray in strays:
                self.assertNotIn(stray, selected, shape)

    # ---- G: the report's ledger reader
    def test_the_report_survives_a_scalar_ledger_line(self):
        campaign = runner.Campaign(self.campaign)
        tid = runner.trial_id("claude-code", testlib.CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        with open(campaign.trials_jsonl, "a", encoding="utf-8") as handle:
            handle.write('"a line no reader should index"\n')
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertTrue(report)
        rows = runner.jsonl_lines(campaign.trials_jsonl)
        self.assertTrue(all(isinstance(row, dict) for row in rows))
        self.assertIn(tid, [row.get("id") for row in rows])


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
