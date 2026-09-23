"""E13 amendment A7: three defects Astra's slice 2 review found inside this component.

- **F5** (`importer.py`): a line the log already records natively was recognised by its bytes
  alone. A native slice A review line placed under slice B's heading vanished instead of
  importing as news for B, and two identical native lines (one A, one B) placed under A's heading
  were both skipped without the ambiguity stop. A native occurrence is now matched by event kind
  and by finding identity in the document's slice context as well as by exact bytes, and each
  occurrence is consumed once.
- **F9** (`render.py`): the review line wrote a ranged location as its first `file:line`, so the
  rendered line read back under another finding identity. It now writes the raw location.
- **F10** (`records.py`, `import-report.schema.json`): A4's new response shapes were published
  under `interface_version` 1, and a closed version-1 reader rejects them. They are version 2
  now; version 1 is kept only through `--interface-version 1`, a compatibility response that
  preserves version 1's closed shape.

Every test drives the real CLI; the reader and the finding-id function are the oracles, the way
`test_native_rendered.py` uses them.
"""
import json
import os
import shutil
import sys
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import identity as identity_mod, ids, legacy, validate  # noqa: E402

DOC = testlib.DOC
RUN = "signoff-2026-04-01-a"
ACTOR = {"station": "signoff", "run_id": RUN, "harness": "claude-code"}
V1_IMPORT_SCHEMA = os.path.join(testlib.REFERENCES, "v1", "import-report.schema.json")
V2_IMPORT_SCHEMA = os.path.join(testlib.REFERENCES, "import-report.schema.json")
V1_RENDER_FIELDS = ["component_version", "date", "events", "exists", "grants", "head",
                    "interface_version", "lines", "log", "ok", "block", "rendered", "run_id",
                    "skipped", "slices", "spec", "text"]


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def schema_errors(schema_path, document):
    """Validate `document` against one schema file, closed as it is; the list of messages."""
    import jsonschema
    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(error.message for error in validator.iter_errors(document))


