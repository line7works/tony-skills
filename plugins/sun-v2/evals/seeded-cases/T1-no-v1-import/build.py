#!/usr/bin/env python3
"""Generator for the T1-no-v1-import family of the E16 seeded cases (the lane contract's section 12; slice 1).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "T1-no-v1-import"
CASES = {
    "T1-01-clean": {"drive": [{"do": "v1scan"}]},
    "T1-02-a-v1-path": {"drive": [{"do": "v1scan", "plant": {"rel": "lifecycle/scripts/sun_core/facts.py", "text_parts": ["\nV1 = \"plugins/", "s", "un/assets/rise.wav\"\n"]}}]},
    "T1-03-a-deference": {"drive": [{"do": "v1scan", "plant": {"rel": "skills/sunset-v2/SKILL.md", "text_parts": ["\nThe v1 skill is the ", "law where this skill is silent.\n"]}}]},
    "T1-04-a-subprocess-that-names-a-v1-skill": {"drive": [{"do": "v1scan", "plant": {"rel": "lifecycle/scripts/sun.py", "text_parts": ["\nimport subprocess\nsubprocess.run([\"claude\", \"/", "sun", "set\"])\n"]}}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
