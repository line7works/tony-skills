"""Without changing history (contract section 11.7), one test per bullet.

    1. the legacy document's SHA-256 is equal before and after an import, on every fixture,
       and `git status --porcelain` shows only the log;
    2. a second import of an unchanged document appends nothing (`imported: 0`);
    3. a second import of a document that has only grown at its tail appends only the new
       records, proved by re-reading every previously imported line;
    4. a document whose previously imported lines changed or moved is exit 7 (`conflict`)
       naming the first such line, and nothing is written.

The two bullets that are not numbered rules are here too: `origin.recorded_commit` is what
`git blame` gives for the line, never the source it verified, and an imported event's `at` is
the block heading's date with `source` left at `{"known": false}` unless the line names a full
commit, which goes to `origin.commit_named` and still leaves the source unknown.
"""
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()
testlib.add_fixtures_to_path()

from records_core import events as events_mod  # noqa: E402

HISTORY = "docs/plans/2026-05-12-history.md"


class HistoryCase(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-history-")
        self.workspace = testlib.fixture_workspace(self.scratch)
        self.build = testlib.fixture_build_module()

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def path(self, doc):
        return os.path.join(self.workspace, *doc.split("/"))

    def read(self, doc):
        with open(self.path(doc), encoding="utf-8") as fh:
            return fh.read()

    def write(self, doc, text):
        with open(self.path(doc), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def run_import(self, doc, *extra):
        return testlib.run_json(["import-legacy", "--workspace", self.workspace,
                                 "--doc", doc] + list(extra))

    def log_bytes(self, doc):
        path = events_mod.log_path(self.workspace, doc)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()


class BulletOneTheDocumentIsNeverWritten(HistoryCase):
    def test_every_fixture_keeps_its_hash_across_an_import(self):
        documents = [d for d in self.build.ledger_documents() if d.endswith(".md")]
        self.assertGreater(len(documents), 15)
        before = dict((doc, testlib.doc_sha256(self.workspace, doc)) for doc in documents)
        for doc in documents:
            code, body, err = self.run_import(doc)
            self.assertIn(code, (0, 5), "%s: exit %d, %s" % (doc, code, err))
        after = dict((doc, testlib.doc_sha256(self.workspace, doc)) for doc in documents)
        self.assertEqual(before, after)

    def test_git_status_shows_only_the_log_directory(self):
        for doc in self.build.ledger_documents():
            self.run_import(doc)
        self.assertEqual(testlib.porcelain(self.workspace), ["?? docs/records/"])

    def test_a_dry_run_writes_nothing_at_all(self):
        before = testlib.porcelain(self.workspace)
        code, body, err = self.run_import(HISTORY, "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertTrue(body["dry_run"])
        self.assertEqual(body["imported"], 0)
        self.assertGreater(body["would_import"], 0)
        self.assertIsNone(self.log_bytes(HISTORY))
        self.assertEqual(testlib.porcelain(self.workspace), before)

    def test_the_importer_never_writes_outside_the_records_directory(self):
        """Every byte of the workspace, before and after: the log is the only thing that moved.

        The outside review's finding 13: this used to filter the files it had just walked down
        to `docs/records/` and then check THOSE, so an importer that wrote `workspace/leaked.txt`
        passed it. The comparison is now over the whole tree, contents included.
        """
        def snapshot():
            out = {}
            for dirpath, dirnames, filenames in os.walk(self.workspace):
                dirnames[:] = [d for d in dirnames if d != ".git"]
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    rel = os.path.relpath(path, self.workspace).replace(os.sep, "/")
                    with open(path, "rb") as fh:
                        out[rel] = fh.read()
            return out

        before = snapshot()
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, (body, err))
        after = snapshot()
        changed = set(p for p in set(before) | set(after) if before.get(p) != after.get(p))
        self.assertEqual(changed, {events_mod.log_relpath(HISTORY)},
                         "the import touched something other than this document's log")


class BulletTwoASecondImportOfAnUnchangedDocument(HistoryCase):
    def test_it_appends_nothing(self):
        code, first, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        self.assertGreater(first["imported"], 0)
        before = self.log_bytes(HISTORY)
        code, second, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        self.assertEqual(second["imported"], 0)
        self.assertEqual(second["appended"], [])
        self.assertEqual(self.log_bytes(HISTORY), before)

    def test_the_head_and_the_count_do_not_move(self):
        code, first, _ = self.run_import(HISTORY)
        code, second, _ = self.run_import(HISTORY)
        self.assertEqual(second["head"], first["head"])
        self.assertEqual(second["events"], first["events"])
        # `previously_imported` counts RECORD lines. A `Status:` line is an observation and is
        # outside both 11.7 checks (owner amendment A4), so it is classified again every pass
        # and compared by its text instead.
        cards = first["counts"].get("card_observed", 0)
        self.assertEqual(second["previously_imported"], first["lines_classified"] - cards)
        self.assertEqual(second["lines_classified"], cards)

    def test_the_log_still_verifies(self):
        self.run_import(HISTORY)
        self.run_import(HISTORY)
        code, body, err = testlib.run_json(
            ["verify", "--workspace", self.workspace, "--doc", HISTORY])
        self.assertEqual(code, 0, err)
        self.assertTrue(body["ok"])


class BulletThreeADocumentThatOnlyGrewAtItsTail(HistoryCase):
    def grow(self):
        self.write(HISTORY, self.read(HISTORY).rstrip("\n") + "\n" + self.build.GROWN_TAIL)

    def test_only_the_new_records_are_appended(self):
        code, first, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        before = self.log_bytes(HISTORY)
        self.grow()
        code, second, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, "%s %s" % (second, err))
        self.assertGreater(second["imported"], 0)
        kinds = [row["kind"] for row in second["appended"]]
        self.assertEqual(kinds, ["import_started", "disposition", "import_finished"])
        self.assertTrue(self.log_bytes(HISTORY).startswith(before),
                        "the old bytes are kept and the new lines land at the tail (E12-5)")

    def test_the_new_record_is_the_one_the_tail_added(self):
        self.run_import(HISTORY)
        self.grow()
        self.run_import(HISTORY)
        events = testlib.events_of(self.workspace, HISTORY)
        cleared = [e for e in events if e["kind"] == "disposition"]
        self.assertEqual(len(cleared), 2)
        self.assertEqual([e["disposition"] for e in cleared], ["fixed", "not_fixed"])
        self.assertEqual(cleared[-1]["join_basis"], "location_only_no_claim")

    def test_the_document_is_re_read_line_by_line_to_prove_it_only_grew(self):
        code, first, _ = self.run_import(HISTORY)
        self.grow()
        code, second, _ = self.run_import(HISTORY)
        # the card line is classified again every pass and compared by its text (amendment A4),
        # so it is in neither `previously_imported` nor the first pass's record count
        cards = first["counts"].get("card_observed", 0)
        self.assertEqual(second["previously_imported"], first["lines_classified"] - cards)
        self.assertEqual(second["lines_classified"], 1 + cards, "the new record, and the card")
        self.assertEqual(second["counts"], {"disposition": 1}, "the card's text did not change")

    def test_a_second_log_opened_is_not_written(self):
        self.run_import(HISTORY)
        self.grow()
        self.run_import(HISTORY)
        events = testlib.events_of(self.workspace, HISTORY)
        self.assertEqual([e["kind"] for e in events].count("log_opened"), 1)
        self.assertEqual(events[0]["kind"], "log_opened")
        self.assertEqual(events[0]["seq"], 0)

    def test_the_grown_document_still_verifies_and_its_hash_matches_the_second_pass(self):
        self.run_import(HISTORY)
        self.grow()
        code, second, _ = self.run_import(HISTORY)
        self.assertEqual(second["doc_sha256"], testlib.doc_sha256(self.workspace, HISTORY))
        code, body, err = testlib.run_json(
            ["verify", "--workspace", self.workspace, "--doc", HISTORY])
        self.assertEqual(code, 0, err)


class BulletFourAnImportedLineThatChangedOrMoved(HistoryCase):
    def test_a_changed_line_is_exit_seven_and_writes_nothing(self):
        code, first, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        before = self.log_bytes(HISTORY)
        self.write(HISTORY, self.read(HISTORY).replace(self.build.CHANGED_FROM,
                                                       self.build.CHANGED_TO))
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 7, "%s %s" % (body, err))
        self.assertEqual(body["error"], "conflict")
        self.assertEqual(self.log_bytes(HISTORY), before)

    def test_it_names_the_first_such_line_with_both_texts(self):
        self.run_import(HISTORY)
        self.write(HISTORY, self.read(HISTORY).replace(self.build.CHANGED_FROM,
                                                       self.build.CHANGED_TO))
        code, body, _ = self.run_import(HISTORY)
        self.assertEqual(body["line"], 12)
        self.assertEqual(body["imported_raw"], self.build.CHANGED_FROM)
        self.assertEqual(body["current_raw"], self.build.CHANGED_TO)
        self.assertIn("changed or moved", body["reason"])
        self.assertIn("Nothing was written", body["reason"])

    def test_a_line_that_moved_is_caught_too(self):
        self.run_import(HISTORY)
        before = self.log_bytes(HISTORY)
        text = self.read(HISTORY)
        self.write(HISTORY, "<!-- a line inserted above every record -->\n" + text)
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 7, "%s %s" % (body, err))
        self.assertEqual(self.log_bytes(HISTORY), before)

    def test_a_deleted_record_is_caught_too(self):
        self.run_import(HISTORY)
        self.write(HISTORY, self.read(HISTORY).replace(self.build.CHANGED_FROM + "\n", ""))
        code, body, _ = self.run_import(HISTORY)
        self.assertEqual(code, 7)
        self.assertEqual(body["error"], "conflict")

    def test_the_dry_run_reports_the_same_conflict_and_takes_no_lock(self):
        self.run_import(HISTORY)
        self.write(HISTORY, self.read(HISTORY).replace(self.build.CHANGED_FROM,
                                                       self.build.CHANGED_TO))
        code, body, _ = self.run_import(HISTORY, "--dry-run")
        self.assertEqual(code, 7)
        self.assertFalse(os.path.exists(events_mod.log_path(self.workspace, HISTORY) + ".lock"))


