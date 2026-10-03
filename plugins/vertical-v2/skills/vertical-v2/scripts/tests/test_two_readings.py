"""Two readings (the E15 lane contract A13; contract section 5, "Two readings").

vertical-v2 reads the build doc twice: once by its line rules (A8 to A12, `fences.py`, `spec.py`) and once by a
pinned CommonMark reader (`vertical_core/commonmark.py` over the vendored `markdown-it-py`), whose heading names and
label lines come from the rendered text (character references decoded, inline markup removed, whitespace runs
collapsed). Any decision the station takes from the doc that the two readings take differently (the slices, by name
and heading line; each slice's card; the recorded base; the withheld sections, by name, first and last line) stops
the run `doc-unreadable` naming the first line where they differ, before any ask, request or packet; so does a
builder's-notes declaration of any other Markdown file of the reviewed commit that the two readings decide
differently. A doc both readings take the same way runs as before.

`FAMILIES` are the five families the outside reviewer's look 3b and the control room found (A13): a Setext heading,
character references, inline markup in a heading, extra spaces in a slice heading, and an escaped, bold or
character-coded `Base:` line. `TheGate` drives each through the real CLI, records off and on; `TheNotes` drives a
character-coded notes heading through the CLI; `TheReadings` drives the two readings directly; `TheEqualDecisions`
holds that markup which leaves every decision equal still runs.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, spec  # noqa: E402

D = vlib.D
SLICE_B = "## Slice B %s the spinner" % D
SHA = "1111111"


def two_slices(tail_b, header=(), slice_b=SLICE_B):
    """Slice A `signed off`, then (unless `slice_b` is None) slice B's heading and its first lines, then `tail_b`;
    `header` lines go after the header paragraph. Every doc ends with the ledger's `## Punch list`."""
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "", "Intent: a counter.", "Out of scope: a dashboard"]
    lines += list(header)
    lines += ["", "## Slice A %s the counter" % D, "Goal: count.", "Depends on: nothing", "Status: signed off", ""]
    if slice_b is not None:
        lines += [slice_b, "Goal: spin.", "Depends on: A"]
    lines += list(tail_b)
    lines += ["", "## Punch list", "- PUNCH-MARKER", ""]
    return "\n".join(lines)


def number_of(text, line):
    return text.split("\n").index(line) + 1


# (what, the doc, the text of the first line where the readings differ, the decision that differs)
FAMILIES = [
    # (1) a Setext heading
    ("a Setext slice heading in the header hides a slice (its Status: line is header text to the line rules)",
     two_slices(["Status: signed off"], header=["", "Slice Z %s the encoder" % D, "---", "Goal: encode.", "",
                                               "Status: built"]),
     "Slice Z %s the encoder" % D, "slices"),
    ("a Setext slice heading after the last slice hides a slice with no label",
     two_slices(["Status: signed off", "", "Slice C %s the encoder" % D, "---", "Goal: encode."]),
     "Slice C %s the encoder" % D, "slices"),
    ("a Setext Punch list hides a withheld section",
     two_slices(["Status: signed off", "", "Punch list", "---", "- LEAK-MARKER the double tap"]),
     "Punch list", "withheld"),
    ("a Setext Handoffs heading at level 1 hides a withheld section",
     two_slices(["Status: signed off", "", "Handoffs", "========", "- LEAK-MARKER skim slice B"]),
     "Handoffs", "withheld"),
    # (2) character references
    ("a character-coded dash hides a slice",
     two_slices(["Status: built"], slice_b="## Slice B &#8212; the spinner"), "## Slice B &#8212; the spinner",
     "slices"),
    ("a named character reference for the dash hides a slice",
     two_slices(["Status: built"], slice_b="## Slice B &mdash; the spinner"), "## Slice B &mdash; the spinner",
     "slices"),
    ("a character-coded space hides a withheld section",
     two_slices(["Status: signed off", "", "## Punch&#32;list", "- LEAK-MARKER the double tap"]), "## Punch&#32;list",
     "withheld"),
    ("a character-coded colon makes a second label",
     two_slices(["Status&#58; built", "", "Status: signed off"]), "Status&#58; built", "card"),
    ("a character-coded colon is a slice's only rendered label",
     two_slices(["Status&#x3A; signed off"]), "Status&#x3A; signed off", "card"),
    ("a character-coded colon hides a base", two_slices(["Status: signed off"], header=["", "Base&#58; " + SHA]),
     "Base&#58; " + SHA, "base"),
    # (3) inline markup in a heading
    ("bold markup hides a withheld section",
     two_slices(["Status: signed off", "", "## **Punch list**", "- LEAK-MARKER the double tap"]), "## **Punch list**",
     "withheld"),
    ("a code span hides a withheld section",
     two_slices(["Status: signed off", "", "## `Deviations`", "- LEAK-MARKER skipped the retry"]), "## `Deviations`",
     "withheld"),
    ("emphasis inside a slice heading's name hides a slice",
     two_slices(["Status: built"], slice_b="## Slice *B* %s the spinner" % D), "## Slice *B* %s the spinner" % D,
     "slices"),
    ("an inline comment inside a withheld heading hides it",
     two_slices(["Status: signed off", "", "## Punch <!-- x --> list", "- LEAK-MARKER the double tap"]),
     "## Punch <!-- x --> list", "withheld"),
    # (4) extra spaces in a slice heading
    ("two spaces inside a slice heading hide a slice",
     two_slices(["Status: built"], slice_b="## Slice  B %s the spinner" % D), "## Slice  B %s the spinner" % D,
     "slices"),
    ("two spaces before the dash hide a slice",
     two_slices(["Status: built"], slice_b="## Slice B  %s the spinner" % D), "## Slice B  %s the spinner" % D,
     "slices"),
    ("a no-break space inside a slice heading hides a slice",
     two_slices(["Status: built"], slice_b="## Slice B %s the spinner" % D), "## Slice B %s the spinner" % D,
     "slices"),
    # (5) a Base: line the line rules ignore
    ("an escaped colon hides a base", two_slices(["Status: signed off"], header=["", "Base\\: " + SHA]),
     "Base\\: " + SHA, "base"),
    ("a bold label hides a base", two_slices(["Status: signed off"], header=["", "**Base:** " + SHA]),
     "**Base:** " + SHA, "base"),
    ("a code span label hides a base", two_slices(["Status: signed off"], header=["", "`Base:` " + SHA]),
     "`Base:` " + SHA, "base"),
]