class Workspace(unittest.TestCase):
    """A fresh workspace per test, and the CLI calls every class below uses."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-a7-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)
        self.doc_path = os.path.join(self.workspace, *DOC.split("/"))

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def append(self, events, head=None):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        code, body, err = testlib.run_json(
            ["append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
             "--expect-head", head or self.head()])
        self.assertEqual(code, 0, (body, err))
        return body

    def head(self):
        code, body, err = testlib.run_json(["verify", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        return body["head"]

    def render(self, run_id=RUN, extra=()):
        code, body, err = testlib.run_json(
            list(extra) + ["render", "--workspace", self.workspace, "--doc", DOC,
                           "--run-id", run_id])
        self.assertEqual(code, 0, err)
        return body

    def place(self, text):
        testlib.write(self.doc_path, legacy.append_at_home(read(self.doc_path), text, DOC))

    def dry_run(self, extra=()):
        return testlib.run_json(list(extra) + [
            "import-legacy", "--workspace", self.workspace, "--doc", DOC, "--dry-run"])

    def import_now(self, extra=()):
        return testlib.run_json(list(extra) + [
            "import-legacy", "--workspace", self.workspace, "--doc", DOC])

    def state(self):
        code, body, err = testlib.run_json(["state", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        return body

    def raise_native(self, slice_name="A", **fields):
        event = testlib.raised(identity=self.identity, slice_name=slice_name, **fields)
        event["actor"] = dict(ACTOR)
        event["raised_by"] = "the signoff reviewer"  # one reviewer, so two slices' lines can match
        return event

    def raised_events(self):
        code, listing, err = testlib.run_json(
            ["events", "--workspace", self.workspace, "--doc", DOC, "--kind", "finding_raised"])
        self.assertEqual(code, 0, err)
        return [row["event"] for row in listing["results"]]


# ---- F5 ------------------------------------------------------------------------------------------

class F5NativeLinesAreMatchedInTheirSliceContext(Workspace):
    """F5: bytes alone no longer decide that a document line is already recorded."""

    def review_line(self, body, slice_name):
        """The one review line `render` wrote under slice `slice_name`'s block."""
        blocks = body["review"].split("\n### ")
        for block in blocks:
            if block.split("\n", 1)[0].endswith("review: Slice %s" % slice_name):
                return [row for row in block.split("\n") if row.startswith("- ")][0]
        self.fail("no review block for slice %s in %r" % (slice_name, body["review"]))

    def test_a_native_a_line_under_slice_b_s_heading_imports_as_news_for_b(self):
        """F5, Astra's first shape: the A line under B's heading used to vanish (native_rendered
        1, would_import 0, imported 0, only A in state). It is news for B."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        line = self.review_line(self.render(), "A")
        self.place("\n### 2026-04-01 — review: Slice B\n" + line + "\n")
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 0, body)
        self.assertEqual(body["counts"].get("finding_raised"), 1, body)
        self.assertGreater(body["would_import"], 0, body)
        code, body, err = self.import_now()
        self.assertEqual(code, 0, (body, err))
        self.assertGreater(body["imported"], 0, body)
        slices = sorted(row["slice"] for row in self.state()["findings"])
        self.assertEqual(slices, ["A", "B"])

    def test_two_identical_native_a_and_b_lines_under_a_s_heading_stop(self):
        """F5, Astra's second shape: native A and B findings whose lines are byte-identical, both
        lines placed under A's heading. The first is A's rendering; the second, read under A, is a
        second raise of A's finding, which is the importer's existing ambiguity stop (exit 5), not
        two silent skips."""
        self.append([testlib.opened(self.identity), self.raise_native("A"),
                     self.raise_native("B", at="2026-04-01T09:00:02Z")], testlib.ZERO)
        body = self.render()
        a_line, b_line = self.review_line(body, "A"), self.review_line(body, "B")
        self.assertEqual(a_line, b_line, "the two findings render to identical bytes")
        self.place("\n### 2026-04-01 — review: Slice A\n" + a_line + "\n" + b_line + "\n")
        code, body, err = self.dry_run()
        self.assertEqual(code, 5, (body, err))
        self.assertEqual(body["native_rendered"], 1, body)
        self.assertEqual(len(body["ambiguities"]), 1, body)
        self.assertIn("same finding id", body["ambiguities"][0]["reason"])

    def test_the_same_two_lines_each_under_its_own_heading_are_both_recognised(self):
        """F5, the ordinary shape beside the second: what `render` wrote, placed as written."""
        self.append([testlib.opened(self.identity), self.raise_native("A"),
                     self.raise_native("B", at="2026-04-01T09:00:02Z")], testlib.ZERO)
        self.place(self.render()["review"])
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 2, body)
        self.assertEqual(sorted(body["counts"]), ["card_observed"], body)

    def test_a_changed_heading_date_alone_does_not_change_finding_identity(self):
        """F5: the date is not part of a finding's identity, so a rendered block whose heading
        date was changed is still the rendering of the same native raise."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        review = self.render()["review"].replace("### 2026-04-01 — review", "### 2026-04-09 — review")
        self.assertIn("2026-04-09", review)
        self.place(review)
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 1, body)
        self.assertEqual(sorted(body["counts"]), ["card_observed"], body)

    def test_a_native_recheck_line_under_a_heading_naming_another_slice_is_not_recognised(self):
        """F5 for a clearing line: its slice context is the recheck heading's slices. Moved under a
        heading that does not name the finding's slice, it is read as legacy news (here the
        legacy join places it exactly and it imports as an unbound clear)."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        finding = self.raised_events()[0]["finding"]
        clear = testlib.disposition(finding, self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear])
        block = self.render()["block"]
        self.assertIn("recheck: Slice A", block)
        self.place(block.replace("recheck: Slice A", "recheck: Slice B"))
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 0, body)
        self.assertEqual(body["counts"].get("disposition"), 1, body)

    def test_a_native_recheck_line_under_its_own_heading_is_still_recognised(self):
        """F5, the ordinary clearing shape stays green."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        finding = self.raised_events()[0]["finding"]
        clear = testlib.disposition(finding, self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear])
        self.place(self.render()["block"])
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["native_rendered"], 1, body)
        self.assertEqual(sorted(body["counts"]), ["card_observed"], body)

    def test_each_native_occurrence_is_consumed_once_across_two_slices(self):
        """F5: two byte-identical native clears of two findings in two slices, rendered under one
        heading naming both, are two occurrences; each line consumes one."""
        self.append([testlib.opened(self.identity), self.raise_native("A"),
                     self.raise_native("B", at="2026-04-01T09:00:02Z")], testlib.ZERO)
        raised = self.raised_events()
        clears = []
        for event in raised:
            clear = testlib.disposition(event["finding"], self.identity)
            clear["actor"] = dict(ACTOR)
            clears.append(clear)
        self.append(clears)
        body = self.render()
        self.assertEqual(len(body["lines"]), 2)
        self.assertEqual(body["lines"][0], body["lines"][1])
        self.place(body["block"])
        code, report, err = self.dry_run()
        self.assertEqual(code, 0, (report, err))
        self.assertEqual(report["native_rendered"], 2, report)
        self.assertEqual(sorted(report["counts"]), ["card_observed"], report)


