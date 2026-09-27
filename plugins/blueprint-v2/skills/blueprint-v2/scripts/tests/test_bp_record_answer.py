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

    def test_a_line_in_the_owners_words_quoted_is_accepted(self):
        # R1 (CB-1): the owner's words quoted verbatim are a trace here, as the discussion is in the station
        doc = bplib.clean_answer()
        doc["lines"][0]["trace"] = {"kind": "owner_words", "ref": "spin(n) gives back n plus one, nothing more"}
        self.accepted(doc)

    def test_blank_owners_words_are_refused_by_the_schema(self):
        for words in ("", "   "):
            doc = bplib.clean_answer()
            doc["lines"][0]["trace"] = {"kind": "owner_words", "ref": words}
            self.refused(doc, None, code=4)

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


class OutOfScopeLines(_Record):
    """R2 (CL1-1): an out-of-scope line carries a parked or deferred item forward by its id; a scope
    `Open:` item is the owner's call, carried as out of scope only when an answered question touched it."""

    def harvested(self):
        return testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))

    def test_an_out_of_scope_line_carrying_a_deferred_item_forward_is_accepted(self):
        deferred = self.harvested()["architecture"]["deferred"][0]
        doc = bplib.clean_answer()
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": "a web view %s deferred in the architecture "
                           "doc: the module has no I/O" % bplib.D, "trace": {"kind": "ledger", "ref": deferred["id"]}}
        self.accepted(doc)

    def test_an_out_of_scope_line_carrying_a_parked_item_forward_is_accepted(self):
        doc = bplib.clean_answer()
        doc["questions"] = []
        doc["lines"][1]["trace"] = {"kind": "repo_path", "ref": "src/turnstile.py"}
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": "where the count is kept between sessions "
                           "%s parked: needs research" % bplib.D,
                           "trace": {"kind": "ledger", "ref": self.ids["Where the count is kept between sessions"]}}
        self.accepted(doc)

    def test_an_out_of_scope_line_carrying_an_open_item_is_refused(self):
        doc = bplib.clean_answer()
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": "how often the counter resets %s not now"
                           % bplib.D, "trace": {"kind": "ledger", "ref": self.ids["how often the counter resets"]}}
        out = self.refused(doc, "open-item-descoped")
        self.assertIn("how often the counter resets", " ".join(r["message"] for r in out["refusals"]))

    def test_an_open_item_an_answered_question_touched_may_be_carried_out_of_scope(self):
        doc = bplib.clean_answer()
        doc["questions"].append({"id": "Q2", "text": "Is the reset in this build?",
                                 "touches": [self.ids["how often the counter resets"]],
                                 "answer": "no, leave it out of this build"})
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": "how often the counter resets %s the owner "
                           "left it out" % bplib.D,
                           "trace": {"kind": "ledger", "ref": self.ids["how often the counter resets"]}}
        self.accepted(doc)

    def test_an_open_item_touched_only_by_an_unanswered_question_is_still_refused(self):
        doc = bplib.clean_answer()
        doc["questions"].append({"id": "Q2", "text": "Is the reset in this build?",
                                 "touches": [self.ids["how often the counter resets"]], "answer": ""})
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": "how often the counter resets %s not now"
                           % bplib.D, "trace": {"kind": "ledger", "ref": self.ids["how often the counter resets"]}}
        self.refused(doc, "open-item-descoped")

    def test_a_requirement_carrying_a_deferred_item_is_still_refused(self):
        deferred = self.harvested()["architecture"]["deferred"][0]
        doc = bplib.clean_answer()
        doc["lines"][1]["trace"] = {"kind": "ledger", "ref": deferred["id"]}
        self.refused(doc, "quietly-resolved")

    def test_a_constraint_carrying_a_parked_item_is_still_refused(self):
        doc = bplib.clean_answer()
        doc["questions"] = []
        doc["lines"][1]["trace"] = {"kind": "repo_path", "ref": "src/turnstile.py"}
        doc["lines"][2]["trace"] = {"kind": "ledger", "ref": self.ids["Where the count is kept between sessions"]}
        self.refused(doc, "quietly-resolved")



