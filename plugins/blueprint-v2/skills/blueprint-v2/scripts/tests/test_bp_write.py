"""blueprint-v2's `write` (lane L, brief 3.5 and required test 6; readings CR-10 and CR-13).

A new build doc is byte-identical to `templates.render_build_doc` on the answer's values and
passes `templates.check`, its five ledger sections present and empty; an existing doc is extended
in place, its `Status:`, `Plan: inspected` and ledger-section lines byte-identical and the new
slice after the last; a write that would change one of them is refused before anything is written
(hashes unchanged); `needs_build_doc: false` writes nothing and stops `no-build-doc`; every write
is in `receipt.json`; report-only writes nothing outside the run directory.
"""
import copy
import os
import unittest

import bplib
import testlib

testlib.add_scripts_to_path()

from station_core import templates  # noqa: E402
from blueprint_core import buildoc  # noqa: E402

D, M = bplib.D, bplib.M


class _Write(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("bp-write-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def through_answer(self, files, answer, report_only=False, run_id="run-0001"):
        self.ws = testlib.git_workspace(self.tmp, "ws", files)
        self.run = bplib.Run(self.tmp, self.ws, report_only=report_only, run_id=run_id)
        self.run.to_harvest()
        code, out, err = self.run.record(answer)
        self.assertEqual(code, 0, (out, err))
        self.harvest = testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))
        return self.run


class ANewDoc(_Write):

    def test_the_new_doc_is_the_renderers_output_and_holds_its_form(self):
        run = self.through_answer(bplib.base_files(), bplib.clean_answer())
        before = testlib.tree_digest(self.ws)
        code, out, err = run.write()
        self.assertEqual(code, 0, (out, err))
        path = self.harvest["target"]
        self.assertEqual(out["doc"], path)
        self.assertEqual(out["action"], "created")
        text = bplib.read(path)
        date = self.harvest["run_date"]
        expected = templates.render_build_doc(
            title="Turnstile", date=date,
            intent="count turns for the owner's bench rig, so a bench session reports its turns.",
            constraints="Python 3.9 standard library only. Assumed: the bench script prints the count "
                        "itself. Open: how often the counter resets.",
            out_of_scope=["a web dashboard %s the owner declined it" % D],
            slices=[{"name": "A", "short": "Count turns",
                     "goal": "`spin()` returns the count after one more turn.",
                     "requirements": ["R1 %s `spin(n)` returns `n + 1`" % D,
                                      "R2 %s the count lives in memory only" % D],
                     "criteria": [("AC1: `spin(2)` returns 3", "new test at tests/test_turnstile.py")],
                     "footprint": "src/turnstile.py, tests/test_turnstile.py",
                     "not_in_slice": "the reset", "depends_on": "nothing", "status": "not started"}])
        self.assertEqual(text, expected)
        self.assertEqual(templates.check("build-doc", text), [])
        self.assertEqual(templates.render(templates.parse("build-doc", text)), text)
        tail = text[text.index("## Build assumptions"):]
        self.assertEqual(tail, "## Build assumptions\n## Deviations\n## Discovered\n## Handoffs\n## Punch list\n")
        self.assertNotEqual(before, testlib.tree_digest(self.ws))

    def test_the_receipt_names_the_write_with_its_hashes(self):
        run = self.through_answer(bplib.base_files(), bplib.clean_answer())
        code, out, err = run.write()
        receipt = testlib.load_json(os.path.join(run.run_dir, "receipt.json"))
        self.assertEqual(receipt["writes"], [{"path": self.harvest["target"], "kind": "document",
                                              "sha256_before": None,
                                              "sha256_after": testlib.sha256_file(self.harvest["target"])}])

    def test_dependency_and_several_slices_render(self):
        answer = bplib.clean_answer()
        second = copy.deepcopy(answer["slices"][0])
        second.update(name="B", short="Print the count", requirements=["R2"], depends_on=["A"])
        answer["slices"][0]["requirements"] = ["R1"]
        answer["slices"].append(second)
        run = self.through_answer(bplib.base_files(), answer)
        code, out, err = run.write()
        self.assertEqual(code, 0, (out, err))
        text = bplib.read(self.harvest["target"])
        self.assertIn("## Slice B %s Print the count\n" % D, text)
        self.assertIn("Depends on: Slice A\n", text)
        self.assertEqual(templates.check("build-doc", text), [])

    def test_a_docs_plans_symlink_leaving_the_workspace_is_refused(self):
        run = self.through_answer(bplib.base_files(), bplib.clean_answer())
        outside = os.path.join(self.tmp, "outside-plans")
        os.makedirs(outside)
        os.makedirs(os.path.join(self.ws, "docs"), exist_ok=True)
        os.symlink(outside, os.path.join(self.ws, "docs", "plans"))
        code, out, err = run.write()
        self.assertEqual(code, 10, err)
        self.assertEqual(out["stop_tag"], "unsafe-path")
        self.assertEqual(os.listdir(outside), [])


