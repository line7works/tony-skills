"""E13 slice 2, the last fix round: what Astra's recheck left in the build core, rebuilt as tests.

Her probe scripts are not available to this round; `astra-recheck-slice-2.md` names each probe's
shape and printed output, and each class below rebuilds that shape through the real CLI and the
real records component. The class docstring names her item. Written red first; the red output is
kept in the round's scratch folder.
"""
import json
import os
import subprocess
import unittest

import testlib
from test_fix2_astra import _Phases, card_sets, read_log

testlib.add_scripts_to_path()

RECORDS_CLI = os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")
SIGNOFF_RUN = "signoff-fix3-ranged-1"
RANGED = {"raw": "src/widget.py:1-2", "file": "src/widget.py", "line": 1, "line_end": 2,
          "tag": None, "more": [], "resolved": True}


class _Records(_Phases):
    """The records component run directly, the way a signoff station reaches it."""

    def records(self, *args, **kwargs):
        env = testlib.base_env()
        proc = subprocess.run([testlib.GEN_PYTHON, RECORDS_CLI] + list(args), cwd=self.scratch,
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        body = json.loads(out) if out.strip() else None
        if kwargs.get("check", True):
            self.assertEqual(proc.returncode, 0, "%s: %s %s" % (
                args[0], out, proc.stderr.decode("utf-8", "replace")))
        return proc.returncode, body

    def raise_native(self, location=RANGED, run_id=SIGNOFF_RUN):
        """A signoff station's native raise: level, append one `finding_raised`, render the run."""
        ws, doc = self.ws, testlib.DOC_PATH
        self.records("import-legacy", "--workspace", ws, "--doc", doc)
        head = self.records("verify", "--workspace", ws, "--doc", doc)[1]["head"]
        identity = self.records("identity", "--workspace", ws)[1]["identity"]
        event = {"v": 1, "kind": "finding_raised", "at": "2026-09-21T10:00:00Z", "ledger_doc": doc,
                 "actor": {"station": "signoff-v2", "run_id": run_id, "harness": "claude-code"},
                 "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                 "slice": "A", "severity": "MAJOR", "location": location,
                 "claim": "spin returns zero turns", "scenario": "call spin() and observe 0",
                 "raised_by": "independent reviewer"}
        path = os.path.join(self.scratch, "native-events.json")
        testlib.write_json(path, [event])
        self.records("append", "--workspace", ws, "--doc", doc, "--events", path,
                     "--expect-head", head)
        return self.records("render", "--workspace", ws, "--doc", doc, "--run-id", run_id)[1]

    def run_all(self, answer=None, run_id="run-1", **extra):
        """Every phase in turn, stopping at the first that does not exit 0 (a stop can land at
        preflight or at report). Returns (exit code, the phase, result.json or None)."""
        path = self.write_input(self.run_dir, run_id, **extra)
        answer_path = self.write_answer(answer)
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", answer_path],
                     ["report", "--run-dir", self.run_dir]):
            code, out, err = self.build(args)
            if code != 0 or args[0] == "report":
                break
        result_path = os.path.join(self.run_dir, "result.json")
        result = testlib.load_json(result_path) if os.path.isfile(result_path) else None
        return code, args[0], result

    def place(self, text, commit=True):
        path = os.path.join(self.ws, testlib.DOC_PATH)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)
        if commit:
            testlib.commit_work(self.ws, "the signoff station's review block")


class N1ANativeRangedReviewPassesTheNextBuild(_Records):
    """N1 (MAJOR). Records preserves a ranged location on a native review line (F9); the build
    core's Appendix A detector read that native line with the legacy grammar and stopped the next
    build `legacy_unplaced`. Astra's `probe_fix_edges.py`: first signoff completed, dry import
    `native_rendered=2, would_import=0`, next build `stopped / legacy_unplaced`, `second field
    'src/widget.py:2-3' is not a file:line location`. Native occurrences are identified through the
    records CLI (render, events, the dry run's `native_rendered`), consumed once, and the unchanged
    Appendix A stop applies to what remains."""

    def test_the_next_build_proceeds_over_the_rendered_ranged_line(self):
        rendered = self.raise_native()
        self.assertIn("src/widget.py:1-2", rendered["review_lines"][0])
        self.place(rendered["review"])
        code, phase, result = self.run_all()
        self.assertEqual(code, 10, (phase, result))
        self.assertNotEqual(result.get("stop_tag"), "legacy_unplaced", json.dumps(result)[:1500])
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["card"]["moved"])

    def test_a_hand_written_ranged_line_still_stops(self):
        """Only lines the component itself rendered are accepted: the same shape written by hand
        (another reviewer name, so no native event renders to it) stops as before."""
        rendered = self.raise_native()
        by_hand = rendered["review"].replace("independent reviewer", "a person")
        self.place(by_hand)
        code, phase, result = self.run_all()
        self.assertEqual(code, 10, (phase, result))
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "legacy_unplaced")
        self.assertIn("src/widget.py:1-2", result["stop_reason"])
        self.assertEqual(card_sets(self.ws), [])

    def test_a_second_copy_of_the_rendered_line_still_stops_before_any_write(self):
        """An ambiguous duplicate: each native occurrence answers for one line, so the copy is a
        hand-written line Appendix A cannot place, and the run stops before levelling."""
        rendered = self.raise_native()
        line = rendered["review_lines"][0]
        self.place(rendered["review"] + line + "\n")
        before = read_log(self.ws)
        code, phase, result = self.run_all()
        self.assertEqual(code, 10, (phase, result))
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "legacy_unplaced")
        self.assertEqual(read_log(self.ws), before, "nothing was levelled")
        self.assertEqual(card_sets(self.ws), [])


