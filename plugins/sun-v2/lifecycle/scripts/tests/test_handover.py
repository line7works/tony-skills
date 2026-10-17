"""EV-7's handover and the one order of first records (the reviewer's H13 closing rule; SEC-12, "The order of
first records"; RUN-1, RUN-3, RUN-13, EV-7), on fakes.

The restore here is a run of fake rows: a restore's own plan (EV-5: which reverses it offers) is not
built in this slice and is not tested. What is tested is the handover the frame gives a restore's go:
one deciding write, the retirement closed from that moment, its `closed` record written next or by
the next invocation of either run, after the recovery records SEC-12's order puts before it.
"""
import json
import os
import unittest

import harness
import rowlib
from sun_core import plan, texts
from test_log_op import at
from test_secrets_end_to_end import kinds

P = plan.RETIREMENT_PHASES
SECRET = "zz9handover" + harness.canary("handover")[-8:]
LATER_PASSWORD = "pw" + harness.canary("later")
DESCRIPTION = "retiring it; see %s and %s" % (SECRET, LATER_PASSWORD)


def address(password):
    return "postgres://appuser:%s@db.fixture.invalid:5432/appdb" % password


class Handover(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.count = 0

    def machine_with_lanes(self):
        self.count += 1
        m = harness.Machine(self.tmp, "h%d" % self.count, "h%d" % self.count)
        sunset_rows = [rowlib.keep("P1", P[0]), rowlib.owner_step("O1", P[2], mode="on his word"),
                       rowlib.secret_op("X1", P[2], needs=[{"output": "dump", "level": "made", "treatment": "then not applicable"}])]
        rowlib.install(m, rowlib.lane("sunset", sunset_rows, phases=P), rowlib.lane("restore", [rowlib.check("V1", "back")], phases=["back"]))
        m.put("dev/demo.env", "DATABASE_URL=%s\n" % address("pw-at-the-look-" + "0" * 8), 0o600)
        return m

    def open_sunset(self, m, kill=None, description="retiring a fixture project"):
        looked = m.look(kind="sunset", inputs=m.inputs(description=description))
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset", kill=kill)
        return looked.doc["run"], went

    def test_EV7_RUN3_a_restores_go_closes_the_open_retirement_by_one_deciding_write(self):
        m = self.machine_with_lanes()
        sunset, went = self.open_sunset(m)
        self.assertEqual(went.ending, "waiting", went.text)
        refused = m.look(kind="sunrise")
        self.assertEqual(refused.lines[0], texts.RUN_OPEN + sunset, "any other new summons is refused while the retirement is open")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", "a restore over the open retirement was not accepted: " + looked.text)
        restore = looked.doc["run"]
        self.assertEqual(set(m.open_runs().values()), {sunset}, "the retirement is not open before the restore's go")
        self.assertEqual(m.summon("status", "demo", "--kind", "sunset").ending, "waiting", "the retirement is not resumable before the restore's go")
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        opening = m.journal(restore)[0]
        self.assertEqual((opening["kind"], opening["closes"]), ("open", sunset))
        self.assertEqual(kinds(m.journal(sunset))[-1], ("run-end", "closed"))
        self.assertEqual(m.journal(sunset)[-1]["restore"], restore)
        again = m.summon("resume", "demo", "--run", sunset, "--position", len(m.journal(sunset)), "--word", "go on")
        self.assertEqual((again.ending, again.lines), ("refused", [texts.CLOSED_NEVER_RESUMES]))

    def sweep_points(self):
        m = self.machine_with_lanes()
        self.open_sunset(m)
        looked = m.look(kind="restore")
        went = m.go(looked, kind="restore")
        return len([e for e in went.events if e["stage"] in ("pre", "mid", "post")])

    def test_EV7_at_no_write_boundary_of_the_restores_go_can_both_runs_go_on_and_at_none_can_neither(self):
        total = self.sweep_points()
        seen = {"before the deciding write": 0, "after it": 0}
        for point in range(total):
            m = self.machine_with_lanes()
            sunset, _ = self.open_sunset(m)
            looked = m.look(kind="restore")
            restore = looked.doc["run"]
            count = {"n": -1}

            def kill(event, want=point, count=count):
                if event["stage"] in ("pre", "mid", "post"):
                    count["n"] += 1
                    return count["n"] == want
                return False
            went = m.go(looked, kind="restore", kill=kill)
            self.assertTrue(went.killed)
            holders = set(m.open_runs().values())
            if not holders:
                # the restore has ended: the key has no open run because its last run is finished, not because one was lost
                self.assertEqual(m.journal(restore)[-1]["kind"], "run-end", "kill point %d: the key is left with no run that can go on" % point)
                self.assertEqual(kinds(m.journal(sunset))[-1], ("run-end", "closed"), "kill point %d" % point)
                seen["after it"] += 1
                continue
            self.assertIn(holders, ({sunset}, {restore}), "kill point %d: the key is left with %s" % (point, holders))
            if holders == {sunset}:
                seen["before the deciding write"] += 1
                status = m.summon("status", "demo", "--kind", "sunset")
                self.assertEqual(status.ending, "waiting", "kill point %d: the retirement cannot go on though the restore has no go" % point)
                self.assertEqual([r for r in m.journal(sunset) if r["kind"] == "run-end"], [])
            else:
                seen["after it"] += 1
                before = len(m.journal(sunset))
                effects = [c for c in m.calls("fakehost") if c["changing"]]
                closed_already = bool([r for r in m.journal(sunset) if r["kind"] == "run-end"])
                refused = m.summon("resume", "demo", "--kind", "sunset", "--position", before, "--word", "go on")
                self.assertEqual((refused.ending, refused.lines), ("refused", [texts.CLOSED_NEVER_RESUMES]), "kill point %d" % point)
                after = m.journal(sunset)
                self.assertEqual(kinds(after)[-1], ("run-end", "closed"), "kill point %d: the closing record was not written" % point)
                self.assertEqual(len(after), before + (0 if closed_already else 1), "kill point %d: more than the one closing record was written" % point)
                self.assertEqual([c for c in m.calls("fakehost") if c["changing"]], effects, "the retirement applied an effect after the handover")
                self.assertIn(m.summon("status", "demo", "--kind", "restore").ending, ("complete", "stopped", "waiting", "refused"))
        self.assertGreater(seen["before the deciding write"], 3)
        self.assertGreater(seen["after it"], 3)

    def handed_over_without_its_closing_record(self, m, sunset):
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="restore", kill=at("post", "replace", "open-runs.json"))
        self.assertTrue(went.killed)
        self.assertEqual(set(m.open_runs().values()), {looked.doc["run"]})
        self.assertEqual([r for r in m.journal(sunset) if r["kind"] == "run-end"], [])
        return looked.doc["run"]

    def test_EV7_the_restores_own_next_invocation_writes_the_missing_closing_record_before_any_other_record(self):
        m = self.machine_with_lanes()
        sunset, _ = self.open_sunset(m)
        restore = self.handed_over_without_its_closing_record(m, sunset)
        before = len(m.journal(restore))
        status = m.summon("status", "demo", "--kind", "restore")
        self.assertEqual(kinds(m.journal(sunset))[-1], ("run-end", "closed"))
        self.assertEqual(m.journal(sunset)[-1]["restore"], restore)

    def test_EV7_a_failed_gate_or_a_held_lock_in_that_invocation_leaves_the_record_unwritten_and_nothing_changed(self):
        m = self.machine_with_lanes()
        sunset, _ = self.open_sunset(m)
        self.handed_over_without_its_closing_record(m, sunset)
        before = m.snapshot(".sun-v2")
        os.rename(m.vault, m.vault + ".gone")
        gate = m.summon("resume", "demo", "--kind", "sunset")
        os.rename(m.vault + ".gone", m.vault)
        self.assertEqual(gate.ending, "refused")
        self.assertEqual(m.snapshot(".sun-v2"), before)
        close = m.hold_lock("demo", sunset)
        try:
            held = m.summon("resume", "demo", "--kind", "sunset")
        finally:
            close()
        self.assertEqual(held.lines[0][: len(texts.LOCK_HELD)], texts.LOCK_HELD)
        self.assertEqual([r for r in m.journal(sunset) if r["kind"] == "run-end"], [])

    def test_SEC12_RUN1_H13_two_disproof_records_then_the_receipt_then_the_closed_record_and_no_other_then_refused(self):
        self.count += 1
        m = harness.Machine(self.tmp, "k%d" % self.count, "k%d" % self.count)
        sunset_rows = [rowlib.keep("P1", P[0]), rowlib.secret_op("X1", P[2])]
        rowlib.install(m, rowlib.lane("sunset", sunset_rows, phases=P), rowlib.lane("restore", [rowlib.check("V1", "back")], phases=["back"]))
        m.put("dev/demo.env", "DATABASE_URL=%s\n" % address("pw-at-the-look-" + "0" * 8), 0o600)
        m.plan_fake("fakehost", {"command": "issue", "nth": 1, "value": SECRET})
        looked = m.look(kind="sunset", inputs=m.inputs(description=DESCRIPTION))
        self.assertEqual(looked.ending, "preview", looked.text)
        sunset = looked.doc["run"]
        # the retirement's go is killed between the secret's protected record and its disproof record and receipt
        killed = m.go(looked, kind="sunset", kill=lambda e: e["stage"] == "post" and e["op"] == "create" and os.sep + "protected" + os.sep in e["subject"]
                      and kinds(m.journal(sunset))[-1] == ("step", "receipt-due"))
        self.assertTrue(killed.killed, killed.text)
        self.assertEqual(kinds(m.journal(sunset))[-1], ("step", "receipt-due"))
        restore = self.handed_over_without_its_closing_record(m, sunset)
        self.assertEqual([r for r in m.journal(sunset) if r["kind"] == "disproof"], [], "the restore wrote in the retirement's journal before its go")
        # its env file then comes to hold a password equal to a saved description
        m.put("dev/demo.env", "DATABASE_URL=%s\n" % address(LATER_PASSWORD), 0o600)
        before = len(m.journal(sunset))
        calls = len(m.calls("fakehost")) + len(m.calls("fakedump"))
        refused = m.summon("resume", "demo", "--kind", "sunset", "--position", before, "--word", "go on")
        self.assertEqual((refused.ending, refused.lines), ("refused", [texts.CLOSED_NEVER_RESUMES]))
        new = m.journal(sunset)[before:]
        self.assertEqual(kinds(new), [("disproof", ""), ("disproof", ""), ("step", "receipt"), ("run-end", "closed")],
                         "the first records were not written in the one order, or another record stands among them")
        self.assertEqual(sorted(r["source"] for r in new[:2]), ["channel", "secret field"])
        self.assertEqual(new[3]["restore"], restore)
        for value in (SECRET, LATER_PASSWORD, DESCRIPTION):
            self.assertNowhere(value, refused)
            for record in new:
                self.assertNotIn(value, json.dumps(record))
        self.assertEqual(len(m.calls("fakehost")) + len(m.calls("fakedump")), calls, "a refused resume made a provider call")
        again = m.summon("resume", "demo", "--kind", "sunset", "--position", len(m.journal(sunset)), "--word", "go on")
        self.assertEqual((again.ending, again.lines), ("refused", [texts.CLOSED_NEVER_RESUMES]))
        self.assertEqual(len(m.journal(sunset)), before + 4, "a second refused resume wrote something more")

if __name__ == "__main__":
    unittest.main()
