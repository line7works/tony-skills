"""vertical-v2's gate (contract section 3, `gate`; reading CR-1 and CR-2 of the slice 1a brief).

The gate passes only when every slice stands `signed off`: each slice's card read from the records
component's `state`, compared with the build doc's `Status:` line; a slice with no log events falls back
to its line and the result says so; a card and a line that disagree is a stop naming both. Zero slices
or a slice with no `Status:` line is malformed input. A collapse comes only from the input's owner-words
field and is recorded verbatim. The two preconditions run with the gate: a git work tree, and a tree
clean where the review looks (dirt touching the boundary or the build doc stops; dirt elsewhere is
listed and the review proceeds on HEAD). The base is v1's precedence: a `Base:` line the build doc
records, then `git merge-base` with the default branch, then a stop that asks. Nothing is summoned and
nothing is written outside the run directory by any of it. The slices and their `Status:` lines are read
with vertical-v2's own fence reader (the E15 lane contract A7), never the frame's parse, and under the exact
label rule (A10, C1A6-1): a slice's one `Status:` label and the header's one `Base:` line are exact and end
their paragraph, or the gate stops `doc-unreadable` naming the line (TheExactLabels, TheExactBaseLine).
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import gate as gatemod, spec as specmod  # noqa: E402

D = vlib.D


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class _Gate(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vgate-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def gate(self, ws, args=(), **station):
        self.runs = getattr(self, "runs", 0) + 1
        drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.runs, **station)
        code, out, err = drive(["gate", "--run-dir", run_dir] + list(args))
        self.run_dir = run_dir
        return code, out, err

    def stopped(self, code, out, tag):
        self.assertEqual(code, 10, out)
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", tag), out)
        result = vlib.load(self.run_dir, "result.json")
        self.assertEqual(result["stop_tag"], tag)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "requests-local.json")))
        return result


class TheSlices(_Gate):

    def test_every_slice_signed_off_passes_with_the_cards_from_the_records(self):
        ws, info = vlib.make_repo(self.tmp, records=True)
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "ask")
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual([(s["name"], s["status_line"], s["card"], s["card_source"]) for s in gate["slices"]],
                         [("A", "signed off", "signed off", "records"), ("B", "signed off", "signed off", "records")])
        self.assertIsNone(gate["collapse"])

    def test_a_slice_with_no_log_events_falls_back_to_its_status_line_and_says_so(self):
        ws, info = vlib.make_repo(self.tmp, records=False)
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual([s["card_source"] for s in gate["slices"]], ["status-line", "status-line"])
        self.assertTrue(any("no log events" in note for note in gate["notes"]), gate["notes"])

    def test_each_short_state_stops_naming_the_slice_and_its_state(self):
        for state in ("built", "signed off with conditions", "rejected", "not started", "in progress"):
            doc = vlib.build_doc([("A", "the counter", "signed off"), ("B", "the spinner", state)])
            ws, info = vlib.make_repo(self.tmp, doc_text=doc, name="ws-" + state.replace(" ", "-"))
            code, out, err = self.gate(ws)
            result = self.stopped(code, out, "gate-short")
            short = result["station_result"]["gate"]["short"]
            self.assertEqual(short, [{"name": "B", "state": state}], state)
            if state == "built":
                self.assertIn("fresh signoff", result["reason"])

    def test_a_rejected_or_conditional_label_stops_short_and_the_collapse_words_pass_it(self):
        """A11: an exact label's value is one of six (A10's four plus `rejected` and `signed off with conditions`,
        which the records component and the v2 stations write). Such a slice stops `gate-short` as it did before
        A10, records off and on, and the owner's collapse words pass it exactly as before."""
        for state in ("signed off with conditions", "rejected"):
            doc = vlib.build_doc([("A", "the counter", "signed off"), ("B", "the spinner", state)])
            for records in (False, True):
                with self.subTest(state=state, records=records):
                    ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records,
                                              name="ws-%s-%s" % (state.replace(" ", "-"), records))
                    result = self.stopped(*self.gate(ws)[:2], tag="gate-short")
                    self.assertEqual(result["station_result"]["gate"]["short"], [{"name": "B", "state": state}])
                    self.assertIn("slice B (%s)" % state, result["reason"])
                    code, out, err = self.gate(ws, owner_words={"collapse_gate": "run it anyway"})
                    self.assertEqual(code, 0, (out, err))
                    gate = vlib.load(self.run_dir, "gate.json")
                    self.assertEqual(gate["collapse"], {"words": "run it anyway", "short": [{"name": "B", "state": state}]})

    def test_zero_slices_is_malformed(self):
        doc = vlib.build_doc([])
        ws, info = vlib.make_repo(self.tmp, doc_text=doc)
        self.stopped(*self.gate(ws)[:2], tag="gate-malformed")

    def test_a_slice_with_no_status_line_is_malformed(self):
        doc = vlib.build_doc([("A", "the counter", "signed off"), ("B", "the spinner", None)])
        ws, info = vlib.make_repo(self.tmp, doc_text=doc)
        result = self.stopped(*self.gate(ws)[:2], tag="gate-malformed")
        self.assertIn("B", result["reason"])

    def test_a_card_and_a_line_that_disagree_stop_naming_both(self):
        ws, info = vlib.make_repo(self.tmp, records=True)
        path = os.path.join(ws, vlib.DOC)
        text = testlib.read_text(path)
        text = text.replace("## Slice B %s the spinner" % D, "## Slice B %s the spinner" % D)
        head, tail = text.split("## Slice B", 1)
        tail = tail.replace("Status: signed off", "Status: built", 1)
        testlib.write_text(path, head + "## Slice B" + tail)
        testlib.git(ws, ["commit", "-q", "-am", "flip B"])
        result = self.stopped(*self.gate(ws)[:2], tag="card-disagrees")
        self.assertIn("built", result["reason"])
        self.assertIn("signed off", result["reason"])
        self.assertEqual(result["station_result"]["gate"]["disagree"],
                         [{"name": "B", "card": "signed off", "status_line": "built"}])

    def test_the_owners_collapse_words_pass_a_short_slice_and_are_recorded_verbatim(self):
        doc = vlib.build_doc([("A", "the counter", "signed off"), ("B", "the spinner", "built")])
        ws, info = vlib.make_repo(self.tmp, doc_text=doc)
        code, out, err = self.gate(ws, owner_words={"collapse_gate": "run it anyway"})
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual(gate["collapse"], {"words": "run it anyway", "short": [{"name": "B", "state": "built"}]})

    def test_a_collapse_never_passes_a_malformed_doc(self):
        doc = vlib.build_doc([])
        ws, info = vlib.make_repo(self.tmp, doc_text=doc)
        code, out, err = self.gate(ws, owner_words={"collapse_gate": "run it anyway"})
        self.stopped(code, out, "gate-malformed")


