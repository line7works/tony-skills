"""E13 slice 2 fix round: Astra's findings against the build core, rebuilt as tests.

Each class below rebuilds the SHAPE of one of her probes through the real CLI (her probe scripts
are not available to this round; `astra-review-slice-2.md` names each probe's shape and output).
The class docstring names the finding. They were written red first; the red output is kept in the
fix round's scratch folder.
"""
import json
import os
import unittest

import shimlib
import testlib

testlib.add_scripts_to_path()

LOG = "docs/records/docs__plans__2026-09-20-widget.events.jsonl"


def read_log(workspace):
    path = os.path.join(workspace, LOG)
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh.read().split("\n") if line.strip()]


def card_sets(workspace):
    return [e for e in read_log(workspace) if e.get("kind") == "card_set"]


class _Phases(unittest.TestCase):
    """A workspace, and the five phases driven one at a time so a test can act between them."""

    DOC = testlib.BUILD_DOC

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-fix2-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch, doc=self.DOC)
        self.run_dir = os.path.join(self.scratch, "run")
        self.env = None

    def write_input(self, run_dir=None, run_id="run-1", **extra):
        path = os.path.join(self.scratch, "input-%s.json" % run_id)
        testlib.write_json(path, testlib.make_input(run_dir or self.run_dir, self.ws,
                                                    run_id=run_id, **extra))
        return path

    def write_answer(self, answer=None, name="answer.json"):
        path = os.path.join(self.scratch, name)
        testlib.write_json(path, answer or testlib.ANSWER)
        return path

    def build(self, args):
        return testlib.run_build(args, env=self.env)

    def through_preflight(self, run_dir=None, run_id="run-1", **extra):
        run_dir = run_dir or self.run_dir
        path = self.write_input(run_dir, run_id, **extra)
        outs = []
        for args in (["check-input", path], ["contract", "--run-dir", run_dir],
                     ["preflight", "--run-dir", run_dir]):
            code, out, err = self.build(args)
            self.assertEqual(code, 0, "%s: %s%s" % (args, out, err))
            outs.append(json.loads(out))
        return outs[-1]

    def answer_and_report(self, answer=None, run_dir=None):
        run_dir = run_dir or self.run_dir
        path = self.write_answer(answer)
        code, out, err = self.build(["record-answer", "--run-dir", run_dir, "--answer", path])
        self.assertEqual(code, 0, "%s%s" % (out, err))
        code, out, err = self.build(["report", "--run-dir", run_dir])
        result_path = os.path.join(run_dir, "result.json")
        result = testlib.load_json(result_path) if os.path.isfile(result_path) else None
        return code, out, err, result

    def whole_run(self, answer=None, run_dir=None, run_id="run-1", **extra):
        self.through_preflight(run_dir, run_id, **extra)
        return self.answer_and_report(answer, run_dir)

    def status_line(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), encoding="utf-8") as fh:
            for line in fh.read().split("\n"):
                if line.startswith("Status:"):
                    return line[len("Status:"):].strip()
        return None

    def doc_bytes(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), "rb") as fh:
            return fh.read()

    def answer_with_reason(self, *paths):
        answer = json.loads(json.dumps(testlib.ANSWER))
        for path in paths:
            answer["edits"].append({"path": path, "reason": "reason for %s" % path})
        return answer


