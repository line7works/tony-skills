"""One synthetic fixture per shape family of contract section 11.1, each asserting its events.

The families are L1 to L6 (the location shapes), F1 to F4 (the line shapes), S1 (a first field
that is not a severity) and D1 (two findings with one identity). Each has its own document under
`fixtures/legacy/docs/plans/`, built into a throwaway git repository by `fixtures/build.py`, and
each test asserts the events the importer would produce for it: the kinds, the counts, and the
fields the family is about.

Nothing here writes: every test reads the plan, which takes no lock and touches no file.
"""
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import ids, legacy  # noqa: E402

PLANS = "docs/plans/"


class Family(unittest.TestCase):
    """A shared, read-only fixture workspace; the plan of one document per test."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-families-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def text(self, name):
        with open(self.workspace + "/" + PLANS + name, encoding="utf-8") as fh:
            return fh.read()

    def plan(self, name):
        return testlib.plan_for(self.workspace, PLANS + name)

    def events(self, name, kind=None):
        rows = self.plan(name)["events"]
        return [e for e in rows if kind is None or e["kind"] == kind]

    def counts(self, name):
        return self.plan(name)["counts"]

    def one(self, name, kind):
        rows = self.events(name, kind)
        self.assertEqual(len(rows), 1, "%s: expected one %s, got %d" % (name, kind, len(rows)))
        return rows[0]

    def assertJoins(self, name, basis="exact"):
        """Every clear in the document joined, on the basis named."""
        for event in self.events(name):
            if event["kind"] in ("disposition", "waived", "reopened"):
                self.assertEqual(event["join_basis"], basis, "%s seq %s" % (name, event.get("seq")))


class L1Backticks(Family):
    DOC = "2026-05-01-l1-backticks.md"

    def test_a_backticked_location_is_read_and_its_backticks_are_not_in_the_key(self):
        raised = self.events(self.DOC, "finding_raised")
        self.assertEqual(len(raised), 2)
        first = raised[0]
        self.assertEqual(first["location"]["raw"], "`src/packer.py:12`")
        self.assertEqual(first["location"]["file"], "src/packer.py")
        self.assertEqual(first["location"]["line"], 12)
        self.assertTrue(first["location"]["resolved"])
        self.assertEqual(ids.location_key(first["location"]), "src/packer.py:12")

    def test_the_recheck_line_joins_the_backticked_finding(self):
        self.assertEqual(self.counts(self.DOC),
                         {"card_observed": 1, "finding_raised": 2, "disposition": 1})
        self.assertJoins(self.DOC, "exact")

    def test_the_strict_reader_calls_every_one_of_these_lines_ambiguous(self):
        """The family exists because the pilot's own reader cannot read it (section 11.1)."""
        text = self.text(self.DOC)
        strict = legacy.parse_document(text, PLANS + self.DOC)
        self.assertEqual([r["kind"] for r in strict["records"]], ["ambiguous"] * 3)


class L2Ranges(Family):
    DOC = "2026-05-01-l2-ranges.md"

    def test_a_hyphen_range_carries_its_end(self):
        first = self.events(self.DOC, "finding_raised")[0]
        self.assertEqual((first["location"]["file"], first["location"]["line"],
                          first["location"]["line_end"]), ("src/ramp.py", 20, 28))

    def test_an_en_dash_range_carries_its_end_too(self):
        second = self.events(self.DOC, "finding_raised")[1]
        self.assertEqual((second["location"]["line"], second["location"]["line_end"]), (51, 55))
        self.assertEqual(second["location"]["raw"], "src/ramp.py:51–55")

    def test_the_range_stays_in_the_join_key_and_the_recheck_line_joins(self):
        first = self.events(self.DOC, "finding_raised")[0]
        self.assertEqual(ids.location_key(first["location"]), "src/ramp.py:20-28")
        cleared = self.one(self.DOC, "disposition")
        self.assertEqual(cleared["finding"], first["finding"])
        self.assertEqual(cleared["disposition"], "not_fixed")
        self.assertEqual(cleared["join_basis"], "exact")


