"""E16 slice 5, the join, part J1b: the one machinery change the join asked for (its item 3, J1's Stop 3).

A line `move-line` moved under a heading, put back by its reverse between its saved neighbours (G19-14; rows-set T19 and
V08): where the saved neighbour on one side stood nowhere (the line was the file's last, or its first), the line goes back
right next to its saved neighbour on the other side, that neighbour found exactly once; the probe then reads the reverse's
own after-state. Every other placement is as before.

Every test's name carries the item, the row and the rule.
"""
import unittest

import harness  # noqa: F401  (it puts the scripts folder on the path, as every module of this suite needs under -I)
from sun_core import effects, engine as enginemod

OTHER = "- [Other](project_other.md): another project"
DEMO = "- [demo](project_demo.md): a disposable project"
HEAD = "# Memory"


def back(text, above, below):
    """V08's edit, as the restore's manifest holds it (its records' contents here as literals)."""
    edit = {"kind": "move-line", "holding": {"literal": "(project_demo.md)"}, "above": {"literal": above},
            "below": {"literal": below}}
    out = effects.edited(text.encode("utf-8"), edit, lambda mark: mark["literal"])
    return out.decode("utf-8") if out is not None else None


class MoveLineAtAnEdge(unittest.TestCase):
    def test_J1b_3_V08_EV6_a_line_that_was_the_files_last_goes_back_right_after_its_saved_line_above(self):
        archived = "\n".join([HEAD, OTHER, "## Archived", DEMO]) + "\n"
        self.assertEqual(back(archived, OTHER, enginemod.EDGE_END), "\n".join([HEAD, OTHER, DEMO, "## Archived"]) + "\n")

    def test_J1b_3_V08_EV6_a_line_that_was_the_files_first_goes_back_right_before_its_saved_line_below(self):
        archived = "\n".join([OTHER, "## Archived", DEMO]) + "\n"
        self.assertEqual(back(archived, enginemod.EDGE_START, OTHER), "\n".join([DEMO, OTHER, "## Archived"]) + "\n")

    def test_J1b_3_V08_EV6_the_saved_neighbour_on_the_other_side_found_twice_or_not_at_all_is_no_placement(self):
        twice = "\n".join([HEAD, OTHER, OTHER, "## Archived", DEMO]) + "\n"
        self.assertIsNone(back(twice, OTHER, enginemod.EDGE_END))
        gone = "\n".join([HEAD, "## Archived", DEMO]) + "\n"
        self.assertIsNone(back(gone, OTHER, enginemod.EDGE_END))

    def test_J1b_3_V08_EV6_a_line_between_two_saved_neighbours_goes_back_between_them_as_before(self):
        archived = "\n".join([HEAD, OTHER, "## Archived", DEMO]) + "\n"
        self.assertEqual(back(archived, HEAD, OTHER), "\n".join([HEAD, DEMO, OTHER, "## Archived"]) + "\n")


class MoveLineAtTheEndThroughARestore(harness.Case):
    def test_J1e_J4_V08_EV6_OP5_a_line_he_adds_at_the_end_after_the_restores_look_stops_V08_and_is_kept(self):
        """The reviewer's J4, her `edge-after-look` case, through a complete sunset and restore: the memory index's project
        line was its file's last; after the restore's look, and after V07, he adds a line at the end. V08-1's probe finds
        the file in neither state its reverse names (its tracked state, OP-5), and the restore stops `foreign` there: V08-1
        given no status, his line kept. The guard J1b's edge branch relies on, tested where it stands."""
        import test_lane_set_lib as lib
        m = lib.machine(self, "edge")
        m.put("mem/home/MEMORY.md", "# Memory\n- [Other](project_other.md) other\n- [Demo](project_demo_notes.md) the demo\n")
        lib.run(self, m)
        looked = lib.look(m, "restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        path = m.path("mem", "home", "MEMORY.md")
        planted = []

        def hook(e):
            if not planted and e["stage"] == "post" and e["op"] == "journal" and e.get("operation") == "V07" and e["subject"] == "completion":
                with open(path, "a") as fh:
                    fh.write("A LINE HE ADDED AT THE END\n")
                planted.append(True)
            return False
        went = lib.go(m, looked, "restore", kill=hook)
        self.assertTrue(planted)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertIn("V08-1", went.text)
        self.assertNotIn("V08-1", m.statuses(looked.doc["run"]))
        self.assertTrue(lib.read(m, "mem", "home", "MEMORY.md").endswith("A LINE HE ADDED AT THE END\n"))


if __name__ == "__main__":
    unittest.main()