class N2AnExecutedRerunAfterAMismatchIsAValidCompletion(_Records):
    """N2 (MAJOR). After an answer-command mismatch, a rerun that EXECUTES kept
    `attribution_refused`, and V11 rejected the completion the core itself wrote. Astra's
    `probe_fix_edges.py` and the standalone validator: named `sh checks/unit.sh`, observed exit 0,
    output `unit-ok`, result passed; report exit 10, completed, card moved; validate-result exit 4,
    V11 `the check is not_run, not 'passed'`; the same with a failing rerun. Rejected recorded
    evidence is kept apart from the observed rerun, V11 requires `not_run` only when no executed
    observation of the named command exists, and the proposed result is validated before any card
    transaction opens."""

    def check_script(self, body):
        testlib.write_text(os.path.join(self.ws, "checks", "unit.sh"), "#!/bin/sh\n%s\n" % body)
        testlib.commit_work(self.ws, "the named check")

    def mismatched_answer(self, **update):
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["checks"][0].update(command="sh checks/other.sh", output="ok from another command")
        answer["edits"].append({"path": "checks/unit.sh", "reason": "the fixture's named check"})
        answer.update(update)
        return answer

    def validate_written_result(self):
        code, out, err = testlib.run_script(
            "validate-result.py", [os.path.join(self.run_dir, "result.json"),
                                   "--input", os.path.join(self.scratch, "input-run-1.json"),
                                   "--run-dir", self.run_dir])
        return code, (json.loads(out) if out.strip() else None), err

    def test_a_passing_rerun_reports_what_it_observed_and_validates(self):
        self.check_script("echo unit-ok")
        code, phase, result = self.run_all(self.mismatched_answer(), rerun_checks=True)
        self.assertEqual(code, 10, (phase, result))
        row = result["checks"][0]
        self.assertEqual((row["result"], row["exit_code"], row["output"], row["source"]),
                         ("passed", 0, "unit-ok\n", "rerun"), row)
        self.assertEqual(row["recorded_command"], "sh checks/other.sh")
        self.assertEqual(row["recorded_output"], "ok from another command")
        self.assertEqual(row["recorded_result"], "passed")
        self.assertTrue(row["attribution_refused"], "the rejected recorded evidence says why")
        self.assertIsNone(row["rerun_refused"])
        vcode, report, err = self.validate_written_result()
        self.assertEqual(vcode, 0, (report, err))
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["card"]["moved"])

    def test_a_failing_rerun_reports_what_it_observed_and_validates(self):
        self.check_script("echo unit-broken\nexit 1")
        code, phase, result = self.run_all(self.mismatched_answer(), rerun_checks=True)
        self.assertEqual(code, 10, (phase, result))
        row = result["checks"][0]
        self.assertEqual((row["result"], row["exit_code"], row["source"]), ("failing", 1, "rerun"))
        self.assertEqual(row["recorded_command"], "sh checks/other.sh")
        vcode, report, err = self.validate_written_result()
        self.assertEqual(vcode, 0, (report, err))
        self.assertEqual(result["status"], "checks_not_passed")
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(card_sets(self.ws), [])

    def test_an_unexecutable_rerun_after_a_mismatch_stays_not_run(self):
        doc = os.path.join(self.ws, testlib.DOC_PATH)
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        testlib.write_text(doc, text.replace("- unit: sh checks/unit.sh",
                                             "- unit: no-such-executable-e13"))
        testlib.commit_work(self.ws, "a check that cannot run")
        code, phase, result = self.run_all(self.mismatched_answer(), rerun_checks=True)
        self.assertEqual(code, 10, (phase, result))
        row = result["checks"][0]
        self.assertEqual(row["result"], "not_run", row)
        self.assertTrue(row["rerun_refused"])
        self.assertTrue(row["attribution_refused"])
        vcode, report, err = self.validate_written_result()
        self.assertEqual(vcode, 0, (report, err))
        self.assertEqual(result["status"], "checks_not_passed")


    def test_an_invalid_completion_is_never_committed(self):
        """N2's last sentence: the proposed result is validated before any card transaction. The
        build is driven through its real `main`, with the check rows replaced by the old N2 shape
        (a `passed` row that keeps `attribution_refused` with no executed observation), which V11
        refuses: the run stops `result_invalid`, no `card_set` is appended, the line is unchanged."""
        wrapper = os.path.join(self.scratch, "build-with-old-rows.py")
        testlib.write_text(wrapper, "\n".join([
            "import sys",
            "sys.path.insert(0, %r)" % testlib.SCRIPTS,
            "sys.argv[0] = %r" % os.path.join(testlib.SCRIPTS, "build.py"),
            "import build",
            "from build_core import checks",
            "real = checks.rows",
            "def old_rows(*args, **kwargs):",
            "    out = real(*args, **kwargs)",
            "    for row in out:",
            "        if row.get('named_by_slice'):",
            "            row.update(result='passed', source='recorded', exit_code=0,",
            "                       attribution_refused='another command', rerun_refused=None)",
            "    return out",
            "checks.rows = old_rows",
            "build.checksmod.rows = old_rows",
            "sys.exit(build.main(sys.argv[1:]))",
        ]))
        path = self.write_input(self.run_dir, "run-1")
        answer_path = self.write_answer(self.mismatched_answer())
        for args in (["check-input", path], ["contract", "--run-dir", self.run_dir],
                     ["preflight", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer", answer_path]):
            self.assertEqual(self.build(args)[0], 0, args)
        import subprocess, sys
        proc = subprocess.run([sys.executable, wrapper, "report", "--run-dir", self.run_dir],
                              env=testlib.base_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 10, proc.stderr.decode("utf-8", "replace"))
        result = testlib.load_json(os.path.join(self.run_dir, "result.json"))
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "result_invalid")
        self.assertIn("V11", result["stop_reason"])
        self.assertEqual(card_sets(self.ws), [])
        self.assertEqual(self.status_line(), "not started")
        self.assertFalse(result["card"]["moved"])

    def test_v11_still_refuses_an_attributed_row_with_no_executed_observation(self):
        from build_core import validate
        row = {"name": "unit", "command": "sh checks/unit.sh", "result": "passed", "exit_code": 0,
               "output": "ok", "source": "recorded", "named_by_slice": True,
               "rerun_refused": None, "recorded_result": "passed",
               "recorded_command": "sh checks/other.sh", "recorded_output": "ok",
               "attribution_refused": "another command"}
        found = validate.run_semantic({"status": "completed", "checks": [row]})["semantic"]
        self.assertTrue(any(f["id"] == "V11" for f in found), found)
        row.update(source="rerun")
        found = validate.run_semantic({"status": "completed", "checks": [row]})["semantic"]
        self.assertFalse(any(f["id"] == "V11" for f in found), found)
        row.update(rerun_refused="could not start")
        found = validate.run_semantic({"status": "completed", "checks": [row]})["semantic"]
        self.assertTrue(any(f["id"] == "V11" for f in found), found)


class F15AnIgnoredFileAChildWroteIsStillAWrite(_Records):
    """F15 remainder (MAJOR). Astra's `probe_recovery_and_child.py`: a check that creates a
    git-IGNORED `generated-cache.txt` returned `completed`, `checks_changed_workspace: false`,
    `wrote_nothing: true`. The before/after measurement sees every byte under the workspace
    (`.git` excluded), ignored files included; a detected write is reported as today."""

    def test_a_check_that_writes_an_ignored_file(self):
        testlib.write_text(os.path.join(self.ws, ".gitignore"),
                           "__pycache__/\n*.pyc\nbuild/\ngenerated-cache.txt\n")
        testlib.write_text(os.path.join(self.ws, "checks", "unit.sh"),
                           "#!/bin/sh\necho cached > generated-cache.txt\necho ok\n")
        testlib.commit_work(self.ws, "a check that leaves an ignored cache")
        answer = json.loads(json.dumps(testlib.ANSWER))
        answer["edits"] += [{"path": "checks/unit.sh", "reason": "the fixture's check"},
                            {"path": ".gitignore", "reason": "the fixture's ignore list"}]
        code, phase, result = self.run_all(answer, rerun_checks=True)
        self.assertEqual(code, 10, (phase, result))
        self.assertTrue(os.path.exists(os.path.join(self.ws, "generated-cache.txt")))
        self.assertNotIn("generated-cache.txt", result["source_set"]["untracked"],
                         "ignored, so outside the source set")
        self.assertTrue(result["checks_changed_workspace"], json.dumps(result)[:1200])
        self.assertFalse(result["wrote_nothing"])

    def test_a_check_that_writes_nothing_is_still_no_child_write(self):
        answer = json.loads(json.dumps(testlib.ANSWER))
        code, phase, result = self.run_all(answer, rerun_checks=True)
        self.assertEqual(code, 10, (phase, result))
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1200])
        self.assertFalse(result["checks_changed_workspace"])


if __name__ == "__main__":
    unittest.main()
