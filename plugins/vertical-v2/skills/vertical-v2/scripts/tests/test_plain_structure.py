"""Plain structure only (the E15 lane contract A12; C1A7-1; contract section 5, "Plain structure").

Outside an accepted fence, any line that, after any indent and any list-item or block-quote markers (A8's
prefix), opens like an ATX heading (one to six `#`, then a space, a tab or the line's end) or like a `Status:`
or `Base:` label is read only when it is plain: at column 0 with no marker, a heading being one to six `#`
then exactly one space, a label as A10 and A11 rule. Every other such line is a problem named with its line
number, anywhere in the doc (inside a slice, in the header, between sections), so every reader of the build
doc (the gate's slices, the recorded base, the spec) stops `doc-unreadable` before any ask, request or packet.

`TheRule` drives the three readers directly over every shape; `TheGate` drives check 7's shapes through the
real CLI with records off and on; `TheScope` drives two of them through `scope` on the reviewed commit.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, spec  # noqa: E402

D = vlib.D
SLICE_B = "## Slice B %s the spinner" % D
PREFIXES = ("- ", "* ", "+ ", "1. ", "2) ", "> ", ">", "> > ", "> - ", "\t", " ", "  ", "   ", "    ", "-\t")


def two_slices(tail_b, header=(), slice_b=SLICE_B, between=()):
    """Slice A `signed off`, then (unless `slice_b` is None) slice B's heading and its first lines, then `tail_b`;
    `header` lines go after the header paragraph; `between` lines go between slice A's label and slice B."""
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "", "Intent: a counter.", "Out of scope: a dashboard"]
    lines += list(header)
    lines += ["", "## Slice A %s the counter" % D, "Goal: count.", "Depends on: nothing", "Status: signed off", ""]
    lines += list(between)
    if slice_b is not None:
        lines += [slice_b, "Goal: spin.", "Depends on: A"]
    lines += list(tail_b)
    lines += ["", "## Punch list", "- PUNCH-MARKER", ""]
    return "\n".join(lines)


def number_of(text, line, start=0):
    lines = text.split("\n")
    return lines.index(line, start) + 1


# (what, the doc, the line text whose first occurrence is the first problem)
CHECK_7 = []
for _indent in (" ", "  ", "   "):
    CHECK_7.append(("a slice heading and its label indented %d" % len(_indent),
                    two_slices([_indent + "Status: built"], slice_b=_indent + SLICE_B), _indent + SLICE_B))
CHECK_7 += [
    ("a slice heading with a tab after its hashes", two_slices(["Status: built"], slice_b=SLICE_B.replace("## ", "##\t", 1)),
     SLICE_B.replace("## ", "##\t", 1)),
    ("a bare ## heading", two_slices(["Status: signed off", "", "##", "a paragraph under an empty heading"]), "##"),
    ("an indented Base: line in the header", two_slices(["Status: signed off"], header=["", " Base: 1111111"]),
     " Base: 1111111"),
    ("a real slice's exact label in a lazy block-quote line, its rendered label indented",
     two_slices([" Status: built", "", "> Earlier draft:", "Status: signed off"]), " Status: built"),
    ("a real slice's exact label in a lazy list line, its rendered label indented",
     two_slices([" Status: built", "", "- earlier draft:", "Status: signed off"]), " Status: built"),
    ("a real slice's exact label under an empty ##, its rendered label indented",
     two_slices([" Status: built", "", "##", "Status: signed off"]), " Status: built"),
]


def stop_shapes():
    """(what, doc, first) for every shape the rule stops, beyond check 7's."""
    out = []
    for prefix in PREFIXES:
        for what, line in (("a heading", prefix + "## Notes"), ("a level 1 heading", prefix + "# Notes"),
                           ("a slice label", prefix + "Status: built"), ("a base label", prefix + "Base: 1111111")):
            out.append(("%s after %r inside a slice" % (what, prefix), two_slices(["Status: signed off", "", line]),
                        line))
            out.append(("%s after %r in the header" % (what, prefix), two_slices(["Status: signed off"],
                                                                                header=["", line]), line))
            out.append(("%s after %r between sections" % (what, prefix),
                        two_slices([], slice_b=None, between=["## Notes", "", line, ""]), line))
    for line in ("##\tNotes", "#\tTitle", "######\tsix", "##", "#", "######", "##  Notes", "#  Title",
                 "### \ta sub-heading", "## \t", "##   punch   LIST  ", " # Title", "   # Title", "   ##", "\t#"):
        out.append(("the heading %r inside a slice" % line, two_slices(["Status: signed off", "", line, "text"]),
                    line))
        out.append(("the heading %r in the header" % line, two_slices(["Status: signed off"], header=["", line]),
                    line))
    for line in ("##\tDeviations", "  ## Handoffs", "##  Punch list", "   ## Build assumptions"):
        out.append(("a withheld section's heading off the plain form, %r" % line,
                    two_slices(["Status: signed off", "", line, "- WITHHELD-MARKER"]), line))
    return out


