"""One rule for every form of this core's own labels (the E15 lane contract A26, after Astra's look 5b).

Inside a slice's section, every rendered block of any kind (a heading, a paragraph line, a list item, a block quote,
a table cell, a wrapped line) whose rendered text reads as a `Questions:` or `Depends on:` label candidate (A25's
folding) must come from that label in its plain form on one source line, with its value on the same line; anything
else stops `doc-unreadable` naming the line, before any write. A `Depends on:` line whose value is empty stops as an
empty `Questions:` does (A24 (2)).

`TheReading` drives `handoff_core/doc.py` on each form; `TheCli` drives the same documents through the real CLI on a
repository with an imported records log: each stop is `doc-unreadable` at `select`, naming the line, with nothing
written (doc, log, tree, HEAD) and `photograph` refused after it; each control selects as before. The table-cell case
records what the pinned reader does: its `commonmark` preset renders no table, so a pipe row is paragraph text that
reads as no label candidate in either reading (the report's numbered question).
"""
import json
import os
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import commonmark, doc as docmod  # noqa: E402

D = hlib.D

# Astra's two smallest cases, look 5b (her JSON strings, decoded; her U+2014 carried as the escape `D`).
MINIMAL_HEADING = ("# Plan\n\n## Slice A %s work\nStatus: not started\n\nDepends on: nothing\n\n"
                   "### Questions: Which mode?\n\n## Handoffs\n\n## Punch list\n" % D)
MINIMAL_DEPENDENCY = ("# Plan\n\n## Slice A %s work\nStatus: not started\n\nDepends on:\nSlice B\n\n"
                      "## Slice B %s prerequisite\nStatus: not started\n\nDepends on: Slice A\n\n"
                      "## Handoffs\n\n## Punch list\n" % (D, D))


def one_slice(slice_tail=()):
    """A single startable slice (`not started`, `Depends on: nothing`), then the ledger; `slice_tail` lines go after
    the slice's `Status:` line, in the slice's section, behind one blank line."""
    text = hlib.build_doc(slices=[("A", "the counter", "not started", "nothing", None)])
    at = text.index("Status: not started\n") + len("Status: not started\n")
    return text[:at] + "\n" + "\n".join(slice_tail) + "\n" + text[at:]


def two_slices(old, new):
    """The default two-slice doc (A signed off; B not started, `Depends on: Slice A`) with `old` replaced by `new`."""
    text = hlib.build_doc()
    assert old in text, old
    return text.replace(old, new, 1)


B_DEPENDS = "Depends on: Slice A\nStatus: not started"


def three_slices(new):
    """A signed off, B built (not signed off), C not started with `Depends on: Slice A`; that label and C's
    `Status:` line replaced by `new`."""
    text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing", None),
                                  ("B", "the spinner", "built", "Slice A", None),
                                  ("C", "the display", "not started", "Slice A", None)])
    old = "Depends on: Slice A\nStatus: not started"
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def one_slice_form(new):
    """One startable slice A whose `Depends on: nothing` and `Status:` lines are replaced by `new`."""
    text = hlib.build_doc(slices=[("A", "the counter", "not started", "nothing", None)])
    old = "Depends on: nothing\nStatus: not started"
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)

