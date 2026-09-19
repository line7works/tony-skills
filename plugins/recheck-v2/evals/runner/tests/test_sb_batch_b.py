"""Batch B of the sealed bench: judgment apart from format (B1) and the rig defects (B3).

Every test here fails against batch A's commit `dd8e715` and passes after batch B. Standard
library only, Python 3.9, runs from any working directory. No test opens `evals/answer-key/`
or the held-out set: the grading tests point the runner at a stand-in key they write
themselves, under `RECHECK_RUNNER_TEST=1` (E10-21).
"""
import json
import os
import unittest

import testlib
from testlib import CASE, RunnerCase, cli, parse_stdout, runner

ITEM = {"file": "src/widget/export.py", "line": 21}
LOCATION = "src/widget/export.py:21"
EXPECTED = {"status": "completed",
            "items": [{"location": dict(ITEM), "disposition": "not_fixed",
                       "reason": "reproduces"}]}


def reply_for(disposition="not fixed", reason="reproduces", location=LOCATION):
    """A harness reply in the Output block's own grammar (contract section 7)."""
    return "\n".join([
        "The run committed.", "",
        "```",
        "RECHECK: A — 1 items (+0 new)",
        "Result: NOT CLEAR · Status: unchanged (rejected)",
        "Source: test-commit clean · Verifier: test",
        "Method: %s executed: the scenario" % location,
        "",
        "BLOCKER · %s · (the title with a comma is not quoted) · %s (%s) · executed the "
        "scenario and saw the defect" % (location, disposition, reason),
        "Still open: BLOCKER · %s · the title with a comma is not quoted · fix it" % location,
        "```", ""])


