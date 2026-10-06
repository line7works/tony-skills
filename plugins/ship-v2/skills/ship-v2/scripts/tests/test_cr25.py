"""CR-25's measurement as tests (contract section 6.2; `cr25lib.py` says how each row is measured), after the E15 lane
contract A27 (1).

These tests hold the measurement: what the records, the slice's `Status:` line and vertical-v2's real gate show after a
ship run that recorded a mid-run waiver or reopening and then ended each way. Before A27 (1), ship-v2 wrote the grant
event and no card move, and 6 of the 11 endings left the card wrong by v1's rule while 3 let vertical-v2's gate pass a
reopened slice (the slice 2 build report's Q1). Since A27 (1) ship-v2 moves the card with the grant (a `card_set` and
its `Status:` line, in build-v2's transaction), and every ending agrees by v1's rule: the card the records hold, the
`Status:` line and v1's rule are one value, and no ending lets the gate pass a reopened slice.
"""
import unittest

import cr25lib
import slib
import testlib

S = "signed off"
C = "signed off with conditions"
# scenario: (how the ship run ends, the card the records hold, the card by v1's rule, the Status: line, the gate)
MEASURED = {
    "waive_clean_end": ("completed ", S, S, S, "passes"),
    "waive_stop_1": ("stopped extra-lap-exhausted", C, C, C, "stops"),
    "waive_stop_2": ("stopped spec-change", C, C, C, "stops"),
    "waive_stop_3": ("stopped build-not-complete", S, S, S, "passes"),
    "waive_stop_4": ("stopped outside-footprint", C, C, C, "stops"),
    "waive_pause": ("paused (the run waits)", S, S, S, "passes"),
    "reopen_clean_end": ("completed ", S, S, S, "passes"),
    "reopen_stop_1": ("stopped extra-lap-exhausted", C, C, C, "stops"),
    "reopen_stop_2": ("stopped spec-change", C, C, C, "stops"),
    "reopen_stop_4": ("stopped outside-footprint", C, C, C, "stops"),
    "reopen_pause": ("paused (the run waits)", C, C, C, "stops"),
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
                grants = [k for k in row["ship_events"] if k in ("waived", "reopened")]
                self.assertEqual(len(grants), 1, row)
                self.assertEqual(row["ship_events"][0], grants[0], row)
                self.assertTrue(set(row["ship_events"]) <= {"waived", "reopened", "card_set"}, row)
                self.assertFalse(row["disagrees"], row)
                self.assertFalse(row["gate_passes_reopened"], row)

    def test_every_ending_agrees_by_v1s_rule_and_none_passes_a_reopened_slice(self):
        """A27 (1): the card the records hold, the Status: line and v1's rule agree in all 11 endings; no ending lets
        vertical-v2's gate pass a reopened slice (before the ruling: 6 disagreed and 3 passed one)."""
        disagree = [name for name, row in MEASURED.items() if row[1] != row[2] or row[3] != row[2]]
        passes_reopened = [name for name, row in MEASURED.items() if name.startswith("reopen") and row[4] == "passes"
                           and row[2] != "signed off"]
        self.assertEqual(len(MEASURED), 11)
        self.assertEqual(disagree, [])
        self.assertEqual(passes_reopened, [])

if __name__ == "__main__":
    unittest.main()
