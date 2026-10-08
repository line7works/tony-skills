"""The second reading (the E15 lane contract A25 (1), after Astra's look 5): handoff-v2 reads every build doc it
decides from twice, by A22's copied line rules (`handoff_core/fences.py`, `tests/test_line_rules.py`) and by
vertical-v2's second reading (A13: the pinned CommonMark reader whose decisions are compared with the line rules'),
and the first line where their decisions differ stops `doc-unreadable`, naming the line, before any write and before
the gate.

`TheCopy` holds the second reading's code to vertical-v2's files byte for byte (`commonmark.py`, `readings.py` and
the two modules it reads with, `spec.py` and `notes.py`) and the vendored reader to vertical-v2's `scripts/vendor/`
(every file and `VENDOR.json`): skipped, never passed, in the installed shape where vertical-v2 is absent, as A22's
test is; the statement is checked in both shapes. `TheReading` drives `handoff_core/doc.py` on Astra's two smallest
cases and on every shape A25 names: a Setext heading inside `## Handoffs`, a Setext `Handoffs` heading, a
`## Handoffs ##` closing-hash heading, a bold `**Depends on:**` and `**Questions:**`, a code-span label, a marked-up
handoff block heading, a character-coded section name; and on clean docs, which read as before. `TheStops` drives
Astra's two cases and the two heading shapes through the real CLI on a repository with an imported records log: each
stops `doc-unreadable` at `select`, nothing written (doc, log, tree, HEAD).
"""
import hashlib
import os
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import doc as docmod  # noqa: E402

D = hlib.D
COPIED = ("commonmark.py", "readings.py", "spec.py", "notes.py")


def vertical_scripts():
    path = testlib.checkout_sibling("vertical-v2")
    return None if path is None else os.path.join(path, "skills", "vertical-v2", "scripts")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def tree(root):
    out = []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            out.append(os.path.relpath(os.path.join(base, name), root).replace(os.sep, "/"))
    return sorted(out)


class TheCopy(unittest.TestCase):

    def theirs(self):
        scripts = vertical_scripts()
        if scripts is None or not os.path.isdir(scripts):
            self.skipTest("vertical-v2 is not beside this core (the installed shape): the copy cannot be compared "
                          "here, and this is reported as skipped, not passed")
        return scripts

    def test_the_second_reading_is_vertical_v2s_code_byte_for_byte(self):
        scripts = self.theirs()
        for name in COPIED:
            mine = os.path.join(testlib.SCRIPTS, "handoff_core", name)
            self.assertTrue(os.path.isfile(mine), name)
            self.assertEqual(digest(mine), digest(os.path.join(scripts, "vertical_core", name)), name)

    def test_the_vendored_reader_is_vertical_v2s_tree_byte_for_byte(self):
        scripts = self.theirs()
        mine, theirs = os.path.join(testlib.SCRIPTS, "vendor"), os.path.join(scripts, "vendor")
        self.assertTrue(os.path.isfile(os.path.join(mine, "VENDOR.json")))
        self.assertEqual(tree(mine), tree(theirs))
        for rel in tree(theirs):
            self.assertEqual(digest(os.path.join(mine, *rel.split("/"))), digest(os.path.join(theirs, *rel.split("/"))),
                             rel)

    def test_the_statement(self):
        from handoff_core import readings, two_readings  # noqa: E402
        for name in ("THE TWO-READINGS RULE", "THE SECOND READING'S FOUR REFUSALS"):
            self.assertIn(name, readings.__doc__)
        self.assertIn("THE HANDOFF TWO-READINGS RULE", two_readings.__doc__)


def one_slice(handoffs=None, with_handoffs=True, extra_sections=None, slice_tail=()):
    """Astra's shape: a single startable slice (`not started`), then the ledger; `slice_tail` lines go after the
    slice's `Status:` line, in the slice's section."""
    text = hlib.build_doc(slices=[("A", "the counter", "not started", "nothing", None)], handoffs=handoffs,
                          with_handoffs=with_handoffs, extra_sections=extra_sections)
    if slice_tail:
        at = text.index("Status: not started\n") + len("Status: not started\n")
        text = text[:at] + "\n" + "\n".join(slice_tail) + "\n" + text[at:]
    return text


def number_of(text, line):
    return text.split("\n").index(line) + 1


SETEXT_UNDER_HANDOFFS = one_slice(handoffs=["", "Other", "-----", ""])
BOLD_QUESTION = one_slice(slice_tail=["**Questions:** Which mode?"])
SETEXT_HANDOFFS = one_slice(with_handoffs=False, extra_sections=[["", "Handoffs", "--------", ""]])
CLOSING_HASHES = one_slice(with_handoffs=False, extra_sections=[["## Handoffs ##"]])


