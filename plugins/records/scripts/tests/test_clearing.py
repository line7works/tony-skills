"""Section 8.3: a record cannot clear findings against a different source revision.

Also section 8.2: the identity a native event carries is computed with docs/records/ excluded,
so appending to the log does not change the identity of the source the log describes.
"""
import copy
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from records_core import events as events_mod, identity as identity_mod, validate  # noqa: E402

DOC = testlib.DOC
OTHER_COMMIT = "1f0c9b7a4d2e6f80315c8ab4d9e2071c6b35a8f4"
OTHER_SHA = "9a8b7c6d5e4f30211203040506070809a0b1c2d3e4f5061728394a5b6c7d8e9f"


class ClearingCase(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-clear-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)
        self.head = self.append_ok([testlib.opened(self.identity),
                                    testlib.raised(identity=self.identity)])
        code, doc, _ = testlib.run_json(["events", "--workspace", self.workspace, "--doc", DOC,
                                         "--kind", "finding_raised"])
        self.finding = doc["results"][0]["event"]["finding"]

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def append(self, events, head=None):
        path = testlib.events_file(self.batches, events,
                                   name="batch-%d.json" % len(os.listdir(self.batches)))
        return testlib.run_json(["append", "--workspace", self.workspace, "--doc", DOC,
                                 "--events", path, "--expect-head", head or self.head])

    def append_ok(self, events, head=None):
        code, doc, err = self.append(events, head or testlib.ZERO)
        self.assertEqual(code, 0, (doc, err))
        return doc["head"]


class FixedDisposition(ClearingCase):
    def test_it_is_accepted_when_the_workspace_matches(self):
        before = identity_mod.source_identity(self.workspace)
        code, doc, err = self.append([testlib.disposition(self.finding, self.identity)])
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["appended"][0]["kind"], "disposition")
        after = identity_mod.source_identity(self.workspace)
        self.assertEqual(before, after, "appending to the log leaves 8.2's identity unchanged")

    def test_it_is_refused_with_known_false(self):
        clear = testlib.disposition(self.finding, self.identity, verified={"known": False})
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([clear])
        self.assertEqual(code, 6)
        self.assertEqual(doc["error"], "stale_source")
        self.assertEqual(doc["condition"], "known")
        self.assertIsNone(doc["expected"])
        self.assertEqual(doc["actual"], self.identity)
        self.assertEqual(testlib.read_log(self.workspace), before, "nothing was written")

    def test_it_is_refused_on_each_of_the_six_fields_in_turn(self):
        changes = {
            "commit": OTHER_COMMIT,
            "dirty": True,
            "tracked_diff_sha256": OTHER_SHA,
            "untracked": ["scratch/notes.txt"],
            "untracked_sha256": OTHER_SHA,
            "submodules": ["vendor/thing"],
        }
        for field in identity_mod.FIELDS:
            wrong = copy.deepcopy(self.identity)
            wrong[field] = changes[field]
            self.assertNotEqual(wrong[field], self.identity[field], field)
            clear = testlib.disposition(self.finding, self.identity,
                                        verified={"known": True, "identity": wrong})
            before = testlib.read_log(self.workspace)
            code, doc, _ = self.append([clear])
            self.assertEqual(code, 6, "%s: %s" % (field, doc))
            self.assertEqual(doc["condition"], "identity", field)
            self.assertEqual(doc["differing_fields"], [field], field)
            self.assertEqual(doc["expected"], wrong, field)
            self.assertEqual(doc["actual"], self.identity, field)
            self.assertEqual(testlib.read_log(self.workspace), before, field)

    def test_it_is_refused_against_a_finding_that_is_not_open(self):
        head = self.append_ok([testlib.disposition(self.finding, self.identity)], self.head)
        second = testlib.disposition(self.finding, self.identity, at="2026-04-01T12:00:00Z",
                                     how="ran it twice")
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([second], head)
        self.assertEqual(code, 6)
        self.assertEqual(doc["condition"], "open")
        self.assertEqual(doc["status"], "fixed")
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_it_is_accepted_again_after_a_reopening(self):
        head = self.append_ok([testlib.disposition(self.finding, self.identity)], self.head)
        reopen = testlib.native("reopened", at="2026-04-02T09:00:00Z", identity=self.identity,
                                finding=self.finding, words="it came back", grant_date="2026-04-02")
        head = self.append_ok([reopen], head)
        code, doc, err = self.append([testlib.disposition(self.finding, self.identity,
                                                          at="2026-04-02T10:00:00Z")], head)
        self.assertEqual(code, 0, (doc, err))

    def test_a_dirty_workspace_clears_against_its_own_dirty_identity(self):
        testlib.write(os.path.join(self.workspace, "src", "widget.py"), "def widget():\n    return 2\n")
        dirty = identity_mod.source_identity(self.workspace)
        self.assertTrue(dirty["dirty"])
        code, doc, err = self.append([testlib.disposition(self.finding, dirty)])
        self.assertEqual(code, 0, (doc, err))

    def test_a_not_fixed_disposition_needs_no_open_finding(self):
        """Only a clear is held to 8.3; `not_fixed` leaves the finding open and is not a clear."""
        head = self.append_ok([testlib.disposition(self.finding, self.identity)], self.head)
        not_fixed = testlib.disposition(self.finding, self.identity, value="not_fixed",
                                        at="2026-04-01T12:00:00Z", how="still broken",
                                        verified={"known": False})
        code, doc, err = self.append([not_fixed], head)
        self.assertEqual(code, 0, (doc, err))


