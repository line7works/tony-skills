"""The recorded reviewer answer: evidence, scope, independence, and the clean-review rule.

What the core does with an answer, and what it refuses:

- **Evidence-backed findings.** A finding is recorded only with a location inside the source set,
  a claim, a scenario and an evidence kind (`executed`, `read`, `reasoned`). One missing refuses
  the whole answer (`answer_invalid`): nothing is raised and no verdict is recorded (S2-03).
- **Scope.** A finding whose location is outside the source set is kept as a note, not raised
  (S2-04). What the answer itself kept as a note stays a note (S2-02).
- **Independence.** An answer from the session that built the slice is refused
  (`refusal_reason: independence`, S3-02), and so is a finding or a verdict that cites the
  builder's conversation.
- **A clean review lists its checks.** No findings and no checks executed is a validation failure
  of the result, not a clean verdict.
- **Severity to verdict** is v1's mapping over the RAISED findings, unchanged under pick P5.

The script records what the reviewer concluded; it never re-judges the code. The mapping is
arithmetic over severities, so the core computes it and reports the reviewer's stated verdict
beside it.
"""
import copy
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import answer as ans  # noqa: E402
from signoff_core import verdict as vd  # noqa: E402

SET = ["src/signpost/columns.py", "src/signpost/pad.py", "src/signpost/render.py",
       "tests/test_columns.py"]


def finding(location="src/signpost/columns.py:9", severity="BLOCKER", kind="executed", **over):
    row = {"location": location, "severity": severity, "claim": "join joins bare",
           "scenario": "run the render case; the count line reads columns=3",
           "evidence_kind": kind}
    row.update(over)
    return row


def an_answer(findings=(), notes_kept=(), checks=1, session="sess-review-1", verdict="rejected"):
    return {
        "seeded_answer": 1, "case": "T", "role": "reviewer", "session_id": session,
        "checks_executed": [{"name": "unit", "command": "sh checks/unit.sh", "exit_code": 0,
                             "output": "Ran 2 tests\n\nOK"}][:checks],
        "findings": list(findings), "notes_kept": list(notes_kept),
        "verdict": verdict, "notes": "prose",
    }


SESSIONS = {"building": "sess-build-1", "reviewing": "sess-review-1"}


class EvidenceIsRequired(unittest.TestCase):
    def test_a_complete_finding_is_raised(self):
        got = ans.adjudicate(an_answer([finding()]), SET, SESSIONS, withheld_lines=())
        self.assertTrue(got["ok"])
        self.assertEqual([r["location"] for r in got["raised"]], ["src/signpost/columns.py:9"])
        self.assertEqual(got["raised"][0]["evidence_kind"], "executed")

    def test_a_finding_with_no_evidence_kind_refuses_the_whole_answer(self):
        bad = finding()
        del bad["evidence_kind"]
        got = ans.adjudicate(an_answer([bad]), SET, SESSIONS, withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "answer_invalid")
        self.assertEqual(got["raised"], [])
        self.assertIsNone(got["verdict"])
        self.assertTrue(any("evidence_kind" in problem["why"] for problem in got["problems"]))

    def test_each_of_the_four_required_fields_refuses_when_absent(self):
        for field in ("location", "claim", "scenario", "evidence_kind"):
            bad = finding()
            del bad[field]
            got = ans.adjudicate(an_answer([bad]), SET, SESSIONS, withheld_lines=())
            self.assertFalse(got["ok"], field)
            self.assertEqual(got["refusal_reason"], "answer_invalid", field)

    def test_an_evidence_kind_outside_the_three_is_refused(self):
        got = ans.adjudicate(an_answer([finding(kind="vibes")]), SET, SESSIONS, withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "answer_invalid")

    def test_a_refused_answer_is_neither_acted_on_nor_repaired(self):
        bad = finding()
        del bad["evidence_kind"]
        original = copy.deepcopy(bad)
        got = ans.adjudicate(an_answer([bad]), SET, SESSIONS, withheld_lines=())
        self.assertEqual(bad, original, "the answer is not edited into shape")
        self.assertEqual(got["raised"], [])
        self.assertEqual(got["notes"], [])


class ScopeDecidesRaisedFromNote(unittest.TestCase):
    def test_a_location_outside_the_set_is_kept_as_a_note(self):
        out = finding(location="src/signpost/__init__.py:1", severity="MINOR", kind="read")
        got = ans.adjudicate(an_answer([finding(), out]), SET, SESSIONS, withheld_lines=())
        self.assertTrue(got["ok"])
        self.assertEqual([r["location"] for r in got["raised"]], ["src/signpost/columns.py:9"])
        self.assertEqual([r["location"] for r in got["notes"]], ["src/signpost/__init__.py:1"])
        self.assertEqual(got["notes"][0]["why"], "the location is outside the source set")

    def test_what_the_answer_kept_as_a_note_stays_a_note(self):
        kept = finding(location="src/signpost/pad.py:6", severity="MAJOR")
        got = ans.adjudicate(an_answer([finding()], notes_kept=[kept]), SET, SESSIONS,
                             withheld_lines=())
        self.assertEqual([r["location"] for r in got["notes"]], ["src/signpost/pad.py:6"])
        self.assertEqual(got["notes"][0]["why"], "the reviewer kept it as a note")

    def test_a_location_with_no_file_part_is_refused(self):
        got = ans.adjudicate(an_answer([finding(location="somewhere in the joiner")]), SET,
                             SESSIONS, withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "answer_invalid")