class F1TheReportRecomputesTheSourceSet(_Phases):
    """F1 (BLOCKER). After preflight, add an untracked file, change a tracked file, or commit an
    out-of-scope change: `report` must recompute the three lists against the pinned base, publish
    that set, and bind the card event to the identity that goes with it. Astra's
    `probe_windows.py` saw `completed`/`moved` with the preflight lists and `out_of_scope: []`."""

    def assert_stopped_on(self, path, lists):
        code, out, err, result = self.answer_and_report()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "stopped", json.dumps(result, indent=1)[:1500])
        self.assertEqual(result["stop_tag"], "scope_unexplained")
        rows = [row for row in result["out_of_scope"] if row["path"] == path]
        self.assertEqual(len(rows), 1, result["out_of_scope"])
        self.assertEqual(rows[0]["lists"], lists)
        every = (result["source_set"]["committed"] + result["source_set"]["changed"]
                 + result["source_set"]["untracked"])
        self.assertIn(path, every, "the published set is the one computed at report")
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(card_sets(self.ws), [])
        self.assertEqual(self.status_line(), "not started")

    def test_an_untracked_file_added_after_preflight(self):
        self.through_preflight()
        testlib.write_text(os.path.join(self.ws, "src", "late.py"), "LATE = 1\n")
        self.assert_stopped_on("src/late.py", ["untracked"])

    def test_a_tracked_file_changed_after_preflight(self):
        self.through_preflight()
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 7\n")
        self.assert_stopped_on("src/other.py", ["changed"])

    def test_an_out_of_scope_change_committed_after_preflight(self):
        self.through_preflight()
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 8\n")
        testlib.commit_work(self.ws, "late commit")
        self.assert_stopped_on("src/other.py", ["committed"])

    def test_the_card_event_carries_the_identity_of_the_set_it_was_decided_on(self):
        pre = self.through_preflight()
        # an in-scope change after preflight: the decision stands, the identity moved
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 3\n")
        code, out, err, result = self.answer_and_report()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "completed")
        self.assertIn("src/widget.py", result["source_set"]["changed"])
        event = card_sets(self.ws)[0]
        self.assertNotEqual(event["source"]["identity"], pre["identity"],
                            "the event is bound to the identity computed at report, not preflight's")
        self.assertEqual(event["source"]["identity"], result["identity"])
        self.assertIn(testlib.DOC_PATH, [row["path"] for row in result["source_set"]["sanctioned"]],
                      "the ledger document stays in the set, sanctioned")

    def test_a_settle_re_delivers_the_recomputed_set_and_reruns_nothing(self):
        counter = os.path.join(self.scratch, "rerun-count.txt")
        testlib.write_text(os.path.join(self.ws, "checks", "unit.sh"),
                           "#!/bin/sh\necho run >> %s\necho ok\n" % counter)
        testlib.commit_work(self.ws, "counting check")
        shim_root, fault = shimlib.make_shim(self.scratch, testlib.RECORDS_ROOT)
        self.env = testlib.base_env(shimlib.env(shim_root, testlib.RECORDS_ROOT, fault))
        self.through_preflight(rerun_checks=True)
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 4\n")
        path = self.write_answer(self.answer_with_reason("checks/unit.sh"))
        self.assertEqual(self.build(["record-answer", "--run-dir", self.run_dir, "--answer", path])[0], 0)
        shimlib.fault(fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.build(["report", "--run-dir", self.run_dir])[0], 10)
        shimlib.disarm(fault)
        code, out, err = self.build(["report", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, err)
        result = testlib.load_json(os.path.join(self.run_dir, "result.json"))
        self.assertEqual(result["status"], "completed")
        self.assertIn("src/widget.py", result["source_set"]["changed"])
        with open(counter, encoding="utf-8") as fh:
            self.assertEqual(fh.read().count("run"), 1, "recovery does not rerun the checks")
        events = card_sets(self.ws)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"]["identity"], result["identity"])


class F2AnUnrunnableOrContradictedCheckNeverAwardsBuilt(_Phases):
    """F2 (BLOCKER). A requested rerun that cannot execute is `not_run`, keeps its refusal reason
    and the executor's claim separately, and the run finishes `checks_not_passed` without moving
    the card. A recorded `passed` contradicted by a nonzero exit is refused. One command's output
    is never attributed to another named command. Astra's `probe_build.py` (a missing executable,
    a shell-syntax rerun) and `probe_followups.py` (`passed`, exit 8, output FAILED) each built."""

    DOC = testlib.BUILD_DOC.replace("- unit: sh checks/unit.sh", "- unit: %s")

    def workspace_with_check(self, command):
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        testlib.write_text(doc, text.replace("- unit: %s", "- unit: %s" % command))
        testlib.commit_work(self.ws, "the slice names its check")

    def test_a_missing_executable_is_not_run(self):
        self.workspace_with_check("no-such-executable-e13 --flag")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0]["command"] = "no-such-executable-e13 --flag"
        code, out, err, result = self.whole_run(answer, rerun_checks=True)
        self.assertEqual(code, 10, err)
        row = result["checks"][0]
        self.assertEqual(row["result"], "not_run", row)
        self.assertTrue(row["rerun_refused"])
        self.assertEqual(row["recorded_result"], "passed", "the executor's claim is kept separately")
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(card_sets(self.ws), [])
        self.assertEqual(self.status_line(), "not started")

    def test_a_shell_syntax_rerun_is_not_run(self):
        self.workspace_with_check("sh checks/unit.sh | tee out.log")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0]["command"] = "sh checks/unit.sh | tee out.log"
        code, out, err, result = self.whole_run(answer, rerun_checks=True)
        self.assertEqual(code, 10, err)
        row = result["checks"][0]
        self.assertEqual(row["result"], "not_run", row)
        self.assertIn("shell syntax", row["rerun_refused"])
        self.assertEqual(row["recorded_result"], "passed")
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertFalse(result["card"]["moved"])

    def test_a_recorded_pass_with_a_nonzero_exit_is_refused(self):
        self.workspace_with_check("sh checks/unit.sh")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(result="passed", exit_code=8, output="FAILED")
        code, out, err, result = self.whole_run(answer)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused", result["status"])
        self.assertTrue(any("exit" in why for why in result["answer"]["refusals"]),
                        result["answer"]["refusals"])
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(card_sets(self.ws), [])

    def test_another_commands_output_is_never_attributed_to_the_named_check(self):
        self.workspace_with_check("sh checks/unit.sh")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(command="sh checks/other.sh", output="ok from another command")
        code, out, err, result = self.whole_run(answer)
        self.assertEqual(code, 10, err)
        row = result["checks"][0]
        self.assertEqual(row["command"], "sh checks/unit.sh")
        self.assertNotEqual(row["output"], "ok from another command",
                            "the output of `sh checks/other.sh` is not the output of the named check")
        self.assertEqual(row["result"], "not_run")
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertFalse(result["card"]["moved"])


