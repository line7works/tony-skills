"""The lane contract read against the code (lane contract section 12, required test 1).

`references/inspect-v2-contract.md` names this core's own commands and its own stop tags; `--help`
lists exactly those commands under "Commands of this core", and the result schema's `stop_tag`
enum and description carry exactly the shared tags plus those. The contract quotes each fixed
mandate verbatim, as the code sends it; `references/inspect-mandate.md` is v1's outside mandate
byte for byte (its hash, recorded when it was carried over); `SKILL.md` names every command it
runs, stays under 250 lines, and states no deference to another skill as law.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()

from inspect_core import mandates  # noqa: E402

CONTRACT = os.path.join(testlib.REF, "inspect-v2-contract.md")
SHARED_TAGS = ["phase-not-built", "selection-none", "selection-several", "ledger-refused",
               "write-refused", "records-refused"]
# sha256 of v1's outside mandate as it was carried over (E14-12: the fixed mandate, byte for byte)
MANDATE_SHA256 = "086506ee6e0dcd4946b54d9f860d411e4b25839b5c8c218b2df6b93d2d99af35"


def contract():
    return testlib.read_text(CONTRACT)


def section(title):
    text = contract()
    start = text.index("\n## %s" % title)
    end = text.find("\n## ", start + 1)
    return text[start:end if end > 0 else len(text)]


def table_names(block):
    return [m.group(1) for m in re.finditer(r"^\| `([a-z-]+)` \|", block, re.M)]


class TheContractAndTheCode(unittest.TestCase):

    def help_text(self):
        proc = subprocess.run([sys.executable, testlib.DRIVER, "--help"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return proc.stdout.decode()

    def test_the_own_commands_are_the_contracts(self):
        named = table_names(section("5. The core's own commands"))
        self.assertEqual(named, ["named", "choose", "packet", "request"])
        text = self.help_text()
        block = text.split("Commands of this core", 1)[1].split("\n\n", 1)[0]
        listed = [line.split()[0] for line in block.splitlines()[1:] if line.strip()]
        self.assertEqual(listed, named)

    def test_the_stop_tags_are_the_contracts(self):
        own = table_names(section("11. Stops"))
        self.assertTrue(set(SHARED_TAGS) <= set(own), own)
        schema = testlib.load_json(os.path.join(testlib.REF, "result.schema.json"))
        enum = [t for t in schema["properties"]["stop_tag"]["enum"] if t]
        self.assertEqual(sorted(enum), sorted(own))
        described = [t.strip("`") for t in schema["properties"]["stop_tag"]["description"].split("`")[1::2]]
        for tag in own:
            self.assertIn(tag, described)

    def test_every_mandate_is_quoted_verbatim(self):
        text = contract()
        for lens, body in sorted(mandates.CLAUDE.items()):
            self.assertIn(body, text, lens)
        self.assertIn(mandates.REPORTING, text)
        self.assertIn(mandates.OUTSIDE_LINE, text)
        self.assertIn(mandates.NO_RECORD_LINE, text)

    def test_the_outside_mandate_is_v1s_byte_for_byte(self):
        with open(os.path.join(testlib.REF, "inspect-mandate.md"), "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), MANDATE_SHA256)
        body = testlib.read_text(os.path.join(testlib.REF, "inspect-mandate.md"))
        for slot in ("[CODE_BOOK]", "[BUILD_DOC]", "[SCOPE_DOC_OR_NO_RECORD]"):
            self.assertEqual(body.count(slot), 1, slot)

    def test_the_procedure_names_every_command_and_stays_short(self):
        skill = testlib.read_text(os.path.join(testlib.SKILL, "SKILL.md"))
        self.assertLess(len(skill.splitlines()), 250)
        for command in ("check-input", "select", "named", "choose", "harvest", "packet", "request",
                        "record-answer", "write", "report"):
            self.assertIn("inspect_v2.py %s" % command, skill, command)
        self.assertNotIn("is the law", skill)
        self.assertNotIn("is the law", contract())
        self.assertNotIn("frame (E14 slice 1)", skill, "the skeleton's placeholder is gone")

    def test_the_re_inspection_closure_lines_retire_under_p8(self):
        # CI1-9: said once, in section 2, so the claim "nothing v1 decided changes" is not silent on it
        kept = section("2. What is kept from v1")
        self.assertIn("re-inspection writes no `fixed | not fixed` line", kept)
        self.assertIn("pick P8", kept)

    def test_the_intent_fallback_and_the_named_doc_are_stated(self):
        # CI1-11 and CI1-10: v1 Step 1's Intent-line fallback, and a doc the invocation names
        skill = testlib.read_text(os.path.join(testlib.SKILL, "SKILL.md"))
        step = skill.split("## Step 2", 1)[1].split("## Step 3", 1)[0]
        self.assertIn("select --run-dir D --hunt build` without `--name`", step)
        self.assertIn("choose --run-dir D --hunt build --path <candidate> --by intent", step)
        self.assertIn("inspect_v2.py named --run-dir D --path <the doc>", step)
        hunts = section("6. The hunt, the packet and the requests")
        self.assertIn("`named`", hunts)
        self.assertIn("`scope/*.md` and `*-scope.md`", hunts)

    def test_the_answer_schema_names_the_rules_the_contract_states(self):
        rules = table_names(section("7. record-answer"))
        for rule in ("independence", "session-mismatch", "run-mismatch", "row-mismatch",
                     "owner-word-mismatch", "lanes-mismatch", "duplicate-call", "field-separator",
                     "unknown-finding", "refuted-citation", "unauthorized-send"):
            self.assertIn(rule, rules)


if __name__ == "__main__":
    unittest.main()