# ---- F9 ------------------------------------------------------------------------------------------

class F9ARangedLocationKeepsItsIdentity(Workspace):
    """F9: the review line writes the raw location the finding carries."""

    RANGED = testlib.location("src/widget.py:2-3", "src/widget.py", 2, line_end=3, resolved=True)

    def test_a_ranged_location_renders_as_the_range(self):
        """F9: `src/widget.py:2-3` used to render as `src/widget.py:2`."""
        self.append([testlib.opened(self.identity), self.raise_native("A", loc=self.RANGED)],
                    testlib.ZERO)
        line = self.render()["review_lines"][0]
        self.assertIn(legacy.SEP + "src/widget.py:2-3" + legacy.SEP, line)

    def test_a_ranged_review_line_imports_back_to_the_same_finding_in_an_empty_twin(self):
        """F9, Astra's shape: appended natively, rendered, imported into a twin workspace whose log
        is empty: the same finding id (it was f1:d94a... native against f1:89e1... imported)."""
        self.append([testlib.opened(self.identity), self.raise_native("A", loc=self.RANGED)],
                    testlib.ZERO)
        native = self.raised_events()[0]["finding"]
        block = self.render()["review"]
        twin = testlib.make_workspace(os.path.join(self.scratch, "twin"))
        path = os.path.join(twin, *DOC.split("/"))
        testlib.write(path, legacy.append_at_home(read(path), block, DOC))
        code, body, err = testlib.run_json(["import-legacy", "--workspace", twin, "--doc", DOC])
        self.assertEqual(code, 0, (body, err))
        imported = [row["finding"] for row in body["appended"] if row["kind"] == "finding_raised"]
        self.assertEqual(imported, [native])

    def test_the_reader_computes_the_native_id_from_the_ranged_line(self):
        """F9, against the component's own reader as the oracle."""
        self.append([testlib.opened(self.identity), self.raise_native("A", loc=self.RANGED)],
                    testlib.ZERO)
        native = self.raised_events()[0]["finding"]
        parsed = legacy.tolerant_document(self.render()["review"], DOC)
        item = parsed["items"][0]
        self.assertEqual(ids.finding_id(DOC, legacy.item_slice(item, DOC), item["location"],
                                        item.get("claim"), item.get("scenario")), native)

    def test_the_recheck_line_of_a_ranged_finding_is_unchanged(self):
        """F9 leaves the recheck block's bytes alone: it still names the first `file:line`."""
        self.append([testlib.opened(self.identity), self.raise_native("A", loc=self.RANGED)],
                    testlib.ZERO)
        finding = self.raised_events()[0]["finding"]
        clear = testlib.disposition(finding, self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear])
        line = self.render()["lines"][0]
        self.assertIn(legacy.SEP + "src/widget.py:2" + legacy.SEP, line)
        self.assertNotIn("2-3", line)

    def test_the_ranged_recheck_line_is_still_recognised_as_native(self):
        """F9 with F5: the recheck line names the first `file:line`, and it is still the
        rendering of its native clear in its slice context."""
        self.append([testlib.opened(self.identity), self.raise_native("A", loc=self.RANGED)],
                    testlib.ZERO)
        finding = self.raised_events()[0]["finding"]
        clear = testlib.disposition(finding, self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear])
        body = self.render()
        self.place(body["review"] + body["block"])
        code, report, err = self.dry_run()
        self.assertEqual(code, 0, (report, err))
        self.assertEqual(report["native_rendered"], 2, report)
        self.assertEqual(sorted(report["counts"]), ["card_observed"], report)