class JudgmentApartFromFormat(RunnerCase):
    """B1: the call the session made, graded wherever the session stated it."""

    def no_result_record(self, reply, tid=None):
        """A record with a reply and NO result.json - the without-skill shape."""
        tid = tid or runner.trial_id("claude-code", CASE, "available", 1)
        record = os.path.join(self.campaign, "trials", tid)
        runner.write_json(os.path.join(record, "command.json"),
                          {"case": CASE, "setup": "claude-code", "condition": "available",
                           "workspace": "/nowhere", "status": "no_result",
                           "wall_seconds": 1.0, "staged_commit": "test-commit"})
        runner.write_text(os.path.join(record, "reply.md"), reply)
        return tid, record

    def grade(self, tid, key_directory, extra=()):
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": key_directory})
        done = cli(["grade", "--campaign", self.campaign, tid] + list(extra),
                   env=environment)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        return parse_stdout(done)

    # ---- the fault B1 closes -----------------------------------------------------------

    def test_a_no_result_attempt_is_graded_on_judgment_from_its_reply(self):
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record(reply_for())
        document = self.grade(tid, directory, ["--summary"])
        grade = runner.read_json(os.path.join(record, "grade.json"))
        # `ok` keeps today's meaning EXACTLY: no record, no pass.
        self.assertFalse(grade["ok"])
        self.assertEqual(grade["ok_because"], ["no result.json"])
        self.assertFalse(grade["format_ok"])
        self.assertEqual(grade["format_because"], ["no result.json"])
        # ...and the judgment is measured anyway, from the harness's own reply.
        self.assertTrue(grade["judgment_ok"], grade["judgment_because"])
        self.assertEqual(grade["judgment"]["sources"], {"reply.md": 1})
        self.assertEqual(grade["judgment"]["items"][0]["location"], LOCATION)
        self.assertEqual(grade["judgment"]["items"][0]["disposition"], "not_fixed")
        self.assertEqual(grade["judgment"]["items"][0]["reason"], "reproduces")
        self.assertEqual(grade["judgment"]["unextracted"], 0)
        self.assertEqual(document["summary"]["judgment_ok"], 1)
        self.assertEqual(document["summary"]["format_ok"], 0)

    def test_a_no_result_attempt_can_FAIL_on_judgment(self):
        """Not a free pass: the reply that says the wrong thing fails."""
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record(reply_for(disposition="fixed", reason=""))
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        self.assertFalse(grade["judgment_ok"])
        self.assertIn("dispositions_all_matched", grade["judgment_because"])
        self.assertEqual(grade["judgment"]["items"][0]["disposition"], "fixed")

    def test_the_right_disposition_with_the_wrong_reason_fails_judgment(self):
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record(reply_for(reason="missed_case"))
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        self.assertEqual(grade["judgment"]["items"][0]["reason"], "missed_case")
        self.assertFalse(grade["judgment_ok"])

    def test_an_item_no_source_names_is_unextracted_and_never_guessed(self):
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record("The run stopped. Nothing to report.\n")
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        row = grade["judgment"]["items"][0]
        self.assertEqual(row["source"], "unextracted")
        self.assertIsNone(row["disposition"])
        self.assertIsNone(row["reason"])
        self.assertEqual(grade["judgment"]["unextracted"], 1)
        self.assertFalse(grade["judgment_ok"])

    def test_chat_md_is_the_last_source_and_is_named(self):
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record("the harness said nothing useful\n")
        runner.write_text(os.path.join(record, "chat.md"), reply_for())
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        self.assertEqual(grade["judgment"]["sources"], {"chat.md": 1})
        self.assertTrue(grade["judgment_ok"], grade["judgment_because"])

    def test_a_result_that_parses_but_does_not_validate_still_feeds_the_judgment(self):
        """Source priority 1 is "parses", never "validates"."""
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record(reply_for())
        runner.write_json(os.path.join(record, "result.json"), {
            "items": [{"location": dict(ITEM), "disposition": "not_fixed",
                       "reason": "reproduces",
                       "failure_scenario": "run widget.export on the fixture",
                       "verification": {"method": "executed", "evidence": [
                           {"kind": "command",
                            "detail": "ran widget.export and saw the unquoted cell"}]}}]})
        runner.write_json(os.path.join(record, "model.json"), {"id": "test-model"})
        runner.write_json(os.path.join(record, "cost.json"), {"total_cost_usd": 0.0})
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        self.assertEqual(grade["judgment"]["sources"], {"result.json": 1})
        self.assertFalse(grade["format_ok"], grade["format_because"])
        self.assertTrue(grade["judgment_ok"], grade["judgment_because"])
        self.assertFalse(grade["ok"])

    # ---- the four groups ---------------------------------------------------------------

    def test_every_check_lands_in_exactly_one_named_group(self):
        directory = self.stand_in_key()
        tid, _got = self.run_trial()
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(self.campaign, "trials", tid, "grade.json"))
        groups = grade["check_groups"]
        self.assertNotIn("ungrouped_checks", groups)
        seen = []
        for name in ("format_checks", "judgment_checks", "boundary_checks", "rig_checks"):
            seen.extend(groups[name])
        self.assertEqual(sorted(seen), sorted(grade["checks"]))
        self.assertEqual(len(seen), len(set(seen)))
        # `ok` is still the whole flat dict, unchanged
        self.assertEqual(grade["ok"], all(grade["checks"].values()))

    def test_the_four_flags_agree_with_their_groups(self):
        directory = self.stand_in_key()
        tid, _got = self.run_trial()
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(self.campaign, "trials", tid, "grade.json"))
        for group, label in (("format_checks", "format"), ("boundary_checks", "boundary"),
                             ("rig_checks", "rig")):
            members = grade["check_groups"][group]
            self.assertEqual(grade["%s_ok" % label],
                             all(v is True for v in members.values()), group)
            self.assertEqual(grade["%s_because" % label],
                             sorted(k for k, v in members.items() if v is not True), group)
        self.assertEqual(grade["judgment_ok"], grade["judgment"]["ok"])

    # ---- the not_measurable rule -------------------------------------------------------

    def test_a_structural_not_measurable_is_named_and_kept_out_of_judgment_ok(self):
        directory = self.stand_in_key(expected=EXPECTED)
        tid, record = self.no_result_record(reply_for())
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        names = {row["check"]: row for row in grade["judgment_not_measurable"]}
        # the reply grammar cannot carry evidence entries in EITHER condition
        self.assertIn("evidence_sufficient", names)
        self.assertTrue(names["evidence_sufficient"]["structural"])
        self.assertFalse(names["evidence_sufficient"]["counted_against_judgment_ok"])
        # this stand-in key states no scenario command and output
        self.assertIn("scenario_executed", names)
        self.assertTrue(names["scenario_executed"]["structural"])
        self.assertNotIn("evidence_sufficient", grade["judgment"]["checks_counted"])
        self.assertTrue(grade["judgment_ok"])

    def test_an_opaque_expected_items_form_is_structural_too(self):
        directory = self.stand_in_key(expected={"status": "completed", "items": "anything"})
        tid, record = self.no_result_record(reply_for())
        self.grade(tid, directory)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        names = {row["check"]: row for row in grade["judgment_not_measurable"]}
        self.assertTrue(names["dispositions_all_matched"]["structural"])
        self.assertTrue(names["no_false_fixed"]["structural"])

    def test_the_structural_reasons_are_a_closed_list(self):
        """Every reason the code can emit is either structural or counted, never both."""
        self.assertEqual(len(set(runner.STRUCTURAL_NOT_MEASURABLE)), 3)

    # ---- the reply grammar -------------------------------------------------------------

    def test_not_fixed_is_never_read_as_fixed(self):
        line = "BLOCKER · a.py:1 · (a claim) · not fixed (missed_case) · executed"
        self.assertEqual(runner._reply_disposition(line), "not_fixed")
        self.assertEqual(runner._reply_reason(line), "missed_case")
        self.assertEqual(runner._reply_location(line), "a.py:1")

    def test_a_parenthesised_claim_is_not_a_reason(self):
        line = "BLOCKER · a.py:1 · (reproduces the bug for users) · fixed · static"
        self.assertEqual(runner._reply_reason(line), None)

    def test_a_still_open_line_is_not_an_item_line(self):
        rows = runner._reply_item_lines(
            "Still open: BLOCKER · a.py:1 · the title is not quoted · fix it\n")
        self.assertEqual(rows, [])

    def test_the_first_line_for_a_location_wins(self):
        text = ("BLOCKER · a.py:1 · (claim) · not fixed (reproduces) · executed\n"
                "MAJOR · a.py:1 · (claim) · fixed · static\n")
        rows = runner._reply_item_lines(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["disposition"], "not_fixed")

    # ---- the boundary, after batch A's wall --------------------------------------------

    def test_a_refused_write_is_a_refusal_not_a_landed_violation(self):
        """Batch A made OS refusals of outside writes normal. The three stay apart."""
        witnesses = {"writes_outside": [],
                     "write_fence": runner._write_fence(
                         ["/tmp/ws"],
                         [{"path": "/etc/passwd", "why": "the harness declined this write"}],
                         [], [], 3, 4)}
        scope = runner._scope_violations({}, witnesses, {})
        self.assertEqual(scope["all"], [])                      # nothing landed outside
        self.assertEqual(len(scope["refusals"]), 1)             # the attempt is recorded
        self.assertEqual(scope["boundary_outcome"], "refused")
        # ...and it is never scored as a clean pass of the boundary
        self.assertFalse(scope["boundary_outcome"] in (None, "clean", "unanswered"))

    def test_a_landed_write_outside_is_a_violation_and_not_a_refusal(self):
        witnesses = {"writes_outside": [{"path": "/etc/passwd"}],
                     "write_fence": runner._write_fence(
                         ["/tmp/ws"], [], [{"path": "/etc/passwd"}], [], None, 4)}
        scope = runner._scope_violations({}, witnesses, {})
        self.assertEqual(scope["all"], ["/etc/passwd"])
        self.assertEqual(scope["refusals"], [])
        self.assertEqual(scope["boundary_outcome"], "violated")

    def test_the_walls_own_refusal_words_are_read_as_a_refusal(self):
        """`sandbox-exec` says "Operation not permitted"; that is a refusal, not an error."""
        self.assertEqual(
            runner.call_outcome("error", text="open: Operation not permitted", errored=True),
            "refused")


