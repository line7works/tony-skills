"""Round 10 of class (a): a character allowlist (the E15 lane contract A16; contract section 5, "The character list").

(1) Outside accepted fences, every character of the build doc must be printable ASCII, a tab, a line ending, a byte
order mark at the start of line 1, or one of the fixed list (`fences.LISTED`); any other character stops every reader
`doc-unreadable`, naming its code point and its line, before any ask, request or packet. Inside an accepted fence no
character is refused (A8's fence rule comes first). A character reference that a CommonMark reader decodes to a
character outside the list stops the same way (the second reading's refusal (d)).
(2) In any other Markdown file the station includes, a heading line holding a character outside the list makes the file
a notes candidate: withheld and named, never a stop. Since send-back 1 of this round, the heading lines read are the ones
the builder's-notes declaration test itself reads (the candidates up to the file's first certain heading, never a fenced
line; the CommonMark reader's first heading), so a later heading or a fenced sample holding such a character leaves the
file an ordinary one; and the declaration test reads a curly apostrophe (U+2018, U+2019) as `'` in both readings.
(3) Label and heading-name tests compare after NFKC normalization and case folding, and `Status` or `Base` followed by
spaces or tabs before the colon is a label candidate, so a non-exact one stops.
(4) The withheld-name test compares after NFKC, case folding, hyphens, dashes (U+2010 to U+2015) and underscores read
as spaces, whitespace collapsed and a leading number (`1.`, `2)`) or a leading `the` dropped (A17 (2) widens it:
`test_folded_names.py`; since then a bare leading number is numbering too, so `## 10 punches` is withheld).

`TheList` holds the code's constant against the contract's statement. `TheReadings` drives the readers directly;
`TheGate` drives the stopping shapes through the real CLI, records off and on; `TheScope` drives them through `scope`
on the reviewed commit only (the owner's committed-state-only words), records off and on, and drives the withheld
shapes and the notes candidates to the packets.
"""
import os
import re
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, packet, readings, spec  # noqa: E402

D = vlib.D
SLICE_B = "## Slice B %s the spinner" % D
B_BODY = ["Goal: one sentence about the spinner.", "Depends on: nothing"]
# check 9's C1A9-1 characters: default-ignorable or blank characters outside Unicode category Cf and the spaces
C1A9_1 = (0x034F, 0xFE00, 0xFE0F, 0x180B, 0x180C, 0x180D, 0x17B4, 0x115F, 0x1160, 0x3164, 0xFFA0, 0x2800)
FIXED = (0x00A7, 0x00B2, 0x00B7, 0x00D7, 0x2013, 0x2014, 0x2019, 0x2026, 0x2190, 0x2191, 0x2192, 0x2193, 0x2194,
         0x2197, 0x2212, 0x2248, 0x2264, 0x2265, 0x2715, 0x2018, 0x201C, 0x201D)
ACCENTED = tuple(c for c in range(0xC0, 0x100) if c != 0xF7)
# unlisted characters a fence may hold: the C1A9-1 set, format characters, Unicode spaces and line separators, a
# right-to-left override, a Cyrillic and a full-width letter, an emoji, U+00F7 and two control characters
UNLISTED = C1A9_1 + (0x200B, 0x00AD, 0xFEFF, 0x2060, 0x00A0, 0x3000, 0x2028, 0x0085, 0x202E, 0x0405, 0xFF33, 0x1F680,
                     0x00F7, 0x0001, 0x000C, 0x000B, 0x007F)


def u(code):
    return "U+%04X" % code


def with_b(lines, heading=SLICE_B, slice_a="signed off"):
    """vlib's doc with slice A only, then `heading`, slice B's first lines and `lines`, before the working records."""
    base = vlib.build_doc(slices=[("A", "the counter", slice_a)])
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join([heading] + B_BODY + list(lines)) + "\n" + base[at:]


def header(lines):
    return vlib.build_doc(extra_header=list(lines))


def number_of(text, line):
    return text.split("\n").index(line) + 1