class IndependenceIsAHardRule(unittest.TestCase):
    def test_the_building_session_may_not_record_a_verdict(self):
        same = {"building": "sess-build-1", "reviewing": "sess-build-1"}
        got = ans.adjudicate(an_answer(session="sess-build-1", verdict="signed off"), SET, same,
                             withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "independence")
        self.assertIsNone(got["verdict"])

    def test_an_answer_whose_session_is_the_building_session_is_refused(self):
        """Even when the input's two session ids differ, the answer's own id decides."""
        got = ans.adjudicate(an_answer(session="sess-build-1", verdict="signed off"), SET,
                             SESSIONS, withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "independence")

    def test_a_finding_that_cites_the_builders_conversation_is_refused(self):
        withheld = ("I already ran the separator case by hand and it renders two columns.",)
        cited = finding(scenario="the builder states: I already ran the separator case by hand "
                                 "and it renders two columns.")
        got = ans.adjudicate(an_answer([cited]), SET, SESSIONS, withheld_lines=withheld)
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "independence")
        self.assertEqual(got["raised"], [])

    def test_a_verdict_that_cites_the_builders_conversation_is_refused(self):
        withheld = ("Sign this slice off as built.",)
        a = an_answer(verdict="signed off")
        a["notes"] = "Sign this slice off as built."
        got = ans.adjudicate(a, SET, SESSIONS, withheld_lines=withheld)
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "independence")


class ACleanReviewListsItsChecks(unittest.TestCase):
    def test_no_findings_with_checks_executed_is_clean(self):
        got = ans.adjudicate(an_answer(verdict="signed off"), SET, SESSIONS, withheld_lines=())
        self.assertTrue(got["ok"])
        self.assertTrue(got["clean_review_checks_listed"])
        self.assertEqual(got["verdict"], "signed off")

    def test_no_findings_and_no_checks_is_not_a_clean_verdict(self):
        got = ans.adjudicate(an_answer(checks=0, verdict="signed off"), SET, SESSIONS,
                             withheld_lines=())
        self.assertFalse(got["clean_review_checks_listed"])
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "answer_invalid")

    def test_a_check_with_no_output_does_not_count_as_listed(self):
        a = an_answer(verdict="signed off")
        a["checks_executed"][0]["output"] = ""
        got = ans.adjudicate(a, SET, SESSIONS, withheld_lines=())
        self.assertFalse(got["clean_review_checks_listed"])


class SeverityToVerdict(unittest.TestCase):
    """v1 signoff's table, unchanged under pick P5."""

    def test_the_three_rows(self):
        self.assertEqual(vd.verdict_for([]), "signed off")
        self.assertEqual(vd.verdict_for(["MINOR"]), "signed off")
        self.assertEqual(vd.verdict_for(["MAJOR", "MINOR"]), "signed off with conditions")
        self.assertEqual(vd.verdict_for(["BLOCKER", "MAJOR"]), "rejected")

    def test_a_note_never_moves_the_verdict(self):
        out = finding(location="src/signpost/__init__.py:1", severity="BLOCKER", kind="read")
        got = ans.adjudicate(an_answer([out], verdict="signed off"), SET, SESSIONS,
                             withheld_lines=())
        self.assertEqual(got["raised"], [])
        self.assertEqual(got["verdict"], "signed off")

    def test_the_reviewers_stated_verdict_is_recorded_beside_the_mapping(self):
        got = ans.adjudicate(an_answer([finding()], verdict="signed off"), SET, SESSIONS,
                             withheld_lines=())
        self.assertEqual(got["verdict"], "rejected")
        self.assertEqual(got["verdict_stated"], "signed off")
        self.assertFalse(got["verdict_matches_mapping"])


class TheSeededAnswersLoadAndAdjudicate(unittest.TestCase):
    """Each family's recorded replies, fed exactly as the case supplies them."""

    def answer_file(self, family, case_id):
        return testlib.load_json(os.path.join(testlib.SEEDED, family, "answers", case_id + ".json"))

    def test_s2_03_is_refused_as_answer_invalid(self):
        a = self.answer_file("S2-evidence", "S2-03-no-evidence-kind")
        got = ans.adjudicate(a, SET, SESSIONS, withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "answer_invalid")

    def test_s2_04_raises_the_in_set_finding_and_notes_the_other(self):
        a = self.answer_file("S2-evidence", "S2-04-location-outside-set")
        got = ans.adjudicate(a, SET, SESSIONS, withheld_lines=())
        self.assertTrue(got["ok"])
        self.assertEqual([r["location"] for r in got["raised"]], ["src/signpost/columns.py:9"])
        self.assertIn("src/signpost/__init__.py:1", [r["location"] for r in got["notes"]])
        self.assertEqual(got["verdict"], "rejected")

    def test_s3_02_is_refused_for_independence(self):
        a = self.answer_file("S3-independence", "S3-02-same-session")
        same = {"building": "sess-build-1", "reviewing": "sess-build-1"}
        got = ans.adjudicate(a, SET, same, withheld_lines=())
        self.assertFalse(got["ok"])
        self.assertEqual(got["refusal_reason"], "independence")


if __name__ == "__main__":
    unittest.main()
