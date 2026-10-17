"""The command line itself (the contract's E16-15, the A7a helper interface), started as the real `sun.py`.

`--help` with arguments, defaults, an example and side effects; JSON on standard output and nothing
else; exits 0, 2, 3, 4, 10 and 1 with their A7a meanings; `skill-identity`; and that nothing in the
session's environment makes the shipped tool load code (the control room's line, 2026-10-13).
"""
import json
import os
import unittest

import fab
import harness
import rowlib
from sun_core import cli, exits, schemas, texts


class CommandLine(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.m = self.machine()

    def test_E16_15_help_names_arguments_defaults_an_example_and_side_effects(self):
        for argv in (["--help"], ["look", "--help"]):
            result = self.m.run_child(*argv)
            self.assertEqual(result.code, 0, result.text)
            for word in ("--kind", "--name", "--inputs", "Defaults:", "Example:", "Side effects:", "Exit:", "skill-identity"):
                self.assertIn(word, result.out)
            self.assertEqual(result.err, "")

    def test_E16_15_exit_2_on_a_missing_or_malformed_argument_with_nothing_on_standard_output(self):
        for argv in (["look", "--kind", "sunrise"], ["look", "--kind", "sideways", "--name", "x", "--inputs", "y"],
                     ["no-such-command"], ["resume", "--name"], ["go", "--kind", "sunrise", "--name", "x", "--run", "nonsense", "--manifest-sha256", "0"]):
            result = self.m.run_child(*argv)
            self.assertEqual(result.code, exits.USAGE, (argv, result.text))
            self.assertEqual(result.out, "")
            self.assertEqual(result.err.strip(), texts.USAGE)

    def test_E16_15_json_on_standard_output_and_nothing_else_with_interface_version_1(self):
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.check()]))
        looked = self.m.look()
        self.assertEqual(looked.code, exits.SUCCESS, looked.text)
        doc = json.loads(looked.out)
        self.assertEqual(doc["interface_version"], 1)
        self.assertEqual(doc["plugin_version"], "0.1.0")
        self.assertEqual(schemas.errors("cli-response", doc), [])
        refused = self.m.run_child("status", "--name", "nothing-here")
        self.assertEqual(refused.code, exits.TERMINAL)
        self.assertEqual(json.loads(refused.out)["ending"], "refused")
        self.assertEqual(schemas.errors("cli-response", json.loads(refused.out)), [])
        self.assertEqual(refused.err, "")

    def test_E16_15_exit_4_where_a_lanes_rows_fail_validation_and_exit_10_at_an_ending(self):
        bad = rowlib.check()
        bad["before_test"] = [{"read": "path", "path": rowlib.DEV, "is": "dir"}]
        rowlib.install(self.m, rowlib.lane("sunrise", [bad]))
        looked = self.m.look()
        self.assertEqual(looked.code, exits.VALIDATION, looked.text)
        self.assertEqual(looked.doc["findings"][0]["row"], "K1")
        self.assertEqual(looked.doc["findings"][0]["entry"], "before_test")
        os.rename(self.m.vault, self.m.vault + ".gone")
        self.assertEqual(self.m.look().code, exits.TERMINAL)

    def test_E16_15_exit_1_on_a_defect_reported_by_its_type_and_never_its_message(self):
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.check()]))
        secret = harness.canary("exception")
        from sun_core import plan

        def boom(*_a, **_k):
            raise RuntimeError("a message holding " + secret)
        original, plan.build = plan.build, boom
        try:
            result = self.m.look()
        finally:
            plan.build = original
        self.assertEqual(result.code, exits.GENERAL)
        self.assertEqual(result.out, "")
        self.assertIn("RuntimeError", result.err)
        self.assertNowhere(secret, result)

    def test_E16_15_skill_identity(self):
        result = self.m.run_child("skill-identity")
        self.assertEqual(result.code, 0, result.text)
        doc = json.loads(result.out)
        self.assertEqual((doc["name"], doc["version"], doc["interface_version"]), ("sun-v2", "0.1.0", 1))
        self.assertRegex(doc["content_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual(doc["skills"], ["sunrise-v2", "sunset-v2"])
        self.assertEqual(schemas.errors("cli-response", doc), [])

    def test_nothing_in_the_session_makes_the_shipped_tool_load_code(self):
        # the control room's line: the shipped core loads no code that the environment names
        marker = os.path.join(self.tmp, "hook-ran")
        hook = os.path.join(self.tmp, "hook.py")
        with open(hook, "w") as fh:
            fh.write("open(%r, 'w').write('ran')\ndef install(world):\n    open(%r, 'w').write('installed')\n" % (marker, marker))
        argv = ("status", "--name", "nothing-here")
        plain = self.m.run_child(*argv)
        hooked = self.m.run_child(*argv, env={"SUN_V2_TEST": "1", "SUN_V2_TEST_HOOK": hook, "PYTHONSTARTUP": hook})
        self.assertFalse(os.path.exists(marker), "a file the environment named was run by the shipped tool")
        self.assertEqual((hooked.code, hooked.out, hooked.err), (plain.code, plain.out, plain.err))
        source = open(os.path.join(harness.SCRIPTS, "sun_core", "world.py")).read()
        for word in ("SUN_V2_TEST", "importlib", "exec_module", "__import__"):
            self.assertNotIn(word, source)


if __name__ == "__main__":
    unittest.main()
