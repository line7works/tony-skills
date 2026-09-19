"""E10-62: the plan's per-setup model and effort, honoured to the launcher and recorded.

Tony settled the campaign's four lanes on 2026-09-15: `claude-code` = Claude Opus 5 at effort
`medium`, `codex` = `gpt-5.6-sol` at `model_reasoning_effort=medium`, `opencode` =
`openrouter/qwen/qwen3.8-flash`, `opencode-deepseek` =
`openrouter/deepseek/deepseek-v4.1-flash`. One test per item of the ruling, each exercising the
real path the item names: the plan validator, the three launchers, the home paths, and the
`configured` half of `model.json` at both of its write sites.

Nothing here opens `evals/answer-key/` or `evals/trigger-set/held-out/`; the plan tests carry
their own held-out stand-in (E10-21) as every other plan test does.
"""
import json
import os
import shutil
import stat
import subprocess
import types
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner, CASE, FAKE

SETUPS_DIR = os.path.join(runner.PLUGIN_DIR, "setups")


# ------------------------------------------------------------------ item 1: the plan validates


class PlanModelAndEffortTest(RunnerCase):
    """E10-62 item 1: `model` and `effort` are validated, before any write."""

    def write_plan(self, setups):
        plan = runner.default_plan("test")
        plan["setups"] = setups
        path = os.path.join(self.scratch, "plan-%d.json" % len(os.listdir(self.scratch)))
        runner.write_json(path, plan)
        return path

    def plan_it(self, setups):
        return cli(["plan", "--campaign", self.campaign, "--refresh", "--plan",
                    self.write_plan(setups)], env=self.held_out_env())

    def refuse(self, setups, fragment):
        got = self.plan_it(setups)
        self.assertEqual(got.returncode, 2, got.stdout)
        self.assertIn(fragment, got.stderr)
        return got

    def test_the_four_pinned_setups_are_accepted(self):
        got = self.plan_it([
            {"name": "claude-code", "harness": "claude-code", "model": "opus",
             "effort": "medium"},
            {"name": "codex", "harness": "codex", "model": "gpt-5.6-sol", "effort": "medium"},
            {"name": "opencode", "harness": "opencode",
             "model": "openrouter/qwen/qwen3.8-flash"},
            {"name": "opencode-deepseek", "harness": "opencode",
             "model": "openrouter/deepseek/deepseek-v4.1-flash"},
        ])
        self.assertEqual(got.returncode, 0, got.stderr)
        written = runner.read_json(os.path.join(self.campaign, "campaign.json"))["setups"]
        self.assertEqual([s["name"] for s in written],
                         ["claude-code", "codex", "opencode", "opencode-deepseek"])
        self.assertEqual(written[0]["effort"], "medium")
        self.assertEqual(written[3]["model"], "openrouter/deepseek/deepseek-v4.1-flash")
        self.assertNotIn("effort", written[3])

    def test_a_model_that_is_not_a_string_is_refused(self):
        self.refuse([{"name": "codex", "harness": "codex", "model": 5}],
                    "'model' must be a string")

    def test_an_effort_that_is_not_a_string_is_refused(self):
        self.refuse([{"name": "codex", "harness": "codex", "effort": ["medium"]}],
                    "'effort' must be a string")

    def test_an_empty_model_is_refused(self):
        self.refuse([{"name": "codex", "harness": "codex", "model": "  "}],
                    "'model' is empty")

    def test_an_effort_on_opencode_is_refused(self):
        """E10-26: OpenCode 1.18.31 records no reasoning effort, so an effort there is a label
        with no record behind it (E10-19)."""
        self.refuse([{"name": "opencode", "harness": "opencode",
                      "model": "openrouter/qwen/qwen3.8-flash", "effort": "medium"}],
                    "the opencode harness takes none")

    def test_an_effort_outside_the_harness_s_values_is_refused(self):
        self.refuse([{"name": "claude-code", "harness": "claude-code", "effort": "ultra"}],
                    "which claude-code does not accept")
        self.refuse([{"name": "codex", "harness": "codex", "effort": "minimal"}],
                    "which codex does not accept")

    def test_every_value_the_harness_accepts_is_accepted(self):
        for effort in runner.HARNESS_EFFORTS["claude-code"]:
            got = self.plan_it([{"name": "claude-code", "harness": "claude-code",
                                 "model": "opus", "effort": effort}])
            self.assertEqual(got.returncode, 0, "%s: %s" % (effort, got.stderr))

    def test_an_unknown_key_on_a_setup_entry_is_refused(self):
        """Ignoring it would run the whole lane at the harness's own default with nothing in
        the record to say so."""
        self.refuse([{"name": "codex", "harness": "codex", "efort": "medium"}],
                    "the unknown key 'efort'")
        self.refuse([{"name": "codex", "harness": "codex", "model": "gpt-5.6-sol",
                      "reasoning": "high", "zz": 1}],
                    "the unknown keys 'reasoning', 'zz'")

    def test_every_problem_is_collected_and_raised_once(self):
        got = self.refuse([{"name": "opencode", "harness": "opencode", "effort": "medium",
                            "nope": 1}], "the plan is refused")
        self.assertIn("takes none", got.stderr)
        self.assertIn("unknown key 'nope'", got.stderr)

    def test_the_default_plan_carries_the_four_pinned_lanes(self):
        plan = runner.default_plan("test")
        self.assertEqual(
            [(s["name"], s.get("model"), s.get("effort")) for s in plan["setups"]],
            [("claude-code", "opus", "medium"),
             ("codex", "gpt-5.6-sol", "medium"),
             ("opencode", "openrouter/qwen/qwen3.8-flash", None),
             ("opencode-deepseek", "openrouter/deepseek/deepseek-v4.1-flash", None)])
        runner.validate_plan(plan)


