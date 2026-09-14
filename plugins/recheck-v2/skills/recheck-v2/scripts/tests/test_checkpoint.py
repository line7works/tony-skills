"""recheck_core.checkpoint: section 11 verdicts on every C fixture (C-continuation/CASES.md facts),
the binding hash (E8-9), the tolerated state (E8-15), writes with log-before-rename."""
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import checkpoint as cpmod, inputs, validate  # noqa: E402

# C-continuation/CASES.md, per case: the integrity facts stated under "Planted facts".
VALID = ("C2-01", "C3-01", "C3-02", "C3-03", "C4-04", "C4-08", "C1-01")
# C4-01 "recomputing the digest ... yields a different value"; C4-02 "the checkpoint's (seq, self) matches no log line";
# C4-03 "the line before that ... differs from the checkpoint's prev"; C4-06 "(4, <new>) matches no log line";
# C4-07 "the checkpoint's prev does not equal the line before its own" beside an announced write (E8-15);
# C4-09 "the seq column reads 0, 1, 3".
CORRUPT_STEP2 = {"C4-01": "does not recompute", "C4-02": "ahead of its log", "C4-03": "not the log line before",
                 "C4-06": "ahead of its log", "C4-07": "corrupted earlier line", "C4-09": "gap or a repeated seq"}
# C4-05: item 0's result lacks adjudication, so the checkpoint fails its schema (step 1);
# C4-10: no checkpoint.json; C4-11: json.loads raises.
CORRUPT_STEP1 = {"C4-05": "fails its schema", "C4-10": "does not exist", "C4-11": "does not parse"}
# C5-01: the last line announces seq one past the checkpoint's and prev equals the line before its own.
TOLERATED = ("C5-01",)


class Verdicts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = dict(testlib.lane_cases("C-continuation"))
        cls.schemas = validate.load_schemas()

    def verdict(self, prefix):
        for cid, cdir in self.cases.items():
            if cid.startswith(prefix):
                return cpmod.read_and_verify(os.path.join(cdir, "run"), self.schemas), cdir
        raise AssertionError(prefix)

    def test_every_case_has_a_verdict(self):
        expected = set(VALID) | set(CORRUPT_STEP2) | set(CORRUPT_STEP1) | set(TOLERATED)
        got = set(c.rsplit("-", 1)[0][:5] for c in self.cases)
        self.assertEqual(got, expected, "every C case is classified by this suite")

    def test_valid(self):
        for prefix in VALID:
            v, _ = self.verdict(prefix)
            self.assertTrue(v["ok"], (prefix, v["reason"]))
            self.assertFalse(v["tolerated"], prefix)

    def test_corrupt_step2(self):
        for prefix, needle in CORRUPT_STEP2.items():
            v, _ = self.verdict(prefix)
            self.assertFalse(v["ok"], prefix)
            self.assertEqual(v["step"], 2, (prefix, v["reason"]))
            self.assertIn(needle, v["reason"], (prefix, v["reason"]))

    def test_corrupt_step1(self):
        for prefix, needle in CORRUPT_STEP1.items():
            v, _ = self.verdict(prefix)
            self.assertFalse(v["ok"], prefix)
            self.assertEqual(v["step"], 1, (prefix, v["reason"]))
            self.assertIn(needle, v["reason"], (prefix, v["reason"]))

    def test_tolerated(self):
        v, cdir = self.verdict("C5-01")
        self.assertTrue(v["ok"]); self.assertTrue(v["tolerated"]); self.assertIn("seq 4", v["reason"])
        self.assertEqual(len(cpmod.read_log(os.path.join(cdir, "run", "checkpoint.log"))), 5)

    def test_binding_hash_facts(self):
        """C CASES.md: C2-01's input_sha256 equals the binding value of the resume input; C3-02's resume input
        minus invocation alone hashes differently, minus both removals equals the stored value; C3-03's stored
        original input minus invocation alone differs, its resume input hashes to the stored value; C4-04's
        resume input hashes to a different value (target differs); C4-08's binding holds (the run id is outside it)."""
        for prefix in ("C2-01", "C3-02", "C3-03", "C4-08"):
            v, cdir = self.verdict(prefix)
            inp = testlib.load_json(os.path.join(cdir, "input.json"))
            self.assertEqual(inputs.binding_hash(inp), v["doc"]["input_sha256"], prefix)
        v, cdir = self.verdict("C3-02")
        inp = testlib.load_json(os.path.join(cdir, "input.json"))
        only_invocation = {k: val for k, val in inp.items() if k != "invocation"}
        from recheck_core import canon
        self.assertNotEqual(canon.sha256_hex(canon.canonical_json(only_invocation)), v["doc"]["input_sha256"])
        v, cdir = self.verdict("C3-03")
        saved = testlib.load_json(os.path.join(cdir, "run", "resolved-input.json"))
        self.assertIn("extra_continuation", saved["authorization"])
        self.assertEqual(inputs.binding_hash(saved), v["doc"]["input_sha256"])
        v, cdir = self.verdict("C4-04")
        self.assertNotEqual(inputs.binding_hash(testlib.load_json(os.path.join(cdir, "input.json"))), v["doc"]["input_sha256"])

    def test_u1_seeded_checkpoint_is_valid(self):
        """VXUM CASES.md, U1-01: seq 0, prev null, the log's only line; the digest recomputes."""
        for cid, cdir in testlib.lane_cases("VXUM-verifier-execution"):
            if cid.startswith("U1-01"):
                v = cpmod.read_and_verify(os.path.join(cdir, "run"), self.schemas)
                self.assertTrue(v["ok"], v["reason"]); self.assertEqual(v["doc"]["integrity"]["seq"], 0)


