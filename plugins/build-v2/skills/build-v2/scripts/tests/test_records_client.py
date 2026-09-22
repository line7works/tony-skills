"""The records wiring is copied, not reinvented (E13-3; lane B brief, "The pattern").

Three things this suite holds:

1. `build_core/records_client.py` is the pilot's `recheck_core/records_client.py` byte for byte
   below a header that names its origin and the commit it was taken from. A divergence in
   either direction fails here, which is the same shape the records component uses for its own
   copied region (`plugins/records/scripts/tests/test_parity.py`).
2. The copy's pilot-owned constants are never this station's: `build_core/records_link.py`
   carries `build-v2` as the station and its own test hook name.
3. The component-identity check: a component that speaks interface version 2, and a component
   that is not there at all, each exit 3 with empty stdout and one line on stderr.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from build_core import records_client as rcl, records_link  # noqa: E402

HEADER_END = '"""Reaching the records component'


class TheCopyIsThePilotsFile(unittest.TestCase):

    def setUp(self):
        with open(testlib.pilot_records_client(), encoding="utf-8") as fh:
            self.original = fh.read()
        with open(os.path.join(testlib.SCRIPTS, "build_core", "records_client.py"),
                  encoding="utf-8") as fh:
            self.mine = fh.read()

    def test_the_copied_region_is_the_pilot_file_byte_for_byte(self):
        start = self.mine.index(HEADER_END)
        self.assertEqual(self.mine[start:], self.original,
                         "build_core/records_client.py has diverged from the pilot's "
                         "recheck_core/records_client.py")

    def test_the_header_names_its_origin_and_the_commit(self):
        head = self.mine[:self.mine.index(HEADER_END)]
        self.assertIn("recheck_core/records_client.py", head)
        self.assertIn("a80cdd04432c5f4662ed415d6a72d54f9b8208c1", head)

    def test_the_header_is_comment_lines_only(self):
        head = self.mine[:self.mine.index(HEADER_END)]
        for line in head.split("\n"):
            if line.strip():
                self.assertTrue(line.startswith("#"), line)

    def test_the_stations_own_name_is_not_in_the_copy(self):
        self.assertEqual(rcl.STATION, "recheck-v2")
        self.assertEqual(records_link.STATION, "build-v2")
        self.assertNotEqual(records_link.NO_RECORDS_HOOK, rcl.NO_RECORDS_HOOK)

    def test_nothing_in_this_station_reads_the_copys_station_constant(self):
        """The pilot's STATION and its hook name are in the file only so the bytes match."""
        offenders = []
        for base, dirs, files in os.walk(testlib.SKILL):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
            for name in files:
                if not name.endswith(".py") or name == "records_client.py":
                    continue
                with open(os.path.join(base, name), encoding="utf-8") as fh:
                    text = fh.read()
                for needle in ("rcl.STATION", "records_client.STATION",
                               "rcl.NO_RECORDS_HOOK", "records_client.NO_RECORDS_HOOK"):
                    if needle in text:
                        offenders.append((os.path.join(base, name), needle))
        self.assertEqual(offenders, [])


class TheStationPluginRootIsThisPlugin(unittest.TestCase):

    def test_route_3a_resolves_to_the_sibling_records_folder(self):
        root = rcl.station_plugin_root()
        self.assertEqual(os.path.realpath(root), os.path.realpath(testlib.PLUGIN))

    def test_the_client_opens_against_the_checkout(self):
        client = records_link.open_client()
        self.assertEqual(client.interface_version, 1)
        self.assertEqual(os.path.realpath(client.root), os.path.realpath(testlib.RECORDS_ROOT))


class TheComponentIdentityCheck(unittest.TestCase):
    """Exit 3, empty stdout, one line on stderr, for both refusals."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-identity-")
        self.addCleanup(testlib.rmtree, self.scratch)

    def test_a_component_at_another_interface_version_is_refused(self):
        """A real copy of the component with `INTERFACE_VERSION = 2`, not a stand-in."""
        root = testlib.fake_component(self.scratch, interface_version=2)
        with open(os.path.join(root, "scripts", "records.py"), encoding="utf-8") as fh:
            self.assertIn("\nINTERFACE_VERSION = 2\n", fh.read())
        code, out, err = testlib.run_build(["skill-identity", "--records-root", root])
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().split("\n")), 1, err)
        self.assertIn("speaks interface version 2, not 1", err)

    def test_a_component_that_reports_no_interface_version_is_refused(self):
        root = os.path.join(self.scratch, "silent")
        os.makedirs(os.path.join(root, "scripts"))
        with open(os.path.join(root, "scripts", "records.py"), "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env python3\nprint('not json')\n")
        code, out, err = testlib.run_build(["skill-identity", "--records-root", root])
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertIn("did not report an interface version", err)

    def test_a_missing_component_is_refused_and_names_where_it_looked(self):
        env = testlib.base_env({records_link.NO_RECORDS_HOOK: "1", "BUILD_TEST": "1"})
        code, out, err = testlib.run_build(["skill-identity"], env=env)
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().split("\n")), 1, err)
        self.assertIn("missing dependency: records component", err)
        self.assertIn("looked in", err)

    def test_the_hook_is_ignored_without_the_test_flag(self):
        env = testlib.base_env({records_link.NO_RECORDS_HOOK: "1"})
        code, out, err = testlib.run_build(["skill-identity"], env=env)
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
