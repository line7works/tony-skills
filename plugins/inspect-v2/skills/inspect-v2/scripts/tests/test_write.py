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
        code, doc, out, err = self.go(fleet)
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
        code, doc, out, err = self.go(fleet)
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
        self.go(fleet, last="record-answer")
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
        self.assertIn("exit 7", doc["reason"])
        self.assertIn("conflict", doc["reason"])
        self.assertEqual(testlib.sha256_file(os.path.join(self.ws, ilib.BUILD_REL)), before)
        self.assertFalse(doc["station_result"]["stamp_written"])


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
        code, doc, out, err = self.go(fleet, build=build)
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
        code, doc, out, err = self.go(fleet)
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


class TheMirrorAndTheReceipt(_Write):

    def test_the_mirror_holds_the_block_and_mirrors_is_asked(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        code, doc, out, err = self.go(fleet)
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
        code, doc, out, err = self.go(fleet)
        self.assertEqual(code, 0, out + err)
        code, body, err = ilib.records_cli(["mirrors", "--workspace", self.ws, "--doc", ilib.BUILD_REL])
        self.assertEqual(code, 0, err)
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
        code, doc, out, err = self.go(fleet)
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
        self.go(fleet, last="record-answer")
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
        self.assertEqual(testlib.read_text(paths["named"]), "the reader's reply\n")


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
        testlib.write_json(path, ilib.answer(R, fleet, row="gpt-astra", owner_word=self.WORD))
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

    def test_a_short_fleet_is_named_in_the_mirror_the_result_and_the_chat(self):
        code, doc, out, err = self.recorded(with_repo=False)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.run.phase("write")[0], 0)
        code, doc, out, err = self.run.phase("report")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["station_result"]["lenses_not_run"], ["repo-reality"])
        self.assertIn("Lenses not run: repo-reality", doc["chat"])
        mirror = testlib.read_text(os.path.join(self.ws, "docs", "reviews", "%s-inspect-turnstile.md" % ilib.TODAY))
        self.assertIn("Lenses not run: repo-reality", mirror)


class ReportOnly(_Write):

    def test_report_only_appends_nothing_stamps_nothing_mirrors_nothing(self):
        fleet = ilib.claude_fleet(R, model=MODEL, code_book=[ilib.finding("build-doc.md:12", quote="AC1")])
        self.go(fleet, report_only=True, last="request")
        ws_digest = testlib.tree_digest(self.ws)
        path = os.path.join(self.tmp, "answer.json")
        testlib.write_json(path, ilib.answer(R, fleet))
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
