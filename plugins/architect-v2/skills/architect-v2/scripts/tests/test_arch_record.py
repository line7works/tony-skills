"""`record-answer` (brief 3.4 and CR-9, required test 4), through the real CLI.

Each refusal of architect-v2's answer is exit 5 with the refusals on stdout and nothing written
(the run directory and the workspace unchanged, hash for hash); a schema failure is exit 4 the
same way; the clean answer is accepted and `answer.json` written. The no-loss check refuses a
re-run whose answer drops a prior poured-concrete line, and a living doc whose run-log block the
re-render would drop, before any write.
"""
import os
import unittest

import archlib
import testlib

D = archlib.D
M = archlib.M


class _Record(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-record-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        self.ws = archlib.repo_workspace(self.tmp, files=getattr(self, "FILES", None))
        self.run = archlib.ArchRun(self.tmp, self.ws, self.staging)
        code, doc, out, err = self.run.to_harvest()
        self.assertEqual(code, 0, out + err)
        self.i = archlib.ids()

    def refused(self, answer, rule, code=5):
        before_run = archlib.listing(self.run.run_dir)
        before_ws = archlib.listing(self.ws)
        got, doc, out, err = self.run.record(answer)
        self.assertEqual(got, code, out + err)
        if code == 5:
            rules = sorted(set(r["rule"] for r in doc["refusals"]))
            self.assertIn(rule, rules, doc["refusals"])
            self.assertFalse(doc["accepted"])
        self.assertEqual(archlib.listing(self.run.run_dir), before_run, "nothing written in the run")
        self.assertEqual(archlib.listing(self.ws), before_ws, "nothing written in the workspace")
        return doc


class TheCleanAnswer(_Record):

    def test_accepted_and_recorded(self):
        code, doc, out, err = self.run.record(archlib.clean_answer())
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["accepted"])
        self.assertEqual(doc["next"], "write")
        self.assertEqual(archlib.sha(os.path.join(self.run.run_dir, "answer.json")), doc["sha256"])


class TheSharedRefusals(_Record):

    def test_a_question_touching_a_decided_line(self):
        a = archlib.clean_answer()
        a["questions"].append({"id": "Q9", "text": "Python, or something with a package manager?",
                               "touches": [self.i["decided"]], "answer": "Python"})
        self.refused(a, "re-asked-decided")

    def test_the_decided_text_asked_again(self):
        a = archlib.clean_answer()
        a["questions"].append({"id": "Q9", "text": self.i["decided_text"], "touches": [], "answer": "yes"})
        self.refused(a, "re-asked-decided")

    def test_a_poured_line_with_no_trace(self):
        a = archlib.clean_answer()
        del a["poured_concrete"][1]["trace"]
        self.refused(a, "untraced")

    def test_a_deferred_line_with_no_trace(self):
        a = archlib.clean_answer()
        del a["deferred"][0]["trace"]
        self.refused(a, "untraced")

    def test_a_walkthrough_with_no_trace(self):
        a = archlib.clean_answer()
        del a["walkthrough"]["trace"]
        self.refused(a, "untraced")

    def test_a_trace_that_names_nothing(self):
        a = archlib.clean_answer()
        a["poured_concrete"][0]["trace"] = {"kind": "ledger", "ref": "dec-000000000000"}
        self.refused(a, "untraced")

    def test_an_assumed_trace_with_no_why(self):
        a = archlib.clean_answer()
        a["poured_concrete"][0]["trace"] = {"kind": "assumed", "ref": "  "}
        self.refused(a, "untraced")

    def test_a_parked_line_quietly_resolved(self):
        a = archlib.clean_answer()
        a["questions"] = [q for q in a["questions"] if q["id"] != "Q2"]
        a["poured_concrete"][1]["trace"] = {"kind": "ledger", "ref": self.i["parked"]}
        self.refused(a, "quietly-resolved")


