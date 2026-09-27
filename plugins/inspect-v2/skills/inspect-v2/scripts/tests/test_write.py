"""`write` (lane contract section 8, required test 7; family I3), through the real CLI and the
real records component of this checkout, in a scratch git workspace.

The two writes (P8): each surviving finding raised through `records.py append` (one
`finding_raised` per finding, `raised_by` the reader's effective model, the head pinned at
`harvest`, a head that moved surfaced as `records-refused` with the component's sentence), and the
block the component's `render` produces placed at the punch list's tail; then the station's own
lines (QUESTION lines, or the clean line only with zero findings and zero questions) and the stamp,
placed by v1's rule (below the previous stamp; else after the `Out of scope:` block; else above the
first `## Slice`), a prior stamp never rewritten. The verdict mirror under `docs/reviews/`, checked
with `mirrors`. No clear is ever sent. Report-only appends nothing, stamps nothing, mirrors nothing.
The receipt names every write with its hashes; a refused write leaves the bytes as found.
"""
import hashlib
import os
import unittest

import ilib
import testlib

testlib.add_scripts_to_path()

from station_core import templates  # noqa: E402

NEEDS = testlib.checkout_sibling("blueprint-v2") is None or testlib.records_root() is None or \
    testlib.checkout_sibling("readers") is None
R = "run-0001"
MODEL = "claude-test-model"
# round 5, R1: a verified finding survives only with the executor's adjudication
CB1 = [ilib.adjudication("%s-code-book#1" % R)]
GPT1 = [ilib.adjudication("%s-gpt-astra#1" % R)]


