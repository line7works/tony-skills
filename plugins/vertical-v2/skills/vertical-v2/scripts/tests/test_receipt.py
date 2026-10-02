"""The local review's receipt (the E15 lane contract A4, class (b); contract sections 3.5 and 3.6).

`record-local` is the only writer of the local verdict, and when it completes it writes
`local-receipt.json`: the run id, each local call's id, row and lens with the sha256 of the readers
sidecar and capture as readers wrote them, the sha256 of `local.json`, and the time; its own closed
schema. `request --outside` releases nothing unless the receipt exists, validates, matches this run's
requested local calls, and every hash in it still matches the files on disk; and the record it covers
still holds as `record-local` would hold it. The run directory is the station's: a hand edit is not
prevented, it is detected, and the run refuses (exit 5) before any outside file is written. Each test
forges one piece in turn.
"""
import hashlib
import json
import os
import unittest

import testlib
import vlib

FIELDS = ["at", "calls", "local_sha256", "receipt_version", "run_id"]
CALL_FIELDS = ["call_id", "capture_sha256", "lens", "row", "sidecar_sha256"]


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the receipt follows record-local (records, readers' roster, jsonschema)")
class _Receipt(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vreceipt-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def recorded(self, **options):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, **options)
        self.drive, self.run_dir = drive, run_dir
        return run_dir

    def path(self, *parts):
        return os.path.join(self.run_dir, *parts)

    def refused(self, *words):
        code, out, err = self.drive(["request", "--run-dir", self.run_dir, "--outside"])
        self.assertEqual(code, 5, (out, err))
        for word in words:
            self.assertIn(word, out["reason"])
        self.assertEqual(vlib.outside_files(self.run_dir), [])
        self.assertFalse(os.path.exists(self.path("requests-outside.json")))
        summons = self.path("summons")
        if os.path.isdir(summons):
            self.assertEqual([n for n in os.listdir(summons) if not n.startswith("%s-local-" % self.run_id())], [])
        return out

    def run_id(self):
        return vlib.load(self.run_dir, "input.json")["run_id"]

    def receipt(self):
        return vlib.load(self.run_dir, "local-receipt.json")

    def rewrite_receipt(self, change):
        doc = self.receipt()
        change(doc)
        testlib.write_json(self.path("local-receipt.json"), doc)


class TheReceiptRecordLocalWrites(_Receipt):

    def test_record_local_writes_a_closed_receipt_over_the_files_readers_wrote(self):
        self.recorded()
        receipt = self.receipt()
        self.assertEqual(sorted(receipt), FIELDS)
        self.assertEqual(receipt["receipt_version"], 1)
        self.assertEqual(receipt["run_id"], self.run_id())
        self.assertEqual(receipt["local_sha256"], sha(self.path("local.json")))
        requested = vlib.load(self.run_dir, "requests-local.json")["calls"]
        self.assertEqual([(c["call_id"], c["row"], c["lens"]) for c in receipt["calls"]],
                         [(c["call_id"], c["row"], c["lens"]) for c in requested])
        for call in receipt["calls"]:
            self.assertEqual(sorted(call), CALL_FIELDS)
            self.assertEqual(call["sidecar_sha256"], sha(self.path("readers", call["call_id"], "sidecar.json")))
            self.assertEqual(call["capture_sha256"], sha(self.path("readers", call["call_id"], "raw.md")))

    def test_the_receipt_schema_is_closed(self):
        schema = testlib.load_json(os.path.join(testlib.REF, "local-receipt.schema.json"))
        self.assertFalse(schema.get("additionalProperties", True))
        call = schema["properties"]["calls"]["items"]
        self.assertFalse(call.get("additionalProperties", True))
        self.assertEqual(sorted(schema["required"]), FIELDS)
        self.assertEqual(sorted(call["required"]), CALL_FIELDS)

    def test_no_receipt_before_record_local_completes(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "local-receipt.json")))
        vlib.file_local_sidecars(run_dir)
        ids = vlib.local_ids(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir, findings=[vlib.finding("src/nowhere.py:3",
                                                                                            found_by=[ids[0]])])
        self.assertEqual(code, 5, (out, err))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "local-receipt.json")))

    def test_an_intact_receipt_releases_the_outside_requests(self):
        self.recorded()
        code, out, err = self.drive(["request", "--run-dir", self.run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(len(vlib.outside_files(self.run_dir)), 2)


class EachPieceForged(_Receipt):
    """Each piece forged in turn; each refused, exit 5, with no outside file on disk."""

    def test_the_checkpoint_alone_with_a_hand_written_local_record(self):
        """B3, the outside reviewer's probe: the phase set by hand, a local.json naming the requested call ids
        with an invented lens, no sidecars, an invented method and a finding that is not one."""
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        self.drive, self.run_dir = drive, run_dir
        checkpoint = vlib.load(run_dir, "checkpoint.json")
        checkpoint["phase"] = "recorded-local"
        testlib.write_json(self.path("checkpoint.json"), checkpoint)
        testlib.write_json(self.path("local.json"), {
            "calls": [{"call_id": c, "lens": "invented", "status": "ok"} for c in vlib.local_ids(run_dir)],
            "method": "invented", "findings": [{"not": "a finding"}], "tried": []})
        self.refused("local-receipt.json")

    def test_local_json_edited_after_record_local(self):
        self.recorded()
        local = vlib.load(self.run_dir, "local.json")
        local["method"] = "a method the executor never stated"
        testlib.write_json(self.path("local.json"), local)
        self.refused("local.json")

    def test_a_sidecar_edited_after_record_local(self):
        self.recorded()
        call = vlib.local_ids(self.run_dir)[1]
        side = vlib.load(self.run_dir, os.path.join("readers", call, "sidecar.json"))
        side["effective_model"] = "a-model-that-never-ran"
        testlib.write_json(self.path("readers", call, "sidecar.json"), side)
        self.refused(call, "sidecar")

    def test_a_capture_edited_after_record_local(self):
        self.recorded()
        call = vlib.local_ids(self.run_dir)[0]
        testlib.write_text(self.path("readers", call, "raw.md"), "Findings: none, and nothing was tried.\n")
        self.refused(call, "capture")

    def test_the_receipt_deleted(self):
        self.recorded()
        os.remove(self.path("local-receipt.json"))
        self.refused("local-receipt.json")

    def test_the_receipt_not_json(self):
        self.recorded()
        testlib.write_text(self.path("local-receipt.json"), "{ not json\n")
        self.refused("local-receipt.json")

    def test_the_receipt_with_a_hash_changed(self):
        self.recorded()
        self.rewrite_receipt(lambda d: d.update(local_sha256="0" * 64))
        self.refused("local.json")

    def test_the_receipt_with_a_call_dropped(self):
        self.recorded()
        self.rewrite_receipt(lambda d: d.update(calls=d["calls"][1:]))
        self.refused("requested")

    def test_the_receipt_with_an_unknown_key(self):
        self.recorded()
        self.rewrite_receipt(lambda d: d.update(note="trust me"))
        self.refused("local-receipt.json")

    def test_the_receipt_for_another_run(self):
        self.recorded()
        self.rewrite_receipt(lambda d: d.update(run_id="another-run"))
        self.refused("another-run")

    def test_a_consistent_forgery_of_the_record_and_its_receipt_that_record_local_would_refuse(self):
        """local.json and the receipt rewritten together, every hash recomputed: the record still has to hold
        the way record-local holds it, and a finding at a location that does not exist does not."""
        self.recorded()
        local = vlib.load(self.run_dir, "local.json")
        ids = vlib.local_ids(self.run_dir)
        local["findings"] = [vlib.finding("src/nowhere.py:3", found_by=[ids[0]])]
        testlib.write_json(self.path("local.json"), local)
        self.rewrite_receipt(lambda d: d.update(local_sha256=sha(self.path("local.json"))))
        self.refused("src/nowhere.py:3")

    def test_a_second_record_local_after_completion_is_refused(self):
        self.recorded()
        before = sha(self.path("local-receipt.json"))
        code, out, err = vlib.record_local(self.drive, self.tmp, self.run_dir)
        self.assertEqual(code, 2, (out, err))
        self.assertEqual(sha(self.path("local-receipt.json")), before)


if __name__ == "__main__":
    unittest.main()
