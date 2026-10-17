#!/usr/bin/env python3
"""Generator for the L6-resume family of the E16 seeded cases (the lane contract's section 12; slice 1).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L6-resume"
CASES = {
    "L6-01-clean": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go"}]},
    "L6-02-a-kill-at-every-point-of-every-operation": {"fixture": "clean", "drive": [{"do": "sweep"}]},
    "L6-03-a-lost-create-response": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go"}, {"do": "resume"}, {"do": "resume"}],
                                      "plants": [{"plant": "fake-plan", "tool": "fakehost", "entry": {"command": "create", "nth": 1, "do": "lose-answer"}}]},
    "L6-04-a-torn-last-line": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go", "kill_mid_append_of": ["start", "S1"], "torn": True}, {"do": "status"}, {"do": "resume"}]},
    "L6-05-two-runs-at-once": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go", "kill_after_journal": ["start", "C1"]}, {"do": "second-summons-while-held"}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
