"""punch-F3: a withheld builder-notes file cited through a spelling the tokenizer missed (E13 punch list).

Astra's recheck left F3 (MAJOR) partly closed: "`probe_stricter.py`: `[source](<./builder
notes.md#proof>)` still produces `completed / verdict_recorded: true`, despite that file being
explicitly withheld." `MD_DESTINATION` stopped at the space inside the angle brackets, so the
destination never reached `canonical`.

Each class below plants a withheld builder-notes file whose path needs a CommonMark spelling
(`builder notes.md`, a space; `docs/builder-notes(1).md`, parentheses) in the S3-03 seeded case,
runs the real `signoff.py` through `record-answer`, and asserts the answer is an `independence`
refusal before any verdict or finding is written. Covered: her instance; every spelling class the
fix round's F3 module covers (`./`, absolute, percent encoding, `file://`, a Markdown destination
with a fragment, `..` segments, a check output, a check command, a kept note) re-run on the spaced
path; angle-bracket destinations with and without a title; a bare `<...>` token with a space, and a
`file://` one; `%20`; a reference-style link with its definition line (angle and `%20` forms);
an HTML `<a href>` and `<img src>` with the space; a citation inside a link title; backslash-
escaped and balanced parentheses in a destination; a shell-quoted and a backslash-escaped space in
a check command; and prose that names the spaced path with no markup at all. Controls: a
DELIVERED file with a space in its name, cited the same ways, is still accepted.
"""
import json
import os
import unittest

import testlib
from test_fix2_astra import _Case, read_log

testlib.add_scripts_to_path()

SPACED = "builder notes.md"
PARENS = "docs/builder-notes(1).md"
NOTES_TEXT = "# Builder notes\n\nproof: the separator case was run by hand.\n"


class _Punch(_Case):

    CASE = "S3-03-builder-notes-untracked"

    def setUp(self):
        _Case.setUp(self)

    def plant(self):
        self.write(SPACED, NOTES_TEXT)
        self.write(PARENS, NOTES_TEXT)

    def refused(self, answer):
        self.plant()
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 10, "the answer was accepted: %s %s" % (err, json.dumps(body)))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1200])
        self.assertEqual(result["refusal_reason"], "independence", json.dumps(result["problems"]))
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(result["findings"], [], "no finding is written")
        self.assertEqual(read_log(self.workspace), [])
        withheld = [row["path"] for row in result["packet"]["files"] if not row["delivered"]]
        self.assertIn(SPACED, withheld, "the planted file is withheld builder material")

    def with_notes(self, text):
        answer = self.answer()
        answer["notes"] = text
        return answer

    def abs(self, rel):
        return os.path.join(self.workspace, rel)


class PunchF3HerInstanceAndAngleForms(_Punch):
    """Her probe, then the angle-bracket family."""

    def test_her_instance(self):
        self.refused(self.with_notes("[source](<./builder notes.md#proof>)"))

    def test_an_angle_destination_without_dot_slash(self):
        self.refused(self.with_notes("see [the notes](<builder notes.md>)"))

    def test_an_angle_destination_with_a_title(self):
        self.refused(self.with_notes('see [the notes](<./builder notes.md> "proof")'))

    def test_an_image_with_an_angle_destination(self):
        self.refused(self.with_notes("![shot](<./builder notes.md>)"))

    def test_a_bare_angle_token_with_a_space(self):
        self.refused(self.with_notes("per <./builder notes.md#proof>, it ran"))

    def test_a_bare_angle_file_url_with_a_space(self):
        self.refused(self.with_notes("per <file://%s>" % self.abs(SPACED)))

    def test_a_citation_inside_a_link_title(self):
        self.refused(self.with_notes(
            '[columns](src/signpost/columns.py "as <./builder notes.md> says")'))


class PunchF3TheFixRoundClassesOnTheSpacedPath(_Punch):
    """Every spelling class of the fix round's F3 module, re-run on a path with a space."""

    def test_dot_slash_in_prose(self):
        self.refused(self.with_notes("Evidence: ./builder notes.md:2 says the case was run."))

    def test_bare_path_in_prose(self):
        self.refused(self.with_notes("Evidence: builder notes.md line 2."))

    def test_an_absolute_path(self):
        self.refused(self.with_notes("Evidence: %s:2 says so." % self.abs(SPACED)))

    def test_percent_encoded_space(self):
        self.refused(self.with_notes("Evidence: ./builder%20notes.md#proof"))

    def test_percent_encoded_in_a_destination(self):
        self.refused(self.with_notes("[x](./builder%20notes.md#proof)"))

    def test_a_file_url(self):
        self.refused(self.with_notes("See file://%s#L2." % self.abs("builder%20notes.md")))

    def test_a_relative_segment(self):
        self.refused(self.with_notes("[x](<src/../builder notes.md>)"))

    def test_in_a_check_output(self):
        answer = self.answer()
        answer["checks_executed"][0]["output"] = "OK\n(cross-checked with [n](<./builder notes.md>))"
        self.refused(answer)

    def test_in_a_check_command_shell_quoted(self):
        answer = self.answer()
        answer["checks_executed"].append({"name": "read", "command": 'cat "./builder notes.md"',
                                          "exit_code": 0, "output": "read"})
        self.refused(answer)

    def test_in_a_check_command_backslash_escaped(self):
        answer = self.answer()
        answer["checks_executed"].append({"name": "read", "command": "cat ./builder\\ notes.md",
                                          "exit_code": 0, "output": "read"})
        self.refused(answer)

    def test_in_a_kept_note(self):
        answer = self.answer()
        answer["notes_kept"] = [{"location": "src/signpost/columns.py:2", "severity": "MINOR",
                                 "claim": "see [n](<./builder notes.md#proof>)",
                                 "scenario": "none", "evidence_kind": "read"}]
        self.refused(answer)


class PunchF3OtherTokenizerGaps(_Punch):
    """Reference-style links, HTML attributes, escaped and balanced parentheses."""

    def test_a_reference_link_with_an_angle_definition(self):
        self.refused(self.with_notes("See [the notes][n].\n\n[n]: <./builder notes.md> \"proof\""))

    def test_a_reference_link_with_a_percent_encoded_definition(self):
        self.refused(self.with_notes("See [n].\n\n  [n]: ./builder%20notes.md#proof"))

    def test_an_html_anchor(self):
        self.refused(self.with_notes('<a href="./builder notes.md#proof">the notes</a>'))

    def test_an_html_anchor_single_quoted_with_an_entity(self):
        self.refused(self.with_notes("<a href='./builder&#32;notes.md'>n</a>"))

    def test_an_html_image(self):
        self.refused(self.with_notes('<img src="builder notes.md">'))

    def test_backslash_escaped_parentheses(self):
        self.refused(self.with_notes("[x](./docs/builder-notes\\(1\\).md)"))

    def test_balanced_parentheses(self):
        self.refused(self.with_notes("[x](./docs/builder-notes(1).md#proof)"))


class PunchF3Controls(_Punch):
    """A DELIVERED file with a space in its name is cited the same ways and still accepted."""

    DELIVERED = "src/signpost/spaced name.py"

    def accepted(self, text):
        self.write(self.DELIVERED, "X = 1\n")
        answer = self.answer()
        answer["notes"] = text
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(body))

    def test_an_angle_destination_to_a_delivered_spaced_file(self):
        self.accepted("[x](<./src/signpost/spaced name.py#L1>) and <src/signpost/spaced name.py>")

    def test_an_html_anchor_to_a_delivered_file(self):
        self.accepted('<a href="./src/signpost/columns.py">columns</a>')


if __name__ == "__main__":
    unittest.main()
