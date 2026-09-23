"""What the core decides, and what it refuses to decide.

Scope adherence, honest failure handling, the refused answer, report-only, the open BLOCKER, the
importer signal, and the rerun of a named check. The seeded cases exercise these too, but only
the control room knows what each case should produce; these tests fix the RULES against
workspaces this lane built itself, so a rule that changed would fail here with a name.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from build_core import answer as answermod, checks as checksmod, doc as docmod, scope  # noqa: E402


class _Run(unittest.TestCase):

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-decide-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")

    def run_all(self, answer=None, **extra):
        """Every phase in order; returns (exit code, the parsed result or None)."""
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.ws, **extra))
        answer_path = os.path.join(self.scratch, "answer.json")
        testlib.write_json(answer_path, answer or testlib.ANSWER)
        last = None
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", answer_path],
                     ["report", "--run-dir", self.run_dir]):
            code, out, err = testlib.run_build(args)
            last = (code, out, err)
            if code != 0:
                break
        result_path = os.path.join(self.run_dir, "result.json")
        result = testlib.load_json(result_path) if os.path.isfile(result_path) else None
        return last, result

    def status_line(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), encoding="utf-8") as fh:
            for line in fh.read().split("\n"):
                if line.startswith("Status:"):
                    return line[len("Status:"):].strip()
        return None


class ScopeAdherence(_Run):
    """A path outside the slice's named paths is reported with its stated reason, or the run stops."""

    def test_a_path_the_slice_names_is_not_out_of_scope(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.commit_work(self.ws)
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["out_of_scope"], [])
        self.assertEqual(result["status"], "completed")

    def test_a_path_outside_them_is_listed_with_the_executors_stated_reason(self):
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 9\n")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["edits"].append({"path": "src/other.py",
                                "reason": "the neighbouring module was adjusted while reading it"})
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual([row["path"] for row in result["out_of_scope"]], ["src/other.py"])
        row = result["out_of_scope"][0]
        self.assertTrue(row["reason_given"])
        self.assertEqual(row["reason"], "the neighbouring module was adjusted while reading it")
        self.assertEqual(row["lists"], ["changed"])
        self.assertTrue(row["named_in_not_in_slice"], "the slice states this path as a boundary")
        self.assertEqual(result["status"], "completed", "a stated reason does not stop the run")

    def test_a_path_outside_them_with_no_reason_stops_the_run(self):
        testlib.write_text(os.path.join(self.ws, "src", "stray.py"), "X = 1\n")
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "scope_unexplained")
        self.assertIn("src/stray.py", result["stop_reason"])
        self.assertIn("never passed over in silence", result["stop_reason"])
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(self.status_line(), "not started")

    def test_all_three_lists_are_compared_against_the_named_paths(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.write_text(os.path.join(self.ws, "src", "a.py"), "A = 1\n")
        testlib.commit_work(self.ws)
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 2\n")
        testlib.write_text(os.path.join(self.ws, "src", "b.py"), "B = 1\n")
        answer = json.loads(json.dumps(testlib.ANSWER))
        for path in ("src/a.py", "src/other.py", "src/b.py"):
            answer["edits"].append({"path": path, "reason": "reason for %s" % path})
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual([row["path"] for row in result["out_of_scope"]],
                         ["src/a.py", "src/b.py", "src/other.py"])
        self.assertEqual([row["lists"] for row in result["out_of_scope"]],
                         [["committed"], ["untracked"], ["changed"]])

    def test_a_directory_named_with_a_trailing_slash_covers_what_is_under_it(self):
        self.assertTrue(docmod.in_named_paths("checks/unit.sh", ["checks/"]))
        self.assertTrue(docmod.in_named_paths("checks/unit.sh", ["checks"]))
        self.assertFalse(docmod.in_named_paths("checksum.txt", ["checks"]),
                         "a shared prefix of a file name is not a directory relationship")
        self.assertFalse(docmod.in_named_paths("src/a.py", ["src/a"]))


class HonestFailure(_Run):
    """A failing or skipped check is reported with its output; the card does not move; and the
    run is a COMPLETION with a named result, not a stop (amendment A3 item 1)."""

    def _answer_with(self, result_value, output, exit_code):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["claimed_status"] = "partial"
        answer["claimed_card"] = "not started"
        answer["checks"][0].update(result=result_value, output=output, exit_code=exit_code)
        return answer

    def test_a_failing_check_is_a_named_completion_and_the_card_stays(self):
        (code, _, err), result = self.run_all(
            answer=self._answer_with("failing", "FAILED (failures=1)", 1))
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertEqual(result["terminal_status"], "completion")
        self.assertIsNone(result["stop_reason"])
        self.assertEqual(result["checks"][0]["result"], "failing")
        self.assertEqual(result["checks"][0]["output"], "FAILED (failures=1)")
        self.assertEqual(result["checks"][0]["exit_code"], 1)
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(result["card"]["after"], "not started")
        self.assertEqual(self.status_line(), "not started")
        self.assertEqual(result["records"]["appended"], [])

    def test_a_check_that_could_not_run_is_reported_as_skipped_with_its_output(self):
        (code, _, err), result = self.run_all(
            answer=self._answer_with("not_run", "the fixture directory is not on this machine", 127))
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertEqual(result["checks"][0]["result"], "not_run")
        self.assertIn("not on this machine", result["checks"][0]["output"])
        self.assertFalse(result["card"]["moved"])

    def test_a_check_the_slice_names_that_the_answer_never_reports_is_not_run(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"] = []
        answer["claimed_status"] = "partial"
        answer["claimed_card"] = "not started"
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["checks"][0]["name"], "unit")
        self.assertEqual(result["checks"][0]["result"], "not_run")
        self.assertEqual(result["status"], "checks_not_passed")

    def test_a_check_the_slice_does_not_name_is_carried_but_never_gates_the_card(self):
        """`checks_not_passed` is decided over the checks the SLICE names, and no others."""
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["claimed_status"] = "partial"
        answer["claimed_card"] = "not started"
        answer["checks"].append({"name": "lint", "command": "sh checks/lint.sh",
                                 "result": "failing", "exit_code": 1, "output": "3 warnings"})
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        rows = dict((row["name"], row) for row in result["checks"])
        self.assertFalse(rows["lint"]["named_by_slice"])
        self.assertEqual(rows["lint"]["result"], "failing")
        self.assertEqual(rows["lint"]["output"], "3 warnings")
        self.assertEqual(result["status"], "not_complete",
                         "the unnamed failing check did not make this `checks_not_passed`")

    def test_a_complete_claim_over_any_failing_check_of_its_own_is_refused(self):
        """The refusal rule reads the answer's OWN list, named by the slice or not: an answer
        that calls itself finished while reporting a check of its own as failing contradicts
        itself, and the contradiction is the executor's to resolve."""
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"].append({"name": "lint", "command": "sh checks/lint.sh",
                                 "result": "failing", "exit_code": 1, "output": "3 warnings"})
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused")
        self.assertIn("lint failing", result["answer"]["refusals"][0])
        self.assertFalse(result["card"]["moved"])

    def test_an_answer_that_claims_partial_does_not_move_the_card_even_with_every_check_green(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["claimed_status"] = "partial"
        answer["claimed_card"] = "not started"
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "not_complete")
        self.assertEqual(result["terminal_status"], "completion")
        self.assertFalse(result["card"]["moved"])


