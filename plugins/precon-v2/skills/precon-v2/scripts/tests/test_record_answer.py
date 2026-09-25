"""precon-v2's `record-answer` (precon-v2-contract.md section 5; required test 5 of lane P), through the real CLI.

Every refusal of precon's own, and the shared refusals precon relies on (proved, not
duplicated): exit 5, the refusals listed on stdout, nothing written. A schema failure is exit 4.
The clean answer is accepted and `answer.json` is written.
"""
import json
import os
import unittest

import preconlib
import testlib
from preconlib import D


class _Answer(unittest.TestCase):

    doc_text = preconlib.SCOPE_DOC

    def setUp(self):
        self.tmp = testlib.make_scratch("answer-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)
        if self.doc_text is not None:
            preconlib.ensure_scope_doc(self.fx, text=self.doc_text)
        self.run_ = self.fx.new_run()
        self.run_.select()
        code, doc, err = self.run_.harvest()
        self.assertEqual(code, 0, err)

    def refused(self, answer, rule):
        before = sorted(os.listdir(self.run_.run_dir))
        digest = testlib.tree_digest(self.fx.ws)
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 5, "%s %s" % (json.dumps(doc), err))
        self.assertFalse(doc["accepted"])
        rules = sorted(set(r["rule"] for r in doc["refusals"]))
        self.assertIn(rule, rules, json.dumps(doc["refusals"], ensure_ascii=False))
        for row in doc["refusals"]:
            self.assertTrue(row["message"])
        self.assertEqual(sorted(os.listdir(self.run_.run_dir)), before, "nothing written in the run directory")
        self.assertEqual(testlib.tree_digest(self.fx.ws), digest)
        self.assertFalse(os.path.exists(self.run_.run_file("answer.json")))
        return doc

    def answer(self, **fields):
        return preconlib.answer(self.run_, **fields)


class TheLedgerRules(_Answer):

    def test_a_decided_line_with_no_source_is_the_shared_untraced(self):
        self.refused(self.answer(lines=[{"text": "Counts are written to the bench log", "tag": "decided"}]),
                     "untraced")

    def test_a_decided_line_traced_as_an_assumption_has_no_source(self):
        self.refused(self.answer(lines=[{"text": "Counts are written to the bench log", "tag": "decided",
                                         "trace": {"kind": "assumed", "ref": "it seemed obvious"}}]),
                     "decided-without-source")

    def test_an_assumed_ledger_line_promoted_to_decided_without_a_question(self):
        self.refused(self.answer(lines=[{"text": "One module, no package", "tag": "decided",
                                         "trace": {"kind": "ledger", "ref": preconlib.ASSUMED_ID}}]),
                     "decided-without-source")

    def test_an_assumed_line_with_no_why_is_the_shared_untraced(self):
        self.refused(self.answer(lines=[{"text": "Tests use unittest", "tag": "assumed",
                                         "trace": {"kind": "assumed", "ref": "   "}}]), "untraced")

    def test_an_assumed_line_traced_to_a_question_carries_no_why(self):
        q = {"id": "Q1", "text": "Which test runner?", "touches": [], "answer": "unittest"}
        self.refused(self.answer(questions=[q], lines=[{"text": "Tests use unittest", "tag": "assumed",
                                                        "trace": {"kind": "question", "ref": "Q1"}}]),
                     "assumed-without-why")

    def test_a_parked_line_with_none_of_the_three_reasons(self):
        for reason in ("later", "", "waiting on ", "needs research soon", None):
            line = {"text": "Reverse turns", "tag": "parked",
                    "trace": {"kind": "owner_words", "ref": "not now"}}
            if reason is not None:
                line["reason"] = reason
            self.refused(self.answer(lines=[line]), "parked-without-reason")

    def test_a_parked_ledger_line_quietly_resolved_is_the_shared_rule(self):
        self.refused(self.answer(lines=[{"text": "A second counting mode for reverse turns", "tag": "decided",
                                         "trace": {"kind": "ledger", "ref": preconlib.PARKED_WAITING_ID}}]),
                     "quietly-resolved")

    def test_an_open_item_quietly_resolved_is_the_shared_rule(self):
        self.refused(self.answer(lines=[{"text": "how often the counter resets", "tag": "decided",
                                         "trace": {"kind": "ledger", "ref": preconlib.OPEN_ID}}]),
                     "quietly-resolved")

    def test_a_decided_line_re_asked_is_the_shared_rule(self):
        q = {"id": "Q1", "text": "Standard library only?", "touches": [preconlib.DECIDED_ID], "answer": "yes"}
        self.refused(self.answer(questions=[q]), "re-asked-decided")

    def test_a_line_retagged_against_its_ledger_line(self):
        self.refused(self.answer(lines=[{"text": "Python 3.9 standard library only", "tag": "parked",
                                         "reason": "needs research",
                                         "trace": {"kind": "ledger", "ref": preconlib.DECIDED_ID}}]),
                     "retagged")

    def test_an_open_line_carries_the_call_it_waits_on(self):
        self.refused(self.answer(lines=[{"text": "Whether resets are logged", "tag": "open",
                                         "trace": {"kind": "owner_words", "ref": "ask me later"}}]),
                     "open-without-call")


    def test_a_parked_or_open_line_or_an_item_traced_as_an_assumption(self):
        self.refused(self.answer(lines=[{"text": "Reverse turns", "tag": "parked", "reason": "needs prototype",
                                         "trace": {"kind": "assumed", "ref": "probably later"}}]), "source-kind")
        self.refused(self.answer(lines=[{"text": "Resets", "tag": "open", "waits_on": "the owner's call",
                                         "trace": {"kind": "assumed", "ref": "seems open"}}]), "source-kind")
        self.refused(self.answer(out_of_scope=[{"text": "a phone app", "reason": "declined",
                                                "trace": {"kind": "repo_path", "ref": "src/turnstile.py"}}]),
                     "source-kind")