class AnExistingDoc(_Write):

    def extend(self, answer=None):
        run = self.through_answer(bplib.base_files(build=bplib.BUILD_FILLED), answer or bplib.extension_answer())
        self.path = os.path.join(self.ws, bplib.BUILD_PATH)
        return run

    def test_extended_in_place_with_the_protected_lines_byte_identical(self):
        run = self.extend()
        code, out, err = run.write()
        self.assertEqual(code, 0, (out, err))
        self.assertEqual((out["doc"], out["action"]), (self.path, "extended"))
        after = bplib.read(self.path)
        self.assertEqual(buildoc.protected_changes(bplib.BUILD_FILLED, after), [])
        tail = bplib.BUILD_FILLED[bplib.BUILD_FILLED.index("## Build assumptions"):]
        self.assertTrue(after.endswith(tail))
        self.assertLess(after.index("## Slice A"), after.index("## Slice B"))
        self.assertLess(after.index("## Slice B"), after.index("## Build assumptions"))
        self.assertIn("Status: in progress\n", after)
        self.assertIn("Plan: inspected 2026-09-23 by gpt-6-astra", after)
        self.assertIn("- a reverse-turn mode %s waiting on the encoder spec\n" % D, after)
        self.assertEqual(templates.check("build-doc", after), [])
        self.assertEqual(sorted(os.listdir(os.path.join(self.ws, "docs", "plans"))), ["2026-09-22-turnstile.md"])
        receipt = testlib.load_json(os.path.join(run.run_dir, "receipt.json"))
        self.assertEqual(receipt["writes"][0]["sha256_before"], bplib.sha256_text(bplib.BUILD_FILLED))

    def test_the_existing_slice_text_before_the_new_one_is_unchanged(self):
        run = self.extend()
        run.write()
        after = bplib.read(self.path)
        head = bplib.BUILD_FILLED[:bplib.BUILD_FILLED.index("## Build assumptions")]
        slice_a = head[head.index("## Slice A"):]
        self.assertIn(slice_a, after)

    def test_a_revision_that_would_change_a_status_line_is_refused_before_any_write(self):
        answer = bplib.extension_answer()
        answer["slices"][0]["name"] = "A"
        answer["slices"][0]["depends_on"] = []
        run = self.extend(answer)
        before = testlib.sha256_file(self.path)
        code, out, err = run.write()
        self.assertEqual(code, 10, err)
        self.assertEqual(out["stop_tag"], "write-refused")
        self.assertIn("Status: in progress", out["reason"])
        self.assertEqual(testlib.sha256_file(self.path), before)
        self.assertTrue(out["wrote_nothing"])

    def test_a_doc_edited_by_hand_after_harvest_is_refused(self):
        run = self.extend()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("- a line added by hand\n")
        before = testlib.sha256_file(self.path)
        code, out, err = run.write()
        self.assertEqual(code, 10, err)
        self.assertEqual(out["stop_tag"], "stale-harvest")
        self.assertEqual(testlib.sha256_file(self.path), before)


