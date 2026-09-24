"""punch2-F9: the first-heading reader still let a builder-notes declaration through (E13 punch list
round 2, from the independent checker's round 1 report).

The checker's four shapes, each a file whose first actual CommonMark heading is `# Builder notes`
(or a Setext `Builder notes`) and which `packet.first_headings` read as source, delivered and let a
verdict record:

1. a REGRESSION against `dfe8919`: a list-item or block-quote line, then `---`, then
   `# Builder notes`. A Setext underline cannot follow a list item or a lazy block-quote line, so
   the `---` is a thematic break (`- first item\\n---\\n# Builder notes`,
   `> a quoted line\\n---\\n# Builder notes`);
2. a Setext heading in a CRLF file (`Builder notes\\r\\n====\\r\\n`);
3. a raw HTML block of CommonMark type 6 (`<div>`, `<details>`) holding a decoy heading; the block
   ends at a blank line and nothing inside it is a heading;
4. a leading UTF-8 byte order mark before `# Builder notes`.

Widened in the same class: a bare carriage-return file, a type-7 HTML block (`<span>` alone on its
line), a processing instruction, a `<!DOCTYPE ...>` and a CDATA block holding a decoy, a type-1 block
closed by another type-1 end tag, a link reference definition that a following `===` would
otherwise turn into a decoy Setext heading, an ordered list item and a `*` item before `---`, a
block quote holding a fence, and a list item whose lazy continuation holds an `===` line.

Controls (delivered, accepted): the first heading is something else; four-space indented code; a
heading inside a block quote or a list item and an HTML `<h1>` (the contract's exclusions); a list
item that interrupts a paragraph before a `---` (no heading at all in CommonMark); a lazy `===`
after a block quote (paragraph text inside the quote); a type-7 tag cannot interrupt a paragraph,
so a Setext heading after it still counts (withheld). The fix round's and round 1's F9 modules are
unchanged and still pass.

Each case plants `notes.md` in the S1-02 seeded case and runs the real `signoff.py` (`scope` for
the packet row; `record-answer` with an answer citing the file for the refusals).
"""
import os
import unittest

import testlib
from test_punch_f9 import _Punch

testlib.add_scripts_to_path()

from signoff_core import packet  # noqa: E402

BODY = "\n\nThe separator case passed for me.\n"