class BulletThreeAndAHalfARecordAboveTheImportedTail(HistoryCase):
    """Section 11.7's "only grown at its tail", with E12-4: file order is time order.

    `check_only_grown` proves the lines an earlier pass read are still where they were and still
    say what they said. It cannot see a record written into the gap ABOVE them, which would land
    in the log after records that sit below it in the file. That is the send-back's F1.
    """

    def write_above_the_tail(self, text=None):
        """Replace the blank line above the recheck heading, so no imported line moves."""
        lines = self.read(HISTORY).split("\n")
        for index, line in enumerate(lines):
            if line.startswith("### 2026-05-13"):
                self.assertEqual(lines[index - 1], "", "the fixture's shape moved")
                lines[index - 1] = text or (
                    "- MINOR · src/list.py:9 · the list header is not printed · a loader guesses "
                    "· Slice A review")
                self.write(HISTORY, "\n".join(lines))
                return index  # the 1-based line number of the line just written
        self.fail("no recheck heading in the fixture")

    def test_a_new_record_above_the_imported_tail_is_exit_seven(self):
        code, first, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        before = self.log_bytes(HISTORY)
        line_no = self.write_above_the_tail()
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 7, "%s %s" % (body, err))
        self.assertEqual(body["error"], "conflict")
        self.assertEqual(self.log_bytes(HISTORY), before, "nothing is written")

    def test_it_names_the_line_the_text_and_the_mark(self):
        self.run_import(HISTORY)
        line_no = self.write_above_the_tail()
        code, body, _ = self.run_import(HISTORY)
        self.assertEqual(body["line"], line_no)
        self.assertIn("the list header is not printed", body["current_raw"])
        self.assertGreater(body["last_imported_line"], line_no)
        self.assertEqual(body["doc"], HISTORY)
        self.assertEqual(body["log"], events_mod.log_relpath(HISTORY))
        self.assertIn("is not an append", body["reason"])
        self.assertIn("file order is time order", body["reason"])

    def test_the_dry_run_reports_the_same_refusal(self):
        self.run_import(HISTORY)
        self.write_above_the_tail()
        code, body, _ = self.run_import(HISTORY, "--dry-run")
        self.assertEqual(code, 7)
        self.assertEqual(body["error"], "conflict")
        self.assertFalse(os.path.exists(events_mod.log_path(self.workspace, HISTORY) + ".lock"))

    def test_a_new_block_below_the_tail_still_imports(self):
        code, _, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        self.write(HISTORY, self.read(HISTORY).rstrip("\n") + "\n" + self.build.GROWN_TAIL)
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertGreater(body["imported"], 0)

    def test_the_log_is_never_out_of_file_order(self):
        """What the rule is for: every legacy record's line rises with its seq."""
        self.run_import(HISTORY)
        self.write(HISTORY, self.read(HISTORY).rstrip("\n") + "\n" + self.build.GROWN_TAIL)
        self.run_import(HISTORY)
        lines = [e["origin"]["line"] for e in testlib.events_of(self.workspace, HISTORY)
                 if e["origin"]["kind"] == "legacy" and e["kind"] != "card_observed"]
        self.assertEqual(lines, sorted(lines), lines)

    def test_a_card_line_neither_sets_the_mark_nor_is_judged_by_it(self):
        """Cards are outside the rule in both directions (owner amendment A4)."""
        from records_core import importer as importer_mod
        self.run_import(HISTORY)
        events = testlib.events_of(self.workspace, HISTORY)
        cards = [e for e in events if e["kind"] == "card_observed"]
        self.assertEqual(len(cards), 1)
        self.assertLess(cards[0]["origin"]["line"],
                        importer_mod.high_water_line(events, HISTORY),
                        "the Status: line sits above every record, so it must not set the mark")
        only_the_card = [e for e in events if e["kind"] == "card_observed"]
        self.assertIsNone(importer_mod.high_water_line(only_the_card, HISTORY))
        unit = importer_mod.Unit(1, "Status: signed off", "card")
        importer_mod.check_only_grew_at_the_tail([unit], 99, HISTORY, "log")  # raises nothing


