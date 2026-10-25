"""E17 fix round 1, slice A: one full suite run per review.

The E17 canary's signoff took about 10 hours because every reviewer ran the repository's full
suite on its own beside the session's own run of it (canary finding C-12). The mandate now tells
each reviewer that the reviewing session runs the full test command once for the review, that
the reviewer does not run the full suite or any long-running sweep itself, and that it runs the
narrowest command that proves or refutes its finding instead. A finding only the full suite can
show is reported, naming the command, never run. The Read-only section's opening sentence ("Run
tests and read anything") is narrowed to that rule and nothing else in the mandate moves.

SKILL.md Step 3.5 and the contract say the same thing, so the session and the reviewers read one
rule.
"""
import os
import re
import unittest

import testlib

SKILL_ROOT = testlib.SKILL

ONE_FULL_RUN = ("The reviewing session runs the repository's full test command once for this "
                "review; you do not run the full suite or any long-running sweep yourself.")
NARROWEST = ("Run the narrowest command that proves or refutes a finding: one test module, one "
             "test, or a probe you write in your own scratch directory.")
SAY_SO = ("A finding you believe only the full suite can show is reported as such, naming the "
          "command, instead of running it.")
OLD_OPENING = "Run tests and read anything"

# The rest of the Read-only section, word for word as it stood before this slice: "Nothing else
# in the mandate changes."
UNCHANGED_READ_ONLY = (
    "No migrations against a real database, no writes to dev or prod services, no destructive "
    "commands, no git operation that changes branches or history, no edit to a tracked file. An "
    "execution the sandbox stopped is reported as \"verification blocked\", never marked "
    "checked. Use no other model, no MCP tool and no outbound service: a finding is checked "
    "against the workspace. Redirect bulk output to a file and read back the summary lines.")


def flat(text):
    """The text with every run of whitespace read as one space, so a rule wrapped across lines
    is still the same sentence."""
    return re.sub(r"\s+", " ", text)


def section(text, heading):
    """The body of one `## ` section of a Markdown text, up to the next `## ` heading."""
    start = text.index("\n## %s\n" % heading) + len("\n## %s\n" % heading)
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


class TheMandateCarriesTheOneRunRule(unittest.TestCase):
    """A `request` run's `readers/mandate.md`, written by the real CLI on a seeded case."""

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("signoff-e17-one-run-")
        case = testlib.build_case("S1-review-scope", "S1-01-clean",
                                  os.path.join(cls.dir, "S1-review-scope"))
        workspace = os.path.join(case, "workspace")
        run_dir = os.path.join(case, "run")
        seeded = testlib.load_json(os.path.join(case, "input.json"))
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "e17-one-run",
                              "run_dir": run_dir, "run_date": "2026-10-24", "harness": None,
                              "sessions": seeded["sessions"]},
               "workspace": workspace,
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": True, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(case, "in.json"), doc)
        env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        for args in (["check-input", path], ["scope", "--run-dir", run_dir],
                     ["request", "--run-dir", run_dir]):
            code, out, err = testlib.signoff(args, env=env)
            if code != 0:
                testlib.rmtree(cls.dir)
                raise AssertionError("%s exited %d: %s %s" % (args[0], code, out, err))
        cls.mandate = testlib.read_text(os.path.join(run_dir, "readers", "mandate.md"))

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def test_the_session_runs_the_full_suite_once_and_the_reviewer_does_not(self):
        self.assertIn(ONE_FULL_RUN, flat(self.mandate))

    def test_the_reviewer_runs_the_narrowest_command_and_lists_it(self):
        text = flat(self.mandate)
        self.assertIn(NARROWEST, text)
        self.assertIn("List each one under your executed checks.", text)

    def test_a_finding_only_the_full_suite_shows_is_named_not_run(self):
        self.assertIn(SAY_SO, flat(self.mandate))

    def test_the_old_opening_is_gone(self):
        self.assertNotIn(OLD_OPENING, flat(self.mandate))

    def test_the_rule_sits_in_the_read_only_section_and_the_rest_of_it_is_unchanged(self):
        body = flat(section(self.mandate, "Read-only"))
        self.assertTrue(body.strip().startswith("Read anything; never mutate shared state."),
                        body[:120])
        for rule in (ONE_FULL_RUN, NARROWEST, SAY_SO, UNCHANGED_READ_ONLY):
            self.assertIn(rule, body)

    def test_the_finding_shape_still_asks_for_every_executed_check(self):
        self.assertIn("List every check you executed with its command, its exit code and its "
                      "output.", flat(section(self.mandate, "The finding shape")))


class TheSkillAndTheContractSayTheSame(unittest.TestCase):
    """SKILL.md Step 3.5 and the contract carry the rule the mandate gives the reviewers."""

    def test_skill_step_3_5_says_the_one_full_run_is_the_sessions(self):
        text = testlib.read_text(os.path.join(SKILL_ROOT, "SKILL.md"))
        step = flat(text[text.index("## Step 3.5"):text.index("## Step 4")])
        self.assertIn("Run the project's full test command once per review", step)
        self.assertIn("this is the only full run in the review: the reviewers do not run it",
                      step)

    def test_the_contract_says_it_beside_the_request_bullets_and_in_the_phase_table(self):
        text = testlib.read_text(os.path.join(SKILL_ROOT, "references", "signoff-contract.md"))
        independence = flat(section(text, "5. Independence"))
        self.assertIn("The reviewing session runs the project's full test command once per "
                      "review, and that is the only full run in the review", independence)
        rows = [line for line in text.splitlines()
                if line.startswith("| `request` |") and "readers/mandate.md" in line]
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertIn("the session's one full test run", row)


if __name__ == "__main__":
    unittest.main()
