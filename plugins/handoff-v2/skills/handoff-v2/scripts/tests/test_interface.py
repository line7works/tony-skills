"""The CLI's shape (back-loop sections 2 and 3): the phases in the contract's order, `--help` without jsonschema,
exit 3 without it, a phase against the wrong phase exit 2 naming the command to run instead, every phase built
(none answers `phase-not-built`), and the manual-only controls (owner pick P5) on this core.
"""
import os
import re
import unittest

import hlib
import testlib

PHASES = ("select", "photograph", "gate", "record-answer", "write", "report")


class TheHelp(unittest.TestCase):

    def test_help_lists_the_phases_in_order_without_jsonschema(self):
        tmp = testlib.make_scratch("handoff-help-")
        self.addCleanup(testlib.rmtree, tmp)
        stub = testlib.stub_without_jsonschema(tmp)
        code, out, err = testlib.run_driver(["--help"], env=testlib.base_env({"PYTHONPATH": stub}),
                                            python="/usr/bin/python3" if os.path.exists("/usr/bin/python3") else None)
        self.assertEqual(code, 0, err)
        order = re.search(r"The phases, in order: (.+)\.", out).group(1)
        self.assertEqual(order, "check-input, " + ", ".join(PHASES))
        self.assertNotIn("not built yet", out)

    def test_without_jsonschema_check_input_is_exit_3(self):
        tmp = testlib.make_scratch("handoff-nojs-")
        self.addCleanup(testlib.rmtree, tmp)
        stub = testlib.stub_without_jsonschema(tmp)
        path = os.path.join(tmp, "input.json")
        testlib.write_json(path, hlib.make_input(tmp, os.path.join(tmp, "run")))
        code, out, err = testlib.run_driver(["check-input", path], env=testlib.base_env({"PYTHONPATH": stub}))
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("missing dependency: jsonschema", err)


@unittest.skipUnless(hlib.jsonschema_here(), "the driver needs jsonschema (run under uv)")
class ThePhases(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-phases-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_a_phase_out_of_order_is_exit_2_naming_the_command_to_run(self):
        ws, _ = hlib.make_repo(self.tmp)
        drive, run_dir = hlib.start(self.tmp, ws)
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))
        self.assertIn("select", err)

    def test_the_input_station_fields_are_closed(self):
        ws, _ = hlib.make_repo(self.tmp)
        path = os.path.join(self.tmp, "bad-input.json")
        doc = hlib.make_input(ws, os.path.join(self.tmp, "run-bad"), surprise=True)
        testlib.write_json(path, doc)
        code, out, err = hlib.Driver(self.tmp)(["check-input", path])
        self.assertEqual(code, 4, (out, err))


class TheManualOnlyControls(unittest.TestCase):
    """Owner pick P5: handoff-v2 keeps `disable-model-invocation: true` and the Codex manual-only sidecar."""

    def test_the_frontmatter_carries_the_flag(self):
        with open(os.path.join(testlib.SKILL, "SKILL.md"), encoding="utf-8") as fh:
            body = fh.read()
        front = body.split("---\n")[1]
        self.assertIn("\ndisable-model-invocation: true\n", "\n" + front)
        self.assertTrue(re.search(r"^name: handoff-v2$", front, flags=re.M))

    def test_the_codex_sidecar_carries_the_policy(self):
        with open(os.path.join(testlib.SKILL, "agents", "openai.yaml"), encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("allow_implicit_invocation: false", body)

    def test_the_skill_names_the_summons_and_never_auto_invokes(self):
        with open(os.path.join(testlib.SKILL, "SKILL.md"), encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("STRICTLY user-invoked", body)
        self.assertNotIn("not built yet", body)


if __name__ == "__main__":
    unittest.main()
