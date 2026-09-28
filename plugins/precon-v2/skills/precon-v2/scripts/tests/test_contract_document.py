"""The lane contract read against the code (required test 1).

`references/precon-v2-contract.md` states, in its Interface section, the commands of this core
and the stop tags it can end a run in. Each own command (a row of the Commands table that no
shared command names) is listed under "Commands of this core" in the driver's `--help`, and no
other own command is; each stop tag is in the result schema's
`stop_tag` enum and named in its description, and the lane's own tags are exactly the enum's
tags that are not shared; `SKILL.md` names every command it runs; the quoted mandate is the one
the code sends.
"""
import os
import re
import unittest

import testlib

CONTRACT = os.path.join(testlib.REF, "precon-v2-contract.md")
SHARED_TAGS = ("phase-not-built", "selection-none", "selection-several", "ledger-refused", "write-refused",
               "records-refused")


def table(heading):
    """The first column of the Markdown table under `heading`, backticks stripped."""
    text = testlib.read_text(CONTRACT)
    start = text.index("\n%s\n" % heading) + len(heading) + 2
    rows = []
    for line in text[start:].split("\n"):
        if line.startswith("#"):
            break
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        cell = line.split("|")[1].strip()
        if cell.startswith("`"):
            rows.append(cell.strip("`"))
    return rows


def own_commands():
    """The Commands table's rows that are no shared command's (E14 slice 3c: one table, build-v2's
    shape, where the frame had "Shared commands" and "Commands of this core")."""
    testlib.add_scripts_to_path()
    from station_core import driver
    return [name for name in table("### Commands") if name not in driver.SHARED_COMMANDS]


def own_help_lines():
    code, out, err = testlib.run_driver(["--help"])
    assert code == 0, err
    block = out.split("Commands of this core")[1].split("\n\n")[0]
    return [line.split()[0] for line in block.split("\n")[1:] if line.strip()]


class TheContract(unittest.TestCase):

    def test_the_own_commands_are_the_helps(self):
        commands = own_commands()
        self.assertEqual(sorted(commands), ["request", "state"])
        self.assertEqual(sorted(own_help_lines()), sorted(commands))

    def test_every_command_the_contract_names_answers_help(self):
        for command in table("### Commands"):
            code, out, err = testlib.run_driver([command, "--help"])
            self.assertEqual(code, 0, (command, err))

    def test_every_stop_tag_is_in_the_result_schema(self):
        schema = testlib.load_json(os.path.join(testlib.REF, "result.schema.json"))
        enum = [t for t in schema["properties"]["stop_tag"]["enum"] if t]
        description = schema["properties"]["stop_tag"]["description"]
        tags = table("### Stop tags")
        self.assertTrue(tags)
        for tag in tags:
            self.assertIn(tag, enum, tag)
            self.assertIn("`%s`" % tag, description, tag)
        own = [t for t in tags if t not in SHARED_TAGS]
        self.assertEqual(sorted(own), sorted(t for t in enum if t not in SHARED_TAGS))
        self.assertEqual(sorted(own), ["doc-changed", "form-refused", "no-scope-doc"])

    def test_the_code_emits_only_the_tags_the_contract_names(self):
        tags = set(table("### Stop tags"))
        emitted = set()
        for base, dirs, files in os.walk(os.path.join(testlib.SCRIPTS, "precon_core")):
            for name in files:
                if name.endswith(".py"):
                    emitted.update(re.findall(r'stop_tag="([a-z-]+)"', testlib.read_text(os.path.join(base, name))))
                    emitted.update(re.findall(r'TAG_[A-Z_]+ = "([a-z-]+)"', testlib.read_text(os.path.join(base, name))))
        self.assertTrue(emitted)
        self.assertEqual(sorted(emitted - tags), [])

    def test_the_skill_names_every_command_it_runs(self):
        skill = testlib.read_text(os.path.join(testlib.SKILL, "SKILL.md"))
        for command in ("check-input", "select", "harvest", "state", "request", "record-answer", "write", "report"):
            self.assertIn("`%s" % command, skill, command)
        self.assertLess(len(skill.split("\n")), 250)

    def test_the_round_header_is_stated_not_deferred(self):
        # CP1-12: the procedure states the round header itself (v1's form, quoted byte for byte, the
        # board as `state` printed it), never "as v1's header does"
        skill = testlib.read_text(os.path.join(testlib.SKILL, "SKILL.md"))
        header = "Round N %s <tier> %s board: decided N · assumed N · parked N · open your-calls N" % (
            chr(0x2014), chr(0x2014))
        self.assertIn("`%s`" % header, skill)
        self.assertNotIn("as v1's", skill)

    def test_the_panel_pointer_keeps_v1_s_words(self):
        # CP1-13: the suggest-only pointer names the panel skill as v1 does
        skill = testlib.read_text(os.path.join(testlib.SKILL, "SKILL.md"))
        self.assertIn("this smells like a /jpb", skill)

    def test_the_quoted_mandate_is_the_code_s(self):
        text = testlib.read_text(CONTRACT)
        start = text.index("```mandate\n") + len("```mandate\n")
        quoted = text[start:text.index("\n```", start)]
        testlib.add_scripts_to_path()
        from precon_core import exit_test
        self.assertEqual(exit_test.MANDATE, quoted)
        self.assertEqual(text.count("```mandate\n"), 1, "quoted once")


if __name__ == "__main__":
    unittest.main()