def five_places(ch):
    """(what, doc, the line holding the character) for A16's five places: before a label, a base, a slice heading's
    name, a withheld heading's name and a `### Status:` heading's name. Without the character each doc reads plainly
    the way its shape intends; with it, 209c611's two readings were both blind to the hidden structure."""
    c = chr(ch)
    return [
        ("%s before Status: built in slice B" % u(ch), with_b(["", c + "Status: built", "", "Status: signed off"]),
         c + "Status: built"),
        ("%s before a header Base: line" % u(ch), header(["", c + "Base: 1234567"]), c + "Base: 1234567"),
        ("%s before Slice in slice B's heading" % u(ch), with_b(["Status: built"], heading="## %sSlice B %s the spinner"
                                                                % (c, D)), "## %sSlice B %s the spinner" % (c, D)),
        ("%s before Punch list in a withheld heading" % u(ch),
         with_b(["Status: signed off", "", "## %sPunch list" % c, "- LEAK-MARKER the builder says skim B"]),
         "## %sPunch list" % c),
        ("%s before Status: in a ### heading" % u(ch), with_b(["", "### %sStatus: built" % c, "", "Status: signed off"]),
         "### %sStatus: built" % c),
    ]


def c1a9_1_shapes():
    out = []
    for ch in C1A9_1:
        out += [(what, doc, line, ch) for what, doc, line in five_places(ch)]
    return out


# (1) the other stopping shapes: (what, doc, the line, the code point named)
PROSE_SHAPES = [
    ("a right-to-left override in plain prose", with_b(["The spinner turns %s left." % chr(0x202E), "",
                                                        "Status: signed off"]),
     "The spinner turns %s left." % chr(0x202E), 0x202E),
    ("a no-break space in plain prose", with_b(["The spinner%sturns." % chr(0xA0), "", "Status: signed off"]),
     "The spinner%sturns." % chr(0xA0), 0xA0),
    ("a Cyrillic letter in a slice heading", with_b(["Status: built"], heading="## %slice B %s the spinner"
                                                     % (chr(0x0405), D)),
     "## %slice B %s the spinner" % (chr(0x0405), D), 0x0405),
    ("full-width letters in a label", with_b(["", "%stATUS: built" % chr(0xFF33), "", "Status: signed off"]),
     "%stATUS: built" % chr(0xFF33), 0xFF33),
    ("full-width letters in a slice heading", with_b(["Status: built"], heading="## %s%slice B %s the spinner"
                                                     % (chr(0xFF33), chr(0xFF4C), D)),
     "## %s%slice B %s the spinner" % (chr(0xFF33), chr(0xFF4C), D), 0xFF33),
    ("full-width letters in plain prose", with_b(["The %s%s%s spinner." % (chr(0xFF21), chr(0xFF22), chr(0xFF23)), "",
                                                  "Status: signed off"]),
     "The %s%s%s spinner." % (chr(0xFF21), chr(0xFF22), chr(0xFF23)), 0xFF21),
    ("U+00F7 in plain prose", with_b(["Six %s two is three." % chr(0xF7), "", "Status: signed off"]),
     "Six %s two is three." % chr(0xF7), 0xF7),
    ("a byte order mark past the start of line 1", with_b(["The%sspinner." % chr(0xFEFF), "", "Status: signed off"]),
     "The%sspinner." % chr(0xFEFF), 0xFEFF),
    ("an emoji in a slice's goal", with_b(["Notes %s here." % chr(0x1F680), "", "Status: signed off"]),
     "Notes %s here." % chr(0x1F680), 0x1F680),
    ("a form feed in plain prose", with_b(["The spinner%sturns." % chr(0x0C), "", "Status: signed off"]),
     "The spinner%sturns." % chr(0x0C), 0x0C),
    ("a character outside the list in an indented code block, which is no accepted fence",
     with_b(["", "    code %s here" % chr(0x3164), "", "Status: signed off"]), "    code %s here" % chr(0x3164), 0x3164),
]