class L3NoLineNumber(Family):
    DOC = "2026-05-01-l3-no-line-number.md"

    def test_a_field_with_no_file_line_keeps_its_text_and_resolves_to_nothing(self):
        for event in self.events(self.DOC, "finding_raised"):
            location = event["location"]
            self.assertFalse(location["resolved"])
            self.assertEqual((location["file"], location["line"], location["line_end"]),
                             (None, None, None))
            self.assertTrue(location["raw"])

    def test_it_still_joins_on_the_raw_text(self):
        cleared = self.one(self.DOC, "disposition")
        self.assertEqual(cleared["join_basis"], "exact")
        self.assertEqual(cleared["finding"], self.events(self.DOC, "finding_raised")[0]["finding"])


class L4SeveralLocations(Family):
    DOC = "2026-05-01-l4-several-locations.md"

    def test_the_first_location_wins_and_the_rest_go_to_more(self):
        first = self.events(self.DOC, "finding_raised")[0]
        location = first["location"]
        self.assertEqual((location["file"], location["line"]), ("src/label.py", 8))
        self.assertEqual(location["more"],
                         [{"file": "src/label.py", "line": 19, "line_end": None, "tag": None},
                          {"file": "src/printer.py", "line": 33, "line_end": None, "tag": None}])

    def test_a_comma_separated_field_splits_too(self):
        second = self.events(self.DOC, "finding_raised")[1]
        self.assertEqual((second["location"]["file"], second["location"]["line"]),
                         ("src/label.py", 60))
        self.assertEqual([m["line"] for m in second["location"]["more"]], [74])

    def test_the_whole_field_is_the_join_key_so_the_recheck_line_joins(self):
        first = self.events(self.DOC, "finding_raised")[0]
        self.assertEqual(ids.location_key(first["location"]),
                         "src/label.py:8, :19 and src/printer.py:33")
        self.assertEqual(self.one(self.DOC, "disposition")["finding"], first["finding"])


class L5OtherForms(Family):
    DOC = "2026-05-01-l5-other-forms.md"

    def test_a_path_outside_the_repository_still_resolves_to_a_file_and_a_line(self):
        first = self.events(self.DOC, "finding_raised")[0]
        self.assertEqual((first["location"]["file"], first["location"]["line"]),
                         ("~/crates/desk-notes.txt", 4))

    def test_a_note_in_place_of_a_location_resolves_to_nothing_and_joins_on_its_text(self):
        second = self.events(self.DOC, "finding_raised")[1]
        self.assertFalse(second["location"]["resolved"])
        self.assertEqual(self.one(self.DOC, "disposition")["finding"], second["finding"])


class L6GluedTag(Family):
    DOC = "2026-05-01-l6-glued-tag.md"

    def test_a_tag_glued_to_a_file_line_is_carried_and_left_out_of_the_key(self):
        first = self.events(self.DOC, "finding_raised")[0]
        self.assertEqual(first["location"]["tag"], "second pass")
        self.assertEqual(ids.location_key(first["location"]), "src/scale.py:31")

    def test_a_tag_glued_to_a_range_is_carried_and_left_out_of_the_key(self):
        second = self.events(self.DOC, "finding_raised")[1]
        self.assertEqual(second["location"]["tag"], "tare")
        self.assertEqual((second["location"]["line"], second["location"]["line_end"]), (77, 80))
        self.assertEqual(ids.location_key(second["location"]), "src/scale.py:77-80")

    def test_both_recheck_lines_join_the_tagged_findings_without_the_tag(self):
        raised = dict((e["finding"], e) for e in self.events(self.DOC, "finding_raised"))
        cleared = self.events(self.DOC, "disposition")
        self.assertEqual(len(cleared), 2)
        for event in cleared:
            self.assertIn(event["finding"], raised)
            self.assertEqual(event["join_basis"], "exact")


class F1FusedDisposition(Family):
    DOC = "2026-05-01-f1-fused-disposition.md"

    def test_every_dash_the_corpus_uses_is_read(self):
        cleared = self.events(self.DOC, "disposition")
        self.assertEqual(len(cleared), 3)
        self.assertEqual([e["disposition"] for e in cleared], ["fixed", "not_fixed", "fixed"])

    def test_the_word_is_the_disposition_and_the_text_is_the_how(self):
        cleared = self.events(self.DOC, "disposition")
        self.assertEqual(cleared[0]["how"], "executed: the latch test runs on every crate")
        self.assertEqual(cleared[1]["how"], "static: the constant is still there")
        self.assertEqual(cleared[2]["how"], "executed: the crate id is in every line")

    def test_a_not_fixed_line_leaves_its_finding_open(self):
        testlib.add_scripts_to_path()
        from records_core import state as state_mod
        events = self.plan(self.DOC)["events"]
        for index, event in enumerate(events):
            event["seq"] = index
        rows = state_mod.state_of(PLANS + self.DOC, events)["findings"]
        by_status = dict((r["severity"], r["status"]) for r in rows)
        self.assertEqual(by_status, {"BLOCKER": "fixed", "MAJOR": "open", "MINOR": "fixed"})


