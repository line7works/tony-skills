"""The doc shapes the slice 1b check found (C1B1-3, C1B1-4, C1B1-7, C1B1-9), each by the check's replacement.

- C1B1-3: a section ends at the next plain level 1 or level 2 heading outside an accepted fence (the way
  vertical-v2's spec ends a withheld section); only `## ` lines open a named section. So a `# Appendix` after the
  last block, or after `## Punch list`, is never where the new block or a grant line lands.
- C1B1-4: a `Questions:` label whose value is empty, `none` or `nothing` is accepted only when no list item follows
  it in its paragraph; one followed by a list stops `doc-unreadable`, naming the line.
- R1B1-2 (the E15 lane contract A24 (2)): a `Questions:` line whose value is empty stops `doc-unreadable` always,
  naming the line; a value `none` or `nothing` followed by any non-blank line in its paragraph stops too.
  `Questions: which encoder?` still asks, and `Questions: none` alone still asks nothing.
- C1B1-7: a doc with no final newline whose last section holds a handoff block takes the new block.
- C1B1-9: in a slice's section, a paragraph holding `<!--` or a link reference definition stops `doc-unreadable`
  when it also holds one of this core's two labels.
"""
import os
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import doc as docmod  # noqa: E402

D = hlib.D
TODAY_HEADING = hlib.HEADING % hlib.TODAY
APPENDIX = ["", "# Appendix: bench wiring", "", "The bench has two sensors."]


def with_slice_c(c_lines):
    text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing"),
                                  ("B", "the spinner", "signed off", "Slice A")])
    return text.replace("\n## Build assumptions", "\n" + "\n".join(c_lines) + "\n\n## Build assumptions", 1)


C = ["", "## Slice C %s the encoder" % D, "Goal: the encoder.", "Footprint: src/enc.py"]


