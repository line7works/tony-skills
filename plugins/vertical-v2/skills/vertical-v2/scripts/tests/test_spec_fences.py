"""vertical-v2's own fence reader for the spec (the E15 lane contract A5 (2) and A8; C1A3-1, C1A4-1; contract
section 5).

The spec a reviewer receives is the build doc with the five withheld sections and every `Status:` label
removed outside fences. What is fenced is decided by one strict rule, plain code blocks only (A8): a fence is
accepted only when its opening line and its closing line both start at the left margin (no indent, no list
marker, no `>`), the closing line is the same character, at least as long, with nothing after it but spaces
or tabs, and no line between is another fence line off the margin. Any other fence line (three or more
backticks or tildes after any indent, after a list-item or block-quote marker, a backtick line whose info
string holds a backtick, a fence never closed) stops the run with its line number before any packet is built.

No raw HTML lines (A9, C1A5-1 and C1A5-2): any line outside an accepted fence whose first characters, after
any indent and any list-item or block-quote markers, are `<` followed by a letter, `/`, `!` or `?` stops the
run with its line number too; the reader no longer tracks where a raw HTML block ends. A `<` line inside an
accepted fence is content.

Exact labels (A10, C1A6-1): a slice's `Status:` line and the header's `Base:` line are taken only when exact and
the last line of their paragraph, one each; every reader of the build doc (the spec, the gate's slices, the
recorded base) refuses any other such line naming it (TheLabelRule).
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, spec  # noqa: E402

D = vlib.D
MARKERS = ("PUNCH-MARKER", "HANDOFF-MARKER", "ASSUMPTION-MARKER", "DEVIATION-MARKER", "DISCOVERED-MARKER",
           "Status: signed off")


def doc_with(before_slices=(), after_slices=()):
    """A build doc whose slice carries an exact `Status: signed off` label (A10: a label with text after it stops
    the run, so the label is its own marker) and whose five withheld sections carry markers, with `before_slices`
    lines after the header and `after_slices` lines after the last slice."""
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "", "Intent: a counter.", "Constraints: none.",
             "Out of scope: a dashboard", ""]
    lines += list(before_slices)
    lines += ["", "## Slice A %s the counter" % D, "Goal: count.", "Requirements:", "- R1 counts",
              "Acceptance criteria:", "- AC1 adds one", "Footprint: src/turnstile.py", "Not in this slice: none",
              "Depends on: nothing", "Status: signed off", ""]
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
        """A9: the raw HTML line itself stops (at check 5 the fence line inside the block did)."""
        for block in (["<pre>", "```", "</pre>"], ["<!--", "```", "-->"], ["<div>", "```", ""]):
            text = doc_with(after_slices=block + ["## Punch list", "```"])
            with self.assertRaises(spec.SpecUnreadable) as caught:
                spec.clean(text)
            self.assertEqual(caught.exception.line, text.split("\n").index(block[0]) + 1, block)

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


UNICODE_BLANKS = (("a no-break space", "\u00a0"), ("a form feed", "\x0c"), ("a vertical tab", "\x0b"),
                  ("a next-line character", "\x85"), ("an ideographic space", "\u3000"), ("an em space", "\u2003"))


class TheRawHtmlRule(unittest.TestCase):
    """A9, C1A5-1 and C1A5-2: any raw HTML line outside an accepted fence stops the run naming its line, before
    any packet; a `<` line inside an accepted fence is content, and a `<` that does not open a tag does not stop."""

    def assert_stops(self, text, first):
        with self.assertRaises(spec.SpecUnreadable) as caught:
            spec.clean(text)
        self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, (repr(first), str(caught.exception)))
        self.assertIn("line %d" % caught.exception.line, str(caught.exception))
        self.assertIn("raw HTML", caught.exception.what)
        scan = fences.scan(fences.split_lines(text))
        self.assertEqual(scan.problems[0][0], caught.exception.line)
        return caught.exception

    def test_check_5s_six_unicode_space_shapes_stop_at_the_html_line(self):
        """C1A5-1: `<div>`, a line of a Unicode space CommonMark does not count as blank, a margin fence, then the
        withheld sections, and a second `<div>` and fence at the end: the reader once accepted the fence."""
        for what, blank in UNICODE_BLANKS:
            text = doc_with(after_slices=["<div>", blank, "```", ""]) + "<div>\n```\n"
            self.assert_stops(text, "<div>")

    def test_a_comment_holding_a_heading_inside_the_punch_list_stops(self):
        """C1A5-2: `## Older entries` inside a comment once ended the withheld `## Punch list` early."""
        text = doc_with() + "<!--\n## Older entries\n-->\n- PUNCH-LEAK an older entry\n"
        self.assert_stops(text, "<!--")

    def test_each_raw_html_opening_stops_at_its_line(self):
        for line in ("<pre>", "<details>", "<div>", "<?php x ?>", "<!DOCTYPE html>", "<![CDATA[ x ]]>", "</div>",
                     "<!-- a note -->", "<script>", "<textarea>", "<style>", "<summary>a</summary>", "<br/>",
                     "<a href=\"x\">link</a>"):
            self.assert_stops(doc_with(after_slices=["", line, "", "text"]), line)

    def test_a_tag_after_a_list_marker_a_quote_marker_a_tab_or_an_indent_stops(self):
        for line in ("- <div>", "* <details>", "+ <pre>", "1. <div>", "2) <!--", "> <div>", "><div>", "> > <pre>",
                     "> - <div>", "\t<div>", " <div>", "   <!--", "    <div>", "-\t<div>"):
            self.assert_stops(doc_with(after_slices=["", line, "", "text"]), line)

    def test_a_line_opening_with_an_inline_placeholder_or_an_autolink_stops_by_design(self):
        for line in ("<path> is where the counter lives", "<https://example.com/turnstile>",
                     "<turns@example.com> for questions"):
            self.assert_stops(doc_with(after_slices=["a paragraph that wraps", line]), line)

    def test_a_raw_html_line_before_the_slices_stops(self):
        self.assert_stops(doc_with(before_slices=["<!--", "Status: signed off", "-->"]), "<!--")

    def test_a_raw_html_line_inside_an_accepted_fence_is_content(self):
        for fence in (["```html", "<div>", "<!--", "## Punch list", "-->", "</div>", "```"],
                      ["~~~~", "<pre>", "Status: an example", "</pre>", "~~~~"]):
            kept, removed = kept_and_removed(doc_with(after_slices=fence))
            self.assertEqual(removed, ALL_FIVE, fence)
            self.assertIn("\n".join(fence) + "\n", kept)

    def test_a_less_than_sign_mid_line_does_not_stop(self):
        kept, removed = kept_and_removed(doc_with(after_slices=["the count stays < 3 and <div> is inline here",
                                                                "Footprint note: see <path> later"]))
        self.assertEqual(removed, ALL_FIVE)
        self.assertIn("the count stays < 3 and <div> is inline here\n", kept)

    def test_a_less_than_sign_followed_by_a_space_or_a_digit_or_another_sign_does_not_stop(self):
        for line in ("< 3 turns", "<3 turns", "<= 3 turns", "<- back", "<<", "\u00a0<div> after a no-break space",
                     "-<div> with no space after the dash"):
            kept, removed = kept_and_removed(doc_with(after_slices=["", line, ""]))
            self.assertEqual(removed, ALL_FIVE, repr(line))
            self.assertIn(line + "\n", kept)


HIDING = (("an inline comment opened mid-line", ["Depends on: A <!--", "%s", "-->"]),
          ("a link reference definition title in double quotes", ["", "[plan-note]: /plan \"", "%s", "\""]),
          ("a link reference definition title in parentheses", ["", "[plan-note]: /plan (", "%s", ")"]),
          ("an inline link title", ["see [the plan](/plan \"", "%s", "\")"]))


def two_slices(tail_b, header=()):
    """Slice A `signed off`, then slice B whose section ends with `tail_b` (its label lines), then the withheld
    sections; `header` lines go after the header paragraph."""
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "", "Intent: a counter.", "Out of scope: a dashboard"]
    lines += list(header)
    lines += ["", "## Slice A %s the counter" % D, "Goal: count.", "Depends on: nothing", "Status: signed off", "",
              "## Slice B %s the spinner" % D, "Goal: spin.", "Depends on: A"]
    lines += list(tail_b)
    lines += ["", "## Punch list", "- PUNCH-MARKER", ""]
    return "\n".join(lines)


class TheLabelRule(unittest.TestCase):
    """A10, C1A6-1: the exact-label rule, one statement in `fences.py`, read by every reader of the build doc: the
    gate's slices (`slices_of`), the header's base (`recorded_base`) and the spec (`spec.clean`). Each refusal
    names its line, and the same problem is the first `fences.read` reports."""

    def assert_stops(self, text, number, what=None, readers=("slices", "base", "spec")):
        calls = {"slices": gatemod.slices_of, "base": gatemod.recorded_base, "spec": spec.clean}
        for name in readers:
            with self.assertRaises(spec.SpecUnreadable) as caught:
                calls[name](text)
            self.assertEqual(caught.exception.line, number, (name, str(caught.exception)))
            self.assertIn("line %d" % number, str(caught.exception))
            if what is not None:
                self.assertIn(what, caught.exception.what)
        self.assertEqual(fences.read(text).problems[0][0], number)

    def number(self, text, line, after="## Slice B %s the spinner" % D):
        lines = text.split("\n")
        return lines.index(line, lines.index(after) if after else 0) + 1

    def test_check_6s_four_hiding_shapes_stop_every_reader(self):
        for what, shape in HIDING:
            for visible in ("Status: built", None):
                tail = [line % "Status: signed off" if "%s" in line else line for line in shape]
                text = two_slices(tail + ([visible] if visible else []))
                with self.subTest(shape=what, visible=visible):
                    self.assert_stops(text, self.number(text, "Status: signed off"), "Status:")

    def test_check_6s_four_hiding_shapes_hold_no_base(self):
        for what, shape in HIDING:
            head = [line % "Base: 1111111" if "%s" in line else line for line in shape] + ["Base: 2222222"]
            text = two_slices(["Status: signed off"], header=head)
            with self.subTest(shape=what):
                self.assert_stops(text, self.number(text, "Base: 1111111", after=None), "Base:")

    def test_two_labels_stop_naming_both(self):
        text = two_slices(["Status: built", "", "Status: signed off"])
        first, second = self.number(text, "Status: built"), self.number(text, "Status: signed off")
        self.assert_stops(text, second, "line %d" % first)
        text = two_slices(["Status: signed off"], header=["Base: 1111111", "", "Base: 2222222"])
        self.assert_stops(text, self.number(text, "Base: 2222222", after=None),
                          "line %d" % self.number(text, "Base: 1111111", after=None))

    def test_each_label_the_rule_does_not_take_stops(self):
        for tail, line in ((["Status: signed off pending"], "Status: signed off pending"),
                           (["Status: done"], "Status: done"),
                           (["Status: Rejected"], "Status: Rejected"),
                           (["Status: signed off with  conditions"], "Status: signed off with  conditions"),
                           (["Status: signed off with conditions, pending"], "Status: signed off with conditions, pending"),
                           (["Status: Signed off"], "Status: Signed off"),
                           (["Status:\u00a0signed off"], "Status:\u00a0signed off"),
                           (["Status:"], "Status:"),
                           (["Status: signed off", "and more"], "Status: signed off"),
                           (["Status: signed off", "---"], "Status: signed off"),
                           (["Status: signed off", "==="], "Status: signed off"),
                           (["Status: signed off", "\u00a0"], "Status: signed off"),
                           (["Status: signed off", "\u3000"], "Status: signed off")):
            text = two_slices(tail)
            with self.subTest(tail=tail):
                self.assert_stops(text, self.number(text, line))
        for head, line in ((["Base: abc123"], "Base: abc123"), (["Base: ABCDEF1"], "Base: ABCDEF1"),
                           (["Base: 1111111 the branch point"], "Base: 1111111 the branch point"),
                           (["Base:\u00a01111111"], "Base:\u00a01111111"),
                           (["Base: 1111111", "and more"], "Base: 1111111"),
                           (["Base: 1111111", "---"], "Base: 1111111")):
            text = two_slices(["Status: signed off"], header=head)
            with self.subTest(head=head):
                self.assert_stops(text, self.number(text, line, after=None))

    def test_a_label_that_ends_its_paragraph_counts(self):
        for tail, value in ((["Status: built"], "built"), (["Status: in progress", " \t"], "in progress"),
                            (["Status: rejected"], "rejected"),
                            (["Status: signed off with conditions \t"], "signed off with conditions"),
                            (["Status: not started \t", "### a note", "text"], "not started"),
                            (["Status: signed off", "```", "Status: built", "```"], "signed off"),
                            (["Status: signed off", "## Notes"], "signed off")):
            text = two_slices(tail)
            with self.subTest(tail=tail):
                self.assertEqual([s["status"] for s in gatemod.slices_of(text)], ["signed off", value])
                spec.clean(text)

    def test_a_label_at_the_docs_end_counts(self):
        text = "\n".join(["# T", "", "## Slice A %s the counter" % D, "Goal: count.", "Status: built"])
        for body in (text, text + "\n", text.replace("\n", "\r\n") + "\r\n"):
            self.assertEqual([s["status"] for s in gatemod.slices_of(body)], ["built"])

    def test_an_exact_base_that_ends_its_paragraph_is_the_base(self):
        for head in (["Base: 1111111"], ["Base: %s \t" % ("a" * 40)], ["Base: 1111111", "## Notes"],
                     ["Base: 1111111", "```", "Base: 2222222", "```"]):
            text = two_slices(["Status: signed off"], header=head)
            with self.subTest(head=head):
                self.assertEqual(gatemod.recorded_base(text)["commit"], head[0].split()[1])

    def test_label_lines_outside_a_slice_and_base_lines_outside_the_header_are_not_labels(self):
        """The rule reads `Status:` inside a slice's section and `Base:` in the header only, as the gate always
        did; a `Status:` line elsewhere is still removed from the spec (M6)."""
        text = two_slices(["Status: signed off", "", "Base: not a base here"],
                          header=["Status: an earlier reviewer's note", "more of the note"])
        self.assertEqual([s["status"] for s in gatemod.slices_of(text)], ["signed off", "signed off"])
        self.assertIsNone(gatemod.recorded_base(text))
        kept, removed = spec.clean(text)
        self.assertNotIn("an earlier reviewer's note", kept)


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