def no_stop_docs():
    """(what, doc, the slices' statuses, a line the spec keeps or None) for shapes the rule never stops."""
    fenced = ["```text", " ## Slice C %s indented" % D, "  Status: built", "##\tx", "##", "- Base: 1111111",
              "> Status: signed off", "\t# Title", "```"]
    out = [
        ("heading- and label-shaped lines inside an accepted fence", two_slices(["Status: signed off", ""] + fenced),
         ["signed off", "signed off"], "\n".join(fenced) + "\n"),
        ("a heading-shaped line in a tilde fence before the slices",
         two_slices(["Status: signed off"], header=["", "~~~", "   ## not a heading here", " Base: 2222222", "~~~"]),
         ["signed off", "signed off"], "~~~\n   ## not a heading here\n Base: 2222222\n~~~\n"),
        ("a #hashtag with no space", two_slices(["Status: signed off", "", "#hashtag and ##two and ######six"]),
         ["signed off", "signed off"], "#hashtag and ##two and ######six\n"),
        ("seven hashes", two_slices(["Status: signed off", "", "####### seven is not a heading"]),
         ["signed off", "signed off"], "####### seven is not a heading\n"),
        ("Status: mid-line", two_slices(["Status: signed off", "", "The Status: built line above was an old note."]),
         ["signed off", "signed off"], "The Status: built line above was an old note.\n"),
        ("Base: mid-line", two_slices(["Status: signed off"], header=["", "the branch point, Base: 1111111, moved"]),
         ["signed off", "signed off"], "the branch point, Base: 1111111, moved\n"),
        ("a list item that only names the word", two_slices(["Status: signed off", "", "- the Status field is shown"]),
         ["signed off", "signed off"], "- the Status field is shown\n"),
        ("a dash with no space before the label", two_slices(["Status: signed off", "", "-Status: is text here"]),
         ["signed off", "signed off"], "-Status: is text here\n"),
        ("plain headings of every level", two_slices(["Status: signed off", "", "# One", "### Three", "#### Four",
                                                       "###### Six", "## Notes  ", "## Discovered ##"]),
         ["signed off", "signed off"], "# One\n### Three\n#### Four\n###### Six\n"),
        ("an empty heading of exactly one space", two_slices(["Status: signed off", "", "## ", "text"]),
         ["signed off", "signed off"], None),
    ]
    return out


