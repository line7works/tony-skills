"""The ledger reader (required test 6): every tag, every section, and an untaggable line.

`decided`, `assumed`, `parked` with each of its three reasons, the `Out of scope:`, `Research:`
and `Open:` sections, stable line ids, and a line the reader cannot tag refused with the line
quoted, never dropped or guessed.
"""
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import ledger  # noqa: E402

DOC = """# Widget \u2014 scope doc (2026-09-20)

Intent: a small widget that counts turns, for the owner's own bench tests.
Decisions:
- Python 3.9 standard library only \u2014 decided (the owner's words: "no dependencies")
- One module, no package \u2014 assumed (small and reversible)
- The storage format \u2014 parked: needs research
- A second counter mode \u2014 parked: needs prototype
- Export to the bench log \u2014 parked: waiting on the bench log's format
- Counts are integers \u2014 decided (Q2)
Out of scope: a web view \u2014 the owner declined it
Research: docs/research/turns.md
Open:
- how often the counter resets
- whether the widget names itself
Next: /blueprint when ready.
"""


class EveryTag(unittest.TestCase):

    def setUp(self):
        self.lines = ledger.read(DOC)
        self.by_tag = {}
        for row in self.lines:
            self.by_tag.setdefault(row["tag"], []).append(row)

    def test_the_tags_and_counts(self):
        self.assertEqual({tag: len(rows) for tag, rows in self.by_tag.items()},
                         {"decided": 2, "assumed": 1, "parked": 3, "out-of-scope": 1,
                          "research": 1, "open": 2})

    def test_decided_carries_its_source(self):
        first = self.by_tag["decided"][0]
        self.assertEqual(first["text"], "Python 3.9 standard library only")
        self.assertEqual(first["source"], 'the owner\'s words: "no dependencies"')
        self.assertEqual(first["section"], "Decisions")

    def test_assumed_carries_its_why(self):
        (row,) = self.by_tag["assumed"]
        self.assertEqual((row["text"], row["source"]), ("One module, no package", "small and reversible"))

    def test_parked_with_each_reason(self):
        reasons = [row["reason"] for row in self.by_tag["parked"]]
        self.assertEqual(reasons, ["needs research", "needs prototype", "waiting on"])
        self.assertEqual(self.by_tag["parked"][2]["source"], "waiting on the bench log's format")

    def test_the_other_sections(self):
        self.assertEqual(self.by_tag["out-of-scope"][0]["text"], "a web view \u2014 the owner declined it")
        self.assertEqual(self.by_tag["research"][0]["text"], "docs/research/turns.md")
        self.assertEqual([r["text"] for r in self.by_tag["open"]],
                         ["how often the counter resets", "whether the widget names itself"])

    def test_every_line_has_a_line_number_and_its_raw_text(self):
        raw = DOC.split("\n")
        for row in self.lines:
            self.assertIn(row["raw"], raw[row["line"] - 1])

    def test_ids_are_stable_and_unique(self):
        ids = [row["id"] for row in self.lines]
        self.assertEqual(len(ids), len(set(ids)))
        appended = DOC.replace("Out of scope:", "- appended at the tail \u2014 decided (Q9)\nOut of scope:")
        again = {row["text"]: row["id"] for row in ledger.read(appended)}
        for row in self.lines:
            self.assertEqual(again[row["text"]], row["id"])

    def test_an_id_survives_a_line_added_above_it(self):
        moved = DOC.replace("Decisions:\n", "Decisions:\n- A new first line \u2014 decided (Q1)\n")
        before = {row["text"]: row["id"] for row in self.lines}
        after = {row["text"]: row["id"] for row in ledger.read(moved)}
        for text, ident in before.items():
            self.assertEqual(after[text], ident, text)

    def test_the_id_follows_the_item_not_its_tag(self):
        settled = DOC.replace("The storage format \u2014 parked: needs research",
                              "The storage format \u2014 decided (Q4)")
        before = [r for r in self.lines if r["text"] == "The storage format"][0]
        after = [r for r in ledger.read(settled) if r["text"] == "The storage format"][0]
        self.assertEqual(before["id"], after["id"])
        self.assertEqual((before["tag"], after["tag"]), ("parked", "decided"))

    def test_crlf_reads_the_same(self):
        crlf = ledger.read(DOC.replace("\n", "\r\n"))
        self.assertEqual([(r["id"], r["tag"], r["text"]) for r in crlf],
                         [(r["id"], r["tag"], r["text"]) for r in self.lines])