# ---- F10 -----------------------------------------------------------------------------------------

class F10TheA4ShapesAreInterfaceVersion2(Workspace):
    """F10: version 2 by default; version 1 only through `--interface-version 1`."""

    def with_a_rendered_review(self):
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        self.place(self.render()["review"])

    def test_every_default_response_says_version_2(self):
        """F10: the component speaks interface version 2."""
        code, body, err = testlib.run_json(["component-identity"])
        self.assertEqual(code, 0, err)
        self.assertEqual(body["interface_version"], 2)
        self.with_a_rendered_review()
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["interface_version"], 2)
        self.assertEqual(self.render()["interface_version"], 2)

    def test_the_default_import_response_validates_against_version_2_only(self):
        """F10: the default response carries `native_rendered` and validates against the published
        (version 2) schema; the frozen version-1 schema rejects it, which is Astra's break."""
        self.with_a_rendered_review()
        code, body, err = self.dry_run()
        self.assertEqual(code, 0, (body, err))
        self.assertIn("native_rendered", body)
        self.assertEqual(schema_errors(V2_IMPORT_SCHEMA, body), [])
        self.assertTrue(schema_errors(V1_IMPORT_SCHEMA, body), "a v1 reader must not accept it")

    def test_a_version_1_reader_given_the_compatibility_response_validates(self):
        """F10: `--interface-version 1` answers in version 1's closed shape."""
        self.with_a_rendered_review()
        code, body, err = self.dry_run(extra=["--interface-version", "1"])
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["interface_version"], 1)
        self.assertNotIn("native_rendered", body)
        self.assertEqual(schema_errors(V1_IMPORT_SCHEMA, body), [])
        self.assertTrue(schema_errors(V2_IMPORT_SCHEMA, body),
                        "a version-1 response is not a version-2 one")

    def test_the_compatibility_refusal_validates_against_version_1(self):
        """F10: the ambiguity refusal (exit 5) is a changed shape too; version 1 gets it closed."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        review = self.render()["review"]
        line = [row for row in review.split("\n") if row.startswith("- ")][0]
        self.place(review + line + "\n")
        code, body, err = self.dry_run(extra=["--interface-version", "1"])
        self.assertEqual(code, 5, (body, err))
        self.assertEqual(body["interface_version"], 1)
        self.assertNotIn("native_rendered", body)
        self.assertEqual(schema_errors(V1_IMPORT_SCHEMA, body), [])
        code, body, err = self.dry_run()
        self.assertEqual(code, 5, (body, err))
        self.assertEqual(schema_errors(V2_IMPORT_SCHEMA, body), [])

    def test_a_landed_compatibility_import_validates_against_version_1(self):
        """F10: the landed shape as well as the preview."""
        self.place("\n### 2026-04-02 — review: Slice A\n"
                   "- MAJOR · src/widget.py:5 · (the export drops a column) · "
                   "the CSV loses the qty column · A\n")
        code, body, err = self.import_now(extra=["--interface-version", "1"])
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(schema_errors(V1_IMPORT_SCHEMA, body), [])

    def test_the_compatibility_render_has_version_1_s_fields_and_meanings(self):
        """F10: `render` gained three fields and changed `text`, `rendered`, `skipped`, `date` and
        `spec.slice` in A4; version 1 gets the fields and the meanings it was published with."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        v2 = self.render()
        v1 = self.render(extra=["--interface-version", "1"])
        self.assertEqual(sorted(v1), sorted(V1_RENDER_FIELDS))
        self.assertEqual(v1["interface_version"], 1)
        self.assertEqual(v1["text"], "")
        self.assertEqual(v1["rendered"], 0)
        self.assertIsNone(v1["date"])
        self.assertIsNone(v1["spec"]["slice"])
        self.assertEqual([row["kind"] for row in v1["skipped"]], ["finding_raised"])
        self.assertEqual(v2["skipped"], [])
        self.assertTrue(v2["review"])
        self.assertEqual(v2["rendered"], 1)

    def test_component_identity_answers_in_the_version_asked_for(self):
        code, body, err = testlib.run_json(["--interface-version", "1", "component-identity"])
        self.assertEqual(code, 0, err)
        self.assertEqual(body["interface_version"], 1)

    def test_a_version_the_component_does_not_speak_is_a_usage_error(self):
        code, out, err = testlib.run_cli(["--interface-version", "3", "component-identity"])
        self.assertEqual(code, 2, (out, err))
        self.assertEqual(out.strip(), "")

    def test_the_log_bytes_do_not_depend_on_the_version_asked_for(self):
        """F10: the flag shapes the response only. A log opened by a compatibility import records
        the interface version the component speaks, 2, like any other."""
        self.place("\n### 2026-04-02 — review: Slice A\n"
                   "- MAJOR · src/widget.py:5 · (the export drops a column) · "
                   "the CSV loses the qty column · A\n")
        code, body, err = self.import_now(extra=["--interface-version", "1"])
        self.assertEqual(code, 0, (body, err))
        code, listing, err = testlib.run_json(
            ["events", "--workspace", self.workspace, "--doc", DOC, "--kind", "log_opened"])
        self.assertEqual(code, 0, err)
        self.assertEqual(listing["results"][0]["event"]["interface_version"], 2)

    def test_the_frozen_version_1_schema_is_closed_and_names_no_a4_field(self):
        """F10: the shipped version-1 schema is the closed pre-A4 shape."""
        text = read(V1_IMPORT_SCHEMA)
        self.assertNotIn("native_rendered", text)
        schema = json.loads(text)
        for branch in ("import_ok", "import_refused"):
            self.assertFalse(schema["$defs"][branch]["additionalProperties"], branch)


