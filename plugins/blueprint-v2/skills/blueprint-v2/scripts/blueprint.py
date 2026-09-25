#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""blueprint.py: the phase driver of blueprint-v2 (E14; the frame of slice 1).

    uv run blueprint.py check-input <input.json>
    uv run blueprint.py select --run-dir D [--hunt architecture|build|scope] [--name NAME]
    uv run blueprint.py harvest --run-dir D
    uv run blueprint.py record-answer --run-dir D --answer FILE
    uv run blueprint.py write --run-dir D
    uv run blueprint.py report --run-dir D
    uv run blueprint.py identity <workspace>
    uv run blueprint.py skill-identity

The shared phase driver is `station_core/driver.py`; `references/station-loop.md` is the contract
of every command, its output and its exit codes. This file holds what is blueprint-v2's own: its
name, its hunt table, and the phases its lane has built. Until slice 2 builds them, `harvest`,
`record-answer`, `write` and `report` stop as `phase-not-built`.

The hunt tables are the v1 blueprint station's own (its Steps 1 and 4), plus the
architecture doc the E14 hand-off adds (station-loop.md section 9). `scope`:
`docs/scope/*.md` first, the older flat `docs/*-scope.md` second; matching to the named
feature is the executor's, and `several` is asked. `architecture`:
`docs/architecture/*.md`, then the older flat `docs/*-architecture.md`. `build` (the
living build doc, under the feature's topic): `docs/plans/*-<topic>.md`, then the older
flat `docs/<feature>-build-plan.md`.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402

STATION = "blueprint-v2"

HUNTS = {
    "architecture": [
        {"home": "repo-architecture", "root": "workspace", "globs": ["docs/architecture/*.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/*-architecture.md"], "tier": 2},
    ],
    "build": [
        {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
    ],
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/*-scope.md"], "tier": 2},
    ],
}

# The phases slice 2's lane L builds: {"harvest": fn, "record-answer": fn, "write": fn, "report": fn}.
HANDLERS = {}


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS))