# (1) refusal (d): a character reference the CommonMark reader decodes to a character outside the list
REFERENCE_SHAPES = [
    ("a coded U+3164 before Status: built in slice B", with_b(["", "&#x3164;Status: built", "", "Status: signed off"]),
     "&#x3164;Status: built", 0x3164),
    ("a coded Cyrillic letter in a slice heading", with_b(["Status: built"], heading="## &#x405;lice B %s the spinner"
                                                         % D),
     "## &#x405;lice B %s the spinner" % D, 0x0405),
    ("a coded right-to-left override in plain prose", with_b(["The spinner &#8238; turns.", "", "Status: signed off"]),
     "The spinner &#8238; turns.", 0x202E),
    ("a coded U+034F before a header Base: line", header(["", "&#x34F;Base: 1234567"]), "&#x34F;Base: 1234567", 0x034F),
    ("a named reference to a no-break space before Status: built", with_b(["", "&nbsp;Status: built", "",
                                                                           "Status: signed off"]),
     "&nbsp;Status: built", None),
]

# (3) NFKC and case folding: (what, doc, the line)
FOLD_SHAPES = [
    ("a lower-case status: label above slice B's plain one", with_b(["", "status: built", "", "Status: signed off"]),
     "status: built"),
    ("an upper-case STATUS: label", with_b(["", "STATUS: built", "", "Status: signed off"]), "STATUS: built"),
    ("a space before the colon", with_b(["", "Status : built", "", "Status: signed off"]), "Status : built"),
    ("a tab before the colon", with_b(["", "Status\t: built", "", "Status: signed off"]), "Status\t: built"),
    ("slice B's only label in lower case", with_b(["", "status: signed off"]), "status: signed off"),
    ("a lower-case ### status: heading", with_b(["", "### status: built", "", "Status: signed off"]),
     "### status: built"),
    ("a ### Status : heading", with_b(["", "### Status : built", "", "Status: signed off"]), "### Status : built"),
    ("a lower-case base: line in the header", header(["", "base: 1234567"]), "base: 1234567"),
    ("a Base : line in the header", header(["", "Base : 1234567"]), "Base : 1234567"),
    ("a lower-case base: line after a list marker in the header", header(["", "- base: 1234567"]), "- base: 1234567"),
]

# (4) the withheld names: (what, heading, canonical)
WITHHELD_SHAPES = [
    ("Hand off as two words", "## Hand off", "## Handoffs"),
    ("Hand-offs with an en dash", "## Hand%soffs" % chr(0x2013), "## Handoffs"),
    ("a numbered Punch list", "## 1. Punch list", "## Punch list"),
    ("The punch list", "## The punch list", "## Punch list"),
    ("Build-assumptions", "## Build-assumptions", "## Build assumptions"),
    ("a numbered Deviations with a parenthesis", "## 2) Deviations", "## Deviations"),
    ("Hand_off with an underscore", "## Hand_off", "## Handoffs"),
    ("THE HANDOFFS in upper case", "## THE HANDOFFS", "## Handoffs"),
    ("Hand off with an em dash", "## Hand%soff" % D, "## Handoffs"),
]


def withheld_doc(heading, marker="NEARMISS-MARKER"):
    return with_b(["Status: signed off", "", heading, "- %s the builder says skim slice B" % marker])


def listed_doc():
    """Every listed character outside the printable ASCII range in plain prose, and the printable ASCII range in a
    line that opens like text: it runs."""
    listed = "".join(chr(c) for c in FIXED + ACCENTED)
    ascii_line = "Ascii " + "".join(chr(c) for c in range(0x20, 0x7F)) + "\tand a tab"
    return with_b(["Listed: %s." % listed, "", ascii_line, "", "Status: signed off"])


def fenced_doc(fence="```"):
    """Every listed and every unlisted character of `UNLISTED` inside an accepted fence: it runs."""
    listed = "".join(chr(c) for c in FIXED + ACCENTED)
    inside = ["Listed: %s" % listed] + ["%s %s inside" % (u(c), chr(c)) for c in UNLISTED] + \
             ["%sStatus: built" % chr(0x3164), "## %sPunch list" % chr(0x3164), "status: built"]
    return with_b(["", fence + "text " + chr(0x3164)] + inside + [fence, "", "Status: signed off"])


