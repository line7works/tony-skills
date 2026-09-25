#!/usr/bin/env python3
"""Generator for the P2-one-living-doc family (E14 lane contract section 14, precon-v2).

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

FAMILY = "P2-one-living-doc"
CORE = "precon-v2"
SPECS = json.loads('{"P2-01-clean": {"drive": [{"hunt": "scope", "kind": "select", "name": "turnstile"}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n"}}, "P2-02-one-home": {"drive": [{"hunt": "scope", "kind": "select", "name": "turnstile"}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n", "docs/scope/2026-09-20-turnstile.md": "# Turnstile \\u2014 scope doc (2026-09-20)\\n\\nIntent: a small turn counter for the owner\'s bench rig, so one bench session can report how many turns a fixture made.\\nDecisions:\\n- Python 3.9 standard library only \\u2014 decided (the owner\'s words: \\"no dependencies on the bench\\")\\n- One module, no package \\u2014 assumed (small and reversible; nothing imports it yet)\\n- Where the count is kept between sessions \\u2014 parked: needs research\\n- A second counting mode for reverse turns \\u2014 parked: waiting on the bench rig\'s encoder spec\\nOut of scope: a web dashboard \\u2014 the owner declined it for the first version\\nResearch:\\nOpen:\\n- how often the counter resets\\nNext: /blueprint when ready.\\n"}}, "P2-03-two-homes": {"drive": [{"hunt": "scope", "kind": "select", "name": "turnstile"}], "staging": {"turnstile-scope.md": "# Turnstile \\u2014 scope doc (2026-09-20)\\n\\nIntent: a small turn counter for the owner\'s bench rig, so one bench session can report how many turns a fixture made.\\nDecisions:\\n- Python 3.9 standard library only \\u2014 decided (the owner\'s words: \\"no dependencies on the bench\\")\\n- One module, no package \\u2014 assumed (small and reversible; nothing imports it yet)\\n- Where the count is kept between sessions \\u2014 parked: needs research\\n- A second counting mode for reverse turns \\u2014 parked: waiting on the bench rig\'s encoder spec\\nOut of scope: a web dashboard \\u2014 the owner declined it for the first version\\nResearch:\\nOpen:\\n- how often the counter resets\\nNext: /blueprint when ready.\\n"}, "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n", "docs/scope/2026-09-20-turnstile.md": "# Turnstile \\u2014 scope doc (2026-09-20)\\n\\nIntent: a small turn counter for the owner\'s bench rig, so one bench session can report how many turns a fixture made.\\nDecisions:\\n- Python 3.9 standard library only \\u2014 decided (the owner\'s words: \\"no dependencies on the bench\\")\\n- One module, no package \\u2014 assumed (small and reversible; nothing imports it yet)\\n- Where the count is kept between sessions \\u2014 parked: needs research\\n- A second counting mode for reverse turns \\u2014 parked: waiting on the bench rig\'s encoder spec\\nOut of scope: a web dashboard \\u2014 the owner declined it for the first version\\nResearch:\\nOpen:\\n- how often the counter resets\\nNext: /blueprint when ready.\\n"}}, "P2-04-flat-home": {"drive": [{"hunt": "scope", "kind": "select", "name": "turnstile"}], "workspace": {"README.md": "# Turnstile\\n\\nA bench-rig turn counter.\\n", "docs/turnstile-scope.md": "# Turnstile \\u2014 scope doc (2026-09-20)\\n\\nIntent: a small turn counter for the owner\'s bench rig, so one bench session can report how many turns a fixture made.\\nDecisions:\\n- Python 3.9 standard library only \\u2014 decided (the owner\'s words: \\"no dependencies on the bench\\")\\n- One module, no package \\u2014 assumed (small and reversible; nothing imports it yet)\\n- Where the count is kept between sessions \\u2014 parked: needs research\\n- A second counting mode for reverse turns \\u2014 parked: waiting on the bench rig\'s encoder spec\\nOut of scope: a web dashboard \\u2014 the owner declined it for the first version\\nResearch:\\nOpen:\\n- how often the counter resets\\nNext: /blueprint when ready.\\n"}}}')

if __name__ == "__main__":
    caselib.make_family(FAMILY, CORE, SPECS)
