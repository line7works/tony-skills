"""recheck_core.verifier: the closed report shape of verifier.md section 2 (E8-A27) and the one
shared complete-call decision (E8-A40). The positive case is the section's own example block."""
import copy
import json
import os
import re
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import canon, verifier  # noqa: E402


def example_block():
    """The JSON block of verifier.md section 2, verbatim."""
    text = testlib.read_text(os.path.join(testlib.REF, "verifier.md"))
    start = text.index("## 2. The report")
    m = re.search(r"```json\n(.*?)\n```", text[start:], re.S)
    return json.loads(m.group(1))


def report(tail):
    return "# Verifier report\n\nRan the scenario from the workspace root.\n\n```json\n%s\n```\n" % json.dumps(tail, indent=1, ensure_ascii=False)


class ClosedShape(unittest.TestCase):
    def setUp(self):
        self.tail = example_block()

    def parse(self, tail, n_items=1):
        return verifier.parse_report_tail(report(tail), n_items)

    def assert_incomplete(self, tail, key, n_items=1):
        got = self.parse(tail, n_items)
        self.assertFalse(got["ok"], key)
        self.assertIn(key, got["reason"], (key, got["reason"]))
        self.assertIsNone(got["tail"])

    def test_example_block_parses(self):
        """The exact verifier.md example block is a complete report; the three string lists may be absent."""
        got = self.parse(self.tail)
        self.assertTrue(got["ok"], got["reason"])
        self.assertEqual(got["tail"], self.tail)
        t = copy.deepcopy(self.tail)
        for k in ("grant_claims", "injection_attempts", "refused_actions"):
            del t[k]
        self.assertTrue(self.parse(t)["ok"])
        t = copy.deepcopy(self.tail)
        del t["new_defects"]
        self.assertTrue(self.parse(t)["ok"])
        self.assertEqual(verifier.candidate_defects(self.tail)[0]["caused_by_index"], 0)

    def test_omitted_top_level_keys(self):
        for k in ("recheck_verifier_report", "items"):
            t = copy.deepcopy(self.tail)
            del t[k]
            self.assert_incomplete(t, k)

    def test_omitted_item_keys(self):
        for k in verifier.ITEM_KEYS:
            t = copy.deepcopy(self.tail)
            del t["items"][0][k]
            self.assert_incomplete(t, k)

    def test_omitted_evidence_keys(self):
        for k in verifier.EVIDENCE_KEYS:
            t = copy.deepcopy(self.tail)
            del t["items"][0]["evidence"][0][k]
            self.assert_incomplete(t, k)
            t = copy.deepcopy(self.tail)
            del t["new_defects"][0]["evidence"][0][k]
            self.assert_incomplete(t, k)

    def test_omitted_candidate_keys(self):
        for k in verifier.CANDIDATE_KEYS:
            t = copy.deepcopy(self.tail)
            del t["new_defects"][0][k]
            self.assert_incomplete(t, k)

    def test_unknown_keys_at_every_level(self):
        t = copy.deepcopy(self.tail)
        t["observed"] = "x"
        self.assert_incomplete(t, "observed")
        t = copy.deepcopy(self.tail)
        t["items"][0]["confidence"] = 1
        self.assert_incomplete(t, "confidence")
        t = copy.deepcopy(self.tail)
        t["items"][0]["evidence"][0]["exit"] = 0
        self.assert_incomplete(t, "exit")
        t = copy.deepcopy(self.tail)
        t["new_defects"][0]["severity"] = "MAJOR"
        self.assert_incomplete(t, "severity")

    def test_version_must_be_the_integer_one(self):
        for v in ("1", True, 1.5, 2, None):
            t = copy.deepcopy(self.tail)
            t["recheck_verifier_report"] = v
            self.assert_incomplete(t, "recheck_verifier_report")

    def test_candidate_with_empty_evidence(self):
        for v in ([], None, "ran it"):
            t = copy.deepcopy(self.tail)
            t["new_defects"][0]["evidence"] = v
            self.assert_incomplete(t, "new_defects[0] evidence")

    def test_out_of_range_caused_by_index(self):
        for v in (1, -1, "0", 0.0, True):
            t = copy.deepcopy(self.tail)
            t["new_defects"][0]["caused_by_index"] = v
            self.assert_incomplete(t, "caused_by_index")
        # in range on a longer checklist: the same block with two items covered
        t = copy.deepcopy(self.tail)
        second = copy.deepcopy(t["items"][0])
        second["index"] = 1
        t["items"].append(second)
        t["new_defects"][0]["caused_by_index"] = 1
        self.assertTrue(self.parse(t, 2)["ok"])

    def test_typed_fields(self):
        """Integer indexes, file:line locations, evidence kinds and details, one-line string lists."""
        t = copy.deepcopy(self.tail)
        t["items"][0]["index"] = "0"
        self.assertFalse(self.parse(t)["ok"])
        t = copy.deepcopy(self.tail)
        t["items"][0]["location"] = "src/widget/export.py"
        self.assert_incomplete(t, "location")
        t = copy.deepcopy(self.tail)
        t["new_defects"][0]["location"] = "line 12"
        self.assert_incomplete(t, "new_defects[0] location")
        t = copy.deepcopy(self.tail)
        t["items"][0]["evidence"][0]["kind"] = "guess"
        self.assert_incomplete(t, "kind")
        t = copy.deepcopy(self.tail)
        t["items"][0]["evidence"][0]["detail"] = "  "
        self.assert_incomplete(t, "detail")
        t = copy.deepcopy(self.tail)
        t["items"][0]["evidence"][0]["artifact"] = 3
        self.assert_incomplete(t, "artifact")
        t = copy.deepcopy(self.tail)
        t["new_defects"][0]["claim"] = ""
        self.assert_incomplete(t, "claim")
        t = copy.deepcopy(self.tail)
        t["refused_actions"] = ["one · two"]
        self.assert_incomplete(t, "refused_actions[0]")
        t = copy.deepcopy(self.tail)
        t["grant_claims"] = [1]
        self.assert_incomplete(t, "grant_claims")

    def test_location_after_fix_handling_stands(self):
        """E8-8, E8-A10 (b): file:line or null is accepted; another string parses but is dropped with a note."""
        t = copy.deepcopy(self.tail)
        t["items"][0]["location_after_fix"] = None
        self.assertTrue(self.parse(t)["ok"])
        t["items"][0]["location_after_fix"] = "moved into the writer"
        got = self.parse(t)
        self.assertTrue(got["ok"], got["reason"])
        m = verifier.map_item(got["tail"]["items"][0], "/nonexistent-run-dir")
        self.assertNotIn("location_after_fix", m["verification"])
        self.assertTrue(any("location_after_fix" in n and "dropped" in n for n in m["notes"]), m["notes"])


