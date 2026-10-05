"""Section 11.7 as the E15 lane contract A23 (1) widened it: an imported record line that only MOVED.

A build doc keeps `## Handoffs` and the ledger sections above `## Punch list`, so a station that writes a handoff
block, or a build-v2 ledger line, above the imported record lines moves every one of them down. Before A23 every
later `import-legacy` refused such a document (exit 7). Now an imported record line that only moved, its raw bytes
unchanged and its order among the imported lines unchanged (matched in order by `origin.raw`), is accepted; a
changed, dropped or reordered imported line still refuses (exit 7), and so does a new record above the imported
tail, wherever that tail now stands. The shapes are the slice 1b check's `p02` (a handoff block above the imported
lines) and `p18` (a build-v2 ledger line above them).
"""
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()
testlib.add_fixtures_to_path()

from records_core import events as events_mod  # noqa: E402

D = "\u2014"
M = "\u00b7"
HISTORY = "docs/plans/2026-05-12-history.md"
TWO = "docs/plans/2026-05-20-two-findings.md"
HANDOFF_BLOCK = ("## Handoffs\n\n### 2026-10-04 %s handoff\n- Next: /ship-v2 B docs/plans/2026-05-12-history.md\n"
                 "- Cards: A signed off %s B not started\n- Perishable: the crate scale drifts\n\n" % (D, M))
LEDGER_LINE = "## Build assumptions\n- 2026-10-04 slice A: the list reuses the loader\n\n"
FIRST = "- MAJOR %s src/gate.py:3 %s the gate sticks %s a crate waits %s Slice A review" % (M, M, M, M)
SECOND = "- MINOR %s src/gate.py:9 %s the gate name is vague %s a reader guesses %s Slice A review" % (M, M, M, M)


class MovedCase(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-moved-")
        self.workspace = testlib.fixture_workspace(self.scratch)
        self.build = testlib.fixture_build_module()

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def path(self, doc):
        return os.path.join(self.workspace, *doc.split("/"))

    def read(self, doc=HISTORY):
        with open(self.path(doc), encoding="utf-8") as fh:
            return fh.read()

    def write(self, text, doc=HISTORY):
        with open(self.path(doc), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def run_import(self, *extra, **kwargs):
        doc = kwargs.get("doc", HISTORY)
        return testlib.run_json(["import-legacy", "--workspace", self.workspace, "--doc", doc] + list(extra))

    def log_bytes(self, doc=HISTORY):
        path = events_mod.log_path(self.workspace, doc)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()

    def imported_first(self, doc=HISTORY):
        code, body, err = self.run_import(doc=doc)
        self.assertEqual(code, 0, (body, err))
        self.assertGreater(body["imported"], 0)
        return self.log_bytes(doc)

    def insert_before_punch_list(self, block, doc=HISTORY):
        text = self.read(doc)
        self.assertIn("\n## Punch list\n", text)
        self.write(text.replace("\n## Punch list\n", "\n" + block + "## Punch list\n", 1), doc)


class AnImportedLineThatOnlyMovedIsAccepted(MovedCase):
    def test_p02_a_handoff_block_above_the_imported_lines_levels_with_a_dry_run(self):
        before = self.imported_first()
        self.insert_before_punch_list(HANDOFF_BLOCK)
        code, body, err = self.run_import("--dry-run")
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["would_import"], 0, body)
        self.assertEqual(body["previously_imported"], 2)
        self.assertEqual(self.log_bytes(), before, "a dry run writes nothing")

    def test_p02_and_the_real_pass_appends_nothing(self):
        before = self.imported_first()
        self.insert_before_punch_list(HANDOFF_BLOCK)
        code, body, err = self.run_import()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["imported"], 0)
        self.assertEqual(self.log_bytes(), before)

    def test_p18_a_build_ledger_line_above_the_imported_lines_levels(self):
        before = self.imported_first()
        self.insert_before_punch_list(LEDGER_LINE)
        code, body, err = self.run_import("--dry-run")
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["would_import"], 0, body)
        self.assertEqual(self.log_bytes(), before)

    def test_a_line_that_moved_up_is_accepted_too(self):
        self.imported_first()
        text = self.read()
        self.assertIn("importer's feet.\n\n## Slice A", text)
        self.write(text.replace("importer's feet.\n\n## Slice A", "importer's feet.\n## Slice A", 1))
        code, body, err = self.run_import("--dry-run")
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["would_import"], 0, body)

    def test_after_a_move_a_record_grown_at_the_tail_is_the_only_news(self):
        before = self.imported_first()
        self.insert_before_punch_list(HANDOFF_BLOCK)
        self.write(self.read().rstrip("\n") + "\n" + self.build.GROWN_TAIL)
        code, body, err = self.run_import()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual([row["kind"] for row in body["appended"]],
                         ["import_started", "disposition", "import_finished"])
        self.assertTrue(self.log_bytes().startswith(before))
        lines = self.read().split("\n")
        news = [e for e in testlib.events_of(self.workspace, HISTORY) if e["kind"] == "disposition"][-1]
        self.assertEqual(lines[news["origin"]["line"] - 1], news["origin"]["raw"],
                         "a new record's origin names the line it reads on now")

    def test_after_a_move_a_new_record_above_the_moved_tail_still_refuses(self):
        before = self.imported_first()
        self.insert_before_punch_list(HANDOFF_BLOCK)
        lines = self.read().split("\n")
        at = next(i for i, line in enumerate(lines) if line.startswith("### 2026-05-13"))
        self.assertEqual(lines[at - 1], "")
        lines[at - 1] = "- MINOR %s src/list.py:9 %s the list header is not printed %s a loader guesses %s " \
                        "Slice A review" % (M, M, M, M)
        self.write("\n".join(lines))
        code, body, err = self.run_import()
        self.assertEqual(code, 7, (body, err))
        self.assertEqual(body["error"], "conflict")
        self.assertEqual(body["line"], at)
        self.assertGreater(body["last_imported_line"], at, "the tail is where the moved lines stand now")
        self.assertEqual(self.log_bytes(), before)


