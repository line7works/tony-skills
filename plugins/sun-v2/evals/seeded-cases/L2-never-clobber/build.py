#!/usr/bin/env python3
"""Generator for the L2-never-clobber family of the E16 seeded cases (the lane contract's section 12; the join, part J2).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome. The fixture is the join's
one machine on the three joined lanes (`caselib.joined`).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L2-never-clobber"
LOOK_GO = [{"do": "look", "inputs": {"type": "web app", "scaffold": "web app"}}, {"do": "go"}]
INDEX = "# Vault\n\n## Active projects\n- [[projects/other/_index|Other]]\n- [[projects/demo/_index|demo]]\n"

CASES = {
    "L2-01-clean": {"fixture": "joined", "drive": LOOK_GO[:1]},
    "L2-02-an-existing-local-folder": {"fixture": "joined", "drive": LOOK_GO,
                                       "plants": [{"plant": "put", "rel": "dev/demo/x.txt", "text": "his own file\n"}]},
    "L2-03-an-existing-remote": {"fixture": "joined", "drive": LOOK_GO, "plants": [{"plant": "remote-with-a-commit"}]},
    "L2-04-a-taken-project-name-on-the-host": {"fixture": "joined", "drive": LOOK_GO,
                                               "plants": [{"plant": "provider-state", "provider": "vercel", "fields": {"things": {"demo": {
                                                   "id": "prj_another1", "kind": "project", "state": "active", "name": "demo", "account": "team_another1"}}}}]},
    "L2-05-a-shortcut-that-shadows-a-program": {"fixture": "joined", "drive": LOOK_GO, "plants": [{"plant": "program-on-login-path", "name": "dm"}]},
    "L2-06-the-owners-own-identical-line-already-present": {"fixture": "joined", "drive": LOOK_GO,
                                                            "plants": [{"plant": "put", "rel": "vault/_index.md", "text": INDEX}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
