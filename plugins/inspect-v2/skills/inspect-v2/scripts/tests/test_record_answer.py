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
WORD = {"rows": ["gpt-astra"], "words": "send it to gpt-astra"}


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

    def outside_fleet(self, status=None):
        paper = ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model",
                                   findings=[ilib.finding("build-doc.md:12", quote="AC1")])
        if status:
            paper["status"], paper["reason"] = status, "no authorized flag on the request"
        return [paper, ilib.reader_result("%s-repo-reality" % R)]

    def test_an_outside_result_the_input_never_authorized_is_refused(self):
        # R4 (CI1-4): readers sends nothing for an outside row without the owner's word, so a result
        # that claims it did is refused, and nothing is raised or stamped under that row's name
        outcome = self.record(self.outside_fleet(), row="gpt-astra")
        self.assert_refused("unauthorized-send", outcome)
        refusal = [r for r in outcome[1]["refusals"] if r["rule"] == "unauthorized-send"][0]
        self.assertIn("gpt-astra", refusal["message"])
        self.assertEqual(refusal["call_id"], "%s-gpt-astra" % R)
        self.assertFalse(os.path.exists(os.path.join(self.run.ws, "docs", "records")))

    def test_a_word_for_another_row_authorizes_nothing(self):
        other = {"rows": ["gemini"], "words": "gemini only"}
        self.assert_refused("unauthorized-send", self.record(
            self.outside_fleet(), row="gpt-astra", input_extra={"owner_word": other}, owner_word=other))

    def test_the_same_result_with_the_word_is_accepted(self):
        code, doc, out, err = self.record(self.outside_fleet(), row="gpt-astra",
                                          input_extra={"owner_word": WORD}, owner_word=WORD,
                                          adjudications=[ilib.adjudication("%s-gpt-astra#1" % R)])
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.triage()["calls"][0]["authorized"], True)

    def test_an_unauthorized_call_readers_refused_is_lane_down_not_a_refusal(self):
        code, doc, out, err = self.record(self.outside_fleet(status="invalid-request"), row="gpt-astra")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "lane-down")

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

    def test_a_quote_the_line_does_not_carry_is_refuted_one_it_carries_is_the_executors_to_judge(self):
        # round 5, R1: a quote the line carries shows only that the text exists; the label is the adjudication
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12", quote="AC1"),
                                                ilib.finding("build-doc.md:10", claim="R2 is wrong", quote="AC1")])
        code, doc, out, err = self.record(fleet, adjudications=[ilib.adjudication("%s-code-book#1" % R)])
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual([(s["label"], s["location"]) for s in tri["survivors"]],
                         [("CONFIRMED", ilib.BUILD_REL + ":12")])
        self.assertEqual(tri["counts"]["refuted"], 1)

    def test_the_label_is_the_executors_adjudication(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12"),
                                                ilib.finding("build-doc.md:13", claim="footprint misses a file")])
        adj = [{"finding": "%s-code-book#1" % R, "decision": "plausible", "why": "likely, not shown"},
               {"finding": "%s-code-book#2" % R, "decision": "confirmed", "why": "the footprint names no test data"}]
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
        code, doc, out, err = self.record(ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:13", severity="MINOR")]))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual([(s["severity"], s["label"], s["location"]) for s in tri["survivors"]],
                         [("MINOR", "UNVERIFIED", ilib.BUILD_REL + ":13")])

    def test_a_claude_minor_or_question_whose_citation_fails_is_refuted_never_raised(self):
        # R5 (CI1-5): every finding written anywhere names a place in the workspace; a citation that
        # matches nothing is refuted and counted even where the claim itself passes unverified
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:500", severity="MINOR", claim="minor past end"),
                                                ilib.finding("summary.md:2", severity="QUESTION", claim="a question nowhere")])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["questions"], tri["counts"]["refuted"]), ([], [], 2))
        self.assertEqual(sorted(r["location"] for r in tri["refuted"]), ["build-doc.md:500", "summary.md:2"])

    def test_an_outside_minor_is_verified(self):
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model",
                                    findings=[ilib.finding("build-doc.md:99", severity="MINOR")]),
                 ilib.reader_result("%s-repo-reality" % R)]
        code, doc, out, err = self.record(fleet, row="gpt-astra", input_extra={"owner_word": WORD},
                                          owner_word=WORD)
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
        code, doc, out, err = self.record(fleet, adjudications=[ilib.adjudication("%s-traceability#1" % R)])
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
        code, doc, out, err = self.record(fleet, adjudications=[ilib.adjudication("%s-code-book#1" % R)])
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