class TheRule(unittest.TestCase):
    """Every reader of the build doc (the gate's slices, the recorded base, the spec) refuses each shape naming the
    same line, and `fences.read` reports it first."""

    def assert_stops(self, what, text, first):
        number = number_of(text, first)
        for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base), ("spec", spec.clean)):
            with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                call(text)
            self.assertEqual(caught.exception.line, number, (what, name, str(caught.exception)))
            self.assertIn("line %d" % number, str(caught.exception))
            self.assertIn("plain", caught.exception.what, what)
        self.assertEqual(fences.read(text).problems[0][0], number, what)

    def test_check_7s_shapes_stop_every_reader(self):
        for what, text, first in CHECK_7:
            with self.subTest(shape=what):
                self.assert_stops(what, text, first)

    def test_every_marker_and_indent_before_a_heading_or_a_label_stops_every_reader(self):
        for what, text, first in stop_shapes():
            with self.subTest(shape=what):
                self.assert_stops(what, text, first)

    def test_bold_label_text_passes_this_rule_and_the_second_reading_stops_it(self):
        """`**Status:** a note in bold` is no plain-structure problem, so this rule never stops it (it stood in the list
        above until A13); a CommonMark reader renders it `Status: a note in bold`, a second label line in slice B
        that the line rules never take, so the two readings differ on slice B's card and every reader stops naming
        the line (A13, `readings.py`)."""
        text = two_slices(["Status: signed off", "", "**Status:** a note in bold"])
        self.assertEqual(fences.read(text).problems, [])
        for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base), ("spec", spec.clean)):
            with self.assertRaises(spec.SpecUnreadable, msg=name) as caught:
                call(text)
            self.assertEqual(caught.exception.line, number_of(text, "**Status:** a note in bold"), name)
            self.assertIn("the two readings differ on a slice's card", caught.exception.what, name)

    def test_the_shapes_the_rule_never_stops(self):
        for what, text, statuses, kept_line in no_stop_docs():
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                self.assertEqual([s["status"] for s in gatemod.slices_of(text)], statuses, what)
                kept, removed = spec.clean(text)
                if kept_line is not None:
                    self.assertIn(kept_line, kept, what)

    def test_the_names_of_a_withheld_section_still_collapse_on_a_plain_heading(self):
        """C1A2-5 on the plain form: inner runs of whitespace, letter case and closing hashes still match."""
        text = two_slices(["Status: signed off", "", "## punch   LIST  ", "- WITHHELD-ONE", "## Deviations ##",
                           "- WITHHELD-TWO"])
        kept, removed = spec.clean(text)
        self.assertNotIn("WITHHELD-ONE", kept)
        self.assertNotIn("WITHHELD-TWO", kept)
        self.assertIn("## Deviations", [r["what"] for r in removed])

    def test_a_problem_line_is_never_read_as_structure(self):
        """The fenced-off reading is unchanged: the first problem is the first line in document order, whatever
        kind of line it is (a fence line, a raw HTML line, a label, a heading)."""
        text = two_slices(["Status: signed off", "", "<div>", "", " ## Notes"])
        self.assertEqual(fences.read(text).problems[0][0], number_of(text, "<div>"))
        text = two_slices(["Status: signed off", "", " ## Notes", "", "<div>"])
        self.assertEqual(fences.read(text).problems[0][0], number_of(text, " ## Notes"))
        self.assertEqual([p[0] for p in fences.read(text).problems],
                         [number_of(text, " ## Notes"), number_of(text, "<div>")])


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Check 7's shapes through the real CLI, records off and on: exit 10, `doc-unreadable` naming the line,
    `next: done`, no `ask.json`, no request file."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vplain-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records, **station):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count, **station)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def assert_unreadable(self, what, doc, first, records, **station):
        code, out, err, run_dir = self.gate(doc, records, **station)
        self.assertEqual(code, 10, (what, records, out, err))
        self.assertEqual((out["status"], out["stop_tag"], out.get("next")), ("stopped", "doc-unreadable", "done"),
                         (what, records, out))
        self.assertIn("line %d" % number_of(doc, first), out["reason"], (what, records))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "ask.json")), what)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-local.json")), what)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)
        self.assertEqual(vlib.load(run_dir, "checkpoint.json")["phase"], "done")

    def test_check_7s_shapes_stop_the_gate_with_no_records_log(self):
        for what, doc, first in CHECK_7:
            with self.subTest(shape=what):
                self.assert_unreadable(what, doc, first, records=False)

    def test_check_7s_shapes_stop_the_gate_with_a_records_log(self):
        for what, doc, first in CHECK_7:
            with self.subTest(shape=what):
                self.assert_unreadable(what, doc, first, records=True)

    def test_the_owners_base_never_clears_an_indented_base_line(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        line = "  Base: %s" % info0["base"]
        doc = vlib.build_doc(extra_header=["", line])
        self.assert_unreadable("an indented base", doc, line, records=False,
                               owner_words={"base": {"commit": info0["base"], "words": "from the first commit"}})

    def test_a_plain_doc_still_passes_with_its_fenced_shapes(self):
        doc = vlib.build_doc().replace("Depends on: nothing\nStatus: signed off\n\n## Slice B",
                                       "Depends on: nothing\n```text\n ## Slice C %s x\n  Status: built\n```\n"
                                       "#hashtag\nStatus: signed off\n\n## Slice B" % D, 1)
        self.assertIn("#hashtag", doc)
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate(doc, records)
                self.assertEqual(code, 0, (out, err))
                gate = vlib.load(run_dir, "gate.json")
                self.assertEqual([s["status_line"] for s in gate["slices"]], ["signed off", "signed off"])


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):
    """The reviewed commit holds the shape, the working tree a plain doc, under the owner's committed-state-only
    words: `scope` stops `doc-unreadable` naming the line before any packet."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vplain-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_scope_stops_on_an_indented_heading_and_an_indented_label_in_the_commit(self):
        for index, (what, line) in enumerate((("an indented slice label", " Status: built"),
                                              ("a heading with a tab", "##\tNotes"))):
            with self.subTest(shape=what):
                doc = vlib.build_doc().replace("## Build assumptions\n", line + "\n\n## Build assumptions\n", 1)
                ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=True, name="ws-%d" % index)
                testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
                drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % index,
                                            owner_words={"committed_only": "review the committed state only"})
                self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
                code, out, err = drive(["scope", "--run-dir", run_dir])
                self.assertEqual(code, 10, (out, err))
                self.assertEqual(out["stop_tag"], "doc-unreadable")
                self.assertIn("line %d" % number_of(doc, line), out["reason"])
                self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")))
                self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))


if __name__ == "__main__":
    unittest.main()
