"""Finding identity: contract section 7's key rules, E8-22 and E8-A28."""
import unittest

import testlib

testlib.add_scripts_to_path()
from records_core import canon, ids  # noqa: E402

DOC = "docs/plans/2026-04-01-widget.md"


def loc(raw, **kw):
    return testlib.location(raw, **kw)


class LocationKey(unittest.TestCase):
    def test_backticks_are_removed(self):
        self.assertEqual(ids.location_key(loc("`src/widget.py:88`")), "src/widget.py:88")

    def test_a_glued_tag_is_not_part_of_the_key(self):
        """E8-22: `file:line (tag)` joins to `file:line`."""
        self.assertEqual(ids.location_key(loc("src/widget.py:88 (legacy tag)")), "src/widget.py:88")
        self.assertEqual(ids.location_key(loc("src/widget.py:88(tag)")), "src/widget.py:88")

    def test_backticks_and_a_tag_together(self):
        self.assertEqual(ids.location_key(loc("`src/widget.py:88` (moved)")), "src/widget.py:88")

    def test_a_tag_glued_to_a_line_range_is_not_part_of_the_key(self):
        """F2: family L6 is a tag on a location "with backticks or a range"."""
        self.assertEqual(ids.location_key(loc("src/a.py:10 (wave 2)")), "src/a.py:10")
        self.assertEqual(ids.location_key(loc("`src/a.py:10-20` (wave 2)")), "src/a.py:10-20")
        self.assertEqual(ids.location_key(loc("src/a.py:10-20 (wave 2)")), "src/a.py:10-20")

    def test_an_en_dash_range_keeps_its_own_text(self):
        self.assertEqual(ids.location_key(loc("src/a.py:10\u201320 (wave 2)")), "src/a.py:10\u201320")

    def test_a_tagged_range_joins_to_the_untagged_one(self):
        """The whole point of E8-22: the recheck line omits the tag and must still join."""
        self.assertEqual(ids.location_key(loc("src/a.py:10-20 (wave 2)")),
                         ids.location_key(loc("src/a.py:10-20")))
        self.assertEqual(ids.finding_id(DOC, "A", loc("src/a.py:10-20 (wave 2)"), "c"),
                         ids.finding_id(DOC, "A", loc("src/a.py:10-20"), "c"))

    def test_a_field_naming_several_locations_drops_a_tag_from_each_of_them(self):
        """Amendment A8 (the outside review's finding 6): section 7 removes a glued tag without
        narrowing the rule to a field that names one location, so slice 1's exception is gone.
        The separators and the location spellings stay in the key; the tags do not."""
        for raw in ("src/widget.py:12, :40 and src/gauge.py:7",
                    "src/widget.py:12, :40 and src/gauge.py:7 (wave 2)",
                    "src/widget.py:12; src/gauge.py:7 (wave 2)",
                    "src/widget.py:12 + src/gauge.py:7 (wave 2)"):
            self.assertEqual(ids.location_key(loc(raw)), raw.replace(" (wave 2)", ""), raw)

    def test_a_tag_on_each_location_of_one_field_comes_off_both(self):
        self.assertEqual(ids.location_key(loc("src/a.py:1 (first), src/b.py:2 (second)")),
                         "src/a.py:1, src/b.py:2")

    def test_a_range_without_a_tag_is_untouched(self):
        self.assertEqual(ids.location_key(loc("src/a.py:10-20")), "src/a.py:10-20")
        self.assertEqual(ids.location_key(loc("`src/a.py:10-20`")), "src/a.py:10-20")

    def test_internal_whitespace_collapses(self):
        self.assertEqual(ids.location_key(loc("  the   parser   section  ")), "the parser section")

    def test_case_is_kept(self):
        self.assertEqual(ids.location_key(loc("src/Widget.py:88")), "src/Widget.py:88")
        self.assertNotEqual(ids.location_key(loc("src/Widget.py:88")), ids.location_key(loc("src/widget.py:88")))

    def test_a_parenthesis_in_an_unresolved_location_is_kept(self):
        """Only a parenthetical glued to a file:line is a legacy tag; prose keeps its own."""
        raw = "the migration notes (the second half)"
        self.assertEqual(ids.location_key(loc(raw)), raw)

    def test_a_line_range_stays_in_the_key(self):
        self.assertEqual(ids.location_key(loc("src/widget.py:120-133")), "src/widget.py:120-133")

    def test_several_locations_stay_in_the_key(self):
        raw = "src/widget.py:12, :40 and src/gauge.py:7"
        self.assertEqual(ids.location_key(loc(raw)), raw)

    def test_a_bare_string_is_accepted(self):
        self.assertEqual(ids.location_key("`src/widget.py:88`"), "src/widget.py:88")