class WhereACitationMayPoint(_Rec):
    """CI1-7: the records log is read through the component only, never by a citation check.
    CI1-13: a citation is checked against the documents that lens's request carried."""

    def test_a_repo_reality_citation_into_the_records_log_is_refuted(self):
        ws = ilib.workspace(self.tmp)
        event = {"v": 1, "kind": "finding_raised", "at": "2026-09-25T11:00:00Z", "ledger_doc": ilib.BUILD_REL,
                 "slice": "A", "severity": "MINOR",
                 "location": {"raw": ilib.BUILD_REL + ":8", "file": ilib.BUILD_REL, "line": 8, "line_end": None,
                              "tag": None, "more": [], "resolved": True},
                 "claim": "an earlier finding", "scenario": "it is in the log", "raised_by": "someone",
                 "actor": {"station": "another-station", "run_id": "other-run", "harness": None},
                 "origin": {"kind": "native"}, "source": {"known": False}}
        events = os.path.join(self.tmp, "events.json")
        testlib.write_json(events, [event])
        code, body, err = ilib.records_cli(["append", "--workspace", ws, "--doc", ilib.BUILD_REL, "--events", events,
                                            "--expect-head", "0" * 64])
        self.assertEqual(code, 0, err)
        log = body["log"]
        self.run = ilib.Runner(self.tmp, ws)
        self.run.upto("request")
        fleet = ilib.claude_fleet(R, repo_reality=[ilib.finding("%s:1" % log, quote="finding_raised"),
                                                   ilib.finding("./%s:1" % log, claim="c2", quote="finding_raised")])
        code, doc, out, err = self._record(ilib.answer(R, fleet))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["counts"]["refuted"]), ([], 2))
        self.assertIn("records log", tri["refuted"][0]["why"])

    def test_a_lens_cites_only_the_documents_its_request_carried(self):
        fleet = ilib.claude_fleet(R, repo_reality=[ilib.finding("scope-doc.md:3", claim="c1")],
                                  traceability=[ilib.finding("code-book.md:1", claim="c2")],
                                  code_book=[ilib.finding("scope-doc.md:3", claim="c3")])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["counts"]["refuted"]), ([], 3))
        self.assertTrue(all("not among the documents" in r["why"] for r in tri["refuted"]), tri["refuted"])

    def test_the_paper_call_cites_any_of_the_three(self):
        word = {"rows": ["gpt-astra"], "words": "send it"}
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model", findings=[
            ilib.finding("code-book.md:1", claim="c1"), ilib.finding("scope-doc.md:3", claim="c2"),
            ilib.finding("build-doc.md:12", claim="c3")]), ilib.reader_result("%s-repo-reality" % R)]
        code, doc, out, err = self.record(fleet, row="gpt-astra", input_extra={"owner_word": word}, owner_word=word,
                                          adjudications=[ilib.adjudication("%s-gpt-astra#%d" % (R, n)) for n in (1, 2, 3)])
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((len(tri["survivors"]), tri["counts"]["refuted"]), (3, 0))