@unittest.skipIf(NEEDS, "the installed shape: no blueprint-v2, records or readers beside this core")
class _Write(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("write-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def go(self, fleet, build=ilib.BUILD_DOC, scope=ilib.SCOPE_DOC, report_only=False, last="write", **extra):
        self.ws = ilib.workspace(self.tmp, build=build, scope=scope)
        self.run = ilib.Runner(self.tmp, self.ws)
        doc = ilib.make_input(self.ws, self.run.run_dir, report_only=report_only)
        return self.run.upto(last, doc=doc, answer=ilib.answer(R, fleet, **extra))

    def doc_text(self):
        return testlib.read_text(os.path.join(self.ws, ilib.BUILD_REL))

    def events(self):
        code, body, err = ilib.records_cli(["events", "--workspace", self.ws, "--doc", ilib.BUILD_REL])
        self.assertEqual(code, 0, err)
        return body

    def render(self):
        code, body, err = ilib.records_cli(["render", "--workspace", self.ws, "--doc", ilib.BUILD_REL, "--run-id", R])
        self.assertEqual(code, 0, err)
        return body


class TheRecords(_Write):

    def test_one_event_per_finding_raised_by_the_effective_model(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[
            ilib.finding("build-doc.md:12", quote="AC1"),
            ilib.finding("build-doc.md:5", severity="MINOR", claim="the dashboard reason is thin",
                         scenario="a later reader cannot tell why")])
        code, doc, out, err = self.go(fleet, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        body = self.events()
        raised = [r["event"] for r in body["results"] if r["event"]["kind"] == "finding_raised"]
        self.assertEqual(len(raised), 2)
        self.assertEqual(set(e["raised_by"] for e in raised), {MODEL})
        self.assertEqual(sorted((e["slice"], e["location"]["raw"]) for e in raised),
                         [("A", ilib.BUILD_REL + ":12"), ("plan", ilib.BUILD_REL + ":5")])
        self.assertEqual(set(e["actor"]["station"] for e in raised), {"inspect-v2"})
        kinds = set(r["event"]["kind"] for r in body["results"])
        self.assertEqual(kinds, {"finding_raised"}, "inspect raises and clears nothing")

    def test_the_block_is_renders_text_at_the_punch_list_tail(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        code, doc, out, err = self.go(fleet, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        text = self.doc_text()
        rendered = self.render()["text"]
        self.assertTrue(rendered.startswith("\n### %s \u2014 review: Slice A\n" % ilib.TODAY), rendered)
        punch = text.index("## Punch list\n")
        self.assertEqual(text[punch:punch + len("## Punch list\n") + len(rendered)], "## Punch list\n" + rendered)
        self.assertEqual(templates.check("build-doc", text), [])
        self.assertEqual(templates.render(templates.parse("build-doc", text)), text)

    def test_a_head_that_moved_since_harvest_is_records_refused(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        self.go(fleet, last="record-answer", adjudications=CB1)
        before = testlib.sha256_file(os.path.join(self.ws, ilib.BUILD_REL))
        other = {"v": 1, "kind": "finding_raised", "at": "2026-09-25T11:00:00Z", "ledger_doc": ilib.BUILD_REL,
                 "slice": "A", "severity": "MINOR",
                 "location": {"raw": ilib.BUILD_REL + ":8", "file": ilib.BUILD_REL, "line": 8, "line_end": None,
                              "tag": None, "more": [], "resolved": True},
                 "claim": "another writer", "scenario": "it moved the head", "raised_by": "someone",
                 "actor": {"station": "another-station", "run_id": "other-run", "harness": None},
                 "origin": {"kind": "native"}, "source": {"known": False}}
        events = os.path.join(self.tmp, "other.json")
        testlib.write_json(events, [other])
        code, body, err = ilib.records_cli(["append", "--workspace", self.ws, "--doc", ilib.BUILD_REL,
                                            "--events", events, "--expect-head", "0" * 64])
        self.assertEqual(code, 0, err)
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "records-refused"))
        # round 5, R3: the head read before any write refuses it first; the append's own --expect-head
        # stays behind it (TheHeadIsReadBeforeAnyWrite)
        self.assertIn(body["head"], doc["reason"])
        self.assertIn("pinned at harvest", doc["reason"])
        self.assertIn("conflict", doc["reason"])
        self.assertEqual(testlib.sha256_file(os.path.join(self.ws, ilib.BUILD_REL)), before)
        self.assertFalse(doc["station_result"]["stamp_written"])


class TheHeadIsReadBeforeAnyWrite(_Write):
    """Round 5, R3 (F4): before any workspace write, a clean run's stamp included, `write` reads the
    records head through the component's CLI and compares it with the head `harvest` pinned; a head
    that moved ends the run `records-refused` with no stamp, no mirror, no document write and no
    append. A finding run's append keeps `--expect-head` as well."""

    OTHER = {"v": 1, "kind": "finding_raised", "at": "2026-09-25T11:00:00Z", "ledger_doc": ilib.BUILD_REL,
             "slice": "A", "severity": "MINOR",
             "location": {"raw": ilib.BUILD_REL + ":8", "file": ilib.BUILD_REL, "line": 8, "line_end": None,
                          "tag": None, "more": [], "resolved": True},
             "claim": "competing review", "scenario": "head advanced", "raised_by": "other-reader",
             "actor": {"station": "other-station", "run_id": "other-run", "harness": None},
             "origin": {"kind": "native"}, "source": {"known": False}}

    def compete(self):
        events = os.path.join(self.tmp, "other.json")
        testlib.write_json(events, [self.OTHER])
        code, body, err = ilib.records_cli(["append", "--workspace", self.ws, "--doc", ilib.BUILD_REL,
                                            "--events", events, "--expect-head", "0" * 64])
        self.assertEqual(code, 0, err)
        return body["head"]

    def assert_refused_whole(self, fleet, **extra):
        self.assertEqual(self.go(fleet, last="record-answer", **extra)[0], 0)
        pinned = self.run.artifact("harvest.json")["records"]["head"]
        moved = self.compete()
        digest = testlib.tree_digest(self.ws)
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "records-refused"))
        self.assertIn(moved, doc["reason"])
        self.assertIn(str(pinned), doc["reason"])
        self.assertEqual(testlib.tree_digest(self.ws), digest, "no stamp, no mirror, no document, no append")
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))
        self.assertIsNone(doc["station_result"]["stamp"])
        self.assertFalse(doc["station_result"]["stamp_written"])
        self.assertEqual([w for w in doc["writes"] if w["kind"] != "run_artifact"], [])
        return doc

    def test_a_clean_run_whose_head_moved_writes_nothing(self):
        self.assert_refused_whole(ilib.claude_fleet(R, model=MODEL))

    def test_a_question_only_run_whose_head_moved_writes_nothing(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:14", severity="QUESTION",
                                                                          claim="was the reset deferred")])
        self.assert_refused_whole(fleet)

    def test_a_finding_run_whose_head_moved_appends_nothing(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12")])
        self.assert_refused_whole(fleet, adjudications=[ilib.adjudication("%s-code-book#1" % R)])
        kinds = [(r["event"]["kind"], r["event"]["claim"]) for r in self.events()["results"]]
        self.assertEqual(kinds, [("finding_raised", "competing review")])

    def shim(self):
        """The records test double (`ilib.records_double`): it logs its argv, runs the real component for
        every command, and recognises the verdict mirror at `mirrors` (the capability `write` requires)."""
        return ilib.records_double(self.tmp)

    def logged(self, root):
        import json
        with open(os.path.join(root, "argv.log"), encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_the_head_is_read_through_the_cli_and_the_append_keeps_expect_head(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12")])
        self.assertEqual(self.go(fleet, last="record-answer",
                                 adjudications=[ilib.adjudication("%s-code-book#1" % R)])[0], 0)
        pinned = self.run.artifact("harvest.json")["records"]["head"]
        root = self.shim()
        code, doc, out, err = self.run.phase("write", "--records-root", root)
        self.assertEqual(code, 0, out + err)
        calls = [argv[0] for argv in self.logged(root)]
        self.assertIn("events", calls)
        self.assertIn("append", calls)
        self.assertLess(calls.index("events"), calls.index("append"), calls)
        append = [argv for argv in self.logged(root) if argv[0] == "append"][0]
        self.assertEqual(append[append.index("--expect-head") + 1], pinned)

    def test_a_clean_run_reads_the_head_too(self):
        self.assertEqual(self.go(ilib.claude_fleet(R, model=MODEL), last="record-answer")[0], 0)
        root = self.shim()
        code, doc, out, err = self.run.phase("write", "--records-root", root)
        self.assertEqual(code, 0, out + err)
        calls = [argv[0] for argv in self.logged(root)]
        self.assertIn("events", calls)
        self.assertNotIn("append", calls)


class TheMirrorsCapabilityIsRequired(_Write):
    """The reviewer's F1 (MAJOR), ruling A5(3): before appending findings, stamping the plan or writing the
    verdict, `write` establishes through the records component's `mirrors` that the frozen interface
    recognises the intended verdict mirror (a row whose `verdict_doc` is the mirror's workspace path). When
    it does not, or the component refuses, the run stops `records-refused`, names the missing capability
    and asks for the owner's ruling: no records event, no stamp, no document, no mirror. `recognised:
    false` never completes a run."""

    FIND = [ilib.finding("build-doc.md:12", quote="AC1")]
    MIRROR = "docs/reviews/%s-inspect-turnstile.md" % ilib.TODAY

    def upto_answer(self, records, fleet=None, adjudications=CB1):
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws, records=records)
        fleet = fleet if fleet is not None else ilib.claude_fleet(R, model=MODEL, code_book=self.FIND)
        extra = {"adjudications": adjudications} if adjudications else {}
        self.assertEqual(self.run.upto("record-answer", answer=ilib.answer(R, fleet, **extra))[0], 0)

    def assert_stopped_whole(self, code, doc, out, err):
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "records-refused"))
        self.assertIn(self.MIRROR, doc["reason"])
        self.assertIn("`mirrors`", doc["reason"])
        self.assertIn("owner's ruling", doc["reason"])
        self.assertEqual(testlib.tree_digest(self.ws), self.digest, "no stamp, no mirror, no document, no append")
        self.assertEqual(testlib.sha256_file(os.path.join(self.ws, ilib.BUILD_REL)), self.doc_sha)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "records")), "no records event")
        sr = doc["station_result"]
        self.assertIsNone(sr["stamp"])
        self.assertFalse(sr["stamp_written"])
        self.assertFalse(sr["mirror"]["recognised"])
        self.assertEqual([w for w in doc["writes"] if w["kind"] != "run_artifact"], [])
        wrote = self.run.artifact("write.json")
        self.assertFalse(wrote["stamp_written"])
        self.assertEqual(wrote["records"]["appended"], 0)
        # the stop is final: the run is done, `report` prints the same stopped result
        code, again, out, err = self.run.phase("report")
        self.assertEqual((code, again["status"], again["stop_tag"]), (10, "stopped", "records-refused"))

    def freeze(self):
        self.digest = testlib.tree_digest(self.ws)
        self.doc_sha = testlib.sha256_file(os.path.join(self.ws, ilib.BUILD_REL))

    def test_a_double_that_recognises_the_mirror_lets_the_write_proceed(self):
        self.upto_answer("recognise")
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 0, out + err)
        mirror = self.run.artifact("write.json")["mirror"]
        self.assertIs(mirror["recognised"], True)
        self.assertEqual(mirror["state"], "recognised by the test double")
        self.assertIn(self.MIRROR, [r["verdict_doc"] for r in mirror["answer"]["mirrors"]])
        self.assertTrue(os.path.isfile(os.path.join(self.ws, self.MIRROR)))
        self.assertEqual(len([l for l in self.doc_text().splitlines() if l.startswith("Plan: inspected")]), 1)
        self.assertEqual([r["event"]["kind"] for r in self.events()["results"]], ["finding_raised"])
        # asked before any write: `mirrors` comes before the append, the render and the doc write
        calls = [argv[0] for argv in self.logged()]
        self.assertLess(calls.index("mirrors"), calls.index("append"), calls)
        self.assertEqual(calls.count("mirrors"), 1, calls)

    def logged(self):
        import json
        with open(os.path.join(self.run.double, "argv.log"), encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_a_double_with_no_row_for_the_mirror_stops_a_finding_run_before_any_write(self):
        self.upto_answer("other")
        self.freeze()
        code, doc, out, err = self.run.phase("write")
        self.assert_stopped_whole(code, doc, out, err)
        self.assertIn("does not recognise", doc["reason"])
        self.assertNotIn("append", [argv[0] for argv in self.logged()])

    def test_a_double_with_no_row_for_the_mirror_stops_a_clean_run_before_the_stamp(self):
        self.upto_answer("other", fleet=ilib.claude_fleet(R, model=MODEL), adjudications=None)
        self.freeze()
        self.assert_stopped_whole(*self.run.phase("write"))

    def test_a_double_that_refuses_mirrors_stops_with_its_sentence(self):
        self.upto_answer("refuse")
        self.freeze()
        code, doc, out, err = self.run.phase("write")
        self.assert_stopped_whole(code, doc, out, err)
        self.assertIn(ilib.DOUBLE_REFUSAL, doc["reason"])
        self.assertIn("exit 4", doc["reason"])

    def test_the_real_component_of_this_checkout_stops_every_write(self):
        # the consequence the ruling states: the frozen component's `mirrors` lists signoff verdict docs
        # only, so against it every `write` stops here until the owner rules (E14-2)
        self.upto_answer("real")
        self.freeze()
        code, doc, out, err = self.run.phase("write")
        self.assert_stopped_whole(code, doc, out, err)
        kept = doc["station_result"]["mirror"]["answer"]
        self.assertEqual(kept["doc"], ilib.BUILD_REL, "the component's own answer, kept whole")
        self.assertNotIn(self.MIRROR, [r.get("verdict_doc") for r in kept["mirrors"]])

    def test_a_resumed_write_still_asks_first(self):
        self.upto_answer("other")
        self.freeze()
        self.assert_stopped_whole(*self.run.phase("write"))
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 2, out + err)
        self.assertEqual(testlib.tree_digest(self.ws), self.digest)

    def test_a_completed_result_with_an_unrecognised_mirror_does_not_validate(self):
        import copy
        import json
        from station_core import validate
        path = os.path.join(testlib.EX, "result", "valid", "completed-a-document-written.json")
        with open(path, encoding="utf-8") as fh:
            good = json.load(fh)
        schema = validate.load_schema("result", testlib.PREFIX, testlib.SKILL)
        self.assertEqual(validate.errors_for(good, schema, testlib.PREFIX), [])
        self.assertIs(good["station_result"]["mirror"]["recognised"], True)
        for recognised in (False, None):
            bad = copy.deepcopy(good)
            bad["station_result"]["mirror"]["recognised"] = recognised
            self.assertNotEqual(validate.errors_for(bad, schema, testlib.PREFIX), [], recognised)
        bad = copy.deepcopy(good)
        bad["station_result"]["mirror"] = None
        self.assertNotEqual(validate.errors_for(bad, schema, testlib.PREFIX), [])