class F2FieldCounts(Family):
    DOC = "2026-05-01-f2-field-counts.md"

    def test_three_fields_make_the_third_the_scenario_and_no_claim(self):
        short = [e for e in self.events(self.DOC, "finding_raised") if e["severity"] == "MINOR"][0]
        self.assertIsNone(short["claim"])
        self.assertEqual(short["scenario"], "a stack is never numbered")
        self.assertIsNone(short["raised_by"])

    def test_more_than_five_fields_join_the_scenario_with_the_separator_kept(self):
        long = [e for e in self.events(self.DOC, "finding_raised") if e["severity"] == "BLOCKER"][0]
        self.assertEqual(long["claim"], "the pallet weight is read from the wrong column")
        self.assertEqual(long["scenario"],
                         "every stack is under-weighted · observed on the Tuesday run · "
                         "the loader agrees")
        self.assertEqual(long["raised_by"], "Slice A review")

    def test_a_six_field_finding_keeps_its_middle_field_in_the_scenario(self):
        six = [e for e in self.events(self.DOC, "finding_raised") if e["severity"] == "MAJOR"][0]
        self.assertEqual(six["claim"], "the stack height is unbounded")
        self.assertEqual(six["scenario"], "a tall stack topples · the ramp test reproduces it")
        self.assertEqual(six["raised_by"], "Slice A review")
        self.assertEqual(self.one(self.DOC, "disposition")["finding"], six["finding"],
                         "the recheck line joins the six-field finding on its claim")


class F3DefectForms(Family):
    DOC = "2026-05-01-f3-defect-forms.md"

    def test_all_three_legacy_defect_forms_are_read(self):
        defects = self.events(self.DOC, "defect_raised")
        self.assertEqual(len(defects), 3)
        self.assertEqual([d["location"]["line"] for d in defects], [30, 41, 52])

    def test_the_dashed_form_splits_the_claim_from_the_scenario(self):
        first = self.events(self.DOC, "defect_raised")[0]
        self.assertEqual(first["claim"], "the tension check runs twice per strap")
        self.assertEqual(first["scenario"], "the second run reports the first run's value")
        self.assertEqual(first["raised_by"], "Slice A recheck")

    def test_the_form_without_a_scenario_keeps_the_text_as_the_claim(self):
        second = self.events(self.DOC, "defect_raised")[1]
        self.assertEqual(second["claim"], "the strap log now writes one line per measurement")
        self.assertIsNone(second["scenario"])

    def test_the_fix_introduced_spelling_is_the_same_record(self):
        third = self.events(self.DOC, "defect_raised")[2]
        self.assertEqual(third["claim"], "the tension constant is duplicated")
        self.assertEqual(third["scenario"], "one copy is never read")

    def test_every_defect_is_charged_to_the_headings_slice_and_causes_nothing(self):
        for defect in self.events(self.DOC, "defect_raised"):
            self.assertEqual(defect["slice"], "A")
            self.assertIsNone(defect["caused_by"])


class F4OtherRecheckPatterns(Family):
    DOC = "2026-05-01-f4-other-recheck-patterns.md"

    def test_section_11_3_adds_no_rule_for_them_so_each_is_unparsed(self):
        self.assertEqual(self.counts(self.DOC),
                         {"card_observed": 1, "finding_raised": 1, "legacy_unparsed": 2})

    def test_each_carries_its_raw_text_and_a_reason(self):
        reasons = []
        for event in self.events(self.DOC, "legacy_unparsed"):
            self.assertTrue(event["origin"]["raw"].startswith("- MAJOR"))
            self.assertTrue(event["reason"])
            reasons.append(event["reason"])
        self.assertIn("field count 3 matches no shape under a recheck heading", reasons[0])
        self.assertIn("fourth field 'confirmed' is neither a disposition", reasons[1])

    def test_they_bear_no_state_so_the_finding_stays_open(self):
        testlib.add_scripts_to_path()
        from records_core import state as state_mod
        events = self.plan(self.DOC)["events"]
        for index, event in enumerate(events):
            event["seq"] = index
        rows = state_mod.state_of(PLANS + self.DOC, events)["findings"]
        self.assertEqual([r["status"] for r in rows], ["open"])


