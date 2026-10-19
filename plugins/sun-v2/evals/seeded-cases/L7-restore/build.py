#!/usr/bin/env python3
"""Generator for the L7-restore family of the E16 seeded cases (the lane contract's section 12; the join, part J2).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome. The fixture is the join's
one machine on the three joined lanes (`caselib.joined`).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L7-restore"
SUNRISE = [{"do": "look", "inputs": {"type": "web app", "scaffold": "web app"}}, {"do": "go"},
           {"do": "plant", "what": {"plant": "schedule-layers"}}, {"do": "snapshot", "label": "after the sunrise"}]
SUNSET = [{"do": "look", "kind": "sunset"}, {"do": "go", "kind": "sunset"}, {"do": "snapshot", "label": "after the sunset"}]
RESTORE = [{"do": "look", "kind": "restore"}, {"do": "go", "kind": "restore"}]


def case(*between, **more):
    drive = SUNRISE + SUNSET + list(between) + RESTORE + list(more.get("after") or [])
    if more.get("kill"):
        drive[-1 - len(more.get("after") or [])] = {"do": "go", "kind": "restore", "kill": more["kill"]}
    return {"fixture": "joined", "drive": drive}


CASES = {
    "L7-01-clean": case(),
    "L7-02-an-expired-provider-state": case({"do": "plant", "what": {"plant": "provider-thing-gone", "provider": "vercel", "name": "demo"}}),
    "L7-03-a-line-someone-edited-after-sunset": case({"do": "plant", "what": {"plant": "edit-text", "rel": "vault/archive/demo/_index.md",
                                                                              "old": "status: archived\n", "new": "status: archived, edited by hand\n"}}),
    "L7-04-the-old-name-taken": case({"do": "plant", "what": {"plant": "put", "rel": "dev/demo/other.txt", "text": "another project\n"}}),
    "L7-05-a-kill-mid-restore": case(kill={"after_start_of": "V02"}, after=[{"do": "status", "kind": "restore"}, {"do": "resume", "kind": "restore"}]),
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
