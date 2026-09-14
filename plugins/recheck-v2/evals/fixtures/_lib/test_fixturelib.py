"""Unit tests for fixturelib (stdlib unittest; run from any directory with
`python3 -m unittest /path/to/test_fixturelib.py` or `python3 -m unittest discover -s <this dir>`).

The checkpoint checks port the integrity logic of
skills/recheck-v2/references/examples/validate-examples.py (check_checkpoint), with the
predecessor-link check the contract's Appendix B carries as item 11 added to the tolerated state.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fixturelib  # noqa: E402
from fixturelib import Fixture, canonical_json, identity_of, sha256_hex, tree_sha256  # noqa: E402

EXAMPLES = os.path.normpath(os.path.join(HERE, "..", "..", "..", "skills", "recheck-v2", "references", "examples"))

ITEM_RESULT = {
    "severity": "BLOCKER",
    "location": {"file": "src/widget/export.py", "line": 12},
    "claim": "CSV export writes unescaped commas inside quoted fields",
    "failure_scenario": "export a row whose title contains a comma; the produced CSV has one extra column",
    "slice": "A",
    "disposition": "fixed",
    "verification": {"method": "executed", "evidence": [{"kind": "command", "detail": "ran the export; three columns"}]},
    "adjudication": {"verifier_said": "fixed", "driver_action": "confirmed", "session_wrote_fix": False},
}


def check_checkpoint(cp, log_lines):
    """Port of validate-examples.py check_checkpoint: 'ok', 'repair', or the first defect."""
    for i, st in enumerate(cp["items"]):
        if st["state"] == "pending" and "result" in st:
            return "item %d: pending with a result" % i
        if st["state"] == "done" and not isinstance(st.get("result"), dict):
            return "item %d: done without a valid result" % i
        if st["state"] not in ("pending", "done"):
            return "item %d: unknown state" % i
    body = copy.deepcopy(cp)
    self_ = body["integrity"].pop("self")
    if hashlib.sha256(canonical_json(body)).hexdigest() != self_:
        return "self digest does not recompute"
    seq, prev = cp["integrity"]["seq"], cp["integrity"]["prev"]
    rows = [l.split() for l in log_lines if l.strip()]
    if [int(r[0]) for r in rows] != list(range(len(rows))):
        return "log has a gap or a repeated seq"
    if rows and rows[-1] == [str(seq), self_]:
        if seq == 0:
            return "ok" if prev is None and len(rows) == 1 else "prev must be null at seq 0"
        return "ok" if len(rows) >= 2 and rows[-2][1] == prev else "prev is not the line before"
    if len(rows) >= 2 and rows[-2] == [str(seq), self_] and int(rows[-1][0]) == seq + 1:
        # carried item 11: the tolerated state also needs the predecessor link
        if seq == 0:
            return "repair" if prev is None else "prev must be null at seq 0"
        return "repair" if len(rows) >= 3 and rows[-3][1] == prev else "prev is not the line before"
    return "(seq, self) is not the log's last line"


def base_doc():
    return {
        "protocol_version": 1,
        "run_id": "x-run",
        "phase": "adjudicating",
        "items": [{"state": "done", "retries": 0, "result": copy.deepcopy(ITEM_RESULT)},
                  {"state": "pending", "retries": 0}],
        "continuations": 0,
    }


def build_widget(fx, extra=None):
    """A representative case: base commit with a defect, fix commit, build doc, input, manifest."""
    fx.checks = ["F1", "X1"]
    fx.skeleton()
    fx.write("src/widget/export.py", "def cell(value):\n    return str(value)\n")
    doc = fx.build_doc("widget-export", "2026-09-18", "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"}],
                       {"A": "Export rows as CSV."})
    fx.review_block(doc, "2026-09-19", "A", [{"severity": "BLOCKER", "file": "src/widget/export.py", "line": 2,
                                              "claim": "commas are not quoted",
                                              "scenario": "export a title with a comma; one extra column"}])
    fx.commit("Slice A review", fixturelib.GIT_BASE_DATE)
    fx.write("src/widget/export.py", "def cell(value):\n    s = str(value)\n    return '\"%s\"' % s if ',' in s else s\n")
    fx.commit("Quote commas in cells", fixturelib.GIT_FIX_DATE)
    fx.write_input({"protocol_version": 1, "invocation": {"mode": "interactive", "caller": "direct"},
                    "target": {"build_doc": doc, "slice": "A"}})
    if extra:
        extra(fx)
    return fx.manifest(notes="test case")


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fixturelib-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def out(self, name):
        return os.path.join(self.tmp, name)


class TestCanonical(unittest.TestCase):
    def test_canonical_json_sorted_compact_utf8(self):
        self.assertEqual(canonical_json({"b": 1, "a": "é"}), '{"a":"é","b":1}'.encode("utf-8"))

    def test_sha256_hex(self):
        self.assertEqual(sha256_hex(b""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_example_checkpoint_self_recomputes(self):
        path = os.path.join(EXAMPLES, "checkpoint-partial.json")
        if not os.path.exists(path):
            self.skipTest("examples folder not beside the evals tree")
        with open(path, "r", encoding="utf-8") as fh:
            cp = json.load(fh)
        with open(os.path.join(EXAMPLES, "checkpoint-partial.log"), "r", encoding="utf-8") as fh:
            log = fh.read().splitlines()
        body = copy.deepcopy(cp)
        self_ = body["integrity"].pop("self")
        self.assertEqual(sha256_hex(canonical_json(body)), self_)
        self.assertEqual(check_checkpoint(cp, log), "ok")


class TestDeterminism(TempDirTest):
    def test_two_builds_identical(self):
        m1 = fixturelib.build_case(self.out("one"), "F1-01-fixed-clean", "F1-fixed-defect", [], build_widget)
        m2 = fixturelib.build_case(self.out("two"), "F1-01-fixed-clean", "F1-fixed-defect", [], build_widget)
        self.assertEqual(m1["identity"]["commit"], m2["identity"]["commit"])
        self.assertEqual(m1["tree_sha256"], m2["tree_sha256"])
        self.assertEqual(m1["identity"], m2["identity"])
        self.assertFalse(m1["identity"]["dirty"])
        self.assertEqual(m1["checks"], ["F1", "X1"])
        with open(os.path.join(self.out("one"), "F1-01-fixed-clean", "input.json"), "r", encoding="utf-8") as fh:
            inp = json.load(fh)
        self.assertEqual(inp["invocation"]["run_id"], "F1-01-fixed-clean-run")
        self.assertTrue(inp["invocation"]["run_dir"].startswith(os.path.abspath(self.out("one"))))
        self.assertTrue(inp["workspace"].endswith("/F1-01-fixed-clean/workspace"))

    def test_rebuild_into_same_out_is_idempotent(self):
        m1 = fixturelib.build_case(self.out("one"), "F1-01-fixed-clean", "F1-fixed-defect", [], build_widget)
        m2 = fixturelib.build_case(self.out("one"), "F1-01-fixed-clean", "F1-fixed-defect", [], build_widget)
        self.assertEqual(m1, m2)

    def test_file_modes_and_trailing_newline(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        fx.write("a.txt", "no newline")
        fx.write("bin/tool.py", "print(1)\n", executable=True)
        with open(os.path.join(fx.workspace, "a.txt"), "rb") as fh:
            self.assertEqual(fh.read(), b"no newline\n")
        self.assertEqual(os.stat(os.path.join(fx.workspace, "a.txt")).st_mode & 0o777, 0o644)
        self.assertEqual(os.stat(os.path.join(fx.workspace, "bin/tool.py")).st_mode & 0o777, 0o755)

    def test_tree_sha256_factors_out_the_out_dir_and_manifest(self):
        m1 = fixturelib.build_case(self.out("one"), "c", "lane", [], build_widget)
        case = os.path.join(self.out("one"), "c")
        self.assertEqual(tree_sha256(case, self.out("one")), m1["tree_sha256"])
        with open(os.path.join(case, "manifest.json"), "a") as fh:
            fh.write("\n")
        self.assertEqual(tree_sha256(case, self.out("one")), m1["tree_sha256"])
        with open(os.path.join(case, "run", "extra.txt"), "w") as fh:
            fh.write("x\n")
        self.assertNotEqual(tree_sha256(case, self.out("one")), m1["tree_sha256"])


class TestIdentity(TempDirTest):
    def test_six_fields_clean(self):
        m = fixturelib.build_case(self.out("one"), "c", "lane", [], build_widget)
        ident = m["identity"]
        self.assertEqual(sorted(ident), ["commit", "dirty", "submodules", "tracked_diff_sha256", "untracked", "untracked_sha256"])
        self.assertRegex(ident["commit"], "^[0-9a-f]{40}$")
        self.assertFalse(ident["dirty"])
        self.assertEqual(ident["tracked_diff_sha256"], fixturelib.EMPTY_SHA256)
        self.assertEqual(ident["untracked"], [])
        self.assertEqual(ident["untracked_sha256"], fixturelib.EMPTY_SHA256)
        self.assertEqual(ident["submodules"], [])
        self.assertEqual(identity_of(os.path.join(self.out("one"), "c", "workspace")), ident)

    def test_staged_change(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        build_widget(fx)
        clean = fx.identity()
        fx.write("README.md", "# widget\n\nchanged\n")
        fx.stage("README.md")
        ident = fx.identity()
        self.assertTrue(ident["dirty"])
        self.assertNotEqual(ident["tracked_diff_sha256"], clean["tracked_diff_sha256"])
        self.assertEqual(ident["commit"], clean["commit"])
        self.assertEqual(ident["untracked"], [])

    def test_binary_change(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        fx.skeleton()
        fx.write_bytes("assets/logo.png", b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 2)
        fx.commit("Add logo", fixturelib.GIT_BASE_DATE)
        clean = fx.identity()
        fx.write_bytes("assets/logo.png", b"\x89PNG\r\n\x1a\n" + bytes(reversed(range(256))) * 2)
        ident = fx.identity()
        self.assertTrue(ident["dirty"])
        self.assertNotEqual(ident["tracked_diff_sha256"], clean["tracked_diff_sha256"])
        # the same change twice hashes the same: the diff bytes are deterministic
        self.assertEqual(ident["tracked_diff_sha256"], fx.identity()["tracked_diff_sha256"])

    def test_untracked_content_change(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        build_widget(fx)
        fx.untracked("notes.txt", "first\n")
        a = fx.identity()
        self.assertTrue(a["dirty"])
        self.assertEqual(a["untracked"], ["notes.txt"])
        expected = sha256_hex(("notes.txt\0" + sha256_hex(b"first\n") + "\n").encode("utf-8"))
        self.assertEqual(a["untracked_sha256"], expected)
        self.assertEqual(a["tracked_diff_sha256"], fixturelib.EMPTY_SHA256)
        fx.untracked("notes.txt", "second\n")
        b = fx.identity()
        self.assertEqual(b["untracked"], a["untracked"])
        self.assertNotEqual(b["untracked_sha256"], a["untracked_sha256"])

    def test_ignored_files_excluded(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        build_widget(fx)
        fx.write("src/widget/__pycache__/x.pyc", "junk\n")
        ident = fx.identity()
        self.assertFalse(ident["dirty"])
        self.assertEqual(ident["untracked"], [])

    def test_submodule(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        build_widget(fx)
        fx.add_submodule("vendor-lib")
        ident = fx.identity()
        self.assertEqual(ident["submodules"], ["vendor-lib"])
        self.assertFalse(ident["dirty"])
        self.assertTrue(os.path.exists(os.path.join(fx.workspace, ".gitmodules")))
        with open(os.path.join(fx.workspace, ".gitmodules"), "r", encoding="utf-8") as fh:
            self.assertIn("../_sub/vendor-lib", fh.read())
        m1 = fx.manifest()
        fx2 = Fixture(self.out("two"), "c", "lane", [])
        build_widget(fx2)
        fx2.add_submodule("vendor-lib")
        m2 = fx2.manifest()
        self.assertEqual(m1["identity"], m2["identity"])
        self.assertEqual(m1["tree_sha256"], m2["tree_sha256"])


class TestRecords(TempDirTest):
    def test_build_doc_and_ledger_shapes(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        fx.skeleton()
        doc = fx.build_doc("widget-export", "2026-09-18", "Widget export",
                           [{"name": "A", "title": "CSV export", "status": "rejected"},
                            {"name": "B", "title": "JSON export", "status": "built"}], {"A": "Prose A."})
        self.assertEqual(doc, "docs/plans/2026-09-18-widget-export.md")
        fx.review_block(doc, "2026-09-19", "A", [{"severity": "BLOCKER", "file": "src/widget/export.py", "line": 42,
                                                  "claim": "c1", "scenario": "s1"}])
        fx.recheck_block(doc, "2026-09-20", "A", [{"severity": "BLOCKER", "file": "src/widget/export.py", "line": 42,
                                                   "claim": "c1", "disposition": "not fixed", "how": "ran it"}])
        fx.waiver_line(doc, "2026-09-20", "BLOCKER", "src/widget/export.py", 42, "c1", 'waive "it"')
        fx.waiver_line(doc, "2026-09-20", "MINOR", "src/widget/export.py", 50, "c2")
        fx.reopen_line(doc, "2026-09-21", "src/widget/export.py", 42, "c1", "reopen it")
        fx.raw_ledger_line(doc, "- legacy · text")
        fx.set_status(doc, "A", "signed off")
        text = fx.read(doc)
        expected = (
            "# Widget export\n\n"
            "## Slice A — CSV export\nStatus: signed off\n\nProse A.\n\n"
            "## Slice B — JSON export\nStatus: built\n\n"
            "## Punch list\n\n"
            "### 2026-09-19 — review: Slice A\n"
            "- BLOCKER · src/widget/export.py:42 · c1 · s1 · Slice A\n\n"
            "### 2026-09-20 — recheck: Slice A\n"
            "- BLOCKER · src/widget/export.py:42 · (c1) · not fixed · ran it\n"
            "- WAIVED (per user) · 2026-09-20 · BLOCKER · src/widget/export.py:42 · c1 · \"waive 'it'\"\n"
            "- WAIVED (per user) · 2026-09-20 · MINOR · src/widget/export.py:50 · c2\n"
            "- REOPENED (per user) · 2026-09-21 · src/widget/export.py:42 · c1 · \"reopen it\"\n"
            "- legacy · text\n"
        )
        self.assertEqual(text, expected)

    def test_ledger_tail_stays_inside_punch_list_section(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        fx.skeleton()
        doc = fx.build_doc("t", "2026-09-18", "T", [{"name": "A", "title": "x", "status": "rejected"}])
        fx.write(doc, fx.read(doc) + "\n## Notes\n\nafter\n")
        fx.raw_ledger_line(doc, "- one")
        fx.raw_ledger_line(doc, "- two")
        self.assertEqual(fx.read(doc).split("## Punch list\n")[1], "- one\n- two\n\n## Notes\n\nafter\n")

    def test_review_sheet_and_verdict_doc(self):
        fx = Fixture(self.out("one"), "c", "lane", [])
        fx.review_sheet({"lint": "on", "types": False}, ["BLOCKER: a regression in shipped output"], ["run the export smoke test"])
        self.assertEqual(fx.read("REVIEW.md"),
                         "# Review sheet\n\n## Passes\n- lint: on\n- types: off\n\n## Severity bar\n"
                         "- BLOCKER: a regression in shipped output\n\n## Repo-specific checks\n- run the export smoke test\n")
        rel = fx.verdict_doc("2026-09-19", "widget-export", "A", "# Signoff\n")
        self.assertEqual(rel, "docs/reviews/2026-09-19-signoff-widget-export-a.md")
        self.assertEqual(fx.read(rel), "# Signoff\n")


class TestCheckpoint(TempDirTest):
    def fx(self):
        return Fixture(self.out("one"), "c", "lane", [])

    def read_state(self, fx, name="checkpoint"):
        with open(os.path.join(fx.run_dir, name + ".json"), "r", encoding="utf-8") as fh:
            cp = json.load(fh)
        with open(os.path.join(fx.run_dir, name + ".log"), "r", encoding="utf-8") as fh:
            log = fh.read().splitlines()
        return cp, log

    def chain(self, fx, n=3):
        hashes = []
        for i in range(n):
            d = base_doc()
            d["continuations"] = i
            hashes.append(fx.checkpoint(d))
        return hashes

    def test_valid_chain(self):
        fx = self.fx()
        hashes = self.chain(fx)
        cp, log = self.read_state(fx)
        self.assertEqual(check_checkpoint(cp, log), "ok")
        self.assertEqual(cp["integrity"], {"seq": 2, "prev": hashes[1], "self": hashes[2]})
        self.assertEqual(log, ["%d %s" % (i, h) for i, h in enumerate(hashes)])
        body = copy.deepcopy(cp)
        del body["integrity"]["self"]
        self.assertEqual(sha256_hex(canonical_json(body)), hashes[2])
        self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "checkpoint.json.tmp")))

    def test_first_write_prev_null(self):
        fx = self.fx()
        fx.checkpoint(base_doc())
        cp, log = self.read_state(fx)
        self.assertEqual(cp["integrity"]["seq"], 0)
        self.assertIsNone(cp["integrity"]["prev"])
        self.assertEqual(check_checkpoint(cp, log), "ok")

    def test_bad_digest(self):
        fx = self.fx()
        self.chain(fx)
        cp, _ = self.read_state(fx)
        cp["items"][0]["result"]["disposition"] = "not_fixed"
        fx.run_file("checkpoint.json", json.dumps(cp, indent=2))
        cp, log = self.read_state(fx)
        self.assertEqual(check_checkpoint(cp, log), "self digest does not recompute")

    def test_checkpoint_ahead_of_log(self):
        fx = self.fx()
        self.chain(fx)
        fx.checkpoint(base_doc(), log=False)
        cp, log = self.read_state(fx)
        self.assertEqual(cp["integrity"]["seq"], 3)
        self.assertEqual(len(log), 3)
        self.assertEqual(check_checkpoint(cp, log), "(seq, self) is not the log's last line")

    def test_broken_chain(self):
        fx = self.fx()
        self.chain(fx)
        fx.checkpoint(base_doc(), prev="0" * 64)
        cp, log = self.read_state(fx)
        self.assertEqual(check_checkpoint(cp, log), "prev is not the line before")

    def test_log_gap(self):
        fx = self.fx()
        self.chain(fx)
        fx.checkpoint(base_doc(), seq=5)
        cp, log = self.read_state(fx)
        self.assertEqual([l.split()[0] for l in log], ["0", "1", "2", "5"])
        self.assertEqual(check_checkpoint(cp, log), "log has a gap or a repeated seq")

    def test_resigned_ahead(self):
        fx = self.fx()
        hashes = self.chain(fx)
        cp, _ = self.read_state(fx)
        cp["items"][1] = {"state": "done", "retries": 0, "result": copy.deepcopy(ITEM_RESULT)}
        new_self = fx.checkpoint(cp, resign=True, seq=3, prev=hashes[2])
        cp, log = self.read_state(fx)
        self.assertEqual(cp["integrity"], {"seq": 3, "prev": hashes[2], "self": new_self})
        self.assertEqual(len(log), 3)
        self.assertEqual(check_checkpoint(cp, log), "(seq, self) is not the log's last line")

    def test_resign_after_edit_keeps_seq_and_log(self):
        fx = self.fx()
        self.chain(fx)
        cp, _ = self.read_state(fx)
        cp["items"][1]["retries"] = 1
        fx.checkpoint(cp, resign=True)
        cp2, log = self.read_state(fx)
        body = copy.deepcopy(cp2)
        del body["integrity"]["self"]
        self.assertEqual(sha256_hex(canonical_json(body)), cp2["integrity"]["self"])
        self.assertEqual(cp2["integrity"]["seq"], 2)
        self.assertEqual(len(log), 3)
        self.assertEqual(check_checkpoint(cp2, log), "(seq, self) is not the log's last line")

    def test_altered_item_state_stale_digest(self):
        fx = self.fx()
        self.chain(fx)
        cp, _ = self.read_state(fx)
        cp["items"][1]["result"] = copy.deepcopy(ITEM_RESULT)
        fx.run_file("checkpoint.json", json.dumps(cp, indent=2))
        cp, log = self.read_state(fx)
        self.assertEqual(check_checkpoint(cp, log), "item 1: pending with a result")

    def test_announced_never_landed_is_tolerated(self):
        fx = self.fx()
        hashes = self.chain(fx)
        # announce seq 3 in the log, then put the seq-2 document back as if the rename never landed
        fx.checkpoint(base_doc(), log=True)
        d = base_doc()
        d["continuations"] = 2
        back = fx.checkpoint(d, log=False, seq=2, prev=hashes[1])
        self.assertEqual(back, hashes[2])
        cp, log = self.read_state(fx)
        self.assertEqual(len(log), 4)
        self.assertEqual(check_checkpoint(cp, log), "repair")

    def test_corrupt_earlier_plus_announced(self):
        fx = self.fx()
        hashes = self.chain(fx)
        fx.checkpoint(base_doc(), log=True)
        d = base_doc()
        d["continuations"] = 2
        fx.checkpoint(d, log=False, seq=2, prev=hashes[1])
        cp, log = self.read_state(fx)
        log[1] = "1 " + "f" * 64
        self.assertEqual(check_checkpoint(cp, log), "prev is not the line before")

    def test_receipt_same_mechanism(self):
        fx = self.fx()
        doc = {"run_id": "c-run", "phase": "recording",
               "plan": [{"step": 1, "kind": "reopened_line", "target": "docs/plans/2026-09-18-t.md",
                         "before_sha256": "0" * 64, "after_sha256": "1" * 64}],
               "entries": [{"step": 1, "type": "intent"}]}
        h0 = fx.receipt(doc)
        doc2 = copy.deepcopy(doc)
        doc2["entries"].append({"step": 1, "type": "done", "observed_sha256": "1" * 64})
        h1 = fx.receipt(doc2)
        cp, log = self.read_state(fx, "receipt")
        self.assertEqual(cp["integrity"], {"seq": 1, "prev": h0, "self": h1})
        self.assertEqual(log, ["0 " + h0, "1 " + h1])
        body = copy.deepcopy(cp)
        del body["integrity"]["self"]
        self.assertEqual(sha256_hex(canonical_json(body)), h1)
        self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "checkpoint.log")))


class TestCli(TempDirTest):
    def setUp(self):
        super().setUp()
        self.script = os.path.join(self.tmp, "build.py")
        with open(self.script, "w", encoding="utf-8") as fh:
            fh.write(
                "import os, sys\n"
                "sys.path.insert(0, %r)\n"
                "import fixturelib\n"
                "def one(fx):\n"
                "    fx.checks = ['F1']\n"
                "    fx.skeleton()\n"
                "    fx.commit('Base', fixturelib.GIT_BASE_DATE)\n"
                "    fx.write_input({'protocol_version': 1, 'invocation': {'mode': 'interactive', 'caller': 'direct'},\n"
                "                    'target': {'build_doc': 'docs/plans/x.md', 'slice': 'A'}})\n"
                "    fx.manifest(notes='cli test')\n"
                "fixturelib.make_lane('T-lane', {'T-01-one': one, 'T-02-two': one})\n" % HERE)

    def run_cli(self, *args, **kw):
        env = dict(os.environ)
        env.update(kw.get("env", {}))
        cwd = kw.get("cwd", self.tmp)
        return subprocess.run([sys.executable, self.script] + list(args), cwd=cwd, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def test_help(self):
        p = self.run_cli("--help")
        self.assertEqual(p.returncode, 0)
        self.assertIn("--out", p.stdout)
        self.assertIn("--list", p.stdout)

    def test_list(self):
        p = self.run_cli("--list")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "T-01-one\nT-02-two\n")

    def test_json_from_another_cwd(self):
        out = self.out("built")
        p = self.run_cli("--out", out, "--json", cwd="/")
        self.assertEqual(p.returncode, 0, p.stderr)
        doc = json.loads(p.stdout)
        self.assertEqual(doc["lane"], "T-lane")
        self.assertEqual([c["case"] for c in doc["cases"]], ["T-01-one", "T-02-two"])
        for c in doc["cases"]:
            self.assertTrue(os.path.isdir(os.path.join(c["path"], "workspace", ".git")))
            self.assertRegex(c["tree_sha256"], "^[0-9a-f]{64}$")
        # the same case built into another out dir hashes the same (the out prefix is factored out)
        again = self.run_cli("--out", self.out("built2"), "--json", cwd="/")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual([c["tree_sha256"] for c in json.loads(again.stdout)["cases"]],
                         [c["tree_sha256"] for c in doc["cases"]])
        p2 = self.run_cli("--out", out, "--case", "T-01-one")
        self.assertEqual(p2.returncode, 0, p2.stderr)
        self.assertEqual(len(p2.stdout.splitlines()), 1)
        self.assertTrue(p2.stdout.startswith("T-01-one  "))

    def test_unknown_case_exit_2(self):
        p = self.run_cli("--out", self.out("x"), "--case", "T-99-nope")
        self.assertEqual(p.returncode, 2)
        self.assertIn("T-99-nope", p.stderr)
        self.assertEqual(p.stdout, "")

    def test_missing_out_exit_2(self):
        p = self.run_cli()
        self.assertEqual(p.returncode, 2)

    def test_git_missing_exit_3(self):
        empty = os.path.join(self.tmp, "emptybin")
        os.makedirs(empty)
        p = self.run_cli("--out", self.out("x"), env={"PATH": empty})
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn("git", p.stderr)
        self.assertEqual(p.stdout, "")


if __name__ == "__main__":
    unittest.main()


class OpaqueCaseDirTests(unittest.TestCase):
    """Ruling E7-18: --opaque names the case directory by a digest of the case id."""

    def test_opaque_name_is_stable_and_hides_the_case_id(self):
        import fixturelib as fl
        name = fl.opaque_case_name("F1-01-fixed-clean")
        self.assertEqual(name, fl.opaque_case_name("F1-01-fixed-clean"))
        self.assertEqual(len(name), 12)
        self.assertNotIn("fixed", name)
        self.assertNotEqual(name, fl.opaque_case_name("F1-02-regression"))

    def test_opaque_fixture_keeps_workspace_and_run_leaves(self):
        import tempfile, os
        import fixturelib as fl
        with tempfile.TemporaryDirectory() as out:
            fx = fl.Fixture(out, "S1-99-opaque-probe", "S1-colocated", ["S1"], opaque=True)
            self.assertEqual(os.path.basename(fx.case_dir), fl.opaque_case_name("S1-99-opaque-probe"))
            self.assertEqual(os.path.basename(fx.workspace), "workspace")
            self.assertEqual(os.path.basename(fx.run_dir), "run")
            self.assertNotIn("opaque-probe", fx.case_dir)
            fx.skeleton()
            fx.commit("Initial", "2026-09-19T09:00:00-07:00")
            fx.write_input({"protocol_version": 1, "target": {"build_doc": "docs/plans/x.md", "slice": "A"}})
            m = fx.manifest(notes="probe")
            self.assertEqual(m["case"], "S1-99-opaque-probe")
            fx2 = fl.Fixture(out, "S1-99-opaque-probe", "S1-colocated", ["S1"], opaque=True)
            fx2.skeleton()
            fx2.commit("Initial", "2026-09-19T09:00:00-07:00")
            fx2.write_input({"protocol_version": 1, "target": {"build_doc": "docs/plans/x.md", "slice": "A"}})
            m2 = fx2.manifest(notes="probe")
            self.assertEqual(m["tree_sha256"], m2["tree_sha256"])
