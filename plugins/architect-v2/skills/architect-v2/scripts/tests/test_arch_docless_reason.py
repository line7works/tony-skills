"""The docless reason (round 4 R2, CA3-2 and CA3-3).

CA3-2: a reason of whitespace, format or zero-width characters only records nothing. The input's
`station.docless_reason` of that kind is refused at `check-input` (exit 4, no run made): the input
schema's pattern asks for one character the frame's `answer._visible` keeps that is not whitespace,
and this file holds the pattern to exactly those characters, code point by code point. The
answer's `docless.reason` of that kind is refused `docless-without-reason` (exit 5).

CA3-3: the answer's reason is the input's reason byte for byte once each one's runs of whitespace
are collapsed to one space and its ends trimmed, case kept; a re-cased reason, or one with an
added invisible character, is refused `docless-reason-mismatch`, and the doc's `Docless:` header
carries the reason so collapsed. Every run case drives the real CLI.
"""
import json
import os
import re
import sys
import unittest

import archlib
import testlib
from test_arch_set_aside import OTHER, OTHER_REL, REASON, docless_answer

testlib.add_scripts_to_path()
from station_core import answer as shared  # noqa: E402

# Nothing visible: spaces, format characters (zero-width, bidi marks, joiners, the BOM, tags), a
# combining grapheme joiner, the letter-shaped fillers, and mixes of them.
INVISIBLE_ONLY = [u"\u200b", u"\u200e", u"\u200f", u"\ufeff\u3164", u"\U000e0020", u"\u034f", u"\u2060 \u00ad",
                  u" \u200f\t", u"\u202a\u202c", u"\u180e", u"\uffa0", u"\u115f", u"\u2061", u"\ufe0f",
                  u"\u3000\u200b", u"\u2800"]


def input_pattern():
    with open(os.path.join(testlib.SKILL, "references", "input.schema.json"), encoding="utf-8") as fh:
        schema = json.load(fh)
    return schema["properties"]["station"]["properties"]["docless_reason"]["pattern"]


def seen(ch):
    """True when the frame's invisible rule keeps a character that is not whitespace."""
    return bool(shared._visible(ch).strip())


class TheInputPattern(unittest.TestCase):

    def test_the_pattern_holds_exactly_the_frames_visible_characters(self):
        pattern = re.compile(input_pattern())
        wrong = []
        for code in range(0x110000):
            if 0xd800 <= code <= 0xdfff or code in (0x0a, 0x0d):
                continue
            ch = chr(code)
            if bool(pattern.search(ch)) != seen(ch):
                wrong.append("U+%04X" % code)
        self.assertEqual(wrong[:20], [], "%d code points differ from answer._visible" % len(wrong))

    def test_a_visible_reason_still_matches_and_a_line_break_still_does_not(self):
        pattern = re.compile(input_pattern())
        self.assertTrue(pattern.search(REASON))
        self.assertTrue(pattern.search(u"\u200b" + REASON + u" \u200e"))
        self.assertFalse(pattern.search(REASON + "\n"))
        self.assertFalse(pattern.search("a\nb"))


