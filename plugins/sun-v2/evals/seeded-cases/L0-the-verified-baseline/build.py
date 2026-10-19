#!/usr/bin/env python3
"""Generator for the L0-the-verified-baseline family of the E16 seeded cases (the lane contract's section 12; the join, part J2).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome. The fixture is the join's
one machine on the three joined lanes (`caselib.joined`).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L0-the-verified-baseline"
RISE = [{"do": "look"}, {"do": "go"}]


def sunrise(type_, **more):
    steps = [dict(s) for s in RISE]
    steps[0]["inputs"] = {"type": type_, "scaffold": type_}
    steps[0].update(more)
    return steps


CASES = {
    "L0-01-clean": {"fixture": "joined", "drive": sunrise("web app")},
    "L0-02-a-static-site": {"fixture": "joined", "drive": sunrise("static site")},
    "L0-03-a-desktop-app": {"fixture": "joined", "drive": sunrise("desktop app")},
    "L0-04-a-script-or-cli": {"fixture": "joined", "drive": sunrise("script or CLI")},
    "L0-05-a-harness-that-declares-no-canary": {"fixture": "joined", "drive": sunrise("web app", caps=["memory stores", "routines"])},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