class NothingTheAnswerCarriesIsDropped(_Write):
    """R4 (CL1-4): on an extension the answer's constraints, assumptions and open questions reach the
    doc: a `Constraints:` line is inserted after `Intent:` when the doc has none, and an item already
    there is one equal to it whole, never a substring."""

    def extend_with(self, doc, answer):
        self.through_answer(bplib.base_files(build=doc), answer)
        path = os.path.join(self.ws, bplib.BUILD_PATH)
        code, out, err = self.run.write()
        self.assertEqual(code, 0, (out, err))
        return path, bplib.read(path)

    def test_a_doc_with_no_constraints_line_gets_one_after_intent(self):
        doc = bplib.BUILD_FILLED.replace("Constraints: Python 3.9 standard library; `python3 -m unittest`.\n", "")
        answer = bplib.extension_answer()
        answer["assumptions"] = ["the bench rig keeps one process per session"]
        answer["open_questions"] = ["does reset persist across sessions"]
        path, after = self.extend_with(doc, answer)
        lines = after.split("\n")
        at = lines.index("Intent: count turns for the owner's bench rig.")
        self.assertEqual(lines[at + 1], "Constraints: Python 3.9 standard library. Assumed: the bench rig keeps one "
                                        "process per session. Open: does reset persist across sessions.")
        self.assertEqual(buildoc.protected_changes(doc, after), [])
        self.assertEqual([f for f in templates.check("build-doc", after)], [])
        code, out, err = self.run.report()
        self.assertEqual(code, 10, err)
        self.assertIn("Open: does reset persist across sessions", out["station_result"]["readback"])

    def test_an_item_that_is_a_substring_of_the_existing_value_is_still_added(self):
        answer = bplib.extension_answer()
        answer["lines"][1]["text"] = "Python 3.9"
        answer["open_questions"] = ["unittest"]
        answer["assumptions"] = ["standard library"]
        path, after = self.extend_with(bplib.BUILD_FILLED, answer)
        line = next(l for l in after.split("\n") if l.startswith("Constraints:"))
        self.assertEqual(line, "Constraints: Python 3.9 standard library; `python3 -m unittest`. Python 3.9. "
                               "Assumed: standard library. Open: unittest.")

    def test_an_item_already_there_whole_is_not_repeated(self):
        answer = bplib.extension_answer()
        answer["lines"][1]["text"] = "`python3 -m unittest`"
        path, after = self.extend_with(bplib.BUILD_FILLED, answer)
        line = next(l for l in after.split("\n") if l.startswith("Constraints:"))
        self.assertEqual(line, "Constraints: Python 3.9 standard library; `python3 -m unittest`.")

    def test_items_carried_by_an_earlier_run_are_not_repeated(self):
        doc = bplib.BUILD_FILLED.replace(
            "Constraints: Python 3.9 standard library; `python3 -m unittest`.\n",
            "Constraints: Python 3.9 standard library. Assumed: one process per session. Open: does reset persist.\n")
        answer = bplib.extension_answer()
        answer["assumptions"] = ["one process per session"]
        answer["open_questions"] = ["does reset persist"]
        path, after = self.extend_with(doc, answer)
        line = next(l for l in after.split("\n") if l.startswith("Constraints:"))
        self.assertEqual(line, "Constraints: Python 3.9 standard library. Assumed: one process per session. "
                               "Open: does reset persist.")


