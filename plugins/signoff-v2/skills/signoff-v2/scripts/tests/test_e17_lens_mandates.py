"""E17 fix round 1, slice B: one lens per reviewer.

The E17 canary's five DEEP lenses got byte-identical mandates, each listing all five lenses, so
the run paid for five full reviews instead of one review split five ways (canary finding C-7).
`request` now writes one mandate per lens at `readers/mandate-<lens>.md`, beside the unchanged
`readers/mandate.md`. In each, the lens section carries only its own lens's line from the one lens
table, one sentence names the review's other lenses as covered by sibling reviewers, and every
other section is the same as `readers/mandate.md`'s, Slice A's suite rule included. LIGHT's one
fused lens writes no per-lens file, and its `request.json` carries an empty map.
"""
import os
import re
import unittest

import testlib

# The plan's words for each lens, one line per lens name (slice B, requirement 1).
TABLE = {
    "spec": ("does the built thing match the doc? Silently skipped requirements, quietly "
             "narrowed scope, stubs presented as finished. Walk the slice's acceptance criteria "
             "one by one and check files changed outside its Footprint."),
    "correctness": ("bugs, unhandled edge cases, error paths that swallow failures, state that "
                    "can desync."),
    "seams": ("integration with what already shipped. Regressions in prior slices, broken "
              "assumptions at the boundary, migrations that do not run twice."),
    "security": "authz, injection, secrets, trust boundaries.",
    "tests": "do the tests assert real behavior, or do they pass vacuously?",
    "accessibility": "screen-reader and keyboard paths, contrast, focus order, labels.",
    "data-safety": "migrations, backups, destructive writes, data at rest.",
}
SEVEN = ["spec", "correctness", "seams", "security", "accessibility", "data-safety", "tests"]
FIVE = ["spec", "correctness", "seams", "security", "tests"]

SHEET = """# REVIEW.md

## Passes
- correctness: on
- security: on
- accessibility: off (CLI, no UI)
- data-safety: off (no data store)

## Severity bar
- MAJOR: a failing check that CI would catch

## Repo-specific checks
- (none yet)
"""

ONE_FULL_RUN = ("The reviewing session runs the repository's full test command once for this "
                "review; you do not run the full suite or any long-running sweep yourself.")
LENS_HEADING = "Lens"
MANDATE_LENS_HEADING = "Lenses"


def flat(text):
    return re.sub(r"\s+", " ", text)


def sections(text):
    """[(heading or None for the preamble, body)] for every `## ` section, in order."""
    out, heading, body = [], None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            out.append((heading, "\n".join(body)))
            heading, body = line[3:].strip(), []
            continue
        body.append(line)
    out.append((heading, "\n".join(body)))
    return out


def lens_names_in(text):
    """The lens names a text names in backticks, in order."""
    return [name for name in re.findall(r"`([a-z][a-z0-9-]*)`", text) if name in TABLE]


def drive(case_dir, depth, sheet=None, run_id="e17-lens"):
    """check-input, scope and request on a seeded case: (run dir, request.json)."""
    workspace = os.path.join(case_dir, "workspace")
    run_dir = os.path.join(case_dir, "run")
    if sheet is not None:
        with open(os.path.join(workspace, "REVIEW.md"), "w", encoding="utf-8") as fh:
            fh.write(sheet)
    seeded = testlib.load_json(os.path.join(case_dir, "input.json"))
    doc = {"protocol_version": 1,
           "invocation": {"mode": "headless", "caller": "test", "run_id": run_id,
                          "run_dir": run_dir, "run_date": "2026-10-24", "harness": None,
                          "sessions": seeded["sessions"]},
           "workspace": workspace,
           "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                      "base": seeded["base"]},
           "report_only": True, "review": {"depth": depth, "route": "test"}}
    path = testlib.write_json(os.path.join(case_dir, "in.json"), doc)
    env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
    for args in (["check-input", path], ["scope", "--run-dir", run_dir],
                 ["request", "--run-dir", run_dir]):
        code, out, err = testlib.signoff(args, env=env)
        if code != 0:
            raise AssertionError("%s exited %d: %s %s" % (args[0], code, out, err))
    return run_dir, testlib.load_json(os.path.join(run_dir, "request.json"))


class Runs(object):
    """The three runs every test reads, built once."""

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("signoff-e17-lens-")
        try:
            cls.runs = {}
            for label, depth, sheet in (("deep-sheet", "DEEP", SHEET), ("deep", "DEEP", None),
                                        ("light", "LIGHT", None)):
                case = testlib.build_case("S1-review-scope", "S1-01-clean",
                                          os.path.join(cls.dir, label))
                cls.runs[label] = drive(case, depth, sheet, run_id="e17-lens-" + label)
        except Exception:
            testlib.rmtree(cls.dir)
            raise

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def mandates(self, label):
        run_dir, request = self.runs[label]
        return {lens: testlib.read_text(path)
                for lens, path in request["lens_mandates"].items()}

    def base_mandate(self, label):
        return testlib.read_text(os.path.join(self.runs[label][0], "readers", "mandate.md"))