class TheReading(unittest.TestCase):

    def stop(self, text):
        with self.assertRaises(docmod.DocUnreadable) as caught:
            docmod.read(text)
        return caught.exception

    def test_a_level_one_heading_ends_the_handoffs_section(self):
        doc = docmod.read(hlib.build_doc(handoffs=hlib.handoff_block("2026-09-25") + APPENDIX))
        handoffs = doc.sections[doc.handoffs]
        appendix = doc.raw.index("# Appendix: bench wiring\n") + 1
        self.assertEqual(handoffs["end"], appendix)

    def test_a_block_under_a_level_one_heading_after_handoffs_is_misplaced(self):
        text = hlib.build_doc(with_punch=False, handoffs=hlib.handoff_block("2026-09-25") + APPENDIX
                              + hlib.handoff_block("2026-09-28"))
        doc = docmod.read(text)
        self.assertEqual([b["date"] for b in doc.misplaced], ["2026-09-28"])

    def test_questions_then_a_list_stops_naming_the_label(self):
        text = with_slice_c(C + ["Depends on: Slice B", "Questions:", "- which encoder?", "- what speed?",
                                 "Status: not started"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "Questions:")
        self.assertIn("own `Questions:` line", found.words)

    def test_questions_none_then_a_list_stops_too(self):
        text = with_slice_c(C + ["Depends on: Slice B", "Questions: none", "- which encoder?", "Status: not started"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "Questions: none")

    def test_questions_none_alone_reads_as_none(self):
        doc = docmod.read(with_slice_c(C + ["Depends on: Slice B", "Questions: none", "", "Status: not started"]))
        self.assertEqual([q["text"] for q in doc.slices[2]["questions"]], ["none"])

    def test_r1b1_2_questions_then_a_plain_line_stops_naming_the_label(self):
        text = with_slice_c(C + ["Depends on: Slice B", "Questions:", "Which encoder? What speed?", "",
                                 "Status: not started"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "Questions:")
        self.assertIn("write each open question on its own `Questions:` line, or `Questions: none`", found.words)

    def test_r1b1_2_questions_then_a_blank_a_sentence_and_a_list_stops(self):
        text = with_slice_c(C + ["Depends on: Slice B", "Questions:", "", "The open ones:", "- which encoder?", "",
                                 "Status: not started"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "Questions:")

    def test_r1b1_2_an_empty_questions_label_stops_always(self):
        for after in (["", "Status: not started"], ["Status: not started"]):
            text = with_slice_c(C + ["Depends on: Slice B", "Questions:"] + after)
            found = self.stop(text)
            self.assertEqual(text.splitlines()[found.line - 1], "Questions:")

    def test_r1b1_2_an_empty_value_of_spaces_stops_too(self):
        text = with_slice_c(C + ["Depends on: Slice B", "Questions:   ", "", "Status: not started"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "Questions:   ")

    def test_r1b1_2_questions_none_then_any_non_blank_line_in_its_paragraph_stops(self):
        for value in ("none", "nothing", "None"):
            text = with_slice_c(C + ["Depends on: Slice B", "Questions: %s" % value, "which encoder?", "",
                                     "Status: not started"])
            found = self.stop(text)
            self.assertEqual(text.splitlines()[found.line - 1], "Questions: %s" % value)

    def test_r1b1_2_questions_none_then_the_status_line_in_its_paragraph_stops(self):
        """A24 (2) read literally: ANY non-blank line after a `none` value in its paragraph stops, the slice's own
        `Status:` label included (CommonMark renders the two as one line, `Questions: none Status: not started`)."""
        text = with_slice_c(C + ["Depends on: Slice B", "Questions: none", "Status: not started"])
        found = self.stop(text)
        self.assertEqual(text.splitlines()[found.line - 1], "Questions: none")

    def test_r1b1_2_lines_before_the_label_in_its_paragraph_do_not_stop_it(self):
        doc = docmod.read(with_slice_c(C + ["Depends on: Slice B", "Questions: none", "", "Status: not started"]))
        self.assertEqual(doc.slices[2]["depends"], "Slice B")

    def test_r1b1_2_a_question_on_the_label_line_is_still_read(self):
        doc = docmod.read(with_slice_c(C + ["Depends on: Slice B", "Questions: which encoder?", "Status: not started"]))
        self.assertEqual([q["text"] for q in doc.slices[2]["questions"]], ["which encoder?"])

    def test_a_depends_on_in_a_paragraph_holding_an_inline_comment_stops(self):
        text = with_slice_c(C[:-1] + ["Footprint: src/enc.py <!-- draft", "Depends on: nothing", "-->",
                                      "Status: not started"])
        found = self.stop(text)
        self.assertIn("<!--", found.words)

    def test_a_questions_line_in_a_paragraph_holding_a_link_reference_definition_stops(self):
        text = with_slice_c(C + ['[enc]: https://example.invalid "a title', "Questions: a hidden question", '"',
                                 "Depends on: Slice B", "Status: not started"])
        found = self.stop(text)
        self.assertIn("link reference definition", found.words)

    def test_a_comment_closed_before_the_label_is_no_stop(self):
        doc = docmod.read(with_slice_c(C[:-1] + ["Footprint: src/enc.py <!-- the old path -->", "Depends on: Slice B",
                                                 "Status: not started"]))
        self.assertEqual(doc.slices[2]["depends"], "Slice B")

    def test_a_second_comment_still_open_at_the_label_stops(self):
        found = self.stop(with_slice_c(C[:-1] + ["Footprint: src/enc.py <!-- one", "and two --> and <!-- three",
                                                 "Depends on: nothing", "-->", "Status: not started"]))
        self.assertIn("still open", found.words)

    def test_an_inline_comment_in_another_paragraph_is_no_stop(self):
        doc = docmod.read(with_slice_c(C[:-1] + ["Footprint: src/enc.py <!-- draft -->", "", "Depends on: Slice B",
                                                 "Status: not started"]))
        self.assertEqual(doc.slices[2]["depends"], "Slice B")


@unittest.skipUnless(hlib.jsonschema_here(), "the driver needs jsonschema (run under uv)")
class TheQuestionsLabelThroughTheCli(unittest.TestCase):
    """R1B1-2 through the real CLI: the re-check's two `r07` shapes stop at `select` with nothing written; the control
    `Questions: which encoder?` still asks `r-q1`; `Questions: none` alone asks nothing."""

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-questions-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def c_doc(self, lines):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing"),
                                      ("B", "the spinner", "signed off", "Slice A")])
        return text.replace("\n## Build assumptions", "\n" + "\n".join(C + lines) + "\n\n## Build assumptions", 1)

    def selected(self, lines):
        ws, _ = hlib.make_repo(self.tmp, self.c_doc(lines))
        before = hlib.snapshot(ws)
        drive, run_dir = hlib.start(self.tmp, ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        return ws, before, drive, run_dir, (code, out, err)

    def assert_stops(self, lines):
        ws, before, drive, run_dir, (code, out, err) = self.selected(lines)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "doc-unreadable", out["reason"])
        self.assertIn("Questions:", out["reason"])
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(hlib.snapshot(ws), before)

    def gate_questions(self, lines):
        ws, before, drive, run_dir, (code, out, err) = self.selected(lines)
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["photograph", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["gate", "--run-dir", run_dir, "--questions",
                                hlib.questions_file(self.tmp, run_dir)])
        self.assertEqual(code, 0, (out, err))
        return [(q["id"], q["text"]) for q in out["questions"]]

    def test_r07_questions_then_a_plain_paragraph_line_stops(self):
        self.assert_stops(["Depends on: Slice B", "Questions:", "Which encoder? What speed?", "", "Status: not started"])

    def test_r07_questions_a_blank_a_sentence_then_a_list_stops(self):
        self.assert_stops(["Depends on: Slice B", "Questions:", "", "The open ones:", "- which encoder?", "",
                           "Status: not started"])

    def test_control_questions_which_encoder_still_asks(self):
        self.assertEqual(self.gate_questions(["Depends on: Slice B", "Questions: which encoder?", "Status: not started"]),
                         [("r-q1", "which encoder?")])

    def test_questions_none_alone_still_asks_nothing(self):
        self.assertEqual(self.gate_questions(["Depends on: Slice B", "Questions: none", "", "Status: not started"]), [])


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheWrites(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-shapes-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def written(self, text, records=False, answers=(), questions=()):
        ws, info = hlib.make_repo(self.tmp, text, records=records)
        drive, run_dir = hlib.start(self.tmp, ws)
        gate = hlib.through_gate(self, drive, self.tmp, run_dir, questions=questions)
        answers = [dict(a, effect=dict(a["effect"], finding=gate["open"][0]["id"])) if a["effect"]["kind"] == "waive"
                   else a for a in answers]
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer",
                                hlib.answers_file(self.tmp, run_dir, answers)])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        return hlib.read_doc(ws)

    def test_c1b1_3_the_new_block_lands_before_a_level_one_heading_after_the_last_block(self):
        after = self.written(hlib.build_doc(handoffs=hlib.handoff_block("2026-09-25") + APPENDIX))
        self.assertLess(after.index(TODAY_HEADING), after.index("# Appendix: bench wiring"))
        self.assertGreater(after.index(TODAY_HEADING), after.index(hlib.HEADING % "2026-09-25"))

    def test_c1b1_3_the_grant_line_lands_before_a_level_one_heading_after_the_punch_list(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A")],
                              punch=hlib.review_block() + APPENDIX)
        after = self.written(text, records=True, questions=[{"source": "chat-ruling", "text": "waive it?"}],
                             answers=[{"question": "q1", "answered": True, "words": "ship it",
                                       "effect": {"kind": "waive", "finding": None}}])
        grant = next(l for l in after.splitlines() if "WAIVED (per user)" in l)
        self.assertLess(after.index(grant), after.index("# Appendix: bench wiring"))
        self.assertGreater(after.index(grant), after.index("## Punch list"))

    def test_c1b1_7_a_doc_with_no_final_newline_takes_the_block(self):
        text = hlib.build_doc(with_punch=False, handoffs=hlib.handoff_block("2026-09-25")).rstrip("\n")
        after = self.written(text)
        self.assertIn(TODAY_HEADING, after)
        self.assertLess(after.index(hlib.HEADING % "2026-09-25"), after.index(TODAY_HEADING))


if __name__ == "__main__":
    unittest.main()
