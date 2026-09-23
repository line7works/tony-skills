"""E13 full-review fix round: Astra's F2, F3, F5, F7 and F9 against the signoff core, as tests.

Her probe scripts are not available to this round; `astra-full-review.md` names each probe's
shape, its inputs and what printed. Each class rebuilds that shape through the real CLI in front of
the real records component (the shim forwards everything it does not inject). The class docstring
names her item. Written red first; the red output is kept in the round's scratch folder.
"""
import json
import os
import unittest

import shimlib
import testlib
from test_fix2_astra import DOC, _Case, kinds, read_log

testlib.add_scripts_to_path()

OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-4-5"
NOTES = "docs/BUILDER-NOTES.md"
# The real rule, with the synthetic replay interface of the test library switched off.
NO_REPLAY = {"SIGNOFF_TEST_REPLAY_MODEL": ""}


class F2SourceAddedDuringTheFinalAppendIsNeverSigned(_Case):
    """F2 (BLOCKER). Astra's `probe_windows.py`, `signoff-source-at-card`: `src/late.py` is added
    immediately before the final card append is forwarded to the real component; the run printed
    `exit 10 / completed / verdict_recorded true` for source its packet never held. After the final
    append and on recovery the source now, minus exactly the receipt's document targets, is compared
    with the masked source pinned for review; movement is a named stale-source stop."""

    def arm_late_file(self):
        shimlib.fault(self.fault, command="append", kind="card_set", action="mutate",
                      path=os.path.join(self.workspace, "src", "late.py"),
                      text="LATE = True\n")

    def test_a_file_added_during_the_card_append_is_a_stale_source_stop(self):
        code, body, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(body))
        self.arm_late_file()
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "stale_source", json.dumps(result)[:1500])
        self.assertEqual(result["stop_reason_code"], "source_moved")
        self.assertFalse(result["verdict_recorded"])
        self.assertIn("src/late.py", result["stop_reason"])
        # what landed is reported as landed: both appends, and every document step
        names = [row["name"] for row in result["records"]["appended"]]
        self.assertEqual(sorted(names), ["card", "findings"], json.dumps(result["records"]))
        self.assertTrue(result["document_steps"])
        self.assertEqual(len(kinds(self.workspace, "card_set")), 1)
        self.assertEqual(len(kinds(self.workspace, "finding_raised")), 1)

    def test_recovery_after_the_stop_stays_stale(self):
        self.through_answer()
        self.arm_late_file()
        self.record()
        shimlib.disarm(self.fault)
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "stale_source", json.dumps(result)[:1500])
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(len(kinds(self.workspace, "card_set")), 1, "never appended twice")

    def test_the_unmoved_control_still_completes(self):
        self.through_answer()
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        self.assertEqual(self.result()["status"], "completed")
        self.assertTrue(self.result()["verdict_recorded"])


class F3AlternateSpellingsOfAWithheldCitationAreRefused(_Case):
    """F3 (MAJOR). Astra's `probe_evidence.py`: `builder-notes.md` stopped on independence, but
    `./builder-notes.md`, the absolute path, `builder%2Dnotes.md` and a `./` citation inside a
    check's output each printed `completed / verdict_recorded true`. Citations are resolved to
    canonical workspace paths before the withheld-provenance comparison, over every answer string."""

    CASE = "S3-03-builder-notes-untracked"

    def refused(self, answer):
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 10, "the answer was accepted: %s %s" % (err, json.dumps(body)))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1200])
        self.assertEqual(result["refusal_reason"], "independence", json.dumps(result["problems"]))
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(result["findings"], [], "no finding is written")
        self.assertEqual(read_log(self.workspace), [])

    def with_notes(self, text):
        answer = self.answer()
        answer["notes"] = text
        return answer

    def test_a_dot_slash_path(self):
        self.refused(self.with_notes("Evidence: ./%s:2 says the separator case was run." % NOTES))

    def test_an_absolute_path(self):
        self.refused(self.with_notes("Evidence: %s:2 says so."
                                     % os.path.join(self.workspace, NOTES)))

    def test_a_percent_encoded_path(self):
        self.refused(self.with_notes("Evidence: docs/BUILDER%2DNOTES.md line 2."))

    def test_a_file_url(self):
        self.refused(self.with_notes("See file://%s#L2." % os.path.join(self.workspace, NOTES)))

    def test_a_markdown_destination_with_a_fragment(self):
        self.refused(self.with_notes("Per [the account](./docs/BUILDER-NOTES.md#separator), "
                                     "the case ran."))

    def test_a_relative_segment(self):
        self.refused(self.with_notes("Evidence: src/../docs/BUILDER-NOTES.md."))

    def test_a_dot_slash_citation_in_a_check_output(self):
        answer = self.answer()
        answer["checks_executed"][0]["output"] = ("Ran 4 tests in 0.000s\n\nOK\n"
                                                  "(cross-checked with ./%s)" % NOTES)
        self.refused(answer)

    def test_a_citation_in_a_check_command(self):
        answer = self.answer()
        answer["checks_executed"].append({"name": "read", "command": "cat ./docs/BUILDER%2DNOTES.md",
                                          "exit_code": 0, "output": "read"})
        self.refused(answer)

    def test_a_citation_in_a_kept_note(self):
        answer = self.answer()
        answer["notes_kept"] = [{"location": "./docs/BUILDER-NOTES.md:2", "severity": "MINOR",
                                 "claim": "a note", "scenario": "none",
                                 "evidence_kind": "read"}]
        self.refused(answer)

    def test_a_delivered_path_spelled_with_dot_slash_is_still_accepted(self):
        answer = self.with_notes("Read ./src/signpost/columns.py and ran the unit check.")
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 0, err or json.dumps(body))


