"""`render` as a command (contract section 9.4 and 12.2).

The byte-for-byte comparison with the pilot's writers is in `test_parity.py`; here is what the
command does with a real log: which events it renders, which it names as skipped, how it builds
the heading, and that it writes nothing.
"""
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import identity as identity_mod, legacy, render  # noqa: E402

DOC = testlib.DOC
GRANTS = "docs/plans/2026-05-05-grants.md"


class RenderFromAnImportedLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-render-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)
        code, body, err = testlib.run_json(
            ["import-legacy", "--workspace", cls.workspace, "--doc", GRANTS])
        assert code == 0, (body, err)
        cls.run_id = body["run_id"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def render(self, run_id=None):
        code, body, err = testlib.run_json(
            ["render", "--workspace", self.workspace, "--doc", GRANTS,
             "--run-id", run_id or self.run_id])
        self.assertEqual(code, 0, err)
        return body

    def test_it_renders_the_block_the_run_wrote(self):
        body = self.render()
        self.assertEqual(body["date"], "2026-05-06")
        self.assertEqual(body["slices"], ["A"])
        self.assertTrue(body["block"].startswith("\n### 2026-05-06 — recheck: Slice A\n"))
        self.assertEqual(len(body["lines"]), 1)
        self.assertIn("· (the shift log is written at dawn) · fixed · ", body["lines"][0])

    def test_the_grants_follow_the_block_as_standalone_lines(self):
        body = self.render()
        self.assertEqual(len(body["grants"]), 2)
        self.assertTrue(body["grants"][0].startswith("- " + legacy.WAIVED))
        self.assertTrue(body["grants"][1].startswith("- " + legacy.REOPENED))
        # E13 amendment A4: the review block this run's `finding_raised` events produce comes
        # first, then the recheck block, then the grants.
        self.assertEqual(body["text"],
                         body["review"] + body["block"] + "".join(body["grants"]))
        self.assertEqual(body["rendered"], 3 + len(body["review_lines"]))

    def test_a_waiver_without_words_keeps_the_legacy_grant_shape(self):
        waiver = self.render()["grants"][0]
        self.assertEqual(waiver.count(legacy.SEP), 4)
        self.assertNotIn('"', waiver)

    def test_a_reopening_with_words_quotes_them(self):
        reopening = self.render()["grants"][1]
        self.assertIn('"the dawn write came back"', reopening)

    def test_every_event_the_run_wrote_that_carries_no_line_is_named_as_skipped(self):
        body = self.render()
        kinds = sorted(set(row["kind"] for row in body["skipped"]))
        # `finding_raised` left this list in E13 amendment A4: it renders a review block now.
        self.assertEqual(kinds, ["card_observed", "import_finished", "import_started",
                                 "log_opened"])

    def test_a_run_nobody_wrote_renders_nothing_rather_than_failing(self):
        body = self.render("a-run-that-never-happened")
        self.assertEqual(body["text"], "")
        self.assertEqual(body["lines"], [])
        self.assertEqual(body["grants"], [])
        self.assertIsNone(body["date"])
        self.assertEqual(body["rendered"], 0)

    def test_it_writes_nothing(self):
        before = testlib.porcelain(self.workspace)
        digest = testlib.doc_sha256(self.workspace, GRANTS)
        self.render()
        self.assertEqual(testlib.porcelain(self.workspace), before)
        self.assertEqual(testlib.doc_sha256(self.workspace, GRANTS), digest)

    def test_it_is_byte_stable_across_runs(self):
        code, first, _ = testlib.run_cli(
            ["render", "--workspace", self.workspace, "--doc", GRANTS, "--run-id", self.run_id])
        code, second, _ = testlib.run_cli(
            ["render", "--workspace", self.workspace, "--doc", GRANTS, "--run-id", self.run_id])
        self.assertEqual(first, second)


class RenderFromANativeLog(unittest.TestCase):
    """A run a station wrote, with a defect line and two slices in one heading."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-render-native-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def append(self, events, head):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        code, doc, err = testlib.run_json(
            ["append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
             "--expect-head", head])
        self.assertEqual(code, 0, (doc, err))
        return doc

    def test_a_defect_line_under_a_two_slice_heading_names_the_slice_it_is_charged_to(self):
        raised_a = testlib.raised(identity=self.identity, slice_name="A")
        raised_b = testlib.raised(identity=self.identity, slice_name="B",
                                  claim="the gauge never resets",
                                  loc=testlib.location("src/gauge.py:3", "src/gauge.py", 3))
        first = self.append([testlib.opened(self.identity), raised_a, raised_b], testlib.ZERO)
        code, listing, _ = testlib.run_json(
            ["events", "--workspace", self.workspace, "--doc", DOC, "--kind", "finding_raised"])
        ids_by_slice = dict((row["event"]["slice"], row["event"]["finding"])
                            for row in listing["results"])
        run = "recheck-2026-04-02-ab"
        actor = {"station": "recheck", "run_id": run, "harness": "claude-code"}
        clear_a = testlib.disposition(ids_by_slice["A"], self.identity, at="2026-04-02T09:00:00Z")
        clear_a["actor"] = dict(actor)
        clear_b = testlib.disposition(ids_by_slice["B"], self.identity, at="2026-04-02T09:00:01Z",
                                      value="not_fixed", verified={"known": False})
        clear_b["actor"] = dict(actor)
        defect = testlib.native("defect_raised", at="2026-04-02T09:00:02Z", identity=self.identity,
                                actor=actor, slice="B", severity="MINOR",
                                location=testlib.location("src/gauge.py:9", "src/gauge.py", 9),
                                claim="the reset runs twice", scenario="the second reset is a no-op",
                                raised_by="A", caused_by=ids_by_slice["A"])
        self.append([clear_a, clear_b, defect], first["head"])
        code, body, err = testlib.run_json(
            ["render", "--workspace", self.workspace, "--doc", DOC, "--run-id", run])
        self.assertEqual(code, 0, err)
        self.assertEqual(body["slices"], ["A", "B"])
        self.assertTrue(body["block"].startswith("\n### 2026-04-02 — recheck: Slice A, Slice B\n"))
        self.assertEqual(len(body["lines"]), 3)
        self.assertTrue(body["lines"][2].endswith(legacy.SEP + "B"),
                        "E8-A25: under a multi-slice heading the defect line names its charge")
        self.assertIn("broke: the reset runs twice — the second reset is a no-op", body["lines"][2])
        self.assertIn(legacy.SEP + "not fixed" + legacy.SEP, body["lines"][1])

    def test_a_disposition_naming_a_finding_the_log_never_raised_cannot_be_rendered(self):
        """It cannot happen through `append`; the library still refuses rather than guessing."""
        events = [{"seq": 0, "kind": "disposition", "finding": "f1:" + "a" * 20,
                   "disposition": "fixed", "how": "x", "at": "2026-04-02T09:00:00Z",
                   "actor": {"station": "s", "run_id": "r", "harness": None}}]
        with self.assertRaises(render.RenderError):
            render.render_run(DOC, events, "r")


if __name__ == "__main__":
    unittest.main()
