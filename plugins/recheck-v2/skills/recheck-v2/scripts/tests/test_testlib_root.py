"""testlib finds its root (E8-A48): the worktree root from `git rev-parse --show-toplevel` run in the scripts directory
when that succeeds, else the plugin root (the directory holding `.claude-plugin/`); `other_cwd` accepts any scratch
directory outside that root. The reviewer's layout is rebuilt here: `<dir>/copy/recheck-v2/` with no git repository
above it and the scratch at `<dir>/scratch/`; a subprocess imports the copy's testlib and prints its root, then
test_cli.py and test_skill_body.py run from the copy and pass."""
import json
import os
import shutil
import subprocess
import sys
import unittest

import testlib

# the wall: evals/answer-key and evals/trigger-set/held-out are never read; neither suite needs them
IGNORE = shutil.ignore_patterns("__pycache__", "answer-key", "held-out")


def git_above(path):
    """The first directory at or above `path` holding a .git entry, or None."""
    d = os.path.realpath(path)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def git_toplevel(cwd):
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return None
    return proc.stdout.decode("utf-8", "replace").strip() if proc.returncode == 0 else None


class RootDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e8-fix5-root-")
        cls.copy = os.path.join(cls.dir, "copy", "recheck-v2")
        cls.scratch = os.path.join(cls.dir, "scratch")
        os.makedirs(cls.scratch)
        shutil.copytree(testlib.PLUGIN, cls.copy, ignore=IGNORE)
        cls.tests = os.path.join(cls.copy, "skills", "recheck-v2", "scripts", "tests")

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def no_git_layout(self):
        above = git_above(self.copy)
        if above:
            self.skipTest("the scratch base %s sits inside the git repository %s; the no-git layout cannot be built here" % (testlib.scratch_base(), above))

    def test_here_the_root_is_git_toplevel_or_the_plugin_root(self):
        self.assertTrue(os.path.isdir(os.path.join(testlib.PLUGIN, ".claude-plugin")), testlib.PLUGIN)
        top = git_toplevel(testlib.SCRIPTS)
        self.assertEqual(os.path.realpath(testlib.REPO), os.path.realpath(top or testlib.PLUGIN))
        real_plugin, real_repo = os.path.realpath(testlib.PLUGIN), os.path.realpath(testlib.REPO)
        self.assertTrue(real_plugin == real_repo or real_plugin.startswith(real_repo + os.sep), "the plugin root sits under the root")
        with self.assertRaises(AssertionError):
            testlib.other_cwd(testlib.SCRIPTS, "never")
        self.assertFalse(os.path.exists(os.path.join(testlib.SCRIPTS, "never")))

    def test_copy_without_git_reports_its_plugin_root_and_accepts_a_sibling(self):
        self.no_git_layout()
        code = ("import json, os, sys; sys.path.insert(0, %r); import testlib; "
                "print(json.dumps({'repo': testlib.REPO, 'plugin': testlib.PLUGIN, 'other': testlib.other_cwd(%r)}))" % (self.tests, self.scratch))
        proc = subprocess.run([sys.executable, "-c", code], cwd=self.tests, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        got = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(os.path.realpath(got["plugin"]), os.path.realpath(self.copy))
        self.assertEqual(os.path.realpath(got["repo"]), os.path.realpath(self.copy), "no git repository around the copy: the root is the plugin root")
        self.assertEqual(os.path.realpath(got["other"]), os.path.realpath(os.path.join(self.scratch, "elsewhere")))
        self.assertTrue(os.path.isdir(got["other"]))

    def test_cli_and_skill_body_suites_pass_from_the_copy(self):
        self.no_git_layout()
        env = dict(os.environ, RECHECK_TEST_SCRATCH=self.scratch)
        proc = subprocess.run([sys.executable, "-m", "unittest", "test_cli", "test_skill_body"], cwd=self.tests, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        err = proc.stderr.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 0, err[-4000:])
        self.assertRegex(err, r"Ran \d+ tests")
        self.assertIn("\nOK", err)
        self.assertNotIn("skipped", err.splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
