"""Round 9 of class (a): the label bug and three near misses (the E15 lane contract A14; contract section 5,
"Two readings").

(1) C1A8-1. The second reading keeps every rendered label line, a list, never one entry per source line; and a
rendered `Status:` or `Base:` line inside a paragraph whose rendered lines cannot all be mapped to source lines (a
code span or a link title running over a line ending) stops `doc-unreadable` naming the paragraph's first line.
(2) C1A8-2. A level 1 or level 2 heading whose rendered name, with format characters (Unicode category Cf) removed,
starts with `slice` in any case and does not match the build-doc form's slice pattern stops `doc-unreadable` naming
its line; a level 3 `### Slice D <dot> <date>` note is not touched.
(3) C1A8-3. A level 1 or level 2 section whose rendered name, lower-cased with format characters removed, starts with
a withheld name's stem (`punch`, `handoff`, `hand-off`, `build assumption`, `deviation`, `discover`) is withheld and
named as withheld, the same in both readings; a heading of any level whose rendered name starts with `Status:` or
`Base:` stops `doc-unreadable`.
(4) C1A8-4. The notes leg stops only when the CommonMark reading declares a file the builder's notes and the line
reading does not; a file the line reading withholds wider stays withheld, as before A13.

`TheReadings` drives the readers directly; `TheGate` drives the stopping shapes through the real CLI, records off and
on; `TheScope` drives the withheld shapes, a committed-only stop and the notes leg through `scope`.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, notes, spec  # noqa: E402

D = vlib.D
M = vlib.M
SLICE_B = "## Slice B %s the spinner" % D
B_BODY = ["Goal: one sentence about the spinner.", "Depends on: nothing"]
ZWSP = "​"
EN_DASH = "–"


def with_b(lines, heading=SLICE_B, slice_a="signed off"):
    """vlib's doc with slice A only, then `heading`, slice B's first lines and `lines`, before the working records."""
    base = vlib.build_doc(slices=[("A", "the counter", slice_a)])
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join([heading] + B_BODY + list(lines)) + "\n" + base[at:]


def header(lines):
    return vlib.build_doc(extra_header=list(lines))


def number_of(text, line):
    return text.split("\n").index(line) + 1


CODE_SPAN = ["", "Note `a", "b` here."]
LINK_TITLE = ["", "See [the plan](/plan \"a", "b\")."]

# (1) C1A8-1: (what, doc, the text of the paragraph's first line)
LABEL_SHAPES = [
    ("a bold Status: built above the plain label, after a multi-line code span",
     with_b(CODE_SPAN + ["**Status:** built", "Status: signed off"]), "Note `a"),
    ("a character-coded Status: built above the plain label, after a multi-line code span",
     with_b(CODE_SPAN + ["&#83;tatus: built", "Status: signed off"]), "Note `a"),
    ("a bold Status: built above the plain label, after a multi-line link title",
     with_b(LINK_TITLE + ["**Status:** built", "Status: signed off"]), "See [the plan](/plan \"a"),
    ("a character-coded Status: built above the plain label, after a multi-line link title",
     with_b(LINK_TITLE + ["&#83;tatus: built", "Status: signed off"]), "See [the plan](/plan \"a"),
    ("one exact label ending a paragraph that holds a multi-line code span",
     with_b(CODE_SPAN + ["Status: signed off"]), "Note `a"),
    ("two rendered Base: lines after a multi-line code span",
     header(CODE_SPAN + ["**Base:** 1234567", "Base: abcdef1"]), "Note `a"),
    ("a character-coded Base: above the plain one, after a multi-line link title",
     header(LINK_TITLE + ["&#66;ase: 1234567", "Base: abcdef1"]), "See [the plan](/plan \"a"),
]
# a plain doc with a multi-line code span (its own paragraph) and one exact label: it runs
LABEL_CONTROL = with_b(CODE_SPAN + ["", "Status: signed off"])

# (2) C1A8-2: (what, doc, the heading's first line)
SLICE_FORM_SHAPES = [
    ("an en dash", with_b(["Status: built"], heading="## Slice B %s the spinner" % EN_DASH),
     "## Slice B %s the spinner" % EN_DASH),
    ("a hyphen", with_b(["Status: built"], heading="## Slice B - the spinner"), "## Slice B - the spinner"),
    ("a colon", with_b(["Status: built"], heading="## Slice B: the spinner"), "## Slice B: the spinner"),
    ("no spaces around the dash", with_b(["Status: built"], heading="## Slice B%sthe spinner" % D),
     "## Slice B%sthe spinner" % D),
    ("a lower-case slice", with_b(["Status: built"], heading="## slice B %s the spinner" % D),
     "## slice B %s the spinner" % D),
    ("a zero-width space inside Slice", with_b(["Status: built"], heading="## Sl%sice B %s the spinner" % (ZWSP, D)),
     "## Sl%sice B %s the spinner" % (ZWSP, D)),
    ("a level 1 heading in the form", with_b([], heading="# Slice B %s the spinner" % D),
     "# Slice B %s the spinner" % D),
    ("a Setext heading with an en dash", with_b([], heading="Slice B %s the spinner\n---" % EN_DASH),
     "Slice B %s the spinner" % EN_DASH),
]
# a level 3 note inside slice B is not touched: it runs
LEVEL_3_NOTE = with_b(["", "### Slice D %s 2026-10-01" % M, "a note on the day.", "", "Status: signed off"])

# (3) C1A8-3, a heading named like a label: (what, doc, the heading's line)
LABEL_HEADING_SHAPES = [
    ("### Status: built inside a slice", with_b(["", "### Status: built", "", "Status: signed off"]),
     "### Status: built"),
    ("#### Status: signed off inside a slice", with_b(["", "#### Status: signed off", "", "Status: signed off"]),
     "#### Status: signed off"),
    ("a zero-width space before a Status: heading", with_b(["", "### %sStatus: built" % ZWSP, "", "Status: signed off"]),
     "### %sStatus: built" % ZWSP),
    ("a character-coded Status: heading", with_b(["", "### &#83;tatus: built", "", "Status: signed off"]),
     "### &#83;tatus: built"),
    ("a Base: heading in the header", header(["", "### Base: 1234567"]), "### Base: 1234567"),
]
# (3) C1A8-3, the withheld near misses: (what, heading, canonical name)
WITHHELD_SHAPES = [
    ("a hyphen in Punch list", "## Punch-list", "## Punch list"),
    ("a colon after Punch list", "## Punch list:", "## Punch list"),
    ("a singular Handoff", "## Handoff", "## Handoffs"),
    ("a hyphen in Hand-offs", "## Hand-offs", "## Handoffs"),
    ("a zero-width space in Punch list", "## Punch%s list" % ZWSP, "## Punch list"),
    ("a dated Handoff, as one real plan writes it", "## Handoff, 2026-09-25", "## Handoffs"),
    ("a singular Build assumption", "## Build assumption", "## Build assumptions"),
    ("a singular Deviation", "## Deviation", "## Deviations"),
    ("Discoveries", "## Discoveries", "## Discovered"),
    ("a level 1 Punch-list", "# Punch-list", "## Punch list"),
]


def withheld_doc(heading, marker="NEARMISS-MARKER"):
    return with_b(["Status: signed off", "", heading, "- %s the builder says skim slice B" % marker])


README_HTML = ("<p align=\"center\">Turnstile</p>\n\n# Turnstile\n\nA bench-rig turn counter.\n\n## Build notes\n\n"
               "NOTES-WIDE-MARKER the counter is obviously right\n")
LINT_COMMENT = "<!-- markdownlint-disable MD041 -->\n# Bench guide\n\n## Builder notes\n\nNOTES-LINT-MARKER skim B\n"


def readings():
    from vertical_core import readings as mod  # noqa: E402
    return mod


class TheReadings(unittest.TestCase):

    def assert_stops(self, what, text, first, needle=None):
        number = number_of(text, first)
        for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base), ("spec", spec.clean)):
            with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                call(text)
            self.assertEqual(caught.exception.line, number, (what, name, str(caught.exception)))
            if needle:
                self.assertIn(needle, caught.exception.what, (what, name))

    def test_every_label_shape_passes_the_line_rules_and_stops_every_reader_at_the_paragraphs_first_line(self):
        for what, text, first in LABEL_SHAPES:
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                self.assert_stops(what, text, first, "cannot")

    def test_the_second_reading_keeps_every_rendered_label_line(self):
        """Two rendered labels in one paragraph whose lines carry one line number stay two entries."""
        mod = readings()
        text = LABEL_SHAPES[0][1]
        doc = fences.read(text)
        second = mod.second_reading(text, len(doc.lines))
        self.assertEqual(len(second["cards"][1]), 2, second["cards"])
        self.assertEqual([entry[1] for entry in second["cards"][1]], ["built", "signed off"], second["cards"])
        text = LABEL_SHAPES[5][1]
        second = mod.second_reading(text, len(fences.read(text).lines))
        self.assertEqual(len(second["base"]), 2, second["base"])

    def test_a_multi_line_code_span_in_its_own_paragraph_and_one_exact_label_still_read(self):
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(LABEL_CONTROL)],
                         [("A", "signed off"), ("B", "signed off")])
        self.assertIsNone(readings().difference(LABEL_CONTROL))

    def test_every_slice_form_near_miss_stops_every_reader_naming_its_heading(self):
        for what, text, first in SLICE_FORM_SHAPES:
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                self.assert_stops(what, text, first, "slice")

    def test_a_level_3_slice_note_is_not_touched(self):
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(LEVEL_3_NOTE)],
                         [("A", "signed off"), ("B", "signed off")])
        self.assertIsNone(readings().difference(LEVEL_3_NOTE))

    def test_every_heading_named_like_a_label_stops_every_reader_naming_its_line(self):
        for what, text, first in LABEL_HEADING_SHAPES:
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                self.assert_stops(what, text, first)

    def test_every_withheld_near_miss_is_withheld_and_named_the_same_in_both_readings(self):
        mod = readings()
        for what, heading, canonical in WITHHELD_SHAPES:
            with self.subTest(shape=what):
                text = withheld_doc(heading)
                self.assertIsNone(mod.difference(text), what)
                kept, removed = spec.clean(text)
                self.assertNotIn("NEARMISS-MARKER", kept, what)
                self.assertNotIn(heading, kept, what)
                first = number_of(text, heading)
                self.assertIn({"what": canonical, "lines": [first, first + 2]}, removed, (what, removed))

    def test_the_wide_line_reading_alone_never_stops_a_notes_file(self):
        mod = readings()
        for text in (README_HTML, LINT_COMMENT):
            self.assertIsNone(mod.notes_difference(text), text)
            self.assertIsNotNone(notes.declares(text), text)

    def test_the_leaking_direction_still_differs(self):
        found = readings().notes_difference("# Builder&#32;notes\n\nNOTES-MARKER\n")
        self.assertIsNotNone(found)
        self.assertEqual(found[0], 1)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every stopping shape through the real CLI, records off and on: exit 10, `doc-unreadable` naming the line, no
    `ask.json`, no request file, no `packets`; the controls pass the gate."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vnear-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records, extra=None):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count,
                                  extra_build_files=extra)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def assert_unreadable(self, what, code, out, err, run_dir, needle):
        self.assertEqual(code, 10, (what, out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), (what, out))
        self.assertIn(needle, out["reason"], what)
        for name in ("ask.json", "requests-local.json", "packets", "scope.json"):
            self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))

    def stops(self, shapes):
        for what, doc, first in shapes:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assert_unreadable(what, code, out, err, run_dir, "line %d" % number_of(doc, first))

    def test_every_label_shape_stops_the_gate(self):
        self.stops(LABEL_SHAPES)

    def test_every_slice_form_near_miss_stops_the_gate(self):
        self.stops(SLICE_FORM_SHAPES)

    def test_every_heading_named_like_a_label_stops_the_gate(self):
        self.stops(LABEL_HEADING_SHAPES)

    def test_the_controls_pass_the_gate(self):
        for what, doc in (("a multi-line code span and one exact label", LABEL_CONTROL),
                          ("a level 3 slice note", LEVEL_3_NOTE),
                          ("a withheld near miss", withheld_doc("## Punch-list"))):
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 0, (what, out, err))
                    self.assertEqual(out["next"], "ask", what)

    def test_a_notes_file_the_line_reading_alone_declares_passes_the_gate(self):
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate(None, records, extra={"README.md": README_HTML,
                                                                          "notes/bench-guide.md": LINT_COMMENT})
                self.assertEqual(code, 0, (out, err))

    def test_the_leaking_notes_direction_still_stops_the_gate(self):
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate(None, records, extra={"notes/bench.md": "# Builder&#32;notes\n\nX\n"})
                self.assert_unreadable("coded notes", code, out, err, run_dir, "notes/bench.md")


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vnear-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def packets(self, run_dir):
        root = os.path.join(run_dir, "packets")
        names = sorted(os.listdir(root))
        self.assertTrue(names)
        return [os.path.join(root, name) for name in names]

    def assert_absent(self, run_dir, marker):
        for packet_dir in self.packets(run_dir):
            for base, dirs, files in os.walk(packet_dir):
                for name in files:
                    if name in ("files.json", "withheld.json"):
                        continue
                    with open(os.path.join(base, name), "rb") as fh:
                        self.assertNotIn(marker.encode("utf-8"), fh.read(), os.path.join(base, name))

    def withheld(self, packet_dir):
        return testlib.load_json(os.path.join(packet_dir, "withheld.json"))["withheld"]

    def test_every_withheld_near_miss_reaches_no_packet_and_is_named(self):
        for index, (what, heading, canonical) in enumerate(WITHHELD_SHAPES):
            with self.subTest(shape=what):
                doc = withheld_doc(heading)
                drive, run_dir, ws, info = vlib.through_scope(os.path.join(self.tmp, "w%d" % index),
                                                              repo={"doc_text": doc})
                self.assert_absent(run_dir, "NEARMISS-MARKER")
                first = number_of(doc, heading)
                for packet_dir in self.packets(run_dir):
                    entries = [w for w in self.withheld(packet_dir) if w["what"] == "%s %s" % (vlib.DOC, canonical)]
                    self.assertTrue(any("lines %d to %d" % (first, first + 2) in w["why"] for w in entries),
                                    (what, packet_dir, entries))

    def test_scope_stops_on_a_label_shape_only_in_the_commit(self):
        for index, (what, doc, first) in enumerate((LABEL_SHAPES[0], LABEL_SHAPES[5], SLICE_FORM_SHAPES[0],
                                                     LABEL_HEADING_SHAPES[0])):
            with self.subTest(shape=what):
                # records off: the frozen records importer reads some of these shapes from the commit (the en-dash
                # slice B as `built`), which would stop the gate `card-disagrees` against the plain working-tree doc
                ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=False, name="ws-%d" % index)
                testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
                drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % index,
                                            owner_words={"committed_only": "review the committed state only"})
                self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0, what)
                code, out, err = drive(["scope", "--run-dir", run_dir])
                self.assertEqual(code, 10, (what, out, err))
                self.assertEqual(out["stop_tag"], "doc-unreadable", what)
                self.assertIn("line %d" % number_of(doc, first), out["reason"], what)
                self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)

    def test_a_notes_file_the_line_reading_alone_declares_is_withheld_and_named(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp, repo={"extra_build_files": {
            "README.md": README_HTML, "notes/bench-guide.md": LINT_COMMENT}})
        self.assert_absent(run_dir, "NOTES-WIDE-MARKER")
        self.assert_absent(run_dir, "NOTES-LINT-MARKER")
        for packet_dir in self.packets(run_dir):
            whys = dict((w["what"], w["why"]) for w in self.withheld(packet_dir))
            self.assertIn("first heading", whys.get("README.md", ""), packet_dir)
            self.assertIn("first heading", whys.get("notes/bench-guide.md", ""), packet_dir)


if __name__ == "__main__":
    unittest.main()