NOTES_FILES = {
    "notes/hidden.md": "# Bench%sguide\n\nHIDDEN-HEADING-MARKER the counter is obviously right\n" % chr(0x3164),
    "notes/emoji.md": "# Release %s notes\n\nEMOJI-HEADING-MARKER skim slice B\n" % chr(0x1F680),
    "notes/coded.md": "# Bench&#x3164;guide\n\nCODED-HEADING-MARKER skim slice B\n",
    "notes/opening.md": "# %sBuilder notes\n\nOPENING-HEADING-MARKER\n" % chr(0x3164),
    "notes/coded-opening.md": "# Builder&#x3164; notes\n\nCODED-OPENING-MARKER\n",
    "notes/lead.md": "%s# Builder notes\n\nLEAD-OPENING-MARKER\n" % chr(0x3164),
    "notes/curly.md": "# Builder%ss notes\n\nCURLY-NOTES-MARKER\n" % chr(0x2019),
    "notes/curly-left.md": "# Builder%ss notes\n\nCURLY-LEFT-MARKER\n" % chr(0x2018),
    "notes/README.md": "# Bench guide\n\nText.\n\n## %s Features\n\nDEEP-EMOJI-MARKER\n" % chr(0x1F680),
    "notes/shell.md": "Intro text.\n\n```sh\n# %s deploy\n```\n\n# Bench guide\n\nSHELL-SAMPLE-MARKER\n" % chr(0x1F680),
    "notes/later.md": "# Bench guide\n\nText.\n\n## Later %s part\n\nLATER-HEADING-MARKER\n" % chr(0x2800),
    "README.md": "# Turnstile\n\nA bench-rig turn counter, PLAIN-README-MARKER.\n",
}
# withheld: path -> what its withheld entry's reason names
NOTES_WITHHELD = {"notes/hidden.md": u(0x3164), "notes/emoji.md": u(0x1F680), "notes/coded.md": u(0x3164),
                  "notes/opening.md": u(0x3164), "notes/coded-opening.md": u(0x3164), "notes/lead.md": u(0x3164),
                  "notes/curly.md": "first heading", "notes/curly-left.md": "first heading"}
# included as ordinary files: a heading past the first certain one, or a fenced sample, holding an unlisted character
NOTES_INCLUDED = ("README.md", "notes/README.md", "notes/shell.md", "notes/later.md")
NOTES_MARKERS = ("HIDDEN-HEADING-MARKER", "EMOJI-HEADING-MARKER", "CODED-HEADING-MARKER", "OPENING-HEADING-MARKER",
                 "CODED-OPENING-MARKER", "LEAD-OPENING-MARKER", "CURLY-NOTES-MARKER", "CURLY-LEFT-MARKER")


class TheList(unittest.TestCase):

    def test_the_code_holds_exactly_the_list_a16_rules(self):
        expected = set(chr(c) for c in range(0x20, 0x7F)) | {"\t"} | set(chr(c) for c in FIXED + ACCENTED)
        self.assertEqual(set(fences.LISTED), expected)

    def test_the_contract_states_the_same_list(self):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index("**The character list**")
        para = text[start:text.index("\n\n", start)]
        ranges = re.findall(r"U\+([0-9A-F]{4}) to U\+([0-9A-F]{4})", para)
        excepted = re.findall(r"except U\+([0-9A-F]{4})", para)
        stated = set()
        for first, last in ranges:
            stated |= set(chr(c) for c in range(int(first, 16), int(last, 16) + 1))
        stated -= set(chr(int(c, 16)) for c in excepted)
        bounds = set(c for pair in ranges for c in pair) | set(excepted)
        stated |= set(chr(int(c, 16)) for c in re.findall(r"U\+([0-9A-F]{4})", para) if c not in bounds)
        stated |= {"\t"}
        self.assertEqual(stated, set(fences.LISTED))