# ----------------------------------------------------- item 3: the setup name keys the homes


class SetupNameKeysTheHomesTest(RunnerCase):
    """E10-62 item 3: `opencode-deepseek` gets its own three homes, and nothing else moves."""

    def setup(self, name, harness=None, model=None):
        cls = runner.SETUP_CLASSES[harness or name]
        return cls(runner.Campaign(self.campaign), stage=self.stage, name=name, model=model)

    def test_the_three_existing_setups_keep_every_path(self):
        """The literals below are the paths E9 built and E10 has used all along."""
        root = runner.PILOT_ROOT
        self.assertEqual(
            [self.setup("claude-code").home(h) for h in runner.HOMES],
            [os.path.join(root, "claude-code"),
             os.path.join(root, "claude-code", "absent"),
             os.path.join(root, "claude-code", "routing")])
        self.assertEqual(
            [self.setup("codex").home(h) for h in runner.HOMES],
            [os.path.join(root, "codex", "home"),
             os.path.join(root, "codex", "homes", "absent"),
             os.path.join(root, "codex", "homes", "routing")])
        self.assertEqual(
            [self.setup("opencode").home(h) for h in runner.HOMES],
            [os.path.join(root, "opencode"),
             os.path.join(root, "opencode", "absent"),
             os.path.join(root, "opencode", "routing")])

    def test_the_deepseek_setup_gets_three_homes_of_its_own(self):
        root = runner.PILOT_ROOT
        deepseek = self.setup("opencode-deepseek", harness="opencode",
                              model="openrouter/deepseek/deepseek-v4.1-flash")
        self.assertEqual(
            [deepseek.home(h) for h in runner.HOMES],
            [os.path.join(root, "opencode-deepseek"),
             os.path.join(root, "opencode-deepseek", "absent"),
             os.path.join(root, "opencode-deepseek", "routing")])
        qwen = self.setup("opencode")
        for home in runner.HOMES:
            self.assertNotEqual(deepseek.home(home), qwen.home(home))
            self.assertFalse(runner.path_contains(qwen.home("available"), deepseek.home(home)))

    def test_the_two_opencode_setups_never_share_the_shared_config(self):
        """E10-31: every OpenCode install rewrites `opencode.json`'s default model, which is
        why the second lane must not install into the first lane's home."""
        qwen = self.setup("opencode", model="openrouter/qwen/qwen3.8-flash")
        deepseek = self.setup("opencode-deepseek", harness="opencode",
                              model="openrouter/deepseek/deepseek-v4.1-flash")
        shared = os.path.join("xdg-config", "opencode", "opencode.json")
        self.assertNotEqual(os.path.join(qwen.home("available"), shared),
                            os.path.join(deepseek.home("available"), shared))

    def test_pilot_home_without_a_name_is_the_harness_s_own_layout(self):
        for harness in runner.HARNESSES:
            for home in runner.HOMES:
                self.assertEqual(runner.pilot_home(harness, home),
                                 runner.pilot_home(harness, home, setup_name=harness))

    def test_the_auth_store_exemptions_cover_a_named_setup_s_own_store(self):
        deepseek = self.setup("opencode-deepseek", harness="opencode")
        store = os.path.join(deepseek.home("available"), "xdg-data", "opencode", "auth.json")
        runner.ensure_dir(os.path.dirname(store))
        self.addCleanup(runner.rmtree, deepseek.home("available"))
        runner.write_text(store, "{}")
        self.assertNotIn(store, runner.auth_store_exemptions())
        self.assertIn(store,
                      runner.auth_store_exemptions([("opencode", "opencode-deepseek")]))

    def test_a_setup_the_plan_does_not_name_is_refused(self):
        """`install --setup opencode-deepseek` against a plan without it used to build that
        home on the OpenCode default model, which is the qwen lane's model."""
        plan = runner.read_json(os.path.join(self.campaign, "campaign.json"))
        with self.assertRaises(runner.Usage) as caught:
            runner._selected_setups(runner.Campaign(self.campaign), plan,
                                    ["opencode-deepseek"])
        self.assertIn("the plan has no setup opencode-deepseek", str(caught.exception))