class ARefusedAnswer(_Run):
    """Not acted on, not repaired, said plainly. A STOP, and the card does not move.

    The control room reversed itself on this during the lane's first check round: a refused
    answer is a stop, not a completion. Amendment A3 item 1's named completion covers FAILING
    CHECKS only. A run whose answer cannot be recorded has nothing it may record, so the tool
    could not proceed; it still reports everything it computed.
    """

    def test_complete_and_built_over_a_failing_check_is_refused(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(result="failing", exit_code=1, output="FAILED (failures=1)")
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused")
        self.assertEqual(result["terminal_status"], "stop")
        self.assertTrue(result["stop_reason"])
        self.assertEqual(result["refusal_reason"], "answer_invalid")
        self.assertFalse(result["answer"]["accepted"])
        self.assertIn("unit failing", result["answer"]["refusals"][0])
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(self.status_line(), "not started")
        self.assertEqual(result["records"]["appended"], [])
        # it is not repaired: the answer is reported exactly as it was recorded
        self.assertEqual(result["answer"]["claimed_status"], "complete")
        self.assertEqual(result["answer"]["claimed_card"], "built")
        # and the run still reports everything it computed
        self.assertIn("source_set", result)
        self.assertTrue(result["checks"])

    def test_a_card_value_outside_the_vocabulary_is_refused(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["claimed_card"] = "nearly done"
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused")
        self.assertEqual(result["terminal_status"], "stop")
        self.assertIn("nearly done", result["answer"]["refusals"][0])

    def test_an_answer_recorded_for_another_case_is_refused(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["case"] = "some-other-case"
        (code, _, err), result = self.run_all(answer=answer, case="this-case")
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused")
        self.assertEqual(result["terminal_status"], "stop")
        self.assertIn("some-other-case", result["answer"]["refusals"][0])

    def test_the_refusal_is_said_at_record_answer_too(self):
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.ws))
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(result="failing", exit_code=1, output="FAILED")
        answer_path = os.path.join(self.scratch, "answer.json")
        testlib.write_json(answer_path, answer)
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir]):
            self.assertEqual(testlib.run_build(args)[0], 0)
        code, out, err = testlib.run_build(["record-answer", "--run-dir", self.run_dir,
                                            "--answer", answer_path])
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertFalse(document["answer_accepted"])
        self.assertTrue(document["answer_refusals"])

    def test_the_rules_each_produce_their_own_sentence(self):
        body = json.loads(json.dumps(testlib.ANSWER))
        self.assertEqual(answermod.contents_refusals(body), [])
        twice = json.loads(json.dumps(testlib.ANSWER))
        twice["checks"].append(dict(twice["checks"][0]))
        self.assertIn("twice", answermod.contents_refusals(twice)[0])
        two_reasons = json.loads(json.dumps(testlib.ANSWER))
        two_reasons["edits"].append({"path": "src/widget.py", "reason": "another reason"})
        self.assertIn("two different reasons", answermod.contents_refusals(two_reasons)[0])


