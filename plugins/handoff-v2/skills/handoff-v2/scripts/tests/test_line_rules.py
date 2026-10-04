"""CR-17 (the E15 lane contract A22 (1)): every line handoff-v2 reads from a build doc to decide anything goes
through vertical-v2's plain-structure line rules (A8's strict fences, A9's raw HTML lines, A12's plain structure,
A16's character list), copied into `handoff_core/fences.py` byte for byte and held equal here.

`TheCopy` holds the copy to vertical-v2's file (skipped, never passed, in the installed shape) and to its
statement and character list. `TheReading` drives `handoff_core/doc.py` on the four shapes CR-17 names (a fenced
`## Handoffs` heading, a raw HTML line, an indented heading, an unlisted character) and on handoff-v2's own two
labels (`Depends on:` and `Questions:`), read the plain way. `TheStops` drives the same shapes through the real CLI:
each stops `doc-unreadable` before any write, naming the line.
"""
import hashlib
import os
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import doc as docmod, fences  # noqa: E402

D = hlib.D
VERTICAL_FENCES = ("vertical-v2", "skills", "vertical-v2", "scripts", "vertical_core", "fences.py")


def vertical_copy():
    path = testlib.checkout_sibling("vertical-v2")
    return None if path is None else os.path.join(os.path.dirname(path), *VERTICAL_FENCES)


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TheCopy(unittest.TestCase):

    def test_the_line_rules_are_vertical_v2s_file_byte_for_byte(self):
        theirs = vertical_copy()
        if theirs is None or not os.path.isfile(theirs):
            self.skipTest("vertical-v2 is not beside this core (the installed shape): the copy cannot be compared "
                          "here, and this is reported as skipped, not passed")
        mine = os.path.join(testlib.SCRIPTS, "handoff_core", "fences.py")
        self.assertEqual(digest(mine), digest(theirs))

    def test_the_statement_and_the_character_list(self):
        listed = set(chr(c) for c in range(0x20, 0x7F)) | {"\t"}
        listed |= set(chr(c) for c in (0x00A7, 0x00B2, 0x00B7, 0x00D7, 0x2013, 0x2014, 0x2019, 0x2026, 0x2190,
                                        0x2191, 0x2192, 0x2193, 0x2194, 0x2197, 0x2212, 0x2248, 0x2264, 0x2265,
                                        0x2715, 0x2018, 0x201C, 0x201D))
        listed |= set(chr(c) for c in range(0xC0, 0x100) if c != 0xF7)
        self.assertEqual(set(fences.LISTED), listed)
        for name in ("THE FENCE RULE", "THE RAW HTML RULE", "THE PLAIN-STRUCTURE RULE", "THE CHARACTER LIST",
                     "THE LABEL RULE", "THE STRAY-LABEL RULE", "THE LEADING MARKS", "THE FOLD"):
            self.assertIn(name, fences.__doc__)


def with_handoffs_lines(lines):
    """The fixture doc with `lines` placed just before `## Handoffs`."""
    text = hlib.build_doc()
    at = text.index("## Handoffs")
    return text[:at] + "\n".join(lines) + "\n" + text[at:]


class TheReading(unittest.TestCase):

    def stop(self, text):
        with self.assertRaises(docmod.DocUnreadable) as caught:
            docmod.read(text)
        return caught.exception

    def test_the_fixture_doc_reads(self):
        doc = docmod.read(hlib.build_doc())
        self.assertEqual([s["name"] for s in doc.slices], ["A", "B"])
        self.assertIsNotNone(doc.handoffs)
        self.assertIsNotNone(doc.punch)

    def test_a_handoffs_heading_inside_an_accepted_fence_is_content(self):
        text = hlib.build_doc(with_handoffs=False)
        at = text.index("## Punch list")
        text = text[:at] + "```text\n## Handoffs\n```\n" + text[at:]
        doc = docmod.read(text)
        self.assertIsNone(doc.handoffs)

    def test_a_handoffs_heading_inside_a_fence_off_the_margin_stops(self):
        text = with_handoffs_lines(["- a list item", "  ```", "  ## Handoffs", "  ```"])
        found = self.stop(text)
        self.assertIn("fence", found.words)

    def test_a_raw_html_line_stops(self):
        found = self.stop(with_handoffs_lines(["<!-- ## Handoffs -->"]))
        self.assertIn("raw HTML", found.words)

    def test_an_indented_heading_stops(self):
        found = self.stop(with_handoffs_lines(["  ## Handoffs"]))
        self.assertIn("heading", found.words)

    def test_an_unlisted_character_stops_naming_its_code_point(self):
        found = self.stop(with_handoffs_lines(["a line with a zero width\u200bspace"]))
        self.assertIn("U+200B", found.words)

    def test_an_indented_depends_on_label_stops(self):
        text = hlib.build_doc().replace("Depends on: Slice A", "  Depends on: Slice A")
        found = self.stop(text)
        self.assertIn("Depends on:", found.words)

    def test_a_questions_label_off_the_exact_form_stops(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing", None),
                                      ("B", "the spinner", "not started", "Slice A", None)])
        text = text.replace("Depends on: Slice A", "Depends on: Slice A\nquestions : does it wrap?")
        found = self.stop(text)
        self.assertIn("Questions:", found.words)

    def test_a_second_handoffs_section_stops(self):
        text = hlib.build_doc(extra_sections=[["## Handoffs"]])
        found = self.stop(text)
        self.assertIn("Handoffs", found.words)

    def test_every_problem_names_its_line(self):
        text = with_handoffs_lines(["<p>"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "<p>")


@unittest.skipUnless(hlib.jsonschema_here(), "the driver needs jsonschema (run under uv)")
class TheStops(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-lines-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def stops(self, text):
        ws, _ = hlib.make_repo(self.tmp, text)
        before = hlib.snapshot(ws)
        drive, run_dir = hlib.start(self.tmp, ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "stopped")
        self.assertEqual(out["stop_tag"], "doc-unreadable")
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(hlib.snapshot(ws), before)
        return out

    def test_a_fenced_handoffs_heading_off_the_margin(self):
        out = self.stops(with_handoffs_lines(["- a list item", "  ```", "  ## Handoffs", "  ```"]))
        self.assertIn("line", out["reason"])

    def test_a_raw_html_line(self):
        self.stops(with_handoffs_lines(["<div>"]))

    def test_an_indented_heading(self):
        self.stops(with_handoffs_lines(["   ## Handoffs"]))

    def test_an_unlisted_character(self):
        out = self.stops(with_handoffs_lines(["text\u202eswapped"]))
        self.assertIn("U+202E", out["reason"])


if __name__ == "__main__":
    unittest.main()