# ------------------------------------------- item 2: the keys reach each launcher, for real


class ClaudeCodeLauncherFlagsTest(RunnerCase):
    """E10-62 item 2: `--model` and `--effort` on the launcher, and on the `claude` argv."""

    def stub_claude(self):
        """A `claude` on PATH that records its own argv and answers like the real one.

        The real `setups/claude-code/launch.sh` runs below it, unedited except for the two
        flags this ruling added, so what this test proves is the script's own argument
        handling and the two keys it writes into `launch.json`.
        """
        binary_dir = os.path.join(self.scratch, "stub-bin")
        runner.ensure_dir(binary_dir)
        path = os.path.join(binary_dir, "claude")
        runner.write_text(path, "\n".join([
            "#!/bin/sh",
            'printf "%s\\n" "$@" > "$RECHECK_STUB_ARGV"',
            'echo \'{"type":"system","subtype":"init","session_id":"stub-1",'
            '"model":"claude-opus-5-20260101","permissionMode":"acceptEdits"}\'',
            'echo \'{"type":"result","session_id":"stub-1","result":"done",'
            '"is_error":false,"num_turns":1,"total_cost_usd":0.5}\'',
            "exit 0",
        ]) + "\n")
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return binary_dir, path

    def launch(self, extra):
        binary_dir, _ = self.stub_claude()
        argv_file = os.path.join(self.scratch, "claude-argv.txt")
        out_dir = os.path.join(self.scratch, "harness-%d" % len(os.listdir(self.scratch)))
        workspace = os.path.join(self.scratch, "ws")
        runner.ensure_dir(workspace)
        prompt = os.path.join(self.scratch, "prompt.txt")
        runner.write_text(prompt, "do the thing\n")
        plugin_dir = os.path.join(self.scratch, "plugin")
        runner.ensure_dir(plugin_dir)
        environment = dict(os.environ)
        environment["PATH"] = binary_dir + os.pathsep + environment["PATH"]
        environment["RECHECK_STUB_ARGV"] = argv_file
        environment["SKILLS_V2_PILOT_HOME"] = os.path.join(self.scratch, "pilot-home")
        step = subprocess.run(
            ["sh", os.path.join(SETUPS_DIR, "claude-code", "launch.sh"),
             prompt, workspace, out_dir, "--plugin-dir", plugin_dir] + list(extra),
            capture_output=True, text=True, env=environment)
        return step, out_dir, argv_file

    def test_the_real_launch_sh_puts_both_flags_on_the_claude_argv(self):
        step, out_dir, argv_file = self.launch(["--model", "opus", "--effort", "medium"])
        self.assertEqual(step.returncode, 0, step.stderr)
        argv = runner.read_text(argv_file).splitlines()
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")

    def test_the_real_launch_sh_records_what_it_was_told_apart_from_the_init_event(self):
        step, out_dir, _ = self.launch(["--model", "opus", "--effort", "medium"])
        self.assertEqual(step.returncode, 0, step.stderr)
        launch = runner.read_json(os.path.join(out_dir, "launch.json"))
        self.assertEqual(launch["configured_model"], "opus")
        self.assertEqual(launch["configured_effort"], "medium")
        # the `model` key is and stays the session's own init event
        self.assertEqual(launch["model"], "claude-opus-5-20260101")

    def test_neither_flag_is_defaulted(self):
        """An E9-shaped call runs exactly the command E9 measured."""
        step, out_dir, argv_file = self.launch([])
        self.assertEqual(step.returncode, 0, step.stderr)
        argv = runner.read_text(argv_file).splitlines()
        self.assertNotIn("--model", argv)
        self.assertNotIn("--effort", argv)
        launch = runner.read_json(os.path.join(out_dir, "launch.json"))
        self.assertIsNone(launch["configured_model"])
        self.assertIsNone(launch["configured_effort"])

    def test_a_flag_with_no_value_is_a_usage_exit(self):
        step, _, _ = self.launch(["--model"])
        self.assertEqual(step.returncode, 2, step.stdout)
        self.assertIn("--model takes a value", step.stderr)

    def test_the_setup_puts_the_plan_s_pair_on_the_launcher_argv(self):
        setup = runner.ClaudeCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                       name="claude-code", model="opus", effort="medium")
        argv = []

        def capture(command, **kwargs):
            argv.extend(command)
            return {"argv": list(command), "exit": 0, "stdout": "", "stderr": "",
                    "started_at": runner.now_iso(), "ended_at": runner.now_iso(),
                    "timed_out": False, "wall_seconds": 0.0, "label": "launch.sh"}

        original = runner.run_cmd
        runner.run_cmd = capture
        try:
            setup.launch("available", "/tmp/p.txt", "/tmp/ws", "/tmp/out", 60,
                         fake=os.path.join(FAKE, "claude-code-launch.sh"))
        finally:
            runner.run_cmd = original
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")


