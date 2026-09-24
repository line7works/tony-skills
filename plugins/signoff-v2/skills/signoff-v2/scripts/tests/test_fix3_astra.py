"""E13 slice 2, the last fix round: what Astra's recheck left in the signoff core, rebuilt as tests.

Her probe scripts are not available to this round; `astra-recheck-slice-2.md` names each probe's
shape and printed output. Each class rebuilds that shape through the real CLI in front of the real
component. The class docstring names her item. Written red first; the red output is kept in the
round's scratch folder.
"""
import json
import os
import shutil
import unittest

import shimlib
import testlib
from test_fix2_astra import DOC, _Case, kinds, read_log

testlib.add_scripts_to_path()

RANGED = "src/signpost/pad.py:1-2"


def ranged_answer(answer):
    answer = json.loads(json.dumps(answer))
    answer["findings"][0]["location"] = RANGED
    return answer


class N1ANativeRangedReviewPassesTheNextSignoff(_Case):
    """N1 (MAJOR). The first signoff raises a ranged finding and places the component's rendered
    review line, which keeps the range (F9). The next signoff's Appendix A detector read that
    NATIVE line with the legacy grammar and stopped `missing_input / legacy_ambiguous`. Astra's
    `probe_fix_edges.py`: `next signoff: missing_input / legacy_ambiguous`. Native occurrences are
    identified through the records CLI and consumed once; the unchanged stop applies to the rest."""

    def second_run(self, name="second"):
        """A second signoff run on the same document, from scope to record."""
        run_dir = os.path.join(self.case, "run-" + name)
        doc = testlib.load_json(self.input_path)
        doc["invocation"]["run_id"] = "signoff-fix3-" + name
        doc["invocation"]["run_dir"] = run_dir
        path = testlib.write_json(os.path.join(self.case, "signoff-input-%s.json" % name), doc)
        code, body, err = self.phase(["check-input", path])
        self.assertEqual(code, 0, err or json.dumps(body))
        code, body, err = self.phase(["scope", "--run-dir", run_dir])
        result_path = os.path.join(run_dir, "result.json")
        result = testlib.load_json(result_path) if os.path.isfile(result_path) else None
        return code, body, err, result

    def first_ranged_signoff(self):
        code, body, err = self.through_answer(ranged_answer(self.answer()))
        self.assertEqual(code, 0, err or json.dumps(body))
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertIn(RANGED, self.doc_text(), "records keeps the range on the review line (F9)")

    def test_the_next_signoff_proceeds_over_the_rendered_ranged_line(self):
        self.first_ranged_signoff()
        code, body, err, result = self.second_run()
        self.assertEqual(code, 0, "%s %s %s" % (err, json.dumps(body), json.dumps(result)[:1500]))
        self.assertIsNone(result, "scope wrote no terminal result")

    def test_a_hand_written_ranged_line_still_stops(self):
        """Only lines the component rendered are accepted, and only because the CLI says so."""
        self.first_ranged_signoff()
        text = self.doc_text()
        line = [row for row in text.split("\n") if RANGED in row][0]
        # another claim, so the importer reads it as news rather than as a second raise of the
        # native finding: the component recognises its own line, and the station sets aside that
        # one line only, and stops on the hand-written one
        by_hand = line.replace("(pad() returns", "(pad() still returns")
        self.assertNotEqual(by_hand, line)
        self.write(DOC, text + "\n### 2026-09-22 — review: Slice D\n%s\n" % by_hand)
        testlib.git(self.workspace, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-qam", "a hand-written ranged review")
        before = read_log(self.workspace)
        code, body, err, result = self.second_run()
        self.assertEqual(code, 10, err or json.dumps(body))
        self.assertEqual(result["status"], "missing_input")
        self.assertEqual(result["stop_reason_code"], "legacy_ambiguous")
        self.assertIn(by_hand, result["stop_reason"])
        self.assertNotIn("%s:%d" % (DOC, text.split("\n").index(line) + 1), result["stop_reason"],
                         "the rendered line itself is not named")
        self.assertEqual(read_log(self.workspace), before)


class F7AnIdentityFailureDuringRecoveryEndsInANamedStop(_Case):
    """F7 remainder (MAJOR). Astra's `probe_recovery_and_child.py`: identity computation failing
    while `record` recovers a killed run exited 1 with `ScopeUnavailable` and no `result.json`.
    Every identity computation on the recovery path ends in a terminal result."""

    def test_identity_fails_while_record_recovers_a_killed_run(self):
        self.through_answer()
        shimlib.fault(self.fault, command="append", kind="finding_raised", action="kill_after")
        code, body, err = self.record()
        self.assertNotEqual(code, 10, "the run was killed after its findings append")
        shimlib.disarm(self.fault)
        git_dir = os.path.join(self.workspace, ".git")
        shutil.move(git_dir, git_dir + ".hidden")
        try:
            code, body, err = self.record()
        finally:
            shutil.move(git_dir + ".hidden", git_dir)
        self.assertNotIn("Traceback", err)
        self.assertEqual(code, 10, err or json.dumps(body))
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "result.json")), err)
        result = self.result()
        self.assertEqual(result["status"], "recording_failed", json.dumps(result)[:1500])
        self.assertEqual(result["stop_reason_code"], "identity_refused")
        # punch-F2 (E13 punch list) replaced this assertion: before a stop is delivered, an append
        # the receipt holds as `unknown` is asked about in the log (read-only), so the killed
        # findings append, which the log holds, is reported landed and recovered, never appended.
        self.assertEqual([(row["name"], row["recovered"]) for row in result["records"]["appended"]],
                         [("findings", True)],
                         "the killed append the log holds is reported landed, found on recovery")
        self.assertTrue(result["receipt"], "the receipt that recovery settles later is named")
        self.assertEqual(len(kinds(self.workspace, "finding_raised")), 1)
        # with git answering again, the next `record` recovers: the append is settled, not repeated
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertIn("findings", result["recovered"])
        self.assertEqual(len(kinds(self.workspace, "finding_raised")), 1)


if __name__ == "__main__":
    unittest.main()
