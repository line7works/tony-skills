"""E18 slice B: the build-doc form's slice heading takes any slice-heading dash (the E18 plan, slice B).

`templates.BUILD["slice"]` reads `## Slice <name> <dash> <short>` where `<dash>` is one or more em dashes, en dashes or
hyphens (so `--` too, as the records component, build-v2 and recheck-v2 read it), with one space on each side, and the
second reading's slice form (`readings.FORM`) takes the same dashes. This reverses ruling C1A8-2 for the spaced en
dash, the spaced hyphen and the spaced double hyphen only: they now read as exact slice headings, in both readings,
with their cards. Everything else C1A8-2 and A21 (2) refuse stays refused (`NEAR_MISSES`). A level 3 heading on the
hyphen, en dash or double hyphen form is now refused as a near miss, as the em dash form already was; the label form
`### 7.1 Slice 1: the frame` stays as it is. `templates.D`, the dash every station writes, stays the em dash.

Every dash is written as an escape, never typed.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from station_core import templates  # noqa: E402
from vertical_core import fences, gate as gatemod, readings, spec  # noqa: E402

EM = "\u2014"
EN = "\u2013"
DASHES = (("an em dash", EM), ("an en dash", EN), ("a hyphen", "-"), ("a double hyphen", "--"))
B_BODY = ["Goal: one sentence about the spinner.", "Depends on: nothing"]


def with_b(heading, lines=("Status: built",)):
    """vlib's doc with slice A only, then `heading`, slice B's first lines and `lines`, before the working records."""
    base = vlib.build_doc(slices=[("A", "the counter", "signed off")])
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join([heading] + B_BODY + list(lines)) + "\n" + base[at:]


def number_of(text, line):
    return text.split("\n").index(line) + 1


# the near misses the third requirement names, each still refused at its heading: (what, heading, lines under it)
NEAR_MISSES = [
    ("a colon for the dash", "## Slice B: the spinner", ["Status: built"]),
    ("a lower-case slice", "## slice B - the spinner", ["Status: built"]),
    ("a zero-width character", "## Sl\u200bice B - the spinner", ["Status: built"]),
    ("an accented letter", "## Sl\u00efce B - the spinner", ["Status: built"]),
    ("a leading curly quote", "## \u2018Slice B - the spinner", ["Status: built"]),
    ("a level 1 heading", "# Slice B - the spinner", []),
    ("a numbered level 2 heading", "## 2. Slice B - beta", ["Status: built"]),
    ("a labelled level 2 heading", "## Next: Slice B - beta", ["Status: built"]),
]
for _what, _dash in DASHES:
    NEAR_MISSES += [
        ("%s with no spaces around it" % _what, "## Slice B%sthe spinner" % _dash, ["Status: built"]),
        ("%s with no space before it" % _what, "## Slice B%s the spinner" % _dash, ["Status: built"]),
        ("%s with no space after it" % _what, "## Slice B %sthe spinner" % _dash, ["Status: built"]),
    ]
del _what, _dash


class TheDashes(unittest.TestCase):
    """An em dash, en dash, hyphen and double hyphen heading each read as slice B, with its card, in both readings."""

    def test_each_dash_reads_as_the_slice_with_its_card_in_both_readings(self):
        for what, dash in DASHES:
            heading = "## Slice B %s the spinner" % dash
            text = with_b(heading)
            with self.subTest(dash=what):
                doc = fences.read(text)
                self.assertEqual(doc.problems, [], what)
                at = number_of(text, heading)
                status_at = number_of(text, "Status: built")
                first = readings.line_reading(doc, spec.sections(doc))
                second = readings.second_reading(text, len(doc.lines))
                for name, reading in (("line", first), ("second", second)):
                    self.assertEqual(reading["slices"].get(at), "B", (what, name, reading["slices"]))
                    self.assertEqual(reading["cards"][-1], [(status_at, "built", True)], (what, name))
                self.assertEqual(second["refused"], [], what)
                self.assertIsNone(readings.difference(text), what)
                self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                                 [("A", "signed off"), ("B", "built")], what)
                spec.clean(text)

    def test_the_build_doc_form_takes_each_dash_and_names_the_slice(self):
        for what, dash in DASHES:
            with self.subTest(dash=what):
                match = templates.BUILD["slice"].match("## Slice B %s the spinner" % dash)
                self.assertIsNotNone(match, what)
                self.assertEqual(match.groups(), ("B", "the spinner"), what)
                self.assertFalse(readings.slice_form(2, "Slice B %s the spinner" % dash), what)

    def test_the_dash_every_station_writes_stays_the_em_dash(self):
        self.assertEqual(templates.D, EM)


class TheNearMisses(unittest.TestCase):
    """The near misses C1A8-2 and A21 (2) refuse, other than the three spaced dashes, still stop at their heading."""

    def test_each_near_miss_stops_every_reader_naming_its_heading(self):
        for what, heading, lines in NEAR_MISSES:
            text = with_b(heading, lines)
            at = number_of(text, heading)
            with self.subTest(shape=what):
                for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base),
                                   ("spec", spec.clean)):
                    with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                        call(text)
                    self.assertEqual(caught.exception.line, at, (what, name, str(caught.exception)))


class TheLevelThree(unittest.TestCase):
    """A level 3 heading on the slice form with any of the dashes is refused as a near miss."""

    def test_a_level_3_slice_heading_on_each_dash_stops_naming_its_line(self):
        for what, dash in DASHES:
            note = "### Slice B %s x" % dash
            text = with_b("## Slice B %s the spinner" % EM, ["", note, "a note on the day.", "", "Status: built"])
            at = number_of(text, note)
            with self.subTest(dash=what):
                self.assertTrue(readings.slice_form(3, "Slice B %s x" % dash), what)
                for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base),
                                   ("spec", spec.clean)):
                    with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                        call(text)
                    self.assertEqual(caught.exception.line, at, (what, name, str(caught.exception)))
                    self.assertIn("reads like a slice heading", str(caught.exception), (what, name))

    def test_the_level_3_label_form_stays_as_it_is(self):
        self.assertFalse(readings.slice_form(3, "7.1 Slice 1: the frame"))
        text = with_b("## Slice B %s the spinner" % EM, ["", "### 7.1 Slice 1: the frame", "a note.", "",
                                                         "Status: built"])
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                         [("A", "signed off"), ("B", "built")])


class TheStatement(unittest.TestCase):
    """The rule texts that describe C1A8-2 say what is now read (the module docstring and the contract's one line)."""

    OLD = "C1A8-2: an en dash, a hyphen or a colon for the form's dash"
    NEW = ("C1A8-2 as E18 narrowed it: a colon for the form's dash, a dash with no spaces around it or with no space "
           "on one side")

    def test_the_old_reading_is_gone_and_the_new_one_stated_in_both_texts(self):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            contract = " ".join(fh.read().split())
        docstring = " ".join(readings.__doc__.split())
        for name, text in (("readings", docstring), ("contract", contract)):
            with self.subTest(text=name):
                self.assertNotIn(self.OLD, text, name)
                self.assertIn(self.NEW, text, name)


if __name__ == "__main__":
    unittest.main()
