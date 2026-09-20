"""Derived state (contract section 9) and the source comparison of section 8.4.

The contract's required tests for slice 2: "the same log gives byte-equal state on two runs;
the open filter's 'later wins' on a fixed, reopened, fixed sequence; `cleared_unbound`;
`card_drift`". The first and the third run through the CLI against a real log; the second is
built natively with `append`, so the sequence is one a station could really write.
"""
import copy
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import canon, events as events_mod, identity as identity_mod, state as state_mod, validate  # noqa: E402

DOC = testlib.DOC
PLANS = "docs/plans/"
GRANTS = PLANS + "2026-05-05-grants.md"
CARDS = PLANS + "2026-05-08-cards.md"
PUNCH = "docs/punch-list.md"


class NativeLog(unittest.TestCase):
    """A log a station wrote, so the sequences under test are ones `append` really accepts."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-state-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)
        self.head = self.append_ok([testlib.opened(self.identity),
                                    testlib.raised(identity=self.identity)], testlib.ZERO)
        code, doc, _ = testlib.run_json(["events", "--workspace", self.workspace, "--doc", DOC,
                                         "--kind", "finding_raised"])
        self.finding = doc["results"][0]["event"]["finding"]

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def append(self, events, head=None):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        return testlib.run_json(["append", "--workspace", self.workspace, "--doc", DOC,
                                 "--events", path, "--expect-head", head or self.head])

    def append_ok(self, events, head=None):
        code, doc, err = self.append(events, head)
        self.assertEqual(code, 0, (doc, err))
        self.head = doc["head"]
        return doc["head"]

    def state(self, *extra):
        code, doc, err = testlib.run_json(
            ["state", "--workspace", self.workspace, "--doc", DOC] + list(extra))
        self.assertEqual(code, 0, err)
        return doc

    def reopening(self, words="bring it back"):
        return testlib.native("reopened", at="2026-04-01T12:00:00Z", identity=self.identity,
                              finding=self.finding, words=words, grant_date="2026-04-01",
                              join_basis=None)


class LaterWins(NativeLog):
    """Appendix A's open filter with the finding id as the join key (section 9.2)."""

    def test_a_fixed_reopened_fixed_sequence_ends_fixed(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        self.assertEqual(self.state()["findings"][0]["status"], "fixed")
        self.append_ok([self.reopening()])
        self.assertEqual(self.state()["findings"][0]["status"], "open")
        self.append_ok([testlib.disposition(self.finding, self.identity,
                                            how="ran the widget suite again")])
        final = self.state()["findings"][0]
        self.assertEqual(final["status"], "fixed")
        self.assertEqual(final["events"], [1, 2, 3, 4])
        self.assertEqual(final["decided"], {"log": events_mod.log_relpath(DOC), "seq": 4},
                         "the deciding event is the LAST that names the finding, not the first")
        self.assertEqual(final["raised"], {"log": events_mod.log_relpath(DOC), "seq": 1})

    def test_the_deciding_event_is_the_last_one_whatever_its_date_says(self):
        """E12-4: a date on an event is information, never an ordering key."""
        self.append_ok([testlib.disposition(self.finding, self.identity,
                                            at="2026-04-09T09:00:00Z")])
        older = self.reopening()
        older["at"] = "2026-04-02T09:00:00Z"
        older["grant_date"] = "2026-04-02"
        self.append_ok([older])
        self.assertEqual(self.state()["findings"][0]["status"], "open")

    def test_a_not_fixed_disposition_leaves_it_open_and_still_decides(self):
        self.append_ok([testlib.disposition(self.finding, self.identity, value="not_fixed",
                                            verified={"known": False})])
        row = self.state()["findings"][0]
        self.assertEqual(row["status"], "open")
        self.assertIsNotNone(row["decided"])
        self.assertFalse(row["cleared_unbound"], "nothing cleared it, so nothing is unbound")

    def test_a_waiver_clears_and_a_later_reopening_opens_again(self):
        waiver = testlib.native("waived", at="2026-04-01T13:00:00Z", identity=self.identity,
                                finding=self.finding, severity="BLOCKER", words="accepted",
                                grant_date="2026-04-01",
                                verified_source={"known": True,
                                                 "identity": copy.deepcopy(self.identity)})
        self.append_ok([waiver])
        self.assertEqual(self.state()["findings"][0]["status"], "waived")
        self.append_ok([self.reopening()])
        self.assertEqual(self.state()["findings"][0]["status"], "open")


class ByteEqualOnTwoRuns(NativeLog):
    """Section 9.1: state is a pure function of the log's bytes."""

    def raw_state(self, *extra):
        code, out, err = testlib.run_cli(
            ["state", "--workspace", self.workspace, "--doc", DOC] + list(extra))
        self.assertEqual(code, 0, err)
        return out

    def test_the_same_log_gives_the_same_bytes_twice(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        first = self.raw_state()
        second = self.raw_state()
        self.assertEqual(first, second)
        self.assertEqual(canon.sha256_hex(first.encode("utf-8")),
                         canon.sha256_hex(second.encode("utf-8")))

    def test_it_holds_from_another_working_directory_too(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        code, here, _ = testlib.run_cli(["state", "--workspace", self.workspace, "--doc", DOC],
                                        cwd=self.workspace)
        code, there, _ = testlib.run_cli(["state", "--workspace", self.workspace, "--doc", DOC],
                                         cwd=self.scratch)
        self.assertEqual(here, there)

    def test_reading_the_state_writes_nothing(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        before = testlib.read_log(self.workspace)
        identity_before = identity_mod.source_identity(self.workspace)
        self.raw_state()
        self.assertEqual(testlib.read_log(self.workspace), before)
        self.assertEqual(identity_mod.source_identity(self.workspace), identity_before)

    def test_a_state_response_validates_against_its_schema(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        doc = json.loads(self.raw_state())
        self.assertEqual(validate.validate_document("state", doc, testlib.schemas()), [])
        with_source = json.loads(self.raw_state(
            "--at-source", self.write_identity()))
        self.assertEqual(validate.validate_document("state", with_source, testlib.schemas()), [])

    def write_identity(self, identity=None):
        return testlib.write_json(os.path.join(self.scratch, "identity.json"),
                                  {"identity": identity or self.identity})


class AtSource(NativeLog):
    """Section 8.4: which clears were verified on the revision in front of the station."""

    def write_identity(self, identity):
        return testlib.write_json(
            os.path.join(self.scratch, "at-%d.json" % len(os.listdir(self.scratch))),
            {"identity": identity})

    def test_a_bound_clear_on_this_commit_says_so(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        row = self.state("--at-source", self.write_identity(self.identity))["findings"][0]
        self.assertTrue(row["cleared_at_this_source"])

    def test_a_bound_clear_on_another_commit_does_not(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        other = copy.deepcopy(self.identity)
        other["commit"] = "1f0c9b7a4d2e6f80315c8ab4d9e2071c6b35a8f4"
        row = self.state("--at-source", self.write_identity(other))["findings"][0]
        self.assertFalse(row["cleared_at_this_source"])

    def test_it_changes_no_state(self):
        self.append_ok([testlib.disposition(self.finding, self.identity)])
        plain = self.state()
        with_source = self.state("--at-source", self.write_identity(self.identity))
        for row in with_source["findings"]:
            row.pop("cleared_at_this_source")
        self.assertEqual(plain["findings"], with_source["findings"])
        self.assertEqual(plain["slices"], with_source["slices"])
        self.assertEqual(with_source["at_source"], {"commit": self.identity["commit"]})

    def test_an_at_source_file_that_holds_no_identity_is_a_usage_error(self):
        path = testlib.write_json(os.path.join(self.scratch, "nope.json"), {"commit": 3})
        code, out, err = testlib.run_cli(
            ["state", "--workspace", self.workspace, "--doc", DOC, "--at-source", path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--at-source", err)


class FromAnImportedLog(unittest.TestCase):
    """cleared_unbound, card_drift, the punch list's absent card, and the slice filter."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-state-import-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)
        for doc in (GRANTS, CARDS, PUNCH):
            code, body, err = testlib.run_json(
                ["import-legacy", "--workspace", cls.workspace, "--doc", doc])
            assert code == 0, (doc, body, err)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def state(self, doc, *extra):
        code, body, err = testlib.run_json(
            ["state", "--workspace", self.workspace, "--doc", doc] + list(extra))
        self.assertEqual(code, 0, err)
        return body

    def test_cleared_unbound_is_true_for_every_imported_clear(self):
        """Owner ruling O4: a legacy clear keeps its effect and carries no source."""
        body = self.state(GRANTS)
        waived = [f for f in body["findings"] if f["status"] == "waived"]
        self.assertEqual(len(waived), 1)
        self.assertTrue(waived[0]["cleared_unbound"])
        self.assertEqual(waived[0]["join_basis"], "location_only")
        self.assertEqual(body["counts"]["cleared_unbound"], 1)

    def test_a_reopened_finding_is_open_and_no_longer_unbound(self):
        body = self.state(GRANTS)
        reopened = [f for f in body["findings"] if f["status"] == "open"]
        self.assertEqual(len(reopened), 1)
        self.assertFalse(reopened[0]["cleared_unbound"])
        self.assertEqual(reopened[0]["join_basis"], "exact")

    def test_a_card_that_agrees_with_what_is_open_does_not_drift(self):
        rows = dict((s["name"], s) for s in self.state(CARDS)["slices"])
        self.assertEqual(rows["A"]["card_observed"], "signed off")
        self.assertEqual(rows["A"]["card_derived"], "signed off")
        self.assertFalse(rows["A"]["card_drift"])
        self.assertEqual(rows["A"]["open"], {"BLOCKER": 0, "MAJOR": 0, "MINOR": 0})

    def test_a_slice_at_built_keeps_built_whatever_is_open(self):
        rows = dict((s["name"], s) for s in self.state(CARDS)["slices"])
        self.assertEqual(rows["B"]["card_observed"], "built")
        self.assertEqual(rows["B"]["card_derived"], "built")
        self.assertFalse(rows["B"]["card_drift"])
        self.assertEqual(rows["B"]["open"]["BLOCKER"], 1)

    def test_a_status_text_that_is_not_a_card_reads_none_and_drifts(self):
        rows = dict((s["name"], s) for s in self.state(CARDS)["slices"])
        self.assertEqual(rows["C"]["card_observed"], "none")
        self.assertEqual(rows["C"]["card_observed_text"], "built (2026-05-08; awaiting signoff)")
        self.assertEqual(rows["C"]["card_derived"], "signed off with conditions")
        self.assertTrue(rows["C"]["card_drift"], "the component reports drift, never corrects it")

    def test_the_component_never_writes_a_card_back(self):
        before = testlib.doc_sha256(self.workspace, CARDS)
        self.state(CARDS)
        self.assertEqual(testlib.doc_sha256(self.workspace, CARDS), before)

    def test_the_punch_list_has_no_card(self):
        body = self.state(PUNCH)
        self.assertEqual(len(body["slices"]), 1)
        row = body["slices"][0]
        self.assertEqual(row["name"], "none")
        self.assertIsNone(row["card_derived"])
        self.assertIsNone(row["card_observed"])
        self.assertFalse(row["card_drift"])
        self.assertEqual([f["slice"] for f in body["findings"]], ["none"])

    def test_the_slice_filter_keeps_one_slice_and_says_so(self):
        body = self.state(CARDS, "--slice", "B")
        self.assertEqual([s["name"] for s in body["slices"]], ["B"])
        self.assertEqual(set(f["slice"] for f in body["findings"]), {"B"})
        self.assertEqual(body["filters"], {"slice": "B"})
        self.assertEqual(body["spec"], {"doc": CARDS, "slice": "B"})
        self.assertEqual(body["open"], {"BLOCKER": 1, "MAJOR": 0, "MINOR": 0})

    def test_a_slice_nobody_named_returns_an_empty_state_rather_than_an_error(self):
        body = self.state(CARDS, "--slice", "Z")
        self.assertEqual(body["slices"], [])
        self.assertEqual(body["findings"], [])
        self.assertEqual(body["counts"]["findings"], 0)

    def test_a_log_that_does_not_exist_yet_gives_an_empty_state(self):
        body = self.state(PLANS + "2026-05-01-l1-backticks.md")
        self.assertFalse(body["exists"])
        self.assertEqual(body["head"], testlib.ZERO)
        self.assertEqual(body["events"], 0)
        self.assertEqual(body["findings"], [])


class TheLibraryAgreesWithTheCli(unittest.TestCase):
    def test_finding_status_is_the_same_rule_the_whole_object_uses(self):
        doc = "docs/plans/x.md"
        finding = "f1:" + "a" * 20
        base = {"seq": 0, "kind": "finding_raised", "finding": finding, "slice": "A",
                "severity": "MAJOR", "location": None, "claim": "c", "scenario": None,
                "raised_by": None}
        fixed = {"seq": 1, "kind": "disposition", "finding": finding, "disposition": "fixed",
                 "join_basis": None, "verified_source": {"known": False}}
        reopened = {"seq": 2, "kind": "reopened", "finding": finding, "join_basis": None}
        for events, expected in (([base], "open"), ([base, fixed], "fixed"),
                                 ([base, fixed, reopened], "open")):
            self.assertEqual(state_mod.finding_status(events, finding), expected)
            self.assertEqual(state_mod.state_of(doc, events)["findings"][0]["status"], expected)

    def test_a_finding_the_log_never_raised_has_no_status(self):
        self.assertIsNone(state_mod.finding_status([], "f1:" + "b" * 20))

    def test_events_dot_finding_status_is_the_same_function(self):
        finding = "f1:" + "c" * 20
        rows = [{"seq": 0, "kind": "finding_raised", "finding": finding}]
        self.assertEqual(events_mod.finding_status(rows, finding),
                         state_mod.finding_status(rows, finding))


if __name__ == "__main__":
    unittest.main()
