"""The outside review of 2026-09-20, ported attack by attack (findings 2 to 15).

Each class here is one numbered finding of the reviewer's closed checklist, and each test is
one of her probes turned into an assertion. Finding 1 was the contract's and is amendment A7;
it has no test here. The rulings the control room made before this round are cited where they
decide a shape the review left open (amendment A8 above all).

Nothing here is written into the worktree: every fixture is built under `testlib.make_scratch`
and removed in `tearDown`.
"""
import copy
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()
from records_core import (canon, events as events_mod, identity as identity_mod,  # noqa: E402
                          ids, importer as importer_mod, legacy, validate)

DOC = testlib.DOC


class ReviewCase(unittest.TestCase):
    """A git workspace, a batch directory, and the CLI helpers every finding below reuses."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-review-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def cli(self, *args):
        return testlib.run_json([str(a) for a in args])

    def append(self, events, head, doc=DOC, extra=None):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        return self.cli("append", "--workspace", self.workspace, "--doc", doc,
                        "--events", path, "--expect-head", head, *(extra or []))

    def write_doc(self, rel, text):
        testlib.write(os.path.join(self.workspace, *rel.split("/")), text)


# ---- finding 2: addresses collide, forbidden ledger paths, symlinked writes (A8) --------------

def document(rows, slice_name="A", date="2026-05-01"):
    return ("# Fixture\n\n## Slice %s\nStatus: built\n\n### %s - review: Slice %s\n%s\n"
            % (slice_name, date, slice_name, "\n".join(rows)))


FINDING_LINE = "- MAJOR · src/a.py:1 · alpha · scenario · A"


class TwoAddressesAreTwoLogs(ReviewCase):
    """Review finding 2. Amendment A8: the slug escapes `%` and `_` before `/` becomes `__`."""

    def test_a_document_named_with_underscores_does_not_share_a_log(self):
        self.assertNotEqual(events_mod.slug_of("docs/a/b.md"), events_mod.slug_of("docs/a__b.md"))

    def test_appending_through_the_second_document_does_not_land_in_the_first(self):
        first, second = "docs/a/b.md", "docs/a__b.md"
        code, doc, err = self.append([testlib.opened(doc=first), testlib.raised(doc=first)],
                                     testlib.ZERO, doc=first)
        self.assertEqual(code, 0, (doc, err))
        code, other, err = self.append([testlib.opened(doc=second)], testlib.ZERO, doc=second)
        self.assertEqual(code, 0, (other, err))
        self.assertNotEqual(doc["log"], other["log"])
        code, listing, err = self.cli("events", "--workspace", self.workspace, "--doc", second)
        self.assertEqual(code, 0, (listing, err))
        self.assertEqual([row["event"]["ledger_doc"] for row in listing["results"]], [second])

    def test_a_percent_in_a_name_is_escaped_before_the_underscore_rule(self):
        self.assertNotEqual(events_mod.slug_of("docs/a%5Fb.md"), events_mod.slug_of("docs/a_b.md"))


class ForbiddenLedgerAddresses(ReviewCase):
    """Review finding 2 and amendment A8: history and a mirror are never ledger addresses."""

    def test_a_document_under_docs_records_is_refused(self):
        self.write_doc("docs/records/spec.md", document([FINDING_LINE]))
        code, doc, err = self.cli("import-legacy", "--workspace", self.workspace,
                                  "--doc", "docs/records/spec.md")
        self.assertEqual(code, 4, (doc, err))
        self.assertEqual(doc["error"], "invalid")

    def test_a_verdict_doc_is_refused_as_a_ledger(self):
        self.write_doc("docs/reviews/verdict.md", document([FINDING_LINE]))
        code, doc, err = self.cli("import-legacy", "--workspace", self.workspace,
                                  "--doc", "docs/reviews/verdict.md")
        self.assertEqual(code, 4, (doc, err))
        self.assertEqual(doc["error"], "invalid")

    def test_every_command_refuses_the_two_forbidden_addresses(self):
        for command in ("verify", "state", "events", "mirrors"):
            for rel in ("docs/records/spec.md", "docs/reviews/verdict.md"):
                code, doc, err = self.cli(command, "--workspace", self.workspace, "--doc", rel)
                self.assertEqual(code, 4, (command, rel, doc, err))


class SymlinkedRecordsPathsAreRefused(ReviewCase):
    """Review finding 2 and amendment A8: a log, a lock, or docs/records/ reached by a link."""

    def test_a_symlinked_records_directory_is_refused_and_writes_nothing_outside(self):
        outside = os.path.join(self.scratch, "outside")
        os.makedirs(outside)
        os.makedirs(os.path.join(self.workspace, "docs"), exist_ok=True)
        os.symlink(outside, os.path.join(self.workspace, "docs", "records"))
        code, doc, err = self.append([testlib.opened(doc=DOC)], testlib.ZERO)
        self.assertEqual(code, 4, (doc, err))
        self.assertEqual(os.listdir(outside), [])

    def test_a_symlinked_log_is_refused_rather_than_read(self):
        path = events_mod.log_path(self.workspace, DOC)
        os.makedirs(os.path.dirname(path))
        target = os.path.join(self.workspace, "docs", "spec.md")
        event = dict(testlib.opened(doc=DOC), seq=0, prev=testlib.ZERO)
        testlib.write(target, canon.canonical_json(event).decode("utf-8") + "\n")
        os.symlink(target, path)
        code, doc, err = self.cli("verify", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 4, (doc, err))

    def test_a_symlinked_lock_is_refused(self):
        path = events_mod.log_path(self.workspace, DOC)
        os.makedirs(os.path.dirname(path))
        target = os.path.join(self.scratch, "lock-target")
        testlib.write(target, '{"pid": 999999, "pid_start": "dead"}\n')
        os.symlink(target, events_mod.lock_path(path))
        code, doc, err = self.append([testlib.opened(doc=DOC)], testlib.ZERO)
        self.assertEqual(code, 4, (doc, err))

    def test_a_document_reached_through_a_symlink_is_refused(self):
        real = os.path.join(self.scratch, "elsewhere")
        os.makedirs(real)
        os.symlink(real, os.path.join(self.workspace, "linked"))
        testlib.write(os.path.join(real, "a.md"), document([FINDING_LINE]))
        code, doc, err = self.cli("verify", "--workspace", self.workspace, "--doc", "linked/a.md")
        self.assertIn(code, (2, 4), (doc, err))


class EveryReaderChecksTheLogsOwner(ReviewCase):
    """Review finding 2 and amendment A8: an event that names another document is a conflict."""

    def _log_holding_a_foreign_event(self):
        code, doc, err = self.append([testlib.opened(doc=DOC), testlib.raised(doc=DOC)],
                                     testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        path = events_mod.log_path(self.workspace, DOC)
        with open(path, "rb") as fh:
            lines = fh.read().split(b"\n")[:-1]
        second = json.loads(lines[1].decode("utf-8"))
        second["ledger_doc"] = "docs/plans/other.md"
        with open(path, "wb") as fh:
            fh.write(lines[0] + b"\n" + canon.canonical_json(second) + b"\n")

    def test_verify_refuses_a_log_holding_another_documents_event(self):
        self._log_holding_a_foreign_event()
        code, doc, err = self.cli("verify", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 7, (doc, err))

    def test_state_refuses_a_log_holding_another_documents_event(self):
        self._log_holding_a_foreign_event()
        code, doc, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 7, (doc, err))


# ---- finding 3: what changed between validation and the write -------------------------------

class TheWriterCommitsWhatItValidated(ReviewCase):
    """Review finding 3, both interleaving probes: the log, and the source, changed in flight.

    The mutation happens after the component's own checks have run and returned, which is the
    window the writer had: it validated one snapshot and then re-read the file to build the
    bytes it wrote.
    """

    def _open_with_one_finding(self):
        code, doc, err = self.append([testlib.opened(self.identity),
                                      testlib.raised(identity=self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        return doc["head"], doc["appended"][1]["finding"]

    def _truncating_prepare(self, path):
        original = events_mod.prepare_batch

        def truncate(*args, **kwargs):
            prepared = original(*args, **kwargs)
            with open(path, "rb") as fh:
                first = fh.read().split(b"\n")[0]
            with open(path, "wb") as fh:
                fh.write(first + b"\n")
            return prepared
        return truncate

    def test_a_log_truncated_after_validation_stops_the_append(self):
        head, _ = self._open_with_one_finding()
        path = events_mod.log_path(self.workspace, DOC)
        with open(path, "rb") as fh:
            before = fh.read()
        truncate = self._truncating_prepare(path)
        saved = events_mod.prepare_batch
        events_mod.prepare_batch = truncate
        try:
            with self.assertRaises(events_mod.RecordsError) as caught:
                events_mod.append(self.workspace, DOC,
                                  [testlib.raised(identity=self.identity, claim="a second one")],
                                  head, testlib.schemas())
        finally:
            events_mod.prepare_batch = saved
        self.assertEqual(caught.exception.code, 7)
        with open(path, "rb") as fh:
            after = fh.read()
        self.assertNotEqual(after, before)  # the probe truncated it; the writer did not restore it
        self.assertTrue(before.startswith(after))
        code, doc, err = self.cli("verify", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, (doc, err))  # what is left is the old prefix, still a valid chain

    def test_a_log_truncated_after_validation_stops_the_import(self):
        self.write_doc(DOC, document([FINDING_LINE]))
        body = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(body["imported"])
        path = events_mod.log_path(self.workspace, DOC)
        with open(path, "rb") as fh:
            before = fh.read()
        self.write_doc(DOC, document([FINDING_LINE, "- MINOR · src/b.py:2 · beta · scenario · A"]))
        truncate = self._truncating_prepare(path)
        saved = events_mod.prepare_batch
        events_mod.prepare_batch = truncate
        try:
            with self.assertRaises(events_mod.RecordsError) as caught:
                testlib.import_doc(self.workspace, DOC)
        finally:
            events_mod.prepare_batch = saved
        self.assertEqual(caught.exception.code, 7)
        with open(path, "rb") as fh:
            after = fh.read()
        self.assertTrue(before.startswith(after))

    def test_a_source_changed_after_validation_stops_the_clear(self):
        head, finding = self._open_with_one_finding()
        original = events_mod.prepare_batch

        def change_the_source(*args, **kwargs):
            prepared = original(*args, **kwargs)
            testlib.write(os.path.join(self.workspace, "src", "widget.py"),
                          "def widget():\n    return 2\n")
            return prepared
        events_mod.prepare_batch = change_the_source
        try:
            with self.assertRaises(events_mod.RecordsError) as caught:
                events_mod.append(self.workspace, DOC,
                                  [testlib.disposition(finding, self.identity, doc=DOC)],
                                  head, testlib.schemas())
        finally:
            events_mod.prepare_batch = original
        self.assertEqual(caught.exception.code, 6)
        self.assertEqual(caught.exception.document["error"], "stale_source")
        code, state, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, (state, err))
        self.assertEqual(state["findings"][0]["status"], "open")


# ---- finding 4: the lock is an inode, not a pathname ----------------------------------------

class TheLockIsAnInode(ReviewCase):
    """Review finding 4: recovery stole a replacement lock and release deleted another's.

    The lock is now held open for its whole life, with an advisory `flock` on it; ownership is
    the (device, inode) pair of the file this process created, never the pathname.
    """

    def setUp(self):
        ReviewCase.setUp(self)
        self.log = events_mod.log_path(self.workspace, DOC)
        os.makedirs(os.path.dirname(self.log), exist_ok=True)
        self.lock_file = events_mod.lock_path(self.log)

    def test_a_lock_file_that_is_json_of_the_wrong_shape_is_a_refusal(self):
        code, doc, err = self.append([testlib.opened(self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        testlib.write(self.lock_file, "[]\n")
        code, doc, err = self.append([testlib.raised(identity=self.identity)], doc["head"])
        self.assertEqual(code, 7, (doc, err))
        self.assertEqual(doc["error"], "conflict")
        self.assertIn("unreadable", doc["lock"])
        self.assertNotIn("Traceback", err)

    def test_recovery_refuses_a_lock_whose_inode_another_holder_owns(self):
        """The recorded pid is dead, but the inode is held: a live writer took it over."""
        holder = events_mod.Lock(self.log, "append").acquire()
        try:
            with open(self.lock_file, "r+", encoding="utf-8") as fh:
                fh.seek(0)
                fh.write(json.dumps({"pid": 999999, "pid_start": "dead", "command": "append"}))
                fh.truncate()
            breaker = events_mod.Lock(self.log, "append")
            with self.assertRaises(events_mod.RecordsError) as caught:
                breaker.acquire(break_lock=True)
            self.assertEqual(caught.exception.code, 7)
            self.assertFalse(breaker.held)
            self.assertTrue(os.path.isfile(self.lock_file))
        finally:
            holder.release()

    def test_releasing_leaves_a_replacement_lock_alone(self):
        first = events_mod.Lock(self.log, "append").acquire()
        os.unlink(self.lock_file)
        second = events_mod.Lock(self.log, "append").acquire()
        try:
            first.release()
            self.assertTrue(os.path.isfile(self.lock_file),
                            "the first holder must not delete the second holder's lock")
        finally:
            second.release()
        self.assertFalse(os.path.isfile(self.lock_file))

    def test_a_write_stops_when_the_lock_was_replaced_under_it(self):
        lock = events_mod.Lock(self.log, "append").acquire()
        try:
            os.unlink(self.lock_file)
            replacement = events_mod.Lock(self.log, "append").acquire()
            try:
                with self.assertRaises(events_mod.RecordsError) as caught:
                    lock.assert_owned()
                self.assertEqual(caught.exception.code, 7)
            finally:
                replacement.release()
        finally:
            lock.release()


# ---- finding 5: two answers for one line ------------------------------------------------------

TWO_FINDINGS = document(["- MAJOR · src/a.py:1 · alpha · scenario · A",
                         "- MAJOR · src/a.py:1 · beta · scenario · A"])
AMBIGUOUS_CLEAR = ("\n### 2026-05-02 - recheck: Slice A\n"
                   "- MAJOR · src/a.py:1 · (unknown) · fixed · checked\n")


class ContradictoryAnswersAreRefused(ReviewCase):
    """Review finding 5: two answers for one line silently kept the first."""

    def setUp(self):
        ReviewCase.setUp(self)
        self.write_doc(DOC, TWO_FINDINGS + AMBIGUOUS_CLEAR)
        code, body, err = self.cli("import-legacy", "--workspace", self.workspace,
                                   "--doc", DOC, "--dry-run")
        self.assertEqual(code, 5, (body, err))
        self.question = body["ambiguities"][0]
        self.assertEqual(len(self.question["candidates"]), 2)

    def answers(self, *findings):
        return {"answered_by": "the review", "answered_on": "2026-05-03", "doc": DOC,
                "answers": [{"line": self.question["line"], "raw": self.question["raw"],
                             "finding": finding} for finding in findings]}

    def run_with(self, answers):
        path = testlib.write_json(os.path.join(self.scratch, "answers.json"), answers)
        return self.cli("import-legacy", "--workspace", self.workspace, "--doc", DOC,
                        "--resolutions", path, "--dry-run")

    def test_two_answers_for_one_line_are_refused(self):
        first, second = (c["finding"] for c in self.question["candidates"])
        code, body, err = self.run_with(self.answers(first, second))
        self.assertEqual(code, 4, (body, err))
        self.assertIn(str(self.question["line"]), body["reason"])

    def test_one_answer_for_that_line_still_works(self):
        first = self.question["candidates"][0]["finding"]
        code, body, err = self.run_with(self.answers(first))
        self.assertEqual(code, 0, (body, err))
        self.assertEqual(body["counts"]["resolution_applied"], 1)


# ---- finding 6: a tag is presentation at every location of a field (A8) ----------------------

class MultiLocationTagsAreNotIdentity(ReviewCase):
    """Review finding 6 and amendment A8: section 7's tag rule has no single-location exception."""

    RAW = "src/a.py:1, src/b.py:2"

    def test_the_tag_falls_out_of_the_key_of_a_multi_location_field(self):
        self.assertEqual(ids.location_key(legacy.tolerant_location(self.RAW + " (tag)")),
                         ids.location_key(legacy.tolerant_location(self.RAW)))

    def test_the_same_finding_tagged_and_untagged_is_one_identity(self):
        events = [testlib.opened(self.identity),
                  testlib.raised(identity=self.identity,
                                 loc=legacy.tolerant_location(self.RAW)),
                  testlib.raised(identity=self.identity,
                                 loc=legacy.tolerant_location(self.RAW + " (tag)"))]
        code, body, err = self.append(events, testlib.ZERO)
        self.assertEqual(code, 5, (body, err))
        self.assertEqual(body["error"], "ambiguous_identity")
        self.assertEqual(testlib.read_log(self.workspace), b"")


