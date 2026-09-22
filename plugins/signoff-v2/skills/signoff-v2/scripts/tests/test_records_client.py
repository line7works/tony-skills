"""Reaching the records component (E13 slice 2 lane S; records interface version 1).

The wiring is COPIED, not reinvented (brief, "The pattern"): `signoff_core/records_client.py` is
`recheck_core/records_client.py` byte for byte, and `TheCopyIsExact` fails the moment the two
files differ, the way the records component holds its own copied region in step with the pilot
(`plugins/records/scripts/tests/test_parity.py`).

Because the copy is exact, its module constants are the pilot's — `STATION` reads `recheck-v2`
and the test hook is named `RECHECK_TEST_NO_RECORDS`. This station never reads either: its own
station name lives in `signoff_core.constants`, and a test that wants a missing component points
the resolver at a station root with nothing beside it, which is the real failure rather than a
hook. `TheCopyIsNeverReadForThisStationsName` holds that line.

The refusals proved here are the brief's two: a component speaking interface version 2, and no
component at all. Both are exit 3 with empty stdout and one line on stderr.
"""
import os
import shutil
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()

PILOT_CLIENT = os.path.join(testlib.PLUGIN, os.pardir, "recheck-v2", "skills", "recheck-v2",
                            "scripts", "recheck_core", "records_client.py")
MINE = os.path.join(testlib.SCRIPTS, "signoff_core", "records_client.py")


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


class TheCopyIsExact(unittest.TestCase):
    def test_the_two_files_are_byte_identical(self):
        pilot = os.path.normpath(PILOT_CLIENT)
        self.assertTrue(os.path.isfile(pilot), "the pilot's client is missing at %s" % pilot)
        self.assertTrue(os.path.isfile(MINE), "this station's copy is missing at %s" % MINE)
        self.assertEqual(read_bytes(pilot), read_bytes(MINE),
                         "signoff_core/records_client.py must be recheck_core/records_client.py "
                         "byte for byte; re-copy it rather than editing either")


class TheCopyIsNeverReadForThisStationsName(unittest.TestCase):
    """The copy carries the pilot's STATION constant; nothing in this station may read it."""

    def test_this_stations_name_comes_from_its_own_module(self):
        from signoff_core import constants
        self.assertEqual(constants.STATION, "signoff-v2")

    def test_no_shipped_file_reads_the_copied_stations_constants(self):
        offenders = []
        for dirpath, dirnames, filenames in os.walk(testlib.SCRIPTS):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if not name.endswith(".py") or name == os.path.basename(MINE):
                    continue
                if os.path.basename(dirpath) == "tests" and name != "testlib.py":
                    continue
                text = testlib.read_text(os.path.join(dirpath, name))
                for needle in ("rcl.STATION", "records_client.STATION", "RECHECK_TEST_NO_RECORDS",
                               "rcl.NO_RECORDS_HOOK", "records_client.NO_RECORDS_HOOK"):
                    if needle in text:
                        offenders.append((os.path.join(dirpath, name), needle))
        self.assertEqual(offenders, [])


def copy_component(dst, interface_version=None):
    """A copy of the real records component, optionally speaking another interface version."""
    shutil.copytree(testlib.RECORDS_ROOT, dst,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    if interface_version is not None:
        path = os.path.join(dst, "scripts", "records.py")
        text = testlib.read_text(path)
        want = "INTERFACE_VERSION = 1"
        assert want in text, "the component no longer declares %r" % want
        text = text.replace(want, "INTERFACE_VERSION = %d" % interface_version, 1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return dst


class TheComponentMustSpeakVersionOne(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("signoff-records-identity-")
        self.addCleanup(testlib.rmtree, self.dir)

    def test_a_component_speaking_version_two_is_exit_three(self):
        root = copy_component(os.path.join(self.dir, "records"), interface_version=2)
        code, out, err = testlib.run_script("signoff.py", ["skill-identity", "--records-root", root])
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().split("\n")), 1, err)
        self.assertIn("speaks interface version 2, not 1", err)

    def test_no_component_anywhere_is_exit_three(self):
        lonely = os.path.join(self.dir, "lonely-plugin")
        os.makedirs(lonely)
        code, out, err = testlib.run_script("signoff.py", ["skill-identity", "--plugin-root", lonely],
                                            env={"RECORDS_ROOT": ""})
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().split("\n")), 1, err)
        self.assertTrue(err.strip().startswith("missing dependency: records component (looked in: "), err)

    def test_the_real_component_confirms_version_one(self):
        from signoff_core import records_client as rc
        client = rc.open_client(records_root=testlib.RECORDS_ROOT)
        self.assertEqual(client.interface_version, 1)
        self.assertEqual(client.component_identity()["interface_version"], 1)


class TheComponentIsReachedThroughTheCliOnly(unittest.TestCase):
    """E13-3 and the guide's records assessment: never a log file, never an import, argv only."""

    def test_no_shipped_file_imports_records_core_or_names_a_log_path(self):
        """The SHIPPED files only. A test may read a log to assert what landed in it; the
        station may not, and it may not compute a log's path either — the slug rule (the
        escapes, the separator) is the component's, and duplicating it here would be a copy of
        its code in all but name. Every log path this station records comes from the
        component's own response."""
        offenders = []
        for dirpath, dirnames, filenames in os.walk(testlib.SCRIPTS):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            if os.path.basename(dirpath) == "tests":
                continue
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                text = testlib.read_text(os.path.join(dirpath, name))
                for needle in ("import records_core", "from records_core", "events.jsonl",
                               "docs/records/%s"):
                    if needle in text:
                        offenders.append((os.path.relpath(os.path.join(dirpath, name),
                                                          testlib.SCRIPTS), needle))
        self.assertEqual(offenders, [])

    def test_a_shell_metacharacter_in_a_value_stays_literal(self):
        """A caller value is an argv item; nothing is pasted into shell text.

        `verify` accepts this `--doc` — it is relative, normalized and ends in `.md`, and a log
        that does not exist verifies clean — so the proof is not a refusal but the sentinel: had
        the value reached a shell, `touch` would have run."""
        from signoff_core import records_client as rc
        client = rc.open_client(records_root=testlib.RECORDS_ROOT)
        scratch = testlib.make_scratch("signoff-argv-")
        self.addCleanup(testlib.rmtree, scratch)
        sentinel = os.path.join(scratch, "sentinel")
        doc = "docs/plans/x; touch %s .md" % sentinel
        try:
            body = client.verify(scratch, doc)
        except rc.RecordsRefusal as refusal:
            self.assertIn(refusal.exit_code, (1, 2, 4))
        else:
            self.assertEqual(body["spec"]["doc"], doc,
                             "the value came back exactly as it was sent")
        self.assertFalse(os.path.exists(sentinel),
                         "the metacharacter reached a shell: `touch` created %s" % sentinel)
        self.assertEqual(sorted(os.listdir(scratch)), [],
                         "nothing at all was created in the scratch directory")


if __name__ == "__main__":
    unittest.main()