class TheStationsOwnLines(_Write):

    def stamp_lines(self):
        return [l for l in self.doc_text().splitlines() if l.startswith("Plan: inspected")]

    def test_a_first_stamp_goes_after_the_out_of_scope_block(self):
        build = ilib.BUILD_DOC.replace("Out of scope: a web dashboard \u2014 declined in the scope doc\n",
                                       "Out of scope:\n- a web dashboard \u2014 declined\n- a reset \u2014 later\n")
        code, doc, out, err = self.go(ilib.claude_fleet(R, model=MODEL), build=build, hunted_and_held="all held")
        self.assertEqual(code, 0, out + err)
        lines = self.doc_text().splitlines()
        at = lines.index("- a reset \u2014 later")
        self.assertEqual(lines[at + 1], "Plan: inspected %s by %s · clean" % (ilib.TODAY, MODEL))

    def test_a_doc_with_no_out_of_scope_stamps_above_the_first_slice(self):
        build = ilib.BUILD_DOC.replace("Out of scope: a web dashboard \u2014 declined in the scope doc\n", "")
        code, doc, out, err = self.go(ilib.claude_fleet(R, model=MODEL), build=build, hunted_and_held="all held")
        self.assertEqual(code, 0, out + err)
        lines = self.doc_text().splitlines()
        at = lines.index("## Slice A \u2014 Count turns")
        self.assertEqual(lines[at - 1], "Plan: inspected %s by %s · clean" % (ilib.TODAY, MODEL))

    def test_a_second_stamp_goes_below_the_first_which_is_never_rewritten(self):
        prior = "Plan: inspected 2026-09-01 by an-older-model · 1 BLOCKER · 0 MAJOR · 0 MINOR"
        build = ilib.BUILD_DOC.replace("declined in the scope doc\n", "declined in the scope doc\n%s\n" % prior)
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:14", quote="Footprint")])
        code, doc, out, err = self.go(fleet, build=build, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        stamps = self.stamp_lines()
        self.assertEqual(stamps, [prior, "Plan: inspected %s by %s · 0 BLOCKER · 1 MAJOR · 0 MINOR"
                                  % (ilib.TODAY, MODEL)])
        lines = self.doc_text().splitlines()
        self.assertEqual(lines.index(stamps[1]), lines.index(prior) + 1)

    def test_the_clean_line_only_with_no_finding_and_no_question(self):
        code, doc, out, err = self.go(ilib.claude_fleet(R, model=MODEL), hunted_and_held="all held")
        self.assertEqual(code, 0, out + err)
        text = self.doc_text()
        self.assertTrue(text.endswith("## Punch list\n\nclean \u2014 no surviving findings or questions · %s\n" % MODEL), text[-300:])
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "records")), "no finding, no log")

    def test_questions_write_their_lines_and_no_clean_line(self):
        fleet = ilib.claude_fleet(R, model=MODEL, traceability=[ilib.finding(
            "build-doc.md:10", severity="BLOCKER", claim="R1 traces to nothing in the record")])
        code, doc, out, err = self.go(fleet, scope=None)
        self.assertEqual(code, 0, out + err)
        text = self.doc_text()
        self.assertIn("\nQUESTION · %s:10 · R1 traces to nothing in the record · %s\n" % (ilib.BUILD_REL, MODEL), text)
        self.assertNotIn("clean \u2014", text)
        self.assertEqual(self.stamp_lines(), ["Plan: inspected %s by %s · 0 BLOCKER · 0 MAJOR · 0 MINOR · 1 QUESTION" % (ilib.TODAY, MODEL)])
        for line in text.splitlines():
            if line.startswith("QUESTION"):
                self.assertEqual(templates.parse_line(line)["kind"], "question")

    def test_no_status_line_and_no_verdict_word_is_written(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", severity="BLOCKER", quote="AC1")])
        code, doc, out, err = self.go(fleet, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        text = self.doc_text()
        self.assertEqual([l for l in text.splitlines() if l.startswith("Status:")], ["Status: not started"])
        self.assertNotIn("REJECTED", text)
        original = ilib.BUILD_DOC.splitlines()
        kept = [l for l in text.splitlines() if l in original]
        self.assertEqual([l for l in original if l], [l for l in kept if l], "additive only")


class ThePlacementRule(unittest.TestCase):
    """CI1-8: v1's stamp placement, on the two shapes round 1 placed wrong (the library, no run)."""

    def place(self, lines):
        from inspect_core import writing
        return writing.stamp_index([l + "\n" for l in lines])

    def test_an_out_of_scope_block_under_a_heading_is_found(self):
        lines = ["# Turnstile build plan", "", "## Header", "Intent: count turns.",
                 "Out of scope:", "- a web dashboard", "- a reset", "", "## Slice A", "Status: not started"]
        self.assertEqual(self.place(lines), lines.index("- a reset") + 1)

    def test_a_prior_stamp_that_does_not_parse_strictly_is_still_the_previous_stamp(self):
        lines = ["# Turnstile build plan", "Out of scope: a dashboard",
                 "Plan: inspected 2026-09-01 by  someone \u00b7 clean", "", "## Slice A"]
        self.assertEqual(self.place(lines), 3)

    def test_a_stamp_inside_a_fence_is_not_a_stamp(self):
        lines = ["# Turnstile build plan", "Out of scope: a dashboard", "```",
                 "Plan: inspected 2026-09-01 by m \u00b7 clean", "```", "## Slice A"]
        self.assertEqual(self.place(lines), 2)

    def test_a_slice_body_line_that_starts_like_a_stamp_never_pulls_the_stamp(self):
        # round 3, R3 (CI2-2): the stamp's home is found from the header and the `Out of scope:` block
        lines = ["# Turnstile build plan", "Intent: count turns.", "Out of scope:", "- a web dashboard", "",
                 "## Slice A \u2014 Count turns", "Goal: count.", "Plan: inspected by hand before the build",
                 "Depends on: nothing", "Status: not started", "", "## Punch list"]
        self.assertEqual(self.place(lines), lines.index("- a web dashboard") + 1)

    def test_a_prior_stamp_above_the_first_slice_still_wins_over_a_slice_body_line(self):
        lines = ["# Turnstile build plan", "Out of scope: a dashboard",
                 "Plan: inspected 2026-09-01 by m \u00b7 clean", "", "## Slice A",
                 "Plan: inspected the fixture by hand", "Status: not started"]
        self.assertEqual(self.place(lines), 3)

    def test_with_no_slice_a_punch_list_line_never_pulls_the_stamp(self):
        lines = ["# Turnstile build plan", "Out of scope: a dashboard", "", "## Punch list",
                 "Plan: inspected by hand, a note"]
        self.assertEqual(self.place(lines), 2)


class TheMirrorAndTheReceipt(_Write):

    def test_the_mirror_holds_the_block_and_mirrors_is_asked(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        code, doc, out, err = self.go(fleet, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        mirror = os.path.join(self.ws, "docs", "reviews", "%s-inspect-turnstile.md" % ilib.TODAY)
        self.assertTrue(os.path.isfile(mirror))
        self.assertIn(self.render()["text"], testlib.read_text(mirror))
        receipt = self.run.artifact("receipt.json")
        mirror_row = self.run.artifact("write.json")["mirror"]
        self.assertEqual(mirror_row["path"], mirror)
        self.assertIsNotNone(mirror_row["state"], "records.py mirrors was asked and its answer kept")
        self.assertIn(mirror, [w["path"] for w in receipt["writes"]])

    def test_the_mirrors_answer_is_kept_verbatim(self):
        # CI1-6: the component's `mirrors` answer is kept whole, never only a derived word
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        code, doc, out, err = self.go(fleet, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        # the component `write` asked is the test double (it recognises the mirror, F1); asked again, it
        # gives the same answer the run kept, byte for byte, all but the version fields
        import json
        import subprocess
        import sys
        proc = subprocess.run([sys.executable, os.path.join(self.run.double, "scripts", "records.py"), "mirrors",
                               "--workspace", self.ws, "--doc", ilib.BUILD_REL], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=self.run.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        body = json.loads(proc.stdout.decode("utf-8"))
        kept = self.run.artifact("write.json")["mirror"]["answer"]
        drop = ("interface_version", "plugin_version", "component_version")
        self.assertEqual(dict((k, v) for k, v in kept.items() if k not in drop),
                         dict((k, v) for k, v in body.items() if k not in drop))
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["station_result"]["mirror"]["answer"], kept)

    def test_a_same_day_repeat_takes_the_next_mirror_name(self):
        fleet = ilib.claude_fleet(R, model=MODEL)
        self.go(fleet, hunted_and_held="held")
        again = ilib.Runner(self.tmp, self.ws, run_dir=os.path.join(self.tmp, "run2"))
        again.upto("write", doc=ilib.make_input(self.ws, again.run_dir, run_id="run-0002"),
                   answer=ilib.answer("run-0002", ilib.claude_fleet("run-0002", model=MODEL), hunted_and_held="held"))
        names = sorted(os.listdir(os.path.join(self.ws, "docs", "reviews")))
        self.assertEqual(names, ["%s-inspect-turnstile-2.md" % ilib.TODAY, "%s-inspect-turnstile.md" % ilib.TODAY])

    def test_the_receipt_names_every_write_with_its_hashes(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        before = hashlib.sha256(ilib.BUILD_DOC.encode("utf-8")).hexdigest()
        code, doc, out, err = self.go(fleet, adjudications=CB1)
        self.assertEqual(code, 0, out + err)
        writes = dict((w["path"], w) for w in self.run.artifact("receipt.json")["writes"])
        path = os.path.join(self.ws, ilib.BUILD_REL)
        self.assertEqual(writes[path]["kind"], "document")
        self.assertEqual(writes[path]["sha256_before"], before)
        self.assertEqual(writes[path]["sha256_after"], testlib.sha256_file(path))
        logs = [w for w in writes.values() if w["kind"] == "records_log"]
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0]["path"].startswith(os.path.join(self.ws, "docs", "records") + os.sep))

    def test_a_doc_edited_after_harvest_is_write_refused_and_left_as_found(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        self.go(fleet, last="record-answer", adjudications=CB1)
        path = os.path.join(self.ws, ilib.BUILD_REL)
        testlib.write_text(path, testlib.read_text(path) + "an edit by hand\n")
        before = testlib.sha256_file(path)
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "write-refused")
        self.assertEqual(testlib.sha256_file(path), before)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "records")), "nothing appended")


class TheRawCopies(_Write):
    """The banner goes on the raw copy readers filed at the request's own `raw_path`, and nowhere else."""

    def outside(self, raw_of):
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra",
                              owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        self.run.upto("request", doc=doc)
        named = self.run.artifact("requests.json")["calls"][0]["raw_path"]
        testlib.write_text(named, "the reader's reply\n")
        other = os.path.join(self.ws, "docs", "reviews", "2026-09-01-signoff-turnstile-a.md")
        testlib.write_text(other, "a signoff verdict doc\n")
        paths = {"named": named, "other": other}
        fleet = [ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model",
                                    raw_path=paths[raw_of]),
                 ilib.reader_result("%s-repo-reality" % R, model=MODEL)]
        path = os.path.join(self.tmp, "answer.json")
        testlib.write_json(path, ilib.answer(R, fleet, row="gpt-astra", hunted_and_held="held",
                                             owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"}))
        code, out_doc, out, err = self.run.phase("record-answer", "--answer", path)
        self.assertEqual(code, 0, out + err)
        code, out_doc, out, err = self.run.phase("write")
        self.assertEqual(code, 0, out + err)
        return paths

    def test_the_named_copy_gets_the_banner_once(self):
        paths = self.outside("named")
        text = testlib.read_text(paths["named"])
        self.assertTrue(text.startswith("Raw inspector output \u2014 unverified."), text)
        self.assertTrue(text.endswith("the reader's reply\n"))
        self.assertEqual(testlib.read_text(paths["other"]), "a signoff verdict doc\n")
        stamps = [l for l in self.doc_text().splitlines() if l.startswith("Plan: inspected")]
        self.assertEqual(stamps, ["Plan: inspected %s by gpt-test-model \u00b7 clean" % ilib.TODAY])

    def test_a_raw_path_that_is_not_the_calls_is_left_alone(self):
        paths = self.outside("other")
        self.assertEqual(testlib.read_text(paths["other"]), "a signoff verdict doc\n")
        # round 3, R1: the request's own raw_path is the one source, so the copy readers filed there is
        # bannered whatever path the result names
        self.assertTrue(testlib.read_text(paths["named"]).startswith("Raw inspector output \u2014 unverified."))


class TheBannerBeforeTriage(_Write):
    """R2 (CI1-2): the banner goes on the outside raw copy at `record-answer`, before anything is triaged,
    on every run that records one, a stopped run included; a short fleet is named in the mirror (R1)."""

    WORD = {"rows": ["gpt-astra"], "words": "send it to gpt-astra"}

    def recorded(self, paper_extra=None, with_repo=True):
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra", owner_word=self.WORD)
        self.run.upto("request", doc=doc)
        self.raw = self.run.artifact("requests.json")["calls"][0]["raw_path"]
        testlib.write_text(self.raw, "the reader's reply\n")
        paper = ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model", raw_path=self.raw,
                                   findings=[ilib.finding("build-doc.md:12", quote="AC1")])
        paper.update(paper_extra or {})
        fleet = [paper] + ([ilib.reader_result("%s-repo-reality" % R, model=MODEL)] if with_repo else [])
        path = os.path.join(self.tmp, "answer.json")
        testlib.write_json(path, ilib.answer(R, fleet, row="gpt-astra", owner_word=self.WORD, adjudications=GPT1))
        return self.run.phase("record-answer", "--answer", path)

    def assert_bannered(self):
        text = testlib.read_text(self.raw)
        self.assertTrue(text.startswith("Raw inspector output \u2014 unverified."), text)
        self.assertEqual(text.count("Raw inspector output"), 1)
        self.assertTrue(text.endswith("the reader's reply\n"))

    def test_the_banner_is_on_before_write_runs(self):
        code, doc, out, err = self.recorded()
        self.assertEqual(code, 0, out + err)
        self.assert_bannered()
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 0, out + err)
        self.assert_bannered()
        writes = [w for w in self.run.artifact("receipt.json")["writes"] if w["path"] == self.raw]
        self.assertEqual(len(writes), 1, "the banner write is in the receipt once")

    def test_a_lane_down_stop_leaves_the_copy_bannered_and_says_so(self):
        code, doc, out, err = self.recorded({"status": "incomplete", "reason": "the reply was cut off"})
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "lane-down")
        self.assert_bannered()
        self.assertIn(self.raw, [w["path"] for w in doc["writes"]])
        self.assertFalse(doc["wrote_nothing"])

    def test_a_no_effective_model_stop_leaves_the_copy_bannered(self):
        code, doc, out, err = self.recorded({"effective_model": None})
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "no-effective-model")
        self.assert_bannered()

    def test_a_short_fleet_is_lane_down_and_leaves_the_copy_bannered(self):
        # round 5, R2: a recorded fleet holds one result per built call; a missing one is lane-down,
        # nothing triaged, raised or stamped, and the raw copy keeps its banner
        code, doc, out, err = self.recorded(with_repo=False)
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "lane-down")
        self.assertIn("%s-repo-reality" % R, doc["reason"])
        self.assert_bannered()
        self.assertFalse(doc["station_result"]["stamp_written"])
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "records")))