class TheDocumentAPacketFileStandsFor(_Rec):
    """Round 3, R2 (CI1-5's class): every packet file the packet can hold (`build-doc.md`, `scope-doc.md`,
    `no-record.md`, `code-book.md`) maps to the document it stands for; a citation of `no-record.md`
    becomes a QUESTION note naming the scope doc's absence, never a packet file name in the build doc;
    a citation of a packet file the packet does not hold, or of any other name, is refuted."""

    HARVEST = {"build_doc": {"rel": ilib.BUILD_REL}, "scope_doc": {"label": ilib.SCOPE_REL}}

    def where(self, name, line=3):
        return {"kind": "packet", "file": name, "start": line, "end": line}

    def test_translate_maps_each_packet_file(self):
        self.assertEqual(verify.translate(self.where("build-doc.md"), self.HARVEST), ilib.BUILD_REL + ":3")
        self.assertEqual(verify.translate(self.where("scope-doc.md"), self.HARVEST), ilib.SCOPE_REL + ":3")
        self.assertEqual(verify.translate(self.where("code-book.md"), self.HARVEST), "skills/blueprint-v2/SKILL.md:3")
        no_scope = {"build_doc": {"rel": ilib.BUILD_REL}, "scope_doc": None}
        self.assertEqual(verify.translate(self.where("no-record.md", 1), no_scope), verify.NO_SCOPE_DOC + ":1")
        self.assertNotIn("no-record.md", verify.NO_SCOPE_DOC)

    def test_translate_names_nothing_for_a_file_the_packet_does_not_hold_or_an_unknown(self):
        no_scope = {"build_doc": {"rel": ilib.BUILD_REL}, "scope_doc": None}
        self.assertIsNone(verify.translate(self.where("scope-doc.md"), no_scope))
        self.assertIsNone(verify.translate(self.where("no-record.md", 1), self.HARVEST))
        self.assertIsNone(verify.translate(self.where("packet.md"), self.HARVEST))
        self.assertIsNone(verify.translate(self.where("summary.md"), self.HARVEST))

    def test_a_no_record_citation_is_a_question_naming_the_scope_docs_absence(self):
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("no-record.md:1", severity="BLOCKER",
                                                               claim="R1 traces to nothing in the record")])
        code, doc, out, err = self.record(fleet, scope=None)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["counts"]["refuted"]), ([], 0))
        self.assertEqual(len(tri["questions"]), 1)
        q = tri["questions"][0]
        self.assertEqual(q["location"], verify.NO_SCOPE_DOC + ":1")
        self.assertIn("no scope doc", q["what"])
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(os.path.join(self.run.ws, ilib.BUILD_REL))
        self.assertNotIn("no-record.md", text)
        lines = [l for l in text.splitlines() if l.startswith("QUESTION")]
        self.assertEqual(len(lines), 1, text)
        self.assertIn(verify.NO_SCOPE_DOC + ":1", lines[0])

    def test_an_outside_no_record_citation_of_any_lens_is_a_question(self):
        word = {"rows": ["gpt-astra"], "words": "send it"}
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model", findings=[
            ilib.finding("no-record.md:1", severity="MAJOR", claim="the plan names no record", lens="code-book")]),
            ilib.reader_result("%s-repo-reality" % R)]
        code, doc, out, err = self.record(fleet, scope=None, row="gpt-astra", input_extra={"owner_word": word},
                                          owner_word=word)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], [q["location"] for q in tri["questions"]]),
                         ([], [verify.NO_SCOPE_DOC + ":1"]))

    def test_a_packet_file_the_packet_does_not_hold_is_refuted(self):
        # no scope doc: the packet holds no-record.md, so scope-doc.md matches nothing, for every lens,
        # repo reality included, even when the workspace happens to hold a file of that name
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("scope-doc.md:1", claim="c1")],
                                  repo_reality=[ilib.finding("scope-doc.md:1", claim="c2", severity="MINOR")])
        ws = ilib.workspace(self.tmp, scope=None, extra={"scope-doc.md": "a file of the repo\n"})
        self.run = ilib.Runner(self.tmp, ws)
        self.run.upto("request")
        code, doc, out, err = self._record(ilib.answer(R, fleet))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["questions"], tri["counts"]["refuted"]), ([], [], 2))

    def test_no_record_md_in_a_run_with_a_scope_doc_is_refuted(self):
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("no-record.md:1", claim="c1")])
        code, doc, out, err = self.record(fleet)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["questions"], tri["counts"]["refuted"]), ([], [], 1))

    def test_an_unknown_packet_name_is_refuted(self):
        word = {"rows": ["gpt-astra"], "words": "send it"}
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model", findings=[
            ilib.finding("packet.md:3", claim="c1", severity="MINOR")]), ilib.reader_result("%s-repo-reality" % R)]
        code, doc, out, err = self.record(fleet, row="gpt-astra", input_extra={"owner_word": word}, owner_word=word)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["counts"]["refuted"]), ([], 1))


