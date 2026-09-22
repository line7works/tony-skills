"""Report-only writes nothing, and the identity this station computes is the component's.

**Report-only** is a field of the input. In that mode the run writes nothing to the workspace and
nothing to the log, and its result says so. It is not a dry run that skips the work: the source
set is computed, the packet is built, the reviewer's answer is adjudicated and the findings the
reviewer raised are named as raised in the result. Only the recording is withheld, and
`verdict_recorded` is false.

The measurement is a hash over every file of the workspace — the log included, and `.git`
excluded, since git's own bookkeeping is not this station's write — taken before and after the
whole run. Equal hashes, or the test means nothing.

**Identity agreement** matters because the component refuses a clear whose `verified_source` is
not the identity IT computes, field for field. The two implementations exclude the same fixed
prefix (`docs/records/`) and must agree; a test that only checked this station's own function
would pass while the two drifted apart.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import identity as idmod  # noqa: E402
from signoff_core import records_client as rcl  # noqa: E402


class ReportOnlyCase(unittest.TestCase):
    CASE = "S1-05-report-only"

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-report-only-")
        self.addCleanup(testlib.rmtree, self.dir)
        family = testlib.family_of(self.CASE)
        self.case = testlib.build_case(family, self.CASE, os.path.join(self.dir, family))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}

    def write_input(self, report_only):
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "report-only-run",
                              "run_dir": self.run_dir, "run_date": "2026-09-21", "harness": None,
                              "sessions": self.seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": self.seeded["build_doc"], "slice": self.seeded["slice"],
                          "base": self.seeded["base"]},
               "report_only": report_only,
               "review": {"depth": "LEAN", "route": "test"}}
        return testlib.write_json(os.path.join(self.case, "signoff-input.json"), doc)

    def drive(self, report_only=True):
        path = self.write_input(report_only)
        out = None
        for args in (["check-input", path], ["scope", "--run-dir", self.run_dir],
                     ["request", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer",
                      os.path.join(self.case, "answer.json")]):
            code, out, err = testlib.signoff(args, env=self.env)
            self.assertEqual(code, 0, err or json.dumps(out))
        code, out, err = testlib.signoff(["record", "--run-dir", self.run_dir], env=self.env)
        return code, out, err


class ReportOnlyWritesNothing(ReportOnlyCase):
    def test_the_workspace_and_the_log_are_byte_identical_before_and_after(self):
        before = testlib.tree_hash(self.workspace, exclude=(".git",))
        code, out, err = self.drive(report_only=True)
        self.assertEqual(code, 10, err or json.dumps(out))
        self.assertEqual(out["status"], "completed", json.dumps(out))
        after = testlib.tree_hash(self.workspace, exclude=(".git",))
        self.assertEqual(before, after, "a report-only run wrote into the workspace")
        self.assertFalse(os.path.isdir(os.path.join(self.workspace, "docs", "records")),
                         "a report-only run opened a log")
        self.assertEqual(testlib.project_status(self.workspace).strip(), "")

    def test_the_result_says_report_only_and_records_no_verdict(self):
        code, out, err = self.drive(report_only=True)
        self.assertTrue(out["report_only"])
        self.assertTrue(out["writes_none"])
        self.assertFalse(out["verdict_recorded"])
        self.assertIsNone(out["verdict_doc"])
        result = testlib.load_json(out["result"])
        self.assertTrue(result["report_only"])
        self.assertFalse(result["verdict_recorded"])
        self.assertIn("report-only", testlib.read_text(out["chat"]).lower())

    def test_the_findings_the_reviewer_raised_are_still_named_as_raised(self):
        """Report-only withholds the recording, never the review."""
        code, out, err = self.drive(report_only=True)
        result = testlib.load_json(out["result"])
        self.assertEqual([row["location"] for row in result["findings"]],
                         ["src/signpost/pad.py:6"])
        self.assertEqual(result["findings"][0]["severity"], "MAJOR")
        self.assertEqual(result["findings"][0]["evidence_kind"], "executed")
        self.assertTrue(result["source_set"]["committed"])
        self.assertTrue(result["packet"]["files"])

    def test_every_artifact_it_wrote_is_inside_the_run_directory(self):
        code, out, err = self.drive(report_only=True)
        result = testlib.load_json(out["result"])
        self.assertTrue(result["records_written"])
        for row in result["records_written"]:
            self.assertEqual(row["kind"], "run_artifact", row)
            self.assertTrue(os.path.realpath(row["path"]).startswith(
                os.path.realpath(self.run_dir) + os.sep), row)

    def test_the_same_case_not_report_only_does_write(self):
        """The control: without the flag this workspace IS written, so the test above measures
        the flag and not an inert case."""
        before = testlib.tree_hash(self.workspace, exclude=(".git",))
        code, out, err = self.drive(report_only=False)
        self.assertEqual(code, 10, err or json.dumps(out))
        self.assertEqual(out["status"], "completed", json.dumps(out))
        self.assertNotEqual(before, testlib.tree_hash(self.workspace, exclude=(".git",)))
        self.assertTrue(out["verdict_recorded"])


class TheIdentityIsTheComponents(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("signoff-identity-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case("S1-review-scope", "S1-02-untracked-defect",
                                       os.path.join(self.dir, "S1-review-scope"))
        self.workspace = os.path.join(self.case, "workspace")
        self.client = rcl.open_client(records_root=testlib.RECORDS_ROOT)

    def test_the_six_fields_agree_field_for_field(self):
        mine = idmod.identity_of(self.workspace)
        theirs = self.client.identity(self.workspace)["identity"]
        self.assertEqual(mine, theirs)

    def test_the_exclusion_list_is_the_one_the_component_publishes(self):
        published = self.client.identity(self.workspace)["excluded"]
        self.assertEqual(list(idmod.EXCLUDED_PREFIXES), published)

    def test_a_log_write_does_not_change_the_identity(self):
        """CR-3: the component's history describes the source and is never part of it."""
        before = idmod.identity_of(self.workspace)
        self.client.import_legacy(self.workspace, "docs/plans/2026-09-18-signpost-rows.md")
        self.assertTrue(os.path.isdir(os.path.join(self.workspace, "docs", "records")),
                        "the import opened a log, so there is something to exclude")
        self.assertEqual(idmod.identity_of(self.workspace), before)
        self.assertEqual(self.client.identity(self.workspace)["identity"], before)

    def test_the_source_set_excludes_the_log_too(self):
        self.client.import_legacy(self.workspace, "docs/plans/2026-09-18-signpost-rows.md")
        source = idmod.source_set(self.workspace, "base")
        every = source["committed"] + source["changed"] + source["untracked"]
        self.assertEqual([p for p in every if p.startswith("docs/records/")], [])


if __name__ == "__main__":
    unittest.main()
