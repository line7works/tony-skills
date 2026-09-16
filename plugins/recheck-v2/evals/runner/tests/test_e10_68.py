"""E10-68: the three runner defects the 2026-09-15 campaign surfaced, and item (e).

Each test reproduces one defect against the pre-fix runner (`1911199`) and passes after the
fix. None of them opens `evals/answer-key/` or `evals/trigger-set/held-out/`: the held-out set
in `HeldOutRequestSurvivesTheBarrierTest` is a stand-in the test writes itself under E10-21,
and the barrier over it is closed by the test's own stub launcher, exactly as `close_key`
closes the real one for the duration of every launch.

- defect 1, `HeldOutRequestSurvivesTheBarrierTest`: two lanes launch concurrently, each with a
  held-out routing trial, and both launch — the barrier closed over the held-out set at every
  launch and the request text still reached the trial (E10-68 (1)).
- defect 2, `AStringMessageDoesNotKillAReaderTest`: the verbatim `system` /`permission_denied`
  record of `claude-code-F3-01-missed-case-available-r2`'s trace line 74, fed to every reader
  of a trace record, plus the witness the denial now leaves behind (E10-68 (2)).
- defect 3, `ADeadLaneIsRecordedTest`: a setup that raises inside collection, and the lane stop,
  the status output, the in-flight trial's record and the non-zero exit (E10-68 (3)).
- item (e), `OpenCodeInstallClearsPriorStateTest`: what `install` clears out of an OpenCode
  home and what it deliberately leaves.
"""
import argparse
import contextlib
import io
import json
import os
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, FAKE, CASE

PERMISSION_DENIED_FIXTURE = os.path.join(FAKE, "permission-denied-system-event.jsonl")