class Waivers(ClearingCase):
    def waiver(self, identity=None, verified=None, at="2026-04-02T08:00:00Z"):
        return testlib.native("waived", at=at, identity=identity or self.identity, finding=self.finding,
                              severity="BLOCKER", words="ship it", grant_date="2026-04-01",
                              join_basis=None,
                              verified_source=verified if verified is not None
                              else {"known": True, "identity": copy.deepcopy(identity or self.identity)})

    def test_a_waiver_clears_when_the_workspace_matches(self):
        code, doc, err = self.append([self.waiver()])
        self.assertEqual(code, 0, (doc, err))

    def test_a_waiver_is_refused_with_known_false(self):
        code, doc, _ = self.append([self.waiver(verified={"known": False})])
        self.assertEqual(code, 6)
        self.assertEqual(doc["condition"], "known")

    def test_a_waiver_is_refused_against_a_stale_identity(self):
        wrong = copy.deepcopy(self.identity)
        wrong["commit"] = OTHER_COMMIT
        code, doc, _ = self.append([self.waiver(verified={"known": True, "identity": wrong})])
        self.assertEqual(code, 6)
        self.assertEqual(doc["differing_fields"], ["commit"])


class AWaiverOverAClearance(ClearingCase):
    """E13 amendment A2: `append` admits a `waived` whose finding is `fixed` at the current head.

    Appendix A orders records by file position and the later one wins, so a user's waiver written
    after a clearance is what decides the finding; `state`'s deciding-event rule already reads the
    pair that way, and the recheck pilot records exactly it when one run clears an item the user
    also waived. Only that one pair moves: a `waived` over a `waived`, and a `disposition: fixed`
    over anything but `open`, are refused as they always were, and the `known` and `identity`
    conditions are untouched.
    """

    def waiver(self, identity=None, verified=None, at="2026-04-02T08:00:00Z", words="ship it"):
        return testlib.native("waived", at=at, identity=identity or self.identity, finding=self.finding,
                              severity="BLOCKER", words=words, grant_date="2026-04-01",
                              join_basis=None,
                              verified_source=verified if verified is not None
                              else {"known": True, "identity": copy.deepcopy(identity or self.identity)})

    def clearance(self, at="2026-04-01T11:00:00Z"):
        return testlib.disposition(self.finding, self.identity, at=at)

    def status(self):
        code, doc, err = testlib.run_json(["state", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, (doc, err))
        return doc["findings"][0]

    # ---- admitted, in both shapes ----------------------------------------------------------

    def test_two_appends_the_waiver_lands_over_the_clearance(self):
        head = self.append_ok([self.clearance()], self.head)
        code, doc, err = self.append([self.waiver()], head)
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(doc["appended"][0]["kind"], "waived")
        row = self.status()
        self.assertEqual(row["status"], "waived")
        self.assertEqual(row["decided"]["seq"], doc["appended"][0]["seq"],
                         "the waiver is the deciding event")

    def test_one_batch_the_waiver_sees_the_clearance_beside_it(self):
        """The pilot's real shape: a `disposition: fixed` and a `waived` for one finding in one
        `--events` call. The second event's check must see the first."""
        code, doc, err = self.append([self.clearance(), self.waiver()], self.head)
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual([row["kind"] for row in doc["appended"]], ["disposition", "waived"])
        row = self.status()
        self.assertEqual(row["status"], "waived")
        self.assertEqual(row["decided"]["seq"], doc["appended"][1]["seq"])

    def test_render_gives_the_block_line_then_the_waiver_line(self):
        run = {"station": "recheck-v2", "run_id": "a2-run", "harness": "test"}
        clearance = self.clearance()
        clearance["actor"] = run
        waiver = self.waiver()
        waiver["actor"] = run
        code, doc, err = self.append([clearance, waiver], self.head)
        self.assertEqual(code, 0, (doc, err))
        code, body, err = testlib.run_json(["render", "--workspace", self.workspace, "--doc", DOC,
                                            "--run-id", "a2-run"])
        self.assertEqual(code, 0, (body, err))
        self.assertIn("\u00b7 fixed \u00b7", body["block"])
        self.assertEqual(len(body["grants"]), 1)
        self.assertTrue(body["grants"][0].startswith("- WAIVED (per user) \u00b7 2026-04-01 \u00b7 BLOCKER"),
                        body["grants"][0])
        self.assertTrue(body["text"].index(body["grants"][0]) > body["text"].index("\u00b7 fixed \u00b7"),
                        "the waiver line follows the block, as Appendix A places it")

    def test_a_reopening_after_that_waiver_still_reopens(self):
        head = self.append_ok([self.clearance(), self.waiver()], self.head)
        reopen = testlib.native("reopened", at="2026-04-03T09:00:00Z", identity=self.identity,
                                finding=self.finding, words="it came back", grant_date="2026-04-03",
                                join_basis=None)
        code, doc, err = self.append([reopen], head)
        self.assertEqual(code, 0, (doc, err))
        self.assertEqual(self.status()["status"], "open")

    # ---- everything else refuses exactly as it did ------------------------------------------

    def test_a_waiver_over_a_waiver_is_still_refused(self):
        head = self.append_ok([self.clearance(), self.waiver()], self.head)
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([self.waiver(at="2026-04-03T08:00:00Z", words="again")], head)
        self.assertEqual(code, 6)
        self.assertEqual(doc["error"], "stale_source")
        self.assertEqual(doc["condition"], "open")
        self.assertEqual(doc["status"], "waived")
        self.assertEqual(testlib.read_log(self.workspace), before, "nothing was written")

    def test_a_clearance_over_a_clearance_is_still_refused(self):
        head = self.append_ok([self.clearance()], self.head)
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([self.clearance(at="2026-04-01T12:00:00Z")], head)
        self.assertEqual(code, 6)
        self.assertEqual(doc["condition"], "open")
        self.assertEqual(doc["status"], "fixed")
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_a_clearance_over_a_waiver_is_still_refused(self):
        head = self.append_ok([self.clearance(), self.waiver()], self.head)
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([self.clearance(at="2026-04-03T12:00:00Z")], head)
        self.assertEqual(code, 6)
        self.assertEqual(doc["condition"], "open")
        self.assertEqual(doc["status"], "waived")
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_the_identity_condition_still_holds_over_a_clearance(self):
        head = self.append_ok([self.clearance()], self.head)
        wrong = copy.deepcopy(self.identity)
        wrong["commit"] = OTHER_COMMIT
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([self.waiver(verified={"known": True, "identity": wrong})], head)
        self.assertEqual(code, 6)
        self.assertEqual(doc["condition"], "identity")
        self.assertEqual(doc["differing_fields"], ["commit"])
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_the_known_condition_still_holds_over_a_clearance(self):
        head = self.append_ok([self.clearance()], self.head)
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([self.waiver(verified={"known": False})], head)
        self.assertEqual(code, 6)
        self.assertEqual(doc["condition"], "known")
        self.assertIsNone(doc["expected"])
        self.assertEqual(testlib.read_log(self.workspace), before)


class TheImporterException(ClearingCase):
    """Owner ruling O4: the importer is the one writer allowed to append a clear with known false,
    and only with origin.kind legacy.

    The exemption lives on the library keyword `importer=True`, which slice 2's importer passes
    and no CLI caller can. These tests therefore call the library directly; the CLI's own refusal
    of every legacy-shaped event is in `TheImporterDoorIsShutAtTheCli` below.
    """

    def legacy_clear(self, actor=None, origin=None):
        event = testlib.native("disposition", at="2026-03-09", identity=None, actor=actor or testlib.IMPORTER,
                               finding=self.finding, disposition="fixed",
                               how="the loop now stops after three tries", join_basis="location_only",
                               verified_source={"known": False})
        event["origin"] = origin if origin is not None else testlib.legacy_origin(line=77)
        event["source"] = {"known": False}
        return event

    def as_importer(self, events, head=None):
        """`events.append` the way slice 2's importer.py will call it."""
        schemas = validate.load_schemas(testlib.ROOT)
        return events_mod.append(self.workspace, DOC, events, head or self.head, schemas, importer=True)

    def test_a_legacy_clear_from_the_importer_is_accepted(self):
        body = self.as_importer([self.legacy_clear()])
        self.assertEqual(body["appended"][0]["kind"], "disposition")

    def test_a_legacy_clear_from_another_station_is_refused(self):
        """Owner ruling O4's exemption belongs to the importer's station and to nothing else.

        Since the outside review's finding 7 the EVENT SCHEMA says so too: a legacy origin
        carries the station `records-import`, so a clear like this one is refused a step earlier,
        as a malformed event (exit 4) rather than as an unbound clear (exit 6). Either way it
        does not land, and it does not reach the exemption.
        """
        other = {"station": "signoff", "run_id": "r", "harness": "claude-code"}
        before = testlib.read_log(self.workspace)
        with self.assertRaises(events_mod.RecordsError) as caught:
            self.as_importer([self.legacy_clear(actor=other)])
        self.assertEqual(caught.exception.code, 4)
        self.assertEqual([e["path"] for e in caught.exception.document["errors"]],
                         ["/actor/station"])
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_the_importer_cannot_write_an_unbound_native_clear(self):
        event = self.legacy_clear(origin={"kind": "native"})
        event["at"] = "2026-04-04T07:00:00Z"
        with self.assertRaises(events_mod.RecordsError) as caught:
            self.as_importer([event])
        self.assertEqual(caught.exception.code, 6)
        self.assertEqual(caught.exception.document["condition"], "known")

    def test_a_legacy_clear_may_land_on_a_finding_that_is_already_fixed(self):
        """History is not changed: a second legacy recheck line keeps its effect."""
        head = self.as_importer([self.legacy_clear()])["head"]
        second = self.legacy_clear()
        second["origin"]["line"] = 91
        body = self.as_importer([second], head)
        self.assertEqual(body["appended"][0]["kind"], "disposition")

    def test_the_exemption_needs_the_keyword_not_the_declaration(self):
        """The same event, the same fields, without importer=True: refused at the CLI's door."""
        code, doc, _ = self.append([self.legacy_clear()])
        self.assertEqual(code, 4)
        self.assertEqual(doc["error"], "invalid")


class TheImporterDoorIsShutAtTheCli(ClearingCase):
    """F1: no station reaches owner ruling O4 by declaring itself the importer (sections 8.3, 11)."""

    def legacy_clear(self):
        event = testlib.native("disposition", at="2026-03-09", identity=None, actor=testlib.IMPORTER,
                               finding=self.finding, disposition="fixed", how="the loop now stops",
                               join_basis="location_only", verified_source={"known": False})
        event["origin"] = testlib.legacy_origin(line=77)
        event["source"] = {"known": False}
        return event

    def assert_refused(self, event):
        before = testlib.read_log(self.workspace)
        code, doc, err = self.append([event])
        self.assertEqual(code, 4, (doc, err))
        self.assertEqual(doc["error"], "invalid")
        self.assertEqual(doc["event_index"], 1)
        self.assertIn("import-legacy", doc["reason"])
        self.assertEqual(testlib.read_log(self.workspace), before, "nothing was written")
        return doc

    def test_a_legacy_clear_through_the_cli_is_refused(self):
        doc = self.assert_refused(self.legacy_clear())
        self.assertEqual(doc["errors"][0]["path"], "/origin/kind")

    def test_a_legacy_finding_raised_through_the_cli_is_refused(self):
        event = testlib.raised(identity=self.identity, claim="an imported finding",
                               loc=testlib.location("src/widget.py:120", "src/widget.py", 120))
        event["at"] = "2026-03-02"
        event["origin"] = testlib.legacy_origin(line=51)
        event["actor"] = dict(testlib.IMPORTER)
        doc = self.assert_refused(event)
        self.assertEqual(doc["errors"][0]["path"], "/origin/kind")

    def test_a_native_event_from_the_importers_station_is_refused(self):
        event = testlib.raised(identity=self.identity, claim="a finding from the importer station",
                               loc=testlib.location("src/widget.py:121", "src/widget.py", 121))
        event["actor"] = dict(testlib.IMPORTER)
        doc = self.assert_refused(event)
        self.assertEqual(doc["errors"][0]["path"], "/actor/station")

    def test_the_refusal_comes_before_every_other_judgement(self):
        """An event that is legacy AND otherwise broken is refused as legacy, not as malformed."""
        event = self.legacy_clear()
        event.pop("how")
        event["finding"] = "f1:" + "e" * 20
        self.assert_refused(event)

    def test_a_legacy_event_later_in_a_batch_stops_the_whole_batch(self):
        good = testlib.raised(identity=self.identity, claim="a native one",
                              loc=testlib.location("src/widget.py:122", "src/widget.py", 122))
        before = testlib.read_log(self.workspace)
        code, doc, _ = self.append([good, self.legacy_clear()])
        self.assertEqual(code, 4)
        self.assertEqual(doc["event_index"], 2)
        self.assertEqual(testlib.read_log(self.workspace), before)

    def test_the_cli_has_no_flag_that_opens_the_door(self):
        code, out, err = testlib.run_cli(["append", "--help"])
        self.assertEqual(code, 0, err)
        self.assertNotIn("--importer", out)
        self.assertIn("import-legacy", out)


class ExcludedIdentity(unittest.TestCase):
    """Section 8.2: the fixed exclusion list, and what it does and does not cover."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-identity-")
        self.workspace = testlib.make_workspace(self.scratch)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def test_the_exclusion_list_is_docs_records(self):
        self.assertEqual(identity_mod.EXCLUDED, ("docs/records",))

    def test_a_file_under_docs_records_does_not_change_the_identity(self):
        before = identity_mod.source_identity(self.workspace)
        testlib.write(os.path.join(self.workspace, "docs", "records", "x.events.jsonl"), "{}\n")
        testlib.write(os.path.join(self.workspace, "docs", "records", "x.events.jsonl.lock"), "{}\n")
        self.assertEqual(identity_mod.source_identity(self.workspace), before)

    def test_a_tracked_log_that_changed_does_not_change_the_identity(self):
        testlib.write(os.path.join(self.workspace, "docs", "records", "x.events.jsonl"), "{}\n")
        testlib.git(self.workspace, "add", "-A")
        testlib.git(self.workspace, "commit", "-qm", "the log")
        before = identity_mod.source_identity(self.workspace)
        testlib.write(os.path.join(self.workspace, "docs", "records", "x.events.jsonl"), "{}\n{}\n")
        self.assertEqual(identity_mod.source_identity(self.workspace), before)

    def test_the_pilots_own_identity_does_see_the_log(self):
        """The exclusion is this component's; the pilot's identity_of is left as it was."""
        before = identity_mod.identity_of(self.workspace)
        testlib.write(os.path.join(self.workspace, "docs", "records", "x.events.jsonl"), "{}\n")
        self.assertNotEqual(identity_mod.identity_of(self.workspace), before)

    def test_a_file_elsewhere_does_change_the_identity(self):
        before = identity_mod.source_identity(self.workspace)
        testlib.write(os.path.join(self.workspace, "src", "gauge.py"), "def gauge():\n    return 0\n")
        after = identity_mod.source_identity(self.workspace)
        self.assertNotEqual(after, before)
        self.assertEqual(identity_mod.differing_fields(before, after),
                         ["dirty", "untracked", "untracked_sha256"])

    def test_the_identity_command_reports_the_exclusion(self):
        code, doc, err = testlib.run_json(["identity", "--workspace", self.workspace])
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["excluded"], ["docs/records/"])
        self.assertEqual(sorted(doc["identity"]), sorted(identity_mod.FIELDS))
        self.assertEqual(doc["identity"], identity_mod.source_identity(self.workspace))

    def test_a_workspace_with_an_initialized_submodule_is_refused(self):
        """Pilot contract section 6: a submodule's contents can change without its pinned commit
        changing, and the diff sees only the commit, so the workspace is refused before any work."""
        inner = os.path.join(self.scratch, "inner")
        os.makedirs(inner)
        testlib.write(os.path.join(inner, "a.txt"), "a\n")
        testlib.git(inner, "init", "-q", ".")
        testlib.git(inner, "add", "-A")
        testlib.git(inner, "commit", "-qm", "inner")
        testlib.git(self.workspace, "-c", "protocol.file.allow=always", "submodule", "add", "-q",
                    inner, "vendor/inner")
        testlib.git(self.workspace, "commit", "-qm", "the submodule")
        code, doc, err = testlib.run_json(["identity", "--workspace", self.workspace])
        self.assertEqual(code, 1, err)
        self.assertEqual(doc["error"], "unsupported")
        self.assertIn("unsupported: submodules: vendor/inner", doc["reason"])
        batch = testlib.events_file(self.scratch, [testlib.opened()])
        code, doc, _ = testlib.run_json(["append", "--workspace", self.workspace, "--doc", DOC,
                                         "--events", batch, "--expect-head", testlib.ZERO])
        self.assertEqual(code, 1)
        self.assertEqual(doc["error"], "unsupported")
        self.assertFalse(os.path.isfile(testlib.log_file(self.workspace)), "nothing was written")

    def test_the_identity_command_refuses_a_workspace_that_is_not_a_work_tree(self):
        plain = os.path.join(self.scratch, "plain")
        os.makedirs(plain)
        code, out, err = testlib.run_cli(["identity", "--workspace", plain])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("git work tree", err)


if __name__ == "__main__":
    unittest.main()
