"""The documented commands against the shipped CLI (the guide's Scripts section: "exercise the skill's documented
commands against the shipped CLI"; contract section 15).

Every `uv run scripts/ship.py <command> ...` line of `SKILL.md` names a command the driver has, with flags its
`--help` lists, and the procedure names every phase of the contract in its order. Written after the core, not red
first (the slice 2 report says so): it guards the body against drift, it names no behavior of section 10.
"""
import os
import re
import subprocess
import sys
import unittest

import testlib

LINE = re.compile(r"uv run scripts/ship\.py (\S+)((?: [^\n#]*)?)")


def body():
    with open(os.path.join(testlib.SKILL, "SKILL.md"), encoding="utf-8") as fh:
        return fh.read()


def help_of(command):
    proc = subprocess.run([sys.executable, testlib.DRIVER, command, "--help"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=testlib.base_env())
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


class TheDocumentedCommands(unittest.TestCase):

    def test_every_documented_command_and_flag_is_the_clis(self):
        found = LINE.findall(body())
        self.assertTrue(found)
        for command, rest in found:
            if command.startswith("<"):
                continue
            code, text = help_of(command)
            self.assertEqual(code, 0, command)
            for flag in re.findall(r"(--[a-z-]+)", rest):
                self.assertIn(flag, text, (command, flag))

    def test_the_procedure_names_every_phase_in_order(self):
        text = body()
        at = [text.index("ship.py %s" % name) for name in ("check-input", "select", "hook", "visit", "fix", "lap",
                                                            "pause", "report")]
        self.assertEqual(at[:3], sorted(at[:3]))
        for name in ("visit --run-dir <run dir> --station build-v2", "--station signoff-v2", "--station recheck-v2"):
            self.assertIn(name, text)

    def test_help_works_without_jsonschema(self):
        tmp = testlib.make_scratch("ship-help-")
        self.addCleanup(testlib.rmtree, tmp)
        stub = testlib.stub_without_jsonschema(tmp)
        for command in ("select", "hook", "visit", "fix", "lap", "pause", "report"):
            proc = subprocess.run([sys.executable, testlib.DRIVER, command, "--help"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=testlib.base_env({"PYTHONPATH": stub}))
            self.assertEqual(proc.returncode, 0, (command, proc.stderr.decode()))


if __name__ == "__main__":
    unittest.main()