class TheReading(unittest.TestCase):

    def stop(self, text, line):
        with self.assertRaises(docmod.DocUnreadable) as caught:
            docmod.read(text)
        self.assertEqual(text.split("\n")[caught.exception.line - 1], line, caught.exception.words)
        return caught.exception

    def test_astras_boundary_case_stops_at_the_setext_heading(self):
        found = self.stop(SETEXT_UNDER_HANDOFFS, "Other")
        self.assertIn("CommonMark", found.words)

    def test_astras_question_case_stops_at_the_bold_label(self):
        found = self.stop(BOLD_QUESTION, "**Questions:** Which mode?")
        self.assertIn("Questions:", found.words)

    def test_a_setext_handoffs_heading_stops(self):
        self.stop(SETEXT_HANDOFFS, "Handoffs")

    def test_a_closing_hash_handoffs_heading_stops_never_a_duplicate_section(self):
        found = self.stop(CLOSING_HASHES, "## Handoffs ##")
        self.assertIn("Handoffs", found.words)

    def test_a_bold_depends_on_label_stops(self):
        text = hlib.build_doc().replace("Depends on: Slice A", "**Depends on:** Slice A")
        found = self.stop(text, "**Depends on:** Slice A")
        self.assertIn("Depends on:", found.words)

    def test_a_code_span_questions_label_stops(self):
        self.stop(one_slice(slice_tail=["`Questions:` which mode?"]), "`Questions:` which mode?")

    def test_a_code_span_depends_on_label_stops(self):
        text = hlib.build_doc().replace("Depends on: Slice A", "`Depends on:` Slice A")
        self.stop(text, "`Depends on:` Slice A")

    def test_a_marked_up_handoff_block_heading_stops(self):
        heading = "### **2026-09-25 %s handoff**" % D
        self.stop(one_slice(handoffs=["", heading, "- Next: /ship-v2 A"]), heading)

    def test_a_closing_hash_handoff_block_heading_stops(self):
        heading = "### 2026-09-25 %s handoff ###" % D
        self.stop(one_slice(handoffs=["", heading, "- Next: /ship-v2 A"]), heading)

    def test_a_character_coded_handoffs_heading_stops(self):
        self.stop(one_slice(with_handoffs=False, extra_sections=[["## Hand&#111;ffs"]]), "## Hand&#111;ffs")

    def test_a_label_in_a_paragraph_whose_lines_cannot_be_mapped_stops(self):
        text = one_slice(slice_tail=["see `the", "mode` here", "Questions: Which mode?"])
        found = self.stop(text, "see `the")
        self.assertIn("Questions:", found.words)

    def test_a_setext_heading_inside_a_slice_stops(self):
        self.stop(one_slice(slice_tail=["Notes", "-----"]), "Notes")

    def test_clean_docs_read_as_before(self):
        texts = [hlib.build_doc(), one_slice(),
                 hlib.build_doc(handoffs=hlib.handoff_block(), punch=hlib.review_block()),
                 hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing", None),
                                        ("B", "the spinner", "not started", "Slice A", ["Which mode?", "How fast?"])]),
                 one_slice(slice_tail=["**Goal:** a bold word that is no label of this core", "",
                                       "Questions: none"])]
        for text in texts:
            doc = docmod.read(text)
            self.assertTrue(doc.slices)

    def test_plain_labels_are_read_as_before(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing", None),
                                      ("B", "the spinner", "not started", "Slice A", ["Which mode?"])])
        doc = docmod.read(text)
        self.assertEqual(doc.slices[1]["depends"], "Slice A")
        self.assertEqual([q["text"] for q in doc.slices[1]["questions"]], ["Which mode?"])


@unittest.skipUnless(hlib.records_usable(), "the CLI needs jsonschema and the records component (run under uv in the "
                                            "checkout)")
class TheStops(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-two-readings-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def stops(self, text, line):
        ws, _ = hlib.make_repo(self.tmp, text, records=True)
        before = hlib.snapshot(ws)
        self.assertIsNotNone(before["log"])
        drive, run_dir = hlib.start(self.tmp, ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "stopped")
        self.assertEqual(out["stop_tag"], "doc-unreadable")
        self.assertTrue(out["wrote_nothing"])
        self.assertIn("line %d" % number_of(text, line), out["reason"])
        self.assertEqual(hlib.snapshot(ws, run_dir), dict(before, pointer=None))
        code, out, err = drive(["photograph", "--run-dir", run_dir])
        self.assertNotEqual(code, 0, (out, err))
        self.assertEqual(hlib.snapshot(ws, run_dir), dict(before, pointer=None))

    def test_astras_boundary_case(self):
        self.stops(SETEXT_UNDER_HANDOFFS, "Other")

    def test_astras_question_case(self):
        self.stops(BOLD_QUESTION, "**Questions:** Which mode?")

    def test_a_setext_handoffs_heading(self):
        self.stops(SETEXT_HANDOFFS, "Handoffs")

    def test_a_closing_hash_handoffs_heading(self):
        self.stops(CLOSING_HASHES, "## Handoffs ##")


if __name__ == "__main__":
    unittest.main()