STOPS = {
    "astras-minimal-heading": (MINIMAL_HEADING, "### Questions: Which mode?"),
    "astras-minimal-dependency": (MINIMAL_DEPENDENCY, "Depends on:"),
    "level-3-questions-heading": (one_slice(["### Questions: Which mode?"]), "### Questions: Which mode?"),
    "level-4-questions-heading": (one_slice(["#### Questions: Which mode?"]), "#### Questions: Which mode?"),
    "level-3-depends-on-heading": (one_slice(["### Depends on: nothing"]), "### Depends on: nothing"),
    "list-item": (one_slice(["- Questions: Which mode?"]), "- Questions: Which mode?"),
    "ordered-list-item": (one_slice(["1. Questions: Which mode?"]), "1. Questions: Which mode?"),
    "block-quote": (one_slice(["> Questions: Which mode?"]), "> Questions: Which mode?"),
    "wrapped-questions-line": (one_slice(["Questions: Which <span", "title=\"t\">mode?</span>"]),
                               "Questions: Which <span"),
    "wrapped-depends-on-line": (two_slices(B_DEPENDS, "Depends on: Slice <span\ntitle=\"t\">A</span>\n"
                                                      "Status: not started"), "Depends on: Slice <span"),
    "depends-on-empty-then-the-value": (two_slices(B_DEPENDS, "Depends on:\nSlice A\n\nStatus: not started"),
                                        "Depends on:"),
    "depends-on-empty-alone": (two_slices(B_DEPENDS, "Depends on:\n\nStatus: not started"), "Depends on:"),
    "depends-on-empty-before-the-status-line": (two_slices(B_DEPENDS, "Depends on:\nStatus: not started"),
                                                "Depends on:"),
    "depends-on-spaces-only": (two_slices(B_DEPENDS, "Depends on:   \nStatus: not started"), "Depends on:   "),
    "depends-on-value-continues": (three_slices("Depends on: Slice A,\nSlice B\nStatus: not started"),
                                   "Depends on: Slice A,"),
    "depends-on-nothing-then-a-sentence": (
        one_slice_form("Depends on: nothing\nThe encoder has to land first.\nStatus: not started"),
        "Depends on: nothing"),
    "questions-value-continues": (one_slice_form("Depends on: nothing\nQuestions: Which mode,\nand why?\n"
                                                 "Status: not started"), "Questions: Which mode,"),
}

TABLE = one_slice(["| Questions: | Which mode? |", "| --- | --- |"])

# Each control: (text, {slice name: (depends, [question texts])}) as the reading takes it.
CONTROLS = {
    "plain-one-line-labels": (hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing", None),
                                                     ("B", "the spinner", "not started", "Slice A",
                                                      ["Which mode?", "How fast?"])]),
                              {"A": ("nothing", []), "B": ("Slice A", ["Which mode?", "How fast?"])}),
    "questions-none": (one_slice(["Questions: none"]), {"A": ("nothing", ["none"])}),
    "depends-on-nothing": (hlib.build_doc(slices=[("A", "the counter", "not started", "nothing", None)]),
                           {"A": ("nothing", [])}),
    "a-heading-that-is-no-label": (one_slice(["### Open questions", "", "Questions: Which mode?"]),
                                   {"A": ("nothing", ["Which mode?"])}),
    "depends-on-then-status": (three_slices("Depends on: Slice A\nStatus: not started"),
                               {"A": ("nothing", []), "B": ("Slice A", []), "C": ("Slice A", [])}),
    "questions-then-status": (one_slice_form("Depends on: nothing\nQuestions: Which mode?\nStatus: not started"),
                              {"A": ("nothing", ["Which mode?"])}),
}


def number_of(text, line):
    return text.split("\n").index(line) + 1


def readings(parsed):
    return dict((s["name"], (s["depends"], [q["text"] for q in s["questions"]])) for s in parsed.slices)


CONTINUATION = ("whose paragraph continues on the next source line with a line that is not `Status:`, `Base:`, "
                "`Depends on:` or `Questions:`")


class TheStatement(unittest.TestCase):

    def test_the_rule_is_stated_once_in_the_code_and_once_in_the_contract(self):
        from handoff_core import two_readings  # noqa: E402
        name = "THE ONE LABEL RULE"
        self.assertEqual(two_readings.__doc__.count(name), 1)
        contract = testlib.read_text(os.path.join(testlib.REF, "handoff-contract.md"))
        self.assertEqual(contract.count(name), 1)
        for text in (two_readings.__doc__, contract):
            self.assertIn("A26", text)
            self.assertIn(CONTINUATION, " ".join(text.split()))


