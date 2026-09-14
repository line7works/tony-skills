"""checkpoint.schema.json and receipt.schema.json against the seeded C and W fixtures.

The lanes are built once in setUpClass with the E7 generators into a temporary directory and
removed in tearDownClass. Every expectation is a CASES.md fact, cited on the assertion; the
answer key is never read. Set RECHECK_TEST_ALL_LANES=1 to also build every lane and check each
input.json against its manifest's input_validates (the E7 runner's step 2 does the same).
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import validate  # noqa: E402

# C-continuation/CASES.md, C4-05-altered-item-state: "item 0's result edited: the adjudication object
# is removed ... result.schema.json's item_result lists adjudication under required, so that result does
# not validate against the item definition."
EXPECTED_INVALID = {"C4-05-altered-item-state"}
# C-continuation/CASES.md, C4-11-unparseable-checkpoint: "json.loads on those bytes raises JSONDecodeError
# (the object is never closed)."
EXPECTED_UNPARSEABLE = {"C4-11-unparseable-checkpoint"}
# C-continuation/CASES.md, C4-10-missing-checkpoint: "no checkpoint.json exists under run/".
EXPECTED_ABSENT = {"C4-10-missing-checkpoint"}
# W-recording/CASES.md, "Run directory of a mid-transaction case": W2-01 to W2-05 pre-seed run/ with
# checkpoint.json, checkpoint.log, receipt.json, receipt.log; every other W case has an empty run/.
W_SEEDED = {"W2-01-between-steps", "W2-02-landed-without-done", "W2-03-between-two-status-lines",
            "W2-04-outside-edit", "W2-05-two-steps-same-target"}


class SeededRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = testlib.make_scratch("e8-slice1-seeded-")
        cls.lanes = list(testlib.LANES_WITH_SEEDED_RUNS)
        if os.environ.get("RECHECK_TEST_ALL_LANES") == "1":
            cls.lanes = sorted(d for d in os.listdir(testlib.FIXTURES)
                               if os.path.isfile(os.path.join(testlib.FIXTURES, d, "build.py")))
        for lane in cls.lanes:
            testlib.build_lane(lane, os.path.join(cls.out, lane))
        cls.schemas = validate.load_schemas()

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.out)

    def cases(self, lane):
        return [(os.path.basename(d), d) for d in testlib.case_dirs(self.out, lane)]

    def test_example_checkpoint_validates(self):
        doc = testlib.load_json(os.path.join(testlib.EX, "checkpoint-partial.json"))
        self.assertEqual(validate.validate_checkpoint(doc, self.schemas), [])

    def test_item_state_union(self):
        """Section 11: exactly {pending, retries} and {done, retries, result}; nothing else."""
        doc = testlib.load_json(os.path.join(testlib.EX, "checkpoint-partial.json"))
        bad = json.loads(json.dumps(doc)); bad["items"][1]["result"] = doc["items"][0]["result"]
        self.assertTrue(validate.validate_checkpoint(bad, self.schemas), "a pending item carrying a result")
        bad = json.loads(json.dumps(doc)); del bad["items"][0]["result"]
        self.assertTrue(validate.validate_checkpoint(bad, self.schemas), "a done item without a result")
        bad = json.loads(json.dumps(doc)); bad["items"][1]["note"] = "x"
        self.assertTrue(validate.validate_checkpoint(bad, self.schemas), "a pending item with another key")
        bad = json.loads(json.dumps(doc)); bad["items"][0]["state"] = "skipped"
        self.assertTrue(validate.validate_checkpoint(bad, self.schemas), "an unknown state")
        bad = json.loads(json.dumps(doc)); bad["scope"]["grants"]["extra_continuation"] = {"by": "user"}
        self.assertTrue(validate.validate_checkpoint(bad, self.schemas), "E8-10: no continuation slot")

    def test_seeded_checkpoints(self):
        seen = set()
        for lane in ("C-continuation", "W-recording"):
            for cid, cdir in self.cases(lane):
                path = os.path.join(cdir, "run", "checkpoint.json")
                if not os.path.exists(path):
                    self.assertTrue(cid in EXPECTED_ABSENT or (lane == "W-recording" and cid not in W_SEEDED),
                                    "%s: checkpoint.json unexpectedly absent" % cid)
                    continue
                seen.add(cid)
                with open(path, "rb") as fh:
                    raw = fh.read()
                try:
                    doc = json.loads(raw.decode("utf-8"))
                except ValueError:
                    self.assertIn(cid, EXPECTED_UNPARSEABLE, "%s: checkpoint.json does not parse" % cid)
                    continue
                self.assertNotIn(cid, EXPECTED_UNPARSEABLE, "%s parsed but CASES.md says it cannot" % cid)
                errs = validate.validate_checkpoint(doc, self.schemas)
                if cid in EXPECTED_INVALID:
                    self.assertTrue(errs, "%s: CASES.md says item 0's result lacks adjudication; the schema accepted it" % cid)
                    self.assertTrue(any(e["path"].startswith("/items/0") for e in errs), errs)
                else:
                    self.assertEqual(errs, [], "%s: a seeded checkpoint the schema must accept was rejected" % cid)
        self.assertTrue(EXPECTED_INVALID <= seen and W_SEEDED <= seen, seen)

    def test_seeded_receipts(self):
        found = set()
        for lane in ("C-continuation", "W-recording"):
            for cid, cdir in self.cases(lane):
                path = os.path.join(cdir, "run", "receipt.json")
                if not os.path.exists(path):
                    continue
                found.add(cid)
                doc = testlib.load_json(path)
                self.assertEqual(validate.validate_receipt(doc, self.schemas), [], "%s: receipt.json rejected" % cid)
                self.assertTrue(os.path.exists(os.path.join(cdir, "run", "receipt.log")), cid)
        # C-continuation/CASES.md: "No receipt.json, no receipt.log, no result.json" in the reference form.
        self.assertEqual(found, W_SEEDED)

    def test_receipt_entry_facts(self):
        """W-recording/CASES.md per-case entry lists and final seqs."""
        facts = {
            # "Entries, in order: step 1 intent, step 1 done ..., step 2 intent, step 2 done ..., step 3 intent. Receipt final seq 5"
            "W2-01-between-steps": ([(1, "intent"), (1, "done"), (2, "intent"), (2, "done"), (3, "intent")], 5, 4),
            # "Entries: step 1 intent, step 1 done, step 2 intent. No done entry for step 2. Receipt final seq 3."
            "W2-02-landed-without-done": ([(1, "intent"), (1, "done"), (2, "intent")], 3, 2),
            # "Entries: step 1 intent, step 1 done, step 2 intent, step 2 done, step 3 intent. Receipt final seq 5."
            "W2-03-between-two-status-lines": ([(1, "intent"), (1, "done"), (2, "intent"), (2, "done"), (3, "intent")], 5, 3),
            # "Entries: step 1 intent, step 1 done ..., step 2 intent. Receipt final seq 3."
            "W2-04-outside-edit": ([(1, "intent"), (1, "done"), (2, "intent")], 3, 2),
            # "Entries: step 1 intent only. Receipt final seq 1."
            "W2-05-two-steps-same-target": ([(1, "intent")], 1, 3),
        }
        for cid, cdir in self.cases("W-recording"):
            if cid not in facts:
                continue
            entries, seq, steps = facts[cid]
            doc = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))
            self.assertEqual([(e["step"], e["type"]) for e in doc["entries"]], entries, cid)
            self.assertEqual(doc["integrity"]["seq"], seq, cid)
            self.assertEqual(len(doc["plan"]), steps, cid)
            for e in doc["entries"]:
                if e["type"] == "done":
                    # "observed_sha256 ... = after_sha256 of step k"
                    self.assertEqual(e["observed_sha256"], doc["plan"][e["step"] - 1]["after_sha256"], cid)

    def test_checkpoint_grant_facts(self):
        """W-recording/CASES.md, W2-01: scope.grants.waivers holds G-waive-E4, reopenings holds G-reopen-E2;
        the item E2 carries the reopened marker. W2-05: waivers holds G-waive-E1 and E1 carries no marker."""
        for cid, cdir in self.cases("W-recording"):
            if cid not in ("W2-01-between-steps", "W2-05-two-steps-same-target"):
                continue
            doc = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
            if cid.startswith("W2-01"):
                self.assertEqual([w["item"]["location"]["line"] for w in doc["scope"]["grants"]["waivers"]], [32])
                self.assertEqual([r["item"]["location"]["line"] for r in doc["scope"]["grants"]["reopenings"]], [14])
                self.assertIn("reopened", doc["items"][1]["result"])
            else:
                self.assertEqual([w["item"]["location"]["line"] for w in doc["scope"]["grants"]["waivers"]], [9])
                self.assertNotIn("waived", doc["items"][0]["result"])
            self.assertEqual(doc["scope"]["review_sheet"], "absent")

    def test_fixture_inputs_validate_per_manifest(self):
        """Every built case's input.json validates exactly as its manifest's input_validates says."""
        n = 0
        for lane in self.lanes:
            for cid, cdir in self.cases(lane):
                manifest = testlib.load_json(os.path.join(cdir, "manifest.json"))
                doc = testlib.load_json(os.path.join(cdir, manifest.get("input", "input.json")))
                valid = not validate.validate_input(doc, self.schemas)
                self.assertEqual(valid, bool(manifest["input_validates"]), "%s: validator %s, manifest %s" % (cid, valid, manifest["input_validates"]))
                n += 1
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