class ClaimKey(unittest.TestCase):
    def test_wrapping_parentheses_are_not_part_of_the_claim(self):
        """E8-A28: a claim written in parentheses matches its recheck line."""
        self.assertEqual(ids.claim_key("(the loop never ends)"), "the loop never ends")

    def test_inner_parentheses_are_kept(self):
        self.assertEqual(ids.claim_key("the loop (the retry one) never ends"),
                         "the loop (the retry one) never ends")

    def test_no_claim_falls_back_to_the_scenario(self):
        self.assertEqual(ids.claim_key(None, "it spins forever"), "it spins forever")
        self.assertEqual(ids.claim_key("()", "it spins forever"), "it spins forever")

    def test_neither_is_the_empty_string(self):
        self.assertEqual(ids.claim_key(None, None), "")
        self.assertEqual(ids.claim_key("()", None), "")

    def test_whitespace_collapses(self):
        self.assertEqual(ids.claim_key("the   loop\tnever  ends"), "the loop never ends")


class FindingId(unittest.TestCase):
    def test_shape(self):
        value = ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop never ends")
        self.assertTrue(value.startswith("f1:"))
        self.assertEqual(len(value), len("f1:") + 20)
        self.assertTrue(ids.looks_like_id(value))

    def test_it_is_the_documented_hash(self):
        key = [DOC, "A", "src/widget.py:88", "the loop never ends"]
        expected = "f1:" + canon.sha256_hex(canon.canonical_json(key))[:20]
        self.assertEqual(ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop never ends"), expected)

    def test_the_tag_and_the_backticks_do_not_change_it(self):
        plain = ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop never ends")
        dressed = ids.finding_id(DOC, "A", loc("`src/widget.py:88` (tag)"), "(the loop never ends)")
        self.assertEqual(plain, dressed)

    def test_each_of_the_four_parts_changes_it(self):
        base = ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop never ends")
        self.assertNotEqual(base, ids.finding_id("docs/punch-list.md", "A", loc("src/widget.py:88"), "the loop never ends"))
        self.assertNotEqual(base, ids.finding_id(DOC, "B", loc("src/widget.py:88"), "the loop never ends"))
        self.assertNotEqual(base, ids.finding_id(DOC, "A", loc("src/widget.py:89"), "the loop never ends"))
        self.assertNotEqual(base, ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop ends late"))

    def test_a_missing_slice_is_none(self):
        self.assertEqual(ids.finding_id(DOC, None, loc("x.py:1"), "c"),
                         ids.finding_id(DOC, "none", loc("x.py:1"), "c"))

    def test_it_is_stable_across_runs(self):
        first = ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop never ends")
        second = ids.finding_id(DOC, "A", loc("src/widget.py:88"), "the loop never ends")
        self.assertEqual(first, second)

    def test_an_id_of_another_shape_is_not_an_id(self):
        for value in ("A-1", "f1:zzzz", "f1:" + "a" * 19, "", None, "f0:" + "a" * 20):
            self.assertFalse(ids.looks_like_id(value), value)

    def test_a_future_scheme_still_looks_like_an_id(self):
        self.assertTrue(ids.looks_like_id("f2:" + "a" * 20))


if __name__ == "__main__":
    unittest.main()
