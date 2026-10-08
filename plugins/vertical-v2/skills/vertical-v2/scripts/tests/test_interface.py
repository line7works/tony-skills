"""vertical-v2's interface held to its documents: the examples to the schemas, the CLI to the contract's
tables, the stop tags to the result schema, the dependency exits, and the no-dash rule with its one
exception (the v1 forms, contract section 8).
"""
import json
import os
import re
import unittest

import testlib
import vlib

CONTRACT = os.path.join(testlib.REF, "vertical-contract.md")
PHASES = ["gate", "ask", "scope", "request", "record-local", "record-outside", "verdict", "report"]


def contract():
    return testlib.read_text(CONTRACT)


def section(text, heading):
    start = text.index(heading)
    rest = text[start + len(heading):]
    stop = re.search(r"^#{2,3} ", rest, flags=re.M)
    return rest[:stop.start()] if stop else rest


class TheExamples(unittest.TestCase):

    def test_every_example_holds_both_ways(self):
        if not vlib.jsonschema_here():
            self.skipTest("jsonschema is not importable here: the examples are checked under uv run")
        code, out, err = testlib.run_script("validate-examples.py", [])
        self.assertEqual(code, 0, out[-3000:] + err)
        report = json.loads(out)
        self.assertTrue(report["ok"])
        self.assertEqual(report["counts"]["stop_tags"], report["counts"]["stop_tags_with_an_example"])


class TheCommandLine(unittest.TestCase):

    def test_help_lists_the_phases_in_the_contracts_order(self):
        code, out, err = testlib.run_driver(["--help"])
        self.assertEqual(code, 0, err)
        order = out.split("The phases, in order: ")[1].split(".")[0]
        self.assertEqual(order, ", ".join(["check-input"] + PHASES))

    def test_every_command_of_the_contracts_table_is_a_command(self):
        table = section(contract(), "### Commands")
        names = set(re.findall(r"^\| `([a-z-]+)", table, flags=re.M))
        code, out, err = testlib.run_driver(["--help"])
        for name in names:
            self.assertIn(name, out, name)
        self.assertTrue(set(PHASES) <= names)

    def test_every_stop_tag_is_documented_and_emitted_by_the_schema(self):
        schema = testlib.load_json(os.path.join(testlib.REF, "result.schema.json"))
        tags = set(t for t in schema["properties"]["stop_tag"]["enum"] if t)
        table = section(contract(), "## 7. Stops and exits")
        documented = set(re.findall(r"^\| `([a-z-]+)` \|", table, flags=re.M))
        self.assertEqual(tags, documented)

    def test_without_jsonschema_check_input_exits_3_with_one_line(self):
        tmp = testlib.make_scratch("vif-")
        self.addCleanup(testlib.rmtree, tmp)
        path = vlib.write(tmp, "input.json", vlib.make_input(tmp, os.path.join(tmp, "..", "run-x")))
        env = testlib.base_env({"VERTICAL_V2_TEST": "1", "VERTICAL_V2_TEST_NO_JSONSCHEMA": "1"})
        code, out, err = testlib.run_driver(["check-input", path], env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    @unittest.skipUnless(vlib.records_usable(), "the gate runs under uv run in the checkout")
    def test_without_the_records_component_the_gate_exits_3_naming_where_it_looked(self):
        tmp = testlib.make_scratch("vif-")
        self.addCleanup(testlib.rmtree, tmp)
        ws, info = vlib.make_repo(tmp)
        drive, run_dir = vlib.start(tmp, ws)
        drive.env["VERTICAL_V2_TEST_NO_RECORDS"] = "1"
        code, out, err = drive(["gate", "--run-dir", run_dir])
        self.assertEqual(code, 3, (out, err))
        self.assertIn("missing dependency: records component", err)
        self.assertIsNone(out)


class TheNoDashRule(unittest.TestCase):

    def test_no_em_dash_outside_the_named_v1_forms(self):
        dash = "\u2014"
        skill = testlib.read_text(os.path.join(testlib.SKILL, "SKILL.md"))
        outside_output = skill.split("## Output")[0]
        self.assertFalse(dash in outside_output, "SKILL.md before its Output section")
        for folder in ("references", "adapters"):
            for base, dirs, files in os.walk(os.path.join(testlib.SKILL, folder)):
                for name in files:
                    if name.endswith((".md", ".json", ".py")):
                        self.assertFalse(dash in testlib.read_text(os.path.join(base, name)), os.path.join(base, name))
        for base, dirs, files in os.walk(os.path.join(testlib.SCRIPTS, "vertical_core")):
            for name in files:
                if name.endswith(".py"):
                    self.assertFalse(dash in testlib.read_text(os.path.join(base, name)), name)

    def test_the_mandate_is_v1s_byte_for_byte(self):
        path = os.path.join(testlib.SKILL, "assets", "vertical-mandate.md")
        self.assertEqual(testlib.sha256_file(path), "761198d9855129627f6ada47d0e985f87ede25d97ef584b728670611c223729e")


if __name__ == "__main__":
    unittest.main()
