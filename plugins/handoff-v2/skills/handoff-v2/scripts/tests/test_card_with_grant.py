"""The E15 lane contract A23: the card moves with a grant (2), and records' tail rule after a handoff write (1).

A23 (2), E15-9 as amended for handoff-v2: for each grant the run writes the `waived` or `reopened` event and, when the
slice's card changes by v1's rule after the grants, a `card_set` event and its `Status:` line, in the same records
transaction build-v2 uses for a card (build-contract sections 9 and 10), all or none; the block's `Cards:` line shows
the new card. So a waived slice then passes vertical-v2's sign-off check, a reopened one stops it (the slice 1b
check's `p01b` shape), and a failure mid-transaction leaves the doc and the log byte-equal.

A23 (1): records' section 11.7 accepts an imported record line that only moved, so the next levelling pass accepts
the doc a handoff wrote above imported lines (the check's `p02` shape); handoff-v2 keeps a guard: a write that would
leave the doc in a shape the widened rule still refuses stops `write-refused` with nothing written.
"""
import json
import os
import subprocess
import sys
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import doc as docmod  # noqa: E402

M = hlib.M
WAIVED_BLOCKER = ("- WAIVED (per user) %s 2026-09-26 %s BLOCKER %s src/turnstile.py:2 %s the counter skips a turn %s "
                  "\"later\"" % (M, M, M, M, M))
CONDITIONS = dict(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                          ("B", "the spinner", "signed off", "Slice A")], punch=hlib.review_block())
REOPENABLE = dict(slices=[("A", "the counter", "signed off", "nothing"), ("B", "the spinner", "signed off", "Slice A")],
                  punch=hlib.review_block(findings=[("BLOCKER", "src/turnstile.py:2", "the counter skips a turn",
                                                     "a double tap loses one")]) + [WAIVED_BLOCKER])


def vertical_skill():
    path = testlib.checkout_sibling("vertical-v2")
    return None if path is None else os.path.join(path, "skills", "vertical-v2")