class WhatAnImportedEventCarries(HistoryCase):
    def test_recorded_commit_is_what_blame_gives_for_the_line(self):
        code, _, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        head = testlib.git(self.workspace, "rev-parse", "HEAD").strip()
        for event in testlib.events_of(self.workspace, HISTORY):
            if event["origin"]["kind"] != "legacy":
                continue
            self.assertEqual(event["origin"]["recorded_commit"], head,
                             "every line of the fixture was written down in its one commit")

    def test_recorded_commit_is_null_for_a_document_that_is_not_tracked(self):
        untracked = "docs/plans/2026-05-30-untracked.md"
        self.write(untracked, self.read(HISTORY))
        code, _, err = self.run_import(untracked)
        self.assertEqual(code, 0, err)
        for event in testlib.events_of(self.workspace, untracked):
            if event["origin"]["kind"] == "legacy":
                self.assertIsNone(event["origin"]["recorded_commit"])

    def test_an_imported_event_takes_the_block_headings_date(self):
        self.run_import(HISTORY)
        by_kind = {}
        for event in testlib.events_of(self.workspace, HISTORY):
            by_kind.setdefault(event["kind"], []).append(event)
        self.assertEqual(by_kind["finding_raised"][0]["at"], "2026-05-12")
        self.assertEqual(by_kind["disposition"][0]["at"], "2026-05-13")

    def test_every_imported_record_carries_an_unknown_source(self):
        self.run_import(HISTORY)
        for event in testlib.events_of(self.workspace, HISTORY):
            self.assertEqual(event["source"], {"known": False}, event["kind"])
            if "verified_source" in event:
                self.assertEqual(event["verified_source"], {"known": False}, event["kind"])

    def test_a_commit_a_line_names_goes_to_commit_named_and_leaves_the_source_unknown(self):
        named = "docs/plans/2026-05-31-commit-named.md"
        commit = "b" * 40
        self.write(named, "\n".join([
            "# A line that names a commit",
            "",
            "## Slice A — the gate",
            "Status: signed off",
            "",
            "## Punch list",
            "",
            "### 2026-05-31 — review: Slice A",
            "- MAJOR · src/gate.py:3 · the gate sticks · a crate waits · Slice A review",
            "",
            "### 2026-05-31 — recheck: Slice A",
            "- MAJOR · src/gate.py:3 · (the gate sticks) · fixed — executed at %s" % commit,
            "",
        ]))
        code, _, err = self.run_import(named)
        self.assertEqual(code, 0, err)
        cleared = [e for e in testlib.events_of(self.workspace, named)
                   if e["kind"] == "disposition"][0]
        self.assertEqual(cleared["origin"]["commit_named"], commit)
        self.assertEqual(cleared["source"], {"known": False},
                         "a bare commit is not the six-field identity (section 11.7)")
        self.assertEqual(cleared["verified_source"], {"known": False})

    def test_the_brackets_are_this_components_own_events_not_legacy_records(self):
        self.run_import(HISTORY)
        events = testlib.events_of(self.workspace, HISTORY)
        brackets = [e for e in events if e["kind"] in ("import_started", "import_finished",
                                                       "log_opened")]
        self.assertEqual(len(brackets), 3)
        for event in brackets:
            self.assertEqual(event["origin"], {"kind": "native"})
            self.assertTrue(event["at"].endswith("Z"), event["kind"])
            self.assertEqual(event["actor"]["station"], "records-import")
        finished = [e for e in events if e["kind"] == "import_finished"][0]
        self.assertEqual(finished["doc_sha256"], testlib.doc_sha256(self.workspace, HISTORY))
        self.assertEqual(finished["lines_read"], len(self.read(HISTORY).split("\n")))
        self.assertEqual(finished["counts"],
                         {"card_observed": 1, "finding_raised": 1, "disposition": 1})