class DeepWritesOneMandatePerLens(Runs, unittest.TestCase):
    def test_a_sheet_that_turns_two_passes_off_gives_five_lens_mandates(self):
        run_dir, request = self.runs["deep-sheet"]
        readers = os.path.join(run_dir, "readers")
        self.assertEqual(sorted(request["lens_mandates"]), sorted(FIVE))
        for lens, path in request["lens_mandates"].items():
            self.assertEqual(path, os.path.join(readers, "mandate-%s.md" % lens))
            self.assertTrue(os.path.isfile(path), path)
        on_disk = sorted(name for name in os.listdir(readers)
                         if name.startswith("mandate-") and name.endswith(".md"))
        self.assertEqual(on_disk, sorted("mandate-%s.md" % lens for lens in FIVE))

    def test_with_no_sheet_deep_gives_seven(self):
        run_dir, request = self.runs["deep"]
        self.assertEqual(sorted(request["lens_mandates"]), sorted(SEVEN))
        for lens in SEVEN:
            self.assertTrue(os.path.isfile(os.path.join(run_dir, "readers",
                                                        "mandate-%s.md" % lens)))

    def test_the_request_still_names_the_shared_mandate(self):
        for label in ("deep-sheet", "deep", "light"):
            run_dir, request = self.runs[label]
            self.assertEqual(request["mandate"], os.path.join(run_dir, "readers", "mandate.md"))


class EachLensSectionNamesOnlyItsOwnLens(Runs, unittest.TestCase):
    def lens_section(self, text):
        found = [body for heading, body in sections(text) if heading == LENS_HEADING]
        self.assertEqual(len(found), 1, "one lens section")
        self.assertNotIn(MANDATE_LENS_HEADING, [h for h, _ in sections(text)])
        return found[0]

    def test_the_lens_sections_differ_pairwise(self):
        for label in ("deep-sheet", "deep"):
            bodies = [self.lens_section(text) for text in self.mandates(label).values()]
            self.assertEqual(len(set(bodies)), len(bodies), label)

    def test_the_table_line_is_the_lens_own_in_the_plans_words(self):
        for label in ("deep-sheet", "deep"):
            for lens, text in self.mandates(label).items():
                body = self.lens_section(text)
                lines = [line for line in body.split("\n") if line.startswith("- ")]
                self.assertEqual(lines, ["- `%s`: %s" % (lens, TABLE[lens])], (label, lens))

    def test_only_the_sibling_sentence_names_another_lens(self):
        for label, lenses in (("deep-sheet", FIVE), ("deep", SEVEN)):
            for lens, text in self.mandates(label).items():
                body = self.lens_section(text)
                others = [name for name in lenses if name != lens]
                sibling = [s for s in re.split(r"(?<=[.?])\s+", flat(body).strip())
                           if "sibling reviewers" in s]
                self.assertEqual(len(sibling), 1, (label, lens, body))
                self.assertEqual(lens_names_in(sibling[0]), others, (label, lens))
                rest = flat(body).replace(sibling[0], "")
                self.assertEqual(set(lens_names_in(rest)), {lens}, (label, lens, rest))

    def test_outside_the_lens_it_reports_what_it_finds_and_does_not_go_looking(self):
        for lens, text in self.mandates("deep-sheet").items():
            body = flat(self.lens_section(text))
            self.assertIn("You still report anything you find outside your lens; you do not "
                          "go looking there.", body, lens)


class EveryOtherSectionIsTheSharedMandates(Runs, unittest.TestCase):
    def test_every_section_but_the_lens_section_equals_mandate_md(self):
        for label in ("deep-sheet", "deep"):
            shared = [(h, b) for h, b in sections(self.base_mandate(label))
                      if h != MANDATE_LENS_HEADING]
            self.assertEqual([h for h, _ in shared],
                             [None, "What you are reviewing", "What is NOT evidence",
                              "The finding shape", "Read-only",
                              shared[-1][0]], "the shared mandate's section order")
            for lens, text in self.mandates(label).items():
                own = [(h, b) for h, b in sections(text) if h != LENS_HEADING]
                self.assertEqual(own, shared, (label, lens))

    def test_slice_as_suite_rule_and_the_sheet_reach_every_lens(self):
        for lens, text in self.mandates("deep-sheet").items():
            self.assertIn(ONE_FULL_RUN, flat(text), lens)
            self.assertIn("MAJOR: a failing check that CI would catch", text, lens)

    def test_the_shared_mandate_still_lists_the_whole_lens_set(self):
        body = [b for h, b in sections(self.base_mandate("deep-sheet"))
                if h == MANDATE_LENS_HEADING][0]
        self.assertEqual([line for line in body.split("\n") if line.startswith("- ")],
                         ["- %s" % lens for lens in FIVE])


class LightKeepsTheSharedMandate(Runs, unittest.TestCase):
    def test_light_writes_no_lens_mandate_and_an_empty_map(self):
        run_dir, request = self.runs["light"]
        self.assertEqual(request["lens_mandates"], {})
        readers = os.path.join(run_dir, "readers")
        self.assertEqual([name for name in os.listdir(readers) if name.startswith("mandate-")],
                         [])
        self.assertIn("- spec + correctness", self.base_mandate("light"))


if __name__ == "__main__":
    unittest.main()