class TheReading(unittest.TestCase):

    def stop(self, text, line):
        with self.assertRaises(docmod.DocUnreadable) as caught:
            docmod.read(text)
        self.assertEqual(caught.exception.line, number_of(text, line), caught.exception.words)
        return caught.exception

    def test_each_form_stops_at_its_line(self):
        for name, (text, line) in sorted(STOPS.items()):
            with self.subTest(name):
                self.stop(text, line)

    def test_a_label_heading_is_named_as_a_heading(self):
        for name in ("astras-minimal-heading", "level-3-questions-heading", "level-4-questions-heading",
                     "level-3-depends-on-heading"):
            with self.subTest(name):
                found = self.stop(*STOPS[name])
                self.assertIn("heading", found.words)
                self.assertIn("A26", found.words)

    def test_a_wrapped_label_line_is_named_as_wrapped(self):
        """The line rules' continuation half (send-back 1) names a wrapped label line first; the second reading's
        own refusal of it stands behind it, at the same line."""
        from handoff_core import fences, readings, two_readings  # noqa: E402
        for name in ("wrapped-questions-line", "wrapped-depends-on-line"):
            with self.subTest(name):
                text, line = STOPS[name]
                found = self.stop(text, line)
                self.assertIn("continues on the next source line", found.words)
                total = len(fences.split_lines(text))
                mine = two_readings.second(text, total, readings.second_reading(text, total)["slices"])
                wrapped = [n for n, words in mine["refused"] if "more than one source line" in words]
                self.assertEqual(wrapped, [number_of(text, line)])

    def test_a_label_whose_paragraph_continues_is_named_as_continued(self):
        for name in ("depends-on-value-continues", "depends-on-nothing-then-a-sentence", "questions-value-continues"):
            with self.subTest(name):
                found = self.stop(*STOPS[name])
                self.assertIn("continues on the next source line", found.words)
                self.assertIn("A26", found.words)

    def test_questions_none_then_status_still_stops_by_a24(self):
        text = one_slice_form("Depends on: nothing\nQuestions: none\nStatus: not started")
        found = self.stop(text, "Questions: none")
        self.assertIn("A24 (2)", found.words)

    def test_an_empty_depends_on_value_stops_as_an_empty_questions_does(self):
        for name in ("astras-minimal-dependency", "depends-on-empty-then-the-value", "depends-on-empty-alone",
                     "depends-on-empty-before-the-status-line", "depends-on-spaces-only"):
            with self.subTest(name):
                found = self.stop(*STOPS[name])
                self.assertIn("`Depends on:` line with no dependency on it", found.words)
                self.assertIn("A26", found.words)

    def test_the_pinned_reader_renders_no_table_cell(self):
        kinds = set(token.type for token in commonmark.tokens(TABLE))
        self.assertFalse(kinds & {"table_open", "th_open", "td_open"}, kinds)
        self.assertEqual(readings(docmod.read(TABLE)), {"A": ("nothing", [])})

    def test_controls_read_as_before(self):
        for name, (text, expected) in sorted(CONTROLS.items()):
            with self.subTest(name):
                self.assertEqual(readings(docmod.read(text)), expected)


@unittest.skipUnless(hlib.records_usable(), "the CLI needs jsonschema and the records component (run under uv in the "
                                            "checkout)")
