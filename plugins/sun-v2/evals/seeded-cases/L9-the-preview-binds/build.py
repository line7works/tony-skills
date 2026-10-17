#!/usr/bin/env python3
"""Generator for the L9-the-preview-binds family of the E16 seeded cases (the lane contract's section 12; slice 1).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L9-the-preview-binds"
CASES = {
    "L9-01-clean": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go"}]},
    "L9-02-a-manifest-changed-after-the-go": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go", "kill_after_journal": ["completion", "B1"]}, {"do": "alter-manifest"}, {"do": "resume"}]},
    "L9-03-an-operation-outside-it": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go", "kill_after_journal": ["completion", "B1"]}, {"do": "alter-manifest", "inject": True}, {"do": "status"}]},
    "L9-04-an-owner-operation": {"fixture": "owner-step", "drive": [{"do": "look"}, {"do": "go"}, {"do": "status"}, {"do": "owner-acts"}, {"do": "status"}]},
    "L9-05-a-go-on-another-manifest": {"fixture": "clean", "drive": [{"do": "look"}, {"do": "go", "wrong_hash": True}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
