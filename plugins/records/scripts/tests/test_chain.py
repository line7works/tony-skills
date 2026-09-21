"""The chain: contract section 10's walk, through `verify` and through the library.

The four damages the contract names are here: an edited line, a deleted line, a swapped pair,
and a joined pair of tails (a simulated git merge). Each is built from a log the component
itself wrote, so nothing is asserted about a log shape the component would not produce.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from records_core import canon, events as events_mod  # noqa: E402

DOC = testlib.DOC


def build_log(workspace, scratch, count=4):
    """A log with `log_opened` and `count` findings, written through the CLI."""
    batch = [testlib.opened()]
    for i in range(count):
        batch.append(testlib.raised(claim="finding number %d" % i, at="2026-04-01T09:0%d:00Z" % i,
                                    loc=testlib.location("src/widget.py:%d" % (10 + i), "src/widget.py", 10 + i)))
    path = testlib.events_file(scratch, batch)
    code, doc, err = testlib.run_json(["append", "--workspace", workspace, "--doc", DOC,
                                       "--events", path, "--expect-head", testlib.ZERO])
    assert code == 0, (code, doc, err)
    return doc["head"]


class ChainWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-chain-")
        cls.workspace = testlib.make_workspace(cls.scratch)
        cls.head = build_log(cls.workspace, cls.scratch)
        cls.log = testlib.log_file(cls.workspace)
        with open(cls.log, "rb") as fh:
            cls.original = fh.read()

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.scratch)

    def setUp(self):
        with open(self.log, "wb") as fh:
            fh.write(self.original)

    def lines(self):
        return self.original.rstrip(b"\n").split(b"\n")

    def rewrite(self, lines):
        with open(self.log, "wb") as fh:
            fh.write(b"".join(line + b"\n" for line in lines))

    def verify(self):
        return testlib.run_json(["verify", "--workspace", self.workspace, "--doc", DOC])

    # ---- the healthy log -------------------------------------------------------------------

    def test_an_untouched_log_verifies(self):
        code, doc, err = self.verify()
        self.assertEqual(code, 0, err)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["events"], 5)
        self.assertEqual(doc["head"], self.head)
        self.assertEqual(doc["log"], "docs/records/docs__plans__2026-04-01-widget.events.jsonl")

    def test_a_log_that_does_not_exist_verifies_empty(self):
        code, doc, err = testlib.run_json(["verify", "--workspace", self.workspace,
                                           "--doc", "docs/plans/no-such-doc.md"])
        self.assertEqual(code, 0, err)
        self.assertFalse(doc["exists"])
        self.assertEqual(doc["head"], testlib.ZERO)
        self.assertEqual(doc["events"], 0)

    # ---- the four damages ------------------------------------------------------------------

    def test_an_edited_line_is_caught(self):
        lines = self.lines()
        event = json.loads(lines[2].decode("utf-8"))
        event["claim"] = "a claim nobody wrote"
        lines[2] = canon.canonical_json(event)
        self.rewrite(lines)
        code, doc, err = self.verify()
        self.assertEqual(code, 7, (doc, err))
        self.assertEqual(doc["error"], "conflict")
        self.assertEqual(doc["line"], 4, "the break shows at the line after the edited one")

    def test_an_edited_line_is_caught_at_its_own_line_when_seq_changes(self):
        lines = self.lines()
        event = json.loads(lines[2].decode("utf-8"))
        event["seq"] = 9
        lines[2] = canon.canonical_json(event)
        self.rewrite(lines)
        code, doc, _ = self.verify()
        self.assertEqual(code, 7)
        self.assertEqual(doc["line"], 3)
        self.assertEqual(doc["seq"], 9)
        self.assertEqual(doc["expected_seq"], 2)

    def test_a_deleted_line_is_caught(self):
        lines = self.lines()
        del lines[2]
        self.rewrite(lines)
        code, doc, _ = self.verify()
        self.assertEqual(code, 7)
        self.assertEqual(doc["error"], "conflict")
        self.assertEqual(doc["line"], 3, "the line that moved up is the first bad one")

    def test_a_swapped_pair_is_caught(self):
        lines = self.lines()
        lines[2], lines[3] = lines[3], lines[2]
        self.rewrite(lines)
        code, doc, _ = self.verify()
        self.assertEqual(code, 7)
        self.assertEqual(doc["line"], 3)

    def test_a_joined_pair_of_tails_is_caught(self):
        """A git merge that kept both sides: the second tail's first prev names a line that is no
        longer its predecessor, and its seq repeats one already used."""
        lines = self.lines()
        joined = lines + lines[3:]
        self.rewrite(joined)
        code, doc, _ = self.verify()
        self.assertEqual(code, 7)
        self.assertEqual(doc["error"], "conflict")
        self.assertEqual(doc["line"], len(lines) + 1)
        self.assertEqual(doc["expected_seq"], len(lines))

    def test_a_joined_pair_of_tails_with_repaired_seqs_is_still_caught(self):
        """Even with seq renumbered down the file, the prev chain does not join."""
        lines = self.lines()
        tail = []
        for i, raw in enumerate(lines[3:], start=len(lines)):
            event = json.loads(raw.decode("utf-8"))
            event["seq"] = i
            tail.append(canon.canonical_json(event))
        self.rewrite(lines + tail)
        code, doc, _ = self.verify()
        self.assertEqual(code, 7)
        self.assertEqual(doc["line"], len(lines) + 1)
        self.assertIn("prev", doc)

    # ---- validation failures, which are exit 4 ------------------------------------------------

    def test_an_unknown_version_in_the_log_is_refused_not_skipped(self):
        """E12-7: a reader refuses an event whose `v` it does not know, naming the line."""
        lines = self.lines()
        event = json.loads(lines[1].decode("utf-8"))
        event["v"] = 99
        lines[1] = canon.canonical_json(event)
        self.rewrite(lines)
        code, doc, _ = self.verify()
        self.assertEqual(code, 4)
        self.assertEqual(doc["error"], "invalid")
        self.assertEqual(doc["line"], 2)
        self.assertIn("unknown event version", doc["errors"][0]["message"])

    def test_a_line_that_is_not_json_is_refused(self):
        lines = self.lines()
        lines[1] = b"{not json"
        self.rewrite(lines)
        code, doc, _ = self.verify()
        self.assertEqual(code, 4)
        self.assertEqual(doc["line"], 2)

    def test_a_line_that_fails_the_schema_is_refused(self):
        lines = self.lines()
        event = json.loads(lines[1].decode("utf-8"))
        event.pop("actor")
        lines[1] = canon.canonical_json(event)
        self.rewrite(lines)
        code, doc, _ = self.verify()
        self.assertEqual(code, 4)
        self.assertEqual(doc["line"], 2)

    def test_a_missing_trailing_newline_is_refused(self):
        with open(self.log, "wb") as fh:
            fh.write(self.original.rstrip(b"\n"))
        code, doc, _ = self.verify()
        self.assertEqual(code, 4)
        self.assertIn("newline", doc["reason"])

    def test_an_empty_line_is_refused(self):
        self.rewrite(self.lines() + [b""])
        code, doc, _ = self.verify()
        self.assertEqual(code, 4)
        self.assertIn("empty line", doc["reason"])

    def test_a_carriage_return_is_refused(self):
        with open(self.log, "wb") as fh:
            fh.write(self.original.replace(b"\n", b"\r\n"))
        code, doc, _ = self.verify()
        self.assertEqual(code, 4)
        self.assertIn("carriage return", doc["reason"])

    # ---- the events reader walks the same chain ---------------------------------------------

    def test_events_returns_history_and_spec_addresses(self):
        code, doc, err = testlib.run_json(["events", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["returned"], 5)
        first = doc["results"][0]
        self.assertEqual(first["history"], {"log": doc["log"], "seq": 0})
        self.assertEqual(first["spec"]["doc"], DOC)
        self.assertEqual(doc["spec"], {"doc": DOC, "slice": None})

    def test_events_filters(self):
        code, doc, _ = testlib.run_json(["events", "--workspace", self.workspace, "--doc", DOC,
                                         "--kind", "finding_raised", "--from", 3])
        self.assertEqual(code, 0)
        self.assertEqual([r["seq"] for r in doc["results"]], [3, 4])
        finding = doc["results"][0]["event"]["finding"]
        code, doc, _ = testlib.run_json(["events", "--workspace", self.workspace, "--doc", DOC,
                                         "--finding", finding])
        self.assertEqual([r["seq"] for r in doc["results"]], [3])

    def test_events_refuses_a_broken_log(self):
        lines = self.lines()
        del lines[2]
        self.rewrite(lines)
        code, doc, _ = testlib.run_json(["events", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 7)
        self.assertEqual(doc["error"], "conflict")


class LogAddresses(unittest.TestCase):
    def test_the_slug_of_the_contract(self):
        self.assertEqual(events_mod.slug_of("docs/plans/2026-09-06-readers.md"),
                         "docs__plans__2026-09-06-readers")
        self.assertEqual(events_mod.log_relpath("docs/punch-list.md"),
                         "docs/records/docs__punch-list.events.jsonl")

    def test_the_log_sits_under_docs_records(self):
        path = events_mod.log_path("/tmp/ws", "docs/plans/a.md")
        self.assertEqual(path, os.path.join("/tmp/ws", "docs", "records", "docs__plans__a.events.jsonl"))


if __name__ == "__main__":
    unittest.main()