def vertical_gate(tmp, ws, run):
    """vertical-v2's own gate through its real CLI (check-input, then gate), as the next station runs it."""
    skill = vertical_skill()
    run_dir = os.path.join(tmp, run)
    doc = testlib.make_input(ws, run_dir)
    doc["station"] = {"session_model": "claude-opus-5-5"}
    path = os.path.join(tmp, run + "-input.json")
    testlib.write_json(path, doc)
    env = testlib.base_env({"VERTICAL_V2_TEST": "1"})
    out = None
    for args in (["check-input", path], ["gate", "--run-dir", run_dir, "--name", hlib.FEATURE]):
        proc = subprocess.run([sys.executable, os.path.join(skill, "scripts", "vertical.py")] + args, cwd=tmp, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out = json.loads(proc.stdout.decode("utf-8"))
        except ValueError:
            out = None
        if proc.returncode != 0:
            return proc.returncode, out, proc.stderr.decode("utf-8", "replace")
    return 0, out, ""


def subsequence(before, after):
    """Whether every line of `before` is in `after`, in order (`after` is `before` with lines inserted)."""
    rest = iter(after.splitlines(True))
    return all(any(line == other for other in rest) for line in before.splitlines(True))


def commit_all(ws, subject="after the handoff"):
    testlib.git(ws, ["add", "-A"])
    testlib.git(ws, ["commit", "-q", "-m", subject], when="2026-10-04T13:00:00-07:00")


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheCardMovesWithTheGrant(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-card-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def granted(self, doc, kind, location="src/turnstile.py:2", report_only=False, before_write=None,
                edit_before_select=None):
        ws, info = hlib.make_repo(self.tmp, hlib.build_doc(**doc), records=True)
        if edit_before_select is not None:
            testlib.write_text(os.path.join(ws, hlib.DOC), edit_before_select(hlib.read_doc(ws)))
        state = hlib.state(ws)
        finding = next(f["id"] for f in state["findings"] if f["location"]["raw"] == location)
        drive, run_dir = hlib.start(self.tmp, ws, report_only=report_only)
        hlib.through_gate(self, drive, self.tmp, run_dir, questions=[{"source": "chat-ruling", "text": "the grant"}])
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer", hlib.answers_file(
            self.tmp, run_dir, [{"question": "q1", "answered": True, "words": "the owner's words",
                                 "effect": {"kind": kind, "finding": finding}}])])
        self.assertEqual(code, 0, (out, err))
        if before_write is not None:
            before_write(ws)
        before = hlib.snapshot(ws, run_dir)
        before_doc = hlib.read_doc(ws)
        result = drive(["write", "--run-dir", run_dir])
        return ws, run_dir, drive, before, before_doc, result

    def ours(self, ws):
        return [e for e in hlib.events(ws) if e["actor"]["station"] == "handoff-v2"]

    def test_a_waiver_moves_the_card_and_its_status_line_in_one_append(self):
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(CONDITIONS, "waive")
        self.assertEqual(code, 0, (out, err))
        new = self.ours(ws)
        self.assertEqual([e["kind"] for e in new], ["waived", "card_set"])
        card = new[1]
        self.assertEqual((card["slice"], card["before"], card["after"]),
                         ("A", "signed off with conditions", "signed off"))
        self.assertEqual(new[0]["actor"]["run_id"], card["actor"]["run_id"])
        self.assertEqual(card["seq"], new[0]["seq"] + 1, "one append, all or none")
        after_doc = hlib.read_doc(ws)
        self.assertIn("## Slice A %s the counter" % hlib.D, after_doc)
        self.assertEqual(after_doc.count("Status: signed off with conditions\n"), 0)
        self.assertTrue(subsequence(before_doc.replace("Status: signed off with conditions\n", "Status: signed off\n"),
                                    after_doc),
                        "the Status: line is the one line edited; every other change is an insertion")
        cards_line = next(l for l in after_doc.splitlines() if l.startswith("- Cards: "))
        self.assertTrue(cards_line.startswith("- Cards: A signed off "), cards_line)
        self.assertIn("signed off with conditions", cards_line, "the line names the card the grant moved it from")
        state = hlib.state(ws)
        self.assertEqual(next(s for s in state["slices"] if s["name"] == "A")["card_observed"], "signed off")
        self.assertEqual([w["kind"] for w in out["writes"] if w["kind"] != "run_artifact"], ["records_log", "build_doc"])

    def test_after_a_waiver_vertical_v2_passes_the_slice(self):
        if vertical_skill() is None:
            self.skipTest("vertical-v2 is not beside this core (the installed shape)")
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(CONDITIONS, "waive")
        self.assertEqual(code, 0, (out, err))
        commit_all(ws)
        code, out, err = vertical_gate(self.tmp, ws, "vertical-after-waiver")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out.get("next"), "ask", out)

    def test_a_reopening_moves_the_card_to_rejected(self):
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(REOPENABLE, "reopen")
        self.assertEqual(code, 0, (out, err))
        new = self.ours(ws)
        self.assertEqual([(e["kind"], e.get("before"), e.get("after")) for e in new],
                         [("reopened", None, None), ("card_set", "signed off", "rejected")])
        after_doc = hlib.read_doc(ws)
        a_section = after_doc[after_doc.index("## Slice A"):after_doc.index("## Slice B")]
        self.assertIn("Status: rejected\n", a_section)

    def test_after_a_reopening_vertical_v2_stops_the_slice(self):
        if vertical_skill() is None:
            self.skipTest("vertical-v2 is not beside this core (the installed shape)")
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(REOPENABLE, "reopen")
        self.assertEqual(code, 0, (out, err))
        commit_all(ws)
        code, out, err = vertical_gate(self.tmp, ws, "vertical-after-reopen")
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "gate-short", out)
        self.assertIn("slice A (rejected)", out["reason"])

    def test_a_grant_that_leaves_the_card_where_it_stands_writes_no_card(self):
        doc = dict(slices=[("A", "the counter", "signed off", "nothing"), ("B", "the spinner", "not started", "Slice A")],
                   punch=hlib.review_block(findings=[("MINOR", "src/turnstile.py:5", "the name is vague",
                                                      "a reader guesses")]))
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(doc, "waive",
                                                                               location="src/turnstile.py:5")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual([e["kind"] for e in self.ours(ws)], ["waived"])
        self.assertEqual(hlib.read_doc(ws).count("Status: signed off\n"), 1)

    def test_a_failure_mid_transaction_leaves_the_doc_and_the_log_byte_equal(self):
        def hold_the_lock(ws):
            testlib.write_text(hlib.log_path(ws) + ".lock",
                               json.dumps({"pid": os.getpid(), "pid_start": "held by the test", "command": "append"}))
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(CONDITIONS, "waive",
                                                                               before_write=hold_the_lock)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "records-refused", out["reason"])
        now = hlib.snapshot(ws, run_dir)
        self.assertEqual((now["doc"], now["log"]), (before["doc"], before["log"]))
        self.assertEqual(self.ours(ws), [])
        self.assertIn("Status: signed off with conditions\n", hlib.read_doc(ws))

    def test_a_status_line_that_disagrees_with_the_records_card_is_refused_before_any_write(self):
        edit = lambda text: text.replace("Status: signed off with conditions\n", "Status: built\n")  # noqa: E731
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(CONDITIONS, "waive",
                                                                               edit_before_select=edit)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "write-refused", out["reason"])
        self.assertIn("Status:", out["reason"])
        now = hlib.snapshot(ws, run_dir)
        self.assertEqual((now["doc"], now["log"]), (before["doc"], before["log"]))

    def test_report_only_plans_the_card_and_writes_nothing(self):
        ws, run_dir, drive, before, before_doc, (code, out, err) = self.granted(CONDITIONS, "waive", report_only=True)
        self.assertEqual(code, 0, (out, err))
        now = hlib.snapshot(ws, run_dir)
        self.assertEqual((now["doc"], now["log"]), (before["doc"], before["log"]))
        planned = testlib.load_json(os.path.join(run_dir, "events.json"))
        self.assertEqual([e["kind"] for e in planned], ["waived", "card_set"])
        with open(os.path.join(run_dir, "planned-doc.md"), encoding="utf-8") as fh:
            self.assertNotIn("Status: signed off with conditions\n", fh.read())


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheNextLevellingPass(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-level-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_p02_the_doc_a_handoff_wrote_above_imported_lines_still_levels(self):
        doc = dict(slices=[("A", "the counter", "signed off", "nothing"), ("B", "the spinner", "not started", "Slice A")],
                   punch=hlib.review_block(findings=[("MINOR", "src/turnstile.py:2", "the counter name is vague",
                                                      "a reader guesses")]))
        ws, info = hlib.make_repo(self.tmp, hlib.build_doc(**doc), records=True)
        drive, run_dir = hlib.start(self.tmp, ws)
        hlib.through_write(self, drive, self.tmp, run_dir)
        body = hlib.records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", hlib.DOC, "--dry-run"])
        self.assertEqual(body["would_import"], 0, body)

    def test_a_waiver_then_the_next_levelling_pass_imports_nothing(self):
        ws, info = hlib.make_repo(self.tmp, hlib.build_doc(**CONDITIONS), records=True)
        drive, run_dir = hlib.start(self.tmp, ws)
        gate = hlib.through_gate(self, drive, self.tmp, run_dir, questions=[{"source": "chat-ruling", "text": "waive?"}])
        finding = gate["open"][0]["id"]
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer", hlib.answers_file(
            self.tmp, run_dir, [{"question": "q1", "answered": True, "words": "ship it",
                                 "effect": {"kind": "waive", "finding": finding}}])])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        body = hlib.records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", hlib.DOC, "--dry-run"])
        self.assertEqual(body["would_import"], 0, body)

    MINOR_DOC = dict(slices=[("A", "the counter", "signed off", "nothing"),
                             ("B", "the spinner", "not started", "Slice A")],
                     punch=hlib.review_block(findings=[("MINOR", "src/turnstile.py:2", "the counter name is vague",
                                                        "a reader guesses")]))

    def refused_at_photograph(self, ws):
        """R1B1-5, handoff's half: the guard's dry run runs at `photograph` too, so a doc the records component already
        refuses stops before the gate (no answer is lost), with the way out; nothing written."""
        before = hlib.snapshot(ws)
        drive, run_dir = hlib.start(self.tmp, ws, run="refused")
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["photograph", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "write-refused", out["reason"])
        self.assertTrue(out["wrote_nothing"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "gate.json")), "the stop comes before the gate")
        self.assertEqual(hlib.snapshot(ws), before)
        self.assertTrue(out["reason"].endswith("records section 11.7 accepts only lines that moved"), out["reason"])
        return out["reason"]

    def test_a_doc_the_rule_already_refuses_stops_at_photograph_with_the_way_out(self):
        ws, info = hlib.make_repo(self.tmp, hlib.build_doc(**self.MINOR_DOC), records=True)
        path = os.path.join(ws, hlib.DOC)
        testlib.write_text(path, hlib.read_doc(ws).replace("the counter name is vague", "the counter name is fine"))
        number = next(i for i, l in enumerate(hlib.read_doc(ws).splitlines(), 1) if "the counter name is fine" in l)
        reason = self.refused_at_photograph(ws)
        self.assertIn("put line %d back to its imported text" % number, reason)
        self.assertIn("the counter name is vague", reason, "the imported text is named")

    def test_on_a_doc_whose_lines_moved_the_way_out_names_where_the_edited_line_stands_now(self):
        ws, info = hlib.make_repo(self.tmp, hlib.build_doc(**self.MINOR_DOC), records=True)
        drive, run_dir = hlib.start(self.tmp, ws)
        hlib.through_write(self, drive, self.tmp, run_dir)
        path = os.path.join(ws, hlib.DOC)
        text = hlib.read_doc(ws)
        at = text.rindex("the counter name is vague")   # the punch-list line, not the block's `- Open:` line
        testlib.write_text(path, text[:at] + "the counter name is fine" + text[at + len("the counter name is vague"):])
        number = next(i for i, l in enumerate(hlib.read_doc(ws).splitlines(), 1) if "the counter name is fine" in l)
        self.assertGreater(number, 40, "the line moved down under the handoff block")
        reason = self.refused_at_photograph(ws)
        self.assertIn("put line %d back to its imported text" % number, reason)


