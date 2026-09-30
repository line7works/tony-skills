"""The setup home guard (E14 slice 3c review F1+F2; check 5's C3C5-1, C3C5-2 and C3C5-6): every script of
this core that creates or writes under a path its caller names refuses, exit 2 and nothing created, a path
under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, as given, through a symlink or a `..`; an ordinary
path passes the guard. The scripts: both installers; both launchers (the out-dir, the installed or condition
home, each --writable root); negative-cases.py behind both negative-tests.sh; the seeded cases' observe.py
and a family's build.py (caselib); and, where the core has them, seven-stations.sh and the replay's --keep.
A fake HOME and inert `claude`, `codex` and `uv` stand-ins first on PATH; never the real homes or commands."""
import os
import subprocess
import sys
import unittest

import testlib

STANDIN = "#!/bin/sh\ncase \"$*\" in *'plugin install'*) echo '{\"outcome\":\"ok\"}';; esac\nexit 0\n"
CONFIG = 'model = "m"\nmodel_reasoning_effort = "high"\nsandbox_mode = "workspace-write"\n'
SETUPS = os.path.join(testlib.PLUGIN, "setups")
SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
SEVEN = os.path.join(SETUPS, "seven-stations.sh")
REPLAY = os.path.join(testlib.PLUGIN, "evals", "replay", "replay.py")
HARNESSES = ("claude-code", "codex")


def listing(root):
    return sorted(os.path.relpath(os.path.join(d, n), root) for d, ds, fs in os.walk(root) for n in ds + fs)


