"""Verdict docs are mirrors (contract section 11.6): same, differing, and absent copies.

The fixture `docs/plans/2026-05-14-mirrors.md` has three slices: A's verdict doc holds a
byte-identical copy of the build doc's block, B's holds the same block with one line worded
differently plus a record the build doc does not hold at all, and C has no verdict doc. Nothing
is repaired, nothing is imported, and a difference never blocks an import.
"""
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import events as events_mod  # noqa: E402

DOC = "docs/plans/2026-05-14-mirrors.md"
VERDICT_A = "docs/reviews/2026-05-15-signoff-mirrors-a.md"
VERDICT_B = "docs/reviews/2026-05-15-signoff-mirrors-b.md"


class Mirrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-mirrors-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)
        code, cls.body, err = testlib.run_json(
            ["mirrors", "--workspace", cls.workspace, "--doc", DOC])
        assert code == 0, (cls.body, err)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def row(self, slice_name):
        rows = [r for r in self.body["mirrors"] if r["slice"] == slice_name]
        self.assertEqual(len(rows), 1, slice_name)
        return rows[0]

    def test_every_slice_of_the_document_is_reported(self):
        self.assertEqual([r["slice"] for r in self.body["mirrors"]], ["A", "B", "C"])
        self.assertEqual(self.body["slices"], ["A", "B", "C"])
        self.assertEqual(self.body["spec"], {"doc": DOC, "slice": None})

    def test_a_byte_identical_copy_is_same(self):
        row = self.row("A")
        self.assertEqual(row["verdict_doc"], VERDICT_A)
        self.assertEqual(row["state"], "same")
        self.assertEqual([b["state"] for b in row["blocks"]], ["same"])
        self.assertEqual(row["only_in_mirror"], [])

    def test_a_copy_with_one_line_reworded_differs(self):
        row = self.row("B")
        self.assertEqual(row["verdict_doc"], VERDICT_B)
        self.assertEqual(row["state"], "differs")
        states = [b["state"] for b in row["blocks"]]
        self.assertEqual(states, ["differs", "absent"])
        self.assertEqual(row["blocks"][0]["heading"], "### 2026-05-15 — recheck: Slice B")
        self.assertEqual(row["blocks"][0]["lines"], 1)
        self.assertEqual(row["blocks"][0]["ledger_lines"], 1)

    def test_a_record_only_the_verdict_doc_holds_is_reported(self):
        """A demonstration run recorded only there is a real case (section 11.6)."""
        row = self.row("B")
        self.assertEqual(len(row["only_in_mirror"]), 1)
        only = row["only_in_mirror"][0]
        self.assertEqual(only["kind"], "recheck")
        self.assertIn("the demonstration run printed a blank label", only["raw"])

    def test_a_slice_with_no_verdict_doc_is_absent(self):
        row = self.row("C")
        self.assertIsNone(row["verdict_doc"])
        self.assertEqual(row["state"], "absent")
        self.assertEqual(row["blocks"], [])
        self.assertIn("no verdict doc matches the glob", row["reason"])

    def test_the_counts_add_up(self):
        self.assertEqual(self.body["counts"],
                         {"same": 1, "differs": 1, "absent": 1, "only_in_mirror": 1})

    def test_the_verdict_docs_are_found_by_the_pilots_own_glob(self):
        testlib.add_pilot_to_path()
        from recheck_core import ledger as pilot
        self.assertEqual(pilot.verdict_doc_glob(self.workspace, DOC, "A"), [VERDICT_A])
        self.assertEqual(pilot.verdict_doc_glob(self.workspace, DOC, "C"), [])


class MirrorsChangeNothing(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-mirrors-write-")
        self.workspace = testlib.fixture_workspace(self.scratch)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_it_writes_nothing_at_all(self):
        before = testlib.porcelain(self.workspace)
        hashes = dict((d, testlib.doc_sha256(self.workspace, d))
                      for d in (DOC, VERDICT_A, VERDICT_B))
        code, body, err = testlib.run_json(["mirrors", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        self.assertEqual(testlib.porcelain(self.workspace), before)
        for doc, digest in hashes.items():
            self.assertEqual(testlib.doc_sha256(self.workspace, doc), digest, doc)
        self.assertFalse(os.path.isdir(os.path.join(self.workspace, "docs", "records")))

    def test_a_difference_never_blocks_an_import(self):
        code, body, err = testlib.run_json(
            ["import-legacy", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertGreater(body["imported"], 0)

    def test_the_verdict_doc_is_never_imported(self):
        testlib.run_json(["import-legacy", "--workspace", self.workspace, "--doc", DOC])
        for event in testlib.events_of(self.workspace, DOC):
            origin = event["origin"]
            if origin["kind"] == "legacy":
                self.assertEqual(origin["doc"], DOC,
                                 "an import reads one document; a mirror is never a second source")
        self.assertFalse(os.path.exists(events_mod.log_path(self.workspace, VERDICT_A)))
        self.assertFalse(os.path.exists(events_mod.log_path(self.workspace, VERDICT_B)))

    def test_the_only_in_mirror_record_never_reaches_the_log(self):
        testlib.run_json(["import-legacy", "--workspace", self.workspace, "--doc", DOC])
        raws = [e["origin"].get("raw") or "" for e in testlib.events_of(self.workspace, DOC)]
        self.assertFalse(any("demonstration run" in raw for raw in raws))

    def test_a_document_with_no_verdict_doc_directory_reports_every_slice_absent(self):
        shutil.rmtree(os.path.join(self.workspace, "docs", "reviews"))
        code, body, err = testlib.run_json(["mirrors", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        self.assertEqual([r["state"] for r in body["mirrors"]], ["absent", "absent", "absent"])


if __name__ == "__main__":
    unittest.main()
