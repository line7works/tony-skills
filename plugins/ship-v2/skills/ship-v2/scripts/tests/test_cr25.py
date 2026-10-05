"""CR-25's measurement as tests (contract section 6.2; `cr25lib.py` says how each row is measured).

These tests hold the measurement, not a ruling: they state what the records, the slice's `Status:` line and
vertical-v2's real gate show after a ship run that recorded a mid-run waiver or reopening (E15-9 as it stands: ship-v2
writes the grant event and no card move) and then ended each way. Where a row shows a card that disagrees with v1's
rule, or a gate that passes a reopened slice, that is the builder's numbered question to the owner (CR-25), not a
behavior this core chose; a ruling that moves the card with the grant (as A23 (2) did for handoff-v2) changes these
rows, and these tests then fail on purpose.
"""
import unittest

import cr25lib
import slib
import testlib

# scenario: (how the ship run ends, the card the records hold, the card by v1's rule, the Status: line, the gate)
MEASURED = {
    "waive_clean_end": ("completed ", "signed off with conditions", "signed off", "signed off with conditions", "stops"),
    "waive_stop_1": ("stopped extra-lap-exhausted", "signed off with conditions", "signed off with conditions",
                     "signed off with conditions", "stops"),
    "waive_stop_2": ("stopped spec-change", "signed off with conditions", "signed off with conditions",
                     "signed off with conditions", "stops"),
    "waive_stop_3": ("stopped build-not-complete", "signed off with conditions", "signed off",
                     "signed off with conditions", "stops"),
    "waive_stop_4": ("stopped outside-footprint", "signed off with conditions", "signed off with conditions",
                     "signed off with conditions", "stops"),
    "waive_pause": ("paused (the run waits)", "signed off with conditions", "signed off", "signed off with conditions",
                    "stops"),
    "reopen_clean_end": ("completed ", "signed off", "signed off", "signed off", "passes"),
    "reopen_stop_1": ("stopped extra-lap-exhausted", "signed off with conditions", "signed off with conditions",
                      "signed off with conditions", "stops"),
    "reopen_stop_2": ("stopped spec-change", "signed off", "signed off with conditions", "signed off", "passes"),
    "reopen_stop_4": ("stopped outside-footprint", "signed off", "signed off with conditions", "signed off", "passes"),
    "reopen_pause": ("paused (the run waits)", "signed off", "signed off with conditions", "signed off", "passes"),
}


@unittest.skipUnless(slib.usable() and cr25lib.vertical_skill() is not None,
                     "needs jsonschema, the records component, the three stations and vertical-v2 beside this core")
class TheMeasurement(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-cr25-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_every_scenario_measures_as_recorded(self):
        for name, scenario in cr25lib.scenarios():
            with self.subTest(scenario=name):
                row = scenario(self, self.tmp)
                end, observed, v1_card, status, gate = MEASURED[name]
                self.assertEqual((row["ship_end"], row["card_observed"], row["v1_card"], row["status_line"],
                                  row["gate"]), (end, observed, v1_card, status, gate), row)
                self.assertIn(row["ship_events"][-1] if row["ship_events"] else None, ("waived", "reopened"), row)

    def test_the_disagreement_is_the_owners_question(self):
        """Measured: a waived slice's card stays where the station left it, so vertical-v2's gate stalls it; a
        reopened slice's card stays `signed off`, so the gate passes it. Both are CR-25's numbered question."""
        disagree = [name for name, row in MEASURED.items() if row[1] != row[2] or row[3] != row[2]]
        passes_reopened = [name for name, row in MEASURED.items() if name.startswith("reopen") and row[4] == "passes"
                           and row[2] != "signed off"]
        self.assertEqual(sorted(disagree), ["reopen_pause", "reopen_stop_2", "reopen_stop_4", "waive_clean_end",
                                            "waive_pause", "waive_stop_3"])
        self.assertEqual(sorted(passes_reopened), ["reopen_pause", "reopen_stop_2", "reopen_stop_4"])


if __name__ == "__main__":
    unittest.main()
