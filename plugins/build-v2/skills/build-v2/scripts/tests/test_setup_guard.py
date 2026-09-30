"""The setup home guard in build-v2 and signoff-v2 (E14 punch list, items 1 and 2; the four station cores'
`test_setup_guard.py` is the model, its methods aimed at this core's scripts): every script of this core that
creates or writes under a path its caller or the environment names refuses, exit 2 and nothing created, a path
under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, as given, through a symlink or a `..`, and a TMPDIR under
one of them; an ordinary path passes the guard. The scripts: both installers; both launchers (the out-dir, the
installed or condition home, each --writable root); negative-cases.py behind both negative-tests.sh; the seeded
cases' observe.py and a family's build.py (caselib); and, where the core has it, three-stations.sh. The launchers
are byte-equal to the four front cores' (precon-v2's copy is compared, in the checkout shape), and the guard
blocks of the installers, negative-cases.py and three-stations.sh are the front cores' byte for byte.
A fake HOME and inert `claude`, `codex` and `uv` stand-ins first on PATH; never the real homes or commands.
Byte-identical in build-v2 and signoff-v2."""
import hashlib
import os
import subprocess
import sys
import unittest

import testlib

CORE = os.path.basename(testlib.SKILL)                  # build-v2, signoff-v2
PREFIX = CORE.upper().replace("-", "_")                 # BUILD_V2, SIGNOFF_V2
STANDIN = "#!/bin/sh\ncase \"$*\" in *'plugin install'*) echo '{\"outcome\":\"ok\"}';; esac\nexit 0\n"
CONFIG = 'model = "m"\nmodel_reasoning_effort = "high"\nsandbox_mode = "workspace-write"\n'
SETUPS = os.path.join(testlib.PLUGIN, "setups")
SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
THREE = os.path.join(SETUPS, "three-stations.sh")
SEVEN = ("inspect-v2", "setups", "seven-stations.sh")
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
CANONICAL = "precon-v2"
GUARD_START = "# The home guard, before anything is created (E14 slice 3c fix 3)"
GUARD_END = 'SETUP_HOME=$(CDPATH= cd -- "$SETUP_HOME" && pwd -P)\n'