class ArchitectsOwnRefusals(_Record):

    def test_one_candidate(self):
        a = archlib.clean_answer()
        a["candidates"] = a["candidates"][:1]
        a["rejected"] = []
        self.refused(a, "candidates-fewer-than-two")

    def test_two_candidates_in_one_category(self):
        a = archlib.clean_answer()
        a["candidates"][1]["categories"] = ["platform:library"]
        self.refused(a, "candidates-not-distinct")

    def test_re_cased_or_re_spaced_categories_are_not_distinct(self):
        """R4 (CA1-5): category names and choices compare casefolded and whitespace-normalized."""
        for first, second in ((["platform:library"], ["Platform:library"]),
                              (["platform:library"], ["platform:Library"]),
                              (["platform:library"], [" platform :  library "]),
                              (["storage:flat  file"], ["STORAGE:Flat File"])):
            a = archlib.clean_answer()
            a["candidates"][0]["categories"] = first
            a["candidates"][1]["categories"] = second
            self.refused(a, "candidates-not-distinct")

    def test_a_category_only_one_candidate_names_is_no_difference(self):
        """R4: padding one candidate with a category the other does not name differs in nothing
        both name; a difference counts only in a category both candidates name."""
        a = archlib.clean_answer()
        a["candidates"][0]["categories"] = ["platform:library"]
        a["candidates"][1]["categories"] = ["platform:library", "storage:none"]
        self.refused(a, "candidates-not-distinct")

    def test_a_second_choice_padded_into_a_shared_category_is_no_difference(self):
        """CA2-4: a category differs only when the two candidates share no choice in it."""
        for first, second in ((["platform:library", "platform:server"], ["platform:library"]),
                              (["platform:library", "storage:csv"], ["platform:library", "storage:csv", "storage:none"])):
            a = archlib.clean_answer()
            a["candidates"][0]["categories"] = first
            a["candidates"][1]["categories"] = second
            self.refused(a, "candidates-not-distinct")

    def test_a_component_serving_nothing(self):
        a = archlib.clean_answer()
        a["components"].append({"name": "metrics exporter", "serves": ""})
        self.refused(a, "razor")

    def test_a_component_serving_no_walkthrough_requirement(self):
        a = archlib.clean_answer()
        a["components"].append({"name": "metrics exporter", "serves": "export metrics"})
        self.refused(a, "razor")

    def test_a_rejected_candidate_with_no_why(self):
        a = archlib.clean_answer()
        a["rejected"][0]["why"] = " "
        self.refused(a, "rejected-without-why")

    def test_a_rejected_list_that_misses_a_candidate(self):
        a = archlib.clean_answer()
        a["rejected"] = []
        self.refused(a, "rejected-mismatch")

    def test_a_pick_that_is_no_candidate(self):
        a = archlib.clean_answer(pick="monolith")
        self.refused(a, "pick-not-a-candidate")

    def test_an_ended_interview_with_candidates(self):
        a = archlib.clean_answer()
        a["exit_ramp"] = {"continued": False, "why": "a single static page"}
        self.refused(a, "exit-ramp-ended-with-candidates")

    def test_a_docless_block_on_a_run_with_a_scope_doc(self):
        a = archlib.clean_answer(docless={"reason": "no precon", "home": "staging"})
        self.refused(a, "docless-with-scope-doc")

    def test_the_session_is_the_inputs(self):
        self.refused(archlib.clean_answer(session_id="another-session"), "session-mismatch")

    def test_the_run_is_this_one(self):
        self.refused(archlib.clean_answer(run_id="run-9999"), "run-mismatch")

    def test_a_scope_doc_run_offers_the_review(self):
        self.refused(archlib.clean_answer(review={"outcome": "not-offered"}), "review-offer")

    def test_rulings_without_a_review(self):
        a = archlib.clean_answer(rulings=[{"disagreement": "a server", "ruling": "no server",
                                           "reviewers": ["gpt"], "changes": [],
                                           "trace": {"kind": "question", "ref": "Q1"}}])
        self.refused(a, "rulings-without-review")

    def test_a_done_review_with_no_take_saved(self):
        self.refused(archlib.clean_answer(review={"outcome": "done", "spine": "a module"}), "review-no-take")

    def test_a_republish_that_names_no_url_is_a_first_publish_only(self):
        self.refused(archlib.clean_answer(publish_url="https://example.invalid/artifact/other"), "republish-url")