class _Floor(_Case):
    """The real floor rule: the test library's synthetic replay interface switched off."""

    def setUp(self):
        _Case.setUp(self)
        self.env = dict(self.env, **NO_REPLAY)

    def with_model(self, model):
        doc = testlib.load_json(self.input_path)
        if model is None:
            doc["invocation"].pop("model", None)
        else:
            doc["invocation"]["model"] = model
        testlib.write_json(self.input_path, doc)

    def answer_model(self, model):
        answer = self.answer()
        if model is None:
            answer.pop("model", None)
        else:
            answer["model"] = model
        return answer

    def request(self):
        code, body, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(body))
        return self.phase(["request", "--run-dir", self.run_dir])

    def assert_floor_stop(self, code, body, err):
        self.assertEqual(code, 10, "the run went on: %s %s" % (err, json.dumps(body)))
        result = self.result()
        self.assertEqual(result["status"], "stopped", json.dumps(result)[:1200])
        self.assertEqual(result["stop_reason_code"], "floor_refused", json.dumps(result)[:1200])
        self.assertFalse(result["verdict_recorded"])
        self.assertEqual(read_log(self.workspace), [], "no project-record write")
        return result


class F5TheOpusFloorIsEnforcedBeforeTheRequest(_Floor):
    """F5 (MAJOR). Astra's `probe_floor_false.py`: `claude-haiku-4-5`, class `haiku`,
    `floor_met: false` printed `request: exit 0` and `record: exit 10 / completed / verdict_recorded
    true`. `probe_claims.py` recorded with a missing model, an unknown or null floor, and a typed
    true floor for Haiku. The floor is enforced before the reviewer request and before accepting or
    recording, from the adapter's observed model id, never an executor-typed `floor_met`."""

    def test_a_known_failed_floor(self):
        self.with_model({"id": HAIKU, "floor_class": "haiku", "floor_met": False})
        result = self.assert_floor_stop(*self.request())
        self.assertFalse(os.path.isfile(os.path.join(self.run_dir, "request.json")),
                         "no reviewer request is emitted")

    def test_a_missing_model(self):
        self.with_model(None)
        self.assert_floor_stop(*self.request())

    def test_an_unknown_model_with_a_null_floor(self):
        self.with_model({"id": "unknown", "floor_class": "unknown", "floor_met": None})
        self.assert_floor_stop(*self.request())

    def test_a_typed_true_floor_for_haiku_disagrees_with_the_id(self):
        self.with_model({"id": HAIKU, "floor_class": "opus", "floor_met": True})
        self.assert_floor_stop(*self.request())

    def test_an_opus_session_is_summoned(self):
        self.with_model({"id": OPUS, "floor_class": "opus", "floor_met": True})
        code, body, err = self.request()
        self.assertEqual(code, 0, err or json.dumps(body))


class F5TheReviewerModelIsCheckedBeforeTheAnswerIsAccepted(_Floor):
    """F5, the readers half: the answer's model (readers' effective model, as the adapter maps it)
    must be established, at the floor, and the model the session recorded."""

    def setUp(self):
        _Floor.setUp(self)
        self.with_model({"id": OPUS, "floor_class": "opus", "floor_met": True})

    def test_an_answer_below_the_floor(self):
        code, body, err = self.through_answer(self.answer_model(HAIKU))
        self.assert_floor_stop(code, body, err)

    def test_an_answer_that_names_no_model(self):
        code, body, err = self.through_answer(self.answer_model(None))
        self.assert_floor_stop(code, body, err)

    def test_an_answer_whose_model_disagrees_with_the_session(self):
        code, body, err = self.through_answer(self.answer_model("claude-fable-5-1"))
        self.assert_floor_stop(code, body, err)

    def test_the_agreeing_answer_records(self):
        code, body, err = self.through_answer(self.answer_model(OPUS))
        self.assertEqual(code, 0, err or json.dumps(body))
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1200])
        self.assertEqual(result["reviewer"]["model"], OPUS)
        self.assertEqual(result["floor"]["met"], True)

    def test_replay_facts_outside_test_mode_are_ignored(self):
        env = dict(self.env, SIGNOFF_TEST="", SIGNOFF_TEST_REPLAY_MODEL=OPUS)
        self.env = env
        code, body, err = self.through_answer(self.answer_model(None))
        self.assert_floor_stop(code, body, err)