class Twins(_Answer):
    """CP1-1 (ruling R1): a line that repeats a ledger line's text without its id. The shared
    `quietly-resolved` refuses a parked or open line's words asserted as decided under any trace
    kind unless a question of this run touched it; precon's `retagged` refuses every repeat of a
    `Decisions:` or `Open:` line under a non-ledger trace (an assumed line included, and a parked or
    open line a question did touch), so the doc never holds a line and its twin."""

    PARKED = "Where the count is kept between sessions"
    OPEN = "how often the counter resets"
    ASSUMED = "One module, no package"

    def rules(self, answer):
        doc = self.refused(answer, "retagged")
        return sorted(set(r["rule"] for r in doc["refusals"]))

    def test_the_parked_open_and_assumed_twins_under_owner_words(self):
        # the checker's probes/30 shape: each ledger line's text re-asserted as decided under owner_words
        for text, shared in ((self.PARKED, True), (self.OPEN, True), (self.ASSUMED, False)):
            rules = self.rules(self.answer(lines=[preconlib.owner_line(text, "we settled it")]))
            if shared:
                self.assertEqual(rules, ["quietly-resolved", "retagged"], text)
            else:
                self.assertEqual(rules, ["retagged"], text)

    def test_a_twin_the_shared_rule_passes_is_still_refused(self):
        # a question of this run touched the parked line, so the shared rule is satisfied; the twin is not
        q = {"id": "Q1", "text": "Where is the count kept?", "touches": [preconlib.PARKED_RESEARCH_ID],
             "answer": "in memory only"}
        for trace in ({"kind": "owner_words", "ref": "in memory only"}, {"kind": "question", "ref": "Q1"},
                      {"kind": "repo_path", "ref": "src/turnstile.py"}):
            rules = self.rules(self.answer(questions=[q], lines=[
                {"text": self.PARKED, "tag": "decided", "trace": trace}]))
            self.assertEqual(rules, ["retagged"], trace)

    def test_a_twin_by_case_and_whitespace_and_under_every_tag(self):
        self.rules(self.answer(lines=[preconlib.owner_line("  where THE count is kept   between sessions ",
                                                           "we settled it")]))
        self.rules(self.answer(lines=[{"text": "Python 3.9 standard library only", "tag": "decided",
                                       "trace": {"kind": "owner_words", "ref": "again"}}]))
        self.rules(self.answer(lines=[{"text": self.OPEN, "tag": "parked", "reason": "needs prototype",
                                       "trace": {"kind": "owner_words", "ref": "later"}}]))

    def test_the_doc_never_holds_a_parked_line_and_a_decided_twin(self):
        before = preconlib.read(os.path.join(self.fx.ws, preconlib.SCOPE_REL))
        self.rules(self.answer(lines=[preconlib.owner_line(self.PARKED, "we settled it")]))
        self.assertEqual(self.run_.write()[0], 2, "no accepted answer, nothing to write")
        self.assertEqual(preconlib.read(os.path.join(self.fx.ws, preconlib.SCOPE_REL)), before)


