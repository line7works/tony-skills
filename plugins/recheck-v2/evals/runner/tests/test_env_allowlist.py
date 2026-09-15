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
        self.assertEqual(banned, [], "banned shapes reached the child: %s" % banned)
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
        self.assertEqual(sorted(n for n in names if n not in downstream),
                         sorted(list(runner.ALLOWED_ENV) + ["SKILLS_V2_PILOT_HOME"]),
                         "the child's environment is not the allowlist plus the one pointer "
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

    def test_only_the_opencode_install_receives_the_credential_name(self):
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
