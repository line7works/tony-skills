#!/usr/bin/env python3
"""Generator for the L1-the-gate family of the E16 seeded cases (the lane contract's section 12; slice 1).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L1-the-gate"
CASES = {
    "L1-01-clean": {"fixture": "clean", "drive": [{"do": "look"}]},
    "L1-02-no-vault": {"fixture": "clean", "plants": [{"plant": "no-vault"}], "drive": [{"do": "look"}]},
    "L1-03-stub-without-its-marker": {"fixture": "clean", "plants": [{"plant": "stub-vault"}], "drive": [{"do": "look"}]},
    "L1-04-vault-in-a-synced-folder": {"fixture": "clean", "plants": [{"plant": "synced-vault"}], "drive": [{"do": "look"}]},
    "L1-05-marker-but-no-projects-folder": {"fixture": "clean", "plants": [{"plant": "no-projects-folder"}], "drive": [{"do": "look"}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
