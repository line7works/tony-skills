"""blueprint-v2's `record-answer` (lane L, brief 3.4 and required test 5; reading CR-9).

The answer is held to `references/answer.schema.json` (exit 4), then to the shared refusals of
`station_core/answer.py` with `allowed` exactly `ledger`, `repo_path`, `question` (exit 5), then to
blueprint's own content checks (exit 5). On 4 and 5 nothing is written and the run stays where it
was, so a corrected answer can be recorded; the clean answer writes `answer.json`.
"""
import copy
import os
import unittest

import bplib
import testlib


class _Record(unittest.TestCase):

    files = None

    def setUp(self):
        self.tmp = testlib.make_scratch("bp-record-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = testlib.git_workspace(self.tmp, "ws", self.files or bplib.base_files(arch=True))
        self.run = bplib.Run(self.tmp, self.ws)
        self.run.to_harvest()
        self.ids = bplib.ledger_ids()

    def refused(self, answer, rule, code=5):
        before = self.run.listing()
        got, out, err = self.run.record(answer)
        self.assertEqual(got, code, (out, err))
        self.assertEqual(self.run.listing(), before, "nothing written")
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")))
        if code == 5:
            self.assertFalse(out["accepted"])
            self.assertIn(rule, [r["rule"] for r in out["refusals"]], out)
        return out

    def accepted(self, answer):
        got, out, err = self.run.record(answer)
        self.assertEqual(got, 0, (out, err))
        self.assertTrue(out["accepted"])
        self.assertEqual(testlib.load_json(os.path.join(self.run.run_dir, "answer.json")), answer)
        return out


class TheCleanAnswer(_Record):

    def test_accepted_and_written(self):
        out = self.accepted(bplib.clean_answer())
        self.assertEqual(out["next"], "write")
        cp = testlib.load_json(os.path.join(self.run.run_dir, "checkpoint.json"))
        self.assertEqual(cp["phase"], "answered")

    def test_a_second_answer_after_acceptance_is_usage(self):
        self.accepted(bplib.clean_answer())
        self.assertEqual(self.run.record(bplib.clean_answer())[0], 2)

    def test_a_refusal_leaves_the_run_to_take_a_corrected_answer(self):
        bad = bplib.clean_answer()
        del bad["lines"][0]["trace"]
        self.refused(bad, "untraced")
        self.accepted(bplib.clean_answer())


class SharedRefusals(_Record):
    """E14-11 through `station_core/answer.py`, with blueprint's three trace kinds."""

    def test_a_requirement_with_no_trace(self):
        doc = bplib.clean_answer()
        del doc["lines"][1]["trace"]
        self.refused(doc, "untraced")

    def test_a_repo_path_that_does_not_exist(self):
        doc = bplib.clean_answer()
        doc["lines"][0]["trace"] = {"kind": "repo_path", "ref": "src/reset.py"}
        self.refused(doc, "untraced")

    def test_a_repo_path_through_a_symlink_that_leaves_the_workspace(self):
        outside = os.path.join(self.tmp, "outside.py")
        testlib.write_text(outside, "x = 1\n")
        os.symlink(outside, os.path.join(self.ws, "src", "escape.py"))
        doc = bplib.clean_answer()
        doc["lines"][0]["trace"] = {"kind": "repo_path", "ref": "src/escape.py"}
        self.refused(doc, "untraced")

    def test_an_assumed_trace_is_not_allowed_here(self):
        doc = bplib.clean_answer()
        doc["lines"][0]["trace"] = {"kind": "assumed", "ref": "small and reversible"}
        out = self.refused(doc, "untraced")
        self.assertIn("not one this core allows", " ".join(r["message"] for r in out["refusals"]))

    def test_an_owner_words_trace_is_not_allowed_here(self):
        doc = bplib.clean_answer()
        doc["lines"][0]["trace"] = {"kind": "owner_words", "ref": "make it spin"}
        self.refused(doc, "untraced")

    def test_a_question_not_answered_in_this_run(self):
        doc = bplib.clean_answer()
        doc["questions"][0]["answer"] = ""
        self.refused(doc, "untraced")

    def test_a_question_that_re_asks_a_decided_line(self):
        doc = bplib.clean_answer()
        doc["questions"].append({"id": "Q2", "text": "Python or something else?",
                                 "touches": [self.ids["Python 3.9 standard library only"]], "answer": "Python"})
        self.refused(doc, "re-asked-decided")

    def test_a_question_that_repeats_decided_text_touching_nothing(self):
        doc = bplib.clean_answer()
        doc["questions"].append({"id": "Q2", "text": "python 3.9 standard  library only",
                                 "touches": [], "answer": "yes"})
        self.refused(doc, "re-asked-decided")

    def test_a_parked_line_quietly_resolved_as_a_requirement(self):
        doc = bplib.clean_answer()
        doc["questions"] = []
        doc["lines"][1]["trace"] = {"kind": "ledger", "ref": self.ids["Where the count is kept between sessions"]}
        self.refused(doc, "quietly-resolved")

    def test_an_open_line_quietly_resolved_as_a_requirement(self):
        doc = bplib.clean_answer()
        doc["lines"][1]["trace"] = {"kind": "ledger", "ref": self.ids["how often the counter resets"]}
        self.refused(doc, "quietly-resolved")

    def test_a_poured_concrete_line_re_asked(self):
        harvest = testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))
        poured = harvest["architecture"]["poured"][0]
        doc = bplib.clean_answer()
        doc["questions"].append({"id": "Q2", "text": "Which language?", "touches": [poured["id"]],
                                 "answer": "Python"})
        self.refused(doc, "re-asked-decided")

    def test_a_deferred_line_quietly_resolved(self):
        harvest = testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))
        deferred = harvest["architecture"]["deferred"][0]
        doc = bplib.clean_answer()
        doc["lines"][1]["trace"] = {"kind": "ledger", "ref": deferred["id"]}
        self.refused(doc, "quietly-resolved")

    def test_a_poured_line_passes_forward_by_its_id(self):
        harvest = testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))
        doc = bplib.clean_answer()
        doc["lines"][2]["trace"] = {"kind": "ledger", "ref": harvest["architecture"]["poured"][0]["id"]}
        self.accepted(doc)