class TheBannerOnAContentRefusal(_Write):
    """The owner's ruling C4 (the check 5 observation): a content refusal at `record-answer` (exit 5,
    nothing recorded) also puts the banner on every outside raw copy, so an executor who abandons the run
    after the refusal leaves no bare copy. Nothing else of the refusal changes: exit 5, `accepted` false,
    the answer not recorded. A run with no outside copy writes no banner file at a refusal."""

    WORD = {"rows": ["gpt-astra"], "words": "send it to gpt-astra"}
    MINE = "raw reply: this run's own copy\n"
    PRIOR = "an earlier run's reply, never bannered\n"

    def refused(self, adjudications=None):
        """An outside run: an earlier same-day copy at the base (bare), this run's at -2; the paper result
        holds a finding with a citation that holds and, unless given, no adjudication."""
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra", owner_word=self.WORD)
        self.assertEqual(self.run.upto("request", doc=doc)[0], 0)
        base = self.run.artifact("requests.json")["calls"][0]["raw_path"]
        stem, ext = os.path.splitext(base)
        self.copies = [base, stem + "-2" + ext]
        testlib.write_text(self.copies[0], self.PRIOR)
        testlib.write_text(self.copies[1], self.MINE)
        paper = ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model", raw_path=self.copies[1],
                                   findings=[ilib.finding("build-doc.md:12", quote="AC1")])
        fleet = [paper, ilib.reader_result("%s-repo-reality" % R, model=MODEL)]
        extra = {"adjudications": adjudications} if adjudications else {}
        self.answer = os.path.join(self.tmp, "answer.json")
        testlib.write_json(self.answer, ilib.answer(R, fleet, row="gpt-astra", owner_word=self.WORD, **extra))
        return self.run.phase("record-answer", "--answer", self.answer)

    def assert_bannered(self):
        for path, tail in zip(self.copies, (self.PRIOR, self.MINE)):
            text = testlib.read_text(path)
            self.assertTrue(text.startswith("Raw inspector output \u2014 unverified."), path)
            self.assertEqual(text.count("Raw inspector output"), 1, path)
            self.assertTrue(text.endswith(tail), path)

    def test_a_refused_answer_leaves_the_banner_on_every_outside_raw_copy(self):
        code, doc, out, err = self.refused()
        self.assertEqual(code, 5, out + err)
        self.assertIs(doc["accepted"], False)
        self.assertEqual([r["rule"] for r in doc["refusals"]], ["missing-adjudication"])
        self.assert_bannered()
        self.assertEqual(sorted(w["path"] for w in self.run.artifact("banner.json")["writes"]), sorted(self.copies))
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")), "the answer is not recorded")
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "triage.json")))
        self.assertEqual(self.run.phase("write")[0], 2, "the run stays where it was")

    def test_a_corrected_answer_after_the_refusal_keeps_the_banner_writes_once(self):
        self.assertEqual(self.refused()[0], 5)
        code, doc, out, err = self.run.phase("record-answer", "--answer", self.answer)
        self.assertEqual(code, 5, "the same refused answer again: still refused")
        self.assert_bannered()
        testlib.write_json(self.answer, dict(testlib.load_json(self.answer), adjudications=GPT1))
        code, doc, out, err = self.run.phase("record-answer", "--answer", self.answer)
        self.assertEqual(code, 0, out + err)
        self.assert_bannered()
        banners = [w["path"] for w in self.run.artifact("banner.json")["writes"]]
        self.assertEqual(sorted(banners), sorted(self.copies), "each copy's banner write named once")
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 0, out + err)
        receipt = [w["path"] for w in self.run.artifact("receipt.json")["writes"]]
        for path in self.copies:
            self.assertEqual(receipt.count(path), 1, path)

    def test_a_claude_row_refusal_writes_no_banner_file(self):
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        code, doc, out, err = self.run.upto("record-answer", answer=ilib.answer(R, fleet))
        self.assertEqual(code, 5, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "banner.json")))
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer.json")))


