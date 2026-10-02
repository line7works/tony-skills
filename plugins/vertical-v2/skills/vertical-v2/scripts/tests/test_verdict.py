"""vertical-v2's verdict and report (contract sections 3.8 and 3.9; readings CR-7 and CR-8).

The verified findings (CONFIRMED and PLAUSIBLE) are deduped on file:line and claim, the refuted ones
counted as `Refuted: N`, the severity mapping names the verdict, the repeats and misses are read against
the ledger through the records component, and the one write is the verdict doc
`docs/reviews/<date>-vertical-<feature>.md`, v1's three sections, rendered by `forms.py`; a rerun appends
a dated block to the same file, never a second file, never an edit of an earlier block. The archive copies
are removed after the verdict. A report-only run writes nothing. `report` ends the run with the
`VERTICAL:` block.
"""
import json
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()

from vertical_core import forms  # noqa: E402

DOC_NAME = "2026-10-01-vertical-turnstile.md"
OUT_A = "run-0001-gpt-astra"


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the verdict runs after the fleets (records, readers' roster, jsonschema)")
class _Verdict(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vverdict-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def verdict(self, drive, run_dir):
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        return out

    def doc(self, ws):
        return testlib.read_text(os.path.join(ws, "docs", "reviews", DOC_NAME))


class TheWrite(_Verdict):

    def test_a_local_only_review_writes_one_doc_with_v1s_three_sections(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        before = testlib.tree_digest(ws)
        out = self.verdict(drive, run_dir)
        self.assertEqual(vlib.verdict_docs(ws), [DOC_NAME])
        parsed = forms.parse_doc(self.doc(ws))
        block = parsed["blocks"][0]
        self.assertEqual((block["verdict"], block["refuted"], block["findings"]), ("SIGNED OFF", 0, []))
        self.assertTrue(any(line.startswith("Base: %s" % info["base"]) for line in block["method"]), block["method"])
        self.assertIn(forms.BANNER, self.doc(ws))
        self.assertEqual(len(block["appendix"]), 3)
        os.remove(os.path.join(ws, "docs", "reviews", DOC_NAME))
        self.assertEqual(testlib.tree_digest(ws), before, "the verdict doc is the one write")

    def test_the_copies_are_removed_after_the_verdict(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        self.verdict(drive, run_dir)
        for name in ("local", "export"):
            self.assertFalse(os.path.exists(os.path.join(run_dir, name)), name)

    def test_a_rerun_appends_a_dated_block_to_the_same_file(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        self.verdict(drive, run_dir)
        first = self.doc(ws)
        testlib.git(ws, ["add", "-A"])
        testlib.git(ws, ["commit", "-q", "-m", "file the verdict"])
        drive2, run_dir2 = vlib.start(self.tmp, ws, run="run-2")
        code, out, err = vlib.through_ask(drive2, self.tmp, run_dir2, rows=())
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(drive2(["scope", "--run-dir", run_dir2])[0], 0)
        self.assertEqual(drive2(["request", "--run-dir", run_dir2])[0], 0)
        vlib.file_local_sidecars(run_dir2)
        self.assertEqual(vlib.record_local(drive2, self.tmp, run_dir2, name="local-2.json")[0], 0)
        self.verdict(drive2, run_dir2)
        second = self.doc(ws)
        self.assertEqual(vlib.verdict_docs(ws), [DOC_NAME])
        self.assertTrue(second.startswith(first))
        self.assertEqual(len(forms.parse_doc(second)["blocks"]), 2)

    def test_two_verdict_docs_for_one_build_stop_the_write(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        for name in ("2026-09-01-vertical-turnstile.md", "2026-09-02-vertical-turnstile.md"):
            testlib.write_text(os.path.join(ws, "docs", "reviews", name), "# Vertical review\n")
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "verdict-doc-ambiguous")

    def test_a_report_only_run_writes_nothing(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=(), report_only=True)
        before = testlib.tree_digest(ws)
        out = self.verdict(drive, run_dir)
        self.assertEqual(testlib.tree_digest(ws), before)
        self.assertEqual(vlib.verdict_docs(ws), [])
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Clean; nothing to fix."])
        self.assertEqual(code, 10, (out, err))
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(out["writes"][-1]["kind"], "run_artifact")


class TheMerge(_Verdict):

    def test_refuted_findings_are_counted_and_kept_out_of_the_verdict(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, outside_findings=[
            vlib.finding("src/turnstile.py:4", severity="BLOCKER", found_by=[OUT_A], claim="reset loses the count"),
            vlib.finding("src/ghost.py:9", stamp="REFUTED", found_by=[OUT_A], claim="a ghost import",
                         refuted_because="no such file in the reviewed copy")])
        self.verdict(drive, run_dir)
        block = forms.parse_doc(self.doc(ws))["blocks"][0]
        self.assertEqual(block["verdict"], "REJECTED")
        self.assertEqual(block["refuted"], 1)
        self.assertEqual([f["location"] for f in block["findings"]], ["src/turnstile.py:4"])

    def test_one_finding_from_two_reviewers_is_listed_once_with_both(self):
        local_id = "run-0001-local-correctness"
        drive, run_dir, ws, info = vlib.through_outside(
            self.tmp, local_findings=[vlib.finding("src/turnstile.py:4", found_by=[local_id], claim="reset loses the count")],
            outside_findings=[vlib.finding("src/turnstile.py:4", found_by=[OUT_A], claim="reset loses the count")])
        self.verdict(drive, run_dir)
        block = forms.parse_doc(self.doc(ws))["blocks"][0]
        self.assertEqual(len(block["findings"]), 1)
        self.assertEqual(sorted(block["findings"][0]["reviewers"]), ["gpt-astra", "local:correctness"])
        self.assertEqual(block["verdict"], "SIGNED OFF WITH CONDITIONS")

    def test_repeats_and_misses_are_read_against_the_ledger(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=("gpt-astra",), outside_findings=[
            vlib.finding("src/turnstile.py:2", severity="MINOR", found_by=[OUT_A], claim="the counter skips a turn")])
        self.verdict(drive, run_dir)
        block = forms.parse_doc(self.doc(ws))["blocks"][0]
        self.assertEqual(len(block["repeats"]), 1)
        self.assertIn("fixed", block["repeats"][0])
        again = os.path.join(self.tmp, "again")
        os.makedirs(again)
        drive, run_dir, ws2, info = vlib.through_outside(again, rows=("gpt-astra",))
        self.verdict(drive, run_dir)
        block = forms.parse_doc(testlib.read_text(os.path.join(ws2, "docs", "reviews", DOC_NAME)))["blocks"][0]
        self.assertEqual(len(block["misses"]), 1)
        self.assertIn("src/turnstile.py:2", block["misses"][0])

    def test_the_method_line_names_the_outside_reviewer_and_the_dropped_one(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, statuses={"deepseek": "transport-failed"})
        self.verdict(drive, run_dir)
        method = forms.parse_doc(self.doc(ws))["blocks"][0]["method"]
        self.assertTrue(any(l.startswith("Outside: gpt-astra") and "parity:" in l and "isolation:" in l for l in method), method)
        self.assertTrue(any(l.startswith("Dropped: deepseek") and "transport-failed" in l for l in method), method)
        self.assertTrue(any(l.startswith("Local: ") for l in method), method)


class ThePhases(_Verdict):

    def test_the_verdict_waits_for_the_named_outside_fleet(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra",))
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))
        self.assertIn("request --outside", err)

    def test_report_ends_the_run_with_the_vertical_block(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=("gpt-astra",))
        self.verdict(drive, run_dir)
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Signed off; nothing to fix."])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("completed", None))
        chat = testlib.read_text(os.path.join(run_dir, "chat.md"))
        fields = forms.parse_vertical(chat)
        self.assertEqual(fields["verdict"], "SIGNED OFF")
        self.assertEqual(fields["reviewers"], ["gpt-astra"])
        self.assertEqual(fields["verdict_doc"], "docs/reviews/%s" % DOC_NAME)
        code, rout, rerr = testlib.run_script("validate-result.py", [os.path.join(run_dir, "result.json")])
        self.assertEqual(code, 0, rout + rerr)
        trace_check = testlib.run_script("validate-trace.py", [os.path.join(run_dir, "trace.jsonl")])
        self.assertEqual(trace_check[0], 0, trace_check[1] + trace_check[2])

    def test_report_needs_the_bottom_line(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        self.verdict(drive, run_dir)
        code, out, err = drive(["report", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))


if __name__ == "__main__":
    unittest.main()