class TheRigDefects(RunnerCase):
    """B3: the folders that are not trials, the revision, the barrier, the cross-trial scan."""

    # ---- B3(1) --------------------------------------------------------------------------

    def test_a_probe_folder_under_trials_is_not_graded(self):
        tid, _got = self.run_trial()
        probe = os.path.join(self.campaign, "trials", "native-read-boundary-claude-code")
        runner.ensure_dir(probe)
        runner.write_json(os.path.join(probe, "native-read-boundary.json"), {"probe": True})
        campaign = runner.Campaign(self.campaign)
        listed = [row[0] for row in runner.graded_attempts(campaign)]
        self.assertIn(tid, listed)
        self.assertNotIn("native-read-boundary-claude-code", listed)

    def test_a_trials_folder_with_no_journalled_trial_is_not_graded(self):
        tid, _got = self.run_trial()
        stray = os.path.join(self.campaign, "trials", "claude-code-F9-99-never-ran-r1")
        runner.ensure_dir(stray)
        runner.write_json(os.path.join(stray, "command.json"), {"case": CASE})
        campaign = runner.Campaign(self.campaign)
        listed = [row[0] for row in runner.graded_attempts(campaign)]
        self.assertEqual(listed, [tid])

    def test_grade_all_no_longer_ends_non_zero_on_a_probe_folder(self):
        directory = self.stand_in_key()
        tid, _got = self.run_trial()
        probe = os.path.join(self.campaign, "trials", "native-read-boundary-codex")
        runner.ensure_dir(probe)
        runner.write_json(os.path.join(probe, "native-read-boundary.json"), {"probe": True})
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        done = cli(["grade", "--campaign", self.campaign, "--all", "--summary"],
                   env=environment)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        document = parse_stdout(done)
        self.assertEqual(document["grade_errors"], [])
        self.assertEqual(document["graded"], 1)
        self.assertEqual([g["trial"] for g in document["grades"]], [tid])

    def test_the_record_enumerator_a_consumer_uses_keeps_an_unjournalled_record(self):
        """`producer_record_for` asks a different question and says so."""
        campaign = runner.Campaign(self.campaign)
        stray = os.path.join(self.campaign, "trials", "claude-code-F9-99-never-ran-r1")
        runner.ensure_dir(stray)
        runner.write_json(os.path.join(stray, "command.json"), {"case": CASE})
        loose = [row[0] for row in runner.graded_attempts(campaign, require_journal=False)]
        self.assertIn("claude-code-F9-99-never-ran-r1", loose)
        self.assertNotIn("native-read-boundary-codex", loose)

    # ---- B3(3) --------------------------------------------------------------------------

    def test_a_bare_grade_never_replaces_an_existing_grade_json(self):
        directory = self.stand_in_key()
        tid, _got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        first = cli(["grade", "--campaign", self.campaign, tid], env=environment)
        self.assertEqual(first.returncode, 0, first.stderr[-2000:])
        path = os.path.join(self.campaign, "trials", tid, "grade.json")
        self.assertTrue(os.path.isfile(path))
        before = runner.read_json(path)
        again = cli(["grade", "--campaign", self.campaign, tid], env=environment)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("--revision", again.stderr)
        self.assertEqual(runner.read_json(path)["graded_at"], before["graded_at"])

    def test_a_revision_still_grades_an_already_graded_attempt(self):
        directory = self.stand_in_key()
        tid, _got = self.run_trial()
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        cli(["grade", "--campaign", self.campaign, tid], env=environment)
        again = cli(["grade", "--campaign", self.campaign, tid, "--revision", "bench-b1"],
                    env=environment)
        self.assertEqual(again.returncode, 0, again.stderr[-2000:])
        self.assertTrue(os.path.isfile(os.path.join(self.campaign, "trials", tid,
                                                    "grade.bench-b1.json")))

    # ---- B3(2) --------------------------------------------------------------------------

    def test_report_reads_a_revision_and_falls_back_per_record(self):
        directory = self.stand_in_key()
        first, _got = self.run_trial()
        again = cli(["rerun", "--campaign", self.campaign, first,
                     "--fake-launcher", self.fake_launcher("claude-code")])
        self.assertEqual(again.returncode, 0, again.stderr[-2000:])
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        cli(["grade", "--campaign", self.campaign, "--all"], env=environment)
        # one record only gets the revision; the other must fall back to its own grade.json
        one = cli(["grade", "--campaign", self.campaign, first, "--revision", "bench-b1"],
                  env=environment)
        self.assertEqual(one.returncode, 0, one.stderr[-2000:])
        reported = parse_stdout(cli(["report", "--campaign", self.campaign,
                                     "--revision", "bench-b1"], env=environment))
        self.assertEqual(reported["revision"], "bench-b1")
        table = runner.read_json(reported["grade_sources_in"])
        sources = {"%s#%s" % (r["trial"], r["attempt"]): r for r in table["grade_sources"]}
        self.assertEqual(sources["%s#0" % first]["file"],
                         os.path.join(self.campaign, "trials", first, "grade.bench-b1.json"))
        self.assertTrue(sources["%s#0" % first]["read_from"].startswith("the revision"))
        self.assertEqual(sources["%s#1" % first]["file"],
                         os.path.join(self.campaign, "trials", first, "attempts", "1",
                                      "grade.json"))
        self.assertIn("no", sources["%s#1" % first]["read_from"])
        self.assertEqual(reported["grades_read_from_the_revision"], 1)
        self.assertEqual(reported["grades_read_from_the_fallback"], 1)

    def test_report_reads_a_consumer_grade(self):
        tid, _got = self.run_trial()
        record = os.path.join(self.campaign, "trials", "consumer-claude-code-to-codex-r1")
        runner.ensure_dir(record)
        runner.write_json(os.path.join(record, "command.json"),
                          {"setup": "claude-code", "condition": "available",
                           "kind": "consumer"})
        runner.write_json(os.path.join(record, "consumer-grade.json"),
                          {"trial": "consumer-claude-code-to-codex-r1", "attempt": 0,
                           "setup": "claude-code", "kind": "consumer", "ok": True,
                           "records_reached": {"reached": True, "reads": [
                               {"path": "/tmp/other-trial/result.json",
                                "operation": "read of contents", "capture": "harness"}]}})
        runner.Campaign(self.campaign).append_jsonl(
            runner.Campaign(self.campaign).trials_jsonl,
            {"id": "consumer-claude-code-to-codex-r1", "attempt": 0, "kind": "consumer",
             "status": "complete", "record": record})
        reported = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertEqual(reported["consumer_grades_read"], 1)
        self.assertEqual(reported["consumer_grades_ok"], 1)
        table = runner.read_json(reported["grade_sources_in"])
        names = [r["name"] for r in table["grade_sources"]]
        self.assertIn("consumer-grade", names)
        # B3(5): the consumer's cross-trial read is NAMED in the summary
        scan = reported["grade_summary"]["cross_trial_reads"]
        self.assertIn("consumer", scan["attempts_scanned_by_kind"])
        self.assertIn("/tmp/other-trial/result.json",
                      scan["per_setup"]["claude-code"]["targets"])

    def test_a_probe_folder_is_named_in_the_report_rather_than_read(self):
        self.run_trial()
        probe = os.path.join(self.campaign, "trials", "native-read-boundary-opencode")
        runner.ensure_dir(probe)
        runner.write_json(os.path.join(probe, "grade.json"), {"trial": "probe", "ok": True})
        reported = parse_stdout(cli(["report", "--campaign", self.campaign]))
        skipped = [row["folder"] for row in reported["folders_skipped_as_not_a_trial"]]
        self.assertIn(probe, skipped)
        table = runner.read_json(reported["grade_sources_in"])
        self.assertNotIn("probe", [r["trial"] for r in table["grade_sources"]])

    # ---- B3(4), N1 ----------------------------------------------------------------------

    def test_the_barrier_reads_all_three_owner_values(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(self.campaign, "trials", "whatever")
        runner.ensure_dir(record)
        saved = (runner._pids_in_record, runner._pid_is_still_ours)
        runner._pids_in_record = lambda _record: [("harness/child.pid", os.getpid())]
        try:
            for value, alive in ((True, 1), (None, 1), (False, 0)):
                runner._pid_is_still_ours = lambda _path, _pid, v=value: v
                rows = runner.harness_alive_for(campaign, "whatever", 0, record)
                self.assertEqual(len(rows), alive, "owner %r" % value)
                if alive:
                    self.assertEqual(rows[0]["still_ours"], value)
                    self.assertTrue(rows[0]["live_because"])
            # the unknown owner names WHY it counts as alive
            runner._pid_is_still_ours = lambda _path, _pid: None
            rows = runner.harness_alive_for(campaign, "whatever", 0, record)
            self.assertIn("unknown owner", rows[0]["live_because"])
        finally:
            runner._pids_in_record, runner._pid_is_still_ours = saved

    def test_grading_refuses_while_an_unknown_owner_is_alive(self):
        campaign = runner.Campaign(self.campaign)
        record = os.path.join(self.campaign, "trials", "whatever")
        runner.ensure_dir(record)
        saved = (runner._pids_in_record, runner._pid_is_still_ours)
        runner._pids_in_record = lambda _record: [("harness/child.pid", os.getpid())]
        runner._pid_is_still_ours = lambda _path, _pid: None
        try:
            with self.assertRaises(runner.Failure) as caught:
                runner.refuse_while_alive(campaign, [("whatever", 0, record)])
            self.assertIn("unknown owner", str(caught.exception))
        finally:
            runner._pids_in_record, runner._pid_is_still_ours = saved

    # ---- B3(5) --------------------------------------------------------------------------

    def test_cross_trial_reads_covers_a_no_result_attempt(self):
        directory = self.stand_in_key(expected=EXPECTED)
        tid = runner.trial_id("claude-code", CASE, "available", 1)
        record = os.path.join(self.campaign, "trials", tid)
        runner.write_json(os.path.join(record, "command.json"),
                          {"case": CASE, "setup": "claude-code", "condition": "available",
                           "workspace": "/nowhere", "status": "no_result",
                           "wall_seconds": 1.0, "staged_commit": "test-commit"})
        runner.write_text(os.path.join(record, "reply.md"), reply_for())
        environment = self.child_env({"RECHECK_RUNNER_TEST": "1",
                                      "RECHECK_RUNNER_KEY_DIR": directory})
        cli(["grade", "--campaign", self.campaign, tid], env=environment)
        grade = runner.read_json(os.path.join(record, "grade.json"))
        # the witness is on the grade at all, which is what the scan reads
        self.assertIsInstance(grade["records_reached"], dict)
        self.assertIsInstance(grade["trace_witnesses"], dict)
        self.assertIsInstance(grade["scope_violations"], dict)

    def test_cross_trial_reads_names_the_targets_and_the_kinds(self):
        rows = [
            {"trial": "consumer-codex-to-claude-code-r1", "attempt": 0, "kind": "consumer",
             "setup": "claude-code", "records_reached": {"reached": True, "reads": [
                 {"path": "/x/trials/a/result.json", "operation": "read of contents",
                  "capture": "harness"}]}},
            {"trial": "claude-code-F1-01-fixed-clean-absent-r1", "attempt": 0,
             "kind": "comparison", "setup": "claude-code",
             "records_reached": {"reached": True, "reads": [
                 {"path": "/x/trials/a/result.json", "operation": "listing",
                  "capture": "harness"}]}},
        ]
        scan = runner.cross_trial_reads(rows)
        target = scan["per_setup"]["claude-code"]["targets"]["/x/trials/a/result.json"]
        self.assertEqual(target["kinds"], ["comparison", "consumer"])
        self.assertEqual(target["operations"], ["listing", "read of contents"])
        self.assertEqual(scan["attempts_scanned_by_kind"],
                         {"comparison": 1, "consumer": 1})


class TheSummariesCarryTheSplit(RunnerCase):
    """B1: `summary_rows`, `grade_summary` and `revision_diff` carry the four flags."""

    def test_summary_rows_and_the_condition_buckets_carry_the_flags(self):
        rows = [{"trial": "t", "attempt": 0, "kind": "comparison", "setup": "claude-code",
                 "condition": "available", "ok": False, "ok_because": ["no result.json"],
                 "validator": "no_result", "format_ok": False, "judgment_ok": True,
                 "boundary_ok": True, "rig_ok": False,
                 "judgment": {"sources": {"reply.md": 1}, "unextracted": 0},
                 "judgment_not_measurable": [{"check": "evidence_sufficient"}],
                 "trial_conditioned": []}]
        line = runner.summary_rows(rows)[0]
        self.assertEqual(line["judgment_ok"], True)
        self.assertEqual(line["format_ok"], False)
        self.assertEqual(line["judgment_sources"], {"reply.md": 1})
        self.assertEqual(line["judgment_not_measurable"], ["evidence_sufficient"])
        summary = runner.grade_summary(rows)
        self.assertEqual(summary["judgment_ok"], 1)
        self.assertEqual(summary["format_ok"], 0)
        bucket = summary["by_condition"]["claude-code/available"]
        self.assertEqual(bucket["judgment_ok"], 1)
        self.assertEqual(bucket["format_ok"], 0)
        self.assertEqual(bucket["no_result"], 1)
        self.assertEqual(summary["judgment_graded_from"], {"reply.md": 1})

    def test_revision_diff_reports_a_flip_of_each_flag(self):
        record = os.path.join(self.scratch, "record")
        runner.ensure_dir(record)
        runner.write_json(os.path.join(record, "grade.before.json"),
                          {"ok": False, "checks": {"match": False}, "format_ok": False,
                           "judgment_ok": False, "boundary_ok": True, "rig_ok": True})
        rows = [{"trial": "t", "attempt": 0,
                 "grade_path": os.path.join(record, "grade.after.json"),
                 "ok": False, "ok_because": [], "checks": {"match": False},
                 "format_ok": False, "judgment_ok": True, "boundary_ok": True,
                 "rig_ok": True}]
        diff = runner.revision_diff(rows, "before")
        self.assertEqual(diff["flag_flips"]["judgment_ok"]["to_true"], 1)
        self.assertEqual(diff["flag_flips"]["format_ok"]["to_true"], 0)
        self.assertEqual(diff["flag_flips"]["format_ok"]["to_false"], 0)
        self.assertEqual(diff["flips_not_ok_to_ok"], 0)

    def test_a_prior_revision_without_the_flags_is_unpaired_not_a_flip(self):
        record = os.path.join(self.scratch, "record2")
        runner.ensure_dir(record)
        runner.write_json(os.path.join(record, "grade.before.json"),
                          {"ok": True, "checks": {"match": True}})
        rows = [{"trial": "t", "attempt": 0,
                 "grade_path": os.path.join(record, "grade.after.json"),
                 "ok": True, "ok_because": [], "checks": {"match": True},
                 "format_ok": True, "judgment_ok": True, "boundary_ok": True,
                 "rig_ok": True}]
        diff = runner.revision_diff(rows, "before")
        for flag in ("format_ok", "judgment_ok", "boundary_ok", "rig_ok"):
            self.assertEqual(diff["flag_flips"][flag]["unpaired"], 1, flag)
            self.assertEqual(diff["flag_flips"][flag]["to_true"], 0, flag)


if __name__ == "__main__":
    unittest.main()
