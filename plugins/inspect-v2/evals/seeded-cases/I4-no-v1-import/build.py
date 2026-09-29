#!/usr/bin/env python3
"""Generator for the I4-no-v1-import family (E14 lane contract section 14, inspect-v2).

Standard library only, Python 3.9. Uses ../_lib/caselib.py; git runs only inside the throwaway
repositories the library creates under --out. CASES.md says what each case holds. `SPECS` holds
the files each case is built from and the steps `observe.py` drives; it states no outcome.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))
sys.dont_write_bytecode = True

import caselib  # noqa: E402

FAMILY = "I4-no-v1-import"
CORE = "inspect-v2"
SPECS = json.loads('{"I4-01-clean": {"drive": [{"kind": "v1scan", "plant": null}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n"}}, "I4-02-planted-v1-folder": {"drive": [{"kind": "v1scan", "plant": {"rel": "references/station-loop.md", "text_parts": ["\\nThe code book is plugins/", "blue", "print/skills/SKILL.md.\\n"]}}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n"}}, "I4-03-planted-deference": {"drive": [{"kind": "v1scan", "plant": {"rel": "SKILL.md", "text_parts": ["\\nThe other station\'s SKILL.md is the ", "law wherever this file is silent.\\n"]}}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n"}}, "I4-04-planted-subprocess": {"drive": [{"kind": "v1scan", "plant": {"rel": "scripts/station_core/exits.py", "text_parts": ["\\nimport subprocess\\nsubprocess.run([\\"claude\\", \\"-p\\", \\"/", "in", "spect\\"])\\n"]}}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n"}}}')

if __name__ == "__main__":
    caselib.make_family(FAMILY, CORE, SPECS)
