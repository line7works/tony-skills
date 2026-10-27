"""E18 fix round 1, Slice B: the provenance check reads the whole delivered packet.

`signoff.py` `provenance_of` read the delivered packet through `packet.read_text_or_none`, which
stops at `MAX_DELIVERED_BYTES` (512 KiB, the cap on what a packet delivers per file). A packet
larger than that was cut, so a reviewer quoting the back of the packet was refused on independence
as if the words came only from the builder's withheld notes. The cap on each delivered file stays;
only the provenance check's read of the assembled material is whole. A quotation found only in
withheld text is still refused, however large the packet.

The end-to-end cases plant files in the S1-02 seeded case and drive the real `signoff.py`; the
direct cases call `provenance_of` on a packet description. They were written red first.
"""
import json
import os
import unittest

import testlib
from test_fix2_astra import _Case

testlib.add_scripts_to_path()

import signoff  # noqa: E402
from signoff_core import packet as packetmod  # noqa: E402

CAP = packetmod.MAX_DELIVERED_BYTES
LATE = "The late separator sentence held in every run."
PRIVATE = "My own private run of the separator passed."
NOTES = "notes.md"


def padding(size):
    """ASCII lines with no quotation marks, `size` bytes long."""
    line = "pad line for the packet size check, nothing to review here\n"
    text = line * (size // len(line) + 1)
    return text[:size]


class _Large(_Case):
    """The S1-02 case with a delivered packet well over the per-file cap: one file over the cap
    (delivered truncated), one under it, and a short file whose sentence lands past the cap's
    offset in the assembled material. The builder's notes repeat that sentence."""

    def plant(self):
        self.write(NOTES, "# Builder notes\n\n%s\n%s\n" % (LATE, PRIVATE))
        self.write("big/pad-a.txt", padding(CAP + 64 * 1024))
        self.write("big/pad-b.txt", padding(200 * 1024))
        self.write("big/zz-late.txt", "The closing line follows.\n%s\n" % LATE)

    def material(self):
        packet = testlib.load_json(os.path.join(self.run_dir, "packet", "packet.json"))
        return packet, testlib.read_text(packet["material_path"])

    def quoting(self, sentence):
        answer = self.answer()
        answer["notes"] = 'The packet closes with "%s" at its very end.' % sentence.rstrip(".")
        return answer

    def assert_large_packet(self):
        packet, material = self.material()
        rows = dict((row["path"], row) for row in packet["files"])
        self.assertEqual((rows[NOTES]["kind"], rows[NOTES]["delivered"]),
                         ("builder_conversation", False), json.dumps(rows[NOTES]))
        self.assertTrue(rows["big/zz-late.txt"]["delivered"])
        self.assertNotIn(PRIVATE, material, "the builder's notes are never delivered")
        offset = len(material.encode("utf-8")[:material.rfind(LATE)])
        self.assertGreater(offset, CAP, "the quotation sits past the cap in the material")
        # The cap on what a packet delivers per file does not change.
        self.assertIn("<!-- truncated at %d bytes -->" % CAP, material)


class ALateQuotationTracesToTheDeliveredText(_Large):
    """Requirement 1: a quotation anywhere in the delivered packet traces to it."""

    def test_the_answer_is_recorded_not_refused(self):
        self.plant()
        code, doc, err = self.through_answer(self.quoting(LATE))
        self.assertEqual(code, 0, err or json.dumps(doc))
        self.assert_large_packet()
        code, doc, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(doc))
        result = self.result()
        self.assertNotEqual(result.get("refusal_reason"), "independence", json.dumps(result)[:1200])
        self.assertTrue(result["verdict_recorded"], json.dumps(result)[:1200])


class AWithheldOnlyQuotationIsStillRefused(_Large):
    """Requirement 2: words found only in withheld text are refused, whatever the packet's size."""

    def test_independence_refuses_it(self):
        self.plant()
        code, doc, err = self.through_answer(self.quoting(PRIVATE))
        self.assertEqual(code, 10, err or json.dumps(doc))
        self.assert_large_packet()
        result = self.result()
        self.assertEqual(result["refusal_reason"], "independence", json.dumps(result)[:1200])
        self.assertFalse(result["verdict_recorded"])


class ProvenanceOfReadsTheWholeMaterial(unittest.TestCase):
    """Requirement 1 at the function: the whole material, with the same refusals for a binary or
    non-UTF-8 file, while the packet's own reader keeps its cap."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-fr1b-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.workspace = os.path.join(self.dir, "workspace")
        os.makedirs(self.workspace)
        self.material_path = os.path.join(self.dir, "material.md")

    def provenance(self, raw):
        with open(self.material_path, "wb") as fh:
            fh.write(raw)
        built = {"files": [], "withheld": [], "ledger_doc": "docs/plan.md",
                 "material_path": self.material_path}
        return signoff.provenance_of(self.workspace, built)

    def test_a_material_over_the_cap_is_read_in_full(self):
        raw = (padding(2 * CAP) + LATE + "\n").encode("utf-8")
        got = self.provenance(raw)
        self.assertEqual(got["delivered_text"], raw.decode("utf-8"))
        self.assertTrue(got["delivered_text"].endswith(LATE + "\n"))

    def test_a_multibyte_character_across_the_cap_is_still_text(self):
        raw = (padding(CAP - 1) + "é" + padding(1024) + LATE).encode("utf-8")
        self.assertEqual(self.provenance(raw)["delivered_text"], raw.decode("utf-8"))

    def test_a_binary_material_is_still_refused(self):
        raw = padding(2 * CAP).encode("utf-8") + b"\0" + LATE.encode("utf-8")
        self.assertEqual(self.provenance(raw)["delivered_text"], "")

    def test_a_non_utf8_material_is_still_refused(self):
        raw = padding(2 * CAP).encode("utf-8") + b"\xff\xfe" + LATE.encode("utf-8")
        self.assertEqual(self.provenance(raw)["delivered_text"], "")

    def test_the_packet_reader_keeps_its_cap(self):
        path = os.path.join(self.dir, "big.txt")
        with open(path, "wb") as fh:
            fh.write(padding(2 * CAP).encode("utf-8"))
        self.assertEqual(len(packetmod.read_text_or_none(path).encode("utf-8")), CAP + 1)


if __name__ == "__main__":
    unittest.main()