class TheRequestsRawPathIsTheOneSource(_Write):
    """Round 3, R1 (CI1-2's class): the banner keys on the request's own `raw_path` (recorded at `request`),
    never on the result's optional field: with the result's `raw_path` present, absent, or pointing
    elsewhere, `record-answer` banners the copy readers filed at the request's path, a stop at any tag
    afterwards leaves no bare copy, and the chat prints the real raw path for an outside lane."""

    WORD = {"rows": ["gpt-astra"], "words": "send it to gpt-astra"}

    def recorded(self, raw_of, paper_extra=None, file_at="named"):
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra", owner_word=self.WORD)
        self.run.upto("request", doc=doc)
        self.named = self.run.artifact("requests.json")["calls"][0]["raw_path"]
        base, ext = os.path.splitext(self.named)
        self.variant = base + "-2" + ext
        self.other = os.path.join(self.ws, "docs", "reviews", "2026-09-01-signoff-turnstile-a.md")
        testlib.write_text(self.other, "a signoff verdict doc\n")
        self.raw = {"named": self.named, "variant": self.variant}[file_at]
        testlib.write_text(self.raw, "raw reply: BLOCKER everything is wrong\n")
        paper = ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model",
                                   findings=[ilib.finding("build-doc.md:12", quote="AC1")])
        if raw_of is not None:
            paper["raw_path"] = {"named": self.named, "variant": self.variant, "other": self.other}[raw_of]
        paper.update(paper_extra or {})
        fleet = [paper, ilib.reader_result("%s-repo-reality" % R, model=MODEL)]
        path = os.path.join(self.tmp, "answer.json")
        testlib.write_json(path, ilib.answer(R, fleet, row="gpt-astra", owner_word=self.WORD, adjudications=GPT1))
        return self.run.phase("record-answer", "--answer", path)

    def assert_bannered(self, path=None):
        text = testlib.read_text(path or self.raw)
        self.assertTrue(text.startswith("Raw inspector output \u2014 unverified."), text)
        self.assertEqual(text.count("Raw inspector output"), 1)
        self.assertTrue(text.endswith("raw reply: BLOCKER everything is wrong\n"))

    def test_absent_on_a_lane_down_stop(self):
        code, doc, out, err = self.recorded(None, {"status": "incomplete", "reason": "cut off"})
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "lane-down")
        self.assert_bannered()
        self.assertIn(self.raw, [w["path"] for w in doc["writes"]])

    def test_absent_on_a_no_effective_model_stop(self):
        code, doc, out, err = self.recorded(None, {"effective_model": None})
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "no-effective-model")
        self.assert_bannered()

    def test_absent_then_a_write_refused_stop(self):
        code, doc, out, err = self.recorded(None)
        self.assertEqual(code, 0, out + err)
        with open(os.path.join(self.ws, ilib.BUILD_REL), "a", encoding="utf-8") as fh:
            fh.write("an edit by hand\n")
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "write-refused")
        self.assert_bannered()
        self.assertIn(self.raw, [w["path"] for w in doc["writes"]])

    def test_absent_on_a_completed_run_the_chat_names_the_real_raw_path(self):
        code, doc, out, err = self.recorded(None)
        self.assertEqual(code, 0, out + err)
        self.assert_bannered()
        self.assertEqual(self.run.phase("write")[0], 0)
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 10, out + err)
        self.assert_bannered()
        raw_line = [l for l in doc["chat"].splitlines() if l.startswith("Raw:")]
        self.assertEqual(raw_line, ["Raw: %s" % self.named])

    def test_present_the_chat_names_it(self):
        code, doc, out, err = self.recorded("named")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.run.phase("write")[0], 0)
        code, doc, out, err = self.run.phase("report")
        self.assert_bannered()
        self.assertEqual([l for l in doc["chat"].splitlines() if l.startswith("Raw:")], ["Raw: %s" % self.named])

    def test_pointing_elsewhere_the_requests_copy_is_bannered_and_the_other_left_alone(self):
        code, doc, out, err = self.recorded("other", {"status": "transport-failed", "reason": "no reply"})
        self.assertEqual(code, 10, out + err)
        self.assert_bannered()
        self.assertEqual(testlib.read_text(self.other), "a signoff verdict doc\n")
        self.assertNotIn(self.other, [w["path"] for w in doc["writes"]])

    def test_pointing_elsewhere_on_a_completed_run_the_chat_names_the_requests_copy(self):
        code, doc, out, err = self.recorded("other")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.run.phase("write")[0], 0)
        code, doc, out, err = self.run.phase("report")
        self.assertEqual([l for l in doc["chat"].splitlines() if l.startswith("Raw:")], ["Raw: %s" % self.named])
        self.assertEqual(testlib.read_text(self.other), "a signoff verdict doc\n")

    def test_absent_and_readers_filed_the_numbered_variant(self):
        code, doc, out, err = self.recorded(None, {"status": "empty", "reason": "no text"}, file_at="variant")
        self.assertEqual(code, 10, out + err)
        self.assert_bannered(self.variant)
        self.assertFalse(os.path.exists(self.named))