class EveryLaunchPathCarriesThePairTest(RunnerCase):
    """E10-62 item 2: "all the way to the launcher" means EVERY launch path.

    Four of the six go through `Setup.launch` (`probe-env`, `run`, `routing`, and a
    continuation hand-off's fresh session). The other two build their own argv, because the
    cut needs the `Popen` handle to freeze and kill the process group (E10-47, E10-55) and the
    resume is the harness's own resume command: those two carried no pinned pair at all, and
    would have put the continuation lane on the sign-in's own model with `configured` still
    claiming the plan's.
    """

    def setups_of(self):
        campaign = runner.Campaign(self.campaign)
        return {
            "claude-code": runner.ClaudeCodeSetup(campaign, stage=self.stage,
                                                  name="claude-code", model="opus",
                                                  effort="medium"),
            "codex": runner.CodexSetup(campaign, stage=self.stage, name="codex",
                                       model="gpt-5.6-sol", effort="medium"),
            "opencode": runner.OpenCodeSetup(campaign, stage=self.stage,
                                             name="opencode-deepseek", model="deepseek"),
        }

    def test_every_setup_launch_call_site_is_one_method(self):
        """So a new launch path cannot miss the pair by writing its own argv."""
        source = runner.read_text(os.path.join(runner.EVALS_DIR, "runner", "runner.py"))
        # E11-7 items 5 and 6 add two call sites: the guarded manual-only routing launch and
        # the consumer trial. E11-45 S1 adds a seventh, the `write-fence` proof, and E11-46 R4
        # an eighth, the native read-boundary probe. All of them go through `Setup.launch`,
        # which is what this pins; the count is the canary that says a new path was added, so
        # that it can be checked rather than slipping in unseen.
        self.assertEqual(source.count("setup.launch("), 8)

    def test_the_cut_s_own_argv_carries_the_pair(self):
        setups = self.setups_of()
        argv = runner._launch_argv(setups["claude-code"], "launch.sh", "p", "w", "o",
                                   "available")
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")
        argv = runner._launch_argv(setups["opencode"], "launch.sh", "p", "w", "o", "available")
        self.assertEqual(argv[2], "openrouter/deepseek/deepseek-v4.1-flash")
        # Codex takes neither: its pair is the pilot home's config.toml lines
        argv = runner._launch_argv(setups["codex"], "launch.sh", "p", "w", "o", "available")
        self.assertNotIn("--model", argv)
        self.assertNotIn("--effort", argv)

    def test_the_cut_s_argv_is_unchanged_for_a_setup_that_pinned_nothing(self):
        campaign = runner.Campaign(self.campaign)
        plain = runner.ClaudeCodeSetup(campaign, stage=self.stage, name="claude-code")
        argv = runner._launch_argv(plain, "launch.sh", "p", "w", "o", "available")
        self.assertEqual(argv, ["sh", "launch.sh", "p", "w", "o",
                                "--plugin", "recheck-v2", "--plugin", "readers"])

    def resume_argv(self, setup, harness):
        # E11-28 fix 6 (D-U): a REAL launch is refused when run-leaf writability cannot be
        # established, and OpenCode's is established from its own `external_directory` rule.
        # A real home always has one — `setups/opencode/install.sh` writes it — so this bench
        # writes the rule it would have rather than driving a resume against a home no
        # campaign could have launched. Restored afterwards: the pilot homes are shared.
        if harness == "opencode":
            config = os.path.join(setup.home("available"), "xdg-config", "opencode",
                                  "opencode.json")
            before = runner.read_text(config, None)

            def restore():
                if before is None:
                    if os.path.isfile(config):
                        os.remove(config)
                else:
                    runner.write_text(config, before)
            self.addCleanup(restore)
            runner.write_json(config, {"permission": {"external_directory": {
                os.path.dirname(self.scratch.rstrip("/")) + "/**": "allow"}}})
        recorded = []

        def capture(command, **kwargs):
            recorded.append(list(command))
            return {"argv": list(command), "exit": 0, "stdout": "", "stderr": "",
                    "started_at": runner.now_iso(), "ended_at": runner.now_iso(),
                    "timed_out": False, "wall_seconds": 0.0, "label": "resume"}

        resume_path = os.path.join(self.scratch, "resume-%s.txt" % harness)
        runner.write_text(resume_path, "resume the run\n")
        out_dir = os.path.join(self.scratch, "second-%s" % harness)
        original = runner.run_cmd
        runner.run_cmd = capture
        try:
            runner._compaction_resume(
                runner.Campaign(self.campaign), setup, {"session": "s-1"}, resume_path,
                self.scratch, out_dir, 60, types.SimpleNamespace(compact_tokens=2000))
        finally:
            runner.run_cmd = original
        return recorded[0]

    def test_the_claude_compaction_resume_carries_the_pair(self):
        argv = self.resume_argv(self.setups_of()["claude-code"], "claude-code")
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")
        # the prompt stays the last word, after the flags
        self.assertEqual(argv[-1], "resume the run\n")

    def test_the_opencode_compaction_resume_takes_the_resolved_id(self):
        setup = self.setups_of()["opencode"]
        argv = self.resume_argv(setup, "opencode")
        self.assertEqual(argv[argv.index("--model") + 1],
                         "openrouter/deepseek/deepseek-v4.1-flash")