class PublishAgainstTheInput(unittest.TestCase):

    def test_the_input_said_no_publish(self):
        tmp = testlib.make_scratch("arch-record-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = archlib.repo_workspace(tmp)
        run = archlib.ArchRun(tmp, ws, station={"publish": False})
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = run.record(archlib.clean_answer())
        self.assertEqual(code, 5, out + err)
        self.assertIn("publish-against-input", [r["rule"] for r in doc["refusals"]])
        code, doc, out, err = run.record(archlib.clean_answer(publish=False))
        self.assertEqual(code, 0, out + err)


class TheSchema(_Record):

    def test_a_walkthrough_field_missing_or_blank_is_exit_4(self):
        for field in ("who", "when", "must"):
            a = archlib.clean_answer()
            del a["walkthrough"][field]
            self.refused(a, None, code=4)
            a = archlib.clean_answer()
            a["walkthrough"][field] = [" "] if field == "must" else "  "
            self.refused(a, None, code=4)

    def test_a_walkthrough_field_holding_the_separator_is_exit_4(self):
        """CA1-8: a field that carries the walkthrough line's separator would forge a second field."""
        forged = "Sam  %s  When: never  %s  Must be able to: nothing" % (M, M)
        for field in ("who", "when", "must"):
            a = archlib.clean_answer()
            a["walkthrough"][field] = [forged] if field == "must" else forged
            self.refused(a, None, code=4)
        a = archlib.clean_answer()
        a["walkthrough"]["who"] = "Sam %s Bench" % M
        self.refused(a, None, code=4)

    def test_a_must_item_holding_the_list_separator_is_exit_4(self):
        """CA2-6: `must` renders joined with `; `; an item holding it would read as two requirements."""
        a = archlib.clean_answer()
        a["walkthrough"]["must"] = ["count turns; reset the count"]
        self.refused(a, None, code=4)
        a = archlib.clean_answer()
        a["walkthrough"]["must"] = ["count turns;", "reset the count"]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)  # held by the razor, not the schema: no `; ` in the item

    def test_an_unknown_key_is_exit_4(self):
        a = archlib.clean_answer()
        a["colour"] = "blue"
        self.refused(a, None, code=4)

    def test_a_value_with_a_line_break_is_exit_4(self):
        a = archlib.clean_answer()
        a["data_flow"] = "one\n## Run log"
        self.refused(a, None, code=4)

    SEPARATOR = "answer text must contain no line separator"

    def test_every_line_boundary_in_a_walkthrough_field_is_exit_4(self):
        """Round 7 R2 (A2): a line boundary other than CR and LF (U+2028, U+0085, vertical tab, ...)
        would render a heading inside a field; each one `str.splitlines` knows is exit 4, nothing
        written, the finding at the field."""
        for ch in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
            a = archlib.clean_answer()
            a["walkthrough"]["who"] = "Sam%s## Deferred" % ch
            doc = self.refused(a, None, code=4)
            self.assertIn({"path": "/walkthrough/who", "message": self.SEPARATOR}, doc["errors"], repr(ch))

    def test_a_line_boundary_at_any_depth_is_exit_4(self):
        """Every string of the answer, at every depth, whatever its own pattern says."""
        a = archlib.clean_answer()
        a["questions"][1]["answer"] = "in memory\u2028## Run log"
        a["poured_concrete"][0]["trace"]["ref"] = "dec\x85x"
        a["walkthrough"]["must"][1] = "reset the count\u2029"
        a["session_id"] = "session\vtest"
        doc = self.refused(a, None, code=4)
        paths = [e["path"] for e in doc["errors"] if e["message"] == self.SEPARATOR]
        self.assertEqual(sorted(paths), ["/poured_concrete/0/trace/ref", "/questions/1/answer", "/session_id",
                                         "/walkthrough/must/1"], doc["errors"])

    def test_the_boundaries_are_exactly_the_ones_splitlines_knows(self):
        testlib.add_scripts_to_path()
        from architect_core import schema
        known = set(ch for ch in map(chr, range(0x110000)) if len(("a%sb" % ch).splitlines()) > 1)
        self.assertEqual(set(schema.LINE_BOUNDARIES), known)
        self.assertEqual(schema.errors(archlib.clean_answer()), [])