class CheckInputRefusesAnInvisibleReason(unittest.TestCase):

    def check(self, reason):
        tmp = testlib.make_scratch("arch-reason-input-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = testlib.git_workspace(tmp, "ws")
        run = archlib.ArchRun(tmp, ws, station={"docless": True, "docless_reason": reason})
        code, doc, out, err = run.check_input()
        return code, doc, out + err, run.run_dir

    def test_each_invisible_only_reason_is_exit_4_with_no_run(self):
        for reason in INVISIBLE_ONLY:
            with self.subTest(reason=reason.encode("unicode_escape")):
                code, doc, text, run_dir = self.check(reason)
                self.assertEqual(code, 4, text)
                self.assertFalse(os.path.exists(run_dir))
                self.assertIn("/station/docless_reason", [e["path"] for e in doc["errors"]], text)

    def test_a_reason_with_invisibles_around_its_words_is_accepted(self):
        code, doc, text, run_dir = self.check(u"\u200b" + REASON)
        self.assertEqual(code, 0, text)


class _Aside(unittest.TestCase):

    def start(self, reason=REASON):
        self.tmp = testlib.make_scratch("arch-reason-")
        self.addCleanup(testlib.rmtree, self.tmp)
        staging = os.path.join(self.tmp, "staging")
        os.makedirs(staging)
        self.ws = testlib.git_workspace(self.tmp, "ws", {"README.md": "# Bench\n", OTHER_REL: OTHER})
        self.run = archlib.ArchRun(self.tmp, self.ws, staging, station={"docless": True, "docless_reason": reason})
        code, doc, out, err = self.run.to_harvest()
        self.assertEqual(code, 0, out + err)

    def refused(self, answer, rule):
        before = archlib.listing(self.run.run_dir)
        code, doc, out, err = self.run.record(answer)
        self.assertEqual(code, 5, out + err)
        self.assertIn(rule, [r["rule"] for r in doc["refusals"]], out)
        self.assertEqual(archlib.listing(self.run.run_dir), before)


class TheAnswersReasonIsTheInputs(_Aside):

    def test_a_re_cased_reason_is_refused(self):
        self.start()
        for reason in (REASON.upper(), REASON[0].upper() + REASON[1:], REASON.replace("Metronome", "metronome")):
            with self.subTest(reason=reason):
                self.refused(docless_answer(reason=reason), "docless-reason-mismatch")

    def test_a_reason_with_an_added_invisible_is_refused(self):
        self.start()
        for reason in (REASON.replace("scope doc", u"scope\u200b doc", 1), REASON + u"\u200e", u"\ufeff" + REASON):
            with self.subTest(reason=reason.encode("unicode_escape")):
                self.refused(docless_answer(reason=reason), "docless-reason-mismatch")

    def test_a_trailing_period_is_another_reason(self):
        self.start()
        self.refused(docless_answer(reason=REASON + "."), "docless-reason-mismatch")

    def test_a_re_spaced_reason_is_accepted_and_the_header_holds_the_collapsed_words(self):
        self.start()
        respaced = "  " + REASON.replace(" ", "   ").replace("; ", ";\t") + " "
        code, doc, out, err = self.run.record(docless_answer(reason=respaced))
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(testlib.read_text(doc["doc"]).split("\n")[2], "Docless: %s" % REASON)

    def test_an_input_reason_with_runs_of_spaces_lands_collapsed(self):
        self.start(reason=REASON.replace(" ", "  ") + "  ")
        code, doc, out, err = self.run.record(docless_answer(reason=REASON))
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(testlib.read_text(doc["doc"]).split("\n")[2], "Docless: %s" % REASON)


class TheAnswersReasonIsVisible(unittest.TestCase):
    """A plain docless run (the hunt found nothing, no input reason): the answer's own reason."""

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-reason-none-")
        self.addCleanup(testlib.rmtree, self.tmp)
        ws = testlib.git_workspace(self.tmp, "ws")
        self.run = archlib.ArchRun(self.tmp, ws)
        code, doc, out, err = self.run.to_harvest()
        self.assertEqual(code, 0, out + err)

    def test_an_invisible_only_answer_reason_is_docless_without_reason(self):
        for reason in INVISIBLE_ONLY:
            with self.subTest(reason=reason.encode("unicode_escape")):
                before = archlib.listing(self.run.run_dir)
                code, doc, out, err = self.run.record(docless_answer(reason=reason))
                self.assertEqual(code, 5, out + err)
                self.assertIn("docless-without-reason", [r["rule"] for r in doc["refusals"]], out)
                self.assertEqual(archlib.listing(self.run.run_dir), before)

    def test_a_visible_answer_reason_is_accepted_and_lands_collapsed(self):
        code, doc, out, err = self.run.record(docless_answer(reason="an   experiment  drawn before any precon "))
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(testlib.read_text(doc["doc"]).split("\n")[2],
                         "Docless: an experiment drawn before any precon")


if __name__ == "__main__":
    unittest.main()
