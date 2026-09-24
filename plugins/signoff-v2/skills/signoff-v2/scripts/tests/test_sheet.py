"""The repo's inspection sheet, `REVIEW.md`, read exactly as v1 signoff reads it.

v1 Step 1's sheet test is mechanical, so it is a script's job rather than prose: a file is the
sheet only when it carries the template's three headings (`## Passes`, `## Severity bar`,
`## Repo-specific checks`) AND every `## Passes` line reads `- <name>: on` or `- <name>: off`
with an optional parenthetical. Anything else under that name — a human review guide, a sheet
missing a heading, a pass with no on/off — is NOT the sheet: the run uses the defaults and says
`present but not the kit sheet`.

A pass name outside the four the template carries (`correctness`, `security`, `accessibility`,
`data-safety`) is reported as unknown and ignored. A pass marked `off` never runs, even at DEEP,
and the verdict names the skip with its reason. `spec` and `seams` are the loop's own and are
not passes: nothing in `REVIEW.md` turns them off.

Pick P5 keeps every one of those rules word for word. This suite is the proof they did not move.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import sheet  # noqa: E402

TEMPLATE = """# REVIEW.md
<!-- verified: 2026-09-21 -->

## Passes
- correctness: on
- security: on
- accessibility: off (CLI, no UI)
- data-safety: on (hosted database; migrations must ship with a backup)

## Severity bar
- BLOCKER: data loss, auth bypass, a gate in AGENTS.md violated, a migration without a backup
- MAJOR: a user-visible regression, a failing check that CI would catch
- MINOR: everything else worth a line

## Repo-specific checks
- the joiner escapes the separator (found 2026-09-19, again 2026-09-21)
"""


class TheSheetTest(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("signoff-sheet-")
        self.addCleanup(testlib.rmtree, self.dir)

    def write(self, text, name="REVIEW.md"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return self.dir

    def test_the_kit_template_is_the_sheet(self):
        got = sheet.read(self.write(TEMPLATE))
        self.assertTrue(got["is_sheet"])
        self.assertEqual(got["state"], "read")
        self.assertEqual(got["passes"], {"correctness": True, "security": True,
                                         "accessibility": False, "data-safety": True})
        self.assertEqual(got["skipped"], ["accessibility"])
        self.assertEqual(got["skip_reasons"], {"accessibility": "CLI, no UI"})
        self.assertEqual(len(got["bar"]), 3)
        self.assertEqual(len(got["repo_checks"]), 1)

    def test_no_file_at_all_is_absent_and_the_defaults_apply(self):
        got = sheet.read(self.dir)
        self.assertFalse(got["is_sheet"])
        self.assertEqual(got["state"], "absent")
        self.assertEqual(got["passes"], sheet.DEFAULT_PASSES)

    def test_a_file_missing_a_heading_is_not_the_sheet(self):
        text = TEMPLATE.replace("## Repo-specific checks\n", "")
        got = sheet.read(self.write(text))
        self.assertFalse(got["is_sheet"])
        self.assertEqual(got["state"], "present but not the kit sheet")
        self.assertEqual(got["passes"], sheet.DEFAULT_PASSES)

    def test_a_pass_with_no_on_or_off_makes_it_not_the_sheet(self):
        text = TEMPLATE.replace("- correctness: on", "- correctness: as appropriate")
        got = sheet.read(self.write(text))
        self.assertFalse(got["is_sheet"])
        self.assertEqual(got["state"], "present but not the kit sheet")

    def test_a_human_review_guide_under_that_name_is_not_the_sheet(self):
        got = sheet.read(self.write("# How we review here\n\nBe nice. Read the diff twice.\n"))
        self.assertFalse(got["is_sheet"])
        self.assertEqual(got["state"], "present but not the kit sheet")

    def test_a_pass_outside_the_four_is_reported_as_unknown_and_ignored(self):
        text = TEMPLATE.replace("- security: on", "- security: on\n- vibes: on")
        got = sheet.read(self.write(text))
        self.assertTrue(got["is_sheet"])
        self.assertEqual(got["unknown_passes"], ["vibes"])
        self.assertNotIn("vibes", got["passes"])


class TheLensesTheSheetChooses(unittest.TestCase):
    """`spec` and `seams` are the loop's own; nothing in the sheet turns them off."""

    def test_an_off_pass_is_not_a_lens_at_any_depth(self):
        passes = {"correctness": True, "security": True, "accessibility": False,
                  "data-safety": True}
        for depth in ("LIGHT", "LEAN", "DEEP"):
            lenses = sheet.lenses_for(depth, passes)
            self.assertNotIn("accessibility", lenses, depth)
            self.assertIn("spec", " ".join(lenses), depth)

    def test_deep_adds_security_and_tests_when_security_is_on(self):
        lenses = sheet.lenses_for("DEEP", {"correctness": True, "security": True})
        self.assertIn("security", lenses)
        self.assertIn("tests", lenses)

    def test_security_off_drops_it_even_at_deep(self):
        lenses = sheet.lenses_for("DEEP", {"correctness": True, "security": False})
        self.assertNotIn("security", lenses)

    def test_light_is_one_fused_reviewer(self):
        lenses = sheet.lenses_for("LIGHT", sheet.DEFAULT_PASSES)
        self.assertEqual(len(lenses), 1)
        self.assertIn("spec", lenses[0])
        self.assertIn("correctness", lenses[0])

    def test_a_pass_that_is_on_and_is_a_lens_of_its_own_runs_at_lean(self):
        lenses = sheet.lenses_for("LEAN", {"correctness": True, "data-safety": True})
        self.assertIn("data-safety", lenses)
        for loop_lens in ("spec", "seams"):
            self.assertIn(loop_lens, lenses)