class Docless(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-record-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        ws = testlib.git_workspace(self.tmp, "ws")
        self.run = archlib.ArchRun(self.tmp, ws, self.staging)
        self.run.check_input()
        self.run.select("scope")
        self.run.select("architecture", "bench-counter")
        code, doc, out, err = self.run.harvest()
        self.assertEqual(code, 0, out + err)

    def docless_answer(self, **over):
        a = archlib.clean_answer(**over)
        a["questions"] = [{"id": "Q0", "text": "Is there a scope doc somewhere the glob cannot see?",
                           "touches": [], "answer": "none", "about": "scope-doc"}] + \
            [q for q in a["questions"] if q["id"] != "Q2"]
        a["poured_concrete"] = [{"text": "language %s Python 3.9 %s the bench" % (D, D), "tag": "decided",
                                 "trace": {"kind": "question", "ref": "Q3"}}]
        a["deferred"] = []
        a["review"] = {"outcome": "not-offered"}
        a.setdefault("docless", {"reason": "an experiment the owner wants drawn before any precon",
                                 "home": "staging"})
        return a

    def test_the_docless_answer_is_accepted(self):
        code, doc, out, err = self.run.record(self.docless_answer())
        self.assertEqual(code, 0, out + err)

    def test_a_docless_run_with_no_reason(self):
        a = self.docless_answer()
        a["docless"]["reason"] = " "
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("docless-without-reason", [r["rule"] for r in doc["refusals"]])

    def test_a_docless_run_with_no_docless_block(self):
        a = self.docless_answer()
        del a["docless"]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("docless-without-reason", [r["rule"] for r in doc["refusals"]])

    def test_a_docless_run_that_never_asked(self):
        a = self.docless_answer()
        a["questions"] = [q for q in a["questions"] if q.get("about") != "scope-doc"]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("docless-unasked", [r["rule"] for r in doc["refusals"]])


LIVING = ("# Turnstile %(D)s architecture (2026-09-21)\n\n"
          "Scope doc: docs/scope/2026-09-20-turnstile.md\n"
          "Blind review: declined 2026-09-21\n\n"
          "## Walkthrough target\n"
          "Who: Sam Bench  %(M)s  When: 2026-10-01  %(M)s  Must be able to: count turns; reset the count\n\n"
          "## v0 drawing\nComponents: turnstile.py (serves: count turns); reset() (serves: reset the count)\n"
          "Data flow: the fixture calls turnstile.py; reset() zeroes the count\n"
          "Diagram: fixture -> turnstile.py -> count\n\n"
          "## Poured concrete (one-way doors)\n"
          "- language %(D)s Python 3.9 %(D)s every bench script imports it\n"
          "- storage %(D)s none in v0 %(D)s nothing is remembered\n\n"
          "## Deferred\n- a web dashboard %(D)s door stays open because the module has no I/O\n\n"
          "## Run log\n"
          "### Run 1 %(D)s 2026-09-21 %(D)s trigger: first run\n"
          "Exit ramp: system\nStep 3.1 (walkthrough target): Sam Bench\nStep 3.2 (candidates): module; service\n"
          "Step 3.3 (one-way doors): language\nRulings: declined\nChanged this run: first run\n") % {"D": D, "M": M}
LIVING_REL = "docs/architecture/2026-09-21-turnstile.md"


def rerun_answer(**over):
    a = archlib.clean_answer(trigger="idea blossomed", changed="storage moves to a file")
    a["questions"].append({"id": "Q5", "text": "Does the count survive a restart now?", "touches": [],
                           "answer": "yes, in a file"})
    a["poured_concrete"] = [
        {"carried": "language %s Python 3.9 %s every bench script imports it" % (D, D)},
        {"strike": "storage %s none in v0 %s nothing is remembered" % (D, D),
         "trace": {"kind": "question", "ref": "Q5"}},
        {"text": "storage %s a JSON file %s the count survives a restart" % (D, D), "tag": "decided",
         "trace": {"kind": "question", "ref": "Q5"}}]
    a["deferred"] = [{"carried": "a web dashboard %s door stays open because the module has no I/O" % D}]
    a.update(over)
    return a


class NoLoss(_Record):

    FILES = {LIVING_REL: LIVING}

    def test_the_clean_rerun_is_accepted(self):
        code, doc, out, err = self.run.record(rerun_answer())
        self.assertEqual(code, 0, out + err)

    def test_a_dropped_poured_line_is_refused_before_any_write(self):
        a = rerun_answer()
        a["poured_concrete"] = [e for e in a["poured_concrete"] if "strike" not in e]
        before = archlib.sha(os.path.join(self.ws, LIVING_REL))
        doc = self.refused(a, "no-loss")
        self.assertTrue(any("storage" in r["message"] for r in doc["refusals"]))
        self.assertEqual(archlib.sha(os.path.join(self.ws, LIVING_REL)), before)

    def test_a_carried_line_the_doc_does_not_hold(self):
        a = rerun_answer()
        a["deferred"].append({"carried": "a phone app %s door stays open because nothing needs it" % D})
        self.refused(a, "unknown-prior-line")


RUN99 = "### Run 99 %s 2026-09-20 %s trigger: list text" % (D, D)


class AListItemShapedLikeARunHeading(_Record):
    """Round 7 R3 (A3): harvest accepts a Deferred list item of the shape `### Run 99 ...` and keeps
    it out of the run numbering; the answer carries or strikes it as plain one-line text, the
    renderer supplies the list prefix, and dropping it stays a loss."""

    FILES = {LIVING_REL: LIVING.replace("## Deferred\n", "## Deferred\n- ~~retired decision~~\n- %s\n" % RUN99)}

    def test_it_is_carried(self):
        a = rerun_answer()
        a["deferred"] += [{"carried": "~~retired decision~~"}, {"carried": RUN99}]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["run"], 2)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(doc["doc"])
        self.assertIn("\n- ~~retired decision~~\n- %s\n" % RUN99, text)
        from station_core import runlog, templates
        self.assertEqual([n for n, _ in runlog.runs(text)], [1, 2])
        self.assertEqual(templates.check("architecture-doc", text), [])

    def test_it_is_struck(self):
        a = rerun_answer()
        a["deferred"] += [{"carried": "~~retired decision~~"},
                          {"strike": RUN99, "trace": {"kind": "question", "ref": "Q5"}}]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertIn("\n- ~~%s~~\n" % RUN99, testlib.read_text(doc["doc"]))

    def test_dropping_it_is_still_a_loss(self):
        a = rerun_answer()
        a["deferred"] += [{"carried": "~~retired decision~~"}]
        self.refused(a, "no-loss")

    def test_a_carried_text_the_section_does_not_hold_is_still_refused(self):
        a = rerun_answer()
        a["deferred"] += [{"carried": "~~retired decision~~"}, {"carried": RUN99},
                          {"carried": "### Run 98 %s 2026-09-20 %s trigger: never there" % (D, D)}]
        self.refused(a, "unknown-prior-line")