class TheViewCarriesTheWordsWithoutTheirLabel(_Record):
    """Round 3, R2 (CL2-1): the shared text rule compares a line's words with the ledger's, so the view it
    reads carries a requirement's text without its `R<n>` prefix, and a constraint's or out-of-scope
    line's without a label; the doc still renders the prefix. An open, parked or deferred item's words
    written as `R2 <dash> ...` under the owner's words, a repo path, or a question that touched something
    else are refused `quietly-resolved`; the same with an answered question touching the item is
    accepted."""

    def harvested(self):
        return testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))

    def answer_with(self, text, trace, tag="requirement", settle=None):
        doc = bplib.clean_answer()
        doc["questions"] = [{"id": "Q1", "text": "Does the bench script print the count itself?", "touches": [],
                             "answer": "yes"}]
        if settle:
            doc["questions"].append({"id": "Q2", "text": "Is this one settled for the build?", "touches": [settle],
                                     "answer": "yes, settle it as written"})
        line = doc["lines"][1] if tag == "requirement" else doc["lines"][2]
        line["text"] = text
        line["trace"] = trace
        return doc

    def items(self):
        deferred = self.harvested()["architecture"]["deferred"][0]
        return (("open", "how often the counter resets", self.ids["how often the counter resets"]),
                ("parked", "Where the count is kept between sessions",
                 self.ids["Where the count is kept between sessions"]),
                ("deferred", deferred["text"], deferred["id"]))

    def traces(self):
        return ({"kind": "owner_words", "ref": "the owner said so in the discussion"},
                {"kind": "repo_path", "ref": "README.md"},
                {"kind": "question", "ref": "Q1"})

    def test_an_item_written_as_a_numbered_requirement_is_refused_under_every_trace(self):
        for label, text, ident in self.items():
            for trace in self.traces():
                for words in ("R2 %s %s" % (bplib.D, text), "R2 %s  %s" % (bplib.D, text.upper()),
                              "R12: %s" % text):
                    out = self.refused(self.answer_with(words, trace), "quietly-resolved")
                    self.assertIn(ident, " ".join(r["message"] for r in out["refusals"]), (label, trace, words))

    def test_a_labelled_constraint_carrying_an_item_is_refused(self):
        for label, text, ident in self.items():
            for words in ("Constraint: %s" % text, "Constraints: %s" % text, "- %s" % text):
                self.refused(self.answer_with(words, {"kind": "repo_path", "ref": "README.md"}, tag="constraint"),
                             "quietly-resolved")

    def test_with_an_answered_question_touching_the_item_it_is_accepted(self):
        for label, text, ident in self.items():
            testlib.rmtree(self.run.run_dir)
            self.run.to_harvest()
            self.accepted(self.answer_with("R2 %s %s" % (bplib.D, text), {"kind": "question", "ref": "Q2"},
                                           settle=ident))

    def test_the_view_carries_each_lines_original_text(self):
        # round 5, R3: the shared forms read each line as written (a bare `R<n>` label is part of the words
        # when both sides carry one); the marked `R1 <dash> ` is the frame's decoration, seen through there
        from blueprint_core import checks
        doc = bplib.clean_answer()
        self.assertEqual([l["text"] for l in checks.view(doc)["lines"]], [l["text"] for l in doc["lines"]])
        self.assertEqual(doc["lines"][0]["text"], "R1 %s `spin(n)` returns `n + 1`" % bplib.D)


class AnOpenItemUnderAnotherTrace(_Record):
    """Round 3, R3 (CL2-2): `open-item-descoped` fires by the item's words as well as by its id: an
    out-of-scope line whose words (whole, or the item before its reason) are a scope `Open:` item is
    refused unless an answered question of this run touched that item, whatever the line's trace."""

    OPEN = "how often the counter resets"

    def answer_with(self, text, trace, settle=False):
        doc = bplib.clean_answer()
        doc["questions"].append({"id": "Q2", "text": "Does the bench script print the count itself?",
                                 "touches": [], "answer": "yes"})
        if settle:
            doc["questions"].append({"id": "Q3", "text": "Is the reset in this build?",
                                     "touches": [self.ids[self.OPEN]], "answer": "no, leave it out"})
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": text, "trace": trace}
        return doc

    def shapes(self):
        dashboard = self.ids["a web dashboard %s the owner declined it" % bplib.D]
        traces = ({"kind": "repo_path", "ref": "README.md"},
                  {"kind": "owner_words", "ref": "leave the reset out"},
                  {"kind": "question", "ref": "Q2"},
                  {"kind": "ledger", "ref": dashboard})
        texts = (self.OPEN, "How  often the counter RESETS", "%s %s later" % (self.OPEN, bplib.D),
                 "%s: later" % self.OPEN, "Out of scope: %s" % self.OPEN, "- %s (later)" % self.OPEN)
        return [(t, tr) for t in texts for tr in traces]

    def test_the_open_items_words_under_every_other_trace_are_refused(self):
        for text, trace in self.shapes():
            out = self.refused(self.answer_with(text, trace), "open-item-descoped")
            self.assertIn(self.ids[self.OPEN], " ".join(r["message"] for r in out["refusals"]), (text, trace))

    def test_with_an_answered_question_touching_the_item_they_are_accepted(self):
        for index, (text, trace) in enumerate(self.shapes()):
            testlib.rmtree(self.run.run_dir)
            self.run.to_harvest()
            self.accepted(self.answer_with(text, trace, settle=True))

    def test_other_words_are_not_the_open_item(self):
        self.accepted(self.answer_with("how often the counter resets its display %s later" % bplib.D,
                                       {"kind": "repo_path", "ref": "README.md"}))