# ---- finding 9: a grant carries the grant's date ---------------------------------------------

class AGrantKeepsItsOwnDate(ReviewCase):
    """Review finding 9: a waiver inherited its enclosing heading's date, against section 11.7."""

    def test_a_waiver_under_an_earlier_heading_is_dated_by_its_grant(self):
        self.write_doc(DOC, document(["- MAJOR · src/a.py:1 · alpha · scenario · A"])
                       + "WAIVED (per user) · 2026-06-09 · MAJOR · src/a.py:1 · alpha\n")
        body = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(body["imported"])
        waivers = [e for e in testlib.events_of(self.workspace, DOC) if e["kind"] == "waived"]
        self.assertEqual(len(waivers), 1, waivers)
        self.assertEqual(waivers[0]["grant_date"], "2026-06-09")
        self.assertEqual(waivers[0]["at"], "2026-06-09")

    def test_a_reopening_under_an_earlier_heading_is_dated_by_its_grant(self):
        self.write_doc(DOC, document(["- MAJOR · src/a.py:1 · alpha · scenario · A"])
                       + "REOPENED (per user) · 2026-06-11 · src/a.py:1 · alpha\n")
        body = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(body["imported"])
        reopenings = [e for e in testlib.events_of(self.workspace, DOC) if e["kind"] == "reopened"]
        self.assertEqual(len(reopenings), 1, reopenings)
        self.assertEqual(reopenings[0]["at"], "2026-06-11")