class CodexConfigLinesTest(RunnerCase):
    """E10-62 item 2: the plan's model and effort in the pilot home's own `config.toml`."""

    setups = ("codex",)

    def a_home(self, model="gpt-5.6-sol", effort="medium"):
        """A home in the shape `setups/codex/install.sh` writes: the three copied lines."""
        home = os.path.join(self.scratch, "codex-home")
        runner.ensure_dir(os.path.join(home, "child"))
        body = ('model = "gpt-6-astra"\n'
                'model_reasoning_effort = "high"\n'
                'sandbox_mode = "workspace-write"\n'
                'approval_policy = "never"\n'
                'web_search = "disabled"\n\n'
                '[features]\nshell_snapshot = false\n')
        runner.write_text(os.path.join(home, "config.toml"), body)
        runner.write_text(os.path.join(home, "child", "config.toml"), body)
        setup = runner.CodexSetup(runner.Campaign(self.campaign), stage=self.stage,
                                  name="codex", model=model, effort=effort)
        return setup, home

    def test_both_config_files_take_the_plan_s_two_lines(self):
        setup, home = self.a_home()
        record = setup._write_model_lines(home)
        self.assertEqual([r["file"] for r in record["written"]],
                         ["config.toml", os.path.join("child", "config.toml")])
        for name in ("config.toml", os.path.join("child", "config.toml")):
            text = runner.read_text(os.path.join(home, name))
            self.assertIn('model = "gpt-5.6-sol"', text)
            self.assertIn('model_reasoning_effort = "medium"', text)
            self.assertNotIn("gpt-6-astra", text)
            self.assertNotIn('model_reasoning_effort = "high"', text)

    def test_sandbox_mode_still_comes_from_the_real_config(self):
        setup, home = self.a_home()
        setup._write_model_lines(home)
        for name in ("config.toml", os.path.join("child", "config.toml")):
            text = runner.read_text(os.path.join(home, name))
            self.assertIn('sandbox_mode = "workspace-write"', text)
            self.assertIn("shell_snapshot = false", text)
            self.assertIn('approval_policy = "never"', text)

    def test_it_writes_nothing_outside_the_home(self):
        setup, home = self.a_home()
        record = setup._write_model_lines(home)
        for row in record["written"]:
            self.assertFalse(os.path.isabs(row["file"]))
        self.assertEqual(record["machine_codex_home"], "never written")

    def test_a_setup_that_pinned_nothing_leaves_the_config_alone(self):
        setup, home = self.a_home(model=None, effort=None)
        before = runner.read_text(os.path.join(home, "config.toml"))
        record = setup._write_model_lines(home)
        self.assertEqual(record["written"], [])
        self.assertEqual(runner.read_text(os.path.join(home, "config.toml")), before)

    def test_a_config_with_no_line_to_replace_is_a_failure(self):
        setup, home = self.a_home()
        runner.write_text(os.path.join(home, "config.toml"), 'sandbox_mode = "read-only"\n')
        with self.assertRaises(runner.Failure) as caught:
            setup._write_model_lines(home)
        self.assertIn("holds no model", str(caught.exception))

    def test_only_the_effort_line_moves_when_only_an_effort_is_pinned(self):
        setup, home = self.a_home(model=None, effort="low")
        setup._write_model_lines(home)
        text = runner.read_text(os.path.join(home, "config.toml"))
        self.assertIn('model = "gpt-6-astra"', text)
        self.assertIn('model_reasoning_effort = "low"', text)