class AnOpenItemUnderAnyDecoration(_Record):
    """Round 4, R1 (CL2-2, its last round): `open-item-descoped` reads the line and the row through the
    frame's own readings (`station_core.answer.forms` for the line, `row_forms` for the row), never a
    comparison of this core's own, so an open item carried out of scope under any trace and any decoration
    the frame knows is refused: a trailing period, a label, a zero-width space, a tail, the row decorated.
    A genuinely new out-of-scope line that shares a word with an open item is accepted."""

    OPEN = "how often the counter resets"
    PERIOD_ROW = "whether readings persist across sessions."
    TAIL_ROW = "sync to the cloud %s later" % bplib.D
    SCOPE = bplib.SCOPE.replace("- %s\n" % OPEN, "- %s\n- %s\n- %s\n" % (OPEN, PERIOD_ROW, TAIL_ROW))
    files = dict(bplib.base_files(arch=True), **{bplib.SCOPE_PATH: SCOPE})

    def setUp(self):
        super(AnOpenItemUnderAnyDecoration, self).setUp()
        self.ids = bplib.ledger_ids(self.SCOPE)

    def answer_with(self, text, settle=None, trace=None):
        doc = bplib.clean_answer()
        if settle:
            doc["questions"].append({"id": "Q3", "text": "Is this one in this build?", "touches": [self.ids[settle]],
                                     "answer": "no, leave it out"})
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": text,
                           "trace": trace or {"kind": "repo_path", "ref": "README.md"}}
        return doc

    def shapes(self):
        o = self.OPEN
        return ((o + ".", o), ("O1: " + o, o), ("OOS2 %s %s" % (bplib.D, o), o),
                (u"​" + o, o), (o + u"​", o), (u"how often the​ counter resets", o),
                ("%s %s parked: needs prototype" % (o, bplib.M), o), (o + ", later", o),
                ("1. " + o, o), ("**%s**" % o, o), ("R2 %s %s." % (bplib.D, o), o),
                ("%s (not now)." % o, o), (u"﻿- %s;" % o, o),
                ("whether readings persist across sessions", self.PERIOD_ROW),
                ("Whether readings persist across sessions %s later" % bplib.D, self.PERIOD_ROW),
                ("sync to the cloud", self.TAIL_ROW), ("sync to the cloud.", self.TAIL_ROW),
                ("sync to the cloud %s later" % bplib.D, self.TAIL_ROW))

    def test_each_decoration_is_refused(self):
        for text, row in self.shapes():
            out = self.refused(self.answer_with(text), "open-item-descoped")
            self.assertIn(self.ids[row], " ".join(r["message"] for r in out["refusals"]), text)

    def test_each_decoration_is_refused_under_every_trace(self):
        dashboard = self.ids["a web dashboard %s the owner declined it" % bplib.D]
        for trace in ({"kind": "owner_words", "ref": "leave it out"}, {"kind": "question", "ref": "Q1"},
                      {"kind": "ledger", "ref": dashboard}):
            for text, row in self.shapes():
                self.refused(self.answer_with(text, trace=trace), "open-item-descoped")

    def test_with_an_answered_question_touching_the_item_they_are_accepted(self):
        for text, row in self.shapes():
            testlib.rmtree(self.run.run_dir)
            self.run.to_harvest()
            self.accepted(self.answer_with(text, settle=row))

    def test_a_new_line_sharing_a_word_with_an_open_item_is_accepted(self):
        for text in ("how often the display refreshes %s later" % bplib.D, "the counter resets on power loss",
                     "sync to the display", "whether readings are signed %s later" % bplib.D,
                     "later %s how often" % bplib.D, "a cloud backup of the readings."):
            testlib.rmtree(self.run.run_dir)
            self.run.to_harvest()
            self.accepted(self.answer_with(text))

    def test_the_match_is_the_frames_own(self):
        from blueprint_core import checks
        for own in ("_normalized", "_item_forms"):
            self.assertFalse(hasattr(checks, own), own)