def write_text(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def read_text(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def listing(root):
    return sorted(os.path.relpath(os.path.join(d, n), root) for d, ds, fs in os.walk(root) for n in ds + fs)


def sibling(name):
    """`plugins/<name>` beside this core in a checkout, or None in the installed shape."""
    path = os.path.join(os.path.dirname(testlib.PLUGIN), name)
    return path if os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json")) else None


def between(text, start, end):
    """The block from the line that opens with `start` through `end`, or None."""
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i)
    return None if j < 0 else text[i:j + len(end)]


@unittest.skipUnless(os.path.isdir(SETUPS), "no setups folder beside this copy")
class TheHomeGuard(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("setup-guard-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.home = h = os.path.join(self.tmp, "home")
        for rel in (".codex", os.path.join(".claude", "config"), os.path.join(".local", "share", "skills-v2-locked"),
                    "ordinary", os.path.join("iso-claude", "config"), "iso-codex", "ws"):
            os.makedirs(os.path.join(h, rel))
        write_text(os.path.join(h, ".codex", "config.toml"), CONFIG)
        write_text(os.path.join(h, "iso-codex", "config.toml"), CONFIG)
        write_text(os.path.join(h, "prompt.txt"), "a prompt this test wrote\n")
        os.symlink(os.path.join(h, ".codex"), os.path.join(h, "link"))
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        for name, body in (("claude", STANDIN), ("codex", STANDIN), ("uv", "#!/bin/sh\nexit 1\n")):
            write_text(os.path.join(bin_dir, name), body)
            os.chmod(os.path.join(bin_dir, name), 0o755)
        self.env = {"PATH": bin_dir + os.pathsep + os.environ.get("PATH", ""), "HOME": h,
                    "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
        if "TMPDIR" in os.environ:
            self.env["TMPDIR"] = os.environ["TMPDIR"]
        # the last two pin the E14 punch-list check's O-7: a case-changed spelling, and a skills-v2-* home beyond
        # the pilot and locked ones
        self.protected = (h + "/.claude/x", h + "/.codex/x", h + "/.local/share/skills-v2-pilot/x",
                          h + "/.local/share/skills-v2-locked/x", h + "/link/x", h + "/ordinary/../.claude/x",
                          h + "/.CLAUDE/x", h + "/.local/share/skills-v2-other/deep/x")

    def run_it(self, argv, extra=None):
        env = dict(self.env)
        env.update(extra or {})
        return subprocess.run(argv, env=env, cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=600).returncode

    def assert_refused(self, argv, extra=None, label=None):
        before = listing(self.tmp)
        self.assertEqual(self.run_it(argv, extra), 2, label or argv)
        self.assertEqual(listing(self.tmp), before, label or argv)

    def install(self, harness, target, extra=None):
        return ["sh", os.path.join(SETUPS, harness, "install.sh"), "--home", target], extra

    def launch(self, harness, out, home=None, writable=None):
        name = "CLAUDE_HOME" if harness == "claude-code" else "CODEX_HOME"
        home = home or os.path.join(self.home, "iso-claude" if harness == "claude-code" else "iso-codex")
        argv = ["sh", os.path.join(SETUPS, harness, "launch.sh"), os.path.join(self.home, "prompt.txt"),
                os.path.join(self.home, "ws"), out] + (["--writable", writable] if writable else [])
        return argv, {"%s_%s" % (PREFIX, name): home}

    def seeded(self):
        got = subprocess.run([sys.executable, os.path.join(SEEDED, "observe.py"), "--list"], env=self.env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        case = got.stdout.decode("utf-8").split()[0]
        family = [f for f in testlib.FAMILIES if case.startswith(f.split("-")[0] + "-")][0]
        return family, case

    def test_every_protected_home_is_refused_before_anything_is_created(self):
        for harness in HARNESSES:
            for target in self.protected:
                self.assert_refused(*self.install(harness, target), label=(harness, target))

    def test_an_ordinary_home_passes_the_guard(self):
        for harness in HARNESSES:
            target = os.path.join(self.home, "ordinary", harness)
            self.assertEqual(self.run_it(*self.install(harness, target)), 0, harness)
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

    @unittest.skipUnless(os.path.isfile(THREE), "no three-stations.sh in this core")
    def test_three_stations_refuses_a_protected_home(self):
        for harness in HARNESSES:
            for target in self.protected:
                self.assert_refused(["sh", THREE, harness, target], label=(harness, target))

    def test_a_tmpdir_under_a_protected_home_is_refused(self):
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        extra = {"TMPDIR": tmp}
        for harness in HARNESSES:
            argv, _ = self.install(harness, os.path.join(self.home, "ordinary", "t-" + harness))
            self.assert_refused(argv, extra, ("install.sh", harness))
            argv, env = self.launch(harness, os.path.join(self.home, "ordinary", "run-" + harness))
            env.update(extra)
            self.assert_refused(argv, env, ("launch.sh", harness))
            if os.path.isfile(THREE):
                self.assert_refused(["sh", THREE, harness, os.path.join(self.home, "ordinary", "st-" + harness)],
                                    extra, ("three-stations.sh", harness))
        if os.path.isfile(os.path.join(SEEDED, "observe.py")):
            family, case = self.seeded()
            self.assert_refused([sys.executable, os.path.join(SEEDED, "observe.py"), "--case", case, "--out",
                                 os.path.join(self.home, "ordinary", "obs")], extra, "observe.py")

    @unittest.skipUnless(os.path.isfile(os.path.join(SEEDED, "observe.py")), "no seeded cases beside this copy")
    def test_a_protected_temp_folder_is_refused_without_a_write_in_it(self):
        # the E14 punch-list check's CPL-1: observe.py reads TMPDIR, TEMP and TMP from the environment, never
        # through tempfile.gettempdir(), which proves a folder writable by creating and removing a file in it;
        # the spy sees no call under the protected folder, and the refusal is unchanged
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        family, case = self.seeded()
        argv = [os.path.join(SEEDED, "observe.py"), "--case", case, "--out", os.path.join(self.home, "ordinary", "obs")]
        for name in ("TMPDIR", "TEMP"):
            env = dict((k, v) for k, v in self.env.items() if k not in ("TMPDIR", "TEMP", "TMP"))
            env[name] = tmp
            before = listing(self.tmp)
            got = subprocess.run([sys.executable, "-c", SPY, tmp] + argv, env=env, cwd=self.tmp,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
            err = got.stderr.decode("utf-8", "replace")
            self.assertEqual(got.returncode, 2, (name, err))
            self.assertEqual([line for line in err.splitlines() if line.startswith("SPY ")], [], name)
            self.assertIn("which no setup may touch; nothing created", err, name)
            self.assertEqual(listing(self.tmp), before, name)


class TheSixCoresHoldOneGuard(unittest.TestCase):
    """The launchers are byte-equal to the four front cores' (six copies per harness: the front cores hold their
    four equal through test_shared_equal.py, this compares this core's with precon-v2's), and the guard blocks of
    the installers, negative-cases.py and three-stations.sh are the front cores' byte for byte (only the plugin
    lists and the headers differ)."""

    def setUp(self):
        self.canonical = sibling(CANONICAL)
        if self.canonical is None:
            self.skipTest("no %s beside this core (the installed shape): the copies cannot be compared here, and "
                          "this is reported as skipped, not passed" % CANONICAL)

    def test_the_launchers_are_the_front_cores_copy(self):
        for harness in HARNESSES:
            rel = os.path.join("setups", harness, "launch.sh")
            self.assertEqual(digest(os.path.join(testlib.PLUGIN, rel)), digest(os.path.join(self.canonical, rel)),
                             rel)

    def test_the_installers_guard_block_is_the_front_cores(self):
        for harness in HARNESSES:
            rel = os.path.join("setups", harness, "install.sh")
            mine = between(read_text(os.path.join(testlib.PLUGIN, rel)), GUARD_START, GUARD_END)
            theirs = between(read_text(os.path.join(self.canonical, rel)), GUARD_START, GUARD_END)
            self.assertIsNotNone(mine, rel)
            self.assertEqual(mine, theirs, rel)

    def test_negative_cases_carries_the_front_cores_guard(self):
        rel = os.path.join("setups", "negative-cases.py")
        start, end = '    home = os.environ.get("HOME", "")\n', "    if os.path.exists(out):\n"
        mine = between(read_text(os.path.join(testlib.PLUGIN, rel)), start, end)
        self.assertIsNotNone(mine)
        self.assertEqual(mine, between(read_text(os.path.join(self.canonical, rel)), start, end))

    @unittest.skipUnless(os.path.isfile(THREE), "no three-stations.sh in this core")
    def test_three_stations_carries_the_seven_stations_guard(self):
        seven = os.path.join(os.path.dirname(testlib.PLUGIN), *SEVEN)
        if not os.path.isfile(seven):
            self.skipTest("no inspect-v2 seven-stations.sh beside this core")
        mine = between(read_text(THREE), GUARD_START, GUARD_END)
        self.assertIsNotNone(mine)
        theirs = between(read_text(seven), GUARD_START, GUARD_END)
        self.assertEqual(mine, theirs.replace('"seven-stations.sh" <<', '"three-stations.sh" <<'))


if __name__ == "__main__":
    unittest.main()
