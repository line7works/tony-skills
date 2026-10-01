"""The setup home guard (E14 slice 3c review F1+F2; check 5's C3C5-1, C3C5-2 and C3C5-6): every script of
this core that creates or writes under a path its caller names refuses, exit 2 and nothing created, a path
under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, as given, through a symlink or a `..`; an ordinary
path passes the guard. The scripts: both installers; both launchers (the out-dir, the installed or condition
home, each --writable root); negative-cases.py behind both negative-tests.sh; the seeded cases' observe.py
and a family's build.py (caselib); and, where the core has them, seven-stations.sh and the replay's --keep.
A fake HOME and inert `claude`, `codex` and `uv` stand-ins first on PATH; never the real homes or commands."""
import os
import shlex
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
# an audit-hook spy (the E14 punch-list check's CPL-1): runs a Python script and reports, after it ends, every
# open or os./shutil. call whose path is under the folder it watches, one "SPY" line each on stderr
SPY = r"""
import os, runpy, sys
watch, script = sys.argv[1], sys.argv[2]
forms = set(f.casefold().rstrip(os.sep) for f in (os.path.abspath(watch), os.path.realpath(watch)))
seen, busy = [], [False]
def hook(event, args):
    if busy[0] or not args or not (event == "open" or event.startswith(("os.", "shutil."))):
        return
    busy[0] = True
    try:
        p = args[0]
        if isinstance(p, (str, bytes, os.PathLike)):
            p = os.fsdecode(os.fspath(p))
            a = os.path.abspath(p).casefold()
            if any(a == f or a.startswith(f + os.sep) for f in forms):
                seen.append("%s %s" % (event, p))
    finally:
        busy[0] = False
sys.addaudithook(hook)
sys.argv = [script] + sys.argv[3:]
try:
    runpy.run_path(script, run_name="__main__")
finally:
    for line in seen:
        sys.stderr.write("SPY " + line + "\n")
"""

# an audit-hook spy for launches (the E14 punch-list review's F1): runs a Python script and reports, after it ends,
# every subprocess or exec it started, one "LAUNCH" line each on stderr
LAUNCH_SPY = r"""
import runpy, sys
script = sys.argv[1]
seen = []
def hook(event, args):
    if event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork"):
        seen.append(("%s %r" % (event, args))[:300])
sys.addaudithook(hook)
sys.argv = [script] + sys.argv[2:]
try:
    runpy.run_path(script, run_name="__main__")
finally:
    for line in seen:
        sys.stderr.write("LAUNCH " + line + "\n")
"""
# a python3 stand-in (the E14 punch-list review's F1): the native python3 writes into the temp folder as it starts
# (`xcrun_db`) before any line of a script runs; this stand-in makes that start-up write into each of TMPDIR, TEMP
# and TMP it is started with, then runs the real interpreter
STARTUP = "#!/bin/sh\nfor t in \"${TMPDIR-}\" \"${TEMP-}\" \"${TMP-}\"; do\n  if [ -n \"$t\" ] && [ -d \"$t\" ]; then " \
          "mkdir -p \"$t/startup-write\"; fi\ndone\nexec %s \"$@\"\n"