class ALinkToTheRecordsLog(_Rec):
    """Round 3, R3 (CI1-7): a file symlink or a hard link to the records log is caught as the folder link
    is: the log is read through the component only, never opened by a citation check."""

    def test_a_file_link_and_a_hard_link_to_the_log_are_refuted(self):
        ws = ilib.workspace(self.tmp)
        event = {"v": 1, "kind": "finding_raised", "at": "2026-09-25T11:00:00Z", "ledger_doc": ilib.BUILD_REL,
                 "slice": "A", "severity": "MINOR",
                 "location": {"raw": ilib.BUILD_REL + ":8", "file": ilib.BUILD_REL, "line": 8, "line_end": None,
                              "tag": None, "more": [], "resolved": True},
                 "claim": "an earlier finding", "scenario": "it is in the log", "raised_by": "someone",
                 "actor": {"station": "another-station", "run_id": "other-run", "harness": None},
                 "origin": {"kind": "native"}, "source": {"known": False}}
        events = os.path.join(self.tmp, "events.json")
        testlib.write_json(events, [event])
        code, body, err = ilib.records_cli(["append", "--workspace", ws, "--doc", ilib.BUILD_REL, "--events", events,
                                            "--expect-head", "0" * 64])
        self.assertEqual(code, 0, err)
        log = os.path.join(ws, body["log"])
        os.symlink(log, os.path.join(ws, "log-link.jsonl"))
        os.makedirs(os.path.join(ws, "deep"))
        os.symlink(os.path.relpath(log, os.path.join(ws, "deep")), os.path.join(ws, "deep", "x.txt"))
        os.link(log, os.path.join(ws, "hard-copy.jsonl"))
        self.run = ilib.Runner(self.tmp, ws)
        self.run.upto("request")
        fleet = ilib.claude_fleet(R, repo_reality=[
            ilib.finding("log-link.jsonl:1", claim="c1", quote="finding_raised"),
            ilib.finding("deep/x.txt:1", claim="c2", quote="finding_raised"),
            ilib.finding("hard-copy.jsonl:1", claim="c3", quote="finding_raised"),
            ilib.finding("src/turnstile.py:2", claim="c4", quote="return n + 1")])
        code, doc, out, err = self._record(ilib.answer(R, fleet, adjudications=[
            ilib.adjudication("%s-repo-reality#4" % R)]))
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual([s["location"] for s in tri["survivors"]], ["src/turnstile.py:2"])
        self.assertEqual(tri["counts"]["refuted"], 3)
        self.assertTrue(all("records log" in r["why"] for r in tri["refuted"]), tri["refuted"])


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


