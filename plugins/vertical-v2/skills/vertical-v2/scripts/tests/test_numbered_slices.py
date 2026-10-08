"""Round 14 (2): the numbered slice style refused (the E15 lane contract A21 (2); Astra's look 4, its MAJOR; contract
section 5, "Two readings", refusal (b)).

Refusal (b) also refuses a heading of level 1 or 2 whose folded name, behind its numbering and at most one word ending
in a colon (A20's reading, `readings.behind_numbering` and `readings.LABEL_WORD`), reads `slice <name>` ending the
name, or followed by a colon or a dash (a hyphen or U+2010 to U+2015, spaced or not), unless it is an exact slice
heading. So `## 2. Slice B`, `## Next: Slice B`, `## 2. Slice B: beta`, `## 2. Slice B - beta` and `## 7. Slice 1: the
frame` stop at the heading, over no `Status:` line yet and over a label only the rendered text shows
(`**Status:** built`). Level 3 is not widened: `### 7.1 Slice 1: the frame` runs. A heading that only mentions a slice
later in its name (`## Notes on slice A <dash> what we learned`) and an exact `## Slice B <dash> x` run.

`TheReaders` drives the readers directly; `TheGate` drives every shape through the real CLI, records off and on;
`TheScope` drives the stopping shapes through `scope` (only in the reviewed commit), records off and on.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, readings, spec  # noqa: E402

D = vlib.D
B_BODY = ["Goal: one sentence about the spinner.", "Depends on: nothing"]


def with_b(lines, heading, slice_a="signed off"):
    """vlib's doc with slice A only, then `heading`, slice B's first lines and `lines`, before the working records."""
    base = vlib.build_doc(slices=[("A", "the counter", slice_a)])
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join([heading] + B_BODY + list(lines)) + "\n" + base[at:]


def number_of(text, line):
    return text.split("\n").index(line) + 1


HEADS = ("## 2. Slice B", "## Next: Slice B", "## 2. Slice B: beta", "## 2. Slice B - beta", "## 7. Slice 1: the frame")
UNDER = (("no Status: line", []), ("**Status:** built", ["**Status:** built"]))
# (what, doc, the line the stop names)
STOP_SHAPES = [("%s over %s" % (heading, label), with_b(lines, heading), heading)
               for heading in HEADS for label, lines in UNDER]
# (what, doc): each runs, slices A and B both signed off
RUN_SHAPES = [
    ("## Notes on slice A %s what we learned" % D,
     with_b(["Status: signed off", "", "## Notes on slice A %s what we learned" % D, "A note on the day."],
            "## Slice B %s the spinner" % D)),
    ("### 7.1 Slice 1: the frame (level 3)",
     with_b(["", "### 7.1 Slice 1: the frame", "A note on the frame.", "", "Status: signed off"],
            "## Slice B %s the spinner" % D)),
    ("an exact ## Slice B %s x" % D, with_b(["Status: signed off"], "## Slice B %s x" % D)),
]


class TheReaders(unittest.TestCase):

    def test_every_shape_stops_every_reader_at_its_heading(self):
        for what, text, line in STOP_SHAPES:
            with self.subTest(shape=what):
                self.assertTrue(all(fences.unlisted(row) is None for row in text.split("\n")), what)
                number = number_of(text, line)
                for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base),
                                   ("spec", spec.clean)):
                    with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                        call(text)
                    self.assertEqual(caught.exception.line, number, (what, name, str(caught.exception)))
                    self.assertIn("reads like a slice heading", str(caught.exception), (what, name))

    def test_every_control_runs_with_both_slices(self):
        for what, text in RUN_SHAPES:
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                                 [("A", "signed off"), ("B", "signed off")], what)
                spec.clean(text)

    def test_the_rule_by_level_and_shape(self):
        refused = ("2. Slice B", "Next: Slice B", "2. Slice B: beta", "2. Slice B - beta", "7. Slice 1: the frame",
                   "2. Slice B:beta", "2. Slice B -beta", "2. Slice B- beta", "2. Slice B-beta", "2. Slice B -",
                   "2) Slice B", "(2) Slice B", "B. Slice B", "Next: Slice B: beta", "1.1 Slice B: beta",
                   "²Slice B", "2. Slice B :")
        dashes = ["2. Slice B %s beta" % chr(code) for code in range(0x2010, 0x2016)]
        dashes += ["2. Slice B%sbeta" % chr(code) for code in range(0x2010, 0x2016)]
        for name in refused + tuple(dashes):
            for level in (1, 2):
                with self.subTest(name=name, level=level):
                    self.assertTrue(readings.slice_form(level, name), (name, level))
            with self.subTest(name=name, level=3):
                self.assertEqual(readings.slice_form(3, name), D in name and " %s " % D in name, name)
            self.assertFalse(readings.slice_form(4, name), name)
        for name in ("Notes on slice A %s what we learned" % D, "2. Slice B notes", "2. Slices overview",
                     "2. Slice B (beta)", "Next: then: Slice B", "2. Sliced bread", "Notes: slice B is late"):
            for level in (1, 2, 3):
                with self.subTest(name=name, level=level):
                    self.assertFalse(readings.slice_form(level, name), (name, level))
        self.assertFalse(readings.slice_form(2, "Slice B %s x" % D))


class TheStatement(unittest.TestCase):
    """The rule stated once in code and once in the contract."""

    WORDS = ("A21 (2)", "`slice <name>` ending the name", "a colon or a dash", "U+2010 to U+2015",
             "Level 3 is not widened")

    def test_the_rule_is_stated_in_the_contract(self):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index("**The CommonMark reading's four refusals**")
        para = " ".join(text[start:text.index("\n\n", start)].split())
        for words in self.WORDS:
            self.assertIn(words, para)

    def test_the_rule_is_stated_in_the_code(self):
        doc = " ".join(readings.__doc__.split())
        for words in self.WORDS:
            self.assertIn(words, doc)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every shape through the real CLI, records off and on: a stopping shape exits 10, `doc-unreadable` naming the
    heading, no `ask.json`, no request file, no `packets`; a control passes to the ask."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vnumbered-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def gate(self, doc, records):
        self.count += 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        return code, out, err, run_dir

    def test_every_stopping_shape_stops_the_gate_at_its_heading(self):
        for what, doc, line in STOP_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 10, (what, out, err))
                    self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), (what, out))
                    self.assertIn("line %d" % number_of(doc, line), out["reason"], what)
                    for name in ("ask.json", "requests-local.json", "packets", "scope.json"):
                        self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))

    def test_every_control_passes_to_the_ask(self):
        for what, doc in RUN_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    code, out, err, run_dir = self.gate(doc, records)
                    self.assertEqual(code, 0, (what, out, err))
                    self.assertEqual(out["next"], "ask", what)


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vnumbered-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

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


if __name__ == "__main__":
    unittest.main()
