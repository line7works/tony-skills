"""`record-answer` (lane contract section 7, required test 6; families I2 and I3), real CLI.

The schema first (exit 4, nothing written), then the shared E14-11 refusals through
station_core/answer.py, then this core's own (exit 5, nothing written): another run's or another
session's answer, another row, a result with no reader call id (independence) or a call id this run
never built, a field the records line cannot carry, an adjudication that keeps a refuted citation.
Then verify: a citation past the end or to a file not in the packet is refuted and counted, a quote
the cited line does not carry is refuted, a locationless finding never reaches the result, the
no-record rule turns a traceability item into a QUESTION note, a Claude-lane MINOR passes
unverified; a null effective model and a lane that did not answer `ok` are stops. The verdict rule
over every severity mix is the library's (`inspect_core.verify.verdict`).
"""
import os
import unittest

import ilib
import testlib

testlib.add_scripts_to_path()

from inspect_core import verify  # noqa: E402

NEEDS = testlib.checkout_sibling("blueprint-v2") is None or testlib.records_root() is None or \
    testlib.checkout_sibling("readers") is None
R = "run-0001"


@unittest.skipIf(NEEDS, "the installed shape: no blueprint-v2, records or readers beside this core")
class _Rec(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("record-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def record(self, results, scope=ilib.SCOPE_DOC, row="claude-session", input_extra=None, **answer_extra):
        ws = ilib.workspace(self.tmp, scope=scope)
        self.run = ilib.Runner(self.tmp, ws)
        doc = ilib.make_input(ws, self.run.run_dir, row=row, **(input_extra or {}))
        self.run.upto("request", doc=doc)
        return self._record(ilib.answer(R, results, row=row, **answer_extra))

    def _record(self, answer):
        path = os.path.join(self.tmp, "answer.json")
        testlib.write_json(path, answer)
        return self.run.phase("record-answer", "--answer", path)

    def triage(self):
        return self.run.artifact("triage.json")

    def assert_refused(self, rule, outcome):
        code, doc, out, err = outcome
        self.assertEqual(code, 5, out + err)
        self.assertIn(rule, [r["rule"] for r in doc["refusals"]], doc)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")))
        self.assertEqual(self.run.artifact("checkpoint.json")["phase"], "requested")


class TheGates(_Rec):

    def test_a_schema_failure_is_exit_4_and_writes_nothing(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R), extra_key=1)
        self.assertEqual(code, 4, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")))

    def test_a_finding_with_no_reader_call_id_is_refused(self):
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("build-doc.md:10")])
        fleet[0]["call_id"] = None
        self.assert_refused("independence", self.record(fleet, lanes=["code-book", "repo-reality", "traceability"]))

    def test_a_call_id_this_run_never_built(self):
        fleet = ilib.claude_fleet(R)
        fleet[0]["call_id"] = "run-0001-my-own-reading"
        self.assert_refused("independence", self.record(fleet, lanes=["code-book", "repo-reality", "traceability"]))

    def test_another_session(self):
        self.assert_refused("session-mismatch", self.record(ilib.claude_fleet(R), session_id="someone-else"))

    def test_another_run(self):
        ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, ws)
        self.run.upto("request")
        self.assert_refused("run-mismatch", self._record(ilib.answer("run-0009", ilib.claude_fleet(R))))

    def test_another_row(self):
        ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, ws)
        self.run.upto("request")
        self.assert_refused("row-mismatch", self._record(ilib.answer(R, ilib.claude_fleet(R), row="claude-opus")))

    def test_a_result_whose_row_is_not_its_calls(self):
        fleet = ilib.claude_fleet(R)
        fleet[1]["row"] = "claude-opus"
        self.assert_refused("row-mismatch", self.record(fleet))

    def test_lanes_that_are_not_the_results_lenses(self):
        self.assert_refused("lanes-mismatch", self.record(ilib.claude_fleet(R), lanes=["traceability"]))

    def test_two_results_for_one_call(self):
        fleet = ilib.claude_fleet(R)
        fleet.append(dict(fleet[0]))
        self.assert_refused("duplicate-call", self.record(fleet))

    def test_a_claim_the_records_line_cannot_carry(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12", claim="one · two")])
        self.assert_refused("field-separator", self.record(fleet))

    def test_an_owner_word_on_a_claude_row(self):
        self.assert_refused("owner-word-mismatch", self.record(
            ilib.claude_fleet(R), owner_word={"rows": ["claude-session"], "words": "go"}))

    def test_the_shared_refusal_of_a_re_asked_decided_line(self):
        questions = [{"id": "Q1", "text": "Python 3.9 standard library only", "touches": [], "answer": "yes"}]
        self.assert_refused("re-asked-decided", self.record(ilib.claude_fleet(R), questions=questions))

    def test_an_adjudication_cannot_keep_a_refuted_citation(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:99")])
        adj = [{"finding": "%s-code-book#1" % R, "decision": "confirmed", "why": "I say so"}]
        self.assert_refused("refuted-citation", self.record(fleet, adjudications=adj))

    def test_an_adjudication_naming_no_finding(self):
        adj = [{"finding": "%s-code-book#4" % R, "decision": "refuted", "why": "none"}]
        self.assert_refused("unknown-finding", self.record(ilib.claude_fleet(R), adjudications=adj))

    def test_an_accepted_answer_is_recorded_once(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R))
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(os.path.join(self.run.run_dir, "answer.json")))
        again = self._record(ilib.answer(R, ilib.claude_fleet(R)))
        self.assertEqual(again[0], 2, "a second answer to an answered run is usage")


