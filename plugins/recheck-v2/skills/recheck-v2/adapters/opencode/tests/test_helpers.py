"""A7a interface tests for the three OpenCode adapter helpers (E9 section 9.1).

Every helper: `--help`; JSON on stdout and nothing else; exit 2 on an unknown argument; exit 3
with the record or binary absent; run from another working directory (testlib.run always runs
them from the system temp directory, never from the adapter folder).

Ruling E9-34, Astra finding 13: an absent binary is a missing dependency and exits 3 naming
it, never a reported status.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

HELPERS = ("invocation.py", "turns.py", "verifier.py")
TEST_ENV = {"RECHECK_ADAPTER_TEST": "1"}


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

    def test_an_empty_find_is_a_usage_error(self):
        code, out, err = testlib.run("turns.py", ["--find", "   "])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("needs words", err)

    def test_the_test_only_arguments_are_refused_at_run_time(self):
        """Ruling E9-32: the fixture interface is not a run-time override."""
        for helper, args in (
            ("turns.py", ["--session", "ses_x"]),
            ("turns.py", ["--workspace", "/tmp"]),
            ("turns.py", ["--db", "/tmp/x.db"]),
            ("invocation.py", ["--session", "ses_x"]),
            ("invocation.py", ["--opencode", "/bin/true"]),
            ("verifier.py", ["--session", "ses_x"]),
        ):
            code, out, err = testlib.run(helper, args)
            self.assertEqual(code, 2, "%s %s" % (helper, args))
            self.assertEqual(out, "")
            self.assertIn("test-only argument", err)


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
                "turns.py", ["--setup", setup, "--workspace", os.path.join(root, "elsewhere")],
                env=TEST_ENV)
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no session in the store", err)
        finally:
            testlib.cleanup(root)

    def test_turns_exits_three_on_an_unknown_session_id(self):
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root, testlib.load_record())
            code, out, err = testlib.run(
                "turns.py", ["--setup", setup, "--session", "ses_nope"], env=TEST_ENV)
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no session ses_nope", err)
        finally:
            testlib.cleanup(root)

    def test_invocation_exits_three_when_the_setup_has_no_binary(self):
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root, testlib.load_record())
            env = testlib.write_pointer(root, 5150, testlib.load_record()["session"]["id"])
            env["PATH"] = os.path.join(root, "empty-path")
            code, out, err = testlib.run("invocation.py", ["--setup", setup], env=env)
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no opencode binary at", err)
            self.assertIn("no PATH fallback", err)
        finally:
            testlib.cleanup(root)

    def test_invocation_exits_three_when_the_setup_is_absent(self):
        root = tempfile.mkdtemp()
        try:
            code, out, err = testlib.run(
                "invocation.py", ["--setup", os.path.join(root, "no-such-setup")])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no isolated pilot setup at", err)
        finally:
            testlib.cleanup(root)

    def test_verifier_exits_three_when_the_brief_is_absent(self):
        root = tempfile.mkdtemp()
        try:
            run_dir = os.path.join(root, "run")
            os.makedirs(run_dir)
            setup = testlib.make_setup(root, testlib.load_record(), binary=True)
            code, out, err = testlib.run(
                "verifier.py",
                ["--brief", os.path.join(run_dir, "checklist.md"), "--workspace", root,
                 "--setup", setup,
                 "--scratch", os.path.join(run_dir, "verifier"),
                 "--raw", os.path.join(run_dir, "verifier", "raw.md")])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no brief at", err)
        finally:
            testlib.cleanup(root)

    def test_verifier_exits_three_when_the_binary_is_absent(self):
        """Astra finding 13 / ruling E9-34: A7a's dependency exit, not `lane-unavailable`."""
        root = tempfile.mkdtemp()
        try:
            setup = testlib.make_setup(root, testlib.load_record())   # no binary
            run_dir = os.path.join(root, "run")
            os.makedirs(run_dir)
            brief = os.path.join(run_dir, "checklist.md")
            with open(brief, "w", encoding="utf-8") as handle:
                handle.write("the brief\n")
            code, out, err = testlib.run(
                "verifier.py",
                ["--brief", brief, "--workspace", root, "--setup", setup,
                 "--scratch", os.path.join(run_dir, "verifier"),
                 "--raw", os.path.join(run_dir, "verifier", "raw.md")],
                env={"PATH": os.path.join(root, "empty-path")},
            )
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no opencode binary at", err)
            self.assertFalse(os.path.isdir(os.path.join(run_dir, "verifier")))
        finally:
            testlib.cleanup(root)

    def test_verifier_exits_three_when_the_setup_is_absent(self):
        """Finding 9: an absent setup stops before any launch, never on the live home."""
        root = tempfile.mkdtemp()
        try:
            run_dir = os.path.join(root, "run")
            os.makedirs(run_dir)
            brief = os.path.join(run_dir, "checklist.md")
            with open(brief, "w", encoding="utf-8") as handle:
                handle.write("the brief\n")
            code, out, err = testlib.run(
                "verifier.py",
                ["--brief", brief, "--workspace", root,
                 "--setup", os.path.join(root, "no-such-setup"),
                 "--scratch", os.path.join(run_dir, "verifier"),
                 "--raw", os.path.join(run_dir, "verifier", "raw.md")])
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("no isolated pilot setup at", err)
        finally:
            testlib.cleanup(root)


class JsonOnStdoutOnly(unittest.TestCase):
    def test_turns_prints_one_json_document_and_diagnostics_go_to_stderr(self):
        root = tempfile.mkdtemp()
        try:
            record = testlib.load_record()
            setup = testlib.make_setup(root, record, directory=root)
            env = testlib.write_pointer(root, 5151, record["session"]["id"])
            code, out, err = testlib.run("turns.py", ["--setup", setup], env=env)
            self.assertEqual(code, 0, err)
            document = json.loads(out)          # parses whole: nothing else on stdout
            self.assertEqual(document["harness"], "opencode")
            self.assertEqual(document["resolved_by"], "pointer")
            self.assertNotIn("{", err)
        finally:
            testlib.cleanup(root)

    def test_turns_never_reads_the_credential_table(self):
        root = tempfile.mkdtemp()
        try:
            record = testlib.load_record()
            setup = testlib.make_setup(root, record, directory=root)
            env = testlib.write_pointer(root, 5152, record["session"]["id"])
            code, out, err = testlib.run("turns.py", ["--setup", setup, "--raw"], env=env)
            self.assertEqual(code, 0, err)
            self.assertNotIn("a-value-no-test-may-print", out)
            self.assertNotIn("a-value-no-test-may-print", err)
        finally:
            testlib.cleanup(root)


if __name__ == "__main__":
    unittest.main()
