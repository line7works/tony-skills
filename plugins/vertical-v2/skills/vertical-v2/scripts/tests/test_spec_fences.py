"""vertical-v2's own fence reader for the spec (the E15 lane contract A5 (2) and A8; C1A3-1, C1A4-1; contract
section 5).

The spec a reviewer receives is the build doc with the five withheld sections and every `Status:` label
removed outside fences. What is fenced is decided by one strict rule, plain code blocks only (A8): a fence is
accepted only when its opening line and its closing line both start at the left margin (no indent, no list
marker, no `>`), the closing line is the same character, at least as long, with nothing after it but spaces
or tabs, and no line between is another fence line off the margin. Any other fence line (three or more
backticks or tildes after any indent, after a list-item or block-quote marker, a backtick line whose info
string holds a backtick, a fence never closed, a fence line inside raw HTML) stops the run with its line
number before any packet is built.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, spec  # noqa: E402

D = vlib.D
MARKERS = ("PUNCH-MARKER", "HANDOFF-MARKER", "ASSUMPTION-MARKER", "DEVIATION-MARKER", "DISCOVERED-MARKER",
           "SLICE-STATUS")


def doc_with(before_slices=(), after_slices=()):
    """A build doc whose slices carry SLICE-STATUS labels and whose five withheld sections carry markers, with
    `before_slices` lines after the header and `after_slices` lines after the last slice."""
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "", "Intent: a counter.", "Constraints: none.",
             "Out of scope: a dashboard", ""]
    lines += list(before_slices)
    lines += ["", "## Slice A %s the counter" % D, "Goal: count.", "Requirements:", "- R1 counts",
              "Acceptance criteria:", "- AC1 adds one", "Footprint: src/turnstile.py", "Not in this slice: none",
              "Depends on: nothing", "Status: signed off SLICE-STATUS-A", ""]
    lines += list(after_slices)
    lines += ["", "## Build assumptions", "- ASSUMPTION-MARKER", "## Deviations", "- DEVIATION-MARKER",
              "## Discovered", "- DISCOVERED-MARKER", "## Handoffs", "- HANDOFF-MARKER",
              "## Punch list", "- PUNCH-MARKER", ""]
    return "\n".join(lines)


def kept_and_removed(text):
    kept, removed = spec.clean(text)
    return kept, sorted(r["what"] for r in removed)


ALL_FIVE = sorted(["## Build assumptions", "## Deviations", "## Discovered", "## Handoffs", "## Punch list",
                   "Status: line"])


class TheFenceShapes(unittest.TestCase):

    def assert_clean(self, text, literal=None):
        kept, removed = kept_and_removed(text)
        for marker in MARKERS:
            self.assertNotIn(marker, kept, marker)
        self.assertEqual(removed, ALL_FIVE)
        if literal is not None:
            self.assertIn(literal, kept)
        return kept

    def test_a_four_backtick_fence_holding_a_three_backtick_line(self):
        self.assert_clean(doc_with(after_slices=["````markdown", "```", "## Punch list", "Status: FENCED-LITERAL",
                                                 "```", "````"]),
                          literal="```\n## Punch list\nStatus: FENCED-LITERAL\n```\n````\n")

    def test_a_four_backtick_fence_holding_only_a_three_backtick_line(self):
        self.assert_clean(doc_with(after_slices=["````", "```", "````"]), literal="````\n```\n````\n")

    def test_a_tilde_fence_holding_backticks(self):
        self.assert_clean(doc_with(after_slices=["~~~", "```", "## Handoffs", "~~~"]),
                          literal="~~~\n```\n## Handoffs\n~~~\n")

    def test_a_longer_closing_line_closes_and_a_shorter_one_does_not(self):
        self.assert_clean(doc_with(after_slices=["~~~~", "~~~", "## Deviations", "~~~~~~"]),
                          literal="~~~~\n~~~\n## Deviations\n~~~~~~\n")

    def test_a_closing_line_with_text_after_it_does_not_close(self):
        self.assert_clean(doc_with(after_slices=["```", "``` not a close", "## Discovered", "```"]),
                          literal="``` not a close\n## Discovered\n```\n")

    def test_a_fence_with_an_info_string(self):
        self.assert_clean(doc_with(after_slices=["```python title=x", "## Build assumptions", "```"]),
                          literal="```python title=x\n## Build assumptions\n```\n")

    def test_an_unclosed_fence_after_the_slices_stops_with_its_line(self):
        text = doc_with(after_slices=["````", "```", "```"])
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(text)
        self.assertEqual(caught.exception.line, text.split("\n").index("````") + 1)
        self.assertIn("line %d" % caught.exception.line, str(caught.exception))

    def test_an_unclosed_fence_before_the_slices_stops_with_its_line(self):
        text = doc_with(before_slices=["~~~~", "an example"])
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(text)
        self.assertEqual(caught.exception.line, text.split("\n").index("~~~~") + 1)

    def test_a_fence_inside_a_container_stops_with_its_line(self):
        for opener in ("> ```", "- ```", "1. ~~~"):
            text = doc_with(after_slices=[opener, "## Punch list", "```"])
            with self.assertRaises(spec.SpecUnreadable) as caught:
                spec.clean(text)
            self.assertEqual(caught.exception.line, text.split("\n").index(opener) + 1, opener)

    def test_a_list_item_fence_left_by_a_dedented_line_stops(self):
        """A8: the indented fence line itself stops (at check 4 the dedented line did)."""
        text = doc_with(after_slices=["- an item", "  ```", "## Punch list", "  ```"])
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(text)
        self.assertEqual(caught.exception.line, text.split("\n").index("  ```") + 1)

    def test_a_fence_marker_inside_a_raw_html_block_stops(self):
        for block in (["<pre>", "```", "</pre>"], ["<!--", "```", "-->"], ["<div>", "```", ""]):
            text = doc_with(after_slices=block + ["## Punch list", "```"])
            with self.assertRaises(spec.SpecUnreadable) as caught:
                spec.clean(text)
            self.assertEqual(caught.exception.line, text.split("\n").index(block[0]) + 2, block)

    def test_crlf_endings_read_the_same(self):
        text = doc_with(after_slices=["````", "```", "## Punch list", "````"]).replace("\n", "\r\n")
        kept, removed = kept_and_removed(text)
        self.assertEqual(removed, ALL_FIVE)
        self.assertNotIn("PUNCH-MARKER", kept)


LAZY_BULLET = ["- a note on the counter", "that continues lazily on this line", "  ```text", "## Punch list",
               "Status: LAZY-FENCED", "```"]
LAZY_NUMBERED = ["1. a note on the counter", "continues lazily", "   ~~~", "## Handoffs", "~~~"]


class TheStrictRule(unittest.TestCase):
    """A8, C1A4-1: strict plain code blocks. Every fence line off the left margin, in a container, or that the
    margin rule cannot pair stops the run naming its line; the reader follows no list or lazy-continuation
    rule. `first` is the line text whose first occurrence the stop names."""

    def assert_stops(self, text, first, what=None):
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(text)
        self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, (first, str(caught.exception)))
        self.assertIn("line %d" % caught.exception.line, str(caught.exception))
        if what is not None:
            self.assertIn(what, caught.exception.what)
        scan = fences.scan(fences.split_lines(text))
        self.assertEqual(scan.problems[0][0], caught.exception.line)

    def test_check_4s_lazy_continuation_shape_stops_at_the_indented_fence(self):
        self.assert_stops(doc_with(after_slices=LAZY_BULLET), "  ```text")

    def test_the_numbered_lazy_continuation_shape_stops_at_the_indented_fence(self):
        self.assert_stops(doc_with(after_slices=LAZY_NUMBERED), "   ~~~")

    def test_an_indented_fence_in_a_list_item_stops(self):
        self.assert_stops(doc_with(after_slices=["- an item", "", "  ```", "  ## Punch list", "  ```"]), "  ```")

    def test_a_fence_in_a_block_quote_stops(self):
        for opener in ("> ```", ">```", "> > ~~~", "   > ```"):
            self.assert_stops(doc_with(after_slices=["> a quote", opener, "> ## Punch list", "> ```"]), opener)

    def test_a_fence_after_a_list_marker_stops(self):
        for opener in ("- ```", "* ~~~", "+ ```", "1. ```", "2) ~~~", "- - ```"):
            self.assert_stops(doc_with(after_slices=[opener, "## Punch list", "```"]), opener)

    def test_a_fence_with_one_to_three_spaces_of_indent_at_top_level_stops(self):
        for indent in (" ", "  ", "   "):
            self.assert_stops(doc_with(after_slices=[indent + "```", "## Punch list", indent + "```"]), indent + "```")

    def test_a_fence_line_with_four_spaces_or_a_tab_before_it_stops(self):
        for opener in ("    ```", "\t~~~"):
            self.assert_stops(doc_with(after_slices=["", opener, "", "text"]), opener)

    def test_an_unclosed_margin_fence_stops_at_its_opening_line(self):
        self.assert_stops(doc_with(after_slices=["```text", "## Punch list"]), "```text", "never closes")

    def test_a_margin_backtick_fence_whose_info_string_holds_a_backtick_stops(self):
        for opener in ("``` a`b", "```x`y", "````js `x`"):
            self.assert_stops(doc_with(after_slices=[opener, "text"]), opener)

    def test_an_indented_line_inside_a_margin_fence_that_could_close_it_stops(self):
        self.assert_stops(doc_with(after_slices=["```", "code", "  ```", "## Punch list", "```"]), "  ```")

    def test_an_indented_fence_line_inside_a_margin_fence_stops(self):
        self.assert_stops(doc_with(after_slices=["````", "- ```", "x", "````"]), "- ```")
        self.assert_stops(doc_with(after_slices=["~~~", "   ```python", "x", "   ```", "~~~"]), "   ```python")

    def test_a_tilde_fence_may_hold_backticks_in_its_info_string(self):
        kept, removed = kept_and_removed(doc_with(after_slices=["~~~ a`b", "## Punch list", "~~~"]))
        self.assertEqual(removed, ALL_FIVE)
        self.assertIn("~~~ a`b\n## Punch list\n~~~\n", kept)

    def test_the_rule_follows_no_list_context(self):
        """A margin fence right after a list item is a top-level fence, as CommonMark reads it."""
        kept, removed = kept_and_removed(doc_with(after_slices=["- an item", "```", "## Punch list", "```"]))
        self.assertEqual(removed, ALL_FIVE)
        self.assertIn("- an item\n```\n## Punch list\n```\n", kept)


class TheCleanDoc(unittest.TestCase):

    def test_the_clean_doc_spec_is_unchanged_byte_for_byte(self):
        text = vlib.build_doc()
        kept, removed = spec.clean(text)
        lines = text.split("\n")
        status = [i + 1 for i, line in enumerate(lines) if line.startswith("Status:")]
        cut = lines.index("## Build assumptions")
        expected = "".join(line + "\n" for number, line in enumerate(lines[:cut], 1) if number not in status)
        self.assertEqual(kept, expected)
        self.assertEqual([r["what"] for r in removed],
                         ["Status: line", "Status: line", "## Build assumptions", "## Deviations", "## Discovered",
                          "## Handoffs", "## Punch list"])

    def test_the_reader_places_every_line_of_the_clean_doc(self):
        scan = fences.scan(fences.split_lines(vlib.build_doc()))
        self.assertEqual((scan.fenced, scan.problems), (set(), []))


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheStopAtScope(unittest.TestCase):
    """Through the real CLI: scope stops `doc-unreadable` naming the line, before any packet is built."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vfence-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_an_unclosed_fence_stops_scope_before_any_packet(self):
        """The gate reads the working tree's doc and stops on the same shape (A7, test_gate.py); scope reads
        the reviewed commit's, so the commit holds the unclosed fence and the working tree a closed one, under
        the owner's committed-state-only words."""
        doc = vlib.build_doc().replace("## Build assumptions\n", "````\n```\n## Build assumptions\n")
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=True)
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
        drive, run_dir = vlib.start(self.tmp, ws, owner_words={"committed_only": "review the committed state only"})
        self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("````") + 1), out["reason"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))

    def test_check_4s_lazy_continuation_shape_stops_scope_before_any_packet(self):
        """C1A4-1 through the real CLI: the commit holds the lazy-list fence (the gate read the working tree's
        clean doc under the owner's committed-state-only words); scope stops naming the indented fence line."""
        trick = "\n".join(LAZY_BULLET) + "\n\n"
        doc = vlib.build_doc().replace("## Build assumptions\n", trick + "## Build assumptions\n")
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=True)
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
        drive, run_dir = vlib.start(self.tmp, ws, owner_words={"committed_only": "review the committed state only"})
        self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("  ```text") + 1), out["reason"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))


if __name__ == "__main__":
    unittest.main()
