"""Round 11 of class (a): folded letters, wider withheld names, notes read with spaces (the E15 lane contract A17;
contract section 5, "Exact labels", "Two readings", "The spec" and "A notes file declared by its first heading").

(1) Every fold a label, slice-heading or withheld-name test uses is NFKD with the combining marks removed, then NFKC,
then case folding (`fences.fold`), and refusal (b)'s `slice` test sets aside leading punctuation and symbols first. So
an accented letter the character list admits (`## Sl` U+00EF `ce B`, `St` U+00E4 `tus: built`, `B` U+00E4 `se:`) or a
leading curly quote (`## ` U+2018 `Slice B`) no longer hides a slice heading, a label or a base from both readings:
each stops `doc-unreadable` at its line, before any ask, request or packet. An accented letter in ordinary prose
runs, and a plain `Status: built` still stops `gate-short`.
(2) The withheld-name key reads U+2212, U+00B7, U+2018 and U+2019 as spaces besides hyphens, dashes and underscores,
drops any leading numbering (`1`, `1.`, `1.1`, `2)`, `(1)`, `A.`) besides a leading `the`, and its stems also match
`build assumption` and `builder assumption` with or without the space; no contains rule (A17 rejects it), so
`## Open punch list` stays an ordinary section (a carried item).
(3) `notes.unlisted_heading` reads each candidate line three ways (as written, the characters outside the list
removed, the characters outside the list read as spaces) and tests a Setext candidate's underline line too, so a
notes file whose first heading is `#`, an unlisted space-like character, then `Builder notes`, or `Builder notes` over
an underline holding an unlisted character, is a notes candidate: withheld and named, never a stop.

`TheFold` and `TheNames` and `TheNotes` drive the readers directly; `TheGate` drives the shapes through the real CLI,
records off and on; `TheScope` drives them through `scope`, the stopping shapes only in the reviewed commit, records
off and on, and the withheld names and the notes files to every packet, the outside packet included.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, notes, packet, readings, spec  # noqa: E402

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


def u(code):
    return "U+%04X" % code


# (1) the folded shapes: (what, doc, the line the stop names)
SLICE_LETTERS = (0x00EF, 0x00EC, 0x00E9, 0x00E7)


def folded_slice_heading(code):
    word = {0x00EF: "Sl%sce", 0x00EC: "Sl%sce", 0x00E9: "Slic%s", 0x00E7: "Sli%se"}[code] % chr(code)
    return "## %s B %s the spinner" % (word, D)


FOLD_SHAPES = [("a slice heading spelled with %s over Status: built" % u(code),
                with_b(["Status: built"], heading=folded_slice_heading(code)), folded_slice_heading(code))
               for code in SLICE_LETTERS] + [
    ("a slice heading after a left curly quote (U+2018) over Status: built",
     with_b(["Status: built"], heading="## ‘Slice B %s the spinner" % D), "## ‘Slice B %s the spinner" % D),
    ("a slice heading in curly quotes over Status: built",
     with_b(["Status: built"], heading="## ‘Slice B’ %s the spinner" % D),
     "## ‘Slice B’ %s the spinner" % D),
    ("Stätus: built above the plain Status: signed off",
     with_b(["", "Stätus: built", "", "Status: signed off"]), "Stätus: built"),
    ("Bäse: 1234567 in the header", header(["", "Bäse: 1234567"]), "Bäse: 1234567"),
]

# (2) the withheld names: (what, heading, canonical)
NAME_SHAPES = [
    ("Hand-offs joined by a minus sign (U+2212)", "## Hand−offs", "## Handoffs"),
    ("Hand-offs joined by a middle dot (U+00B7)", "## Hand·offs", "## Handoffs"),
    ("Hand-offs joined by a right curly quote (U+2019)", "## Hand’offs", "## Handoffs"),
    ("Handoffs with an accented a (U+00E0)", "## Hàndoffs", "## Handoffs"),
    ("Punch list with an umlaut (U+00FC)", "## Pünch list", "## Punch list"),
    ("a bare number before Punch list", "## 1 Punch list", "## Punch list"),
    ("a dotted number before Punch list", "## 1.1 Punch list", "## Punch list"),
    ("a parenthesized number before Punch list", "## (1) Punch list", "## Punch list"),
    ("a letter with a dot before Punch list", "## A. Punch list", "## Punch list"),
    ("Buildassumptions as one word", "## Buildassumptions", "## Build assumptions"),
    ("Builder assumptions", "## Builder assumptions", "## Build assumptions"),
]
# not withheld: ordinary sections, and the carried `## Open punch list` (A17 adopts no contains rule)
NAME_CONTROLS = ("## Theory", "## Handy offsets", "## A note on punctuation", "## Open punch list")


def withheld_doc(heading, marker="A17-NAME-MARKER"):
    return with_b(["Status: signed off", "", heading, "- %s the builder says skim slice B" % marker])


# (3) the notes files: path -> (text, the line the candidate is named at, the character named)
NOTES_SHAPES = {
    "notes/nbsp.md": ("# Builder notes\n\nA17-NBSP-MARKER skim slice B\n", 1, 0x00A0),
    "notes/filler.md": ("#ㅤBuilder notes\n\nA17-FILLER-MARKER skim slice B\n", 1, 0x3164),
    "notes/em-space.md": ("# Builder notes\n\nA17-EMSPACE-MARKER skim slice B\n", 1, 0x2003),
    "notes/ideographic.md": ("#　Builder notes\n\nA17-IDEOGRAPHIC-MARKER skim slice B\n", 1, 0x3000),
    "notes/zwsp.md": ("#​Builder notes\n\nA17-ZWSP-MARKER skim slice B\n", 1, 0x200B),
    "notes/underline-after.md": ("Builder notes\n===ㅤ\n\nA17-UNDERLINE-AFTER-MARKER skim slice B\n", 2, 0x3164),
    "notes/underline-before.md": ("Builder notes\n　===\n\nA17-UNDERLINE-BEFORE-MARKER skim slice B\n", 2, 0x3000),
}
NOTES_KEPT = {"notes/guide.md": "# Bench guide\n\nA17-GUIDE-KEPT the counter's wiring.\n",
              "notes/underlined.md": "Bench guide\n===\n\nA17-UNDERLINED-KEPT the spinner's wiring.\n"}


def marker_of(text):
    return next(word for word in text.split() if word.startswith("A17-"))


class TheFold(unittest.TestCase):

    def test_the_fold_drops_the_marks_of_the_listed_letters(self):
        for code in range(0xC0, 0x100):
            if code in (0xD7, 0xF7):
                continue
            with self.subTest(code=u(code)):
                folded = fences.fold(chr(code))
                self.assertFalse(any(0x300 <= ord(c) <= 0x36F for c in folded), (u(code), folded))
        self.assertEqual(fences.fold("Stätus"), "status")
        self.assertEqual(fences.fold("SLÏCE"), "slice")
        self.assertEqual(fences.fold("Straße"), "strasse")

    def assert_stops(self, what, text, line):
        number = number_of(text, line)
        for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base), ("spec", spec.clean)):
            with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                call(text)
            self.assertEqual(caught.exception.line, number, (what, name, str(caught.exception)))

    def test_every_folded_shape_stops_every_reader_at_its_line(self):
        for what, text, line in FOLD_SHAPES:
            with self.subTest(shape=what):
                self.assertTrue(all(fences.unlisted(row) is None for row in text.split("\n")), what)
                self.assert_stops(what, text, line)

    def test_an_accented_letter_in_ordinary_prose_runs(self):
        text = with_b(["The café spinner turns naïvely, À la façade.", "", "Status: signed off"])
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                         [("A", "signed off"), ("B", "signed off")])
        kept, removed = spec.clean(text)
        self.assertIn("café spinner", kept)

    def test_a_level_3_note_after_a_quote_is_not_touched(self):
        text = with_b(["", "### ‘Slice D’ notes, 2026-09-25", "", "Status: signed off"])
        self.assertEqual([s["name"] for s in gatemod.slices_of(text)], ["A", "B"])


class TheNames(unittest.TestCase):

    def test_every_name_shape_is_withheld_and_named_the_same_in_both_readings(self):
        for what, heading, canonical in NAME_SHAPES:
            with self.subTest(shape=what):
                text = withheld_doc(heading)
                self.assertIsNone(readings.difference(text), what)
                doc = fences.read(text)
                self.assertEqual(doc.problems, [], what)
                first = number_of(text, heading)
                second = readings.second_reading(text, len(doc.lines))
                self.assertEqual(second["withheld"].get(first, (None,))[0], canonical, (what, second["withheld"]))
                self.assertEqual([s[:3] for s in spec.sections(doc) if s[1] == first], [(canonical, first, first + 2)],
                                 what)
                kept, removed = spec.clean(text)
                self.assertNotIn("A17-NAME-MARKER", kept, what)
                self.assertIn({"what": canonical, "lines": [first, first + 2]}, removed, (what, removed))

    def test_the_controls_are_not_withheld(self):
        for heading in NAME_CONTROLS:
            with self.subTest(heading=heading):
                self.assertIsNone(spec.withheld_of(heading[3:]), heading)
                kept, removed = spec.clean(withheld_doc(heading, marker="A17-KEPT-MARKER"))
                self.assertIn("A17-KEPT-MARKER", kept, heading)


class TheNotes(unittest.TestCase):

    def test_each_shape_is_a_notes_candidate_named_at_its_line(self):
        for path, (text, line, code) in sorted(NOTES_SHAPES.items()):
            with self.subTest(path=path):
                self.assertEqual(readings.notes_unlisted(text), (line, chr(code)), path)

    def test_the_plain_files_are_not(self):
        for path, text in sorted(NOTES_KEPT.items()):
            with self.subTest(path=path):
                self.assertIsNone(readings.notes_unlisted(text), path)
                self.assertIsNone(notes.declares(text), path)

    def test_the_one_packet_builder_withholds_and_names_each_and_keeps_the_plain_files(self):
        tmp = testlib.make_scratch("vfold-notes-")
        self.addCleanup(testlib.rmtree, tmp)
        files = dict((path, text) for path, (text, line, code) in NOTES_SHAPES.items())
        files.update(NOTES_KEPT)
        ws, info = vlib.make_repo(tmp, extra_build_files=files)
        snap = packet.Snapshot(ws, info["head"], vlib.DOC)
        whys = dict((item["what"], item["why"]) for item in snap.left)
        for path, (text, line, code) in sorted(NOTES_SHAPES.items()):
            self.assertIn(u(code), whys.get(path, ""), (path, whys.get(path)))
            self.assertIn("line %d" % line, whys.get(path, ""), (path, whys.get(path)))
            self.assertNotIn(path, snap.tree)
        for path in NOTES_KEPT:
            self.assertIn(path, snap.tree, path)
            self.assertNotIn(path, whys, path)


class TheStatement(unittest.TestCase):
    """Each rule stated once in code and once in the contract, the two held together."""

    def paragraph(self, title):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index(title)
        return " ".join(text[start:text.index("\n\n", start)].split())

    def test_the_fold_is_stated_in_the_contract(self):
        para = self.paragraph("**The fold**")
        for words in ("NFKD normalization", "combining mark (Unicode category M) removed", "NFKC normalization",
                      "case folding", "refusal (b)", "withheld-name"):
            self.assertIn(words, para)

    def test_the_withheld_name_rule_names_every_stem_and_every_joiner(self):
        from vertical_core import spec as specmod  # noqa: E402
        para = self.paragraph("**The spec**")
        for stem, canonical in specmod.STEMS:
            self.assertIn("`%s`" % stem, para, stem)
        for code in (0x2212, 0x00B7, 0x2018, 0x2019):
            self.assertIn(u(code), para)
            self.assertEqual(specmod.name_key("Hand%soffs" % chr(code)), "hand offs", u(code))   # A18 (2): P, S, Z
        for numbering in ("`1`", "`1.`", "`1.1`", "`2)`", "`(1)`", "`A.`"):
            self.assertIn(numbering, para)

    def test_refusal_b_and_the_notes_scan_are_stated_in_the_contract(self):
        self.assertIn("leading punctuation, symbols and spaces (Unicode categories P, S and Z) set aside",
                      self.paragraph("**The CommonMark reading's four refusals**"))
        para = self.paragraph("**A notes file declared by its first heading**")
        self.assertIn("its underline line", para)
        self.assertIn("read as spaces", para)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every folded shape through the real CLI, records off and on: exit 10, `doc-unreadable` naming the line, no
    `ask.json`, no request file, no `packets`; the controls and the notes files pass or stop as they did."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vfold-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records, extra=None):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count,
                                  extra_build_files=extra)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def test_every_folded_shape_stops_the_gate_at_its_line(self):
        for what, doc, line in FOLD_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 10, (what, out, err))
                    self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), (what, out))
                    self.assertIn("line %d" % number_of(doc, line), out["reason"], what)
                    for name in ("ask.json", "requests-local.json", "packets", "scope.json"):
                        self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))

    def test_a_plain_built_slice_still_stops_gate_short(self):
        for records in (False, True):
            with self.subTest(records=records):
                code, out, err, run_dir = self.gate(with_b(["Status: built"]), records)
                self.assertEqual(code, 10, (out, err))
                self.assertEqual(out["stop_tag"], "gate-short", out)
                self.assertFalse(os.path.lexists(os.path.join(run_dir, "ask.json")))

    def test_an_accented_letter_in_prose_and_the_withheld_names_and_the_notes_files_pass_the_gate(self):
        notes_files = dict((path, text) for path, (text, line, code) in NOTES_SHAPES.items())
        for what, doc, extra in (
                ("an accented letter in prose",
                 with_b(["The café spinner turns naïvely.", "", "Status: signed off"]), None),
                ("a withheld name", withheld_doc("## (1) Punch list"), None),
                ("the notes files", None, notes_files)):
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records, extra=extra)
                    self.assertEqual(code, 0, (what, out, err))
                    self.assertEqual(out["next"], "ask", what)


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vfold-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def packets(self, run_dir):
        root = os.path.join(run_dir, "packets")
        names = sorted(os.listdir(root))
        self.assertTrue(any(name.startswith("outside-") for name in names), names)
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

    def test_scope_stops_on_every_folded_shape_only_in_the_commit(self):
        for what, doc, line in FOLD_SHAPES:
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
        for index, (what, heading, canonical) in enumerate(NAME_SHAPES):
            with self.subTest(shape=what):
                doc = withheld_doc(heading)
                drive, run_dir, ws, info = vlib.through_scope(os.path.join(self.tmp, "w%d" % index),
                                                              repo={"doc_text": doc})
                self.assert_absent(run_dir, "A17-NAME-MARKER")
                first = number_of(doc, heading)
                for packet_dir in self.packets(run_dir):
                    entries = [w for w in self.withheld(packet_dir) if w["what"] == "%s %s" % (vlib.DOC, canonical)]
                    self.assertTrue(any("lines %d to %d" % (first, first + 2) in w["why"] for w in entries),
                                    (what, packet_dir, entries))

    def test_every_notes_shape_reaches_no_packet_and_is_named(self):
        files = dict((path, text) for path, (text, line, code) in NOTES_SHAPES.items())
        files.update(NOTES_KEPT)
        for records in (False, True):
            with self.subTest(records=records):
                drive, run_dir, ws, info = vlib.through_scope(os.path.join(self.tmp, "n%d" % records),
                                                              repo={"extra_build_files": files, "records": records})
                for path, (text, line, code) in sorted(NOTES_SHAPES.items()):
                    self.assert_absent(run_dir, marker_of(text))
                for packet_dir in self.packets(run_dir):
                    whys = dict((w["what"], w["why"]) for w in self.withheld(packet_dir))
                    for path, (text, line, code) in sorted(NOTES_SHAPES.items()):
                        self.assertIn(u(code), whys.get(path, ""), (packet_dir, path, whys.get(path)))
                    listing = testlib.load_json(os.path.join(packet_dir, "files.json"))["files"]
                    paths = [entry.get("source") or entry["path"] for entry in listing]
                    for path in NOTES_KEPT:
                        self.assertNotIn(path, whys, (packet_dir, path))
                        self.assertIn(path, paths, (packet_dir, path))


if __name__ == "__main__":
    unittest.main()
