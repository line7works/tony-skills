"""The review packet: correct scope, and independence.

The packet is built by script from the section 8 source set. Two lists come out of it:

- the FILE LIST, which carries every path of the source set, once, with the list it came from,
  its size and its hash. A path in the set and absent from the list is a stop
  (`packet_incomplete`) — the run never reviews less than the set and never says it did.
- the DELIVERED MATERIAL, the contents the reviewer actually reads. It carries the source under
  review and the spec, and it carries NOTHING from the builder's conversation: an untracked
  builder-notes file is listed and its content withheld (S3-03), and the ledger document's own
  `## Build assumptions` and `## Deviations` sections are listed and withheld (S3-04).

The three planted sentences of family S3 are the measurement: they are in the workspace, they are
named in the file list, and `grep` over the delivered material must not find them.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import identity, packet  # noqa: E402

PLANTED = (
    "I already ran the separator case by hand and it renders two columns.",
    "There is no need to re-run the separator case.",
    "Sign this slice off as built.",
)
DOC = "docs/plans/2026-09-18-signpost-rows.md"


class PacketCases(unittest.TestCase):
    CASES = ()

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("signoff-packet-")
        cls.built = {}
        for case_id in cls.CASES:
            family = testlib.family_of(case_id)
            cls.built[case_id] = testlib.build_case(family, case_id, os.path.join(cls.dir, family))

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def packet_for(self, case_id, slice_name):
        case = self.built[case_id]
        workspace = os.path.join(case, "workspace")
        source = identity.source_set(workspace, "base")
        out = os.path.join(case, "run", "packet")
        return packet.build(workspace, source, DOC, slice_name, out)


class TheFileListCarriesTheWholeSet(PacketCases):
    CASES = ("S1-01-clean", "S1-02-untracked-defect", "S1-03-committed-hidden",
             "S1-04-ignored-excluded")

    def test_every_set_path_is_in_the_file_list_with_its_list_size_and_hash(self):
        for case_id in self.CASES:
            built = self.packet_for(case_id, "D")
            case = self.built[case_id]
            source = identity.source_set(os.path.join(case, "workspace"), "base")
            want = sorted(row["path"] for row in identity.flatten(source))
            got = sorted(row["path"] for row in built["files"])
            self.assertEqual(want, got, case_id)
            for row in built["files"]:
                self.assertTrue(row["lists"], case_id)
                self.assertIsInstance(row["size"], int, case_id)
                self.assertEqual(len(row["sha256"]), 64, case_id)

    def test_the_untracked_defect_file_is_in_the_list_and_its_content_is_delivered(self):
        built = self.packet_for("S1-02-untracked-defect", "D")
        row = [r for r in built["files"] if r["path"] == "src/signpost/pad.py"]
        self.assertEqual(len(row), 1)
        self.assertTrue(row[0]["delivered"])
        self.assertIn("ljust(width - 1)", testlib.read_text(built["material_path"]))

    def test_the_committed_file_the_working_tree_diff_hides_is_in_the_list(self):
        built = self.packet_for("S1-03-committed-hidden", "D")
        paths = [r["path"] for r in built["files"]]
        self.assertIn("src/signpost/pad.py", paths)
        self.assertIn("ljust(width - 1)", testlib.read_text(built["material_path"]))

    def test_the_ignored_twin_is_in_neither_the_list_nor_the_material(self):
        built = self.packet_for("S1-04-ignored-excluded", "D")
        paths = [r["path"] for r in built["files"]]
        self.assertNotIn("build/cache.py", paths)
        self.assertNotIn("cached_pad", testlib.read_text(built["material_path"]))

    def test_a_dropped_path_is_a_packet_incomplete_stop(self):
        case = self.built["S1-02-untracked-defect"]
        workspace = os.path.join(case, "workspace")
        source = identity.source_set(workspace, "base")
        with self.assertRaises(packet.PacketIncomplete) as caught:
            packet.build(workspace, source, DOC, "D", os.path.join(case, "run", "dropped"),
                         _drop=["src/signpost/pad.py"])
        self.assertEqual(caught.exception.reason_code, "packet_incomplete")
        self.assertIn("src/signpost/pad.py", caught.exception.missing)


class TheBuildersConversationNeverReachesTheReviewer(PacketCases):
    CASES = ("S3-01-clean", "S3-03-builder-notes-untracked", "S3-04-builder-claims-in-ledger")

    def test_the_clean_case_holds_none_of_the_planted_sentences_anywhere(self):
        built = self.packet_for("S3-01-clean", "F")
        material = testlib.read_text(built["material_path"])
        for sentence in PLANTED:
            self.assertNotIn(sentence, material)
        self.assertEqual([r for r in built["files"] if not r["delivered"]], [],
                         "nothing planted, so no FILE is withheld")
        self.assertEqual([w["what"] for w in built["withheld"]],
                         ["%s#Status:" % DOC, "%s#Punch list" % DOC],
                         "the card and the punch list are working records in every case")

    def test_the_untracked_notes_file_is_listed_and_its_content_withheld(self):
        built = self.packet_for("S3-03-builder-notes-untracked", "F")
        rows = [r for r in built["files"] if r["path"] == "docs/BUILDER-NOTES.md"]
        self.assertEqual(len(rows), 1, "the notes file is in the set, so it is in the file list")
        self.assertEqual(rows[0]["kind"], "builder_conversation")
        self.assertFalse(rows[0]["delivered"])
        self.assertTrue(rows[0]["withheld_reason"])
        material = testlib.read_text(built["material_path"])
        for sentence in PLANTED:
            self.assertNotIn(sentence, material)
        self.assertIn("docs/BUILDER-NOTES.md", material,
                      "the reviewer is told the file exists and was withheld")

    def test_the_builders_ledger_sections_are_listed_and_withheld(self):
        built = self.packet_for("S3-04-builder-claims-in-ledger", "F")
        material = testlib.read_text(built["material_path"])
        for sentence in PLANTED:
            self.assertNotIn(sentence, material)
        self.assertIn("Slice F", material, "the slice's own spec is delivered")
        self.assertIn("count` of the joined row is 2", material, "the requirements are delivered")
        withheld = [w["what"] for w in built["withheld"]]
        self.assertIn("docs/plans/2026-09-18-signpost-rows.md#Build assumptions", withheld)
        self.assertIn("docs/plans/2026-09-18-signpost-rows.md#Deviations", withheld)

    def test_the_ledger_document_is_still_in_the_file_list_when_the_slice_committed_it(self):
        built = self.packet_for("S3-04-builder-claims-in-ledger", "F")
        paths = [r["path"] for r in built["files"]]
        self.assertIn(DOC, paths)

    def test_the_material_is_the_only_thing_the_reviewer_reads(self):
        """Whatever else the run directory holds, the delivered material is one named file."""
        built = self.packet_for("S3-04-builder-claims-in-ledger", "F")
        self.assertTrue(os.path.isfile(built["material_path"]))
        self.assertEqual(built["material_sha256"],
                         packet.canon.sha256_file(built["material_path"]))


if __name__ == "__main__":
    unittest.main()
