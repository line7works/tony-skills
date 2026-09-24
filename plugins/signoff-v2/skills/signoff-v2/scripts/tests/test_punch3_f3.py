"""punch3-F3: a withheld builder-notes path broken at its space by a BACKSLASH hard line break still
reached a verdict (E13 punch list round 3, the round 2 checker's remainder, MINOR).

`the proof sits in ./builder\\` then a line ending, then `notes.md, section proof`: a backslash
before the line ending is CommonMark's other hard line break, which renders where the space was.
The contract's words (each space of a withheld path "also matches a line break with the blanks
around it (a Markdown soft or hard line break renders there)") already cover it; the pattern
allowed blanks around the line ending but not the backslash.

Widened: a CRLF line ending after the backslash, a backslash break with indentation on the next
line, and the same break inside a folder name. Controls: a DELIVERED file with a space in its name,
cited with a backslash break, is accepted; a backslash break that splits a name no withheld file
has is accepted.

Each case plants the withheld files in the S3-03 seeded case and runs the real `signoff.py` through
`record-answer`: an `independence` refusal before any verdict or finding is written.
"""
import unittest

import test_punch2_f3 as round2
from test_punch_f3 import _Punch


class Punch3F3BackslashBreak(_Punch):
    """A path broken across lines at its own space by a backslash hard line break."""

    def test_the_checkers_instance(self):
        self.refused(self.with_notes("the proof sits in ./builder\\\nnotes.md, section proof"))

    def test_a_crlf_line_ending(self):
        self.refused(self.with_notes("the proof sits in ./builder\\\r\nnotes.md, section proof"))

    def test_an_indented_continuation_line(self):
        self.refused(self.with_notes("the proof sits in builder\\\n   notes.md#proof"))

    def test_a_break_in_a_directory_name(self):
        self.write(round2.DIR_SPACED, "text\n")
        answer = self.with_notes("the log is ./my\\\ndocs/builder-log.md")
        round2.Punch2F3SoftWrap._declare(self, round2.DIR_SPACED)
        self.refused(answer)


class Punch3F3Controls(_Punch):
    """What names another file is accepted."""

    accepted = round2.Punch2F3Controls.accepted

    def test_a_delivered_spaced_file_cited_with_a_backslash_break(self):
        self.accepted(self.with_notes("measured in ./docs/field\\\nnotes.md, section a"))

    def test_a_backslash_break_between_other_words(self):
        self.accepted(self.with_notes("the widths held\\\nnotes follow in the report"))


if __name__ == "__main__":
    unittest.main()