# markup that leaves every decision equal: (what, the doc, the slices' Status: lines)
EQUAL = [
    ("a slice's short title with a code span and bold",
     vlib.build_doc().replace("## Slice B %s the spinner" % D, "## Slice B %s the `spinner` **loop**" % D),
     ["signed off", "signed off"]),
    ("a heading with bold and a code span that is no slice and no withheld section",
     vlib.build_doc().replace("## Build assumptions\n", "## **Notes** on `spin()`\n\nthe bench is quiet.\n\n"
                              "## Build assumptions\n", 1), ["signed off", "signed off"]),
    ("a withheld heading with closing hashes and odd case",
     vlib.build_doc().replace("## Deviations\n", "## DEVIATIONS ##\n", 1), ["signed off", "signed off"]),
    ("a slice heading with closing hashes",
     vlib.build_doc().replace("## Slice A %s the counter" % D, "## Slice A %s the counter ##" % D, 1),
     ["signed off", "signed off"]),
    ("a character reference and emphasis in body text",
     vlib.build_doc().replace("Goal: one sentence about the spinner.",
                              "Goal: one sentence about the *spinner* &amp; its `twice()`.", 1),
     ["signed off", "signed off"]),
    ("a slice label that ends a lazy list item, as the build-doc form writes it", vlib.build_doc(),
     ["signed off", "signed off"]),
]


def readings():
    """The new module, imported where a test needs it (a missing module fails the test, never the file)."""
    from vertical_core import readings as mod  # noqa: E402
    return mod


