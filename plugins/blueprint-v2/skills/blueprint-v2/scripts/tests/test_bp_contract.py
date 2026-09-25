"""The lane contract read against the code (lane L, readings CR-6, CR-11 and CR-12, required test 1).

`references/blueprint-v2-contract.md` states the core's own commands, its stop tags, its own
refusal rules, its allowed trace kinds and its hunts; this suite holds each list to the code that
implements it: the driver's `--help` ("Commands of this core"), the result schema's `stop_tag`
enum and description, `blueprint_core/checks.py`, and `scripts/blueprint.py`'s hunt table.
`SKILL.md` names every command it runs and stays under 250 lines.
"""
import importlib.util
import json
import os
import re
import unittest

import testlib

testlib.add_scripts_to_path()

from blueprint_core import checks  # noqa: E402

CONTRACT = os.path.join(testlib.REF, "blueprint-v2-contract.md")
SKILL_MD = os.path.join(testlib.SKILL, "SKILL.md")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def section(text, heading):
    start = text.index("\n## %s" % heading)
    rest = text[start + 1:]
    stop = rest.find("\n## ", 1)
    return rest if stop < 0 else rest[:stop]


def first_column(block):
    return [m.group(1) for m in re.finditer(r"^\| `([^`]+)` \|", block, re.M)]


def driver_module():
    spec = importlib.util.spec_from_file_location("blueprint_driver_under_test", testlib.DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheContractAndTheCode(unittest.TestCase):

    def setUp(self):
        self.contract = read(CONTRACT)

    def help_text(self):
        code, out, err = testlib.run_driver(["--help"])
        self.assertEqual(code, 0, err)
        return out

    def test_the_own_commands_are_the_ones_help_lists(self):
        stated = first_column(section(self.contract, "9. Own commands"))
        help_text = self.help_text()
        block = help_text[help_text.index("Commands of this core"):]
        block = block[:block.index("\n\n")]
        listed = re.findall(r"^  (\S+)\s", block, re.M)
        self.assertEqual(stated, listed)
        self.assertEqual(stated, [c["name"] for c in driver_module().COMMANDS])

    def test_the_stop_tags_are_the_result_schemas(self):
        stated = first_column(section(self.contract, "12. Stop tags"))
        result = json.loads(read(os.path.join(testlib.REF, "result.schema.json")))
        enum = [t for t in result["properties"]["stop_tag"]["enum"] if t]
        described = [t.strip("`") for t in result["properties"]["stop_tag"]["description"].split("`")[1::2]]
        self.assertEqual(sorted(stated), sorted(enum))
        self.assertEqual(sorted(set(described)), sorted(enum))

    def test_the_own_refusals_are_the_checks(self):
        stated = first_column(section(self.contract, "7. The recorded answer"))
        self.assertEqual(sorted(stated), sorted(checks.RULES))

    def test_the_allowed_traces_are_the_checks(self):
        block = section(self.contract, "7. The recorded answer")
        line = next(l for l in block.split("\n") if l.startswith("Allowed trace kinds:"))
        self.assertEqual(tuple(re.findall(r"`([^`]+)`", line)), checks.ALLOWED_TRACES)

    def test_the_hunts_are_the_drivers(self):
        block = section(self.contract, "5. Selection")
        hunts = driver_module().HUNTS
        rows = re.findall(r"^\| `(\w+)` \| `([^`]+)` \| (\d) \|", block, re.M)
        stated = sorted((h, g, int(t)) for h, g, t in rows)
        actual = sorted((name, glob_, home["tier"]) for name, homes in hunts.items()
                        for home in homes for glob_ in home["globs"])
        self.assertEqual(stated, actual)

    def test_the_verify_forms_are_the_checks(self):
        block = section(self.contract, "7. The recorded answer")
        line = next(l for l in block.split("\n") if l.startswith("Verify forms:"))
        self.assertEqual(tuple(re.findall(r"`([^`]+)`", line)), checks.VERIFY_FORMS)

    def test_the_readme_carries_no_stale_join_sentence(self):
        readme = read(os.path.join(testlib.PLUGIN, "README.md"))
        self.assertNotIn("still asserts", readme)
        self.assertNotIn("phase-not-built", readme)

    def test_the_contract_says_records_are_never_opened(self):
        self.assertIn("never opens the records component", self.contract)


class TheProcedure(unittest.TestCase):

    def test_skill_md_names_every_command_and_fits(self):
        text = read(SKILL_MD)
        self.assertLess(len(text.split("\n")), 250)
        self.assertTrue(text.startswith("---\nname: blueprint-v2\n"))
        for command in ("check-input", "select", "choose", "harvest", "record-answer", "write", "report"):
            self.assertIn("`%s" % command, text, command)
        self.assertNotIn("phase-not-built", text)
        self.assertIn("BLUEPRINT:", text)


if __name__ == "__main__":
    unittest.main()
