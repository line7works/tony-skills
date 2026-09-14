"""recheck.py as an A7a helper: every subcommand from another working directory, an invalid
argument (exit 2), a missing input file (exit 2), jsonschema unavailable (exit 3), --help
content, and the read-only commands identity, ledger, skill-identity."""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()


class CommandLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e8-slice2-cli-")
        cls.cdir = testlib.build_case("W-recording", "W3-01-legacy-round-trip", os.path.join(cls.dir, "W"))
        testlib.prepare_input(cls.cdir)

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def run_cli(self, *args, **kw):
        return testlib.run_script("recheck.py", args, cwd=kw.get("cwd", self.dir), env=kw.get("env"), python=kw.get("python"))

    def test_help(self):
        code, out, err = self.run_cli("--help")
        self.assertEqual(code, 0)
        for phrase in ("start", "record-call", "adjudicate", "new-defect", "record", "resume", "identity", "ledger", "skill-identity",
                       "examples:", "exit status", "test only", "side effects"):
            self.assertIn(phrase, out, phrase)
        code, out, err = self.run_cli("start", "--help")
        self.assertEqual(code, 0)
        for phrase in ("E8-17", "E8-23", "side effects", "example:", "exit:"):
            self.assertIn(phrase, out, phrase)
        with open(os.path.join(testlib.SCRIPTS, "recheck.py"), encoding="utf-8") as fh:
            doc = fh.read()
        for phrase in ("Partial effects", "Test hooks", "RECHECK_TEST_FAIL_AFTER_STEP", "RECHECK_TEST_FAIL_BEFORE_STEP", "RECHECK_TEST_INJECT_BEFORE_STEP",
                       "idempotent", "--skill-root DIR (test only)", "# dependencies = [\"jsonschema==4.25.1\"]"):
            self.assertIn(phrase, doc, phrase)

    def test_invalid_argument_exit_2(self):
        for args in (("--bogus",), ("start",), ("adjudicate", "--run-dir", self.dir, "--item", "x", "--action", "confirmed"),
                     ("record-call", "--run-dir", self.dir, "--call-id", "c", "--status", "weird"), ("nonsense",)):
            code, out, err = self.run_cli(*args)
            self.assertEqual(code, 2, args); self.assertEqual(out, ""); self.assertIn("usage", err)

    def test_missing_input_file_exit_2(self):
        code, out, err = self.run_cli("start", os.path.join(self.dir, "absent.json"))
        self.assertEqual(code, 2); self.assertEqual(out, ""); self.assertIn("does not exist", err)
        code, out, err = self.run_cli("resume", os.path.join(self.dir, "absent.json"))
        self.assertEqual(code, 2)
        bad = os.path.join(self.dir, "bad.json")
        with open(bad, "w") as fh:
            fh.write("{not json")
        code, out, err = self.run_cli("start", bad)
        self.assertEqual(code, 2); self.assertIn("not readable JSON", err)
        code, out, err = self.run_cli("record", "--run-dir", os.path.join(self.dir, "no-such-dir"))
        self.assertEqual(code, 2)
        code, out, err = self.run_cli("record", "--run-dir", self.dir)
        self.assertEqual(code, 2); self.assertIn("no resolved input", err)

    def test_exit_3_without_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.dir)
        env = dict(os.environ, PYTHONPATH=stub)
        for args in (("skill-identity",), ("identity", os.path.join(self.cdir, "workspace")), ("start", os.path.join(self.cdir, "input.json"))):
            code, out, err = self.run_cli(*args, env=env)
            self.assertEqual(code, 3, args); self.assertEqual(out, ""); self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
        env = dict(os.environ, RECHECK_TEST="1", RECHECK_TEST_NO_JSONSCHEMA="1")
        code, out, err = self.run_cli("skill-identity", env=env)
        self.assertEqual(code, 3); self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
        # the hook is inert without RECHECK_TEST=1
        env = dict(os.environ, RECHECK_TEST_NO_JSONSCHEMA="1")
        env.pop("RECHECK_TEST", None)
        code, out, err = self.run_cli("skill-identity", env=env)
        self.assertEqual(code, 0, err); json.loads(out)
        code, out, err = self.run_cli("skill-identity", python="/usr/bin/python3")
        if code != 3:
            self.skipTest("/usr/bin/python3 has jsonschema installed; the stub path above covers exit 3")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_identity_command(self):
        ws = os.path.join(self.cdir, "workspace")
        code, out, err = self.run_cli("identity", ws, cwd=os.path.expanduser("~"))
        self.assertEqual(code, 0, err)
        got = json.loads(out)
        self.assertEqual(got, testlib.load_json(os.path.join(self.cdir, "manifest.json"))["identity"])
        code, out, err = self.run_cli("identity", os.path.join(self.cdir, "run"))
        self.assertEqual(code, 2); self.assertIn("work tree", err)
        # a relative path resolves from the current directory
        code, out, err = self.run_cli("identity", "workspace", cwd=self.cdir)
        self.assertEqual(code, 0, err)

    def test_ledger_command(self):
        """W CASES.md, W3-01: three findings and a legacy waiver; the tag is dropped from the location; the
        MAJOR at :14 has no claim; E4 is waived; the home is the Punch list section."""
        doc = os.path.join(self.cdir, "workspace", "docs/plans/2026-09-18-widget-export.md")
        code, out, err = self.run_cli("ledger", doc, "--workspace", os.path.join(self.cdir, "workspace"))
        self.assertEqual(code, 0, err)
        got = json.loads(out)
        self.assertEqual(got["document"], "docs/plans/2026-09-18-widget-export.md")
        self.assertEqual([r["kind"] for r in got["records"]], ["finding", "finding", "finding", "waiver"])
        self.assertEqual(got["records"][0]["tag"], "csv"); self.assertEqual(got["records"][0]["file"], "src/widget/export.py")
        self.assertEqual([(e["location"], e["claim"] is None, e["state"]) for e in got["entries"]],
                         [("src/widget/export.py:9", False, "open"), ("src/widget/export.py:14", True, "open"), ("src/widget/export.py:32", False, "waived")])
        self.assertEqual(got["cards"], [{"slice": "A", "card": "rejected", "open": 2, "mapping": "rejected"}])
        self.assertFalse(got["ledger_home"]["create"]); self.assertEqual(got["ambiguities"], [])
        code, out, err = self.run_cli("ledger", os.path.join(self.dir, "absent.md"))
        self.assertEqual(code, 2)

    def test_nonexistent_skill_root_exit_2(self):
        missing = os.path.join(self.dir, "absent-root")
        code, out, err = self.run_cli("--skill-root", missing, "skill-identity")
        self.assertEqual(code, 2); self.assertEqual(out, ""); self.assertIn(missing, err); self.assertIn("usage", err)
        code, out, err = self.run_cli("--skill-root", missing, "ledger", os.path.join(self.cdir, "workspace", "docs/plans/2026-09-18-widget-export.md"))
        self.assertEqual(code, 2)

    def test_skill_identity_command(self):
        code, out, err = self.run_cli("skill-identity", cwd=os.path.expanduser("~"))
        self.assertEqual(code, 0, err)
        got = json.loads(out)
        self.assertEqual(sorted(got), ["commit", "content_sha256", "name", "version"])
        self.assertEqual(got["name"], "recheck-v2")
        self.assertTrue(len(got["content_sha256"]) == 64)
        self.assertTrue(got["commit"] == "unversioned" or len(got["commit"]) == 40)
        # from a copied skill root outside any work tree, with no plugin.json beside it: unversioned version and
        # commit; content_sha256 is SKILL.md's (slice 3 wrote it; the contract's hash was the stand-in before)
        import shutil
        copy = os.path.join(self.dir, "root-copy")
        shutil.copytree(testlib.SKILL, copy, ignore=shutil.ignore_patterns("tests", "__pycache__", "examples"))
        code, out, err = self.run_cli("--skill-root", copy, "skill-identity")
        got = json.loads(out)
        self.assertEqual((got["name"], got["version"], got["commit"]), ("recheck-v2", "unversioned", "unversioned"))
        from recheck_core import canon
        self.assertEqual(got["content_sha256"], canon.sha256_file(os.path.join(copy, "SKILL.md")), "content_sha256 of SKILL.md")
        os.remove(os.path.join(copy, "SKILL.md"))
        code, out, err = self.run_cli("--skill-root", copy, "skill-identity")
        self.assertEqual(json.loads(out)["content_sha256"], canon.sha256_file(os.path.join(copy, "references", "pilot-contract.md")), "the contract's hash only when SKILL.md is absent")

    def test_stdout_is_json_only(self):
        code, out, err = self.run_cli("start", os.path.join(self.cdir, "input.json"), cwd=os.path.expanduser("~"))
        self.assertEqual(code, 0, err)
        self.assertTrue(out.strip().startswith("{") and out.strip().endswith("}"))
        json.loads(out)


if __name__ == "__main__":
    unittest.main()
