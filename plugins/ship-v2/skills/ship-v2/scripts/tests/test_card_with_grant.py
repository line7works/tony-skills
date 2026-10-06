"""The E15 lane contract A27 (1): ship-v2 moves the card with a mid-run grant (E15-9 as amended for ship-v2).

For each mid-run grant ship-v2 writes the `waived` or `reopened` event and, when the slice's card changes by v1's rule
after the grant, a `card_set` event and its `Status:` line, in build-v2's records transaction (build-contract
sections 9 and 10), all or none, as handoff-v2 does (A23 (2)): one append carrying both events, then the doc. So a
waived slice then passes vertical-v2's sign-off check and a reopened one stops it; a refused append leaves the doc and
the log byte-equal; a `Status:` line that disagrees with the records' card is refused before any write; ship-v2's own
`Status:` write is never a fix's move (stop 2); a report-only run plans the card and writes nothing.
"""
import os
import unittest

import cr25lib
import slib
import testlib


def ours(ws):
    return [e for e in slib.log_lines(ws) if e["actor"]["station"] == "ship-v2"]


def status_of(ws, name="A"):
    text = testlib.read_text(os.path.join(ws, slib.DOC))
    section = text[text.index("## Slice %s " % name):]
    return next(line for line in section.split("\n") if line.startswith("Status:"))


def log_path(ws, doc=slib.DOC):
    slug = doc[:-3].replace("%", "%25").replace("_", "%5F").replace("/", "__")
    return os.path.join(ws, "docs", "records", slug + ".events.jsonl")


def blocker_cleared(test, tmp, name):
    """A run whose slice A held a BLOCKER that lap 1 fixed and recheck-v2 cleared: the card `signed off`, stage `clean`."""
    run = cr25lib.Run(test, tmp, name, majors=0)
    run.build()

    def signoff_writes(visit):          # what signoff-v2 itself writes while it runs
        run.findings.append(slib.raise_finding(run.tmp, run.ws, severity="BLOCKER", card=None,
                                               claim="the counter loses turns"))
        cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "rejected", "signoff-run")
    code, out, err = run.visit("signoff-v2", "findings", before_result=signoff_writes)
    test.assertEqual((code, out["next"]), (0, "fix"), (out, err))
    finding = run.findings[0]
    run.fix(1, [finding])
    out = run.recheck("all_clear", lambda: cr25lib.recheck(run.tmp, run.ws, finding, True, "rejected", "signed off",
                                                           "recheck-1"))
    test.assertEqual(out["next"], "report", out)
    return run, finding


@unittest.skipUnless(slib.usable() and cr25lib.vertical_skill() is not None,
                     "needs jsonschema, the records component, the three stations and vertical-v2 beside this core")
