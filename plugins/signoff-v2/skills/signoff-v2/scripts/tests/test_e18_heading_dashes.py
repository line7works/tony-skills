"""E18 round 1, slice A: signoff-v2's ledger reads any slice-heading dash.

signoff-v2's ledger read a slice heading and a record heading only when the separator was an em
dash (canary finding C-23), while the records component reads one or more em dashes, en dashes or
hyphens (`plugins/records/scripts/records_core/legacy.py`, `SLICE_HEADING_RE` and
`RECORD_HEADING_RE`). A plan written with a hyphen or an en dash therefore had its card unread by
signoff-v2 and read by the records component. The ledger now reads both headings by the records
component's own patterns, so for any heading the slice name signoff-v2 reads is the name the
records component reads, and the card this station sets and the records it appends name the same
slice.

Two names change with this, deliberately: an em dash with no spaces around it reads the whole run
as the name (`A`, the dash, `x`), and a multi-word name (`A notes`) now reads. A heading with no
separator reads as before. The records component's module is imported here, in the test only, to
read its own patterns; the station's core never imports it.

The dashes are written as escapes (U+2014 em dash, U+2013 en dash) so this file carries none.
"""
import os
import sys
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import ledger  # noqa: E402

RECORDS_SCRIPTS = os.path.join(testlib.RECORDS_ROOT, "scripts")
if RECORDS_SCRIPTS not in sys.path:
    sys.path.insert(0, RECORDS_SCRIPTS)
from records_core import legacy  # noqa: E402

EM = "\u2014"
EN = "\u2013"

SEPARATORS = (("em dash", EM), ("en dash", EN), ("hyphen", "-"), ("double hyphen", "--"))
DASHED = tuple((label, "## Slice A %s alpha" % sep) for label, sep in SEPARATORS)
UNSPACED_EM = "## Slice A%sx" % EM
MULTI_WORD = "## Slice A notes"
BARE = "## Slice A"
EVERY_HEADING = tuple(h for _, h in DASHED) + (UNSPACED_EM, MULTI_WORD, BARE)


def plan(heading, card="not started"):
    return ("# A plan\n\nIntent: a test.\n\n%s\n\nStatus: %s\n\nRequirements:\n\n- one\n\n"
            "## Slice B %s beta\n\nStatus: built\n" % (heading, card, EM))


class DashedSliceHeadingsRead(unittest.TestCase):
    def test_card_of_finds_slice_a_under_each_separator(self):
        for label, heading in DASHED:
            with self.subTest(separator=label):
                card, index = ledger.card_of(plan(heading), "A")
                self.assertEqual(card, "not started")
                self.assertEqual(plan(heading).split("\n")[index], "Status: not started")

    def test_set_card_sets_slice_a_under_each_separator(self):
        for label, heading in DASHED:
            with self.subTest(separator=label):
                out = ledger.set_card(plan(heading), "A", "rejected")
                self.assertEqual(ledger.card_of(out, "A")[0], "rejected")
                self.assertEqual(out, plan(heading, card="rejected"))
                self.assertEqual(ledger.card_of(out, "B")[0], "built")

    def test_record_heading_with_each_separator_is_found(self):
        for label, sep in SEPARATORS:
            with self.subTest(separator=label):
                heading = "### 2026-10-25 %s review: A" % sep
                self.assertIsNotNone(ledger.RECORD_HEADING.match(heading))
                text = ("# A plan\n\n## Slice A %s alpha\n\nStatus: built\n\n## Notes\n\n"
                        "%s\n- one line\n\n## Punch list\n\n" % (EM, heading))
                insert, created = ledger.ledger_home(text)
                self.assertIsNone(created)
                self.assertEqual(text.split("\n")[insert - 1], "- one line")


class NamesMatchTheRecordsComponent(unittest.TestCase):
    def test_every_heading_names_the_records_component_slice(self):
        for heading in EVERY_HEADING:
            with self.subTest(heading=heading):
                ours = ledger.SLICE_HEADING.match(heading)
                theirs = legacy.SLICE_HEADING_RE.match(heading.rstrip())
                self.assertIsNotNone(theirs)
                self.assertIsNotNone(ours)
                self.assertEqual(ours.group(1), theirs.group(1))

    def test_every_record_heading_reads_as_the_records_component_reads_it(self):
        for label, sep in SEPARATORS:
            with self.subTest(separator=label):
                heading = "### 2026-10-25 %s recheck: Slice A" % sep
                ours = ledger.RECORD_HEADING.match(heading)
                theirs = legacy.RECORD_HEADING_RE.match(heading)
                self.assertIsNotNone(theirs)
                self.assertIsNotNone(ours)
                self.assertEqual(ours.groups(), theirs.groups())

    def test_the_two_changed_names(self):
        self.assertEqual(ledger.SLICE_HEADING.match(UNSPACED_EM).group(1), "A%sx" % EM)
        self.assertEqual(ledger.card_of(plan(UNSPACED_EM), "A%sx" % EM)[0], "not started")
        self.assertEqual(ledger.card_of(plan(UNSPACED_EM), "A"), (None, None))
        self.assertEqual(ledger.SLICE_HEADING.match(MULTI_WORD).group(1), "A notes")
        self.assertEqual(ledger.card_of(plan(MULTI_WORD), "A notes")[0], "not started")


class BareHeadingReadsAsBefore(unittest.TestCase):
    def test_bare_heading_names_slice_a(self):
        self.assertEqual(ledger.SLICE_HEADING.match(BARE).group(1), "A")
        self.assertEqual(ledger.card_of(plan(BARE), "A")[0], "not started")
        self.assertEqual(ledger.set_card(plan(BARE), "A", "built"), plan(BARE, card="built"))


class DocstringNamesTheSeparators(unittest.TestCase):
    def test_card_line_names_each_separator_read(self):
        card_line = [line for line in ledger.__doc__.split("\n- ") if line.startswith("**The card.**")]
        self.assertEqual(len(card_line), 1)
        text = " ".join(card_line[0].split())
        for word in ("em dashes", "en dashes", "hyphens"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
