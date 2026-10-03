"""A builder's-notes file declared by its first heading (C1A3-3; the E15 lane contract A5 (3); contract
section 5, the allow rule's (3)).

The first heading is read wide: every heading-shaped line up to the first certain heading (an ATX heading at
the left margin, outside every fence, with no raw HTML before it and after any front matter) is a candidate,
so a declaration a CommonMark reader would see as the first heading is never missed. A declaration that only
a later heading makes, after a certain first heading, is not one. What is fenced is the strict rule's (A8,
`fences.py`): a margin fence it accepts holds its lines; from the first fence line the rule cannot place, no
heading is certain, so every later heading-shaped line is a candidate (C1A4-1). A notes file never stops the
run.
"""
import unittest

import testlib

testlib.add_scripts_to_path()
from vertical_core import notes  # noqa: E402

BODY = "\n\nthe counter is obviously right\n"


class TheFirstHeading(unittest.TestCase):

    def declared(self, text):
        self.assertIsNotNone(notes.declares(text), repr(text))

    def kept(self, text):
        self.assertIsNone(notes.declares(text), repr(text))

    def test_the_declaring_words_in_an_atx_first_heading(self):
        for heading in ("# Builder notes", "## builder's notes", "# Builders notes", "### Build notes",
                        "# Notes from the builder", "   # BUILDER NOTES #", "#\tBuild notes"):
            self.declared(heading + BODY)

    def test_a_setext_first_heading_over_two_lines(self):
        self.declared("Builder\nnotes\n=====" + BODY)
        self.declared("Build notes\n---" + BODY)

    def test_after_front_matter_and_in_its_setext_reading(self):
        self.declared("---\ntitle: x\n---\n\n# Builder notes" + BODY)
        self.declared("---\nBuilder notes\n---\n\n# Plain" + BODY)

    def test_past_a_fenced_example_an_html_comment_and_blank_lines(self):
        self.declared("\n\n```\n# Plain example\n```\n\n# Builder notes" + BODY)
        self.declared("````\n```\n# Plain\n````\n# Build notes" + BODY)
        self.declared("<!--\n# Plain\n-->\n# Builder notes" + BODY)
        self.declared("<!-->\n# Builder notes" + BODY)

    def test_inside_containers_and_with_crlf_and_a_bom(self):
        self.declared("> # Builder notes" + BODY)
        self.declared("- # Build notes" + BODY)
        self.declared("﻿# Builder notes\r\n\r\nbody\r\n")

    def test_check_4s_lazy_list_shape_never_hides_a_declaring_first_heading(self):
        """C1A4-1: CommonMark ends the list item's fence at the margin line, so `# Intro` is code and `# Builder
        notes` is the first heading; the reader no longer takes `# Intro` as a certain first heading."""
        self.declared("- a\nlazy\n  ```\n```\n# Intro\n```\n# Builder notes\n```\n")
        self.declared("1. a\nlazy\n   ~~~\n~~~\n# Intro\n~~~\n# Build notes\n")

    def test_past_any_fence_line_the_rule_cannot_place(self):
        for shape in ("  ```", "> ```", "- ```", "```x`y", "```"):
            self.declared(shape + "\n# Intro\n" + shape + "\n# Builder notes" + BODY)

    def test_a_certain_first_heading_before_a_fence_line_the_rule_cannot_place_still_counts(self):
        self.kept("# Bench guide\n\n- a\nlazy\n  ```\n# Builder notes\n")

    def test_a_file_whose_first_heading_does_not_declare_it_is_kept(self):
        self.kept("# Bench notes\n\n## Build notes\n\nlater sections do not declare the file\n")
        self.kept("# Turnstile\n\nThe builder notes nothing here.\n")
        self.kept("no heading at all\n")
        self.kept("#Builder notes is no heading\n\n# Plain\n")


if __name__ == "__main__":
    unittest.main()
