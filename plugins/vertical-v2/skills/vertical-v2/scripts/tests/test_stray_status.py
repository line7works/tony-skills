"""Round 12 of class (a): a stray `Status:` line stops the run, wider withheld names, leading marks before a label (the
E15 lane contract A18; contract section 5, "Exact labels", "The spec" and "The fold").

(1) In the line reading (raw source lines outside accepted fences, never the second reading's rendered lines), a
`Status:` label candidate after the build doc's first level 2 heading and outside every slice's section stops the run
`doc-unreadable` naming its line, before any ask, request or packet. So a slice heading no reading takes (`## 1. Slice
B`, `## (1) Slice B`, `## A. Slice B`, `## 1.1 Slice B`, `## SIice B`, `## S1ice B`, `## Next: Slice B`, `## The Slice
B`, `## ` U+00B2 `Slice B`) over `Status: built` stops at the `Status:` line instead of leaving its `built` slice out of
the sign-off check. A candidate before the first level 2 heading keeps its handling (the spec removes it), and a
`Status:` line inside an accepted fence is content.
(2) The withheld-name key maps U+00F0, U+00F8, U+00FE and U+00E6 after the fold, reads every character of Unicode
category P, S or Z as a space, drops leading numbering (`1`, `1.1`, `1a`, a single letter, a lower-case roman numeral,
`the`) and matches the stems `builders assumption` and `builder s assumption` too.
(3) The label test sets aside a leading run of Unicode spaces and of the listed non-ASCII punctuation and symbols
before it tests `Status` or `Base`, so `‘Status: built` above a plain `Status: signed off` and `‘Base: 1234567` in
the header stop at their line, and the spec removes such a line; `### ‘Status: built` is refusal (c). ASCII
punctuation is not set aside.

`TheReaders` drives the readers directly; `TheGate` drives the shapes through the real CLI, records off and on;
`TheScope` drives the stopping shapes through `scope` (only in the reviewed commit) and the withheld names to every
packet, the outside packet included.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, readings, spec  # noqa: E402

D = vlib.D
SLICE_B = "## Slice B %s the spinner" % D
B_BODY = ["Goal: one sentence about the spinner.", "Depends on: nothing"]


def with_b(lines, heading=SLICE_B, slice_a="signed off"):
    """vlib's doc with slice A only, then `heading`, slice B's first lines and `lines`, before the working records."""
    base = vlib.build_doc(slices=[("A", "the counter", slice_a)])
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join([heading] + B_BODY + list(lines)) + "\n" + base[at:]


def header(lines):
    return vlib.build_doc(extra_header=list(lines))


def number_of(text, line):
    return text.split("\n").index(line) + 1


# (1) the vanishing slice headings, each over `Status: built`: (what, doc, the line the stop names)
VANISHING = ("## 1. Slice B", "## (1) Slice B", "## A. Slice B", "## 1.1 Slice B", "## SIice B", "## S1ice B",
             "## Next: Slice B", "## The Slice B", "## ²Slice B")
STRAY_SHAPES = [("%s over Status: built" % heading,
                 with_b(["Status: built"], heading="%s %s the spinner" % (heading, D)), "Status: built")
                for heading in VANISHING]
STRAY_IN_WITHHELD = vlib.build_doc().replace("## Deviations\n", "## Deviations\n- one\n\nStatus: built\n", 1)

# (3) a leading listed mark before a label: (what, doc, the line the stop names)
MARKS = ("‘Status: built", "“Status: built”", "§ Status: built", "…Status: built",
         "· Status: built")
MARK_SHAPES = [("%s above the plain Status: signed off" % mark, with_b(["", mark, "", "Status: signed off"]), mark)
               for mark in MARKS] + [
    ("‘Base: 1234567 in the header", header(["", "‘Base: 1234567"]), "‘Base: 1234567")]

STOP_SHAPES = STRAY_SHAPES + [("Status: built in a withheld section", STRAY_IN_WITHHELD, "Status: built")] + MARK_SHAPES

# (2) the withheld names: (heading, canonical)
NAME_SHAPES = [
    ("## Hand“offs", "## Handoffs"), ("## Hand”offs", "## Handoffs"), ("## Hand…offs", "## Handoffs"),
    ("## Hand×offs", "## Handoffs"), ("## Hand→offs", "## Handoffs"), ("## Hand.offs", "## Handoffs"),
    ("## Hand/offs", "## Handoffs"), ("## Hand+offs", "## Handoffs"), ("## Hand~offs", "## Handoffs"),
    ("## Hand'offs", "## Handoffs"),
    ("## a) Punch list", "## Punch list"), ("## (a) Punch list", "## Punch list"),
    ("## II. Punch list", "## Punch list"), ("## 1: Punch list", "## Punch list"),
    ("## 1.) Punch list", "## Punch list"), ("## #1 Punch list", "## Punch list"),
    ("## [1] Punch list", "## Punch list"),
    ("## Builder’s assumptions", "## Build assumptions"), ("## Builder's assumptions", "## Build assumptions"),
    ("## Builders assumptions", "## Build assumptions"),
    ("## Ðeviations", "## Deviations"), ("## HandØffs", "## Handoffs"),
]
NAME_CONTROLS = ("## Theory", "## Handy offsets", "## A note on punctuation", "## I/O notes", "## Mix and match")


def withheld_doc(heading, marker="A18-NAME-MARKER"):
    return with_b(["Status: signed off", "", heading, "- %s the builder says skim slice B" % marker])


class TheReaders(unittest.TestCase):

    def assert_stops(self, what, text, line):
        number = number_of(text, line)
        for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base), ("spec", spec.clean)):
            with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                call(text)
            self.assertEqual(caught.exception.line, number, (what, name, str(caught.exception)))

    def test_every_stray_status_line_stops_every_reader_at_its_line(self):
        for what, text, line in STRAY_SHAPES + [("in a withheld section", STRAY_IN_WITHHELD, "Status: built")]:
            with self.subTest(shape=what):
                self.assertTrue(all(fences.unlisted(row) is None for row in text.split("\n")), what)
                problems = fences.read(text).problems
                self.assertTrue(problems, what)
                self.assertEqual(problems[0][0], number_of(text, line), (what, problems))
                self.assertIn("outside every slice", problems[0][1], what)
                self.assert_stops(what, text, line)

    def test_every_leading_mark_before_a_label_stops_every_reader_at_its_line(self):
        for what, text, line in MARK_SHAPES:
            with self.subTest(shape=what):
                self.assertTrue(all(fences.unlisted(row) is None for row in text.split("\n")), what)
                self.assertIsNotNone(fences.label_candidate(line), what)
                self.assert_stops(what, text, line)

    def test_ascii_punctuation_before_a_label_is_not_set_aside(self):
        for line in ("*Status: built", "\"Status: built", "(Status: built", "-Status: built", "\\Status: built"):
            with self.subTest(line=line):
                self.assertIsNone(fences.label_candidate(line), line)

    def test_a_label_heading_after_a_curly_quote_is_refusal_c(self):
        text = with_b(["", "### ‘Status: built", "", "Status: signed off"])
        line = number_of(text, "### ‘Status: built")
        self.assertEqual(fences.read(text).problems, [])
        refused = readings.second_reading(text, len(fences.read(text).lines))["refused"]
        self.assertIn((line, "label-heading"), [(r[0], r[1]) for r in refused])
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(text)
        self.assertEqual(caught.exception.line, line)

    def test_a_marked_status_line_in_the_header_is_removed_by_the_spec(self):
        for mark in ("‘Status: draft", "“Status: draft”", "· Status: draft"):
            with self.subTest(mark=mark):
                text = header(["", mark])
                self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                                 [("A", "signed off"), ("B", "signed off")])
                kept, removed = spec.clean(text)
                self.assertNotIn(mark, kept)
                self.assertIn({"what": "Status: line", "lines": [number_of(text, mark)] * 2}, removed)

    def test_the_controls(self):
        """A well-formed slice runs; a header `Status:` line keeps its handling (removed); a fenced `Status:` line after
        a non-slice heading runs and stays."""
        well = with_b(["Status: signed off"])
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(well)],
                         [("A", "signed off"), ("B", "signed off")])
        head = header(["Status: draft HEADER-A18"])
        self.assertEqual(len(gatemod.slices_of(head)), 2)
        kept, removed = spec.clean(head)
        self.assertNotIn("HEADER-A18", kept)
        fenced = with_b(["Status: signed off", "", "## Bench notes", "```", "Status: built FENCED-A18", "```"])
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(fenced)],
                         [("A", "signed off"), ("B", "signed off")])
        kept, removed = spec.clean(fenced)
        self.assertIn("Status: built FENCED-A18", kept)

    def test_every_name_shape_is_withheld_and_named_the_same_in_both_readings(self):
        for heading, canonical in NAME_SHAPES:
            with self.subTest(heading=heading):
                text = withheld_doc(heading)
                self.assertTrue(all(fences.unlisted(row) is None for row in text.split("\n")), heading)
                self.assertIsNone(readings.difference(text), heading)
                doc = fences.read(text)
                self.assertEqual(doc.problems, [], heading)
                first = number_of(text, heading)
                second = readings.second_reading(text, len(doc.lines))
                self.assertEqual(second["withheld"].get(first, (None,))[0], canonical, (heading, second["withheld"]))
                self.assertEqual([s[:3] for s in spec.sections(doc) if s[1] == first], [(canonical, first, first + 2)],
                                 heading)
                kept, removed = spec.clean(text)
                self.assertNotIn("A18-NAME-MARKER", kept, heading)
                self.assertIn({"what": canonical, "lines": [first, first + 2]}, removed, (heading, removed))

    def test_the_name_controls_are_not_withheld(self):
        for heading in NAME_CONTROLS:
            with self.subTest(heading=heading):
                self.assertIsNone(spec.withheld_of(heading[3:]), heading)
                kept, removed = spec.clean(withheld_doc(heading, marker="A18-KEPT-MARKER"))
                self.assertIn("A18-KEPT-MARKER", kept, heading)

    def test_the_stroke_letters_reach_the_stems(self):
        self.assertEqual(spec.name_key("Ðeviations"), "deviations")
        self.assertEqual(spec.name_key("HandØffs"), "handoffs")
        self.assertEqual(spec.name_key("ÞE punch list"), "punch list")
        self.assertEqual(spec.name_key("Æsop"), "aesop")


class TheStatement(unittest.TestCase):
    """Each rule stated once in code and once in the contract."""

    def paragraph(self, title):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index(title)
        return " ".join(text[start:text.index("\n\n", start)].split())

    def test_the_stray_rule_and_the_leading_marks_are_stated_in_the_contract(self):
        para = self.paragraph("**Exact labels**")
        self.assertIn("after the build doc's first level 2 heading and outside every slice's section", para)
        self.assertIn("A18 (1)", para)
        self.assertIn("A18 (3)", para)
        self.assertIn("ASCII punctuation is not set aside", para)

    def test_the_name_key_is_stated_in_the_contract(self):
        para = self.paragraph("**The spec**")
        for words in ("Unicode category P, S or Z", "U+00F0", "U+00F8", "U+00FE", "U+00E6", "`1a`",
                      "lower-case roman numeral", "`builders assumption`", "`builder s assumption`"):
            self.assertIn(words, para)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every stopping shape through the real CLI, records off and on: exit 10, `doc-unreadable` naming the line, no
    `ask.json`, no request file, no `packets`; the controls pass."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vstray-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def test_every_stopping_shape_stops_the_gate_at_its_line(self):
        for what, doc, line in STOP_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 10, (what, out, err))
                    self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), (what, out))
                    self.assertIn("line %d" % number_of(doc, line), out["reason"], what)
                    for name in ("ask.json", "requests-local.json", "packets", "scope.json"):
                        self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))

    def test_the_controls_pass_or_stop_as_before(self):
        for what, doc, tag in (
                ("a well-formed slice", with_b(["Status: signed off"]), None),
                ("a plain built slice", with_b(["Status: built"]), "gate-short"),
                ("a header Status: line", header(["", "Status: draft"]), None),
                ("a marked header Status: line", header(["", "‘Status: draft"]), None),
                ("a fenced Status: line after a non-slice heading",
                 with_b(["Status: signed off", "", "## Bench notes", "```", "Status: built", "```"]), None),
                ("a withheld name", withheld_doc("## a) Punch list"), None)):
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    if tag is None:
                        self.assertEqual(code, 0, (what, out, err))
                        self.assertEqual(out["next"], "ask", what)
                    else:
                        self.assertEqual(code, 10, (what, out, err))
                        self.assertEqual(out["stop_tag"], tag, (what, out))


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vstray-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def packets(self, run_dir):
        root = os.path.join(run_dir, "packets")
        names = sorted(os.listdir(root))
        self.assertTrue(any(name.startswith("outside-") for name in names), names)
        return [os.path.join(root, name) for name in names]

    def test_scope_stops_on_every_stopping_shape_only_in_the_commit(self):
        for what, doc, line in STOP_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    self.count += 1
                    ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
                    testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
                    drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count,
                                                owner_words={"committed_only": "review the committed state only"})
                    code, out, err = vlib.through_ask(drive, self.tmp, run_dir)
                    self.assertEqual(code, 0, (what, out, err))
                    code, out, err = drive(["scope", "--run-dir", run_dir])
                    self.assertEqual(code, 10, (what, out, err))
                    self.assertEqual(out["stop_tag"], "doc-unreadable", what)
                    self.assertIn("line %d" % number_of(doc, line), out["reason"], what)
                    self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)

    def test_every_name_shape_reaches_no_packet_and_is_named(self):
        for index, (heading, canonical) in enumerate(NAME_SHAPES):
            with self.subTest(heading=heading):
                doc = withheld_doc(heading)
                drive, run_dir, ws, info = vlib.through_scope(os.path.join(self.tmp, "w%d" % index),
                                                              repo={"doc_text": doc})
                first = number_of(doc, heading)
                for packet_dir in self.packets(run_dir):
                    for base, dirs, files in os.walk(packet_dir):
                        for name in files:
                            if name in ("files.json", "withheld.json"):
                                continue
                            with open(os.path.join(base, name), "rb") as fh:
                                self.assertNotIn(b"A18-NAME-MARKER", fh.read(), (heading, os.path.join(base, name)))
                    entries = [w for w in testlib.load_json(os.path.join(packet_dir, "withheld.json"))["withheld"]
                               if w["what"] == "%s %s" % (vlib.DOC, canonical)]
                    self.assertTrue(any("lines %d to %d" % (first, first + 2) in w["why"] for w in entries),
                                    (heading, packet_dir, entries))


if __name__ == "__main__":
    unittest.main()