class TheCli(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-label-forms-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def select(self, text):
        ws, _ = hlib.make_repo(self.tmp, text, records=True)
        before = hlib.snapshot(ws)
        self.assertIsNotNone(before["log"])
        drive, run_dir = hlib.start(self.tmp, ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        return ws, before, drive, run_dir, code, out, err

    def stops(self, text, line):
        ws, before, drive, run_dir, code, out, err = self.select(text)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "stopped")
        self.assertEqual(out["stop_tag"], "doc-unreadable")
        self.assertTrue(out["wrote_nothing"])
        self.assertIn("line %d" % number_of(text, line), out["reason"])
        self.assertEqual(hlib.snapshot(ws, run_dir), dict(before, pointer=None))
        code, out, err = drive(["photograph", "--run-dir", run_dir])
        self.assertNotEqual(code, 0, (out, err))
        self.assertEqual(hlib.snapshot(ws, run_dir), dict(before, pointer=None))

    def reads(self, text, expected):
        ws, before, drive, run_dir, code, out, err = self.select(text)
        self.assertEqual(code, 0, (out, err))
        with open(os.path.join(run_dir, "doc.json"), encoding="utf-8") as fh:
            view = json.load(fh)
        got = dict((s["name"], (s["depends"], [q["text"] for q in s["questions"]])) for s in view["slices"])
        self.assertEqual(got, expected)
        self.assertEqual(hlib.snapshot(ws), before)
        return run_dir

    def test_astras_minimal_heading(self):
        self.stops(*STOPS["astras-minimal-heading"])

    def test_astras_minimal_dependency(self):
        self.stops(*STOPS["astras-minimal-dependency"])

    def test_a_level_3_questions_heading(self):
        self.stops(*STOPS["level-3-questions-heading"])

    def test_a_level_4_questions_heading(self):
        self.stops(*STOPS["level-4-questions-heading"])

    def test_a_level_3_depends_on_heading(self):
        self.stops(*STOPS["level-3-depends-on-heading"])

    def test_a_list_item(self):
        self.stops(*STOPS["list-item"])

    def test_an_ordered_list_item(self):
        self.stops(*STOPS["ordered-list-item"])

    def test_a_block_quote(self):
        self.stops(*STOPS["block-quote"])

    def test_a_wrapped_questions_line(self):
        self.stops(*STOPS["wrapped-questions-line"])

    def test_a_wrapped_depends_on_line(self):
        self.stops(*STOPS["wrapped-depends-on-line"])

    def test_depends_on_empty_then_the_value_on_the_next_line(self):
        self.stops(*STOPS["depends-on-empty-then-the-value"])

    def test_depends_on_empty_alone(self):
        self.stops(*STOPS["depends-on-empty-alone"])

    def test_depends_on_empty_before_the_status_line(self):
        self.stops(*STOPS["depends-on-empty-before-the-status-line"])

    def test_depends_on_slice_a_comma_then_slice_b(self):
        self.stops(*STOPS["depends-on-value-continues"])

    def test_depends_on_nothing_then_a_sentence(self):
        self.stops(*STOPS["depends-on-nothing-then-a-sentence"])

    def test_questions_which_mode_comma_then_and_why(self):
        self.stops(*STOPS["questions-value-continues"])

    def test_depends_on_followed_directly_by_status_reads_as_before(self):
        self.reads(*CONTROLS["depends-on-then-status"])

    def test_questions_followed_directly_by_status_is_asked_no_stop(self):
        run_dir = self.reads(*CONTROLS["questions-then-status"])
        drive = hlib.Driver(self.tmp)
        code, out, err = drive(["photograph", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["gate", "--run-dir", run_dir, "--questions", hlib.questions_file(self.tmp, run_dir)])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual([q["text"] for q in out["questions"]], ["Which mode?"])

    def test_a_table_row_reads_as_no_label_where_commonmark_renders_no_cell(self):
        self.reads(TABLE, {"A": ("nothing", [])})

    def test_the_plain_one_line_labels_read_as_before(self):
        self.reads(*CONTROLS["plain-one-line-labels"])

    def test_questions_none_reads_as_before(self):
        self.reads(*CONTROLS["questions-none"])

    def test_depends_on_nothing_reads_as_before(self):
        self.reads(*CONTROLS["depends-on-nothing"])

    def test_a_heading_that_is_no_label_reads_as_before(self):
        self.reads(*CONTROLS["a-heading-that-is-no-label"])


if __name__ == "__main__":
    unittest.main()
