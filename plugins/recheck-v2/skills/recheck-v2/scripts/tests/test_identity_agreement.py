"""E13 slice 1, brief 3.2 CR-3: the pilot's identity and the component's are the same six fields.

`append` refuses a clear (exit 6) unless `verified_source` equals the identity the component
computes, and the component excludes `docs/records/` from the dirty check, the tracked diff and the
untracked list. The pilot applies the same fixed exclusion, so a log this run wrote is never a
boundary violation and never makes the run `stale_source`. A workspace with no `docs/records/`
hashes to exactly the bytes it did before (E7 step 6 stays green).
"""
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import identity  # noqa: E402
from recheck_core import records_client as rc  # noqa: E402

RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
DOC = "docs/plans/2026-09-18-widget-export.md"


class IdentityAgreement(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e13-identity-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean", self.dir)
        self.workspace = os.path.join(self.case, "workspace")
        self.client = rc.open_client(records_root=RECORDS)

    def component_identity(self):
        return self.client.identity(self.workspace)["identity"]

    def pilot_identity(self):
        return identity.identity_of(self.workspace)

    def assert_agree(self, why):
        want, got = self.component_identity(), self.pilot_identity()
        self.assertEqual(want, got, "%s: the component and the pilot disagree" % why)

    def write(self, rel, text):
        path = os.path.join(self.workspace, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # ---- the four workspaces CR-3 names ---------------------------------------------------

    def test_clean_workspace(self):
        self.assert_agree("a clean workspace")
        self.assertFalse(self.pilot_identity()["dirty"])

    def test_dirty_workspace(self):
        self.write("src/widget/export.py", "# changed by the test\n")
        self.assert_agree("a tracked file changed")
        self.assertTrue(self.pilot_identity()["dirty"])

    def test_untracked_content(self):
        self.write("notes.txt", "a new untracked file\n")
        self.assert_agree("an untracked file")
        self.assertIn("notes.txt", self.pilot_identity()["untracked"])

    def test_log_present_workspace_is_not_dirty(self):
        before = self.pilot_identity()
        self.client.import_legacy(self.workspace, DOC)
        log = os.path.join(self.workspace, "docs", "records")
        self.assertTrue(os.path.isdir(log))
        self.assert_agree("a log this run wrote")
        after = self.pilot_identity()
        self.assertFalse(after["dirty"], "a log-present workspace that is otherwise clean is not dirty")
        self.assertEqual(before, after, "writing the log changes no identity byte")

    def test_log_present_and_otherwise_dirty(self):
        self.client.import_legacy(self.workspace, DOC)
        self.write("src/widget/export.py", "# changed by the test\n")
        self.assert_agree("a log beside a real change")
        self.assertTrue(self.pilot_identity()["dirty"])

    # ---- E7 step 6: a workspace with no docs/records/ hashes as it always did ---------------

    def test_no_records_folder_keeps_the_e7_bytes(self):
        lib = testlib.fixturelib()
        self.assertFalse(os.path.exists(os.path.join(self.workspace, "docs", "records")))
        self.assertEqual(lib.identity_of(self.workspace), self.pilot_identity())
        self.write("notes.txt", "untracked\n")
        self.assertEqual(lib.identity_of(self.workspace), self.pilot_identity())

    # ---- the exclusion is the component's fixed list, not a guess --------------------------

    def test_the_exclusion_is_the_one_the_component_publishes(self):
        published = self.client.identity(self.workspace)["excluded"]
        self.assertEqual(list(published), list(identity.EXCLUDED_PREFIXES))

    def test_tracked_diff_excluding_also_drops_the_log(self):
        """The section 9 boundary check uses the same exclusion, so a committed log that the run
        then appends to is not a tracked change outside the plan."""
        self.client.import_legacy(self.workspace, DOC)
        subprocess.run(["git", "add", "-A"], cwd=self.workspace, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@e.invalid", "commit", "-q", "-m", "log"],
                       cwd=self.workspace, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        state = self.client.state(self.workspace, DOC)
        ident = self.component_identity()
        event = {"v": 1, "kind": "disposition", "at": "2026-09-20T09:00:00Z", "ledger_doc": DOC,
                 "actor": {"station": "recheck-v2", "run_id": "probe", "harness": "h"},
                 "origin": {"kind": "native"}, "source": {"known": True, "identity": ident},
                 "finding": state["findings"][0]["id"], "disposition": "fixed",
                 "how": "executed the scenario", "verified_source": {"known": True, "identity": ident},
                 "join_basis": None}
        self.client.append(self.workspace, DOC, [event], state["head"], self.dir)
        self.assertEqual(identity.tracked_diff_excluding(self.workspace, []), b"")
        self.assert_agree("an appended log that is tracked")


if __name__ == "__main__":
    unittest.main()