class ReportOnly(_Run):
    """Nothing to the workspace, nothing to the log, and the result says so."""

    def test_the_run_writes_nothing_and_still_reports_everything(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.commit_work(self.ws)
        before = testlib.tree_digest(self.ws)
        (code, _, err), result = self.run_all(report_only=True)
        self.assertEqual(code, 10, err)
        after = testlib.tree_digest(self.ws)
        self.assertEqual(before, after, "the workspace and the log are byte-identical")
        self.assertTrue(result["report_only"])
        self.assertTrue(result["wrote_nothing"])
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(result["records"]["appended"], [])
        self.assertTrue(result["records"]["levelled"]["dry_run"])
        self.assertFalse(result["records"]["wrote"])
        self.assertIn("report-only", result["card"]["reason"])
        # everything the run computed is still there
        self.assertEqual(result["source_set"]["committed"], ["src/widget.py"])
        self.assertTrue(result["checks"])
        self.assertIn("out_of_scope", result)
        self.assertEqual([entry["kind"] for entry in result["writes"]],
                         ["run_artifact"] * len(result["writes"]))

    def test_no_log_file_is_created_at_all(self):
        (code, _, err), result = self.run_all(report_only=True)
        self.assertEqual(code, 10, err)
        self.assertFalse(os.path.isdir(os.path.join(self.ws, "docs", "records")),
                         "a report-only run does not even open the log")


class TheOpenBlockerRefusal(_Run):
    """v1 build, step 2: no framing on a failed foundation without the user's word."""

    def _raise_a_blocker(self):
        """Put an open BLOCKER on the slice, through the component, the way a review would."""
        import subprocess
        records = os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")
        walk = subprocess.run([testlib.GEN_PYTHON, records, "verify", "--workspace", self.ws,
                               "--doc", testlib.DOC_PATH], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        head = json.loads(walk.stdout.decode("utf-8"))["head"]
        events = os.path.join(self.scratch, "finding.json")
        testlib.write_json(events, [{
            "v": 1, "at": "2026-09-21T10:00:00Z", "ledger_doc": testlib.DOC_PATH,
            "actor": {"station": "signoff", "run_id": "review-1", "harness": "test-harness"},
            "origin": {"kind": "native"}, "source": {"known": False},
            "kind": "finding_raised", "slice": "A", "severity": "BLOCKER",
            "location": {"raw": "src/widget.py:1", "file": "src/widget.py", "line": 1,
                         "line_end": None, "tag": None, "more": [], "resolved": True},
            "claim": "spin() returns the wrong count", "scenario": "spin() answers 0 for one turn",
            "raised_by": "A"}])
        done = subprocess.run([testlib.GEN_PYTHON, records, "append", "--workspace", self.ws,
                               "--doc", testlib.DOC_PATH, "--events", events,
                               "--expect-head", head],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))

    def test_an_open_blocker_refuses_the_run(self):
        self._raise_a_blocker()
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "open_blocker")
        self.assertIn("open BLOCKER", result["stop_reason"])
        self.assertEqual(result["records"]["open"]["BLOCKER"], 1)
        self.assertEqual(self.status_line(), "not started")

    def test_the_input_can_say_to_build_on_it_anyway(self):
        self._raise_a_blocker()
        (code, _, err), result = self.run_all(allow_open_blocker=True)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["records"]["open"]["BLOCKER"], 1)