class AChangedDroppedOrReorderedLineStillRefuses(MovedCase):
    def two_finding_doc(self):
        self.write("\n".join([
            "# Two findings", "", "## Slice A %s the gate" % D, "Status: signed off with conditions", "",
            "## Punch list", "", "### 2026-05-20 %s review: Slice A" % D, FIRST, SECOND, ""]), doc=TWO)
        return self.imported_first(doc=TWO)

    def test_a_changed_line_after_a_move_is_exit_seven(self):
        before = self.imported_first()
        self.insert_before_punch_list(HANDOFF_BLOCK)
        self.write(self.read().replace(self.build.CHANGED_FROM, self.build.CHANGED_TO))
        code, body, err = self.run_import()
        self.assertEqual(code, 7, (body, err))
        self.assertEqual(body["error"], "conflict")
        self.assertEqual(body["imported_raw"], self.build.CHANGED_FROM)
        self.assertEqual(self.log_bytes(), before)

    def test_a_dropped_line_after_a_move_is_exit_seven(self):
        before = self.imported_first()
        self.insert_before_punch_list(HANDOFF_BLOCK)
        self.write(self.read().replace(self.build.CHANGED_FROM + "\n", ""))
        code, body, err = self.run_import("--dry-run")
        self.assertEqual(code, 7, (body, err))
        self.assertEqual(body["imported_raw"], self.build.CHANGED_FROM)
        self.assertEqual(self.log_bytes(), before)

    def test_two_swapped_lines_are_exit_seven(self):
        before = self.two_finding_doc()
        text = self.read(TWO)
        self.write(text.replace(FIRST + "\n" + SECOND, SECOND + "\n" + FIRST), doc=TWO)
        code, body, err = self.run_import(doc=TWO)
        self.assertEqual(code, 7, (body, err))
        self.assertEqual(body["error"], "conflict")
        self.assertIn(body["imported_raw"], (FIRST, SECOND))
        self.assertEqual(self.log_bytes(TWO), before)

    def test_two_swapped_lines_that_also_moved_are_exit_seven(self):
        before = self.two_finding_doc()
        text = self.read(TWO)
        text = text.replace(FIRST + "\n" + SECOND, SECOND + "\n" + FIRST)
        self.write(text.replace("\n## Punch list\n", "\n" + HANDOFF_BLOCK + "## Punch list\n", 1), doc=TWO)
        code, body, err = self.run_import("--dry-run", doc=TWO)
        self.assertEqual(code, 7, (body, err))
        self.assertEqual(self.log_bytes(TWO), before)

    def test_the_same_two_lines_moved_in_order_are_accepted(self):
        before = self.two_finding_doc()
        self.insert_before_punch_list(HANDOFF_BLOCK, doc=TWO)
        code, body, err = self.run_import(doc=TWO)
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["imported"], 0)
        self.assertEqual(self.log_bytes(TWO), before)

    def test_a_copy_of_an_imported_line_outside_every_record_block_does_not_stand_in_for_it(self):
        """The match is among the doc's record lines: a prose or fenced copy of an imported line above it is not
        the imported line, so the real line, moved, is still matched and nothing is news."""
        before = self.two_finding_doc()
        copy = "## Notes\n\n```text\n%s\n```\n\n" % FIRST
        self.insert_before_punch_list(copy, doc=TWO)
        code, body, err = self.run_import(doc=TWO)
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["imported"], 0)
        self.assertEqual(self.log_bytes(TWO), before)


if __name__ == "__main__":
    unittest.main()
