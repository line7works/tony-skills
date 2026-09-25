#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""precon.py: the phase driver of precon-v2 (E14; the frame of slice 1).

    uv run precon.py check-input <input.json>
    uv run precon.py select --run-dir D [--hunt scope] [--name NAME]
    uv run precon.py harvest --run-dir D
    uv run precon.py record-answer --run-dir D --answer FILE
    uv run precon.py write --run-dir D
    uv run precon.py report --run-dir D
    uv run precon.py identity <workspace>
    uv run precon.py skill-identity

The shared phase driver is `station_core/driver.py`; `references/station-loop.md` is the contract
of every command, its output and its exit codes. This file holds what is precon-v2's own: its
name, its hunt table, and the phases its lane has built. Until slice 2 builds them, `harvest`,
`record-answer`, `write` and `report` stop as `phase-not-built`.

The hunt table is the v1 precon station's own homes for an existing scope doc under an idea
slug (its Step 4): the repo doc kit's `docs/scope/*-<idea>.md`, the older flat
`docs/<idea>-scope.md`, and the staging home's `<idea>-scope.md`, all one tier, so a doc
found in two homes is `several` and asked, never picked.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402

STATION = "precon-v2"

HUNTS = {
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*-{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-scope.md"], "tier": 1},
        {"home": "staging", "root": "staging", "globs": ["{name}-scope.md"], "tier": 1},
    ],
}

# The phases slice 2's lane P builds: {"harvest": fn, "record-answer": fn, "write": fn, "report": fn}.
HANDLERS = {}


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS))