class OpenCodeModelMappingTest(RunnerCase):
    """E10-62 item 2: the plan's full `openrouter/...` id, and the short names it took."""

    setups = ("opencode",)

    def setup_named(self, model):
        return runner.OpenCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                    name="opencode", model=model)

    def test_the_short_names_and_the_full_ids_both_resolve(self):
        self.assertEqual(self.setup_named("qwen").resolved_model(),
                         "openrouter/qwen/qwen3.8-flash")
        self.assertEqual(self.setup_named("deepseek").resolved_model(),
                         "openrouter/deepseek/deepseek-v4.1-flash")
        self.assertEqual(self.setup_named("openrouter/qwen/qwen3.8-flash").resolved_model(),
                         "openrouter/qwen/qwen3.8-flash")
        self.assertEqual(
            self.setup_named("openrouter/deepseek/deepseek-v4.1-flash").resolved_model(),
            "openrouter/deepseek/deepseek-v4.1-flash")
        self.assertEqual(self.setup_named(None).resolved_model(),
                         "openrouter/qwen/qwen3.8-flash")

    def test_the_launcher_is_handed_the_full_id(self):
        for given in ("deepseek", "openrouter/deepseek/deepseek-v4.1-flash"):
            setup = runner.OpenCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                         name="opencode-deepseek", model=given)
            argv = []

            def capture(command, **kwargs):
                argv.extend(command)
                return {"argv": list(command), "exit": 0, "stdout": "", "stderr": "",
                        "started_at": runner.now_iso(), "ended_at": runner.now_iso(),
                        "timed_out": False, "wall_seconds": 0.0, "label": "launch.sh"}

            original = runner.run_cmd
            runner.run_cmd = capture
            try:
                setup.launch("available", "/tmp/p.txt", "/tmp/ws", "/tmp/out", 60,
                             fake=os.path.join(FAKE, "opencode-launch.sh"))
            finally:
                runner.run_cmd = original
            self.assertIn("openrouter/deepseek/deepseek-v4.1-flash", argv, given)
            self.assertNotIn("deepseek", argv[1:2], given)

    def test_the_real_launch_sh_takes_the_full_id(self):
        """`setups/opencode/launch.sh` documents `qwen | deepseek | provider/model`."""
        text = runner.read_text(os.path.join(SETUPS_DIR, "opencode", "launch.sh"))
        self.assertIn("*/*) MODEL=\"$MODEL_ARG\" ;;", text)

    def test_install_passes_the_full_id_to_the_script(self):
        setup = runner.OpenCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                     name="opencode-deepseek",
                                     model="openrouter/deepseek/deepseek-v4.1-flash")
        runner.ensure_dir(os.path.join(self.stage, "plugins", "recheck-v2", "setups",
                                       "opencode"))
        runner.write_text(os.path.join(self.stage, "plugins", "recheck-v2", "setups",
                                       "opencode", "install.sh"), "#!/bin/sh\nexit 0\n")
        argv = []

        def capture(command, **kwargs):
            argv.extend(command)
            return {"argv": list(command), "exit": 0, "stdout": "", "stderr": "",
                    "started_at": runner.now_iso(), "ended_at": runner.now_iso(),
                    "timed_out": False, "wall_seconds": 0.0, "label": "install.sh"}

        original = runner.run_cmd
        runner.run_cmd = capture
        try:
            record = setup.install("available")
        finally:
            runner.run_cmd = original
        self.assertEqual(argv[argv.index("--model") + 1],
                         "openrouter/deepseek/deepseek-v4.1-flash")
        self.assertEqual(record["model"], "openrouter/deepseek/deepseek-v4.1-flash")
        self.assertEqual(argv[argv.index("--setup") + 1], setup.home("available"))


# --------------------------------------- item 4: model.json carries the plan's configured pair


