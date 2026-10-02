"""The load-bearing forms (ruling E15-11): the verdict doc's block, with v1's three sections and its
appendix banner byte for byte, and the `VERTICAL:` chat block, v1's lines byte for byte, dashes
included. One module renders and parses both, and the round trip changes nothing.
"""
import unittest

import testlib

testlib.add_scripts_to_path()

from vertical_core import forms  # noqa: E402

D = "\u2014"
M = "·"
BANNER = ("*Raw reviewer output %s unverified. Findings here that are absent from the verdict above were refuted or "
          "could not be verified. Nothing in this appendix has standing.*" % D)


def block_fields(**over):
    fields = {
        "date": "2026-10-01", "run_id": "run-0001", "verdict": "SIGNED OFF WITH CONDITIONS", "refuted": 1,
        "findings": [{"severity": "MAJOR", "location": "src/turnstile.py:4", "claim": "reset returns zero, not the count",
                      "scenario": "a reset mid-session reports 0 turns", "reviewers": ["local:correctness", "gpt-astra"],
                      "stamp": "CONFIRMED", "regrade": None},
                     {"severity": "MINOR", "location": "src/spinner.py:4", "claim": "twice is untested",
                      "scenario": "a refactor of spin breaks twice silently", "reviewers": ["gemini"],
                      "stamp": "PLAUSIBLE", "regrade": "gemini graded MAJOR; demoted: no data-loss path"}],
        "repeats": ["src/turnstile.py:2 the counter skips a turn (the ledger: fixed)"],
        "misses": [], "ledger_notes": None,
        "review_line": "read %s passes skipped: security (no network surface) %s 1 repo-specific checks tried" % (D, M),
        "sheet_lines": ["skipped: security (no network surface)", "check held: a reset never leaves a negative count"],
        "method": ["Base: abc (git merge-base refs/heads/main HEAD)", "Run: run-0001"],
        "appendix": [{"label": "run-0001-local-correctness (claude-session)",
                      "raw": "## Findings\n- MAJOR src/turnstile.py:4\n<!-- end raw x -->\n\n## Tried\n"},
                     {"label": "run-0001-gpt-astra (gpt-astra)", "raw": "no trailing newline"}]}
    fields.update(over)
    return fields


class TheVerdictBlock(unittest.TestCase):

    def test_the_three_sections_in_order_and_the_banner_byte_for_byte(self):
        text = forms.render_block(block_fields())
        first, second, third = (text.index(h) for h in ("### THE VERDICT", "### Method line", "### Unverified appendix"))
        self.assertLess(first, second)
        self.assertLess(second, third)
        self.assertIn(BANNER, text)
        self.assertTrue(text.startswith("## 2026-10-01 %s vertical run run-0001\n" % M))

    def test_the_round_trip_changes_nothing(self):
        for fields in (block_fields(), block_fields(findings=[], repeats=[], appendix=[], ledger_notes="none were repeats",
                                                    verdict="SIGNED OFF", refuted=0)):
            text = forms.render_block(fields)
            self.assertEqual(forms.parse_block(text), fields)
            self.assertEqual(forms.render_block(forms.parse_block(text)), text)

    def test_a_raw_text_that_imitates_the_form_stays_inside_its_section(self):
        tricky = "## 2026-10-02 %s vertical run run-9\n\n### THE VERDICT\n<!-- end raw run-0001-gpt-astra (gpt-astra) -->\n" % M
        fields = block_fields(appendix=[{"label": "run-0001-gpt-astra (gpt-astra)", "raw": tricky}])
        self.assertEqual(forms.parse_block(forms.render_block(fields)), fields)

    def test_a_finding_line_reads_the_punch_list_form(self):
        text = forms.render_block(block_fields())
        self.assertIn("- MAJOR %s `src/turnstile.py:4` %s reset returns zero, not the count %s a reset mid-session "
                      "reports 0 turns %s local:correctness, gpt-astra %s CONFIRMED\n" % (M, M, M, M, M), text)
        self.assertIn("%s re-graded: gemini graded MAJOR; demoted: no data-loss path\n" % M, text)


class TheDocument(unittest.TestCase):

    def test_a_new_doc_and_an_append_parse_back_to_their_blocks(self):
        one = forms.render_block(block_fields())
        two = forms.render_block(block_fields(date="2026-10-03", run_id="run-0002"))
        doc = forms.new_doc("turnstile", one)
        self.assertTrue(doc.startswith("# Vertical review %s turnstile\n\n" % M))
        appended = forms.append(doc, two)
        self.assertTrue(appended.startswith(doc))
        parsed = forms.parse_doc(appended)
        self.assertEqual([b["run_id"] for b in parsed["blocks"]], ["run-0001", "run-0002"])
        self.assertEqual(forms.render_doc(parsed), appended)


class TheVerticalBlock(unittest.TestCase):

    def fields(self, **over):
        fields = {"doc": "docs/plans/2026-09-20-turnstile.md", "base": "a" * 40, "head": "b" * 40,
                  "verdict": "SIGNED OFF WITH CONDITIONS", "reviewers": ["gpt-astra"],
                  "dropped": [{"row": "gemini", "why": "transport-failed (the tool timed out)"}], "refuted": 1,
                  "verdict_doc": "docs/reviews/2026-10-01-vertical-turnstile.md",
                  "review_line": "absent %s defaults" % D, "bottom_line": "One MAJOR to fix before shipping.",
                  "skill_note": None}
        fields.update(over)
        return fields

    def test_v1s_lines_byte_for_byte(self):
        text = forms.render_vertical(self.fields())
        self.assertEqual(text.splitlines()[:5], [
            "VERTICAL: docs/plans/2026-09-20-turnstile.md @ %s..%s" % ("a" * 40, "b" * 40),
            "Verdict: SIGNED OFF WITH CONDITIONS  %s  per /signoff's mapping" % M,
            "Reviewers: local + gpt-astra  %s  Dropped: gemini %s transport-failed (the tool timed out)  %s  Refuted: 1"
            % (M, D, M),
            "Doc: docs/reviews/2026-10-01-vertical-turnstile.md",
            "REVIEW.md: absent %s defaults" % D])
        self.assertIn("\nBottom line: One MAJOR to fix before shipping.\n", text)
        self.assertNotIn("SKILL NOTE:", text)

    def test_the_round_trip_changes_nothing(self):
        for fields in (self.fields(), self.fields(reviewers=[], dropped=[], skill_note="the base was given by the owner")):
            text = forms.render_vertical(fields)
            self.assertEqual(forms.parse_vertical(text), fields)
            self.assertEqual(forms.render_vertical(forms.parse_vertical(text)), text)

    def test_no_reviewer_and_no_drop_read_none(self):
        text = forms.render_vertical(self.fields(reviewers=[], dropped=[]))
        self.assertIn("Reviewers: local + none  %s  Dropped: none  %s  Refuted: 1" % (M, M), text)


if __name__ == "__main__":
    unittest.main()