class VerifyForms(_Record):
    """R5 (CL1-6): a verify form is one of the template's three."""

    def test_each_of_the_three_forms_is_accepted(self):
        for index, verify in enumerate(("existing test tests/test_turnstile.py::test_spin",
                                        "existing test test_turnstile.TurnCounter.test_spin",
                                        "existing test test_spin_returns_one_more",
                                        "new test at tests/test_turnstile.py",
                                        "new test at tests/turnstile/",
                                        "new test at test_turnstile.py",
                                        "manual: run the bench script and read the count")):
            run = bplib.Run(self.tmp, self.ws, run_id="run-v%d" % index, name="run-v%d" % index)
            run.to_harvest()
            doc = bplib.clean_answer(run_id=run.run_id)
            doc["criteria"][0]["verify"] = verify
            got, out, err = run.record(doc)
            self.assertEqual(got, 0, (verify, out, err))

    def test_a_verify_outside_the_three_forms_is_refused(self):
        for verify in ("verify:", "will be tested later", "new test at", "manual:", "manual:   ", "tests pass",
                       "New test at tests/x.py", "existing tests",
                       # round 3, R4 (CL1-6): free text one step to the side of each form
                       "new test at some point", "new test at TBD", "manual: TBD", "existing test will cover it",
                       "existing test", "existing test TBD", "new test at tests/test turnstile.py",
                       "new test at n/a", "manual: later", "existing test n/a", "new test at TBD.py"):
            doc = bplib.clean_answer()
            doc["criteria"][0]["verify"] = verify
            out = self.refused(doc, "criterion-without-verify")
            self.assertIn("existing test", " ".join(r["message"] for r in out["refusals"]), verify)

    def test_a_token_with_no_letter_or_digit_names_nothing(self):
        # round 4, R2 (CL1-6): after the form's prefix the rest holds at least one letter or digit
        for verify in ("existing test ?", "existing test -", "existing test .", "existing test _",
                       "new test at /", "new test at ./", "new test at ../", "new test at /.",
                       "manual: - -", "manual: ? ?", "manual: ... ---"):
            doc = bplib.clean_answer()
            doc["criteria"][0]["verify"] = verify
            self.refused(doc, "criterion-without-verify")

    def test_a_token_holding_a_letter_or_digit_is_still_a_form(self):
        for index, verify in enumerate(("existing test t1", "new test at tests/9.py", "manual: - run it",
                                        "new test at ./tests/")):
            run = bplib.Run(self.tmp, self.ws, run_id="run-w%d" % index, name="run-w%d" % index)
            run.to_harvest()
            doc = bplib.clean_answer(run_id=run.run_id)
            doc["criteria"][0]["verify"] = verify
            got, out, err = run.record(doc)
            self.assertEqual(got, 0, (verify, out, err))


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


