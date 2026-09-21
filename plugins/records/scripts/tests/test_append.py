"""`append`: the optimistic head, the lock, the atomic batch, and section 7's identity stops."""
import copy
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from records_core import events as events_mod, identity as identity_mod, validate  # noqa: E402

DOC = testlib.DOC


class AppendCase(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-append-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def append(self, events, head, extra=None):
        path = testlib.events_file(self.batches, events, name="batch-%d.json" % len(os.listdir(self.batches)))
        args = ["append", "--workspace", self.workspace, "--doc", DOC, "--events", path,
                "--expect-head", head] + list(extra or [])
        return testlib.run_json(args)

    def open_log(self):
        code, doc, err = self.append([testlib.opened(self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        return doc["head"]

    def raise_one(self, head, **kw):
        code, doc, err = self.append([testlib.raised(identity=self.identity, **kw)], head)
        self.assertEqual(code, 0, (doc, err))
        return doc["head"], doc["appended"][0]["finding"]


class Heads(AppendCase):
    def test_the_first_append_takes_sixty_four_zeros(self):
        head = self.open_log()
        self.assertNotEqual(head, testlib.ZERO)
        self.assertEqual(len(head), 64)

    def test_a_wrong_head_is_refused_and_writes_nothing(self):
        head = self.open_log()
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([testlib.raised(identity=self.identity)], "b" * 64)
        self.assertEqual(code, 7)
        self.assertEqual(doc["error"], "conflict")
        self.assertEqual(doc["expected_head"], "b" * 64)
        self.assertEqual(doc["actual_head"], head)
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_replaying_a_landed_append_is_refused(self):
        head = self.open_log()
        self.raise_one(head)
        code, doc, _ = self.append([testlib.raised(identity=self.identity)], head)
        self.assertEqual(code, 7)

    def test_a_head_that_is_not_hex_is_a_usage_error(self):
        code, out, err = testlib.run_cli(["append", "--workspace", self.workspace, "--doc", DOC,
                                          "--events", testlib.events_file(self.batches, [testlib.opened()]),
                                          "--expect-head", "not-a-hash"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--expect-head", err)


class Batches(AppendCase):
    def test_a_batch_with_one_invalid_event_writes_nothing(self):
        head = self.open_log()
        before = testlib.read_log(self.workspace)
        good = testlib.raised(identity=self.identity)
        bad = testlib.raised(identity=self.identity, claim="the second one",
                             loc=testlib.location("src/widget.py:99", "src/widget.py", 99))
        bad.pop("severity")
        third = testlib.raised(identity=self.identity, claim="the third one",
                               loc=testlib.location("src/widget.py:100", "src/widget.py", 100))
        code, doc, _ = self.append([good, bad, third], head)
        self.assertEqual(code, 4)
        self.assertEqual(doc["error"], "invalid")
        self.assertEqual(doc["event_index"], 2)
        self.assertEqual(testlib.read_log(self.workspace), before, "nothing was written")

    def test_a_batch_lands_whole(self):
        head = self.open_log()
        batch = [testlib.raised(identity=self.identity, claim="one"),
                 testlib.raised(identity=self.identity, claim="two",
                                loc=testlib.location("src/widget.py:99", "src/widget.py", 99))]
        code, doc, err = self.append(batch, head)
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual([row["seq"] for row in doc["appended"]], [1, 2])
        self.assertEqual(doc["events"], 3)

    def test_a_later_event_in_a_batch_sees_an_earlier_one(self):
        """A raise and its disposition in one batch: the disposition finds the finding."""
        head = self.open_log()
        raise_event = testlib.raised(identity=self.identity)
        from records_core import ids
        finding = ids.id_of_event(raise_event)
        clear = testlib.disposition(finding, self.identity)
        code, doc, err = self.append([raise_event, clear], head)
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["appended"][1]["kind"], "disposition")

    def test_an_unknown_version_is_refused(self):
        head = self.open_log()
        event = testlib.raised(identity=self.identity)
        event["v"] = 2
        code, doc, _ = self.append([event], head)
        self.assertEqual(code, 4)
        self.assertIn("unknown event version", doc["errors"][0]["message"])
        self.assertEqual(doc["event_index"], 1)

    def test_seq_and_prev_are_the_components_to_assign(self):
        head = self.open_log()
        event = testlib.raised(identity=self.identity)
        event["seq"] = 40
        code, doc, _ = self.append([event], head)
        self.assertEqual(code, 4)
        self.assertIn("assigned by the component", doc["reason"])

    def test_an_event_for_another_document_is_refused(self):
        head = self.open_log()
        event = testlib.raised(identity=self.identity, doc="docs/plans/other.md")
        code, doc, _ = self.append([event], head)
        self.assertEqual(code, 4)
        self.assertIn("ledger_doc", doc["reason"])

    def test_an_empty_events_file_is_a_usage_error(self):
        path = os.path.join(self.batches, "empty.json")
        testlib.write(path, "[]\n")
        code, out, err = testlib.run_cli(["append", "--workspace", self.workspace, "--doc", DOC,
                                          "--events", path, "--expect-head", testlib.ZERO])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_a_missing_events_file_is_a_usage_error(self):
        code, out, err = testlib.run_cli(["append", "--workspace", self.workspace, "--doc", DOC,
                                          "--events", os.path.join(self.batches, "nothing.json"),
                                          "--expect-head", testlib.ZERO])
        self.assertEqual(code, 2)
        self.assertIn("--events", err)

    def test_log_opened_after_the_first_line_is_refused(self):
        head = self.open_log()
        code, doc, _ = self.append([testlib.opened(self.identity)], head)
        self.assertEqual(code, 4)
        self.assertEqual(doc["event_index"], 1)


class Identities(AppendCase):
    def test_a_malformed_event_is_refused_rather_than_crashing(self):
        """Garbage in a field the ID is computed from is exit 4, never a traceback."""
        head = self.open_log()
        for mutation in ({"location": 12}, {"location": {"raw": 7}}, {"claim": 5}, {"slice": None}):
            event = testlib.raised(identity=self.identity)
            event.update(mutation)
            code, doc, err = self.append([event], head)
            self.assertEqual(code, 4, "%s: %s %s" % (mutation, doc, err))
            self.assertEqual(doc["error"], "invalid", mutation)

    def test_the_schema_is_checked_before_the_identity_rules(self):
        """An event that is both malformed and a second raise is exit 4, the validation failure."""
        head = self.open_log()
        head, _ = self.raise_one(head)
        event = testlib.raised(identity=self.identity)
        event.pop("raised_by")
        code, doc, _ = self.append([event], head)
        self.assertEqual(code, 4)

    def test_a_second_raise_of_a_held_id_is_refused(self):
        head = self.open_log()
        head, finding = self.raise_one(head)
        code, doc, _ = self.append([testlib.raised(identity=self.identity)], head)
        self.assertEqual(code, 5)
        self.assertEqual(doc["error"], "ambiguous_identity")
        self.assertEqual(doc["finding"], finding)
        self.assertEqual(doc["candidates"], [{"log": doc["log"] if "log" in doc else
                                              events_mod.log_relpath(DOC), "seq": 1}])

    def test_two_raises_of_one_id_inside_one_batch_are_refused(self):
        head = self.open_log()
        twice = [testlib.raised(identity=self.identity), testlib.raised(identity=self.identity)]
        code, doc, _ = self.append(twice, head)
        self.assertEqual(code, 5)
        self.assertEqual(doc["event_index"], 2)

    def test_an_unknown_finding_id_is_refused(self):
        head = self.open_log()
        unknown = "f1:" + "a" * 20
        code, doc, _ = self.append([testlib.disposition(unknown, self.identity, value="not_fixed")], head)
        self.assertEqual(code, 5)
        self.assertEqual(doc["error"], "ambiguous_identity")
        self.assertEqual(doc["finding"], unknown)

    def test_an_unknown_caused_by_is_refused(self):
        head = self.open_log()
        head, finding = self.raise_one(head)
        defect = testlib.native("defect_raised", at="2026-04-01T12:00:00Z", identity=self.identity,
                                slice="A", severity="MINOR",
                                location=testlib.location("src/widget.py:90", "src/widget.py", 90),
                                claim="the counter is never reset", scenario="a second failure miscounts",
                                raised_by="A", caused_by="f1:" + "b" * 20)
        code, doc, _ = self.append([defect], head)
        self.assertEqual(code, 5)
        self.assertEqual(doc["path"], "/caused_by")

    def test_a_supplied_finding_that_is_not_the_computed_one_is_refused(self):
        head = self.open_log()
        event = testlib.raised(identity=self.identity)
        event["finding"] = "f1:" + "c" * 20
        code, doc, _ = self.append([event], head)
        self.assertEqual(code, 4)
        self.assertIn("compute", doc["reason"])

    def test_the_component_stamps_the_finding_id(self):
        from records_core import ids
        head = self.open_log()
        event = testlib.raised(identity=self.identity)
        expected = ids.id_of_event(event)
        _, finding = self.raise_one(head)
        self.assertEqual(finding, expected)

    def test_a_reopening_after_a_fix_is_accepted(self):
        head = self.open_log()
        head, finding = self.raise_one(head)
        code, doc, err = self.append([testlib.disposition(finding, self.identity)], head)
        self.assertEqual(code, 0, (doc, err))
        head = doc["head"]
        reopen = testlib.native("reopened", at="2026-04-02T09:00:00Z", identity=self.identity,
                                finding=finding, words="it came back", grant_date="2026-04-02")
        code, doc, err = self.append([reopen], head)
        self.assertEqual(code, 0, (doc, err))


class Locks(AppendCase):
    def lock_path(self):
        return events_mod.lock_path(testlib.log_file(self.workspace))

    def test_a_held_lock_is_refused_with_its_contents(self):
        head = self.open_log()
        testlib.write(self.lock_path(), json.dumps({"pid": os.getpid(),
                                                    "pid_start": events_mod.process_start(os.getpid()),
                                                    "command": "append"}))
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([testlib.raised(identity=self.identity)], head)
        self.assertEqual(code, 7)
        self.assertEqual(doc["error"], "conflict")
        self.assertEqual(doc["lock"]["pid"], os.getpid())
        self.assertTrue(doc["holder_alive"])
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_break_lock_is_refused_while_the_holder_is_alive(self):
        head = self.open_log()
        testlib.write(self.lock_path(), json.dumps({"pid": os.getpid(),
                                                    "pid_start": events_mod.process_start(os.getpid()),
                                                    "command": "append"}))
        code, doc, _ = self.append([testlib.raised(identity=self.identity)], head, extra=["--break-lock"])
        self.assertEqual(code, 7)
        self.assertTrue(doc["holder_alive"])
        self.assertTrue(os.path.isfile(self.lock_path()), "a live holder's lock is left alone")

    def test_break_lock_removes_a_dead_holders_lock_and_says_so(self):
        head = self.open_log()
        dead = {"pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026", "command": "append"}
        testlib.write(self.lock_path(), json.dumps(dead))
        code, doc, err = self.append([testlib.raised(identity=self.identity)], head, extra=["--break-lock"])
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["broke_lock"]["pid"], 999999)
        self.assertFalse(os.path.isfile(self.lock_path()), "the lock is released at the end")

    def test_a_recycled_pid_is_not_the_holder(self):
        """A pid is not an identity: the same pid under another start time is a stale lock.

        This is the one rule in the component that needs `ps`. A sandbox that denies it cannot
        tell a recycled pid from a live one, and `holder_alive` then trusts the live pid, which
        is the safe answer; the test says so rather than failing for the sandbox.
        """
        if events_mod.process_start(os.getpid()) is None:
            self.skipTest("this environment does not allow `ps`, so a recycled pid cannot be "
                          "told from a live one")
        head = self.open_log()
        testlib.write(self.lock_path(), json.dumps({"pid": os.getpid(),
                                                    "pid_start": "Wed Jan  1 00:00:00 2020",
                                                    "command": "append"}))
        code, doc, err = self.append([testlib.raised(identity=self.identity)], head, extra=["--break-lock"])
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["broke_lock"]["pid"], os.getpid())

    def test_a_breaker_that_loses_the_race_conflicts_rather_than_crashing(self):
        """F3: another breaker takes the lock between this one's unlink and its open. That is a
        held lock, so it is exit 7 `conflict` with the new lock's contents, never an exit 1."""
        import unittest.mock as mock
        self.open_log()
        dead = {"pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026", "command": "append"}
        testlib.write(self.lock_path(), json.dumps(dead))
        winner = {"pid": os.getpid(), "pid_start": events_mod.process_start(os.getpid()),
                  "command": "append"}
        real_unlink = os.unlink

        def unlink_then_lose_the_race(path):
            real_unlink(path)
            if path == self.lock_path():
                testlib.write(path, json.dumps(winner))

        schemas = validate.load_schemas(testlib.ROOT)
        lock = events_mod.Lock(testlib.log_file(self.workspace), "append")
        with mock.patch.object(events_mod.os, "unlink", unlink_then_lose_the_race):
            with self.assertRaises(events_mod.RecordsError) as caught:
                lock.acquire(break_lock=True)
        self.assertEqual(caught.exception.code, 7)
        document = caught.exception.document
        self.assertEqual(document["error"], "conflict")
        self.assertEqual(document["lock"]["pid"], os.getpid(), "the new holder's contents")
        self.assertEqual(document["broke_lock"]["pid"], 999999, "the stale lock it had removed")
        self.assertTrue(document["holder_alive"])
        self.assertFalse(lock.held)
        real_unlink(self.lock_path())

    def test_the_lock_is_released_after_a_refusal(self):
        head = self.open_log()
        code, _, _ = self.append([testlib.raised(identity=self.identity)], "d" * 64)
        self.assertEqual(code, 7)
        self.assertFalse(os.path.isfile(self.lock_path()))

    def test_an_unreadable_lock_is_still_reported(self):
        head = self.open_log()
        testlib.write(self.lock_path(), "not json at all")
        code, doc, _ = self.append([testlib.raised(identity=self.identity)], head)
        self.assertEqual(code, 7)
        self.assertIn("unreadable", doc["lock"])


class StateFromTheLog(unittest.TestCase):
    """The smallest piece of derived state slice 1 needs (section 9.2's deciding event)."""

    def test_the_last_deciding_event_wins(self):
        raised = {"kind": "finding_raised", "finding": "f1:" + "a" * 20}
        fixed = {"kind": "disposition", "finding": "f1:" + "a" * 20, "disposition": "fixed"}
        reopened = {"kind": "reopened", "finding": "f1:" + "a" * 20}
        waived = {"kind": "waived", "finding": "f1:" + "a" * 20}
        self.assertEqual(events_mod.finding_status([raised], "f1:" + "a" * 20), "open")
        self.assertEqual(events_mod.finding_status([raised, fixed], "f1:" + "a" * 20), "fixed")
        self.assertEqual(events_mod.finding_status([raised, fixed, reopened], "f1:" + "a" * 20), "open")
        self.assertEqual(events_mod.finding_status([raised, fixed, reopened, waived], "f1:" + "a" * 20), "waived")

    def test_a_finding_the_log_never_raised_has_no_status(self):
        self.assertIsNone(events_mod.finding_status([], "f1:" + "a" * 20))

    def test_a_not_fixed_disposition_leaves_it_open(self):
        raised = {"kind": "finding_raised", "finding": "f1:" + "a" * 20}
        not_fixed = {"kind": "disposition", "finding": "f1:" + "a" * 20, "disposition": "not_fixed"}
        self.assertEqual(events_mod.finding_status([raised, not_fixed], "f1:" + "a" * 20), "open")


if __name__ == "__main__":
    unittest.main()
