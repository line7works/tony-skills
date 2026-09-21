"""The join of contract section 11.4 and the stop of section 11.5.

One fixture per join basis (`exact`, `location_only_no_claim`, `location_only`) and one per
ambiguous case (a location several findings share, a location no finding holds, and a finding
whose slice the heading does not name). Each ambiguous case is driven through the CLI as well as
the library, so exit 5, the explanation's content, and an untouched log are all measured.
"""
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import events as events_mod  # noqa: E402

PLANS = "docs/plans/"
EXACT = "2026-05-03-join-exact.md"
NO_CLAIM = "2026-05-03-join-no-claim.md"
LOCATION_ONLY = "2026-05-03-join-location-only.md"
SHARED = "2026-05-03-join-ambiguous-shared.md"
NOTHING = "2026-05-03-join-ambiguous-nothing.md"
OTHER_SLICE = "2026-05-03-join-ambiguous-other-slice.md"
AMBIGUOUS = (SHARED, NOTHING, OTHER_SLICE)


class JoinCase(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-join-")
        self.workspace = testlib.fixture_workspace(self.scratch)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def doc(self, name):
        return PLANS + name

    def log_path(self, name):
        return events_mod.log_path(self.workspace, self.doc(name))

    def run_import(self, name, *extra):
        args = ["import-legacy", "--workspace", self.workspace, "--doc", self.doc(name)] + list(extra)
        return testlib.run_json(args)


class TheThreeJoinBases(JoinCase):
    def basis(self, name):
        plan = testlib.plan_for(self.workspace, self.doc(name))
        self.assertEqual(plan["ambiguities"], [], name)
        cleared = [e for e in plan["events"] if e["kind"] == "disposition"]
        self.assertEqual(len(cleared), 1, name)
        return cleared[0], plan

    def test_rule_1_an_exact_location_and_claim(self):
        cleared, plan = self.basis(EXACT)
        self.assertEqual(cleared["join_basis"], "exact")
        raised = [e for e in plan["events"] if e["kind"] == "finding_raised"]
        self.assertEqual(cleared["finding"], raised[0]["finding"])
        self.assertNotEqual(cleared["finding"], raised[1]["finding"])

    def test_rule_2_no_claim_and_one_finding_at_the_location(self):
        cleared, _ = self.basis(NO_CLAIM)
        self.assertEqual(cleared["join_basis"], "location_only_no_claim")

    def test_rule_3_a_reworded_claim_at_a_location_one_finding_of_the_slice_holds(self):
        cleared, _ = self.basis(LOCATION_ONLY)
        self.assertEqual(cleared["join_basis"], "location_only")

    def test_owner_ruling_o3_is_visible_on_the_event(self):
        """Every reader can see that the claim was reworded, which is the point of O3."""
        cleared, _ = self.basis(LOCATION_ONLY)
        self.assertEqual(cleared["origin"]["kind"], "legacy")
        self.assertIn("wrong sensor", cleared["origin"]["raw"])
        self.assertEqual(cleared["verified_source"], {"known": False})

    def test_each_basis_lands_in_the_log_and_reaches_derived_state(self):
        for name, basis in ((EXACT, "exact"), (NO_CLAIM, "location_only_no_claim"),
                            (LOCATION_ONLY, "location_only")):
            code, doc, err = self.run_import(name)
            self.assertEqual(code, 0, "%s: %s %s" % (name, doc, err))
            code, state, err = testlib.run_json(
                ["state", "--workspace", self.workspace, "--doc", self.doc(name)])
            self.assertEqual(code, 0, err)
            decided = [f for f in state["findings"] if f["decided"] is not None]
            self.assertEqual(len(decided), 1, name)
            self.assertEqual(decided[0]["join_basis"], basis, name)
            self.assertTrue(decided[0]["cleared_unbound"], "owner ruling O4")


class AnAmbiguousLineStopsTheDocument(JoinCase):
    def test_each_ambiguous_case_exits_five(self):
        for name in AMBIGUOUS:
            code, doc, err = self.run_import(name)
            self.assertEqual(code, 5, "%s: %s" % (name, err))
            self.assertFalse(doc["ok"], name)
            self.assertEqual(doc["error"], "ambiguous_identity", name)
            self.assertEqual(doc["report"], "import", name)

    def test_nothing_is_written_and_no_log_is_left_behind(self):
        before = testlib.porcelain(self.workspace)
        for name in AMBIGUOUS:
            code, doc, _ = self.run_import(name)
            self.assertEqual(code, 5)
            self.assertFalse(os.path.exists(self.log_path(name)), name)
            self.assertFalse(os.path.exists(self.log_path(name) + ".lock"), name)
        self.assertEqual(testlib.porcelain(self.workspace), before)

    def test_a_document_already_imported_keeps_its_log_untouched_when_a_later_line_is_ambiguous(self):
        """The stop is the whole document's: a second pass that goes ambiguous writes nothing."""
        code, first, err = self.run_import(EXACT)
        self.assertEqual(code, 0, err)
        with open(self.log_path(EXACT), "rb") as fh:
            before = fh.read()
        path = os.path.join(self.workspace, *self.doc(EXACT).split("/"))
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n### 2026-05-05 — recheck: Slice A\n"
                     "- MINOR · src/chock.py:404 · (a claim nothing holds) · fixed · executed\n")
        code, doc, _ = self.run_import(EXACT)
        self.assertEqual(code, 5)
        with open(self.log_path(EXACT), "rb") as fh:
            self.assertEqual(fh.read(), before)

    def test_the_explanation_names_the_line_its_text_and_the_reason(self):
        code, doc, _ = self.run_import(SHARED)
        self.assertEqual(code, 5)
        self.assertEqual(len(doc["ambiguities"]), 1)
        stop = doc["ambiguities"][0]
        self.assertEqual(stop["line"], 16)
        self.assertIn("(the seal is not verified)", stop["raw"])
        self.assertIn("2 findings of this document hold the location 'src/seal.py:30'",
                      stop["reason"])

    def test_the_explanation_names_every_candidate_with_its_line(self):
        code, doc, _ = self.run_import(SHARED)
        stop = doc["ambiguities"][0]
        self.assertEqual(len(stop["candidates"]), 2)
        self.assertEqual(sorted(c["line"] for c in stop["candidates"]), [12, 13])
        for candidate in stop["candidates"]:
            self.assertTrue(candidate["finding"].startswith("f1:"))
            self.assertEqual(candidate["slice"], "A")

    def test_a_location_no_finding_holds_says_so_and_offers_no_candidate(self):
        code, doc, _ = self.run_import(NOTHING)
        stop = doc["ambiguities"][0]
        self.assertIn("no finding of this document holds the location 'src/floor.py:90'",
                      stop["reason"])
        self.assertEqual(stop["candidates"], [])

    def test_a_finding_of_another_slice_is_not_joined_on_location_alone(self):
        """Rule 3 needs the one finding at the location to belong to a slice the heading names."""
        code, doc, _ = self.run_import(OTHER_SLICE)
        stop = doc["ambiguities"][0]
        self.assertIn("its claim is worded differently", stop["reason"])
        self.assertIn("its slice 'A' is not one of the heading's (B)", stop["reason"])
        self.assertEqual([c["slice"] for c in stop["candidates"]], ["A"])

    def test_the_stop_reports_what_the_pass_would_otherwise_have_recorded(self):
        """A reader sees the shape of the document even though nothing was written."""
        code, doc, _ = self.run_import(SHARED)
        self.assertEqual(doc["counts"], {"card_observed": 1, "finding_raised": 2})
        self.assertEqual(doc["lines_read"], 17)
        self.assertEqual(doc["lines_classified"], 4)
        self.assertEqual(doc["head"], testlib.ZERO)
        self.assertEqual(doc["events"], 0)

    def test_a_dry_run_stops_the_same_way_and_says_it_was_a_dry_run(self):
        code, doc, _ = self.run_import(SHARED, "--dry-run")
        self.assertEqual(code, 5)
        self.assertTrue(doc["dry_run"])
        self.assertEqual(len(doc["ambiguities"]), 1)

    def test_the_refusal_validates_against_the_import_report_schema(self):
        code, doc, _ = self.run_import(SHARED)
        from records_core import validate
        errors = validate.validate_document("import_report", doc, testlib.schemas())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
