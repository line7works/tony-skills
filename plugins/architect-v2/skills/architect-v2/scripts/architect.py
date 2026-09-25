#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""architect.py: the phase driver of architect-v2 (E14; the frame of slice 1).

    uv run architect.py check-input <input.json>
    uv run architect.py select --run-dir D [--hunt architecture|scope] [--name NAME]
    uv run architect.py harvest --run-dir D
    uv run architect.py record-answer --run-dir D --answer FILE
    uv run architect.py write --run-dir D
    uv run architect.py report --run-dir D
    uv run architect.py identity <workspace>
    uv run architect.py skill-identity

The shared phase driver is `station_core/driver.py`; `references/station-loop.md` is the contract
of every command, its output and its exit codes. This file holds what is architect-v2's own: its
name, its hunt table, and the phases its lane has built. Until slice 2 builds them, `harvest`,
`record-answer`, `write` and `report` stop as `phase-not-built`.

The hunt tables are the v1 architect station's own. `scope` (its Step 1, the input gate): a
glob over precon's homes, `docs/scope/*.md`, the older flat `docs/*-scope.md`, and the
staging home's `*-scope.md`, one tier; matching a candidate to the project by its `Intent:`
line is the executor's, and `several` is asked. `architecture` (its Step 4, the living doc,
under the scope doc's slug): `docs/architecture/*-<slug>.md`, then the older flat
`docs/<slug>-architecture.md`, then the staging home's `<slug>-architecture.md`, in that order.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402

STATION = "architect-v2"

HUNTS = {
    "architecture": [
        {"home": "repo-architecture", "root": "workspace", "globs": ["docs/architecture/*-{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-architecture.md"], "tier": 2},
        {"home": "staging", "root": "staging", "globs": ["{name}-architecture.md"], "tier": 3},
    ],
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/*-scope.md"], "tier": 1},
        {"home": "staging", "root": "staging", "globs": ["*-scope.md"], "tier": 1},
    ],
}

# The phases slice 2's lane A builds: {"harvest": fn, "record-answer": fn, "write": fn, "report": fn}.
HANDLERS = {}


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS))
