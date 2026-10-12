"""The E15 punch list, item 2 (the E15 lane contract A27 (3) and A34 (2)): the one-line `Footprint:`.

Every real plan, and the build-doc form blueprint-v2 renders, writes a slice's footprint on the label's own line
(`Footprint: <files expected to change>`). This core read only the bulleted form under a bare `Footprint:` label, so
a one-line footprint read as no path at all and every edited path of a real build was listed out of scope.

The rule these tests fix (build-contract section 6, "The footprint's two forms"): `Footprint: <value>` on one line
names the slice's paths, split as ship-v2 splits it (commas outside backtick spans separate; an entry holding
backtick spans names the spans' contents; any other entry names its text, trimmed); the bulleted form under a bare
`Footprint:` reads as it always did; a slice holding both is read by its one-line form, wherever the two stand; a
slice's first one-line `Footprint:` is its footprint. Only `Footprint:` gains the one-line form.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from build_core import doc as docmod, scope  # noqa: E402

D = "\u2014"        # the dash of the build-doc form, carried as an escape
TEMPLATE_SLICE = """# Widget %(D)s build plan (2026-09-22)

Intent: count turns for the owner's bench tests.
Constraints: Python 3.9 standard library; `python3 -m unittest`.
Out of scope: a web view %(D)s declined in the scope doc

## Slice A %(D)s Count turns
Goal: `spin()` returns the number of turns.
Requirements:
- R1 %(D)s `spin()` returns an int
Acceptance criteria:
- AC1: `spin()` returns 3 after three calls %(D)s verify: new test at tests/test_widget.py
Footprint: src/widget.py, tests/test_widget.py
Not in this slice: the reset
Depends on: nothing
Status: not started

