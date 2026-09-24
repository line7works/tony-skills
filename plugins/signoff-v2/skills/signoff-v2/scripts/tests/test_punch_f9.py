"""punch-F9: Setext, indented and long-fence headings hid a builder-notes declaration (E13 punch list).

Astra's recheck left F9 (MAJOR) partly closed: "Stricter Setext, indented-heading and
four-backtick-fence cases still produce `kind: source`, `delivered: true`, then
`verdict_recorded: true`." `packet.first_heading` read only a `#` heading at column 0, and closed a
fence at the first line starting with three of its characters.

Each shape plants `notes.md` in the S1-02 seeded case and runs the real `signoff.py`: `scope` for
the packet row, then `record-answer` with an answer citing the file, which must be an
`independence` refusal. Beyond her three instances: a `---` Setext underline, an ATX heading
indented one and three spaces, a closing `#` sequence, a four-tilde fence, a five-backtick fence
with a four-backtick line inside, a backtick fence that tildes do not close, a fence indented by
up to three spaces, an HTML comment hiding a decoy heading, frontmatter with no closing line, and a `---` first line that is both a frontmatter opener and a Setext underline.
Controls: four-space indentation is code, not a heading; a decoy heading inside a fence is never
the first heading; `#hashtag` is no heading; a Setext underline after a blank line is a thematic
break; and the fix round's "only the first heading decides" still delivers a file whose first
heading is not a declaration.
"""
import json
import os
import unittest

import testlib
from test_fix2_astra import _Case

testlib.add_scripts_to_path()

BODY = "\n\nThe separator case passed for me.\n"


class _Punch(_Case):

    REL = "notes.md"

    def row(self):
        packet = testlib.load_json(os.path.join(self.run_dir, "packet", "packet.json"))
        return [r for r in packet["files"] if r["path"] == self.REL][0], packet

    def withheld(self, text):
        self.write(self.REL, text)
        code, body, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(body))
        row, packet = self.row()
        self.assertEqual((row["kind"], row["delivered"]), ("builder_conversation", False),
                         json.dumps(row))
        self.assertNotIn("passed for me", testlib.read_text(packet["material_path"]))

    def refused(self, text):
        self.write(self.REL, text)
        answer = self.answer()
        answer["notes"] = "Evidence: notes.md confirms the separator case."
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["refusal_reason"], "independence", json.dumps(result)[:1200])
        self.assertFalse(result["verdict_recorded"])

    def delivered(self, text):
        self.write(self.REL, text)
        code, body, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(body))
        row, _ = self.row()
        self.assertEqual((row["kind"], row["delivered"]), ("source", True), json.dumps(row))


class PunchF9Setext(_Punch):
    """Her Setext instance, both underlines."""

    def test_an_equals_underline(self):
        self.withheld("Builder notes\n=============" + BODY)

    def test_a_dash_underline(self):
        self.withheld("Builder's notes\n---" + BODY)

    def test_after_frontmatter(self):
        self.withheld("---\ntitle: x\n---\n\nBuild notes\n===" + BODY)

    def test_a_setext_answer_is_refused(self):
        self.refused("Builder notes\n=============" + BODY)


class PunchF9Indented(_Punch):
    """Her indented instance: an ATX heading indented up to three spaces."""

    def test_three_spaces(self):
        self.withheld("   # Builder notes" + BODY)

    def test_one_space_with_a_closing_sequence(self):
        self.withheld(" ## Builder notes ##" + BODY)

    def test_an_indented_answer_is_refused(self):
        self.refused("  # Builder notes" + BODY)


class PunchF9LongFences(_Punch):
    """Her four-backtick instance: a fence is closed only by a fence at least as long, of the same
    character."""

    def test_four_backticks_hiding_a_three_backtick_line_and_a_decoy(self):
        self.withheld("````md\n```\n# Padding design\n````\n\n# Builder notes" + BODY)

    def test_four_tildes(self):
        self.withheld("~~~~\n~~~\n# Padding design\n~~~~\n# Builder notes" + BODY)

    def test_a_backtick_fence_is_not_closed_by_tildes(self):
        self.withheld("```\n~~~\n# Padding design\n```\n# Builder notes" + BODY)

    def test_five_backticks(self):
        self.withheld("`````\n````\n# Padding design\n`````\n# Builder notes" + BODY)

    def test_an_indented_fence(self):
        self.withheld("   ````\n   ```\n# Padding design\n   ````\n# Builder notes" + BODY)

    def test_a_long_fence_answer_is_refused(self):
        self.refused("````md\n```\n# Padding design\n````\n\n# Builder notes" + BODY)


class PunchF9OtherHiders(_Punch):
    """Other things that could hide the first heading: an HTML comment, unterminated frontmatter,
    and a `---` first line read both ways."""

    def test_an_html_comment_hiding_a_decoy(self):
        self.withheld("<!--\n# Padding design\n-->\n# Builder notes" + BODY)

    def test_frontmatter_that_never_closes(self):
        self.withheld("---\ntitle: x\n\n# Builder notes" + BODY)

    def test_a_dash_line_that_is_a_setext_underline(self):
        self.withheld("---\nBuilder notes\n---" + BODY)


class PunchF9Controls(_Punch):
    """What is not a heading stays not a heading; the first heading still decides."""

    def test_four_spaces_is_code(self):
        self.delivered("    # Builder notes\n\n# Padding design" + BODY)

    def test_a_decoy_inside_a_fence_is_not_first(self):
        self.delivered("```\n# Builder notes\n```\n# Padding design" + BODY)

    def test_a_hashtag_is_not_a_heading(self):
        self.delivered("#Builder notes\n\n# Padding design" + BODY)

    def test_a_first_heading_that_is_not_a_declaration(self):
        self.delivered("Padding design\n==============\n\n## Builder notes" + BODY)

    def test_a_dash_line_after_a_blank_is_a_thematic_break(self):
        self.delivered("Builder notes\n\n---\n\n# Padding design" + BODY)


if __name__ == "__main__":
    unittest.main()
