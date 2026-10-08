"""The E15 lane contract A27 (2): `skill-identity` reports `interface_version` 1 and answers without importing
jsonschema.

ship-v2 reads each station's identity through the station's own CLI before a visit, run isolated
(`python3 -I -B recheck.py skill-identity`), and refuses a station whose identity carries no interface version it
knows (E15-7). These tests hold the command to that: under `/usr/bin/python3 -I` (no user site, so no jsonschema) and
under the suite's own interpreter (`uv run`, where jsonschema is importable), the command exits 0 and prints
`{name, version, commit, content_sha256, interface_version}`; the first four are the run block's `skill` fields, as
before; the process never imports jsonschema; and every other command still needs it (exit 3 without it).
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import result as rmod  # noqa: E402

SYSTEM_PYTHON = "/usr/bin/python3"
SCRIPT = os.path.join(testlib.SCRIPTS, "recheck.py")
# runs recheck.py as `__main__` with the given argv and reports, at exit, whether jsonschema was ever imported
PROBE = ("import atexit, runpy, sys\n"
         "atexit.register(lambda: sys.stderr.write('JSONSCHEMA_IMPORTED=%s\\n' % ('jsonschema' in sys.modules)))\n"
         "sys.argv = [sys.argv[1]] + sys.argv[2:]\n"
         "runpy.run_path(sys.argv[0], run_name='__main__')\n")


def run(python, args, isolated=False, env=None, cwd=None):
    cmd = [python] + (["-I"] if isolated else []) + ["-B", "-c", PROBE, SCRIPT] + list(args)
    proc = subprocess.run(cmd, cwd=cwd or testlib.SCRIPTS, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


class TheIdentityReportsItsInterface(unittest.TestCase):

    def setUp(self):
        self.dir = testlib.make_scratch("a27-identity-")
        self.addCleanup(testlib.rmtree, self.dir)

    def check(self, code, out, err):
        self.assertEqual(code, 0, err)
        got = json.loads(out)
        self.assertEqual(sorted(got), ["commit", "content_sha256", "interface_version", "name", "version"])
        self.assertIs(type(got["interface_version"]), int)
        self.assertEqual(got["interface_version"], 1)
        expected = rmod.skill_identity(testlib.SKILL)
        self.assertEqual(dict((k, got[k]) for k in expected), expected, "the other fields are the run block's own")
        self.assertIn("JSONSCHEMA_IMPORTED=False", err, "skill-identity answers without importing jsonschema")
        return got

    def test_under_the_system_python_isolated(self):
        if not os.path.exists(SYSTEM_PYTHON):
            self.skipTest("no %s on this machine" % SYSTEM_PYTHON)
        self.check(*run(SYSTEM_PYTHON, ["skill-identity"], isolated=True))

    def test_under_this_runtime(self):
        """Under `uv run` the suite's interpreter imports jsonschema for every other command; this one never does."""
        self.check(*run(sys.executable, ["skill-identity"]))
        self.check(*run(sys.executable, ["skill-identity"], isolated=True))

    def test_with_jsonschema_refusing_to_import(self):
        stub = testlib.stub_without_jsonschema(self.dir)
        self.check(*run(sys.executable, ["skill-identity"], env=dict(os.environ, PYTHONPATH=stub)))
        env = dict(os.environ, RECHECK_TEST="1", RECHECK_TEST_NO_JSONSCHEMA="1")
        self.check(*run(sys.executable, ["skill-identity"], env=env))

    def test_with_a_skill_root(self):
        code, out, err = run(sys.executable, ["--skill-root", testlib.SKILL, "skill-identity"])
        self.check(code, out, err)

    def test_every_other_command_still_needs_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.dir)
        env = dict(os.environ, PYTHONPATH=stub)
        for args in (["identity", self.dir], ["check-input", os.path.join(self.dir, "absent.json")]):
            code, out, err = run(sys.executable, args, env=env)
            self.assertEqual((code, out), (3, ""), (args, err))
            self.assertIn(testlib.MISSING_DEPENDENCY, err)

    def test_help_still_lists_the_command_and_its_fields(self):
        code, out, err = testlib.run_script("recheck.py", ["--help"], cwd=self.dir)
        self.assertEqual(code, 0, err)
        self.assertIn("skill-identity", out)
        code, out, err = testlib.run_script("recheck.py", ["skill-identity", "--help"], cwd=self.dir)
        self.assertEqual(code, 0, err)
        self.assertIn("interface_version", out)


if __name__ == "__main__":
    unittest.main()