# ---- the last fix round (E13 slice 2, Astra's recheck): F5's remainder and N3 ------------------

class F5RemainderTheFindingIdentityIsPartOfTheMatch(Workspace):
    """F5, Astra's stricter shape (`probe_identity_match.py`): a native ranged DEFECT renders in
    Appendix A's first-line form (the recheck block keeps `location_text`, A7), so the line reads
    back under another finding identity than the native event's stored id. It used to be skipped
    (`native_rendered: 1, would_import: 0`); a line whose identity differs is legacy news."""

    RANGED = testlib.location("src/widget.py:2-3", "src/widget.py", 2, line_end=3, resolved=True)
    RUN_R = "recheck-2026-04-02-a"
    ACTOR_R = {"station": "recheck", "run_id": RUN_R, "harness": "claude-code"}

    def raise_defect(self, loc):
        """A native finding for slice A, then a recheck run clearing it and raising a defect."""
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        finding = self.raised_events()[0]["finding"]
        clear = testlib.disposition(finding, self.identity, at="2026-04-02T09:00:00Z")
        clear["actor"] = dict(self.ACTOR_R)
        defect = testlib.native("defect_raised", at="2026-04-02T09:00:01Z", identity=self.identity,
                                actor=self.ACTOR_R, slice="A", severity="MAJOR", location=loc,
                                claim="the reset runs twice", scenario="the second reset is a no-op",
                                raised_by="the recheck verifier", caused_by=finding)
        self.append([clear, defect])
        code, listing, err = testlib.run_json(
            ["events", "--workspace", self.workspace, "--doc", DOC, "--kind", "defect_raised"])
        self.assertEqual(code, 0, err)
        return listing["results"][0]["event"]["finding"]

    def test_a_native_ranged_defect_line_whose_identity_differs_is_news(self):
        """F5 remainder, her shape: the reader computes another id from the first-line form."""
        native_id = self.raise_defect(self.RANGED)
        body = self.render(self.RUN_R)
        defect_line = body["lines"][1]
        self.assertIn(legacy.SEP + "src/widget.py:2" + legacy.SEP, defect_line)
        self.assertNotIn("2-3", defect_line)
        item = [i for i in legacy.tolerant_document(body["block"], DOC)["items"]
                if i["kind"] == "defect"][0]
        read_back = ids.finding_id(DOC, legacy.item_slice(item, DOC), item["location"],
                                   item.get("claim"), item.get("scenario"))
        self.assertNotEqual(read_back, native_id, "the oracle: the line names another finding")
        self.place(body["block"])
        code, report, err = self.dry_run()
        self.assertEqual(code, 0, (report, err))
        self.assertEqual(report["native_rendered"], 1, report)  # the disposition line only
        self.assertEqual(report["counts"].get("defect_raised"), 1, report)
        self.assertGreater(report["would_import"], 0, report)
        code, report, err = self.import_now()
        self.assertEqual(code, 0, (report, err))
        imported = [row["finding"] for row in report["appended"] if row["kind"] == "defect_raised"]
        self.assertEqual(imported, [read_back])

    def test_a_native_defect_line_that_reads_back_to_its_own_id_is_still_recognised(self):
        """F5 remainder, the ordinary defect stays green: one `file:line`, the same identity."""
        self.raise_defect(testlib.location("src/widget.py:2", "src/widget.py", 2))
        self.place(self.render(self.RUN_R)["block"])
        code, report, err = self.dry_run()
        self.assertEqual(code, 0, (report, err))
        self.assertEqual(report["native_rendered"], 2, report)
        self.assertEqual(sorted(report["counts"]), ["card_observed"], report)

    def test_a_native_clear_whose_line_joins_another_finding_is_news(self):
        """F5 remainder for a clearing line: the finding a recheck line imports to is the one the
        importer's own join names. A native ranged finding's clear renders its first `file:line`;
        when the log also holds a finding of the same slice AT that line with the same claim, the
        join names that other finding, so the line is its clear (news), never skipped."""
        other = testlib.location("src/widget.py:2", "src/widget.py", 2)
        self.append([testlib.opened(self.identity), self.raise_native("A", loc=self.RANGED),
                     self.raise_native("A", loc=other, at="2026-04-01T09:00:02Z")], testlib.ZERO)
        raised = self.raised_events()
        ranged_id = [e["finding"] for e in raised if e["location"]["raw"].endswith("2-3")][0]
        other_id = [e["finding"] for e in raised if e["finding"] != ranged_id][0]
        clear = testlib.disposition(ranged_id, self.identity)
        clear["actor"] = dict(ACTOR)
        self.append([clear])
        self.place(self.render()["block"])
        code, report, err = self.dry_run()
        self.assertEqual(code, 0, (report, err))
        self.assertEqual(report["native_rendered"], 0, report)
        self.assertEqual(report["counts"].get("disposition"), 1, report)
        code, report, err = self.import_now()
        self.assertEqual(code, 0, (report, err))
        cleared = [row["finding"] for row in report["appended"] if row["kind"] == "disposition"]
        self.assertEqual(cleared, [other_id])