class ALabelIsPartOfTheWords(_Record):
    """Round 5, R3 (the lane half of the outside reviewer's L-2): each line's ORIGINAL text reaches the shared
    `forms` and `row_forms`, so a bare `R<n>` label is part of the words when both sides carry one, and this
    core's own reason cut keeps it. `R4 budget approval` is not the parked `R3 budget approval`; `R12.3 W` is
    the parked `W`; `R21 storage` is not the parked `R2.1 storage`; a plain `budget approval` is still the
    parked `R3 budget approval`. The same for an open item carried out of scope."""

    PARKED = ("R3 budget approval", "W", "R2.1 storage")
    OPEN = "R3 sensor calibration"
    SCOPE = bplib.SCOPE.replace(
        "- Where the count is kept between sessions",
        "".join("- %s %s parked: needs research\n" % (t, bplib.D) for t in PARKED)
        + "- Where the count is kept between sessions").replace(
        "- how often the counter resets\n", "- how often the counter resets\n- %s\n" % OPEN)
    files = dict(bplib.base_files(arch=True), **{bplib.SCOPE_PATH: SCOPE})

    def setUp(self):
        super(ALabelIsPartOfTheWords, self).setUp()
        self.ids = bplib.ledger_ids(self.SCOPE)

    def fresh(self):
        testlib.rmtree(self.run.run_dir)
        self.run.to_harvest()

    def requirement(self, text):
        doc = bplib.clean_answer()
        doc["lines"][1]["text"] = text
        doc["lines"][1]["trace"] = {"kind": "repo_path", "ref": "README.md"}
        return doc

    def out_of_scope(self, text):
        doc = bplib.clean_answer()
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": text,
                           "trace": {"kind": "repo_path", "ref": "README.md"}}
        return doc

    def test_a_different_label_is_a_different_line(self):
        for text in ("R4 budget approval", "R21 storage", "R4 budget approval.", "R2.2 storage"):
            self.fresh()
            self.accepted(self.requirement(text))

    def test_the_same_words_with_the_same_label_or_one_side_bare_are_refused(self):
        for text, row in (("R12.3 W", "W"), ("budget approval", "R3 budget approval"),
                          ("R3 budget approval", "R3 budget approval"), ("R3: budget approval", "R3 budget approval"),
                          ("R2.1 storage", "R2.1 storage"), ("W", "W")):
            self.fresh()
            out = self.refused(self.requirement(text), "quietly-resolved")
            self.assertIn(self.ids[row], " ".join(r["message"] for r in out["refusals"]), text)

    def test_an_open_item_under_another_label_is_not_the_item(self):
        for text in ("R4 sensor calibration", "R4 sensor calibration, later", "R4 sensor calibration: not now",
                     "Out of scope: R4 sensor calibration (not now)", "- R4 sensor calibration; later"):
            self.fresh()
            self.accepted(self.out_of_scope(text))

    def test_an_open_item_with_its_label_or_none_is_refused(self):
        for text in ("sensor calibration", "R3 sensor calibration", "sensor calibration, later",
                     "R3 sensor calibration: not now", "Out of scope: sensor calibration (not now)",
                     "- R3 sensor calibration; later", "R3: sensor calibration"):
            self.fresh()
            out = self.refused(self.out_of_scope(text), "open-item-descoped")
            self.assertIn(self.ids[self.OPEN], " ".join(r["message"] for r in out["refusals"]), text)


class AMarkedLabelIsALabel(_Record):
    """Slice 3a round 4, R2 (C3A-3 with C3A2-2, landed on the owner's word A8): the frame keys a marked label
    (`R2:`, `(R2)`, `[R2]`, `**R2:**`) in any case and a bare one in upper case only, so this core's reason cut
    keeps a marked label in upper or lower case as it keeps a bare one, and an open item carried out of scope
    under a marked label is still the open item. A lower-case bare token is words, and other words are a new
    line."""

    OPEN = "budget ceiling"
    SCOPE = bplib.SCOPE.replace("- how often the counter resets\n", "- how often the counter resets\n- %s\n" % OPEN)
    files = dict(bplib.base_files(arch=True), **{bplib.SCOPE_PATH: SCOPE})

    def setUp(self):
        super(AMarkedLabelIsALabel, self).setUp()
        self.ids = bplib.ledger_ids(self.SCOPE)

    def fresh(self):
        testlib.rmtree(self.run.run_dir)
        self.run.to_harvest()

    def out_of_scope(self, text):
        doc = bplib.clean_answer()
        doc["lines"][3] = {"id": "O1", "tag": "out-of-scope", "text": text,
                           "trace": {"kind": "repo_path", "ref": "README.md"}}
        return doc

    def test_a_marked_label_in_either_case_carrying_the_open_item_is_refused(self):
        for text in ("R2: budget ceiling, declined by owner", "AC1: budget ceiling, not in v1",
                     "r2: budget ceiling, declined by owner", "ac1: budget ceiling, not in v1",
                     "r2 : budget ceiling, declined by owner", "Ac1 : budget ceiling; not in v1",
                     "R2A: budget ceiling, declined by owner", "R2\u034f: budget ceiling, declined by owner",
                     "R2\u212a: budget ceiling, declined by owner", "R\x1c2: budget ceiling, declined by owner",
                     "R\uff12: budget ceiling, declined by owner"):
            self.fresh()
            out = self.refused(self.out_of_scope(text), "open-item-descoped")
            self.assertIn(self.ids[self.OPEN], " ".join(r["message"] for r in out["refusals"]), text)

    def test_other_words_or_a_lower_case_bare_token_are_a_new_line(self):
        for text in ("r2: a phone app, declined by owner", "R2: a phone app, declined by owner",
                     "ac1 budget ceiling review, later", "r2 budget ceiling, declined by owner",
                     "(r2) a phone app: declined", "Q3: budget ceiling review board, not now",
                     "R2A: a phone app, declined by owner", "R2\u212a: a phone app, declined by owner"):
            self.fresh()
            self.accepted(self.out_of_scope(text))


if __name__ == "__main__":
    unittest.main()