class TheResearchRule(_Answer):

    def research_q(self, answer="park it, I will look it up"):
        return {"id": "Q1", "text": "Where is the count kept between sessions?",
                "touches": [preconlib.PARKED_RESEARCH_ID], "answer": answer, "needs_research": True}

    def test_a_research_question_resolved_by_a_line(self):
        self.refused(self.answer(questions=[self.research_q()], lines=[
            {"text": "The count is kept in a file", "tag": "decided", "trace": {"kind": "question", "ref": "Q1"}}]),
            "research-resolved")

    def test_a_research_question_resolving_its_parked_ledger_line(self):
        self.refused(self.answer(questions=[self.research_q()], lines=[
            {"text": "Where the count is kept between sessions", "tag": "decided",
             "trace": {"kind": "ledger", "ref": preconlib.PARKED_RESEARCH_ID}}]), "research-resolved")

    def test_a_new_research_question_with_no_parked_line(self):
        q = {"id": "Q1", "text": "Which encoder library fits?", "touches": [], "answer": "no idea yet",
             "needs_research": True}
        self.refused(self.answer(questions=[q]), "research-not-parked")

    def test_an_out_of_scope_item_traced_to_a_research_question(self):
        # CP1-3: ruling an item out is settling it; a needs-research question settles nothing in the run
        q = {"id": "Q1", "text": "Which encoder library fits?", "touches": [], "answer": "park it",
             "needs_research": True}
        line = {"text": "Which encoder library to use", "tag": "parked", "reason": "needs research",
                "trace": {"kind": "question", "ref": "Q1"}}
        self.refused(self.answer(questions=[q], lines=[line], out_of_scope=[
            {"text": "a vendor encoder library", "reason": "the owner declined it",
             "trace": {"kind": "question", "ref": "Q1"}}]), "research-resolved")

    def test_a_research_question_parked_for_another_reason(self):
        # CP1-3: what a needs-research question leaves is a `needs research` line, never another reason
        q = {"id": "Q1", "text": "Which encoder library fits?", "touches": [], "answer": "park it",
             "needs_research": True}
        lines = [{"text": "Which encoder library to use", "tag": "parked", "reason": "needs research",
                  "trace": {"kind": "question", "ref": "Q1"}},
                 {"text": "An encoder mock", "tag": "parked", "reason": "needs prototype",
                  "trace": {"kind": "question", "ref": "Q1"}}]
        self.refused(self.answer(questions=[q], lines=lines), "research-resolved")

    def test_a_research_question_parked_is_accepted(self):
        q = {"id": "Q1", "text": "Which encoder library fits?", "touches": [], "answer": "no idea yet",
             "needs_research": True}
        line = {"text": "Which encoder library to use", "tag": "parked", "reason": "needs research",
                "trace": {"kind": "question", "ref": "Q1"}}
        code, doc, err = self.run_.record(self.answer(questions=[q], lines=[line]))
        self.assertEqual(code, 0, json.dumps(doc))