class OwnRefusals(_Record):
    """Blueprint's own content checks (brief 3.4)."""

    def test_a_criterion_with_no_verify(self):
        doc = bplib.clean_answer()
        del doc["criteria"][0]["verify"]
        self.refused(doc, "criterion-without-verify")

    def test_a_criterion_with_a_blank_verify(self):
        doc = bplib.clean_answer()
        doc["criteria"][0]["verify"] = "   "
        self.refused(doc, "criterion-without-verify")

    def test_a_slice_naming_a_requirement_that_does_not_exist(self):
        doc = bplib.clean_answer()
        doc["slices"][0]["requirements"].append("R9")
        self.refused(doc, "unknown-id")

    def test_a_slice_naming_a_constraint_as_a_requirement(self):
        doc = bplib.clean_answer()
        doc["slices"][0]["requirements"].append("C1")
        self.refused(doc, "unknown-id")

    def test_a_slice_naming_a_criterion_that_does_not_exist(self):
        doc = bplib.clean_answer()
        doc["slices"][0]["criteria"].append("AC9")
        self.refused(doc, "unknown-id")

    def test_a_slice_depending_on_a_slice_that_does_not_exist(self):
        doc = bplib.clean_answer()
        doc["slices"][0]["depends_on"] = ["Z"]
        self.refused(doc, "unknown-id")

    def test_a_slice_depending_on_itself_or_a_later_slice(self):
        doc = bplib.clean_answer()
        second = copy.deepcopy(doc["slices"][0])
        second["name"] = "B"
        second["depends_on"] = []
        doc["slices"][0]["depends_on"] = ["B"]
        doc["slices"].append(second)
        self.refused(doc, "depends-forward")
        doc["slices"] = doc["slices"][:1]
        doc["slices"][0]["depends_on"] = ["A"]
        self.refused(doc, "depends-forward")

    def test_two_lines_sharing_an_id(self):
        doc = bplib.clean_answer()
        doc["lines"][1]["id"] = "R1"
        self.refused(doc, "duplicate-id")

    def test_two_slices_sharing_a_name(self):
        doc = bplib.clean_answer()
        doc["slices"].append(copy.deepcopy(doc["slices"][0]))
        self.refused(doc, "duplicate-id")

    def test_a_requirement_no_slice_carries(self):
        doc = bplib.clean_answer()
        doc["slices"][0]["requirements"] = ["R1"]
        self.refused(doc, "unplaced")

    def test_needs_build_doc_false_with_slices(self):
        doc = bplib.clean_answer()
        doc["ceremony"] = {"needs_build_doc": False, "why": "a one-line change"}
        self.refused(doc, "slices-without-build-doc")

    def test_needs_build_doc_true_with_no_slice(self):
        doc = bplib.clean_answer()
        doc["slices"] = []
        self.refused(doc, "no-slice")

    def test_needs_build_doc_false_with_no_slices_is_accepted(self):
        doc = bplib.clean_answer()
        doc["ceremony"] = {"needs_build_doc": False, "why": "a one-line change"}
        doc["slices"] = []
        self.accepted(doc)

    def test_a_feature_other_than_the_build_hunts_name(self):
        doc = bplib.clean_answer(feature="counter")
        self.refused(doc, "feature-not-hunted")

    def test_a_session_other_than_the_inputs(self):
        doc = bplib.clean_answer(session="another-session")
        self.refused(doc, "session-mismatch")

    def test_a_run_id_other_than_the_runs(self):
        doc = bplib.clean_answer(run_id="run-9999")
        self.refused(doc, "run-id-mismatch")

    def test_every_refusal_is_listed_at_once(self):
        doc = bplib.clean_answer()
        del doc["criteria"][0]["verify"]
        del doc["lines"][1]["trace"]
        out = self.refused(doc, "untraced")
        self.assertIn("criterion-without-verify", [r["rule"] for r in out["refusals"]])