class ARunBlockUnderDeferred(unittest.TestCase):
    """A hand-edited living doc whose Run 1 block sits under Deferred: the re-render, which draws
    the Deferred section from the answer, would drop it. Its lines are no list lines, so the run
    stops at harvest `living-doc-malformed`, quoting the block's heading, before anything is asked
    (CA1-11); the no-loss check of such a drop is held at the library by the answer example
    `content-no-loss-run-block`."""

    def test_harvest_stops_quoting_the_block(self):
        tmp = testlib.make_scratch("arch-record-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = archlib.repo_workspace(tmp, files={LIVING_REL: LIVING.replace(
            "## Run log\n### Run 1",
            "### Run 1 %s 2026-09-20 %s trigger: first run\nExit ramp: system\nChanged this run: first run\n\n"
            "## Run log\n### Run 2" % (D, D))})
        before = archlib.sha(os.path.join(ws, LIVING_REL))
        run = archlib.ArchRun(tmp, ws)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "living-doc-malformed")
        self.assertIn("### Run 1", doc["reason"])
        self.assertEqual(archlib.sha(os.path.join(ws, LIVING_REL)), before)


DASHED = archlib.SCOPE.replace(
    "- Where the count is kept between sessions %s parked: needs research\n" % D,
    "- Where the count is kept between sessions %s parked: needs research\n"
    "- counts kept on the bench %s or on the rig server %s parked: waiting on the rig budget\n" % (D, D, D))