class TheGate(_Answer):

    def test_a_gate_absent(self):
        answer = self.answer()
        del answer["gate"]
        self.refused(answer, "gate-missing")

    def test_a_gate_blank_or_on_two_lines(self):
        for gate in ("", "   ", "every branch visited\nand parked"):
            self.refused(self.answer(gate=gate), "gate-missing")

    def test_a_gate_of_format_characters_only(self):
        # CP1-4: a zero-width space, a byte-order mark and the like carry no justification
        for gate in ("\u200b", " \u200b\ufeff ", "\u2060\u00a0"):
            self.refused(self.answer(gate=gate), "gate-missing")


class TheRun(_Answer):

    def test_the_session_is_the_executors(self):
        self.refused(self.answer(session_id="session-someone-else"), "session-mismatch")

    def test_the_run_is_this_run(self):
        self.refused(self.answer(run_id="run-9999"), "run-mismatch")

    def test_a_detail_that_would_break_the_ledger_line_is_unrenderable(self):
        self.refused(self.answer(lines=[preconlib.owner_line("Counts print to stdout",
                                                               "print it %s nothing fancy" % D)]), "unrenderable")
        self.refused(self.answer(lines=[preconlib.owner_line("Counts print\nto stdout", "print it")]),
                     "unrenderable")

    def test_a_text_that_would_read_back_as_another_line_is_unrenderable(self):
        # the ledger reader would take `Counts print` as the text and the rest as its source
        self.refused(self.answer(lines=[preconlib.owner_line("Counts print %s decided (by the rig)" % D, "print it")]),
                     "unrenderable")
        self.refused(self.answer(lines=[{"text": "Reverse %s parked: needs research" % D, "tag": "parked",
                                         "reason": "needs prototype",
                                         "trace": {"kind": "owner_words", "ref": "later"}}]), "unrenderable")

    def test_doc_fields_on_an_existing_doc(self):
        self.refused(self.answer(doc=preconlib.new_doc_fields(),
                                 lines=[preconlib.owner_line("Counts print to stdout", "print it")]), "doc-fields")

    def test_the_napkin_outcome_over_an_existing_doc(self):
        self.refused(self.answer(triage={"tier": "napkin", "why": "one sentence", "no_scope_doc": True}),
                     "napkin-outcome")


class NoDoc(_Answer):

    doc_text = None

    def test_a_title_or_intent_on_two_lines_is_unrenderable(self):
        for fields in ({"title": "Turnstile", "intent": "a counter\nNext: something else"},
                       {"title": "Turnstile", "intent": "a counter\nfor the bench rig"},
                       {"title": "Turn\nstile", "intent": "a counter"}):
            self.refused(self.answer(doc=fields, lines=[preconlib.owner_line("Counts print to stdout", "print it")]),
                         "unrenderable")

    def test_a_new_doc_needs_its_title_and_intent(self):
        self.refused(self.answer(lines=[preconlib.owner_line("Counts print to stdout", "print it")]), "doc-fields")

    def test_no_scope_doc_is_napkin_only_and_carries_no_line(self):
        self.refused(self.answer(triage={"tier": "bounded", "why": "known edges", "no_scope_doc": True}),
                     "napkin-outcome")
        self.refused(self.answer(triage={"tier": "napkin", "why": "one sentence", "no_scope_doc": True},
                                 lines=[preconlib.owner_line("Counts print to stdout", "print it")]),
                     "napkin-outcome")

    def test_the_napkin_outcome_ends_the_sitting(self):
        # CP1-10: "no scope doc" ends the sitting; a napkin outcome that says it continues is refused
        self.refused(self.answer(triage={"tier": "napkin", "why": "one sentence", "no_scope_doc": True},
                                 sitting="continues"), "napkin-outcome")

    def test_the_napkin_outcome_is_accepted(self):
        code, doc, err = self.run_.record(self.answer(
            triage={"tier": "napkin", "why": "describable in one sentence", "no_scope_doc": True}))
        self.assertEqual(code, 0, json.dumps(doc))