class TheReadings(unittest.TestCase):

    def assert_stops(self, what, text, line, code):
        number = number_of(text, line)
        for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base), ("spec", spec.clean)):
            with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                call(text)
            self.assertEqual(caught.exception.line, number, (what, name, str(caught.exception)))
            if code is not None:
                self.assertIn(u(code), caught.exception.what, (what, name))

    def test_every_c1a9_1_character_in_every_place_stops_every_reader_naming_it_and_its_line(self):
        for what, text, line, code in c1a9_1_shapes():
            with self.subTest(shape=what):
                self.assert_stops(what, text, line, code)

    def test_without_the_character_each_place_reads_as_its_shape_intends(self):
        """The controls: the five places with the character taken out each read plainly (a second label stops, a
        recorded base, a slice B, a withheld section, a label heading that stops), so the stop above is the list's."""
        plain = dict((what.split(" ", 1)[1], doc.replace(chr(0x3164), "")) for what, doc, line in five_places(0x3164))
        self.assertRaises(spec.SpecUnreadable, spec.read, plain["before Status: built in slice B"])
        self.assertEqual(gatemod.recorded_base(plain["before a header Base: line"])["commit"], "1234567")
        self.assertEqual([s["name"] for s in gatemod.slices_of(plain["before Slice in slice B's heading"])], ["A", "B"])
        kept, removed = spec.clean(plain["before Punch list in a withheld heading"])
        self.assertNotIn("LEAK-MARKER", kept)
        self.assertRaises(spec.SpecUnreadable, spec.read, plain["before Status: in a ### heading"])

    def test_every_other_unlisted_shape_stops_every_reader_naming_it_and_its_line(self):
        for what, text, line, code in PROSE_SHAPES:
            with self.subTest(shape=what):
                self.assert_stops(what, text, line, code)

    def test_a_character_reference_to_an_unlisted_character_stops_every_reader(self):
        for what, text, line, code in REFERENCE_SHAPES:
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                self.assert_stops(what, text, line, code)

    def test_every_listed_character_in_plain_prose_runs(self):
        text = listed_doc()
        self.assertEqual(fences.read(text).problems, [])
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                         [("A", "signed off"), ("B", "signed off")])
        kept, removed = spec.clean(text)
        self.assertIn("".join(chr(c) for c in FIXED + ACCENTED), kept)

    def test_line_endings_a_tab_and_a_leading_byte_order_mark_run(self):
        text = listed_doc()
        for what, variant in (("CRLF", text.replace("\n", "\r\n")), ("CR", text.replace("\n", "\r")),
                              ("a byte order mark at the start of line 1", chr(0xFEFF) + text),
                              ("a tab inside a line", text.replace("Goal: one sentence", "Goal:\tone sentence"))):
            with self.subTest(shape=what):
                self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(variant)],
                                 [("A", "signed off"), ("B", "signed off")], what)
                spec.clean(variant)

    def test_every_listed_and_unlisted_character_inside_a_fence_runs(self):
        for fence in ("```", "~~~~"):
            with self.subTest(fence=fence):
                text = fenced_doc(fence)
                self.assertEqual(fences.read(text).problems, [], fence)
                self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                                 [("A", "signed off"), ("B", "signed off")])
                kept, removed = spec.clean(text)
                self.assertIn("%s %s inside" % (u(0x3164), chr(0x3164)), kept)

    def test_every_fold_shape_stops_every_reader_naming_its_line(self):
        for what, text, line in FOLD_SHAPES:
            with self.subTest(shape=what):
                self.assert_stops(what, text, line, None)

    def test_a_folded_status_line_outside_every_slice_is_removed_from_the_spec(self):
        text = with_b(["Status: signed off", "", "## Notes", "", "status: STATUS-FOLD-MARKER draft", "",
                       "Status : SPACED-FOLD-MARKER draft"])
        kept, removed = spec.clean(text)
        for marker in ("STATUS-FOLD-MARKER", "SPACED-FOLD-MARKER"):
            self.assertNotIn(marker, kept)
        for line in ("status: STATUS-FOLD-MARKER draft", "Status : SPACED-FOLD-MARKER draft"):
            at = number_of(text, line)
            self.assertIn({"what": "Status: line", "lines": [at, at]}, removed)

    def test_every_withheld_name_shape_is_withheld_and_named_the_same_in_both_readings(self):
        for what, heading, canonical in WITHHELD_SHAPES:
            with self.subTest(shape=what):
                text = withheld_doc(heading)
                self.assertIsNone(readings.difference(text), what)
                doc = fences.read(text)
                second = readings.second_reading(text, len(doc.lines))
                first = number_of(text, heading)
                self.assertEqual(second["withheld"].get(first, (None,))[0], canonical, (what, second["withheld"]))
                kept, removed = spec.clean(text)
                self.assertNotIn("NEARMISS-MARKER", kept, what)
                self.assertIn({"what": canonical, "lines": [first, first + 2]}, removed, (what, removed))

    def test_a_heading_that_only_resembles_a_withheld_name_stays(self):
        for heading in ("## Theory of the counter", "## Handover", "## Builds and assumptions"):
            with self.subTest(heading=heading):
                kept, removed = spec.clean(withheld_doc(heading, marker="KEPT-MARKER"))
                self.assertIn("KEPT-MARKER", kept, heading)

    def test_a_bare_leading_number_is_numbering_since_a17(self):
        """A17 (2) drops any leading numbering, a bare number such as `1` included, so `## 10 punches` (a control
        under A16, which dropped only `1.` and `2)`) now reads `punches` and is withheld as the punch list; a wider
        match only ever withholds more."""
        text = withheld_doc("## 10 punches", marker="NUMBERED-MARKER")
        kept, removed = spec.clean(text)
        self.assertNotIn("NUMBERED-MARKER", kept)
        first = number_of(text, "## 10 punches")
        self.assertIn({"what": "## Punch list", "lines": [first, first + 2]}, removed)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every stopping shape through the real CLI, records off and on: exit 10, `doc-unreadable` naming the line (and
    the code point), no `ask.json`, no request file, no `packets`; the running shapes pass the gate."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vchars-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records, extra=None):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count,
                                  extra_build_files=extra)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def assert_unreadable(self, what, code, out, err, run_dir, needles):
        self.assertEqual(code, 10, (what, out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), (what, out))
        for needle in needles:
            self.assertIn(needle, out["reason"], what)
        for name in ("ask.json", "requests-local.json", "packets", "scope.json"):
            self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))

    def test_every_c1a9_1_character_in_every_place_stops_the_gate(self):
        for what, doc, line, code in c1a9_1_shapes():
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code_, out, err, run_dir = self.gate(doc, records)
                    self.assert_unreadable(what, code_, out, err, run_dir, ("line %d" % number_of(doc, line), u(code)))

    def test_every_other_stopping_shape_stops_the_gate(self):
        for what, doc, line, code in PROSE_SHAPES + REFERENCE_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code_, out, err, run_dir = self.gate(doc, records)
                    needles = ("line %d" % number_of(doc, line),) + ((u(code),) if code is not None else ())
                    self.assert_unreadable(what, code_, out, err, run_dir, needles)

    def test_every_fold_shape_stops_the_gate(self):
        for what, doc, line in FOLD_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assert_unreadable(what, code, out, err, run_dir, ("line %d" % number_of(doc, line),))

    def test_the_running_shapes_pass_the_gate(self):
        for what, doc in (("every listed character in plain prose", listed_doc()),
                          ("every listed and unlisted character inside a fence", fenced_doc()),
                          ("a withheld name shape", withheld_doc("## 1. Punch list"))):
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 0, (what, out, err))
                    self.assertEqual(out["next"], "ask", what)

    def test_a_notes_candidate_never_stops_the_gate(self):
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate(None, records, extra=dict(NOTES_FILES))
                self.assertEqual(code, 0, (out, err))


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vchars-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

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

    def scope_only_in_the_commit(self, doc, records):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count,
                                    owner_words={"committed_only": "review the committed state only"})
        code, out, err = vlib.through_ask(drive, self.tmp, run_dir)
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["scope", "--run-dir", run_dir])
        return code, out, err, run_dir

    def assert_scope_stops(self, what, code, out, err, run_dir, needles):
        self.assertEqual(code, 10, (what, out, err))
        self.assertEqual(out["stop_tag"], "doc-unreadable", what)
        for needle in needles:
            self.assertIn(needle, out["reason"], what)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)

    def test_scope_stops_on_every_c1a9_1_character_in_every_place_only_in_the_commit(self):
        for what, doc, line, code in c1a9_1_shapes():
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code_, out, err, run_dir = self.scope_only_in_the_commit(doc, records)
                    self.assert_scope_stops(what, code_, out, err, run_dir, ("line %d" % number_of(doc, line), u(code)))

    def test_scope_stops_on_the_other_shapes_only_in_the_commit(self):
        for what, doc, line, code in (PROSE_SHAPES[0], PROSE_SHAPES[1], PROSE_SHAPES[2], PROSE_SHAPES[3],
                                      REFERENCE_SHAPES[0]):
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code_, out, err, run_dir = self.scope_only_in_the_commit(doc, records)
                    self.assert_scope_stops(what, code_, out, err, run_dir, ("line %d" % number_of(doc, line), u(code)))
        for what, doc, line in FOLD_SHAPES[:3] + FOLD_SHAPES[5:7]:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code_, out, err, run_dir = self.scope_only_in_the_commit(doc, records)
                    self.assert_scope_stops(what, code_, out, err, run_dir, ("line %d" % number_of(doc, line),))

    def test_every_withheld_name_shape_reaches_no_packet_and_is_named(self):
        for index, (what, heading, canonical) in enumerate(WITHHELD_SHAPES[:5]):
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

    def test_a_heading_holding_an_unlisted_character_withholds_its_file_and_names_it(self):
        for records in (False, True):
            with self.subTest(records=records):
                drive, run_dir, ws, info = vlib.through_scope(
                    os.path.join(self.tmp, "n%d" % records),
                    repo={"extra_build_files": dict(NOTES_FILES), "records": records})
                for marker in NOTES_MARKERS:
                    self.assert_absent(run_dir, marker)
                for packet_dir in self.packets(run_dir):
                    whys = dict((w["what"], w["why"]) for w in self.withheld(packet_dir))
                    for path, needle in sorted(NOTES_WITHHELD.items()):
                        self.assertIn(needle, whys.get(path, ""), (packet_dir, path, whys.get(path)))
                    listing = testlib.load_json(os.path.join(packet_dir, "files.json"))["files"]
                    paths = [entry.get("source") or entry["path"] for entry in listing]
                    for path in NOTES_INCLUDED:
                        self.assertNotIn(path, whys, (packet_dir, path))
                        self.assertIn(path, paths, (packet_dir, path))


