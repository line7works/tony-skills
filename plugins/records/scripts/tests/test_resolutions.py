"""Resolutions (contract section 11.5): a file that fixes each ambiguous case, and the rejections.

One resolutions file answers every ambiguous case the join fixtures hold, one answer shape at a
time, and the import then lands. The four rejected-resolution cases are the ones section 11.5
and the answer shapes admit:

    raw_changed          the answer records the line as it was; the line now reads otherwise
    unknown_finding      the answer names a finding the document does not raise
    line_not_asked       the answer names a line the import did not stop on
    answer_does_not_fit  the answer's shape cannot resolve that question

Each rejection is exit 4, with nothing written and no lock left behind.
"""
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import events as events_mod  # noqa: E402

PLANS = "docs/plans/"
SHARED = PLANS + "2026-05-03-join-ambiguous-shared.md"
GRANTS = PLANS + "2026-05-05-grants.md"
NOTHING = PLANS + "2026-05-03-join-ambiguous-nothing.md"
OTHER_SLICE = PLANS + "2026-05-03-join-ambiguous-other-slice.md"
D1 = PLANS + "2026-05-01-d1-one-identity.md"


class ResolutionCase(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-resolutions-")
        self.workspace = testlib.fixture_workspace(self.scratch)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def stops(self, doc):
        code, body, err = testlib.run_json(
            ["import-legacy", "--workspace", self.workspace, "--doc", doc, "--dry-run"])
        self.assertEqual(code, 5, "%s did not stop: %s %s" % (doc, body, err))
        return body["ambiguities"]

    def answers_file(self, name, answers, answered_by="the owner", answered_on="2026-05-21",
                     **extra):
        body = {"answered_by": answered_by, "answered_on": answered_on, "answers": answers}
        body.update(extra)
        return testlib.write_json(os.path.join(self.scratch, name), body)

    def run_import(self, doc, resolutions=None, dry_run=False):
        args = ["import-legacy", "--workspace", self.workspace, "--doc", doc]
        if resolutions:
            args += ["--resolutions", resolutions]
        if dry_run:
            args.append("--dry-run")
        return testlib.run_json(args)

    def log_bytes(self, doc):
        path = events_mod.log_path(self.workspace, doc)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()


class AnAnswerFixesEachAmbiguousCase(ResolutionCase):
    def test_a_finding_answer_joins_a_shared_location(self):
        stop = self.stops(SHARED)[0]
        chosen = stop["candidates"][0]["finding"]
        path = self.answers_file("shared.json", [
            {"line": stop["line"], "raw": stop["raw"], "finding": chosen}])
        code, body, err = self.run_import(SHARED, path)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        kinds = [row["kind"] for row in body["appended"]]
        self.assertEqual(kinds.count("resolution_applied"), 1)
        self.assertEqual(kinds.count("disposition"), 1)
        events = testlib.events_of(self.workspace, SHARED)
        applied = [e for e in events if e["kind"] == "resolution_applied"][0]
        cleared = [e for e in events if e["kind"] == "disposition"][0]
        self.assertEqual(applied["seq"] + 1, cleared["seq"],
                         "the answer is recorded before the event it enables")
        self.assertEqual(applied["answer"], {"finding": chosen})
        self.assertEqual(applied["answered_by"], "the owner")
        self.assertEqual(applied["answered_on"], "2026-05-21")
        self.assertEqual(applied["at"], "2026-05-21")
        self.assertEqual(cleared["finding"], chosen)
        self.assertIsNone(cleared["join_basis"], "a person decided it, not one of 11.4's rules")

    def test_a_new_finding_answer_raises_the_line_as_its_own_finding(self):
        stop = self.stops(NOTHING)[0]
        path = self.answers_file("nothing.json", [
            {"line": stop["line"], "raw": stop["raw"], "new_finding": True}])
        code, body, err = self.run_import(NOTHING, path)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        events = testlib.events_of(self.workspace, NOTHING)
        raised = [e for e in events if e["kind"] == "finding_raised"]
        self.assertEqual(len(raised), 2)
        new = raised[-1]
        self.assertEqual(new["severity"], "MINOR")
        self.assertEqual(new["location"]["line"], 90)
        self.assertEqual(new["claim"], "the floor mat curls at the edge")
        cleared = [e for e in events if e["kind"] == "disposition"][0]
        self.assertEqual(cleared["finding"], new["finding"])
        self.assertEqual(new["origin"]["line"], stop["line"],
                         "the raise and the clear come from one legacy line")

    def test_a_skip_answer_records_the_line_as_unparsed_with_its_reason(self):
        stop = self.stops(OTHER_SLICE)[0]
        path = self.answers_file("other.json", [
            {"line": stop["line"], "raw": stop["raw"], "skip": True,
             "why": "the gate finding belongs to Slice A, and Slice B never touched it"}])
        code, body, err = self.run_import(OTHER_SLICE, path)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        events = testlib.events_of(self.workspace, OTHER_SLICE)
        unparsed = [e for e in events if e["kind"] == "legacy_unparsed"]
        self.assertEqual(len(unparsed), 1)
        self.assertEqual(unparsed[0]["reason"],
                         "the gate finding belongs to Slice A, and Slice B never touched it")
        self.assertEqual([e["kind"] for e in events if e["kind"] == "disposition"], [])

    def test_a_skip_answer_settles_a_second_raise_of_one_identity(self):
        """The D1 family: `skip` is the answer an identity collision takes (section 7)."""
        stop = self.stops(D1)[0]
        path = self.answers_file("d1.json", [
            {"line": stop["line"], "raw": stop["raw"], "skip": True,
             "why": "one finding, written twice by two reviewers in one block"}])
        code, body, err = self.run_import(D1, path)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        events = testlib.events_of(self.workspace, D1)
        self.assertEqual(len([e for e in events if e["kind"] == "finding_raised"]), 1)
        self.assertEqual(len([e for e in events if e["kind"] == "legacy_unparsed"]), 1)

    def test_a_resolved_import_still_verifies_and_leaves_the_document_untouched(self):
        before = testlib.doc_sha256(self.workspace, SHARED)
        stop = self.stops(SHARED)[0]
        path = self.answers_file("shared.json", [
            {"line": stop["line"], "raw": stop["raw"], "finding": stop["candidates"][0]["finding"]}])
        code, _, _ = self.run_import(SHARED, path)
        self.assertEqual(code, 0)
        self.assertEqual(testlib.doc_sha256(self.workspace, SHARED), before)
        code, body, err = testlib.run_json(
            ["verify", "--workspace", self.workspace, "--doc", SHARED])
        self.assertEqual(code, 0, err)
        self.assertTrue(body["ok"])
        self.assertEqual(testlib.porcelain(self.workspace), ["?? docs/records/"])

    def test_a_resolutions_file_may_name_the_document_it_answers(self):
        stop = self.stops(NOTHING)[0]
        path = self.answers_file("named.json",
                                 [{"line": stop["line"], "raw": stop["raw"], "new_finding": True}],
                                 doc=NOTHING)
        code, _, err = self.run_import(NOTHING, path)
        self.assertEqual(code, 0, err)

    def test_a_resolutions_file_for_another_document_is_refused(self):
        stop = self.stops(NOTHING)[0]
        path = self.answers_file("wrong-doc.json",
                                 [{"line": stop["line"], "raw": stop["raw"], "new_finding": True}],
                                 doc=SHARED)
        code, body, _ = self.run_import(NOTHING, path)
        self.assertEqual(code, 4)
        self.assertIn("answers", body["reason"])
        self.assertIsNone(self.log_bytes(NOTHING))


class TheFourRejectedResolutions(ResolutionCase):
    def reject(self, doc, answers, why):
        path = self.answers_file("answers.json", answers)
        code, body, err = self.run_import(doc, path)
        self.assertEqual(code, 4, "%s %s" % (body, err))
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "invalid")
        self.assertEqual([r["why"] for r in body["rejected_resolutions"]], [why])
        self.assertIsNone(self.log_bytes(doc), "a rejected resolutions file writes nothing")
        self.assertFalse(os.path.exists(events_mod.log_path(self.workspace, doc) + ".lock"))
        return body["rejected_resolutions"][0]

    def test_1_a_line_whose_raw_text_has_changed(self):
        stop = self.stops(SHARED)[0]
        row = self.reject(SHARED, [{"line": stop["line"], "raw": stop["raw"] + " (edited)",
                                    "finding": stop["candidates"][0]["finding"]}], "raw_changed")
        self.assertIn("the answer records the line as", row["reason"])
        self.assertIn("it now reads", row["reason"])

    def test_2_a_finding_the_document_does_not_raise(self):
        stop = self.stops(SHARED)[0]
        row = self.reject(SHARED, [{"line": stop["line"], "raw": stop["raw"],
                                    "finding": "f1:" + "0" * 20}], "unknown_finding")
        self.assertIn("this document raises no such finding", row["reason"])

    def test_3_a_line_the_import_did_not_stop_on(self):
        stop = self.stops(SHARED)[0]
        row = self.reject(SHARED, [{"line": stop["line"], "raw": stop["raw"],
                                    "finding": stop["candidates"][0]["finding"]},
                                   {"line": 1, "raw": "# Crate packer, an ambiguous join: a shared location",
                                    "skip": True, "why": "the title is not a record"}],
                          "line_not_asked")
        self.assertIn("is not a line this import stopped on", row["reason"])

    def test_4b_a_reopening_line_cannot_raise_a_finding_of_its_own(self):
        """It carries no severity (Appendix A), so `new_finding` has nothing to raise."""
        path = os.path.join(self.workspace, *GRANTS.split("/"))
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace("src/night.py:26 · (the shift log is written at dawn) · \"the "
                                  "dawn write came back\"",
                                  "src/night.py:404 · (a claim nothing holds) · \"it came back\""))
        stop = self.stops(GRANTS)[0]
        row = self.reject(GRANTS, [{"line": stop["line"], "raw": stop["raw"],
                                    "new_finding": True}], "answer_does_not_fit")
        self.assertIn("takes finding or skip", row["reason"])
        self.assertIn("A reopening line carries no severity", row["reason"])
        self.assertIn("name the finding it reopens, or skip it", row["reason"])

    def test_4c_a_skip_answers_that_reopening_line(self):
        path = os.path.join(self.workspace, *GRANTS.split("/"))
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace("src/night.py:26 · (the shift log is written at dawn) · \"the "
                                  "dawn write came back\"",
                                  "src/night.py:404 · (a claim nothing holds) · \"it came back\""))
        stop = self.stops(GRANTS)[0]
        answers = self.answers_file("reopen.json", [
            {"line": stop["line"], "raw": stop["raw"], "skip": True,
             "why": "the reopening names a location this document never raised"}])
        code, body, err = self.run_import(GRANTS, answers)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        kinds = [row["kind"] for row in body["appended"]]
        self.assertEqual(kinds.count("legacy_unparsed"), 1)
        self.assertEqual(kinds.count("reopened"), 0)

    def test_4_an_answer_whose_shape_the_question_cannot_take(self):
        """A second raise of one identity takes `skip`; there is no other finding to join to."""
        stop = self.stops(D1)[0]
        row = self.reject(D1, [{"line": stop["line"], "raw": stop["raw"],
                                "new_finding": True}], "answer_does_not_fit")
        self.assertIn("takes skip", row["reason"])
        self.assertIn("the answer is 'new_finding'", row["reason"])

    def test_a_rejection_carries_the_answer_it_refused(self):
        stop = self.stops(SHARED)[0]
        row = self.reject(SHARED, [{"line": stop["line"], "raw": "not what the line says",
                                    "new_finding": True}], "raw_changed")
        self.assertEqual(row["answer"]["raw"], "not what the line says")
        self.assertEqual(row["line"], stop["line"])

    def test_a_rejection_happens_before_the_ambiguity_report(self):
        """A file that answers one line and misfires on another is rejected, not partly applied."""
        stops = self.stops(SHARED)
        path = self.answers_file("answers.json", [
            {"line": stops[0]["line"], "raw": stops[0]["raw"], "finding": "f1:" + "1" * 20}])
        code, body, _ = self.run_import(SHARED, path)
        self.assertEqual(code, 4)
        self.assertEqual(body["error"], "invalid")


