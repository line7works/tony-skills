"""punch3-F9: the first-heading reader still let a builder-notes declaration through (E13 punch list
round 3, from the round 2 checker's report; F9's third round).

Each shape is a file whose first actual CommonMark heading is `# Builder notes` (or a Setext
`Builder notes`) and which round 2's walker read as having no declaring heading, so the file was
delivered and a verdict citing it recorded. Against `dfe8919` (withheld there):

1. a raw HTML block of type 2 or 3 whose end marker sits on its own start line (`<!-->`,
   `<!--->`, `<?>`): CommonMark ends the block on the first line, the start line included, that
   holds the end marker, so it closes at once;
2. a link reference definition whose destination is on the next line (`[a]:` then `===`): the
   definition opener never becomes a Setext heading's text.

Against `8133cb3` (withheld there):

3. an empty list item followed by a blank line (`-\\n\\n  # Builder notes`): a list item can begin
   with at most one blank line, so the item ends and the heading is top level;
4. a new list after a list item or a block quote (`- item\\n2. x`, `- item\\n1.`, `- a\\n-`,
   `> a\\n-`): the paragraph-interrupt restriction applies only when the innermost matched
   container is the paragraph itself, so the line starts a new list and what follows is top level.

Controls (delivered, accepted): a heading inside an item that continues it; the round 2 controls
CommonMark delivers; a definition with its title on the next line followed by `===` (no heading in
either reading); a later ordinary comment; a new ordered list whose lazy paragraph a thematic break
ends. The fix round's, round 1's and round 2's F9 modules are unchanged and still pass.

Each case plants `notes.md` in the S1-02 seeded case and runs the real `signoff.py` (`scope` for
the packet row; `record-answer` with an answer citing the file for the refusals).
"""
import unittest

import testlib
from test_punch2_f9 import BODY, _Punch2

testlib.add_scripts_to_path()

from signoff_core import packet  # noqa: E402


class Punch3F9HtmlEndOnTheStartLine(_Punch2):
    """Shape 1: a type 2 or 3 block closes on its start line when that line holds the marker."""

    def test_an_empty_comment(self):
        self.withheld("<!-->\n# Builder notes" + BODY)

    def test_an_empty_comment_three_dashes(self):
        self.withheld("<!--->\n# Builder notes" + BODY)

    def test_an_empty_processing_instruction(self):
        self.withheld("<?>\n# Builder notes" + BODY)

    def test_an_empty_processing_instruction_then_setext(self):
        self.withheld("<?>\n\nBuilder notes\n===" + BODY)

    def test_an_empty_comment_is_refused(self):
        self.refused("<!-->\n# Builder notes" + BODY)

    def test_an_empty_processing_instruction_is_refused(self):
        self.refused("<?>\n# Builder notes" + BODY)


class Punch3F9MultiLineDefinition(_Punch2):
    """Shape 2: a definition whose destination is on the next line."""

    def test_the_destination_on_the_next_line(self):
        self.withheld("[a]:\n===\n# Builder notes" + BODY)

    def test_the_destination_then_a_setext_heading(self):
        self.withheld("[a]:\n/url\nBuilder notes\n===" + BODY)

    def test_a_definition_opener_read_as_a_heading(self):
        # the reference implementation reads `[Builder notes]:` over `===` as a heading
        self.withheld("[Builder notes]:\n===" + BODY)

    def test_the_destination_on_the_next_line_is_refused(self):
        self.refused("[a]:\n===\n# Builder notes" + BODY)


class Punch3F9EmptyItemThenBlank(_Punch2):
    """Shape 3: an empty list item followed by a blank line ends there."""

    def test_an_empty_bullet(self):
        self.withheld("-\n\n  # Builder notes" + BODY)

    def test_an_empty_star(self):
        self.withheld("*\n\n  # Builder notes" + BODY)

    def test_an_empty_ordered_item(self):
        self.withheld("1.\n\n   # Builder notes" + BODY)

    def test_an_empty_bullet_then_setext(self):
        self.withheld("-\n\n  Builder notes\n  ---" + BODY)

    def test_an_empty_bullet_is_refused(self):
        self.refused("-\n\n  # Builder notes" + BODY)


