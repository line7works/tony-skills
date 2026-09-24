"""punch2-F3: two spellings of a withheld builder-notes path still reached a verdict (E13 punch list
round 2, from the independent checker's round 1 report, MINOR).

1. A soft-wrapped path: the answer's prose breaks the line at the path's own space
   (`./builder\\nnotes.md`). A Markdown soft line break renders as that space, so the reader of the
   answer sees `./builder notes.md`.
2. A relative path that climbs out of the workspace and back in by the folder's own name
   (`../workspace/builder%20notes.md`, the seeded workspace folder being named `workspace`). The
   contract resolves `..` segments and drops a path OUTSIDE the workspace; resolved against the
   workspace, this one is inside it.

Widened: a CRLF soft break, a wrap with indentation on the next line, a two-space hard break, a
wrap in a directory name holding a space, a climb out and in through two levels, and an absolute
path that climbs out and back in. Controls: a DELIVERED file with a space in its name, cited
wrapped, is accepted; a climb out to a sibling folder that merely shares the file's name is
accepted (it is outside the workspace and resolves to nothing).

Each case plants the withheld files in the S3-03 seeded case and runs the real `signoff.py` through
`record-answer`: an `independence` refusal before any verdict or finding is written.
"""
import os
import unittest

from test_punch_f3 import _Punch

DIR_SPACED = "my docs/builder-log.md"


class Punch2F3SoftWrap(_Punch):
    """A path broken across lines at its own space."""

    def test_the_checkers_instance(self):
        self.refused(self.with_notes("the proof sits in ./builder\nnotes.md, section proof"))

    def test_a_crlf_soft_break(self):
        self.refused(self.with_notes("the proof sits in ./builder\r\nnotes.md, section proof"))

    def test_an_indented_continuation_line(self):
        self.refused(self.with_notes("the proof sits in ./builder\n    notes.md, section proof"))

    def test_a_hard_break(self):
        self.refused(self.with_notes("the proof sits in builder  \nnotes.md#proof"))

    def test_a_wrap_in_a_directory_name(self):
        self.write(DIR_SPACED, "text\n")
        answer = self.with_notes("the log is ./my\ndocs/builder-log.md")
        self._declare(DIR_SPACED)
        self.refused(answer)

    def _declare(self, rel):
        """Name `rel` in the input's builder_conversation list."""
        import json
        with open(self.input_path) as fh:
            doc = json.load(fh)
        doc["review"]["builder_conversation"] = (doc["review"].get("builder_conversation") or []) + [rel]
        with open(self.input_path, "w") as fh:
            json.dump(doc, fh)


class Punch2F3ClimbOutAndIn(_Punch):
    """A relative path that leaves the workspace and comes back in by the folder's own name."""

    def test_the_checkers_instance(self):
        self.assertEqual(os.path.basename(self.workspace), "workspace")
        self.refused(self.with_notes("see ../workspace/builder%20notes.md"))

    def test_two_levels(self):
        parent = os.path.basename(os.path.dirname(self.workspace))
        self.refused(self.with_notes("see [n](<../../%s/workspace/builder notes.md>)" % parent))

    def test_an_absolute_path_through_the_parent(self):
        self.refused(self.with_notes("see %s/../workspace/builder notes.md"
                                     % self.workspace))


class Punch2F3Controls(_Punch):
    """What names another file is accepted."""

    def accepted(self, answer):
        self.plant()
        self.write("docs/field notes.md", "# Field\n\nmeasured widths.\n")
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 0, "the answer was refused: %s %s" % (err, body))

    def test_a_delivered_spaced_file_cited_wrapped(self):
        self.accepted(self.with_notes("measured in ./docs/field\nnotes.md, section a"))

    def test_a_sibling_folder_outside_the_workspace(self):
        self.accepted(self.with_notes("compare ../other/builder%20notes.md, which is not ours"))


if __name__ == "__main__":
    unittest.main()