class OwnerAmendmentA4AStatusLineIsAnObservation(HistoryCase):
    """Owner amendment A4 (2026-09-20): a `Status:` line is an observation, not a record.

    It is outside BOTH of section 11.7's checks, so a card a station flips in place, or that
    moves because lines were written above it, never stops a later import. Each pass appends a
    `card_observed` for a slice only when the current text differs from the `value` of that
    slice's last `card_observed` in the log, matched by slice name and never by line number.
    RECORD lines keep section 11.7 exactly as it was built.
    """

    CARDS_ONLY = "docs/plans/2026-05-20-cards-only.md"
    CARDS_ONLY_TEXT = ("# Loading board\n\nA board with cards and no punch list yet.\n\n"
                       "## Slice A - the bay\nStatus: built\n\n"
                       "## Slice B - the ramp\nStatus: signed off\n")

    def cards_of(self, doc=HISTORY):
        return [e for e in testlib.events_of(self.workspace, doc) if e["kind"] == "card_observed"]

    def flip_the_card(self, text):
        """Rewrite the one `Status:` line of the history fixture in place, nothing else."""
        old = self.read(HISTORY)
        self.assertIn("Status: signed off\n", old, "the fixture's card moved")
        self.write(HISTORY, old.replace("Status: signed off\n", "Status: %s\n" % text, 1))

    def state_of(self, doc=HISTORY):
        code, body, err = testlib.run_json(["state", "--workspace", self.workspace, "--doc", doc])
        self.assertEqual(code, 0, err)
        return dict((row["name"], row) for row in body["slices"])

    def test_a_card_flipped_in_place_is_imported_as_one_new_observation(self):
        code, _, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        self.assertEqual([c["value"] for c in self.cards_of()], ["signed off"])
        before = self.state_of()["A"]
        self.assertEqual(before["card_observed"], "signed off")
        self.assertFalse(before["card_drift"], "the fixture's card agrees with what is open")

        self.flip_the_card("rejected")
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertEqual(body["counts"], {"card_observed": 1},
                         "the only news is the card; no record is read again")
        self.assertEqual(body["imported"], 3, "import_started, the card, import_finished")
        self.assertEqual([c["value"] for c in self.cards_of()], ["signed off", "rejected"])

        after = self.state_of()["A"]
        self.assertEqual(after["card_observed"], "rejected", "state follows the last observation")
        self.assertEqual(after["card_derived"], "signed off", "nothing is open")
        self.assertTrue(after["card_drift"], "the drift is recomputed from the new observation")

    def test_a_card_flipped_and_a_block_appended_both_land_in_file_order(self):
        code, _, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        self.flip_the_card("rejected")
        self.write(HISTORY, self.read(HISTORY).rstrip("\n") + "\n" + self.build.GROWN_TAIL)
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertEqual(body["counts"].get("card_observed"), 1)
        self.assertGreater(sum(v for k, v in body["counts"].items() if k != "card_observed"), 0,
                           "the appended block is read too")
        events = testlib.events_of(self.workspace, HISTORY)
        self.assertEqual([c["value"] for c in self.cards_of()], ["signed off", "rejected"])
        records = [e["origin"]["line"] for e in events
                   if e["origin"]["kind"] == "legacy" and e["kind"] != "card_observed"]
        self.assertEqual(records, sorted(records), records)

    def test_a_status_line_that_only_moved_appends_nothing_and_does_not_conflict(self):
        """No imported RECORD sits below the insertion, so only the card moved (A4)."""
        self.write(self.CARDS_ONLY, self.CARDS_ONLY_TEXT)
        code, body, err = self.run_import(self.CARDS_ONLY)
        self.assertEqual(code, 0, err)
        self.assertEqual(body["counts"], {"card_observed": 2})
        before = self.log_bytes(self.CARDS_ONLY)

        self.write(self.CARDS_ONLY,
                   self.CARDS_ONLY_TEXT.replace("A board with cards",
                                                "One more paragraph.\n\nA board with cards", 1))
        code, body, err = self.run_import(self.CARDS_ONLY)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertEqual(body["imported"], 0, "the text did not change, so there is no news")
        self.assertEqual(self.log_bytes(self.CARDS_ONLY), before, "nothing is written")
        self.assertEqual([c["slice"] for c in self.cards_of(self.CARDS_ONLY)], ["A", "B"])

    def test_one_slices_card_changing_leaves_the_other_alone(self):
        self.write(self.CARDS_ONLY, self.CARDS_ONLY_TEXT)
        code, _, err = self.run_import(self.CARDS_ONLY)
        self.assertEqual(code, 0, err)
        self.write(self.CARDS_ONLY, self.CARDS_ONLY_TEXT.replace("Status: built", "Status: rejected", 1))
        code, body, err = self.run_import(self.CARDS_ONLY)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertEqual(body["counts"], {"card_observed": 1})
        self.assertEqual([(c["slice"], c["value"]) for c in self.cards_of(self.CARDS_ONLY)],
                         [("A", "built"), ("B", "signed off"), ("A", "rejected")])

    def test_a_second_import_of_an_unchanged_document_still_appends_nothing(self):
        code, _, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        before = self.log_bytes(HISTORY)
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, "%s %s" % (body, err))
        self.assertEqual(body["imported"], 0)
        self.assertEqual(body["counts"], {}, "not even a bracket")
        self.assertEqual(self.log_bytes(HISTORY), before)

    def test_a_changed_record_line_is_still_a_conflict(self):
        code, _, err = self.run_import(HISTORY)
        self.assertEqual(code, 0, err)
        before = self.log_bytes(HISTORY)
        self.write(HISTORY, self.read(HISTORY).replace(
            "the loading list is not sorted · a heavy crate",
            "the loading list is not sorted at all · a heavy crate", 1))
        code, body, err = self.run_import(HISTORY)
        self.assertEqual(code, 7, "%s %s" % (body, err))
        self.assertEqual(body["error"], "conflict")
        self.assertEqual(self.log_bytes(HISTORY), before, "nothing is written")

    def test_a_card_set_is_not_an_observation_of_the_documents_text(self):
        """A native card move does not tell the importer what the `Status:` line says (A4)."""
        from records_core import importer as importer_mod
        events = [{"kind": "card_set", "ledger_doc": HISTORY, "slice": "A",
                   "before": "built", "after": "signed off"},
                  {"kind": "card_observed", "ledger_doc": HISTORY, "slice": "A",
                   "value": "built"},
                  {"kind": "card_observed", "ledger_doc": "docs/other.md", "slice": "A",
                   "value": "rejected"}]
        self.assertEqual(importer_mod.last_card_values(events, HISTORY), {"A": "built"})


if __name__ == "__main__":
    unittest.main()