class TheResolutionsFileItself(ResolutionCase):
    def test_a_file_that_fails_the_schema_is_exit_four_and_writes_nothing(self):
        path = testlib.write_json(os.path.join(self.scratch, "bad.json"),
                                  {"answered_by": "the owner", "answers": []})
        code, body, _ = self.run_import(SHARED, path)
        self.assertEqual(code, 4)
        self.assertIn("resolutions.schema.json", body["reason"])
        self.assertTrue(body["errors"])
        self.assertIsNone(self.log_bytes(SHARED))

    def test_an_answer_with_two_shapes_is_refused_by_the_schema(self):
        stop = self.stops(SHARED)[0]
        path = self.answers_file("two.json", [
            {"line": stop["line"], "raw": stop["raw"], "new_finding": True, "skip": True,
             "why": "both"}])
        code, body, _ = self.run_import(SHARED, path)
        self.assertEqual(code, 4)
        self.assertIn("resolutions.schema.json", body["reason"])

    def test_a_missing_file_is_a_usage_error(self):
        code, out, err = testlib.run_cli(
            ["import-legacy", "--workspace", self.workspace, "--doc", SHARED,
             "--resolutions", os.path.join(self.scratch, "absent.json")])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--resolutions", err)

    def test_the_shipped_examples_are_the_shape_the_importer_reads(self):
        from records_core import validate
        base = os.path.join(testlib.REFERENCES, "examples", "resolutions", "valid")
        schemas = testlib.schemas()
        names = sorted(os.listdir(base))
        self.assertTrue(names)
        for name in names:
            with open(os.path.join(base, name), encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertEqual(validate.validate_document("resolutions", doc, schemas), [], name)


if __name__ == "__main__":
    unittest.main()
