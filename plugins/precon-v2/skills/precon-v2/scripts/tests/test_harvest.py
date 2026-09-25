"""precon-v2's `harvest` phase (precon-v2-contract.md section 3; required test 3 of lane P), through the real CLI.

No doc, one doc, a doc carrying the triage comment, a doc with an untaggable line
(`ledger-refused`, quoted), a heading inside a ledger section, a doc off the form
(`form-refused`), a slug found in two homes (`selection-several`), and the usage slips.
"""
import json
import os
import unittest

import preconlib
import testlib
from preconlib import D


class _Harvest(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("harvest-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)

    def result(self, run):
        return testlib.load_json(run.run_file("result.json"))

    def assert_valid_result(self, run):
        code, out, err = testlib.run_script("validate-result.py", [run.run_file("result.json")], cwd=self.fx.cwd)
        self.assertEqual(code, 0, out + err)


class NoDoc(_Harvest):

    def test_no_doc_names_where_a_new_doc_would_go(self):
        before = testlib.tree_digest(self.fx.ws)
        run = self.fx.new_run()
        self.assertEqual(run.select()["outcome"], "none")
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["next"], "record-answer")
        self.assertIsNone(doc["doc"])
        self.assertEqual(doc["idea"], "turnstile")
        self.assertEqual(doc["date"], preconlib.DATE)
        self.assertEqual(doc["new_doc"], os.path.join(self.fx.ws, "docs", "scope", "2026-09-20-turnstile.md"))
        self.assertEqual(doc["counts"], {"decided": 0, "assumed": 0, "parked": 0, "open": 0, "out-of-scope": 0,
                                         "research": 0})
        self.assertEqual(doc["board"], "decided 0 · assumed 0 · parked 0 · open your-calls 0")
        self.assertEqual(doc["ledger"], [])
        self.assertTrue(os.path.isfile(run.run_file("harvest.json")))
        self.assertEqual(testlib.tree_digest(self.fx.ws), before, "harvest writes nothing in the workspace")

    def test_the_staging_home_names_the_staged_path(self):
        run = self.fx.new_run(station={"home": "staging"})
        run.select()
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["new_doc"], os.path.join(self.fx.staging, "turnstile-scope.md"))
        self.assertEqual(doc["home"], "staging")

    def test_the_staging_home_without_a_staging_input_is_refused_at_check_input(self):
        path = os.path.join(self.tmp, "in.json")
        doc = testlib.make_input(self.fx.ws, os.path.join(self.tmp, "runs", "x"), station={"home": "staging"})
        testlib.write_json(path, doc)
        code, out, err = self.fx.cli(["check-input", path])
        self.assertEqual(code, 4, out + err)


class Containment(_Harvest):

    def test_a_docs_folder_that_resolves_outside_the_workspace_is_refused(self):
        outside = os.path.join(self.tmp, "outside")
        os.makedirs(os.path.join(outside, "scope"))
        os.symlink(outside, os.path.join(self.fx.ws, "docs"))
        run = self.fx.new_run()
        self.assertEqual(run.select()["outcome"], "none")
        code, doc, err = run.harvest()
        self.assertEqual(code, 2, err)
        self.assertIn("outside", err)
        self.assertEqual(os.listdir(os.path.join(outside, "scope")), [])


class OneDoc(_Harvest):

    def test_the_ledger_the_counts_the_board_and_the_header(self):
        preconlib.ensure_scope_doc(self.fx)
        run = self.fx.new_run()
        self.assertEqual(run.select()["outcome"], "one")
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["doc"]["path"], os.path.join(self.fx.ws, preconlib.SCOPE_REL))
        self.assertEqual(doc["doc"]["home"], "repo")
        self.assertEqual(doc["doc"]["title"], "Turnstile")
        self.assertEqual(doc["doc"]["date"], "2026-09-20")
        self.assertTrue(doc["doc"]["intent"].startswith("a small turn counter"))
        self.assertIsNone(doc["doc"]["tier"])
        self.assertEqual(doc["doc"]["sha256"], testlib.sha256_file(doc["doc"]["path"]))
        self.assertEqual(doc["counts"], {"decided": 1, "assumed": 1, "parked": 2, "open": 1, "out-of-scope": 1,
                                         "research": 0})
        self.assertEqual(doc["board"], "decided 1 · assumed 1 · parked 2 · open your-calls 1")
        ids = sorted(row["id"] for row in doc["ledger"])
        self.assertEqual(ids, sorted(preconlib.ids().values()))
        self.assertEqual(testlib.load_json(run.run_file("harvest.json"))["ledger"], doc["ledger"])

    def test_the_triage_comment_is_read(self):
        text = preconlib.SCOPE_DOC.replace("(2026-09-20)\n", "(2026-09-20)\n<!-- precon-v2 triage: architectural -->\n", 1)
        preconlib.ensure_scope_doc(self.fx, text=text)
        run = self.fx.new_run()
        run.select()
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["doc"]["tier"], "architectural")

    def test_a_flat_and_a_staged_doc_are_harvested_where_they_are(self):
        preconlib.ensure_scope_doc(self.fx, staged=True, rel="turnstile-scope.md")
        run = self.fx.new_run()
        run.select()
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["doc"]["home"], "staging")