class TheImporterSignalStopsTheRun(_Run):
    """Amendment A3 item 3: this core stops on any importer signal rather than trusting silence."""

    def test_a_record_line_the_importer_cannot_place_stops_the_run(self):
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        text += ("\n### 2026-09-21 — review: slice A\n"
                 "- this line sits under a record heading and fits no record shape at all\n")
        testlib.write_text(doc, text)
        testlib.commit_work(self.ws)
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "legacy_unplaced")
        self.assertIn("fit no record shape", result["stop_reason"])
        self.assertIn("second record grammar", result["stop_reason"])
        self.assertEqual(self.status_line(), "not started")


class RerunningANamedCheck(_Run):
    """The core may rerun a check command the slice names, and must say which it did."""

    def test_a_rerun_reports_what_this_core_observed(self):
        (code, _, err), result = self.run_all(rerun_checks=True)
        self.assertEqual(code, 10, err)
        row = result["checks"][0]
        self.assertEqual(row["source"], "rerun")
        self.assertEqual(row["result"], "passed")
        self.assertEqual(row["exit_code"], 0)
        self.assertEqual(row["output"].strip(), "ok")

    def test_a_rerun_that_fails_is_reported_as_failing_and_keeps_what_the_answer_claimed(self):
        """The answer is not refused here: it does not contradict ITSELF, this core's own rerun
        contradicts it. That is honest failure handling, so the run is `checks_not_passed` with
        both values on the row and the card stays where it was."""
        testlib.write_text(os.path.join(self.ws, "checks", "unit.sh"),
                           "#!/bin/sh\necho 'two tests failed'\nexit 1\n")
        testlib.commit_work(self.ws)
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["edits"].append({"path": "checks/unit.sh", "reason": "the check itself was changed"})
        (code, _, err), result = self.run_all(answer=answer, rerun_checks=True)
        self.assertEqual(code, 10, err)
        row = result["checks"][0]
        self.assertEqual(row["source"], "rerun")
        self.assertEqual(row["result"], "failing")
        self.assertEqual(row["recorded_result"], "passed", "the disagreement is kept, not hidden")
        self.assertIn("two tests failed", row["output"])
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(self.status_line(), "not started")

    def test_the_default_is_the_recorded_answer(self):
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["checks"][0]["source"], "recorded")

    def test_a_command_with_shell_syntax_is_never_run_and_says_why(self):
        """Astra's F2 changed what the row says: a requested rerun that cannot execute is
        `not_run`, and the answer's claim is kept beside it rather than standing in for it."""
        command = "sh checks/unit.sh | tee out.log"
        rows = checksmod.rows([{"name": "unit", "command": command}],
                              [{"name": "unit", "command": command, "result": "passed",
                                "exit_code": 0, "output": "recorded"}],
                              workspace=self.ws, rerun=True)
        self.assertEqual(rows[0]["result"], "not_run")
        self.assertIn("shell syntax", rows[0]["rerun_refused"])
        self.assertEqual(rows[0]["output"], "")
        self.assertEqual(rows[0]["recorded_result"], "passed")
        self.assertEqual(rows[0]["recorded_output"], "recorded")