class TheRunReportsWhatTheSheetSaid(unittest.TestCase):
    """The sheet's state and its skips reach the result, where the user reads them."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-sheet-run-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case("S1-review-scope", "S1-01-clean",
                                       os.path.join(self.dir, "S1-review-scope"))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")

    def drive(self):
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "sheet-run",
                              "run_dir": self.run_dir, "run_date": "2026-09-21", "harness": None,
                              "sessions": seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": True, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(self.case, "in.json"), doc)
        env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        out = None
        for args in (["check-input", path], ["scope", "--run-dir", self.run_dir],
                     ["request", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer",
                      os.path.join(self.case, "answer.json")],
                     ["record", "--run-dir", self.run_dir]):
            code, out, err = testlib.signoff(args, env=env)
            self.assertIn(code, (0, 10), err)
        return testlib.load_json(os.path.join(self.run_dir, "result.json"))

    def test_with_no_sheet_the_result_says_absent_and_carries_the_defaults(self):
        result = self.drive()
        self.assertEqual(result["review_sheet"]["state"], "absent")
        self.assertFalse(result["review_sheet"]["is_sheet"])
        self.assertEqual(result["review_sheet"]["skipped"], [])

    def test_with_a_sheet_the_result_names_the_skips_and_the_repo_checks(self):
        with open(os.path.join(self.workspace, "REVIEW.md"), "w", encoding="utf-8") as fh:
            fh.write(TEMPLATE)
        result = self.drive()
        self.assertEqual(result["review_sheet"]["state"], "read")
        self.assertEqual(result["review_sheet"]["skipped"], ["accessibility"])
        self.assertEqual(result["review_sheet"]["repo_checks"],
                         ["the joiner escapes the separator (found 2026-09-19, again 2026-09-21)"])
        self.assertIn("accessibility", testlib.read_text(
            os.path.join(self.run_dir, "chat.md")))

    def test_the_sheet_travels_to_the_reviewer_and_is_never_a_withheld_claim(self):
        """v1: the sheet's passes, bar and checks are the repo's standing sheet, not the
        author's rationale, so the reviewer gets them."""
        with open(os.path.join(self.workspace, "REVIEW.md"), "w", encoding="utf-8") as fh:
            fh.write(TEMPLATE)
        self.drive()
        mandate = testlib.read_text(os.path.join(self.run_dir, "readers", "mandate.md"))
        self.assertIn("the joiner escapes the separator", mandate)
        self.assertIn("BLOCKER: data loss", mandate)


if __name__ == "__main__":
    unittest.main()
