"""recheck_core.canon: canonical bytes equal the E7 library's, digests, and the write primitives."""
import hashlib
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import canon  # noqa: E402


class CanonicalBytes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = testlib.fixturelib()
        cls.cp = testlib.load_json(os.path.join(testlib.EX, "checkpoint-partial.json"))
        cls.rc = testlib.load_json(os.path.join(testlib.EX, "receipt-partial.json"))

    def test_canonical_json_equals_fixturelib(self):
        for doc in (self.cp, self.rc, {"z": [1, 2.5, None, True], "a": {"é": "—", "b": ""}}):
            self.assertEqual(canon.canonical_json(doc), self.lib.canonical_json(doc))
            self.assertEqual(canon.sha256_hex(canon.canonical_json(doc)), self.lib.sha256_hex(self.lib.canonical_json(doc)))

    def test_canonical_json_shape(self):
        out = canon.canonical_json({"b": 1, "a": "—"})
        self.assertEqual(out, '{"a":"—","b":1}'.encode("utf-8"), "keys sorted, no whitespace, non-ASCII unescaped")

    def test_example_self_digests_recompute(self):
        for doc, log in ((self.cp, "checkpoint-partial.log"), (self.rc, "receipt-partial.log")):
            body = {k: v for k, v in doc.items()}
            body["integrity"] = {"seq": doc["integrity"]["seq"], "prev": doc["integrity"]["prev"]}
            self.assertEqual(canon.sha256_hex(canon.canonical_json(body)), doc["integrity"]["self"])
            with open(os.path.join(testlib.EX, log)) as fh:
                last = fh.read().splitlines()[-1].split()
            self.assertEqual(last, [str(doc["integrity"]["seq"]), doc["integrity"]["self"]], "the log's last line is (seq, self)")

    def test_receipt_example_chain(self):
        """The receipt example's chain: prev is the line before, every line a real write."""
        with open(os.path.join(testlib.EX, "receipt-partial.log")) as fh:
            rows = [l.split() for l in fh.read().splitlines()]
        self.assertEqual([int(r[0]) for r in rows], list(range(len(rows))))
        self.assertEqual(self.rc["integrity"]["prev"], rows[-2][1])
        self.assertEqual(self.rc["integrity"]["seq"], len(self.rc["entries"]), "one write per entry after seq 0")

    def test_sha256_file(self):
        path = os.path.join(testlib.EX, "checkpoint-partial.json")
        with open(path, "rb") as fh:
            self.assertEqual(canon.sha256_file(path), hashlib.sha256(fh.read()).hexdigest())


class WritePrimitives(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e8-slice1-canon-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    def test_atomic_write_creates_and_replaces(self):
        target = os.path.join(self.dir, "checkpoint.json")
        canon.atomic_write(target, b'{"a":1}')
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b'{"a":1}')
        canon.atomic_write(target, b'{"a":2}')
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b'{"a":2}')
        self.assertEqual(sorted(os.listdir(self.dir)), ["checkpoint.json"], "no temporary file left beside the target")

    def test_atomic_write_rejects_text(self):
        with self.assertRaises(TypeError):
            canon.atomic_write(os.path.join(self.dir, "x"), "text")

    def test_atomic_write_failure_leaves_old_bytes(self):
        target = os.path.join(self.dir, "missing-dir", "x.json")
        with self.assertRaises(OSError):
            canon.atomic_write(target, b"x")
        self.assertEqual(os.listdir(self.dir), [])

    def test_log_then_rename_order_and_bytes(self):
        log = os.path.join(self.dir, "checkpoint.log")
        target = os.path.join(self.dir, "checkpoint.json")
        canon.log_then_rename(log, "0 " + "a" * 64, target, b"first")
        canon.log_then_rename(log, "1 " + "b" * 64 + "\n", target, b"second")
        with open(log) as fh:
            self.assertEqual(fh.read(), "0 " + "a" * 64 + "\n" + "1 " + "b" * 64 + "\n", "one line per write, one newline each")
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b"second")
        self.assertEqual(sorted(os.listdir(self.dir)), ["checkpoint.json", "checkpoint.log"])

    def test_log_then_rename_writes_log_first(self):
        """A rename that never lands leaves the log one line ahead: the one tolerated state (section 11)."""
        log = os.path.join(self.dir, "checkpoint.log")
        target = os.path.join(self.dir, "gone", "checkpoint.json")  # the rename cannot land
        with self.assertRaises(OSError):
            canon.log_then_rename(log, "0 " + "c" * 64, target, b"never")
        with open(log) as fh:
            self.assertEqual(fh.read(), "0 " + "c" * 64 + "\n", "the announcing line was written before the rename was attempted")
        self.assertFalse(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()
