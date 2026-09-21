"""E13 slice 1, brief 3.2 CR-1 and CR-2: the log is levelled with the document before it is read.

v1 signoff still writes findings into the Markdown by hand, so a document can be AHEAD of its log.
At the start of every phase that used to parse the document for records the pilot runs
`import-legacy` for that document, whether or not a log exists; the importer is idempotent. An
ambiguous document, or a record that changed above the imported tail, stops the run with the
importer's own explanation and writes nothing to the document.

CR-2: a pilot command that is read-only today stays read-only. `check-input` and `ledger` use
`import-legacy --dry-run`, which takes no lock and writes nothing.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import records_client as rc  # noqa: E402

RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
DOC = "docs/plans/2026-09-18-widget-export.md"
LOG = "docs/records/docs__plans__2026-09-18-widget-export.events.jsonl"


class SyncBase(unittest.TestCase):
    LANE = "F1-fixed-defect"
    CASE = "F1-01-fixed-clean"

    def setUp(self):
        self.dir = testlib.make_scratch("e13-sync-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case(self.LANE, self.CASE, self.dir)
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.client = rc.open_client(records_root=RECORDS)
        testlib.prepare_input(self.case)

    def doc_path(self):
        return os.path.join(self.workspace, DOC)

    def doc_bytes(self):
        with open(self.doc_path(), "rb") as fh:
            return fh.read()

    def log_path(self):
        return os.path.join(self.workspace, LOG)

    def log_lines(self):
        if not os.path.isfile(self.log_path()):
            return []
        with open(self.log_path(), "r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def append_to_doc(self, text):
        with open(self.doc_path(), "a", encoding="utf-8") as fh:
            fh.write(text)

    def start(self, *extra):
        return testlib.recheck(["start", os.path.join(self.case, "input.json")] + list(extra), cwd=self.dir)


class Sync(SyncBase):
    def test_start_imports_the_document_before_the_open_set_is_read(self):
        self.assertFalse(os.path.exists(self.log_path()))
        code, doc, err = self.start()
        self.assertEqual(code, 0, err)
        self.assertTrue(os.path.isfile(self.log_path()), "the log was not written before scope was read")
        kinds = [e["kind"] for e in self.log_lines()]
        self.assertIn("finding_raised", kinds)
        self.assertEqual(len(doc["checklist"]), 1)
        self.assertEqual(doc["checklist"][0]["claim"],
                         "CSV export writes a title containing a comma without quoting")

    def test_a_second_pass_over_an_unchanged_document_appends_nothing(self):
        self.client.import_legacy(self.workspace, DOC)
        before = self.log_lines()
        code, doc, err = self.start()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.log_lines(), before, "the importer is not idempotent")

    def test_a_document_ahead_of_its_log_is_levelled(self):
        self.client.import_legacy(self.workspace, DOC)
        first = len(self.log_lines())
        self.append_to_doc(
            "\n### 2026-09-19 — review: Slice A\n"
            "- MAJOR · src/widget/export.py:31 · the header line is written twice · "
            "run the exporter twice and read the file; two header lines · Slice A\n")
        code, doc, err = self.start()
        self.assertEqual(code, 0, err)
        self.assertGreater(len(self.log_lines()), first, "the hand-written finding never reached the log")
        claims = sorted(it["claim"] for it in doc["checklist"])
        self.assertEqual(claims, ["CSV export writes a title containing a comma without quoting",
                                  "the header line is written twice"])


class Ambiguous(SyncBase):
    def test_an_ambiguous_document_stops_the_run_and_writes_nothing(self):
        # Two findings at one location and a clearing line that names no claim: Appendix A says a
        # claim-less record at a shared location decides nothing, and the importer stops on it.
        self.append_to_doc(
            "\n### 2026-09-19 — review: Slice A\n"
            "- MAJOR · src/widget/export.py:17 · a second finding at the same line · "
            "run the exporter and read the header · Slice A\n"
            "\n### 2026-09-19 — recheck: Slice A\n"
            "- MAJOR · src/widget/export.py:17 · () · fixed · executed the scenario\n")
        before = self.doc_bytes()
        code, doc, err = self.start()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "missing_input")
        self.assertEqual(self.doc_bytes(), before, "the document was written")
        self.assertFalse(os.path.exists(self.log_path()), "an ambiguous document must append nothing")


class ReadOnlyCommands(SyncBase):
    """CR-2: a command that writes nothing today still writes nothing."""

    def test_check_input_writes_no_log(self):
        code, doc, err = testlib.recheck(["check-input", os.path.join(self.case, "input.json")], cwd=self.dir)
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["wrote"], [])
        self.assertFalse(os.path.exists(self.log_path()), "check-input wrote the log")
        self.assertIn("records_behind", doc)
        self.assertGreater(doc["records_behind"], 0, "the dry run saw nothing the log lacks")

    def test_ledger_writes_no_log(self):
        code, doc, err = testlib.recheck(["ledger", self.doc_path(), "--workspace", self.workspace], cwd=self.dir)
        self.assertEqual(code, 0, err)
        self.assertFalse(os.path.exists(self.log_path()), "ledger wrote the log")
        self.assertIn("records_behind", doc)


if __name__ == "__main__":
    unittest.main()