class TheDocumentIsReadForStructureOnly(unittest.TestCase):

    def test_the_slice_is_read_from_its_heading_and_its_labelled_lists(self):
        entry = docmod.find_slice(testlib.BUILD_DOC, "A")
        self.assertEqual(entry["title"], "Make the widget spin")
        self.assertEqual(entry["status"], "not started")
        self.assertEqual(docmod.named_paths(entry), ["src/widget.py"])
        self.assertEqual(docmod.not_in_slice(entry), ["src/other.py", "checks/"])
        self.assertEqual(docmod.checks(entry), [{"name": "unit", "command": "sh checks/unit.sh"}])
        self.assertEqual(len(docmod.requirements(entry)), 1)

    def test_a_slice_the_document_does_not_carry_is_named(self):
        with self.assertRaises(docmod.DocumentError) as caught:
            docmod.find_slice(testlib.BUILD_DOC, "Z")
        self.assertIn("no slice 'Z'", str(caught.exception))
        self.assertIn("it carries: A", str(caught.exception))

    def test_setting_the_card_changes_one_line_and_nothing_else(self):
        entry = docmod.find_slice(testlib.BUILD_DOC, "A")
        after = docmod.set_status(testlib.BUILD_DOC, entry, "built")
        before_lines = testlib.BUILD_DOC.split("\n")
        after_lines = after.split("\n")
        self.assertEqual(len(before_lines), len(after_lines))
        differing = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
        self.assertEqual(differing, [entry["status_line"] - 1])
        self.assertEqual(after_lines[differing[0]], "Status: built")


class TheScopeHelperOnItsOwn(unittest.TestCase):

    def test_the_stop_sentence_names_every_path_with_no_reason(self):
        source = {"base": "base", "committed": ["a.py"], "changed": ["b.py"], "untracked": [],
                  "base_commit": "0" * 40, "head": "0" * 40, "excluded": []}
        rows = scope.out_of_scope(source, [], {"a.py": "a reason"})
        self.assertEqual(len(rows), 2)
        self.assertEqual(scope.unexplained(rows)[0]["path"], "b.py")
        sentence = scope.stop_sentence(rows)
        self.assertIn("b.py", sentence)
        self.assertNotIn("a.py,", sentence)

    def test_an_empty_reason_counts_as_no_reason(self):
        source = {"base": "base", "committed": ["a.py"], "changed": [], "untracked": [],
                  "base_commit": "0" * 40, "head": "0" * 40, "excluded": []}
        rows = scope.out_of_scope(source, [], {"a.py": "   "})
        self.assertFalse(rows[0]["reason_given"])


if __name__ == "__main__":
    unittest.main()