class _Punch2(_Punch):

    def write(self, rel, text):
        """Bytes exactly as given: a CRLF or bare-CR file keeps its line endings."""
        path = os.path.join(self.workspace, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(text.encode("utf-8"))


class Punch2F9ListOrQuoteThenBreak(_Punch2):
    """Shape 1, the regression: `---` after a list item or a block-quote line is a thematic
    break, so `# Builder notes` is the first heading."""

    def test_a_list_item_then_a_break(self):
        self.withheld("- first item\n---\n# Builder notes\n\ntext\n")

    def test_a_quote_line_then_a_break(self):
        self.withheld("> a quoted line\n---\n# Builder notes\n\ntext\n")

    def test_an_ordered_item_then_a_break(self):
        self.withheld("1. first item\n---\n# Builder notes" + BODY)

    def test_a_star_item_then_a_break(self):
        self.withheld("* first item\n---\nBuilder notes\n=============" + BODY)

    def test_a_list_item_then_a_break_is_refused(self):
        self.refused("- first item\n---\n# Builder notes\n\ntext\n")

    def test_a_quote_line_then_a_break_is_refused(self):
        self.refused("> a quoted line\n---\n# Builder notes\n\ntext\n")


class Punch2F9LineEndings(_Punch2):
    """Shape 2: line endings are normalised before the block walk (CRLF, and a bare CR)."""

    def test_a_crlf_setext_heading(self):
        self.withheld("Builder notes\r\n====\r\n\r\ntext\r\n")

    def test_a_bare_cr_setext_heading(self):
        self.withheld("Builder notes\r----\r\rtext\r")

    def test_a_crlf_setext_heading_is_refused(self):
        self.refused("Builder notes\r\n====\r\n\r\ntext\r\n")


class Punch2F9HtmlBlocks(_Punch2):
    """Shape 3: a raw HTML block holds no heading; types 6 and 7 end at a blank line, types 1 to 5
    at their end marker."""

    def test_a_div_block(self):
        self.withheld("<div>\n# Fake\n</div>\n\n# Builder notes\n\ntext\n")

    def test_a_details_block(self):
        self.withheld("<details>\n## Fake summary\n</details>\n\n# Builder notes\n\ntext\n")

    def test_a_closing_type6_tag_opens_a_block(self):
        self.withheld("</section>\n# Fake\n\n# Builder notes" + BODY)

    def test_a_type7_tag_alone_on_its_line(self):
        self.withheld("<span class=\"x\">\n# Fake\n</span>\n\n# Builder notes" + BODY)

    def test_a_processing_instruction(self):
        self.withheld("<?php\n# Fake\n?>\n# Builder notes" + BODY)

    def test_a_declaration(self):
        self.withheld("<!DOCTYPE\n# Fake\n>\n# Builder notes" + BODY)

    def test_a_cdata_block(self):
        self.withheld("<![CDATA[\n# Fake\n]]>\n# Builder notes" + BODY)

    def test_a_type1_block_closed_by_another_type1_end_tag(self):
        self.withheld("<pre>\n# Fake\n</script>\n# Builder notes" + BODY)

    def test_a_div_block_is_refused(self):
        self.refused("<div>\n# Fake\n</div>\n\n# Builder notes\n\ntext\n")


class Punch2F9ByteOrderMark(_Punch2):
    """Shape 4: a leading byte order mark is not part of the first line."""

    def test_a_bom_before_an_atx_heading(self):
        self.withheld("﻿# Builder notes\n\ntext\n")

    def test_a_bom_before_frontmatter(self):
        self.withheld("﻿---\ntitle: x\n---\n# Builder notes" + BODY)

    def test_a_bom_is_refused(self):
        self.refused("﻿# Builder notes\n\ntext\n")


class Punch2F9Containers(_Punch2):
    """Block quotes and list items are containers: their content never makes a top-level heading
    and never lends a line to a top-level Setext heading; a line that leaves them is read at the
    top level."""

    def test_a_link_reference_definition_is_no_setext_text(self):
        self.withheld("[x]: /u\n===\n# Builder notes" + BODY)

    def test_a_quoted_fence_does_not_take_a_lazy_line(self):
        self.withheld("> ```\n> text\nBuilder notes\n===" + BODY)

    def test_an_atx_heading_leaves_a_quote(self):
        self.withheld("> a quoted line\n# Builder notes" + BODY)

    def test_an_atx_heading_leaves_a_list(self):
        self.withheld("- first item\n# Builder notes" + BODY)

    def test_a_fence_in_a_list_item_is_closed_by_the_item(self):
        self.withheld("- ```\n  # Padding design\n  ```\n# Builder notes" + BODY)


class Punch2F9Controls(_Punch2):
    """What is not a heading stays not a heading; the contract's exclusions stay excluded; the
    first heading still decides."""

    def test_a_first_heading_that_is_not_a_declaration(self):
        self.delivered("# Widths measured\n\n## Builder notes\n\ntext\n")

    def test_four_spaces_is_code(self):
        self.delivered("    # Builder notes\n\n# Widths measured\n")

    def test_a_heading_inside_a_block_quote(self):
        self.delivered("> # Builder notes\n\ntext\n")

    def test_a_heading_inside_a_list_item(self):
        self.delivered("- # Builder notes\n\ntext\n")

    def test_an_html_h1(self):
        self.delivered("<h1>Builder notes</h1>\n\ntext\n")

    def test_a_list_item_interrupts_a_paragraph(self):
        self.delivered("Builder notes\n- item\n---\n\ntext\n")

    def test_a_lazy_equals_line_stays_in_the_quote(self):
        self.delivered("> quoted\nBuilder notes\n===\n\ntext\n")

    def test_a_type7_tag_does_not_interrupt_a_paragraph(self):
        self.withheld("Builder notes\n<span>\n===" + BODY)

    def test_a_decoy_in_a_type6_block_after_a_real_first_heading(self):
        self.delivered("# Widths measured\n\n<div>\n# Builder notes\n</div>\n")


class Punch2F9Reader(unittest.TestCase):
    """The reader itself, on the checker's direct-read shapes."""

    def test_the_checkers_direct_reads(self):
        for text in ("- first item\n---\n# Builder notes\n",
                     "> a quoted line\n---\n# Builder notes\n",
                     "<div>\n# Fake\n</div>\n\n# Builder notes\n",
                     "Builder notes\r\n====\r\n",
                     "﻿# Builder notes\n"):
            self.assertEqual(packet.first_headings(text), ["Builder notes"], repr(text))


if __name__ == "__main__":
    unittest.main()
