#!/usr/bin/env python3
"""Generator for the L5-git family of the E16 seeded cases (the lane contract's section 12; the join, part J2).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome. The fixture is the join's
one machine on the three joined lanes (`caselib.joined`).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L5-git"
LOOK = {"do": "look", "inputs": {"type": "web app", "scaffold": "web app"}}

CASES = {
    "L5-01-clean": {"fixture": "joined", "drive": [LOOK, {"do": "go"}]},
    "L5-02-a-remote-that-already-has-a-commit": {"fixture": "joined", "drive": [LOOK, {"do": "go"}], "plants": [{"plant": "remote-with-a-commit"}]},
    "L5-03-a-tracked-edit-after-the-push": {"fixture": "joined",
                                            "drive": [LOOK, {"do": "go", "kill": {"after_status": ["SR15", "done"]}},
                                                      {"do": "plant", "what": {"plant": "put", "rel": "dev/demo/README.md", "text": "# demo, edited by hand\n"}},
                                                      {"do": "status"}, {"do": "resume"}]},
    "L5-04-a-secret-in-a-commit-to-be-pushed": {"fixture": "joined", "plants": [{"plant": "committed-secret"}],
                                                "drive": [{"do": "look", "inputs": {"type": "web app", "scaffold": "adopted", "adopt": True}},
                                                          {"do": "go"}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