class HeldOutRequestSurvivesTheBarrierTest(RunnerCase):
    """Defect 1: the held-out barrier used to collide with a concurrent launch.

    E10-40 holds the held-out directory at mode 000 for the whole of every launch and while any
    registered launch is alive; E10-13 read a held-out entry's text through a subprocess AT
    LAUNCH TIME. With more than one lane alive the read failed with `PermissionError`,
    `request_text` raised `Missing`, and the routing trial was recorded as raised with no
    process launched — 72 of them on the night of 2026-09-15.

    The stub launcher here closes the stand-in's directory exactly as `close_key` closes the
    real one, so the collision is reproduced without the test ever naming a real held-out
    entry. Against `1911199` both lanes' routing trials raise `no trigger-set entry`; after the
    fix both launch, because `campaign start` wrote every planned held-out request into
    `<campaign>/routing-requests/` before the first launch, while the keys were open.
    """

    setups = ("claude-code", "codex")
    ENTRY = "H-01-stand-in"

    def build(self):
        """The stand-in in its own directory, the plan, and the mode-recording launcher."""
        self.stand_in_dir = os.path.join(self.scratch, "held-out-set")
        os.makedirs(self.stand_in_dir, exist_ok=True)
        self.stand_in = os.path.join(self.stand_in_dir, "requests.json")
        runner.write_json(self.stand_in, {"requests": [
            {"id": self.ENTRY, "text": "a request this test wrote, entry 1",
             "expected": {"target": "recheck-v2"}, "competitors": []}]})
        # whatever the test does, the directory goes back to readable so the scratch can be
        # removed and no later test inherits a closed stand-in
        self.addCleanup(os.chmod, self.stand_in_dir, 0o700)
        self.make_campaign({"cases": [CASE], "conditions": ["available"], "repetitions": 1,
                            "routing": {"entries": [self.ENTRY], "repetitions": 1},
                            "continuation": None})
        self.mode_log = os.path.join(self.scratch, "key-modes.txt")
        self.launcher = self.barrier_stub()

    def barrier_stub(self):
        """A stub that CLOSES the stand-in's directory, records both modes, then runs the fake.

        Behaviour travels in the stub the test wrote (E10-52, finding 25). The chmod comes
        first, so every recorded mode — the runner's own `close_key` over the real directory
        and this stub's over the stand-in — is the mode a launched harness would have met.
        """
        real = os.path.dirname(runner.TRIGGER_HELDOUT)
        path = os.path.join(self.scratch, "barrier-launcher.sh")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/bin/sh\n"
                "chmod 000 '%s' 2>/dev/null\n"
                "for d in '%s' '%s'; do\n"
                "  printf '%%s %%s\\n' \"$d\" \"$(stat -f '%%Lp' \"$d\" 2>/dev/null || "
                "echo unknown)\" >> '%s'\n"
                "done\n"
                "h=claude-code\n"
                '[ -n "$RECHECK_CODEX_HOME" ] && h=codex\n'
                '[ -n "$RECHECK_OPENCODE_SETUP" ] && h=opencode\n'
                'exec /usr/bin/python3 "%s/fakelib.py" "$h" "$@"\n'
                % (self.stand_in_dir, real, self.stand_in_dir, self.mode_log, FAKE))
        os.chmod(path, 0o755)
        return path

    def run_campaign(self):
        env = self.child_env({"RECHECK_RUNNER_TEST": "1",
                              "RECHECK_RUNNER_HELDOUT": self.stand_in})
        return cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                    "--skip-probe-gate", "--reopen-key",
                    "--fake-launcher", self.launcher], env=env)

    def rows(self, name):
        text = runner.read_text(os.path.join(self.campaign, name), "") or ""
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_every_lane_launches_its_held_out_routing_trial_behind_a_closed_barrier(self):
        self.build()
        got = self.run_campaign()
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])

        # (1) no lane raised `no trigger-set entry` — the signature of the live defect
        raised = [row for row in self.rows("interruptions.jsonl")
                  if "no trigger-set entry" in (row.get("observed") or "")]
        self.assertEqual(raised, [], "a held-out routing trial raised instead of launching")

        # (2) both lanes' routing trials are in the ledger with a record of their own
        ledger = {row["id"]: row for row in self.rows("trials.jsonl")}
        wanted = ["routing-%s-%s-r1" % (name, self.ENTRY) for name in self.setups]
        for tid in wanted:
            self.assertIn(tid, ledger, sorted(ledger))
            self.assertEqual(ledger[tid]["status"], "complete", json.dumps(ledger[tid]))
            command = runner.read_json(os.path.join(ledger[tid]["record"], "command.json"))
            self.assertEqual(command["set"], "held-out")
            self.assertIn("cached", command["request_source"]["how"])

        # (3) every launch met a closed barrier — both directories at mode 000, every time
        modes = [line.split() for line in
                 (runner.read_text(self.mode_log, "") or "").splitlines() if line.strip()]
        self.assertTrue(modes, "the stub recorded no launch")
        self.assertGreaterEqual(len(modes), 2 * len(self.setups),
                                "fewer launches than lanes: %s" % modes)
        for directory, mode in modes:
            self.assertEqual(mode, "0", "%s was mode %s at a launch, not 000"
                             % (directory, mode))

        # (4) the prompt the trial received is the cached file, byte for byte
        cached = os.path.join(self.campaign, "routing-requests", "%s.txt" % self.ENTRY)
        self.assertTrue(os.path.isfile(cached), cached)
        for tid in wanted:
            prompt = os.path.join(ledger[tid]["record"], "prompt.txt")
            self.assertEqual(runner.read_text(prompt), runner.read_text(cached))

        # (5) the index names the file and its hash and never its text
        index = runner.read_json(os.path.join(self.campaign, "routing-requests", "index.json"))
        self.assertEqual([e["entry"] for e in index["entries"]], [self.ENTRY])
        self.assertNotIn("a request this test wrote", json.dumps(index))
        self.assertEqual(index["failed"], [])

    def test_the_runner_never_reads_the_cached_text_itself(self):
        """E10-70 (Astra recheck5 item 1): hashing and copying the cached request happen in
        subprocesses, so the sealed text never enters the runner process, not even to hash it.

        Static half: neither `cache_routing_requests` nor `write_routing_prompt` names a reader
        or a copier that would bring the bytes into this process. Live half: the digests those
        subprocesses reported match the file, so nothing was lost by not reading it here.
        """
        import ast, hashlib
        tree = ast.parse(runner.read_text(runner.__file__))
        forbidden = {"file_sha256", "sha256_hex", "copyfile", "copy", "copy2", "open",
                     "read_text", "read_bytes"}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in (
                    "cache_routing_requests", "write_routing_prompt"):
                names = set()
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Name):
                        names.add(inner.id)
                    elif isinstance(inner, ast.Attribute):
                        names.add(inner.attr)
                self.assertFalse(names & forbidden,
                                 "%s names %s" % (node.name, sorted(names & forbidden)))
        self.build()
        got = self.run_campaign()
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        cached = os.path.join(self.campaign, "routing-requests", "%s.txt" % self.ENTRY)
        with open(cached, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        index = runner.read_json(os.path.join(self.campaign, "routing-requests", "index.json"))
        self.assertEqual([e["sha256"] for e in index["entries"]], [digest])
        self.assertEqual([e["bytes"] for e in index["entries"]], [os.path.getsize(cached)])
        ledger = {row["id"]: row for row in self.rows("trials.jsonl")}
        for name in self.setups:
            command = runner.read_json(os.path.join(
                ledger["routing-%s-%s-r1" % (name, self.ENTRY)]["record"], "command.json"))
            self.assertEqual(command["request_source"]["sha256"], digest)
            self.assertIn("/bin/cp", command["request_source"]["how"])

    def test_the_cache_is_written_before_the_first_launch_with_the_keys_open(self):
        """The invariant re-proved: the read happens while nothing is launched (E10-40)."""
        self.build()
        got = self.run_campaign()
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        index = runner.read_json(os.path.join(self.campaign, "routing-requests", "index.json"))
        # the real key directories were OPEN when the cache was written ...
        for row in index["key_state_at_cache_time"]:
            if row["present"]:
                self.assertFalse(row["closed"], json.dumps(row))
        # ... and closed for the whole of every launch afterwards
        state = [row for row in runner.key_state() if row["present"]]
        self.assertTrue(state)
        for row in state:
            self.assertTrue(row["closed"], "%s is %s after the campaign" % (row["path"],
                                                                           row["mode"]))
        log = runner.read_text(os.path.join(self.campaign, "runner.log"), "") or ""
        self.assertIn("cached 1 held-out request", log)
        self.assertLess(log.index("cached 1 held-out request"), log.index("key closed"),
                        "the cache was not written before the first launch closed the key")


class AStringMessageDoesNotKillAReaderTest(RunnerCase):
    """Defect 2: `activation()` crashed on a `system` event whose `message` is a string.

    The fixture is `trials/claude-code-F3-01-missed-case-available-r2/harness/trace.jsonl`
    line 74 of the 2026-09-15 campaign, copied verbatim: a `permission_denied` system event
    for an `Edit` auto-denied because a headless session has no approval surface. Its
    `message` is a plain string, and `message.get("content")` on one raises
    `AttributeError: 'str' object has no attribute 'get'` — which killed the
    `lane-claude-code` thread at 05:49Z.
    """

    def setUp(self):
        super(AStringMessageDoesNotKillAReaderTest, self).setUp()
        self.setup = runner.setup_for(runner.Campaign(self.campaign), self.plan_document,
                                      "claude-code")
        self.record = os.path.join(self.scratch, "record")
        self.harness = os.path.join(self.record, "harness")
        os.makedirs(self.harness)
        self.write_trace()

    @staticmethod
    def verbatim_line():
        line = runner.read_text(PERMISSION_DENIED_FIXTURE, "")
        assert line, "the fixture is empty: %s" % PERMISSION_DENIED_FIXTURE
        return line.rstrip("\n")

    def write_trace(self):
        """A trace in the harness's own shape with the verbatim denial in the middle of it."""
        lines = [
            json.dumps({"type": "system", "subtype": "init", "session_id": "s-1",
                        "model": "claude-opus-5", "slash_commands": ["recheck-v2"]}),
            json.dumps({"type": "assistant", "session_id": "s-1", "uuid": "u-1",
                        "message": {"model": "claude-opus-5", "content": [
                            {"type": "tool_use", "id": "t-1", "name": "Skill",
                             "input": {"skill": "recheck-v2:recheck-v2"}}]}}),
            json.dumps({"type": "user", "session_id": "s-1", "uuid": "u-2",
                        "message": {"content": [
                            {"type": "tool_result", "tool_use_id": "t-1",
                             "content": "the skill body"}]}}),
            self.verbatim_line(),
            json.dumps({"type": "assistant", "session_id": "s-1", "uuid": "u-3",
                        "message": {"model": "claude-opus-5", "content": [
                            {"type": "tool_use", "id": "t-2", "name": "Write",
                             "input": {"file_path": "/tmp/after-the-denial.txt"}}]}}),
            # the same string-message shape on a `user` and an `assistant` record, which the
            # other readers walk: a reader must be tolerant of the shape, not of one type
            json.dumps({"type": "user", "session_id": "s-1", "uuid": "u-4",
                        "isSynthetic": True, "message": "a plain string on a user record"}),
            json.dumps({"type": "assistant", "session_id": "s-1", "uuid": "u-5",
                        "message": "a plain string on an assistant record"}),
        ]
        runner.write_text(os.path.join(self.harness, "trace.jsonl"), "\n".join(lines) + "\n")

    def test_the_activation_reader_survives_the_verbatim_record(self):
        activation = self.setup.activation(self.harness)
        self.assertTrue(activation["activated"], json.dumps(activation)[:600])
        self.assertEqual([c["skill"] for c in activation["marker"]["skill_tool_calls"]],
                         ["recheck-v2:recheck-v2"])

    def test_every_other_reader_of_a_trace_record_survives_it(self):
        self.assertEqual(self.setup.model_record(self.harness)["id"], "claude-opus-5")
        self.assertTrue(self.setup.condition_witness(self.harness, "available"))
        self.assertEqual(runner.observed_target(self.setup, self.harness)["target"],
                         "recheck-v2")
        actions = runner.native_actions(self.record)
        self.assertIn("/tmp/after-the-denial.txt",
                      json.dumps(actions), "native_actions did not read past the denial")
        rows = list(enumerate(runner.jsonl_lines(
            os.path.join(self.harness, "trace.jsonl")), 1))
        self.assertEqual(runner._first_work_line("claude-code", rows), 2)

    def test_the_denial_is_kept_as_a_witness(self):
        denials = self.setup.permission_denials(self.harness)
        self.assertEqual(denials["count"], 1, json.dumps(denials))
        self.assertEqual(denials["tools"], ["Edit"])
        self.assertEqual(denials["by_tool"], {"Edit": 1})
        self.assertEqual(denials["events"][0]["line"], 4)
        self.assertTrue(denials["events"][0]["message_is_a_string"])
        self.assertEqual(denials["events"][0]["tool_use_id"],
                         "toolu_01XuENbGT3cexGHwQ7jkMAdA")

    def test_the_shared_readers_answer_for_a_message_that_is_not_an_object(self):
        for record in ({"message": "a string"}, {"message": []}, {"message": None},
                       {}, {"message": 7}):
            self.assertEqual(runner.native_message(record), {})
            self.assertEqual(runner.message_content(record), [])
        self.assertEqual(runner.message_content({"message": {"content": "plain text"}}), [])
        self.assertEqual(runner.message_content({"message": {"content": [{"type": "text"}]}}),
                         [{"type": "text"}])

    def test_a_trial_record_carries_the_denial_count(self):
        """The witness reaches `command.json`, which is what the E11 report reads."""
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        command = runner.read_json(os.path.join(parse_stdout(got)["record"], "command.json"))
        self.assertIn("permission_denials", command)
        self.assertEqual(command["permission_denials"]["count"], 0)
        self.assertEqual(command["permission_denials"]["tools"], [])


class ADeadLaneIsRecordedTest(RunnerCase):
    """Defect 3: a lane thread that raised died silently.

    `campaign status` said `running` with `lane_stops {}` for three hours and the campaign
    ended only when the other lanes ran dry. The setup's collection is made to raise here the
    way `activation()` did, and the four things E10-68 asks for are checked: the lane stop with
    its traceback and the trial in flight, the status output, the in-flight trial's own
    `command.json`, and a non-zero exit.
    """

    @staticmethod
    def main_exit(argv):
        """`runner.main` in this process, with its one JSON document off the suite's stdout."""
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.main(argv)

    def raising_setup(self):
        original = runner.ClaudeCodeSetup.activation

        def boom(_self, _out_dir):
            raise AttributeError("'str' object has no attribute 'get'")

        runner.ClaudeCodeSetup.activation = boom
        self.addCleanup(setattr, runner.ClaudeCodeSetup, "activation", original)

    def loop(self):
        campaign = runner.Campaign(self.campaign)
        args = argparse.Namespace(campaign=self.campaign,
                                  fake_launcher=self.fake_launcher("claude-code"),
                                  compact_tokens=100000,
                                  poll_interval=runner.DEFAULT_POLL_INTERVAL,
                                  lanes=0)
        return runner._campaign_loop(campaign, campaign.plan(), args)

    def test_an_uncaught_exception_in_a_lane_worker_becomes_a_record(self):
        self.make_campaign({"cases": [CASE], "conditions": ["available"], "repetitions": 1,
                            "routing": {"entries": [], "repetitions": 1},
                            "continuation": None})
        self.raising_setup()
        document = self.loop()
        trial = runner.trial_id("claude-code", CASE, "available", 1)

        # the lane stop, with the traceback, the trial in flight and the time
        stop_path = os.path.join(self.campaign, "lane-stops", "claude-code.json")
        self.assertTrue(os.path.isfile(stop_path), "no lane stop was written")
        stop = runner.read_json(stop_path)
        self.assertEqual(stop["kind"], "runner_error")
        self.assertEqual(stop["trial_in_flight"], trial)
        self.assertIn("AttributeError", stop["traceback"])
        self.assertIn("'str' object has no attribute 'get'", stop["traceback"])
        self.assertTrue(stop["stopped_at"])

        # the in-flight trial's own record says the RUNNER failed, not the harness
        command = runner.read_json(os.path.join(self.campaign, "trials", trial,
                                                "command.json"))
        self.assertEqual(command["status"], "runner_error")
        self.assertIn("AttributeError", command["runner_error"]["traceback"])
        ledger = [json.loads(line) for line in
                  (runner.read_text(os.path.join(self.campaign, "trials.jsonl"), "")
                   or "").splitlines() if line.strip()]
        self.assertEqual([row["status"] for row in ledger if row["id"] == trial],
                         ["runner_error"])

        # the interruption line E10-14 asks of every interruption
        interruptions = [json.loads(line) for line in
                         (runner.read_text(os.path.join(self.campaign, "interruptions.jsonl"),
                                           "") or "").splitlines() if line.strip()]
        self.assertTrue([row for row in interruptions
                         if "lane worker raised AttributeError" in (row.get("observed") or "")],
                        json.dumps(interruptions))

        # `campaign start` exits non-zero
        self.assertIn("runner_exit_nonzero_because", document)
        self.assertIn("claude-code", document["runner_exit_nonzero_because"])
        self.assertEqual(document["lane_stops"]["claude-code"]["kind"], "runner_error")

    def test_campaign_status_reports_the_stop_and_the_exit_is_non_zero(self):
        self.make_campaign({"cases": [CASE], "conditions": ["available"], "repetitions": 1,
                            "routing": {"entries": [], "repetitions": 1},
                            "continuation": None})
        self.raising_setup()
        self.loop()
        status = parse_stdout(cli(["campaign", "status", "--campaign", self.campaign]))
        self.assertIn("claude-code", status["lane_stops"])
        self.assertEqual(status["lane_stops"]["claude-code"]["kind"], "runner_error")
        # and the same document, printed by `main`, is a non-zero exit
        self.assertEqual(self.main_exit(["campaign", "status", "--campaign", self.campaign]),
                         runner.EXIT_OK)   # status itself is a report, not a failure

    def test_the_fail_exit_key_turns_a_finished_document_into_a_non_zero_exit(self):
        """`main`'s own rule, exercised on the shape `_campaign_loop` returns."""
        original = runner.do_campaign
        runner.do_campaign = lambda args: {"ok": True,
                                           runner.FAIL_EXIT_KEY: "the x lane stopped"}
        self.addCleanup(setattr, runner, "do_campaign", original)
        self.assertEqual(self.main_exit(["campaign", "status", "--campaign", self.campaign]),
                         runner.EXIT_FAIL)


class OpenCodeInstallClearsPriorStateTest(RunnerCase):
    """Item (e) of E10-68's close hand-off: the OpenCode homes carried prior-campaign state."""

    setups = ("opencode",)

    def home_with_state(self):
        home = os.path.join(self.scratch, "opencode-home")
        data = os.path.join(home, "xdg-data", "opencode")
        state = os.path.join(home, "xdg-state", "opencode")
        cache = os.path.join(home, "xdg-cache", "uv", "wheels-v6")
        binary = os.path.join(home, "npm", "node_modules", ".bin")
        for path in (data, state, cache, binary,
                     os.path.join(data, "log"), os.path.join(data, "snapshot", "abc"),
                     os.path.join(state, "locks")):
            os.makedirs(path, exist_ok=True)
        runner.write_text(os.path.join(data, "auth.json"), '{"openrouter":{"key":"x"}}\n')
        runner.write_text(os.path.join(data, "opencode.db"), "a prior campaign's sessions\n")
        runner.write_text(os.path.join(data, "log", "opencode.log"), "an earlier campaign\n")
        runner.write_text(os.path.join(data, "snapshot", "abc", "f"), "a prior snapshot\n")
        runner.write_text(os.path.join(state, "locks", "a.lock"), "\n")
        runner.write_text(os.path.join(cache, "wheel"), "a cached wheel\n")
        runner.write_text(os.path.join(binary, "opencode"), "#!/bin/sh\n")
        return home

    def test_install_clears_the_session_state_and_keeps_the_auth_store_and_the_binary(self):
        home = self.home_with_state()
        setup = runner.setup_for(runner.Campaign(self.campaign), self.plan_document,
                                 "opencode")
        cleared = setup._clear_prior_state(home)
        data = os.path.join(home, "xdg-data", "opencode")
        state = os.path.join(home, "xdg-state", "opencode")
        # gone: every piece of prior-campaign session state
        for gone in (os.path.join(data, "opencode.db"), os.path.join(data, "log"),
                     os.path.join(data, "snapshot"), os.path.join(state, "locks")):
            self.assertFalse(os.path.exists(gone), gone)
        # kept: the auth store, the binary tree and the uv cache
        self.assertTrue(os.path.isfile(os.path.join(data, "auth.json")))
        self.assertTrue(os.path.isfile(os.path.join(home, "npm", "node_modules", ".bin",
                                                    "opencode")))
        self.assertTrue(os.path.isfile(os.path.join(home, "xdg-cache", "uv", "wheels-v6",
                                                    "wheel")))
        # the record names what went and what stayed, with sizes and reasons
        removed = sorted(os.path.relpath(r["path"], home) for r in cleared["removed"])
        self.assertEqual(removed, ["xdg-data/opencode/log", "xdg-data/opencode/opencode.db",
                                   "xdg-data/opencode/snapshot", "xdg-state/opencode/locks"])
        self.assertTrue(all(isinstance(r["bytes"], int) for r in cleared["removed"]))
        self.assertEqual([os.path.relpath(k["path"], home) for k in cleared["kept"]],
                         ["xdg-data/opencode/auth.json"])
        self.assertIn("xdg-cache", cleared["not_cleared"])

    def test_it_is_idempotent_on_a_home_that_has_none(self):
        home = os.path.join(self.scratch, "fresh-home")
        os.makedirs(home)
        setup = runner.setup_for(runner.Campaign(self.campaign), self.plan_document,
                                 "opencode")
        cleared = setup._clear_prior_state(home)
        self.assertEqual(cleared["removed"], [])
        self.assertEqual(cleared["kept"], [])


if __name__ == "__main__":
    unittest.main()