class Schema(_Answer):

    def test_an_unknown_key_is_exit_4(self):
        answer = self.answer()
        answer["extra"] = 1
        before = sorted(os.listdir(self.run_.run_dir))
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 4, json.dumps(doc))
        self.assertTrue(doc["errors"])
        self.assertEqual(sorted(os.listdir(self.run_.run_dir)), before)

    def test_a_tier_outside_the_three_is_exit_4(self):
        code, doc, err = self.run_.record(self.answer(triage={"tier": "huge", "why": "big"}))
        self.assertEqual(code, 4, json.dumps(doc))

    def test_a_question_field_of_the_wrong_type_is_exit_4(self):
        q = {"id": "Q1", "text": "Where?", "touches": "dec-1", "answer": "here"}
        code, doc, err = self.run_.record(self.answer(questions=[q]))
        self.assertEqual(code, 4, json.dumps(doc))

    def test_an_answer_that_is_not_json_is_usage(self):
        path = os.path.join(self.tmp, "bad.json")
        testlib.write_text(path, "not json")
        code, out, err = self.run_.phase("record-answer", "--answer", path)
        self.assertEqual(code, 2, out + err)


class Accepted(_Answer):

    def clean(self):
        q1 = {"id": "Q1", "text": "Where is the count kept between sessions?",
              "touches": [preconlib.PARKED_RESEARCH_ID], "answer": "in memory only"}
        return self.answer(questions=[q1], lines=[
            {"text": "Python 3.9 standard library only", "tag": "decided",
             "trace": {"kind": "ledger", "ref": preconlib.DECIDED_ID}},
            {"text": "Where the count is kept between sessions", "tag": "decided",
             "trace": {"kind": "ledger", "ref": preconlib.PARKED_RESEARCH_ID}},
            {"text": "The count is kept in memory only", "tag": "decided", "trace": {"kind": "question", "ref": "Q1"}},
            {"text": "The counter lives in src/turnstile.py", "tag": "decided",
             "trace": {"kind": "repo_path", "ref": "src/turnstile.py"}},
            {"text": "Tests use unittest", "tag": "assumed",
             "trace": {"kind": "assumed", "ref": "the standard library already has it"}},
            {"text": "Whether resets are logged", "tag": "open", "waits_on": "the owner's call on logging",
             "trace": {"kind": "owner_words", "ref": "ask me when the rig is wired"}}],
            out_of_scope=[{"text": "a phone app", "reason": "the owner declined it",
                           "trace": {"kind": "owner_words", "ref": "no phone app"}}])

    def test_the_clean_answer_is_accepted_and_written(self):
        answer = self.clean()
        code, doc, err = self.run_.record(answer)
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertTrue(doc["accepted"])
        self.assertEqual(doc["next"], "write")
        self.assertEqual(testlib.load_json(self.run_.run_file("answer.json")), answer)

    def test_a_second_answer_is_usage(self):
        self.assertEqual(self.run_.record(self.clean())[0], 0)
        self.assertEqual(self.run_.record(self.clean())[0], 2)

    def test_a_refusal_leaves_the_run_where_it_was(self):
        self.refused(self.answer(gate=""), "gate-missing")
        code, doc, err = self.run_.record(self.clean())
        self.assertEqual(code, 0, json.dumps(doc))

    def test_record_answer_before_harvest_is_usage(self):
        run = self.fx.new_run()
        run.select()
        self.assertEqual(run.record(preconlib.answer(run))[0], 2)


class ReportOnly(_Answer):

    def test_report_only_records_in_the_run_directory_only(self):
        run = self.fx.new_run(report_only=True)
        run.select()
        run.harvest()
        digest = (testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging))
        code, doc, err = run.record(preconlib.answer(run, lines=[preconlib.owner_line("Counts print to stdout",
                                                                                          "print it")]))
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertTrue(os.path.isfile(run.run_file("answer.json")))
        self.assertEqual((testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging)), digest)


if __name__ == "__main__":
    unittest.main()