class EveryKeptFindingCarriesTheExecutorsJudgment(_Rec):
    """Round 5, R1 (F1): a matching citation establishes only that the cited text exists. Every outside
    finding and every Claude-lane BLOCKER or MAJOR whose citation holds carries the executor's
    adjudication before it survives; `record-answer` refuses a missing one (exit 5,
    `missing-adjudication`) before any write, and CONFIRMED and PLAUSIBLE come only from it. An invalid
    citation is still refuted mechanically and counted, a locationless concern is still excluded, and
    the no-record rule still turns a traceability item into a QUESTION note, none of them adjudicated."""

    FALSE = dict(claim="AC1 has no verify clause", quote="verify: new test at tests/test_turnstile.py")

    def assert_missing(self, outcome, *finding_ids):
        self.assert_refused("missing-adjudication", outcome)
        named = sorted(r["finding"] for r in outcome[1]["refusals"] if r["rule"] == "missing-adjudication")
        self.assertEqual(named, sorted(finding_ids), outcome[1])
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "triage.json")))
        self.assertFalse(os.path.exists(os.path.join(self.run.ws, "docs", "records")))
        self.assertEqual(self.run.phase("write")[0], 2, "a refused answer leaves the run where it was")

    def test_a_false_claim_quoting_a_real_line_is_refused_unadjudicated(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12", severity="BLOCKER", **self.FALSE)])
        self.assert_missing(self.record(fleet), "%s-code-book#1" % R)

    def test_a_claude_major_with_no_quote_is_refused_unadjudicated(self):
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("build-doc.md:10")])
        self.assert_missing(self.record(fleet), "%s-traceability#1" % R)

    def test_an_outside_finding_of_every_severity_is_refused_unadjudicated(self):
        findings = [ilib.finding("build-doc.md:12", severity=s, claim="c-%s" % s, quote="AC1")
                    for s in ("BLOCKER", "MAJOR", "MINOR", "QUESTION")]
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model", findings=findings),
                 ilib.reader_result("%s-repo-reality" % R)]
        outcome = self.record(fleet, row="gpt-astra", input_extra={"owner_word": WORD}, owner_word=WORD)
        self.assert_missing(outcome, *["%s-gpt-astra#%d" % (R, n) for n in (1, 2, 3, 4)])

    def test_the_refusal_names_every_missing_one_and_only_those(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12"),
                                                ilib.finding("build-doc.md:13", claim="c2"),
                                                ilib.finding("build-doc.md:13", claim="c3", severity="MINOR")])
        outcome = self.record(fleet, adjudications=[ilib.adjudication("%s-code-book#1" % R)])
        self.assert_missing(outcome, "%s-code-book#2" % R)

    def test_confirmed_and_plausible_come_only_from_the_adjudication(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12", quote="AC1"),
                                                ilib.finding("build-doc.md:13", claim="c2")])
        adj = [ilib.adjudication("%s-code-book#1" % R, "plausible", "the quote is there; the claim is unproven"),
               ilib.adjudication("%s-code-book#2" % R, "confirmed", "the footprint names no test data")]
        code, doc, out, err = self.record(fleet, adjudications=adj)
        self.assertEqual(code, 0, out + err)
        labels = dict((s["location"], s["label"]) for s in self.triage()["survivors"])
        self.assertEqual(labels, {ilib.BUILD_REL + ":12": "PLAUSIBLE", ilib.BUILD_REL + ":13": "CONFIRMED"})

    def test_a_refuted_adjudication_drops_the_false_claim_and_counts_it(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12", severity="BLOCKER", **self.FALSE)])
        adj = [ilib.adjudication("%s-code-book#1" % R, "refuted", "line 12 carries its verify clause")]
        code, doc, out, err = self.record(fleet, adjudications=adj)
        self.assertEqual(code, 0, out + err)
        tri = self.triage()
        self.assertEqual((tri["survivors"], tri["counts"]["refuted"], tri["verdict"]), ([], 1, "APPROVED"))

    def test_what_needs_no_adjudication(self):
        # an invalid citation (refuted mechanically), a locationless concern (excluded), a Claude MINOR
        # (unverified), a Claude QUESTION (a note), and, with no scope doc, a traceability BLOCKER (the
        # no-record rule's QUESTION note)
        fleet = ilib.claude_fleet(R, traceability=[ilib.finding("build-doc.md:10", severity="BLOCKER", claim="t1")],
                                  code_book=[ilib.finding("build-doc.md:99", severity="BLOCKER", claim="c1"),
                                             ilib.finding(None, severity="MAJOR", claim="c2"),
                                             ilib.finding("build-doc.md:13", severity="MINOR", claim="c3"),
                                             ilib.finding("build-doc.md:14", severity="QUESTION", claim="c4")])
        code, doc, out, err = self.record(fleet, scope=None)
        self.assertEqual(code, 0, out + err)
        c = self.triage()["counts"]
        self.assertEqual((c["refuted"], c["locationless"], c["unverified"], c["questions"], c["blocker"]),
                         (1, 1, 1, 2, 0))


class TheWholeFleet(_Rec):
    """Round 5, R2 (F2): a recorded fleet holds exactly one result for every call `request` built. A
    missing call ends the run `lane-down`, names the missing call ids and re-asks; nothing is triaged,
    raised or stamped. `lanes` is compared with the lenses of the BUILT requests, never the results."""

    def assert_lane_down(self, outcome, *missing):
        code, doc, out, err = outcome
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "lane-down"))
        for call_id in missing:
            self.assertIn(call_id, doc["reason"])
        self.assertIn("re-ask", doc["reason"])
        self.assertIsNone(doc["station_result"]["stamp"])
        self.assertFalse(doc["station_result"]["stamp_written"])
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "triage.json")))
        self.assertFalse(os.path.exists(os.path.join(self.run.ws, "docs", "records")))
        self.assertEqual(self.run.phase("write")[0], 2, "a stopped run writes nothing")

    def test_one_result_of_three_is_lane_down(self):
        self.assert_lane_down(self.record([ilib.reader_result("%s-traceability" % R)]),
                              "%s-code-book" % R, "%s-repo-reality" % R)

    def test_one_result_of_three_with_every_lane_listed_is_lane_down(self):
        outcome = self.record([ilib.reader_result("%s-traceability" % R)],
                              lanes=["code-book", "repo-reality", "traceability"])
        self.assert_lane_down(outcome, "%s-code-book" % R, "%s-repo-reality" % R)

    def test_an_outside_fleet_without_its_repo_reality_call_is_lane_down(self):
        paper = ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model")
        outcome = self.record([paper], row="gpt-astra", input_extra={"owner_word": WORD}, owner_word=WORD)
        self.assert_lane_down(outcome, "%s-repo-reality" % R)

    def test_lanes_are_the_built_requests_lenses(self):
        outcome = self.record(ilib.claude_fleet(R), lanes=["code-book", "traceability"])
        self.assert_refused("lanes-mismatch", outcome)
        refusal = [r for r in outcome[1]["refusals"] if r["rule"] == "lanes-mismatch"][0]
        self.assertIn("built", refusal["message"])

    def test_the_whole_fleet_is_accepted(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.triage()["lenses_not_run"], [])