def fence_shape_doc(closer=False):
    """Slice B's real `Status:` line reads `built`, after a four-backtick fence holding a three-backtick line and a
    fenced literal `Status: signed off`, which the frame's parse (a toggle on every backtick line) reads as B's
    label: the gate must never read B as signed off. With `closer`, the doc as check 3 wrote it, with one blank
    line added after B's label (A10: a label followed by a line the fence rule refuses is not the last line of its
    paragraph and would stop first): a backtick line whose info string holds a backtick follows, which the strict
    rule (A8) stops on."""
    base = vlib.build_doc()
    old = "Depends on: nothing\nStatus: signed off\n\n## Build assumptions"
    new = ("Depends on: nothing\n````text\n```\nStatus: signed off\n````\nStatus: built\n%s\n"
           "## Build assumptions" % ("\n```x`y\n" if closer else ""))
    assert base.count(old) == 1
    return base.replace(old, new)


def lazy_doc():
    """C1A4-1, check 4's shape: in slice B, a list item whose paragraph continues lazily, then a fence indented to
    the item's content. CommonMark ends that fence at the next margin line, so B's real label is `built`; a
    reader that loses the item on the lazy line runs the fence on and reads `signed off`."""
    text = vlib.build_doc(slices=[("A", "the counter", "signed off"), ("B", "the spinner", None)])
    trick = ("- a note on the spinner\nthat continues lazily on this line\n  ```text\nStatus: built\n```\n"
             "Status: signed off\n")
    old = "Depends on: nothing\n\n## Build assumptions"
    assert text.count(old) == 1
    return text.replace(old, "Depends on: nothing\n" + trick + "\n## Build assumptions", 1)


