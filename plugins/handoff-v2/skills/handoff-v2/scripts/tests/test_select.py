"""`select`: the doc hunt (ruling E15-10, the copied `hunt.py`, the repo's tiers; A2 Q4: no vault tier) and the
feature identity (CR-15: the `<topic>` of a dated plan, else the flat `<feature>`, else a slug of the title; none
is a stop that asks; the same doc always gives the same identity).
"""
import os
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import doc as docmod  # noqa: E402

D = hlib.D


class TheIdentity(unittest.TestCase):
    """CR-15's three name shapes and the stop, read from the path and the doc's first line."""

    def test_a_dated_plan_gives_its_topic(self):
        self.assertEqual(docmod.identity("docs/plans/2026-09-20-turnstile.md", hlib.build_doc()),
                         ("turnstile", "dated-plan"))

    def test_a_flat_plan_gives_its_feature(self):
        self.assertEqual(docmod.identity("docs/turnstile-build-plan.md", hlib.build_doc()),
                         ("turnstile", "flat-plan"))

    def test_any_other_doc_gives_a_slug_of_its_title(self):
        text = hlib.build_doc(title="# Bench Rig Counter %s build plan (2026-09-20)" % D)
        self.assertEqual(docmod.identity("docs/phase-two.md", text), ("bench-rig-counter", "title"))
        text = hlib.build_doc(title="# The Bench Rig, Phase 2")
        self.assertEqual(docmod.identity("plan/notes.md", text), ("the-bench-rig-phase-2", "title"))

    def test_no_title_gives_none(self):
        text = "Intent: no title line here.\n\n## Slice A %s the counter\nStatus: built\n" % D
        self.assertEqual(docmod.identity("docs/phase-two.md", text), (None, None))

    def test_the_same_doc_gives_the_same_identity_every_time(self):
        text = hlib.build_doc()
        first = docmod.identity("docs/plans/2026-09-20-turnstile.md", text)
        for _ in range(3):
            self.assertEqual(docmod.identity("docs/plans/2026-09-20-turnstile.md", text), first)


@unittest.skipUnless(hlib.jsonschema_here(), "the driver needs jsonschema (run under uv)")
class TheHunt(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-select-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def select(self, ws, args, **station):
        drive, run_dir = hlib.start(self.tmp, ws, **station)
        return drive(["select", "--run-dir", run_dir] + args)

    def test_a_dated_plan_found_by_name(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err = self.select(ws, ["--name", "turnstile"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["doc"], hlib.DOC)
        self.assertEqual(out["feature"], "turnstile")
        self.assertEqual(out["identity_how"], "dated-plan")
        self.assertEqual(out["next"], "photograph")

    def test_the_plans_folder_beats_the_flat_doc_and_the_result_says_which_it_took(self):
        ws, _ = hlib.make_repo(self.tmp, extra_files={"docs/turnstile-build-plan.md": hlib.build_doc()})
        code, out, err = self.select(ws, ["--name", "turnstile"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["doc"], hlib.DOC)
        self.assertTrue(any("docs/turnstile-build-plan.md" in note for note in out["notes"]), out["notes"])

    def test_an_invocation_naming_nothing_stops_and_asks(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err = self.select(ws, [])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "selection-unnamed")

    def test_nothing_found_stops_and_asks(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err = self.select(ws, ["--name", "spinner"])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "selection-none")

    def test_several_in_one_tier_are_listed_never_picked(self):
        ws, _ = hlib.make_repo(self.tmp, extra_files={"docs/plans/2026-09-21-turnstile.md": hlib.build_doc()})
        code, out, err = self.select(ws, ["--name", "turnstile"])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "selection-several")
        self.assertIn("2026-09-21-turnstile.md", out["reason"])

    def test_an_intent_line_is_consulted_only_when_no_file_name_matches(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err = self.select(ws, ["--name", "bench-rig"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["doc"], hlib.DOC)
        self.assertEqual(out["selection"]["how"], "intent-line")

    def test_a_named_doc_outside_the_workspace_is_refused(self):
        ws, _ = hlib.make_repo(self.tmp)
        outside = os.path.join(self.tmp, "elsewhere.md")
        testlib.write_text(outside, hlib.build_doc())
        code, out, err = self.select(ws, ["--doc", outside])
        self.assertEqual(code, 5, (out, err))

    def test_a_doc_with_no_identity_stops_and_asks(self):
        text = "Intent: no title line here.\n\n## Slice A %s the counter\nStatus: built\n\n## Handoffs\n" % D
        ws, _ = hlib.make_repo(self.tmp, text, doc="docs/phase-two.md")
        code, out, err = self.select(ws, ["--doc", "docs/phase-two.md"])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "identity-unnamed")

    def test_the_owners_name_is_taken_only_when_none_derives(self):
        text = "Intent: no title line here.\n\n## Slice A %s the counter\nStatus: built\n\n## Handoffs\n" % D
        ws, _ = hlib.make_repo(self.tmp, text, doc="docs/phase-two.md")
        code, out, err = self.select(ws, ["--doc", "docs/phase-two.md"], feature={"name": "phase-two",
                                                                                  "words": "call it phase-two"})
        self.assertEqual(code, 0, (out, err))
        self.assertEqual((out["feature"], out["identity_how"]), ("phase-two", "owner"))

    def test_an_owners_name_against_a_derived_identity_stops(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err = self.select(ws, ["--name", "turnstile"], feature={"name": "spinner", "words": "call it spinner"})
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "identity-conflict")

    def test_a_block_outside_handoffs_stops_before_anything_else(self):
        text = hlib.build_doc(punch=hlib.handoff_block("2026-09-25"))
        ws, _ = hlib.make_repo(self.tmp, text)
        code, out, err = self.select(ws, ["--name", "turnstile"])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "block-misplaced")


if __name__ == "__main__":
    unittest.main()
