"""punch-F2: a recovery that stops names what actually landed, per append (E13 punch list).

Astra's recheck left F2 (BLOCKER) partly closed: "Kill/recovery probe stops correctly but reports
only finding seq 4; the records CLI shows landed card seq 5. Its receipt remains `unknown`."

The shape: `record` is killed around its final `card_set` append, the source moves (a new file),
and `record` runs again. The recovery pass stops `stale_source / source_moved`, correctly, before it
reaches the settle step, so an append whose outcome the receipt never learned stayed `unknown` and
the result listed only what the receipt already held as landed.

Now, before a stop is delivered, every append the receipt holds as `unknown` is asked about through
the records component (`records.py events`, argv only, read-only): an append the log holds is
recorded in the receipt as `landed` (recovered) and reported with its seqs; an append the log does
not hold is reported under `records.not_landed` as `absent`. Nothing is ever appended by that
question, and the stale stop still wins.

Every shape runs through the real `signoff.py` in front of the real component, the kill injected
by the stand-in `records.py`; what landed is read back through the records CLI.
"""
import json
import os
import subprocess
import sys
import unittest

import shimlib
import testlib
from test_fix2_astra import DOC, _Case

testlib.add_scripts_to_path()

RECORDS = os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")


class _Punch(_Case):

    def cli_seqs(self, kind):
        """The seqs of this run's events of one kind, as the records CLI reports them."""
        proc = subprocess.run([sys.executable, RECORDS, "events", "--workspace", self.workspace,
                               "--doc", DOC, "--kind", kind],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        body = json.loads(proc.stdout.decode("utf-8"))
        return [row["seq"] for row in body.get("results", [])
                if ((row.get("event") or {}).get("actor") or {}).get("run_id")
                == "signoff-fix2-run"]

    def receipt(self):
        return testlib.load_json(os.path.join(self.run_dir, "receipt.json"))

    def kill(self, kind, when):
        shimlib.fault(self.fault, command="append", kind=kind, action=when)
        code, body, err = self.record()
        self.assertNotIn(code, (0, 10), "the first pass was killed: %s %s" % (code, err))
        shimlib.disarm(self.fault)

    def add_late(self):
        self.write("src/late.py", "LATE = True\n")

    def stale(self):
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual((result["status"], result["stop_reason_code"]),
                         ("stale_source", "source_moved"), json.dumps(result)[:1500])
        self.assertFalse(result["verdict_recorded"])
        return result

    def appended(self, result):
        return {row["name"]: row for row in result["records"]["appended"]}


class PunchF2KilledDuringTheCardAppend(_Punch):
    """Her probe: the card append landed (the kill came after it), the source moved, recovery."""

    def test_the_landed_card_is_reported_with_its_seq_and_the_receipt_says_landed(self):
        code, body, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(body))
        self.kill("card_set", "kill_after")
        card_seqs = self.cli_seqs("card_set")
        finding_seqs = self.cli_seqs("finding_raised")
        self.assertEqual(len(card_seqs), 1, "the card append landed before the kill")
        self.assertEqual(self.receipt()["appends"]["card"]["outcome"], "unknown")
        self.add_late()
        result = self.stale()
        rows = self.appended(result)
        self.assertEqual(sorted(rows), ["card", "findings"], json.dumps(result["records"]))
        self.assertEqual(rows["card"]["seqs"], card_seqs, "the card's seq is the log's")
        self.assertTrue(rows["card"].get("recovered"))
        self.assertEqual(rows["findings"]["seqs"], finding_seqs)
        self.assertEqual(result["records"].get("not_landed") or [], [])
        block = self.receipt()["appends"]["card"]
        self.assertEqual((block["outcome"], block["seqs"], block["recovered"]),
                         ("landed", card_seqs, True))
        self.assertIn("card", result["stop_reason"])
        self.assertEqual(self.cli_seqs("card_set"), card_seqs, "nothing appended again")

    def test_a_second_recovery_says_the_same_and_appends_nothing(self):
        self.through_answer()
        self.kill("card_set", "kill_after")
        card_seqs = self.cli_seqs("card_set")
        self.add_late()
        self.stale()
        result = self.stale()
        self.assertEqual(self.appended(result)["card"]["seqs"], card_seqs)
        self.assertEqual(self.cli_seqs("card_set"), card_seqs)


class PunchF2KilledBetweenTheTwoAppends(_Punch):
    """The kill lands after the findings append and before the card append reaches the log."""

    def test_the_absent_card_is_reported_absent_and_never_appended(self):
        code, body, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(body))
        self.kill("card_set", "kill_before")
        self.assertEqual(self.cli_seqs("card_set"), [])
        finding_seqs = self.cli_seqs("finding_raised")
        self.add_late()
        result = self.stale()
        rows = self.appended(result)
        self.assertEqual(sorted(rows), ["findings"], json.dumps(result["records"]))
        self.assertEqual(rows["findings"]["seqs"], finding_seqs)
        self.assertEqual(result["records"].get("not_landed"),
                         [{"name": "card", "kinds": ["card_set"], "checked": "absent"}],
                         json.dumps(result["records"]))
        self.assertEqual(self.receipt()["appends"]["card"]["outcome"], "unknown",
                         "an append the log does not hold stays an intent, never `landed`")
        self.assertEqual(self.cli_seqs("card_set"), [], "never appended by the stop")


class PunchF2KilledDuringTheFindingsAppend(_Punch):
    """The kill lands after the findings append; the card was never planned."""

    def test_the_landed_findings_are_reported_from_the_log(self):
        code, body, err = self.through_answer()
        self.assertEqual(code, 0, err or json.dumps(body))
        self.kill("finding_raised", "kill_after")
        finding_seqs = self.cli_seqs("finding_raised")
        self.assertTrue(finding_seqs)
        self.assertEqual(self.receipt()["appends"]["findings"]["outcome"], "unknown")
        self.add_late()
        result = self.stale()
        rows = self.appended(result)
        self.assertEqual(sorted(rows), ["findings"], json.dumps(result["records"]))
        self.assertEqual(rows["findings"]["seqs"], finding_seqs)
        self.assertTrue(rows["findings"].get("recovered"))
        self.assertEqual(self.receipt()["appends"]["findings"]["outcome"], "landed")
        self.assertEqual(self.cli_seqs("card_set"), [])


class PunchF2Control(_Punch):
    """Control: the same kill with the source unmoved settles and completes, once."""

    def test_an_unmoved_recovery_completes_with_one_card_event(self):
        self.through_answer()
        self.kill("card_set", "kill_after")
        card_seqs = self.cli_seqs("card_set")
        code, body, err = self.record()
        self.assertEqual(code, 10, err or json.dumps(body))
        result = self.result()
        self.assertEqual(result["status"], "completed", json.dumps(result)[:1500])
        self.assertTrue(result["verdict_recorded"])
        self.assertEqual(self.cli_seqs("card_set"), card_seqs)


if __name__ == "__main__":
    unittest.main()
