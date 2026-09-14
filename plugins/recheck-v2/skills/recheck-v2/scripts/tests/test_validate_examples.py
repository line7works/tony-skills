"""scripts/validate-examples.py (A7a, E8-A37): JSON on stdout, the per-check lines on stderr under --verbose,
--help, --skill-root, exit 2 on an unknown argument, 3 without jsonschema, 4 when a check fails."""
import json
import os
import shutil
import unittest

import testlib

# the cases the suite defines after the fix round that followed Astra's review; a suite that lost cases
# would still report counts equal to totals, so the floor catches that
NEGATIVE_FLOOR = 155
POSITIVE_FLOOR = 32
CHECKPOINT_FLOOR = 15
RECEIPT_FLOOR = 9
# the case names earlier fix rounds added: finding 1 (E8-2), finding 4 (E8-A2), finding 5 (receipt plan steps)
NEW_NEGATIVE_CASES = (
    "stopped submodule result carrying source_identity (E8-2)",
    "run.model with floor_met as a string (E8-A2)",
    "receipt: a plan target with a .. segment",
    "receipt: a cancelled flag on a punch-list step",
    "receipt: a value on a punch-list step",
    "receipt: content on a status-line step",
    # E8-A34
    "stopped result carrying items (E8-A34)",
    "a completed result with floor_met false (E8-A34)",
    "a completed result with floor_met null (E8-A34)",
    "a new defect without severity_basis (E8-A34)",
    "checkpoint: seq 0 with a prev string (E8-A34)",
    "receipt: a status_line value of built (E8-A34)",
    "input: a waiver dated 2026-02-30 (E8-A34, FormatChecker)",
    "input: a run_date of 2026-99-99 (E8-A34, FormatChecker)",
    # E8-A50
    "input: a seven-hex pin (E8-A50)",
)
NEW_POSITIVE_CASES = (
    "a stopped submodule result without source_identity (E8-2)",
    "run.model carrying floor_met true (E8-A2)",
    "a receipt plan target whose segment merely starts with two dots",
    "a receipt status-line step carrying cancelled false beside its value",
    "a receipt reopened-line step carrying content",
    # E8-A34
    "a verifier_unavailable run.model carrying floor_met null (unknown capability, E8-A2, E8-A34)",
    "a new defect carrying its severity_basis (E8-A34)",
    "a receipt status_line value of signed off with conditions (E8-A34)",
    # E8-A50
    "input: a forty-hex pin (E8-A50)",
)
KEYS = ["checkpoint", "failures", "mutations", "negative", "ok", "positive", "receipt"]


class ValidateExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e8-slice1-examples-")

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def run_cli(self, *args, **kw):
        return testlib.run_script("validate-examples.py", args, cwd=kw.get("cwd", self.dir), env=kw.get("env"))

    def assert_report(self, doc):
        self.assertEqual(sorted(doc), KEYS, "the fixed stdout shape")
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["failures"], [])
        self.assertEqual(doc["positive"]["failing"], 0)
        self.assertEqual(doc["positive"]["files"], len([f for f in os.listdir(testlib.EX) if f.endswith(".json")]))
        self.assertEqual(doc["negative"]["rejected"], doc["negative"]["total"])
        self.assertEqual(doc["mutations"]["accepted"], doc["mutations"]["total"])
        self.assertEqual(doc["checkpoint"]["passed"], doc["checkpoint"]["total"])
        self.assertEqual(doc["receipt"]["passed"], doc["receipt"]["total"])
        self.assertGreaterEqual(doc["negative"]["total"], NEGATIVE_FLOOR, "the negative suite lost cases")
        self.assertGreaterEqual(doc["mutations"]["total"], POSITIVE_FLOOR, "the positive mutations lost cases")
        self.assertGreaterEqual(doc["checkpoint"]["total"], CHECKPOINT_FLOOR)
        self.assertGreaterEqual(doc["receipt"]["total"], RECEIPT_FLOOR)

    def test_passes_from_another_directory_with_json_on_stdout(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 0, err + out[-2000:])
        self.assertTrue(out.strip().startswith("{") and out.strip().endswith("}"), "stdout is JSON and nothing else")
        doc = json.loads(out)
        self.assert_report(doc)
        self.assertNotIn("(BUG)", err); self.assertNotIn("FAIL ", err)
        self.assertNotIn("REJECTED ", err, "the per-file lines appear only under --verbose")
        self.assertIn("positive:", err, "the summary line is a diagnostic on stderr")

    def test_verbose_prints_every_check_on_stderr(self):
        code, out, err = self.run_cli("--verbose")
        self.assertEqual(code, 0, err[-2000:])
        self.assert_report(json.loads(out))
        self.assertNotIn("(BUG)", err); self.assertNotIn("FAIL ", err)
        for needle in ("receipt-partial.json", "checkpoint-partial.json", "E8-15", "harness given as a string",
                       "model without floor_met", "turn_attribution", "refused_actions", "raw_sha256", "every new invocation field"):
            self.assertIn(needle, err, needle)
        lines = err.splitlines()
        for name in NEW_NEGATIVE_CASES:
            self.assertIn("REJECTED " + name, lines, name)
        for name in NEW_POSITIVE_CASES:
            self.assertIn("ACCEPTED " + name, lines, name)
        self.assertEqual(len([l for l in lines if l.startswith("PASS ")]), json.loads(out)["positive"]["files"])

    def test_exit_3_without_jsonschema(self):
        env = dict(os.environ, PYTHONPATH=testlib.stub_without_jsonschema(self.dir))
        code, out, err = self.run_cli(env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_exit_2_on_an_unknown_argument(self):
        code, out, err = self.run_cli("--bogus")
        self.assertEqual(code, 2); self.assertEqual(out, ""); self.assertIn("usage", err)
        code, out, err = self.run_cli("--skill-root", os.path.join(self.dir, "nowhere"))
        self.assertEqual(code, 2); self.assertEqual(out, ""); self.assertIn("not a directory", err)

    def test_help(self):
        code, out, _ = self.run_cli("--help")
        self.assertEqual(code, 0)
        flat = " ".join(out.split())
        for phrase in ("--skill-root", "--verbose", "test only", "example", "side effects", "exit status", "4 a check failed", "2 usage", "3 jsonschema missing"):
            self.assertIn(phrase, flat, phrase)

    def test_skill_root_override_and_exit_4(self):
        """A copied skill root with one example broken: exit 4, the JSON names the failure, --verbose prints FAIL."""
        root = os.path.join(self.dir, "skill-root")
        shutil.copytree(testlib.SKILL, root, ignore=shutil.ignore_patterns("tests", "__pycache__"))
        code, out, err = self.run_cli("--skill-root", root)
        self.assertEqual(code, 0, err)
        self.assert_report(json.loads(out))
        broken = os.path.join(root, "references", "examples", "result-stopped.json")
        doc = testlib.load_json(broken)
        doc["items"] = []  # E8-A34: a stopped result may not carry items
        with open(broken, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        code, out, err = self.run_cli("--skill-root", root, "--verbose")
        self.assertEqual(code, 4)
        got = json.loads(out)
        self.assertFalse(got["ok"])
        self.assertEqual(got["positive"]["failing"], 1)
        self.assertTrue(any("result-stopped.json" in f for f in got["failures"]), got["failures"])
        self.assertIn("FAIL result-stopped.json", err)
        # a missing schema under the override is exit 1 (reference unavailable), nothing on stdout
        os.remove(os.path.join(root, "references", "receipt.schema.json"))
        code, out, err = self.run_cli("--skill-root", root)
        self.assertEqual(code, 1); self.assertEqual(out, ""); self.assertIn("reference unavailable: references/receipt.schema.json", err)

    def test_a_malformed_example_is_a_failure_not_a_crash(self):
        """E8-A51: a positive example replaced by {} fails its schema and breaks the mutations that use it as a base;
        one that is not JSON fails to load; the checkpoint example replaced breaks its checks. Each is exit 4 with the
        JSON on stdout, ok false, and a failure naming the file; never exit 1 (reserved for a missing schema)."""
        root = os.path.join(self.dir, "skill-root-malformed")
        shutil.copytree(testlib.SKILL, root, ignore=shutil.ignore_patterns("tests", "__pycache__"))
        examples = os.path.join(root, "references", "examples")
        target = "input-direct.json"
        self.assertTrue(os.path.exists(os.path.join(examples, target)))

        def run_expecting_failure(name):
            code, out, err = self.run_cli("--skill-root", root)
            self.assertEqual(code, 4, err[-2000:] + out[-500:])
            self.assertNotIn("validate-examples.py failed", err)
            got = json.loads(out)
            self.assertEqual(sorted(got), KEYS)
            self.assertFalse(got["ok"])
            self.assertTrue(any(name in f for f in got["failures"]), got["failures"])
            return got

        with open(os.path.join(examples, target), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        got = run_expecting_failure(target)
        self.assertEqual(got["positive"]["failing"], 1)
        self.assertTrue(any(target in f and "mutation raised" in f for f in got["failures"]), "a mutation on {} raises (KeyError) and is reported")
        self.assertLess(got["negative"]["rejected"], got["negative"]["total"] + 1)
        with open(os.path.join(examples, target), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        got = run_expecting_failure(target)
        self.assertTrue(any(target in f and "does not load" in f for f in got["failures"]), got["failures"])
        self.assertLess(got["mutations"]["accepted"], got["mutations"]["total"], "the cases on the unloadable base count as not passed")
        shutil.copy(os.path.join(testlib.EX, target), os.path.join(examples, target))
        with open(os.path.join(examples, "checkpoint-partial.json"), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        got = run_expecting_failure("checkpoint-partial.json")
        self.assertEqual(got["checkpoint"]["passed"], 0)
        self.assertEqual(got["checkpoint"]["total"], CHECKPOINT_FLOOR)

    def test_old_location_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(testlib.EX, "validate-examples.py")))
        self.assertTrue(os.path.exists(os.path.join(testlib.SCRIPTS, "validate-examples.py")))


if __name__ == "__main__":
    unittest.main()