class AnIncompleteLedger(_Rec):
    """Round 5, R4 (F6): an incomplete ledger is not an empty ledger. When `harvest` refused a scope-doc
    row (`ledger.refused`), `record-answer` refuses any question or asserted line (exit 5,
    `ledger-incomplete`) before the shared check runs on what is left; a findings-only answer is still
    recorded, so a malformed plan stays inspectable."""

    SCOPE = ("# Scope\nIntent: counter\nDecisions:\n- keep dependency free \u2014 decided (owner)\n"
             "- future color theme \u2014 parked (later)\nOpen:\n- budget\n")

    def test_the_harvest_records_the_refused_row(self):
        code, doc, out, err = self.record(ilib.claude_fleet(R), scope=self.SCOPE)
        self.assertEqual(code, 0, out + err)
        ledger = self.run.artifact("harvest.json")["ledger"]
        self.assertEqual((ledger["lines"], len(ledger["refused"])), ([], 1))

    def test_a_question_that_re_asks_a_decided_row_is_refused(self):
        questions = [{"id": "Q1", "text": "keep dependency free", "touches": [], "answer": "yes"}]
        outcome = self.record(ilib.claude_fleet(R), scope=self.SCOPE, questions=questions)
        self.assert_refused("ledger-incomplete", outcome)
        refusal = [r for r in outcome[1]["refusals"] if r["rule"] == "ledger-incomplete"][0]
        self.assertIn("future color theme", refusal["message"])

    def test_an_asserted_line_is_refused(self):
        lines = [{"text": "a new decided line", "tag": "decided", "trace": {"kind": "repo_path", "ref": "README.md"}}]
        self.assert_refused("ledger-incomplete", self.record(ilib.claude_fleet(R), scope=self.SCOPE, lines=lines))

    def test_a_findings_only_answer_is_recorded(self):
        fleet = ilib.claude_fleet(R, code_book=[ilib.finding("build-doc.md:12")])
        code, doc, out, err = self.record(fleet, scope=self.SCOPE,
                                          adjudications=[ilib.adjudication("%s-code-book#1" % R)])
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.triage()["counts"]["major"], 1)


class TheVerdictRule(unittest.TestCase):

    def test_every_severity_mix(self):
        cases = [((), "APPROVED"), (("MINOR",), "APPROVED"), (("MAJOR",), "APPROVED WITH CONDITIONS"),
                 (("MAJOR", "MINOR"), "APPROVED WITH CONDITIONS"), (("BLOCKER",), "REJECTED"),
                 (("BLOCKER", "MAJOR", "MINOR"), "REJECTED"), (("BLOCKER", "MINOR"), "REJECTED")]
        for severities, word in cases:
            self.assertEqual(verify.verdict([{"severity": s} for s in severities]), word, severities)


if __name__ == "__main__":
    unittest.main()
