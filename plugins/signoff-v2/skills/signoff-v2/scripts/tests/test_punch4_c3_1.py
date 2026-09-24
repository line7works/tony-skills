"""punch4-C3-1: the first-heading walker was quadratic on a run of link reference definitions (E13
punch list round 4, from the round 3 checker's report, MINOR).

Round 3 reads link reference definitions two ways. In the blocks reading, at every top-level line
that opens with `[`, the walker gathered EVERY following line up to a blank line or a terminator,
joined them and scanned the result, so a run of N one-line definitions cost on the order of N
squared (the checker's `f9perf.py`: 1,000 definitions 0.53 s, 5,000 12.98 s, 20,000 205.90 s in
`first_headings`; an untracked file of 8,000 definitions made `scope` take 32.4 s against 1.5 s at
`79e3243`). The paragraphs reading stripped a paragraph's leading definitions by joining the rest
of the paragraph again for each one, the same shape at a smaller constant.

The scan is now linear in the file's length: each run of lines a definition may take is found and
joined once, and each definition is parsed in place, reading only as far as it runs. What is
withheld does not change (every F9 module of the fix round and rounds 1 to 3 still passes).

Timing is measured with `time.perf_counter` after one warm-up call, against bounds far above the
linear cost (about 0.1 s for 8,000 definitions here) and far below the quadratic one.
"""
import os
import time
import unittest

import testlib
from test_punch2_f9 import _Punch2

testlib.add_scripts_to_path()

from signoff_core import packet  # noqa: E402

N = 8000
DIRECT_BOUND = 3.0        # seconds for one `first_headings` call; the quadratic walk took ~33 s
PARAGRAPH_N = 40000
PARAGRAPH_BOUND = 2.0     # seconds for the paragraphs reading alone
SCOPE_BOUND = 15.0        # seconds for the real `scope` phase; the quadratic walk took ~32 s


def definitions(n, prefix="a"):
    return "".join("[%s%d]: /u%d\n" % (prefix, i, i) for i in range(n))


def timed(call, *args):
    started = time.perf_counter()
    out = call(*args)
    return out, time.perf_counter() - started


class Punch4C31TheWalkIsLinear(unittest.TestCase):

    def setUp(self):
        packet.first_headings(definitions(50) + "# Warm up\n")      # the warm-up call

    def test_a_run_of_definitions_then_an_atx_heading(self):
        headings, took = timed(packet.first_headings, definitions(N) + "# Builder notes\n")
        self.assertEqual(headings, ["Builder notes"])
        self.assertLess(took, DIRECT_BOUND, "%d definitions took %.2f s" % (N, took))

    def test_a_run_of_definitions_then_a_setext_heading(self):
        headings, took = timed(packet.first_headings, definitions(N) + "Builder notes\n===\n")
        self.assertEqual(headings, ["Builder notes"])
        self.assertLess(took, DIRECT_BOUND, "%d definitions took %.2f s" % (N, took))

    def test_definitions_over_two_lines_each(self):
        text = "".join("[a%d]:\n/u%d\n" % (i, i) for i in range(N)) + "# Builder notes\n"
        headings, took = timed(packet.first_headings, text)
        self.assertEqual(headings, ["Builder notes"])
        self.assertLess(took, DIRECT_BOUND, "%d two-line definitions took %.2f s" % (N, took))

    def test_the_paragraphs_reading_strips_a_long_run_once(self):
        lines = packet._lines(definitions(PARAGRAPH_N) + "Builder notes\n===\n")
        heading, took = timed(packet._first_heading_from, lines, 0,
                              packet.DEFINITIONS_IN_PARAGRAPHS)
        self.assertEqual(heading, "Builder notes")
        self.assertLess(took, PARAGRAPH_BOUND,
                        "%d definitions in a paragraph took %.2f s" % (PARAGRAPH_N, took))


class Punch4C31ScopeEndToEnd(_Punch2):
    """The checker's end-to-end shape: an untracked `.md` of 8,000 one-line definitions in the
    source set, through the real `signoff.py scope`."""

    REL = "docs/refs.md"

    def test_scope_on_eight_thousand_definitions(self):
        self.write(self.REL, "".join("[r%d]: https://example.invalid/%d\n" % (i, i)
                                     for i in range(N)))
        code, doc, err = self.phase(["check-input", self.input_path])
        self.assertEqual(code, 0, err)
        started = time.perf_counter()
        code, doc, err = self.phase(["scope", "--run-dir", self.run_dir])
        took = time.perf_counter() - started
        self.assertEqual(code, 0, err)
        row, _ = self.row()
        self.assertEqual((row["kind"], row["delivered"]), ("source", True))
        self.assertLess(took, SCOPE_BOUND, "scope took %.1f s" % took)

    def test_a_declaring_heading_after_the_run_is_still_withheld(self):
        self.withheld(definitions(N, "r") + "# Builder notes\n\nThe separator case passed for me.\n")


if __name__ == "__main__":
    unittest.main()