class TheReadings(unittest.TestCase):
    """The two readings driven directly: every family is accepted by the line rules alone, and the agreement check
    names the first line where they differ and the decision."""

    def test_every_family_passes_the_line_rules_alone(self):
        """The families are what A8 to A12 let through: the line rules find no problem in any of them."""
        for what, doc, first, decision in FAMILIES:
            self.assertEqual(fences.read(doc).problems, [], what)

    def test_every_family_stops_each_reader_naming_its_line(self):
        from vertical_core import gate as gatemod  # noqa: E402
        for what, doc, first, decision in FAMILIES:
            with self.subTest(shape=what):
                for reader in (gatemod.slices_of, gatemod.recorded_base, spec.clean):
                    with self.assertRaises(spec.SpecUnreadable, msg=(what, reader.__name__)) as caught:
                        reader(doc)
                    self.assertEqual(caught.exception.line, number_of(doc, first), (what, reader.__name__))

    def test_every_family_names_the_decision_that_differs(self):
        mod = readings()
        for what, doc, first, decision in FAMILIES:
            with self.subTest(shape=what):
                found = mod.difference(doc)
                self.assertIsNotNone(found, what)
                self.assertEqual(found[0], number_of(doc, first), (what, found))
                self.assertIn(mod.DECISIONS[decision], found[1], (what, found))
                self.assertIn("CommonMark", found[1], what)

    def test_equal_decisions_find_no_difference(self):
        mod = readings()
        for what, doc, statuses in EQUAL:
            with self.subTest(shape=what):
                self.assertEqual(fences.read(doc).problems, [], what)
                self.assertIsNone(mod.difference(doc), what)

    def test_the_line_rules_go_first(self):
        """A doc the line rules refuse is refused by them, naming their line, whatever the second reading says."""
        doc = two_slices(["Status: signed off", "", " ## Notes", "", "## Punch&#32;list"])
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(doc)
        self.assertEqual(caught.exception.line, number_of(doc, " ## Notes"))
        self.assertNotIn("the two readings differ", str(caught.exception))

    def test_the_first_line_wins_across_decisions(self):
        """Two differences: the earlier line is named, whichever decision it belongs to."""
        doc = two_slices(["Status: signed off", "", "## **Punch list**", "- LEAK"], header=["", "**Base:** " + SHA])
        found = readings().difference(doc)
        self.assertEqual(found[0], number_of(doc, "**Base:** " + SHA))
        doc = two_slices(["Status: built"], slice_b="## Slice  B %s the spinner" % D,
                         header=["", "Notes", "---", "a Setext heading that is no slice and no withheld section"])
        found = readings().difference(doc)
        self.assertEqual(found[0], number_of(doc, "## Slice  B %s the spinner" % D))

    def test_a_level_1_heading_ends_a_slice_for_the_second_reading(self):
        """The second reading's slice section runs to the next heading of level 1 or 2, as a withheld section does:
        a label after `# Notes` is the slice's to the line rules and no slice's to CommonMark, so the doc stops."""
        doc = two_slices(["", "# Notes", "", "Status: built"])
        self.assertEqual(fences.read(doc).problems, [])
        found = readings().difference(doc)
        self.assertEqual(found[0], number_of(doc, "Status: built"))
        self.assertIn(readings().DECISIONS["card"], found[1])

    def test_a_crlf_doc_and_a_byte_order_mark_read_the_same(self):
        doc = vlib.build_doc()
        self.assertIsNone(readings().difference("﻿" + doc.replace("\n", "\r\n")))
        bad = two_slices(["Status: signed off", "", "## Punch&#32;list", "- LEAK"])
        found = readings().difference("﻿" + bad.replace("\n", "\r\n"))
        self.assertEqual(found[0], number_of(bad, "## Punch&#32;list"))


