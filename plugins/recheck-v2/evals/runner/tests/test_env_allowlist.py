"""The environment allowlist of E10-7 and the one install-time credential of E10-20."""
import json
import os
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner

PLANTED = {
    "CLAUDE_CODE_X": "planted",
    "CLAUDECODE": "planted",
    "CODEX_X": "planted",
    "OPENROUTER_API_KEY": "planted",
    "FOO_TOKEN": "planted",
    "SOME_SECRET": "planted",
    "AWS_REGION": "planted",
    "GH_TOKEN": "planted",
    "GITHUB_ACTOR": "planted",
    "NOTION_KEY": "planted",
    "SLACK_TEAM": "planted",
    "SSH_AUTH_SOCK": "planted",
    "ANTHROPIC_API_KEY": "planted",
}


class AllowlistShapeTest(RunnerCase):
    def test_the_allowlist_holds_the_names_E10_7_names_plus_the_one_it_measured(self):
        """E10-7's seven, plus `USER`, which the clause about a harness that will not start
        under the allowlist added.

        Measured 2026-09-15 on Claude Code 2.1.272: with the seven alone a session answers
        `"Not logged in · Please run /login"` at cost 0; with `USER` it answers (cost
        0.011564); with `LOGNAME` instead of `USER` it does not. The harness reaches its
        Keychain item only when `USER` is set. `USER` names the process's own identity, carries
        no credential, and matches no banned shape (the next test).
        """
        self.assertEqual(
            sorted(runner.ALLOWED_ENV),
            sorted(["PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "TERM", "SHELL", "USER"]))
        self.assertIsNone(runner.BANNED_ENV_RE.match("USER"))
        self.assertEqual(runner.allowlist_env("/tmp/x", require_binaries=False)["USER"],
                         os.path.basename(os.path.expanduser("~")))

    def test_allowlist_env_starts_from_nothing_and_adds_only_the_allowed_names(self):
        built = runner.allowlist_env("/tmp/x", require_binaries=False)
        self.assertEqual(sorted(built), sorted(runner.ALLOWED_ENV))
        self.assertEqual(built["TMPDIR"], "/tmp/x")
        self.assertEqual(built["LANG"], "C.UTF-8")

    def test_every_banned_shape_matches_the_banned_pattern(self):
        for name in PLANTED:
            self.assertTrue(runner.BANNED_ENV_RE.match(name), "%s is not caught" % name)

    def test_a_harmless_name_does_not_match_the_banned_pattern(self):
        for name in ("PATH", "HOME", "TMPDIR", "LANG", "TERM", "SHELL", "COLUMNS"):
            self.assertIsNone(runner.BANNED_ENV_RE.match(name), name)

    def test_the_path_the_runner_builds_carries_the_fixed_system_entries_in_order(self):
        """The four system entries are present, in order, and nothing follows the last.

        They are appended only when the binaries' own locations did not already contribute
        them, so `/usr/bin` can sit earlier (git resolves there): the invariant is presence
        and relative order, not a fixed tail. Under `uv run python3` the interpreter's own
        directory joins the list too, which is why the earlier absolute-tail assertion was
        wrong on that interpreter and is recorded here as measured.
        """
        entries = runner.path_entries(require=False)
        for tail in runner.PATH_TAIL:
            self.assertIn(tail, entries, tail)
        positions = [entries.index(t) for t in runner.PATH_TAIL]
        self.assertEqual(positions, sorted(positions), "the system entries are out of order")
        self.assertEqual(entries[-1], runner.PATH_TAIL[-1])

    def test_the_path_names_every_binary_the_allowlist_needs(self):
        entries = runner.path_entries(require=False)
        for binary in runner.PATH_BINARIES:
            found = runner.which(binary)
            if not found:
                continue
            self.assertTrue(any(os.path.isfile(os.path.join(d, binary)) for d in entries),
                            "%s is not reachable from the PATH the runner builds" % binary)


class LaunchedChildEnvironmentTest(RunnerCase):
    """A real child process: the fake launcher records the names its environment carried."""

    def test_a_launched_child_holds_exactly_the_allowed_names_plus_its_launcher_pointer(self):
        environment = self.child_env(PLANTED)
        tid, got = self.run_trial(env=environment)
        self.assertEqual(got.returncode, 0, got.stderr)
        names = self._child_names(tid)
        planted = sorted(n for n in names if n in PLANTED)
        self.assertEqual(planted, [], "planted names reached the child: %s" % planted)
        banned = sorted(n for n in names if runner.BANNED_ENV_RE.match(n))
        # every banned-shaped name a child may carry is on DECLARED_ENV, with its reason
        self.assertEqual([n for n in banned if n not in runner.DECLARED_ENV], [],
                         "undeclared banned shapes reached the child: %s" % banned)
        self.assertEqual(banned, ["CLAUDE_CODE_TMPDIR"], banned)
        # Measured on this machine (macOS 25.6, Darwin 25.6.0), and recorded because it is
        # what E10-7 can and cannot reach: `env -i` plus the allowlist is exactly what the
        # runner hands its child, and the names below are added BELOW that boundary, by the
        # platform and by the two shims on the way to the launcher's own python:
        #   __CF_USER_TEXT_ENCODING   CoreFoundation, on every exec
        #   PWD, SHLVL                /bin/sh itself, running launch.sh
        #   SDKROOT, CPATH, LIBRARY_PATH, MANPATH   the /usr/bin/python3 xcrun shim, which
        #     re-execs the Xcode python with these set
        # None is a banned shape, none carries a credential, and none can be removed by the
        # parent: a launcher that starts a shell gets them. The load-bearing assertion is the
        # one above (no planted name, no banned shape).
        downstream = ("__CF_USER_TEXT_ENCODING", "PWD", "SHLVL", "SDKROOT", "CPATH",
                      "LIBRARY_PATH", "MANPATH")
        injected = sorted(n for n in names if n in downstream)
        # send-back 2: plus `CLAUDE_CODE_TMPDIR`, the one DECLARED name this harness's launches
        # carry. Claude Code otherwise makes its scratch at `/tmp/claude-<uid>`, one folder
        # shared by every Claude session on this Mac; behind the wall the live session died on
        # `mkdir '/tmp/claude-501'` after it had signed in and reached the model. The name is a
        # path the runner chose and carries no credential, which is why `DECLARED_ENV` names it
        # with that measurement beside it.
        self.assertEqual(sorted(n for n in names if n not in downstream),
                         sorted(list(runner.ALLOWED_ENV)
                                + ["SKILLS_V2_PILOT_HOME", "CLAUDE_CODE_TMPDIR"]),
                         "the child's environment is not the allowlist plus its pointers "
                         "(added below the boundary: %s)" % injected)
        for name in injected:
            self.assertIsNone(runner.BANNED_ENV_RE.match(name), name)

    def test_the_recorded_allowlist_names_carry_no_value(self):
        tid, got = self.run_trial(env=self.child_env(PLANTED))
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        for name in command["allowlisted_env_names"]:
            self.assertNotIn("=", name)
        blob = json.dumps(command)
        self.assertNotIn("planted", blob)

    def _child_names(self, tid):
        path = os.path.join(self.campaign, "trials", tid, "harness", "env-names.json")
        self.assertTrue(os.path.isfile(path), "the launcher recorded no environment names")
        return runner.read_json(path)["names"]


class InstallCredentialTest(RunnerCase):
    """E10-20: `install` is the only path that passes OPENROUTER_API_KEY, to one script."""

    def real_script(self, harness):
        return os.path.join(runner.PLUGIN_DIR, "setups", harness, "install.sh")

    def synthetic_home(self):
        """A HOME this test built, with an EMPTY auth store and nothing else (E10-59 (25)).

        The second round's pattern: a live-install proof needs no credential, so the store the
        scripts would write into is `{}` and stays `{}` unless a script writes it.
        """
        home = os.path.join(self.scratch, "synthetic-home")
        for rel in (".codex", ".config", os.path.join(".local", "share")):
            os.makedirs(os.path.join(home, rel), exist_ok=True)
        runner.write_text(os.path.join(home, ".codex", "auth.json"), "{}\n")
        return home

    def test_only_the_opencode_install_receives_the_credential_name(self):
        """E10-59 (25): this test RUNS THE REAL INSTALL SCRIPTS against a synthetic home.

        It used to compare dictionaries only — zero subprocess calls — so what it proved was
        that `campaign.env` puts the name in one place, never that the script on disk is the
        one that needs it or that the others do not. The three real scripts are run here, under
        a HOME this test built and a PATH without their binaries, so each stops at its own
        precondition and nothing is installed anywhere.
        """
        campaign = runner.Campaign(self.campaign)
        os.environ["OPENROUTER_API_KEY"] = "planted-not-a-real-key"
        self.addCleanup(os.environ.pop, "OPENROUTER_API_KEY", None)
        claude = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        codex = runner.CodexSetup(campaign, stage=self.stage)
        opencode = runner.OpenCodeSetup(campaign, stage=self.stage)
        # the two that must never see it
        for setup in (claude, codex):
            built = campaign.env(extra=setup.launch_env("available"), require_binaries=False)
            self.assertNotIn("OPENROUTER_API_KEY", built)
        # the one that does, and only through `install`
        built = campaign.env(extra={"RECHECK_OPENCODE_SETUP": "x",
                                    "OPENROUTER_API_KEY": os.environ["OPENROUTER_API_KEY"]},
                             require_binaries=False)
        self.assertIn("OPENROUTER_API_KEY", built)
        # a launch never carries it
        launch = campaign.env(extra=opencode.launch_env("available"), require_binaries=False)
        self.assertNotIn("OPENROUTER_API_KEY", launch)

        # ---- the real scripts, against the synthetic home
        home = self.synthetic_home()
        base = dict(campaign.env(require_binaries=False), HOME=home,
                    PATH="/usr/bin:/bin:/usr/sbin:/sbin")
        self.assertNotIn("OPENROUTER_API_KEY", base)
        setup_dir = os.path.join(home, "opencode-setup")
        runner.ensure_dir(setup_dir)
        runner.write_text(os.path.join(setup_dir, "auth.json"), "{}\n")

        # 1. the real OpenCode install, with the name absent: refused before anything is built
        refused = runner.run_cmd(
            ["sh", self.real_script("opencode"), "--setup", setup_dir,
             "--without", "recheck-v2"],
            env=base, timeout=180, label="the real opencode install, no credential name")
        self.assertEqual(refused["exit"], 3, refused["stderr"][-600:])
        self.assertIn("OPENROUTER_API_KEY is not set", refused["stderr"])
        self.assertEqual(runner.read_text(os.path.join(setup_dir, "auth.json")), "{}\n")

        # 2. the same real script with the name passed: past the credential gate, and it stops
        #    at the next precondition because this PATH has no npm
        passed = runner.run_cmd(
            ["sh", self.real_script("opencode"), "--setup", setup_dir,
             "--without", "recheck-v2"],
            env=dict(base, OPENROUTER_API_KEY=os.environ["OPENROUTER_API_KEY"]),
            timeout=180, label="the real opencode install, with the credential name")
        self.assertIn("credential: OPENROUTER_API_KEY set in this shell", passed["stdout"])
        self.assertNotEqual(passed["exit"], 0)
        # the VALUE never appears in anything the runner kept
        self.assertNotIn(os.environ["OPENROUTER_API_KEY"],
                         json.dumps({k: passed[k] for k in ("stdout", "stderr", "label")}))
        self.assertEqual(runner.read_text(os.path.join(setup_dir, "auth.json")), "{}\n")

        # 3. the other two real scripts never ask for it
        others = (("claude-code", ["sh", self.real_script("claude-code"), "--pilot-home",
                                   os.path.join(home, "cc"), "--without", "recheck-v2"], base),
                  ("codex", ["sh", self.real_script("codex"), "--without", "recheck-v2"],
                   dict(base, RECHECK_CODEX_HOME=os.path.join(home, "codex-home"))))
        for harness, argv, env in others:
            step = runner.run_cmd(argv, env=env, timeout=180,
                                  label="the real %s install" % harness)
            self.assertNotEqual(step["exit"], 0, harness)
            self.assertNotIn("OPENROUTER", step["stdout"] + step["stderr"], harness)
        # nothing was written outside the synthetic home this test built
        self.assertEqual(runner.read_text(os.path.join(home, ".codex", "auth.json")), "{}\n")

    def test_a_launch_of_every_setup_passes_only_that_setup_s_home_pointer(self):
        campaign = runner.Campaign(self.campaign)
        expected = {"claude-code": "SKILLS_V2_PILOT_HOME",
                    "codex": "RECHECK_CODEX_HOME",
                    "opencode": "RECHECK_OPENCODE_SETUP"}
        for harness, pointer in expected.items():
            setup = runner.make_setup(campaign, {"name": harness, "harness": harness})
            names = sorted(setup.launch_env("available"))
            self.assertEqual(names, [pointer], "%s: %s" % (harness, names))


if __name__ == "__main__":
    unittest.main()


class WalledLaunchEnvironmentTest(RunnerCase):
    """A2: the proxy names, and the wall's two declarations, on a WALLED launch only.

    The allowlist itself does not grow. `allowlist_env` starts from nothing and adds the names
    it is given; the wall gives a walled launch four proxy names in both cases plus
    `RECHECK_HARNESS_SANDBOX` and `RECHECK_WALL_PROBE`, and gives an unwalled one none of
    them, which is why the fake-launcher test above still sees the allowlist plus one pointer.
    """

    def test_the_proxy_names_are_declared_in_both_cases(self):
        self.assertEqual(sorted(runner.PROXY_ENV),
                         sorted(["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY",
                                 "https_proxy", "http_proxy", "all_proxy", "no_proxy"]))

    def test_no_declared_wall_name_matches_a_banned_shape(self):
        for name in runner.PROXY_ENV + ("RECHECK_HARNESS_SANDBOX", "RECHECK_WALL_PROBE"):
            self.assertIsNone(runner.BANNED_ENV_RE.match(name), name)

    def test_an_unwalled_launch_carries_none_of_them(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        with setup.walled("available", os.path.join(self.scratch, "harness"),
                          launcher=self.fake_launcher("claude-code")) as wall:
            self.assertEqual(wall.env, {})
        # send-back 5: the uv names ride with the wall too, so an unwalled launch keeps the
        # machine's own uv setup and the fake harness's real-core runs are unaffected.
        self.assertNotIn("UV_CACHE_DIR", setup.launch_env("available"))
        self.assertNotIn("UV_OFFLINE", setup.launch_env("available"))

    def test_a_walled_launch_carries_the_proxy_url_and_the_wall_declarations(self):
        """No harness and no model: the wall is built directly, around nothing."""
        campaign = runner.Campaign(self.campaign)
        # `walled` bypasses for a synthetic campaign, which every test campaign is, so the
        # pieces are exercised directly rather than through a campaign that would skip them.
        log = os.path.join(self.scratch, "proxy.jsonl")
        proxy = runner.wall_proxy.WallProxy(["api.anthropic.com"], log)
        proxy.start()
        self.addCleanup(proxy.stop)
        probe = runner.wall_probe_path(campaign)
        wall = runner._Wall("/dev/null", "/dev/null", {}, proxy, {"sealed": True},
                            probe=probe)
        self.assertEqual(wall.env["HTTPS_PROXY"], "http://127.0.0.1:%d" % proxy.port)
        self.assertEqual(wall.env["https_proxy"], wall.env["HTTPS_PROXY"])
        self.assertEqual(wall.env["NO_PROXY"], runner.PROXY_BYPASS)
        self.assertEqual(wall.env["no_proxy"], runner.PROXY_BYPASS)
        self.assertEqual(wall.env["RECHECK_HARNESS_SANDBOX"], runner.WALL_MARKER)
        self.assertEqual(wall.env["RECHECK_WALL_PROBE"], probe)
        self.assertTrue(os.path.isfile(probe))
        built = campaign.env(extra=wall.env, require_binaries=False)
        self.assertEqual(sorted(n for n in runner.banned_names(built)), [])
        self.assertEqual(wall.prefix(["sh", "launch.sh"]),
                         ["/usr/bin/sandbox-exec", "-f", "/dev/null", "sh", "launch.sh"])

    def test_the_wall_probe_sits_outside_every_root_a_launch_profile_allows(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        probe = runner.wall_probe_path(campaign)
        spec = runner.wall_spec(campaign, setup, "available",
                                os.path.join(campaign.trials, "a-trial", "harness"),
                                workspace=os.path.join(self.scratch, "ws"),
                                scratch=os.path.join(self.scratch, "tree", "scratch"))
        for row in spec["read_roots"] + spec["write_roots"]:
            self.assertFalse(runner.path_contains(row["path"], probe),
                             "%s allows the probe file" % row["path"])


class ClaudeCodeTmpdirIsDeclaredTest(RunnerCase):
    """Send-back 2: the one banned-shaped name a Claude Code launch carries on purpose."""

    def test_it_is_on_DECLARED_ENV_with_the_measurement_beside_it(self):
        self.assertIn("CLAUDE_CODE_TMPDIR", runner.DECLARED_ENV)
        reason = runner.DECLARED_ENV["CLAUDE_CODE_TMPDIR"]
        self.assertIn("shared", reason)
        self.assertIn("TMPDIR", reason)

    def test_run_cmd_lets_a_declared_name_through_and_still_refuses_an_undeclared_one(self):
        campaign = runner.Campaign(self.campaign)
        good = campaign.env(extra={"CLAUDE_CODE_TMPDIR": os.path.join(self.scratch, "cc")},
                            require_binaries=False)
        step = runner.run_cmd(["/usr/bin/true"], env=good, label="a declared name")
        self.assertEqual(step["exit"], 0)
        bad = dict(good, CLAUDE_CODE_SOMETHING_ELSE="planted")
        with self.assertRaises(runner.Failure) as caught:
            runner.run_cmd(["/usr/bin/true"], env=bad, label="an undeclared name")
        self.assertIn("CLAUDE_CODE_SOMETHING_ELSE", str(caught.exception))
        self.assertNotIn("CLAUDE_CODE_TMPDIR", str(caught.exception))

    def test_only_claude_code_launches_carry_it(self):
        campaign = runner.Campaign(self.campaign)
        tmpdir = os.path.join(self.scratch, "tmpdir")
        runner.ensure_dir(tmpdir)
        self.assertEqual(
            sorted(runner.ClaudeCodeSetup(campaign, stage=self.stage).scratch_env(tmpdir)),
            ["CLAUDE_CODE_TMPDIR"])
        self.assertEqual(runner.CodexSetup(campaign, stage=self.stage).scratch_env(tmpdir), {})
        self.assertEqual(
            runner.OpenCodeSetup(campaign, stage=self.stage, name="opencode")
            .scratch_env(tmpdir), {})