class Verify(_Rec):

    def test_a_citation_past_the_end_is_refuted_and_counted(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:99")]))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["counts"]["refuted"], tri["survivors"]), (1, []))
        self.assertIn("past the end", tri["refuted"][0]["why"])

    def test_a_file_not_in_the_packet_is_refuted(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R, code_book=[ilib.finding("summary.md:1")]))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.triage()["counts"]["refuted"], 1)

    def test_a_blank_cited_line_is_refuted(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:6")]))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.triage()["counts"]["refuted"], 1)

    def test_a_quote_the_line_carries_is_confirmed_one_it_does_not_is_refuted(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12", quote="AC1"),
                                                ilib.finding("build-doc.md:10", claim="R2 is wrong", quote="AC1")])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual([(s["label"], s["location"]) for s in tri["survivors"]],
                         [("CONFIRMED", ilib.BUILD_REL + ":12")])
        self.assertEqual(tri["counts"]["refuted"], 1)

    def test_no_quote_is_plausible_until_the_executor_confirms(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12"),
                                                ilib.finding("build-doc.md:13", claim="footprint misses a file")])
        adj = [{"finding": "%s-code-book#2" % R, "decision": "confirmed", "why": "the footprint names no test data"}]
        code, doc, out, err = self.record(fleet, adjudications=adj)
        self.assertEqual(code, 0, out + err)
        labels = dict((s["location"], s["label"]) for s in self.triage()["survivors"])
        self.assertEqual(labels, {ilib.BUILD_REL + ":12": "PLAUSIBLE", ilib.BUILD_REL + ":13": "CONFIRMED"})

    def test_a_locationless_finding_never_reaches_the_result(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R, code_book=[ilib.finding(None)]))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["questions"], tri["counts"]["locationless"]), ([], [], 1))

    def test_a_claude_minor_passes_unverified(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:99", severity="MINOR")]))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual([(s["severity"], s["label"]) for s in tri["survivors"]], [("MINOR", "UNVERIFIED")])

    def test_an_outside_minor_is_verified(self):
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model",
                                    findings=[ilib.finding("build-doc.md:99", severity="MINOR")]),
                 ilib.reader_result("%s-repo-reality" % R)]
        code, doc, out, err = self.record(fleet, row="gpt-astra")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.triage()["counts"]["refuted"], 1)

    def test_the_no_record_rule(self):
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("build-doc.md:10", severity="BLOCKER",
                                                               claim="R1 traces to nothing in the record")])
        code, doc, out, err = self.record(fleet, scope=None)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual(tri["survivors"], [])
        self.assertEqual([q["location"] for q in tri["questions"]], [ilib.BUILD_REL + ":10"])
        self.assertEqual(tri["counts"]["blocker"], 0)
        self.assertTrue(tri["weaker"])
        self.assertEqual(tri["verdict"], "APPROVED")

    def test_with_a_scope_doc_the_same_finding_is_a_blocker(self):
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("build-doc.md:10", severity="BLOCKER",
                                                               claim="R1 traces to nothing in the record")])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["counts"]["blocker"], tri["verdict"], tri["weaker"]), (1, "REJECTED", False))

    def test_a_question_severity_is_a_note(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:14", severity="QUESTION",
                                                             claim="was the reset deferred on purpose")])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(self.triage()["questions"]), 1)

    def test_two_lenses_on_one_line_and_claim_merge(self):
        one = ilib.finding("build-doc.md:12", quote="AC1")
        fleet = ilib.claude_fleet(R, traceability=[dict(one, severity="MINOR")], code_book=[one])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual(len(tri["survivors"]), 1)
        self.assertEqual(tri["survivors"][0]["severity"], "MAJOR")
        self.assertEqual(sorted(tri["survivors"][0]["converged"]), ["%s-code-book" % R, "%s-traceability" % R])

    def test_the_executor_refutes_and_questions(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12"), ilib.finding("build-doc.md:13", claim="c2")])
        adj = [{"finding": "%s-code-book#1" % R, "decision": "refuted", "why": "line 12 does name a verify form"},
               {"finding": "%s-code-book#2" % R, "decision": "question", "why": "the owner decides the footprint"}]
        code, doc, out, err = self.record(fleet, adjudications=adj)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["counts"]["refuted"], len(tri["questions"]), tri["survivors"]), (1, 1, []))


class Stops(_Rec):

    def test_a_null_effective_model_is_a_stop_with_no_stamp(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12")])
        fleet[1]["effective_model"] = None
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "no-effective-model"))
        self.assertIsNone(doc["station_result"]["stamp"])
        self.assertFalse(doc["station_result"]["stamp_written"])
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 2, "a stopped run writes nothing: " + out + err)

    def test_a_lane_that_did_not_answer_ok_is_lane_down(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12")])
        fleet[2]["status"] = "lane-unavailable"
        fleet[2]["reason"] = "Workflow tool absent"
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "lane-down")
        self.assertIn("lane-unavailable", doc["reason"])
        self.assertIn("Workflow tool absent", doc["reason"])
        self.assertIn("re-ask", doc["reason"])


class TheVerdictRule(unittest.TestCase):

    def test_every_severity_mix(self):
        cases = [((), "APPROVED"), (("MINOR",), "APPROVED"), (("MAJOR",), "APPROVED WITH CONDITIONS"),
                 (("MAJOR", "MINOR"), "APPROVED WITH CONDITIONS"), (("BLOCKER",), "REJECTED"),
                 (("BLOCKER", "MAJOR", "MINOR"), "REJECTED"), (("BLOCKER", "MINOR"), "REJECTED")]
        for severities, word in cases:
            self.assertEqual(verify.verdict([{"severity": s} for s in severities]), word, severities)


if __name__ == "__main__":
    unittest.main()