class TheNotesCandidates(unittest.TestCase):
    """(2) through the one packet builder, driven directly."""

    def test_each_heading_holding_an_unlisted_character_is_withheld_and_named_and_a_plain_readme_kept(self):
        tmp = testlib.make_scratch("vchars-notes-")
        self.addCleanup(testlib.rmtree, tmp)
        ws, info = vlib.make_repo(tmp, extra_build_files=dict(NOTES_FILES))
        snap = packet.Snapshot(ws, info["head"], vlib.DOC)
        whys = dict((item["what"], item["why"]) for item in snap.left)
        for path, needle in sorted(NOTES_WITHHELD.items()):
            self.assertIn(needle, whys.get(path, ""), (path, whys.get(path)))
            self.assertNotIn(path, snap.tree)
        for path in NOTES_INCLUDED:
            self.assertIn(path, snap.tree, path)
            self.assertNotIn(path, whys, path)

    def test_the_heading_lines_read_are_the_declaration_tests_own(self):
        """Send-back 1: both legs read only the heading lines the declaration test reads; the curly apostrophe is `'`
        to the declaration test in both readings, so the two readings agree on it."""
        from vertical_core import notes  # noqa: E402
        for path in ("notes/README.md", "notes/shell.md", "notes/later.md"):
            self.assertIsNone(readings.notes_unlisted(NOTES_FILES[path]), path)
        for path in ("notes/hidden.md", "notes/emoji.md", "notes/coded.md", "notes/opening.md",
                     "notes/coded-opening.md", "notes/lead.md"):
            self.assertIsNotNone(readings.notes_unlisted(NOTES_FILES[path]), path)
        for path in ("notes/curly.md", "notes/curly-left.md"):
            self.assertIsNotNone(notes.declares(NOTES_FILES[path]), path)
            self.assertIsNone(readings.notes_difference(NOTES_FILES[path]), path)
            self.assertIsNone(readings.notes_unlisted(NOTES_FILES[path]), path)


if __name__ == "__main__":
    unittest.main()