class ConfiguredPairTest(RunnerCase):
    """E10-62 item 4: `configured: {model, effort}` from the PLAN, on all three harnesses.

    The defect this closes: `ClaudeCodeSetup.model_record` built `configured` from
    `launch.json`'s `model` key, and `setups/claude-code/launch.sh` writes that key as
    `init.get("model")` — the session's own init event — so the field labelled "what the
    launcher was told" held an observation. Codex's `launch.json` carries no model key and
    OpenCode's launcher writes no `launch.json`, so both read `null`.
    """

    def harness_dir(self, name, payload, as_json=False):
        directory = os.path.join(self.scratch, "harness-%s" % len(os.listdir(self.scratch)))
        runner.ensure_dir(directory)
        if as_json:
            runner.write_json(os.path.join(directory, name), payload)
        else:
            runner.write_text(os.path.join(directory, name),
                              "\n".join(json.dumps(r) for r in payload) + "\n")
        return directory

    def test_claude_code_configured_is_the_plan_s_pair_not_the_init_event(self):
        directory = self.harness_dir("trace.jsonl", [
            {"type": "system", "subtype": "init", "session_id": "s1",
             "model": "claude-opus-5-20260101"},
            {"type": "assistant", "session_id": "s1", "effort": "medium",
             "message": {"model": "claude-opus-5-20260101"}}])
        # launch.sh's own document, with `model` = the init event and the two new keys beside it
        runner.write_json(os.path.join(directory, "launch.json"),
                          {"ok": True, "session_id": "s1", "model": "claude-opus-5-20260101",
                           "configured_model": "opus", "configured_effort": "medium"})
        setup = runner.ClaudeCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                       name="claude-code", model="opus", effort="medium")
        record = setup.model_record(directory)
        self.assertEqual(record["configured"], {
            "model": "opus", "effort": "medium",
            "source": record["configured"]["source"],
            "note": record["configured"]["note"]})
        self.assertIn("the plan's setup entry", record["configured"]["source"])
        # the observation stays an observation, in its own fields
        self.assertEqual(record["id"], "claude-opus-5-20260101")
        self.assertEqual(record["init_model"], "claude-opus-5-20260101")
        self.assertNotEqual(record["configured"]["model"], record["init_model"])
        # and what the launcher itself recorded sits beside it
        self.assertEqual(record["launcher_recorded"]["model"], "opus")
        self.assertEqual(record["launcher_recorded"]["effort"], "medium")

    def test_the_old_defect_cannot_come_back(self):
        """A `launch.json` whose `model` is the init event no longer reaches `configured`."""
        directory = self.harness_dir("trace.jsonl", [
            {"type": "system", "subtype": "init", "session_id": "s1", "model": "some-init-id"},
            {"type": "assistant", "session_id": "s1", "message": {"model": "some-init-id"}}])
        runner.write_json(os.path.join(directory, "launch.json"),
                          {"session_id": "s1", "model": "some-init-id"})
        setup = runner.ClaudeCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                       name="claude-code", model="opus", effort="medium")
        record = setup.model_record(directory)
        self.assertEqual(record["configured"]["model"], "opus")
        self.assertNotEqual(record["configured"]["model"], "some-init-id")
        self.assertIsNone(record["launcher_recorded"]["model"])

    def test_codex_configured_is_the_plan_s_pair(self):
        directory = self.harness_dir("rollout.jsonl", [
            {"type": "session_meta", "payload": {"type": "session_meta", "id": "t1"}},
            {"type": "turn_context", "payload": {"type": "turn_context",
                                                 "model": "gpt-5.6-sol", "effort": "medium"}}])
        setup = runner.CodexSetup(runner.Campaign(self.campaign), stage=self.stage,
                                  name="codex", model="gpt-5.6-sol", effort="medium")
        record = setup.model_record(directory)
        self.assertEqual(record["configured"]["model"], "gpt-5.6-sol")
        self.assertEqual(record["configured"]["effort"], "medium")
        self.assertIn("config.toml", record["configured"]["reaches_the_session_by"])
        self.assertEqual(record["id"], "gpt-5.6-sol")
        self.assertEqual(record["effort"], "medium")

    def test_opencode_configured_is_the_plan_s_model_and_a_null_effort(self):
        directory = self.harness_dir("session.json", {"session_id": "s9", "records": [
            {"data": {"role": "assistant", "modelID": "deepseek-v4.1-flash",
                      "providerID": "openrouter"}}]}, as_json=True)
        setup = runner.OpenCodeSetup(
            runner.Campaign(self.campaign), stage=self.stage, name="opencode-deepseek",
            model="openrouter/deepseek/deepseek-v4.1-flash")
        record = setup.model_record(directory)
        self.assertEqual(record["configured"]["model"],
                         "openrouter/deepseek/deepseek-v4.1-flash")
        self.assertIsNone(record["configured"]["effort"])
        self.assertIsNone(record["effort"])   # E10-26
        self.assertEqual(record["id"], "openrouter/deepseek-v4.1-flash")

    def test_every_harness_carries_both_keys(self):
        for setup in (runner.ClaudeCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                             name="claude-code", model="opus",
                                             effort="medium"),
                      runner.CodexSetup(runner.Campaign(self.campaign), stage=self.stage,
                                        name="codex", model="gpt-5.6-sol", effort="medium"),
                      runner.OpenCodeSetup(runner.Campaign(self.campaign), stage=self.stage,
                                           name="opencode",
                                           model="openrouter/qwen/qwen3.8-flash")):
            empty = os.path.join(self.scratch, "empty-%s" % setup.name)
            runner.ensure_dir(empty)
            configured = setup.model_record(empty)["configured"]
            self.assertIn("model", configured, setup.name)
            self.assertIn("effort", configured, setup.name)
            self.assertEqual(configured["model"], setup.resolved_model(), setup.name)
            self.assertEqual(configured["effort"], setup.effort, setup.name)


