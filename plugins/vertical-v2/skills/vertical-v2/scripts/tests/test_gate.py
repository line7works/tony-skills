"""vertical-v2's gate (contract section 3, `gate`; reading CR-1 and CR-2 of the slice 1a brief).

The gate passes only when every slice stands `signed off`: each slice's card read from the records
component's `state`, compared with the build doc's `Status:` line; a slice with no log events falls back
to its line and the result says so; a card and a line that disagree is a stop naming both. Zero slices
or a slice with no `Status:` line is malformed input. A collapse comes only from the input's owner-words
field and is recorded verbatim. The two preconditions run with the gate: a git work tree, and a tree
clean where the review looks (dirt touching the boundary or the build doc stops; dirt elsewhere is
listed and the review proceeds on HEAD). The base is v1's precedence: a `Base:` line the build doc
records, then `git merge-base` with the default branch, then a stop that asks. Nothing is summoned and
nothing is written outside the run directory by any of it.
"""
import os
import unittest

import testlib
import vlib

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
        for state in ("built", "signed off with conditions", "rejected", "not started"):
            doc = vlib.build_doc([("A", "the counter", "signed off"), ("B", "the spinner", state)])
            ws, info = vlib.make_repo(self.tmp, doc_text=doc, name="ws-" + state.replace(" ", "-"))
            code, out, err = self.gate(ws)
            result = self.stopped(code, out, "gate-short")
            short = result["station_result"]["gate"]["short"]
            self.assertEqual(short, [{"name": "B", "state": state}], state)
            if state == "built":
                self.assertIn("fresh signoff", result["reason"])

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
    """C1A-7: a recorded `Base:` is 7 to 40 lowercase hex, else a stop naming the line; a recorded base equal
    to HEAD (an empty boundary) is a stop that says so."""

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
        result = self.stopped(*self.gate(ws)[:2], tag="base-unresolved")
        self.assertIn("Base: main", result["reason"])
        self.assertIn("hex", result["reason"])

    def test_head_on_the_base_line_stops_naming_the_line(self):
        ws = self.recorded("HEAD")
        result = self.stopped(*self.gate(ws)[:2], tag="base-unresolved")
        self.assertIn("Base: HEAD", result["reason"])

    def test_upper_case_hex_stops(self):
        ws = self.recorded(lambda w: testlib.git(w, ["rev-parse", "HEAD~1"]).strip().upper())
        self.stopped(*self.gate(ws)[:2], tag="base-unresolved")

    def test_a_recorded_base_equal_to_head_is_a_stop_that_says_the_boundary_is_empty(self):
        ws = self.recorded(lambda w: testlib.git(w, ["rev-parse", "HEAD"]).strip(), commit=False)
        result = self.stopped(*self.gate(ws, owner_words={"committed_only": "review what is committed"})[:2],
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