class Writes(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e8-slice2-cp-")
        self.schemas = validate.load_schemas()

    def tearDown(self):
        testlib.rmtree(self.dir)

    def test_chain_and_tolerated_drop(self):
        cp_doc = testlib.load_json(os.path.join(testlib.EX, "checkpoint-partial.json"))
        cp_doc.pop("integrity")
        cp = cpmod.Checkpoint.new(self.dir, cp_doc, self.schemas)
        cp.doc["phase"] = "recording"
        cp.save()
        v = cpmod.read_and_verify(self.dir, self.schemas)
        self.assertTrue(v["ok"]); self.assertEqual(v["doc"]["integrity"]["seq"], 1); self.assertFalse(v["tolerated"])
        # announce a write that never lands (the one tolerated state), then drop it
        with open(cp.log_path, "a") as fh:
            fh.write("2 " + "a" * 64 + "\n")
        v = cpmod.read_and_verify(self.dir, self.schemas)
        self.assertTrue(v["ok"]); self.assertTrue(v["tolerated"])
        cpmod.drop_last_log_line(cp.log_path)
        self.assertEqual(len(cpmod.read_log(cp.log_path)), 2)
        cp.save()
        v = cpmod.read_and_verify(self.dir, self.schemas)
        self.assertTrue(v["ok"]); self.assertEqual(v["doc"]["integrity"]["seq"], 2); self.assertFalse(v["tolerated"])
        # a checkpoint rewritten without its log is corrupt (a re-signed checkpoint ahead of its log)
        cp.doc["integrity"]["seq"] = 3
        cp.doc["integrity"]["self"] = cpmod.self_hash(cp.doc)
        with open(cp.path, "wb") as fh:
            fh.write(cpmod.serialize(cp.doc))
        v = cpmod.read_and_verify(self.dir, self.schemas)
        self.assertFalse(v["ok"]); self.assertIn("ahead of its log", v["reason"])

    def test_invalid_document_never_lands(self):
        cp_doc = testlib.load_json(os.path.join(testlib.EX, "checkpoint-partial.json"))
        cp_doc.pop("integrity"); cp_doc["phase"] = "elsewhere"
        with self.assertRaises(cpmod.CheckpointError):
            cpmod.Checkpoint.new(self.dir, cp_doc, self.schemas)
        self.assertEqual(os.listdir(self.dir), [])

    def test_scan_order(self):
        for rel in ("zeta.txt", "verifier/raw.md", "verifier/b.log", "receipt.log", "receipt.json", "checkpoint.log", "checkpoint.json", "checklist.md", "input.json", "result.json", "chat.md"):
            path = os.path.join(self.dir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").close()
        got = [os.path.relpath(p, self.dir) for p in cpmod.scan_artifacts(self.dir)]
        self.assertEqual(got, ["input.json", "checklist.md", "checkpoint.json", "checkpoint.log", "verifier/b.log", "verifier/raw.md", "receipt.json", "receipt.log", "zeta.txt"])


if __name__ == "__main__":
    unittest.main()