class AStatusLineInAnyCase(_Write):
    """R4 (CL1-5): a re-cased or indented `Status:` line is protected as an exact one is, and a slice
    whose status is anything but `not started` (or that has no `Status:` line) is never revised."""

    def revise_a(self, doc):
        answer = bplib.extension_answer()
        answer["slices"][0]["name"] = "A"
        answer["slices"][0]["depends_on"] = []
        self.through_answer(bplib.base_files(build=doc), answer)
        path = os.path.join(self.ws, bplib.BUILD_PATH)
        before = testlib.sha256_file(path)
        code, out, err = self.run.write()
        self.assertEqual(testlib.sha256_file(path), before)
        return code, out, err

    def test_each_shape_is_refused_with_the_line_quoted(self):
        for status, quoted in (("status: built", "status: built"), (" Status: built", " Status: built"),
                               ("STATUS: in progress", "STATUS: in progress"),
                               ("  Status: not started", "  Status: not started"),
                               ("status: not started", "status: not started"),
                               (None, "slice A has no Status: line")):
            testlib.rmtree(self.tmp)
            os.makedirs(self.tmp)
            if status is None:
                doc = bplib.BUILD_FILLED.replace("Status: in progress\n", "")
            else:
                doc = bplib.BUILD_FILLED.replace("Status: in progress", status)
            code, out, err = self.revise_a(doc)
            self.assertEqual(code, 10, (status, err))
            self.assertEqual(out["stop_tag"], "write-refused", status)
            self.assertIn(quoted, out["reason"], status)
            self.assertTrue(out["wrote_nothing"], status)

    def test_a_re_cased_status_line_survives_an_extension_byte_for_byte(self):
        doc = bplib.BUILD_FILLED.replace("Status: in progress", "status: built")
        self.through_answer(bplib.base_files(build=doc), bplib.extension_answer())
        code, out, err = self.run.write()
        self.assertEqual(code, 0, (out, err))
        after = bplib.read(os.path.join(self.ws, bplib.BUILD_PATH))
        self.assertIn("\nstatus: built\n", after)
        self.assertEqual(buildoc.protected_changes(doc, after), [])

    def test_the_structure_reads_the_status_of_every_shape(self):
        for line, value in (("status: built", "built"), ("  Status: in progress", "in progress"),
                            ("Status: not started", "not started")):
            st = buildoc.structure(bplib.BUILD_FILLED.replace("Status: in progress", line))
            self.assertEqual((st["slices"][0]["status"], st["slices"][0]["status_line"]), (value, line))


class TheProtectedLines(unittest.TestCase):
    """Each protected-line change is caught by the comparison `write` runs before it writes."""

    def changes(self, after):
        return buildoc.protected_changes(bplib.BUILD_FILLED, after)

    def test_each_kind_of_change_is_named_with_the_line(self):
        doc = bplib.BUILD_FILLED
        cases = [
            doc.replace("Status: in progress", "Status: not started"),
            doc.replace("1 MAJOR", "0 MAJOR"),
            doc.replace("Plan: inspected 2026-09-23 by gpt-6-astra %s 0 BLOCKER %s 1 MAJOR %s 0 MINOR\n" % (M, M, M), ""),
            doc.replace("- The bench rig runs Python 3.9 (assumed at build).\n", ""),
            doc.replace("the reset is named nowhere else", "the reset is fine"),
            doc + "- a line appended to the punch list\n",
            doc.replace("## Slice A %s Count turns" % D, "## Slice Z %s Count turns" % D),
        ]
        for after in cases:
            found = self.changes(after)
            self.assertTrue(found, after)
            self.assertTrue(all(row.get("line") for row in found), found)
        self.assertEqual(self.changes(doc), [])


class NoBuildDoc(_Write):

    def test_needs_build_doc_false_writes_nothing_and_stops_no_build_doc(self):
        answer = bplib.clean_answer()
        answer["ceremony"] = {"needs_build_doc": False, "why": "a one-line change"}
        answer["slices"] = []
        run = self.through_answer(bplib.base_files(), answer)
        before = testlib.tree_digest(self.ws)
        code, out, err = run.write()
        self.assertEqual(code, 10, err)
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "no-build-doc"))
        self.assertIn("a one-line change", out["reason"])
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(before, testlib.tree_digest(self.ws))
        self.assertFalse(os.path.exists(self.harvest["target"]))