class ThePouredDecisionField(_Record):
    """Round 3 R4 (CS-1, the lane's half): the neutral view gives a poured-concrete line's DECISION
    field (`<category> <dash> <decision> <dash> <why>`: everything between the first field and the
    last) as a row's text, with the category and the why beside it, beside the whole line; so the
    shared text rule meets a parked or open line re-asserted as the decision alone, and as the
    whole line, even where the decision itself holds the dash."""

    FILES = {archlib.SCOPE_REL: DASHED}

    def parked(self, text):
        from station_core import ledger
        return next(r for r in ledger.read(DASHED) if r["tag"] == "parked" and r["text"] == text)

    def poured(self, text, trace=None):
        a = archlib.clean_answer()
        for q in a["questions"]:
            q["touches"] = []  # no question of this run settles a parked line here
        a["poured_concrete"].append({"text": text, "tag": "decided",
                                     "trace": trace or {"kind": "assumed", "ref": "it seemed settled"}})
        return a

    def test_the_whole_line_whose_decision_holds_the_dash_is_quietly_resolved(self):
        words = "counts kept on the bench %s or on the rig server" % D
        self.parked(words)
        doc = self.refused(self.poured("storage %s %s %s one-way" % (D, words, D)), "quietly-resolved")
        self.assertEqual(len([r for r in doc["refusals"] if r["rule"] == "quietly-resolved"]), 1, doc["refusals"])

    def test_the_decision_alone_is_quietly_resolved(self):
        words = "counts kept on the bench %s or on the rig server" % D
        self.refused(self.poured(words), "quietly-resolved")
        self.refused(self.poured("Where the count is kept between sessions"), "quietly-resolved")

    def test_the_whole_line_of_a_plain_decision_is_quietly_resolved(self):
        self.refused(self.poured("storage %s Where the count is kept between sessions %s one-way" % (D, D)),
                     "quietly-resolved")

    def test_a_question_that_settled_it_lets_it_pass(self):
        words = "counts kept on the bench %s or on the rig server" % D
        a = self.poured("storage %s %s %s one-way" % (D, words, D), trace={"kind": "question", "ref": "Q9"})
        a["questions"].append({"id": "Q9", "text": "Where are the counts kept?", "touches": [self.parked(words)["id"]],
                               "answer": "on the bench"})
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)

    def test_an_untraced_form_line_is_refused_once(self):
        a = archlib.clean_answer()
        a["poured_concrete"].append({"text": "platform %s macOS %s the bench is a Mac" % (D, D), "tag": "decided"})
        doc = self.refused(a, "untraced")
        self.assertEqual(len([r for r in doc["refusals"] if r["rule"] == "untraced"]), 1, doc["refusals"])


class TheAnswersOwnWords(_Record):
    """Round 6 R1 (the outside reviewer's A1): the shared checker reads the walkthrough's values one by
    one (`who`, `when`, each `must` item, each its own row, its place named) and each `lines` entry's
    own text. The `Who: ... Must be able to:` formatting and the `NEEDS CHECK:` prefix are the doc's
    rendering, added after the check, never the answer's words: an open ledger item asserted as a
    walkthrough value or a `lines` entry is `quietly-resolved`, and write, render and report never
    run on it."""

    OPEN = "how often the counter resets"

    def fields(self, doc, rule="quietly-resolved"):
        return [r.get("field") for r in doc["refusals"] if r["rule"] == rule]

    def test_a_must_item_holding_an_open_item(self):
        a = archlib.clean_answer()
        a["walkthrough"]["must"] = [self.OPEN]
        a["components"] = [{"name": "counter", "serves": self.OPEN}]
        doc = self.refused(a, "quietly-resolved")
        self.assertEqual(self.fields(doc), ["walkthrough/must/0"], doc["refusals"])

    def test_a_who_or_when_holding_an_open_item(self):
        for key in ("who", "when"):
            a = archlib.clean_answer()
            a["walkthrough"][key] = self.OPEN
            doc = self.refused(a, "quietly-resolved")
            self.assertEqual(self.fields(doc), ["walkthrough/%s" % key], doc["refusals"])

    def test_a_lines_entry_holding_an_open_item(self):
        a = archlib.clean_answer()
        a["lines"] = [{"text": self.OPEN, "tag": "decided", "trace": {"kind": "assumed", "ref": "executor"}}]
        doc = self.refused(a, "quietly-resolved")
        self.assertEqual(self.fields(doc), ["lines/0"], doc["refusals"])

    def test_a_question_that_settled_it_lets_it_pass(self):
        a = archlib.clean_answer()
        a["questions"].append({"id": "Q9", "text": "How often does the counter reset?",
                               "touches": [self.i["open"]], "answer": "at every session start"})
        a["walkthrough"]["must"] = [self.OPEN, "count turns"]
        a["components"] = [{"name": "counter", "serves": self.OPEN}, {"name": "turnstile.py", "serves": "count turns"}]
        a["lines"] = [{"text": self.OPEN, "tag": "decided", "trace": {"kind": "question", "ref": "Q9"}}]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)

    def test_an_untraced_walkthrough_is_refused_once(self):
        a = archlib.clean_answer()
        del a["walkthrough"]["trace"]
        doc = self.refused(a, "untraced")
        self.assertEqual(self.fields(doc, "untraced"), ["walkthrough"], doc["refusals"])

    def test_the_escaped_sequence_never_reaches_write_render_or_report(self):
        """The outside reviewer's `paths.py` "escaped fields" sequence: 0, 0, 0, 10 before this round."""
        a = archlib.clean_answer(review={"outcome": "declined", "date": "2026-09-25"}, publish=False)
        a["walkthrough"]["must"] = [self.OPEN]
        a["components"] = [{"name": "counter", "serves": self.OPEN}]
        a["lines"] = [{"text": self.OPEN, "tag": "decided", "trace": {"kind": "assumed", "ref": "executor"}}]
        doc = self.refused(a, "quietly-resolved")
        self.assertEqual(sorted(self.fields(doc)), ["lines/0", "walkthrough/must/0"], doc["refusals"])
        before_ws = archlib.listing(self.ws)
        for step in (self.run.write, self.run.render, self.run.report):
            code, doc, out, err = step()
            self.assertEqual(code, 2, out + err)
        self.assertEqual(archlib.listing(self.ws), before_ws)