class N3TheMatcherIsIterative(Workspace):
    """N3 (`probe_matching_depth.py`): 1,000 legal native `not_fixed` dispositions of one
    finding, appended and rendered, placed in the document as written. The recursive augmenting
    path died with `RecursionError` (exit 1, empty stdout); every line must be recognised."""

    COUNT = 1000

    def test_one_thousand_native_not_fixed_lines_are_all_recognised(self):
        import time
        self.append([testlib.opened(self.identity), self.raise_native("A")], testlib.ZERO)
        code, body, err = self.import_now()  # the fixture's `Status:` line, observed once
        self.assertEqual(code, 0, (body, err))
        finding = self.raised_events()[0]["finding"]
        clears = []
        for n in range(self.COUNT):
            clear = testlib.disposition(finding, self.identity, value="not_fixed",
                                        verified={"known": False},
                                        at="2026-04-02T%02d:%02d:%02dZ" % (n // 3600, n // 60 % 60, n % 60))
            clear["actor"] = {"station": "recheck", "run_id": "recheck-n3",
                              "harness": "claude-code"}
            clears.append(clear)
        self.append(clears)
        body = self.render("recheck-n3")
        self.assertEqual(body["rendered"], self.COUNT)
        self.place(body["block"])
        started = time.time()
        code, report, err = self.dry_run()
        elapsed = time.time() - started
        self.assertEqual(code, 0, (report, err[-2000:]))
        self.assertEqual(report["native_rendered"], self.COUNT, report)
        self.assertEqual(report["would_import"], 0, report)
        self.assertEqual(report["ambiguous"], 0, report)
        sys.stderr.write("\n[N3] import-legacy --dry-run over %d native lines: %.2fs\n"
                         % (self.COUNT, elapsed))

    def test_the_matching_is_maximum_and_keeps_file_order(self):
        """N3: the iterative matcher still finds a maximum matching, earlier lines first."""
        from records_core import importer

        class U(object):
            def __init__(self, text, slices):
                self.kind = "item"
                self.item = {"kind": "recheck", "text": text,
                             "heading": {"slices": list(slices)}}

        natives = [importer.NativeLine("disposition", "x", "A", "f1:a", 1),
                   importer.NativeLine("disposition", "x", "B", "f1:b", 2)]
        # line 0 admits A or B, line 1 admits A only: a greedy pass gives line 0 A and strands
        # line 1; the maximum matching recognises both.
        units = [U("x", ["A", "B"]), U("x", ["A"])]
        self.assertEqual(sorted(importer.match_native_lines(units, natives, DOC)), [0, 1])
        # a path as long as the history: every line holds its first occurrence until the last
        # line, which admits only the first; the one augmenting path runs through all of them.
        n = 5000
        natives = [importer.NativeLine("disposition", "x", "A", "f1:%d" % i, i) for i in range(n)]
        units = [U("x", ["A"]) for _ in range(n)]
        options = dict((i, [i, i + 1]) for i in range(n - 1))
        options[n - 1] = [0]
        owner, matched = {}, {}
        for position in range(n):
            free = next((i for i in options[position] if i not in owner), None)
            if free is not None:
                owner[free], matched[position] = position, free
            else:
                self.assertTrue(importer._augment(position, options, owner, matched))
        self.assertEqual(len(matched), n)
        self.assertEqual(sorted(matched.values()), list(range(n)))
        # three lines, two occurrences: the first two lines (file order) keep them.
        natives = natives[:2]
        natives[1].slice = "B"
        units = [U("x", ["A", "B"]), U("x", ["A", "B"]), U("x", ["A", "B"])]
        self.assertEqual(sorted(importer.match_native_lines(units, natives, DOC)), [0, 1])


if __name__ == "__main__":
    unittest.main()
