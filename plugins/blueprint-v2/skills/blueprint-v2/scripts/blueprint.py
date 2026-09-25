#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""blueprint.py: the phase driver of blueprint-v2 (E14; the frame of slice 1, the core of lane L).

    uv run blueprint.py check-input <input.json>
    uv run blueprint.py select --run-dir D --hunt scope|architecture|build [--name NAME]
    uv run blueprint.py choose --run-dir D --hunt NAME --path P --words "<the owner's words>"
    uv run blueprint.py harvest --run-dir D
    uv run blueprint.py record-answer --run-dir D --answer FILE
    uv run blueprint.py write --run-dir D
    uv run blueprint.py report --run-dir D
    uv run blueprint.py identity <workspace>
    uv run blueprint.py skill-identity

The shared phase driver is `station_core/driver.py` and `references/station-loop.md` is the
contract every front core shares; `references/blueprint-v2-contract.md` is this core's own: its
hunt table (below, with the tiers and why), its four lane phases and its one own command
(`blueprint_core/phases.py`), its stop tags and its recorded answer.

The hunts hold the v1 homes only (round 3, R6): each folder's dated name `<YYYY-MM-DD>-<topic>.md`,
matched by its topic, the part after the date, whole (`DATED`), and v1's older flat names.
`docs/plans/2026-09-22-big-turnstile.md` is another feature's doc and never `turnstile`'s. `scope`:
`docs/scope/<date>-{name}.md` and the older flat `docs/{name}-scope.md` in ONE tier (carried item
C1-7): a scope doc in the newer folder and one at the flat name that both match are `several`, listed
for the owner and never picked, as the station's step 1 says ("when more than one could match, list
them and ask"); an undated `docs/scope/<topic>.md` is no home. `architecture`: the folder's dated name
first, the flat `docs/{name}-architecture.md` second, since the hand-off table ranks the newer home
first; an undated `docs/architecture/<topic>.md` is no home. `build` (the living doc, under the
feature's name): `docs/plans/<date>-{name}.md` AND `docs/plans/{name}.md` first (round 5, R2: the
contract's `select` over `docs/plans/*.md` by topic; an existing undated plan is extended where it
lies, never forked into a dated twin, and the two together are `several`), the flat
`docs/{name}-build-plan.md` second, the station's step 4 order, so an older flat doc is extended where
it lies when no plan in the folder exists.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402
from blueprint_core import phases  # noqa: E402

STATION = "blueprint-v2"

DATED = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-{name}.md"

HUNTS = {
    "architecture": [
        {"home": "repo-architecture", "root": "workspace", "globs": ["docs/architecture/" + DATED], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-architecture.md"], "tier": 2},
    ],
    "build": [
        {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/" + DATED, "docs/plans/{name}.md"],
         "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
    ],
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/" + DATED], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-scope.md"], "tier": 1},
    ],
}

HANDLERS = {"harvest": phases.phase_harvest, "record-answer": phases.phase_record_answer,
            "write": phases.phase_write, "report": phases.phase_report}

COMMANDS = [
    {"name": "choose", "help": "record the owner's pick among a hunt's several candidates (before harvest)",
     "handler": phases.command_choose,
     "arguments": [{"flags": ["--run-dir"], "metavar": "D", "required": True, "help": "the run directory"},
                   {"flags": ["--hunt"], "metavar": "NAME", "required": True,
                    "help": "the hunt whose outcome was several"},
                   {"flags": ["--path"], "metavar": "P", "required": True,
                    "help": "the candidate the owner picked, as select listed it"},
                   {"flags": ["--words"], "metavar": "TEXT", "required": True,
                    "help": "the owner's words that picked it, verbatim, one line"}]},
]


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS, commands=COMMANDS))