class SchemaRefusals(_Record):

    def test_a_field_of_the_wrong_type_is_exit_4(self):
        for mutate in (lambda d: d.update(questions="none"),
                       lambda d: d["lines"][0].update(trace={"kind": "ledger", "ref": 7}),
                       lambda d: d["lines"][0].update(tag="decided"),
                       lambda d: d["lines"][0].update(trace={"kind": "vibes", "ref": "x"}),
                       lambda d: d.update(extra=True),
                       lambda d: d["slices"][0].update(goal="two\nlines"),
                       lambda d: d["slices"][0].update(goal="   "),
                       lambda d: d.update(answer_version=2)):
            doc = bplib.clean_answer()
            mutate(doc)
            got, out, err = self.run.record(doc)
            self.assertEqual(got, 4, (out, err))
            self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")))

    def test_a_file_that_is_not_json_is_usage(self):
        path = os.path.join(self.tmp, "bad.json")
        testlib.write_text(path, "not json")
        got, out, err = self.run.cli(["record-answer", "--run-dir", self.run.run_dir, "--answer", path])
        self.assertEqual(got, 2)

    def test_record_before_harvest_is_usage(self):
        run = bplib.Run(self.tmp, self.ws, run_id="run-0002", name="run2")
        run.check_input()
        run.select_all()
        self.assertEqual(run.record(bplib.clean_answer(run_id="run-0002"))[0], 2)


if __name__ == "__main__":
    unittest.main()
