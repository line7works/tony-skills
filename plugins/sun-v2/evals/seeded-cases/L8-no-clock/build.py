#!/usr/bin/env python3
"""Generator for the L8-no-clock family of the E16 seeded cases (the lane contract's section 12; the join, part J2).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome. The fixture is the join's
one machine on the three joined lanes (`caselib.joined`).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L8-no-clock"
SUNRISE = [{"do": "look", "inputs": {"type": "web app", "scaffold": "web app"}}, {"do": "go"}]
SUNSET = [{"do": "look", "kind": "sunset"}, {"do": "go", "kind": "sunset"}]
STATUS = [{"do": "status", "kind": "sunset"}]

CASES = {
    "L8-01-clean": {"fixture": "joined", "drive": SUNRISE + SUNSET},
    "L8-02-a-dump-cut-off": {"fixture": "joined", "drive": SUNRISE + [{"do": "plant", "what": {"plant": "provider-plan", "provider": "pg", "entries": [
        {"command": "pg_dump", "do": "short"}]}}] + SUNSET + STATUS},
    "L8-03-a-failed-tag-push": {"fixture": "joined", "drive": SUNRISE + [{"do": "plant", "what": {"plant": "tag-push-refused"}}] + SUNSET + STATUS},
    "L8-04-a-dump-of-another-database": {"fixture": "joined", "drive": SUNRISE + [{"do": "plant", "what": {
        "plant": "dump-of-another-database", "becomes": {"identity": "8000000000000000002", "tables": {"beta": ["3"]}}}}] + SUNSET + STATUS},
    "L8-05-a-dump-that-cannot-be-bound": {"fixture": "joined", "drive": SUNRISE + [{"do": "plant", "what": {
        "plant": "provider-state", "provider": "pg", "fields": {"identity": None}}}] + SUNSET + STATUS},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
