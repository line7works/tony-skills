#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""inspect_v2.py: the phase driver of inspect-v2 (E14; the frame of slice 1).

    uv run inspect_v2.py check-input <input.json>
    uv run inspect_v2.py select --run-dir D [--hunt build|scope] [--name NAME]
    uv run inspect_v2.py harvest --run-dir D
    uv run inspect_v2.py record-answer --run-dir D --answer FILE
    uv run inspect_v2.py write --run-dir D
    uv run inspect_v2.py report --run-dir D
    uv run inspect_v2.py identity <workspace>
    uv run inspect_v2.py skill-identity

The shared phase driver is `station_core/driver.py`; `references/station-loop.md` is the contract
of every command, its output and its exit codes. This file holds what is inspect-v2's own: its
name, its hunt table, and the phases its lane has built. Until slice 2 builds them, `harvest`,
`record-answer`, `write` and `report` stop as `phase-not-built`.

The hunt tables are the v1 inspect station's own (its Step 1). `build`: `docs/plans/*-<topic>.md`,
then the older flat `docs/<feature>-build-plan.md`, then any phase or slice doc under `docs/`
or `plan/`, in that order (the two-source narrowing, then the fallback). `scope`: by glob,
never by a guessed slug, over every `docs/scope/*.md`, every older flat `docs/*-scope.md` and
every staging `*-scope.md`, one tier; matching by `Intent:` line is the executor's.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402

STATION = "inspect-v2"

HUNTS = {
    "build": [
        {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
        {"home": "phase-or-slice", "root": "workspace", "globs": ["docs/*phase*.md", "docs/*slice*.md", "plan/*.md"], "tier": 3},
    ],
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/*-scope.md"], "tier": 1},
        {"home": "staging", "root": "staging", "globs": ["*-scope.md"], "tier": 1},
    ],
}

# The phases slice 2's lane I builds: {"harvest": fn, "record-answer": fn, "write": fn, "report": fn}.
HANDLERS = {}


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS))