class F11ASecondBuildMakesNoCardMove(_Phases):
    """F11 (MINOR). A second build on a card already at `built` opens no transaction, appends no
    `card_set`, reports no `Status:` write, and says the card was already built. Astra saw
    `not started -> built`, then `built -> built` with `moved: true`."""

    def test_the_second_run_moves_nothing(self):
        code, out, err, first = self.whole_run()
        self.assertEqual(first["status"], "completed")
        self.assertEqual(len(card_sets(self.ws)), 1)
        before = self.doc_bytes()
        second_dir = os.path.join(self.scratch, "run-2")
        code, out, err, second = self.whole_run(run_dir=second_dir, run_id="run-2")
        self.assertEqual(code, 10, err)
        self.assertEqual(second["status"], "completed")
        self.assertFalse(second["card"]["moved"])
        self.assertEqual(second["card"]["before"], "built")
        self.assertEqual(second["card"]["after"], "built")
        self.assertIn("already", second["card"]["reason"])
        self.assertEqual(len(card_sets(self.ws)), 1, "no `built -> built` event")
        self.assertEqual(self.doc_bytes(), before)
        self.assertNotIn("status_line", [w["kind"] for w in second["writes"]])
        self.assertFalse(os.path.exists(os.path.join(second_dir, "receipt.json")),
                         "no card transaction was opened")


class F12TheStrictLegacyStopBeforeLevelling(_Phases):
    """F12 (MAJOR), build's half. A hand-written line under a review heading that fits no Appendix
    A shape stops the run with its document, line and raw bytes before the log is levelled; the
    importer's tolerant success does not authorize proceeding. Astra's `probe_legacy_parity.py`
    supplied the line below: both pilot versions stopped `missing_input`, build completed/built."""

    LINE = "- MAJOR · src/widget.py:2 · Call spin and observe zero."

    def test_the_reader_is_the_pilots_own_byte_for_byte(self):
        """One record grammar: the stop check is the recheck pilot's `ledger.py`, copied whole and
        held equal here, never a second reader of this station's own."""
        pilot = os.path.join(os.path.dirname(testlib.PLUGIN), "recheck-v2", "skills", "recheck-v2",
                             "scripts", "recheck_core", "ledger.py")
        mine = os.path.join(testlib.SCRIPTS, "build_core", "record_grammar.py")
        with open(pilot, "rb") as fh:
            want = fh.read()
        with open(mine, "rb") as fh:
            self.assertEqual(fh.read(), want)

    def test_an_unplaceable_line_stops_with_document_line_and_bytes(self):
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        text += "\n### 2026-09-21 — review: Slice A\n%s\n" % self.LINE
        testlib.write_text(doc, text)
        testlib.commit_work(self.ws, "a hand-written review")
        line_no = text.split("\n").index(self.LINE) + 1
        path = self.write_input()
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir]):
            self.assertEqual(self.build(args)[0], 0)
        code, out, err = self.build(["preflight", "--run-dir", self.run_dir])
        self.assertEqual(code, 10, out + err)
        result = testlib.load_json(os.path.join(self.run_dir, "result.json"))
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "legacy_unplaced")
        self.assertIn("%s:%d" % (testlib.DOC_PATH, line_no), result["stop_reason"])
        self.assertIn(self.LINE, result["stop_reason"])
        self.assertEqual(result["unplaced"], [{"doc": testlib.DOC_PATH, "line": line_no,
                                               "raw": self.LINE,
                                               "reason": result["unplaced"][0]["reason"]}])
        self.assertFalse(os.path.isdir(os.path.join(self.ws, "docs", "records")),
                         "the log was not levelled over a record this core cannot place")
        self.assertEqual(self.status_line(), "not started")

    def test_a_line_added_between_preflight_and_report_stops_report(self):
        self.through_preflight()
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        testlib.write_text(doc, text + "\n### 2026-09-21 — review: Slice A\n%s\n" % self.LINE)
        before = read_log(self.ws)
        code, out, err, result = self.answer_and_report()
        self.assertEqual(code, 10, err)
        self.assertEqual(result["stop_tag"], "legacy_unplaced")
        self.assertEqual(read_log(self.ws), before, "no levelling pass over the unplaceable line")
        self.assertEqual(card_sets(self.ws), [])


