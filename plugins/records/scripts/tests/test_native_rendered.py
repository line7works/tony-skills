"""E13 amendment A4: the review block `render` writes, and the rendered lines the importer knows.

Two halves of one defect, measured through the real CLI.

1. `render` had one block shape. A run holding only `finding_raised` events rendered nothing and
   named them `skipped`, and Appendix A's review block heading `### <date> — review: <slice>` was
   emitted by nothing in the component. A station that raises findings therefore had to write
   that block itself, in a grammar the component owns.
2. The importer's idempotence was keyed on the `origin` records of the lines IT imported
   (`previously_imported`), never on the NATIVE events the log already holds. A document
   carrying the rendering of a native event was therefore read as news: a rendered review line
   computed the same finding id as its native raise and stopped the document exit 5, and a
   rendered recheck line was imported as a second `disposition` with `known: false`, which
   `state` then reports as `cleared_unbound` beside `fixed` (the control room's CR-F2).

The round trip is checked against the component's OWN reader, which is the oracle: a rendered
review line, read back by `legacy.tolerant_document` and identified by `ids.finding_id` the way
`importer.plan_import` identifies one, computes the finding id the native event carries.
"""
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import identity as identity_mod, ids, legacy  # noqa: E402

DOC = testlib.DOC
RUN = "signoff-2026-04-01-a"
ACTOR = {"station": "signoff", "run_id": RUN, "harness": "claude-code"}


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class ARunThatOnlyRaisedFindings(unittest.TestCase):
    """Half 1: the review block."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-a4-review-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)
        self.doc_path = os.path.join(self.workspace, *DOC.split("/"))

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def append(self, events, head):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        code, body, err = testlib.run_json(
            ["append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
             "--expect-head", head])
        self.assertEqual(code, 0, (body, err))
        return body

    def raise_two(self):
        """Two native `finding_raised` events of one run, one slice, in seq order."""
        first = testlib.raised(identity=self.identity, slice_name="A")
        first["actor"] = dict(ACTOR)
        second = testlib.raised(identity=self.identity, slice_name="A",
                                claim="the gauge never resets",
                                loc=testlib.location("src/widget.py:3", "src/widget.py", 3),
                                scenario="a second call reads the old value",
                                at="2026-04-01T09:00:02Z")
        second["actor"] = dict(ACTOR)
        body = self.append([testlib.opened(self.identity), first, second], testlib.ZERO)
        code, listing, err = testlib.run_json(
            ["events", "--workspace", self.workspace, "--doc", DOC, "--kind", "finding_raised"])
        self.assertEqual(code, 0, err)
        return body, [row["event"] for row in listing["results"]]

    def render(self):
        code, body, err = testlib.run_json(
            ["render", "--workspace", self.workspace, "--doc", DOC, "--run-id", RUN])
        self.assertEqual(code, 0, err)
        return body

    def test_render_emits_appendix_as_review_block(self):
        self.raise_two()
        body = self.render()
        self.assertEqual(body["review_slices"], ["A"])
        self.assertTrue(body["review"].startswith("\n### 2026-04-01 — review: Slice A\n"),
                        body["review"])
        self.assertEqual(len(body["review_lines"]), 2)
        self.assertEqual(body["rendered"], 2)
        self.assertEqual(body["text"], body["review"])

    def test_a_finding_raised_is_no_longer_named_as_skipped(self):
        self.raise_two()
        body = self.render()
        self.assertEqual(body["skipped"], [])

    def test_the_review_line_carries_appendix_as_five_fields(self):
        _, raised = self.raise_two()
        line = self.render()["review_lines"][0]
        self.assertEqual(line.count(legacy.SEP), 4)
        self.assertTrue(line.startswith("- " + raised[0]["severity"] + legacy.SEP))
        self.assertIn(legacy.SEP + "(" + raised[0]["claim"] + ")" + legacy.SEP, line)
        self.assertTrue(line.endswith(legacy.SEP + raised[0]["raised_by"]))

    def test_the_component_s_own_reader_computes_the_same_finding_id(self):
        """The reader is the oracle: every rendered line reads back as its own native event."""
        _, raised = self.raise_two()
        body = self.render()
        parsed = legacy.tolerant_document(body["review"], DOC)
        kinds = [item["kind"] for item in parsed["items"]]
        self.assertEqual(kinds, ["finding", "finding"])
        computed = [ids.finding_id(DOC, legacy.item_slice(item, DOC), item["location"],
                                   item.get("claim"), item.get("scenario"))
                    for item in parsed["items"]]
        self.assertEqual(computed, [event["finding"] for event in raised])

    def test_a_run_spanning_slices_renders_one_review_block_per_slice(self):
        """Appendix A's review heading names ONE slice, and `item_slice` reads the heading's
        first: a single heading naming two slices would charge both findings to the first and
        would not round-trip, so each slice gets its own block, in ascending order."""
        first = testlib.raised(identity=self.identity, slice_name="B",
                               loc=testlib.location("src/widget.py:8", "src/widget.py", 8),
                               claim="the B claim", at="2026-04-01T09:00:03Z")
        first["actor"] = dict(ACTOR)
        second = testlib.raised(identity=self.identity, slice_name="A", at="2026-04-01T09:00:04Z")
        second["actor"] = dict(ACTOR)
        self.append([testlib.opened(self.identity), first, second], testlib.ZERO)
        body = self.render()
        self.assertEqual(body["review_slices"], ["A", "B"])
        self.assertIn("### 2026-04-01 — review: Slice A\n", body["review"])
        self.assertIn("### 2026-04-01 — review: Slice B\n", body["review"])
        self.assertLess(body["review"].index("review: Slice A"),
                        body["review"].index("review: Slice B"))
        parsed = legacy.tolerant_document(body["review"], DOC)
        self.assertEqual(sorted(legacy.item_slice(i, DOC) for i in parsed["items"]), ["A", "B"])

    def test_a_run_holding_both_kinds_renders_review_then_recheck_then_the_grants(self):
        body, raised = self.raise_two()
        clear = testlib.disposition(raised[0]["finding"], self.identity,
                                    at="2026-04-01T11:00:00Z")
        clear["actor"] = dict(ACTOR)
        self.append([clear], body["head"])
        body = self.render()
        self.assertTrue(body["review"])
        self.assertTrue(body["block"].startswith("\n### 2026-04-01 — recheck: Slice A\n"))
        self.assertEqual(body["text"], body["review"] + body["block"] + "".join(body["grants"]))


class TheImporterAndARenderedNativeLine(unittest.TestCase):
    """Half 2: a line that is the rendering of a native event is already recorded."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-a4-import-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)
        self.doc_path = os.path.join(self.workspace, *DOC.split("/"))

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def append(self, events, head):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        code, body, err = testlib.run_json(
            ["append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
             "--expect-head", head])
        self.assertEqual(code, 0, (body, err))
        return body

    def head(self):
        code, body, err = testlib.run_json(["verify", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        return body["head"]

    def render(self, run_id=RUN):
        code, body, err = testlib.run_json(
            ["render", "--workspace", self.workspace, "--doc", DOC, "--run-id", run_id])
        self.assertEqual(code, 0, err)
        return body

    def place(self, text):
        testlib.write(self.doc_path, legacy.append_at_home(read(self.doc_path), text, DOC))

    def move_card(self, before, after, name="A"):
        """A station's card move: the native `card_set`, then the `Status:` line it wrote."""
        card = testlib.native("card_set", at="2026-04-01T11:00:00Z", identity=self.identity,
                              actor=dict(ACTOR), slice=name, before=before, after=after)
        self.append([card], self.head())
        testlib.write(self.doc_path, legacy.set_status_text(read(self.doc_path), name, after))

    def dry_run(self):
        return testlib.run_json(
            ["import-legacy", "--workspace", self.workspace, "--doc", DOC, "--dry-run"])

    def state(self):
        code, body, err = testlib.run_json(["state", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        return body

    def raise_one(self):
        raised = testlib.raised(identity=self.identity, slice_name="A")
        raised["actor"] = dict(ACTOR)
        self.append([testlib.opened(self.identity), raised], testlib.ZERO)
        code, listing, err = testlib.run_json(
            ["events", "--workspace", self.workspace, "--doc", DOC, "--kind", "finding_raised"])
        self.assertEqual(code, 0, err)
        return listing["results"][0]["event"]

    def test_a_rendered_review_line_no_longer_stops_the_document(self):
        """Lane S's shape: a native raise plus its own review line used to be two raises."""
        self.raise_one()
        self.place(self.render()["review"])
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 1)
        self.assertEqual(body["ambiguous"], 0)
        self.assertIsNone(body["counts"].get("finding_raised"))

    def test_a_rendered_recheck_line_is_not_imported_as_a_second_clear(self):
        """CR-F2: the phantom clear, as a unittest against the component alone."""
        raised = self.raise_one()
        clear = testlib.disposition(raised["finding"], self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear], self.head())
        self.place(self.render()["block"])
        code, body, err = testlib.run_json(
            ["import-legacy", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 1)
        self.assertIsNone(body["counts"].get("disposition"))
        counts = self.state()["counts"]
        self.assertEqual(counts["cleared_unbound"], 0)
        self.assertEqual(counts["fixed"], 1)

    def test_a_status_line_a_native_card_set_already_moved_is_not_news(self):
        raised = self.raise_one()
        self.move_card("built", "rejected")
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertIsNone(body["counts"].get("card_observed"))
        self.assertEqual(body["native_rendered"], 1)
        self.assertEqual(raised["slice"], "A")

    def test_a_whole_recorded_run_leaves_the_next_pass_nothing_to_do(self):
        """CR-F2 whole: the block AND the card the pilot wrote are both already recorded, so the
        next levelling appends nothing at all, not even a bracket."""
        raised = self.raise_one()
        clear = testlib.disposition(raised["finding"], self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear], self.head())
        self.place(self.render()["block"])
        self.move_card("built", "signed off")
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["would_import"], 0)
        self.assertEqual(body["native_rendered"], 2)
        self.assertEqual(body["counts"], {})
        self.assertEqual(body["lines_classified"], 0)

    def test_a_hand_written_line_is_still_imported(self):
        """The recognition is byte-equality with a native rendering; nothing else changes."""
        self.raise_one()
        self.place("\n### 2026-04-02 — review: Slice A\n"
                   "- MAJOR · src/widget.py:5 · (the export drops a column) · "
                   "the CSV loses the qty column · A\n")
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["counts"].get("finding_raised"), 1)
        self.assertEqual(body["native_rendered"], 0)

    def test_recognised_lines_are_outside_lines_classified(self):
        self.raise_one()
        self.place(self.render()["review"])
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        # the `Status:` line is the only line left to classify
        self.assertEqual(body["lines_classified"], 1)
        self.assertEqual(body["previously_imported"], 0)

    def test_the_rendered_review_line_imports_to_the_same_finding_id_elsewhere(self):
        """End to end, through the CLI: the same document path in a workspace whose log is empty
        imports the rendered block back to the finding id the native event carries."""
        raised = self.raise_one()
        block = self.render()["review"]
        other = testlib.make_workspace(os.path.join(self.scratch, "twin"))
        path = os.path.join(other, *DOC.split("/"))
        testlib.write(path, legacy.append_at_home(read(path), block, DOC))
        code, body, err = testlib.run_json(
            ["import-legacy", "--workspace", other, "--doc", DOC])
        self.assertEqual(code, 0, (body, err))
        findings = [row["finding"] for row in body["appended"] if row["kind"] == "finding_raised"]
        self.assertEqual(findings, [raised["finding"]])
        self.assertEqual(body["native_rendered"], 0)

    def test_a_second_identical_line_is_still_read_as_news(self):
        """One native event answers for one line: a duplicate below it is not already recorded."""
        self.raise_one()
        block = self.render()["review"]
        line = [row for row in block.split("\n") if row.startswith("- ")][0]
        self.place(block + line + "\n")
        code, body, err = self.dry_run()
        self.assertEqual(code, 5, (body, err))
        self.assertEqual(body["native_rendered"], 1)
        self.assertIn("same finding id", body["ambiguities"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
