"""SKILL.md: the portable procedure, held to the CLI it drives and to v1's behaviour.

Three things this suite proves, and each of them has failed in a shipped skill before:

1. **The body names the real commands.** Every command the skill tells the executor to type is a
   command the CLI actually has, spelled the way it is spelled, in the order the phases run. A
   changed flag or a renamed phase fails here rather than in a session.
2. **The frontmatter is portable.** Standard fields only, the name matches the directory, and no
   harness-specific substitution (`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, an `@file` include, inline
   shell-output injection) is in the body. `adapters/` and `setups/` are slice 3's, and the seam
   stays open.
3. **v1's behaviour is kept** (ruling E13-1): the five steps, the nine rules, the block's shape,
   and the "what NOT to do" list are all still here, in a body that names the scripts.
"""
import os
import re
import unittest

import testlib

testlib.add_scripts_to_path()

SKILL = os.path.join(testlib.SKILL, "SKILL.md")
CONTRACT = os.path.join(testlib.REF, "build-contract.md")

COMMANDS = ("check-input", "contract", "preflight", "record-answer", "report")
FORBIDDEN = ("$ARGUMENTS", "${CLAUDE_SKILL_DIR}", "${CLAUDE_PLUGIN_ROOT}", "!`", "@references/")
STANDARD_FRONTMATTER = {"name", "description", "metadata"}


def body():
    with open(SKILL, encoding="utf-8") as fh:
        return fh.read()


def flowed(text):
    """The body with its line wrapping removed, so a phrase split across two lines still reads
    as one phrase. A wrapped sentence is the same sentence."""
    return re.sub(r"\s+", " ", text)


def frontmatter(text):
    """The YAML block between the first two `---` lines, as {key: raw text}, without a parser."""
    lines = text.split("\n")
    assert lines[0] == "---", "SKILL.md starts with valid frontmatter"
    end = lines.index("---", 1)
    fields = {}
    key = None
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            key = match.group(1)
            fields[key] = match.group(2)
        elif key is not None:
            fields[key] += "\n" + line.strip()
    return fields, "\n".join(lines[end + 1:])


class TheFrontmatter(unittest.TestCase):

    def setUp(self):
        self.fields, self.rest = frontmatter(body())

    def test_the_name_matches_the_directory(self):
        self.assertEqual(self.fields["name"], os.path.basename(testlib.SKILL))
        self.assertEqual(self.fields["name"], "build-v2")

    def test_only_standard_fields(self):
        self.assertEqual(set(self.fields), STANDARD_FRONTMATTER,
                         "an extended field belongs in an adapter, not in the portable body")

    def test_the_version_is_the_plugins(self):
        manifest = testlib.load_json(os.path.join(testlib.PLUGIN, ".claude-plugin", "plugin.json"))
        self.assertIn('"%s"' % manifest["version"], self.fields["metadata"])

    def test_the_description_says_what_it_is_and_what_it_is_not(self):
        description = self.fields["description"]
        for word in ("slice", "build doc", "Not ", "check"):
            self.assertIn(word, description, word)
        self.assertLess(len(description), 1200, "the description survives a shortened catalog view")


class TheBodyIsPortable(unittest.TestCase):

    def test_no_harness_substitution_is_in_the_body(self):
        text = body()
        for token in FORBIDDEN:
            self.assertNotIn(token, text, token)

    def test_no_adapter_or_setup_is_named(self):
        """Slice 3 builds them; this lane leaves the seam open and names none."""
        text = body().lower()
        for token in ("adapters/", "setups/", "agents/openai.yaml"):
            self.assertNotIn(token, text, token)

    def test_no_harness_is_named_as_the_one_it_runs_in(self):
        text = body()
        for name in ("Claude Code", "Codex", "OpenCode"):
            self.assertNotIn(name, text, name)

    def test_the_body_fits_the_smallest_documented_budget(self):
        """Codex 0.154.0 has an 8,000-byte main-prompt truncation branch for plugin skills."""
        size = len(body().encode("utf-8"))
        self.assertLess(size, 24000, "the body is %d bytes" % size)