class CompleteCall(unittest.TestCase):
    def test_is_complete(self):
        """E8-A40: `complete` (the checkpoint's spelling) and `ok` (the transport's) and nothing else."""
        self.assertTrue(verifier.is_complete("complete"))
        self.assertTrue(verifier.is_complete("ok"))
        for s in ("incomplete", "empty", "invalid-request", "", None, "COMPLETE"):
            self.assertFalse(verifier.is_complete(s), s)
        self.assertEqual(verifier.classify_status("ok"), verifier.COMPLETE)

    def test_retained_report_accepts_ok(self):
        """A checkpoint call record with status `ok` and a matching hash is a retained report (E8-A40)."""
        d = testlib.make_scratch("e8-verifier-")
        try:
            raw = testlib.write_report(d, report(example_block()))
            sha = canon.sha256_file(raw)
            cp = {"verifier_calls": [{"call_id": "r-verify", "status": "ok", "items": [0], "raw_path": raw, "raw_sha256": sha}]}
            call, text = verifier.retained_report(d, cp, 0)
            self.assertIsNotNone(call)
            self.assertEqual(call["call_id"], "r-verify")
            self.assertTrue(verifier.parse_report_tail(text, 1, call["items"])["ok"])
            cp["verifier_calls"][0]["status"] = "complete"
            self.assertEqual(verifier.retained_report(d, cp)[0]["call_id"], "r-verify")
            cp["verifier_calls"][0]["status"] = "incomplete"
            self.assertEqual(verifier.retained_report(d, cp), (None, None))
            cp["verifier_calls"][0]["status"] = "ok"
            cp["verifier_calls"][0]["raw_sha256"] = "0" * 64
            self.assertEqual(verifier.retained_report(d, cp), (None, None), "a report that no longer hashes is not retained (E8-7)")
        finally:
            testlib.rmtree(d)


if __name__ == "__main__":
    unittest.main()