class Punch3F9NewSiblingList(_Punch2):
    """Shape 4: a list item that cannot interrupt a paragraph still starts a new list where the
    innermost matched container is not that paragraph."""

    def test_an_ordered_item_not_at_one(self):
        self.withheld("- item\n2. x\n  # Builder notes" + BODY)

    def test_an_empty_ordered_item(self):
        self.withheld("- item\n1.\n  # Builder notes" + BODY)

    def test_an_empty_bullet_after_a_bullet(self):
        self.withheld("- a\n-\nBuilder notes\n---" + BODY)

    def test_an_empty_bullet_after_an_ordered_item(self):
        self.withheld("10. z\n-\nBuilder notes\n---" + BODY)

    def test_an_empty_bullet_after_a_quote(self):
        self.withheld("> a\n-\nBuilder notes\n---" + BODY)

    def test_nested_in_a_quote(self):
        self.withheld("> - item\n> 2. x\n>   # y\n\n# Builder notes" + BODY)

    def test_an_ordered_item_not_at_one_is_refused(self):
        self.refused("- item\n2. x\n  # Builder notes" + BODY)

    def test_an_empty_bullet_after_a_quote_is_refused(self):
        self.refused("> a\n-\nBuilder notes\n---" + BODY)


class Punch3F9Controls(_Punch2):
    """What CommonMark delivers stays delivered."""

    def test_a_heading_inside_an_empty_item_it_continues(self):
        self.delivered("-\n  # Builder notes\n\ntext\n")

    def test_a_heading_inside_an_item_after_a_blank(self):
        self.delivered("- a\n\n  # Builder notes\n\ntext\n")

    def test_a_list_item_interrupts_a_paragraph(self):
        self.delivered("Builder notes\n- item\n---\n\ntext\n")

    def test_a_lazy_equals_line_stays_in_the_quote(self):
        self.delivered("> quoted\nBuilder notes\n===\n\ntext\n")

    def test_an_ordered_item_in_the_paragraph_of_an_item(self):
        self.delivered("- item\n  2. x\n  Builder notes\n  ---\n\ntext\n")

    def test_a_new_list_whose_lazy_line_a_break_ends(self):
        self.delivered("> a\n2. x\nBuilder notes\n---\n\ntext\n")

    def test_a_definition_with_its_title_on_the_next_line(self):
        self.delivered("[a]: /u\n\"Builder notes\"\n===\n\ntext\n")

    def test_a_comment_then_another_first_heading(self):
        self.delivered("<!-- a note -->\n# Widths measured\n\n## Builder notes\n")

    def test_a_closed_comment_block_then_another_heading(self):
        self.delivered("<!--\n# Builder notes\n-->\n# Widths measured\n")


class Punch3F9Reader(unittest.TestCase):
    """The reader itself, on the round 2 checker's direct-read shapes."""

    def test_the_checkers_direct_reads(self):
        for text in ("<!-->\n# Builder notes\n", "<!--->\n# Builder notes\n",
                     "<?>\n# Builder notes\n", "-\n\n  # Builder notes\n",
                     "- item\n2. x\n  # Builder notes\n", "- item\n1.\n  # Builder notes\n",
                     "- a\n-\nBuilder notes\n---\n", "> a\n-\nBuilder notes\n---\n"):
            self.assertEqual(packet.first_headings(text), ["Builder notes"], repr(text))

    def test_a_definition_is_read_both_ways(self):
        self.assertEqual(packet.first_headings("[a]:\n===\n# Builder notes\n"),
                         ["Builder notes", "[a]:"])


if __name__ == "__main__":
    unittest.main()