class TheGuard(unittest.TestCase):
    """`doc.levelling_problem`: the planned doc must keep every imported record line, in order, and add no line
    byte-equal to one (a copy would take the imported line's place in the widened rule's in-order match)."""

    LINE = "- MINOR %s src/turnstile.py:2 %s a vague name %s a reader guesses %s Slice A review" % (M, M, M, M)

    def test_lines_that_only_moved_hold(self):
        text = "a\n## Handoffs\n\n### x\n## Punch list\n%s\n" % self.LINE
        self.assertIsNone(docmod.levelling_problem(text, [1, 2, 3], [(2, self.LINE)]))

    def test_an_inserted_copy_of_an_imported_line_is_a_problem(self):
        text = "a\n%s\n## Punch list\n%s\n" % (self.LINE, self.LINE)
        found = docmod.levelling_problem(text, [1], [(3, self.LINE)])
        self.assertIsNotNone(found)
        self.assertIn("byte-equal", found)

    def test_an_imported_line_the_plan_lost_is_a_problem(self):
        text = "a\n## Punch list\n- something else\n"
        self.assertIsNotNone(docmod.levelling_problem(text, [], [(3, self.LINE)]))

    def test_r1b1_5_the_way_out_names_where_the_changed_line_stands_now(self):
        """Imported at lines 3 and 4; two lines were inserted above them since, and the second was edited: its
        neighbour stands two lines lower now, so the way out names line 6, never the old number 4."""
        other = self.LINE.replace("a vague name", "a short name")
        text = "a\nb\nc\n## Punch list\n%s\n%s\n" % (other, self.LINE.replace("vague", "fine"))
        found = docmod.tail_rule_way_out(text, [(3, other), (4, self.LINE)],
                                         {"line": 4, "imported_raw": self.LINE})
        self.assertTrue(found.startswith("put line 6 back to its imported text"), found)
        self.assertIn(repr(self.LINE), found)
        self.assertTrue(found.endswith("records section 11.7 accepts only lines that moved"), found)

    def test_r1b1_5_one_imported_line_is_named_by_how_far_its_record_heading_moved(self):
        """One imported line, no neighbour to measure by: its record block heading, read then at line 3, stands at
        line 6 now, so the changed line imported at line 4 is named at line 7."""
        heading = "### 2026-09-24 %s review: Slice A" % hlib.D
        text = "# T\n\na\nb\nc\n%s\n%s\n" % (heading, self.LINE.replace("vague", "fine"))
        found = docmod.tail_rule_way_out(text, [(4, self.LINE)], {"line": 4, "imported_raw": self.LINE}, {4: 3})
        self.assertTrue(found.startswith("put line 7 back to its imported text"), found)

    def test_r1b1_5_a_new_record_above_the_tail_names_its_own_way_out(self):
        found = docmod.tail_rule_way_out("a\n", [(3, self.LINE)], {"line": 2, "current_raw": "x",
                                                                    "last_imported_line": 3})
        self.assertIn("line 2", found)
        self.assertTrue(found.endswith("records section 11.7 accepts only lines that moved"), found)


if __name__ == "__main__":
    unittest.main()