## Build assumptions
## Deviations
## Discovered
## Handoffs
## Punch list
""" % {"D": D}

ONE_LINE = testlib.BUILD_DOC.replace("Footprint:\n- src/widget.py\n", "Footprint: src/widget.py, tests/test_widget.py\n")


def slice_with(*lines):
    return "## Slice A %s Count turns\n%s\nStatus: not started\n" % (D, "\n".join(lines))


def source_of(*paths):
    return {"base": "base", "committed": [], "changed": list(paths), "untracked": [], "base_commit": "0" * 40,
            "head": "0" * 40, "excluded": []}


class TheOneLineFootprint(unittest.TestCase):

    def named(self, text, name="A"):
        return docmod.named_paths(docmod.find_slice(text, name))

    def test_the_templates_own_line_reads_as_its_two_paths(self):
        self.assertEqual(self.named(TEMPLATE_SLICE), ["src/widget.py", "tests/test_widget.py"])

    def test_an_edit_inside_them_is_in_scope_and_one_outside_is_listed(self):
        named = self.named(TEMPLATE_SLICE)
        inside = scope.out_of_scope(source_of("src/widget.py", "tests/test_widget.py"), named, {})
        self.assertEqual(inside, [])
        rows = scope.out_of_scope(source_of("src/widget.py", "src/other.py"), named, {"src/other.py": "a reason"})
        self.assertEqual([row["path"] for row in rows], ["src/other.py"])
        self.assertTrue(rows[0]["reason_given"])

    def test_the_value_is_split_as_ship_v2_splits_it(self):
        cases = [("Footprint: src/a.py", ["src/a.py"]),
                 ("Footprint: src/a.py, tests/", ["src/a.py", "tests/"]),
                 ("Footprint:   src/a.py ,tests/b.py  ", ["src/a.py", "tests/b.py"]),
                 ("Footprint:src/a.py", ["src/a.py"]),
                 ("Footprint: `src/a.py`, `tests/`", ["src/a.py", "tests/"]),
                 ("Footprint: `src/a.py` (the counter), the tests under `tests/`", ["src/a.py", "tests/"]),
                 ("Footprint: `src/a,b.py`, c.py", ["src/a,b.py", "c.py"]),
                 ("Footprint: `src/a.py` and `src/b.py`", ["src/a.py", "src/b.py"]),
                 ("Footprint: src/a.py, src/a.py, ,", ["src/a.py"]),
                 ("Footprint: src/my file.py", ["src/my file.py"])]
        for line, want in cases:
            self.assertEqual(self.named(slice_with(line)), want, line)

    def test_a_directory_named_on_one_line_holds_what_sits_under_it(self):
        named = self.named(slice_with("Footprint: `src/turnstile.py`, `tests/`"))
        self.assertTrue(docmod.in_named_paths("tests/test_turnstile.py", named))
        self.assertTrue(docmod.in_named_paths("./src/turnstile.py", named))
        self.assertFalse(docmod.in_named_paths("src/turnstile.pyc", named))

    def test_the_bulleted_form_reads_as_it_always_did(self):
        self.assertEqual(self.named(testlib.BUILD_DOC), ["src/widget.py"])
        self.assertEqual(self.named(slice_with("Footprint:", "- src/a.py", "* src/b.py", "", "- src/c.py")),
                         ["src/a.py", "src/b.py", "src/c.py"])
        self.assertEqual(self.named(slice_with("Footprint:   ", "- src/a.py")), ["src/a.py"])
        self.assertEqual(self.named(slice_with("Goal: no footprint at all")), [])

    def test_a_slice_holding_both_forms_is_read_by_its_one_line_form(self):
        after = slice_with("Footprint:", "- src/listed.py", "", "Footprint: src/one.py, src/two.py")
        before = slice_with("Footprint: src/one.py, src/two.py", "", "Footprint:", "- src/listed.py")
        for text in (after, before):
            self.assertEqual(self.named(text), ["src/one.py", "src/two.py"], text)
            rows = scope.out_of_scope(source_of("src/one.py", "src/listed.py"), self.named(text), {})
            self.assertEqual([row["path"] for row in rows], ["src/listed.py"], text)

    def test_a_slices_first_one_line_footprint_is_its_footprint(self):
        text = slice_with("Footprint: src/first.py", "Footprint: src/second.py")
        self.assertEqual(self.named(text), ["src/first.py"])

    def test_lines_under_a_one_line_footprint_are_not_its_entries(self):
        self.assertEqual(self.named(slice_with("Footprint: src/a.py", "- src/b.py")), ["src/a.py"])

    def test_a_one_line_footprint_belongs_to_its_own_slice(self):
        text = (slice_with("Footprint: src/a.py") + "\n## Slice B %s Reset\nFootprint: src/b.py\nStatus: not started\n" % D
                + "\n## Punch list\nFootprint: src/never.py\n")
        self.assertEqual(self.named(text, "A"), ["src/a.py"])
        self.assertEqual(self.named(text, "B"), ["src/b.py"])

    def test_only_footprint_gains_the_one_line_form(self):
        entry = docmod.find_slice(slice_with("Requirements: one thing", "Checks: unit: sh checks/unit.sh",
                                             "Not in this slice: src/other.py", "Depends on: nothing",
                                             "Footprint notes: src/never.py", "The Footprint: src/never.py",
                                             "footprint: src/never.py", " Footprint: src/never.py"), "A")
        self.assertEqual(docmod.requirements(entry), [])
        self.assertEqual(docmod.checks(entry), [])
        self.assertEqual(docmod.not_in_slice(entry), [])
        self.assertEqual(docmod.named_paths(entry), [])
        self.assertEqual(entry["status"], "not started")

    def test_a_one_line_footprint_ends_the_list_above_it_as_any_paragraph_line_does(self):
        entry = docmod.find_slice(slice_with("Not in this slice:", "- src/other.py", "Footprint: src/a.py",
                                             "- src/not-a-boundary.py"), "A")
        self.assertEqual(docmod.not_in_slice(entry), ["src/other.py"])
        self.assertEqual(docmod.named_paths(entry), ["src/a.py"])

    def test_the_card_line_is_still_set_and_nothing_else(self):
        entry = docmod.find_slice(TEMPLATE_SLICE, "A")
        after = docmod.set_status(TEMPLATE_SLICE, entry, "built")
        self.assertEqual(after, TEMPLATE_SLICE.replace("Status: not started", "Status: built"))


class ThroughTheCli(unittest.TestCase):
    """The same rule through every phase: `contract` writes the two paths, and `report` lists nothing for an edit
    inside them and the one path for an edit outside."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-footprint-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch, doc=ONE_LINE)
        self.run_dir = os.path.join(self.scratch, "run")

    def run_all(self, answer=None):
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.ws))
        answer_path = os.path.join(self.scratch, "answer.json")
        testlib.write_json(answer_path, answer or testlib.ANSWER)
        last = None
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", answer_path],
                     ["report", "--run-dir", self.run_dir]):
            last = testlib.run_build(args)
            if last[0] != 0:
                break
        result_path = os.path.join(self.run_dir, "result.json")
        return last, (testlib.load_json(result_path) if os.path.isfile(result_path) else None)

    def test_an_edit_inside_the_one_line_footprint_is_not_out_of_scope(self):
        self.assertNotEqual(ONE_LINE, testlib.BUILD_DOC)
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.write_text(os.path.join(self.ws, "tests", "test_widget.py"), "import widget\n")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["edits"].append({"path": "tests/test_widget.py", "reason": "R1"})
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["out_of_scope"], [])
        contract = testlib.load_json(os.path.join(self.run_dir, "contract.json"))
        self.assertEqual(contract["named_paths"], ["src/widget.py", "tests/test_widget.py"])

    def test_an_edit_outside_it_is_the_one_path_listed(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 9\n")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["edits"].append({"path": "src/other.py", "reason": "the neighbouring module was adjusted"})
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual([row["path"] for row in result["out_of_scope"]], ["src/other.py"])
        self.assertTrue(result["out_of_scope"][0]["named_in_not_in_slice"])


if __name__ == "__main__":
    unittest.main()
