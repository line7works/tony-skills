"""The next move (CR-14), resolved by script from the record, on the three shapes: a clean boundary and exactly one
next slice gives the kickoff `/ship-v2 <slice> <doc>` and states `/build-v2` once; an open card gives the fix list
then `/recheck-v2`; a complete loop gives no kickoff line. Never a `/ship-v2` of a slice that does not exist. Then
`report`: the `HANDOFF:` block from the result, closing with the safe-to-clear line.
"""
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import nextmove  # noqa: E402

DOC = hlib.DOC


def row(name, card, depends=(), open_=()):
    return {"name": name, "card": card, "depends": list(depends), "open": list(open_)}


class TheResolution(unittest.TestCase):

    def resolve(self, slices, finished=None, owner=None):
        return nextmove.resolve(slices, DOC, finished=finished, owner=owner)

    def test_a_clean_boundary(self):
        move = self.resolve([row("A", "signed off"), row("B", "not started", ["A"])], finished="A")
        self.assertEqual((move["shape"], move["slice"]), ("clean-boundary", "B"))

    def test_an_open_card(self):
        finding = {"id": "f1:aaaaaaaaaaaaaaaaaaaa", "slice": "A", "severity": "MAJOR", "location": "x.py:2",
                   "claim": "c"}
        move = self.resolve([row("A", "signed off with conditions", open_=[finding]), row("B", "not started", ["A"])])
        self.assertEqual(move["shape"], "open-card")
        self.assertEqual(move["recheck"], ["A"])
        self.assertEqual([f["location"] for f in move["fix_list"]], ["x.py:2"])

    def test_an_open_major_behind_a_signed_card_is_an_open_card(self):
        finding = {"id": "f1:aaaaaaaaaaaaaaaaaaaa", "slice": "A", "severity": "MAJOR", "location": "x.py:2",
                   "claim": "c"}
        move = self.resolve([row("A", "signed off", open_=[finding]), row("B", "not started", ["A"])])
        self.assertEqual(move["shape"], "open-card")

    def test_an_open_minor_alone_leaves_the_boundary_clean(self):
        finding = {"id": "f1:aaaaaaaaaaaaaaaaaaaa", "slice": "A", "severity": "MINOR", "location": "x.py:2",
                   "claim": "c"}
        move = self.resolve([row("A", "signed off", open_=[finding]), row("B", "not started", ["A"])])
        self.assertEqual(move["shape"], "clean-boundary")

    def test_a_complete_loop(self):
        move = self.resolve([row("A", "signed off"), row("B", "signed off", ["A"])])
        self.assertEqual(move["shape"], "loop-complete")
        self.assertIsNone(move.get("slice"))

    def test_an_ambiguity_with_no_owner_answer_resolves_to_nothing(self):
        move = self.resolve([row("A", "signed off"), row("B", "not started"), row("C", "not started")])
        self.assertEqual(move["shape"], "unresolved")
        self.assertEqual(move["candidates"], ["B", "C"])

    def test_the_owners_answer_resolves_an_ambiguity(self):
        move = self.resolve([row("A", "signed off"), row("B", "not started"), row("C", "not started")],
                            owner={"slice": "C", "words": "C first"})
        self.assertEqual((move["shape"], move["slice"]), ("clean-boundary", "C"))
        move = self.resolve([row("A", "signed off"), row("B", "not started"), row("C", "not started")],
                            owner={"slice": None, "words": "hold, I will decide"})
        self.assertEqual(move["shape"], "owner-holds")

    def test_never_a_slice_that_does_not_exist(self):
        with self.assertRaises(ValueError):
            self.resolve([row("A", "signed off"), row("B", "not started")], owner={"slice": "Z", "words": "Z"})


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheShapesThroughTheCLI(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-next-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def full(self, text, records=False):
        ws, _ = hlib.make_repo(self.tmp, text, records=records)
        drive, run_dir = hlib.start(self.tmp, ws)
        gate, written = hlib.through_write(self, drive, self.tmp, run_dir, perishables=["a seam note"])
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line",
                                "The record is captured. Type the next line after clearing."])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "completed")
        return ws, written, out

    def test_the_clean_boundary_kickoff_names_ship_v2_and_the_doc(self):
        ws, written, out = self.full(hlib.build_doc())
        move = out["station_result"]["next_move"]
        self.assertEqual(move["shape"], "clean-boundary")
        self.assertEqual(move["kickoff"], "/ship-v2 B %s" % DOC)
        self.assertEqual(move["alternative"], "/build-v2 B %s" % DOC)
        chat = out["station_result"]["chat"]
        self.assertIn("Next: /ship-v2 B %s" % DOC, chat)
        self.assertTrue(chat.endswith("Thread is safe to clear.\n"))
        self.assertIn("- Next: /ship-v2 B %s" % DOC, hlib.read_doc(ws))

    def test_the_open_card_is_the_fix_list_then_recheck_v2(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A")], punch=hlib.review_block())
        ws, written, out = self.full(text, records=True)
        move = out["station_result"]["next_move"]
        self.assertEqual(move["shape"], "open-card")
        self.assertIsNone(move["kickoff"])
        chat = out["station_result"]["chat"]
        self.assertIn("/recheck-v2 A %s" % DOC, chat)
        self.assertNotIn("/ship-v2", chat)
        self.assertIn("Open: MAJOR", chat)

    def test_the_complete_loop_has_no_kickoff_line(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing"),
                                      ("B", "the spinner", "signed off", "Slice A")])
        ws, written, out = self.full(text)
        move = out["station_result"]["next_move"]
        self.assertEqual(move["shape"], "loop-complete")
        self.assertIsNone(move["kickoff"])
        self.assertNotIn("/ship", out["station_result"]["chat"])
        self.assertNotIn("/ship", hlib.read_doc(ws).split(hlib.HEADING % hlib.TODAY)[1])


if __name__ == "__main__":
    unittest.main()
