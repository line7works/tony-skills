"""The load-bearing forms (ruling E15-11): rendered and parsed by one module, `handoff_core/forms.py`, with a
round trip for each; the kickoff lines name the v2 stations (A2, Q5); the em dash of the block heading is one
constant in code and is typed nowhere in this core's own files (standing rule 10's one named exception).
"""
import os
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import forms  # noqa: E402

D = hlib.D
DOC = hlib.DOC


def block_fields(**extra):
    fields = {"date": "2026-10-04", "next": {"shape": "clean-boundary", "slice": "B", "doc": DOC},
              "cards": [{"name": "A", "card": "signed off", "after": None}, {"name": "B", "card": "not started",
                                                                              "after": None}],
              "open": [], "repo": {"branch": "feat", "ahead": 2, "base": "main", "tree": "clean", "checkpoint": None},
              "suite": None, "questions": [], "perishables": ["the bench clock drifts"]}
    fields.update(extra)
    return fields


class TheHeading(unittest.TestCase):

    def test_the_heading_is_v1s_bytes_with_the_dash_as_one_constant(self):
        self.assertEqual(forms.D, "\u2014")
        self.assertEqual(forms.heading("2026-10-04"), "### 2026-10-04 \u2014 handoff")
        self.assertEqual(forms.parse_heading("### 2026-10-04 \u2014 handoff"), "2026-10-04")
        self.assertIsNone(forms.parse_heading("### 2026-10-04 - handoff"))
        self.assertIsNone(forms.parse_heading("### 2026-10-04 \u2014 review: Slice A"))


class TheKickoff(unittest.TestCase):

    def test_a_clean_boundary_names_ship_v2_and_states_build_v2_once(self):
        move = forms.next_move_text({"shape": "clean-boundary", "slice": "B", "doc": DOC})
        self.assertEqual(move["kickoff"], "/ship-v2 B %s" % DOC)
        self.assertEqual(move["alternative"], "/build-v2 B %s" % DOC)
        self.assertNotIn("/ship ", move["line"] + " ")
        self.assertEqual(move["line"].count("/build-v2"), 1)

    def test_an_open_card_is_the_fix_list_then_recheck_v2(self):
        move = forms.next_move_text({"shape": "open-card", "doc": DOC, "recheck": ["A"],
                                     "fix_list": [{"severity": "MAJOR", "location": "src/turnstile.py:2",
                                                   "claim": "the counter skips a turn"}]})
        self.assertIsNone(move["kickoff"])
        self.assertIn("/recheck-v2 A %s" % DOC, move["line"])
        self.assertNotIn("/ship-v2", move["line"])

    def test_a_complete_loop_has_no_kickoff_line(self):
        move = forms.next_move_text({"shape": "loop-complete", "doc": DOC})
        self.assertIsNone(move["kickoff"])
        self.assertNotIn("/ship", move["line"])
        self.assertNotIn("/build", move["line"])


class TheRoundTrips(unittest.TestCase):

    def test_the_block(self):
        fields = block_fields(questions=[{"question": "does the spinner wrap", "answer": "yes, at 99",
                                          "landed": "block"}],
                              open=[{"severity": "MINOR", "location": "src/turnstile.py:5", "claim": "a vague name"}],
                              suite={"state": "3 passed", "provenance": "build-v2 run r-7"})
        text = forms.render_block(fields)
        self.assertTrue(text.startswith("### 2026-10-04 \u2014 handoff\n"))
        self.assertEqual(forms.render_block(forms.parse_block(text)), text)

    def test_the_handoff_report(self):
        fields = {"feature": "turnstile", "after": "A", "doc": DOC, "next": "/ship-v2 B %s" % DOC,
                  "repo": "feat \u00b7 2 ahead of main \u00b7 clean", "suite": "none recorded",
                  "questions": "1 asked \u00b7 1 answered \u00b7 1 in the block", "perishables": 1,
                  "bottom_line": "Slice A is signed off. Type the kickoff line.", "open": [], "skill_note": None}
        text = forms.render_report(fields)
        self.assertTrue(text.startswith("HANDOFF: turnstile \u2014 after A\n"))
        self.assertTrue(text.endswith("Thread is safe to clear.\n"))
        self.assertEqual(forms.render_report(forms.parse_report(text)), text)

    def test_the_gate_open_form(self):
        fields = {"feature": "turnstile", "doc": DOC, "unanswered": ["which slice is next", "is the wrap at 99"]}
        text = forms.render_gate_open(fields)
        self.assertTrue(text.startswith("HANDOFF: turnstile \u2014 GATE OPEN, nothing written\n"))
        self.assertIn("Thread is NOT safe to clear", text)
        self.assertNotIn("Thread is safe to clear", text)
        self.assertEqual(forms.render_gate_open(forms.parse_gate_open(text)), text)

    def test_a_field_holding_a_line_break_or_the_separator_is_refused(self):
        with self.assertRaises(forms.FormError):
            forms.render_block(block_fields(perishables=["two\nlines"]))
        with self.assertRaises(forms.FormError):
            forms.render_block(block_fields(perishables=["a %s b" % forms.SEP.strip()]))


class NoTypedDash(unittest.TestCase):
    """Standing rule 10: no file this core writes holds a typed em dash; the forms carry it as `forms.D`."""

    def test_no_file_of_this_core_holds_a_typed_em_dash(self):
        plugin = testlib.PLUGIN
        found = []
        for base, dirs, names in os.walk(plugin):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git"))
            for name in sorted(names):
                path = os.path.join(base, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        if "\u2014" in fh.read():
                            found.append(os.path.relpath(path, plugin))
                except (UnicodeDecodeError, OSError):
                    continue
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