# ---- finding 10: a preview promises only what the writer would take --------------------------

class ThePreviewValidatesTheBatch(ReviewCase):
    """Review finding 10: `--dry-run` never called `prepare_batch`, so it promised a bad batch."""

    IMPOSSIBLE = document(["- MAJOR · src/a.py:1 · alpha · scenario · A"], date="2026-02-30")

    def test_a_preview_of_a_batch_the_writer_refuses_refuses_too(self):
        self.write_doc(DOC, self.IMPOSSIBLE)
        dry = self.cli("import-legacy", "--workspace", self.workspace, "--doc", DOC, "--dry-run")
        landed = self.cli("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(landed[0], 4, landed)
        self.assertEqual(dry[0], landed[0], (dry, landed))

    def test_a_preview_of_a_good_document_still_reports_what_it_would_append(self):
        self.write_doc(DOC, document([FINDING_LINE]))
        code, body, err = self.cli("import-legacy", "--workspace", self.workspace,
                                   "--doc", DOC, "--dry-run")
        self.assertEqual(code, 0, (body, err))
        self.assertTrue(body["would_import"])
        self.assertEqual(testlib.read_log(self.workspace), b"")


# ---- finding 14: record bytes, and the bullets that fit no shape -----------------------------

class RecordTextIsKeptByteForByte(ReviewCase):
    """Review finding 14: trailing whitespace was normalized away when recording and comparing."""

    def test_a_trailing_space_added_to_an_imported_line_is_a_conflict(self):
        self.write_doc(DOC, document([FINDING_LINE]))
        first = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(first["imported"])
        self.write_doc(DOC, document([FINDING_LINE + "  "]))
        with self.assertRaises(events_mod.RecordsError) as caught:
            testlib.import_doc(self.workspace, DOC)
        self.assertEqual(caught.exception.code, 7)
        self.assertEqual(caught.exception.document["error"], "conflict")

    def test_an_unchanged_document_still_appends_nothing(self):
        self.write_doc(DOC, document([FINDING_LINE]))
        testlib.import_doc(self.workspace, DOC)
        before = testlib.read_log(self.workspace)
        again = testlib.import_doc(self.workspace, DOC)
        self.assertEqual(again["imported"], 0)
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_a_record_bullet_that_fits_no_shape_is_kept_and_reported(self):
        self.write_doc(DOC, document([FINDING_LINE, "- a line with no separator"]))
        body = testlib.import_doc(self.workspace, DOC)
        self.assertEqual(body["counts"].get("legacy_unparsed"), 1, body["counts"])
        unparsed = [e for e in testlib.events_of(self.workspace, DOC)
                    if e["kind"] == "legacy_unparsed"]
        self.assertEqual(len(unparsed), 1)
        self.assertEqual(unparsed[0]["origin"]["raw"], "- a line with no separator")

    def test_a_bullet_outside_a_record_heading_is_not_a_record(self):
        text = document([FINDING_LINE]) + "\n## Notes\n\n- an ordinary prose bullet\n"
        self.write_doc(DOC, text)
        body = testlib.import_doc(self.workspace, DOC)
        self.assertIsNone(body["counts"].get("legacy_unparsed"), body["counts"])


# ---- finding 7: the schemas are offered to consumers as the interface ------------------------

def valid_example(name):
    with open(os.path.join(testlib.REFERENCES, "examples", "valid", name), encoding="utf-8") as fh:
        return json.load(fh)


class TheSchemaIsTheInterface(ReviewCase):
    """Review finding 7: a constraint the wrapper enforces and a schema can express belongs in
    the schema too, because consumers are handed the schemas as the interface."""

    def raw_errors(self, event):
        return [e.message for e in testlib.schemas().event.iter_errors(event)]

    def test_the_standalone_schema_refuses_an_unknown_version(self):
        event = dict(valid_example("finding_raised.json"), v=2)
        self.assertTrue(self.raw_errors(event))

    def test_the_standalone_schema_refuses_a_claim_holding_a_line_break(self):
        event = dict(valid_example("finding_raised.json"), claim="alpha\nbeta")
        self.assertTrue(self.raw_errors(event))

    def test_the_standalone_schema_refuses_a_claim_holding_the_separator(self):
        event = dict(valid_example("finding_raised.json"), claim="alpha · beta")
        self.assertTrue(self.raw_errors(event))

    def test_the_standalone_schema_still_accepts_a_claimless_finding(self):
        event = dict(valid_example("finding_raised.json"), claim=None)
        self.assertEqual(self.raw_errors(event), [])

    def test_the_standalone_schema_keeps_a_legacy_scenarios_separator(self):
        event = valid_example("finding_raised-legacy-joined-scenario.json")
        self.assertIn(" · ", event["scenario"])
        self.assertEqual(self.raw_errors(event), [])

    def test_a_native_scenario_may_not_hold_the_separator(self):
        event = dict(valid_example("finding_raised.json"), scenario="alpha · beta")
        self.assertTrue(self.raw_errors(event))

    def test_a_legacy_event_names_the_importer_station_and_an_unknown_source(self):
        event = valid_example("disposition-legacy-unbound.json")
        self.assertEqual(self.raw_errors(event), [])
        self.assertTrue(self.raw_errors(dict(
            event, actor=dict(event["actor"], station="signoff"))))
        self.assertTrue(self.raw_errors(dict(event, source={"known": True, "identity": self.identity})))

    def test_a_ledger_doc_that_is_not_a_ledger_address_is_refused(self):
        for bad in ("docs/records/spec.md", "docs/reviews/verdict.md", "/absolute/a.md",
                    "docs/../a.md", "notes.txt"):
            self.assertTrue(self.raw_errors(dict(valid_example("finding_raised.json"),
                                                 ledger_doc=bad)), bad)

    def test_both_import_brackets_carry_the_same_three_fields(self):
        for name in ("import_started.json", "import_finished.json"):
            event = valid_example(name)
            for field in ("doc_sha256", "lines_read", "counts"):
                self.assertIn(field, event, name)
                mutated = dict(event)
                mutated.pop(field)
                self.assertTrue(validate.validate_event(mutated, testlib.schemas()),
                                "%s without /%s is still accepted" % (name, field))

    def test_an_import_writes_both_brackets_with_their_counts(self):
        self.write_doc(DOC, document([FINDING_LINE]))
        testlib.import_doc(self.workspace, DOC)
        brackets = [e for e in testlib.events_of(self.workspace, DOC)
                    if e["kind"] in ("import_started", "import_finished")]
        self.assertEqual(len(brackets), 2)
        for event in brackets:
            self.assertIn("lines_read", event)
            self.assertIn("counts", event)
            self.assertEqual(event["doc_sha256"], testlib.doc_sha256(self.workspace, DOC))
        self.assertEqual(brackets[0]["counts"], brackets[1]["counts"])

    def test_a_state_findings_location_is_a_location(self):
        code, doc, err = self.append([testlib.opened(self.identity),
                                      testlib.raised(identity=self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        code, state, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, (state, err))
        self.assertEqual(validate.validate_document("state", state, testlib.schemas()), [])
        broken = copy.deepcopy(state)
        broken["findings"][0]["location"] = {"arbitrary": True}
        self.assertTrue(validate.validate_document("state", broken, testlib.schemas()))

    def test_verify_refuses_a_line_that_is_not_canonical_json(self):
        code, doc, err = self.append([testlib.opened(self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        path = events_mod.log_path(self.workspace, DOC)
        with open(path, encoding="utf-8") as fh:
            event = json.loads(fh.read())
        testlib.write(path, json.dumps(event, sort_keys=False) + "\n")
        code, doc, err = self.cli("verify", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 4, (doc, err))
        self.assertIn("canonical", doc["reason"])


# ---- finding 8: derived state names the source a clear was decided against -------------------

class DerivedStateNamesTheClearingSource(ReviewCase):
    """Review finding 8 and contract section 8.4: state dropped `_deciding_source` and offered
    nothing in its place, so a reader could not see the source a finding was cleared against."""

    def cleared_state(self):
        code, doc, err = self.append([testlib.opened(self.identity),
                                      testlib.raised(identity=self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        finding = doc["appended"][1]["finding"]
        code, doc, err = self.append([testlib.disposition(finding, self.identity)], doc["head"])
        self.assertEqual(code, 0, (doc, err))
        code, state, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, (state, err))
        return state

    def test_a_cleared_finding_reports_the_source_it_was_cleared_against(self):
        state = self.cleared_state()
        row = state["findings"][0]
        self.assertEqual(row["status"], "fixed")
        self.assertEqual(row["verified_source"]["known"], True)
        self.assertEqual(row["verified_source"]["identity"]["commit"], self.identity["commit"])
        self.assertEqual(validate.validate_document("state", state, testlib.schemas()), [])

    def test_an_open_finding_names_no_source(self):
        code, doc, err = self.append([testlib.opened(self.identity),
                                      testlib.raised(identity=self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        code, state, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, (state, err))
        self.assertIsNone(state["findings"][0]["verified_source"])

    def test_an_imported_clear_reports_its_unbound_source(self):
        self.write_doc(DOC, document([FINDING_LINE])
                       + "\n### 2026-05-02 - recheck: Slice A\n"
                         "- MAJOR · src/a.py:1 · (alpha) · fixed · checked\n")
        testlib.import_doc(self.workspace, DOC)
        code, state, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, (state, err))
        row = state["findings"][0]
        self.assertTrue(row["cleared_unbound"])
        self.assertEqual(row["verified_source"], {"known": False})

    def test_the_state_schema_requires_the_field(self):
        state = self.cleared_state()
        del state["findings"][0]["verified_source"]
        self.assertTrue(validate.validate_document("state", state, testlib.schemas()))


# ---- finding 15: what an interrupted write really leaves behind ------------------------------

class InterruptedWritesAreReported(ReviewCase):
    """Review finding 15: the lock was called "the one partial effect"; a kill during the atomic
    replacement also leaves a sibling temporary file, which `--break-lock` now names."""

    def stale_lock(self):
        path = events_mod.log_path(self.workspace, DOC)
        testlib.write(events_mod.lock_path(path),
                      json.dumps({"pid": 999999, "pid_start": "Wed Apr  1 09:00:00 2026",
                                  "command": "append"}))

    def orphan(self):
        path = events_mod.log_path(self.workspace, DOC)
        name = "." + os.path.basename(path) + ".cico_2_s.tmp"
        testlib.write(os.path.join(os.path.dirname(path), name), "{}\n")
        return name

    def test_break_lock_names_an_orphan_temporary_file_and_keeps_it(self):
        code, doc, err = self.append([testlib.opened(self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        name = self.orphan()
        self.stale_lock()
        code, doc, err = self.append([testlib.raised(identity=self.identity)], doc["head"],
                                     extra=["--break-lock"])
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["orphan_temporaries"],
                         [events_mod.RECORDS_DIR + "/" + name])
        path = os.path.join(os.path.dirname(events_mod.log_path(self.workspace, DOC)), name)
        self.assertTrue(os.path.isfile(path), "an orphan is reported, never deleted")

    def test_break_lock_with_no_orphan_says_so(self):
        code, doc, err = self.append([testlib.opened(self.identity)], testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        self.stale_lock()
        code, doc, err = self.append([testlib.raised(identity=self.identity)], doc["head"],
                                     extra=["--break-lock"])
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["orphan_temporaries"], [])

    def test_an_import_under_break_lock_names_them_too(self):
        self.write_doc(DOC, document([FINDING_LINE]))
        testlib.import_doc(self.workspace, DOC)
        name = self.orphan()
        self.stale_lock()
        self.write_doc(DOC, document([FINDING_LINE, "- MINOR · src/b.py:2 · beta · scenario · A"]))
        body = testlib.import_doc(self.workspace, DOC, break_lock=True)
        self.assertEqual(body["orphan_temporaries"], [events_mod.RECORDS_DIR + "/" + name])

    def test_the_interface_documents_the_partial_effects(self):
        with open(os.path.join(testlib.REFERENCES, "interface.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(".tmp", text)
        self.assertIn("orphan_temporaries", text)


# ---- finding 12: the document and the execution say the same thing --------------------------

class TheDocumentedInterfaceIsTheRealOne(ReviewCase):
    """Review finding 12: six places where `interface.md` and the CLI disagreed."""

    def interface_text(self):
        with open(os.path.join(testlib.REFERENCES, "interface.md"), encoding="utf-8") as fh:
            return fh.read()

    def test_at_source_refuses_something_that_is_not_an_identity(self):
        path = testlib.write_json(os.path.join(self.scratch, "garbage.json"),
                                  {"commit": "garbage"})
        code, out, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC,
                                  "--at-source", path)
        self.assertEqual(code, 2, (out, err))
        self.assertEqual(out, None)
        self.assertTrue(err.strip())

    def test_at_source_still_takes_a_real_identity_and_a_response_carrying_one(self):
        for body in (self.identity, {"identity": self.identity}):
            path = testlib.write_json(os.path.join(self.scratch, "identity.json"), body)
            code, out, err = self.cli("state", "--workspace", self.workspace, "--doc", DOC,
                                      "--at-source", path)
            self.assertEqual(code, 0, (out, err))

    def test_a_missing_document_is_a_usage_error_on_stderr(self):
        for command, extra in (("import-legacy", ["--dry-run"]), ("mirrors", [])):
            code, out, err = testlib.run_cli(
                [command, "--workspace", self.workspace, "--doc", "docs/plans/missing.md"] + extra)
            self.assertEqual(code, 2, (command, out, err))
            self.assertEqual(out, "", command)
            self.assertTrue(err.strip(), command)

    def test_component_identity_answers_without_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.scratch)
        code, out, err = self.cli_with_stub(stub, "component-identity")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["name"], "records")
        self.assertEqual(out["interface_version"], 1)

    def test_every_other_command_still_needs_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.scratch)
        for command, args in (("verify", ["--workspace", self.workspace, "--doc", DOC]),
                              ("identity", ["--workspace", self.workspace]),
                              ("survey", ["--workspace", self.workspace])):
            code, out, err = testlib.run_cli([command] + args, env={"PYTHONPATH": stub})
            self.assertEqual(code, 3, (command, out, err))
            self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY, command)

    def cli_with_stub(self, stub, *args):
        code, out, err = testlib.run_json([str(a) for a in args], env={"PYTHONPATH": stub})
        return code, out, err

    def test_no_environment_variable_changes_what_the_component_does(self):
        for env in ({"RECORDS_TEST": "1", "RECORDS_TEST_NO_JSONSCHEMA": "1"},
                    {"RECORDS_TEST_NO_JSONSCHEMA": "1"}):
            code, out, err = testlib.run_json(["component-identity"], env=env)
            self.assertEqual(code, 0, err)
        with open(os.path.join(testlib.SCRIPTS, "records_core", "validate.py"),
                  encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("RECORDS_TEST_NO_JSONSCHEMA", source)
        self.assertNotIn("RECORDS_TEST_NO_JSONSCHEMA", self.interface_text())

    def test_the_interface_names_every_hook_that_exists(self):
        text = self.interface_text()
        self.assertIn("`--component-root`", text)
        for name in ("RECORDS_TEST", "RECORDS_TEST_NO_JSONSCHEMA"):
            self.assertNotIn(name, text, "interface.md names a hook that no longer exists")

    def test_an_empty_tracked_diff_hashes_to_the_hash_of_empty_bytes(self):
        code, doc, err = self.cli("identity", "--workspace", self.workspace)
        self.assertEqual(code, 0, (doc, err))
        empty = canon.sha256_hex(b"")
        self.assertEqual(doc["identity"]["tracked_diff_sha256"], empty)
        self.assertNotEqual(empty, "0" * 64)
        self.assertIn(empty, self.interface_text(),
                      "interface.md still promises 64 zeros for an empty diff")

    def test_an_untracked_file_alone_makes_the_workspace_dirty(self):
        testlib.write(os.path.join(self.workspace, "src", "new.py"), "x = 1\n")
        code, doc, err = self.cli("identity", "--workspace", self.workspace)
        self.assertEqual(code, 0, (doc, err))
        self.assertTrue(doc["identity"]["dirty"])
        self.assertEqual(doc["identity"]["untracked"], ["src/new.py"])

    def test_the_interface_documents_the_predecessor_fields(self):
        text = self.interface_text()
        for field in ("| `prev` |", "| `expected_prev` |"):
            self.assertIn(field, text)


# ---- item 16 (amendment A9): a claim the separator cut in half -------------------------------

class AClaimTheSeparatorCutIsAmbiguous(ReviewCase):
    """Amendment A9 (1): `(alpha · beta)` is not a claim of `(alpha` with the rest elsewhere."""

    CUT = "- MAJOR · src/a.py:1 · (alpha · beta) · scenario · A"

    def test_the_import_stops_and_names_the_line(self):
        self.write_doc(DOC, document([self.CUT]))
        code, body, err = self.cli("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 5, (body, err))
        lines = [stop["line"] for stop in body["ambiguities"]]
        self.assertIn(7, lines, body["ambiguities"])
        self.assertEqual(testlib.read_log(self.workspace), b"")

    def test_it_is_never_imported_with_the_claim_cut(self):
        self.write_doc(DOC, document([self.CUT]))
        with self.assertRaises(events_mod.RecordsError) as caught:
            testlib.import_doc(self.workspace, DOC)
        self.assertEqual(caught.exception.code, 5)
        self.assertNotIn("(alpha", json.dumps(caught.exception.document.get("ambiguities"))[:0] or "")
        plan = testlib.plan_for(self.workspace, DOC)
        claims = [e.get("claim") for e in plan["events"] if e["kind"] == "finding_raised"]
        self.assertNotIn("(alpha", claims)

    def test_a_resolutions_answer_settles_it(self):
        self.write_doc(DOC, document([self.CUT]))
        code, body, err = self.cli("import-legacy", "--workspace", self.workspace,
                                   "--doc", DOC, "--dry-run")
        self.assertEqual(code, 5, (body, err))
        question = body["ambiguities"][0]
        answers = {"answered_by": "the owner", "answered_on": "2026-05-03", "doc": DOC,
                   "answers": [{"line": question["line"], "raw": question["raw"],
                                "skip": True, "why": "the claim is not readable from this line"}]}
        path = testlib.write_json(os.path.join(self.scratch, "answers.json"), answers)
        code, body, err = self.cli("import-legacy", "--workspace", self.workspace, "--doc", DOC,
                                   "--resolutions", path)
        self.assertEqual(code, 0, (body, err))
        kinds = [e["kind"] for e in testlib.events_of(self.workspace, DOC)]
        self.assertIn("resolution_applied", kinds)
        self.assertIn("legacy_unparsed", kinds)
        self.assertNotIn("finding_raised", kinds)

    def test_a_balanced_parenthesized_claim_is_still_an_ordinary_claim(self):
        self.write_doc(DOC, document(["- MAJOR · src/a.py:1 · (alpha) · scenario · A"]))
        body = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(body["imported"])
        raised = [e for e in testlib.events_of(self.workspace, DOC)
                  if e["kind"] == "finding_raised"]
        self.assertEqual(raised[0]["claim"], "alpha")  # the pilot's wrapping-parenthesis rule


# ---- item 17 (amendment A9): scenario text builds an ID and never joins a clear --------------

SHARED = document(["- MAJOR · src/a.py:1 · () · the widget spins · A",
                   "- MAJOR · src/a.py:1 · beta · scenario · A"])
ALONE = document(["- MAJOR · src/a.py:1 · () · the widget spins · A"])
CLEAR = ("\n### 2026-05-02 - recheck: Slice A\n"
         "- MAJOR · src/a.py:1 · (the widget spins) · fixed · checked\n")


class ScenarioTextNeverJoinsAClear(ReviewCase):
    """Amendment A9 (2): the scenario stands in for a missing claim when the ID is built, and
    at no other moment. A claim-less finding at a shared location is ambiguous."""

    def test_a_claimless_finding_at_a_shared_location_stops_the_document(self):
        self.write_doc(DOC, SHARED + CLEAR)
        code, body, err = self.cli("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 5, (body, err))
        self.assertEqual([stop["line"] for stop in body["ambiguities"]], [11])
        self.assertEqual(testlib.read_log(self.workspace), b"")

    def test_a_claimless_finding_on_its_own_still_joins_but_never_as_exact(self):
        self.write_doc(DOC, ALONE + CLEAR)
        body = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(body["imported"])
        clears = [e for e in testlib.events_of(self.workspace, DOC) if e["kind"] == "disposition"]
        self.assertEqual(len(clears), 1)
        self.assertEqual(clears[0]["join_basis"], "location_only")

    def test_the_scenario_still_builds_the_finding_id(self):
        """Section 7 is unchanged: with no claim, the claim key is the scenario."""
        self.write_doc(DOC, ALONE)
        testlib.import_doc(self.workspace, DOC)
        raised = [e for e in testlib.events_of(self.workspace, DOC)
                  if e["kind"] == "finding_raised"][0]
        self.assertEqual(raised["finding"],
                         ids.finding_id(DOC, "A", raised["location"], None, "the widget spins"))
        self.assertNotEqual(raised["finding"],
                            ids.finding_id(DOC, "A", raised["location"], None, None))

    def test_an_exact_join_still_needs_the_claim_itself(self):
        self.write_doc(DOC, document(["- MAJOR · src/a.py:1 · alpha · scenario · A",
                                      "- MAJOR · src/b.py:2 · beta · scenario · A"])
                       + "\n### 2026-05-02 - recheck: Slice A\n"
                         "- MAJOR · src/a.py:1 · (alpha) · fixed · checked\n")
        body = testlib.import_doc(self.workspace, DOC)
        self.assertTrue(body["imported"])
        clears = [e for e in testlib.events_of(self.workspace, DOC) if e["kind"] == "disposition"]
        self.assertEqual(clears[0]["join_basis"], "exact")


# ---- item 18 (amendment A9): survey is bounded -----------------------------------------------

class SurveyIsBounded(ReviewCase):
    """Amendment A9 (3): interface version 1 promises bounded output."""

    def survey(self, *args):
        return self.cli("survey", "--workspace", testlib.REPO, *args)

    def test_it_returns_fifty_documents_by_default_and_says_it_truncated(self):
        code, body, err = self.survey()
        self.assertEqual(code, 0, err)
        self.assertEqual(body["offset"], 0)
        self.assertEqual(body["returned"], len(body["documents"]))
        self.assertLessEqual(body["returned"], 50)
        self.assertGreater(body["total"], 50, "this repository no longer has 50 documents to page")
        self.assertEqual(body["returned"], 50)
        self.assertTrue(body["truncated"])

    def test_a_limit_and_an_offset_page_through_in_path_order(self):
        first = self.survey("--limit", "3")[1]
        second = self.survey("--limit", "3", "--offset", "3")[1]
        self.assertEqual([row["doc"] for row in first["documents"]],
                         sorted(row["doc"] for row in first["documents"]))
        self.assertEqual(first["offset"], 0)
        self.assertEqual(second["offset"], 3)
        self.assertEqual(len(second["documents"]), 3)
        self.assertEqual(first["total"], second["total"])
        self.assertNotEqual([r["doc"] for r in first["documents"]],
                            [r["doc"] for r in second["documents"]])

    def test_the_counts_still_cover_every_document(self):
        whole = self.survey("--limit", str(10 ** 6))[1]
        page = self.survey("--limit", "1")[1]
        self.assertEqual(page["counts"], whole["counts"])
        self.assertEqual(page["total"], whole["total"])
        self.assertEqual(page["returned"], 1)
        self.assertFalse(whole["truncated"])

    def test_an_offset_past_the_end_returns_nothing_and_still_counts_everything(self):
        whole = self.survey("--limit", str(10 ** 6))[1]
        past = self.survey("--offset", str(whole["total"] + 10))[1]
        self.assertEqual(past["documents"], [])
        self.assertEqual(past["returned"], 0)
        self.assertEqual(past["counts"], whole["counts"])
        self.assertEqual(past["total"], whole["total"])
        self.assertTrue(past["truncated"], "a page holding none of them left all of them out")

    def test_a_limit_or_an_offset_that_is_not_a_whole_number_is_a_usage_error(self):
        for args in (["--limit", "-1"], ["--limit", "two"], ["--offset", "-1"],
                     ["--offset", "1.5"]):
            code, out, err = testlib.run_cli(["survey", "--workspace", self.workspace] + args)
            self.assertEqual(code, 2, (args, out, err))
            self.assertEqual(out, "", args)

    def test_the_response_still_validates_against_its_schema(self):
        code, body, err = self.survey("--limit", "4")
        self.assertEqual(code, 0, err)
        self.assertEqual(validate.validate_document("import_report", body, testlib.schemas()), [])

    def test_the_interface_and_the_help_document_the_two_arguments(self):
        with open(os.path.join(testlib.REFERENCES, "interface.md"), encoding="utf-8") as fh:
            text = fh.read()
        for phrase in ("--limit", "--offset", "`truncated`", "`total`", "`returned`"):
            self.assertIn(phrase, text, phrase)
        code, out, err = testlib.run_cli(["survey", "--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("--limit", out)
        self.assertIn("--offset", out)


if __name__ == "__main__":
    unittest.main()