class Untaggable(unittest.TestCase):

    def refused(self, doc):
        with self.assertRaises(ledger.LedgerRefused) as ctx:
            ledger.read(doc)
        return ctx.exception

    def test_a_decisions_line_with_no_tag(self):
        exc = self.refused(DOC.replace("- Counts are integers \u2014 decided (Q2)",
                                       "- Counts are integers, probably"))
        self.assertEqual(len(exc.lines), 1)
        self.assertEqual(exc.lines[0]["raw"], "- Counts are integers, probably")
        self.assertIn("- Counts are integers, probably", str(exc))

    def test_a_parked_line_with_another_reason(self):
        exc = self.refused(DOC.replace("parked: needs prototype", "parked: later"))
        self.assertIn("parked: later", str(exc))

    def test_a_decided_line_with_an_empty_source(self):
        self.refused(DOC.replace("decided (Q2)", "decided ()"))

    def test_a_line_that_is_not_a_list_item(self):
        self.refused(DOC.replace("- One module, no package", "One module, no package"))

    def test_every_untaggable_line_is_listed_not_only_the_first(self):
        doc = DOC.replace("decided (Q2)", "maybe").replace("parked: needs prototype", "parked: soon")
        exc = self.refused(doc)
        self.assertEqual(len(exc.lines), 2)

    def test_a_doc_with_no_decisions_label(self):
        self.refused(DOC.replace("Decisions:\n", "Decision:\n"))


    # C1-8 (the E14 slice 1 checker): a list line under a section below `Decisions:` that ends in a
    # Decisions tag is a Decisions line out of place, refused with the line quoted, never read as
    # an item of that section carrying the tag text.
    def test_a_decisions_line_under_out_of_scope(self):
        doc = DOC.replace("Out of scope: a web view \u2014 the owner declined it\n",
                          "Out of scope:\n- a web view \u2014 decided (Q1)\n")
        exc = self.refused(doc)
        self.assertEqual([row["raw"] for row in exc.lines], ["- a web view \u2014 decided (Q1)"])
        self.assertIn("a Decisions line below the Decisions block", exc.lines[0]["why"])
        self.assertIn("- a web view \u2014 decided (Q1)", str(exc))

    def test_a_decisions_line_under_open(self):
        for tail in ("decided (Q1)", "assumed (small)", "parked: needs research"):
            doc = DOC.replace("- whether the widget names itself\n",
                              "- whether the widget names itself \u2014 %s\n" % tail)
            exc = self.refused(doc)
            self.assertEqual([row["raw"] for row in exc.lines],
                             ["- whether the widget names itself \u2014 %s" % tail], tail)
            self.assertIn("a Decisions line below the Decisions block", exc.lines[0]["why"])

    def test_the_clean_shape_under_those_sections_is_still_read(self):
        doc = DOC.replace("Out of scope: a web view \u2014 the owner declined it\n",
                          "Out of scope:\n- a web view \u2014 the owner declined it\n- a decided look\n")
        rows = ledger.read(doc)
        self.assertEqual([r["text"] for r in rows if r["tag"] == "out-of-scope"],
                         ["a web view \u2014 the owner declined it", "a decided look"])
        self.assertEqual([r["text"] for r in rows if r["tag"] == "open"],
                         ["how often the counter resets", "whether the widget names itself"])


    # Finding 1 of the reviewer's short look (round 3): a heading met while a ledger section is
    # open is refused with the line quoted, never a silent end of the section that drops the
    # lines after it.
    def test_a_heading_inside_decisions_is_refused_and_quoted(self):
        doc = "Decisions:\n### note\n- Python only \u2014 decided (Q1)\nOut of scope:\nResearch:\nOpen:\n"
        exc = self.refused(doc)
        self.assertEqual([(row["line"], row["raw"]) for row in exc.lines], [(2, "### note")])
        self.assertEqual(exc.lines[0]["why"], "an unexpected heading inside Decisions")
        self.assertIn("'### note'", str(exc))

    def test_a_heading_inside_each_other_section_is_refused(self):
        for label, anchor in (("Out of scope", "Out of scope: a web view \u2014 the owner declined it\n"),
                              ("Research", "Research: docs/research/turns.md\n"),
                              ("Open", "Open:\n")):
            doc = DOC.replace(anchor, anchor + "## Aside\n")
            exc = self.refused(doc)
            self.assertEqual([row["raw"] for row in exc.lines], ["## Aside"], label)
            self.assertEqual(exc.lines[0]["why"], "an unexpected heading inside %s" % label)

    def test_a_heading_between_sections_is_still_read(self):
        before = [(r["id"], r["tag"], r["text"]) for r in ledger.read(DOC)]
        for doc in (DOC.replace("Decisions:\n", "### note\nDecisions:\n"),
                    DOC + "## Notes\n- not a ledger line\n"):
            self.assertEqual([(r["id"], r["tag"], r["text"]) for r in ledger.read(doc)], before)


class Empty(unittest.TestCase):

    def test_bare_labels_hold_no_item(self):
        doc = ("# W \u2014 scope doc (2026-09-20)\n\nIntent: x\nDecisions:\nOut of scope:\n"
               "Research:\nOpen:\nNext: /blueprint when ready.\n")
        self.assertEqual(ledger.read(doc), [])

    def test_counts(self):
        counts = ledger.counts(ledger.read(DOC))
        self.assertEqual(counts, {"decided": 2, "assumed": 1, "parked": 3, "out-of-scope": 1,
                                  "research": 1, "open": 2})


if __name__ == "__main__":
    unittest.main()
