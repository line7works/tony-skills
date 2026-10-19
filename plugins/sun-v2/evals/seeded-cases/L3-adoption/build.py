#!/usr/bin/env python3
"""Generator for the L3-adoption family of the E16 seeded cases (the lane contract's section 12; the join, part J2).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome. The fixture is the join's
one machine on the three joined lanes (`caselib.joined`).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L3-adoption"
LOOK_GO = [{"do": "look", "inputs": {"type": "web app", "scaffold": "web app"}}, {"do": "go"}]
SCOPE = "# demo scope doc (2026-09-03)\nbody\n"


def staged(rel, text):
    return {"plant": "put", "rel": "staged/" + rel, "text": text, "note_sha256_as": "sha256 of staged/" + rel}


CASES = {
    "L3-01-clean": {"fixture": "joined", "drive": LOOK_GO, "plants": [staged("demo-scope.md", SCOPE)]},
    "L3-02-two-candidates-for-one-role": {"fixture": "joined", "drive": LOOK_GO,
                                          "plants": [staged("precon-cold-reads/demo-cold-read-2026-10-01.md", "# demo cold read\none\n"),
                                                     staged("precon-cold-reads/demo-cold-read-2026-10-02.md", "# demo cold read\ntwo\n")]},
    "L3-03-a-doc-an-interrupted-run-already-moved": {"fixture": "joined", "plants": [staged("demo-scope.md", SCOPE)],
                                                     "drive": [LOOK_GO[0], {"do": "go", "kill": {"stage": "post", "act": "rename",
                                                                                                "subject_endswith": "2026-09-03-demo.md"}},
                                                               {"do": "status"}, {"do": "resume"}]},
    "L3-04-a-doc-with-no-date-anywhere": {"fixture": "joined", "drive": LOOK_GO,
                                          "plants": [staged("demo-scope.md", "# demo scope doc\nbody\n")]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