class TheBodyNamesTheRealCommands(unittest.TestCase):

    def setUp(self):
        self.text = body()
        _, _, self.help_text = testlib.run_build(["--help"])
        code, self.help_out, _ = testlib.run_build(["--help"])
        self.assertEqual(code, 0)

    def test_every_command_the_body_types_exists_in_the_cli(self):
        typed = set(re.findall(r"build\.py\s+([a-z-]+)", self.text))
        self.assertTrue(typed, "the body types at least one command")
        for command in sorted(typed):
            self.assertIn(command, self.help_out, "the CLI has no command %r" % command)

    def test_every_phase_is_typed_in_the_body_in_order(self):
        positions = []
        for command in COMMANDS:
            index = self.text.find("build.py %s" % command)
            self.assertNotEqual(index, -1, "the body never types %r" % command)
            positions.append(index)
        self.assertEqual(positions, sorted(positions), "the phases are named out of order")

    def test_every_flag_the_body_types_is_a_flag_the_cli_takes(self):
        for flag in sorted(set(re.findall(r"(--[a-z][a-z-]*)", self.text))):
            if flag in ("--run-dir", "--answer", "--skill-root", "--records-root", "--input",
                        "--verbose", "--with", "--python", "--quiet"):
                continue
            self.fail("the body types an unexpected flag: %s" % flag)

    def test_the_documented_commands_run(self):
        """The guide: exercise the skill's documented commands against the shipped CLI."""
        scratch = testlib.make_scratch("build-v2-body-")
        self.addCleanup(testlib.rmtree, scratch)
        ws = testlib.make_workspace(scratch)
        run_dir = os.path.join(scratch, "run")
        ip = os.path.join(scratch, "input.json")
        testlib.write_json(ip, testlib.make_input(run_dir, ws))
        ap = os.path.join(scratch, "answer.json")
        testlib.write_json(ap, testlib.ANSWER)
        for args, expect in ((["check-input", ip], 0), (["contract", "--run-dir", run_dir], 0),
                             (["preflight", "--run-dir", run_dir], 0),
                             (["record-answer", "--run-dir", run_dir, "--answer", ap], 0),
                             (["report", "--run-dir", run_dir], 10)):
            code, out, err = testlib.run_build(args)
            self.assertEqual(code, expect, "%s: %s%s" % (args, out, err))

    def test_every_reference_the_table_names_exists(self):
        table = self.text.split("## References")[-1]
        for path in re.findall(r"`(references/[^`]+)`", table):
            full = os.path.join(testlib.SKILL, path.rstrip("/"))
            self.assertTrue(os.path.exists(full), path)

    def test_every_reference_file_is_named_in_the_table(self):
        table = self.text.split("## References")[-1]
        for name in sorted(os.listdir(testlib.REF)):
            if name == "examples":
                self.assertIn("references/examples/", table)
            else:
                self.assertIn("references/%s" % name, table, name)


class V1BehaviourIsKept(unittest.TestCase):
    """Ruling E13-1: no slice changes what build decides. The body still says all of it."""

    def setUp(self):
        self.text = body()

    def test_the_spine_and_the_unforgivable_move(self):
        self.assertIn("The spec is the only source of requirements", self.text)
        self.assertIn("fake completeness", self.text)
        self.assertIn("Honest incompleteness", self.text)

    def test_all_nine_rules_are_there(self):
        rules = self.text.split("## The rules")[1].split("## Output")[0]
        for number in range(1, 10):
            self.assertIn("%d. **" % number, rules, "rule %d" % number)
        for phrase in ("traces to a spec line", "gap protocol", "Reuse before writing",
                       "No stubs, ever", "Descoping is a deviation", "No orphaned code",
                       "Blast radius", "Thrash limit: two", "Report faithfully"):
            self.assertIn(phrase, rules, phrase)

    def test_the_five_steps_are_all_present(self):
        for heading in ("Find the doc and the slice", "Post the contract", "Preflight",
                        "Build, verify, and record your answer", "Report"):
            self.assertIn(heading, self.text, heading)

    def test_the_contract_form_is_kept(self):
        for label in ("In scope:", "Not authorized:", "Reuse:", "Footprint:", "New:"):
            self.assertIn("**%s**" % label, self.text, label)

    def test_the_doc_resolution_order_is_kept(self):
        flat = flowed(self.text)
        for phrase in ("docs/plans/*.md", "docs/<feature>-build-plan.md", "Intent:",
                       "stop-and-ask", "never the lone doc on disk"):
            self.assertIn(phrase, flat, phrase)

    def test_the_block_keeps_its_shape(self):
        block = self.text.split("## Output")[1]
        for line in ("BUILD:", "Status:", "Spec:", "Method:", "Bottom line:", "Built",
                     "Deviations", "Assumptions", "Discovered", "New",
                     "Ready for /signoff:", "SKILL NOTE:"):
            self.assertIn(line, block, line)

    def test_the_block_adds_what_this_core_now_reports(self):
        block = self.text.split("## Output")[1]
        for line in ("Out of scope", "Checks", "Card", "Result"):
            self.assertIn(line, block, line)

    def test_the_what_not_to_do_list_is_kept(self):
        section = flowed(self.text.split("## What NOT to do")[1])
        for phrase in ("invent requirements", "stubs or vacuous tests", "gold-plate",
                       "dependency the contract doesn't name", "attempt three",
                       "push, open a pull request, or merge"):
            self.assertIn(phrase, section, phrase)

    def test_the_boundaries_say_who_may_write_what(self):
        flat = flowed(self.text)
        for phrase in ("the script makes every write", "builder writes intentions",
                       "never read the conversation for scope"):
            self.assertIn(phrase, flat, phrase)

    def test_the_body_never_tells_the_executor_to_run_an_unnamed_check(self):
        """It directs the executor to the checks the SLICE names, never to invent one."""
        self.assertIn("Run each check the slice names", flowed(self.text))


class TheContractDocumentIsComplete(unittest.TestCase):

    def test_it_has_every_section_its_own_table_of_contents_names(self):
        with open(CONTRACT, encoding="utf-8") as fh:
            text = fh.read()
        contents = text.split("Contents:")[1].split("\n\n")[0]
        for entry in re.findall(r"(\d+) ([A-Za-z][^·\n]*)", contents):
            number, title = entry[0], entry[1].strip().rstrip(".")
            self.assertIn("## %s. %s" % (number, title), text, title)

    def test_it_names_the_authorized_writes_and_nothing_else(self):
        with open(CONTRACT, encoding="utf-8") as fh:
            text = fh.read()
        for phrase in ("run's own artifacts", "card_set", "`Status:` line"):
            self.assertIn(phrase, text, phrase)
        self.assertIn("Anything else is a defect of this core", text)


if __name__ == "__main__":
    unittest.main()