class F14ADotfileIsNotItsUndottedTwin(_Phases):
    """F14 (MAJOR). The footprint names `config.env`; an untracked `.config.env` created before
    preflight is a different path and is out of scope. Astra's `probe_scope_dot.py` saw it pass."""

    DOC = testlib.BUILD_DOC.replace("- src/widget.py\n", "- src/widget.py\n- config.env\n")

    def test_the_leading_dot_is_kept(self):
        from build_core import doc as docmod
        self.assertFalse(docmod.in_named_paths(".config.env", ["config.env"]))
        self.assertFalse(docmod.in_named_paths("config.env", [".config.env"]))
        self.assertTrue(docmod.in_named_paths("./config.env", ["config.env"]))
        self.assertTrue(docmod.in_named_paths("config.env", ["././config.env"]))
        self.assertFalse(docmod.in_named_paths("src/.hidden/x.py", ["src/hidden"]))

    def test_the_dotfile_is_out_of_scope_through_the_cli(self):
        testlib.write_text(os.path.join(self.ws, ".config.env"), "SECRET_SHAPE=0\n")
        code, out, err, result = self.whole_run()
        self.assertEqual(code, 10, err)
        self.assertIn(".config.env", result["source_set"]["untracked"])
        self.assertEqual([row["path"] for row in result["out_of_scope"]], [".config.env"])
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "scope_unexplained")
        self.assertFalse(result["card"]["moved"])


class F15CheckSubprocessesHonourTheNoWriteBranches(_Phases):
    """F15 (MAJOR). A refused answer launches no check subprocess; report-only covers child writes
    (a rerun that would write in the live report-only workspace is `not_run` and the run finishes
    `checks_not_passed`); a result never claims no writes when a child changed workspace bytes.
    Astra's `probe_report_only.py` got `source-change.txt` beside `wrote_nothing: true`, and
    `probe_refused_rerun.py` changed the ledger before returning `answer_refused`."""

    def writing_check(self, body):
        testlib.write_text(os.path.join(self.ws, "checks", "unit.sh"), "#!/bin/sh\n%s\n" % body)
        testlib.commit_work(self.ws, "a check that writes")

    def test_a_refused_answer_runs_no_check(self):
        self.writing_check("echo tampered >> %s\necho ok" % testlib.DOC_PATH)
        before = self.doc_bytes()
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["claimed_card"] = "nearly done"            # R2: refused on its contents
        code, out, err, result = self.whole_run(answer, rerun_checks=True)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "answer_refused")
        self.assertEqual(self.doc_bytes(), before, "no check ran, so nothing touched the ledger")
        self.assertEqual(result["checks"][0]["source"], "recorded")

    def test_report_only_runs_no_check_in_the_live_workspace(self):
        self.writing_check("echo changed > source-change.txt\necho ok")
        before = testlib.tree_digest(self.ws)
        code, out, err, result = self.whole_run(self.answer_with_reason("checks/unit.sh"),
                                                report_only=True, rerun_checks=True)
        self.assertEqual(code, 10, err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "source-change.txt")))
        self.assertEqual(testlib.tree_digest(self.ws), before)
        row = result["checks"][0]
        self.assertEqual(row["result"], "not_run", row)
        self.assertIn("report-only", row["rerun_refused"])
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertTrue(result["wrote_nothing"])

    def test_a_child_that_wrote_is_never_reported_as_no_writes(self):
        self.writing_check("echo changed > child-wrote.txt\necho broken\nexit 1")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer.update(claimed_status="partial", claimed_card="not started")
        code, out, err, result = self.whole_run(answer, rerun_checks=True)
        self.assertEqual(code, 10, err)
        self.assertTrue(os.path.exists(os.path.join(self.ws, "child-wrote.txt")))
        self.assertFalse(result["wrote_nothing"], "a check subprocess changed the workspace")
        self.assertTrue(result["checks_changed_workspace"])
        self.assertIn("child-wrote.txt", result["source_set"]["untracked"])


if __name__ == "__main__":
    unittest.main()