class S1NotASeverity(Family):
    DOC = "2026-05-01-s1-not-a-severity.md"

    def test_every_line_whose_first_field_is_not_a_severity_is_unparsed(self):
        self.assertEqual(self.counts(self.DOC),
                         {"card_observed": 1, "finding_raised": 1, "legacy_unparsed": 3})

    def test_the_reason_names_the_field_it_read(self):
        reasons = [e["reason"] for e in self.events(self.DOC, "legacy_unparsed")]
        self.assertTrue(all("neither a severity nor a grant keyword" in r for r in reasons), reasons)
        self.assertIn("'QUESTION'", reasons[0])
        self.assertIn("'MINOR (pre-existing)'", reasons[1])

    def test_a_bulleted_line_without_a_severity_blocks_nothing(self):
        self.assertEqual(self.plan(self.DOC)["ambiguities"], [])


class D1TwoFindingsOneIdentity(Family):
    DOC = "2026-05-01-d1-one-identity.md"

    def test_the_second_raise_stops_the_document(self):
        plan = self.plan(self.DOC)
        self.assertEqual(len(plan["ambiguities"]), 1)
        stop = plan["ambiguities"][0]
        self.assertEqual(stop["line"], 14)
        self.assertIn("compute the same finding id", stop["reason"])
        self.assertIn("section 7", stop["reason"])

    def test_the_explanation_names_the_line_it_collides_with(self):
        stop = self.plan(self.DOC)["ambiguities"][0]
        self.assertEqual([c["line"] for c in stop["candidates"]], [13])
        self.assertTrue(stop["candidates"][0]["finding"].startswith("f1:"))
        self.assertEqual(stop["candidates"][0]["slice"], "A")

    def test_the_two_lines_really_do_compute_one_id(self):
        items = [i for i in legacy.tolerant_document(self.text(self.DOC), PLANS + self.DOC)["items"]
                 if i["kind"] == "finding"]
        keys = set(ids.finding_id(PLANS + self.DOC, "A", i["location"], i["claim"], i["scenario"])
                   for i in items)
        self.assertEqual(len(items), 2)
        self.assertEqual(len(keys), 1)


class TheGrantShapes(Family):
    DOC = "2026-05-05-grants.md"

    def test_a_waiver_and_a_reopening_written_without_a_bullet_are_read(self):
        self.assertEqual(self.counts(self.DOC),
                         {"card_observed": 1, "finding_raised": 2, "disposition": 1,
                          "waived": 1, "reopened": 1})

    def test_the_waiver_carries_its_grant_date_its_severity_and_no_words(self):
        waived = self.one(self.DOC, "waived")
        self.assertEqual(waived["grant_date"], "2026-05-06")
        self.assertEqual(waived["severity"], "BLOCKER")
        self.assertIsNone(waived["words"])
        self.assertEqual(waived["at"], "2026-05-06", "an imported grant's `at` is its grant date")
        self.assertEqual(waived["verified_source"], {"known": False}, "owner ruling O4")

    def test_the_reopening_carries_its_quoted_words(self):
        reopened = self.one(self.DOC, "reopened")
        self.assertEqual(reopened["words"], "the dawn write came back")
        self.assertEqual(reopened["grant_date"], "2026-05-07")
        self.assertEqual(reopened["at"], "2026-05-07")

    def test_a_grant_line_is_the_one_shape_read_without_its_bullet(self):
        """Every structured grant line under docs/ in this repository is written that way."""
        text = "\n".join([
            "### 2026-05-05 — review: Slice A",
            "- MAJOR · src/a.py:1 · a claim · a scenario · Slice A review",
            "MAJOR · src/a.py:1 · another claim · another scenario · Slice A review",
            "WAIVED (per user) · 2026-05-06 · MAJOR · src/a.py:1 · a claim",
            "",
        ])
        items = legacy.tolerant_document(text, "docs/plans/x.md")["items"]
        self.assertEqual([i["kind"] for i in items], ["finding", "waiver"],
                         "a bulletless line that is not a grant is not a record")


if __name__ == "__main__":
    unittest.main()
