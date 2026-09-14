"""validate-result.py (A7a interface) and the slice-1 semantic checks of recheck_core.validate."""
import copy
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import validate  # noqa: E402

# example results and the input each resolved (matched on run_id)
INPUT_FOR = {
    "result-completed.json": "input-caller.json",
    "result-missing-input-interactive.json": "input-direct.json",
    "result-stale-source.json": "input-direct.json",
}
SLICE1_CHECKS = {"V1", "V2", "V5", "V9", "V10", "V11", "V12", "V15", "V16"}
V12_SKIP = "skipped: cancelled flags on the receipt's status-line steps: slice 2"


def example(name):
    return os.path.join(testlib.EX, name)


def status_line_index(doc):
    idx = [i for i, w in enumerate(doc["records_written"]) if w["kind"] == "status_line"]
    assert len(idx) == 1, idx
    return idx[0]


def violated(doc):
    """The completed example as a violated run: a boundary violation, result not_clear, the card frozen, no status line."""
    d = copy.deepcopy(doc)
    d["boundary_violations"] = ["src/export.ts changed between the pre-transaction identity and the status-line check"]
    d["result"] = "not_clear"
    d["cards"][0]["after"] = d["cards"][0]["before"]
    d["records_written"].pop(status_line_index(d))
    return d


class CommandLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e8-slice1-cli-")

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def run_cli(self, *args, **kw):
        return testlib.run_script("validate-result.py", args, cwd=kw.get("cwd", self.dir), python=kw.get("python"), env=kw.get("env"))

    def test_every_example_result_passes(self):
        for name in sorted(os.listdir(testlib.EX)):
            if not name.startswith("result-"):
                continue
            args = [example(name)]
            if name in INPUT_FOR:
                args += ["--input", example(INPUT_FOR[name])]
            code, out, err = self.run_cli(*args)
            self.assertEqual(code, 0, "%s: exit %d, stderr %s, stdout %s" % (name, code, err, out))
            doc = json.loads(out)
            self.assertEqual(sorted(doc), ["ok", "schema", "semantic", "skipped"], "the fixed stdout shape")
            self.assertTrue(doc["ok"], name)
            self.assertEqual(doc["schema"], [], name)
            self.assertEqual(doc["semantic"], [], name)
            self.assertTrue(out.strip().startswith("{") and out.strip().endswith("}"), "stdout is JSON and nothing else")
            skipped = {s["id"] for s in doc["skipped"]}
            if name in INPUT_FOR:
                self.assertNotIn("V16", skipped, name)
            else:
                self.assertIn("V16", skipped, "V16 needs the input")

    def test_runs_from_another_directory_with_relative_path(self):
        shutil.copy(example("result-nothing-open.json"), os.path.join(self.dir, "r.json"))
        code, out, _ = self.run_cli("r.json", cwd=self.dir)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["ok"])

    def test_exit_3_without_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.dir)
        env = dict(os.environ, PYTHONPATH=stub)
        code, out, err = self.run_cli(example("result-completed.json"), env=env)
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "", "nothing on stdout")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
        code, out, err = self.run_cli(example("result-completed.json"), python="/usr/bin/python3")
        if code != 3 and "missing dependency" not in err:
            self.skipTest("/usr/bin/python3 has jsonschema installed; the stub path above covers exit 3")
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)

    def test_exit_3_through_the_gated_hook(self):
        """RECHECK_TEST_NO_JSONSCHEMA=1 counts only with RECHECK_TEST=1 (lane contract section 9)."""
        for script in ("validate-result.py", "validate-examples.py"):
            args = [example("result-completed.json")] if script == "validate-result.py" else []
            env = dict(os.environ, RECHECK_TEST="1", RECHECK_TEST_NO_JSONSCHEMA="1")
            code, out, err = testlib.run_script(script, args, cwd=self.dir, env=env)
            self.assertEqual(code, 3, script); self.assertEqual(out, ""); self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
            env = dict(os.environ, RECHECK_TEST_NO_JSONSCHEMA="1")
            env.pop("RECHECK_TEST", None)
            code, out, err = testlib.run_script(script, args, cwd=self.dir, env=env)
            self.assertEqual(code, 0, "%s: the hook is inert without RECHECK_TEST=1 (%s)" % (script, err))

    def test_exit_2_usage(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 2); self.assertEqual(out, ""); self.assertIn("usage", err)
        code, out, err = self.run_cli(os.path.join(self.dir, "absent.json"))
        self.assertEqual(code, 2); self.assertIn("does not exist", err)
        code, out, err = self.run_cli(example("result-completed.json"), "--input", os.path.join(self.dir, "absent.json"))
        self.assertEqual(code, 2)
        code, out, err = self.run_cli(example("result-completed.json"), "--bogus")
        self.assertEqual(code, 2)

    def test_exit_4_schema_failure(self):
        doc = testlib.load_json(example("result-completed.json"))
        del doc["run"]["verifier"]
        path = os.path.join(self.dir, "bad.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        code, out, err = self.run_cli(path)
        self.assertEqual(code, 4)
        got = json.loads(out)
        self.assertFalse(got["ok"]); self.assertTrue(got["schema"]); self.assertEqual(got["semantic"], [])
        self.assertTrue(all(s["reason"] == "skipped: schema failed" for s in got["skipped"]))
        with open(path, "w") as fh:
            fh.write("{not json")
        code, out, err = self.run_cli(path)
        self.assertEqual(code, 4)
        self.assertIn("not readable JSON", json.loads(out)["schema"][0]["message"])

    def test_exit_4_semantic_failure(self):
        doc = testlib.load_json(example("result-completed.json"))
        doc["still_open"] = ["MAJOR · src/other.ts:1 · something else · fix it"]
        path = os.path.join(self.dir, "sem.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        code, out, _ = self.run_cli(path)
        self.assertEqual(code, 4)
        got = json.loads(out)
        self.assertEqual(got["schema"], [])
        self.assertEqual({f["id"] for f in got["semantic"]}, {"V5"})

    def test_strict_counts_skips(self):
        code, out, _ = self.run_cli(example("result-completed.json"), "--input", example("input-caller.json"), "--strict")
        self.assertEqual(code, 4)
        got = json.loads(out)
        self.assertFalse(got["ok"]); self.assertEqual(got["semantic"], []); self.assertTrue(got["skipped"])

    def test_strict_with_run_dir_never_passes_a_violated_run(self):
        """Finding 3: with --run-dir supplied, V12's cancelled-flags part is still a skip, so --strict exits 4."""
        doc = violated(testlib.load_json(example("result-completed.json")))
        path = os.path.join(self.dir, "violated.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        code, out, _ = self.run_cli(path, "--run-dir", self.dir)
        self.assertEqual(code, 0, "the result-only part of V12 holds: no card moved, no status line, not_clear")
        got = json.loads(out)
        self.assertEqual(got["semantic"], [])
        self.assertIn({"id": "V12", "reason": V12_SKIP}, got["skipped"])
        code, out, _ = self.run_cli(path, "--run-dir", self.dir, "--strict")
        self.assertEqual(code, 4)
        got = json.loads(out)
        self.assertFalse(got["ok"])
        self.assertIn({"id": "V12", "reason": V12_SKIP}, got["skipped"])

    def test_help(self):
        code, out, _ = self.run_cli("--help")
        self.assertEqual(code, 0)
        for phrase in ("--input", "--run-dir", "--strict", "example", "side effects", "exit"):
            self.assertIn(phrase, out.lower() if phrase == "exit" else out)
        # E8-A4: the exit rules for a missing and a non-JSON result file, and --skill-root as a test-only option
        flat = " ".join(out.split())  # argparse wraps the option help across lines
        self.assertIn("test only: load references from DIR instead of the script's own skill root", flat)
        self.assertIn("missing: exit 2; present but not JSON: exit 4 with the parse error inside schema[]", flat)
        self.assertIn("2 usage (a result file that does not exist", flat)
        with open(os.path.join(testlib.SCRIPTS, "validate-result.py"), encoding="utf-8") as fh:
            docstring = fh.read()
        for phrase in ("exit\n4, with the parse error as the one entry inside schema[]", "does not exist is a usage error: exit 2"):
            self.assertIn(phrase, docstring, phrase)

    def test_missing_reference_exits_1(self):
        root = os.path.join(self.dir, "skill-root")
        shutil.copytree(testlib.SKILL, root, ignore=shutil.ignore_patterns("tests", "__pycache__", "examples"))
        os.remove(os.path.join(root, "references", "result.schema.json"))
        code, out, err = self.run_cli(example("result-completed.json"), "--skill-root", root)
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("reference unavailable: references/result.schema.json", err)


class SemanticChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e8-slice1-semantic-")
        cls.schemas = validate.load_schemas()
        cls.completed = testlib.load_json(example("result-completed.json"))
        cls.blocked = testlib.load_json(example("result-completed-blocked.json"))
        cls.caller = testlib.load_json(example("input-caller.json"))
        cls.direct = testlib.load_json(example("input-direct.json"))

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def run_checks(self, doc, **kw):
        return validate.run_semantic(doc, schemas=self.schemas, **kw)

    def ids(self, doc, **kw):
        return sorted({f["id"] for f in self.run_checks(doc, **kw)["semantic"]})

    def paths(self, doc, check_id, **kw):
        return [f["path"] for f in self.run_checks(doc, **kw)["semantic"] if f["id"] == check_id]

    def skips(self, doc, **kw):
        return {s["id"]: s["reason"] for s in self.run_checks(doc, **kw)["skipped"]}

    def mutated(self, base, fn):
        d = copy.deepcopy(base); fn(d); return d

    def test_examples_clean(self):
        self.assertEqual(self.ids(self.completed, input_doc=self.caller), [])
        self.assertEqual(self.ids(self.blocked), [])

    def test_stubs_report_their_reason(self):
        """Finding 7: each stub's skip reason is worded by what was supplied."""
        reasons = self.skips(self.completed)
        for cid in validate.CHECK_IDS:
            if cid not in SLICE1_CHECKS:
                self.assertIn(reasons.get(cid), ("skipped: needs run directory", "skipped: needs workspace"), cid)
        self.assertEqual(reasons["V16"], "skipped: needs input")
        self.assertEqual(reasons["V2"], "skipped: needs input")
        self.assertEqual(reasons["V1"], "skipped: needs run directory", "V1 without the input: key order against the checkpoint scope")
        self.assertEqual(reasons["V12"], V12_SKIP)
        run_dir_stubs, workspace_stubs = ("V3", "V4", "V7", "V8", "V13", "V14", "V18"), ("V6", "V17")
        self.assertEqual(set(run_dir_stubs) | set(workspace_stubs), set(validate.CHECK_IDS) - SLICE1_CHECKS)
        for cid in run_dir_stubs:
            self.assertEqual(reasons[cid], "skipped: needs run directory", cid)
        for cid in workspace_stubs:
            self.assertEqual(reasons[cid], "skipped: needs workspace", cid)
        # with the run directory and the workspace supplied, a stub says it is not implemented and what it would read
        reasons = self.skips(self.completed, run_dir=self.dir, workspace=self.dir)
        for cid in run_dir_stubs + ("V1",):
            self.assertRegex(reasons[cid], r"^skipped: not implemented until slice 2 \(needs the run directory's [^()]+\)$", (cid, reasons[cid]))
        for cid in workspace_stubs:
            self.assertRegex(reasons[cid], r"^skipped: not implemented until slice 2 \(needs the workspace's [^()]+\)$", (cid, reasons[cid]))
        self.assertEqual(reasons["V1"], "skipped: not implemented until slice 2 (needs the run directory's checkpoint scope for the key order)")
        self.assertEqual(reasons["V12"], V12_SKIP, "finding 3: the cancelled-flags part is a skip with the run directory too")
        # only the thing the stub needs changes its wording
        reasons = self.skips(self.completed, run_dir=self.dir)
        for cid in workspace_stubs:
            self.assertEqual(reasons[cid], "skipped: needs workspace", cid)
        reasons = self.skips(self.completed, workspace=self.dir)
        for cid in run_dir_stubs:
            self.assertEqual(reasons[cid], "skipped: needs run directory", cid)

    def test_v1(self):
        self.assertEqual(self.ids(self.mutated(self.completed, lambda d: d["checklist"].__setitem__("count", 3))), ["V1"])
        swapped = self.mutated(self.completed, lambda d: d["items"].reverse())
        self.assertIn("V1", self.ids(swapped, input_doc=self.caller), "explicit items: same keys, same order")
        self.assertNotIn("V1", self.ids(swapped), "without the input the order cannot be checked")
        # finding 2: two items sharing a location and claim are reported, not a TypeError from the message formatting
        dup = self.mutated(self.completed, lambda d: d["items"][1].__setitem__("claim", d["items"][0]["claim"]))
        found = [f for f in self.run_checks(dup)["semantic"] if f["id"] == "V1"]
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0]["path"], "/items")
        self.assertIn("two items share a location and claim", found[0]["message"])
        self.assertIn("src/export.ts:142", found[0]["message"])
        path = os.path.join(self.dir, "duplicate-key.json")
        with open(path, "w") as fh:
            json.dump(dup, fh)
        code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.dir)
        self.assertEqual(code, 4, "exit 4 with JSON on stdout, not exit 1 with nothing (stderr: %s)" % err)
        got = json.loads(out)
        self.assertFalse(got["ok"]); self.assertEqual(got["schema"], [])
        self.assertIn("V1", {f["id"] for f in got["semantic"]})

    def test_v2(self):
        """Amendment E8-A5: the workspace-free part for an explicit-items input (finding 9)."""
        self.assertEqual(self.paths(self.completed, "V2", input_doc=self.caller), [])
        self.assertNotIn("V2", self.skips(self.completed, input_doc=self.caller))
        wrong = self.mutated(self.completed, lambda d: d["items"][1].__setitem__("slice", "B"))
        self.assertEqual(self.paths(wrong, "V2", input_doc=self.caller), ["/items/1/slice"])
        self.assertEqual(self.paths(wrong, "V2"), [], "without the input the slices cannot be checked")
        defect = {"severity": "MAJOR", "location": {"file": "src/export.ts", "line": 150}, "claim": "broke: quoted commas double their quotes",
                  "failure_scenario": "export a title with a comma; the cell carries four quote marks", "source": "fix_introduced", "charged_to_slice": "A"}
        charged = self.mutated(self.completed, lambda d: d.__setitem__("new_defects", [dict(defect)]))
        self.assertEqual(self.paths(charged, "V2", input_doc=self.caller), [], "charged to a slice the input carries")
        none = self.mutated(self.completed, lambda d: d.__setitem__("new_defects", [dict(defect, charged_to_slice="none")]))
        self.assertEqual(self.paths(none, "V2", input_doc=self.caller), [], "charged to none")
        other = self.mutated(self.completed, lambda d: d.__setitem__("new_defects", [dict(defect, charged_to_slice="Z")]))
        self.assertEqual(self.paths(other, "V2", input_doc=self.caller), ["/new_defects/0/charged_to_slice"])
        # an item the input does not carry is V1's finding, not V2's
        renamed = self.mutated(self.completed, lambda d: d["items"][1].__setitem__("claim", "another claim"))
        self.assertIn("V1", self.ids(renamed, input_doc=self.caller))
        self.assertEqual(self.paths(renamed, "V2", input_doc=self.caller), [])
        # a build_doc input needs the workspace (slice 2)
        self.assertEqual(self.skips(self.completed, input_doc=self.direct)["V2"], "skipped: needs workspace")
        self.assertEqual(self.skips(self.completed, input_doc=self.direct, workspace=self.dir)["V2"],
                         "skipped: not implemented until slice 2 (needs the workspace's build doc and its slices)")

    def test_v5(self):
        self.assertIn("V5", self.ids(self.mutated(self.completed, lambda d: d.__setitem__("still_open", []))))
        extra = self.mutated(self.completed, lambda d: d["still_open"].append("MINOR · src/x.ts:1 · noise · none"))
        self.assertIn("V5", self.ids(extra))
        # a waived not_fixed item leaves the open set; a new defect joins it
        waived = self.mutated(self.completed, lambda d: (d["items"][1].__setitem__("waived", {"date": "2026-09-20", "quoted_words": "waive it"}), d.__setitem__("still_open", []), d.__setitem__("result", "all_clear"), d["cards"][0].__setitem__("after", "signed off")))
        self.assertEqual(self.ids(waived), [])
        defect = self.mutated(self.blocked, lambda d: d["still_open"].pop(2))
        self.assertIn("V5", self.ids(defect), "the new defect needs its line")

    def test_v9(self):
        bad = self.mutated(self.completed, lambda d: d["items"][0]["adjudication"].__setitem__("driver_action", "downgraded"))
        self.assertIn("V9", self.ids(bad))
        wrote = self.mutated(self.completed, lambda d: d["items"][0]["adjudication"].__setitem__("session_wrote_fix", True))
        self.assertIn("V9", self.ids(wrote), "item and run disagree on session_wrote_fix")
        upgraded = self.mutated(self.completed, lambda d: (d["items"][1].update({"disposition": "fixed"}), d["items"][1].pop("reason"), d["items"][1]["adjudication"].update({"driver_action": "upgraded", "upgrade_evidence": "x", "session_wrote_fix": True}), d["run"].__setitem__("session_wrote_fix", True)))
        self.assertIn("V9", self.ids(upgraded), "E8-13: never upgraded under session_wrote_fix")

    def test_v10(self):
        self.assertIn("V10", self.ids(self.mutated(self.completed, lambda d: d.__setitem__("result", "not_clear"))))
        self.assertIn("V10", self.ids(self.mutated(self.completed, lambda d: d.__setitem__("result", "all_clear"))))
        violated = self.mutated(self.completed, lambda d: d.__setitem__("boundary_violations", ["wrote src/x.ts"]))
        self.assertIn("V10", self.ids(violated), "violations force not_clear")

    def test_v11(self):
        self.assertIn("V11", self.ids(self.mutated(self.completed, lambda d: d["items"][0]["verification"].__setitem__("blocked", "x"))))
        self.assertIn("V11", self.ids(self.mutated(self.completed, lambda d: d["items"][0]["verification"].__setitem__("missing", "x"))))

    def test_v12(self):
        """One assertion per sub-check (finding 12): a moved card, a written status line, a promoted result."""
        frozen = violated(self.completed)
        self.assertEqual(frozen["cards"][0]["after"], frozen["cards"][0]["before"])
        self.assertEqual([w["kind"] for w in frozen["records_written"] if w["kind"] == "status_line"], [])
        self.assertNotIn("V12", self.ids(frozen))
        moved = self.mutated(frozen, lambda d: d["cards"][0].__setitem__("after", "signed off"))
        self.assertEqual(self.paths(moved, "V12"), ["/cards/0"], "a card moved beside a violation")
        written = self.mutated(frozen, lambda d: d["records_written"].append({"kind": "status_line", "path": "docs/plans/2026-09-18-widget-export.md", "appended": False}))
        self.assertEqual(self.paths(written, "V12"), ["/records_written/%d" % (len(frozen["records_written"]))], "a status line written beside a violation")
        promoted = self.mutated(frozen, lambda d: d.__setitem__("result", "partial"))
        self.assertEqual(self.paths(promoted, "V12"), ["/result"], "a result other than not_clear beside a violation")
        clean = self.mutated(self.completed, lambda d: d.__setitem__("boundary_violations", []))
        self.assertEqual(self.paths(clean, "V12"), [], "no violation, nothing to hold")

    def test_v12_cancelled_flags_always_skipped(self):
        """Finding 3: until slice 2 reads the receipt, the cancelled-flags part is a skip whether or not a run directory was given."""
        for doc in (self.completed, violated(self.completed)):
            for kw in ({}, {"run_dir": self.dir}, {"run_dir": self.dir, "workspace": self.dir}):
                self.assertEqual(self.skips(doc, **kw).get("V12"), V12_SKIP, kw)
        # the result-only part keeps running beside the skip
        moved = self.mutated(violated(self.completed), lambda d: d["cards"][0].__setitem__("after", "signed off"))
        got = self.run_checks(moved, run_dir=self.dir)
        self.assertEqual([f["path"] for f in got["semantic"] if f["id"] == "V12"], ["/cards/0"])
        self.assertIn({"id": "V12", "reason": V12_SKIP}, got["skipped"])

    def test_v15(self):
        stopped = testlib.load_json(example("result-stopped.json"))
        listed = self.mutated(stopped, lambda d: d["records_written"].append({"kind": "punch_list_block", "path": "docs/x.md", "appended": True}))
        self.assertIn("V15", self.ids(listed))
        envelope = testlib.load_json(example("result-invalid-input-envelope.json"))
        listed = self.mutated(envelope, lambda d: d.__setitem__("records_written", [{"kind": "run_artifact", "path": "/tmp/x", "appended": False}]))
        self.assertIn("V15", self.ids(listed), "a status that never reached a run directory lists nothing")

    def test_v16(self):
        bad_input = self.mutated(self.caller, lambda d: d["invocation"].__setitem__("harness", "codex-cli 0.154.0"))
        self.assertIn("V16", self.ids(self.completed, input_doc=bad_input), "run block present while the input fails the schema")
        envelope = testlib.load_json(example("result-invalid-input-envelope.json"))
        self.assertNotIn("V16", self.ids(envelope, input_doc=bad_input))
        self.assertIn("V16", self.ids(envelope, input_doc=self.caller), "no run block while the input validates")


if __name__ == "__main__":
    unittest.main()