class ConfiguredPairInTheRecordTest(RunnerCase):
    """E10-62 item 4: both `model.json` write sites, on a real trial the runner drove."""

    def setup_spec(self, name):
        if name == "opencode":
            return {"name": "opencode", "harness": "opencode",
                    "model": "openrouter/qwen/qwen3.8-flash"}
        if name == "codex":
            return {"name": "codex", "harness": "codex", "model": "gpt-5.6-sol",
                    "effort": "medium"}
        return {"name": name, "harness": name, "model": "opus", "effort": "medium"}

    def test_the_comparison_path_writes_the_plan_s_pair(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        model = runner.read_json(os.path.join(self.campaign, "trials", tid, "model.json"))
        self.assertEqual(model["configured"]["model"], "opus")
        self.assertEqual(model["configured"]["effort"], "medium")
        # and the launcher was actually handed them
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertIn("--model", command["argv"])
        self.assertEqual(command["argv"][command["argv"].index("--model") + 1], "opus")
        self.assertEqual(command["argv"][command["argv"].index("--effort") + 1], "medium")
        self.assertEqual(model["launcher_recorded"]["model"], "opus")
        self.assertEqual(model["launcher_recorded"]["effort"], "medium")

    def test_the_routing_path_writes_the_plan_s_pair(self):
        entry = self.plan_document["routing_entries"][0]
        tid = runner.routing_trial_id("claude-code", entry, 1)
        got = cli(["routing", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(got.returncode, 0, got.stderr)
        model = runner.read_json(os.path.join(self.campaign, "trials", tid, "model.json"))
        self.assertEqual(model["configured"]["model"], "opus")
        self.assertEqual(model["configured"]["effort"], "medium")


if __name__ == "__main__":
    unittest.main()


# ------------------------------------- E10-64: every refusal precedes the first directory


class RefusedPlanLeavesNothingTest(RunnerCase):
    """E10-64 (Astra's recheck3, item 1): a refused plan makes no campaign skeleton.

    `validate_plan` checked the whole plan before any RECORD was written, but `do_plan` called
    `campaign.ensure()` first, so a plan refused for a bad model, a bad effort or an unknown
    key still left a campaign root behind holding empty `records/`, `tmp/` and `trials/`.
    E10-43 finding 4's own words are "before any write", and a directory is a write. These
    tests use a campaign path that does not exist yet, which is the only way the difference
    shows: `RunnerCase.setUp` builds its own campaign, so a test that reused it would pass
    either way.
    """

    SKELETON = ("records", "tmp", "trials")

    def unused_campaign(self):
        path = os.path.join(self.scratch, "never-made-%d" % len(os.listdir(self.scratch)))
        self.assertFalse(os.path.exists(path))
        return path

    def refuse_into(self, path, setups):
        plan = runner.default_plan("test")
        plan["setups"] = setups
        plan_path = os.path.join(self.scratch, "refused-%d.json" % len(os.listdir(self.scratch)))
        runner.write_json(plan_path, plan)
        got = cli(["plan", "--campaign", path, "--plan", plan_path], env=self.held_out_env())
        self.assertEqual(got.returncode, 2, got.stdout)
        return got

    def assert_nothing_made(self, path):
        self.assertFalse(os.path.exists(path),
                         "the refused plan left %s behind: %s"
                         % (path, os.listdir(path) if os.path.isdir(path) else "?"))

    def test_a_bad_model_leaves_no_campaign_directory(self):
        path = self.unused_campaign()
        got = self.refuse_into(path, [{"name": "codex", "harness": "codex", "model": 5}])
        self.assertIn("'model' must be a string", got.stderr)
        self.assert_nothing_made(path)

    def test_a_bad_effort_leaves_no_campaign_directory(self):
        path = self.unused_campaign()
        self.refuse_into(path, [{"name": "codex", "harness": "codex", "effort": ["medium"]}])
        self.assert_nothing_made(path)

    def test_an_unknown_setup_key_leaves_no_campaign_directory(self):
        path = self.unused_campaign()
        self.refuse_into(path, [{"name": "codex", "harness": "codex", "modle": "gpt-5.6-sol"}])
        self.assert_nothing_made(path)

    def test_an_effort_on_a_harness_that_takes_none_leaves_no_campaign_directory(self):
        path = self.unused_campaign()
        self.refuse_into(path, [{"name": "opencode", "harness": "opencode",
                                 "model": "openrouter/qwen/qwen3.8-flash",
                                 "effort": "medium"}])
        self.assert_nothing_made(path)

    def test_an_unknown_harness_leaves_no_campaign_directory(self):
        path = self.unused_campaign()
        self.refuse_into(path, [{"name": "nope", "harness": "nope"}])
        self.assert_nothing_made(path)

    def test_an_accepted_plan_still_makes_the_skeleton(self):
        """The reorder must not stop `plan` building the campaign it accepts."""
        path = self.unused_campaign()
        plan = runner.default_plan("test")
        plan_path = os.path.join(self.scratch, "accepted.json")
        runner.write_json(plan_path, plan)
        # `plan` needs the stage record the fixture campaign carries, so accept into that one.
        got = cli(["plan", "--campaign", self.campaign, "--refresh", "--plan", plan_path],
                  env=self.held_out_env())
        self.assertEqual(got.returncode, 0, got.stderr)
        for name in self.SKELETON:
            self.assertTrue(os.path.isdir(os.path.join(self.campaign, name)), name)
        self.assert_nothing_made(path)