@unittest.skipUnless(os.path.isdir(SETUPS), "no setups folder beside this copy")
class TheHomeGuard(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("setup-guard-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.home = h = os.path.join(self.tmp, "home")
        for rel in (".codex", os.path.join(".claude", "config"), os.path.join(".local", "share", "skills-v2-locked"),
                    "ordinary", os.path.join("iso-claude", "config"), "iso-codex", "ws"):
            os.makedirs(os.path.join(h, rel))
        testlib.write_text(os.path.join(h, ".codex", "config.toml"), CONFIG)
        testlib.write_text(os.path.join(h, "iso-codex", "config.toml"), CONFIG)
        testlib.write_text(os.path.join(h, "prompt.txt"), "a prompt this test wrote\n")
        os.symlink(os.path.join(h, ".codex"), os.path.join(h, "link"))
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        for name, body in (("claude", STANDIN), ("codex", STANDIN), ("uv", "#!/bin/sh\nexit 1\n")):
            testlib.write_text(os.path.join(bin_dir, name), body)
            os.chmod(os.path.join(bin_dir, name), 0o755)
        self.env = testlib.base_env({"HOME": h, "PATH": bin_dir + os.pathsep + os.environ.get("PATH", "")})
        self.protected = (h + "/.claude/x", h + "/.codex/x", h + "/.local/share/skills-v2-pilot/x",
                          h + "/.local/share/skills-v2-locked/x", h + "/link/x", h + "/ordinary/../.claude/x")
        self.prefix = testlib.PREFIX

    def run_it(self, argv, extra=None):
        env = dict(self.env)
        env.update(extra or {})
        return subprocess.run(argv, env=env, cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=600).returncode

    def assert_refused(self, argv, extra=None, label=None):
        before = listing(self.tmp)
        self.assertEqual(self.run_it(argv, extra), 2, label or argv)
        self.assertEqual(listing(self.tmp), before, label or argv)

    def install(self, harness, target):
        return self.run_it(["sh", os.path.join(SETUPS, harness, "install.sh"), "--home", target])

    def launch(self, harness, out, home=None, writable=None):
        name = "CLAUDE_HOME" if harness == "claude-code" else "CODEX_HOME"
        home = home or os.path.join(self.home, "iso-claude" if harness == "claude-code" else "iso-codex")
        argv = ["sh", os.path.join(SETUPS, harness, "launch.sh"), os.path.join(self.home, "prompt.txt"),
                os.path.join(self.home, "ws"), out] + (["--writable", writable] if writable else [])
        return argv, {"%s_%s" % (self.prefix, name): home}

    def test_every_protected_home_is_refused_before_anything_is_created(self):
        for harness in HARNESSES:
            for target in self.protected:
                before = listing(self.tmp)
                self.assertEqual(self.install(harness, target), 2, (harness, target))
                self.assertEqual(listing(self.tmp), before, (harness, target))

    def test_an_ordinary_home_passes_the_guard(self):
        for harness in HARNESSES:
            target = os.path.join(self.home, "ordinary", harness)
            self.assertEqual(self.install(harness, target), 0, harness)
            self.assertTrue(os.path.isdir(os.path.join(target, "marketplace")), harness)

    def test_negative_tests_refuse_a_protected_out(self):
        for harness in HARNESSES:
            for target in self.protected:
                self.assert_refused(["sh", os.path.join(SETUPS, harness, "negative-tests.sh"), target,
                                     "--case", "missing-resource"], label=(harness, target))

    def test_negative_tests_pass_an_ordinary_out(self):
        for harness in HARNESSES:
            out = os.path.join(self.home, "ordinary", "neg-" + harness)
            code = self.run_it(["sh", os.path.join(SETUPS, harness, "negative-tests.sh"), out,
                                "--case", "missing-resource"])
            self.assertNotEqual(code, 2, harness)
            self.assertTrue(os.path.isdir(os.path.join(out, "missing-resource")), harness)

    def test_the_launchers_refuse_a_protected_out_dir(self):
        for harness in HARNESSES:
            for target in self.protected:
                argv, extra = self.launch(harness, target)
                self.assert_refused(argv, extra, (harness, target))

    def test_the_launchers_refuse_a_protected_home(self):
        h = self.home
        out = os.path.join(h, "ordinary", "run")
        cases = [self.launch("claude-code", out, home=h + "/.claude"),
                 self.launch("claude-code", out, home=h + "/ordinary/../.claude")]
        for home in (h + "/.codex", h + "/link", h + "/.local/share/skills-v2-locked", h + "/ordinary/../.codex"):
            cases.append(self.launch("codex", out, home=home))
        for writable in (h + "/.codex", h + "/link", h + "/.local/share/skills-v2-locked"):
            cases.append(self.launch("codex", out, writable=writable))
        for argv, extra in cases:
            self.assert_refused(argv, extra, (argv[1:], extra))

    def test_the_launchers_pass_an_ordinary_out_dir(self):
        for harness, kept in (("claude-code", "launch.json"), ("codex", "codex-home")):
            out = os.path.join(self.home, "ordinary", "run-" + harness)
            writable = os.path.join(self.home, "ws") if harness == "codex" else None
            argv, extra = self.launch(harness, out, writable=writable)
            self.assertNotEqual(self.run_it(argv, extra), 2, harness)
            self.assertTrue(os.path.exists(os.path.join(out, kept)), harness)

    def seeded(self):
        got = subprocess.run([sys.executable, os.path.join(SEEDED, "observe.py"), "--list"], env=self.env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        family, case = got.stdout.decode("utf-8").splitlines()[0].split()
        return family, case

    @unittest.skipUnless(os.path.isfile(os.path.join(SEEDED, "observe.py")), "no seeded cases beside this copy")
    def test_the_seeded_case_scripts_refuse_a_protected_out(self):
        family, case = self.seeded()
        for target in self.protected:
            self.assert_refused([sys.executable, os.path.join(SEEDED, "observe.py"), "--case", case, "--out", target],
                                label=("observe.py", target))
            self.assert_refused([sys.executable, os.path.join(SEEDED, family, "build.py"), "--case", case,
                                 "--out", target], label=("build.py", target))

    @unittest.skipUnless(os.path.isfile(os.path.join(SEEDED, "observe.py")), "no seeded cases beside this copy")
    def test_the_seeded_case_scripts_pass_an_ordinary_out(self):
        family, case = self.seeded()
        out = os.path.join(self.home, "ordinary", "built")
        self.assertEqual(self.run_it([sys.executable, os.path.join(SEEDED, family, "build.py"), "--case", case,
                                      "--out", out]), 0)
        self.assertTrue(os.path.isfile(os.path.join(out, case, "manifest.json")))
        out = os.path.join(self.home, "ordinary", "observed")
        self.assertNotEqual(self.run_it([sys.executable, os.path.join(SEEDED, "observe.py"), "--case", case,
                                         "--out", out]), 2)
        self.assertTrue(os.path.isdir(os.path.join(out, family, case)))

    @unittest.skipUnless(os.path.isfile(SEVEN), "no seven-stations.sh in this core")
    def test_seven_stations_refuses_a_protected_home(self):
        for harness in HARNESSES:
            for target in self.protected:
                self.assert_refused(["sh", SEVEN, harness, target], label=(harness, target))

    @unittest.skipUnless(os.path.isfile(REPLAY), "no replay in this core")
    def test_the_replay_refuses_a_protected_keep(self):
        for target in self.protected:
            self.assert_refused([sys.executable, REPLAY, "--keep", target], label=target)


if __name__ == "__main__":
    unittest.main()
