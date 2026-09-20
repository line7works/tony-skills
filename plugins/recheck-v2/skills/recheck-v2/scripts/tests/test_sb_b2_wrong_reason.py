"""Batch B, B2: the core's wrong reason (E11-45 S3 and N2).

`derive_reason` step 3 returned `reproduces` for ANY executed command before step 4 could see
an absent required input, and step 4 asked for `not commands`, so a command that RAN AND HIT
the absent input could never reach the absent-input rule. All eight round-2 with-skill F4
trials had a correct `missing_evidence` from the verifier replaced: six defaulted to
`reproduces`, two went to `verification_blocked` through `declared_block` reading a BACKTICKED
negation ("this is not `verification_blocked`") as a declaration.

The eight cases live in `fixtures/f4-missing-fixture-round2.json`, copied from each trial's own
retained verifier report with its source path and sha256. Only verifier output is copied; no
expected value from the answer key is read here, and the assertion is the core's own
derivation, never a key comparison.

Standard library only, Python 3.9, runs from anywhere.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import verifier  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures",
                       "f4-missing-fixture-round2.json")
# The derivation reads artifact files relative to a run directory. Every fixture entry carries
# its evidence as DETAIL TEXT with no artifact, so no run directory has to exist.
NO_RUN_DIR = "/nonexistent/run-dir-the-fixtures-never-read"


def cases():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


class TheEightF4Examples(unittest.TestCase):
    """Each of the eight must KEEP `missing_evidence`."""

    def test_all_eight_are_present_with_their_source_named(self):
        rows = cases()
        self.assertEqual(len(rows), 8)
        self.assertEqual(sorted({r["setup"] for r in rows}),
                         ["claude-code", "codex", "opencode", "opencode-deepseek"])
        self.assertEqual(sorted({r["repetition"] for r in rows}), ["r1", "r2"])
        for row in rows:
            self.assertTrue(row["retained_copy"].startswith("~/"), row["trial"])
            self.assertEqual(len(row["retained_copy_sha256"]), 64, row["trial"])
            self.assertEqual(row["verifier_typed_reason"], "missing_evidence", row["trial"])

    def test_every_one_of_the_eight_keeps_missing_evidence(self):
        for row in cases():
            with self.subTest(trial=row["trial"]):
                got = verifier.derive_reason(dict(row["item"]), NO_RUN_DIR,
                                             call_status="ok",
                                             report_text=row["report_excerpt"] or None)
                self.assertEqual(got["reason"], "missing_evidence",
                                 "%s: derived %r (%s)"
                                 % (row["trial"], got["reason"], got["how"]))
                self.assertEqual(got["observed"], "a required input is absent")

    def test_the_two_backticked_negations_are_the_ones_that_needed_the_scan_fix(self):
        """The two `verification_blocked` cases carry the negation the old scan lost."""
        backticked = [r for r in cases()
                      if r["what_the_core_wrote_instead"] == "verification_blocked"]
        self.assertEqual(len(backticked), 2)
        for row in backticked:
            with self.subTest(trial=row["trial"]):
                self.assertIn("`verification_blocked`", row["report_excerpt"])


class TheBacktickedNegation(unittest.TestCase):
    """N2: a negation survives backticks and markdown emphasis."""

    def test_a_backticked_phrase_is_still_negated(self):
        phrase, _quote = verifier.declared_block(
            "The command ran to completion, so this is not `verification_blocked`.")
        self.assertIsNone(phrase)

    def test_bolded_and_italicised_phrases_are_still_negated(self):
        for text in ("Nothing is **verification blocked**.",
                     "This was not _execution was refused_ in any sense.",
                     "It is not ~~verification blocked~~ at all."):
            with self.subTest(text=text):
                self.assertIsNone(verifier.declared_block(text)[0])

    def test_an_unnegated_backticked_declaration_still_declares(self):
        """The fix must not make every backticked phrase disappear."""
        phrase, quote = verifier.declared_block(
            "The sandbox refused it: `verification_blocked` is the outcome.")
        self.assertEqual(phrase, "verification_blocked")
        self.assertTrue(quote)

    def test_a_punctuation_only_token_does_not_end_the_walk_early(self):
        self.assertTrue(verifier._negated_before(
            "this is not ` verification_blocked".lower(), len("this is not ` ")))


class TheInverseCases(unittest.TestCase):
    """A real reproduction stays `reproduces`; a real refusal stays `verification_blocked`."""

    RUN = NO_RUN_DIR

    def derive(self, **item):
        item.setdefault("method", "executed")
        item.setdefault("evidence", [])
        report = item.pop("report_text", None)
        return verifier.derive_reason(item, self.RUN,
                                      call_status=item.pop("call_status", "ok"),
                                      report_text=report)

    def test_a_real_reproduction_stays_reproduces(self):
        got = self.derive(evidence=[{
            "kind": "command",
            "detail": "PYTHONPATH=src python3 -m widget.export tests/fixtures/orders-comma.tsv"
                      " -> Widget, large,3,9.99 (four fields, the title unquoted), exit 0"}])
        self.assertEqual(got["reason"], "reproduces", got["how"])

    def test_a_real_refusal_stays_verification_blocked(self):
        got = self.derive(evidence=[{
            "kind": "command",
            "detail": "curl https://service.internal/v1/emit -> operation not permitted by "
                      "the sandbox"}])
        self.assertEqual(got["reason"], "verification_blocked", got["how"])

    def test_a_refusal_wins_over_an_absent_input_in_the_same_output(self):
        """The refusal and the unreachable service are tested first and still are."""
        got = self.derive(evidence=[{
            "kind": "command",
            "detail": "curl https://service.internal/v1/emit -> operation not permitted; "
                      "then ls cache/token: No such file or directory"}])
        self.assertEqual(got["reason"], "verification_blocked", got["how"])

    def test_an_unreachable_service_wins_over_an_absent_input(self):
        got = self.derive(evidence=[{
            "kind": "command",
            "detail": "curl: (6) Could not resolve host: service.internal; the cached "
                      "response file does not exist either"}])
        self.assertEqual(got["reason"], "verification_blocked", got["how"])

    def test_a_declared_block_with_no_command_still_blocks(self):
        got = self.derive(method="static",
                          evidence=[{"kind": "read", "detail": "read the handler source"}],
                          report_text="The environment stopped the run before it began.")
        self.assertEqual(got["reason"], "verification_blocked", got["how"])

    def test_an_absent_input_with_no_command_is_still_missing_evidence(self):
        """Step 4, untouched: no command ran at all."""
        got = self.derive(method="static", static_reason="non_executable_artifact",
                          missing="the fixture carries no such file or directory to read",
                          evidence=[{"kind": "read", "detail": "looked for the artifact"}])
        self.assertEqual(got["reason"], "missing_evidence", got["how"])

    def test_the_derivation_still_never_reads_the_typed_reason(self):
        evidence = [{"kind": "command",
                     "detail": "ran the scenario -> No such file or directory: fixtures/x.tsv"}]
        a = self.derive(reason="reproduces", evidence=[dict(e) for e in evidence])
        b = self.derive(reason="missing_evidence", evidence=[dict(e) for e in evidence])
        self.assertEqual(a, b)
        self.assertEqual(a["reason"], "missing_evidence")


if __name__ == "__main__":
    unittest.main()