class TheFenceReading(_Gate):
    """The E15 lane contract A7: the gate reads slice headings and `Status:` lines with vertical-v2's own fence
    reader (`fences.py`, CommonMark's fence rule), never the frame's parse; a doc it cannot place stops the gate
    (`doc-unreadable`, naming the line) before any ask."""

    def test_a_fenced_status_literal_is_never_the_card_with_no_records_log(self):
        ws, info = vlib.make_repo(self.tmp, doc_text=fence_shape_doc(), records=False)
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "gate-short")
        self.assertIn("slice B (built)", result["reason"])
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual([(s["name"], s["status_line"]) for s in gate["slices"]], [("A", "signed off"), ("B", "built")])

    def test_a_records_log_that_reads_the_fenced_literal_stops_card_and_line_naming_both(self):
        ws, info = vlib.make_repo(self.tmp, doc_text=fence_shape_doc(), records=True)
        self.assertEqual([(s["name"], s["card_observed"]) for s in vlib.state(ws)["slices"]],
                         [("A", "signed off"), ("B", "signed off")])
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "card-disagrees")
        self.assertIn("slice B: the records say 'signed off', its Status: line says 'built'", result["reason"])

    def test_a_fenced_slice_heading_is_not_a_slice(self):
        doc = vlib.build_doc().replace("\n## Build assumptions",
                                       "\n````\n```\n## Slice C %s an example\nStatus: built\n````\n\n"
                                       "## Build assumptions" % D, 1)
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=False)
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual([s["name"] for s in gate["slices"]], ["A", "B"])

    def test_an_unclosed_fence_before_the_slices_stops_the_gate_before_the_ask(self):
        doc = vlib.build_doc().replace("\n## Slice A", "\n~~~~\nan example\n\n## Slice A", 1)
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=False)
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("~~~~") + 1), result["reason"])
        self.assertEqual(vlib.load(self.run_dir, "checkpoint.json")["phase"], "done")
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "ask.json")))

    def test_a_fence_inside_a_list_item_stops_the_gate_naming_the_line(self):
        doc = vlib.build_doc().replace("- R1 ", "- ```\n- R1 ", 1)
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=False)
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("- ```") + 1), result["reason"])

    def assert_unreadable_before_the_ask(self, doc, first, records):
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%s" % records)
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index(first) + 1), result["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "ask.json")))
        return result

    def test_check_4s_lazy_list_fence_stops_the_gate_with_no_records_log(self):
        self.assert_unreadable_before_the_ask(lazy_doc(), "  ```text", records=False)

    def test_check_4s_lazy_list_fence_stops_the_gate_with_a_records_log(self):
        """The frozen importer reads B `signed off` from the same line; the gate never gets that far."""
        self.assert_unreadable_before_the_ask(lazy_doc(), "  ```text", records=True)

    def test_check_3s_fence_shape_with_its_backtick_info_closer_now_stops(self):
        """A8: a margin backtick line whose info string holds a backtick is a fence line the rule cannot pair."""
        for records in (False, True):
            self.assert_unreadable_before_the_ask(fence_shape_doc(closer=True), "```x`y", records=records)


def commented_label_doc():
    """C1A5-2: in slice B, an HTML comment holding `Status: signed off` before the real `Status: built`; a reader
    that takes lines inside raw HTML as structure reads B as signed off (the frozen importer reads the same line)."""
    text = vlib.build_doc(slices=[("A", "the counter", "signed off"), ("B", "the spinner", None)])
    old = "Depends on: nothing\n\n## Build assumptions"
    assert text.count(old) == 1
    new = "Depends on: nothing\n<!--\nStatus: signed off\n-->\nStatus: built\n\n## Build assumptions"
    return text.replace(old, new, 1)


def unicode_flip_doc(blank):
    """C1A5-1, check 5's gate shape: `<div>`, a line of a Unicode space CommonMark does not count as blank, a margin
    fence holding slice B's CommonMark-real `Status: built`, then a raw-HTML `Status: signed off`."""
    text = vlib.build_doc(slices=[("A", "the counter", "signed off"), ("B", "the spinner", None)])
    trick = "<div>\n%s\n```\n\nStatus: built\n<div>\n```\nStatus: signed off\n" % blank
    old = "Depends on: nothing\n\n## Build assumptions"
    assert text.count(old) == 1
    return text.replace(old, "Depends on: nothing\n" + trick + "\n## Build assumptions", 1)


class TheRawHtmlLines(_Gate):
    """A9, C1A5-1 and C1A5-2: a raw HTML line anywhere outside an accepted fence stops the gate (`doc-unreadable`,
    naming the line) before the ask, with and without a records log; never a pass on a label inside raw HTML."""

    def assert_unreadable_before_the_ask(self, doc, first, records):
        self.repos = getattr(self, "repos", 0) + 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.repos)
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index(first) + 1), result["reason"])
        self.assertIn("raw HTML", result["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "ask.json")))
        self.assertEqual(vlib.load(self.run_dir, "checkpoint.json")["phase"], "done")
        return result

    def test_a_commented_signed_off_label_before_a_real_built_one_stops_with_no_records_log(self):
        self.assert_unreadable_before_the_ask(commented_label_doc(), "<!--", records=False)

    def test_a_commented_signed_off_label_before_a_real_built_one_stops_with_a_records_log(self):
        """The frozen importer reads B `signed off` from the commented line; the gate never gets that far."""
        self.assert_unreadable_before_the_ask(commented_label_doc(), "<!--", records=True)

    def test_check_5s_unicode_space_flip_stops_the_gate_records_on_and_off(self):
        for blank in ("\u00a0", "\u3000"):
            for records in (False, True):
                self.assert_unreadable_before_the_ask(unicode_flip_doc(blank), "<div>", records=records)

    def test_slices_of_refuses_a_raw_html_line(self):
        with self.assertRaises(specmod.SpecUnreadable) as caught:
            gatemod.slices_of(commented_label_doc())
        self.assertEqual(caught.exception.line, commented_label_doc().split("\n").index("<!--") + 1)


class TheDocHunt(_Gate):

    def test_a_named_doc_is_taken(self):
        ws, info = vlib.make_repo(self.tmp)
        code, out, err = self.gate(ws, ["--doc", vlib.DOC])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(vlib.load(self.run_dir, "gate.json")["doc"], vlib.DOC)

    def test_a_named_doc_outside_the_workspace_is_refused(self):
        ws, info = vlib.make_repo(self.tmp)
        outside = os.path.join(self.tmp, "elsewhere.md")
        testlib.write_text(outside, vlib.build_doc())
        code, out, err = self.gate(ws, ["--doc", outside])
        self.assertEqual(code, 5, (out, err))

    def test_several_candidates_stop_and_are_listed_never_picked(self):
        ws, info = vlib.make_repo(self.tmp, extra_build_files={"docs/plans/2026-09-21-turnstile.md": vlib.build_doc()})
        code, out, err = self.gate(ws, ["--name", "turnstile"])
        result = self.stopped(code, out, "selection-several")
        self.assertEqual(len(result["selection"]["build"]["candidates"]), 2)

    def test_nothing_found_is_a_stop_that_asks(self):
        ws, info = vlib.make_repo(self.tmp)
        code, out, err = self.gate(ws, ["--name", "no-such-feature"])
        self.stopped(code, out, "selection-none")


class ThePreconditions(_Gate):

    def test_a_workspace_that_is_not_git_stops(self):
        ws = os.path.join(self.tmp, "plain")
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
        self.stopped(*self.gate(ws)[:2], tag="not-git")

    def test_dirt_inside_the_boundary_stops_naming_it(self):
        ws, info = vlib.make_repo(self.tmp)
        testlib.write_text(os.path.join(ws, "src", "spinner.py"), "# edited after the build\n")
        result = self.stopped(*self.gate(ws)[:2], tag="dirty-boundary")
        self.assertIn("src/spinner.py", result["reason"])

    def test_dirt_on_the_build_doc_stops(self):
        ws, info = vlib.make_repo(self.tmp)
        with open(os.path.join(ws, vlib.DOC), "a", encoding="utf-8") as fh:
            fh.write("\nan edit\n")
        self.stopped(*self.gate(ws)[:2], tag="dirty-boundary")

    def test_dirt_outside_the_boundary_proceeds_on_head_and_is_listed(self):
        ws, info = vlib.make_repo(self.tmp)
        testlib.write_text(os.path.join(ws, "src", "legacy.py"), "OLD = 2\n")
        testlib.write_text(os.path.join(ws, "notes.txt"), "an unrelated note\n")
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        dirt = vlib.load(self.run_dir, "gate.json")["dirt"]
        self.assertEqual(dirt["inside"], [])
        self.assertEqual(sorted(dirt["outside"]), [".env", "notes.txt", "src/legacy.py"])

    def test_the_owners_committed_only_order_proceeds_over_dirt_in_the_boundary(self):
        ws, info = vlib.make_repo(self.tmp)
        testlib.write_text(os.path.join(ws, "src", "spinner.py"), "# edited after the build\n")
        code, out, err = self.gate(ws, owner_words={"committed_only": "review what is committed"})
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual(gate["committed_only"], {"words": "review what is committed"})
        self.assertEqual(gate["dirt"]["inside"], ["src/spinner.py"])


class TheBase(_Gate):

    def test_a_base_the_build_doc_records_wins(self):
        ws, info = vlib.make_repo(self.tmp)
        first = testlib.git(ws, ["rev-list", "--max-parents=0", "HEAD"]).strip()
        doc = vlib.build_doc(base_line="Base: %s" % first)
        testlib.write_text(os.path.join(ws, vlib.DOC), doc)
        testlib.git(ws, ["commit", "-q", "-am", "record the base"])
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"]), (first, "doc"))

    def test_the_merge_base_with_the_default_branch_is_next(self):
        ws, info = vlib.make_repo(self.tmp)
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual((gate["base"]["commit"], gate["base"]["how"]), (info["base"], "merge-base"))
        self.assertEqual(sorted(r["path"] for r in gate["boundary"]),
                         sorted(["docs/plans/2026-09-20-turnstile.md", "docs/reviews/2026-09-24-signoff-turnstile-A.md",
                                 "src/spinner.py", "src/turnstile.py"]))

    def test_no_base_and_no_merge_base_is_a_stop_that_asks(self):
        ws, info = vlib.make_repo(self.tmp, on_main=True)
        result = self.stopped(*self.gate(ws)[:2], tag="base-unresolved")
        self.assertIn("ask the owner", result["reason"])

    def test_the_owners_base_answers_the_ask(self):
        ws, info = vlib.make_repo(self.tmp, on_main=True)
        code, out, err = self.gate(ws, owner_words={"base": {"commit": info["base"], "words": "from the first commit"}})
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"], base["words"]), (info["base"], "owner", "from the first commit"))

    def test_a_recorded_base_that_does_not_resolve_stops(self):
        ws, info = vlib.make_repo(self.tmp)
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc(base_line="Base: deadbeef"))
        testlib.git(ws, ["commit", "-q", "-am", "a bad base"])
        self.stopped(*self.gate(ws)[:2], tag="base-unresolved")


class TheFencedBaseLine(_Gate):
    """The E15 lane contract A7 as the control room reads it (send-back 2): the recorded `Base:` line is read with
    vertical-v2's own fence reader too: a `Base:` line, or a `## ` line, inside a fence is content."""

    def commit_doc(self, ws, header):
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc(extra_header=header))
        testlib.git(ws, ["commit", "-q", "-am", "a header with a fenced example"])

    def test_a_fenced_base_example_before_the_real_base_line_leaves_the_real_one_counting(self):
        ws, info = vlib.make_repo(self.tmp)
        first = testlib.git(ws, ["rev-list", "--max-parents=0", "HEAD"]).strip()
        self.commit_doc(ws, ["````", "```", "Base: deadbeef", "````", "Base: %s" % first])
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"], base["field"]), (first, "doc", "Base: %s" % first))

    def test_a_fenced_base_example_alone_is_no_recorded_base(self):
        ws, info = vlib.make_repo(self.tmp)
        self.commit_doc(ws, ["~~~", "Base: deadbeef", "~~~"])
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"]), (info["base"], "merge-base"))

    def test_a_fenced_heading_does_not_end_the_header(self):
        ws, info = vlib.make_repo(self.tmp)
        first = testlib.git(ws, ["rev-list", "--max-parents=0", "HEAD"]).strip()
        self.commit_doc(ws, ["```", "## an example heading", "```", "Base: %s" % first])
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"]), (first, "doc"))

    def test_check_4s_lazy_list_shape_never_gives_a_fenced_base(self):
        """C1A4-1: the lazy-list shape in the header stops the gate (`doc-unreadable`) at the indented fence line;
        the fenced `Base:` is never the recorded base, and `recorded_base` alone refuses the text too."""
        ws, info = vlib.make_repo(self.tmp)
        first = testlib.git(ws, ["rev-list", "--max-parents=0", "HEAD"]).strip()
        header = ["- a note on the base", "that continues lazily", "  ```text", "Base: %s" % first, "```",
                  "Base: deadbeef", "```"]
        self.commit_doc(ws, header)
        doc = vlib.build_doc(extra_header=header)
        result = self.stopped(*self.gate(ws)[:2], tag="doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("  ```text") + 1), result["reason"])
        with self.assertRaises(specmod.SpecUnreadable):
            gatemod.recorded_base(doc)

    def test_an_unclosed_fence_in_the_header_stops_doc_unreadable_naming_its_line(self):
        ws, info = vlib.make_repo(self.tmp)
        self.commit_doc(ws, ["````", "Base: deadbeef"])
        doc = vlib.build_doc(extra_header=["````", "Base: deadbeef"])
        result = self.stopped(*self.gate(ws)[:2], tag="doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("````") + 1), result["reason"])


class TheCommentedBaseLine(_Gate):
    """A9, C1A5-2: a `Base:` line inside an HTML comment was once the recorded base; now the comment's opening line
    stops the gate (`doc-unreadable`) and `recorded_base` refuses the text."""

    def test_a_commented_base_line_before_the_real_one_stops_doc_unreadable(self):
        ws, info = vlib.make_repo(self.tmp)
        first = testlib.git(ws, ["rev-list", "--max-parents=0", "HEAD"]).strip()
        header = ["<!--", "Base: 1111111", "-->", "Base: %s" % first]
        testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc(extra_header=header))
        testlib.git(ws, ["commit", "-q", "-am", "a header with a commented base"])
        doc = vlib.build_doc(extra_header=header)
        result = self.stopped(*self.gate(ws)[:2], tag="doc-unreadable")
        self.assertIn("line %d" % (doc.split("\n").index("<!--") + 1), result["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "ask.json")))
        with self.assertRaises(specmod.SpecUnreadable):
            gatemod.recorded_base(doc)


# A10, C1A6-1: the shapes CommonMark renders nothing of, each holding a label line inside one paragraph (check 6's
# four): an inline comment opened mid-line, a link reference definition's title in double quotes and in parentheses
# (after a blank line: a definition cannot interrupt a paragraph), and an inline link's title.
HIDING = (
    ("an inline comment opened mid-line", " <!--\n%s\n-->\n"),
    ("a link reference definition title in double quotes", "\n\n[plan-note]: /plan \"\n%s\n\"\n"),
    ("a link reference definition title in parentheses", "\n\n[plan-note]: /plan (\n%s\n)\n"),
    ("an inline link title", " [see](/plan \"\n%s\n\")\n"),
)
SLICE_B = "## Slice B %s the spinner" % D


def slice_b_doc(tail):
    """Slice A `signed off`; slice B's section ends `Depends on: nothing` then `tail` (its label lines, as written)."""
    text = vlib.build_doc(slices=[("A", "the counter", "signed off"), ("B", "the spinner", None)])
    old = "Depends on: nothing\n\n## Build assumptions"
    assert text.count(old) == 1
    return text.replace(old, "Depends on: nothing" + tail + "\n## Build assumptions", 1)


def hidden_label_doc(shape, visible="Status: built"):
    """Check 6's C1A6-1 gate shape: a hidden `Status: signed off` in slice B, then (unless None) a visible label."""
    return slice_b_doc(shape % "Status: signed off" + (visible + "\n" if visible else ""))


def line_in_b(text, line):
    """The 1-based number of the first `line` in slice B's section."""
    lines = text.split("\n")
    return lines.index(line, lines.index(SLICE_B)) + 1


class TheExactLabels(_Gate):
    """A10, C1A6-1: inside a slice's section a `Status:` line outside an accepted fence is the slice's label only
    when it reads exactly `Status: ` and one of the four cards, with nothing after but spaces or tabs, and is the
    last line of its paragraph; a slice holds at most one. Any other such line stops the gate (`doc-unreadable`,
    naming the line, both lines for a second label) before the ask, with and without a records log."""

    def assert_unreadable_before_the_ask(self, doc, number, records=False, also=None):
        self.repos = getattr(self, "repos", 0) + 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.repos)
        code, out, err = self.gate(ws)
        result = self.stopped(code, out, "doc-unreadable")
        self.assertIn("line %d" % number, result["reason"])
        if also is not None:
            self.assertIn("line %d" % also, result["reason"])
        self.assertIn("Status:", result["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "ask.json")))
        self.assertEqual(vlib.load(self.run_dir, "checkpoint.json")["phase"], "done")
        with self.assertRaises(specmod.SpecUnreadable) as caught:
            gatemod.slices_of(doc)
        self.assertEqual(caught.exception.line, number)
        return result

    def assert_counts(self, doc, cards=("signed off", "signed off")):
        self.repos = getattr(self, "repos", 0) + 1
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, name="ws-%d" % self.repos)
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual([s["status_line"] for s in gate["slices"]], list(cards))

    def test_check_6s_four_hiding_shapes_stop_records_off_and_on(self):
        for what, shape in HIDING:
            doc = hidden_label_doc(shape)
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    self.assert_unreadable_before_the_ask(doc, line_in_b(doc, "Status: signed off"), records=records)

    def test_a_slice_whose_only_label_is_hidden_stops(self):
        for what, shape in HIDING:
            doc = hidden_label_doc(shape, visible=None)
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    self.assert_unreadable_before_the_ask(doc, line_in_b(doc, "Status: signed off"), records=records)

    def test_two_plain_visible_labels_in_one_slice_stop_naming_both(self):
        doc = slice_b_doc("\nStatus: built\n\nStatus: signed off\n")
        first, second = line_in_b(doc, "Status: built"), line_in_b(doc, "Status: signed off")
        result = self.assert_unreadable_before_the_ask(doc, second, also=first)
        self.assertIn("second", result["reason"])

    def test_each_label_the_rule_does_not_take_stops(self):
        for what, tail, line in (
                ("trailing text", "\nStatus: signed off, pending a look\n", "Status: signed off, pending a look"),
                ("an unknown value", "\nStatus: done\n", "Status: done"),
                ("upper case", "\nStatus: Signed Off\n", "Status: Signed Off"),
                ("all upper case", "\nStatus: SIGNED OFF\n", "Status: SIGNED OFF"),
                ("a no-break space after the colon", "\nStatus: signed off\n", "Status: signed off"),
                ("two spaces after the colon", "\nStatus:  signed off\n", "Status:  signed off"),
                ("a tab after the colon", "\nStatus:\tsigned off\n", "Status:\tsigned off"),
                ("a no-break space after the value", "\nStatus: signed off \n", "Status: signed off "),
                ("a following paragraph line", "\nStatus: signed off\nthe reviewer agreed\n", "Status: signed off"),
                ("a Setext underline of dashes", "\nStatus: signed off\n---\n", "Status: signed off"),
                ("a Setext underline of equals signs", "\nStatus: signed off\n===\n", "Status: signed off"),
                ("a next line of a no-break space only", "\nStatus: signed off\n \n", "Status: signed off"),
                ("a next line of a form feed only", "\nStatus: signed off\n\x0c\n", "Status: signed off"),
                ("a next line holding a closing quote", "\nStatus: signed off\n\"\n", "Status: signed off")):
            doc = slice_b_doc(tail)
            with self.subTest(label=what):
                self.assert_unreadable_before_the_ask(doc, line_in_b(doc, line))

    def test_a_label_followed_by_a_blank_line_counts(self):
        self.assert_counts(slice_b_doc("\nStatus: signed off\n"))
        self.assert_counts(slice_b_doc("\nStatus: signed off \t\n \t\n"))

    def test_a_label_followed_by_a_heading_counts(self):
        doc = vlib.build_doc().replace("Status: signed off\n\n## Slice B", "Status: signed off\n## Slice B", 1)
        self.assertIn("Status: signed off\n## Slice B", doc)
        self.assert_counts(doc)
        self.assert_counts(slice_b_doc("\nStatus: signed off\n### a note under the slice\nsome text\n"))

    def test_a_label_followed_by_a_fence_counts(self):
        self.assert_counts(slice_b_doc("\nStatus: signed off\n```text\nan example\n```\n"))
        self.assert_counts(slice_b_doc("\nStatus: signed off\n~~~\nStatus: built\n~~~\n"))

    def test_a_label_at_the_docs_end_counts(self):
        whole = vlib.build_doc()
        cut = whole[:whole.index("\n\n## Build assumptions")]
        self.assertTrue(cut.endswith("Status: signed off"))
        self.assert_counts(cut + "\n")
        self.assert_counts(cut)

    def test_each_value_the_rule_takes_is_read(self):
        for value in ("not started", "in progress", "built", "rejected", "signed off with conditions", "signed off"):
            self.assertEqual(gatemod.slices_of(slice_b_doc("\nStatus: %s\n" % value))[1]["status"], value)


def hidden_base_header(shape, hidden, visible):
    """The header's `Out of scope` paragraph continued by `shape` holding `Base: <hidden>`, then `Base: <visible>`."""
    return vlib.build_doc().replace("the owner declined it for the first version",
                                    "the owner declined it for the first version" + shape % ("Base: %s" % hidden)
                                    + "Base: %s" % visible, 1)


class TheExactBaseLine(_Gate):
    """A10, C1A6-1: in the header a `Base:` line is the recorded base only when it reads exactly `Base: ` and 7 to 40
    lower-case hex digits, with nothing after but spaces or tabs, and is the last line of its paragraph; the header
    holds at most one. Any other `Base:` line there stops the gate (`doc-unreadable`, naming the line) before the
    ask, and the owner's base never clears it."""

    def commit_doc(self, ws, doc):
        testlib.write_text(os.path.join(ws, vlib.DOC), doc)
        testlib.git(ws, ["commit", "-q", "-am", "the header's base"])

    def assert_unreadable(self, doc, line, also=None, **station):
        self.repos = getattr(self, "repos", 0) + 1
        ws, info = vlib.make_repo(self.tmp, name="ws-%d" % self.repos)
        self.commit_doc(ws, doc)
        result = self.stopped(*self.gate(ws, **station)[:2], tag="doc-unreadable")
        number = doc.split("\n").index(line) + 1
        self.assertIn("line %d" % number, result["reason"])
        if also is not None:
            self.assertIn("line %d" % (doc.split("\n").index(also) + 1), result["reason"])
        self.assertIn("Base:", result["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "ask.json")))
        with self.assertRaises(specmod.SpecUnreadable) as caught:
            gatemod.recorded_base(doc)
        self.assertEqual(caught.exception.line, number)
        return result

    def test_check_6s_four_hiding_shapes_never_give_the_base(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        for what, shape in HIDING:
            with self.subTest(shape=what):
                doc = hidden_base_header(shape, info0["base"], "2222222")
                self.assert_unreadable(doc, "Base: %s" % info0["base"])

    def test_two_base_lines_stop_naming_both(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        doc = vlib.build_doc(base_line="Base: %s" % info0["base"], extra_header=["", "Base: %s" % info0["base"][:12]])
        result = self.assert_unreadable(doc, "Base: %s" % info0["base"][:12], also="Base: %s" % info0["base"])
        self.assertIn("second", result["reason"])

    def test_a_short_or_upper_case_sha_stops(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        for value in (info0["base"][:6], info0["base"].upper(), info0["base"][:7].upper(), info0["base"] + "0",
                      "main", "HEAD", "%s trailing" % info0["base"], " " + info0["base"]):
            with self.subTest(value=value):
                self.assert_unreadable(vlib.build_doc(base_line="Base: %s" % value), "Base: %s" % value)

    def test_the_owners_base_never_clears_a_base_line_the_rule_refuses(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        self.assert_unreadable(vlib.build_doc(base_line="Base: main"), "Base: main",
                               owner_words={"base": {"commit": info0["base"], "words": "from the first commit"}})

    def test_a_base_line_followed_by_a_paragraph_line_stops(self):
        ws0, info0 = vlib.make_repo(self.tmp, name="probe")
        line = "Base: %s" % info0["base"]
        self.assert_unreadable(vlib.build_doc(base_line=line, extra_header=["the base above is the branch point"]), line)

    def test_an_exact_base_line_with_trailing_spaces_and_tabs_counts(self):
        ws, info = vlib.make_repo(self.tmp)
        self.commit_doc(ws, vlib.build_doc(base_line="Base: %s \t" % info["base"]))
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"]), (info["base"], "doc"))


class TheDerivedCard(_Gate):
    """C1A-2, the owner's ruling in A3: the gate compares the observed card with the `Status:` line only; a
    derived card that differs (an open finding in the log behind a signed card) does not stop the run."""

    def test_an_open_finding_behind_a_signed_card_does_not_stop_the_gate(self):
        ws, info = vlib.make_repo(self.tmp, doc_text=vlib.open_major_doc(), records=True)
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        gate = vlib.load(self.run_dir, "gate.json")
        self.assertEqual(gate["disagree"], [])
        self.assertEqual(gate["short"], [])
        slice_a = [s for s in gate["slices"] if s["name"] == "A"][0]
        self.assertEqual((slice_a["card"], slice_a["card_source"], slice_a["card_derived"]),
                         ("signed off", "records", "signed off with conditions"))

    def test_the_observed_card_against_the_status_line_still_stops(self):
        ws, info = vlib.make_repo(self.tmp, doc_text=vlib.open_major_doc(), records=True)
        path = os.path.join(ws, vlib.DOC)
        head, tail = testlib.read_text(path).split("## Slice B", 1)
        testlib.write_text(path, head + "## Slice B" + tail.replace("Status: signed off", "Status: built", 1))
        testlib.git(ws, ["commit", "-q", "-am", "flip B"])
        result = self.stopped(*self.gate(ws)[:2], tag="card-disagrees")
        self.assertEqual(result["station_result"]["gate"]["disagree"],
                         [{"name": "B", "card": "signed off", "status_line": "built"}])


class TheRecordedBaseLine(_Gate):
    """C1A-7 as A10 reads it: a recorded `Base:` is exactly 7 to 40 lowercase hex, else the label rule stops the
    gate (`doc-unreadable`) naming the line; a recorded base equal to HEAD (an empty boundary) is a stop that says
    so (`base-unresolved`)."""

    def recorded(self, value, commit=True):
        ws, info = vlib.make_repo(self.tmp, name="ws-%d" % (getattr(self, "n", 0)))
        self.n = getattr(self, "n", 0) + 1
        text = vlib.build_doc(base_line="Base: %s" % (value(ws) if callable(value) else value))
        testlib.write_text(os.path.join(ws, vlib.DOC), text)
        if commit:
            testlib.git(ws, ["commit", "-q", "-am", "record the base"])
        return ws

    def test_a_branch_name_on_the_base_line_stops_naming_the_line(self):
        ws = self.recorded("main")
        result = self.stopped(*self.gate(ws)[:2], tag="doc-unreadable")
        self.assertIn("line %d" % (vlib.build_doc(base_line="Base: main").split("\n").index("Base: main") + 1),
                      result["reason"])
        self.assertIn("hex", result["reason"])

    def test_head_on_the_base_line_stops_naming_the_line(self):
        ws = self.recorded("HEAD")
        result = self.stopped(*self.gate(ws)[:2], tag="doc-unreadable")
        self.assertIn("Base:", result["reason"])

    def test_upper_case_hex_stops(self):
        ws = self.recorded(lambda w: testlib.git(w, ["rev-parse", "HEAD~1"]).strip().upper())
        self.stopped(*self.gate(ws)[:2], tag="doc-unreadable")

    def test_a_recorded_base_equal_to_head_is_a_stop_that_says_the_boundary_is_empty(self):
        ws = self.recorded(lambda w: testlib.git(w, ["rev-parse", "HEAD"]).strip(), commit=False)
        result = self.stopped(*self.gate(ws, owner_words={"committed_only": "review what is committed"})[:2],
                              tag="base-unresolved")
        self.assertIn("HEAD", result["reason"])
        self.assertIn("empty", result["reason"])


class TheOwnersBaseOverARecordedStop(_Gate):
    """C1A2-3 and C1A2-4 as A10 reads them: an exact `Base:` line that cannot be taken (it resolves to nothing or
    names HEAD) is cleared by the owner's base on a fresh run; a `Base:` line the label rule refuses is never
    cleared (`doc-unreadable`, TheExactBaseLine); an owner's base equal to HEAD stops (an empty boundary) wherever
    it is taken."""

    OWNER = "from the first commit, the owner said"
    recorded = TheRecordedBaseLine.recorded

    def test_the_owners_base_clears_an_unresolvable_base_line_and_both_are_named(self):
        ws = self.recorded("deadbeef")
        first = testlib.git(ws, ["rev-list", "--max-parents=0", "HEAD"]).strip()
        code, out, err = self.gate(ws, owner_words={"base": {"commit": first, "words": self.OWNER}})
        self.assertEqual(code, 0, (out, err))
        base = vlib.load(self.run_dir, "gate.json")["base"]
        self.assertEqual((base["commit"], base["how"], base["words"]), (first, "owner", self.OWNER))
        self.assertIn("Base: deadbeef", base["field"])

    def test_a_base_line_stop_with_no_owners_base_names_where_his_answer_goes(self):
        ws = self.recorded("deadbeef")
        result = self.stopped(*self.gate(ws)[:2], tag="base-unresolved")
        self.assertIn("station.owner_words.base", result["reason"])

    def test_an_owners_base_equal_to_head_over_a_base_line_stops(self):
        ws = self.recorded("deadbeef")
        head = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
        result = self.stopped(*self.gate(ws, owner_words={"base": {"commit": head, "words": self.OWNER}})[:2],
                              tag="base-unresolved")
        self.assertIn("empty", result["reason"])

    def test_an_owners_base_equal_to_head_stops(self):
        ws, info = vlib.make_repo(self.tmp, on_main=True)
        result = self.stopped(*self.gate(ws, owner_words={"base": {"commit": info["head"], "words": self.OWNER}})[:2],
                              tag="base-unresolved")
        self.assertIn("HEAD", result["reason"])
        self.assertIn("empty", result["reason"])


class TheRenameInTheTree(_Gate):
    """C1A-8: the dirt check reads both paths of a rename or copy; a boundary file moved away stops the run."""

    def test_a_staged_rename_of_a_boundary_file_stops_naming_its_old_path(self):
        ws, info = vlib.make_repo(self.tmp)
        testlib.git(ws, ["mv", "src/spinner.py", "src/moved.py"])
        result = self.stopped(*self.gate(ws)[:2], tag="dirty-boundary")
        self.assertIn("src/spinner.py", result["reason"])
        dirt = result["station_result"]["gate"]["dirt"]
        self.assertEqual(dirt["inside"], ["src/spinner.py"])
        self.assertIn("src/moved.py", dirt["outside"])

    def test_a_staged_rename_outside_the_boundary_proceeds_and_lists_both_paths(self):
        ws, info = vlib.make_repo(self.tmp)
        testlib.git(ws, ["mv", "src/legacy.py", "src/older.py"])
        code, out, err = self.gate(ws)
        self.assertEqual(code, 0, (out, err))
        dirt = vlib.load(self.run_dir, "gate.json")["dirt"]
        self.assertEqual(dirt["inside"], [])
        self.assertIn("src/legacy.py", dirt["outside"])
        self.assertIn("src/older.py", dirt["outside"])


class NothingWritten(_Gate):

    def test_the_gate_writes_nothing_outside_its_run_directory(self):
        ws, info = vlib.make_repo(self.tmp, records=True)
        before = testlib.tree_digest(ws)
        self.gate(ws)
        self.assertEqual(testlib.tree_digest(ws), before)


if __name__ == "__main__":
    unittest.main()
