"""The shared files are equal in the four front cores (ruling E14-3, reading CR-4).

`references/shared-files.txt` (itself shared) lists every shared path relative to the plugin
root, `{core}` standing for the core's own name. Each listed file is hashed and compared with the
`precon-v2` copy found through the checkout layout: this plugin root's parent (`plugins/`), then
`precon-v2/`. In the installed shape there is no such sibling, and the comparison is reported as
skipped with that reason, never as passed.
"""
import hashlib
import os
import unittest

import testlib

LIST = os.path.join(testlib.REF, "shared-files.txt")
CANONICAL = "precon-v2"


def listed():
    rows = []
    with open(LIST, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append(line)
    return rows


def all_four_skip_reason(present):
    return "the checkout holds %s of the four cores" % (", ".join(present) or "none")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TheList(unittest.TestCase):

    def test_every_listed_file_exists_here(self):
        rows = listed()
        self.assertTrue(rows)
        self.assertEqual(len(rows), len(set(rows)), "a path is listed twice")
        for row in rows:
            path = os.path.join(testlib.PLUGIN, row.replace("{core}", testlib.CORE))
            self.assertTrue(os.path.isfile(path), row)

    def test_the_list_names_itself_and_the_contract(self):
        rows = listed()
        self.assertIn("skills/{core}/references/shared-files.txt", rows)
        self.assertIn("skills/{core}/references/station-loop.md", rows)

    def test_every_station_core_file_is_listed(self):
        rows = set(listed())
        folder = os.path.join(testlib.SCRIPTS, "station_core")
        for name in sorted(os.listdir(folder)):
            if name.endswith(".py"):
                self.assertIn("skills/{core}/scripts/station_core/%s" % name, rows, name)


class EqualToTheCanonicalCopy(unittest.TestCase):

    def setUp(self):
        self.canonical = testlib.checkout_sibling(CANONICAL)
        if self.canonical is None:
            self.skipTest("no %s beside this core (the installed shape): the shared files cannot "
                          "be compared here, and this is reported as skipped, not passed" % CANONICAL)

    def test_every_listed_file_is_byte_identical(self):
        different = []
        for row in listed():
            mine = os.path.join(testlib.PLUGIN, row.replace("{core}", testlib.CORE))
            theirs = os.path.join(self.canonical, row.replace("{core}", CANONICAL))
            if not os.path.isfile(theirs):
                different.append((row, "absent from %s" % CANONICAL))
            elif digest(mine) != digest(theirs):
                different.append((row, "differs"))
        self.assertEqual(different, [])

    def test_the_list_itself_is_the_canonical_list(self):
        theirs = os.path.join(self.canonical, "skills", CANONICAL, "references", "shared-files.txt")
        self.assertEqual(digest(LIST), digest(theirs))


class AllFourCores(unittest.TestCase):

    def test_the_other_cores_hold_the_same_files(self):
        present = [c for c in testlib.CORES if testlib.checkout_sibling(c) is not None]
        if len(present) < len(testlib.CORES):
            self.skipTest(all_four_skip_reason(present))
        rows = listed()
        for row in rows:
            digests = set()
            for core in testlib.CORES:
                path = os.path.join(testlib.checkout_sibling(core), row.replace("{core}", core))
                self.assertTrue(os.path.isfile(path), (core, row))
                digests.add(digest(path))
            self.assertEqual(len(digests), 1, row)



class TheSkipReason(unittest.TestCase):
    """C1-11 (the E14 slice 1 checker): the reason names the cores present, or `none`."""

    def test_no_core_present_reads_none(self):
        self.assertEqual(all_four_skip_reason([]), "the checkout holds none of the four cores")

    def test_the_cores_present_are_named(self):
        self.assertEqual(all_four_skip_reason(["precon-v2", "inspect-v2"]),
                         "the checkout holds precon-v2, inspect-v2 of the four cores")

if __name__ == "__main__":
    unittest.main()