class ReportOnly(_Write):

    def test_a_new_doc_is_not_written_and_the_proposal_stays_in_the_run(self):
        run = self.through_answer(bplib.base_files(), bplib.clean_answer(), report_only=True)
        before = testlib.tree_digest(self.ws)
        code, out, err = run.write()
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(before, testlib.tree_digest(self.ws))
        self.assertFalse(os.path.exists(self.harvest["target"]))
        proposed = os.path.join(run.run_dir, "proposed-build-doc.md")
        self.assertEqual(templates.check("build-doc", bplib.read(proposed)), [])
        receipt = testlib.load_json(os.path.join(run.run_dir, "receipt.json"))
        self.assertEqual(receipt["writes"], [])
        self.assertEqual(receipt["would_write"]["path"], self.harvest["target"])

    def test_an_extension_is_not_written(self):
        run = self.through_answer(bplib.base_files(build=bplib.BUILD_FILLED), bplib.extension_answer(),
                                  report_only=True)
        before = testlib.tree_digest(self.ws)
        code, out, err = run.write()
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(before, testlib.tree_digest(self.ws))

    def test_every_phase_under_report_only_writes_only_in_the_run_directory(self):
        ws = testlib.git_workspace(self.tmp, "ws2", bplib.base_files(build=bplib.BUILD_FILLED))
        before = testlib.tree_digest(ws)
        run = bplib.Run(self.tmp, ws, report_only=True, name="run2")
        run.check_input()
        run.select_all()
        self.assertEqual(run.harvest()[0], 0)
        self.assertEqual(run.record(bplib.extension_answer())[0], 0)
        self.assertEqual(run.write()[0], 0)
        code, out, err = run.report()
        self.assertEqual(code, 10, err)
        self.assertEqual((out["status"], out["report_only"], out["wrote_nothing"]), ("completed", True, True))
        self.assertEqual(before, testlib.tree_digest(ws))
        for write in out["writes"]:
            self.assertEqual(write["kind"], "run_artifact", write)


class Phases(_Write):

    def test_write_before_an_answer_is_usage(self):
        ws = testlib.git_workspace(self.tmp, "ws3", bplib.base_files())
        run = bplib.Run(self.tmp, ws, name="run3")
        run.to_harvest()
        self.assertEqual(run.write()[0], 2)

    def test_write_twice_is_usage(self):
        run = self.through_answer(bplib.base_files(), bplib.clean_answer())
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.write()[0], 2)


if __name__ == "__main__":
    unittest.main()


class TheStructureEdges(unittest.TestCase):
    """Astra's shapes on the extension: a heading inside the body, a fence, CRLF, a second Status."""

    NOTES = bplib.BUILD_FILLED.replace(
        "Status: in progress\n\n", "Status: not started\n\n## Notes\n- a note written by hand\n\n")

    def blocks(self, name="B"):
        values = {"name": name, "short": "Reset", "goal": "g.", "requirements": ["R2 %s r" % D],
                  "criteria": [("AC2: c", "manual: look")], "footprint": "src/turnstile.py",
                  "not_in_slice": "n", "depends_on": "nothing", "status": "not started"}
        return values

    def test_a_foreign_heading_between_slices_survives_a_revision_and_an_append(self):
        for name in ("A", "B"):
            text = buildoc.extend(self.NOTES, [(name, buildoc.slice_block(self.blocks(name)))])
            self.assertIn("## Notes\n- a note written by hand\n", text, name)
            self.assertEqual(buildoc.protected_changes(self.NOTES, text), [], name)

    def test_a_fenced_slice_heading_is_not_a_slice(self):
        fenced = bplib.BUILD_FILLED.replace(
            "Status: in progress\n\n", "Status: in progress\n```\n## Slice Q %s quoted\nStatus: built\n```\n\n" % D)
        st = buildoc.structure(fenced)
        self.assertEqual([s["name"] for s in st["slices"]], ["A"])
        text = buildoc.extend(fenced, [("B", buildoc.slice_block(self.blocks()))])
        self.assertIn("```\n## Slice Q %s quoted\nStatus: built\n```\n" % D, text)
        self.assertLess(text.index("## Slice Q"), text.index("## Slice B"))

    def test_every_status_line_of_a_slice_is_protected(self):
        doubled = bplib.BUILD_FILLED.replace("Status: in progress\n", "Status: in progress\nStatus: built\n")
        dropped = doubled.replace("Status: built\n", "")
        self.assertTrue(buildoc.protected_changes(doubled, dropped))

    def test_a_crlf_doc_is_extended_in_crlf(self):
        crlf = bplib.BUILD_FILLED.replace("\n", "\r\n")
        text = buildoc.extend(crlf, [("B", buildoc.slice_block(self.blocks(), "\r\n"))],
                              out_of_scope=["a reverse mode %s later" % D])
        self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertEqual(buildoc.protected_changes(crlf, text), [])
        self.assertEqual(templates.check("build-doc", text), [])