class TheCardMovesWithTheGrant(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-card-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_a_waiver_moves_the_card_and_its_status_line_in_one_append(self):
        run = cr25lib.Run(self, self.tmp, "w")
        run.build()
        run.signoff()
        before = testlib.read_text(os.path.join(run.ws, slib.DOC))
        out = run.grant("waive", run.findings[0], "Waive it, a bench quirk")
        self.assertEqual(out["next"], "fix", out)
        new = ours(run.ws)
        self.assertEqual([e["kind"] for e in new], ["waived", "card_set"])
        card = new[1]
        self.assertEqual((card["slice"], card["before"], card["after"]), ("A", "signed off with conditions",
                                                                          "signed off"))
        self.assertEqual(card["seq"], new[0]["seq"] + 1, "one append, all or none")
        self.assertEqual(card["actor"]["run_id"], new[0]["actor"]["run_id"])
        self.assertEqual(new[0]["words"], "Waive it, a bench quirk")
        after = testlib.read_text(os.path.join(run.ws, slib.DOC))
        self.assertEqual(status_of(run.ws), "Status: signed off")
        self.assertEqual(after, before.replace("Status: signed off with conditions", "Status: signed off", 1),
                         "the Status: line is the one line ship-v2 writes")
        row = next(s for s in slib.state(run.ws)["slices"] if s["name"] == "A")
        self.assertEqual((row["card_observed"], row["card_derived"]), ("signed off", "signed off"))
        slib.commit_all(run.ws, "after the waiver")
        code, gate = cr25lib.vertical_gate(run.tmp, run.ws, "vertical-after-waiver")
        self.assertEqual((code, (gate or {}).get("next")), (0, "ask"), gate)

    def test_a_reopened_blocker_moves_the_card_to_rejected_and_vertical_v2_stops_the_slice(self):
        run, finding = blocker_cleared(self, self.tmp, "r")
        self.assertEqual(status_of(run.ws), "Status: signed off")
        out = run.grant("reopen", finding, "Reopen it, it came back on the bench")
        self.assertEqual(out["next"], "lap", out)
        new = ours(run.ws)
        self.assertEqual([(e["kind"], e.get("before"), e.get("after")) for e in new],
                         [("reopened", None, None), ("card_set", "signed off", "rejected")])
        self.assertEqual(status_of(run.ws), "Status: rejected")
        slib.commit_all(run.ws, "after the reopening")
        code, gate = cr25lib.vertical_gate(run.tmp, run.ws, "vertical-after-reopen")
        self.assertEqual(code, 10, gate)
        self.assertEqual(gate["stop_tag"], "gate-short", gate)
        self.assertIn("slice A (rejected)", gate["reason"])

    def test_a_grant_that_leaves_the_card_where_it_stands_writes_no_card(self):
        run = cr25lib.Run(self, self.tmp, "two", majors=2)
        run.build()
        run.signoff()
        before = testlib.read_text(os.path.join(run.ws, slib.DOC))
        run.grant("waive", run.findings[0], "Waive the first one")
        self.assertEqual([e["kind"] for e in ours(run.ws)], ["waived"])
        self.assertEqual(testlib.read_text(os.path.join(run.ws, slib.DOC)), before)

    def test_ship_v2s_own_status_write_is_never_a_fixs_move(self):
        """The waiver lands after the lap's pin; the fix that follows is not stop 2 for the doc ship-v2 itself moved."""
        run = cr25lib.Run(self, self.tmp, "pin", majors=2)
        run.build()
        run.signoff()
        run.grant("waive", run.findings[0], "Waive the first one")
        run.grant("waive", run.findings[1], "And the second")
        self.assertEqual(status_of(run.ws), "Status: signed off")
        out = run.fix(1)
        self.assertEqual(out["next"], "visit --station recheck-v2", out)

    def test_after_a_reopening_the_next_lap_is_not_stop_2(self):
        run, finding = blocker_cleared(self, self.tmp, "lap")
        run.grant("reopen", finding, "Reopen it")
        code, out, err = run.lap()
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        out = run.fix(2, [finding])
        self.assertEqual(out["next"], "visit --station recheck-v2", out)

    def test_a_refused_append_leaves_the_doc_and_the_log_byte_equal(self):
        run = cr25lib.Run(self, self.tmp, "lock")
        run.build()
        run.signoff()
        log = log_path(run.ws)
        testlib.write_text(log + ".lock", '{"pid": %d, "pid_start": "held by the test", "command": "append"}'
                           % os.getpid())
        doc_before, log_before = slib.sha(os.path.join(run.ws, slib.DOC)), slib.sha(log)
        code, asked, err = run.drive(["pause", "--run-dir", run.run_dir, "--question", slib.question_file(
            run.tmp, run.run_dir, "Waive it or hold?", source="ship", station=None, finding=run.findings[0])])
        self.assertEqual(code, 0, (asked, err))
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", slib.answer_file(
            run.tmp, run.run_dir, asked["pause"], "Waive it", {"kind": "waive", "finding": run.findings[0]})])
        self.assertEqual((code, out.get("stop_tag")), (0, "records-refused"), (out, err))
        self.assertEqual((slib.sha(os.path.join(run.ws, slib.DOC)), slib.sha(log)), (doc_before, log_before))
        self.assertEqual(ours(run.ws), [])
        os.remove(log + ".lock")
        code, out, err = slib.report(run.drive, run.run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "records-refused"), (out, err))
        self.assertTrue(out["wrote_nothing"], out["writes"])

    def test_a_status_line_that_disagrees_with_the_records_card_is_refused_before_any_write(self):
        run = cr25lib.Run(self, self.tmp, "line")
        run.build()
        run.signoff()
        # the records move the card and the doc does not (another station's half-done card): the line disagrees with
        # the records' card although the doc never moved since the pin (a hand edit of the doc is the window rule's
        # stop 2 instead, test_window.py)
        slib.append(run.tmp, run.ws, [dict(slib._base("signoff-v2", "a-later-signoff", run.ws), kind="card_set",
                                           slice="A", before="signed off with conditions", after="rejected")])
        doc_before, log_before = slib.sha(os.path.join(run.ws, slib.DOC)), slib.sha(log_path(run.ws))
        code, asked, err = run.drive(["pause", "--run-dir", run.run_dir, "--question", slib.question_file(
            run.tmp, run.run_dir, "Waive it or hold?", source="ship", station=None, finding=run.findings[0])])
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", slib.answer_file(
            run.tmp, run.run_dir, asked["pause"], "Waive it", {"kind": "waive", "finding": run.findings[0]})])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("Status:", out["reason"])
        self.assertEqual((slib.sha(os.path.join(run.ws, slib.DOC)), slib.sha(log_path(run.ws))),
                         (doc_before, log_before))
        self.assertEqual(testlib.load_json(os.path.join(run.run_dir, "checkpoint.json"))["phase"], "paused")


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class ReportOnly(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-card-ro-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_report_only_plans_the_card_and_writes_nothing(self):
        ws = slib.make_repo(self.tmp)
        tree = slib.Tree(self.tmp)
        finding = slib.raise_finding(self.tmp, ws)          # the records as an earlier review left them
        slib.set_status(ws, "A", "signed off with conditions")
        drive, run_dir = slib.start(self, tree, self.tmp, ws, report_only=True)
        slib.through_hook(self, drive, self.tmp, run_dir)
        slib.visit(self, drive, run_dir, "build-v2", "report-only", ws)
        code, out, err = slib.visit(self, drive, run_dir, "signoff-v2", "report-only", ws)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        before = slib.snapshot(ws)
        code, asked, err = drive(["pause", "--run-dir", run_dir, "--question", slib.question_file(
            self.tmp, run_dir, "Waive it or hold?", source="ship", station=None, finding=finding)])
        code, out, err = drive(["pause", "--run-dir", run_dir, "--answer", slib.answer_file(
            self.tmp, run_dir, asked["pause"], "Waive it", {"kind": "waive", "finding": finding})])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(before, slib.snapshot(ws), "report-only: nothing outside the run directory")
        planned = testlib.load_json(os.path.join(run_dir, "events.json"))
        self.assertEqual([e["kind"] for e in planned["events"]], ["waived", "card_set"])
        self.assertEqual((planned["events"][1]["before"], planned["events"][1]["after"]),
                         ("signed off with conditions", "signed off"))


if __name__ == "__main__":
    unittest.main()