class TheNotesDeclaration(unittest.TestCase):
    """A Markdown file of the reviewed commit, read twice for its builder's-notes declaration."""

    def test_a_character_coded_declaration_differs_and_names_its_line(self):
        found = readings().notes_difference("# Builder&#32;notes\n\nNOTES-MARKER\n")
        self.assertEqual(found[0], 1)
        self.assertIn("builder's notes", found[1])

    def test_markup_and_a_setext_declaration_differ_or_agree_by_decision(self):
        mod = readings()
        self.assertIsNotNone(mod.notes_difference("# **Builder** notes\n"))
        self.assertIsNotNone(mod.notes_difference("intro\n\n# Build&#x20;notes\n"))
        self.assertIsNone(mod.notes_difference("# Builder notes\n\nbody\n"))
        self.assertIsNone(mod.notes_difference("Build notes\n---\n\nbody\n"))
        self.assertIsNone(mod.notes_difference("# Bench guide\n\n## Builder notes\n"))
        self.assertIsNone(mod.notes_difference("no heading at all\n"))

    def test_a_declaration_only_the_wide_line_reading_finds_is_no_difference_and_the_file_stays_withheld(self):
        """The line reading's first heading is read wide (a fenced heading-shaped line before the first certain
        heading is a candidate); CommonMark's first heading here is `# Intro`, which declares nothing. Since A14
        (C1A8-4) only the leaking direction stops: the wide reading withholds the file, as before A13."""
        from vertical_core import notes  # noqa: E402
        text = "```\n# Builder notes\n```\n\n# Intro\n"
        self.assertIsNone(readings().notes_difference(text))
        self.assertEqual(notes.declaration(text), ("Builder notes", 2))


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every family through the real CLI, records off and on: exit 10, `doc-unreadable` naming the line, `next:
    done`, no `ask.json`, no request file, no `packets`."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vtwo-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records, extra=None, **station):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count,
                                  extra_build_files=extra)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count, **station)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def assert_unreadable(self, what, code, out, err, run_dir, needle):
        self.assertEqual(code, 10, (what, out, err))
        self.assertEqual((out["status"], out["stop_tag"], out.get("next")), ("stopped", "doc-unreadable", "done"),
                         (what, out))
        self.assertIn(needle, out["reason"], what)
        for name in ("ask.json", "requests-local.json", "packets", "scope.json"):
            self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))
        self.assertEqual(vlib.load(run_dir, "checkpoint.json")["phase"], "done")

    def families(self, records):
        for what, doc, first, decision in FAMILIES:
            with self.subTest(shape=what, records=records):
                code, out, err, run_dir = self.gate(doc, records)
                self.assert_unreadable(what, code, out, err, run_dir, "line %d" % number_of(doc, first))

    def test_every_family_stops_the_gate_with_no_records_log(self):
        self.families(False)

    def test_every_family_stops_the_gate_with_a_records_log(self):
        self.families(True)

    def test_the_owners_base_never_clears_a_hidden_base_line(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        for line in ("Base\\: %s" % info0["base"], "**Base:** %s" % info0["base"], "Base&#58; %s" % info0["base"]):
            with self.subTest(line=line):
                doc = vlib.build_doc(extra_header=["", line])
                code, out, err, run_dir = self.gate(doc, False, owner_words={
                    "base": {"commit": info0["base"], "words": "from the first commit"}})
                self.assert_unreadable(line, code, out, err, run_dir, "line %d" % number_of(doc, line))

    def test_equal_decisions_still_pass_the_gate(self):
        for what, doc, statuses in EQUAL:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 0, (what, records, out, err))
                    gate = vlib.load(run_dir, "gate.json")
                    self.assertEqual([s["status_line"] for s in gate["slices"]], statuses, what)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheNotes(unittest.TestCase):
    """A character-coded builder's-notes heading in another Markdown file of the reviewed commit stops the gate,
    records off and on, naming the file and the line; a plainly declared file is still withheld and runs."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vtwo-notes-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, files, records):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, records=records, name="ws-%d" % self.count, extra_build_files=files)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def test_a_character_coded_notes_heading_stops_the_gate(self):
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate({"notes/bench.md": "# Builder&#32;notes\n\nNOTES-MARKER\n"},
                                                    records)
                self.assertEqual(code, 10, (out, err))
                self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), out)
                self.assertIn("notes/bench.md", out["reason"])
                self.assertIn("line 1", out["reason"])
                for name in ("ask.json", "packets", "scope.json"):
                    self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), name)

    def test_a_plainly_declared_notes_file_still_runs(self):
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate({"notes/bench.md": "# Builder notes\n\nNOTES-MARKER\n"}, records)
                self.assertEqual(code, 0, (out, err))


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):
    """The reviewed commit holds a family, the working tree a plain doc, under the owner's committed-state-only
    words: `scope` stops `doc-unreadable` naming the line before any packet; a notes file in the commit the two
    readings decide differently stops there too."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vtwo-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_scope_stops_on_a_family_in_the_commit(self):
        for index, line in enumerate(("## Punch&#32;list", "Punch list\n---", "## **Handoffs**")):
            with self.subTest(shape=line):
                doc = vlib.build_doc().replace("## Build assumptions\n", line + "\n- LEAK\n\n## Build assumptions\n", 1)
                ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=True, name="ws-%d" % index)
                testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
                drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % index,
                                            owner_words={"committed_only": "review the committed state only"})
                self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
                code, out, err = drive(["scope", "--run-dir", run_dir])
                self.assertEqual(code, 10, (out, err))
                self.assertEqual(out["stop_tag"], "doc-unreadable")
                self.assertIn("line %d" % number_of(doc, line.split("\n")[0]), out["reason"])
                self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")))
                self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))

    def test_scope_builds_packets_for_equal_decisions(self):
        doc = EQUAL[0][1]
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=True, name="ws-equal")
        drive, run_dir = vlib.start(self.tmp, ws, run="run-equal")
        self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertTrue(os.path.isdir(os.path.join(run_dir, "packets")))


if __name__ == "__main__":
    unittest.main()