class F7ASymlinkIsItsLinkTarget(_Case):
    """F7 (MAJOR). Astra's `probe_symlink_identity.py` made tracked `src/widget.py` a symlink,
    built the packet, then changed its referent: `identity_equal_after_source_bytes_changed true`
    and `completed / verdict_recorded true`. The packet read the referent while Git's identity
    records the link target. Packet entries now use lstat semantics, and every delivered entry's
    content identity is verified before recording."""

    def setUp(self):
        _Case.setUp(self)
        self.outside = os.path.join(self.dir, "outside-referent.py")
        with open(self.outside, "w", encoding="utf-8") as fh:
            fh.write("REFERENT_ORIGINAL = 1\n")
        link = os.path.join(self.workspace, "src", "signpost", "widget.py")
        os.symlink(self.outside, link)
        testlib.git(self.workspace, "add", "src/signpost/widget.py")
        testlib.git(self.workspace, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-qm", "a tracked symlink")

    def packet_row(self):
        packet = testlib.load_json(os.path.join(self.run_dir, "packet", "packet.json"))
        return [row for row in packet["files"] if row["path"] == "src/signpost/widget.py"][0], packet

    def test_the_packet_carries_the_link_target_never_the_referent(self):
        code, body, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(body))
        row, packet = self.packet_row()
        import hashlib
        self.assertEqual(row["sha256"], hashlib.sha256(self.outside.encode("utf-8")).hexdigest())
        self.assertEqual(row["size"], len(self.outside.encode("utf-8")))
        material = testlib.read_text(packet["material_path"])
        self.assertNotIn("REFERENT_ORIGINAL", material, "the referent is never presented as the file")
        self.assertIn(self.outside, material, "the link target is what the entry delivers")

    def test_a_referent_change_is_not_a_change_to_what_was_reviewed(self):
        self.through_answer()
        with open(self.outside, "w", encoding="utf-8") as fh:
            fh.write("REFERENT_CHANGED = 2\n")
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        # the delivered bytes are the link target, which did not move, so the verdict stands on
        # what the reviewer was actually given
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1200])
        row, packet = self.packet_row()
        self.assertNotIn("REFERENT_CHANGED", testlib.read_text(packet["material_path"]))


class F7EveryDeliveredEntryIsVerifiedBeforeRecording(_Case):
    """F7, the verification half: a delivered entry whose bytes moved after the packet was built
    is named in the stale-source stop, before any project record is written."""

    def test_a_delivered_untracked_entry_that_moved_is_named(self):
        self.through_answer()
        self.write("src/signpost/pad.py", "def pad(text, width):\n    return text.ljust(width)\n")
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "stale_source", json.dumps(result)[:1200])
        self.assertIn("src/signpost/pad.py", result["stop_reason"])
        self.assertEqual(read_log(self.workspace), [])


class F9FrontmatterNeverHidesADeclaredBuilderNotesHeading(_Case):
    """F9 (MAJOR). Astra's `probe_notes_heading.py`: `notes.md` with six frontmatter lines, then
    its first Markdown heading `# Builder notes`, was classified `kind: source`, `delivered: true`,
    and an answer citing it recorded. The first actual Markdown heading after frontmatter decides,
    with no line cutoff; only that first heading is tested."""

    FRONTMATTER = "---\ntitle: notes\nauthor: builder\ndate: 2026-09-20\nslice: F\nkind: notes\n---\n"

    def add_notes(self, text, rel="notes.md"):
        self.write(rel, text)

    def row(self, rel="notes.md"):
        packet = testlib.load_json(os.path.join(self.run_dir, "packet", "packet.json"))
        return [r for r in packet["files"] if r["path"] == rel][0], packet

    def test_frontmatter_then_the_heading(self):
        self.add_notes(self.FRONTMATTER + "# Builder notes\n\nThe separator case passed for me.\n")
        code, body, err = self.to_scope()
        self.assertEqual(code, 0, err or json.dumps(body))
        row, packet = self.row()
        self.assertEqual(row["kind"], "builder_conversation", json.dumps(row))
        self.assertFalse(row["delivered"])
        self.assertTrue(row["withheld_reason"])
        self.assertNotIn("passed for me", testlib.read_text(packet["material_path"]))

    def test_leading_blank_lines_then_the_heading(self):
        self.add_notes("\n\n\n\n\n\n\n# Builder's notes\n\nIt works on my machine.\n")
        self.to_scope()
        row, _ = self.row()
        self.assertEqual(row["kind"], "builder_conversation", json.dumps(row))

    def test_an_answer_citing_the_notes_is_refused(self):
        self.add_notes(self.FRONTMATTER + "# Builder notes\n\nThe separator case passed for me.\n")
        answer = self.answer()
        answer["notes"] = "Evidence: notes.md confirms the separator case."
        code, body, err = self.through_answer(answer)
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["refusal_reason"], "independence", json.dumps(result)[:1200])
        self.assertFalse(result["verdict_recorded"])

    def test_only_the_first_heading_is_tested(self):
        self.add_notes(self.FRONTMATTER + "# Padding design\n\nText.\n\n## Builder notes\n\nMore.\n")
        self.to_scope()
        row, _ = self.row()
        self.assertEqual(row["kind"], "source", json.dumps(row))
        self.assertTrue(row["delivered"])


if __name__ == "__main__":
    unittest.main()