def listing(root):
    """Every path under `root`, and `root` itself, with its modification time in ns: a folder made and removed
    again still shows, in its parent's time (the E14 punch-list re-check's O-7)."""
    return [(".", os.lstat(root).st_mtime_ns)] + sorted(
        (os.path.relpath(os.path.join(d, n), root), os.lstat(os.path.join(d, n)).st_mtime_ns)
        for d, ds, fs in os.walk(root) for n in ds + fs)


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

    def test_a_tmpdir_under_a_protected_home_is_refused(self):
        # check 6's C3C6-1 (E14 punch list, item 2): a script that makes its scratch folder under TMPDIR, or
        # carries the GUARD, refuses a TMPDIR under a protected home, exit 2 and nothing created
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        extra = {"TMPDIR": tmp}
        for harness in HARNESSES:
            self.assert_refused(["sh", os.path.join(SETUPS, harness, "install.sh"), "--home",
                                 os.path.join(self.home, "ordinary", "t-" + harness)], extra, ("install.sh", harness))
            argv, env = self.launch(harness, os.path.join(self.home, "ordinary", "run-" + harness))
            env.update(extra)
            self.assert_refused(argv, env, ("launch.sh", harness))
            if os.path.isfile(SEVEN):
                self.assert_refused(["sh", SEVEN, harness, os.path.join(self.home, "ordinary", "st-" + harness)],
                                    extra, ("seven-stations.sh", harness))
        if os.path.isfile(os.path.join(SEEDED, "observe.py")):
            family, case = self.seeded()
            self.assert_refused([sys.executable, os.path.join(SEEDED, "observe.py"), "--case", case, "--out",
                                 os.path.join(self.home, "ordinary", "obs")], extra, "observe.py")
        if os.path.isfile(REPLAY):
            self.assert_refused([sys.executable, REPLAY], extra, "replay.py")

    @unittest.skipUnless(os.path.isfile(os.path.join(SEEDED, "observe.py")) or os.path.isfile(REPLAY),
                         "no Python writer that reads the temp folder beside this copy")
    def test_a_protected_temp_folder_is_refused_without_a_write_in_it(self):
        # the E14 punch-list check's CPL-1: the Python writers read TMPDIR, TEMP and TMP from the environment,
        # never through tempfile.gettempdir(), which proves a folder writable by creating and removing a file in
        # it; the spy sees no call under the protected folder, and the refusal is unchanged
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        runs = []
        if os.path.isfile(os.path.join(SEEDED, "observe.py")):
            family, case = self.seeded()
            runs.append([os.path.join(SEEDED, "observe.py"), "--case", case, "--out",
                         os.path.join(self.home, "ordinary", "obs")])
        if os.path.isfile(REPLAY):
            runs.append([REPLAY])
        for name in ("TMPDIR", "TEMP"):
            env = dict((k, v) for k, v in self.env.items() if k not in ("TMPDIR", "TEMP", "TMP"))
            env[name] = tmp
            for argv in runs:
                label = (os.path.basename(argv[0]), name)
                before = listing(self.tmp)
                got = subprocess.run([sys.executable, "-c", SPY, tmp] + argv, env=env, cwd=self.tmp,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
                err = got.stderr.decode("utf-8", "replace")
                self.assertEqual(got.returncode, 2, (label, err))
                self.assertEqual([line for line in err.splitlines() if line.startswith("SPY ")], [], label)
                self.assertIn("which no setup may touch; nothing created", err, label)
                self.assertEqual(listing(self.tmp), before, label)

    def guarded_shell_scripts(self):
        """(label, argv, env) for every shell script of this core that carries the GUARD: both installers, both
        launchers and, where the core has it, seven-stations.sh, each aimed at an ordinary path."""
        o = os.path.join(self.home, "ordinary")
        rows = []
        for harness in HARNESSES:
            rows.append((("install.sh", harness), ["sh", os.path.join(SETUPS, harness, "install.sh"), "--home",
                                                   os.path.join(o, "t-" + harness)], {}))
            argv, extra = self.launch(harness, os.path.join(o, "run-" + harness))
            rows.append((("launch.sh", harness), argv, extra))
            if os.path.isfile(SEVEN):
                rows.append((("seven-stations.sh", harness), ["sh", SEVEN, harness, os.path.join(o, "st-" + harness)],
                             {}))
        return rows

    def python_writers(self):
        """(label, argv) for the Python scripts of this core that read the temp folder: observe.py and, where the
        core has it, the replay."""
        rows = []
        if os.path.isfile(os.path.join(SEEDED, "observe.py")):
            family, case = self.seeded()
            rows.append(("observe.py", [os.path.join(SEEDED, "observe.py"), "--case", case, "--out",
                                        os.path.join(self.home, "ordinary", "obs")]))
        if os.path.isfile(REPLAY):
            rows.append(("replay.py", [REPLAY]))
        return rows

    def under_temp(self, name, tmp, extra=None):
        """This test's environment with TMPDIR, TEMP and TMP removed and `name` alone set to `tmp`."""
        env = dict((k, v) for k, v in self.env.items() if k not in ("TMPDIR", "TEMP", "TMP"))
        env.update(extra or {})
        env[name] = tmp
        return env

    def refused_under(self, env, argv, label):
        before = listing(self.tmp)
        got = subprocess.run(argv, env=env, cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=600)
        err = got.stderr.decode("utf-8", "replace")
        self.assertEqual(got.returncode, 2, (label, err[-800:]))
        self.assertEqual(listing(self.tmp), before, label)
        return err

    def test_a_temp_or_tmp_under_a_protected_home_is_refused(self):
        # the E14 punch-list review's F1: TEMP and TMP are held to TMPDIR's rule by every script that carries the
        # GUARD, as by the Python writers; each alone (TMPDIR unset) under a protected home is refused, exit 2 and
        # nothing created
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        python = [(label, [sys.executable] + argv, {}) for label, argv in self.python_writers()]
        for name in ("TEMP", "TMP"):
            for label, argv, extra in self.guarded_shell_scripts() + python:
                self.refused_under(self.under_temp(name, tmp, extra), argv, (label, name))

    def test_nothing_starts_under_a_protected_temp_folder_before_the_guard(self):
        # the E14 punch-list review's F1: the shell GUARD's interpreter starts with TMPDIR, TEMP and TMP cleared
        # (their values reach it as arguments), so an interpreter's own start-up write into the temp folder cannot
        # land under a protected home; and observe.py starts no subprocess (its case catalog) before its guard
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        startup = os.path.join(self.tmp, "startup-bin")
        os.makedirs(startup)
        with open(os.path.join(startup, "python3"), "w", encoding="utf-8") as fh:
            fh.write(STARTUP % shlex.quote(sys.executable))
        os.chmod(os.path.join(startup, "python3"), 0o755)
        path = {"PATH": startup + os.pathsep + self.env["PATH"]}
        for name in ("TMPDIR", "TEMP", "TMP"):
            for label, argv, extra in self.guarded_shell_scripts():
                extra = dict(extra, **path)
                self.refused_under(self.under_temp(name, tmp, extra), argv, (label, name))
                self.assertFalse(os.path.exists(os.path.join(tmp, "startup-write")), (label, name))
            for label, argv in self.python_writers():
                err = self.refused_under(self.under_temp(name, tmp), [sys.executable, "-c", LAUNCH_SPY] + argv,
                                         (label, name))
                self.assertEqual([line for line in err.splitlines() if line.startswith("LAUNCH ")], [],
                                 (label, name))
                self.assertIn("which no setup may touch; nothing created", err, (label, name))

    def test_the_claude_code_launcher_refuses_a_missing_protected_home(self):
        # the E14 punch-list review's F2: the GUARD runs before the existence check, so an installed home under a
        # protected home that does not exist is refused, exit 2; an ordinary one that does not exist is still 3
        h = self.home
        out = os.path.join(h, "ordinary", "run")
        for home in (h + "/.claude/missing", h + "/.codex/missing", h + "/.local/share/skills-v2-pilot/missing",
                     h + "/link/missing", h + "/ordinary/../.claude/missing"):
            argv, extra = self.launch("claude-code", out, home=home)
            self.assert_refused(argv, extra, home)
        argv, extra = self.launch("claude-code", out, home=h + "/ordinary/missing")
        before = listing(self.tmp)
        self.assertEqual(self.run_it(argv, extra), 3)
        self.assertEqual(listing(self.tmp), before)

    def test_the_codex_launcher_refuses_a_missing_protected_condition_home_or_writable_root(self):
        # the E14 punch-list review's F2: the GUARD runs before the existence checks, so a condition home or a
        # --writable root under a protected home that does not exist is refused, exit 2; an ordinary one that does
        # not exist is still 3
        h = self.home
        out = os.path.join(h, "ordinary", "run")
        missing = (h + "/.codex/missing", h + "/.claude/missing", h + "/.local/share/skills-v2-locked/missing",
                   h + "/link/missing", h + "/ordinary/../.codex/missing")
        for home in missing:
            argv, extra = self.launch("codex", out, home=home)
            self.assert_refused(argv, extra, ("condition", home))
        for writable in missing:
            argv, extra = self.launch("codex", out, writable=writable)
            self.assert_refused(argv, extra, ("writable", writable))
        for home, writable in ((h + "/ordinary/missing", None), (None, h + "/ordinary/missing")):
            argv, extra = self.launch("codex", out, home=home, writable=writable)
            before = listing(self.tmp)
            self.assertEqual(self.run_it(argv, extra), 3, (home, writable))
            self.assertEqual(listing(self.tmp), before, (home, writable))

    def test_a_temp_variable_spelled_through_a_symlink_is_refused(self):
        # the E14 punch-list re-check's O-6: TMPDIR, TEMP and TMP, each alone, spelled through a symlink into a
        # protected home (`link` is the fake ~/.codex) are refused by every script that carries the GUARD and by
        # the Python writers, exit 2 and nothing created
        os.makedirs(os.path.join(self.home, ".codex", "tmp"))
        tmp = os.path.join(self.home, "link", "tmp")
        python = [(label, [sys.executable] + argv, {}) for label, argv in self.python_writers()]
        for name in ("TMPDIR", "TEMP", "TMP"):
            for label, argv, extra in self.guarded_shell_scripts() + python:
                self.refused_under(self.under_temp(name, tmp, extra), argv, (label, name))

    def other_names(self):
        """This test's home under the other names macOS gives its folder, which neither abspath nor realpath
        rewrites: the firmlink into the Data volume and the /.nofollow prefix (the E14 punch-list re-check's
        CPL3-1). A name that does not reach the same folder here skips the test, reported as skipped."""
        real = os.path.realpath(self.home)
        names = []
        for prefix in ("/System/Volumes/Data", "/.nofollow"):
            try:
                same = os.path.samestat(os.stat(prefix + real), os.stat(real))
            except OSError:
                same = False
            if not same:
                self.skipTest("%s<home> does not name this test's home here" % prefix)
            names.append(prefix + real)
        return names

    @unittest.skipUnless(os.path.isdir("/System/Volumes/Data"), "no /System/Volumes/Data on this system")
    def test_a_protected_home_under_another_name_of_its_folder_is_refused(self):
        # the E14 punch-list re-check's CPL3-1: every protected row spelled through the firmlink and through
        # /.nofollow is refused as the target of every script that takes one, as a launcher's home or --writable
        # root, and as each of TMPDIR, TEMP and TMP, exit 2 and nothing created (listing with modification times):
        # the guard holds the nearest existing folder to the protected home by device and inode, beside the names
        h = self.home
        names = self.other_names()
        family, case = self.seeded()
        os.makedirs(os.path.join(h, ".claude", "tmp"))
        python = [(label, [sys.executable] + argv, {}) for label, argv in self.python_writers()]
        out = os.path.join(h, "ordinary", "run")
        for other in names:
            for row in self.protected:
                target = other + row[len(h):]
                rows = []
                for harness in HARNESSES:
                    rows.append((("install.sh", harness),
                                 ["sh", os.path.join(SETUPS, harness, "install.sh"), "--home", target], {}))
                    argv, extra = self.launch(harness, target)
                    rows.append((("launch.sh", harness), argv, extra))
                    rows.append((("negative-tests.sh", harness),
                                 ["sh", os.path.join(SETUPS, harness, "negative-tests.sh"), target, "--case",
                                  "missing-resource"], {}))
                    if os.path.isfile(SEVEN):
                        rows.append((("seven-stations.sh", harness), ["sh", SEVEN, harness, target], {}))
                rows.append(("observe.py", [sys.executable, os.path.join(SEEDED, "observe.py"), "--case", case,
                                            "--out", target], {}))
                rows.append(("build.py", [sys.executable, os.path.join(SEEDED, family, "build.py"), "--case", case,
                                          "--out", target], {}))
                if os.path.isfile(REPLAY):
                    rows.append(("replay.py", [sys.executable, REPLAY, "--keep", target], {}))
                for label, argv, extra in rows:
                    self.assert_refused(argv, extra, (label, target))
            for argv, extra in (self.launch("claude-code", out, home=other + "/.claude"),
                                self.launch("codex", out, home=other + "/.codex"),
                                self.launch("codex", out, writable=other + "/.codex"),
                                self.launch("codex", out, writable=other + "/.local/share/skills-v2-locked")):
                self.assert_refused(argv, extra, (argv[1:], extra))
            tmp = other + "/.claude/tmp"
            for name in ("TMPDIR", "TEMP", "TMP"):
                for label, argv, extra in self.guarded_shell_scripts() + python:
                    self.refused_under(self.under_temp(name, tmp, extra), argv, (label, name, tmp))


if __name__ == "__main__":
    unittest.main()