class TheLedgerDocumentIsSanctionedNotHidden(_Run):
    """The build doc stays IN the source set — section 8 is the truth of what changed — and is a
    SANCTIONED path for the scope comparison: never out of scope, and published with its reason so
    a reader sees the loop's own write acknowledged rather than missing."""

    def test_the_build_doc_is_in_the_source_set_when_it_changed(self):
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        testlib.write_text(doc, text + "\n## Build assumptions\n- 2026-09-22 a note\n")
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertIn(testlib.DOC_PATH, result["source_set"]["changed"])

    def test_it_is_never_listed_out_of_scope(self):
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        testlib.write_text(doc, text + "\n## Deviations\n- 2026-09-22 a deviation · builder call\n")
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertNotIn(testlib.DOC_PATH, [row["path"] for row in result["out_of_scope"]])
        self.assertEqual(result["status"], "completed", "the loop's own write does not stop the run")

    def test_it_is_published_as_sanctioned_with_a_reason(self):
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        sanctioned = result["source_set"]["sanctioned"]
        self.assertEqual([row["path"] for row in sanctioned], [testlib.DOC_PATH])
        self.assertTrue(sanctioned[0]["reason"].strip())
        self.assertEqual(result["source_set"]["excluded"], ["docs/records/"],
                         "only the component's own history is excluded now")

    def test_a_card_move_of_a_previous_run_does_not_stop_the_next_one(self):
        """The trap the exclusion was guarding against, now handled by sanctioning instead."""
        (code, _, err), result = self.run_all()
        self.assertEqual(code, 10, err)
        self.assertTrue(result["card"]["moved"])
        second = os.path.join(self.scratch, "run-2")
        path = os.path.join(self.scratch, "input-2.json")
        testlib.write_json(path, testlib.make_input(second, self.ws, run_id="run-2"))
        answer_path = os.path.join(self.scratch, "answer.json")
        for args in (["check-input", path], ["contract", "--run-dir", second],
                     ["preflight", "--run-dir", second],
                     ["record-answer", "--run-dir", second, "--answer", answer_path]):
            code, out, err = testlib.run_build(args)
            self.assertEqual(code, 0, "%s: %s%s" % (args, out, err))
        code, out, err = testlib.run_build(["report", "--run-dir", second])
        self.assertEqual(code, 10, err)
        second_result = testlib.load_json(os.path.join(second, "result.json"))
        self.assertNotEqual(second_result["stop_tag"], "scope_unexplained",
                            "the previous run's `Status:` write is sanctioned, not unexplained")


class ThePrecedenceOfTheOutcomes(_Run):
    """When several outcomes could apply, which one the run reports (build-contract.md section 12)."""

    def test_a_refused_answer_is_decided_before_the_scope_stop(self):
        """The reason a path needs is the answer's, so a broken answer is the first thing to fix."""
        testlib.write_text(os.path.join(self.ws, "src", "stray.py"), "X = 1\n")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(result="failing", exit_code=1, output="FAILED")
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused")
        self.assertEqual(result["terminal_status"], "stop")
        # nothing is hidden by the order: the unexplained path is still listed
        rows = [row for row in result["out_of_scope"] if row["path"] == "src/stray.py"]
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["reason_given"])

    def test_a_stop_of_the_records_pre_empts_every_completion(self):
        """A run that could not read its records never reaches the answer at all."""
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        testlib.write_text(doc, text + "\n### 2026-09-21 — review: slice A\n- an unplaceable line\n")
        testlib.commit_work(self.ws)
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(result="failing", exit_code=1, output="FAILED")
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "legacy_unplaced")

    def test_a_failing_check_is_decided_before_an_incomplete_claim(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer.update(claimed_status="partial", claimed_card="not started")
        answer["checks"][0].update(result="failing", exit_code=1, output="FAILED")
        (code, _, err), result = self.run_all(answer=answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "checks_not_passed")