class TheAnswerIsNeverRepaired(_Record):

    def test_a_refused_then_corrected_answer(self):
        a = archlib.clean_answer()
        a["rejected"] = []
        self.refused(a, "rejected-mismatch")
        code, doc, out, err = self.run.record(archlib.clean_answer())
        self.assertEqual(code, 0, out + err)


class TheDeferredSectionIsAMoveBack(_Record):
    """Slice 3a round 4, R3 (C3A2-1, landed on the owner's word A8): every entry of the Deferred section is read
    as parked by the next station (blueprint's ledger view), and a `lines` entry renders there as a
    `NEEDS CHECK:` line, so each such entry reaches the frame a second time under the tag `deferred`. A decided
    scope row named by a `deferred` entry or a `lines` entry under any tag is a move back, refused
    `re-asked-decided`; the same entry on another row, or traced to a question, passes."""

    def test_a_decided_row_in_the_deferred_section_is_refused_under_any_tag(self):
        ledger = {"kind": "ledger", "ref": self.i["decided"]}
        for tag in ("assumed", "decided"):
            a = archlib.clean_answer()
            a["lines"] = [{"text": self.i["decided_text"], "tag": tag, "trace": ledger}]
            doc = self.refused(a, "re-asked-decided")
            self.assertIn(self.i["decided"], " ".join(r["message"] for r in doc["refusals"]), tag)
            a = archlib.clean_answer()
            a["deferred"].append({"text": "the stdlib-only rule %s revisit when the bench grows" % D, "tag": tag,
                                  "trace": ledger})
            doc = self.refused(a, "re-asked-decided")
            self.assertIn(self.i["decided"], " ".join(r["message"] for r in doc["refusals"]), tag)

    def test_a_needs_check_line_on_another_row_or_a_question_is_accepted(self):
        for tag in ("assumed", "decided"):
            for trace in ({"kind": "ledger", "ref": self.i["parked"]}, {"kind": "question", "ref": "Q1"}):
                testlib.rmtree(self.run.run_dir)
                code, doc, out, err = self.run.to_harvest()
                self.assertEqual(code, 0, out + err)
                a = archlib.clean_answer()
                a["lines"] = [{"text": "the bench clock drift", "tag": tag, "trace": trace}]
                code, doc, out, err = self.run.record(a)
                self.assertEqual(code, 0, (tag, trace, out + err))
                self.assertTrue(doc["accepted"])


if __name__ == "__main__":
    unittest.main()
