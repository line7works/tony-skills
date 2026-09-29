"""The lane contract read against the code (CR-11, required test 1).

`references/architect-v2-contract.md` names this core's own commands and its own stop tags in two
tables; `--help` lists exactly those commands under "Commands of this core", each command
answers `--help`, the result schema's `stop_tag` enum holds the shared tags and exactly these
own ones, and its description names every one. The contract names no v1 path and holds no em dash;
`SKILL.md` names every phase and own command it runs and stays under 250 lines.
"""
import json
import os
import re
import unittest

import testlib

CONTRACT = os.path.join(testlib.REF, "architect-v2-contract.md")
SHARED_TAGS = ["phase-not-built", "selection-none", "selection-several", "ledger-refused", "write-refused",
               "records-refused"]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def table_names(heading):
    text = read(CONTRACT)
    start = text.find(heading)
    if start < 0:
        return None
    body = text[start + len(heading):]
    stop = body.find("\n## ")
    body = body if stop < 0 else body[:stop]
    return [m.group(1) for m in re.finditer(r"(?m)^\| `([a-z][a-z0-9-]*)`", body)]


class OwnCommands(unittest.TestCase):

    def test_the_contract_and_help_list_the_same_commands(self):
        named = table_names("### Own commands")
        self.assertTrue(named, "the contract has an Own commands table")
        code, out, err = testlib.run_driver(["--help"])
        self.assertEqual(code, 0, err)
        section = out.split("Commands of this core", 1)[1].split("\n\n", 1)[0]
        listed = re.findall(r"(?m)^  ([a-z][a-z0-9-]*) ", section)
        self.assertEqual(sorted(listed), sorted(named))

    def test_every_own_command_answers_help(self):
        for name in table_names("### Own commands"):
            code, out, err = testlib.run_driver([name, "--help"])
            self.assertEqual(code, 0, (name, err))
            self.assertIn("--run-dir", out, name)


class StopTags(unittest.TestCase):

    def test_the_contract_and_the_schema_hold_the_same_own_tags(self):
        own = table_names("### Own stop tags")
        self.assertTrue(own, "the contract has an Own stop tags table")
        schema = json.loads(read(os.path.join(testlib.REF, "result.schema.json")))
        enum = [t for t in schema["properties"]["stop_tag"]["enum"] if t]
        self.assertEqual(sorted(enum), sorted(SHARED_TAGS + own))
        described = schema["properties"]["stop_tag"]["description"]
        for tag in enum:
            self.assertIn("`%s`" % tag, described)
        self.assertEqual(set(own) & set(SHARED_TAGS), set(), "an own tag never reuses a shared one")


class TheProse(unittest.TestCase):

    def test_no_em_dash_and_no_v1_path(self):
        for path in (CONTRACT, os.path.join(testlib.SKILL, "SKILL.md")):
            text = read(path)
            self.assertNotIn("\u2014", text, path)
            self.assertNotIn("plugins/" + "archi" + "tect/", text, path)

    def test_the_procedure_names_every_command_and_stays_short(self):
        text = read(os.path.join(testlib.SKILL, "SKILL.md"))
        self.assertLess(len(text.splitlines()), 250)
        for name in ["check-input", "select", "harvest", "record-answer", "write", "report"] + \
                table_names("### Own commands"):
            self.assertIn("`%s" % name, text, name)
        self.assertIn("disable-model-invocation: true", text)


class TheRulingsInTheWords(unittest.TestCase):
    """R5, R6, R7: the control room's rulings stand in the procedure, the contract and the profiles."""

    NEW_RUN = "start a new run on the same doc whose input carries his words verbatim in `owner_word`"

    def text(self, *rel):
        return read(os.path.join(testlib.SKILL, *rel))

    def test_a_reviewer_named_at_the_offer_means_a_new_run(self):
        skill = " ".join(self.text("SKILL.md").split())
        self.assertIn(self.NEW_RUN, skill)
        self.assertIn("Never add the flag or the word by hand.", skill)
        contract = " ".join(read(CONTRACT).split())
        self.assertIn("ruled: the executor ends this run and starts a new one whose input carries the word; "
                      "this core does not widen the source", contract)
        self.assertNotIn("needs the control room's ruling on a second source", contract)
        for harness in ("claude-code", "codex"):
            profile = " ".join(self.text("adapters", harness, "profile.md").split())
            self.assertIn(self.NEW_RUN, profile, harness)

    def test_the_three_step_6_rules_are_back(self):
        skill = " ".join(self.text("SKILL.md").split())
        self.assertIn("a call the harness backgrounds past its foreground limit is not a failure: wait for its "
                      "notification and judge what arrives", skill)
        self.assertIn("unescape HTML entities (`&amp;`, `&lt;`, `&gt;`) in the raw text before `save-take`; it is "
                      "the only transformation", skill)
        self.assertIn("failed_lanes", skill)

    def test_a_single_hit_is_matched_by_its_intent_line(self):
        skill = " ".join(self.text("SKILL.md").split())
        self.assertIn("`one`: read its `Intent:` line; when it is the project he is talking about, that is the "
                      "scope doc; when it is not, treat the hunt as `none`.", skill)

    def test_the_readme_and_the_driver_carry_no_stale_words(self):
        readme = read(os.path.join(testlib.PLUGIN, "README.md"))
        self.assertNotIn("the shared driver test that expects the four phases unbuilt", readme)
        driver = read(testlib.DRIVER)
        self.assertEqual(len(re.findall(r"(?m)^import os$", driver)), 1)


if __name__ == "__main__":
    unittest.main()
