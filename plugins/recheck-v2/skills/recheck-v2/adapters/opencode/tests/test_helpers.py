"""A7a interface tests for the three OpenCode adapter helpers (E9 section 9.1).

Every helper: `--help`; JSON on stdout and nothing else; exit 2 on an unknown argument; exit 3
with the record or binary absent; run from another working directory (testlib.run always runs
them from the system temp directory, never from the adapter folder).
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

HELPERS = ("invocation.py", "turns.py", "verifier.py")


class HelpAndUsage(unittest.TestCase):
    def test_help_exits_zero_and_documents_the_interface(self):
        for helper in HELPERS:
            code, out, _err = testlib.run(helper, ["--help"])
            self.assertEqual(code, 0, helper)
            for wanted in ("Arguments", "Example", "Exit status", "Side effects"):
                self.assertIn(wanted, out, "%s --help is missing %s" % (helper, wanted))

    def test_unknown_argument_exits_two_and_says_nothing_on_stdout(self):
        for helper in HELPERS:
            code, out, err = testlib.run(helper, ["--no-such-flag"])
            self.assertEqual(code, 2, helper)
            self.assertEqual(out, "", "%s wrote to stdout on a usage slip" % helper)
            self.assertIn("unknown argument", err, helper)

    def test_a_flag_without_its_value_exits_two(self):
        for helper, flag in (("invocation.py", "--workspace"), ("turns.py", "--find"),
                             ("verifier.py", "--brief")):
            code, out, err = testlib.run(helper, [flag])
            self.assertEqual(code, 2, helper)
            self.assertEqual(out, "")
            self.assertIn("needs a value", err)

    def test_verifier_requires_its_four_paths(self):
        code, out, err = testlib.run("verifier.py", ["--brief", "/tmp/x"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("is required", err)

    def test_invocation_rejects_a_bad_run_date_and_a_relative_run_dir(self):
        code, _out, err = testlib.run("invocation.py", ["--run-date", "20260920"])
        self.assertEqual(code, 2)
        self.assertIn("YYYY-MM-DD", err)
        code, _out, err = testlib.run(
            "invocation.py", ["--run-id", "r", "--run-dir", "relative/dir"])
        self.assertEqual(code, 2)
        self.assertIn("absolute", err)

    def test_invocation_caller_route_needs_the_callers_ids(self):
        code, _out, err = testlib.run("invocation.py", ["--caller", "ship-v2"])
        self.assertEqual(code, 2)
        self.assertIn("--run-id", err)


class MissingRecordOrBinary(unittest.TestCase):
    def test_turns_exits_three_when_the_store_is_absent(self):
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root)
            os.remove(os.path.join(setup, "xdg-data", "opencode", "opencode.db"))
            code, out, err = testlib.run("turns.py", ["--setup", setup])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("session store not found", err)
        finally:
            testlib.cleanup(root)

    def test_turns_exits_three_when_no_session_ran_in_the_workspace(self):
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root, testlib.load_record(), directory="/nowhere/at/all")
            code, out, err = testlib.run(
                "turns.py", ["--setup", setup, "--workspace", os.path.join(root, "elsewhere")])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no session in the store", err)
        finally:
            testlib.cleanup(root)

    def test_turns_exits_three_on_an_unknown_session_id(self):
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root, testlib.load_record())
            code, out, err = testlib.run("turns.py", ["--setup", setup, "--session", "ses_nope"])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no session ses_nope", err)
        finally:
            testlib.cleanup(root)

    def test_invocation_exits_three_when_the_binary_is_absent(self):
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root, testlib.load_record())
            code, out, err = testlib.run(
                "invocation.py",
                ["--setup", setup, "--session", testlib.load_record()["session"]["id"],
                 "--opencode", os.path.join(root, "no-such-binary")],
                env={"PATH": os.path.join(root, "empty-path")},
            )
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("opencode binary was not found", err)
        finally:
            testlib.cleanup(root)

    def test_verifier_exits_three_when_the_brief_is_absent(self):
        root = tempfile.mkdtemp()
        try:
            code, out, err = testlib.run(
                "verifier.py",
                ["--brief", os.path.join(root, "no-brief.md"), "--workspace", root,
                 "--scratch", os.path.join(root, "scratch"),
                 "--raw", os.path.join(root, "scratch", "raw.md")])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no brief at", err)
        finally:
            testlib.cleanup(root)

    def test_verifier_reports_lane_unavailable_when_the_binary_is_absent(self):
        """A missing harness is a reported status, not a helper failure (verifier.md section 7)."""
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root)
            brief = os.path.join(root, "checklist.md")
            with open(brief, "w", encoding="utf-8") as handle:
                handle.write("the brief\n")
            code, out, _err = testlib.run(
                "verifier.py",
                ["--brief", brief, "--workspace", root, "--setup", setup,
                 "--scratch", os.path.join(root, "scratch"),
                 "--raw", os.path.join(root, "scratch", "raw.md"),
                 "--opencode", os.path.join(root, "no-such-binary")],
                env={"PATH": os.path.join(root, "empty-path")},
            )
            self.assertEqual(code, 0)
            document = json.loads(out)
            self.assertEqual(document["status"], "lane-unavailable")
            self.assertIsNone(document["raw"])
        finally:
            testlib.cleanup(root)


class JsonOnStdoutOnly(unittest.TestCase):
    def test_turns_prints_one_json_document_and_diagnostics_go_to_stderr(self):
        root = tempfile.mkdtemp()
        try:
            record = testlib.load_record()
            setup = testlib.make_setup(root, record, directory=root)
            code, out, err = testlib.run(
                "turns.py", ["--setup", setup, "--workspace", root])
            self.assertEqual(code, 0)
            document = json.loads(out)          # parses whole: nothing else on stdout
            self.assertEqual(document["harness"], "opencode")
            self.assertEqual(document["resolved_by"], "newest-in-directory")
            self.assertNotIn("{", err)
        finally:
            testlib.cleanup(root)

    def test_turns_never_reads_the_credential_table(self):
        root = tempfile.mkdtemp()
        try:
            record = testlib.load_record()
            setup = testlib.make_setup(root, record, directory=root)
            code, out, err = testlib.run("turns.py", ["--setup", setup, "--workspace", root,
                                                      "--raw"])
            self.assertEqual(code, 0)
            self.assertNotIn("a-value-no-test-may-print", out)
            self.assertNotIn("a-value-no-test-may-print", err)
        finally:
            testlib.cleanup(root)


if __name__ == "__main__":
    unittest.main()