class TheVariantFamilyNumbering(unittest.TestCase):
    """Round 4, R1: `common.raw_variant` accepts every member of readers' same-day family, `-2` to `-9`
    and `-10` onwards, and nothing else."""

    WANT = "/w/docs/reviews/2026-09-25-inspect-turnstile-gpt.md"

    def member(self, tail):
        from inspect_core import common
        return common.raw_variant("/w/docs/reviews/2026-09-25-inspect-turnstile-gpt%s.md" % tail, self.WANT)

    def test_every_member_of_the_family(self):
        for tail in ("", "-2", "-3", "-9", "-10", "-11", "-19", "-20", "-99", "-100", "-123"):
            self.assertTrue(self.member(tail), tail)

    def test_nothing_else(self):
        for tail in ("-0", "-1", "-01", "-02", "-010", "-2a", "-", "--2", "-2-3", "2", "-x", "-10.5"):
            self.assertFalse(self.member(tail), tail)


class TheWholeFamilyIsBannered(_Write):
    """Round 4, R1 (CI1-2's fourth round): the raw copy's banner never depends on what the result names.
    `record-answer` banners the request's own `raw_path` and every existing `-N` variant of it; the chat's
    `Raw:` prints the member the result names when it exists in the family, else every member. A same-day
    repeat files this run's copy at a variant while an earlier run's copy sits at the base."""

    WORD = {"rows": ["gpt-astra"], "words": "send it to gpt-astra"}
    PRIOR = ("Raw inspector output \u2014 unverified. Findings absent from the chat verdict were refuted or "
             "could not be verified. Nothing in this file has standing.\n\nan earlier run's reply\n")
    MINE = "raw reply: this run's own copy\n"

    def path(self, n):
        base, ext = os.path.splitext(self.want)
        return self.want if n == 1 else "%s-%d%s" % (base, n, ext)

    def repeat(self, earlier, mine, names, paper_extra=None):
        """Earlier runs filed copies 1 (the base) to `earlier`, bannered; this run's copy is at `mine`;
        the result names `names` (a member number, or None for no `raw_path`)."""
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra", owner_word=self.WORD)
        self.assertEqual(self.run.upto("request", doc=doc)[0], 0)
        self.want = self.run.artifact("requests.json")["calls"][0]["raw_path"]
        for n in range(1, earlier + 1):
            testlib.write_text(self.path(n), self.PRIOR)
        self.mine = self.path(mine)
        testlib.write_text(self.mine, self.MINE)
        paper = ilib.reader_result("%s-gpt-astra" % R, row="gpt-astra", model="gpt-test-model",
                                   findings=[ilib.finding("build-doc.md:12", quote="AC1")])
        if names is not None:
            paper["raw_path"] = self.path(names)
        paper.update(paper_extra or {})
        fleet = [paper, ilib.reader_result("%s-repo-reality" % R, model=MODEL)]
        answer = os.path.join(self.tmp, "answer.json")
        testlib.write_json(answer, ilib.answer(R, fleet, row="gpt-astra", owner_word=self.WORD, adjudications=GPT1))
        return self.run.phase("record-answer", "--answer", answer)

    def family(self, upto):
        return [self.path(n) for n in range(1, upto + 1)]

    def assert_no_bare_copy(self, upto):
        for p in self.family(upto):
            text = testlib.read_text(p)
            self.assertTrue(text.startswith("Raw inspector output \u2014 unverified."), p)
            self.assertEqual(text.count("Raw inspector output"), 1, p)
        self.assertTrue(testlib.read_text(self.mine).endswith(self.MINE))

    def raw_line(self):
        self.assertEqual(self.run.phase("write")[0], 0)
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 10, out + err)
        return [l for l in doc["chat"].splitlines() if l.startswith("Raw:")]

    # H: a same-day repeat, the earlier copy at the base, this run's at -2
    def test_h_the_result_names_the_requests_own_path(self):
        code, doc, out, err = self.repeat(1, 2, 1)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(2)
        self.assertIn(self.mine, [w["path"] for w in self.run.artifact("banner.json")["writes"]])
        # the result names an existing member: the chat prints that one, never an unnamed earlier copy
        self.assertEqual(self.raw_line(), ["Raw: %s" % self.want])
        self.assert_no_bare_copy(2)

    def test_h_the_result_names_a_variant_that_does_not_exist(self):
        code, doc, out, err = self.repeat(1, 2, 3)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(2)
        self.assertFalse(os.path.exists(self.path(3)))
        self.assertEqual(self.raw_line(), ["Raw: %s, %s" % (self.want, self.mine)])

    def test_h_the_result_names_this_runs_copy(self):
        code, doc, out, err = self.repeat(1, 2, 2)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(2)
        self.assertEqual(self.raw_line(), ["Raw: %s" % self.mine])

    def test_h_the_result_names_nothing(self):
        code, doc, out, err = self.repeat(1, 2, None)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(2)
        self.assertEqual(self.raw_line(), ["Raw: %s, %s" % (self.want, self.mine)])

    # I: the base and -2 to -9 filed by earlier runs, this run's copy at -10 (and the same for -11)
    def test_i_the_tenth_copy_named(self):
        code, doc, out, err = self.repeat(9, 10, 10)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(10)
        self.assertEqual(self.raw_line(), ["Raw: %s" % self.mine])

    def test_i_the_tenth_copy_named_by_nothing(self):
        code, doc, out, err = self.repeat(9, 10, None)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(10)
        self.assertEqual(self.raw_line(), ["Raw: %s" % ", ".join(self.family(10))])

    def test_i_the_eleventh_copy_named(self):
        code, doc, out, err = self.repeat(10, 11, 11)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(11)
        self.assertEqual(self.raw_line(), ["Raw: %s" % self.mine])

    def test_i_the_eleventh_copy_named_by_nothing(self):
        code, doc, out, err = self.repeat(10, 11, None)
        self.assertEqual(code, 0, out + err)
        self.assert_no_bare_copy(11)

    # a stop at each tag after record-answer leaves no bare copy (this run at -2, the result naming the base)
    def test_stop_lane_down(self):
        code, doc, out, err = self.repeat(1, 2, 1, {"status": "incomplete", "reason": "cut off"})
        self.assertEqual((code, doc["stop_tag"]), (10, "lane-down"), out + err)
        self.assert_no_bare_copy(2)
        self.assertIn(self.mine, [w["path"] for w in doc["writes"]])

    def test_stop_no_effective_model(self):
        code, doc, out, err = self.repeat(1, 2, 1, {"effective_model": None})
        self.assertEqual((code, doc["stop_tag"]), (10, "no-effective-model"), out + err)
        self.assert_no_bare_copy(2)
        self.assertIn(self.mine, [w["path"] for w in doc["writes"]])

    def test_stop_write_refused(self):
        self.assertEqual(self.repeat(1, 2, 1)[0], 0)
        with open(os.path.join(self.ws, ilib.BUILD_REL), "a", encoding="utf-8") as fh:
            fh.write("an edit by hand\n")
        code, doc, out, err = self.run.phase("write")
        self.assertEqual((code, doc["stop_tag"]), (10, "write-refused"), out + err)
        self.assert_no_bare_copy(2)
        self.assertIn(self.mine, [w["path"] for w in doc["writes"]])

    def test_stop_records_refused(self):
        self.assertEqual(self.repeat(1, 2, 1)[0], 0)
        other = {"v": 1, "kind": "finding_raised", "at": "2026-09-25T11:00:00Z", "ledger_doc": ilib.BUILD_REL,
                 "slice": "A", "severity": "MINOR",
                 "location": {"raw": ilib.BUILD_REL + ":8", "file": ilib.BUILD_REL, "line": 8, "line_end": None,
                              "tag": None, "more": [], "resolved": True},
                 "claim": "another writer", "scenario": "it moved the head", "raised_by": "someone",
                 "actor": {"station": "another-station", "run_id": "other-run", "harness": None},
                 "origin": {"kind": "native"}, "source": {"known": False}}
        events = os.path.join(self.tmp, "other.json")
        testlib.write_json(events, [other])
        code, body, err = ilib.records_cli(["append", "--workspace", self.ws, "--doc", ilib.BUILD_REL,
                                            "--events", events, "--expect-head", "0" * 64])
        self.assertEqual(code, 0, err)
        code, doc, out, err = self.run.phase("write")
        self.assertEqual((code, doc["stop_tag"]), (10, "records-refused"), out + err)
        self.assert_no_bare_copy(2)
        self.assertIn(self.mine, [w["path"] for w in doc["writes"]])

    def test_completed(self):
        self.assertEqual(self.repeat(1, 2, 1)[0], 0)
        self.raw_line()
        self.assert_no_bare_copy(2)


class ReportOnly(_Write):

    def test_report_only_appends_nothing_stamps_nothing_mirrors_nothing(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        self.go(fleet, report_only=True, last="request")
        ws_digest = testlib.tree_digest(self.ws)
        path = os.path.join(self.tmp, "answer.json")
        testlib.write_json(path, ilib.answer(R, fleet, adjudications=CB1))
        self.assertEqual(self.run.phase("record-answer", "--answer", path)[0], 0)
        code, doc, out, err = self.run.phase("write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(testlib.tree_digest(self.ws), ws_digest)
        self.assertEqual(self.run.artifact("receipt.json")["writes"], [])
        would = self.run.artifact("write.json")
        self.assertEqual(would["would_raise"][0]["location"], ilib.BUILD_REL + ":12")
        self.assertTrue(would["stamp"].startswith("Plan: inspected"))
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 10, out + err)
        self.assertTrue(doc["wrote_nothing"])
        self.assertEqual(testlib.tree_digest(self.ws), ws_digest)


if __name__ == "__main__":
    unittest.main()
