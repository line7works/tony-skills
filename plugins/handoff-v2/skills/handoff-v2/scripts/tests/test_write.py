"""`write` (CR-13): the sanctioned writes, exhaustively, each alone on its fixture: (1) a `waived` or `reopened`
event through `records.py append` with the owner's words and its rendered line placed at the ledger home's tail;
(2) one block `### <date> <dash> handoff` at the tail of `## Handoffs`, created before `## Punch list` when
missing; (3) the checkpoint commit, read and recorded, never made; (4) the pointer, carried as text for the Claude
Code adapter. Nothing else, ever: an earlier block, the punch-list history and a `Status:` line are never edited,
and every write has its hash before and after. An edited earlier block, a block outside `## Handoffs` and a record
that moved since the photograph stop before any write.
"""
import json
import os
import unittest

import hlib
import testlib

D = hlib.D
TODAY_HEADING = hlib.HEADING % hlib.TODAY


def inserted(before, after):
    """The lines `after` holds that `before` does not, when `after` is `before` with lines inserted (else None)."""
    a, b = before.splitlines(True), after.splitlines(True)
    out, i = [], 0
    for line in b:
        if i < len(a) and line == a[i]:
            i += 1
        else:
            out.append(line)
    return out if i == len(a) else None


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheSanctionedWrites(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-write-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def run_to_write(self, text, records=False, answers=(), questions=(), perishables=("the bench clock drifts",),
                     harness="claude-code", checkpoint=False, dirt=None):
        ws, info = hlib.make_repo(self.tmp, text, records=records, dirt=dirt)
        drive, run_dir = hlib.start(self.tmp, ws, harness=harness)
        gate = hlib.through_gate(self, drive, self.tmp, run_dir, questions=questions)
        answers = [dict(a, effect=dict(a["effect"], finding=next(o["id"] for o in gate["open"]
                                                                  if o["location"] == a["effect"]["finding"])))
                   if a.get("effect", {}).get("kind") in ("waive", "reopen") and not a["effect"]["finding"].startswith("f1:")
                   else a for a in answers]
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer",
                                hlib.answers_file(self.tmp, run_dir, answers, perishables)])
        self.assertEqual(code, 0, (out, err))
        if checkpoint:
            testlib.git(ws, ["add", "-A"])
            testlib.git(ws, ["commit", "-q", "-m", "handoff checkpoint (local): turnstile after A"])
        before_doc = hlib.read_doc(ws)
        before = hlib.snapshot(ws, run_dir)
        code, out, err = drive(["write", "--run-dir", run_dir])
        return ws, info, drive, run_dir, before_doc, before, (code, out, err)

    def test_the_block_alone(self):
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(hlib.build_doc())
        self.assertEqual(code, 0, (out, err))
        after_doc = hlib.read_doc(ws)
        added = inserted(before_doc, after_doc)
        self.assertIsNotNone(added)
        self.assertEqual(added[1], TODAY_HEADING + "\n")
        self.assertIn("- Perishable: the bench clock drifts\n", added)
        handoffs = after_doc.index("## Handoffs\n")
        self.assertLess(handoffs, after_doc.index(TODAY_HEADING), "the block sits under ## Handoffs")
        self.assertLess(after_doc.index(TODAY_HEADING), after_doc.index("## Punch list"))
        now = hlib.snapshot(ws, run_dir)
        self.assertEqual((now["log"], now["head"], now["commits"]), (before["log"], before["head"], before["commits"]))
        kinds = [w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"]
        self.assertEqual(kinds, ["build_doc"])
        doc_write = next(w for w in out["writes"] if w["kind"] == "build_doc")
        self.assertEqual((doc_write["sha256_before"], doc_write["sha256_after"]), (before["doc"], now["doc"]))

    def test_the_block_lands_at_the_tail_after_every_earlier_block_unchanged(self):
        text = hlib.build_doc(handoffs=hlib.handoff_block("2026-09-25") + hlib.handoff_block("2026-09-28"))
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(text)
        self.assertEqual(code, 0, (out, err))
        after_doc = hlib.read_doc(ws)
        self.assertIsNotNone(inserted(before_doc, after_doc))
        self.assertLess(after_doc.index(hlib.HEADING % "2026-09-28"), after_doc.index(TODAY_HEADING))

    def test_handoffs_is_created_before_the_punch_list_when_missing(self):
        text = hlib.build_doc(with_handoffs=False)
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(text)
        self.assertEqual(code, 0, (out, err))
        after_doc = hlib.read_doc(ws)
        self.assertIsNotNone(inserted(before_doc, after_doc))
        self.assertLess(after_doc.index("## Handoffs\n"), after_doc.index(TODAY_HEADING))
        self.assertLess(after_doc.index(TODAY_HEADING), after_doc.index("## Punch list"))

    def test_a_waiver_alone_is_one_event_with_the_owners_words_and_its_rendered_line_at_the_home(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A")], punch=hlib.review_block())
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(
            text, records=True, questions=[{"source": "chat-ruling", "text": "the owner waived the double tap MAJOR"}],
            answers=[{"question": "q1", "answered": True, "words": "ship it, the double tap is rare",
                      "effect": {"kind": "waive", "finding": "src/turnstile.py:2"}}])
        self.assertEqual(code, 0, (out, err))
        new = [e for e in hlib.events(ws) if e["actor"]["station"] == "handoff-v2"]
        self.assertEqual([(e["kind"], e["words"], e["severity"]) for e in new],
                         [("waived", "ship it, the double tap is rare", "MAJOR")])
        self.assertEqual(hlib.events(ws)[-1], new[0])
        after_doc = hlib.read_doc(ws)
        added = inserted(before_doc, after_doc)
        grant = [l for l in added if "WAIVED (per user)" in l]
        self.assertEqual(len(grant), 1)
        self.assertGreater(after_doc.index(grant[0]), after_doc.index("## Punch list"))
        self.assertIn('"ship it, the double tap is rare"', grant[0])
        self.assertIn("Status: signed off with conditions\n", after_doc, "a Status: line is never edited")
        kinds = [w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"]
        self.assertEqual(kinds, ["records_log", "build_doc"])

    def test_a_reopening_alone(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A")],
                              punch=hlib.review_block() + ["- WAIVED (per user) %s 2026-09-26 %s MAJOR %s src/turnstile.py:2 "
                                                           "%s the counter skips a turn %s \"later\"" % (hlib.M, hlib.M, hlib.M,
                                                                                                         hlib.M, hlib.M)])
        ws, info = hlib.make_repo(self.tmp, text, records=True)
        state = hlib.state(ws)
        waived = next(f["id"] for f in state["findings"] if f["status"] == "waived")
        testlib.rmtree(ws)
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(
            text, records=True, questions=[{"source": "chat-ruling", "text": "reopen the double tap?"}],
            answers=[{"question": "q1", "answered": True, "words": "it came back on the bench",
                      "effect": {"kind": "reopen", "finding": waived}}])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(hlib.events(ws)[-1]["kind"], "reopened")
        added = inserted(before_doc, hlib.read_doc(ws))
        self.assertEqual(len([l for l in added if "REOPENED (per user)" in l]), 1)

    def test_the_checkpoint_commit_is_read_and_recorded_never_made(self):
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(
            hlib.build_doc(), dirt={"notes.txt": "loose work\n"}, checkpoint=True)
        self.assertEqual(code, 0, (out, err))
        now = hlib.snapshot(ws, run_dir)
        self.assertEqual((now["head"], now["commits"]), (before["head"], before["commits"]))
        self.assertEqual(out["checkpoint"]["commit"], before["head"])
        self.assertIn("checkpointed", hlib.read_doc(ws))

    def test_the_pointer_is_carried_as_text_and_the_core_writes_nothing_outside_the_workspace(self):
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(hlib.build_doc())
        self.assertEqual(code, 0, (out, err))
        pointer = testlib.load_json(os.path.join(run_dir, "pointer.json"))
        self.assertEqual(pointer["file_name"], "handoff-turnstile.md")
        self.assertIn("/ship-v2 B %s" % hlib.DOC, pointer["text"])
        self.assertTrue(pointer["for_adapter"])
        outside = [w for w in out["writes"] if not w["path"].startswith(ws + os.sep) and not w["path"].startswith(run_dir)]
        self.assertEqual(outside, [])

    def test_on_codex_no_pointer_is_written_and_the_result_says_so(self):
        ws, info, drive, run_dir, before_doc, before, (code, out, err) = self.run_to_write(hlib.build_doc(),
                                                                                           harness="codex-cli")
        self.assertEqual(code, 0, (out, err))
        pointer = testlib.load_json(os.path.join(run_dir, "pointer.json"))
        self.assertFalse(pointer["for_adapter"])
        self.assertIn("no memory pointer", pointer["note"])


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheRefusals(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-refuse-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def answered(self, text, records=False):
        ws, info = hlib.make_repo(self.tmp, text, records=records)
        drive, run_dir = hlib.start(self.tmp, ws)
        hlib.through_gate(self, drive, self.tmp, run_dir)
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer",
                                hlib.answers_file(self.tmp, run_dir)])
        self.assertEqual(code, 0, (out, err))
        return ws, drive, run_dir

    def stops(self, ws, drive, run_dir, tag):
        before = hlib.snapshot(ws, run_dir)
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], tag, out["reason"])
        self.assertTrue(out["wrote_nothing"])
        now = hlib.snapshot(ws, run_dir)
        self.assertEqual((now["doc"], now["log"], now["head"]), (before["doc"], before["log"], before["head"]))
        return out

    def test_an_earlier_block_edited_after_the_photograph_is_refused_before_any_write(self):
        text = hlib.build_doc(handoffs=hlib.handoff_block("2026-09-25"))
        ws, drive, run_dir = self.answered(text)
        edited = text.replace("the bench clock drifts", "the bench clock never drifts")
        testlib.write_text(os.path.join(ws, hlib.DOC), edited)
        testlib.git(ws, ["commit", "-q", "-am", "handoff checkpoint (local): turnstile"])
        self.stops(ws, drive, run_dir, "block-edited")

    def test_the_doc_changed_since_the_photograph_is_refused(self):
        ws, drive, run_dir = self.answered(hlib.build_doc())
        testlib.write_text(os.path.join(ws, hlib.DOC), hlib.read_doc(ws) + "one more line\n")
        self.stops(ws, drive, run_dir, "photograph-moved")

    def test_a_commit_that_is_not_the_checkpoint_is_refused(self):
        ws, drive, run_dir = self.answered(hlib.build_doc())
        testlib.write_text(os.path.join(ws, "src", "other.py"), "X = 1\n")
        testlib.git(ws, ["add", "-A"])
        testlib.git(ws, ["commit", "-q", "-m", "more work"])
        self.stops(ws, drive, run_dir, "photograph-moved")

    def test_a_log_that_moved_since_the_photograph_is_refused(self):
        text = hlib.build_doc(punch=hlib.review_block())
        ws, drive, run_dir = self.answered(text, records=True)
        changed = text + "\n".join(hlib.review_block("2026-09-30", "B", [
            ("MINOR", "src/turnstile.py:1", "a new nit", "a reader trips")])) + "\n"
        testlib.write_text(os.path.join(ws, hlib.DOC), changed)
        hlib.records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", hlib.DOC])
        testlib.write_text(os.path.join(ws, hlib.DOC), text)
        self.stops(ws, drive, run_dir, "photograph-moved")


if __name__ == "__main__":
    unittest.main()
