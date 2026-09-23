"""E13 pick P6 (SB-14): the Codex per-trial session-folder lock, and its preflight target.

SB-14's finding: every Codex launch in a condition home could read the whole home, which keeps
every earlier session's rollout under `$CODEX_HOME/sessions/`, and the read-boundary preflight
never tested that target. E13 slice 3 measured (codex-cli 0.155.1) that no setting moves the
rollout folder but CODEX_HOME itself, so the lock is a per-launch home, `<out-dir>/codex-home`,
built by `setups/codex/launch.sh`'s session-lock block (byte-identical in the pilot's launcher and
in both cores' Codex launchers). This file proves, with no model and no Codex:

- the lock block is byte-identical in the three launchers;
- the launcher, driven with a stub `codex`, runs the session in `<out>/codex-home` and writes
  nothing into the condition home's `sessions/`;
- the preflight names a sibling launch's session folder (and the condition home's shared
  folders) as targets, and a readable sibling fails the preflight while a refused one passes;
- on a SEALED plan the real wall refuses the sibling launch's session folder (sandbox-exec, a
  plain `python3 -c` child).

Nothing here opens `evals/answer-key/`, the held-out set or any routing request.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from testlib import REPO, RunnerCase, runner

LAUNCHERS = [os.path.join(REPO, "plugins", name, "setups", "codex", "launch.sh")
             for name in ("recheck-v2", "build-v2", "signoff-v2")]
BLOCK = re.compile(r"# >>> session lock.*?# <<< session lock <<<\n", re.S)


class TheLockBlockIsOneBlockTest(unittest.TestCase):
    def test_the_three_launchers_carry_the_same_locking_lines(self):
        blocks = []
        for path in LAUNCHERS:
            with open(path) as handle:
                found = BLOCK.findall(handle.read())
            self.assertEqual(len(found), 1, path)
            blocks.append(found[0])
        self.assertEqual(len(set(blocks)), 1, "the lock block differs between the launchers")


class TheLauncherUsesItsOwnHomeTest(unittest.TestCase):
    """The pilot's launcher with a stub `codex` that writes a rollout where CODEX_HOME says."""

    def test_the_session_lands_in_the_launch_home_and_never_in_the_condition_home(self):
        root = tempfile.mkdtemp(prefix="lock-launch-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, root, True)
        binaries = os.path.join(root, "bin")
        os.makedirs(binaries)
        stub = os.path.join(binaries, "codex")
        runner.write_text(stub, "#!/bin/sh\n"
                          "d=\"$CODEX_HOME/sessions/2026/09/23\"; mkdir -p \"$d\"\n"
                          "echo '{\"type\":\"session_meta\",\"payload\":{\"id\":\"t-1\"}}' "
                          "> \"$d/rollout-2026-09-23T00-00-00-t-1.jsonl\"\n"
                          "echo '{\"type\":\"thread.started\",\"thread_id\":\"t-1\"}'\n")
        os.chmod(stub, 0o755)
        condition = os.path.join(root, "condition")
        os.makedirs(os.path.join(condition, "child"))
        os.makedirs(os.path.join(condition, "plugins", "cache", "m", "p", "0.1.0"))
        runner.write_text(os.path.join(condition, "config.toml"),
                          'model = "m"\n\n[shell_environment_policy.set]\nCODEX_HOME = "%s"\n'
                          'UV_CACHE_DIR = "%s"\n' % (os.path.join(condition, "child"),
                                                     os.path.join(condition, "child", "uv-cache")))
        runner.write_text(os.path.join(condition, "child", "config.toml"), 'model = "m"\n')
        workspace = os.path.join(root, "ws")
        os.makedirs(workspace)
        prompt = os.path.join(root, "prompt.txt")
        runner.write_text(prompt, "a prompt this test wrote\n")
        out = os.path.join(root, "harness")
        got = subprocess.run(["sh", LAUNCHERS[0], prompt, workspace, out], capture_output=True,
                             text=True, env={"PATH": binaries + ":/usr/bin:/bin", "HOME": root,
                                             "RECHECK_CODEX_HOME": condition})
        self.assertEqual(got.returncode, 0, got.stderr)
        launch = runner.read_json(os.path.join(out, "launch.json"))
        mine = os.path.realpath(os.path.join(out, "codex-home"))
        self.assertEqual(os.path.realpath(launch["codex_home"]), mine)
        self.assertTrue(os.path.isfile(os.path.join(out, "rollout.jsonl")))
        self.assertFalse(os.path.exists(os.path.join(condition, "sessions")))
        self.assertTrue(os.path.isdir(os.path.join(mine, "plugins", "cache", "m", "p", "0.1.0")))
        self.assertFalse(os.path.islink(os.path.join(mine, "plugins")))
        with open(os.path.join(mine, "config.toml")) as handle:
            config = handle.read()
        self.assertIn('CODEX_HOME = "%s"' % os.path.join(mine, "child"), config)
        self.assertIn(os.path.join(condition, "child", "uv-cache"), config)
        command = runner.read_json(os.path.join(out, "command.json"))
        self.assertEqual(command[command.index("--add-dir") + 1], os.path.join(mine, "child"))
        again = subprocess.run(["sh", LAUNCHERS[0], prompt, workspace, out], capture_output=True,
                               text=True, env={"PATH": binaries + ":/usr/bin:/bin", "HOME": root,
                                               "RECHECK_CODEX_HOME": condition})
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("refusing to overwrite", again.stderr)


class CodexCase(RunnerCase):
    setups = ("codex",)


class ThePreflightNamesTheLockTest(CodexCase):
    def test_a_sibling_launchs_session_folder_is_a_target(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, campaign.plan(), "codex")
        theirs = runner.trial_id("codex", "read-boundary-probe-b", "available", 1)
        targets = runner.session_lock_targets(campaign, setup, theirs)
        paths = [row["path"] for row in targets]
        self.assertIn(os.path.join(campaign.trial_dir(theirs), "harness", "codex-home",
                                   "sessions"), paths)
        self.assertIn(os.path.join(setup.home("available"), "sessions"), paths)
        self.assertIn(os.path.join(setup.home("available"), "child", "sessions"), paths)

    def test_no_lock_target_for_another_harness(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        self.assertEqual(runner.session_lock_targets(campaign, setup, "x"), [])

    def test_a_readable_sibling_fails_the_preflight_and_a_refused_one_passes(self):
        base = {"probe_ran": True, "exit": 0, "sentinel_outcome": "refused",
                "other_home_outcome": "refused", "other_home_sentinel_outcome": "refused",
                "discovered_other_trial_trees": [],
                "planted": {"sentinel_ok": True, "other_home_sentinel_ok": True,
                            "session_lock": [{"sentinel": "/s/1", "ok": True},
                                             {"sentinel": "/s/2", "ok": True}]}}
        refused = dict(base, session_lock_outcomes={"/s/1": "refused", "/s/2": "refused"})
        self.assertTrue(runner._read_boundary_separated(refused))
        readable = dict(base, session_lock_outcomes={"/s/1": "read", "/s/2": "refused"})
        self.assertFalse(runner._read_boundary_separated(readable))
        missing = dict(base, session_lock_outcomes={"/s/1": "refused"})
        self.assertFalse(runner._read_boundary_separated(missing))
        unplanted = dict(refused, planted=dict(base["planted"], session_lock=[
            {"sentinel": "/s/1", "ok": False}, {"sentinel": "/s/2", "ok": True}]))
        self.assertFalse(runner._read_boundary_separated(unplanted))

    def test_the_plain_child_reports_a_readable_sibling_session(self):
        """Unwalled, the filesystem lets the child read a sibling's session folder: not separated."""
        campaign = runner.Campaign(self.campaign)
        document = runner.read_boundary_probe(campaign, campaign.plan())
        row = document["rows"][0]
        self.assertTrue(row["probe_ran"], row)
        self.assertEqual(len(row["session_lock_outcomes"]), 3, row)
        self.assertIn("read", row["session_lock_outcomes"].values())
        self.assertFalse(row["separated"])

    def test_the_condition_homes_shared_sessions_are_refused_roots(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, campaign.plan(), "codex")
        home = setup.home("available")
        rows = runner.wall_refused_roots(campaign, setup, "available", [home])
        paths = {row["path"] for row in rows}
        self.assertIn(os.path.realpath(os.path.join(home, "sessions")), paths)
        self.assertIn(os.path.realpath(os.path.join(home, "child", "sessions")), paths)


@unittest.skipUnless(os.path.isfile(runner.SANDBOX_EXEC), "this machine has no sandbox-exec")
class TheWallRefusesTheSiblingTest(CodexCase):
    def test_the_walled_child_is_refused_every_lock_target(self):
        campaign = runner.Campaign(self.campaign)
        document = runner.read_json(campaign.campaign_json)
        document["sealed"] = True
        runner.write_json(campaign.campaign_json, document)
        setup = runner.setup_for(campaign, campaign.plan(), "codex")
        runner.ensure_dir(setup.home("available"))
        runner.write_text(os.path.join(setup.home("absent"), "install.json"), "{}\n")
        probe = runner.read_boundary_probe(campaign, campaign.plan())
        row = probe["rows"][0]
        self.assertTrue(row["walled"], row)
        self.assertTrue(row["probe_ran"], row)
        self.assertEqual(set(row["session_lock_outcomes"].values()), {"refused"}, row)
        self.assertTrue(all(p["ok"] for p in row["planted"]["session_lock"]), row)
        fact = row["unwalled_filesystem_fact"]
        self.assertIn("read", fact["session_lock_outcomes"].values())


if __name__ == "__main__":
    unittest.main()