class Refused(_Harvest):

    def stop(self, text):
        preconlib.ensure_scope_doc(self.fx, text=text)
        run = self.fx.new_run()
        run.select()
        before = testlib.tree_digest(self.fx.ws)
        code, doc, err = run.harvest()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "stopped")
        self.assertEqual(testlib.tree_digest(self.fx.ws), before)
        self.assert_valid_result(run)
        self.assertEqual(self.result(run), doc)
        return run, doc

    def test_an_untaggable_line_is_ledger_refused_and_quoted(self):
        text = preconlib.SCOPE_DOC.replace("parked: needs research", "parked: later")
        run, doc = self.stop(text)
        self.assertEqual(doc["stop_tag"], "ledger-refused")
        self.assertIn("line 7", doc["reason"])
        self.assertIn("- Where the count is kept between sessions %s parked: later" % D, doc["reason"])
        refused = doc["station_result"]["ledger_refused"]
        self.assertEqual([row["line"] for row in refused], [7])

    def test_a_heading_inside_the_decisions_block_is_ledger_refused(self):
        text = preconlib.SCOPE_DOC.replace("Decisions:\n", "Decisions:\n### a note\n", 1)
        run, doc = self.stop(text)
        self.assertEqual(doc["stop_tag"], "ledger-refused")
        self.assertIn("### a note", doc["reason"])

    def test_a_doc_off_the_form_is_form_refused(self):
        text = preconlib.SCOPE_DOC.replace("Research:\n", "")
        run, doc = self.stop(text)
        self.assertEqual(doc["stop_tag"], "form-refused")
        self.assertIn("Research:", doc["reason"])

    def test_a_slug_in_two_homes_is_listed_never_picked(self):
        preconlib.ensure_scope_doc(self.fx)
        preconlib.ensure_scope_doc(self.fx, staged=True, rel="turnstile-scope.md")
        run = self.fx.new_run()
        self.assertEqual(run.select()["outcome"], "several")
        code, doc, err = run.harvest()
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["stop_tag"], "selection-several")
        paths = sorted(c["path"] for c in doc["station_result"]["candidates"])
        self.assertEqual(paths, sorted([os.path.join(self.fx.ws, preconlib.SCOPE_REL),
                                        os.path.join(self.fx.staging, "turnstile-scope.md")]))
        self.assertIsNone(doc["station_result"].get("doc"))
        self.assert_valid_result(run)

    def test_a_command_after_the_stop_reports_the_recorded_outcome(self):
        text = preconlib.SCOPE_DOC.replace("parked: needs research", "parked: later")
        run, doc = self.stop(text)
        digest = testlib.sha256_file(run.run_file("result.json"))
        code, again, err = run.harvest()
        self.assertEqual((code, again), (10, doc))
        code, again, err = run.report()
        self.assertEqual((code, again), (10, doc))
        self.assertEqual(testlib.sha256_file(run.run_file("result.json")), digest)


class Usage(_Harvest):

    def test_harvest_before_select_is_usage(self):
        run = self.fx.new_run()
        code, doc, err = run.harvest()
        self.assertEqual(code, 2, err)
        self.assertIn("select", err)

    def test_a_scope_hunt_without_a_name_is_usage(self):
        run = self.fx.new_run()
        run.select(name=None)
        code, doc, err = run.harvest()
        self.assertEqual(code, 2, err)
        self.assertIn("--name", err)

    def test_harvest_after_an_answer_is_usage(self):
        run = self.fx.new_run()
        run.select()
        self.assertEqual(run.harvest()[0], 0)
        code, doc, err = run.record(preconlib.answer(run))
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertEqual(run.harvest()[0], 2)


class ReportOnly(_Harvest):

    def test_report_only_harvest_writes_only_in_the_run_directory(self):
        preconlib.ensure_scope_doc(self.fx)
        before = (testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging))
        run = self.fx.new_run(report_only=True)
        run.select()
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertTrue(doc["report_only"])
        self.assertEqual((testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging)), before)


if __name__ == "__main__":
    unittest.main()
