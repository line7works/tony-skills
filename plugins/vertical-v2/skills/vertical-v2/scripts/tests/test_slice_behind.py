"""Round 13, the closing fix of slice 1a: a slice name behind a number or a label (the E15 lane contract A20; C1A12-1
and C1A12-2; contract section 5, "Two readings", refusal (b)).

Refusal (b) also refuses a heading of level 1, 2 or 3 whose folded name, with its leading punctuation, symbols and
spaces set aside, then any leading numbering of A18 (2)'s forms dropped (digits joined directly to the name included,
so a superscript two folds to `2` and drops), then at most one word ending in a colon dropped, reads as the slice form
`slice <name> <dash> ` and is not an exact slice heading. So `## 1. Slice B <dash> x`, `## (1) Slice B <dash> x`,
`## B. Slice B <dash> x`, `## Next: Slice B <dash> x` and `## ` U+00B2 `Slice B <dash> x` stop at the heading whatever
lies under them: no `Status:` line yet, a bold `**Status:** built` only the rendered text shows as a label, or a
character-coded `St&auml;tus: built`. A level 3 `### Slice B <dash> x` inside slice A stops at its heading too, so it
can no longer lend its card to the slice above (C1A12-2). A heading that only mentions a slice later in its name
(`## Notes on slice A <dash> what we learned`, `## Why slice B <dash> took longer`), a level 3 `### Slice A notes`
and an exact `## Slice B <dash> x` run.

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
    """vlib's doc with slice A only (its `Status:` line omitted when `slice_a` is None), then `heading`, slice B's
    first lines and `lines`, before the working records."""
    base = vlib.build_doc(slices=[("A", "the counter", slice_a)])
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join([heading] + B_BODY + list(lines)) + "\n" + base[at:]


def number_of(text, line):
    return text.split("\n").index(line) + 1


# C1A12-1: slice B's heading behind a number or a one-word label, each over three label shapes
BEHIND = ("## 1. Slice B %s the spinner" % D, "## (1) Slice B %s the spinner" % D, "## B. Slice B %s the spinner" % D,
          "## Next: Slice B %s the spinner" % D, "## ²Slice B %s the spinner" % D)
UNDER = (("no Status: line", []), ("**Status:** built", ["**Status:** built"]),
         ("St&auml;tus: built", ["St&auml;tus: built"]))
# (what, doc, the line the stop names)
STOP_SHAPES = [("%s over %s" % (heading, label), with_b(lines, heading), heading)
               for heading in BEHIND for label, lines in UNDER] + [
    ("### Slice B %s x over Status: %s inside an unlabeled slice A (C1A12-2)" % (D, card),
     with_b(["Status: %s" % card], "### Slice B %s the spinner" % D, slice_a=None), "### Slice B %s the spinner" % D)
    for card in ("built", "signed off")]

# (what, doc): each runs, slices A and B both signed off
RUN_SHAPES = [
    ("## Notes on slice A %s what we learned" % D,
     with_b(["Status: signed off", "", "## Notes on slice A %s what we learned" % D, "A note on the day."],
            "## Slice B %s the spinner" % D)),
    ("## Why slice B %s took longer" % D,
     with_b(["Status: signed off", "", "## Why slice B %s took longer" % D, "A note on the day."],
            "## Slice B %s the spinner" % D)),
    ("### Slice A notes",
     with_b(["", "### Slice A notes", "A note on the day.", "", "Status: signed off"], "## Slice B %s the spinner" % D)),
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
        refused = ("1. Slice B %s x", "(1) Slice B %s x", "B. Slice B %s x", "Next: Slice B %s x", "²Slice B %s x",
                   "1.1 Slice B %s x", "a) Slice B %s x", "II. Slice B %s x", "The Slice B %s x", "1 Next: Slice B %s x",
                   "‘Slice B %s x")
        for name in refused:
            for level in (1, 2, 3):
                with self.subTest(name=name, level=level):
                    self.assertTrue(readings.slice_form(level, name % D), (name, level))
            self.assertFalse(readings.slice_form(4, name % D), name)
        self.assertTrue(readings.slice_form(3, "Slice B %s x" % D))
        self.assertTrue(readings.slice_form(1, "Slice B %s x" % D))
        self.assertFalse(readings.slice_form(2, "Slice B %s x" % D))
        for name in ("Notes on slice A %s what we learned", "Why slice B %s took longer", "Slice A notes",
                     "Next: then: Slice B %s x", "Slice D · 2026-10-01", "Slices %s overview", "Slice B - x",
                     "2 slices %s overview"):
            with self.subTest(name=name):
                self.assertFalse(readings.slice_form(3, name.replace("%s", D)), name)


class TheStatement(unittest.TestCase):
    """The rule stated once in code and once in the contract."""

    def test_refusal_b_is_stated_in_the_contract(self):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index("**The CommonMark reading's four refusals**")
        para = " ".join(text[start:text.index("\n\n", start)].split())
        for words in ("A20", "level 1, 2 or 3", "at most one word ending in a colon", "digits joined directly to the name",
                      "only mentions a slice later in its name"):
            self.assertIn(words, para)

    def test_refusal_b_is_stated_in_the_code(self):
        doc = " ".join(readings.__doc__.split())
        for words in ("A20", "level 1, 2 or 3", "at most one word ending in a colon", "digits joined directly to the name",
                      "only mentions a slice later in its name"):
            self.assertIn(words, doc)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):
    """Every shape through the real CLI, records off and on: a stopping shape exits 10, `doc-unreadable` naming the
    heading, no `ask.json`, no request file, no `packets`; a control passes to the ask."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vbehind-")
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
        self.tmp = testlib.make_scratch("vbehind-scope-")
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
                    if records and line.startswith("### ") and "Status: built" in what:
                        # the records, imported from the commit, read slice A `built` from the level 3 heading's
                        # label, and the working tree's doc says `signed off`: the gate stops on that first
                        self.assertEqual((code, out["stop_tag"]), (10, "card-disagrees"), (what, out, err))
                        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)
                        continue
                    self.assertEqual(code, 0, (what, out, err))
                    code, out, err = drive(["scope", "--run-dir", run_dir])
                    self.assertEqual(code, 10, (what, out, err))
                    self.assertEqual(out["stop_tag"], "doc-unreadable", what)
                    self.assertIn("line %d" % number_of(doc, line), out["reason"], what)
                    self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)


if __name__ == "__main__":
    unittest.main()
